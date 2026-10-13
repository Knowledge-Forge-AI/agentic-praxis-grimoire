# Specification: Review-Stage Mutation Seam Inventory and Semantic Interpretation

- **Status**: Authoritative Technical Specification
- **Version**: 1.2.0 (exact-subject work review eligibility, verified structured receipts, and attribution-free closer disposition amended under APG160 / V0130-B)
- **Governing ADR**: [ADR 0070](../adr/2026/09/0070-configurable-review-stage-mutation-policy.md)
- **Phase**: APG160 (Milestone V0130-B)

---

## 1. Executive Summary

This specification provides a source-backed technical inventory of all drift detection and validation seams across the V1 lifecycle runtime and V2 multi-turn execution coordinator. It defines the unified drift observer, specifies the distinct HEAD movement code, details closer-owned path disposition rules, and analyzes the semantic interpretation risks of reviewer worktree mutations.

---

## 2. Source Seam Inventory

Drift verification occurs across four review/retry seams in the APGR codebase. A fifth, adjacent guard is listed for completeness because it was previously misdescribed as a drift seam:

| Seam ID | Source Location | Current Inspection Behavior | Unified v0.13 Behavior |
|---|---|---|---|
| **S1: V1 Stage Verify** | `libexec/agent_phase/review_binding.py:90-127` | Compares `after == before` and `observed_index == binding["index"]`. Raises `DispatchError` with `READ_ONLY_STAGE_MUTATED_CANDIDATE` or `READ_ONLY_STAGE_MUTATED_INDEX`. Conflates HEAD drift with candidate drift. | Calls unified `observe_review_drift()`. Routes through `apply_review_mutation_policy()`. Under `warn`, records observation, preserves result, sets `subject_drift_observed = true`. |
| **S2: V2 Turn Verify** | `libexec/agent_phase/v2_turns.py:472-493` | Compares only `tree_after != tree_before`. Raises `V2TurnError`. Does not inspect index identity or HEAD commit. | Captures full candidate, index, and HEAD before/after identities. Calls unified `observe_review_drift()` and applies configured policy identically to V1. |
| **S3: Lifecycle Strict Guard** | `libexec/agent_phase/lifecycle_dispatch.py:325-341` | Strict mode check asserting unchanged working tree before parsing or resuming. | Integrates with `observe_review_drift()` to honor configured worktree policy while keeping index/HEAD strictly fail-closed. |
| **S4: Review Recovery Guard** | `libexec/agent_phase/review_recovery.py:65-70` | Prevents second parsing retry if worktree changed during attempt 1. | Preserves retry boundary; retry allowed only if worktree drift is accounted for under policy. |
| **S5 (adjacent, not a drift seam): Repair Working-Directory Guard** | `libexec/agent_phase/v2_repair.py:120-145` | Guards the auxiliary result-repair working directory: records a `result-repair-cwd.json` inventory artifact and raises `FinalizationError("RESULT_REPAIR_WORKDIR_UNSAFE")` when that directory is non-empty or repository-attached. It does **not** compare reviewed-tree identities and does not validate that repair turns leave reviewed code unmutated. | Unchanged. The Turn 5 repair runs in a repository-detached temporary directory, so reviewed-subject drift is structurally prevented rather than observed. No `observe_review_drift()` integration is required; V0130-B must not count this guard as an observation site. |

---

## 3. Dedicated Git Authority Codes

To resolve Discrepancy D7 (conflation of candidate and HEAD drift), v0.13 defines distinct fail-closed codes:

1. `READ_ONLY_STAGE_MUTATED_CANDIDATE` — Working tree file additions, modifications, or deletions observed. Under `worktree = "warn"`, triggers observation capture rather than abort.
2. `READ_ONLY_STAGE_MUTATED_INDEX` — Staged changes in the Git index observed. Always aborts under `index = "block"`.
3. `READ_ONLY_STAGE_MUTATED_HEAD` — Git HEAD ref or commit hash changed during read-only stage. Always aborts under `head = "block"`.

---

## 4. Semantic Interpretation and Subject Invalidation Analysis

### 4.1 The Semantic Interpretation Question
When an LLM reviewer mutates files during a review turn, does the review remain semantically valid?

**Analysis**:
- If an agent performs edits while reviewing (e.g. attempting to fix a bug it noticed, or leaving commentary inline), its structured review response (the critique, score, and recommendations) may refer to the **modified** bytes rather than the **original** candidate tree.
- If the downstream producer or closer interprets the review text as applying strictly to the original candidate, semantic mismatches can occur (e.g. line number offsets, references to code that exists only in the reviewer's uncommitted edit).

### 4.2 Architectural Resolution
To preserve substantive critique without corrupting Git truth or semantic integrity:
1. **Original Subject Stays Immutable**: The original candidate tree identity and subject binding remain frozen. APGR never updates the subject binding to point to the reviewer's drifted tree.
2. **Flagging Subject Drift**: The review result record records `subject_drift_observed = true`.
3. **Truthful Freshness and Restoration**:
   - A warned or allowed mutation invalidates initial candidate freshness (`subject_drift_observed = true`). Closer disposition is ownership handling, not independent review, and does not mint freshness.
   - If no eligible exact-final review exists, `final_candidate_reviewed` remains `false`.
   - However, earlier warning history does **not** permanently poison freshness: a subsequent valid independent review stage bound to the exact final candidate tree (`candidate_tree == terminal_tree`) **restores** `final_candidate_reviewed = true`.
4. **Exact-Subject Work Review Eligibility & Verified Structured Receipts (M1)**:
   Freshness restoration cannot be established by agent assertions or by a plan review of a plan artifact (even if repository trees match). A review certifies only its actual subject kind and exact identity. Work freshness is derived strictly from verified structured receipts verifying:
   - **Role Authority**: Independent work review role (`Work Review` / `work_reviewer`, or V1 `work_review` / `final_review`), distinct from producer or closer.
   - **Exact Work Subject Identity**: Candidate tree matches final terminal tree (`candidate_tree == terminal_tree`).
   - **Zero Drift**: Zero worktree, index, or HEAD drift during that qualifying review turn.
   - **Verified Structured Receipt**: Valid structured review result artifact verified using runtime-controlled integrity checks (zero PKI, external brokers, or cryptographic signing services).
5. **Bounded Downstream Prompting**: The producer/closer stage prompt receives an explicit warning section:
   ```text
   [WARNING: REVIEWER MUTATIONS OBSERVED]
   The preceding review stage produced irregular file mutations across N paths:
     - path/to/file.py
   These mutations carry ZERO review or implementation authority.
   If any of these changes survive into the final delta, you must explicitly disposition them.
   ```

### 4.3 Read-Only Sample of Retained REVIEWIMMUT1 Invalidation Evidence

The task required sampling existing retained invalidation evidence to test whether reviewer edits are load-bearing for the review text. Sample performed 2026-09-20, read-only, against the operator outbox root on the execution host.

- **Bound**: the first 20 `state.json` / `result.json` files (by search order) containing the key `review_binding_invalidations`. The unbounded search returned only 2 `state.json` matches across the whole outbox root, so the bound was not binding in practice.
- **Result**: 18 of 20 files carry an empty `review_binding_invalidations` map. 2 files (one run's `state.json` and its `result.json`) carry the same single invalidation record: stage `final_review`, code `READ_ONLY_STAGE_MUTATED_CANDIDATE`, 5 changed worktree paths, `paths_complete = true`, no index paths, transport `ok = true`, exit code 0. The run belongs to an external private project; its paths and identifiers are deliberately not reproduced here.
- **Semantic-drift question**: unanswerable from retained evidence. The invalidated `final_review` stage retained only its scan, meta, stderr, and worker-drain artifacts; **no review result body or stdout for the invalidated stage was retained**, so whether the reviewer's findings referred to the edited bytes cannot be determined. (The run's earlier, valid `plan_review` result mentions three of the five later-edited path basenames, but that stage predates the edits and is not evidence about the invalidated review.)
- **Consequence for V0130-B**: under `block`, the current runtime discards the review response along with the checkpoint, which is exactly why the question cannot be answered retrospectively. Under `warn`, ADR 0070 already requires the original result and observation to be retained even when the response is malformed. V0130-B must additionally retain the reviewer's raw response artifact for every observed-drift stage, whatever the policy, so that the load-bearing question in §4.1 becomes answerable from the next sample. Until at least several such records exist, the "load-bearing edits are rare" premise behind parsing against the original subject remains an assumption, and `subject_drift_observed = true` must be exposed downstream as stated in §4.2.

---

## 5. Closer-Owned Path Disposition Rules

Under `worktree = "warn"`, paths changed during the review window that survive to finalization do not inherit ordinary implementation ownership:

1. **Explicit Terminal Disposition**: At finalization (`libexec/agent_phase/finalization.py`), every surviving modified, added, or deleted path originating from a review turn must be explicitly claimed by the closer under the `path_dispositions` vocabulary:
   - `phase_owned` — The closer explicitly adopts the edit as part of the phase deliverable.
   - `exclude_unrelated` — The path is excluded from staging as unrelated operator or environment dirt.
   - `exclude_environment` — The path is excluded as host-specific environment artifact.
   - Or reverted entirely before finalization.
2. **Closer Scope vs Manager Escalation**: Delegated closers disposition surviving paths within delegated phase scope. Escalation to manager attention (`record_manager_attention(reason="review_mutation_disposition_required")`) is reserved for ambiguous authority, out-of-scope paths, or policy conflicts, not every harmless edit. No indiscriminate new mandatory review loop is authorized.

---

## 6. Resume and Transition Boundaries

When resuming an interrupted run (`agent-phase-resume`):
- Completed stages retain their historical `review_mutation_observations` as immutable evidence.
- Unperformed suffix stages resolve the current active policy.
- If the active policy differs from the original run's policy, an explicit `policy_transition` record is persisted in SQLite `configuration_provenance`.
- Resume never retroactively converts a previously blocked stage into an accepted stage.
