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

APG14 adds no ADR. The v0.2.0 release applies the accepted licensing, roadmap,
distribution, lineage, and maturity decisions in ADRs 0005, 0006, 0009, and
0010 without changing their architecture.
