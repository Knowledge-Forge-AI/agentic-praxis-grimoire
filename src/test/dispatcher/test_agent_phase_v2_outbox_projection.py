"""Tests for Request V2 outbox projection engine and locator truth.

Covers:
- Acceptance Item: Outbox projection topology and navigation symlinks.
- Acceptance Item: Atomic locator writing and SHA-256 verification.
- Acceptance Item: Collision refusal and hostile symlink parent refusal.
- Acceptance Item: Canonical state preservation on failure.
- Acceptance Item: Symlinks rejected as resume/continue-from authority.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import pytest

from agent_phase.cli import dispatch_main
from agent_phase.outbox_projection import (
    project_v2_run,
    resolve_outbox_root,
)
from agent_phase.run import RunPathError


def _setup_canonical(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    state_root = tmp_path / "apgr_home" / "state"
    runs_root = state_root / "runs"
    runs_root.mkdir(parents=True)
    db_path = state_root / "dispatcher.sqlite3"
    db_path.touch()
    run_dir = runs_root / "run-1"
    run_dir.mkdir()
    (run_dir / "meta.json").write_text('{"phase_id": "test-phase"}', encoding="utf-8")
    archive = runs_root / "run-1.zip"
    archive.write_bytes(b"PK\x03\x04fake_zip_payload_bytes_for_testing")
    return db_path, run_dir, archive, tmp_path / "outbox"


def test_default_outbox_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGENT_PHASE_RUN_ROOT", raising=False)
    fake_home = tmp_path / "fake_home"
    resolved = resolve_outbox_root(home=fake_home)
    assert resolved == fake_home / "Documents" / "agent" / "outbox"


def test_project_and_global_outbox_overrides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_target = tmp_path / "env_outbox"
    monkeypatch.setenv("AGENT_PHASE_RUN_ROOT", str(env_target))
    assert resolve_outbox_root() == env_target.resolve()

    explicit_target = tmp_path / "explicit_outbox"
    assert resolve_outbox_root(explicit=explicit_target) == explicit_target.resolve()

    proj_dir = tmp_path / "proj"
    proj_apgr = proj_dir / ".apgr"
    proj_apgr.mkdir(parents=True)
    proj_outbox = tmp_path / "proj_outbox"
    (proj_apgr / "config.toml").write_text(f'outbox_root = "{proj_outbox}"\n', encoding="utf-8")
    assert resolve_outbox_root(project_root=proj_dir) == proj_outbox.resolve()

    # Project TOML overrides AGENT_PHASE_RUN_ROOT
    assert resolve_outbox_root(project_root=proj_dir) == proj_outbox.resolve()

    fake_home = tmp_path / "fake_home"
    global_apgr = fake_home / ".apgr"
    global_apgr.mkdir(parents=True)
    global_outbox = tmp_path / "global_outbox"
    (global_apgr / "config.toml").write_text(f'outbox_root = "{global_outbox}"\n', encoding="utf-8")
    monkeypatch.delenv("AGENT_PHASE_RUN_ROOT", raising=False)
    assert resolve_outbox_root(home=fake_home) == global_outbox.resolve()


def test_cli_outbox_root_option(tmp_path: Path) -> None:
    from agent_phase.cli import dispatch_main
    req_file = tmp_path / "req.json"
    req_file.write_text(json.dumps({"schema": "agent-phase-request-v2", "phase_type": "implementation_testing", "prompt": "test"}), encoding="utf-8")
    outbox_target = tmp_path / "cli_outbox"
    ret = dispatch_main(["--dry-run", "--outbox-root", str(outbox_target), str(req_file)])
    assert ret == 0


def test_phase_dispatch_topology(tmp_path: Path) -> None:
    db_path, run_dir, archive, outbox_root = _setup_canonical(tmp_path)
    h = hashlib.sha256(archive.read_bytes()).hexdigest()
    project_v2_run(
        outbox_root=outbox_root,
        project="demo-proj",
        phase_id="p01",
        run_id="run-1",
        leaf="p01-dispatch--20260917T000000Z",
        canonical_run_dir=run_dir,
        canonical_archive_path=archive,
        archive_sha256=h,
        database_path=db_path,
        request_digest="sha256-req",
        semantic_status="completed",
        finalization_policy="publish",
        finalization_status="finalized",
    )
    phase_dir = outbox_root / "demo-proj" / "p01"
    assert phase_dir.is_dir()
    assert (phase_dir / "p01-dispatch--20260917T000000Z").is_symlink()
    assert (phase_dir / "p01-dispatch--20260917T000000Z.zip").is_symlink()
    assert (phase_dir / "p01-dispatch--20260917T000000Z.locator.json").is_file()


def test_symlink_targets(tmp_path: Path) -> None:
    db_path, run_dir, archive, outbox_root = _setup_canonical(tmp_path)
    leaf = "p01-dispatch--target"
    project_v2_run(
        outbox_root=outbox_root,
        project="projA",
        phase_id="p02",
        run_id="run-1",
        leaf=leaf,
        canonical_run_dir=run_dir,
        canonical_archive_path=archive,
        archive_sha256="abc",
        database_path=db_path,
        request_digest="req1",
        semantic_status="completed",
        finalization_policy="commit",
        finalization_status="finalized",
    )
    phase_dir = outbox_root / "projA" / "p02"
    run_link = phase_dir / leaf
    zip_link = phase_dir / f"{leaf}.zip"
    assert run_link.resolve() == run_dir.resolve()
    assert zip_link.resolve() == archive.resolve()


def test_locator_truth_and_digests(tmp_path: Path) -> None:
    db_path, run_dir, archive, outbox_root = _setup_canonical(tmp_path)
    leaf = "p01-dispatch--loc"
    locator = project_v2_run(
        outbox_root=outbox_root,
        project="projB",
        phase_id="p03",
        run_id="run-1",
        leaf=leaf,
        canonical_run_dir=run_dir,
        canonical_archive_path=archive,
        archive_sha256="abc",
        database_path=db_path,
        request_digest="req1",
        semantic_status="completed",
        finalization_policy="publish",
        finalization_status="finalized",
        commit={"commit": "abc1234"},
        tree="tree5678",
        publication_status="published",
    )
    assert locator["schema"] == "agent-phase-dispatch-locator-v1"
    assert locator["version"] == 1
    assert locator["project"] == "projB"
    assert locator["phase_id"] == "p03"
    assert locator["run_id"] == "run-1"
    assert locator["request_digest"] == "req1"
    assert locator["canonical_run_path"] == str(run_dir.resolve())
    assert locator["database_path"] == str(db_path.resolve())
    assert locator["publication_status"] == "published"
    assert locator["commit"] == {"commit": "abc1234"}
    assert locator["tree"] == "tree5678"

    on_disk = json.loads(
        (outbox_root / "projB" / "p03" / f"{leaf}.locator.json").read_text(
            encoding="utf-8"
        )
    )
    assert on_disk == locator


def test_archive_hash_identity(tmp_path: Path) -> None:
    db_path, run_dir, archive, outbox_root = _setup_canonical(tmp_path)
    leaf = "p01-dispatch--hash"
    archive_bytes = b"Sealed Archive Binary Payload Exactly Here"
    archive.write_bytes(archive_bytes)
    real_sha256 = hashlib.sha256(archive_bytes).hexdigest()

    locator = project_v2_run(
        outbox_root=outbox_root,
        project="projC",
        phase_id="p04",
        run_id="run-1",
        leaf=leaf,
        canonical_run_dir=run_dir,
        canonical_archive_path=archive,
        archive_sha256=real_sha256,
        database_path=db_path,
        request_digest="req-hash",
        semantic_status="completed",
        finalization_policy="publish",
        finalization_status="finalized",
    )
    file_sha256 = hashlib.sha256(Path(locator["archive_path"]).read_bytes()).hexdigest()
    assert locator["archive_sha256"] == real_sha256 == file_sha256


def test_collision_refusal(tmp_path: Path) -> None:
    db_path, run_dir, archive, outbox_root = _setup_canonical(tmp_path)
    leaf = "p01-dispatch--collision"
    project_v2_run(
        outbox_root=outbox_root,
        project="projD",
        phase_id="p05",
        run_id="run-1",
        leaf=leaf,
        canonical_run_dir=run_dir,
        canonical_archive_path=archive,
        archive_sha256="abc",
        database_path=db_path,
        request_digest="req-col",
        semantic_status="completed",
        finalization_policy="publish",
        finalization_status="finalized",
    )
    with pytest.raises(RunPathError, match="projection target already exists"):
        project_v2_run(
            outbox_root=outbox_root,
            project="projD",
            phase_id="p05",
            run_id="run-1",
            leaf=leaf,
            canonical_run_dir=run_dir,
            canonical_archive_path=archive,
            archive_sha256="abc",
            database_path=db_path,
            request_digest="req-col",
            semantic_status="completed",
            finalization_policy="publish",
            finalization_status="finalized",
        )


def test_hostile_symlink_parent_refusal(tmp_path: Path) -> None:
    db_path, run_dir, archive, outbox_root = _setup_canonical(tmp_path)
    evil_target = tmp_path / "somewhere_else"
    evil_target.mkdir()
    phase_parent = outbox_root / "evil_proj"
    phase_parent.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(evil_target, phase_parent)

    with pytest.raises(RunPathError, match="hostile symlink detected"):
        project_v2_run(
            outbox_root=outbox_root,
            project="evil_proj",
            phase_id="p06",
            run_id="run-1",
            leaf="leaf1",
            canonical_run_dir=run_dir,
            canonical_archive_path=archive,
            archive_sha256="abc",
            database_path=db_path,
            request_digest="req-evil",
            semantic_status="completed",
            finalization_policy="publish",
            finalization_status="finalized",
        )


def test_missing_canonical_target_refusal(tmp_path: Path) -> None:
    db_path, run_dir, archive, outbox_root = _setup_canonical(tmp_path)
    missing_run = tmp_path / "apgr_home" / "state" / "runs" / "does_not_exist"
    with pytest.raises(RunPathError, match="canonical run directory does not exist"):
        project_v2_run(
            outbox_root=outbox_root,
            project="projF",
            phase_id="p07",
            run_id="run-1",
            leaf="leaf2",
            canonical_run_dir=missing_run,
            canonical_archive_path=archive,
            archive_sha256="abc",
            database_path=db_path,
            request_digest="req-miss",
            semantic_status="completed",
            finalization_policy="publish",
            finalization_status="finalized",
        )
    symlink_run = tmp_path / "apgr_home" / "state" / "runs" / "symlink_run"
    os.symlink(run_dir, symlink_run)
    with pytest.raises(RunPathError, match="canonical run directory must not be a symlink"):
        project_v2_run(
            outbox_root=outbox_root,
            project="projF",
            phase_id="p07",
            run_id="run-1",
            leaf="leaf3",
            canonical_run_dir=symlink_run,
            canonical_archive_path=archive,
            archive_sha256="abc",
            database_path=db_path,
            request_digest="req-miss",
            semantic_status="completed",
            finalization_policy="publish",
            finalization_status="finalized",
        )


def test_canonical_state_preserved_on_projection_failure(tmp_path: Path) -> None:
    db_path, run_dir, archive, outbox_root = _setup_canonical(tmp_path)
    can_meta = (run_dir / "meta.json").read_text(encoding="utf-8")
    can_zip = archive.read_bytes()

    phase_dir = outbox_root / "projG" / "p08"
    phase_dir.mkdir(parents=True)
    (phase_dir / "fail-leaf.locator.json").write_text("pre-existing", encoding="utf-8")

    with pytest.raises(RunPathError):
        project_v2_run(
            outbox_root=outbox_root,
            project="projG",
            phase_id="p08",
            run_id="run-1",
            leaf="fail-leaf",
            canonical_run_dir=run_dir,
            canonical_archive_path=archive,
            archive_sha256="abc",
            database_path=db_path,
            request_digest="req-fail",
            semantic_status="completed",
            finalization_policy="publish",
            finalization_status="finalized",
        )

    assert (run_dir / "meta.json").read_text(encoding="utf-8") == can_meta
    assert archive.read_bytes() == can_zip


def test_outbox_symlink_rejected_as_resume_authority(tmp_path: Path) -> None:
    req_file = tmp_path / "req.json"
    req_file.write_text(
        '{"schema": "agent-phase-request-v2", "phase_type": "implementation_testing", "prompt": "test"}',
        encoding="utf-8",
    )
    dummy_dir = tmp_path / "real_dir"
    dummy_dir.mkdir()
    symlink_dir = tmp_path / "symlink_dir"
    os.symlink(dummy_dir, symlink_dir)

    with pytest.raises(SystemExit) as exc_info:
        dispatch_main([str(req_file), "--resume", str(symlink_dir)])
    assert exc_info.value.code == 2

    with pytest.raises(SystemExit) as exc_info2:
        dispatch_main([str(req_file), "--continue-from", str(symlink_dir)])
    assert exc_info2.value.code == 2
