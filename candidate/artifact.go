package candidate

import (
	"errors"
	"fmt"
	"path"
	"strings"
)

// ArtifactManifestSchema is the accepted manifest envelope identifier.
const ArtifactManifestSchema = "agent-phase-artifact-manifest-v1"

// Artifact describes a single immutable evidence file emitted during phase execution.
type Artifact struct {
	ArtifactID   string `json:"artifact_id"`
	RunID        string `json:"run_id"`
	PhaseID      string `json:"phase_id"`
	RelativePath string `json:"relative_path"`
	MediaType    string `json:"media_type"`
	ByteSize     int64  `json:"byte_size"`
	SHA256       string `json:"sha256"`
}

// ArtifactManifest lists all artifacts emitted by a single phase run.
type ArtifactManifest struct {
	Schema    string     `json:"schema"`
	ProjectID string     `json:"project_id"`
	PhaseID   string     `json:"phase_id"`
	Artifacts []Artifact `json:"artifacts"`
}

var (
	ErrInvalidPath = errors.New("candidate: artifact relative path is invalid or attempts traversal")
	ErrInvalidSize = errors.New("candidate: artifact byte_size must be non-negative")
	ErrInvalidSHA  = errors.New("candidate: artifact sha256 must be 64 hexadecimal characters")
)

// ValidateArtifact verifies path safety, non-negative size, and SHA-256 formatting.
func ValidateArtifact(a Artifact) error {
	if strings.TrimSpace(a.ArtifactID) == "" {
		return errors.New("candidate: artifact_id must be non-empty")
	}
	if strings.TrimSpace(a.RunID) == "" {
		return errors.New("candidate: run_id must be non-empty")
	}
	if strings.TrimSpace(a.PhaseID) == "" {
		return errors.New("candidate: phase_id must be non-empty")
	}

	cleaned := path.Clean(strings.ReplaceAll(a.RelativePath, "\\", "/"))
	if cleaned == "." || cleaned == ".." || strings.HasPrefix(cleaned, "../") || strings.HasPrefix(cleaned, "/") {
		return fmt.Errorf("%w: %q", ErrInvalidPath, a.RelativePath)
	}

	if a.ByteSize < 0 {
		return ErrInvalidSize
	}

	if !isValidHexDigest(a.SHA256, 64) {
		return fmt.Errorf("%w: got %q", ErrInvalidSHA, a.SHA256)
	}

	return nil
}

// ValidateManifest validates all artifacts in the manifest.
func ValidateManifest(m ArtifactManifest) error {
	if m.Schema != ArtifactManifestSchema {
		return fmt.Errorf("candidate: unexpected manifest schema: %q", m.Schema)
	}
	if strings.TrimSpace(m.ProjectID) == "" {
		return errors.New("candidate: project_id must be non-empty")
	}
	if strings.TrimSpace(m.PhaseID) == "" {
		return errors.New("candidate: phase_id must be non-empty")
	}
	seenPaths := make(map[string]bool)
	for i, a := range m.Artifacts {
		if err := ValidateArtifact(a); err != nil {
			return fmt.Errorf("candidate: artifact %d invalid: %w", i, err)
		}
		if seenPaths[a.RelativePath] {
			return fmt.Errorf("candidate: duplicate relative path in manifest: %q", a.RelativePath)
		}
		seenPaths[a.RelativePath] = true
	}
	return nil
}
