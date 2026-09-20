package schema

// RunRecord represents a row in the runs table.
type RunRecord struct {
	RunID               string  `json:"run_id"`
	Project             string  `json:"project"`
	PhaseID             *string `json:"phase_id,omitempty"`
	SchemaVersion       int     `json:"schema_version"`
	RequestSchema       string  `json:"request_schema"`
	RequestDigest       string  `json:"request_digest"`
	WorkflowVersion     string  `json:"workflow_version"`
	Lifecycle           string  `json:"lifecycle"`
	ExecutionMode       string  `json:"execution_mode"`
	CreatedAt           string  `json:"created_at"`
	Status              string  `json:"status"`
	Outcome             *string `json:"outcome,omitempty"`
	SemanticOutcome     *string `json:"semantic_outcome,omitempty"`
	FinalizationPolicy  *string `json:"finalization_policy,omitempty"`
	FinalizationOutcome *string `json:"finalization_outcome,omitempty"`
	RunDirectory        *string `json:"run_directory,omitempty"`
	ArchivePath         *string `json:"archive_path,omitempty"`
	ArchiveSHA256       *string `json:"archive_sha256,omitempty"`
}

// RouteResolutionRecord represents a row in the route_resolutions table.
type RouteResolutionRecord struct {
	ResolutionID       string  `json:"resolution_id"`
	RunID              string  `json:"run_id"`
	BindingID          string  `json:"binding_id"`
	AttemptNumber      int     `json:"attempt_number"`
	Provider           string  `json:"provider"`
	Profile            string  `json:"profile"`
	EndpointAlias      *string `json:"endpoint_alias,omitempty"`
	IntelligenceJSON   *string `json:"intelligence_json,omitempty"`
	PolicySnapshotJSON *string `json:"policy_snapshot_json,omitempty"`
	ObservationIDsJSON *string `json:"observation_ids_json,omitempty"`
	SelectionRationale *string `json:"selection_rationale,omitempty"`
	ResolvedAt         string  `json:"resolved_at"`
}

// InvocationAttemptRecord represents a row in the invocation_attempts table.
type InvocationAttemptRecord struct {
	AttemptID            string  `json:"attempt_id"`
	RunID                string  `json:"run_id"`
	BindingID            string  `json:"binding_id"`
	AttemptNumber        int     `json:"attempt_number"`
	PredecessorAttemptID *string `json:"predecessor_attempt_id,omitempty"`
	Provider             string  `json:"provider"`
	Profile              string  `json:"profile"`
	EndpointAlias        *string `json:"endpoint_alias,omitempty"`
	Status               string  `json:"status"`
	ExitCode             *int    `json:"exit_code,omitempty"`
	StartedAt            string  `json:"started_at"`
	CompletedAt          *string `json:"completed_at,omitempty"`
	RouteResolutionID    *string `json:"route_resolution_id,omitempty"`
	AttemptKind          string  `json:"attempt_kind"`
}

// OperationalObservationRecord represents a row in the operational_observations table.
type OperationalObservationRecord struct {
	ObservationID   string   `json:"observation_id"`
	Producer        string   `json:"producer"`
	ObservationType string   `json:"observation_type"`
	Provider        string   `json:"provider"`
	Profile         *string  `json:"profile,omitempty"`
	Timestamp       float64  `json:"timestamp"`
	ExpiresAt       *float64 `json:"expires_at,omitempty"`
	Digest          *string  `json:"digest,omitempty"`
	StateValue      string   `json:"state_value"`
	DetailJSON      *string  `json:"detail_json,omitempty"`
}

// ReviewMutationObservationRecord represents a row in the review_mutation_observations table.
type ReviewMutationObservationRecord struct {
	RunID                           string  `json:"run_id"`
	Stage                           string  `json:"stage"`
	Sequence                        int     `json:"sequence"`
	WorktreePolicy                  string  `json:"worktree_policy"`
	IndexPolicy                     string  `json:"index_policy"`
	HeadPolicy                      string  `json:"head_policy"`
	ActionTaken                     string  `json:"action_taken"`
	SubjectDriftObserved            int     `json:"subject_drift_observed"`
	WorktreeDrift                   int     `json:"worktree_drift"`
	IndexDrift                      int     `json:"index_drift"`
	HeadDrift                       int     `json:"head_drift"`
	DiagnosticCode                  *string `json:"diagnostic_code,omitempty"`
	WorktreePathsJSON               *string `json:"worktree_paths_json,omitempty"`
	IndexPathsJSON                  *string `json:"index_paths_json,omitempty"`
	ExpectedTree                    *string `json:"expected_tree,omitempty"`
	ObservedTree                    *string `json:"observed_tree,omitempty"`
	ExpectedIndex                   *string `json:"expected_index,omitempty"`
	ObservedIndex                   *string `json:"observed_index,omitempty"`
	ExpectedHead                    *string `json:"expected_head,omitempty"`
	ObservedHead                    *string `json:"observed_head,omitempty"`
	RecordedAt                      string  `json:"recorded_at"`
	AttemptID                       *string `json:"attempt_id,omitempty"`
	BindingID                       *string `json:"binding_id,omitempty"`
	AttemptNumber                   *int    `json:"attempt_number,omitempty"`
	Role                            *string `json:"role,omitempty"`
	SubjectKind                     *string `json:"subject_kind,omitempty"`
	LimitationsJSON                 *string `json:"limitations_json,omitempty"`
	PolicyGeneration                int     `json:"policy_generation"`
	RawStdoutArtifact               *string `json:"raw_stdout_artifact,omitempty"`
	RawStderrArtifact               *string `json:"raw_stderr_artifact,omitempty"`
	CandidateObservationUnavailable int     `json:"candidate_observation_unavailable"`
	IndexObservationUnavailable     int     `json:"index_observation_unavailable"`
	HeadObservationUnavailable      int     `json:"head_observation_unavailable"`
}

// ReviewMutationPolicyRecord represents a row in the review_mutation_policies table.
type ReviewMutationPolicyRecord struct {
	RunID            string  `json:"run_id"`
	SourceType       string  `json:"source_type"`
	SourcePath       *string `json:"source_path,omitempty"`
	ContentDigest    *string `json:"content_digest,omitempty"`
	WorktreePolicy   *string `json:"worktree_policy,omitempty"`
	IndexPolicy      *string `json:"index_policy,omitempty"`
	HeadPolicy       *string `json:"head_policy,omitempty"`
	ResolvedMode     *string `json:"resolved_mode,omitempty"`
	PolicyGeneration int     `json:"policy_generation"`
	IsWinner         int     `json:"is_winner"`
	PrecedenceRank   int     `json:"precedence_rank"`
	ResolvedAt       string  `json:"resolved_at"`
}

// LegacyQuarantineObservationRecord represents a row in legacy_quarantine_review_mutation_observations.
type LegacyQuarantineObservationRecord struct {
	RunID                           string  `json:"run_id"`
	Stage                           string  `json:"stage"`
	Sequence                        int     `json:"sequence"`
	WorktreePolicy                  *string `json:"worktree_policy,omitempty"`
	IndexPolicy                     *string `json:"index_policy,omitempty"`
	HeadPolicy                      *string `json:"head_policy,omitempty"`
	ActionTaken                     *string `json:"action_taken,omitempty"`
	SubjectDriftObserved            *int    `json:"subject_drift_observed,omitempty"`
	WorktreeDrift                   *int    `json:"worktree_drift,omitempty"`
	IndexDrift                      *int    `json:"index_drift,omitempty"`
	HeadDrift                       *int    `json:"head_drift,omitempty"`
	DiagnosticCode                  *string `json:"diagnostic_code,omitempty"`
	WorktreePathsJSON               *string `json:"worktree_paths_json,omitempty"`
	IndexPathsJSON                  *string `json:"index_paths_json,omitempty"`
	ExpectedTree                    *string `json:"expected_tree,omitempty"`
	ObservedTree                    *string `json:"observed_tree,omitempty"`
	ExpectedIndex                   *string `json:"expected_index,omitempty"`
	ObservedIndex                   *string `json:"observed_index,omitempty"`
	ExpectedHead                    *string `json:"expected_head,omitempty"`
	ObservedHead                    *string `json:"observed_head,omitempty"`
	RecordedAt                      *string `json:"recorded_at,omitempty"`
	AttemptID                       *string `json:"attempt_id,omitempty"`
	BindingID                       *string `json:"binding_id,omitempty"`
	AttemptNumber                   *int    `json:"attempt_number,omitempty"`
	Role                            *string `json:"role,omitempty"`
	SubjectKind                     *string `json:"subject_kind,omitempty"`
	LimitationsJSON                 *string `json:"limitations_json,omitempty"`
	PolicyGeneration                *int    `json:"policy_generation,omitempty"`
	RawStdoutArtifact               *string `json:"raw_stdout_artifact,omitempty"`
	RawStderrArtifact               *string `json:"raw_stderr_artifact,omitempty"`
	CandidateObservationUnavailable *int    `json:"candidate_observation_unavailable,omitempty"`
	IndexObservationUnavailable     *int    `json:"index_observation_unavailable,omitempty"`
	HeadObservationUnavailable      *int    `json:"head_observation_unavailable,omitempty"`
	QuarantinedAt                   string  `json:"quarantined_at"`
	QuarantineReason                string  `json:"quarantine_reason"`
}

// LegacyQuarantinePolicyRecord represents a row in legacy_quarantine_review_mutation_policies.
type LegacyQuarantinePolicyRecord struct {
	RunID            string  `json:"run_id"`
	SourceType       string  `json:"source_type"`
	SourcePath       *string `json:"source_path,omitempty"`
	ContentDigest    *string `json:"content_digest,omitempty"`
	WorktreePolicy   *string `json:"worktree_policy,omitempty"`
	IndexPolicy      *string `json:"index_policy,omitempty"`
	HeadPolicy       *string `json:"head_policy,omitempty"`
	ResolvedMode     *string `json:"resolved_mode,omitempty"`
	PolicyGeneration *int    `json:"policy_generation,omitempty"`
	IsWinner         *int    `json:"is_winner,omitempty"`
	PrecedenceRank   *int    `json:"precedence_rank,omitempty"`
	ResolvedAt       *string `json:"resolved_at,omitempty"`
	QuarantinedAt    string  `json:"quarantined_at"`
	QuarantineReason string  `json:"quarantine_reason"`
}
