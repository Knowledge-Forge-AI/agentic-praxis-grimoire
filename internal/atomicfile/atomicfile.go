// Package atomicfile owns APG's private outbox lock, transaction, and atomic
// replacement primitives. It is internal implementation, not public API.
package atomicfile

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"reflect"
	"strconv"
	"strings"
	"syscall"
	"time"
)

// ErrUnsafe identifies an unsafe filesystem shape or identity.
var ErrUnsafe = errors.New("unsafe atomic report path")

// ErrConflict identifies a live lock or unresolved transaction.
var ErrConflict = errors.New("atomic report publication conflict")

// Paths contains the canonical private paths for one phase outbox.
type Paths struct {
	Directory   string
	Lock        string
	Transaction string
	Phase       string
}

// Prepare creates and validates owner-only outbox, project, and phase directories.
func Prepare(root, project, phase string) (Paths, error) {
	if !filepath.IsAbs(root) || filepath.Clean(root) != root {
		return Paths{}, fmt.Errorf("%w: outbox root must be absolute and clean", ErrUnsafe)
	}
	projectDirectory := filepath.Join(root, project)
	phaseDirectory := filepath.Join(projectDirectory, phase)
	for _, directory := range []string{root, projectDirectory, phaseDirectory} {
		if metadata, err := os.Lstat(directory); err == nil && metadata.Mode()&os.ModeSymlink != 0 {
			return Paths{}, fmt.Errorf("%w: report directory link", ErrUnsafe)
		}
		if err := os.MkdirAll(directory, 0o700); err != nil {
			return Paths{}, fmt.Errorf("%w: report directory creation", ErrUnsafe)
		}
		if err := os.Chmod(directory, 0o700); err != nil {
			return Paths{}, fmt.Errorf("%w: report directory mode", ErrUnsafe)
		}
		if err := validateDirectory(directory); err != nil {
			return Paths{}, err
		}
	}
	return Paths{Directory: phaseDirectory, Lock: filepath.Join(phaseDirectory, ".phase.lock"), Transaction: filepath.Join(phaseDirectory, ".phase.transaction"), Phase: phase}, nil
}

// WithLock acquires the canonical phase lock, runs action, and releases only
// the exact lock and owner token created by this invocation.
func WithLock(ctx context.Context, paths Paths, action func() error) error {
	lock, err := acquire(ctx, paths)
	if err != nil {
		return err
	}
	defer lock.release()
	return action()
}

// EnsureNoTransaction refuses unresolved private transaction state.
func EnsureNoTransaction(paths Paths) error {
	metadata, err := os.Lstat(paths.Transaction)
	if os.IsNotExist(err) {
		return nil
	}
	if err != nil || validatePrivateFile(paths.Transaction, metadata) != nil {
		return fmt.Errorf("%w: transaction marker", ErrUnsafe)
	}
	return fmt.Errorf("%w: unresolved transaction marker", ErrConflict)
}

// ReadPrivate reads an existing private direct regular file. Missing is not an error.
func ReadPrivate(path string) ([]byte, bool, error) {
	metadata, err := os.Lstat(path)
	if os.IsNotExist(err) {
		return nil, false, nil
	}
	if err != nil {
		return nil, false, fmt.Errorf("%w: report file metadata", ErrUnsafe)
	}
	if err := validatePrivateFile(path, metadata); err != nil {
		return nil, false, err
	}
	file, err := os.OpenFile(path, os.O_RDONLY|syscall.O_NOFOLLOW, 0)
	if err != nil {
		return nil, false, fmt.Errorf("%w: report file open", ErrUnsafe)
	}
	defer file.Close()
	opened, err := file.Stat()
	if err != nil || !sameObject(metadata, opened) {
		return nil, false, fmt.Errorf("%w: report file identity", ErrUnsafe)
	}
	content, err := io.ReadAll(io.LimitReader(file, 128<<20))
	if err != nil {
		return nil, false, fmt.Errorf("%w: report file read", ErrUnsafe)
	}
	return content, true, nil
}

// Replace transactionally publishes content at target and removes stale names.
// All names must be basenames beneath paths.Directory and the phase lock must
// already be held by the caller.
func Replace(ctx context.Context, paths Paths, target string, stale []string, content []byte) error {
	if err := ctx.Err(); err != nil {
		return err
	}
	if err := EnsureNoTransaction(paths); err != nil {
		return err
	}
	for _, name := range append([]string{target}, stale...) {
		if filepath.Base(name) != name || name == "." || name == ".." {
			return fmt.Errorf("%w: transaction artifact name", ErrUnsafe)
		}
	}
	token, err := randomToken()
	if err != nil {
		return fmt.Errorf("%w: transaction identity", ErrUnsafe)
	}
	marker := strings.Join([]string{
		"agent-report-transaction-v1",
		"phase: " + paths.Phase,
		"target: " + target,
		"stale: " + strings.Join(stale, ","),
		"token: " + token,
		"",
	}, "\n")
	markerFile, err := os.OpenFile(paths.Transaction, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o600)
	if err != nil {
		if os.IsExist(err) {
			return fmt.Errorf("%w: transaction marker", ErrConflict)
		}
		return fmt.Errorf("%w: transaction marker", ErrUnsafe)
	}
	markerInfo, markerStatErr := markerFile.Stat()
	if markerStatErr != nil || writeAndSync(markerFile, []byte(marker)) != nil || markerFile.Close() != nil {
		_ = markerFile.Close()
		_ = os.Remove(paths.Transaction)
		return fmt.Errorf("%w: transaction marker write", ErrUnsafe)
	}
	_ = syncDirectory(paths.Directory)
	if err := ctx.Err(); err != nil {
		return err
	}
	if err := atomicReplace(paths.Directory, target, content); err != nil {
		return err
	}
	for _, name := range stale {
		if name == target {
			continue
		}
		if err := removePrivate(filepath.Join(paths.Directory, name)); err != nil {
			return err
		}
	}
	current, err := os.Lstat(paths.Transaction)
	if err != nil || !sameObject(markerInfo, current) {
		return fmt.Errorf("%w: transaction marker identity", ErrUnsafe)
	}
	if err := os.Remove(paths.Transaction); err != nil {
		return fmt.Errorf("%w: transaction marker removal", ErrUnsafe)
	}
	_ = syncDirectory(paths.Directory)
	return nil
}

// Recover completes stale-primary cleanup for a published target or rolls back
// a pre-publication marker. It returns false when no transaction exists.
func Recover(ctx context.Context, paths Paths, allowed []string) (bool, error) {
	recovered := false
	err := WithLock(ctx, paths, func() error {
		metadata, err := os.Lstat(paths.Transaction)
		if os.IsNotExist(err) {
			return nil
		}
		if err != nil || validatePrivateFile(paths.Transaction, metadata) != nil {
			return fmt.Errorf("%w: transaction marker", ErrUnsafe)
		}
		raw, _, err := ReadPrivate(paths.Transaction)
		if err != nil {
			return err
		}
		lines := strings.Split(strings.TrimSuffix(string(raw), "\n"), "\n")
		if len(lines) < 5 || lines[0] != "agent-report-transaction-v1" {
			return fmt.Errorf("%w: transaction marker format", ErrUnsafe)
		}
		fields := map[string]string{}
		for _, line := range lines[1:] {
			parts := strings.SplitN(line, ": ", 2)
			if len(parts) == 2 {
				fields[parts[0]] = parts[1]
			}
		}
		allowedSet := map[string]bool{}
		for _, name := range allowed {
			allowedSet[name] = true
		}
		target := fields["target"]
		if fields["phase"] != paths.Phase || !allowedSet[target] {
			return fmt.Errorf("%w: transaction marker identity", ErrUnsafe)
		}
		stale := []string{}
		if fields["stale"] != "" {
			stale = strings.Split(fields["stale"], ",")
		}
		for _, name := range stale {
			if !allowedSet[name] {
				return fmt.Errorf("%w: transaction marker stale set", ErrUnsafe)
			}
		}
		_, targetExists, readErr := ReadPrivate(filepath.Join(paths.Directory, target))
		if readErr != nil {
			return readErr
		}
		if targetExists {
			for _, name := range stale {
				if name != target {
					if err := removePrivate(filepath.Join(paths.Directory, name)); err != nil {
						return err
					}
				}
			}
		}
		current, err := os.Lstat(paths.Transaction)
		if err != nil || !sameObject(metadata, current) {
			return fmt.Errorf("%w: transaction marker identity", ErrUnsafe)
		}
		if err := os.Remove(paths.Transaction); err != nil {
			return fmt.Errorf("%w: transaction marker removal", ErrUnsafe)
		}
		_ = syncDirectory(paths.Directory)
		recovered = true
		return nil
	})
	return recovered, err
}

type heldLock struct {
	path, token          string
	directoryID, ownerID objectID
}

func acquire(ctx context.Context, paths Paths) (*heldLock, error) {
	for attempt := 0; attempt < 400; attempt++ {
		if err := ctx.Err(); err != nil {
			return nil, err
		}
		err := os.Mkdir(paths.Lock, 0o700)
		if err == nil {
			metadata, statErr := os.Lstat(paths.Lock)
			if statErr != nil || !metadata.IsDir() || metadata.Mode()&os.ModeSymlink != 0 {
				return nil, fmt.Errorf("%w: lock directory", ErrUnsafe)
			}
			token, tokenErr := randomToken()
			if tokenErr != nil {
				_ = os.Remove(paths.Lock)
				return nil, fmt.Errorf("%w: lock identity", ErrUnsafe)
			}
			token = strconv.Itoa(os.Getpid()) + "-" + token + "-" + paths.Phase
			ownerPath := filepath.Join(paths.Lock, "owner")
			owner, ownerErr := os.OpenFile(ownerPath, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o600)
			if ownerErr != nil {
				_ = os.RemoveAll(paths.Lock)
				return nil, fmt.Errorf("%w: lock owner", ErrUnsafe)
			}
			ownerInfo, ownerStatErr := owner.Stat()
			writeErr := writeAndSync(owner, []byte(token+"\n"))
			closeErr := owner.Close()
			if ownerStatErr != nil || writeErr != nil || closeErr != nil {
				_ = os.Remove(ownerPath)
				_ = os.Remove(paths.Lock)
				return nil, fmt.Errorf("%w: lock owner", ErrUnsafe)
			}
			return &heldLock{path: paths.Lock, token: token, directoryID: objectIdentity(metadata), ownerID: objectIdentity(ownerInfo)}, nil
		}
		if !os.IsExist(err) {
			return nil, fmt.Errorf("%w: lock directory", ErrUnsafe)
		}
		if recovered, recoverErr := recoverStaleLock(paths.Lock, paths.Directory); recoverErr != nil {
			return nil, recoverErr
		} else if recovered {
			continue
		}
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		case <-time.After(10 * time.Millisecond):
		}
	}
	return nil, fmt.Errorf("%w: report append is already active", ErrConflict)
}

func recoverStaleLock(path, parent string) (bool, error) {
	directory, err := os.Lstat(path)
	if err != nil || !directory.IsDir() || directory.Mode()&os.ModeSymlink != 0 {
		return false, fmt.Errorf("%w: lock directory", ErrUnsafe)
	}
	ownerPath := filepath.Join(path, "owner")
	owner, err := os.Lstat(ownerPath)
	if os.IsNotExist(err) {
		if time.Since(directory.ModTime()) < time.Second {
			return false, nil
		}
		entries, readErr := os.ReadDir(path)
		if readErr != nil || len(entries) != 0 {
			return false, nil
		}
		current, statErr := os.Lstat(path)
		if statErr != nil || !sameObject(directory, current) {
			return false, fmt.Errorf("%w: lock identity changed", ErrUnsafe)
		}
		if err := os.Remove(path); err != nil {
			return false, fmt.Errorf("%w: stale lock removal", ErrUnsafe)
		}
		_ = syncDirectory(parent)
		return true, nil
	}
	if err != nil || validatePrivateFile(ownerPath, owner) != nil {
		return false, fmt.Errorf("%w: lock owner", ErrUnsafe)
	}
	raw, _, err := ReadPrivate(ownerPath)
	if err != nil {
		return false, err
	}
	pidText := strings.SplitN(strings.TrimSuffix(string(raw), "\n"), "-", 2)[0]
	pid, err := strconv.Atoi(pidText)
	if err != nil || pid <= 0 {
		return false, fmt.Errorf("%w: lock owner identity", ErrUnsafe)
	}
	if processAlive(pid) {
		return false, nil
	}
	currentDirectory, directoryErr := os.Lstat(path)
	currentOwner, ownerErr := os.Lstat(ownerPath)
	if directoryErr != nil || ownerErr != nil || !sameObject(directory, currentDirectory) || !sameObject(owner, currentOwner) {
		return false, fmt.Errorf("%w: lock ownership changed", ErrUnsafe)
	}
	if err := os.Remove(ownerPath); err != nil {
		return false, fmt.Errorf("%w: stale lock owner removal", ErrUnsafe)
	}
	if err := os.Remove(path); err != nil {
		return false, fmt.Errorf("%w: stale lock removal", ErrUnsafe)
	}
	_ = syncDirectory(parent)
	return true, nil
}

func (lock *heldLock) release() {
	metadata, err := os.Lstat(lock.path)
	if err != nil || objectIdentity(metadata) != lock.directoryID || !metadata.IsDir() || metadata.Mode()&os.ModeSymlink != 0 {
		return
	}
	ownerPath := filepath.Join(lock.path, "owner")
	owner, err := os.Lstat(ownerPath)
	if err != nil || objectIdentity(owner) != lock.ownerID {
		return
	}
	raw, _, err := ReadPrivate(ownerPath)
	if err != nil || strings.TrimSuffix(string(raw), "\n") != lock.token {
		return
	}
	_ = os.Remove(ownerPath)
	_ = os.Remove(lock.path)
}

func atomicReplace(directory, target string, content []byte) error {
	temporary, err := os.CreateTemp(directory, "."+strings.TrimSuffix(target, ".txt")+".")
	if err != nil {
		return fmt.Errorf("%w: replacement creation", ErrUnsafe)
	}
	temporaryName := temporary.Name()
	remove := true
	defer func() {
		_ = temporary.Close()
		if remove {
			_ = os.Remove(temporaryName)
		}
	}()
	if err := temporary.Chmod(0o600); err != nil || writeAndSync(temporary, content) != nil || temporary.Close() != nil {
		return fmt.Errorf("%w: replacement write", ErrUnsafe)
	}
	if err := os.Rename(temporaryName, filepath.Join(directory, target)); err != nil {
		return fmt.Errorf("%w: replacement publish", ErrUnsafe)
	}
	remove = false
	if err := os.Chmod(filepath.Join(directory, target), 0o600); err != nil {
		return fmt.Errorf("%w: replacement mode", ErrUnsafe)
	}
	_ = syncDirectory(directory)
	return nil
}

func removePrivate(path string) error {
	metadata, err := os.Lstat(path)
	if os.IsNotExist(err) {
		return nil
	}
	if err != nil || validatePrivateFile(path, metadata) != nil {
		return fmt.Errorf("%w: stale report artifact", ErrUnsafe)
	}
	if err := os.Remove(path); err != nil {
		return fmt.Errorf("%w: stale report removal", ErrUnsafe)
	}
	return nil
}

func validateDirectory(path string) error {
	metadata, err := os.Lstat(path)
	if err != nil || !metadata.IsDir() || metadata.Mode()&os.ModeSymlink != 0 || metadata.Mode().Perm() != 0o700 || ownerID(metadata) != int64(os.Getuid()) {
		return fmt.Errorf("%w: private directory", ErrUnsafe)
	}
	return nil
}

func validatePrivateFile(path string, metadata os.FileInfo) error {
	if !metadata.Mode().IsRegular() || metadata.Mode()&os.ModeSymlink != 0 || metadata.Mode().Perm() != 0o600 || ownerID(metadata) != int64(os.Getuid()) || linkCount(metadata) != 1 {
		return fmt.Errorf("%w: private regular file", ErrUnsafe)
	}
	return nil
}

type objectID struct{ dev, ino int64 }

func objectIdentity(info os.FileInfo) objectID {
	value := reflect.Indirect(reflect.ValueOf(info.Sys()))
	return objectID{fieldInteger(value, "Dev"), fieldInteger(value, "Ino")}
}

func sameObject(left, right os.FileInfo) bool { return objectIdentity(left) == objectIdentity(right) }
func ownerID(info os.FileInfo) int64 {
	return fieldInteger(reflect.Indirect(reflect.ValueOf(info.Sys())), "Uid")
}
func linkCount(info os.FileInfo) int64 {
	return fieldInteger(reflect.Indirect(reflect.ValueOf(info.Sys())), "Nlink")
}

func fieldInteger(value reflect.Value, name string) int64 {
	field := value.FieldByName(name)
	if !field.IsValid() {
		return -1
	}
	switch field.Kind() {
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		return field.Int()
	default:
		return int64(field.Uint())
	}
}

func writeAndSync(file *os.File, content []byte) error {
	if _, err := file.Write(content); err != nil {
		return err
	}
	return file.Sync()
}

func syncDirectory(path string) error {
	directory, err := os.Open(path)
	if err != nil {
		return err
	}
	defer directory.Close()
	return directory.Sync()
}

func randomToken() (string, error) {
	value := make([]byte, 8)
	if _, err := rand.Read(value); err != nil {
		return "", err
	}
	return hex.EncodeToString(value), nil
}

func processAlive(pid int) bool {
	err := syscall.Kill(pid, 0)
	return err == nil || err == syscall.EPERM
}
