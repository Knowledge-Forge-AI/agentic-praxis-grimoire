package skills

import (
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"syscall"
)

// CaptureCatalogSource is the provisional read-only filesystem adapter. The
// selected root may be a symlink; descendant access is confined with os.Root.
func CaptureCatalogSource(source, root string) (CatalogInput, error) {
	input := CatalogInput{SchemaVersion: CatalogSchemaV1, Snapshots: []SkillSnapshot{}, Diagnostics: []CatalogDiagnostic{}, Sources: []CatalogSourceStatus{}}
	relative := "skills"
	if source == "project" {
		relative = ".apgr/skills"
	} else if source != "user" {
		return input, fmt.Errorf("unsupported local catalog source")
	}
	status := CatalogSourceStatus{Source: source, SelectedRoot: root, Status: "absent"}
	finish := func(message string) (CatalogInput, error) {
		status.Status = message
		input.Sources = append(input.Sources, status)
		return input, nil
	}
	if root == "" {
		return finish("not-selected")
	}
	if !filepath.IsAbs(root) {
		return input, fmt.Errorf("source root must be absolute")
	}
	resolved, err := filepath.EvalSymlinks(root)
	if os.IsNotExist(err) {
		return finish("absent")
	}
	if err != nil {
		input.Diagnostics = append(input.Diagnostics, CatalogDiagnostic{source, root, "unusable source root"})
		return finish("unusable")
	}
	status.ResolvedRoot = resolved
	owner, err := os.OpenRoot(resolved)
	if err != nil {
		input.Diagnostics = append(input.Diagnostics, CatalogDiagnostic{source, root, "unreadable source root"})
		return finish("unusable")
	}
	defer owner.Close()
	for _, part := range []string{strings.Split(relative, "/")[0], relative} {
		info, inspectErr := owner.Lstat(part)
		if os.IsNotExist(inspectErr) {
			return finish("absent")
		}
		if inspectErr != nil || !info.IsDir() || info.Mode()&os.ModeSymlink != 0 {
			input.Diagnostics = append(input.Diagnostics, CatalogDiagnostic{source, filepath.Join(root, relative), "unsafe/unreadable skills root"})
			return finish("unusable")
		}
	}
	sourceRoot, err := owner.OpenRoot(relative)
	if os.IsNotExist(err) {
		return finish("absent")
	}
	if err != nil {
		input.Diagnostics = append(input.Diagnostics, CatalogDiagnostic{source, filepath.Join(root, relative), "unsafe/unreadable skills root"})
		return finish("unusable")
	}
	defer sourceRoot.Close()
	directory, err := sourceRoot.Open(".")
	if err != nil {
		return input, err
	}
	entries, err := directory.ReadDir(4097)
	directory.Close()
	if err != nil && err != io.EOF {
		return input, err
	}
	if len(entries) > 4096 {
		return input, fmt.Errorf("catalog source exceeds leaf limit")
	}
	capturedBytes := 0
	for _, entry := range entries {
		id := entry.Name()
		path := filepath.Join(resolved, relative, id, "SKILL.md")
		if !entry.IsDir() && entry.Type()&os.ModeSymlink == 0 {
			continue
		}
		snapshot := SkillSnapshot{QualifiedID: source + ":" + id, Path: path, Support: map[string][]byte{}}
		if !catalogID.MatchString(id) {
			input.Diagnostics = append(input.Diagnostics, CatalogDiagnostic{snapshot.QualifiedID, path, "invalid directory ID"})
			continue
		}
		if entry.Type()&os.ModeSymlink != 0 {
			input.Diagnostics = append(input.Diagnostics, CatalogDiagnostic{snapshot.QualifiedID, path, "leaf directory symlink refused"})
			continue
		}
		leaf, err := sourceRoot.OpenRoot(id)
		if err != nil {
			input.Diagnostics = append(input.Diagnostics, CatalogDiagnostic{snapshot.QualifiedID, path, "unsafe/unreadable leaf"})
			continue
		}
		snapshot.Body, err = captureCatalogFile(leaf, "SKILL.md")
		if err == nil {
			var fields map[string]string
			fields, _, err = catalogMetadata(snapshot.Body)
			if err == nil {
				var names []string
				names, err = declaredList(fields, "support")
				if err == nil {
					for _, name := range names {
						if strings.Contains(name, "\\") {
							err = fmt.Errorf("invalid support path")
							break
						}
						var data []byte
						data, err = captureCatalogFile(leaf, name)
						if err != nil {
							break
						}
						snapshot.Support[name] = data
					}
				}
			}
		}
		leaf.Close()
		if err != nil {
			input.Diagnostics = append(input.Diagnostics, CatalogDiagnostic{snapshot.QualifiedID, path, err.Error()})
			continue
		}
		capturedBytes += len(snapshot.Body)
		for _, data := range snapshot.Support {
			capturedBytes += len(data)
		}
		if capturedBytes > 64<<20 {
			return input, fmt.Errorf("catalog source exceeds byte limit")
		}
		input.Snapshots = append(input.Snapshots, snapshot)
	}
	return finish("captured")
}

func captureCatalogFile(root *os.Root, name string) ([]byte, error) {
	before, err := root.Lstat(name)
	if err != nil || !before.Mode().IsRegular() {
		return nil, fmt.Errorf("unreadable/non-regular catalog file %s", name)
	}
	if before.Size() > MaxCatalogFileBytes {
		return nil, fmt.Errorf("oversize catalog file %s", name)
	}
	f, err := root.OpenFile(name, os.O_RDONLY|syscall.O_NONBLOCK|syscall.O_NOFOLLOW, 0)
	if err != nil {
		return nil, fmt.Errorf("unsafe catalog file %s", name)
	}
	defer f.Close()
	opened, err := f.Stat()
	if err != nil || !os.SameFile(before, opened) || !opened.Mode().IsRegular() {
		return nil, fmt.Errorf("catalog file changed during capture")
	}
	data, err := io.ReadAll(io.LimitReader(f, MaxCatalogFileBytes+1))
	if err != nil || len(data) > MaxCatalogFileBytes {
		return nil, fmt.Errorf("unreadable/oversize catalog file")
	}
	after, err := f.Stat()
	entry, endErr := root.Lstat(name)
	if err != nil || endErr != nil || !os.SameFile(opened, entry) || after.Size() != opened.Size() || !after.ModTime().Equal(opened.ModTime()) || int64(len(data)) != after.Size() {
		return nil, fmt.Errorf("catalog file changed during capture")
	}
	return data, nil
}
