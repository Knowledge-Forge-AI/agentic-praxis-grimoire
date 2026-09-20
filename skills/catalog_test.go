package skills

import (
	"bytes"
	"encoding/json"
	"io/fs"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
	"testing/fstest"
)

func catalogLeaf(id, extra, text string) SkillSnapshot {
	_, name, _ := qualifiedParts(id)
	return SkillSnapshot{QualifiedID: id, Path: "/fixture/" + name + "/SKILL.md", Body: []byte("---\nname: " + name + "\ndescription: café\n" + extra + "---\n" + text), Support: map[string][]byte{}}
}
func catalogInput(leaves ...SkillSnapshot) CatalogInput {
	return CatalogInput{SchemaVersion: CatalogSchemaV1, Snapshots: leaves}
}
func override() CatalogOverride {
	return CatalogOverride{"apgr:go-language-profile", "project:go-language-profile", "/project/.apgr/config.toml", strings.Repeat("a", 64)}
}

func TestCatalogQualifiedSelection(t *testing.T) {
	project := catalogLeaf("project:go-language-profile", "maturity: stable\n", "project")
	user := catalogLeaf("user:go-language-profile", "", "user")
	input := catalogInput(project, user)
	c, err := BuildCatalog(input)
	if err != nil {
		t.Fatal(err)
	}
	found := 0
	for _, d := range c.Skills {
		if d.ID == "go-language-profile" {
			found++
			if d.QualifiedID == project.QualifiedID && (d.Maturity != "unqualified" || d.SourceDeclaredMaturity != "stable") {
				t.Fatal(d)
			}
		}
	}
	if found != 3 {
		t.Fatal(found)
	}
	if _, err := ResolveCatalog(input, "go-language-profile", ConsumerGo); err == nil {
		t.Fatal("silent shadowing")
	}
	selected, err := ResolveCatalog(input, "apgr:go-language-profile", ConsumerGo)
	if err != nil || selected.SelectedIdentity != "apgr:go-language-profile" {
		t.Fatal(selected, err)
	}
	input.Overrides = []CatalogOverride{override()}
	selected, err = ResolveCatalog(input, "apgr:go-language-profile", ConsumerGo)
	if err != nil || selected.SelectedIdentity != project.QualifiedID || !bytes.Equal(selected.Snapshot.Body, project.Body) {
		t.Fatal(selected, err)
	}
	c, err = BuildCatalog(input)
	if err != nil || len(c.Overrides) != 1 {
		t.Fatal(c, err)
	}
	selected.Snapshot.Body[0] = 'x'
	c.Skills[0].ConsumerLimitations[0] = "changed"
	fresh, err := ResolveCatalog(input, "apgr:go-language-profile", ConsumerGo)
	if err != nil || fresh.Snapshot.Body[0] != '-' {
		t.Fatal("shared state")
	}
}

func TestCatalogInvalidOverrides(t *testing.T) {
	for _, modify := range []func(*CatalogOverride){func(o *CatalogOverride) { o.Selected = o.Requested }, func(o *CatalogOverride) { o.Selected = "user:go-language-profile" }, func(o *CatalogOverride) { o.Requested = "project:go-language-profile" }, func(o *CatalogOverride) { o.ConfigSHA256 = "invalid" }, func(o *CatalogOverride) { o.Requested = "apgr:missing" }} {
		o := override()
		modify(&o)
		input := catalogInput()
		input.Overrides = []CatalogOverride{o}
		if _, err := BuildCatalog(input); err == nil {
			t.Fatal(o)
		}
	}
	input := catalogInput()
	input.Overrides = []CatalogOverride{override()}
	c, err := BuildCatalog(input)
	if err != nil || len(c.Diagnostics) == 0 {
		t.Fatal("missing replacement must be diagnosed", err)
	}
	if _, err = ResolveCatalog(input, override().Requested, ConsumerGo); err == nil {
		t.Fatal("missing target fallback")
	}
	input.Overrides = append(input.Overrides, override())
	if _, err := BuildCatalog(input); err == nil {
		t.Fatal("duplicate mapping")
	}
}

func TestCatalogExactCostsIdentityAndIsolation(t *testing.T) {
	leaf := catalogLeaf("project:sample", "support: [\"note.txt\"]\n", "## Do not use\nNo.\n## Project-owned parameters\nKnobs.\n")
	leaf.Support["note.txt"] = []byte("é")
	d, err := descriptor(leaf)
	if err != nil {
		t.Fatal(err)
	}
	if d.DescriptionBytes != 5 || d.DescriptionCharacters != 4 || d.BodyBytes != int64(len(leaf.Body)) || d.BodySHA256 != sha256Hex(leaf.Body) || d.Tokens != nil || d.DoNotUse != "No." || d.ProjectOwnedParameters != "Knobs." || d.SupportFiles[0].Bytes != 2 {
		t.Fatal(d)
	}
	a, _ := BuildCatalog(catalogInput(leaf))
	leaf.Path = "/relocated/sample/SKILL.md"
	b, _ := BuildCatalog(catalogInput(leaf))
	if a.Fingerprint != b.Fingerprint || reflect.DeepEqual(a.Provenance, b.Provenance) {
		t.Fatal("path/content identity conflated")
	}
	leaf.Body = append(leaf.Body, '!')
	c, _ := BuildCatalog(catalogInput(leaf))
	if a.Fingerprint == c.Fingerprint {
		t.Fatal("stale content identity")
	}
}

func TestCatalogMalformedAndDuplicate(t *testing.T) {
	for _, body := range [][]byte{[]byte("bad"), {0xff}, []byte(strings.Repeat("x", MaxCatalogFileBytes+1)), []byte("---\nname: x\nname: x\ndescription: x\n---\n"), []byte("---\nname: x\ndescription: x\nrequires: [\"project:x\",\"project:x\"]\n---\n")} {
		input := catalogInput(SkillSnapshot{QualifiedID: "project:x", Body: body})
		c, err := BuildCatalog(input)
		if err != nil || len(c.Diagnostics) != 1 {
			t.Fatal(err, c.Diagnostics)
		}
		if _, err = ResolveCatalog(input, "project:x", ConsumerGo); err == nil {
			t.Fatal("malformed selection accepted")
		}
	}
	leaf := catalogLeaf("project:x", "", "x")
	if _, err := BuildCatalog(catalogInput(leaf, leaf)); err == nil {
		t.Fatal("duplicate source IDs accepted")
	}
	leaf.QualifiedID = "apgr:x"
	if _, err := BuildCatalog(catalogInput(leaf)); err == nil {
		t.Fatal("external canonical injection")
	}
}

func TestCatalogDependenciesAreExplicit(t *testing.T) {
	before := CompositionRules()
	c, err := BuildCatalog(catalogInput())
	if err != nil {
		t.Fatal(err)
	}
	for _, d := range c.Skills {
		if len(d.RequiredDependencies) != 0 {
			t.Fatal("invented dependency")
		}
	}
	for _, input := range []CatalogInput{
		catalogInput(catalogLeaf("project:a", "requires: [\"project:b\"]\n", "a")),
		catalogInput(catalogLeaf("project:a", "requires: [\"project:b\"]\n", "a"), catalogLeaf("project:b", "requires: [\"project:a\"]\n", "b")),
	} {
		if _, err := ResolveCatalog(input, "project:a", ConsumerGo); err == nil {
			t.Fatal("invalid DAG accepted")
		}
	}
	input := catalogInput(catalogLeaf("project:a", "requires: [\"project:b\"]\n", "a"), catalogLeaf("project:b", "", "b"))
	if _, err := ResolveCatalog(input, "project:a", ConsumerGo); err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(before, CompositionRules()) {
		t.Fatal("changed informational rules")
	}
}

func TestCatalogManagerConsumerRestriction(t *testing.T) {
	input := catalogInput(catalogLeaf("project:manager", "", "local"))
	o := override()
	o.Requested = "apgr:chatgpt-manager-workflow"
	o.Selected = "project:manager"
	input.Overrides = []CatalogOverride{o}
	if _, err := ResolveCatalog(input, o.Requested, ConsumerGo); err == nil {
		t.Fatal("consumer restriction bypass")
	}
	if _, err := ResolveCatalog(input, o.Requested, ConsumerChatGPT); err != nil {
		t.Fatal(err)
	}
}

func TestCatalogCaptureBoundaries(t *testing.T) {
	root := t.TempDir()
	input, err := CaptureCatalogSource("project", root)
	if err != nil || input.Sources[0].Status != "absent" {
		t.Fatal(input, err)
	}
	entries, _ := os.ReadDir(root)
	if len(entries) != 0 {
		t.Fatal("listing writes")
	}
	path := filepath.Join(root, ".apgr", "skills", "sample")
	if err := os.MkdirAll(path, 0700); err != nil {
		t.Fatal(err)
	}
	leaf := catalogLeaf("project:sample", "", "é")
	if err := os.WriteFile(filepath.Join(path, "SKILL.md"), leaf.Body, 0600); err != nil {
		t.Fatal(err)
	}
	linked := filepath.Join(t.TempDir(), "root")
	if err := os.Symlink(root, linked); err != nil {
		t.Fatal(err)
	}
	input, err = CaptureCatalogSource("project", linked)
	if err != nil || len(input.Snapshots) != 1 || input.Sources[0].SelectedRoot == input.Sources[0].ResolvedRoot {
		t.Fatal(input, err)
	}
	outside := t.TempDir()
	os.WriteFile(filepath.Join(outside, "SKILL.md"), leaf.Body, 0600)
	os.Symlink(outside, filepath.Join(root, ".apgr", "skills", "escape"))
	os.Symlink("loop", filepath.Join(root, ".apgr", "skills", "loop"))
	input, err = CaptureCatalogSource("project", root)
	if err != nil || len(input.Snapshots) != 1 || len(input.Diagnostics) != 2 {
		t.Fatal(input, err)
	}
	os.Remove(filepath.Join(path, "SKILL.md"))
	os.Symlink(filepath.Join(outside, "SKILL.md"), filepath.Join(path, "SKILL.md"))
	input, err = CaptureCatalogSource("project", root)
	if err != nil || len(input.Snapshots) != 0 {
		t.Fatal("leaf symlink escaped", err)
	}
}

func TestCatalogGenerationDrift(t *testing.T) {
	root := os.DirFS("..")
	if err := VerifyCatalogGeneration(root); err != nil {
		t.Fatal(err)
	}
	var generated catalogGeneration
	if err := json.Unmarshal(generatedCatalog, &generated); err != nil {
		t.Fatal(err)
	}
	for _, authority := range generated.Authorities {
		overlay := fstest.MapFS{}
		data, err := os.ReadFile(filepath.Join("..", authority.Path))
		if err != nil {
			t.Fatal(err)
		}
		overlay[authority.Path] = &fstest.MapFile{Data: append(data, ' ')}
		if err := VerifyCatalogGeneration(catalogOverlay{overlay, root}); err == nil {
			t.Fatal("authority drift accepted", authority.Path)
		}
	}
}

type catalogOverlay struct {
	overlay fstest.MapFS
	base    fs.FS
}

func (f catalogOverlay) Open(name string) (fs.File, error) {
	if _, ok := f.overlay[name]; ok {
		return f.overlay.Open(name)
	}
	return f.base.Open(name)
}

func TestCatalogSupportAndProjectionIsolation(t *testing.T) {
	root := t.TempDir()
	leafPath := filepath.Join(root, ".apgr/skills/x")
	os.MkdirAll(leafPath, 0700)
	body := catalogLeaf("project:x", "support: [\"script.sh\"]\n", "x")
	os.WriteFile(filepath.Join(leafPath, "SKILL.md"), body.Body, 0600)
	os.WriteFile(filepath.Join(leafPath, "script.sh"), []byte("#!/bin/sh\nexit 99\n"), 0700)
	os.MkdirAll(filepath.Join(root, ".agents/skills/projected"), 0700)
	os.WriteFile(filepath.Join(root, ".agents/skills/projected/SKILL.md"), body.Body, 0600)
	c, err := CaptureCatalogSource("project", root)
	if err != nil || len(c.Snapshots) != 1 || len(c.Snapshots[0].Support) != 1 {
		t.Fatal(c, err)
	}
	catalog, err := BuildCatalog(c)
	if err != nil {
		t.Fatal(err)
	}
	for _, d := range catalog.Skills {
		if d.QualifiedID == "project:x" && !d.SupportFiles[0].Captured {
			t.Fatal("support snapshot missing")
		}
	}
	os.Remove(filepath.Join(leafPath, "script.sh"))
	outside := filepath.Join(t.TempDir(), "outside")
	os.WriteFile(outside, []byte("outside"), 0600)
	os.Symlink(outside, filepath.Join(leafPath, "script.sh"))
	c, err = CaptureCatalogSource("project", root)
	if err != nil || len(c.Snapshots) != 0 || len(c.Diagnostics) != 1 {
		t.Fatal("support symlink accepted", c, err)
	}
}

func TestCatalogDecodeClosedBoundary(t *testing.T) {
	for _, data := range []string{`{"schema_version":"apg.skill-catalog/v1","extra":1}`, `{"schema_version":"apg.skill-catalog/v1","schema_version":"apg.skill-catalog/v1"}`, `{"schema_version":"v2"}`, `{"schema_version":"apg.skill-catalog/v1","snapshots":[{"qualified_id":"project:x","qualified_id":"project:y"}]}`} {
		if _, err := DecodeCatalogInput([]byte(data)); err == nil {
			t.Fatal("malformed JSON accepted", data)
		}
	}
}
