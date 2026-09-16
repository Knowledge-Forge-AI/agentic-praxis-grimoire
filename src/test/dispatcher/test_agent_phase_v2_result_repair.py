"""Deterministic regression tests for Request V2 terminal formatting repair.

Verifies:
1. APG151 recovery: missing closing fence triggers single-shot repository-detached repair.
2. Zero semantic work replay (earlier turns are not re-executed).
3. Fresh repair nonce generated and enforced.
4. Auxiliary attempt accounting in SQLite persistence and result artifacts.
5. Worktree mutation during repair fails closed (RESULT_REPAIR_CANDIDATE_MUTATED).
6. Scratch CWD side effects fail closed (RESULT_REPAIR_SIDE_EFFECT).
7. Non-zero terminal transport does not trigger repair.
8. Semantically blocked/failed outcome does not trigger repair.
9. Perfectly valid closeout makes zero repair attempts.
10. Repair failure fails closed cleanly.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any
import pytest

from agent_phase import result as result_module
from agent_phase.persistence import (
    PersistenceError,
    get_invocation_attempts,
    open_dispatcher_db,
    resolve_dispatcher_db_path,
)
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


def _make_v2_request_bytes(prompt: str = "Test V2 result repair") -> bytes:
    return json.dumps({
        "schema": "agent-phase-request-v2",
        "phase_type": "implementation_testing",
        "prompt": prompt,
    }).encode("utf-8")


def _make_closeout_payload(outcome: str = "completed", body: str = "Closeout ok.") -> dict[str, Any]:
    return {
        "version": 1,
        "stage": "closeout",
        "outcome": outcome,
        "body": body,
        "commit_message": {
            "subject": "Implement terminal changes",
            "body": "Detailed commit description.",
        },
    }


def test_v2_result_repair_apg151_recovery_success(tmp_path: Path) -> None:
    """APG151 failure shape: missing closing fence triggers single-shot detached repair and succeeds."""
    root, home = _repo_root(), tmp_path / "apgr_home"
    repo, remote = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)

    work_invocation_count = 0
    repair_invocation_count = 0
    observed_repair_nonce: str | None = None

    def runner(*, run_id: str, binding: Any, route: Any, run_dir: Path, nonce: str | None = None, **kwargs: Any) -> bytes | None:
        nonlocal work_invocation_count, repair_invocation_count, observed_repair_nonce
        if binding.binding_id == "binding_work":
            work_invocation_count += 1
            (repo / "file.txt").write_text("repaired_work\n", encoding="utf-8")
            return b"Work completed."
        if binding.binding_id == "binding_closeout":
            if kwargs.get("is_repair") or kwargs.get("invocation_kind") == "auxiliary_result_repair":
                repair_invocation_count += 1
                observed_repair_nonce = nonce
                # Return strictly valid result with the new repair nonce
                begin, end = result_module.markers(nonce)
                return f"{begin}\n{json.dumps(_make_closeout_payload())}\n{end}\n".encode("utf-8")
            # Primary closeout: simulate APG151 defect (valid json with start fence, missing end fence)
            begin, _ = result_module.markers(nonce)
            return f"{begin}\n{json.dumps(_make_closeout_payload())}\n".encode("utf-8")
        return None

    res = dispatch_v2(
        root, repo, req, raw,
        execution_mode="dynamic", finalization_policy="publish",
        apgr_home=home, outbox_root=tmp_path / "outbox",
        runner=runner,
    )

    # 1. Successful overall and finalization status
    assert res["status"] == "completed"
    assert res["semantic_status"] == "completed"
    assert res["finalization_status"] == "completed"
    assert res["publication_status"] == "succeeded"

    # 2. Zero semantic work replay
    assert work_invocation_count == 1
    assert repair_invocation_count == 1

    # 3. Auxiliary invocation accounting in result payload
    assert res["auxiliary_provider_invocations"] == 1
    assert res["auxiliary_provider_invocations_performed"] == 1
    assert res["total_effective_provider_turns"] == 6

    # 4. Result repair machine evidence
    repair_ev = res.get("result_repair")
    assert isinstance(repair_ev, dict)
    assert repair_ev["operation"] == "result-repair"
    assert repair_ev["one_shot"] is True
    assert repair_ev["semantic_work_replayed"] is False
    assert repair_ev["source_result_blocker"] == "RESULT_MISSING_FENCE"
    assert repair_ev["repair_transport_status"] == "succeeded"
    assert repair_ev["strict_parse_outcome"] == "completed"
    assert repair_ev["candidate_tree_identical"] is True
    assert repair_ev["no_side_effect_truth"] is True

    # 5. Fresh repair nonce was supplied and used
    assert observed_repair_nonce is not None

    # 6. Database persistence check: auxiliary attempt recorded
    conn = open_dispatcher_db(resolve_dispatcher_db_path(home))
    attempts = conn.execute(
        "SELECT attempt_id, binding_id, status, exit_code FROM invocation_attempts WHERE binding_id = 'binding_closeout'"
    ).fetchall()
    assert len(attempts) == 2
    attempt_ids = [a[0] for a in attempts]
    assert any(a.endswith("-repair-1") for a in attempt_ids)
    repair_att = [a for a in attempts if a[0].endswith("-repair-1")][0]
    assert repair_att[2] == "completed"
    assert repair_att[3] == 0

    # 7. Run directory artifacts exist
    run_dir = Path(res["run_directory"])
    assert (run_dir / "result-repair.json").exists()
    assert (run_dir / "result-repair-cwd.json").exists()
    assert (run_dir / "closeout.result.json").exists()

    # 8. Markdown summary mentions Result Repair Evidence
    res_md = (run_dir / "result.md").read_text(encoding="utf-8")
    assert "## Result Repair Evidence" in res_md
    assert "RESULT_MISSING_FENCE" in res_md


def test_v2_result_repair_fails_closed_when_repair_invalid(tmp_path: Path) -> None:
    """When the repair attempt also produces an unparseable response, fail closed cleanly."""
    root, home = _repo_root(), tmp_path / "apgr_home"
    repo, _ = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)

    def runner(*, run_id: str, binding: Any, route: Any, run_dir: Path, nonce: str | None = None, **kwargs: Any) -> bytes | None:
        if binding.binding_id == "binding_closeout":
            # Both primary and repair output broken results
            return b"Malformed completely without fences."
        return None

    with pytest.raises(V2DispatchError, match="Turn execution failed"):
        dispatch_v2(
            root, repo, req, raw,
            execution_mode="dynamic", finalization_policy="publish",
            apgr_home=home, outbox_root=tmp_path / "outbox",
            runner=runner,
        )

    conn = open_dispatcher_db(resolve_dispatcher_db_path(home))
    runs = conn.execute("SELECT status, outcome FROM runs").fetchall()
    assert runs[0][0] == "failed"
    assert runs[0][1] == "failed"


def test_v2_result_repair_nonzero_terminal_transport_ineligible(tmp_path: Path) -> None:
    """Non-zero terminal transport code is not eligible for formatting repair."""
    root, home = _repo_root(), tmp_path / "apgr_home"
    repo, _ = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)

    repair_called = False

    def runner(*, run_id: str, binding: Any, route: Any, run_dir: Path, nonce: str | None = None, **kwargs: Any) -> Any:
        nonlocal repair_called
        if kwargs.get("is_repair"):
            repair_called = True
            return b""
        if binding.binding_id == "binding_closeout":
            # Return exit code 1
            return 1, b"", b"Crash in closeout"
        return None

    with pytest.raises(V2DispatchError, match="Turn execution failed"):
        dispatch_v2(
            root, repo, req, raw,
            execution_mode="dynamic", finalization_policy="publish",
            apgr_home=home, outbox_root=tmp_path / "outbox",
            runner=runner,
        )

    assert repair_called is False


def test_v2_result_repair_candidate_mutation_detected(tmp_path: Path) -> None:
    """Candidate tree mutation during auxiliary repair fails closed with RESULT_REPAIR_CANDIDATE_MUTATED."""
    root, home = _repo_root(), tmp_path / "apgr_home"
    repo, _ = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)

    def runner(*, run_id: str, binding: Any, route: Any, run_dir: Path, nonce: str | None = None, **kwargs: Any) -> bytes | None:
        if binding.binding_id == "binding_closeout":
            if kwargs.get("is_repair"):
                # Maliciously mutate the worktree during repair
                (repo / "rogue.txt").write_text("illegal\n", encoding="utf-8")
                begin, end = result_module.markers(nonce)
                return f"{begin}\n{json.dumps(_make_closeout_payload())}\n{end}\n".encode("utf-8")
            # Primary: missing fence
            begin, _ = result_module.markers(nonce)
            return f"{begin}\n{json.dumps(_make_closeout_payload())}\n".encode("utf-8")
        return None

    with pytest.raises(V2DispatchError, match="RESULT_REPAIR_CANDIDATE_MUTATED"):
        dispatch_v2(
            root, repo, req, raw,
            execution_mode="dynamic", finalization_policy="publish",
            apgr_home=home, outbox_root=tmp_path / "outbox",
            runner=runner,
        )


def test_v2_result_repair_scratch_side_effect_detected(tmp_path: Path) -> None:
    """Auxiliary provider writing files in scratch working directory fails closed with RESULT_REPAIR_SIDE_EFFECT."""
    root, home = _repo_root(), tmp_path / "apgr_home"
    repo, _ = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)

    def runner(*, run_id: str, binding: Any, route: Any, run_dir: Path, nonce: str | None = None, **kwargs: Any) -> bytes | None:
        if binding.binding_id == "binding_closeout":
            if kwargs.get("is_repair"):
                cwd = kwargs.get("cwd")
                if cwd:
                    (Path(cwd) / "unwanted_scratch.txt").write_text("polluted", encoding="utf-8")
                begin, end = result_module.markers(nonce)
                return f"{begin}\n{json.dumps(_make_closeout_payload())}\n{end}\n".encode("utf-8")
            # Primary: missing fence
            begin, _ = result_module.markers(nonce)
            return f"{begin}\n{json.dumps(_make_closeout_payload())}\n".encode("utf-8")
        return None

    with pytest.raises(V2DispatchError, match="RESULT_REPAIR_SIDE_EFFECT"):
        dispatch_v2(
            root, repo, req, raw,
            execution_mode="dynamic", finalization_policy="publish",
            apgr_home=home, outbox_root=tmp_path / "outbox",
            runner=runner,
        )


def test_v2_result_repair_zero_attempts_on_valid_result(tmp_path: Path) -> None:
    """Valid terminal result triggers exactly 0 repair attempts."""
    root, home = _repo_root(), tmp_path / "apgr_home"
    repo, _ = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)

    repair_called = False

    def runner(*, run_id: str, binding: Any, route: Any, run_dir: Path, nonce: str | None = None, **kwargs: Any) -> bytes | None:
        nonlocal repair_called
        if kwargs.get("is_repair"):
            repair_called = True
            return b""
        if binding.binding_id == "binding_closeout":
            begin, end = result_module.markers(nonce)
            return f"{begin}\n{json.dumps(_make_closeout_payload())}\n{end}\n".encode("utf-8")
        return None

    res = dispatch_v2(
        root, repo, req, raw,
        execution_mode="dynamic", finalization_policy="publish",
        apgr_home=home, outbox_root=tmp_path / "outbox",
        runner=runner,
    )

    assert res["status"] == "completed"
    assert repair_called is False
    assert res["auxiliary_provider_invocations"] == 0
    assert res["auxiliary_provider_invocations_performed"] == 0
    assert res["total_effective_provider_turns"] == 5
    assert res["result_repair"] is None


def test_v2_result_repair_semantically_blocked_ineligible(tmp_path: Path) -> None:
    """Clean JSON with outcome='blocked' is not a formatting defect and does not trigger repair."""
    root, home = _repo_root(), tmp_path / "apgr_home"
    repo, _ = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)

    repair_called = False

    def runner(*, run_id: str, binding: Any, route: Any, run_dir: Path, nonce: str | None = None, **kwargs: Any) -> bytes | None:
        nonlocal repair_called
        if kwargs.get("is_repair"):
            repair_called = True
            return b""
        if binding.binding_id == "binding_closeout":
            begin, end = result_module.markers(nonce)
            # Semantically blocked outcome
            return f"{begin}\n{json.dumps(_make_closeout_payload(outcome='blocked', body='Cannot complete.'))}\n{end}\n".encode("utf-8")
        return None

    with pytest.raises(V2DispatchError, match="Turn execution failed"):
        dispatch_v2(
            root, repo, req, raw,
            execution_mode="dynamic", finalization_policy="publish",
            apgr_home=home, outbox_root=tmp_path / "outbox",
            runner=runner,
        )

    assert repair_called is False


def test_v2_result_repair_runner_returns_none_fails_closed(tmp_path: Path) -> None:
    """Repair runner returning None fails closed with RESULT_REPAIR_TRANSPORT_INVALID, never fabricating completion."""
    root, home = _repo_root(), tmp_path / "apgr_home"
    repo, _ = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)

    def runner(*, run_id: str, binding: Any, route: Any, run_dir: Path, nonce: str | None = None, **kwargs: Any) -> bytes | None:
        if binding.binding_id == "binding_closeout":
            if kwargs.get("is_repair"):
                # Defective repair runner returns None instead of valid bytes
                return None
            # Primary closeout: missing fence triggers repair
            begin, _ = result_module.markers(nonce)
            return f"{begin}\n{json.dumps(_make_closeout_payload())}\n".encode("utf-8")
        return None

    with pytest.raises(V2DispatchError, match="RESULT_REPAIR_TRANSPORT_INVALID"):
        dispatch_v2(
            root, repo, req, raw,
            execution_mode="dynamic", finalization_policy="publish",
            apgr_home=home, outbox_root=tmp_path / "outbox",
            runner=runner,
        )

    # Persistence truthfully records the auxiliary attempt as failed
    conn = open_dispatcher_db(resolve_dispatcher_db_path(home))
    attempts = conn.execute(
        "SELECT attempt_id, binding_id, status, exit_code FROM invocation_attempts WHERE binding_id = 'binding_closeout'"
    ).fetchall()
    assert len(attempts) == 2
    repair_att = [a for a in attempts if a[0].endswith("-repair-1")][0]
    assert repair_att[2] == "failed"
    assert repair_att[3] == 1


def test_v2_result_repair_runner_unsupported_result_fails_closed(tmp_path: Path) -> None:
    """Repair runner returning an unsupported object fails closed with RESULT_REPAIR_TRANSPORT_INVALID."""
    root, home = _repo_root(), tmp_path / "apgr_home"
    repo, _ = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)

    def runner(*, run_id: str, binding: Any, route: Any, run_dir: Path, nonce: str | None = None, **kwargs: Any) -> Any:
        if binding.binding_id == "binding_closeout":
            if kwargs.get("is_repair"):
                # Returns an unsupported dictionary instead of Result/bytes/str/tuple
                return {"unsupported": "result_type"}
            begin, _ = result_module.markers(nonce)
            return f"{begin}\n{json.dumps(_make_closeout_payload())}\n".encode("utf-8")
        return None

    with pytest.raises(V2DispatchError, match="RESULT_REPAIR_TRANSPORT_INVALID"):
        dispatch_v2(
            root, repo, req, raw,
            execution_mode="dynamic", finalization_policy="publish",
            apgr_home=home, outbox_root=tmp_path / "outbox",
            runner=runner,
        )


def test_v2_result_repair_attempt_persistence_failure_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Failure to persist auxiliary repair attempt fails closed with PersistenceError."""
    root, home = _repo_root(), tmp_path / "apgr_home"
    repo, _ = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)

    import agent_phase.v2_repair as v2_repair_mod
    original_record = v2_repair_mod.record_invocation_attempt

    def failing_record(*args: Any, **kwargs: Any) -> None:
        if kwargs.get("attempt_kind") == "auxiliary" or kwargs.get("attempt_id", "").endswith("-repair-1"):
            raise PersistenceError("simulated auxiliary attempt persistence failure")
        original_record(*args, **kwargs)

    monkeypatch.setattr(v2_repair_mod, "record_invocation_attempt", failing_record)

    def runner(*, run_id: str, binding: Any, route: Any, run_dir: Path, nonce: str | None = None, **kwargs: Any) -> bytes | None:
        if binding.binding_id == "binding_closeout":
            if kwargs.get("is_repair"):
                begin, end = result_module.markers(nonce)
                return f"{begin}\n{json.dumps(_make_closeout_payload())}\n{end}\n".encode("utf-8")
            begin, _ = result_module.markers(nonce)
            return f"{begin}\n{json.dumps(_make_closeout_payload())}\n".encode("utf-8")
        return None

    with pytest.raises(V2DispatchError, match="simulated auxiliary attempt persistence failure"):
        dispatch_v2(
            root, repo, req, raw,
            execution_mode="dynamic", finalization_policy="publish",
            apgr_home=home, outbox_root=tmp_path / "outbox",
            runner=runner,
        )


def test_v2_result_repair_artifact_persistence_failure_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Failure to register required repair artifacts fails closed with PersistenceError."""
    root, home = _repo_root(), tmp_path / "apgr_home"
    repo, _ = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)

    import agent_phase.v2_repair as v2_repair_mod
    original_record_art = v2_repair_mod.record_artifact

    def failing_record_artifact(*args: Any, **kwargs: Any) -> None:
        if "repair" in kwargs.get("artifact_name", ""):
            raise PersistenceError("simulated repair artifact registration failure")
        original_record_art(*args, **kwargs)

    monkeypatch.setattr(v2_repair_mod, "record_artifact", failing_record_artifact)

    def runner(*, run_id: str, binding: Any, route: Any, run_dir: Path, nonce: str | None = None, **kwargs: Any) -> bytes | None:
        if binding.binding_id == "binding_closeout":
            if kwargs.get("is_repair"):
                begin, end = result_module.markers(nonce)
                return f"{begin}\n{json.dumps(_make_closeout_payload())}\n{end}\n".encode("utf-8")
            begin, _ = result_module.markers(nonce)
            return f"{begin}\n{json.dumps(_make_closeout_payload())}\n".encode("utf-8")
        return None

    with pytest.raises(V2DispatchError, match="simulated repair artifact registration failure"):
        dispatch_v2(
            root, repo, req, raw,
            execution_mode="dynamic", finalization_policy="publish",
            apgr_home=home, outbox_root=tmp_path / "outbox",
            runner=runner,
        )


def test_v2_result_repair_artifact_exact_byte_identity(tmp_path: Path) -> None:
    """Registered size and sha256 of all repair artifacts must exactly equal the written file bytes."""
    root, home = _repo_root(), tmp_path / "apgr_home"
    repo, _ = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)

    def runner(*, run_id: str, binding: Any, route: Any, run_dir: Path, nonce: str | None = None, **kwargs: Any) -> bytes | None:
        if binding.binding_id == "binding_closeout":
            if kwargs.get("is_repair"):
                begin, end = result_module.markers(nonce)
                return f"{begin}\n{json.dumps(_make_closeout_payload())}\n{end}\n".encode("utf-8")
            begin, _ = result_module.markers(nonce)
            return f"{begin}\n{json.dumps(_make_closeout_payload())}\n".encode("utf-8")
        return None

    res = dispatch_v2(
        root, repo, req, raw,
        execution_mode="dynamic", finalization_policy="publish",
        apgr_home=home, outbox_root=tmp_path / "outbox",
        runner=runner,
    )
    assert res["status"] == "completed"

    run_dir = Path(res["run_directory"])
    conn = open_dispatcher_db(resolve_dispatcher_db_path(home))

    for artifact_name in ("result-repair-cwd.json", "result-repair.json", "closeout.result.json"):
        file_path = run_dir / artifact_name
        assert file_path.exists()
        file_bytes = file_path.read_bytes()

        # Must have trailing newline
        assert file_bytes.endswith(b"\n")

        row = conn.execute(
            "SELECT size_bytes, sha256 FROM artifacts WHERE run_id = ? AND artifact_name = ?",
            (res["run_id"], artifact_name),
        ).fetchone()
        assert row is not None, f"Artifact {artifact_name} not found in database"
        registered_size, registered_sha = row[0], row[1]

        # Exact byte identity proof
        assert registered_size == len(file_bytes), f"Size mismatch for {artifact_name}"
        assert registered_sha == hashlib.sha256(file_bytes).hexdigest(), f"SHA mismatch for {artifact_name}"


def test_v2_result_repair_index_mutation_detected(tmp_path: Path) -> None:
    """Real git index mutation during auxiliary repair fails closed with RESULT_REPAIR_INDEX_MUTATED."""
    root, home = _repo_root(), tmp_path / "apgr_home"
    repo, _ = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)

    def runner(*, run_id: str, binding: Any, route: Any, run_dir: Path, nonce: str | None = None, **kwargs: Any) -> bytes | None:
        if binding.binding_id == "binding_closeout":
            if kwargs.get("is_repair"):
                # Mutate the real git index without altering the worktree candidate tree
                blob = subprocess.check_output(
                    ["git", "-C", str(repo), "hash-object", "-w", "--stdin"],
                    input=b"index only content\n",
                ).decode("utf-8").strip()
                subprocess.run(
                    ["git", "-C", str(repo), "update-index", "--add", "--cacheinfo", "100644", blob, "phantom.txt"],
                    check=True,
                )
                begin, end = result_module.markers(nonce)
                return f"{begin}\n{json.dumps(_make_closeout_payload())}\n{end}\n".encode("utf-8")
            begin, _ = result_module.markers(nonce)
            return f"{begin}\n{json.dumps(_make_closeout_payload())}\n".encode("utf-8")
        return None

    with pytest.raises(V2DispatchError, match="RESULT_REPAIR_INDEX_MUTATED"):
        dispatch_v2(
            root, repo, req, raw,
            execution_mode="dynamic", finalization_policy="publish",
            apgr_home=home, outbox_root=tmp_path / "outbox",
            runner=runner,
        )


def test_v2_result_repair_same_provider_profile_and_fresh_nonce(tmp_path: Path) -> None:
    """Repair invocation preserves provider and profile while generating a fresh nonce."""
    root, home = _repo_root(), tmp_path / "apgr_home"
    repo, _ = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)

    primary_route_info: tuple[str, str] | None = None
    repair_route_info: tuple[str, str] | None = None
    primary_nonce: str | None = None
    repair_nonce: str | None = None

    def runner(*, run_id: str, binding: Any, route: Any, run_dir: Path, nonce: str | None = None, **kwargs: Any) -> bytes | None:
        nonlocal primary_route_info, repair_route_info, primary_nonce, repair_nonce
        if binding.binding_id == "binding_closeout":
            if kwargs.get("is_repair"):
                repair_route_info = (route.provider, route.profile)
                repair_nonce = nonce
                begin, end = result_module.markers(nonce)
                return f"{begin}\n{json.dumps(_make_closeout_payload())}\n{end}\n".encode("utf-8")
            primary_route_info = (route.provider, route.profile)
            primary_nonce = nonce
            begin, _ = result_module.markers(nonce)
            return f"{begin}\n{json.dumps(_make_closeout_payload())}\n".encode("utf-8")
        return None

    res = dispatch_v2(
        root, repo, req, raw,
        execution_mode="dynamic", finalization_policy="publish",
        apgr_home=home, outbox_root=tmp_path / "outbox",
        runner=runner,
    )
    assert res["status"] == "completed"

    # Same provider and profile preserved
    assert primary_route_info is not None
    assert repair_route_info is not None
    assert primary_route_info == repair_route_info

    # Fresh distinct 32-hex nonce used
    assert primary_nonce is not None
    assert repair_nonce is not None
    assert primary_nonce != repair_nonce
    assert len(repair_nonce) == 32


def test_v2_result_repair_auxiliary_attempt_does_not_poison_semantic_lineage(tmp_path: Path) -> None:
    """Auxiliary repair attempt cannot be mistaken for an ordinary semantic attempt or corrupt predecessor lineage."""
    root, home = _repo_root(), tmp_path / "apgr_home"
    repo, _ = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)

    def runner(*, run_id: str, binding: Any, route: Any, run_dir: Path, nonce: str | None = None, **kwargs: Any) -> bytes | None:
        if binding.binding_id == "binding_closeout":
            if kwargs.get("is_repair"):
                begin, end = result_module.markers(nonce)
                return f"{begin}\n{json.dumps(_make_closeout_payload())}\n{end}\n".encode("utf-8")
            begin, _ = result_module.markers(nonce)
            return f"{begin}\n{json.dumps(_make_closeout_payload())}\n".encode("utf-8")
        return None

    res = dispatch_v2(
        root, repo, req, raw,
        execution_mode="dynamic", finalization_policy="publish",
        apgr_home=home, outbox_root=tmp_path / "outbox",
        runner=runner,
    )
    assert res["status"] == "completed"
    run_id = res["run_id"]

    conn = open_dispatcher_db(resolve_dispatcher_db_path(home))
    all_closeout_attempts = get_invocation_attempts(conn, run_id, binding_id="binding_closeout")
    assert len(all_closeout_attempts) == 2

    # Verify auxiliary attempt distinction
    semantic_attempts = [
        a for a in all_closeout_attempts
        if a.get("attempt_kind", "semantic") != "auxiliary"
        and not (a["attempt_id"].endswith("-repair-1") or "-repair-" in a["attempt_id"])
    ]
    auxiliary_attempts = [
        a for a in all_closeout_attempts
        if a.get("attempt_kind") == "auxiliary" or "-repair-" in a["attempt_id"]
    ]

    assert len(semantic_attempts) == 1
    assert len(auxiliary_attempts) == 1

    sem_att = semantic_attempts[0]
    aux_att = auxiliary_attempts[0]

    assert sem_att["attempt_id"] == f"att-{run_id}-binding_closeout-1"
    assert aux_att["attempt_id"] == f"att-{run_id}-binding_closeout-repair-1"
    assert aux_att["predecessor_attempt_id"] == sem_att["attempt_id"]
    assert aux_att.get("attempt_kind") == "auxiliary"

    # Prove that deriving the next semantic attempt for binding_closeout yields attempt 2 with predecessor att-*-1
    curr_attempt_number = len(semantic_attempts) + 1
    assert curr_attempt_number == 2
    predecessor_id = semantic_attempts[-1]["attempt_id"]
    assert predecessor_id == f"att-{run_id}-binding_closeout-1"

