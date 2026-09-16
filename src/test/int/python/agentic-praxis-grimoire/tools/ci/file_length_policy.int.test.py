"""Integration tests for APGR file_length_policy using disposable Git repositories."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ENTRYPOINT = Path(__file__).resolve().parents[7] / "tools/ci/file_length_policy.py"


def init_disposable_repo(root: Path) -> None:
    """Initialize a disposable git repository with standard APGR candidate layout."""
    (root / "src/agentic_praxis_grimoire").mkdir(parents=True, exist_ok=True)
    (root / "libexec").mkdir(parents=True, exist_ok=True)
    (root / "tools/ci").mkdir(parents=True, exist_ok=True)
    (root / "release/ci").mkdir(parents=True, exist_ok=True)
    (root / "src/test").mkdir(parents=True, exist_ok=True)
    (root / "bin").mkdir(parents=True, exist_ok=True)

    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    subprocess.run(["git", "init", "-q", str(root)], check=True, env=env)


def git_add(root: Path, *paths: str) -> None:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    subprocess.run(["git", "-C", str(root), "add", "--", *paths], check=True, env=env)


def write_lines(path: Path, line_count: int, terminate: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if line_count == 0:
        path.write_bytes(b"")
        return
    content = b"x\n" * (line_count - 1)
    if terminate:
        content += b"x\n"
    else:
        content += b"x"
    path.write_bytes(content)


def make_policy_file(root: Path, allowances: list[dict] | None = None) -> Path:
    policy_file = root / "tools/ci/file_length_policy.json"
    policy_file.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "schema": "apg-file-length-policy-v1",
        "warning_limit": 400,
        "failure_limit": 1000,
        "allowances": allowances or [],
    }
    policy_file.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return policy_file


def run_cli(
    root: Path,
    *extra_args: str,
    env_override: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[7])
    if env_override:
        env.update(env_override)
    cmd = [
        sys.executable,
        str(ENTRYPOINT),
        "--repo-root",
        str(root),
        *extra_args,
    ]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=root,
    )


def test_clean_repo_passes(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    init_disposable_repo(root)
    make_policy_file(root)
    f = root / "libexec/helper.py"
    write_lines(f, 200)
    git_add(root, "libexec/helper.py")

    proc = run_cli(root)
    assert proc.returncode == 0
    assert "file-length: passed\n" in proc.stdout
    assert "warnings: 0\n" in proc.stdout
    assert "failures: 0\n" in proc.stdout


def test_retained_warning_boundary_401(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    init_disposable_repo(root)
    make_policy_file(root)
    f = root / "libexec/warn.py"
    write_lines(f, 401)
    git_add(root, "libexec/warn.py")

    proc = run_cli(root, "--format", "json")
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["status"] == "passed_with_warnings"
    assert data["warning_count"] == 1
    assert data["failure_count"] == 0
    assert data["findings"][0]["path"] == "libexec/warn.py"
    assert data["findings"][0]["severity"] == "warning"


def test_retained_oversized_file_with_allowance_passes_as_warning(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    init_disposable_repo(root)
    f = root / "libexec/oversized.py"
    write_lines(f, 1050)
    git_add(root, "libexec/oversized.py")

    make_policy_file(
        root,
        [
            {
                "path": "libexec/oversized.py",
                "role": "maintained-source",
                "owner": "test-owner",
                "sha256": "e" * 64,
                "count": 1050,
                "rationale": "Historical oversized",
                "maintenance": "Refactor",
            }
        ],
    )

    proc = run_cli(root)
    assert proc.returncode == 0
    assert "file-length: passed with warnings\n" in proc.stdout
    assert "warnings: 1\n" in proc.stdout
    assert "failures: 0\n" in proc.stdout
    assert "WARNING  1050  libexec/oversized.py" in proc.stdout


def test_new_oversized_file_without_allowance_fails(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    init_disposable_repo(root)
    make_policy_file(root)
    f = root / "libexec/new_fail.py"
    write_lines(f, 1001)
    git_add(root, "libexec/new_fail.py")

    proc = run_cli(root)
    assert proc.returncode == 1
    assert "file-length: failed\n" in proc.stdout
    assert "failures: 1\n" in proc.stdout
    assert "FAILURE  1001  libexec/new_fail.py" in proc.stdout


def test_retained_growth_beyond_allowance_fails(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    init_disposable_repo(root)
    f = root / "libexec/growing.py"
    write_lines(f, 1051)
    git_add(root, "libexec/growing.py")

    make_policy_file(
        root,
        [
            {
                "path": "libexec/growing.py",
                "role": "maintained-source",
                "owner": "test-owner",
                "sha256": "f" * 64,
                "count": 1050,
                "rationale": "Historical oversized",
                "maintenance": "Refactor",
            }
        ],
    )

    proc = run_cli(root, "--format", "json")
    assert proc.returncode == 1
    data = json.loads(proc.stdout)
    assert data["status"] == "failed"
    assert data["failure_count"] == 1
    assert data["findings"][0]["path"] == "libexec/growing.py"
    assert data["findings"][0]["severity"] == "failure"


def test_allowance_is_nontransferable_on_removal(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    init_disposable_repo(root)
    # File A had allowance
    make_policy_file(
        root,
        [
            {
                "path": "libexec/old_allowed.py",
                "role": "maintained-source",
                "owner": "test-owner",
                "sha256": "a" * 64,
                "count": 1200,
                "rationale": "test",
                "maintenance": "test",
            }
        ],
    )
    # File A is NOT created/tracked (removed), but File B is created with 1100 lines
    file_b = root / "libexec/new_target.py"
    write_lines(file_b, 1100)
    git_add(root, "libexec/new_target.py")

    proc = run_cli(root)
    # File B must not inherit File A's allowance!
    assert proc.returncode == 1
    assert "FAILURE  1100  libexec/new_target.py" in proc.stdout


def test_no_aggregate_failure_count_allowance(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    init_disposable_repo(root)
    file_allowed = root / "libexec/allowed.py"
    write_lines(file_allowed, 1200)
    file_unallowed = root / "libexec/unallowed.py"
    write_lines(file_unallowed, 1005)
    git_add(root, "libexec/allowed.py", "libexec/unallowed.py")

    make_policy_file(
        root,
        [
            {
                "path": "libexec/allowed.py",
                "role": "maintained-source",
                "owner": "test-owner",
                "sha256": "b" * 64,
                "count": 1200,
                "rationale": "test",
                "maintenance": "test",
            }
        ],
    )

    proc = run_cli(root)
    assert proc.returncode == 1
    assert "failures: 1\n" in proc.stdout
    assert "warnings: 1\n" in proc.stdout
    assert "FAILURE  1005  libexec/unallowed.py" in proc.stdout
    assert "WARNING  1200  libexec/allowed.py" in proc.stdout


def test_unterminated_last_line_counts_correctly(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    init_disposable_repo(root)
    make_policy_file(root)
    # Exactly 400 lines without newline => counts as 400
    f1 = root / "libexec/exact400.py"
    write_lines(f1, 400, terminate=False)
    # 400 lines without newline + 1 byte => counts as 401 => warning
    f2 = root / "libexec/warn401.py"
    write_lines(f2, 401, terminate=False)
    # 0 bytes => 0 lines
    f3 = root / "libexec/empty.py"
    write_lines(f3, 0)
    git_add(root, "libexec/exact400.py", "libexec/warn401.py", "libexec/empty.py")

    proc = run_cli(root, "--format", "json")
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["status"] == "passed_with_warnings"
    assert data["warning_count"] == 1
    assert data["failure_count"] == 0
    assert data["findings"][0]["path"] == "libexec/warn401.py"
    assert data["findings"][0]["line_count"] == 401


def test_malformed_policy_fails_with_exit_2(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    init_disposable_repo(root)
    policy_file = root / "tools/ci/file_length_policy.json"
    policy_file.parent.mkdir(parents=True, exist_ok=True)
    policy_file.write_text("{ corrupt json ", encoding="utf-8")

    proc = run_cli(root)
    assert proc.returncode == 2
    assert "file-length: error: malformed policy JSON" in proc.stderr


def test_duplicate_policy_fails_with_exit_2(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    init_disposable_repo(root)
    entry = {
        "path": "libexec/dup.py",
        "role": "maintained-source",
        "owner": "test",
        "sha256": "c" * 64,
        "count": 1200,
        "rationale": "test",
        "maintenance": "test",
    }
    make_policy_file(root, [entry, entry])

    proc = run_cli(root)
    assert proc.returncode == 2
    assert "duplicate allowance path" in proc.stderr


def test_missing_tracked_file_fails_with_exit_2(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    init_disposable_repo(root)
    make_policy_file(root)
    f = root / "libexec/missing_after_add.py"
    write_lines(f, 50)
    git_add(root, "libexec/missing_after_add.py")
    f.unlink()

    proc = run_cli(root)
    assert proc.returncode == 2
    assert "missing or not a regular file" in proc.stderr


def test_untracked_files_ignored_by_default(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    init_disposable_repo(root)
    make_policy_file(root)
    # Tracked file with 10 lines
    tracked = root / "libexec/ok.py"
    write_lines(tracked, 10)
    git_add(root, "libexec/ok.py")
    # Untracked file with 5000 lines
    untracked = root / "libexec/untracked_huge.py"
    write_lines(untracked, 5000)

    # By default, untracked is not scanned -> exit 0
    proc = run_cli(root)
    assert proc.returncode == 0
    assert "failures: 0\n" in proc.stdout

    # With --include-untracked, untracked is scanned -> exit 1
    proc_untracked = run_cli(root, "--include-untracked")
    assert proc_untracked.returncode == 1
    assert "FAILURE  5000  libexec/untracked_huge.py" in proc_untracked.stdout


def test_shebang_scripts_in_bin(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    init_disposable_repo(root)
    make_policy_file(root)

    # Python shebang script exceeding 1000 lines -> scanned and fails
    py_tool = root / "bin/py-tool"
    py_tool.write_bytes(b"#!/usr/bin/env python3\n" + b"x = 1\n" * 1001)
    # Bash shebang script exceeding 1000 lines -> excluded
    sh_tool = root / "bin/sh-tool"
    sh_tool.write_bytes(b"#!/bin/bash\n" + b"echo hi\n" * 1001)
    git_add(root, "bin/py-tool", "bin/sh-tool")

    proc = run_cli(root)
    assert proc.returncode == 1
    assert "FAILURE  1002  bin/py-tool" in proc.stdout
    assert "bin/sh-tool" not in proc.stdout


def test_git_environment_isolation(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    init_disposable_repo(root)
    make_policy_file(root)
    f = root / "libexec/sample.py"
    write_lines(f, 20)
    git_add(root, "libexec/sample.py")

    fake_index = tmp_path / "nonexistent.index"
    proc = run_cli(root, env_override={"GIT_INDEX_FILE": str(fake_index)})
    assert proc.returncode == 0
    assert "scanned: 1 Python files" in proc.stdout
