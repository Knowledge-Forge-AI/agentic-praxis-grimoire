package hotspot

import (
	"bytes"
	"encoding/json"
	"encoding/xml"
	"fmt"
	"io"
	"strconv"
	"strings"
)

const maxStructuredDepth = 512

type jsonFrame struct {
	kind       json.Delim
	path       string
	count      int64
	expectKey  bool
	pendingKey string
	ownerIndex int
}

type jsonScanState struct {
	path                                    string
	language                                Language
	stack                                   []jsonFrame
	owners                                  []OwnerRow
	objects, keys, arrays, scalars          int64
	maxDepth, maxKeys, maxArray, rootValues int64
}

func analyzeJSON(path string, content []byte, row *FileRow) ([]OwnerRow, []Warning) {
	if maximum, ok := boundedJSONDepth(content); !ok || maximum > maxStructuredDepth {
		return jsonParseFailure(path, row, "JSON nesting exceeds the bounded parser depth")
	}
	decoder := json.NewDecoder(bytes.NewReader(content))
	decoder.UseNumber()
	state := jsonScanState{path: path, language: row.Language, stack: []jsonFrame{}, owners: []OwnerRow{}}
	for {
		token, err := decoder.Token()
		if err == io.EOF {
			break
		}
		if err != nil {
			return jsonParseFailure(path, row, "strict JSON parsing failed; target bytes were not normalized")
		}
		if err := state.consume(token); err != nil {
			return jsonParseFailure(path, row, err.Error())
		}
	}
	if len(state.stack) != 0 || state.rootValues != 1 {
		return jsonParseFailure(path, row, "strict JSON contains trailing or incomplete content")
	}
	row.Metrics = append(row.Metrics,
		notApplicable(MetricStatements, "JSON statements are not meaningful"), metric(MetricSymbols, AvailabilityStructural, int64(len(state.owners)), "object paths", ""),
		notApplicable(MetricCyclomatic, "JSON cyclomatic complexity is not meaningful"), metric(MetricNesting, AvailabilityExact, state.maxDepth, "levels", "json-depth:E"),
		notApplicable(MetricProceduralSize, "JSON procedural regions are not meaningful"), metric(MetricObjects, AvailabilityExact, state.objects, "objects", ""),
		metric(MetricKeys, AvailabilityExact, state.keys, "keys", ""), metric(MetricArrays, AvailabilityExact, state.arrays, "arrays", ""),
		metric(MetricScalars, AvailabilityExact, state.scalars, "scalars", ""), metric(MetricMaxObjectKeys, AvailabilityExact, state.maxKeys, "keys", ""),
		metric(MetricMaxArrayLength, AvailabilityExact, state.maxArray, "items", ""),
	)
	return state.owners, nil
}

func (state *jsonScanState) consume(token json.Token) error {
	if delimiter, ok := token.(json.Delim); ok {
		switch delimiter {
		case '{', '[':
			return state.open(delimiter)
		case '}', ']':
			return state.close(delimiter)
		}
	}
	if len(state.stack) > 0 && state.stack[len(state.stack)-1].kind == '{' && state.stack[len(state.stack)-1].expectKey {
		key, ok := token.(string)
		if !ok {
			return fmt.Errorf("strict JSON object key is invalid")
		}
		current := &state.stack[len(state.stack)-1]
		current.pendingKey, current.expectKey = key, false
		current.count++
		state.keys++
		return nil
	}
	if len(state.stack) == 0 {
		state.rootValues++
	} else if _, valid := jsonValuePath(state.stack); !valid {
		return fmt.Errorf("strict JSON token order is invalid")
	}
	state.scalars++
	return nil
}

func (state *jsonScanState) open(delimiter json.Delim) error {
	valuePath, valid := jsonValuePath(state.stack)
	if !valid {
		return fmt.Errorf("strict JSON token order is invalid")
	}
	if len(state.stack) == 0 {
		state.rootValues++
	}
	frame := jsonFrame{kind: delimiter, path: valuePath, ownerIndex: -1}
	if delimiter == '{' {
		state.objects++
		frame.expectKey = true
		if len(state.owners) < 256 {
			frame.ownerIndex = len(state.owners)
			state.owners = append(state.owners, OwnerRow{ID: fmt.Sprintf("owner:json:%s:%d", state.path, state.objects), Path: state.path, Language: state.language, Kind: "object-path", DisplayName: valuePath, Confidence: ConfidenceHigh})
		}
	} else {
		state.arrays++
	}
	state.stack = append(state.stack, frame)
	if int64(len(state.stack)) > state.maxDepth {
		state.maxDepth = int64(len(state.stack))
	}
	return nil
}

func (state *jsonScanState) close(delimiter json.Delim) error {
	if len(state.stack) == 0 || delimiter == '}' && state.stack[len(state.stack)-1].kind != '{' || delimiter == ']' && state.stack[len(state.stack)-1].kind != '[' {
		return fmt.Errorf("strict JSON delimiter order is invalid")
	}
	closed := state.stack[len(state.stack)-1]
	state.stack = state.stack[:len(state.stack)-1]
	if closed.kind == '{' {
		if !closed.expectKey {
			return fmt.Errorf("strict JSON object value is missing")
		}
		if closed.count > state.maxKeys {
			state.maxKeys = closed.count
		}
		if closed.ownerIndex >= 0 {
			state.owners[closed.ownerIndex].Metrics = []Metric{metric(MetricKeys, AvailabilityExact, closed.count, "keys", "")}
		}
	} else if closed.count > state.maxArray {
		state.maxArray = closed.count
	}
	return nil
}

func jsonValuePath(stack []jsonFrame) (string, bool) {
	if len(stack) == 0 {
		return "$", true
	}
	current := &stack[len(stack)-1]
	if current.kind == '{' {
		if current.expectKey {
			return "", false
		}
		path := current.path + "." + current.pendingKey
		current.pendingKey = ""
		current.expectKey = true
		return path, true
	}
	path := current.path + "[" + strconv.FormatInt(current.count, 10) + "]"
	current.count++
	return path, true
}

func jsonParseFailure(path string, row *FileRow, detail string) ([]OwnerRow, []Warning) {
	row.ParseFailure = "strict-json-parse-failure"
	row.Metrics = append(row.Metrics, notApplicable(MetricStatements, "JSON statements are not meaningful"), unavailable(MetricSymbols, "strict-json-parse-failed"), notApplicable(MetricCyclomatic, "JSON cyclomatic complexity is not meaningful"), unavailable(MetricNesting, "strict-json-parse-failed"), notApplicable(MetricProceduralSize, "JSON procedural regions are not meaningful"))
	return nil, []Warning{{Code: "parse-failure", Path: path, Detail: detail}}
}

func boundedJSONDepth(content []byte) (int, bool) {
	depth, maximum := 0, 0
	inString, escaped := false, false
	for _, value := range content {
		if inString {
			if escaped {
				escaped = false
				continue
			}
			if value == '\\' {
				escaped = true
				continue
			}
			if value == '"' {
				inString = false
			}
			continue
		}
		if value == '"' {
			inString = true
			continue
		}
		switch value {
		case '{', '[':
			depth++
			if depth > maximum {
				maximum = depth
			}
		case '}', ']':
			depth--
			if depth < 0 {
				return maximum, false
			}
		}
	}
	return maximum, !inString && depth == 0
}

func analyzeXML(path string, content []byte, row *FileRow) ([]OwnerRow, []Warning) {
	decoder := xml.NewDecoder(bytes.NewReader(content))
	depth, elements, attributes, maximum := 0, int64(0), int64(0), int64(0)
	pathParts := []string{}
	var owners []OwnerRow
	for {
		token, err := decoder.Token()
		if err == io.EOF {
			break
		}
		if err != nil {
			row.ParseFailure = "xml-parse-failure"
			row.Metrics = append(row.Metrics, notApplicable(MetricStatements, "XML statements are not meaningful"), unavailable(MetricSymbols, "xml-parse-failed"), notApplicable(MetricCyclomatic, "XML cyclomatic complexity is not meaningful"), unavailable(MetricNesting, "xml-parse-failed"), notApplicable(MetricProceduralSize, "XML procedural regions are not meaningful"))
			return nil, []Warning{{Code: "parse-failure", Path: path, Detail: "XML parsing failed"}}
		}
		switch value := token.(type) {
		case xml.StartElement:
			depth++
			if depth > maxStructuredDepth {
				row.ParseFailure = "xml-depth-limit"
				row.Metrics = append(row.Metrics, notApplicable(MetricStatements, "XML statements are not meaningful"), unavailable(MetricSymbols, "xml-depth-limit"), notApplicable(MetricCyclomatic, "XML cyclomatic complexity is not meaningful"), unavailable(MetricNesting, "xml-depth-limit"), notApplicable(MetricProceduralSize, "XML procedural regions are not meaningful"))
				return nil, []Warning{{Code: "parse-failure", Path: path, Detail: "XML nesting exceeds the bounded parser depth"}}
			}
			elements++
			attributes += int64(len(value.Attr))
			if int64(depth) > maximum {
				maximum = int64(depth)
			}
			pathParts = append(pathParts, value.Name.Local)
			if len(owners) < 256 {
				name := "/" + strings.Join(pathParts, "/")
				owners = append(owners, OwnerRow{ID: fmt.Sprintf("owner:xml:%s:%d", path, elements), Path: path, Language: row.Language, Kind: "element-path", DisplayName: name, Confidence: ConfidenceHigh, Metrics: []Metric{metric(MetricAttributes, AvailabilityExact, int64(len(value.Attr)), "attributes", "")}})
			}
		case xml.EndElement:
			if depth > 0 {
				depth--
			}
			if len(pathParts) > 0 {
				pathParts = pathParts[:len(pathParts)-1]
			}
		}
	}
	row.Metrics = append(row.Metrics, notApplicable(MetricStatements, "XML statements are not meaningful"), metric(MetricSymbols, AvailabilityStructural, int64(len(owners)), "element paths", ""), notApplicable(MetricCyclomatic, "XML cyclomatic complexity is not meaningful"), metric(MetricNesting, AvailabilityExact, maximum, "levels", "xml-depth:E"), notApplicable(MetricProceduralSize, "XML procedural regions are not meaningful"), metric(MetricElements, AvailabilityExact, elements, "elements", ""), metric(MetricAttributes, AvailabilityExact, attributes, "attributes", ""))
	return owners, nil
}
