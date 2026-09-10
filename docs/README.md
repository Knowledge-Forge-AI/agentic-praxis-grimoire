# APG Documentation

This index organizes Agentic Praxis Grimoire documentation by the task a
reader is trying to complete. For a product overview and safe first commands,
start with the [root README](../README.md).

## Get started

- [Root README](../README.md) — what APG is, current availability, quick
  start, consumption choices, and release status.
- [APGR CLI reference](reference/cli.md) — command families, exit behavior,
  build information, bridge rules, and safety boundaries.
- [APG distribution](distribution.md) — supported targets, multi-registry
  distribution, and the complete package architecture.
- [Release notes (v0.10.0)](../release/v0.10.0-notes.md) — version highlights,
  platform status, and compatibility limits.
- [Release notes (v0.9.0)](../release/v0.9.0-notes.md) — preceding release
  highlights and publication reconciliation.

This documentation covers v0.10.0. The retained CI-first interfaces are preserved.
Once this version is published, its packages are available across supported
registries. The preceding **v0.9.0** and **v0.8.1** releases remain frozen.
The [v0.10 roadmap](v0-10-roadmap.md) consolidates the six provisional web profiles.

## Use the CLI

- [APGR CLI reference](reference/cli.md) is the primary command owner.
- `apgr test` (including `--summary-file` and the `policy` mechanical role)
  provides the v0.9 CI qualification interface in APGR Git source checkouts.
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
- [Skill catalog](../skills/README.md) lists the 45 development canonical leaves and their
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
JACA or creating a production dependency. The published v0.9.0 release contains
the complete `footprint` package alongside `schema`, `report`, `skills`,
`envsnap`, and `hotspot`. [JACA CI Integration Handoff](architecture/jaca-ci-handoff.md)
specifies qualification entry points for JACA CI, and [JACA XO Compatibility Handoff](architecture/jaca-xo-handoff.md)
qualifies APGR-owned Go library consumption for JACA XO. Downstream JACA CI registration
and production XO adoption remain consumer-owned and pending; APGR-local qualification
does not equal JACA registration, and the XO consumer fixture is not JACA's production adapter.

## Plan Repo Map support

- [Repo Map support roadmap](repo-map-support-roadmap.md) separates reusable
  v0.10 support from future protocol, graph-quality and migration gates.

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

- [Release notes (v0.10.0)](../release/v0.10.0-notes.md) cover this version and its permanent release contents.
- [Release notes (v0.9.0)](../release/v0.9.0-notes.md) preserve the frozen release description; APG121 records terminal publication.
- [Release notes (v0.8.1)](../release/v0.8.1-notes.md) preserves the published frozen baseline.
- [v0.7 roadmap](v0-7-roadmap.md) preserves the published v0.7 release sequence.
- [v0.8 roadmap](v0-8-roadmap.md) records the completed v0.8.1 context-footprint program.
- [v0.9 roadmap](v0-9-roadmap.md) records the released CI-first program and remaining consumer-owned work.
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

## Qualification limitations

The [known-debt register](governance/language-profile-known-debt.md) and
[ADR 0054](adr/2026/09/0054-js-qd-005-refresh-trigger-interpretation.md)
describe retained qualification limitations and condition-triggered refresh.
The [Repo Map support roadmap](repo-map-support-roadmap.md) is a v0.10.0
deliverable with RM-S0 through RM-S5 intact. Retained debt, qualification
boundaries, and historical outcomes remain preserved in the architecture and
evaluation records.
