package xoconsumer

import (
	"context"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/footprint"
	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/schema"
	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/skills"
)

const fixtureSourcePayload = "xo-adapter-fixture-source-v1"

// CallerSkillEvidence captures bounded skill selection evidence for the caller
// without leaking APGR domain types across the caller boundary.
type CallerSkillEvidence struct {
	SelectedSkillIDs  []string `json:"selected_skill_ids"`
	BundleFingerprint string   `json:"bundle_fingerprint"`
	SchemaVersion     string   `json:"schema_version"`
}

// CallerComponentEvidence captures a single footprint component's observation facts
// without leaking APGR domain types across the caller boundary.
type CallerComponentEvidence struct {
	Kind         string `json:"kind"`
	Name         string `json:"name"`
	Unit         string `json:"unit"`
	Availability string `json:"availability"`
	Value        *int64 `json:"value,omitempty"`
	Reason       string `json:"reason,omitempty"`
}

// CallerSourceReference captures source reference metadata
// without leaking APGR domain types across the caller boundary.
type CallerSourceReference struct {
	URI       string `json:"uri"`
	Digest    string `json:"digest"`
	MediaType string `json:"media_type"`
	Size      int64  `json:"size"`
}

// CallerFootprintEvidence captures bounded footprint metrics for the caller
// without leaking APGR domain types across the caller boundary.
type CallerFootprintEvidence struct {
	RecordFingerprint     string                    `json:"record_fingerprint"`
	SchemaVersion         string                    `json:"schema_version"`
	MetricCount           int                       `json:"metric_count"`
	Components            []CallerComponentEvidence `json:"components"`
	SourceReferences      []CallerSourceReference   `json:"source_references,omitempty"`
	ObservationBasis      string                    `json:"observation_basis,omitempty"`
	ObservationHarness    string                    `json:"observation_harness,omitempty"`
	ObservationExclusions []string                  `json:"observation_exclusions,omitempty"`
}

// CallerComparisonDelta captures footprint delta between two measurements
// without leaking APGR domain types across the caller boundary.
type CallerComparisonDelta struct {
	ComparisonSchema     string `json:"comparison_schema"`
	BaselineFingerprint  string `json:"baseline_fingerprint"`
	CandidateFingerprint string `json:"candidate_fingerprint"`
	ComponentKind        string `json:"component_kind"`
	ComponentName        string `json:"component_name"`
	Delta                int64  `json:"delta"`
	Unit                 string `json:"unit"`
}

// CallerProjectionEvidence captures factual source binding and projection properties
// without leaking APGR domain types across the caller boundary.
type CallerProjectionEvidence struct {
	ProjectionFingerprint string   `json:"projection_fingerprint"`
	ProjectionSchema      string   `json:"projection_schema"`
	CanonicalSourceDigest string   `json:"canonical_source_digest"`
	CanonicalSourceSchema string   `json:"canonical_source_schema"`
	CanonicalSourceSize   int64    `json:"canonical_source_size"`
	Fidelity              string   `json:"fidelity"`
	OmittedFields         []string `json:"omitted_fields"`
	Sensitivity           string   `json:"sensitivity"`
	Retention             string   `json:"retention"`
	ProjectedRecordBytes  int64    `json:"projected_record_bytes"`
}

// XOAdapter is a caller-owned adapter that invokes public APGR libraries
// and translates results into caller-owned DTOs without leaking APGR types.
type XOAdapter struct{}

// NewXOAdapter returns an instantiated caller adapter.
func NewXOAdapter() *XOAdapter {
	return &XOAdapter{}
}

func buildSkillBundleRequest(explicitSkillIDs []string, maxDescriptionBytes *int64) skills.BundleRequest {
	req := skills.BundleRequest{
		SchemaVersion:    skills.BundleRequestSchemaV1,
		ExplicitSkillIDs: explicitSkillIDs,
		Consumer: skills.Consumer{
			Kind:                skills.ConsumerGo,
			MaterializationForm: skills.MaterializationInMemory,
			ProviderConstraints: []string{"in_process_library"},
		},
	}
	if maxDescriptionBytes != nil {
		req.Budget.MaxDescriptionBytes = maxDescriptionBytes
	}
	return req
}

func translateRecordToCallerEvidence(rec footprint.Record) CallerFootprintEvidence {
	components := make([]CallerComponentEvidence, len(rec.Components))
	for i, comp := range rec.Components {
		var valPtr *int64
		if comp.Metric.Availability == footprint.Available && comp.Metric.Value != nil {
			v := *comp.Metric.Value
			valPtr = &v
		}
		components[i] = CallerComponentEvidence{
			Kind:         string(comp.Kind),
			Name:         comp.Name,
			Unit:         string(comp.Metric.Unit),
			Availability: string(comp.Metric.Availability),
			Value:        valPtr,
			Reason:       comp.Metric.Reason,
		}
	}

	sourceRefs := make([]CallerSourceReference, len(rec.SourceReferences))
	for i, ref := range rec.SourceReferences {
		sourceRefs[i] = CallerSourceReference{
			URI:       ref.URI,
			Digest:    ref.Digest,
			MediaType: ref.MediaType,
			Size:      ref.Size,
		}
	}

	exclusions := make([]string, len(rec.Observation.Exclusions))
	copy(exclusions, rec.Observation.Exclusions)

	return CallerFootprintEvidence{
		RecordFingerprint:     rec.Fingerprint(),
		SchemaVersion:         rec.SchemaVersion,
		MetricCount:           len(rec.Components),
		Components:            components,
		SourceReferences:      sourceRefs,
		ObservationBasis:      string(rec.Observation.Basis),
		ObservationHarness:    rec.Observation.Harness,
		ObservationExclusions: exclusions,
	}
}

func (a *XOAdapter) internalMeasure(ctx context.Context, variant string, bodyUnit footprint.Unit, bodyValue int64) (footprint.Record, error) {
	val := bodyValue
	return footprint.Measure(ctx, footprint.MeasureRequest{
		SchemaVersion: footprint.FootprintSchemaV1,
		Observation: footprint.Observation{
			Basis:        footprint.ObservationBasisDirectMeasurement,
			Availability: footprint.Available,
			Exclusions:   []string{"provider_prompt_overhead"},
			Harness:      "xo-adapter-fixture",
			Method:       "fixture-measurement",
			Provider:     "provider-neutral",
			Quality:      footprint.QualityVerified,
			Repetitions:  1,
			StudyDesign:  footprint.StudyDesignSingleRun,
			Tokenizer:    "not_applicable",
			Variant:      variant,
			Workload:     "multi_component_context",
		},
		Components: []footprint.ComponentInput{
			{
				Kind: footprint.ComponentSelectedDescription,
				Name: "selected_description",
				Unit: footprint.UnitCharacters,
				Text: "APGR-XO",
			},
			{
				Kind: footprint.ComponentSelectedBody,
				Name: "selected_body",
				Unit: bodyUnit,
				Metric: footprint.Metric{
					Availability: footprint.Available,
					Unit:         bodyUnit,
					Value:        &val,
				},
			},
			{
				Kind: footprint.ComponentPromptOverhead,
				Name: "provider_prompt_overhead",
				Unit: footprint.UnitTokensTiktokenCL100k,
				Metric: footprint.Metric{
					Availability: footprint.Unavailable,
					Reason:       "provider tokenizer is outside the adapter fixture",
					Unit:         footprint.UnitTokensTiktokenCL100k,
				},
			},
		},
		SourceReferences: []footprint.SourceReference{{
			Digest:    "sha256:" + schema.SHA256([]byte(fixtureSourcePayload)),
			MediaType: "text/plain",
			Size:      int64(len(fixtureSourcePayload)),
			URI:       "fixture://xo-adapter/source",
		}},
		Sensitivity: footprint.SensitivityPublic,
		Retention:   footprint.RetentionRetained,
	})
}

// ValidateSchemaCompatibility verifies that the underlying APGR report schema
// is compatible with the caller adapter envelope requirements.
func (a *XOAdapter) ValidateSchemaCompatibility() bool {
	return schema.EnvelopeVersion == 1 && schema.EnvelopeFormat == "agent-report-record"
}

// ResolveSkills resolves requested skill bundles and translates results to CallerSkillEvidence.
func (a *XOAdapter) ResolveSkills(ctx context.Context, explicitSkillIDs []string) (CallerSkillEvidence, error) {
	return a.ResolveSkillsWithMaxBytes(ctx, explicitSkillIDs, nil)
}

// ResolveSkillsWithMaxBytes resolves requested skill bundles with an optional byte budget constraint.
func (a *XOAdapter) ResolveSkillsWithMaxBytes(ctx context.Context, explicitSkillIDs []string, maxDescriptionBytes *int64) (CallerSkillEvidence, error) {
	req := buildSkillBundleRequest(explicitSkillIDs, maxDescriptionBytes)
	res, err := skills.Resolve(ctx, req)
	if err != nil {
		return CallerSkillEvidence{}, err
	}
	return CallerSkillEvidence{
		SelectedSkillIDs:  res.SelectedSkillIDs,
		BundleFingerprint: res.BundleFingerprint,
		SchemaVersion:     res.SchemaVersion,
	}, nil
}

// FootprintSkills measures the context footprint of resolved skills under context.
func (a *XOAdapter) FootprintSkills(ctx context.Context, explicitSkillIDs []string) (CallerFootprintEvidence, error) {
	req := buildSkillBundleRequest(explicitSkillIDs, nil)
	res, err := skills.Resolve(ctx, req)
	if err != nil {
		return CallerFootprintEvidence{}, err
	}
	rec, err := skills.FootprintContext(ctx, req, res)
	if err != nil {
		return CallerFootprintEvidence{}, err
	}
	return translateRecordToCallerEvidence(rec), nil
}

// MeasureFootprint measures context footprint for a given variant and byte size.
func (a *XOAdapter) MeasureFootprint(ctx context.Context, variant string, bodyBytes int64) (CallerFootprintEvidence, error) {
	rec, err := a.internalMeasure(ctx, variant, footprint.UnitBytes, bodyBytes)
	if err != nil {
		return CallerFootprintEvidence{}, err
	}
	return translateRecordToCallerEvidence(rec), nil
}

// CompareFootprints compares baseline and treatment measurements with support for unit mismatch testing.
func (a *XOAdapter) CompareFootprints(ctx context.Context, controlBytes, treatmentBytes int64, unitMismatch bool) (CallerComparisonDelta, error) {
	control, err := a.internalMeasure(ctx, "control", footprint.UnitBytes, controlBytes)
	if err != nil {
		return CallerComparisonDelta{}, err
	}
	treatmentUnit := footprint.UnitBytes
	if unitMismatch {
		treatmentUnit = footprint.UnitCharacters
	}
	treatment, err := a.internalMeasure(ctx, "treatment", treatmentUnit, treatmentBytes)
	if err != nil {
		return CallerComparisonDelta{}, err
	}

	comp, err := footprint.Compare(ctx, footprint.CompareRequest{
		Control:   control,
		Treatment: treatment,
		Component: footprint.ComponentSelector{
			ControlIdentity: footprint.ControlSelectedBody,
			Kind:            footprint.ComponentSelectedBody,
			Name:            "selected_body",
		},
	})
	if err != nil {
		return CallerComparisonDelta{}, err
	}

	return CallerComparisonDelta{
		ComparisonSchema:     comp.SchemaVersion,
		BaselineFingerprint:  control.Fingerprint(),
		CandidateFingerprint: treatment.Fingerprint(),
		ComponentKind:        string(comp.Component.Kind),
		ComponentName:        comp.Component.Name,
		Delta:                comp.Delta,
		Unit:                 string(comp.Unit),
	}, nil
}

// ProjectFootprint projects a footprint measurement with specified omitted fields.
func (a *XOAdapter) ProjectFootprint(ctx context.Context, bodyBytes int64, omittedFields []string) (CallerProjectionEvidence, error) {
	record, err := a.internalMeasure(ctx, "basis", footprint.UnitBytes, bodyBytes)
	if err != nil {
		return CallerProjectionEvidence{}, err
	}

	proj, err := footprint.Project(ctx, footprint.ProjectRequest{
		Source:        record,
		Fidelity:      footprint.FidelitySummarizedLossy,
		OmittedFields: omittedFields,
	})
	if err != nil {
		return CallerProjectionEvidence{}, err
	}

	recCanonical, err := proj.Record.CanonicalJSON()
	if err != nil {
		return CallerProjectionEvidence{}, err
	}

	return CallerProjectionEvidence{
		ProjectionFingerprint: proj.Fingerprint(),
		ProjectionSchema:      proj.SchemaVersion,
		CanonicalSourceDigest: proj.CanonicalSourceDigest,
		CanonicalSourceSchema: proj.CanonicalSourceSchema,
		CanonicalSourceSize:   proj.CanonicalSourceSize,
		Fidelity:              string(proj.Fidelity),
		OmittedFields:         proj.OmittedFields,
		Sensitivity:           string(proj.Sensitivity),
		Retention:             string(proj.Retention),
		ProjectedRecordBytes:  int64(len(recCanonical)),
	}, nil
}
