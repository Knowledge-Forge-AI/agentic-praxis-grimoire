package envsnap

import (
	"fmt"
	"io"
	"os"
	"path/filepath"
	"reflect"
	"strings"
)

func requireAbsoluteClean(path string) error {
	if path == "" || !filepath.IsAbs(path) || filepath.Clean(path) != path {
		return fmt.Errorf("%w: path must be absolute and clean", ErrUnsafePath)
	}
	if filepath.VolumeName(path) == "" && path == string(filepath.Separator) {
		return fmt.Errorf("%w: root directory is not an acceptable storage root", ErrUnsafePath)
	}
	return nil
}

func validateNoSymlinkChain(path string, allowMissing bool) error {
	volume := filepath.VolumeName(path)
	remainder := strings.TrimPrefix(path, volume)
	absolute := filepath.IsAbs(remainder)
	if absolute {
		remainder = strings.TrimPrefix(remainder, string(filepath.Separator))
	}
	current := volume
	if absolute {
		current += string(filepath.Separator)
	}
	parts := strings.Split(remainder, string(filepath.Separator))
	for index, part := range parts {
		if part == "" {
			continue
		}
		current = filepath.Join(current, part)
		info, err := os.Lstat(current)
		if err != nil {
			if os.IsNotExist(err) && allowMissing {
				return nil
			}
			return fmt.Errorf("%w: path component", ErrUnsafePath)
		}
		if info.Mode()&os.ModeSymlink == 0 {
			continue
		}
		// A system-owned alias such as macOS /var -> /private/var is
		// accepted for portability. Any caller-owned symlink, including the
		// requested leaf, is refused.
		leaf := index == len(parts)-1
		uid, ownerKnown := fileUID(info)
		if leaf || !ownerKnown || uid == currentProcessUID() {
			return fmt.Errorf("%w: symlink path component", ErrUnsafePath)
		}
	}
	return nil
}

func ensurePrivateDirectory(path string) error {
	if err := validateNoSymlinkChain(path, true); err != nil {
		return err
	}
	if err := os.MkdirAll(path, 0o700); err != nil {
		return fmt.Errorf("%w: create directory", ErrUnsafePath)
	}
	if err := validateNoSymlinkChain(path, false); err != nil {
		return err
	}
	info, err := os.Lstat(path)
	if err != nil || !info.IsDir() || info.Mode()&os.ModeSymlink != 0 {
		return fmt.Errorf("%w: directory type", ErrUnsafePath)
	}
	if err := validateOwner(info); err != nil {
		return err
	}
	if info.Mode().Perm() != 0o700 {
		if err := os.Chmod(path, 0o700); err != nil {
			return fmt.Errorf("%w: directory mode", ErrUnsafePath)
		}
		info, err = os.Lstat(path)
		if err != nil || info.Mode().Perm() != 0o700 {
			return fmt.Errorf("%w: directory mode", ErrUnsafePath)
		}
	}
	return nil
}

func requirePrivateDirectory(path string) error {
	if err := requireAbsoluteClean(path); err != nil {
		return err
	}
	if err := validateNoSymlinkChain(path, false); err != nil {
		return err
	}
	info, err := os.Lstat(path)
	if err != nil {
		return fmt.Errorf("%w: directory is missing", ErrUnsafePath)
	}
	if !info.IsDir() || info.Mode()&os.ModeSymlink != 0 {
		return fmt.Errorf("%w: directory type", ErrUnsafePath)
	}
	if err := validateOwner(info); err != nil {
		return err
	}
	if info.Mode().Perm() != 0o700 {
		return fmt.Errorf("%w: directory mode", ErrUnsafePath)
	}
	return nil
}

func validateOwner(info os.FileInfo) error {
	if !ownerChecksAvailable() {
		return fmt.Errorf("%w: owner checks unavailable", ErrUnsafePath)
	}
	uid, ok := fileUID(info)
	if !ok || uid != currentProcessUID() {
		return fmt.Errorf("%w: owner", ErrUnsafePath)
	}
	return nil
}

func fileUID(info os.FileInfo) (uint32, bool) {
	if info == nil || info.Sys() == nil {
		return 0, false
	}
	value := reflect.ValueOf(info.Sys())
	if value.Kind() == reflect.Pointer {
		if value.IsNil() {
			return 0, false
		}
		value = value.Elem()
	}
	if value.Kind() != reflect.Struct {
		return 0, false
	}
	field := value.FieldByName("Uid")
	if !field.IsValid() {
		return 0, false
	}
	switch field.Kind() {
	case reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64:
		return uint32(field.Uint()), true
	default:
		return 0, false
	}
}

func fileNlink(info os.FileInfo) (uint64, bool) {
	if info == nil || info.Sys() == nil {
		return 0, false
	}
	value := reflect.ValueOf(info.Sys())
	if value.Kind() == reflect.Pointer {
		if value.IsNil() {
			return 0, false
		}
		value = value.Elem()
	}
	if value.Kind() != reflect.Struct {
		return 0, false
	}
	for _, name := range []string{"Nlink", "Nlink64"} {
		field := value.FieldByName(name)
		if !field.IsValid() {
			continue
		}
		switch field.Kind() {
		case reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64:
			return field.Uint(), true
		}
	}
	return 0, false
}

func requireDirectPrivateFile(path string, maxSize int64) (os.FileInfo, error) {
	info, err := os.Lstat(path)
	if err != nil {
		return nil, err
	}
	if info.Mode()&os.ModeSymlink != 0 || !info.Mode().IsRegular() {
		return nil, fmt.Errorf("%w: file type", ErrUnsafePath)
	}
	if nlink, ok := fileNlink(info); !ok || nlink != 1 {
		return nil, fmt.Errorf("%w: file link count", ErrUnsafePath)
	}
	if err := validateOwner(info); err != nil {
		return nil, err
	}
	if info.Mode().Perm() != 0o600 {
		return nil, fmt.Errorf("%w: file mode", ErrUnsafePath)
	}
	if maxSize > 0 && info.Size() > maxSize {
		return nil, fmt.Errorf("%w: file size", ErrUnsafePath)
	}
	return info, nil
}

func readPrivateFileStable(path string, maxSize int64) ([]byte, os.FileInfo, error) {
	initial, err := os.Lstat(path)
	if err != nil {
		return nil, nil, err
	}
	if _, err := requireDirectPrivateFileInfo(initial, maxSize); err != nil {
		return nil, nil, err
	}
	file, err := os.Open(path)
	if err != nil {
		return nil, nil, fmt.Errorf("%w: open private file", ErrUnsafePath)
	}
	defer file.Close()
	opened, err := file.Stat()
	if err != nil || !sameFile(initial, opened) {
		return nil, nil, fmt.Errorf("%w: private file changed during open", ErrUnsafePath)
	}
	data, err := io.ReadAll(io.LimitReader(file, maxSize+1))
	if err != nil {
		return nil, nil, fmt.Errorf("%w: read private file", ErrUnsafePath)
	}
	if int64(len(data)) > maxSize {
		return nil, nil, fmt.Errorf("%w: private file size", ErrUnsafePath)
	}
	final, err := os.Lstat(path)
	if err != nil || !sameFile(initial, final) {
		return nil, nil, fmt.Errorf("%w: private file changed during read", ErrUnsafePath)
	}
	if _, err := requireDirectPrivateFileInfo(final, maxSize); err != nil {
		return nil, nil, err
	}
	return data, initial, nil
}

func sameFile(a, b os.FileInfo) bool {
	if a == nil || b == nil {
		return false
	}
	return os.SameFile(a, b)
}
