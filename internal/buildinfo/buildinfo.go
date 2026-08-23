// Package buildinfo owns deterministic APGR binary identity reporting.
package buildinfo

import (
	"encoding/json"
	"errors"
	"runtime"
	"runtime/debug"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/schema"
	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/skills"
)

// BuildInfoSchema identifies the stable build-info JSON contract used by
// release manifests and runtime wrapper validation.
const BuildInfoSchema = "apg.build-info/v1"

// Version and CorpusFingerprint are release-build injection points. Source
// builds deliberately retain development sentinels rather than duplicating
// package or corpus authority in Go source.
var (
	Version           = "devel"
	CorpusFingerprint = "devel"
)

// Target is a supported binary target.
type Target struct {
	GOOS   string `json:"goos"`
	GOARCH string `json:"goarch"`
}

// SchemaVersions derives every report schema version from package schema.
type SchemaVersions struct {
	Envelope    int `json:"envelope"`
	GitShow     int `json:"git_show"`
	GitDiff     int `json:"git_diff"`
	Operational int `json:"operational"`
}

// Info is the stable machine-readable build-information contract.
type Info struct {
	SchemaVersion             string         `json:"schema_version"`
	Version                   string         `json:"version"`
	ModulePath                string         `json:"module_path"`
	ModuleVersion             string         `json:"module_version"`
	Target                    string         `json:"target"`
	GoVersion                 string         `json:"go_version"`
	CorpusFingerprint         string         `json:"corpus_fingerprint"`
	EmbeddedCorpusFingerprint string         `json:"embedded_corpus_fingerprint"`
	CorpusFingerprintVerified bool           `json:"corpus_fingerprint_verified"`
	ReportSchemaVersion       SchemaVersions `json:"report_schema_versions"`
	SupportedTargets          []Target       `json:"supported_targets"`
}

// Current returns build information without host names, paths, time, or other
// machine-specific state.
func Current() Info {
	modulePath := "github.com/Knowledge-Forge-AI/agentic-praxis-grimoire"
	moduleVersion := "devel"
	if details, ok := debug.ReadBuildInfo(); ok {
		if details.Main.Path != "" {
			modulePath = details.Main.Path
		}
		if details.Main.Version != "" && details.Main.Version != "(devel)" {
			moduleVersion = details.Main.Version
		}
	}
	show, showOK := schema.GitShowRecord.FormatVersion()
	diff, diffOK := schema.GitDiffRecord.FormatVersion()
	ops, opsOK := schema.OperationalRecord.FormatVersion()
	if !showOK || !diffOK || !opsOK {
		panic("invalid canonical schema format version")
	}
	embeddedFingerprint := ""
	if metadata, err := skills.Metadata(); err == nil {
		embeddedFingerprint = metadata.Fingerprint
	}
	return Info{
		SchemaVersion: BuildInfoSchema,
		Version:       Version, ModulePath: modulePath, ModuleVersion: moduleVersion,
		Target: runtime.GOOS + "/" + runtime.GOARCH, GoVersion: runtime.Version(),
		CorpusFingerprint: CorpusFingerprint, EmbeddedCorpusFingerprint: embeddedFingerprint,
		CorpusFingerprintVerified: CorpusFingerprint != "devel" && CorpusFingerprint == embeddedFingerprint,
		ReportSchemaVersion:       SchemaVersions{Envelope: schema.EnvelopeVersion, GitShow: show, GitDiff: diff, Operational: ops},
		SupportedTargets:          []Target{{GOOS: "darwin", GOARCH: "arm64"}, {GOOS: "linux", GOARCH: "amd64"}, {GOOS: "linux", GOARCH: "arm64"}},
	}
}

// JSON returns stable compact JSON terminated by one newline.
func JSON() ([]byte, error) {
	current := Current()
	if current.EmbeddedCorpusFingerprint == "" {
		return nil, errors.New("embedded corpus identity is unavailable")
	}
	if current.Version != "devel" && !current.CorpusFingerprintVerified {
		return nil, errors.New("injected and embedded corpus identities disagree")
	}
	content, err := json.Marshal(current)
	if err != nil {
		return nil, err
	}
	return append(content, '\n'), nil
}
