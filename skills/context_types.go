package skills

// ContextPlanSchemaV1 is independent of the legacy bundle contract.
const ContextPlanSchemaV1 = "apg.context-plan/v1"
const ContextRuleVersionV1 = "apg.context-packing/v1"

// ContextFact is an exact generated selection fact; unknown values stay unknown.
type ContextFact struct {
	Kind  string `json:"kind"`
	Value string `json:"value"`
}
type ContextSkillRequest struct {
	ID       string `json:"id"`
	Required bool   `json:"required"`
}
type ContextComponent struct {
	ID           string `json:"id"`
	Kind         string `json:"kind"`
	Text         string `json:"text"`
	SourcePath   string `json:"source_path"`
	SourceSHA256 string `json:"source_sha256"`
}
type ContextAffinity struct {
	Role        string `json:"role"`
	QualifiedID string `json:"qualified_id"`
	Score       int    `json:"score"`
}
type ContextBudget struct {
	MaxInitialContextBytes      *int64 `json:"max_initial_context_bytes"`
	MaxInitialContextCharacters *int64 `json:"max_initial_context_characters"`
}
type ContextQualification struct {
	SelectiveProjection bool   `json:"selective_projection"`
	IndependentRecovery bool   `json:"independent_recovery"`
	Evidence            string `json:"evidence"`
}
type ContextPlanRequest struct {
	SchemaVersion string                `json:"schema_version"`
	RunID         string                `json:"run_id"`
	BindingID     string                `json:"binding_id"`
	AttemptID     string                `json:"attempt_id"`
	Roles         []string              `json:"roles"`
	Consumer      ConsumerKind          `json:"consumer"`
	RequestedMode string                `json:"requested_mode"`
	Catalog       CatalogInput          `json:"catalog"`
	Facts         []ContextFact         `json:"facts"`
	Requests      []ContextSkillRequest `json:"requests"`
	Mandatory     []ContextComponent    `json:"mandatory"`
	Affinities    []ContextAffinity     `json:"affinities"`
	Budget        ContextBudget         `json:"budget"`
	Qualification ContextQualification  `json:"qualification"`
}
type ContextCost struct {
	Bytes      int64  `json:"bytes"`
	Characters int64  `json:"characters"`
	SHA256     string `json:"sha256"`
}
type ContextDecision struct {
	RequestedID     string        `json:"requested_id"`
	SelectedID      string        `json:"selected_id"`
	Status          string        `json:"status"`
	Reason          string        `json:"reason"`
	Required        bool          `json:"required"`
	ContentIdentity string        `json:"content_identity"`
	WholeSource     ContextCost   `json:"whole_source"`
	BodyOnly        ContextCost   `json:"body_only"`
	Description     ContextCost   `json:"description"`
	Support         []CatalogFile `json:"support"`
}
type InstructionComponent struct {
	ContextComponent
	Rendered ContextCost `json:"rendered"`
}
type ContextPlan struct {
	SchemaVersion          string                 `json:"schema_version"`
	RuleVersion            string                 `json:"rule_version"`
	RunID                  string                 `json:"run_id"`
	BindingID              string                 `json:"binding_id"`
	AttemptID              string                 `json:"attempt_id"`
	Roles                  []string               `json:"roles"`
	RequestedMode          string                 `json:"requested_mode"`
	EffectiveMode          string                 `json:"effective_mode"`
	Reasons                []string               `json:"reasons"`
	CatalogFingerprint     string                 `json:"catalog_fingerprint"`
	ContentIdentity        string                 `json:"content_identity"`
	Catalog                Catalog                `json:"catalog"`
	Decisions              []ContextDecision      `json:"decisions"`
	UnknownFacts           []ContextFact          `json:"unknown_facts"`
	Instructions           []InstructionComponent `json:"instructions"`
	SelectedSnapshots      []SkillSnapshot        `json:"selected_snapshots"`
	Budget                 ContextBudget          `json:"budget"`
	Qualification          ContextQualification   `json:"qualification"`
	BudgetPassed           bool                   `json:"budget_passed"`
	RequiredSatisfied      bool                   `json:"required_satisfied"`
	MandatoryCost          ContextCost            `json:"mandatory_cost"`
	PayloadCost            ContextCost            `json:"payload_cost"`
	Payload                string                 `json:"payload"`
	Tokens                 *int64                 `json:"tokens"`
	ProviderNativeOverhead *int64                 `json:"provider_native_overhead"`
}
