package footprint

import "context"

const (
	// Public schema identities. These strings are immutable wire identities.
	FootprintSchemaV1  = "apg.context-footprint/v1"
	ComparisonSchemaV1 = "apg.context-comparison/v1"
	ProjectionSchemaV1 = "apg.context-projection/v1"

	// Component and capacity-control registries are versioned independently.
	ComponentRegistrySchemaV1      = "apg.context-component-registry/v1"
	ControlMappingSchemaV1         = "apg.capacity-control-mapping/v1"
	CapacityControlMappingSchemaV1 = ControlMappingSchemaV1
)

// ObservationBasis describes how an observation was obtained.
type ObservationBasis string

const (
	ObservationBasisDirectMeasurement ObservationBasis = "direct_measurement"
	ObservationBasisModeledEstimate   ObservationBasis = "modeled_estimate"
	ObservationBasisImportedTelemetry ObservationBasis = "imported_telemetry"
	ObservationBasisDeclaredMetadata  ObservationBasis = "declared_metadata"

	BasisDirectMeasurement = ObservationBasisDirectMeasurement
	BasisModeledEstimate   = ObservationBasisModeledEstimate
	BasisImportedTelemetry = ObservationBasisImportedTelemetry
	BasisDeclaredMetadata  = ObservationBasisDeclaredMetadata
)

// StudyDesign identifies the experimental shape of an observation.
type StudyDesign string

const (
	StudyDesignSingleRun             StudyDesign = "single_run"
	StudyDesignPairedAB              StudyDesign = "paired_ab"
	StudyDesignMultiRepetitionSample StudyDesign = "multi_repetition_sample"
	StudyDesignSyntheticBenchmark    StudyDesign = "synthetic_benchmark"

	DesignSingleRun             = StudyDesignSingleRun
	DesignPairedAB              = StudyDesignPairedAB
	DesignMultiRepetitionSample = StudyDesignMultiRepetitionSample
	DesignSyntheticBenchmark    = StudyDesignSyntheticBenchmark
)

// QualityStatus states the evidence quality independently of its basis.
type QualityStatus string

const (
	QualityVerified    QualityStatus = "verified"
	QualityProvisional QualityStatus = "provisional"
	QualityDegraded    QualityStatus = "degraded"
	QualityUnvalidated QualityStatus = "unvalidated"
)

// Availability is deliberately binary. An unavailable metric has no value;
// absence is never represented as a zero value.
type Availability string

const (
	Available   Availability = "available"
	Unavailable Availability = "unavailable"
)

// Unit is the exact unit attached to an integer metric. Units are never
// converted implicitly by Compare.
type Unit string

const (
	UnitBytes                Unit = "bytes"
	UnitCharacters           Unit = "characters"
	UnitTokensTiktokenCL100k Unit = "tokens_tiktoken_cl100k"
	UnitTokensTiktokenO200k  Unit = "tokens_tiktoken_o200k"
	UnitTokensGemini         Unit = "tokens_gemini"
	UnitTokensClaude         Unit = "tokens_claude"
	MetricUnitBytes               = UnitBytes
	MetricUnitCharacters          = UnitCharacters
)

// Sensitivity is an ordered classification. Higher values are more
// restrictive and may be requested by a projection, but never downgraded.
type Sensitivity string

const (
	SensitivityPublic       Sensitivity = "public"
	SensitivityInternal     Sensitivity = "internal"
	SensitivityConfidential Sensitivity = "confidential"
	SensitivityRestricted   Sensitivity = "restricted"
)

// Retention is an ordered disposal/retention classification.
type Retention string

const (
	RetentionEphemeral  Retention = "ephemeral"
	RetentionTaskScoped Retention = "task_scoped"
	RetentionRetained   Retention = "retained"
	RetentionImmutable  Retention = "immutable"
)

// Fidelity describes how much of a canonical source a projection retains.
type Fidelity string

const (
	FidelityExact              Fidelity = "exact"
	FidelityLosslessStructural Fidelity = "lossless_structural"
	FidelitySummarizedLossy    Fidelity = "summarized_lossy"
)

// ComponentKind is the closed registry vocabulary for measurable material.
type ComponentKind string

const (
	ComponentCanonicalDescription ComponentKind = "canonical_description"
	ComponentSelectedDescription  ComponentKind = "selected_description"
	ComponentSelectedBody         ComponentKind = "selected_body"
	ComponentSupportMaterial      ComponentKind = "support_material"
	ComponentMaterializedBundle   ComponentKind = "materialized_bundle"
	ComponentPromptOverhead       ComponentKind = "prompt_overhead"
	ComponentDescription          ComponentKind = "description"
	ComponentBody                 ComponentKind = "body"
	ComponentSupport              ComponentKind = "support"
	ComponentBundle               ComponentKind = "bundle"
	ComponentAuthority            ComponentKind = "authority"
	ComponentSecurity             ComponentKind = "security"
	ComponentFailure              ComponentKind = "failure"
	ComponentDiagnostic           ComponentKind = "diagnostic"
	ComponentFinding              ComponentKind = "finding"
	ComponentRefusal              ComponentKind = "refusal"
	ComponentUncertainty          ComponentKind = "uncertainty"
	ComponentUnavailable          ComponentKind = "unavailable"
	ComponentSensitivity          ComponentKind = "sensitivity"
	ComponentRetention            ComponentKind = "retention"
)

// Stable control identities used by the built-in registry.
const (
	ControlCorpusIntegrity    = "apg.capacity-control/corpus-integrity/v1"
	ControlSelectedDiscovery  = "apg.capacity-control/selected-discovery/v1"
	ControlSelectedBody       = "apg.capacity-control/selected-body/v1"
	ControlSupportMaterial    = "apg.capacity-control/support-material/v1"
	ControlMaterializedBundle = "apg.capacity-control/materialized-bundle/v1"
	ControlPromptOverhead     = "apg.capacity-control/prompt-overhead/v1"
	ControlConsequence        = "apg.capacity-control/consequence-bearing/v1"
)

// Metric is one integer observation. Value is a pointer so that zero is a
// valid available measurement while an unavailable measurement has no value.
type Metric struct {
	Availability Availability `json:"availability"`
	Reason       string       `json:"reason,omitempty"`
	Unit         Unit         `json:"unit"`
	Value        *int64       `json:"value,omitempty"`
}

// Measurement is a compatibility alias for callers that use the architecture
// term rather than the wire term Component.
type Measurement = Component

// Component is one named measurable component and its control binding.
type Component struct {
	ControlIdentity string        `json:"control_identity"`
	Kind            ComponentKind `json:"kind"`
	Metric          Metric        `json:"metric"`
	Name            string        `json:"name"`
}

// Observation holds the dimensions shared by all components in a record.
type Observation struct {
	Basis        ObservationBasis `json:"basis"`
	Availability Availability     `json:"availability"`
	Exclusions   []string         `json:"exclusions"`
	Harness      string           `json:"harness"`
	Method       string           `json:"method"`
	Provider     string           `json:"provider"`
	Quality      QualityStatus    `json:"quality"`
	Repetitions  int64            `json:"repetitions"`
	StudyDesign  StudyDesign      `json:"study_design"`
	Tokenizer    string           `json:"tokenizer"`
	Variant      string           `json:"variant"`
	Workload     string           `json:"workload"`
}

// SourceReference binds a record to an exact source identity. URI is an
// identifier only; APGR does not fetch it.
type SourceReference struct {
	Digest    string `json:"digest"`
	MediaType string `json:"media_type"`
	Size      int64  `json:"size"`
	URI       string `json:"uri"`
}

// Record is the canonical APGR context-footprint record.
type Record struct {
	SchemaVersion    string            `json:"schema_version"`
	Observation      Observation       `json:"observation"`
	Components       []Component       `json:"components"`
	SourceReferences []SourceReference `json:"source_references"`
	Sensitivity      Sensitivity       `json:"sensitivity"`
	Retention        Retention         `json:"retention"`
}

// Footprint is a descriptive alias for Record.
type Footprint = Record

// ComponentSelector identifies one corresponding component in a comparison.
type ComponentSelector struct {
	ControlIdentity string        `json:"control_identity"`
	Kind            ComponentKind `json:"kind"`
	Name            string        `json:"name"`
}

// ComparisonObservation binds an exact record identity, shared observation,
// and selected metric into a comparison side.
type ComparisonObservation struct {
	RecordDigest string      `json:"record_digest"`
	Observation  Observation `json:"observation"`
	Metric       Metric      `json:"metric"`
}

// Comparison is a deterministic integer-only treatment-minus-control delta.
type Comparison struct {
	SchemaVersion string                `json:"schema_version"`
	Component     ComponentSelector     `json:"component"`
	Control       ComparisonObservation `json:"control"`
	Treatment     ComparisonObservation `json:"treatment"`
	Delta         int64                 `json:"delta"`
	Unit          Unit                  `json:"unit"`
}

// CompareRequest requests comparison of two records. When Component is empty,
// a single component in each record is selected. ComponentKind and
// ComponentName are convenience fields for callers that prefer flat input.
type CompareRequest struct {
	Control       Record
	Treatment     Record
	Component     ComponentSelector
	ComponentKind ComponentKind
	ComponentName string
}

// ComparisonRequest is an explicit-name alias.
type ComparisonRequest = CompareRequest

// Projection is a bounded derived record retaining source identity and loss
// disclosure. Record contains the retained canonical content.
type Projection struct {
	SchemaVersion         string      `json:"schema_version"`
	CanonicalSourceDigest string      `json:"canonical_source_digest"`
	CanonicalSourceSchema string      `json:"canonical_source_schema"`
	CanonicalSourceSize   int64       `json:"canonical_source_size"`
	Fidelity              Fidelity    `json:"fidelity"`
	OmittedFields         []string    `json:"omitted_fields"`
	Record                Record      `json:"record"`
	Sensitivity           Sensitivity `json:"sensitivity"`
	Retention             Retention   `json:"retention"`
}

// ProjectRequest requests a bounded projection. Omissions is a compatibility
// spelling; callers should use OmittedFields.
type ProjectRequest struct {
	Source        Record
	Fidelity      Fidelity
	OmittedFields []string
	Omissions     []string
	Sensitivity   Sensitivity
	Retention     Retention
}

// ProjectionRequest is an explicit-name alias.
type ProjectionRequest = ProjectRequest

// ComponentInput is the measurement input accepted by Measure. Data is
// measured in bytes or characters according to Unit; Metric can provide an
// already observed value or an unavailable state.
type ComponentInput struct {
	Kind            ComponentKind
	Name            string
	ControlIdentity string
	Unit            Unit
	Data            []byte
	Text            string
	Metric          Metric
}

// MeasureRequest describes one first-party measurement operation.
type MeasureRequest struct {
	SchemaVersion    string
	Observation      Observation
	Components       []ComponentInput
	SourceReferences []SourceReference
	Sensitivity      Sensitivity
	Retention        Retention
}

// MeasurementRequest is an alias for callers using the longer term.
type MeasurementRequest = MeasureRequest

// ComponentDefinition is one registry vocabulary entry.
type ComponentDefinition struct {
	Kind            ComponentKind `json:"kind"`
	ControlIdentity string        `json:"control_identity"`
}

// ComponentRegistry is the versioned closed component-kind registry.
type ComponentRegistry struct {
	SchemaVersion string                `json:"schema_version"`
	Components    []ComponentDefinition `json:"components"`
}

// ControlMappingEntry maps a component kind to one versioned APGR capacity
// control. The registry and mapping are independently versioned.
type ControlMappingEntry struct {
	ComponentKind   ComponentKind `json:"component_kind"`
	ControlIdentity string        `json:"control_identity"`
}

// ControlMapping is the canonical capacity-control mapping.
type ControlMapping struct {
	SchemaVersion string                `json:"schema_version"`
	Mappings      []ControlMappingEntry `json:"mappings"`
}

// CapacityControlMapping is a descriptive alias.
type CapacityControlMapping = ControlMapping

// Context-aware function signatures are asserted here to keep the public
// boundary visible to package consumers and future adapters.
var (
	_ func(context.Context, MeasureRequest) (Record, error)     = Measure
	_ func(context.Context, CompareRequest) (Comparison, error) = Compare
	_ func(context.Context, ProjectRequest) (Projection, error) = Project
)
