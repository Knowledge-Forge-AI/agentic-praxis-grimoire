"""Focused regressions for bounded stage-evidence handoff details."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

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


class ArtifactDirectory:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.mkdir()

    def write_bytes(self, name: str, data: bytes) -> None:
        (self.path / name).write_bytes(data)


def test_prompt_summary_uses_normalization_totals_and_omissions() -> None:
    inline_changes = [
        {"path": f"staged-{index:03}.txt", "status": "modified"}
        for index in range(stage_delta_module.MAX_STAGE_INLINE_DELTAS)
    ]
    inline_intent = [f"intent-{index:03}.txt" for index in range(64)]
    state: dict[str, Any] = {
        "index_normalizations": [
            {
                "stage": "work",
                "safety": "safe_restored",
                "staged_changes": inline_changes,
                "staged_changes_total_count": 5000,
                "staged_changes_inline_count": len(inline_changes),
                "staged_changes_omitted_count": 4744,
                "intent_to_add_paths": inline_intent,
                "intent_to_add_paths_total_count": 100,
                "intent_to_add_paths_inline_count": len(inline_intent),
                "intent_to_add_paths_omitted_count": 36,
                "overflow": {
                    "written_count": 300,
                    "omitted_overflow_count": 4444,
                    "artifact_written": True,
                },
            }
        ]
    }

    summary = stage_delta_module.format_stage_deltas_summary(state)

    assert "5000 path(s) (256 inline, 4744 omitted)" in summary
    assert "intent-to-add: 100 path(s) (64 inline, 36 omitted)" in summary
    assert "overflow JSONL: 300 written, 4444 omitted" in summary
    assert "index normalization safe_restored: 256 path(s)" not in summary


def test_overflow_budget_is_shared_by_index_and_stage_artifacts(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = ArtifactDirectory(tmp_path / "run")
    entry_index = gitstate_module.index_identity(repository)
    for index in range(300):
        (repository / f"intent-{index:03}.txt").write_text(f"intent {index}\n")
    git(repository, "add", "-N", ".")

    monkeypatch.setattr(stage_delta_module, "MAX_OVERFLOW_AGGREGATE_BYTES", 1000)
    state: dict[str, Any] = {}
    normalization = stage_delta_module.normalize_index_if_needed(
        repository,
        entry_index,
        state,
        stage_name="work",
        directory=directory,
    )
    assert normalization is not None
    index_overflow = normalization["overflow"]
    index_bytes = index_overflow["bytes"]
    assert index_bytes > 0

    stage_deltas = [
        {
            "stage": "work",
            "path": f"product-{index:03}.txt",
            "status": "modified",
            "classification": "product",
        }
        for index in range(300)
    ]
    stage_delta_module._record_deltas_to_ledger(
        state,
        "work",
        "before",
        "after",
        {},
        {},
        stage_deltas,
        {},
        directory=directory,
    )
    stage_overflow = state["stage_delta_ledger"]["stages"]["work"]["overflow"]
    aggregate = state["stage_delta_ledger"]["overflow_aggregate"]

    assert stage_overflow["aggregate_bytes_before"] == index_bytes
    assert stage_overflow["truncated"] is True
    assert aggregate["bytes"] == index_bytes + stage_overflow["bytes"]
    assert aggregate["bytes"] <= 1000
    assert aggregate["artifact_count"] == 2


def test_rewritten_index_overflow_uses_latest_same_named_record() -> None:
    old = {
        "name": "work.index_normalizations.jsonl",
        "bytes": 111,
        "truncated": False,
        "artifact_written": True,
    }
    new = {
        "name": "work.index_normalizations.jsonl",
        "bytes": 222,
        "truncated": False,
        "artifact_written": True,
    }
    state: dict[str, Any] = {
        "stage_delta_ledger": {
            "stages": {
                "work": {
                    "index_normalizations": [{"overflow": old}],
                }
            }
        },
        "index_normalizations": [
            {"overflow": old},
            {"overflow": new},
        ],
    }

    assert stage_delta_module._overflow_bytes_in_use(state) == 222
    aggregate = stage_delta_module._refresh_overflow_aggregate(state)
    assert aggregate["bytes"] == 222
    assert aggregate["artifact_count"] == 1


def test_metadata_capture_uses_one_tracked_set_instead_of_path_subprocesses(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    metadata = {
        ".scratch/one.log": {
            "exists": True,
            "type": "file",
            "size_bytes": 1,
            "mtime": 1,
        },
        ".scratch/two.log": {
            "exists": True,
            "type": "file",
            "size_bytes": 2,
            "mtime": 2,
        },
    }
    monkeypatch.setattr(
        stage_delta_module,
        "scan_operational_metadata",
        lambda root, observation=None: metadata,
    )
    monkeypatch.setattr(
        stage_delta_module,
        "_tracked_path_set",
        lambda root, observation=None: set(),
    )

    def unexpected_per_path_lookup(root: Path, path: str) -> bool:
        raise AssertionError(f"per-path tracked lookup for {path}")

    monkeypatch.setattr(stage_delta_module, "is_tracked", unexpected_per_path_lookup)
    state: dict[str, Any] = {}

    deltas = stage_delta_module.capture_stage_boundary(
        repository,
        state,
        stage="work",
        before_tree="same-tree",
        after_tree="same-tree",
        before_index={},
        after_index={},
        before_metadata={},
    )

    assert {delta["path"] for delta in deltas} == set(metadata)
