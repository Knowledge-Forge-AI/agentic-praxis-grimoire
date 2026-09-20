# Provider Conformance Matrix

- Schema: `apgr-provider-conformance-matrix-v1`
- Generated: 2026-09-16
- Target Architecture: Single-Phase Dispatcher V2 / Dynamic Role Routing

## Overview

This document defines the truthful operational conformance matrix across all three supported execution providers in APGR: **Codex**, **Claude**, and **Antigravity**.

Per ADR 0064 and ADR 0065, APGR rejects aspirational claims and records vendor capabilities truthfully. Features that cannot be proven or queried without burning model tokens or reading private secrets are marked as unobservable (`unknown`) and handled fail-open during dynamic routing admission.

## Conformance Evaluation (22 Capability Rows)

| # | Capability ID | Capability Name | Codex | Claude | Antigravity | Operational Notes |
|---|---------------|-----------------|:-----:|:------:|:-----------:|-------------------|
| 1 | `executable_version_provenance` | Executable & Version Provenance | Yes | Yes | Yes | PATH binary resolution and version string query without interactive TTY. |
| 2 | `profile_resolution` | Profile Resolution & Pinning | Yes | Yes | Yes | Deterministic argument binding from profile definitions in TOML catalog. |
| 3 | `requested_model_readback` | Requested Model Readback | Yes | Yes | Yes | Verified model configuration matching provider profiles and endpoints. |
| 4 | `reasoning_effort_readback` | Reasoning / Effort Readback | Yes | Yes | Yes | Configured reasoning effort and thinking budgets where supported. |
| 5 | `planner_role_qualification` | Planner Eligibility | Yes | Yes | Yes | Qualified via primary provider endpoints for implementation planning. |
| 6 | `reviewer_role_qualification` | Reviewer Role Qualification | Yes | Yes | Yes | `-s read-only` (Codex), `--read-only` (Claude), `--reviewer` (Antigravity). |
| 7 | `producer_role_qualification` | Producer Eligibility | Yes | Yes | Yes | Qualified with mutation capability and workspace execution. |
| 8 | `reviser_role_qualification` | Reviser Eligibility | Yes | Yes | Yes | Qualified for post-review candidate amendments and tree mutations. |
| 9 | `closeout_role_qualification` | Closeout Eligibility | Yes | Yes | Yes | Qualified for terminal qualification receipts and finalization. |
| 10 | `adapter_structured_output` | Adapter Structured Output CLI Flag | No | No | No | Upstream adapter CLI lacks direct schema flag; APGR uses nonce-fenced decoding. |
| 11 | `process_group_cleanup` | Process Group Supervision & Cleanup | Yes | Yes | Yes | Process group signal delivery (SIGTERM/SIGKILL) with verified custody teardown. |
| 12 | `stdout_overflow_protection` | Bounded Stdout Capture | Yes | Yes | Yes | Hard 4 MiB buffer ceiling; overflow triggers fatal exception. |
| 13 | `stderr_overflow_drain` | Stderr Overflow Draining | Yes | Yes | Yes | Excess stderr streams drained safely without failing phase execution. |
| 14 | `liveness_outer_ceiling` | Absolute Timeout / Outer Ceiling | Yes | Yes | Yes | Provider execution supervisor bounds overall execution (default 90,000s). |
| 15 | `liveness_advisory_silence` | Liveness / Advisory Silence Observation | Yes | Yes | Yes | Silence monitored in 900s intervals; never terminates legitimate quiet commands. |
| 16 | `interruption_cleanup` | Interruption & Signal Cleanup | Yes | Yes | Yes | Supervisor traps SIGINT/SIGTERM and cleanly tears down child process group. |
| 17 | `tokenless_auth_probe` | Tokenless Authentication Probe | No | No | No | No non-intrusive tokenless probe exists; truthfully returns `unknown` (fail-open). |
| 18 | `tokenless_quota_probe` | Tokenless Quota Usage Observation | No | No | No | Quota cannot be queried without consuming tokens; returns `unknown` (fail-open). |
| 19 | `subagent_worker_support` | Subagent / Worker Support | No | No | Yes | Supported via Antigravity worker facility and gemini_sub / gemini_flash_sub modes. |
| 20 | `failure_cooldown_tracking` | Failure Cooldown Tracking | Yes | Yes | Yes | SQLite `invocation_attempts` failure history within `window_seconds`. |
| 21 | `run_resumption` | Resume & Recovery Evidence | Yes | Yes | Yes | Full V2 multi-turn execution resumption with attempt derivation and route pinning. |
| 22 | `activity_pipe_telemetry` | Activity Pipe Telemetry | No | No | Yes | Private FIFO token pipe (`AGENT_CENTRAL_ANTIGRAVITY_ACTIVITY_FD`) for progress. |

## Dynamic Routing Interaction

The operational observations collected by `libexec/agent_phase/probes.py` map directly into the dynamic router's 6-stage decision ladder:
1. **Capability Eligibility**: Evaluated strictly from `capabilities.toml` (fails closed).
2. **Hard Unusable Exclusion**: `availability == "unavailable"` or `authentication == "unusable"` excludes an endpoint.
3. **Quota Exhaustion**: Only `quota == "exhausted"` excludes; `unknown` is admitted fail-open.
4. **Active Cooldown Exclusion**: Endpoints with recent failures in SQLite within `window_seconds` are skipped.
5. **Reviewer Independence**: Plan Reviewer != Planner; Work Reviewer != Producer parent.
6. **Deterministic Ranking**: Highest affinity score, with lexical tie-breaking (`-score, provider, profile, endpoint_alias`). Explicit availability bonuses/penalties distinguish known available from unknown or unobserved states.
