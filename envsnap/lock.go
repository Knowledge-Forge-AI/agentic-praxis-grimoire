package envsnap

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"time"
)

type lockOwner struct {
	PID          int       `json:"pid"`
	InvocationID string    `json:"invocation_id"`
	CreatedAt    time.Time `json:"created_at"`
}

type heldLock struct {
	path         string
	ownerPath    string
	invocationID string
	directory    os.FileInfo
	guard        *os.File
}

type staleLockCandidate struct {
	path      string
	directory os.FileInfo
	ownerPath string
	owner     os.FileInfo
	identity  lockOwner
}

func acquireLock(ctx context.Context, directory string, timeout time.Duration) (*heldLock, error) {
	if !ownerChecksAvailable() {
		return nil, fmt.Errorf("%w: owner checks unavailable", ErrUnsafePath)
	}
	lockPath := filepath.Join(directory, ".lock")
	deadline := time.Time{}
	if timeout > 0 {
		deadline = time.Now().Add(timeout)
	}
	for {
		if err := ctx.Err(); err != nil {
			return nil, err
		}
		guard, err := acquireGuard(directory)
		if err != nil {
			if !lockBusy(err) {
				return nil, err
			}
			if err := waitForLock(ctx, &deadline); err != nil {
				return nil, err
			}
			continue
		}
		if err := os.Mkdir(lockPath, 0o700); err == nil {
			held, createErr := createHeldLock(lockPath)
			if createErr != nil {
				_ = unlockExclusive(guard)
				_ = guard.Close()
				return nil, createErr
			}
			held.guard = guard
			return held, nil
		} else if !os.IsExist(err) {
			_ = unlockExclusive(guard)
			_ = guard.Close()
			return nil, fmt.Errorf("%w: create lock", ErrLockConflict)
		}
		candidate, staleErr := lockIsReclaimable(lockPath)
		if staleErr != nil {
			_ = unlockExclusive(guard)
			_ = guard.Close()
			return nil, staleErr
		}
		if candidate != nil {
			if err := reclaimLock(candidate); err == nil {
				_ = unlockExclusive(guard)
				_ = guard.Close()
				continue
			} else if !os.IsExist(err) {
				_ = unlockExclusive(guard)
				_ = guard.Close()
				return nil, err
			}
		}
		_ = unlockExclusive(guard)
		_ = guard.Close()
		if err := waitForLock(ctx, &deadline); err != nil {
			return nil, err
		}
	}
}

func acquireGuard(directory string) (*os.File, error) {
	path := filepath.Join(directory, ".lock.guard")
	before, beforeErr := os.Lstat(path)
	if beforeErr == nil && before.Mode()&os.ModeSymlink != 0 {
		return nil, fmt.Errorf("%w: lock guard symlink", ErrUnsafePath)
	}
	if beforeErr != nil && !os.IsNotExist(beforeErr) {
		return nil, fmt.Errorf("%w: lock guard state", ErrUnsafePath)
	}
	file, err := os.OpenFile(path, os.O_RDWR|os.O_CREATE, 0o600)
	if err != nil {
		return nil, fmt.Errorf("%w: lock guard", ErrLockConflict)
	}
	info, err := file.Stat()
	if err != nil || info.Mode().Perm() != 0o600 || fileNlinkValue(info) != 1 {
		_ = file.Close()
		return nil, fmt.Errorf("%w: lock guard state", ErrUnsafePath)
	}
	after, afterErr := os.Lstat(path)
	if afterErr != nil || after.Mode()&os.ModeSymlink != 0 || !sameFile(info, after) {
		_ = file.Close()
		return nil, fmt.Errorf("%w: lock guard identity", ErrUnsafePath)
	}
	if err := validateOwner(info); err != nil {
		_ = file.Close()
		return nil, err
	}
	if err := tryExclusiveLock(file); err != nil {
		_ = file.Close()
		return nil, err
	}
	return file, nil
}

func waitForLock(ctx context.Context, deadline *time.Time) error {
	if deadline.IsZero() || !time.Now().Before(*deadline) {
		return fmt.Errorf("%w: profile snapshot is already locked", ErrLockConflict)
	}
	wait := 10 * time.Millisecond
	remaining := time.Until(*deadline)
	if remaining < wait {
		wait = remaining
	}
	timer := time.NewTimer(wait)
	defer timer.Stop()
	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-timer.C:
		return nil
	}
}

func createHeldLock(lockPath string) (*heldLock, error) {
	if err := validateNoSymlinkChain(lockPath, false); err != nil {
		_ = os.Remove(lockPath)
		return nil, err
	}
	info, err := os.Lstat(lockPath)
	if err != nil || !info.IsDir() || info.Mode().Perm() != 0o700 {
		_ = os.Remove(lockPath)
		return nil, fmt.Errorf("%w: lock directory", ErrUnsafePath)
	}
	if err := validateOwner(info); err != nil {
		_ = os.Remove(lockPath)
		return nil, err
	}
	invocationID, err := randomToken()
	if err != nil {
		_ = os.Remove(lockPath)
		return nil, fmt.Errorf("%w: lock token", ErrLockConflict)
	}
	ownerPath := filepath.Join(lockPath, "owner.json")
	owner := lockOwner{PID: os.Getpid(), InvocationID: invocationID, CreatedAt: time.Now().UTC()}
	data, err := json.Marshal(owner)
	if err != nil {
		_ = os.Remove(lockPath)
		return nil, fmt.Errorf("%w: lock owner", ErrLockConflict)
	}
	file, err := os.OpenFile(ownerPath, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o600)
	if err != nil {
		_ = os.Remove(lockPath)
		return nil, fmt.Errorf("%w: lock owner", ErrLockConflict)
	}
	writeErr := writeSync(file, append(data, '\n'))
	closeErr := file.Close()
	if writeErr != nil || closeErr != nil {
		_ = os.Remove(ownerPath)
		_ = os.Remove(lockPath)
		return nil, fmt.Errorf("%w: lock owner", ErrLockConflict)
	}
	ownerInfo, err := os.Lstat(ownerPath)
	if err != nil || ownerInfo.Mode().Perm() != 0o600 || fileNlinkValue(ownerInfo) != 1 {
		_ = os.Remove(ownerPath)
		_ = os.Remove(lockPath)
		return nil, fmt.Errorf("%w: lock owner state", ErrUnsafePath)
	}
	return &heldLock{path: lockPath, ownerPath: ownerPath, invocationID: invocationID, directory: info}, nil
}

func lockIsReclaimable(lockPath string) (*staleLockCandidate, error) {
	info, err := os.Lstat(lockPath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, fmt.Errorf("%w: inspect lock", ErrLockConflict)
	}
	if !info.IsDir() || info.Mode()&os.ModeSymlink != 0 || info.Mode().Perm() != 0o700 {
		return nil, fmt.Errorf("%w: ambiguous lock directory", ErrLockConflict)
	}
	if err := validateOwner(info); err != nil {
		return nil, err
	}
	entries, err := os.ReadDir(lockPath)
	if err != nil || len(entries) != 1 || entries[0].Name() != "owner.json" || entries[0].Type()&os.ModeSymlink != 0 {
		return nil, fmt.Errorf("%w: ambiguous lock contents", ErrLockConflict)
	}
	ownerPath := filepath.Join(lockPath, "owner.json")
	ownerInfo, err := os.Lstat(ownerPath)
	if err != nil {
		return nil, fmt.Errorf("%w: ambiguous lock owner", ErrLockConflict)
	}
	if _, err := requireDirectPrivateFileInfo(ownerInfo, 64*1024); err != nil {
		return nil, fmt.Errorf("%w: ambiguous lock owner", ErrLockConflict)
	}
	data, stableOwnerInfo, err := readPrivateFileStable(ownerPath, 64*1024)
	if err != nil {
		return nil, fmt.Errorf("%w: read lock owner", ErrLockConflict)
	}
	if !sameFile(ownerInfo, stableOwnerInfo) {
		return nil, fmt.Errorf("%w: lock owner changed", ErrLockConflict)
	}
	var owner lockOwner
	if err := decodeStrict(data, &owner); err != nil || owner.PID <= 0 || owner.InvocationID == "" || owner.CreatedAt.IsZero() {
		return nil, fmt.Errorf("%w: malformed lock owner", ErrLockConflict)
	}
	if processIsAlive(owner.PID) {
		return nil, nil
	}
	return &staleLockCandidate{path: lockPath, directory: info, ownerPath: ownerPath, owner: stableOwnerInfo, identity: owner}, nil
}

func reclaimLock(candidate *staleLockCandidate) error {
	if candidate == nil {
		return fmt.Errorf("%w: missing stale lock candidate", ErrLockConflict)
	}
	info, err := os.Lstat(candidate.path)
	if err != nil {
		return err
	}
	if !sameFile(info, candidate.directory) {
		return fmt.Errorf("%w: lock identity changed", ErrLockConflict)
	}
	entries, err := os.ReadDir(candidate.path)
	if err != nil || len(entries) != 1 || entries[0].Name() != "owner.json" || entries[0].Type()&os.ModeSymlink != 0 {
		return fmt.Errorf("%w: lock contents changed", ErrLockConflict)
	}
	ownerPath := filepath.Join(candidate.path, "owner.json")
	data, ownerInfo, err := readPrivateFileStable(ownerPath, 64*1024)
	if err != nil || !sameFile(ownerInfo, candidate.owner) {
		return fmt.Errorf("%w: lock owner identity changed", ErrLockConflict)
	}
	var owner lockOwner
	if err := decodeStrict(data, &owner); err != nil || owner != candidate.identity || processIsAlive(owner.PID) {
		return fmt.Errorf("%w: lock is no longer reclaimable", ErrLockConflict)
	}
	token, err := randomToken()
	if err != nil {
		return fmt.Errorf("%w: stale lock quarantine identity", ErrLockConflict)
	}
	stalePath := candidate.path + ".stale." + token
	if err := os.Rename(candidate.path, stalePath); err != nil {
		return err
	}
	ownerPath = filepath.Join(stalePath, "owner.json")
	if err := os.Remove(ownerPath); err != nil && !os.IsNotExist(err) {
		return fmt.Errorf("%w: reclaim lock owner", ErrLockConflict)
	}
	if err := os.Remove(stalePath); err != nil {
		return fmt.Errorf("%w: reclaim lock directory", ErrLockConflict)
	}
	return nil
}

func (lock *heldLock) release() (result error) {
	if lock == nil {
		return nil
	}
	defer func() {
		if lock.guard != nil {
			if err := unlockExclusive(lock.guard); result == nil && err != nil {
				result = err
			}
			if err := lock.guard.Close(); result == nil && err != nil {
				result = err
			}
		}
	}()
	info, err := os.Lstat(lock.path)
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}
	if !sameFile(info, lock.directory) {
		return fmt.Errorf("%w: lock ownership changed", ErrLockConflict)
	}
	data, _, err := readPrivateFileStable(lock.ownerPath, 64*1024)
	if err != nil {
		return err
	}
	var owner lockOwner
	if err := decodeStrict(data, &owner); err != nil || owner.InvocationID != lock.invocationID || owner.PID != os.Getpid() {
		return fmt.Errorf("%w: lock owner mismatch", ErrLockConflict)
	}
	if err := os.Remove(lock.ownerPath); err != nil {
		return err
	}
	if err := os.Remove(lock.path); err != nil {
		return err
	}
	return result
}

func randomToken() (string, error) {
	var bytes [24]byte
	if _, err := io.ReadFull(rand.Reader, bytes[:]); err != nil {
		return "", err
	}
	return hex.EncodeToString(bytes[:]), nil
}

func writeSync(file *os.File, data []byte) error {
	if _, err := file.Write(data); err != nil {
		return err
	}
	return file.Sync()
}

func fileNlinkValue(info os.FileInfo) uint64 {
	value, ok := fileNlink(info)
	if !ok {
		return 0
	}
	return value
}
