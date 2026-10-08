# Operational observations (v0.13 pilot)

APGR v0.13.0 is an early dispatcher and context-management pilot. Ordinary
dispatch attempts leave a small local observation so an operator can later ask
which context mode was requested and used, why static fallback happened, which
skills a plan would have selected, how many controlled bytes crossed the runner
boundary, and which stages, providers or builds failed. The observations inform
later promotion, remediation and improvement decisions. They are not a savings
claim, a benefit gate or a maturity score.

## What is recorded

One event is written beside each V1 or V2 provider attempt, including attempts
that fail to start, time out, are interrupted or are rejected before launch:

```text
<run directory>/<attempt prefix>.dispatch-observation.json
```

The V1 prefix is the stage artifact prefix (for example `03-work`); the V2 prefix
is the attempt ID. V2 already owns `<attempt>.observation.json` for review-drift
evidence; the dispatch event deliberately uses a different name.

Schema `apg.dispatch-observation/v1` has a stable `event_id`
(SHA-256 of schema, run ID and attempt prefix) and records:

- run, binding/stage, attempt ID and number, invocation kind, predecessor
  attempt (V2 reroutes and V1 review retries), and the worker parent ID only
  when a worker parent was actually registered;
- phase type and execution mode; project where the dispatcher knows it;
  task category is `null` (not classified);
- requested provider, profile and endpoint alias, plus requested model and
  effort where the V1 route record already carries them (`null` on V2);
  `provider_reported` is `null` because separately reported provider metadata is
  not available at this seam;
- APGR version and controller commit/tree when already known (no Git probe on
  the dispatch path; `source_dirty` is always `null`);
- outcome status (`runner_returned`, `not_started`, `start_failed`,
  `liveness_expired`, `cleanup_failed`, `interrupted`, `failed`), exit code,
  runner and dispatch error type names, and runner duration from a monotonic
  clock;
- a reference (file name, SHA-256, size) to the existing context-plan record
  with requested/effective mode, reason and whether planning ran;
- expected artifact names and `self_report: null`.

It never copies argv, prompts, source, settings, transcripts or environment
values, never reads provider credentials or session stores, and never records
absolute paths. Unknown values stay `null`; the report prints `unavailable`,
never zero.

The summary reuses the native records that every run already produces: V1
`state.json` routes and controller generation, `*.meta.json`, context plans,
context deliveries and failures, run-owned acquisition events and worker
`*.result.json` files. Runs made before this feature are still summarized from
those records, with a coverage warning.

## Opt-out and failure behavior

Collection is on by default for normal dispatch. Either of these disables it:

```sh
export APGR_DISPATCH_OBSERVATIONS=0      # also off, false, no, disabled
```

```toml
# <project>/.apgr/config.toml (preferred) or <APGR_HOME>/config.toml
[dispatcher.observations]
enabled = false
```

The table is closed: only a Boolean `enabled` is accepted, and an invalid value
is an ordinary configuration error reported before any provider starts, like
other `[dispatcher]` keys. Builds older than this feature reject the
`observations` key; when an older installed APGR shares the same APGR home, put
the opt-out in project configuration or use the environment variable.

Observations never permit or block a run. Disabled collection does not change
provider argv, prompts or permissions and starts no database, server or probe.
A missing or unwritable run directory, an oversized event or any other writer
error is reduced to its exception type name: V1 appends
`{"prefix", "diagnostic"}` to `observation_failures` in `state.json`; V2 prints
one `optional observation not recorded (<Type>)` notice on stderr. The provider
is not retried and the task result is unchanged. Interrupts propagate normally
and are recorded as `interrupted` when the event can still be written. The
observation is lost when storage is unavailable.

## Commands

All commands are provider-free: they never start a provider, context planner,
Go bridge or dispatcher, and never write into run directories.

```sh
# Selected run directories (V1 leaves, V2 canonical runs, or V2 projections)
apgr dispatcher observations summarize RUN_DIR [RUN_DIR ...]

# Bounded outbox selection: newest N run leaves (1..200) per project/phase
apgr dispatcher observations summarize --outbox-root OUTBOX --project PROJECT \
    [--phase PHASE] --latest 20 [--json]

# Include canonical V2 runs under <APGR_HOME>/state/runs
apgr --apgr-home HOME dispatcher observations summarize --v2 --latest 20

# Optional rebuildable SQLite index, then summarize from it
apgr dispatcher observations index [--rebuild] RUN_DIR ...
apgr dispatcher observations summarize --from-index [--run-id RUN_ID ...]

# List runs and their recorded state, newest first (no index required)
apgr dispatcher observations list --project PROJECT [--phase PHASE] [--latest N] [--json]
apgr dispatcher observations list --all-projects [--outbox-root OUTBOX] [--latest N]
apgr --apgr-home HOME dispatcher observations list --v2 [--project PROJECT] [--phase PHASE]

# Explain one run's context decisions (no index required)
apgr dispatcher observations explain RUN_DIR [--attempt PREFIX|ID] [--stage BINDING] [--json]
apgr dispatcher observations explain --project PROJECT [--outbox-root OUTBOX] [--phase PHASE] [--leaf LEAF]
apgr --apgr-home HOME dispatcher observations explain --v2 [--leaf RUN_ID]

# Explicitly attributed feedback
apgr dispatcher observations feedback --run-id RUN_ID [--attempt-id ID] \
    --label helpful|missing|misleading --source operator|agent|reviewer \
    [--skill apgr:SKILL] [--note "at most 512 characters"]
```

The same commands are available from a source checkout as
`bin/agent-phase-observations summarize|index|feedback|explain|list`. The `apgr` route, like
`apgr dispatcher bundle`, runs from an APGR source checkout (or with
`--project-root` naming it). That route changes the working directory to the
checkout, so pass absolute paths to subcommand options such as
`--outbox-root`; the global `apgr --outbox-root` is resolved first and is
forwarded to `list`, which rejects it (exit 2) without `--project` or
`--all-projects`.

Selection scans only the known run-leaf depth
(`<outbox>/<project>/<phase>/<phase>-dispatch--<timestamp>`) and never imports
historical outboxes recursively or at launch.

## Storage, retention and cleanup

- Per-attempt events live in their run directory and are archived with it. They
  follow that run's existing retention.
- Optional analytics live under `<APGR_HOME>/state/observations/`:
  `feedback.jsonl` (append-only, `0600`, advisory lock) and `index.sqlite3`
  (`0600`). This is never `dispatcher.sqlite3` and is never execution authority.
- The index keys one row per `(run_id, resolved run directory name)`. Repeated
  imports report `unchanged`; `--rebuild` writes a fresh file and replaces it
  atomically. A locked (2 s busy timeout), corrupt or incompatible index fails
  that command with exit status 1 and a bounded message; it never affects
  dispatch or the file-based summary.
- Deleting `<APGR_HOME>/state/observations/` removes only the rebuildable index
  and the feedback rows. It never deletes run evidence or execution state.
  Exporting is `summarize --json` over an explicit selection; it contains run
  IDs and counts, not paths or bodies. Do not publish raw run directories.

## Reading the report

The summary preserves raw counts and denominators and separates:

- requested versus effective context mode and each fallback reason (a comma
  joined planner reason is counted once per component);
- context delivery per attempt (`adaptive`, `static_with_shadow_plan`,
  `static_fallback`, `static`) and ordinary route support
  (`supported` or `unsupported:<code>`); older rows show `unavailable`;
- planner facts actually supplied (`work_class=...` plus configured, task and
  manifest facts on adaptive attempts);
- skills *planned* (prospective plan) versus skills *delivered* (delivery
  records). Only attempts whose effective mode is adaptive on the supported
  Claude route place selected skills on the runner transport;
- controlled initial bytes per measured boundary. The context plan's
  "canonical argv JSON plus runner stdin" total is preferred; stdin-only
  delivery records are used only when no plan total exists; the two are never
  added together. Late bytes come from acquisition delivery events;
- acquisition event kinds, misses by requested ID and repeat deliveries;
- attempt status and failures by stage, provider, build and status;
- worker jobs by kind and status, requested versus effective model with the
  worker's own evidence source, and quota observations;
- feedback by label and source. Feedback is attribution, not machine
  observation, and agent self-report is always labelled `agent`.

## Example (fixture runs)

Generated from three fixture runs with counting fake providers: one full V1
dispatch, one V1 stage with the experimental adaptive opt-in and a fixture
planner, and one V2 dispatch, plus one operator feedback row:

```text
APGR dispatch observations (raw counts only; no savings, benefit or maturity score is computed)
runs=3 attempts=11 attempts_with_event=11 dispatchers={'v1': 2, 'v2': 1}

Requested -> effective context mode
  static -> static: 10/11
  adaptive -> static: 1/11

Context reasons / fallback
  static_requested: 10/11
  independent_recovery_unqualified: 1/11
  selective_projection_unqualified: 1/11

Planner facts supplied
  work_class=review_verification: 1

Skills planned (prospective)
  apgr:planning-repository-work: 1

Skills delivered
  (none)

Controlled initial bytes (per measured boundary; views are never summed)
  [context-plan controlled_total: canonical argv JSON plus runner stdin] n=11, sum=94161, min=1965, median=6756, max=18815
  attempts without a byte record: 0
Controlled late bytes (acquisition deliveries): n=0, sum=unavailable, min=unavailable, median=unavailable, max=unavailable

Attempt status
  runner_returned: 11/11

Feedback (label/source; attributed, not machine-observed)
  missing (operator): 1

Coverage and missing-data warnings
  - build_commit unavailable for 11/11 attempts
```

(Sections with no rows, such as acquisition misses and worker jobs, are
omitted here for brevity; the command prints them as `(none)`.)

## Explaining one run

`explain` answers "what context did this run select, send and why" for one run,
from that run's own records. It works on live, partial, older (PILOT1) and
malformed runs with explicit "not recorded" fields and warnings, never needs
the index, and never starts a provider, planner, Go bridge or MCP server.

Selection: an explicit run directory; `--project NAME` (newest run leaf, using
`--outbox-root` or the resolved dispatcher outbox root, optionally `--phase`);
or `--v2` (newest canonical V2 run under `<APGR_HOME>/state/runs`). Filters:
`--attempt` (prefix or attempt ID) and `--stage` (binding). `--no-feedback`
skips the feedback file.

For each attempt it shows:

- provider/profile and the ordinary route classification (seam, supported or
  `unsupported:<code>`, binary preflight);
- requested versus effective mode, reason, diagnostic type and a delivery
  label. `STATIC_WITH_SHADOW_PLAN` is printed as "planned only; selected
  skills NOT delivered". Hints explain common fallbacks, for example setting
  `APGR_GO_BINARY` or why `required_skills_unsatisfied` occurred;
- inputs: each fact with source and status (`supplied`, `overridden`,
  `conflicting`, `unknown`), each explicit request with source and whether it
  applies to this posture, and manifest file statuses;
- skills: selected (reason, bytes), deferred, unavailable, unknown facts, how
  many were not selected for lack of a positive fact, how many are acquirable
  later, and prepared recovery copies;
- four separate byte views, each labelled with its boundary: *planned*
  (prospective mandatory and payload), *runner transport* (argv plus stdin the
  adapter prepared), *transmitted* (runner and launcher process records with
  coverage and bytes by channel) and acquisition records (including prelaunch
  recovery preparation, late controlled bytes, misses and rejections);
- instructions: whether static or projected APGR standing-instruction
  material was used (`projected`, `static`, `static_fallback`, `disabled`,
  `not_applicable`, `not_used_static_fallback` or `unknown`), the role
  classes and capability, selected fragments and each omitted fragment with
  why, the labelled `claude/CLAUDE.md` byte boundary with static, projected,
  delta and percentage (`delta_basis` is `transmitted_projection` or
  `prospective_projection`; for fallback and consumed-but-unapplied attempts
  it is `not_transmitted`, the delta is null and only the prepared projection
  bytes are shown), the source, manifest and projection digests, and the
  measurement: `observed_at_launcher_boundary` when the wrapper witnessed the
  body in native argv, otherwise `prospective_only:<why>` or `unknown`. The
  observed instructions-argument bytes and the wrapper's static counterfactual
  (computed, not transmitted) are shown when recorded. These are APGR-owned
  instruction bytes, not tokens or total provider context;
- provider-reported usage (`unavailable`), outcome with the reminder that
  `runner_returned` is process return rather than task success, attributed
  feedback, and the names and sizes of the attempt's sibling records.

Run-level output separates runtime state (a recorded terminal outcome, or "no
terminal outcome recorded: running, interrupted or crashed", never "healthy")
from telemetry completeness counts. Reads are bounded per file (the existing
limits) and in aggregate (64 MiB), with at most 256 attempts; exhausted budgets
are reported as warnings. Human text is rendered only from the same dict that
`--json` prints (`apg.dispatch-context-explanation/v1`).

## Listing runs

`list` answers "which runs do I have, and what happened?" without run paths.
It needs one scope: `--project NAME`, `--all-projects`, or `--v2` (canonical
V2 runs under `<APGR_HOME>/state/runs`; `--project`/`--phase` then filter by
the project and phase recorded in `result.json`, and runs without a readable
`result.json` are excluded and counted as `v2_unattributed_excluded`, or as
`v2_unread_excluded` when the read budget ran out first). `--outbox-root` defaults to
the resolved dispatcher outbox. `--latest N` (default 20, at most 200) applies
once across the whole selection, newest first; unlike `summarize`, it is not
per selector. An empty result prints `no runs found` and exits 0; usage errors
and unsafe project or phase names exit 2.

Discovery is name-only and bounded. It scans exactly
`<outbox>/<project>/<phase>/<phase>-dispatch--<timestamp>`, the historical
`<outbox>/<project>/<phase>--<timestamp>` layout and, with `--v2`,
`<APGR_HOME>/state/runs/<run-id>`; nothing else is crawled. Project and phase
directories must be real directories: symlinks, special files and unreadable
entries are counted under `discovery.skipped` and never entered. A symlinked
leaf is read only as a verified V2 projection: a regular sibling
`<leaf>.locator.json` naming the run, and a target that is a directory directly
under this APGR home's `state/runs`; `explain --leaf` then reads that target.
A symlinked `state/runs` itself is refused by both `list` (with a warning) and
`explain`. Any other symlinked leaf is listed by
identity only with `records: not_read` and a reason (for example
`symlink_target_outside_apgr_home_runs` or
`symlink_target_other_apgr_home_runs`). A verified projection and its canonical
run appear once, as the newest projection row. Bounds: 256 projects, 4,096 phase directories, 50,000 scanned
entries, 256 attempts per run, 128 MiB of record reads for the whole listing,
plus the existing per-file limits. Projection locators (64 KiB each), feedback
(100,000 rows of at most 16 KiB) and acquisition events keep their own bounds.
A reached discovery bound sets `truncated` and `order_complete: false`; the rows
are then not guaranteed to be the newest. Once the read budget is exhausted,
later rows keep their identity with `records: budget_exhausted`. Known limits:
the shared run reader lists every entry name of a selected run directory
before the attempt bound applies, so that per-run name listing is outside the
50,000-entry discovery bound; and the feedback reader stops, with a warning,
at the first line over 16 KiB rather than reading past it.

Rows are ordered by the timestamp in the leaf or V2 run name; a caller-supplied
V2 run id without one falls back to the directory modification time, labelled
`filesystem_mtime`. Each row reports identity (run id, project, phase, source,
dispatcher), phase type, execution mode, lifecycle, the recorded controller
generation, roster generation and APGR versions, start time from the name, the
latest attempt time from attempt records, the record file's modification time,
attempt counts by status and provider/profile, requested/effective context
modes with delivery, route-support and fallback-reason counts, worker
kind/status and quota counts, telemetry coverage (records read, attempts
without an observation event, observation failures, warnings, missing
records) and attributed feedback labels. No terminal timestamp is recorded by
the dispatcher, so none is shown.

Runtime state is `terminal_recorded`, `no_terminal_record` ("running,
interrupted or crashed; not a health claim") or `records_unavailable`. A V2 run
without `result.json` may have its terminal status only in
`dispatcher.sqlite3`, which `list` does not read. Telemetry coverage is
reported separately from runtime state, and nothing is labelled healthy.

Each row carries an `explain` command (`--project/--phase/--leaf`, or
`--v2 --leaf`) as guidance only; with an explicit `--outbox-root` or
`--apgr-home` it contains `<OUTBOX_ROOT>`/`<APGR_HOME>` placeholders so the JSON
stays path-free. `list` never runs it and never retries, resumes, cancels,
cleans, commits or writes anything; it does not read or require the optional
index. Human text is rendered only from the `--json` value
(`apg.dispatch-run-list/v1`).

Not implemented: live views, timelines, index-backed listing and dashboards; see the
[observability direction](../architecture/v0-13-observability-direction.md).

## Limits

- Observations cover every V1 `_stage` invocation (semantic, review retry,
  result repair, resume) and every V2 binding attempt. Dry runs and V2 turns
  without a runner start no attempt and write no event.
- Only runner-level duration is measured; token counts, provider-native
  overhead and model consumption are not observed.
- Delivery of a skill never implies the model read or used it.
- The report is local, file-based and optional; there is no daemon, dashboard,
  cloud collector, reviewer or promotion engine.
