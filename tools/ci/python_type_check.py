#!/usr/bin/env python3
"""Type checking runner for APGR Python modules."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.ci.mypy_identity import MypyIdentityError, resolve_mypy_command

ROOT = Path(__file__).resolve().parents[2]


def run_type_check(
    manifest_path: Path,
    tool_root: Path | None = None,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> int:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        targets = [str(ROOT / t) for t in manifest.get("targets", ["src/agentic_praxis_grimoire"])]
    except (OSError, TypeError, ValueError, UnicodeError) as error:
        print(f"python_type_check: invalid manifest: {error}", file=sys.stderr)
        return 2

    try:
        cmd = resolve_mypy_command(tool_root, targets, runner=runner)
    except MypyIdentityError as error:
        print(f"python_type_check: identity failure: {error}", file=sys.stderr)
        return 2

    try:
        res = runner(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
        sys.stdout.write(res.stdout)
        sys.stderr.write(res.stderr)
        return res.returncode
    except (OSError, subprocess.SubprocessError, UnicodeError) as error:
        print(f"mypy: execution error: {error}", file=sys.stderr)
        return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Type checking runner for APGR Python modules")
    parser.add_argument("--manifest", type=Path, default=Path(__file__).with_name("python_type_ownership.json"))
    parser.add_argument("--tool-root", type=Path, default=None)
    args = parser.parse_args(argv)
    return run_type_check(args.manifest, tool_root=args.tool_root)


if __name__ == "__main__":
    raise SystemExit(main())
