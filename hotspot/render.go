package hotspot

import (
	"bytes"
	"fmt"
	"sort"
	"strings"
)

// RenderTerminal returns the bounded concise situational view configured by Report.
func RenderTerminal(report Report) ([]byte, error) {
	if err := validateReport(report); err != nil {
		return nil, err
	}
	top := report.ScanConfiguration.DisplayTopN
	if top <= 0 {
		top = 10
	}
	var output bytes.Buffer
	fmt.Fprintf(&output, "Hotspot analysis: %s\nAnalyzed files: %d\n\nLanguages\n", report.RootID, len(report.Files))
	for _, aggregate := range report.LanguageAggregates {
		fmt.Fprintf(&output, "  %-18s %5d files %10d bytes\n", aggregate.Language, aggregate.Files, aggregate.Bytes)
	}
	fmt.Fprintf(&output, "\nLargest files\n")
	largest := append([]FileRow(nil), report.Files...)
	sort.Slice(largest, func(i, j int) bool {
		if largest[i].Bytes != largest[j].Bytes {
			return largest[i].Bytes > largest[j].Bytes
		}
		return largest[i].Path < largest[j].Path
	})
	for index, row := range largest {
		if index >= top {
			break
		}
		fmt.Fprintf(&output, "  %-50s %8d %s\n", row.Path, row.PrimarySize.Value, row.PrimarySize.Unit)
	}
	fmt.Fprintf(&output, "\nDifficult owners\n")
	ownerCount := 0
	for _, row := range report.Owners {
		if row.Language != LanguageGo || row.Generated {
			continue
		}
		if ownerCount >= top {
			break
		}
		fmt.Fprintf(&output, "  %-42s score=%5d weight=%3d confidence=%s\n", row.DisplayName, row.Ranking.Score, row.Ranking.AvailableWeight, row.Confidence)
		ownerCount++
	}
	fmt.Fprintf(&output, "\nHotspot candidates\n")
	for index, row := range report.RefactoringCandidates {
		if index >= top {
			break
		}
		fmt.Fprintf(&output, "  %-50s score=%5d %s\n", row.Path, row.RiskScore, strings.Join(row.ReasonCodes, ","))
	}
	if len(report.Warnings) > 0 {
		fmt.Fprintf(&output, "\nWarnings: %d (see JSON or Markdown for details)\n", len(report.Warnings))
	}
	fmt.Fprintf(&output, "\nFingerprint: %s\n", report.Fingerprint)
	return output.Bytes(), nil
}

// RenderMarkdown returns a deterministic detailed report with a complete file appendix.
func RenderMarkdown(report Report) ([]byte, error) {
	if err := validateReport(report); err != nil {
		return nil, err
	}
	var output bytes.Buffer
	fmt.Fprintf(&output, "# Hotspot analysis: %s\n\nReport fingerprint: `%s`\n\n## Executive summary\n\nThe complete scan analyzed %d files. Rankings are report-local inspection signals, not proof of a design defect.\n\n", report.RootID, report.Fingerprint, len(report.Files))
	output.WriteString("## Table of contents\n\n- [Scan configuration and exclusions](#scan-configuration-and-exclusions)\n- [Capability and confidence legend](#capability-and-confidence-legend)\n- [Largest files](#largest-files)\n- [Aggregate statistics](#aggregate-statistics)\n- [Per-language breakdown](#per-language-breakdown)\n- [Complexity hotspots](#complexity-hotspots)\n- [Owners, functions, and methods](#owners-functions-and-methods)\n- [Large procedural regions](#large-procedural-regions)\n- [Refactoring candidates](#refactoring-candidates)\n- [Unavailable and deferred metrics](#unavailable-and-deferred-metrics)\n- [Warnings and limitations](#warnings-and-limitations)\n- [Appendix: all analyzed files](#appendix-all-analyzed-files)\n\n")
	renderMarkdownConfiguration(&output, report)
	renderMarkdownCapabilities(&output, report)
	renderMarkdownSizes(&output, report)
	renderMarkdownOwners(&output, report)
	renderMarkdownRegionsAndCandidates(&output, report)
	renderMarkdownLimitationsAndAppendix(&output, report)
	return output.Bytes(), nil
}

func renderMarkdownConfiguration(output *bytes.Buffer, report Report) {
	fmt.Fprintf(output, "## Scan configuration and exclusions\n\n| Limit | Value |\n| --- | ---: |\n| Files | %d |\n| Bytes per file | %d |\n| Total bytes | %d |\n| Duration milliseconds | %d |\n\n", report.ScanConfiguration.MaxFiles, report.ScanConfiguration.MaxBytesPerFile, report.ScanConfiguration.MaxTotalBytes, report.ScanConfiguration.MaxDurationMilliseconds)
	output.WriteString("| Exclusion rule | Directories | Files |\n| --- | ---: | ---: |\n")
	for _, row := range report.Exclusions {
		fmt.Fprintf(output, "| `%s` | %d | %d |\n", markdownCell(row.Rule), row.Directories, row.Files)
	}
}

func renderMarkdownCapabilities(output *bytes.Buffer, report Report) {
	output.WriteString("\n## Capability and confidence legend\n\n`exact` is exact for the stated grammar, `structural` is a bounded scan, `unavailable` has no numeric approximation, and `not-applicable` is not meaningful. Confidence is high, medium, or low.\n\n| Surface | Statements | Cyclomatic | Nesting | Procedural | Confidence |\n| --- | --- | --- | --- | --- | --- |\n")
	for _, row := range report.Capabilities {
		fmt.Fprintf(output, "| %s | %s | %s | %s | %s | %s |\n", markdownCell(row.Surface), row.Statements, row.Cyclomatic, row.Nesting, row.ProceduralRegions, row.Confidence)
	}
}

func renderMarkdownSizes(output *bytes.Buffer, report Report) {
	output.WriteString("\n## Largest files\n\n| Path | Bytes | Primary size |\n| --- | ---: | ---: |\n")
	largest := append([]FileRow(nil), report.Files...)
	sort.Slice(largest, func(i, j int) bool {
		if largest[i].Bytes != largest[j].Bytes {
			return largest[i].Bytes > largest[j].Bytes
		}
		return largest[i].Path < largest[j].Path
	})
	for _, row := range largest {
		fmt.Fprintf(output, "| `%s` | %d | %d %s |\n", markdownCell(row.Path), row.Bytes, row.PrimarySize.Value, markdownCell(row.PrimarySize.Unit))
	}
	output.WriteString("\n## Aggregate statistics\n\n")
	totalBytes := int64(0)
	for _, row := range report.Files {
		totalBytes += row.Bytes
	}
	fmt.Fprintf(output, "- Files: %d\n- Bytes: %d\n- Owners: %d\n- Procedural regions: %d\n\n", len(report.Files), totalBytes, len(report.Owners), len(report.ProceduralRegions))
	output.WriteString("## Per-language breakdown\n\n| Language | Files | Bytes |\n| --- | ---: | ---: |\n")
	for _, row := range report.LanguageAggregates {
		fmt.Fprintf(output, "| %s | %d | %d |\n", row.Language, row.Files, row.Bytes)
	}
}

func renderMarkdownOwners(output *bytes.Buffer, report Report) {
	output.WriteString("\n## Complexity hotspots\n\n| Owner | Path | Score | Weight | Confidence |\n| --- | --- | ---: | ---: | --- |\n")
	for _, row := range report.Owners {
		if row.Language == LanguageGo && !row.Generated {
			fmt.Fprintf(output, "| %s | `%s` | %d | %d | %s |\n", markdownCell(row.DisplayName), markdownCell(row.Path), row.Ranking.Score, row.Ranking.AvailableWeight, row.Confidence)
		}
	}
	output.WriteString("\n## Owners, functions, and methods\n\n| ID | Kind | Lines | Confidence |\n| --- | --- | ---: | --- |\n")
	owners := append([]OwnerRow(nil), report.Owners...)
	sort.Slice(owners, func(i, j int) bool {
		if owners[i].Path != owners[j].Path {
			return owners[i].Path < owners[j].Path
		}
		return owners[i].ID < owners[j].ID
	})
	for _, row := range owners {
		fmt.Fprintf(output, "| `%s` | %s | %d-%d | %s |\n", markdownCell(row.ID), row.Kind, row.StartLine, row.EndLine, row.Confidence)
	}
}

func renderMarkdownRegionsAndCandidates(output *bytes.Buffer, report Report) {
	output.WriteString("\n## Large procedural regions\n\n| ID | Path | Kind | Score | Confidence |\n| --- | --- | --- | ---: | --- |\n")
	for _, row := range report.ProceduralRegions {
		fmt.Fprintf(output, "| `%s` | `%s` | %s | %d | %s |\n", markdownCell(row.ID), markdownCell(row.Path), row.Kind, row.Ranking.Score, row.Confidence)
	}
	output.WriteString("\n## Refactoring candidates\n\nThese metric-derived candidates warrant inspection; they do not establish coupling, architecture, or responsibility defects.\n\n| Kind | Target | Score | Reasons |\n| --- | --- | ---: | --- |\n")
	for _, row := range report.RefactoringCandidates {
		fmt.Fprintf(output, "| %s | `%s` | %d | %s |\n", row.Kind, markdownCell(row.TargetID), row.RiskScore, strings.Join(row.ReasonCodes, ", "))
	}
}

func renderMarkdownLimitationsAndAppendix(output *bytes.Buffer, report Report) {
	output.WriteString("\n## Unavailable and deferred metrics\n\n- `growth/churn`: deferred; this analyzer does not inspect Git history.\n- Unsupported semantic metrics remain explicit `unavailable` values and contribute no ranking weight.\n\n## Warnings and limitations\n\n")
	if len(report.Warnings) == 0 {
		output.WriteString("No parse warnings were recorded. Structural scanners remain bounded lexical evidence, not grammar validity.\n")
	} else {
		for _, row := range report.Warnings {
			fmt.Fprintf(output, "- `%s` `%s`: %s\n", row.Code, markdownCell(row.Path), markdownCell(row.Detail))
		}
	}
	output.WriteString("\n## Appendix: all analyzed files\n\n| Path | Language | Bytes | SHA-256 | Confidence |\n| --- | --- | ---: | --- | --- |\n")
	files := append([]FileRow(nil), report.Files...)
	sort.Slice(files, func(i, j int) bool { return files[i].Path < files[j].Path })
	for _, row := range files {
		fmt.Fprintf(output, "| `%s` | %s | %d | `%s` | %s |\n", markdownCell(row.Path), row.Language, row.Bytes, row.SHA256, row.Confidence)
	}
}

func markdownCell(value string) string {
	return strings.ReplaceAll(strings.ReplaceAll(value, "|", "\\|"), "\n", " ")
}
