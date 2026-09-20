package evidence_test

import (
	"encoding/json"
	"errors"
	"os"
	"os/exec"
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

func TestValidateReviewMutationPolicy(t *testing.T) {
	valid := evidence.ReviewMutationPolicy{
		Worktree:   evidence.WorktreeWarn,
		Index:      evidence.GitBlock,
		Head:       evidence.GitBlock,
		Generation: 7,
	}
	if err := evidence.ValidateReviewMutationPolicy(valid); err != nil {
		t.Fatalf("expected valid policy, got: %v", err)
	}

	for _, wt := range []evidence.ReviewMutationWorktreePolicy{evidence.WorktreeBlock, evidence.WorktreeWarn, evidence.WorktreeAllow} {
		p := valid
		p.Worktree = wt
		if err := evidence.ValidateReviewMutationPolicy(p); err != nil {
			t.Errorf("expected valid worktree policy %q, got: %v", wt, err)
		}
	}

	invalidWT := valid
	invalidWT.Worktree = "invalid"
	if err := evidence.ValidateReviewMutationPolicy(invalidWT); err == nil {
		t.Errorf("expected error for invalid worktree policy, got nil")
	}

	invalidIndex := valid
	invalidIndex.Index = "warn"
	if err := evidence.ValidateReviewMutationPolicy(invalidIndex); err == nil {
		t.Errorf("expected error for non-block index policy, got nil")
	}

	invalidHead := valid
	invalidHead.Head = "allow"
	if err := evidence.ValidateReviewMutationPolicy(invalidHead); err == nil {
		t.Errorf("expected error for non-block head policy, got nil")
	}

	invalidGen := valid
	invalidGen.Generation = 0
	if err := evidence.ValidateReviewMutationPolicy(invalidGen); err == nil {
		t.Errorf("expected error for non-positive generation, got nil")
	}
}

func TestReviewMutation_GoldenVectors(t *testing.T) {
	path := filepath.Join("..", "testing", "fixtures", "conformance", "review_mutation_vectors.json")
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("failed to read %s: %v", path, err)
	}

	var fixture struct {
		WorktreePolicies []string `json:"worktree_policies"`
		GitPolicies      []string `json:"git_policies"`
		ActionsTaken     []string `json:"actions_taken"`
		DiagnosticCodes  []string `json:"diagnostic_codes"`
		SamplePolicy     evidence.ReviewMutationPolicy `json:"sample_policy"`
		ValidObservations []struct {
			Name        string                         `json:"name"`
			Observation evidence.ReviewMutationObservation `json:"observation"`
		} `json:"valid_observations"`
		InvalidObservations []struct {
			Name        string                         `json:"name"`
			Observation evidence.ReviewMutationObservation `json:"observation"`
		} `json:"invalid_observations"`
	}

	if err := json.Unmarshal(data, &fixture); err != nil {
		t.Fatalf("failed to parse %s: %v", path, err)
	}

	for _, wt := range fixture.WorktreePolicies {
		if !evidence.ValidWorktreePolicy(evidence.ReviewMutationWorktreePolicy(wt)) {
			t.Errorf("worktree policy %q not recognized", wt)
		}
	}

	for _, act := range fixture.ActionsTaken {
		if !evidence.ValidActionTaken(act) {
			t.Errorf("action %q not recognized", act)
		}
	}

	for _, code := range fixture.DiagnosticCodes {
		if !evidence.ValidDiagnosticCode(code) {
			t.Errorf("diagnostic code %q not recognized", code)
		}
	}

	if err := evidence.ValidateReviewMutationPolicy(fixture.SamplePolicy); err != nil {
		t.Errorf("sample policy invalid: %v", err)
	}

	for _, tc := range fixture.ValidObservations {
		t.Run("valid_"+tc.Name, func(t *testing.T) {
			if err := evidence.ValidateReviewMutationObservation(tc.Observation); err != nil {
				t.Errorf("valid observation %q failed validation: %v", tc.Name, err)
			}
		})
	}

	for _, tc := range fixture.InvalidObservations {
		t.Run("invalid_"+tc.Name, func(t *testing.T) {
			if err := evidence.ValidateReviewMutationObservation(tc.Observation); err == nil {
				t.Errorf("invalid observation %q unexpectedly passed validation", tc.Name)
			}
		})
	}
}

func TestReviewMutation_ActualPythonObserverOutputs(t *testing.T) {
	pythonScript := `
import json, sys
from agent_phase.config_routing import ReviewMutationPolicy
from agent_phase.review_drift import observe_review_drift, apply_review_mutation_policy

scenarios = []

p_warn = ReviewMutationPolicy(worktree="warn", index="block", head="block", generation=7)
obs1 = observe_review_drift(
    ".", stage="work_review",
    before={"tree": "tree1", "index": "idx1", "head": "head1"},
    after={"tree": "tree1", "observation_unavailable": False},
    expected_index="idx1", observed_index="idx1",
    expected_head="head1", observed_head="head1",
    policy=p_warn, role="work_reviewer", subject_kind="work",
    sequence=0, attempt_id="att-clean-1", binding_id="bind-1", attempt_number=1,
)
e1 = apply_review_mutation_policy(obs1, p_warn, raise_on_block=False)
scenarios.append({"name": "clean_observation", "data": e1.as_dict(), "should_pass": True})

p_block = ReviewMutationPolicy(worktree="block", index="block", head="block", generation=7)
obs2 = observe_review_drift(
    ".", stage="work_review",
    before={"tree": "tree1", "index": "idx1", "head": "head1"},
    after={"tree": "tree2", "observation_unavailable": False},
    expected_index="idx1", observed_index="idx1",
    expected_head="head1", observed_head="head1",
    policy=p_block, role="work_reviewer", subject_kind="work",
    sequence=1, attempt_id="att-wt-block", binding_id="bind-1", attempt_number=1,
)
obs2.worktree_paths = ["file_modified.py"]
e2 = apply_review_mutation_policy(obs2, p_block, raise_on_block=False)
scenarios.append({"name": "worktree_drift_blocked", "data": e2.as_dict(), "should_pass": True})

obs3 = observe_review_drift(
    ".", stage="work_review",
    before={"tree": "tree1", "index": "idx1", "head": "head1"},
    after={"tree": "tree2", "observation_unavailable": False},
    expected_index="idx1", observed_index="idx1",
    expected_head="head1", observed_head="head1",
    policy=p_warn, role="work_reviewer", subject_kind="work",
    sequence=2, attempt_id="att-wt-warn", binding_id="bind-1", attempt_number=1,
)
obs3.worktree_paths = ["notes.txt"]
e3 = apply_review_mutation_policy(obs3, p_warn, raise_on_block=False)
scenarios.append({"name": "worktree_drift_warned", "data": e3.as_dict(), "should_pass": True})

p_allow = ReviewMutationPolicy(worktree="allow", index="block", head="block", generation=7)
obs4 = observe_review_drift(
    ".", stage="work_review",
    before={"tree": "tree1", "index": "idx1", "head": "head1"},
    after={"tree": "tree2", "observation_unavailable": False},
    expected_index="idx1", observed_index="idx1",
    expected_head="head1", observed_head="head1",
    policy=p_allow, role="work_reviewer", subject_kind="work",
    sequence=3, attempt_id="att-wt-allow", binding_id="bind-1", attempt_number=1,
)
obs4.worktree_paths = ["allowed.md"]
e4 = apply_review_mutation_policy(obs4, p_allow, raise_on_block=False)
scenarios.append({"name": "worktree_drift_allowed", "data": e4.as_dict(), "should_pass": True})

obs5 = observe_review_drift(
    ".", stage="work_review",
    before={"tree": "tree1", "index": "idx1", "head": "head1"},
    after={"tree": "tree1", "observation_unavailable": False},
    expected_index="idx1", observed_index="idx2",
    expected_head="head1", observed_head="head1",
    policy=p_warn, role="work_reviewer", subject_kind="work",
    sequence=4, attempt_id="att-idx-block", binding_id="bind-1", attempt_number=1,
)
obs5.index_paths = ["staged.py"]
e5 = apply_review_mutation_policy(obs5, p_warn, raise_on_block=False)
scenarios.append({"name": "index_drift_blocked", "data": e5.as_dict(), "should_pass": True})

obs6 = observe_review_drift(
    ".", stage="work_review",
    before={"tree": "tree1", "index": "idx1", "head": "head1"},
    after={"tree": "tree1", "observation_unavailable": False},
    expected_index="idx1", observed_index="idx1",
    expected_head="head1", observed_head="head2",
    policy=p_warn, role="work_reviewer", subject_kind="work",
    sequence=5, attempt_id="att-hd-block", binding_id="bind-1", attempt_number=1,
)
e6 = apply_review_mutation_policy(obs6, p_warn, raise_on_block=False)
scenarios.append({"name": "head_drift_blocked", "data": e6.as_dict(), "should_pass": True})

obs7 = observe_review_drift(
    ".", stage="work_review",
    before={"tree": "tree1", "index": "idx1", "head": "head1"},
    after={"tree": "tree1", "observation_unavailable": True},
    expected_index="idx1", observed_index="idx1",
    expected_head="head1", observed_head="head1",
    policy=p_warn, role="work_reviewer", subject_kind="work",
    sequence=6, attempt_id="att-cand-unavail", binding_id="bind-1", attempt_number=1,
)
e7 = apply_review_mutation_policy(obs7, p_warn, raise_on_block=False)
scenarios.append({"name": "candidate_unavailable_blocked", "data": e7.as_dict(), "should_pass": True})

obs8 = observe_review_drift(
    ".", stage="work_review",
    before={"tree": "tree1", "index": "idx1", "head": "head1"},
    after={"tree": "tree1", "observation_unavailable": False},
    expected_index="idx1", observed_index=None,
    expected_head="head1", observed_head="head1",
    policy=p_warn, role="work_reviewer", subject_kind="work",
    sequence=7, attempt_id="att-idx-unavail", binding_id="bind-1", attempt_number=1,
)
obs8.index_observation_unavailable = True
e8 = apply_review_mutation_policy(obs8, p_warn, raise_on_block=False)
scenarios.append({"name": "index_unavailable_blocked", "data": e8.as_dict(), "should_pass": True})

obs9 = observe_review_drift(
    ".", stage="work_review",
    before={"tree": "tree1", "index": "idx1", "head": "head1"},
    after={"tree": "tree1", "observation_unavailable": False},
    expected_index="idx1", observed_index="idx1",
    expected_head="head1", observed_head=None,
    policy=p_warn, role="work_reviewer", subject_kind="work",
    sequence=8, attempt_id="att-hd-unavail", binding_id="bind-1", attempt_number=1,
)
obs9.head_observation_unavailable = True
e9 = apply_review_mutation_policy(obs9, p_warn, raise_on_block=False)
scenarios.append({"name": "head_unavailable_blocked", "data": e9.as_dict(), "should_pass": True})

obs10 = observe_review_drift(
    ".", stage="work_review",
    before={"tree": "tree1", "index": "idx1", "head": "head1"},
    after={"tree": "tree2", "observation_unavailable": False},
    expected_index="idx1", observed_index="idx1",
    expected_head="head1", observed_head="head1",
    policy=p_warn, role="work_reviewer", subject_kind="work",
    sequence=9, attempt_id="att-nonzero-transport", binding_id="bind-1", attempt_number=1,
    transport={"exit_code": 127, "signal": None, "duration_ms": 1500},
)
obs10.worktree_paths = ["crash.log"]
e10 = apply_review_mutation_policy(obs10, p_warn, raise_on_block=False)
scenarios.append({"name": "transport_nonzero_with_drift", "data": e10.as_dict(), "should_pass": True})

bad_data = dict(e2.as_dict())
bad_data["subject_drift_observed"] = False
scenarios.append({"name": "inconsistent_drift_tampered", "data": bad_data, "should_pass": False})

print(json.dumps(scenarios))
`

	cmd := exec.Command("python3", "-c", pythonScript)
	cmd.Env = append(os.Environ(), "PYTHONPATH="+filepath.Join("..", "libexec"))
	out, err := cmd.Output()
	if err != nil {
		t.Fatalf("python observer script execution failed: %v", err)
	}

	var rawScenarios []struct {
		Name       string          `json:"name"`
		Data       json.RawMessage `json:"data"`
		ShouldPass bool            `json:"should_pass"`
	}
	if err := json.Unmarshal(out, &rawScenarios); err != nil {
		t.Fatalf("failed to decode python output: %v", err)
	}

	for _, sc := range rawScenarios {
		t.Run("actual_py_"+sc.Name, func(t *testing.T) {
			var obs evidence.ReviewMutationObservation
			if err := json.Unmarshal(sc.Data, &obs); err != nil {
				t.Fatalf("failed to unmarshal observation into Go struct: %v", err)
			}
			err := evidence.ValidateReviewMutationObservation(obs)
			if sc.ShouldPass && err != nil {
				t.Errorf("expected observation %q to pass validation, got: %v", sc.Name, err)
			}
			if !sc.ShouldPass && err == nil {
				t.Errorf("expected observation %q to fail validation, unexpectedly passed", sc.Name)
			}
		})
	}
}

