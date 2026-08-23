package response

import (
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"syscall"
	"time"
)

func reserve(ctx context.Context, phaseDirectory, phase string) (int, string, os.FileInfo, error) {
	entries, err := os.ReadDir(phaseDirectory)
	if err != nil {
		return 0, "", nil, wrappedError(ErrUnsafe, "could not inspect response directory", err)
	}
	reserved := map[int]bool{}
	for _, entry := range entries {
		match := reservationPattern.FindStringSubmatch(entry.Name())
		if match == nil || match[1] != phase {
			continue
		}
		var number int
		if _, scanErr := fmt.Sscanf(match[2], "%d", &number); scanErr == nil {
			reserved[number] = true
		}
	}
	for number := 1; number <= MaxResponseNumber; number++ {
		if err := ctx.Err(); err != nil {
			return 0, "", nil, err
		}
		destination := responsePath(phaseDirectory, phase, number)
		exists, err := lexists(destination)
		if err != nil {
			return 0, "", nil, err
		}
		if exists || reserved[number] {
			continue
		}
		token, err := randomToken()
		if err != nil {
			return 0, "", nil, wrappedError(ErrUnsafe, "could not create response reservation identity", err)
		}
		path := reservationPath(phaseDirectory, phase, number, token)
		file, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL|syscall.O_NOFOLLOW, 0o600)
		if err != nil {
			if os.IsExist(err) {
				continue
			}
			return 0, "", nil, wrappedError(ErrUnsafe, "could not create response reservation", err)
		}
		content := []byte(fmt.Sprintf("response-reservation-v1\nphase=%s\nnumber=%03d\n", phase, number))
		info, writeErr := writeAndSync(file, content)
		closeErr := file.Close()
		if writeErr != nil || closeErr != nil {
			_ = removeOwned(path, info)
			if writeErr == nil {
				writeErr = closeErr
			}
			return 0, "", nil, wrappedError(ErrUnsafe, "could not write response reservation", writeErr)
		}
		if err := syncDirectory(phaseDirectory); err != nil {
			_ = removeOwned(path, info)
			return 0, "", nil, wrappedError(ErrUnsafe, "could not make response reservation durable", err)
		}
		return number, path, info, nil
	}
	return 0, "", nil, allocationError("response numbers exhausted (001..999)")
}

func writeTemporary(ctx context.Context, phaseDirectory string, body []byte) (string, os.FileInfo, error) {
	for attempt := 0; attempt < 8; attempt++ {
		if err := ctx.Err(); err != nil {
			return "", nil, err
		}
		token, err := randomToken()
		if err != nil {
			return "", nil, wrappedError(ErrUnsafe, "could not create response temporary identity", err)
		}
		path := filepath.Join(phaseDirectory, ".response-write."+token+".tmp")
		file, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL|syscall.O_NOFOLLOW, 0o600)
		if err != nil {
			if os.IsExist(err) {
				continue
			}
			return "", nil, wrappedError(ErrUnsafe, "could not create response temporary file", err)
		}
		info, writeErr := writeAndSync(file, body)
		closeErr := file.Close()
		if writeErr == nil {
			writeErr = closeErr
		}
		if writeErr != nil {
			_ = removeOwned(path, info)
			return "", nil, wrappedError(ErrUnsafe, "could not write response temporary file", writeErr)
		}
		if err := ctx.Err(); err != nil {
			_ = removeOwned(path, info)
			return "", nil, err
		}
		return path, info, nil
	}
	return "", nil, unsafeError("could not reserve response temporary file")
}

func cleanOrphanTemporaries(ctx context.Context, phaseDirectory string) error {
	entries, err := os.ReadDir(phaseDirectory)
	if err != nil {
		return wrappedError(ErrUnsafe, "could not inspect response temporary files", err)
	}
	for _, entry := range entries {
		if temporaryPattern.FindString(entry.Name()) == "" {
			continue
		}
		if err := ctx.Err(); err != nil {
			return err
		}
		path := filepath.Join(phaseDirectory, entry.Name())
		info, statErr := os.Lstat(path)
		if os.IsNotExist(statErr) {
			continue
		}
		if statErr != nil {
			return wrappedError(ErrUnsafe, "could not inspect response temporary file", statErr)
		}
		if err := validatePrivateFileMetadata(info, false); err != nil {
			return unsafeError("response temporary artifact is unsafe")
		}
		if err := removeOwned(path, info); err != nil {
			return err
		}
	}
	return syncDirectory(phaseDirectory)
}

type heldLock struct {
	file *os.File
}

func acquireLock(ctx context.Context, phaseDirectory string) (*heldLock, error) {
	lockPath := filepath.Join(phaseDirectory, LockName)
	deadline := time.Now().Add(lockTimeout)
	for {
		if err := ctx.Err(); err != nil {
			return nil, err
		}
		file, err := os.OpenFile(lockPath, os.O_RDWR|os.O_CREATE|syscall.O_NOFOLLOW, 0o600)
		if err != nil {
			return nil, wrappedError(ErrUnsafe, "could not acquire response phase lock", err)
		}
		info, statErr := file.Stat()
		if statErr != nil || info.Mode()&os.ModeSymlink != 0 || !info.Mode().IsRegular() || info.Mode().Perm() != 0o600 || ownerID(info) != int64(os.Getuid()) || linkCount(info) != 1 {
			_ = file.Close()
			return nil, unsafeError("response lock is unsafe")
		}
		flockErr := syscall.Flock(int(file.Fd()), syscall.LOCK_EX|syscall.LOCK_NB)
		if flockErr == nil {
			if err := file.Truncate(0); err != nil {
				_ = file.Close()
				return nil, wrappedError(ErrUnsafe, "could not write response phase lock", err)
			}
			if _, err := file.Write([]byte("response-lock-v2\n")); err != nil {
				_ = syscall.Flock(int(file.Fd()), syscall.LOCK_UN)
				_ = file.Close()
				return nil, wrappedError(ErrUnsafe, "could not write response phase lock", err)
			}
			if err := file.Sync(); err != nil {
				_ = syscall.Flock(int(file.Fd()), syscall.LOCK_UN)
				_ = file.Close()
				return nil, wrappedError(ErrUnsafe, "could not synchronize response phase lock", err)
			}
			if err := syncDirectory(phaseDirectory); err != nil {
				_ = syscall.Flock(int(file.Fd()), syscall.LOCK_UN)
				_ = file.Close()
				return nil, wrappedError(ErrUnsafe, "could not synchronize response phase lock", err)
			}
			return &heldLock{file: file}, nil
		}
		_ = file.Close()
		if !errors.Is(flockErr, syscall.EAGAIN) && !errors.Is(flockErr, syscall.EWOULDBLOCK) {
			if errors.Is(flockErr, syscall.EINTR) {
				continue
			}
			return nil, wrappedError(ErrUnsafe, "could not acquire response phase lock", flockErr)
		}
		if time.Now().After(deadline) {
			return nil, allocationError("response phase lock remained busy")
		}
		timer := time.NewTimer(lockPoll)
		select {
		case <-ctx.Done():
			if !timer.Stop() {
				<-timer.C
			}
			return nil, ctx.Err()
		case <-timer.C:
		}
	}
}

func (lock *heldLock) release() {
	if lock == nil || lock.file == nil {
		return
	}
	_ = syscall.Flock(int(lock.file.Fd()), syscall.LOCK_UN)
	_ = lock.file.Close()
}
