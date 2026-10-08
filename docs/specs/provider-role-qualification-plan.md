# Specification: Provider and Role Context Qualification Plan

- **Status**: Authoritative Technical Specification
- **Version**: 1.1.0 (qualification states, MCP lifecycle, Q1 MCP invocation, and acquisition persistence amended under APG159A / V0130-A-CORR1)
- **Governing ADR**: [ADR 0074](../adr/2026/09/0074-context-plan-byte-budgets-and-bounded-mcp-adapter.md)
- **Phase**: APG159 (Milestone V0130-A); amended by APG159A (Milestone V0130-A-CORR1)

---

## 1. Objectives and Qualification Framework

To support adaptive context delivery, APGR must qualify provider capabilities across four orthogonal axes:
1. `skill_selection_projection` — Delivering only selected skills to the provider runtime.
2. `instruction_slice_projection` — Delivering mode-specific instruction slices (e.g. RTK hook vs instructions).
3. `late_acquisition_cli_channel` — Executing `apgr skills search` and `acquire` via shell.
4. `late_acquisition_mcp_channel` — Acquiring skills in-band via stdio MCP JSON-RPC protocol.

### 1.1 Evidence and Qualification States
To eliminate unsupported "Supported" assertions, provider capabilities must be classified into six rigorous qualification states backed by concrete source evidence:
- **`inspected`** — Code inspection of existing launcher scripts, CLI argument builders, and filesystem templates confirms interface compatibility.
- **`documented`** — Upstream provider documentation or official specification describes the interface mechanism.
- **`planned`** — Architectural design completed; implementation and test fixtures scheduled for milestones V0130-E through V0130-G.
- **`experimental`** — Candidate mechanism identified (e.g. Claude `--add-dir` or isolated settings) but live selective delivery and isolation remain unverified empirically.
- **`qualified`** — Empirical execution with live provider instances demonstrates end-to-end functionality, measured token savings, and zero authority drift.
- **`unavailable`** — The provider or role binding fundamentally lacks support (e.g. Antigravity per-run selective skill projection, or Claude read-only review without Bash).

Phase V0130-A establishes `inspected`, `documented`, and `planned` baselines. No provider is marked `qualified` for adaptive delivery in this foundation phase; live qualification is scheduled for V0130-H.

---

## 2. Provider Capability Matrix

| Provider / Role Combination | Selective Skill Projection | Instruction Slice Projection | Late Acquisition (CLI) | Late Acquisition (MCP) | Overall Posture |
|---|---|---|---|---|---|
| **Codex (Producer / Mutation)** | **`planned`** (Tier 1: config flag inspection; live discovery unverified) | **`inspected`** (Tier 1: inline developer instructions slice) | **`inspected`** (Tier 1: native shell tool permitted) | **`experimental`** (G native argv/protocol harness; no live qualification) | Full Adaptive Candidate |
| **Codex (Reviewer / Read-Only)** | **`planned`** (Tier 1) | **`inspected`** (Tier 1: read-only instruction slice) | **`planned`** (Tier 1: run-store stdout return) | **`experimental`** (G native argv/protocol harness; no live qualification) | Full Adaptive Candidate |
| **Claude (Producer / Mutation)** | **`experimental`** (Tier 1: candidate `--add-dir` / isolated root; live selective discovery unverified) | **`inspected`** (Tier 1: `CLAUDE.md` slice projection) | **`inspected`** (Tier 1: Bash tool permitted) | **`planned`** (Tier 1/2: `--mcp-config` stdio injection) | Candidate Adaptive (Contingent) |
| **Claude (Reviewer / Read-Only)** | **`experimental`** (Tier 1: isolated settings directory; unverified) | **`inspected`** (Tier 1: read-only notice slice) | **`unavailable`** (Bash withheld to protect read-only fence) | **`experimental`** (G native Read-only seam; profile wrapper unqualified) | MCP-Primary Adaptive |
| **Antigravity (Producer / Mutation)** | **`unavailable`** (Global skill directory `~/.gemini/antigravity-cli/skills` only) | **`inspected`** (Tier 1: `GEMINI.md` slice projection) | **`inspected`** (Tier 1: terminal commands available) | **`experimental`** (MCP transport unqualified) | Static Default / Opt-in |
| **Antigravity (Reviewer / Read-Only)** | **`unavailable`** (Global skill directory only) | **`inspected`** (Tier 1: read-only prompt slice) | **`unavailable`** (Terminal restricted during review) | **`experimental`** (MCP transport unqualified) | **Static Default** |

---

## 3. Strict Safety and Role Rules

### 3.1 No Synthetic Authority Expansion
- Under no circumstances will shell tools (`Bash`) be enabled on a Claude read-only review stage merely to satisfy a CLI acquisition test.
- Claude read-only reviewers rely exclusively on the in-band stdio MCP adapter for late acquisition, preserving least-privilege security boundaries.

### 3.2 Antigravity Usable Static Fallback
- Antigravity currently loads skills from a single global path (`~/.gemini/antigravity-cli/skills`). Per-run selective skill projection is not supported natively without mutating the user's global configuration.
- APGR strictly preserves Antigravity's **first-class static mode**. Antigravity runs default to static delivery until a non-destructive per-run projection mechanism is qualified. Static fallback is a successful architectural outcome, not a failure.

---

## 4. Qualification Test Scenarios

Milestones V0130-F through V0130-H will execute four concrete qualification gates:

1. **Gate Q1: Codex MCP Tool Invocation**
   - Inject stdio MCP adapter configuration via `-c mcp_servers.apgr={...}` into Codex launch arguments.
   - Assert Codex invokes the MCP tool `skill_acquire` with `{"id": "apgr:go-test-profile"}`.
   - Assert MCP server returns the complete canonical skill body directly in the tool result payload and records the acquisition event.
2. **Gate Q2: Claude Read-Only MCP Acquisition**
   - Verify `--tools` excludes Bash and includes `mcp__apgr__skill_acquire`.
   - Assert reviewer acquires a required skill without producing worktree, index, or HEAD drift.
3. **Gate Q3: Mid-Turn Recovery Fallback**
   - Simulate MCP server process termination mid-turn.
   - Assert provider completes the turn using run-owned pre-materialized snapshot fallback without replaying the turn or aborting the run.
4. **Gate Q4: Antigravity Static Baseline Equivalence**
   - Verify Antigravity dispatch with `mode = "static"` is byte-identical to v0.12 prompt transport (with corrected RTK slice).

## F candidate evidence boundary (APG164)

The existing selective-discovery and acquisition rows retain their experimental,
planned or unavailable states. No row has been promoted to qualified by F.
Normal bindings use static transport even when adaptive is requested. The
projection adapter seam requires both selective projection and independently
readable recovery evidence; no live adapter is shipped.

Instrumented V1 branches cover Codex, Claude and Antigravity runner-bound inputs;
V2 records each actual merged binding and attempt. Fixtures preserve readonly
launch arguments and RTK on/off behavior, selected-home authority and optional
worker fallback. Native generation and installed CLI checks exercise maintained
module/resource boundaries. These prove APGR-controlled behavior only; they do
not prove provider discovery, model consumption, token savings or suppression of
ambient native skills. Q1–Q3 remain G/H work; no live dogfooding was performed.

F-CONTEXT1 replaces historical estimated accounting for F checks with exact
source plus explicitly synthetic envelope measurements. Scenario 03's historical
31,544-byte sum exceeded its unchanged 30,000-byte threshold. Its effective
transport expectation is static. Cohorts and H median/p95 thresholds remain
unchanged; unit tests do not establish H benefits or skill promotions.

APG164 revise-close narrows runtime prospective-plan evidence: actual V1/V2
callers supply work-class facts only, with no explicit skill requests or role
affinities. Language/runtime/test ownership is a pure API and consumer-fixture
proof, not automatic repository fact capture. Antigravity maps to the Go-library
consumer contract without gaining live qualification. Configuration is captured
per attempt independently of routing/RTK run capture; changes between attempts
may affect context settings or validation. Static raw-byte transport remains
available with character count unavailable for non-UTF-8 input.

## G controlled-channel evidence boundary (APG165)

APG165 implements the shared acquisition engine, CLI and real stdio MCP protocol
process. Instrumented read-only actors exercise exact body recovery, disposable
native argv configuration, prelaunch fallback and mid-turn native snapshot reads.
Native Claude admission retains Read and adds only the three APGR MCP tools
to availability and the MCP permission allowlist;
Bash is absent. Native Codex injection adds the named run-owned MCP declaration.
These are explicit caller seams, not qualification of the existing profile wrapper
or of provider behavior inferred from its name.

Q1/Q2 acquisition protocol and Q3 recovery availability have controlled harness
evidence; their live invocation, substantive critique/task results and model-use
claims remain unqualified. The three implemented native MCP cells are experimental; none is qualified.
Q4 static behavior remains covered by the existing V1/V2 context regressions.
Antigravity is unchanged. No empirical token savings or H paired benefit follows.

The native acquisition seam does not establish filesystem read permission for
the run directory. Its caller must independently authorize and qualify that scope;
G checks instrumented reads and exact argv only. No live row is promoted.

## H produced evidence boundary (APG166)

No provider-role capability is promoted to qualified. The repository-owned H
harness invokes the native planner and records controlled test evidence, but
has no qualified live paired provider route. All live task/critique outcomes,
provider-native bytes and token observations remain unavailable. Scenario 15
remains contingent: isolated settings and MCP configuration are not evidence of
selective discovery without leakage. No filesystem permission is broadened.
Antigravity remains static. The H gate is unsatisfied; the
[H evaluation and I handoff](../evaluations/apg166-maturity-and-integrated-evaluation.md)
require static to remain the default pending sufficient evidence and I authority.

## APG166A mechanism readiness

The continuation qualifies controlled transport recording through the shared
V1/V2 process owner, native Codex argv, the actual Claude profile launcher and
the actual Antigravity launcher using instrumented executables. It also qualifies
the pair interface through real subprocesses, acquisition channels and the
bounded recovery-read seam. Fake actors establish no model quality, native
selective-discovery qualification or measured adaptive benefit. Every provider
capability cell above retains its prior state. Scenario 15 remains contingent.

The repository-owned interface is `testing.h_eval.paired.run_pair`. The caller
must supply equal provider/profile/model/binding/role identities, frozen scenario
and clean subject inputs, authorized executable paths, a result importer, and an
external task-oracle callback returning `apg.h-task-oracle/v1`. It uses APGR's
argv builder, context adapter and provider runner rather than a second launcher.
The caller must independently qualify selective projection and native read
authority before requesting an adaptive route. Missing observations, a failed
start, nonzero result, malformed import or timeout retain the admitted attempt
and fail closed; an existing pair directory cannot be replayed. `read_pair`
verifies retained artifact digests after archive/resume without launching a
provider. Instrumented output is labelled runner qualification and is not H raw
benefit data. Live execution additionally requires the accepted readiness seal.

The common `prompt` carries the identical task/role envelope. Optional exact
`static_context` bytes carry the baseline skill context; adaptive bodies come
from the unchanged planner/projection seam. This keeps the task constant while
allowing only the delivered context to differ. A caller must not substitute
native discovery estimates for those transmissions. Ambient discovery outside
the qualified observation scope cannot establish complete live H coverage.

A separately authorized prerequisite continuation must bind concrete subjects,
provider versions/model routes, result
importers and substantive oracle implementations before opening the holdout.
Those are evaluation prerequisites, not evidence supplied by fake actors.
It must verify the accepted APG166A source and readiness inventory. Changing a
sealed selection, measurement or transport input after seeing results invalidates
the entire live set. Neither this interface nor its tests authorize APG166B,
promotions, a default change, Scenario 15 qualification or V0130-I.

APG166A revise-close does not establish prerequisite readiness. Live arms exposing
recovery snapshots are incomplete until a qualified native-read observer exists;
this plumbing must be completed and resealed before any live holdout is opened.
The interface now requires explicit catalog `capture` for live calls and a frozen
`runtime_inputs` mapping from physical controlled-file references to exact
`bytes`/`sha256` identities. It preserves overrides and the catalog home and checks
runtime settings against observed handoffs. These runtime inputs are separate
from the public source inventory. Binary subjects are supported within the archive
budget. No second independent review covers the revise-close amendments.


## APG166B native Read observation and blocked prerequisites

This continuation qualifies only observation of native Claude Read deliveries,
using the current Work Review route's `normal-final-review` family, actual
profile wrapper, context adapter and provider runner. One non-holdout sentinel
probe used Claude Code 2.1.281, model `claude-opus-5`, high effort and the existing
read-only tool contract. Native Read succeeded without an additional directory
handoff. Bash remained absent, settings sources isolated and MCP strict-empty;
no hooks or global settings were added. No capability cell above is promoted.

The parser enumerates all native Reads, binds ordered tool-use/results within
one session, and rejects malformed, partial, missing, duplicate, ambiguous or
error evidence. Raw file identity and provider-visible formatting are separate.
Only exact authorized recovery snapshots produce delivery events. The probe
establishes neither selective discovery nor meaningful skill use, MCP failure
recovery, token savings, task quality, Scenario 15 or H paired benefit.

The [APG166B evaluation](../evaluations/apg166b-native-read-qualification.md)
owns qualification and limitations. Raw receipt custody is private; the public
inventory binds semantic probe identity and digests without host-path dependencies.
Its source recomputation is distinct from manager inspection of live evidence.
No Codex or Antigravity native-read qualification is implied. Holdout execution
still requires manager acceptance and a subsequent bounded authorization.


The supplied independent review identified an incompatible route composition:
`claude_reads.prepare` admits the read-only profile wrapper, while
`AcquisitionLaunch` requires native Claude tools/MCP flags that wrapper rejects.
The sentinel stub bypassed acquisition and supplies no evidence for this seam.
APG166B revise-close therefore retains false readiness with explicit blockers,
including unbound evaluation inputs and unqualified current-CLI repeated Reads.
Zero recovery deliveries from a complete bound stream are valid; unsupported
partial/error/image/dedup Read results still fail the arm closed, with potential
behavior-dependent attrition. No second independent review covers these revisions.
