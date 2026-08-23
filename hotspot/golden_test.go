package hotspot

import (
	"os"
	"path/filepath"
	"testing"
)

func TestCanonicalMultilanguageGolden(t *testing.T) {
	report := Report{
		SchemaVersion: ReportSchemaV1, ToolVersion: "golden", RootID: "golden-root", CompletionStatus: CompletionComplete,
		ScanConfiguration: ScanConfiguration{RequestSchemaVersion: RequestSchemaV1, MaxFiles: 10, MaxBytesPerFile: 1024, MaxTotalBytes: 2048, MaxDurationMilliseconds: 1000, DefaultExclusionsEnabled: true, IncludeLanguages: []Language{}, IncludePaths: []string{}, ExcludePaths: []string{}, DisplayTopN: 10},
		Exclusions:        []Exclusion{}, CapabilityVersion: CapabilityMatrixV1, Capabilities: []SurfaceCapability{frozenCapabilities()[0], frozenCapabilities()[4]}, DeferredCapabilities: []DeferredCapability{{Name: "growth/churn", Status: "deferred"}},
		Owners: []OwnerRow{}, ProceduralRegions: []RegionRow{}, Warnings: []Warning{},
		Files: []FileRow{
			{ID: "file:main.go", Path: "main.go", Language: LanguageGo, Confidence: ConfidenceHigh, SHA256: "sha256:go", Bytes: 20, PhysicalLines: int64Pointer(2), PrimarySize: PrimarySize{Value: 1, Unit: "statements"}, RankingEligible: true, Metrics: []Metric{
				metric(MetricFileSize, AvailabilityExact, 20, "bytes", "bytes:E"), metric(MetricStatements, AvailabilityExact, 1, "statements", "go-statements:E"), metric(MetricCyclomatic, AvailabilityExact, 1, "complexity", "go-cyclomatic:E"), metric(MetricNesting, AvailabilityExact, 0, "levels", "go-control-nesting:E"),
			}},
			{ID: "file:tool.py", Path: "tool.py", Language: LanguagePython, Confidence: ConfidenceLow, SHA256: "sha256:python", Bytes: 10, PhysicalLines: int64Pointer(1), PrimarySize: PrimarySize{Value: 1, Unit: "lines"}, RankingEligible: true, Metrics: []Metric{
				metric(MetricFileSize, AvailabilityExact, 10, "bytes", "bytes:E"), unavailable(MetricStatements, "qualified-parser-unavailable"), unavailable(MetricCyclomatic, "qualified-parser-unavailable"), unavailable(MetricNesting, "qualified-parser-unavailable"), unavailable(MetricProceduralSize, "qualified-parser-unavailable"),
			}},
		},
	}
	report.LanguageAggregates = aggregateLanguages(report.Files)
	rankReport(&report)
	report.RefactoringCandidates = candidates(report)
	var err error
	report.Fingerprint, err = fingerprint(report)
	if err != nil {
		t.Fatal(err)
	}
	actual, err := MarshalJSON(report)
	if err != nil {
		t.Fatal(err)
	}
	expected, err := os.ReadFile(filepath.Join("testdata", "golden", "multilanguage.json"))
	if err != nil {
		t.Fatalf("golden unavailable: %v\nactual:\n%s", err, actual)
	}
	if string(actual) != string(expected) {
		t.Fatalf("canonical JSON drift\nactual:\n%s\nexpected:\n%s", actual, expected)
	}
}
