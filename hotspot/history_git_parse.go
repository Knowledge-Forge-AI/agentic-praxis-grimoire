package hotspot

import (
	"errors"
	"fmt"
	"os/exec"
	"path/filepath"
	"strings"
	"unicode"
	"unicode/utf8"
)

func isValidOID(oid string, format string) bool {
	expectedLen := 40
	if format == "sha256" {
		expectedLen = 64
	} else if format != "sha1" {
		return false
	}
	if len(oid) != expectedLen {
		return false
	}
	for i := 0; i < len(oid); i++ {
		b := oid[i]
		if !((b >= '0' && b <= '9') || (b >= 'a' && b <= 'f')) {
			return false
		}
	}
	return true
}

func isZeroOID(oid string, format string) bool {
	expectedLen := 40
	if format == "sha256" {
		expectedLen = 64
	} else if format != "sha1" {
		return false
	}
	if len(oid) != expectedLen {
		return false
	}
	for i := 0; i < len(oid); i++ {
		if oid[i] != '0' {
			return false
		}
	}
	return true
}

func validateGitPath(path string) error {
	if path == "" {
		return errors.New("empty path")
	}
	if !utf8.ValidString(path) {
		return errors.New("path is not valid UTF-8")
	}
	for _, r := range path {
		if r < 0x20 || r == 0x7f || (r >= 0x80 && r <= 0x9f) || unicode.IsControl(r) {
			return fmt.Errorf("path contains control character %U", r)
		}
	}
	if strings.Contains(path, "\\") {
		return errors.New("path contains backslash")
	}
	if strings.HasPrefix(path, "/") || filepath.IsAbs(path) {
		return errors.New("path is absolute")
	}
	if path == "." || path == ".." ||
		strings.HasPrefix(path, "../") || strings.HasPrefix(path, "./") ||
		strings.HasSuffix(path, "/..") || strings.HasSuffix(path, "/.") ||
		strings.Contains(path, "/../") || strings.Contains(path, "/./") ||
		strings.Contains(path, "//") {
		return errors.New("path contains directory traversal or redundant slashes")
	}
	if filepath.Clean(path) != path || filepath.ToSlash(path) != path {
		return errors.New("path is not clean root-relative path")
	}
	if path == ".git" || strings.HasPrefix(path, ".git/") || strings.Contains(path, "/.git/") || strings.HasSuffix(path, "/.git") {
		return errors.New("path targets .git directory")
	}
	return nil
}

func isSupportedGitMode(mode string) bool {
	return mode == "000000" || mode == "100644" || mode == "100755"
}

func isGitConfigNotFound(err error) bool {
	var exitErr *exec.ExitError
	if errors.As(err, &exitErr) {
		return exitErr.ExitCode() == 1
	}
	return false
}
