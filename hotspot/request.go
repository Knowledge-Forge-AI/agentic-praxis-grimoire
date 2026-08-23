package hotspot

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"
)

const (
	defaultMaxFiles        = 50_000
	defaultMaxBytesPerFile = int64(16 * 1024 * 1024)
	defaultMaxTotalBytes   = int64(512 * 1024 * 1024)
	defaultMaxDuration     = 120 * time.Second
	defaultDisplayTopN     = 10
)

var rootIDPattern = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$`)

// DefaultRequest returns the mandatory bounded v1 defaults. Root remains
// subject to Analyze's absolute-clean, direct-directory validation.
func DefaultRequest(root string) Request {
	id := filepath.Base(root)
	if !rootIDPattern.MatchString(id) {
		id = ""
	}
	return Request{
		SchemaVersion: RequestSchemaV1, Root: root, RootID: id, ToolVersion: ProducerVersion,
		Limits:      Limits{MaxFiles: defaultMaxFiles, MaxBytesPerFile: defaultMaxBytesPerFile, MaxTotalBytes: defaultMaxTotalBytes, MaxDuration: defaultMaxDuration},
		DisplayTopN: defaultDisplayTopN,
	}
}

type requestJSON struct {
	SchemaVersion string      `json:"schema_version"`
	Root          string      `json:"root"`
	RootID        string      `json:"root_id"`
	ToolVersion   string      `json:"tool_version"`
	MaxFiles      int         `json:"max_files"`
	MaxBytesFile  int64       `json:"max_bytes_per_file"`
	MaxTotalBytes int64       `json:"max_total_bytes"`
	MaxDurationMS int64       `json:"max_duration_milliseconds"`
	DisplayTopN   int         `json:"display_top_n"`
	Filters       FiltersJSON `json:"filters"`
}

type FiltersJSON struct {
	DisableDefaultExclusions bool       `json:"disable_default_exclusions"`
	IncludeLanguages         []Language `json:"include_languages"`
	IncludePaths             []string   `json:"include_paths"`
	ExcludePaths             []string   `json:"exclude_paths"`
}

// ParseRequestJSON decodes the strict request schema and rejects duplicate or
// unknown consequence-bearing keys before validation by Analyze.
func ParseRequestJSON(content []byte) (Request, error) {
	if err := rejectDuplicateJSONKeys(content); err != nil {
		return Request{}, invalidRequest(err.Error())
	}
	decoder := json.NewDecoder(bytes.NewReader(content))
	decoder.DisallowUnknownFields()
	var wire requestJSON
	if err := decoder.Decode(&wire); err != nil {
		return Request{}, invalidRequest("request JSON is invalid")
	}
	if err := requireJSONEOF(decoder); err != nil {
		return Request{}, invalidRequest("request JSON has trailing content")
	}
	return Request{
		SchemaVersion: wire.SchemaVersion, Root: wire.Root, RootID: wire.RootID, ToolVersion: wire.ToolVersion,
		Limits:      Limits{MaxFiles: wire.MaxFiles, MaxBytesPerFile: wire.MaxBytesFile, MaxTotalBytes: wire.MaxTotalBytes, MaxDuration: time.Duration(wire.MaxDurationMS) * time.Millisecond},
		Filters:     Filters{DisableDefaultExclusions: wire.Filters.DisableDefaultExclusions, IncludeLanguages: wire.Filters.IncludeLanguages, IncludePaths: wire.Filters.IncludePaths, ExcludePaths: wire.Filters.ExcludePaths},
		DisplayTopN: wire.DisplayTopN,
	}, nil
}

func requireJSONEOF(decoder *json.Decoder) error {
	var extra any
	if err := decoder.Decode(&extra); err == io.EOF {
		return nil
	}
	return fmt.Errorf("extra JSON value")
}

func rejectDuplicateJSONKeys(content []byte) error {
	decoder := json.NewDecoder(bytes.NewReader(content))
	if err := walkDuplicateJSON(decoder); err != nil {
		return err
	}
	if err := requireJSONEOF(decoder); err != nil {
		return err
	}
	return nil
}

func walkDuplicateJSON(decoder *json.Decoder) error {
	token, err := decoder.Token()
	if err != nil {
		return err
	}
	delimiter, ok := token.(json.Delim)
	if !ok {
		return nil
	}
	if delimiter == '[' {
		for decoder.More() {
			if err := walkDuplicateJSON(decoder); err != nil {
				return err
			}
		}
		_, err = decoder.Token()
		return err
	}
	if delimiter != '{' {
		return fmt.Errorf("unexpected JSON delimiter")
	}
	seen := map[string]struct{}{}
	for decoder.More() {
		keyToken, keyErr := decoder.Token()
		if keyErr != nil {
			return keyErr
		}
		key, keyOK := keyToken.(string)
		if !keyOK {
			return fmt.Errorf("object key is not a string")
		}
		if _, duplicate := seen[key]; duplicate {
			return fmt.Errorf("duplicate JSON key %q", key)
		}
		seen[key] = struct{}{}
		if err := walkDuplicateJSON(decoder); err != nil {
			return err
		}
	}
	_, err = decoder.Token()
	return err
}

func validateRequest(request Request) (Request, error) {
	if request.SchemaVersion != RequestSchemaV1 {
		return Request{}, invalidRequest("unsupported schema version")
	}
	if request.Root == "" || !filepath.IsAbs(request.Root) || filepath.Clean(request.Root) != request.Root {
		return Request{}, invalidRequest("root must be an absolute clean path")
	}
	if !rootIDPattern.MatchString(request.RootID) {
		return Request{}, invalidRequest("root_id must be a safe logical identifier")
	}
	if request.ToolVersion == "" || len([]byte(request.ToolVersion)) > 128 {
		return Request{}, invalidRequest("tool version is invalid")
	}
	if err := validateRequestLimits(request); err != nil {
		return Request{}, err
	}
	if err := validateRequestFilters(request); err != nil {
		return Request{}, err
	}
	request.Filters.IncludeLanguages = append([]Language{}, request.Filters.IncludeLanguages...)
	request.Filters.IncludePaths = normalizedSortedPaths(request.Filters.IncludePaths)
	request.Filters.ExcludePaths = normalizedSortedPaths(request.Filters.ExcludePaths)
	sort.Slice(request.Filters.IncludeLanguages, func(i, j int) bool { return request.Filters.IncludeLanguages[i] < request.Filters.IncludeLanguages[j] })
	return request, nil
}

func validateRequestLimits(request Request) error {
	if request.Limits.MaxFiles <= 0 || request.Limits.MaxBytesPerFile <= 0 || request.Limits.MaxTotalBytes <= 0 || request.Limits.MaxDuration <= 0 {
		return invalidRequest("all scan limits must be positive")
	}
	if request.Limits.MaxBytesPerFile > request.Limits.MaxTotalBytes {
		return invalidRequest("per-file byte limit exceeds total byte limit")
	}
	if request.Limits.MaxDuration > 24*time.Hour {
		return invalidRequest("elapsed-time limit exceeds 24 hours")
	}
	if request.DisplayTopN <= 0 || request.DisplayTopN > 100 {
		return invalidRequest("display top-N must be between 1 and 100")
	}
	return nil
}

func validateRequestFilters(request Request) error {
	known := map[Language]bool{}
	for _, row := range frozenCapabilities() {
		for _, language := range row.Languages {
			known[language] = true
		}
	}
	seenLanguages := map[Language]bool{}
	for _, language := range request.Filters.IncludeLanguages {
		if !known[language] || seenLanguages[language] {
			return invalidRequest("include language is unknown or duplicated")
		}
		seenLanguages[language] = true
	}
	for _, paths := range [][]string{request.Filters.IncludePaths, request.Filters.ExcludePaths} {
		seen := map[string]bool{}
		for _, path := range paths {
			if path == "" || filepath.IsAbs(path) || filepath.Clean(path) != path || path == ".." || strings.HasPrefix(path, ".."+string(filepath.Separator)) || strings.Contains(path, "\\") {
				return invalidRequest("filter paths must be clean root-relative paths")
			}
			normalized := filepath.ToSlash(path)
			if seen[normalized] {
				return invalidRequest("filter paths must not be duplicated")
			}
			seen[normalized] = true
		}
	}
	return nil
}

func normalizedSortedPaths(values []string) []string {
	result := make([]string, len(values))
	for index, value := range values {
		result[index] = filepath.ToSlash(value)
	}
	sort.Strings(result)
	return result
}
