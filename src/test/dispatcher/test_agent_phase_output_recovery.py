from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
from types import SimpleNamespace
import zipfile

import pytest

from agent_phase import archive as archive_module
from agent_phase import dispatch as dispatch_module
from agent_phase import antigravity_output_recovery as output_recovery_module
from agent_phase.dispatch import DispatchError, Dispatcher
from agent_phase.provider import MAX_STAGE_OUTPUT_BYTES, Result
from agent_phase.request import PhaseRequest
from agent_phase.transport import PromptLimitError
from antigravity_profile import StreamObserver
from antigravity_terminal_evidence import StderrCapture, write_terminal_evidence


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = Path(__file__).resolve().parent / "fixtures/antigravity_output_recovery_v1/fixture.json"
PHASE = "TEST-ANTIGRAVITY-OUTPUT-RECOVERY"
REQUEST = PhaseRequest(
    "implementation_testing",
    "conserve_claude",
    "Implement the sanitized provider-output recovery fixture.",
)
NONCE = "0123456789abcdef0123456789abcdef"


def git(cwd: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=cwd, text=True, capture_output=True, check=True
    )
    return completed.stdout.strip()


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "fixture-project"
    remote = tmp_path / "fixture-project.git"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "Fixture User")
    git(root, "config", "user.email", "fixture@example.invalid")
    (root / "README.md").write_text("fixture\n", encoding="utf-8")
    git(root, "add", "README.md")
    git(root, "commit", "-m", "fixture entry")
    git(tmp_path, "init", "--bare", str(remote))
    git(root, "remote", "add", "origin", str(remote))
    git(root, "push", "-u", "origin", "main")
    return root


def response_bytes(size: int) -> bytes:
    unit = b"sanitized provider response line\n"
    return (unit * ((size // len(unit)) + 1))[:size]


def _record(value: dict[str, object]) -> bytes:
    return json.dumps(value, separators=(",", ":")).encode("utf-8")


def write_exact_evidence(argv: list[str], response: bytes) -> None:
    index = argv.index("--evidence-prefix")
    prefix = Path(argv[index + 1])
    observer = StreamObserver(fence_nonce=NONCE)
    observer.feed(
        _record({
            "event": "step_update",
            "step_update": {
                "step_type": "agent_response",
                "text_delta": f"fixture\n<<<AGENT-CENTRAL-COMPLETE {NONCE}>>>\n",
            },
        })
        + b"\n"
    )
    observer.feed(
        _record({
            "event": "result",
            "result": {
                "status": "SUCCESS",
                "response": response.decode("utf-8"),
            },
        })
        + b"\n"
    )
    cleanup = {
        "schema": "antigravity-process-group-cleanup-v1",
        "reason": "fixture-cleanup",
        "attempted": True,
        "term_status": "absent",
        "kill_status": "not_attempted",
        "group_absent": True,
        "group_state": "absent",
        "parent_reaped": True,
        "stdout_reader_joined": True,
        "stderr_reader_joined": True,
        "readers_joined": True,
        "cleanup_complete": True,
        "failure_class": None,
    }
    write_terminal_evidence(
        prefix,
        profile=argv[1],
        model=argv[1],
        reviewer="--reviewer" in argv,
        command=["agy"],
        observer=observer,
        stderr_capture=StderrCapture.create(),
        started_at="2026-08-30T00:00:00+00:00",
        ended_at="2026-08-30T00:00:01+00:00",
        duration_seconds=1.0,
        child_started=True,
        child_exit_code=0,
        wrapper_exit_code=0,
        received_signals=[],
        signal_events=[],
        child_exit_monotonic=3.0,
        process_group_cleanup=cleanup,
        version_probe_cleanup={**cleanup, "reason": "fixture-probe-cleanup"},
    )


def review_payload(prompt: bytes) -> bytes:
    nonce = re.search(rb"<<<AGENT-REVIEW-RESULT ([0-9a-f]{32})>>>", prompt)
    assert nonce is not None
    value = nonce.group(1).decode("ascii")
    payload = {
        "version": 1,
        "stage": "work_review",
        "outcome": "reviewed_with_findings",
        "body": "Sanitized independent review findings.",
    }
    return (
        f"<<<AGENT-REVIEW-RESULT {value}>>>\n{json.dumps(payload)}\n"
        f"<<<END-AGENT-REVIEW-RESULT {value}>>>\n"
    ).encode()


def terminal_payload(prompt: bytes) -> bytes:
    nonce = re.search(rb"<<<AGENT-PHASE-RESULT ([0-9a-f]{32})>>>", prompt)
    assert nonce is not None
    value = nonce.group(1).decode("ascii")
    payload = {
        "version": 1,
        "stage": "revise_close",
        "outcome": "completed",
        "body": "Sanitized recovery closeout.",
        "commit_message": {
            "subject": "Publish sanitized recovered candidate",
            "body": "",
        },
    }
    return (
        f"<<<AGENT-PHASE-RESULT {value}>>>\n{json.dumps(payload)}\n"
        f"<<<END-AGENT-PHASE-RESULT {value}>>>\n"
    ).encode()


class SourceRunner:
    def __init__(self, root: Path, paths: list[str], response: bytes) -> None:
        self.root = root
        self.paths = paths
        self.response = response
        self.calls: list[dict[str, object]] = []

    def __call__(self, argv, prompt, cwd, max_output, on_output=None):
        self.calls.append({"prompt": prompt, "max_output": max_output})
        for index, name in enumerate(self.paths):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"candidate {index}\n", encoding="utf-8")
        write_exact_evidence(list(argv), self.response)
        now = time.time()
        prefix = self.response[:9958]
        return Result(
            0, prefix, b"sanitized diagnostic", True, now, now,
            stderr_truncated=True,
        )


class RecoveryRunner:
    def __init__(self, root: Path, response: bytes, changed_path: str) -> None:
        self.root = root
        self.response = response
        self.changed_path = changed_path
        self.calls: list[dict[str, object]] = []

    def __call__(self, argv, prompt, cwd, max_output, on_output=None):
        self.calls.append({
            "argv": list(argv), "prompt": prompt, "max_output": max_output
        })
        now = time.time()
        if len(self.calls) == 1:
            assert self.response in prompt
            return Result(0, review_payload(prompt), b"", False, now, now)
        path = self.root / self.changed_path
        path.write_text(path.read_text() + "revised\n", encoding="utf-8")
        output = terminal_payload(prompt)
        write_exact_evidence(list(argv), output)
        return Result(0, output, b"", False, now, now)


class SuccessfulLifecycleRunner:
    def __init__(self, root: Path, paths: list[str], response: bytes) -> None:
        self.root = root
        self.paths = paths
        self.response = response
        self.calls: list[dict[str, object]] = []

    def __call__(self, argv, prompt, cwd, max_output, on_output=None):
        self.calls.append({"prompt": prompt, "max_output": max_output})
        now = time.time()
        if len(self.calls) == 1:
            for index, name in enumerate(self.paths):
                path = self.root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"candidate {index}\n", encoding="utf-8")
            write_exact_evidence(list(argv), self.response)
            return Result(0, self.response, b"diagnostic", False, now, now)
        if len(self.calls) == 2:
            assert self.response in prompt
            return Result(0, review_payload(prompt), b"", False, now, now)
        output = terminal_payload(prompt)
        write_exact_evidence(list(argv), output)
        return Result(0, output, b"", False, now, now)


class ForbiddenRunner:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError("provider must not be invoked")


def _seal(directory: Path) -> None:
    target = directory.parent / f"{directory.name}.zip"
    if target.exists():
        target.unlink()
    # This helper deliberately reseals mutated disposable fixture evidence.
    # Production publication keeps both ZIP and receipt no-clobber.
    archive_module.receipt_path(target).unlink(missing_ok=True)
    archive_module.create(SimpleNamespace(
        path=directory,
        leaf=directory.name,
        archive_path=target,
        archive_temporary_path=directory.parent / f".{directory.name}.zip.tmp",
    ))


def make_source(repository: Path, tmp_path: Path) -> tuple[Path, bytes, dict]:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    response = response_bytes(fixture["response_bytes"])
    assert len(response) == 13227
    runner = SourceRunner(repository, fixture["candidate_paths"], response)
    dispatcher = Dispatcher(
        ROOT, repository, run_root=tmp_path / "runs",
        runner=runner, resolve_scanner=False,
    )
    with pytest.raises(DispatchError) as caught:
        dispatcher.dispatch(
            PHASE, REQUEST, lifecycle="work-reviewed", finalization_policy="publish"
        )
    assert caught.value.code == "PROVIDER_OUTPUT_LIMIT"
    assert len(runner.calls) == 1
    assert runner.calls[0]["max_output"] == MAX_STAGE_OUTPUT_BYTES
    source = next((tmp_path / "runs").rglob("state.json")).parent
    state_path = source / "state.json"
    result_path = source / "result.json"
    state = json.loads(state_path.read_text())
    result = json.loads(result_path.read_text())
    assert len(state["failure_candidate"]["paths"]) == 19
    assert len(state["phase_delta"]) == 19
    assert len(state["phase_owned_paths"]) == 19
    assert state["manager_disposition_required"] is True
    assert len(state["candidate_manifest"]["paths"]) == 19
    assert result["phase_delta"] == state["phase_delta"]
    assert result["phase_owned_paths"] == state["phase_owned_paths"]
    assert result["manager_disposition_required"] is True
    assert result["failure_stage_transport"]["status"] == "overflowed"
    assert "manager disposition required: **True**" in (
        source / "result.md"
    ).read_text()
    with zipfile.ZipFile(source.parent / f"{source.name}.zip") as archive:
        archived = json.loads(
            archive.read(f"{source.name}/state.json").decode("utf-8")
        )
    assert archived["phase_owned_paths"] == state["phase_owned_paths"]
    assert archived["manager_disposition_required"] is True
    for value in (state, result):
        value["phase_delta"] = []
        value["phase_owned_paths"] = []
        value["manager_disposition_required"] = False
        value.pop("candidate_manifest", None)
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    markdown = (source / "result.md").read_text()
    markdown = re.sub(r"- manager disposition required: \*\*True\*\*",
                      "- manager disposition required: **False**", markdown)
    markdown = re.sub(r"- phase delta: \d+ path\(s\)(?:\n  - .*?)*\n",
                      "- phase delta: 0 path(s)\n", markdown)
    markdown = re.sub(r"- phase-owned paths: \d+(?:\n  - .*?)*\n",
                      "- phase-owned paths: 0\n", markdown)
    (source / "result.md").write_text(markdown)
    _seal(source)
    return source, response, fixture


def digest_tree(source: Path) -> dict[str, str]:
    values = {
        path.relative_to(source).as_posix():
        hashlib.sha256(path.read_bytes()).hexdigest()
        for path in source.rglob("*") if path.is_file()
    }
    archive = source.parent / f"{source.name}.zip"
    values["<archive>"] = hashlib.sha256(archive.read_bytes()).hexdigest()
    return values


def assert_recovery_stops_before_provider(
    repository: Path, tmp_path: Path, source: Path
) -> None:
    runner = ForbiddenRunner()
    with pytest.raises(DispatchError):
        Dispatcher(
            ROOT, repository, run_root=tmp_path / "blocked-runs",
            runner=runner, resolve_scanner=False,
        ).resume(
            PHASE,
            REQUEST,
            source,
            "work-review",
            lifecycle="work-reviewed",
            finalization_policy="publish",
        )
    assert runner.calls == 0


@pytest.mark.parametrize("from_stage", ["work-review", "auto"])
def test_exact_output_recovery_inherits_producer_and_publishes(
    repository: Path, tmp_path: Path, from_stage: str
) -> None:
    source, response, fixture = make_source(repository, tmp_path)
    before = digest_tree(source)
    runner = RecoveryRunner(repository, response, fixture["candidate_paths"][0])
    state = Dispatcher(
        ROOT, repository, run_root=tmp_path / "recovered-runs",
        runner=runner, resolve_scanner=False,
    ).resume(
        PHASE,
        REQUEST,
        source,
        from_stage,
        lifecycle="work-reviewed",
        finalization_policy="publish",
    )
    assert state["complete"] is True
    assert state["effective_stages"] == {
        "produce": "recovered",
        "work_review": "performed",
        "revise_close": "performed",
    }
    assert state["semantic_provider_invocations_inherited"] == 1
    assert state["semantic_provider_invocations_performed"] == 2
    assert state["auxiliary_provider_invocations_performed"] == 0
    assert len(runner.calls) == 2
    assert all(call["max_output"] == MAX_STAGE_OUTPUT_BYTES for call in runner.calls)
    recovered = Path(state["run_directory"])
    assert (recovered / "01-produce.recovered-complete.stdout.md").read_bytes() == response
    for basename in (
        "01-produce.prompt.md",
        "01-produce.stdout.md",
        "01-produce.stderr.log",
        "01-produce.meta.json",
        "01-produce.antigravity-terminal-result.json",
        "01-produce.antigravity-terminal-result.raw.json",
    ):
        assert (recovered / basename).read_bytes() == (source / basename).read_bytes()
    recovery_record = json.loads(
        (recovered / output_recovery_module.RECORD).read_text()
    )
    assert recovery_record["schema"] == output_recovery_module.SCHEMA
    assert recovery_record["response_bytes"] == 13227
    assert recovery_record["captured_prefix_bytes"] == 9958
    assert recovery_record["provider_invocation_performed"] is False
    assert digest_tree(source) == before
    remote_head = git(repository, "ls-remote", "origin", "refs/heads/main").split()[0]
    assert git(repository, "rev-parse", "HEAD") == remote_head


def test_successful_13227_byte_producer_uses_global_capture_bound(
    repository: Path, tmp_path: Path
) -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    response = response_bytes(fixture["response_bytes"])
    runner = SuccessfulLifecycleRunner(
        repository, fixture["candidate_paths"], response
    )
    state = Dispatcher(
        ROOT, repository, run_root=tmp_path / "successful-runs",
        runner=runner, resolve_scanner=False,
    ).dispatch(
        PHASE,
        REQUEST,
        lifecycle="work-reviewed",
        finalization_policy="checkpoint",
    )
    assert state["complete"] is True
    assert len(runner.calls) == 3
    assert all(
        call["max_output"] == MAX_STAGE_OUTPUT_BYTES for call in runner.calls
    )
    run = Path(state["run_directory"])
    assert (run / "01-produce.stdout.md").read_bytes() == response
    assert json.loads((run / "01-produce.meta.json").read_text())[
        "stdout_bytes"
    ] == 13227


def test_recovered_output_is_mandatory_exact_for_reviewer(
    repository: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, _, _ = make_source(repository, tmp_path)
    original = dispatch_module.ensure_prompt_fits

    def reject_reviewer(stage, endpoint, rendered):
        if stage == "work_review":
            raise PromptLimitError("fixture mandatory exact material does not fit")
        return original(stage, endpoint, rendered)

    monkeypatch.setattr(dispatch_module, "ensure_prompt_fits", reject_reviewer)
    runner = ForbiddenRunner()
    with pytest.raises(DispatchError) as caught:
        Dispatcher(
            ROOT, repository, run_root=tmp_path / "mandatory-blocked-runs",
            runner=runner, resolve_scanner=False,
        ).resume(
            PHASE,
            REQUEST,
            source,
            "work-review",
            lifecycle="work-reviewed",
            finalization_policy="publish",
        )
    assert caught.value.code == "PROVIDER_PROMPT_LIMIT"
    assert runner.calls == 0


def test_failure_accounting_closes_all_nineteen_paths(
    repository: Path, tmp_path: Path
) -> None:
    source, _, fixture = make_source(repository, tmp_path)
    archived_state = json.loads((source / "state.json").read_text())
    assert archived_state["stages_completed"] == []
    assert archived_state["blocking_reason"]["code"] == "PROVIDER_OUTPUT_LIMIT"
    assert len(archived_state["failure_candidate"]["paths"]) == len(
        fixture["candidate_paths"]
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("wrapper_exit_code", 1),
        ("child_exit_code", 1),
        ("normalized_status", "error"),
        ("response_source", "event.response"),
    ],
)
def test_invalid_terminal_evidence_blocks_before_provider(
    repository: Path, tmp_path: Path, field: str, value: object
) -> None:
    source, _, _ = make_source(repository, tmp_path)
    summary_path = source / "01-produce.antigravity-terminal-result.json"
    summary = json.loads(summary_path.read_text())
    summary[field] = value
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    _seal(source)
    assert_recovery_stops_before_provider(repository, tmp_path, source)


@pytest.mark.parametrize("mode", ["raw_hash", "nonprefix"])
def test_raw_hash_and_nonprefix_capture_block_before_provider(
    repository: Path, tmp_path: Path, mode: str
) -> None:
    source, _, _ = make_source(repository, tmp_path)
    if mode == "raw_hash":
        raw = source / "01-produce.antigravity-terminal-result.raw.json"
        raw.write_bytes(raw.read_bytes() + b" ")
    else:
        stdout = source / "01-produce.stdout.md"
        changed = b"X" + stdout.read_bytes()[1:]
        stdout.write_bytes(changed)
        meta_path = source / "01-produce.meta.json"
        meta = json.loads(meta_path.read_text())
        meta["stdout_bytes"] = len(changed)
        meta["stdout_sha256"] = hashlib.sha256(changed).hexdigest()
        meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")
    _seal(source)
    assert_recovery_stops_before_provider(repository, tmp_path, source)


@pytest.mark.parametrize(
    "mode",
    [
        "oversize", "route", "candidate", "staged", "git_operation",
        "failure_head", "missing_meta", "resolved_identity",
        "malformed_routes", "archive_record", "duplicate_paths",
    ],
)
def test_oversize_route_candidate_index_and_git_operation_block(
    repository: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    source, _, fixture = make_source(repository, tmp_path)
    if mode == "oversize":
        monkeypatch.setattr(output_recovery_module, "MAX_STAGE_OUTPUT_BYTES", 10_000)
    elif mode == "route":
        resolved_path = source / "resolved.json"
        resolved = json.loads(resolved_path.read_text())
        resolved["stages"]["produce"]["profile"] = "drifted-profile"
        resolved_path.write_text(
            json.dumps(resolved, indent=2, sort_keys=True) + "\n"
        )
        _seal(source)
    elif mode == "candidate":
        candidate = repository / fixture["candidate_paths"][0]
        candidate.write_text("drifted candidate\n")
    elif mode == "staged":
        git(repository, "add", fixture["candidate_paths"][0])
    elif mode == "git_operation":
        (repository / ".git/MERGE_HEAD").write_text(
            git(repository, "rev-parse", "HEAD")
        )
    elif mode == "failure_head":
        for name in ("state.json", "result.json"):
            path = source / name
            value = json.loads(path.read_text())
            value["failure_candidate"]["head"] = "f" * 40
            path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
        _seal(source)
    elif mode == "missing_meta":
        (source / "01-produce.meta.json").unlink()
        _seal(source)
    elif mode == "resolved_identity":
        path = source / "resolved.json"
        value = json.loads(path.read_text())
        value["expected_review_count"] = 2
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
        _seal(source)
    elif mode == "malformed_routes":
        path = source / "resolved.json"
        value = json.loads(path.read_text())
        value["stages"] = []
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
        _seal(source)
    elif mode == "archive_record":
        for name in ("state.json", "result.json"):
            path = source / name
            value = json.loads(path.read_text())
            value["archive"]["path"] = str(source.parent / "foreign.zip")
            path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
        _seal(source)
    else:
        for name in ("state.json", "result.json"):
            path = source / name
            value = json.loads(path.read_text())
            value["failure_candidate"]["paths"].append(
                value["failure_candidate"]["paths"][0]
            )
            path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
        _seal(source)
    assert_recovery_stops_before_provider(repository, tmp_path, source)
