// Package skills embeds the canonical APG skill corpus and resolves
// deterministic, task-scoped bundles without prompt interpretation.
package skills

import (
	"bytes"
	"fmt"
	"sort"
	"strings"
	"unicode/utf8"
)

const (
	// DiscoveryPolicyVersionV010 identifies the versioned v0.10 discovery capacity policy (historical).
	DiscoveryPolicyVersionV010 = "v0.10"
	// DiscoveryPolicyVersionV010BrowserUI identifies the versioned v0.10-browser-ui discovery capacity policy (historical).
	DiscoveryPolicyVersionV010BrowserUI = "v0.10-browser-ui"
	// DiscoveryPolicyVersionV010Toolchain identifies the versioned v0.10-toolchain discovery capacity policy (historical).
	DiscoveryPolicyVersionV010Toolchain = "v0.10-toolchain"
	// DiscoveryPolicyVersionV010BrowserRuntime identifies the versioned v0.10-browser-runtime discovery capacity policy (current).
	DiscoveryPolicyVersionV010BrowserRuntime = "v0.10-browser-runtime"
	// DiscoveryPolicyVersion is the current active discovery policy version.
	DiscoveryPolicyVersion = DiscoveryPolicyVersionV010BrowserRuntime

	// HistoricalSkillCount is the preserved original leaf count (39 leaves).
	HistoricalSkillCount = 39
	// HistoricalDescriptionBytes is the preserved total UTF-8 description byte count of the 39 original skills.
	HistoricalDescriptionBytes = int64(9504)
	// HistoricalDescriptionCharacters is the preserved total character count of the 39 original skills.
	HistoricalDescriptionCharacters = int64(9492)
	// HistoricalGlobalDescriptionLimit preserves the historical limit semantics.
	HistoricalGlobalDescriptionLimit = GlobalDescriptionLimit // 9527

	// V010MaxReservationDescriptionBytes is the maximum description UTF-8 byte reservation per admitted candidate (<= 330 bytes).
	V010MaxReservationDescriptionBytes = int64(330)
	// V010CurrentSVGAdmissionCeiling is the maximum total description byte ceiling upon SVG admission (9527 + 330 = 9857).
	V010CurrentSVGAdmissionCeiling = int64(9857)
	// V010BrowserUIAdmissionCeiling is the maximum total description byte ceiling upon browser-ui admission (9527 + 3*330 = 10517).
	V010BrowserUIAdmissionCeiling = int64(10517)
	// V010CurrentBrowserUIAdmissionCeiling is an alias for the v0.10-browser-ui admission ceiling.
	V010CurrentBrowserUIAdmissionCeiling = V010BrowserUIAdmissionCeiling
	// V010ToolchainAdmissionCeiling is the maximum total description byte ceiling upon toolchain admission (9527 + 5*330 = 11177).
	V010ToolchainAdmissionCeiling = int64(11177)
	// V010CurrentToolchainAdmissionCeiling is an alias for the v0.10-toolchain admission ceiling.
	V010CurrentToolchainAdmissionCeiling = V010ToolchainAdmissionCeiling
	// V010BrowserRuntimeAdmissionCeiling is the maximum total description byte ceiling upon browser-runtime admission (9527 + 6*330 = 11507).
	V010BrowserRuntimeAdmissionCeiling = int64(11507)
	// V010CurrentBrowserRuntimeAdmissionCeiling is an alias for the v0.10-browser-runtime admission ceiling.
	V010CurrentBrowserRuntimeAdmissionCeiling = V010BrowserRuntimeAdmissionCeiling
	// V010OverallFutureCeiling is the overall future ceiling across all six candidates (9527 + 6*330 = 11507).
	V010OverallFutureCeiling = int64(11507)
	// V010MaxSVGFileBytes is the maximum allowed file byte size for the SVG skill leaf (<= 20480 bytes).
	V010MaxSVGFileBytes = int64(20480)
	// V010CurrentAdmittedCandidate is the single candidate profile authorized for admission at count 40 (historical).
	V010CurrentAdmittedCandidate = "svg-language-profile"
	// V010AdmittedSkillCount is the expected skill count after SVG admission (40 leaves, historical).
	V010AdmittedSkillCount = 40
	// V010BrowserUIAdmittedSkillCount is the expected skill count under v0.10-browser-ui (42 leaves).
	V010BrowserUIAdmittedSkillCount = 42
	// V010ToolchainAdmittedSkillCount is the expected skill count under v0.10-toolchain (44 leaves).
	V010ToolchainAdmittedSkillCount = 44
	// V010BrowserRuntimeAdmittedSkillCount is the expected skill count under v0.10-browser-runtime (45 leaves).
	V010BrowserRuntimeAdmittedSkillCount = 45

	// FrozenSVGSkillDescription records the byte-identical description frozen for svg-language-profile under v0.10-browser-ui, v0.10-toolchain, and v0.10-browser-runtime.
	FrozenSVGSkillDescription = "Use when SVG authoring depends on namespaces, viewBox, paths, transforms, paint, reuse, clipping, masking, text, naming, resources, or serialization; not for general CSS, JSX, React, browser runtime, accessibility audits, or test automation."

	// FrozenPlaywrightSkillDescription records the byte-identical description frozen for playwright-test-profile under v0.10-toolchain and v0.10-browser-runtime.
	FrozenPlaywrightSkillDescription = "Use when a project selects Playwright Test and decisions depend on configuration, fixtures, locators, waiting, isolation, parallel execution, browser projects, network controls, or test artifacts; not for accessibility standards or general browser/runtime semantics."

	// FrozenWebAccessibilitySkillDescription records the byte-identical description frozen for web-accessibility-profile under v0.10-toolchain and v0.10-browser-runtime.
	FrozenWebAccessibilitySkillDescription = "Use when web implementation decisions affect native semantics, accessible names, keyboard and focus behavior, images/SVG, forms, dynamic content, motion, contrast, or accessibility evidence; not for test-runner mechanics or a claim of automated WCAG conformance."

	// FrozenViteSkillDescription records the byte-identical description frozen for vite-build-profile under v0.10-browser-runtime.
	FrozenViteSkillDescription = "Use when a project selects Vite for dev serving or production building and decisions depend on root, base, publicDir, mode, env prefixes, loopback fs limits, Rolldown bundling, alias/CSS/plugin hooks, SSR seams, or preview."

	// FrozenNPMSkillDescription records the byte-identical description frozen for npm-package-manager-profile under v0.10-browser-runtime.
	FrozenNPMSkillDescription = "Use when package management decisions depend on npm CLI contracts, package.json and lockfile v3 integrity, install versus ci execution, peer dependencies and overrides, workspaces, script lifecycle and ignore-scripts, local pack tarballs, caching, or publication provenance; not for Node host runtime or bundler transforms."
)

// V010EligibleCandidates lists all six candidate profiles eligible under the v0.10 discovery policy.
var V010EligibleCandidates = []string{
	"svg-language-profile",
	"playwright-test-profile",
	"web-accessibility-profile",
	"browser-runtime-profile",
	"npm-package-manager-profile",
	"vite-build-profile",
}

// V010BrowserUIAdmittedCandidates lists the three candidate profiles authorized for admission under v0.10-browser-ui (42 leaves).
var V010BrowserUIAdmittedCandidates = []string{
	"svg-language-profile",
	"playwright-test-profile",
	"web-accessibility-profile",
}

// V010ToolchainAdmittedCandidates lists the five candidate profiles authorized for admission under v0.10-toolchain (44 leaves).
var V010ToolchainAdmittedCandidates = []string{
	"svg-language-profile",
	"playwright-test-profile",
	"web-accessibility-profile",
	"vite-build-profile",
	"npm-package-manager-profile",
}

// V010BrowserRuntimeAdmittedCandidates lists the six candidate profiles authorized for admission under v0.10-browser-runtime (45 leaves).
var V010BrowserRuntimeAdmittedCandidates = []string{
	"svg-language-profile",
	"playwright-test-profile",
	"web-accessibility-profile",
	"vite-build-profile",
	"npm-package-manager-profile",
	"browser-runtime-profile",
}

// Documented update requirement:
// The original 39 skill identities and their exact descriptions are frozen under
// Discovery Policy v0.10. Modifying, renaming, removing, or changing descriptions
// of the original 39 skills constitutes reservation theft and requires formal APG
// governance authorization and an approved specification change.
const FrozenOriginal39Digest = "f9255d38eadff7b2bfc5ab13cd1722b8d98ac1ea974d8220475ff7067a1e8cc7"

// Original39SkillDescriptions records the immutable baseline of original skill identities and descriptions.
var Original39SkillDescriptions = map[string]string{
	"agentic-praxis-grimoire-workflow":        "Use when an operator or manager needs to choose among multiple plausible APG skills, audit an APG routing decision, or diagnose a missing or stale APG capability.",
	"astro-profile":                           "Use when Astro behavior hinges on .astro execution, islands/client directives, server/client boundaries, collections, routing, or integrations; not for React, JSX, MDX, TypeScript, Node, Vite, Starlight, CSS, accessibility, or deployment.",
	"bash-language-profile":                   "Use when Bash-specific judgment is material to quoting, expansion, arrays, pipelines, traps, subprocesses, files, portability, or warning and crisis thresholds beyond repository policy.",
	"bats-test-profile":                       "Use when Bats-specific test judgment is material to evaluation, run status and output, hooks, fixtures, TAP, file descriptors, parallelism, background cleanup, or warning and crisis thresholds beyond repository policy.",
	"chatgpt-manager-workflow":                "Use when selection among multiple plausible ChatGPT top-level-manager capabilities is ambiguous or a ChatGPT-manager routing decision requires audit.",
	"composing-approved-roadmap-assignments":  "Use when a human-approved roadmap phase or explicitly approved bounded phase sequence must become a reviewable top-level coding-agent manager assignment with authority, scope, evidence, acceptance, stop, reporting, and handoff boundaries.",
	"composing-bounded-worker-assignments":    "Use when internal delegation is already authorized and independently selected, and one non-trivial worker assignment needs explicit scope, ownership, evidence, acceptance, or return boundaries.",
	"converting-bash-scripts-to-python":       "Use when an existing Bash executable or script family needs a bounded conversion to Python that preserves or deliberately migrates its observable contract.",
	"css-language-profile":                    "Use when a material decision depends on CSS-specific static semantics \u2014 syntax validity, selector specificity, cascade ordering, inheritance, shorthand resets, custom-property substitution, or value consequences \u2014 for an established CSS region whose artifact boundary and consequence-bearing evidence are identified.",
	"debugging-systematically":                "Use when behavior is failing, inconsistent, flaky, unexplained, or affected by multiple plausible causes.",
	"designing-significant-changes":           "Use when consequential behavior, architecture, ownership, interfaces, data contracts, safety boundaries, or irreversible choices remain unresolved before implementation.",
	"dockerfile-profile":                      "Use when Dockerfile-specific judgment is material to parser directives, build stages, instruction forms, variable scope, build context, copies, mounts, cache behavior, file ownership, runtime metadata, platform behavior, or warning and crisis thresholds beyond repository policy.",
	"go-cmp-test-profile":                     "Use when a repository has already selected google/go-cmp v0.7.0 and comparison judgment is material to equality versus diff, option composition and filters, comparers and transformers, ignores and unexported fields, sorting, approximation, panics, diagnostic exposure, or thresholds beyond repository policy.",
	"go-language-profile":                     "Use when Go-specific judgment is material to structure, errors, context, interfaces, generics, concurrency, public APIs, reflection, unsafe, cgo, subprocesses, compatibility, or warning and crisis thresholds beyond repository policy.",
	"go-test-profile":                         "Use when native Go test judgment is material to package placement, subtests, helper attribution, cleanup and isolation, TestMain, parallelism, goroutine reporting, examples, benchmarks, fuzzing, caching, effective language version, or warning and crisis thresholds beyond repository policy.",
	"gomock-test-profile":                     "Use when a project has already selected GoMock v0.6.0 and judgment is material to mockgen generation, generated mocks, controller lifecycle, expectations, call counts or order, matchers, or GoMock failure diagnosis; not for native test lifecycle, value diffs, or Go semantics.",
	"implementing-with-test-discipline":       "Use when implementing a bugfix, new behavior, behavioral refactor, schema or contract change, or another code change whose correctness benefits from executable evidence.",
	"javascript-language-profile":             "Use when a material decision depends on ECMAScript language semantics \u2014 evaluation order, lexical scope and temporal dead zones, coercion and equality, prototypes and property descriptors, this binding, classes, iteration, completion values, promise and async semantics, or module live bindings \u2014 for an established JavaScript source region whose parse goal, strictness state, and whole-file owner are identified.",
	"jsx-language-profile":                    "Use when JSX-specific judgment is material to element, attribute, child, expression, fragment, spread, file-kind, or transform semantics; not for React behavior, TypeScript checking, JavaScript evaluation, runtime hosts, MDX, Astro, or build tools.",
	"markdown-language-profile":               "Use when a material decision depends on the repository's actual Markdown parser or selected-dialect document semantics, or on qualitative Markdown document-structure policy.",
	"mdx-profile":                             "Use when an MDX decision depends on the Markdown-to-JSX/component seam, imports/exports, expressions, provider mapping, or compile/runtime split; not for pure Markdown, JSX, React, TypeScript, JavaScript, or Astro.",
	"minitest-test-profile":                   "Use when Minitest-specific judgment is material to test or spec organization, assertions, lifecycle, mocks, stubs, fixture alternatives, isolation, parallelism, filtering, runners, plugins, reporters, subprocess, filesystem, or database test boundaries, or warning and crisis thresholds beyond repository policy.",
	"nix-language-profile":                    "Use when Nix-specific judgment is material to expressions, attribute sets, modules, derivations, flakes, overlays, purity, evaluation, store exposure, activation, remote builders, or warning and crisis thresholds beyond repository policy.",
	"nix-test-profile":                        "Use when Nix test judgment is material to selecting which already-selected testing surface can prove an exact claim, package check and install-check behavior, flake checks, Nixpkgs or NixOS test ownership, test-evidence qualification across sandbox, store, builder, or cache boundaries, or Nix-test-specific structural review.",
	"nodejs-runtime-profile":                  "Use when a material decision depends on Node.js-specific host behavior \u2014 package scope and module mapping, CommonJS wrapper bindings, ESM host metadata, specifier resolution and package exports, module identity, process and CLI state, stdio and exit status, filesystem and path APIs, errors, signals, timers and the event loop, child processes and workers, or Node's exposure of network and Web-compatible APIs \u2014 for an established Node execution role whose exact version, platform, flags, package scope, loader, and whole-file owner are identified.",
	"planning-repository-work":                "Use when an accepted objective requires multiple dependent implementation steps, cross-file coordination, staged risk reduction, or a durable handoff.",
	"postgresql-database-profile":             "Use when PostgreSQL-specific judgment is material to SQL, schemas, MVCC, transactions, locks, DDL, migrations, routines, triggers, security, backup and restore, replication, maintenance, or warning and crisis thresholds beyond repository policy.",
	"pytest-test-profile":                     "Use when pytest-specific judgment is material to discovery, collection, assertions, fixtures, parametrization, mocks, isolation, xdist, coverage, or warning and crisis thresholds beyond repository policy.",
	"python-language-profile":                 "Use when Python implementation, design, debugging, or review needs Python-specific judgment about structure, complexity, public APIs, typing, concurrency, serialization, packaging, or warning and crisis thresholds beyond repository policy.",
	"react-component-profile":                 "Use when React component judgment is material to composition, props, rendering, state, effects, hooks, context, memoization, error boundaries, or component testing; not for JSX syntax, language typing, runner mechanics, routing, styling, MDX, Astro, or metaframeworks.",
	"reviewing-and-verifying-repository-work": "Use when a bounded repository artifact, change, phase, commit, or worker result requires evidence-backed acceptance, correction, disposition, or a completion claim.",
	"ruby-language-profile":                   "Use when Ruby-specific judgment is material to structure, exceptions, blocks, shared state, dynamic dispatch, metaprogramming, callbacks, concurrency, gems, public compatibility, serialization, subprocesses, or warning and crisis thresholds beyond repository policy.",
	"sqlite-database-profile":                 "Use when SQLite-specific judgment is material to SQL, transaction modes, single-writer concurrency, busy handling, journal or WAL behavior, schema rebuilds, pragmas, affinity, file ownership, backup and integrity, extensions, or warning and crisis thresholds beyond repository policy.",
	"synthesizing-repository-guidance":        "Use when a dense, duplicated, mixed-scope, private, or source-derived guidance corpus needs ownership, provenance, privacy, migration, or rejection dispositions before any rewrite.",
	"typescript-language-profile":             "Use when a material decision depends on TypeScript-specific static semantics or type-erasure boundaries for an established source region, after the exact compiler role, version, options, project, source kind, and declaration environment are evidenced.",
	"vagrantfile-profile":                     "Use when Vagrantfile-specific judgment is material to configuration versions and loading, machines, boxes, provider blocks, networks, synced folders, provisioners, triggers, Vagrant state, host-dependent behavior, or warning and crisis thresholds beyond repository policy.",
	"vitest-test-profile":                     "Use when a project has already selected Vitest 4.1 and runner-specific judgment is material to configuration, projects, environments, assertions, mocks, timers, concurrency, isolation, snapshots, or coverage providers; not for test sufficiency, language or React semantics, or coverage policy.",
	"zsh-language-profile":                    "Use when Zsh-specific judgment is material to option state, arrays, expansion, globbing, autoloading, startup or interactive behavior, hooks, modules, processes, or warning and crisis thresholds beyond repository policy.",
	"zunit-test-profile":                      "Use when a repository explicitly uses the APG-verified ZUnit v0.8.2 and Zsh 5.9.2 pair and needs ZUnit-specific judgment about runner invocation, discovery, assertions, hooks, configuration, output, isolation, process cleanup, compatibility, or warning and crisis thresholds beyond repository policy.",
}

// ComputeOriginal39Digest computes the SHA-256 hex digest of the 39 original skill identities and descriptions.
func ComputeOriginal39Digest(descriptions map[string]string) string {
	names := make([]string, 0, len(descriptions))
	for name := range descriptions {
		names = append(names, name)
	}
	sort.Strings(names)
	var buf bytes.Buffer
	for _, name := range names {
		buf.WriteString(name)
		buf.WriteString(":")
		buf.WriteString(descriptions[name])
		buf.WriteString("\n")
	}
	return sha256Hex(buf.Bytes())
}

// ValidateDiscoveryPolicy validates a slice of SkillMetadata against the versioned discovery policy.
// Under v0.10 (historical):
// - Policy version must be "v0.10".
// - Exactly 39 leaves (pre-leaf baseline) or 40 leaves (after SVG admission).
// - All original 39 skills must be present with exact frozen descriptions and matching digest.
// - At 39 leaves: total description bytes == 9504, chars == 9492, <= GlobalDescriptionLimit (9527).
// - At 40 leaves: the 40th skill must be "svg-language-profile"; other candidates are rejected.
// - svg-language-profile description UTF-8 bytes <= 330.
// - svg-language-profile file body bytes <= 20480.
// - Total description bytes <= 9857 (current SVG admission ceiling) and <= 11507 (overall future ceiling).
//
// Under v0.10-browser-ui (historical):
// - Policy version must be "v0.10-browser-ui".
// - Exactly 42 leaves: original 39 + svg-language-profile + playwright-test-profile + web-accessibility-profile.
// - All original 39 skills must be present with exact frozen descriptions and matching digest.
// - svg-language-profile description must be byte-identical to FrozenSVGSkillDescription.
// - svg-language-profile file body bytes <= 20480.
// - playwright-test-profile and web-accessibility-profile have no added fixed body ceiling.
// - Each candidate description UTF-8 bytes <= 330.
// - Total description bytes <= 10517 (V010BrowserUIAdmissionCeiling) and <= 11507 (overall future ceiling).
//
// Under v0.10-toolchain (historical):
// - Policy version must be "v0.10-toolchain".
// - Exactly 44 leaves: original 39 + svg-language-profile + playwright-test-profile + web-accessibility-profile + vite-build-profile + npm-package-manager-profile.
// - All original 39 skills must be present with exact frozen descriptions and matching digest.
// - svg-language-profile description must be byte-identical to FrozenSVGSkillDescription.
// - svg-language-profile file body bytes <= 20480.
// - playwright-test-profile description must be byte-identical to FrozenPlaywrightSkillDescription.
// - web-accessibility-profile description must be byte-identical to FrozenWebAccessibilitySkillDescription.
// - vite-build-profile and npm-package-manager-profile have no added fixed body ceiling.
// - Each candidate description UTF-8 bytes <= 330.
// - Total description bytes <= 11177 (V010ToolchainAdmissionCeiling) and <= 11507 (overall future ceiling).
//
// Under v0.10-browser-runtime (current):
// - Policy version must be "v0.10-browser-runtime".
// - Exactly 45 leaves: original 39 + svg-language-profile + playwright-test-profile + web-accessibility-profile + vite-build-profile + npm-package-manager-profile + browser-runtime-profile.
// - All original 39 skills must be present with exact frozen descriptions and matching digest.
// - svg-language-profile description must be byte-identical to FrozenSVGSkillDescription.
// - svg-language-profile file body bytes <= 20480.
// - playwright-test-profile description must be byte-identical to FrozenPlaywrightSkillDescription.
// - web-accessibility-profile description must be byte-identical to FrozenWebAccessibilitySkillDescription.
// - vite-build-profile description must be byte-identical to FrozenViteSkillDescription.
// - npm-package-manager-profile description must be byte-identical to FrozenNPMSkillDescription.
// - browser-runtime-profile and other new non-SVG profiles have no added fixed body ceiling.
// - Each candidate description UTF-8 bytes <= 330.
// - Total description bytes <= 11507 (V010BrowserRuntimeAdmissionCeiling) and <= 11507 (overall future ceiling).
func ValidateDiscoveryPolicy(policyVersion string, skillList []SkillMetadata) error {
	switch policyVersion {
	case DiscoveryPolicyVersionV010:
		if len(skillList) != HistoricalSkillCount && len(skillList) != V010AdmittedSkillCount {
			return fmt.Errorf("%w: expected %d or %d leaves under %s discovery policy, got %d",
				ErrCorpusMismatch, HistoricalSkillCount, V010AdmittedSkillCount, policyVersion, len(skillList))
		}
	case DiscoveryPolicyVersionV010BrowserUI:
		if len(skillList) != V010BrowserUIAdmittedSkillCount {
			return fmt.Errorf("%w: expected %d leaves under %s discovery policy, got %d",
				ErrCorpusMismatch, V010BrowserUIAdmittedSkillCount, policyVersion, len(skillList))
		}
	case DiscoveryPolicyVersionV010Toolchain:
		if len(skillList) != V010ToolchainAdmittedSkillCount {
			return fmt.Errorf("%w: expected %d leaves under %s discovery policy, got %d",
				ErrCorpusMismatch, V010ToolchainAdmittedSkillCount, policyVersion, len(skillList))
		}
	case DiscoveryPolicyVersionV010BrowserRuntime:
		if len(skillList) != V010BrowserRuntimeAdmittedSkillCount {
			return fmt.Errorf("%w: expected %d leaves under %s discovery policy, got %d",
				ErrCorpusMismatch, V010BrowserRuntimeAdmittedSkillCount, policyVersion, len(skillList))
		}
	default:
		return fmt.Errorf("%w: unknown discovery policy %q", ErrCorpusMismatch, policyVersion)
	}

	byID := make(map[string]SkillMetadata, len(skillList))
	var totalBytes, totalChars int64

	for _, skill := range skillList {
		if skill.ID == "" || skill.Description == "" {
			return fmt.Errorf("%w: malformed skill metadata with empty ID or description", ErrCorpusMismatch)
		}
		if !strings.HasPrefix(skill.Description, "Use when ") {
			return fmt.Errorf("%w: skill %q description must begin with 'Use when '", ErrCorpusMismatch, skill.ID)
		}
		measuredBytes := int64(len([]byte(skill.Description)))
		measuredChars := int64(utf8.RuneCountInString(skill.Description))
		if skill.DescriptionBytes != measuredBytes {
			return fmt.Errorf("%w: skill %q description bytes mismatch (recorded %d, measured %d)",
				ErrCorpusMismatch, skill.ID, skill.DescriptionBytes, measuredBytes)
		}
		if skill.DescriptionCharacters != measuredChars {
			return fmt.Errorf("%w: skill %q description characters mismatch (recorded %d, measured %d)",
				ErrCorpusMismatch, skill.ID, skill.DescriptionCharacters, measuredChars)
		}
		if skill.DescriptionBytes <= 0 || skill.DescriptionCharacters <= 0 {
			return fmt.Errorf("%w: skill %q has non-positive description measurements (bytes=%d, chars=%d)",
				ErrCorpusMismatch, skill.ID, skill.DescriptionBytes, skill.DescriptionCharacters)
		}
		if skill.BodyBytes <= 0 || skill.BodyCharacters <= 0 {
			return fmt.Errorf("%w: skill %q has non-positive body measurements (bytes=%d, chars=%d)",
				ErrCorpusMismatch, skill.ID, skill.BodyBytes, skill.BodyCharacters)
		}
		if skill.Lines <= 0 {
			return fmt.Errorf("%w: skill %q has non-positive line count %d", ErrCorpusMismatch, skill.ID, skill.Lines)
		}
		if len(skill.BodySHA256) != 64 {
			return fmt.Errorf("%w: skill %q has invalid body SHA256 digest %q", ErrCorpusMismatch, skill.ID, skill.BodySHA256)
		}
		if _, exists := byID[skill.ID]; exists {
			return fmt.Errorf("%w: duplicate skill ID %q", ErrCorpusMismatch, skill.ID)
		}
		byID[skill.ID] = skill
		totalBytes += measuredBytes
		totalChars += measuredChars
	}

	// Verify all original 39 skills are present and unchanged
	for origName, origDesc := range Original39SkillDescriptions {
		skill, ok := byID[origName]
		if !ok {
			return fmt.Errorf("%w: missing original 39 skill %q", ErrCorpusMismatch, origName)
		}
		if skill.Description != origDesc {
			return fmt.Errorf("%w: original 39 skill %q description mutated (reservation theft)", ErrCorpusMismatch, origName)
		}
	}

	// Verify frozen digest of original 39 skills
	origMap := make(map[string]string, HistoricalSkillCount)
	for origName := range Original39SkillDescriptions {
		origMap[origName] = byID[origName].Description
	}
	if digest := ComputeOriginal39Digest(origMap); digest != FrozenOriginal39Digest {
		return fmt.Errorf("%w: original 39 digest mismatch: got %s, want %s", ErrCorpusMismatch, digest, FrozenOriginal39Digest)
	}

	if policyVersion == DiscoveryPolicyVersionV010 {
		if len(skillList) == HistoricalSkillCount {
			if totalBytes != HistoricalDescriptionBytes || totalChars != HistoricalDescriptionCharacters || totalBytes > GlobalDescriptionLimit {
				return fmt.Errorf("%w: baseline description footprint mismatch: bytes=%d, chars=%d, limit=%d",
					ErrCorpusMismatch, totalBytes, totalChars, GlobalDescriptionLimit)
			}
			return nil
		}

		// len(skillList) == V010AdmittedSkillCount (40)
		var addedSkill *SkillMetadata
		for i := range skillList {
			if _, isOrig := Original39SkillDescriptions[skillList[i].ID]; !isOrig {
				if addedSkill != nil {
					return fmt.Errorf("%w: multiple non-original skills in admission: %q and %q",
						ErrCorpusMismatch, addedSkill.ID, skillList[i].ID)
				}
				addedSkill = &skillList[i]
			}
		}
		if addedSkill == nil {
			return fmt.Errorf("%w: expected 40th admitted candidate skill not found", ErrCorpusMismatch)
		}

		if addedSkill.ID != V010CurrentAdmittedCandidate {
			return fmt.Errorf("%w: candidate %q is not authorized for admission under %s discovery policy",
				ErrCorpusMismatch, addedSkill.ID, policyVersion)
		}
		if addedSkill.DescriptionBytes <= 0 || addedSkill.DescriptionBytes > V010MaxReservationDescriptionBytes {
			return fmt.Errorf("%w: candidate %q description bytes %d exceeds reservation ceiling of %d (must be in 1..%d)",
				ErrCorpusMismatch, addedSkill.ID, addedSkill.DescriptionBytes, V010MaxReservationDescriptionBytes, V010MaxReservationDescriptionBytes)
		}
		if addedSkill.BodyBytes <= 0 || addedSkill.BodyBytes > V010MaxSVGFileBytes {
			return fmt.Errorf("%w: candidate %q body bytes %d exceeds SVG file limit of %d (must be in 1..%d)",
				ErrCorpusMismatch, addedSkill.ID, addedSkill.BodyBytes, V010MaxSVGFileBytes, V010MaxSVGFileBytes)
		}
		if totalBytes > V010CurrentSVGAdmissionCeiling {
			return fmt.Errorf("%w: total description bytes %d exceeds current SVG admission ceiling of %d",
				ErrCorpusMismatch, totalBytes, V010CurrentSVGAdmissionCeiling)
		}
		if totalBytes > V010OverallFutureCeiling {
			return fmt.Errorf("%w: total description bytes %d exceeds overall future ceiling of %d",
				ErrCorpusMismatch, totalBytes, V010OverallFutureCeiling)
		}
		return nil
	}

	if policyVersion == DiscoveryPolicyVersionV010BrowserUI {
		requiredCandidates := map[string]bool{
			"svg-language-profile":      true,
			"playwright-test-profile":   true,
			"web-accessibility-profile": true,
		}

		for id := range byID {
			if _, isOrig := Original39SkillDescriptions[id]; !isOrig {
				if !requiredCandidates[id] {
					return fmt.Errorf("%w: candidate %q is not authorized for admission under %s discovery policy",
						ErrCorpusMismatch, id, policyVersion)
				}
			}
		}

		for req := range requiredCandidates {
			cand, ok := byID[req]
			if !ok {
				return fmt.Errorf("%w: missing required candidate skill %q", ErrCorpusMismatch, req)
			}
			if cand.DescriptionBytes <= 0 || cand.DescriptionBytes > V010MaxReservationDescriptionBytes {
				return fmt.Errorf("%w: candidate %q description bytes %d exceeds reservation ceiling of %d (must be in 1..%d)",
					ErrCorpusMismatch, cand.ID, cand.DescriptionBytes, V010MaxReservationDescriptionBytes, V010MaxReservationDescriptionBytes)
			}
			if req == "svg-language-profile" {
				if cand.Description != FrozenSVGSkillDescription {
					return fmt.Errorf("%w: candidate %q description mutated (reservation theft)", ErrCorpusMismatch, cand.ID)
				}
				if cand.BodyBytes <= 0 || cand.BodyBytes > V010MaxSVGFileBytes {
					return fmt.Errorf("%w: candidate %q body bytes %d exceeds SVG file limit of %d (must be in 1..%d)",
						ErrCorpusMismatch, cand.ID, cand.BodyBytes, V010MaxSVGFileBytes, V010MaxSVGFileBytes)
				}
			}
		}

		if totalBytes > V010BrowserUIAdmissionCeiling {
			return fmt.Errorf("%w: total description bytes %d exceeds current browser UI admission ceiling of %d",
				ErrCorpusMismatch, totalBytes, V010BrowserUIAdmissionCeiling)
		}
		if totalBytes > V010OverallFutureCeiling {
			return fmt.Errorf("%w: total description bytes %d exceeds overall future ceiling of %d",
				ErrCorpusMismatch, totalBytes, V010OverallFutureCeiling)
		}

		return nil
	}

	if policyVersion == DiscoveryPolicyVersionV010Toolchain {
		requiredCandidates := map[string]bool{
			"svg-language-profile":        true,
			"playwright-test-profile":     true,
			"web-accessibility-profile":   true,
			"vite-build-profile":          true,
			"npm-package-manager-profile": true,
		}

		for id := range byID {
			if _, isOrig := Original39SkillDescriptions[id]; !isOrig {
				if !requiredCandidates[id] {
					return fmt.Errorf("%w: candidate %q is not authorized for admission under %s discovery policy",
						ErrCorpusMismatch, id, policyVersion)
				}
			}
		}

		for req := range requiredCandidates {
			cand, ok := byID[req]
			if !ok {
				return fmt.Errorf("%w: missing required candidate skill %q", ErrCorpusMismatch, req)
			}
			if cand.DescriptionBytes <= 0 || cand.DescriptionBytes > V010MaxReservationDescriptionBytes {
				return fmt.Errorf("%w: candidate %q description bytes %d exceeds reservation ceiling of %d (must be in 1..%d)",
					ErrCorpusMismatch, cand.ID, cand.DescriptionBytes, V010MaxReservationDescriptionBytes, V010MaxReservationDescriptionBytes)
			}
			switch req {
			case "svg-language-profile":
				if cand.Description != FrozenSVGSkillDescription {
					return fmt.Errorf("%w: candidate %q description mutated (reservation theft)", ErrCorpusMismatch, cand.ID)
				}
				if cand.BodyBytes <= 0 || cand.BodyBytes > V010MaxSVGFileBytes {
					return fmt.Errorf("%w: candidate %q body bytes %d exceeds SVG file limit of %d (must be in 1..%d)",
						ErrCorpusMismatch, cand.ID, cand.BodyBytes, V010MaxSVGFileBytes, V010MaxSVGFileBytes)
				}
			case "playwright-test-profile":
				if cand.Description != FrozenPlaywrightSkillDescription {
					return fmt.Errorf("%w: candidate %q description mutated (reservation theft)", ErrCorpusMismatch, cand.ID)
				}
			case "web-accessibility-profile":
				if cand.Description != FrozenWebAccessibilitySkillDescription {
					return fmt.Errorf("%w: candidate %q description mutated (reservation theft)", ErrCorpusMismatch, cand.ID)
				}
			}
		}

		if totalBytes > V010ToolchainAdmissionCeiling {
			return fmt.Errorf("%w: total description bytes %d exceeds current toolchain admission ceiling of %d",
				ErrCorpusMismatch, totalBytes, V010ToolchainAdmissionCeiling)
		}
		if totalBytes > V010OverallFutureCeiling {
			return fmt.Errorf("%w: total description bytes %d exceeds overall future ceiling of %d",
				ErrCorpusMismatch, totalBytes, V010OverallFutureCeiling)
		}

		return nil
	}

	// policyVersion == DiscoveryPolicyVersionV010BrowserRuntime (45 leaves)
	requiredCandidates := map[string]bool{
		"svg-language-profile":        true,
		"playwright-test-profile":     true,
		"web-accessibility-profile":   true,
		"vite-build-profile":          true,
		"npm-package-manager-profile": true,
		"browser-runtime-profile":     true,
	}

	for id := range byID {
		if _, isOrig := Original39SkillDescriptions[id]; !isOrig {
			if !requiredCandidates[id] {
				return fmt.Errorf("%w: candidate %q is not authorized for admission under %s discovery policy",
					ErrCorpusMismatch, id, policyVersion)
			}
		}
	}

	for req := range requiredCandidates {
		cand, ok := byID[req]
		if !ok {
			return fmt.Errorf("%w: missing required candidate skill %q", ErrCorpusMismatch, req)
		}
		if cand.DescriptionBytes <= 0 || cand.DescriptionBytes > V010MaxReservationDescriptionBytes {
			return fmt.Errorf("%w: candidate %q description bytes %d exceeds reservation ceiling of %d (must be in 1..%d)",
				ErrCorpusMismatch, cand.ID, cand.DescriptionBytes, V010MaxReservationDescriptionBytes, V010MaxReservationDescriptionBytes)
		}
		switch req {
		case "svg-language-profile":
			if cand.Description != FrozenSVGSkillDescription {
				return fmt.Errorf("%w: candidate %q description mutated (reservation theft)", ErrCorpusMismatch, cand.ID)
			}
			if cand.BodyBytes <= 0 || cand.BodyBytes > V010MaxSVGFileBytes {
				return fmt.Errorf("%w: candidate %q body bytes %d exceeds SVG file limit of %d (must be in 1..%d)",
					ErrCorpusMismatch, cand.ID, cand.BodyBytes, V010MaxSVGFileBytes, V010MaxSVGFileBytes)
			}
		case "playwright-test-profile":
			if cand.Description != FrozenPlaywrightSkillDescription {
				return fmt.Errorf("%w: candidate %q description mutated (reservation theft)", ErrCorpusMismatch, cand.ID)
			}
		case "web-accessibility-profile":
			if cand.Description != FrozenWebAccessibilitySkillDescription {
				return fmt.Errorf("%w: candidate %q description mutated (reservation theft)", ErrCorpusMismatch, cand.ID)
			}
		case "vite-build-profile":
			if cand.Description != FrozenViteSkillDescription {
				return fmt.Errorf("%w: candidate %q description mutated (reservation theft)", ErrCorpusMismatch, cand.ID)
			}
		case "npm-package-manager-profile":
			if cand.Description != FrozenNPMSkillDescription {
				return fmt.Errorf("%w: candidate %q description mutated (reservation theft)", ErrCorpusMismatch, cand.ID)
			}
		}
	}

	if totalBytes > V010BrowserRuntimeAdmissionCeiling {
		return fmt.Errorf("%w: total description bytes %d exceeds current browser runtime admission ceiling of %d",
			ErrCorpusMismatch, totalBytes, V010BrowserRuntimeAdmissionCeiling)
	}
	if totalBytes > V010OverallFutureCeiling {
		return fmt.Errorf("%w: total description bytes %d exceeds overall future ceiling of %d",
			ErrCorpusMismatch, totalBytes, V010OverallFutureCeiling)
	}

	return nil
}
