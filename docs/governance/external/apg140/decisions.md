# APG140 external closure decisions

Status: terminal outcomes bound to the supplied [independent review](independent-review.md).
The closure ledger records 55 inherited / 43 terminal / 12 open / zero invalid.
All outcomes below are allowed by the unchanged frozen row contract.

| Identity | Terminal outcome | Evidence and reason |
| --- | --- | --- |
| APGR-REPORT-OUTBOX | CONSUMER_HANDOFF_CLOSED | In-memory report.Result supplies canonical bytes, record payload and evidence; JACA owns adoption, envelope adaptation and transaction/outbox custody |
| APGR-CI-QUAL | CONSUMER_HANDOFF_CLOSED | Existing summary and role handoff supplies producer evidence; JACA's current registry admits its own roles only, with no new APGR producer requirement |
| APGR-XO-COMPAT | CONSUMER_HANDOFF_CLOSED | Existing public APIs and caller adapter fixture cover the acknowledged interface; JACA separately owns production import and adapter qualification |
| SKILL-VER-PROTO | REJECTED | Current wire and presentation contracts have explicit limits; no accepted multi-source integration qualification or demonstrated reusable existing-owner gap supports this inherited leaf |
| SKILL-KG-QUALITY | REJECTED | Bounded canonicalization/conflict fixtures are relevant, but do not establish the required empirical multi-source publication qualification or a reusable owner gap |
| SKILL-MIGRATION | REJECTED | The current Python/PostgreSQL identity migration composes with all applicable existing process owners; the exact reusable-gap condition is assessed FALSE |
| RM-S0 | DELIVERED | Source inventory, bounded synthetic consumer evidence, limitations and refresh responsibilities delivered as APGR support evidence |
| RM-S1 | REJECTED | Same protocol specialization decision as SKILL-VER-PROTO; useful contract-watch fixtures remain support maintenance |
| RM-S2 | REJECTED | Same graph specialization decision as SKILL-KG-QUALITY; known-outcome graph comparisons remain bounded support evidence |
| RM-S3 | REJECTED | Same migration specialization decision as SKILL-MIGRATION; the tested composition and source analysis remain support evidence |
| RM-S4 | DELIVERED | Matrix separates APGR producer evidence from Repo Map storage/publication and JACA orchestration/adoption |
| RM-S5 | DELIVERED | Named material-change triggers, fixture decisions and refresh owners replace inherited release-backlog scheduling |

## Protocol decision: wire, semantic identity and claims

The [source inventory](source-inventory.md) binds public-read ARCH7A and
coordinator ASYNC1 separately. Public-read explicitly accepts versions 0 and 1;
the legacy alias stays bounded. ASYNC1 has fixed version-1 negotiation, strict
field sets, message ordering, generation checks and terminal-state constraints.
These are useful implemented contracts, not evidence of qualified arbitrary
version interoperability. Public-read continuation assumes no intervening
graph mutation; separate requests have no snapshot-isolation guarantee.

| Concrete obligation | Existing owner and application | Remaining boundary |
| --- | --- | --- |
| Separate wire fields, semantic generation and authority | [Design procedure steps 2–7](../../../../skills/designing-significant-changes/SKILL.md): freeze interface, failure, compatibility and ownership decisions | Repo Map defines its actual versions, fields and generation algorithms |
| Python serialized/persisted form changes | [Python language profile, compatibility-sensitive escalation](../../../../skills/python-language-profile/SKILL.md): identify consumers and require migration, tests and rollback | No new universal field vocabulary is needed |
| Go API/error and module compatibility | [Go language profile](../../../../skills/go-language-profile/SKILL.md): preserve consumer/error behavior and separately authorize breaks | Caller translates provider types and preserves cancellation/sentinels |
| Unknown, partial, malformed, drift and refusal examples | [Implementation steps 2–6](../../../../skills/implementing-with-test-discipline/SKILL.md) and [verification evidence rules](../../../../skills/reviewing-and-verifying-repository-work/SKILL.md): execute real local boundary and qualify only that boundary | Fixture unknown-field refusal is explicitly selected APGR consumer policy; it is not inferred public-read server behavior |

No reusable guidance gap was demonstrated by these cases. The frozen
multi-source publication/integration prerequisite is also unestablished at
this observation. REJECTED disposes this inherited request; it does not prove
that protocols never warrant specialized guidance. A materially different
qualified contract and demonstrated gap require a new admission request.

## Graph-quality decision: evidence strength and model boundaries

The inspected canonical contract integration owner calls the real
canonicalizer on golden raw-observation corpora, including `files_conflict`,
and compares exact expected JSON. This is useful source-bound test design,
not fresh execution evidence from APG140. The raw-observation and canonical
SQL contracts distinguish evidence records from entities and edges. Keys are
repository-scoped; edges have directed source/target keys and identity metadata.
That database scope alone does not prove the absence of multiple extractors or
multiple evidence sources within a repository.

ADR 0056 places proposed PublicationRef, source-blind access and reconciliation
work in a separately authorized program, with later multi-source identity
proof. The inspected mainline contract and bounded test slices do not establish
accepted empirical multi-source publication qualification for the proposed
profile. We do not generalize this observation to every historical Repo Map
experiment, and do not treat a lack of evidence as proof of bad graph quality.

| Quality dimension | Concrete synthetic oracle / source example | Owning guidance |
| --- | --- | --- |
| Entity identity and deduplication | Same canonical entity must not become two distinct expected nodes; exact node identity set | Design defines model identity; implementation freezes representative positive/adverse outcomes |
| Directed edges and identity metadata | Reverse an expected edge or change metadata and report missing/spurious assertions | Project graph contract owns direction; test discipline compares exact expected relations |
| Provenance and source conflict | Preserve separately identified supporting evidence and conflicting claims rather than overwriting them | Verification distinguishes shared lineage, conflicting evidence and claim strength |
| Missing and spurious claims | Independent expected graph compared with observed graph; an omitted or invented assertion changes the result | Testing strategy owns independent oracles and representative corpus selection |
| Cycles | A valid directed cycle remains admissible | Project model decides validity; no universal DAG rule is introduced |
| Materialization | Raw observations and canonical output are separate; successful storage does not prove extraction correctness | Python/Go owners govern transformation code, PostgreSQL owns storage constraints, verification owns claim limits |

Existing [testing policy](../../../testing-and-coverage-policy.md),
[design](../../../../skills/designing-significant-changes/SKILL.md),
[implementation](../../../../skills/implementing-with-test-discipline/SKILL.md)
and [verification](../../../../skills/reviewing-and-verifying-repository-work/SKILL.md)
cover these reusable obligations. Repo Map owns domain identity/conflict policy.
Neither empirical prerequisite nor reusable owner gap is established, so the
two inherited specialization rows are REJECTED. A future admission proposal
must supply both; it cannot rely solely on these synthetic examples.

## Migration decision and exact trigger transition

The [migration fixture](migration-fixture.json) is a synthetic evidence packet
derived from current `schema_upgrade.py`, `repository_identity_migration.py`,
`schema_decommission.py` and the ARCH5C/ARCH5D migrations. It represents two
repository rows reconciled to one stable identity before destructive legacy
removal, after a verified backup and compatible migration-ledger prefix.
Its symbolic ledger entries name the source sequence; they are not executable
migration checksums. Empty/current-database special cases are outside this
fixture. The source permits some empty-database cases; the fixture's selected
nonempty migration does not redefine them.

The APGR evidence consumer refuses foreign ownership, hosted claims, drift,
diverged schema history, unverified backup, failed restore rehearsal, conflicting
identity, malformed counts, unstable post-state, reversed cutover order and
missing rollback. It executes no SQL, container or backup operation. Synthetic
restore success is an oracle input, not an actual backup/restore observation.
The extra restore-rehearsal requirement is APGR evidence policy; the source's
`restore_supported` flag alone is not a completed restore rehearsal.

All five frozen process-owner prerequisites are mapped explicitly:

| Frozen process owner | Concrete obligation and applicable clauses | Result |
| --- | --- | --- |
| [designing-significant-changes](../../../../skills/designing-significant-changes/SKILL.md) | Procedure 2–7: inspect current migration, select compatibility model, identify owner, define state transitions, failure and rollback before cutover | Covers staged identity introduction, reconciliation and destructive-removal boundary |
| [planning-repository-work](../../../../skills/planning-repository-work/SKILL.md) | Procedure 2–5, 7–8: order owned units by dependencies/risk and bind migration/rollback and acceptance evidence | Covers backup → schema compatibility → identity → verification → removal sequence |
| [implementing-with-test-discipline](../../../../skills/implementing-with-test-discipline/SKILL.md) | Procedure 2–8 and real-boundary rules: characterize behavior, adverse cases, changed-boundary evidence and truthful omissions | Covers ledger drift, conflict, malformed state, recovery failure and local-versus-production claims |
| [converting-bash-scripts-to-python](../../../../skills/converting-bash-scripts-to-python/SKILL.md) | Do-not-use and procedure 1: requires an actual authorized Bash conversion | Not applicable: this is existing Python and PostgreSQL migration code, not a Bash conversion; non-applicability is not a guidance gap |
| [synthesizing-repository-guidance](../../../../skills/synthesizing-repository-guidance/SKILL.md) | Procedure 4–10: split obligations, inspect smallest existing owners, resolve overlap and route without inventing a capability | Routes SQL/runtime/process obligations to existing owners; source-private operational details stay private |

[PostgreSQL](../../../../skills/postgresql-database-profile/SKILL.md) procedure
1 and escalation guidance own schema compatibility, transaction/lock boundaries,
data movement, backup/restore and production evidence. Python owns process and
serialized state semantics. [Debugging](../../../../skills/debugging-systematically/SKILL.md)
and verification own causal failure evidence and recovery claims. SQLite and Go
are not substituted for PostgreSQL and Python in this scenario.

Therefore the exact `SKILL-MIGRATION` condition is FALSE: no reusable gap was
demonstrated by the inspected single-language scenario. This is not proof of
absence across all multi-language migrations. This record supplies state
evidence; frozen refresh, repair and consequence fields remain unchanged.
The supplied independent review accepts this bounded UNKNOWN-to-FALSE transition. No new leaf is substantively
required by the observed obligations, so no admission proposal is warranted.

## JACA provider handoff: concrete incompatibilities remain visible

CI source `tools/ci/evidence.go` accepts only its registered `ci-policy` and
`rnr-unit` roles; the latter requires `subproject: rnr`. APGR correctly emits
`subproject: apg`, not a forged RNR identity. Its six-field summary, explicit
role handoff, failure mapping, freshness handling and Git-drift refusal already
serve the APGR producer need. JACA must register APGR roles and toolchain
environment before adoption. Existing APGR whole-inventory Linux qualification
limits remain explicit; APG140 does not claim portable runner qualification or
repeat canonical coverage. No new current JACA contract mandates a missing APGR
producer field or behavior.

JACA's interface register requires caller-owned type containment and separately
qualified released imports. Its XO module declares Go 1.25 and no APGR
dependency. The APGR-local adapter exercises public skills/footprint/schema
APIs, DTO containment, dependency restrictions, error/cancellation preservation
and unavailable metrics. Fresh candidate-only execution is separate from
historical APG114 dual-lane evidence; neither proves JACA adoption.

JACA's `state/report_artifact.go` recognizes `chatgpt-report-record` and
standalone Git-show V2, whereas APGR's canonical common envelope is
`agent-report-record`. Direct ingestion of `report.Result.Bytes` is therefore
unsupported. `report.Result` also supplies its parsed Record and Payload;
the source parser's standalone path is an adapter option, not freshly proven
cross-project compatibility. The caller must select and qualify any translation
or standalone path without rewriting APGR's public envelope identity. The
current interface-control boundary explicitly makes APGR schemas supporting
models, never JACA control protocol. No reusable APGR producer defect follows
from a pre-adoption consumer parser expecting an older envelope.

The inspected JACA artifact owners do not establish an adopted report.Result
outbox transaction integration. That absence stays consumer-owned: APGR does
not absorb persistence, retry, transaction resolution or scheduling.
`report.Append` remains excluded from JACA adoption. The three handoff closures
dispose provider obligations only, with these incompatibilities listed as
unsupported cases and actionable refresh triggers.
