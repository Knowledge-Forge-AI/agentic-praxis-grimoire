package response

import (
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"sort"
)

// PhaseDirectory creates and validates the private response directory tree.
func PhaseDirectory(outboxRoot, project, phase string) (string, error) {
	if err := validateAbsoluteClean(outboxRoot, "outbox root"); err != nil {
		return "", err
	}
	if err := validateComponent(project, "project"); err != nil {
		return "", err
	}
	if err := validateComponent(phase, "phase"); err != nil {
		return "", err
	}
	root := filepath.Clean(outboxRoot)
	projectDirectory := filepath.Join(root, project)
	phaseDirectory := filepath.Join(projectDirectory, phase)
	if err := ensureDirectoryTree(root); err != nil {
		return "", err
	}
	if err := ensureDirectory(projectDirectory, true); err != nil {
		return "", err
	}
	if err := ensureDirectory(phaseDirectory, true); err != nil {
		return "", err
	}
	return phaseDirectory, nil
}

// ListReservations returns valid directly-owned reservation paths in one
// phase directory, sorted by filename.
func ListReservations(phaseDirectory string) ([]string, error) {
	metadata, err := os.Lstat(phaseDirectory)
	if os.IsNotExist(err) {
		return []string{}, nil
	}
	if err != nil {
		return nil, unsafeError("could not inspect response phase directory")
	}
	if err := validateDirectoryMetadata(metadata, true); err != nil {
		return nil, unsafeError("response phase directory is unsafe")
	}
	phase := filepath.Base(filepath.Clean(phaseDirectory))
	if err := validateComponent(phase, "phase"); err != nil {
		return nil, err
	}
	entries, err := os.ReadDir(phaseDirectory)
	if err != nil {
		return nil, wrappedError(ErrUnsafe, "could not inspect response reservations", err)
	}
	result := make([]string, 0)
	for _, entry := range entries {
		match := reservationPattern.FindStringSubmatch(entry.Name())
		if match == nil || match[1] != phase {
			continue
		}
		path := filepath.Join(phaseDirectory, entry.Name())
		info, statErr := os.Lstat(path)
		if statErr != nil {
			return nil, wrappedError(ErrUnsafe, "response reservation artifact changed", statErr)
		}
		if err := validatePrivateFileMetadata(info, false); err != nil {
			return nil, unsafeError("response reservation artifact is unsafe")
		}
		result = append(result, path)
	}
	sort.Strings(result)
	return result, nil
}

// ListReservationArtifacts is a compatibility alias for ListReservations.
func ListReservationArtifacts(phaseDirectory string) ([]string, error) {
	return ListReservations(phaseDirectory)
}

// CleanReservation removes one exact, directly-owned reservation artifact.
func CleanReservation(path, outboxRoot, project, phase string) error {
	if err := validateAbsoluteClean(outboxRoot, "outbox root"); err != nil {
		return err
	}
	if err := validateComponent(project, "project"); err != nil {
		return err
	}
	if err := validateComponent(phase, "phase"); err != nil {
		return err
	}
	cleanPath := filepath.Clean(path)
	match := reservationPattern.FindStringSubmatch(filepath.Base(cleanPath))
	if match == nil {
		return usageError("path is not a response reservation artifact")
	}
	expectedDirectory := filepath.Join(filepath.Clean(outboxRoot), project, phase)
	if filepath.Dir(cleanPath) != expectedDirectory || match[1] != phase {
		return usageError("reservation path does not belong to its phase")
	}
	metadata, err := os.Lstat(cleanPath)
	if os.IsNotExist(err) {
		return nil
	}
	if err != nil {
		return wrappedError(ErrUnsafe, "could not inspect response reservation", err)
	}
	if err := ensureDirectory(filepath.Clean(outboxRoot), false); err != nil {
		return err
	}
	if err := ensureDirectory(filepath.Dir(expectedDirectory), true); err != nil {
		return err
	}
	if err := ensureDirectory(expectedDirectory, true); err != nil {
		return err
	}
	if err := validatePrivateFileMetadata(metadata, false); err != nil {
		return unsafeError("response reservation must be a regular file")
	}
	for _, directory := range []string{filepath.Clean(outboxRoot), filepath.Dir(expectedDirectory), expectedDirectory} {
		before, statErr := os.Lstat(directory)
		if statErr != nil || before.Mode()&os.ModeSymlink != 0 || !before.IsDir() {
			return unsafeError("response reservation ancestry is unsafe")
		}
	}
	if err := removeOwned(cleanPath, metadata); err != nil {
		return err
	}
	return syncDirectory(expectedDirectory)
}

// CleanReservationArtifact is a compatibility alias for CleanReservation.
func CleanReservationArtifact(path, outboxRoot, project, phase string) error {
	return CleanReservation(path, outboxRoot, project, phase)
}

func ensureDirectoryTree(path string) error {
	clean := filepath.Clean(path)
	if metadata, err := os.Lstat(clean); os.IsNotExist(err) {
		if mkdirErr := os.MkdirAll(clean, 0o700); mkdirErr != nil {
			return wrappedError(ErrUnsafe, "could not create response directory", mkdirErr)
		}
	} else if err != nil {
		return wrappedError(ErrUnsafe, "could not inspect response directory", err)
	} else if metadata.Mode()&os.ModeSymlink != 0 {
		return unsafeError("response directory is unsafe")
	}
	return ensureDirectory(clean, false)
}

func ensureDirectory(path string, private bool) error {
	metadata, err := os.Lstat(path)
	if os.IsNotExist(err) {
		if err := os.Mkdir(path, 0o700); err != nil {
			if !os.IsExist(err) {
				return wrappedError(ErrUnsafe, "could not create response directory", err)
			}
		}
		metadata, err = os.Lstat(path)
	}
	if err != nil {
		return wrappedError(ErrUnsafe, "could not inspect response directory", err)
	}
	if err := validateDirectoryMetadata(metadata, private); err != nil {
		return unsafeError("response directory is unsafe")
	}
	return nil
}

func validateDirectoryMetadata(metadata os.FileInfo, private bool) error {
	if metadata == nil || metadata.Mode()&os.ModeSymlink != 0 || !metadata.IsDir() || ownerID(metadata) != int64(os.Getuid()) {
		return ErrUnsafe
	}
	if private && metadata.Mode().Perm() != 0o700 {
		return ErrUnsafe
	}
	return nil
}

func validatePrivateFileMetadata(metadata os.FileInfo, requireSingleLink bool) error {
	if metadata == nil || metadata.Mode()&os.ModeSymlink != 0 || !metadata.Mode().IsRegular() || metadata.Mode().Perm() != 0o600 || ownerID(metadata) != int64(os.Getuid()) {
		return ErrUnsafe
	}
	if requireSingleLink && linkCount(metadata) != 1 {
		return ErrUnsafe
	}
	return nil
}

func validateAbsoluteClean(path, label string) error {
	if path == "" || !filepath.IsAbs(path) || filepath.Clean(path) != path {
		return usageError("%s must be absolute and clean", label)
	}
	return nil
}

func validateComponent(value, label string) error {
	if value == "" || len(value) > MaxComponentLength || value == "." || value == ".." || componentPattern.FindString(value) == "" {
		return usageError("%s is unsafe", label)
	}
	return nil
}

func responsePath(phaseDirectory, phase string, number int) string {
	return filepath.Join(phaseDirectory, fmt.Sprintf("%s.%03d.response.md", phase, number))
}

func reservationPath(phaseDirectory, phase string, number int, token string) string {
	return filepath.Join(phaseDirectory, fmt.Sprintf(".%s.%03d.response.md.reservation.%s", phase, number, token))
}

func lexists(path string) (bool, error) {
	_, err := os.Lstat(path)
	if err == nil {
		return true, nil
	}
	if os.IsNotExist(err) {
		return false, nil
	}
	return false, wrappedError(ErrUnsafe, "could not inspect response path", err)
}

func removeOwned(path string, expected os.FileInfo) error {
	if expected == nil {
		return nil
	}
	current, err := os.Lstat(path)
	if os.IsNotExist(err) {
		return nil
	}
	if err != nil {
		return wrappedError(ErrUnsafe, "could not inspect response temporary artifact", err)
	}
	if current.Mode()&os.ModeSymlink != 0 || !current.Mode().IsRegular() || !sameObject(expected, current) {
		return unsafeError("response temporary artifact changed during cleanup")
	}
	if err := os.Remove(path); err != nil {
		return wrappedError(ErrUnsafe, "could not remove response temporary artifact", err)
	}
	return nil
}

func syncDirectory(path string) error {
	before, err := os.Lstat(path)
	if err != nil || before.Mode()&os.ModeSymlink != 0 || !before.IsDir() {
		return errors.New("response directory is unsafe")
	}
	directory, err := os.Open(path)
	if err != nil {
		return err
	}
	opened, statErr := directory.Stat()
	if statErr != nil || !sameObject(before, opened) {
		_ = directory.Close()
		return errors.New("response directory identity changed")
	}
	syncErr := directory.Sync()
	closeErr := directory.Close()
	if syncErr != nil {
		return syncErr
	}
	if closeErr != nil {
		return closeErr
	}
	after, err := os.Lstat(path)
	if err != nil || !sameObject(before, after) {
		return errors.New("response directory identity changed")
	}
	return nil
}

func writeAndSync(file *os.File, content []byte) (os.FileInfo, error) {
	if err := writeAll(file, content); err != nil {
		return nil, err
	}
	if err := file.Sync(); err != nil {
		return nil, err
	}
	info, err := file.Stat()
	if err != nil {
		return nil, err
	}
	if err := validatePrivateFileMetadata(info, true); err != nil {
		return nil, err
	}
	return info, nil
}

func writeAll(file *os.File, content []byte) error {
	for len(content) > 0 {
		written, err := file.Write(content)
		if err != nil {
			return err
		}
		if written <= 0 {
			return errors.New("response write made no progress")
		}
		content = content[written:]
	}
	return nil
}

func randomToken() (string, error) {
	value := make([]byte, 12)
	if _, err := rand.Read(value); err != nil {
		return "", err
	}
	return hex.EncodeToString(value), nil
}

func sameObject(left, right os.FileInfo) bool {
	return objectIdentity(left) == objectIdentity(right)
}

type objectID struct {
	device int64
	inode  int64
}

func objectIdentity(info os.FileInfo) objectID {
	if info == nil {
		return objectID{-1, -1}
	}
	value := reflect.Indirect(reflect.ValueOf(info.Sys()))
	return objectID{fieldInteger(value, "Dev"), fieldInteger(value, "Ino")}
}

func ownerID(info os.FileInfo) int64 {
	if info == nil {
		return -1
	}
	return fieldInteger(reflect.Indirect(reflect.ValueOf(info.Sys())), "Uid")
}

func linkCount(info os.FileInfo) int64 {
	if info == nil {
		return -1
	}
	return fieldInteger(reflect.Indirect(reflect.ValueOf(info.Sys())), "Nlink")
}

func fieldInteger(value reflect.Value, name string) int64 {
	if !value.IsValid() {
		return -1
	}
	field := value.FieldByName(name)
	if !field.IsValid() {
		return -1
	}
	switch field.Kind() {
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		return field.Int()
	case reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64, reflect.Uintptr:
		return int64(field.Uint())
	default:
		return -1
	}
}
