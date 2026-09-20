package candidate_test

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"testing"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/candidate"
)

func TestValidateCandidate_Valid(t *testing.T) {
	c := candidate.CandidateIdentity{
		CandidateID:       "cand-1",
		Generation:        1,
		ProducerRole:      "Producer",
		ProducerAttemptID: "att-1",
		Commit:            "4885f5f290fe6adc0d763cc8a284ac1179be5c90",
		TreeDigest:        "0ec1c98f51e3b6419e4ab0f3d25fa120aaffb1f8",
	}
	if err := candidate.ValidateCandidate(c); err != nil {
		t.Fatalf("expected valid candidate, got: %v", err)
	}
}

func TestValidateArtifact_Valid(t *testing.T) {
	a := candidate.Artifact{
		ArtifactID:   "art-1",
		RunID:        "run-1",
		PhaseID:      "APG150",
		RelativePath: "docs/plan.md",
		MediaType:    "text/markdown",
		ByteSize:     1024,
		SHA256:       "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
	}
	if err := candidate.ValidateArtifact(a); err != nil {
		t.Fatalf("expected valid artifact, got: %v", err)
	}
}

func TestValidateArtifact_PathTraversalRejected(t *testing.T) {
	cases := []string{
		"../escape.txt",
		"/absolute/path.txt",
		"foo/../../escape.txt",
		"",
		".",
	}
	for _, p := range cases {
		t.Run(p, func(t *testing.T) {
			a := candidate.Artifact{
				ArtifactID:   "art-1",
				RunID:        "run-1",
				PhaseID:      "APG150",
				RelativePath: p,
				MediaType:    "text/plain",
				ByteSize:     10,
				SHA256:       "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
			}
			err := candidate.ValidateArtifact(a)
			if err == nil {
				t.Fatalf("expected path traversal rejection for %q, got nil", p)
			}
			if !errors.Is(err, candidate.ErrInvalidPath) {
				t.Errorf("expected ErrInvalidPath, got: %v", err)
			}
		})
	}
}

func TestCandidateArtifact_GoldenVectors(t *testing.T) {
	path := filepath.Join("..", "testing", "fixtures", "conformance", "candidate_artifact_vectors.json")
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("failed to read %s: %v", path, err)
	}

	var fixture struct {
		SampleCandidate      candidate.CandidateIdentity `json:"sample_candidate"`
		SampleArtifact       candidate.Artifact          `json:"sample_artifact"`
		InvalidRelativePaths []string                    `json:"invalid_relative_paths"`
	}

	if err := json.Unmarshal(data, &fixture); err != nil {
		t.Fatalf("failed to parse %s: %v", path, err)
	}

	if err := candidate.ValidateCandidate(fixture.SampleCandidate); err != nil {
		t.Errorf("sample candidate invalid: %v", err)
	}

	if err := candidate.ValidateArtifact(fixture.SampleArtifact); err != nil {
		t.Errorf("sample artifact invalid: %v", err)
	}

	for _, p := range fixture.InvalidRelativePaths {
		a := fixture.SampleArtifact
		a.RelativePath = p
		if err := candidate.ValidateArtifact(a); err == nil {
			t.Errorf("expected invalid path for %q, got nil", p)
		}
	}
}
