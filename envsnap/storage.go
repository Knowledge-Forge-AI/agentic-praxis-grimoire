package envsnap

import (
	"context"
	"fmt"
	"io"
	"os"
	"path/filepath"
)

func snapshotDirectory(storageRoot, profileID string) (string, error) {
	if err := requireAbsoluteClean(storageRoot); err != nil {
		return "", err
	}
	if err := validateProfileID(profileID); err != nil {
		return "", fmt.Errorf("%w: profile id", ErrUnsafePath)
	}
	return filepath.Join(storageRoot, "environment", profileID), nil
}

// Store atomically publishes a validated canonical snapshot under
// <root>/environment/<profile-id>/current.json. Equivalent content is reused
// without touching inode, bytes, mode, or mtime.
func Store(ctx context.Context, request StoreRequest) (result StoredSnapshot, resultErr error) {
	if ctx == nil {
		ctx = context.Background()
	}
	if err := ctx.Err(); err != nil {
		return StoredSnapshot{}, err
	}
	if request.Profile == nil {
		return StoredSnapshot{}, ErrProfileMismatch
	}
	if err := ValidateProfile(*request.Profile); err != nil {
		return StoredSnapshot{}, err
	}
	snapshot := cloneSnapshot(request.Snapshot)
	if err := validateSnapshotAgainstProfile(snapshot, *request.Profile); err != nil {
		return StoredSnapshot{}, err
	}
	directory, err := snapshotDirectory(request.StorageRoot, snapshot.ProfileID)
	if err != nil {
		return StoredSnapshot{}, err
	}
	if err := ensureStorageDirectories(request.StorageRoot, directory); err != nil {
		return StoredSnapshot{}, err
	}
	lock, err := acquireLock(ctx, directory, request.Timeout)
	if err != nil {
		return StoredSnapshot{}, err
	}
	defer func() {
		if releaseErr := lock.release(); resultErr == nil && releaseErr != nil {
			result = StoredSnapshot{}
			resultErr = releaseErr
		}
	}()
	if err := ctx.Err(); err != nil {
		return StoredSnapshot{}, err
	}
	path := filepath.Join(directory, "current.json")
	if existing, exists, err := readStoredSnapshot(path, ctx); err != nil {
		return StoredSnapshot{}, err
	} else if exists {
		if existing.ProfileID == snapshot.ProfileID && existing.ContentFingerprint == snapshot.ContentFingerprint {
			return StoredSnapshot{
				Path:               path,
				Disposition:        DispositionUnchanged,
				Snapshot:           existing,
				ContentFingerprint: existing.ContentFingerprint,
			}, nil
		}
	}
	encoded, err := MarshalSnapshot(snapshot)
	if err != nil {
		return StoredSnapshot{}, err
	}
	if int64(len(encoded)) > MaxSnapshotBytes {
		return StoredSnapshot{}, fmt.Errorf("%w: snapshot size", ErrUnsafePath)
	}
	if err := atomicPublish(ctx, directory, path, encoded); err != nil {
		return StoredSnapshot{}, err
	}
	return StoredSnapshot{
		Path:               path,
		Disposition:        DispositionStored,
		Snapshot:           snapshot,
		ContentFingerprint: snapshot.ContentFingerprint,
	}, nil
}

// Load opens and verifies one owner-safe canonical snapshot. When ExpectedProfile
// is non-nil, every entry and fingerprint is checked against that profile.
func Load(ctx context.Context, request LoadRequest) (Snapshot, error) {
	if ctx == nil {
		ctx = context.Background()
	}
	if err := ctx.Err(); err != nil {
		return Snapshot{}, err
	}
	profileID := request.ProfileID
	if profileID == "" && request.ExpectedProfile != nil {
		profileID = request.ExpectedProfile.ProfileID
	}
	if err := validateProfileID(profileID); err != nil {
		return Snapshot{}, fmt.Errorf("%w: profile id", ErrUnsafePath)
	}
	if request.ExpectedProfile == nil {
		return Snapshot{}, ErrProfileMismatch
	}
	if err := ValidateProfile(*request.ExpectedProfile); err != nil {
		return Snapshot{}, err
	}
	if request.ExpectedProfile.ProfileID != profileID {
		return Snapshot{}, ErrProfileMismatch
	}
	if request.MaxAge < 0 {
		return Snapshot{}, fmt.Errorf("%w: negative max age", ErrStale)
	}
	directory, err := snapshotDirectory(request.StorageRoot, profileID)
	if err != nil {
		return Snapshot{}, err
	}
	if err := requireStorageDirectories(request.StorageRoot, directory); err != nil {
		return Snapshot{}, err
	}
	path := filepath.Join(directory, "current.json")
	snapshot, exists, err := readStoredSnapshot(path, ctx)
	if err != nil {
		return Snapshot{}, err
	}
	if !exists {
		return Snapshot{}, fmt.Errorf("%w: snapshot does not exist", ErrInvalidSnapshot)
	}
	if snapshot.ProfileID != profileID {
		return Snapshot{}, ErrProfileMismatch
	}
	if err := validateSnapshotAgainstProfile(snapshot, *request.ExpectedProfile); err != nil {
		return Snapshot{}, err
	}
	now := nowUTC(request.Clock)
	if now.Before(snapshot.CapturedAt) {
		snapshot.Age = 0
	} else {
		snapshot.Age = now.Sub(snapshot.CapturedAt)
	}
	snapshot.Stale = request.MaxAge > 0 && snapshot.Age > request.MaxAge
	if snapshot.Stale {
		return Snapshot{}, &StaleError{Age: snapshot.Age, MaxAge: request.MaxAge}
	}
	return snapshot, nil
}

func ensureStorageDirectories(storageRoot, profileDirectory string) error {
	if err := requireAbsoluteClean(storageRoot); err != nil {
		return err
	}
	if err := ensurePrivateDirectory(storageRoot); err != nil {
		return err
	}
	environmentDirectory := filepath.Dir(profileDirectory)
	if err := ensurePrivateDirectory(environmentDirectory); err != nil {
		return err
	}
	return ensurePrivateDirectory(profileDirectory)
}

func requireStorageDirectories(storageRoot, profileDirectory string) error {
	if err := requireAbsoluteClean(storageRoot); err != nil {
		return err
	}
	if err := requirePrivateDirectory(storageRoot); err != nil {
		return err
	}
	environmentDirectory := filepath.Dir(profileDirectory)
	if err := requirePrivateDirectory(environmentDirectory); err != nil {
		return err
	}
	return requirePrivateDirectory(profileDirectory)
}

func readStoredSnapshot(path string, ctx context.Context) (Snapshot, bool, error) {
	if ctx != nil {
		if err := ctx.Err(); err != nil {
			return Snapshot{}, false, err
		}
	}
	initial, err := os.Lstat(path)
	if err != nil {
		if os.IsNotExist(err) {
			return Snapshot{}, false, nil
		}
		return Snapshot{}, false, fmt.Errorf("%w: inspect snapshot", ErrUnsafePath)
	}
	if _, err := requireDirectPrivateFile(path, MaxSnapshotBytes); err != nil {
		return Snapshot{}, false, err
	}
	file, err := os.Open(path)
	if err != nil {
		return Snapshot{}, false, fmt.Errorf("%w: open snapshot", ErrUnsafePath)
	}
	defer file.Close()
	opened, err := file.Stat()
	if err != nil || !sameFile(initial, opened) {
		return Snapshot{}, false, fmt.Errorf("%w: snapshot changed during open", ErrUnsafePath)
	}
	if _, err := requireDirectPrivateFileInfo(opened, MaxSnapshotBytes); err != nil {
		return Snapshot{}, false, err
	}
	data, err := io.ReadAll(io.LimitReader(file, MaxSnapshotBytes+1))
	if err != nil {
		return Snapshot{}, false, fmt.Errorf("%w: read snapshot", ErrUnsafePath)
	}
	if int64(len(data)) > MaxSnapshotBytes {
		return Snapshot{}, false, fmt.Errorf("%w: snapshot size", ErrUnsafePath)
	}
	if ctx != nil {
		if err := ctx.Err(); err != nil {
			return Snapshot{}, false, err
		}
	}
	final, err := os.Lstat(path)
	if err != nil || !sameFile(initial, final) {
		return Snapshot{}, false, fmt.Errorf("%w: snapshot changed during read", ErrUnsafePath)
	}
	if _, err := requireDirectPrivateFileInfo(final, MaxSnapshotBytes); err != nil {
		return Snapshot{}, false, err
	}
	snapshot, err := DecodeSnapshot(data)
	if err != nil {
		return Snapshot{}, false, err
	}
	canonical, err := MarshalSnapshot(snapshot)
	if err != nil || string(canonical) != string(data) {
		return Snapshot{}, false, fmt.Errorf("%w: non-canonical JSON", ErrInvalidSnapshot)
	}
	return snapshot, true, nil
}

func requireDirectPrivateFileInfo(info os.FileInfo, maxSize int64) (os.FileInfo, error) {
	if info == nil || info.Mode()&os.ModeSymlink != 0 || !info.Mode().IsRegular() {
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

func atomicPublish(ctx context.Context, directory, path string, data []byte) error {
	if err := ctx.Err(); err != nil {
		return err
	}
	token, err := randomToken()
	if err != nil {
		return fmt.Errorf("%w: temporary path", ErrUnsafePath)
	}
	temporary := filepath.Join(directory, ".current.json."+token+".tmp")
	file, err := os.OpenFile(temporary, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o600)
	if err != nil {
		return fmt.Errorf("%w: create temporary snapshot", ErrUnsafePath)
	}
	cleanup := true
	defer func() {
		_ = file.Close()
		if cleanup {
			_ = os.Remove(temporary)
		}
	}()
	if err := writeSync(file, data); err != nil {
		return fmt.Errorf("%w: write temporary snapshot", ErrUnsafePath)
	}
	if err := file.Close(); err != nil {
		return fmt.Errorf("%w: close temporary snapshot", ErrUnsafePath)
	}
	if err := ctx.Err(); err != nil {
		return err
	}
	if existing, err := os.Lstat(path); err == nil {
		if existing.Mode()&os.ModeSymlink != 0 || !existing.Mode().IsRegular() {
			return fmt.Errorf("%w: destination file type", ErrUnsafePath)
		}
		if nlink, ok := fileNlink(existing); !ok || nlink != 1 {
			return fmt.Errorf("%w: destination link count", ErrUnsafePath)
		}
		if err := validateOwner(existing); err != nil {
			return err
		}
		if existing.Mode().Perm() != 0o600 {
			return fmt.Errorf("%w: destination mode", ErrUnsafePath)
		}
	} else if !os.IsNotExist(err) {
		return fmt.Errorf("%w: inspect destination", ErrUnsafePath)
	}
	if err := os.Rename(temporary, path); err != nil {
		return fmt.Errorf("%w: publish snapshot", ErrUnsafePath)
	}
	cleanup = false
	if err := syncDirectory(directory); err != nil {
		return err
	}
	return nil
}

func syncDirectory(path string) error {
	directory, err := os.Open(path)
	if err != nil {
		return fmt.Errorf("%w: open snapshot directory", ErrUnsafePath)
	}
	err = directory.Sync()
	closeErr := directory.Close()
	if err != nil && err != os.ErrInvalid {
		return fmt.Errorf("%w: sync snapshot directory", ErrUnsafePath)
	}
	if closeErr != nil {
		return fmt.Errorf("%w: close snapshot directory", ErrUnsafePath)
	}
	return nil
}

func validateSnapshotAgainstProfile(snapshot Snapshot, profile Profile) error {
	if err := ValidateProfile(profile); err != nil {
		return err
	}
	if snapshot.ProfileID != profile.ProfileID {
		return ErrProfileMismatch
	}
	profileHash, err := profileFingerprint(profile)
	if err != nil || snapshot.ProfileFingerprint != profileHash {
		return ErrProfileMismatch
	}
	entries := profileEntryMap(profile)
	seen := make(map[string]struct{}, len(snapshot.Entries))
	for _, snapshotEntry := range snapshot.Entries {
		profileEntry, ok := entries[snapshotEntry.Name]
		if !ok {
			return invalidSnapshot("snapshot entry is not in profile")
		}
		if _, ok := seen[snapshotEntry.Name]; ok {
			return invalidSnapshot("snapshot contains duplicate names")
		}
		seen[snapshotEntry.Name] = struct{}{}
		if snapshotEntry.Validator != profileEntry.Validator {
			return invalidSnapshot("snapshot validator does not match profile")
		}
		if err := validateValue(snapshotEntry.Value, profileEntry.Validator, profileEntry.MaxBytes); err != nil {
			return invalidValueForName(snapshotEntry.Name, profileEntry.Validator, err)
		}
	}
	missingSet := make(map[string]struct{}, len(snapshot.MissingOptional))
	for _, name := range snapshot.MissingOptional {
		entry, ok := entries[name]
		if !ok || entry.Required {
			return invalidSnapshot("missing optional name does not match profile")
		}
		if _, ok := seen[name]; ok {
			return invalidSnapshot("name is both present and missing")
		}
		missingSet[name] = struct{}{}
	}
	for name, entry := range entries {
		if entry.Required {
			if _, present := seen[name]; !present {
				return invalidSnapshot("required profile name is absent")
			}
			continue
		}
		if _, present := seen[name]; !present {
			if _, missing := missingSet[name]; !missing {
				return invalidSnapshot("optional profile name is not classified")
			}
		}
	}
	return nil
}
