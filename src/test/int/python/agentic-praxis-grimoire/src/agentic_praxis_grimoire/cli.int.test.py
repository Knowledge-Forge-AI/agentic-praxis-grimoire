"""Cross-process integration replay for the APGR CLI package contract."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
PACKAGE_UNIT_ROOT = (
    ROOT
    / "src/test/unit/python/agentic-praxis-grimoire/src/agentic_praxis_grimoire"
)


def test_package_contracts_replay_in_an_isolated_python_process(
    tmp_path: Path,
) -> None:
    """Keep the maintained package branch contract observable across a child."""

    environment = os.environ.copy()
    environment["PYTEST_ADDOPTS"] = ""
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            f"--basetemp={tmp_path / 'child-base'}",
            os.fspath(PACKAGE_UNIT_ROOT),
        ],
        cwd=ROOT,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, (
        f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    )
    assert "154 passed" in completed.stdout


def test_checkout_apgr_rejects_symlinked_source_adapter(tmp_path: Path) -> None:
    checkout = tmp_path / "checkout"
    bin_root = checkout / "bin"
    bin_root.mkdir(parents=True)
    launcher = bin_root / "apgr"
    launcher.write_bytes((ROOT / "bin/apgr").read_bytes())
    launcher.chmod(0o755)
    (checkout / "src").symlink_to(ROOT / "src", target_is_directory=True)

    completed = subprocess.run(
        [os.fspath(launcher), "--version"],
        cwd=checkout,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    assert completed.returncode == 1
    assert completed.stderr == "apgr: source checkout package is unavailable\n"


def test_checkout_apgr_rejects_launcher_outside_bin_directory(tmp_path: Path) -> None:
    checkout = tmp_path / "checkout"
    shutil.copytree(
        ROOT / "src/agentic_praxis_grimoire",
        checkout / "src/agentic_praxis_grimoire",
    )
    tools = checkout / "tools"
    tools.mkdir()
    launcher = tools / "apgr"
    launcher.write_bytes((ROOT / "bin/apgr").read_bytes())
    launcher.chmod(0o755)

    completed = subprocess.run(
        [os.fspath(launcher), "--version"],
        cwd=checkout,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    assert completed.returncode == 1
    assert completed.stderr == "apgr: source checkout package is unavailable\n"
