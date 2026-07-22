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
