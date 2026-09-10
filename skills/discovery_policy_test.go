package skills

import (
	"fmt"
	"strings"
	"testing"
	"unicode/utf8"
)

func TestDiscoveryPolicyConstants(t *testing.T) {
	if DiscoveryPolicyVersionV010 != "v0.10" {
		t.Fatalf("DiscoveryPolicyVersionV010 = %q, want v0.10", DiscoveryPolicyVersionV010)
	}
	if DiscoveryPolicyVersionV010BrowserUI != "v0.10-browser-ui" {
		t.Fatalf("DiscoveryPolicyVersionV010BrowserUI = %q, want v0.10-browser-ui", DiscoveryPolicyVersionV010BrowserUI)
	}
	if DiscoveryPolicyVersionV010Toolchain != "v0.10-toolchain" {
		t.Fatalf("DiscoveryPolicyVersionV010Toolchain = %q, want v0.10-toolchain", DiscoveryPolicyVersionV010Toolchain)
	}
	if DiscoveryPolicyVersionV010BrowserRuntime != "v0.10-browser-runtime" {
		t.Fatalf("DiscoveryPolicyVersionV010BrowserRuntime = %q, want v0.10-browser-runtime", DiscoveryPolicyVersionV010BrowserRuntime)
	}
	if DiscoveryPolicyVersion != "v0.10-browser-runtime" {
		t.Fatalf("DiscoveryPolicyVersion = %q, want v0.10-browser-runtime", DiscoveryPolicyVersion)
	}
	if HistoricalSkillCount != 39 {
		t.Fatalf("HistoricalSkillCount = %d, want 39", HistoricalSkillCount)
	}
	if HistoricalDescriptionBytes != 9504 {
		t.Fatalf("HistoricalDescriptionBytes = %d, want 9504", HistoricalDescriptionBytes)
	}
	if HistoricalDescriptionCharacters != 9492 {
		t.Fatalf("HistoricalDescriptionCharacters = %d, want 9492", HistoricalDescriptionCharacters)
	}
	if HistoricalGlobalDescriptionLimit != 9527 || GlobalDescriptionLimit != 9527 {
		t.Fatalf("HistoricalGlobalDescriptionLimit = %d, want 9527", HistoricalGlobalDescriptionLimit)
	}
	if V010MaxReservationDescriptionBytes != 330 {
		t.Fatalf("V010MaxReservationDescriptionBytes = %d, want 330", V010MaxReservationDescriptionBytes)
	}
	if V010CurrentSVGAdmissionCeiling != 9857 {
		t.Fatalf("V010CurrentSVGAdmissionCeiling = %d, want 9857", V010CurrentSVGAdmissionCeiling)
	}
	if V010BrowserUIAdmissionCeiling != 10517 {
		t.Fatalf("V010BrowserUIAdmissionCeiling = %d, want 10517", V010BrowserUIAdmissionCeiling)
	}
	if V010CurrentBrowserUIAdmissionCeiling != 10517 {
		t.Fatalf("V010CurrentBrowserUIAdmissionCeiling = %d, want 10517", V010CurrentBrowserUIAdmissionCeiling)
	}
	if V010ToolchainAdmissionCeiling != 11177 {
		t.Fatalf("V010ToolchainAdmissionCeiling = %d, want 11177", V010ToolchainAdmissionCeiling)
	}
	if V010CurrentToolchainAdmissionCeiling != 11177 {
		t.Fatalf("V010CurrentToolchainAdmissionCeiling = %d, want 11177", V010CurrentToolchainAdmissionCeiling)
	}
	if V010BrowserRuntimeAdmissionCeiling != 11507 {
		t.Fatalf("V010BrowserRuntimeAdmissionCeiling = %d, want 11507", V010BrowserRuntimeAdmissionCeiling)
	}
	if V010CurrentBrowserRuntimeAdmissionCeiling != 11507 {
		t.Fatalf("V010CurrentBrowserRuntimeAdmissionCeiling = %d, want 11507", V010CurrentBrowserRuntimeAdmissionCeiling)
	}
	if V010OverallFutureCeiling != 11507 {
		t.Fatalf("V010OverallFutureCeiling = %d, want 11507", V010OverallFutureCeiling)
	}
	if V010MaxSVGFileBytes != 20480 {
		t.Fatalf("V010MaxSVGFileBytes = %d, want 20480", V010MaxSVGFileBytes)
	}
	if V010CurrentAdmittedCandidate != "svg-language-profile" {
		t.Fatalf("V010CurrentAdmittedCandidate = %q, want svg-language-profile", V010CurrentAdmittedCandidate)
	}
	if V010AdmittedSkillCount != 40 {
		t.Fatalf("V010AdmittedSkillCount = %d, want 40", V010AdmittedSkillCount)
	}
	if V010BrowserUIAdmittedSkillCount != 42 {
		t.Fatalf("V010BrowserUIAdmittedSkillCount = %d, want 42", V010BrowserUIAdmittedSkillCount)
	}
	if V010ToolchainAdmittedSkillCount != 44 {
		t.Fatalf("V010ToolchainAdmittedSkillCount = %d, want 44", V010ToolchainAdmittedSkillCount)
	}
	if V010BrowserRuntimeAdmittedSkillCount != 45 {
		t.Fatalf("V010BrowserRuntimeAdmittedSkillCount = %d, want 45", V010BrowserRuntimeAdmittedSkillCount)
	}
	if len([]byte(FrozenSVGSkillDescription)) != 241 || !strings.HasPrefix(FrozenSVGSkillDescription, "Use when ") {
		t.Fatalf("FrozenSVGSkillDescription invalid length or prefix")
	}
	if len([]byte(FrozenPlaywrightSkillDescription)) != 266 || !strings.HasPrefix(FrozenPlaywrightSkillDescription, "Use when ") {
		t.Fatalf("FrozenPlaywrightSkillDescription invalid length or prefix")
	}
	if len([]byte(FrozenWebAccessibilitySkillDescription)) != 262 || !strings.HasPrefix(FrozenWebAccessibilitySkillDescription, "Use when ") {
		t.Fatalf("FrozenWebAccessibilitySkillDescription invalid length or prefix")
	}
	if len([]byte(FrozenViteSkillDescription)) != 223 || !strings.HasPrefix(FrozenViteSkillDescription, "Use when ") {
		t.Fatalf("FrozenViteSkillDescription invalid length or prefix")
	}
	if len([]byte(FrozenNPMSkillDescription)) != 323 || !strings.HasPrefix(FrozenNPMSkillDescription, "Use when ") {
		t.Fatalf("FrozenNPMSkillDescription invalid length or prefix")
	}

	expectedCandidates := []string{
		"svg-language-profile",
		"playwright-test-profile",
		"web-accessibility-profile",
		"browser-runtime-profile",
		"npm-package-manager-profile",
		"vite-build-profile",
	}
	if len(V010EligibleCandidates) != len(expectedCandidates) {
		t.Fatalf("V010EligibleCandidates len = %d, want %d", len(V010EligibleCandidates), len(expectedCandidates))
	}
	for index, expected := range expectedCandidates {
		if V010EligibleCandidates[index] != expected {
			t.Fatalf("V010EligibleCandidates[%d] = %q, want %q", index, V010EligibleCandidates[index], expected)
		}
	}

	expectedAdmitted := []string{
		"svg-language-profile",
		"playwright-test-profile",
		"web-accessibility-profile",
	}
	if len(V010BrowserUIAdmittedCandidates) != len(expectedAdmitted) {
		t.Fatalf("V010BrowserUIAdmittedCandidates len = %d, want %d", len(V010BrowserUIAdmittedCandidates), len(expectedAdmitted))
	}
	for index, expected := range expectedAdmitted {
		if V010BrowserUIAdmittedCandidates[index] != expected {
			t.Fatalf("V010BrowserUIAdmittedCandidates[%d] = %q, want %q", index, V010BrowserUIAdmittedCandidates[index], expected)
		}
	}

	expectedToolchainAdmitted := []string{
		"svg-language-profile",
		"playwright-test-profile",
		"web-accessibility-profile",
		"vite-build-profile",
		"npm-package-manager-profile",
	}
	if len(V010ToolchainAdmittedCandidates) != len(expectedToolchainAdmitted) {
		t.Fatalf("V010ToolchainAdmittedCandidates len = %d, want %d", len(V010ToolchainAdmittedCandidates), len(expectedToolchainAdmitted))
	}
	for index, expected := range expectedToolchainAdmitted {
		if V010ToolchainAdmittedCandidates[index] != expected {
			t.Fatalf("V010ToolchainAdmittedCandidates[%d] = %q, want %q", index, V010ToolchainAdmittedCandidates[index], expected)
		}
	}

	expectedBrowserRuntimeAdmitted := []string{
		"svg-language-profile",
		"playwright-test-profile",
		"web-accessibility-profile",
		"vite-build-profile",
		"npm-package-manager-profile",
		"browser-runtime-profile",
	}
	if len(V010BrowserRuntimeAdmittedCandidates) != len(expectedBrowserRuntimeAdmitted) {
		t.Fatalf("V010BrowserRuntimeAdmittedCandidates len = %d, want %d", len(V010BrowserRuntimeAdmittedCandidates), len(expectedBrowserRuntimeAdmitted))
	}
	for index, expected := range expectedBrowserRuntimeAdmitted {
		if V010BrowserRuntimeAdmittedCandidates[index] != expected {
			t.Fatalf("V010BrowserRuntimeAdmittedCandidates[%d] = %q, want %q", index, V010BrowserRuntimeAdmittedCandidates[index], expected)
		}
	}
}

func TestOriginal39FrozenDigestAndInvariants(t *testing.T) {
	if len(Original39SkillDescriptions) != 39 {
		t.Fatalf("Original39SkillDescriptions len = %d, want 39", len(Original39SkillDescriptions))
	}
	var totalBytes, totalChars int64
	for name, desc := range Original39SkillDescriptions {
		if !strings.HasPrefix(desc, "Use when ") {
			t.Fatalf("description for %q does not begin with 'Use when '", name)
		}
		totalBytes += int64(len([]byte(desc)))
		totalChars += int64(utf8.RuneCountInString(desc))
	}
	if totalBytes != 9504 {
		t.Fatalf("total description bytes = %d, want 9504", totalBytes)
	}
	if totalChars != 9492 {
		t.Fatalf("total description characters = %d, want 9492", totalChars)
	}
	digest := ComputeOriginal39Digest(Original39SkillDescriptions)
	if digest != FrozenOriginal39Digest {
		t.Fatalf("computed digest = %q, want frozen digest %q", digest, FrozenOriginal39Digest)
	}
	if FrozenOriginal39Digest != "f9255d38eadff7b2bfc5ab13cd1722b8d98ac1ea974d8220475ff7067a1e8cc7" {
		t.Fatalf("frozen digest constant = %q", FrozenOriginal39Digest)
	}
}

func baselineSkillMetadataList() []SkillMetadata {
	list := make([]SkillMetadata, 0, len(Original39SkillDescriptions))
	for name, desc := range Original39SkillDescriptions {
		list = append(list, SkillMetadata{
			ID:                    name,
			Description:           desc,
			DescriptionBytes:      int64(len([]byte(desc))),
			DescriptionCharacters: int64(utf8.RuneCountInString(desc)),
			BodyBytes:             1000,
			BodyCharacters:        1000,
			BodySHA256:            "0000000000000000000000000000000000000000000000000000000000000000",
			CanonicalPath:         name + "/SKILL.md",
			Lines:                 50,
		})
	}
	return list
}

func makeCandidateMetadata(id, desc string, bodyBytes int64) SkillMetadata {
	return SkillMetadata{
		ID:                    id,
		Description:           desc,
		DescriptionBytes:      int64(len([]byte(desc))),
		DescriptionCharacters: int64(utf8.RuneCountInString(desc)),
		BodyBytes:             bodyBytes,
		BodyCharacters:        bodyBytes,
		BodySHA256:            "abcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd",
		CanonicalPath:         id + "/SKILL.md",
		Lines:                 100,
	}
}

func makeDescriptionWithBytes(prefix string, targetBytes int) string {
	needed := targetBytes - len([]byte(prefix))
	if needed < 0 {
		panic("prefix longer than target bytes")
	}
	return prefix + strings.Repeat("x", needed)
}

func TestValidateDiscoveryPolicyExactBoundaries(t *testing.T) {
	// Baseline 39 skills: exactly 9504 description bytes, 9492 chars.
	baseline := baselineSkillMetadataList()
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010, baseline); err != nil {
		t.Fatalf("baseline validation error: %v", err)
	}

	// 40 skills with svg-language-profile at exact reservation boundary of 330 description bytes and 20480 file bytes.
	desc330 := makeDescriptionWithBytes("Use when SVG syntax is needed ", 330)
	candidateExact := makeCandidateMetadata("svg-language-profile", desc330, 20480)
	skills40 := append(baselineSkillMetadataList(), candidateExact)
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010, skills40); err != nil {
		t.Fatalf("exact 330/20480 candidate validation error: %v", err)
	}

	// Exact current SVG admission ceiling: 9857 description bytes (9504 baseline + 353 bytes... but reservation limit is 330)
	// Notice: 9504 baseline + 330 = 9834 <= 9857.
	// If candidate is exactly 330 bytes, total is 9834 <= 9857.
}

func TestValidateDiscoveryPolicyOneOverBoundaries(t *testing.T) {
	// 1. One-over description reservation: 331 bytes
	desc331 := makeDescriptionWithBytes("Use when SVG syntax is needed ", 331)
	skills40OneOverDesc := append(baselineSkillMetadataList(), makeCandidateMetadata("svg-language-profile", desc331, 1000))
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010, skills40OneOverDesc); err == nil {
		t.Fatal("expected failure for 331-byte description (reservation limit is 330)")
	}

	// 2. One-over file size: 20481 bytes
	desc300 := makeDescriptionWithBytes("Use when SVG syntax is needed ", 300)
	skills40OneOverFile := append(baselineSkillMetadataList(), makeCandidateMetadata("svg-language-profile", desc300, 20481))
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010, skills40OneOverFile); err == nil {
		t.Fatal("expected failure for 20481-byte SVG file (limit is 20480)")
	}

	// 3. Count 41 (one over admitted count 40)
	cand2 := makeCandidateMetadata("playwright-test-profile", "Use when Playwright applies.", 1000)
	skills41 := append(baselineSkillMetadataList(),
		makeCandidateMetadata("svg-language-profile", desc300, 1000),
		cand2,
	)
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010, skills41); err == nil {
		t.Fatal("expected failure for 41 skills (limit is 40)")
	}

	// 4. Count 38 (under 39)
	skills38 := baselineSkillMetadataList()[:38]
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010, skills38); err == nil {
		t.Fatal("expected failure for 38 skills (must be 39 or 40)")
	}
}

func TestValidateDiscoveryPolicyMultibyteEnforcement(t *testing.T) {
	// Build multibyte description containing 'é' (2 bytes each)
	// "Use when " = 9 bytes (9 runes)
	// 160 * 'é' = 320 bytes (160 runes)
	// 'x' = 1 byte (1 rune)
	// Total bytes: 9 + 320 + 1 = 330 bytes.
	// Total runes: 9 + 160 + 1 = 170 runes.
	multibyte330 := "Use when " + strings.Repeat("é", 160) + "x"
	if len([]byte(multibyte330)) != 330 || utf8.RuneCountInString(multibyte330) != 170 {
		t.Fatalf("multibyte330 setup invalid: bytes=%d runes=%d", len([]byte(multibyte330)), utf8.RuneCountInString(multibyte330))
	}
	skillsMultibyteExact := append(baselineSkillMetadataList(), makeCandidateMetadata("svg-language-profile", multibyte330, 1000))
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010, skillsMultibyteExact); err != nil {
		t.Fatalf("multibyte 330-byte description should pass: %v", err)
	}

	// Multibyte 331 bytes (one over byte limit, even though character count is only 171)
	multibyte331 := "Use when " + strings.Repeat("é", 160) + "xx"
	if len([]byte(multibyte331)) != 331 {
		t.Fatalf("multibyte331 setup invalid: bytes=%d", len([]byte(multibyte331)))
	}
	skillsMultibyteOver := append(baselineSkillMetadataList(), makeCandidateMetadata("svg-language-profile", multibyte331, 1000))
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010, skillsMultibyteOver); err == nil {
		t.Fatal("multibyte 331-byte description must fail even with low rune count")
	}

	// Mismatched DescriptionBytes field vs actual len([]byte)
	tamperedBytes := makeCandidateMetadata("svg-language-profile", multibyte330, 1000)
	tamperedBytes.DescriptionBytes = int64(utf8.RuneCountInString(multibyte330)) // tampered to 170
	skillsTampered := append(baselineSkillMetadataList(), tamperedBytes)
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010, skillsTampered); err == nil {
		t.Fatal("tampered DescriptionBytes field must fail")
	}
}

func TestValidateDiscoveryPolicyMalformed(t *testing.T) {
	// Empty ID
	badID := baselineSkillMetadataList()
	badID[0].ID = ""
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010, badID); err == nil {
		t.Fatal("empty ID must fail")
	}

	// Empty Description
	badDesc := baselineSkillMetadataList()
	badDesc[0].Description = ""
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010, badDesc); err == nil {
		t.Fatal("empty Description must fail")
	}

	// Description does not start with "Use when "
	badPrefix := baselineSkillMetadataList()
	badPrefix[0].Description = "Invalid prefix description for skill."
	badPrefix[0].DescriptionBytes = int64(len([]byte(badPrefix[0].Description)))
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010, badPrefix); err == nil {
		t.Fatal("description without 'Use when ' prefix must fail")
	}
}

func TestValidateDiscoveryPolicyMissingSkills(t *testing.T) {
	// 39 skills, but one of the original 39 is replaced by an imposter
	imposter := baselineSkillMetadataList()
	imposter[0] = makeCandidateMetadata("svg-language-profile", "Use when SVG applies.", 1000)
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010, imposter); err == nil {
		t.Fatal("omitting an original 39 skill in 39-count corpus must fail")
	}

	// 40 skills, but missing one original 39 skill and having two candidates
	missingOriginal40 := baselineSkillMetadataList()[:38]
	missingOriginal40 = append(missingOriginal40,
		makeCandidateMetadata("svg-language-profile", "Use when SVG applies.", 1000),
		makeCandidateMetadata("playwright-test-profile", "Use when Playwright applies.", 1000),
	)
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010, missingOriginal40); err == nil {
		t.Fatal("omitting an original 39 skill in 40-count corpus must fail")
	}
}

func TestValidateDiscoveryPolicyDuplicateSkills(t *testing.T) {
	// Duplicate original skill in list
	dupes := baselineSkillMetadataList()
	dupes[1] = dupes[0]
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010, dupes); err == nil {
		t.Fatal("duplicate skill ID must fail")
	}
}

func TestValidateDiscoveryPolicyReservationTheft(t *testing.T) {
	// 1. Mutate an original 39 skill description (shorten it to free up bytes)
	theftShorten := baselineSkillMetadataList()
	for i := range theftShorten {
		if theftShorten[i].ID == "agentic-praxis-grimoire-workflow" {
			theftShorten[i].Description = "Use when APG routing is needed."
			theftShorten[i].DescriptionBytes = int64(len([]byte(theftShorten[i].Description)))
			theftShorten[i].DescriptionCharacters = int64(utf8.RuneCountInString(theftShorten[i].Description))
			break
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010, theftShorten); err == nil {
		t.Fatal("mutating an original 39 description must fail as reservation theft")
	}

	// 2. Unauthorized candidate admission: playwright-test-profile at count 40
	playwrightAt40 := append(baselineSkillMetadataList(),
		makeCandidateMetadata("playwright-test-profile", "Use when Playwright applies.", 1000),
	)
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010, playwrightAt40); err == nil {
		t.Fatal("admitting playwright-test-profile at count 40 must fail (only svg-language-profile authorized)")
	}

	// 3. Unauthorized non-eligible identity at count 40
	unauthorizedAt40 := append(baselineSkillMetadataList(),
		makeCandidateMetadata("unregistered-profile", "Use when unregistered applies.", 1000),
	)
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010, unauthorizedAt40); err == nil {
		t.Fatal("admitting unregistered-profile must fail")
	}

	// 4. Candidate exceeding 330 bytes even if total bytes under ceiling
	theftOverReserved := append(baselineSkillMetadataList(),
		makeCandidateMetadata("svg-language-profile", makeDescriptionWithBytes("Use when SVG applies ", 335), 1000),
	)
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010, theftOverReserved); err == nil {
		t.Fatal("candidate exceeding 330 bytes reservation must fail")
	}
}

func TestValidateDiscoveryPolicyUnknownPolicy(t *testing.T) {
	baseline := baselineSkillMetadataList()
	for _, unknownPolicy := range []string{"v0.9", "v0.11", "v1.0", "unknown", ""} {
		t.Run(fmt.Sprintf("policy_%s", unknownPolicy), func(t *testing.T) {
			if err := ValidateDiscoveryPolicy(unknownPolicy, baseline); err == nil {
				t.Fatalf("policy %q must fail as unknown policy", unknownPolicy)
			}
		})
	}
}

func TestValidateDiscoveryPolicyMeasurements(t *testing.T) {
	// 1. Negative / zero BodyBytes on candidate
	zeroBodyCandidate := append(baselineSkillMetadataList(),
		makeCandidateMetadata("svg-language-profile", "Use when SVG applies.", 0),
	)
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010, zeroBodyCandidate); err == nil {
		t.Fatal("candidate with zero BodyBytes must fail")
	}

	negativeBodyCandidate := append(baselineSkillMetadataList(),
		makeCandidateMetadata("svg-language-profile", "Use when SVG applies.", -5),
	)
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010, negativeBodyCandidate); err == nil {
		t.Fatal("candidate with negative BodyBytes must fail")
	}

	// 2. Negative / zero BodyBytes on original skill
	badBodyOriginal := baselineSkillMetadataList()
	badBodyOriginal[0].BodyBytes = -1
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010, badBodyOriginal); err == nil {
		t.Fatal("original skill with negative BodyBytes must fail")
	}

	// 3. Negative / zero BodyCharacters
	badBodyChars := baselineSkillMetadataList()
	badBodyChars[0].BodyCharacters = 0
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010, badBodyChars); err == nil {
		t.Fatal("skill with zero BodyCharacters must fail")
	}

	// 4. Negative lines
	badLines := baselineSkillMetadataList()
	badLines[0].Lines = 0
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010, badLines); err == nil {
		t.Fatal("skill with zero Lines must fail")
	}

	// 5. Invalid body SHA256 digest length
	badSHA := baselineSkillMetadataList()
	badSHA[0].BodySHA256 = "short"
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010, badSHA); err == nil {
		t.Fatal("skill with invalid BodySHA256 must fail")
	}

	// 6. Character count mismatch against actual unicode runes
	badRuneCount := baselineSkillMetadataList()
	badRuneCount[0].DescriptionCharacters = badRuneCount[0].DescriptionCharacters + 1
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010, badRuneCount); err == nil {
		t.Fatal("skill with DescriptionCharacters mismatch must fail")
	}
}

func browserUIBaseline42() []SkillMetadata {
	list := baselineSkillMetadataList()
	list = append(list,
		makeCandidateMetadata("svg-language-profile", FrozenSVGSkillDescription, 20480),
		makeCandidateMetadata("playwright-test-profile", "Use when Playwright end-to-end browser tests, fixtures, locators, tracing, network mocking, or page interactions are evaluated.", 35000),
		makeCandidateMetadata("web-accessibility-profile", "Use when accessibility auditing, ARIA attributes, semantic landmarks, focus management, screen-reader semantics, or WCAG compliance are evaluated.", 40000),
	)
	return list
}

func TestValidateDiscoveryPolicyV010BrowserUIExactBoundaries(t *testing.T) {
	baseline42 := browserUIBaseline42()
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserUI, baseline42); err != nil {
		t.Fatalf("valid 42-skill baseline under %s must pass: %v", DiscoveryPolicyVersionV010BrowserUI, err)
	}

	// SVG body at exactly 20480 bytes passes
	skillsExactSVG := browserUIBaseline42()
	for i := range skillsExactSVG {
		if skillsExactSVG[i].ID == "svg-language-profile" {
			skillsExactSVG[i].BodyBytes = 20480
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserUI, skillsExactSVG); err != nil {
		t.Fatalf("exact 20480 SVG body bytes must pass: %v", err)
	}

	// Playwright at exact 330 description bytes passes
	skillsExactPlaywright := browserUIBaseline42()
	for i := range skillsExactPlaywright {
		if skillsExactPlaywright[i].ID == "playwright-test-profile" {
			desc := makeDescriptionWithBytes("Use when Playwright testing is needed ", 330)
			skillsExactPlaywright[i].Description = desc
			skillsExactPlaywright[i].DescriptionBytes = int64(len([]byte(desc)))
			skillsExactPlaywright[i].DescriptionCharacters = int64(utf8.RuneCountInString(desc))
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserUI, skillsExactPlaywright); err != nil {
		t.Fatalf("exact 330 description bytes for Playwright must pass: %v", err)
	}

	// Web-accessibility at exact 330 description bytes passes
	skillsExactA11y := browserUIBaseline42()
	for i := range skillsExactA11y {
		if skillsExactA11y[i].ID == "web-accessibility-profile" {
			desc := makeDescriptionWithBytes("Use when web accessibility is needed ", 330)
			skillsExactA11y[i].Description = desc
			skillsExactA11y[i].DescriptionBytes = int64(len([]byte(desc)))
			skillsExactA11y[i].DescriptionCharacters = int64(utf8.RuneCountInString(desc))
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserUI, skillsExactA11y); err != nil {
		t.Fatalf("exact 330 description bytes for Web-a11y must pass: %v", err)
	}
}

func TestValidateDiscoveryPolicyV010BrowserUIOneOverBoundaries(t *testing.T) {
	// 1. One-over description reservation: 331 bytes on Playwright
	skillsOverPlaywright := browserUIBaseline42()
	for i := range skillsOverPlaywright {
		if skillsOverPlaywright[i].ID == "playwright-test-profile" {
			desc := makeDescriptionWithBytes("Use when Playwright testing is needed ", 331)
			skillsOverPlaywright[i].Description = desc
			skillsOverPlaywright[i].DescriptionBytes = int64(len([]byte(desc)))
			skillsOverPlaywright[i].DescriptionCharacters = int64(utf8.RuneCountInString(desc))
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserUI, skillsOverPlaywright); err == nil {
		t.Fatal("expected failure for 331-byte description on Playwright")
	}

	// 2. One-over description reservation: 331 bytes on Web-a11y
	skillsOverA11y := browserUIBaseline42()
	for i := range skillsOverA11y {
		if skillsOverA11y[i].ID == "web-accessibility-profile" {
			desc := makeDescriptionWithBytes("Use when web accessibility is needed ", 331)
			skillsOverA11y[i].Description = desc
			skillsOverA11y[i].DescriptionBytes = int64(len([]byte(desc)))
			skillsOverA11y[i].DescriptionCharacters = int64(utf8.RuneCountInString(desc))
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserUI, skillsOverA11y); err == nil {
		t.Fatal("expected failure for 331-byte description on Web-a11y")
	}

	// 3. One-over file size for SVG: 20481 bytes
	skillsOverSVGFile := browserUIBaseline42()
	for i := range skillsOverSVGFile {
		if skillsOverSVGFile[i].ID == "svg-language-profile" {
			skillsOverSVGFile[i].BodyBytes = 20481
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserUI, skillsOverSVGFile); err == nil {
		t.Fatal("expected failure for 20481-byte SVG file (limit is 20480)")
	}

	// 4. Count 41 (missing web-accessibility-profile)
	skills41 := browserUIBaseline42()[:41]
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserUI, skills41); err == nil {
		t.Fatal("expected failure for 41 skills under v0.10-browser-ui (must be exactly 42)")
	}

	// 5. Count 43 (extra candidate)
	candExtra := makeCandidateMetadata("browser-runtime-profile", "Use when browser runtime applies.", 1000)
	skills43 := append(browserUIBaseline42(), candExtra)
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserUI, skills43); err == nil {
		t.Fatal("expected failure for 43 skills under v0.10-browser-ui (must be exactly 42)")
	}

	// 6. Count 40 (only SVG, missing playwright and web-a11y)
	skills40 := browserUIBaseline42()[:40]
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserUI, skills40); err == nil {
		t.Fatal("expected failure for 40 skills under v0.10-browser-ui (must be exactly 42)")
	}

	// 7. Count 39
	skills39 := baselineSkillMetadataList()
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserUI, skills39); err == nil {
		t.Fatal("expected failure for 39 skills under v0.10-browser-ui (must be exactly 42)")
	}
}

func TestValidateDiscoveryPolicyV010BrowserUIMultibyteEnforcement(t *testing.T) {
	// Multibyte 330 bytes description on Playwright: 9 bytes "Use when " + 160 * 2 bytes 'é' + 1 byte 'x' = 330 bytes
	multibyte330 := "Use when " + strings.Repeat("é", 160) + "x"
	skillsMultibyte := browserUIBaseline42()
	for i := range skillsMultibyte {
		if skillsMultibyte[i].ID == "playwright-test-profile" {
			skillsMultibyte[i].Description = multibyte330
			skillsMultibyte[i].DescriptionBytes = int64(len([]byte(multibyte330)))
			skillsMultibyte[i].DescriptionCharacters = int64(utf8.RuneCountInString(multibyte330))
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserUI, skillsMultibyte); err != nil {
		t.Fatalf("multibyte 330-byte candidate description must pass: %v", err)
	}

	// Multibyte 331 bytes description on Playwright
	multibyte331 := "Use when " + strings.Repeat("é", 160) + "xx"
	skillsMultibyteOver := browserUIBaseline42()
	for i := range skillsMultibyteOver {
		if skillsMultibyteOver[i].ID == "playwright-test-profile" {
			skillsMultibyteOver[i].Description = multibyte331
			skillsMultibyteOver[i].DescriptionBytes = int64(len([]byte(multibyte331)))
			skillsMultibyteOver[i].DescriptionCharacters = int64(utf8.RuneCountInString(multibyte331))
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserUI, skillsMultibyteOver); err == nil {
		t.Fatal("multibyte 331-byte description must fail")
	}

	// Tampered DescriptionBytes field
	skillsTampered := browserUIBaseline42()
	for i := range skillsTampered {
		if skillsTampered[i].ID == "playwright-test-profile" {
			skillsTampered[i].Description = multibyte330
			skillsTampered[i].DescriptionBytes = int64(utf8.RuneCountInString(multibyte330)) // tampered to 170
			skillsTampered[i].DescriptionCharacters = int64(utf8.RuneCountInString(multibyte330))
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserUI, skillsTampered); err == nil {
		t.Fatal("tampered DescriptionBytes field must fail")
	}
}

func TestValidateDiscoveryPolicyV010BrowserUISetEqualityAndSubstitution(t *testing.T) {
	// 1. Substitute web-accessibility-profile with browser-runtime-profile (eligible candidate not in current admission)
	subFuture := browserUIBaseline42()
	for i := range subFuture {
		if subFuture[i].ID == "web-accessibility-profile" {
			subFuture[i] = makeCandidateMetadata("browser-runtime-profile", "Use when browser runtime applies.", 1000)
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserUI, subFuture); err == nil {
		t.Fatal("substituting web-accessibility-profile with future candidate browser-runtime-profile must fail")
	}

	// 2. Substitute with npm-package-manager-profile
	subNPM := browserUIBaseline42()
	for i := range subNPM {
		if subNPM[i].ID == "web-accessibility-profile" {
			subNPM[i] = makeCandidateMetadata("npm-package-manager-profile", "Use when npm package manager applies.", 1000)
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserUI, subNPM); err == nil {
		t.Fatal("substituting with npm-package-manager-profile must fail")
	}

	// 3. Substitute with vite-build-profile
	subVite := browserUIBaseline42()
	for i := range subVite {
		if subVite[i].ID == "web-accessibility-profile" {
			subVite[i] = makeCandidateMetadata("vite-build-profile", "Use when vite build applies.", 1000)
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserUI, subVite); err == nil {
		t.Fatal("substituting with vite-build-profile must fail")
	}

	// 4. Substitute with unregistered candidate
	subUnreg := browserUIBaseline42()
	for i := range subUnreg {
		if subUnreg[i].ID == "web-accessibility-profile" {
			subUnreg[i] = makeCandidateMetadata("unregistered-profile", "Use when unregistered applies.", 1000)
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserUI, subUnreg); err == nil {
		t.Fatal("substituting with unregistered candidate must fail")
	}

	// 5. Duplicate candidate ID (two playwright candidates, missing web-accessibility)
	dupeCand := browserUIBaseline42()
	for i := range dupeCand {
		if dupeCand[i].ID == "web-accessibility-profile" {
			dupeCand[i] = dupeCand[i-1] // duplicate playwright
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserUI, dupeCand); err == nil {
		t.Fatal("duplicate candidate ID must fail")
	}

	// 6. Duplicate original skill ID
	dupeOrig := browserUIBaseline42()
	dupeOrig[1] = dupeOrig[0]
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserUI, dupeOrig); err == nil {
		t.Fatal("duplicate original skill ID must fail")
	}
}

func TestValidateDiscoveryPolicyV010BrowserUIFrozenDescriptions(t *testing.T) {
	// 1. Mutate an original 39 skill description
	theftOrig := browserUIBaseline42()
	for i := range theftOrig {
		if theftOrig[i].ID == "agentic-praxis-grimoire-workflow" {
			theftOrig[i].Description = "Use when APG routing is needed."
			theftOrig[i].DescriptionBytes = int64(len([]byte(theftOrig[i].Description)))
			theftOrig[i].DescriptionCharacters = int64(utf8.RuneCountInString(theftOrig[i].Description))
			break
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserUI, theftOrig); err == nil {
		t.Fatal("mutating original 39 skill description under v0.10-browser-ui must fail as reservation theft")
	}

	// 2. Mutate SVG description under v0.10-browser-ui (must be byte-identical to FrozenSVGSkillDescription)
	theftSVG := browserUIBaseline42()
	for i := range theftSVG {
		if theftSVG[i].ID == "svg-language-profile" {
			theftSVG[i].Description = "Use when SVG authoring is needed."
			theftSVG[i].DescriptionBytes = int64(len([]byte(theftSVG[i].Description)))
			theftSVG[i].DescriptionCharacters = int64(utf8.RuneCountInString(theftSVG[i].Description))
			break
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserUI, theftSVG); err == nil {
		t.Fatal("mutating SVG description under v0.10-browser-ui must fail as reservation theft")
	}
}

func TestValidateDiscoveryPolicyV010BrowserUIBodyCeilingExemptionAndSVGLimit(t *testing.T) {
	// Playwright and Web-a11y have body sizes > 20480 (e.g. 50000 bytes) -> MUST PASS!
	skillsLargeNonSVG := browserUIBaseline42()
	for i := range skillsLargeNonSVG {
		if skillsLargeNonSVG[i].ID == "playwright-test-profile" {
			skillsLargeNonSVG[i].BodyBytes = 50000
			skillsLargeNonSVG[i].BodyCharacters = 50000
		}
		if skillsLargeNonSVG[i].ID == "web-accessibility-profile" {
			skillsLargeNonSVG[i].BodyBytes = 60000
			skillsLargeNonSVG[i].BodyCharacters = 60000
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserUI, skillsLargeNonSVG); err != nil {
		t.Fatalf("large body bytes on new non-SVG leaves must pass (exemption from 20480 limit): %v", err)
	}

	// SVG body size > 20480 -> MUST FAIL!
	skillsOverSVG := browserUIBaseline42()
	for i := range skillsOverSVG {
		if skillsOverSVG[i].ID == "svg-language-profile" {
			skillsOverSVG[i].BodyBytes = 20481
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserUI, skillsOverSVG); err == nil {
		t.Fatal("SVG body size > 20480 must fail")
	}

	// Non-positive body bytes on Playwright -> MUST FAIL!
	skillsZeroBody := browserUIBaseline42()
	for i := range skillsZeroBody {
		if skillsZeroBody[i].ID == "playwright-test-profile" {
			skillsZeroBody[i].BodyBytes = 0
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserUI, skillsZeroBody); err == nil {
		t.Fatal("zero body bytes on Playwright must fail")
	}
}

func TestValidateDiscoveryPolicyV010BrowserUIMalformedMetadata(t *testing.T) {
	// Empty ID on candidate
	badID := browserUIBaseline42()
	for i := range badID {
		if badID[i].ID == "playwright-test-profile" {
			badID[i].ID = ""
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserUI, badID); err == nil {
		t.Fatal("empty candidate ID must fail")
	}

	// Empty Description on candidate
	badDesc := browserUIBaseline42()
	for i := range badDesc {
		if badDesc[i].ID == "playwright-test-profile" {
			badDesc[i].Description = ""
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserUI, badDesc); err == nil {
		t.Fatal("empty candidate Description must fail")
	}

	// Candidate description without "Use when " prefix
	badPrefix := browserUIBaseline42()
	for i := range badPrefix {
		if badPrefix[i].ID == "playwright-test-profile" {
			badPrefix[i].Description = "Invalid prefix description."
			badPrefix[i].DescriptionBytes = int64(len([]byte(badPrefix[i].Description)))
			badPrefix[i].DescriptionCharacters = int64(utf8.RuneCountInString(badPrefix[i].Description))
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserUI, badPrefix); err == nil {
		t.Fatal("candidate description without 'Use when ' must fail")
	}
}

func TestValidateDiscoveryPolicyV010BrowserUITotalCeiling(t *testing.T) {
	skills := browserUIBaseline42()
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserUI, skills); err != nil {
		t.Fatalf("baseline total description bytes should be under ceiling: %v", err)
	}

	// Verify that the ceiling constants are correctly sized
	if V010BrowserUIAdmissionCeiling != 10517 {
		t.Fatalf("V010BrowserUIAdmissionCeiling = %d, want 10517", V010BrowserUIAdmissionCeiling)
	}
	if V010OverallFutureCeiling != 11507 {
		t.Fatalf("V010OverallFutureCeiling = %d, want 11507", V010OverallFutureCeiling)
	}
}

func toolchainBaseline44() []SkillMetadata {
	list := baselineSkillMetadataList()
	list = append(list,
		makeCandidateMetadata("svg-language-profile", FrozenSVGSkillDescription, 20480),
		makeCandidateMetadata("playwright-test-profile", FrozenPlaywrightSkillDescription, 35000),
		makeCandidateMetadata("web-accessibility-profile", FrozenWebAccessibilitySkillDescription, 40000),
		makeCandidateMetadata("vite-build-profile", "Use when Vite build configuration, dev server, plugin pipeline, bundling, or asset optimization decisions are evaluated.", 25000),
		makeCandidateMetadata("npm-package-manager-profile", "Use when npm package manager configuration, workspaces, lockfiles, lifecycle scripts, or dependency resolution decisions are evaluated.", 30000),
	)
	return list
}

func TestValidateDiscoveryPolicyV010ToolchainExactBoundaries(t *testing.T) {
	baseline44 := toolchainBaseline44()
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010Toolchain, baseline44); err != nil {
		t.Fatalf("valid 44-skill baseline under %s must pass: %v", DiscoveryPolicyVersionV010Toolchain, err)
	}

	// SVG body at exactly 20480 bytes passes
	skillsExactSVG := toolchainBaseline44()
	for i := range skillsExactSVG {
		if skillsExactSVG[i].ID == "svg-language-profile" {
			skillsExactSVG[i].BodyBytes = 20480
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010Toolchain, skillsExactSVG); err != nil {
		t.Fatalf("exact 20480 SVG body bytes must pass: %v", err)
	}

	// Vite at exact 330 description bytes passes
	skillsExactVite := toolchainBaseline44()
	for i := range skillsExactVite {
		if skillsExactVite[i].ID == "vite-build-profile" {
			desc := makeDescriptionWithBytes("Use when Vite build is needed ", 330)
			skillsExactVite[i].Description = desc
			skillsExactVite[i].DescriptionBytes = int64(len([]byte(desc)))
			skillsExactVite[i].DescriptionCharacters = int64(utf8.RuneCountInString(desc))
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010Toolchain, skillsExactVite); err != nil {
		t.Fatalf("exact 330 description bytes for Vite must pass: %v", err)
	}

	// npm at exact 330 description bytes passes
	skillsExactNPM := toolchainBaseline44()
	for i := range skillsExactNPM {
		if skillsExactNPM[i].ID == "npm-package-manager-profile" {
			desc := makeDescriptionWithBytes("Use when npm package manager is needed ", 330)
			skillsExactNPM[i].Description = desc
			skillsExactNPM[i].DescriptionBytes = int64(len([]byte(desc)))
			skillsExactNPM[i].DescriptionCharacters = int64(utf8.RuneCountInString(desc))
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010Toolchain, skillsExactNPM); err != nil {
		t.Fatalf("exact 330 description bytes for npm must pass: %v", err)
	}
}

func TestValidateDiscoveryPolicyV010ToolchainOneOverBoundaries(t *testing.T) {
	// 1. One-over description reservation: 331 bytes on Vite
	skillsOverVite := toolchainBaseline44()
	for i := range skillsOverVite {
		if skillsOverVite[i].ID == "vite-build-profile" {
			desc := makeDescriptionWithBytes("Use when Vite build is needed ", 331)
			skillsOverVite[i].Description = desc
			skillsOverVite[i].DescriptionBytes = int64(len([]byte(desc)))
			skillsOverVite[i].DescriptionCharacters = int64(utf8.RuneCountInString(desc))
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010Toolchain, skillsOverVite); err == nil {
		t.Fatal("expected failure for 331-byte description on Vite")
	}

	// 2. One-over description reservation: 331 bytes on npm
	skillsOverNPM := toolchainBaseline44()
	for i := range skillsOverNPM {
		if skillsOverNPM[i].ID == "npm-package-manager-profile" {
			desc := makeDescriptionWithBytes("Use when npm package manager is needed ", 331)
			skillsOverNPM[i].Description = desc
			skillsOverNPM[i].DescriptionBytes = int64(len([]byte(desc)))
			skillsOverNPM[i].DescriptionCharacters = int64(utf8.RuneCountInString(desc))
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010Toolchain, skillsOverNPM); err == nil {
		t.Fatal("expected failure for 331-byte description on npm")
	}

	// 3. One-over file size for SVG: 20481 bytes
	skillsOverSVGFile := toolchainBaseline44()
	for i := range skillsOverSVGFile {
		if skillsOverSVGFile[i].ID == "svg-language-profile" {
			skillsOverSVGFile[i].BodyBytes = 20481
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010Toolchain, skillsOverSVGFile); err == nil {
		t.Fatal("expected failure for 20481-byte SVG file (limit is 20480)")
	}

	// 4. Count 43 (missing npm-package-manager-profile)
	skills43 := toolchainBaseline44()[:43]
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010Toolchain, skills43); err == nil {
		t.Fatal("expected failure for 43 skills under v0.10-toolchain (must be exactly 44)")
	}

	// 5. Count 45 (extra candidate: browser-runtime-profile)
	candExtra := makeCandidateMetadata("browser-runtime-profile", "Use when browser runtime applies.", 1000)
	skills45 := append(toolchainBaseline44(), candExtra)
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010Toolchain, skills45); err == nil {
		t.Fatal("expected failure for 45 skills under v0.10-toolchain (must be exactly 44)")
	}

	// 6. Count 42 (historical browser-ui count)
	skills42 := toolchainBaseline44()[:42]
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010Toolchain, skills42); err == nil {
		t.Fatal("expected failure for 42 skills under v0.10-toolchain (must be exactly 44)")
	}

	// 7. Count 40 (historical v0.10 count)
	skills40 := toolchainBaseline44()[:40]
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010Toolchain, skills40); err == nil {
		t.Fatal("expected failure for 40 skills under v0.10-toolchain (must be exactly 44)")
	}

	// 8. Count 39 (historical baseline count)
	skills39 := baselineSkillMetadataList()
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010Toolchain, skills39); err == nil {
		t.Fatal("expected failure for 39 skills under v0.10-toolchain (must be exactly 44)")
	}
}

func TestValidateDiscoveryPolicyV010ToolchainMultibyteEnforcement(t *testing.T) {
	// Multibyte 330 bytes description on Vite: 9 bytes "Use when " + 160 * 2 bytes 'é' + 1 byte 'x' = 330 bytes
	multibyte330 := "Use when " + strings.Repeat("é", 160) + "x"
	skillsMultibyte := toolchainBaseline44()
	for i := range skillsMultibyte {
		if skillsMultibyte[i].ID == "vite-build-profile" {
			skillsMultibyte[i].Description = multibyte330
			skillsMultibyte[i].DescriptionBytes = int64(len([]byte(multibyte330)))
			skillsMultibyte[i].DescriptionCharacters = int64(utf8.RuneCountInString(multibyte330))
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010Toolchain, skillsMultibyte); err != nil {
		t.Fatalf("multibyte 330-byte candidate description must pass: %v", err)
	}

	// Multibyte 331 bytes description on Vite
	multibyte331 := "Use when " + strings.Repeat("é", 160) + "xx"
	skillsMultibyteOver := toolchainBaseline44()
	for i := range skillsMultibyteOver {
		if skillsMultibyteOver[i].ID == "vite-build-profile" {
			skillsMultibyteOver[i].Description = multibyte331
			skillsMultibyteOver[i].DescriptionBytes = int64(len([]byte(multibyte331)))
			skillsMultibyteOver[i].DescriptionCharacters = int64(utf8.RuneCountInString(multibyte331))
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010Toolchain, skillsMultibyteOver); err == nil {
		t.Fatal("multibyte 331-byte description must fail")
	}

	// Multibyte 330 bytes description on npm
	skillsMultibyteNPM := toolchainBaseline44()
	for i := range skillsMultibyteNPM {
		if skillsMultibyteNPM[i].ID == "npm-package-manager-profile" {
			skillsMultibyteNPM[i].Description = multibyte330
			skillsMultibyteNPM[i].DescriptionBytes = int64(len([]byte(multibyte330)))
			skillsMultibyteNPM[i].DescriptionCharacters = int64(utf8.RuneCountInString(multibyte330))
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010Toolchain, skillsMultibyteNPM); err != nil {
		t.Fatalf("multibyte 330-byte npm description must pass: %v", err)
	}

	// Multibyte 331 bytes description on npm
	skillsMultibyteNPMOver := toolchainBaseline44()
	for i := range skillsMultibyteNPMOver {
		if skillsMultibyteNPMOver[i].ID == "npm-package-manager-profile" {
			skillsMultibyteNPMOver[i].Description = multibyte331
			skillsMultibyteNPMOver[i].DescriptionBytes = int64(len([]byte(multibyte331)))
			skillsMultibyteNPMOver[i].DescriptionCharacters = int64(utf8.RuneCountInString(multibyte331))
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010Toolchain, skillsMultibyteNPMOver); err == nil {
		t.Fatal("multibyte 331-byte npm description must fail")
	}

	// Tampered DescriptionBytes field
	skillsTampered := toolchainBaseline44()
	for i := range skillsTampered {
		if skillsTampered[i].ID == "vite-build-profile" {
			skillsTampered[i].Description = multibyte330
			skillsTampered[i].DescriptionBytes = int64(utf8.RuneCountInString(multibyte330)) // tampered to 170
			skillsTampered[i].DescriptionCharacters = int64(utf8.RuneCountInString(multibyte330))
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010Toolchain, skillsTampered); err == nil {
		t.Fatal("tampered DescriptionBytes field must fail")
	}
}

func TestValidateDiscoveryPolicyV010ToolchainSetEqualityAndSubstitution(t *testing.T) {
	// 1. Substitute npm-package-manager-profile with browser-runtime-profile (only unadmitted candidate!)
	subBR := toolchainBaseline44()
	for i := range subBR {
		if subBR[i].ID == "npm-package-manager-profile" {
			subBR[i] = makeCandidateMetadata("browser-runtime-profile", "Use when browser runtime applies.", 1000)
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010Toolchain, subBR); err == nil {
		t.Fatal("substituting npm-package-manager-profile with unadmitted browser-runtime-profile must fail")
	}

	// 2. Substitute with unregistered candidate
	subUnreg := toolchainBaseline44()
	for i := range subUnreg {
		if subUnreg[i].ID == "npm-package-manager-profile" {
			subUnreg[i] = makeCandidateMetadata("unregistered-profile", "Use when unregistered applies.", 1000)
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010Toolchain, subUnreg); err == nil {
		t.Fatal("substituting with unregistered candidate must fail")
	}

	// 3. Duplicate candidate ID (two vite candidates, missing npm)
	dupeCand := toolchainBaseline44()
	for i := range dupeCand {
		if dupeCand[i].ID == "npm-package-manager-profile" {
			dupeCand[i] = dupeCand[i-1] // duplicate vite
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010Toolchain, dupeCand); err == nil {
		t.Fatal("duplicate candidate ID must fail")
	}

	// 4. Duplicate original skill ID
	dupeOrig := toolchainBaseline44()
	dupeOrig[1] = dupeOrig[0]
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010Toolchain, dupeOrig); err == nil {
		t.Fatal("duplicate original skill ID must fail")
	}
}

func TestValidateDiscoveryPolicyV010ToolchainFrozenDescriptions(t *testing.T) {
	// 1. Mutate an original 39 skill description
	theftOrig := toolchainBaseline44()
	for i := range theftOrig {
		if theftOrig[i].ID == "agentic-praxis-grimoire-workflow" {
			theftOrig[i].Description = "Use when APG routing is needed."
			theftOrig[i].DescriptionBytes = int64(len([]byte(theftOrig[i].Description)))
			theftOrig[i].DescriptionCharacters = int64(utf8.RuneCountInString(theftOrig[i].Description))
			break
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010Toolchain, theftOrig); err == nil {
		t.Fatal("mutating original 39 skill description under v0.10-toolchain must fail as reservation theft")
	}

	// 2. Mutate SVG description under v0.10-toolchain (must be byte-identical to FrozenSVGSkillDescription)
	theftSVG := toolchainBaseline44()
	for i := range theftSVG {
		if theftSVG[i].ID == "svg-language-profile" {
			theftSVG[i].Description = "Use when SVG authoring is needed."
			theftSVG[i].DescriptionBytes = int64(len([]byte(theftSVG[i].Description)))
			theftSVG[i].DescriptionCharacters = int64(utf8.RuneCountInString(theftSVG[i].Description))
			break
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010Toolchain, theftSVG); err == nil {
		t.Fatal("mutating SVG description under v0.10-toolchain must fail as reservation theft")
	}

	// 3. Mutate Playwright description under v0.10-toolchain (must be byte-identical to FrozenPlaywrightSkillDescription)
	theftPW := toolchainBaseline44()
	for i := range theftPW {
		if theftPW[i].ID == "playwright-test-profile" {
			theftPW[i].Description = "Use when Playwright test runner applies to browsers."
			theftPW[i].DescriptionBytes = int64(len([]byte(theftPW[i].Description)))
			theftPW[i].DescriptionCharacters = int64(utf8.RuneCountInString(theftPW[i].Description))
			break
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010Toolchain, theftPW); err == nil {
		t.Fatal("mutating Playwright description under v0.10-toolchain must fail as reservation theft")
	}

	// 4. Mutate Web Accessibility description under v0.10-toolchain (must be byte-identical to FrozenWebAccessibilitySkillDescription)
	theftA11y := toolchainBaseline44()
	for i := range theftA11y {
		if theftA11y[i].ID == "web-accessibility-profile" {
			theftA11y[i].Description = "Use when web accessibility checks apply."
			theftA11y[i].DescriptionBytes = int64(len([]byte(theftA11y[i].Description)))
			theftA11y[i].DescriptionCharacters = int64(utf8.RuneCountInString(theftA11y[i].Description))
			break
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010Toolchain, theftA11y); err == nil {
		t.Fatal("mutating Web Accessibility description under v0.10-toolchain must fail as reservation theft")
	}
}

func TestValidateDiscoveryPolicyV010ToolchainBodyCeilingExemptionAndSVGLimit(t *testing.T) {
	// Playwright, Web-a11y, Vite, and npm have body sizes > 20480 (e.g. 50000 bytes) -> MUST PASS!
	skillsLargeNonSVG := toolchainBaseline44()
	for i := range skillsLargeNonSVG {
		switch skillsLargeNonSVG[i].ID {
		case "playwright-test-profile":
			skillsLargeNonSVG[i].BodyBytes = 50000
			skillsLargeNonSVG[i].BodyCharacters = 50000
		case "web-accessibility-profile":
			skillsLargeNonSVG[i].BodyBytes = 60000
			skillsLargeNonSVG[i].BodyCharacters = 60000
		case "vite-build-profile":
			skillsLargeNonSVG[i].BodyBytes = 70000
			skillsLargeNonSVG[i].BodyCharacters = 70000
		case "npm-package-manager-profile":
			skillsLargeNonSVG[i].BodyBytes = 80000
			skillsLargeNonSVG[i].BodyCharacters = 80000
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010Toolchain, skillsLargeNonSVG); err != nil {
		t.Fatalf("large body bytes on new non-SVG leaves must pass (exemption from 20480 limit): %v", err)
	}

	// SVG body size > 20480 -> MUST FAIL!
	skillsOverSVG := toolchainBaseline44()
	for i := range skillsOverSVG {
		if skillsOverSVG[i].ID == "svg-language-profile" {
			skillsOverSVG[i].BodyBytes = 20481
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010Toolchain, skillsOverSVG); err == nil {
		t.Fatal("SVG body size > 20480 must fail")
	}

	// Non-positive body bytes on Vite -> MUST FAIL!
	skillsZeroBody := toolchainBaseline44()
	for i := range skillsZeroBody {
		if skillsZeroBody[i].ID == "vite-build-profile" {
			skillsZeroBody[i].BodyBytes = 0
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010Toolchain, skillsZeroBody); err == nil {
		t.Fatal("zero body bytes on Vite must fail")
	}

	// Non-positive body bytes on npm -> MUST FAIL!
	skillsZeroBodyNPM := toolchainBaseline44()
	for i := range skillsZeroBodyNPM {
		if skillsZeroBodyNPM[i].ID == "npm-package-manager-profile" {
			skillsZeroBodyNPM[i].BodyBytes = -1
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010Toolchain, skillsZeroBodyNPM); err == nil {
		t.Fatal("negative body bytes on npm must fail")
	}
}

func TestValidateDiscoveryPolicyV010ToolchainMalformedMetadata(t *testing.T) {
	// Empty ID on candidate
	badID := toolchainBaseline44()
	for i := range badID {
		if badID[i].ID == "vite-build-profile" {
			badID[i].ID = ""
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010Toolchain, badID); err == nil {
		t.Fatal("empty candidate ID must fail")
	}

	// Empty Description on candidate
	badDesc := toolchainBaseline44()
	for i := range badDesc {
		if badDesc[i].ID == "npm-package-manager-profile" {
			badDesc[i].Description = ""
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010Toolchain, badDesc); err == nil {
		t.Fatal("empty candidate Description must fail")
	}

	// Candidate description without "Use when " prefix
	badPrefix := toolchainBaseline44()
	for i := range badPrefix {
		if badPrefix[i].ID == "vite-build-profile" {
			badPrefix[i].Description = "Invalid prefix description."
			badPrefix[i].DescriptionBytes = int64(len([]byte(badPrefix[i].Description)))
			badPrefix[i].DescriptionCharacters = int64(utf8.RuneCountInString(badPrefix[i].Description))
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010Toolchain, badPrefix); err == nil {
		t.Fatal("candidate description without 'Use when ' must fail")
	}
}

func TestValidateDiscoveryPolicyV010ToolchainTotalCeiling(t *testing.T) {
	skills := toolchainBaseline44()
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010Toolchain, skills); err != nil {
		t.Fatalf("baseline total description bytes should be under ceiling: %v", err)
	}

	// Verify that the ceiling constants are correctly sized
	if V010ToolchainAdmissionCeiling != 11177 {
		t.Fatalf("V010ToolchainAdmissionCeiling = %d, want 11177", V010ToolchainAdmissionCeiling)
	}
	if V010CurrentToolchainAdmissionCeiling != 11177 {
		t.Fatalf("V010CurrentToolchainAdmissionCeiling = %d, want 11177", V010CurrentToolchainAdmissionCeiling)
	}
	if V010OverallFutureCeiling != 11507 {
		t.Fatalf("V010OverallFutureCeiling = %d, want 11507", V010OverallFutureCeiling)
	}
}

func browserRuntimeBaseline45() []SkillMetadata {
	list := baselineSkillMetadataList()
	list = append(list,
		makeCandidateMetadata("svg-language-profile", FrozenSVGSkillDescription, 20480),
		makeCandidateMetadata("playwright-test-profile", FrozenPlaywrightSkillDescription, 35000),
		makeCandidateMetadata("web-accessibility-profile", FrozenWebAccessibilitySkillDescription, 40000),
		makeCandidateMetadata("vite-build-profile", FrozenViteSkillDescription, 25000),
		makeCandidateMetadata("npm-package-manager-profile", FrozenNPMSkillDescription, 30000),
		makeCandidateMetadata("browser-runtime-profile", "Use when browser host runtime behavior, Web APIs, DOM, workers, or navigation are evaluated.", 28000),
	)
	return list
}

func TestValidateDiscoveryPolicyV010BrowserRuntimeExactBoundaries(t *testing.T) {
	baseline45 := browserRuntimeBaseline45()
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserRuntime, baseline45); err != nil {
		t.Fatalf("valid 45-skill baseline under %s must pass: %v", DiscoveryPolicyVersionV010BrowserRuntime, err)
	}

	// SVG body at exactly 20480 bytes passes
	skillsExactSVG := browserRuntimeBaseline45()
	for i := range skillsExactSVG {
		if skillsExactSVG[i].ID == "svg-language-profile" {
			skillsExactSVG[i].BodyBytes = 20480
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserRuntime, skillsExactSVG); err != nil {
		t.Fatalf("exact 20480 SVG body bytes must pass: %v", err)
	}

	// browser-runtime-profile at exact 330 description bytes passes
	skillsExactBR := browserRuntimeBaseline45()
	for i := range skillsExactBR {
		if skillsExactBR[i].ID == "browser-runtime-profile" {
			desc := makeDescriptionWithBytes("Use when browser runtime is needed ", 330)
			skillsExactBR[i].Description = desc
			skillsExactBR[i].DescriptionBytes = int64(len([]byte(desc)))
			skillsExactBR[i].DescriptionCharacters = int64(utf8.RuneCountInString(desc))
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserRuntime, skillsExactBR); err != nil {
		t.Fatalf("exact 330 description bytes for browser-runtime must pass: %v", err)
	}
}

func TestValidateDiscoveryPolicyV010BrowserRuntimeOneOverBoundaries(t *testing.T) {
	// 1. One-over description reservation: 331 bytes on browser-runtime-profile
	skillsOverBR := browserRuntimeBaseline45()
	for i := range skillsOverBR {
		if skillsOverBR[i].ID == "browser-runtime-profile" {
			desc := makeDescriptionWithBytes("Use when browser runtime is needed ", 331)
			skillsOverBR[i].Description = desc
			skillsOverBR[i].DescriptionBytes = int64(len([]byte(desc)))
			skillsOverBR[i].DescriptionCharacters = int64(utf8.RuneCountInString(desc))
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserRuntime, skillsOverBR); err == nil {
		t.Fatal("expected failure for 331-byte description on browser-runtime-profile")
	}

	// 2. One-over file size for SVG: 20481 bytes
	skillsOverSVGFile := browserRuntimeBaseline45()
	for i := range skillsOverSVGFile {
		if skillsOverSVGFile[i].ID == "svg-language-profile" {
			skillsOverSVGFile[i].BodyBytes = 20481
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserRuntime, skillsOverSVGFile); err == nil {
		t.Fatal("expected failure for 20481-byte SVG file (limit is 20480)")
	}

	// 3. Count 44 (missing browser-runtime-profile)
	skills44 := browserRuntimeBaseline45()[:44]
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserRuntime, skills44); err == nil {
		t.Fatal("expected failure for 44 skills under v0.10-browser-runtime (must be exactly 45)")
	}

	// 4. Count 46 (extra candidate)
	candExtra := makeCandidateMetadata("unregistered-profile", "Use when unregistered profile applies.", 1000)
	skills46 := append(browserRuntimeBaseline45(), candExtra)
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserRuntime, skills46); err == nil {
		t.Fatal("expected failure for 46 skills under v0.10-browser-runtime (must be exactly 45)")
	}

	// 5. Count 42 (historical browser-ui count)
	skills42 := browserRuntimeBaseline45()[:42]
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserRuntime, skills42); err == nil {
		t.Fatal("expected failure for 42 skills under v0.10-browser-runtime (must be exactly 45)")
	}

	// 6. Count 40 (historical v0.10 count)
	skills40 := browserRuntimeBaseline45()[:40]
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserRuntime, skills40); err == nil {
		t.Fatal("expected failure for 40 skills under v0.10-browser-runtime (must be exactly 45)")
	}

	// 7. Count 39 (historical baseline count)
	skills39 := baselineSkillMetadataList()
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserRuntime, skills39); err == nil {
		t.Fatal("expected failure for 39 skills under v0.10-browser-runtime (must be exactly 45)")
	}
}

func TestValidateDiscoveryPolicyV010BrowserRuntimeMultibyteEnforcement(t *testing.T) {
	// Multibyte 330 bytes description on browser-runtime-profile: 9 bytes "Use when " + 160 * 2 bytes 'é' + 1 byte 'x' = 330 bytes
	multibyte330 := "Use when " + strings.Repeat("é", 160) + "x"
	skillsMultibyte := browserRuntimeBaseline45()
	for i := range skillsMultibyte {
		if skillsMultibyte[i].ID == "browser-runtime-profile" {
			skillsMultibyte[i].Description = multibyte330
			skillsMultibyte[i].DescriptionBytes = int64(len([]byte(multibyte330)))
			skillsMultibyte[i].DescriptionCharacters = int64(utf8.RuneCountInString(multibyte330))
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserRuntime, skillsMultibyte); err != nil {
		t.Fatalf("multibyte 330-byte candidate description must pass: %v", err)
	}

	// Multibyte 331 bytes description on browser-runtime-profile
	multibyte331 := "Use when " + strings.Repeat("é", 160) + "xx"
	skillsMultibyteOver := browserRuntimeBaseline45()
	for i := range skillsMultibyteOver {
		if skillsMultibyteOver[i].ID == "browser-runtime-profile" {
			skillsMultibyteOver[i].Description = multibyte331
			skillsMultibyteOver[i].DescriptionBytes = int64(len([]byte(multibyte331)))
			skillsMultibyteOver[i].DescriptionCharacters = int64(utf8.RuneCountInString(multibyte331))
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserRuntime, skillsMultibyteOver); err == nil {
		t.Fatal("multibyte 331-byte description must fail")
	}

	// Tampered DescriptionBytes field
	skillsTampered := browserRuntimeBaseline45()
	for i := range skillsTampered {
		if skillsTampered[i].ID == "browser-runtime-profile" {
			skillsTampered[i].Description = multibyte330
			skillsTampered[i].DescriptionBytes = int64(utf8.RuneCountInString(multibyte330)) // tampered to 170
			skillsTampered[i].DescriptionCharacters = int64(utf8.RuneCountInString(multibyte330))
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserRuntime, skillsTampered); err == nil {
		t.Fatal("tampered DescriptionBytes field must fail")
	}
}

func TestValidateDiscoveryPolicyV010BrowserRuntimeSetEqualityAndSubstitution(t *testing.T) {
	// 1. Substitute browser-runtime-profile with unregistered candidate
	subUnreg := browserRuntimeBaseline45()
	for i := range subUnreg {
		if subUnreg[i].ID == "browser-runtime-profile" {
			subUnreg[i] = makeCandidateMetadata("unregistered-profile", "Use when unregistered applies.", 1000)
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserRuntime, subUnreg); err == nil {
		t.Fatal("substituting with unregistered candidate must fail")
	}

	// 2. Duplicate candidate ID (two vite candidates, missing browser-runtime-profile)
	dupeCand := browserRuntimeBaseline45()
	for i := range dupeCand {
		if dupeCand[i].ID == "browser-runtime-profile" {
			dupeCand[i] = dupeCand[i-2] // duplicate vite
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserRuntime, dupeCand); err == nil {
		t.Fatal("duplicate candidate ID must fail")
	}

	// 3. Duplicate original skill ID
	dupeOrig := browserRuntimeBaseline45()
	dupeOrig[1] = dupeOrig[0]
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserRuntime, dupeOrig); err == nil {
		t.Fatal("duplicate original skill ID must fail")
	}
}

func TestValidateDiscoveryPolicyV010BrowserRuntimeFrozenDescriptions(t *testing.T) {
	// 1. Mutate an original 39 skill description
	theftOrig := browserRuntimeBaseline45()
	for i := range theftOrig {
		if theftOrig[i].ID == "agentic-praxis-grimoire-workflow" {
			theftOrig[i].Description = "Use when APG routing is needed."
			theftOrig[i].DescriptionBytes = int64(len([]byte(theftOrig[i].Description)))
			theftOrig[i].DescriptionCharacters = int64(utf8.RuneCountInString(theftOrig[i].Description))
			break
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserRuntime, theftOrig); err == nil {
		t.Fatal("mutating original 39 skill description under v0.10-browser-runtime must fail as reservation theft")
	}

	// 2. Mutate SVG description under v0.10-browser-runtime
	theftSVG := browserRuntimeBaseline45()
	for i := range theftSVG {
		if theftSVG[i].ID == "svg-language-profile" {
			theftSVG[i].Description = "Use when SVG authoring is needed."
			theftSVG[i].DescriptionBytes = int64(len([]byte(theftSVG[i].Description)))
			theftSVG[i].DescriptionCharacters = int64(utf8.RuneCountInString(theftSVG[i].Description))
			break
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserRuntime, theftSVG); err == nil {
		t.Fatal("mutating SVG description under v0.10-browser-runtime must fail as reservation theft")
	}

	// 3. Mutate Playwright description under v0.10-browser-runtime
	theftPW := browserRuntimeBaseline45()
	for i := range theftPW {
		if theftPW[i].ID == "playwright-test-profile" {
			theftPW[i].Description = "Use when Playwright test runner applies to browsers."
			theftPW[i].DescriptionBytes = int64(len([]byte(theftPW[i].Description)))
			theftPW[i].DescriptionCharacters = int64(utf8.RuneCountInString(theftPW[i].Description))
			break
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserRuntime, theftPW); err == nil {
		t.Fatal("mutating Playwright description under v0.10-browser-runtime must fail as reservation theft")
	}

	// 4. Mutate Web Accessibility description under v0.10-browser-runtime
	theftA11y := browserRuntimeBaseline45()
	for i := range theftA11y {
		if theftA11y[i].ID == "web-accessibility-profile" {
			theftA11y[i].Description = "Use when web accessibility checks apply."
			theftA11y[i].DescriptionBytes = int64(len([]byte(theftA11y[i].Description)))
			theftA11y[i].DescriptionCharacters = int64(utf8.RuneCountInString(theftA11y[i].Description))
			break
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserRuntime, theftA11y); err == nil {
		t.Fatal("mutating Web Accessibility description under v0.10-browser-runtime must fail as reservation theft")
	}

	// 5. Mutate Vite description under v0.10-browser-runtime
	theftVite := browserRuntimeBaseline45()
	for i := range theftVite {
		if theftVite[i].ID == "vite-build-profile" {
			theftVite[i].Description = "Use when Vite build and bundling applies."
			theftVite[i].DescriptionBytes = int64(len([]byte(theftVite[i].Description)))
			theftVite[i].DescriptionCharacters = int64(utf8.RuneCountInString(theftVite[i].Description))
			break
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserRuntime, theftVite); err == nil {
		t.Fatal("mutating Vite description under v0.10-browser-runtime must fail as reservation theft")
	}

	// 6. Mutate npm description under v0.10-browser-runtime
	theftNPM := browserRuntimeBaseline45()
	for i := range theftNPM {
		if theftNPM[i].ID == "npm-package-manager-profile" {
			theftNPM[i].Description = "Use when npm package management workflows apply."
			theftNPM[i].DescriptionBytes = int64(len([]byte(theftNPM[i].Description)))
			theftNPM[i].DescriptionCharacters = int64(utf8.RuneCountInString(theftNPM[i].Description))
			break
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserRuntime, theftNPM); err == nil {
		t.Fatal("mutating npm description under v0.10-browser-runtime must fail as reservation theft")
	}
}

func TestValidateDiscoveryPolicyV010BrowserRuntimeBodyCeilingExemptionAndSVGLimit(t *testing.T) {
	// Playwright, Web-a11y, Vite, npm, and browser-runtime have body sizes > 20480 (e.g. 50000 bytes) -> MUST PASS!
	skillsLargeNonSVG := browserRuntimeBaseline45()
	for i := range skillsLargeNonSVG {
		switch skillsLargeNonSVG[i].ID {
		case "playwright-test-profile":
			skillsLargeNonSVG[i].BodyBytes = 50000
			skillsLargeNonSVG[i].BodyCharacters = 50000
		case "web-accessibility-profile":
			skillsLargeNonSVG[i].BodyBytes = 60000
			skillsLargeNonSVG[i].BodyCharacters = 60000
		case "vite-build-profile":
			skillsLargeNonSVG[i].BodyBytes = 70000
			skillsLargeNonSVG[i].BodyCharacters = 70000
		case "npm-package-manager-profile":
			skillsLargeNonSVG[i].BodyBytes = 80000
			skillsLargeNonSVG[i].BodyCharacters = 80000
		case "browser-runtime-profile":
			skillsLargeNonSVG[i].BodyBytes = 90000
			skillsLargeNonSVG[i].BodyCharacters = 90000
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserRuntime, skillsLargeNonSVG); err != nil {
		t.Fatalf("large body bytes on new non-SVG leaves must pass (exemption from 20480 limit): %v", err)
	}

	// SVG body size > 20480 -> MUST FAIL!
	skillsOverSVG := browserRuntimeBaseline45()
	for i := range skillsOverSVG {
		if skillsOverSVG[i].ID == "svg-language-profile" {
			skillsOverSVG[i].BodyBytes = 20481
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserRuntime, skillsOverSVG); err == nil {
		t.Fatal("SVG body size > 20480 must fail")
	}

	// Non-positive body bytes on browser-runtime-profile -> MUST FAIL!
	skillsZeroBody := browserRuntimeBaseline45()
	for i := range skillsZeroBody {
		if skillsZeroBody[i].ID == "browser-runtime-profile" {
			skillsZeroBody[i].BodyBytes = 0
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserRuntime, skillsZeroBody); err == nil {
		t.Fatal("zero body bytes on browser-runtime-profile must fail")
	}

	skillsNegativeBody := browserRuntimeBaseline45()
	for i := range skillsNegativeBody {
		if skillsNegativeBody[i].ID == "browser-runtime-profile" {
			skillsNegativeBody[i].BodyBytes = -1
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserRuntime, skillsNegativeBody); err == nil {
		t.Fatal("negative body bytes on browser-runtime-profile must fail")
	}
}

func TestValidateDiscoveryPolicyV010BrowserRuntimeMalformedMetadata(t *testing.T) {
	// Empty ID on candidate
	badID := browserRuntimeBaseline45()
	for i := range badID {
		if badID[i].ID == "browser-runtime-profile" {
			badID[i].ID = ""
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserRuntime, badID); err == nil {
		t.Fatal("empty candidate ID must fail")
	}

	// Empty Description on candidate
	badDesc := browserRuntimeBaseline45()
	for i := range badDesc {
		if badDesc[i].ID == "browser-runtime-profile" {
			badDesc[i].Description = ""
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserRuntime, badDesc); err == nil {
		t.Fatal("empty candidate Description must fail")
	}

	// Candidate description without "Use when " prefix
	badPrefix := browserRuntimeBaseline45()
	for i := range badPrefix {
		if badPrefix[i].ID == "browser-runtime-profile" {
			badPrefix[i].Description = "Invalid prefix description."
			badPrefix[i].DescriptionBytes = int64(len([]byte(badPrefix[i].Description)))
			badPrefix[i].DescriptionCharacters = int64(utf8.RuneCountInString(badPrefix[i].Description))
		}
	}
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserRuntime, badPrefix); err == nil {
		t.Fatal("candidate description without 'Use when ' must fail")
	}
}

func TestValidateDiscoveryPolicyV010BrowserRuntimeTotalCeiling(t *testing.T) {
	skills := browserRuntimeBaseline45()
	if err := ValidateDiscoveryPolicy(DiscoveryPolicyVersionV010BrowserRuntime, skills); err != nil {
		t.Fatalf("baseline total description bytes should be under ceiling: %v", err)
	}

	// Verify that the ceiling constants are correctly sized
	if V010BrowserRuntimeAdmissionCeiling != 11507 {
		t.Fatalf("V010BrowserRuntimeAdmissionCeiling = %d, want 11507", V010BrowserRuntimeAdmissionCeiling)
	}
	if V010CurrentBrowserRuntimeAdmissionCeiling != 11507 {
		t.Fatalf("V010CurrentBrowserRuntimeAdmissionCeiling = %d, want 11507", V010CurrentBrowserRuntimeAdmissionCeiling)
	}
	if V010OverallFutureCeiling != 11507 {
		t.Fatalf("V010OverallFutureCeiling = %d, want 11507", V010OverallFutureCeiling)
	}
}
