package gitexec

import (
	"bytes"
	"context"
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"testing"
	"time"
)

func buildHelper(t *testing.T) string {
	t.Helper()
	directory := t.TempDir()
	source := `package main

import (
	"fmt"
	"os"
	"strings"
	"time"
)

func main() {
	if os.Getenv("APG_GITEXEC_HELPER_MODE") == "sleep" {
		time.Sleep(30 * time.Second)
		return
	}
	fmt.Printf("ARGS=%s\n", strings.Join(os.Args[1:], "\x00"))
	for _, name := range []string{"LC_ALL", "LANG", "GIT_PAGER", "PAGER", "GIT_OPTIONAL_LOCKS", "APG_TEST_INHERITED", "APG_TEST_OVERRIDE"} {
		fmt.Printf("%s=%s\n", name, os.Getenv(name))
	}
}
`
	if err := os.WriteFile(filepath.Join(directory, "main.go"), []byte(source), 0o600); err != nil {
		t.Fatal(err)
	}
	binary := filepath.Join(directory, "git-helper")
	command := exec.Command("go", "build", "-o", binary, filepath.Join(directory, "main.go"))
	if output, err := command.CombinedOutput(); err != nil {
		t.Fatalf("helper build failed: %v\n%s", err, output)
	}
	return binary
}

func TestRunnerUsesExactArgvAndDeterministicInheritedEnvironment(t *testing.T) {
	helper := buildHelper(t)
	t.Setenv("APG_TEST_INHERITED", "inherited")
	runner := New("/exact repository root", helper)
	result, err := runner.Run(context.Background(), []string{"status", "$(touch should-not-exist)"}, map[string]string{"APG_TEST_OVERRIDE": "override"}, nil)
	if err != nil {
		t.Fatal(err)
	}
	wantLines := [][]byte{
		[]byte("ARGS=-C\x00/exact repository root\x00--no-pager\x00status\x00$(touch should-not-exist)\n"),
		[]byte("LC_ALL=C\n"), []byte("LANG=C\n"), []byte("GIT_PAGER=cat\n"), []byte("PAGER=cat\n"),
		[]byte("GIT_OPTIONAL_LOCKS=0\n"), []byte("APG_TEST_INHERITED=inherited\n"), []byte("APG_TEST_OVERRIDE=override\n"),
	}
	for _, line := range wantLines {
		if !bytes.Contains(result.Stdout, line) {
			t.Fatalf("missing helper observation %q", line)
		}
	}
}

func TestRunnerCancelsActiveChildPromptly(t *testing.T) {
	helper := buildHelper(t)
	runner := New("/repository", helper)
	ctx, cancel := context.WithTimeout(context.Background(), 50*time.Millisecond)
	defer cancel()
	started := time.Now()
	_, err := runner.Run(ctx, nil, map[string]string{"APG_GITEXEC_HELPER_MODE": "sleep"}, nil)
	if !errors.Is(err, context.DeadlineExceeded) {
		t.Fatalf("cancellation error = %v", err)
	}
	if elapsed := time.Since(started); elapsed > 2*time.Second {
		t.Fatalf("active child cancellation took %s", elapsed)
	}
}
