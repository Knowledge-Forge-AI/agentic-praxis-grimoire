package phase

// AttemptStatus represents the lifecycle state of an invocation attempt.
type AttemptStatus string

const (
	StatusStaged          AttemptStatus = "staged"
	StatusRunning         AttemptStatus = "running"
	StatusCompleted       AttemptStatus = "completed"
	StatusFailed          AttemptStatus = "failed"
	StatusFailedPreLaunch AttemptStatus = "failed_pre_launch"
	StatusInterrupted     AttemptStatus = "interrupted"
)

// InvocationAttempt records a single provider invocation attempt for an actor binding turn.
type InvocationAttempt struct {
	AttemptID     string        `json:"attempt_id"`
	BindingID     string        `json:"binding_id"`
	PredecessorID *string       `json:"predecessor_id,omitempty"`
	Status        AttemptStatus `json:"status"`
	StartedAt     string        `json:"started_at"`
	CompletedAt   *string       `json:"completed_at,omitempty"`
	ExitCode      *int          `json:"exit_code,omitempty"`
}
