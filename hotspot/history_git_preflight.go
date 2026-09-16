package hotspot

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

func (gc *gitContext) validateRepo(ctx context.Context) error {
	bareOut, err := gc.runGit(ctx, "rev-parse", "--is-bare-repository")
	if err != nil {
		// Check if the failure is due to malformed config in an existing repository
		cfgPath := filepath.Join(gc.root, ".git", "config")
		if _, statErr := os.Lstat(cfgPath); statErr == nil {
			if _, listErr := gc.runGit(ctx, "config", "--local", "--list"); listErr != nil {
				return fmt.Errorf("invalid or unreadable git config: %w", listErr)
			}
		}
		return fmt.Errorf("root is not a valid git repository: %w", err)
	}
	if strings.TrimSpace(string(bareOut)) == "true" {
		return errors.New("bare repositories are not supported")
	}

	topOut, err := gc.runGit(ctx, "rev-parse", "--show-toplevel")
	if err != nil {
		return fmt.Errorf("cannot determine git toplevel: %w", err)
	}
	toplevel := strings.TrimSpace(string(topOut))
	resolvedToplevel, err := filepath.EvalSymlinks(toplevel)
	if err != nil {
		return fmt.Errorf("cannot resolve toplevel symlinks: %w", err)
	}
	if gc.root != resolvedToplevel {
		return errors.New("root must equal physical Git toplevel; subtrees are not supported")
	}

	expectedGitDir := filepath.Join(gc.root, ".git")
	gitDirStat, err := os.Lstat(expectedGitDir)
	if err != nil {
		return fmt.Errorf("cannot stat .git directory: %w", err)
	}
	if gitDirStat.Mode()&os.ModeSymlink != 0 {
		return errors.New("git directory symlinks are not supported")
	}
	if !gitDirStat.IsDir() {
		return errors.New("linked worktrees and non-directory .git are not supported")
	}
	resolvedGitDir, err := filepath.EvalSymlinks(expectedGitDir)
	if err != nil {
		return fmt.Errorf("cannot resolve .git directory symlinks: %w", err)
	}
	if resolvedGitDir != expectedGitDir {
		return errors.New("git directory symlinks are not supported")
	}
	gc.gitDir = expectedGitDir

	cfgFile := filepath.Join(gc.gitDir, "config")
	cfgStat, err := os.Lstat(cfgFile)
	if err != nil {
		return fmt.Errorf("failed to stat git config: %w", err)
	}
	if cfgStat.Mode()&os.ModeSymlink != 0 {
		return errors.New("git config symlinks are not supported")
	}
	if !cfgStat.Mode().IsRegular() {
		return errors.New("git config must be a regular file")
	}

	if _, err := gc.runGit(ctx, "config", "--local", "--list"); err != nil {
		return fmt.Errorf("invalid or unreadable git config: %w", err)
	}

	gitDirOut, err := gc.runGit(ctx, "rev-parse", "--git-dir")
	if err != nil {
		return fmt.Errorf("cannot determine git directory: %w", err)
	}
	gitDirStr := strings.TrimSpace(string(gitDirOut))
	if !filepath.IsAbs(gitDirStr) {
		gitDirStr = filepath.Join(gc.root, gitDirStr)
	}
	resolvedParsedGitDir, err := filepath.EvalSymlinks(filepath.Clean(gitDirStr))
	if err != nil || resolvedParsedGitDir != expectedGitDir {
		return errors.New("non-standard or linked git directory is not supported")
	}

	commonDirOut, err := gc.runGit(ctx, "rev-parse", "--git-common-dir")
	if err != nil {
		return fmt.Errorf("cannot determine git common directory: %w", err)
	}
	commonDirStr := strings.TrimSpace(string(commonDirOut))
	if !filepath.IsAbs(commonDirStr) {
		commonDirStr = filepath.Join(gc.root, commonDirStr)
	}
	resolvedCommonDir, err := filepath.EvalSymlinks(filepath.Clean(commonDirStr))
	if err != nil || resolvedCommonDir != expectedGitDir {
		return errors.New("git common directory indirection is not supported")
	}

	formatOut, err := gc.runGit(ctx, "rev-parse", "--show-object-format")
	if err != nil {
		return fmt.Errorf("failed to determine git object format: %w", err)
	}
	gc.objectFormat = strings.TrimSpace(string(formatOut))
	if gc.objectFormat != "sha1" && gc.objectFormat != "sha256" {
		return fmt.Errorf("unsupported git object format %q; must be sha1 or sha256", gc.objectFormat)
	}

	if _, err := os.Lstat(filepath.Join(gc.gitDir, "shallow")); err == nil {
		return errors.New("shallow repositories are not supported")
	} else if !errors.Is(err, os.ErrNotExist) {
		return fmt.Errorf("failed to stat git shallow marker: %w", err)
	}

	shallowOut, err := gc.runGit(ctx, "rev-parse", "--is-shallow-repository")
	if err != nil {
		return fmt.Errorf("failed to check shallow repository status: %w", err)
	}
	if strings.TrimSpace(string(shallowOut)) == "true" {
		return errors.New("shallow repositories are not supported")
	}

	if _, err := os.Lstat(filepath.Join(gc.gitDir, "info", "grafts")); err == nil {
		return errors.New("git grafts are not supported")
	} else if !errors.Is(err, os.ErrNotExist) {
		return fmt.Errorf("failed to stat git grafts: %w", err)
	}

	if _, err := os.Lstat(filepath.Join(gc.gitDir, "objects", "info", "alternates")); err == nil {
		return errors.New("git alternates are not supported")
	} else if !errors.Is(err, os.ErrNotExist) {
		return fmt.Errorf("failed to stat git alternates: %w", err)
	}

	if _, err := os.Lstat(filepath.Join(gc.gitDir, "objects", "info", "http-alternates")); err == nil {
		return errors.New("git http-alternates are not supported")
	} else if !errors.Is(err, os.ErrNotExist) {
		return fmt.Errorf("failed to stat git http-alternates: %w", err)
	}

	objDir := filepath.Join(gc.gitDir, "objects")
	objStat, err := os.Lstat(objDir)
	if err != nil {
		return fmt.Errorf("cannot stat git objects directory: %w", err)
	}
	if objStat.Mode()&os.ModeSymlink != 0 || !objStat.IsDir() {
		return errors.New("git objects directory symlinks are not supported")
	}
	resolvedObjDir, err := filepath.EvalSymlinks(objDir)
	if err != nil || resolvedObjDir != objDir {
		return errors.New("git objects directory symlinks are not supported")
	}

	infoDir := filepath.Join(objDir, "info")
	infoStat, err := os.Lstat(infoDir)
	if err == nil {
		if infoStat.Mode()&os.ModeSymlink != 0 || !infoStat.IsDir() {
			return errors.New("git objects/info directory symlinks are not supported")
		}
	} else if !errors.Is(err, os.ErrNotExist) {
		return fmt.Errorf("failed to stat git objects/info: %w", err)
	}

	packDir := filepath.Join(objDir, "pack")
	packStat, err := os.Lstat(packDir)
	if err == nil {
		if packStat.Mode()&os.ModeSymlink != 0 || !packStat.IsDir() {
			return errors.New("git objects/pack directory symlinks are not supported")
		}
		packEntries, err := os.ReadDir(packDir)
		if err != nil {
			return fmt.Errorf("failed to read git pack directory: %w", err)
		}
		for _, pe := range packEntries {
			if pe.Type()&os.ModeSymlink != 0 {
				return errors.New("symlinks in git pack directory are not supported")
			}
			if strings.HasSuffix(pe.Name(), ".promisor") {
				return errors.New("partial or promisor clones are not supported")
			}
		}
	} else if !errors.Is(err, os.ErrNotExist) {
		return fmt.Errorf("failed to stat git objects/pack: %w", err)
	}

	// Includes can hide partial-clone or protocol settings from --local queries.
	includeOut, includeErr := gc.runGit(ctx, "config", "--local", "--no-includes", "--get-regexp", `^include.*\.path$`)
	if includeErr == nil && len(includeOut) > 0 {
		return errors.New("local config includes are not supported")
	}
	if includeErr != nil && !isGitConfigNotFound(includeErr) {
		return errors.New("cannot inspect local config includes")
	}
	if err := validateObjectStorage(objDir); err != nil {
		return err
	}

	partOut, err := gc.runGit(ctx, "config", "--local", "--get", "extensions.partialclone")
	if err == nil && len(bytes.TrimSpace(partOut)) > 0 {
		return errors.New("partial or promisor clones are not supported")
	}
	if err != nil && !isGitConfigNotFound(err) {
		return fmt.Errorf("failed to read partialclone config: %w", err)
	}

	promOut, err := gc.runGit(ctx, "config", "--local", "--get-regexp", `^remote\..*\.promisor$`)
	if err == nil && len(bytes.TrimSpace(promOut)) > 0 {
		return errors.New("partial or promisor clones are not supported")
	}
	if err != nil && !isGitConfigNotFound(err) {
		return fmt.Errorf("failed to read promisor config: %w", err)
	}

	filterOut, err := gc.runGit(ctx, "config", "--local", "--get-regexp", `^remote\..*\.partialclonefilter$`)
	if err == nil && len(bytes.TrimSpace(filterOut)) > 0 {
		return errors.New("partial or promisor clones are not supported")
	}
	if err != nil && !isGitConfigNotFound(err) {
		return fmt.Errorf("failed to read partialclonefilter config: %w", err)
	}

	protoOut, err := gc.runGit(ctx, "config", "--local", "--get-regexp", `^protocol\..*\.allow$`)
	if err == nil && len(bytes.TrimSpace(protoOut)) > 0 {
		return errors.New("local protocol configurations are not supported")
	}
	if err != nil && !isGitConfigNotFound(err) {
		return fmt.Errorf("failed to check protocol configurations: %w", err)
	}

	return nil
}
