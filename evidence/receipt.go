package evidence

import (
	"errors"
	"fmt"
	"strings"
)

// CompletionReceipt represents a verifiable finalization receipt for a completed phase run.
type CompletionReceipt struct {
	ReceiptID      string `json:"receipt_id"`
	RunID          string `json:"run_id"`
	PhaseID        string `json:"phase_id"`
	CompletedAt    string `json:"completed_at"`
	TerminalStatus string `json:"terminal_status"`
	ArchiveSHA256  string `json:"archive_sha256"`
}

// ValidateReceipt checks structural validity and SHA-256 formatting of a CompletionReceipt.
func ValidateReceipt(r CompletionReceipt) error {
	if strings.TrimSpace(r.ReceiptID) == "" {
		return errors.New("evidence: receipt_id must be non-empty")
	}
	if strings.TrimSpace(r.RunID) == "" {
		return errors.New("evidence: run_id must be non-empty")
	}
	if strings.TrimSpace(r.PhaseID) == "" {
		return errors.New("evidence: phase_id must be non-empty")
	}
	if strings.TrimSpace(r.CompletedAt) == "" {
		return errors.New("evidence: completed_at must be non-empty")
	}
	if strings.TrimSpace(r.TerminalStatus) == "" {
		return errors.New("evidence: terminal_status must be non-empty")
	}
	if len(r.ArchiveSHA256) != 64 {
		return fmt.Errorf("evidence: archive_sha256 must be 64 hexadecimal chars, got %d", len(r.ArchiveSHA256))
	}
	for _, c := range r.ArchiveSHA256 {
		if !((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f')) {
			return fmt.Errorf("evidence: archive_sha256 contains non-hexadecimal character: %c", c)
		}
	}
	return nil
}
