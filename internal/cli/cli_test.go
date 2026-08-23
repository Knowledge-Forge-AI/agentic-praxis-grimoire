package cli

import (
	"bytes"
	"context"
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/internal/buildinfo"
	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/report"
)

func runTest(t *testing.T, ctx context.Context, arguments ...string) (int, string, string) {
	t.Helper()
	var stdout, stderr bytes.Buffer
	exit := Run(ctx, arguments, &stdout, &stderr)
	return exit, stdout.String(), stderr.String()
}

func gitTest(t *testing.T, repository string, arguments ...string) string {
	t.Helper()
	command := exec.Command("git", append([]string{"-C", repository}, arguments...)...)
	command.Env = append(os.Environ(), "GIT_AUTHOR_DATE=2030-01-02T03:04:05+00:00", "GIT_COMMITTER_DATE=2030-01-02T03:04:05+00:00")
	output, err := command.CombinedOutput()
	if err != nil {
		t.Fatalf("git %v: %v: %s", arguments, err, output)
	}
	return strings.TrimSpace(string(output))
}

func repositoryTest(t *testing.T) (string, string) {
	t.Helper()
	base, err := filepath.EvalSymlinks(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	repository := filepath.Join(base, "repository")
	if err := os.Mkdir(repository, 0o700); err != nil {
		t.Fatal(err)
	}
	gitTest(t, repository, "init", "-q", "-b", "main")
	gitTest(t, repository, "config", "user.name", "CLI Test")
	gitTest(t, repository, "config", "user.email", "cli@example.invalid")
	if err := os.WriteFile(filepath.Join(repository, "tracked.txt"), []byte("base\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	gitTest(t, repository, "add", "tracked.txt")
	gitTest(t, repository, "commit", "-q", "-m", "base")
	return repository, gitTest(t, repository, "rev-parse", "HEAD")
}

func explicit(repository, outbox string) []string {
	return []string{"--repository", repository, "--outbox-root", outbox, "--project", filepath.Base(repository)}
}

func TestTopLevelHelpVersionAndBuildInfo(t *testing.T) {
	exit, stdout, stderr := runTest(t, context.Background(), "--help")
	if exit != 0 || !strings.Contains(stdout, "report recover") || stderr != "" {
		t.Fatalf("help = %d %q %q", exit, stdout, stderr)
	}
	exit, stdout, stderr = runTest(t, context.Background(), "--version")
	if exit != 0 || stdout != "apgr devel\n" || stderr != "" {
		t.Fatalf("version = %d %q %q", exit, stdout, stderr)
	}
	exit, stdout, stderr = runTest(t, context.Background(), "build-info")
	if exit != 0 || stderr != "" {
		t.Fatalf("build-info = %d %q", exit, stderr)
	}
	var info buildinfo.Info
	if err := json.Unmarshal([]byte(stdout), &info); err != nil {
		t.Fatal(err)
	}
	if info.Version != "devel" || len(info.SupportedTargets) != 3 {
		t.Fatalf("build info = %#v", info)
	}
}

func TestSkillsListAndContextReport(t *testing.T) {
	exit, stdout, stderr := runTest(t, context.Background(), "skills", "list")
	if exit != 0 || stderr != "" {
		t.Fatalf("list = %d %q", exit, stderr)
	}
	names := strings.Split(strings.TrimSpace(stdout), "\n")
	if len(names) != 39 || names[0] != "agentic-praxis-grimoire-workflow" || names[len(names)-1] != "zunit-test-profile" {
		t.Fatalf("names = %d %q %q", len(names), names[0], names[len(names)-1])
	}
	exit, stdout, stderr = runTest(t, context.Background(), "skills", "context-report")
	if exit != 0 || stderr != "" {
		t.Fatalf("context = %d %q", exit, stderr)
	}
	var report struct {
		SkillCount   int   `json:"skill_count"`
		Discoverable int   `json:"discoverable_skill_count"`
		Bytes        int   `json:"total_bytes"`
		Characters   int   `json:"total_characters"`
		Malformed    []any `json:"malformed"`
	}
	if err := json.Unmarshal([]byte(stdout), &report); err != nil {
		t.Fatal(err)
	}
	if report.SkillCount != 39 || report.Discoverable != 39 || report.Bytes != 9504 || report.Characters != 9492 || len(report.Malformed) != 0 {
		t.Fatalf("context = %#v", report)
	}
	for _, arguments := range [][]string{{"skills", "list", "--json", "--format", "json"}, {"skills", "list", "--format"}, {"skills", "context-report", "--format", "yaml"}} {
		exit, _, _ = runTest(t, context.Background(), arguments...)
		if exit != 2 {
			t.Fatalf("usage %v = %d", arguments, exit)
		}
	}
}

func TestSkillsResolveAndMaterialize(t *testing.T) {
	request := `{"budget":{"max_body_bytes":null,"max_description_bytes":null,"max_initial_context_bytes":null,"prompt_overhead_bytes":0},"capabilities":[],"consumer":{"architecture":"","kind":"codex","materialization_form":"flat_directory","operating_system":"","provider_constraints":["filesystem_skill_discovery","isolated_apg_root"]},"eager_bodies":false,"explicit_skill_ids":["planning-repository-work"],"languages":[],"repository_characteristics":[],"runtimes":[],"schema_version":"apg.skill-bundle-request/v1","test_frameworks":[],"work_class":""}`
	var stdout, stderr bytes.Buffer
	exit := RunWithInput(context.Background(), []string{"skills", "resolve", "--stdin"}, strings.NewReader(request), &stdout, &stderr)
	if exit != 0 || stderr.String() != "" || !strings.HasSuffix(stdout.String(), "\n") {
		t.Fatalf("resolve = %d %q %q", exit, stdout.String(), stderr.String())
	}
	resultFile := filepath.Join(t.TempDir(), "result.json")
	if err := os.WriteFile(resultFile, stdout.Bytes(), 0o600); err != nil {
		t.Fatal(err)
	}
	parent, err := filepath.EvalSymlinks(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	if err := os.Chmod(parent, 0o700); err != nil {
		t.Fatal(err)
	}
	exit, stdoutValue, stderrValue := runTest(t, context.Background(), "skills", "materialize", "--result", resultFile, "--destination-parent", parent)
	if exit != 0 || stderrValue != "" {
		t.Fatalf("materialize = %d %q", exit, stderrValue)
	}
	var materialized struct {
		Root          string `json:"root"`
		SelectedFiles []any  `json:"selected_files"`
	}
	if err := json.Unmarshal([]byte(stdoutValue), &materialized); err != nil {
		t.Fatal(err)
	}
	if len(materialized.SelectedFiles) != 1 {
		t.Fatalf("materialized = %#v", materialized)
	}
	if _, err := os.Stat(filepath.Join(materialized.Root, "planning-repository-work", "SKILL.md")); err != nil {
		t.Fatal(err)
	}

	stdout.Reset()
	stderr.Reset()
	exit = RunWithInput(context.Background(), []string{"skills", "resolve", "--stdin", "--request", resultFile}, strings.NewReader(request), &stdout, &stderr)
	if exit != 2 {
		t.Fatalf("conflicting input = %d %q", exit, stderr.String())
	}
}

func TestCanonicalShowOperationalPathAndRecovery(t *testing.T) {
	repository, commit := repositoryTest(t)
	outbox := filepath.Join(t.TempDir(), "outbox")
	base := explicit(repository, outbox)
	arguments := append(append([]string{}, base...), "report", "show", "CLI-SHOW", commit, "status.md", "passed", "gate")
	exit, stdout, stderr := runTest(t, context.Background(), arguments...)
	if exit != 0 || stderr != "" || !strings.HasPrefix(stdout, "git-show-report: appended ") {
		t.Fatalf("show = %d %q %q", exit, stdout, stderr)
	}
	path := filepath.Join(outbox, filepath.Base(repository), "CLI-SHOW", "CLI-SHOW.git.show.report.txt")
	content, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	records, err := report.ParseRecords(content)
	if err != nil || len(records) != 1 {
		t.Fatalf("show records = %d err=%v", len(records), err)
	}
	source := filepath.Join(t.TempDir(), "ops.txt")
	body := []byte("report_schema: operational-report-v1\nphase: CLI-SHOW\noutcome: passed\nprimary_commit: " + commit + "\n")
	if err := os.WriteFile(source, body, 0o600); err != nil {
		t.Fatal(err)
	}
	arguments = append(append([]string{}, base...), "report", "ops", "CLI-SHOW", source, "passed", "gate", "--related-commit", commit, "--related-git-report-id", records[0].ID)
	exit, _, stderr = runTest(t, context.Background(), arguments...)
	if exit != 0 || stderr != "" {
		t.Fatalf("operational = %d %q", exit, stderr)
	}
	content, err = os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	records, err = report.ParseRecords(content)
	if err != nil || len(records) != 2 {
		t.Fatalf("associated records = %d err=%v", len(records), err)
	}

	pathArguments := []string{"--outbox-root", outbox, "--project", filepath.Base(repository), "report", "path", "--phase", "CLI-SHOW", "--kind", "show"}
	exit, stdout, stderr = runTest(t, context.Background(), pathArguments...)
	if exit != 0 || strings.TrimSpace(stdout) != path || stderr != "" {
		t.Fatalf("path = %d %q %q", exit, stdout, stderr)
	}
	reversedPathArguments := []string{"--outbox-root", outbox, "--project", filepath.Base(repository), "report", "path", "--kind", "show", "--phase", "CLI-SHOW"}
	exit, stdout, stderr = runTest(t, context.Background(), reversedPathArguments...)
	if exit != 0 || strings.TrimSpace(stdout) != path || stderr != "" {
		t.Fatalf("reversed path = %d %q %q", exit, stdout, stderr)
	}
	recoverArguments := append(append([]string{}, base...), "report", "recover", "--phase", "CLI-NONE")
	exit, stdout, stderr = runTest(t, context.Background(), recoverArguments...)
	if exit != 0 || stdout != "no transaction\n" || stderr != "" {
		t.Fatalf("recover = %d %q %q", exit, stdout, stderr)
	}
}

func TestDiffAndRecoveryMarker(t *testing.T) {
	repository, _ := repositoryTest(t)
	if err := os.WriteFile(filepath.Join(repository, "tracked.txt"), []byte("changed\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	outbox := filepath.Join(t.TempDir(), "outbox")
	base := explicit(repository, outbox)
	arguments := append(append([]string{}, base...), "report", "diff", "CLI-DIFF", "passed", "gate")
	exit, _, stderr := runTest(t, context.Background(), arguments...)
	if exit != 0 || stderr != "" {
		t.Fatalf("diff = %d %q", exit, stderr)
	}
	directory := filepath.Join(outbox, filepath.Base(repository), "CLI-DIFF")
	marker := filepath.Join(directory, ".phase.transaction")
	if err := os.WriteFile(marker, []byte("agent-report-transaction-v1\nphase: CLI-DIFF\ntarget: CLI-DIFF.git.diff.report.txt\nstale: CLI-DIFF.git.show.report.txt,CLI-DIFF.ops.report.txt\ntoken: interrupted\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	arguments = append(append([]string{}, base...), "report", "recover", "--phase", "CLI-DIFF")
	exit, stdout, stderr := runTest(t, context.Background(), arguments...)
	if exit != 0 || stdout != "recovered\n" || stderr != "" {
		t.Fatalf("recover marker = %d %q %q", exit, stdout, stderr)
	}
	if _, err := os.Stat(marker); !os.IsNotExist(err) {
		t.Fatal("transaction marker remains")
	}
	prePhase := "CLI-PRE"
	preDirectory := filepath.Join(outbox, filepath.Base(repository), prePhase)
	if err := os.Mkdir(preDirectory, 0o700); err != nil {
		t.Fatal(err)
	}
	preMarker := filepath.Join(preDirectory, ".phase.transaction")
	if err := os.WriteFile(preMarker, []byte("agent-report-transaction-v1\nphase: CLI-PRE\ntarget: CLI-PRE.git.show.report.txt\nstale: CLI-PRE.git.diff.report.txt,CLI-PRE.ops.report.txt\ntoken: interrupted\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	arguments = append(append([]string{}, base...), "report", "recover", "--phase", prePhase)
	exit, stdout, stderr = runTest(t, context.Background(), arguments...)
	if exit != 0 || stdout != "recovered\n" || stderr != "" {
		t.Fatalf("pre-publication recover = %d %q %q", exit, stdout, stderr)
	}
	if _, err := os.Stat(preMarker); !os.IsNotExist(err) {
		t.Fatal("pre-publication marker remains")
	}
	if _, err := os.Stat(filepath.Join(preDirectory, "CLI-PRE.git.show.report.txt")); !os.IsNotExist(err) {
		t.Fatal("pre-publication recovery created a target")
	}
}

func TestOperationalSourceSafetyAndCancellation(t *testing.T) {
	repository, _ := repositoryTest(t)
	outbox := filepath.Join(t.TempDir(), "outbox")
	base := explicit(repository, outbox)
	source := filepath.Join(t.TempDir(), "ops.txt")
	if err := os.WriteFile(source, []byte("evidence\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	link := filepath.Join(t.TempDir(), "link.txt")
	if err := os.Symlink(source, link); err != nil {
		t.Fatal(err)
	}
	arguments := append(append([]string{}, base...), "report", "ops", "CLI-SAFE", link, "passed", "gate")
	exit, _, _ := runTest(t, context.Background(), arguments...)
	if exit != 1 {
		t.Fatalf("symlink exit = %d", exit)
	}
	hardlink := filepath.Join(t.TempDir(), "hard.txt")
	if err := os.Link(source, hardlink); err != nil {
		t.Fatal(err)
	}
	arguments[len(arguments)-3] = hardlink
	exit, _, _ = runTest(t, context.Background(), arguments...)
	if exit != 1 {
		t.Fatalf("hard link exit = %d", exit)
	}
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	arguments = append(append([]string{}, base...), "report", "show", "CLI-CANCEL", strings.Repeat("a", 40), "status.md", "passed", "gate")
	exit, _, stderr := runTest(t, ctx, arguments...)
	if exit != 1 || !strings.Contains(stderr, "interrupted") {
		t.Fatalf("canceled = %d %q", exit, stderr)
	}
}

func TestHistoricalLegacyOmnibus(t *testing.T) {
	repository, commit := repositoryTest(t)
	root := filepath.Join(t.TempDir(), "legacy")
	t.Setenv("GIT_SHOW_REPORT_ROOT", root)
	arguments := []string{"--repository", repository, "legacy", "git-show-report", "LEGACY", commit, "status.md", "passed", "gate"}
	exit, stdout, stderr := runTest(t, context.Background(), arguments...)
	want := filepath.Join(root, filepath.Base(repository), "LEGACY.report.txt")
	if exit != 0 || stderr != "" || !strings.HasSuffix(strings.TrimSpace(stdout), " to "+want) {
		t.Fatalf("legacy show = %d %q %q", exit, stdout, stderr)
	}
	metadata, err := os.Stat(want)
	if err != nil || metadata.Mode().Perm() != 0o600 {
		t.Fatalf("legacy artifact = %v err=%v", metadata, err)
	}
}
