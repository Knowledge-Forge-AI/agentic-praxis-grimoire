package footprint

import (
	"context"
	"sort"
	"strings"
)

// Project creates a source-bound derived record.  The source fingerprint and
// canonical byte length are retained even when explicitly permitted material
// is omitted.  Consequence-bearing components and labels are never omitted.
func Project(ctx context.Context, request ProjectRequest) (Projection, error) {
	if err := contextError(ctx); err != nil {
		return Projection{}, err
	}
	if err := validateRecord(request.Source); err != nil {
		return Projection{}, invalid(ErrInvalidProjection, err, "projection source is invalid")
	}
	if _, ok := knownFidelities[request.Fidelity]; !ok {
		return Projection{}, invalid(ErrInvalidProjection, ErrUnknownVocabulary, "unknown projection fidelity %q", request.Fidelity)
	}
	omitted, err := requestedOmissions(request)
	if err != nil {
		return Projection{}, err
	}
	if request.Fidelity == FidelityExact && len(omitted) > 0 {
		return Projection{}, invalid(ErrInvalidProjection, ErrInvalidType, "exact projection cannot omit fields")
	}
	if request.Fidelity == FidelityLosslessStructural && len(omitted) > 0 {
		return Projection{}, invalid(ErrInvalidProjection, ErrInvalidType, "lossless structural projection cannot omit components")
	}
	for _, field := range omitted {
		if protectedOmission(field) {
			return Projection{}, invalid(ErrInvalidProjection, ErrConsequenceBearingOmissionRefused, "omission of %q is refused", field)
		}
	}

	sourceCanonical, err := request.Source.CanonicalJSON()
	if err != nil {
		return Projection{}, err
	}
	sourceDigest := domainFingerprint("fp-sha256:", FootprintSchemaV1, sourceCanonical)
	projected := normalizeRecord(request.Source)
	kept := projected.Components[:0]
	for _, component := range projected.Components {
		if err := contextError(ctx); err != nil {
			return Projection{}, err
		}
		omit := componentOmitted(component, omitted)
		if omit && isConsequenceKind(component.Kind) {
			return Projection{}, invalid(ErrInvalidProjection, ErrConsequenceBearingOmissionRefused, "omission of consequence-bearing component %q is refused", component.Kind)
		}
		if !omit {
			kept = append(kept, component)
		}
	}
	if len(kept) == 0 {
		return Projection{}, invalid(ErrInvalidProjection, ErrInvalidType, "projection must retain at least one component")
	}
	projected.Components = kept

	sensitivity, err := projectionSensitivity(request.Source.Sensitivity, request.Sensitivity)
	if err != nil {
		return Projection{}, err
	}
	retention, err := projectionRetention(request.Source.Retention, request.Retention)
	if err != nil {
		return Projection{}, err
	}
	projected.Sensitivity = sensitivity
	projected.Retention = retention
	projection := Projection{
		SchemaVersion:         ProjectionSchemaV1,
		CanonicalSourceDigest: sourceDigest,
		CanonicalSourceSchema: FootprintSchemaV1,
		CanonicalSourceSize:   int64(len(sourceCanonical)),
		Fidelity:              request.Fidelity,
		OmittedFields:         omitted,
		Record:                projected,
		Sensitivity:           sensitivity,
		Retention:             retention,
	}
	if err := contextError(ctx); err != nil {
		return Projection{}, err
	}
	if err := validateProjection(projection); err != nil {
		return Projection{}, err
	}
	return normalizeProjection(projection), nil
}

func requestedOmissions(request ProjectRequest) ([]string, error) {
	omittedSet := make(map[string]struct{}, len(request.OmittedFields))
	omissionsSet := make(map[string]struct{}, len(request.Omissions))
	for _, field := range request.OmittedFields {
		if err := validString(field, "omitted field", false); err != nil {
			return nil, invalid(ErrInvalidProjection, err, "invalid omitted field")
		}
		if _, exists := omittedSet[field]; exists {
			return nil, invalid(ErrInvalidProjection, ErrDuplicateField, "duplicate omitted field %q", field)
		}
		omittedSet[field] = struct{}{}
	}
	for _, field := range request.Omissions {
		if err := validString(field, "omitted field", false); err != nil {
			return nil, invalid(ErrInvalidProjection, err, "invalid omitted field")
		}
		if _, exists := omissionsSet[field]; exists {
			return nil, invalid(ErrInvalidProjection, ErrDuplicateField, "duplicate omitted field %q", field)
		}
		omissionsSet[field] = struct{}{}
	}
	combined := make([]string, 0, len(omittedSet)+len(omissionsSet))
	for field := range omittedSet {
		combined = append(combined, field)
	}
	for field := range omissionsSet {
		if _, exists := omittedSet[field]; !exists {
			combined = append(combined, field)
		}
	}
	sort.Strings(combined)
	return combined, nil
}

func protectedOmission(field string) bool {
	normalized := field
	if strings.HasPrefix(normalized, "kind:") {
		normalized = strings.TrimPrefix(normalized, "kind:")
	}
	switch normalized {
	case "authority", "security", "failure", "diagnostic", "finding", "refusal", "uncertainty", "unavailable", "sensitivity", "retention":
		return true
	case "source_references", "observation", "components", "record", "canonical_source_digest", "canonical_source_schema", "canonical_source_size":
		// Source references, observation, and binding metadata are required to
		// keep a projection traceable. "components" is safe only when the
		// component loop below proves every retained component is ordinary;
		// the early refusal is conservative and fail-closed.
		return true
	default:
		return false
	}
}

func componentOmitted(component Component, omitted []string) bool {
	for _, field := range omitted {
		if field == component.Name || field == string(component.Kind) || field == "kind:"+string(component.Kind) {
			return true
		}
		if componentKindAlias(component.Kind) == field {
			return true
		}
	}
	return false
}

func componentKindAlias(kind ComponentKind) string {
	switch kind {
	case ComponentCanonicalDescription, ComponentSelectedDescription, ComponentDescription:
		return "description"
	case ComponentSelectedBody, ComponentBody:
		return "body"
	case ComponentSupportMaterial, ComponentSupport:
		return "support"
	case ComponentMaterializedBundle, ComponentBundle:
		return "bundle"
	case ComponentPromptOverhead:
		return "prompt_overhead"
	default:
		return ""
	}
}

func projectionSensitivity(source, requested Sensitivity) (Sensitivity, error) {
	if requested == "" {
		return source, nil
	}
	if _, ok := knownSensitivities[requested]; !ok {
		return "", invalid(ErrInvalidProjection, ErrUnknownVocabulary, "unknown projection sensitivity %q", requested)
	}
	if knownSensitivities[requested] < knownSensitivities[source] {
		return "", invalid(ErrInvalidProjection, ErrSensitivityDowngrade, "projection sensitivity is lower than source sensitivity")
	}
	return requested, nil
}

func projectionRetention(source, requested Retention) (Retention, error) {
	if requested == "" {
		return source, nil
	}
	if _, ok := knownRetentions[requested]; !ok {
		return "", invalid(ErrInvalidProjection, ErrUnknownVocabulary, "unknown projection retention %q", requested)
	}
	if knownRetentions[requested] < knownRetentions[source] {
		return "", invalid(ErrInvalidProjection, ErrRetentionDowngrade, "projection retention is lower than source retention")
	}
	return requested, nil
}

// ValidateProjection validates a projection without access to its original
// source bytes.  Source digest equality is therefore checked for shape and
// domain, while Project performs the authoritative source binding.
func ValidateProjection(projection Projection) error { return validateProjection(projection) }

// ValidateRecord validates a record in memory.
func ValidateRecord(record Record) error { return validateRecord(record) }

// ValidateComparison validates a comparison in memory.
func ValidateComparison(comparison Comparison) error { return validateComparison(comparison) }

// ValidateComponentRegistry validates the complete component registry.
func ValidateComponentRegistry(registry ComponentRegistry) error { return validateRegistry(registry) }

// ValidateControlMapping validates the complete capacity-control mapping.
func ValidateControlMapping(mapping ControlMapping) error { return validateControlMapping(mapping) }
