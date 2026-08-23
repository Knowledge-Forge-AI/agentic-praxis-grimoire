package cli

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/hotspot"
)

func hotspotRoot(t *testing.T) string {
	t.Helper()
	root, err := filepath.EvalSymlinks(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "main.go"), []byte("package p\nfunc F() { if true { return } }\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "guide.md"), []byte("# Guide\n\nText.\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	return root
}

func TestAnalyzeHotspotsTerminalJSONMarkdownAndTop(t *testing.T) {
	root := hotspotRoot(t)
	for _, format := range []string{"terminal", "json", "markdown"} {
		arguments := []string{"--repository", root, "analyze", "hotspots", "--format", format, "--root-id", "cli-fixture", "--top", "1"}
		exit, stdout, stderr := runTest(t, context.Background(), arguments...)
		if exit != 0 || stderr != "" {
			t.Fatalf("%s = %d %q %q", format, exit, stdout, stderr)
		}
		switch format {
		case "terminal":
			if !strings.Contains(stdout, "Largest files") || !strings.Contains(stdout, "Fingerprint: sha256:") {
				t.Fatalf("terminal = %q", stdout)
			}
		case "json":
			var report hotspot.Report
			if err := json.Unmarshal([]byte(stdout), &report); err != nil || report.SchemaVersion != hotspot.ReportSchemaV1 || len(report.Files) != 2 {
				t.Fatalf("JSON = %#v %v", report, err)
			}
			if strings.Contains(stdout, root) {
				t.Fatal("canonical JSON leaked the absolute root")
			}
		case "markdown":
			if !strings.Contains(stdout, "## Table of contents") || !strings.Contains(stdout, "## Appendix: all analyzed files") {
				t.Fatalf("Markdown = %q", stdout)
			}
		}
	}
}

func TestAnalyzeHotspotsRequiresOneGlobalRootAndEnforcesLimits(t *testing.T) {
	exit, _, stderr := runTest(t, context.Background(), "analyze", "hotspots")
	if exit != 2 || !strings.Contains(stderr, "absolute clean --repository") {
		t.Fatalf("missing root = %d %q", exit, stderr)
	}
	root := hotspotRoot(t)
	exit, _, stderr = runTest(t, context.Background(), "--repository", root, "analyze", "hotspots", "--max-files", "1")
	if exit != 1 || !strings.Contains(stderr, "scan limit exceeded") {
		t.Fatalf("max files = %d %q", exit, stderr)
	}
	exit, _, stderr = runTest(t, context.Background(), "--repository", root, "analyze", "hotspots", "--format", "yaml")
	if exit != 2 || !strings.Contains(stderr, "format must be terminal, json, or markdown") {
		t.Fatalf("invalid format = %d %q", exit, stderr)
	}
}

func TestAnalyzeHotspotsOutputIsExclusiveAndOutsideTarget(t *testing.T) {
	root := hotspotRoot(t)
	outputRoot, err := filepath.EvalSymlinks(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	output := filepath.Join(outputRoot, "report.json")
	arguments := []string{"--repository", root, "analyze", "hotspots", "--format", "json", "--output", output}
	exit, stdout, stderr := runTest(t, context.Background(), arguments...)
	if exit != 0 || stdout != "" || stderr != "" {
		t.Fatalf("output = %d %q %q", exit, stdout, stderr)
	}
	content, err := os.ReadFile(output)
	if err != nil || !strings.Contains(string(content), `"schema_version":"apg.hotspot-report/v1"`) {
		t.Fatalf("output content = %q %v", content, err)
	}
	exit, _, stderr = runTest(t, context.Background(), arguments...)
	if exit != 1 || !strings.Contains(stderr, "output destination already exists") {
		t.Fatalf("overwrite = %d %q", exit, stderr)
	}
	inside := filepath.Join(root, "report.json")
	exit, _, stderr = runTest(t, context.Background(), "--repository", root, "analyze", "hotspots", "--format", "json", "--output", inside)
	if exit != 2 || !strings.Contains(stderr, "outside the analyzed root") {
		t.Fatalf("inside output = %d %q", exit, stderr)
	}
}
