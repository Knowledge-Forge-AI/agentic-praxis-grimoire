# Agent-Central Dispatcher Migration Inventory (v0.12)

- Status: Accepted Architecture Inventory
- Target Version: APGR v0.12
- Inspected Pinned Baseline: Agent-Central `56e9bb039536dfc8893e61a431681d6a32167b6f`
- Governing Decisions: ADR 0058, ADR 0061

## Overview

This document establishes the inventory of files, modules, configuration assets,
and scripts inspected in Agent-Central for migration into APGR during the v0.12
program.

Each asset is assigned one of four dispositions:

1. **`MIGRATE`**: Asset will be transferred into APGR during stage `V0120-B` and maintained natively within APGR.
2. **`COMPATIBILITY-SHIM`**: Recommended lightweight forwarding wrapper to be retained in Agent-Central (delivered as an advisory recommendation for the Agent-Central team to disposition; APGR executes no mutations in Agent-Central).
3. **`RETAIN`**: Excluded from APGR migration scope. APGR claims no ownership and proposes no change; whether the asset stays, moves, or is deleted is entirely the Agent-Central team's decision.
4. **`REJECT`**: Concepts, daemons, or out-of-scope mechanisms permanently excluded from APGR.

### Coverage statement

At the pinned baseline, `libexec/agent_phase/` contains **62** Python modules.
All 62 are enumerated individually in §1 below; the module rationales are derived
from each module's own docstring at that baseline rather than inferred from its
filename. §2 covers the 10 `bin/agent-phase-*` wrappers and the
`libexec/controller_generation*.py` bootstrap chain that `bin/agent-phase-dispatch`
actually invokes. §3 covers provider catalogs and profile compilers. §4 covers the
65 `tests/test_agent_phase_*.py` suites. `V0120-B`'s parity exit criterion is
evaluated against this enumeration; any asset discovered at migration time that is
absent here is a scope finding for `V0120-B`, not a silent addition.

> **Entrypoint note.** `libexec/agent_phase/cli.py` is the argparse entrypoint for
> all `agent-phase-*` commands. `libexec/agent_phase/dispatch.py` is the stage
> orchestration engine, not a CLI entrypoint. `bin/agent-phase-dispatch` does not
> call either directly: it execs `libexec/controller_generation_bootstrap.py
> dispatch`, which is why the controller-generation chain is in migration scope.

---

## 1. Core Dispatcher Runtime (`libexec/agent_phase/`, 62 modules)

### 1.1 Entry, orchestration, and lifecycle

| Agent-Central Source Path | Disposition | Target Location in APGR | Architectural Rationale |
| --- | --- | --- | --- |
| `libexec/agent_phase/__init__.py` | **MIGRATE** | `libexec/agent_phase/__init__.py` | Package marker: semantic phase requests to routed provider runs. |
| `libexec/agent_phase/cli.py` | **MIGRATE** | `libexec/agent_phase/cli.py` | Argparse entrypoints for every `agent-phase-*` command (`dispatch`, `resolve`, `scan-summary`, `scan-label`). |
| `libexec/agent_phase/dispatch.py` | **MIGRATE** | `libexec/agent_phase/dispatch.py` | Stage orchestration engine for dispatcher-owned lifecycle specifications; each stage is a fresh process with explicitly rebuilt context. Includes the standard five-stage progression. |
| `libexec/agent_phase/lifecycle.py` | **MIGRATE** | `libexec/agent_phase/lifecycle.py` | Closed, typed lifecycle and Git-finalization policy registry (`standard`/`solo`, `publish`). |
| `libexec/agent_phase/lifecycle_dispatch.py` | **MIGRATE** | `libexec/agent_phase/lifecycle_dispatch.py` | Execution helpers for **non-standard** lifecycle specifications. |
| `libexec/agent_phase/dry_run.py` | **MIGRATE** | `libexec/agent_phase/dry_run.py` | No-provider lifecycle resolution and first-prompt rendering. |
| `libexec/agent_phase/display.py` | **MIGRATE** | `libexec/agent_phase/display.py` | Live operator display; a strict observer that can never alter dispatch behaviour. |

### 1.2 Request, routing, and roster

| Agent-Central Source Path | Disposition | Target Location in APGR | Architectural Rationale |
| --- | --- | --- | --- |
| `libexec/agent_phase/request.py` | **MIGRATE** | `libexec/agent_phase/request.py` | Strict `agent-phase-request-v1` parsing; carries phase semantics only. Extension point for Request V2 (ADR 0060). |
| `libexec/agent_phase/routing.py` | **MIGRATE** | `libexec/agent_phase/routing.py` | Pure, launch-free resolution of a phase request into a routed multi-stage phase plan (`agent-phase-resolved-v6`), including the derived per-provider `intelligence` block read back from profile authority. Deterministic given an `execution_mode`; the bounded router of ADR 0060 §3 extends this module rather than replacing it. |
| `libexec/agent_phase/roster.py` | **MIGRATE** | `libexec/agent_phase/roster.py` | Closed, bounded capture and lookup for the tracked dispatcher roster (provider and profile only; model/effort remain profile-owned). |
| `libexec/agent_phase/route_provenance.py` | **MIGRATE** | `libexec/agent_phase/route_provenance.py` | Truthful route provenance and transition audit records, including `RESOLVED_V6` and effective-route construction. |
| `libexec/agent_phase/worker_capability.py` | **MIGRATE** | `libexec/agent_phase/worker_capability.py` | Optional worker capability resolution; the dispatcher must stay importable when the worker facility is absent. |

### 1.3 Provider invocation and transport

| Agent-Central Source Path | Disposition | Target Location in APGR | Architectural Rationale |
| --- | --- | --- | --- |
| `libexec/agent_phase/provider.py` | **MIGRATE** | `libexec/agent_phase/provider.py` | Provider invocation; dispatcher-owned argv construction with no shell string anywhere and no prompt on the command line. |
| `libexec/agent_phase/transport.py` | **MIGRATE** | `libexec/agent_phase/transport.py` | Provider-specific prompt transport bounds (`ensure_prompt_fits`). |
| `libexec/agent_phase/capacity.py` | **MIGRATE** | `libexec/agent_phase/capacity.py` | Lifecycle-aware prompt capacity planning before the first provider turn is spent. |
| `libexec/agent_phase/prompt_policy.py` | **MIGRATE** | `libexec/agent_phase/prompt_policy.py` | Deterministic policy for brittle Git-state identities in model-facing prose. |
| `libexec/agent_phase/envelope.py` | **MIGRATE** | `libexec/agent_phase/envelope.py` | Dispatcher-owned prompt envelopes rendered ahead of every task prompt; owns stage, allowed action, and reviewer framing. |
| `libexec/agent_phase/run.py` | **MIGRATE** | `libexec/agent_phase/run.py` | Durable run artifacts, written outside any target repository. |
| `libexec/agent_phase/runtime_exclusion.py` | **MIGRATE** | `libexec/agent_phase/runtime_exclusion.py` | Exact disposable-runtime boundary shared by evidence consumers. |

### 1.4 Result parsing, repair, and artifacts

| Agent-Central Source Path | Disposition | Target Location in APGR | Architectural Rationale |
| --- | --- | --- | --- |
| `libexec/agent_phase/result.py` | **MIGRATE** | `libexec/agent_phase/result.py` | Strict provider stage-result parsing; exit 0 is explicitly not a completion claim. |
| `libexec/agent_phase/jsonc.py` | **MIGRATE** | `libexec/agent_phase/jsonc.py` | Bounded JSONC normalization for nonce-fenced provider results. |
| `libexec/agent_phase/outcomes.py` | **MIGRATE** | `libexec/agent_phase/outcomes.py` | Additive terminal truth plus closed dispatcher-owned failure categories. |
| `libexec/agent_phase/result_artifacts.py` | **MIGRATE** | `libexec/agent_phase/result_artifacts.py` | Canonical machine and human result artifacts (`result.json`, `result.md`) for a run. |
| `libexec/agent_phase/result_repair.py` | **MIGRATE** | `libexec/agent_phase/result_repair.py` | Repository-detached formatting repair for one retained terminal response. |
| `libexec/agent_phase/result_repair_authority.py` | **MIGRATE** | `libexec/agent_phase/result_repair_authority.py` | Structured operator authority gating explicit result-repair finalization. |
| `libexec/agent_phase/failure_boundary.py` | **MIGRATE** | `libexec/agent_phase/failure_boundary.py` | Mechanical candidate accounting at an incomplete mutating-stage boundary. |

### 1.5 Candidate identity, Git state, and mutation authority

| Agent-Central Source Path | Disposition | Target Location in APGR | Architectural Rationale |
| --- | --- | --- | --- |
| `libexec/agent_phase/candidate.py` | **MIGRATE** | `libexec/agent_phase/candidate.py` | Candidate identity independent of any model claim: a real Git tree object built from the working tree. |
| `libexec/agent_phase/gitstate.py` | **MIGRATE** | `libexec/agent_phase/gitstate.py` | Dispatcher-owned Git facts: entry state, phase delta, and the local commit, computed outside provider sandboxes. |
| `libexec/agent_phase/native_git.py` | **MIGRATE** | `libexec/agent_phase/native_git.py` | Explicit native-Git transition custody and independent reconciliation of authorized native-tool commits. |
| `libexec/agent_phase/native_git_cli.py` | **MIGRATE** | `libexec/agent_phase/native_git_cli.py` | Provider-free operator native-Git authorization command. |
| `libexec/agent_phase/stage_delta.py` | **MIGRATE** | `libexec/agent_phase/stage_delta.py` | Consecutive stage-boundary evidence; classifies changes as product versus operational metadata. |
| `libexec/agent_phase/path_disposition.py` | **MIGRATE** | `libexec/agent_phase/path_disposition.py` | Structured publication ownership. Git observations alone do not own deletions; this is the mutation-scope and path-exclusion authority. |
| `libexec/agent_phase/ownership_challenge.py` | **MIGRATE** | `libexec/agent_phase/ownership_challenge.py` | Immutable unclaimed-deletion ownership observations and separate, closed resolution events. Not a general mutation-authority module. |
| `libexec/agent_phase/ownership_cli.py` | **MIGRATE** | `libexec/agent_phase/ownership_cli.py` | Provider-free manager resolutions binding one immutable ownership challenge per receipt. |
| `libexec/agent_phase/metadata_policy.py` | **MIGRATE** | `libexec/agent_phase/metadata_policy.py` | Pure built-in operational-metadata classification with no Git dependency. |
| `libexec/agent_phase/metadata_noop.py` | **MIGRATE** | `libexec/agent_phase/metadata_noop.py` | Closed proof for exclusion of already-observed, unpublished metadata. |

### 1.6 Review checkpoints

| Agent-Central Source Path | Disposition | Target Location in APGR | Architectural Rationale |
| --- | --- | --- | --- |
| `libexec/agent_phase/plan_material.py` | **MIGRATE** | `libexec/agent_phase/plan_material.py` | Dispatcher-owned, byte-bound material selection for a planning checkpoint. |
| `libexec/agent_phase/review_binding.py` | **MIGRATE** | `libexec/agent_phase/review_binding.py` | Attribution-free immutability fence for independent review checkpoints. |
| `libexec/agent_phase/review_result.py` | **MIGRATE** | `libexec/agent_phase/review_result.py` | Nonce-bound structured outcomes for independent review stages. |
| `libexec/agent_phase/review_recovery.py` | **MIGRATE** | `libexec/agent_phase/review_recovery.py` | One fresh independent review after a successful but invalid review transport. |
| `libexec/agent_phase/checkpoint.py` | **MIGRATE** | `libexec/agent_phase/checkpoint.py` | Exact, reconstruction-verified evidence for checkpoint candidates. |

### 1.7 Finalization, resume, and recovery

| Agent-Central Source Path | Disposition | Target Location in APGR | Architectural Rationale |
| --- | --- | --- | --- |
| `libexec/agent_phase/finalization.py` | **MIGRATE** | `libexec/agent_phase/finalization.py` | Dispatcher-owned Git finalization for normal and resumed lifecycles. |
| `libexec/agent_phase/finalization_proof.py` | **MIGRATE** | `libexec/agent_phase/finalization_proof.py` | Exact-run recovery proofs with no provider, publication, or worktree writes. |
| `libexec/agent_phase/finalization_recovery.py` | **MIGRATE** | `libexec/agent_phase/finalization_recovery.py` | Provider-free finalization with new receipts over immutable source runs. |
| `libexec/agent_phase/publication.py` | **MIGRATE** | `libexec/agent_phase/publication.py` | Dispatcher-owned push state around mechanically fixed Git operations. |
| `libexec/agent_phase/publication_summary.py` | **MIGRATE** | `libexec/agent_phase/publication_summary.py` | Separates disposition-eligible Git paths from historical stage observations. |
| `libexec/agent_phase/resume.py` | **MIGRATE** | `libexec/agent_phase/resume.py` | Validated, immutable evidence for same-phase dispatcher resume. |
| `libexec/agent_phase/resume_validation.py` | **MIGRATE** | `libexec/agent_phase/resume_validation.py` | Strict source-run structure and artifact validation before resume. |
| `libexec/agent_phase/resume_dispatch.py` | **MIGRATE** | `libexec/agent_phase/resume_dispatch.py` | Provider suffix execution for a validated resume plan. |
| `libexec/agent_phase/adoption.py` | **MIGRATE** | `libexec/agent_phase/adoption.py` | Explicit operator selection of sealed objects for a new substantive request; bounded checksummed local authority records. |
| `libexec/agent_phase/adoption_cli.py` | **MIGRATE** | `libexec/agent_phase/adoption_cli.py` | Provider-free operator adoption command. |
| `libexec/agent_phase/entry_adoption.py` | **MIGRATE** | `libexec/agent_phase/entry_adoption.py` | Explicit entry-candidate adoption for pre-existing worktree modifications. |
| `libexec/agent_phase/entry_adoption_cli.py` | **MIGRATE** | `libexec/agent_phase/entry_adoption_cli.py` | Provider-free operator entry-candidate adoption command. |

### 1.8 Archive and evidence transport

| Agent-Central Source Path | Disposition | Target Location in APGR | Architectural Rationale |
| --- | --- | --- | --- |
| `libexec/agent_phase/archive.py` | **MIGRATE** | `libexec/agent_phase/archive.py` | Atomic, no-clobber ZIP packaging for one finalized run directory. |
| `libexec/agent_phase/archive_snapshot.py` | **MIGRATE** | `libexec/agent_phase/archive_snapshot.py` | Bounded, no-follow snapshots of dispatcher evidence, excluding owned runtimes. |
| `libexec/agent_phase/archive_verify.py` | **MIGRATE** | `libexec/agent_phase/archive_verify.py` | Read-only verification of legacy and receipt-backed run transports. |
| `libexec/agent_phase/archive_recovery.py` | **MIGRATE** | `libexec/agent_phase/archive_recovery.py` | Provider-free, Git-free review transport from one exact settled local run. |
| `libexec/agent_phase/antigravity_evidence.py` | **MIGRATE** | `libexec/agent_phase/antigravity_evidence.py` | Closed validation for dispatcher-owned Antigravity terminal evidence. |
| `libexec/agent_phase/antigravity_output_recovery.py` | **MIGRATE** | `libexec/agent_phase/antigravity_output_recovery.py` | Exact recovery of one successful Antigravity response lost to capture policy. |

### 1.9 Optional worker custody (dispatcher side)

| Agent-Central Source Path | Disposition | Target Location in APGR | Architectural Rationale |
| --- | --- | --- | --- |
| `libexec/agent_phase/worker_custody.py` | **MIGRATE** | `libexec/agent_phase/worker_custody.py` | Drains optional owned children before final stage observations. Dispatcher-side custody only; the worker pool implementation is `RETAIN` (§5). |
| `libexec/agent_phase/worker_recovery.py` | **MIGRATE** | `libexec/agent_phase/worker_recovery.py` | Read-only resume qualification for previously uncertain owned cleanup. |

### 1.10 Pre-execution and telemetry scanning

| Agent-Central Source Path | Disposition | Target Location in APGR | Architectural Rationale |
| --- | --- | --- | --- |
| `libexec/agent_phase/scanner.py` | **MIGRATE** (reclassified) | `libexec/agent_phase/scanner.py` | Reclassified from RETAIN to MIGRATE in `V0120-B` per ADR 0063. Pre-execution dispatcher sanity checks and CLI scan labeling import and invoke scanner validation routines. |

---

## 2. Command Wrappers and Controller-Generation Bootstrap

| Agent-Central Source Path | Disposition | Target Location in APGR | Architectural Rationale |
| --- | --- | --- | --- |
| `bin/agent-phase-dispatch` | **MIGRATE** (behaviour & path) | `bin/agent-phase-dispatch` | Native APGR launcher executing `libexec/controller_generation_bootstrap.py dispatch`. Preserved at native path for parity; Agent-Central may forward to this script. |
| `bin/agent-phase-resolve` | **MIGRATE** | `bin/agent-phase-resolve` | Native APGR launcher forwarding to `cli.py resolve`. |
| `bin/agent-phase-archive` | **MIGRATE** | `bin/agent-phase-archive` | Native APGR run archive packaging entrypoint. |
| `bin/agent-phase-finalize` | **MIGRATE** | `bin/agent-phase-finalize` | Native APGR finalization entrypoint. |
| `bin/agent-phase-native-git` | **MIGRATE** | `bin/agent-phase-native-git` | Native APGR Native-Git authorization entrypoint. |
| `bin/agent-phase-ownership` | **MIGRATE** | `bin/agent-phase-ownership` | Native APGR Ownership-challenge resolution entrypoint. |
| `bin/agent-phase-adopt` | **MIGRATE** | `bin/agent-phase-adopt` | Native APGR Operator adoption entrypoint. |
| `bin/agent-phase-adopt-entry` | **MIGRATE** | `bin/agent-phase-adopt-entry` | Native APGR Entry-candidate adoption entrypoint. |
| `bin/agent-phase-scan-label` | **MIGRATE** | `bin/agent-phase-scan-label` | Native APGR Scan labelling entrypoint. |
| `bin/agent-phase-scan-summary` | **MIGRATE** | `bin/agent-phase-scan-summary` | Native APGR Scan summary entrypoint. |
| `libexec/controller_generation_bootstrap.py` | **MIGRATE** | `libexec/controller_generation_bootstrap.py` | Directly invoked by `bin/agent-phase-dispatch`; establishes generation-isolated runtime before dispatch. |
| `libexec/controller_generation.py` | **MIGRATE** | `libexec/controller_generation.py` | Generation identity and resolution. |
| `libexec/controller_generation_store.py` | **MIGRATE** | `libexec/controller_generation_store.py` | Generation object store. |
| `libexec/controller_generation_process.py` | **MIGRATE** | `libexec/controller_generation_process.py` | Generation process construction. |
| `libexec/controller_generation_admin.py` | **MIGRATE** | `libexec/controller_generation_admin.py` | Generation administration commands. |

---

## 3. Provider Catalogs and Profile Configurations

| Agent-Central Source Path | Disposition | Target Location in APGR | Architectural Rationale |
| --- | --- | --- | --- |
| `common/dispatcher/endpoints.toml` | **MIGRATE** | `common/dispatcher/endpoints.toml` | Declares model endpoints, context limits, and timeout parameters. |
| `common/dispatcher/routes.toml` | **MIGRATE** | `common/dispatcher/routes.toml` | Maps execution modes to provider profiles across stage types (30 routes). |
| `common/dispatcher/README.md` | **MIGRATE** | `common/dispatcher/README.md` | Documentation for route and endpoint configuration. |
| `antigravity/profiles/*` | **MIGRATE** | `antigravity/profiles/*` | Provider profile templates for Gemini / Antigravity models. |
| `claude/profiles/*` | **MIGRATE** | `claude/profiles/*` | Provider profile templates for Anthropic Claude models. |
| `claude/model-catalog-v1.json` | **MIGRATE** | `claude/model-catalog-v1.json` | Standard model catalog for Claude profiles. |
| `codex/profiles/*` | **MIGRATE** | `codex/profiles/*` | Provider profile templates for OpenAI Codex models. |
| `codex/config.d/170-subagents.toml` | **MIGRATE** | `codex/config.d/170-subagents.toml` | Codex worker configuration schema and defaults. |
| `libexec/antigravity_profile.py` | **MIGRATE** | `libexec/antigravity_profile.py` | Compiles Antigravity runtime profiles from descriptors. |
| `libexec/antigravity_terminal_evidence.py` | **MIGRATE** | `libexec/antigravity_terminal_evidence.py` | Antigravity terminal output parsing and validation. |
| `libexec/claude_vc_profile.py` | **MIGRATE** | `libexec/claude_vc_profile.py` | Compiles Claude runtime profiles and `PROFILE_CONTRACTS`, read back by `routing.py`. |
| `libexec/claude_model_catalog.py` | **MIGRATE** | `libexec/claude_model_catalog.py` | Catalog metadata and role resolution for Claude model variants. |
| `libexec/claude_live_renderer.py` | **MIGRATE** | `libexec/claude_live_renderer.py` | Live rendering formatting for Claude stream output. |
| `libexec/agent_source_guidance.py` | **MIGRATE** | `libexec/agent_source_guidance.py` | Repository-wide agent prompt guidance resolution. |

---

## 4. Dispatcher Test Suites

| Agent-Central Source Path | Disposition | Target Location in APGR | Architectural Rationale |
| --- | --- | --- | --- |
| `tests/test_agent_phase_*.py` (65 suites) | **MIGRATE** | `src/test/dispatcher/` | Migrated under dedicated sidecar test lane `src/test/dispatcher/`, run via `bin/apg-test-dispatcher`. |
| `tests/test_controller_generation_*.py` (6 suites) | **MIGRATE** | `src/test/dispatcher/` | Controller generation and cutover tests migrated alongside dispatcher suites. |
| Golden parity corpus | **NEW (APGR)** | `src/test/dispatcher/test_agent_phase_parity_corpus.py` | Continuous verification of all 30 routes, grammar, topology, readback, and errors against `fixtures/parity_golden_corpus.json`. |
| `claude/test/test_claude_*.py` (4 suites) | **DEFER** | `src/test/dispatcher/` (V0120-C/D) | Baseline helper suites for Claude profile/catalog/rendering CLI tools; integrated execution is covered by dispatcher test suites; standalone suites deferred to V0120-C/D. |
| `antigravity/tests/test_*.py` (3 suites) | **DEFER** | `src/test/dispatcher/` (V0120-C/D) | Baseline helper suites for Antigravity launcher/evidence CLI tools; integrated execution is covered by dispatcher test suites; standalone suites deferred to V0120-C/D. |
| `codex/tests/test_codex_profiles.py` (1 suite) | **DEFER** | `src/test/dispatcher/` (V0120-C/D) | Baseline helper suite for Codex profile compilation; integrated execution is covered by dispatcher routing tests; standalone suite deferred to V0120-C/D. |

---

## 5. Forwarding Wrappers and Compatibility Shims

| Component / Path | Disposition | Execution Owner | Architectural Rationale |
| --- | --- | --- | --- |
| `bin/agent-phase-dispatch` (path retention) | **COMPATIBILITY-SHIM** | Agent-Central Team (Recommendation) | Thin shell wrapper forwarding to the APGR dispatch subcommand, preserving existing operator habit and automated launcher compatibility. |
| `common/dispatcher/` links | **COMPATIBILITY-SHIM** | Agent-Central Team (Recommendation) | Symlinks or redirection pointing at APGR's installed configurations. |

---

## 6. Assets Excluded from APGR Migration Scope

APGR claims no ownership over the following and proposes no change to them. Their
future placement is entirely the Agent-Central team's decision.

| Component / Path | Disposition | Architectural Rationale |
| --- | --- | --- |
| `bin/agent-worker` | **RETAIN** | Interactive supervisor process for ad-hoc local child workers; independent of structured phase execution. |
| `libexec/agent_workers/` | **RETAIN** | Implementation of interactive worker pools and quota tracking. |
| `common/workers/policy.json` | **RETAIN** | Worker pool policy owned by the local worker facility, not by phase execution. |
| Host credential and security tooling | **RETAIN** | API keys, private tokens, macOS keychain access, and host authorization helpers are host-level concerns outside a portable developer tool. |
| Workstation multi-repo tooling | **RETAIN** | Machine-specific sync and checkout scripts. |
| Personal shell and client configuration | **RETAIN** | Shell startup files, editor settings, and per-client agent configuration are host/home-level assets, not repository assets of the dispatcher runtime, and are explicitly out of scope per the v0.12 migration boundary. |

---

## 7. Excluded and Rejected Mechanisms

| Prototyped or Proposed Concept | Disposition | Rationale for Rejection |
| --- | --- | --- |
| Multi-phase roadmap manager loop | **REJECT** | Violates APGR's single-phase boundary (ADR 0058); multi-phase orchestration belongs exclusively to JACA. |
| Long-running background daemon | **REJECT** | Violates stateless CLI execution invariant; APGR runs on-demand without daemon overhead. |
| Predictive scheduling engine | **REJECT** | Dynamic routing in APGR is bounded, empirical, and immediate; no probabilistic future modeling. |
| Generalized host command broker | **REJECT** | APGR is an execution runtime, not an OS security sandbox. Security is minimal and fence-based (ADR 0061 §4). |
| Machine-specific Nix-darwin configs | **REJECT** | Host workstation definitions have no place in a portable, embeddable developer tool. |
