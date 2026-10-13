package skills

import (
	"bytes"
	"encoding/json"
	"strings"
	"testing"
)

func ownershipInput() CatalogInput {
	leaf := func(id string) SkillSnapshot {
		_, name, _ := qualifiedParts(id)
		return SkillSnapshot{QualifiedID: id, Path: "/selected/" + name + "/SKILL.md",
			Body:    []byte("---\nname: " + name + "\ndescription: ownership fixture\nsupport: [\"note.txt\"]\n---\nGuidance.\n"),
			Support: map[string][]byte{"note.txt": []byte("support")}}
	}
	return CatalogInput{SchemaVersion: CatalogSchemaV1,
		Snapshots: []SkillSnapshot{leaf("project:python-language-profile"), leaf("project:go-language-profile")},
		Overrides: []CatalogOverride{
			{"apgr:python-language-profile", "project:python-language-profile", "/selected/.apgr/config.toml", strings.Repeat("a", 64)},
			{"apgr:go-language-profile", "project:go-language-profile", "/selected/.apgr/config.toml", strings.Repeat("a", 64)},
		},
		Diagnostics: []CatalogDiagnostic{{Identity: "z", Message: "last"}, {Identity: "a", Message: "first"}},
		Sources:     []CatalogSourceStatus{{Source: "user", Status: "absent"}, {Source: "project", Status: "captured"}},
	}
}

func ownershipJSON(t *testing.T, value any) []byte {
	t.Helper()
	data, err := json.Marshal(value)
	if err != nil {
		t.Fatal(err)
	}
	return data
}

func TestCatalogBuildDoesNotMutateInputCollections(t *testing.T) {
	input := ownershipInput()
	before := ownershipJSON(t, input)
	if _, err := BuildCatalog(input); err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(before, ownershipJSON(t, input)) {
		t.Fatal("BuildCatalog mutated caller-owned input")
	}
}

func TestCatalogReturnedSnapshotDoesNotAliasInput(t *testing.T) {
	input := ownershipInput()
	before := ownershipJSON(t, input)
	selected, err := ResolveCatalog(input, "project:go-language-profile", ConsumerGo)
	if err != nil {
		t.Fatal(err)
	}
	selected.Snapshot.Body[0] = '!'
	selected.Snapshot.Support["note.txt"][0] = '!'
	delete(selected.Snapshot.Support, "note.txt")
	if !bytes.Equal(before, ownershipJSON(t, input)) {
		t.Fatal("returned snapshot aliases caller-owned input")
	}
}

func TestCatalogReturnedRelationsDoNotAliasInput(t *testing.T) {
	input := ownershipInput()
	before := ownershipJSON(t, input)
	catalog, err := BuildCatalog(input)
	if err != nil {
		t.Fatal(err)
	}
	catalog.Overrides[0].Selected = "project:changed"
	catalog.Diagnostics[0].Message = "changed"
	catalog.Sources[0].Status = "changed"
	if !bytes.Equal(before, ownershipJSON(t, input)) {
		t.Fatal("returned relations alias caller-owned input")
	}
}

func TestCatalogInputMutationDoesNotChangeExistingResult(t *testing.T) {
	input := ownershipInput()
	catalog, err := BuildCatalog(input)
	if err != nil {
		t.Fatal(err)
	}
	before := ownershipJSON(t, catalog)
	input.Snapshots[0].Body[0] = '!'
	input.Snapshots[0].Support["note.txt"][0] = '!'
	input.Snapshots[0].Support["new.txt"] = []byte("new")
	input.Overrides[0].Selected = "project:changed"
	input.Diagnostics[0].Message = "changed"
	input.Sources[0].Status = "changed"
	if !bytes.Equal(before, ownershipJSON(t, catalog)) {
		t.Fatal("caller mutation changed a returned catalog")
	}
}
