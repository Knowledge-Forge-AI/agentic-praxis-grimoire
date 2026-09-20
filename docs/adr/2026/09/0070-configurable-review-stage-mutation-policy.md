# ADR 0070 — Configurable Review-Stage Mutation Policy

- Status: Accepted (Amended under APG160 / V0130-B)
- Date: 2026-09-20
- Phase: APG160 (Roadmap Stage: V0130-B)

## Context

In the v0.12 architecture, ADR 0061 §4 ("Evidence vs Abortion") established the architectural principle that unexpected mutations during read-only review checkpoints should be captured, isolated, and emitted as typed diagnostic evidence rather than aggressively aborting the entire phase.

However, historical implementation diverged:
- In V1 lifecycle dispatch (`libexec/agent_phase/review_binding.py`), observed candidate or index drift raises `DispatchError(READ_ONLY_STAGE_MUTATED_*)`, marking the phase as blocked and aborting execution before parsing or saving review findings.
- In V2 turn coordination (`libexec/agent_phase/v2_turns.py`), `tree_after != tree_before` raises `V2TurnError`, failing to distinguish between worktree changes, staged index mutations, or HEAD movement.

This rigid behavior caused substantive review findings (such as extensive plan critique or code review feedback) to be discarded entirely whenever an LLM reviewer inadvertently modified a file (e.g. adding a scratch comment or applying an edit during review).

## Decision

### 1. Tri-State Review-Stage Mutation Policy
APGR adopts an operator-configurable policy controlling review-stage mutations:

```toml
schema = "agent-phase-policy-v1"

[review_mutation]
worktree = "warn"  # block | warn | allow
index = "block"    # block only in v0.13
head = "block"     # block only in v0.13
```

- **Mode Semantics for `worktree`**:
  - `block`: Fails the review stage immediately upon observing any working tree file additions, modifications, or deletions. Discards checkpoint and halts execution.
  - `warn` (Shipped Default): Preserves immutable review subject binding, parses review findings against the original subject, captures drift observations as typed evidence, emits downstream warning notices, and requires closer-side disposition of surviving paths.
  - `allow`: Changes ownership handling so surviving reviewer edits proceed into finalization without error, but **never** confers review authority or mints freshness.
- **Fail-Closed Git Authority**: `index` and `head` drift remain strictly `block` in v0.13 across all worktree modes. Modifying the Git index or moving HEAD during a read-only review turn represents unauthorized Git execution authority and is unconditionally rejected with distinct diagnostic codes: `READ_ONLY_STAGE_MUTATED_INDEX` and `READ_ONLY_STAGE_MUTATED_HEAD`.

### 2. Observation Capture, Freshness Restoration, and Ownership
1. **Immutable Review Subject**: The original review subject binding (`immutable_review_bindings[stage]`) is immutable. Review findings are parsed against the original bound subject tree.
2. **Distinct Observation Capture**: Drift is captured as `review_mutation_observations[stage]` under schema `agent-phase-review-mutation-observation-v1`. It is NOT recorded as an abort.
3. **Truthful Freshness and Restoration**:
   - A warned or allowed mutation invalidates immediate freshness: `subject_drift_observed = true`.
   - Neither a closer's ownership disposition nor worktree `allow` constitutes independent review or mints freshness.
   - However, earlier warning history does **not** permanently poison candidate freshness. A subsequent valid independent review stage bound to the exact final candidate tree (`candidate_tree == terminal_tree`) **restores** `final_candidate_reviewed = true`.
   - If no eligible exact-final review exists, freshness remains `false`.
4. **Exact-Subject Work Review Eligibility & Verified Structured Receipts (M1)**:
   Freshness restoration cannot be established by agent assertions or by a plan review of a plan artifact (even if repository trees match). A review certifies only its actual subject kind and exact identity. Work freshness is derived strictly from verified structured receipts verifying:
   - **Role Authority**: The reviewing actor executed under an authorized independent work review role (`Work Review` / `work_reviewer`, or V1 `work_review` / `final_review`), distinct from producer or closer.
   - **Exact Work Subject Identity**: The reviewed candidate tree SHA matches the final terminal tree SHA (`candidate_tree == terminal_tree`).
   - **Zero Drift**: Zero worktree, index, or HEAD drift occurred during that qualifying review turn (`drift_observed = false`).
   - **Verified Structured Receipt**: A valid structured review result artifact exists and is verified using runtime-controlled integrity checks (zero PKI, external brokers, or cryptographic signing services).
5. **Closer Disposition Scope**: Paths changed during the review window that survive to finalization under `warn` are dispositioned by the delegated closer within scope (`phase_owned`, `exclude_unrelated`, `exclude_environment`). Manager attention is reserved for ambiguous authority or out-of-scope paths. No indiscriminate new mandatory review loop is authorized.

### 3. Malformed Review Output Behavior
Observation capture and review response parsing are independent operations:
- If a reviewer mutates the worktree and outputs a malformed or unparseable response, drift observations and raw reviewer output (stdout/stderr) are still captured and preserved in stage artifacts.
- The stage fails with a malformed review error, but raw evidence and drift observations remain recorded for auditing and recovery.

### 4. Policy Precedence and Configuration Provenance
The policy is resolved through the standard four-tier hierarchy:
CLI flag (`--review-mutation-worktree`) > Project config (`.apgr/config.toml`) > Global config (`<APGR_HOME>/config.toml`) > Tracked default (`common/dispatcher/policy.toml`).
Resolution provenance is immutably recorded in `ConfigurationProvenance`.

### 5. Resume Semantics
Resuming an interrupted run preserves completed-stage observations. Current policy applies to unperformed suffix stages with an explicit `policy_transition` record. Historical observations are never rewritten retroactively.

## Consequences

- Substantive review feedback is preserved and utilized even if a reviewer produces extraneous worktree modifications.
- Git index and HEAD integrity remain strictly fail-closed.
- Review freshness claims remain completely truthful; fresh independent reviews can certify final candidate trees without permanent poisoning from earlier stages.
- Closer-side accountability is enforced for any surviving reviewer changes before final commit.
