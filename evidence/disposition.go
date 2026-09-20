package evidence

import (
	"errors"
	"fmt"
	"strings"
)

// DispositionAction represents the disposition action taken on a review finding.
type DispositionAction string

const (
	DispositionAccept DispositionAction = "accept"
	DispositionAmend  DispositionAction = "amend"
	DispositionReject DispositionAction = "reject"
	DispositionDefer  DispositionAction = "defer"
)

// BasisType represents the authoritative rationale basis for the disposition.
type BasisType string

const (
	BasisAcceptedAuthority BasisType = "accepted_authority"
	BasisCanonicalEvidence BasisType = "canonical_evidence"
	BasisScopeOwner        BasisType = "scope_owner"
	BasisNone              BasisType = "none"
)

var (
	ErrInvalidAction  = errors.New("evidence: invalid disposition action")
	ErrInvalidBasis   = errors.New("evidence: invalid disposition basis")
	ErrEmptyRationale = errors.New("evidence: disposition rationale must be non-empty")
)

// FindingDisposition records the single-source disposition of a review finding.
type FindingDisposition struct {
	FindingID string            `json:"finding_id"`
	Action    DispositionAction `json:"action"`
	Basis     BasisType         `json:"basis"`
	Rationale string            `json:"rationale"`
}

// ValidAction reports whether a is one of the four canonical disposition actions.
func ValidAction(a DispositionAction) bool {
	switch a {
	case DispositionAccept, DispositionAmend, DispositionReject, DispositionDefer:
		return true
	default:
		return false
	}
}

// ValidBasis reports whether b is one of the four canonical basis types.
func ValidBasis(b BasisType) bool {
	switch b {
	case BasisAcceptedAuthority, BasisCanonicalEvidence, BasisScopeOwner, BasisNone:
		return true
	default:
		return false
	}
}

// ValidateDisposition validates invariants on a FindingDisposition.
func ValidateDisposition(d FindingDisposition) error {
	if strings.TrimSpace(d.FindingID) == "" {
		return errors.New("evidence: finding_id must be non-empty")
	}
	if !ValidAction(d.Action) {
		return fmt.Errorf("%w: %q", ErrInvalidAction, d.Action)
	}
	if !ValidBasis(d.Basis) {
		return fmt.Errorf("%w: %q", ErrInvalidBasis, d.Basis)
	}
	if strings.TrimSpace(d.Rationale) == "" {
		return ErrEmptyRationale
	}
	return nil
}
