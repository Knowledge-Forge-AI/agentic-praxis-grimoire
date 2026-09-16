package evidence

import (
	"errors"
	"fmt"
	"strings"
)

// ReviewOutcome represents the result classification of a review attempt.
type ReviewOutcome string

const (
	OutcomeReviewedWithNoFindings ReviewOutcome = "reviewed_with_no_findings"
	OutcomeReviewedWithFindings   ReviewOutcome = "reviewed_with_findings"
	OutcomeUnreviewable           ReviewOutcome = "unreviewable"
)

// ValidReviewOutcome reports whether o is one of the three canonical review outcomes.
func ValidReviewOutcome(o ReviewOutcome) bool {
	switch o {
	case OutcomeReviewedWithNoFindings, OutcomeReviewedWithFindings, OutcomeUnreviewable:
		return true
	default:
		return false
	}
}

// ReviewBinding links a review execution attempt with candidate identity, outcome, and findings.
type ReviewBinding struct {
	ReviewID         string          `json:"review_id"`
	RunID            string          `json:"run_id"`
	CandidateID      string          `json:"candidate_id"`
	ReviewerProvider string          `json:"reviewer_provider"`
	ReviewerProfile  string          `json:"reviewer_profile"`
	Outcome          ReviewOutcome   `json:"outcome"`
	Findings         []ReviewFinding `json:"findings,omitempty"`
}

// ValidateReviewBinding validates structural consistency of a ReviewBinding.
func ValidateReviewBinding(rb ReviewBinding) error {
	if strings.TrimSpace(rb.ReviewID) == "" {
		return errors.New("evidence: review_id must be non-empty")
	}
	if strings.TrimSpace(rb.RunID) == "" {
		return errors.New("evidence: run_id must be non-empty")
	}
	if strings.TrimSpace(rb.CandidateID) == "" {
		return errors.New("evidence: candidate_id must be non-empty")
	}
	if !ValidReviewOutcome(rb.Outcome) {
		return fmt.Errorf("evidence: invalid review outcome: %q", rb.Outcome)
	}
	for i, f := range rb.Findings {
		if err := ValidateFinding(f); err != nil {
			return fmt.Errorf("evidence: finding %d invalid: %w", i, err)
		}
	}
	if rb.Outcome == OutcomeReviewedWithNoFindings && len(rb.Findings) > 0 {
		return errors.New("evidence: outcome reviewed_with_no_findings cannot have findings")
	}
	return nil
}
