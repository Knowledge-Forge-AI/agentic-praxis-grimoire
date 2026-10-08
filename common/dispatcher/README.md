# Dispatcher roster

This directory is the tracked, repository-owned roster surface for the local
phase-dispatcher prototype. `endpoints.toml` assigns stable aliases to exactly
one provider and one provider profile. `routes.toml` assigns every supported
`(phase_type, execution_mode)` pair to the five standard routing slots: `plan`,
`plan_review`, `work`, `final_review`, and `closeout`.

Lifecycle topology is not duplicated here. The lifecycle registry projects
lightweight semantic stages onto the standard slots. The captured `models.toml` is authoritative for model and reasoning effort.
Provider profile sources retain permission and tool posture. Executables, paths,
environment, credentials, permissions, approval modes, sandbox settings, and
hooks are forbidden roster concerns; security-sensitive configuration remains
owned by `agent-security-nd`.

The loader uses Python `tomllib`, fixed repository-relative paths, exact schemas,
closed fields, complete phase/mode coverage, exact slot sets, referential
integrity, and provider-profile readback. There is no hard-coded routing fallback.
Resolution records the selected aliases and SHA-256 provenance of both files.
The `claude_only`, `codex_only`, and `gemini_only` modes are additionally
validated to use only Claude, Codex, and Antigravity endpoints respectively.

APGR owns this portable single-phase execution runtime. JACA owns permanent
cross-phase orchestration, capacity-aware selection, and multi-phase authority.

## Operator roster workflow

<!-- BEGIN MANAGED DISPATCHER ROSTER OPERATIONS -->
Edit `endpoints.toml` when adding or renaming a stable endpoint alias. Each
alias contains only `provider` and `profile`. Edit `routes.toml` when changing a
stage roster; every supported phase/mode table must contain exactly the five
standard slots. The bundle owns model and effort; provider profiles own launch posture;
endpoints alias provider plus profile; routes alias phase, mode, and stage.
Do not copy model or reasoning-effort values into either roster file.

All six bundle members carry one positive `generation`. Advance them as one
operator edit; a mismatch is unusable roster state and dispatch fails closed.
Select `execution_mode` from the explicit current operator instruction for each
run. These directions define no active default and do not change routing policy.

APGR owns the portable single-phase runtime and its provider/profile catalogs.
Agent-Central owns workstation composition; its checkout and link-installation
procedures are not APGR runtime prerequisites. See
[ADR 0058](../../docs/adr/2026/09/0058-apgr-jaca-product-boundary-and-runtime-ownership.md)
for the APGR/JACA ownership boundary. Permanent cross-phase orchestration,
capacity selection, and fail-closed brokerage remain JACA concerns.

Keep security-sensitive controls outside the roster. Never add executables,
arbitrary paths, environment variables, permissions, approval or sandbox
settings, hooks, credentials, or other launch/security controls to these files.
Agent-Security retains its security-control ownership when integrated, but
Agent-Security and JACA are not mandatory dependencies of the availability-first
local prototype. Their absence, staleness, or failure does not block local
prototype launch; optional hardening may observe, warn, or enhance.

Before dispatch, run from the APGR repository root using its qualified Python:

```bash
python3 tools/add_dispatcher_roster_operator_directions.py --check
python3 -m pytest -q src/test/dispatcher/test_agent_phase_roster.py src/test/dispatcher/test_agent_phase_routing.py
bin/agent-phase-resolve path/to/request.json
bin/agent-phase-dispatch --help
```

The first command validates the canonical bundle and checks these
managed directions. The tests cover completeness, referential integrity,
provider-profile validation, and behavioral routing. Resolution is provider-free
and exposes selected aliases, captured-bundle intelligence, the shared
generation, repository-relative source paths, and SHA-256 source digests.
Inspect that evidence before using a changed roster. A passing local check does
not authorize dispatch, publication, or workstation installation.

For explicit result repair, use the APGR runtime binary with the working
directory set to the source phase's target repository. Retain the source run as
immutable evidence. An operator commit message supplies explicit finalization
authority; `--result-repair-commit-subject` is restricted to explicit
`--from-stage result-repair` with commit-local or publish finalization. It is
unavailable to ordinary dispatch, automatic repair, other resume modes, and
checkpoint finalization. Inspect the runtime's `--help` for supported options;
do not rewrite retained evidence or infer permission to finalize from a repair.

Phase resume routes unperformed suffix stages from the current validated roster
snapshot while preserving historical execution evidence for completed prefix
stages in an immutable per-stage ledger. Historical V4 and V5 source runs are
adapted upon resume. Finalization-only operations require no fabricated current
provider route and do not load the current roster.

Producer requests remain strict JSON. Nonce-fenced provider review and terminal
result objects accept a JSONC-compatible subset: strict JSON plus `//` comments,
`/* ... */` comments, and trailing commas. Duplicate keys, prose, YAML, a second
object, malformed comments, unknown fields, and identity/domain violations remain
rejected. This is not a general JSON5 contract.
<!-- END MANAGED DISPATCHER ROSTER OPERATIONS -->

## Checkpoint and resume boundaries

Planning produces one dispatcher-owned `plan-material.md` per run. Its closed
`agent-phase-plan-material-v1` binding records `schema`, `relative_path`,
`bytes`, `sha256`, `materialization_kind`, `provider`, and `profile`; raw
provider stdout is retained separately. Inline stdout is preferred. The only
file-material adapter is the Antigravity-native fixed brain shape under the
effective account, `~/.gemini/antigravity-cli/brain/<safe-session>/<safe-name>.md`.
It accepts exactly one safe Markdown artifact and performs bounded no-follow,
owner/mode/link/type/identity/UTF-8 checks. It is not an arbitrary file
importer. Private absolute paths and URIs are never forwarded to reviewers or
stored in run state. Review, work, archive, and resume use the exact embedded
canonical bytes; historical runs use only their already-bound raw stdout.

Planning and review stages are mechanically read-only. Their envelopes forbid
test runners, builds, compilers, generators, reconcilers, installers,
formatters/fixers, external reviewers, and uncertain-side-effect commands.
The dispatcher independently checks the worktree and real index before and
after each such stage. Providers never stage, commit, or publish.

Antigravity is an availability-first personal-laptop prototype. Every
non-dry-run request starts `agy` directly as the launcher's supervised child
and process group; holder absence, failure, or nondeployment never blocks it.
The bounded version probe is advisory and begins only after the requested
provider has started. New evidence is honest direct-launch V3 evidence.
Immutable V4/V5 lease-era evidence remains readable but neither authorizes nor
requires a new lease.

Resume is concurrency-safe but remains evidence-bound. It validates request,
repository identity, applicable branch/index conditions, immutable artifacts,
stage/checkpoint/result evidence, V5 roster provenance (or narrow V4 route
compatibility), and the candidate-specific manifest. Unrelated commits and
worktree changes may coexist when they do not overlap inherited candidate
paths. Current HEAD, entry/published trees, and the whole worktree no longer
serve as equality gates for continuing a semantic phase. Conflicts, active
operations, staged work at an incompatible boundary, route/stage/checkpoint
drift, or artifact tampering still fail closed. Final commit and publication
checks remain dispatcher-owned; publication remains normal Git fast-forward
only.

Review-result and terminal-result objects accept only the bounded JSONC subset:
strict JSON with `//` line comments, `/* ... */` block comments, and trailing
commas. Producer requests remain strict JSON. Duplicate keys, malformed
comments, extra objects/prose, unknown fields, invalid UTF-8, and domain or
nonce violations remain rejected. `--dangerously-skip-permissions` is
unconditional for every headless AGY launch; planning and review add
`--mode plan`. Tool auto-approval is not mutation authority.

Use the provider-free qualification commands in the operator workflow above.
The [v0.12 ownership transition](../../docs/architecture/v0-12-agent-central-ownership-transition.md)
records the runtime migration boundary. Do not encode transient provider
capacity in this roster; permanent orchestration,
capacity selection, and future lifecycle authority belong to JACA.
Agent-Security is a possible optional integrated authority for a future
high-assurance or multi-tenant deployment, not a prerequisite for this
proportionate single-user boundary.

## APG166S worker and home authority

`models.toml` and `workers.toml` complete the dispatcher bundle. The APGR-home
capture is runtime authority; `common/dispatcher` supplies source defaults.
`apgr dispatcher bundle project` and `verify` implement the standalone staging
contract described in [the bundle specification](../../docs/specs/apgr-dispatcher-bundle-v1.md).
No live operator bundle is migrated automatically.

The standard `gemini_sub` roster uses Opus 5.5/high for planning and both reviews,
and GPT-6.1 Sol/xhigh for work and closeout. Each stage requires the independent
4+4+4 worker pools. APGR owns the workers and resolves their entrypoints within
its candidate root. Dynamic routes qualify runtime workers before launch.
Configuration alone is not observed worker-canary evidence.

### v0.13 execution-mode compatibility and specialist exceptions

`gemini_fable` is a deprecated v0.13 compatibility alias to `gemini_opus`.
Both remain separately accepted execution-mode inputs for every supported
phase type. Their effective stage launch contracts are equivalent: Gemini
3.8-Flash High handles plan, work and closeout; Claude Opus 5.5/high handles
both reviews. Neither mode selects a Fable parent. Redesign, renaming or
removal belongs to a future-version decision; v0.13 retains both names.

Effective equivalence includes provider, model, effort, minimum CLI version,
profile permission/scope/isolated settings, process posture, stage launch
transport and worker capability/transports. It does not mean profile-identity
equality. These are the only retained `plan_review` identity differences:

| Phase type | `gemini_opus` alias / profile | `gemini_fable` alias / profile |
| --- | --- | --- |
| `implementation_testing` | `claude-normal-final-review` / `normal-final-review` | `claude-normal-plan-review` / `normal-plan-review` |
| `architecture_docs` | `claude-normal-final-review` / `normal-final-review` | `claude-normal-plan-review` / `normal-plan-review` |
| `sysadmin` | `claude-sysadmin-opus-review` / `sysadmin-opus-review` | `claude-normal-sysadmin-plan-review` / `normal-sysadmin-plan-review` |

For each row, the `gemini_opus` inventory `role` and profile `model_role` are
`primary`; the `gemini_fable` values are `review`. These compatibility metadata
differences preserve the same launch behavior and are pinned by the tests.

General Claude primary/review parent routes use Opus 5.5. Exactly two static
specialist closeout routes intentionally select the
`fable-architecture-docs-primary` alias/profile instead:

- `architecture_docs.normal.closeout`
- `architecture_docs.gemini_flash_sub.closeout`

They resolve to `claude-fable-5-1` at high effort and require Claude Code
`2.1.250` or later, just as explicit use of that profile does. Its stable name
and `review` role metadata are retained for compatibility; the route selects
specialist closeout work, not a general primary/review default.

Request V2's `dynamic` mode selects no Fable default when all endpoints are
eligible and no operational observations are active. It can automatically
select the Fable architecture-docs specialist for producer turns when
observations rank it highest, through score adjustments or exclusions. This
dynamic selection is separate from the two static closeout exceptions.

The maintained-resolver contract tests in
[`test_apg167d_fable_route_contract.py`](../../src/test/dispatcher/test_apg167d_fable_route_contract.py)
cover both accepted mode names, all phase types and lifecycles, those exact
metadata differences, the two static exceptions, general Claude Opus defaults,
and dynamic score-only and exclusion cases. Any additional identity/launch
divergence between the aliases or any third static Fable route fails that
contract. These documentation and test contracts preserve effective routing.
