package schema_test

import (
	"encoding/json"
	"testing"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/schema"
)

func TestRecords_RunRecordSerialization(t *testing.T) {
	phaseID := "APG161"
	outcome := "success"
	rec := schema.RunRecord{
		RunID:           "test/APG161/run--1",
		Project:         "test",
		PhaseID:         &phaseID,
		SchemaVersion:   5,
		RequestSchema:   "agent-phase-request-v2",
		RequestDigest:   "abc",
		WorkflowVersion: "v1",
		Lifecycle:       "work-reviewed",
		ExecutionMode:   "gemini_flash_sub",
		CreatedAt:       "2026-09-21T18:00:00Z",
		Status:          "completed",
		Outcome:         &outcome,
	}

	data, err := json.Marshal(rec)
	if err != nil {
		t.Fatalf("failed to marshal RunRecord: %v", err)
	}

	var roundTrip schema.RunRecord
	if err := json.Unmarshal(data, &roundTrip); err != nil {
		t.Fatalf("failed to unmarshal RunRecord: %v", err)
	}

	if roundTrip.RunID != rec.RunID {
		t.Errorf("RunID mismatch: %q vs %q", roundTrip.RunID, rec.RunID)
	}
	if roundTrip.PhaseID == nil || *roundTrip.PhaseID != phaseID {
		t.Errorf("PhaseID mismatch: %v", roundTrip.PhaseID)
	}
	if roundTrip.SemanticOutcome != nil {
		t.Errorf("expected nil SemanticOutcome, got %v", roundTrip.SemanticOutcome)
	}
}

func TestRecords_ReviewMutationObservationRecord(t *testing.T) {
	raw := []byte(`{
		"run_id": "test/APG161/run--1",
		"stage": "produce",
		"sequence": 0,
		"worktree_policy": "warn",
		"index_policy": "block",
		"head_policy": "block",
		"action_taken": "warned",
		"subject_drift_observed": 1,
		"worktree_drift": 1,
		"index_drift": 0,
		"head_drift": 0,
		"recorded_at": "2026-09-21T18:00:00Z",
		"policy_generation": 7,
		"candidate_observation_unavailable": 0,
		"index_observation_unavailable": 0,
		"head_observation_unavailable": 0
	}`)

	var obs schema.ReviewMutationObservationRecord
	if err := json.Unmarshal(raw, &obs); err != nil {
		t.Fatalf("failed to unmarshal observation record: %v", err)
	}

	if obs.RunID != "test/APG161/run--1" || obs.WorktreePolicy != "warn" {
		t.Errorf("unexpected record: %+v", obs)
	}
	if obs.DiagnosticCode != nil {
		t.Errorf("expected nil diagnostic code, got %v", obs.DiagnosticCode)
	}
}

func TestRecords_ReviewMutationPolicyRecord(t *testing.T) {
	raw := []byte(`{
		"run_id": "test/APG161/run--1",
		"source_type": "project",
		"resolved_mode": "normal",
		"policy_generation": 7,
		"is_winner": 1,
		"precedence_rank": 1,
		"resolved_at": "2026-09-21T18:00:00Z"
	}`)

	var pol schema.ReviewMutationPolicyRecord
	if err := json.Unmarshal(raw, &pol); err != nil {
		t.Fatalf("failed to unmarshal policy record: %v", err)
	}

	if pol.WorktreePolicy != nil {
		t.Errorf("expected nullable WorktreePolicy, got %v", *pol.WorktreePolicy)
	}
	if pol.PolicyGeneration != 7 || pol.IsWinner != 1 {
		t.Errorf("unexpected policy fields: %+v", pol)
	}
}

func TestRecords_QuarantineRecords(t *testing.T) {
	rawObs := []byte(`{
		"run_id": "test/APG161/run--1",
		"stage": "produce",
		"sequence": 0,
		"quarantined_at": "2026-09-21T18:00:00Z",
		"quarantine_reason": "orphan"
	}`)

	var qObs schema.LegacyQuarantineObservationRecord
	if err := json.Unmarshal(rawObs, &qObs); err != nil {
		t.Fatalf("failed to unmarshal quarantine observation: %v", err)
	}
	if qObs.QuarantineReason != "orphan" {
		t.Errorf("unexpected quarantine reason: %s", qObs.QuarantineReason)
	}

	rawPol := []byte(`{
		"run_id": "test/APG161/run--1",
		"source_type": "project",
		"quarantined_at": "2026-09-21T18:00:00Z",
		"quarantine_reason": "orphan"
	}`)

	var qPol schema.LegacyQuarantinePolicyRecord
	if err := json.Unmarshal(rawPol, &qPol); err != nil {
		t.Fatalf("failed to unmarshal quarantine policy: %v", err)
	}
	if qPol.QuarantineReason != "orphan" {
		t.Errorf("unexpected quarantine reason: %s", qPol.QuarantineReason)
	}
}
