package candidate

import (
	"errors"
	"fmt"
	"strings"
)

// CandidateIdentity represents an immutable proposed workspace state produced by a mutating role.
type CandidateIdentity struct {
	CandidateID       string  `json:"candidate_id"`
	Generation        int     `json:"generation"`
	ProducerRole      string  `json:"producer_role"`
	ProducerAttemptID string  `json:"producer_attempt_id"`
	PredecessorID     *string `json:"predecessor_id,omitempty"`
	Commit            string  `json:"commit,omitempty"`
	TreeDigest        string  `json:"tree_digest,omitempty"`
	ExpectedBase      string  `json:"expected_base,omitempty"`
}

// ValidateCandidate validates structural invariants on CandidateIdentity.
func ValidateCandidate(c CandidateIdentity) error {
	if strings.TrimSpace(c.CandidateID) == "" {
		return errors.New("candidate: candidate_id must be non-empty")
	}
	if c.Generation < 0 {
		return errors.New("candidate: generation cannot be negative")
	}
	if strings.TrimSpace(c.ProducerRole) == "" {
		return errors.New("candidate: producer_role must be non-empty")
	}
	if strings.TrimSpace(c.ProducerAttemptID) == "" {
		return errors.New("candidate: producer_attempt_id must be non-empty")
	}
	if c.Commit != "" && !isValidHexDigest(c.Commit, 40) && !isValidHexDigest(c.Commit, 64) {
		return fmt.Errorf("candidate: invalid commit hash format: %q", c.Commit)
	}
	if c.TreeDigest != "" && !isValidHexDigest(c.TreeDigest, 40) && !isValidHexDigest(c.TreeDigest, 64) {
		return fmt.Errorf("candidate: invalid tree digest format: %q", c.TreeDigest)
	}
	if c.ExpectedBase != "" && !isValidHexDigest(c.ExpectedBase, 40) && !isValidHexDigest(c.ExpectedBase, 64) {
		return fmt.Errorf("candidate: invalid expected_base hash format: %q", c.ExpectedBase)
	}
	return nil
}

func isValidHexDigest(s string, length int) bool {
	if len(s) != length {
		return false
	}
	for _, c := range s {
		if !((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f')) {
			return false
		}
	}
	return true
}
