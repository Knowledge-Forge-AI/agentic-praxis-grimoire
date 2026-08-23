package response

import (
	"context"
	"errors"
	"os"
)

var syncPublishedDirectory = syncDirectory

// Capture allocates the next immutable response number and publishes the
// exact selected input bytes under <outbox>/<project>/<phase>.
func Capture(ctx context.Context, options Options) (string, error) {
	if ctx == nil {
		ctx = context.Background()
	}
	if err := ctx.Err(); err != nil {
		return "", err
	}
	body, err := readInput(ctx, options)
	if err != nil {
		return "", err
	}
	phaseDirectory, err := PhaseDirectory(options.OutboxRoot, options.Project, options.Phase)
	if err != nil {
		return "", err
	}
	lock, err := acquireLock(ctx, phaseDirectory)
	if err != nil {
		return "", err
	}
	defer lock.release()

	var (
		reservationPath string
		reservationInfo os.FileInfo
		temporaryPath   string
		temporaryInfo   os.FileInfo
		destination     string
	)
	defer func() {
		// Cleanup is intentionally best-effort here. The destination is
		// never removed after hard-link publication, even if a later cleanup
		// or directory-sync operation fails.
		if temporaryPath != "" {
			_ = removeOwned(temporaryPath, temporaryInfo)
		}
		if reservationPath != "" {
			_ = removeOwned(reservationPath, reservationInfo)
		}
		if temporaryPath != "" || reservationPath != "" {
			_ = syncDirectory(phaseDirectory)
		}
	}()

	if err := cleanOrphanTemporaries(ctx, phaseDirectory); err != nil {
		return "", err
	}
	number, reserved, reservedInfo, err := reserve(ctx, phaseDirectory, options.Phase)
	if err != nil {
		return "", err
	}
	reservationPath, reservationInfo = reserved, reservedInfo
	destination = responsePath(phaseDirectory, options.Phase, number)
	if err := ctx.Err(); err != nil {
		return "", err
	}
	temporaryPath, temporaryInfo, err = writeTemporary(ctx, phaseDirectory, body)
	if err != nil {
		return "", err
	}
	if exists, err := lexists(destination); err != nil {
		return "", err
	} else if exists {
		return "", unsafeError("response destination appeared after reservation")
	}
	if err := ctx.Err(); err != nil {
		return "", err
	}
	if err := os.Link(temporaryPath, destination); err != nil {
		return "", wrappedError(ErrUnsafe, "atomic no-overwrite response publication failed", err)
	}
	destinationInfo, err := os.Lstat(destination)
	if err != nil || destinationInfo.Mode()&os.ModeSymlink != 0 || !destinationInfo.Mode().IsRegular() || !sameObject(temporaryInfo, destinationInfo) || ownerID(destinationInfo) != int64(os.Getuid()) || destinationInfo.Mode().Perm() != 0o600 {
		if err == nil {
			err = errors.New("response destination identity is unsafe")
		}
		return "", wrappedError(ErrUnsafe, "response destination is not a regular file", err)
	}
	if err := removeOwned(temporaryPath, temporaryInfo); err != nil {
		return "", err
	}
	temporaryPath, temporaryInfo = "", nil
	if err := ctx.Err(); err != nil {
		return "", err
	}
	if err := syncPublishedDirectory(phaseDirectory); err != nil {
		return "", wrappedError(ErrUnsafe, "response publication durability failed", err)
	}
	if err := removeOwned(reservationPath, reservationInfo); err != nil {
		return "", err
	}
	reservationPath, reservationInfo = "", nil
	if err := syncPublishedDirectory(phaseDirectory); err != nil {
		return "", wrappedError(ErrUnsafe, "response reservation cleanup durability failed", err)
	}
	return destination, nil
}

// Record is the compatibility alias for Capture.
func Record(ctx context.Context, options Options) (string, error) {
	return Capture(ctx, options)
}

// CaptureResponse is a descriptive compatibility alias for Capture.
func CaptureResponse(ctx context.Context, options Options) (string, error) {
	return Capture(ctx, options)
}

// RecordResponse is a descriptive compatibility alias for Capture.
func RecordResponse(ctx context.Context, options Options) (string, error) {
	return Capture(ctx, options)
}
