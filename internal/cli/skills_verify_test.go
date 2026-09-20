package cli

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestSkillsVerifyCorpusMatchesCheckout(t *testing.T) {
	root, err := filepath.Abs(filepath.Join("..", ".."))
	if err != nil {
		t.Fatal(err)
	}
	exit, stdout, stderr := runTest(t, context.Background(), "skills", "verify-corpus", "--repository", root)
	if exit != 0 || stdout != "" || stderr != "" {
		t.Fatalf("verify corpus = %d %q %q", exit, stdout, stderr)
	}
}

func TestSkillsVerifyCorpusRejectsMetadataDrift(t *testing.T) {
	candidate := newDirectCorpusFixture(t)
	if exit, _, stderr := runTest(t, context.Background(), "skills", "verify-corpus", "--repository", candidate); exit != 0 {
		t.Fatal("valid fixture rejected", stderr)
	}
	manifest := filepath.Join(candidate, "src", "agentic_praxis_grimoire", "resources", "skill-metadata.json")
	if err := os.WriteFile(manifest, []byte("{}\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	exit, _, stderr := runTest(t, context.Background(), "skills", "verify-corpus", "--repository", candidate)
	if exit != 1 || !strings.Contains(stderr, "checkout skill metadata disagrees") {
		t.Fatalf("metadata drift = %d %q", exit, stderr)
	}
}

func TestSkillsVerifyCorpusRejectsLinkedRoots(t *testing.T) {
	candidate := newDirectCorpusFixture(t)
	if exit, _, stderr := runTest(t, context.Background(), "skills", "verify-corpus", "--repository", candidate); exit != 0 {
		t.Fatal("canonical fixture rejected", stderr)
	}
	parent, err := filepath.EvalSymlinks(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	linkedRoot := filepath.Join(parent, "linked-root")
	if err := os.Symlink(candidate, linkedRoot); err != nil {
		t.Fatal(err)
	}
	linkedParent := filepath.Join(parent, "linked-parent")
	if err := os.Symlink(filepath.Dir(candidate), linkedParent); err != nil {
		t.Fatal(err)
	}
	for name, repository := range map[string]string{
		"root":     linkedRoot,
		"ancestor": filepath.Join(linkedParent, filepath.Base(candidate)),
	} {
		t.Run(name, func(t *testing.T) {
			exit, _, stderr := runTest(t, context.Background(), "skills", "verify-corpus", "--repository", repository)
			if exit != 1 || !strings.Contains(stderr, "skill repository root is unsafe") {
				t.Fatalf("linked %s = %d %q", name, exit, stderr)
			}
		})
	}
}

func newDirectCorpusFixture(t *testing.T) string {
	t.Helper()
	root, err := filepath.Abs(filepath.Join("..", ".."))
	if err != nil {
		t.Fatal(err)
	}
	// Only the generated fixture is canonicalized. The verifier must continue
	// rejecting linked repository authority, including linked ancestors.
	candidate, err := filepath.EvalSymlinks(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(candidate, "src/agentic_praxis_grimoire/resources"), 0o700); err != nil {
		t.Fatal(err)
	}
	copyCorpusFixture(t, root, candidate)
	for _, name := range []string{"skills/README.md", "skills/rules.go", "skills/catalog_generated.json", "docs/governance/skill-maturity-ledger.json", "docs/guides/skill-context-bundles.md", "docs/chatgpt-manager-skill-topology.md"} {
		copySkillFile(t, root, candidate, name)
	}
	return candidate
}

func copyCorpusFixture(t *testing.T, source, destination string) {
	t.Helper()
	paths := []string{filepath.Join("src", "agentic_praxis_grimoire", "resources", "skill-metadata.json")}
	metadata, err := os.ReadFile(filepath.Join(source, paths[0]))
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(destination, paths[0]), metadata, 0o600); err != nil {
		t.Fatal(err)
	}
	entries, err := os.ReadDir(filepath.Join(source, "skills"))
	if err != nil {
		t.Fatal(err)
	}
	for _, entry := range entries {
		if !entry.IsDir() || entry.Name() == "chatgpt" {
			continue
		}
		copySkillFile(t, source, destination, filepath.Join("skills", entry.Name(), "SKILL.md"))
	}
	nested, err := os.ReadDir(filepath.Join(source, "skills", "chatgpt"))
	if err != nil {
		t.Fatal(err)
	}
	for _, entry := range nested {
		if entry.IsDir() {
			copySkillFile(t, source, destination, filepath.Join("skills", "chatgpt", entry.Name(), "SKILL.md"))
		}
	}
}

func copySkillFile(t *testing.T, source, destination, relative string) {
	t.Helper()
	body, err := os.ReadFile(filepath.Join(source, relative))
	if err != nil {
		t.Fatal(err)
	}
	target := filepath.Join(destination, relative)
	if err := os.MkdirAll(filepath.Dir(target), 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(target, body, 0o600); err != nil {
		t.Fatal(err)
	}
}
