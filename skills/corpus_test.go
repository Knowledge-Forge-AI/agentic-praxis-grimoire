package skills

import (
	"bytes"
	"io/fs"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"testing"
)

func TestEmbeddedCorpusMatchesCanonicalMetadata(t *testing.T) {
	metadata, err := Metadata()
	if err != nil {
		t.Fatal(err)
	}
	if len(metadata.Skills) != 39 || metadata.DescriptionBytes != 9504 || metadata.DescriptionCharacters != 9492 {
		t.Fatalf("corpus invariants = %#v", metadata)
	}
	want, err := os.ReadFile(filepath.Join("..", "src", "agentic_praxis_grimoire", "resources", "skill-metadata.json"))
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(metadata.ManifestJSON, want) {
		limit := len(want)
		if len(metadata.ManifestJSON) < limit {
			limit = len(metadata.ManifestJSON)
		}
		position := 0
		for position < limit && metadata.ManifestJSON[position] == want[position] {
			position++
		}
		t.Fatalf("reconstructed metadata differs at byte %d (length %d, want %d)", position, len(metadata.ManifestJSON), len(want))
	}
	if metadata.Fingerprint != sha256Hex(want) {
		t.Fatalf("fingerprint = %q", metadata.Fingerprint)
	}

	paths := make([]string, 0, len(metadata.Skills))
	ids := make([]string, 0, len(metadata.Skills))
	for _, skill := range metadata.Skills {
		paths = append(paths, skill.CanonicalPath)
		ids = append(ids, skill.ID)
		body, readErr := fs.ReadFile(Corpus(), skill.CanonicalPath)
		if readErr != nil || !bytes.Equal(body, skillBody(t, skill.ID)) {
			t.Fatalf("embedded body %s: err=%v", skill.ID, readErr)
		}
	}
	if !sort.StringsAreSorted(ids) || len(uniqueStrings(ids)) != 39 {
		t.Fatalf("IDs are unsorted or duplicated: %v", ids)
	}
	wantNested := []string{
		"chatgpt/chatgpt-manager-workflow/SKILL.md",
		"chatgpt/composing-approved-roadmap-assignments/SKILL.md",
	}
	for _, path := range wantNested {
		if !contains(paths, path) {
			t.Fatalf("missing nested ChatGPT path %q", path)
		}
	}
}

func TestCorpusWalkContainsOnlySkillLeaves(t *testing.T) {
	var paths []string
	err := fs.WalkDir(Corpus(), ".", func(path string, entry fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if !entry.IsDir() {
			paths = append(paths, path)
		}
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(paths) != 39 {
		t.Fatalf("embedded files = %d: %v", len(paths), paths)
	}
	for _, path := range paths {
		if filepath.Base(path) != "SKILL.md" {
			t.Fatalf("unexpected embedded resource %q", path)
		}
	}
	if !reflect.DeepEqual(paths, sortedCopy(paths)) {
		t.Fatalf("walk order is not deterministic: %v", paths)
	}
}

func skillBody(t *testing.T, id string) []byte {
	t.Helper()
	metadata, err := Metadata()
	if err != nil {
		t.Fatal(err)
	}
	for _, skill := range metadata.Skills {
		if skill.ID == id {
			body, readErr := fs.ReadFile(Corpus(), skill.CanonicalPath)
			if readErr != nil {
				t.Fatal(readErr)
			}
			return body
		}
	}
	t.Fatalf("unknown test skill %q", id)
	return nil
}

func uniqueStrings(values []string) []string {
	seen := map[string]bool{}
	result := make([]string, 0, len(values))
	for _, value := range values {
		if !seen[value] {
			seen[value] = true
			result = append(result, value)
		}
	}
	return result
}

func contains(values []string, value string) bool {
	for _, candidate := range values {
		if candidate == value {
			return true
		}
	}
	return false
}

func sortedCopy(values []string) []string {
	result := append([]string(nil), values...)
	sort.Strings(result)
	return result
}
