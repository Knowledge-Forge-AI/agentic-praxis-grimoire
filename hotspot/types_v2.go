package hotspot

const (
	RequestSchemaV2    = "apg.hotspot-request/v2"
	ReportSchemaV2     = "apg.hotspot-report/v2"
	CapabilityMatrixV2 = "apg.hotspot-capabilities/v2"
	HistoryPolicyV2    = "first-parent-path-lf-lcs/v1"
)

const (
	DefaultMaxCommits                  = 256
	DefaultMaxPathTransitions          = 50_000
	DefaultMaxBlobBytes                = int64(4 * 1024 * 1024)   // 4 MiB
	DefaultMaxTotalInputBytes          = int64(128 * 1024 * 1024) // 128 MiB
	DefaultMaxComparisonCellsPerPair   = int64(4_000_000)
	DefaultMaxAggregateComparisonCells = int64(64_000_000)
)

// WorkingTreeStatus classifies working tree state relative to the end commit blob.
type WorkingTreeStatus string

const (
	WorkingTreeClean      WorkingTreeStatus = "clean"
	WorkingTreeNotScanned WorkingTreeStatus = "not-scanned"
	WorkingTreeModified   WorkingTreeStatus = "modified"
	WorkingTreeUntracked  WorkingTreeStatus = "untracked"
	WorkingTreeDeleted    WorkingTreeStatus = "deleted"
)

// HistoryLimits defines bounded resource budgets for Git history traversal and diffing.
type HistoryLimits struct {
	MaxCommits                  int   `json:"max_commits"`
	MaxPathTransitions          int   `json:"max_path_transitions"`
	MaxBlobBytes                int64 `json:"max_blob_bytes"`
	MaxTotalInputBytes          int64 `json:"max_total_input_bytes"`
	MaxComparisonCellsPerPair   int64 `json:"max_comparison_cells_per_pair"`
	MaxAggregateComparisonCells int64 `json:"max_aggregate_comparison_cells"`
}

// HistoryRequest specifies the history range and resource limits for v2 analysis.
type HistoryRequest struct {
	StartOID string        `json:"start_oid"`
	EndOID   string        `json:"end_oid"`
	Limits   HistoryLimits `json:"limits"`
}

// RequestV2 identifies one exact root and history configuration for v2 analysis.
type RequestV2 struct {
	SchemaVersion string         `json:"schema_version"`
	Root          string         `json:"root"`
	RootID        string         `json:"root_id"`
	ToolVersion   string         `json:"tool_version"`
	Limits        Limits         `json:"limits"`
	Filters       Filters        `json:"filters"`
	DisplayTopN   int            `json:"display_top_n"`
	History       HistoryRequest `json:"history"`
}

// ScanConfigurationV2 records the exact configuration used for a v2 report.
type ScanConfigurationV2 struct {
	RequestSchemaVersion     string        `json:"request_schema_version"`
	MaxFiles                 int           `json:"max_files"`
	MaxBytesPerFile          int64         `json:"max_bytes_per_file"`
	MaxTotalBytes            int64         `json:"max_total_bytes"`
	MaxDurationMilliseconds  int64         `json:"max_duration_milliseconds"`
	DefaultExclusionsEnabled bool          `json:"default_exclusions_enabled"`
	IncludeLanguages         []Language    `json:"include_languages"`
	IncludePaths             []string      `json:"include_paths"`
	ExcludePaths             []string      `json:"exclude_paths"`
	DisplayTopN              int           `json:"display_top_n"`
	HistoryStartOID          string        `json:"history_start_oid"`
	HistoryEndOID            string        `json:"history_end_oid"`
	HistoryLimits            HistoryLimits `json:"history_limits"`
}

// FileHistory records file-level churn, growth, transitions, and status.
type FileHistory struct {
	StartOID           string            `json:"start_blob_oid"`
	EndOID             string            `json:"end_blob_oid"`
	ChurnUnit          string            `json:"churn_unit"`
	GrowthUnit         string            `json:"growth_unit"`
	Path               string            `json:"path"`
	WorkingTreeStatus  WorkingTreeStatus `json:"working_tree_status"`
	TransitionCount    int               `json:"transition_count"`
	Churn              *int64            `json:"churn,omitempty"`
	Growth             *int64            `json:"growth,omitempty"`
	ChurnAvailability  Availability      `json:"churn_availability"`
	GrowthAvailability Availability      `json:"growth_availability"`
	StartLines         *int64            `json:"start_lines,omitempty"`
	EndLines           *int64            `json:"end_lines,omitempty"`
}

// FileRowV2 extends FileRow with optional file history metrics.
type FileRowV2 struct {
	ID              string       `json:"id"`
	Path            string       `json:"path"`
	Language        Language     `json:"language"`
	Confidence      Confidence   `json:"confidence"`
	SHA256          string       `json:"sha256,omitempty"`
	Bytes           int64        `json:"bytes"`
	PhysicalLines   *int64       `json:"physical_lines,omitempty"`
	PrimarySize     PrimarySize  `json:"primary_size"`
	Generated       bool         `json:"generated"`
	RankingEligible bool         `json:"ranking_eligible"`
	ParseFailure    string       `json:"parse_failure,omitempty"`
	Metrics         []Metric     `json:"metrics"`
	Ranking         Ranking      `json:"ranking"`
	History         *FileHistory `json:"history,omitempty"`
}

// HistorySummary holds aggregated and per-path history findings.
// TotalBlobsRead, TotalInputBytes and AggregateCells are execution diagnostics,
// excluded from both history and report semantic fingerprints.
type HistorySummary struct {
	Policy              string        `json:"policy"`
	Commits             []string      `json:"commits"`
	UnavailablePaths    int           `json:"unavailable_paths"`
	ID                  string        `json:"id"`
	StartOID            string        `json:"start_oid"`
	EndOID              string        `json:"end_oid"`
	ObjectFormat        string        `json:"object_format"`
	CommitCount         int           `json:"commit_count"`
	PathTransitionCount int           `json:"path_transition_count"`
	TotalBlobsRead      int           `json:"total_blobs_read"`
	TotalInputBytes     int64         `json:"total_input_bytes"`
	AggregateCells      int64         `json:"aggregate_cells"`
	TotalChurn          int64         `json:"available_churn_subtotal"`
	NetGrowth           int64         `json:"available_growth_subtotal"`
	Limits              HistoryLimits `json:"limits"`
	Files               []FileHistory `json:"files"`
}

// ReportV2 is the complete immutable v2 report containing structural and history data.
type ReportV2 struct {
	SchemaVersion         string                 `json:"schema_version"`
	ToolVersion           string                 `json:"tool_version"`
	RootID                string                 `json:"root_id"`
	CompletionStatus      string                 `json:"completion_status"`
	ScanConfiguration     ScanConfigurationV2    `json:"scan_configuration"`
	Exclusions            []Exclusion            `json:"exclusions"`
	CapabilityVersion     string                 `json:"capability_version"`
	Capabilities          []SurfaceCapability    `json:"capabilities"`
	DeferredCapabilities  []DeferredCapability   `json:"deferred_capabilities"`
	LanguageAggregates    []LanguageAggregate    `json:"language_aggregates"`
	Files                 []FileRowV2            `json:"files"`
	Owners                []OwnerRow             `json:"owners"`
	ProceduralRegions     []RegionRow            `json:"procedural_regions"`
	RefactoringCandidates []RefactoringCandidate `json:"refactoring_candidates"`
	History               HistorySummary         `json:"history"`
	Warnings              []Warning              `json:"warnings"`
	Fingerprint           string                 `json:"report_fingerprint"`
}
