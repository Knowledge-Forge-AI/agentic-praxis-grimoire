# JavaScript Language-Profile Lean Validation Contract

## Status

- Phase: APG67 proposal corrected and terminally reviewed by APG68
- Status: Rejected historical corrected-proposal evidence under
  [ADR 0039](../adr/2026/08/0039-javascript-language-profile-architecture-and-lean-validation.md);
  no candidate skill exists and authoring requires separate authority
- Governing architecture: [JavaScript language-profile architecture](../architecture/javascript-language-profile-architecture.md)

This contract would be wrong if a future candidate could satisfy every
scenario invariant below while still misassigning ownership, permission,
stop, safety, privacy, or rollback behavior — or if honoring it required
the candidate to explain generic APG lifecycle internals, or if its
machine-checkable guards could pass while the guarded prose fact was
false. Those are its falsification conditions.

## Scope

This is a candidate-independent authoring contract, not a candidate skill.
It binds one future, separately authorized JavaScript candidate-authoring
phase and one future, separately authorized validation review. It creates
no catalog, maturity, route, projection, release, test-inventory, or
report surface. It does not amend generic APG policy: the severity,
correction, and evidence rules below are proposed for JavaScript review
only.

## Source identities

- Stable reference: ECMA-262, 17th edition, ECMAScript 2026 — tag object
  `f7db29f16c5175a93f0d6e8fb27a8e3cb9b97a9e`, commit
  `0248456c758431e4bb8e5d26333ff1865123c9cd`, and tree
  `02137fef007dced3167756ba3dbd3e11306ad4bf` in the tc39 ecma262
  repository; the Ecma
  publication page and the annual HTML snapshot confirm the edition, and
  the HTML version is normative.
- Annual errata: tag object `5ebd9700730a7d3b833af8f10793d76443803c0c`
  resolves to commit `d89c03f2db8a597bc915b363a6518d0cc8acdbc0`
  and tree `9e4b9d538cef2863b67bef26d7b414f9a3384ca6`; its sole change restores
  a non-normative feature-summary paragraph. It is a non-semantic
  source-correspondence overlay. A later consequence-bearing corrigendum
  stops for explicit dual-source disposition.
- Moving draft: the live repository head is the ECMAScript 2027 draft —
  refresh evidence only, never the stable baseline.
- Test262: bounded validation and corpus evidence under the verified Ecma
  BSD-style license; never normative authority; nothing is copied.
- Authority is question-specific: the annual HTML controls normative
  language semantics; exact host configuration establishes source goal;
  exact tool/runtime versions establish feature availability and observed
  behavior; owner evidence establishes divergence; project, repository,
  and security policy establish support and permission. Annex B applies
  only under an established context and later drafts have no authority
  without explicit selection plus implementation evidence.
- Natural-language specification text, repository source, annual embedded
  software, contributions, and Test262 have distinct verified rights
  statements. Source, rights, pipeline, or target changes require
  reverification.

## Closed owner vocabulary

A scenario's `Owner` and `Route` statements use exactly this vocabulary:

- `javascript-language-profile` — the candidate owner (ECMAScript
  language semantics after goal and context are established);
- `typescript-owner` — TypeScript whole-file and static-type semantics;
- `node-runtime-owner` — Node runtime, CommonJS, resolution and loading,
  process/filesystem/CLI, and user-script installation facts;
- `browser-platform-owner` — Window/DOM/events/timers/fetch/Web APIs,
  workers, storage, CSP, and script-element selection;
- `jsx-owner` — JSX syntax and transformation;
- `host-owner` — the owner of an Astro, MDX, HTML, or other host artifact
  in which JavaScript is embedded;
- `parser-tool-owner` — parser, transpiler, and source-transform behavior;
- `build-tool-owner` — generator, bundler, minifier, and produced-output
  behavior;
- `runtime-implementation-owner` — non-Node engine version, Unicode-data,
  implementation-divergence, and observed-runtime facts;
- `intl-owner` — ECMA-402 Intl semantics;
- `security-owner` — security acceptance for dynamic code, prototype
  pollution, and comparable mechanisms;
- `data-language-owner` — JSON documents and schemas and other data
  languages;
- `project-design` — project architecture, decomposition, and the
  JavaScript-versus-TypeScript division;
- `project-policy` — project-owned compatibility, permission, and tool
  policy;
- `repository-policy` — stricter repository rules that always control;
- `generic-lifecycle` — existing APG workflow and integration contracts.

`typescript-owner`, `node-runtime-owner`, `browser-platform-owner`,
`jsx-owner`, `runtime-implementation-owner`, `intl-owner`,
`security-owner`, and `data-language-owner`
are conceptual receiving owners: they identify competence boundaries and
do not assert that an integrated APG skill exists. No route for a
nonexistent skill is added to the APG router. `dom-owner` remains folded
into `browser-platform-owner`; there is no `package-tool-owner`, because
project policy selects tools and `node-runtime-owner` owns Node package
resolution. Task authority is governed by repository and manager-worker
policy rather than encoded as a scenario owner. No other owner token is
valid in the register, and no alias exists for any token.

## Closed selection, response, and routing vocabularies

`Selection` uses exactly: `selected`, `embedded-route`,
`route-to-owner`, or `non-trigger`. `Response` uses exactly the four
ordered warning severities of the accepted language-profile contract:
`proceed-routine` (Green), `inspect-before-judgment` (Yellow),
`bounded-local-decision` (Orange), and `stop-and-escalate` (Red).
`Route` contains one exact owner token or `not-applicable`. Selection and
routing never replace severity; a routed stop stays stopped until the
receiving owner resolves it; `non-trigger` is a selection state, not a
Green JavaScript decision. No other token is valid.

## Closed source-boundary vocabulary

`SourceBoundary` uses exactly one of: `ecma262-2026-annual`;
`runtime-parser-behavior`; `ecma262-2026-plus-runtime`;
`ecma262-2026-plus-host`; `host-defined-behavior`;
`implementation-defined-behavior`; `annex-b-normative-optional`;
`later-draft-or-proposal`; `ecma402-intl`; `node-documented-behavior`;
`browser-web-standard`; `project-configuration`; `transpiler-output`;
`ecma262-2026-plus-security-policy`;
`ecma262-2026-plus-data-contract`;
`artifact-provenance-and-repository-policy`; or `process-record`. Each
`plus` class names exactly two authorities and
each row states both roles. "JavaScript behavior" is never an
undifferentiated source class.

## Closed rollback vocabulary

`Rollback` uses exactly one of: `not-material`; `local-revert` (one
artifact revert restores prior behavior); `owner-coordinated-revert`
(consumers or owners must participate); or `process-owned` (rollback
belongs to `generic-lifecycle`).

## Scenario schema

The register contains exactly APG67-JS-001 through APG67-JS-040. Every
row has exactly these sixteen fields: `ID`, `In`, `SourceGoal`, `Host`,
`Decision`, `Owner`, `Selection`, `Response`, `Route`, `NonOwners`,
`StructuralSignals`, `SemanticSignals`, `Invariant`, `Forbid`,
`Rollback`, and `SourceBoundary`. Rows 001–038 are candidate-semantic
scenarios a future candidate must satisfy; each produces one exact
consequence-bearing result with no `or` owner, no conditional primary
response, and no route sentence masquerading as an owner token. Rows
039–040 are review-process invariants owned by `generic-lifecycle`; the
candidate must not satisfy or explain them. No optional prose field may
silently change a result, and no exact per-scenario action map is
recreated.

`NonOwners` applies to the primary decision only. A token may therefore
appear in `Route` when it owns a separately stated consequence without
contradicting its exclusion from the primary `Decision`/`Owner` tuple.

## Register authority and vocabulary independence

This contract owns every closed vocabulary. The register consumes the
vocabularies and never authorizes its own tokens: a token that appears
only in the register is a defect, not a vocabulary extension. Register
controls: continuous IDs; exact row count; exact field count; no
duplicate or alias owner token; no conditional result; no process row in
candidate obligations; no candidate clause IDs; no target, source, or
Test262 expression; public-safe facts only.

`StructuralSignals` consumes exactly this ordered array:
`multiple-runtime-responsibilities`, `host-language-responsibility-mixing`,
`module-resolution-language-mixing`,
`side-effect-and-pure-transform-mixing`, `implicit-shared-state`,
`mutation-and-aliasing-pressure`, `async-control-flow-fanout`,
`error-contract-scattering`, `data-shape-contract-pressure`,
`dynamic-code-generation`, `prototype-or-metaobject-complexity`,
`compatibility-branching`, `generated-manual-mixing`, `test-seam-absence`,
and `whole-module-review-boundary`. Semantic rows may use `none`; process
rows use `not-applicable`.

`SemanticSignals` consumes exactly this ordered array:
`source-goal-mismatch`, `strict-mode-consequence`,
`coercion-and-equality-surprise`, `property-model-surprise`,
`binding-and-capture-mismatch`, `evaluation-order-side-effects`,
`protocol-contract-mismatch`, `async-completion-ordering`,
`module-semantics-misunderstanding`, `unsupported-or-divergent-syntax`,
`host-api-misattribution`, `security-sensitive-language-mechanism`,
`data-shape-contract-mismatch`, `regexp-runtime-divergence`,
`proxy-invariant-risk`, `finalization-timing-assumption`, and
`annex-b-context-mismatch`. Semantic rows may use `none`; process rows use
`not-applicable`. The register may not derive either array from its own
rows, and each token must be exercised directly or identified as an
architecture-only signal with an explicit reason.

The corrected register directly exercises thirteen structural tokens and
sixteen semantic tokens. `side-effect-and-pure-transform-mixing` and
`test-seam-absence` remain architecture-only because neither changes the
owned consequence in any of the thirty-eight frozen semantic scenarios;
inventing a row occurrence would be coverage padding. Likewise,
`annex-b-context-mismatch` remains architecture-only because the frozen
register has no Annex B consequence scenario. Its explicit source and stop
boundary remains governed by the architecture. These three omissions are
declared coverage, not silent vocabulary growth.

## Structural-policy decision

Disposition C is selected: qualitative
responsibility-and-complexity-first policy with no numeric whole-file
bands. Fifteen named structural signals carry frozen evidence classes,
observable evidence and scope, default response and route, and
false-positive controls in the governing architecture;
`javascript-typescript-boundary-pressure` is merged into
`data-shape-contract-pressure`. APG67 froze a digest before disposition
selection but did not retain its preimage durably. APG68 corrects that
evidence gap with this exact canonical UTF-8 preimage (one LF after every
displayed line, including the last):

```text
APG68 JavaScript structural-policy purpose controls
01 A tiny one-off utility is not automatically architecture-free.
02 A short script with unsafe dynamic-code or host assumptions can be Red.
03 A long generated bundle is not ordinary handwritten growth.
04 A minified or vendored artifact is not refactored as handwritten source.
05 A cohesive library module is not split merely for physical length.
06 A short module mixing CLI, filesystem, parsing, and formatting can already contain multiple responsibilities.
07 ECMAScript module syntax does not make package resolution a language concern.
08 Browser/DOM calls do not become ECMAScript built-ins.
09 Node APIs do not become JavaScript-language ownership.
10 TypeScript adoption is a project-design decision, not a line-count result.
11 Public data-shape and cross-module contract growth may justify a TypeScript route without making JavaScript invalid.
12 A simple user script may remain JavaScript even when Node supplies its host.
13 A .ts, .tsx, or .jsx file does not become a JavaScript whole-file trigger through embedded expressions.
14 Embedded JavaScript retains host whole-file ownership.
15 Configuration JavaScript remains real JavaScript semantic dogfood.
16 Existing large JavaScript uses smallest-safe change and bounded exceptions, not automatic broad rewrite.
```

The preimage is 1,332 bytes and its SHA-256 is
`54248e6141363bcc200dcc1212d36dd9871f99def3cf1cb9b2f7f696c370a25c`.
Line count is
descriptive only. The numeric values rejected with APG50/APG57 are
forbidden, and no normative threshold may be derived from corpus
percentiles or upper tails. A candidate that introduces numeric
whole-file bands violates this contract unless a later accepted decision
changes the disposition first.

## Severity model

- `material`: wrong owner; wrong permission or stop; missing required
  safety or rollback; contradictory normative behavior; rights, privacy,
  or source defect; structurally incomplete policy; false success.
- `ordinary`: wording ambiguity with one clear intended meaning;
  incomplete cross-reference; non-behavioral metadata; navigation,
  formatting, link, or index issue.
- `note`: optional improvement; redundant but noncontradictory
  explanation; benign bookkeeping recommendation.

Exactness is tiered. Exact: primary owner, selection, response severity,
receiving route, permission and stop, safety and rollback, rights,
privacy, and source integrity, and false completion. Not automatically
material: extra explanation, benign bookkeeping, an additional
inspection note, or an additional record action — these become material
only when they change an exact consequence.

## One-correction and corrected-state rules

The review collects the complete initial material set before any
correction; applies at most one coherent architecture correction;
records the corrected artifact hashes and one exact full-index
correction patch with its digest and path set before corrected-state
review; binds every reviewer to the corrected hashes; performs fresh
corrected-state review; and rejects on a genuinely new material defect
after the sole correction. If retained, hashes must match integrated
bytes; if rejected, a compact publication-excluded correction artifact
is preserved before deletion. The original authoring object is never
rewritten.

## Machine-versus-human proof boundary

Machine-checkable claims are narrower than human semantic review, and
every automated check states exactly what it proves. Inherited from the
Markdown evidence corrections, validation evidence must never rely on:

- fixture self-authorization;
- fixture-to-itself expected/actual comparison;
- global token presence as local evidence;
- substring matching inside larger tokens;
- positive-marker-only polarity (a guard must also fail on the negated
  fact);
- loss of a shared subject across coordinated predicates;
- test-order-dependent cache claims;
- missing-versus-present-None conflation;
- claiming complete prose equivalence from bounded lexical guards.

Any APG68 scripted check must be mutation-negative: deleting or negating
the guarded fact must fail the check. Full prose sufficiency remains
human review and is never claimed as mechanically proven. APG67 authors
no maintained parser or test; APG68 decides the executable evidence
design.

## Future review and lifecycle boundary

APG68 independently reverified sources, rights, Test262, targets, and
corpus; parses all forty rows; validates the independent vocabularies;
replays all thirty-eight semantic scenarios; enforces the two process
invariants outside candidate prose; challenges every adjacent-owner
boundary; and terminally rejects ADR 0039 after the sole correction leaves
material semantic defects. It authors no skill and
integrates nothing. Retention and rejection process remains owned by
`generic-lifecycle`: a candidate stays unintegrated until decision,
rejection removes current authority while preserving complete history.
Git, report, catalog, release, and projection operations never become
JavaScript-language clauses.

The corrected proposal is not a future authoring contract. Its mechanical
schema and vocabularies passed, but fresh semantic review found wrong
response precedence, unresolved simultaneous-route semantics, padded signal
applications, and incomplete source boundaries. Any future architecture
requires new authorization and cannot inherit this file as an accepted
oracle.

## Known limitations

- Target whole-file JavaScript dogfood is one small configuration
  module; browser, CommonJS, CLI, generated, minified, and vendored
  classes have no target instance. Two `.cjs` instances occur inside the
  descriptive JavaScript corpus, but CommonJS has no separate class.
- APG68 independently fetched the annual, errata, and Test262 Git objects
  and closed APG67's tree-hash limitation.
- Implementation conformance of any concrete runtime is never
  established by this contract; it always requires version-bound
  evidence from the appropriate owner.
- No JSON adjunct accompanies this contract: the scenario register is
  the single frozen validation artifact, and a machine-readable
  duplicate would add maintenance surface without validation value.
