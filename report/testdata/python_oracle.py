#!/usr/bin/env python3
"""Test-only direct entry to the frozen APG95 Python report oracle."""

from __future__ import annotations

import os
from pathlib import Path
import sys


def main(arguments: list[str]) -> int:
    root = os.environ.get("APG_TEST_PYTHON_ORACLE_ROOT")
    if not root or not Path(root).is_absolute() or not (Path(root) / "agent_report" / "cli.py").is_file():
        print("python-oracle: optional historical oracle is unavailable", file=sys.stderr)
        return 2
    sys.path.insert(0, root)
    from agent_report.cli import append_operational_main, git_diff_main, git_show_main

    owners = {
        "git-show-report": git_show_main,
        "git-diff-report": git_diff_main,
        "append-operational-report": append_operational_main,
    }
    if not arguments or arguments[0] not in owners:
        print("python-oracle: exact report command is required", file=sys.stderr)
        return 2
    return owners[arguments[0]](arguments[1:])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
