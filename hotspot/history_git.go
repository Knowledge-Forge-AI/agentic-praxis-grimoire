package hotspot

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"sync/atomic"
)

const (
	maxGitMetadataBytes = 16 * 1024 * 1024 // 16 MiB fixed declared metadata budget per command
	maxTreeEntries      = 100_000          // bound tree path metadata entries
)

type gitContext struct {
	gitPath      string
	root         string
	gitDir       string
	objectFormat string
	env          []string
}

func initGitContext(ctx context.Context, root string) (*gitContext, error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}

	gitPath, err := exec.LookPath("git")
	if err != nil {
		return nil, errors.New("git executable not found on PATH; required for history analysis")
	}

	if root == "" || !filepath.IsAbs(root) || filepath.Clean(root) != root {
		return nil, errors.New("root must be an absolute clean path")
	}
	st, err := os.Lstat(root)
	if err != nil {
		return nil, fmt.Errorf("cannot stat root: %w", err)
	}
	if st.Mode()&os.ModeSymlink != 0 || !st.IsDir() {
		return nil, errors.New("root must be a direct directory")
	}
	resolvedRoot, err := filepath.EvalSymlinks(root)
	if err != nil {
		return nil, fmt.Errorf("cannot resolve root symlinks: %w", err)
	}
	if resolvedRoot != root {
		return nil, errors.New("root cannot contain symlinks")
	}

	var cleanEnv []string
	for _, env := range os.Environ() {
		if strings.HasPrefix(env, "GIT_") {
			continue
		}
		cleanEnv = append(cleanEnv, env)
	}
	cleanEnv = append(cleanEnv,
		"GIT_CONFIG_NOSYSTEM=1",
		"GIT_CONFIG_GLOBAL=/dev/null",
		"GIT_CONFIG_SYSTEM=/dev/null",
		"GIT_NO_REPLACE_OBJECTS=1",
		"GIT_NO_LAZY_FETCH=1",
		"GIT_TERMINAL_PROMPT=0",
		"GIT_OPTIONAL_LOCKS=0",
		"GIT_ALLOW_PROTOCOL=",
		"LC_ALL=C",
	)

	gc := &gitContext{
		gitPath: gitPath,
		root:    root,
		env:     cleanEnv,
	}

	if err := gc.validateRepo(ctx); err != nil {
		return nil, err
	}

	return gc, nil
}

func (gc *gitContext) runGit(ctx context.Context, args ...string) ([]byte, error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}

	subcmd := "git"
	if len(args) > 0 {
		subcmd = args[0]
	}

	baseArgs := []string{
		"-c", "protocol.allow=never",
		"-c", "protocol.file.allow=never",
		"-c", "protocol.http.allow=never",
		"-c", "protocol.https.allow=never",
		"-c", "protocol.ssh.allow=never",
		"-c", "protocol.git.allow=never",
		"-c", "protocol.ext.allow=never",
		"-c", "core.useReplaceRefs=false",
		"-c", "diff.external=",
		"-c", "diff.textconv=false",
		"-c", "diff.renames=false",
	}
	cmdArgs := append(baseArgs, args...)
	cmd := exec.CommandContext(ctx, gc.gitPath, cmdArgs...)
	cmd.Dir = gc.root
	cmd.Env = gc.env

	stdoutPipe, err := cmd.StdoutPipe()
	if err != nil {
		return nil, fmt.Errorf("failed to open stdout pipe for git %s: %w", subcmd, err)
	}
	stderrPipe, err := cmd.StderrPipe()
	if err != nil {
		_ = stdoutPipe.Close()
		return nil, fmt.Errorf("failed to open stderr pipe for git %s: %w", subcmd, err)
	}

	if err := cmd.Start(); err != nil {
		_ = stdoutPipe.Close()
		_ = stderrPipe.Close()
		if ctx.Err() != nil {
			return nil, ctx.Err()
		}
		return nil, fmt.Errorf("failed to start git %s: %w", subcmd, err)
	}

	var stdoutBuf bytes.Buffer
	var excess atomic.Bool
	var wg sync.WaitGroup

	wg.Add(2)
	go func() {
		defer wg.Done()
		lr := io.LimitReader(stdoutPipe, maxGitMetadataBytes+1)
		n, copyErr := io.Copy(&stdoutBuf, lr)
		if copyErr != nil {
			excess.Store(true)
		}
		if n > maxGitMetadataBytes {
			excess.Store(true)
			if cmd.Process != nil {
				_ = cmd.Process.Kill()
			}
		}
	}()

	go func() {
		defer wg.Done()
		lr := io.LimitReader(stderrPipe, maxGitMetadataBytes+1)
		var discard bytes.Buffer
		n, copyErr := io.Copy(&discard, lr)
		if copyErr != nil {
			excess.Store(true)
		}
		if n > maxGitMetadataBytes {
			excess.Store(true)
			if cmd.Process != nil {
				_ = cmd.Process.Kill()
			}
		}
	}()

	wg.Wait()
	waitErr := cmd.Wait()

	if ctx.Err() != nil {
		return nil, ctx.Err()
	}

	if excess.Load() {
		return nil, fmt.Errorf("git %s: command output exceeded metadata budget (%d bytes)", subcmd, maxGitMetadataBytes)
	}

	if waitErr != nil {
		return nil, fmt.Errorf("git %s failed: %w", subcmd, waitErr)
	}

	return stdoutBuf.Bytes(), nil
}

func (gc *gitContext) verifyCommitExists(ctx context.Context, oid string, role string) error {
	if !isValidOID(oid, gc.objectFormat) {
		return fmt.Errorf("history %s commit %q does not match %s format", role, oid, gc.objectFormat)
	}

	out, err := gc.runGit(ctx, "cat-file", "-t", oid)
	if err != nil {
		return fmt.Errorf("history %s commit %q does not exist", role, oid)
	}

	objType := strings.TrimSpace(string(out))
	if objType != "commit" {
		return fmt.Errorf("history %s object %q is not a commit (type is %s)", role, oid, objType)
	}

	return nil
}

// firstParentCommits returns the chronological sequence of commits in the range
// (start excluded, end included) along the first-parent chain of end.
func (gc *gitContext) firstParentCommits(ctx context.Context, startOID, endOID string, maxCommits int) ([]string, error) {
	if startOID == endOID {
		return nil, nil
	}
	if !isValidOID(startOID, gc.objectFormat) {
		return nil, fmt.Errorf("invalid start OID %q", startOID)
	}
	if !isValidOID(endOID, gc.objectFormat) {
		return nil, fmt.Errorf("invalid end OID %q", endOID)
	}

	maxCountArg := fmt.Sprintf("--max-count=%d", maxCommits+1)
	out, err := gc.runGit(ctx, "rev-list", "--first-parent", maxCountArg, endOID)
	if err != nil {
		return nil, fmt.Errorf("failed to traverse first-parent chain from %s: %w", endOID, err)
	}

	lines := strings.Split(strings.TrimSpace(string(out)), "\n")
	var rangeReversed []string
	foundStart := false

	for _, line := range lines {
		commit := strings.TrimSpace(line)
		if commit == "" {
			continue
		}
		if !isValidOID(commit, gc.objectFormat) {
			return nil, fmt.Errorf("malformed commit OID %q in rev-list", commit)
		}
		if commit == startOID {
			foundStart = true
			break
		}
		rangeReversed = append(rangeReversed, commit)
		if len(rangeReversed) > maxCommits {
			return nil, fmt.Errorf("history limit exceeded: commit count (%d) exceeds limit (%d)", len(rangeReversed), maxCommits)
		}
	}

	if !foundStart {
		return nil, fmt.Errorf("start commit %s is not an ancestor of end commit %s along its first-parent chain", startOID, endOID)
	}

	// Reverse so that commits are chronological: [child of start, ..., end]
	commits := make([]string, len(rangeReversed))
	for i, commit := range rangeReversed {
		commits[len(rangeReversed)-1-i] = commit
	}

	return commits, nil
}
