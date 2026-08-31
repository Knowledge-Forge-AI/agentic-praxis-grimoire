package main

import (
	"bytes"
	"context"
	"errors"
	"io/fs"
	"path/filepath"
	"testing"
	"time"

	footprint "github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/footprint"
	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/skills"
)

func observation(variant string) footprint.Observation {
	return footprint.Observation{
		Basis:        footprint.ObservationBasisDirectMeasurement,
		Availability: footprint.Available,
		Exclusions:   []string{"provider_prompt_overhead"},
		Harness:      "external-consumer-fixture",
		Method:       "fixture-measurement",
		Provider:     "provider-neutral",
		Quality:      footprint.QualityVerified,
		Repetitions:  1,
		StudyDesign:  footprint.StudyDesignSingleRun,
		Tokenizer:    "not_applicable",
		Variant:      variant,
		Workload:     "multi_component_context",
	}
}

func measuredRecord(t *testing.T, variant string, bodyUnit footprint.Unit, bodyValue int64) footprint.Record {
	t.Helper()
	value := bodyValue
	record, err := footprint.Measure(context.Background(), footprint.MeasureRequest{
		SchemaVersion: footprint.FootprintSchemaV1,
		Observation:   observation(variant),
		Components: []footprint.ComponentInput{
			{
				Kind: footprint.ComponentSelectedDescription,
				Name: "selected_description",
				Unit: footprint.UnitCharacters,
				Text: "APGR",
			},
			{
				Kind: footprint.ComponentSelectedBody,
				Name: "selected_body",
				Unit: bodyUnit,
				Metric: footprint.Metric{
					Availability: footprint.Available,
					Unit:         bodyUnit,
					Value:        &value,
				},
			},
			{
				Kind: footprint.ComponentPromptOverhead,
				Name: "provider_prompt_overhead",
				Unit: footprint.UnitTokensTiktokenCL100k,
				Metric: footprint.Metric{
					Availability: footprint.Unavailable,
					Reason:       "provider tokenizer is outside the independent fixture",
					Unit:         footprint.UnitTokensTiktokenCL100k,
				},
			},
		},
		SourceReferences: []footprint.SourceReference{{
			Digest:    "sha256:fixture-source",
			MediaType: "text/plain",
			Size:      4,
			URI:       "fixture://external-consumer/source",
		}},
		Sensitivity: footprint.SensitivityPublic,
		Retention:   footprint.RetentionRetained,
	})
	if err != nil {
		t.Fatalf("measure %s record: %v", variant, err)
	}
	return record
}

func requireIs(t *testing.T, err error, target error) {
	t.Helper()
	if !errors.Is(err, target) {
		t.Fatalf("error %v is not %v", err, target)
	}
}

func requireNoError(t *testing.T, err error) {
	t.Helper()
	if err != nil {
		t.Fatal(err)
	}
}

func rootFieldJSON(data []byte, field string, value []byte) []byte {
	trimmed := bytes.TrimSpace(data)
	trimmed = trimmed[:len(trimmed)-1]
	result := append([]byte{}, trimmed...)
	result = append(result, []byte(",\"")...)
	result = append(result, field...)
	result = append(result, []byte("\":")...)
	result = append(result, value...)
	result = append(result, '}', '\n')
	return result
}

func replaceFirst(data []byte, old, replacement string) []byte {
	return bytes.Replace(data, []byte(old), []byte(replacement), 1)
}

func TestFootprintPublicRoundTripAndDeterminism(t *testing.T) {
	record := measuredRecord(t, "control", footprint.UnitBytes, 12)
	if err := footprint.ValidateRecord(record); err != nil {
		t.Fatalf("validate record: %v", err)
	}

	canonical, err := record.CanonicalJSON()
	requireNoError(t, err)
	if !bytes.Equal(canonical, mustMarshalRecord(t, record)) || !bytes.Equal(canonical, mustMarshalFootprint(t, record)) {
		t.Fatal("record marshal aliases disagree")
	}
	if !bytes.Equal(canonical, mustCanonical(t, record)) {
		t.Fatal("generic canonical encoder disagrees")
	}
	if !bytes.HasSuffix(canonical, []byte{'\n'}) || bytes.HasSuffix(canonical, []byte{'\n', '\n'}) {
		t.Fatal("canonical record must have exactly one trailing LF")
	}

	decoded, err := footprint.DecodeRecord(canonical)
	requireNoError(t, err)
	decodedMeasurement, err := footprint.DecodeMeasurement(canonical)
	requireNoError(t, err)
	decodedFootprint, err := footprint.DecodeFootprint(canonical)
	requireNoError(t, err)
	if decoded.Fingerprint() != decodedMeasurement.Fingerprint() || decoded.Fingerprint() != decodedFootprint.Fingerprint() {
		t.Fatal("record decoder aliases disagree")
	}
	if got := footprint.FingerprintRecord(record); got == "" || got != record.Fingerprint() || got != footprint.FingerprintFootprint(record) || got != footprint.Fingerprint(record) {
		t.Fatalf("record fingerprint aliases disagree: %q", got)
	}
	if got, err := footprint.FingerprintWithError(record); err != nil || got != record.Fingerprint() {
		t.Fatalf("fingerprint with error: %q, %v", got, err)
	}
	if got, err := footprint.FingerprintWithError(struct{}{}); !errors.Is(err, footprint.ErrInvalidType) || got != "" {
		t.Fatalf("unsupported fingerprint result = %q, %v", got, err)
	}
	if got := footprint.Fingerprint(struct{}{}); got != "" {
		t.Fatalf("unsupported generic fingerprint = %q", got)
	}

	zero := measuredRecord(t, "zero", footprint.UnitBytes, 0)
	if got := metricValue(t, zero, footprint.ComponentSelectedBody, "selected_body"); got != 0 {
		t.Fatalf("available zero metric = %d", got)
	}
	if metric := metricFor(t, record, footprint.ComponentPromptOverhead, "provider_prompt_overhead"); metric.Availability != footprint.Unavailable || metric.Value != nil {
		t.Fatalf("unavailable metric was coerced: %#v", metric)
	}
	_, err = footprint.Measure(context.Background(), footprint.MeasureRequest{
		SchemaVersion: footprint.FootprintSchemaV1,
		Observation:   observation("invalid-unit"),
		Components: []footprint.ComponentInput{{
			Kind: footprint.ComponentBody,
			Name: "body",
			Unit: footprint.UnitBytes,
			Metric: footprint.Metric{
				Availability: footprint.Available,
				Unit:         footprint.UnitCharacters,
				Value:        int64ptrForTest(1),
			},
		}},
		Sensitivity: footprint.SensitivityPublic,
		Retention:   footprint.RetentionEphemeral,
	})
	requireIs(t, err, footprint.ErrUnitMismatch)
	_, err = footprint.Measure(context.Background(), footprint.MeasureRequest{
		SchemaVersion: footprint.FootprintSchemaV1,
		Observation:   observation("invalid-unavailable"),
		Components: []footprint.ComponentInput{{
			Kind: footprint.ComponentBody,
			Name: "body",
			Unit: footprint.UnitBytes,
			Metric: footprint.Metric{
				Availability: footprint.Unavailable,
				Reason:       "not measured",
				Unit:         footprint.UnitBytes,
				Value:        int64ptrForTest(1),
			},
		}},
		Sensitivity: footprint.SensitivityPublic,
		Retention:   footprint.RetentionEphemeral,
	})
	requireIs(t, err, footprint.ErrUnavailableMetric)

	mutated := append([]byte{}, canonical...)
	mutated = rootFieldJSON(mutated, "unexpected", []byte("true"))
	_, err = footprint.DecodeRecord(mutated)
	requireIs(t, err, footprint.ErrUnknownField)
	_, err = footprint.DecodeRecord(replaceFirst(canonical, footprint.FootprintSchemaV1, "apg.context-footprint/v99"))
	requireIs(t, err, footprint.ErrUnknownSchema)
	_, err = footprint.DecodeRecord([]byte("{"))
	requireIs(t, err, footprint.ErrMalformedJSON)
	_, err = footprint.DecodeRecord(append(append([]byte{}, canonical...), []byte("{}")...))
	requireIs(t, err, footprint.ErrTrailingData)
	_, err = footprint.DecodeRecord(append(append([]byte{}, canonical...), 0xff))
	requireIs(t, err, footprint.ErrInvalidUTF8)
	missingRetention := replaceFirst(canonical, `,"retention":"retained"`, "")
	_, err = footprint.DecodeRecord(missingRetention)
	requireIs(t, err, footprint.ErrMissingField)
}

func int64ptrForTest(value int64) *int64 { return &value }

func TestFootprintCompareProjectAndValidationBoundaries(t *testing.T) {
	control := measuredRecord(t, "control", footprint.UnitBytes, 10)
	treatment := measuredRecord(t, "treatment", footprint.UnitBytes, 16)
	comparison, err := footprint.Compare(context.Background(), footprint.CompareRequest{
		Control:   control,
		Treatment: treatment,
		Component: footprint.ComponentSelector{
			ControlIdentity: footprint.ControlSelectedBody,
			Kind:            footprint.ComponentSelectedBody,
			Name:            "selected_body",
		},
	})
	requireNoError(t, err)
	if comparison.Delta != 6 || comparison.Unit != footprint.UnitBytes {
		t.Fatalf("comparison = %#v", comparison)
	}
	if err := footprint.ValidateComparison(comparison); err != nil {
		t.Fatalf("validate comparison: %v", err)
	}
	comparisonJSON, err := footprint.MarshalComparison(comparison)
	requireNoError(t, err)
	if !bytes.Equal(comparisonJSON, mustCanonical(t, comparison)) {
		t.Fatal("comparison canonical aliases disagree")
	}
	decoded, err := footprint.DecodeComparison(comparisonJSON)
	requireNoError(t, err)
	if decoded.Fingerprint() != comparison.Fingerprint() || footprint.FingerprintComparison(comparison) != comparison.Fingerprint() || footprint.Fingerprint(comparison) != comparison.Fingerprint() {
		t.Fatal("comparison round trip or fingerprint failed")
	}

	projection, err := footprint.Project(context.Background(), footprint.ProjectRequest{
		Source:        control,
		Fidelity:      footprint.FidelitySummarizedLossy,
		OmittedFields: []string{"body"},
	})
	requireNoError(t, err)
	if projection.CanonicalSourceDigest != control.Fingerprint() || projection.CanonicalSourceSchema != footprint.FootprintSchemaV1 || projection.CanonicalSourceSize <= 0 || len(projection.OmittedFields) != 1 {
		t.Fatalf("projection binding = %#v", projection)
	}
	if err := footprint.ValidateProjection(projection); err != nil {
		t.Fatalf("validate projection: %v", err)
	}
	projectionJSON, err := footprint.MarshalProjection(projection)
	requireNoError(t, err)
	decodedProjection, err := footprint.DecodeProjection(projectionJSON)
	requireNoError(t, err)
	if decodedProjection.CanonicalSourceDigest != projection.CanonicalSourceDigest || footprint.FingerprintProjection(projection) != projection.Fingerprint() || footprint.Fingerprint(projection) != projection.Fingerprint() {
		t.Fatal("projection round trip or fingerprint failed")
	}

	_, err = footprint.Project(context.Background(), footprint.ProjectRequest{Source: control, Fidelity: footprint.FidelitySummarizedLossy, OmittedFields: []string{"observation"}})
	requireIs(t, err, footprint.ErrConsequenceBearingOmissionRefused)
	_, err = footprint.Project(context.Background(), footprint.ProjectRequest{Source: control, Fidelity: footprint.FidelitySummarizedLossy, OmittedFields: []string{"body", "body"}})
	requireIs(t, err, footprint.ErrDuplicateField)
	_, err = footprint.Compare(context.Background(), footprint.CompareRequest{Control: control, Treatment: measuredRecord(t, "treatment", footprint.UnitCharacters, 16), ComponentKind: footprint.ComponentSelectedBody, ComponentName: "selected_body"})
	requireIs(t, err, footprint.ErrUnitMismatch)
	withUnavailable := measuredRecord(t, "unavailable", footprint.UnitBytes, 16)
	withUnavailable.Components = append(withUnavailable.Components, footprint.Component{ControlIdentity: footprint.ControlPromptOverhead, Kind: footprint.ComponentPromptOverhead, Name: "other", Metric: footprint.Metric{Availability: footprint.Unavailable, Reason: "not observed", Unit: footprint.UnitTokensTiktokenCL100k}})
	if err := footprint.ValidateRecord(withUnavailable); err != nil {
		t.Fatalf("validate unavailable source: %v", err)
	}
	_, err = footprint.Compare(context.Background(), footprint.CompareRequest{Control: withUnavailable, Treatment: withUnavailable, Component: footprint.ComponentSelector{ControlIdentity: footprint.ControlPromptOverhead, Kind: footprint.ComponentPromptOverhead, Name: "other"}})
	requireIs(t, err, footprint.ErrUnavailableMetric)
	internal := control
	internal.Sensitivity = footprint.SensitivityInternal
	_, err = footprint.Project(context.Background(), footprint.ProjectRequest{
		Source:      internal,
		Fidelity:    footprint.FidelityExact,
		Sensitivity: footprint.SensitivityPublic,
	})
	requireIs(t, err, footprint.ErrSensitivityDowngrade)
}

func TestFootprintContextCancellationAndDeadline(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	_, err := footprint.Measure(ctx, footprint.MeasureRequest{SchemaVersion: footprint.FootprintSchemaV1, Observation: observation("cancelled"), Components: []footprint.ComponentInput{{Kind: footprint.ComponentBody, Name: "body", Unit: footprint.UnitBytes, Data: []byte("x")}}, Sensitivity: footprint.SensitivityPublic, Retention: footprint.RetentionEphemeral})
	requireIs(t, err, footprint.ErrContextCancelled)
	deadline, cancel := context.WithDeadline(context.Background(), unixEpoch())
	defer cancel()
	_, err = footprint.Compare(deadline, footprint.CompareRequest{})
	requireIs(t, err, footprint.ErrContextCancelled)
	_, err = footprint.Project(deadline, footprint.ProjectRequest{})
	requireIs(t, err, footprint.ErrContextCancelled)
}

func unixEpoch() (value time.Time) { return time.Unix(0, 0) }

func TestFootprintRegistriesAndMappings(t *testing.T) {
	registry := footprint.DefaultComponentRegistry()
	mapping := footprint.DefaultControlMapping()
	requireNoError(t, footprint.ValidateComponentRegistry(registry))
	requireNoError(t, footprint.ValidateControlMapping(mapping))
	registryJSON, err := footprint.MarshalComponentRegistry(registry)
	requireNoError(t, err)
	mappingJSON, err := footprint.MarshalControlMapping(mapping)
	requireNoError(t, err)
	if !bytes.Equal(registryJSON, mustCanonical(t, registry)) || !bytes.Equal(mappingJSON, mustCanonical(t, mapping)) {
		t.Fatal("registry or mapping canonical aliases disagree")
	}
	decodedRegistry, err := footprint.DecodeComponentRegistry(registryJSON)
	requireNoError(t, err)
	decodedRegistryAlias, err := footprint.DecodeRegistry(registryJSON)
	requireNoError(t, err)
	decodedMapping, err := footprint.DecodeControlMapping(mappingJSON)
	requireNoError(t, err)
	decodedMappingAlias, err := footprint.DecodeCapacityControlMapping(mappingJSON)
	requireNoError(t, err)
	if len(decodedRegistry.Components) != len(registry.Components) || len(decodedRegistryAlias.Components) != len(registry.Components) || len(decodedMapping.Mappings) != len(mapping.Mappings) || len(decodedMappingAlias.Mappings) != len(mapping.Mappings) {
		t.Fatal("registry or mapping decoder aliases disagree")
	}
	if footprint.FingerprintComponentRegistry(registry) != registry.Fingerprint() || footprint.FingerprintControlMapping(mapping) != mapping.Fingerprint() {
		t.Fatal("registry or mapping fingerprint aliases disagree")
	}
	_, err = footprint.DecodeComponentRegistry(replaceFirst(registryJSON, footprint.ComponentRegistrySchemaV1, "apg.context-component-registry/v99"))
	requireIs(t, err, footprint.ErrUnknownSchema)
	_, err = footprint.DecodeControlMapping(rootFieldJSON(mappingJSON, "unexpected", []byte("true")))
	requireIs(t, err, footprint.ErrUnknownField)
}

func TestIndependentSkillsWorkflow(t *testing.T) {
	metadata, err := skills.Metadata()
	requireNoError(t, err)
	if metadata.Fingerprint == "" || metadata.DescriptionBytes <= 0 || len(metadata.Skills) == 0 {
		t.Fatalf("unexpected corpus metadata: %#v", metadata)
	}
	entries, err := fs.ReadDir(skills.Corpus(), ".")
	requireNoError(t, err)
	if len(entries) == 0 {
		t.Fatal("embedded corpus is empty")
	}
	if len(skills.SelectionRules()) == 0 || len(skills.CompositionRules()) == 0 {
		t.Fatal("selection/composition registries are empty")
	}

	request := skills.BundleRequest{
		Budget: skills.Budget{},
		Consumer: skills.Consumer{
			Kind:                skills.ConsumerGo,
			MaterializationForm: skills.MaterializationInMemory,
			ProviderConstraints: []string{"in_process_library"},
		},
		ExplicitSkillIDs: []string{"go-language-profile"},
		SchemaVersion:    skills.BundleRequestSchemaV1,
	}
	result, err := skills.Resolve(context.Background(), request)
	requireNoError(t, err)
	if len(result.SelectedSkillIDs) != 1 || result.SelectedSkillIDs[0] != "go-language-profile" {
		t.Fatalf("resolved result = %#v", result.SelectedSkillIDs)
	}
	resultJSON, err := result.CanonicalJSON()
	requireNoError(t, err)
	decodedResult, err := skills.DecodeBundleResult(resultJSON)
	requireNoError(t, err)
	if decodedResult.BundleFingerprint != result.BundleFingerprint {
		t.Fatal("bundle result did not round trip")
	}
	requestJSON, err := request.CanonicalJSON()
	requireNoError(t, err)
	decodedRequest, err := skills.DecodeBundleRequest(requestJSON)
	requireNoError(t, err)
	if decodedRequest.SchemaVersion != request.SchemaVersion || decodedRequest.Consumer.Kind != request.Consumer.Kind {
		t.Fatal("bundle request did not round trip")
	}

	record, err := skills.Footprint(request, result)
	requireNoError(t, err)
	recordContext, err := skills.FootprintContext(context.Background(), request, result)
	requireNoError(t, err)
	recordMeasure, err := skills.MeasureFootprint(context.Background(), request, result)
	requireNoError(t, err)
	canonical, err := record.CanonicalJSON()
	requireNoError(t, err)
	if record.Fingerprint() != recordContext.Fingerprint() || record.Fingerprint() != recordMeasure.Fingerprint() || !bytes.Equal(canonical, mustCanonical(t, recordContext)) || !bytes.Equal(canonical, mustCanonical(t, recordMeasure)) {
		t.Fatal("skills footprint aliases are not deterministic")
	}
	if metric := metricFor(t, record, footprint.ComponentSelectedDescription, skills.FootprintSelectedDescriptions); metric.Availability != footprint.Available {
		t.Fatalf("selected description metric = %#v", metric)
	}
	if metric := metricFor(t, record, footprint.ComponentPromptOverhead, skills.FootprintPromptOverhead); metric.Availability != footprint.Unavailable || metric.Value != nil {
		t.Fatalf("provider overhead should remain unavailable: %#v", metric)
	}

	flatRequest := request
	flatRequest.Consumer = skills.Consumer{Kind: skills.ConsumerCodex, MaterializationForm: skills.MaterializationFlatDirectory}
	flatResult, err := skills.Resolve(context.Background(), flatRequest)
	requireNoError(t, err)
	materializationParent, err := filepath.EvalSymlinks(t.TempDir())
	requireNoError(t, err)
	materialization, err := skills.Materialize(context.Background(), skills.MaterializeRequest{DestinationParent: materializationParent, Result: flatResult})
	requireNoError(t, err)
	materializedRecord, err := skills.FootprintWithMaterialization(flatRequest, flatResult, materialization)
	requireNoError(t, err)
	materializedRecordContext, err := skills.FootprintWithMaterializationContext(context.Background(), flatRequest, flatResult, materialization)
	requireNoError(t, err)
	if materializedRecord.Fingerprint() != materializedRecordContext.Fingerprint() {
		t.Fatal("materialized skills footprint aliases differ")
	}
	if _, err := materialization.CanonicalJSON(); err != nil {
		t.Fatalf("materialization canonical JSON: %v", err)
	}

	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	_, err = skills.FootprintContext(ctx, request, result)
	if err == nil {
		t.Fatal("cancelled skills footprint unexpectedly succeeded")
	}
	// The skills adapter owns the context boundary and must not return a
	// partially measured record on cancellation.
	if !errors.Is(err, footprint.ErrContextCancelled) {
		t.Fatalf("cancelled skills footprint error = %v", err)
	}
}

func metricFor(t *testing.T, record footprint.Record, kind footprint.ComponentKind, name string) footprint.Metric {
	t.Helper()
	for _, component := range record.Components {
		if component.Kind == kind && component.Name == name {
			return component.Metric
		}
	}
	t.Fatalf("component %s/%s not found", kind, name)
	return footprint.Metric{}
}

func metricValue(t *testing.T, record footprint.Record, kind footprint.ComponentKind, name string) int64 {
	t.Helper()
	metric := metricFor(t, record, kind, name)
	if metric.Value == nil {
		t.Fatalf("metric %s/%s has no value", kind, name)
	}
	return *metric.Value
}

func mustCanonical(t *testing.T, value any) []byte {
	t.Helper()
	result, err := footprint.CanonicalJSON(value)
	requireNoError(t, err)
	return result
}

func mustMarshalRecord(t *testing.T, record footprint.Record) []byte {
	t.Helper()
	result, err := footprint.MarshalRecord(record)
	requireNoError(t, err)
	return result
}

func mustMarshalFootprint(t *testing.T, record footprint.Footprint) []byte {
	t.Helper()
	result, err := footprint.MarshalFootprint(record)
	requireNoError(t, err)
	return result
}
