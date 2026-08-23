// Package response owns APGR's private numbered response capture contract.
//
// The package deliberately accepts already-selected project and phase
// identities. Repository discovery, configuration, and command-line parsing
// remain owners of their respective adapters.
package response

import (
	"errors"
	"fmt"
	"io"
	"regexp"
	"time"
)

const (
	MaxComponentLength = 128
	MaxResponseNumber  = 999
	MaxResponseBytes   = 8 << 20
	LockName           = ".response.lock"
	TempGlob           = ".response-write.*.tmp"
	lockTimeout        = 10 * time.Second
	lockPoll           = 10 * time.Millisecond
)

var (
	ErrUsage      = errors.New("response usage error")
	ErrInput      = errors.New("response input error")
	ErrAllocation = errors.New("response allocation error")
	ErrUnsafe     = errors.New("response path is unsafe")

	componentPattern   = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9._-]*$`)
	reservationPattern = regexp.MustCompile(`^\.([A-Za-z0-9][A-Za-z0-9._-]*)\.([0-9]{3})\.response\.md\.reservation\.([A-Za-z0-9_-]+)$`)
	temporaryPattern   = regexp.MustCompile(`^\.response-write\.[A-Za-z0-9_-]+\.tmp$`)
)

// Error is the common typed error returned by this package. Its category is
// available through errors.Is with ErrUsage, ErrInput, ErrAllocation, or
// ErrUnsafe; the wrapped cause, when any, remains available to callers.
type Error struct {
	kind    error
	message string
	cause   error
}

func (err *Error) Error() string {
	if err == nil {
		return ""
	}
	return err.message
}

func (err *Error) Unwrap() error { return err.cause }

func (err *Error) Is(target error) bool {
	return target == err.kind || (err.cause != nil && errors.Is(err.cause, target))
}

func responseError(kind error, message string, cause error) error {
	return &Error{kind: kind, message: message, cause: cause}
}

func usageError(format string, values ...any) error {
	return responseError(ErrUsage, fmt.Sprintf(format, values...), nil)
}

func inputError(format string, values ...any) error {
	return responseError(ErrInput, fmt.Sprintf(format, values...), nil)
}

func allocationError(format string, values ...any) error {
	return responseError(ErrAllocation, fmt.Sprintf(format, values...), nil)
}

func unsafeError(format string, values ...any) error {
	return responseError(ErrUnsafe, fmt.Sprintf(format, values...), nil)
}

func wrappedError(kind error, message string, cause error) error {
	return responseError(kind, message, cause)
}

// Options supplies exactly one byte-preserving response input. A non-nil Body
// is selected even when it is empty; InputPath and Stdin are selected when
// their values are non-empty/non-nil respectively.
type Options struct {
	OutboxRoot string
	Project    string
	Phase      string
	Body       []byte
	InputPath  string
	Stdin      io.Reader
}

// Request is a compatibility spelling for Options.
type Request = Options
