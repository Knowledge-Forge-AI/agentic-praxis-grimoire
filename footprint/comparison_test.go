package footprint_test

import (
	"context"
	"errors"
	"math"
	"reflect"
	"testing"
	"time"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/footprint"
)

func comparableRecord(variant string, bodyValue int64, bodyUnit footprint.Unit) footprint.Record {
	record := baseRecord()
	record.Observation.Variant = variant
	record.Components = []footprint.Component{component(footprint.ComponentSelectedBody, "body", bodyValue)}
	record.Components[0].Metric.Unit = bodyUnit
	return record
}

func TestCompareSelectsMatchingComponentAndCalculatesTreatmentDelta(t *testing.T) {
	control := comparableRecord("control", 4, footprint.UnitBytes)
	treatment := comparableRecord("treatment", 11, footprint.UnitBytes)

	comparison, err := footprint.Compare(context.Background(), footprint.CompareRequest{
		Control:       control,
		Treatment:     treatment,
		ComponentKind: footprint.ComponentSelectedBody,
		ComponentName: "body",
	})
	requireNoError(t, err)
	if comparison.SchemaVersion != footprint.ComparisonSchemaV1 {
		t.Fatalf("schema = %q", comparison.SchemaVersion)
	}
	if comparison.Delta != 7 {
		t.Fatalf("delta = %d, want 7", comparison.Delta)
	}
	if comparison.Component.ControlIdentity != footprint.ControlSelectedBody || comparison.Component.Kind != footprint.ComponentSelectedBody || comparison.Component.Name != "body" {
		t.Fatalf("component selector = %#v", comparison.Component)
	}
	if comparison.Control.RecordDigest != footprint.FingerprintRecord(control) || comparison.Treatment.RecordDigest != footprint.FingerprintRecord(treatment) {
		t.Fatalf("comparison record digests do not bind source records: %#v", comparison)
	}

	canonical, err := comparison.CanonicalJSON()
	requireNoError(t, err)
	decoded, err := footprint.DecodeComparison(canonical)
	requireNoError(t, err)
	if decoded.Delta != comparison.Delta || decoded.Unit != comparison.Unit {
		t.Fatalf("decoded comparison = %#v", decoded)
	}
}

func TestCompareCanInferSelectorForSingleComponent(t *testing.T) {
	control := comparableRecord("control", 2, footprint.UnitBytes)
	treatment := comparableRecord("treatment", 3, footprint.UnitBytes)
	comparison, err := footprint.Compare(nil, footprint.CompareRequest{Control: control, Treatment: treatment})
	requireNoError(t, err)
	if comparison.Component.Name != "body" || comparison.Delta != 1 {
		t.Fatalf("inferred comparison = %#v", comparison)
	}
}

func TestCompareRequiresSelectorForMultipleComponents(t *testing.T) {
	control := baseRecord()
	treatment := baseRecord()
	treatment.Observation.Variant = "treatment"
	treatment.Components[0].Metric.Value = int64ptr(2)
	_, err := footprint.Compare(nil, footprint.CompareRequest{Control: control, Treatment: treatment})
	requireErrorIs(t, err, footprint.ErrInvalidType)
}

func TestCompareRejectsIncompatibleInputs(t *testing.T) {
	cases := []struct {
		name   string
		want   error
		mutate func(footprint.Record, footprint.Record) (footprint.Record, footprint.Record)
	}{
		{
			name: "observation workload",
			want: footprint.ErrIncompatibleComparison,
			mutate: func(control, treatment footprint.Record) (footprint.Record, footprint.Record) {
				treatment.Observation.Workload = "different-workload"
				return control, treatment
			},
		},
		{
			name: "unit mismatch",
			want: footprint.ErrUnitMismatch,
			mutate: func(control, treatment footprint.Record) (footprint.Record, footprint.Record) {
				treatment.Components[0].Metric.Unit = footprint.UnitCharacters
				return control, treatment
			},
		},
		{
			name: "unavailable metric",
			want: footprint.ErrUnavailableMetric,
			mutate: func(control, treatment footprint.Record) (footprint.Record, footprint.Record) {
				treatment.Components[0] = unavailableComponent(footprint.ComponentSelectedBody, "body", footprint.UnitBytes)
				return control, treatment
			},
		},
		{
			name: "selector kind",
			want: footprint.ErrUnknownVocabulary,
			mutate: func(control, treatment footprint.Record) (footprint.Record, footprint.Record) {
				return control, treatment
			},
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			control := comparableRecord("control", 2, footprint.UnitBytes)
			treatment := comparableRecord("treatment", 3, footprint.UnitBytes)
			control, treatment = tc.mutate(control, treatment)
			request := footprint.CompareRequest{Control: control, Treatment: treatment}
			if tc.name == "selector kind" {
				request.Component = footprint.ComponentSelector{
					ControlIdentity: footprint.ControlSelectedBody,
					Kind:            footprint.ComponentKind("future_kind"),
					Name:            "body",
				}
			}
			_, err := footprint.Compare(nil, request)
			requireErrorIs(t, err, tc.want)
		})
	}
}

func TestCompareRejectsConflictingConvenienceSelectors(t *testing.T) {
	control := comparableRecord("control", 2, footprint.UnitBytes)
	treatment := comparableRecord("treatment", 3, footprint.UnitBytes)
	_, err := footprint.Compare(nil, footprint.CompareRequest{
		Control:       control,
		Treatment:     treatment,
		Component:     footprint.ComponentSelector{Kind: footprint.ComponentSelectedBody, Name: "body"},
		ComponentKind: footprint.ComponentSelectedDescription,
	})
	requireErrorIs(t, err, footprint.ErrUnknownVocabulary)

	_, err = footprint.Compare(nil, footprint.CompareRequest{
		Control:       control,
		Treatment:     treatment,
		Component:     footprint.ComponentSelector{Kind: footprint.ComponentSelectedBody, Name: "body"},
		ComponentName: "other",
	})
	requireErrorIs(t, err, footprint.ErrInvalidType)
}

func TestCompareRejectsForgedComparisonAndInvalidDigest(t *testing.T) {
	control := comparableRecord("control", 2, footprint.UnitBytes)
	treatment := comparableRecord("treatment", 3, footprint.UnitBytes)
	comparison, err := footprint.Compare(nil, footprint.CompareRequest{Control: control, Treatment: treatment})
	requireNoError(t, err)
	comparison.Delta++
	_, err = comparison.CanonicalJSON()
	requireErrorIs(t, err, footprint.ErrInvalidComparison)

	comparison, err = footprint.Compare(nil, footprint.CompareRequest{Control: control, Treatment: treatment})
	requireNoError(t, err)
	comparison.Control.RecordDigest = "fp-sha256:not-a-digest"
	_, err = comparison.CanonicalJSON()
	requireErrorIs(t, err, footprint.ErrInvalidType)
}

func TestCompareHonorsCancellationAndDeadline(t *testing.T) {
	control := comparableRecord("control", 2, footprint.UnitBytes)
	treatment := comparableRecord("treatment", 3, footprint.UnitBytes)

	cancelled, cancel := context.WithCancel(context.Background())
	cancel()
	_, err := footprint.Compare(cancelled, footprint.CompareRequest{Control: control, Treatment: treatment})
	requireErrorIs(t, err, footprint.ErrContextCancelled)
	requireErrorIs(t, err, context.Canceled)

	deadline, cancel := context.WithDeadline(context.Background(), pastTime())
	defer cancel()
	_, err = footprint.Compare(deadline, footprint.CompareRequest{Control: control, Treatment: treatment})
	requireErrorIs(t, err, context.DeadlineExceeded)
}

func pastTime() time.Time { return time.Unix(0, 0) }

func TestCompareAllowsZeroDeltaAndRejectsUnavailableMetric(t *testing.T) {
	control := comparableRecord("control", 0, footprint.UnitBytes)
	treatment := comparableRecord("treatment", 0, footprint.UnitBytes)
	comparison, err := footprint.Compare(nil, footprint.CompareRequest{Control: control, Treatment: treatment})
	requireNoError(t, err)
	if comparison.Delta != 0 || comparison.Control.Metric.Value == nil || *comparison.Control.Metric.Value != 0 {
		t.Fatalf("zero comparison = %#v", comparison)
	}

	control.Components[0] = unavailableComponent(footprint.ComponentSelectedBody, "body", footprint.UnitBytes)
	_, err = footprint.Compare(nil, footprint.CompareRequest{Control: control, Treatment: treatment})
	requireErrorIs(t, err, footprint.ErrUnavailableMetric)
}

func TestCompareBoundariesUseIntegerMetrics(t *testing.T) {
	// Non-negative available metrics make the regular subtraction boundary
	// explicit; the maximal treatment value remains representable.
	control := comparableRecord("control", 0, footprint.UnitBytes)
	treatment := comparableRecord("treatment", math.MaxInt64, footprint.UnitBytes)
	comparison, err := footprint.Compare(nil, footprint.CompareRequest{Control: control, Treatment: treatment})
	requireNoError(t, err)
	if comparison.Delta != math.MaxInt64 {
		t.Fatalf("maximal delta = %d", comparison.Delta)
	}

	// Context cancellation is an error class, not a partial comparison.
	cancelled, cancel := context.WithCancel(context.Background())
	cancel()
	if result, err := footprint.Compare(cancelled, footprint.CompareRequest{Control: control, Treatment: treatment}); !errors.Is(err, footprint.ErrContextCancelled) || !reflect.DeepEqual(result, footprint.Comparison{}) {
		t.Fatalf("cancelled comparison = %#v, %v", result, err)
	}
}
