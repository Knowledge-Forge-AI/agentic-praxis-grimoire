package hotspot

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"strings"
)

// fingerprint calculates the SHA-256 over a canonical JSON identity view.
// It excludes the Fingerprint field itself and human diagnostic warning prose,
// while preserving all deterministic scan facts, file metrics, and rankings.
func fingerprint(report Report) (string, error) {
	identity := report
	identity.Fingerprint = ""
	identity.Warnings = nil
	content, err := json.Marshal(identity)
	if err != nil {
		return "", err
	}
	hash := sha256.Sum256(content)
	return "sha256:" + hex.EncodeToString(hash[:]), nil
}

// MarshalJSON emits complete deterministic schema-v1 JSON terminated by one newline.
func MarshalJSON(report Report) ([]byte, error) {
	if err := validateReport(report); err != nil {
		return nil, err
	}
	expected, err := fingerprint(report)
	if err != nil {
		return nil, err
	}
	if report.Fingerprint != expected {
		return nil, invalidReport("report fingerprint does not match its identity view")
	}
	content, err := json.Marshal(report)
	if err != nil {
		return nil, err
	}
	return append(content, '\n'), nil
}

func validateReport(report Report) error {
	if report.SchemaVersion != ReportSchemaV1 || report.CapabilityVersion != CapabilityMatrixV1 || report.CompletionStatus != CompletionComplete {
		return invalidReport("unsupported or incomplete report")
	}
	if !rootIDPattern.MatchString(report.RootID) || report.ToolVersion == "" {
		return invalidReport("report identity is invalid")
	}
	if !strings.HasPrefix(report.Fingerprint, "sha256:") {
		return invalidReport("report fingerprint is absent")
	}
	for _, file := range report.Files {
		if file.Path == "" || strings.HasPrefix(file.Path, "/") || strings.Contains(file.Path, "\\") || strings.Contains(file.Path, "../") {
			return invalidReport("file path is not root-relative")
		}
	}
	return nil
}
