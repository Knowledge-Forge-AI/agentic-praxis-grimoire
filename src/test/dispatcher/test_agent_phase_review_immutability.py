"""Real Git boundaries: a valid transport cannot accept a stale review."""

import json

import pytest

from agent_phase.dispatch import DispatchError
from agent_phase.lifecycle import LIFECYCLES
from test_agent_phase_dispatch import git, repository as _repository
from test_agent_phase_lifecycle_dispatch import (
    LifecycleRunner, REQUEST, dispatcher, only_run,
)

repository = _repository


def evidence(tmp_path):
    source = only_run(tmp_path / "runs")
    return source, json.loads((source / "state.json").read_bytes())


@pytest.mark.parametrize("change", ["modify", "add", "delete", "index", "tracked_metadata", "tracked_metadata_index"])
@pytest.mark.parametrize("policy", ["checkpoint", "commit-local", "publish"])
def test_work_review_drift_blocks_without_acceptance_or_finalization(repository, tmp_path, change, policy):
    target = "file.txt"
    if change.startswith("tracked_metadata"):
        target = ".serena/product.txt"
        (repository / ".serena").mkdir()
        (repository / target).write_text("tracked product")
        git(repository, "add", target)
        git(repository, "commit", "-m", "Track metadata-looking product")
    head = git(repository, "rev-parse", "HEAD")
    original = (repository / target).read_bytes()
    observed = {}

    def mutate(stage, cwd):
        if stage != "work_review":
            return
        path = cwd / ("new-product.txt" if change == "add" else target)
        if change == "delete":
            path.unlink()
        else:
            path.write_text("observed concurrent change")
        if "index" in change:
            git(cwd, "add", target)
            # Isolate an index-only change from worktree drift.
            path.write_bytes(original)
        observed["index"] = (cwd / ".git/index").read_bytes()
        observed["bytes"] = path.read_bytes() if path.exists() else None

    runner = LifecycleRunner(mutate)
    with pytest.raises(DispatchError) as caught:
        dispatcher(repository, tmp_path, runner).dispatch("IMMUT", REQUEST, "work-reviewed", policy)
    expected = "READ_ONLY_STAGE_MUTATED_INDEX" if "index" in change else "READ_ONLY_STAGE_MUTATED_CANDIDATE"
    assert caught.value.code == expected
    source, state = evidence(tmp_path)
    assert [call["stage"] for call in runner.calls] == ["produce", "work_review"]
    assert state["checkpoints_completed"] == []
    assert state["stages_completed"] == ["produce"]
    assert not (source / "02-work-review.result.json").exists()
    assert (source / "02-work-review.stdout.md").is_file()
    invalidation = state["review_binding_invalidations"]["work_review"]
    assert invalidation["expected_tree"]
    assert invalidation["observed_tree"]
    assert invalidation["expected_index"]
    assert invalidation["observed_index"]
    assert invalidation["candidate_binding"] == state["produced_candidate"]
    assert invalidation["transport"]["exit_code"] == 0
    path = "new-product.txt" if change == "add" else target
    assert path in invalidation["paths"] + invalidation["index_paths"]
    assert state["manager_disposition_required"] is True
    assert not state.get("failure_candidate")
    assert not state.get("phase_owned_paths")
    result = json.loads((source / "result.json").read_bytes())
    assert result["semantic_outcome"] == "blocked"
    assert result["finalization_outcome"] == "not_attempted"
    assert not state.get("commit")
    assert git(repository, "rev-parse", "HEAD") == head
    current = repository / path
    assert (current.read_bytes() if current.exists() else None) == observed["bytes"]
    if "index" in change:
        assert invalidation["expected_tree"] == invalidation["observed_tree"]
        assert (repository / ".git/index").read_bytes() == observed["index"]


REVIEWS = [(name, stage.name) for name, spec in LIFECYCLES.items()
           for stage in spec.stages if stage.checkpoint]


@pytest.mark.parametrize("lifecycle,review", REVIEWS)
def test_every_registered_checkpoint_is_fenced(repository, tmp_path, lifecycle, review):
    def mutate(stage, cwd):
        if stage == review:
            (cwd / "concurrent.txt").write_text("change")
    runner = LifecycleRunner(mutate)
    with pytest.raises(DispatchError) as caught:
        dispatcher(repository, tmp_path, runner).dispatch("IMMUT", REQUEST, lifecycle, "checkpoint")
    assert caught.value.code == "READ_ONLY_STAGE_MUTATED_CANDIDATE"
    assert runner.calls[-1]["stage"] == review
    _, state = evidence(tmp_path)
    assert review not in state["stages_completed"]
    assert LIFECYCLES[lifecycle].stage(review).checkpoint not in state["checkpoints_completed"]
    if review == "plan_review":
        record = state["review_binding_invalidations"][review]
        assert record["candidate_binding"] == state["plan_candidate"]
        assert state["immutable_review_bindings"][review]["repository"]["kind"] == "git_tree"


@pytest.mark.parametrize("staged", [False, True])
def test_operational_metadata_remains_informational(repository, tmp_path, staged):
    def mutate(stage, cwd):
        if stage == "work_review":
            (cwd / ".serena").mkdir()
            (cwd / ".serena/cache").write_text("metadata")
            if staged:
                git(cwd, "add", ".serena/cache")
    state = dispatcher(repository, tmp_path, LifecycleRunner(mutate)).dispatch(
        "IMMUT", REQUEST, "work-reviewed", "checkpoint")
    assert state["checkpoints_completed"] == ["post_work"]
    assert (repository / ".serena/cache").read_text() == "metadata"
    assert ".serena/cache" in state["stage_delta_ledger"]["stages"]["work_review"]["operational_metadata_paths"]
    if staged:
        assert state["index_normalizations"][0]["restored_clean"]


@pytest.mark.parametrize("attempt", [0, 1, 2])
def test_malformed_retry_has_same_immutable_boundary(repository, tmp_path, attempt):
    class Runner(LifecycleRunner):
        reviews = 0

        def __call__(self, argv, prompt, cwd, max_output, on_output=None):
            result = super().__call__(argv, prompt, cwd, max_output, on_output)
            if self.calls[-1]["stage"] == "work_review":
                self.reviews += 1
                if self.reviews == attempt:
                    (cwd / "concurrent.txt").write_text("change")
                if self.reviews == 1:
                    result = result._replace(stdout=b"malformed review")
            return result
    runner = Runner()
    execute = dispatcher(repository, tmp_path, runner)
    if attempt:
        with pytest.raises(DispatchError) as caught:
            execute.dispatch("IMMUT", REQUEST, "work-reviewed", "checkpoint")
        assert caught.value.code == "READ_ONLY_STAGE_MUTATED_CANDIDATE"
        source, state = evidence(tmp_path)
        assert state["checkpoints_completed"] == []
        assert not (source / "02-work-review.result.json").exists()
        if attempt == 2:
            assert len(state["review_recoveries"]["work_review"]["attempts"]) == 2
    else:
        state = execute.dispatch("IMMUT", REQUEST, "work-reviewed", "checkpoint")
        assert state["checkpoints_completed"] == ["post_work"]
    assert runner.reviews == (1 if attempt == 1 else 2)


def test_transport_failure_without_drift_keeps_transport_blocker(repository, tmp_path):
    runner = LifecycleRunner(fail_stage="work_review")
    with pytest.raises(DispatchError) as caught:
        dispatcher(repository, tmp_path, runner).dispatch("IMMUT", REQUEST, "work-reviewed", "checkpoint")
    assert caught.value.code == "PROVIDER_TRANSPORT_FAILED"


def test_resume_requires_fresh_review_after_manager_resolution(repository, tmp_path):
    original = (repository / "file.txt").read_bytes()
    def mutate(stage, cwd):
        if stage == "produce":
            (cwd / "produced.txt").write_text("produced candidate")
        elif stage == "work_review":
            (cwd / "file.txt").write_text("concurrent change")
    with pytest.raises(DispatchError):
        dispatcher(repository, tmp_path, LifecycleRunner(mutate)).dispatch(
            "IMMUT", REQUEST, "work-reviewed", "checkpoint")
    source, _ = evidence(tmp_path)
    runner = LifecycleRunner()
    with pytest.raises(DispatchError):
        dispatcher(repository, tmp_path / "skip", runner).resume(
            "IMMUT", REQUEST, source, "revise_close")
    assert runner.calls == []
    with pytest.raises(DispatchError) as caught:
        dispatcher(repository, tmp_path / "unresolved", runner).resume(
            "IMMUT", REQUEST, source, "work_review")
    assert caught.value.code == "RESUME_CANDIDATE_CONFLICT"
    assert runner.calls == []
    # Explicit fixture operator resolution; dispatcher never performs this write.
    (repository / "file.txt").write_bytes(original)
    (repository / "unrelated.txt").write_text("operator dirt")
    state = dispatcher(repository, tmp_path / "fresh", runner).resume(
        "IMMUT", REQUEST, source, "work_review")
    assert [call["stage"] for call in runner.calls] == ["work_review", "revise_close"]
    assert state["checkpoints_completed"] == ["post_work"]
    assert (repository / "unrelated.txt").read_text() == "operator dirt"
    assert "unrelated.txt" not in state["phase_owned_paths"]


def test_parser_time_drift_cannot_become_accepted_review(repository, tmp_path, monkeypatch):
    from agent_phase import review_result
    original = review_result.parse
    def parse(data, stage, nonce):
        parsed = original(data, stage, nonce)
        if stage == "work_review":
            (repository / "concurrent.txt").write_text("changed while parsing")
        return parsed
    monkeypatch.setattr(review_result, "parse", parse)
    with pytest.raises(DispatchError) as caught:
        dispatcher(repository, tmp_path, LifecycleRunner()).dispatch(
            "IMMUT", REQUEST, "work-reviewed", "checkpoint")
    assert caught.value.code == "READ_ONLY_STAGE_MUTATED_CANDIDATE"
    source, state = evidence(tmp_path)
    assert not (source / "02-work-review.result.json").exists()
    assert state["checkpoints_completed"] == []
    transport = state["review_binding_invalidations"]["work_review"]["transport"]
    assert transport["status"] == "completed"
    assert transport["exit_code"] == 0


def test_failed_transport_with_drift_retains_both_facts(repository, tmp_path):
    def mutate(stage, cwd):
        if stage == "work_review":
            (cwd / "concurrent.txt").write_text("changed before transport failed")
    with pytest.raises(DispatchError) as caught:
        dispatcher(repository, tmp_path, LifecycleRunner(mutate, fail_stage="work_review")).dispatch(
            "IMMUT", REQUEST, "work-reviewed", "checkpoint")
    assert caught.value.code == "READ_ONLY_STAGE_MUTATED_CANDIDATE"
    source, state = evidence(tmp_path)
    assert state["review_binding_invalidations"]["work_review"]["transport"]["exit_code"] == 1
    assert json.loads((source / "02-work-review.meta.json").read_bytes())["exit_code"] == 1


def test_malformed_retry_parser_race_preserves_mutation_blocker(repository, tmp_path, monkeypatch):
    from agent_phase import review_result
    original = review_result.parse
    attempts = []
    def parse(data, stage, nonce):
        if stage == "work_review":
            attempts.append(nonce)
            if len(attempts) == 2:
                (repository / "concurrent.txt").write_text("changed during retry parsing")
        return original(data, stage, nonce)
    class Runner(LifecycleRunner):
        def __call__(self, *args):
            result = super().__call__(*args)
            return result._replace(stdout=b"malformed") if self.calls[-1]["stage"] == "work_review" else result
    monkeypatch.setattr(review_result, "parse", parse)
    with pytest.raises(DispatchError) as caught:
        dispatcher(repository, tmp_path, Runner()).dispatch(
            "IMMUT", REQUEST, "work-reviewed", "checkpoint")
    assert caught.value.code == "READ_ONLY_STAGE_MUTATED_CANDIDATE"
    source, state = evidence(tmp_path)
    assert len(state["review_recoveries"]["work_review"]["attempts"]) == 2
    assert not (source / "02-work-review.result.json").exists()
    assert state["checkpoints_completed"] == []


def test_head_only_drift_is_self_describing(repository, tmp_path):
    def mutate(stage, cwd):
        if stage == "work_review":
            git(cwd, "commit", "--allow-empty", "-m", "Concurrent ref change")
    with pytest.raises(DispatchError) as caught:
        dispatcher(repository, tmp_path, LifecycleRunner(mutate)).dispatch(
            "IMMUT", REQUEST, "work-reviewed", "checkpoint")
    assert caught.value.code == "READ_ONLY_STAGE_MUTATED_CANDIDATE"
    _, state = evidence(tmp_path)
    record = state["review_binding_invalidations"]["work_review"]
    assert record["expected_head"] != record["observed_head"]
    assert record["expected_tree"] == record["observed_tree"]
    assert record["expected_index"] == record["observed_index"]
    assert record["paths"] == record["index_paths"] == []
    assert state["checkpoints_completed"] == []


@pytest.mark.parametrize("unavailable", ["paths", "candidate"])
def test_incomplete_observation_retains_blocker_and_requires_resolution(repository, monkeypatch, unavailable):
    from agent_phase import candidate, review_binding
    from agent_phase.resume_validation import ResumeError
    state = {"lifecycle": "work-reviewed"}
    binding = review_binding.bind(repository, state, "work_review", None)
    (repository / "file.txt").write_text("concurrent change")
    current = candidate.tree_identity(repository)
    original_delta = candidate.tree_delta
    def fail(*args):
        raise candidate.CandidateError("injected observation failure")
    monkeypatch.setattr(candidate, "tree_delta" if unavailable == "paths" else "tree_identity", fail)
    with pytest.raises(DispatchError) as caught:
        review_binding.verify(repository, state, "work_review")
    assert caught.value.code == "READ_ONLY_STAGE_MUTATED_CANDIDATE"
    record = state["review_binding_invalidations"]["work_review"]
    assert record["paths_complete"] is False
    assert record["observation_limitations"]
    assert record["candidate_observation_unavailable"] is (unavailable == "candidate")
    assert state["manager_disposition_required"] is True
    assert state["blocking_reason"]["code"] == caught.value.code
    assert (repository / "file.txt").read_text() == "concurrent change"
    monkeypatch.setattr(candidate, "tree_delta", original_delta)
    with pytest.raises(ResumeError) as resumed:
        review_binding.require_resolved_resume(repository, state, current["tree"])
    assert resumed.value.code == "RESUME_CANDIDATE_CONFLICT"
    review_binding.require_resolved_resume(repository, state, binding["repository"]["tree"])


def test_combined_drift_retains_product_and_index_diagnosis(repository, tmp_path):
    def mutate(stage, cwd):
        if stage == "work_review":
            (cwd / "file.txt").write_text("concurrent change")
            git(cwd, "add", "file.txt")
    with pytest.raises(DispatchError) as caught:
        dispatcher(repository, tmp_path, LifecycleRunner(mutate)).dispatch(
            "IMMUT", REQUEST, "work-reviewed", "checkpoint")
    assert caught.value.code == "READ_ONLY_STAGE_MUTATED_INDEX"
    _, state = evidence(tmp_path)
    record = state["review_binding_invalidations"]["work_review"]
    assert record["paths"] == record["index_paths"] == ["file.txt"]
    assert record["index_normalization_reason"] == "protected review index mutation; normalization not attempted"
