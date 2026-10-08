# APG162C / V0130-D-CALLPATH1 — RTK Caller Integration Correction Exit

Phase ID: `APG162C`
Exit ID: `Exit 00218`
Roadmap Milestone: `V0130-D-CALLPATH1`
Governing Decision: [ADR 0072](../../../../adr/2026/09/0072-optional-rtk-integration-and-conditional-slices.md)

## Status and scope

Revised candidate for checkpoint finalization after the dispatcher-owned work
review, pending manager acceptance. This record does not accept milestone D. The
retained APG162/APG162A/APG162B source and historical responses remain preserved.
No staging, commit, publication, deployment or successor work is included.

## Corrections

- F1: V2 uses the maintained capability resolver for the selected provider,
  profile and execution mode, gated by process posture. Missing, broken and
  denied workers suppress worker advertising without blocking parent work.
- F2: V1 and Claude distinguish explicit project roots from discovery starts.
  Explicit config-free targets remain authoritative; nested starts discover
  the nearest Git worktree and never cross it for ancestor configuration. No-project searches do not restart from ambient cwd. V1 carries
  selected target, original discovery start and home through the actual provider
  launch boundary without changing worker workspace context.
- F3: Injection into RTK resolution captures and serializes the real V1, V2
  and Claude exception fallbacks; the test-local fallback implementation is removed.
- F4: Disposable materialized generations cover missing and malformed VERSION
  resources, alongside the retained intact generation test. The release
  authority remains `0.12.0`.
- F5/F7: Hook effect wording is conditional; ADR and CLI guidance distinguish
  declared/effective mode, disabled/unavailable state, known hook targeting,
  double-wrap prevention, and bounded matcher inspection.
- The catalog admits valid unused entries while validating every entry and
  actual role reference. No roster inventory equality or model-count gate is added.
- Recorded successful formatting repairs are read with exact stream, metadata,
  transport, nonce, normalized-result and outcome cross-checks. Original raw
  responses and existing lifecycle/ownership validation remain authoritative;
  readback does not rerun providers or alter historical runs. In-run repairs
  reuse the original nonce; post-hoc repairs use the nonce bound by their own
  recorded formatter prompt.

## Additive historical correction

F6: APG162A's provider-directory/grandparent association and claimed V2 turn
coverage are historical assertions, not current verification. APG162B removed
the guessed association but retained the F1 mode tuple and F2 cwd pinning.
APG162C supplies the caller corrections and provider/binding-specific evidence.
Earlier responses and receipts are not rewritten or retroactively revalidated.

## Verification and limitations

Historical produce qualification used disposable homes, filesystem fixtures, fake
provider runners and fake RTK executables. Raw commands, results and JUnit
records are retained in the launcher-owned produce evidence. Intermediate
fixture failures remain recorded and are superseded only by relevant reruns.
The scoped pytest groups pass 433 distinct cases: RTK/callers/catalog 91,
configuration/source guidance 114, V1 dispatch 117, V2 compatibility 43, and
retained repair/resume/outcomes 68. Two optional external-worker modules are
collection-skipped because `agent_workers` is unavailable. A final 40-case
caller recheck confirms added posture assertions and the final formatting
correction; these repeated cases are excluded from the aggregate.

Skill governance passes at 46 canonical skills/catalog rows/projections.
Record identity passes at 74 ADRs and 216 exits/phase IDs, next exit 00219.
Whitespace validation passes. Go test/vet are not rerun because no Go source,
JSON schema or Go consumer behavior changes in this correction. These are produce-stage results, not a claim of fresh revision verification.

F8 remains a bounded limitation: Python regex matcher fallback does not prove
equivalence with all Claude matcher semantics. F9 probe diagnostic readability
is unchanged; started/timed-out/truncated fields remain the structured evidence.
No live RTK installation, provider behavior, hook invocation, token savings,
operator-setting mutation, E/MCP/adaptive context or promotion is claimed.

## Independent review disposition

Disposition: amend

Rationale: Required R1 and R2 are accepted and corrected. V1 now leaves implicit
project selection to RTK's maintained Git-marker discovery. Dedicated APGR
root/start context reaches Claude without rewriting worker workspace context,
including when execution occurs in a different directory. New fixtures place a
config-free Git repository beneath a configured ancestor with a conflicting
selected home, and check restoration of pre-existing target context.

Advisory A2 is accepted and corrected using real disposable parser/outcome
fixtures for both recorded repair forms. A first revision admitted the post-hoc
success marker but still rejected its fresh nonce; that failed check remains
recorded. The subsequent repair binds the fresh nonce to the recorded formatter
prompt and retains stream, metadata, transport, normalized-result and outcome
cross-checks. No historical run or receipt is changed.

Advisory A1 is deferred as a concrete remaining limitation: V2 capability
advertising does not establish V1-equivalent ParentLedger registration, worker
context, worker-envelope admission or Astra native binding. Actual V2 worker
execution is unqualified. Its caller-local suppression for all read-only
bindings is conservative and now documented. The style/private-helper nit is
non-blocking and retained; the existing ownership validator remains the shared
implementation. F8 and F9 remain as described above.

The revision is not independently re-reviewed. The sole supplied review covers
the producer candidate; fresh closer qualification covers the amended bytes.
Dispatcher checkpointing and manager acceptance remain external.

Qualification evidence: Revision-stage qualification passes 98 RTK/caller/catalog
cases, 12 retained-repair cases, 114 configuration/source-guidance cases, 10
focused V1 boundary cases and 43 V2 compatibility cases. Two optional worker
modules are collection-skipped, not passing, because `agent_workers` is absent.
A final 29-case caller recheck passes after adding inherited target-context
restoration assertions; it overlaps the 98-case group and is not added to the
277 distinct passing cases. Skill governance passes at 46/46/46; record identity
passes at 74 ADRs and 216 exits/phase IDs, retaining exit 00218 and next exit
00219. Whitespace validation passes on the final documentation bytes.
Raw commands, exit status, stdout/stderr, JUnit, tool versions and native dirty
candidate identities are retained separately under revision qualification.
Producer evidence remains historical and is not combined into the fresh count.

Unresolved concerns: A1 V2 worker admission/execution remains unqualified; F8
matcher equivalence and F9 diagnostic readability remain bounded limitations.
The non-blocking reader style/private-helper nit is deferred. There is no
second independent review of the revision. Go test/vet and live provider,
worker, RTK/hook execution are not claimed; no Go or schema change warrants a
new Go gate.

## Accepted local integration addendum (APG163 entry)

The supplied manager/operator disposition accepts and closes V0130-D for local
development integration. APG162C-LOCAL-FINALIZE1 committed the accepted correction
as `5360d4cb0cf8e4bd87ee054f4c6de8c109c1f94c`, above preservation commit
`0fbb45ba389e2514b66017bb21c16317b2f2d5a5`. These supplied identities record the
accepted operation, not a current-head prerequisite. The native APG162C lifecycle
remains a checkpoint; no independent-review freshness is upgraded. Original run
limits, 277 distinct passes, two optional-module skips and 29 repeated caller
checks excluded from that total remain preserved. No provider, shared database,
worker/hook, deployment or publication qualification is added by this addendum.
A1, F8 and F9 remain bounded debt; they do not reopen D.
