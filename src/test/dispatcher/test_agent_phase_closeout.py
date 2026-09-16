"""Regressions for the dispatcher git-closeout repair.

The bug these cover was real: run 20260818T023814Z-8835c223 exited 0 from a
closeout that reported `Commit closeout — BLOCKED` (`.git/index.lock`:
Operation not permitted), left the target worktree dirty, and was recorded as
`complete: true` with five stages and two reviews.

Two invariants are under test throughout:

* CLI exit 0 is transport success, never phase completion.
* The dispatcher, not the provider, performs the local commit — the provider
  sandbox denies `.git` writes by design, so a provider that cannot commit is
  the normal architecture rather than an exceptional workaround.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import zipfile

import pytest

from agent_phase import gitstate as gitstate_module
from agent_phase import result as result_module
from agent_phase.dispatch import DispatchError, Dispatcher
from agent_phase.request import PhaseRequest

from test_agent_phase_dispatch import (
    ROOT, STAGE_ORDER, FakeRunner, closeout_payload, git, make_dispatcher,
    repository,
)


__all__ = ["repository"]

REQUEST = PhaseRequest("implementation_testing", "claude_only", "task")
PHASE_ID = "TEST-PHASE"


def status(repo: Path) -> str:
    return subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo, capture_output=True, check=True
    ).stdout.decode()


def head(repo: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, check=True
    ).stdout.decode().strip()


def artifact(tmp_path: Path, name: str, run_root: str = "runs") -> dict:
    """Read a run artifact, whether the run completed or not.

    Runs live at `<root>/<project>/<phase-id>--<timestamp>/`. Each dispatcher
    gets its own run root and this asserts there is exactly one run under it,
    so a test never reads an artifact from a run it did not make.
    """
    runs = list((tmp_path / run_root).rglob(name))
    assert len(runs) == 1, f"expected one run under {run_root}, found {len(runs)}"
    return json.loads(runs[0].read_text())


def state_of(dispatcher: Dispatcher, tmp_path: Path) -> dict:
    return artifact(tmp_path, "state.json")


def writing(repo: Path, path: str, text: str):
    """Provider behaviour: edit the worktree during the work stage only."""
    def hook(index: int) -> None:
        if index == 2:
            target = repo / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
    return hook


# -- Case A: provider exits 0 but does not report completion -----------------


@pytest.mark.parametrize("outcome", ["blocked", "failed"])
def test_provider_exit_zero_with_non_completed_outcome_cannot_complete(
    repository: Path, tmp_path: Path, outcome: str
) -> None:
    """The exact observed bug: exit 0, phase not done, dirty delta pending."""
    runner = FakeRunner(
        closeout_outcome=outcome, on_stage=writing(repository, "new.txt", "phase\n")
    )
    dispatcher = make_dispatcher(repository, tmp_path, runner)
    before = head(repository)

    with pytest.raises(DispatchError) as caught:
        dispatcher.dispatch(PHASE_ID, REQUEST)

    assert caught.value.code == f"PROVIDER_OUTCOME_{outcome.upper()}"
    assert runner.calls[4] is not None  # closeout did run
    state = state_of(dispatcher, tmp_path)
    assert state["complete"] is False
    assert state["outcome"] == "blocked"
    assert state["blocking_reason"]["code"] == f"PROVIDER_OUTCOME_{outcome.upper()}"
    assert state["commit"] is None
    assert head(repository) == before
    assert "new.txt" in status(repository)


def test_prose_closeout_is_not_parsed_for_the_word_blocked(
    repository: Path, tmp_path: Path
) -> None:
    """No prose fallback: unstructured output is invalid, not interpreted."""
    prose = (
        b"**Commit closeout - BLOCKED.**\n"
        b"fatal: Unable to create '.git/index.lock': Operation not permitted\n"
    )
    runner = FakeRunner(
        closeout_stdout=prose, on_stage=writing(repository, "new.txt", "phase\n")
    )
    dispatcher = make_dispatcher(repository, tmp_path, runner)

    with pytest.raises(DispatchError) as caught:
        dispatcher.dispatch(PHASE_ID, REQUEST)

    assert caught.value.code == "RESULT_MISSING_FENCE"
    assert state_of(dispatcher, tmp_path)["complete"] is False


class FormattingRepairRunner(FakeRunner):
    """Emit the attached begin-only closeout, then one formatter response."""

    def __init__(self, repository: Path, *, repair_succeeds: bool = True) -> None:
        super().__init__(on_stage=writing(repository, "phase.txt", "phase\n"))
        self.repair_succeeds = repair_succeeds

    def __call__(self, argv, prompt, cwd, max_output, on_output=None):
        index = len(self.calls)
        result = super().__call__(argv, prompt, cwd, max_output, on_output)
        if index == 4:
            match = re.search(rb"<<<AGENT-PHASE-RESULT ([0-9a-f]{32})>>>", prompt)
            assert match is not None
            nonce = match.group(1).decode()
            malformed = (
                f"<<<AGENT-PHASE-RESULT {nonce}>>>\n"
                "{\n"
                '  "run_id": "developer-ux-nd/sanitized",\n'
                '  "stage": "closeout",\n'
                '  "phase_type": "implementation_testing",\n'
                '  "primary_disposition": "QUALIFIED",\n'
                '  "status": "QUALIFIED"\n'
                "}\n"
                "<<<ND-DEVUX63-CONSERVE-CLAUDE-COMPLETE>>>\n"
            ).encode()
            return result._replace(stdout=malformed)
        if index == 5:
            repaired = (
                closeout_payload(prompt, body="formatting-only repair")
                if self.repair_succeeds
                else b"formatter returned prose"
            )
            return result._replace(stdout=repaired)
        return result


def test_attached_malformed_closeout_gets_one_detached_same_provider_repair(
    repository: Path, tmp_path: Path
) -> None:
    runner = FormattingRepairRunner(repository)
    request = PhaseRequest(
        "implementation_testing",
        "claude_only",
        "UNIQUE_TASK_CONTEXT\nEnd exactly with:\n<<<CUSTOM-TASK-END>>>",
    )
    dispatcher = make_dispatcher(repository, tmp_path, runner)

    state = dispatcher.dispatch(PHASE_ID, request)

    assert state["complete"] is True
    assert state["completion_kind"] == "published"
    assert state["phase_owned_paths"] == ["phase.txt"]
    assert state["phase_delta"] == [{"status": "A", "path": "phase.txt"}]
    assert state["auxiliary_provider_invocations_performed"] == 1
    assert state["result_repair"]["source_result_blocker"] == "RESULT_MISSING_FENCE"
    assert state["terminal_transport"]["stage"] == "closeout"
    assert state["result_repair_transport"]["stage"] == "result_repair"
    assert state["stages_invoked"] == STAGE_ORDER
    assert state["stage_transports_completed"] == STAGE_ORDER
    assert state["terminal_result_validated"] is True
    assert state["stages_completed"] == STAGE_ORDER
    assert state["finalization_attempted"] is True
    assert len(runner.calls) == 6
    terminal_meta = artifact(tmp_path, "05-closeout.meta.json")
    repair_meta = artifact(tmp_path, "result-repair.meta.json")
    assert (repair_meta["provider"], repair_meta["profile"]) == (
        terminal_meta["provider"], terminal_meta["profile"]
    )
    assert repair_meta["invocation_kind"] == "auxiliary_result_repair"
    terminal_prompt = runner.calls[4]["prompt"]
    assert terminal_prompt.rstrip().endswith(
        re.search(
            rb"<<<END-AGENT-PHASE-RESULT [0-9a-f]{32}>>>", terminal_prompt
        ).group(0)
    )
    assert terminal_prompt.index(b"<<<CUSTOM-TASK-END>>>") < terminal_prompt.index(
        b"Earlier task and prior material"
    )
    repair_prompt = runner.calls[5]["prompt"]
    assert b"UNIQUE_TASK_CONTEXT" not in repair_prompt
    assert b"developer-ux-nd/sanitized" in repair_prompt
    assert repair_prompt.index(
        b"<<<ND-DEVUX63-CONSERVE-CLAUDE-COMPLETE>>>"
    ) < repair_prompt.index(
        b"The nonce-bound dispatcher contract below is the only active output instruction"
    )
    assert re.search(
        rb"<<<END-AGENT-PHASE-RESULT [0-9a-f]{32}>>>$", repair_prompt
    ) is not None
    assert runner.calls[5]["cwd"] != repository
    assert not Path(runner.calls[5]["cwd"]).exists()


def test_terminal_revision_paths_remain_distinct_from_full_phase_delta(
    repository: Path, tmp_path: Path
) -> None:
    def mutate(index: int) -> None:
        if index == 2:
            (repository / "work.txt").write_text("work\n")
        if index == 4:
            (repository / "closeout.txt").write_text("closeout revision\n")

    state = make_dispatcher(
        repository, tmp_path, FakeRunner(on_stage=mutate)
    ).dispatch(PHASE_ID, REQUEST)

    assert state["complete"] is True
    assert state["phase_owned_paths"] == ["closeout.txt", "work.txt"]
    assert state["revision_paths"] == ["closeout.txt"]
    assert state["closeout_delta"]["paths"] == ["closeout.txt"]


def test_failed_inline_repair_is_one_shot_and_preserves_delta_in_archive(
    repository: Path, tmp_path: Path
) -> None:
    runner = FormattingRepairRunner(repository, repair_succeeds=False)
    dispatcher = make_dispatcher(repository, tmp_path, runner)

    with pytest.raises(DispatchError) as caught:
        dispatcher.dispatch(PHASE_ID, REQUEST)

    assert caught.value.code == "RESULT_MISSING_FENCE"
    assert len(runner.calls) == 6
    state = state_of(dispatcher, tmp_path)
    result = artifact(tmp_path, "result.json")
    assert state["phase_owned_paths"] == ["phase.txt"]
    assert state["phase_delta"] == [{"status": "A", "path": "phase.txt"}]
    assert state["result_repair"]["source_result_blocker"] == "RESULT_MISSING_FENCE"
    assert state["stages_invoked"] == STAGE_ORDER
    assert state["stage_transports_completed"] == STAGE_ORDER
    assert state["terminal_result_validated"] is False
    assert state["stages_completed"] == STAGE_ORDER[:4]
    assert state["terminal_transport"]["validated"] is True
    assert state["result_repair_transport"]["validated"] is True
    assert result["phase_owned_paths"] == state["phase_owned_paths"]
    assert result["phase_delta"] == state["phase_delta"]
    assert result["terminal_transport"] == state["terminal_transport"]
    assert result["result_repair_transport"] == state["result_repair_transport"]
    assert result["stages_invoked"] == STAGE_ORDER
    assert result["stage_transports_completed"] == STAGE_ORDER
    assert result["terminal_result_validated"] is False
    assert result["stages_completed"] == STAGE_ORDER[:4]
    assert state["finalization_attempted"] is False
    markdown = Path(state["run_directory"]).joinpath("result.md").read_text()
    assert "- stages completed: 4 of 5" in markdown
    assert "- phase delta: 1 path(s)" in markdown
    assert "- phase-owned paths: 1" in markdown
    assert "- finalization attempted: **False**" in markdown
    archive = Path(state["archive"]["path"])
    with zipfile.ZipFile(archive) as bundle:
        prefix = f"{Path(state['run_directory']).name}/"
        archived_state = json.loads(bundle.read(prefix + "state.json"))
        archived_result = json.loads(bundle.read(prefix + "result.json"))
        archived_markdown = bundle.read(prefix + "result.md").decode()
    assert archived_state["phase_delta"] == state["phase_delta"]
    assert archived_state["stages_completed"] == STAGE_ORDER[:-1]
    assert archived_state["stage_transports_completed"] == STAGE_ORDER
    assert archived_state["terminal_result_validated"] is False
    assert archived_result["phase_delta"] == result["phase_delta"]
    assert archived_result["stages_completed"] == STAGE_ORDER[:-1]
    assert archived_result["stage_transports_completed"] == STAGE_ORDER
    assert archived_result["terminal_result_validated"] is False
    assert archived_markdown == markdown


def test_transport_noise_around_the_fence_is_tolerated(
    repository: Path, tmp_path: Path
) -> None:
    """Provider CLIs frame their own output; only the fenced bytes are parsed."""
    runner = FakeRunner(on_stage=writing(repository, "new.txt", "phase\n"))
    inner: dict[str, bytes] = {}

    def noisy(argv, prompt, cwd, max_output, on_output=None):
        result = FakeRunner.__call__(runner, argv, prompt, cwd, max_output, on_output)
        if len(runner.calls) == 5:
            inner["payload"] = result.stdout
            noise = b"OpenAI Codex v0.147.0\n--------\nworkdir: /x\n"
            return result._replace(stdout=noise + result.stdout + b"\ntokens used: 12\n")
        return result

    dispatcher = make_dispatcher(repository, tmp_path, runner)
    dispatcher.runner = noisy
    state = dispatcher.dispatch(PHASE_ID, REQUEST)

    assert state["complete"] is True
    assert state["commit"] is not None


# -- Case B: provider completes but never writes .git ------------------------


def test_dispatcher_commits_what_the_sandboxed_provider_could_not(
    repository: Path, tmp_path: Path
) -> None:
    runner = FakeRunner(on_stage=writing(repository, "new.txt", "phase work\n"))
    dispatcher = make_dispatcher(repository, tmp_path, runner)
    before = head(repository)

    state = dispatcher.dispatch(PHASE_ID, REQUEST)

    assert state["complete"] is True
    assert state["outcome"] == "completed"
    assert state["blocking_reason"] is None
    after = head(repository)
    assert after != before
    assert state["final_head"] == after
    assert state["commit"]["sha"] == after
    assert state["commit"]["subject"] == "Apply phase changes"
    # Exactly one new commit, entry HEAD is its parent.
    parent = subprocess.run(
        ["git", "rev-parse", "HEAD^"], cwd=repository, capture_output=True, check=True
    ).stdout.decode().strip()
    assert parent == before
    assert [change["path"] for change in state["phase_delta"]] == ["new.txt"]
    # Clean entry means successful exit implies a clean worktree.
    assert status(repository) == ""


def test_committed_tree_contains_exactly_the_phase_delta(
    repository: Path, tmp_path: Path
) -> None:
    def hook(index: int) -> None:
        if index == 2:
            (repository / "added.txt").write_text("added\n")
            (repository / "file.txt").write_text("modified\n")
            (repository / "gone.txt").unlink()

    (repository / "gone.txt").write_text("delete me\n")
    git(repository, "add", "gone.txt")
    git(repository, "commit", "-q", "-m", "add gone.txt")

    class ResolvedDeletionRunner(FakeRunner):
        def __call__(self, argv, prompt, *args, **kwargs):
            response = super().__call__(argv, prompt, *args, **kwargs)
            if len(self.calls) == 5:
                challenge_ids = re.findall(rb'"challenge_id"\s*:\s*"(ownch1-[0-9a-f]{64})"', prompt)
                assert len(challenge_ids) == 1
                lines = response.stdout.splitlines()
                payload = json.loads(lines[1])
                payload['ownership_resolutions'] = [{'challenge_id': challenge_ids[0].decode(),
                                                     'decision': 'phase_owned'}]
                lines[1] = json.dumps(payload).encode()
                response = response._replace(stdout=b'\n'.join(lines) + b'\n')
            return response

    runner = ResolvedDeletionRunner(on_stage=hook)
    dispatcher = make_dispatcher(repository, tmp_path, runner)
    state = dispatcher.dispatch(PHASE_ID, REQUEST)

    assert state["complete"] is True
    delta = {change["path"]: change["status"] for change in state["phase_delta"]}
    assert delta == {"added.txt": "A", "file.txt": "M", "gone.txt": "D"}
    names = subprocess.run(
        ["git", "diff-tree", "-r", "--name-only", "--no-commit-id", "HEAD^", "HEAD"],
        cwd=repository, capture_output=True, check=True,
    ).stdout.decode().split()
    assert sorted(names) == ["added.txt", "file.txt", "gone.txt"]
    assert status(repository) == ""


# -- Case C: git transport failure must not yield a false success ------------


def test_commit_transport_failure_blocks_and_preserves_the_worktree(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = FakeRunner(on_stage=writing(repository, "new.txt", "phase work\n"))
    dispatcher = make_dispatcher(repository, tmp_path, runner)
    before = head(repository)

    def refuse(root, paths, message):
        raise gitstate_module.GitStateError(
            "GIT_COMMIT_FAILED",
            "fatal: Unable to create '.git/index.lock': Operation not permitted",
        )

    monkeypatch.setattr(gitstate_module, "commit", refuse)

    with pytest.raises(DispatchError) as caught:
        dispatcher.dispatch(PHASE_ID, REQUEST)

    assert caught.value.code == "GIT_COMMIT_FAILED"
    state = state_of(dispatcher, tmp_path)
    assert state["complete"] is False
    assert state["commit"] is None
    assert head(repository) == before
    assert "new.txt" in status(repository)


def test_content_drift_between_candidate_and_commit_is_caught(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A worktree write between final-tree capture and staging must not commit."""
    runner = FakeRunner(on_stage=writing(repository, "new.txt", "phase work\n"))
    dispatcher = make_dispatcher(repository, tmp_path, runner)
    real_commit = gitstate_module.commit

    def drift(root, paths, message):
        (repository / "new.txt").write_text("something else entirely\n")
        return real_commit(root, paths, message)

    monkeypatch.setattr(gitstate_module, "commit", drift)

    with pytest.raises(DispatchError) as caught:
        dispatcher.dispatch(PHASE_ID, REQUEST)

    assert caught.value.code == "COMMIT_CONTENT_DRIFT"
    state = state_of(dispatcher, tmp_path)
    assert state["complete"] is False
    # HEAD moved, so the record must carry the sha rather than claim none.
    assert state["commit"]["sha"] == head(repository)


# -- Case D: unrelated operator dirt is preserved ----------------------------


def test_unstaged_operator_change_is_preserved_and_not_committed(
    repository: Path, tmp_path: Path
) -> None:
    (repository / "file.txt").write_text("operator edit\n")
    operator_bytes = (repository / "file.txt").read_bytes()

    runner = FakeRunner(on_stage=writing(repository, "phase.txt", "phase work\n"))
    dispatcher = make_dispatcher(repository, tmp_path, runner)
    state = dispatcher.dispatch(PHASE_ID, REQUEST)

    assert state["complete"] is True
    assert [change["path"] for change in state["phase_delta"]] == ["phase.txt"]
    names = subprocess.run(
        ["git", "diff-tree", "-r", "--name-only", "--no-commit-id", "HEAD^", "HEAD"],
        cwd=repository, capture_output=True, check=True,
    ).stdout.decode().split()
    assert names == ["phase.txt"]
    assert (repository / "file.txt").read_bytes() == operator_bytes
    assert status(repository) == " M file.txt\n"


def test_untracked_operator_file_is_preserved_and_not_committed(
    repository: Path, tmp_path: Path
) -> None:
    (repository / "operator-notes.md").write_text("scratch\n")
    operator_bytes = (repository / "operator-notes.md").read_bytes()

    runner = FakeRunner(on_stage=writing(repository, "phase.txt", "phase work\n"))
    dispatcher = make_dispatcher(repository, tmp_path, runner)
    state = dispatcher.dispatch(PHASE_ID, REQUEST)

    assert state["complete"] is True
    assert [change["path"] for change in state["phase_delta"]] == ["phase.txt"]
    assert (repository / "operator-notes.md").read_bytes() == operator_bytes
    assert status(repository) == "?? operator-notes.md\n"


# -- Case E: overlap between operator dirt and phase work --------------------


def test_overlap_with_entry_dirt_preserves_candidate_for_manager_disposition(
    repository: Path, tmp_path: Path
) -> None:
    (repository / "file.txt").write_text("operator edit\n")

    runner = FakeRunner(on_stage=writing(repository, "file.txt", "phase edit\n"))
    dispatcher = make_dispatcher(repository, tmp_path, runner)
    before = head(repository)

    state = dispatcher.dispatch(PHASE_ID, REQUEST)

    assert state["complete"] is True
    assert state["outcome"] == "completed"
    assert state["manager_disposition_required"] is True
    assert state["manager_disposition"]["reason"] == "entry_dirt_overlap"
    assert state["manager_disposition"]["paths"] == ["file.txt"]
    assert state["repository_finalized"] is False
    assert state["completion_kind"] == "candidate_requires_manager_disposition"
    assert state["commit"] is None
    assert head(repository) == before
    assert (repository / "file.txt").read_text() == "phase edit\n"


# -- Case F: pre-staged entry state is out of V1 scope -----------------------


def test_staged_entry_refuses_before_any_provider_invocation(
    repository: Path, tmp_path: Path
) -> None:
    (repository / "file.txt").write_text("operator staged\n")
    git(repository, "add", "file.txt")
    staged_bytes = (repository / "file.txt").read_bytes()
    before = head(repository)
    index_before = (repository / ".git/index").read_bytes()

    runner = FakeRunner()
    dispatcher = make_dispatcher(repository, tmp_path, runner)

    with pytest.raises(gitstate_module.GitStateError) as caught:
        dispatcher.dispatch(PHASE_ID, REQUEST)

    assert caught.value.code == "ENTRY_STAGED_CHANGES"
    assert runner.calls == []
    assert head(repository) == before
    assert (repository / ".git/index").read_bytes() == index_before
    assert (repository / "file.txt").read_bytes() == staged_bytes
    assert not (tmp_path / "runs").exists()


def test_unborn_head_refuses_with_a_typed_reason(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    git(empty, "init", "-q")
    runner = FakeRunner()
    dispatcher = Dispatcher(
        root=ROOT, cwd=empty, run_root=tmp_path / "runs",
        claude_launcher="/fake/claude-profile", scanner_executable=None,
        resolve_scanner=False, runner=runner,
    )
    with pytest.raises(gitstate_module.GitStateError) as caught:
        dispatcher.dispatch(PHASE_ID, REQUEST)
    assert caught.value.code == "ENTRY_UNBORN_HEAD"
    assert runner.calls == []


# -- Case G: a phase that changed nothing ------------------------------------


def test_no_change_phase_completes_without_an_empty_commit(
    repository: Path, tmp_path: Path
) -> None:
    runner = FakeRunner(closeout_subject=None)
    dispatcher = make_dispatcher(repository, tmp_path, runner)
    before = head(repository)

    state = dispatcher.dispatch(PHASE_ID, REQUEST)

    assert state["complete"] is True
    assert state["phase_delta"] == []
    assert state["commit"] is None
    assert head(repository) == before
    assert status(repository) == ""


def test_no_change_phase_preserves_entry_dirt(
    repository: Path, tmp_path: Path
) -> None:
    (repository / "file.txt").write_text("operator edit\n")
    runner = FakeRunner(closeout_subject=None)
    dispatcher = make_dispatcher(repository, tmp_path, runner)

    state = dispatcher.dispatch(PHASE_ID, REQUEST)

    assert state["complete"] is True
    assert state["phase_delta"] == []
    assert status(repository) == " M file.txt\n"


def test_delta_without_a_proposed_message_blocks(
    repository: Path, tmp_path: Path
) -> None:
    runner = FakeRunner(
        closeout_subject=None, on_stage=writing(repository, "new.txt", "phase\n")
    )
    dispatcher = make_dispatcher(repository, tmp_path, runner)

    with pytest.raises(DispatchError) as caught:
        dispatcher.dispatch(PHASE_ID, REQUEST)

    assert caught.value.code == "COMMIT_MESSAGE_MISSING"
    assert state_of(dispatcher, tmp_path)["complete"] is False


# -- Authority boundary ------------------------------------------------------


def test_closeout_envelope_never_asks_the_provider_to_commit(
    repository: Path, tmp_path: Path
) -> None:
    runner = FakeRunner()
    dispatcher = make_dispatcher(repository, tmp_path, runner)
    dispatcher.dispatch(PHASE_ID, REQUEST)
    prompt = runner.calls[4]["prompt"].decode()
    collapsed = " ".join(prompt.split())

    assert "Do not stage, commit, or push" in prompt
    assert "The dispatcher owns the local commit" in prompt
    assert "`body` may truthfully report actions you performed or omitted" in collapsed
    assert (
        "When discussing dispatcher-owned work, distinguish your provider-local "
        "action from the final dispatcher outcome" in collapsed
    )
    assert (
        "`commit_message` describes repository scope, result, and verification only"
        in collapsed
    )
    assert (
        "must not claim that dispatcher-owned staging, commit creation, "
        "configured-upstream publication, live push verification, or archive "
        "finalization did or did not occur" in collapsed
    )
    assert (
        "Final Git publication and archive truth belongs to the dispatcher's "
        "`result.json` and `result.md`" in collapsed
    )
    # The instruction that caused the bug is gone, not merely softened.
    assert "Perform task-authorized local commit" not in prompt
    # git add / git commit / git push appear only inside the prohibition sentence.
    assert (
        "Do not run `git add`, `git commit`, `git push`, or any other "
        "git-metadata mutation" in collapsed
    )
    assert collapsed.count("`git add`") == 1
    assert collapsed.count("`git commit`") == 1


def test_result_artifact_is_written_on_success_and_on_failure(
    repository: Path, tmp_path: Path
) -> None:
    runner = FakeRunner(on_stage=writing(repository, "new.txt", "phase\n"))
    dispatcher = make_dispatcher(repository, tmp_path, runner)
    state = dispatcher.dispatch(PHASE_ID, REQUEST)
    directory = Path(state["run_directory"])
    result = json.loads((directory / "result.json").read_text())
    assert result["outcome"] == "completed"
    assert result["complete"] is True
    assert result["entry_head"] != result["final_head"]
    assert result["review_count"] == 2
    assert result["review_outcomes"] == {
        "plan_review": "reviewed_with_no_findings",
        "final_review": "reviewed_with_no_findings",
    }
    assert result["final_review"] == "reviewed_with_no_findings"
    assert [item["name"] for item in result["review_artifacts"]] == [
        "02-plan-review.result.json", "04-final-review.result.json",
    ]
    assert result["review_artifact_outcomes"] == {
        "plan_review": "reviewed_with_no_findings",
        "final_review": "reviewed_with_no_findings",
    }
    assert result["planner_proposal"]["binding"] == result["proposal_binding"]
    assert result["planner_proposal"]["implementation_authority"] is False
    assert result["producer_candidate"] == result["producer_binding"]
    assert result["work_review"]["name"] == "04-final-review.result.json"
    assert result["work_review"]["stage"] == "final_review"
    assert result["revisor_candidate"] == result["revisor_binding"]
    assert result["revisor_revision_paths"] == []
    assert result["authorized_revisor_revisions"] is None
    assert result["commit"]["sha"] == result["final_head"]
    assert result["task_artifacts_unverified"] is True
    markdown = (directory / "result.md").read_text()
    assert markdown.startswith("# Phase dispatch result")
    assert "review artifact outcomes:" in markdown
    assert "`02-plan-review.result.json`: reviewed_with_no_findings" in markdown
    assert "`04-final-review.result.json`: reviewed_with_no_findings" in markdown
    assert "automatic post-revisor independent review: none" in markdown

    blocked_runner = FakeRunner(
        closeout_outcome="blocked", on_stage=writing(repository, "other.txt", "x\n")
    )
    blocked = Dispatcher(
        root=ROOT, cwd=repository, run_root=tmp_path / "blocked-runs",
        codex_executable="/fake/codex", claude_launcher="/fake/claude-profile",
        scanner_executable=None, resolve_scanner=False, runner=blocked_runner,
    )
    with pytest.raises(DispatchError):
        blocked.dispatch(PHASE_ID, REQUEST)
    failure = artifact(tmp_path, "result.json", "blocked-runs")
    assert failure["complete"] is False
    assert failure["blocking_reason"]["code"] == "PROVIDER_OUTCOME_BLOCKED"


def test_result_artifact_is_written_when_an_early_stage_fails(
    repository: Path, tmp_path: Path
) -> None:
    runner = FakeRunner(exit_codes={2: 3})
    dispatcher = make_dispatcher(repository, tmp_path, runner)
    with pytest.raises(DispatchError):
        dispatcher.dispatch(PHASE_ID, REQUEST)
    failure = artifact(tmp_path, "result.json")
    assert failure["complete"] is False
    assert failure["blocking_reason"]["code"] == "PROVIDER_TRANSPORT_FAILED"
    assert failure["commit"] is None


def test_phase_created_gitlink_is_refused_rather_than_committed(
    repository: Path, tmp_path: Path
) -> None:
    """An embedded repo created mid-phase has undefined delta semantics in V1."""
    def hook(index: int) -> None:
        if index == 2:
            nested = repository / "vendor"
            nested.mkdir()
            git(nested, "init", "-q")
            git(nested, "config", "user.email", "test@example.invalid")
            git(nested, "config", "user.name", "Test")
            (nested / "x.txt").write_text("nested\n")
            git(nested, "add", "x.txt")
            git(nested, "commit", "-q", "-m", "nested")

    runner = FakeRunner(on_stage=hook)
    dispatcher = make_dispatcher(repository, tmp_path, runner)
    before = head(repository)

    with pytest.raises(DispatchError) as caught:
        dispatcher.dispatch(PHASE_ID, REQUEST)

    assert caught.value.code == "DELTA_SUBMODULE_UNSUPPORTED"
    assert head(repository) == before
    assert state_of(dispatcher, tmp_path)["complete"] is False


def test_mid_run_candidate_failure_still_records_a_result(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A non-DispatchError failure must not leave an ambiguous artifact set."""
    from agent_phase import candidate as candidate_module

    runner = FakeRunner()
    dispatcher = make_dispatcher(repository, tmp_path, runner)
    real = candidate_module.tree_identity
    calls: list[int] = []

    def failing(cwd):
        calls.append(1)
        if len(calls) > 1:  # let the entry capture succeed, fail the pre-final one
            raise candidate_module.CandidateError("git write-tree produced no tree")
        return real(cwd)

    monkeypatch.setattr(candidate_module, "tree_identity", failing)

    with pytest.raises(candidate_module.CandidateError):
        dispatcher.dispatch(PHASE_ID, REQUEST)

    result = artifact(tmp_path, "result.json")
    assert result["complete"] is False
    assert result["outcome"] == "blocked"
    assert result["blocking_reason"]["code"] == "CandidateError"
    assert result["commit"] is None


# -- Strict result parsing ---------------------------------------------------


NONCE = "0" * 32


def fenced(payload: str, nonce: str = NONCE) -> bytes:
    return (
        f"<<<AGENT-PHASE-RESULT {nonce}>>>\n{payload}\n"
        f"<<<END-AGENT-PHASE-RESULT {nonce}>>>\n"
    ).encode("utf-8")


def valid(**overrides) -> dict:
    payload = {
        "version": 1,
        "stage": "closeout",
        "outcome": "completed",
        "body": "done",
        "commit_message": {"subject": "Add a thing", "body": ""},
    }
    payload.update(overrides)
    return {k: v for k, v in payload.items() if v is not ...}


def test_valid_result_round_trips() -> None:
    parsed = result_module.parse(fenced(json.dumps(valid())), "closeout", NONCE)
    assert parsed.outcome == "completed"
    assert parsed.commit_message.subject == "Add a thing"
    assert parsed.commit_message.render() == "Add a thing\n"


def test_commit_message_body_renders_after_a_blank_line() -> None:
    parsed = result_module.parse(
        fenced(json.dumps(valid(
            commit_message={"subject": "Add a thing", "body": "Why:\nBecause."}
        ))),
        "closeout", NONCE,
    )
    assert parsed.commit_message.render() == "Add a thing\n\nWhy:\nBecause.\n"


@pytest.mark.parametrize(
    "payload,code",
    [
        ('{"version": 2, "stage": "closeout", "outcome": "completed", '
         '"body": "", "commit_message": null}', "RESULT_VERSION"),
        ('{"version": 1, "stage": "work", "outcome": "completed", '
         '"body": "", "commit_message": null}', "RESULT_STAGE_MISMATCH"),
        ('{"version": 1, "stage": "closeout", "outcome": "done", '
         '"body": "", "commit_message": null}', "RESULT_OUTCOME"),
        ('{"version": 1, "version": 1, "stage": "closeout", '
         '"outcome": "completed", "body": "", "commit_message": null}',
         "RESULT_DUPLICATE_KEY"),
        ('not json at all', "RESULT_NOT_JSON"),
    ],
)
def test_malformed_results_are_rejected_with_typed_codes(
    payload: str, code: str
) -> None:
    with pytest.raises(result_module.ResultError) as caught:
        result_module.parse(fenced(payload), "closeout", NONCE)
    assert caught.value.code == code


def test_trailing_prose_inside_the_fence_is_rejected() -> None:
    body = json.dumps(valid()) + "\n\nAlso, I could not commit."
    with pytest.raises(result_module.ResultError) as caught:
        result_module.parse(fenced(body), "closeout", NONCE)
    assert caught.value.code == "RESULT_TRAILING_CONTENT"


def test_a_second_concatenated_object_is_rejected() -> None:
    body = json.dumps(valid()) + json.dumps(valid(outcome="blocked"))
    with pytest.raises(result_module.ResultError) as caught:
        result_module.parse(fenced(body), "closeout", NONCE)
    assert caught.value.code == "RESULT_TRAILING_CONTENT"


def test_a_second_fence_is_rejected() -> None:
    data = fenced(json.dumps(valid())) + fenced(json.dumps(valid(outcome="blocked")))
    with pytest.raises(result_module.ResultError) as caught:
        result_module.parse(data, "closeout", NONCE)
    assert caught.value.code == "RESULT_DUPLICATE_FENCE"


def test_a_foreign_nonce_does_not_satisfy_the_fence() -> None:
    with pytest.raises(result_module.ResultError) as caught:
        result_module.parse(fenced(json.dumps(valid()), "f" * 32), "closeout", NONCE)
    assert caught.value.code == "RESULT_MISSING_FENCE"


def test_invalid_utf8_inside_the_fence_is_rejected() -> None:
    data = (
        f"<<<AGENT-PHASE-RESULT {NONCE}>>>".encode()
        + b"\xff\xfe"
        + f"<<<END-AGENT-PHASE-RESULT {NONCE}>>>".encode()
    )
    with pytest.raises(result_module.ResultError) as caught:
        result_module.parse(data, "closeout", NONCE)
    assert caught.value.code == "RESULT_NOT_UTF8"


def test_oversized_result_is_rejected() -> None:
    huge = "x" * (result_module.MAX_RESULT_BYTES + 1)
    with pytest.raises(result_module.ResultError) as caught:
        result_module.parse(fenced(huge), "closeout", NONCE)
    assert caught.value.code == "RESULT_TOO_LARGE"


@pytest.mark.parametrize(
    "subject,code",
    [
        ("", "COMMIT_SUBJECT_EMPTY"),
        ("   ", "COMMIT_SUBJECT_EMPTY"),
        ("A" * 73, "COMMIT_SUBJECT_TOO_LONG"),
        ("Add a thing.", "COMMIT_SUBJECT_TRAILING_PERIOD"),
        ("Add a thing\nand more", "COMMIT_SUBJECT_MULTILINE"),
        (" Add a thing", "COMMIT_SUBJECT_WHITESPACE"),
        ("Add a\x00thing", "COMMIT_CONTROL_CHARACTER"),
    ],
)
def test_commit_subject_policy_is_enforced(subject: str, code: str) -> None:
    payload = json.dumps(valid(commit_message={"subject": subject, "body": ""}))
    with pytest.raises(result_module.ResultError) as caught:
        result_module.parse(fenced(payload), "closeout", NONCE)
    assert caught.value.code == code


def test_commit_subject_at_the_limit_is_accepted() -> None:
    subject = "A" * 72
    payload = json.dumps(valid(commit_message={"subject": subject, "body": ""}))
    parsed = result_module.parse(fenced(payload), "closeout", NONCE)
    assert parsed.commit_message.subject == subject


def test_overlong_commit_body_line_is_rejected() -> None:
    payload = json.dumps(
        valid(commit_message={"subject": "Add a thing", "body": "x" * 101})
    )
    with pytest.raises(result_module.ResultError) as caught:
        result_module.parse(fenced(payload), "closeout", NONCE)
    assert caught.value.code == "COMMIT_BODY_LINE_TOO_LONG"


@pytest.mark.parametrize(
    "commit_message",
    ["a string", {"subject": "Add a thing"}, {"subject": 1, "body": ""},
     {"subject": "Add a thing", "body": "", "extra": ""}],
)
def test_malformed_commit_message_shape_is_rejected(commit_message) -> None:
    payload = json.dumps(valid(commit_message=commit_message))
    with pytest.raises(result_module.ResultError) as caught:
        result_module.parse(fenced(payload), "closeout", NONCE)
    assert caught.value.code == "COMMIT_MESSAGE_SHAPE"


# -- Pathspec and delta edge cases -------------------------------------------


def test_glob_metacharacters_in_a_path_do_not_over_match(
    repository: Path, tmp_path: Path
) -> None:
    """A bare path is a glob to git; only the literal file may be committed."""
    (repository / "star[1].txt").write_text("bystander\n")
    git(repository, "add", "star[1].txt")
    git(repository, "commit", "-q", "-m", "add bracket file")

    def hook(index: int) -> None:
        if index == 2:
            (repository / "star[1].txt").write_text("phase edit\n")

    runner = FakeRunner(on_stage=hook)
    dispatcher = make_dispatcher(repository, tmp_path, runner)
    state = dispatcher.dispatch(PHASE_ID, REQUEST)

    assert state["complete"] is True
    assert [change["path"] for change in state["phase_delta"]] == ["star[1].txt"]
    assert status(repository) == ""


def test_phase_delta_is_not_git_diff_head(repository: Path, tmp_path: Path) -> None:
    """With operator dirt present the two differ, and only the delta is committed."""
    (repository / "file.txt").write_text("operator edit\n")
    entry = gitstate_module.capture_entry(repository)
    (repository / "phase.txt").write_text("phase\n")
    final = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repository, capture_output=True, check=True
    ).stdout.decode()
    # git diff HEAD would sweep in file.txt; the tree-to-tree delta does not.
    assert " M file.txt" in final
    from agent_phase import candidate as candidate_module

    after = candidate_module.tree_identity(repository)
    delta = gitstate_module.phase_delta(repository, entry.tree, str(after["tree"]))
    assert [change.path for change in delta] == ["phase.txt"]


def test_symlink_dirt_identity_tracks_the_link_text(
    repository: Path, tmp_path: Path
) -> None:
    link = repository / "link"
    link.symlink_to("file.txt")
    entry = gitstate_module.capture_entry(repository)
    assert entry.dirty["link"]["type"] == "symlink"
    link.unlink()
    link.symlink_to("other.txt")
    assert gitstate_module._identity(repository, "link") != entry.dirty["link"]


def test_valid_result_no_structured_authority_parses_unchanged() -> None:
    payload = valid()
    parsed = result_module.parse(fenced(json.dumps(payload)), "closeout", NONCE)
    assert parsed.completed is True
    assert parsed.path_dispositions == ()
    assert parsed.ownership_resolutions == ()


def test_valid_result_valid_path_dispositions_parses_unchanged() -> None:
    payload = valid(path_dispositions=[{"path": "file.txt", "disposition": "phase_owned"}])
    parsed = result_module.parse(fenced(json.dumps(payload)), "closeout", NONCE)
    assert parsed.completed is True
    assert parsed.path_dispositions == ({"path": "file.txt", "disposition": "phase_owned"},)


@pytest.mark.parametrize(
    "dispositions",
    [
        "not-a-list",
        [{"path": "missing_disposition.txt"}],
        [{"path": "invalid_disp.txt", "disposition": "unknown_disp"}],
        [{"path": "/absolute.txt", "disposition": "phase_owned"}],
    ],
)
def test_invalid_disposition_shape_raises_path_disposition_invalid(dispositions) -> None:
    payload = valid(path_dispositions=dispositions)
    with pytest.raises(result_module.ResultError) as caught:
        result_module.parse(fenced(json.dumps(payload)), "closeout", NONCE)
    assert caught.value.code == "PATH_DISPOSITION_INVALID"


def test_duplicate_disposition_path_and_keys_remain_authority_specific_invalid() -> None:
    # Duplicate path in disposition list
    payload = valid(
        path_dispositions=[
            {"path": "file.txt", "disposition": "phase_owned"},
            {"path": "file.txt", "disposition": "phase_owned"},
        ]
    )
    with pytest.raises(result_module.ResultError) as caught:
        result_module.parse(fenced(json.dumps(payload)), "closeout", NONCE)
    assert caught.value.code == "PATH_DISPOSITION_INVALID"

    # Duplicate key inside path disposition item
    raw_json = (
        '{"version": 1, "stage": "closeout", "outcome": "completed", '
        '"body": "", "commit_message": null, "path_dispositions": '
        '[{"path": "a.txt", "path": "b.txt", "disposition": "phase_owned"}]}'
    )
    with pytest.raises(result_module.ResultError) as caught:
        result_module.parse(fenced(raw_json), "closeout", NONCE)
    assert caught.value.code == "PATH_DISPOSITION_INVALID"

    # Duplicate top-level path_dispositions key
    raw_json = (
        '{"version": 1, "stage": "closeout", "outcome": "completed", '
        '"body": "", "commit_message": null, "path_dispositions": [], "path_dispositions": []}'
    )
    with pytest.raises(result_module.ResultError) as caught:
        result_module.parse(fenced(raw_json), "closeout", NONCE)
    assert caught.value.code == "PATH_DISPOSITION_INVALID"


def test_valid_dispositions_with_overlong_commit_body_retains_commit_body_code() -> None:
    payload = valid(
        commit_message={"subject": "Valid subject", "body": "x" * 101},
        path_dispositions=[{"path": "file.txt", "disposition": "phase_owned"}],
    )
    with pytest.raises(result_module.ResultError) as caught:
        result_module.parse(fenced(json.dumps(payload)), "closeout", NONCE)
    assert caught.value.code == "COMMIT_BODY_LINE_TOO_LONG"


@pytest.mark.parametrize(
    "override,expected_code",
    [
        ({"stage": "wrong_stage"}, "RESULT_STAGE_MISMATCH"),
        ({"version": 2}, "RESULT_VERSION"),
        ({"outcome": "invalid_outcome"}, "RESULT_OUTCOME"),
    ],
)
def test_valid_dispositions_with_unrelated_result_error_retains_core_code(
    override: dict, expected_code: str
) -> None:
    payload = valid(
        path_dispositions=[{"path": "file.txt", "disposition": "phase_owned"}],
        **override,
    )
    with pytest.raises(result_module.ResultError) as caught:
        result_module.parse(fenced(json.dumps(payload)), "closeout", NONCE)
    assert caught.value.code == expected_code


def test_valid_dispositions_with_duplicate_unrelated_key_retains_duplicate_key_code() -> None:
    raw_json = (
        '{"version": 1, "version": 1, "stage": "closeout", "outcome": "completed", '
        '"body": "", "commit_message": null, "path_dispositions": []}'
    )
    with pytest.raises(result_module.ResultError) as caught:
        result_module.parse(fenced(raw_json), "closeout", NONCE)
    assert caught.value.code == "RESULT_DUPLICATE_KEY"


def test_valid_ownership_resolutions_with_unrelated_error_retains_core_code() -> None:
    resolutions = [{"challenge_id": "ownch1-" + "0" * 64, "decision": "phase_owned"}]
    # Overlong commit body
    payload = valid(
        commit_message={"subject": "Valid subject", "body": "x" * 101},
        ownership_resolutions=resolutions,
    )
    with pytest.raises(result_module.ResultError) as caught:
        result_module.parse(fenced(json.dumps(payload)), "closeout", NONCE)
    assert caught.value.code == "COMMIT_BODY_LINE_TOO_LONG"

    # Stage mismatch
    payload = valid(stage="wrong_stage", ownership_resolutions=resolutions)
    with pytest.raises(result_module.ResultError) as caught:
        result_module.parse(fenced(json.dumps(payload)), "closeout", NONCE)
    assert caught.value.code == "RESULT_STAGE_MISMATCH"

    # Duplicate unrelated key
    raw_json = (
        '{"version": 1, "version": 1, "stage": "closeout", "outcome": "completed", '
        '"body": "", "commit_message": null, '
        '"ownership_resolutions": [{"challenge_id": "ownch1-' + '0' * 64 + '", "decision": "phase_owned"}]}'
    )
    with pytest.raises(result_module.ResultError) as caught:
        result_module.parse(fenced(raw_json), "closeout", NONCE)
    assert caught.value.code == "RESULT_DUPLICATE_KEY"


@pytest.mark.parametrize(
    "resolutions",
    [
        "not-a-list",
        [{"challenge_id": "bad_challenge_id", "decision": "phase_owned"}],
        [{"challenge_id": "ownch1-" + "0" * 64, "decision": "invalid_decision"}],
        [{"challenge_id": "ownch1-" + "0" * 64}],
    ],
)
def test_invalid_ownership_resolution_raises_resolution_invalid(resolutions) -> None:
    payload = valid(ownership_resolutions=resolutions)
    with pytest.raises(result_module.ResultError) as caught:
        result_module.parse(fenced(json.dumps(payload)), "closeout", NONCE)
    assert caught.value.code == "OWNERSHIP_PROVIDER_RESOLUTION_INVALID"


def test_duplicate_ownership_resolution_keys_remain_authority_specific_invalid() -> None:
    # Duplicate resolution in array
    payload = valid(
        ownership_resolutions=[
            {"challenge_id": "ownch1-" + "0" * 64, "decision": "phase_owned"},
            {"challenge_id": "ownch1-" + "0" * 64, "decision": "phase_owned"},
        ]
    )
    with pytest.raises(result_module.ResultError) as caught:
        result_module.parse(fenced(json.dumps(payload)), "closeout", NONCE)
    assert caught.value.code == "OWNERSHIP_PROVIDER_RESOLUTION_INVALID"

    # Duplicate resolution key in item
    raw_json = (
        '{"version": 1, "stage": "closeout", "outcome": "completed", "body": "", "commit_message": null, '
        '"ownership_resolutions": [{"challenge_id": "ownch1-' + '0' * 64 + '", '
        '"challenge_id": "ownch1-' + '0' * 64 + '", "decision": "phase_owned"}]}'
    )
    with pytest.raises(result_module.ResultError) as caught:
        result_module.parse(fenced(raw_json), "closeout", NONCE)
    assert caught.value.code == "OWNERSHIP_PROVIDER_RESOLUTION_INVALID"

    # Duplicate top-level ownership_resolutions key
    raw_json = (
        '{"version": 1, "stage": "closeout", "outcome": "completed", "body": "", "commit_message": null, '
        '"ownership_resolutions": [], "ownership_resolutions": []}'
    )
    with pytest.raises(result_module.ResultError) as caught:
        result_module.parse(fenced(raw_json), "closeout", NONCE)
    assert caught.value.code == "OWNERSHIP_PROVIDER_RESOLUTION_INVALID"


def test_closeout_result_contract_guidance_for_path_dispositions() -> None:
    from agent_phase.envelope import TERMINAL_RESULT_CONTRACT
    assert "Omitting `path_dispositions` is the normal case" in TERMINAL_RESULT_CONTRACT
    contract_normalized = " ".join(TERMINAL_RESULT_CONTRACT.split())
    assert "ordinary mechanically observed additions and modifications do not need `path_dispositions`" in contract_normalized
    assert "Do not enumerate every ordinary product path merely to restate mechanical ownership" in contract_normalized
    assert "raw `phase_owned` is not a substitute for OWNCHALLENGE1 exact-ID resolution" in contract_normalized
    assert "Exclusions use the closed exclusion dispositions" in contract_normalized
