# APGR v0.8 Context-Footprint and Skill-Inventory Roadmap

## Authority and current state

This roadmap orders accepted APGR-owned v0.8 work. `APG104` is the canonical
semantic delivery phase for the current bounded slice. `APGR-CAP0` and
`APGR-CXT0` are independently owned program-entry labels within APG104, not
phase IDs. The direct bounded operator assignment authorizes the dependency-
ordered v0.8 program through candidate qualification and, only after dispatcher
pre-final acceptance, closeout publication and immutable readback.

The live public release is v0.7.0. The additive v0.8 source candidate is
implemented and source-qualified; it does not claim publication, deployment,
or active consumer cutover.

The normative product and ownership decisions are in the
[v0.8 context-footprint and skill-inventory contract](architecture/v0-8-context-footprint-and-skill-inventory.md).
The versioned consumer boundary is in the
[APG and JACA integration contract](architecture/apg-jaca-integration.md).

## APG104 delivery entries

| Entry | Scope | Required result | Must not absorb |
| --- | --- | --- | --- |
| `APGR-CAP0` | Re-attest capacity and selection evidence; decide control identities, candidate compatibility classes, corpus change classes, ordering, and supersession | One explicit capacity/selection contract and a versioned mapping input for CXT0 | Catalog or rule mutation, description normalization, candidate authoring, release |
| `APGR-CXT0` | Define footprint/comparison/projection schemas, evidence dimensions, serialization, fidelity, sensitivity, retention, traceability, and external qualification | One complete additive architecture contract aligned to CAP0 controls and the APG–JACA register | Provider execution, JACA schema/dependency change, release, or optional importer adoption |

CAP0 and CXT0 retain separate ownership and evidence. CXT0 consumes CAP0's
terminal control taxonomy and versioned mapping; it cannot replace that
authority or transfer it to JACA.

### CAP0 baseline and decision result

CAP0 re-attests the live public v0.7 inventory with separate accounting
surfaces:

| Surface | Result |
| --- | ---: |
| Canonical skills and maturity | 39 skills; 14 stable / 25 provisional |
| Description discovery | 9,504 UTF-8 bytes; 9,492 characters |
| Historical integrity limit | 9,527 UTF-8 bytes; 23 bytes of headroom |
| Semantic skill bodies | 483,778 bytes |
| Full skill material | 495,319 bytes |
| Repository-only support | 13,074 bytes |
| Corpus fingerprint | `0509803b3c12e0366917a341c9d56945d7966897953415acf0c997254e1331c` |

The 9,527-byte value remains the historical integrity control. CAP0 adds no
250-byte guard, default discovery cap, or implicit selection rule. Stable skill
IDs and versioned control/mapping identities remain explicit. There are zero
current candidates; hole-filling, vocabulary-extension, graph-quality,
versioned-protocol, RepoMap-derived, and Theme Forge queues remain deferred,
and queue size cannot relax a control.

## Dependency-ordered campaign sequence

```text
APG104 — canonical delivery phase
  |
  +--> APGR-CAP0 — capacity and selection governance
  |       |
  |       +--> zero skill candidates selected
  |
  +--> APGR-CXT0 — footprint/comparison/projection architecture
          |
          +--> APGR-CXT1 — footprint core
                    |
                    +--> APGR-CXT2A — first-party APGR measurement
                    |       |
                    |       +--> APGR-CXT3 — bounded projections
                    |               |
                    |               +--> APGR-CXT4 — offline evaluation
                    |                       |
                    |                       +--> APGR-Q1 — immutable consumer fixture
                    |                               |
                    |                               +--> APGR-INTEG — claimed distribution surfaces
                    |                                       |
                    |                                       +--> APGR-R1 — publication and readback
                    |
                    +--> APGR-CXT2B — optional importer (deferred for all missing gates)
```

An optional importer never blocks first-party measurement or projection. CXT2B
is deferred for every missing gate: pinned external-format identity and rights,
reproducible fixtures, allowlisted fail-closed mapping, refusal behavior, and
an independent consumer disposition. A generic non-JACA handoff study is
outside the minimum v0.8 thesis and requires its own later decision.

## CXT0 frozen additive contract

APGR-CXT0 freezes the additive `footprint` package boundary and these
independent canonical schema identities:

- `apg.context-footprint/v1`;
- `apg.context-comparison/v1`;
- `apg.context-projection/v1`;
- `apg.context-component-registry/v1`; and
- `apg.capacity-control-mapping/v1`.

Canonical JSON is strict UTF-8 with one trailing line feed, deterministic
ordering, an explicit vocabulary, and integer metrics. Missing or unavailable
is explicit and is never a zero. Footprint, comparison, and projection
identities use separate domain-separated SHA-256 `fp`, `cmp`, and `proj`
domains. Comparisons are exact integer treatment-minus-control deltas with
matching component, control, schema, observation, and unit identities; no
implicit conversion or inferred correspondence is allowed.

Projections retain canonical-source schema, digest, and size, enumerate every
omitted field, and refuse unbound sources, consequence-bearing omissions,
sensitivity downgrades, and retention downgrades. Sensitivity labels are
`public`, `internal`, `confidential`, and `restricted`; retention labels are
`ephemeral`, `task_scoped`, `retained`, and `immutable`. APGR validates and
propagates labels, while the consumer owns custody and disposal.

## Package and release sequence

The live v0.7 public Go package boundary is `schema`, `report`, `skills`,
`envsnap`, and `hotspot`. APG104 adds `footprint` in the v0.8 source candidate.
The source gate passes Go vet, 364 Go tests including the race run, 3,374
configured unit tests, and 605 configured integration tests with two declared
environmental skips. That evidence is not a release claim until post-review
publication and fresh public readback succeed.

A new public package must be qualified by a substantive immutable external
consumer before its release claim. JACA may add later real-consumer evidence,
but APGR does not wait circularly on JACA scheduling. JACA production adoption
uses an exact published APGR version through a JACA-owned adapter. JACA
qualification remains additional to the primary independent fixture gate.

## Stop and publication boundary

The following remain outside this campaign or are deferred:

- skill, catalog, rule, maturity, or skill-projection mutation, because CAP0
  selected zero candidates;
- the optional diagnostic importer, optimizer, provider, authentication, fallback,
  notification, network, role, security-policy, or workflow implementation;
- JACA dependency or runtime integration;
- irreversible v0.8 publication before dispatcher pre-final acceptance and
  dispatcher-owned Git finalization; and
- deployment, host mutation, global installation, or provider-profile mutation.

The work stage returns one exact candidate and evidence packet. The dispatcher
owns the review transition and Git publication policy; passing local evidence
does not itself publish or deploy the release.
