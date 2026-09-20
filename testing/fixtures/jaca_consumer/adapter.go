package jacaconsumer

import (
	"context"
	"fmt"
	"slices"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/candidate"
	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/evidence"
	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/phase"
	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/provider"
	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/routing"
)

// CallerPhaseRequest represents the consumer-owned request structure.
type CallerPhaseRequest struct {
	PhaseType string `json:"phase_type"`
	Prompt    string `json:"prompt"`
	Validated bool   `json:"validated"`
}

// CallerRouteSelection represents the consumer-owned route selection outcome.
type CallerRouteSelection struct {
	BindingID          string   `json:"binding_id"`
	Provider           string   `json:"provider"`
	Profile            string   `json:"profile"`
	EndpointAlias      string   `json:"endpoint_alias"`
	Capabilities       []string `json:"capabilities"`
	SelectionRationale string   `json:"selection_rationale"`
	UsedObservationIDs []string `json:"used_observation_ids"`
}

// CallerFindingEvidence captures consumer-owned review finding facts.
type CallerFindingEvidence struct {
	FindingID string `json:"finding_id"`
	Severity  string `json:"severity"`
	Category  string `json:"category"`
	Summary   string `json:"summary"`
	FilePath  string `json:"file_path,omitempty"`
	LineStart int    `json:"line_start,omitempty"`
	LineEnd   int    `json:"line_end,omitempty"`
}

// CallerFindingDisposition captures consumer-owned finding disposition facts.
type CallerFindingDisposition struct {
	FindingID string `json:"finding_id"`
	Action    string `json:"action"`
	Basis     string `json:"basis"`
	Rationale string `json:"rationale"`
}

// CallerCandidateSummary captures consumer-owned candidate facts.
type CallerCandidateSummary struct {
	CandidateID  string `json:"candidate_id"`
	Generation   int    `json:"generation"`
	ProducerRole string `json:"producer_role"`
	Commit       string `json:"commit,omitempty"`
	TreeDigest   string `json:"tree_digest,omitempty"`
}

// CallerArtifactRecord captures consumer-owned artifact facts.
type CallerArtifactRecord struct {
	ArtifactID   string `json:"artifact_id"`
	RelativePath string `json:"relative_path"`
	MediaType    string `json:"media_type"`
	ByteSize     int64  `json:"byte_size"`
	SHA256       string `json:"sha256"`
}

// CallerObservationFact captures consumer-owned operational observation digest facts.
type CallerObservationFact struct {
	ObservationID   string `json:"observation_id"`
	Producer        string `json:"producer"`
	ObservationType string `json:"observation_type"`
	Provider        string `json:"provider"`
	StateValue      string `json:"state_value"`
	CanonicalDigest string `json:"canonical_digest"`
}

// CallerConformanceSummary captures provider capability matrix facts.
type CallerConformanceSummary struct {
	RowCount          int      `json:"row_count"`
	SupportedFamilies []string `json:"supported_families"`
}

// ConsumerAdapter wraps public APGR Go libraries into consumer-owned operations.
type ConsumerAdapter struct{}

// NewConsumerAdapter creates a new ConsumerAdapter instance.
func NewConsumerAdapter() *ConsumerAdapter {
	return &ConsumerAdapter{}
}

// ParseAndValidateRequest strictly parses raw JSON bytes using phase.ParseRequestV2
// and returns a caller-owned CallerPhaseRequest.
func (a *ConsumerAdapter) ParseAndValidateRequest(ctx context.Context, raw []byte) (*CallerPhaseRequest, error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}

	req, err := phase.ParseRequestV2(raw)
	if err != nil {
		return nil, fmt.Errorf("consumer: request validation failed: %w", err)
	}

	return &CallerPhaseRequest{
		PhaseType: req.PhaseType,
		Prompt:    req.Prompt,
		Validated: true,
	}, nil
}

// ResolveTurnRoute maps consumer turn requirements into routing.ResolveRequest,
// resolves the route deterministically, and returns a caller-owned CallerRouteSelection.
func (a *ConsumerAdapter) ResolveTurnRoute(
	ctx context.Context,
	bindingID string,
	roles []string,
	phaseType string,
	catalog map[string]routing.EndpointCapabilities,
	observations []routing.OperationalObservation,
	priorRoutes map[string]CallerRouteSelection,
	now float64,
) (*CallerRouteSelection, error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}

	var semanticRoles []phase.SemanticRole
	for _, r := range roles {
		semanticRoles = append(semanticRoles, phase.SemanticRole(r))
	}

	binding, err := phase.NewActorBinding(bindingID, semanticRoles, "consumer_policy")
	if err != nil {
		return nil, fmt.Errorf("consumer: invalid actor binding: %w", err)
	}

	priorMap := make(map[string]routing.ResolvedActorRoute)
	for k, v := range priorRoutes {
		priorMap[k] = routing.ResolvedActorRoute{
			BindingID:     v.BindingID,
			Provider:      v.Provider,
			Profile:       v.Profile,
			EndpointAlias: v.EndpointAlias,
			Capabilities:  v.Capabilities,
			Roles:         []string{},
		}
	}

	route, err := phase.ResolveActorBindingRoute(ctx, binding, phaseType, catalog, observations, priorMap, now)
	if err != nil {
		return nil, fmt.Errorf("consumer: route resolution failed: %w", err)
	}

	return &CallerRouteSelection{
		BindingID:          route.BindingID,
		Provider:           route.Provider,
		Profile:            route.Profile,
		EndpointAlias:      route.EndpointAlias,
		Capabilities:       route.Capabilities,
		SelectionRationale: route.SelectionRationale,
		UsedObservationIDs: route.ObservationIDs,
	}, nil
}

// DigestObservation calculates the canonical digest of an operational observation
// and returns a caller-owned CallerObservationFact.
func (a *ConsumerAdapter) DigestObservation(ctx context.Context, obs routing.OperationalObservation) (*CallerObservationFact, error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}

	digest, err := routing.CanonicalDigest(obs)
	if err != nil {
		return nil, fmt.Errorf("consumer: digest calculation failed: %w", err)
	}

	return &CallerObservationFact{
		ObservationID:   obs.ObservationID,
		Producer:        obs.Producer,
		ObservationType: obs.ObservationType,
		Provider:        obs.Provider,
		StateValue:      obs.StateValue,
		CanonicalDigest: digest,
	}, nil
}

// ValidateFindingsAndDispositions verifies review findings and dispositions using package evidence.
func (a *ConsumerAdapter) ValidateFindingsAndDispositions(
	ctx context.Context,
	findings []CallerFindingEvidence,
	dispositions []CallerFindingDisposition,
) error {
	if err := ctx.Err(); err != nil {
		return err
	}

	for i, f := range findings {
		ef := evidence.ReviewFinding{
			FindingID: f.FindingID,
			Severity:  evidence.FindingSeverity(f.Severity),
			Category:  evidence.FindingCategory(f.Category),
			Summary:   f.Summary,
			FilePath:  f.FilePath,
			LineStart: f.LineStart,
			LineEnd:   f.LineEnd,
		}
		if err := evidence.ValidateFinding(ef); err != nil {
			return fmt.Errorf("consumer: finding %d invalid: %w", i, err)
		}
	}

	for i, d := range dispositions {
		ed := evidence.FindingDisposition{
			FindingID: d.FindingID,
			Action:    evidence.DispositionAction(d.Action),
			Basis:     evidence.BasisType(d.Basis),
			Rationale: d.Rationale,
		}
		if err := evidence.ValidateDisposition(ed); err != nil {
			return fmt.Errorf("consumer: disposition %d invalid: %w", i, err)
		}
	}

	return nil
}

// ValidateCandidateAndArtifacts verifies candidate and artifact manifests using package candidate.
func (a *ConsumerAdapter) ValidateCandidateAndArtifacts(
	ctx context.Context,
	c CallerCandidateSummary,
	artifacts []CallerArtifactRecord,
) error {
	if err := ctx.Err(); err != nil {
		return err
	}

	ci := candidate.CandidateIdentity{
		CandidateID:       c.CandidateID,
		Generation:        c.Generation,
		ProducerRole:      c.ProducerRole,
		ProducerAttemptID: "att-consumer-1",
		Commit:            c.Commit,
		TreeDigest:        c.TreeDigest,
	}
	if err := candidate.ValidateCandidate(ci); err != nil {
		return fmt.Errorf("consumer: candidate validation failed: %w", err)
	}

	var arts []candidate.Artifact
	for _, art := range artifacts {
		a := candidate.Artifact{
			ArtifactID:   art.ArtifactID,
			RunID:        "run-consumer-1",
			PhaseID:      "APG150",
			RelativePath: art.RelativePath,
			MediaType:    art.MediaType,
			ByteSize:     art.ByteSize,
			SHA256:       art.SHA256,
		}
		arts = append(arts, a)
	}

	manifest := candidate.ArtifactManifest{
		Schema:    candidate.ArtifactManifestSchema,
		ProjectID: "project-consumer",
		PhaseID:   "APG150",
		Artifacts: arts,
	}
	if err := candidate.ValidateManifest(manifest); err != nil {
		return fmt.Errorf("consumer: manifest validation failed: %w", err)
	}

	return nil
}

// VerifyProviderMatrix loads and validates the provider conformance matrix using package provider.
func (a *ConsumerAdapter) VerifyProviderMatrix(ctx context.Context, matrixData []byte) (*CallerConformanceSummary, error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}

	m, err := provider.LoadConformanceMatrix(matrixData)
	if err != nil {
		return nil, fmt.Errorf("consumer: matrix validation failed: %w", err)
	}

	fams := make([]string, len(m.Providers))
	for i, f := range m.Providers {
		fams[i] = string(f)
	}
	slices.Sort(fams)

	return &CallerConformanceSummary{
		RowCount:          len(m.Rows),
		SupportedFamilies: fams,
	}, nil
}
