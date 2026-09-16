package phase

import (
	"errors"
	"fmt"
	"slices"
	"strings"
)

// ActorBinding groups one or more semantic responsibilities into an invocation turn.
// This decouples the 8 invariant roles from execution topologies (ADR 0059 / ADR 0064).
type ActorBinding struct {
	BindingID            string         `json:"binding_id"`
	Roles                []SemanticRole `json:"roles"`
	PolicyName           string         `json:"policy_name"`
	IsMutating           bool           `json:"is_mutating"`
	ProcessReadOnly      bool           `json:"process_read_only"`
	RequiredCapabilities []string       `json:"required_capabilities"`
}

// NewActorBinding constructs a validated ActorBinding, automatically computing
// the required capability union, mutating flag, and read-only status.
func NewActorBinding(bindingID string, roles []SemanticRole, policyName string) (ActorBinding, error) {
	if strings.TrimSpace(bindingID) == "" {
		return ActorBinding{}, errors.New("phase: binding_id must be non-empty")
	}
	if len(roles) == 0 {
		return ActorBinding{}, errors.New("phase: binding must contain at least one role")
	}
	for _, r := range roles {
		if !ValidRole(r) {
			return ActorBinding{}, fmt.Errorf("phase: invalid role in binding: %q", r)
		}
	}

	capMap := make(map[string]bool)
	mutating := false
	allReadOnly := true

	for _, r := range roles {
		for _, capStr := range RequiredCapabilities(r) {
			capMap[capStr] = true
		}
		if IsMutating(r) {
			mutating = true
		}
		if !IsReadOnly(r) {
			allReadOnly = false
		}
	}

	caps := make([]string, 0, len(capMap))
	for c := range capMap {
		caps = append(caps, c)
	}
	slices.Sort(caps)

	rolesCopy := append([]SemanticRole(nil), roles...)

	return ActorBinding{
		BindingID:            bindingID,
		Roles:                rolesCopy,
		PolicyName:           policyName,
		IsMutating:           mutating,
		ProcessReadOnly:      allReadOnly,
		RequiredCapabilities: caps,
	}, nil
}

// MustNewActorBinding is a helper that panics if NewActorBinding fails (for static topologies).
func MustNewActorBinding(bindingID string, roles []SemanticRole, policyName string) ActorBinding {
	b, err := NewActorBinding(bindingID, roles, policyName)
	if err != nil {
		panic(err)
	}
	return b
}

// DefaultBindings returns the standard 5-turn topology merging adjacent responsibilities.
func DefaultBindings() []ActorBinding {
	return []ActorBinding{
		MustNewActorBinding("binding_plan", []SemanticRole{RolePlanner}, "default_standard"),
		MustNewActorBinding("binding_plan_review", []SemanticRole{RolePlanReviewer}, "default_standard"),
		MustNewActorBinding("binding_work", []SemanticRole{RolePlanReviewDisposition, RoleProducer}, "default_standard"),
		MustNewActorBinding("binding_work_review", []SemanticRole{RoleWorkReviewer}, "default_standard"),
		MustNewActorBinding("binding_closeout", []SemanticRole{RoleWorkReviewDisposition, RoleReviser, RoleCloseoutAgent}, "default_standard"),
	}
}

// UnmergedBindings returns the discrete 8-turn topology where each role maps to one binding.
func UnmergedBindings() []ActorBinding {
	policyName := "unmerged_discrete"
	bindings := make([]ActorBinding, len(CanonicalRoles))
	for i, role := range CanonicalRoles {
		slug := strings.ToLower(string(role))
		slug = strings.ReplaceAll(slug, " ", "_")
		bindings[i] = MustNewActorBinding("binding_"+slug, []SemanticRole{role}, policyName)
	}
	return bindings
}
