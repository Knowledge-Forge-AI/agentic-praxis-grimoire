package hotspot

import (
	"sort"
)

var rankingWeights = map[string]int{
	MetricCyclomatic:     35,
	MetricStatements:     25,
	MetricNesting:        15,
	MetricProceduralSize: 15,
	MetricFileSize:       10,
}

type rankTarget struct {
	path       string
	id         string
	confidence Confidence
	eligible   bool
	metrics    []Metric
	ranking    *Ranking
}

func rankReport(report *Report) {
	fileTargets := make([]rankTarget, 0, len(report.Files))
	for index := range report.Files {
		fileTargets = append(fileTargets, rankTarget{report.Files[index].Path, report.Files[index].ID, report.Files[index].Confidence, report.Files[index].RankingEligible, report.Files[index].Metrics, &report.Files[index].Ranking})
	}
	rankTargets(fileTargets)
	ownerTargets := make([]rankTarget, 0, len(report.Owners))
	for index := range report.Owners {
		ownerTargets = append(ownerTargets, rankTarget{report.Owners[index].Path, report.Owners[index].ID, report.Owners[index].Confidence, !report.Owners[index].Generated, report.Owners[index].Metrics, &report.Owners[index].Ranking})
	}
	rankTargets(ownerTargets)
	regionTargets := make([]rankTarget, 0, len(report.ProceduralRegions))
	for index := range report.ProceduralRegions {
		regionTargets = append(regionTargets, rankTarget{report.ProceduralRegions[index].Path, report.ProceduralRegions[index].ID, report.ProceduralRegions[index].Confidence, true, report.ProceduralRegions[index].Metrics, &report.ProceduralRegions[index].Ranking})
	}
	rankTargets(regionTargets)
	sort.SliceStable(report.Files, func(i, j int) bool {
		return rankedBefore(report.Files[i].Ranking, report.Files[i].Confidence, report.Files[i].Path, report.Files[i].ID, report.Files[j].Ranking, report.Files[j].Confidence, report.Files[j].Path, report.Files[j].ID)
	})
	sort.SliceStable(report.Owners, func(i, j int) bool {
		return rankedBefore(report.Owners[i].Ranking, report.Owners[i].Confidence, report.Owners[i].Path, report.Owners[i].ID, report.Owners[j].Ranking, report.Owners[j].Confidence, report.Owners[j].Path, report.Owners[j].ID)
	})
	sort.SliceStable(report.ProceduralRegions, func(i, j int) bool {
		return rankedBefore(report.ProceduralRegions[i].Ranking, report.ProceduralRegions[i].Confidence, report.ProceduralRegions[i].Path, report.ProceduralRegions[i].ID, report.ProceduralRegions[j].Ranking, report.ProceduralRegions[j].Confidence, report.ProceduralRegions[j].Path, report.ProceduralRegions[j].ID)
	})
}

type percentileEntry struct {
	target int
	raw    int64
	path   string
	id     string
}

func rankTargets(targets []rankTarget) {
	classes := collectPercentileClasses(targets)
	for key, entries := range classes {
		applyPercentileClass(targets, key, entries)
	}
	for _, target := range targets {
		finalizeRanking(target.ranking)
	}
}

func collectPercentileClasses(targets []rankTarget) map[string][]percentileEntry {
	classes := map[string][]percentileEntry{}
	for targetIndex, target := range targets {
		*target.ranking = Ranking{}
		if !target.eligible {
			continue
		}
		for _, value := range target.metrics {
			if _, weighted := rankingWeights[value.Name]; !weighted || value.Value == nil || value.RankClass == "" {
				continue
			}
			if value.Availability != AvailabilityExact && value.Availability != AvailabilityStructural {
				continue
			}
			key := value.Name + "\x00" + value.RankClass
			classes[key] = append(classes[key], percentileEntry{targetIndex, *value.Value, target.path, target.id})
		}
	}
	return classes
}

func applyPercentileClass(targets []rankTarget, key string, entries []percentileEntry) {
	sort.Slice(entries, func(i, j int) bool {
		if entries[i].raw != entries[j].raw {
			return entries[i].raw < entries[j].raw
		}
		if entries[i].path != entries[j].path {
			return entries[i].path < entries[j].path
		}
		return entries[i].id < entries[j].id
	})
	name, rankClass := splitRankKey(key)
	for start := 0; start < len(entries); {
		end := start + 1
		for end < len(entries) && entries[end].raw == entries[start].raw {
			end++
		}
		percentile := 10000
		if len(entries) > 1 {
			percentile = ((start + end - 1) * 10000) / (2 * (len(entries) - 1))
		}
		for index := start; index < end; index++ {
			target := targets[entries[index].target]
			target.ranking.Vector = append(target.ranking.Vector, RankingMetric{Name: name, Raw: entries[index].raw, Percentile: percentile, Weight: rankingWeights[name], RankClass: rankClass})
		}
		start = end
	}
}

func finalizeRanking(ranking *Ranking) {
	sort.Slice(ranking.Vector, func(i, j int) bool { return ranking.Vector[i].Name < ranking.Vector[j].Name })
	numerator, denominator := int64(0), 0
	for _, value := range ranking.Vector {
		numerator += int64(value.Percentile * value.Weight)
		denominator += value.Weight
	}
	ranking.AvailableWeight = denominator
	if denominator > 0 {
		ranking.Score = int(numerator / int64(denominator))
	}
}

func splitRankKey(value string) (string, string) {
	for index := 0; index < len(value); index++ {
		if value[index] == 0 {
			return value[:index], value[index+1:]
		}
	}
	return value, ""
}

func rankedBefore(left Ranking, leftConfidence Confidence, leftPath, leftID string, right Ranking, rightConfidence Confidence, rightPath, rightID string) bool {
	if left.Score != right.Score {
		return left.Score > right.Score
	}
	if left.AvailableWeight != right.AvailableWeight {
		return left.AvailableWeight > right.AvailableWeight
	}
	if confidenceOrder(leftConfidence) != confidenceOrder(rightConfidence) {
		return confidenceOrder(leftConfidence) > confidenceOrder(rightConfidence)
	}
	if leftPath != rightPath {
		return leftPath < rightPath
	}
	return leftID < rightID
}

func confidenceOrder(value Confidence) int {
	switch value {
	case ConfidenceHigh:
		return 3
	case ConfidenceMedium:
		return 2
	default:
		return 1
	}
}

func candidates(report Report) []RefactoringCandidate {
	result := []RefactoringCandidate{}
	ownerHotspots := map[string]int{}
	for _, row := range report.Owners {
		reasons := reasonCodes(row.Metrics, row.Ranking, row.Confidence, len(report.Owners), "owner")
		if len(reasons) == 0 || row.Generated {
			continue
		}
		ownerHotspots[row.Path]++
		result = append(result, RefactoringCandidate{Kind: "owner", TargetID: row.ID, Path: row.Path, RiskScore: row.Ranking.Score, AvailableWeight: row.Ranking.AvailableWeight, Confidence: row.Confidence, ReasonCodes: reasons})
	}
	for _, row := range report.ProceduralRegions {
		reasons := reasonCodes(row.Metrics, row.Ranking, row.Confidence, len(report.ProceduralRegions), "procedural-region")
		if len(reasons) == 0 {
			continue
		}
		result = append(result, RefactoringCandidate{Kind: "procedural-region", TargetID: row.ID, Path: row.Path, RiskScore: row.Ranking.Score, AvailableWeight: row.Ranking.AvailableWeight, Confidence: row.Confidence, ReasonCodes: reasons})
	}
	for _, row := range report.Files {
		if !row.RankingEligible {
			continue
		}
		reasons := reasonCodes(row.Metrics, row.Ranking, row.Confidence, len(report.Files), "file")
		if ownerHotspots[row.Path] >= 2 {
			reasons = append(reasons, "multiple-hotspot-owners")
		}
		if len(reasons) == 0 {
			continue
		}
		result = append(result, RefactoringCandidate{Kind: "file", TargetID: row.ID, Path: row.Path, RiskScore: row.Ranking.Score, AvailableWeight: row.Ranking.AvailableWeight, Confidence: row.Confidence, ReasonCodes: uniqueSorted(reasons)})
	}
	sort.Slice(result, func(i, j int) bool {
		return rankedBefore(Ranking{Score: result[i].RiskScore, AvailableWeight: result[i].AvailableWeight}, result[i].Confidence, result[i].Path, result[i].TargetID, Ranking{Score: result[j].RiskScore, AvailableWeight: result[j].AvailableWeight}, result[j].Confidence, result[j].Path, result[j].TargetID)
	})
	return result
}

func reasonCodes(metrics []Metric, ranking Ranking, confidence Confidence, population int, kind string) []string {
	reasons := []string{}
	for _, value := range ranking.Vector {
		if reason := rankingReason(value, population, kind); reason != "" {
			reasons = append(reasons, reason)
		}
	}
	if kind == "file" && confidence == ConfidenceLow && ranking.AvailableWeight == 10 && ranking.Score >= 9000 && availableMetricValue(metrics, MetricFileSize) >= 128*1024 {
		reasons = append(reasons, "low-confidence-size-only")
	}
	return uniqueSorted(reasons)
}

func rankingReason(value RankingMetric, population int, kind string) string {
	switch value.Name {
	case MetricCyclomatic:
		if value.Raw >= 10 && value.Percentile >= 7500 {
			return "high-cyclomatic"
		}
	case MetricStatements:
		if kind == "owner" && value.Raw >= 20 && value.Percentile >= 7500 {
			return "large-owner"
		}
	case MetricNesting:
		if value.Raw >= 4 {
			return "deep-nesting"
		}
	case MetricProceduralSize:
		if value.Raw >= 10 && value.Percentile >= 7500 {
			return "large-procedural-region"
		}
	case MetricFileSize:
		if kind == "file" && value.Percentile >= 9000 && value.Raw >= 1024 {
			return "large-file"
		}
	}
	return ""
}

func uniqueSorted(values []string) []string {
	sort.Strings(values)
	result := values[:0]
	for _, value := range values {
		if len(result) == 0 || result[len(result)-1] != value {
			result = append(result, value)
		}
	}
	return result
}
