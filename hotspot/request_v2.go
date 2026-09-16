package hotspot

import (
	"bytes"
	"encoding/json"
	"math"
	"regexp"
	"time"
	"unicode/utf8"
)

var fullOIDPattern = regexp.MustCompile(`^[0-9a-f]{40}$|^[0-9a-f]{64}$`)

// DefaultRequestV2 returns a RequestV2 with mandatory scan and history defaults.
func DefaultRequestV2(root, startOID, endOID string) RequestV2 {
	v1Req := DefaultRequest(root)
	return RequestV2{
		SchemaVersion: RequestSchemaV2,
		Root:          v1Req.Root,
		RootID:        v1Req.RootID,
		ToolVersion:   v1Req.ToolVersion,
		Limits:        v1Req.Limits,
		Filters:       v1Req.Filters,
		DisplayTopN:   v1Req.DisplayTopN,
		History: HistoryRequest{
			StartOID: startOID,
			EndOID:   endOID,
			Limits: HistoryLimits{
				MaxCommits:                  DefaultMaxCommits,
				MaxPathTransitions:          DefaultMaxPathTransitions,
				MaxBlobBytes:                DefaultMaxBlobBytes,
				MaxTotalInputBytes:          DefaultMaxTotalInputBytes,
				MaxComparisonCellsPerPair:   DefaultMaxComparisonCellsPerPair,
				MaxAggregateComparisonCells: DefaultMaxAggregateComparisonCells,
			},
		},
	}
}

type requestV2JSON struct {
	SchemaVersion string             `json:"schema_version"`
	Root          string             `json:"root"`
	RootID        string             `json:"root_id"`
	ToolVersion   string             `json:"tool_version"`
	MaxFiles      int                `json:"max_files"`
	MaxBytesFile  int64              `json:"max_bytes_per_file"`
	MaxTotalBytes int64              `json:"max_total_bytes"`
	MaxDurationMS int64              `json:"max_duration_milliseconds"`
	DisplayTopN   int                `json:"display_top_n"`
	Filters       FiltersJSON        `json:"filters"`
	History       historyRequestJSON `json:"history"`
}

type historyRequestJSON struct {
	StartOID string            `json:"start_oid"`
	EndOID   string            `json:"end_oid"`
	Limits   historyLimitsJSON `json:"limits"`
}

type historyLimitsJSON struct {
	MaxCommits                  int   `json:"max_commits"`
	MaxPathTransitions          int   `json:"max_path_transitions"`
	MaxBlobBytes                int64 `json:"max_blob_bytes"`
	MaxTotalInputBytes          int64 `json:"max_total_input_bytes"`
	MaxComparisonCellsPerPair   int64 `json:"max_comparison_cells_per_pair"`
	MaxAggregateComparisonCells int64 `json:"max_aggregate_comparison_cells"`
}

// ParseRequestV2JSON decodes strict v2 JSON and rejects duplicate or unknown keys.
func ParseRequestV2JSON(content []byte) (RequestV2, error) {
	if len(content) > 65536 || !utf8.Valid(content) {
		return RequestV2{}, invalidRequest("request must be UTF-8 and at most 65536 bytes")
	}
	if err := rejectDuplicateJSONKeys(content); err != nil {
		return RequestV2{}, invalidRequest(err.Error())
	}
	decoder := json.NewDecoder(bytes.NewReader(content))
	decoder.DisallowUnknownFields()
	var wire requestV2JSON
	if err := decoder.Decode(&wire); err != nil {
		return RequestV2{}, invalidRequest("request JSON is invalid")
	}
	if err := requireJSONEOF(decoder); err != nil {
		return RequestV2{}, invalidRequest("request JSON has trailing content")
	}
	if wire.MaxDurationMS < 0 || wire.MaxDurationMS > math.MaxInt64/int64(time.Millisecond) {
		return RequestV2{}, invalidRequest("duration overflows")
	}
	req := RequestV2{
		SchemaVersion: wire.SchemaVersion,
		Root:          wire.Root,
		RootID:        wire.RootID,
		ToolVersion:   wire.ToolVersion,
		Limits: Limits{
			MaxFiles:        wire.MaxFiles,
			MaxBytesPerFile: wire.MaxBytesFile,
			MaxTotalBytes:   wire.MaxTotalBytes,
			MaxDuration:     time.Duration(wire.MaxDurationMS) * time.Millisecond,
		},
		Filters: Filters{
			DisableDefaultExclusions: wire.Filters.DisableDefaultExclusions,
			IncludeLanguages:         wire.Filters.IncludeLanguages,
			IncludePaths:             wire.Filters.IncludePaths,
			ExcludePaths:             wire.Filters.ExcludePaths,
		},
		DisplayTopN: wire.DisplayTopN,
		History: HistoryRequest{
			StartOID: wire.History.StartOID,
			EndOID:   wire.History.EndOID,
			Limits: HistoryLimits{
				MaxCommits:                  wire.History.Limits.MaxCommits,
				MaxPathTransitions:          wire.History.Limits.MaxPathTransitions,
				MaxBlobBytes:                wire.History.Limits.MaxBlobBytes,
				MaxTotalInputBytes:          wire.History.Limits.MaxTotalInputBytes,
				MaxComparisonCellsPerPair:   wire.History.Limits.MaxComparisonCellsPerPair,
				MaxAggregateComparisonCells: wire.History.Limits.MaxAggregateComparisonCells,
			},
		},
	}
	return validateRequestV2(req)
}

func validateRequestV2(req RequestV2) (RequestV2, error) {
	if req.SchemaVersion != RequestSchemaV2 {
		return RequestV2{}, invalidRequest("unsupported schema version for v2 request")
	}
	v1Equivalent := Request{
		SchemaVersion: RequestSchemaV1,
		Root:          req.Root,
		RootID:        req.RootID,
		ToolVersion:   req.ToolVersion,
		Limits:        req.Limits,
		Filters:       req.Filters,
		DisplayTopN:   req.DisplayTopN,
	}
	validatedV1, err := validateRequest(v1Equivalent)
	if err != nil {
		return RequestV2{}, err
	}
	req.Root = validatedV1.Root
	req.RootID = validatedV1.RootID
	req.ToolVersion = validatedV1.ToolVersion
	req.Limits = validatedV1.Limits
	req.Filters = validatedV1.Filters
	req.DisplayTopN = validatedV1.DisplayTopN

	if !fullOIDPattern.MatchString(req.History.StartOID) {
		return RequestV2{}, invalidRequest("history start_oid must be a full 40- or 64-character hexadecimal identifier")
	}
	if !fullOIDPattern.MatchString(req.History.EndOID) {
		return RequestV2{}, invalidRequest("history end_oid must be a full 40- or 64-character hexadecimal identifier")
	}
	if len(req.History.StartOID) != len(req.History.EndOID) {
		return RequestV2{}, invalidRequest("history start_oid and end_oid must have the same hash length")
	}

	if len(req.Filters.IncludeLanguages) > 0 {
		return RequestV2{}, invalidRequest("history language filters are unsupported; select literal paths")
	}
	limits := req.History.Limits
	if limits.MaxCommits <= 0 || limits.MaxCommits > DefaultMaxCommits {
		return RequestV2{}, invalidRequest("max_commits must be between 1 and 256")
	}
	if limits.MaxPathTransitions <= 0 || limits.MaxPathTransitions > DefaultMaxPathTransitions {
		return RequestV2{}, invalidRequest("max_path_transitions must be between 1 and 50000")
	}
	if limits.MaxBlobBytes <= 0 || limits.MaxBlobBytes > DefaultMaxBlobBytes {
		return RequestV2{}, invalidRequest("max_blob_bytes must be between 1 and 4194304")
	}
	if limits.MaxTotalInputBytes <= 0 || limits.MaxTotalInputBytes > DefaultMaxTotalInputBytes {
		return RequestV2{}, invalidRequest("max_total_input_bytes must be between 1 and 134217728")
	}
	if limits.MaxBlobBytes > limits.MaxTotalInputBytes {
		return RequestV2{}, invalidRequest("max_blob_bytes exceeds max_total_input_bytes")
	}
	if limits.MaxComparisonCellsPerPair <= 0 || limits.MaxComparisonCellsPerPair > DefaultMaxComparisonCellsPerPair {
		return RequestV2{}, invalidRequest("max_comparison_cells_per_pair must be between 1 and 4000000")
	}
	if limits.MaxAggregateComparisonCells <= 0 || limits.MaxAggregateComparisonCells > DefaultMaxAggregateComparisonCells {
		return RequestV2{}, invalidRequest("max_aggregate_comparison_cells must be between 1 and 64000000")
	}

	return req, nil
}
