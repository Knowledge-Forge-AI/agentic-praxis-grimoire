package skills

import "testing"

// These fixtures prove structured-fact boundaries, not effective guidance use.
// Technology presence alone must never be promoted to maturity evidence.
func TestHPrimaryPromotionFactBoundaries(t *testing.T) {
	cases := []struct {
		id       string
		positive ContextFact
		negative []ContextFact
	}{
		{"go-language-profile", ContextFact{"language", "go"}, []ContextFact{{"test_framework", "go-native"}, {"language", "python"}}},
		{"go-test-profile", ContextFact{"test_framework", "go-native"}, []ContextFact{{"language", "go"}, {"test_framework", "pytest"}}},
		{"pytest-test-profile", ContextFact{"test_framework", "pytest"}, []ContextFact{{"test_framework", "bats"}, {"test_framework", "unittest"}}},
		{"markdown-language-profile", ContextFact{"language", "markdown"}, []ContextFact{{"language", "mdx"}, {"language", "json"}}},
		{"sqlite-database-profile", ContextFact{"repository_characteristic", "sqlite"}, []ContextFact{{"repository_characteristic", "postgresql"}, {"language", "sql"}}},
	}
	for _, c := range cases {
		t.Run(c.id, func(t *testing.T) {
			for _, role := range []string{"Producer", "Work Review"} {
				for i, fact := range append([]ContextFact{c.positive}, c.negative...) {
					r := contextFixture()
					r.Roles = []string{role}
					r.Facts = []ContextFact{fact}
					p, err := PlanContext(r)
					if err != nil {
						t.Fatal(err)
					}
					selected := false
					for _, s := range p.SelectedSnapshots {
						if s.QualifiedID == "apgr:"+c.id {
							selected = true
						}
					}
					if selected != (i == 0) {
						t.Fatalf("role %s fact %+v selected=%v", role, fact, selected)
					}
				}
			}
		})
	}
}
