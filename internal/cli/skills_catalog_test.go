package cli

import (
	"bytes"
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestCatalogCLIBoundary(t *testing.T) {
	var out bytes.Buffer
	if err := runSkillsList([]string{"--all-sources", "--json"}, &out); err != nil {
		t.Fatal(err)
	}
	var catalog map[string]any
	if err := json.Unmarshal(out.Bytes(), &catalog); err != nil {
		t.Fatal(err)
	}
	if catalog["schema_version"] != "apg.skill-catalog/v1" {
		t.Fatal(catalog)
	}
	root := t.TempDir()
	leaf := filepath.Join(root, "skills", "example")
	os.MkdirAll(leaf, 0700)
	os.WriteFile(filepath.Join(leaf, "SKILL.md"), []byte("---\nname: example\ndescription: local\n---\nlocal"), 0600)
	out.Reset()
	if err := runSkillCatalog([]string{"--stdin", "--apgr-home", root}, strings.NewReader(`{"schema_version":"apg.skill-catalog/v1"}`), &out); err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(out.String(), "user:example") {
		t.Fatal("native capture missing")
	}
	out.Reset()
	if err := runSkillCatalog([]string{"--stdin"}, strings.NewReader(`{"schema_version":"apg.skill-catalog/v2"}`), &out); err == nil {
		t.Fatal("version accepted")
	}
}

func TestCatalogAuthorityReaderRejectsSymlinks(t *testing.T) {
	root := t.TempDir()
	target := filepath.Join(t.TempDir(), "authority.md")
	if err := os.WriteFile(target, []byte("authority"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(target, filepath.Join(root, "authority.md")); err != nil {
		t.Fatal(err)
	}
	f := directCatalogFS{FS: os.DirFS(root), root: root}
	if _, err := f.ReadFile("authority.md"); err == nil {
		t.Fatal("authority symlink accepted")
	}
	if err := os.WriteFile(filepath.Join(root, "direct.md"), []byte("authority"), 0600); err != nil {
		t.Fatal(err)
	}
	if data, err := f.ReadFile("direct.md"); err != nil || string(data) != "authority" {
		t.Fatal(string(data), err)
	}
}

func TestVerifyCorpusRejectsLinkedAuthority(t *testing.T) {
	root, err := filepath.Abs(filepath.Join("..", ".."))
	if err != nil {
		t.Fatal(err)
	}
	candidate := t.TempDir()
	if err := os.MkdirAll(filepath.Join(candidate, "src/agentic_praxis_grimoire/resources"), 0700); err != nil {
		t.Fatal(err)
	}
	copyCorpusFixture(t, root, candidate)
	for _, name := range []string{"skills/README.md", "skills/rules.go", "skills/catalog_generated.json", "docs/governance/skill-maturity-ledger.json", "docs/guides/skill-context-bundles.md", "docs/chatgpt-manager-skill-topology.md"} {
		copySkillFile(t, root, candidate, name)
	}
	if exit, _, stderr := runTest(t, context.Background(), "skills", "verify-corpus", "--repository", candidate); exit != 0 {
		t.Fatal(stderr)
	}
	authority := filepath.Join(candidate, "docs/governance/skill-maturity-ledger.json")
	if err := os.Remove(authority); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(filepath.Join(root, "docs/governance/skill-maturity-ledger.json"), authority); err != nil {
		t.Fatal(err)
	}
	if exit, _, _ := runTest(t, context.Background(), "skills", "verify-corpus", "--repository", candidate); exit != 1 {
		t.Fatal("linked authority accepted", exit)
	}
}
