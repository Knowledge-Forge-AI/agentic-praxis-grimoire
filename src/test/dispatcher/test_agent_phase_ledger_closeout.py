"""Focused regressions for stage-boundary ledger closeout evidence."""

from __future__ import annotations

import json
from typing import Any
import subprocess
from pathlib import Path

import pytest

from agent_phase import gitstate as gitstate_module
from agent_phase import stage_delta as stage_delta_module


def git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, check=True, text=True
    )
    return completed.stdout.strip()


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "Tester")
    git(root, "config", "user.email", "tester@example.com")
    (root / "README.md").write_text("# test\n")
    git(root, "add", "README.md")
    git(root, "commit", "-m", "initial")
    return root


class DummyDirectory:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.mkdir()

    def write_bytes(self, name: str, data: bytes) -> None:
        (self.path / name).write_bytes(data)


def test_failed_boundary_preserves_candidate_when_ledger_capture_fails(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = gitstate_module.capture_entry(repository)
    state: dict[str, Any] = {}
    boundary = stage_delta_module.StageBoundary(repository, "work", state, entry=entry)

    (repository / "failed.py").write_text("preserved failed-stage bytes\n")

    def fail_capture(*args: object, **kwargs: object) -> list[dict[str, Any]]:
        raise RuntimeError("synthetic ledger failure")

    monkeypatch.setattr(stage_delta_module, "capture_stage_boundary", fail_capture)
    assert boundary.close(ok=False, error=RuntimeError("provider transport")) == []

    assert state["stage_delta_capture_error"]["code"] == "RuntimeError"
    assert state["failure_candidate"]["stage"] == "work"
    assert state["failure_candidate"]["tree"]
    assert state["failure_candidate"]["candidate_paths"] == ["failed.py"]


def test_index_normalization_is_in_stage_ledger_and_prompt_handoff(
    repository: Path,
) -> None:
    entry = gitstate_module.capture_entry(repository)
    (repository / "intent.py").write_text("preserve\n")
    git(repository, "add", "-N", "intent.py")
    state: dict[str, Any] = {}
    record = stage_delta_module.normalize_index_if_needed(
        repository, entry.index_identity, state, stage_name="work"
    )
    assert record is not None

    stage_delta_module.capture_stage_boundary(
        repository, state, stage="work", before_tree=entry.tree
    )
    stage = state["stage_delta_ledger"]["stages"]["work"]
    assert stage["index_normalizations"][0]["intent_to_add_paths"] == ["intent.py"]
    summary = stage_delta_module.format_stage_deltas_summary(state)
    assert "index normalization" in summary
    assert "intent.py" in summary


def test_run_and_overflow_bounds_retain_counts_and_complete_jsonl(
    repository: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    directory = DummyDirectory(tmp_path / "run")
    state: dict[str, Any] = {}
    first = [
        {"stage": "one", "path": f"one-{i}-" + "x" * 5000, "status": "added", "classification": "product"}
        for i in range(300)
    ]
    second = [
        {"stage": "two", "path": f"two-{i}-" + "x" * 5000, "status": "modified", "classification": "product"}
        for i in range(300)
    ]
    stage_delta_module._record_deltas_to_ledger(
        state, "one", "before", "one-tree", {}, {}, first, {}, directory=directory
    )
    stage_delta_module._record_deltas_to_ledger(
        state, "two", "one-tree", "two-tree", {}, {}, second, {}, directory=directory
    )
    small_for_run = [
        {"stage": "extra", "path": f"extra-{i}", "status": "modified", "classification": "product"}
        for i in range(300)
    ]
    for stage_name in ("three", "four", "five"):
        stage_delta_module._record_deltas_to_ledger(
            state, stage_name, "before", stage_name, {}, {}, small_for_run, {}, directory=directory
        )
    ledger = state["stage_delta_ledger"]
    assert len(ledger["deltas"]) == stage_delta_module.MAX_RUN_INLINE_DELTAS
    assert ledger["total_deltas_count"] == 1500
    assert ledger["omitted_deltas_count"] == 1500 - stage_delta_module.MAX_RUN_INLINE_DELTAS
    assert ledger["status_counts"] == {"added": 300, "modified": 1200}
    assert ledger["stage_counts"] == {name: 300 for name in ("one", "two", "three", "four", "five")}

    raw = (directory.path / "one.deltas.jsonl").read_bytes()
    assert len(raw) <= stage_delta_module.MAX_OVERFLOW_CHUNK_BYTES
    assert raw.endswith(b"\n")
    assert all(json.loads(line) for line in raw.splitlines())

    monkeypatch.setattr(stage_delta_module, "MAX_OVERFLOW_AGGREGATE_BYTES", 500)
    bounded_state: dict[str, Any] = {}
    small = [
        {"stage": "small", "path": f"small-{i}-" + "y" * 40, "status": "added", "classification": "product"}
        for i in range(270)
    ]
    stage_delta_module._record_deltas_to_ledger(
        bounded_state, "small", "before", "small-tree", {}, {}, small, {}, directory=directory
    )
    stage_delta_module._record_deltas_to_ledger(
        bounded_state, "small-two", "small-tree", "small-two-tree", {}, {}, small, {}, directory=directory
    )
    aggregate = bounded_state["stage_delta_ledger"]["overflow_aggregate"]
    assert aggregate["bytes"] <= 500
    assert aggregate["truncated"] is True
