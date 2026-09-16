package hotspot

import (
	"bytes"
	"fmt"
)

// RenderTerminalV2 preserves the structural view and appends bounded history.
// History rows are path-ordered; this is not an implicit churn ranking.
func RenderTerminalV2(report ReportV2) ([]byte, error) {
	if err := validateReportV2(report); err != nil {
		return nil, err
	}
	v1, err := structuralFromV2(report)
	if err != nil {
		return nil, err
	}
	content, err := RenderTerminal(v1)
	if err != nil {
		return nil, err
	}
	var out bytes.Buffer
	out.Write(content)
	fmt.Fprintf(&out, "\nHistory (v2, first-parent integration): %s..%s\n", report.History.StartOID, report.History.EndOID)
	fmt.Fprintf(&out, "%d commits; %d transitions; available churn subtotal=%d lines; available growth subtotal=%+d lines; unavailable paths=%d\n", report.History.CommitCount, report.History.PathTransitionCount, report.History.TotalChurn, report.History.NetGrowth, report.History.UnavailablePaths)
	for i, h := range report.History.Files {
		if i >= report.ScanConfiguration.DisplayTopN {
			break
		}
		fmt.Fprintf(&out, "  %s churn=%s growth=%s transitions=%d [%s]\n", h.Path, historyNumber(h.Churn), historyNumber(h.Growth), h.TransitionCount, h.WorkingTreeStatus)
	}
	fmt.Fprintf(&out, "History report fingerprint: %s\n", report.Fingerprint)
	return out.Bytes(), nil
}

// RenderMarkdownV2 retains detailed structural evidence and adds all history rows.
func RenderMarkdownV2(report ReportV2) ([]byte, error) {
	if err := validateReportV2(report); err != nil {
		return nil, err
	}
	v1, err := structuralFromV2(report)
	if err != nil {
		return nil, err
	}
	content, err := renderMarkdown(v1, true)
	if err != nil {
		return nil, err
	}
	var out bytes.Buffer
	out.Write(content)
	fmt.Fprintf(&out, "\n## File history (v2)\n\nPolicy: `%s`. First-parent integration range `%s..%s` (start excluded).\n\nHistory report fingerprint: `%s`.\n\nAvailable churn subtotal: %d physical lines; available growth subtotal: %+d physical lines. These are subtotals over available rows, not complete totals when unavailable paths (%d) exist.\n\n", report.History.Policy, report.History.StartOID, report.History.EndOID, report.Fingerprint, report.History.TotalChurn, report.History.NetGrowth, report.History.UnavailablePaths)
	out.WriteString("| Path | Churn (inserted + deleted lines) | Growth (lines) | Changed transitions | Content binding |\n| --- | ---: | ---: | ---: | --- |\n")
	for _, h := range report.History.Files {
		fmt.Fprintf(&out, "| `%s` | %s | %s | %d | %s |\n", markdownCell(h.Path), historyNumber(h.Churn), historyNumber(h.Growth), h.TransitionCount, h.WorkingTreeStatus)
	}
	return out.Bytes(), nil
}

func historyNumber(n *int64) string {
	if n == nil {
		return "unavailable"
	}
	return fmt.Sprint(*n)
}

func structuralFromV2(r ReportV2) (Report, error) {
	c := r.ScanConfiguration
	v1 := Report{SchemaVersion: ReportSchemaV1, ToolVersion: r.ToolVersion, RootID: r.RootID, CompletionStatus: r.CompletionStatus,
		ScanConfiguration: ScanConfiguration{RequestSchemaVersion: RequestSchemaV1, MaxFiles: c.MaxFiles, MaxBytesPerFile: c.MaxBytesPerFile, MaxTotalBytes: c.MaxTotalBytes, MaxDurationMilliseconds: c.MaxDurationMilliseconds, DefaultExclusionsEnabled: c.DefaultExclusionsEnabled, IncludeLanguages: c.IncludeLanguages, IncludePaths: c.IncludePaths, ExcludePaths: c.ExcludePaths, DisplayTopN: c.DisplayTopN},
		Exclusions:        r.Exclusions, CapabilityVersion: CapabilityMatrixV1, Capabilities: r.Capabilities, DeferredCapabilities: structuralDeferredCapabilities(), LanguageAggregates: r.LanguageAggregates, Files: []FileRow{}, Owners: r.Owners, ProceduralRegions: r.ProceduralRegions, RefactoringCandidates: r.RefactoringCandidates, Warnings: r.Warnings}
	for _, f := range r.Files {
		v1.Files = append(v1.Files, FileRow{ID: f.ID, Path: f.Path, Language: f.Language, Confidence: f.Confidence, SHA256: f.SHA256, Bytes: f.Bytes, PhysicalLines: f.PhysicalLines, PrimarySize: f.PrimarySize, Generated: f.Generated, RankingEligible: f.RankingEligible, ParseFailure: f.ParseFailure, Metrics: f.Metrics, Ranking: f.Ranking})
	}
	var err error
	v1.Fingerprint, err = fingerprint(v1)
	return v1, err
}
