# APG95 Go Reporting Library Vertical Slice

## Accepted result

APG95 implements the first library-first Go slice frozen by Accepted ADR 0051.
The root module is
`github.com/Knowledge-Forge-AI/agentic-praxis-grimoire` with a `go 1.25`
directive and no third-party dependency. Public packages are `schema` and
`report`; exact-argv Git execution and atomic publication mechanics remain
under `internal/`.

During APG95, Python remained the active report CLI and compatibility oracle. APG95 adds no
`cmd/apgr`, changes no Python route, and performs no release, publication,
deployment, JACA, `.flakes`, Nix, skill, environment, or hotspot work.

## Implemented surface

The public report surface provides `New`, reusable `Service.Show` and
`Service.Diff`, in-memory `Operational`, strict `ParseRecords`, and optional
`Append`. Requests and results are value-oriented; byte slices and evidence
maps returned by successful calls are defensively copied. Independent Show
calls are safe for concurrent use.

Native Git uses `exec.CommandContext` with exact argument vectors and no shell.
The child preserves the process environment while overriding `LC_ALL`, `LANG`,
`GIT_PAGER`, `PAGER`, and `GIT_OPTIONAL_LOCKS`. Diff refuses inherited
`GIT_INDEX_FILE`, unsupported sparse/split/unmerged state, empty snapshots, and
HEAD/index/status/staged/unstaged/worktree drift. Its temporary index is
invocation-owned and does not mutate the real index.

Publication keeps one current primary, owner-only modes, direct-regular reads,
no-follow behavior, bounded locking, conservative stale-lock recovery,
recoverable transaction markers, fsynced temporary replacement, atomic rename,
and stale-primary cleanup. A later Git primary supersedes and removes an
ops-only primary exactly as the Python oracle does. It does not carry the ops
record into the new Git primary; this is the recorded interpretation of the
APG94 architecture's imprecise “absorbs” wording.

## Differential evidence

The maintained Go corpus exercises 22 accepted exact-byte comparisons:

- seven Show cases: root, ordinary, empty, rename, binary, unusual-path/full-
  message, and first-parent merge;
- seven Diff cases: staged, unstaged, mixed, untracked, intent-to-add, rename,
  and binary;
- five Operational cases: canonical, legacy, free-form, Show-associated, and
  Diff-associated; and
- three full publication cases: Show plus operational append, Show-to-Diff
  supersession, and ops-only-to-Show supersession.

Eleven differential rejected-input cases bind Go sentinel families to the
Python CLI's stable usage/runtime classes: two Show, three Diff, and six
Operational cases. Additional Go invariants cover worktree/index/HEAD drift,
active cancellation, no real-index mutation, repeated valid operational
records, strict parsing, defensive copies, exact Git argv and environment,
live-lock refusal, dead-lock recovery, pre/post-publication transaction
recovery, permissions, and symlink/hard-link refusal.

The current focused Python oracle regression is 114 tests (82 unit tests
under `src/test/unit/.../libexec/agent_report` plus 32 integration tests under
`src/test/int/.../bin/`), correcting the earlier planning figure of 56. The Go
suite reports 64 passing tests and subtests across four packages. An executable
temporary module outside APG imports `report`, constructs a service, calls Show,
and parses its returned bytes without importing APG internals, invoking
`cmd/apgr`, invoking Python, or invoking a shell at the consumer boundary.

Copy detection is not claimed as a separate qualified fixture: the Python
authority enables `--find-renames` but not copy detection, so a stable copy
classification is not part of accepted APG95 parity.

Focused public-release policy tests passed 46 unit cases. The broader historical
public-release integration selection passed 15 cases and failed one fixture
because that fixture's configured Nix-store Python interpreter did not contain
pytest. The failure occurred before candidate validation and named no APG95
source or policy mismatch; it is an environment/infrastructure gap, not a
passing projection claim. Record-identity and skill-library unit/integration
regressions independently passed 160 cases with one intentional skip.

## Preserved state and limitations

Version remains 0.6.0. The skill corpus remains 39 canonical / 39 catalog / 39
projections / 39 discoverable, with 14 stable and 25 provisional, zero
malformed, 9,504 description bytes, 9,492 characters, and the 9,527-byte
ceiling unchanged. Existing CSS and JavaScript qualification debt is untouched.

The current Python CLI remains semantically authoritative until APG96. CLI
path/recovery adapters, Go build-version injection, embedded resources,
cross-consumer JACA integration, distribution artifacts, v0.7 versioning, and
publication remain deferred. Current v0.6 public-release projection policy is
unchanged; later v0.7 packaging phases own release inclusion for the new Go
source.

## Operator acceptance reconciliation

The dispatcher-reported closeout provenance states that finalization could not
own the commit because entry was classified `ENTRY_DIRT_OVERLAP`. The operator
subsequently accepted and committed the exact reviewed closeout tree without a
source-byte change as commit
`04f135980385eda54496b89f9908cc86f52d2884`, tree
`fe3ca7a11007c09e165abddf0de2757dec4e2b08`. These identities record APG95's
terminal acceptance; they are historical evidence, not a successor hash gate.

## Disposition

APG95 is terminally accepted with disposition
`V07_REPORTING_GO_CORE_READY_FOR_APG96`.

APG96 is the separately authorized active successor.
