package skills

import "sort"

const (
	factCapability               = "capability"
	factExplicit                 = "explicit_skill_id"
	factLanguage                 = "language"
	factRepositoryCharacteristic = "repository_characteristic"
	factRuntime                  = "runtime"
	factTestFramework            = "test_framework"
	factWorkClass                = "work_class"
)

var selectionRulesV1 = []SelectionRule{
	{factCapability, "apg-routing", "agentic-praxis-grimoire-workflow", "skills/README.md#APG16"},
	{factCapability, "astro-framework", "astro-profile", "docs/architecture/v0-6-skill-ownership-and-context-budget.md#2.4"},
	{factCapability, "bash-to-python-conversion", "converting-bash-scripts-to-python", "skills/README.md#APG26"},
	{factCapability, "chatgpt-manager-routing", "chatgpt-manager-workflow", "docs/chatgpt-manager-skill-topology.md"},
	{factCapability, "jsx", "jsx-language-profile", "docs/architecture/v0-6-skill-ownership-and-context-budget.md#2.1"},
	{factCapability, "mdx-documents", "mdx-profile", "docs/architecture/v0-6-skill-ownership-and-context-budget.md#2.3"},
	{factCapability, "react-components", "react-component-profile", "docs/architecture/v0-6-skill-ownership-and-context-budget.md#2.2"},
	{factLanguage, "bash", "bash-language-profile", "skills/README.md"},
	{factLanguage, "css", "css-language-profile", "skills/README.md"},
	{factLanguage, "go", "go-language-profile", "skills/README.md"},
	{factLanguage, "javascript", "javascript-language-profile", "skills/README.md"},
	{factLanguage, "markdown", "markdown-language-profile", "skills/README.md"},
	{factLanguage, "nix", "nix-language-profile", "skills/README.md"},
	{factLanguage, "python", "python-language-profile", "skills/README.md"},
	{factLanguage, "ruby", "ruby-language-profile", "skills/README.md"},
	{factLanguage, "typescript", "typescript-language-profile", "skills/README.md"},
	{factLanguage, "zsh", "zsh-language-profile", "skills/README.md"},
	{factRepositoryCharacteristic, "dockerfile", "dockerfile-profile", "skills/README.md#APG33"},
	{factRepositoryCharacteristic, "postgresql", "postgresql-database-profile", "skills/README.md#APG21"},
	{factRepositoryCharacteristic, "sqlite", "sqlite-database-profile", "skills/README.md#APG21"},
	{factRepositoryCharacteristic, "vagrantfile", "vagrantfile-profile", "skills/README.md#APG34"},
	{factRuntime, "nodejs", "nodejs-runtime-profile", "skills/README.md#APG81H"},
	{factTestFramework, "bats", "bats-test-profile", "skills/README.md#APG19"},
	{factTestFramework, "go-cmp-v0.7.0", "go-cmp-test-profile", "docs/specs/go-testing-component-profiles.md"},
	{factTestFramework, "go-native", "go-test-profile", "docs/specs/go-testing-component-profiles.md"},
	{factTestFramework, "gomock-v0.6.0", "gomock-test-profile", "docs/architecture/v0-6-skill-ownership-and-context-budget.md#2.6"},
	{factTestFramework, "minitest", "minitest-test-profile", "skills/README.md#APG32"},
	{factTestFramework, "nix", "nix-test-profile", "skills/README.md#APG40"},
	{factTestFramework, "pytest", "pytest-test-profile", "skills/README.md#APG26"},
	{factTestFramework, "vitest-v4.1", "vitest-test-profile", "docs/architecture/v0-6-skill-ownership-and-context-budget.md#2.5"},
	{factTestFramework, "zunit-v0.8.2-zsh-v5.9.2", "zunit-test-profile", "skills/README.md#APG22B"},
	{factWorkClass, "debugging", "debugging-systematically", "skills/README.md"},
	{factWorkClass, "design", "designing-significant-changes", "skills/README.md"},
	{factWorkClass, "guidance_synthesis", "synthesizing-repository-guidance", "skills/README.md#APG17"},
	{factWorkClass, "implementation_testing", "implementing-with-test-discipline", "skills/README.md"},
	{factWorkClass, "planning", "planning-repository-work", "skills/README.md"},
	{factWorkClass, "review_verification", "reviewing-and-verifying-repository-work", "skills/README.md"},
	{factWorkClass, "roadmap_delegation", "composing-approved-roadmap-assignments", "docs/chatgpt-manager-skill-topology.md"},
	{factWorkClass, "worker_delegation", "composing-bounded-worker-assignments", "skills/README.md"},
}

var acceptedUnmappedFactsV1 = map[string]map[string]bool{
	factCapability:               {"accessibility": true},
	factLanguage:                 {"c": true, "csharp": true, "java": true, "kotlin": true, "php": true, "rust": true, "swift": true},
	factRepositoryCharacteristic: {"monorepo": true},
	factRuntime:                  {"browser": true, "bun": true, "deno": true, "jvm": true},
	factTestFramework:            {"jest": true, "mocha": true, "rspec": true, "unittest": true},
	factWorkClass:                {"research": true},
}

// SelectionRules returns the complete deterministic v1 fact-to-owner table.
func SelectionRules() []SelectionRule {
	result := append([]SelectionRule(nil), selectionRulesV1...)
	sort.Slice(result, func(left, right int) bool {
		if result[left].FactKind != result[right].FactKind {
			return result[left].FactKind < result[right].FactKind
		}
		return result[left].FactValue < result[right].FactValue
	})
	return result
}

var compositionRulesV1 = canonicalEdges([]CompositionEdge{
	{"astro-profile", "mdx-profile"}, {"astro-profile", "react-component-profile"}, {"astro-profile", "jsx-language-profile"}, {"astro-profile", "typescript-language-profile"}, {"astro-profile", "nodejs-runtime-profile"},
	{"gomock-test-profile", "go-language-profile"}, {"gomock-test-profile", "go-test-profile"}, {"gomock-test-profile", "go-cmp-test-profile"},
	{"jsx-language-profile", "javascript-language-profile"}, {"jsx-language-profile", "typescript-language-profile"}, {"jsx-language-profile", "nodejs-runtime-profile"},
	{"mdx-profile", "markdown-language-profile"}, {"mdx-profile", "jsx-language-profile"}, {"mdx-profile", "react-component-profile"},
	{"react-component-profile", "jsx-language-profile"}, {"react-component-profile", "typescript-language-profile"}, {"react-component-profile", "javascript-language-profile"}, {"react-component-profile", "vitest-test-profile"},
	{"vitest-test-profile", "javascript-language-profile"}, {"vitest-test-profile", "typescript-language-profile"}, {"vitest-test-profile", "nodejs-runtime-profile"},
})

// CompositionRules returns the complete informational v1 composition table.
func CompositionRules() []CompositionEdge {
	return append([]CompositionEdge(nil), compositionRulesV1...)
}

func canonicalEdges(values []CompositionEdge) []CompositionEdge {
	seen := map[CompositionEdge]bool{}
	result := make([]CompositionEdge, 0, len(values))
	for _, edge := range values {
		if edge.To < edge.From {
			edge.From, edge.To = edge.To, edge.From
		}
		if edge.From == edge.To || seen[edge] {
			continue
		}
		seen[edge] = true
		result = append(result, edge)
	}
	sort.Slice(result, func(left, right int) bool {
		if result[left].From != result[right].From {
			return result[left].From < result[right].From
		}
		return result[left].To < result[right].To
	})
	return result
}
