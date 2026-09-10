package report

import (
	"bytes"
	"context"
	"fmt"
	"strings"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/schema"
)

// The historical context preserves the previously accepted classification and
// association rules. It never disables artifact integrity or canonical rendering.
func validateRecognizedOperationalFields(raw []byte, fields map[string][][]byte) error {
	if len(fields["report_schema"]) > 0 && !schemaLine.Match(raw) {
		return fmt.Errorf("%w: unsupported report_schema", ErrInvalidRequest)
	}
	if !schemaLine.Match(raw) {
		return nil
	}
	for _, key := range []string{"report_schema", "phase", "outcome", "primary_commit", "primary_git_report_id"} {
		values := fields[key]
		if len(values) > 1 {
			return fmt.Errorf("%w: duplicate operational field", ErrInvalidRequest)
		}
		if len(values) == 0 {
			continue
		}
		value := boundedField(values[0])
		if value == "UNKNOWN" {
			return fmt.Errorf("%w: invalid recognized operational scalar", ErrInvalidRequest)
		}
		switch key {
		case "primary_commit":
			if !showIDValidationPattern.MatchString("GIT-SHOW-REPORT-" + strings.ToLower(value)) {
				return fmt.Errorf("%w: malformed primary_commit", ErrInvalidRequest)
			}
		case "primary_git_report_id":
			if !showIDPattern.MatchString(value) && !diffIDPattern.MatchString(value) {
				return fmt.Errorf("%w: malformed primary_git_report_id", ErrInvalidRequest)
			}
		}
	}
	commit, id := string(firstField(fields["primary_commit"])), string(firstField(fields["primary_git_report_id"]))
	if commit != "" && id != "" && id != "GIT-SHOW-REPORT-"+strings.ToLower(commit) {
		return fmt.Errorf("%w: conflicting primary fields", ErrInvalidRequest)
	}
	return nil
}

func validateOperationalSemantics(source operationalSource, phase, result string, related *Record, commit, id string, historical bool) error {
	if err := validateOperationalBody(source, phase, result, related, commit, id); err != nil {
		return err
	}
	if historical || related == nil || source.bodySchema != "operational-report-v1" {
		return nil
	}
	if source.primaryGitReportID != "UNKNOWN" && source.primaryGitReportID != id {
		return fmt.Errorf("%w: operational primary report mismatch", ErrCompatibility)
	}
	if related.Kind == schema.GitDiffRecord && source.primaryCommit != "UNKNOWN" {
		return fmt.Errorf("%w: Git-diff body cannot declare a primary commit", ErrCompatibility)
	}
	return nil
}

func validateOperationalRecord(record Record, historical bool) error {
	return validateOperationalRecordWithContext(context.Background(), record, historical, nil)
}

func validateOperationalRecordWithContext(ctx context.Context, record Record, historical bool, stats *envelopeExtractionStats) error {
	_, err := decodeOperationalRecordWithContext(ctx, record, historical, stats)
	return err
}

func decodeOperationalRecord(record Record, historical bool) (string, error) {
	return decodeOperationalRecordWithContext(context.Background(), record, historical, nil)
}

func decodeOperationalRecordWithContext(ctx context.Context, record Record, historical bool, stats *envelopeExtractionStats) (string, error) {
	sections, err := decodeSectionsWithContext(ctx, record.Payload, []sectionSpec{
		{name: "READING GUIDE"}, {name: "OPERATIONAL REPORT IDENTITY"}, {name: "OPERATIONAL SUMMARY"}, {name: "RELATED RECORDS"},
		{name: "OPERATIONAL REPORT BODY", hash: "FRAMED-BODY-SHA256", size: "FRAMED-BODY-SIZE-BYTES"},
	}, stats)
	if err != nil {
		return "", err
	}
	identity, _, err := parseSectionFieldsWithContext(ctx, sections["OPERATIONAL REPORT IDENTITY"])
	if err != nil {
		return "", err
	}
	framed := sections["OPERATIONAL REPORT BODY"]
	size, err := persistedSize(identity["SOURCE-PAYLOAD-SIZE-BYTES"], len(framed))
	if err != nil || size == 0 || size > maxOperationalSourceBytes {
		return "", fmt.Errorf("%w: invalid operational source size", ErrCompatibility)
	}
	raw := framed[:size]
	if !bytes.Equal(ensurePayloadEnding(raw), framed) {
		return "", fmt.Errorf("%w: source framing mismatch", ErrCompatibility)
	}
	source, err := parseOperationalSourceMode(identity["SOURCE-FILE-BASENAME"], raw, historical)
	if err != nil {
		return "", err
	}
	request := OperationalRequest{RequestMetadata: RequestMetadata{Phase: record.Phase, Result: identity["RESULT"], FinalGate: identity["FINAL-GATE"]}, Project: record.Project, SourceName: source.name, Source: raw, RelatedCommit: identity["RELATED-COMMIT"], RelatedGitReportID: identity["RELATED-GIT-REPORT-ID"]}
	if err := validateSourceName(source.name); err != nil {
		return "", err
	}
	related, err := persistedRelation(request.RelatedCommit, request.RelatedGitReportID)
	if err != nil {
		return "", err
	}
	if err := validateOperationalSemantics(source, request.Phase, request.Result, related, request.RelatedCommit, request.RelatedGitReportID, historical); err != nil {
		return "", err
	}
	kind := schema.RecordKind("")
	if related != nil {
		kind = related.Kind
	}
	id := "OPERATIONAL-REPORT-" + schema.SHA256(raw)
	payload, err := renderOperationalPayload(request, source, id, schema.SHA256(raw), request.RelatedCommit, request.RelatedGitReportID, kind)
	if err != nil {
		return "", err
	}
	if record.Kind != schema.OperationalRecord || record.ID != id || !bytes.Equal(record.Payload, payload) {
		return "", fmt.Errorf("%w: operational payload differs from canonical semantics", ErrCompatibility)
	}
	return request.RelatedGitReportID, nil
}

func persistedRelation(commit, id string) (*Record, error) {
	if id == "NONE" && commit == "NONE" {
		return nil, nil
	}
	if match := showIDPattern.FindStringSubmatch(id); len(match) == 2 && commit == match[1] {
		return &Record{Kind: schema.GitShowRecord, ID: id}, nil
	}
	if diffIDPattern.MatchString(id) && commit == "NONE" {
		return &Record{Kind: schema.GitDiffRecord, ID: id}, nil
	}
	return nil, fmt.Errorf("%w: invalid operational relation", ErrCompatibility)
}
