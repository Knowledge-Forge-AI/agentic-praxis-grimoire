#!/usr/bin/env python3
"""Type checking runner for APGR Python modules."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run_type_check(manifest_path: Path) -> int:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        targets = [str(ROOT / t) for t in manifest.get("targets", ["src/agentic_praxis_grimoire"])]
    except (OSError, TypeError, ValueError, UnicodeError) as error:
        print(f"python_type_check: invalid manifest: {error}", file=sys.stderr)
        return 2

    # Check if mypy executable or module exists
    mypy_bin = shutil.which("mypy")
    if mypy_bin is not None:
        cmd = [mypy_bin, *targets]
    else:
        # Try python -m mypy
        cmd = [sys.executable, "-m", "mypy", *targets]

    try:
        res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
        sys.stdout.write(res.stdout)
        sys.stderr.write(res.stderr)
        return res.returncode
    except FileNotFoundError:
        print("mypy: command not found", file=sys.stderr)
        return 2
    except (OSError, subprocess.SubprocessError, UnicodeError) as error:
        print(f"mypy: execution error: {error}", file=sys.stderr)
        return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path(__file__).with_name("python_type_ownership.json"))
    args = parser.parse_args(argv)
    return run_type_check(args.manifest)


if __name__ == "__main__":
    raise SystemExit(main())
