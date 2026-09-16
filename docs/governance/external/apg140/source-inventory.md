# APG140 external source inventory

## Observation identity and reproduction

Dated source observations on 2026-09-12 use two stable public identities:
`APG140-RM-MAIN-20260912` and `APG140-JACA-MAIN-20260912`. Repo Map main
was verified against the observed revision. JACA uses the manager-observed
mainline revision with independently verified commit and content; current local
main refs do not establish that revision as their head. The historical MAIN
label does not assert continuing branch-head equality. In the current schema,
`observed_revision` contains a semantic observation ID, not a Git revision. Exact unpublished Git
revisions are retained in phase-private reproduction records; public
[source bindings](source-bindings.json) bind each inspected contract path and
content SHA-256 independently of private access. A refresh must compare actual
new source, not assume these dated labels remain current.

Contract paths below are relative to the named external source, not APGR
links. They identify evidence, not runtime dependencies. Findings distinguish
specification, source implementation, historical test design and fresh
APGR-local fixture execution. No external test runner or live service was run.
The analysis and fixtures are independently written; no external source code
or prose was imported into the public support package. Raw external source
was inspected read-only and retained only as temporary inspection material.

## Repo Map contract slices

| Contract | Exact relative owners | Finding and limit |
| --- | --- | --- |
| ARCH7A bounded public reads | `docs/specs/public-read-contract.md`; `src/main/python/repomap_kg/storage/read_pages.py` | Direct and embedded version-1 envelopes, bounded schema-zero aliases, one-row lookahead; no snapshot isolation across requests |
| ASYNC1 coordinator protocol | `docs/specs/durable-job-and-coordinator-contract.md`; `src/main/python/repomap_kg/coordinator/_protocol_core.py`; `src/test/unit/python/repomap_kg/coordinator/protocol.unit.test.py` | Fixed version-1 negotiation, exact field sets, identity/order/terminal checks; this phase does not qualify a running coordinator or hosted transport |
| Go extractor helper protocol | `src/main/go/internal/protocol/protocol.go` | Version 1 JSONL, 1 MiB frame bound, unknown-field and trailing-message refusal, nonnegative sequence and nonempty path; distinct from public-read schema aliases and not executed here |
| Raw observation and canonical quality | `docs/specs/raw-observation-schema.md`; `src/main/resources/rdbms/2026/06/29-002-core-create_canonical_graph_tables.sql`; `src/test/int/python/repomap_kg/canonical_contract/core_graph_keys.int.test.py` | Extractor/source identity and extracted/heuristic/manual/unknown confidence, repository-scoped canonical keys, directed edges and evidence links; golden fixtures including files_conflict call the real canonicalizer, but were inspected rather than executed here |
| Repository-identity migration | `src/main/python/repomap_kg/runtime/repository_identity_migration.py`; `src/main/python/repomap_kg/runtime/schema_upgrade.py`; `src/main/python/repomap_kg/runtime/schema_decommission.py`; `src/main/python/repomap_kg/storage/repository_identity.py` | Owned local graph database, compatible ledger prefix, verified backup, reconciliation and stable identity before destructive removal; APGR evaluates a synthetic nonempty scenario only |
| Backup and destructive migration seam | `src/main/python/repomap_kg/runtime/backup.py`; `src/main/resources/rdbms/2026/07/16-001-arch5c-add-repository-identity.sql`; `src/main/resources/rdbms/2026/07/16-002-arch5d-drop-legacy-graph-schema.sql` | Separate identity addition and legacy removal; restore capability and actual restore execution remain distinct; no live/hosted backup or recovery was attempted |
| Current publication and planned snapshot contract | `src/main/python/repomap_kg/storage/publication.py`; `docs/adr/2026/08/0056-reconciled-investigation-and-program-direction.md` | Current attempt/generation receipts are implemented evidence; PublicationRef and source-blind reconciliation program are planned mainline direction, not implemented portable snapshot qualification |

The observed `_protocol_core.py` distinguishes wire schema version from source,
configuration and attempt identity. Successful terminal results require committed
publication evidence; cancellation does not itself prove rollback. APGR's new
read fixtures do not emulate the worker state machine. The two-field ASYNC1
negotiation projection tests fixed version-1 acceptance/refusal only. Its owner remains Repo
Map, and existing source refusal tests are inspection evidence only.

Mainline ADR 0056 schedules later multi-source identity/isolation proof. This
does not erase the broad existing canonicalization fixture vocabulary or
claim all Repo Map evidence is synthetic. The bounded inspected sources do
not establish the accepted empirical multi-source publication qualification
required by these inherited profile requests. Branch-only contracts were not
substituted for mainline authority.

## JACA contract slices

| Contract | Exact relative owners | Finding and limit |
| --- | --- | --- |
| Project onboarding and registered CI roles | `docs/specs/ci-cd/project-onboarding-contract.md`; `tools/ci/model.go`; `tools/ci/evidence.go`; `tools/ci/executor.go`; `tools/ci/fixture.go` | Current CI registry and RNR summary validation are consumer-specific; no APGR role adoption follows from the six-field producer summary |
| XO interface control and version selection | `docs/architecture/xo-reference-patterns-and-interface-control.md`; `docs/specs/roadmap/xo-capability-roadmap.md`; `xo/src/main/go/go.mod` | Acknowledged ICR-001..006 and XO-ICR-009 guidance; Go 1.25 module with no declared APGR dependency; production adapter and released-version qualification remain JACA-owned |
| Artifact validation and outbox ownership | `xo/src/main/go/internal/orchestration/state/report_artifact.go`; `xo/src/main/go/internal/orchestration/state/report_payload.go` | Legacy common-envelope and standalone Git-show parsing; APGR agent-report-record common envelope is not directly supported; transaction/outbox adoption is unqualified |

APGR's existing provider owners are [CI handoff](../../../architecture/jaca-ci-handoff.md),
[XO handoff](../../../architecture/jaca-xo-handoff.md),
[integration boundary](../../../architecture/apg-jaca-integration.md),
`report/types.go`, `schema/identity.go`, `testing/fixtures/jaca_ci/` and
`testing/fixtures/xo_consumer/`. The [decision analysis](decisions.md) expressly
dispositions the concrete envelope, CI registration and environment gaps.

## Qualification interpretation

REPO-MAP QUALIFIED covers only the named APGR-local synthetic evidence consumer
and graph assertions. JACA HANDOFF_CLOSED closes the APGR provider obligation
while listing current incompatibilities; it does not qualify direct runtime
interoperability. All matrix entries retain `adoption_claimed: false`.
Unsupported: hosted execution, production graph quality, production migration
and restore, cross-request snapshot isolation, arbitrary future versions,
JACA production import, role registration and raw common-envelope ingestion.
