# APG166B — Claude native recovery-read prerequisite qualification

Phase: APG166B. Continuation: V0130-H-QUAL3. Exit: 00224.
Status: amended after independent work review; prerequisite readiness blocked.

## Result and authority

The candidate qualifies a single full-file native Claude Read observation of
an exact run-owned recovery snapshot, supported by synthetic cases and one
current-Claude non-holdout sentinel probe. It does not establish
`V0130_H_LIVE_EVALUATION_PREREQUISITES_READY`; prerequisite readiness is false. The
[handoff](apg166b/handoff.json) records final verification and the
[readiness inventory](apg166b/readiness-seal.json) binds resulting source.
This is prerequisite qualification, not the frozen H holdout evaluation.

H main gate remains false; live H measured pairs and promotions remain zero.
Scenario 15 remains contingent/unavailable. Static remains the default.
No V0130-I, holdout execution, promotion, reserve substitution, publication or
push authority follows. Manager acceptance and a subsequent bounded assignment
are required before opening any live holdout. No staging or commit occurred.
APG166A's local source acceptance is recorded forward in Exit 00223 and the
roadmap; its historical blocked handoff and inventory are unchanged.

## Observation and delivery contract

The one parser owner is `libexec/agent_phase/claude_read_observer.py`.
The evaluation-only launch seam is `testing/h_eval/claude_reads.py`.
The existing profile live-log owner opens private raw JSONL before child start,
keeps wrapper options out of native argv, and retains its existing stderr,
signal, process-group and exit behavior. A small logging-lifecycle extension
writes a plan/attempt-bound completion receipt after stream drain, file and
parent-directory fsync. Incomplete drain, signal, nonzero exit, raw-log loss or
failed durability prevents complete observation. Normal non-evaluation launches
retain their existing behavior.

The parser bounds UTF-8 JSONL at 64 MiB total and 4 MiB per record. Duplicate
keys, malformed/truncated JSON, duplicate record/tool IDs, missing or reversed
results, errors, ambiguous sessions, nested tool envelopes and unknown partial
Read arguments fail closed. Unknown additive top-level events cannot hide known
tool envelopes. Every native Read is retained with exact input, caller metadata,
ordering, raw record identity and result. Current native wire-input metadata must
agree with the tool-use input.

A recovery delivery additionally requires a captured attempt-authorized path,
successful structured text/file result, matching resolved file path, raw UTF-8
content exactly equal to the prelaunch snapshot, matching source digest, no
partial arguments, start line one and equal returned/total line counts. The
provider-visible result is retained independently from raw file content.
Native line-numbering overhead never becomes a second controlled transmission.
Distinct full-result Reads have distinct stable transmission identities; re-reading
retained evidence does not mint a new transmission. Reading a skill does not
prove semantic guidance use or model consumption.

The pair interface collects raw proof before importing Claude's final result
text, bridges derived recovery events alongside existing transport events, and
retains raw/derived/terminal evidence. Live use requires a ready inventory and
the qualified profile/model route; observed CLI version, model, read-only mode
and tool posture must still match. The recovery exception applies only to
complete Claude stream proof for the current attempt, including a complete
stream with zero Reads. Recovery-file availability does not require consumption. Codex and Antigravity
native recovery remain unqualified. Archive/resume verifies retained evidence
without provider invocation or replay.

## Current-Claude probe

`APG166B-PROBE-1` is one fresh non-holdout qualification attempt through the
actual APGR provider builder, profile wrapper, context adapter and process owner.
It used `normal-final-review`, the current Work Review mapping for implementation
work, with Claude Code 2.1.281, model `claude-opus-5`, high effort, plan permission
mode, isolated settings sources and strict-empty MCP. Native startup readback
exposed only Glob, Grep, Read, WebFetch and WebSearch. Bash, Write, Edit and Agent
were absent. No worker, hook, global setting change or new directory grant was
used. The sentinel-only projection/acquisition stub is probe construction; it
makes no selective-discovery or MCP qualification claim.

Claude performed exactly one native Read of a small non-secret UTF-8 sentinel
and returned `APG166B_READ_OK`. The raw stream was 8,448 bytes. Current structured
`tool_use_result.file.content` exactly retained the underlying file bytes,
including the final newline; visible text used native line numbering. One
observer-derived recovery delivery resulted. Subject, sentinel, Git HEAD and
real index remained unchanged. No corrected rerun was needed or performed.
Subsequent stricter parser checks revalidated the retained stream without a
second model invocation. Private receipts bind the raw bytes, completion,
observations, route admission and terminal result by digest.

Frozen Scenario 12 uses an illustrative `snapshots/skills` location; the existing
G acquisition owner uses `acquisitions/skills`. The observer binds the exact
recovery-entry path in either case. Existing native Read permissions sufficed
for the probe's separate run-owned snapshot root. No broad directory handoff
was introduced. Later holdout subjects and permissions require their own bound
qualification; this probe does not execute Scenario 12 or simulate MCP failure.

## Verification and limitations

The machine handoff records the final required test counts, zero required skips,
parser/adapter coverage, native-generation import check, skill-library,
roadmap/phase identity, frozen-file and whitespace results. Synthetic cases cover
pairing, all Read enumeration, repeated reads, unrelated tools, malformed and
oversized logs, partial/error/path/content mismatches, visible/raw separation,
raw-log failure, route drift, actual wrapper execution, nonzero/signal/timeout,
archive/resume and no replay. A fake CLI exercises the live pair control branch
and result importer; those artifacts are test mechanism evidence only and never
enter H aggregates or promotion counts.

One exploratory broader collection skipped the unrelated optional worker-facade
module because `agent_workers` is unavailable, as declared by the stage envelope.
The required boundary suite was then run explicitly without that module and
without skips. No dependency or worker runtime was added. Coverage tooling's
initial report required combining configured parallel data; a later combine
also encountered a same-prefix XML receipt. Final coverage uses the exact
coverage-data files; neither reporting diagnostic is counted as passing tests.

The parser and evaluation adapter remain separate bounded owners. Existing
large wrapper and pair orchestration owners receive only their local lifecycle
calls; broader decomposition remains deferred. Rollback removes the evaluation
opt-in and restores unconditional live recovery refusal, preserving raw evidence.
No Go source, frozen scenario/metric/oracle, target skill body, maturity semantics,
APG166 historical evidence or APG166A historical JSON was changed. Full project,
release and installed-package qualification were not invoked; the changed native
controller module is covered by generation/materialization import verification.

Source-seal recomputation verifies source identity, not authenticity of private
live receipts. Manager inspection must verify the separately retained probe
packet against the public semantic identity and digests. The source inventory records explicit blockers and no prerequisite token.
Manager acceptance cannot turn the single-Read probe into adaptive-route evidence.


## Independent review disposition and remaining prerequisites

Revise-close amends the producer candidate in response to the supplied review.
There is no second independent review of these amendments.

1. **Readiness overclaim — accepted and corrected.** The observer admits only
   `claude-profile --read-only`; the acquisition adapter requires native
   `--tools Read` and MCP configuration/permission flags. The wrapper rejects
   those overrides and enforces strict-empty MCP. The sentinel acquisition stub
   does not qualify their composition. Claude adaptive acquisition for Scenarios
   11/12 remains unavailable through this observer route. Concrete subjects,
   provider routes, result importers and substantive oracles also remain unbound.
   The regenerated inventory and handoff keep readiness false and omit the token.
   No new MCP permission seam is introduced in this revision.
2. **Zero recovery deliveries — accepted and corrected.** A complete bound stream
   with zero native Reads is valid measurement evidence even when snapshots are
   available. The bridge now accepts this zero-delivery outcome; absent or
   incomplete observation still fails. Synthetic pair tests cover both outcomes
   with explicitly test-only admission, without qualifying the acquisition stub.
3. **Repeated-Read CLI semantics — accepted limitation, deferred qualification.**
   Only one real Read was observed. Synthetic full-result re-reads count each
   actual call, but current CLI unchanged/dedup responses are unqualified and
   fail closed. A synthetic stub case verifies refusal, not live support.
   Partial, image, error and unsupported results on any Read, including subject
   reads, make the entire arm incomplete. This can create behavior-dependent
   attrition; such arms must be retained as incomplete, never silently dropped
   or credited as successful zero-byte reads. A later bounded qualification must
   address this before readiness. No additional live probe was run.
4. **Probe source provenance — accepted limitation.** No contemporaneous
   per-file source manifest was retained at probe time. The producer reports
   later parser tightening and offline revalidation, but final source digests
   alone cannot establish whether the wrapper, adapter or pair runner changed
   after launch. The revised observer is revalidated offline against the retained
   raw stream; this is not a fresh live execution of the final source. The
   original private evidence is preserved rather than retroactively relabelled.
5. **Ordinary-launch import and caller metadata — accepted and corrected.**
   The wrapper imports the observer only for an explicit native-read stream
   scope; a missing module fails evaluation retention closed without crashing
   ordinary live-log runs. Caller metadata now uses the observed tool-use block.
   Subprocess regressions exercise absent, empty, malformed and evaluation scopes.

The local structural change stays at existing lifecycle seams. The large legacy
wrapper gains one bounded optional-evidence helper; general decomposition remains
outside this correction. No dependency, runtime policy, permission or default
changes are introduced. Final revise-close evidence is separately labelled in the
handoff; producer-era counts and live evidence are retained as historical results.


Final revise-close qualification: 379 affected Python tests passed with zero
skips. Scoped observer coverage is 203/211 statements and 112/120 branches;
the evaluation adapter is 38/38 statements and 16/16 branches. This is
parent-process measurement using direct coverage.py because pytest-cov is absent,
not a subprocess coverage-completeness claim. An initial environment-only child
import failure was corrected by including the source package root in PYTHONPATH.
The current allowlisted generation payload passed materialization validation and
isolated observer import; no committed-generation qualification is claimed.
Offline readback verified all 23 retained probe files, the raw-stream digest and
unchanged delivery identity. All 38 frozen files match entry HEAD. Phase identity,
roadmap closure, skill-library, source-seal recomputation and whitespace checks pass.
