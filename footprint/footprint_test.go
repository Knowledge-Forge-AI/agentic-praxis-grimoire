package footprint_test

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"os"
	"reflect"
	"strings"
	"testing"
	"time"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/footprint"
)

func int64ptr(value int64) *int64 { return &value }

func observation(variant string) footprint.Observation {
	return footprint.Observation{
		Basis:        footprint.ObservationBasisDirectMeasurement,
		Availability: footprint.Available,
		Exclusions:   []string{"z-exclusion", "a-exclusion"},
		Harness:      "go-test",
		Method:       "direct-bytes",
		Provider:     "apgr",
		Quality:      footprint.QualityVerified,
		Repetitions:  1,
		StudyDesign:  footprint.StudyDesignSingleRun,
		Tokenizer:    "none",
		Variant:      variant,
		Workload:     "multi-component",
	}
}

func component(kind footprint.ComponentKind, name string, value int64) footprint.Component {
	return footprint.Component{
		Kind:            kind,
		Name:            name,
		ControlIdentity: controlFor(kind),
		Metric: footprint.Metric{
			Availability: footprint.Available,
			Unit:         footprint.UnitBytes,
			Value:        int64ptr(value),
		},
	}
}

func unavailableComponent(kind footprint.ComponentKind, name string, unit footprint.Unit) footprint.Component {
	return footprint.Component{
		Kind:            kind,
		Name:            name,
		ControlIdentity: controlFor(kind),
		Metric: footprint.Metric{
			Availability: footprint.Unavailable,
			Reason:       "provider tokenizer is unavailable",
			Unit:         unit,
		},
	}
}

func controlFor(kind footprint.ComponentKind) string {
	switch kind {
	case footprint.ComponentCanonicalDescription, footprint.ComponentDescription:
		return footprint.ControlCorpusIntegrity
	case footprint.ComponentSelectedDescription:
		return footprint.ControlSelectedDiscovery
	case footprint.ComponentSelectedBody, footprint.ComponentBody:
		return footprint.ControlSelectedBody
	case footprint.ComponentSupportMaterial, footprint.ComponentSupport:
		return footprint.ControlSupportMaterial
	case footprint.ComponentMaterializedBundle, footprint.ComponentBundle:
		return footprint.ControlMaterializedBundle
	case footprint.ComponentPromptOverhead:
		return footprint.ControlPromptOverhead
	default:
		return footprint.ControlConsequence
	}
}

func baseRecord() footprint.Record {
	return footprint.Record{
		SchemaVersion: footprint.FootprintSchemaV1,
		Observation:   observation("control"),
		Components: []footprint.Component{
			component(footprint.ComponentSelectedBody, "body", 1),
			component(footprint.ComponentSelectedDescription, "description", 0),
		},
		SourceReferences: []footprint.SourceReference{
			{Digest: "sha256:z", MediaType: "text/plain", Size: 2, URI: "https://example.invalid/z"},
			{Digest: "sha256:a", MediaType: "text/plain", Size: 1, URI: "https://example.invalid/a"},
		},
		Sensitivity: footprint.SensitivityInternal,
		Retention:   footprint.RetentionRetained,
	}
}

func requireErrorIs(t *testing.T, err error, target error) {
	t.Helper()
	if err == nil {
		t.Fatalf("expected %v, got nil", target)
	}
	if !errors.Is(err, target) {
		t.Fatalf("error %q does not wrap %v", err, target)
	}
}

func requireNoError(t *testing.T, err error) {
	t.Helper()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestMeasureSeparatesByteCharacterAndUnavailableMetrics(t *testing.T) {
	request := footprint.MeasureRequest{
		SchemaVersion: footprint.FootprintSchemaV1,
		Observation:   observation("measured"),
		Components: []footprint.ComponentInput{
			{Kind: footprint.ComponentSelectedBody, Name: "body", Unit: footprint.UnitBytes, Text: "hé"},
			{Kind: footprint.ComponentSelectedDescription, Name: "description", Unit: footprint.UnitCharacters, Text: "aé🙂"},
			{Kind: footprint.ComponentSupportMaterial, Name: "support", Unit: footprint.UnitTokensTiktokenCL100k, Text: "not tokenized"},
		},
		Sensitivity: footprint.SensitivityPublic,
		Retention:   footprint.RetentionTaskScoped,
	}

	measured, err := footprint.Measure(context.Background(), request)
	requireNoError(t, err)
	if len(measured.Components) != 3 {
		t.Fatalf("got %d components, want 3", len(measured.Components))
	}
	if measured.Components[0].Kind != footprint.ComponentSelectedBody {
		t.Fatalf("components were not normalized into canonical order: %#v", measured.Components)
	}
	byName := make(map[string]footprint.Component)
	for _, item := range measured.Components {
		byName[item.Name] = item
	}
	if got := *byName["body"].Metric.Value; got != 3 {
		t.Fatalf("byte count = %d, want 3", got)
	}
	if got := *byName["description"].Metric.Value; got != 3 {
		t.Fatalf("character count = %d, want 3", got)
	}
	if got := byName["support"].Metric; got.Availability != footprint.Unavailable || got.Value != nil || got.Reason == "" {
		t.Fatalf("token metric = %#v, want explicit unavailable metric", got)
	}
	if measured.Observation.Exclusions[0] != "a-exclusion" {
		t.Fatalf("exclusions were not normalized: %#v", measured.Observation.Exclusions)
	}
}

func TestMeasureAllowsAvailableZeroAndExplicitUnavailable(t *testing.T) {
	zero := int64(0)
	request := footprint.MeasureRequest{
		SchemaVersion: footprint.FootprintSchemaV1,
		Observation:   observation("zero"),
		Components: []footprint.ComponentInput{
			{
				Kind: footprint.ComponentSelectedBody,
				Name: "zero",
				Unit: footprint.UnitBytes,
				Metric: footprint.Metric{
					Availability: footprint.Available,
					Unit:         footprint.UnitBytes,
					Value:        &zero,
				},
			},
			{
				Kind: footprint.ComponentSupportMaterial,
				Name: "missing-tokenizer",
				Metric: footprint.Metric{
					Availability: footprint.Unavailable,
					Reason:       "not observed",
					Unit:         footprint.UnitTokensGemini,
				},
			},
		},
		Sensitivity: footprint.SensitivityPublic,
		Retention:   footprint.RetentionEphemeral,
	}

	result, err := footprint.Measure(context.Background(), request)
	requireNoError(t, err)
	if result.Components[0].Metric.Availability != footprint.Unavailable && result.Components[1].Metric.Availability != footprint.Unavailable {
		t.Fatalf("expected one unavailable metric: %#v", result.Components)
	}
	for _, item := range result.Components {
		if item.Name == "zero" {
			if item.Metric.Value == nil || *item.Metric.Value != 0 {
				t.Fatalf("zero metric was not retained: %#v", item.Metric)
			}
		}
		if item.Name == "missing-tokenizer" && item.Metric.Value != nil {
			t.Fatalf("unavailable metric contains a value: %#v", item.Metric)
		}
	}
}

func TestMeasureRejectsInvalidInputs(t *testing.T) {
	cases := []struct {
		name   string
		want   error
		mutate func(*footprint.MeasureRequest)
	}{
		{
			name: "unknown schema",
			want: footprint.ErrUnknownSchema,
			mutate: func(request *footprint.MeasureRequest) {
				request.SchemaVersion = "apg.context-footprint/v99"
			},
		},
		{
			name: "empty components",
			want: footprint.ErrMissingField,
			mutate: func(request *footprint.MeasureRequest) {
				request.Components = nil
			},
		},
		{
			name: "unknown component",
			want: footprint.ErrUnknownVocabulary,
			mutate: func(request *footprint.MeasureRequest) {
				request.Components[0].Kind = footprint.ComponentKind("future_component")
			},
		},
		{
			name: "unknown unit",
			want: footprint.ErrUnknownVocabulary,
			mutate: func(request *footprint.MeasureRequest) {
				request.Components[0].Unit = footprint.Unit("tokens_future")
			},
		},
		{
			name: "unit mismatch",
			want: footprint.ErrUnitMismatch,
			mutate: func(request *footprint.MeasureRequest) {
				request.Components[0].Unit = footprint.UnitBytes
				request.Components[0].Metric = footprint.Metric{Availability: footprint.Available, Unit: footprint.UnitCharacters, Value: int64ptr(1)}
			},
		},
		{
			name: "invalid utf8",
			want: footprint.ErrInvalidUTF8,
			mutate: func(request *footprint.MeasureRequest) {
				request.Components[0].Unit = footprint.UnitCharacters
				request.Components[0].Data = []byte{0xff}
			},
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			request := footprint.MeasureRequest{
				SchemaVersion: footprint.FootprintSchemaV1,
				Observation:   observation("invalid"),
				Components: []footprint.ComponentInput{
					{Kind: footprint.ComponentSelectedBody, Name: "body", Unit: footprint.UnitBytes, Text: "x"},
				},
				Sensitivity: footprint.SensitivityPublic,
				Retention:   footprint.RetentionEphemeral,
			}
			tc.mutate(&request)
			_, err := footprint.Measure(context.Background(), request)
			requireErrorIs(t, err, tc.want)
		})
	}
}

func TestMeasureHonorsCancellationAndDeadline(t *testing.T) {
	request := footprint.MeasureRequest{
		SchemaVersion: footprint.FootprintSchemaV1,
		Observation:   observation("cancelled"),
		Components: []footprint.ComponentInput{
			{Kind: footprint.ComponentSelectedBody, Name: "body", Unit: footprint.UnitBytes, Text: "x"},
		},
		Sensitivity: footprint.SensitivityPublic,
		Retention:   footprint.RetentionEphemeral,
	}
	cancelled, cancel := context.WithCancel(context.Background())
	cancel()
	_, err := footprint.Measure(cancelled, request)
	requireErrorIs(t, err, footprint.ErrContextCancelled)
	requireErrorIs(t, err, context.Canceled)

	deadline, cancel := context.WithDeadline(context.Background(), time.Unix(0, 0))
	defer cancel()
	_, err = footprint.Measure(deadline, request)
	requireErrorIs(t, err, context.DeadlineExceeded)
}

func TestCanonicalRecordRoundTripAndDeterministicFingerprint(t *testing.T) {
	record := baseRecord()
	canonical, err := record.CanonicalJSON()
	requireNoError(t, err)
	fixture, err := os.ReadFile("testdata/record.golden.json")
	requireNoError(t, err)
	if !bytes.Equal(canonical, fixture) {
		t.Fatalf("canonical record differs from fixture:\n got: %s\nwant: %s", canonical, fixture)
	}
	if len(canonical) < 2 || canonical[len(canonical)-1] != '\n' || canonical[len(canonical)-2] == '\n' {
		t.Fatalf("canonical encoding must end in exactly one LF: %q", canonical[len(canonical)-minInt(32, len(canonical)):])
	}
	decoded, err := footprint.DecodeRecord(canonical)
	requireNoError(t, err)
	decodedCanonical, err := footprint.CanonicalJSON(decoded)
	requireNoError(t, err)
	if !bytes.Equal(decodedCanonical, canonical) {
		t.Fatal("decode and re-encode changed canonical bytes")
	}
	normalized, err := footprint.DecodeRecord(canonical)
	requireNoError(t, err)
	if !reflect.DeepEqual(decoded, normalized) {
		t.Fatalf("decoded record = %#v, want normalized %#v", decoded, normalized)
	}
	if alias, err := footprint.DecodeFootprint(canonical); err != nil || !reflect.DeepEqual(alias, decoded) {
		t.Fatalf("DecodeFootprint mismatch: %#v, %v", alias, err)
	}
	if alias, err := footprint.DecodeMeasurement(canonical); err != nil || !reflect.DeepEqual(alias, decoded) {
		t.Fatalf("DecodeMeasurement mismatch: %#v, %v", alias, err)
	}

	digest := footprint.FingerprintRecord(record)
	if !strings.HasPrefix(digest, "fp-sha256:") || len(digest) != len("fp-sha256:")+64 {
		t.Fatalf("record fingerprint = %q", digest)
	}
	hash := sha256.New()
	_, _ = hash.Write([]byte(footprint.FootprintSchemaV1))
	_, _ = hash.Write([]byte{0})
	_, _ = hash.Write(canonical)
	expected := "fp-sha256:" + hex.EncodeToString(hash.Sum(nil))
	if digest != expected {
		t.Fatalf("domain digest = %q, want %q", digest, expected)
	}
	if digest != record.Fingerprint() || digest != footprint.Fingerprint(record) || digest != footprint.FingerprintFootprint(record) {
		t.Fatal("record fingerprint aliases disagree")
	}
	withError, err := footprint.FingerprintWithError(record)
	requireNoError(t, err)
	if withError != digest {
		t.Fatalf("FingerprintWithError = %q, want %q", withError, digest)
	}
}

func TestCanonicalRecordDoesNotMutateInputOrder(t *testing.T) {
	record := baseRecord()
	originalComponents := append([]footprint.Component(nil), record.Components...)
	originalExclusions := append([]string(nil), record.Observation.Exclusions...)
	originalReferences := append([]footprint.SourceReference(nil), record.SourceReferences...)
	_, err := record.CanonicalJSON()
	requireNoError(t, err)
	if !reflect.DeepEqual(record.Components, originalComponents) || !reflect.DeepEqual(record.Observation.Exclusions, originalExclusions) || !reflect.DeepEqual(record.SourceReferences, originalReferences) {
		t.Fatal("canonicalization mutated the caller's record")
	}
}

func TestCanonicalJSONRejectsUnsupportedValues(t *testing.T) {
	if _, err := footprint.CanonicalJSON(struct{ Value string }{Value: "unsupported"}); !errors.Is(err, footprint.ErrInvalidType) {
		t.Fatalf("unsupported canonical value error = %v", err)
	}
	if _, err := footprint.CanonicalJSON((*footprint.Record)(nil)); !errors.Is(err, footprint.ErrInvalidType) {
		t.Fatalf("nil record error = %v", err)
	}
	if got := footprint.Fingerprint(struct{ Value string }{Value: "unsupported"}); got != "" {
		t.Fatalf("invalid fingerprint = %q, want empty", got)
	}
}

func TestGoldenFixturesForAllSchemaIdentities(t *testing.T) {
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

	projection, err := footprint.Project(nil, footprint.ProjectRequest{
		Source:   control,
		Fidelity: footprint.FidelityExact,
	})
	requireNoError(t, err)

	registry := footprint.DefaultComponentRegistry()
	mapping := footprint.DefaultControlMapping()

	cases := []struct {
		filename string
		value    any
	}{
		{"testdata/record.golden.json", control},
		{"testdata/comparison.golden.json", comparison},
		{"testdata/projection.golden.json", projection},
		{"testdata/component_registry.golden.json", registry},
		{"testdata/control_mapping.golden.json", mapping},
	}

	for _, tc := range cases {
		t.Run(tc.filename, func(t *testing.T) {
			canonical, err := footprint.CanonicalJSON(tc.value)
			requireNoError(t, err)
			if os.Getenv("UPDATE_GOLDEN") == "1" {
				requireNoError(t, os.WriteFile(tc.filename, canonical, 0o644))
			}
			fixture, err := os.ReadFile(tc.filename)
			requireNoError(t, err)
			if !bytes.Equal(canonical, fixture) {
				t.Fatalf("canonical %s differs from fixture:\n got: %s\nwant: %s", tc.filename, canonical, fixture)
			}
		})
	}
}

func minInt(left, right int) int {
	if left < right {
		return left
	}
	return right
}
