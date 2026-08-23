# APG Documentation

This index organizes Agentic Praxis Grimoire documentation by the task a
reader is trying to complete. For a product overview and safe first commands,
start with the [root README](../README.md).

## Get started

- [Root README](../README.md) — what APG is, current availability, quick
  start, consumption choices, and release status.
- [APGR CLI reference](reference/cli.md) — command families, exit behavior,
  build information, bridge rules, and safety boundaries.
- [APG v0.7 distribution](distribution.md) — supported targets and locally
  qualified Python/npm candidate architecture.

The latest published release is v0.6.0. The development tree is a locally
qualified v0.7.0 release candidate; v0.7 packages are not yet published.

## Use the CLI

- [APGR CLI reference](reference/cli.md) is the primary command owner.
- [Public release process](public-release-process.md) covers maintainer-only
  candidate construction and publication boundaries.
- [Structured project defaults](structured-project-phase-defaults.md) covers
  APG phase and reporting conventions.

## Embed the Go library

- [Go library reference](reference/go-library.md) maps the public `schema`,
  `report`, `skills`, `envsnap`, and `hotspot` packages.
- [APG–JACA integration boundary](architecture/apg-jaca-integration.md)
  defines the direct-import contract and the one-way dependency rule.
- [v0.7 embeddable toolkit architecture](architecture/v0-7-embeddable-toolkit.md)
  is the complete product architecture.

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

Growth and churn analysis is not part of the v0.7 capability.

## Understand distribution and installation

- [APG v0.7 distribution](distribution.md) is the primary package and target
  owner.
- [Public release process](public-release-process.md) defines candidate,
  validation, and publication boundaries.
- [User-scoped skill integration](user-scoped-skill-integration.md) covers
  source-qualified skill installation.

## Integrate APG with JACA or another orchestrator

- [APG–JACA integration boundary](architecture/apg-jaca-integration.md)
  separates APG deterministic primitives from JACA orchestration authority.
- [v0.7 embeddable toolkit architecture](architecture/v0-7-embeddable-toolkit.md)
  defines consumer-facing APIs, schemas, and ownership.

Real JACA cross-consumer qualification remains owned by the later v0.7
readiness phase.

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

- [v0.7 roadmap](v0-7-roadmap.md) owns the current release sequence.
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
