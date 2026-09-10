package hotspot

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"path"
	"reflect"
	"strings"
	"unicode/utf8"
)

// fingerprintV2 calculates the SHA-256 over a canonical JSON identity view of ReportV2.
// It excludes the Fingerprint field itself, resource metering and warning prose,
// while preserving all deterministic scan facts, history metrics, and rankings.
func fingerprintV2(report ReportV2) (string, error) {
	identity := report
	identity.Fingerprint = ""
	identity.Warnings = nil
	identity.History = historyIdentityView(identity.History)
	content, err := json.Marshal(identity)
	if err != nil {
		return "", err
	}
	hash := sha256.Sum256(content)
	return "sha256:" + hex.EncodeToString(hash[:]), nil
}

// MarshalJSONV2 emits complete deterministic schema-v2 JSON terminated by one newline.
func MarshalJSONV2(report ReportV2) ([]byte, error) {
	if err := validateReportV2(report); err != nil {
		return nil, err
	}
	expected, err := fingerprintV2(report)
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

func validateReportV2(report ReportV2) error {
	if report.SchemaVersion != ReportSchemaV2 || report.CapabilityVersion != CapabilityMatrixV2 || report.CompletionStatus != CompletionComplete {
		return invalidReport("unsupported or incomplete v2 report")
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
	if !fullOIDPattern.MatchString(report.History.StartOID) || !fullOIDPattern.MatchString(report.History.EndOID) {
		return invalidReport("history endpoints are invalid")
	}

	if report.ScanConfiguration.DisplayTopN < 1 || report.ScanConfiguration.DisplayTopN > 100 {
		return invalidReport("invalid display bound")
	}
	h := report.History
	if h.Policy != HistoryPolicyV2 || h.ID != historyIdentity(h) || h.CommitCount != len(h.Commits) || h.CommitCount > h.Limits.MaxCommits {
		return invalidReport("invalid history identity or sequence")
	}
	if h.ObjectFormat != "sha1" && h.ObjectFormat != "sha256" {
		return invalidReport("unsupported object format")
	}
	if h.StartOID != report.ScanConfiguration.HistoryStartOID || h.EndOID != report.ScanConfiguration.HistoryEndOID || h.Limits != report.ScanConfiguration.HistoryLimits {
		return invalidReport("history configuration mismatch")
	}
	previous := ""
	byPath := map[string]FileHistory{}
	var churn, growth int64
	transitions, unavailable := 0, 0
	for _, f := range h.Files {
		if !utf8.ValidString(f.Path) || f.Path == "." || path.Clean(f.Path) != f.Path || strings.HasPrefix(f.Path, "/") || strings.Contains(f.Path, "\\") || f.Path <= previous || strings.HasPrefix(f.Path, "../") {
			return invalidReport("invalid history path order")
		}
		previous = f.Path
		byPath[f.Path] = f
		if f.TransitionCount < 0 || f.TransitionCount > h.CommitCount {
			return invalidReport("invalid transition count")
		}
		transitions += f.TransitionCount
		if f.ChurnUnit != "physical-lines-inserted-plus-deleted" || f.GrowthUnit != "physical-lines" {
			return invalidReport("invalid history units")
		}
		if f.Churn == nil {
			if f.ChurnAvailability != AvailabilityUnavailable || f.Growth != nil || f.GrowthAvailability != AvailabilityUnavailable {
				return invalidReport("invalid unavailable metrics")
			}
			unavailable++
		} else {
			if *f.Churn < 0 || f.Growth == nil || f.StartLines == nil || f.EndLines == nil || *f.StartLines < 0 || *f.EndLines < 0 || *f.Growth != *f.EndLines-*f.StartLines || f.ChurnAvailability != AvailabilityExact || f.GrowthAvailability != AvailabilityExact {
				return invalidReport("invalid history metrics")
			}
			churn += *f.Churn
			growth += *f.Growth
		}
	}
	if churn != h.TotalChurn || growth != h.NetGrowth || transitions != h.PathTransitionCount || unavailable != h.UnavailablePaths {
		return invalidReport("history aggregation mismatch")
	}
	for _, f := range report.Files {
		history, exists := byPath[f.Path]
		if !exists || f.History == nil || !reflect.DeepEqual(*f.History, history) {
			return invalidReport("file history binding mismatch")
		}
	}
	expected, err := fingerprintV2(report)
	if err != nil {
		return err
	}
	if report.Fingerprint != expected {
		return invalidReport("report fingerprint does not match its identity view")
	}
	return nil
}
