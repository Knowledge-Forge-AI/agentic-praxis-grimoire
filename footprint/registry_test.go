package footprint_test

import (
	"bytes"
	"reflect"
	"testing"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/footprint"
)

func TestDefaultRegistryAndControlMappingAreCompleteAndIndependent(t *testing.T) {
	registry := footprint.DefaultComponentRegistry()
	mapping := footprint.DefaultControlMapping()
	requireNoError(t, footprint.ValidateComponentRegistry(registry))
	requireNoError(t, footprint.ValidateControlMapping(mapping))
	if registry.SchemaVersion != footprint.ComponentRegistrySchemaV1 {
		t.Fatalf("registry schema = %q", registry.SchemaVersion)
	}
	if mapping.SchemaVersion != footprint.ControlMappingSchemaV1 {
		t.Fatalf("mapping schema = %q", mapping.SchemaVersion)
	}
	if len(registry.Components) == 0 || len(registry.Components) != len(mapping.Mappings) {
		t.Fatalf("registry/mapping cardinality = %d/%d", len(registry.Components), len(mapping.Mappings))
	}
	for index, definition := range registry.Components {
		entry := mapping.Mappings[index]
		if definition.Kind != entry.ComponentKind || definition.ControlIdentity != entry.ControlIdentity {
			t.Fatalf("registry/mapping mismatch at %d: %#v vs %#v", index, definition, entry)
		}
		if index > 0 && registry.Components[index-1].Kind >= definition.Kind {
			t.Fatalf("registry is not canonical order: %#v", registry.Components)
		}
	}

	// Each accessor returns a copy. Mutating a readback must not alter the
	// package-owned registry or mapping used by later callers.
	registry.Components[0].ControlIdentity = "tampered"
	mapping.Mappings[0].ControlIdentity = "tampered"
	registryAgain := footprint.DefaultComponentRegistry()
	mappingAgain := footprint.DefaultControlMapping()
	if registryAgain.Components[0].ControlIdentity == "tampered" || mappingAgain.Mappings[0].ControlIdentity == "tampered" {
		t.Fatal("default registry or mapping leaked mutable package state")
	}
}

func TestRegistryAndMappingCanonicalRoundTrips(t *testing.T) {
	registry := footprint.DefaultComponentRegistry()
	registryJSON, err := registry.CanonicalJSON()
	requireNoError(t, err)
	decodedRegistry, err := footprint.DecodeComponentRegistry(registryJSON)
	requireNoError(t, err)
	if !reflect.DeepEqual(decodedRegistry, registry) {
		t.Fatalf("registry round trip changed value: %#v vs %#v", decodedRegistry, registry)
	}
	if !bytes.Equal(registryJSON, mustCanonical(t, decodedRegistry)) {
		t.Fatal("registry canonical bytes changed across decode")
	}

	mapping := footprint.DefaultControlMapping()
	mappingJSON, err := mapping.CanonicalJSON()
	requireNoError(t, err)
	decodedMapping, err := footprint.DecodeControlMapping(mappingJSON)
	requireNoError(t, err)
	if !reflect.DeepEqual(decodedMapping, mapping) {
		t.Fatalf("mapping round trip changed value: %#v vs %#v", decodedMapping, mapping)
	}
	if !bytes.Equal(mappingJSON, mustCanonical(t, decodedMapping)) {
		t.Fatal("mapping canonical bytes changed across decode")
	}
	if footprint.FingerprintComponentRegistry(registry) == "" || footprint.FingerprintControlMapping(mapping) == "" {
		t.Fatal("valid registry or mapping did not receive a fingerprint")
	}
}

func mustCanonical(t *testing.T, value any) []byte {
	t.Helper()
	canonical, err := footprint.CanonicalJSON(value)
	requireNoError(t, err)
	return canonical
}

func TestRegistryAndMappingRejectUnknownVersionFieldDuplicateAndIncompleteEntries(t *testing.T) {
	registry := footprint.DefaultComponentRegistry()
	registry.Components = registry.Components[:len(registry.Components)-1]
	requireErrorIs(t, footprint.ValidateComponentRegistry(registry), footprint.ErrUnknownVocabulary)

	registry = footprint.DefaultComponentRegistry()
	registry.Components[0].ControlIdentity = "future-control"
	requireErrorIs(t, footprint.ValidateComponentRegistry(registry), footprint.ErrUnknownMapping)

	registry = footprint.DefaultComponentRegistry()
	registry.SchemaVersion = "apg.context-component-registry/v99"
	requireErrorIs(t, footprint.ValidateComponentRegistry(registry), footprint.ErrUnknownSchema)

	mapping := footprint.DefaultControlMapping()
	mapping.Mappings = mapping.Mappings[:len(mapping.Mappings)-1]
	requireErrorIs(t, footprint.ValidateControlMapping(mapping), footprint.ErrUnknownMapping)

	mapping = footprint.DefaultControlMapping()
	mapping.Mappings[0].ControlIdentity = "future-control"
	requireErrorIs(t, footprint.ValidateControlMapping(mapping), footprint.ErrUnknownMapping)

	mapping = footprint.DefaultControlMapping()
	mapping.SchemaVersion = "apg.capacity-control-mapping/v99"
	requireErrorIs(t, footprint.ValidateControlMapping(mapping), footprint.ErrUnknownSchema)
}
