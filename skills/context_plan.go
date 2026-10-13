package skills

import (
	"encoding/json"
	"fmt"
	"sort"
	"strings"
	"unicode/utf8"
)

// PlanContext is a pure, versioned prospective plan. No paths are opened and no
// provider capabilities are inferred. The returned catalog owns its snapshots.
func PlanContext(request ContextPlanRequest) (ContextPlan, error) {
	if err := validateContextRequest(request); err != nil {
		return ContextPlan{}, err
	}
	raw, err := json.Marshal(request)
	if err != nil {
		return ContextPlan{}, err
	}
	if len(raw) > 96<<20 {
		return ContextPlan{}, fmt.Errorf("context input too large")
	}
	var r ContextPlanRequest
	if err = json.Unmarshal(raw, &r); err != nil {
		return ContextPlan{}, err
	}
	if err = validateContextRequest(r); err != nil {
		return ContextPlan{}, err
	}
	c, err := BuildCatalog(r.Catalog)
	if err != nil {
		return ContextPlan{}, err
	}
	p := ContextPlan{SchemaVersion: ContextPlanSchemaV1, RuleVersion: ContextRuleVersionV1,
		RunID: r.RunID, BindingID: r.BindingID, AttemptID: r.AttemptID, Roles: uniqueSorted(r.Roles),
		RequestedMode: r.RequestedMode, EffectiveMode: "static", CatalogFingerprint: c.Fingerprint,
		Catalog: c, Budget: r.Budget, Qualification: r.Qualification, RequiredSatisfied: true,
		Reasons: []string{}, Decisions: []ContextDecision{}, UnknownFacts: []ContextFact{},
		Instructions: []InstructionComponent{}, SelectedSnapshots: []SkillSnapshot{}}
	mandatory := ""
	for _, part := range r.Mandatory {
		mandatory += part.Text
		p.Instructions = append(p.Instructions, InstructionComponent{part, contextCost(part.Text)})
	}
	p.MandatoryCost = contextCost(mandatory)
	candidates := contextCandidates(r, c, &p)
	selected := map[string]bool{}
	byID, snapshots, overrides := contextIndexes(c)
	for _, candidate := range candidates {
		chosen := candidate.id
		if replacement, ok := overrides[chosen]; ok {
			chosen = replacement
		}
		d := contextDecision(candidate, chosen, byID)
		closure, closureErr := contextClosure(candidate.id, r.Consumer, byID, overrides)
		if closureErr != nil {
			d.Status, d.Reason = "unavailable", closureErr.Error()
		} else {
			trial := map[string]bool{}
			for id := range selected {
				trial[id] = true
			}
			for _, id := range closure {
				trial[id] = true
			}
			payload, renderErr := renderContext(mandatory, trial, snapshots)
			if renderErr != nil {
				return p, renderErr
			}
			if contextFits(r.Budget, payload) {
				selected = trial
				d.Status, d.Reason = "selected", candidate.reason
			} else {
				d.Status, d.Reason = "deferred", "required_closure_exceeds_budget"
			}
		}
		if candidate.required && d.Status != "selected" {
			p.RequiredSatisfied = false
		}
		p.Decisions = append(p.Decisions, d)
	}
	considered := map[string]bool{}
	for _, d := range p.Decisions {
		considered[d.SelectedID] = true
		considered[d.RequestedID] = true
	}
	for _, d := range c.Skills {
		if considered[d.QualifiedID] {
			continue
		}
		decision := contextDecision(contextCandidate{id: d.QualifiedID}, d.QualifiedID, byID)
		decision.Status, decision.Reason = "deferred", "applicability_unknown_no_positive_fact"
		if selected[d.QualifiedID] {
			decision.Status, decision.Reason = "selected", "required_dependency"
		}
		if strings.HasPrefix(d.CanonicalPath, "chatgpt/") && r.Consumer != ConsumerChatGPT {
			decision.Status, decision.Reason = "unavailable", ErrConsumerMismatch.Error()
		}
		p.Decisions = append(p.Decisions, decision)
	}
	ids := make([]string, 0, len(selected))
	for id := range selected {
		ids = append(ids, id)
	}
	sort.Strings(ids)
	for _, id := range ids {
		p.SelectedSnapshots = append(p.SelectedSnapshots, snapshots[id])
	}
	p.Payload, err = renderContext(mandatory, selected, snapshots)
	if err != nil {
		return p, err
	}
	p.PayloadCost = contextCost(p.Payload)
	p.BudgetPassed = contextFits(r.Budget, p.Payload)
	if r.RequestedMode == "static" {
		p.Reasons = append(p.Reasons, "static_requested")
	}
	if !contextFits(r.Budget, mandatory) {
		p.Reasons = append(p.Reasons, "mandatory_overflow")
	}
	if !p.RequiredSatisfied {
		p.Reasons = append(p.Reasons, "required_skills_unsatisfied")
	}
	if !r.Qualification.SelectiveProjection {
		p.Reasons = append(p.Reasons, "selective_projection_unqualified")
	}
	if !r.Qualification.IndependentRecovery {
		p.Reasons = append(p.Reasons, "independent_recovery_unqualified")
	}
	if len(p.Reasons) == 0 {
		p.EffectiveMode = "adaptive"
	}
	// Portable identity binds the complete plan with only execution provenance
	// removed. Returned provenance retains the actual paths and attempt identity.
	portable := p
	portable.RunID, portable.BindingID, portable.AttemptID = "", "", ""
	portable.Catalog.Provenance = nil
	portable.Catalog.Sources = nil
	portable.Catalog.Diagnostics = nil
	portable.Catalog.Snapshots = nil
	portable.Catalog.Overrides = append([]CatalogOverride(nil), p.Catalog.Overrides...)
	for i := range portable.Catalog.Overrides {
		portable.Catalog.Overrides[i].ConfigPath = ""
	}
	portable.SelectedSnapshots = nil
	portable.Instructions = append([]InstructionComponent(nil), p.Instructions...)
	for i := range portable.Instructions {
		portable.Instructions[i].SourcePath = ""
	}
	identity, err := json.Marshal(portable)
	if err != nil {
		return p, err
	}
	p.ContentIdentity = sha256Hex(identity)
	// Do not export unrelated source bodies with retained plans.
	p.Catalog.Snapshots = nil
	// Retention includes only elected descriptors; unrelated local prose is
	// not exported merely because the source catalog was inspected.
	retained := []SkillDescriptor{}
	for _, d := range p.Catalog.Skills {
		if selected[d.QualifiedID] {
			retained = append(retained, d)
		}
	}
	p.Catalog.Skills = retained
	provenance := []CatalogProvenance{}
	for _, source := range p.Catalog.Provenance {
		if selected[source.QualifiedID] {
			provenance = append(provenance, source)
		}
	}
	p.Catalog.Provenance = provenance
	// Root-level capture status and qualified decision identities explain the
	// complete catalog boundary; unrelated per-file paths are not retained.
	p.Catalog.Diagnostics = nil
	return p, nil
}

func validateContextRequest(r ContextPlanRequest) error {
	if len(r.Roles) > 32 || len(r.Facts) > 256 || len(r.Requests) > 256 || len(r.Mandatory) > 128 || len(r.Affinities) > 4096 {
		return fmt.Errorf("context collection exceeds bound")
	}
	if r.SchemaVersion != ContextPlanSchemaV1 || r.RunID == "" || r.BindingID == "" || r.AttemptID == "" || len(r.Roles) == 0 {
		return fmt.Errorf("invalid context identity")
	}
	if r.RequestedMode != "static" && r.RequestedMode != "adaptive" {
		return fmt.Errorf("invalid context mode")
	}
	switch r.Consumer {
	case ConsumerClaude, ConsumerCodex, ConsumerGo, ConsumerChatGPT:
	default:
		return ErrConsumerMismatch
	}
	for _, limit := range []*int64{r.Budget.MaxInitialContextBytes, r.Budget.MaxInitialContextCharacters} {
		if limit != nil && *limit < 0 {
			return fmt.Errorf("negative context budget")
		}
	}
	if (r.Qualification.SelectiveProjection || r.Qualification.IndependentRecovery) && r.Qualification.Evidence == "" {
		return fmt.Errorf("qualification evidence required")
	}
	seen := map[string]bool{}
	for _, c := range r.Mandatory {
		if c.ID == "" || seen[c.ID] || !utf8.ValidString(c.Text) {
			return fmt.Errorf("invalid mandatory component")
		}
		seen[c.ID] = true
		if c.SourceSHA256 != "" && !validDigest(c.SourceSHA256) {
			return fmt.Errorf("invalid source digest")
		}
	}
	for _, a := range r.Affinities {
		if a.Score < 0 || a.Score > 10 || !contextContainsString(r.Roles, a.Role) {
			return fmt.Errorf("invalid role affinity")
		}
		if _, _, err := qualifiedParts(a.QualifiedID); err != nil {
			return err
		}
	}
	return nil
}

func contextCost(s string) ContextCost {
	return ContextCost{int64(len(s)), int64(utf8.RuneCountInString(s)), sha256Hex([]byte(s))}
}
func contextFits(b ContextBudget, s string) bool {
	return (b.MaxInitialContextBytes == nil || int64(len(s)) <= *b.MaxInitialContextBytes) && (b.MaxInitialContextCharacters == nil || int64(utf8.RuneCountInString(s)) <= *b.MaxInitialContextCharacters)
}
func uniqueSorted(values []string) []string {
	set := map[string]bool{}
	for _, v := range values {
		set[v] = true
	}
	out := make([]string, 0, len(set))
	for v := range set {
		out = append(out, v)
	}
	sort.Strings(out)
	return out
}
func contextContainsString(values []string, s string) bool {
	for _, v := range values {
		if v == s {
			return true
		}
	}
	return false
}

// DecodeContextPlanRequest rejects unknown and duplicate fields.
func DecodeContextPlanRequest(data []byte) (ContextPlanRequest, error) {
	if _, err := scanJSONObject(data); err != nil {
		return ContextPlanRequest{}, err
	}
	var r ContextPlanRequest
	err := decodeTyped(data, &r)
	return r, err
}
