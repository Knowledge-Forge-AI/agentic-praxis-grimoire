package cli

import (
	"bytes"
	"context"
	"errors"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/report"
)

func appendLegacy(ctx context.Context, root, project, phase string, record []byte) (string, error) {
	directory := filepath.Join(root, project)
	if err := prepareLegacyDirectory(root, directory); err != nil {
		return "", err
	}
	path := filepath.Join(directory, phase+".report.txt")
	lock := path + ".lock"
	release, err := acquireLegacyLock(ctx, lock)
	if err != nil {
		return "", err
	}
	defer release()
	existing, exists, err := readLegacy(path)
	if err != nil {
		return "", err
	}
	if exists {
		if err := validateLegacyRecords(existing); err != nil {
			return "", errors.New("existing report record structure is unsafe")
		}
	}
	if parsed, err := report.ParseRecords(record); err != nil || len(parsed) != 1 {
		return "", errors.New("report record envelope is invalid")
	}
	combined := append([]byte(nil), existing...)
	if len(combined) > 0 && combined[len(combined)-1] != '\n' {
		combined = append(combined, '\n')
	}
	combined = append(combined, record...)
	if err := validateLegacyRecords(combined); err != nil {
		return "", errors.New("combined report record structure is unsafe")
	}
	if err := replaceLegacy(directory, path, phase, combined); err != nil {
		return "", err
	}
	return path, nil
}

func validateLegacyRecords(data []byte) error {
	if len(data) == 0 {
		return nil
	}
	startMarker := []byte("<<<AGENT-REPORT-ENVELOPE\nBEGIN AGENT-REPORT-RECORD\n")
	firstIndex := bytes.Index(data, startMarker)
	if firstIndex < 0 {
		return nil
	}
	_, err := report.ParseRecords(data[firstIndex:])
	return err
}

func prepareLegacyDirectory(root, projectDirectory string) error {
	for _, directory := range []string{root, projectDirectory} {
		if metadata, err := os.Lstat(directory); err == nil && (metadata.Mode()&os.ModeSymlink != 0 || !metadata.IsDir()) {
			return errors.New("report directory is unsafe")
		}
		if err := os.MkdirAll(directory, 0o700); err != nil {
			return errors.New("report directory creation failed")
		}
		if err := os.Chmod(directory, 0o700); err != nil {
			return errors.New("report directory mode is unsafe")
		}
		metadata, err := os.Lstat(directory)
		if err != nil || !metadata.IsDir() || metadata.Mode()&os.ModeSymlink != 0 || metadata.Mode().Perm() != 0o700 {
			return errors.New("report directory is unsafe")
		}
		if stat, ok := metadata.Sys().(*syscall.Stat_t); !ok || stat.Uid != uint32(os.Getuid()) {
			return errors.New("report directory is unsafe")
		}
	}
	return nil
}

func readLegacy(path string) ([]byte, bool, error) {
	metadata, err := os.Lstat(path)
	if os.IsNotExist(err) {
		return nil, false, nil
	}
	if err != nil || !metadata.Mode().IsRegular() || metadata.Mode()&os.ModeSymlink != 0 || metadata.Mode().Perm() != 0o600 {
		return nil, false, errors.New("existing report file is unsafe")
	}
	file, err := os.OpenFile(path, os.O_RDONLY|syscall.O_NOFOLLOW, 0)
	if err != nil {
		return nil, false, errors.New("existing report file is unsafe")
	}
	defer file.Close()
	opened, err := file.Stat()
	if err != nil || !sameFile(metadata, opened) {
		return nil, false, errors.New("existing report file is unsafe")
	}
	content, err := io.ReadAll(io.LimitReader(file, 128<<20))
	if err != nil {
		return nil, false, errors.New("existing report file is unsafe")
	}
	return content, true, nil
}

func acquireLegacyLock(ctx context.Context, path string) (func(), error) {
	owner := filepath.Join(path, "owner")
	token := strconv.Itoa(os.Getpid()) + "\n"
	for attempt := 0; attempt < 400; attempt++ {
		if err := ctx.Err(); err != nil {
			return nil, err
		}
		err := os.Mkdir(path, 0o700)
		if err == nil {
			if writeErr := os.WriteFile(owner, []byte(token), 0o600); writeErr != nil {
				_ = os.Remove(path)
				return nil, errors.New("report append lock owner is unsafe")
			}
			return func() {
				content, readErr := os.ReadFile(owner)
				if readErr == nil && bytes.Equal(content, []byte(token)) {
					_ = os.Remove(owner)
					_ = os.Remove(path)
				}
			}, nil
		}
		if !os.IsExist(err) {
			return nil, errors.New("report append lock is unsafe")
		}
		if recoverLegacyLock(path, owner) {
			continue
		}
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		case <-time.After(10 * time.Millisecond):
		}
	}
	return nil, errors.New("report append is already active")
}

func recoverLegacyLock(path, owner string) bool {
	metadata, err := os.Lstat(path)
	if err != nil || !metadata.IsDir() || metadata.Mode()&os.ModeSymlink != 0 {
		return false
	}
	content, err := os.ReadFile(owner)
	if err != nil {
		if os.IsNotExist(err) && time.Since(metadata.ModTime()) >= time.Second {
			return os.Remove(path) == nil
		}
		return false
	}
	pid, err := strconv.Atoi(strings.TrimSpace(string(content)))
	if err != nil || pid <= 0 {
		return false
	}
	err = syscall.Kill(pid, 0)
	if err == nil || err == syscall.EPERM {
		return false
	}
	if err != syscall.ESRCH {
		return false
	}
	if os.Remove(owner) != nil {
		return false
	}
	return os.Remove(path) == nil
}

func replaceLegacy(directory, target, phase string, content []byte) error {
	file, err := os.CreateTemp(directory, "."+phase+".report.")
	if err != nil {
		return errors.New("report replacement creation failed")
	}
	temporary := file.Name()
	defer os.Remove(temporary)
	if err := file.Chmod(0o600); err != nil {
		_ = file.Close()
		return errors.New("report replacement mode is unsafe")
	}
	if _, err := file.Write(content); err != nil {
		_ = file.Close()
		return errors.New("report replacement write failed")
	}
	if err := file.Sync(); err != nil {
		_ = file.Close()
		return errors.New("report replacement sync failed")
	}
	if err := file.Close(); err != nil {
		return errors.New("report replacement close failed")
	}
	if err := testFailStep("before-destination-replacement"); err != nil {
		return err
	}
	if err := os.Rename(temporary, target); err != nil {
		return errors.New("report replacement failed")
	}
	if err := os.Chmod(target, 0o600); err != nil {
		return errors.New("report destination mode is unsafe")
	}
	if directoryFile, err := os.Open(directory); err == nil {
		_ = directoryFile.Sync()
		_ = directoryFile.Close()
	}
	return nil
}

func testFailStep(step string) error {
	if os.Getenv("APG_REPORT_GO_TESTING") != "1" && os.Getenv("GIT_SHOW_REPORT_TESTING") != "1" && os.Getenv("AGENT_REPORT_TESTING") != "1" {
		return nil
	}
	target := os.Getenv("APG_REPORT_GO_TEST_FAIL_STEP")
	if target == "" {
		target = os.Getenv("GIT_SHOW_REPORT_TEST_FAIL_STEP")
	}
	if target == "" {
		target = os.Getenv("AGENT_REPORT_TEST_FAIL_STEP")
	}
	if target != "" && (target == step || step == "*") {
		return errors.New("injected test failure at step " + target)
	}
	return nil
}
