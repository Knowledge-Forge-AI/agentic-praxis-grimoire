"""Integration tests for APGR python_retention_inventory using disposable Git repositories."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ENTRYPOINT = Path(__file__).resolve().parents[7] / "tools/ci/python_retention_inventory.py"


def init_disposable_repo(root: Path) -> None:
    for d in ("src/agentic_praxis_grimoire", "libexec", "tools", "release/ci", "src/test", "bin"):
        (root / d).mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    subprocess.run(["git", "init", "-q", str(root)], check=True, env=env)


def git_add(root: Path, *paths: str) -> None:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    subprocess.run(["git", "-C", str(root), "add", "--", *paths], check=True, env=env)


def run_cli(
    root: Path,
    *extra_args: str,
) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[7])
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


def test_cli_disposable_repo_success(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    init_disposable_repo(root)

    f1 = root / "libexec/helper.py"
    f1.write_text("def h(): pass\n", encoding="utf-8")
    f2 = root / "bin/my-tool"
    f2.write_bytes(b"#!/usr/bin/env python3\nprint('ok')\n")
    f3 = root / "bin/my-shell"
    f3.write_bytes(b"#!/bin/bash\necho ok\n")
    git_add(root, "libexec/helper.py", "bin/my-tool", "bin/my-shell")

    proc = run_cli(root, "--check", "--json")
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["status"] == "passed"
    assert data["classification"] == "passed"
    assert data["schema"] == "apg-python-retention-inventory-v1"
    assert data["counts"]["total_files"] == 2
    paths = [m["path"] for m in data["modules"]]
    assert "libexec/helper.py" in paths
    assert "bin/my-tool" in paths
    assert "bin/my-shell" not in paths


def test_cli_missing_candidate_fails_with_tool_failure(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    init_disposable_repo(root)

    f = root / "libexec/ghost.py"
    f.write_text("pass\n", encoding="utf-8")
    git_add(root, "libexec/ghost.py")
    f.unlink()

    proc = run_cli(root, "--check", "--json")
    assert proc.returncode == 2
    data = json.loads(proc.stdout)
    assert data["status"] == "failed"
    assert data["classification"] == "tool-failure"
    assert "missing or not a regular file" in data["detail"]


def test_cli_non_git_root_fails_with_tool_failure(tmp_path: Path) -> None:
    root = tmp_path / "non_git"
    root.mkdir()

    proc = run_cli(root, "--check", "--json")
    assert proc.returncode == 2
    data = json.loads(proc.stdout)
    assert data["status"] == "failed"
    assert data["classification"] == "tool-failure"


def test_cli_real_repo_passes() -> None:
    repo_root = Path(__file__).resolve().parents[7]
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["PYTHONPATH"] = str(repo_root)
    proc = subprocess.run(
        [sys.executable, str(ENTRYPOINT), "--check", "--json"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=repo_root,
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["status"] == "passed"
    assert data["classification"] == "passed"
    assert data["counts"]["total_files"] >= 278


def test_cli_public_inventory_completeness(tmp_path: Path) -> None:
    """Decision A fixture: census covers candidate files across candidate roots without omitting new candidate files."""
    root = tmp_path / "candidate_repo"
    init_disposable_repo(root)
    for d in ("src/agentic_praxis_grimoire", "libexec", "tools", "release/ci", "src/test", "bin"):
        p = root / d / ("tool_script" if d == "bin" else "component.py")
        p.parent.mkdir(parents=True, exist_ok=True)
        if d == "bin":
            p.write_bytes(b"#!/usr/bin/env python3\nprint('tool')\n")
            p.chmod(0o755)
        else:
            p.write_bytes(b"x = 1\n")
        git_add(root, str(p.relative_to(root)))
    proc = run_cli(root, "--check", "--json")
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["status"] == "passed"
    assert data["classification"] == "passed"
    assert data["counts"]["total_files"] == 6

