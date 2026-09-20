# APG166 — Maturity tranche and integrated evaluation

Phase: APG166. Milestone: V0130-H-EVAL1. Status: revised checkpoint after dispatcher-owned independent work review;
H release gate unsatisfied. Documentation amendments have no second independent review.

## Outcome and authority

H establishes bounded acquisition-authority retention, complete successful
CLI/MCP response-write telemetry at its declared channel boundary, a sealed
provider-free evaluation harness, and five individual promotion inventories.
It establishes **zero qualified stable promotions** and **no measured adaptive
benefit**. The shipped static default remains unchanged. I must not infer a
recommendation to flip the default from this candidate.

APG165 was manager-accepted for local integration before H. Its original provider
checkpoint and revise-close history remain intact; amendments had no second
independent review. No push or publication occurred. Native provider filesystem
permissions and live model behavior remained unqualified. That acceptance did
not establish H benefit or authorize any promotion. Exact supplied Git evidence
is retained separately under the phase's publication-excluded entry authority.

## Implementation and accounting boundary

The installed Python CLI retains immutable content-addressed configuration
authority. Identical bytes reuse one file; different captures never overwrite one
another. A descriptor-relative lock serializes admission. New runs retain at most
64 authority records of at most 1 MiB each, one bounded pending inode, and one
lock. Legacy UUID records count toward admission; existing evidence is not
removed to reclaim capacity. Exhaustion refuses a new capture and calls for a new
run. A killed writer can leave one pending file; the next invocation reuses it or
removes only its verified extra hardlink after publication. Exact selected source
snapshots, override provenance, acquisition events and recovery records remain.
No operator settings are written. This cap does not reserve whole-run archive
capacity for other artifacts.

The H boundary is `apgr-controlled-channel-write/v1`. MCP counts the exact UTF-8
JSON response frame including its LF once on successful complete write. Tool
schema discovery, search, explain, skill and context resources, initialization
and ping are included. Acquisition frames retain `channel_delivered`; other
successful responses use `response_delivered`. CLI search now has the same
successful-write evidence as acquisition. Short/failed writes and tool/protocol
errors do not claim successful delivery. An observation-write failure terminates
the channel with a diagnostic; missing traces cannot establish complete coverage.
Preflight responses use `preparation_response` and channel `preparation`, and
cannot be included as provider delivery. Preparation servers refuse normal agent
requests. Repeated real responses are additive, including repeated explain views
of historical metadata. Event references and snapshot views are not extra
transmissions of that response.

There is no tested bridge from engine events to the harness delivery schema.
Engine events lack payload digests and initial/late classification; collection
retains empty deliveries with unavailable coverage. Prompt, instruction and MCP
configuration delivery emitters are not integrated here. Thus H0.2 is only
partially addressed: successful CLI/MCP writes are measured, but complete
end-to-end controlled-channel accounting remains an unsatisfied prerequisite.

Initial prompt and instruction transport stays owned by F's separate invocation
observations. MCP configuration is counted only if actually delivered at a
specified provider boundary, not merely materialized. Native recovery bytes
require a witnessed read. H's aggregator requires measured complete coverage and
consistent transmission identities; it cannot construct an initial or cumulative
total from absent provider traces. APGR preflight, this outer dispatcher, source
materialization and prospective plans are not scenario delivery. Provider-native
bytes and tokens remain unavailable; no token heuristic is used.

## Seal and method

[Seal](apg166/seal.json) binds all 15 scenarios, metrics, F accounting owner,
selection/packing implementation and rule version, canonical corpus/descriptors,
maturity/debt inputs, provider instruction inputs, channel implementation,
harness and native binary. It records both arms' requested modes and identical
provider/binding identity. Model route and native binding remain explicitly
unavailable: no provider is invoked by this harness.

`testing/h_eval/evaluate.py` consumes the frozen definitions without editing them.
It materializes the exact synthetic Scenario 08/09 bodies and override input in
external isolated subjects. Each of the 15 cases invokes the real planner twice
with identical structured primary-language facts and checks reproducibility.
Those prospective probes deliberately use **no expected-output selection list**;
they do not claim full scenario selection or task success. The fixed task/role
envelope is synthetic, while source and rendered byte lengths are exact. All
normal effective modes remain static because qualification is absent.

[Raw results](apg166/raw.json) preserve both arms and each frozen quality oracle,
including unavailable task output, retries, revisions, missing-guidance findings,
restart incidents, acquisitions, authority, recovery, provider bytes and tokens.
[Aggregate](apg166/aggregate.json) is reproduced independently from raw results.
The result schema is `testing/h_eval/results.schema.json`. Its schema describes
retained evidence; the aggregator also enforces duplicate/missing pairs, route
agreement, positive measured denominators, complete delivery coverage, additive
transmissions, cohort integrity and Scenario 15's live contingency.

No qualified repository-owned live paired provider harness was found. Existing F/G
harnesses exercise instrumented actors and real native channels, not model
outcomes. H therefore does not improvise nested provider calls. The commands for
Scenarios 06, 10 and 15 are **not run** against invented successful solutions:
the required provider-produced subject output is unavailable. Semantic oracles
requiring provider critique/use are also unavailable. Controlled mechanism tests
remain separately labelled and cannot satisfy those substantive outcomes.

Two full collections were invalidated: first, a retained-request representation
included standing instruction text unsuitable for public evidence; second,
preflight response telemetry needed explicit preparation scope. The complete
15-case collection was rerun after each correction under a new seal. Prior raw
observations and reasons are retained in the private qualification packet. No
selection rule, ranking weight, skill body, scenario budget, cohort, task input
or oracle was changed. No selective failure rerun contributes to the aggregate.

Reproduction (explicit locally built native binary and external empty subjects):

```sh
python3 testing/h_eval/evaluate.py collect --root . --binary /selected/apgr \
  --seal docs/evaluations/apg166/seal.json --subjects /selected/new-subjects \
  --output /selected/raw.json
python3 testing/h_eval/evaluate.py aggregate --root . \
  --raw /selected/raw.json --output /selected/aggregate.json
```

The binary must match the seal. Outputs are exclusive-create; input drift requires
invalidation, not silent resealing. A different build identity is a new collection.

## Frozen gates and limitations

| Gate | Result |
| --- | --- |
| Full applicable savings cohort | Expected n=5; measured pairs n=0; median and p95 unavailable |
| Excluding synthetic 08/09 | Expected n=3; measured pairs n=0; median and p95 unavailable |
| Scenario 15 | Contingent/unavailable; no selective discovery/no-leakage or task-quality proof |
| Exact recovery 10/11/12/14 | Controlled G mechanism tests pass; live paired gate unavailable |
| Authority | Controlled fixtures preserve Git authority; live paired gate unavailable |
| Substantive task quality | Unavailable; no successful dispatch or fake actor is counted as quality |
| Five stable promotions | 0; unchanged criteria and ledger |
| H release gate | Not established |

The frozen formulas remain `1 - adaptive_initial/static_initial` and
`adaptive_cumulative/static_cumulative - 1`, with nearest-rank p95 index
`ceil(0.95*n)-1`. Both full and non-synthetic cohorts must pass. At these sample
sizes p95 is effectively the maximum, not a population estimate. Scenario 15's
exclusion permits only the explicitly labelled applicable-subset calculation;
it cannot establish the full default-flip evidence.

## Individual maturity disposition

The [five records](apg166/promotions/) bind whole source, body, canonical descriptor
entry and maturity entry identities. All seven inherited evidence categories
remain visible. Historical rollback/provenance support is attributed to APG139;
it is not a new live removal or source-rights review. Current positive structured
fact fixtures, representative foreign-owner non-triggers, Producer/Work Review
role variation, exact acquisition and provenance checks provide mechanical support.
They are not verified positive guidance-use invocations. New verified invocation
count is zero. In particular, Go's required three non-trivial guidance invocations
are absent. No skill body is modified and no stable ledger string is changed.

The supplied independent reviewer explicitly rejected stable promotion for each
of the five exact body/evidence records because verified positive guidance use
is absent and non-trigger tests establish only mechanical fact boundaries. The
original promotion inventories remain unchanged as the reviewed evidence; their
pending fields describe the producer checkpoint. The separate
[review disposition](apg166/review-disposition.json) records the terminal decision.
A review alone cannot manufacture missing positive use. No reserve is substituted: none has an independently complete
promotion case in this checkpoint. CSS stays excluded and Bash-to-Python deferred.

## Verification and handoff

Fresh test results and original failures are retained in the bounded qualification
packet. H checks include 15-input integrity and seal identity, synthetic
materialization, deterministic plans, strict aggregates, missing-data refusal,
nearest-rank edge cases, Scenario 15 contingency, five primary fact/role fixtures,
exact body acquisition, controlled G recovery and authority, installed wheel/native
generation, configuration, persistence/archive/resume and governance validation.
The candidate qualification record reports exact counts and skips separately.
Full release readiness is not claimed.

The [machine-readable I input](apg166/i-handoff.json) recommends retaining static.
No provider matrix cell is promoted. Antigravity remains static; Claude filesystem
permissions and selective isolation are unqualified. I-only work includes release
hardening, any default decision, versioning, publication and owner-controlled
cutover. This checkpoint stages, commits, pushes and installs nothing.

## Revise-close disposition

- F1 accepted: narrow H0.2 to the CLI/MCP successful-response-write boundary.
  Complete delivery bridging, digests, initial/late classification and prompt,
  instruction/configuration observations remain prerequisites to a future live
  cumulative-byte gate. No claim that both carried debts are closed remains.
- F2 accepted as a residual outside installed-CLI H0.1: provider attempts still
  create UUID-named prelaunch, server and MCP configuration files. Their lifecycle
  needs separately authorized follow-up before repeated provider measurement;
  the installed-CLI retention cap does not cover them.
- F3 accepted as a documentation clarification: `full_applicable` means only the
  eligible subset after contingent Scenario 15 exclusion. Even a true subset
  `pass` cannot satisfy full quality/authority or `benefit_gate_pass`. The I input
  explicitly marks `applicable_subset_only`; no aggregate formula is changed.

These are documentation and handoff amendments only. The seal, harness, raw
results, aggregate, skill bodies, evidence inventories and selection policy are
unchanged, so no measurement result is invalidated by this revision. No second
independent review was obtained. Zero promotions and the blocked H gate remain.
