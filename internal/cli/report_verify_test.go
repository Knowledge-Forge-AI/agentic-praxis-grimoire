package cli

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestReportVerifyHelpAndUsage(t *testing.T) {
	// Top-level report help
	exit, stdout, stderr := runTest(t, context.Background(), "report", "--help")
	if exit != 0 || stderr != "" || !strings.Contains(stdout, "verify") || !strings.Contains(stdout, "--idempotent") {
		t.Fatalf("report --help = %d %q %q", exit, stdout, stderr)
	}
	exit, stdout, stderr = runTest(t, context.Background(), "report", "help")
	if exit != 0 || stderr != "" || !strings.Contains(stdout, "verify") {
		t.Fatalf("report help = %d %q %q", exit, stdout, stderr)
	}
	exit, stdout, stderr = runTest(t, context.Background(), "report", "-h")
	if exit != 0 || stderr != "" || !strings.Contains(stdout, "verify") {
		t.Fatalf("report -h = %d %q %q", exit, stdout, stderr)
	}

	// Top-level report with no args -> usage error (exit 2)
	exit, _, stderr = runTest(t, context.Background(), "report")
	if exit != 2 || !strings.Contains(stderr, "verify") {
		t.Fatalf("report (no args) = %d %q", exit, stderr)
	}

	// Verify help
	exit, stdout, stderr = runTest(t, context.Background(), "report", "verify", "--help")
	if exit != 0 || stderr != "" || !strings.Contains(stdout, "Usage: apgr report verify <path>") {
		t.Fatalf("verify --help = %d %q %q", exit, stdout, stderr)
	}
	exit, stdout, stderr = runTest(t, context.Background(), "report", "verify", "-h")
	if exit != 0 || stderr != "" || !strings.Contains(stdout, "Usage: apgr report verify <path>") {
		t.Fatalf("verify -h = %d %q %q", exit, stdout, stderr)
	}

	// Verify with no path -> usage error (exit 2)
	exit, _, stderr = runTest(t, context.Background(), "report", "verify")
	if exit != 2 || !strings.Contains(stderr, "report verify requires PATH") {
		t.Fatalf("verify (no path) = %d %q", exit, stderr)
	}

	// Verify with extra arguments -> usage error (exit 2)
	exit, _, stderr = runTest(t, context.Background(), "report", "verify", "path1", "path2")
	if exit != 2 || !strings.Contains(stderr, "report verify requires PATH") {
		t.Fatalf("verify (extra args) = %d %q", exit, stderr)
	}

	// Verify with empty string path -> usage error (exit 2)
	exit, _, stderr = runTest(t, context.Background(), "report", "verify", "")
	if exit != 2 || !strings.Contains(stderr, "report verify requires a non-empty PATH") {
		t.Fatalf("verify (empty path) = %d %q", exit, stderr)
	}
}

func TestReportPublicationHelpDistinguishesCanonicalAndLegacy(t *testing.T) {
	repository, _ := repositoryTest(t)
	outbox := filepath.Join(t.TempDir(), "uncreated-outbox")
	t.Setenv("APGR_OUTBOX_ROOT", outbox)
	for _, test := range []struct {
		command, legacy, legacyHelp string
	}{
		{"show", "git-show-report", showUsage},
		{"diff", "git-diff-report", diffUsage},
		{"operational", "append-operational-report", operationalUsage},
		{"ops", "append-operational-report", operationalUsage},
	} {
		args := []string{"--repository", repository, "--project", filepath.Base(repository), "--outbox-root", outbox, "report", test.command, "--help"}
		exit, stdout, stderr := runTest(t, context.Background(), args...)
		if exit != 0 || stderr != "" || !strings.HasPrefix(stdout, "Usage: apgr report ") || !strings.Contains(stdout, "--idempotent") {
			t.Fatalf("canonical %s help = %d %q %q", test.command, exit, stdout, stderr)
		}
		args = []string{"--repository", repository, "legacy", test.legacy, "--help"}
		exit, stdout, stderr = runTest(t, context.Background(), args...)
		if exit != 0 || stderr != "" || stdout != test.legacyHelp || strings.Contains(stdout, "--idempotent") {
			t.Fatalf("legacy %s help = %d %q %q", test.legacy, exit, stdout, stderr)
		}
	}
	if _, err := os.Stat(outbox); !os.IsNotExist(err) {
		t.Fatalf("help prepared an outbox: %v", err)
	}
}

func TestReportVerifyRealFilesNoRepoOrOutboxAndNoMutation(t *testing.T) {
	repository, commit := repositoryTest(t)
	outbox := filepath.Join(t.TempDir(), "outbox")
	base := explicit(repository, outbox)

	// 1. Create a real show report
	showArgs := append(append([]string{}, base...), "report", "show", "CLI-VERIFY", commit, "status.md", "passed", "gate")
	exit, _, stderr := runTest(t, context.Background(), showArgs...)
	if exit != 0 || stderr != "" {
		t.Fatalf("show = %d %q", exit, stderr)
	}
	showPath := filepath.Join(outbox, filepath.Base(repository), "CLI-VERIFY", "CLI-VERIFY.git.show.report.txt")

	// Read content and stat before verify
	contentBefore, err := os.ReadFile(showPath)
	if err != nil {
		t.Fatal(err)
	}
	infoBefore, err := os.Stat(showPath)
	if err != nil {
		t.Fatal(err)
	}

	// Run verify with NO repository or outbox options
	exit, stdout, stderr := runTest(t, context.Background(), "report", "verify", showPath)
	if exit != 0 || stderr != "" || strings.TrimSpace(stdout) != "verified 1 record" {
		t.Fatalf("verify show = %d %q %q", exit, stdout, stderr)
	}

	// Assert no mutation
	contentAfter, err := os.ReadFile(showPath)
	if err != nil {
		t.Fatal(err)
	}
	infoAfter, err := os.Stat(showPath)
	if err != nil {
		t.Fatal(err)
	}
	if string(contentBefore) != string(contentAfter) {
		t.Fatal("report file content was mutated by verify")
	}
	if infoBefore.Mode() != infoAfter.Mode() {
		t.Fatalf("report file mode changed: before=%v after=%v", infoBefore.Mode(), infoAfter.Mode())
	}

	// 2. Append an operational record
	source := filepath.Join(t.TempDir(), "ops.txt")
	body := []byte("report_schema: operational-report-v1\nphase: CLI-VERIFY\noutcome: passed\nprimary_commit: " + commit + "\n")
	if err := os.WriteFile(source, body, 0o600); err != nil {
		t.Fatal(err)
	}
	opsArgs := append(append([]string{}, base...), "report", "ops", "CLI-VERIFY", source, "passed", "gate", "--related-commit", commit, "--related-git-report-id", "GIT-SHOW-REPORT-"+commit)
	exit, _, stderr = runTest(t, context.Background(), opsArgs...)
	if exit != 0 || stderr != "" {
		t.Fatalf("ops = %d %q", exit, stderr)
	}

	// Verify multi-record report without repo or outbox
	exit, stdout, stderr = runTest(t, context.Background(), "report", "verify", showPath)
	if exit != 0 || stderr != "" || strings.TrimSpace(stdout) != "verified 2 records" {
		t.Fatalf("verify 2 records = %d %q %q", exit, stdout, stderr)
	}
}

func TestReportVerifyMissingEmptyAndMalformedFiles(t *testing.T) {
	tempDir := t.TempDir()

	// 1. Missing file -> exit 1, IO error
	missingPath := filepath.Join(tempDir, "nonexistent.report.txt")
	exit, stdout, stderr := runTest(t, context.Background(), "report", "verify", missingPath)
	if exit != 1 || stdout != "" || !strings.Contains(stderr, "verify io error") {
		t.Fatalf("verify missing = %d %q %q", exit, stdout, stderr)
	}

	// 2. Empty file -> exit 1, empty report diagnostic
	emptyPath := filepath.Join(tempDir, "empty.report.txt")
	if err := os.WriteFile(emptyPath, []byte(""), 0o600); err != nil {
		t.Fatal(err)
	}
	exit, stdout, stderr = runTest(t, context.Background(), "report", "verify", emptyPath)
	if exit != 1 || stdout != "" || !strings.Contains(stderr, "empty report") {
		t.Fatalf("verify empty = %d %q %q", exit, stdout, stderr)
	}

	// Whitespace-only file -> exit 1, empty report diagnostic
	whitespacePath := filepath.Join(tempDir, "whitespace.report.txt")
	if err := os.WriteFile(whitespacePath, []byte("   \n\t\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	exit, stdout, stderr = runTest(t, context.Background(), "report", "verify", whitespacePath)
	if exit != 1 || stdout != "" || !strings.Contains(stderr, "empty report") {
		t.Fatalf("verify whitespace = %d %q %q", exit, stdout, stderr)
	}

	// 3. Malformed file -> exit 1
	malformedPath := filepath.Join(tempDir, "corrupt.report.txt")
	if err := os.WriteFile(malformedPath, []byte("not a canonical report envelope\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	exit, stdout, stderr = runTest(t, context.Background(), "report", "verify", malformedPath)
	if exit != 1 || stdout != "" || stderr == "" {
		t.Fatalf("verify malformed = %d %q %q", exit, stdout, stderr)
	}
}

func TestIdempotentPublicationAndConflict(t *testing.T) {
	repository, commit := repositoryTest(t)
	outbox := filepath.Join(t.TempDir(), "outbox")
	base := explicit(repository, outbox)

	// --- SHOW IDEMPOTENCY ---
	showArgs := append(append([]string{}, base...), "report", "show", "CLI-IDEM-SHOW", commit, "status.md", "passed", "gate", "--idempotent")
	exit, stdout, stderr := runTest(t, context.Background(), showArgs...)
	if exit != 0 || stderr != "" || !strings.Contains(stdout, "git-show-report: appended ") {
		t.Fatalf("initial idempotent show = %d %q %q", exit, stdout, stderr)
	}

	// Exact retry with --idempotent outputs already-present
	exit, stdout, stderr = runTest(t, context.Background(), showArgs...)
	if exit != 0 || stderr != "" || !strings.Contains(stdout, "git-show-report: already-present ") {
		t.Fatalf("retry idempotent show = %d %q %q", exit, stdout, stderr)
	}

	// Default append without --idempotent appends
	defaultShowArgs := append(append([]string{}, base...), "report", "show", "CLI-IDEM-SHOW", commit, "status.md", "passed", "gate")
	exit, stdout, stderr = runTest(t, context.Background(), defaultShowArgs...)
	if exit != 0 || stderr != "" || !strings.Contains(stdout, "git-show-report: appended ") {
		t.Fatalf("default show = %d %q %q", exit, stdout, stderr)
	}

	// --- DIFF IDEMPOTENCY ---
	if err := os.WriteFile(filepath.Join(repository, "tracked.txt"), []byte("diff change\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	diffArgs := append(append([]string{}, base...), "report", "diff", "CLI-IDEM-DIFF", "passed", "gate", "--idempotent")
	exit, stdout, stderr = runTest(t, context.Background(), diffArgs...)
	if exit != 0 || stderr != "" || !strings.Contains(stdout, "git-diff-report: appended ") {
		t.Fatalf("initial idempotent diff = %d %q %q", exit, stdout, stderr)
	}

	// Exact retry with --idempotent outputs already-present
	exit, stdout, stderr = runTest(t, context.Background(), diffArgs...)
	if exit != 0 || stderr != "" || !strings.Contains(stdout, "git-diff-report: already-present ") {
		t.Fatalf("retry idempotent diff = %d %q %q", exit, stdout, stderr)
	}

	// --- OPERATIONAL IDEMPOTENCY AND CONFLICT ---
	opsSource := filepath.Join(t.TempDir(), "ops.txt")
	body := []byte("report_schema: operational-report-v1\nphase: CLI-IDEM-OPS\noutcome: passed\nprimary_commit: " + commit + "\n")
	if err := os.WriteFile(opsSource, body, 0o600); err != nil {
		t.Fatal(err)
	}
	// First create show report for relationship
	showForOps := append(append([]string{}, base...), "report", "show", "CLI-IDEM-OPS", commit, "status.md", "passed", "gate")
	exit, _, stderr = runTest(t, context.Background(), showForOps...)
	if exit != 0 || stderr != "" {
		t.Fatalf("show for ops = %d %q", exit, stderr)
	}

	opsArgs := append(append([]string{}, base...), "report", "ops", "CLI-IDEM-OPS", opsSource, "passed", "gate", "--related-commit", commit, "--related-git-report-id", "GIT-SHOW-REPORT-"+commit, "--idempotent")
	exit, stdout, stderr = runTest(t, context.Background(), opsArgs...)
	if exit != 0 || stderr != "" || !strings.Contains(stdout, "append-operational-report: appended ") {
		t.Fatalf("initial idempotent ops = %d %q %q", exit, stdout, stderr)
	}

	// Exact retry with --idempotent outputs already-present
	exit, stdout, stderr = runTest(t, context.Background(), opsArgs...)
	if exit != 0 || stderr != "" || !strings.Contains(stdout, "append-operational-report: already-present ") {
		t.Fatalf("retry idempotent ops = %d %q %q", exit, stdout, stderr)
	}

	// Replay conflict: same commit (same record ID) but different final-gate metadata
	conflictShowArgs := append(append([]string{}, base...), "report", "show", "CLI-IDEM-SHOW", commit, "status.md", "passed", "different-gate", "--idempotent")
	exit, _, stderr = runTest(t, context.Background(), conflictShowArgs...)
	if exit != 1 || !strings.Contains(stderr, "replay conflict") {
		t.Fatalf("conflicting idempotent show = %d %q", exit, stderr)
	}
}

func TestLegacyCommandsRejectIdempotentOption(t *testing.T) {
	repository, commit := repositoryTest(t)
	root := filepath.Join(t.TempDir(), "legacy")
	t.Setenv("GIT_SHOW_REPORT_ROOT", root)

	// Legacy show with --idempotent rejected
	args := []string{"--repository", repository, "legacy", "git-show-report", "LEGACY", commit, "status.md", "passed", "gate", "--idempotent"}
	exit, _, stderr := runTest(t, context.Background(), args...)
	if exit != 2 || !strings.Contains(stderr, "Usage: git-show-report") {
		t.Fatalf("legacy show --idempotent exit=%d %q", exit, stderr)
	}

	// Legacy diff with --idempotent rejected
	diffArgs := []string{"--repository", repository, "legacy", "git-diff-report", "LEGACY", "passed", "gate", "--idempotent"}
	exit, _, stderr = runTest(t, context.Background(), diffArgs...)
	if exit != 2 || !strings.Contains(stderr, "Usage: git-diff-report") {
		t.Fatalf("legacy diff --idempotent exit=%d %q", exit, stderr)
	}

	// Legacy operational with --idempotent rejected
	source := filepath.Join(t.TempDir(), "ops.txt")
	if err := os.WriteFile(source, []byte("evidence\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	opsArgs := []string{"--repository", repository, "legacy", "append-operational-report", "LEGACY", source, "passed", "gate", "--idempotent"}
	exit, _, stderr = runTest(t, context.Background(), opsArgs...)
	if exit != 2 || !strings.Contains(stderr, "Usage: append-operational-report") {
		t.Fatalf("legacy ops --idempotent exit=%d %q", exit, stderr)
	}
}

func TestPositionalMetadataRespectAndOptionOrdering(t *testing.T) {
	repository, commit := repositoryTest(t)
	outbox := filepath.Join(t.TempDir(), "outbox")
	base := explicit(repository, outbox)

	// Final-gate containing "idempotent" is treated as positional metadata, NOT stripped flag
	args := append(append([]string{}, base...), "report", "show", "CLI-POS", commit, "status.md", "passed", "idempotent")
	exit, stdout, stderr := runTest(t, context.Background(), args...)
	if exit != 0 || stderr != "" || !strings.Contains(stdout, "git-show-report: appended ") {
		t.Fatalf("positional value containing idempotent = %d %q %q", exit, stdout, stderr)
	}

	// Duplicate --idempotent flag rejected
	dupArgs := append(append([]string{}, base...), "report", "show", "CLI-DUP", commit, "status.md", "passed", "gate", "--idempotent", "--idempotent")
	exit, _, stderr = runTest(t, context.Background(), dupArgs...)
	if exit != 2 || !strings.Contains(stderr, "--idempotent may be specified only once") {
		t.Fatalf("duplicate --idempotent exit=%d %q", exit, stderr)
	}

	// Unknown option rejected
	badArgs := append(append([]string{}, base...), "report", "show", "CLI-BAD", commit, "status.md", "passed", "gate", "--unknown")
	exit, _, stderr = runTest(t, context.Background(), badArgs...)
	if exit != 2 || !strings.Contains(stderr, "unknown report show option") {
		t.Fatalf("unknown option exit=%d %q", exit, stderr)
	}
}
