package skills

import (
	"bytes"
	"context"
	"fmt"
	"math"

	apgfootprint "github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/footprint"
)

// The component names are stable identities in the skills-to-footprint
// adapter.  They intentionally distinguish the selected bundle surfaces from
// provider-owned context accounting.
const (
	FootprintSelectedDescriptions = "selected_descriptions"
	FootprintSelectedBodies       = "selected_bodies"
	FootprintSupportMaterial      = "support_material"
	FootprintRepositorySupport    = "repository_support_material"
	FootprintMaterializedBundle   = "full_materialized_bundle"
	FootprintPromptOverhead       = "provider_prompt_overhead"
)

const (
	footprintSerializerIdentity = "apg.canonical-json/v1"
	footprintRecordDigest       = "fp-sha256:"
	footprintComparisonDigest   = "cmp-sha256:"
	footprintProjectionDigest   = "proj-sha256:"
)

// Footprint adapts one accepted, deterministic BundleResult into an APGR
// context-footprint record.  It uses the deterministic materialization
// document as the support surface even when the caller has not written a
// filesystem root.  Provider prompt overhead and provider total-context fit
// remain explicitly outside this first-party measurement boundary.
func Footprint(request BundleRequest, result BundleResult) (apgfootprint.Record, error) {
	return FootprintContext(context.Background(), request, result)
}

// FootprintContext is the cancellation-aware form of Footprint.
func FootprintContext(ctx context.Context, request BundleRequest, result BundleResult) (apgfootprint.Record, error) {
	return footprintWithMaterialization(ctx, request, result, nil)
}

// FootprintWithMaterialization adapts a result and the exact materialization
// metadata returned by Materialize.  The root path is never copied into the
// public record; only its deterministic, validated file metadata contributes
// to the measured bundle surface.
func FootprintWithMaterialization(request BundleRequest, result BundleResult, materialization Materialization) (apgfootprint.Record, error) {
	return FootprintWithMaterializationContext(context.Background(), request, result, materialization)
}

// FootprintWithMaterializationContext is the cancellation-aware materialized
// bundle adapter.
func FootprintWithMaterializationContext(ctx context.Context, request BundleRequest, result BundleResult, materialization Materialization) (apgfootprint.Record, error) {
	return footprintWithMaterialization(ctx, request, result, &materialization)
}

// MeasureFootprint is an explicit verb alias for callers that prefer the
// measurement terminology used by the footprint package.
func MeasureFootprint(ctx context.Context, request BundleRequest, result BundleResult) (apgfootprint.Record, error) {
	return FootprintContext(ctx, request, result)
}

func footprintWithMaterialization(ctx context.Context, request BundleRequest, result BundleResult, supplied *Materialization) (apgfootprint.Record, error) {
	if err := footprintContextError(ctx); err != nil {
		return apgfootprint.Record{}, err
	}
	if ctx == nil {
		ctx = context.Background()
	}

	// Re-resolving is deliberate: it binds the adapter to the current
	// first-party corpus, rule table, and result identity instead of accepting a
	// forged or stale BundleResult that merely has plausible byte counts.
	expected, err := Resolve(ctx, request)
	if err != nil {
		if contextErr := footprintContextError(ctx); contextErr != nil {
			return apgfootprint.Record{}, contextErr
		}
		return apgfootprint.Record{}, fmt.Errorf("%w: bundle result cannot be resolved: %v", apgfootprint.ErrInvalidRecord, err)
	}
	expectedJSON, err := expected.CanonicalJSON()
	if err != nil {
		return apgfootprint.Record{}, fmt.Errorf("%w: expected bundle result identity: %v", apgfootprint.ErrInvalidRecord, err)
	}
	actualJSON, err := result.CanonicalJSON()
	if err != nil {
		return apgfootprint.Record{}, fmt.Errorf("%w: supplied bundle result identity: %v", apgfootprint.ErrInvalidRecord, err)
	}
	if !bytes.Equal(expectedJSON, actualJSON) {
		return apgfootprint.Record{}, fmt.Errorf("%w: supplied bundle result does not match request", apgfootprint.ErrInvalidRecord)
	}
	if err := footprintContextError(ctx); err != nil {
		return apgfootprint.Record{}, err
	}

	_, manifestJSON, expectedMaterialization, err := materializationDocuments(result)
	if err != nil {
		return apgfootprint.Record{}, fmt.Errorf("%w: materialization support document: %v", apgfootprint.ErrInvalidRecord, err)
	}
	if supplied != nil {
		if err := validateSuppliedMaterialization(*supplied, expectedMaterialization); err != nil {
			return apgfootprint.Record{}, err
		}
	}
	bodyBytes, err := materializedBodyBytes(expectedMaterialization.SelectedFiles)
	if err != nil {
		return apgfootprint.Record{}, err
	}
	if int64(len(manifestJSON)) > math.MaxInt64-bodyBytes {
		return apgfootprint.Record{}, fmt.Errorf("%w: materialized bundle measurement overflows int64", apgfootprint.ErrInvalidRecord)
	}
	fullBundleBytes := bodyBytes + int64(len(manifestJSON))

	sources, err := footprintSources(request, result, manifestJSON)
	if err != nil {
		return apgfootprint.Record{}, err
	}

	components := []apgfootprint.ComponentInput{
		availableBytes(apgfootprint.ComponentSelectedDescription, FootprintSelectedDescriptions, result.SelectedDescriptionBytes),
		availableBytes(apgfootprint.ComponentSelectedBody, FootprintSelectedBodies, result.SelectedBodyBytes),
		availableBytes(apgfootprint.ComponentSupportMaterial, FootprintSupportMaterial, int64(len(manifestJSON))),
		unavailableBytes(apgfootprint.ComponentSupportMaterial, FootprintRepositorySupport, "repository-only support material is not present in BundleResult or Materialization"),
		availableBytes(apgfootprint.ComponentMaterializedBundle, FootprintMaterializedBundle, fullBundleBytes),
		unavailableBytes(apgfootprint.ComponentPromptOverhead, FootprintPromptOverhead, "provider prompt overhead and provider total-context accounting are outside APGR measurement"),
	}

	record, err := apgfootprint.Measure(ctx, apgfootprint.MeasureRequest{
		SchemaVersion:    apgfootprint.FootprintSchemaV1,
		Observation:      footprintObservation(result, supplied == nil),
		Components:       components,
		SourceReferences: sources,
		Sensitivity:      apgfootprint.SensitivityPublic,
		Retention:        apgfootprint.RetentionRetained,
	})
	if err != nil {
		return apgfootprint.Record{}, err
	}
	return record, nil
}

func availableBytes(kind apgfootprint.ComponentKind, name string, value int64) apgfootprint.ComponentInput {
	return apgfootprint.ComponentInput{
		Kind: kind,
		Name: name,
		Unit: apgfootprint.UnitBytes,
		Metric: apgfootprint.Metric{
			Availability: apgfootprint.Available,
			Unit:         apgfootprint.UnitBytes,
			Value:        int64Pointer(value),
		},
	}
}

func unavailableBytes(kind apgfootprint.ComponentKind, name, reason string) apgfootprint.ComponentInput {
	return apgfootprint.ComponentInput{
		Kind: kind,
		Name: name,
		Unit: apgfootprint.UnitBytes,
		Metric: apgfootprint.Metric{
			Availability: apgfootprint.Unavailable,
			Reason:       reason,
			Unit:         apgfootprint.UnitBytes,
		},
	}
}

func int64Pointer(value int64) *int64 { return &value }

func footprintObservation(result BundleResult, materializationNotExecuted bool) apgfootprint.Observation {
	exclusions := []string{
		"provider_prompt_overhead",
		"provider_total_context",
		"provider_context_fit",
	}
	if materializationNotExecuted {
		exclusions = append(exclusions, "filesystem_materialization_not_executed")
	}
	return apgfootprint.Observation{
		Basis:        apgfootprint.ObservationBasisDirectMeasurement,
		Availability: apgfootprint.Available,
		Exclusions:   exclusions,
		Harness:      "skills.Resolve/" + BundleResultSchemaV1,
		Method:       "embedded-corpus-and-materialization-byte-count",
		Provider:     "provider-neutral",
		Quality:      apgfootprint.QualityVerified,
		Repetitions:  1,
		StudyDesign:  apgfootprint.StudyDesignSingleRun,
		Tokenizer:    "not_applicable",
		Variant:      "bundle/" + result.BundleFingerprint,
		Workload:     "resolved_skill_bundle",
	}
}

func materializedBodyBytes(files []MaterializedFile) (int64, error) {
	var total int64
	for _, file := range files {
		if file.BodyBytes < 0 || total > math.MaxInt64-file.BodyBytes {
			return 0, fmt.Errorf("%w: materialized body measurement overflows int64", apgfootprint.ErrInvalidRecord)
		}
		total += file.BodyBytes
	}
	return total, nil
}

func validateSuppliedMaterialization(actual, expected Materialization) error {
	if actual.BundleFingerprint != expected.BundleFingerprint ||
		actual.ManifestFingerprint != expected.ManifestFingerprint ||
		actual.ManifestSchemaVersion != expected.ManifestSchemaVersion ||
		actual.CleanupOwnership != expected.CleanupOwnership ||
		!sameMaterializedFiles(actual.SelectedFiles, expected.SelectedFiles) {
		return fmt.Errorf("%w: supplied materialization is not bound to the bundle result", apgfootprint.ErrInvalidRecord)
	}
	return nil
}

func sameMaterializedFiles(left, right []MaterializedFile) bool {
	if len(left) != len(right) {
		return false
	}
	for index := range left {
		if left[index] != right[index] {
			return false
		}
	}
	return true
}

func footprintSources(request BundleRequest, result BundleResult, manifestJSON []byte) ([]apgfootprint.SourceReference, error) {
	requestJSON, err := request.CanonicalJSON()
	if err != nil {
		return nil, fmt.Errorf("%w: request source identity: %v", apgfootprint.ErrInvalidRecord, err)
	}
	resultJSON, err := result.CanonicalJSON()
	if err != nil {
		return nil, fmt.Errorf("%w: result source identity: %v", apgfootprint.ErrInvalidRecord, err)
	}
	metadata, err := Metadata()
	if err != nil {
		return nil, fmt.Errorf("%w: corpus source identity: %v", apgfootprint.ErrInvalidRecord, err)
	}
	if metadata.Fingerprint != result.EmbeddedCorpusFingerprint {
		return nil, fmt.Errorf("%w: result corpus identity is stale", apgfootprint.ErrInvalidRecord)
	}
	rulesJSON, err := canonicalJSON(SelectionRules())
	if err != nil {
		return nil, fmt.Errorf("%w: rule source identity: %v", apgfootprint.ErrInvalidRecord, err)
	}
	compositionJSON, err := canonicalJSON(CompositionRules())
	if err != nil {
		return nil, fmt.Errorf("%w: composition source identity: %v", apgfootprint.ErrInvalidRecord, err)
	}
	registry := apgfootprint.DefaultComponentRegistry()
	registryJSON, err := registry.CanonicalJSON()
	if err != nil {
		return nil, fmt.Errorf("%w: component registry identity: %v", apgfootprint.ErrInvalidRecord, err)
	}
	mapping := apgfootprint.DefaultControlMapping()
	mappingJSON, err := mapping.CanonicalJSON()
	if err != nil {
		return nil, fmt.Errorf("%w: capacity mapping identity: %v", apgfootprint.ErrInvalidRecord, err)
	}

	sources := []apgfootprint.SourceReference{
		byteSource("apg:skill-bundle-request/"+BundleRequestSchemaV1, "application/json", requestJSON),
		byteSource("apg:skill-bundle-result/"+BundleResultSchemaV1+"/"+result.BundleFingerprint, "application/json", resultJSON),
		byteSource("apg:skill-corpus/"+result.EmbeddedCorpusFingerprint, "application/json", metadata.ManifestJSON),
		byteSource("apg:skill-selection-rules/"+result.RuleTableVersion, "application/json", rulesJSON),
		byteSource("apg:skill-composition-rules/"+result.CompositionRuleVersion, "application/json", compositionJSON),
		byteSource("apg:skill-bundle-manifest/"+result.BundleFingerprint, "application/json", manifestJSON),
		byteSource("apg:context-component-registry/"+apgfootprint.ComponentRegistrySchemaV1+"/"+registry.Fingerprint(), "application/json", registryJSON),
		byteSource("apg:capacity-control-mapping/"+apgfootprint.ControlMappingSchemaV1+"/"+mapping.Fingerprint(), "application/json", mappingJSON),
		identitySource("apg:context-footprint/schema", apgfootprint.FootprintSchemaV1),
		identitySource("apg:context-projection/schema", apgfootprint.ProjectionSchemaV1),
		identitySource("apg:context-footprint/serializer", footprintSerializerIdentity),
		identitySource("apg:context-footprint/digest/record", footprintRecordDigest),
		identitySource("apg:context-footprint/digest/comparison", footprintComparisonDigest),
		identitySource("apg:context-footprint/digest/projection", footprintProjectionDigest),
	}
	return sources, nil
}

func byteSource(uri, mediaType string, content []byte) apgfootprint.SourceReference {
	return apgfootprint.SourceReference{
		Digest:    "sha256:" + sha256Hex(content),
		MediaType: mediaType,
		Size:      int64(len(content)),
		URI:       uri,
	}
}

func identitySource(uri, identity string) apgfootprint.SourceReference {
	return byteSource(uri, "text/plain", []byte(identity))
}

func footprintContextError(ctx context.Context) error {
	if ctx == nil {
		return nil
	}
	if err := ctx.Err(); err != nil {
		return fmt.Errorf("%w: %w", apgfootprint.ErrContextCancelled, err)
	}
	return nil
}
