"""Archive-boundary contracts through the real dispatcher finalization path."""

from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import zipfile

import pytest

from agent_phase import archive as archive_module
from agent_phase import archive_snapshot as snapshot_module
from agent_phase.dispatch import DispatchError
from agent_phase.display import Display
from agent_phase.request import PhaseRequest
from agent_phase.run import stage_parent_id

from test_agent_phase_dispatch import FakeRunner, PHASE_ID, make_dispatcher, repository


__all__ = ["repository"]
REQUEST = PhaseRequest("implementation_testing", "normal", "archive boundary")


def only_run(tmp_path: Path) -> Path:
    states = list((tmp_path / "runs").rglob("state.json"))
    assert len(states) == 1
    return states[0].parent


def state_of(tmp_path: Path) -> dict[str, object]:
    return json.loads((only_run(tmp_path) / "state.json").read_text())


def archive_members(path: Path) -> tuple[str, dict[str, bytes]]:
    with zipfile.ZipFile(path) as bundle:
        assert bundle.testzip() is None
        return bundle.namelist(), {
            name: bundle.read(name)
            for name in bundle.namelist()
            if not name.endswith("/")
        }


def assert_archive_receipt(tmp_path: Path) -> dict[str, object]:
    state = state_of(tmp_path)
    archive = Path(state["archive_path"])
    assert archive.is_file()
    receipt = json.loads(archive_module.receipt_path(archive).read_text())
    assert receipt["status"] == "succeeded"
    assert receipt["purpose"] == "dispatcher-finalization"
    names, _ = archive_members(archive)
    leaf = only_run(tmp_path).name
    assert {f"{leaf}/{name}" for name in (
        "request.json", "resolved.json", "state.json", "result.json",
        "TRANSPORT-MANIFEST.json",
    )} <= set(names)
    return state


class InterruptedRunner(FakeRunner):
    """Raise a real stage interruption while retaining the invocation record."""

    def __call__(self, argv, prompt, cwd, max_output, on_output=None):
        if len(self.calls) == 2:
            self.calls.append({
                "argv": list(argv), "prompt": prompt, "cwd": cwd,
                "max_output": max_output, "pid": 2,
            })
            if self.on_stage is not None:
                self.on_stage(2)
            raise KeyboardInterrupt("fixture interruption")
        return super().__call__(argv, prompt, cwd, max_output, on_output)


def add_worker_trees(run: Path) -> list[Path]:
    """Create namespaced ledgers plus realistic Serena trees for two stages."""
    run_id = json.loads((run / "state.json").read_text())["run_id"]
    roots: list[Path] = []
    for stage, index, language_server in (
        ("plan", 0, "TypeScriptLanguageServer/ts-lsp"),
        ("final_review", 3, "BashLanguageServer/bash-lsp"),
    ):
        parent = run / "workers" / stage_parent_id(run_id, stage, index)
        parent.mkdir(parents=True)
        (parent / "ledger.json").write_text(
            json.dumps({"parent_id": str(parent.name), "status": "closed"}) + "\n"
        )
        job = parent / "jobs" / "worker-job"
        job.mkdir(parents=True)
        (job / "worker-job.result.json").write_text(
            json.dumps({"schema": "agent-worker-result-v1", "status": "accepted"}) + "\n"
        )
        runtime = parent / "serena-home"
        bin_dir = runtime / "language_servers" / "static" / language_server / "node_modules" / ".bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / ("tsc" if "TypeScript" in language_server else "bash-language-server")).symlink_to(
            "/outside/runtime/executable"
        )
        (runtime / "generated-language-server.bin").write_bytes(b"generated runtime\n")
        os.mkfifo(runtime / "server.sock")
        roots.append(runtime)
    (run / "01-plan.worker-drain.json").write_text(
        json.dumps({"status": "closed", "cleanup_proven": True}) + "\n"
    )
    (run / "04-final-review.worker-drain.json").write_text(
        json.dumps({"status": "closed", "cleanup_proven": True}) + "\n"
    )
    return roots


def test_dispatch_archive_prunes_runtime_before_scandir_and_hashes_manifest(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime_roots: list[Path] = []

    def on_stage(index: int) -> None:
        if index == 0:
            run = only_run(tmp_path)
            runtime_roots.extend(add_worker_trees(run))
            (run / ".DS_Store").write_bytes(b"metadata")
            (run / "__MACOSX").mkdir()
            (run / "__MACOSX" / "noise").write_bytes(b"metadata")

    real_open_directory = snapshot_module.open_directory
    fd_paths: dict[int, Path] = {}
    real_scandir = snapshot_module.os.scandir

    def tracked_open_directory(path, *, dir_fd=None):
        descriptor = real_open_directory(path, dir_fd=dir_fd)
        parent = fd_paths.get(dir_fd, Path())
        fd_paths[descriptor] = (parent / path).resolve() if dir_fd is not None else Path(path).resolve()
        return descriptor

    def guarded_scandir(path):
        if isinstance(path, int):
            observed = fd_paths.get(path)
            if observed is not None and any(
                observed == root or root in observed.parents for root in runtime_roots
            ):
                raise AssertionError(f"runtime descendant enumerated: {observed}")
        return real_scandir(path)

    monkeypatch.setattr(snapshot_module, "open_directory", tracked_open_directory)
    monkeypatch.setattr(snapshot_module.os, "scandir", guarded_scandir)
    state = make_dispatcher(repository, tmp_path, FakeRunner(on_stage=on_stage)).dispatch(
        PHASE_ID, REQUEST
    )

    archive = Path(state["archive_path"])
    names, payloads = archive_members(archive)
    leaf = only_run(tmp_path).name
    assert all("serena-home" not in name for name in names)
    assert not any("__MACOSX" in name or name.endswith(".DS_Store") for name in names)
    for required in (
        "request.json", "resolved.json", "state.json", "result.json",
        "01-plan.worker-drain.json", "04-final-review.worker-drain.json",
    ):
        assert f"{leaf}/{required}" in names
    assert any(name.endswith("/ledger.json") for name in names)
    assert any(name.endswith("/worker-job.result.json") for name in names)

    manifest = json.loads(payloads[f"{leaf}/TRANSPORT-MANIFEST.json"])
    assert manifest["schema"] == "agent-phase-transport-v1"
    assert manifest["purpose"] == "dispatcher-finalization"
    assert manifest["review_only"] is True
    assert manifest["resume_authority"] == "full original local run"
    included = {entry["path"]: entry for entry in manifest["included"]}
    for name, data in payloads.items():
        relative = name.removeprefix(f"{leaf}/")
        if relative == "TRANSPORT-MANIFEST.json":
            continue
        record = included[relative]
        assert record["bytes"] == len(data)
        assert record["sha256"] == hashlib.sha256(data).hexdigest()
    assert manifest["selected_count"] == len(included)
    assert manifest["selected_bytes"] == sum(item["bytes"] for item in included.values())
    excluded = {entry["path"]: entry for entry in manifest["excluded"]}
    runtime_excluded = [
        path for path in excluded if path.endswith("/serena-home")
    ]
    assert len(runtime_excluded) == 2
    assert all("not observed" in entry["reason"] for entry in excluded.values())


@pytest.mark.parametrize("node", ["symlink", "fifo"])
def test_required_nonregular_artifact_fails_without_following_and_keeps_task_truth(
    repository: Path, tmp_path: Path, node: str
) -> None:
    outside = tmp_path / "outside-secret"
    outside.write_bytes(b"must never be read")

    def on_stage(index: int) -> None:
        if index != 0:
            return
        run = only_run(tmp_path)
        if node == "symlink":
            (run / "required-external-link").symlink_to(outside)
        else:
            os.mkfifo(run / "required-fifo")

    with pytest.raises(DispatchError) as caught:
        make_dispatcher(repository, tmp_path, FakeRunner(on_stage=on_stage)).dispatch(
            PHASE_ID, REQUEST
        )

    state = state_of(tmp_path)
    assert caught.value.code == "RUN_ARCHIVE_FAILED"
    assert state["complete"] is True
    assert state["outcome"] == "completed"
    failure = state["archive"]["failure"]
    assert failure["code"] == "RUN_ARCHIVE_FAILED"
    expected_name = "required-external-link" if node == "symlink" else "required-fifo"
    assert expected_name in failure["detail"]
    assert not Path(state["archive_path"]).exists()
    assert outside.read_bytes() == b"must never be read"


def test_archive_limit_is_truthful_and_preserves_completed_closeout(
    repository: Path, tmp_path: Path
) -> None:
    def on_stage(index: int) -> None:
        if index == 0:
            oversized = only_run(tmp_path) / "oversized-evidence.bin"
            with oversized.open("wb") as handle:
                handle.truncate(snapshot_module.MAX_FILE_BYTES + 1)

    with pytest.raises(DispatchError) as caught:
        make_dispatcher(repository, tmp_path, FakeRunner(on_stage=on_stage)).dispatch(
            PHASE_ID, REQUEST
        )

    state = state_of(tmp_path)
    assert caught.value.code == "RUN_ARCHIVE_LIMIT"
    assert state["complete"] is True
    assert state["outcome"] == "completed"
    assert state["archive"]["failure"]["code"] == "RUN_ARCHIVE_LIMIT"
    assert "oversized-evidence.bin" in state["archive"]["failure"]["detail"]
    assert "retain full local run" in state["archive"]["failure"]["detail"]
    assert not Path(state["archive_path"]).exists()


def test_archive_entry_limit_is_truthful_and_preserves_completed_closeout(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(snapshot_module, "MAX_ENTRIES", 1)
    with pytest.raises(DispatchError) as caught:
        make_dispatcher(repository, tmp_path, FakeRunner()).dispatch(PHASE_ID, REQUEST)

    state = state_of(tmp_path)
    assert caught.value.code == "RUN_ARCHIVE_LIMIT"
    assert state["complete"] is True
    assert state["outcome"] == "completed"
    assert state["archive"]["failure"]["code"] == "RUN_ARCHIVE_LIMIT"
    assert "entry limit" in state["archive"]["failure"]["detail"]
    assert not Path(state["archive_path"]).exists()


def test_required_permission_error_is_explicit_and_preserves_completed_closeout(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def on_stage(index: int) -> None:
        if index == 0:
            (only_run(tmp_path) / "permission-denied-evidence.json").write_text("{}\n")

    real_read = snapshot_module.Snapshot._read

    def denied_read(snapshot, descriptor, child, info):
        if child.as_posix() == "permission-denied-evidence.json":
            raise PermissionError("fixture permission denied")
        return real_read(snapshot, descriptor, child, info)

    monkeypatch.setattr(snapshot_module.Snapshot, "_read", denied_read)
    with pytest.raises(DispatchError) as caught:
        make_dispatcher(repository, tmp_path, FakeRunner(on_stage=on_stage)).dispatch(
            PHASE_ID, REQUEST
        )

    state = state_of(tmp_path)
    assert caught.value.code == "RUN_ARCHIVE_FAILED"
    assert state["complete"] is True
    assert state["outcome"] == "completed"
    assert state["archive"]["failure"]["code"] == "RUN_ARCHIVE_FAILED"
    assert "permission-denied-evidence.json" in state["archive"]["failure"]["detail"]
    assert not Path(state["archive_path"]).exists()


def test_growing_selected_input_fails_after_snapshot_without_publishing_partial_zip(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_box: dict[str, Path] = {}

    def on_stage(index: int) -> None:
        if index == 0:
            run = only_run(tmp_path)
            run_box["run"] = run
            (run / "growing-evidence.json").write_text("before\n")

    real_read = snapshot_module.Snapshot._read

    def read_then_grow(snapshot, descriptor, child, info):
        data = real_read(snapshot, descriptor, child, info)
        if child.as_posix() == "growing-evidence.json":
            (run_box["run"] / "growing-evidence.json").write_bytes(data + b"growth\n")
        return data

    monkeypatch.setattr(snapshot_module.Snapshot, "_read", read_then_grow)
    with pytest.raises(DispatchError) as caught:
        make_dispatcher(repository, tmp_path, FakeRunner(on_stage=on_stage)).dispatch(
            PHASE_ID, REQUEST
        )

    state = state_of(tmp_path)
    assert caught.value.code == "RUN_ARCHIVE_CHANGED"
    assert state["complete"] is True
    assert state["outcome"] == "completed"
    assert "growing-evidence.json" in state["archive"]["failure"]["detail"]
    assert not Path(state["archive_path"]).exists()


def test_provider_failure_keeps_blocker_and_publishes_transport_receipt(
    repository: Path, tmp_path: Path
) -> None:
    with pytest.raises(DispatchError) as caught:
        make_dispatcher(
            repository, tmp_path, FakeRunner(exit_codes={2: 7})
        ).dispatch(PHASE_ID, REQUEST)

    assert caught.value.code == "PROVIDER_TRANSPORT_FAILED"
    state = assert_archive_receipt(tmp_path)
    assert state["complete"] is False
    assert state["outcome"] == "blocked"
    assert state["blocking_reason"]["code"] == "PROVIDER_TRANSPORT_FAILED"
    assert state["archive"]["failure"] is None


def test_failed_terminal_outcome_keeps_outcome_and_publishes_transport_receipt(
    repository: Path, tmp_path: Path
) -> None:
    with pytest.raises(DispatchError) as caught:
        make_dispatcher(
            repository, tmp_path, FakeRunner(closeout_outcome="failed")
        ).dispatch(PHASE_ID, REQUEST)

    assert caught.value.code == "PROVIDER_OUTCOME_FAILED"
    state = assert_archive_receipt(tmp_path)
    assert state["complete"] is False
    assert state["outcome"] == "blocked"
    assert state["blocking_reason"]["code"] == "PROVIDER_OUTCOME_FAILED"
    assert state["archive"]["failure"] is None


def test_interrupted_provider_keeps_interruption_and_publishes_transport_receipt(
    repository: Path, tmp_path: Path
) -> None:
    with pytest.raises(KeyboardInterrupt):
        make_dispatcher(repository, tmp_path, InterruptedRunner()).dispatch(
            PHASE_ID, REQUEST
        )

    state = assert_archive_receipt(tmp_path)
    assert state["complete"] is False
    assert state["outcome"] == "blocked"
    assert state["blocking_reason"]["code"] == "KeyboardInterrupt"
    assert state["archive"]["failure"] is None


@pytest.mark.parametrize("case", ["missing", "binding"])
def test_required_core_validation_is_explicit_and_preserves_completed_truth(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    on_stage = None
    if case == "missing":
        monkeypatch.setattr(
            snapshot_module, "CORE", (*snapshot_module.CORE, "missing-core.json")
        )
    else:
        def on_stage(index: int) -> None:
            if index == 0:
                run = only_run(tmp_path)
                (run / "bound-evidence.txt").write_text("bound\n")
                (run / "binding.json").write_text(json.dumps({
                    "evidence_binding": {
                        "relative_path": "bound-evidence.txt",
                        "sha256": "0" * 64,
                    }
                }) + "\n")

        monkeypatch.setattr(
            snapshot_module, "CORE", (*snapshot_module.CORE, "binding.json")
        )

    runner = FakeRunner(on_stage=on_stage)
    with pytest.raises(DispatchError) as caught:
        make_dispatcher(repository, tmp_path, runner).dispatch(PHASE_ID, REQUEST)

    state = state_of(tmp_path)
    expected_code = (
        "RUN_ARCHIVE_MISSING_REQUIRED" if case == "missing" else "RUN_ARCHIVE_INTEGRITY"
    )
    assert caught.value.code == expected_code
    assert state["complete"] is True
    assert state["outcome"] == "completed"
    assert state["archive"]["failure"]["code"] == expected_code
    assert not Path(state["archive_path"]).exists()
    if case == "missing":
        assert "missing-core.json" in state["archive"]["failure"]["detail"]
    else:
        assert "binding digest mismatch" in state["archive"]["failure"]["detail"]


def test_archive_failure_keeps_commit_push_and_prior_blocker_separate(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(_directory, **_kwargs):
        raise archive_module.ArchiveError("RUN_ARCHIVE_FAILED", "workers/x/serena-home")

    def mutate(index: int) -> None:
        if index == 2:
            (repository / "phase.txt").write_text("phase\n")

    monkeypatch.setattr(archive_module, "create", fail)
    with pytest.raises(DispatchError) as caught:
        make_dispatcher(repository, tmp_path, FakeRunner(on_stage=mutate)).dispatch(
            PHASE_ID, REQUEST
        )
    state = state_of(tmp_path)
    assert caught.value.code == "RUN_ARCHIVE_FAILED"
    assert state["complete"] is True
    assert state["outcome"] == "completed"
    assert state["commit"] is not None
    assert state["push"]["succeeded"] is True
    assert state["archive"]["failure"]["code"] == "RUN_ARCHIVE_FAILED"
    assert state["finalization_failures"][0]["code"] == "RUN_ARCHIVE_FAILED"

    (repository / "operator.txt").write_text("operator\n")

    def overlap(index: int) -> None:
        if index == 2:
            (repository / "operator.txt").write_text("phase overlap\n")

    overlap_root = tmp_path / "overlap"
    with pytest.raises(DispatchError):
        make_dispatcher(repository, overlap_root, FakeRunner(on_stage=overlap)).dispatch(
            PHASE_ID, REQUEST
        )
    overlap_state = state_of(overlap_root)
    assert overlap_state["manager_disposition_required"] is True
    blocking = overlap_state.get("blocking_reason")
    assert blocking is None or blocking["code"] != "RUN_ARCHIVE_FAILED"
    assert overlap_state["finalization_failures"][0]["code"] == "RUN_ARCHIVE_FAILED"


def test_display_keeps_archive_failure_code_and_detail_with_task_blocker() -> None:
    stream = io.StringIO()
    display = Display(stream)
    display.finished(
        {
            "outcome": "blocked", "complete": False, "expected_stages": [],
            "stages_invoked": [], "stage_transports_completed": [],
            "stages_completed": [],
            "blocking_reason": {"code": "PROVIDER_OUTCOME_FAILED", "detail": "task blocker"},
            "archive_path": "/tmp/run.zip",
            "archive": {"status": "failed", "failure": {
                "code": "RUN_ARCHIVE_FAILED", "detail": "required-fifo"
            }},
        }
    )
    display.close()
    assert display._writer is not None
    display._writer.join(timeout=1)
    text = stream.getvalue()
    assert "blocked: PROVIDER_OUTCOME_FAILED" in text
    assert "archive (failed): /tmp/run.zip" in text
    assert "archive failure: RUN_ARCHIVE_FAILED" in text
    assert "required-fifo" in text
