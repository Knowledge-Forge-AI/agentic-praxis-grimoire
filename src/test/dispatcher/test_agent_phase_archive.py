"""Final run packages are upload-ready, complete, and no-clobber."""

from __future__ import annotations

import json
from pathlib import Path
import zipfile

import pytest

from agent_phase import archive as archive_module
from agent_phase.dispatch import DispatchError
from agent_phase.request import PhaseRequest
from agent_phase.run import LABEL_FILE, TELEMETRY_FILE, RunDirectory

from test_agent_phase_dispatch import FakeRunner, PHASE_ID, make_dispatcher, repository


__all__ = ["repository"]
REQUEST = PhaseRequest("implementation_testing", "normal", "task")


def members(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        return archive.namelist()


def test_successful_finalization_creates_clean_complete_zip(
    repository: Path, tmp_path: Path
) -> None:
    run_root = tmp_path / "runs"

    def add_excluded_artifacts(index: int) -> None:
        if index == 0:
            run_directory = next(run_root.glob("*/*"))
            (run_directory / ".DS_Store").write_bytes(b"finder")
            (run_directory / "._result.json").write_bytes(b"appledouble")
            (run_directory / "__MACOSX").mkdir()
            (run_directory / "__MACOSX" / "noise").write_bytes(b"noise")
            (run_root / TELEMETRY_FILE).write_text("global\n")
            (run_root / LABEL_FILE).write_text("global\n")

    state = make_dispatcher(
        repository, tmp_path, FakeRunner(on_stage=add_excluded_artifacts)
    ).dispatch(PHASE_ID, REQUEST)
    archive_path = Path(state["archive_path"])
    names = members(archive_path)
    leaf = Path(state["run_directory"]).name

    assert archive_path == Path(state["run_directory"]).parent / f"{leaf}.zip"
    assert {name.split("/", 1)[0] for name in names} == {leaf}
    expected = {
        "request.json", "resolved.json", "state.json", "result.json", "result.md",
        "prompt-policy.json", "01-plan.prompt.md", "05-closeout.result.json",
    }
    assert {f"{leaf}/{name}" for name in expected} <= set(names)
    assert not any(
        "__MACOSX" in name
        or name.endswith(".DS_Store")
        or Path(name).name.startswith("._")
        or name.endswith(".zip")
        or TELEMETRY_FILE in name
        or LABEL_FILE in name
        for name in names
    )
    with zipfile.ZipFile(archive_path) as archive:
        archived_result = json.loads(archive.read(f"{leaf}/result.json"))
        archived_state = json.loads(archive.read(f"{leaf}/state.json"))
    assert archived_result["archive"]["status"] == "in_progress"
    receipt = json.loads(archive_module.receipt_path(archive_path).read_text())
    assert receipt["status"] == "succeeded"
    assert state["archive"]["succeeded"] is True
    assert archived_state["archive_path"] == str(archive_path)
    assert archived_result["push"] == state["push"]


def test_blocked_run_is_archived_after_run_directory_exists(
    repository: Path, tmp_path: Path
) -> None:
    dispatcher = make_dispatcher(repository, tmp_path, FakeRunner(exit_codes={0: 7}))
    with pytest.raises(DispatchError) as caught:
        dispatcher.dispatch(PHASE_ID, REQUEST)

    archives = list((tmp_path / "runs").rglob("*.zip"))
    assert caught.value.code == "PROVIDER_TRANSPORT_FAILED"
    assert len(archives) == 1
    leaf = archives[0].stem
    with zipfile.ZipFile(archives[0]) as archive:
        result = json.loads(archive.read(f"{leaf}/result.json"))
    assert result["complete"] is False
    assert result["blocking_reason"]["code"] == "PROVIDER_TRANSPORT_FAILED"


def test_archive_collision_does_not_overwrite_existing_file(tmp_path: Path) -> None:
    directory = RunDirectory(
        tmp_path / "runs", "proj", "PHASE", "20260820T120000000000Z"
    )
    for name in ("state.json", "request.json", "resolved.json", "result.json"):
        directory.write_text(name, "{}\n")
    directory.archive_path.write_bytes(b"existing")

    with pytest.raises(archive_module.ArchiveError) as caught:
        archive_module.create(directory)

    assert caught.value.code == "RUN_ARCHIVE_COLLISION"
    assert directory.archive_path.read_bytes() == b"existing"
    assert not directory.archive_temporary_path.exists()


def test_dry_run_is_packaged_without_inventing_result_artifacts(
    repository: Path, tmp_path: Path
) -> None:
    state = make_dispatcher(repository, tmp_path, FakeRunner()).dry_run(PHASE_ID, REQUEST)
    archive_path = Path(state["archive_path"])
    names = members(archive_path)
    leaf = Path(state["run_directory"]).name

    assert f"{leaf}/state.json" in names
    assert f"{leaf}/01-plan.prompt.md" in names
    assert f"{leaf}/result.json" not in names


def test_archive_failure_preserves_an_otherwise_complete_run(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(_directory) -> Path:
        raise archive_module.ArchiveError("RUN_ARCHIVE_FAILED", "injected failure")

    monkeypatch.setattr(archive_module, "create", fail)
    dispatcher = make_dispatcher(repository, tmp_path, FakeRunner())
    with pytest.raises(DispatchError) as caught:
        dispatcher.dispatch(PHASE_ID, REQUEST)

    state_path = next((tmp_path / "runs").rglob("state.json"))
    state = json.loads(state_path.read_text())
    assert caught.value.code == "RUN_ARCHIVE_FAILED"
    assert state["complete"] is True
    assert state["outcome"] == "completed"
    assert state["blocking_reason"] is None
    assert state["archive"]["succeeded"] is False


def test_blocked_run_preserves_primary_blocker_when_archive_also_fails(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(_directory) -> Path:
        raise archive_module.ArchiveError("RUN_ARCHIVE_FAILED", "injected failure")

    monkeypatch.setattr(archive_module, "create", fail)
    dispatcher = make_dispatcher(repository, tmp_path, FakeRunner(exit_codes={0: 7}))
    with pytest.raises(DispatchError) as caught:
        dispatcher.dispatch(PHASE_ID, REQUEST)

    state_path = next((tmp_path / "runs").rglob("state.json"))
    state = json.loads(state_path.read_text())
    assert caught.value.code == "PROVIDER_TRANSPORT_FAILED"
    assert state["blocking_reason"]["code"] == "PROVIDER_TRANSPORT_FAILED"
    assert state["finalization_failures"][0]["code"] == "RUN_ARCHIVE_FAILED"


def test_archive_write_failure_leaves_no_partial_zip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = RunDirectory(
        tmp_path / "runs", "proj", "PHASE", "20260820T120000000000Z"
    )
    for name in ("state.json", "request.json", "resolved.json", "result.json"):
        directory.write_text(name, "{}\n")

    def fail(*_args, **_kwargs):
        raise OSError("injected write failure")

    monkeypatch.setattr(archive_module.zipfile, "ZipFile", fail)
    with pytest.raises(archive_module.ArchiveError) as caught:
        archive_module.create(directory)

    assert caught.value.code == "RUN_ARCHIVE_FAILED"
    assert not directory.archive_path.exists()
    assert not directory.archive_temporary_path.exists()


def test_published_archive_survives_persistent_temporary_unlink_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = RunDirectory(
        tmp_path / "runs", "proj", "PHASE", "20260820T120000000000Z"
    )
    for name in ("state.json", "request.json", "resolved.json", "result.json"):
        directory.write_text(name, "{}\n")
    original_unlink = Path.unlink

    def unlink(path: Path, *args, **kwargs) -> None:
        if path == directory.archive_temporary_path:
            raise PermissionError("injected cleanup failure")
        original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", unlink)
    result = archive_module.create(directory)

    assert result == directory.archive_path
    assert directory.archive_path.exists()
    with zipfile.ZipFile(directory.archive_path) as archive:
        assert archive.testzip() is None
