package cli

import (
	"context"
	"errors"
	"io"
	"os"
	"path/filepath"
	"syscall"
	"time"
)

const maxOperationalSourceBytes = 8 << 20

func readOperationalSource(ctx context.Context, value string, destinations []string) ([]byte, string, error) {
	if value == "" || !filepath.IsAbs(value) || filepath.Clean(value) != value {
		return nil, "", usageError{"operational report path must be absolute and clean"}
	}
	for _, destination := range destinations {
		if value == destination {
			return nil, "", errors.New("source operational report is the destination report")
		}
	}
	before, err := os.Lstat(value)
	if err != nil {
		return nil, "", errors.New("source operational report is unsafe")
	}
	if err := validateSourceMetadata(before); err != nil {
		return nil, "", err
	}
	file, err := os.OpenFile(value, os.O_RDONLY|syscall.O_NOFOLLOW, 0)
	if err != nil {
		return nil, "", errors.New("source operational report is unsafe")
	}
	defer file.Close()
	opened, err := file.Stat()
	if err != nil || !sameFile(before, opened) {
		return nil, "", errors.New("source operational report changed before reading")
	}
	if err := sourceTestPause(ctx); err != nil {
		return nil, "", err
	}
	content, err := io.ReadAll(io.LimitReader(file, maxOperationalSourceBytes+1))
	if err != nil {
		return nil, "", errors.New("source operational report is unsafe")
	}
	if len(content) == 0 {
		return nil, "", errors.New("source operational report is empty")
	}
	if len(content) > maxOperationalSourceBytes {
		return nil, "", errors.New("source operational report is oversized")
	}
	after, err := os.Lstat(value)
	if err != nil || !sameFile(before, after) || after.Size() != int64(len(content)) {
		return nil, "", errors.New("source operational report changed during reading")
	}
	return content, filepath.Base(value), nil
}

func sourceTestPause(ctx context.Context) error {
	if os.Getenv("APG_REPORT_GO_TESTING") != "1" || os.Getenv("APG_REPORT_GO_TEST_PAUSE_STEP") != "source-validated" {
		return nil
	}
	directory := os.Getenv("APG_REPORT_GO_TEST_SIGNAL_DIR")
	if directory == "" {
		return errors.New("test pause signal directory is unavailable")
	}
	if err := os.WriteFile(filepath.Join(directory, "ready"), []byte{}, 0o600); err != nil {
		return errors.New("test pause signal unavailable")
	}
	ticker := time.NewTicker(10 * time.Millisecond)
	defer ticker.Stop()
	timer := time.NewTimer(30 * time.Second)
	defer timer.Stop()
	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-ticker.C:
			if _, err := os.Stat(filepath.Join(directory, "continue")); err == nil {
				return nil
			}
		case <-timer.C:
			return errors.New("test pause timed out")
		}
	}
}

func validateSourceMetadata(metadata os.FileInfo) error {
	if !metadata.Mode().IsRegular() || metadata.Mode()&os.ModeSymlink != 0 {
		return errors.New("source operational report is unsafe")
	}
	if metadata.Mode().Perm() != 0o600 {
		return errors.New("source operational report permissions are unsafe")
	}
	stat, ok := metadata.Sys().(*syscall.Stat_t)
	if !ok || stat.Uid != uint32(os.Getuid()) {
		return errors.New("source operational report is unsafe")
	}
	if stat.Nlink != 1 {
		return errors.New("source operational report hard links are unsafe")
	}
	if metadata.Size() > maxOperationalSourceBytes {
		return errors.New("source operational report is oversized")
	}
	return nil
}

func sameFile(left, right os.FileInfo) bool {
	leftStat, leftOK := left.Sys().(*syscall.Stat_t)
	rightStat, rightOK := right.Sys().(*syscall.Stat_t)
	return leftOK && rightOK && leftStat.Dev == rightStat.Dev && leftStat.Ino == rightStat.Ino && left.Mode() == right.Mode() && left.Size() == right.Size()
}
