# Evaluation: Agent-Central and APGR Dispatcher Differences

- **Status**: Filename-level and byte-level inventory; semantic content diff pending (V0130-I)
- **Phase**: APG159 (Milestone V0130-A)
- **Governing ADR**: [ADR 0069](../adr/2026/09/0069-v0-13-program-scope-and-dispatcher-reference-doctrine.md)
- **Inspection Basis**: Read-only comparison of `libexec/agent_phase/`, `common/dispatcher/`, and the `bin/agent-phase-*` wrappers between the two Agent-Central checkouts available on the execution host (the nix-darwin managed checkout and the secondary operator checkout) and this APGR clone at the APG159 candidate tree. Commands: `git log 56e9bb03..HEAD -- <paths>`, `diff -rqs -x __pycache__`, and `cmp -s`. Performed 2026-09-20.

---

## 1. Purpose

To evaluate the readiness of APGR as the forward reference single-phase dispatcher and prepare for the reversible owner-executed transition in Agent-Central, this report inventories the differences between the two codebases and states exactly what was and was not compared. It isolates dispatcher functionality from the external worker supervisor.

---

## 2. Inventory of Differences

### 2.1 Modules Present Exclusively in APGR (16 Modules)

The following 16 modules were authored or formalized during the v0.12 architecture transfer and exist only in APGR's `libexec/agent_phase/`:

1. `capabilities.py` — Provider capability inspection and model parameter catalog.
2. `config_routing.py` — Multi-tier configuration resolution and home path derivation.
3. `dynamic_router.py` — Bounded dynamic provider routing and eligibility evaluation.
4. `failure_classifier.py` — Provider error classification and quota exhaustion detection.
5. `outbox_projection.py` — Operator outbox directory projection and run receipt formatting.
6. `persistence.py` — Embedded SQLite persistence engine (`SCHEMA_VERSION = 2`).
7. `persistence_feedback.py` — SQLite feedback recording and operational observation management.
8. `probes.py` — Read-only availability and capability probes.
9. `resolution_v2.py` — Request V2 contract resolution and route binding.
10. `semantic_roles.py` — Decoupled semantic role graph and responsibility tracking.
11. `v2_dispatch.py` — Request V2 dispatch entrypoint and lifecycle driver.
12. `v2_prompts.py` — Prompt template generation for V2 semantic roles.
13. `v2_records.py` — Machine record schema validation for V2 turns.
14. `v2_repair.py` — Turn 5 result repair coordination.
15. `v2_reroute.py` — Dynamic failure rerouting state machine.
16. `v2_turns.py` — Multi-turn coordinator for V2 execution.

Agent-Central contains **zero** modules in `libexec/agent_phase/` that do not exist in APGR (at filename granularity, excluding `__pycache__`).

### 2.2 Shared Modules: Byte-Identical versus Differing

Of the 62 modules present in both trees, `diff -rqs` reports:

| Class | Count | Modules |
|---|---|---|
| Byte-identical | 44 | `__init__.py`, `adoption.py`, `adoption_cli.py`, `antigravity_evidence.py`, `antigravity_output_recovery.py`, `archive.py`, `archive_recovery.py`, `archive_snapshot.py`, `archive_verify.py`, `candidate.py`, `capacity.py`, `checkpoint.py`, `display.py`, `dry_run.py`, `envelope.py`, `failure_boundary.py`, `finalization.py`, `finalization_proof.py`, `finalization_recovery.py`, `gitstate.py`, `jsonc.py`, `lifecycle.py`, `metadata_noop.py`, `metadata_policy.py`, `outcomes.py`, `ownership_challenge.py`, `path_disposition.py`, `plan_material.py`, `prompt_policy.py`, `publication.py`, `publication_summary.py`, `result_artifacts.py`, `result_repair_authority.py`, `review_binding.py`, `review_recovery.py`, `roster.py`, `routing.py`, `run.py`, `runtime_exclusion.py`, `scanner.py`, `transport.py`, `worker_capability.py`, `worker_custody.py`, `worker_recovery.py` |
| Content differs | 18 | `cli.py`, `dispatch.py`, `entry_adoption.py`, `entry_adoption_cli.py`, `lifecycle_dispatch.py`, `native_git.py`, `native_git_cli.py`, `ownership_cli.py`, `provider.py`, `request.py`, `result.py`, `result_repair.py`, `resume.py`, `resume_dispatch.py`, `resume_validation.py`, `review_result.py`, `route_provenance.py`, `stage_delta.py` |

The 18 differing modules were **not** semantically diffed in APG159. The v0.12 records (ADR 0063, ADR 0064, ADR 0065) attribute APGR-side differences to SQLite persistence integration, Request V2 support, operational observation capture, and outbox projection; that attribution is inherited from those records, not re-derived here. A line-level content review of the 18 modules is assigned to V0130-I as part of the standalone-operation gate.

Related surfaces:
- `common/dispatcher/`: `routes.toml` byte-identical; `README.md` and `endpoints.toml` differ; `capabilities.toml` exists only in APGR.
- `bin/agent-phase-dispatch`, `bin/agent-phase-resolve`, `bin/agent-phase-finalize`: byte-identical wrappers in both trees.

### 2.3 Agent-Central Changes After the Parity Baseline

Both available Agent-Central checkouts are at commit `56e9bb0` (2026-09-14), which **is** the ADR 0063 parity baseline `56e9bb039536dfc8893e61a431681d6a32167b6f`. `git log 56e9bb03..HEAD` over `libexec/agent_phase`, `common/dispatcher`, and `bin/agent-phase-dispatch` returns no commits in either checkout, and neither has uncommitted changes under those paths.

Consequently:
- No post-baseline Agent-Central dispatcher behavior exists on this host to compare against APGR.
- This is a **host observation**, not proof that no newer Agent-Central dispatcher revision exists elsewhere. If the Agent-Central owner has a newer revision, the comparison must be repeated against it before any cutover recommendation. This is a reported source limitation and an assigned V0130-I follow-up.

---

## 3. Separation of Dispatcher from Worker Supervisor

A critical architectural distinction governs the boundary between APGR and Agent-Central:

| Component Category | Location | Ownership | Relationship to APGR |
|---|---|---|---|
| **Single-Phase Dispatcher** | `bin/agent-phase-dispatch`, `libexec/agent_phase/`, `common/dispatcher/` | APGR Forward Reference | Migrated to APGR. Agent-Central's copy enters a reversible, owner-executed transition. |
| **Interactive Worker Supervisor** | `bin/agent-worker`, `libexec/agent_workers/` | Agent-Central Permanent Owner | Stays in Agent-Central. APGR does NOT import, duplicate, or manage the supervisor. |
| **Worker Facade Environment** | `AGENT_CENTRAL_WORKER_*`, `AGENT_CENTRAL_PARENT_ID` | Shared Interface Contract | Stable compatibility contract. APGR preserves these variable names without alteration. |
| **Operator Settings & Hooks** | `claude/settings.json`, shell hooks | Operator / Workstation Config | Managed by operator; APGR treats as read-only configuration. |

---

## 4. Evaluation Conclusion

1. **Filename-level superset**: At filename granularity APGR contains every Agent-Central dispatcher module plus 16 APGR-only modules. 44 shared modules are byte-identical; 18 differ and await a content review.
2. **Runtime dependence not established either way by this document**: This inventory did not execute APGR without an Agent-Central checkout and did not trace imports. The gate `V0130_I_NO_AGENT_CENTRAL_DISPATCHER_DEPENDENCY` therefore remains **unverified** and is owned by V0130-I, which must combine a dependency-oriented static check with standalone behavioral tests per ADR 0069.
3. **No missing behavior found, within the stated limits**: Because both available Agent-Central checkouts sit at the parity baseline, no post-baseline behavior gap was observable. A newer Agent-Central revision, if one exists, is an explicit open comparison.
4. **Cutover posture**: The Agent-Central owner controls adoption, rollback, and eventual retirement. Nothing in this evaluation authorizes removing or replacing the Agent-Central dispatcher.
