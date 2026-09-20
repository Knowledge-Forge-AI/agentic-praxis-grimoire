package evidence_test

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"testing"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/evidence"
)

func TestValidateFinding_Valid(t *testing.T) {
	f := evidence.ReviewFinding{
		FindingID: "F-001",
		Severity:  evidence.SeverityBlocking,
		Category:  evidence.CategoryContractViolation,
		Summary:   "Must reject execution_mode",
		FilePath:  "phase/request.go",
		LineStart: 10,
		LineEnd:   15,
	}
	if err := evidence.ValidateFinding(f); err != nil {
		t.Fatalf("expected valid finding, got: %v", err)
	}
}

func TestValidateFinding_RejectsPathTraversal(t *testing.T) {
	cases := []string{
		"../escape.go",
		"../../foo.go",
		"/etc/passwd",
		"a/../../b.go",
		".",
		"..",
	}
	for _, p := range cases {
		t.Run(p, func(t *testing.T) {
			f := evidence.ReviewFinding{
				FindingID: "F-001",
				Severity:  evidence.SeverityBlocking,
				Category:  evidence.CategoryContractViolation,
				Summary:   "Summary",
				FilePath:  p,
			}
			err := evidence.ValidateFinding(f)
			if err == nil {
				t.Fatalf("expected path traversal error for %q, got nil", p)
			}
			if !errors.Is(err, evidence.ErrPathTraversal) {
				t.Errorf("expected ErrPathTraversal, got: %v", err)
			}
		})
	}
}

func TestValidateDisposition_Valid(t *testing.T) {
	d := evidence.FindingDisposition{
		FindingID: "F-001",
		Action:    evidence.DispositionAmend,
		Basis:     evidence.BasisAcceptedAuthority,
		Rationale: "Amended according to ADR 0066",
	}
	if err := evidence.ValidateDisposition(d); err != nil {
		t.Fatalf("expected valid disposition, got: %v", err)
	}
}

func TestValidateReceipt_Valid(t *testing.T) {
	r := evidence.CompletionReceipt{
		ReceiptID:      "rcpt-1",
		RunID:          "run-1",
		PhaseID:        "APG150",
		CompletedAt:    "2026-09-17T00:00:00Z",
		TerminalStatus: "completed",
		ArchiveSHA256:  "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
	}
	if err := evidence.ValidateReceipt(r); err != nil {
		t.Fatalf("expected valid receipt, got: %v", err)
	}
}

func TestValidateReceipt_InvalidSHA(t *testing.T) {
	r := evidence.CompletionReceipt{
		ReceiptID:      "rcpt-1",
		RunID:          "run-1",
		PhaseID:        "APG150",
		CompletedAt:    "2026-09-17T00:00:00Z",
		TerminalStatus: "completed",
		ArchiveSHA256:  "invalid-not-64-hex",
	}
	if err := evidence.ValidateReceipt(r); err == nil {
		t.Fatal("expected error for invalid sha256, got nil")
	}
}

func TestEvidenceReview_GoldenVectors(t *testing.T) {
	path := filepath.Join("..", "testing", "fixtures", "conformance", "evidence_review_vectors.json")
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("failed to read %s: %v", path, err)
	}

	var fixture struct {
		Severities         []string                    `json:"severities"`
		Categories         []string                    `json:"categories"`
		ReviewOutcomes     []string                    `json:"review_outcomes"`
		DispositionActions []string                    `json:"disposition_actions"`
		DispositionBases   []string                    `json:"disposition_bases"`
		SampleFinding      evidence.ReviewFinding      `json:"sample_finding"`
		SampleDisposition  evidence.FindingDisposition `json:"sample_disposition"`
		SampleReceipt      evidence.CompletionReceipt  `json:"sample_receipt"`
	}

	if err := json.Unmarshal(data, &fixture); err != nil {
		t.Fatalf("failed to parse %s: %v", path, err)
	}

	for _, s := range fixture.Severities {
		if !evidence.ValidSeverity(evidence.FindingSeverity(s)) {
			t.Errorf("severity %q not recognized", s)
		}
	}

	for _, c := range fixture.Categories {
		if !evidence.ValidCategory(evidence.FindingCategory(c)) {
			t.Errorf("category %q not recognized", c)
		}
	}

	for _, a := range fixture.DispositionActions {
		if !evidence.ValidAction(evidence.DispositionAction(a)) {
			t.Errorf("action %q not recognized", a)
		}
	}

	for _, b := range fixture.DispositionBases {
		if !evidence.ValidBasis(evidence.BasisType(b)) {
			t.Errorf("basis %q not recognized", b)
		}
	}

	if err := evidence.ValidateFinding(fixture.SampleFinding); err != nil {
		t.Errorf("sample finding invalid: %v", err)
	}

	if err := evidence.ValidateDisposition(fixture.SampleDisposition); err != nil {
		t.Errorf("sample disposition invalid: %v", err)
	}

	if err := evidence.ValidateReceipt(fixture.SampleReceipt); err != nil {
		t.Errorf("sample receipt invalid: %v", err)
	}
}
