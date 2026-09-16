#!/usr/bin/env python3
"""Enforce exact retained package ownership and zero quality allowances."""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]


def evaluate_ratchets(baseline_path: Path, *, root: Path = ROOT,
                      runner=subprocess.run) -> tuple[dict, int]:
    report = {"schema": "apg-retained-python-ratchets-result-v1", "checks": {}}
    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        paths = baseline["paths"]
        if (baseline["schema"] != "apg-retained-python-ratchets-v1"
                or not isinstance(paths, list) or not paths
                or len(paths) != len(set(paths))
                or baseline["quality"] != {"ruff_f": 0, "mypy": 0}):
            raise ValueError("invalid ratchet contract")
        observed = sorted(str(p.relative_to(root)) for p in
                          (root / "src/agentic_praxis_grimoire").rglob("*.py"))
        if sorted(paths) != observed:
            report.update(status="failed", classification="policy-finding",
                          detail="retained Python owner inventory changed")
            return report, 1
        codes = []
        for name, command in (
            ("ruff_f", [sys.executable, "-m", "ruff", "check", "--select", "F", *paths]),
            ("mypy", [sys.executable, "-m", "mypy", "src/agentic_praxis_grimoire"]),
        ):
            result = runner(command, cwd=root, capture_output=True, text=True,
                            check=False, timeout=240)
            code = result.returncode if result.returncode in (0, 1) else 2
            if "No module named" in result.stderr:
                code = 2
            codes.append(code)
            report["checks"][name] = {
                "returncode": result.returncode,
                "classification": ("passed", "policy-finding", "tool-failure")[code],
            }
        code = max(codes)
        report.update(status="passed" if code == 0 else "failed",
                      classification=("passed", "policy-finding", "tool-failure")[code],
                      detail="quality tools retain their findings; no debt waiver is applied")
        return report, code
    except (KeyError, TypeError, ValueError, OSError, subprocess.SubprocessError):
        report.update(status="failed", classification="tool-failure",
                      detail="invalid inventory or checker execution failure")
        return report, 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, default=Path(__file__).with_suffix(".json"))
    args = parser.parse_args(argv)
    report, code = evaluate_ratchets(args.baseline)
    print(json.dumps(report, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
