package hotspot

import "testing"

func int64Pointer(value int64) *int64 { return &value }

func TestRankingTiesCapabilityClassesAndTotalOrder(t *testing.T) {
	report := Report{Files: []FileRow{
		{ID: "file:b.go", Path: "b.go", Language: LanguageGo, Confidence: ConfidenceHigh, RankingEligible: true, Metrics: []Metric{
			{Name: MetricStatements, Availability: AvailabilityExact, Value: int64Pointer(10), RankClass: "go-statements:E"},
			{Name: MetricFileSize, Availability: AvailabilityExact, Value: int64Pointer(100), RankClass: "bytes:E"},
		}},
		{ID: "file:a.go", Path: "a.go", Language: LanguageGo, Confidence: ConfidenceHigh, RankingEligible: true, Metrics: []Metric{
			{Name: MetricStatements, Availability: AvailabilityExact, Value: int64Pointer(10), RankClass: "go-statements:E"},
			{Name: MetricFileSize, Availability: AvailabilityExact, Value: int64Pointer(100), RankClass: "bytes:E"},
		}},
		{ID: "file:Dockerfile", Path: "Dockerfile", Language: LanguageDockerfile, Confidence: ConfidenceHigh, RankingEligible: true, Metrics: []Metric{
			{Name: MetricStatements, Availability: AvailabilityStructural, Value: int64Pointer(10), RankClass: "docker-instructions:S"},
			{Name: MetricFileSize, Availability: AvailabilityExact, Value: int64Pointer(50), RankClass: "bytes:E"},
		}},
		{ID: "file:z.py", Path: "z.py", Language: LanguagePython, Confidence: ConfidenceLow, RankingEligible: true, Metrics: []Metric{
			{Name: MetricStatements, Availability: AvailabilityUnavailable, Reason: "qualified-parser-unavailable"},
			{Name: MetricFileSize, Availability: AvailabilityExact, Value: int64Pointer(25), RankClass: "bytes:E"},
		}},
	}}
	rankReport(&report)
	a := fileByPath(t, report, "a.go")
	b := fileByPath(t, report, "b.go")
	docker := fileByPath(t, report, "Dockerfile")
	if a.Ranking.Score != b.Ranking.Score {
		t.Fatalf("equal values received different scores: a=%#v b=%#v", a.Ranking, b.Ranking)
	}
	if percentileFor(t, a.Ranking, MetricStatements) != percentileFor(t, b.Ranking, MetricStatements) {
		t.Fatal("equal Go statement values received different percentiles")
	}
	if percentileFor(t, docker.Ranking, MetricStatements) != 10000 {
		t.Fatalf("single Docker structural class percentile = %d", percentileFor(t, docker.Ranking, MetricStatements))
	}
	positions := map[string]int{}
	for index, row := range report.Files {
		positions[row.Path] = index
	}
	if positions["a.go"] >= positions["b.go"] {
		t.Fatalf("path tie order = %#v", report.Files)
	}
	python := fileByPath(t, report, "z.py")
	if python.Ranking.AvailableWeight != 10 {
		t.Fatalf("missing metric contributed weight: %#v", python.Ranking)
	}
}

func percentileFor(t *testing.T, ranking Ranking, name string) int {
	t.Helper()
	for _, metric := range ranking.Vector {
		if metric.Name == name {
			return metric.Percentile
		}
	}
	t.Fatalf("ranking metric %q missing from %#v", name, ranking)
	return 0
}
