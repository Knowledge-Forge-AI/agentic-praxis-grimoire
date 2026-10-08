# Context planning

## APG166A transport observations

The V1 and V2 invocation adapters share one process-boundary recorder. Preparation
still describes planned transport; successful `Popen` and a complete stdin write
supply separate observations. `context-deliveries.json` retains run/binding/attempt
identity, collision-resistant transmission IDs, initial/late phase, UTF-8 byte
count, SHA-256, source and boundary. Repeated transmissions have new IDs;
overlapping source/component views do not add bytes.

Codex's explicitly injected instruction arguments are measured as their actual
UTF-8 argument bytes. Claude's launcher records added instruction arguments and
MCP/settings handoffs at the native process start. Antigravity records its final
transformed prompt argument; the earlier wrapper stdin view is excluded from
totals while retaining instruction/selected-body views bound to the exact caller
prefix and a separate launcher-instruction suffix view. Claude inherited stdin is counted once by the parent. A launcher receipt
missing after a wrapper start leaves coverage incomplete. The observed Claude
exec path uses an inherited-stream child with signal forwarding only when an
explicit evaluation or adaptive observation scope is present. Ordinary static
launches keep the existing exec path. Argv, permissions and task bytes are
preserved. Operator settings are never written.

Configuration references record the exact handoff fact: the child receives a
path, and the observation binds the referenced controlled UTF-8 configuration's
digest and length. This counts the declared H configuration boundary, not a
witnessed provider read or model observation. File materialization alone emits
no delivery. Claude settings are classified as instructions with settings provenance,
not MCP configuration; live handoffs must match a frozen runtime-input manifest.
Native discovery outside instrumented boundaries, native provider
overhead, tokens and model consumption remain unavailable. A selected source
body represented inside a transmitted serialized prompt is a component view,
not a second transmission of its unescaped source bytes.

Ordinary static dispatch remains availability-first: absent or failed observation
artifacts invalidate evaluation evidence without requiring the evaluator, MCP,
SQLite or a network service. The pair runner refuses incomplete observations.

APG164 introduces `apg.context-plan/v1` and `apg.context-packing/v1` without
changing BundleRequest or Resolve. The implemented planner preserves the following packing expectations.

Explicit requests precede generated structured-fact owners. Within each tier,
caller-declared role affinity (0–10, maximum across actual roles) precedes lexical
qualified identity. Affinity never establishes applicability. Unknown facts and
unrequested sources remain unknown/deferred; descriptive substrings and composition
associations do not select bodies. Material fact owners are required. Directed
required closure is packed atomically after qualified override resolution.

Budgets apply to exact UTF-8 rendered payload bytes and Unicode code points,
including serialized skill/support envelopes. Absent limits are unbounded; zero
is exact zero. Mandatory components retain their original order and bytes.
Whole source, body-only, description and support measurements are separate views,
not additional transmissions. Tokens and provider-native overhead are unavailable.

Mandatory overflow, unsatisfied required owners, invalid optional planning,
unqualified selective projection or unreadable recovery choose static transport
before invocation. Static fallback does not assert an adaptive budget pass.
At APG164 no real provider binding was qualified for reduction (APG166Z-CONTEXT1 later adds the ordinary Claude seam described below; it is an operational opt-in, not an H qualification). Fixture projection
adapters prove controlled transport only. They do not qualify native discovery,
model consumption, tool use or savings. G now provides the bounded [acquisition candidate](skill-acquisition.md); live
qualification and benefit evaluation belong to H.

Plans are immutable per run/binding/attempt; delivery observations are separate
artifacts. A runner call is an invocation observation, never model-use proof.
Collection does not plan again or execute providers. No SQLite migration, shared
home mutation, permission expansion, provider replay or version bump is part of F.

## v0.13 pilot: experimental adaptive delivery on the ordinary Claude route

Static is the shipped default. Setting `mode = "adaptive"` in
`[dispatcher.context]` (project `.apgr/config.toml` or `<APGR_HOME>/config.toml`)
is an explicit, reversible **experimental** opt-in. Remove the key or set
`mode = "static"` to revert; nothing else needs undoing.

### What changed in APG166Z-CONTEXT1

Before this increment (APG166X PILOT1) the opt-in was shadow planning only:
callers passed `work_class` facts, no projection adapter existed, and every
attempt launched static transport with reasons `selective_projection_unqualified`
and `independent_recovery_unqualified`. Those records remain valid history.

Now, on the one supported seam, opting in **delivers** the selected optional
skills to the native Claude child:

- **Supported seam.** Provider `claude`, launched through the maintained
  `bin/claude-profile` wrapper with its ordinary argv
  `[claude-profile, PROFILE, (--read-only), -p]`, and a profile that does not
  use isolated settings. This covers all five stages of the V1 `claude_only`
  `implementation_testing` route (`opus-high-plan`, `opus-high-review`,
  `claude-only-implementation-primary`) and Claude bindings in V2, through one
  shared seam (`libexec/agent_phase/context_route.py`).
- **Delivery.** The runner stdin is the planner's payload: the unchanged
  mandatory prompt (task, role, worker envelope and prior material,
  byte-identical to the static prompt) followed by one `<apgr-skills>` block of
  selected skill bodies, and a short APGR notice. Wrapper standing
  instructions (`--append-system-prompt`), target `AGENTS.md`/`CLAUDE.md`,
  operator settings and user instructions are untouched and are neither packed
  nor truncated; they are measured separately as launcher additions.
- **Late acquisition.** Deferred embedded `apgr:` skills stay reachable through
  the existing APGR MCP server (`skill_search`, `skill_acquire`,
  `context_explain`), which the wrapper composes into the same `--mcp-config`
  as the worker facade. Budget-deferred requests are also prepared as exact
  run-owned recovery copies under `acquisitions/skills/`, granted by exact
  `Read(//file)` rules. `project:`/`user:` bodies are not retained by the plan,
  so they are not acquirable later; the plan never substitutes another skill.
- **Permissions.** Read-only stages keep their read-only tool set and gain only
  the three MCP tool names; like the existing headless worker-facade posture,
  the permission mode is `default` with an exact allowlist (no Bash, Write, Edit
  or `--add-dir`). Mutation-capable stages keep their existing permission mode
  and ambient MCP sources; only the run-owned `apgr` server and its grants are
  added. An operator-configured server also named `apgr` in an ambient source
  could shadow the run-owned server on a mutating stage; the recovery copies
  remain the fallback.

Other providers, isolated-settings Claude profiles, other launchers or argv
shapes keep static transport with reason `route_unsupported:<code>`
(`provider_not_in_pilot`, `launcher_not_claude_profile`, `argv_shape`,
`isolated_settings_profile`, `profile_unknown`). The planner still runs there,
so `apgr dispatcher observations explain` shows what adaptive would have
selected.

**Opting in currently adds bytes.** Provider-native discovery, standing
instructions and the mandatory prompt are unchanged, so the selected
`<apgr-skills>` block, the APGR notice and the MCP configuration are additive.
In repositories with several manifests, each matched fact makes its profile
skill required for the stage: without a context budget several bodies are
appended; with one, the attempt often falls back to static with
`required_skills_unsatisfied`. The pilot makes no context or token savings
claim.

`--context-fact`/`--context-skill` are consulted only when the effective
configuration is adaptive. Under static mode each attempt's context plan
records them as `task_inputs_ignored` (reason `static_mode`), and `explain`
shows that line; they never change static transport.

### Prerequisite: a persistent APGR binary

The MCP server outlives one bridge call, so the route needs a persistent
executable: `APGR_GO_BINARY` (for example a binary built with
`bin/apg-build-go-cli`) or the bundled binary of an installed package. A source
checkout without either records `acquisition_binary_unavailable` and launches
static. `APGR_GO_BINARY` is process-wide; set it in the environment of the
dispatch command itself.

### Structured inputs

Facts use a closed vocabulary (`language`, `runtime`, `test_framework`,
`repository_characteristic`, `capability`); `work_class` stays
dispatcher-owned. Precedence is per fact kind:
**task > project config > home config > repository manifest**. A higher source
that declares a kind replaces lower sources for that kind (`overridden`); a
declared empty list means "none". A manifest value missing from the winning
declaration is `conflicting` and is not sent to the planner. Unreadable,
oversized, symlinked or unparseable manifests are `unknown` with a reason.

Manifest facts (enabled by default when adaptive; `manifest_facts = false`
disables them) read only top-level regular files of the stage working tree.
Nothing is executed; only `pyproject.toml` is parsed (bounded, `tomllib`).

| File | Facts |
|---|---|
| `go.mod` | `language=go`, `test_framework=go-native` |
| `pyproject.toml` | `language=python`; `test_framework=pytest` with `[tool.pytest.ini_options]` |
| `pytest.ini` | `test_framework=pytest` |
| `setup.py`, `setup.cfg`, `requirements.txt` | `language=python` |
| `package.json` | `runtime=nodejs`, `language=javascript` |
| `tsconfig.json` | `language=typescript` |
| `Gemfile` | `language=ruby` |
| `flake.nix`, `default.nix` | `language=nix` |
| `Dockerfile` | `repository_characteristic=dockerfile` |
| `Vagrantfile` | `repository_characteristic=vagrantfile` |
| `Cargo.toml` | `language=rust` (reported as an unknown fact; no owning skill) |

Explicit skill requests come from `skills` (the nearest declaring config list
replaces lower lists) plus task requests, which are unioned and win attributes.
A request may set `required` and `stages` (a subset of `plan`, `review`,
`work`); requests for another posture are recorded `not_applicable`. V1 maps
`plan` to plan, `plan_review`/`final_review` to review and `work`/`closeout` to
work; V2 maps planner, reviewer and producer/closeout/reviser roles likewise.

Task inputs are dispatch flags for fresh dispatches only:

```zsh
bin/agent-phase-dispatch request.json \
  --context-fact language=python --context-skill apgr:pytest-test-profile
```

They are recorded in each attempt's context plan (`inputs`, schema
`apg.context-inputs/v1`) and are rejected with `--resume`; a resumed run uses
configuration only. Request JSON is unchanged.

A matched fact makes its owning skill **required**, and a required skill that
does not fit the budget makes the whole attempt static
(`required_skills_unsatisfied`). Multi-manifest repositories (for example
`go.mod` plus `pyproject.toml`) can make four or more skills required; under a
tight budget, raise it, declare narrower facts, or set `manifest_facts = false`.

### Fallback before launch; no replay after

Every failure before the provider starts keeps argv and stdin byte-identical to
static and records a reason: planner reasons (`mandatory_overflow`,
`required_skills_unsatisfied`, ...), `optional_plan_failed`,
`acquisition_binary_unavailable`, `acquisition_prelaunch_failed`,
`recovery_path_unrepresentable`, `acquisition_config_failed`,
`transport_overhead_overflow`, `route_unsupported:*` or
`plan_persistence_failed`. An invalid context configuration remains an ordinary
configuration error.

After the provider starts there is one runner call. Existing retry, cancel,
liveness, cleanup and worker-drain paths are unchanged; MCP failures are left
to the agent's recovery reads; observation failures never change the outcome.
If the wrapper refuses a tampered handoff it exits 2 before `claude` runs; that
is an ordinary launch error and is not retried.

The `<prefix>.prompt.md` file keeps the static rendered prompt; in adaptive
attempts the delivered stdin is the planned payload in the context-plan record.

### Stage projection of APGR standing instructions (APG166ZB-CONTEXT-PROJECTION1)

On the same ordinary Claude route, an attempt whose skill plan is effectively
adaptive also receives a deterministic stage projection of the APGR-owned
standing instructions (`claude/CLAUDE.md`) instead of the whole file. Static
mode never reads the projection inputs and its wrapper argument is unchanged.

- **Source and classification.** `claude/CLAUDE.md` stays the authoritative
  static source, byte for byte. `claude/instruction-fragments-v1.json` holds
  classification only: fragments named by `## ` section and an optional exact
  anchor line, each either `invariant` (always kept: role and stop
  boundaries, permissions, host configuration, Liquibase authority, settings
  and SSH authority, dispatcher profile ownership, Git/hook policy, scratch,
  worker delegation and worker runtime authority) or declared for role
  classes (`planning`, `review_verification`, `implementation`, `closeout`)
  with an optional `ambient_tools` requirement. The manifest pins the source
  digest; editing `CLAUDE.md` without re-reviewing the manifest fails its
  tiling test and, at runtime, falls back with `instruction_source_changed`.
  The closed schema has no tool, permission, MCP, worker or path field.
- **Selection.** V1 maps `plan` to planning, reviewer roles and review stages
  to review/verification, `closeout` to closeout and everything else to
  implementation; V2 uses the union of its role flags. `ambient_tools` is
  false for effective read-only launches, which have no shell, no ambient
  MCP and no native skills, so shell- and MCP-only guidance (Codex reviewer
  invocation, `claude-profile` operations, server-memory, RepoMap and
  curated-environment guidance) is omitted there. The adversarial-review
  paragraph goes to every class because its single-example abstraction rule
  also binds implementers, so writable implementation and closeout launches
  currently receive every fragment and save no bytes.
- **Run-owned projection.** The dispatcher writes
  `<prefix>.instruction-projection.md` and its handoff
  `<prefix>.instruction-projection.json` (exclusive, mode 0600) into the run
  directory, records `instruction_projection`
  (`apg.claude-instruction-projection/v1`) in the context plan and passes the
  wrapper-private `--apgr-instruction-projection`. The wrapper refuses with
  exit 2 before Claude starts unless scope, plan, handoff, projected body,
  live source, live manifest and its own read-only capability agree and a
  recomputation yields identical bytes; it claims the handoff once. It then
  replaces only the standing-instruction body inside the existing
  `--append-system-prompt` value; the header names the classes and the
  omitted fragment IDs. The worker facade prompt, RTK slice and worker-skill
  notice are unchanged, as are tools, permissions, MCP and directories. An
  edit to `CLAUDE.md` or the manifest in the launcher checkout between
  preparation and launch therefore fails that stage without replay.
- **Fallbacks before launch** keep the static instruction path and do not
  change the skill plan: `instruction_manifest_unavailable`,
  `instruction_manifest_invalid`, `instruction_source_unavailable`,
  `instruction_source_changed`, `instruction_selection_unavailable`,
  `instruction_projection_write_failed`, and `transport_overhead_overflow`
  when the projection option alone exceeds the budget. A later whole-attempt
  static fallback marks the projection `not_used_static_fallback`.
  `instructions = "static"` records `disabled`. Attempts without an
  effectively adaptive ordinary route record `not_applicable`.
- **Not applied.** A writable launch without a worker facade or
  `APGR_MANAGED_PARENT=1` receives no standing instructions at all, and safe
  mode suppresses them; the wrapper still validates and claims the handoff but
  records `applied: false` with `source_guidance_inactive` or `safe_mode` in
  the launcher deliveries.
- **Default.** `instructions` defaults to `projected`, so operators already
  on `mode = "adaptive"` receive projected instructions after upgrading; set
  `instructions = "static"` to keep the whole file or to compare.

The comparison boundary is the `claude/CLAUDE.md` body only. A reduction there
is not a token measurement and not a reduction of total provider context;
provider-native prompt construction and user/global instructions are outside
it.

## Configuration and callers

```toml
[dispatcher.context]
mode = "static"            # "adaptive" is the experimental opt-in
# Optional exact UTF-8 bytes and Unicode code points (not grapheme clusters):
# max_initial_context_bytes = 40000
# max_initial_context_characters = 40000
# Adaptive inputs (APG166Z-CONTEXT1):
# instructions = "projected"   # or "static"; consulted only when adaptive
# manifest_facts = true
# skills = ["apgr:pytest-test-profile",
#           {id = "project:house-style", required = true, stages = ["work"]}]
# [dispatcher.context.facts]
# language = ["python"]
# test_framework = ["pytest"]
```

The closed table accepts only these keys; both configuration owners apply the
same rules. Negative, Boolean, string and
unknown limits are rejected. Project values override selected-home values per
key; explicit target and home win over discovery and ambient environment. Each
file is captured once for this planning boundary, and the same bytes supply TOML
and digest provenance. Discovery uses the routing owner's nearest `.apgr` directory, including across
nested Git boundaries. Context configuration is captured afresh per executable
attempt, separately from routing/RTK run capture. A mid-run edit can therefore
change later context settings or fail later validation; the per-attempt digest
records that boundary. Operators needing fixed settings must keep configuration
unchanged during the run. V1/V2 request JSON
receives no optimizer controls.

`skills plan --stdin` accepts ContextPlanRequest JSON. The native command may
also capture explicit `--project-root` and `--apgr-home` roots once; it never
parses TOML, reads environment roots or discovers a project. Python runtime
adapters pass captured project overrides and the selected roots. Bare request
IDs are not accepted by this new planner; callers use qualified IDs. Existing
Resolve and ResolveCatalog meanings remain unchanged.

The runtime maps actual review/planning roles and the structured phase type to
existing work-class facts. It never guesses from task prose. Since
APG166Z-CONTEXT1 the V1/V2 callers also supply configured, task and manifest
facts and explicit requests (see above); no affinities are supplied. Antigravity uses the `go_library`
consumer contract; that mapping establishes no provider capability. Unknown facts are retained as unknown. The external consumer fixture
shows material Go language plus native-test ownership and a merged role binding.

The adapter reserves canonical UTF-8 argv JSON overhead before packing stdin,
then reconciles the final argv and stdin again. The budget boundary is these two
disjoint controlled portions. Provider-native schemas, ambient discovery and
launcher-added context outside that runner boundary remain unmeasured. Instruction
component views carry source/rendered hashes and RTK slice costs without counting
those overlapping views again. Claude's downstream profile launcher remains the
owner of its standing additions and tool policy; F's runner record does not claim
to observe those downstream bytes.

## Artifacts and recovery boundaries

V1 uses the native stage prefix (`NN-stage.context-plan.json`); V2 uses its existing
attempt identity as prefix. A new attempt receives a new artifact. Exclusive
creation preserves retained bytes on collisions. Static records retain exact byte counts and SHA-256 of runner stdin, without
duplicating its text. Non-UTF-8 static bytes remain intact and their character
count is unavailable. Adaptive records may include captured prospective payloads,
selected snapshots, configuration provenance and portable catalog/rule/content
identities; unrelated catalog source bodies and unselected local prose are not
retained. Selected-file provenance is retained; decision qualified IDs and
root-level capture status describe the inspected inventory, including deferred
entries. These private run records are not disclosure-safe public reports.
Each artifact is bounded to 16 MiB. Archive's existing whole-run traversal,
file digest and total-size limits include these ordinary sibling files.

`context-transport.json` is written separately after the runner observation.
A known failed start records no delivery; an exception with possible partial
execution records unknown delivery. A normal runner return still does not prove
provider consumption. No model-observed state is synthesized. Optional V2 artifact
index failure leaves the canonical plan intact and writes a bounded diagnostic.
Plan-write failure returns ordinary static input and claims no unwritten reference.
Auxiliary result formatters do not plan again or inherit producer delivery.

The installed Python CLI forwards the pure JSON contract. Native generation
includes the shared adapter/config modules and its explicit maintained Go bridge;
if the optional binary/resources are absent it falls back to static. Imports bind
to the controller's own source rather than an ambient package or sys.path addition.

## Fixture and qualification limits

`testing/fixtures/context-eval/f-context1-accounting.json` is the sealed historical
F correction owner and remains unchanged. Current-source regression accounting
lives in `src/test/fixtures/context-current/f-context1-accounting.json`, generated
by `testing/fixtures/context-eval/measure_f.py` using an explicitly built CLI.
The regression test compares exact current output and independently preserves
all frozen fields except the four source-dependent standing/cost/identity fields.
Historical estimates remain labelled in their original scenario documents and
are not operative F costs. The correction measures exact current standing and
skill sources with a fixed synthetic task/role envelope; it is not an estimate
of live provider input. Original cohorts, IDs, thresholds and E collision cases
remain unchanged. No median/p95 benefit, token savings, live recovery or skill
promotion follows from these fixtures.

Adaptive opt-in in a source checkout may build the Go CLI per attempt through
the existing bridge. Missing build support selects static. Default static never
calls that bridge. F native CLI fixture cases explicitly skip when their required
prebuilt qualification binary is absent; qualification runs must build it first
and report skips separately. The G acquisition suite builds a session-scoped
offline binary by default; an explicit APG_ACQUISITION_BINARY may replace it,
and missing or failed build prerequisites fail visibly rather than skip.

## H evaluation boundary

APG166 preserves the packing rule and all canonical skill bodies. Its sealed
harness records prospective planner costs separately from controlled deliveries.
A file present on disk or a generated plan is not an initial transmission.
Both arms need complete measured prompt/instruction, delivered configuration/tool
schema, channel response and witnessed recovery traces before a cumulative gate
can pass. Provider-native overhead and tokens stay unavailable without direct
measurement. The [H result](../evaluations/apg166-maturity-and-integrated-evaluation.md)
has no qualified live pairs and recommends retaining static in I.
