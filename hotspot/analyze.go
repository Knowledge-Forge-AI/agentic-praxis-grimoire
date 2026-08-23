package hotspot

import (
	"context"
	"os"
	"path/filepath"
	"sort"
)

// Analyze scans one exact root read-only and returns only complete reports.
func Analyze(ctx context.Context, request Request) (Report, error) {
	validated, err := validateRequest(request)
	if err != nil {
		return Report{}, err
	}
	root, err := validateRoot(validated.Root)
	if err != nil {
		return Report{}, err
	}
	bounded, cancel := context.WithTimeout(ctx, validated.Limits.MaxDuration)
	defer cancel()
	scan := newScanner(bounded, ctx, validated, root)
	if err := scan.walk("", 0); err != nil {
		return Report{}, err
	}
	sort.Slice(scan.files, func(i, j int) bool { return scan.files[i].Path < scan.files[j].Path })
	sort.Slice(scan.owners, func(i, j int) bool {
		if scan.owners[i].Path == scan.owners[j].Path {
			return scan.owners[i].ID < scan.owners[j].ID
		}
		return scan.owners[i].Path < scan.owners[j].Path
	})
	sort.Slice(scan.regions, func(i, j int) bool {
		if scan.regions[i].Path == scan.regions[j].Path {
			return scan.regions[i].ID < scan.regions[j].ID
		}
		return scan.regions[i].Path < scan.regions[j].Path
	})
	sort.Slice(scan.warnings, func(i, j int) bool {
		if scan.warnings[i].Path == scan.warnings[j].Path {
			return scan.warnings[i].Code < scan.warnings[j].Code
		}
		return scan.warnings[i].Path < scan.warnings[j].Path
	})
	report := Report{
		SchemaVersion: ReportSchemaV1, ToolVersion: validated.ToolVersion, RootID: validated.RootID,
		CompletionStatus: CompletionComplete,
		ScanConfiguration: ScanConfiguration{
			RequestSchemaVersion: RequestSchemaV1, MaxFiles: validated.Limits.MaxFiles,
			MaxBytesPerFile: validated.Limits.MaxBytesPerFile, MaxTotalBytes: validated.Limits.MaxTotalBytes,
			MaxDurationMilliseconds: validated.Limits.MaxDuration.Milliseconds(), DefaultExclusionsEnabled: !validated.Filters.DisableDefaultExclusions,
			IncludeLanguages: validated.Filters.IncludeLanguages, IncludePaths: validated.Filters.IncludePaths,
			ExcludePaths: validated.Filters.ExcludePaths, DisplayTopN: validated.DisplayTopN,
		},
		Exclusions: scan.exclusionRows(), CapabilityVersion: CapabilityMatrixV1, Capabilities: frozenCapabilities(),
		DeferredCapabilities: []DeferredCapability{{Name: "growth/churn", Status: "deferred"}},
		Files:                scan.files, Owners: scan.owners, ProceduralRegions: scan.regions, Warnings: scan.warnings,
	}
	report.LanguageAggregates = aggregateLanguages(report.Files)
	rankReport(&report)
	report.RefactoringCandidates = candidates(report)
	report.Fingerprint, err = fingerprint(report)
	if err != nil {
		return Report{}, err
	}
	return report, nil
}

func validateRoot(root string) (string, error) {
	metadata, err := os.Lstat(root)
	if err != nil || metadata.Mode()&os.ModeSymlink != 0 || !metadata.IsDir() {
		return "", rootSafety("root must be an existing direct directory")
	}
	resolved, err := filepath.EvalSymlinks(root)
	if err != nil || resolved != root {
		return "", rootSafety("resolved physical root differs from requested root")
	}
	return root, nil
}

func aggregateLanguages(files []FileRow) []LanguageAggregate {
	byLanguage := map[Language]*LanguageAggregate{}
	for _, file := range files {
		row := byLanguage[file.Language]
		if row == nil {
			row = &LanguageAggregate{Language: file.Language, Metrics: []AggregateMetric{}}
			byLanguage[file.Language] = row
		}
		row.Files++
		row.Bytes += file.Bytes
		for _, metric := range file.Metrics {
			if metric.Value == nil || metric.Name == MetricFileSize || metric.Name == MetricBytes {
				continue
			}
			found := false
			for index := range row.Metrics {
				if row.Metrics[index].Name == metric.Name && row.Metrics[index].Unit == metric.Unit {
					row.Metrics[index].Value += *metric.Value
					found = true
					break
				}
			}
			if !found {
				row.Metrics = append(row.Metrics, AggregateMetric{Name: metric.Name, Value: *metric.Value, Unit: metric.Unit})
			}
		}
	}
	result := make([]LanguageAggregate, 0, len(byLanguage))
	for _, row := range byLanguage {
		sort.Slice(row.Metrics, func(i, j int) bool { return row.Metrics[i].Name < row.Metrics[j].Name })
		result = append(result, *row)
	}
	sort.Slice(result, func(i, j int) bool { return result[i].Language < result[j].Language })
	return result
}
