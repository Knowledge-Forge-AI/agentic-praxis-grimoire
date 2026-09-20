# Local skill acquisition (G candidate)

## APG166A controlled delivery and retention

Successful CLI/MCP response events extend `apg.acquisition-event/v1` with
`payload_sha256`, `phase`, `provenance` and `observation_kind`. The byte count and
digest cover the exact written frame, including its newline. Existing count-only
records remain readable but cannot establish complete H delivery coverage.
Failed/short writes and protocol/tool errors do not become successful deliveries.
Preparation events are excluded. Initial MCP discovery responses are initial
until the first tool/resource read; subsequent requests and repeated discovery
are late transmissions. No model observation is inferred.

`acquisition_records.delivery_entries` bridges retained raw observations directly
into H's delivery shape, independently of SQLite. It sorts by identity, coalesces
identical views, retains distinct repeat transmissions, and reports incomplete
coverage for missing payload identity or conflicting views. The evaluator must
also require complete launch traces; an empty event list is not proof of complete
invocation coverage.

`read_recovery` is a bounded evaluation/native-read seam over the attempt's exact
captured recovery allowlist. It verifies source bytes and records a late
`recovery_read` only after a complete witnessed handoff. It neither watches
arbitrary filesystem reads nor grants Bash or broader provider permissions.

Installed CLI and provider-launch preparation now use the same retention owner.
Canonical JSON is content-addressed. A server alias is keyed by run, binding and
attempt, links its retained canonical bytes, and refuses conflicting reuse.
The shared limit is 64 retained authority/configuration names, each at most
1 MiB, plus one pending file and one lock. Legacy authority, prelaunch, server
and MCP names count toward admission. Identical retries reuse bytes; exhaustion
requires a new run and never deletes canonical evidence. Interrupted publication
leaves at most one recoverable pending inode. The owner rejects symlink traversal
and never cleans acquisition events, plans, recovery snapshots or responses.

These limits do not reserve all run storage. The existing archive budget remains
128 MiB selected uncompressed evidence, 64 MiB per file, 20,000 entries and
256 MiB archive output. Exceeding archive bounds preserves the local run and
fails archive delivery; launcher retention is not a whole-run success guarantee.

APG165 adds a shared native acquisition engine to the existing CLI and a bounded
stdio MCP server. Acquisition is optional. Static dispatcher mode does not probe
or start the server. This candidate does not qualify live provider discovery,
model consumption, task quality, token savings or adaptive benefit.

## CLI and authority

```sh
apgr skills search 'go test' --run-dir /selected/run \
  --run-id run --binding-id review --attempt-id attempt --consumer claude
apgr skills acquire apgr:go-test-profile --run-dir /selected/run \
  --run-id run --binding-id review --attempt-id attempt --consumer claude
```

The run directory must already exist. All acquisition writes belong there.
Python captures project/home precedence and project-only override authority
through the same owner as catalog listing. Explicit project/home flags override
discovery. Native callers can supply explicit roots or a captured JSON authority
with `--config /selected/run/authority.json`. Native code does not parse TOML or
discover environment configuration. The authority is private run data, not
operator settings. No dependency on MCP is introduced into CLI acquisition.

Search is case-insensitive substring matching over metadata, ordered by qualified
identity, with at most 100 rows and a 256-byte query. It does not rank applicability
or change planner weights. Results identify requested and selected sources.
Acquisition requires qualified `apgr:`, `project:` or `user:` identities and
preserves E's consumer restrictions and explicit overrides. Unavailable override
targets never silently fall back to canonical bodies.

CLI results are JSON: `selection.snapshot.body` and `support` contain base64 exact
bytes. MCP returns the complete UTF-8 SKILL.md directly as its first text content
block and a separate identity/support envelope with base64 support bytes. These
are encodings of the selected snapshot, not regenerated skill prose. The engine
executes no skill, subprocess or network request. Public Go API signatures remain
unchanged; this channel engine is private implementation.

## Storage, bounds and observations

Bodies and declared support are exclusively created under
`acquisitions/skills/<snapshot-digest>/<selected-qualified-id>/`. Each event is
an atomically published, exclusively linked, one-line `acquisitions/event-<event-id>.jsonl` artifact.
A private pending file is synced before no-replace publication; interrupted pending files are not events. Existing records are never rewritten. Filenames refine ADR 0074's illustrative
sequence layout so independent processes and attempts do not share a journal.
An event identity hashes the run, binding, attempt, process-local random 128-bit
nonce and sequence. It does not rely on clocks or directory enumeration.

Requested, rejected, materialized, available and channel-delivered events are
distinct. Search misses, repeat availability and recovery observations are
explicit. A successful writer observation counts the exact serialized channel
bytes, including the envelope and newline. Repeat transmissions count again.
Materialized/available records do not prove a successful channel write. An event
references prior acquisition facts instead of updating them to assert later facts.
Prelaunch uses `skills acquire <id> --prepare-only --config <authority>`: its `recovery_candidate`, materialized and available events use channel `preparation`, with no agent request or channel-delivery claim. Preparation remains historical even if launch falls back to static, and never marks the first real acquisition as a repeat.
All provider/model observations and token counts remain unknown/unavailable.

The run store uses confined filesystem access, direct directory checks,
exclusive files and a nonblocking advisory writer lock. Source capture retains
E's bounds. Channel results and retained context inputs are limited to 768 KiB;
stdio lines and responses to 1 MiB; nesting to 32; a session to 4096 messages;
raw run events to 4096 and events per binding (across attempts) to 256. Exact selected snapshots are reused after byte verification; every delivery still emits distinct events. Materialized files/directories are capped at 4096 entries and 24 MiB per run, below whole-run archive limits. These caps reserve no space for unrelated run artifacts and do not guarantee arbitrary whole-run archive size. Oversized results fail rather than truncate bodies.
The server sends no requests; clients own finite connection/read deadlines and
close stdin for shutdown. It does not implement a daemon or cache service.

The Python persistence owner can idempotently index raw event identities into
the existing artifact table. V2's optional adaptive invocation completion invokes
that projection; raw reads remain available independently. Index diagnostics are
separate run artifacts. No SQLite driver, migration, CGO or shared database is
added. Resume collection reads retained records without catalog resolution;
malformed optional event entries are retained, omitted from the valid projection and reported diagnostically, so they do not block ordinary resume. Whole-run archive traversal includes the acquisition files under existing bounds.

## MCP protocol and resources

`apgr mcp serve --config /selected/run/authority.json` uses newline-delimited
JSON-RPC with the intentionally pinned **2025-11-25** revision. Initialization
negotiates that supported revision, followed by `notifications/initialized`.
A client requesting an incompatible revision receives the pinned revision and
must disconnect if it cannot support it. There is no JSON-RPC shutdown method;
EOF ends the process. See the pinned [lifecycle specification](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle).
A protocol upgrade requires a separate decision.

The tools are exactly `skill_search`, `skill_acquire` and `context_explain`.
Discovery also exposes exactly `apgr://skills/{namespace}:{id}` and
`apgr://context/{run_id}/{binding_id}` templates. The skill template is the RFC 6570 spelling of the accepted qualified-ID family. Scope components are URI-escaped.
Skill resource reads explicitly acquire the requested permitted snapshot and
count their delivery again. Context reads return the captured immutable F record
and scoped raw acquisition observations, never a plan recomputed against current
source. Missing context is reported as null. An optional allowed-ID list narrows
search/acquisition/resource authority; an empty list grants no skill access.

Ping, tool/resource discovery, calls and reads accept reserved request `_meta` objects. Lists are single-page and issue no cursors; supplied continuation cursors are rejected as invalid parameters. This follows the pinned [metadata](https://modelcontextprotocol.io/specification/2025-11-25/basic#_meta) and [pagination](https://modelcontextprotocol.io/specification/2025-11-25/server/utilities/pagination) contracts. Other methods,
subscriptions, arbitrary paths, subprocess tools and plugin hosting are absent.
Invalid shapes, duplicate fields, invalid UTF-8, trailing JSON and oversized
frames are rejected. stdout contains protocol frames only; diagnostics use stderr.

## Dispatcher and recovery boundary

v0.13 pilot note (APG166X, historical): late acquisition was not wired into
normal V1/V2 bindings, so ordinary runs recorded no late acquisition events.

APG166Z-CONTEXT1 wires it for the ordinary adaptive Claude route only (see the
[context-planning guide](context-planning.md)). A separate ordinary seam
(`OrdinaryAcquisition` in `libexec/agent_phase/context_route.py`) reuses this
guide's engine, retention and prelaunch helpers: it allows only deferred
embedded `apgr:` skills (at most 128), prepares budget-deferred requests (at
most 16) as exact recovery copies with `skills acquire --prepare-only`, probes
`mcp serve` before and after writing the final authority, and stores a compact
plan view (identity, modes, decisions and costs; no prompt or payload) so the
768 KiB `context_plan` bound is not reached. No project root or APGR home is
passed, so the server never reads live source roots. The wrapper-private
`--apgr-context-acquisition` handoff (schema
`apg.claude-context-acquisition/v1`) is validated against the attempt scope
digest and claimed once; the wrapper adds the `apgr` server beside the worker
facade and grants the three tool names plus exact `Read(//file)` rules. The
evaluation-only `--apgr-acquisition-handoff` contract below is unchanged and
the two cannot be combined. When run-owned
`acquisitions/event-*.jsonl` files exist, the provider-free
[operational observation summary](operational-observations.md) reports their
kinds, misses (`search_miss`, `rejected`) by requested ID, repeat deliveries and
late controlled bytes, using the same bounded reader as this guide.

The existing qualified projection interface may attach an `AcquisitionLaunch`
for an explicitly configured native Codex or native Claude read-only argv seam.
This is not provider-name inference and does not enable the existing Claude
profile wrapper. Normal V1/V2 bindings still have no qualified selective
projection; their effective mode stays static. Antigravity remains static.

The optional seam acquires selected recovery candidates through the shared CLI
before launch, probes the real server with bounded streams/deadline, creates
run-owned MCP configuration, and appends exact native-read recovery paths to the
controlled prompt. The final transport budget includes those additions. Failures
or overflow return the original static argv/stdin before the actor is invoked.
Claude native read-only admission requires exactly `Read` as its existing native
tool list, then adds only the three named APGR tools to availability and `--allowed-tools`. Existing native Read permission and run-directory scope must be independently established by the caller. The seam does not add `--add-dir`, grant native filesystem permission, or prove the provider can read the run directory. It never adds Bash.

MCP failure during the actor turn does not restart the actor. The independently
materialized snapshot is available for native recovery only where the caller has
already established read permission for that exact run directory.
`native_read_authorized` is a caller assertion, not a permission probe or live
provider qualification. Instrumented harnesses can append separately witnessed failure and
native-read observations. A merely readable path never implies the model read it.
No live provider is invoked by qualification. Scenarios 10–14 retain their frozen
cohorts and task oracles; G evidence addresses controlled recovery/protocol/Git
mechanisms. H still owns substantive model task outcomes and paired benefit.

Events are sorted deterministically by identity, not wall-clock chronology.
Acquisition links identify causality within each delivery; no global cross-process
time ordering is asserted. The bounded search currently resolves each matched
row through the shared catalog resolver; optimization is deferred.

## H measurement and authority retention

APG166 bounds installed CLI authority retention with immutable content-addressed
reuse, a serialized admission check and one reusable unpublished staging file.
A new run admits at most 64 records of at most 1 MiB each. Existing UUID records
count toward the limit and are never deleted to make room. Reaching the limit
refuses a new authority; retain the run for audit and select a new run. Identical
configuration bytes reuse their exact authority; selected skill snapshots and
source/override provenance remain canonical audit evidence. Interrupted staging
never rewrites a published authority or deletes acquisition history.

Successful non-acquisition MCP frames and CLI search output now emit
`response_delivered` with exact serialized bytes. Acquisition responses retain
`channel_delivered`; these two categories do not overlap for a single frame.
A failed/short write or error response is not a successful delivery. Repeated
responses count again, including an explanation's serialized historical views.
Preflight uses explicit preparation authority and `preparation_response`; it
cannot serve agent tool/resource requests or count toward provider delivery.
If a delivery observation cannot be recorded, the server reports the failure and
stops. Consumers must reject incomplete traces for cumulative-byte gates.

The [H evaluation](../evaluations/apg166-maturity-and-integrated-evaluation.md)
separates these channel facts from provider observation and explains which
initial prompt/configuration and witnessed recovery components must also be
present. No live provider capability or measured benefit is established by H.

### APG166A revise-close recovery limit

The pair interface rejects complete live coverage whenever recovery snapshots are
exposed: arbitrary native Read operations are not connected to the instrumented
read seam. A witnessed fake recovery read cannot fill that gap. APG166A prerequisite
readiness remains blocked until the provider observation seam is qualified and the
pre-live inventory regenerated. Read-only Claude gains no Bash authority.


## Evaluation-only Claude native Read observations

APG166B adds `testing.h_eval.claude_reads` over the existing `claude-profile`
live-log mechanism. Explicit read-only evaluation opts in before invocation;
ordinary static launches retain their argv and exec behavior. The wrapper opens
mode-0600 raw stream storage before child start and emits a plan-bound receipt
only after successful termination, stream drain and fsync. Missing, altered,
truncated or undurable evidence cannot establish coverage. Wrapper live-log and
display options are removed before the native CLI launch.

`agent_phase.claude_read_observer` accepts bounded UTF-8 JSONL (64 MiB total,
4 MiB per record), rejects duplicate keys and enumerates every native Read.
Tool-use IDs and results must pair in order in one session, with one successful
terminal result. Unknown additive events are accepted only outside known tool
envelopes. Partial arguments, unknown Read arguments, error results, nested
sessions, path mismatches and incomplete line metadata fail closed.

The successful text/file result's raw `file.content` must exactly equal the
prelaunch authorized snapshot bytes and digest, with `startLine == 1` and
`numLines == totalLines`. The provider-visible `tool_result.content` is retained
separately with its own identity; it never adds a second controlled transmission.
For text-block arrays the identity is explicitly labelled JSON serialization;
the complete raw record preserves the original representation. Every repeated
actual recovery Read with a complete structured file result counts again. Current
CLI unchanged/dedup responses remain unqualified and fail closed. Re-reading evidence creates no new event ID.
Reading a skill never establishes semantic guidance use.

The evaluation bridge relaxes live recovery refusal only after complete Claude
stream proof, including zero Reads when no snapshot is consumed; other providers
retain the block. Complete observation does not require a recovery delivery. Stream, completion receipt,
derived observation and terminal evidence are ordinary run-owned archive inputs.
Resume verifies retained identity without launching a provider. These interfaces
confer no permission or automatic retry. Scenario 12's frozen illustrative
`snapshots/skills` location and G's actual `acquisitions/skills` location are both
handled through exact attempt-owned recovery entries, never a broad directory
allowlist. A later evaluation must independently qualify its actual read scope.


This observer does not qualify a live adaptive acquisition route. The read-only
profile wrapper rejects caller-supplied native MCP flags required by the
evaluation `AcquisitionLaunch`; APG166B prerequisite readiness therefore
remains false. (The ordinary APG166Z-CONTEXT1 route composes MCP inside the
wrapper instead; it is an operational opt-in, not an H qualification.) Unsupported results on
any native Read (including non-recovery partial/error/image or dedup results)
make the arm incomplete. Preserve those failures as possible outcome-dependent
attrition. The single real sentinel Read does not qualify repeated-Read behavior.
