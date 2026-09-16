"""Archive-only recovery preserves historical bytes and invokes no work stages."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest

from agent_phase import archive, archive_recovery
from agent_phase.archive_snapshot import ArchiveError


def terminal(tmp_path: Path) -> Path:
    source = tmp_path / "terminal-run"
    source.mkdir()
    state = {"outcome": "blocked", "complete": False,
             "blocking_reason": {"code": "PRODUCT_AUDIT", "detail": "audit outstanding"},
             "archive": {"status": "failed", "failure": {"code": "RUN_ARCHIVE_FAILED"}},
             "commit": {"sha": "already-published"}, "push": {"succeeded": True}}
    for name in ("request.json", "resolved.json", "state.json", "result.json"):
        (source / name).write_text(json.dumps(state) + "\n")
    return source


def test_recovery_preserves_bytes_and_has_no_provider_git_imports(tmp_path: Path) -> None:
    source = terminal(tmp_path)
    before = {p.name: p.read_bytes() for p in source.iterdir()}
    target = tmp_path / "review.zip"
    script = """
import sys
from pathlib import Path
def audit(event, args):
    if event in ('subprocess.Popen', 'os.system', 'os.exec', 'os.posix_spawn'):
        raise AssertionError('archive recovery attempted a subprocess')
sys.addaudithook(audit)
from agent_phase.archive_recovery import main
assert not any(n in sys.modules for n in ('agent_phase.dispatch', 'agent_phase.provider', 'agent_phase.gitstate'))
raise SystemExit(main(sys.argv[1:]))
"""
    result = subprocess.run([sys.executable, "-c", script, str(source), str(target)],
                            env={**os.environ, "PYTHONPATH": str(Path(__file__).parents[3] / "libexec")},
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["purpose"] == "archive-only-recovery"
    assert receipt["review_only"] is True
    assert receipt["archive_sha256"] == hashlib.sha256(target.read_bytes()).hexdigest()
    with zipfile.ZipFile(target) as zipped:
        for name, raw in before.items():
            assert zipped.read(f"{source.name}/{name}") == raw
        manifest = json.loads(zipped.read(f"{source.name}/TRANSPORT-MANIFEST.json"))
        assert manifest["resume_authority"] == "full original local run"
    assert {p.name: p.read_bytes() for p in source.iterdir()} == before
    with pytest.raises(ArchiveError, match="RUN_ARCHIVE_COLLISION"):
        archive_recovery.recover(source, target)


@pytest.mark.parametrize("mutation", ["active", "pending", "ledger", "drain", "job"])
def test_recovery_refuses_unsettled_source(tmp_path: Path, mutation: str) -> None:
    source = terminal(tmp_path)
    state = json.loads((source / "state.json").read_bytes())
    if mutation == "active":
        state["outcome"] = None
    elif mutation == "pending":
        state["worker_cleanup_pending"] = {"stage": "work"}
    else:
        name = "01-work.worker-drain.json" if mutation == "drain" else "workers/parent/ledger.json"
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {"status": "open"}
        if mutation == "job":
            record = {"status": "closed", "gemini_jobs": {"job": {"status": "running"}}}
        path.write_text(json.dumps(record))
    (source / "state.json").write_text(json.dumps(state))
    with pytest.raises(ArchiveError, match="RUN_ARCHIVE_NOT_SETTLED"):
        archive_recovery.recover(source, tmp_path / "review.zip")
    assert not (tmp_path / "review.zip").exists()


def test_recovery_refuses_inside_source_and_dangling_collision(tmp_path: Path) -> None:
    source = terminal(tmp_path)
    with pytest.raises(ArchiveError, match="RUN_ARCHIVE_DESTINATION"):
        archive_recovery.recover(source, source / "new.zip")
    target = tmp_path / "new.zip"
    target.symlink_to("missing")
    with pytest.raises(ArchiveError, match="RUN_ARCHIVE_COLLISION"):
        archive_recovery.recover(source, target)
    assert target.is_symlink()


def test_receipt_failure_does_not_rewrite_publication_facts(tmp_path: Path, monkeypatch) -> None:
    source = terminal(tmp_path)
    from types import SimpleNamespace
    directory = SimpleNamespace(path=source, leaf=source.name,
                                archive_path=tmp_path / f"{source.name}.zip",
                                archive_temporary_path=tmp_path / f"{source.name}.zip.tmp")
    state = {"complete": True, "outcome": "completed", "commit": {"sha": "committed"},
             "push": {"succeeded": True}, "blocking_reason": None}
    def fail(*args):
        raise ArchiveError("RUN_ARCHIVE_RECEIPT_FAILED", "ZIP published; receipt failed")
    real_receipt = archive._receipt
    monkeypatch.setattr(archive, "_receipt", fail)
    def write():
        for name in ("state.json", "result.json"):
            (source / name).write_text(json.dumps(state))
    error = archive.finalize(directory, state, write, lambda: None)
    assert error.code == "RUN_ARCHIVE_RECEIPT_FAILED"
    assert state["complete"] is True and state["outcome"] == "completed"
    assert state["push"]["succeeded"] is True
    assert state["blocking_reason"] is None
    assert directory.archive_path.exists()
    assert state["archive"]["failure_receipt_status"] == "written"
    with zipfile.ZipFile(directory.archive_path) as bundle:
        for name in ("state.json", "result.json"):
            assert bundle.read(f"{source.name}/{name}") == (source / name).read_bytes()
    assert json.loads((source / "state.json").read_bytes())["archive"]["status"] == "in_progress"
    failure = json.loads(archive.failure_receipt_path(directory.archive_path).read_bytes())
    assert failure["zip_published"] is True
    monkeypatch.setattr(archive, "_receipt", real_receipt)
    archive_recovery.recover(source, tmp_path / "receipt-failure.review.zip")


def test_long_destination_keeps_receipt_and_temporary_names_bounded(tmp_path: Path) -> None:
    source = terminal(tmp_path)
    target = tmp_path / ("r" * 240 + ".zip")
    archive_recovery.recover(source, target)
    assert target.is_file()
    receipt = archive.receipt_path(target)
    assert len(os.fsencode(receipt.name)) <= 255
    assert json.loads(receipt.read_bytes())["archive_name"] == target.name


def test_recovery_accepts_verified_canonical_snapshot_receipt(tmp_path: Path) -> None:
    from types import SimpleNamespace
    source = terminal(tmp_path)
    state = json.loads((source / "state.json").read_bytes())
    directory = SimpleNamespace(path=source, leaf=source.name,
        archive_path=source.with_suffix(".zip"),
        archive_temporary_path=source.with_suffix(".zip.tmp"))
    def write():
        for name in ("state.json", "result.json"):
            (source / name).write_text(json.dumps(state))
    assert archive.finalize(directory, state, write, lambda: None) is None
    before = (source / "result.json").read_bytes()
    assert json.loads(before)["archive"]["status"] == "in_progress"
    target = tmp_path / "recovered.zip"
    archive_recovery.recover(source, target)
    assert (source / "result.json").read_bytes() == before
    assert target.is_file()
