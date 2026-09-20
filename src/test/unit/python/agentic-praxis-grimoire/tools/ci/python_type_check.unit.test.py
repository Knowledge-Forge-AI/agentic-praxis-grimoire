"""Unit tests for APGR pinned owned mypy identity and type check runner."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import venv

from tools.ci.mypy_identity import (
    get_expected_mypy_version,
)
from tools.ci.python_type_check import ROOT, run_type_check


def make_tool_root(root: Path) -> Path:
    tool_root = root / "tools"
    py_bin = tool_root / "python" / "bin"
    py_bin.mkdir(parents=True, exist_ok=True)
    python_exe = py_bin / "python"
    python_exe.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    python_exe.chmod(0o755)
    return tool_root


def make_manifest(root: Path, targets: list[str] | None = None) -> Path:
    manifest_path = root / "python_type_ownership.json"
    manifest_path.write_text(
        json.dumps({
            "schema": "apg-python-type-ownership-v1",
            "targets": targets or ["src/agentic_praxis_grimoire"],
        }),
        encoding="utf-8",
    )
    return manifest_path


def make_valid_probe_runner(tool_root: Path, expected_version: str):
    python_dir = (tool_root / "python").resolve()

    def runner(cmd, **kwargs):
        command = list(cmd)
        if "-c" in command:
            payload = {
                "prefix": str(python_dir),
                "mypy_file": str(python_dir / "lib/python3.13/site-packages/mypy/__init__.py"),
                "meta_version": expected_version,
            }
            return subprocess.CompletedProcess(cmd, 0, json.dumps(payload), "")
        if "--version" in command:
            return subprocess.CompletedProcess(cmd, 0, f"mypy {expected_version} (compiled: yes)", "")
        return subprocess.CompletedProcess(cmd, 0, "Success: no issues found\n", "")

    return runner


def test_rootless_invocation_fails_closed(tmp_path: Path) -> None:
    manifest = make_manifest(tmp_path)
    code = run_type_check(manifest, tool_root=None)
    assert code == 2


def test_real_owned_interpreter_executes_probe_and_ignores_shadowing(tmp_path: Path, monkeypatch) -> None:
    """Exercise the production probe and command through a disposable synthetic engine."""
    tool_root = tmp_path / "real-tools"
    python_dir = tool_root / "python"
    venv.EnvBuilder(with_pip=False).create(python_dir)
    python = python_dir / "bin/python"
    sites = json.loads(subprocess.check_output(
        [str(python), "-I", "-c", "import json,site;print(json.dumps(site.getsitepackages()))"], text=True
    ))
    site = next(Path(p) for p in sites if Path(p).is_relative_to(python_dir))
    package = site / "mypy"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("# Synthetic tool for identity contract only.\n")
    pin = get_expected_mypy_version()
    metadata = site / f"mypy-{pin}.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text(f"Metadata-Version: 2.1\nName: mypy\nVersion: {pin}\n")
    (package / "__main__.py").write_text(
        f"import sys\nprint('mypy {pin}' if '--version' in sys.argv else 'owned synthetic check')\n"
    )
    ambient = tmp_path / "ambient"
    (ambient / "mypy").mkdir(parents=True)
    marker = tmp_path / "shadow-executed"
    (ambient / "mypy/__init__.py").write_text(f"from pathlib import Path\nPath({str(marker)!r}).touch()\n")
    executable = ambient / "mypy-bin"
    executable.mkdir()
    (executable / "mypy").write_text(f"#!/bin/sh\ntouch '{marker}'\nexit 0\n")
    (executable / "mypy").chmod(0o755)
    monkeypatch.setenv("PYTHONPATH", str(ambient))
    monkeypatch.setenv("PATH", str(executable))
    assert run_type_check(make_manifest(tmp_path), tool_root=tool_root) == 0
    assert not marker.exists()


def test_python_directory_cannot_escape_owned_root(tmp_path: Path) -> None:
    tool_root = tmp_path / "tool-root"
    tool_root.mkdir()
    outside = tmp_path / "ambient-python"
    outside.mkdir()
    (tool_root / "python").symlink_to(outside, target_is_directory=True)
    assert run_type_check(make_manifest(tmp_path), tool_root=tool_root) == 2


def test_malformed_identity_payload_is_a_tool_failure(tmp_path: Path) -> None:
    tool_root = make_tool_root(tmp_path)
    for payload in ([], {"prefix": 1, "mypy_file": None, "meta_version": "1.15.0"}):
        def runner(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, json.dumps(payload), "")
        assert run_type_check(make_manifest(tmp_path), tool_root=tool_root, runner=runner) == 2


def test_ambient_path_fake_is_never_executed(tmp_path: Path, monkeypatch) -> None:
    ambient_bin = tmp_path / "ambient_bin"
    ambient_bin.mkdir(parents=True)
    sentinel = tmp_path / "sentinel.txt"

    fake_mypy = ambient_bin / "mypy"
    fake_mypy.write_text(
        f"#!/bin/sh\necho 'EXECUTED' > '{sentinel}'\nexit 0\n",
        encoding="utf-8",
    )
    fake_mypy.chmod(0o755)

    monkeypatch.setenv("PATH", f"{ambient_bin}:{os.environ.get('PATH', '')}")
    manifest = make_manifest(tmp_path)

    # 1. Rootless invocation must fail closed without invoking ambient PATH fake
    code_rootless = run_type_check(manifest, tool_root=None)
    assert code_rootless == 2
    assert not sentinel.exists()

    # 2. Owned tool-root invocation must use isolated tool python, never ambient PATH fake
    tool_root = make_tool_root(tmp_path)
    expected_version = get_expected_mypy_version()
    runner = make_valid_probe_runner(tool_root, expected_version)

    code_owned = run_type_check(manifest, tool_root=tool_root, runner=runner)
    assert code_owned == 0
    assert not sentinel.exists()


def test_wrong_metadata_version_rejected(tmp_path: Path) -> None:
    tool_root = make_tool_root(tmp_path)
    manifest = make_manifest(tmp_path)
    python_dir = (tool_root / "python").resolve()

    def runner(cmd, **kwargs):
        command = list(cmd)
        if "-c" in command:
            payload = {
                "prefix": str(python_dir),
                "mypy_file": str(python_dir / "lib/python3.13/site-packages/mypy/__init__.py"),
                "meta_version": "1.14.0",  # wrong version
            }
            return subprocess.CompletedProcess(cmd, 0, json.dumps(payload), "")
        if "--version" in command:
            return subprocess.CompletedProcess(cmd, 0, "mypy 1.14.0", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    assert run_type_check(manifest, tool_root=tool_root, runner=runner) == 2


def test_wrong_cli_version_rejected(tmp_path: Path) -> None:
    tool_root = make_tool_root(tmp_path)
    manifest = make_manifest(tmp_path)
    python_dir = (tool_root / "python").resolve()
    expected_version = get_expected_mypy_version()

    def runner(cmd, **kwargs):
        command = list(cmd)
        if "-c" in command:
            payload = {
                "prefix": str(python_dir),
                "mypy_file": str(python_dir / "lib/python3.13/site-packages/mypy/__init__.py"),
                "meta_version": expected_version,
            }
            return subprocess.CompletedProcess(cmd, 0, json.dumps(payload), "")
        if "--version" in command:
            return subprocess.CompletedProcess(cmd, 0, "mypy 1.14.0", "")  # wrong CLI version
        return subprocess.CompletedProcess(cmd, 0, "", "")

    assert run_type_check(manifest, tool_root=tool_root, runner=runner) == 2


def test_wrong_sys_prefix_rejected(tmp_path: Path) -> None:
    tool_root = make_tool_root(tmp_path)
    manifest = make_manifest(tmp_path)
    python_dir = (tool_root / "python").resolve()
    expected_version = get_expected_mypy_version()

    def runner(cmd, **kwargs):
        command = list(cmd)
        if "-c" in command:
            payload = {
                "prefix": "/usr/local/outside_tool_root",
                "mypy_file": str(python_dir / "lib/python3.13/site-packages/mypy/__init__.py"),
                "meta_version": expected_version,
            }
            return subprocess.CompletedProcess(cmd, 0, json.dumps(payload), "")
        if "--version" in command:
            return subprocess.CompletedProcess(cmd, 0, f"mypy {expected_version}", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    assert run_type_check(manifest, tool_root=tool_root, runner=runner) == 2


def test_wrong_mypy_module_path_rejected(tmp_path: Path) -> None:
    tool_root = make_tool_root(tmp_path)
    manifest = make_manifest(tmp_path)
    python_dir = (tool_root / "python").resolve()
    expected_version = get_expected_mypy_version()

    def runner(cmd, **kwargs):
        command = list(cmd)
        if "-c" in command:
            payload = {
                "prefix": str(python_dir),
                "mypy_file": "/Library/Python/3.13/site-packages/mypy/__init__.py",
                "meta_version": expected_version,
            }
            return subprocess.CompletedProcess(cmd, 0, json.dumps(payload), "")
        if "--version" in command:
            return subprocess.CompletedProcess(cmd, 0, f"mypy {expected_version}", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    assert run_type_check(manifest, tool_root=tool_root, runner=runner) == 2


def test_correct_identity_returns_child_exit_success_and_failure(tmp_path: Path) -> None:
    tool_root = make_tool_root(tmp_path)
    manifest = make_manifest(tmp_path)
    expected_version = get_expected_mypy_version()
    python_dir = (tool_root / "python").resolve()

    # Success case: child exits 0
    def runner_success(cmd, **kwargs):
        command = list(cmd)
        if "-c" in command:
            payload = {
                "prefix": str(python_dir),
                "mypy_file": str(python_dir / "lib/mypy/__init__.py"),
                "meta_version": expected_version,
            }
            return subprocess.CompletedProcess(cmd, 0, json.dumps(payload), "")
        if "--version" in command:
            return subprocess.CompletedProcess(cmd, 0, f"mypy {expected_version}", "")
        return subprocess.CompletedProcess(cmd, 0, "Success: no issues found", "")

    assert run_type_check(manifest, tool_root=tool_root, runner=runner_success) == 0

    # Policy finding case: child exits 1
    def runner_finding(cmd, **kwargs):
        command = list(cmd)
        if "-c" in command:
            payload = {
                "prefix": str(python_dir),
                "mypy_file": str(python_dir / "lib/mypy/__init__.py"),
                "meta_version": expected_version,
            }
            return subprocess.CompletedProcess(cmd, 0, json.dumps(payload), "")
        if "--version" in command:
            return subprocess.CompletedProcess(cmd, 0, f"mypy {expected_version}", "")
        return subprocess.CompletedProcess(cmd, 1, "error: Incompatible return value type", "")

    assert run_type_check(manifest, tool_root=tool_root, runner=runner_finding) == 1


def test_pythonpath_shadow_package_ignored_by_real_isolated_subprocess(tmp_path: Path) -> None:
    """Prove with real python subprocess that -I ignores PYTHONPATH shadow package."""
    shadow_site = tmp_path / "shadow_site"
    shadow_pkg = shadow_site / "mypy"
    shadow_pkg.mkdir(parents=True)
    (shadow_pkg / "__init__.py").write_text(
        'SHADOW_MYPY_MARKER = "SHADOW_PACKAGE_LOADED"\n',
        encoding="utf-8",
    )

    env = dict(os.environ)
    env["PYTHONPATH"] = str(shadow_site)

    # 1. Non-isolated subprocess (-c without -I) sees the shadow package in sys.path
    res_non_isolated = subprocess.run(
        [sys.executable, "-c", "import sys; print(str(sys.path))"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert res_non_isolated.returncode == 0
    assert str(shadow_site) in res_non_isolated.stdout

    # 2. Isolated subprocess (-I) completely ignores PYTHONPATH
    res_isolated = subprocess.run(
        [sys.executable, "-I", "-c", "import sys; print(str(sys.path))"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert res_isolated.returncode == 0
    assert str(shadow_site) not in res_isolated.stdout

    # 3. Direct module import under -I does NOT load the shadow package marker
    res_probe = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            "try:\n    import mypy\n    print(getattr(mypy, 'SHADOW_MYPY_MARKER', 'clean'))\nexcept ImportError:\n    print('clean')",
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert res_probe.returncode == 0
    assert res_probe.stdout.strip() == "clean"
    assert "SHADOW_PACKAGE_LOADED" not in res_probe.stdout


def test_manifest_scope_and_targets_preserved(tmp_path: Path) -> None:
    tool_root = make_tool_root(tmp_path)
    custom_targets = ["src/agentic_praxis_grimoire", "libexec"]
    manifest = make_manifest(tmp_path, targets=custom_targets)
    expected_version = get_expected_mypy_version()
    python_dir = (tool_root / "python").resolve()
    executed_commands = []

    def runner(cmd, **kwargs):
        command = list(cmd)
        if "-c" in command or "--version" in command:
            if "-c" in command:
                payload = {
                    "prefix": str(python_dir),
                    "mypy_file": str(python_dir / "lib/mypy/__init__.py"),
                    "meta_version": expected_version,
                }
                return subprocess.CompletedProcess(cmd, 0, json.dumps(payload), "")
            return subprocess.CompletedProcess(cmd, 0, f"mypy {expected_version}", "")
        executed_commands.append(command)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    code = run_type_check(manifest, tool_root=tool_root, runner=runner)
    assert code == 0
    assert len(executed_commands) == 1
    child_cmd = executed_commands[0]

    # Verify isolated interpreter '-I -m mypy'
    assert child_cmd[1:4] == ["-I", "-m", "mypy"]
    # Verify exact target scope
    assert child_cmd[4:] == [str(ROOT / "src/agentic_praxis_grimoire"), str(ROOT / "libexec")]
