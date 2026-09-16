"""Unit tests for APGR python_retention_inventory shared census and selection."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from tools.ci.python_inventory import (
    classify_exclusion,
    is_candidate_root,
)
from tools.ci.python_retention_inventory import collect_inventory


def init_disposable_repo(root: Path) -> None:
    for d in ("src/agentic_praxis_grimoire", "libexec", "tools", "release/ci", "src/test", "bin"):
        (root / d).mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    subprocess.run(["git", "init", "-q", str(root)], check=True, env=env)


def git_add(root: Path, *paths: str) -> None:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    subprocess.run(["git", "-C", str(root), "add", "--", *paths], check=True, env=env)


def test_is_candidate_root() -> None:
    assert is_candidate_root(("src", "agentic_praxis_grimoire", "cli.py")) is True
    assert is_candidate_root(("src", "test", "unit.test.py")) is True
    assert is_candidate_root(("libexec", "helper.py")) is True
    assert is_candidate_root(("tools", "ci", "policy.py")) is True
    assert is_candidate_root(("release", "ci", "matrix.py")) is True
    assert is_candidate_root(("bin", "apg-test")) is True
    assert is_candidate_root(("docs", "README.md")) is False
    assert is_candidate_root((".github", "workflows", "test.yml")) is False
    assert is_candidate_root(("src", "other", "file.py")) is False


def test_classify_exclusion() -> None:
    assert classify_exclusion(("private", "evaluations", "data.json")) == "private"
    assert classify_exclusion(("tools", "__pycache__", "foo.pyc")) == "cache"
    assert classify_exclusion(("node_modules", "package", "index.js")) == "vendor"
    assert classify_exclusion((".venv", "lib", "site.py")) == "vendor"
    assert classify_exclusion(("build", "lib", "bundle.py")) == "generated"
    assert classify_exclusion((".scratch", "temp.py")) == "generated"
    assert classify_exclusion((".agents", "skills", "python-language-profile")) == "projections"
    assert classify_exclusion(("docs", "adr", "0001.md")) == "non_candidate_root"
    assert classify_exclusion(("src", "agentic_praxis_grimoire", "cli.py")) is None


def test_collect_inventory_disposable_repo(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    init_disposable_repo(root)

    pkg_file = root / "src/agentic_praxis_grimoire/cli.py"
    pkg_file.write_text("print('cli')\n", encoding="utf-8")

    test_file = root / "src/test/cli.test.py"
    test_file.write_text("def test_cli(): pass\n", encoding="utf-8")

    bin_file = root / "bin/run-tool"
    bin_file.write_bytes(b"#!/usr/bin/env python3\nprint('run')\n")

    bin_sh = root / "bin/run-sh"
    bin_sh.write_bytes(b"#!/bin/bash\necho run\n")

    git_add(
        root,
        "src/agentic_praxis_grimoire/cli.py",
        "src/test/cli.test.py",
        "bin/run-tool",
        "bin/run-sh",
    )

    inv = collect_inventory(repo_root=root)
    assert inv["schema"] == "apg-python-retention-inventory-v1"
    assert inv["status"] == "passed"
    assert inv["classification"] == "passed"

    modules = {m["path"]: m for m in inv["modules"]}
    assert "src/agentic_praxis_grimoire/cli.py" in modules
    assert "src/test/cli.test.py" in modules
    assert "bin/run-tool" in modules
    assert "bin/run-sh" not in modules

    pkg_mod = modules["src/agentic_praxis_grimoire/cli.py"]
    assert pkg_mod["type_owner"] == "mypy"
    assert pkg_mod["role"] == "maintained-source"
    assert pkg_mod["syntax_owner"] == "python-compile"
    assert pkg_mod["lint_owner"] == "ruff"

    test_mod = modules["src/test/cli.test.py"]
    assert test_mod["type_owner"] is None
    assert test_mod["role"] == "fixture-or-test"

    bin_mod = modules["bin/run-tool"]
    assert bin_mod["type_owner"] is None
    assert bin_mod["role"] == "maintained-source"

    assert inv["counts"]["total_files"] == 3
    assert inv["counts"]["excluded"]["non_python"] == 1


def test_collect_inventory_fails_on_missing_candidate(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    init_disposable_repo(root)
    sample = root / "libexec/helper.py"
    sample.write_text("pass\n", encoding="utf-8")
    git_add(root, "libexec/helper.py")
    sample.unlink()

    with pytest.raises(ValueError, match="missing or not a regular file"):
        collect_inventory(repo_root=root)


def test_collect_inventory_fails_on_tracked_symlink(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    init_disposable_repo(root)
    target = root / "libexec/target.py"
    target.write_text("pass\n", encoding="utf-8")
    link = root / "libexec/link.py"
    link.symlink_to(target)
    git_add(root, "libexec/link.py")

    with pytest.raises(ValueError, match="tracked candidate path is a symlink"):
        collect_inventory(repo_root=root)
