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
	envelopeLine = bytes.Repeat([]byte("="), 80)
	sectionLine  = bytes.Repeat([]byte("-"), 80)
	safeField    = regexp.MustCompile(`^[^\x00-\x1f\x7f\r\n]+$`)
)

func ensurePayloadEnding(payload []byte) []byte {
	result := bytes.Clone(payload)
	if len(result) != 0 && result[len(result)-1] != '\n' {
		result = append(result, '\n')
	}
	return result
}

func renderSection(name string, payload []byte) ([]byte, error) {
	if name == "" || !isASCII(name) || !safeField.MatchString(name) {
		return nil, fmt.Errorf("%w: unsafe section name", ErrCompatibility)
	}
	framed := ensurePayloadEnding(payload)
	var result bytes.Buffer
	result.Write(envelopeBytes(sectionLine, "BEGIN "+name))
	result.Write(framed)
	result.Write(envelopeBytes(sectionLine, "END "+name))
	return result.Bytes(), nil
}

func envelopeBytes(line []byte, label string) []byte {
	result := make([]byte, 0, len(line)*2+len(label)+3)
	result = append(result, line...)
	result = append(result, '\n')
	result = append(result, label...)
	result = append(result, '\n')
	result = append(result, line...)
	result = append(result, '\n')
	return result
}

func encodeLines(values ...[2]string) ([]byte, error) {
	var result bytes.Buffer
	for _, pair := range values {
		if !safeField.MatchString(pair[0]) || strings.ContainsRune(pair[1], 0) || strings.ContainsAny(pair[1], "\r\n") {
			return nil, fmt.Errorf("%w: unsafe report field", ErrCompatibility)
		}
		result.WriteString(pair[0])
		result.WriteString(": ")
		result.WriteString(pair[1])
		result.WriteByte('\n')
	}
	return result.Bytes(), nil
}

func buildRecord(record Record) ([]byte, error) {
	if err := validateRecordIdentity(record); err != nil {
		return nil, err
	}
	common := [][2]string{
		{"RECORD-TYPE", string(record.Kind)},
		{"RECORD-FORMAT-VERSION", strconv.Itoa(record.FormatVersion)},
		{"RECORD-ID", record.ID},
		{"PROJECT", record.Project},
		{"PHASE", record.Phase},
	}
	for _, pair := range common {
		if !safeField.MatchString(pair[1]) {
			return nil, fmt.Errorf("%w: unsafe record field", ErrCompatibility)
		}
	}
	var result bytes.Buffer
	result.Write(envelopeLine)
	result.WriteString("\nBEGIN AGENT-REPORT-RECORD\n")
	result.WriteString("ENVELOPE-FORMAT: " + schema.EnvelopeFormat + "\n")
	result.WriteString("ENVELOPE-VERSION: 1\n")
	for _, pair := range common {
		result.WriteString(pair[0] + ": " + pair[1] + "\n")
	}
	result.WriteString("PAYLOAD-SHA256: " + schema.SHA256(record.Payload) + "\n")
	result.WriteString("PAYLOAD-SIZE-BYTES: " + strconv.Itoa(len(record.Payload)) + "\n")
	result.Write(envelopeLine)
	result.WriteByte('\n')
	result.Write(record.Payload)
	result.Write(envelopeLine)
	result.WriteString("\nEND AGENT-REPORT-RECORD\n")
	result.WriteString("ENVELOPE-FORMAT: " + schema.EnvelopeFormat + "\n")
	result.WriteString("ENVELOPE-VERSION: 1\n")
	for _, pair := range common {
		result.WriteString(pair[0] + ": " + pair[1] + "\n")
	}
	result.WriteString("RECORD-COMPLETE: true\n")
	result.Write(envelopeLine)
	result.WriteByte('\n')
	return result.Bytes(), nil
}

func resultFor(record Record, evidence map[string][]byte) (Result, error) {
	record.Payload = bytes.Clone(record.Payload)
	encoded, err := buildRecord(record)
	if err != nil {
		return Result{}, err
	}
	copied := make(map[string][]byte, len(evidence))
	for key, value := range evidence {
		copied[key] = bytes.Clone(value)
	}
	return Result{Record: record, Bytes: encoded, Evidence: copied}, nil
}

func isASCII(value string) bool {
	for _, character := range value {
		if character > 127 {
			return false
		}
	}
	return true
}
