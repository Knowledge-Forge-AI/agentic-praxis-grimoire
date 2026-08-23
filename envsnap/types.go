package envsnap

import (
	"context"
	"time"
)

const (
	// ProfileSchemaV1 is the canonical environment profile schema identifier.
	ProfileSchemaV1 = "apg.environment-profile/v1"
	// SnapshotSchemaV1 is the canonical environment snapshot schema identifier.
	SnapshotSchemaV1 = "apg.environment-snapshot/v1"
	// SensitiveNamePolicyV1 is the fail-closed token-aware name policy.
	SensitiveNamePolicyV1 = "apg.environment-sensitive-name-policy/v1"
	// ProducerVersion is the source-build producer identity recorded by Capture
	// when the caller does not inject its build identity.
	ProducerVersion = "devel"
	// MaxSnapshotBytes bounds one stored snapshot read.
	MaxSnapshotBytes int64 = 10 << 20
)

// Validator identifies one of the twelve supported profile value validators.
type Validator string

const (
	ValidatorBool      Validator = "bool"
	ValidatorCommand   Validator = "command"
	ValidatorHost      Validator = "host"
	ValidatorInteger   Validator = "integer"
	ValidatorPath      Validator = "path"
	ValidatorPathList  Validator = "path_list"
	ValidatorPort      Validator = "port"
	ValidatorRawSafe   Validator = "raw_safe"
	ValidatorToken     Validator = "token"
	ValidatorTokenList Validator = "token_list"
	ValidatorURI       Validator = "uri"
	ValidatorURIOrPath Validator = "uri_or_path"
)

// Profile is a named, versioned, explicit environment allowlist.
type Profile struct {
	SchemaVersion string         `json:"schema_version"`
	ProfileID     string         `json:"profile_id"`
	Entries       []ProfileEntry `json:"entries"`
}

// ProfileEntry describes one exact environment variable.
type ProfileEntry struct {
	Name        string `json:"name"`
	Validator   string `json:"validator"`
	MaxBytes    int    `json:"max_bytes"`
	Required    bool   `json:"required"`
	Default     string `json:"default,omitempty"`
	Description string `json:"description,omitempty"`
}

// SnapshotProvenance identifies the explicit capture context. These fields
// are metadata and are excluded from content fingerprints.
type SnapshotProvenance struct {
	Context string `json:"context"`
	Host    string `json:"host,omitempty"`
	Shell   string `json:"shell,omitempty"`
}

// Snapshot is a canonical, validated environment capture.
type Snapshot struct {
	SchemaVersion      string             `json:"schema_version"`
	ProfileID          string             `json:"profile_id"`
	ProfileFingerprint string             `json:"profile_fingerprint"`
	ProducerVersion    string             `json:"producer_version"`
	Provenance         SnapshotProvenance `json:"provenance"`
	CapturedAt         time.Time          `json:"captured_at"`
	Entries            []SnapshotEntry    `json:"entries"`
	MissingOptional    []string           `json:"missing_optional"`
	ContentFingerprint string             `json:"content_fingerprint"`

	// Age and Stale are derived by Load and are never serialized.
	Age   time.Duration `json:"-"`
	Stale bool          `json:"-"`
}

// SnapshotEntry is one deterministic captured value. Source is normally
// "capture" for Capture results.
type SnapshotEntry struct {
	Name      string `json:"name"`
	Validator string `json:"validator"`
	Value     string `json:"value"`
	Source    string `json:"source"`
}

// Clock supplies timestamps to Capture and Load. A nil Clock uses UTC wall
// time. It is intentionally tiny so tests and embedders can control time.
type Clock interface {
	Now() time.Time
}

// CaptureRequest supplies all data Capture may read.
type CaptureRequest struct {
	Profile         Profile
	Environment     map[string]string
	Provenance      SnapshotProvenance
	ProducerVersion string
	Clock           Clock
}

// StoreDisposition describes whether a canonical file was published.
type StoreDisposition string

const (
	DispositionStored    StoreDisposition = "stored"
	DispositionUnchanged StoreDisposition = "unchanged"
)

// StoreRequest supplies an exact storage root and snapshot to publish.
type StoreRequest struct {
	StorageRoot string
	Snapshot    Snapshot
	// Profile is required so Store can validate every snapshot value and its
	// profile identity before publication.
	Profile *Profile
	Timeout time.Duration
}

// StoredSnapshot reports the canonical path and publication outcome.
type StoredSnapshot struct {
	Path               string
	Disposition        StoreDisposition
	Snapshot           Snapshot
	ContentFingerprint string
}

// LoadRequest identifies one stored snapshot and its expected profile.
type LoadRequest struct {
	StorageRoot     string
	ProfileID       string
	ExpectedProfile *Profile
	MaxAge          time.Duration
	Clock           Clock
}

// ResolutionMode controls whether the caller's base map participates.
type ResolutionMode string

const (
	ModeIsolated ResolutionMode = "isolated"
	ModeOverlay  ResolutionMode = "overlay"
	// SourceCapture identifies values captured from the explicit source map.
	SourceCapture = "capture"
	// SourceSnapshot identifies values contributed by a snapshot during resolve.
	SourceSnapshot = "snapshot"
	// SourceOverride identifies explicit resolve overrides.
	SourceOverride = "override"
	// SourceBase identifies values contributed by an Overlay base map.
	SourceBase = "base"
)

// ResolveRequest supplies a validated profile, snapshot, and explicit maps.
// Profile is required; a nil profile is rejected so overrides cannot bypass
// profile membership, validators, or sensitive-name policy.
type ResolveRequest struct {
	Snapshot  Snapshot
	Mode      ResolutionMode
	Base      map[string]string
	Overrides map[string]string
	Profile   *Profile
}

// ValueProvenance records the layer that supplied one resolved name.
type ValueProvenance struct {
	Name   string `json:"name"`
	Source string `json:"source"`
}

// ResolvedEnvironment is a fresh environment map with deterministic source
// metadata. The returned maps are caller-owned and never alias request maps.
type ResolvedEnvironment struct {
	Mode        ResolutionMode
	Environment map[string]string
	Provenance  map[string]ValueProvenance
}

// Compile-time assertions keep the frozen public call surface visible.
var _ func(context.Context, CaptureRequest) (Snapshot, error) = Capture
var _ func(context.Context, StoreRequest) (StoredSnapshot, error) = Store
var _ func(context.Context, LoadRequest) (Snapshot, error) = Load
var _ func(context.Context, ResolveRequest) (ResolvedEnvironment, error) = Resolve
