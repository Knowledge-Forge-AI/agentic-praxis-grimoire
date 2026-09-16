package phase

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"strings"
	"unicode/utf8"
)

// SchemaNameV2 is the exact schema identifier for Request V2.
const SchemaNameV2 = "agent-phase-request-v2"

// Supported phase type constants.
const (
	PhaseTypeImplementationTesting = "implementation_testing"
	PhaseTypeArchitectureDocs      = "architecture_docs"
	PhaseTypeSysadmin              = "sysadmin"
)

// Size bounds matching APGR Python runtime specifications.
const (
	MaxPromptBytes  = 256 * 1024
	MaxRequestBytes = MaxPromptBytes + 64*1024
)

var (
	// ErrInvalidSchema indicates schema is not agent-phase-request-v2.
	ErrInvalidSchema = errors.New("phase: invalid schema")
	// ErrUnsupportedPhaseType indicates phase_type is not in the supported set.
	ErrUnsupportedPhaseType = errors.New("phase: unsupported phase_type")
	// ErrEmptyPrompt indicates prompt is empty or whitespace-only.
	ErrEmptyPrompt = errors.New("phase: prompt must be non-empty")
	// ErrPromptTooLarge indicates prompt byte length exceeds MaxPromptBytes.
	ErrPromptTooLarge = errors.New("phase: prompt exceeds maximum size")
	// ErrRequestTooLarge indicates overall payload exceeds MaxRequestBytes.
	ErrRequestTooLarge = errors.New("phase: request payload exceeds maximum size")
	// ErrInvalidUTF8 indicates payload is not valid UTF-8.
	ErrInvalidUTF8 = errors.New("phase: request contains invalid UTF-8")
	// ErrUnexpectedField indicates an unrecognized or prohibited field was found.
	ErrUnexpectedField = errors.New("phase: unexpected field in request")
)

// RequestV2 represents a validated, work-only single-phase request envelope.
// In accordance with ADR 0058 and ADR 0066, Request V2 contains no runtime routing
// or execution mode fields; policy remains external to the task contract.
type RequestV2 struct {
	Schema    string `json:"schema"`
	PhaseType string `json:"phase_type"`
	Prompt    string `json:"prompt"`
}

// ValidPhaseType returns true if phaseType is one of the supported APGR phase types.
func ValidPhaseType(phaseType string) bool {
	switch phaseType {
	case PhaseTypeImplementationTesting, PhaseTypeArchitectureDocs, PhaseTypeSysadmin:
		return true
	default:
		return false
	}
}

// ParseRequestV2 parses and strictly validates raw JSON bytes as RequestV2.
// Any unknown or prohibited fields (e.g. execution_mode, constraints) fail closed.
func ParseRequestV2(data []byte) (RequestV2, error) {
	if len(data) > MaxRequestBytes {
		return RequestV2{}, fmt.Errorf("%w: %d > %d", ErrRequestTooLarge, len(data), MaxRequestBytes)
	}
	if !utf8.Valid(data) {
		return RequestV2{}, ErrInvalidUTF8
	}

	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.DisallowUnknownFields()

	var req RequestV2
	if err := decoder.Decode(&req); err != nil {
		if strings.Contains(err.Error(), "unknown field") {
			return RequestV2{}, fmt.Errorf("%w: %v", ErrUnexpectedField, err)
		}
		return RequestV2{}, fmt.Errorf("phase: json decode error: %w", err)
	}

	// Ensure no trailing tokens
	var extra json.RawMessage
	if err := decoder.Decode(&extra); err != io.EOF {
		return RequestV2{}, errors.New("phase: unexpected content after top-level JSON object")
	}

	if err := ValidateRequestV2(req); err != nil {
		return RequestV2{}, err
	}

	return req, nil
}

// ValidateRequestV2 checks domain invariants on an existing RequestV2 struct.
func ValidateRequestV2(req RequestV2) error {
	if req.Schema != SchemaNameV2 {
		return fmt.Errorf("%w: got %q, expected %q", ErrInvalidSchema, req.Schema, SchemaNameV2)
	}
	if !ValidPhaseType(req.PhaseType) {
		return fmt.Errorf("%w: %q", ErrUnsupportedPhaseType, req.PhaseType)
	}
	if strings.TrimSpace(req.Prompt) == "" {
		return ErrEmptyPrompt
	}
	if len(req.Prompt) > MaxPromptBytes {
		return fmt.Errorf("%w: %d > %d", ErrPromptTooLarge, len(req.Prompt), MaxPromptBytes)
	}
	return nil
}
