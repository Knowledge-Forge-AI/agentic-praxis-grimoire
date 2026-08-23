package hotspot

import "time"

const (
	RequestSchemaV1    = "apg.hotspot-request/v1"
	ReportSchemaV1     = "apg.hotspot-report/v1"
	CapabilityMatrixV1 = "apg.hotspot-capabilities/v1"
	ProducerVersion    = "devel"
)

const (
	CompletionComplete = "complete"
)

type Language string

const (
	LanguageGo          Language = "go"
	LanguageMarkdown    Language = "markdown"
	LanguageMDX         Language = "mdx"
	LanguageAstro       Language = "astro"
	LanguagePython      Language = "python"
	LanguageJava        Language = "java"
	LanguageKotlin      Language = "kotlin"
	LanguageJavaScript  Language = "javascript"
	LanguageTypeScript  Language = "typescript"
	LanguageJSX         Language = "jsx"
	LanguageTSX         Language = "tsx"
	LanguageHTML        Language = "html"
	LanguageCSS         Language = "css"
	LanguageXML         Language = "xml"
	LanguageXMLPlist    Language = "xml-plist"
	LanguageBinaryPlist Language = "binary-plist"
	LanguageJSON        Language = "json"
	LanguageJSONFamily  Language = "json-family"
	LanguageYAML        Language = "yaml"
	LanguageTOML        Language = "toml"
	LanguageTerraform   Language = "terraform"
	LanguageGradle      Language = "gradle"
	LanguageSQL         Language = "sql"
	LanguageBash        Language = "bash"
	LanguageZsh         Language = "zsh"
	LanguagePOSIXShell  Language = "posix-shell"
	LanguageDockerfile  Language = "dockerfile"
	LanguageVagrantfile Language = "vagrantfile"
	LanguageBinary      Language = "binary"
	LanguageUnknown     Language = "unknown"
)

type Confidence string

const (
	ConfidenceHigh   Confidence = "high"
	ConfidenceMedium Confidence = "medium"
	ConfidenceLow    Confidence = "low"
)

type Availability string

const (
	AvailabilityExact         Availability = "exact"
	AvailabilityStructural    Availability = "structural"
	AvailabilityUnavailable   Availability = "unavailable"
	AvailabilityNotApplicable Availability = "not-applicable"
)

const (
	MetricBytes           = "bytes"
	MetricPhysicalLines   = "physical-lines"
	MetricProseLines      = "prose-lines"
	MetricFenceLines      = "fence-lines"
	MetricStatements      = "statements"
	MetricSymbols         = "symbols"
	MetricCyclomatic      = "cyclomatic"
	MetricNesting         = "nesting"
	MetricParameters      = "parameters"
	MetricProceduralSize  = "top-level-procedural-size"
	MetricFileSize        = "file-size"
	MetricLexicalLines    = "lexical-lines"
	MetricHeadings        = "headings"
	MetricFences          = "fences"
	MetricLinks           = "links"
	MetricEmbeddedLines   = "embedded-lines"
	MetricEmbeddedRegions = "embedded-regions"
	MetricElements        = "elements"
	MetricAttributes      = "attributes"
	MetricSelectors       = "selectors"
	MetricDeclarations    = "declarations"
	MetricObjects         = "objects"
	MetricKeys            = "keys"
	MetricArrays          = "arrays"
	MetricScalars         = "scalars"
	MetricMaxObjectKeys   = "max-object-keys"
	MetricMaxArrayLength  = "max-array-length"
	MetricInstructions    = "instructions"
	MetricStages          = "stages"
	MetricRuns            = "run-instructions"
	MetricKeysStructural  = "structural-keys"
	MetricBlocks          = "blocks"
	MetricCommands        = "commands"
	MetricControlTokens   = "control-tokens"
	MetricClauses         = "clauses"
)

// Limits bounds all consequence-bearing scan resources.
type Limits struct {
	MaxFiles        int
	MaxBytesPerFile int64
	MaxTotalBytes   int64
	MaxDuration     time.Duration
}

// Filters are deterministic, root-relative inclusion and exclusion controls.
// Paths are literal clean relative path prefixes; they are not globs.
type Filters struct {
	DisableDefaultExclusions bool
	IncludeLanguages         []Language
	IncludePaths             []string
	ExcludePaths             []string
}

// Request identifies one exact root and one bounded analysis configuration.
type Request struct {
	SchemaVersion string
	Root          string
	RootID        string
	ToolVersion   string
	Limits        Limits
	Filters       Filters
	DisplayTopN   int
}

type ScanConfiguration struct {
	RequestSchemaVersion     string     `json:"request_schema_version"`
	MaxFiles                 int        `json:"max_files"`
	MaxBytesPerFile          int64      `json:"max_bytes_per_file"`
	MaxTotalBytes            int64      `json:"max_total_bytes"`
	MaxDurationMilliseconds  int64      `json:"max_duration_milliseconds"`
	DefaultExclusionsEnabled bool       `json:"default_exclusions_enabled"`
	IncludeLanguages         []Language `json:"include_languages"`
	IncludePaths             []string   `json:"include_paths"`
	ExcludePaths             []string   `json:"exclude_paths"`
	DisplayTopN              int        `json:"display_top_n"`
}

type Exclusion struct {
	Rule        string `json:"rule"`
	Description string `json:"description"`
	Directories int    `json:"directories"`
	Files       int    `json:"files"`
}

type SurfaceCapability struct {
	Surface           string       `json:"surface"`
	Languages         []Language   `json:"languages"`
	Classification    Availability `json:"classification"`
	Lines             Availability `json:"lines"`
	Statements        Availability `json:"statements"`
	Symbols           Availability `json:"symbols"`
	Cyclomatic        Availability `json:"cyclomatic"`
	Nesting           Availability `json:"nesting"`
	ProceduralRegions Availability `json:"procedural_regions"`
	StructuralMetrics Availability `json:"structural_metrics"`
	Confidence        Confidence   `json:"confidence"`
}

type DeferredCapability struct {
	Name   string `json:"name"`
	Status string `json:"status"`
}

type Metric struct {
	Name         string       `json:"name"`
	Availability Availability `json:"availability"`
	Value        *int64       `json:"value,omitempty"`
	Unit         string       `json:"unit,omitempty"`
	RankClass    string       `json:"rank_class,omitempty"`
	Reason       string       `json:"reason,omitempty"`
}

type RankingMetric struct {
	Name       string `json:"name"`
	Raw        int64  `json:"raw"`
	Percentile int    `json:"percentile"`
	Weight     int    `json:"weight"`
	RankClass  string `json:"rank_class"`
}

type Ranking struct {
	Score           int             `json:"score"`
	AvailableWeight int             `json:"available_weight"`
	Vector          []RankingMetric `json:"vector"`
}

type PrimarySize struct {
	Value int64  `json:"value"`
	Unit  string `json:"unit"`
}

type FileRow struct {
	ID              string      `json:"id"`
	Path            string      `json:"path"`
	Language        Language    `json:"language"`
	Confidence      Confidence  `json:"confidence"`
	SHA256          string      `json:"sha256"`
	Bytes           int64       `json:"bytes"`
	PhysicalLines   *int64      `json:"physical_lines,omitempty"`
	PrimarySize     PrimarySize `json:"primary_size"`
	Generated       bool        `json:"generated"`
	RankingEligible bool        `json:"ranking_eligible"`
	ParseFailure    string      `json:"parse_failure,omitempty"`
	Metrics         []Metric    `json:"metrics"`
	Ranking         Ranking     `json:"ranking"`
}

type OwnerRow struct {
	ID          string     `json:"id"`
	Path        string     `json:"path"`
	Language    Language   `json:"language"`
	Kind        string     `json:"kind"`
	DisplayName string     `json:"display_name"`
	StartLine   int        `json:"start_line"`
	EndLine     int        `json:"end_line"`
	Confidence  Confidence `json:"confidence"`
	Generated   bool       `json:"generated"`
	Metrics     []Metric   `json:"metrics"`
	Ranking     Ranking    `json:"ranking"`
}

type RegionRow struct {
	ID          string     `json:"id"`
	Path        string     `json:"path"`
	Language    Language   `json:"language"`
	Kind        string     `json:"kind"`
	DisplayName string     `json:"display_name"`
	StartLine   int        `json:"start_line"`
	EndLine     int        `json:"end_line"`
	Confidence  Confidence `json:"confidence"`
	Metrics     []Metric   `json:"metrics"`
	Ranking     Ranking    `json:"ranking"`
}

type AggregateMetric struct {
	Name  string `json:"name"`
	Value int64  `json:"value"`
	Unit  string `json:"unit"`
}

type LanguageAggregate struct {
	Language Language          `json:"language"`
	Files    int               `json:"files"`
	Bytes    int64             `json:"bytes"`
	Metrics  []AggregateMetric `json:"metrics"`
}

type RefactoringCandidate struct {
	Kind            string     `json:"kind"`
	TargetID        string     `json:"target_id"`
	Path            string     `json:"path"`
	RiskScore       int        `json:"risk_score"`
	AvailableWeight int        `json:"available_weight"`
	Confidence      Confidence `json:"confidence"`
	ReasonCodes     []string   `json:"reason_codes"`
}

type Warning struct {
	Code   string `json:"code"`
	Path   string `json:"path,omitempty"`
	Detail string `json:"detail"`
}

// Report is the complete immutable-by-convention analyzer result consumed by
// all renderers. It deliberately contains no absolute target root.
type Report struct {
	SchemaVersion         string                 `json:"schema_version"`
	ToolVersion           string                 `json:"tool_version"`
	RootID                string                 `json:"root_id"`
	CompletionStatus      string                 `json:"completion_status"`
	ScanConfiguration     ScanConfiguration      `json:"scan_configuration"`
	Exclusions            []Exclusion            `json:"exclusions"`
	CapabilityVersion     string                 `json:"capability_version"`
	Capabilities          []SurfaceCapability    `json:"capabilities"`
	DeferredCapabilities  []DeferredCapability   `json:"deferred_capabilities"`
	LanguageAggregates    []LanguageAggregate    `json:"language_aggregates"`
	Files                 []FileRow              `json:"files"`
	Owners                []OwnerRow             `json:"owners"`
	ProceduralRegions     []RegionRow            `json:"procedural_regions"`
	RefactoringCandidates []RefactoringCandidate `json:"refactoring_candidates"`
	Warnings              []Warning              `json:"warnings"`
	Fingerprint           string                 `json:"report_fingerprint"`
}
