package report

import (
	"fmt"
	"path/filepath"
	"regexp"
	"strings"
)

var (
	identifierPattern = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9._-]*$`)
	hexCommitPattern  = regexp.MustCompile(`^[0-9a-f]{40,64}$`)
)

func validateIdentifier(value, name string) error {
	if len(value) == 0 || len(value) > 128 || value == "." || value == ".." || !identifierPattern.MatchString(value) {
		return fmt.Errorf("%w: %s is unsafe", ErrInvalidRequest, name)
	}
	return nil
}

func validateMetadata(value, name string) error {
	for _, character := range value {
		if character < 32 || character == 127 {
			return fmt.Errorf("%w: %s contains a control character", ErrInvalidRequest, name)
		}
	}
	return nil
}

func headerValue(value string) string {
	if value == "" {
		return "NULL"
	}
	return value
}

func validateRequestMetadata(metadata RequestMetadata) error {
	if err := validateIdentifier(metadata.Phase, "phase"); err != nil {
		return err
	}
	if err := validateMetadata(metadata.Result, "result"); err != nil {
		return err
	}
	return validateMetadata(metadata.FinalGate, "final gate")
}

func validateStatusDoc(value string, optional bool) (string, error) {
	if optional && value == "" {
		return "NONE", nil
	}
	if err := validateMetadata(value, "status document"); err != nil {
		return "", err
	}
	if optional {
		if filepath.IsAbs(value) || filepath.Clean(value) != value || strings.Contains(value, `\`) {
			return "", fmt.Errorf("%w: status document must be clean and repository-relative", ErrInvalidRequest)
		}
	}
	return value, nil
}

func validateSourceName(value string) error {
	if value == "" || value != filepath.Base(value) || strings.ContainsAny(value, `/\`) {
		return fmt.Errorf("%w: source name must be a basename", ErrInvalidRequest)
	}
	return validateMetadata(value, "source name")
}
