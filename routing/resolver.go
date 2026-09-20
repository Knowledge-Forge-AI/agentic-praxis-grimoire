package routing

import (
	"context"
	"errors"
	"fmt"
	"slices"
	"strings"
)

var (
	// ErrNoRouteAvailable indicates no candidate survived capability, operational, or independence checks.
	ErrNoRouteAvailable = errors.New("routing: no route available")
	// ErrMissingCapability indicates an endpoint lacks required capabilities.
	ErrMissingCapability = errors.New("routing: missing required capabilities")
	// ErrProviderIndependence indicates an endpoint violates provider independence.
	ErrProviderIndependence = errors.New("routing: violates provider independence invariant")
)

// RouteRequirements holds the policy-neutral requirements for resolving a route.
type RouteRequirements struct {
	PhaseType            string   `json:"phase_type"`
	RequiredCapabilities []string `json:"required_capabilities"`
	RequiresMutating     bool     `json:"requires_mutating"`
	IsReviewTurn         bool     `json:"is_review_turn"`
	IsProducerTurn       bool     `json:"is_producer_turn"`
	DistinctProviders    []string `json:"distinct_providers,omitempty"`
}

// ResolveRequest wraps all in-memory inputs required to resolve a route deterministically.
type ResolveRequest struct {
	Requirements        RouteRequirements               `json:"requirements"`
	BindingID           string                          `json:"binding_id"`
	Roles               []string                        `json:"roles,omitempty"`
	CapabilitiesCatalog map[string]EndpointCapabilities `json:"capabilities_catalog"`
	Observations        []OperationalObservation        `json:"observations,omitempty"`
	Now                 float64                         `json:"now"`
}

// ResolvedActorRoute represents a selected endpoint and its provenance.
type ResolvedActorRoute struct {
	BindingID          string   `json:"binding_id"`
	Provider           string   `json:"provider"`
	Profile            string   `json:"profile"`
	EndpointAlias      string   `json:"endpoint_alias"`
	Capabilities       []string `json:"capabilities"`
	SelectionRationale string   `json:"selection_rationale"`
	Roles              []string `json:"roles,omitempty"`
	ObservationIDs     []string `json:"observation_ids,omitempty"`
}

func phaseAffinity(phaseType, provider, profile string) int {
	score := 0
	switch phaseType {
	case "implementation_testing":
		if strings.Contains(profile, "implementation") {
			score += 20
		}
		if provider == "codex" {
			score += 10
		} else if provider == "antigravity" {
			score += 8
		}
	case "architecture_docs":
		if strings.Contains(profile, "architecture") || strings.Contains(profile, "docs") {
			score += 20
		}
		if provider == "claude" {
			score += 10
		} else if provider == "codex" {
			score += 8
		}
	case "sysadmin":
		if strings.Contains(profile, "sysadmin") {
			score += 20
		}
		if provider == "claude" {
			score += 10
		} else if provider == "codex" {
			score += 8
		}
	}
	return score
}

func roleAffinity(req RouteRequirements, ep EndpointCapabilities) int {
	score := 0
	if req.IsReviewTurn {
		if ep.IsReadOnly() {
			score += 15
		}
		if strings.Contains(ep.EndpointAlias, "review") {
			score += 15
		}
	} else if req.IsProducerTurn {
		if ep.IsMutating() {
			score += 15
		}
		if strings.Contains(ep.EndpointAlias, "primary") || strings.Contains(ep.EndpointAlias, "testing") {
			score += 10
		}
	}
	return score
}

type scoredCandidate struct {
	score int
	ep    EndpointCapabilities
}

// Resolve executes the pure, deterministic 6-stage decision ladder.
// It performs no filesystem, subprocess, or database operations.
func Resolve(ctx context.Context, req ResolveRequest) (*ResolvedActorRoute, error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}

	// Extract and sort candidates by alias for deterministic iteration
	var aliases []string
	for alias := range req.CapabilitiesCatalog {
		aliases = append(aliases, alias)
	}
	slices.Sort(aliases)

	// 1. Capability Eligibility (Fails Closed)
	var capable []EndpointCapabilities
	for _, alias := range aliases {
		ep := req.CapabilitiesCatalog[alias]
		if ep.Satisfies(req.Requirements.RequiredCapabilities, req.Requirements.RequiresMutating) {
			capable = append(capable, ep)
		}
	}
	if len(capable) == 0 {
		return nil, fmt.Errorf("%w: no capability-eligible endpoints for %q with required %v",
			ErrNoRouteAvailable, req.BindingID, req.Requirements.RequiredCapabilities)
	}

	// Filter active observations
	var activeObs []OperationalObservation
	for _, obs := range req.Observations {
		if obs.IsActive(req.Now) {
			activeObs = append(activeObs, obs)
		}
	}

	usedObsIDsMap := make(map[string]bool)

	// 2. Hard Unusable / Unavailable Exclusions
	var usable []EndpointCapabilities
	for _, ep := range capable {
		excluded := false
		for _, obs := range activeObs {
			applies := (obs.Provider == ep.Provider) && (obs.Profile == nil || *obs.Profile == ep.Profile)
			if !applies {
				continue
			}
			usedObsIDsMap[obs.ObservationID] = true
			if obs.ObservationType == ObservationTypeAvailability && obs.StateValue == StateUnavailable {
				excluded = true
				break
			}
			if obs.ObservationType == ObservationTypeAuthentication && obs.StateValue == StateUnusable {
				excluded = true
				break
			}
		}
		if !excluded {
			usable = append(usable, ep)
		}
	}
	if len(usable) == 0 {
		return nil, fmt.Errorf("%w: all capable endpoints marked unavailable or unusable for %q",
			ErrNoRouteAvailable, req.BindingID)
	}

	// 3. Quota Exhausted Exclusion
	var quotaEligible []EndpointCapabilities
	for _, ep := range usable {
		excluded := false
		for _, obs := range activeObs {
			applies := (obs.Provider == ep.Provider) && (obs.Profile == nil || *obs.Profile == ep.Profile)
			if !applies {
				continue
			}
			usedObsIDsMap[obs.ObservationID] = true
			if obs.ObservationType == ObservationTypeQuota && obs.StateValue == StateExhausted {
				excluded = true
				break
			}
		}
		if !excluded {
			quotaEligible = append(quotaEligible, ep)
		}
	}
	if len(quotaEligible) == 0 {
		return nil, fmt.Errorf("%w: all usable endpoints have exhausted quota for %q",
			ErrNoRouteAvailable, req.BindingID)
	}

	// 4. Active Failure Cooldown Exclusion
	var nonCooldown []EndpointCapabilities
	for _, ep := range quotaEligible {
		excluded := false
		for _, obs := range activeObs {
			applies := (obs.Provider == ep.Provider) && (obs.Profile == nil || *obs.Profile == ep.Profile)
			if !applies {
				continue
			}
			usedObsIDsMap[obs.ObservationID] = true
			if obs.ObservationType == ObservationTypeCooldown && (obs.StateValue == StateCooldown || obs.StateValue == StateActiveCooldown) {
				excluded = true
				break
			}
		}
		if !excluded {
			nonCooldown = append(nonCooldown, ep)
		}
	}
	if len(nonCooldown) == 0 {
		return nil, fmt.Errorf("%w: all quota-eligible endpoints are in cooldown for %q",
			ErrNoRouteAvailable, req.BindingID)
	}

	// 5. Reviewer Independence Invariants
	var independent []EndpointCapabilities
	for _, ep := range nonCooldown {
		if slices.Contains(req.Requirements.DistinctProviders, ep.Provider) {
			continue
		}
		independent = append(independent, ep)
	}
	if len(independent) == 0 {
		return nil, fmt.Errorf("%w: no independent routes for %q (distinct from %v)",
			ErrNoRouteAvailable, req.BindingID, req.Requirements.DistinctProviders)
	}

	// 6. Deterministic Ranking & Lexical Tie-Breaking
	var scored []scoredCandidate
	for _, ep := range independent {
		score := phaseAffinity(req.Requirements.PhaseType, ep.Provider, ep.Profile) +
			roleAffinity(req.Requirements, ep)

		availObsFound := false
		for _, obs := range activeObs {
			applies := (obs.Provider == ep.Provider) && (obs.Profile == nil || *obs.Profile == ep.Profile)
			if !applies {
				continue
			}
			if obs.ObservationType == ObservationTypeAvailability {
				availObsFound = true
				if obs.StateValue == StateAvailable {
					score += 10
				} else if obs.StateValue == StateUnknown {
					score -= 5
				}
			} else if obs.ObservationType == ObservationTypeQuota {
				if obs.StateValue == StateHealthy {
					score += 5
				} else if obs.StateValue == StateConstrained {
					score -= 10
				}
			}
		}
		if !availObsFound && len(activeObs) > 0 {
			score -= 10
		}
		scored = append(scored, scoredCandidate{score: score, ep: ep})
	}

	// Sort by (-score, provider, profile, alias)
	slices.SortFunc(scored, func(a, b scoredCandidate) int {
		if a.score != b.score {
			// Higher score comes first
			if a.score > b.score {
				return -1
			}
			return 1
		}
		if a.ep.Provider != b.ep.Provider {
			return strings.Compare(a.ep.Provider, b.ep.Provider)
		}
		if a.ep.Profile != b.ep.Profile {
			return strings.Compare(a.ep.Profile, b.ep.Profile)
		}
		return strings.Compare(a.ep.EndpointAlias, b.ep.EndpointAlias)
	})

	winner := scored[0].ep
	winnerScore := scored[0].score

	usedIDs := make([]string, 0, len(usedObsIDsMap))
	for id := range usedObsIDsMap {
		usedIDs = append(usedIDs, id)
	}
	slices.Sort(usedIDs)

	capsCopy := append([]string(nil), winner.Capabilities...)
	slices.Sort(capsCopy)

	rolesCopy := append([]string(nil), req.Roles...)

	rationale := fmt.Sprintf("selected with score %d for %s (%s)", winnerScore, req.BindingID, req.Requirements.PhaseType)

	return &ResolvedActorRoute{
		BindingID:          req.BindingID,
		Provider:           winner.Provider,
		Profile:            winner.Profile,
		EndpointAlias:      winner.EndpointAlias,
		Capabilities:       capsCopy,
		SelectionRationale: rationale,
		Roles:              rolesCopy,
		ObservationIDs:     usedIDs,
	}, nil
}
