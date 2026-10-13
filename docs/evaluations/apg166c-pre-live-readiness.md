# APG166C — Pre-live H qualification remains blocked

Phase: APG166C. Continuation: V0130-H-QUAL4. Exit: 00225.
Status: independently work-reviewed; revise-close retains a blocked checkpoint.

## Disposition and authority

Prerequisite readiness is false. The phase does not establish
`V0130_H_LIVE_EVALUATION_PREREQUISITES_READY`. The complete frozen execution
package is not delivered. The [handoff](apg166c/handoff.json) and
[source inventory](apg166c/readiness-seal.json) record the partial result and
remaining blockers. The holdout remains closed: zero live H pairs, zero
promotions, Scenario 15 contingent/unavailable, static default and no V0130-I.

APG166B manager acceptance is recorded forward in Exit 00224 and the roadmap.
Its blocked evaluation, handoff and inventory remain byte-identical. Acceptance
does not supply missing qualification or authorize live H. No producer-selected
review, staging, commit, push or publication occurred.

## Implemented mechanism

`libexec/agent_phase/claude_acquisition_handoff.py` owns the internal profile
handoff. `AcquisitionLaunch` has a distinct `claude-profile-readonly` seam;
the lower-level native seam remains an instrumented/native argv contract.
The acquisition owner creates an exclusive mode-0600 handoff bound to run,
binding, attempt, final context-plan bytes, MCP configuration and executable
identity. The process owner places the handoff identity in its transport scope.
The wrapper checks the retained plan, complete fixed tool set, one APGR server,
server authority and physical paths before exclusively claiming a consumed
marker. Copied, conflicting, changed, unrelated and replayed inputs fail closed.
This is an internal same-user ownership contract, not protection from an
operator able to replace APGR source and environment.

The wrapper removes the private option before native launch. Available tools
are exactly Read and the three APGR MCP tools; only those MCP tools are
auto-allowed. Strict MCP and isolated setting-source doctrine remain. Arbitrary
raw MCP/tool overrides and profile-owned model/effort/settings overrides remain
rejected. The handoff additionally rejects settings and directory overrides.
Ordinary calls retain their existing profile behavior, with explicit strict-MCP
override refusal. No operator/global settings were changed.

The first live construction demonstrated that native plan mode denies MCP even
with the fixed allowlist. The internal handoff therefore selects default
permission mode, following the existing headless-facade pattern while exposing
only native Read plus the three MCP tools. This change is not a live composition
qualification: the corrected probe demonstrated a separate filesystem denial.
The seam remains opt-in and unavailable to ordinary dispatch without its
caller-owned projection/acquisition authority.

## Repeated Read evidence

The first combined non-holdout invocation observed Claude Code 2.1.281 emit
one complete structured text/file result, followed by exactly
`{"type":"file_unchanged","file":{"filePath":"..."}}` for a second native
Read of the same unchanged sentinel. The observer now supports only that
observed deduplication shape. Other aliases, including `unchanged`, remain
unsupported. A prior complete result must precede the repeated tool use, have
the identical requested path and belong to the same stream/session/attempt.
Direct retained source bytes must still match. Partial, error, missing, changed,
concurrent and ambiguous evidence fails closed.

The repeated observation retains its native use/result, visible content and
prior full-result identity. It adds zero controlled recovery bytes and emits no
second source-payload delivery. A second complete structured payload remains
additive. Provider-native unchanged formatting is not APGR-controlled payload.
These parser changes passed synthetic tests; no complete final-source live
stream qualifies their composition with MCP. Incomplete arms must be retained,
never silently excluded from later measurement.

## Authorized non-holdout probes

C1 and C2 shared one initial invocation and their one corrected invocation.
Both used the actual provider builder, profile wrapper, process owner, APGR Go
MCP server and fresh private run. Neither used frozen H task text.

| Attempt | MCP | Native Read | Qualification |
| --- | --- | --- | --- |
| Initial construction | Connected; context_explain denied by plan mode | Full sentinel result, then file_unchanged | C1 failed; repeated shape observed; complete observer rejected denial event |
| Corrected final source | context_explain succeeded | Sentinel Read denied by workingDir; second Read absent | C1 and C2 incomplete |

Both providers exited zero, which does not establish either contract. The
strict observer retained the raw evidence and rejected the permission-denial
event instead of converting failure into zero-byte success. The corrected
native startup exposed exactly the intended tools, one connected dynamic APGR
server, Claude Opus 5, high effort and default permission mode. No Bash, Write,
Edit or Agent tool was exposed. No further rerun is authorized or performed.

Each invocation has a contemporaneous source manifest and a prospective Git
tree computed with a disposable index. The real index was not staged. The final
manifest covers 353 source inputs and private runtime identities; before/after
source and runtime checks match. No bound source changed afterward. The private
packet includes construction, stdin/stdout/stderr, source payloads, sentinel,
raw stream, completion, failed observation, route/admission, transport, MCP and
terminal artifacts. Initial source payloads were reconstructed from the exact
prospective tree captured before launch, verified against its original manifest
and labelled as reconstruction. Original failed artifacts were preserved.
Private packet verification is distinct from public source-seal recomputation.

## Execution and promotion inventories

`testing/h_eval/scenario-bindings.json` binds all fifteen frozen scenario hashes,
both-arm routes, role declarations, authority, exact oracle declarations,
runtime requirements and cohort/recovery/contingency flags. Its null materializer,
importer and substantive-oracle owners are explicit blockers. The provider-free
preflight creates fifteen new unavailable records in the APG166C namespace and
invokes no provider. It is not the required all-subject dry-run and does not
fabricate subjects or successful output. The existing pair runner still requires
caller-supplied implementations and projection authority. A complete single-arm
execution/import/oracle/aggregation driver remains unfinished.

The separate `apg.h-runtime-inputs/v1` contract verifies physical file identities
and optionally rechecks installed provider versions. The Claude probe binds its
actual runtime; the full H provider/settings/projection manifest is not frozen.
No private runtime values or secrets are placed in the public source contract.

`testing/h_eval/promotion-preregistration.json` records three distinct positive
tasks and two semantic non-trigger tasks for each of the five primaries. Each
case binds prompt, clean subject bytes, route source, relevance category,
external command where applicable, independent rubric and evidence of material
guidance use or semantic non-use. Exact skill identities, complete maturity
entries and prior refusal digests remain bound. Go language retains at least
three non-trivial invocations; the other skills retain their qualitative
repeated-use criteria. Three planned cases do not redefine those criteria.
Runtime-dependent rendering and worker evidence must remain unavailable until
the specified runtime exists. A reviewer cannot manufacture missing use.
No task was run, no reserve substituted and no skill promoted. Any skill-body
or case change invalidates preregistration before live use.

## Verification and remaining work

426 affected Python tests passed with zero skips, including actual-wrapper
native argv, real MCP instrumented composition, delivery/recovery, unchanged
Read refusal cases, archive/resume, native-generation import, profile routing,
historical aggregate recomputation and inventory drift checks. The optional
unavailable worker facility was not used. Skill-library, roadmap closure,
phase identity and whitespace checks pass. All 44 protected files match entry:
frozen scenarios/metrics, five skills and maturity records, historical H JSON,
APG166A/B handoff/readiness and APG166B public evaluation. No Go source changed;
Go test/vet and full release qualification were not run.

Initial diagnostics remain disclosed: an unquoted pytest glob failed before
collection; two erroneous direct-launch unit-test attempts reached the installed
CLI with no supplied prompt and exited 1 without retained model evidence; the
test was changed to call rejection functions directly. A malformed heredoc was
corrected before collection. Those attempts receive no qualification credit.

The candidate requires manager disposition of the blocked result. Additional
live probes require new explicit authorization because both corrected reruns
are consumed. Read custody/permissions must compose without broad grants; the
complete scenario execution package, substantive oracles, runtime bindings and
all-subject dry-run remain required. Live H, promotion, Scenario 15 and I cannot
start from this checkpoint. Rollback can remove the optional profile seam and
retain raw evidence; ordinary static dispatch remains the default.

## Revise-close disposition

Disposition: defer

Rationale: The independent work review confirms the blocked result. Retain the
partial implementation as unqualified evidence, with no readiness or live-use
acceptance. Both authorized corrected probe reruns are exhausted. No additional
probe or second substantive review was obtained. Revise-close changes only the
current evaluation, handoff and exit; probe-bound source remains unchanged.
The producer source inventory is retained as its original snapshot. Its review
pending field is historical and superseded by this disposition and the handoff.

| Finding | Disposition | Required resolution before readiness |
| --- | --- | --- |
| 1: Read directory custody | Accept finding; defer repair | Bind narrowly owned recovery access and prove it with a cwd-enforcing fake and a newly authorized live probe. The current fake proves protocol plumbing only. |
| 2: Override test gap | Accept finding; defer repair | Separate rejection assertions and drive wrapper launch with raw overrides and missing scope. Existing passing tests do not establish these cases. |
| 3: Permission mode and prompt tool | Accept finding; defer repair and policy decision | Resolve the departure from plan-mode doctrine explicitly and reject caller permission-prompt-tool on the internal route. Default mode is an unqualified implementation choice, not an accepted policy decision. |
| 4: Post-run config identity | Accept evidentiary gap; defer repair | Recheck config and server-authority identities after child completion. The disclosed same-user contract does not prove post-run identity. |
| 5: Early consumption | Accept limitation | The marker is consumed before executable/version/settings checks. A pre-model failure can burn the attempt; no retry authority is inferred. |
| 6: Prepare-time argv validation | Accept finding; defer repair | Refuse a pre-existing separator during prepare and normalize or explicitly document print spelling before creating the handoff. |
| 7: Repeated Read identity | Accept finding; defer repair | Align retained-payload/path/size authority checks and freshly qualify the final source. Initial file_unchanged observation remains shape evidence only. |
| 8: Promotion attribution | Accept finding; defer preregistration acceptance | Remove checklist-leading prompts or freeze an attribution rubric that distinguishes prompt compliance from skill influence before any live observation. Current tasks are not accepted for promotion evidence. |
| 9: Execution package | Accept blocker; defer completion | Supply concrete subjects, importers, substantive oracles, runtime bindings and the all-subject dry-run. Unavailable preflight records are not that dry-run. |

All findings remain visible; none is overruled. No skill criteria or frozen
inputs were changed. Further repair remains necessary, and a new live-probe
allowance requires manager authority. This checkpoint does not recommend live H
authorization. Final Git and archive disposition belongs to the dispatcher.

Qualification evidence: Revise-close ran `python3 -m pytest -q -p no:cacheprovider`
with `PYTHONPATH=.:libexec:src/test/dispatcher`, an external disposable basetemp,
and the four dispatcher modules `test_h_wrapper_handoff.py`,
`test_h_preregistration.py`, `test_h_claude_reads.py` and
`test_agent_phase_acquisition.py`: 141 passed, zero skips. The first invocation
failed collection because the dispatcher test directory was absent from
PYTHONPATH; the corrected invocation passed. Before revision, a read-only Git
blob comparison matched all 5,989 producer-tree blobs. After revision, all 353
sealed source hashes still matched; 36 selected historical/scenario/skill files
were freshly compared byte-for-byte with entry HEAD. All fifteen preflight
records remain unavailable with zero provider calls and no materialized subject
or executed oracle. `git diff --check` passed. Earlier 426-test, 44-file and packet
claims above are producer evidence, not newly repeated revise-close checks.
Private packet custody and live probes were not requalified in revise-close.

Unresolved concerns: Findings 1-9 above remain open at their stated boundaries.
The phase is blocked, and no complete readiness token can be issued. The amended
disposition documentation has not received a second independent review.
