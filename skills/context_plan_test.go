package skills

import (
	"encoding/json"
	"strings"
	"testing"
)

func contextFixture() ContextPlanRequest {
	return ContextPlanRequest{SchemaVersion: ContextPlanSchemaV1, RunID: "run", BindingID: "binding", AttemptID: "attempt-1", Roles: []string{"work", "review"}, Consumer: ConsumerGo, RequestedMode: "adaptive", Catalog: CatalogInput{SchemaVersion: CatalogSchemaV1}, Mandatory: []ContextComponent{{ID: "task", Text: "immutable é\n"}}, Qualification: ContextQualification{true, true, "instrumented fixture only"}}
}
func TestContextPlanFactsDeterminismOwnership(t *testing.T) {
	r := contextFixture()
	r.Facts = []ContextFact{{"language", "go"}, {"test_framework", "go-native"}, {"language", "unknown"}}
	p, err := PlanContext(r)
	if err != nil {
		t.Fatal(err)
	}
	if p.EffectiveMode != "adaptive" || len(p.SelectedSnapshots) != 2 || len(p.UnknownFacts) != 1 {
		t.Fatalf("unexpected selection: %v %v", p.Reasons, p.SelectedSnapshots)
	}
	if strings.Contains(p.Payload, "pytest-test-profile") {
		t.Fatal("nontrigger selected")
	}
	r.Facts[0], r.Facts[1] = r.Facts[1], r.Facts[0]
	r.Roles[0], r.Roles[1] = r.Roles[1], r.Roles[0]
	again, err := PlanContext(r)
	if err != nil {
		t.Fatal(err)
	}
	a, _ := json.Marshal(p)
	b, _ := json.Marshal(again)
	if string(a) != string(b) {
		t.Fatal("order changes plan")
	}
	p.SelectedSnapshots[0].Body[0] = 'X'
	p.Roles[0] = "changed"
	p.Catalog.Skills[0].ConsumerLimitations = append(p.Catalog.Skills[0].ConsumerLimitations, "x")
	fresh, _ := PlanContext(r)
	b, _ = json.Marshal(fresh)
	if string(a) != string(b) {
		t.Fatal("returned values alias inputs/cache")
	}
	r.RunID = "other"
	r.BindingID = "other-binding"
	r.AttemptID = "attempt-2"
	other, _ := PlanContext(r)
	if fresh.ContentIdentity != other.ContentIdentity || other.AttemptID == fresh.AttemptID {
		t.Fatal("execution identity mixed with content")
	}
}
func TestContextPlanExactBudgets(t *testing.T) {
	r := contextFixture()
	r.Requests = []ContextSkillRequest{{"apgr:go-language-profile", true}}
	p, err := PlanContext(r)
	if err != nil {
		t.Fatal(err)
	}
	bytes, chars := p.PayloadCost.Bytes, p.PayloadCost.Characters
	r.Budget = ContextBudget{&bytes, &chars}
	exact, _ := PlanContext(r)
	if !exact.RequiredSatisfied || exact.EffectiveMode != "adaptive" {
		t.Fatal("exact budget rejected")
	}
	bytes--
	off, _ := PlanContext(r)
	if off.RequiredSatisfied || off.EffectiveMode != "static" {
		t.Fatal("off-by-one accepted")
	}
	bytes++
	chars--
	off, _ = PlanContext(r)
	if off.RequiredSatisfied {
		t.Fatal("character off-by-one accepted")
	}
	zero := int64(0)
	r.Budget = ContextBudget{&zero, nil}
	over, _ := PlanContext(r)
	if over.Payload != r.Mandatory[0].Text || over.BudgetPassed || over.EffectiveMode != "static" {
		t.Fatal("mandatory truncated or overflow hidden")
	}
	negative := int64(-1)
	r.Budget.MaxInitialContextBytes = &negative
	if _, err := PlanContext(r); err == nil {
		t.Fatal("negative accepted")
	}
}
func localContextSkill(id, requires string) SkillSnapshot {
	body := "---\nname: " + id + "\ndescription: synthetic fixture\n"
	if requires != "" {
		body += "requires: " + requires + "\n"
	}
	body += "---\nfixture é\n"
	return SkillSnapshot{QualifiedID: "project:" + id, Path: "/relocated/" + id, Body: []byte(body)}
}
func TestContextPlanClosureOverridesAndRelocation(t *testing.T) {
	r := contextFixture()
	r.Catalog.Snapshots = []SkillSnapshot{localContextSkill("a", `["project:b"]`), localContextSkill("b", "")}
	r.Catalog.Overrides = []CatalogOverride{{"apgr:go-language-profile", "project:a", "/config", strings.Repeat("a", 64)}}
	r.Requests = []ContextSkillRequest{{"apgr:go-language-profile", true}, {"project:b", true}}
	p, err := PlanContext(r)
	if err != nil {
		t.Fatal(err)
	}
	if len(p.SelectedSnapshots) != 2 || !p.RequiredSatisfied {
		t.Fatal("closure not shared")
	}
	requested := 0
	for _, d := range p.Decisions {
		if d.RequestedID == "apgr:go-language-profile" {
			requested++
			if d.Status != "selected" || d.SelectedID != "project:a" {
				t.Fatal("override decision contradicted")
			}
		}
	}
	if requested != 1 {
		t.Fatal("duplicate overridden request decision")
	}
	r.Catalog.Snapshots[0].Path = "/different/a"
	r.Catalog.Overrides[0].ConfigPath = "/elsewhere/config"
	q, _ := PlanContext(r)
	if p.ContentIdentity != q.ContentIdentity {
		t.Fatal("path-dependent identity")
	}
	for _, cycle := range []bool{false, true} {
		if cycle {
			r.Catalog.Snapshots[1] = localContextSkill("b", `["project:a"]`)
		} else {
			r.Catalog.Snapshots = r.Catalog.Snapshots[:1]
		}
		bad, e := PlanContext(r)
		if e != nil {
			t.Fatal(e)
		}
		if bad.RequiredSatisfied || bad.EffectiveMode != "static" {
			t.Fatal("invalid closure accepted")
		}
		r.Catalog.Snapshots = append(r.Catalog.Snapshots[:1], localContextSkill("b", ""))
	}
}
func TestContextPlanSupportWrapperAndQualification(t *testing.T) {
	r := contextFixture()
	s := localContextSkill("a", "")
	s.Body = []byte(strings.Replace(string(s.Body), "---\nfixture", "support: [\"ref.txt\"]\n---\nfixture", 1))
	s.Support = map[string][]byte{"ref.txt": []byte("\"é\"\n")}
	r.Catalog.Snapshots = []SkillSnapshot{s}
	r.Requests = []ContextSkillRequest{{"project:a", true}}
	p, e := PlanContext(r)
	if e != nil {
		t.Fatal(e)
	}
	if p.PayloadCost.Bytes <= int64(len(s.Body)+len(s.Support["ref.txt"])+len(r.Mandatory[0].Text)) {
		t.Fatal("free wrapper")
	}
	r.Qualification = ContextQualification{}
	p, e = PlanContext(r)
	if e != nil {
		t.Fatal(e)
	}
	if p.EffectiveMode != "static" || len(p.Reasons) != 2 || !p.BudgetPassed {
		t.Fatal("qualification not separate from fit")
	}
	r.Affinities = []ContextAffinity{{"review", "project:a", 11}}
	if _, e := PlanContext(r); e == nil {
		t.Fatal("unbounded affinity")
	}
}

func TestContextPlanFootprintAndDependencyAtomicity(t *testing.T) {
	r := contextFixture()
	r.Catalog.Snapshots = []SkillSnapshot{localContextSkill("a", `["project:b"]`), localContextSkill("b", "")}
	r.Requests = []ContextSkillRequest{{"project:a", true}}
	p, err := PlanContext(r)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := ContextPlanFootprint(p); err != nil {
		t.Fatal(err)
	}
	cost := p.PayloadCost.Bytes - 1
	r.Budget.MaxInitialContextBytes = &cost
	p, err = PlanContext(r)
	if err != nil {
		t.Fatal(err)
	}
	if len(p.SelectedSnapshots) != 0 || p.RequiredSatisfied {
		t.Fatal("partial closure packed")
	}
	p.Payload += "tamper"
	if _, err := ContextPlanFootprint(p); err == nil {
		t.Fatal("forged measurement accepted")
	}
}
