package hotspot

import (
	"bytes"
	"context"
	"fmt"
	"strings"
)

// treeBlobs returns a map of root-relative path to blob OID at a given commit.
func (gc *gitContext) treeBlobs(ctx context.Context, commitOID string) (map[string]string, error) {
	if !isValidOID(commitOID, gc.objectFormat) {
		return nil, fmt.Errorf("invalid commit OID %q", commitOID)
	}

	out, err := gc.runGit(ctx, "ls-tree", "-r", "-z", "--full-name", commitOID)
	if err != nil {
		return nil, fmt.Errorf("failed to list tree at %s: %w", commitOID, err)
	}

	blobs := make(map[string]string)
	entries := bytes.Split(out, []byte{0})
	for _, entry := range entries {
		if len(entry) == 0 {
			continue
		}
		tabIdx := bytes.IndexByte(entry, '\t')
		if tabIdx == -1 {
			return nil, fmt.Errorf("malformed ls-tree entry: missing tab in %q", string(entry))
		}
		meta := string(entry[:tabIdx])
		path := string(entry[tabIdx+1:])

		if err := validateGitPath(path); err != nil {
			return nil, fmt.Errorf("invalid path %q in tree %s: %w", path, commitOID, err)
		}

		fields := strings.Fields(meta)
		if len(fields) != 3 {
			return nil, fmt.Errorf("malformed ls-tree metadata %q for path %q", meta, path)
		}

		mode := fields[0]
		objType := fields[1]
		oid := fields[2]

		if mode == "120000" {
			return nil, fmt.Errorf("unsupported tree entry type for path %q: symlinks are not supported", path)
		}
		if mode == "160000" || objType == "commit" {
			return nil, fmt.Errorf("unsupported tree entry type for path %q: gitlinks/submodules are not supported", path)
		}
		if objType != "blob" || !isSupportedGitMode(mode) {
			return nil, fmt.Errorf("unsupported tree entry %s (%s) for path %q; only regular blobs are supported", objType, mode, path)
		}

		if !isValidOID(oid, gc.objectFormat) {
			return nil, fmt.Errorf("invalid blob OID %q for path %q in tree %s", oid, path, commitOID)
		}

		if _, exists := blobs[path]; exists {
			return nil, fmt.Errorf("duplicate path %q in tree %s", path, commitOID)
		}

		if len(blobs) >= maxTreeEntries {
			return nil, fmt.Errorf("history limit exceeded: tree %s exceeds maximum entry limit (%d)", commitOID, maxTreeEntries)
		}

		blobs[path] = oid
	}
	return blobs, nil
}

type pathTransition struct {
	path   string
	oldOID string
	newOID string
}

// diffFirstParentCommit returns all content-changing path transitions for commit against its first parent.
func (gc *gitContext) diffFirstParentCommit(ctx context.Context, parentOID, commitOID string) ([]pathTransition, error) {
	if !isValidOID(parentOID, gc.objectFormat) {
		return nil, fmt.Errorf("invalid parent OID %q", parentOID)
	}
	if !isValidOID(commitOID, gc.objectFormat) {
		return nil, fmt.Errorf("invalid commit OID %q", commitOID)
	}

	out, err := gc.runGit(ctx, "diff-tree", "-r", "--no-renames", "--no-abbrev", "--no-ext-diff", "-z", "--raw", parentOID, commitOID)
	if err != nil {
		return nil, fmt.Errorf("failed to diff %s against %s: %w", parentOID, commitOID, err)
	}

	if len(out) == 0 {
		return nil, nil
	}
	if out[len(out)-1] != 0 {
		return nil, fmt.Errorf("malformed diff-tree output: missing null terminator")
	}

	tokens := bytes.Split(out[:len(out)-1], []byte{0})
	if len(tokens)%2 != 0 {
		return nil, fmt.Errorf("malformed diff-tree output: odd number of tokens (%d)", len(tokens))
	}

	var transitions []pathTransition
	for i := 0; i < len(tokens); i += 2 {
		metaBytes := tokens[i]
		pathBytes := tokens[i+1]
		path := string(pathBytes)

		if err := validateGitPath(path); err != nil {
			return nil, fmt.Errorf("invalid path %q in diff between %s and %s: %w", path, parentOID, commitOID, err)
		}

		meta := string(metaBytes)
		if !strings.HasPrefix(meta, ":") {
			return nil, fmt.Errorf("malformed diff-tree meta %q for path %q", meta, path)
		}

		fields := strings.Fields(meta)
		if len(fields) != 5 {
			return nil, fmt.Errorf("malformed diff-tree metadata fields %q for path %q", meta, path)
		}

		srcMode := strings.TrimPrefix(fields[0], ":")
		dstMode := fields[1]
		oldOID := fields[2]
		newOID := fields[3]

		if srcMode == "120000" || dstMode == "120000" {
			return nil, fmt.Errorf("unsupported entry type for path %q: symlinks are not supported", path)
		}
		if srcMode == "160000" || dstMode == "160000" {
			return nil, fmt.Errorf("unsupported entry type for path %q: gitlinks/submodules are not supported", path)
		}
		if !isSupportedGitMode(srcMode) || !isSupportedGitMode(dstMode) {
			return nil, fmt.Errorf("unsupported mode %s->%s for path %q; only regular blobs are supported", srcMode, dstMode, path)
		}

		if !isZeroOID(oldOID, gc.objectFormat) && !isValidOID(oldOID, gc.objectFormat) {
			return nil, fmt.Errorf("invalid old OID %q for path %q", oldOID, path)
		}
		if !isZeroOID(newOID, gc.objectFormat) && !isValidOID(newOID, gc.objectFormat) {
			return nil, fmt.Errorf("invalid new OID %q for path %q", newOID, path)
		}

		if oldOID != newOID {
			transitions = append(transitions, pathTransition{
				path:   path,
				oldOID: oldOID,
				newOID: newOID,
			})
		}
	}

	return transitions, nil
}
