from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_phase import cli as cli_module
from agent_phase import resume_validation as resume_validation_module
from agent_phase import run as run_module


def request_file(tmp_path: Path) -> Path:
    path = tmp_path / "PHASE.request.json"
    path.write_text(json.dumps({
        "schema": "agent-phase-request-v1",
        "phase_type": "implementation_testing",
        "execution_mode": "codex_only",
        "prompt": "Do the work.",
    }))
    return path


def test_from_stage_requires_resume(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as caught:
        cli_module.dispatch_main([
            str(request_file(tmp_path)), "--from-stage", "work", "--quiet"
        ])

    assert caught.value.code == 2


def test_resume_defaults_from_stage_to_auto(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    called = {}

    class FakeDispatcher:
        def __init__(self, *args, **kwargs):
            pass

        def resume(
            self, phase_id, request, source, from_stage, *, lifecycle,
            finalization_policy, dry_run,
            result_repair_commit_subject, result_repair_commit_body_file,
        ):
            called.update(
                phase_id=phase_id, source=source, from_stage=from_stage,
                lifecycle=lifecycle, finalization_policy=finalization_policy,
                dry_run=dry_run,
                result_repair_commit_subject=result_repair_commit_subject,
                result_repair_commit_body_file=result_repair_commit_body_file,
            )
            return {"ok": True}

    monkeypatch.setattr(cli_module, "Dispatcher", FakeDispatcher)
    monkeypatch.setattr(cli_module, "repository_root", lambda: tmp_path)
    monkeypatch.setattr(
        cli_module.resume_validation_module,
        "phase_id_for_resume",
        lambda source, request: "SOURCE-PHASE",
    )
    source = tmp_path / "source"

    assert cli_module.dispatch_main([
        str(request_file(tmp_path)), "--resume", str(source), "--dry-run", "--quiet"
    ]) == 0

    assert called == {
        "phase_id": "SOURCE-PHASE",
        "source": source,
        "from_stage": "auto",
        "lifecycle": None,
        "finalization_policy": None,
        "dry_run": True,
        "result_repair_commit_subject": None,
        "result_repair_commit_body_file": None,
    }
    assert json.loads(capsys.readouterr().out) == {"ok": True}


def source_run(tmp_path: Path) -> Path:
    project = tmp_path / "fixture-project"
    source = project / "SOURCE-PHASE--20260830T000000000000Z"
    source.mkdir(parents=True)
    retained = {
        "schema": "agent-phase-request-v1",
        "phase_type": "implementation_testing",
        "execution_mode": "codex_only",
        "prompt": "Do the retained work.",
    }
    (source / "request.json").write_text(
        json.dumps(retained, indent=2, sort_keys=True) + "\n"
    )
    identity = {
        "project": "fixture-project",
        "phase_id": "SOURCE-PHASE",
        "run_id": f"fixture-project/{source.name}",
        "run_directory": str(source.resolve()),
    }
    (source / "state.json").write_text(json.dumps(identity))
    (source / "result.json").write_text(json.dumps(identity))
    (source / "resolved.json").write_text("{}")
    return source


def test_retained_request_json_supplies_source_phase_identity(
    tmp_path: Path,
) -> None:
    source = source_run(tmp_path)
    assert resume_validation_module.phase_id_for_resume(
        source, source / "request.json"
    ) == "SOURCE-PHASE"
    assert run_module.phase_id_from_request(Path("request.json")) == "request"


def test_resume_rejects_semantically_equal_but_byte_different_request(
    tmp_path: Path,
) -> None:
    source = source_run(tmp_path)
    supplied = tmp_path / "copy.json"
    supplied.write_text(json.dumps(json.loads((source / "request.json").read_text())))
    with pytest.raises(
        resume_validation_module.ResumeError, match="RESUME_REQUEST_MISMATCH"
    ):
        resume_validation_module.phase_id_for_resume(source, supplied)


@pytest.mark.parametrize(
    ("field", "value"),
    [("phase_id", ".foreign"), ("run_id", "fixture-project/foreign")],
)
def test_resume_rejects_malformed_or_foreign_source_identity(
    tmp_path: Path, field: str, value: str
) -> None:
    source = source_run(tmp_path)
    for name in ("state.json", "result.json"):
        data = json.loads((source / name).read_text())
        data[field] = value
        (source / name).write_text(json.dumps(data))
    with pytest.raises(resume_validation_module.ResumeError):
        resume_validation_module.phase_id_for_resume(
            source, source / "request.json"
        )


def test_resume_rejects_malformed_timestamped_source_leaf(
    tmp_path: Path,
) -> None:
    source = source_run(tmp_path)
    malformed = source.with_name("SOURCE-PHASE--not-a-timestamp")
    source.rename(malformed)
    for name in ("state.json", "result.json"):
        data = json.loads((malformed / name).read_text())
        data["run_id"] = f"fixture-project/{malformed.name}"
        data["run_directory"] = str(malformed.resolve())
        (malformed / name).write_text(json.dumps(data))
    with pytest.raises(resume_validation_module.ResumeError):
        resume_validation_module.phase_id_for_resume(
            malformed, malformed / "request.json"
        )
