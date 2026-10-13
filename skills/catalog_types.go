package skills

// DescriptorSchemaV1 is the experimental generated skill descriptor contract.
const DescriptorSchemaV1 = "apg.skill-descriptor/v1"

// CatalogSchemaV1 is the experimental, explicit multi-source catalog contract.
const CatalogSchemaV1 = "apg.skill-catalog/v1"
const CatalogRuleVersionV1 = "apg.catalog-selection/v1"
const MaxCatalogFileBytes = 1 << 20

// SkillDescriptor is a provisional generated view, not a classification authority.
// BodyBytes/BodySHA256 retain whole SKILL.md compatibility semantics.
type SkillDescriptor struct {
	SchemaVersion string `json:"schema_version"`
	QualifiedID   string `json:"qualified_id"`
	SkillMetadata
	BodyOnlyBytes          int64           `json:"body_only_bytes"`
	BodyOnlyCharacters     int64           `json:"body_only_characters"`
	BodyOnlySHA256         string          `json:"body_only_sha256"`
	DescriptionSHA256      string          `json:"description_sha256"`
	Tokens                 *int64          `json:"tokens"`
	DoNotUse               string          `json:"do_not_use"`
	ProjectOwnedParameters string          `json:"project_owned_parameters"`
	TriggerBoundary        string          `json:"trigger_boundary"`
	Maturity               string          `json:"maturity"`
	SourceDeclaredMaturity string          `json:"source_declared_maturity"`
	ConsumerLimitations    []string        `json:"consumer_limitations"`
	SelectionFacts         []SelectionRule `json:"selection_facts"`
	RequiredDependencies   []string        `json:"required_dependencies"`
	SupportFiles           []CatalogFile   `json:"support_files"`
	ContentIdentity        string          `json:"content_identity"`
}

// CatalogFile measures an explicitly declared file. Captured records a source
// snapshot, never delivery into a provider context.
type CatalogFile struct {
	Path     string `json:"path"`
	Bytes    int64  `json:"bytes"`
	SHA256   string `json:"sha256"`
	Captured bool   `json:"captured"`
}

// SkillSnapshot carries exact source bytes. No source code is executed.
type SkillSnapshot struct {
	QualifiedID string            `json:"qualified_id"`
	Path        string            `json:"path"`
	Body        []byte            `json:"body"`
	Support     map[string][]byte `json:"support"`
}

// CatalogOverride is explicit project authority, separate from source identity.
type CatalogOverride struct {
	Requested    string `json:"requested"`
	Selected     string `json:"selected"`
	ConfigPath   string `json:"config_path"`
	ConfigSHA256 string `json:"config_sha256"`
}

type CatalogDiagnostic struct {
	Identity string `json:"identity"`
	Path     string `json:"path"`
	Message  string `json:"message"`
}

type CatalogSourceStatus struct {
	Source       string `json:"source"`
	SelectedRoot string `json:"selected_root"`
	ResolvedRoot string `json:"resolved_root"`
	Status       string `json:"status"`
}

// CatalogInput is an experimental pure data input; canonical bytes always come
// from the embedded owner. External inputs cannot assert canonical maturity.
type CatalogInput struct {
	SchemaVersion string                `json:"schema_version"`
	Snapshots     []SkillSnapshot       `json:"snapshots"`
	Overrides     []CatalogOverride     `json:"overrides"`
	Diagnostics   []CatalogDiagnostic   `json:"diagnostics"`
	Sources       []CatalogSourceStatus `json:"sources"`
}

// CatalogProvenance is operation-local and excluded from portable identity.
type CatalogProvenance struct {
	QualifiedID string `json:"qualified_id"`
	Path        string `json:"path"`
	SHA256      string `json:"sha256"`
}

type Catalog struct {
	DerivationInputs []CatalogFile         `json:"derivation_inputs"`
	Provenance       []CatalogProvenance   `json:"provenance"`
	SchemaVersion    string                `json:"schema_version"`
	RuleVersion      string                `json:"rule_version"`
	Skills           []SkillDescriptor     `json:"skills"`
	Snapshots        []SkillSnapshot       `json:"snapshots"`
	Overrides        []CatalogOverride     `json:"overrides"`
	Diagnostics      []CatalogDiagnostic   `json:"diagnostics"`
	Sources          []CatalogSourceStatus `json:"sources"`
	Fingerprint      string                `json:"fingerprint"`
}

// CatalogSelection binds requested identity, selected body and the rule identity.
type CatalogSelection struct {
	RequestedIdentity  string        `json:"requested_identity"`
	SelectedIdentity   string        `json:"selected_identity"`
	SourceSHA256       string        `json:"source_sha256"`
	ContentIdentity    string        `json:"content_identity"`
	CatalogFingerprint string        `json:"catalog_fingerprint"`
	RuleVersion        string        `json:"rule_version"`
	Snapshot           SkillSnapshot `json:"snapshot"`
}
