package evidence

import (
	"errors"
	"fmt"
	"path"
	"strings"
)

// FindingSeverity represents the severity level of a review finding.
type FindingSeverity string

const (
	SeverityBlocking    FindingSeverity = "blocking"
	SeveritySubstantive FindingSeverity = "substantive"
	SeverityAdvisory    FindingSeverity = "advisory"
)

// FindingCategory represents the domain category of a review finding.
type FindingCategory string

const (
	CategoryCorrectness       FindingCategory = "correctness"
	CategoryContractViolation FindingCategory = "contract_violation"
	CategorySecurity          FindingCategory = "security"
	CategoryScope             FindingCategory = "scope"
	CategoryEvidence          FindingCategory = "evidence"
	CategoryClarity           FindingCategory = "clarity"
)

var (
	ErrInvalidSeverity = errors.New("evidence: invalid finding severity")
	ErrInvalidCategory = errors.New("evidence: invalid finding category")
	ErrEmptySummary    = errors.New("evidence: finding summary must be non-empty")
	ErrPathTraversal   = errors.New("evidence: finding file path contains traversal elements")
)

// ReviewFinding represents a structured finding reported by a Plan Reviewer or Work Reviewer.
type ReviewFinding struct {
	FindingID string          `json:"finding_id"`
	Severity  FindingSeverity `json:"severity"`
	Category  FindingCategory `json:"category"`
	Summary   string          `json:"summary"`
	FilePath  string          `json:"file_path,omitempty"`
	LineStart int             `json:"line_start,omitempty"`
	LineEnd   int             `json:"line_end,omitempty"`
}

// ValidSeverity reports whether s is one of the three canonical severities.
func ValidSeverity(s FindingSeverity) bool {
	switch s {
	case SeverityBlocking, SeveritySubstantive, SeverityAdvisory:
		return true
	default:
		return false
	}
}

// ValidCategory reports whether c is one of the six canonical finding categories.
func ValidCategory(c FindingCategory) bool {
	switch c {
	case CategoryCorrectness, CategoryContractViolation, CategorySecurity,
		CategoryScope, CategoryEvidence, CategoryClarity:
		return true
	default:
		return false
	}
}

// ValidateFinding validates boundary invariants on a ReviewFinding.
func ValidateFinding(f ReviewFinding) error {
	if strings.TrimSpace(f.FindingID) == "" {
		return errors.New("evidence: finding_id must be non-empty")
	}
	if !ValidSeverity(f.Severity) {
		return fmt.Errorf("%w: %q", ErrInvalidSeverity, f.Severity)
	}
	if !ValidCategory(f.Category) {
		return fmt.Errorf("%w: %q", ErrInvalidCategory, f.Category)
	}
	if strings.TrimSpace(f.Summary) == "" {
		return ErrEmptySummary
	}
	if len(f.Summary) > 4096 {
		return errors.New("evidence: finding summary exceeds maximum length of 4096 bytes")
	}
	if f.FilePath != "" {
		cleaned := path.Clean(filepathToSlash(f.FilePath))
		if cleaned == "." || cleaned == ".." || strings.HasPrefix(cleaned, "../") || strings.HasPrefix(cleaned, "/") {
			return fmt.Errorf("%w: %q", ErrPathTraversal, f.FilePath)
		}
	}
	if f.LineStart < 0 || f.LineEnd < 0 {
		return errors.New("evidence: line numbers cannot be negative")
	}
	if f.LineEnd > 0 && f.LineStart > f.LineEnd {
		return errors.New("evidence: line_start cannot exceed line_end")
	}
	return nil
}

func filepathToSlash(p string) string {
	return strings.ReplaceAll(p, "\\", "/")
}
