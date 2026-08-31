# APG104 v0.8 Context Footprint and Skill Inventory

## Result

APG104 is the canonical delivery phase for the bounded APGR v0.8
context-footprint and skill-inventory slice. Its independently owned program
entries are `APGR-CAP0` and `APGR-CXT0`; those labels are not phase IDs and do
not merge ownership or evidence.

Architecture status: complete. Source implementation status: complete.

Current phase disposition:
`V08_SOURCE_CANDIDATE_QUALIFIED_AWAITING_PREFINAL`.

The resulting source gate passes Go vet, 364 Go tests including the race run,
3,374 configured unit tests, and 605 configured integration tests with two
declared environmental skips. This evaluation makes no release, publication,
deployment, or active-consumer claim; immutable candidate-artifact and fixture
evidence is owned by the pre-final packet.

## Current public baseline

The live public release is v0.7.0. Its public Go boundary remains `schema`,
`report`, `skills`, `envsnap`, and `hotspot`. APG104 is additive and does not
change that release or its existing package ownership.

CAP0 records the current public skill inventory as 39 skills, with 14 stable
and 25 provisional entries. Canonical discovery descriptions measure 9,504
UTF-8 bytes and 9,492 characters. The historical 9,527-byte integrity limit
therefore retains 23 bytes of headroom. Separate accounting records 483,778
semantic skill-body bytes, 495,319 full-skill bytes, and 13,074 repository-only
support bytes. The corpus fingerprint is
`0509803b3c12e0366917a341c9d56945d7966897953415acf0c997254e1331c`.

These values are distinct surfaces: descriptions, semantic bodies, full skill
material, repository-only support, and consumer-total-context are not summed
into one substitute measure. No new 250-byte guard or default discovery guard
is introduced. The 9,527-byte value retains its historical integrity meaning.

## APGR-CAP0 result

CAP0 freezes capacity and selection-identity governance for this phase:

- versioned controls and mappings are explicit, with stable skill, component,
  control, corpus, and supersession identities;
- queue size cannot relax a control, and zero skill candidates are selected or
  authored;
- hole-filling, vocabulary-extension, graph-quality, versioned-protocol,
  RepoMap-derived, and Theme Forge candidate queues remain deferred; and
- selection-affecting changes require a new policy identity and a consumer
  requalification signal.

CAP0 does not mutate the current catalog, projections, maturity, descriptions,
or selection rules. It does not claim that an APGR bundle fits a provider's
full context.

## APGR-CXT0 result

CXT0 freezes the additive `footprint` package boundary and these independent
canonical identities:

- `apg.context-footprint/v1` — canonical observation and component record;
- `apg.context-comparison/v1` — exact control/treatment comparison;
- `apg.context-projection/v1` — source-bound derived record;
- `apg.context-component-registry/v1` — closed component-kind vocabulary; and
- `apg.capacity-control-mapping/v1` — component-to-control mapping.

Canonical records use strict UTF-8 JSON with one trailing line feed,
deterministic field and array order, closed field vocabulary, and integer
metrics. Unknown versions, fields, units, evidence bases, vocabularies, or
mappings fail closed. Missing or unavailable values have an explicit state and
reason with no value; missing is never zero, while an observed zero remains
valid.

Footprint, comparison, and projection fingerprints are separate,
domain-separated SHA-256 identities using the `fp`, `cmp`, and `proj` domains.
They are not interchangeable. Source references retain exact URI, media type,
size, and digest identity without making APGR a fetcher or network authority.

Observation dimensions remain orthogonal: basis, study design, quality,
availability, method, harness, provider label, repetitions, workload, variant,
exclusions, and metric/unit identity are not collapsed into a single score.
The component registry and CAP0 mapping are independently versioned.

Comparisons are exact integer treatment-minus-control deltas for matching
component kind, name, control identity, schema, compatible observation
dimensions, and unit. Unit conversion, rounding, inferred correspondence,
unavailable substitution, and synthetic zeroes are refused.

Projections retain canonical-source schema, digest, and size, declare fidelity,
and enumerate every omitted field. An unbound source, consequence-bearing
omission, sensitivity downgrade, or retention downgrade is refused. A
projection never replaces its canonical source.

Sensitivity labels are `public`, `internal`, `confidential`, and `restricted`.
Retention labels are `ephemeral`, `task_scoped`, `retained`, and `immutable`.
APGR validates and propagates these labels; the consumer owns access, custody,
transmission, and disposal.

## Corrected disposition and boundaries

APGR-D6 is Accepted only now because CAP0 and CXT0 supply the ownership,
identity, compatibility, and additive package boundary together in APG104.
APGR-D18 remains Amended: the substantive immutable independent public-package
fixture is the primary new-package qualification gate, while JACA is extra
valuable evidence and non-gating unless the shared register explicitly changes
that allocation. APGR-D19 is superseded only by the direct bounded operator
authority for APG104; no general, automatic, or successor authority follows.

The optional `APGR-CXT2B` external importer is deferred for all missing gates,
including pinned format identity and rights, reproducible fixtures, an
allowlisted fail-closed mapping, refusal behavior, and independent consumer
disposition. First-party footprint work does not depend on that importer.

APGR does not own provider execution, authentication, credentials, routes,
retries, notifications, workflow progression, process confinement, consumer
retention enforcement, or JACA control-protocol types. JACA remains a consumer
behind a JACA-owned adapter and cannot become the APGR schema owner.

## Compatibility and rollback

The contract is additive. Existing v0.7 package paths, schemas, skill IDs,
corpus identity, and the historical integrity limit retain their meaning. A
consumer that does not understand a v0.8 identity fails closed rather than
guessing, coercing missing values, or reusing a digest from another domain.

Rollback is forward-only and identity-preserving: stop producing the new
package version, restore the prior default for new work, or publish a new
policy identity while retaining schema definitions, mappings, fixtures, and
decoders for completed records. Rollback never relabels old evidence,
deletes its canonical source, or changes projection fidelity, sensitivity,
retention, or digest domain.
