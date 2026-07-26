# Architecture Decision Records

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
