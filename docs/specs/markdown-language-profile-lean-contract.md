# Markdown Language-Profile Lean Validation Contract

## Status

- Phase: APG63 proposal, forward-corrected and terminally reviewed by APG64
- Status: Current accepted candidate-independent input under
  [ADR 0037](../adr/2026/07/0037-markdown-language-profile-architecture-and-lean-validation.md);
  no candidate skill exists and authoring requires separate authority
- Governing architecture: [Markdown language-profile architecture](../architecture/markdown-language-profile-architecture.md)

This contract would be wrong if a future candidate could satisfy every
scenario invariant below while still misassigning ownership, permission,
stop, safety, privacy, or rollback behavior — or if honoring it required
the candidate to explain generic APG lifecycle internals. Those are its
falsification conditions.

## Scope

This is a candidate-independent authoring contract, not a candidate skill.
It binds one future, separately authorized Markdown candidate-authoring
phase and one future, separately authorized validation review. It does not
create catalog, maturity, route, projection, release, test-inventory, or
report surfaces, and it deliberately omits exact repository owner
inventories. It does not amend generic APG policy: the severity,
correction, and evidence rules below are proposed for Markdown review
only.

## Source hierarchy

- Effective grammar: actual renderer/parser, exact version, configuration,
  and enabled extensions. Implementation behavior is version-bound and owned
  by `parser-tool-owner`.
- Base reference: CommonMark 0.31.2 (2024-01-28) only where applicable.
- Extension reference: GFM 0.29 (2019-04-06) only for its five specified
  extension families. It is not normatively composed with CommonMark 0.31.2.
- GitHub platform rendering and Astro/Starlight/Satteri rendering are
  distinct implementation contexts; neither is defined by the two references
  alone.
- Both exact specification documents state CC BY-SA 4.0. Identified
  implementation/test regions use separate BSD-2-Clause or MIT terms. No
  copied or adapted specification or target expression was identified. This
  is a bounded factual result, not legal advice or a universal guarantee.
- Exact object identities and target toolchain limitations are recorded in
  publication-excluded evidence. Source, rights, parser, configuration, or
  target changes require reverification.

## Closed owner vocabulary

A scenario's `Owner` and routing statements use exactly this vocabulary:

- `markdown-language-profile` — the candidate owner (selected dialect
  document semantics);
- `mdx-owner` — MDX whole-file semantics;
- `parser-tool-owner` — the repository's actual parser, plugin, and
  toolchain facts;
- `project-policy` — project-owned content, raw-HTML permission,
  frontmatter schema, asset, and tool-selection policy;
- `project-design` — project architecture and document-taxonomy decisions;
- `repository-policy` — stricter repository rules that always control;
- `human-instruction` — explicit human task authority;
- `host-owner` — the owner of a non-MDX host artifact in which Markdown
  is embedded (documentation string, comment, generated fragment);
- `generic-lifecycle` — existing APG workflow and integration contracts,
  outside Markdown semantic prose;
- `html-owner` — conceptual receiving owner for HTML element semantics;
- `accessibility-owner` — conceptual receiving owner for accessibility
  acceptance;
- `embedded-language-owner` — conceptual receiving owner for a fenced or
  embedded non-Markdown language;
- `data-language-owner` — conceptual receiving owner for frontmatter data
  syntax.

The four conceptual receiving-owner tokens identify competence boundaries;
they do not assert that an integrated APG skill exists. No other owner token
is valid in the register.

## Closed selection, response, and routing vocabularies

A scenario's `Selection` uses exactly:

- `selected` — Markdown owns the primary decision;
- `embedded-route` — one primary owner remains exact while a bounded embedded
  decision routes onward;
- `route-to-owner` — another owner owns the primary decision;
- `non-trigger` — whole-file Markdown selection does not apply.

A scenario's `Response` uses exactly the four ordered warning severities:

- `proceed-routine` — `Green — routine`;
- `inspect-before-judgment` — `Yellow — caution`;
- `bounded-local-decision` — `Orange — warning`;
- `stop-and-escalate` — `Red — crisis / stop`;

`Route` contains one exact owner token or `not-applicable`. Selection and
routing never replace severity. A routed stop stays stopped until the receiving
owner resolves it. No other selection, response, or route token is valid.

## Scenario schema

The corrected register contains exactly APG63-MD-001 through APG63-MD-036 in
six families. Every scenario has exactly these fourteen fields:

- `In:` public-safe artifact or task;
- `Dialect:` selected parser and dialect facts;
- `Decision:` one primary consequence-bearing decision;
- `Owner:` one exact primary owner from the closed vocabulary;
- `Selection:` one exact selection token;
- `Response:` one exact warning severity;
- `Route:` one exact receiving owner or `not-applicable`;
- `Non:` explicit non-owners;
- `Structural:` zero or more closed structural-signal tokens;
- `Semantic:` zero or more closed semantic-signal tokens;
- `Invariant:` required semantic invariant;
- `Forbid:` forbidden claim or action;
- `Rb:` rollback when material;
- `Src:` source or version boundary.

Rows 001–034 are candidate-semantic scenarios a future candidate must satisfy.
Rows 035–036 are review-process invariants owned by `generic-lifecycle`; the
candidate must not explain or satisfy them. Scenario prose remains invariant
guidance, not an exact-action script, and no sixty-row action map may be
recreated.

## Structural-policy decision

Disposition C is selected: qualitative structure-first policy without
numeric whole-file bands. Fourteen named signals have a frozen evidence
class: mechanical observation, contextual judgment, or routed acceptance.
Each signal records its evidence, scope, response, route, and false-positive
control. Signals classify the current decision, never a document score;
co-firing signals use the strongest consequence-bearing response. Line count
is descriptive only: it may prompt inspection but never classifies by itself.
The `whole-document-review-boundary` is a qualitative signal for documents
whose purpose, navigation, ownership, or generated/manual boundary cannot be
judged safely from a local fragment; it is not a numeric size proxy. The ten
frozen purpose controls (SHA-256 recorded in the APG63 bundle) constrain
application. The historically rejected numeric values are forbidden, and no
normative threshold may be derived from percentiles. A candidate that
introduces numeric whole-file bands violates this contract unless a later
accepted decision changes the disposition first.

## Severity model

- `material`: wrong owner; wrong permission or stop; missing required
  safety or rollback; contradictory normative behavior; rights, privacy,
  or source defect; structurally incomplete policy; false success.
- `ordinary`: wording ambiguity with one clear intended meaning;
  incomplete cross-reference; non-behavioral metadata; navigation defect;
  formatting, link, or index issue.
- `note`: optional improvement; redundant but noncontradictory
  explanation; benign bookkeeping recommendation.

Exactness is tiered: ownership-bearing behavior, permission and stop
behavior, and safety and rollback behavior are exact; benign bookkeeping
is recommended-only. An extra reporting action is material only when it
keeps the wrong owner active, crosses a non-owner boundary, changes
permission or stop behavior, creates false completion, creates a privacy
or rights burden, or contradicts the selected architecture. A harmless
superset is not material without one of those consequences. Conversely,
an omitted or extra observation is material only when the omission or
addition produces one of those consequence-bearing failures; mechanical
field inequality alone does not decide severity.

## One-correction rule

APG64 and any future candidate review must: collect the complete initial material set
before any correction; apply at most one coherent semantic correction;
preserve the corrected artifact; perform full corrected-state review; and
reject on a genuinely new material defect found after the sole
correction. The one-correction bound is meaningful only when initial
review is complete and corrected-state evidence is independently
auditable.

## Corrected-state evidence rule

Before corrected-state review: record the corrected architecture,
specification, ADR, and register hashes; record an exact full-index patch
against the authoring commit together with its digest and path set; preserve
corrected candidate tests or their canonical structured vectors; and
associate reviewer results with the corrected hashes. If retained: the
hashes must correspond to the integrated bytes. If rejected: preserve a
compact publication-excluded correction artifact or immutable review object
before deleting current candidate files. Massive generated evidence is not
required, and the original Claude authoring object is never rewritten.

## Future Claude authoring boundary

The smallest separately authorized authoring slice is: one Markdown leaf; one
candidate specification; one compact invariant map or scenario link; one
Proposed or accepted architecture input. It excludes MDX, HTML, and
Starlight skills; catalog, maturity, route, projection, release, or test
surfaces; numeric whole-file bands; copied specification text; and any
generic-lifecycle prose inside candidate semantics. Authoring requires
separate authorization; this contract grants none.

## Future Codex review boundary

The validation phase independently reverifies sources, rights, targets,
and dogfood; replays all thirty-six scenarios; challenges owner
coherence, the raw-HTML, frontmatter, and MDX boundaries, structural-
policy purpose fit, contract determinism, the severity distinction, and
corrected-state evidence; applies at most one coherent correction under
the rules above; and terminally decides the governing ADR. It authorizes
no skill automatically, integrates nothing by default, and runs no target
commands.

## Integration and removal boundary

Generic lifecycle stays outside Markdown semantic prose. The register's
lifecycle group states only: a candidate remains unintegrated until the
deciding review; a retained owner requires later closure through existing
integration contracts; rejection removes current candidate surfaces while
preserving complete history. Catalog, release, projection, test-inventory,
report, and Git operations belong to `generic-lifecycle` owners and never
become Markdown-language clauses.

## Canonical adjunct

No JSON adjunct accompanies this contract. The scenario register is the
single frozen validation artifact; a machine-readable duplicate would add
maintenance surface without adding validation value at this phase.
