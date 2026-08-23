# Go Library Reference

APG's embeddable module is
`github.com/Knowledge-Forge-AI/agentic-praxis-grimoire` at Go 1.25. Public
consumers import root packages directly; they do not import `cmd/apgr` or any
`internal/` package.

## Package map

| Package | Purpose | Detailed owner |
| --- | --- | --- |
| `schema` | Shared schema and envelope version constants | This reference |
| `report` | Commit, worktree, and operational evidence plus optional publication | [Reporting](#reporting) |
| `skills` | Embedded corpus, deterministic bundle resolution, and isolated materialization | [Skill context bundles](../guides/skill-context-bundles.md) |
| `envsnap` | Strict profiles, canonical snapshots, storage, loading, and resolution | [Environment snapshots](../guides/environment-snapshots.md) |
| `hotspot` | Bounded structural analysis, stable results, and renderers | [Hotspot analysis](../guides/hotspot-analysis.md) |

APG exposes no orchestration package. A consumer supplies context, structured
requests, repository or storage authority, and its own lifecycle decisions.
The [APG–JACA boundary](../architecture/apg-jaca-integration.md) is the
controlling integration contract.

## Reporting

Consumers import `report`, construct a repository-bound `Service`, and call
`Show` or `Diff` with a `context.Context`. `Operational` validates
caller-supplied bytes and already parsed records entirely in memory.
`ParseRecords` validates canonical common-envelope records, and `Append`
optionally publishes one record under the owner-only APG outbox convention.

Results contain the parsed record, exact canonical bytes, and fresh
caller-owned evidence copies. The package does not require `cmd/apgr`, Python,
or a shell at the consumer boundary. Report collection may execute the
caller-selected native Git binary through `exec.CommandContext`, fixed exact
arguments, bounded streams, deterministic locale/pager/lock controls, and the
remaining inherited environment.

Public sentinel errors support `errors.Is`; context cancellation and deadlines
remain the standard context errors. Diagnostics do not contain report bodies,
patches, environment values, or caller-supplied absolute paths.

## Compatibility authority

The maintained Python implementation under `libexec/agent_report/` was the
active CLI owner and byte-level compatibility oracle through APG95. APG96 keeps
it as a frozen, directly invoked test oracle while normal canonical and
historical report routes delegate to the Go CLI.

Accepted Show, Diff, and Operational fixtures compare exact canonical bytes.
Rejected fixtures compare stable failure families and mutation-safety
postconditions. Publication tests separately preserve owner-only modes,
single-primary supersession, append behavior, locks, stale-lock recovery,
transaction recovery, atomic replacement, and link refusal.

The Python oracle removes an operational-only primary when a later Git primary
is published; it does not copy that operational record into the Git primary.
The Go implementation follows those observed bytes. APG96 reconciles Accepted
ADR 0051 and the normative architecture accordingly: a later Git primary
removes the stale ops-only primary without copying its record. Operational
evidence created after a Git primary exists still appends inside that primary.

## Publication and recovery boundary

`Append` accepts an absolute clean outbox root, project, phase, and exactly one
canonical record. Directories are mode 0700 and files are mode 0600. Show and
Diff primaries supersede each other. Operational records append to an existing
Git primary or use an ops-only primary when no Git primary exists.

Private locking and transaction helpers retain recoverable interruption state
and never remove a live or foreign lock. Stale-lock recovery uses PID inspection,
assuming a local, single-host, owner-only outbox. If an interrupted execution
leaves a `.phase.transaction` file behind, `internal/atomicfile.Recover` provides
the underlying recovery mechanics. APG96 adds user-facing CLI path and recovery
adapters.

## Supported platforms

In accordance with Accepted ADR 0051, the embeddable Go surface targets POSIX
Unix environments (Linux and macOS) requiring direct regular files, owner modes,
and `O_NOFOLLOW` symlink refusal. Windows is not a supported target for the
embeddable Go reporting core.

## Related command and distribution surfaces

The [APGR CLI reference](cli.md) documents command adapters, path and recovery
operations, build information, and Python delegation. The
[distribution contract](../distribution.md) documents supported targets and
the locally qualified v0.7 Python/npm architecture. The v0.7 candidate is not
published; cross-consumer readiness and publication remain later phases.
