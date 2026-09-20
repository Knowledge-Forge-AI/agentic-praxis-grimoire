# ADR 0067 — Provider Failure Feedback, SQLite Schema v2, and Bounded Dynamic Reroute

- Status: Accepted
- Date: 2026-09-17
- Phase: APG150B (Roadmap Stage: V0120-E-HARDEN1)

## Context

During dogfood validation of Request V2 multi-turn execution (Milestone V0120-E / APG150A), execution encountered a provider-confirmed hard usage-limit exhaustion (`429 / quota_exhausted`) from Codex. Because previous dynamic routing resolved routes only once per actor binding before launch and lacked feedback integration, this transient provider outage caused an immediate terminal phase abort despite capable fallback providers (such as Antigravity) being configured and eligible in the capabilities catalog.

To resolve this operational gap before starting Milestone V0120-F, Milestone V0120-E-HARDEN1 was chartered with the following requirements:
1. **High-Confidence Provider Classifier**: A deterministic, rule-based failure classifier that recognizes provider quota exhaustion and error signatures without speculative or noisy heuristics.
2. **Sanitized Evidence**: Strict extraction of machine-readable error reasons and ordinal reset timestamps (preserving timezone offset provenance) while redacting credentials, tokens, prompts, and confidential output.
3. **SQLite Persistence Schema v2**: An additive migration introducing `invocation_observation_relations` to durably link failed invocation attempts with generated observations, ensuring idempotent recording and duplicate digest conflict detection.
4. **Bounded Dynamic Rerouting ($M=3$)**: Per-binding retry capability bounded by $\min(3, \text{distinct capable routes})$.
5. **Substantive Work Fence**: Retries are permitted only when an attempt fails prior to producing substantive work (unmutated worktree and empty stdout). Any non-zero exit code following substantive modification is strictly terminal to avoid candidate corruption.
6. **Artifact Emission**: Structured recording of `apgr-provider-failure-v1` and `apgr-route-decision-v1` artifacts in the canonical run directory and SQLite.
7. **Cross-Language Conformance**: Preservation of the cross-language golden vector test corpus and absolute signature/digest parity between Python and Go.

## Decision

### 1. High-Confidence Failure Classification (`failure_classifier.py`)
APGR implements a dedicated, non-intrusive failure classifier:
- Matches the captured high-confidence provider quota failure signature from Codex (`You've hit your usage limit. Visit https://chatgpt.com/codex/settings/usage...`), assigning `CONFIDENCE_EXACT` and authorizing dynamic rerouting. Unverified provider error patterns (generic HTTP 429 status codes, heuristic rate limit or token limit messages) remain unpersisted heuristics with non-reroutable status per Requirement B.
- Parses reset times into absolute Unix timestamps while strictly preserving host-local timezone provenance.
- Unverified, ambiguous, or generic non-zero exit codes are classified as non-reroutable, preventing spurious fallback transitions on logic errors.
- Sanitizes all captured error excerpts to eliminate sensitive tokens, file paths, or private prompts.

### 2. SQLite Schema v2 & Durable Relations (`persistence_feedback.py`)
APGR establishes SQLite Schema v2:
- Migration table `invocation_observation_relations` with composite primary key `(attempt_id, observation_id)` and timestamp tracking.
- Idempotent observation recording with SHA-256 digest validation: duplicate observation IDs with identical digests succeed as no-ops; conflicting digests raise deterministic persistence errors.
- Dynamic query functions (`get_active_operational_observations`) filter durable observations by `expires_at > now`, enabling persisted provider state to seamlessly survive dispatcher crashes and resume attempts.

### 3. Bounded Dynamic Retries ($M=3$) and Semantic Role Lifecycle
- Each actor binding is permitted up to $M = \min(3, \text{distinct eligible routes})$ invocation attempts.
- When an attempt fails with a reroutable classification and zero substantive work:
  1. The failed attempt is updated to `status = "failed"`.
  2. The generated observation is recorded in SQLite and linked via `invocation_observation_relations`.
  3. The associated semantic responsibilities transition to `status = "retry_pending"`.
  4. The router re-evaluates eligible routes against the updated observation set.
  5. If an alternative capable route exists, semantic responsibilities transition to `status = "running"` and attempt $N+1$ executes under verified predecessor lineage (`predecessor_attempt_id`).
  6. If no eligible routes remain or the retry ceiling is reached, semantic responsibilities fail closed with `status = "failed"` and the run halts.

### 4. Substantive Work Integrity Boundary
To preserve workspace consistency:
- An attempt is marked as having produced substantive work if `tree_after != tree_before` OR `stdout_bytes.strip()` is non-empty UNLESS stdout strictly consists of the recognized Codex usage-limit banner (`is_recognized_codex_quota_banner_only`).
- A failed attempt with substantive work is classified as non-reroutable (`SubstantiveFailureError`). Dynamic rerouting is refused, and repository finalization treats the failure as terminal to protect operator work. Furthermore, per Scope B / HIGH-1, substantive agent prose on stdout quoting quota text cannot forge durable provider-wide exclusions; observation persistence is strictly gated on `not substantive`.
- **Evidence & Substantive Interaction (Requirement G)**: If a provider emits error/usage-limit text on stderr, or solely the recognized usage-limit banner on stdout while exiting non-zero without tree modifications or agent prose, the failure is pre-substantive and eligible for automatic dynamic rerouting.

### 5. Standardized Artifact Emission & Closed Schemas
- Every turn failure records an `apgr-provider-failure-v1` JSON artifact conforming to a pinned, validated closed schema containing binding/attempt identity, exit code, classification category, confidence, match basis, sanitized excerpt, stdout/stderr digests, observation IDs, observation digests, observation expirations, reset hint, parsed reset timestamp, timezone provenance, substantive boundary facts, observed_at, and retry decision.
- Every route resolution records an `apgr-route-decision-v1` JSON artifact conforming to a pinned, validated closed schema recording the chosen provider/profile/endpoint, selection rationale, active observation IDs, and rejections with explicit elimination rationales.

### 6. Golden Corpus Conformance & Cross-Language Parity
- Conformance corpus `dynamic_routing_scenarios.json` is expanded with 7 feedback scenarios, including profile-scoped exclusion, active observation pruning, deterministic fallback, and scenario-time expiration filtering.
- Both Python (`test_cross_language_conformance.py`) and Go (`routing_test.go`) suites validate against the exact same scenarios with 100% agreement.

### 7. Generic JSON/JSONC Syntax Parsing vs. Semantic Interpretation (FINAL3 Amendment)
- Generic agent JSON syntax validation is strictly decoupled from semantic interpretation. At the generic syntax layer, any syntactically valid JSON value supported by the shared parser is accepted: object, array, string, number, boolean, or null.
- Standard JSONC comments (line and block) and trailing commas are accepted where the shared grammar supports them across stage results (`result.py`, `review_result.py`, and `test_agent_phase_jsonc_results.py`).
- Valid JSON is never classified as "invalid JSON" solely because its root kind, additional fields, or example shape differ from expected schema layouts. Root-shape policing is eliminated: non-object roots, extra fields, or omitted example fields are accepted at the syntax layer.
- Real syntax and security boundaries are strictly preserved: fence and nonce integrity where applicable, UTF-8 validity, payload bounds, malformed syntax rejection, and genuine duplicate-key ambiguity checks.
- Downstream semantic adapters evaluate domain requirements and consume only recognized semantic facts actually present. If completion semantics are absent or unrecognized, the stage result is truthfully represented as semantically blocked/unavailable rather than throwing a JSON syntax or shape error. If review semantics are absent or unrecognized, review results evaluate to `unreviewable` with a bounded explanation. Semantic incompleteness is treated as blocked or unreviewable, not JSON-invalid.
- APG150B FINAL3 provides this narrow parser and semantic-adapter amendment to APG150B while Agent-Central remains an active, supported reference implementation.

### 8. V2 Outbox Topology Alignment with Agent-Central Reference Doctrine
- **Agent-Central Reference Doctrine**: Agent-Central (`~/projs/agent-central`) remains an active, supported dispatcher reference implementation and is NOT being decommissioned. APGR now owns and evolves its copy without immediate Agent-Central decommissioning. APGR improves upon that implementation but preserves reference behavior by default; divergences must be deliberate, documented, and tested.
- **Outbox Topology**: APGR V2 operator outbox projections are aligned with the visible layout of current Agent-Central:
  ```text
  <outbox_root>/<project>/<phase-id>/
    <phase-id>-dispatch--<timestamp>        -> canonical run directory
    <phase-id>-dispatch--<timestamp>.zip    -> canonical archive
    <phase-id>-dispatch--<timestamp>.locator.json (atomic regular file)
  ```
  The redundant `<outbox_root>/phase-dispatch/` prefix is eliminated for new APGR V2 projections, matching Go `internal/response/filesystem.go:102`.
- Canonical APGR V2 state remains authoritative under `<APGR_HOME>/state`. Historical old-layout projections remain preserved and untouched. Premature or failed V2 runs reliably project truthful canonical evidence, sealed archives, and operator locators.

### 9. Publication Accounting and Milestone Boundaries
- **Joint Publication Accounting**: A prior solo finalization partially published APG150B as commit `0670d497d9f3a4c0e56ec8291c07babe693ce5ab` (modifying only `docs/status/README.md`) due to an operator recovery script dirty-path collection defect on macOS. The subsequent FINAL2 commit publishes the remaining 28 adopted candidate paths as its direct descendant, jointly constituting the full publication of APG150B.
- Local recovery refs (`refs/apgr/recovery/apg150b-final2-20260917T231817Z`, etc.) are retained as unpublished operational evidence and verified to not be ancestors of `main`.
- **Milestone Boundary**: Milestone V0120-E-HARDEN1 is completed. FINAL3 is the narrow parser and semantic-adapter amendment to APG150B. Milestone V0120-F does not duplicate the Codex provider-result feedback work completed here and remains confirmed as NOT STARTED until this exit is formally accepted.

## Consequences

### Positive
- Resilience against provider rate limits and quota resets without operator intervention.
- Fail-closed isolation ensuring code changes are never overwritten by secondary providers.
- Complete auditability of routing decisions and failure causes through SQLite and disk artifacts.
- Decoupled JSON syntax parsing preventing spurious rejection of syntactically valid model outputs.
- Direct outbox layout parity with Agent-Central reference dispatcher for operator tooling.
- Full backwards compatibility with existing SQLite databases and non-dynamic execution modes.

### Negative / Neutral
- SQLite database version advances to version 2 (automatically migrated on open).
- Multiple invocation attempts may be recorded per binding in the event of transient provider failure.
- Two consecutive Git commits jointly represent the APG150B publication.
