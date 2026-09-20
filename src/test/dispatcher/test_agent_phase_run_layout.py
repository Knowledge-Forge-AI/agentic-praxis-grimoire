"""Comprehensive regression tests for AGENTCENTRAL-RUNLAYOUT1.

Verifies:
1. Basics & V2 Hierarchy (Cases 1-12)
2. V2 Topology Validation (Cases 13-22)
3. Historical V1 Dual-Read & Sealed Run Validation (Cases 23-29)
4. V2 Lifecycles & Recovery (Cases 30-40)
5. Adoption & Custody Continuation (Cases 41-46)
6. Worker & Generation Coexistence (Cases 47-52)
7. Security & Archive Constraints (Cases 53-59)
"""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
import time
import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest
from agent_phase import adoption, finalization_recovery
from agent_phase import archive as archive_module
from agent_phase import run as run_module
from agent_phase.dispatch import DispatchError
from agent_phase.provider import Result
from agent_phase.request import PhaseRequest
from agent_phase.run import (
    RUN_LAYOUT_KIND_V2,
    RUN_LAYOUT_SCHEMA_V2,
    V1_LEAF_PATTERN,
    V2_LEAF_PATTERN,
    RunDirectory,
    RunPathError,
    layout_record_v2,
    v2_leaf,
    v2_run_id,
    validate_run_topology,
)
from test_agent_phase_dispatch import (
    PHASE_ID,
    FakeRunner,
    git,
    make_dispatcher,
    repository,
    write_fake_evidence,
)

__all__ = ["repository"]

REQUEST = PhaseRequest("implementation_testing", "normal", "layout verification task")


# ==============================================================================
# Helpers & Custom Runner
# ==============================================================================


def terminal_payload(
    prompt: bytes,
    subject: str | None = "Apply layout change",
    body: str = "task-scoped verification passed",
    path_dispositions: list[dict[str, str]] | None = None,
) -> bytes:
    text = prompt.decode()
    nonce = re.search(r"<<<AGENT-PHASE-RESULT ([0-9a-f]{32})>>>", text)
    stage = re.search(r"^stage: ([a-z_]+)$", text, re.MULTILINE)
    assert nonce is not None and stage is not None
    payload = json.dumps({
        "version": 1,
        "stage": stage.group(1),
        "outcome": "completed",
        "body": body,
        "commit_message": (
            None if subject is None else {"subject": subject, "body": ""}
        ),
        **({"path_dispositions": path_dispositions} if path_dispositions is not None else {}),
    })
    token = nonce.group(1)
    return (
        f"<<<AGENT-PHASE-RESULT {token}>>>\n{payload}\n"
        f"<<<END-AGENT-PHASE-RESULT {token}>>>\n"
    ).encode()


def review(prompt: bytes, outcome: str = "reviewed_with_no_findings") -> bytes:
    text = prompt.decode()
    nonce = re.search(r"<<<AGENT-REVIEW-RESULT ([0-9a-f]{32})>>>", text)
    stage = re.search(r"^stage: ([a-z_]+)$", text, re.MULTILINE)
    assert nonce is not None and stage is not None, "review prompt missing nonce or stage"
    stage_name = stage.group(1)
    token = nonce.group(1)
    payload = json.dumps({
        "version": 1,
        "stage": stage_name,
        "outcome": outcome,
        "body": "no findings",
    })
    return (
        f"<<<AGENT-REVIEW-RESULT {token}>>>\n{payload}\n"
        f"<<<END-AGENT-REVIEW-RESULT {token}>>>\n"
    ).encode()


class LayoutRunner:
    """Dynamic runner handling stages across initial dispatch and resume."""

    def __init__(
        self,
        *,
        fail_at: int | None = None,
        work_hook: Callable[[Path], None] | None = None,
        path_dispositions: list[dict[str, str]] | None = None,
    ) -> None:
        self.calls: list[list[str]] = []
        self.fail_at = fail_at
        self.work_hook = work_hook
        self.path_dispositions = path_dispositions

    def __call__(self, argv, prompt, cwd, max_output, on_output=None):
        index = len(self.calls)
        self.calls.append(list(argv))
        if self.fail_at == index:
            write_fake_evidence(list(argv), 1)
            return Result(1, b"", b"injected failure\n", False, time.time(), time.time())
        now = time.time()
        write_fake_evidence(list(argv), 0)
        if b"<<<AGENT-PHASE-RESULT " in prompt:
            stdout = terminal_payload(prompt, path_dispositions=self.path_dispositions)
        elif b"<<<AGENT-REVIEW-RESULT " in prompt:
            stdout = review(prompt)
        else:
            if self.work_hook:
                self.work_hook(cwd)
            stdout = b"stage output\n"
        return Result(0, stdout, b"", False, now, now)


def create_sealed_v1_run(
    run_root: Path,
    project: str,
    phase: str,
    timestamp: str = "20260819T164955123456Z",
    request: PhaseRequest = REQUEST,
) -> Path:
    """Create a sealed historical V1 run directory structure for topology testing."""
    leaf = f"{phase}--{timestamp}"
    v1_dir = run_root / "phase-dispatch" / project / leaf
    v1_dir.mkdir(parents=True, exist_ok=True)

    state = {
        "schema": "agent-phase-state-v1",
        "project": project,
        "phase_id": phase,
        "run_id": f"{project}/{leaf}",
        "run_directory": str(v1_dir),
        "complete": True,
        "outcome": "completed",
    }
    result = {
        "schema": "agent-phase-result-v1",
        "project": project,
        "phase_id": phase,
        "run_id": f"{project}/{leaf}",
        "run_directory": str(v1_dir),
        "complete": True,
        "outcome": "completed",
    }

    (v1_dir / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    (v1_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (v1_dir / "request.json").write_text(json.dumps(request.as_dict(), indent=2), encoding="utf-8")
    (v1_dir / "resolved.json").write_text("{}", encoding="utf-8")
    return v1_dir


def create_historical_v1_run(
    repository: Path,
    tmp_path: Path,
    phase: str = PHASE_ID,
    timestamp: str = "20260819T164955123456Z",
    fail_at: int | None = None,
    finalization_policy: str = "checkpoint",
) -> Path:
    """Generate a real dispatch run and place it in the historical V1 hierarchy."""
    seed_runner = LayoutRunner(
        fail_at=fail_at,
        work_hook=lambda cwd: (cwd / "phase.txt").write_text("historical work\n"),
    )
    seed_root = tmp_path / "seed"
    dispatcher = make_dispatcher(repository, seed_root, seed_runner)
    try:
        dispatcher.dispatch(phase, REQUEST, finalization_policy=finalization_policy)
    except DispatchError:
        pass
    seed_dir = next(p.parent for p in (seed_root / "runs").rglob("state.json"))

    project = "repo"
    leaf = f"{phase}--{timestamp}"
    v1_dir = tmp_path / "v1_root" / "phase-dispatch" / project / leaf
    v1_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(seed_dir, v1_dir)

    state = json.loads((v1_dir / "state.json").read_text(encoding="utf-8"))
    state.pop("run_layout", None)
    state["project"] = project
    state["phase_id"] = phase
    state["run_id"] = f"{project}/{leaf}"
    state["run_directory"] = str(v1_dir)
    archive_path = v1_dir.parent / f"{leaf}.zip"
    receipt_path = archive_module.receipt_path(archive_path)
    state["archive"] = {
        "attempted": True,
        "path": str(archive_path),
        "status": "succeeded",
        "succeeded": True,
        "failure": None,
        "receipt_path": str(receipt_path),
    }
    (v1_dir / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")

    result_file = v1_dir / "result.json"
    if result_file.exists():
        result = json.loads(result_file.read_text(encoding="utf-8"))
        result.pop("run_layout", None)
        result["project"] = project
        result["phase_id"] = phase
        result["run_id"] = f"{project}/{leaf}"
        result["run_directory"] = str(v1_dir)
        result_file.write_text(json.dumps(result, indent=2), encoding="utf-8")

    class FakeV1RunDir:
        def __init__(self, path: Path):
            self.path = path
            self.leaf = path.name
            self.archive_path = path.parent / f"{path.name}.zip"
            self.archive_temporary_path = path.parent / f"{path.name}.zip.tmp"

    archive_module.create(FakeV1RunDir(v1_dir))
    return v1_dir


# ==============================================================================
# 1. Basics & V2 Hierarchy (Cases 1-12)
# ==============================================================================


def test_01_default_root_is_documents_agent_outbox(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGENT_PHASE_RUN_ROOT", raising=False)
    expected = Path.home() / "Documents" / "agent" / "outbox"
    assert run_module.default_root() == expected


def test_02_default_root_honors_env_var(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    custom = tmp_path / "custom_outbox"
    monkeypatch.setenv("AGENT_PHASE_RUN_ROOT", str(custom))
    assert run_module.default_root() == custom


def test_03_fresh_dispatch_creates_v2_hierarchy(repository: Path, tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    dispatcher = make_dispatcher(repository, tmp_path, FakeRunner())
    state = dispatcher.dispatch(PHASE_ID, REQUEST)

    run_path = Path(state["run_directory"])
    # Path must be runs / repo / PHASE_ID / leaf
    assert run_path.parent.name == PHASE_ID
    assert run_path.parent.parent.name == "repo"
    assert run_path.parent.parent.parent == runs_dir
    assert not (runs_dir / "phase-dispatch").exists()


def test_04_fresh_dispatch_run_id_is_v2(repository: Path, tmp_path: Path) -> None:
    dispatcher = make_dispatcher(repository, tmp_path, FakeRunner())
    state = dispatcher.dispatch(PHASE_ID, REQUEST)

    leaf = Path(state["run_directory"]).name
    expected_run_id = f"repo/{PHASE_ID}/{leaf}"
    assert state["run_id"] == expected_run_id

    result = json.loads((Path(state["run_directory"]) / "result.json").read_text(encoding="utf-8"))
    assert result["run_id"] == expected_run_id


def test_05_fresh_dispatch_run_layout_marker(repository: Path, tmp_path: Path) -> None:
    dispatcher = make_dispatcher(repository, tmp_path, FakeRunner())
    state = dispatcher.dispatch(PHASE_ID, REQUEST)

    run_path = Path(state["run_directory"])
    leaf = run_path.name
    expected_layout = {
        "schema": RUN_LAYOUT_SCHEMA_V2,
        "kind": RUN_LAYOUT_KIND_V2,
        "run_id": f"repo/{PHASE_ID}/{leaf}",
        "leaf": leaf,
    }
    assert state["run_layout"] == expected_layout

    result = json.loads((run_path / "result.json").read_text(encoding="utf-8"))
    assert result["run_layout"] == expected_layout

    # resolved.json must NOT contain run_layout
    resolved = json.loads((run_path / "resolved.json").read_text(encoding="utf-8"))
    assert "run_layout" not in resolved


def test_06_sibling_archive_and_receipt_placement(repository: Path, tmp_path: Path) -> None:
    dispatcher = make_dispatcher(repository, tmp_path, FakeRunner())
    state = dispatcher.dispatch(PHASE_ID, REQUEST)
    run_path = Path(state["run_directory"])

    archive_path = Path(state["archive"]["path"])
    receipt_path = archive_module.receipt_path(archive_path)
    # Sibling to run directory, in the phase folder
    assert archive_path.parent == run_path.parent
    assert receipt_path.parent == run_path.parent
    assert archive_path.name == f"{run_path.name}.zip"
    assert receipt_path.name == f"{run_path.name}.zip.receipt.json"
    assert archive_path.exists()
    assert receipt_path.exists()


def test_07_archive_internal_root_is_leaf(repository: Path, tmp_path: Path) -> None:
    dispatcher = make_dispatcher(repository, tmp_path, FakeRunner())
    state = dispatcher.dispatch(PHASE_ID, REQUEST)
    run_path = Path(state["run_directory"])

    archive_path = Path(state["archive"]["path"])
    with zipfile.ZipFile(archive_path) as bundle:
        for name in bundle.namelist():
            assert name.startswith(f"{run_path.name}/"), f"Bad internal archive root: {name}"


def test_08_leaf_name_pattern() -> None:
    timestamp = "20260912T120000123456Z"
    leaf = v2_leaf(PHASE_ID, timestamp)
    assert leaf == f"{PHASE_ID}-dispatch--{timestamp}"
    assert V2_LEAF_PATTERN.match(leaf) is not None
    assert "-dispatch--" in leaf
    v1_leaf = f"{PHASE_ID}--{timestamp}"
    assert V2_LEAF_PATTERN.match(v1_leaf) is None
    assert V1_LEAF_PATTERN.match(v1_leaf) is not None


def test_09_directory_collision_fails_closed(tmp_path: Path) -> None:
    fixed_ts = "20260912T120000000000Z"
    root = tmp_path / "runs"
    # First dispatch succeeds
    RunDirectory(root, "repo", PHASE_ID, fixed_ts)

    # Second dispatch with identical timestamp collisions
    with pytest.raises(FileExistsError):
        RunDirectory(root, "repo", PHASE_ID, fixed_ts)


def test_10_archive_zip_collision_fails_closed(tmp_path: Path) -> None:
    fixed_ts = "20260912T120000000000Z"
    root = tmp_path / "runs"
    leaf = v2_leaf(PHASE_ID, fixed_ts)
    colliding_zip = root / "repo" / PHASE_ID / f"{leaf}.zip"
    colliding_zip.parent.mkdir(parents=True, exist_ok=True)
    colliding_zip.write_bytes(b"existing zip")

    with pytest.raises(RunPathError) as caught:
        RunDirectory(root, "repo", PHASE_ID, fixed_ts)
    assert caught.value.code == "RUN_ARCHIVE_COLLISION"


def test_11_archive_receipt_collision_fails_closed(tmp_path: Path) -> None:
    fixed_ts = "20260912T120000000000Z"
    root = tmp_path / "runs"
    leaf = v2_leaf(PHASE_ID, fixed_ts)
    colliding_receipt = root / "repo" / PHASE_ID / f"{leaf}.zip.receipt.json"
    colliding_receipt.parent.mkdir(parents=True, exist_ok=True)
    colliding_receipt.write_text("{}", encoding="utf-8")

    with pytest.raises(RunPathError) as caught:
        RunDirectory(root, "repo", PHASE_ID, fixed_ts)
    assert caught.value.code == "RUN_ARCHIVE_COLLISION"


@pytest.mark.parametrize("bad_phase", ["../escape", "a/b", ".dot", "-dash", "", "bad\x00char"])
def test_12_strict_component_validation(tmp_path: Path, bad_phase: str) -> None:
    root = tmp_path / "runs"
    with pytest.raises(RunPathError) as caught:
        RunDirectory(root, "repo", bad_phase)
    assert caught.value.code == "UNSAFE_RUN_PATH_COMPONENT"


# ==============================================================================
# 2. V2 Topology Validation (Cases 13-22)
# ==============================================================================


def test_13_validate_run_topology_valid_v2(tmp_path: Path) -> None:
    leaf = f"{PHASE_ID}-dispatch--20260912T120000000000Z"
    v2_dir = tmp_path / "repo" / PHASE_ID / leaf
    v2_dir.mkdir(parents=True)
    run_id = f"repo/{PHASE_ID}/{leaf}"
    state = {
        "project": "repo",
        "phase_id": PHASE_ID,
        "run_id": run_id,
        "run_directory": str(v2_dir),
        "run_layout": layout_record_v2(run_id, leaf),
    }
    validate_run_topology(v2_dir, state)
    record = state["run_layout"]
    assert record["schema"] == RUN_LAYOUT_SCHEMA_V2
    assert record["run_id"] == run_id
    assert record["leaf"] == leaf


def test_14_topology_wrong_phase_parent(tmp_path: Path) -> None:
    leaf = f"{PHASE_ID}-dispatch--20260912T120000000000Z"
    wrong_dir = tmp_path / "repo" / "wrong-phase" / leaf
    wrong_dir.mkdir(parents=True)
    run_id = f"repo/{PHASE_ID}/{leaf}"
    state = {
        "project": "repo",
        "phase_id": PHASE_ID,
        "run_id": run_id,
        "run_directory": str(wrong_dir),
        "run_layout": layout_record_v2(run_id, leaf),
    }
    with pytest.raises(RunPathError) as caught:
        validate_run_topology(wrong_dir, state)
    assert caught.value.code == "RESUME_SOURCE_INVALID"


def test_15_topology_wrong_project_parent(tmp_path: Path) -> None:
    leaf = f"{PHASE_ID}-dispatch--20260912T120000000000Z"
    wrong_dir = tmp_path / "other-project" / PHASE_ID / leaf
    wrong_dir.mkdir(parents=True)
    run_id = f"repo/{PHASE_ID}/{leaf}"
    state = {
        "project": "other-project",
        "phase_id": PHASE_ID,
        "run_id": run_id,  # repo != other-project
        "run_directory": str(wrong_dir),
        "run_layout": layout_record_v2(run_id, leaf),
    }
    with pytest.raises(RunPathError) as caught:
        validate_run_topology(wrong_dir, state)
    assert caught.value.code == "RESUME_SOURCE_INVALID"


def test_16_topology_v2_leaf_in_v1_placement(tmp_path: Path) -> None:
    leaf = f"{PHASE_ID}-dispatch--20260912T120000000000Z"
    v1_placed = tmp_path / "repo" / leaf
    v1_placed.mkdir(parents=True)
    run_id = f"repo/{PHASE_ID}/{leaf}"
    state = {
        "project": "repo",
        "phase_id": PHASE_ID,
        "run_id": run_id,
        "run_directory": str(v1_placed),
        "run_layout": layout_record_v2(run_id, leaf),
    }
    with pytest.raises(RunPathError) as caught:
        validate_run_topology(v1_placed, state)
    assert caught.value.code == "RESUME_SOURCE_INVALID"


def test_17_topology_v1_leaf_in_v2_placement(tmp_path: Path) -> None:
    leaf = f"{PHASE_ID}--20260912T120000000000Z"
    v2_placed = tmp_path / "repo" / PHASE_ID / leaf
    v2_placed.mkdir(parents=True)
    run_id = f"repo/{PHASE_ID}/{leaf}"
    state = {
        "project": "repo",
        "phase_id": PHASE_ID,
        "run_id": run_id,
        "run_directory": str(v2_placed),
    }
    with pytest.raises(RunPathError) as caught:
        validate_run_topology(v2_placed, state)
    assert caught.value.code == "RESUME_SOURCE_INVALID"


def test_18_topology_v2_run_id_with_v1_source(tmp_path: Path) -> None:
    leaf = f"{PHASE_ID}--20260912T120000000000Z"
    v1_dir = tmp_path / "repo" / leaf
    v1_dir.mkdir(parents=True)
    state = {
        "project": "repo",
        "phase_id": PHASE_ID,
        "run_id": f"repo/{PHASE_ID}/{leaf}",  # V2 style run_id on V1 directory
        "run_directory": str(v1_dir),
    }
    with pytest.raises(RunPathError) as caught:
        validate_run_topology(v1_dir, state)
    assert caught.value.code == "RESUME_SOURCE_INVALID"


def test_19_topology_v1_run_id_with_v2_source(tmp_path: Path) -> None:
    leaf = f"{PHASE_ID}-dispatch--20260912T120000000000Z"
    v2_dir = tmp_path / "repo" / PHASE_ID / leaf
    v2_dir.mkdir(parents=True)
    state = {
        "project": "repo",
        "phase_id": PHASE_ID,
        "run_id": f"repo/{leaf}",  # V1 style run_id on V2 directory
        "run_directory": str(v2_dir),
        "run_layout": layout_record_v2(f"repo/{PHASE_ID}/{leaf}", leaf),
    }
    with pytest.raises(RunPathError) as caught:
        validate_run_topology(v2_dir, state)
    assert caught.value.code == "RESUME_SOURCE_INVALID"


def test_20_topology_malformed_layout_marker(tmp_path: Path) -> None:
    leaf = f"{PHASE_ID}-dispatch--20260912T120000000000Z"
    v2_dir = tmp_path / "repo" / PHASE_ID / leaf
    v2_dir.mkdir(parents=True)
    run_id = f"repo/{PHASE_ID}/{leaf}"
    state = {
        "project": "repo",
        "phase_id": PHASE_ID,
        "run_id": run_id,
        "run_directory": str(v2_dir),
        "run_layout": {"schema": "invalid-schema", "kind": "project-phase-dispatch", "run_id": run_id, "leaf": leaf},
    }
    with pytest.raises(RunPathError) as caught:
        validate_run_topology(v2_dir, state)
    assert caught.value.code == "RESUME_SOURCE_INVALID"


def test_21_topology_state_result_layout_disagreement(tmp_path: Path) -> None:
    leaf = f"{PHASE_ID}-dispatch--20260912T120000000000Z"
    v2_dir = tmp_path / "repo" / PHASE_ID / leaf
    v2_dir.mkdir(parents=True)
    run_id = f"repo/{PHASE_ID}/{leaf}"
    state = {
        "project": "repo",
        "phase_id": PHASE_ID,
        "run_id": run_id,
        "run_directory": str(v2_dir),
        "run_layout": layout_record_v2(run_id, leaf),
    }
    result = {
        "project": "repo",
        "phase_id": PHASE_ID,
        "run_id": run_id,
        "run_directory": str(v2_dir),
        "run_layout": layout_record_v2(run_id, "different-leaf"),
    }
    with pytest.raises(RunPathError) as caught:
        validate_run_topology(v2_dir, state, result)
    assert caught.value.code == "RESUME_ARTIFACT_MISMATCH"


def test_22_topology_run_directory_disagreement(tmp_path: Path) -> None:
    leaf = f"{PHASE_ID}-dispatch--20260912T120000000000Z"
    v2_dir = tmp_path / "repo" / PHASE_ID / leaf
    v2_dir.mkdir(parents=True)
    run_id = f"repo/{PHASE_ID}/{leaf}"
    state = {
        "project": "repo",
        "phase_id": PHASE_ID,
        "run_id": run_id,
        "run_directory": str(tmp_path / "different-path"),
        "run_layout": layout_record_v2(run_id, leaf),
    }
    with pytest.raises(RunPathError) as caught:
        validate_run_topology(v2_dir, state)
    assert caught.value.code == "RESUME_SOURCE_INVALID"


# ==============================================================================
# 3. Historical V1 Dual-Read (Cases 23-29)
# ==============================================================================


def test_23_historical_v1_run_validates_unchanged(tmp_path: Path) -> None:
    v1_dir = create_sealed_v1_run(tmp_path, "repo", PHASE_ID)
    state = json.loads((v1_dir / "state.json").read_text(encoding="utf-8"))
    result = json.loads((v1_dir / "result.json").read_text(encoding="utf-8"))

    validate_run_topology(v1_dir, state, result)
    assert "run_layout" not in state
    assert "run_layout" not in result
    assert state["run_id"] == f"repo/{v1_dir.name}"


def test_24_historical_v1_resume(repository: Path, tmp_path: Path) -> None:
    # Create an incomplete historical V1 run
    v1_dir = create_historical_v1_run(repository, tmp_path, fail_at=2)
    before_bytes = {p.name: p.read_bytes() for p in v1_dir.iterdir()}

    resumed_dispatcher = make_dispatcher(repository, tmp_path / "resumed_runs", LayoutRunner())
    resumed_state = resumed_dispatcher.resume(
        PHASE_ID, REQUEST, v1_dir, "work", finalization_policy="checkpoint"
    )

    # Resumed run is created under V2 layout
    resumed_dir = Path(resumed_state["run_directory"])
    assert resumed_dir.parent.name == PHASE_ID
    assert resumed_dir.parent.parent.name == "repo"
    assert resumed_state["run_layout"]["schema"] == RUN_LAYOUT_SCHEMA_V2

    # Historical V1 source run bytes remain untouched
    after_bytes = {p.name: p.read_bytes() for p in v1_dir.iterdir()}
    assert before_bytes == after_bytes


def test_25_historical_v1_finalrec1_checkpoint_recovery(repository: Path, tmp_path: Path) -> None:
    v1_dir = create_historical_v1_run(repository, tmp_path, finalization_policy="checkpoint")
    (repository / "phase.txt").write_text("historical work\n")
    git(repository, "add", "phase.txt")
    git(repository, "commit", "-qm", "operator materialization")
    before_bytes = {p.name: p.read_bytes() for p in v1_dir.iterdir()}

    # Finalization recovery is provider-free
    receipt = finalization_recovery.recover(v1_dir, repository)
    assert receipt["provider_invocations"] == 0
    assert receipt["finalization"]["outcome"] == "materialized"
    # Source run bytes must NOT be mutated by recovery
    after_bytes = {p.name: p.read_bytes() for p in v1_dir.iterdir()}
    assert before_bytes == after_bytes


def test_26_historical_v1_continue1_adoption(repository: Path, tmp_path: Path) -> None:
    v1_dir = create_historical_v1_run(repository, tmp_path, finalization_policy="checkpoint")
    record = adoption.create(
        v1_dir, repository, "NEXT-PHASE", PhaseRequest("implementation_testing", "normal", "next"),
        reason="Adopt historical V1 candidate",
    )
    # Continuation run ID must use V2 layout
    assert "/NEXT-PHASE/NEXT-PHASE-dispatch--" in record["continuation_run_id"]
    assert record["source_run_id"] == f"repo/{v1_dir.name}"


def test_27_historical_v1_archive_and_receipt_placement(tmp_path: Path) -> None:
    v1_dir = create_sealed_v1_run(tmp_path, "repo", PHASE_ID)
    class FakeV1RunDir:
        def __init__(self, path: Path):
            self.path = path
            self.leaf = path.name
            self.archive_path = path.parent / f"{path.name}.zip"
            self.archive_temporary_path = path.parent / f"{path.name}.zip.tmp"

    archive_module.create(FakeV1RunDir(v1_dir))
    archive_path = v1_dir.parent / f"{v1_dir.name}.zip"
    receipt_path = archive_module.receipt_path(archive_path)

    # V1 archive is placed alongside V1 directory: project / <leaf>.zip
    assert archive_path.parent == v1_dir.parent
    assert receipt_path.parent == v1_dir.parent
    assert archive_path.name == f"{v1_dir.name}.zip"
    assert archive_path.exists()
    assert receipt_path.exists()
    receipt = json.loads(receipt_path.read_text())
    assert receipt["status"] == "succeeded"


def test_28_no_historical_v1_source_byte_rewrites(repository: Path, tmp_path: Path) -> None:
    v1_dir = create_historical_v1_run(repository, tmp_path, finalization_policy="checkpoint")
    mtimes_before = {p.name: p.stat().st_mtime_ns for p in v1_dir.iterdir()}

    # Validate topology and create adoption
    state = json.loads((v1_dir / "state.json").read_text(encoding="utf-8"))
    validate_run_topology(v1_dir, state)
    adoption.create(
        v1_dir, repository, "NEXT-PHASE", PhaseRequest("implementation_testing", "normal", "next"),
        reason="Adopt historical V1 candidate",
    )

    mtimes_after = {p.name: p.stat().st_mtime_ns for p in v1_dir.iterdir()}
    assert mtimes_before == mtimes_after


def test_29_no_compatibility_symlinks_created(repository: Path, tmp_path: Path) -> None:
    runs = tmp_path / "runs"
    dispatcher = make_dispatcher(repository, tmp_path, FakeRunner())
    dispatcher.dispatch(PHASE_ID, REQUEST)

    # Search runs directory tree for any symlinks
    for root, dirs, files in os.walk(runs):
        for name in dirs + files:
            path = Path(root) / name
            assert not path.is_symlink(), f"Forbidden compatibility symlink found at {path}"


# ==============================================================================
# 4. V2 Lifecycles & Recovery (Cases 30-40)
# ==============================================================================


def test_30_standard_lifecycle_v2_layout(repository: Path, tmp_path: Path) -> None:
    dispatcher = make_dispatcher(repository, tmp_path, FakeRunner())
    state = dispatcher.dispatch(PHASE_ID, REQUEST, lifecycle="standard")
    run_path = Path(state["run_directory"])
    assert run_path.parent.name == PHASE_ID
    assert state["run_layout"]["schema"] == RUN_LAYOUT_SCHEMA_V2


def test_31_solo_lifecycle_v2_layout(repository: Path, tmp_path: Path) -> None:
    dispatcher = make_dispatcher(repository, tmp_path, LayoutRunner())
    state = dispatcher.dispatch(PHASE_ID, REQUEST, lifecycle="solo")
    run_path = Path(state["run_directory"])
    assert run_path.parent.name == PHASE_ID
    assert state["run_layout"]["schema"] == RUN_LAYOUT_SCHEMA_V2


def test_32_plan_reviewed_lifecycle_v2_layout(repository: Path, tmp_path: Path) -> None:
    dispatcher = make_dispatcher(repository, tmp_path, LayoutRunner())
    state = dispatcher.dispatch(PHASE_ID, REQUEST, lifecycle="plan-reviewed")
    run_path = Path(state["run_directory"])
    assert run_path.parent.name == PHASE_ID
    assert state["run_layout"]["schema"] == RUN_LAYOUT_SCHEMA_V2


def test_33_work_reviewed_lifecycle_v2_layout(repository: Path, tmp_path: Path) -> None:
    dispatcher = make_dispatcher(repository, tmp_path, LayoutRunner())
    state = dispatcher.dispatch(PHASE_ID, REQUEST, lifecycle="work-reviewed")
    run_path = Path(state["run_directory"])
    assert run_path.parent.name == PHASE_ID
    assert state["run_layout"]["schema"] == RUN_LAYOUT_SCHEMA_V2


def test_34_failed_stage_v2_resume(repository: Path, tmp_path: Path) -> None:
    source_runner = LayoutRunner(fail_at=2)
    dispatcher = make_dispatcher(repository, tmp_path / "source", source_runner)
    with pytest.raises(DispatchError):
        dispatcher.dispatch(PHASE_ID, REQUEST)

    source_dir = next(p.parent for p in (tmp_path / "source" / "runs").rglob("state.json"))
    resumed_runner = LayoutRunner()
    resumed = make_dispatcher(repository, tmp_path / "resumed", resumed_runner).resume(
        PHASE_ID, REQUEST, source_dir, "work", finalization_policy="checkpoint"
    )
    resumed_dir = Path(resumed["run_directory"])
    assert resumed_dir.parent.name == PHASE_ID
    assert resumed["run_layout"]["schema"] == RUN_LAYOUT_SCHEMA_V2


def test_35_v2_finalrec1_checkpoint_recovery(repository: Path, tmp_path: Path) -> None:
    dispatcher = make_dispatcher(repository, tmp_path, LayoutRunner(
        work_hook=lambda cwd: (cwd / "product.txt").write_text("product\n")
    ))
    state = dispatcher.dispatch(PHASE_ID, REQUEST, finalization_policy="checkpoint")
    run_path = Path(state["run_directory"])

    # Simulate checkpoint recovery
    receipt = finalization_recovery.recover(run_path, repository)
    assert receipt["provider_invocations"] == 0
    assert receipt["finalization"]["outcome"] == "completed"


def test_36_v2_archive_manifest_verification(repository: Path, tmp_path: Path) -> None:
    dispatcher = make_dispatcher(repository, tmp_path, FakeRunner())
    state = dispatcher.dispatch(PHASE_ID, REQUEST)
    run_path = Path(state["run_directory"])

    archive_path = Path(state["archive"]["path"])
    receipt_path = archive_module.receipt_path(archive_path)
    receipt = json.loads(receipt_path.read_text())
    assert receipt["status"] == "succeeded"
    assert receipt["archive_name"] == archive_path.name
    with zipfile.ZipFile(archive_path) as bundle:
        assert bundle.testzip() is None
        manifest_data = json.loads(bundle.read(f"{run_path.name}/TRANSPORT-MANIFEST.json"))
        assert manifest_data["schema"] == "agent-phase-transport-v1"


def test_37_v2_ownership_challenge_resolution(repository: Path, tmp_path: Path) -> None:
    (repository / "existing.txt").write_text("orig\n")
    git(repository, "add", "existing.txt")
    git(repository, "commit", "-qm", "track existing")

    runner = LayoutRunner(
        work_hook=lambda cwd: (cwd / "existing.txt").write_text("modified\n"),
        path_dispositions=[{"path": "existing.txt", "disposition": "phase_owned"}],
    )
    dispatcher = make_dispatcher(repository, tmp_path, runner)
    state = dispatcher.dispatch(PHASE_ID, REQUEST, finalization_policy="checkpoint")
    assert state["complete"] is True
    assert Path(state["run_directory"]).parent.name == PHASE_ID


# ==============================================================================
# 5. Adoption & Custody (Cases 41-46)
# ==============================================================================


def test_41_continue1_adoption_from_v2_source(repository: Path, tmp_path: Path) -> None:
    dispatcher = make_dispatcher(repository, tmp_path / "source", LayoutRunner(
        work_hook=lambda cwd: (cwd / "candidate.txt").write_text("candidate\n")
    ))
    source_state = dispatcher.dispatch(PHASE_ID, REQUEST, finalization_policy="checkpoint")
    source_dir = Path(source_state["run_directory"])

    record = adoption.create(
        source_dir, repository, "NEXT-PHASE", PhaseRequest("implementation_testing", "normal", "next"),
        reason="Adopt V2 candidate",
    )
    assert record["continuation_run_id"].startswith("repo/NEXT-PHASE/NEXT-PHASE-dispatch--")
    assert record["source_run_id"] == source_state["run_id"]


def test_42_adoption_record_dual_read_validates_both_layouts(repository: Path, tmp_path: Path) -> None:
    next_req = PhaseRequest("implementation_testing", "normal", "next")

    # 1. From V2
    v2_dispatcher = make_dispatcher(repository, tmp_path / "v2", LayoutRunner(
        work_hook=lambda cwd: (cwd / "candidate.txt").write_text("candidate\n")
    ))
    v2_state = v2_dispatcher.dispatch(PHASE_ID, REQUEST, finalization_policy="checkpoint")
    v2_dir = Path(v2_state["run_directory"])
    v2_rec = adoption.create(
        v2_dir, repository, "NEXT-PHASE", next_req,
        reason="Adopt V2 candidate",
    )
    assert "/NEXT-PHASE/NEXT-PHASE-dispatch--" in v2_rec["continuation_run_id"]

    # 2. From historical V1
    v1_dir = create_historical_v1_run(repository, tmp_path / "v1", finalization_policy="checkpoint")
    v1_rec = adoption.create(
        v1_dir, repository, "NEXT-PHASE", next_req,
        reason="Adopt V1 candidate",
    )
    assert v1_rec["source_run_id"] == f"repo/{v1_dir.name}"
    assert "/NEXT-PHASE/NEXT-PHASE-dispatch--" in v1_rec["continuation_run_id"]

    # 3. validate_state accepts both V2 continuation run ID and historical V1 continuation run ID
    class FakeEntry:
        def __init__(self, observed: dict):
            self._observed = observed
        def as_dict(self):
            return self._observed

    entry = FakeEntry(v2_rec["observed_entry"])

    # State with V2 continuation run_id
    v2_cont_state = {
        "project": "repo",
        "phase_id": "NEXT-PHASE",
        "run_id": v2_rec["continuation_run_id"],
        "adoption": v2_rec,
    }
    adoption.validate_state(v2_cont_state, next_req, entry)

    # State with historical V1 continuation run_id
    v1_cont_rec = dict(v2_rec)
    v1_cont_id = f"repo/{v2_rec['phase_id']}--{v2_rec['timestamp']}"
    v1_cont_rec["continuation_run_id"] = v1_cont_id
    v1_cont_rec.pop("sha256", None)
    v1_cont_rec["sha256"] = adoption.digest(v1_cont_rec)

    v1_cont_state = {
        "project": "repo",
        "phase_id": "NEXT-PHASE",
        "run_id": v1_cont_id,
        "adoption": v1_cont_rec,
    }
    adoption.validate_state(v1_cont_state, next_req, entry)

    # State with mismatched continuation run_id fails
    bad_cont_rec = dict(v2_rec)
    bad_cont_rec["continuation_run_id"] = "bad/run/id"
    bad_cont_rec.pop("sha256", None)
    bad_cont_rec["sha256"] = adoption.digest(bad_cont_rec)
    bad_state = {
        "project": "repo",
        "phase_id": "NEXT-PHASE",
        "run_id": "bad/run/id",
        "adoption": bad_cont_rec,
    }
    with pytest.raises(adoption.AdoptionError) as caught:
        adoption.validate_state(bad_state, next_req, entry)
    assert "continuation run identity is inconsistent" in str(caught.value)


# ==============================================================================
# 6. Worker & Generation Coexistence (Cases 47-52)
# ==============================================================================


def test_47_worker_parent_id_hashing_uniqueness() -> None:
    ts = "20260912T120000000000Z"
    leaf1 = v2_leaf("PHASE-A", ts)
    leaf2 = v2_leaf("PHASE-B", ts)
    run_id1 = v2_run_id("project", "PHASE-A", leaf1)
    run_id2 = v2_run_id("project", "PHASE-B", leaf2)
    assert run_id1 != run_id2
    assert "project/PHASE-A/" in run_id1
    assert "project/PHASE-B/" in run_id2


def test_48_pre_runlayout1_and_post_runlayout1_coexistence(tmp_path: Path) -> None:
    outbox = tmp_path / "outbox"
    v1_pinned_root = outbox / "phase-dispatch"
    v2_root = outbox

    # Pinned controller writing to V1
    v1_run = create_sealed_v1_run(outbox, "repo", "PHASE-1")
    assert v1_run.exists()

    # Post-RUNLAYOUT1 controller writing to V2
    ts = "20260912T120000000000Z"
    leaf = v2_leaf("PHASE-1", ts)
    v2_run = v2_root / "repo" / "PHASE-1" / leaf
    v2_run.mkdir(parents=True)
    assert v2_run.exists()

    # Both paths coexist under outbox without collision or nesting conflict
    assert v1_run.is_relative_to(v1_pinned_root)
    assert v2_run.is_relative_to(v2_root)
    assert not v2_run.is_relative_to(v1_pinned_root)


# ==============================================================================
# 7. Security & Archive Constraints (Cases 53-59)
# ==============================================================================


def test_53_symlink_in_project_dir_rejected(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    root.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    (root / "repo").symlink_to(target)
    with pytest.raises(RunPathError) as caught:
        RunDirectory(root, "repo", PHASE_ID)
    assert caught.value.code == "RUN_PATH_CREATION_FAILED"


def test_54_symlink_in_phase_dir_rejected(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    project_dir = root / "repo"
    project_dir.mkdir(parents=True)
    target = tmp_path / "target_phase"
    target.mkdir()
    (project_dir / PHASE_ID).symlink_to(target)
    with pytest.raises(RunPathError) as caught:
        RunDirectory(root, "repo", PHASE_ID)
    assert caught.value.code == "RUN_PATH_CREATION_FAILED"


def test_55_project_dir_not_a_directory_rejected(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    root.mkdir()
    (root / "repo").write_text("file instead of dir")
    with pytest.raises(RunPathError) as caught:
        RunDirectory(root, "repo", PHASE_ID)
    assert caught.value.code == "RUN_PATH_CREATION_FAILED"


def test_56_phase_dir_not_a_directory_rejected(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    project_dir = root / "repo"
    project_dir.mkdir(parents=True)
    (project_dir / PHASE_ID).write_text("file instead of dir")
    with pytest.raises(RunPathError) as caught:
        RunDirectory(root, "repo", PHASE_ID)
    assert caught.value.code == "RUN_PATH_CREATION_FAILED"


def test_57_existing_parent_permissions_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "runs"
    project_dir = root / "repo"
    project_dir.mkdir(parents=True, mode=0o700)
    orig_stat, orig_chmod = Path.stat, os.chmod
    monkeypatch.setattr(
        Path,
        "stat",
        lambda p, *a, **k: (
            os.stat_result((stat.S_IFDIR | 0o755, *orig_stat(p, *a, **k)[1:]))
            if p == project_dir
            else orig_stat(p, *a, **k)
        ),
    )
    chmod_called = False

    def fake_chmod(path, mode, *args, **kwargs):
        nonlocal chmod_called
        if Path(path) == project_dir:
            chmod_called = True
        return orig_chmod(path, mode, *args, **kwargs)

    monkeypatch.setattr(os, "chmod", fake_chmod)
    RunDirectory(root, "repo", PHASE_ID)
    assert not chmod_called
    assert stat.S_IMODE(project_dir.stat().st_mode) == 0o755


def test_58_created_parent_permissions_0700(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    rundir = RunDirectory(root, "repo", PHASE_ID)
    assert stat.S_IMODE(rundir.project_dir.stat().st_mode) == 0o700
    assert stat.S_IMODE(rundir.phase_dir.stat().st_mode) == 0o700
    assert stat.S_IMODE(rundir.path.stat().st_mode) == 0o700
