package report

import "errors"

var (
	// ErrInvalidRequest classifies invalid request or record-schema input.
	ErrInvalidRequest = errors.New("invalid report request")
	// ErrUnsupported classifies unsupported platforms or Git states.
	ErrUnsupported = errors.New("unsupported report capability")
	// ErrRepository classifies repository or native Git precondition failures.
	ErrRepository = errors.New("repository precondition failed")
	// ErrDrift classifies a repository state that changed during observation.
	ErrDrift = errors.New("concurrent repository drift")
	// ErrUnsafePath classifies unsafe path, owner, permission, or file state.
	ErrUnsafePath = errors.New("unsafe report path")
	// ErrCompatibility classifies canonical byte or schema compatibility failures.
	ErrCompatibility = errors.New("report compatibility mismatch")
	// ErrPublication classifies lock conflicts and recoverable transactions.
	ErrPublication = errors.New("report publication conflict")
)
