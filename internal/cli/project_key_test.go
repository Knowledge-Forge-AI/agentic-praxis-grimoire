package cli

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/report"
)

func TestDotPrefixedRepositoryUsesExistingCollectorProjectKey(t *testing.T) {
	repository, commit := repositoryTest(t)
	dotted := filepath.Join(filepath.Dir(repository), "..repository")
	if err := os.Rename(repository, dotted); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dotted, "tracked.txt"), []byte("changed\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	outbox := filepath.Join(t.TempDir(), "outbox")
	base := []string{"--repository", dotted, "--outbox-root", outbox, "--project", "repository"}
	for _, test := range []struct {
		phase, kind string
		args        []string
	}{
		{"KEY-SHOW", "git.show", []string{"report", "show", "KEY-SHOW", commit, "status.md", "custom-outcome", "gate"}},
		{"KEY-DIFF", "git.diff", []string{"report", "diff", "KEY-DIFF", "custom-outcome", "gate"}},
	} {
		t.Run(test.phase, func(t *testing.T) {
			exit, _, stderr := runTest(t, context.Background(), append(append([]string{}, base...), test.args...)...)
			if exit != 0 || stderr != "" {
				t.Fatalf("write = %d %s", exit, stderr)
			}
			content, err := os.ReadFile(filepath.Join(outbox, "repository", test.phase, test.phase+"."+test.kind+".report.txt"))
			if err != nil {
				t.Fatal(err)
			}
			records, err := report.ParseRecords(content)
			if err != nil || len(records) != 1 {
				t.Fatalf("records = %d, %v", len(records), err)
			}
		})
	}
	for _, explicit := range []bool{false, true} {
		args := append([]string{}, base[:4]...)
		if explicit {
			args = append(args, "--project", "repository")
		}
		args = append(args, "response", "--phase", "KEY-RESPONSE")
		exit, path, stderr := runTestWithInput(t, context.Background(), strings.NewReader("exact body"), args...)
		if exit != 0 || stderr != "" {
			t.Fatalf("response = %d %s", exit, stderr)
		}
		content, err := os.ReadFile(strings.TrimSpace(path))
		if err != nil || string(content) != "exact body" {
			t.Fatalf("body = %q, %v", content, err)
		}
	}
}

func TestRepositoryProjectMappingRefusesAliasesAndUnsafeKeys(t *testing.T) {
	for _, name := range []string{".example", "example", "...", "._bad", ".bad name"} {
		t.Run(name, func(t *testing.T) {
			root := filepath.Join(t.TempDir(), name)
			outbox := filepath.Join(t.TempDir(), "outbox")
			for _, action := range [][]string{{"report", "diff", "KEY-REFUSE", "result", "gate"}, {"response", "--phase", "KEY-REFUSE"}} {
				args := []string{"--repository", root, "--outbox-root", outbox, "--project", "unrelated"}
				exit, _, _ := runTestWithInput(t, context.Background(), strings.NewReader("body"), append(args, action...)...)
				if exit != 2 {
					t.Fatalf("alias exit = %d", exit)
				}
			}
			if _, err := os.Stat(outbox); !os.IsNotExist(err) {
				t.Fatalf("refusal created outbox: %v", err)
			}
		})
	}
}

func TestNormalizedUnsafeRepositoryProjectIsStillRefused(t *testing.T) {
	for _, name := range []string{"...", "._bad", ".bad name"} {
		root := filepath.Join(t.TempDir(), name)
		outbox := filepath.Join(t.TempDir(), "outbox")
		key := strings.TrimLeft(name, ".")
		configuration := config{repository: root, outbox: outbox, project: key}
		if err := validateExplicit(configuration, true); err == nil {
			t.Fatalf("unsafe key %q accepted", key)
		}
		exit, _, _ := runTestWithInput(t, context.Background(), strings.NewReader("body"), "--repository", root, "--outbox-root", outbox, "response", "--phase", "KEY-UNSAFE")
		if exit != 2 {
			t.Fatalf("unsafe response key %q exit = %d", key, exit)
		}
		if _, err := os.Stat(outbox); !os.IsNotExist(err) {
			t.Fatalf("unsafe key created outbox: %v", err)
		}
	}
}
