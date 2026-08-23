package skills

import (
	"errors"
	"fmt"
)

const (
	BundleRequestSchemaV1  = "apg.skill-bundle-request/v1"
	BundleResultSchemaV1   = "apg.skill-bundle-result/v1"
	ManifestSchemaV1       = "apg.skill-bundle-manifest/v1"
	RuleTableVersionV1     = "apg.skill-selection-rules/v1"
	CompositionVersionV1   = "apg.skill-composition-rules/v1"
	ManifestFilename       = "manifest.json"
	GlobalDescriptionLimit = int64(9527)
)

var (
	ErrBudgetExceeded    = errors.New("skill bundle budget exceeded")
	ErrCollision         = errors.New("skill bundle materialization collision")
	ErrConsumerMismatch  = errors.New("skill is incompatible with consumer")
	ErrCorpusMismatch    = errors.New("embedded skill corpus mismatch")
	ErrInvalidRequest    = errors.New("invalid skill bundle request")
	ErrInvalidResult     = errors.New("invalid skill bundle result")
	ErrUnsafeDestination = errors.New("unsafe skill bundle destination")
)

type ConsumerKind string

const (
	ConsumerClaude  ConsumerKind = "claude"
	ConsumerCodex   ConsumerKind = "codex"
	ConsumerGo      ConsumerKind = "go_library"
	ConsumerChatGPT ConsumerKind = "chatgpt"
)

type MaterializationForm string

const (
	MaterializationFlatDirectory MaterializationForm = "flat_directory"
	MaterializationInMemory      MaterializationForm = "in_memory"
)

// Budget uses nil limits for explicitly unbounded dimensions. A non-nil zero
// is an exact zero-byte limit.
type Budget struct {
	MaxBodyBytes           *int64 `json:"max_body_bytes"`
	MaxDescriptionBytes    *int64 `json:"max_description_bytes"`
	MaxInitialContextBytes *int64 `json:"max_initial_context_bytes"`
	PromptOverheadBytes    int64  `json:"prompt_overhead_bytes"`
}

type Consumer struct {
	Architecture        string              `json:"architecture"`
	Kind                ConsumerKind        `json:"kind"`
	MaterializationForm MaterializationForm `json:"materialization_form"`
	OperatingSystem     string              `json:"operating_system"`
	ProviderConstraints []string            `json:"provider_constraints"`
}

// BundleRequest is the strict structured, prompt-free resolver input.
type BundleRequest struct {
	Budget                    Budget   `json:"budget"`
	Capabilities              []string `json:"capabilities"`
	Consumer                  Consumer `json:"consumer"`
	EagerBodies               bool     `json:"eager_bodies"`
	ExplicitSkillIDs          []string `json:"explicit_skill_ids"`
	Languages                 []string `json:"languages"`
	RepositoryCharacteristics []string `json:"repository_characteristics"`
	Runtimes                  []string `json:"runtimes"`
	SchemaVersion             string   `json:"schema_version"`
	TestFrameworks            []string `json:"test_frameworks"`
	WorkClass                 string   `json:"work_class"`
}

type BudgetEvaluation struct {
	Limit    *int64 `json:"limit"`
	Measured int64  `json:"measured"`
	Passed   bool   `json:"passed"`
}

type BudgetResult struct {
	BodyBytes           BudgetEvaluation `json:"body_bytes"`
	DescriptionBytes    BudgetEvaluation `json:"description_bytes"`
	InitialContextBytes BudgetEvaluation `json:"initial_context_bytes"`
}

type CompositionEdge struct {
	From string `json:"from"`
	To   string `json:"to"`
}

type Conflict struct {
	Reason     string `json:"reason"`
	SkillID    string `json:"skill_id"`
	SourceFact string `json:"source_fact"`
}

type Exclusion struct {
	Reason     string `json:"reason"`
	SkillID    string `json:"skill_id"`
	SourceFact string `json:"source_fact"`
}

type SelectedSkill struct {
	BodyBytes        int64    `json:"body_bytes"`
	BodySHA256       string   `json:"body_sha256"`
	CanonicalPath    string   `json:"canonical_path"`
	DescriptionBytes int64    `json:"description_bytes"`
	ID               string   `json:"id"`
	InclusionReasons []string `json:"inclusion_reasons"`
	SourceFacts      []string `json:"source_facts"`
}

// BundleResult is the deterministic resolver result and materialization input.
type BundleResult struct {
	Budget                               BudgetResult        `json:"budget"`
	BundleFingerprint                    string              `json:"bundle_fingerprint"`
	CanonicalCorpusDescriptionBytes      int64               `json:"canonical_corpus_description_bytes"`
	CanonicalCorpusDescriptionCharacters int64               `json:"canonical_corpus_description_characters"`
	CanonicalCorpusSkillCount            int                 `json:"canonical_corpus_skill_count"`
	CompositionEdges                     []CompositionEdge   `json:"composition_edges"`
	CompositionRuleVersion               string              `json:"composition_rule_version"`
	Conflicts                            []Conflict          `json:"conflicts"`
	ConsumerKind                         ConsumerKind        `json:"consumer_kind"`
	EagerBodies                          bool                `json:"eager_bodies"`
	EmbeddedCorpusFingerprint            string              `json:"embedded_corpus_fingerprint"`
	Exclusions                           []Exclusion         `json:"exclusions"`
	FixedPromptOverheadBytes             int64               `json:"fixed_prompt_overhead_bytes"`
	InitialContextBytes                  int64               `json:"initial_context_bytes"`
	MaterializationForm                  MaterializationForm `json:"materialization_form"`
	RequestFingerprint                   string              `json:"request_fingerprint"`
	RuleTableVersion                     string              `json:"rule_table_version"`
	SchemaVersion                        string              `json:"schema_version"`
	SelectedBodyBytes                    int64               `json:"selected_body_bytes"`
	SelectedDescriptionBytes             int64               `json:"selected_description_bytes"`
	SelectedSkillIDs                     []string            `json:"selected_skill_ids"`
	SelectedSkills                       []SelectedSkill     `json:"selected_skills"`
}

type BudgetError struct {
	Budget BudgetResult
}

func (err *BudgetError) Error() string {
	return fmt.Sprintf(
		"%s: description=%d/%s body=%d/%s initial_context=%d/%s",
		ErrBudgetExceeded,
		err.Budget.DescriptionBytes.Measured, formatBudgetLimit(err.Budget.DescriptionBytes.Limit),
		err.Budget.BodyBytes.Measured, formatBudgetLimit(err.Budget.BodyBytes.Limit),
		err.Budget.InitialContextBytes.Measured, formatBudgetLimit(err.Budget.InitialContextBytes.Limit),
	)
}
func (err *BudgetError) Unwrap() error { return ErrBudgetExceeded }

func formatBudgetLimit(limit *int64) string {
	if limit == nil {
		return "unbounded"
	}
	return fmt.Sprintf("%d", *limit)
}

type SelectionRule struct {
	FactKind  string `json:"fact_kind"`
	FactValue string `json:"fact_value"`
	SkillID   string `json:"skill_id"`
	Source    string `json:"source"`
}

type SkillMetadata struct {
	BodyBytes             int64  `json:"body_bytes"`
	BodyCharacters        int64  `json:"body_characters"`
	BodySHA256            string `json:"body_sha256"`
	CanonicalPath         string `json:"canonical_path"`
	Description           string `json:"description"`
	DescriptionBytes      int64  `json:"description_bytes"`
	DescriptionCharacters int64  `json:"description_characters"`
	ID                    string `json:"id"`
	Lines                 int64  `json:"lines"`
}

type CorpusMetadata struct {
	DescriptionBytes      int64
	DescriptionCharacters int64
	Fingerprint           string
	ManifestJSON          []byte
	Skills                []SkillMetadata
}

type MaterializeRequest struct {
	DestinationParent string
	Result            BundleResult
}

type MaterializedFile struct {
	BodyBytes    int64  `json:"body_bytes"`
	BodySHA256   string `json:"body_sha256"`
	RelativePath string `json:"relative_path"`
	SkillID      string `json:"skill_id"`
}

type Materialization struct {
	BundleFingerprint     string             `json:"bundle_fingerprint"`
	CleanupOwnership      string             `json:"cleanup_ownership"`
	ManifestFingerprint   string             `json:"manifest_fingerprint"`
	ManifestSchemaVersion string             `json:"manifest_schema_version"`
	Reused                bool               `json:"reused"`
	Root                  string             `json:"root"`
	SelectedFiles         []MaterializedFile `json:"selected_files"`
}

type ManifestFile struct {
	BodyBytes        int64  `json:"body_bytes"`
	BodySHA256       string `json:"body_sha256"`
	CanonicalPath    string `json:"canonical_path"`
	MaterializedPath string `json:"materialized_path"`
	SkillID          string `json:"skill_id"`
}

type BundleManifest struct {
	BundleFingerprint         string         `json:"bundle_fingerprint"`
	EmbeddedCorpusFingerprint string         `json:"embedded_corpus_fingerprint"`
	Files                     []ManifestFile `json:"files"`
	RuleTableVersion          string         `json:"rule_table_version"`
	SchemaVersion             string         `json:"schema_version"`
	SelectedSkillIDs          []string       `json:"selected_skill_ids"`
}
