package cli

import (
	"context"
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/hotspot"
)

func createCLIGitRepo(t *testing.T) (string, string, string) {
	t.Helper()
	dir := t.TempDir()
	root, err := filepath.EvalSymlinks(dir)
	if err != nil {
		t.Fatal(err)
	}

	runGit := func(args ...string) string {
		cmd := exec.Command("git", args...)
		cmd.Dir = root
		cmd.Env = append(os.Environ(),
			"GIT_AUTHOR_NAME=CLI Test",
			"GIT_AUTHOR_EMAIL=cli-test@example.com",
			"GIT_COMMITTER_NAME=CLI Test",
			"GIT_COMMITTER_EMAIL=cli-test@example.com",
			"GIT_CONFIG_NOSYSTEM=1",
			"GIT_AUTHOR_DATE=2026-01-01T00:00:00Z",
			"GIT_COMMITTER_DATE=2026-01-01T00:00:00Z",
		)
		out, err := cmd.CombinedOutput()
		if err != nil {
			t.Fatalf("git %v failed: %v\n%s", args, err, out)
		}
		return strings.TrimSpace(string(out))
	}

	runGit("init")
	runGit("config", "user.name", "CLI Test")
	runGit("config", "user.email", "cli-test@example.com")
	runGit("config", "commit.gpgsign", "false")

	// Commit 1: start
	if err := os.WriteFile(filepath.Join(root, "main.go"), []byte("package main\n\nfunc main() {\n\tprintln(\"v1\")\n}\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	runGit("add", ".")
	startOID := runGit("commit-tree", runGit("write-tree"), "-m", "initial commit")
	runGit("update-ref", "HEAD", startOID)

	// Commit 2: update
	if err := os.WriteFile(filepath.Join(root, "main.go"), []byte("package main\n\nfunc main() {\n\tprintln(\"v2\")\n\tprintln(\"added line\")\n}\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	runGit("add", ".")
	endOID := runGit("commit-tree", runGit("write-tree"), "-p", startOID, "-m", "update main")
	runGit("update-ref", "HEAD", endOID)

	return root, startOID, endOID
}

func TestCLIAnalyzeHistoryTerminalJSONMarkdown(t *testing.T) {
	root, startOID, endOID := createCLIGitRepo(t)

	for _, format := range []string{"terminal", "json", "markdown"} {
		arguments := []string{
			"--repository", root, "analyze", "hotspots",
			"--format", format,
			"--root-id", "cli-history-fixture",
			"--history-start", startOID,
			"--history-end", endOID,
			"--top", "5",
		}
		exit, stdout, stderr := runTest(t, context.Background(), arguments...)
		if exit != 0 || stderr != "" {
			t.Fatalf("format %s failed: exit=%d stderr=%q stdout=%q", format, exit, stderr, stdout)
		}

		switch format {
		case "terminal":
			if !strings.Contains(stdout, "Hotspot analysis:") {
				t.Fatalf("terminal output missing header: %q", stdout)
			}
			if !strings.Contains(stdout, "History (v2, first-parent integration):") || !strings.Contains(stdout, "available churn subtotal=") {
				t.Fatalf("terminal output missing history sections: %q", stdout)
			}
			if !strings.Contains(stdout, "Fingerprint: sha256:") {
				t.Fatalf("terminal output missing fingerprint: %q", stdout)
			}
		case "json":
			var report hotspot.ReportV2
			if err := json.Unmarshal([]byte(stdout), &report); err != nil {
				t.Fatalf("failed to decode JSON report: %v", err)
			}
			if report.SchemaVersion != hotspot.ReportSchemaV2 {
				t.Fatalf("expected schema %s, got %s", hotspot.ReportSchemaV2, report.SchemaVersion)
			}
			if report.History.CommitCount != 1 {
				t.Fatalf("expected 1 commit in history, got %d", report.History.CommitCount)
			}
			if strings.Contains(stdout, root) {
				t.Fatal("JSON output leaked absolute repository root")
			}
		case "markdown":
			if !strings.Contains(stdout, "# Hotspot analysis:") {
				t.Fatalf("markdown output missing header: %q", stdout)
			}
			if !strings.Contains(stdout, "## File history (v2)") {
				t.Fatalf("markdown output missing history summary: %q", stdout)
			}
			if !strings.Contains(stdout, "Churn (inserted + deleted lines)") {
				t.Fatalf("markdown output missing churn table: %q", stdout)
			}
		}
	}
}

func TestCLIAnalyzeHistoryFlagValidation(t *testing.T) {
	root, startOID, endOID := createCLIGitRepo(t)

	// Only --history-start provided
	exit, _, stderr := runTest(t, context.Background(),
		"--repository", root, "analyze", "hotspots",
		"--history-start", startOID,
	)
	if exit != 2 || !strings.Contains(stderr, "both --history-start and --history-end must be specified together") {
		t.Fatalf("expected missing history-end error, got exit=%d stderr=%q", exit, stderr)
	}

	// Only --history-end provided
	exit, _, stderr = runTest(t, context.Background(),
		"--repository", root, "analyze", "hotspots",
		"--history-end", endOID,
	)
	if exit != 2 || !strings.Contains(stderr, "both --history-start and --history-end must be specified together") {
		t.Fatalf("expected missing history-start error, got exit=%d stderr=%q", exit, stderr)
	}

	// Invalid hex OID
	exit, _, stderr = runTest(t, context.Background(),
		"--repository", root, "analyze", "hotspots",
		"--history-start", "not-a-valid-oid",
		"--history-end", endOID,
	)
	if exit != 1 && exit != 2 {
		t.Fatalf("expected failure for invalid OID, got exit=%d stderr=%q", exit, stderr)
	}
}

func TestCLIAnalyzeHistoryOutputFile(t *testing.T) {
	root, startOID, endOID := createCLIGitRepo(t)

	outputDir, err := filepath.EvalSymlinks(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	outputFile := filepath.Join(outputDir, "v2-report.json")

	arguments := []string{
		"--repository", root, "analyze", "hotspots",
		"--format", "json",
		"--history-start", startOID,
		"--history-end", endOID,
		"--output", outputFile,
	}
	exit, stdout, stderr := runTest(t, context.Background(), arguments...)
	if exit != 0 || stdout != "" || stderr != "" {
		t.Fatalf("output flag execution failed: exit=%d stdout=%q stderr=%q", exit, stdout, stderr)
	}

	data, err := os.ReadFile(outputFile)
	if err != nil {
		t.Fatalf("failed to read written output: %v", err)
	}

	var report hotspot.ReportV2
	if err := json.Unmarshal(data, &report); err != nil || report.SchemaVersion != hotspot.ReportSchemaV2 {
		t.Fatalf("invalid report content in output file: %v, report: %+v", err, report)
	}
}
