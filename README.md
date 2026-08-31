# Agentic Praxis Grimoire

<!-- APG-CANDIDATE-STATE: css-language-profile retained-provisional -->

## What is Agentic Praxis Grimoire?

Agentic Praxis Grimoire (APG) is a provider-neutral toolkit and skill corpus
for bounded agent engineering. It gives coding-agent systems reusable,
deterministic primitives for selecting task guidance, collecting evidence,
resolving curated environments, and inspecting repository structure without
dictating an orchestration workflow.

APG includes:

- reusable Go packages for schemas, reports, skill bundles, environment
  snapshots, hotspot analysis, and context-footprint records;
- the `apgr` command-line interface;
- 39 canonical agent skills that can be selected for one task;
- canonical reporting and evidence formats;
- thin Python and npm compatibility/distribution adapters; and
- repository-maintenance tools used to develop APG itself.

APG is not an autonomous orchestrator. It does not choose a model, reviewer,
roadmap, retry policy, or authorization boundary. Orchestrators such as Joint
Agentic Command Aegis (JACA) decide when and how to invoke APG.

## Why use APG?

APG separates reusable engineering mechanics from provider and workflow
policy. That makes the mechanics easier to embed, test, reproduce, and audit.

- **Small task context.** Select only the relevant skills instead of injecting
  a global corpus into every agent session.
- **Deterministic evidence.** Produce canonical Git, diff, and operational
  records with stable identities.
- **Embeddable primitives.** Call public Go packages in-process without
  launching `apgr`, Python, or a shell.
- **Explicit environment inputs.** Capture an allowlisted, non-secret
  environment and resolve it with recorded provenance.
- **Honest structural signals.** Rank repository hotspots while distinguishing
  deep metrics, structural metrics, and unavailable capabilities.
- **One portable semantic owner.** Keep portable behavior in Go while Python
  and npm remain thin compatibility front doors.

## Concrete use cases

Use APG to:

- expose the Markdown and pytest guidance needed for one coding task, and
  nothing else;
- generate deterministic commit or worktree evidence for a review;
- consume report records directly from a Go service or JACA adapter;
- capture a curated build environment once and resolve it in-process later;
- identify complex or structurally important files before a bounded refactor;
- use the same `apgr` interface from a source checkout, Go build, Python
  package, or npm package; and
- retain APG-specific repository checks without moving portable semantics back
  into Python.

APG does not generate autonomous refactoring plans, analyze Git growth or
churn, choose a model, or advance a roadmap.

## Quick start

The latest published release is **v0.7.0**. The source tree contains the
**v0.8.0 work-stage candidate**; it is not yet published to GitHub, PyPI, npm,
or Go-module readback.

To try the work-stage candidate safely from a source checkout, use Go 1.25:

```sh
go run ./cmd/apgr --help
go run ./cmd/apgr skills list
go run ./cmd/apgr skills context-report
go run ./cmd/apgr footprint --help
```

These commands read the embedded corpus and do not modify a global skill root.
To scan the current checkout without executing its source:

```sh
go run ./cmd/apgr --repository "$PWD" analyze hotspots \
  --include-path cmd/apgr --format terminal
```

The scanner requires an absolute physical repository path, stays beneath that
root, and does not follow symlinks.

For the published v0.7 Python release:

```sh
python -m pip install "agentic-praxis-grimoire==0.7.0"
apgr --version
```

The v0.8.0 candidate is not yet available from a public package registry.

## Install and consumption choices

### Go library

The module path is:

```text
github.com/Knowledge-Forge-AI/agentic-praxis-grimoire
```

Its public root packages are:

- `schema` — shared version and envelope constants;
- `report` — canonical Show, Diff, Operational, parsing, and optional
  publication APIs;
- `skills` — embedded corpus, deterministic resolution, and isolated
  materialization;
- `envsnap` — strict profiles, snapshots, storage, loading, and resolution;
- `hotspot` — bounded structural analysis, stable models, and renderers; and
- `footprint` — deterministic context-footprint records, comparisons,
  projections, measurements, and versioned component/control registries.

JACA-style consumers should import these packages directly. See the
[Go library reference](docs/reference/go-library.md).

### Go CLI

`cmd/apgr` exposes these principal command families:

```text
apgr build-info
apgr report ...
apgr skills ...
apgr env ...
apgr analyze hotspots ...
apgr footprint measure|compare|project ...
apgr response ...
```

The CLI is an adapter over the same Go owners. Repository-maintenance commands
and compatibility routes are documented separately in the
[CLI reference](docs/reference/cli.md).

### Python

The Python distribution remains `agentic-praxis-grimoire`, with the `apgr`
console entry point and `python -m agentic_praxis_grimoire`.

Portable commands delegate to a verified bundled Go binary. Python continues
to own APG repository and host maintenance where that behavior is intentionally
not portable. The published v0.7 platform wheels and source distribution remain
the latest public Python surface; v0.8.0 packaging is a work-stage candidate.

### npm

The published v0.7 architecture defines:

- `@knowledge-forge-ai/apgr`;
- `@knowledge-forge-ai/apgr-darwin-arm64`;
- `@knowledge-forge-ai/apgr-linux-x64`; and
- `@knowledge-forge-ai/apgr-linux-arm64`.

The v0.7 packages are the latest published npm surface. The v0.8.0 candidate is
not published. The JavaScript launcher selects and verifies a same-version
platform package, forwards exact arguments with no shell, and owns no APG
semantics.

### Nix and host integration

Nix, shell composition, and host activation are consumer layers. They may
package or activate APG, but they do not own APG runtime semantics. There is
no APGR-local Nix release gate for the v0.8.0 candidate, and this work changes
no Nix configuration, active installation, or host integration.

See [APG distribution](docs/distribution.md) for the target matrix, artifact
architecture, verification, and publication boundary.

## Core concepts

### Canonical skill corpus

APG has 39 canonical leaves: 14 stable and 25 provisional. Canonical Markdown
under `skills/` is the maintained body authority; embedded metadata and
package resources are verified projections of it.

### Explicit, task-scoped selection

The structured resolver uses explicit skill IDs and closed, versioned facts.
It selects only exact owners. Composition edges describe relationships among
already selected skills; they never create an implicit mandatory profile
chain.

Resolved bundles can remain in memory or be materialized beneath a
caller-owned, disposable root. APG never injects a bundle into a global skill
root. See [skill context bundles](docs/guides/skill-context-bundles.md).

### Reproducible context budgets

APG measures descriptions, bodies, fixed prompt overhead, and initial context
in bytes. It fails closed on an exceeded bound rather than truncating a
description or silently dropping a skill. Provider-specific tokenization and
provider limits remain consumer-owned.

### Context footprints

The additive `footprint` package measures selected descriptions, selected
bodies, support material, prompt overhead, and complete materialized bundles as
separate components. Its records use the versioned
`apg.context-footprint/v1`, `apg.context-comparison/v1`, and
`apg.context-projection/v1` schemas. Canonical bytes and domain-separated
fingerprints are deterministic; unavailable metrics remain unavailable and are
never represented as zero. APGR bundle accounting is not provider prompt
accounting or JACA total-context accounting.

Footprint operations are provider-neutral and do not execute tokenizers,
providers, credentials, routes, retries, or workflow transitions. Provider-
specific observations may be supplied as explicitly identified metrics, or
recorded as unavailable.

### Evidence and reporting

Canonical report records carry versioned schemas, stable IDs, deterministic
bytes, and caller-owned evidence copies. The Go API supports in-memory use;
optional outbox publication adds owner-only paths, bounded locking, recovery,
and atomic replacement. See the [reporting reference](docs/reference/go-library.md#reporting).

### Environment snapshots

Environment profiles are strict and allowlisted. Secret-like names are
rejected, snapshot storage is owner-only, and canonical JSON records values
with validators and provenance. `Isolated` resolution starts empty;
`Overlay` explicitly adds a caller-owned base. See the
[environment snapshot guide](docs/guides/environment-snapshots.md).

### Hotspot analysis

The analyzer reports deep Go metrics and honest structural or unavailable
capability levels for other supported surfaces. It does not execute target
source, follow symlinks, or inspect Git history. Rankings are deterministic
within one report. See the [hotspot guide](docs/guides/hotspot-analysis.md).

### Strangler and compatibility architecture

Portable report, skill, environment, hotspot, and response behavior has one Go
semantic owner. Python and npm adapters locate, verify, and invoke that owner.
APG-specific repository or host maintenance remains Python-owned where the
boundary is explicit.

### Provider neutrality and safety boundaries

APG has no model or provider selection authority. Normal Go process adapters
use exact argument vectors and no shell. Task skills use isolated roots rather
than global context injection. Environment snapshots reject secret-like names.
Report and response publication use bounded path, mode, locking, and atomicity
checks. These are concrete safety properties, not a claim of formal security
assurance.

## JACA and library integration

APG supplies deterministic engineering primitives and guidance. JACA supplies
orchestration: attempts, sequencing, provider selection, retries,
authorization, evidence lifecycle, and decisions about what to do next.

The intended dependency points one way:

```text
JACA-owned adapter
    -> APG public Go package
```

APG never imports JACA or accepts JACA protocol types. A JACA adapter passes a
`context.Context` and structured APG requests, then translates returned APG
models and bytes into JACA-owned evidence.

APG102 qualified this integration shape through a disposable JACA-owned adapter
without modifying JACA or creating a production dependency. The published
v0.7.0 package is available for exact-version consumer qualification. The v0.8
footprint records remain an additive work-stage candidate; any JACA adoption
still belongs to a JACA-owned adapter and separately qualified consumer work.
See the [APG–JACA integration boundary](docs/architecture/apg-jaca-integration.md).

## Documentation

Start with the [task-oriented documentation index](docs/README.md).

- [CLI reference](docs/reference/cli.md)
- [Go library reference](docs/reference/go-library.md)
- [Skill context bundles](docs/guides/skill-context-bundles.md)
- [Environment snapshots](docs/guides/environment-snapshots.md)
- [Hotspot analysis](docs/guides/hotspot-analysis.md)
- [Distribution and packaging](docs/distribution.md)
- [APG–JACA integration](docs/architecture/apg-jaca-integration.md)
- [Project model and governance](docs/project-model.md)
- [Roadmaps and current status](docs/roadmap.md)
- [Development releases and phases](docs/history/releases-and-phases.md)

## Project status

- Latest published release: **v0.7.0**
- Development version: **v0.8.0 work-stage candidate**
- Candidate corpus: **39 canonical / 39 catalog / 39 projections / 39
  discoverable**
- Maturity: **14 stable / 25 provisional**
- Skill-candidate decision: **zero new skills**; RepoMap and Theme Forge queues
  remain deferred
- CXT2B diagnostic importer: **deferred and non-blocking**
- Readiness: **implementation and qualification candidate pending dispatcher
  pre-final review**
- Publication: **v0.8.0 has not been published**; Git finalization and
  immutable external readback remain closeout actions

The published v0.7.0 release remains the historical base for this candidate.
Its public package and module surfaces are not changed by the v0.8 work-stage
candidate. See the [v0.7 roadmap](docs/v0-7-roadmap.md),
[status index](docs/status/README.md), [skill catalog](skills/README.md), and
[known language-profile debt](docs/governance/language-profile-known-debt.md).

## Contributing and licensing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before proposing changes. Contributors
must follow the project's authority, provenance, testing, and review
boundaries, and contribution may require the
[Contributor License Agreement](CLA.md).

APG is available under [GNU GPLv3](LICENSE) or a separately negotiated
commercial license. Required third-party notices are recorded in
[NOTICE](NOTICE).
