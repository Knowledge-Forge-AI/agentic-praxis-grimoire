package footprint_test

import (
	"context"
	"reflect"
	"testing"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/footprint"
)

func TestMultiComponentMeasureCompareAndProjectFlow(t *testing.T) {
	makeRequest := func(variant, body, description string) footprint.MeasureRequest {
		return footprint.MeasureRequest{
			SchemaVersion: footprint.FootprintSchemaV1,
			Observation: func() footprint.Observation {
				result := observation(variant)
				result.Workload = "catalog-selection"
				result.Method = "first-party-materialization"
				return result
			}(),
			Components: []footprint.ComponentInput{
				{Kind: footprint.ComponentMaterializedBundle, Name: "bundle", Unit: footprint.UnitBytes, Text: body + description},
				{Kind: footprint.ComponentSelectedBody, Name: "body", Unit: footprint.UnitBytes, Text: body},
				{Kind: footprint.ComponentSelectedDescription, Name: "description", Unit: footprint.UnitCharacters, Text: description},
				{Kind: footprint.ComponentSupportMaterial, Name: "support", Unit: footprint.UnitTokensTiktokenO200k},
			},
			SourceReferences: []footprint.SourceReference{
				{Digest: "sha256:catalog", MediaType: "application/json", Size: int64(len(description)), URI: "urn:apgr:catalog"},
			},
			Sensitivity: footprint.SensitivityInternal,
			Retention:   footprint.RetentionRetained,
		}
	}

	control, err := footprint.Measure(context.Background(), makeRequest("control", "body", "description"))
	requireNoError(t, err)
	treatment, err := footprint.Measure(context.Background(), makeRequest("treatment", "longer body", "description"))
	requireNoError(t, err)
	if len(control.Components) != 4 || len(treatment.Components) != 4 {
		t.Fatalf("multi-component records = %d/%d", len(control.Components), len(treatment.Components))
	}

	comparison, err := footprint.Compare(context.Background(), footprint.CompareRequest{
		Control:   control,
		Treatment: treatment,
		Component: footprint.ComponentSelector{Kind: footprint.ComponentSelectedBody, Name: "body"},
	})
	requireNoError(t, err)
	if comparison.Delta != int64(len("longer body")-len("body")) || comparison.Unit != footprint.UnitBytes {
		t.Fatalf("body comparison = %#v", comparison)
	}
	comparisonJSON, err := comparison.CanonicalJSON()
	requireNoError(t, err)
	if _, err := footprint.DecodeComparison(comparisonJSON); err != nil {
		t.Fatalf("multi-component comparison did not decode: %v", err)
	}

	projection, err := footprint.Project(context.Background(), footprint.ProjectRequest{
		Source:        treatment,
		Fidelity:      footprint.FidelitySummarizedLossy,
		OmittedFields: []string{"description"},
	})
	requireNoError(t, err)
	if len(projection.Record.Components) != 3 || !hasComponentNamed(projection.Record, "body") || hasComponentNamed(projection.Record, "description") {
		t.Fatalf("projected component set = %#v", projection.Record.Components)
	}
	if projection.CanonicalSourceDigest != footprint.FingerprintRecord(treatment) {
		t.Fatalf("projected source identity = %q", projection.CanonicalSourceDigest)
	}
	if !reflect.DeepEqual(projection.Record.SourceReferences, treatment.SourceReferences) {
		t.Fatal("projection did not preserve source references")
	}

	projectionJSON, err := projection.CanonicalJSON()
	requireNoError(t, err)
	decodedProjection, err := footprint.DecodeProjection(projectionJSON)
	requireNoError(t, err)
	if !reflect.DeepEqual(decodedProjection, projection) {
		t.Fatal("multi-component projection changed across decode")
	}
}

func TestValidateRecordCatchesZeroValueUnavailableAndDuplicateSources(t *testing.T) {
	record := baseRecord()
	record.Components[0].Metric = footprint.Metric{Availability: footprint.Available, Unit: footprint.UnitBytes}
	requireErrorIs(t, footprint.ValidateRecord(record), footprint.ErrInvalidType)

	record = baseRecord()
	negative := int64(-1)
	record.Components[0].Metric.Value = &negative
	requireErrorIs(t, footprint.ValidateRecord(record), footprint.ErrInvalidType)

	record = baseRecord()
	record.Components[0].Metric = footprint.Metric{Availability: footprint.Unavailable, Reason: "missing", Unit: footprint.UnitBytes, Value: int64ptr(0)}
	requireErrorIs(t, footprint.ValidateRecord(record), footprint.ErrUnavailableMetric)

	record = baseRecord()
	record.SourceReferences = append(record.SourceReferences, record.SourceReferences[0])
	requireErrorIs(t, footprint.ValidateRecord(record), footprint.ErrDuplicateField)
}
