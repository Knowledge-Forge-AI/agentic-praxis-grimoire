# Architecture Decision Records

<!-- APG-CANDIDATE-STATE: css-language-profile retained-provisional -->

The marker above is the mechanical current-state authority. Bounded
contradiction diagnostics cover only their frozen vocabulary; arbitrary prose
still requires human review.

Architecture decision records preserve consequential APG decisions, their
context, alternatives, consequences, and supersession history.

## Path and sequence

Use:

```text
docs/adr/YYYY/MM/NNNN-<slug>.md
```

- `YYYY/MM` is the year and month in which the ADR first enters the repository.
- `NNNN` is a four-digit sequence that advances across the complete ADR tree.
- Select the next value by finding the greatest assigned ADR number and adding
  one; the first value is `0001`.
- An assigned number is stable and is never reused, including after rejection,
  deprecation, supersession, or an explicit file move.
- Each ADR number must be unique within the ADR namespace.
- ADR numbering is independent of the exit-record namespace under
  `docs/status/`.
- Compute the next ADR only from this namespace; do not compare it with an exit
  number. Numeric equality across the two namespaces is valid.

The [phase and record identity guide](../phase-and-record-identity.md) owns
semantic phase IDs, durable references, precommit finalization, and mechanical
identity checks. An ADR does not allocate a phase ID.

## Record contract

An ADR includes a numbered title, status, decision date, context, decision,
alternatives considered, consequences, and explicitly deferred decisions where
applicable. Supported statuses are `Proposed`, `Accepted`, `Rejected`,
`Deprecated`, and `Superseded`. A superseded ADR points to its successor rather
than erasing the earlier decision.

## Index

- [`0001 — Public Projection, Private Evidence, and Agent Reporting Boundaries`](2026/07/0001-public-projection-private-evidence-and-agent-reporting-boundaries.md)
- [`0002 — First Implementation Sequence and Evaluation Baseline`](2026/07/0002-first-implementation-sequence-and-evaluation-baseline.md)
  — Accepted
- [`0003 — Bootstrap Maturity and Superpowers Coexistence`](2026/07/0003-bootstrap-maturity-and-superpowers-coexistence.md)
  — Accepted
- [`0004 — Project-Local Skill Projection and Rollback`](2026/07/0004-project-local-skill-projection-and-rollback.md)
  — Accepted
- [`0005 — Public License and Contribution Governance`](2026/07/0005-public-license-and-contribution-governance.md)
  — Accepted
- [`0006 — v0.2 Objectives, Roadmap, and Maturity Promotion`](2026/07/0006-v0-2-objectives-roadmap-and-maturity-promotion.md)
  — Accepted
- [`0007 — Experimental Karpathy Guidelines Disposition`](2026/07/0007-experimental-karpathy-guidelines-disposition.md)
  — Accepted
- [`0008 — Skill Authoring, Maintenance, and Mechanical Validation`](2026/07/0008-skill-authoring-maintenance-and-mechanical-validation.md)
  — Accepted
- [`0009 — Public Distribution and Reproducible Release Validation`](2026/07/0009-public-distribution-and-reproducible-release-validation.md)
  — Accepted
- [`0010 — Six-Skill Post-Superpowers Stability Dispositions`](2026/07/0010-six-skill-post-superpowers-stability-dispositions.md)
  — Accepted
- [`0011 — v0.3 Workflow, Synthesis, and Modular Guidance Architecture`](2026/07/0011-v0-3-workflow-synthesis-and-modular-guidance-architecture.md)
  — Accepted
- [`0012 — Language Profile Contract and Warning Levels`](2026/07/0012-language-profile-contract-and-warning-levels.md)
  — Accepted
- [`0013 — Repository-Guidance Synthesis and Migration Dispositions`](2026/07/0013-repository-guidance-synthesis-and-migration-dispositions.md)
  — Accepted
- [`0014 — Shell Language and Shell-Test Profile Ownership`](2026/07/0014-shell-language-and-shell-test-profile-ownership.md)
  — Accepted
- [`0015 — Semantic Phase Identity and Record Finalization`](2026/07/0015-semantic-phase-identity-and-record-finalization.md)
  — Accepted
- [`0016 — Nix and Relational-Engine Profile Ownership`](2026/07/0016-nix-and-relational-engine-profile-ownership.md)
  — Accepted
- [`0017 — Approved-Roadmap Manager-Assignment Ownership`](2026/07/0017-approved-roadmap-manager-assignment-ownership.md)
  — Accepted
- [`0018 — v0.3 Readiness, Maturity, and Release Inclusion`](2026/07/0018-v0-3-readiness-maturity-and-release-inclusion.md)
  — Accepted
- [`0019 — v0.3 Release Distribution and Variable Skill-Set Lifecycle`](2026/07/0019-v0-3-release-distribution-and-variable-skill-set-lifecycle.md)
  — Accepted
- [`0020 — Structured Project Phase Defaults and Prompt Compression`](2026/07/0020-structured-project-phase-defaults-and-prompt-compression.md)
  — Accepted
- [`0021 — Python-First Test and Agent-Reporting Architecture`](2026/07/0021-python-first-test-and-agent-reporting-architecture.md)
  — Accepted
- [`0022 — ChatGPT Manager Skill Topology and Personal Hygiene Transition`](2026/07/0022-chatgpt-manager-skill-topology-and-personal-hygiene-transition.md)
  — Accepted
- [`0023 — Python Agent-Report Formats and Git-Record Association`](2026/07/0023-python-agent-report-formats-and-git-record-association.md)
  — Accepted
- [`0024 — Pytest Suite and Coverage Enforcement`](2026/07/0024-pytest-suite-and-coverage-enforcement.md)
  — Accepted
- [`0025 — Go Testing Component and Stack Ownership`](2026/07/0025-go-testing-component-and-stack-ownership.md)
  — Rejected
- [`0026 — Go Testing Component Profiles Without a Stack Owner`](2026/07/0026-go-testing-component-profiles-without-a-stack-owner.md)
  — Accepted
- [`0027 — Version-Bounded matryer/is as an Independent Go Test Component`](2026/07/0027-version-bounded-matryer-is-go-test-component.md)
  — Rejected
- [`0028 — Exceptional v0.4 NOTICE Identity Correction`](2026/07/0028-exceptional-v0-4-notice-identity-correction.md)
  — Accepted
- [`0029 — v0.5 Evidence, Go Testing, and Web Profile Roadmap`](2026/07/0029-v0-5-evidence-go-testing-and-web-profile-roadmap.md)
  — Accepted with amendment
- [`0030 — Dogfood-Grounded Go Testing Component and Composition Ownership`](2026/07/0030-dogfood-grounded-go-testing-component-and-composition-ownership.md)
  — Rejected
- [`0031 — Web and Node Profile-Family Ownership and Authoring Sequence`](2026/07/0031-web-and-node-profile-family-ownership-and-authoring-sequence.md)
  — Rejected
- [`0032 — Agent Report Storage, Project Identity, and Change-Size Policy`](2026/07/0032-agent-report-storage-project-identity-and-change-size-policy.md)
  — Accepted
- [`0033 — Multi-Repository Global Skill Installation`](2026/07/0033-multi-repository-global-skill-installation.md)
  — Accepted
- [`0034 — Web and Node Profile-Family Reconstruction and Authoring Sequence`](2026/07/0034-web-and-node-profile-family-reconstruction-and-authoring-sequence.md)
  — Rejected
- [`0035 — CSS Language Profile and Policy-Selected Structural Limits`](2026/07/0035-css-language-profile-and-policy-selected-structural-limits.md)
  — Rejected
- [`0036 — CSS Language Profile from Frozen Contract`](2026/07/0036-css-language-profile-from-frozen-contract.md)
  — Rejected
- [`0037 — Markdown Language-Profile Architecture and Lean Validation`](2026/07/0037-markdown-language-profile-architecture-and-lean-validation.md)
  — Accepted with amendment
- [`0038 — Markdown Language Profile Candidate`](2026/07/0038-markdown-language-profile-candidate.md)
  — Accepted with amendment
- [`0039 — JavaScript Language-Profile Architecture and Lean Validation`](2026/08/0039-javascript-language-profile-architecture-and-lean-validation.md)
  — Rejected
- [`0040 — JavaScript Language-Profile Core and Layered Decision Model`](2026/08/0040-javascript-language-profile-core-and-layered-decision-model.md)
  — Rejected
- [`0041 — TypeScript Language-Profile Architecture and Compiler-Generation Boundary`](2026/08/0041-typescript-language-profile-architecture-and-compiler-generation-boundary.md)
  — Rejected
- [`0042 — Language-Profile Production Recovery and Iterative Hardening`](2026/08/0042-language-profile-production-recovery-and-iterative-hardening.md)
  — Accepted
- [`0043 — TypeScript Language-Profile Candidate and Intended-State Harness`](2026/08/0043-typescript-language-profile-candidate-and-intended-state-harness.md)
  — Accepted with amendment
- [`0044 — CSS Language-Profile Candidate and Target-First Harness`](2026/08/0044-css-language-profile-candidate-and-target-first-harness.md)
  — Accepted with amendment
- [`0045 — Narrow JavaScript Core Candidate and Target-First Harness`](2026/08/0045-javascript-language-profile-candidate-and-target-first-harness.md)
  — Accepted with amendment
- [`0046 — Node.js Runtime and CLI-Stack Candidate and Target-First Harness`](2026/08/0046-nodejs-runtime-and-cli-stack-candidate-and-target-first-harness.md)
  — Accepted with amendment

APG14 adds no ADR. The v0.2.0 release applies the accepted licensing, roadmap,
distribution, lineage, and maturity decisions in ADRs 0005, 0006, 0009, and
0010 without changing their architecture. APG15 subsequently proposed ADRs
0011 and 0012. APG16 accepts ADR 0011 with a capability-selection,
native-selection, checked-map, duplicate-name, and no-cutover clarification;
APG17 accepts ADR 0013 after the bounded synthesis candidate passes its frozen
scenarios, dogfood inventory, and independent review without source migration.
APG18 accepts ADR 0012 after bounded contract correction, source calibration,
twenty-four frozen Python scenarios, read-only dogfood, and independent review.
APG19 accepts ADR 0014 with separate Bash, Bats, Zsh, and reserved ZUnit
ownership, three provisional implementations, and one source/version deferral.
APG19A accepts ADR 0015 with globally unique semantic phase IDs, independent ADR
and exit sequences, semantic durable references, precommit record finalization,
and deterministic identity checks.
APG21 accepts ADR 0016 with separate Nix, PostgreSQL, and SQLite ownership,
retains provisional PostgreSQL and SQLite leaves, defers Nix, adopts no generic
SQL profile, and grants no live evaluation or mutation authority.
APG21A subsequently corrects the Nix candidate defect and retains that owner
provisionally without changing ADR 0016's ownership or authority decision.
APG22A accepts ADR 0017 after an ordinary-prompting baseline and 30 frozen
clean-context scenarios support one bounded authority-preserving assignment
owner without replacing native writing or existing APG procedure owners.
APG22B subsequently applies ADR 0014's separately authorized legacy re-entry
path, retaining a provisional ZUnit v0.8.2 and Zsh 5.9.2 profile while
excluding the unsupported 5.3.1 pair and every unverified range.
APG23 accepts ADR 0018 after fresh-session discovery, explicit application,
thirteen independent maturity and inclusion reviews, and aggregate readiness
review. These results support eight stable promotions, five retained
provisional rows, and all thirteen v0.3 skills in release scope.
APG24 accepts ADR 0019 and distributes the complete nineteen-skill release set
while retaining source-specific user and subset-preserving project state under
schema version 1. The active integration keeps its aggregate owner, and any
personal-router decommission remains separately authorized after shadow smoke.
APG25 accepts ADRs 0020-0022: project-owned structured defaults and compressed
manager assignments; Python-first reporting plus pytest/xdist/coverage
architecture; and nested ChatGPT-manager ownership with evidence-gated personal
hygiene transitions. Those decisions implement only one bounded existing-skill
correction and defer tooling, test, topology, and private-source migration.
APG27 accepts ADR 0023's design after exact old/new Git-show and compatible
operational characterization. The implementation phase stops partial before
commit because a second release-policy correction is required to preserve
historical v0.3.0 reconstruction; ADR acceptance does not convert that partial
candidate into adopted repository behavior.
APG27A subsequently preserves the partial record, corrects historical policy
and the Red path-safety signal, and adopts the ADR 0023 implementation.
APG28 closes Partial with ADR 0024 still Proposed. Its uncommitted candidate did
not satisfy the full-source component and union branch gates, release-policy
tests, subprocess and worker accounting, or unconditional Bats equivalence.
APG28A preserves that result, corrects the current release-policy, aggregation,
process-accounting, artifact, and coverage defects, retains both Bats owners,
and accepts ADR 0024.
APG30 implements ADR 0022's topology portion with one nested ChatGPT-manager
owner, one provisional subrouter, source-declared lifecycle paths, and
version-bounded historical release compatibility. Its separately accepted
personal-transition architecture remains gated to APG31 and a full application
restart.
APG35 proposes ADR 0025 on an authoring branch without integrating it. APG36
rejects the ADR after fresh independent source and owner review, transient
fixtures for all 154 scenario families, failing-first contracts, and disposable
Go compatibility evidence. All three component contracts need more than one
material correction, and the stack has neither its required native owner nor
independent current value. No proposed Go-testing owner is integrated. This
index previously recorded 0025 as Proposed after that disposition; APG37
corrects the status label without modifying the ADR.
APG37 proposes ADR 0026 on an authoring branch after redesigning the four
deferred candidates from the APG36 defect dossier against reverified current
sources. It proposes three independent component owners and no composition
owner, leaves ADR 0025 Rejected and unreopened, and creates no
`go-testing-stack` artifact. ADR 0026 is not decided, no candidate is
integrated, and development remains 25/25/25.
APG38 accepts a bounded two-owner ADR 0026 after independent source,
owner-graph, structural, compatibility, rights, privacy, and corrected-state
review retains native Go and go-cmp provisionally. Candidate-independent
removal repairs surviving references without creating a stack. The matryer/is
and Nix candidates are deferred after new post-correction material defects.
APG39 proposes ADR 0027 on an authoring branch after redesigning the two
APG38-deferred candidates from their corrected-state defects. It records,
conditionally on later Codex retention of the matryer/is candidate, a third
exact-version-bounded independent Go component that would supersede ADR 0026
only as the complete owner-graph record while preserving every still-valid
ADR 0026 decision. ADR 0026 remains Accepted and controlling; ADR 0025
remains Rejected; no stack artifact is created; and development remains
27/27/27.
APG40 rejects ADR 0027 after corrected-state review finds the matryer/is
candidate's equality mechanism still materially inaccurate after its one
allowed behavior correction. ADR 0026 remains Accepted and controlling; ADR
0025 remains Rejected; no stack artifact appears.
APG43 accepts ADR 0028 as a one-time maintainer-authorized correction of the
v0.4.0 NOTICE identity. It replaces only the named development and public
release objects, preserves v0.1.0-v0.3.0 and the v0.4.0 surface, and restores
append-only behavior for future releases. No v0.5 authority is allocated.
APG44 proposes ADR 0029 on an authoring branch: the v0.5 dependency order,
the evidence-tested Go retention rule, a Node.js runtime owner separate from
the JavaScript and TypeScript language owners, and the web-family ordering.
APG45 accepts ADR 0029 with amendment after removing the false
Node-to-TypeScript implication, adding the TSX boundary, and making React
integration with JSX, MDX, and Astro conditional. It accepts no profile,
creates no mandatory invocation chain, and implements no recommendation.
ADRs 0025-0028 are unchanged, and development remains 28/28/28.
APG48 proposes ADR 0030 on an authoring branch after bounded read-only
dogfood in five public Go repositories under the ADR 0029 evidence rule:
matryer/is as a third exact-version-bounded independent component
(candidate authored, pending Codex review) and no composition stack (fresh
no-independent-value result). It changes no current architecture; ADR 0025
remains Rejected, ADR 0026 Accepted and controlling, ADR 0027 Rejected, and
development remains 28/28/28.

APG49 rejects ADR 0030 after fresh corrected-state review finds new material
behavior defects following its one allowed correction pass. The matryer/is
candidate is deferred and forward removed, ADR 0026 remains Accepted and
controlling, ADR 0025 and ADR 0027 remain Rejected, and no stack exists.
APG50 proposes ADR 0031 on an authoring branch after bounded read-only
inspection of the two Knowledge Forge AI target repositories at exact
commits: seven web/Node candidates architecture-supported, JSX supported
with a recorded target-evidence gap, React and Vitest deferred for missing
dogfood, HTML and the browser/DOM runtime recorded as unowned adjacent
gaps, and bounded later authoring slices proposed. It accepts no profile,
creates no mandatory chain, modifies no prior ADR, and leaves the decision
to independent Codex review; development remains 28/28/28.
APG56 proposes ADR 0034 on a fresh reconstruction branch after verifying the
APG52 reproducible corpus and rights foundation: separate owner-validity,
authoring-eligibility, and growth-band decisions for all ten Web/Node
candidates, a frozen family-balanced band derivation for eight artifact
classes, explicit deferrals for scoped CSS, JSX/TSX, and MDX evidence, Policy
A deferrals for React and Vitest, typed owner-graph and one-count precedence
rules, and a bounded CSS-first authoring-slice sequence. It does not amend
rejected ADR 0031, accepts nothing terminally, authors no skill, and awaits
independent Codex review; development remains 28/28/28.
APG57 independently reviews and rejects ADR 0034 after corrected-state
interval, target-placement, reproduction-gate, one-count-ledger, and scenario
defects. All numeric bands and authoring remain deferred, no authoring slice is
eligible, and Rejected ADR 0031 remains unchanged.
APG58 proposes ADR 0035 on a fresh CSS-only pilot branch: one candidate
`css-language-profile` leaf and specification under explicit policy-selected
300/600/900 structural limits rather than sampled-tail inference, with the
corpus and pinned targets as falsification and legacy evidence only. It
reopens neither rejected ADR, accepts nothing, authors no other profile,
integrates no skill, and awaits separately authorized independent Codex
validation; development remains 28/28/28.
APG59 independently validates and amends that candidate, then rejects ADR 0035
after corrected-state executable-contract and removal defects. The candidate
is removed; development remains 28/28/28, ADR 0031 and ADR 0034 remain
Rejected, and corrected public/active v0.4.0 remain unchanged.
APG61 proposes ADR 0036 on the Claude authoring branch: one fresh
`css-language-profile` candidate leaf, specification, and sixty-case
traceability map authored from the frozen APG60A contract. APG61 is authoring
only — it decides nothing, restores neither rejected ADR, integrates no
surface, and awaits separately authorized APG62 validation; development
remains 28/28/28.
APG62 independently reconstructs all sixty outcomes, applies one coherent
semantic-traceability correction, and rejects ADR 0036 after corrected-state
review finds a new overbroad `record-growth-state` obligation affecting six
frozen cases. All current candidate surfaces are removed; development remains
28/28/28 with 14 stable / 14 provisional, and APG61/APG62 history is preserved.
APG63 proposes ADR 0037 on the Claude architecture branch: Markdown
language-profile architecture with a narrowed owner, closed raw-HTML,
frontmatter, and MDX boundaries, qualitative structure-first structural
policy under pre-frozen purpose controls, and a lean thirty-six-scenario
validation contract. APG63 decides nothing, authors no skill, reopens no
CSS decision, and awaits separately authorized Codex peer review;
development remains 28/28/28.

APG64 independently reviews that exact object, applies one coherent forward
correction, and accepts ADR 0037 with amendment. The current architecture uses
an actual-parser-first source hierarchy, orthogonal selection/response/routing
axes, 34 semantic scenarios plus two process invariants, and qualitative
structure-first policy without numeric bands. Authoring remains separately
authorized; no skill is created or integrated.

APG65 proposes ADR 0038 on the Claude authoring branch: one fresh
branch-only `markdown-language-profile` candidate — leaf, specification, and
navigation-only scenario-coverage record — authored from the accepted
ADR 0037 architecture with no numeric whole-file bands and no current
integration owner. The candidate is authored-proposed-unintegrated and
pending separately authorized APG66 validation; ADR 0037's index status line
above is also corrected here to its APG64-decided state. Development remains
28/28/28.

APG66 independently validates exact APG65, freezes one coherent correction
before fresh review, and accepts ADR 0038 with amendment. The amendment set
closes fence direction, exact tuple navigation, conditional Orange rollback,
move/extraction rollback, exact project-policy routing, and leaf-to-spec
navigation. The retained profile is integrated provisionally at 29/29/29,
14 stable / 15 provisional, with 27 general routes, one ChatGPT-local route,
and 28 checked edges. ADR 0037 remains Accepted with amendment; ADRs 0031,
0034, 0035, and 0036 remain Rejected; public and active corrected v0.4.0 are
unchanged.

APG67 proposes ADR 0039 on the Claude architecture branch: a JavaScript
language-profile architecture and candidate-independent lean validation
contract built from the exact ECMAScript 2026 annual source, with a frozen
forty-row scenario register, disposition C structural policy, and an
`authoring-eligible-with-narrowing` result. JavaScript, TypeScript, and
Node.js remain separate owners; no skill or integration owner is created;
development remains 29/29/29 pending separately authorized APG68 review,
which terminally decides ADR 0039.

APG68 independently delivers exact APG67, reproduces the complete initial
material set, applies one coherent source-authority, vocabulary, routing,
scenario, and evidence-truth correction, then rejects ADR 0039 when fresh
semantic review finds material defects. Eligibility is
`not-applicable-rejected`; no JavaScript skill or integration owner is
created, and APG69 is not recommended or begun.

APG69, under new human authority, proposes ADR 0040 on the Claude
architecture branch: a narrower ECMAScript-core owner, question-specific
typed authorities, a four-layer semantic/structural/policy/effective
decision model with an ordered effective route union, independent
semantic (24), structural (10-signal), composition (8), and process (2)
registers, qualitative structural disposition C, and eligibility
`authoring-eligible-with-narrowing`. ADR 0039 remains Rejected and
unchanged; no skill or integration owner changes; separately authorized
APG70 terminally decides ADR 0040.

APG70 preserves and delivers exact APG69, freezes the complete initial set,
and applies one coherent correction with the actual patch preserved. Fresh
non-author review finds new material source-truth, signal, context-route,
policy-typing, proof, and owner-binding defects. ADR 0040 is Rejected and
eligibility is `not-applicable-rejected`; its architecture and corrected
registers are historical evidence only. No JavaScript skill/integration owner
changes, APG71 is not recommended, and no successor is authorized.

APG71, under separate new human authority scoped to TypeScript architecture
only (APG70's non-recommendation remains controlling for JavaScript
candidate authoring), proposes ADR 0041 on the Claude architecture branch:
an independent TypeScript static-semantics owner under project-selected
exact compiler authority (disposition B), a first-class TypeScript 6/7
compiler-generation boundary, closed `.tsx`/checked-`.js`/embedded-host/
declaration boundaries, a lean candidate-independent contract owning eleven
closed vocabularies, 22 semantic rows, 12 boundary rows, 2 process
invariants, structural disposition D (deferred), and eligibility
`authoring-eligible-with-narrowing`. ADR 0039 and ADR 0040 remain Rejected
(APG71 also corrects this index's stale `Proposed` marker for ADR 0040 to
match APG70's terminal rejection); no skill or integration owner changes;
separately authorized APG72 terminally decides ADR 0041.

APG72 independently preserves exact APG71, reconstructs the oracle, freezes
the complete initial set, and uses one coherent correction. Two fresh
non-author lanes find new material owner/route, role-state, source-kind, and
evidence-state defects, so ADR 0041 is Rejected and eligibility is
`not-applicable-rejected`. No TypeScript skill or current architecture input
exists, and APG73 is not recommended.

APG73 exercises new human governance authority for production recovery rather
than the obsolete TypeScript-candidate meaning of APG73. ADR 0042 accepts a
controlling charter and iterative hardening contract: up to three separately
preserved rounds by default, `repair-required` for repairable remaining
defects, zero Critical/High for integration, explicit human acceptance of
Medium/Low debt, and human authority for terminal rejection or removal.
TypeScript is essential and targets TypeScript 7 as its intended primary
generation; CSS and JavaScript are desirable; temporary TypeScript 6 is
role-bound. All earlier rejected ADRs stay Rejected, no profile is authored or
integrated, and no successor begins.

APG74, the first ADR 0042 product-recovery authoring phase, proposes ADR
0043 on the Claude candidate branch: one narrow TypeScript language-profile
candidate (leaf, specification, and navigation-only 24-scenario coverage)
plus one APG-owned TypeScript 7 intended-state fixture with fourteen cases,
an exact `typescript@7.0.2` pin, and an explicit `not-required` TypeScript 6
compatibility disposition. The candidate is authored-proposed-unintegrated;
ADR 0041 stays Rejected and is not revived; no catalog, projection,
maturity, route, or test owner changes; and separately authorized APG75
terminally decides ADR 0043 under the iterative-hardening contract.

APG75 preserves exact APG74, reconstructs the semantic and fixture oracle, and
uses three separately reviewed correction rounds. The terminal fresh review
finds zero Critical, High, Medium, or Low defects and no accepted debt. ADR
0043 is Accepted with amendment and `typescript-language-profile` is retained
provisionally at 30/30/30, 14/16, and 28/1/29. Historical corrected v0.4,
public and active v0.4.0, Markdown, rejected ADRs, and read-only targets remain
unchanged; no successor is authorized.

APG75A leaves ADR 0043 Accepted with amendment while clarifying that the
reusable profile consumes project-selected compiler and migration policy.
Theme Forge's TypeScript 7 destination remains project-specific; Selection and
the exact four-value Response vocabulary are disjoint; current lifecycle
surfaces agree on provisional integration. No new ADR is created.
APG76 proposes ADR 0044 on the Claude authoring branch: one reusable CSS
semantics profile, one navigation-only twenty-four-scenario coverage record,
one fourteen-case APG-owned target-first fixture, and a deferred
structural-policy disposition. Nothing is integrated, ADR 0035 and ADR 0036
remain Rejected, and the APG61 and APG62 objects are preserved unchanged. APG77
independently reconstructs every expectation and terminally decides ADR 0044
under ADR 0042; Codex may not reject or remove the candidate without human
authority.

APG77 preserves exact APG76 and three immutable correction rounds. Fresh Round
3 review finds two High evidence defects after the default budget is exhausted,
so ADR 0044 remains Proposed at a `repair-required` human checkpoint. CSS is
not integrated, rejected, or removed; development remains 30/30/30, 14/16,
and 28/1/29.

APG77A and APG77B preserve separately authorized evidence corrections without
integration. APG77C then applies explicit proportionality authority, clarifies
the exact private historical-patch exception, and preserves compact v3. Fresh
APG77C review finds six Medium and one Low unaccepted qualification defects, so
ADR 0044 remains Proposed, CSS remains `repair-required` and unintegrated, and
further action requires a new human decision.

APG77D exercises that human decision for exactly four Medium and one Low
qualification limitations, accepts no Critical/High or semantic/source/target/
runtime/release/rollback debt, and closes the live integration, release,
historical-exclusion, and disposable-rollback gates. ADR 0044 is Accepted with
amendment and CSS is retained provisionally with known qualification debt at
31/31/31, 14 stable / 17 provisional, and 29/1/30 routes. Stable maturity
remains blocked by the accepted Medium debt; TypeScript and Markdown remain
provisional, and public/active corrected v0.4.0 and targets remain unchanged.

APG78 proposes ADR 0045 on the Claude authoring branch: one narrow reusable
JavaScript language-profile candidate owning ECMAScript semantics for an
established source region, with Node, browser, module loading, build, and
adjacent-language concerns as explicit non-owners, structural policy deferred,
twenty-four navigation scenarios, and a fourteen-case APG-owned fixture. ADRs
0039 and 0040 remain Rejected and are used only as falsification evidence. APG78
integrates nothing: current development stays at exact APG77D with 31/31/31, 14
stable / 17 provisional, 29/1/30 routes, and the exact CSS known debt. APG79
independently hardens the candidate and terminally decides ADR 0045.

APG79 preserves all three default correction rounds under ADR 0042. Fresh
terminal review of exact Round 3 finds zero Critical, two High, two Medium, and
zero Low material defects, with no accepted JavaScript debt. ADR 0045 therefore
remains Proposed; the candidate is `repair-required-after-round-3`, JavaScript
integration is absent, and exact APG77D development state is unchanged. A new
human continuation decision is required.

APG79A supplies that separate human continuation decision for exactly the four
terminal findings and preserves one immutable correction. Four fresh non-author
lanes find zero Critical, zero High, five Medium, and zero Low material defects:
CommonJS Selection still contradicts the nested-host-only token definition;
target-only commitments remain accepted on non-target rows; actual pytest
failure diagnostics can expose engine output; wrapper-bypass enforcement misses
common aliases; and required path/output mutation evidence is incomplete. ADR
0045 remains Proposed, JavaScript is `repair-required-after-apg79a` and
unintegrated, no debt is accepted, and a new human decision is required.

APG79B supplies that separate human continuation decision for exactly the five
APG79A findings and preserves one bounded correction. Standalone CommonJS
artifacts remain Node-owned with decision-scoped JavaScript `selected`; target
commitments are target-row-only; raw engine streams do not leave the invocation
owner; named process forms are AST-checked; and resolved-path plus complete
output-field mutations reject drift. ADR 0045 remains Proposed, JavaScript is
`repair-required-after-apg79b` and unintegrated, and no debt is accepted.

Fresh immutable APG79B review found four unique Medium defects: the complete
CommonJS stop vector is not closed for both artifacts; traceback locals and
exception context retain raw streams; two further static alias forms bypass the
AST guard; and four root-scalar output contracts lack same-type wrong-value
mutations. Integration is blocked, ADR 0045 remains Proposed, JavaScript remains
repair-required without rejection or removal, and APG80 is not recommended.

APG79C supplies the explicit human product decision allowed by ADR 0042 for
exactly those four Medium qualification limitations, now identified as
`JS-QD-001` through `JS-QD-004`. All four block stable maturity but do not block
provisional integration under their exact operating restrictions. No Critical,
High, semantic, normative-source, target-fact, owner, release, or rollback debt
is accepted. ADR 0045 remains Proposed and JavaScript remains unintegrated until
every ordinary product gate passes.

Fresh APG79C preflight found the current official Test262 `main` identity
differs from the APG79B terminal and APG79C baseline identity. Test262 is
non-normative rights-only evidence and unused as an oracle, but the discrepancy
is one separate unaccepted Medium source-evidence defect. Integration is
blocked, ADR 0045 remains Proposed, JavaScript remains repair-required and
unintegrated, and APG80 is not recommended.

APG79E accepts exactly one additional Medium supporting qualification
limitation, `JS-QD-005`, under explicit human authority. The maintained proxy
still does not directly bind the APG79B managed report; direct current report
verification is the workaround. With zero Critical, High, or unaccepted
Medium/Low findings and every ordinary integration gate green, ADR 0045 is
Accepted with amendment. JavaScript is provisionally integrated with exactly
`JS-QD-001` through `JS-QD-005`; stable maturity remains blocked.

APG80 proposes ADR 0046 on a Claude authoring branch: one narrow reusable
`nodejs-runtime-profile` candidate, its specification, a navigation-only
twenty-four-scenario coverage record, and a fourteen-case APG-owned target-first
Node fixture. The candidate consumes runtime roles and selects none; it
hard-codes no Node version, treats a declared range, a package-manager
declaration, a continuous-integration release line, an exact version, and an
invocation as separate facts, and defers structural policy entirely. It owns no
ECMAScript or TypeScript semantics, no package-manager or shell behavior, and no
operating-system, network, security, build, or deployment completion. APG80
integrated nothing, added no debt, preserved `CSS-QD-001` through `CSS-QD-005`
and `JS-QD-001` through `JS-QD-005` exactly, and left the mainline at the exact
APG79E terminal. At that checkpoint, ADR 0046 remained Proposed; a separate
Codex phase was required to independently reconstruct every expectation before
the decision.

APG81 preserves three immutable correction rounds under ADR 0042. Fresh
terminal review leaves zero Critical, three High, two Medium, and zero Low
qualification-harness findings. At that checkpoint, no Node debt was accepted,
ADR 0046 remained Proposed, `nodejs-runtime-profile` was
`repair-required-after-round-3` and unintegrated, and a new human continuation
decision was required.

APG81A exercises that human continuation decision, retires the disproportional
immutable-flag and copied-runtime experiment, and completes a fresh zero-
finding controlled-local-or-CI harness correction with zero Node debt. Its
later integration candidate stops on one High rollback defect and one Medium
ADR-index defect. At that checkpoint, ADR 0046 remained Proposed and Node
remained unintegrated.

APG81B clarifies that future candidate-preserving rollback targets 33/32/32,
then stops its complete integration candidate on three Medium staged-review
defects with zero Node debt. All attempted integration bytes are removed. The
then-current index retained one adjacent Proposed status for ADR 0046; no
rejection, acceptance, integration, or candidate removal occurred.

APG81C preserves the reviewed lifecycle, review-sequencing, xdist, and ignored-
scratch support correction but stops before integration after one immutable-
review Medium. APG81D reconstructs integration and stops at C0/H1/M3/L0.
APG81E reconstructs the complete final integration candidate and stops at
C0/H1/M2/L0 because rollback test ownership remains incomplete and self-
attested, phase chronology is misplaced, and fresh Node release-schedule
identities are absent from the phase evidence. All APG81E integration bytes are
discarded. At that checkpoint, ADR 0046 remained Proposed with the candidate
retained, repair-required, and unintegrated; no Node or scratch debt was
accepted.

APG81F attempts the single authorized actual-test-projection, chronology, and
fresh source-evidence correction. Frozen review returns C0/H3/M2/L0, so the
attempted correction bytes were discarded and ADR 0046 remained Proposed. Node
remained retained, repair-required, and unintegrated with zero accepted Node or
scratch debt at that checkpoint.

APG81G exercised the next explicit human continuation. Fresh review of its one
correction found two High and four Medium defects, so all attempted
implementation and test bytes were discarded. At that checkpoint, ADR 0046
remained Proposed and Node remained retained, repair-required, and
unintegrated.

APG81H was the next explicit human continuation. Fresh review of its single
bounded correction found one Medium defect: the evidence did not bind the
complete actual language-profile lifecycle map. Attempted implementation and
test bytes were discarded before commit. At that checkpoint, ADR 0046 remained
Proposed and Node remained retained, repair-required, and unintegrated.

APG81H final resume preserves that checkpoint and the immutable lifecycle-map
and test-isolation corrections. The integration candidate selects ADR 0046 as
Accepted with amendment and provisionally integrates Node in intended State A.
The bounded coverage continuation closes the superseded integration branch-
coverage failure without changing production lifecycle/topology or coverage
policy. The replacement-control continuation preserves production replacement
suppression, and historical corrected-v0.4 qualification is bound to exact
immutable identity and prior evidence while current-runtime replay remains
`DIAGNOSTIC_NONQUALIFYING`. State A and candidate-preserving State B are
mechanically qualified; final Sol and Claude review remains an external commit
gate and is not self-attested by the tree. Node and scratch debt remain zero.
Stable maturity, readiness, publication, deployment, and successor work remain
outside this decision.
