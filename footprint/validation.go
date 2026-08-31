package footprint

import (
	"fmt"
	"sort"
	"strings"
	"unicode/utf8"
)

// The registry and mapping are deliberately kept as code-owned values.  A
// caller can read their canonical representations, but cannot extend the
// vocabulary used by first-party measurements by mutating a package global.
var componentControls = map[ComponentKind]string{
	ComponentCanonicalDescription: string(ControlCorpusIntegrity),
	ComponentSelectedDescription:  string(ControlSelectedDiscovery),
	ComponentSelectedBody:         string(ControlSelectedBody),
	ComponentSupportMaterial:      string(ControlSupportMaterial),
	ComponentMaterializedBundle:   string(ControlMaterializedBundle),
	ComponentPromptOverhead:       string(ControlPromptOverhead),
	ComponentDescription:          string(ControlCorpusIntegrity),
	ComponentBody:                 string(ControlSelectedBody),
	ComponentSupport:              string(ControlSupportMaterial),
	ComponentBundle:               string(ControlMaterializedBundle),
	ComponentAuthority:            string(ControlConsequence),
	ComponentSecurity:             string(ControlConsequence),
	ComponentFailure:              string(ControlConsequence),
	ComponentDiagnostic:           string(ControlConsequence),
	ComponentFinding:              string(ControlConsequence),
	ComponentRefusal:              string(ControlConsequence),
	ComponentUncertainty:          string(ControlConsequence),
	ComponentUnavailable:          string(ControlConsequence),
	ComponentSensitivity:          string(ControlConsequence),
	ComponentRetention:            string(ControlConsequence),
}

var componentKinds = []ComponentKind{
	ComponentCanonicalDescription,
	ComponentSelectedDescription,
	ComponentSelectedBody,
	ComponentSupportMaterial,
	ComponentMaterializedBundle,
	ComponentPromptOverhead,
	ComponentDescription,
	ComponentBody,
	ComponentSupport,
	ComponentBundle,
	ComponentAuthority,
	ComponentSecurity,
	ComponentFailure,
	ComponentDiagnostic,
	ComponentFinding,
	ComponentRefusal,
	ComponentUncertainty,
	ComponentUnavailable,
	ComponentSensitivity,
	ComponentRetention,
}

var consequenceKinds = map[ComponentKind]struct{}{
	ComponentAuthority:   {},
	ComponentSecurity:    {},
	ComponentFailure:     {},
	ComponentDiagnostic:  {},
	ComponentFinding:     {},
	ComponentRefusal:     {},
	ComponentUncertainty: {},
	ComponentUnavailable: {},
	ComponentSensitivity: {},
	ComponentRetention:   {},
}

var knownBases = map[ObservationBasis]struct{}{
	ObservationBasisDirectMeasurement: {},
	ObservationBasisModeledEstimate:   {},
	ObservationBasisImportedTelemetry: {},
	ObservationBasisDeclaredMetadata:  {},
}

var knownDesigns = map[StudyDesign]struct{}{
	StudyDesignSingleRun:             {},
	StudyDesignPairedAB:              {},
	StudyDesignMultiRepetitionSample: {},
	StudyDesignSyntheticBenchmark:    {},
}

var knownQualities = map[QualityStatus]struct{}{
	QualityVerified:    {},
	QualityProvisional: {},
	QualityDegraded:    {},
	QualityUnvalidated: {},
}

var knownAvailabilities = map[Availability]struct{}{
	Available:   {},
	Unavailable: {},
}

var knownUnits = map[Unit]struct{}{
	UnitBytes:                {},
	UnitCharacters:           {},
	UnitTokensTiktokenCL100k: {},
	UnitTokensTiktokenO200k:  {},
	UnitTokensGemini:         {},
	UnitTokensClaude:         {},
}

var knownSensitivities = map[Sensitivity]int{
	SensitivityPublic:       0,
	SensitivityInternal:     1,
	SensitivityConfidential: 2,
	SensitivityRestricted:   3,
}

var knownRetentions = map[Retention]int{
	RetentionEphemeral:  0,
	RetentionTaskScoped: 1,
	RetentionRetained:   2,
	RetentionImmutable:  3,
}

var knownFidelities = map[Fidelity]struct{}{
	FidelityExact:              {},
	FidelityLosslessStructural: {},
	FidelitySummarizedLossy:    {},
}

func invalid(kind, cause error, format string, args ...any) error {
	message := fmt.Sprintf(format, args...)
	if cause == nil {
		return fmt.Errorf("%w: %s", kind, message)
	}
	return fmt.Errorf("%w: %w: %s", kind, cause, message)
}

func invalidValue(cause error, format string, args ...any) error {
	return invalid(ErrInvalidRecord, cause, format, args...)
}

func validString(value string, name string, allowEmpty bool) error {
	if !utf8.ValidString(value) {
		return fmt.Errorf("%w: %s", ErrInvalidUTF8, name)
	}
	if !allowEmpty && value == "" {
		return fmt.Errorf("%w: %s", ErrMissingField, name)
	}
	if strings.IndexByte(value, 0) >= 0 {
		return fmt.Errorf("%w: %s contains NUL", ErrInvalidType, name)
	}
	return nil
}

func validateObservation(observation Observation) error {
	if _, ok := knownBases[observation.Basis]; !ok {
		return invalidValue(ErrUnknownVocabulary, "unknown observation basis %q", observation.Basis)
	}
	if _, ok := knownAvailabilities[observation.Availability]; !ok {
		return invalidValue(ErrUnknownVocabulary, "unknown observation availability %q", observation.Availability)
	}
	if _, ok := knownDesigns[observation.StudyDesign]; !ok {
		return invalidValue(ErrUnknownVocabulary, "unknown study design %q", observation.StudyDesign)
	}
	if _, ok := knownQualities[observation.Quality]; !ok {
		return invalidValue(ErrUnknownVocabulary, "unknown quality status %q", observation.Quality)
	}
	if observation.Repetitions <= 0 {
		return invalidValue(ErrInvalidType, "repetitions must be positive")
	}
	for name, value := range map[string]string{
		"harness":   observation.Harness,
		"method":    observation.Method,
		"provider":  observation.Provider,
		"tokenizer": observation.Tokenizer,
		"variant":   observation.Variant,
		"workload":  observation.Workload,
	} {
		if err := validString(value, name, false); err != nil {
			return invalidValue(err, "invalid observation %s", name)
		}
	}
	for _, exclusion := range observation.Exclusions {
		if err := validString(exclusion, "exclusion", false); err != nil {
			return invalidValue(err, "invalid observation exclusion")
		}
	}
	return nil
}

func validateMetric(metric Metric) error {
	if _, ok := knownAvailabilities[metric.Availability]; !ok {
		return invalidValue(ErrUnknownVocabulary, "unknown metric availability %q", metric.Availability)
	}
	if _, ok := knownUnits[metric.Unit]; !ok {
		return invalidValue(ErrUnknownVocabulary, "unknown metric unit %q", metric.Unit)
	}
	if err := validString(metric.Reason, "metric reason", true); err != nil {
		return invalidValue(err, "invalid metric reason")
	}
	switch metric.Availability {
	case Available:
		if metric.Value == nil {
			return invalidValue(ErrInvalidType, "available metric has no integer value")
		}
		if *metric.Value < 0 {
			return invalidValue(ErrInvalidType, "available metric value is negative")
		}
	case Unavailable:
		if metric.Value != nil {
			return invalidValue(ErrUnavailableMetric, "unavailable metric must not have a value")
		}
		if metric.Reason == "" {
			return invalidValue(ErrUnavailableMetric, "unavailable metric has no reason")
		}
	}
	return nil
}

func validateComponent(component Component) error {
	if err := validString(component.Name, "component name", false); err != nil {
		return invalidValue(err, "invalid component name")
	}
	if _, ok := componentControls[component.Kind]; !ok {
		return invalidValue(ErrUnknownVocabulary, "unknown component kind %q", component.Kind)
	}
	expected := componentControls[component.Kind]
	if component.ControlIdentity != expected {
		return invalidValue(ErrUnknownMapping, "component %q uses control %q, want %q", component.Kind, component.ControlIdentity, expected)
	}
	if err := validateMetric(component.Metric); err != nil {
		return err
	}
	return nil
}

func sourceReferenceKey(reference SourceReference) string {
	return fmt.Sprintf("%s\x00%s\x00%d\x00%s", reference.URI, reference.Digest, reference.Size, reference.MediaType)
}

func validateSourceReference(reference SourceReference) error {
	for name, value := range map[string]string{
		"source reference digest":     reference.Digest,
		"source reference media_type": reference.MediaType,
		"source reference uri":        reference.URI,
	} {
		if err := validString(value, name, false); err != nil {
			return invalidValue(err, "invalid source reference")
		}
	}
	if reference.Size < 0 {
		return invalidValue(ErrInvalidType, "source reference size is negative")
	}
	return nil
}

func validateRecord(record Record) error {
	if record.SchemaVersion != FootprintSchemaV1 {
		return invalid(ErrInvalidRecord, ErrUnknownSchema, "unsupported schema version %q", record.SchemaVersion)
	}
	if err := validateObservation(record.Observation); err != nil {
		return err
	}
	if len(record.Components) == 0 {
		return invalidValue(ErrMissingField, "record must contain at least one component")
	}
	seenComponents := make(map[string]struct{}, len(record.Components))
	for _, component := range record.Components {
		if err := validateComponent(component); err != nil {
			return err
		}
		key := fmt.Sprintf("%s\x00%s\x00%s", component.ControlIdentity, component.Kind, component.Name)
		if _, exists := seenComponents[key]; exists {
			return invalidValue(ErrDuplicateField, "record contains duplicate component")
		}
		seenComponents[key] = struct{}{}
	}
	seenReferences := make(map[string]struct{}, len(record.SourceReferences))
	for _, reference := range record.SourceReferences {
		if err := validateSourceReference(reference); err != nil {
			return err
		}
		key := sourceReferenceKey(reference)
		if _, exists := seenReferences[key]; exists {
			return invalidValue(ErrDuplicateField, "record contains duplicate source reference")
		}
		seenReferences[key] = struct{}{}
	}
	if _, ok := knownSensitivities[record.Sensitivity]; !ok {
		return invalidValue(ErrUnknownVocabulary, "unknown sensitivity %q", record.Sensitivity)
	}
	if _, ok := knownRetentions[record.Retention]; !ok {
		return invalidValue(ErrUnknownVocabulary, "unknown retention %q", record.Retention)
	}
	return nil
}

func observationsCompatible(control, treatment Observation) bool {
	left := normalizeObservation(control)
	right := normalizeObservation(treatment)
	// Variant is the treatment identity. Every other observation dimension is
	// part of the matched workload/design and must be byte-for-byte compatible.
	left.Variant = ""
	right.Variant = ""
	return equalObservation(left, right)
}

func equalObservation(left, right Observation) bool {
	if left.Basis != right.Basis || left.Availability != right.Availability || left.Harness != right.Harness || left.Method != right.Method || left.Provider != right.Provider || left.Quality != right.Quality || left.Repetitions != right.Repetitions || left.StudyDesign != right.StudyDesign || left.Tokenizer != right.Tokenizer || left.Variant != right.Variant || left.Workload != right.Workload {
		return false
	}
	if len(left.Exclusions) != len(right.Exclusions) {
		return false
	}
	for index := range left.Exclusions {
		if left.Exclusions[index] != right.Exclusions[index] {
			return false
		}
	}
	return true
}

func validateSelector(selector ComponentSelector) error {
	if err := validString(selector.Name, "component selector name", false); err != nil {
		return invalid(ErrInvalidComparison, err, "invalid comparison component selector")
	}
	if _, ok := componentControls[selector.Kind]; !ok {
		return invalid(ErrInvalidComparison, ErrUnknownVocabulary, "unknown comparison component kind %q", selector.Kind)
	}
	if selector.ControlIdentity != componentControls[selector.Kind] {
		return invalid(ErrInvalidComparison, ErrUnknownMapping, "unknown comparison component mapping")
	}
	return nil
}

func validateComparison(comparison Comparison) error {
	if comparison.SchemaVersion != ComparisonSchemaV1 {
		return invalid(ErrInvalidComparison, ErrUnknownSchema, "unsupported comparison schema version %q", comparison.SchemaVersion)
	}
	if err := validateSelector(comparison.Component); err != nil {
		return err
	}
	for label, side := range map[string]ComparisonObservation{"control": comparison.Control, "treatment": comparison.Treatment} {
		if !isDigest(side.RecordDigest, "fp-sha256:") {
			return invalid(ErrInvalidComparison, ErrInvalidType, "%s record digest is invalid", label)
		}
		if err := validateObservation(side.Observation); err != nil {
			return invalid(ErrInvalidComparison, err, "%s observation is invalid", label)
		}
		if err := validateMetric(side.Metric); err != nil {
			return invalid(ErrInvalidComparison, err, "%s metric is invalid", label)
		}
	}
	if !observationsCompatible(comparison.Control.Observation, comparison.Treatment.Observation) {
		return invalid(ErrInvalidComparison, ErrIncompatibleComparison, "observations are not compatible")
	}
	if comparison.Control.Metric.Availability != Available || comparison.Treatment.Metric.Availability != Available {
		return invalid(ErrInvalidComparison, ErrUnavailableMetric, "comparison requires two available metrics")
	}
	if comparison.Control.Metric.Unit != comparison.Treatment.Metric.Unit || comparison.Unit != comparison.Control.Metric.Unit {
		return invalid(ErrInvalidComparison, ErrUnitMismatch, "comparison metric units do not match")
	}
	if comparison.Control.Metric.Value == nil || comparison.Treatment.Metric.Value == nil {
		return invalid(ErrInvalidComparison, ErrUnavailableMetric, "comparison metric value is absent")
	}
	if comparison.Delta != *comparison.Treatment.Metric.Value-*comparison.Control.Metric.Value {
		// The subtraction is checked by Compare; this branch only guards a
		// forged comparison passed to CanonicalJSON.
		return invalid(ErrInvalidComparison, ErrInvalidType, "comparison delta does not match metrics")
	}
	return nil
}

func validateProjection(projection Projection) error {
	if projection.SchemaVersion != ProjectionSchemaV1 {
		return invalid(ErrInvalidProjection, ErrUnknownSchema, "unsupported projection schema version %q", projection.SchemaVersion)
	}
	if projection.CanonicalSourceSchema != FootprintSchemaV1 {
		return invalid(ErrInvalidProjection, ErrUnknownSchema, "unsupported canonical source schema %q", projection.CanonicalSourceSchema)
	}
	if !isDigest(projection.CanonicalSourceDigest, "fp-sha256:") {
		return invalid(ErrInvalidProjection, ErrInvalidType, "canonical source digest is invalid")
	}
	if projection.CanonicalSourceSize <= 0 {
		return invalid(ErrInvalidProjection, ErrInvalidType, "canonical source size must be positive")
	}
	if _, ok := knownFidelities[projection.Fidelity]; !ok {
		return invalid(ErrInvalidProjection, ErrUnknownVocabulary, "unknown projection fidelity %q", projection.Fidelity)
	}
	if err := validateRecord(projection.Record); err != nil {
		return invalid(ErrInvalidProjection, err, "projected record is invalid")
	}
	if _, ok := knownSensitivities[projection.Sensitivity]; !ok {
		return invalid(ErrInvalidProjection, ErrUnknownVocabulary, "unknown projection sensitivity %q", projection.Sensitivity)
	}
	if _, ok := knownRetentions[projection.Retention]; !ok {
		return invalid(ErrInvalidProjection, ErrUnknownVocabulary, "unknown projection retention %q", projection.Retention)
	}
	if knownSensitivities[projection.Sensitivity] < knownSensitivities[projection.Record.Sensitivity] {
		return invalid(ErrInvalidProjection, ErrSensitivityDowngrade, "projection sensitivity is lower than record sensitivity")
	}
	if knownRetentions[projection.Retention] < knownRetentions[projection.Record.Retention] {
		return invalid(ErrInvalidProjection, ErrRetentionDowngrade, "projection retention is lower than record retention")
	}
	seen := make(map[string]struct{}, len(projection.OmittedFields))
	for _, field := range projection.OmittedFields {
		if err := validString(field, "omitted field", false); err != nil {
			return invalid(ErrInvalidProjection, err, "invalid omitted field")
		}
		if _, exists := seen[field]; exists {
			return invalid(ErrInvalidProjection, ErrDuplicateField, "duplicate omitted field %q", field)
		}
		seen[field] = struct{}{}
		if protectedOmission(field) {
			return invalid(ErrInvalidProjection, ErrConsequenceBearingOmissionRefused, "omission of %q is refused", field)
		}
	}
	if projection.Fidelity == FidelityExact && len(projection.OmittedFields) != 0 {
		return invalid(ErrInvalidProjection, ErrInvalidType, "exact projection cannot omit fields")
	}
	if projection.Fidelity == FidelityLosslessStructural && len(projection.OmittedFields) != 0 {
		return invalid(ErrInvalidProjection, ErrInvalidType, "lossless structural projection cannot omit components")
	}
	return nil
}

func validateRegistry(registry ComponentRegistry) error {
	if registry.SchemaVersion != ComponentRegistrySchemaV1 {
		return invalid(ErrInvalidRegistry, ErrUnknownSchema, "unsupported component registry schema version %q", registry.SchemaVersion)
	}
	if len(registry.Components) != len(componentKinds) {
		return invalid(ErrInvalidRegistry, ErrUnknownVocabulary, "component registry does not contain the complete vocabulary")
	}
	seen := make(map[ComponentKind]struct{}, len(registry.Components))
	for _, definition := range registry.Components {
		if _, ok := componentControls[definition.Kind]; !ok {
			return invalid(ErrInvalidRegistry, ErrUnknownVocabulary, "unknown component kind %q", definition.Kind)
		}
		if definition.ControlIdentity != componentControls[definition.Kind] {
			return invalid(ErrInvalidRegistry, ErrUnknownMapping, "unknown control mapping for %q", definition.Kind)
		}
		if _, exists := seen[definition.Kind]; exists {
			return invalid(ErrInvalidRegistry, ErrDuplicateField, "duplicate component kind %q", definition.Kind)
		}
		seen[definition.Kind] = struct{}{}
	}
	for _, kind := range componentKinds {
		if _, ok := seen[kind]; !ok {
			return invalid(ErrInvalidRegistry, ErrUnknownVocabulary, "missing component kind %q", kind)
		}
	}
	return nil
}

func validateControlMapping(mapping ControlMapping) error {
	if mapping.SchemaVersion != ControlMappingSchemaV1 {
		return invalid(ErrInvalidControlMapping, ErrUnknownSchema, "unsupported control mapping schema version %q", mapping.SchemaVersion)
	}
	if len(mapping.Mappings) != len(componentKinds) {
		return invalid(ErrInvalidControlMapping, ErrUnknownMapping, "control mapping does not contain the complete mapping")
	}
	seen := make(map[ComponentKind]struct{}, len(mapping.Mappings))
	for _, entry := range mapping.Mappings {
		if _, ok := componentControls[entry.ComponentKind]; !ok {
			return invalid(ErrInvalidControlMapping, ErrUnknownVocabulary, "unknown component kind %q", entry.ComponentKind)
		}
		if entry.ControlIdentity != componentControls[entry.ComponentKind] {
			return invalid(ErrInvalidControlMapping, ErrUnknownMapping, "unknown control mapping for %q", entry.ComponentKind)
		}
		if _, exists := seen[entry.ComponentKind]; exists {
			return invalid(ErrInvalidControlMapping, ErrDuplicateField, "duplicate mapping for %q", entry.ComponentKind)
		}
		seen[entry.ComponentKind] = struct{}{}
	}
	for _, kind := range componentKinds {
		if _, ok := seen[kind]; !ok {
			return invalid(ErrInvalidControlMapping, ErrUnknownMapping, "missing mapping for %q", kind)
		}
	}
	return nil
}

func sortedComponentKinds() []ComponentKind {
	result := append([]ComponentKind(nil), componentKinds...)
	sort.Slice(result, func(i, j int) bool { return result[i] < result[j] })
	return result
}

func isConsequenceKind(kind ComponentKind) bool {
	_, ok := consequenceKinds[kind]
	return ok
}
