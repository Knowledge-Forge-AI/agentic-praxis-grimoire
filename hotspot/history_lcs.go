package hotspot

import (
	"bytes"
	"context"
	"fmt"
	"unicode/utf8"
)

// splitPhysicalLines partitions bytes by LF, counting a non-empty unterminated
// final segment as a physical line, and preserving any preceding CR.
func splitPhysicalLines(data []byte) []string {
	if len(data) == 0 {
		return nil
	}
	var lines []string
	start := 0
	for i := 0; i < len(data); i++ {
		if data[i] == '\n' {
			lines = append(lines, string(data[start:i+1]))
			start = i + 1
		}
	}
	if start < len(data) {
		lines = append(lines, string(data[start:]))
	}
	return lines
}

// isBinary reports whether data contains a NUL byte or is not valid UTF-8.
func isBinary(data []byte) bool {
	if bytes.IndexByte(data, 0) >= 0 {
		return true
	}
	return !utf8.Valid(data)
}

// computeLCSChurn calculates the sum of inserted and deleted lines using the
// deterministic Longest Common Subsequence (LCS) shortest edit script.
// If comparison cell bounds are exceeded, an error is returned.
func computeLCSChurn(ctx context.Context, a, b []string, cellsPerPairLimit int64, aggregateCells *int64, aggregateCellsLimit int64) (int64, error) {
	lenA := len(a)
	lenB := len(b)
	if lenA == 0 && lenB == 0 {
		return 0, nil
	}
	if lenA == 0 {
		return int64(lenB), nil
	}
	if lenB == 0 {
		return int64(lenA), nil
	}

	cells := int64(lenA) * int64(lenB)
	if cells > cellsPerPairLimit {
		return 0, fmt.Errorf("history limit exceeded: comparison cells per pair (%d) exceeds limit (%d)", cells, cellsPerPairLimit)
	}
	if *aggregateCells+cells > aggregateCellsLimit {
		return 0, fmt.Errorf("history limit exceeded: aggregate comparison cells (%d) exceeds limit (%d)", *aggregateCells+cells, aggregateCellsLimit)
	}
	*aggregateCells += cells

	// Ensure slice 'a' is the smaller one to minimize memory allocated for DP rows.
	if lenA > lenB {
		a, b = b, a
		lenA, lenB = lenB, lenA
	}

	prev := make([]int, lenA+1)
	curr := make([]int, lenA+1)

	for j := 1; j <= lenB; j++ {
		if err := ctx.Err(); err != nil {
			return 0, err
		}
		bj := b[j-1]
		for i := 1; i <= lenA; i++ {
			if a[i-1] == bj {
				curr[i] = prev[i-1] + 1
			} else {
				c1 := prev[i]
				c2 := curr[i-1]
				if c1 > c2 {
					curr[i] = c1
				} else {
					curr[i] = c2
				}
			}
		}
		copy(prev, curr)
	}

	lcsLen := curr[lenA]
	churn := int64(lenA + lenB - 2*lcsLen)
	return churn, nil
}
