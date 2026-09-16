package hotspot

import (
	"errors"
	"io"
	"os"
	"path/filepath"
)

// The supported local store is direct regular files under direct directories.
// Bound directory observation as well as object reads; never follow indirection.
func validateObjectStorage(root string) error {
	count := 0
	var visit func(string, int) error
	visit = func(dir string, depth int) error {
		if depth > 3 {
			return rootSafety("unsupported object store depth")
		}
		f, err := os.Open(dir)
		if err != nil {
			return rootSafety("object store is unreadable")
		}
		entries, err := f.ReadDir(maxTreeEntries - count + 1)
		_ = f.Close()
		if err != nil && !errors.Is(err, io.EOF) {
			return rootSafety("object store observation failed")
		}
		count += len(entries)
		if count > maxTreeEntries {
			return limitExceeded("object store entries exceed 100000")
		}
		for _, e := range entries {
			info, err := e.Info()
			if err != nil {
				return rootSafety("object entry unreadable")
			}
			if info.Mode()&os.ModeSymlink != 0 {
				return rootSafety("object store symlinks are unsupported")
			}
			if info.IsDir() {
				if err := visit(filepath.Join(dir, e.Name()), depth+1); err != nil {
					return err
				}
			} else if !info.Mode().IsRegular() {
				return rootSafety("non-regular object store entry")
			}
		}
		return nil
	}
	return visit(root, 0)
}
