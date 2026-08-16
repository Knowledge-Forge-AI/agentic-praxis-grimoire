# APG65 Markdown Language-Profile Authoring

## Outcome

APG65 verified the exact APG64 baseline — the accepted architecture, lean
contract, and corrected scenario register under
[ADR 0037](../adr/2026/07/0037-markdown-language-profile-architecture-and-lean-validation.md)
(Accepted with amendment) — and authored one fresh
`markdown-language-profile` candidate on the Claude authoring branch. The
exact baseline object identities live in the managed phase reports rather
than this public record.

The candidate consists of the leaf
(`skills/markdown-language-profile/SKILL.md`), the
[candidate specification](../specs/markdown-language-profile.md), and the
navigation-only
[scenario-coverage record](../specs/markdown-language-profile-scenario-coverage.md).
[ADR 0038](../adr/2026/07/0038-markdown-language-profile-candidate.md) is
Proposed and not decided. The candidate lifecycle is
authored-proposed-unintegrated: branch-only, Proposed, unintegrated, and
pending separately authorized APG66 validation.

## Candidate shape

- Trigger: a material current decision depending on the repository's actual
  Markdown parser, selected-dialect document semantics, Markdown semantic
  risk, or qualitative document-structure judgment. Non-triggers include
  ordinary prose drafting, editorial and content-strategy questions, HTML
  semantics and accessibility acceptance, frontmatter data and schema,
  fenced-content semantics, MDX whole-file work, pipeline configuration,
  and every tool selection.
- Effective grammar: the actual renderer/parser with exact version and
  configuration first; CommonMark 0.31.2 as a bounded base reference; GFM
  0.29 as a bounded reference for its five specified extension families;
  implementation behavior as version-bound `parser-tool-owner` input. No
  synthetic composite dialect; GitHub and Astro/Starlight/Satteri rendering
  are never equated.
- Owner boundary: selected-dialect document semantics only, with the
  accepted narrowing; link validity, asset policy, fenced content, HTML
  meaning, accessibility acceptance, frontmatter data and schema, MDX
  whole-file semantics, and tool selection remain routed non-owners.
- Axes: selection, response severity, and receiving-owner routing stay
  separate; routing never lowers severity and a routed stop stays stopped.
- Structural policy: qualitative and decision-scoped with the fourteen
  accepted signals, their evidence classes, and false-positive controls;
  no numeric whole-file band exists anywhere in the candidate, and line
  count is descriptive inspection evidence only.

## Coverage and clauses

Twenty-four stable clause IDs exist, each globally unique across the leaf
and specification, and every clause is referenced by the coverage record.
All thirty-four candidate-semantic scenarios (APG63-MD-001 through
APG63-MD-034) are mapped exactly once to supporting clauses; the two
review-process invariants (APG63-MD-035 and APG63-MD-036) are absent from
candidate obligations because they bind the APG66 review. The coverage
record is navigation-only: the accepted register remains the sole behavior
oracle, and the private APG65 review separately verified that each
scenario's mapped clauses collectively support its register expectations.

## Refresh and preservation

The pinned CommonMark 0.31.2 and GFM 0.29 specification objects, their
CC BY-SA 4.0 document rights, the actual-parser-first hierarchy, and both
read-only target repositories were reverified unchanged at their exact
objects; no target command was run and no source, specification, or target
expression was copied. The APG64 architecture, lean contract, scenario
register, and ADR 0037 bytes are unchanged in this phase. One stale ADR
index status line for ADR 0037 was corrected to its APG64-decided state;
the ADR file itself is untouched.

The authoring branch truthfully reports the transitional physical shape of
twenty-nine canonical leaves with twenty-eight catalog rows and twenty-eight
projections; integrated development `main` remains 28/28/28 with fourteen
stable and fourteen provisional maturity rows. No catalog, maturity,
capability-map, router, projection, project-skill, release, public-surface,
fixture, focused-test, or test-inventory owner changed. CSS remains absent;
ADR 0031, 0034, 0035, and 0036 remain Rejected. Corrected public and active
v0.4.0 remain unchanged.

## Boundary

APG65 validates nothing and integrates nothing: the candidate is design
evidence awaiting independent APG66 validation, which is recommended in the
private handoff, separately authorized, and not begun. No readiness,
publication, deployment, or activation work started in this phase.

## Forward APG66 disposition

APG66 subsequently preserved and remotely delivered this exact Claude object,
applied one coherent Codex correction on its child branch, and accepted ADR
0038 with amendment after fresh corrected-state review. The profile is now
retained provisionally in current development. This forward note does not
change APG65's authoring-time result, authorship, commit, or report.
