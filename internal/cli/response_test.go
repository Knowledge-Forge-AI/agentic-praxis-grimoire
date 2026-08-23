package cli

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestResponseRecordAndCaptureAliasesUseExactInput(t *testing.T) {
	outbox := filepath.Join(t.TempDir(), "outbox")
	base := []string{"--outbox-root", outbox, "--project", "project"}
	exit, stdout, stderr := runTestWithInput(t, context.Background(), strings.NewReader("stdin\x00\xff"), append(base, "response", "record", "--phase", "APG100")...)
	if exit != 0 || stderr != "" {
		t.Fatalf("record = %d, stdout %q, stderr %q", exit, stdout, stderr)
	}
	first := filepath.Join(outbox, "project", "APG100", "APG100.001.response.md")
	content, err := os.ReadFile(first)
	if err != nil || string(content) != "stdin\x00\xff" {
		t.Fatalf("record content = %q, err = %v", content, err)
	}
	source := filepath.Join(t.TempDir(), "response.md")
	if err := os.WriteFile(source, []byte("file\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	exit, stdout, stderr = runTestWithInput(t, context.Background(), strings.NewReader("ignored"), append(base, "response", "capture", "--phase", "APG100", "--file", source)...)
	if exit != 0 || stderr != "" {
		t.Fatalf("capture = %d, stdout %q, stderr %q", exit, stdout, stderr)
	}
	second := filepath.Join(outbox, "project", "APG100", "APG100.002.response.md")
	content, err = os.ReadFile(second)
	if err != nil || string(content) != "file\n" {
		t.Fatalf("capture content = %q, err = %v", content, err)
	}
	if strings.TrimSpace(stdout) != second {
		t.Fatalf("capture output = %q, want %q", stdout, second)
	}
}

func TestResponseImplicitRepositoryProjectAndExplicitMismatch(t *testing.T) {
	outbox := filepath.Join(t.TempDir(), "outbox")
	repository := filepath.Join(t.TempDir(), "repository")
	if err := os.Mkdir(repository, 0o700); err != nil {
		t.Fatal(err)
	}
	exit, stdout, stderr := runTestWithInput(t, context.Background(), strings.NewReader("body"), "--repository", repository, "--outbox-root", outbox, "response", "--phase", "APG100")
	if exit != 0 || stderr != "" {
		t.Fatalf("implicit project = %d, stdout %q, stderr %q", exit, stdout, stderr)
	}
	want := filepath.Join(outbox, "repository", "APG100", "APG100.001.response.md")
	if strings.TrimSpace(stdout) != want {
		t.Fatalf("implicit project output = %q, want %q", stdout, want)
	}
	exit, _, stderr = runTestWithInput(t, context.Background(), strings.NewReader("body"), "--repository", repository, "--outbox-root", outbox, "--project", "other", "response", "--phase", "APG100")
	if exit != 2 || !strings.Contains(stderr, "must match the repository basename") {
		t.Fatalf("mismatch = %d, stderr %q", exit, stderr)
	}
}

func TestResponseUsageAndUnsupportedGlobalAliasesAreBounded(t *testing.T) {
	outbox := filepath.Join(t.TempDir(), "outbox")
	cases := [][]string{
		{"--outbox-root", outbox, "--project", "project", "response"},
		{"--outbox-root", outbox, "--project", "project", "response", "--phase", "bad/name"},
		{"--outbox-root", outbox, "--project", "project", "response", "--input", "-", "--file", "-", "--phase", "APG100"},
		{"--outbox-root", outbox, "--project", "project", "response", "--project-root", "/tmp", "--phase", "APG100"},
		{"--outbox-root", outbox, "--project", "project", "response", "--apgr-home", "/tmp", "--phase", "APG100"},
	}
	for _, arguments := range cases {
		exit, _, _ := runTestWithInput(t, context.Background(), strings.NewReader("body"), arguments...)
		if exit != 2 {
			t.Fatalf("arguments %v exit = %d, want 2", arguments, exit)
		}
	}
}

func TestResponseHelpAndCancellationPreserveExitClasses(t *testing.T) {
	exit, stdout, stderr := runTestWithInput(t, context.Background(), strings.NewReader(""), "response", "--help")
	if exit != 0 || stderr != "" || !strings.Contains(stdout, "--input PATH") {
		t.Fatalf("help = %d, stdout %q, stderr %q", exit, stdout, stderr)
	}
	outbox := filepath.Join(t.TempDir(), "outbox")
	phaseDirectory := filepath.Join(outbox, "project", "APG100")
	if err := os.MkdirAll(phaseDirectory, 0o700); err != nil {
		t.Fatal(err)
	}
	lock, err := os.OpenFile(filepath.Join(phaseDirectory, ".response.lock"), os.O_RDWR|os.O_CREATE, 0o600)
	if err != nil {
		t.Fatal(err)
	}
	defer lock.Close()
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	exit, _, stderr = runTestWithInput(t, ctx, strings.NewReader("body"), "--outbox-root", outbox, "--project", "project", "response", "--phase", "APG100")
	if exit != 1 || !strings.Contains(stderr, "interrupted") {
		t.Fatalf("cancelled = %d, stderr %q", exit, stderr)
	}
}

func runTestWithInput(t *testing.T, ctx context.Context, input *strings.Reader, arguments ...string) (int, string, string) {
	t.Helper()
	var stdout, stderr strings.Builder
	exit := RunWithInput(ctx, arguments, input, &stdout, &stderr)
	return exit, stdout.String(), stderr.String()
}
