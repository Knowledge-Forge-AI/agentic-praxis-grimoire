package phase

// TerminalStatus represents the final outcome of an executed phase.
type TerminalStatus string

const (
	TerminalStatusCompleted   TerminalStatus = "completed"
	TerminalStatusFailed      TerminalStatus = "failed"
	TerminalStatusInterrupted TerminalStatus = "interrupted"
)

// FailureCategory classifies phase-level failures for deterministic recovery.
type FailureCategory string

const (
	FailurePreLaunch          FailureCategory = "failed_pre_launch"
	FailureRunner             FailureCategory = "runner_failure"
	FailureVerification       FailureCategory = "verification_failure"
	FailureReviewFindings     FailureCategory = "review_findings_unresolved"
	FailureOperatorInterrupt  FailureCategory = "operator_interrupted"
	FailureUnrecordedMutation FailureCategory = "unrecorded_mutation"
	FailureTimeout            FailureCategory = "timeout"
)
