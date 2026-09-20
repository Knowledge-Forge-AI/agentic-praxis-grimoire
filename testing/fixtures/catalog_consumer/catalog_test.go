package main

import (
	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/skills"
	"strings"
	"testing"
)

// This caller owns its input and consumes real bodies through the public seam.
// It is APGR-local qualification, not JACA adoption or deployment evidence.
func TestQualifiedCatalogConsumer(t *testing.T) {
	input := skills.CatalogInput{SchemaVersion: skills.CatalogSchemaV1}
	for _, source := range []string{"project", "user"} {
		input.Snapshots = append(input.Snapshots, skills.SkillSnapshot{
			QualifiedID: source + ":go-language-profile", Path: "/consumer/" + source + "/SKILL.md",
			Body: []byte("---\nname: go-language-profile\ndescription: consumer rules\n---\n" + source),
		})
	}
	c, err := skills.BuildCatalog(input)
	if err != nil {
		t.Fatal(err)
	}
	matches := 0
	for _, d := range c.Skills {
		if d.ID == "go-language-profile" {
			matches++
		}
	}
	if matches != 3 {
		t.Fatal("lost source identity")
	}
	if _, err := skills.ResolveCatalog(input, "go-language-profile", skills.ConsumerGo); err == nil {
		t.Fatal("silent shadow")
	}
	input.Overrides = []skills.CatalogOverride{{Requested: "apgr:go-language-profile", Selected: "project:go-language-profile", ConfigPath: "/consumer/.apgr/config.toml", ConfigSHA256: strings.Repeat("a", 64)}}
	result, err := skills.ResolveCatalog(input, "apgr:go-language-profile", skills.ConsumerGo)
	if err != nil || result.RequestedIdentity != "apgr:go-language-profile" || result.SelectedIdentity != "project:go-language-profile" || result.SourceSHA256 == "" || !strings.HasSuffix(string(result.Snapshot.Body), "project") {
		t.Fatal(result, err)
	}
}
