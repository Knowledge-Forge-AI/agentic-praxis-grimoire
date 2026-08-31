package skills

import (
	"bytes"
	"context"
	"errors"
	"strings"
	"testing"

	apgfootprint "github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/footprint"
)

func TestFootprintBindsResolvedBundleAndSeparatesSurfaces(t *testing.T) {
	request := baseRequest("go-language-profile", "go-test-profile")
	result, err := Resolve(context.Background(), request)
	if err != nil {
		t.Fatal(err)
	}

	record, err := Footprint(request, result)
	if err != nil {
		t.Fatal(err)
	}
	if record.SchemaVersion != apgfootprint.FootprintSchemaV1 {
		t.Fatalf("schema = %q", record.SchemaVersion)
	}
	if record.Observation.Basis != apgfootprint.ObservationBasisDirectMeasurement || record.Observation.Availability != apgfootprint.Available {
		t.Fatalf("observation = %#v", record.Observation)
	}
	if record.Observation.Provider != "provider-neutral" || record.Observation.Tokenizer != "not_applicable" {
		t.Fatalf("provider boundary = %#v", record.Observation)
	}

	components := footprintComponents(t, record)
	if got := componentValue(t, components, apgfootprint.ComponentSelectedDescription, FootprintSelectedDescriptions); got != result.SelectedDescriptionBytes {
		t.Fatalf("selected descriptions = %d, want %d", got, result.SelectedDescriptionBytes)
	}
	if got := componentValue(t, components, apgfootprint.ComponentSelectedBody, FootprintSelectedBodies); got != result.SelectedBodyBytes {
		t.Fatalf("selected bodies = %d, want %d", got, result.SelectedBodyBytes)
	}
	support := componentValue(t, components, apgfootprint.ComponentSupportMaterial, FootprintSupportMaterial)
	full := componentValue(t, components, apgfootprint.ComponentMaterializedBundle, FootprintMaterializedBundle)
	if support <= 0 || full != result.SelectedBodyBytes+support {
		t.Fatalf("materialization surfaces support=%d full=%d body=%d", support, full, result.SelectedBodyBytes)
	}
	if metric := components[string(apgfootprint.ComponentSupportMaterial)+"/"+FootprintRepositorySupport].Metric; metric.Availability != apgfootprint.Unavailable || metric.Value != nil {
		t.Fatalf("repository support metric = %#v", metric)
	}
	prompt := components[string(apgfootprint.ComponentPromptOverhead)+"/"+FootprintPromptOverhead].Metric
	if prompt.Availability != apgfootprint.Unavailable || prompt.Value != nil || prompt.Reason == "" {
		t.Fatalf("prompt overhead metric = %#v", prompt)
	}
	if !containsString(record.Observation.Exclusions, "provider_context_fit") || !containsString(record.Observation.Exclusions, "provider_total_context") {
		t.Fatalf("provider exclusions = %v", record.Observation.Exclusions)
	}
	if record.Fingerprint() == "" {
		t.Fatal("record has no fingerprint")
	}

	for _, uri := range []string{
		"apg:skill-corpus/",
		"apg:skill-selection-rules/",
		"apg:capacity-control-mapping/",
		"apg:context-projection/schema",
		"apg:context-footprint/serializer",
		"apg:context-footprint/digest/record",
	} {
		if !containsSourceURI(record.SourceReferences, uri) {
			t.Fatalf("source references missing %q: %#v", uri, record.SourceReferences)
		}
	}
}

func TestFootprintMaterializationBindingAndDeterminism(t *testing.T) {
	request := flatRequest("planning-repository-work", "go-language-profile")
	result, err := Resolve(context.Background(), request)
	if err != nil {
		t.Fatal(err)
	}
	materialization, err := Materialize(context.Background(), MaterializeRequest{DestinationParent: privateParent(t), Result: result})
	if err != nil {
		t.Fatal(err)
	}

	first, err := FootprintWithMaterialization(request, result, materialization)
	if err != nil {
		t.Fatal(err)
	}
	second, err := FootprintWithMaterialization(request, result, materialization)
	if err != nil {
		t.Fatal(err)
	}
	firstJSON, err := first.CanonicalJSON()
	if err != nil {
		t.Fatal(err)
	}
	secondJSON, err := second.CanonicalJSON()
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(firstJSON, secondJSON) || first.Fingerprint() != second.Fingerprint() {
		t.Fatal("repeated materialized adaptation changed identity")
	}
	if containsString(first.Observation.Exclusions, "filesystem_materialization_not_executed") {
		t.Fatalf("executed materialization was marked unexecuted: %v", first.Observation.Exclusions)
	}

	tampered := materialization
	tampered.ManifestFingerprint = "sha256:" + strings.Repeat("a", 64)
	if _, err := FootprintWithMaterialization(request, result, tampered); !errors.Is(err, apgfootprint.ErrInvalidRecord) {
		t.Fatalf("tampered materialization error = %v", err)
	}
}

func TestFootprintBaselineIdentityAndZeroAvailability(t *testing.T) {
	metadata, err := Metadata()
	if err != nil {
		t.Fatal(err)
	}
	if len(metadata.Skills) != 39 || metadata.DescriptionBytes != 9504 || metadata.DescriptionCharacters != 9492 {
		t.Fatalf("corpus baseline = skills %d, bytes %d, chars %d", len(metadata.Skills), metadata.DescriptionBytes, metadata.DescriptionCharacters)
	}
	if GlobalDescriptionLimit != 9527 {
		t.Fatalf("historical limit = %d", GlobalDescriptionLimit)
	}

	request := baseRequest()
	result, err := Resolve(context.Background(), request)
	if err != nil {
		t.Fatal(err)
	}
	record, err := Footprint(request, result)
	if err != nil {
		t.Fatal(err)
	}
	descriptions := footprintComponent(t, record, apgfootprint.ComponentSelectedDescription, FootprintSelectedDescriptions)
	if descriptions.Metric.Availability != apgfootprint.Available || descriptions.Metric.Value == nil || *descriptions.Metric.Value != 0 {
		t.Fatalf("zero selected descriptions = %#v", descriptions.Metric)
	}
	prompt := footprintComponent(t, record, apgfootprint.ComponentPromptOverhead, FootprintPromptOverhead)
	if prompt.Metric.Availability != apgfootprint.Unavailable || prompt.Metric.Value != nil {
		t.Fatalf("missing prompt overhead was coerced: %#v", prompt.Metric)
	}
}

func TestFootprintContextCancellationAndResultBinding(t *testing.T) {
	request := baseRequest("go-language-profile")
	result, err := Resolve(context.Background(), request)
	if err != nil {
		t.Fatal(err)
	}
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	if _, err := FootprintContext(ctx, request, result); !errors.Is(err, apgfootprint.ErrContextCancelled) {
		t.Fatalf("cancelled adaptation = %v", err)
	}

	otherRequest := baseRequest("python-language-profile")
	if _, err := Footprint(otherRequest, result); !errors.Is(err, apgfootprint.ErrInvalidRecord) {
		t.Fatalf("mismatched result = %v", err)
	}
}

func footprintComponents(t *testing.T, record apgfootprint.Record) map[string]apgfootprint.Component {
	t.Helper()
	result := make(map[string]apgfootprint.Component, len(record.Components))
	for _, component := range record.Components {
		key := string(component.Kind) + "/" + component.Name
		if _, exists := result[key]; exists {
			t.Fatalf("duplicate component %q", key)
		}
		result[key] = component
	}
	return result
}

func footprintComponent(t *testing.T, record apgfootprint.Record, kind apgfootprint.ComponentKind, name string) apgfootprint.Component {
	t.Helper()
	component, ok := footprintComponents(t, record)[string(kind)+"/"+name]
	if !ok {
		t.Fatalf("component %s/%s is absent", kind, name)
	}
	return component
}

func componentValue(t *testing.T, components map[string]apgfootprint.Component, kind apgfootprint.ComponentKind, name string) int64 {
	t.Helper()
	component, ok := components[string(kind)+"/"+name]
	if !ok || component.Metric.Availability != apgfootprint.Available || component.Metric.Value == nil {
		t.Fatalf("component %s/%s is unavailable: %#v", kind, name, component)
	}
	return *component.Metric.Value
}

func containsSourceURI(references []apgfootprint.SourceReference, prefix string) bool {
	for _, reference := range references {
		if len(reference.URI) >= len(prefix) && reference.URI[:len(prefix)] == prefix {
			return true
		}
	}
	return false
}

func containsString(values []string, want string) bool {
	for _, value := range values {
		if value == want {
			return true
		}
	}
	return false
}
