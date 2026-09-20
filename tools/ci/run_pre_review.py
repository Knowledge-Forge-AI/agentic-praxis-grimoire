#!/usr/bin/env python3
"""Run APGR's adapted pre-review static analysis suite and aggregate once."""

from __future__ import annotations

import argparse
from dataclasses import replace
import os
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.ci.pre_review_checks import (
    _attest_check_owner,
    _attest_python_owner,
    _command_attestation,
    _interpreter,
    checks,
)
from tools.ci.pre_review_evaluation import (
    evaluate,
)
from tools.ci.pre_review_evidence import (
    AGGREGATE_CAP_BYTES,
    bounded_log,
    finalize_evidence,
)
from tools.ci.pre_review_records import (
    SENSITIVE_SCANNERS,
    Check,
    Result,
    sanitize,
)


def execute_all(
    selected: tuple[Check, ...],
    evidence_dir: Path,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    scratch_dir: Path | None = None,
    tool_root: Path | None = None,
) -> tuple[Result, ...]:
    if scratch_dir is None:
        with tempfile.TemporaryDirectory(prefix="apgr-pre-review-run-") as raw:
            return execute_all(
                selected,
                evidence_dir,
                runner=runner,
                scratch_dir=Path(raw),
                tool_root=tool_root,
            )

    evidence_dir.mkdir(parents=True, exist_ok=True)
    scratch_dir.mkdir(parents=True, exist_ok=True)

    clean_env = dict(os.environ)
    for key in tuple(clean_env):
        if key.endswith("_API_KEY") or key in {"ANTHROPIC_API_KEY", "SEMGREP_APP_TOKEN"}:
            clean_env.pop(key)
    clean_env["PYTHONDONTWRITEBYTECODE"] = "1"
    clean_env["PYTHONPYCACHEPREFIX"] = str(scratch_dir / "pycache")
    clean_env["RUFF_CACHE_DIR"] = str(scratch_dir / "ruff-cache")
    clean_env["MYPY_CACHE_DIR"] = str(scratch_dir / "mypy-cache")

    if tool_root is not None:
        owned_paths = (
            tool_root / "bin",
            tool_root / "python" / "bin",
            tool_root / "node" / "node_modules" / ".bin",
            tool_root / "liquibase",
        )
        clean_env["PATH"] = os.pathsep.join(
            str(path) for path in owned_paths if path.exists()
        ) + os.pathsep + clean_env.get("PATH", "")

    results = []
    for check in selected:
        started = time.monotonic()
        interpreter = _interpreter(check)
        try:
            _attest_check_owner(check, tool_root)
            completed = runner(
                list(check.command),
                cwd=check.cwd,
                env=clean_env,
                check=False,
                capture_output=True,
                text=True,
                timeout=300,
            )
            status, detail, classification = evaluate(
                check,
                completed.returncode,
                completed.stdout,
                completed.stderr,
            )
            retained = (
                detail
                if check.name in SENSITIVE_SCANNERS
                else sanitize(
                    completed.stdout + completed.stderr,
                    scratch_dir,
                    *((tool_root,) if tool_root is not None else ()),
                )
            )
            returncode = completed.returncode
        except (OSError, RuntimeError, ValueError, TypeError, AttributeError, subprocess.TimeoutExpired) as error:
            status = "failed"
            detail = f"tool/bootstrap failure: {type(error).__name__}"
            classification = "tool-failure"
            returncode = None
            retained = detail

        header = (
            f"check={check.name}\n"
            f"interpreter={interpreter or 'none'}\n"
            f"command={_command_attestation(check, tool_root)}\n"
            f"classification={classification}\n"
        )
        (evidence_dir / f"{check.name}.log").write_text(
            bounded_log(sanitize(header + retained, scratch_dir, tool_root)),
            encoding="utf-8",
        )
        results.append(
            Result(
                check.name,
                status,
                returncode,
                time.monotonic() - started,
                detail,
                classification,
                interpreter,
            )
        )
    return tuple(results)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run APGR pre-review static analysis stack")
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--tool-root", type=Path, default=None)
    parser.add_argument("--check", type=str, default=None, help="Run only a specific named check")
    parser.add_argument("--public-projection", action="store_true",
                        help="Explicitly validate publication-excluded matrix rows through public traceability")
    args = parser.parse_args(argv)

    if args.tool_root:
        _attest_python_owner(args.tool_root)

    with tempfile.TemporaryDirectory(prefix="apgr-pre-review-scratch-") as raw:
        scratch_dir = Path(raw)
        all_checks = checks(scratch_dir, args.tool_root)
        if args.public_projection:
            all_checks = tuple(
                replace(check, command=(*check.command, "--mode", "public"))
                if check.name == "release-matrix" else check for check in all_checks
            )
        if args.check:
            selected = tuple(c for c in all_checks if c.name == args.check)
            if not selected:
                print(f"Unknown check {args.check!r}. Available: {[c.name for c in all_checks]}", file=sys.stderr)
                return 2
        else:
            selected = all_checks

        results = execute_all(
            selected,
            args.evidence_dir,
            scratch_dir=scratch_dir,
            tool_root=args.tool_root,
        )

        evidence_error = None
        evidence_headroom = None
        try:
            evidence_headroom = finalize_evidence(args.evidence_dir, selected, results)
        except (OSError, RuntimeError) as error:
            evidence_error = sanitize(str(error), scratch_dir, args.tool_root)

    # Print human-readable disposition table
    print("=" * 80)
    print(f"{'STATUS':<8} {'CHECK':<28} {'TIME':<8} {'CLASS':<16} {'DETAIL'}")
    print("-" * 80)
    for result in results:
        print(
            f"{result.status.upper():<8} {result.name:<28} "
            f"{result.elapsed_seconds:6.2f}s {result.classification:<16} {result.detail}"
        )
    print("=" * 80)

    passed_count = sum(1 for r in results if r.status == "passed")
    policy_findings = [r for r in results if r.classification == "policy-finding"]
    tool_failures = [r for r in results if r.classification == "tool-failure"]

    print(
        f"pre-review aggregate: {passed_count} passed, "
        f"{len(policy_findings)} policy findings, "
        f"{len(tool_failures)} tool failures (total {len(results)})"
    )

    if evidence_error is not None:
        print(f"FAILED evidence-finalization: {evidence_error}", file=sys.stderr)
    if evidence_headroom is not None:
        print(f"evidence headroom: {evidence_headroom} bytes (cap {AGGREGATE_CAP_BYTES})")

    if tool_failures:
        return 2
    if policy_findings or evidence_error is not None:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
