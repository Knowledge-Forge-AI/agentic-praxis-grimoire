package evidence

import (
	"encoding/json"
	"errors"
	"fmt"
	"path"
	"strings"
)

const (
	// ReviewMutationObservationSchema is the canonical schema identifier for review mutation observations.
	ReviewMutationObservationSchema = "agent-phase-review-mutation-observation-v1"

	// Canonical diagnostic codes for review-stage mutation.
	DiagnosticMutatedCandidate = "READ_ONLY_STAGE_MUTATED_CANDIDATE"
	DiagnosticMutatedIndex     = "READ_ONLY_STAGE_MUTATED_INDEX"
	DiagnosticMutatedHead      = "READ_ONLY_STAGE_MUTATED_HEAD"

	// Actions taken by the review mutation policy evaluator.
	ActionBlocked = "blocked"
	ActionWarned  = "warned"
	ActionAllowed = "allowed"
	ActionNone    = "none"
)

var (
	ErrEmptyStage                 = errors.New("evidence: stage must be non-empty")
	ErrInvalidSchema              = errors.New("evidence: invalid review mutation observation schema")
	ErrInvalidDiagnosticCode      = errors.New("evidence: invalid diagnostic code")
	ErrInvalidActionTaken         = errors.New("evidence: invalid action taken")
	ErrInconsistentActionTaken    = errors.New("evidence: action taken is inconsistent with drift and policy")
	ErrInconsistentDiagnosticCode = errors.New("evidence: diagnostic code is inconsistent with observed drift")
	ErrInconsistentDriftFlag      = errors.New("evidence: subject_drift_observed flag is inconsistent with observed drift")
)

// ObservationLimitation captures a limitation recorded during turn observation.
type ObservationLimitation struct {
	Kind   string `json:"kind"`
	Detail string `json:"detail"`
}

// ReviewMutationObservation captures observed drift and policy disposition for a read-only review stage.
type ReviewMutationObservation struct {
	Schema                          string                  `json:"schema,omitempty"`
	Stage                           string                  `json:"stage"`
	AttemptID                       string                  `json:"attempt_id,omitempty"`
	BindingID                       string                  `json:"binding_id,omitempty"`
	AttemptNumber                   int                     `json:"attempt_number,omitempty"`
	Role                            string                  `json:"role,omitempty"`
	SubjectKind                     string                  `json:"subject_kind,omitempty"`
	Limitations                     []ObservationLimitation `json:"limitations,omitempty"`
	Policy                          ReviewMutationPolicy    `json:"policy"`
	PolicyGeneration                int                     `json:"policy_generation,omitempty"`
	RawStdoutArtifact               string                  `json:"raw_stdout_artifact,omitempty"`
	RawStderrArtifact               string                  `json:"raw_stderr_artifact,omitempty"`
	SubjectDriftObserved            bool                    `json:"subject_drift_observed"`
	WorktreeDrift                   bool                    `json:"worktree_drift"`
	IndexDrift                      bool                    `json:"index_drift"`
	HeadDrift                       bool                    `json:"head_drift"`
	CandidateObservationUnavailable bool                    `json:"candidate_observation_unavailable,omitempty"`
	IndexObservationUnavailable     bool                    `json:"index_observation_unavailable,omitempty"`
	HeadObservationUnavailable      bool                    `json:"head_observation_unavailable,omitempty"`
	WorktreePaths                   []string                `json:"worktree_paths,omitempty"`
	IndexPaths                      []string                `json:"index_paths,omitempty"`
	ExpectedTree                    string                  `json:"expected_tree,omitempty"`
	ObservedTree                    string                  `json:"observed_tree,omitempty"`
	ExpectedIndex                   json.RawMessage         `json:"expected_index,omitempty"`
	ObservedIndex                   json.RawMessage         `json:"observed_index,omitempty"`
	ExpectedHead                    string                  `json:"expected_head,omitempty"`
	ObservedHead                    string                  `json:"observed_head,omitempty"`
	DiagnosticCode                  string                  `json:"diagnostic_code,omitempty"`
	ActionTaken                     string                  `json:"action_taken"`
	Sequence                        int                     `json:"sequence,omitempty"`
	PathsComplete                   bool                    `json:"paths_complete,omitempty"`
	Detail                          string                  `json:"detail,omitempty"`
	Transport                       json.RawMessage         `json:"transport,omitempty"`
	Paths                           []string                `json:"paths,omitempty"`
	Code                            string                  `json:"code,omitempty"`
}

// ValidDiagnosticCode reports whether code is a recognized diagnostic code or empty.
func ValidDiagnosticCode(code string) bool {
	switch code {
	case "", DiagnosticMutatedCandidate, DiagnosticMutatedIndex, DiagnosticMutatedHead:
		return true
	default:
		return false
	}
}

// ValidActionTaken reports whether action is a recognized policy evaluation action.
func ValidActionTaken(action string) bool {
	switch action {
	case ActionBlocked, ActionWarned, ActionAllowed, ActionNone:
		return true
	default:
		return false
	}
}

// ValidateReviewMutationObservation validates the structural invariants and logical consistency
// of a ReviewMutationObservation.
func ValidateReviewMutationObservation(obs ReviewMutationObservation) error {
	if strings.TrimSpace(obs.Stage) == "" {
		return ErrEmptyStage
	}
	if obs.Schema != "" && obs.Schema != ReviewMutationObservationSchema {
		return fmt.Errorf("%w: %q, expected %q", ErrInvalidSchema, obs.Schema, ReviewMutationObservationSchema)
	}
	if err := ValidateReviewMutationPolicy(obs.Policy); err != nil {
		return fmt.Errorf("evidence: invalid policy in observation: %w", err)
	}
	if !ValidActionTaken(obs.ActionTaken) {
		return fmt.Errorf("%w: %q", ErrInvalidActionTaken, obs.ActionTaken)
	}
	if obs.DiagnosticCode == "" && obs.Code != "" {
		obs.DiagnosticCode = obs.Code
	}
	if !ValidDiagnosticCode(obs.DiagnosticCode) {
		return fmt.Errorf("%w: %q", ErrInvalidDiagnosticCode, obs.DiagnosticCode)
	}

	if len(obs.WorktreePaths) == 0 && len(obs.Paths) > 0 {
		obs.WorktreePaths = obs.Paths
	}
	for i, p := range obs.WorktreePaths {
		cleaned := path.Clean(filepathToSlash(p))
		if cleaned == "." || cleaned == ".." || strings.HasPrefix(cleaned, "../") || strings.HasPrefix(cleaned, "/") {
			return fmt.Errorf("%w in worktree path %d: %q", ErrPathTraversal, i, p)
		}
	}
	for i, p := range obs.IndexPaths {
		cleaned := path.Clean(filepathToSlash(p))
		if cleaned == "." || cleaned == ".." || strings.HasPrefix(cleaned, "../") || strings.HasPrefix(cleaned, "/") {
			return fmt.Errorf("%w in index path %d: %q", ErrPathTraversal, i, p)
		}
	}

	anyDrift := obs.WorktreeDrift || obs.IndexDrift || obs.HeadDrift
	if obs.SubjectDriftObserved != anyDrift {
		return fmt.Errorf("%w: subject_drift_observed=%v, actual any_drift=%v",
			ErrInconsistentDriftFlag, obs.SubjectDriftObserved, anyDrift)
	}

	anyUnavailable := obs.CandidateObservationUnavailable || obs.IndexObservationUnavailable || obs.HeadObservationUnavailable

	if !anyDrift && !anyUnavailable {
		if obs.ActionTaken != ActionNone {
			return fmt.Errorf("%w: expected %q for no drift, got %q",
				ErrInconsistentActionTaken, ActionNone, obs.ActionTaken)
		}
		if obs.DiagnosticCode != "" {
			return fmt.Errorf("%w: expected empty diagnostic code for no drift, got %q",
				ErrInconsistentDiagnosticCode, obs.DiagnosticCode)
		}
		return nil
	}

	// Drift or unavailability was observed. Index or Head drift/unavailability is always fail-closed (blocked).
	if obs.HeadDrift || obs.HeadObservationUnavailable {
		if obs.ActionTaken != ActionBlocked {
			return fmt.Errorf("%w: head drift or unavailability must be blocked, got %q", ErrInconsistentActionTaken, obs.ActionTaken)
		}
		if obs.DiagnosticCode != DiagnosticMutatedHead {
			return fmt.Errorf("%w: head drift or unavailability diagnostic must be %q, got %q",
				ErrInconsistentDiagnosticCode, DiagnosticMutatedHead, obs.DiagnosticCode)
		}
		return nil
	}

	if obs.IndexDrift || obs.IndexObservationUnavailable {
		if obs.ActionTaken != ActionBlocked {
			return fmt.Errorf("%w: index drift or unavailability must be blocked, got %q", ErrInconsistentActionTaken, obs.ActionTaken)
		}
		if obs.DiagnosticCode != DiagnosticMutatedIndex {
			return fmt.Errorf("%w: index drift or unavailability diagnostic must be %q, got %q",
				ErrInconsistentDiagnosticCode, DiagnosticMutatedIndex, obs.DiagnosticCode)
		}
		return nil
	}

	if obs.CandidateObservationUnavailable {
		if obs.ActionTaken != ActionBlocked {
			return fmt.Errorf("%w: candidate observation unavailability must be blocked, got %q", ErrInconsistentActionTaken, obs.ActionTaken)
		}
		if obs.DiagnosticCode != DiagnosticMutatedCandidate {
			return fmt.Errorf("%w: candidate observation unavailability diagnostic must be %q, got %q",
				ErrInconsistentDiagnosticCode, DiagnosticMutatedCandidate, obs.DiagnosticCode)
		}
		return nil
	}

	// Only Worktree drift observed.
	switch obs.Policy.Worktree {
	case WorktreeBlock:
		if obs.ActionTaken != ActionBlocked {
			return fmt.Errorf("%w: policy block requires action %q, got %q",
				ErrInconsistentActionTaken, ActionBlocked, obs.ActionTaken)
		}
		if obs.DiagnosticCode != DiagnosticMutatedCandidate {
			return fmt.Errorf("%w: worktree block diagnostic must be %q, got %q",
				ErrInconsistentDiagnosticCode, DiagnosticMutatedCandidate, obs.DiagnosticCode)
		}
	case WorktreeWarn:
		if obs.ActionTaken != ActionWarned {
			return fmt.Errorf("%w: policy warn requires action %q, got %q",
				ErrInconsistentActionTaken, ActionWarned, obs.ActionTaken)
		}
		if obs.DiagnosticCode != DiagnosticMutatedCandidate {
			return fmt.Errorf("%w: worktree warn diagnostic must be %q, got %q",
				ErrInconsistentDiagnosticCode, DiagnosticMutatedCandidate, obs.DiagnosticCode)
		}
	case WorktreeAllow:
		if obs.ActionTaken != ActionAllowed {
			return fmt.Errorf("%w: policy allow requires action %q, got %q",
				ErrInconsistentActionTaken, ActionAllowed, obs.ActionTaken)
		}
		// Under allow, diagnostic code can be DiagnosticMutatedCandidate or empty
		if obs.DiagnosticCode != "" && obs.DiagnosticCode != DiagnosticMutatedCandidate {
			return fmt.Errorf("%w: worktree allow diagnostic must be empty or %q, got %q",
				ErrInconsistentDiagnosticCode, DiagnosticMutatedCandidate, obs.DiagnosticCode)
		}
	}

	return nil
}
