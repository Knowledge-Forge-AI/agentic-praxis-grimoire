package report

import (
	"bytes"
	"context"
	"crypto/sha256"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"testing"
	"time"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/schema"
)

type stepCancelContext struct {
	cancelAfter int
	calls       int
}

func newStepCancelContext(cancelAfter int) *stepCancelContext {
	return &stepCancelContext{cancelAfter: cancelAfter}
}

func (c *stepCancelContext) Deadline() (time.Time, bool) { return time.Time{}, false }
func (c *stepCancelContext) Done() <-chan struct{}       { return nil }
func (c *stepCancelContext) Value(key any) any           { return nil }
func (c *stepCancelContext) Err() error {
	c.calls++
	if c.calls >= c.cancelAfter {
		return context.Canceled
	}
	return nil
}

func generateDelimiterRichPatch(targetBytes int) []byte {
	delim := envelopeBytes(sectionLine, "END PATCH")
	var buf bytes.Buffer
	buf.WriteString("diff --git a/file.txt b/file.txt\n--- a/file.txt\n+++ b/file.txt\n@@ -1,1 +1,1 @@\n")
	line := []byte("+content line before embedded delimiter\n")
	for buf.Len() < targetBytes {
		buf.Write(line)
		buf.Write(delim)
	}
	buf.WriteString("+final line of patch\n")
	return buf.Bytes()
}

func buildDelimiterRichShowReport(t *testing.T, targetBytes int, valid bool) []byte {
	t.Helper()
	patch := generateDelimiterRichPatch(targetBytes)
	commit := "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
	metadata := commitMetadata{
		commit:         commit,
		parents:        "NONE",
		authorName:     "Author",
		authorEmail:    "author@example.com",
		authorDate:     "2026-09-09T00:00:00Z",
		committerName:  "Committer",
		committerEmail: "committer@example.com",
		committerDate:  "2026-09-09T00:00:00Z",
		subject:        "Test delimiter scaling commit",
	}
	basis := comparison{
		parentsValue: "NONE",
		rootCommit:   "true",
		mergeCommit:  "false",
		patchMode:    "root",
	}
	request := ShowRequest{
		RequestMetadata: RequestMetadata{Phase: "APG129-SCALE", Result: "passed", FinalGate: "gate"},
		Commit:          commit,
		StatusDoc:       "status.md",
	}
	evidence := showEvidence{
		changed:    []byte("file.txt\n"),
		numstatRaw: []byte("1\t0\tfile.txt\n"),
		numstat:    []byte("COLUMNS: ADDED-LINES\tDELETED-LINES\tPATH\nBINARY-MARKER: -\n1\t0\tfile.txt\n"),
		message:    []byte("Test delimiter scaling commit\n"),
		patch:      patch,
	}

	record, err := renderShowRecord(request, request.StatusDoc, "test-repo", metadata, basis, evidence)
	if err != nil {
		t.Fatalf("renderShowRecord failed: %v", err)
	}

	if !valid {
		oldHash := schema.SHA256(evidence.patch)
		corruptedHash := "0000000000000000000000000000000000000000000000000000000000000000"
		if oldHash == corruptedHash {
			corruptedHash = "1111111111111111111111111111111111111111111111111111111111111111"
		}
		record.Payload = bytes.Replace(record.Payload, []byte("PATCH-SHA256: "+oldHash), []byte("PATCH-SHA256: "+corruptedHash), 1)
	}

	envelope, err := buildRecord(record)
	if err != nil {
		t.Fatalf("buildRecord failed: %v", err)
	}
	return envelope
}

func TestVerifyDelimiterRichScaling(t *testing.T) {
	sizes := []struct {
		name  string
		bytes int
	}{
		{name: "256KiB", bytes: 256 * 1024},
		{name: "1MiB", bytes: 1024 * 1024},
		{name: "4MiB", bytes: 4 * 1024 * 1024},
		{name: "16MiB", bytes: 16 * 1024 * 1024},
	}

	for _, tc := range sizes {
		t.Run(tc.name+"/valid", func(t *testing.T) {
			content := buildDelimiterRichShowReport(t, tc.bytes, true)

			start := time.Now()
			v, stats, err := verifyWithStats(context.Background(), content)
			elapsed := time.Since(start)

			if err != nil {
				t.Fatalf("verifyWithStats failed on valid delimiter-rich %s: %v", tc.name, err)
			}
			if v.RecordCount != 1 {
				t.Errorf("expected 1 record, got %d", v.RecordCount)
			}
			if stats.candidateCount <= 10 {
				t.Errorf("expected >10 candidates for %s, got %d", tc.name, stats.candidateCount)
			}
			maxAllowedWork := int64(len(content)) * 3
			if stats.hashedBytes > maxAllowedWork {
				t.Errorf("HashedBytes %d exceeded bounded bound %d for %s", stats.hashedBytes, maxAllowedWork, tc.name)
			}

			// Public Verify API parity
			publicV, err := Verify(context.Background(), content)
			if err != nil || publicV.RecordCount != 1 {
				t.Errorf("public Verify mismatch: %+v, err: %v", publicV, err)
			}

			// VerifyFile parity
			tmpFile := filepath.Join(t.TempDir(), "report.txt")
			if err := os.WriteFile(tmpFile, content, 0600); err != nil {
				t.Fatal(err)
			}
			vf, fStats, err := verifyFileWithStats(context.Background(), tmpFile)
			_ = os.Remove(tmpFile)
			if err != nil {
				t.Fatalf("verifyFileWithStats failed on valid %s: %v", tc.name, err)
			}
			if vf.RecordCount != 1 || fStats.candidateCount != stats.candidateCount {
				t.Errorf("VerifyFile mismatch: vf=%+v v=%+v fStats=%+v stats=%+v", vf, v, fStats, stats)
			}

			t.Logf("[%s valid] payload_len=%d candidates=%d hashed_bytes=%d elapsed=%v",
				tc.name, len(content), stats.candidateCount, stats.hashedBytes, elapsed)
			// Do not retain 16MiB data
			content = nil
		})

		t.Run(tc.name+"/invalid", func(t *testing.T) {
			content := buildDelimiterRichShowReport(t, tc.bytes, false)

			start := time.Now()
			_, stats, err := verifyWithStats(context.Background(), content)
			elapsed := time.Since(start)

			if err == nil {
				t.Fatalf("expected error on invalid %s, got nil", tc.name)
			}
			if !errors.Is(err, ErrCompatibility) {
				t.Errorf("expected ErrCompatibility, got %v", err)
			}
			if stats.hashedBytes > int64(len(content))*3 {
				t.Fatalf("invalid-input extraction exceeded linear hash work: %d bytes for %d input bytes", stats.hashedBytes, len(content))
			}

			// VerifyFile parity
			tmpFile := filepath.Join(t.TempDir(), "report_invalid.txt")
			if err := os.WriteFile(tmpFile, content, 0600); err != nil {
				t.Fatal(err)
			}
			_, _, vfErr := verifyFileWithStats(context.Background(), tmpFile)
			_ = os.Remove(tmpFile)
			if vfErr == nil || !errors.Is(vfErr, ErrCompatibility) {
				t.Errorf("VerifyFile expected ErrCompatibility on invalid %s, got %v", tc.name, vfErr)
			}

			t.Logf("[%s invalid] payload_len=%d candidates=%d hashed_bytes=%d error=%v elapsed=%v",
				tc.name, len(content), stats.candidateCount, stats.hashedBytes, err, elapsed)
			// Do not retain 16MiB data
			content = nil
		})
	}
}

func TestDeterministicMidWorkCancellation(t *testing.T) {
	t.Run("hashed_midwork", func(t *testing.T) {
		content := buildDelimiterRichShowReport(t, 1024*1024, true)
		defer func() { content = nil }()

		// Pre-canceled (cancelAfter=1)
		ctx1 := newStepCancelContext(1)
		_, err := Verify(ctx1, content)
		if !errors.Is(err, context.Canceled) {
			t.Fatalf("expected context.Canceled on check 1, got %v", err)
		}

		// Mid-work canceled (cancelAfter=5)
		ctx5 := newStepCancelContext(5)
		_, err = Verify(ctx5, content)
		if !errors.Is(err, context.Canceled) {
			t.Fatalf("expected context.Canceled on check 5, got %v", err)
		}
		if ctx5.calls < 5 {
			t.Errorf("expected at least 5 calls to ctx.Err(), got %d", ctx5.calls)
		}
	})

	t.Run("no_hash_midwork", func(t *testing.T) {
		// Large buffer with needle only at the very end
		size := 256 * 1024
		buf := make([]byte, size)
		needle := []byte("DELIMITER_AT_END")
		copy(buf[size-len(needle):], needle)

		// cancelAfter=2 should interrupt before reaching the end
		ctx := newStepCancelContext(2)
		idx, err := indexWithContext(ctx, buf, needle)
		if !errors.Is(err, context.Canceled) {
			t.Fatalf("expected context.Canceled, got idx=%d, err=%v", idx, err)
		}
		if ctx.calls < 2 {
			t.Errorf("expected at least 2 calls, got %d", ctx.calls)
		}
	})

	t.Run("sized_midwork", func(t *testing.T) {
		// 256 KiB hashed in 64 KiB chunks
		size := 256 * 1024
		data := make([]byte, size)
		ctx := newStepCancelContext(3)
		stats := &envelopeExtractionStats{}
		_, err := sha256WithContext(ctx, data, stats)
		if !errors.Is(err, context.Canceled) {
			t.Fatalf("expected context.Canceled, got %v", err)
		}
		if ctx.calls < 3 {
			t.Errorf("expected at least 3 calls, got %d", ctx.calls)
		}
		if stats.hashedBytes > 2*cancelQuantum {
			t.Errorf("expected work bounded by cancellation, got hashedBytes=%d", stats.hashedBytes)
		}
	})

	t.Run("no_match_midwork", func(t *testing.T) {
		// 256 KiB buffer with no delimiter matching
		data := make([]byte, 256*1024)
		needle := []byte("NON_EXISTENT_DELIMITER")
		ctx := newStepCancelContext(3)
		idx, err := indexWithContext(ctx, data, needle)
		if !errors.Is(err, context.Canceled) {
			t.Fatalf("expected context.Canceled, got idx=%d, err=%v", idx, err)
		}
		if ctx.calls < 3 {
			t.Errorf("expected at least 3 calls, got %d", ctx.calls)
		}
	})

	t.Run("reverse_integrity_search_midwork", func(t *testing.T) {
		// 256 KiB payload where BEGIN INTEGRITY SUMMARY is near the front (so backwards search has to traverse multiple windows)
		data := make([]byte, 256*1024)
		needle := []byte("BEGIN INTEGRITY SUMMARY")
		copy(data[100:], needle)

		ctx := newStepCancelContext(2)
		pos, err := lastIndexWithContext(ctx, data, needle)
		if !errors.Is(err, context.Canceled) {
			t.Fatalf("expected context.Canceled, got pos=%d, err=%v", pos, err)
		}
		if ctx.calls < 2 {
			t.Errorf("expected at least 2 calls, got %d", ctx.calls)
		}
	})

	t.Run("file_read_loop_midwork", func(t *testing.T) {
		content := make([]byte, 256*1024)
		tmpFile := filepath.Join(t.TempDir(), "large_file.txt")
		if err := os.WriteFile(tmpFile, content, 0600); err != nil {
			t.Fatal(err)
		}
		defer os.Remove(tmpFile)

		ctx := newStepCancelContext(2)
		_, err := VerifyFile(ctx, tmpFile)
		if !errors.Is(err, context.Canceled) {
			t.Fatalf("expected VerifyFile context.Canceled, got %v", err)
		}
		if ctx.calls < 2 {
			t.Errorf("expected at least 2 calls, got %d", ctx.calls)
		}
	})
}

func TestDelimitersSplitAtWindowBoundaries(t *testing.T) {
	quantum := cancelQuantum // 64 KiB = 65536
	delim := envelopeBytes(sectionLine, "END PATCH")
	delimLen := len(delim)

	// Test offsets around quantum boundary
	offsets := []int{
		quantum - delimLen + 1, // split: delimiter starts so it straddles boundary
		quantum - 10,
		quantum - 1,
		quantum,
		quantum + 1,
		quantum + 10,
		quantum*2 - delimLen/2,
	}

	for _, off := range offsets {
		t.Run(fmt.Sprintf("forward_offset_%d", off), func(t *testing.T) {
			totalLen := quantum*3 + 1024
			buf := make([]byte, totalLen)
			// Fill with non-delimiter data
			for i := range buf {
				buf[i] = 'A'
			}
			copy(buf[off:], delim)

			expected := bytes.Index(buf, delim)
			if expected != off {
				t.Fatalf("setup error: expected %d, got %d", off, expected)
			}

			actual, err := indexWithContext(context.Background(), buf, delim)
			if err != nil {
				t.Fatalf("indexWithContext failed: %v", err)
			}
			if actual != expected {
				t.Errorf("offset %d: expected index %d, got %d", off, expected, actual)
			}
		})

		t.Run(fmt.Sprintf("reverse_offset_%d", off), func(t *testing.T) {
			totalLen := quantum*3 + 1024
			buf := make([]byte, totalLen)
			for i := range buf {
				buf[i] = 'B'
			}
			copy(buf[off:], delim)

			expected := bytes.LastIndex(buf, delim)
			if expected != off {
				t.Fatalf("setup error: expected %d, got %d", off, expected)
			}

			actual, err := lastIndexWithContext(context.Background(), buf, delim)
			if err != nil {
				t.Fatalf("lastIndexWithContext failed: %v", err)
			}
			if actual != expected {
				t.Errorf("offset %d: expected lastIndex %d, got %d", off, expected, actual)
			}
		})
	}
}

func TestCanonicalCompatibilityRawNewlineEmptyOneLFTwoLF(t *testing.T) {
	cases := []struct {
		name       string
		raw        []byte
		framed     []byte
		rawNewline bool
	}{
		{name: "empty", raw: []byte{}, framed: []byte{}, rawNewline: true},
		{name: "oneLF", raw: []byte("\n"), framed: []byte("\n"), rawNewline: true},
		{name: "twoLF", raw: []byte("\n\n"), framed: []byte("\n\n"), rawNewline: true},
		{name: "rawWithoutNewline", raw: []byte("raw line without newline"), framed: []byte("raw line without newline\n"), rawNewline: true},
		{name: "rawWithSingleNewline", raw: []byte("already has newline\n"), framed: []byte("already has newline\n"), rawNewline: true},
	}

	for _, tc := range cases {
		t.Run("candidate/"+tc.name, func(t *testing.T) {
			spec := sectionSpec{name: "TEST", hash: "TEST-SHA256", rawNewline: tc.rawNewline}
			integrity := map[string]string{
				"TEST-SHA256": schema.SHA256(tc.raw),
			}
			extracted, ok := sectionHashCandidate(tc.framed, spec, integrity)
			if !ok {
				t.Fatalf("expected candidate match for %s", tc.name)
			}
			if !bytes.Equal(extracted, tc.raw) {
				t.Errorf("expected extracted=%q, got %q", tc.raw, extracted)
			}
		})
	}

	// Sized section with rawNewline empty, oneLF, twoLF, rawWithoutNewline
	for _, tc := range cases {
		t.Run("sized/"+tc.name, func(t *testing.T) {
			spec := sectionSpec{name: "TEST", hash: "TEST-SHA256", size: "TEST-SIZE", rawNewline: tc.rawNewline}
			integrity := map[string]string{
				"TEST-SHA256": schema.SHA256(tc.raw),
				"TEST-SIZE":   strconv.Itoa(len(tc.framed)),
			}
			begin := envelopeBytes(sectionLine, "BEGIN TEST")
			end := envelopeBytes(sectionLine, "END TEST")
			content := append(bytes.Clone(begin), tc.framed...)
			content = append(content, end...)

			stats := &envelopeExtractionStats{}
			val, rest, err := consumeSectionWithContext(context.Background(), content, spec, integrity, stats)
			if err != nil {
				t.Fatalf("consumeSectionWithContext failed on sized %s: %v", tc.name, err)
			}
			if !bytes.Equal(val, tc.raw) {
				t.Errorf("sized %s: expected %q, got %q", tc.name, tc.raw, val)
			}
			if len(rest) != 0 {
				t.Errorf("sized %s: expected empty rest, got %q", tc.name, rest)
			}
		})
	}

	// Unsized section with rawNewline empty, oneLF, twoLF, rawWithoutNewline
	for _, tc := range cases {
		t.Run("unsized/"+tc.name, func(t *testing.T) {
			spec := sectionSpec{name: "TEST", hash: "TEST-SHA256", rawNewline: tc.rawNewline}
			integrity := map[string]string{
				"TEST-SHA256": schema.SHA256(tc.raw),
			}
			begin := envelopeBytes(sectionLine, "BEGIN TEST")
			end := envelopeBytes(sectionLine, "END TEST")
			content := append(bytes.Clone(begin), tc.framed...)
			content = append(content, end...)

			stats := &envelopeExtractionStats{}
			val, rest, err := consumeSectionWithContext(context.Background(), content, spec, integrity, stats)
			if err != nil {
				t.Fatalf("consumeSectionWithContext failed on unsized %s: %v", tc.name, err)
			}
			if !bytes.Equal(val, tc.raw) {
				t.Errorf("unsized %s: expected %q, got %q", tc.name, tc.raw, val)
			}
			if len(rest) != 0 {
				t.Errorf("unsized %s: expected empty rest, got %q", tc.name, rest)
			}
		})
	}
}

func TestReproduceGrowingPrefixOldBaselineBounded(t *testing.T) {
	testBytes := 256 * 1024 // 256 KiB
	end := envelopeBytes(sectionLine, "END STAGED SUMMARY")

	var buf bytes.Buffer
	chunk := []byte("diff content line before delimiter\n")
	for buf.Len() < testBytes {
		buf.Write(chunk)
		buf.Write(end)
	}
	data := buf.Bytes()[:testBytes]

	candidateOffsets := make([]int, 0)
	for offset := 0; offset <= len(data); {
		idx := bytes.Index(data[offset:], end)
		if idx < 0 {
			break
		}
		idx += offset
		candidateOffsets = append(candidateOffsets, idx)
		offset = idx + 1
	}

	var oldHashedBytes int64
	for _, idx := range candidateOffsets {
		oldHashedBytes += int64(idx)     // sha256(content[:idx])
		oldHashedBytes += int64(idx - 1) // sha256(raw)
	}

	scanner := &incrementalScanner{
		hasher:     sha256.New(),
		rawNewline: true,
	}
	stats := &envelopeExtractionStats{}
	for offset := 0; offset <= len(data); {
		idx := bytes.Index(data[offset:], end)
		if idx < 0 {
			break
		}
		idx += offset
		stats.candidateCount++
		canRaw := scanner.rawNewline && idx >= 2 && data[idx-1] == '\n' && data[idx-2] != '\n'
		if canRaw {
			_ = scanner.feed(context.Background(), data, idx-1, stats)
			_ = scanner.feed(context.Background(), data, idx, stats)
		} else {
			_ = scanner.feed(context.Background(), data, idx, stats)
		}
		offset = idx + 1
	}

	t.Logf("256KiB comparison: %d candidates. Old work bytes: %d (~%d MB). New work bytes: %d (~%d KB). Speedup ratio: %.1fx",
		len(candidateOffsets), oldHashedBytes, oldHashedBytes/(1024*1024),
		stats.hashedBytes, stats.hashedBytes/1024,
		float64(oldHashedBytes)/float64(stats.hashedBytes))

	if stats.hashedBytes > int64(testBytes) {
		t.Errorf("New incremental scanner work bytes %d exceeded data size %d", stats.hashedBytes, testBytes)
	}
	if oldHashedBytes <= stats.hashedBytes*100 {
		t.Errorf("Expected old quadratic work to be >100x new work, got %d vs %d", oldHashedBytes, stats.hashedBytes)
	}
}
