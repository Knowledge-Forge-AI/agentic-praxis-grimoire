package report

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"hash"
	"strconv"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/schema"
)

// These are inner record boundaries, not a second common-envelope parser.
// Opaque sections are selected by canonical hashes (or an explicit body size).
type sectionSpec struct {
	name, hash, size string
	rawNewline       bool
}

func decodeSections(payload []byte, specs []sectionSpec) (map[string][]byte, error) {
	return decodeSectionsWithContext(context.Background(), payload, specs, nil)
}

func decodeSectionsWithContext(ctx context.Context, payload []byte, specs []sectionSpec, stats *envelopeExtractionStats) (map[string][]byte, error) {
	if ctx != nil {
		if err := ctx.Err(); err != nil {
			return nil, err
		}
	}
	begin := envelopeBytes(sectionLine, "BEGIN INTEGRITY SUMMARY")
	end := envelopeBytes(sectionLine, "END INTEGRITY SUMMARY")
	position, err := lastIndexWithContext(ctx, payload, begin)
	if err != nil {
		return nil, err
	}
	if !bytes.HasSuffix(payload, end) || position < 0 || position+len(begin) > len(payload)-len(end) {
		return nil, fmt.Errorf("%w: missing trailing integrity section", ErrCompatibility)
	}
	integrity, _, err := parseSectionFieldsWithContext(ctx, payload[position+len(begin):len(payload)-len(end)])
	if err != nil {
		return nil, err
	}
	sections := make(map[string][]byte, len(specs))
	remaining := payload[:position]
	for _, spec := range specs {
		if ctx != nil {
			if err := ctx.Err(); err != nil {
				return nil, err
			}
		}
		value, rest, err := consumeSectionWithContext(ctx, remaining, spec, integrity, stats)
		if err != nil {
			return nil, err
		}
		sections[spec.name], remaining = value, rest
	}
	if len(remaining) != 0 {
		return nil, fmt.Errorf("%w: unexpected trailing section bytes", ErrCompatibility)
	}
	return sections, nil
}

func consumeSection(content []byte, spec sectionSpec, integrity map[string]string) ([]byte, []byte, error) {
	return consumeSectionWithContext(context.Background(), content, spec, integrity, nil)
}

func consumeSectionWithContext(ctx context.Context, content []byte, spec sectionSpec, integrity map[string]string, stats *envelopeExtractionStats) ([]byte, []byte, error) {
	if ctx != nil {
		if err := ctx.Err(); err != nil {
			return nil, nil, err
		}
	}
	begin, end := envelopeBytes(sectionLine, "BEGIN "+spec.name), envelopeBytes(sectionLine, "END "+spec.name)
	if !bytes.HasPrefix(content, begin) {
		return nil, nil, fmt.Errorf("%w: unexpected section order", ErrCompatibility)
	}
	content = content[len(begin):]
	if spec.hash != "" && !hex64.MatchString(integrity[spec.hash]) {
		return nil, nil, fmt.Errorf("%w: invalid section hash", ErrCompatibility)
	}
	if spec.size != "" {
		size, err := persistedSize(integrity[spec.size], len(content))
		if err == nil && bytes.HasPrefix(content[size:], end) {
			digest, err := sha256WithContext(ctx, content[:size], stats)
			if err != nil {
				return nil, nil, err
			}
			if digest == integrity[spec.hash] {
				if stats != nil {
					stats.candidateCount++
				}
				return content[:size], content[size+len(end):], nil
			}
			if spec.rawNewline && size >= 2 && content[size-1] == '\n' && content[size-2] != '\n' {
				rawDigest, err := sha256WithContext(ctx, content[:size-1], stats)
				if err != nil {
					return nil, nil, err
				}
				if rawDigest == integrity[spec.hash] {
					if stats != nil {
						stats.candidateCount++
					}
					return content[:size-1], content[size+len(end):], nil
				}
			}
		}
		return nil, nil, fmt.Errorf("%w: invalid sized section", ErrCompatibility)
	}

	if spec.hash == "" {
		index, err := indexWithContext(ctx, content, end)
		if err != nil {
			return nil, nil, err
		}
		if index < 0 {
			return nil, nil, fmt.Errorf("%w: section boundary or hash mismatch", ErrCompatibility)
		}
		if stats != nil {
			stats.candidateCount++
		}
		return content[:index], content[index+len(end):], nil
	}

	expectedBytes, err := hex.DecodeString(integrity[spec.hash])
	if err != nil || len(expectedBytes) != 32 {
		return nil, nil, fmt.Errorf("%w: invalid section hash", ErrCompatibility)
	}
	var expectedDigest [32]byte
	copy(expectedDigest[:], expectedBytes)

	scanner := &incrementalScanner{
		hasher:     sha256.New(),
		rawNewline: spec.rawNewline,
	}

	for offset := 0; offset <= len(content); {
		if ctx != nil {
			if err := ctx.Err(); err != nil {
				return nil, nil, err
			}
		}
		index, err := indexWithContext(ctx, content[offset:], end)
		if err != nil {
			return nil, nil, err
		}
		if index < 0 {
			break
		}
		index += offset
		if stats != nil {
			stats.candidateCount++
		}

		canRaw := scanner.rawNewline && index >= 2 && content[index-1] == '\n' && content[index-2] != '\n'

		if canRaw {
			if err := scanner.feed(ctx, content, index-1, stats); err != nil {
				return nil, nil, err
			}
			var rawDigest [32]byte
			scanner.hasher.Sum(rawDigest[:0])

			if err := scanner.feed(ctx, content, index, stats); err != nil {
				return nil, nil, err
			}
			var exactDigest [32]byte
			scanner.hasher.Sum(exactDigest[:0])

			if exactDigest == expectedDigest {
				return content[:index], content[index+len(end):], nil
			}
			if rawDigest == expectedDigest {
				return content[:index-1], content[index+len(end):], nil
			}
		} else {
			if err := scanner.feed(ctx, content, index, stats); err != nil {
				return nil, nil, err
			}
			var exactDigest [32]byte
			scanner.hasher.Sum(exactDigest[:0])
			if exactDigest == expectedDigest {
				return content[:index], content[index+len(end):], nil
			}
		}

		offset = index + 1
	}
	return nil, nil, fmt.Errorf("%w: section boundary or hash mismatch", ErrCompatibility)
}

type incrementalScanner struct {
	hasher       hash.Hash
	hashedOffset int
	rawNewline   bool
}

func (s *incrementalScanner) feed(ctx context.Context, content []byte, targetOffset int, stats *envelopeExtractionStats) error {
	for s.hashedOffset < targetOffset {
		if ctx != nil {
			if err := ctx.Err(); err != nil {
				return err
			}
		}
		chunk := cancelQuantum
		if targetOffset-s.hashedOffset < chunk {
			chunk = targetOffset - s.hashedOffset
		}
		n, _ := s.hasher.Write(content[s.hashedOffset : s.hashedOffset+chunk])
		s.hashedOffset += n
		if stats != nil {
			stats.hashedBytes += int64(n)
		}
	}
	return nil
}

// indexWithContext finds the first occurrence of sep in data using bounded windows of at most
// cancelQuantum, checking ctx.Err() at each quantum. Delimiter overlap of len(sep)-1 preserves
// exact first candidate across window splits and on long delimiter-free data.
func indexWithContext(ctx context.Context, data, sep []byte) (int, error) {
	if len(sep) == 0 {
		return 0, nil
	}
	if len(data) < len(sep) {
		return -1, nil
	}
	windowSize := cancelQuantum
	if len(sep) > windowSize {
		windowSize = len(sep)
	}
	overlap := len(sep) - 1
	offset := 0
	for offset < len(data) {
		if ctx != nil {
			if err := ctx.Err(); err != nil {
				return -1, err
			}
		}
		end := offset + windowSize
		if end > len(data) {
			end = len(data)
		}
		idx := bytes.Index(data[offset:end], sep)
		if idx >= 0 {
			return offset + idx, nil
		}
		if end == len(data) {
			break
		}
		offset = end - overlap
	}
	return -1, nil
}

// lastIndexWithContext finds the last occurrence of sep in data using backwards bounded windows
// of at most cancelQuantum, checking ctx.Err() at each quantum. Delimiter overlap of len(sep)-1
// preserves exact last candidate across window splits and on long delimiter-free data.
func lastIndexWithContext(ctx context.Context, data, sep []byte) (int, error) {
	if len(sep) == 0 {
		return len(data), nil
	}
	if len(data) < len(sep) {
		return -1, nil
	}
	windowSize := cancelQuantum
	if len(sep) > windowSize {
		windowSize = len(sep)
	}
	overlap := len(sep) - 1
	end := len(data)
	for end >= len(sep) {
		if ctx != nil {
			if err := ctx.Err(); err != nil {
				return -1, err
			}
		}
		start := end - windowSize
		if start < 0 {
			start = 0
		}
		idx := bytes.LastIndex(data[start:end], sep)
		if idx >= 0 {
			return start + idx, nil
		}
		if start == 0 {
			break
		}
		end = start + overlap
	}
	return -1, nil
}

// indexByteWithContext finds the first occurrence of byte b in data using bounded windows of at most
// cancelQuantum, checking ctx.Err() at each quantum.
func indexByteWithContext(ctx context.Context, data []byte, b byte) (int, error) {
	windowSize := cancelQuantum
	for offset := 0; offset < len(data); {
		if ctx != nil {
			if err := ctx.Err(); err != nil {
				return -1, err
			}
		}
		end := offset + windowSize
		if end > len(data) {
			end = len(data)
		}
		idx := bytes.IndexByte(data[offset:end], b)
		if idx >= 0 {
			return offset + idx, nil
		}
		offset = end
	}
	return -1, nil
}

func sectionHashCandidate(content []byte, spec sectionSpec, integrity map[string]string) ([]byte, bool) {
	if spec.hash == "" || schema.SHA256(content) == integrity[spec.hash] {
		return content, true
	}
	if spec.rawNewline && len(content) >= 2 && content[len(content)-1] == '\n' && content[len(content)-2] != '\n' {
		raw := content[:len(content)-1]
		if schema.SHA256(raw) == integrity[spec.hash] {
			return raw, true
		}
	}
	return nil, false
}

func persistedSize(value string, maximum int) (int, error) {
	size, err := strconv.Atoi(value)
	if err != nil || size < 0 || size > maximum || strconv.Itoa(size) != value {
		return 0, fmt.Errorf("%w: invalid persisted size", ErrCompatibility)
	}
	return size, nil
}

func parseSectionFields(content []byte) (map[string]string, []string, error) {
	return parseSectionFieldsWithContext(context.Background(), content)
}

func parseSectionFieldsWithContext(ctx context.Context, content []byte) (map[string]string, []string, error) {
	if len(content) == 0 || content[len(content)-1] != '\n' {
		return nil, nil, fmt.Errorf("%w: incomplete metadata section", ErrCompatibility)
	}
	fields := map[string]string{}
	var order []string
	for offset := 0; offset < len(content); {
		index, err := indexByteWithContext(ctx, content[offset:], '\n')
		if err != nil {
			return nil, nil, err
		}
		line := content[offset : offset+index]
		offset += index + 1
		key, value, ok := bytes.Cut(line, []byte(": "))
		if !ok || len(key) == 0 {
			return nil, nil, fmt.Errorf("%w: invalid section field", ErrCompatibility)
		}
		if _, exists := fields[string(key)]; exists {
			return nil, nil, fmt.Errorf("%w: duplicate section field", ErrCompatibility)
		}
		if validateMetadata(string(line), "section field") != nil {
			return nil, nil, fmt.Errorf("%w: unsafe section field", ErrCompatibility)
		}
		fields[string(key)] = string(value)
		order = append(order, string(key))
	}
	return fields, order, nil
}
