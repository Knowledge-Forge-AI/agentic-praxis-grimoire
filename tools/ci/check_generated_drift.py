#!/usr/bin/env python3
"""Use the maintained embedded-corpus verifier for generated resource drift."""
from __future__ import annotations
import argparse
import json
import subprocess
import tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]


def evaluate(root: Path, runner=subprocess.run) -> tuple[dict, int]:
    try:
        with tempfile.TemporaryDirectory(prefix="apgr-corpus-check-") as scratch:
            binary = str(Path(scratch) / "apgr")
            build = runner(["go", "build", "-o", binary, "./cmd/apgr"],
                           cwd=root, capture_output=True, text=True, check=False, timeout=240)
            if build.returncode:
                return {"classification": "tool-failure", "status": "failed", "stage": "build"}, 2
            result = runner(
                [binary, "skills", "verify-corpus", "--repository", str(root)],
                cwd=root, capture_output=True, text=True, check=False, timeout=240,
            )
    except (OSError, subprocess.SubprocessError):
        return {"classification": "tool-failure", "status": "failed"}, 2
    # The maintained verifier compares exact metadata bytes and every body
    # digest against compiled resources; cardinality is not sufficient.
    code = 0 if result.returncode == 0 else 1
    return {
        "schema": "apg-generated-corpus-drift-v1",
        "owner": "apgr skills verify-corpus",
        "classification": "passed" if code == 0 else "policy-finding",
        "status": "passed" if code == 0 else "failed",
        "returncode": result.returncode,
    }, code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path)
    args = parser.parse_args(argv)
    report, code = evaluate(ROOT)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.evidence_dir:
        args.evidence_dir.mkdir(parents=True, exist_ok=True)
        (args.evidence_dir / "generated_drift_report.json").write_text(text, encoding="utf-8")
    print(text, end="")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
