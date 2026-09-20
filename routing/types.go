package routing

import "slices"

// Supported standard capability constants.
const (
	CapRead             = "read"
	CapMutation         = "mutation"
	CapExecution        = "execution"
	CapReasoning        = "reasoning"
	CapStructuredOutput = "structured_output"
	CapSubagentWorkers  = "subagent_workers"
)

// Posture values.
const (
	PostureMutating = "mutating"
	PostureReadOnly = "read_only"
)

// EndpointIdentity identifies a provider execution endpoint.
type EndpointIdentity struct {
	Provider      string `json:"provider"`
	Profile       string `json:"profile"`
	EndpointAlias string `json:"endpoint_alias"`
}

// EndpointCapabilities describes the capabilities and posture of an endpoint.
type EndpointCapabilities struct {
	EndpointAlias string   `json:"endpoint_alias"`
	Provider      string   `json:"provider"`
	Profile       string   `json:"profile"`
	Capabilities  []string `json:"capabilities"`
	Posture       string   `json:"posture"`
}

// IsMutating reports whether the endpoint posture allows repository mutations.
func (ep EndpointCapabilities) IsMutating() bool {
	return ep.Posture == PostureMutating
}

// IsReadOnly reports whether the endpoint posture is strictly read-only.
func (ep EndpointCapabilities) IsReadOnly() bool {
	return ep.Posture == PostureReadOnly
}

// Satisfies reports whether ep provides all required capabilities and satisfies posture bounds.
func (ep EndpointCapabilities) Satisfies(required []string, requiresMutating bool) bool {
	for _, req := range required {
		if !slices.Contains(ep.Capabilities, req) {
			return false
		}
	}
	if requiresMutating && !ep.IsMutating() {
		return false
	}
	return true
}
