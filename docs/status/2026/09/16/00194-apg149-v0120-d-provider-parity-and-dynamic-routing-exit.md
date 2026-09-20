# APG149 — v0.12 Provider Parity Closure, V2 Multi-Turn Semantic Runtime, and Dynamic-Routing Hardening Exit

Phase ID: `APG149`

## Status

Disposition: **amend**. Exit 00194 is allocated to APG149 without renumbering or substitution.  
Outcome: `V0120_D_PROVIDER_PARITY_AND_DYNAMIC_ROUTING_HARDENED` (provider parity formally qualified and closed across Codex, Claude, and Antigravity; truthful 22-row capability conformance matrix committed in JSON and Markdown; Codex qualified for review under read-only posture and `codex-*-review` endpoints; Antigravity review endpoint `antigravity-claude-opus-review` registered with read/reasoning capabilities; on-demand bounded operational observation probes implemented in `probes.py` with 5.0s timeout, credential redaction, canonical SHA-256 digests, active cooldown windowing, and truthful `unknown` state for unobservable quota; 6-stage dynamic routing decision ladder hardened with fail-closed capability eligibility, quota fail-open admission, active cooldown window exclusion, reviewer independence invariants, and deterministic ranking with explicit availability scoring; static preset routing hardened to reject unmerged or unknown bindings; full Request V2 multi-turn semantic execution loop implemented in `v2_turns.py` and `v2_dispatch.py` coordinating all actor bindings, deriving referential attempt lineage, enforcing git worktree guards and read-only process postures, detecting unrecorded mutations, validating reviews with nonce fences, executing plan amend and work revision paths, generating reviser candidates, handling non-zero provider exit codes with typed failures, persisting 8 canonical records into SQLite, and packaging terminal ZIP archives with SHA-256 digests; 38 new unit and integration tests across 5 test suites; 100% pass rate on all dispatcher tests; file length policy fully compliant with 0 failures; zero git publication or commits performed).

Accounting: Historical v0.11 closure accounting remains terminal at 55/55/0/0. Milestone V0120-D delivers the final runtime and parity deliverables under ADR 0065.

## Exact Candidate and Baseline Provenance

- **Candidate APGR Commit**: `388f53e63145b8a6e097b933dde4b6d21811b1fb` (APG148 / V0120-C).
- **Candidate APGR Tree**: `0602b196230bdf8e736bd885e5b0a8b395b6c456`.
- **Source Agent-Central Baseline**: `56e9bb039536dfc8893e61a431681d6a32167b6f` (immutable commit).
- **JACA Reference Baseline**: `08ca2208805cf446bd15da0a6b4c8c58db737587` (unmodified).

## Deliverables Summary

1. **Provider Conformance Matrix & Truthful Claims (ADR 0065 §2)**:
   - Evaluated 22 operational and capability rows across Codex, Claude, and Antigravity (`docs/architecture/provider-conformance-matrix.json` and `docs/architecture/provider-conformance-matrix.md`).
   - Qualified all three providers for reviewer roles (`-s read-only` for Codex, `--read-only` for Claude, `--reviewer` for Antigravity).
   - Truthfully marked `adapter_structured_output` as unsupported at upstream CLI flag level (relying on nonce-fenced decoding).
   - Truthfully marked tokenless authentication and quota probes as unobservable (`unknown`), avoiding credential scraping and model token burn.
   - Documented Antigravity's activity pipe telemetry and verified process group teardown contracts across all providers.

2. **Antigravity Reviewer Endpoint Registration**:
   - Registered `antigravity-claude-opus-review` in `common/dispatcher/endpoints.toml` with profile `claude-opus-4-6-thinking-review` under generation 7.
   - Registered `antigravity-claude-opus-review` in `common/dispatcher/capabilities.toml` with posture `read_only` and capabilities `["read", "reasoning"]`.
   - Qualified reviewer independence for Antigravity-managed review turns.

3. **Bounded Operational Probes (ADR 0065 §1)**:
   - Implemented `libexec/agent_phase/probes.py` with `probe_executable_version`, `probe_authentication`, `probe_quota_usage`, `probe_cooldown`, and `collect_operational_observations`.
   - Bounded execution ceiling: strictly <= 5.0 seconds per probe.
   - Applied cooldown time-windowing parsing both ISO text and float timestamps.
   - Zero credential scraping and zero model token burn.
   - Deterministic SHA-256 canonical digest computation for all operational observations.

4. **Hardened 6-Stage Dynamic Routing Decision Ladder (ADR 0065 §3)**:
   - Evaluates: (1) Capability eligibility (fails closed) -> (2) Hard unavailable / unusable exclusion -> (3) Quota exhausted exclusion (unknown admitted fail-open) -> (4) Active cooldown exclusion within window -> (5) Reviewer independence invariants -> (6) Deterministic affinity scoring with explicit availability weighting and lexical tie-breaking.
   - Hardened `resolve_static_preset_route` to raise typed `RoutingResolutionError` when presented with unmerged or unknown bindings.
   - Handled dynamic no-route condition by returning a typed no-route result payload (`status: "no_route"`).

5. **Full Multi-Turn Semantic Execution Loop (ADR 0065 §4)**:
   - Implemented `libexec/agent_phase/v2_turns.py` orchestrating all configured actor bindings (default 5 turns or unmerged 8 turns).
   - Enforced worktree requirements up front via `candidate.require_worktree(work_tree)`.
   - Dynamic attempt derivation from SQLite `invocation_attempts` with referential predecessor lineage.
   - Enforced Invariant 14: route reuse on same-attempt recovery.
   - Real provider execution wiring via `provider.py` / `build_argv` and CLI `--resume` support.
   - Posture enforcement: launches read-only bindings with read-only sandbox/profile flags; compares pre- and post-turn git tree SHAs to actively detect and block unrecorded mutations.
   - Review validation: parses nonce-fenced results without swallowing errors; extracts structured findings into SQLite `review_findings`.
   - Disposition transitions: transitions findings to `amend` and unreviewable states to `reject`; rejects block subsequent mutating work.
   - Reviser candidates: records `cand-{run_id}-revision` git tree candidates upon amended revisions.
   - Typed failure handling: non-zero provider exit codes mark attempt and semantic responsibilities as failed, distinguishing pre-substantive from substantive failures.
   - Persists all 8 canonical semantic records into SQLite (`v2_records.py`, reusing `semantic_roles.py` dataclasses).
   - Terminal ZIP archive packaging with SHA-256 digest in `runs` and `completion_receipts` table.

6. **File Length Governance & Architectural Hygiene**:
   - Compacted `libexec/agent_phase/persistence.py` to 990 lines (strictly under 1000 lines failure ceiling).
   - Compacted `libexec/agent_phase/v2_records.py` to 124 lines by deduplicating dataclasses with `semantic_roles.py`.
   - All newly created modules strictly comply with file length limits: `probes.py` (305), `v2_prompts.py` (137), `v2_records.py` (124), `v2_turns.py` (477), `v2_dispatch.py` (261), `dynamic_router.py` (375).
   - Registered all new modules in `testing/apg-test-inventory.json` under `dispatcher_sources`.
   - `python3 tools/ci/file_length_policy.py` reports 0 failures and passes cleanly.

7. **Liveness and Timeout Disposition (Section F)**:
   - ADR 0061 specified 900-second advisory silence and 90,000-second outer ceiling.
   - Disposition: Retained with evidence-based semantics. The 900-second silence interval is purely advisory (emitting telemetry notices without killing background work). The 90,000-second outer ceiling enforces an absolute safety ceiling for runaway processes. Observed activity refreshes silence tracking. Separate states are distinguished: activity observed, advisory silence, hard timeout, provider exit code, transport failure, and operator interruption.

8. **Live Canary Status**:
   - Local non-destructive CLI canaries executed against installed binaries (`codex --version`, `claude`, `antigravity`).
   - Deterministic qualification test suite runs entirely provider-free with mock runners and simulated subprocesses, ensuring complete test coverage without consuming live token quota or requiring live network credentials. Live observations are maintained separately from deterministic test gates.

9. **Verification & Test Coverage**:
   - 38 unit and integration tests across 5 focused test suites:
     - `test_agent_phase_v2_dispatch.py` (10 tests, including typed no-route result and retry rerouting)
     - `test_agent_phase_v2_full_execution.py` (10 tests, including happy path, plan amend, work revision, plan rejection, read-only mutation detection, and exit code failures)
     - `test_agent_phase_dynamic_routing_hardened.py` (8 tests)
     - `test_agent_phase_operational_probes.py` (6 tests, including cooldown windowing and ISO text timestamps)
     - `test_agent_phase_provider_parity.py` (4 tests, cross-checking 22 conformance rows and capabilities.toml)
   - 100% pass rate across the full dispatcher test suite.

10. **Remaining Provider Gaps & Explicit Deferrals**:
    - Remaining Gaps: Upstream provider CLIs do not provide native JSON schema enforcement flags (standardized on nonce-fenced decoding); remaining quota cannot be queried without model invocation (handled fail-open as `unknown`); subagent worker supervision is supported under Antigravity but not standalone Codex/Claude CLIs.
    - Explicit Deferrals to V0120-E: Go package exports (`pkg/phase`, `pkg/candidate`, `pkg/evidence`, `pkg/provider`), JACA integration fixtures, and JACA qualification harness.
    - Explicit Deferrals to V0120-F: Release operator hardening invariants, Nixpkgs disposition, and full release verification suite.
    - Next Phase: **V0120-E — Go Surfaces and JACA Qualification / Handoff**.
