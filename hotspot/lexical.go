package hotspot

import (
	"fmt"
	"strings"
	"unicode"
)

func analyzeLexicalOnly(content []byte, row *FileRow) {
	lexical := int64(0)
	for _, line := range splitLines(content) {
		trimmed := strings.TrimSpace(line)
		if trimmed != "" && !strings.HasPrefix(trimmed, "//") && !strings.HasPrefix(trimmed, "#") && !strings.HasPrefix(trimmed, "/*") && !strings.HasPrefix(trimmed, "*") {
			lexical++
		}
	}
	row.Metrics = append(row.Metrics, metric(MetricLexicalLines, AvailabilityStructural, lexical, "lines", ""))
	unavailableSemanticMetrics(row, "qualified-parser-unavailable")
}

func analyzeHTML(path string, content []byte, row *FileRow) []OwnerRow {
	text := string(content)
	state := htmlScanState{path: path, balanced: true, stack: []string{}, owners: []OwnerRow{}}
	line := 1
	for index := 0; index < len(text); {
		if text[index] == '\n' {
			line++
			index++
			continue
		}
		if text[index] != '<' {
			index++
			continue
		}
		end := strings.IndexByte(text[index:], '>')
		if end < 0 {
			state.balanced = false
			break
		}
		end += index
		token := strings.TrimSpace(text[index+1 : end])
		state.processToken(token, line, index+1)
		index = end + 1
	}
	if len(state.stack) != 0 {
		state.balanced = false
	}
	row.Metrics = append(row.Metrics, notApplicable(MetricStatements, "HTML statements are not meaningful"), metric(MetricSymbols, AvailabilityStructural, int64(len(state.owners)), "symbols", ""), notApplicable(MetricCyclomatic, "HTML cyclomatic complexity is not meaningful"), notApplicable(MetricProceduralSize, "HTML procedural regions are not meaningful"), metric(MetricElements, AvailabilityStructural, state.elements, "elements", ""), metric(MetricAttributes, AvailabilityStructural, state.attributes, "attributes", ""))
	if state.balanced {
		row.Metrics = append(row.Metrics, metric(MetricNesting, AvailabilityStructural, state.maximum, "levels", "html-tag-depth:S"))
	} else {
		row.Metrics = append(row.Metrics, unavailable(MetricNesting, "unbalanced-html-tags"))
		row.ParseFailure = "unbalanced-html-tags"
	}
	return state.owners
}

type htmlScanState struct {
	path                                 string
	elements, attributes, depth, maximum int64
	balanced                             bool
	stack                                []string
	owners                               []OwnerRow
}

func (state *htmlScanState) processToken(token string, line, column int) {
	if token == "" || strings.HasPrefix(token, "!") || strings.HasPrefix(token, "?") {
		return
	}
	closing := strings.HasPrefix(token, "/")
	selfClosing := strings.HasSuffix(token, "/")
	token = strings.TrimSpace(strings.TrimPrefix(strings.TrimSuffix(token, "/"), "/"))
	name := firstToken(token)
	if name == "" {
		return
	}
	if closing {
		state.closeTag(name)
		return
	}
	rest := token[len(name):]
	state.elements++
	state.attributes += countHTMLAttributes(rest)
	if id := htmlAttribute(rest, "id"); id != "" || isHTMLHeading(name) {
		display := name
		if id != "" {
			display += "#" + id
		}
		state.owners = append(state.owners, OwnerRow{ID: stableID("owner:html", state.path, line, column), Path: state.path, Language: LanguageHTML, Kind: "element-symbol", DisplayName: display, StartLine: line, EndLine: line, Confidence: ConfidenceMedium, Metrics: []Metric{lineSpanMetric(line, line)}})
	}
	if !selfClosing && !htmlVoid(name) {
		state.stack = append(state.stack, strings.ToLower(name))
		state.depth++
		if state.depth > state.maximum {
			state.maximum = state.depth
		}
	}
}

func (state *htmlScanState) closeTag(name string) {
	if len(state.stack) == 0 || !strings.EqualFold(state.stack[len(state.stack)-1], name) {
		state.balanced = false
		return
	}
	state.stack = state.stack[:len(state.stack)-1]
	state.depth--
}

func firstToken(value string) string {
	for index, character := range value {
		if unicode.IsSpace(character) {
			return value[:index]
		}
	}
	return value
}

func countHTMLAttributes(value string) int64 {
	count := int64(0)
	inQuote := rune(0)
	inToken := false
	for _, character := range value {
		if inQuote != 0 {
			if character == inQuote {
				inQuote = 0
			}
			continue
		}
		if character == '\'' || character == '"' {
			inQuote = character
			continue
		}
		if unicode.IsSpace(character) {
			inToken = false
			continue
		}
		if !inToken {
			count++
			inToken = true
		}
	}
	return count
}

func htmlAttribute(value, target string) string {
	lower := strings.ToLower(value)
	needle := strings.ToLower(target) + "="
	index := strings.Index(lower, needle)
	if index < 0 {
		return ""
	}
	rest := strings.TrimSpace(value[index+len(needle):])
	if rest == "" {
		return ""
	}
	if rest[0] == '\'' || rest[0] == '"' {
		quote := rest[0]
		if end := strings.IndexByte(rest[1:], quote); end >= 0 {
			return rest[1 : 1+end]
		}
		return ""
	}
	if end := strings.IndexAny(rest, " \t\r\n"); end >= 0 {
		return rest[:end]
	}
	return rest
}

func isHTMLHeading(name string) bool {
	lower := strings.ToLower(name)
	return len(lower) == 2 && lower[0] == 'h' && lower[1] >= '1' && lower[1] <= '6'
}

func htmlVoid(name string) bool {
	switch strings.ToLower(name) {
	case "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr":
		return true
	}
	return false
}

func analyzeCSS(path string, content []byte, row *FileRow) ([]OwnerRow, []RegionRow) {
	lines := splitLines(content)
	depth, maximum, declarations, selectors := int64(0), int64(0), int64(0), int64(0)
	var owners []OwnerRow
	var regions []RegionRow
	start := 0
	prelude := ""
	for index, line := range lines {
		trimmed := strings.TrimSpace(stripLineComment(line))
		if depth == 0 && strings.Contains(trimmed, "{") {
			start = index + 1
			prelude = strings.TrimSpace(strings.SplitN(trimmed, "{", 2)[0])
			if prelude != "" {
				selectors += int64(strings.Count(prelude, ",") + 1)
			}
		}
		opens, closes := strings.Count(trimmed, "{"), strings.Count(trimmed, "}")
		depth += int64(opens)
		if depth > maximum {
			maximum = depth
		}
		if depth > 0 {
			declarations += int64(strings.Count(trimmed, ";"))
		}
		depth -= int64(closes)
		if depth < 0 {
			depth = 0
		}
		if start > 0 && depth == 0 {
			end := index + 1
			id := stableID("region:css-rule", path, start, 1)
			metrics := []Metric{metric(MetricProceduralSize, AvailabilityStructural, int64(end-start+1), "lines", "css-rule-regions:S"), lineSpanMetric(start, end), notApplicable(MetricCyclomatic, "CSS rule regions have no cyclomatic complexity")}
			owners = append(owners, OwnerRow{ID: stableID("owner:css-rule", path, start, 1), Path: path, Language: LanguageCSS, Kind: "rule", DisplayName: prelude, StartLine: start, EndLine: end, Confidence: ConfidenceMedium, Metrics: append([]Metric(nil), metrics...)})
			regions = append(regions, RegionRow{ID: id, Path: path, Language: LanguageCSS, Kind: "rule-region", DisplayName: prelude, StartLine: start, EndLine: end, Confidence: ConfidenceMedium, Metrics: metrics})
			start = 0
			prelude = ""
		}
	}
	row.Metrics = append(row.Metrics, unavailable(MetricStatements, "CSS semantic statements are unavailable"), metric(MetricSymbols, AvailabilityStructural, int64(len(owners)), "rules", ""), notApplicable(MetricCyclomatic, "CSS cyclomatic complexity is not meaningful"), metric(MetricNesting, AvailabilityStructural, maximum, "levels", "css-block-depth:S"), metric(MetricSelectors, AvailabilityStructural, selectors, "selectors", ""), metric(MetricDeclarations, AvailabilityStructural, declarations, "declarations", ""))
	return owners, regions
}

func analyzeKeysAndIndent(language Language, content []byte, row *FileRow) {
	keys, maximum := int64(0), int64(0)
	for _, line := range splitLines(content) {
		trimmed := strings.TrimSpace(line)
		if trimmed == "" || strings.HasPrefix(trimmed, "#") {
			continue
		}
		indent := int64(len(line) - len(strings.TrimLeft(line, " \t")))
		if indent > maximum {
			maximum = indent
		}
		if language == LanguageYAML && strings.Contains(trimmed, ":") || language == LanguageTOML && (strings.Contains(trimmed, "=") || strings.HasPrefix(trimmed, "[")) {
			keys++
		}
	}
	row.Metrics = append(row.Metrics, notApplicable(MetricStatements, "declarative statements are not meaningful in v1"), unavailable(MetricSymbols, "qualified-parser-unavailable"), notApplicable(MetricCyclomatic, "declarative cyclomatic complexity is not meaningful"), unavailable(MetricNesting, "qualified-parser-unavailable"), notApplicable(MetricProceduralSize, "procedural regions are not meaningful"), metric(MetricKeysStructural, AvailabilityStructural, keys, "keys", ""), metric("maximum-indentation", AvailabilityStructural, maximum, "columns", ""))
}

func analyzeBraceLanguage(path string, language Language, content []byte, row *FileRow) []RegionRow {
	lines := splitLines(content)
	depth := 0
	start := 0
	label := ""
	blocks := int64(0)
	keys := int64(0)
	calls := int64(0)
	var regions []RegionRow
	for index, line := range lines {
		trimmed := strings.TrimSpace(stripLineComment(line))
		if trimmed == "" {
			continue
		}
		if strings.Contains(trimmed, "=") {
			keys++
		}
		if strings.Contains(trimmed, "(") {
			calls++
		}
		opens, closes := strings.Count(trimmed, "{"), strings.Count(trimmed, "}")
		if depth == 0 && opens > 0 {
			start = index + 1
			label = strings.TrimSpace(strings.SplitN(trimmed, "{", 2)[0])
			blocks++
		}
		depth += opens
		depth -= closes
		if depth < 0 {
			depth = 0
		}
		if start > 0 && depth == 0 {
			end := index + 1
			regions = append(regions, RegionRow{ID: stableID("region:block", path, start, 1), Path: path, Language: language, Kind: "top-level-block", DisplayName: label, StartLine: start, EndLine: end, Confidence: ConfidenceLow, Metrics: []Metric{metric(MetricProceduralSize, AvailabilityStructural, int64(end-start+1), "lines", string(language)+"-blocks:S"), lineSpanMetric(start, end), unavailable(MetricCyclomatic, "qualified-parser-unavailable")}})
			start = 0
		}
	}
	row.Metrics = append(row.Metrics, unavailable(MetricStatements, "qualified-parser-unavailable"), unavailable(MetricSymbols, "qualified-parser-unavailable"), unavailable(MetricCyclomatic, "qualified-parser-unavailable"), unavailable(MetricNesting, "qualified-parser-unavailable"), metric(MetricBlocks, AvailabilityStructural, blocks, "blocks", ""), metric(MetricKeysStructural, AvailabilityStructural, keys, "keys", ""), metric("calls", AvailabilityStructural, calls, "calls", ""))
	return regions
}

func analyzeSQL(path string, content []byte, row *FileRow) []RegionRow {
	lines := splitLines(content)
	start := 0
	var regions []RegionRow
	clauses := int64(0)
	keywords := []string{"SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "WHERE", "JOIN", "GROUP BY", "ORDER BY"}
	for index, line := range lines {
		trimmed := strings.TrimSpace(line)
		if trimmed == "" || strings.HasPrefix(trimmed, "--") {
			continue
		}
		upper := strings.ToUpper(trimmed)
		if start == 0 {
			start = index + 1
		}
		for _, keyword := range keywords {
			clauses += int64(strings.Count(upper, keyword))
		}
		if strings.Contains(trimmed, ";") {
			end := index + 1
			regions = append(regions, RegionRow{ID: stableID("region:sql", path, start, 1), Path: path, Language: LanguageSQL, Kind: "statement-region", DisplayName: firstToken(upper), StartLine: start, EndLine: end, Confidence: ConfidenceLow, Metrics: []Metric{metric(MetricProceduralSize, AvailabilityStructural, int64(end-start+1), "lines", "sql-regions:S"), lineSpanMetric(start, end), unavailable(MetricCyclomatic, "qualified-parser-unavailable")}})
			start = 0
		}
	}
	if start > 0 {
		end := len(lines)
		regions = append(regions, RegionRow{ID: stableID("region:sql", path, start, 1), Path: path, Language: LanguageSQL, Kind: "statement-region", DisplayName: "unterminated statement-like region", StartLine: start, EndLine: end, Confidence: ConfidenceLow, Metrics: []Metric{metric(MetricProceduralSize, AvailabilityStructural, int64(end-start+1), "lines", "sql-regions:S"), lineSpanMetric(start, end), unavailable(MetricCyclomatic, "qualified-parser-unavailable")}})
	}
	row.Metrics = append(row.Metrics, unavailable(MetricStatements, "qualified-parser-unavailable"), unavailable(MetricSymbols, "qualified-parser-unavailable"), unavailable(MetricCyclomatic, "qualified-parser-unavailable"), unavailable(MetricNesting, "qualified-parser-unavailable"), metric(MetricClauses, AvailabilityStructural, clauses, "keyword occurrences", ""))
	return regions
}

func analyzeShell(path string, language Language, content []byte, row *FileRow) []RegionRow {
	lines := splitLines(content)
	commands, controls := int64(0), int64(0)
	var regions []RegionRow
	for index, line := range lines {
		trimmed := strings.TrimSpace(line)
		if trimmed == "" || strings.HasPrefix(trimmed, "#") {
			continue
		}
		commands++
		for _, token := range []string{"if ", "for ", "while ", "case ", "&&", "||"} {
			controls += int64(strings.Count(trimmed, token))
		}
		regions = append(regions, RegionRow{ID: stableID("region:shell", path, index+1, 1), Path: path, Language: language, Kind: "top-level-region", DisplayName: firstToken(trimmed), StartLine: index + 1, EndLine: index + 1, Confidence: ConfidenceLow, Metrics: []Metric{metric(MetricProceduralSize, AvailabilityStructural, 1, "lines", "shell-regions:S"), lineSpanMetric(index+1, index+1), unavailable(MetricCyclomatic, "qualified-parser-unavailable")}})
	}
	row.Metrics = append(row.Metrics, unavailable(MetricStatements, "qualified-parser-unavailable"), unavailable(MetricSymbols, "qualified-parser-unavailable"), unavailable(MetricCyclomatic, "qualified-parser-unavailable"), unavailable(MetricNesting, "qualified-parser-unavailable"), metric(MetricCommands, AvailabilityStructural, commands, "commands", ""), metric(MetricControlTokens, AvailabilityStructural, controls, "tokens", ""))
	return regions
}

func analyzeDockerfile(path string, content []byte, row *FileRow) ([]OwnerRow, []RegionRow) {
	lines := splitLines(content)
	type logical struct {
		start, end int
		text       string
	}
	var values []logical
	start := 0
	current := ""
	for index, line := range lines {
		trimmed := strings.TrimSpace(line)
		if start == 0 && trimmed != "" && !strings.HasPrefix(trimmed, "#") {
			start = index + 1
		}
		if start == 0 {
			continue
		}
		continuation := strings.HasSuffix(trimmed, "\\")
		part := strings.TrimSpace(strings.TrimSuffix(trimmed, "\\"))
		if current != "" {
			current += " "
		}
		current += part
		if !continuation {
			values = append(values, logical{start, index + 1, current})
			start = 0
			current = ""
		}
	}
	if start > 0 {
		values = append(values, logical{start, len(lines), current})
	}
	stages, runs := int64(0), int64(0)
	var owners []OwnerRow
	var regions []RegionRow
	for _, value := range values {
		instruction := strings.ToUpper(firstToken(value.text))
		if instruction == "FROM" {
			stages++
		}
		if instruction == "RUN" {
			runs++
		}
		metrics := []Metric{metric(MetricProceduralSize, AvailabilityExact, 1, "instructions", "docker-instructions:E"), metric(MetricStatements, AvailabilityStructural, 1, "instructions", "docker-instructions:S"), lineSpanMetric(value.start, value.end), notApplicable(MetricCyclomatic, "Dockerfile cyclomatic complexity is not meaningful")}
		display := instruction + " at line " + fmt.Sprint(value.start)
		owners = append(owners, OwnerRow{ID: stableID("owner:instruction", path, value.start, 1), Path: path, Language: LanguageDockerfile, Kind: "instruction", DisplayName: display, StartLine: value.start, EndLine: value.end, Confidence: ConfidenceHigh, Metrics: append([]Metric(nil), metrics...)})
		regions = append(regions, RegionRow{ID: stableID("region:instruction", path, value.start, 1), Path: path, Language: LanguageDockerfile, Kind: "instruction", DisplayName: display, StartLine: value.start, EndLine: value.end, Confidence: ConfidenceHigh, Metrics: metrics})
	}
	row.Metrics = append(row.Metrics, metric(MetricStatements, AvailabilityStructural, int64(len(values)), "instructions", "docker-instructions:S"), metric(MetricSymbols, AvailabilityStructural, stages, "stages", ""), notApplicable(MetricCyclomatic, "Dockerfile cyclomatic complexity is not meaningful"), notApplicable(MetricNesting, "Dockerfile nesting is not meaningful"), metric(MetricInstructions, AvailabilityExact, int64(len(values)), "instructions", ""), metric(MetricStages, AvailabilityExact, stages, "stages", ""), metric(MetricRuns, AvailabilityExact, runs, "instructions", ""))
	row.PrimarySize = PrimarySize{Value: int64(len(values)), Unit: "instructions"}
	return owners, regions
}

func stripLineComment(value string) string {
	if index := strings.Index(value, "//"); index >= 0 {
		return value[:index]
	}
	return value
}
