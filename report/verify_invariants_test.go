package report

import (
	"bytes"
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/schema"
)

func TestVerifyRejectsReframedMetadataContradictions(t *testing.T) {
	repository, environment := newGitRepository(t)
	writeFileTest(t, filepath.Join(repository, "file.txt"), []byte("one\n"))
	runGitTest(t, repository, nil, "add", "file.txt")
	commit := commitTest(t, repository, environment, "root", "", false)
	service, err := New(Options{Repository: repository})
	if err != nil {
		t.Fatal(err)
	}
	show, err := service.Show(context.Background(), ShowRequest{
		RequestMetadata: RequestMetadata{Phase: "CHECK", Result: "passed", FinalGate: "gate"},
		Commit:          commit, StatusDoc: "status.md",
	})
	if err != nil {
		t.Fatal(err)
	}
	// Make the fixture edit visible even when filesystem stat times coincide.
	writeFileTest(t, filepath.Join(repository, "file.txt"), []byte("two changed\n"))
	diff, err := service.Diff(context.Background(), DiffRequest{RequestMetadata: RequestMetadata{Phase: "CHECK", Result: "passed", FinalGate: "gate"}})
	if err != nil {
		t.Fatal(err)
	}
	for _, original := range []Result{show, diff} {
		if _, err := Verify(context.Background(), original.Bytes); err != nil {
			t.Fatal(err)
		}
	}
	cases := []struct {
		name     string
		original Result
		from, to string
	}{
		{"show-count-type", show, "FILES-CHANGED: 1", "FILES-CHANGED: banana"},
		{"show-count-value", show, "FILES-CHANGED: 1", "FILES-CHANGED: 2"},
		{"show-parent-count", show, "PARENT-COUNT: 0", "PARENT-COUNT: 1"},
		{"show-root-flag", show, "ROOT-COMMIT: true", "ROOT-COMMIT: false"},
		{"show-merge-type", show, "MERGE-COMMIT: false", "MERGE-COMMIT: maybe"},
		{"show-patch-mode", show, "PATCH-MODE: root", "PATCH-MODE: single-parent"},
		{"show-related-field", show, "RELATED-OPERATIONAL-REPORT: NONE", "RELATED-OPERATIONAL-REPORT: bogus"},
		{"diff-count-type", diff, "FILES-CHANGED: 1", "FILES-CHANGED: -1"},
		{"diff-count-value", diff, "FILES-CHANGED: 1", "FILES-CHANGED: 2"},
		{"diff-index-mode", diff, "INDEX-MODE: regular", "INDEX-MODE: imaginary"},
	}
	for _, item := range cases {
		t.Run(item.name, func(t *testing.T) {
			record := item.original.Record
			if !bytes.Contains(record.Payload, []byte(item.from)) {
				t.Fatal("mutation prerequisite absent")
			}
			record.Payload = bytes.Replace(record.Payload, []byte(item.from), []byte(item.to), 1)
			encoded, err := buildRecord(record)
			if err != nil {
				t.Fatal(err)
			}
			if _, err := Verify(context.Background(), encoded); err == nil {
				t.Fatal("reframed semantic contradiction accepted")
			}
		})
	}
}

func TestOperationalValidationKeepsOptionalStandalonePrimaryFields(t *testing.T) {
	commit := strings.Repeat("a", 40)
	source := []byte("report_schema: operational-report-v1\nphase: CHECK\noutcome: passed\nprimary_commit: " + commit + "\n")
	_, err := Operational(context.Background(), OperationalRequest{
		RequestMetadata: RequestMetadata{Phase: "CHECK", Result: "passed", FinalGate: "gate"},
		Project:         "project", SourceName: "ops.txt", Source: source,
	}, nil)
	if err != nil {
		t.Fatalf("well-formed optional standalone primary field rejected: %v", err)
	}
}

func TestVerifierAndAppendRejectOperationalBodyMismatch(t *testing.T) {
	request := OperationalRequest{RequestMetadata: RequestMetadata{Phase: "CHECK", Result: "passed", FinalGate: "gate"}, Project: "project", SourceName: "ops.txt"}
	sourceBytes := []byte("report_schema: operational-report-v1\nphase: WRONG\noutcome: passed\n")
	source, err := parseOperationalSource("ops.txt", sourceBytes)
	if err != nil {
		t.Fatal(err)
	}
	id := "OPERATIONAL-REPORT-" + schema.SHA256(sourceBytes)
	payload, err := renderOperationalPayload(request, source, id, schema.SHA256(sourceBytes), "NONE", "NONE", "")
	if err != nil {
		t.Fatal(err)
	}
	record := Record{Kind: schema.OperationalRecord, FormatVersion: 1, ID: id, Project: "project", Phase: "CHECK", Payload: payload}
	encoded, err := buildRecord(record)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := Verify(context.Background(), encoded); err == nil {
		t.Fatal("persisted body phase mismatch accepted")
	}
	outbox := filepath.Join(t.TempDir(), "untouched")
	if _, err := Append(context.Background(), AppendRequest{OutboxRoot: outbox, Project: "project", Phase: "CHECK", Record: record}); err == nil {
		t.Fatal("direct append body phase mismatch accepted")
	}
	if _, err := os.Stat(outbox); !os.IsNotExist(err) {
		t.Fatal("invalid record reached filesystem preparation")
	}
}

func TestVerifyMalformedSectionLengthsNeverPanic(t *testing.T) {
	paths, err := filepath.Glob("testdata/persisted/*.report.txt")
	if err != nil || len(paths) == 0 {
		t.Fatalf("persisted fixtures missing: %v", err)
	}
	for _, path := range paths {
		content, err := os.ReadFile(path)
		if err != nil {
			t.Fatal(err)
		}
		records, err := ParseRecords(content)
		if err != nil {
			t.Fatal(err)
		}
		for _, record := range records {
			// Reframe truncated inner sections with valid outer hashes, so envelope
			// rejection cannot hide an inner parser panic.
			for _, marker := range []string{"BEGIN INTEGRITY SUMMARY", "END PATCH", "BEGIN PATCH", "END OPERATIONAL REPORT BODY"} {
				position := bytes.Index(record.Payload, []byte(marker))
				if position < 0 {
					continue
				}
				candidate := record
				candidate.Payload = bytes.Clone(record.Payload[position:])
				encoded, err := buildRecord(candidate)
				if err != nil {
					t.Fatal(err)
				}
				if _, err := Verify(context.Background(), encoded); err == nil {
					t.Fatal("truncated payload accepted")
				}
			}
		}
	}
}
