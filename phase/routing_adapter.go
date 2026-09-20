package phase

import (
	"context"
	"slices"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/routing"
)

// BuildRouteRequirements maps an APGR ActorBinding and prior resolutions into policy-neutral
// RouteRequirements consumed by routing.Resolve.
func BuildRouteRequirements(
	binding ActorBinding,
	phaseType string,
	priorResolutions map[string]routing.ResolvedActorRoute,
) routing.RouteRequirements {
	isReviewTurn := slices.Contains(binding.Roles, RolePlanReviewer) || slices.Contains(binding.Roles, RoleWorkReviewer)
	isProducerTurn := slices.Contains(binding.Roles, RoleProducer) || slices.Contains(binding.Roles, RoleReviser)

	var distinctProviders []string

	// Determine planner provider for plan reviewer independence
	if slices.Contains(binding.Roles, RolePlanReviewer) {
		for _, prior := range priorResolutions {
			if slices.Contains(prior.Roles, string(RolePlanner)) || prior.BindingID == "binding_plan" {
				if prior.Provider != "" && !slices.Contains(distinctProviders, prior.Provider) {
					distinctProviders = append(distinctProviders, prior.Provider)
				}
			}
		}
	}

	// Determine producer provider for work reviewer independence
	if slices.Contains(binding.Roles, RoleWorkReviewer) {
		for _, prior := range priorResolutions {
			if slices.Contains(prior.Roles, string(RoleProducer)) || prior.BindingID == "binding_work" {
				if prior.Provider != "" && !slices.Contains(distinctProviders, prior.Provider) {
					distinctProviders = append(distinctProviders, prior.Provider)
				}
			}
		}
	}

	return routing.RouteRequirements{
		PhaseType:            phaseType,
		RequiredCapabilities: binding.RequiredCapabilities,
		RequiresMutating:     binding.IsMutating,
		IsReviewTurn:         isReviewTurn,
		IsProducerTurn:       isProducerTurn,
		DistinctProviders:    distinctProviders,
	}
}

// ResolveActorBindingRoute is a convenience helper that builds route requirements and calls routing.Resolve.
func ResolveActorBindingRoute(
	ctx context.Context,
	binding ActorBinding,
	phaseType string,
	catalog map[string]routing.EndpointCapabilities,
	observations []routing.OperationalObservation,
	priorResolutions map[string]routing.ResolvedActorRoute,
	now float64,
) (*routing.ResolvedActorRoute, error) {
	reqs := BuildRouteRequirements(binding, phaseType, priorResolutions)

	roleStrings := make([]string, len(binding.Roles))
	for i, r := range binding.Roles {
		roleStrings[i] = string(r)
	}

	return routing.Resolve(ctx, routing.ResolveRequest{
		Requirements:        reqs,
		BindingID:           binding.BindingID,
		Roles:               roleStrings,
		CapabilitiesCatalog: catalog,
		Observations:        observations,
		Now:                 now,
	})
}
