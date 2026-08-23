package envsnap

import (
	"errors"
	"fmt"
	"time"
)

var (
	ErrInvalidProfile  = errors.New("invalid environment profile")
	ErrInvalidSnapshot = errors.New("invalid environment snapshot")
	ErrInvalidValue    = errors.New("invalid environment value")
	ErrMissingRequired = errors.New("required environment value is missing")
	ErrSensitiveName   = errors.New("sensitive environment name is not allowed")
	ErrUnsafePath      = errors.New("unsafe environment snapshot path")
	ErrLockConflict    = errors.New("environment snapshot lock conflict")
	ErrStale           = errors.New("environment snapshot is stale")
	ErrInvalidMode     = errors.New("invalid environment resolution mode")
	ErrProfileMismatch = errors.New("environment profile mismatch")
	ErrFingerprint     = errors.New("environment snapshot fingerprint mismatch")
)

// MissingRequiredError identifies a missing profile name without exposing a
// value. Name is an allowlist identifier, not a captured secret.
type MissingRequiredError struct {
	Names []string
}

func (e *MissingRequiredError) Error() string {
	return fmt.Sprintf("%s: %d required name(s)", ErrMissingRequired, len(e.Names))
}

func (e *MissingRequiredError) Unwrap() error { return ErrMissingRequired }

// StaleError reports a snapshot age failure without exposing environment
// values.
type StaleError struct {
	Age    time.Duration
	MaxAge time.Duration
}

func (e *StaleError) Error() string {
	return fmt.Sprintf("%s: age=%s max_age=%s", ErrStale, e.Age, e.MaxAge)
}

func (e *StaleError) Unwrap() error { return ErrStale }

func invalidProfile(format string, args ...any) error {
	return fmt.Errorf("%w: %s", ErrInvalidProfile, fmt.Sprintf(format, args...))
}

func invalidSnapshot(format string, args ...any) error {
	return fmt.Errorf("%w: %s", ErrInvalidSnapshot, fmt.Sprintf(format, args...))
}

func invalidValue(format string, args ...any) error {
	return fmt.Errorf("%w: %s", ErrInvalidValue, fmt.Sprintf(format, args...))
}

func isOneOf(err error, targets ...error) bool {
	for _, target := range targets {
		if errors.Is(err, target) {
			return true
		}
	}
	return false
}
