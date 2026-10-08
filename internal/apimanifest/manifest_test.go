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

func TestMethodsBindAcrossFiles(t *testing.T) {
	root := t.TempDir()
	for _, name := range []string{"phase", "routing", "evidence", "candidate", "provider", "skills"} {
		if err := os.MkdirAll(filepath.Join(root, name), 0700); err != nil {
			t.Fatal(err)
		}
	}
	for name, body := range map[string]string{
		"a_method.go": "package skills\nfunc (v *Value) Read() string { return \"x\" }\n",
		"z_type.go":   "package skills\ntype Value struct{}\n",
	} {
		if err := os.WriteFile(filepath.Join(root, "skills", name), []byte(body), 0600); err != nil {
			t.Fatal(err)
		}
	}
	for i := 0; i < 20; i++ {
		m, err := apimanifest.Generate(root)
		if err != nil {
			t.Fatal(err)
		}
		s := m.Packages[0]
		if len(s.Functions) != 0 || len(s.Types) != 1 || len(s.Types[0].Methods) != 1 || s.Types[0].Methods[0].Name != "Read" {
			t.Fatalf("method lost its receiver: %+v", s)
		}
	}
}
