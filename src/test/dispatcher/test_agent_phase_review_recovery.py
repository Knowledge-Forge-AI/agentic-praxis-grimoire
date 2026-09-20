"""Fresh-review retry with real temporary Git state and provider-free transports."""
import hashlib
import json
from pathlib import Path
import re
import time

import pytest
from agent_phase.dispatch import DispatchError
from agent_phase.provider import Result
from agent_phase.request import PhaseRequest
from agent_phase.resume_validation import completed_prefix, validate_bindings
from test_agent_phase_dispatch import repository as _repository, make_dispatcher, PHASE_ID, review_payload, closeout_payload, write_fake_evidence

repository = _repository

REQUEST = PhaseRequest("implementation_testing", "normal", "bounded recovery fixture")


class ReviewRunner:
    def __init__(self, bad=1, shape="jsonc", retry_exit=0, mutate=False, review_stage="final_review", fail_closeout=False):
        self.review_stage = review_stage
        self.fail_closeout = fail_closeout
        self.calls = []
        self.bad = bad
        self.shape = shape
        self.reviews = 0
        self.retry_exit = retry_exit
        self.mutate = mutate

    def __call__(self, argv, prompt, cwd, max_output, on_output=None):
        stage = re.search(rb"^stage: (\w+)", prompt, re.M).group(1).decode()
        self.calls.append((stage, prompt, list(argv)))
        exit_code = 0
        if stage in ("plan_review", "final_review", "work_review"):
            stdout = review_payload(prompt, stage)
            if stage == self.review_stage:
                self.reviews += 1
                if self.reviews == 2:
                    exit_code = self.retry_exit
                if self.reviews <= self.bad:
                    if self.shape == "jsonc":
                        stdout = stdout.replace(b'"no findings"', b'"unterminated')
                    elif self.shape == "missing":
                        stdout = b"no result"
                    elif self.shape == "duplicate":
                        stdout += stdout
                    else:
                        nonce = re.search(rb"RESULT ([0-9a-f]{32})", stdout).group(1)
                        stdout = stdout.replace(nonce, b"0" * 32)
                if self.mutate:
                    (cwd / "file.txt").write_text("review mutation")
        elif stage in ("closeout", "produce_close", "revise_close"):
            stdout = closeout_payload(prompt).replace(b'"stage": "closeout"', ('"stage": "' + stage + '"').encode())
            if self.fail_closeout:
                exit_code = 7
        else:
            stdout = b"coherent plan or work"
        write_fake_evidence(list(argv), exit_code)
        return Result(exit_code, stdout, b"diagnostics", False, time.time(), time.time())


@pytest.mark.parametrize("bad,shape", [(0,"jsonc"),(1,"jsonc"),(2,"jsonc"),
    (2,"wrong"),(2,"duplicate"),(2,"missing")])
def test_bounded_review_attempts(repository, tmp_path, bad, shape):
    runner = ReviewRunner(bad, shape)
    index = (repository / ".git/index").read_bytes()
    original = (repository / "file.txt").read_bytes()
    dispatcher = make_dispatcher(repository, tmp_path, runner)
    if bad == 2:
        with pytest.raises(DispatchError) as caught:
            dispatcher.dispatch(PHASE_ID, REQUEST)
        assert caught.value.code == "REVIEW_RESULT_INVALID"
    else:
        dispatcher.dispatch(PHASE_ID, REQUEST)
    source = next((tmp_path / "runs").rglob("state.json")).parent
    state = json.loads((source / "state.json").read_bytes())
    assert runner.reviews == (1 if bad == 0 else 2)
    assert [s for s,p,a in runner.calls].count("work") == 1
    assert (repository / "file.txt").read_bytes() == original
    assert (repository / ".git/index").read_bytes() == index
    assert state["auxiliary_provider_invocations_performed"] == (0 if bad == 0 else 1)
    if bad:
        recovery = state["review_recoveries"]["final_review"]
        assert recovery["second_provider_invocation"] is True
        assert recovery["attempt_count"] == 2
        first, second = recovery["attempts"]
        assert first["nonce"] != second["nonce"]
        for attempt in (first, second):
            for artifact in attempt["artifacts"]:
                data = (source / artifact["name"]).read_bytes()
                assert len(data) == artifact["bytes"]
                assert hashlib.sha256(data).hexdigest() == artifact["sha256"]
            meta = next(a for a in attempt["artifacts"] if a["name"].endswith(".meta.json"))
            assert json.loads((source / meta["name"]).read_bytes())["candidate"] == recovery["candidate"]
    if bad < 2:
        resolved = json.loads((source / "resolved.json").read_bytes())
        completed = completed_prefix(state, resolved, source)
        validate_bindings(source, state, completed)
        assert completed.count("final_review") == 1
    else:
        assert state["stages_completed"] == ["plan", "plan_review", "work"]


def test_retry_transport_failure_remains_transport_failure(repository, tmp_path):
    runner = ReviewRunner(retry_exit=7)
    with pytest.raises(DispatchError) as caught:
        make_dispatcher(repository, tmp_path, runner).dispatch(PHASE_ID, REQUEST)
    assert caught.value.code == "PROVIDER_TRANSPORT_FAILED"
    assert runner.reviews == 2


def test_mutating_first_review_cannot_retry(repository, tmp_path):
    runner = ReviewRunner(mutate=True)
    with pytest.raises(DispatchError) as caught:
        make_dispatcher(repository, tmp_path, runner).dispatch(PHASE_ID, REQUEST)
    assert caught.value.code == "READ_ONLY_STAGE_MUTATED_CANDIDATE"
    assert runner.reviews == 1


def test_recovered_review_can_be_inherited_by_resume(repository, tmp_path):
    runner = ReviewRunner(fail_closeout=True)
    with pytest.raises(DispatchError, match="failed"):
        make_dispatcher(repository, tmp_path, runner).dispatch(PHASE_ID, REQUEST)
    source = next((tmp_path / "runs").rglob("state.json")).parent
    resumed_runner = ReviewRunner(bad=0)
    state = make_dispatcher(repository, tmp_path / "resumed", resumed_runner).resume(
        PHASE_ID, REQUEST, source, "closeout")
    assert [stage for stage, _, _ in resumed_runner.calls] == ["closeout"]
    assert state["auxiliary_provider_invocations_inherited"] == 1
    resumed = Path(state["run_directory"])
    resolved = json.loads((resumed / "resolved.json").read_bytes())
    completed_prefix(state, resolved, resumed)
    assert (resumed / "04-final-review.recovery.json").is_file()


@pytest.mark.parametrize("lifecycle,stage", [("plan-reviewed", "plan_review"), ("work-reviewed", "work_review")])
def test_projected_lifecycle_uses_same_bounded_recovery(repository, tmp_path, lifecycle, stage):
    runner = ReviewRunner(review_stage=stage)
    state = make_dispatcher(repository, tmp_path, runner).dispatch(
        PHASE_ID, REQUEST, lifecycle=lifecycle)
    assert state["outcome"] == "completed"
    assert runner.reviews == 2
    assert state["auxiliary_provider_invocations_performed"] == 1
    assert state["semantic_provider_invocations_performed"] == 3


def test_pending_worker_custody_prevents_second_invocation(repository, tmp_path):
    runner = ReviewRunner()
    dispatcher = make_dispatcher(repository, tmp_path, runner)
    original = runner.__call__
    def pending(argv, prompt, cwd, max_output, on_output=None):
        result = original(argv, prompt, cwd, max_output, on_output)
        if runner.calls[-1][0] == "final_review":
            dispatcher._stage_accounting_state["worker_cleanup_pending"] = {
                "artifact": "04-final-review.worker-drain.json", "status": "incomplete"}
        return result
    dispatcher.runner = pending
    with pytest.raises(DispatchError) as caught:
        dispatcher.dispatch(PHASE_ID, REQUEST)
    assert caught.value.code == "WORKER_CLEANUP_FAILED"
    assert runner.reviews == 1
