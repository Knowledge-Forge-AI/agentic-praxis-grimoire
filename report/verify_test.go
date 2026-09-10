package report

import (
	"bytes"
	"context"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestVerifyPersistedFixtures(t *testing.T) {
	fixtureDir := filepath.Join(repositoryRootForTest(t), "report", "testdata", "persisted")

	cases := []struct {
		filename             string
		expectedRecordCount  int
		expectedCompatLimit  bool
	}{
		{
			filename:            "show_40hex.report.txt",
			expectedRecordCount: 1,
			expectedCompatLimit: false,
		},
		{
			filename:            "diff.report.txt",
			expectedRecordCount: 1,
			expectedCompatLimit: false,
		},
		{
			filename:            "standalone_legacy.ops.report.txt",
			expectedRecordCount: 1,
			expectedCompatLimit: true,
		},
		{
			filename:            "standalone_freeform.ops.report.txt",
			expectedRecordCount: 1,
			expectedCompatLimit: true,
		},
		{
			filename:            "structured_associated.ops.report.txt",
			expectedRecordCount: 1,
			expectedCompatLimit: true,
		},
		{
			filename:            "legacy_omnibus.report.txt",
			expectedRecordCount: 3,
			expectedCompatLimit: true,
		},
		{filename: "historical_unknown_schema.ops.report.txt", expectedRecordCount: 1, expectedCompatLimit: true},
		{filename: "historical_primary_scalar.ops.report.txt", expectedRecordCount: 1, expectedCompatLimit: true},
	}

	for _, tc := range cases {
		t.Run(tc.filename, func(t *testing.T) {
			path := filepath.Join(fixtureDir, tc.filename)

			// 1. Verify file via VerifyFile
			vf, err := VerifyFile(context.Background(), path)
			if err != nil {
				t.Fatalf("VerifyFile failed for %s: %v", tc.filename, err)
			}
			if vf.RecordCount != tc.expectedRecordCount {
				t.Errorf("VerifyFile RecordCount = %d, expected %d", vf.RecordCount, tc.expectedRecordCount)
			}
			if vf.CompatibilityLimited != tc.expectedCompatLimit {
				t.Errorf("VerifyFile CompatibilityLimited = %v, expected %v", vf.CompatibilityLimited, tc.expectedCompatLimit)
			}

			// 2. Verify bytes via Verify
			content, err := os.ReadFile(path)
			if err != nil {
				t.Fatal(err)
			}
			v, err := Verify(context.Background(), content)
			if err != nil {
				t.Fatalf("Verify failed for %s: %v", tc.filename, err)
			}
			if v.RecordCount != tc.expectedRecordCount {
				t.Errorf("Verify RecordCount = %d, expected %d", v.RecordCount, tc.expectedRecordCount)
			}
			if v.CompatibilityLimited != tc.expectedCompatLimit {
				t.Errorf("Verify CompatibilityLimited = %v, expected %v", v.CompatibilityLimited, tc.expectedCompatLimit)
			}
		})
	}
}

func TestVerifyEmptyAndParseRecordsCompatibility(t *testing.T) {
	// ParseRecords empty is valid
	records, err := ParseRecords([]byte{})
	if err != nil || len(records) != 0 {
		t.Fatalf("ParseRecords on empty bytes failed: err=%v records=%d", err, len(records))
	}

	// Verify empty is non-success ErrEmptyReport
	_, err = Verify(context.Background(), []byte{})
	if !errors.Is(err, ErrEmptyReport) {
		t.Fatalf("expected ErrEmptyReport for empty bytes, got %v", err)
	}

	_, err = Verify(context.Background(), []byte("   \n\t  \n"))
	if !errors.Is(err, ErrEmptyReport) {
		t.Fatalf("expected ErrEmptyReport for whitespace bytes, got %v", err)
	}

	// VerifyFile empty file is non-success ErrEmptyReport
	emptyFile := filepath.Join(t.TempDir(), "empty.report.txt")
	writeFileTest(t, emptyFile, []byte{})
	_, err = VerifyFile(context.Background(), emptyFile)
	if !errors.Is(err, ErrEmptyReport) {
		t.Fatalf("expected ErrEmptyReport for empty file, got %v", err)
	}
}

func TestVerifyFileSafeBoundedErrorsNoPathsOrPayloads(t *testing.T) {
	secretPath := filepath.Join(t.TempDir(), "super_secret_dir", "secret_report.txt")

	_, err := VerifyFile(context.Background(), secretPath)
	if err == nil {
		t.Fatal("expected error for non-existent file")
	}
	if !errors.Is(err, ErrVerifyIO) {
		t.Fatalf("expected ErrVerifyIO, got %v", err)
	}
	errStr := err.Error()
	if strings.Contains(errStr, "super_secret_dir") || strings.Contains(errStr, "secret_report.txt") {
		t.Fatalf("error message leaked file path: %s", errStr)
	}

	// Empty path
	_, err = VerifyFile(context.Background(), "")
	if !errors.Is(err, ErrVerifyIO) {
		t.Fatalf("expected ErrVerifyIO for empty path, got %v", err)
	}

	// Directory path
	dirPath := t.TempDir()
	_, err = VerifyFile(context.Background(), dirPath)
	if !errors.Is(err, ErrVerifyIO) {
		t.Fatalf("expected ErrVerifyIO for directory, got %v", err)
	}
	if strings.Contains(err.Error(), dirPath) {
		t.Fatalf("error message leaked directory path: %s", err.Error())
	}
}

func TestVerifyFileStabilityObservation(t *testing.T) {
	// Verify that a file modified during observation or replaced fails safely
	fixtureDir := filepath.Join(repositoryRootForTest(t), "report", "testdata", "persisted")
	validBytes, err := os.ReadFile(filepath.Join(fixtureDir, "show_40hex.report.txt"))
	if err != nil {
		t.Fatal(err)
	}

	testFile := filepath.Join(t.TempDir(), "test.report.txt")
	writeFileTest(t, testFile, validBytes)

	// Valid read should succeed
	v, err := VerifyFile(context.Background(), testFile)
	if err != nil || v.RecordCount != 1 {
		t.Fatalf("expected success, got v=%v err=%v", v, err)
	}
}

func TestVerifyDelimiterLikeMessageAndPatch(t *testing.T) {
	repository, environment := newGitRepository(t)

	// Commit message that contains tricky delimiter-like strings
	subject := "test: delimiter-like message"
	body := strings.Join([]string{
		"--------------------------------------------------------------------------------",
		"BEGIN PATCH",
		"--------------------------------------------------------------------------------",
		"some tricky message text",
		"--------------------------------------------------------------------------------",
		"END COMMIT MESSAGE",
		"--------------------------------------------------------------------------------",
	}, "\n")

	// File content with tricky patch lines
	patchTrickyContent := strings.Join([]string{
		"content before",
		"--------------------------------------------------------------------------------",
		"END PATCH",
		"--------------------------------------------------------------------------------",
		"BEGIN INTEGRITY SUMMARY",
		"--------------------------------------------------------------------------------",
		"content after",
	}, "\n") + "\n"

	writeFileTest(t, filepath.Join(repository, "tricky.txt"), []byte(patchTrickyContent))
	runGitTest(t, repository, nil, "add", "tricky.txt")
	commitHash := commitTest(t, repository, environment, subject, body, false)

	svc, err := New(Options{Repository: repository})
	if err != nil {
		t.Fatal(err)
	}

	showRes, err := svc.Show(context.Background(), ShowRequest{
		RequestMetadata: RequestMetadata{Phase: "DELIM-TEST", Result: "passed", FinalGate: "gate"},
		Commit:          commitHash,
		StatusDoc:       "status.md",
	})
	if err != nil {
		t.Fatalf("Show failed: %v", err)
	}

	// Verify must handle delimiter-like message and patch correctly through cryptographic hash anchoring
	v, err := Verify(context.Background(), showRes.Bytes)
	if err != nil {
		t.Fatalf("Verify failed on delimiter-like commit message and patch: %v", err)
	}
	if v.RecordCount != 1 || v.CompatibilityLimited {
		t.Fatalf("unexpected verification result: %+v", v)
	}
}

func TestVerifyDiffExactAndTrimmedCandidates(t *testing.T) {
	repository, _ := initializeDiffRepository(t)

	// Modify tracked.txt with content that causes status/staged/unstaged to have various endings
	writeFileTest(t, filepath.Join(repository, "tracked.txt"), []byte("tracked\nupdated content\n"))

	svc, err := New(Options{Repository: repository})
	if err != nil {
		t.Fatal(err)
	}

	diffRes, err := svc.Diff(context.Background(), DiffRequest{
		RequestMetadata: RequestMetadata{Phase: "DIFF-TEST", Result: "passed", FinalGate: "gate"},
		StatusDoc:       "status.md",
	})
	if err != nil {
		t.Fatalf("Diff failed: %v", err)
	}

	// Verify directly proves state identity from persisted hashes without Git
	v, err := Verify(context.Background(), diffRes.Bytes)
	if err != nil {
		t.Fatalf("Verify failed on diff record: %v", err)
	}
	if v.RecordCount != 1 || v.CompatibilityLimited {
		t.Fatalf("unexpected verification result: %+v", v)
	}
}

func TestValidateOperationalRecordHistoricalVsStrict(t *testing.T) {
	// Canonical operational record
	canonicalBody := []byte("report_schema: operational-report-v1\nphase: OPS-CHECK\noutcome: passed\n")
	res, err := Operational(context.Background(), OperationalRequest{
		RequestMetadata: RequestMetadata{Phase: "OPS-CHECK", Result: "passed", FinalGate: "gate"},
		Project:         "test-proj",
		SourceName:      "ops.txt",
		Source:          canonicalBody,
	}, nil)
	if err != nil {
		t.Fatal(err)
	}

	// Both strict (historical=false) and historical (historical=true) pass on canonical
	if err := validateOperationalRecord(res.Record, false); err != nil {
		t.Fatalf("validateOperationalRecord(false) failed on canonical record: %v", err)
	}
	if err := validateOperationalRecord(res.Record, true); err != nil {
		t.Fatalf("validateOperationalRecord(true) failed on canonical record: %v", err)
	}

	// Corrupted operational record (payload truncated)
	corruptedRecord := res.Record
	corruptedRecord.Payload = corruptedRecord.Payload[:len(corruptedRecord.Payload)-20]
	if err := validateOperationalRecord(corruptedRecord, false); err == nil {
		t.Fatal("expected failure on corrupted payload in strict mode")
	}
	if err := validateOperationalRecord(corruptedRecord, true); err == nil {
		t.Fatal("expected failure on corrupted payload in historical mode")
	}
}

func TestVerifyCorruptedRecords(t *testing.T) {
	fixtureDir := filepath.Join(repositoryRootForTest(t), "report", "testdata", "persisted")
	validBytes, err := os.ReadFile(filepath.Join(fixtureDir, "show_40hex.report.txt"))
	if err != nil {
		t.Fatal(err)
	}

	// Corrupt payload hash in envelope
	corruptedHeader := bytes.Replace(validBytes, []byte("PAYLOAD-SHA256: "), []byte("PAYLOAD-SHA256: 0000000000000000000000000000000000000000000000000000000000000000"), 1)
	if _, err := Verify(context.Background(), corruptedHeader); !errors.Is(err, ErrCompatibility) {
		t.Fatalf("expected ErrCompatibility on corrupted payload sha, got %v", err)
	}

	// Corrupt section hash in integrity summary
	corruptedIntegrity := bytes.Replace(validBytes, []byte("PATCH-SHA256: "), []byte("PATCH-SHA256: 0000000000000000000000000000000000000000000000000000000000000000"), 1)
	if _, err := Verify(context.Background(), corruptedIntegrity); !errors.Is(err, ErrCompatibility) {
		t.Fatalf("expected ErrCompatibility on corrupted integrity hash, got %v", err)
	}
}
