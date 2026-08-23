"""Cross-process integration replay for the APGR CLI package contract."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

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
    inherited_site_packages = [p for p in sys.path if p]
    environment["PYTHONPATH"] = os.pathsep.join(
        (os.fspath(ROOT / "src"), os.fspath(ROOT), *inherited_site_packages)
    )
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
    assert "passed" in completed.stdout


def test_python_skill_bridge_matches_oracle_and_routes_new_go_surfaces(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.syspath_prepend(os.fspath(ROOT / "src"))
    monkeypatch.syspath_prepend(os.fspath(ROOT / "private/oracles"))
    from agentic_praxis_grimoire import cli
    import skills

    binary = tmp_path / "apgr"
    built = subprocess.run(
        ["go", "build", "-trimpath", "-buildvcs=false", "-o", binary, "./cmd/apgr"],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    assert built.returncode == 0, built.stderr
    monkeypatch.setenv("APGR_GO_BINARY", os.fspath(binary))

    for action, arguments in (
        ("list", ["--format", "json"]),
        ("context-report", []),
        ("context-report", ["--format", "text"]),
    ):
        assert skills.main(action, arguments) == 0
        oracle = capfd.readouterr()
        assert cli.main(["skills", action, *arguments]) == 0
        delegated = capfd.readouterr()
        assert delegated == oracle

    request = tmp_path / "request.json"
    request.write_text(
        '{"budget":{"max_body_bytes":null,"max_description_bytes":null,'
        '"max_initial_context_bytes":null,"prompt_overhead_bytes":0},'
        '"capabilities":[],"consumer":{"architecture":"","kind":"codex",'
        '"materialization_form":"flat_directory","operating_system":"",'
        '"provider_constraints":["filesystem_skill_discovery","isolated_apg_root"]},'
        '"eager_bodies":false,"explicit_skill_ids":["planning-repository-work"],'
        '"languages":[],"repository_characteristics":[],"runtimes":[],'
        '"schema_version":"apg.skill-bundle-request/v1","test_frameworks":[],'
        '"work_class":""}\n',
        encoding="utf-8",
    )
    request.chmod(0o600)
    assert cli.main(["skills", "resolve", "--request", os.fspath(request)]) == 0
    resolved = capfd.readouterr()
    assert resolved.err == ""
    result = tmp_path / "result.json"
    result.write_text(resolved.out, encoding="utf-8")
    result.chmod(0o600)
    destination = tmp_path / "destination"
    destination.mkdir(mode=0o700)
    assert cli.main(
        [
            "skills",
            "materialize",
            "--result",
            os.fspath(result),
            "--destination-parent",
            os.fspath(destination),
        ]
    ) == 0
    materialized = capfd.readouterr()
    assert materialized.err == ""
    assert '"selected_files":[{"body_bytes":' in materialized.out


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
