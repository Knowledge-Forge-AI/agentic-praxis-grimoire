package cli

import (
	"context"
	"os"
	"path/filepath"
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
	root, err := filepath.Abs(filepath.Join("..", ".."))
	if err != nil {
		t.Fatal(err)
	}
	candidate := t.TempDir()
	for _, directory := range []string{"skills", filepath.Join("src", "agentic_praxis_grimoire", "resources")} {
		if err := os.MkdirAll(filepath.Join(candidate, directory), 0o700); err != nil {
			t.Fatal(err)
		}
	}
	copyCorpusFixture(t, root, candidate)
	manifest := filepath.Join(candidate, "src", "agentic_praxis_grimoire", "resources", "skill-metadata.json")
	if err := os.WriteFile(manifest, []byte("{}\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	exit, _, _ := runTest(t, context.Background(), "skills", "verify-corpus", "--repository", candidate)
	if exit != 1 {
		t.Fatalf("metadata drift exit = %d", exit)
	}
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
