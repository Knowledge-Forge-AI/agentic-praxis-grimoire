# APG150B — APGR V0120-E-HARDEN1 — Provider Failure Feedback and Dynamic Reroute Exit

Phase ID: `APG150B`
Exit ID: `Exit 00198`

## Status

Disposition: **advance**. Exit 00198 records the successful implementation and verification of provider failure feedback, high-confidence quota classification, SQLite schema v2, and bounded dynamic rerouting ($M=3$) under Milestone V0120-E-HARDEN1. Transient provider exhaustion events (such as Codex 429 quota exhaustion modeled via simulated test fixtures) are deterministically classified, sanitized, durably recorded in SQLite, and dynamically rerouted to eligible alternatives (e.g. Antigravity or Claude) while enforcing a strict substantive work integrity fence.
Outcome: `V0120_E_PROVIDER_FEEDBACK_AND_DYNAMIC_REROUTE_HARDENED`

## Accomplishments

### 1. High-Confidence Provider Classifier & Sanitized Evidence
Implemented `libexec/agent_phase/failure_classifier.py` providing deterministic classification of execution failures:
- Matches the captured high-confidence provider quota failure signature from Codex (`You've hit your usage limit. Visit https://chatgpt.com/codex/settings/usage...`), assigning `CONFIDENCE_EXACT` and authorizing dynamic rerouting. Unverified provider error patterns (generic HTTP 429 status codes, heuristic rate limit or token limit messages) remain unpersisted fallback errors with non-reroutable status per Requirement B.
- Evaluates the signature on stderr or solely on banner-only stdout (`is_recognized_codex_quota_banner_only`), preventing agent-controlled stdout model prose from forging provider-wide exclusions (HIGH-1).
- Derives observation type, state value, and base reroutability directly from `ROUTER_MAPPING_BY_CATEGORY` (MED-10).
- Parses reset times into absolute Unix timestamps while strictly preserving host-local timezone provenance.
- Classifies unverified, generic, or ambiguous errors as non-reroutable, preventing erroneous fallback.
- Sanitizes captured error excerpts to redact authentication tokens, private prompts, and path details.

### 2. SQLite Persistence Schema v2
Implemented `libexec/agent_phase/persistence_feedback.py` extending dispatcher persistence:
- Migration table `invocation_observation_relations` linking failed attempts to generated observations with composite primary key `(attempt_id, observation_id)`.
- Idempotent observation recording with SHA-256 digest validation: matching digests succeed without duplication, while conflicting digests fail closed.
- Active durable observation queries (`get_active_operational_observations`) filtering by `expires_at > now`.
- Relocated duplicate observation helpers from `persistence.py`, keeping module line count well under policy thresholds.

### 3. Bounded Dynamic Reroute ($M=3$) and Semantic Role Lifecycle
Implemented `libexec/agent_phase/v2_reroute.py` and updated `libexec/agent_phase/v2_turns.py`:
- Actor binding attempts bounded by $\min(3, \text{distinct eligible routes})$.
- Implemented `retry_pending` status transition for semantic responsibilities during rerouting, failing closed to `failed` when retries are exhausted or no routes remain.
- Attempt lineage tracked through `predecessor_attempt_id` pointing to previous attempt.
- Substantive work fence: rerouting is strictly prohibited if an attempt produced unrecorded tree mutations or stdout content (with banner-only stdout carved out as pre-substantive); substantive failures terminate immediately as `SubstantiveFailureError`. Observation persistence is gated on `not substantive`.
- Dropped conflating fallback in `execute_v2_turns` to ensure injected operator observations are passed cleanly (MED-8).

### 4. Canonical Artifact Emission, Closed Schemas, and Agent-Central Topology
- Turn failures emit `apgr-provider-failure-v1` artifacts conforming to a pinned, validated closed schema containing binding/attempt identity, exit code, classification category, confidence, match basis, sanitized excerpt, stdout/stderr digests, observation IDs, observation digests, observation expirations, reset hint, parsed reset timestamp, timezone provenance, substantive boundary facts, observed_at, and retry decision.
- Route resolutions emit `apgr-route-decision-v1` artifacts conforming to a pinned, validated closed schema capturing chosen routes, policy snapshots, active observation IDs, and rejections with explicit elimination rationales (including typed `exhausted` outcome on terminal no-route paths).
- **JSON/JSONC Syntax vs. Semantic Separation (FINAL3 Amendment)**: Generic agent JSON syntax validation is decoupled from semantic interpretation. At the syntax layer, any syntactically valid JSON value (object, array, string, number, boolean, null) and standard JSONC comments/trailing commas supported by the shared parser are accepted (`result.py`, `review_result.py`, `test_agent_phase_jsonc_results.py`). Valid JSON is never classified as invalid due to root kind, extra fields, or example shape differences; root-shape policing is eliminated. Downstream semantic adapters consume only facts actually present: missing completion semantics represent the stage as semantically blocked rather than throwing a JSON syntax error, while missing review semantics return `unreviewable`. Semantic incompleteness is treated as blocked or unreviewable, not JSON-invalid. Agent-Central remains an active supported reference baseline, and FINAL3 is the narrow parser and semantic-adapter amendment to APG150B.
- **Agent-Central Reference Doctrine & V2 Outbox Topology**: Agent-Central (`~/projs/agent-central`) remains an active, supported reference implementation and is NOT being decommissioned. APGR now owns and evolves its copy without immediate Agent-Central decommissioning. APGR improves upon reference behavior by default, with deliberate, documented, and tested divergences. APGR V2 operator outbox projection topology directly mirrors current Agent-Central layout:
  ```text
  <outbox_root>/<project>/<phase-id>/
    <phase-id>-dispatch--<timestamp>        -> canonical run directory
    <phase-id>-dispatch--<timestamp>.zip    -> canonical archive
    <phase-id>-dispatch--<timestamp>.locator.json (atomic regular file)
  ```
  The redundant `<outbox_root>/phase-dispatch/` prefix is eliminated for new APGR V2 projections, aligning with Go `internal/response/filesystem.go:102`. Canonical APGR V2 state remains under `<APGR_HOME>/state`. Historical projections remain untouched, and failed runs project truthful canonical evidence and operator locators.

### 5. Cross-Language Conformance and Golden Vectors
- Added 7 feedback routing scenarios to `tools/conformance/feedback_scenarios.py` covering profile isolation, active pruning, fallback ladders, and scenario time expiration.
- Regenerated golden vector corpus `testing/fixtures/conformance/dynamic_routing_scenarios.json`.
- Validated complete cross-language conformance across Python and Go test suites.

### 6. Qualification and Verification
- **New & Refined Test Suites**:
  - `src/test/dispatcher/test_agent_phase_bootstrap_regression.py`: 7 tests proving injected observation handling, snapshot retention, lexical scoping, hermetic AST fixture validation on previous failed dispatch, and failure evidence/outbox projection.
  - `src/test/dispatcher/test_agent_phase_provider_classifier.py`: 12 tests verifying exact quota pattern recognition, ordinal timestamp parsing, timezone preservation, sanitization, Scope E mapping, and stdout forgery prevention.
  - `src/test/dispatcher/test_agent_phase_persistence_feedback.py`: 6 tests covering schema v2 migration, idempotent recording, digest mismatch detection, and active observation queries.
  - `src/test/dispatcher/test_agent_phase_probes_precedence.py`: 6 tests proving observation precedence (injected > durable SQLite > tokenless probes) and deterministic probe timestamps honoring supplied now.
  - `src/test/dispatcher/test_agent_phase_v2_reroute.py`: 7 tests validating bounded retries, predecessor tracking, substantive work rejection, closed schema validation, exhausted decision artifacts, and attempt resumption without duplicates.
- **File Length & Code Quality Policy**: `tools/ci/file_length_policy.py` reports zero failure-limit violations under 1000 lines (`v2_turns.py` decomposed to 763 lines, strictly below the 800 warning threshold).
- **Cross-Language Conformance**: Python conformance tests and Go routing tests pass 100%.
- **Milestone Boundary**: V0120-E-HARDEN1 is closed. FINAL3 is the narrow parser and semantic-adapter amendment to APG150B. V0120-F does not duplicate the Codex provider-result feedback work and remains confirmed as NOT STARTED until this exit is formally accepted.
- Next milestone: **V0120-F** (Release Hardening, Conditional Nixpkgs, and Integrated Readiness).

### 7. Requirement S Recovery Snapshot & Publication Accounting
Per Requirement S and publication accounting:
- **Joint Publication Accounting**: A prior solo finalization partially published APG150B as commit `0670d497d9f3a4c0e56ec8291c07babe693ce5ab` (publishing only `docs/status/README.md`) due to an operator recovery script single-dirty-path collection defect on macOS. The subsequent FINAL2 commit publishes the remaining 28 adopted APG150B candidate paths as its direct descendant, jointly constituting the full publication of APG150B.
- `refs/apgr/recovery/apg150b-final2-20260917T231817Z` (`commit 334027a5e206aeb133fd00fa7496e0ff2f698011`, `tree 2ffcef7ccea7c9c1add1ad5566f7484410147378`): Snapshotted the full 28 adopted candidate paths prior to provider execution.
- `refs/apgr/recovery/apg150b-bootstrap-worktree-20260917T203157Z` (`commit 9f32a6867d17321384142219fb3ad981cc9fd0c8`, `tree 3b8b40b5240b5a4a0997b5e5b64b8b13e0646380`):
  - Failure cause analysis: `NameError: name 'injected_observations' is not defined` in `v2_dispatch.py` due to variable referenced without definition in local scope or parameter list.
  - Salvaged / Reused: Feedback module decomposition concepts and persistence schema v2 structure.
  - Rejected: Unbound local `injected_observations` reference; reimplemented with proper parameter passing in `v2_dispatch.py` and hermetic AST regression test (`test_agent_phase_bootstrap_regression.py:test_6_broken_snapshot_shape_demonstrates_name_error_and_fix_succeeds`).
- `refs/apgr/recovery/v0120-e-harden1-worktree-20260917T140917Z` (`commit 63efd1f48a0c89473a165c5a96e51ae3725fa5a6`, `tree 20e2c32f5ef41a6c163635e0f6f66b2cf3f7fbd6`):
  - Salvaged / Reused: Ordinal reset hint parsing logic and initial retry loop sketches.
  - Rejected: Incomplete substantive work fencing and unisolated worktree mutations; reimplemented with strict closed schemas, substantive error fences, and bounded dynamic rerouting.
- Verification: Confirmed via `git merge-base --is-ancestor` that none of the recovery refs (`334027a5...`, `9f32a686...`, `63efd1f4...`) are ancestors of `main`, retaining them as unpublished operational evidence while preserving clean history from published APG150A (`a33765bf1609f53b8818b6835aa9dbfd8fd8f5e0`).
