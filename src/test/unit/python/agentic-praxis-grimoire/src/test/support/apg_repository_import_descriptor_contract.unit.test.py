"""Descriptor cleanup controls for isolated repository consumers."""

from __future__ import annotations

import importlib
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
    RepositoryImportError,
    execute_repository_consumer,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _materialize(root: Path) -> None:
    _write(
        root / "skills/css-language-profile/SKILL.md",
        "---\nname: css-language-profile\ndescription: Test.\n---\n",
    )
    _write(
        root / "libexec/apg_skill_topology.py",
        "def discover_canonical_leaves(root, skills, report):\n"
        "    return tuple(path for path in skills.iterdir() if path.is_dir())\n",
    )


@pytest.mark.parametrize("failure", ("timeout", "interrupt"))
def test_worker_descriptors_close_on_timeout_and_interrupt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, failure: str
) -> None:
    root = tmp_path / "repository"
    _materialize(root)
    module = importlib.import_module("apg_repository_import_contract")
    captured: dict[str, object] = {}

    def fail_run(*args, **kwargs):
        captured.update(kwargs)
        if failure == "timeout":
            raise subprocess.TimeoutExpired(args[0], 1)
        raise KeyboardInterrupt

    monkeypatch.setattr(module.subprocess, "run", fail_run)
    expected = RepositoryImportError if failure == "timeout" else KeyboardInterrupt
    with pytest.raises(expected):
        execute_repository_consumer(
            root, "libexec/apg_skill_topology.py", "topology"
        )
    for descriptor in captured["pass_fds"]:
        with pytest.raises(OSError):
            os.fstat(descriptor)


@pytest.mark.parametrize("failure", ("encode", "oversized"))
def test_worker_descriptors_close_before_launch_failures(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, failure: str
) -> None:
    root = tmp_path / "repository"
    _materialize(root)
    module = importlib.import_module("apg_repository_import_contract")
    captured: list[int] = []
    original_dumps = module.json.dumps

    def capture_dumps(value, *args, **kwargs):
        captured.extend((value["root_fd"], value["root_parent_fd"]))
        if failure == "encode":
            raise RuntimeError("controlled encoding failure")
        return original_dumps(value, *args, **kwargs)

    monkeypatch.setattr(module.json, "dumps", capture_dumps)
    if failure == "oversized":
        monkeypatch.setattr(module, "MAX_REQUEST_BYTES", 1)
    with pytest.raises((RuntimeError, RepositoryImportError)):
        execute_repository_consumer(
            root, "libexec/apg_skill_topology.py", "topology"
        )
    for descriptor in captured:
        with pytest.raises(OSError):
            os.fstat(descriptor)


def test_worker_descriptor_partial_acquisition_is_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "repository"
    _materialize(root)
    path_module = importlib.import_module("apg_repository_path_contract")
    captured: list[int] = []
    original = path_module.RepositoryPathContract.duplicate_root_descriptor

    def capture_duplicate(self):
        descriptor = original(self)
        captured.append(descriptor)
        return descriptor

    def fail_parent_duplicate(self):
        raise OSError("controlled partial acquisition failure")

    monkeypatch.setattr(
        path_module.RepositoryPathContract,
        "duplicate_root_descriptor",
        capture_duplicate,
    )
    monkeypatch.setattr(
        path_module.RepositoryPathContract,
        "duplicate_root_parent_descriptor",
        fail_parent_duplicate,
    )
    with pytest.raises(OSError):
        execute_repository_consumer(
            root, "libexec/apg_skill_topology.py", "topology"
        )
    for descriptor in captured:
        with pytest.raises(OSError):
            os.fstat(descriptor)
