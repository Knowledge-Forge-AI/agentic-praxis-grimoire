"""APG60I descriptor-child allocation and cleanup failure matrix."""

from __future__ import annotations

import errno
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
SUPPORT = ROOT / "src/test/support"
sys.path.insert(0, str(SUPPORT))

from apg_repository_import_contract import (  # noqa: E402
    RepositoryImportError,
    execute_repository_consumer,
)


def _module():
    return importlib.import_module("apg_worker_temp_cleanup_contract")


def _environment(repository_root: Path):
    operation = importlib.import_module("apg_worker_temp_contract")
    return operation.worker_temp_environment(repository_root)


def _roots(tmp_path: Path) -> tuple[Path, Path]:
    repository = tmp_path / "repository"
    repository.mkdir()
    selected = tmp_path / "authorized"
    selected.mkdir()
    return repository, selected


def test_collision_retries_exclusively_and_preserves_existing_entry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repository, selected = _roots(tmp_path)
    existing = selected / "apg-worker-collision"
    existing.mkdir()
    names = iter(
        ("apg-worker-collision", "apg-worker-collision", "apg-worker-unique")
    )
    module = _module()
    monkeypatch.setenv("TMPDIR", str(selected))
    monkeypatch.setattr(module, "_candidate_name", lambda _prefix: next(names))

    with _environment(repository) as context:
        assert os.path.basename(context.environment["TMPDIR"]) == "apg-worker-unique"
        assert os.fstat(context.descriptor)

    assert tuple(selected.iterdir()) == (existing,)


def test_collision_retry_exhaustion_creates_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repository, selected = _roots(tmp_path)
    existing = selected / "apg-worker-collision"
    existing.mkdir()
    module = _module()
    monkeypatch.setenv("TMPDIR", str(selected))
    monkeypatch.setattr(
        module, "_candidate_name", lambda _prefix: "apg-worker-collision"
    )

    with pytest.raises(module.WorkerTempError, match="exhausted"):
        with _environment(repository):
            pytest.fail("exhausted allocation was accepted")
    assert tuple(selected.iterdir()) == (existing,)


def test_wrong_type_child_is_removed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repository, selected = _roots(tmp_path)
    module = _module()

    def create_file(state, name: str) -> None:
        descriptor = os.open(
            name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
            dir_fd=state.parent_fd,
        )
        os.close(descriptor)
        state.name = name

    monkeypatch.setenv("TMPDIR", str(selected))
    monkeypatch.setattr(module, "_mkdir_child", create_file)
    with pytest.raises(module.WorkerTempError, match="direct directory"):
        with _environment(repository):
            pytest.fail("wrong-type child was accepted")
    assert tuple(selected.iterdir()) == ()


def test_child_open_failure_is_cleaned(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repository, selected = _roots(tmp_path)
    module = _module()
    monkeypatch.setenv("TMPDIR", str(selected))

    def refuse_open(_parent_fd: int, _name: str) -> int:
        raise OSError(errno.EACCES, "controlled")

    monkeypatch.setattr(module, "_open_child", refuse_open)
    with pytest.raises(module.WorkerTempError, match="cannot be opened"):
        with _environment(repository):
            pytest.fail("child-open failure was accepted")
    assert tuple(selected.iterdir()) == ()


def test_child_identity_replacement_is_not_followed_and_leaves_no_residue(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repository, selected = _roots(tmp_path)
    module = _module()
    original_verify = module._verify_child
    monkeypatch.setenv("TMPDIR", str(selected))

    def replace_before_verify(state) -> None:
        assert state.name is not None
        os.rename(
            state.name,
            f"{state.name}-detached",
            src_dir_fd=state.parent_fd,
            dst_dir_fd=state.parent_fd,
        )
        os.mkdir(state.name, 0o700, dir_fd=state.parent_fd)
        original_verify(state)

    monkeypatch.setattr(module, "_verify_child", replace_before_verify)
    with pytest.raises(module.WorkerTempError, match="changed during open"):
        with _environment(repository):
            pytest.fail("replaced child was accepted")
    assert tuple(selected.iterdir()) == ()


def test_keyboard_interrupt_cleans_child_and_closes_descriptor(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repository, selected = _roots(tmp_path)
    module = _module()
    descriptor: int | None = None
    monkeypatch.setenv("TMPDIR", str(selected))

    with pytest.raises(KeyboardInterrupt):
        with _environment(repository) as context:
            descriptor = context.descriptor
            raise KeyboardInterrupt
    assert tuple(selected.iterdir()) == ()
    assert descriptor is not None
    with pytest.raises(OSError):
        os.fstat(descriptor)


def test_keyboard_interrupt_immediately_after_mkdir_cleans_child(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repository, selected = _roots(tmp_path)
    module = _module()
    original_mkdir = module.os.mkdir
    monkeypatch.setenv("TMPDIR", str(selected))

    def create_then_interrupt(*args, **kwargs) -> None:
        original_mkdir(*args, **kwargs)
        raise KeyboardInterrupt

    monkeypatch.setattr(module.os, "mkdir", create_then_interrupt)
    with pytest.raises(KeyboardInterrupt):
        with _environment(repository):
            pytest.fail("post-mkdir interruption was not raised")
    assert tuple(selected.iterdir()) == ()


def test_body_failure_stays_primary_when_cleanup_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repository, selected = _roots(tmp_path)
    module = _module()
    monkeypatch.setenv("TMPDIR", str(selected))

    def refuse_cleanup(_state) -> None:
        raise module.WorkerTempError("controlled cleanup failure")

    monkeypatch.setattr(module, "_cleanup_child", refuse_cleanup)
    with pytest.raises(RuntimeError, match="primary") as failure:
        with _environment(repository):
            raise RuntimeError("primary body failure")
    assert failure.value.worker_temp_cleanup_failure == (
        "isolated worker temporary cleanup left residue"
    )
    for child in selected.iterdir():
        child.rmdir()


def test_cleanup_failure_closes_the_operation_descriptor(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repository, selected = _roots(tmp_path)
    module = _module()
    original_remove = module._remove_entries
    descriptor: int | None = None
    monkeypatch.setenv("TMPDIR", str(selected))

    def refuse_remove(_descriptor: int) -> None:
        raise module.WorkerTempError("controlled cleanup failure")

    monkeypatch.setattr(module, "_remove_entries", refuse_remove)
    with pytest.raises(module.WorkerTempError, match="cleanup"):
        with _environment(repository) as context:
            descriptor = context.descriptor
    assert descriptor is not None
    with pytest.raises(OSError):
        os.fstat(descriptor)
    monkeypatch.setattr(module, "_remove_entries", original_remove)
    for child in selected.iterdir():
        shutil.rmtree(child)


def test_descriptor_snapshot_preserves_body_failure_and_cleanup_evidence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repository, selected = _roots(tmp_path)
    (repository / "skills").mkdir()
    module = _module()
    snapshot = importlib.import_module("apg_repository_snapshot_contract")
    original_remove = module._remove_entries
    root_fd = os.open(repository, os.O_RDONLY | os.O_DIRECTORY)
    temp_fd = os.open(selected, os.O_RDONLY | os.O_DIRECTORY)

    def refuse_remove(_descriptor: int) -> None:
        raise module.WorkerTempError("controlled cleanup failure")

    monkeypatch.setattr(module, "_remove_entries", refuse_remove)
    try:
        with pytest.raises(RuntimeError, match="primary") as failure:
            with snapshot.worker_snapshot(root_fd, temp_fd):
                raise RuntimeError("primary snapshot body failure")
        assert failure.value.snapshot_cleanup_failure == (
            "worker snapshot cleanup left copied repository residue"
        )
    finally:
        os.close(temp_fd)
        os.close(root_fd)
        monkeypatch.setattr(module, "_remove_entries", original_remove)
        for child in selected.iterdir():
            shutil.rmtree(child)


def test_descriptor_snapshot_does_not_mislabel_a_worker_temp_body_failure(
    tmp_path: Path,
) -> None:
    repository, selected = _roots(tmp_path)
    (repository / "skills").mkdir()
    module = _module()
    snapshot = importlib.import_module("apg_repository_snapshot_contract")
    root_fd = os.open(repository, os.O_RDONLY | os.O_DIRECTORY)
    temp_fd = os.open(selected, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(module.WorkerTempError, match="primary") as failure:
            with snapshot.worker_snapshot(root_fd, temp_fd):
                raise module.WorkerTempError("primary body failure")
        assert not hasattr(failure.value, "snapshot_cleanup_failure")
        assert tuple(selected.iterdir()) == ()
    finally:
        os.close(temp_fd)
        os.close(root_fd)


def test_descriptor_snapshot_does_not_mislabel_cleanup_subclass_body_failure(
    tmp_path: Path,
) -> None:
    repository, selected = _roots(tmp_path)
    (repository / "skills").mkdir()
    module = _module()
    snapshot = importlib.import_module("apg_repository_snapshot_contract")
    root_fd = os.open(repository, os.O_RDONLY | os.O_DIRECTORY)
    temp_fd = os.open(selected, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(
            module.WorkerTempCleanupError, match="primary"
        ) as failure:
            with snapshot.worker_snapshot(root_fd, temp_fd):
                raise module.WorkerTempCleanupError("primary body failure")
        assert not hasattr(failure.value, "snapshot_cleanup_failure")
        assert tuple(selected.iterdir()) == ()
    finally:
        os.close(temp_fd)
        os.close(root_fd)


def test_descriptor_snapshot_preserves_cleaned_child_open_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repository, selected = _roots(tmp_path)
    (repository / "skills").mkdir()
    module = _module()
    snapshot = importlib.import_module("apg_repository_snapshot_contract")
    root_fd = os.open(repository, os.O_RDONLY | os.O_DIRECTORY)
    temp_fd = os.open(selected, os.O_RDONLY | os.O_DIRECTORY)

    def refuse_open(_parent_fd: int, _name: str) -> int:
        raise OSError(errno.EACCES, "controlled")

    monkeypatch.setattr(module, "_open_child", refuse_open)
    try:
        with pytest.raises(module.WorkerTempError, match="cannot be opened"):
            with snapshot.worker_snapshot(root_fd, temp_fd):
                pytest.fail("child-open failure was accepted")
        assert tuple(selected.iterdir()) == ()
    finally:
        os.close(temp_fd)
        os.close(root_fd)


def test_descriptor_snapshot_restore_failure_closes_saved_descriptor(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repository, selected = _roots(tmp_path)
    (repository / "skills").mkdir()
    snapshot = importlib.import_module("apg_repository_snapshot_contract")
    original_fchdir = snapshot.os.fchdir
    outside_fd = os.open(".", os.O_RDONLY | os.O_DIRECTORY)
    root_fd = os.open(repository, os.O_RDONLY | os.O_DIRECTORY)
    temp_fd = os.open(selected, os.O_RDONLY | os.O_DIRECTORY)
    calls: list[int] = []

    def fail_restore(descriptor: int) -> None:
        calls.append(descriptor)
        if len(calls) > 1:
            raise OSError(errno.EIO, "controlled restore failure")
        original_fchdir(descriptor)

    monkeypatch.setattr(snapshot.os, "fchdir", fail_restore)
    try:
        with pytest.raises(snapshot.SnapshotCleanupError):
            with snapshot.worker_snapshot(root_fd, temp_fd):
                pass
        assert len(calls) == 2
        with pytest.raises(OSError):
            os.fstat(calls[1])
    finally:
        monkeypatch.setattr(snapshot.os, "fchdir", original_fchdir)
        original_fchdir(outside_fd)
        os.close(outside_fd)
        os.close(temp_fd)
        os.close(root_fd)
        for child in selected.iterdir():
            shutil.rmtree(child)


def test_substituted_child_symlink_is_unlinked_without_following_target(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repository, selected = _roots(tmp_path)
    marker = repository / "must-remain"
    marker.write_text("unchanged\n", encoding="utf-8")
    module = _module()
    monkeypatch.setenv("TMPDIR", str(selected))

    with _environment(repository) as context:
        child = Path(context.environment["TMPDIR"])
        detached = selected / f"{child.name}-detached"
        child.rename(detached)
        child.symlink_to(repository, target_is_directory=True)

    assert marker.read_text(encoding="utf-8") == "unchanged\n"
    assert tuple(selected.iterdir()) == ()


def test_final_root_revalidation_rejects_recreated_entry_after_body(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repository, selected = _roots(tmp_path)
    original = tmp_path / "authorized-original"
    module = _module()
    monkeypatch.setenv("TMPDIR", str(selected))
    try:
        with pytest.raises(module.WorkerTempError, match="changed"):
            with _environment(repository):
                selected.rename(original)
                selected.mkdir()
        assert tuple(original.iterdir()) == ()
        assert tuple(selected.iterdir()) == ()
    finally:
        selected.rmdir()
        original.rename(selected)


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


def _run_import_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    replacement,
) -> None:
    repository = _repository(tmp_path)
    selected = tmp_path / "authorized"
    selected.mkdir()
    module = importlib.import_module("apg_repository_import_contract")
    monkeypatch.setenv("TMPDIR", str(selected))
    monkeypatch.setattr(module.subprocess, "run", replacement)
    with pytest.raises(RepositoryImportError):
        execute_repository_consumer(
            repository, "libexec/apg_skill_topology.py", "topology"
        )
    assert tuple(selected.iterdir()) == ()


def test_worker_launch_failure_cleans_operation_child(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fail_launch(*_args, **_kwargs):
        raise OSError("controlled launch failure")

    _run_import_failure(monkeypatch, tmp_path, fail_launch)


def test_request_encoding_failure_cleans_operation_child(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repository = _repository(tmp_path)
    selected = tmp_path / "authorized"
    selected.mkdir()
    module = importlib.import_module("apg_repository_import_contract")
    original_dumps = module.json.dumps
    monkeypatch.setenv("TMPDIR", str(selected))

    def fail_request(value, *args, **kwargs):
        if isinstance(value, dict) and "sources" in value and "temp_fd" in value:
            raise TypeError("controlled request encoding failure")
        return original_dumps(value, *args, **kwargs)

    monkeypatch.setattr(module.json, "dumps", fail_request)
    with pytest.raises(RepositoryImportError):
        execute_repository_consumer(
            repository, "libexec/apg_skill_topology.py", "topology"
        )
    assert tuple(selected.iterdir()) == ()


@pytest.mark.parametrize("shape", ("nonzero", "malformed", "failed-envelope"))
def test_worker_result_failures_clean_operation_child(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, shape: str
) -> None:
    def result(args, **_kwargs):
        if shape == "nonzero":
            return subprocess.CompletedProcess(args, 7, b"", b"")
        if shape == "malformed":
            return subprocess.CompletedProcess(args, 0, b"not-json", b"")
        body = json.dumps(
            {"ok": False, "result": None, "schema_version": 3},
            separators=(",", ":"),
        ).encode("utf-8")
        return subprocess.CompletedProcess(args, 0, body, b"")

    _run_import_failure(monkeypatch, tmp_path, result)
