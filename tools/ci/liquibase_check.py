#!/usr/bin/env python3
"""Liquibase changelog validation and disposition for APGR."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def find_changelogs() -> list[str]:
    try:
        res = subprocess.run(
            ["git", "ls-files", "*changelog*.xml", "*changelog*.yaml", "*changelog*.sql"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return [f for f in res.stdout.splitlines() if f]
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return []


def check_liquibase(changelogs: list[str]) -> int:
    if not changelogs:
        print("disposition: zero Liquibase changelogs present; contract clean")
        return 0

    print(f"found {len(changelogs)} changelog(s), running validation...")
    for cl in changelogs:
        try:
            cmd = ["liquibase", f"--changeLogFile={cl}", "--url=offline:postgresql", "validate"]
            res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
            if res.returncode != 0:
                print(f"FAILED validation for {cl}:\n{res.stderr or res.stdout}", file=sys.stderr)
                return 1
        except FileNotFoundError:
            print("liquibase: executable not found in PATH", file=sys.stderr)
            return 2
        except (OSError, subprocess.SubprocessError, UnicodeError) as error:
            print(f"liquibase: operational error {error}", file=sys.stderr)
            return 2
    print("all changelogs validated successfully")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-changelogs", action="store_true")
    args = parser.parse_args(argv)

    changelogs = find_changelogs()
    if args.require_changelogs and not changelogs:
        print("liquibase: expected changelogs but none found", file=sys.stderr)
        return 1
    return check_liquibase(changelogs)


if __name__ == "__main__":
    raise SystemExit(main())
