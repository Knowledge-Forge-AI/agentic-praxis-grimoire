#!/usr/bin/env python3
"""Retention inventory census and cohort verification for APGR Python modules."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

if __package__ in (None, "") and str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.ci.python_inventory import (  # noqa: E402
    PythonInventoryOperationalError,
    discover_python_inventory,
)


def collect_inventory(
    repo_root: Path = ROOT,
    *,
    include_untracked: bool = False,
) -> dict:
    try:
        inventory = discover_python_inventory(
            repo_root,
            include_untracked=include_untracked,
        )
    except PythonInventoryOperationalError as error:
        raise ValueError(str(error)) from error

    modules = [
        {
            "path": entry.path,
            "lines": entry.line_count,
            "syntax_owner": entry.syntax_owner,
            "lint_owner": entry.lint_owner,
            "type_owner": entry.type_owner,
            "role": entry.role,
        }
        for entry in inventory.entries
    ]

    return {
        "schema": "apg-python-retention-inventory-v1",
        "status": "passed",
        "classification": "passed",
        "enforcement_scope": "syntax and Ruff census; package-only mypy; checker findings are separate",
        "detail": f"retention census complete: files={inventory.total_files}, lines={inventory.total_lines}",
        "counts": {
            "total_files": inventory.total_files,
            "total_lines": inventory.total_lines,
            "excluded": inventory.excluded_counts,
        },
        "modules": modules,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="APGR retention inventory census and cohort verification."
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true", default=True)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--include-untracked", action="store_true", default=False)
    args = parser.parse_args(argv)

    try:
        inv = collect_inventory(
            args.repo_root,
            include_untracked=args.include_untracked,
        )
    except (ValueError, OSError) as error:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "classification": "tool-failure",
                    "detail": str(error),
                }
            )
        )
        return 2
    if args.json:
        print(json.dumps(inv, indent=2, sort_keys=True))
    else:
        print(inv["detail"])
    return 0 if inv["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
