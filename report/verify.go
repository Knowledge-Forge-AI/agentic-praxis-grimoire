package report

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"os"
	"syscall"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/schema"
)

const maxReportFileBytes = 128 << 20 // 128 MB

var (
	// ErrEmptyReport classifies empty report content or empty report artifacts.
	ErrEmptyReport = errors.New("empty report")
	// ErrVerifyIO classifies safe read-only I/O failures during report verification.
	ErrVerifyIO = errors.New("verify io error")
)

// Verification records the outcome of report verification.
type Verification struct {
	// RecordCount is the number of verified common envelopes.
	RecordCount int
	// CompatibilityLimited marks legacy body validation or an external relation
	// whose target is not contained in this artifact.
	CompatibilityLimited bool
}

const cancelQuantum = 64 * 1024 // 64 KiB

// envelopeExtractionStats tracks section boundary candidate inspection and envelope-level hashing.
// Note: This accounts for extraction and envelope hashing only; whole-verifier rendering hashes
// (such as canonical reconstruction) are not included.
type envelopeExtractionStats struct {
	candidateCount int
	hashedBytes    int64
}

func sha256WithContext(ctx context.Context, data []byte, stats *envelopeExtractionStats) (string, error) {
	hasher := sha256.New()
	for offset := 0; offset < len(data); {
		if ctx != nil {
			if err := ctx.Err(); err != nil {
				return "", err
			}
		}
		chunk := cancelQuantum
		if len(data)-offset < chunk {
			chunk = len(data) - offset
		}
		hasher.Write(data[offset : offset+chunk])
		if stats != nil {
			stats.hashedBytes += int64(chunk)
		}
		offset += chunk
	}
	var digest [32]byte
	hasher.Sum(digest[:0])
	return hex.EncodeToString(digest[:]), nil
}

func readBoundedFileWithContext(ctx context.Context, file *os.File, limit int64) ([]byte, error) {
	lr := io.LimitReader(file, limit+1)
	buf := make([]byte, 0, min(limit+1, 64*1024))
	chunk := make([]byte, cancelQuantum)
	for {
		if ctx != nil {
			if err := ctx.Err(); err != nil {
				return nil, err
			}
		}
		n, err := lr.Read(chunk)
		if n > 0 {
			buf = append(buf, chunk[:n]...)
			if int64(len(buf)) > limit {
				return buf, nil
			}
		}
		if err != nil {
			if errors.Is(err, io.EOF) {
				return buf, nil
			}
			return nil, err
		}
	}
}

// verifyWithStats strictly validates contiguous canonical report records in memory,
// collecting extraction and envelope metrics for test accounting.
func verifyWithStats(ctx context.Context, content []byte) (Verification, envelopeExtractionStats, error) {
	if err := ctx.Err(); err != nil {
		return Verification{}, envelopeExtractionStats{}, err
	}
	if len(content) == 0 || len(bytes.TrimSpace(content)) == 0 {
		return Verification{}, envelopeExtractionStats{}, ErrEmptyReport
	}
	if len(content) > maxReportFileBytes {
		return Verification{}, envelopeExtractionStats{}, fmt.Errorf("%w: report content is oversized", ErrCompatibility)
	}
	stats := &envelopeExtractionStats{}
	records, err := parseRecordsWithContext(ctx, content, stats)
	if err != nil {
		return Verification{}, *stats, err
	}
	if len(records) == 0 {
		return Verification{}, *stats, ErrEmptyReport
	}

	// Index local relations semantics-preservingly:
	// Map the first occurrence of each Record ID for O(1) lookup.
	firstRecordByID := make(map[string]Record, len(records))
	for _, rec := range records {
		if err := ctx.Err(); err != nil {
			return Verification{}, *stats, err
		}
		if _, exists := firstRecordByID[rec.ID]; !exists {
			firstRecordByID[rec.ID] = rec
		}
	}

	compatLimited := false
	for _, record := range records {
		if err := ctx.Err(); err != nil {
			return Verification{}, *stats, err
		}
		switch record.Kind {
		case schema.GitShowRecord:
			if err := validateShowRecordWithContext(ctx, record, stats); err != nil {
				return Verification{}, *stats, err
			}
		case schema.GitDiffRecord:
			if err := validateDiffRecordWithContext(ctx, record, stats); err != nil {
				return Verification{}, *stats, err
			}
		case schema.OperationalRecord:
			if err := validateOperationalRecordWithContext(ctx, record, false, stats); err != nil {
				if histErr := validateOperationalRecordWithContext(ctx, record, true, stats); histErr != nil {
					return Verification{}, *stats, histErr
				}
				compatLimited = true
			}
			limited, relationErr := verifyLocalRelationIndexed(ctx, record, firstRecordByID)
			if relationErr != nil {
				return Verification{}, *stats, relationErr
			}
			compatLimited = compatLimited || limited
		default:
			return Verification{}, *stats, fmt.Errorf("%w: unsupported record kind %s", ErrCompatibility, record.Kind)
		}
	}

	return Verification{
		RecordCount:          len(records),
		CompatibilityLimited: compatLimited,
	}, *stats, nil
}

// Verify strictly validates contiguous canonical report records in memory.
func Verify(ctx context.Context, content []byte) (Verification, error) {
	v, _, err := verifyWithStats(ctx, content)
	return v, err
}

func verifyLocalRelationIndexed(ctx context.Context, record Record, recordByID map[string]Record) (bool, error) {
	if err := ctx.Err(); err != nil {
		return false, err
	}
	id := payloadField(record.Payload, "RELATED-GIT-REPORT-ID")
	limited := payloadField(record.Payload, "BODY-SCHEMA-DETECTED") != "operational-report-v1"
	if id == "NONE" {
		return limited, nil
	}
	candidate, found := recordByID[id]
	if !found {
		return true, nil
	}
	if candidate.Project != record.Project || candidate.Phase != record.Phase {
		return false, fmt.Errorf("%w: related record ownership mismatch", ErrCompatibility)
	}
	return limited, nil
}

func verifyLocalRelation(ctx context.Context, record Record, records []Record) (bool, error) {
	if err := ctx.Err(); err != nil {
		return false, err
	}
	id := payloadField(record.Payload, "RELATED-GIT-REPORT-ID")
	limited := payloadField(record.Payload, "BODY-SCHEMA-DETECTED") != "operational-report-v1"
	if id == "NONE" {
		return limited, nil
	}
	found := false
	for _, candidate := range records {
		if err := ctx.Err(); err != nil {
			return false, err
		}
		if candidate.ID != id {
			continue
		}
		if candidate.Project != record.Project || candidate.Phase != record.Phase {
			return false, fmt.Errorf("%w: related record ownership mismatch", ErrCompatibility)
		}
		found = true
		break
	}
	return limited || !found, nil
}

func verifyFileWithStats(ctx context.Context, path string) (Verification, envelopeExtractionStats, error) {
	if err := ctx.Err(); err != nil {
		return Verification{}, envelopeExtractionStats{}, err
	}
	if path == "" {
		return Verification{}, envelopeExtractionStats{}, fmt.Errorf("%w: report path is empty", ErrVerifyIO)
	}

	initialInfo, err := os.Lstat(path)
	if err != nil {
		if os.IsNotExist(err) {
			return Verification{}, envelopeExtractionStats{}, fmt.Errorf("%w: report file not found", ErrVerifyIO)
		}
		return Verification{}, envelopeExtractionStats{}, fmt.Errorf("%w: report file stat failed", ErrVerifyIO)
	}
	if !initialInfo.Mode().IsRegular() {
		return Verification{}, envelopeExtractionStats{}, fmt.Errorf("%w: report file is not regular", ErrVerifyIO)
	}
	if initialInfo.Size() == 0 {
		return Verification{}, envelopeExtractionStats{}, ErrEmptyReport
	}
	if initialInfo.Size() > maxReportFileBytes {
		return Verification{}, envelopeExtractionStats{}, fmt.Errorf("%w: report file is oversized", ErrCompatibility)
	}

	file, err := os.OpenFile(path, os.O_RDONLY|syscall.O_NOFOLLOW|syscall.O_NONBLOCK, 0)
	if err != nil {
		return Verification{}, envelopeExtractionStats{}, fmt.Errorf("%w: report file open failed", ErrVerifyIO)
	}
	defer file.Close()

	openedInfo, err := file.Stat()
	if err != nil || !openedInfo.Mode().IsRegular() {
		return Verification{}, envelopeExtractionStats{}, fmt.Errorf("%w: report descriptor stat failed", ErrVerifyIO)
	}
	if !sameFileInfo(initialInfo, openedInfo) {
		return Verification{}, envelopeExtractionStats{}, fmt.Errorf("%w: report file identity changed on open", ErrVerifyIO)
	}

	content, err := readBoundedFileWithContext(ctx, file, maxReportFileBytes)
	if err != nil {
		if errors.Is(err, context.Canceled) || errors.Is(err, context.DeadlineExceeded) {
			return Verification{}, envelopeExtractionStats{}, err
		}
		return Verification{}, envelopeExtractionStats{}, fmt.Errorf("%w: report file read failed", ErrVerifyIO)
	}
	if int64(len(content)) > maxReportFileBytes {
		return Verification{}, envelopeExtractionStats{}, fmt.Errorf("%w: report file exceeded size limit", ErrVerifyIO)
	}

	postOpenedInfo, err := file.Stat()
	if err != nil || !sameFileInfo(openedInfo, postOpenedInfo) || postOpenedInfo.Size() != int64(len(content)) {
		return Verification{}, envelopeExtractionStats{}, fmt.Errorf("%w: report file modified during observation", ErrVerifyIO)
	}

	postPathInfo, err := os.Lstat(path)
	if err != nil || !sameFileInfo(initialInfo, postPathInfo) {
		return Verification{}, envelopeExtractionStats{}, fmt.Errorf("%w: report path replaced during observation", ErrVerifyIO)
	}

	return verifyWithStats(ctx, content)
}

// VerifyFile strictly validates an on-disk report file using read-only bounded
// complete read and stability observation without mutating permissions or filesystem state.
func VerifyFile(ctx context.Context, path string) (Verification, error) {
	v, _, err := verifyFileWithStats(ctx, path)
	return v, err
}

func sameFileInfo(a, b os.FileInfo) bool {
	if a == nil || b == nil {
		return false
	}
	left, leftErr := identityFor(a)
	right, rightErr := identityFor(b)
	return leftErr == nil && rightErr == nil && left == right
}
