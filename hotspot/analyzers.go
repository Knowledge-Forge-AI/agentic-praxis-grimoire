package hotspot

import (
	"fmt"
	"sort"
)

func metric(name string, availability Availability, value int64, unit, rankClass string) Metric {
	copy := value
	return Metric{Name: name, Availability: availability, Value: &copy, Unit: unit, RankClass: rankClass}
}

func unavailable(name, reason string) Metric {
	return Metric{Name: name, Availability: AvailabilityUnavailable, Reason: reason}
}

func notApplicable(name, reason string) Metric {
	return Metric{Name: name, Availability: AvailabilityNotApplicable, Reason: reason}
}

func analyzeFile(path string, class classification, content []byte, identity fileIdentity) (FileRow, []OwnerRow, []RegionRow, []Warning) {
	row := baseFileRow(path, class, identity)
	owners, regions, warnings := runFileAnalyzer(path, class, content, &row)
	if row.Generated {
		row.RankingEligible = false
	}
	setProceduralFileMetric(&row, regions)
	sort.Slice(row.Metrics, func(i, j int) bool { return row.Metrics[i].Name < row.Metrics[j].Name })
	for index := range owners {
		sort.Slice(owners[index].Metrics, func(i, j int) bool { return owners[index].Metrics[i].Name < owners[index].Metrics[j].Name })
	}
	for index := range regions {
		sort.Slice(regions[index].Metrics, func(i, j int) bool { return regions[index].Metrics[i].Name < regions[index].Metrics[j].Name })
	}
	return row, owners, regions, warnings
}

func baseFileRow(path string, class classification, identity fileIdentity) FileRow {
	row := FileRow{
		ID: "file:" + path, Path: path, Language: class.language, Confidence: confidenceFor(class.language),
		SHA256: identity.sha256, Bytes: identity.bytes, Generated: false, RankingEligible: true,
		Metrics:     []Metric{metric(MetricBytes, AvailabilityExact, identity.bytes, "bytes", "")},
		PrimarySize: PrimarySize{Value: identity.bytes, Unit: "bytes"},
	}
	if class.text {
		row.PhysicalLines = identity.lines
		row.Metrics = append(row.Metrics,
			metric(MetricPhysicalLines, AvailabilityExact, *identity.lines, "lines", ""),
			metric(MetricFileSize, AvailabilityExact, identity.bytes, "bytes", "bytes:E"),
		)
		row.PrimarySize = PrimarySize{Value: *identity.lines, Unit: "lines"}
	} else {
		row.Metrics = append(row.Metrics, metric(MetricFileSize, AvailabilityExact, identity.bytes, "bytes", "bytes:E"))
	}
	return row
}

func runFileAnalyzer(path string, class classification, content []byte, row *FileRow) ([]OwnerRow, []RegionRow, []Warning) {
	var owners []OwnerRow
	var regions []RegionRow
	var warnings []Warning
	switch class.language {
	case LanguageGo:
		owners, regions, warnings = analyzeGo(path, content, row)
	case LanguageMarkdown:
		owners, regions = analyzeMarkdown(path, content, row)
	case LanguageMDX, LanguageAstro:
		owners, regions = analyzeHybrid(path, class.language, content, row)
	case LanguageXML, LanguageXMLPlist:
		owners, warnings = analyzeXML(path, content, row)
	case LanguageJSON, LanguageJSONFamily:
		owners, warnings = analyzeJSON(path, content, row)
	case LanguageDockerfile:
		owners, regions = analyzeDockerfile(path, content, row)
	case LanguageHTML:
		owners = analyzeHTML(path, content, row)
	case LanguageCSS:
		owners, regions = analyzeCSS(path, content, row)
	case LanguageYAML, LanguageTOML:
		analyzeKeysAndIndent(class.language, content, row)
	case LanguageTerraform, LanguageGradle, LanguageVagrantfile:
		regions = analyzeBraceLanguage(path, class.language, content, row)
	case LanguageSQL:
		regions = analyzeSQL(path, content, row)
	case LanguageBash, LanguageZsh, LanguagePOSIXShell:
		regions = analyzeShell(path, class.language, content, row)
	case LanguagePython, LanguageJava, LanguageKotlin, LanguageJavaScript, LanguageTypeScript, LanguageJSX, LanguageTSX:
		analyzeLexicalOnly(content, row)
	case LanguageBinaryPlist:
		row.Metrics = append(row.Metrics,
			notApplicable(MetricStatements, "binary-plist-statements-not-meaningful"),
			unavailable(MetricSymbols, "binary-plist-parser-unavailable"),
			notApplicable(MetricCyclomatic, "binary-plist-cyclomatic-not-meaningful"),
			unavailable(MetricNesting, "binary-plist-parser-unavailable"),
			notApplicable(MetricProceduralSize, "binary-plist-procedural-regions-not-meaningful"),
		)
	case LanguageBinary, LanguageUnknown:
		row.Metrics = append(row.Metrics,
			unavailable(MetricStatements, "unsupported-language"), unavailable(MetricSymbols, "unsupported-language"),
			unavailable(MetricCyclomatic, "unsupported-language"), unavailable(MetricNesting, "unsupported-language"),
			unavailable(MetricProceduralSize, "unsupported-language"),
		)
	}
	return owners, regions, warnings
}

func setProceduralFileMetric(row *FileRow, regions []RegionRow) {
	for _, existing := range row.Metrics {
		if existing.Name == MetricProceduralSize {
			return
		}
	}
	if len(regions) == 0 {
		return
	}
	maximum := int64(0)
	rankClass := ""
	availability := AvailabilityStructural
	for _, region := range regions {
		for _, value := range region.Metrics {
			if value.Name == MetricProceduralSize && value.Value != nil && *value.Value >= maximum {
				maximum = *value.Value
				rankClass = value.RankClass
				availability = value.Availability
			}
		}
	}
	row.Metrics = append(row.Metrics, metric(MetricProceduralSize, availability, maximum, "lines", rankClass))
}

func unavailableSemanticMetrics(row *FileRow, reason string) {
	row.Metrics = append(row.Metrics,
		unavailable(MetricStatements, reason), unavailable(MetricSymbols, reason), unavailable(MetricCyclomatic, reason),
		unavailable(MetricNesting, reason), unavailable(MetricProceduralSize, reason),
	)
}

func lineSpanMetric(start, end int) Metric {
	length := int64(0)
	if end >= start && start > 0 {
		length = int64(end - start + 1)
	}
	return metric(MetricFileSize, AvailabilityExact, length, "lines", "owner-lines:E")
}

func stableID(kind, path string, line, column int) string {
	return fmt.Sprintf("%s:%s@%d:%d", kind, path, line, column)
}
