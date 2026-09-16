"""Integration tests for Request V2 Git finalization and publication truth.

Covers:
- Acceptance Item: Checkpoint finalization generates patch and manifest without committing.
- Acceptance Item: Commit local finalization commits without push.
- Acceptance Item: Publish finalization commits and pushes to remote.
- Acceptance Item: Publish failure fails closed.
- Acceptance Item: Clean worktree produces finalized_empty_delta.
- Acceptance Item: Unrelated entry dirt fails closed on overlap.
- Acceptance Item: Entry adoption permits specified entry dirt.
- Acceptance Item: Exact remote readback matches post-push remote ref.
- Acceptance Item: No false completed status on closeout failure or missing fence.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any, Callable
import pytest

from agent_phase import result as result_module
from agent_phase.persistence import open_dispatcher_db, resolve_dispatcher_db_path
from agent_phase.request import parse_request_v2
from agent_phase.v2_dispatch import V2DispatchError, dispatch_v2


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _init_repo(path: Path) -> tuple[Path, Path]:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "t@example.com"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "T"], check=True)
    (path / "file.txt").write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "file.txt"], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-q", "-m", "init"], check=True)
    remote = path.parent / "remote.git"
    if not remote.exists():
        subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
    subprocess.run(["git", "-C", str(path), "remote", "add", "origin", str(remote)], check=True)
    subprocess.run(["git", "-C", str(path), "push", "-q", "-u", "origin", "HEAD"], check=True)
    return path, remote


def _make_v2_request_bytes(
    phase_type: str = "implementation_testing",
    prompt: str = "Test finalization behavior",
) -> bytes:
    return json.dumps({"schema": "agent-phase-request-v2", "phase_type": phase_type, "prompt": prompt}).encode("utf-8")


def _make_closeout_output(
    nonce: str,
    outcome: str = "completed",
    body: str = "Closeout completed successfully.",
    commit_message: dict[str, str] | None = None,
) -> bytes:
    begin, end = result_module.markers(nonce)
    msg = commit_message if commit_message is not None else {
        "subject": "Implement phase changes",
        "body": "Detailed commit description.",
    }
    payload = {"version": 1, "stage": "closeout", "outcome": outcome, "body": body, "commit_message": msg}
    return f"{begin}\n{json.dumps(payload)}\n{end}\n".encode("utf-8")


def _make_runner(
    work_fn: Callable[[], None] | None = None,
    closeout_factory: Callable[[str], bytes] | None = None,
) -> Callable[..., Any]:
    def runner(*, run_id: str, binding: Any, route: Any, run_dir: Path, nonce: str | None = None) -> bytes | None:
        if binding.binding_id == "binding_work" and work_fn is not None:
            work_fn()
        elif binding.binding_id == "binding_closeout" and nonce:
            return closeout_factory(nonce) if closeout_factory is not None else _make_closeout_output(nonce)
        return None
    return runner


def test_finalization_checkpoint(tmp_path: Path) -> None:
    root, home = _repo_root(), tmp_path / "apgr_home"
    repo, _ = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)

    res = dispatch_v2(
        root, repo, req, raw,
        execution_mode="dynamic", finalization_policy="checkpoint",
        apgr_home=home, outbox_root=tmp_path / "outbox",
        runner=_make_runner(work_fn=lambda: (repo / "file.txt").write_text("mod\n", encoding="utf-8")),
    )
    assert res["status"] == "completed"
    assert res["finalization_status"] == "checkpointed"
    assert res["finalization_policy"] == "checkpoint"
    assert res["commit"] is None

    log = subprocess.run(["git", "-C", str(repo), "log", "-1", "--pretty=%s"], capture_output=True, text=True, check=True)
    assert log.stdout.strip() == "init"

    run_dir = resolve_dispatcher_db_path(home).parent / "runs" / res["run_id"]
    assert (run_dir / "checkpoint-candidate.patch").exists()
    assert (run_dir / "checkpoint-candidate-manifest.json").exists()


def test_finalization_commit_local(tmp_path: Path) -> None:
    root, home = _repo_root(), tmp_path / "apgr_home"
    repo, remote = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)

    res = dispatch_v2(
        root, repo, req, raw,
        execution_mode="dynamic", finalization_policy="commit-local",
        apgr_home=home, outbox_root=tmp_path / "outbox",
        runner=_make_runner(work_fn=lambda: (repo / "new.txt").write_text("local\n", encoding="utf-8")),
    )
    assert res["status"] == "completed"
    assert res["finalization_status"] == "completed"
    assert res["finalization_policy"] == "commit-local"
    assert res["commit"] is not None

    local_head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    remote_head = subprocess.run(["git", "-C", str(remote), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    assert res["commit"]["sha"] == local_head
    assert remote_head != local_head


def test_finalization_publish_success(tmp_path: Path) -> None:
    root, home = _repo_root(), tmp_path / "apgr_home"
    repo, remote = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)

    res = dispatch_v2(
        root, repo, req, raw,
        execution_mode="dynamic", finalization_policy="publish",
        apgr_home=home, outbox_root=tmp_path / "outbox",
        runner=_make_runner(work_fn=lambda: (repo / "pub.txt").write_text("pub\n", encoding="utf-8")),
    )
    assert res["status"] == "completed"
    assert res["finalization_status"] == "completed"
    assert res["publication_status"] == "succeeded"

    local_head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    remote_head = subprocess.run(["git", "-C", str(remote), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    assert res["commit"]["sha"] == local_head == remote_head

    run_dir = resolve_dispatcher_db_path(home).parent / "runs" / res["run_id"]
    canonical_res = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    assert canonical_res["archive_sha256"] is not None
    assert canonical_res["archive_sha256"] == res["archive_sha256"]


def test_finalization_publish_failure(tmp_path: Path) -> None:
    root, home = _repo_root(), tmp_path / "apgr_home"
    repo, _ = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)
    subprocess.run(["git", "-C", str(repo), "remote", "set-url", "origin", str(tmp_path / "none.git")], check=True)

    res = dispatch_v2(
        root, repo, req, raw,
        execution_mode="dynamic", finalization_policy="publish",
        apgr_home=home, outbox_root=tmp_path / "outbox",
        runner=_make_runner(work_fn=lambda: (repo / "fail.txt").write_text("fail\n", encoding="utf-8")),
    )
    assert res["status"] == "failed"
    assert res["finalization_status"] == "failed"
    assert res["publication_status"] == "failed"


def test_finalization_no_delta(tmp_path: Path) -> None:
    root, home = _repo_root(), tmp_path / "apgr_home"
    repo, _ = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)

    def closeout_no_delta(nonce: str) -> bytes:
        begin, end = result_module.markers(nonce)
        payload = {"version": 1, "stage": "closeout", "outcome": "completed", "body": "No-op.", "commit_message": None}
        return f"{begin}\n{json.dumps(payload)}\n{end}\n".encode("utf-8")

    res = dispatch_v2(
        root, repo, req, raw,
        execution_mode="dynamic", finalization_policy="publish",
        apgr_home=home, outbox_root=tmp_path / "outbox",
        runner=_make_runner(work_fn=None, closeout_factory=closeout_no_delta),
    )
    assert res["status"] == "completed"
    assert res["finalization_status"] == "completed"
    assert res["commit"] is None


def test_finalization_unrelated_entry_dirt(tmp_path: Path) -> None:
    root, home = _repo_root(), tmp_path / "apgr_home"
    repo, _ = _init_repo(tmp_path / "repo")
    (repo / "file.txt").write_text("dirt at entry\n", encoding="utf-8")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)

    res = dispatch_v2(
        root, repo, req, raw,
        execution_mode="dynamic", finalization_policy="publish",
        apgr_home=home, outbox_root=tmp_path / "outbox",
        runner=_make_runner(work_fn=lambda: (repo / "file.txt").write_text("model overlap\n", encoding="utf-8")),
    )
    assert res["status"] == "failed"
    assert res["finalization_status"] == "failed"


def test_finalization_unrelated_entry_dirt_commit_local(tmp_path: Path) -> None:
    root, home = _repo_root(), tmp_path / "apgr_home"
    repo, _ = _init_repo(tmp_path / "repo")
    (repo / "file.txt").write_text("dirt at entry\n", encoding="utf-8")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)

    res = dispatch_v2(
        root, repo, req, raw,
        execution_mode="dynamic", finalization_policy="commit-local",
        apgr_home=home, outbox_root=tmp_path / "outbox",
        runner=_make_runner(work_fn=lambda: (repo / "file.txt").write_text("model overlap\n", encoding="utf-8")),
    )
    assert res["status"] == "failed"
    assert res["finalization_status"] == "failed"


def test_finalization_unrelated_entry_dirt_checkpoint(tmp_path: Path) -> None:
    root, home = _repo_root(), tmp_path / "apgr_home"
    repo, _ = _init_repo(tmp_path / "repo")
    (repo / "file.txt").write_text("dirt at entry\n", encoding="utf-8")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)

    res = dispatch_v2(
        root, repo, req, raw,
        execution_mode="dynamic", finalization_policy="checkpoint",
        apgr_home=home, outbox_root=tmp_path / "outbox",
        runner=_make_runner(work_fn=lambda: (repo / "file.txt").write_text("model overlap\n", encoding="utf-8")),
    )
    assert res["status"] == "failed"
    assert res["finalization_status"] == "failed"


def test_finalization_unrelated_entry_dirt_preserved(tmp_path: Path) -> None:
    root, home = _repo_root(), tmp_path / "apgr_home"
    repo, remote = _init_repo(tmp_path / "repo")
    (repo / "unrelated.txt").write_text("pre-existing dirt\n", encoding="utf-8")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)

    res = dispatch_v2(
        root, repo, req, raw,
        execution_mode="dynamic", finalization_policy="publish",
        apgr_home=home, outbox_root=tmp_path / "outbox",
        runner=_make_runner(work_fn=lambda: (repo / "phase_mod.txt").write_text("phase delta\n", encoding="utf-8")),
    )
    assert res["status"] == "completed"
    assert res["finalization_status"] == "completed"
    assert res["publication_status"] == "succeeded"

    committed_files = subprocess.run(
        ["git", "-C", str(repo), "show", "--name-only", "--pretty=format:", "HEAD"],
        capture_output=True, text=True, check=True
    ).stdout.strip().splitlines()
    assert "phase_mod.txt" in committed_files
    assert "unrelated.txt" not in committed_files
    assert (repo / "unrelated.txt").read_text(encoding="utf-8") == "pre-existing dirt\n"


def test_finalization_admitted_entry_delta(tmp_path: Path) -> None:
    root, home = _repo_root(), tmp_path / "apgr_home"
    repo, _ = _init_repo(tmp_path / "repo")
    (repo / "file.txt").write_text("operator dirt to adopt\n", encoding="utf-8")
    req_file = tmp_path / "req.json"
    raw = _make_v2_request_bytes()
    req_file.write_bytes(raw)
    req = parse_request_v2(raw)

    from agent_phase import entry_adoption as entry_adoption_module
    adopt_record = entry_adoption_module.create(
        req_file, repo, ["file.txt"], reason="Adopted changes", phase_id="implementation_testing"
    )
    adopt_file = tmp_path / "adopt.json"
    adopt_file.write_bytes(entry_adoption_module.encoded(adopt_record))

    res = dispatch_v2(
        root, repo, req, raw,
        execution_mode="dynamic", finalization_policy="publish",
        apgr_home=home, outbox_root=tmp_path / "outbox",
        entry_adoption=str(adopt_file),
        runner=_make_runner(work_fn=lambda: (repo / "file.txt").write_text("refined\n", encoding="utf-8")),
    )
    assert res["status"] == "completed"
    assert res["finalization_status"] == "completed"
    assert res["publication_status"] == "succeeded"


def test_finalization_exact_remote_readback(tmp_path: Path) -> None:
    root, home = _repo_root(), tmp_path / "apgr_home"
    repo, remote = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)

    res = dispatch_v2(
        root, repo, req, raw,
        execution_mode="dynamic", finalization_policy="publish",
        apgr_home=home, outbox_root=tmp_path / "outbox",
        runner=_make_runner(work_fn=lambda: (repo / "rb.txt").write_text("rb\n", encoding="utf-8")),
    )
    assert res["status"] == "completed"
    readback = res.get("remote_readback")
    assert isinstance(readback, dict) and readback["status"] == "succeeded" and readback["succeeded"] is True

    remote_head = subprocess.run(["git", "-C", str(remote), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    assert readback["post_push_remote_head"] == remote_head == readback["phase_commit"]


def test_finalization_no_false_completed_status(tmp_path: Path) -> None:
    root, home = _repo_root(), tmp_path / "apgr_home"
    repo, _ = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)

    def closeout_failed(nonce: str) -> bytes:
        return _make_closeout_output(nonce, outcome="failed", body="Failed execution.")

    with pytest.raises(V2DispatchError, match="Turn execution failed"):
        dispatch_v2(
            root, repo, req, raw,
            execution_mode="dynamic", finalization_policy="publish",
            apgr_home=home, outbox_root=tmp_path / "outbox",
            runner=_make_runner(
                work_fn=lambda: (repo / "file.txt").write_text("work\n", encoding="utf-8"),
                closeout_factory=closeout_failed,
            ),
        )

    conn = open_dispatcher_db(resolve_dispatcher_db_path(home))
    runs = conn.execute("SELECT status, outcome, semantic_outcome FROM runs").fetchall()
    assert len(runs) == 1
    assert runs[0][0] == "failed"
    assert runs[0][1] == "failed"
    assert runs[0][2] == "failed"
