package apimanifest_test

import (
	"encoding/json"
	"flag"
	"os"
	"path/filepath"
	"testing"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/internal/apimanifest"
)

var update = flag.Bool("update", false, "update docs/architecture/v0-12-apgr-go-api-manifest.json")

func TestAPIManifest_NoDrift(t *testing.T) {
	repoRoot := filepath.Join("..", "..")
	manifestPath := filepath.Join(repoRoot, "docs", "architecture", "v0-12-apgr-go-api-manifest.json")

	manifest, err := apimanifest.Generate(repoRoot)
	if err != nil {
		t.Fatalf("apimanifest.Generate failed: %v", err)
	}

	actualBytes, err := json.MarshalIndent(manifest, "", "  ")
	if err != nil {
		t.Fatalf("json.MarshalIndent failed: %v", err)
	}
	actualBytes = append(actualBytes, '\n')

	if *update {
		if err := os.WriteFile(manifestPath, actualBytes, 0644); err != nil {
			t.Fatalf("failed to update manifest file: %v", err)
		}
		t.Logf("Updated %s", manifestPath)
		return
	}

	expectedBytes, err := os.ReadFile(manifestPath)
	if err != nil {
		// If file does not exist yet, write it
		if os.IsNotExist(err) {
			if err := os.WriteFile(manifestPath, actualBytes, 0644); err != nil {
				t.Fatalf("failed to write initial manifest file: %v", err)
			}
			t.Logf("Created initial %s", manifestPath)
			return
		}
		t.Fatalf("failed to read %s: %v", manifestPath, err)
	}

	if string(actualBytes) != string(expectedBytes) {
		t.Fatalf("API manifest drift detected in %s! Run 'go test ./internal/apimanifest -update' to sync.", manifestPath)
	}
}
