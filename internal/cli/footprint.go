package cli

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"unicode/utf8"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/footprint"
)

const footprintUsage = `Usage: apgr footprint <measure|compare|project> [options]

Commands:
  measure --input FILE|--stdin
      Convert a strict measurement request into canonical footprint JSON.
  compare --control FILE --treatment FILE
      Compare two canonical footprint records.
  project --source FILE|--stdin --fidelity FIDELITY [--omit FIELD ...]
      Create a source-bound canonical projection.

Measure options:
  --input FILE       absolute, clean owner-only 0600 JSON request
  --stdin            read one JSON request from standard input

Compare options:
  --control FILE     absolute, clean owner-only 0600 canonical record
  --treatment FILE   absolute, clean owner-only 0600 canonical record
  --component-kind K select a component kind (alias: --kind)
  --component-name N select a component name (alias: --name)
  --control-identity ID

Project options:
  --source FILE      absolute, clean owner-only 0600 canonical record
  --stdin            read one canonical record from standard input
  --fidelity F       exact, lossless_structural, or summarized_lossy
  --omit FIELD       omit one permitted component or field (repeatable)
  --sensitivity S    public, internal, confidential, or restricted
  --retention R      ephemeral, task_scoped, retained, or immutable

  -h, --help         show this help
`

// measureDocument is the CLI request envelope. The resulting record is
// always encoded by footprint.CanonicalJSON; this envelope is intentionally
// not a second output schema. Canonical record, comparison, and projection
// inputs are decoded by the footprint package itself.
type measureDocument struct {
	SchemaVersion    string                      `json:"schema_version"`
	Observation      footprint.Observation       `json:"observation"`
	Components       []measureComponentDocument  `json:"components"`
	SourceReferences []footprint.SourceReference `json:"source_references"`
	Sensitivity      footprint.Sensitivity       `json:"sensitivity"`
	Retention        footprint.Retention         `json:"retention"`
}

type measureComponentDocument struct {
	ControlIdentity string                  `json:"control_identity"`
	Kind            footprint.ComponentKind `json:"kind"`
	Name            string                  `json:"name"`
	Unit            footprint.Unit          `json:"unit"`
	Data            *string                 `json:"data,omitempty"`
	Text            *string                 `json:"text,omitempty"`
	Metric          *footprint.Metric       `json:"metric,omitempty"`
}

type footprintOptions struct {
	action          string
	inputPath       string
	stdin           bool
	controlPath     string
	treatmentPath   string
	sourcePath      string
	componentKind   footprint.ComponentKind
	componentName   string
	controlIdentity string
	fidelity        footprint.Fidelity
	sensitivity     footprint.Sensitivity
	retention       footprint.Retention
	omitted         []string
}

func runFootprint(ctx context.Context, arguments []string, stdin io.Reader, stdout io.Writer) error {
	if len(arguments) == 0 {
		return usageError{"footprint requires measure, compare, or project"}
	}
	if arguments[0] == "-h" || arguments[0] == "--help" {
		if len(arguments) != 1 {
			return usageError{"footprint help takes no additional arguments"}
		}
		_, err := io.WriteString(stdout, footprintUsage)
		return err
	}
	if len(arguments) == 2 && (arguments[1] == "-h" || arguments[1] == "--help") {
		_, err := io.WriteString(stdout, footprintUsage)
		return err
	}
	options, err := parseFootprintOptions(arguments)
	if err != nil {
		return err
	}
	switch options.action {
	case "measure":
		return runFootprintMeasure(ctx, options, stdin, stdout)
	case "compare":
		return runFootprintCompare(ctx, options, stdout)
	case "project":
		return runFootprintProject(ctx, options, stdin, stdout)
	default:
		return usageError{"unknown footprint command"}
	}
}

func parseFootprintOptions(arguments []string) (footprintOptions, error) {
	if len(arguments) == 0 {
		return footprintOptions{}, usageError{"footprint requires a command"}
	}
	result := footprintOptions{action: arguments[0]}
	if result.action != "measure" && result.action != "compare" && result.action != "project" {
		return footprintOptions{}, usageError{"unknown footprint command"}
	}
	seen := map[string]bool{}
	for position := 1; position < len(arguments); position++ {
		argument := arguments[position]
		if argument == "-h" || argument == "--help" {
			return footprintOptions{}, usageError{"footprint help takes no additional arguments"}
		}
		if argument == "--stdin" {
			if seen[argument] {
				return footprintOptions{}, usageError{"--stdin may be specified only once"}
			}
			seen[argument], result.stdin = true, true
			continue
		}
		if argument == "--omit" {
			if position+1 >= len(arguments) {
				return footprintOptions{}, usageError{"--omit requires a value"}
			}
			result.omitted = append(result.omitted, arguments[position+1])
			position++
			continue
		}
		if position+1 >= len(arguments) {
			return footprintOptions{}, usageError{argument + " requires a value"}
		}
		value := arguments[position+1]
		position++
		switch argument {
		case "--input", "--request":
			if result.action != "measure" && argument == "--request" {
				return footprintOptions{}, usageError{"--request is supported only by footprint measure"}
			}
			if result.action == "project" {
				if seen["--input"] || seen["--source"] || result.stdin {
					return footprintOptions{}, usageError{"one footprint input source is required"}
				}
				seen[argument] = true
				result.sourcePath = value
				continue
			}
			if seen["--input"] || seen["--request"] || result.stdin {
				return footprintOptions{}, usageError{"one footprint input source is required"}
			}
			seen[argument] = true
			result.inputPath = value
		case "--control":
			if result.action != "compare" {
				return footprintOptions{}, usageError{"--control is supported only by footprint compare"}
			}
			if seen[argument] {
				return footprintOptions{}, usageError{"--control may be specified only once"}
			}
			seen[argument], result.controlPath = true, value
		case "--treatment":
			if result.action != "compare" {
				return footprintOptions{}, usageError{"--treatment is supported only by footprint compare"}
			}
			if seen[argument] {
				return footprintOptions{}, usageError{"--treatment may be specified only once"}
			}
			seen[argument], result.treatmentPath = true, value
		case "--source":
			if result.action != "project" {
				return footprintOptions{}, usageError{"--source is supported only by footprint project"}
			}
			if seen["--source"] || seen["--input"] || result.stdin {
				return footprintOptions{}, usageError{"one footprint input source is required"}
			}
			seen[argument], result.sourcePath = true, value
		case "--component-kind", "--kind":
			if result.action != "compare" {
				return footprintOptions{}, usageError{"component selectors are supported only by footprint compare"}
			}
			if seen["--component-kind"] || seen["--kind"] {
				return footprintOptions{}, usageError{"component kind may be specified only once"}
			}
			seen[argument] = true
			result.componentKind = footprint.ComponentKind(value)
		case "--component-name", "--name":
			if result.action != "compare" {
				return footprintOptions{}, usageError{"component selectors are supported only by footprint compare"}
			}
			if seen["--component-name"] || seen["--name"] {
				return footprintOptions{}, usageError{"component name may be specified only once"}
			}
			seen[argument] = true
			result.componentName = value
		case "--control-identity":
			if result.action != "compare" {
				return footprintOptions{}, usageError{"--control-identity is supported only by footprint compare"}
			}
			if seen[argument] {
				return footprintOptions{}, usageError{"--control-identity may be specified only once"}
			}
			seen[argument], result.controlIdentity = true, value
		case "--fidelity":
			if result.action != "project" {
				return footprintOptions{}, usageError{"--fidelity is supported only by footprint project"}
			}
			if seen[argument] {
				return footprintOptions{}, usageError{"--fidelity may be specified only once"}
			}
			seen[argument], result.fidelity = true, footprint.Fidelity(value)
		case "--sensitivity":
			if result.action != "project" {
				return footprintOptions{}, usageError{"--sensitivity is supported only by footprint project"}
			}
			if seen[argument] {
				return footprintOptions{}, usageError{"--sensitivity may be specified only once"}
			}
			seen[argument], result.sensitivity = true, footprint.Sensitivity(value)
		case "--retention":
			if result.action != "project" {
				return footprintOptions{}, usageError{"--retention is supported only by footprint project"}
			}
			if seen[argument] {
				return footprintOptions{}, usageError{"--retention may be specified only once"}
			}
			seen[argument], result.retention = true, footprint.Retention(value)
		default:
			return footprintOptions{}, usageError{"unknown footprint option: " + argument}
		}
	}

	switch result.action {
	case "measure":
		if result.inputPath == "" && !result.stdin {
			return footprintOptions{}, usageError{"measure requires exactly one of --input FILE or --stdin"}
		}
		if result.inputPath != "" && result.stdin {
			return footprintOptions{}, usageError{"measure requires exactly one of --input FILE or --stdin"}
		}
		if len(result.omitted) != 0 {
			return footprintOptions{}, usageError{"--omit is supported only by footprint project"}
		}
	case "compare":
		if result.controlPath == "" || result.treatmentPath == "" || result.stdin || result.inputPath != "" || result.sourcePath != "" {
			return footprintOptions{}, usageError{"compare requires --control FILE and --treatment FILE"}
		}
		if len(result.omitted) != 0 {
			return footprintOptions{}, usageError{"--omit is supported only by footprint project"}
		}
	case "project":
		if result.sourcePath == "" && !result.stdin {
			return footprintOptions{}, usageError{"project requires exactly one of --source FILE or --stdin"}
		}
		if result.sourcePath != "" && result.stdin {
			return footprintOptions{}, usageError{"project requires exactly one of --source FILE or --stdin"}
		}
		if result.fidelity == "" {
			result.fidelity = footprint.FidelityExact
		}
	}
	return result, nil
}

func runFootprintMeasure(ctx context.Context, options footprintOptions, stdin io.Reader, stdout io.Writer) error {
	content, err := readFootprintInput(options.inputPath, options.stdin, stdin)
	if err != nil {
		return err
	}
	request, err := decodeMeasureDocument(content)
	if err != nil {
		return err
	}
	record, err := footprint.Measure(ctx, request)
	if err != nil {
		return err
	}
	canonical, err := record.CanonicalJSON()
	if err != nil {
		return err
	}
	_, err = stdout.Write(canonical)
	return err
}

func runFootprintCompare(ctx context.Context, options footprintOptions, stdout io.Writer) error {
	controlContent, err := readFootprintInput(options.controlPath, false, nil)
	if err != nil {
		return err
	}
	treatmentContent, err := readFootprintInput(options.treatmentPath, false, nil)
	if err != nil {
		return err
	}
	control, err := footprint.DecodeRecord(controlContent)
	if err != nil {
		return err
	}
	treatment, err := footprint.DecodeRecord(treatmentContent)
	if err != nil {
		return err
	}
	request := footprint.CompareRequest{
		Control:       control,
		Treatment:     treatment,
		ComponentKind: options.componentKind,
		ComponentName: options.componentName,
		Component: footprint.ComponentSelector{
			ControlIdentity: options.controlIdentity,
			Kind:            options.componentKind,
			Name:            options.componentName,
		},
	}
	comparison, err := footprint.Compare(ctx, request)
	if err != nil {
		return err
	}
	canonical, err := comparison.CanonicalJSON()
	if err != nil {
		return err
	}
	_, err = stdout.Write(canonical)
	return err
}

func runFootprintProject(ctx context.Context, options footprintOptions, stdin io.Reader, stdout io.Writer) error {
	content, err := readFootprintInput(options.sourcePath, options.stdin, stdin)
	if err != nil {
		return err
	}
	source, err := footprint.DecodeRecord(content)
	if err != nil {
		return err
	}
	projection, err := footprint.Project(ctx, footprint.ProjectRequest{
		Source:        source,
		Fidelity:      options.fidelity,
		OmittedFields: append([]string(nil), options.omitted...),
		Sensitivity:   options.sensitivity,
		Retention:     options.retention,
	})
	if err != nil {
		return err
	}
	canonical, err := projection.CanonicalJSON()
	if err != nil {
		return err
	}
	_, err = stdout.Write(canonical)
	return err
}

func readFootprintInput(path string, fromStdin bool, stdin io.Reader) ([]byte, error) {
	if fromStdin {
		if stdin == nil {
			return nil, errors.New("footprint standard input is unavailable")
		}
		content, err := io.ReadAll(io.LimitReader(stdin, maxSkillDocumentBytes+1))
		if err != nil {
			return nil, errors.New("footprint input could not be read")
		}
		if len(content) == 0 || len(content) > maxSkillDocumentBytes {
			return nil, errors.New("footprint input is empty or oversized")
		}
		return content, nil
	}
	return readPrivateDocument(path)
}

func decodeMeasureDocument(content []byte) (footprint.MeasureRequest, error) {
	var document measureDocument
	if err := decodeStrictFootprintJSON(content, &document); err != nil {
		return footprint.MeasureRequest{}, fmt.Errorf("invalid footprint measurement request: %w", err)
	}
	if document.Components == nil {
		return footprint.MeasureRequest{}, fmt.Errorf("invalid footprint measurement request: %w", footprint.ErrMissingField)
	}
	components := make([]footprint.ComponentInput, 0, len(document.Components))
	for _, input := range document.Components {
		component := footprint.ComponentInput{
			Kind:            input.Kind,
			Name:            input.Name,
			ControlIdentity: input.ControlIdentity,
			Unit:            input.Unit,
		}
		if input.Data != nil {
			decoded, err := base64.StdEncoding.DecodeString(*input.Data)
			if err != nil {
				return footprint.MeasureRequest{}, fmt.Errorf("invalid footprint measurement request: data is not base64: %w", err)
			}
			component.Data = decoded
		}
		if input.Text != nil {
			component.Text = *input.Text
		}
		if input.Metric != nil {
			component.Metric = *input.Metric
		}
		if input.Metric != nil && (input.Data != nil || input.Text != nil) {
			return footprint.MeasureRequest{}, fmt.Errorf("invalid footprint measurement request: metric cannot be combined with text or data")
		}
		if input.Data != nil && input.Text != nil {
			return footprint.MeasureRequest{}, fmt.Errorf("invalid footprint measurement request: text and data cannot both be supplied")
		}
		if input.Data == nil && input.Text == nil && input.Metric == nil && (input.Unit == footprint.UnitBytes || input.Unit == footprint.UnitCharacters) {
			return footprint.MeasureRequest{}, fmt.Errorf("invalid footprint measurement request: byte or character component has no input")
		}
		components = append(components, component)
	}
	if document.SourceReferences == nil {
		document.SourceReferences = []footprint.SourceReference{}
	}
	return footprint.MeasureRequest{
		SchemaVersion:    document.SchemaVersion,
		Observation:      document.Observation,
		Components:       components,
		SourceReferences: document.SourceReferences,
		Sensitivity:      document.Sensitivity,
		Retention:        document.Retention,
	}, nil
}

func decodeStrictFootprintJSON(content []byte, destination any) error {
	if !utf8.Valid(content) {
		return footprint.ErrInvalidUTF8
	}
	decoderWalk := json.NewDecoder(bytes.NewReader(content))
	decoderWalk.UseNumber()
	if err := walkFootprintJSON(decoderWalk); err != nil {
		return err
	}
	if _, err := decoderWalk.Token(); err != io.EOF {
		if err == nil {
			return footprint.ErrTrailingData
		}
		return fmt.Errorf("%w: %v", footprint.ErrTrailingData, err)
	}
	decoder := json.NewDecoder(bytes.NewReader(content))
	decoder.DisallowUnknownFields()
	decoder.UseNumber()
	if err := decoder.Decode(destination); err != nil {
		return fmt.Errorf("%w: %v", footprint.ErrMalformedJSON, err)
	}
	var extra any
	if err := decoder.Decode(&extra); err != io.EOF {
		if err == nil {
			return footprint.ErrTrailingData
		}
		return fmt.Errorf("%w: %v", footprint.ErrTrailingData, err)
	}
	return nil
}

func walkFootprintJSON(decoder *json.Decoder) error {
	token, err := decoder.Token()
	if err != nil {
		return fmt.Errorf("%w: %v", footprint.ErrMalformedJSON, err)
	}
	if token == nil {
		return fmt.Errorf("%w: explicit null is not allowed", footprint.ErrInvalidType)
	}
	delimiter, ok := token.(json.Delim)
	if !ok {
		return nil
	}
	switch delimiter {
	case '{':
		seen := map[string]struct{}{}
		for decoder.More() {
			keyToken, err := decoder.Token()
			if err != nil {
				return fmt.Errorf("%w: %v", footprint.ErrMalformedJSON, err)
			}
			key, ok := keyToken.(string)
			if !ok {
				return fmt.Errorf("%w: object key is not a string", footprint.ErrMalformedJSON)
			}
			if _, exists := seen[key]; exists {
				return fmt.Errorf("%w: %q", footprint.ErrDuplicateField, key)
			}
			seen[key] = struct{}{}
			if err := walkFootprintJSON(decoder); err != nil {
				return err
			}
		}
		if end, err := decoder.Token(); err != nil || end != json.Delim('}') {
			return fmt.Errorf("%w: unterminated object", footprint.ErrMalformedJSON)
		}
	case '[':
		for decoder.More() {
			if err := walkFootprintJSON(decoder); err != nil {
				return err
			}
		}
		if end, err := decoder.Token(); err != nil || end != json.Delim(']') {
			return fmt.Errorf("%w: unterminated array", footprint.ErrMalformedJSON)
		}
	default:
		return fmt.Errorf("%w: unexpected delimiter", footprint.ErrMalformedJSON)
	}
	return nil
}
