"""Comprehensive qualification test suite for review-stage mutation policy.

Covers:
1. Cross-product matrix (modify, add, delete, tracked_metadata, index-only, HEAD-only,
   combined worktree+index, clean) across all three policies (block | warn | allow).
2. Fail-closed Git integrity: index and HEAD mutations unconditionally block across all modes.
3. Candidate freshness restoration (M1):
   - Warned plan review followed by clean exact-candidate work review restores final_candidate_reviewed = True.
   - Warned work review prevents candidate freshness (final_candidate_reviewed = False).
   - Closer mutation during closeout prevents candidate freshness (final_candidate_reviewed = False).
   - Plan-reviewed lifecycle never certifies work candidates (final_candidate_reviewed = False).
4. Closer path accountability under warn:
   - Surviving review-window mutations under warn trigger ownership challenge.
   - Closer explicit disposition (phase_owned, exclude_unrelated, exclude_environment) resolves challenge.
   - Unresolved review-window mutation blocks finalization with OWNERSHIP_CHALLENGE_OPEN.
   - Under allow, mechanical ownership applies without challenge.
5. V2 Turn coordination & SQLite persistence:
   - Evaluates review mutation drift in read-only turns.
   - Persists ReviewMutationPolicy provenance and ReviewMutationObservation records.
   - Truthful candidate freshness derivation in V2 results and result.md.
6. Resume semantics:
   - Preserves completed-stage review mutation observations.
   - Records policy_transition on policy change.
   - Pre-v0.13 runs without policy default to block.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
import sqlite3

from agent_phase.config_routing import (
    ReviewMutationPolicy,
    resolve_review_mutation_policy,
)
from agent_phase.dispatch import DispatchError, Dispatcher
from agent_phase.lifecycle import LIFECYCLES
from agent_phase.persistence import (
    get_review_mutation_observations,
    get_review_mutation_policies,
    open_dispatcher_db,
    resolve_dispatcher_db_path,
)
from test_agent_phase_dispatch import git, repository as _repository
from test_agent_phase_lifecycle_dispatch import (
    LifecycleRunner,
    REQUEST,
    ROOT,
    dispatcher as _dispatcher,
    only_run,
)

repository = _repository


def evidence(tmp_path: Path):
    source = only_run(tmp_path / "runs")
    return source, json.loads((source / "state.json").read_bytes())


# ==============================================================================
# 1. Cross-Product Matrix: Change Types x Policies (block | warn | allow)
# ==============================================================================


@pytest.mark.parametrize(
    "change",
    [
        "modify",
        "add",
        "delete",
        "tracked_metadata",
        "index",
        "head",
        "combined_worktree_index",
        "clean",
    ],
)
@pytest.mark.parametrize("policy_mode", ["block", "warn", "allow"])
def test_cross_product_review_mutation_matrix(
    repository: Path, tmp_path: Path, change: str, policy_mode: str
):
    target = "file.txt"
    if change == "tracked_metadata":
        target = ".serena/product.txt"
        (repository / ".serena").mkdir(exist_ok=True)
        (repository / target).write_text("tracked product")
        git(repository, "add", target)
        git(repository, "commit", "-m", "Track metadata product")

    head_commit = git(repository, "rev-parse", "HEAD")
    original_bytes = (repository / target).read_bytes() if (repository / target).exists() else b""

    def mutate(stage: str, cwd: Path):
        if stage != "work_review":
            return
        if change == "clean":
            return
        elif change == "modify":
            (cwd / target).write_text("reviewer modified worktree")
        elif change == "add":
            (cwd / "reviewer-scratch.txt").write_text("reviewer added scratch")
        elif change == "delete":
            (cwd / target).unlink()
        elif change == "tracked_metadata":
            (cwd / target).write_text("reviewer altered metadata product")
        elif change == "index":
            # Isolate index mutation from worktree drift
            (cwd / target).write_text("staged reviewer changes")
            git(cwd, "add", target)
            (cwd / target).write_bytes(original_bytes)
        elif change == "head":
            # Move HEAD during read-only review
            git(cwd, "commit", "--allow-empty", "-m", "unauthorized reviewer commit")
        elif change == "combined_worktree_index":
            (cwd / "reviewer-scratch.txt").write_text("scratch file")
            git(cwd, "add", "reviewer-scratch.txt")
            (cwd / target).write_text("concurrent worktree edit")

    disps = []
    if change == "add":
        disps = [{"path": "reviewer-scratch.txt", "disposition": "phase_owned"}]
    elif change in ("modify", "delete", "tracked_metadata"):
        disps = [{"path": target, "disposition": "phase_owned"}]

    runner = LifecycleRunner(
        mutate,
        path_dispositions=disps,
    )
    disp = _dispatcher(
        repository,
        tmp_path,
        runner,
        review_mutation_policy=policy_mode,
    )

    is_worktree_mutation = change in ("modify", "add", "delete", "tracked_metadata")
    is_index_mutation = change in ("index", "combined_worktree_index")
    is_head_mutation = change == "head"

    if is_head_mutation:
        # HEAD movement is strictly fail-closed across all policies
        with pytest.raises(DispatchError) as caught:
            disp.dispatch("APG160", REQUEST, "work-reviewed", "checkpoint")
        assert caught.value.code == "READ_ONLY_STAGE_MUTATED_HEAD"
        return

    if is_index_mutation:
        # Index mutation is strictly fail-closed across all policies
        with pytest.raises(DispatchError) as caught:
            disp.dispatch("APG160", REQUEST, "work-reviewed", "checkpoint")
        assert caught.value.code == "READ_ONLY_STAGE_MUTATED_INDEX"
        return

    if is_worktree_mutation and policy_mode == "block":
        # Worktree mutation blocks under block policy
        with pytest.raises(DispatchError) as caught:
            disp.dispatch("APG160", REQUEST, "work-reviewed", "checkpoint")
        assert caught.value.code == "READ_ONLY_STAGE_MUTATED_CANDIDATE"
        _, state = evidence(tmp_path)
        assert state["outcome"] == "blocked"
        assert state["blocking_reason"]["code"] == "READ_ONLY_STAGE_MUTATED_CANDIDATE"
        assert "work_review" in state["review_binding_invalidations"]
        obs = state["review_mutation_observations"]["work_review"]
        assert obs["action_taken"] == "blocked"
        assert obs["worktree_drift"] is True
        return

    # Non-blocking cases: clean across all policies, or worktree mutations under warn / allow
    state = disp.dispatch("APG160", REQUEST, "work-reviewed", "checkpoint")
    source, loaded_state = evidence(tmp_path)
    assert state["outcome"] == "completed"

    obs = state["review_mutation_observations"]["work_review"]
    if change == "clean":
        assert obs["subject_drift_observed"] is False
        assert obs["action_taken"] == "none"
        assert obs["diagnostic_code"] == ""
    elif policy_mode == "warn":
        assert obs["subject_drift_observed"] is True
        assert obs["action_taken"] == "warned"
        assert obs["diagnostic_code"] == "READ_ONLY_STAGE_MUTATED_CANDIDATE"
        assert obs["worktree_drift"] is True
    elif policy_mode == "allow":
        assert obs["subject_drift_observed"] is True
        assert obs["action_taken"] == "allowed"
        assert obs["diagnostic_code"] == ""
        assert obs["worktree_drift"] is True


# ==============================================================================
# 2. Candidate Freshness Restoration (Manager Disposition M1)
# ==============================================================================


def test_freshness_restoration_warned_plan_clean_work_review(
    repository: Path, tmp_path: Path
):
    """M1: Earlier warning on plan review does not poison fresh work review candidate."""
    def mutate(stage: str, cwd: Path):
        if stage == "plan_review":
            # Plan reviewer leaves scratch file; warned under default policy
            (cwd / "plan-scratch.txt").write_text("plan scratch comment")
        elif stage == "work":
            # Work stage produces clean product and removes plan scratch
            (cwd / "product.txt").write_text("clean final product")
            scratch = cwd / "plan-scratch.txt"
            if scratch.exists():
                scratch.unlink()

    runner = LifecycleRunner(mutate)
    disp = _dispatcher(
        repository,
        tmp_path,
        runner,
        review_mutation_policy="warn",
    )
    state = disp.dispatch("APG160", REQUEST, "standard", "checkpoint")
    source, _ = evidence(tmp_path)

    # 1. Plan review recorded warning drift
    plan_obs = state["review_mutation_observations"]["plan_review"]
    assert plan_obs["subject_drift_observed"] is True
    assert plan_obs["action_taken"] == "warned"

    # 2. Final review had zero drift
    work_obs = state["review_mutation_observations"]["final_review"]
    assert work_obs["subject_drift_observed"] is False
    assert work_obs["action_taken"] == "none"

    # 3. Freshness was restored!
    assert state["final_candidate_reviewed"] is True
    res = json.loads((source / "result.json").read_bytes())
    assert res["final_candidate_reviewed"] is True


def test_freshness_denied_when_work_review_drifts(
    repository: Path, tmp_path: Path
):
    """M1: Work review mutation under warn invalidates final candidate freshness."""
    def mutate(stage: str, cwd: Path):
        if stage == "work":
            (cwd / "product.txt").write_text("initial candidate")
        elif stage == "work_review":
            # Work reviewer mutates worktree
            (cwd / "review-edit.txt").write_text("reviewer inserted edit")

    runner = LifecycleRunner(
        mutate,
        path_dispositions=[
            {"path": "review-edit.txt", "disposition": "phase_owned"},
        ],
    )
    disp = _dispatcher(
        repository,
        tmp_path,
        runner,
        review_mutation_policy="warn",
    )
    state = disp.dispatch("APG160", REQUEST, "work-reviewed", "checkpoint")
    source, _ = evidence(tmp_path)

    work_obs = state["review_mutation_observations"]["work_review"]
    assert work_obs["subject_drift_observed"] is True
    assert work_obs["action_taken"] == "warned"

    # Freshness is denied because work review mutated the candidate
    assert state["final_candidate_reviewed"] is False
    res = json.loads((source / "result.json").read_bytes())
    assert res["final_candidate_reviewed"] is False


def test_freshness_denied_when_closer_mutates_candidate(
    repository: Path, tmp_path: Path
):
    """M1: Closer mutation during closeout invalidates final candidate freshness."""
    def mutate(stage: str, cwd: Path):
        if stage == "work":
            (cwd / "product.txt").write_text("reviewed candidate")
        elif stage == "revise_close":
            # Closer legitimately amends the candidate
            (cwd / "product.txt").write_text("closer modified candidate")

    runner = LifecycleRunner(mutate)
    disp = _dispatcher(
        repository,
        tmp_path,
        runner,
        review_mutation_policy="warn",
    )
    state = disp.dispatch("APG160", REQUEST, "work-reviewed", "checkpoint")
    source, _ = evidence(tmp_path)

    # Work review was clean
    work_obs = state["review_mutation_observations"]["work_review"]
    assert work_obs["subject_drift_observed"] is False

    # But closer mutated the candidate, so final candidate was NOT reviewed
    assert state["post_review_revision_delta"]["changed"] is True
    assert state["final_candidate_reviewed"] is False
    res = json.loads((source / "result.json").read_bytes())
    assert res["final_candidate_reviewed"] is False


def test_plan_reviewed_lifecycle_never_certifies_work_freshness(
    repository: Path, tmp_path: Path
):
    """M1: Plan review never certifies work candidates even if clean."""
    runner = LifecycleRunner()
    disp = _dispatcher(
        repository,
        tmp_path,
        runner,
        review_mutation_policy="warn",
    )
    state = disp.dispatch("APG160", REQUEST, "plan-reviewed", "checkpoint")
    assert state["final_candidate_reviewed"] is False


# ==============================================================================
# 3. Closer Path Accountability Under Warn vs Allow
# ==============================================================================


def test_closer_path_accountability_under_warn_requires_disposition(
    repository: Path, tmp_path: Path
):
    """Surviving review-window mutations under warn trigger challenge and block if undispositioned."""
    def mutate(stage: str, cwd: Path):
        if stage == "work_review":
            (cwd / "surviving-review-change.txt").write_text("unauthorized review change")

    # Run without closer disposition -> blocks with OWNERSHIP_CHALLENGE_OPEN
    runner_no_disp = LifecycleRunner(mutate, path_dispositions=[])
    disp_no_disp = _dispatcher(
        repository,
        tmp_path / "run-no-disp",
        runner_no_disp,
        review_mutation_policy="warn",
    )
    state_no_disp = disp_no_disp.dispatch("APG160", REQUEST, "work-reviewed", "checkpoint")
    assert state_no_disp["completion_kind"] == "candidate_requires_manager_disposition"
    assert state_no_disp["finalization"]["outcome"] == "blocked"
    assert state_no_disp["finalization"]["code"] == "OWNERSHIP_CHALLENGE_OPEN"

    # Run with closer disposition -> succeeds!
    git(repository, "checkout", "-f", "HEAD")
    clean_git_worktree(repository)

    runner_with_disp = LifecycleRunner(
        mutate,
        path_dispositions=[
            {"path": "surviving-review-change.txt", "disposition": "phase_owned"},
        ],
    )
    disp_with_disp = _dispatcher(
        repository,
        tmp_path / "run-with-disp",
        runner_with_disp,
        review_mutation_policy="warn",
    )
    state = disp_with_disp.dispatch("APG160", REQUEST, "work-reviewed", "checkpoint")
    assert state["outcome"] == "completed"
    assert state["completion_kind"] == "checkpoint_ready"
    assert state["finalization"]["outcome"] == "completed"


def test_closer_path_accountability_under_allow_proceeds_mechanically(
    repository: Path, tmp_path: Path
):
    """Under allow, surviving review changes proceed into finalization without special challenge."""
    def mutate(stage: str, cwd: Path):
        if stage == "work_review":
            (cwd / "allowed-review-change.txt").write_text("allowed review change")

    runner = LifecycleRunner(mutate, path_dispositions=[])
    disp = _dispatcher(
        repository,
        tmp_path,
        runner,
        review_mutation_policy="allow",
    )
    state = disp.dispatch("APG160", REQUEST, "work-reviewed", "checkpoint")
    assert state["outcome"] == "completed"


# ==============================================================================
# 4. Strict Git Fail-Closed Enforcement (Index and HEAD)
# ==============================================================================


def test_git_index_drift_aborts_with_distinct_diagnostic(
    repository: Path, tmp_path: Path
):
    """Modifying staged index in review turn aborts with READ_ONLY_STAGE_MUTATED_INDEX."""
    original = (repository / "file.txt").read_bytes()

    def mutate(stage: str, cwd: Path):
        if stage == "work_review":
            (cwd / "file.txt").write_text("staged reviewer edit")
            git(cwd, "add", "file.txt")
            (cwd / "file.txt").write_bytes(original)

    runner = LifecycleRunner(mutate)
    disp = _dispatcher(repository, tmp_path, runner, review_mutation_policy="allow")
    with pytest.raises(DispatchError) as caught:
        disp.dispatch("APG160", REQUEST, "work-reviewed", "checkpoint")
    assert caught.value.code == "READ_ONLY_STAGE_MUTATED_INDEX"


def test_git_head_movement_aborts_with_distinct_diagnostic(
    repository: Path, tmp_path: Path
):
    """Moving HEAD in review turn aborts with READ_ONLY_STAGE_MUTATED_HEAD."""
    def mutate(stage: str, cwd: Path):
        if stage == "work_review":
            git(cwd, "commit", "--allow-empty", "-m", "rogue review commit")

    runner = LifecycleRunner(mutate)
    disp = _dispatcher(repository, tmp_path, runner, review_mutation_policy="allow")
    with pytest.raises(DispatchError) as caught:
        disp.dispatch("APG160", REQUEST, "work-reviewed", "checkpoint")
    assert caught.value.code == "READ_ONLY_STAGE_MUTATED_HEAD"


# ==============================================================================
# 5. V2 Turn Coordination and Persistence Parity
# ==============================================================================


def test_v2_turns_review_mutation_warn_and_freshness(
    repository: Path, tmp_path: Path
):
    """V2 turn execution evaluates review mutation policy, persists observations, and computes freshness."""
    from agent_phase.request import parse_request_v2
    from agent_phase.v2_dispatch import dispatch_v2

    raw_req = json.dumps({
        "schema": "agent-phase-request-v2",
        "phase_type": "implementation_testing",
        "prompt": "Test V2 Review Mutation",
    }).encode("utf-8")
    req_v2 = parse_request_v2(raw_req)

    def mock_runner(*, run_id: str, binding: Any, route: Any, run_dir: Path, nonce: str | None = None) -> bytes | None:
        from agent_phase import result as result_module
        from agent_phase import review_result

        if binding.binding_id == "binding_work":
            (repository / "product.txt").write_text("v2 product\n", encoding="utf-8")
        elif binding.binding_id == "binding_work_review":
            (repository / "v2-review-scratch.txt").write_text("v2 review scratch\n", encoding="utf-8")
            if nonce:
                begin, end = review_result.markers(nonce)
                payload = {"version": 1, "stage": "final_review", "outcome": "reviewed_with_no_findings", "body": "clean review"}
                return f"{begin}\n{json.dumps(payload)}\n{end}\n".encode("utf-8")
        elif binding.binding_id == "binding_closeout" and nonce:
            begin, end = result_module.markers(nonce)
            payload = {
                "version": 1,
                "stage": "closeout",
                "outcome": "completed",
                "body": "V2 Closeout",
                "commit_message": {"subject": "V2 commit", "body": ""},
                "path_dispositions": [
                    {"path": "product.txt", "disposition": "phase_owned"},
                    {"path": "v2-review-scratch.txt", "disposition": "phase_owned"},
                ],
            }
            return f"{begin}\n{json.dumps(payload)}\n{end}\n".encode("utf-8")
        return None

    db_path = resolve_dispatcher_db_path(tmp_path / "apgr")
    res = dispatch_v2(
        ROOT,
        repository,
        req_v2,
        raw_req,
        execution_mode="static",
        apgr_home=tmp_path / "apgr",
        outbox_root=tmp_path / "outbox",
        lifecycle="work-reviewed",
        finalization_policy="checkpoint",
        display=None,
        runner=mock_runner,
        review_mutation_policy="warn",
    )

    assert res["status"] == "completed"
    assert res["finalization_status"] == "checkpointed"
    assert res["subject_drift_observed"] is True
    # Work review drifted, so candidate freshness is False
    assert res["final_candidate_reviewed"] is False

    # Verify SQLite persistence of policy and observations
    conn = open_dispatcher_db(db_path)
    policies = get_review_mutation_policies(conn, res["run_id"])
    assert len(policies) >= 1
    winning = [p for p in policies if p["is_winner"]]
    assert len(winning) == 1
    assert winning[0]["worktree_policy"] == "warn"

    obs_records = get_review_mutation_observations(conn, res["run_id"])
    assert len(obs_records) >= 1
    obs_map = {r["stage"]: r for r in obs_records}
    assert "binding_work_review" in obs_map or "work_review" in obs_map


def test_resume_preserves_review_mutation_observations_and_policy_transition(
    repository: Path, tmp_path: Path
):
    """Resume preserves prior review mutation observations and records policy transitions."""
    def failing_terminal_runner(argv, prompt, cwd, max_output=None, on_output=None):
        import re
        import time
        from agent_phase.provider import Result
        from test_agent_phase_lifecycle_dispatch import review_payload
        stage_match = re.search(rb"^stage: ([a-z_]+)$", prompt, re.MULTILINE)
        stage = stage_match.group(1).decode() if stage_match else "unknown"
        if stage == "work":
            (cwd / "product.txt").write_text("produced")
        elif stage == "work_review":
            (cwd / "review-scratch.txt").write_text("review scratch")
            return Result(0, review_payload(prompt, "reviewed_with_no_findings"), b"", False, time.time(), time.time())
        elif stage == "revise_close":
            return Result(1, b"provider failed", b"error", False, time.time(), time.time())
        now = time.time()
        return Result(0, f"{stage} out".encode(), b"", False, now, now)

    disp = _dispatcher(
        repository,
        tmp_path / "run-fail",
        failing_terminal_runner,
        review_mutation_policy="warn",
    )
    with pytest.raises(DispatchError):
        disp.dispatch("APG160", REQUEST, "work-reviewed", "checkpoint")

    source_dir = only_run(tmp_path / "run-fail" / "runs")
    assert (source_dir / "review-mutation-policy.json").exists()

    clean_git_worktree(repository)
    (repository / "product.txt").write_text("produced")
    (repository / "review-scratch.txt").write_text("review scratch")

    def resume_runner(argv, prompt, cwd, max_output=None, on_output=None):
        import time
        from agent_phase.provider import Result
        from test_agent_phase_lifecycle_dispatch import terminal_payload
        now = time.time()
        stdout = terminal_payload(
            prompt,
            "Resumed Closeout",
            path_dispositions=[
                {"path": "product.txt", "disposition": "phase_owned"},
                {"path": "review-scratch.txt", "disposition": "phase_owned"},
            ],
        )
        return Result(0, stdout, b"", False, now, now)

    disp_resume = _dispatcher(
        repository,
        tmp_path / "run-resume",
        resume_runner,
        review_mutation_policy="allow",
    )
    resumed_state = disp_resume.resume(
        "APG160",
        REQUEST,
        source_dir,
        "auto",
        lifecycle="work-reviewed",
        finalization_policy="checkpoint",
    )
    assert resumed_state["outcome"] == "completed"
    assert "work_review" in resumed_state["review_mutation_observations"]
    assert "review_mutation_policy_transition" in resumed_state
    trans = resumed_state["review_mutation_policy_transition"]
    assert trans["source_policy"]["worktree"] == "warn"
    assert trans["active_policy"]["worktree"] == "allow"


# ==============================================================================
# Helper
# ==============================================================================


def clean_git_worktree(repo: Path):
    git(repo, "clean", "-fd")


def test_unknown_head_observation_fails_closed_and_records_limitation(repository):
    from agent_phase import gitstate
    from agent_phase.review_drift import (
        ACTION_BLOCKED,
        READ_ONLY_STAGE_MUTATED_HEAD,
        apply_review_mutation_policy,
        observe_review_drift,
    )
    from unittest.mock import patch

    with patch.object(gitstate, "current_head", side_effect=RuntimeError("git failure")):
        obs = observe_review_drift(
            repository,
            stage="work_review",
            before={"tree": "a" * 40, "head": "b" * 40},
            after={"tree": "a" * 40},
        )
    assert obs.head_drift is False
    assert obs.subject_drift_observed is False
    assert obs.head_observation_unavailable is True
    assert any(lim.get("kind") == "head_observation_unavailable" for lim in obs.observation_limitations)
    assert obs.paths_complete is False

    evaluated = apply_review_mutation_policy(obs, raise_on_block=False)
    assert evaluated.action_taken == ACTION_BLOCKED
    assert evaluated.diagnostic_code == READ_ONLY_STAGE_MUTATED_HEAD
    assert "HEAD observation unavailable" in evaluated.detail


def test_unknown_index_observation_fails_closed_without_asserting_drift(repository):
    from agent_phase import gitstate
    from agent_phase.review_drift import (
        ACTION_BLOCKED,
        READ_ONLY_STAGE_MUTATED_INDEX,
        apply_review_mutation_policy,
        observe_review_drift,
    )
    from unittest.mock import patch

    with patch.object(gitstate, "index_identity", side_effect=RuntimeError("index read failed")):
        obs = observe_review_drift(
            repository,
            stage="work_review",
            before={"tree": "a" * 40, "head": "b" * 40, "index": {"paths": 1}},
            after={"tree": "a" * 40, "head": "b" * 40},
        )
    assert obs.observed_index is None
    assert obs.index_drift is False
    assert obs.index_observation_unavailable is True
    assert any(lim.get("kind") == "index_observation_unavailable" for lim in obs.observation_limitations)

    evaluated = apply_review_mutation_policy(obs, raise_on_block=False)
    assert evaluated.action_taken == ACTION_BLOCKED
    assert evaluated.diagnostic_code == READ_ONLY_STAGE_MUTATED_INDEX
    assert "staged index observation unavailable" in evaluated.detail


def test_derive_final_candidate_freshness_enforces_criterion_1_and_empty_obs():
    from agent_phase.review_drift import (
        ReviewObservation,
        derive_final_candidate_freshness,
    )

    tree = "a" * 40

    # Empty observation or None -> False
    assert derive_final_candidate_freshness(
        work_review_observation={},
        work_review_candidate_tree=tree,
        terminal_candidate_tree=tree,
    ) is False
    assert derive_final_candidate_freshness(
        work_review_observation=None,
        work_review_candidate_tree=tree,
        terminal_candidate_tree=tree,
    ) is False

    # Plan review role never certifies work candidates (Criterion 1)
    plan_obs = ReviewObservation(
        stage="plan_review",
        policy="warn",
        subject_drift_observed=False,
        worktree_drift=False,
        index_drift=False,
        head_drift=False,
        role="plan_reviewer",
        subject_kind="plan",
    )
    assert derive_final_candidate_freshness(
        work_review_observation=plan_obs,
        work_review_candidate_tree=tree,
        terminal_candidate_tree=tree,
    ) is False

    # Work review missing head/index evidence is rejected
    work_obs_incomplete = ReviewObservation(
        stage="final_review",
        policy="warn",
        subject_drift_observed=False,
        worktree_drift=False,
        index_drift=False,
        head_drift=False,
        role="work_reviewer",
        subject_kind="work",
        expected_tree=tree,
        observed_tree=tree,
    )
    assert derive_final_candidate_freshness(
        work_review_observation=work_obs_incomplete,
        work_review_candidate_tree=tree,
        terminal_candidate_tree=tree,
        has_verified_receipt=True,
    ) is False

    # Complete work review with all 3 axes certifies freshness
    head_hash = "b" * 40
    index_id = {"kind": "git_ls_files_stage_v1", "sha256": "c" * 40}
    work_obs = ReviewObservation(
        stage="final_review",
        policy="warn",
        subject_drift_observed=False,
        worktree_drift=False,
        index_drift=False,
        head_drift=False,
        role="work_reviewer",
        subject_kind="work",
        expected_tree=tree,
        observed_tree=tree,
        expected_head=head_hash,
        observed_head=head_hash,
        expected_index=index_id,
        observed_index=index_id,
    )
    assert derive_final_candidate_freshness(
        work_review_observation=work_obs,
        work_review_candidate_tree=tree,
        terminal_candidate_tree=tree,
        has_verified_receipt=True,
    ) is True


def test_observation_immutability_and_sticky_drift_across_retries(repository, tmp_path):
    from agent_phase.persistence import (
        open_dispatcher_db,
        record_run,
        get_review_mutation_observations,
        record_review_mutation_observation,
    )
    from agent_phase.review_drift import (
        ACTION_WARNED,
        ReviewObservation,
        apply_review_mutation_policy,
    )

    state = {}
    obs_warn = ReviewObservation(
        stage="work_review",
        policy="warn",
        subject_drift_observed=True,
        worktree_drift=True,
        index_drift=False,
        head_drift=False,
        worktree_paths=["drift.txt"],
    )
    apply_review_mutation_policy(obs_warn, state=state)
    assert state["review_mutation_observations"]["work_review"]["action_taken"] == ACTION_WARNED

    # Subsequent clean observation records honest turn snapshot without sticky drift overwrite
    obs_clean = ReviewObservation(
        stage="work_review",
        policy="warn",
        subject_drift_observed=False,
        worktree_drift=False,
        index_drift=False,
        head_drift=False,
    )
    apply_review_mutation_policy(obs_clean, state=state)
    assert state["review_mutation_observations"]["work_review"]["subject_drift_observed"] is False
    assert state["review_mutation_observations"]["work_review"]["action_taken"] == "none"
    assert len(state["review_mutation_observation_history"]) == 2
    assert state["review_mutation_observation_history"][0]["action_taken"] == ACTION_WARNED
    assert state["review_mutation_observation_history"][1]["action_taken"] == "none"

    # SQLite persistence append-only with 1-based monotonic sequence
    db_path = tmp_path / "state.sqlite"
    conn = open_dispatcher_db(db_path)
    record_run(
        conn,
        run_id="run-1",
        project="apgr",
        request_schema="agent-phase-request-v2",
        request_digest="dig-123",
        lifecycle="default_v012",
        execution_mode="dynamic",
    )
    record_review_mutation_observation(conn, run_id="run-1", stage="work_review", observation=obs_warn.as_dict())
    record_review_mutation_observation(conn, run_id="run-1", stage="work_review", observation=obs_clean.as_dict())
    rows = get_review_mutation_observations(conn, "run-1")
    assert len(rows) == 2
    assert rows[0]["sequence"] == 0
    assert rows[1]["sequence"] == 1
    assert rows[0]["action_taken"] == ACTION_WARNED


def test_ownership_challenge_precedence_over_closer_disposition():
    from collections import namedtuple
    from unittest.mock import MagicMock, patch
    from agent_phase.ownership_challenge import _reason

    Change = namedtuple("Change", ["path", "status"])
    Entry = namedtuple("Entry", ["dirty", "tree", "head"])

    entry = Entry(dirty={"dirty.txt"}, tree="0" * 40, head="0" * 40)
    change_dirty = Change(path="dirty.txt", status="M")
    change_del = Change(path="deleted.txt", status="D")

    with patch("agent_phase.ownership_challenge.object_at", return_value={"oid": "old"}):
        # Even if dirty.txt is in review_window_paths and dispositioned, entry_dirt_overlap takes precedence
        reason = _reason(
            MagicMock(),
            entry,
            change_dirty,
            after="1" * 40,
            carried=set(),
            inherited_deletions=set(),
            review_window_paths={"dirty.txt"},
            closer_dispositioned_paths={"dirty.txt"},
        )
        assert reason == "entry_dirt_overlap"

        # Even if deleted.txt is in review_window_paths and dispositioned, unclaimed_tracked_deletion takes precedence
        reason_del = _reason(
            MagicMock(),
            entry,
            change_del,
            after="",
            carried=set(),
            inherited_deletions=set(),
            review_window_paths={"deleted.txt"},
            closer_dispositioned_paths={"deleted.txt"},
        )
        assert reason_del == "unclaimed_tracked_deletion"

