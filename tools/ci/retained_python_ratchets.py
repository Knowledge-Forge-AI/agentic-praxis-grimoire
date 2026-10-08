#!/usr/bin/env python3
"""Enforce exact retained package ownership and zero quality allowances."""
from __future__ import annotations

import argparse
from collections.abc import Callable
import json
from pathlib import Path
import subprocess
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.ci.mypy_identity import MypyIdentityError, resolve_mypy_command

ROOT = Path(__file__).resolve().parents[2]


def evaluate_ratchets(
    baseline_path: Path,
    *,
    root: Path = ROOT,
    tool_root: Path | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> tuple[dict, int]:
    report = {"schema": "apg-retained-python-ratchets-result-v1", "checks": {}}
    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        paths = baseline["paths"]
        if (
            baseline["schema"] != "apg-retained-python-ratchets-v1"
            or not isinstance(paths, list)
            or not paths
            or len(paths) != len(set(paths))
            or baseline["quality"] != {"ruff_f": 0, "mypy": 0}
        ):
            raise ValueError("invalid ratchet contract")
        observed = sorted(
            str(p.relative_to(root))
            for p in (root / "src/agentic_praxis_grimoire").rglob("*.py")
        )
        if sorted(paths) != observed:
            report.update(
                status="failed",
                classification="policy-finding",
                detail="retained Python owner inventory changed",
            )
            return report, 1

        codes = []
        # Ruff F checks
        ruff_cmd = [sys.executable, "-m", "ruff", "check", "--select", "F", *paths]
        ruff_res = runner(ruff_cmd, cwd=root, capture_output=True, text=True, check=False, timeout=240)
        ruff_code = ruff_res.returncode if ruff_res.returncode in (0, 1) else 2
        if "No module named" in ruff_res.stderr:
            ruff_code = 2
        codes.append(ruff_code)
        report["checks"]["ruff_f"] = {
            "returncode": ruff_res.returncode,
            "classification": ("passed", "policy-finding", "tool-failure")[ruff_code],
        }

        # Pinned isolated mypy check
        try:
            mypy_cmd = resolve_mypy_command(tool_root, ["src/agentic_praxis_grimoire"], runner=runner)
            mypy_res = runner(mypy_cmd, cwd=root, capture_output=True, text=True, check=False, timeout=240)
            mypy_code = mypy_res.returncode if mypy_res.returncode in (0, 1) else 2
            if "No module named" in mypy_res.stderr:
                mypy_code = 2
            codes.append(mypy_code)
            report["checks"]["mypy"] = {
                "returncode": mypy_res.returncode,
                "classification": ("passed", "policy-finding", "tool-failure")[mypy_code],
            }
        except MypyIdentityError as error:
            report["checks"]["mypy"] = {
                "returncode": 2,
                "classification": "tool-failure",
                "detail": str(error),
            }
            codes.append(2)

        code = max(codes)
        report.update(
            status="passed" if code == 0 else "failed",
            classification=("passed", "policy-finding", "tool-failure")[code],
            detail="quality tools retain their findings; no debt waiver is applied",
        )
        return report, code
    except (KeyError, TypeError, ValueError, OSError, subprocess.SubprocessError):
        report.update(
            status="failed",
            classification="tool-failure",
            detail="invalid inventory or checker execution failure",
        )
        return report, 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, default=Path(__file__).with_suffix(".json"))
    parser.add_argument("--tool-root", type=Path, default=None)
    args = parser.parse_args(argv)
    report, code = evaluate_ratchets(args.baseline, tool_root=args.tool_root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
