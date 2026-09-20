# v0.13 observability direction

Status: product direction adopted into normal planning by APG166Z-CONTEXT1.
It records the maintainer's direction after APG166X PILOT1. It does not claim
that unimplemented interfaces exist.

## Purpose and priority

Operational telemetry is the foundation of a user-facing APGR observability
layer, not only development or benchmark instrumentation. It should help a
user understand what APGR did, what it is doing when current state is
available, why a route or context decision was made, and where a failure or
intervention occurred. The same observations later guide dispatcher and
context improvements and occasional skill promotion or remediation.

Dispatcher reliability and context management remain the priorities.
Observability makes them easier to operate; it is not a separate certification
project. v0.13 is a pilot: promotion quotas, complete benchmark coverage,
perfect attribution and a complete observability platform are not release
prerequisites.

## Scope: CLI first

Prefer a small, coherent CLI over a new service, and extend the existing
normalized reader and `apgr dispatcher observations` command family rather
than adding a second event store. One normalized query result serves both
human output and JSON, so a later TUI, web view or external consumer never
parses display text.

| Capability | Status |
|---|---|
| Per-attempt observation events on V1/V2 | Implemented (APG166X) |
| `summarize` over run directories or the optional index | Implemented (APG166X); delivery and route-support counts added (APG166Z-CONTEXT1) |
| Optional rebuildable SQLite `index` | Implemented (APG166X) |
| Attributed `feedback` (JSONL, survives index rebuild) | Implemented (APG166X) |
| `explain` for one run's context decisions (explicit run, `--project` newest, `--v2` newest) | Implemented (APG166Z-CONTEXT1) |
| Run listing / discovery across projects (`list`, file-based, bounded; `explain --leaf` handoff) | Implemented (APG166ZA-OBSERVABILITY-RUNS1) |
| Index-backed listing | Future |
| Live views, timelines | Future |
| Dashboard, alerting, OpenTelemetry export, stable external API | Future; not promised |

## Data semantics to preserve

- Keep run, binding, attempt, worker-parent and predecessor identities
  distinct; include the executing build and selected configuration identity
  when already available.
- Separate process/transport outcome, dispatcher semantic outcome, test result,
  reviewer finding and user feedback. `runner_returned` is not task success.
- Distinguish requested model, profile and effort from provider-reported
  observations. Missing vendor metadata is not a failed agent.
- Distinguish prospective (planned) context bytes, observed transmissions and
  provider-reported usage. Never convert controlled byte totals into token or
  cost claims.
- Missing fields and partial coverage are normal, visible states with useful
  denominators. Runtime status is distinct from telemetry completeness; no
  status implies a running process is healthy because it has not failed.
- Support older records with explicit missing fields and warnings; version
  machine-facing records and prefer additive evolution. An incompatible
  optional index is rebuilt without changing execution records.

## Operational boundary

Collection is local and optional. Collector, reader, index or UI failure must
not block normal dispatch, change its outcome, skip worker cleanup, replay a
provider, or make a broker or security service a runtime dependency. Essential
execution state and task permission checks are never weakened for analytics.

Default collection is metadata and references, not duplicate prompts, source
trees, transcripts, settings or credentials. Raw diagnostics stay under the
existing local artifact controls; export is a separate explicit operation. Do
not scan HOME or provider session stores to complete fields; if storage is
unavailable, disclose the gap.

The layer observes. Existing dispatcher commands remain the owners of retry,
cancel, resume, commit and other mutations; a future UI must make those actions
explicit rather than infer them from a displayed warning.

## What would make this direction wrong

- If operators routinely need live state for in-flight runs, a post-run reader
  is insufficient and a bounded live view moves up.
- If the per-run explanation cannot answer "why was this skill (not) sent"
  without reading raw plan files, the normalized record is missing fields.
- If collection measurably slows or destabilizes ordinary dispatch, the
  optional-collection boundary is not being honored.

## Sequencing

PILOT1 is integrated. APG166Z-CONTEXT1 pairs the first real ordinary context
delivery (the Claude route) with the `explain` view. Next: exercise the normal
supported dispatcher with a built binary and use its explanations.
APG166ZA-OBSERVABILITY-RUNS1 adds file-based run discovery (`list`). Cross-run comparisons, provider usage metadata, exports
or a richer UI follow when actual usage makes the need clear.

Related: [operational observations](../guides/operational-observations.md),
[context planning](../guides/context-planning.md),
[v0.13 roadmap](../v0-13-roadmap.md).
