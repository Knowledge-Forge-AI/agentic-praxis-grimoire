package footprint_test

import (
	"bytes"
	"errors"
	"fmt"
	"reflect"
	"testing"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/footprint"
)

func withRootMember(canonical []byte, member string) []byte {
	if len(canonical) < 2 || canonical[len(canonical)-2] != '}' || canonical[len(canonical)-1] != '\n' {
		panic("test fixture is not a root object with one trailing LF")
	}
	result := make([]byte, 0, len(canonical)+len(member)+1)
	result = append(result, canonical[:len(canonical)-2]...)
	result = append(result, ',')
	result = append(result, member...)
	result = append(result, '}', '\n')
	return result
}

func replaceFirst(data []byte, old, replacement string) []byte {
	index := bytes.Index(data, []byte(old))
	if index < 0 {
		panic(fmt.Sprintf("fixture did not contain %q", old))
	}
	result := make([]byte, 0, len(data)-len(old)+len(replacement))
	result = append(result, data[:index]...)
	result = append(result, replacement...)
	result = append(result, data[index+len(old):]...)
	return result
}

func replaceSourceReferencesWithNull(data []byte) []byte {
	start := bytes.Index(data, []byte(`"source_references":[`))
	if start < 0 {
		panic("fixture did not contain source references")
	}
	endOffset := bytes.Index(data[start:], []byte(`],"sensitivity"`))
	if endOffset < 0 {
		panic("fixture did not contain source reference terminator")
	}
	end := start + endOffset
	result := make([]byte, 0, len(data))
	result = append(result, data[:start]...)
	result = append(result, []byte(`"source_references":null`)...)
	result = append(result, data[end+1:]...)
	return result
}

func TestDecodeRecordRejectsUnknownSchemaFieldDuplicateTrailingAndInvalidUTF8(t *testing.T) {
	canonical, err := baseRecord().CanonicalJSON()
	requireNoError(t, err)

	cases := []struct {
		name   string
		input  func([]byte) []byte
		checks []error
	}{
		{
			name: "unknown schema",
			input: func(data []byte) []byte {
				return replaceFirst(data, footprint.FootprintSchemaV1, "apg.context-footprint/v99")
			},
			checks: []error{footprint.ErrInvalidRecord, footprint.ErrUnknownSchema},
		},
		{
			name: "unknown root field",
			input: func(data []byte) []byte {
				return withRootMember(data, `"future_field":true`)
			},
			checks: []error{footprint.ErrInvalidRecord, footprint.ErrUnknownField},
		},
		{
			name: "duplicate root field",
			input: func(data []byte) []byte {
				return withRootMember(data, `"schema_version":"apg.context-footprint/v1"`)
			},
			checks: []error{footprint.ErrInvalidRecord, footprint.ErrDuplicateField},
		},
		{
			name: "trailing data",
			input: func(data []byte) []byte {
				return append(append([]byte(nil), data...), []byte(`{"trailing":true}`)...)
			},
			checks: []error{footprint.ErrInvalidRecord, footprint.ErrTrailingData},
		},
		{
			name: "invalid utf8",
			input: func(data []byte) []byte {
				return append(append([]byte(nil), data...), 0xff)
			},
			checks: []error{footprint.ErrInvalidRecord, footprint.ErrInvalidUTF8},
		},
		{
			name: "noncanonical leading whitespace",
			input: func(data []byte) []byte {
				return append([]byte{' '}, data...)
			},
			checks: []error{footprint.ErrInvalidRecord, footprint.ErrNonCanonical},
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			_, err := footprint.DecodeRecord(tc.input(canonical))
			for _, check := range tc.checks {
				requireErrorIs(t, err, check)
			}
		})
	}
}

func TestDecodeRecordRejectsMalformedAndInvalidValues(t *testing.T) {
	canonical, err := baseRecord().CanonicalJSON()
	requireNoError(t, err)

	cases := []struct {
		name  string
		input []byte
		want  error
	}{
		{name: "empty", input: nil, want: footprint.ErrMalformedJSON},
		{name: "array root", input: []byte("[]\n"), want: footprint.ErrInvalidType},
		{name: "null root", input: []byte("null\n"), want: footprint.ErrInvalidType},
		{name: "missing component field", input: replaceFirst(canonical, `"components":[`, `"future":[`), want: footprint.ErrUnknownField},
		{name: "null source references", input: replaceSourceReferencesWithNull(canonical), want: footprint.ErrInvalidType},
		{name: "noninteger repetition", input: replaceFirst(canonical, `"repetitions":1`, `"repetitions":1.5`), want: footprint.ErrInvalidType},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			_, err := footprint.DecodeRecord(tc.input)
			requireErrorIs(t, err, tc.want)
		})
	}
	if _, err := footprint.DecodeRecord(append(append([]byte(nil), canonical...), []byte("\n")...)); !errors.Is(err, footprint.ErrNonCanonical) {
		t.Fatalf("additional trailing whitespace error = %v, want noncanonical", err)
	}
}

func TestDecodeUnavailableMetricRetainsAbsenceRatherThanZero(t *testing.T) {
	record := baseRecord()
	record.Components = append(record.Components, unavailableComponent(footprint.ComponentSupportMaterial, "tokens", footprint.UnitTokensClaude))
	canonical, err := record.CanonicalJSON()
	requireNoError(t, err)
	if bytes.Contains(canonical, []byte(`"name":"tokens","metric":{"availability":"unavailable","reason":"provider tokenizer is unavailable","unit":"tokens_claude","value":`)) {
		t.Fatal("unavailable metric unexpectedly serialized a value")
	}
	if !bytes.Contains(canonical, []byte(`"name":"tokens"`)) {
		t.Fatal("unavailable component is absent from canonical JSON")
	}
	decoded, err := footprint.DecodeRecord(canonical)
	requireNoError(t, err)
	var found bool
	for _, item := range decoded.Components {
		if item.Name != "tokens" {
			continue
		}
		found = true
		if item.Metric.Availability != footprint.Unavailable || item.Metric.Value != nil || item.Metric.Reason == "" {
			t.Fatalf("decoded unavailable metric = %#v", item.Metric)
		}
	}
	if !found {
		t.Fatal("decoded unavailable component is missing")
	}
}

func TestCanonicalJSONAndDecodeAliasesCoverComparisonProjectionRegistryAndMapping(t *testing.T) {
	control := baseRecord()
	treatment := baseRecord()
	treatment.Observation.Variant = "treatment"
	treatment.Components[0].Metric.Value = int64ptr(4)

	comparison, err := footprint.Compare(nil, footprint.CompareRequest{
		Control:       control,
		Treatment:     treatment,
		ComponentKind: footprint.ComponentSelectedBody,
		ComponentName: "body",
	})
	requireNoError(t, err)
	comparisonJSON, err := footprint.MarshalComparison(comparison)
	requireNoError(t, err)
	decodedComparison, err := footprint.DecodeComparison(comparisonJSON)
	requireNoError(t, err)
	if decodedComparison.Delta != 3 || decodedComparison.Unit != footprint.UnitBytes {
		t.Fatalf("decoded comparison = %#v", decodedComparison)
	}
	if footprint.FingerprintComparison(comparison) != decodedComparison.Fingerprint() {
		t.Fatal("comparison fingerprint changed across decode")
	}

	projection, err := footprint.Project(nil, footprint.ProjectRequest{Source: control, Fidelity: footprint.FidelityExact})
	requireNoError(t, err)
	projectionJSON, err := footprint.MarshalProjection(projection)
	requireNoError(t, err)
	decodedProjection, err := footprint.DecodeProjection(projectionJSON)
	requireNoError(t, err)
	if decodedProjection.CanonicalSourceDigest != footprint.FingerprintRecord(control) {
		t.Fatalf("projection source digest = %q", decodedProjection.CanonicalSourceDigest)
	}

	registry := footprint.DefaultComponentRegistry()
	registryJSON, err := footprint.MarshalComponentRegistry(registry)
	requireNoError(t, err)
	decodedRegistry, err := footprint.DecodeRegistry(registryJSON)
	requireNoError(t, err)
	if !reflect.DeepEqual(decodedRegistry, registry) {
		t.Fatalf("decoded registry differs: %#v vs %#v", decodedRegistry, registry)
	}
	mapping := footprint.DefaultControlMapping()
	mappingJSON, err := footprint.MarshalControlMapping(mapping)
	requireNoError(t, err)
	decodedMapping, err := footprint.DecodeCapacityControlMapping(mappingJSON)
	requireNoError(t, err)
	if !reflect.DeepEqual(decodedMapping, mapping) {
		t.Fatalf("decoded mapping differs: %#v vs %#v", decodedMapping, mapping)
	}
}

func TestAllDecodersApplyTheSameStrictInputBoundary(t *testing.T) {
	control := baseRecord()
	treatment := baseRecord()
	treatment.Observation.Variant = "treatment"
	treatment.Components[0].Metric.Value = int64ptr(4)
	comparison, err := footprint.Compare(nil, footprint.CompareRequest{
		Control:       control,
		Treatment:     treatment,
		ComponentKind: footprint.ComponentSelectedBody,
		ComponentName: "body",
	})
	requireNoError(t, err)
	projection, err := footprint.Project(nil, footprint.ProjectRequest{Source: control, Fidelity: footprint.FidelityExact})
	requireNoError(t, err)
	registry := footprint.DefaultComponentRegistry()
	mapping := footprint.DefaultControlMapping()

	cases := []struct {
		name   string
		value  []byte
		decode func([]byte) error
		schema string
		root   error
	}{
		{
			name:  "record",
			value: mustCanonical(t, control),
			decode: func(data []byte) error {
				_, err := footprint.DecodeRecord(data)
				return err
			},
			schema: footprint.FootprintSchemaV1,
			root:   footprint.ErrInvalidRecord,
		},
		{
			name:  "comparison",
			value: mustCanonical(t, comparison),
			decode: func(data []byte) error {
				_, err := footprint.DecodeComparison(data)
				return err
			},
			schema: footprint.ComparisonSchemaV1,
			root:   footprint.ErrInvalidComparison,
		},
		{
			name:  "projection",
			value: mustCanonical(t, projection),
			decode: func(data []byte) error {
				_, err := footprint.DecodeProjection(data)
				return err
			},
			schema: footprint.ProjectionSchemaV1,
			root:   footprint.ErrInvalidProjection,
		},
		{
			name:  "registry",
			value: mustCanonical(t, registry),
			decode: func(data []byte) error {
				_, err := footprint.DecodeComponentRegistry(data)
				return err
			},
			schema: footprint.ComponentRegistrySchemaV1,
			root:   footprint.ErrInvalidRegistry,
		},
		{
			name:  "mapping",
			value: mustCanonical(t, mapping),
			decode: func(data []byte) error {
				_, err := footprint.DecodeControlMapping(data)
				return err
			},
			schema: footprint.ControlMappingSchemaV1,
			root:   footprint.ErrInvalidControlMapping,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			strictCases := []struct {
				name   string
				input  []byte
				checks []error
			}{
				{
					name:   "unknown schema",
					input:  replaceFirst(tc.value, tc.schema, tc.schema+"-future"),
					checks: []error{tc.root, footprint.ErrUnknownSchema},
				},
				{
					name:   "unknown field",
					input:  withRootMember(tc.value, `"future_field":true`),
					checks: []error{tc.root, footprint.ErrUnknownField},
				},
				{
					name:   "duplicate field",
					input:  withRootMember(tc.value, `"schema_version":"`+tc.schema+`"`),
					checks: []error{tc.root, footprint.ErrDuplicateField},
				},
				{
					name:   "trailing data",
					input:  append(append([]byte(nil), tc.value...), []byte(`{"trailing":true}`)...),
					checks: []error{tc.root, footprint.ErrTrailingData},
				},
				{
					name:   "invalid utf8",
					input:  append(append([]byte(nil), tc.value...), 0xff),
					checks: []error{tc.root, footprint.ErrInvalidUTF8},
				},
			}
			for _, strictCase := range strictCases {
				t.Run(strictCase.name, func(t *testing.T) {
					err := tc.decode(strictCase.input)
					for _, check := range strictCase.checks {
						requireErrorIs(t, err, check)
					}
				})
			}
		})
	}
}
