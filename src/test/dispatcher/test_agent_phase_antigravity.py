from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
import zipfile

import pytest

from agent_phase import capacity as capacity_module
from agent_phase.dispatch import DispatchError, Dispatcher
from agent_phase.lifecycle import get_lifecycle
from agent_phase.provider import MAX_STAGE_OUTPUT_BYTES, Result
from agent_phase.request import MAX_PROMPT_BYTES, PHASE_TYPES, PhaseRequest
from agent_phase.routing import Endpoint, resolve, route
from antigravity_profile import MAX_PROMPT_BYTES as ANTIGRAVITY_MAX_PROMPT_BYTES
from agent_source_guidance import codex_guidance_overrides
from antigravity_terminal_evidence import _closed_terminal_fields
from agent_phase_roster_fixtures import (
    SYNTHETIC_ENDPOINTS,
    build_synthetic_roster,
    write_roster_sources,
)


ROOT = Path(__file__).resolve().parents[3]
PHASE_ID = "TEST-ANTIGRAVITY-PROVIDER"
PREFIXES = ["01-plan", "02-plan-review", "03-work", "04-final-review", "05-closeout"]


def write_fake_evidence(argv: list[str], exit_code: int) -> None:
    if "--evidence-prefix" not in argv:
        return
    prefix = Path(argv[argv.index("--evidence-prefix") + 1])
    summary = prefix.with_name(
        f"{prefix.name}.antigravity-terminal-result.json"
    )
    empty = {
        "text": "", "utf8_bytes": 0,
        "sha256": hashlib.sha256(b"").hexdigest(),
        "truncated": False, "source": None,
    }
    summary.write_text(json.dumps({
        "schema": "antigravity-terminal-evidence-v2",
        "version": 2,
        "profile": argv[1], "model": argv[1],
        "reviewer": "--reviewer" in argv, "plan_mode": "--reviewer" in argv,
        "wrapper_exit_code": exit_code,
        "provider_record_observed": False,
        "terminal_result_observed": False,
        "terminal_record_kind": "no_terminal_event",
        "protocol_evidence_outcome": "no_terminal_event",
        "oversized_record_classification": None,
        "completion_fence_observed": exit_code == 0,
        "raw_result_artifact": None,
        "raw_result_absent_reason": "fake completion fence",
        "raw_result_bytes": 0, "raw_result_sha256": None,
        "normalized_status": "success" if exit_code == 0 else "error",
        "raw_status": None,
        "child_started": True,
        "child_exit_code": exit_code,
        "protocol_error": None,
        "reason_fields": {key: dict(empty) for key in (
            "error", "message", "reason", "cancel_reason", "cancellation_reason",
            "finish_reason", "termination_reason", "code", "error_code",
        )},
        "identifier_fields": {key: dict(empty) for key in (
            "conversation_id", "request_id", "session_id", "operation_id",
            "run_id", "turn_id",
        )},
        "preferred_reason": None,
    }) + "\n", encoding="utf-8")
    summary.chmod(0o600)


def strip_evidence(argv: list[str]) -> list[str]:
    if "--evidence-prefix" not in argv:
        return argv
    index = argv.index("--evidence-prefix")
    return argv[:index]


def expected_dispatch_argv(request: PhaseRequest) -> list[list[str]]:
    resolved = resolve(request, ROOT)
    expected: list[list[str]] = []
    for stage in get_lifecycle("standard").stages:
        endpoint = resolved["stages"][stage.name]
        provider = endpoint["provider"]
        profile = endpoint["profile"]
        read_only = endpoint["process_read_only"]
        if provider == "claude":
            argv = ["/fake/claude-profile", profile]
            if read_only:
                argv.append("--read-only")
            argv.append("-p")
        elif provider == "codex":
            argv = ["/fake/codex", "exec", "--profile", profile]
            if read_only:
                argv.extend(["-s", "read-only"])
            for override in codex_guidance_overrides(ROOT, workers=False):
                argv.extend(["-c", override])
            argv.append("-")
        else:
            argv = ["/fake/antigravity-profile", profile, "-p"]
            if read_only:
                argv.append("--reviewer")
        expected.append(argv)
    return expected


def exact_terminal_summary(
    argv: list[str], raw: bytes, exit_code: int, status: str, raw_status: str
) -> dict[str, object]:
    return {
        "schema": "antigravity-terminal-evidence-v2", "version": 2,
        "profile": argv[1], "model": argv[1],
        "reviewer": "--reviewer" in argv, "plan_mode": "--reviewer" in argv,
        "wrapper_exit_code": exit_code,
        "provider_record_observed": True,
        "terminal_result_observed": True,
        "terminal_record_kind": "exact_raw_event",
        "protocol_evidence_outcome": "exact_terminal_event_retained",
        "oversized_record_classification": None,
        "completion_fence_observed": False,
        "raw_result_artifact": None,
        "raw_result_absent_reason": None,
        "raw_result_bytes": len(raw),
        "raw_result_sha256": hashlib.sha256(raw).hexdigest(),
        "normalized_status": status, "raw_status": raw_status,
        "child_started": True, "child_exit_code": 0,
        "protocol_error": None,
        **_closed_terminal_fields(raw),
    }


def closeout_payload(prompt: bytes) -> bytes:
    match = re.search(rb"<<<AGENT-PHASE-RESULT ([0-9a-f]{32})>>>", prompt)
    assert match is not None
    nonce = match.group(1).decode("ascii")
    payload = {
        "version": 1,
        "stage": "closeout",
        "outcome": "completed",
        "body": "fake Antigravity transport closeout",
        "commit_message": {"subject": "Fake transport", "body": ""},
    }
    return (
        f"<<<AGENT-PHASE-RESULT {nonce}>>>\n"
        f"{json.dumps(payload)}\n"
        f"<<<END-AGENT-PHASE-RESULT {nonce}>>>\n"
    ).encode("utf-8")


def review_payload(prompt: bytes, body: bytes = b"fake review") -> bytes:
    match = re.search(rb"<<<AGENT-REVIEW-RESULT ([0-9a-f]{32})>>>", prompt)
    stage = re.search(rb"^stage: ([a-z_]+)$", prompt, re.MULTILINE)
    assert match is not None and stage is not None
    nonce = match.group(1).decode("ascii")
    payload = {
        "version": 1,
        "stage": stage.group(1).decode("ascii"),
        "outcome": "reviewed_with_findings",
        "body": body.decode("utf-8"),
    }
    return (
        f"<<<AGENT-REVIEW-RESULT {nonce}>>>\n{json.dumps(payload)}\n"
        f"<<<END-AGENT-REVIEW-RESULT {nonce}>>>\n"
    ).encode("utf-8")


class FakeRunner:
    def __init__(
        self,
        first_exit_code: int = 0,
        stdout_by_index: dict[int, bytes] | None = None,
    ) -> None:
        self.calls: list[dict[str, object]] = []
        self.first_exit_code = first_exit_code
        self.stdout_by_index = stdout_by_index or {}

    def __call__(self, argv, prompt, cwd, max_output, on_output=None):
        index = len(self.calls)
        self.calls.append({
            "argv": list(argv), "prompt": prompt, "max_output": max_output
        })
        started = time.time()
        exit_code = self.first_exit_code if index == 0 else 0
        write_fake_evidence(list(argv), exit_code)
        if b"<<<AGENT-PHASE-RESULT " in prompt:
            stdout = closeout_payload(prompt)
        elif b"<<<AGENT-REVIEW-RESULT " in prompt:
            stdout = review_payload(
                prompt, self.stdout_by_index.get(index, b"fake review")
            )
        else:
            stdout = self.stdout_by_index.get(index, b"fake output")
        return Result(
            exit_code=exit_code,
            stdout=stdout,
            stderr=b"",
            truncated=False,
            started=started,
            ended=started,
        )


def git(cwd: Path, *arguments: str) -> None:
    subprocess.run(["git", *arguments], cwd=cwd, capture_output=True, check=True)


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "user.name", "Test")
    (root / "file.txt").write_text("one\n", encoding="utf-8")
    git(root, "add", "file.txt")
    git(root, "commit", "-q", "-m", "initial")
    remote = tmp_path / "remote.git"
    subprocess.run(
        ["git", "init", "--bare", "-q", remote], capture_output=True, check=True
    )
    git(root, "remote", "add", "origin", str(remote))
    git(root, "push", "-q", "--set-upstream", "origin", "HEAD")
    return root


def dispatcher(
    repository: Path,
    tmp_path: Path,
    runner: FakeRunner,
    *,
    config_root: Path = ROOT,
) -> Dispatcher:
    return Dispatcher(
        root=config_root,
        cwd=repository,
        run_root=tmp_path / "runs",
        codex_executable="/fake/codex",
        claude_launcher="/fake/claude-profile",
        antigravity_launcher="/fake/antigravity-profile",
        scanner_executable=None,
        resolve_scanner=False,
        runner=runner,
    )


@pytest.mark.parametrize("phase_type", PHASE_TYPES)
def test_normal_uses_exact_five_stage_provider_argv(
    repository: Path,
    tmp_path: Path,
    phase_type: str,
) -> None:
    runner = FakeRunner()
    request = PhaseRequest(phase_type, "normal", "exact prompt fixture")

    state = dispatcher(repository, tmp_path, runner).dispatch(
        PHASE_ID,
        request,
    )

    expected_argv = expected_dispatch_argv(request)
    assert [strip_evidence(call["argv"]) for call in runner.calls] == expected_argv
    for call, expected in zip(runner.calls, expected_argv, strict=True):
        if expected[0] == "/fake/antigravity-profile":
            assert "--evidence-prefix" in call["argv"]
    assert len(runner.calls) == 5
    for index, prefix in enumerate(PREFIXES):
        call = runner.calls[index]
        prompt_path = tmp_path / "runs" / state["run_id"] / f"{prefix}.prompt.md"
        assert call["prompt"] == prompt_path.read_bytes()
    assert state["checkpoints_completed"] == ["post_planning", "pre_final"]
    assert state["complete"] is True
    assert state["commit"] is None
    assert state["push"]["attempted"] is False
    assert state["archive"]["succeeded"] is True


def test_dispatcher_has_no_provider_wall_clock(
    repository: Path, tmp_path: Path
) -> None:
    import inspect

    from agent_phase import provider

    parameters = set(inspect.signature(provider.run).parameters)
    assert not parameters & {"timeout", "timeout_seconds", "deadline"}
    source = (ROOT / "libexec/agent_phase/provider.py").read_text(encoding="utf-8")
    for token in ("timed_out", "timeout_seconds", "STAGE_TIMEOUT", "deadline"):
        assert token not in source

    runner = FakeRunner()
    dispatcher(repository, tmp_path, runner).dispatch(
        PHASE_ID,
        PhaseRequest("implementation_testing", "normal", "task"),
    )

    for call in runner.calls:
        assert "--print-timeout" not in call["argv"]


def test_nonzero_exit_is_a_provider_transport_failure(
    repository: Path, tmp_path: Path
) -> None:
    runner = FakeRunner(first_exit_code=17)
    request = PhaseRequest("implementation_testing", "gemini_only", "task")

    with pytest.raises(DispatchError) as caught:
        dispatcher(repository, tmp_path, runner).dispatch(
            PHASE_ID,
            request,
        )

    assert caught.value.code == "PROVIDER_TRANSPORT_FAILED"
    assert strip_evidence(runner.calls[0]["argv"]) == expected_dispatch_argv(request)[0]


def test_missing_antigravity_evidence_blocks_with_stable_code(
    repository: Path, tmp_path: Path
) -> None:
    class MissingEvidenceRunner:
        def __call__(self, argv, prompt, cwd, max_output, on_output=None):
            now = time.time()
            return Result(0, b"provider output", b"", False, now, now)

    with pytest.raises(DispatchError) as caught:
        dispatcher(repository, tmp_path, MissingEvidenceRunner()).dispatch(
            PHASE_ID,
            PhaseRequest("implementation_testing", "gemini_only", "task"),
        )
    assert caught.value.code == "PROVIDER_EVIDENCE_INVALID"


def test_antigravity_evidence_identity_mismatch_blocks(
    repository: Path, tmp_path: Path
) -> None:
    class IdentityMismatchRunner:
        def __call__(self, argv, prompt, cwd, max_output, on_output=None):
            write_fake_evidence(list(argv), 0)
            prefix = Path(argv[argv.index("--evidence-prefix") + 1])
            summary_path = prefix.with_name(
                f"{prefix.name}.antigravity-terminal-result.json"
            )
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["model"] = "wrong-model"
            summary_path.write_text(json.dumps(summary) + "\n", encoding="utf-8")
            summary_path.chmod(0o600)
            now = time.time()
            return Result(0, b"provider output", b"", False, now, now)

    with pytest.raises(DispatchError) as caught:
        dispatcher(repository, tmp_path, IdentityMismatchRunner()).dispatch(
            PHASE_ID,
            PhaseRequest("implementation_testing", "gemini_only", "task"),
        )
    assert caught.value.code == "PROVIDER_EVIDENCE_INVALID"


def test_raw_antigravity_evidence_digest_mismatch_blocks(
    repository: Path, tmp_path: Path
) -> None:
    class MismatchRunner:
        def __call__(self, argv, prompt, cwd, max_output, on_output=None):
            prefix = Path(argv[argv.index("--evidence-prefix") + 1])
            raw_path = prefix.with_name(
                f"{prefix.name}.antigravity-terminal-result.raw.json"
            )
            raw_path.write_bytes(b'{"type":"result","status":"SUCCESS"}')
            raw_path.chmod(0o600)
            summary_path = prefix.with_name(
                f"{prefix.name}.antigravity-terminal-result.json"
            )
            summary = exact_terminal_summary(
                list(argv), raw_path.read_bytes(), 0, "success", "SUCCESS"
            )
            summary["raw_result_artifact"] = raw_path.name
            summary["raw_result_sha256"] = "0" * 64
            summary_path.write_text(json.dumps(summary) + "\n")
            summary_path.chmod(0o600)
            now = time.time()
            return Result(0, b"provider output", b"", False, now, now)

    with pytest.raises(DispatchError) as caught:
        dispatcher(repository, tmp_path, MismatchRunner()).dispatch(
            PHASE_ID,
            PhaseRequest("implementation_testing", "gemini_only", "task"),
        )
    assert caught.value.code == "PROVIDER_EVIDENCE_INVALID"


def test_canceled_remains_transport_failure_with_exact_status_evidence(
    repository: Path, tmp_path: Path
) -> None:
    raw_record = b'{"type":"result","status":"CANCELED","reason":"provider reason"}'

    class CanceledRunner:
        def __call__(self, argv, prompt, cwd, max_output, on_output=None):
            prefix = Path(argv[argv.index("--evidence-prefix") + 1])
            raw = raw_record
            raw_path = prefix.with_name(
                f"{prefix.name}.antigravity-terminal-result.raw.json"
            )
            raw_path.write_bytes(raw)
            raw_path.chmod(0o600)
            summary_path = prefix.with_name(
                f"{prefix.name}.antigravity-terminal-result.json"
            )
            summary = exact_terminal_summary(
                list(argv), raw, 1, "canceled", "CANCELED"
            )
            summary["raw_result_artifact"] = raw_path.name
            summary_path.write_text(json.dumps(summary) + "\n")
            summary_path.chmod(0o600)
            now = time.time()
            return Result(1, b"", b"provider ended CANCELED", False, now, now)

    with pytest.raises(DispatchError) as caught:
        dispatcher(repository, tmp_path, CanceledRunner()).dispatch(
            PHASE_ID,
            PhaseRequest("implementation_testing", "gemini_only", "task"),
        )
    assert caught.value.code == "PROVIDER_TRANSPORT_FAILED"
    meta_path = next((tmp_path / "runs").glob("*/**/01-plan.meta.json"))
    meta = json.loads(meta_path.read_text())
    evidence = meta["antigravity_evidence"]
    assert evidence["provider_status"] == "canceled"
    assert evidence["provider_raw_status"] == "CANCELED"
    assert evidence["provider_reason_available"] is True
    assert evidence["raw"]["sha256"] == hashlib.sha256(raw_record).hexdigest()


def test_valid_antigravity_evidence_is_bound_into_meta_result_and_archive(
    repository: Path, tmp_path: Path
) -> None:
    runner = FakeRunner()
    request = PhaseRequest("implementation_testing", "gemini_only", "task")
    state = dispatcher(repository, tmp_path, runner).dispatch(
        PHASE_ID,
        request,
        finalization_policy="checkpoint",
    )
    expected_stages = list(resolve(request, ROOT)["stages"])
    assert [record["stage"] for record in state["provider_evidence"]] == expected_stages
    for record in state["provider_evidence"]:
        assert record["validation"] == "validated"
        assert record["summary"]["sha256"]
    run_directory = Path(state["run_directory"])
    plan_meta = json.loads((run_directory / "01-plan.meta.json").read_text())
    expected_plan_evidence = dict(state["provider_evidence"][0])
    expected_plan_evidence.pop("stage")
    assert plan_meta["antigravity_evidence"] == expected_plan_evidence
    result = json.loads((run_directory / "result.json").read_text())
    assert result["provider_evidence"] == state["provider_evidence"]
    with zipfile.ZipFile(state["archive_path"]) as archive:
        members = archive.namelist()
    for prefix in PREFIXES:
        assert any(
            name.endswith(f"{prefix}.antigravity-terminal-result.json")
            for name in members
        )


def test_plan_prompt_limit_fails_before_any_provider_invocation(
    repository: Path, tmp_path: Path
) -> None:
    runner = FakeRunner()

    with pytest.raises(DispatchError) as caught:
        dispatcher(repository, tmp_path, runner).dispatch(
            PHASE_ID,
            PhaseRequest(
                "implementation_testing", "gemini_only", "x" * MAX_PROMPT_BYTES
            ),
        )

    assert caught.value.code == "PROVIDER_PROMPT_LIMIT"
    assert runner.calls == []


def test_dry_run_preflights_antigravity_without_invoking_it(
    repository: Path, tmp_path: Path
) -> None:
    runner = FakeRunner()

    with pytest.raises(DispatchError) as caught:
        dispatcher(repository, tmp_path, runner).dry_run(
            PHASE_ID,
            PhaseRequest(
                "implementation_testing", "gemini_only", "x" * MAX_PROMPT_BYTES
            ),
        )

    assert caught.value.code == "PROVIDER_PROMPT_LIMIT"
    assert runner.calls == []


def test_closeout_actual_prompt_fit_stops_before_closeout_invocation(
    repository: Path, tmp_path: Path
) -> None:
    runner = FakeRunner()
    fixture = build_synthetic_roster(tmp_path / "fixture")
    routes = {key: dict(value) for key, value in fixture.routes.items()}
    routes[("implementation_testing", "normal")] = {
        "plan": "fixture-codex-primary",
        "plan_review": "fixture-claude-review",
        "work": "fixture-codex-primary",
        "final_review": "fixture-claude-review",
        "closeout": "fixture-gemini-gold",
    }
    write_roster_sources(
        fixture.root,
        SYNTHETIC_ENDPOINTS,
        routes,
        generation=fixture.generation,
    )
    subject = dispatcher(
        repository, tmp_path, runner, config_root=fixture.root
    )
    run_id = f"repo/{PHASE_ID}--20260821T000000000000Z"
    base_request = PhaseRequest("implementation_testing", "normal", "x")
    empty_plan = subject.plan_prompt(base_request, run_id, "")
    task = "x" * (ANTIGRAVITY_MAX_PROMPT_BYTES - len(empty_plan.data) - 1)
    request = PhaseRequest("implementation_testing", "normal", task)
    plan = subject.plan_prompt(request, run_id, task)
    assert len(plan.data) == ANTIGRAVITY_MAX_PROMPT_BYTES
    with pytest.raises(DispatchError) as caught:
        subject.dispatch(PHASE_ID, request)

    assert caught.value.code == "PROVIDER_PROMPT_LIMIT"
    assert "closeout" in str(caught.value)
    assert len(runner.calls) == 4
    state = json.loads(next(
        (tmp_path / "runs").rglob("state.json")
    ).read_text())
    assert state["manager_disposition_required"] is False
    assert state["phase_owned_paths"] == []


def test_work_review_capacity_fails_before_producer_is_spent(
    repository: Path, tmp_path: Path
) -> None:
    runner = FakeRunner()
    subject = dispatcher(repository, tmp_path, runner)
    request = PhaseRequest(
        "implementation_testing",
        "conserve_claude",
        "x" * (ANTIGRAVITY_MAX_PROMPT_BYTES - 512),
    )

    with pytest.raises(DispatchError) as caught:
        subject.dispatch(
            PHASE_ID, request, "work-reviewed", "checkpoint"
        )

    assert caught.value.code == "PROVIDER_PROMPT_LIMIT"
    assert runner.calls == []


def test_conserve_claude_keeps_global_capture_and_defers_prompt_fit(
    repository: Path, tmp_path: Path
) -> None:
    runner = FakeRunner()
    state = dispatcher(repository, tmp_path, runner).dispatch(
        PHASE_ID,
        PhaseRequest("implementation_testing", "conserve_claude", "task"),
        finalization_policy="checkpoint",
    )

    limits = state["terminal_prompt_preflight"]["output_limits"]
    assert limits == {}
    by_stage = dict(zip(
        ("plan", "plan_review", "work", "final_review", "closeout"),
        runner.calls,
        strict=True,
    ))
    assert by_stage["work"]["max_output"] == MAX_STAGE_OUTPUT_BYTES
    assert by_stage["final_review"]["max_output"] == MAX_STAGE_OUTPUT_BYTES
    assert state["terminal_prompt_preflight"]["method"] == (
        "static-envelope-evidence-plus-actual-prompt-fit"
    )


@pytest.mark.parametrize(
    ("lifecycle", "terminal"),
    [("plan-reviewed", "produce_close"), ("work-reviewed", "revise_close")],
)
def test_three_agent_terminal_prompt_fit_is_deferred_to_actual_material(
    repository: Path, tmp_path: Path, lifecycle: str, terminal: str
) -> None:
    subject = dispatcher(repository, tmp_path, FakeRunner())
    subject.lifecycle = get_lifecycle(lifecycle)
    request = PhaseRequest(
        "implementation_testing",
        "codex_only",
        "x" * (ANTIGRAVITY_MAX_PROMPT_BYTES - 512),
    )
    endpoints = route(request, subject.lifecycle)
    endpoints[terminal] = Endpoint("antigravity", "gemini-3.7-flash-medium")

    capacity, limits = capacity_module.preflight_lifecycle_capacity(
        subject, request, "run-id", request.prompt, endpoints
    )
    assert limits == {}
    assert capacity["stages"][terminal]["prompt_fit_decision"] == (
        "checked_at_actual_stage_prompt_construction"
    )


def test_oversized_final_review_blocks_without_invoking_closeout(
    repository: Path, tmp_path: Path
) -> None:
    findings = ("review finding λ\n" * 30000).encode("utf-8")
    runner = FakeRunner(stdout_by_index={3: findings})

    with pytest.raises(DispatchError) as caught:
        dispatcher(repository, tmp_path, runner).dispatch(
            PHASE_ID,
            PhaseRequest("implementation_testing", "gemini_only", "bounded task"),
        )

    assert caught.value.code == "PROVIDER_PROMPT_LIMIT"
    assert "closeout" in str(caught.value)
    assert len(runner.calls) == 4
    assert runner.calls[3]["prompt"]


def test_closeout_receives_full_review_findings_and_original_task_scope(
    repository: Path, tmp_path: Path
) -> None:
    findings = "complete final-review findings λ"
    task = "original bounded task scope"
    runner = FakeRunner(stdout_by_index={3: findings.encode("utf-8")})

    dispatcher(repository, tmp_path, runner).dispatch(
        PHASE_ID,
        PhaseRequest("implementation_testing", "normal", task),
    )

    closeout_prompt = runner.calls[4]["prompt"].decode("utf-8")
    assert task in closeout_prompt
    assert closeout_prompt.count(findings) == 1
    assert "Dispatcher transport truncation" not in closeout_prompt


@pytest.mark.parametrize("phase_type", PHASE_TYPES)
def test_conserve_claude_uses_exact_five_stage_provider_argv(
    repository: Path,
    tmp_path: Path,
    phase_type: str,
) -> None:
    runner = FakeRunner()
    request = PhaseRequest(
        phase_type, "conserve_claude", "exact prompt fixture"
    )

    state = dispatcher(repository, tmp_path, runner).dispatch(
        PHASE_ID,
        request,
    )

    expected_argv = expected_dispatch_argv(request)
    assert [strip_evidence(call["argv"]) for call in runner.calls] == expected_argv
    assert len(runner.calls) == 5
    for index, prefix in enumerate(PREFIXES):
        call = runner.calls[index]
        prompt_path = tmp_path / "runs" / state["run_id"] / f"{prefix}.prompt.md"
        assert call["prompt"] == prompt_path.read_bytes()
    assert state["checkpoints_completed"] == ["post_planning", "pre_final"]
    assert state["complete"] is True
    assert state["commit"] is None
    assert state["push"]["attempted"] is False
    assert state["archive"]["succeeded"] is True


def test_final_review_mutation_blocks_before_closeout(
    repository: Path, tmp_path: Path
) -> None:
    class MutatingRunner:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        def __call__(self, argv, prompt, cwd, max_output, on_output=None):
            index = len(self.calls)
            self.calls.append({"argv": list(argv), "prompt": prompt})
            if index == 3:
                (cwd / "untracked_from_review.txt").write_text("mutation from reviewer\n")
            started = time.time()
            write_fake_evidence(list(argv), 0)
            if index == 4:
                stdout = closeout_payload(prompt)
            elif index in (1, 3):
                stdout = review_payload(prompt)
            else:
                stdout = b"fake output"
            return Result(
                exit_code=0,
                stdout=stdout,
                stderr=b"",
                truncated=False,
                started=started,
                ended=started,
            )

    runner = MutatingRunner()
    with pytest.raises(DispatchError) as caught:
        dispatcher(repository, tmp_path, runner).dispatch(
            PHASE_ID,
            PhaseRequest("implementation_testing", "conserve_claude", "task"),
        )
    assert caught.value.code == "READ_ONLY_STAGE_MUTATED_CANDIDATE"
    assert len(runner.calls) == 4
    state_path = next((tmp_path / "runs").rglob("state.json"))
    state = json.loads(state_path.read_text())
    assert "untracked_from_review.txt" in state["final_review_mutation"]["paths"]
    assert state["final_review_mutation"]["expected_tree"] != state["final_review_mutation"]["observed_tree"]
    assert "stage_delta_ledger" in state


def test_standard_plan_is_read_only_and_mutation_checked(
    repository: Path, tmp_path: Path
) -> None:
    class MutatingPlanRunner:
        def __init__(self) -> None:
            self.calls = []

        def __call__(self, argv, prompt, cwd, max_output, on_output=None):
            index = len(self.calls)
            self.calls.append(list(argv))
            if index == 0:
                (cwd / "plan-mutation.txt").write_text("forbidden\n")
            write_fake_evidence(list(argv), 0)
            now = time.time()
            if index == 4:
                stdout = closeout_payload(prompt)
            elif index in (1, 3):
                stdout = review_payload(prompt)
            else:
                stdout = b"plan"
            return Result(0, stdout, b"", False, now, now)

    runner = MutatingPlanRunner()
    dispatcher(repository, tmp_path, runner).dispatch(
        PHASE_ID,
        PhaseRequest("implementation_testing", "gemini_only", "task"),
    )
    assert len(runner.calls) == 5
    assert "--reviewer" in runner.calls[0]
    state_path = next((tmp_path / "runs").rglob("state.json"))
    state = json.loads(state_path.read_text())
    assert "plan_mutation" in state
    assert "plan-mutation.txt" in state["plan_mutation"]["paths"]


def test_resume_rejects_source_with_mutated_final_review_candidate(
    repository: Path, tmp_path: Path
) -> None:
    class MutatingRunner:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        def __call__(self, argv, prompt, cwd, max_output, on_output=None):
            index = len(self.calls)
            self.calls.append({"argv": list(argv), "prompt": prompt})
            if index == 3:
                (cwd / "mutated_file.txt").write_text("mutated\n")
            started = time.time()
            write_fake_evidence(list(argv), 0)
            stdout = (
                review_payload(prompt)
                if index in (1, 3)
                else (closeout_payload(prompt) if index == 4 else b"fake output")
            )
            return Result(
                exit_code=1 if index == 4 else 0,
                stdout=stdout,
                stderr=b"closeout failed" if index == 4 else b"",
                truncated=False,
                started=started,
                ended=started,
            )

    runner = MutatingRunner()
    with pytest.raises(DispatchError):
        dispatcher(repository, tmp_path / "source_runs", runner).dispatch(
            PHASE_ID,
            PhaseRequest("implementation_testing", "conserve_claude", "task"),
        )

    source_dir = next(
        path.parent
        for path in (tmp_path / "source_runs" / "runs").rglob("state.json")
    )
    resume_runner = FakeRunner()
    with pytest.raises(DispatchError) as caught:
        dispatcher(repository, tmp_path / "resumed_runs", resume_runner).resume(
            PHASE_ID,
            PhaseRequest("implementation_testing", "conserve_claude", "task"),
            source_dir, "closeout",
        )
    assert caught.value.code == "RESUME_STAGE_UNSATISFIED"
    assert resume_runner.calls == []


def test_conserve_claude_resume_and_route_drift(
    repository: Path, tmp_path: Path
) -> None:
    runner = FakeRunner(first_exit_code=1)
    with pytest.raises(DispatchError):
        dispatcher(repository, tmp_path / "source_runs", runner).dispatch(
            PHASE_ID,
            PhaseRequest("implementation_testing", "conserve_claude", "task"),
        )
    source_dir = next(
        path.parent
        for path in (tmp_path / "source_runs" / "runs").rglob("state.json")
    )

    resume_runner = FakeRunner()
    resumed = dispatcher(repository, tmp_path / "resumed", resume_runner).resume(
        PHASE_ID,
        PhaseRequest("implementation_testing", "conserve_claude", "task"),
        source_dir,
        dry_run=True,
    )
    assert resumed["execution_mode"] == "conserve_claude"
    assert resumed["resume"]["inherited_stages"] == []

    with pytest.raises(DispatchError) as caught:
        dispatcher(repository, tmp_path / "resumed_normal", resume_runner).resume(
            PHASE_ID,
            PhaseRequest("implementation_testing", "normal", "task"),
            source_dir,
        )
    assert caught.value.code == "RESUME_REQUEST_MISMATCH"


def test_resume_copies_and_revalidates_inherited_antigravity_evidence(
    repository: Path, tmp_path: Path
) -> None:
    class SourceRunner:
        def __init__(self) -> None:
            self.calls = []

        def __call__(self, argv, prompt, cwd, max_output, on_output=None):
            index = len(self.calls)
            self.calls.append(list(argv))
            exit_code = 1 if index == 1 else 0
            write_fake_evidence(list(argv), exit_code)
            now = time.time()
            return Result(exit_code, b"plan", b"", False, now, now)

    request = PhaseRequest("implementation_testing", "gemini_only", "task")
    with pytest.raises(DispatchError):
        dispatcher(repository, tmp_path / "source", SourceRunner()).dispatch(
            PHASE_ID, request, finalization_policy="checkpoint"
        )
    source = next(
        path.parent
        for path in (tmp_path / "source" / "runs").rglob("state.json")
    )

    class ResumeRunner:
        def __init__(self) -> None:
            self.calls = []

        def __call__(self, argv, prompt, cwd, max_output, on_output=None):
            self.calls.append(list(argv))
            write_fake_evidence(list(argv), 0)
            stdout = (
                closeout_payload(prompt)
                if b"<<<AGENT-PHASE-RESULT " in prompt
                else (
                    review_payload(prompt)
                    if b"<<<AGENT-REVIEW-RESULT " in prompt
                    else b"stage output"
                )
            )
            now = time.time()
            return Result(0, stdout, b"", False, now, now)

    resumed = dispatcher(
        repository, tmp_path / "resumed", ResumeRunner()
    ).resume(
        PHASE_ID, request, source, finalization_policy="checkpoint"
    )
    inherited = Path(resumed["run_directory"]) / (
        "01-plan.antigravity-terminal-result.json"
    )
    assert inherited.is_file()
    assert inherited.stat().st_mode & 0o777 == 0o600
    assert [item["stage"] for item in resumed["provider_evidence"]] == list(
        resolve(request, ROOT)["stages"]
    )
