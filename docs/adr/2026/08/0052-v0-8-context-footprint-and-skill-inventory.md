# ADR 0052: v0.8 Context Footprint and Skill Inventory

## Status

Accepted

## Decision date

2026-08-30

## Context

The live public v0.7.0 release provides the five-package Go boundary
`schema`, `report`, `skills`, `envsnap`, and `hotspot`. The next additive
capability needs an APGR-owned vocabulary for context-footprint accounting,
exact comparisons, and reference-preserving projections without claiming
consumer-total-context fit or taking ownership of provider execution.

The APGR proposal dispositions identified capacity and context architecture as
separate concerns. APG104 is the canonical semantic delivery phase for this
bounded work. `APGR-CAP0` and `APGR-CXT0` are independently owned program-entry
labels within APG104; they are not phase identities. Their evidence remains
separate even when the phase delivers them together.

The current public inventory is 39 skills, with 14 stable and 25 provisional
entries. Canonical discovery descriptions occupy 9,504 UTF-8 bytes and 9,492
characters. The historical 9,527-byte integrity limit therefore has 23 bytes
of headroom. Separate CAP0 accounting records 483,778 semantic skill-body
bytes, 495,319 full-skill bytes, and 13,074 repository-only support bytes.
The corpus fingerprint is
`0509803b3c12e0366917a341c9d56945d7966897953415acf0c997254e1331c`.

These are different accounting surfaces. The historical integrity limit must
not be silently reinterpreted as a per-skill or default-discovery policy, and
queue size is not evidence for relaxing it.

## Decision

1. Record `APG104` as the canonical delivery phase. Use `APGR-CAP0` for
   capacity, selection identity, and skill-inventory governance, and
   `APGR-CXT0` for APGR context-footprint, comparison, and projection
   architecture. A direct bounded operator assignment authorizes the listed
   dependency-ordered v0.8 program, without granting unrelated successor work.

2. Accept APGR-D6 only now, after the CAP0 and CXT0 decisions are supplied
   together in APG104. The additive Go package name is `footprint`; this
   acceptance freezes its ownership and schema boundary, not a release or an
   unqualified future API.

3. Preserve the CAP0 baseline and controls. CAP0 adds no new 250-byte guard,
   default discovery cap, implicit selection rule, or description
   normalization requirement. It keeps description, body, support, selected
   bundle, and consumer-total-context measurements distinct. It records zero
   candidates and leaves hole-filling, vocabulary-extension, graph-quality,
   versioned-protocol, RepoMap-derived, and Theme Forge queues deferred.

4. Keep skill IDs, corpus identity, control identities, component identities,
   and supersession relations stable and explicit. Control identities are
   versioned and mapped independently from the component registry. The
   initial control families are corpus integrity, selected discovery, selected
   body, support material, materialized bundle, prompt overhead, and
   consequence-bearing content. A change that affects selection carries a new
   policy identity and a requalification signal.

5. Freeze these additive, independently versioned APGR schema identities:

   - `apg.context-footprint/v1` for canonical observations and components;
   - `apg.context-comparison/v1` for exact control/treatment comparisons;
   - `apg.context-projection/v1` for source-bound derived records;
   - `apg.context-component-registry/v1` for the closed component vocabulary;
     and
   - `apg.capacity-control-mapping/v1` for the component-to-control mapping.

6. Require every canonical record to be strict UTF-8 JSON with one trailing
   line feed, deterministic field and array order, an explicit closed field
   vocabulary, and integer metrics. Unknown schema versions, fields,
   vocabulary values, units, evidence bases, or control mappings fail closed.
   A missing or unavailable measurement is represented explicitly with its
   availability and reason and has no value. Missing is never zero; zero is
   valid only as an observed integer.

7. Domain-separate the SHA-256 identities for footprint, comparison, and
   projection records. The `fp`, `cmp`, and `proj` domains are distinct, and a
   digest from one domain cannot be reused in another. Source references bind
   exact URI, media type, size, and digest facts; APGR does not fetch them or
   acquire network, provider, or authentication authority.

8. Keep observation dimensions orthogonal. A record may state observation
   basis, study design, quality, availability, method, harness, provider
   label, repetitions, workload, variant, exclusions, and metric/unit
   identity. The component registry and capacity-control mapping are separate
   versioned records, so a component cannot silently change its control.

9. Define `apg.context-comparison/v1` as an exact integer
   treatment-minus-control operation over one corresponding component. The
   component kind, name, control identity, schema, compatible observation
   dimensions, and unit must match. No unit conversion, rounding, inferred
   correspondence, unavailable-metric substitution, or synthetic zero is
   permitted.

10. Define `apg.context-projection/v1` as a derived record that never replaces
    its canonical source. It retains canonical-source schema, digest, and
    size; declares fidelity; enumerates every omitted field; and refuses an
    unbound source, omission of consequence-bearing content, sensitivity
    downgrade, or retention downgrade. A projection may disclose less only
    when the permitted loss is explicit and validated against the source.

11. Restrict sensitivity labels to `public`, `internal`, `confidential`, and
    `restricted`. Restrict retention labels to `ephemeral`, `task_scoped`,
    `retained`, and `immutable`. APGR validates and propagates these labels;
    the consumer remains responsible for access control, storage,
    transmission, and disposal.

12. Keep APGR outside provider and JACA ownership. The footprint package does
    not execute providers, choose routes, authenticate, hold credentials,
    perform retries or notifications, advance workflows, enforce consumer
    retention, or define JACA control-protocol types. JACA may consume a
    released and qualified APGR package through a JACA-owned adapter, but it
    does not own the APGR schemas.

13. Retain APGR-D18 as amended: a substantive immutable independent
    public-package consumer fixture is the primary qualification gate for a
    new public package. JACA qualification is additional valuable evidence
    and is non-gating unless the shared register explicitly changes that
    allocation.

14. Supersede APGR-D19's earlier entry-eligibility wording for the direct
    bounded operator authority that delivers the listed v0.8 program entries.
    This does not authorize unrelated work or automatic continuation beyond
    the dispatcher-owned campaign. The optional `APGR-CXT2B` external importer remains
    deferred for all missing gates, including pinned format identity and
    rights, reproducible fixtures, allowlisted mapping, refusal behavior, and
    independent consumer disposition.

APG104 records the architecture and first-party source implementation as
complete for the work-stage candidate. Qualification and publication evidence
remain separate; this ADR makes no release, deployment, or active-consumer
claim.

## Alternatives considered

- **Keep `footprint` permanently reserved without accepting D6.** Rejected
  for APG104 because CAP0 and CXT0 now supply the required ownership,
  identity, and compatibility boundaries. Future APIs and releases still
  require separate qualification.
- **Add a 250-byte or similar default discovery guard.** Rejected because it
  would reinterpret the historical integrity control without consumer-
  grounded evidence and would conflate descriptions with other surfaces.
- **Combine descriptions, bodies, support, and consumer context into one
  total.** Rejected because the measurements answer different questions and
  have different owners.
- **Use an external diagnostic format as the first-party model.** Rejected
  because APGR needs its own versioned schemas, explicit unavailable states,
  and stable source identity before optional import.
- **Let JACA or a provider own the footprint records.** Rejected because
  APGR owns reusable measurement evidence while JACA owns orchestration,
  custody, consumer policy, and lifecycle relations.
- **Select or author candidates from the inventory queues.** Rejected because
  CAP0 governs identity and ordering only; candidate work needs its own
  bounded authority and qualification.

## Consequences

APGR has an additive, provider-neutral footprint package boundary with stable
schema identities and explicit compatibility rules. Consumers can distinguish
observations, components, missing values, exact comparisons, and source-bound
projections without treating advisory evidence as workflow authority.

The live public v0.7 package boundary and its skill inventory remain unchanged.
The additive package is not part of a v0.7 release claim, and APG104 does not
claim a v0.8 release. The external fixture remains the primary future package
qualification gate; JACA can contribute later consumer evidence without
creating a circular dependency.

## Compatibility and rollback

Compatibility is additive and identity-preserving. Existing v0.7 schemas,
package paths, skill IDs, corpus identity, and historical 9,527-byte control
retain their meaning. A consumer that does not understand one of the v0.8
schema identities must fail closed rather than guess, coerce missing values,
or reinterpret a digest. Selection-affecting policy changes require a new
versioned identity and consumer requalification.

Rollback is forward-only: stop producing or publishing the new package
version, restore a prior default for new work, or publish a new policy identity
while retaining the schema definitions, aliases, mappings, fixtures, and
decoders needed to interpret completed records. Rollback never relabels old
evidence, deletes its canonical source, or silently changes a projection's
fidelity, sensitivity, retention, or digest domain.
