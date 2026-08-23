package response

import (
	"context"
	"errors"
	"io"
	"os"
	"path/filepath"
	"strings"
	"syscall"
)

func readInput(ctx context.Context, options Options) ([]byte, error) {
	selected := 0
	if options.Body != nil {
		selected++
	}
	if options.InputPath != "" {
		selected++
	}
	if options.Stdin != nil {
		selected++
	}
	if selected != 1 {
		return nil, usageError("exactly one response input is required")
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	if options.Body != nil {
		if len(options.Body) > MaxResponseBytes {
			return nil, inputError("response input exceeds the 8 MiB limit")
		}
		return append([]byte(nil), options.Body...), nil
	}
	if options.InputPath != "" {
		return readSource(ctx, options.InputPath)
	}
	return readBounded(ctx, options.Stdin, "response stdin")
}

func readSource(ctx context.Context, path string) ([]byte, error) {
	path, err := expandUser(path)
	if err != nil {
		return nil, inputError("response input path is invalid")
	}
	before, err := os.Lstat(path)
	if err != nil {
		return nil, wrappedError(ErrInput, "could not read response input file", err)
	}
	if before.Mode()&os.ModeSymlink != 0 || !before.Mode().IsRegular() {
		return nil, inputError("response input must be a regular file")
	}
	if before.Size() > MaxResponseBytes {
		return nil, inputError("response input exceeds the 8 MiB limit")
	}
	file, err := os.OpenFile(path, os.O_RDONLY|syscall.O_NOFOLLOW, 0)
	if err != nil {
		return nil, wrappedError(ErrInput, "could not read response input file", err)
	}
	defer file.Close()
	opened, err := file.Stat()
	if err != nil || !sameObject(before, opened) || opened.Mode()&os.ModeSymlink != 0 || !opened.Mode().IsRegular() || ownerID(opened) != int64(os.Getuid()) {
		return nil, inputError("response input changed during opening")
	}
	content, err := readBounded(ctx, file, "response input file")
	if err != nil {
		return nil, err
	}
	after, err := os.Lstat(path)
	if err != nil || !sameObject(before, after) || after.Size() != int64(len(content)) {
		return nil, inputError("response input changed during reading")
	}
	return content, nil
}

func readBounded(ctx context.Context, reader io.Reader, label string) ([]byte, error) {
	if reader == nil {
		return nil, usageError("exactly one response input is required")
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	content, err := io.ReadAll(io.LimitReader(reader, MaxResponseBytes+1))
	if err != nil {
		return nil, wrappedError(ErrInput, "could not read "+label, err)
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	if len(content) > MaxResponseBytes {
		return nil, inputError("response input exceeds the 8 MiB limit")
	}
	return content, nil
}

func expandUser(path string) (string, error) {
	if path == "~" {
		home, err := os.UserHomeDir()
		if err != nil {
			return "", err
		}
		return home, nil
	}
	if strings.HasPrefix(path, "~/") {
		home, err := os.UserHomeDir()
		if err != nil {
			return "", err
		}
		return filepath.Join(home, strings.TrimPrefix(path, "~/")), nil
	}
	if strings.HasPrefix(path, "~") {
		return "", errors.New("unsupported user home syntax")
	}
	return path, nil
}
