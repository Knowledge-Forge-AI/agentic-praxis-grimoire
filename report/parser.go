package report

import (
	"bytes"
	"fmt"
	"regexp"
	"strconv"
	"strings"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/schema"
)

var (
	hex64                          = regexp.MustCompile(`^[0-9a-f]{64}$`)
	showIDValidationPattern        = regexp.MustCompile(`^GIT-SHOW-REPORT-(?:[0-9a-f]{40}|[0-9a-f]{64})$`)
	diffIDValidationPattern        = regexp.MustCompile(`^GIT-DIFF-REPORT-[0-9a-f]{64}$`)
	operationalIDValidationPattern = regexp.MustCompile(`^OPERATIONAL-REPORT-[0-9a-f]{64}$`)
)

// ParseRecords strictly validates contiguous canonical common-envelope records.
func ParseRecords(content []byte) ([]Record, error) {
	if len(content) == 0 {
		return []Record{}, nil
	}
	records := []Record{}
	offset := 0
	for offset < len(content) {
		record, next, err := parseRecordAt(content, offset)
		if err != nil {
			return nil, err
		}
		records = append(records, record)
		offset = next
	}
	return records, nil
}

func parseRecordAt(content []byte, offset int) (Record, int, error) {
	start := append(bytes.Clone(envelopeLine), []byte("\nBEGIN AGENT-REPORT-RECORD\n")...)
	if !bytes.HasPrefix(content[offset:], start) {
		return Record{}, offset, fmt.Errorf("%w: non-canonical record prefix", ErrCompatibility)
	}
	lines := make([]string, 12)
	cursor := offset
	for index := range lines {
		ending := bytes.IndexByte(content[cursor:], '\n')
		if ending < 0 {
			return Record{}, offset, fmt.Errorf("%w: incomplete record header", ErrCompatibility)
		}
		lines[index] = string(content[cursor : cursor+ending])
		cursor += ending + 1
	}
	expected := []string{
		string(envelopeLine), "BEGIN AGENT-REPORT-RECORD",
		"ENVELOPE-FORMAT: agent-report-record", "ENVELOPE-VERSION: 1",
	}
	for index, value := range expected {
		if lines[index] != value {
			return Record{}, offset, fmt.Errorf("%w: invalid record header", ErrCompatibility)
		}
	}
	if lines[11] != string(envelopeLine) {
		return Record{}, offset, fmt.Errorf("%w: invalid record header boundary", ErrCompatibility)
	}
	prefixes := []string{"RECORD-TYPE: ", "RECORD-FORMAT-VERSION: ", "RECORD-ID: ", "PROJECT: ", "PHASE: ", "PAYLOAD-SHA256: ", "PAYLOAD-SIZE-BYTES: "}
	values := make([]string, len(prefixes))
	for index, prefix := range prefixes {
		line := lines[index+4]
		if !strings.HasPrefix(line, prefix) {
			return Record{}, offset, fmt.Errorf("%w: invalid record field order", ErrCompatibility)
		}
		values[index] = strings.TrimPrefix(line, prefix)
		if values[index] == "" || !safeField.MatchString(values[index]) {
			return Record{}, offset, fmt.Errorf("%w: unsafe record field", ErrCompatibility)
		}
	}
	formatVersion, err := strconv.Atoi(values[1])
	if err != nil {
		return Record{}, offset, fmt.Errorf("%w: invalid format version", ErrCompatibility)
	}
	payloadSize, err := strconv.Atoi(values[6])
	if err != nil || payloadSize < 0 || !hex64.MatchString(values[5]) {
		return Record{}, offset, fmt.Errorf("%w: invalid payload identity", ErrCompatibility)
	}
	payloadEnd := cursor + payloadSize
	if payloadEnd > len(content) {
		return Record{}, offset, fmt.Errorf("%w: truncated record payload", ErrCompatibility)
	}
	payload := bytes.Clone(content[cursor:payloadEnd])
	if schema.SHA256(payload) != values[5] {
		return Record{}, offset, fmt.Errorf("%w: payload hash mismatch", ErrCompatibility)
	}
	trailer := []string{string(envelopeLine), "END AGENT-REPORT-RECORD", "ENVELOPE-FORMAT: agent-report-record", "ENVELOPE-VERSION: 1"}
	trailer = append(trailer, lines[4:9]...)
	trailer = append(trailer, "RECORD-COMPLETE: true", string(envelopeLine))
	cursor = payloadEnd
	for _, expectedLine := range trailer {
		ending := bytes.IndexByte(content[cursor:], '\n')
		if ending < 0 || string(content[cursor:cursor+ending]) != expectedLine {
			return Record{}, offset, fmt.Errorf("%w: invalid record trailer", ErrCompatibility)
		}
		cursor += ending + 1
	}
	record := Record{Kind: schema.RecordKind(values[0]), FormatVersion: formatVersion, ID: values[2], Project: values[3], Phase: values[4], Payload: payload}
	if err := validateRecordIdentity(record); err != nil {
		return Record{}, offset, err
	}
	return record, cursor, nil
}

func validateRecordIdentity(record Record) error {
	expected, ok := record.Kind.FormatVersion()
	if !ok || record.FormatVersion != expected {
		return fmt.Errorf("%w: unsupported record format version", ErrCompatibility)
	}
	if err := validateIdentifier(record.Project, "project"); err != nil {
		return fmt.Errorf("%w: invalid record project", ErrCompatibility)
	}
	if err := validateIdentifier(record.Phase, "phase"); err != nil {
		return fmt.Errorf("%w: invalid record phase", ErrCompatibility)
	}
	switch record.Kind {
	case schema.GitShowRecord:
		if !showIDValidationPattern.MatchString(record.ID) {
			return fmt.Errorf("%w: invalid Git-show identity", ErrCompatibility)
		}
	case schema.GitDiffRecord:
		if !diffIDValidationPattern.MatchString(record.ID) {
			return fmt.Errorf("%w: invalid Git-diff identity", ErrCompatibility)
		}
	case schema.OperationalRecord:
		if !operationalIDValidationPattern.MatchString(record.ID) {
			return fmt.Errorf("%w: invalid operational identity", ErrCompatibility)
		}
	}
	return nil
}
