package evidence

import (
	"errors"
	"fmt"
)

// ReviewMutationWorktreePolicy defines the policy for review-stage worktree changes.
type ReviewMutationWorktreePolicy string

const (
	WorktreeBlock ReviewMutationWorktreePolicy = "block"
	WorktreeWarn  ReviewMutationWorktreePolicy = "warn"
	WorktreeAllow ReviewMutationWorktreePolicy = "allow"
)

// ReviewMutationGitPolicy defines the strict policy for index and HEAD changes.
type ReviewMutationGitPolicy string

const (
	GitBlock ReviewMutationGitPolicy = "block"
)

var (
	ErrInvalidWorktreePolicy = errors.New("evidence: invalid worktree review mutation policy")
	ErrInvalidGitPolicy      = errors.New("evidence: index and head review mutation policies must be 'block'")
	ErrInvalidGeneration     = errors.New("evidence: review mutation policy generation must be positive")
)

// ReviewMutationPolicy defines the complete tri-state policy across worktree, index, and head.
type ReviewMutationPolicy struct {
	Worktree   ReviewMutationWorktreePolicy `json:"worktree"`
	Index      ReviewMutationGitPolicy      `json:"index"`
	Head       ReviewMutationGitPolicy      `json:"head"`
	Generation int                          `json:"generation"`
}

// ValidWorktreePolicy reports whether p is a supported worktree policy.
func ValidWorktreePolicy(p ReviewMutationWorktreePolicy) bool {
	switch p {
	case WorktreeBlock, WorktreeWarn, WorktreeAllow:
		return true
	default:
		return false
	}
}

// ValidateReviewMutationPolicy validates that the policy contains a valid worktree choice,
// strictly 'block' for index and head, and positive generation.
func ValidateReviewMutationPolicy(p ReviewMutationPolicy) error {
	if !ValidWorktreePolicy(p.Worktree) {
		return fmt.Errorf("%w: %q", ErrInvalidWorktreePolicy, p.Worktree)
	}
	if p.Index != GitBlock {
		return fmt.Errorf("%w: index=%q", ErrInvalidGitPolicy, p.Index)
	}
	if p.Head != GitBlock {
		return fmt.Errorf("%w: head=%q", ErrInvalidGitPolicy, p.Head)
	}
	if p.Generation <= 0 {
		return fmt.Errorf("%w: got %d", ErrInvalidGeneration, p.Generation)
	}
	return nil
}
