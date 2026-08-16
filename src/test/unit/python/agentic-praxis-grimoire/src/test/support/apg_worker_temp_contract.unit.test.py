"""Authorized temporary-storage controls for isolated repository workers."""

from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
SUPPORT = ROOT / "src/test/support"
sys.path.insert(0, str(SUPPORT))

from apg_repository_import_contract import (  # noqa: E402
    REQUEST_SCHEMA_VERSION,
    RepositoryImportError,
    execute_repository_consumer,
)
from apg_worker_temp_contract import (  # noqa: E402
    WorkerTempError,
    worker_temp_environment,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _repository(root: Path) -> Path:
    repository = root / "repository"
    (repository / "skills").mkdir(parents=True)
    _write(
        repository / "libexec/apg_skill_topology.py",
        "def discover_canonical_leaves(root, skills, report):\n"
        "    return tuple()\n",
    )
    return repository


def _successful_result(args) -> subprocess.CompletedProcess[bytes]:
    body = json.dumps(
        {
            "ok": True,
            "result": {"diagnostics": 0, "names": []},
            "schema_version": REQUEST_SCHEMA_VERSION,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    return subprocess.CompletedProcess(args, 0, body, b"")


def _missing_temp(
    monkeypatch: pytest.MonkeyPatch, _root: Path, _repository: Path
) -> None:
    monkeypatch.delenv("TMPDIR", raising=False)


def _relative_temp(
    monkeypatch: pytest.MonkeyPatch, _root: Path, _repository: Path
) -> None:
    monkeypatch.setenv("TMPDIR", "relative-temp")


def _inside_repository_temp(
    monkeypatch: pytest.MonkeyPatch, _root: Path, repository: Path
) -> None:
    selected = repository / "temporary"
    selected.mkdir()
    monkeypatch.setenv("TMPDIR", str(selected))


def _file_temp(
    monkeypatch: pytest.MonkeyPatch, root: Path, _repository: Path
) -> None:
    selected = root / "selected"
    selected.write_text("not a directory\n", encoding="utf-8")
    monkeypatch.setenv("TMPDIR", str(selected))


def _symlink_temp(
    monkeypatch: pytest.MonkeyPatch, root: Path, _repository: Path
) -> None:
    target = root / "target"
    target.mkdir()
    selected = root / "selected"
    selected.symlink_to(target, target_is_directory=True)
    monkeypatch.setenv("TMPDIR", str(selected))


def _dangling_symlink_temp(
    monkeypatch: pytest.MonkeyPatch, root: Path, _repository: Path
) -> None:
    selected = root / "selected"
    selected.symlink_to(root / "target", target_is_directory=True)
    monkeypatch.setenv("TMPDIR", str(selected))


def _symlink_ancestor_temp(
    monkeypatch: pytest.MonkeyPatch, root: Path, _repository: Path
) -> None:
    target = root / "target"
    (target / "selected").mkdir(parents=True)
    ancestor = root / "linked-parent"
    ancestor.symlink_to(target, target_is_directory=True)
    monkeypatch.setenv("TMPDIR", str(ancestor / "selected"))


def _control_temp(
    monkeypatch: pytest.MonkeyPatch, root: Path, _repository: Path
) -> None:
    monkeypatch.setenv("TMPDIR", str(root / "selected") + "\ncontrol")


def test_worker_receives_only_stripped_environment_and_one_temp_family(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repository = _repository(tmp_path)
    selected = tmp_path / "authorized"
    selected.mkdir()
    monkeypatch.setenv("TMPDIR", str(selected))
    monkeypatch.setenv("UNRELATED_PARENT_VALUE", "must-not-cross")
    module = importlib.import_module("apg_repository_import_contract")
    captured: dict[str, object] = {}

    def capture(args, **kwargs):
        captured.update(kwargs)
        worker_root = Path(kwargs["env"]["TMPDIR"])
        assert worker_root.parent == selected
        assert worker_root.is_dir()
        assert not repository in worker_root.parents
        return _successful_result(args)

    monkeypatch.setattr(module.subprocess, "run", capture)
    execute_repository_consumer(
        repository, "libexec/apg_skill_topology.py", "topology"
    )
    environment = captured["env"]
    assert set(environment) == {"LC_ALL", "PATH", "TMPDIR", "TMP", "TEMP"}
    assert environment["TMPDIR"] == environment["TMP"] == environment["TEMP"]
    assert tuple(selected.iterdir()) == ()


def test_parent_removes_worker_residue_after_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repository = _repository(tmp_path)
    selected = tmp_path / "authorized"
    selected.mkdir()
    monkeypatch.setenv("TMPDIR", str(selected))
    module = importlib.import_module("apg_repository_import_contract")

    def timeout(args, **kwargs):
        worker_root = Path(kwargs["env"]["TMPDIR"])
        _write(worker_root / "apg-consumer-snapshot-residue/owner", "copy\n")
        raise subprocess.TimeoutExpired(args, 1)

    monkeypatch.setattr(module.subprocess, "run", timeout)
    with pytest.raises(RepositoryImportError, match="isolated"):
        execute_repository_consumer(
            repository, "libexec/apg_skill_topology.py", "topology"
        )
    assert tuple(selected.iterdir()) == ()


@pytest.mark.parametrize(
    "configure",
    (
        _missing_temp,
        _relative_temp,
        _inside_repository_temp,
        _file_temp,
        _symlink_temp,
        _dangling_symlink_temp,
        _symlink_ancestor_temp,
        _control_temp,
    ),
    ids=lambda configure: configure.__name__.removeprefix("_").removesuffix("_temp"),
)
def test_invalid_worker_temp_roots_fail_before_launch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, configure
) -> None:
    repository = _repository(tmp_path)
    configure(monkeypatch, tmp_path, repository)
    with pytest.raises(WorkerTempError):
        with worker_temp_environment(repository):
            pytest.fail("invalid temporary root was accepted")


def test_worker_temp_cleanup_message_does_not_expose_selected_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repository = _repository(tmp_path)
    selected = tmp_path / "authorized"
    selected.mkdir()
    monkeypatch.setenv("TMPDIR", str(selected))
    module = importlib.import_module("apg_worker_temp_contract")
    cleanup = importlib.import_module("apg_worker_temp_cleanup_contract")

    def refuse(_state) -> None:
        raise module.WorkerTempError("controlled residue")

    monkeypatch.setattr(cleanup, "_cleanup_child", refuse)
    with pytest.raises(WorkerTempError) as failure:
        with worker_temp_environment(repository):
            pass
    assert str(selected) not in str(failure.value)
    for child in selected.iterdir():
        child.rmdir()
