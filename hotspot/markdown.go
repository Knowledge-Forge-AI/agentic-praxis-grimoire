package hotspot

import (
	"bytes"
	"fmt"
	"strings"
)

func splitLines(content []byte) []string {
	if len(content) == 0 {
		return nil
	}
	values := strings.Split(string(content), "\n")
	if len(values) > 0 && values[len(values)-1] == "" {
		values = values[:len(values)-1]
	}
	for index := range values {
		values[index] = strings.TrimSuffix(values[index], "\r")
	}
	return values
}

func analyzeMarkdown(path string, content []byte, row *FileRow) ([]OwnerRow, []RegionRow) {
	lines := splitLines(content)
	var owners []OwnerRow
	prose, fenceLines, headings, fences, links, maxDepth := int64(0), int64(0), int64(0), int64(0), int64(0), int64(0)
	inFence := false
	fenceMarker := ""
	fenceStart := 0
	for index, line := range lines {
		trimmed := strings.TrimSpace(line)
		marker := markdownFenceMarker(trimmed)
		if marker != "" {
			if !inFence {
				inFence, fenceMarker, fenceStart = true, marker, index+1
				fences++
			} else if marker[0] == fenceMarker[0] && len(marker) >= len(fenceMarker) {
				owners = append(owners, OwnerRow{ID: stableID("owner:fence", path, fenceStart, 1), Path: path, Language: LanguageMarkdown, Kind: "fence", DisplayName: fmt.Sprintf("fence at line %d", fenceStart), StartLine: fenceStart, EndLine: index + 1, Confidence: ConfidenceHigh, Metrics: []Metric{lineSpanMetric(fenceStart, index+1)}})
				inFence = false
			}
			continue
		}
		if inFence {
			fenceLines++
			continue
		}
		if trimmed != "" {
			prose++
		}
		if depth, title := atxHeading(line); depth > 0 {
			headings++
			if int64(depth) > maxDepth {
				maxDepth = int64(depth)
			}
			owners = append(owners, OwnerRow{ID: stableID("owner:heading", path, index+1, 1), Path: path, Language: LanguageMarkdown, Kind: "heading", DisplayName: title, StartLine: index + 1, EndLine: index + 1, Confidence: ConfidenceHigh, Metrics: []Metric{metric(MetricNesting, AvailabilityStructural, int64(depth), "levels", "markdown-section-depth:S"), lineSpanMetric(index+1, index+1)}})
		}
		links += int64(strings.Count(line, "]("))
	}
	if inFence {
		owners = append(owners, OwnerRow{ID: stableID("owner:fence", path, fenceStart, 1), Path: path, Language: LanguageMarkdown, Kind: "fence", DisplayName: fmt.Sprintf("unclosed fence at line %d", fenceStart), StartLine: fenceStart, EndLine: len(lines), Confidence: ConfidenceHigh, Metrics: []Metric{lineSpanMetric(fenceStart, len(lines))}})
	}
	row.Metrics = append(row.Metrics,
		metric(MetricProseLines, AvailabilityExact, prose, "lines", ""), metric(MetricFenceLines, AvailabilityExact, fenceLines, "lines", ""),
		notApplicable(MetricStatements, "Markdown statements are not meaningful"), metric(MetricSymbols, AvailabilityStructural, headings+fences, "owners", ""),
		notApplicable(MetricCyclomatic, "Markdown cyclomatic complexity is not meaningful"), metric(MetricNesting, AvailabilityStructural, maxDepth, "levels", "markdown-section-depth:S"),
		notApplicable(MetricProceduralSize, "Markdown procedural regions are not meaningful"), metric(MetricHeadings, AvailabilityExact, headings, "headings", ""),
		metric(MetricFences, AvailabilityExact, fences, "fences", ""), metric(MetricLinks, AvailabilityExact, links, "links", ""),
	)
	row.PrimarySize = PrimarySize{Value: prose, Unit: "prose lines"}
	if prose == 0 && row.PhysicalLines != nil {
		row.PrimarySize = PrimarySize{Value: *row.PhysicalLines, Unit: "lines"}
	}
	return owners, nil
}

func markdownFenceMarker(trimmed string) string {
	if strings.HasPrefix(trimmed, "```") {
		return strings.Repeat("`", leadingRun(trimmed, '`'))
	}
	if strings.HasPrefix(trimmed, "~~~") {
		return strings.Repeat("~", leadingRun(trimmed, '~'))
	}
	return ""
}

func leadingRun(value string, target byte) int {
	index := 0
	for index < len(value) && value[index] == target {
		index++
	}
	return index
}

func atxHeading(line string) (int, string) {
	trimmed := strings.TrimLeft(line, " \t")
	if len(line)-len(trimmed) > 3 || !strings.HasPrefix(trimmed, "#") {
		return 0, ""
	}
	depth := leadingRun(trimmed, '#')
	if depth > 6 || len(trimmed) == depth || trimmed[depth] != ' ' {
		return 0, ""
	}
	return depth, strings.TrimSpace(strings.TrimRight(trimmed[depth+1:], "#"))
}

func analyzeHybrid(path string, language Language, content []byte, row *FileRow) ([]OwnerRow, []RegionRow) {
	lines := splitLines(content)
	embedded := hybridEmbeddedMask(language, lines)
	owners, regions, prose, embeddedLines, maxDepth := hybridRows(path, language, lines, embedded)
	row.Metrics = append(row.Metrics,
		metric(MetricProseLines, AvailabilityExact, prose, "lines", ""), metric(MetricEmbeddedLines, AvailabilityExact, embeddedLines, "lines", ""),
		unavailable(MetricStatements, "embedded-parser-unavailable"), metric(MetricSymbols, AvailabilityStructural, int64(len(owners)), "regions", ""),
		unavailable(MetricCyclomatic, "embedded-parser-unavailable"), metric(MetricNesting, AvailabilityStructural, maxDepth, "levels", "hybrid-region-depth:S"),
		metric(MetricEmbeddedRegions, AvailabilityStructural, int64(len(regions)), "regions", ""),
	)
	row.PrimarySize = PrimarySize{Value: prose, Unit: "prose lines"}
	return owners, regions
}

func hybridEmbeddedMask(language Language, lines []string) []bool {
	embedded := make([]bool, len(lines))
	if language == LanguageAstro && len(lines) > 0 && strings.TrimSpace(lines[0]) == "---" {
		for index := 0; index < len(lines); index++ {
			embedded[index] = true
			if index > 0 && strings.TrimSpace(lines[index]) == "---" {
				break
			}
		}
	}
	braceDepth := 0
	for index, line := range lines {
		if embedded[index] {
			continue
		}
		trimmed := strings.TrimSpace(line)
		if strings.Contains(trimmed, "<") && strings.Contains(trimmed, ">") || braceDepth > 0 || strings.Contains(trimmed, "{") {
			embedded[index] = true
		}
		braceDepth += strings.Count(line, "{") - strings.Count(line, "}")
		if braceDepth < 0 {
			braceDepth = 0
		}
	}
	return embedded
}

func hybridRows(path string, language Language, lines []string, embedded []bool) ([]OwnerRow, []RegionRow, int64, int64, int64) {
	var owners []OwnerRow
	var regions []RegionRow
	prose, embeddedLines, maxDepth := int64(0), int64(0), int64(0)
	start := -1
	depth := int64(0)
	for index, isEmbedded := range embedded {
		if isEmbedded {
			embeddedLines++
			if start < 0 {
				start = index + 1
			}
			depth += int64(strings.Count(lines[index], "{") + strings.Count(lines[index], "<"))
			depth -= int64(strings.Count(lines[index], "}") + strings.Count(lines[index], "</"))
			if depth > maxDepth {
				maxDepth = depth
			}
			if depth < 0 {
				depth = 0
			}
		} else {
			if strings.TrimSpace(lines[index]) != "" {
				prose++
			}
			if start >= 0 {
				owners, regions = appendHybridRegion(owners, regions, path, language, start, index)
				start = -1
			}
		}
	}
	if start >= 0 {
		owners, regions = appendHybridRegion(owners, regions, path, language, start, len(lines))
	}
	return owners, regions, prose, embeddedLines, maxDepth
}

func appendHybridRegion(owners []OwnerRow, regions []RegionRow, path string, language Language, start, end int) ([]OwnerRow, []RegionRow) {
	id := stableID("region:embedded", path, start, 1)
	name := fmt.Sprintf("embedded region at lines %d-%d", start, end)
	metrics := []Metric{metric(MetricProceduralSize, AvailabilityStructural, int64(end-start+1), "lines", "hybrid-regions:S"), unavailable(MetricStatements, "embedded-parser-unavailable"), unavailable(MetricCyclomatic, "embedded-parser-unavailable"), lineSpanMetric(start, end)}
	owners = append(owners, OwnerRow{ID: stableID("owner:embedded", path, start, 1), Path: path, Language: language, Kind: "embedded-region", DisplayName: name, StartLine: start, EndLine: end, Confidence: ConfidenceMedium, Metrics: append([]Metric(nil), metrics...)})
	regions = append(regions, RegionRow{ID: id, Path: path, Language: language, Kind: "embedded-region", DisplayName: name, StartLine: start, EndLine: end, Confidence: ConfidenceMedium, Metrics: metrics})
	return owners, regions
}

var _ = bytes.Count
