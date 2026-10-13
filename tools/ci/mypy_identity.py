#!/usr/bin/env python3
"""Shared verification helper and execution binding for pinned APGR mypy."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.ci.dependency_inventory import CI_REQUIREMENTS

ROOT = Path(__file__).resolve().parents[2]

PROBE_CODE = """import importlib.metadata, json, pathlib, sys
mypy_file = ''
try:
    import mypy
    mypy_file = str(pathlib.Path(mypy.__file__).resolve())
except ImportError:
    pass
meta_ver = ''
try:
    meta_ver = importlib.metadata.version('mypy')
except importlib.metadata.PackageNotFoundError:
    pass
print(json.dumps({'prefix': str(pathlib.Path(sys.prefix).resolve()),
                  'mypy_file': mypy_file, 'meta_version': meta_ver}))
"""


class MypyIdentityError(RuntimeError):
    """Raised when mypy tool-root binding or identity verification fails."""


def get_expected_mypy_version() -> str:
    """Extract expected mypy pin from CI_REQUIREMENTS."""
    for req in CI_REQUIREMENTS:
        if req.startswith("mypy=="):
            return req.split("==", 1)[1]
    raise MypyIdentityError("mypy version pin not found in CI_REQUIREMENTS")


def verify_mypy_identity(
    tool_root: Path | str | None,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> Path:
    """Verify that mypy inside <tool-root>/python satisfies explicit owned identity.

    Fails closed (raising MypyIdentityError) if tool-root is absent, unreadable,
    points to wrong prefix, imports mypy from outside <tool-root>/python, or
    disagrees with CI_REQUIREMENTS version pin across metadata and CLI.
    """
    if tool_root is None or not str(tool_root).strip():
        raise MypyIdentityError("missing tool-root: explicit owned disposable tool-root binding required")

    tool_root_path = Path(tool_root).resolve(strict=False)
    if not tool_root_path.is_dir():
        raise MypyIdentityError(f"tool-root directory does not exist: {tool_root_path}")

    tool_python_dir = (tool_root_path / "python").resolve(strict=False)
    if not tool_python_dir.is_relative_to(tool_root_path):
        raise MypyIdentityError("tool-root python directory escapes the owned tool root")
    if not tool_python_dir.is_dir():
        raise MypyIdentityError(f"tool-root python directory does not exist: {tool_python_dir}")

    python_bin = tool_python_dir / "bin" / "python"
    if not python_bin.is_file():
        python_bin = tool_python_dir / "bin" / "python3"
    if not python_bin.is_file() or not os.access(python_bin, os.X_OK):
        raise MypyIdentityError(f"tool-root python executable missing or not executable: {python_bin}")

    expected_version = get_expected_mypy_version()

    # Probe 1: Isolated interpreter probe checking sys.prefix, module path, and metadata version
    probe_cmd = [str(python_bin), "-I", "-c", PROBE_CODE]
    try:
        probe_res = runner(probe_cmd, capture_output=True, text=True, check=False, timeout=30)
    except (OSError, subprocess.SubprocessError) as error:
        raise MypyIdentityError(f"failed to execute mypy identity probe: {error}") from error

    if probe_res.returncode != 0:
        err_msg = probe_res.stderr.strip() or f"exit code {probe_res.returncode}"
        raise MypyIdentityError(f"mypy identity probe failed: {err_msg}")

    try:
        data = json.loads(probe_res.stdout)
        if not isinstance(data, dict) or any(
            not isinstance(data.get(key), str)
            for key in ("prefix", "mypy_file", "meta_version")
        ):
            raise ValueError("identity probe fields must be strings in an object")
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        raise MypyIdentityError(f"mypy identity probe returned malformed JSON: {error}") from error

    resolved_tool_python = tool_python_dir.resolve(strict=True)

    # Verify resolved sys.prefix is inside <tool-root>/python
    raw_prefix = data.get("prefix", "")
    if not raw_prefix:
        raise MypyIdentityError("mypy identity probe returned empty sys.prefix")
    resolved_prefix = Path(raw_prefix).resolve(strict=False)
    if not (resolved_prefix == resolved_tool_python or resolved_tool_python in resolved_prefix.parents):
        raise MypyIdentityError(
            f"resolved sys.prefix {resolved_prefix} is not inside resolved <tool-root>/python {resolved_tool_python}"
        )

    # Verify resolved mypy module path is inside <tool-root>/python
    raw_mypy_file = data.get("mypy_file", "")
    if not raw_mypy_file:
        raise MypyIdentityError("mypy module could not be imported in tool-root python")
    resolved_mypy = Path(raw_mypy_file).resolve(strict=False)
    if not (resolved_mypy == resolved_tool_python or resolved_tool_python in resolved_mypy.parents):
        raise MypyIdentityError(
            f"resolved mypy module path {resolved_mypy} is not inside resolved <tool-root>/python {resolved_tool_python}"
        )

    # Verify metadata version agrees with CI_REQUIREMENTS
    meta_version = data.get("meta_version", "")
    if meta_version != expected_version:
        raise MypyIdentityError(
            f"mypy metadata version {meta_version!r} does not agree with CI_REQUIREMENTS pin {expected_version!r}"
        )

    # Probe 2: CLI version check via isolated interpreter '-I -m mypy --version'
    cli_cmd = [str(python_bin), "-I", "-m", "mypy", "--version"]
    try:
        cli_res = runner(cli_cmd, capture_output=True, text=True, check=False, timeout=30)
    except (OSError, subprocess.SubprocessError) as error:
        raise MypyIdentityError(f"failed to execute mypy CLI version check: {error}") from error

    if cli_res.returncode != 0:
        err_msg = cli_res.stderr.strip() or f"exit code {cli_res.returncode}"
        raise MypyIdentityError(f"mypy CLI version check failed: {err_msg}")

    cli_output = cli_res.stdout.strip()
    parts = cli_output.split()
    if len(parts) < 2 or parts[0] != "mypy" or parts[1] != expected_version:
        raise MypyIdentityError(
            f"mypy CLI version {cli_output!r} does not agree with CI_REQUIREMENTS pin {expected_version!r}"
        )

    print(
        f"mypy identity verified: version={expected_version}; interpreter={python_bin}; "
        f"prefix={resolved_prefix}; module={resolved_mypy}",
        file=sys.stderr,
    )
    return python_bin


def resolve_mypy_command(
    tool_root: Path | str | None,
    targets: list[str] | tuple[str, ...],
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> list[str]:
    """Verify tool identity and construct isolated mypy execution command."""
    python_bin = verify_mypy_identity(tool_root, runner=runner)
    return [str(python_bin), "-I", "-m", "mypy", *targets]
