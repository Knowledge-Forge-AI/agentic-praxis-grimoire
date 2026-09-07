# APGR v0.8 Context-Footprint and Skill-Inventory Contract

## Status and authority

This contract integrates the accepted APGR-owned dispositions for the v0.8
capability, context-footprint, and skill-inventory program. It preserves the
v0.7 architecture and records the two independently owned program entries
delivered in canonical phase `APG104`: `APGR-CAP0` and `APGR-CXT0`.

The direct bounded operator assignment authorizes the complete v0.8 program
recorded here: CAP0, CXT0, the first-party implementation and integration
entries, qualification, candidate preparation, and post-review release work.
The labels are program entries, not phase identities. This contract is
additive, selects no new skill, and changes no provider, security-policy, JACA,
or host state.

The current release facts are:

*(Post-phase note, 2026-09-06: v0.8.1 publication, readback, and private repository reconciliation completed in phases APG107 and APG108; see `private/releases/v0.8.1/reconciliation1-evidence/` and [v0.9 Roadmap](../v0-9-roadmap.md). The contemporaneous phase-local status below is preserved as historical record.)*

- public v0.8.0 remains the released Git and Go-module baseline;
- GitHub Releases, PyPI, and npm do not contain v0.8.1;
- the prepared v0.8.1 source contains the additive `footprint` package and the
  six-package Go boundary (`schema`, `report`, `skills`, `envsnap`, `hotspot`,
  and `footprint`); and
- source freeze, final asset reconstruction, and registry publication remain
  separate successor boundaries over immutable public v0.8.0.

[Accepted ADR 0051](../adr/2026/08/0051-v0-7-embeddable-toolkit-architecture-and-roadmap.md)
continues to own that v0.7 package architecture. V0.8 work is additive unless
a separately authorized decision explicitly versions a breaking change.

## Decision inputs

This contract terminally dispositions the amended APGR capability/context and
skill-inventory proposal and the APGR-owned rows of the amended JACA integration
proposal. Their reviews remain advisory evidence. Current v0.7 architecture,
APG102 readiness evidence, and the direct public package APIs control factual
claims where proposal text differed. This contract is self-contained and does
not create a runtime or publication dependency on the proposal archive.

## Product boundary

APGR may own reusable guidance, deterministic selection, bounded analysis,
canonical APGR-domain records, exact accounting for APGR-owned material,
reference-preserving projections, narrow import adapters for pinned external
formats, deterministic rendering, and validation.

APGR does not own provider execution, authentication or fallback, attempts,
routes, retries, notifications, workflow progression, credentials, network or
role policy, process confinement, consumer retention enforcement, or JACA
control-protocol types. APGR output is evidence. It cannot authorize work,
change scope, select a route, accept a finding, or advance a workflow.

Task-scoped materialization remains isolated and consumer-controlled. APGR does
not mutate operator-global provider, profile, MCP, or skill state.

## Terminal APGR dispositions

These dispositions supersede the proposal-local APGR-D1 through APGR-D19 table
as APGR canon. The source proposals and reviews remain evidence, not runtime or
implementation authority.

| ID | Disposition | Canonical action |
| --- | --- | --- |
| `APGR-D1` | Accepted | Retain the provider-neutral deterministic-library boundary stated above. |
| `APGR-D2` | Accepted | Preserve in-memory use and isolated task-scoped materialization; forbid global configuration authority. |
| `APGR-D3` | Amended | Preserve the v0.7 corpus-integrity control under its historical identity. CAP0 may define separately named, versioned controls only after consumer-grounded measurement; no change remains a valid outcome. |
| `APGR-D4` | Amended | Keep capacity, candidate evaluation, footprint implementation, external adapters, qualification, and release as separately authorized work. |
| `APGR-D5` | Narrowed | Make footprint, evidence basis, comparison, and reference-preserving projection observable. Generic cross-agent handoff is not a v0.8 core feature. |
| `APGR-D6` | Accepted | APG104 accepts the additive `footprint` package and its footprint, comparison, and projection schema identities; later API and release work remains separately qualified. |
| `APGR-D7` | Narrowed | Retain a diagnostic importer only as optional `APGR-CXT2B`, gated by a pinned format version, reproducible fixtures, an allowlist, and fail-closed mapping. |
| `APGR-D8` | Rejected | Do not embed or distribute a model runtime, proxy, browser, memory service, credential router, provider launcher, or general MCP suite. |
| `APGR-D9` | Deferred | Add no generic brevity, context-economy, or third-party-product skill in the initial program. |
| `APGR-D10` | Amended | Treat graph-quality guidance only as a candidate hypothesis. CAP0 chooses an ordering criterion; a later start decision names at most one candidate. |
| `APGR-D11` | Deferred | Retain versioned-protocol guidance as an independent candidate hypothesis with no authority inherited from graph-quality work. |
| `APGR-D12` | Accepted | Reconcile ownership, stable identity, aliases, and supersession before any candidate authoring. |
| `APGR-D13` | Deferred | Require repeated evidence and class-specific prerequisites for later RepoMap-derived candidates. |
| `APGR-D14` | Narrowed | Retain the Theme Forge inventory only as a non-authoritative hypothesis queue; reclassify and re-cost every candidate before ordering. |
| `APGR-D15` | Rejected | Do not encode one project, product stack, or current plan as broad reusable guidance without independent ownership evidence. |
| `APGR-D16` | Amended | Bind selection results to corpus version, rule identity, and change class; selection-affecting changes require a new corpus identity and consumer requalification signal. |
| `APGR-D17` | Accepted | Preserve the five-package v0.7 public Go boundary; future package work is additive unless separately versioned as breaking. |
| `APGR-D18` | Amended | Require a substantive independent public-package consumer fixture as the primary new-package release gate; JACA qualification is additional evidence and is non-gating unless the shared register explicitly changes that allocation. |
| `APGR-D19` | Superseded | The prior entry-eligibility wording is superseded only by APG104's direct bounded operator authority for this delivery; it grants no general, automatic, or successor authority. |

## APG104 phase and entry identity

`APG104` is the canonical semantic delivery phase for this bounded v0.8
architecture and implementation slice. `APGR-CAP0` and `APGR-CXT0` are
independent ownership labels within that phase. They are not alternate phase
IDs, do not merge their evidence, and do not authorize one another's future
work. CAP0 supplies the terminal control taxonomy and mapping input that CXT0
consumes; CXT0's schema and projection decisions do not transfer ownership to
JACA or to a provider.

APG104 records the bounded v0.8 program under the direct operator assignment.
CAP0, CXT0, CXT1, CXT2A, CXT3, CXT4, Q1 fixture authoring, and source/distribution
integration are implemented in the work-stage candidate. This contract does
not claim v0.8.1 publication, deployment, or public-registry readback. The
candidate's final commit and asset identities belong to the later source-freeze
phase and are intentionally not recorded here.

## CAP0 contract

`APGR-CAP0` owns capacity, selection identity, and skill-inventory governance.
Within APG104 it has two terminal responsibilities:

1. Re-attest the published and development baselines, distinguishing corpus
   integrity, structured discovery, ambient discovery, selected descriptions,
   selected bodies, support material, and materialized context.
2. Decide the control taxonomy, identity and compatibility rules, candidate
   classes and ordering criterion, stable skill IDs and supersession, and the
   mapping needed by CXT0.

CAP0 must evaluate retention/no change, a separately versioned guard, per-
surface controls, replacement-only growth, and description normalization as
combinable options. Queue size is inadmissible evidence for relaxing a control.
Description, body, support-resource, and consumer-total-context measurements
remain separate. APGR may decide whether an APGR bundle meets an APGR policy;
it does not claim that the consumer's full provider context fits.

Skill candidates use an explicit compatibility class. A hole-filling candidate
that can change an existing valid selection is selection-affecting. A
vocabulary-extending candidate may be additive for historical requests, but
the new capability still requires qualification. A CAP0 recommendation does
not start candidate authoring.

### CAP0 baseline and terminal decisions

CAP0 re-attests the current public v0.7 baseline and keeps these surfaces
separate:

| Surface | Current value | Interpretation |
| --- | ---: | --- |
| Canonical skills | 39; 14 stable / 25 provisional | Complete current skill inventory; zero candidates are selected or authored. |
| Description discovery | 9,504 UTF-8 bytes; 9,492 characters | Current canonical discovery description measurement. |
| Historical integrity control | 9,527 UTF-8 bytes; 23 bytes of headroom | Preserved v0.7 integrity limit, not a new v0.8 per-skill budget. |
| Semantic skill bodies | 483,778 bytes | Semantic skill-body accounting surface, separate from descriptions and support. |
| Full skill material | 495,319 bytes | Full skill accounting surface, not a replacement for consumer context measurement. |
| Repository-only support | 13,074 bytes | Repository-support accounting surface, excluded from semantic skill-body totals. |

The canonical corpus fingerprint is
`0509803b3c12e0366917a341c9d56945d7966897953415acf0c997254e1331c`.
These values are public release facts and do not expose private evidence paths
or development identities.

CAP0 preserves the historical 9,527-byte integrity control and introduces no
new 250-byte guard, per-skill default discovery cap, or equivalent implicit
selection rule. A description, body, support-resource, selected-bundle, or
consumer-total-context measurement remains its own named surface. Queue size
cannot relax a control. Candidate queues remain deferred, including
hole-filling, vocabulary-extension, graph-quality, versioned-protocol,
RepoMap-derived, and Theme Forge hypotheses; the current candidate count is
zero.

Stable skill IDs, control IDs, component IDs, corpus identity, and supersession
relations are explicit and versioned. They do not depend on list position,
description text, queue order, or a newly selected candidate. CAP0 publishes a
versioned control mapping for CXT0; it does not mutate the catalog, projection,
or current skill inventory.

The built-in control identities are
`apg.capacity-control/corpus-integrity/v1`,
`apg.capacity-control/selected-discovery/v1`,
`apg.capacity-control/selected-body/v1`,
`apg.capacity-control/support-material/v1`,
`apg.capacity-control/materialized-bundle/v1`,
`apg.capacity-control/prompt-overhead/v1`, and
`apg.capacity-control/consequence-bearing/v1`. They are mapped through
`apg.capacity-control-mapping/v1`; a future control is additive only when its
identity and compatibility rule are explicit.

## CXT0 contract

`APGR-CXT0` owns architecture for APGR-domain footprint, comparison, and
projection records. Within APG104 it defines:

- versioned canonical schemas, serialization, digest identity, and historical
  decoding behavior;
- orthogonal observation basis, study design, quality status, availability,
  and metric/unit identity;
- a versioned component-kind registry and a separate mapping to CAP0 control
  identities;
- exact unavailable states rather than synthetic zeroes;
- comparison registration, workload/control/treatment identities, method,
  exclusions, and unit compatibility;
- projection fidelity, permitted loss, canonical-source identity, omitted
  content, consequence-bearing fields, sensitivity, and retention labels;
- source traceability and noncompetition with existing APGR response records;
- a substantive immutable external-consumer fixture; and
- the disposition and public-support posture of any optional importer.

Missing is never zero. Unknown versions, fields, units, evidence bases,
component mappings, or comparison identities fail closed. A projection never
replaces its canonical source and must disclose every permitted omission.
Sensitivity and retention are labels APGR validates and propagates; the
consumer remains responsible for storage, access, transmission, and disposal.

Within APG104, CXT0 freezes the additive `footprint` package boundary and the
following independent schema identities:

- `apg.context-footprint/v1` — canonical observation and component record;
- `apg.context-comparison/v1` — exact control/treatment comparison;
- `apg.context-projection/v1` — source-bound derived record;
- `apg.context-component-registry/v1` — versioned closed component vocabulary;
  and
- `apg.capacity-control-mapping/v1` — versioned mapping from component kinds
  to CAP0 controls.

### Canonical serialization and identities

Every canonical JSON record is strict UTF-8 JSON with one trailing line feed,
no trailing data, explicit field vocabulary, deterministic field/array order,
and integer metrics. Unknown schema versions, fields, vocabulary values, units,
or control mappings fail closed. A missing or unavailable metric has an
explicit availability/reason state and no value; it is never represented by a
synthetic zero. Zero is valid only as an observed integer value.

Footprint, comparison, and projection fingerprints are separate,
domain-separated SHA-256 identities (`fp`, `cmp`, and `proj` domains). A digest
from one domain cannot be reused as an identity in another. Source references
bind exact URI, media type, size, and digest facts without granting APGR fetch,
network, or provider authority.

### Observation, component, and control dimensions

An observation records basis, study design, quality, availability, method,
provider label, harness, repetition count, workload/variant, exclusions, and
metric/unit identity. The closed component registry is versioned independently
from the CAP0 control mapping. Component kinds and control identities are
stable strings, and a record cannot silently substitute one mapping version for
another.

### Exact comparison

`apg.context-comparison/v1` compares one corresponding component from a
control record and a treatment record. Component kind, name, control identity,
unit, schema, and compatible observation dimensions must match. The result is
the exact integer treatment-minus-control delta. Unit conversion, unavailable
metric substitution, rounding, inferred correspondence, and synthetic zeroes
are refused. Unknown or mismatched identities fail closed.

### Source-bound projection

`apg.context-projection/v1` is a derived record, never a replacement for its
canonical source. It retains the canonical source schema, digest, and size;
declares fidelity (`exact`, `lossless_structural`, or `summarized_lossy`);
enumerates every omitted field; and preserves consequence-bearing fields.
Omission of consequence-bearing content, an unbound source, a sensitivity
downgrade, or a retention downgrade is refused. The projection may disclose
less only when that loss is explicit and validated against its source identity.

Sensitivity is one of `public`, `internal`, `confidential`, or `restricted`.
Retention is one of `ephemeral`, `task_scoped`, `retained`, or `immutable`.
APGR validates and propagates both labels; the consumer remains responsible
for access control, storage, transmission, and disposal.

The first-party path must not depend on a third-party diagnostic format:

```text
APGR-CXT0
    -> APGR-CXT1 footprint core
        -> APGR-CXT2A first-party measurement
            -> APGR-CXT3 bounded projections

APGR-CXT2B optional external importer (non-blocking)
```

None of these successor entries begins through this contract. The optional
`APGR-CXT2B` external importer remains deferred for every missing gate,
including pinned format identity, rights, reproducible fixtures, allowlisted
mapping, failure behavior, and an independent consumer disposition.

## Public-package and consumer qualification doctrine

The released-version rule is fail closed: a production consumer pins an exact
published APGR semantic version and module sums. A mutable branch, development
replacement, private source copy, or internal package is not a released
dependency. The live public v0.7.0 release contains the five-package boundary;
the additive `footprint` package frozen by APG104 is not a v0.7 release claim.

New additive package work must pass an immutable external-module fixture that
imports only public packages, exercises valid and refused inputs, checks
context cancellation where applicable, classifies documented sentinel errors,
verifies deterministic bytes and fingerprints, and uses no development
replacement for the release claim. Selection-affecting corpus or rule changes
also publish a machine-readable change class and requalification requirement.

The versioned APGR-to-JACA package, evidence, upgrade, rollback, and forbidden-
inversion handoff is owned by the
[APG and JACA integration boundary](apg-jaca-integration.md). JACA implements
that handoff behind a JACA-owned adapter; APGR does not add a JACA runtime or
control package.

## Stop and rollback boundary

Stop an affected future phase when a baseline cannot be reproduced, a package
would compete with an existing semantic owner, canonical bytes are not
deterministic, projection loss can hide consequence-bearing content, an
external fixture requires internal or mutable source, or success would require
APGR to own provider, orchestration, authentication, security, or workflow
behavior. APG104 also stops if a missing value is coerced to zero, a digest
crosses its domain, or a projection loses source identity.

Rollback is forward-only and identity-preserving: stop producing the new
version, restore a prior default for new work, or publish a new policy identity
while retaining the schemas, aliases, mappings, fixtures, and decoders needed
to interpret completed historical results. No rollback relabels old evidence.
