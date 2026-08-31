# APG Documentation

This index organizes Agentic Praxis Grimoire documentation by the task a
reader is trying to complete. For a product overview and safe first commands,
start with the [root README](../README.md).

## Get started

- [Root README](../README.md) — what APG is, current availability, quick
  start, consumption choices, and release status.
- [APGR CLI reference](reference/cli.md) — command families, exit behavior,
  build information, bridge rules, and safety boundaries.
- [APG distribution](distribution.md) — supported targets, the v0.7 public
  baseline, and the v0.8 candidate package architecture.

The latest published release is v0.7.0. The development tree contains a
v0.8.0 work-stage candidate; v0.8 packages and release artifacts are not yet
published.

## Use the CLI

- [APGR CLI reference](reference/cli.md) is the primary command owner.
- [Public release process](public-release-process.md) covers maintainer-only
  candidate construction and publication boundaries.
- [Structured project defaults](structured-project-phase-defaults.md) covers
  APG phase and reporting conventions.

## Embed the Go library

- [Go library reference](reference/go-library.md) maps the public `schema`,
  `report`, `skills`, `envsnap`, `hotspot`, and additive `footprint` packages.
- [APG–JACA integration boundary](architecture/apg-jaca-integration.md)
  defines the direct-import contract and the one-way dependency rule.
- [v0.7 embeddable toolkit architecture](architecture/v0-7-embeddable-toolkit.md)
  is the complete product architecture.
- [v0.8 context-footprint and skill-inventory contract](architecture/v0-8-context-footprint-and-skill-inventory.md)
  owns the additive APGR program boundary, capacity decisions, and JACA
  handoff pointer.

## Select skills and build task context

- [Skill context bundles](guides/skill-context-bundles.md) documents the
  structured resolver, budgets, fingerprints, and isolated materialization.
- [Skill catalog](../skills/README.md) lists the 39 canonical leaves and their
  maturity.
- [Skill authoring and maintenance](skill-authoring-and-maintenance.md)
  documents repository-owned lifecycle and validation.
- [User-scoped skill integration](user-scoped-skill-integration.md) covers
  public-sourced installation, update, and rollback.

## Produce reporting and evidence

- [Go library reference: reporting](reference/go-library.md#reporting) is the
  primary API owner.
- [Agent reporting architecture](agent-reporting-architecture.md) preserves
  the accepted record, storage, association, and compatibility rationale.
- [APGR CLI reference](reference/cli.md) covers report commands and response
  capture.

## Capture and resolve environments

- [Environment snapshots](guides/environment-snapshots.md) is the primary
  profile, snapshot, storage, and resolution guide.
- [Environment snapshot cutover contract](environment-snapshot-cutover-contract.md)
  defines the separately authorized host-composition boundary.

## Analyze structural hotspots

- [Hotspot analysis](guides/hotspot-analysis.md) documents traversal limits,
  capability levels, metrics, rankings, JSON, and renderers.

Growth and churn analysis is not part of the v0.8 footprint capability.

## Understand distribution and installation

- [APG distribution](distribution.md) is the primary package and target owner.
- [Public release process](public-release-process.md) defines candidate,
  validation, and publication boundaries.
- [User-scoped skill integration](user-scoped-skill-integration.md) covers
  source-qualified skill installation.

## Integrate APG with JACA or another orchestrator

- [APG–JACA integration boundary](architecture/apg-jaca-integration.md)
  separates APG deterministic primitives from JACA orchestration authority.
- [v0.7 embeddable toolkit architecture](architecture/v0-7-embeddable-toolkit.md)
  defines consumer-facing APIs, schemas, and ownership.

APG102 completed disposable JACA cross-consumer qualification without changing
JACA or creating a production dependency. The published v0.7.0 package is now
available for exact-version consumer qualification. The v0.8 footprint surface
remains a candidate until its release and any JACA adoption remains
JACA-owned and separately qualified.

## Review architecture and decisions

- [Architecture directory](architecture/) contains versioned architecture
  contracts.
- [ADR index](adr/README.md) lists accepted, proposed, rejected, and
  superseded decisions.
- [Project model](project-model.md) defines artifact ownership and practice
  lifecycle.
- [Phase and record identity](phase-and-record-identity.md) defines semantic
  phase IDs and independent record sequences.

## Inspect governance, maturity, and debt

- [Project model](project-model.md) is the governance entry point.
- [Skill catalog](../skills/README.md) owns current skill maturity.
- [Known language-profile debt](governance/language-profile-known-debt.md)
  owns the retained CSS and JavaScript qualification debt.
- [Testing and coverage policy](testing-and-coverage-policy.md) defines
  proportional verification and remediation.

## Check release status

- [v0.7 roadmap](v0-7-roadmap.md) preserves the published release sequence.
- [v0.8 roadmap](v0-8-roadmap.md) records the active additive
  context-footprint and skill-inventory work-stage sequence.
- [Project roadmap](roadmap.md) provides the durable cross-release ledger.
- [Status index](status/README.md) lists terminal phase exit records.
- [Public release process](public-release-process.md) owns publication
  procedure and boundaries.

## Explore development history

- [Development releases and phases](history/releases-and-phases.md) preserves
  the former root README chronology as archaeology.
- [Evaluations](evaluations/) contain phase-specific public evidence and
  dispositions.
- [Status index](status/README.md) links terminal outcomes without requiring
  the landing page to act as a ledger.
- [Roadmaps](roadmap.md) preserve dependency order and successor boundaries.
