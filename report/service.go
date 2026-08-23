package report

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/internal/gitexec"
)

// New validates an exact Git worktree root and returns a reusable service.
func New(options Options) (*Service, error) {
	if options.Repository == "" || !filepath.IsAbs(options.Repository) || filepath.Clean(options.Repository) != options.Repository {
		return nil, fmt.Errorf("%w: repository must be an absolute clean path", ErrInvalidRequest)
	}
	metadata, err := os.Lstat(options.Repository)
	if err != nil || !metadata.IsDir() || metadata.Mode()&os.ModeSymlink != 0 {
		return nil, fmt.Errorf("%w: repository root is unavailable or unsafe", ErrUnsafePath)
	}
	resolved, err := filepath.EvalSymlinks(options.Repository)
	if err != nil || resolved != options.Repository {
		return nil, fmt.Errorf("%w: repository root contains ambiguous links", ErrUnsafePath)
	}
	gitPath := options.GitPath
	if gitPath == "" {
		gitPath = "git"
	} else {
		if !filepath.IsAbs(gitPath) || filepath.Clean(gitPath) != gitPath {
			return nil, fmt.Errorf("%w: Git path must be an absolute clean path", ErrInvalidRequest)
		}
		gitMetadata, statErr := os.Lstat(gitPath)
		if statErr != nil || !gitMetadata.Mode().IsRegular() || gitMetadata.Mode()&os.ModeSymlink != 0 {
			return nil, fmt.Errorf("%w: Git path is not a direct regular file", ErrUnsafePath)
		}
	}
	runner := gitexec.New(options.Repository, gitPath)
	result, err := runner.Run(context.Background(), []string{"rev-parse", "--show-toplevel"}, nil, nil)
	if err != nil {
		return nil, fmt.Errorf("%w: Git root discovery failed", ErrRepository)
	}
	discovered := strings.TrimSuffix(string(result.Stdout), "\n")
	if discovered != options.Repository {
		return nil, fmt.Errorf("%w: repository is not the exact worktree root", ErrRepository)
	}
	return &Service{repository: options.Repository, git: runner}, nil
}

func (service *Service) runGit(ctx context.Context, arguments []string, environment map[string]string, input []byte, family error) ([]byte, error) {
	result, err := service.git.Run(ctx, arguments, environment, input)
	if err != nil {
		if contextErr := ctx.Err(); contextErr != nil {
			return nil, contextErr
		}
		return nil, fmt.Errorf("%w: native Git collection failed", family)
	}
	return result.Stdout, nil
}

func (service *Service) runGitResult(ctx context.Context, arguments []string, environment map[string]string, input []byte) (gitexec.Result, error) {
	result, err := service.git.Run(ctx, arguments, environment, input)
	if contextErr := ctx.Err(); contextErr != nil {
		return result, contextErr
	}
	return result, err
}
