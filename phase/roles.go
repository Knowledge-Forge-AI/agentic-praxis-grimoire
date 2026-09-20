package phase

import "slices"

// SemanticRole represents one of the 8 canonical semantic responsibilities (ADR 0059).
type SemanticRole string

const (
	RolePlanner               SemanticRole = "Planner"
	RolePlanReviewer          SemanticRole = "Plan Reviewer"
	RolePlanReviewDisposition SemanticRole = "Plan Review Disposition"
	RoleProducer              SemanticRole = "Producer"
	RoleWorkReviewer          SemanticRole = "Work Reviewer"
	RoleWorkReviewDisposition SemanticRole = "Work Review Disposition"
	RoleReviser               SemanticRole = "Reviser"
	RoleCloseoutAgent         SemanticRole = "Closeout Agent"
)

// CanonicalRoles lists all 8 semantic responsibilities in standard lifecycle sequence.
var CanonicalRoles = []SemanticRole{
	RolePlanner,
	RolePlanReviewer,
	RolePlanReviewDisposition,
	RoleProducer,
	RoleWorkReviewer,
	RoleWorkReviewDisposition,
	RoleReviser,
	RoleCloseoutAgent,
}

// ValidRole reports whether r is one of the 8 canonical semantic responsibilities.
func ValidRole(r SemanticRole) bool {
	return slices.Contains(CanonicalRoles, r)
}

// IsMutating reports whether the role is authorized to perform repository mutations.
func IsMutating(r SemanticRole) bool {
	switch r {
	case RoleProducer, RoleReviser, RoleCloseoutAgent:
		return true
	default:
		return false
	}
}

// IsReadOnly reports whether the role is strictly read-only by process invariant.
func IsReadOnly(r SemanticRole) bool {
	switch r {
	case RolePlanner, RolePlanReviewer, RoleWorkReviewer:
		return true
	default:
		return false
	}
}

// RequiredCapabilities returns the minimal capability strings required for the role.
func RequiredCapabilities(r SemanticRole) []string {
	switch r {
	case RolePlanner, RolePlanReviewer, RoleWorkReviewer:
		return []string{"read", "reasoning"}
	case RolePlanReviewDisposition, RoleWorkReviewDisposition:
		return []string{"read"}
	case RoleProducer, RoleReviser:
		return []string{"execution", "mutation", "read"}
	case RoleCloseoutAgent:
		return []string{"execution", "read"}
	default:
		return []string{"read"}
	}
}
