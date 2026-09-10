package skills

import (
	"bytes"
	"errors"
	"io/fs"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"testing"
	"testing/fstest"
)

func TestEmbeddedCorpusMatchesCanonicalMetadata(t *testing.T) {
	metadata, err := Metadata()
	if err != nil {
		t.Fatal(err)
	}
	expectedCount := HistoricalSkillCount
	if V010RequireAdmittedLeaf {
		expectedCount = V010BrowserRuntimeAdmittedSkillCount
	}
	if len(metadata.Skills) != expectedCount {
		t.Fatalf("corpus skills count = %d, want exactly %d", len(metadata.Skills), expectedCount)
	}
	if len(metadata.Skills) == HistoricalSkillCount {
		if metadata.DescriptionBytes != HistoricalDescriptionBytes || metadata.DescriptionCharacters != HistoricalDescriptionCharacters {
			t.Fatalf("corpus invariants = %#v", metadata)
		}
	} else if len(metadata.Skills) == V010BrowserRuntimeAdmittedSkillCount {
		if metadata.DescriptionBytes > V010BrowserRuntimeAdmissionCeiling || metadata.DescriptionBytes < HistoricalDescriptionBytes {
			t.Fatalf("corpus invariants = %#v", metadata)
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersion, metadata.Skills); err != nil {
		t.Fatalf("discovery policy validation failed: %v", err)
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
	if !sort.StringsAreSorted(ids) || len(uniqueStrings(ids)) != len(metadata.Skills) {
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
	expectedCount := HistoricalSkillCount
	if V010RequireAdmittedLeaf {
		expectedCount = V010BrowserRuntimeAdmittedSkillCount
	}
	if len(paths) != expectedCount {
		t.Fatalf("embedded files = %d, want %d: %v", len(paths), expectedCount, paths)
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

func TestBuildIndexMissingSVGRejection(t *testing.T) {
	baseline := fstest.MapFS{}
	err := fs.WalkDir(Corpus(), ".", func(path string, entry fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if !entry.IsDir() && path != "svg-language-profile/SKILL.md" {
			body, readErr := fs.ReadFile(Corpus(), path)
			if readErr != nil {
				return readErr
			}
			baseline[path] = &fstest.MapFile{Data: body}
		}
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := buildIndexWithRequirement(baseline, true); !errors.Is(err, ErrCorpusMismatch) {
		t.Fatalf("missing SVG accepted: %v", err)
	}
	delete(baseline, "playwright-test-profile/SKILL.md")
	delete(baseline, "web-accessibility-profile/SKILL.md")
	delete(baseline, "vite-build-profile/SKILL.md")
	delete(baseline, "npm-package-manager-profile/SKILL.md")
	delete(baseline, "browser-runtime-profile/SKILL.md")
	if _, err := buildIndexWithRequirement(baseline, false); err != nil {
		t.Fatal(err)
	}
}

func TestBuildIndex45SyntheticFS(t *testing.T) {
	fs45 := fstest.MapFS{}
	err := fs.WalkDir(Corpus(), ".", func(path string, entry fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if !entry.IsDir() {
			body, readErr := fs.ReadFile(Corpus(), path)
			if readErr != nil {
				return readErr
			}
			fs45[path] = &fstest.MapFile{Data: body}
		}
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}


	index, err := buildIndexWithRequirement(fs45, true)
	if err != nil {
		t.Fatalf("buildIndexWithRequirement failed on synthetic 45-skill corpus: %v", err)
	}
	if len(index.skills) != 45 {
		t.Fatalf("skills count = %d, want 45", len(index.skills))
	}
	if index.fingerprint == "" {
		t.Fatalf("fingerprint should not be empty")
	}

	// 44 skills (missing web-accessibility-profile) must fail
	delete(fs45, "web-accessibility-profile/SKILL.md")
	if _, err := buildIndexWithRequirement(fs45, true); !errors.Is(err, ErrCorpusMismatch) {
		t.Fatalf("expected ErrCorpusMismatch on 44 skills, got %v", err)
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
