from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import Any, Callable

import pytest

from agent_phase import candidate as candidate_module
from agent_phase import finalization as finalization_module
from agent_phase import gitstate as gitstate_module
from agent_phase import provider as provider_module
from agent_phase import result_repair as result_repair_module
from agent_phase import result_repair_authority as authority_module
from agent_phase.dispatch import DispatchError, Dispatcher
from agent_phase.cli import dispatch_main
from agent_phase.provider import Result
from agent_phase.request import PhaseRequest


ROOT = Path(__file__).resolve().parents[3]
PHASE = "RESULT-REPAIR1"
REQUEST = PhaseRequest(
    "implementation_testing",
    "gemini_only",
    "Produce the bounded implementation and verification.",
)
TERMINAL_STDOUT = (
    b"Implementation completed. Focused verification passed. "
    b"Proposed commit: Detach result repair.\n"
)


def git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    )
    return completed.stdout.strip()


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "user.name", "Test")
    (root / "base.txt").write_text("base\n")
    git(root, "add", "base.txt")
    git(root, "commit", "-q", "-m", "initial")
    return root


def _empty_text() -> dict[str, object]:
    return {
        "text": "",
        "utf8_bytes": 0,
        "sha256": hashlib.sha256(b"").hexdigest(),
        "truncated": False,
        "source": None,
    }


def write_antigravity_evidence(
    argv: list[str],
    exit_code: int = 0,
    *,
    completion_fence_observed: bool | None = None,
    transport_success: bool | None = None,
    protocol_error: str | None = None,
    protocol_error_after_fence: bool = False,
    is_error: bool | None = None,
    terminal_after_fence: bool = False,
    response_bytes: bytes | None = None,
) -> None:
    if "--evidence-prefix" not in argv:
        return
    prefix = Path(argv[argv.index("--evidence-prefix") + 1])
    summary = prefix.with_name(f"{prefix.name}.antigravity-terminal-result.json")
    empty = _empty_text()
    fence_obs = exit_code == 0 if completion_fence_observed is None else completion_fence_observed
    trans_succ = exit_code == 0 if transport_success is None else transport_success
    err_flag = is_error if is_error is not None else (exit_code != 0)
    resp_b = response_bytes if response_bytes is not None else (TERMINAL_STDOUT if exit_code == 0 else b"")
    summary.write_text(
        json.dumps({
            "schema": "antigravity-terminal-evidence-v3",
            "version": 3,
            "profile": argv[1],
            "model": argv[1],
            "reviewer": "--reviewer" in argv,
            "plan_mode": "--reviewer" in argv,
            "wrapper_exit_code": exit_code,
            "provider_record_observed": False,
            "terminal_result_observed": False,
            "terminal_record_kind": "no_terminal_event",
            "protocol_evidence_outcome": "no_terminal_event",
            "oversized_record_classification": None,
            "completion_fence_observed": fence_obs,
            "transport_success": trans_succ,
            "completion_fence_sequence": 1 if fence_obs else None,
            "terminal_result_sequence": 2 if terminal_after_fence else (1 if err_flag else None),
            "protocol_error_sequence": 2 if protocol_error_after_fence else (1 if protocol_error else None),
            "terminal_result_after_completion_fence": terminal_after_fence,
            "protocol_error_after_completion_fence": protocol_error_after_fence,
            "raw_result_artifact": None,
            "raw_result_absent_reason": "fake completion fence",
            "raw_result_bytes": 0,
            "raw_result_sha256": None,
            "response_present": bool(resp_b),
            "response_utf8_bytes": len(resp_b),
            "response_sha256": hashlib.sha256(resp_b).hexdigest(),
            "normalized_status": "error" if err_flag else "success",
            "raw_status": None,
            "is_error": err_flag,
            "is_incomplete": False,
            "child_started": True,
            "child_exit_code": exit_code,
            "protocol_error": protocol_error,
            "reason_fields": {
                key: dict(empty)
                for key in (
                    "error", "message", "reason", "cancel_reason",
                    "cancellation_reason", "finish_reason",
                    "termination_reason", "code", "error_code",
                )
            },
            "identifier_fields": {
                key: dict(empty)
                for key in (
                    "conversation_id", "request_id", "session_id",
                    "operation_id", "run_id", "turn_id",
                )
            },
            "preferred_reason": None,
        }) + "\n",
        encoding="utf-8",
    )
    summary.chmod(0o600)


def review_result(prompt: bytes) -> bytes:
    nonce = re.search(rb"<<<AGENT-REVIEW-RESULT ([0-9a-f]{32})>>>", prompt)
    stage = re.search(rb"^stage: ([a-z_]+)$", prompt, re.MULTILINE)
    assert nonce is not None and stage is not None
    token = nonce.group(1).decode()
    payload = json.dumps({
        "version": 1,
        "stage": stage.group(1).decode(),
        "outcome": "reviewed_with_no_findings",
        "body": "no findings",
    })
    return (
        f"<<<AGENT-REVIEW-RESULT {token}>>>\n{payload}\n"
        f"<<<END-AGENT-REVIEW-RESULT {token}>>>\n"
    ).encode()


def source_terminal_output(prompt: bytes, mode: str) -> bytes:
    match = re.search(rb"<<<AGENT-PHASE-RESULT ([0-9a-f]{32})>>>", prompt)
    assert match is not None
    nonce = match.group(1).decode()
    if mode == "missing":
        return TERMINAL_STDOUT
    if mode == "partial":
        return f"<<<AGENT-PHASE-RESULT {nonce}>>>\n{{".encode()
    if mode == "truncated_prefix_begin":
        return b"Implementation completed.\n<<<AGENT-PHASE-RESULT\n"
    if mode == "truncated_prefix_end":
        return b"Implementation completed.\n<<<END-AGENT-PHASE-RESULT\n"
    if mode == "truncated_prefix_short":
        return b"Implementation completed.\n<<<AGENT\n"
    if mode == "wrong_nonce":
        wrong = "0" * 32
        return (
            f"<<<AGENT-PHASE-RESULT {wrong}>>>\n{{}}\n"
            f"<<<END-AGENT-PHASE-RESULT {wrong}>>>\n"
        ).encode()
    if mode == "malformed":
        return (
            f"<<<AGENT-PHASE-RESULT {nonce}>>>\n{{bad json\n"
            f"<<<END-AGENT-PHASE-RESULT {nonce}>>>\n"
        ).encode()
    if mode == "attached":
        return (
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
    if mode == "overlong_commit_with_dispositions":
        payload = json.dumps({
            "version": 1,
            "stage": "closeout",
            "outcome": "completed",
            "body": "done",
            "commit_message": {"subject": "Valid subject", "body": "x" * 101},
            "path_dispositions": [{"path": "base.txt", "disposition": "phase_owned"}],
        })
        return f"<<<AGENT-PHASE-RESULT {nonce}>>>\n{payload}\n<<<END-AGENT-PHASE-RESULT {nonce}>>>\n".encode()
    if mode == "overlong_commit_with_resolutions":
        payload = json.dumps({
            "version": 1,
            "stage": "closeout",
            "outcome": "completed",
            "body": "done",
            "commit_message": {"subject": "Valid subject", "body": "x" * 101},
            "ownership_resolutions": [{"challenge_id": "ownch1-" + "0" * 64, "decision": "phase_owned"}],
        })
        return f"<<<AGENT-PHASE-RESULT {nonce}>>>\n{payload}\n<<<END-AGENT-PHASE-RESULT {nonce}>>>\n".encode()
    raise AssertionError(mode)


class SourceRunner:
    def __init__(self, terminal_mode: str = "missing") -> None:
        self.calls = 0
        self.terminal_mode = terminal_mode

    def __call__(self, argv, prompt, cwd, max_output, on_output=None):
        index = self.calls
        self.calls += 1
        if index in (1, 3):
            stdout = review_result(prompt)
        elif index == 4:
            stdout = source_terminal_output(prompt, self.terminal_mode)
        else:
            stdout = b"producer completed"
        write_antigravity_evidence(list(argv), response_bytes=stdout)
        now = time.time()
        return Result(0, stdout, b"", False, now, now)


class RepairRunner:
    def __init__(
        self,
        mode: str = "good",
        side_effect: bool = False,
        *,
        commit_subject: str | None = "Detach result repair",
        commit_body: str = "",
    ) -> None:
        self.mode = mode
        self.side_effect = side_effect
        self.commit_subject = commit_subject
        self.commit_body = commit_body
        self.calls: list[dict[str, object]] = []

    def __call__(self, argv, prompt, cwd, max_output, on_output=None):
        inventory = list(cwd.iterdir())
        self.calls.append({
            "argv": list(argv),
            "prompt": prompt,
            "cwd": cwd,
            "inventory": inventory,
        })
        assert "--reviewer" in argv
        assert inventory == []
        assert not (cwd / ".git").exists()
        if self.side_effect:
            (cwd / "unexpected.txt").write_text("side effect\n")
        matches = re.findall(rb"<<<AGENT-PHASE-RESULT ([0-9a-f]{32})>>>", prompt)
        assert matches
        nonce = matches[-1].decode()
        if self.mode == "missing":
            stdout = b"still prose"
        elif self.mode == "wrong_nonce":
            wrong = "f" * 32
            stdout = _repaired_block(wrong)
        elif self.mode == "malformed":
            stdout = (
                f"<<<AGENT-PHASE-RESULT {nonce}>>>\n{{bad\n"
                f"<<<END-AGENT-PHASE-RESULT {nonce}>>>\n"
            ).encode()
        else:
            stdout = _repaired_block(
                nonce, self.commit_subject, self.commit_body
            )
        write_antigravity_evidence(list(argv), response_bytes=stdout)
        now = time.time()
        return Result(0, stdout, b"", False, now, now)


class OrdinaryResumeRunner:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def __call__(self, argv, prompt, cwd, max_output, on_output=None):
        self.calls.append({"argv": list(argv), "prompt": prompt, "cwd": cwd})
        matches = re.findall(rb"<<<AGENT-PHASE-RESULT ([0-9a-f]{32})>>>", prompt)
        assert matches
        stdout = _repaired_block(matches[-1].decode())
        write_antigravity_evidence(list(argv), response_bytes=stdout)
        now = time.time()
        return Result(0, stdout, b"", False, now, now)


def _repaired_block(
    nonce: str,
    commit_subject: str | None = "Detach result repair",
    commit_body: str = "",
) -> bytes:
    commit_message = (
        None
        if commit_subject is None
        else {"subject": commit_subject, "body": commit_body}
    )
    payload = json.dumps({
        "version": 1,
        "stage": "closeout",
        "outcome": "completed",
        "body": "Reformatted retained terminal response; no semantic work replayed.",
        "commit_message": commit_message,
    })
    return (
        f"<<<AGENT-PHASE-RESULT {nonce}>>>\n{payload}\n"
        f"<<<END-AGENT-PHASE-RESULT {nonce}>>>\n"
    ).encode()


def make_dispatcher(cwd: Path, run_root: Path, runner: Callable) -> Dispatcher:
    return Dispatcher(
        root=ROOT,
        cwd=cwd,
        run_root=run_root,
        codex_executable="/fake/codex",
        antigravity_launcher="/fake/antigravity-profile",
        scanner_executable=None,
        resolve_scanner=False,
        runner=runner,
    )


def only_run(run_root: Path) -> Path:
    states = list(run_root.rglob("state.json"))
    assert len(states) == 1
    return states[0].parent


def make_source(
    repository: Path,
    tmp_path: Path,
    terminal_mode: str = "missing",
    *,
    finalization_policy: str = "checkpoint",
) -> Path:
    root = tmp_path / f"source-{terminal_mode}"
    with pytest.raises(DispatchError):
        make_dispatcher(repository, root, SourceRunner(terminal_mode)).dispatch(
            PHASE,
            REQUEST,
            lifecycle="standard",
            finalization_policy=finalization_policy,
        )
    return only_run(root)


def repair(
    cwd: Path,
    tmp_path: Path,
    source: Path,
    runner: RepairRunner,
    *,
    from_stage: str = "result-repair",
    finalization_policy: str | None = "checkpoint",
    dry_run: bool = False,
    commit_subject: str | None = None,
    commit_body_file: Path | None = None,
) -> dict[str, object]:
    return make_dispatcher(cwd, tmp_path / "repair", runner).resume(
        PHASE,
        REQUEST,
        source,
        from_stage,
        lifecycle="standard",
        finalization_policy=finalization_policy,
        dry_run=dry_run,
        result_repair_commit_subject=commit_subject,
        result_repair_commit_body_file=commit_body_file,
    )


def test_operator_commit_body_file_is_bounded_strict_and_normalized(
    tmp_path: Path,
) -> None:
    body = tmp_path / "body.txt"
    body.write_text("First line\nSecond line\n", encoding="utf-8")

    authority = authority_module.load("Use operator message", body)

    assert authority is not None
    assert authority.message.subject == "Use operator message"
    assert authority.message.body == "First line\nSecond line"
    assert authority.as_record()["body_source"] == "bounded_body_file"


@pytest.mark.parametrize(
    ("kind", "code"),
    [
        ("missing", "RESULT_REPAIR_COMMIT_BODY_MISSING"),
        ("directory", "RESULT_REPAIR_COMMIT_BODY_TYPE"),
        ("symlink", "RESULT_REPAIR_COMMIT_BODY_SYMLINK"),
        ("oversized", "RESULT_REPAIR_COMMIT_BODY_OVERSIZED"),
        ("invalid_utf8", "RESULT_REPAIR_COMMIT_BODY_UTF8"),
    ],
)
def test_operator_commit_body_file_rejects_unsafe_inputs(
    tmp_path: Path, kind: str, code: str
) -> None:
    path = tmp_path / "body"
    if kind == "directory":
        path.mkdir()
    elif kind == "symlink":
        target = tmp_path / "target"
        target.write_text("body", encoding="utf-8")
        path.symlink_to(target)
    elif kind == "oversized":
        path.write_bytes(b"x" * (authority_module.MAX_COMMIT_BODY_FILE_BYTES + 1))
    elif kind == "invalid_utf8":
        path.write_bytes(b"\xff")

    with pytest.raises(finalization_module.FinalizationError) as caught:
        authority_module.load("Use operator message", path)

    assert caught.value.code == code


def test_operator_commit_body_file_replacement_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "body"
    path.write_text("body", encoding="utf-8")
    real_lstat = authority_module.os.lstat
    calls = 0

    def replaced_lstat(value):
        nonlocal calls
        calls += 1
        info = real_lstat(value)
        if calls == 1:
            return info
        values = list(info)
        values[8] = info.st_mtime + 1
        return authority_module.os.stat_result(values)

    monkeypatch.setattr(authority_module.os, "lstat", replaced_lstat)

    with pytest.raises(finalization_module.FinalizationError) as caught:
        authority_module.load("Use operator message", path)

    assert caught.value.code == "RESULT_REPAIR_COMMIT_BODY_REPLACED"


@pytest.mark.parametrize(
    "argv",
    [
        ["request.json", "--finalization", "publish"],
        [
            "request.json", "--resume", "run", "--from-stage", "auto",
            "--finalization", "publish",
        ],
        [
            "request.json", "--resume", "run", "--from-stage", "result-repair",
            "--finalization", "checkpoint",
        ],
        [
            "request.json", "--resume", "run", "--from-stage", "finalize",
            "--finalization", "publish",
        ],
    ],
)
def test_operator_commit_message_options_are_explicit_repair_only(
    argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as caught:
        dispatch_main(
            [
                *argv,
                "--result-repair-commit-subject",
                "Use operator message",
            ]
        )

    assert caught.value.code == 2
    assert "require --resume" in capsys.readouterr().err


@pytest.mark.parametrize("live_state", ["dirty", "advanced", "staged_and_unstaged"])
def test_explicit_result_repair_ignores_concurrent_live_repository_state(
    repository: Path, tmp_path: Path, live_state: str
) -> None:
    source = make_source(repository, tmp_path)
    if live_state == "dirty":
        (repository / "unrelated.txt").write_text("dirty\n")
    elif live_state == "advanced":
        (repository / "unrelated.txt").write_text("committed\n")
        git(repository, "add", "unrelated.txt")
        git(repository, "commit", "-q", "-m", "advance checkout")
    else:
        (repository / "base.txt").write_text("staged\n")
        git(repository, "add", "base.txt")
        (repository / "base.txt").write_text("unstaged\n")
        (repository / "untracked.txt").write_text("untracked\n")

    state = repair(repository, tmp_path, source, RepairRunner())

    assert state["completion_kind"] == "detached_result_repair_checkpoint"
    assert state["repository_binding"] == "none"
    assert state["repository_state_validated"] is False


def test_result_repair_succeeds_from_nonrepository_and_absent_original_checkout(
    repository: Path, tmp_path: Path
) -> None:
    source = make_source(repository, tmp_path)
    shutil.rmtree(repository)
    nonrepository = tmp_path / "nonrepository"
    nonrepository.mkdir()

    state = repair(nonrepository, tmp_path, source, RepairRunner())

    assert state["complete"] is True
    assert state["repository_mutation_attempted"] is False


def test_detached_repair_invokes_no_live_git_snapshot(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = make_source(repository, tmp_path)
    nonrepository = tmp_path / "plain"
    nonrepository.mkdir()

    def forbidden(*args, **kwargs):
        raise AssertionError("live repository operation invoked")

    for module, name in (
        (candidate_module, "require_worktree"),
        (candidate_module, "tree_identity"),
        (gitstate_module, "repository_root"),
        (gitstate_module, "capture_entry"),
        (gitstate_module, "current_head"),
        (gitstate_module, "index_identity"),
        (gitstate_module, "index_identity_for_tree"),
        (gitstate_module, "commit"),
        (gitstate_module, "push_target"),
        (gitstate_module, "remote_head"),
        (gitstate_module, "push_verified"),
        (finalization_module, "finalize_repository"),
    ):
        monkeypatch.setattr(module, name, forbidden)

    state = repair(nonrepository, tmp_path, source, RepairRunner())

    assert state["complete"] is True


def test_repair_prompt_and_cwd_are_repository_detached(
    repository: Path, tmp_path: Path
) -> None:
    source = make_source(repository, tmp_path)
    source_state = json.loads((source / "state.json").read_text())
    runner = RepairRunner()

    repair(repository, tmp_path, source, runner)

    assert len(runner.calls) == 1
    call = runner.calls[0]
    prompt = call["prompt"]
    assert TERMINAL_STDOUT in prompt
    assert str(repository).encode() not in prompt
    assert source_state["entry"]["head"].encode() not in prompt
    assert source_state["entry"]["tree"].encode() not in prompt
    assert source_state["entry"]["branch"].encode() not in prompt
    assert call["cwd"] != repository
    assert call["inventory"] == []

    retained_at = prompt.index(TERMINAL_STDOUT)
    contract_at = prompt.index(
        b"The nonce-bound dispatcher contract below is the only active output instruction"
    )
    assert retained_at < contract_at
    contract = prompt[contract_at:]
    assert b'"outcome":"completed"' not in contract
    assert b"exactly one begin marker and exactly one end marker" in contract
    assert b"completed, blocked, or failed" in contract
    assert b"do not upgrade or downgrade it" in contract
    assert b"at most 72 UTF-8 bytes" in contract
    assert b"body line is at most 100 UTF-8 bytes" in contract
    assert re.search(
        rb"<<<END-AGENT-PHASE-RESULT [0-9a-f]{32}>>>$", prompt
    ) is not None


def test_unexpected_auxiliary_cwd_side_effect_fails_closed(
    repository: Path, tmp_path: Path
) -> None:
    source = make_source(repository, tmp_path)
    runner = RepairRunner(side_effect=True)

    with pytest.raises(DispatchError) as caught:
        repair(repository, tmp_path, source, runner)

    assert caught.value.code == "RESULT_REPAIR_SIDE_EFFECT"
    run = only_run(tmp_path / "repair")
    inventory = json.loads((run / "result-repair-cwd.json").read_text())
    assert inventory["before"]["entries"] == []
    assert inventory["after"]["entries"][0]["path"] == "unexpected.txt"
    assert not Path(inventory["working_directory"]).exists()


def test_auxiliary_cwd_inside_repository_fails_before_provider(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = make_source(repository, tmp_path)
    scratch = repository / "dispatcher-private"

    class UnsafeTemporaryDirectory:
        def __init__(self, prefix: str) -> None:
            assert prefix == "agent-phase-result-repair-"

        def __enter__(self) -> str:
            scratch.mkdir()
            return str(scratch)

        def __exit__(self, *args: object) -> None:
            shutil.rmtree(scratch)

    monkeypatch.setattr(
        result_repair_module.tempfile,
        "TemporaryDirectory",
        UnsafeTemporaryDirectory,
    )
    runner = RepairRunner()

    with pytest.raises(DispatchError) as caught:
        repair(repository, tmp_path, source, runner)

    assert caught.value.code == "RESULT_REPAIR_WORKDIR_UNSAFE"
    assert runner.calls == []
    assert not scratch.exists()


@pytest.mark.parametrize("policy", ["commit-local", "publish"])
def test_noncheckpoint_policy_fails_before_provider(
    repository: Path, tmp_path: Path, policy: str
) -> None:
    source = make_source(repository, tmp_path)
    runner = RepairRunner()

    with pytest.raises(DispatchError) as caught:
        repair(repository, tmp_path, source, runner, finalization_policy=policy)

    assert caught.value.code == "RESULT_REPAIR_CHECKPOINT_REQUIRED"
    assert runner.calls == []
    assert not (tmp_path / "repair").exists()


def _publish_source_with_phase_delta(repository: Path, tmp_path: Path) -> Path:
    remote = tmp_path / "remote.git"
    subprocess.run(
        ["git", "init", "--bare", "-q", remote], capture_output=True, check=True
    )
    git(repository, "remote", "add", "origin", str(remote))
    git(repository, "push", "-q", "--set-upstream", "origin", "HEAD")

    class MutatingSourceRunner(SourceRunner):
        def __call__(self, argv, prompt, cwd, max_output, on_output=None):
            if self.calls == 2:
                (repository / "phase.txt").write_text("phase candidate\n")
            return super().__call__(argv, prompt, cwd, max_output, on_output)

    root = tmp_path / "publish-source"
    with pytest.raises(DispatchError):
        make_dispatcher(repository, root, MutatingSourceRunner("attached")).dispatch(
            PHASE, REQUEST, lifecycle="standard", finalization_policy="publish"
        )
    return only_run(root)


def test_explicit_result_repair_retains_publish_and_skips_semantic_replay(
    repository: Path, tmp_path: Path
) -> None:
    source = _publish_source_with_phase_delta(repository, tmp_path)
    source_state = json.loads((source / "state.json").read_text())
    assert source_state["phase_owned_paths"] == ["phase.txt"]
    retained_terminal_stdout = (source / "05-closeout.stdout.md").read_bytes()

    # A concurrent fast-forward commit on an unrelated path is admitted; the
    # retained phase path remains the candidate-scoped authority.
    (repository / "unrelated.txt").write_text("concurrent commit\n")
    git(repository, "add", "unrelated.txt")
    git(repository, "commit", "-q", "-m", "concurrent unrelated change")

    pre_provider_head = git(repository, "rev-parse", "HEAD")

    class ConcurrentRepairRunner(RepairRunner):
        def __call__(self, argv, prompt, cwd, max_output, on_output=None):
            (repository / "during-repair.txt").write_text("concurrent repair commit\n")
            git(repository, "add", "during-repair.txt")
            git(repository, "commit", "-q", "-m", "concurrent during repair")
            return super().__call__(argv, prompt, cwd, max_output, on_output)

    operator_subject = "Add composable Antigravity Doki-style controls"
    runner = ConcurrentRepairRunner(commit_subject=operator_subject)
    state = repair(
        repository,
        tmp_path,
        source,
        runner,
        finalization_policy="publish",
        commit_subject=operator_subject,
    )

    assert state["complete"] is True
    assert state["completion_kind"] == "published"
    assert state["repository_binding"] == "current"
    assert state["phase_owned_paths"] == ["phase.txt"]
    assert state["semantic_provider_invocations_performed"] == 0
    assert state["auxiliary_provider_invocations_performed"] == 1
    assert state["terminal_transport"] == source_state["terminal_transport"]
    assert state["result_repair_transport"]["stage"] == "result_repair"
    assert state["finalization_attempted"] is True
    assert state["proposed_commit_message"] == {
        "subject": operator_subject,
        "body": "",
    }
    assert state["commit_message_origin"]["origin"] == (
        "structured_operator_authority"
    )
    assert len(runner.calls) == 1
    prompt = runner.calls[0]["prompt"]
    assert prompt.index(retained_terminal_stdout) < prompt.index(
        operator_subject.encode("utf-8")
    )
    assert state["resume"]["resume_start_head"] == pre_provider_head
    assert state["resume"]["result_repair_post_provider_head"] != pre_provider_head
    entry_evidence = json.loads(
        Path(state["run_directory"]).joinpath("entry-evidence.json").read_text()
    )
    assert entry_evidence["pre_provider"]["head"] == pre_provider_head
    assert entry_evidence["post_provider"]["head"] == state["resume"][
        "result_repair_post_provider_head"
    ]
    branch = git(repository, "rev-parse", "--abbrev-ref", "HEAD")
    remote_head = git(repository, "ls-remote", "origin", f"refs/heads/{branch}").split()[0]
    assert git(repository, "rev-parse", "HEAD") == remote_head


@pytest.mark.parametrize(
    "formatter_subject",
    [None, "Use a different commit subject"],
)
def test_explicit_operator_commit_message_must_match_formatter_exactly(
    repository: Path,
    tmp_path: Path,
    formatter_subject: str | None,
) -> None:
    source = _publish_source_with_phase_delta(repository, tmp_path)
    runner = RepairRunner(commit_subject=formatter_subject)

    with pytest.raises(DispatchError) as caught:
        repair(
            repository,
            tmp_path,
            source,
            runner,
            finalization_policy="publish",
            commit_subject="Add composable Antigravity Doki-style controls",
        )

    assert caught.value.code == "RESULT_REPAIR_COMMIT_MESSAGE_MISMATCH"
    assert len(runner.calls) == 1


def test_no_operator_authority_never_synthesizes_a_missing_message(
    repository: Path, tmp_path: Path
) -> None:
    source = _publish_source_with_phase_delta(repository, tmp_path)
    retained = (source / "05-closeout.stdout.md").read_bytes()
    assert b"<<<ND-DEVUX63-CONSERVE-CLAUDE-COMPLETE>>>" in retained
    assert b"commit_message" not in retained
    runner = RepairRunner(commit_subject=None)

    with pytest.raises(DispatchError) as caught:
        repair(
            repository,
            tmp_path,
            source,
            runner,
            finalization_policy="publish",
        )

    assert caught.value.code == "COMMIT_MESSAGE_MISSING"
    assert len(runner.calls) == 1


def test_explicit_publish_repair_rejects_candidate_overlap_before_provider(
    repository: Path, tmp_path: Path
) -> None:
    source = _publish_source_with_phase_delta(repository, tmp_path)
    (repository / "phase.txt").write_text("conflicting operator bytes\n")
    runner = RepairRunner()

    with pytest.raises(DispatchError) as caught:
        repair(
            repository, tmp_path, source, runner, finalization_policy="publish"
        )

    assert caught.value.code == "RESULT_REPAIR_CANDIDATE_CONFLICT"
    assert runner.calls == []


@pytest.mark.parametrize("mode", ["missing", "wrong_nonce", "malformed"])
def test_repaired_result_remains_strict(
    repository: Path, tmp_path: Path, mode: str
) -> None:
    source = make_source(repository, tmp_path)

    with pytest.raises(DispatchError) as caught:
        repair(repository, tmp_path, source, RepairRunner(mode=mode))

    assert caught.value.code.startswith("RESULT_")


@pytest.mark.parametrize(
    "mode",
    [
        "partial",
        "truncated_prefix_begin",
        "truncated_prefix_end",
        "truncated_prefix_short",
        "wrong_nonce",
        "malformed",
        "attached",
    ],
)
def test_partial_or_malformed_source_results_are_repaired_once(
    repository: Path, tmp_path: Path, mode: str
) -> None:
    source = make_source(repository, tmp_path, mode)
    runner = RepairRunner()

    state = repair(repository, tmp_path, source, runner)

    assert state["complete"] is True
    assert state["result_repair"]["strict_parse_outcome"] == "parsed_completed"
    assert state["semantic_provider_invocations_performed"] == 0
    assert state["auxiliary_provider_invocations_performed"] == 1
    assert len(runner.calls) == 1


def test_result_repair_preserves_exact_lifecycle_aliases(
    repository: Path, tmp_path: Path
) -> None:
    source = make_source(repository, tmp_path, "partial")
    source_state = json.loads((source / "state.json").read_text())

    state = repair(repository, tmp_path, source, RepairRunner())

    for key in (
        "plan_candidate",
        "planner_proposal",
        "proposal_binding",
        "plan_proposal_binding",
        "producer_binding",
        "work_product_binding",
        "revisor_input",
        "review_artifacts",
        "review_artifact_names",
        "review_artifact_outcomes",
        "final_review",
    ):
        assert state[key] == source_state[key]
    assert state["terminal_bytes_verified"] is True


def _repack_source_zip(source: Path) -> None:
    """Build an explicit historical legacy fixture after editing its evidence."""
    from agent_phase.archive import receipt_path
    archive = source.parent / f"{source.name}.zip"
    for name in ("state.json", "result.json"):
        path = source / name
        record = json.loads(path.read_text())
        record["archive"].update(status="succeeded", succeeded=True, failure=None)
        record["archive"].pop("receipt_path", None)
        path.write_text(json.dumps(record) + "\n")
    receipt_path(archive).unlink(missing_ok=True)
    if archive.exists():
        archive.unlink()
    shutil.make_archive(str(source.parent / source.name), "zip", source.parent, source.name)


def _update_source_evidence(
    source: Path,
    update_fn: Callable[[dict[str, Any]], None],
    exit_code: int = 0,
) -> None:
    from agent_phase import antigravity_evidence as antigravity_evidence_module
    evidence_path = source / "05-closeout.antigravity-terminal-result.json"
    evidence_data = json.loads(evidence_path.read_text())
    update_fn(evidence_data)
    evidence_path.write_text(json.dumps(evidence_data) + "\n")
    resolved = json.loads((source / "resolved.json").read_text())
    terminal = resolved["stages"][resolved["terminal_result_stage"]]
    try:
        evidence = antigravity_evidence_module.validate(
            source,
            "05-closeout",
            terminal["profile"],
            terminal["intelligence"]["model"],
            False,
            exit_code,
        )
    except antigravity_evidence_module.EvidenceError as error:
        evidence = {
            "validation": "invalid",
            "detail": str(error),
            "original_wrapper_exit_code": exit_code,
        }
    meta_path = source / "05-closeout.meta.json"
    meta = json.loads(meta_path.read_text())
    meta["antigravity_evidence"] = evidence
    meta["exit_code"] = exit_code
    meta_path.write_text(json.dumps(meta) + "\n")
    state_path = source / "state.json"
    state = json.loads(state_path.read_text())
    state["provider_evidence"] = [{"stage": "closeout", **evidence}]
    state_path.write_text(json.dumps(state) + "\n")
    result_path = source / "result.json"
    result = json.loads(result_path.read_text())
    result["provider_evidence"] = [{"stage": "closeout", **evidence}]
    result_path.write_text(json.dumps(result) + "\n")
    _repack_source_zip(source)


def test_ineligible_no_completion_fence(repository: Path, tmp_path: Path) -> None:
    source = make_source(repository, tmp_path)
    def update(evidence: dict[str, Any]) -> None:
        evidence["completion_fence_observed"] = False
        evidence["completion_fence_sequence"] = None
        evidence["transport_success"] = False
    _update_source_evidence(source, update)

    runner = RepairRunner()
    with pytest.raises(DispatchError) as caught:
        repair(repository, tmp_path, source, runner)

    assert caught.value.code in ("RESULT_REPAIR_INELIGIBLE", "RESUME_ARTIFACT_MISMATCH")
    assert runner.calls == []


def test_ineligible_wrapper_nonzero(repository: Path, tmp_path: Path) -> None:
    source = make_source(repository, tmp_path)
    def update(evidence: dict[str, Any]) -> None:
        evidence["wrapper_exit_code"] = 1
        evidence["transport_success"] = False
    _update_source_evidence(source, update, exit_code=1)

    runner = RepairRunner()
    with pytest.raises(DispatchError) as caught:
        repair(repository, tmp_path, source, runner)

    assert caught.value.code in ("RESULT_REPAIR_INELIGIBLE", "RESUME_ARTIFACT_MISMATCH", "RESUME_STAGE_UNSATISFIED")
    assert runner.calls == []


def test_ineligible_pre_fence_provider_error(repository: Path, tmp_path: Path) -> None:
    source = make_source(repository, tmp_path)
    def update(evidence: dict[str, Any]) -> None:
        evidence["protocol_error"] = "malformed response before fence"
        evidence["protocol_error_sequence"] = 1
        evidence["completion_fence_sequence"] = 2
        evidence["protocol_error_after_completion_fence"] = False
        evidence["transport_success"] = False
    _update_source_evidence(source, update)

    runner = RepairRunner()
    with pytest.raises(DispatchError) as caught:
        repair(repository, tmp_path, source, runner)

    assert caught.value.code in ("RESULT_REPAIR_INELIGIBLE", "RESUME_ARTIFACT_MISMATCH")
    assert runner.calls == []


def test_unbounded_protocol_error_is_rejected_before_repair_provider(
    repository: Path, tmp_path: Path
) -> None:
    source = make_source(repository, tmp_path)

    def update(evidence: dict[str, Any]) -> None:
        evidence["protocol_error"] = "x" * 1025
        evidence["protocol_error_sequence"] = 1
        evidence["completion_fence_sequence"] = 2
        evidence["protocol_error_after_completion_fence"] = False
        evidence["transport_success"] = False

    _update_source_evidence(source, update)
    runner = RepairRunner()

    with pytest.raises(DispatchError) as caught:
        repair(repository, tmp_path, source, runner)

    assert caught.value.code == "RESUME_ARTIFACT_MISMATCH"
    assert runner.calls == []


def test_ineligible_transport_success_false(repository: Path, tmp_path: Path) -> None:
    source = make_source(repository, tmp_path)
    def update(evidence: dict[str, Any]) -> None:
        evidence["transport_success"] = False
    _update_source_evidence(source, update)

    runner = RepairRunner()
    with pytest.raises(DispatchError) as caught:
        repair(repository, tmp_path, source, runner)

    assert caught.value.code in ("RESULT_REPAIR_INELIGIBLE", "RESUME_ARTIFACT_MISMATCH")
    assert runner.calls == []


def test_ineligible_unbound_or_mismatched_evidence(repository: Path, tmp_path: Path) -> None:
    source = make_source(repository, tmp_path)
    def update(evidence: dict[str, Any]) -> None:
        evidence["response_sha256"] = "0" * 64
    _update_source_evidence(source, update)

    runner = RepairRunner()
    with pytest.raises(DispatchError) as caught:
        repair(repository, tmp_path, source, runner)

    assert caught.value.code == "RESUME_ARTIFACT_MISMATCH"
    assert runner.calls == []


def test_eligible_post_fence_nested_error_with_transport_success_true(
    repository: Path, tmp_path: Path
) -> None:
    source = make_source(repository, tmp_path)
    raw_event = json.dumps({
        "event": "result",
        "result": {
            "status": "ERROR",
            "response": TERMINAL_STDOUT.decode("utf-8"),
            "error": "late provider diagnostic after completion fence",
        },
    }, separators=(",", ":")).encode("utf-8")
    raw_path = source / "05-closeout.antigravity-terminal-result.raw.json"
    raw_path.write_bytes(raw_event)
    raw_path.chmod(0o600)

    def update(evidence: dict[str, Any]) -> None:
        evidence["is_error"] = True
        evidence["normalized_status"] = "error"
        evidence["raw_status"] = "ERROR"
        evidence["status_source"] = "result.status"
        evidence["response_source"] = "result.response"
        evidence["error_source"] = "result.error"
        evidence["reason_fields"]["error"]["text"] = "late provider diagnostic after completion fence"
        evidence["reason_fields"]["error"]["utf8_bytes"] = len(b"late provider diagnostic after completion fence")
        evidence["reason_fields"]["error"]["sha256"] = hashlib.sha256(b"late provider diagnostic after completion fence").hexdigest()
        evidence["reason_fields"]["error"]["source"] = "result.error"
        evidence["raw_result_artifact"] = raw_path.name
        evidence["raw_result_absent_reason"] = None
        evidence["raw_result_bytes"] = len(raw_event)
        evidence["raw_result_sha256"] = hashlib.sha256(raw_event).hexdigest()
        evidence["terminal_record_kind"] = "exact_raw_event"
        evidence["protocol_evidence_outcome"] = "exact_terminal_event_retained"
        evidence["provider_record_observed"] = True
        evidence["terminal_result_observed"] = True
        evidence["completion_fence_observed"] = True
        evidence["completion_fence_sequence"] = 1
        evidence["terminal_result_sequence"] = 2
        evidence["terminal_result_after_completion_fence"] = True
        evidence["transport_success"] = True
    _update_source_evidence(source, update)

    runner = RepairRunner()
    state = repair(repository, tmp_path, source, runner)

    assert state["complete"] is True
    assert state["outcome"] == "completed"


def test_accounting_successful_auxiliary_turn(repository: Path, tmp_path: Path) -> None:
    source = make_source(repository, tmp_path)
    state = repair(repository, tmp_path, source, RepairRunner())

    assert state["semantic_provider_invocations_inherited"] == 5
    assert state["semantic_provider_invocations_performed"] == 0
    assert state["provider_invocations_inherited"] == 5
    assert state["provider_invocations_performed"] == 0
    assert state["auxiliary_provider_invocations"] == 1
    assert state["auxiliary_provider_invocations_performed"] == 1
    assert state["provider_invocations_effective"] == 5
    assert state["total_effective_provider_turns"] == 6
    for key in (
        "provider_invocations_inherited",
        "provider_invocations_performed",
        "semantic_provider_invocations_inherited",
        "semantic_provider_invocations_performed",
        "auxiliary_provider_invocations",
        "auxiliary_provider_invocations_performed",
        "provider_invocations_effective",
        "total_effective_provider_turns",
    ):
        assert state["resume"][key] == state[key]

    run = Path(state["run_directory"])
    result = json.loads((run / "result.json").read_text())
    assert result["provider_invocations_effective"] == 5
    assert result["auxiliary_provider_invocations"] == 1
    assert result["auxiliary_provider_invocations_performed"] == 1
    assert result["total_effective_provider_turns"] == 6
    assert result["provider_exits"] == [
        {
            "stage": "result_repair",
            "exit_code": 0,
            "invocation_kind": "auxiliary_result_repair",
        }
    ]


def test_accounting_provider_nonzero(repository: Path, tmp_path: Path) -> None:
    source = make_source(repository, tmp_path)

    class NonzeroRunner(RepairRunner):
        def __call__(self, argv, prompt, cwd, max_output, on_output=None):
            super().__call__(argv, prompt, cwd, max_output, on_output)
            write_antigravity_evidence(list(argv), exit_code=1)
            now = time.time()
            return Result(1, b"error output", b"stderr", False, now, now)

    with pytest.raises(DispatchError) as caught:
        repair(repository, tmp_path, source, NonzeroRunner())

    assert caught.value.code == "PROVIDER_TRANSPORT_FAILED"
    run = only_run(tmp_path / "repair")
    state = json.loads((run / "state.json").read_text())
    result = json.loads((run / "result.json").read_text())
    assert state["semantic_provider_invocations_inherited"] == 5
    assert state["semantic_provider_invocations_performed"] == 0
    assert state["auxiliary_provider_invocations"] == 1
    assert state["auxiliary_provider_invocations_performed"] == 1
    assert state["provider_invocations_effective"] == 5
    assert state["total_effective_provider_turns"] == 6
    assert result["provider_invocations_effective"] == 5
    assert result["auxiliary_provider_invocations"] == 1
    assert result["total_effective_provider_turns"] == 6


def test_accounting_provider_interruption_after_launch(repository: Path, tmp_path: Path) -> None:
    source = make_source(repository, tmp_path)

    class InterruptedRunner(RepairRunner):
        def __call__(self, argv, prompt, cwd, max_output, on_output=None):
            super().__call__(argv, prompt, cwd, max_output, on_output)
            raise provider_module.ProviderInterrupted(b"partial", b"stderr", False, False)

    with pytest.raises(DispatchError) as caught:
        repair(repository, tmp_path, source, InterruptedRunner())

    assert caught.value.code == "OPERATOR_INTERRUPTED"
    run = only_run(tmp_path / "repair")
    state = json.loads((run / "state.json").read_text())
    result = json.loads((run / "result.json").read_text())
    assert state["semantic_provider_invocations_inherited"] == 5
    assert state["semantic_provider_invocations_performed"] == 0
    assert state["auxiliary_provider_invocations"] == 1
    assert state["auxiliary_provider_invocations_performed"] == 1
    assert state["provider_invocations_effective"] == 5
    assert state["total_effective_provider_turns"] == 6
    assert result["provider_invocations_effective"] == 5
    assert result["auxiliary_provider_invocations"] == 1
    assert result["total_effective_provider_turns"] == 6


def test_accounting_prompt_limit_failure_before_launch(repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = make_source(repository, tmp_path)

    def fail_prompt_limit(*args, **kwargs):
        raise result_repair_module.PromptLimitError("prompt too large")

    monkeypatch.setattr(result_repair_module, "ensure_prompt_fits", fail_prompt_limit)
    runner = RepairRunner()

    with pytest.raises(DispatchError) as caught:
        repair(repository, tmp_path, source, runner)

    assert caught.value.code == "PROVIDER_PROMPT_LIMIT"
    assert runner.calls == []
    run = only_run(tmp_path / "repair")
    state = json.loads((run / "state.json").read_text())
    result = json.loads((run / "result.json").read_text())
    assert state["semantic_provider_invocations_inherited"] == 5
    assert state["semantic_provider_invocations_performed"] == 0
    assert state["auxiliary_provider_invocations"] == 0
    assert state["auxiliary_provider_invocations_performed"] == 0
    assert state["provider_invocations_effective"] == 5
    assert state["total_effective_provider_turns"] == 5
    assert result["provider_invocations_effective"] == 5
    assert result["auxiliary_provider_invocations"] == 0
    assert result["total_effective_provider_turns"] == 5


def test_accounting_working_directory_safety_failure_before_launch(repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = make_source(repository, tmp_path)
    scratch = repository / "dispatcher-private-test"

    class UnsafeTempDir:
        def __enter__(self):
            scratch.mkdir(exist_ok=True)
            return str(scratch)

        def __exit__(self, *args):
            shutil.rmtree(scratch, ignore_errors=True)

    monkeypatch.setattr(result_repair_module.tempfile, "TemporaryDirectory", lambda **kw: UnsafeTempDir())
    runner = RepairRunner()

    with pytest.raises(DispatchError) as caught:
        repair(repository, tmp_path, source, runner)

    assert caught.value.code == "RESULT_REPAIR_WORKDIR_UNSAFE"
    assert runner.calls == []
    run = only_run(tmp_path / "repair")
    state = json.loads((run / "state.json").read_text())
    result = json.loads((run / "result.json").read_text())
    assert state["semantic_provider_invocations_inherited"] == 5
    assert state["semantic_provider_invocations_performed"] == 0
    assert state["auxiliary_provider_invocations"] == 0
    assert state["auxiliary_provider_invocations_performed"] == 0
    assert state["provider_invocations_effective"] == 5
    assert state["total_effective_provider_turns"] == 5
    assert result["provider_invocations_effective"] == 5
    assert result["auxiliary_provider_invocations"] == 0
    assert result["total_effective_provider_turns"] == 5


def test_accounting_side_effect_failure_after_launch(repository: Path, tmp_path: Path) -> None:
    source = make_source(repository, tmp_path)
    runner = RepairRunner(side_effect=True)

    with pytest.raises(DispatchError) as caught:
        repair(repository, tmp_path, source, runner)

    assert caught.value.code == "RESULT_REPAIR_SIDE_EFFECT"
    assert len(runner.calls) == 1
    run = only_run(tmp_path / "repair")
    state = json.loads((run / "state.json").read_text())
    result = json.loads((run / "result.json").read_text())
    assert state["semantic_provider_invocations_inherited"] == 5
    assert state["semantic_provider_invocations_performed"] == 0
    assert state["auxiliary_provider_invocations"] == 1
    assert state["auxiliary_provider_invocations_performed"] == 1
    assert state["provider_invocations_effective"] == 5
    assert state["total_effective_provider_turns"] == 6
    assert result["provider_invocations_effective"] == 5
    assert result["auxiliary_provider_invocations"] == 1
    assert result["total_effective_provider_turns"] == 6


@pytest.mark.parametrize(
    "relative",
    [
        "request.json",
        "resolved.json",
        "state.json",
        "result.json",
        "05-closeout.stdout.md",
        "05-closeout.antigravity-terminal-result.json",
    ],
)
def test_source_artifact_drift_fails_before_provider(
    repository: Path, tmp_path: Path, relative: str
) -> None:
    source = make_source(repository, tmp_path)
    path = source / relative
    path.write_bytes(path.read_bytes() + b"\n")
    runner = RepairRunner()

    with pytest.raises(DispatchError) as caught:
        repair(repository, tmp_path, source, runner)

    assert caught.value.code == "RESUME_ARTIFACT_MISMATCH"
    assert runner.calls == []


def test_source_archive_drift_fails_before_provider(
    repository: Path, tmp_path: Path
) -> None:
    source = make_source(repository, tmp_path)
    (source.parent / f"{source.name}.zip").write_bytes(b"not a zip")
    runner = RepairRunner()

    with pytest.raises(DispatchError) as caught:
        repair(repository, tmp_path, source, runner)

    assert caught.value.code == "RESUME_ARTIFACT_MISMATCH"
    assert runner.calls == []


def test_closeout_stage_route_change_routes_auxiliary_from_current_and_preserves_historical_effective_route(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = make_source(repository, tmp_path)
    real_resolve = result_repair_module.resolve

    def drifted(*args, **kwargs):
        value = real_resolve(*args, **kwargs)
        value["stages"]["closeout"]["profile"] = "drifted-profile"
        return value

    monkeypatch.setattr(result_repair_module, "resolve", drifted)
    runner = RepairRunner()

    state = repair(repository, tmp_path, source, runner, dry_run=True)

    assert state["outcome"] == "dry_run"
    assert state["effective_stage_routes"]["closeout"]["source"] == "inherited"
    assert state["effective_stage_routes"]["closeout"]["profile"] != "drifted-profile"
    assert state["route_transition"]["auxiliary_route"] is not None


def test_archive_exclusions_do_not_invalidate_source_repair(
    repository: Path, tmp_path: Path
) -> None:
    source = make_source(repository, tmp_path)
    (source / ".DS_Store").write_bytes(b"finder metadata")
    (source / "._state.json").write_bytes(b"appledouble metadata")
    metadata = source / "__MACOSX"
    metadata.mkdir()
    (metadata / "ignored").write_bytes(b"archive metadata")

    state = repair(repository, tmp_path, source, RepairRunner())

    assert state["complete"] is True
    assert state["source_archive_verified"] is True


def test_prompt_policy_records_versioned_exact_forwarding_exception(
    repository: Path, tmp_path: Path
) -> None:
    source = make_source(repository, tmp_path)

    state = repair(repository, tmp_path, source, RepairRunner())

    assert state["prompt_policy"] == {
        "policy_version": "git-current-state-v1",
        "applied": False,
        "reason": "exact_retained_terminal_stdout_required",
        "sanitized": False,
        "total_removal_count": 0,
        "evidence_artifact": None,
    }


def test_generic_repair_refuses_invalid_enclosing_result_with_path_authority(
    repository: Path, tmp_path: Path
) -> None:
    source = make_source(repository, tmp_path, "overlong_commit_with_dispositions")

    # Requirement 13 & 14: check source state/result/result.md blocker and attention reasons
    source_state = json.loads((source / "state.json").read_text())
    assert source_state["blocking_reason"]["code"] == "COMMIT_BODY_LINE_TOO_LONG"
    assert "path_ownership_invalid" not in (source_state.get("manager_attention_reasons") or [])

    source_result = json.loads((source / "result.json").read_text())
    assert source_result["blocking_reason"]["code"] == "COMMIT_BODY_LINE_TOO_LONG"

    result_md = (source / "result.md").read_text()
    assert "COMMIT_BODY_LINE_TOO_LONG" in result_md

    # Requirement 9 & 11: generic repair refuses, and runner is never called
    runner = RepairRunner()
    with pytest.raises(DispatchError) as caught:
        repair(repository, tmp_path, source, runner)

    assert caught.value.code == "RESULT_REPAIR_INELIGIBLE"
    assert "structured authority" in str(caught.value)
    assert len(runner.calls) == 0


def test_generic_repair_refuses_invalid_enclosing_result_with_ownership_resolutions(
    repository: Path, tmp_path: Path
) -> None:
    source = make_source(repository, tmp_path, "overlong_commit_with_resolutions")

    source_state = json.loads((source / "state.json").read_text())
    assert source_state["blocking_reason"]["code"] == "COMMIT_BODY_LINE_TOO_LONG"

    # Requirement 10 & 11: generic repair refuses, runner is never called
    runner = RepairRunner()
    with pytest.raises(DispatchError) as caught:
        repair(repository, tmp_path, source, runner)

    assert caught.value.code == "RESULT_REPAIR_INELIGIBLE"
    assert "structured authority" in str(caught.value)
    assert len(runner.calls) == 0


def test_semantic_stage_replay_available_on_ordinary_resume_for_structured_authority_blocker(
    repository: Path, tmp_path: Path
) -> None:
    # Requirement 15: exact semantic-stage replay remains available when ordinary resume rules permit it
    from agent_phase import resume as resume_module

    source = make_source(repository, tmp_path, "overlong_commit_with_dispositions")

    plan = resume_module.preflight(
        source,
        "auto",
        PHASE,
        REQUEST,
        repository,
        repository.name,
        None,
        check_route=False,
    )
    assert plan.from_stage == "closeout"
    assert plan.failed_stage_context is not None


def test_terminal_has_structured_authority_without_fence_markers() -> None:
    from agent_phase.result_repair import _terminal_has_structured_authority

    # Unfenced payload with path_dispositions
    data = b'{"version": 1, "path_dispositions": [{"path": "a", "disposition": "phase_owned"}]}'
    assert _terminal_has_structured_authority(data, "testnonce") is True

    # Unfenced payload with ownership_resolutions
    data = b'{"version": 1, "ownership_resolutions": [{"challenge_id": "ch1", "decision": "phase_owned"}]}'
    assert _terminal_has_structured_authority(data, "testnonce") is True

    # Unfenced payload without structured authority
    data = b'{"version": 1, "stage": "closeout", "outcome": "completed"}'
    assert _terminal_has_structured_authority(data, "testnonce") is False


def test_ineligibility_diagnostic_ordering_and_blocker_code_reporting(
    repository: Path, tmp_path: Path
) -> None:
    from agent_phase.result_repair import _ineligibility
    from agent_phase.lifecycle import get_lifecycle

    source = make_source(repository, tmp_path, "overlong_commit_with_dispositions")
    state = json.loads((source / "state.json").read_text())
    lifecycle = get_lifecycle("standard")
    terminal = lifecycle.terminal_result_stage
    terminal_stdout = (source / f"{lifecycle.prefixes[terminal]}.stdout.md").read_bytes()

    reason = _ineligibility(
        source,
        state,
        lifecycle,
        terminal_stdout,
        "corrected-v2-terminal-transport-separated",
    )
    assert reason is not None
    assert "COMMIT_BODY_LINE_TOO_LONG" in reason
    assert "exact semantic terminal-stage replay is required" in reason
