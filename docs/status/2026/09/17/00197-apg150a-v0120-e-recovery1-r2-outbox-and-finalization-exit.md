# APG150A — APGR V0120-E-RECOVERY1-R2 — Request V2 Outbox Projection and Truthful Operational Finalization Exit

Phase ID: `APG150A`
Exit ID: `Exit 00197`

## Status

Disposition: **advance**. Exit 00197 records the successful completion and operational recovery of Request V2 outbox projection, locator truth, and truthful repository finalization under Milestone V0120-E-RECOVERY1-R2. Canonical state remains strictly confined to `<APGR_HOME>/state/`, outbox symlinks serve exclusively as operator navigation and are rejected as resume authority, two-tier archive SHA-256 digests seal post-archive identity truth, and operational finalization (`checkpoint`, `commit-local`, `publish`) enforces exact Git facts with fail-closed security.
Outcome: `V0120_E_RECOVERED_WITH_OUTBOX_AND_TRUTHFUL_FINALIZATION`

## Accomplishments

### 1. Outbox Projection Engine & Atomic Locator Metadata
Implemented `libexec/agent_phase/outbox_projection.py` providing safe, collision-resistant projection of canonical V2 execution runs into operator outbox topologies:
- Topology: `<outbox_root>/phase-dispatch/<project>/<phase-id>/` containing:
  - `<leaf>` -> Symlink to canonical `<APGR_HOME>/state/runs/<run_id>`
  - `<leaf>.zip` -> Symlink to canonical `<APGR_HOME>/state/runs/<run_id>.zip`
  - `<leaf>.locator.json` -> Atomic regular JSON file with schema `agent-phase-dispatch-locator-v1`.
- Safe component validation, parent symlink traversal rejection (`validate_no_symlink_parents`), and collision refusal (no-clobber protection against existing links or locator files).
- Preserves canonical state untouched on any projection failure.
- Scalar root resolution ladder: explicit CLI `--outbox-root` -> `AGENT_PHASE_RUN_ROOT` environment variable -> project TOML configuration -> global TOML configuration -> built-in default (`~/Documents/agent/outbox`).

### 2. Strict Boundary: Outbox Symlinks Rejected as Resume Authority
- Enforced invariant that machine authority remains strictly canonical under `<APGR_HOME>/state/`.
- Outbox symlinks are navigation pointers only; updated `libexec/agent_phase/cli.py` to strictly reject `--resume` or `--continue-from` targets that are symlinks, failing closed with exit code 2 and explicit error messaging.

### 3. Strict Closeout Output Contract & Truthful Git Finalization
- Closeout prompt (`v2_prompts.py`) embeds the required nonce and `TERMINAL_RESULT_CONTRACT`.
- Closeout execution in `v2_turns.py` strictly parses Turn 5 output using `result_module.parse(stdout_bytes, "closeout", nonce)`. Fails closed if fences are missing, duplicated, or unordered, or if closeout outcome is not `completed`.
- Operational finalization in `v2_dispatch.py` wires `finalization_module.finalize_repository` with a `_RunDirectoryAdapter`:
  - `checkpoint`: Generates `checkpoint-candidate.patch` and `checkpoint-candidate-manifest.json` in the canonical run directory without advancing Git HEAD or creating a commit.
  - `commit-local`: Creates a local Git commit with the parsed closeout commit message without pushing to any remote.
  - `publish`: Creates the Git commit and pushes to the bare remote origin, recording exact remote readback (`post_push_remote_head`).
  - `finalized_empty_delta`: Clean worktrees with `commit_message: null` complete with `finalization_status = "completed"` without fabricating empty commits.
  - Fail-closed entry dirt overlap: Unadopted dirty entry files modified by the run trigger manager attention and fail closed with `status = "failed"`.
  - Entry adoption: Explicit adoption receipts via `--entry-adoption` permit approved pre-existing worktree changes to be cleanly incorporated and finalized.

### 4. Two-Tier Archive Digest Sealing
- Resolved archive digest circularity:
  - In-archive `result.json` records `archive_sha256: null` / `pending_sealing`.
  - Run directory is sealed into `<run_id>.zip`.
  - Dispatcher computes post-sealing SHA-256 of the binary archive and embeds it in the on-disk `result.json` and outbox `<leaf>.locator.json`.

### 5. Qualification and Verification
- **New Test Suites**:
  - `src/test/dispatcher/test_agent_phase_v2_outbox_projection.py`: 12 deterministic tests covering topology, symlinks, collision refusal, hostile parents, archive digests, project/global TOML overrides, CLI `--outbox-root`, and CLI resume symlink rejection.
  - `src/test/dispatcher/test_agent_phase_v2_finalization.py`: 12 comprehensive tests covering `checkpoint`, `commit-local`, `publish`, publish failure, empty delta, unrelated dirt overlap (checkpoint, commit-local, and publish variants), preserved unrelated entry dirt, entry adoption, exact remote readback, and no-false-completed status.
- **Dispatcher Regression Matrix**: All dispatcher tests passed (100% green).
- **Go Surfaces & Conformance**: All Go packages passed `go test ./...` and `go vet ./...` (including JACA and XO consumer qualification fixtures).
- **Repository Integrity Gates**:
  - `bin/apg-check-record-identity`: Pass (66 ADRs, 195 exits, next exit 00198).
  - `bin/apg-check-roadmap-closure`: Pass (55/55 closed).
  - `tools/ci/file_length_policy.py`: Pass (all files within limits, all new files < 400 lines).
  - `tools/ci/check_generated_drift.py`: Pass.
  - `tools/ci/prompt_defense_check.py`: Score 100/100.
  - `tools/ci/pre_review_checks.py`: Pass.

### 6. Dogfood Item Disposition & Milestone Boundary
- **Explicit Confirmation — V0120-F Not Begun**: Confirmed that Milestone V0120-F has not been started. Zero V0120-F scope, code, or packaging changes are present in this recovery milestone.
- **Codex Usage-Limit Exhaustion Dogfood Item**: The provider-confirmed hard usage-limit exhaustion encountered during dogfood is explicitly carried as a post-recovery, pre-F hardening item under V0120-F. It will safely encode provider-result-derived temporary quota exhaustion handling within dynamic routing/adapter state machines without widening phase scope or scraping provider credentials/private storage.
- Next milestone: **V0120-F** (Release Hardening, Conditional Nixpkgs, and Integrated Readiness).
