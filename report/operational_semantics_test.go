package report

import (
	"bytes"
	"context"
	"errors"
	"testing"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/schema"
)

func TestParserIntegerOverflowProtection(t *testing.T) {
	record := Record{
		Kind:          schema.OperationalRecord,
		FormatVersion: 1,
		ID:            "OPERATIONAL-REPORT-" + string(bytes.Repeat([]byte{'a'}, 64)),
		Project:       "project",
		Phase:         "APG127",
		Payload:       []byte("payload\n"),
	}
	encoded, err := buildRecord(record)
	if err != nil {
		t.Fatal(err)
	}

	// Craft payload with integer overflow in PAYLOAD-SIZE-BYTES
	overflowPayload := bytes.Replace(
		bytes.Clone(encoded),
		[]byte("PAYLOAD-SIZE-BYTES: 8"),
		[]byte("PAYLOAD-SIZE-BYTES: 9223372036854775800"),
		1,
	)

	// This should fail safely with ErrCompatibility rather than panicking on slice bounds overflow
	defer func() {
		if r := recover(); r != nil {
			t.Fatalf("ParseRecords panicked on integer overflow payload: %v", r)
		}
	}()

	if _, err := ParseRecords(overflowPayload); !errors.Is(err, ErrCompatibility) {
		t.Fatalf("expected ErrCompatibility on overflow payload, got %v", err)
	}
}

func TestOperationalRejectUnsupportedDeclaredSchema(t *testing.T) {
	cases := []struct {
		name string
		body []byte
	}{
		{
			name: "unsupported-schema-name",
			body: []byte("report_schema: unsupported-schema-v1\nphase: OPS\noutcome: passed\n"),
		},
		{
			name: "future-schema-v2",
			body: []byte("report_schema: operational-report-v2\nphase: OPS\noutcome: passed\n"),
		},
		{
			name: "unsupported-with-legacy-fields",
			body: []byte("report_schema: custom\nphase: OPS\noutcome: passed\ncustom: value\n"),
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			_, err := Operational(context.Background(), OperationalRequest{
				RequestMetadata: RequestMetadata{Phase: "OPS", Result: "passed", FinalGate: "gate"},
				Project:         "project",
				SourceName:      "ops.txt",
				Source:          tc.body,
			}, nil)
			if err == nil {
				t.Fatalf("expected error for unsupported report_schema, got nil")
			}
			if !errors.Is(err, ErrInvalidRequest) {
				t.Fatalf("expected ErrInvalidRequest for unsupported report_schema, got %v", err)
			}
		})
	}
}

func TestOperationalRejectMalformedRecognizedStandaloneFieldsAndRelations(t *testing.T) {

	cases := []struct {
		name      string
		body      []byte
		reqCommit string
		reqDiffID string
		wantErrIs error
	}{
		{
			name:      "standalone-malformed-primary-commit",
			body:      []byte("report_schema: operational-report-v1\nphase: OPS\noutcome: passed\nprimary_commit: not-a-hex-hash\n"),
			wantErrIs: ErrInvalidRequest,
		},
		{
			name:      "standalone-short-primary-commit",
			body:      []byte("report_schema: operational-report-v1\nphase: OPS\noutcome: passed\nprimary_commit: 123456\n"),
			wantErrIs: ErrInvalidRequest,
		},
		{
			name:      "standalone-malformed-primary-git-report-id",
			body:      []byte("report_schema: operational-report-v1\nphase: OPS\noutcome: passed\nprimary_git_report_id: not-a-report-id\n"),
			wantErrIs: ErrInvalidRequest,
		},
		{
			name:      "malformed-request-related-commit",
			body:      []byte("report_schema: operational-report-v1\nphase: OPS\noutcome: passed\n"),
			reqCommit: "not-a-valid-commit-input-too-short",
			wantErrIs: ErrInvalidRequest,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			_, err := Operational(context.Background(), OperationalRequest{
				RequestMetadata:    RequestMetadata{Phase: "OPS", Result: "passed", FinalGate: "gate"},
				Project:            "project",
				SourceName:         "ops.txt",
				Source:             tc.body,
				RelatedCommit:      tc.reqCommit,
				RelatedGitReportID: tc.reqDiffID,
			}, nil)
			if err == nil {
				t.Fatalf("expected error for malformed recognized field/relation, got nil")
			}
			if tc.wantErrIs != nil && !errors.Is(err, tc.wantErrIs) {
				t.Fatalf("expected error Is %v, got %v", tc.wantErrIs, err)
			}
		})
	}
}

func TestOperationalPreserveOpaqueVocabularyAndUnknownFields(t *testing.T) {
	// Unknown fields in operational-report-v1 must remain opaque and accepted
	body := []byte("report_schema: operational-report-v1\nphase: OPS\noutcome: passed\nunknown_custom_field: custom value\nanother_field: 12345\n")
	res, err := Operational(context.Background(), OperationalRequest{
		RequestMetadata: RequestMetadata{Phase: "OPS", Result: "passed", FinalGate: "gate"},
		Project:         "custom-project",
		SourceName:      "ops.txt",
		Source:          body,
	}, nil)
	if err != nil {
		t.Fatalf("unexpected error for opaque unknown fields: %v", err)
	}
	if !bytes.Contains(res.Record.Payload, []byte("unknown_custom_field: custom value")) {
		t.Fatalf("expected custom field preserved in payload")
	}

	// Optional / custom result vocabulary remains opaque
	res2, err := Operational(context.Background(), OperationalRequest{
		RequestMetadata: RequestMetadata{Phase: "OPS", Result: "custom-status-verified", FinalGate: "gate"},
		Project:         "custom-project",
		SourceName:      "ops.txt",
		Source:          []byte("report_schema: operational-report-v1\nphase: OPS\noutcome: custom-status-verified\n"),
	}, nil)
	if err != nil {
		t.Fatalf("unexpected error for custom outcome vocabulary: %v", err)
	}
	if res2.Record.Project != "custom-project" {
		t.Fatalf("unexpected project: %s", res2.Record.Project)
	}
}
