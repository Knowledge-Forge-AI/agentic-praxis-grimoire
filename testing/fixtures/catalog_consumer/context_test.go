package main

import (
	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/skills"
	"testing"
)

// The embedding application supplies immutable task text and binding identity.
// This prospective plan grants no provider projection or acquisition authority.
func TestContextConsumer(t *testing.T) {
	request := skills.ContextPlanRequest{SchemaVersion: skills.ContextPlanSchemaV1,
		RunID: "consumer-run", BindingID: "producer-and-disposition", AttemptID: "attempt-2",
		Roles: []string{"producer", "plan_review_disposition"}, Consumer: skills.ConsumerGo, RequestedMode: "adaptive",
		Catalog:   skills.CatalogInput{SchemaVersion: skills.CatalogSchemaV1},
		Facts:     []skills.ContextFact{{Kind: "language", Value: "go"}, {Kind: "test_framework", Value: "go-native"}},
		Mandatory: []skills.ContextComponent{{ID: "task", Kind: "authority", Text: "Inspect only the supplied fixture.\n"}}}
	plan, err := skills.PlanContext(request)
	if err != nil {
		t.Fatal(err)
	}
	if plan.EffectiveMode != "static" || !plan.RequiredSatisfied || len(plan.SelectedSnapshots) != 2 {
		t.Fatal("unexpected prospective plan")
	}
	if _, err := skills.ContextPlanFootprint(plan); err != nil {
		t.Fatal(err)
	}
	if plan.Tokens != nil || plan.ProviderNativeOverhead != nil {
		t.Fatal("fabricated provider metrics")
	}
}
