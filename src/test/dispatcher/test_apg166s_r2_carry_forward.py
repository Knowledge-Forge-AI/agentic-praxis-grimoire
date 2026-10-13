"""APG166S-R2 worker carry-forward regression and posture tests.

Validates that real apgr_workers.supervisor.run_supervisor launches the external
codex executable on PATH without live provider dependency, captures child argv
and environment, strips CODEX_THREAD_ID and CODEX_SESSION_ID orchestration markers,
and inherits CODEX_CI and APG166S_BOOTSTRAP_REQUIRED_WORKERS when present.
Also validates read_only vs mutation_capable Git posture in build_codex_exec_argv.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import sys
from typing import Any

import pytest

# Ensure libexec is on sys.path
ROOT = Path(__file__).resolve().parents[3]
LIBEXEC = ROOT / "libexec"
if str(LIBEXEC) not in sys.path:
    sys.path.insert(0, str(LIBEXEC))

from apgr_workers.codex_external import (
    CodexExternalError,
    LunaProfile,
    build_codex_exec_argv,
    load_luna_profile,
)
from apgr_workers.supervisor import run_supervisor


def _create_fake_codex_executable(bin_dir: Path) -> Path:
    """Create a standalone fake codex executable that records invocation and emits JSONL."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    fake_codex = bin_dir / "codex"
    script = "#!" + sys.executable + "\n" + """
import json
import os
import sys
from pathlib import Path

capture_file = os.environ.get("FAKE_CODEX_CAPTURE_FILE")
if capture_file:
    payload = {
        "argv": list(sys.argv),
        "env": {key: os.environ[key] for key in (
            "CODEX_THREAD_ID", "CODEX_SESSION_ID", "CODEX_CI",
            "APG166S_BOOTSTRAP_REQUIRED_WORKERS", "APGR_WORKER_LEAF"
        ) if key in os.environ},
    }
    Path(capture_file).write_text(json.dumps(payload, indent=2), encoding="utf-8")

# Drain stdin prompt if present
try:
    _ = sys.stdin.read()
except Exception:
    pass

# Emit expected provider metadata and completion JSONL
print(json.dumps({"type": "model_info", "model": "gpt-6-luna", "effort": "max"}), flush=True)
print(json.dumps({"type": "item.completed", "text": "synthetic codex worker response"}), flush=True)
sys.exit(0)
"""
    fake_codex.write_text(script, encoding="utf-8")
    fake_codex.chmod(fake_codex.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return fake_codex


def test_supervisor_codex_env_carry_forward_and_argv_identity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Real run_supervisor with fake codex on PATH verifies argv identity and env carry-forward."""
    bin_dir = tmp_path / "bin"
    _create_fake_codex_executable(bin_dir)

    # Isolate PATH so fake codex is resolved first
    original_path = os.environ.get("PATH", "")
    monkeypatch.setenv("PATH", f"{bin_dir}:{original_path}")

    # Isolate authentication and user homes to prevent live provider access
    fake_codex_home = tmp_path / "fake_codex_home"
    fake_codex_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("CODEX_HOME", str(fake_codex_home))
    monkeypatch.setenv("HOME", str(tmp_path / "fake_user_home"))
    monkeypatch.delenv("APGR_HOME", raising=False)

    # Track ledger calls and stub ledger boundary
    ledger_calls: list[tuple[str, str, tuple[Any, ...], dict[str, Any]]] = []

    def stub_call_ledger(ledger: Any, worker_kind: str, operation: str, *args: Any, **kwargs: Any) -> Any:
        ledger_calls.append((worker_kind, operation, args, kwargs))
        return True

    monkeypatch.setattr("apgr_workers.supervisor._call_ledger", stub_call_ledger)

    workspace = (tmp_path / "workspace").resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    # --- Run 1: WITH ambient orchestration markers ---
    monkeypatch.setenv("CODEX_THREAD_ID", "thread-test-run-1")
    monkeypatch.setenv("CODEX_SESSION_ID", "session-test-run-1")
    monkeypatch.setenv("CODEX_CI", "1")
    monkeypatch.setenv("APG166S_BOOTSTRAP_REQUIRED_WORKERS", "1")

    out_dir_with = tmp_path / "out_with"
    out_dir_with.mkdir(parents=True, exist_ok=True)
    capture_with = tmp_path / "capture_with.json"
    monkeypatch.setenv("FAKE_CODEX_CAPTURE_FILE", str(capture_with))

    task_file_with = tmp_path / "task_with.json"
    task_file_with.write_text(
        json.dumps({
            "job_id": "job-with-markers",
            "parent_id": "parent-apg166s-r2",
            "worker_kind": "luna",
            "profile": "luna-worker",
            "task_authority": "read_only",
            "mutation_scope": [],
            "acceptance_criteria": "capture argv and env with markers",
            "task": "Test read-only leaf execution with ambient markers",
            "workspace": str(workspace),
            "output_dir": str(out_dir_with),
        }),
        encoding="utf-8",
    )

    exit_code_with = run_supervisor(
        parent_id="parent-apg166s-r2",
        job_id="job-with-markers",
        task_file=task_file_with,
        state_dir=tmp_path / "state_with",
    )
    assert exit_code_with == 0

    assert capture_with.is_file()
    data_with = json.loads(capture_with.read_text(encoding="utf-8"))
    argv_with = data_with["argv"]
    env_with = data_with["env"]

    # Verify result artifact was created and succeeded
    result_path_with = out_dir_with / "job-with-markers.result.json"
    assert result_path_with.is_file()
    result_with = json.loads(result_path_with.read_text(encoding="utf-8"))
    assert result_with["status"] == "completed"
    assert result_with["exit_code"] == 0
    assert result_with["worker_kind"] == "luna"
    assert result_with["cleanup_proven"] is True
    assert not {"wrapper_exit_status", "provider_raw_status", "provider_raw_error",
                "provider_natural_exit", "completion_contract", "terminal_chronology"} & result_with.keys()

    # --- Run 2: WITHOUT ambient orchestration markers ---
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.delenv("CODEX_SESSION_ID", raising=False)
    monkeypatch.delenv("CODEX_CI", raising=False)
    monkeypatch.delenv("APG166S_BOOTSTRAP_REQUIRED_WORKERS", raising=False)

    out_dir_without = tmp_path / "out_without"
    out_dir_without.mkdir(parents=True, exist_ok=True)
    capture_without = tmp_path / "capture_without.json"
    monkeypatch.setenv("FAKE_CODEX_CAPTURE_FILE", str(capture_without))

    task_file_without = tmp_path / "task_without.json"
    task_file_without.write_text(
        json.dumps({
            "job_id": "job-without-markers",
            "parent_id": "parent-apg166s-r2",
            "worker_kind": "luna",
            "profile": "luna-worker",
            "task_authority": "read_only",
            "mutation_scope": [],
            "acceptance_criteria": "capture argv and env without markers",
            "task": "Test read-only leaf execution without ambient markers",
            "workspace": str(workspace),
            "output_dir": str(out_dir_without),
        }),
        encoding="utf-8",
    )

    exit_code_without = run_supervisor(
        parent_id="parent-apg166s-r2",
        job_id="job-without-markers",
        task_file=task_file_without,
        state_dir=tmp_path / "state_without",
    )
    assert exit_code_without == 0

    assert capture_without.is_file()
    data_without = json.loads(capture_without.read_text(encoding="utf-8"))
    argv_without = data_without["argv"]
    env_without = data_without["env"]

    # Verify result artifact was created and succeeded
    result_path_without = out_dir_without / "job-without-markers.result.json"
    assert result_path_without.is_file()
    result_without = json.loads(result_path_without.read_text(encoding="utf-8"))
    assert result_without["status"] == "completed"
    assert result_without["exit_code"] == 0

    # --- Invariant 1: Captured argv is IDENTICAL across runs ---
    assert argv_with == argv_without
    # Verify core argv structure
    assert argv_with[0].endswith("codex")
    assert argv_with[1:3] == ["exec", "--json"]
    assert "--skip-git-repo-check" in argv_with
    assert "--ignore-user-config" in argv_with
    assert "-c" in argv_with
    assert 'model="gpt-6-luna"' in argv_with
    assert 'model_reasoning_effort="max"' in argv_with
    assert "agents.enabled=false" in argv_with
    assert "--sandbox" in argv_with
    assert argv_with[argv_with.index("--sandbox") + 1] == "read-only"
    assert argv_with[-1] == "-"

    # --- Invariant 2: CODEX_THREAD_ID and CODEX_SESSION_ID are ALWAYS STRIPPED ---
    assert "CODEX_THREAD_ID" not in env_with
    assert "CODEX_SESSION_ID" not in env_with
    assert "CODEX_THREAD_ID" not in env_without
    assert "CODEX_SESSION_ID" not in env_without

    # --- Invariant 3: CODEX_CI and APG166S marker are INHERITED WHEN PRESENT ---
    assert env_with.get("CODEX_CI") == "1"
    assert env_with.get("APG166S_BOOTSTRAP_REQUIRED_WORKERS") == "1"

    # --- Invariant 4: CODEX_CI and APG166S marker are ABSENT WHEN NOT PRESENT ---
    assert "CODEX_CI" not in env_without
    assert "APG166S_BOOTSTRAP_REQUIRED_WORKERS" not in env_without

    # --- Invariant 5: APGR_WORKER_LEAF is always set to '1' ---
    assert env_with.get("APGR_WORKER_LEAF") == "1"
    assert env_without.get("APGR_WORKER_LEAF") == "1"

    # --- Invariant 6: Real ledger lifecycle boundary operations were executed ---
    operations = [op for _, op, _, _ in ledger_calls]
    assert "bind_supervisor" in operations
    assert "record_provider_custody" in operations
    assert "update_status" in operations


def test_build_codex_exec_argv_git_posture_and_authority(tmp_path: Path) -> None:
    """Compare build_codex_exec_argv read_only and mutation_capable Git checks."""
    profile = load_luna_profile(ROOT, "luna-worker")
    workspace = (tmp_path / "ws").resolve()

    argv_ro = build_codex_exec_argv(profile, workspace, "read_only")
    argv_mut = build_codex_exec_argv(profile, workspace, "mutation_capable")

    # Read-only posture: skips git repo check, sets sandbox to read-only
    assert "--skip-git-repo-check" in argv_ro
    sandbox_ro_idx = argv_ro.index("--sandbox")
    assert argv_ro[sandbox_ro_idx + 1] == "read-only"

    # Mutation-capable posture: retains Git repo check (no skip), sets sandbox to workspace-write
    assert "--skip-git-repo-check" not in argv_mut
    sandbox_mut_idx = argv_mut.index("--sandbox")
    assert argv_mut[sandbox_mut_idx + 1] == "workspace-write"

    # Common security and configuration invariants across both postures
    for argv in (argv_ro, argv_mut):
        assert argv[0] == "codex"
        assert argv[1:3] == ["exec", "--json"]
        assert "--ignore-user-config" in argv
        assert f"model={json.dumps(profile.model)}" in argv
        assert f"model_reasoning_effort={json.dumps(profile.effort)}" in argv
        assert "agents.enabled=false" in argv
        assert "--cd" in argv
        assert argv[argv.index("--cd") + 1] == str(workspace)
        assert argv[-1] == "-"

    # Posture differences are precisely the git check flag and sandbox mode
    ro_flags_set = set(argv_ro)
    mut_flags_set = set(argv_mut)
    diff_ro = ro_flags_set - mut_flags_set
    diff_mut = mut_flags_set - ro_flags_set
    assert diff_ro == {"--skip-git-repo-check", "read-only"}
    assert diff_mut == {"workspace-write"}

    # Negative authority assertions
    with pytest.raises(CodexExternalError, match="task authority must be read_only or mutation_capable"):
        build_codex_exec_argv(profile, workspace, "root_authority")

    with pytest.raises(CodexExternalError, match="task authority must be read_only or mutation_capable"):
        build_codex_exec_argv(profile, workspace, "")


def test_build_codex_exec_argv_profile_validation(tmp_path: Path) -> None:
    """LunaProfile validation rejects invalid or agent-enabled configurations."""
    workspace = (tmp_path / "ws").resolve()

    invalid_profile = LunaProfile(
        name="invalid-luna",
        model="gpt-6-luna",
        effort="max",
        agents_enabled=True,  # Violation: agents must be disabled for leaf
        source="codex/profiles/luna-worker.config.toml",
        source_sha256="abc",
        projection_matches_selected=True,
    )
    with pytest.raises(CodexExternalError, match="external Luna transport requires a valid LunaProfile with agents disabled"):
        build_codex_exec_argv(invalid_profile, workspace, "read_only")
