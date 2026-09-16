#!/usr/bin/env python3
"""Mechanical release readiness regression matrix validator.

Enforces Scope Section Q and Finding 19:
- Complete coverage of REG-R1..R13
- Complete coverage of REG-P1..P13
- Complete F1..F12 traceability
- Physical existence on disk of all referenced owning_code and test_path files
- Non-empty, executable test_command entrypoints
- Rejection of duplicate IDs or orphan rows
- Explicit deterministic fail-closed public projection mode (APG155)
- Explicit row dispositions for public and private-only rows (no silent missing skip)
- Verification of public traceability and rejection of private publication in public mode
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = REPO_ROOT / "testing/release/release-readiness-matrix.json"

EXPECTED_REG_R = [f"REG-R{i}" for i in range(1, 14)]
EXPECTED_REG_P = [f"REG-P{i}" for i in range(1, 14)]
EXPECTED_F = [f"F{i}" for i in range(1, 13)]

VALID_DISPOSITIONS = frozenset({"public", "private_only"})
PRIVATE_DISPOSITIONS = frozenset({"private_only"})
VALID_MODES = frozenset({"private", "public", "public-projection"})

REQUIRED_ROW_FIELDS = [
    "regression_id",
    "historical_source",
    "requirement",
    "owning_code",
    "test_command",
    "test_path",
    "status",
    "classification",
    "fixture",
    "disposition",
    "public_evidence",
]


def validate_matrix(
    matrix_path: Path,
    repo_root: Path,
    mode: str = "private",
) -> dict[str, Any]:
    """Validate release readiness matrix integrity, disk references, and projection contract.

    Modes:
    - 'private': Strict validation of full repository. All referenced owning_code
      and test_path files must physically exist on disk, fixtures must match,
      and all row dispositions must be explicit and valid.
    - 'public' (or 'public-projection'): Deterministic fail-closed validation of public
      projection. Validates public rows and public traceability. Enforces explicit
      dispositions on private-only rows (no silent missing skip) and guarantees no
      private publication.
    """
    if mode not in VALID_MODES:
        return {
            "errors": [f"Invalid mode: {mode}. Expected 'private' or 'public'"],
            "status": "failed",
        }
    is_public_mode = mode in {"public", "public-projection"}

    errors: list[str] = []
    if not matrix_path.is_file():
        return {"errors": [f"Matrix file not found: {matrix_path}"], "status": "failed"}

    try:
        data = json.loads(matrix_path.read_text(encoding="utf-8"))
    except Exception as err:
        return {"errors": [f"Matrix JSON is malformed: {err}"], "status": "failed"}

    if data.get("schema_version") != 1:
        errors.append(f"Invalid schema_version: expected 1, got {data.get('schema_version')}")

    dispositions: dict[str, str] = {}
    public_count = 0
    private_only_count = 0

    # 1. Validate REG-R cases
    reg_r_list = data.get("reg_r_cases", [])
    observed_r_ids: list[str] = []
    reg_r_private_count = 0
    reg_r_public_count = 0
    for row in reg_r_list:
        rid = row.get("regression_id")
        observed_r_ids.append(rid)
        disp = _validate_row(row, repo_root, errors, context=f"REG-R row {rid}", is_public_mode=is_public_mode)
        if rid:
            dispositions[rid] = disp or "unknown"
            if disp in PRIVATE_DISPOSITIONS:
                reg_r_private_count += 1
                private_only_count += 1
            elif disp == "public":
                reg_r_public_count += 1
                public_count += 1

    missing_r = set(EXPECTED_REG_R) - set(observed_r_ids)
    extra_r = set(observed_r_ids) - set(EXPECTED_REG_R)
    if missing_r:
        errors.append(f"Missing REG-R cases: {sorted(missing_r)}")
    if extra_r:
        errors.append(f"Unexpected extra REG-R cases: {sorted(extra_r)}")
    if len(observed_r_ids) != len(set(observed_r_ids)):
        errors.append("Duplicate regression IDs observed in reg_r_cases")

    # 2. Validate REG-P cases
    reg_p_list = data.get("reg_p_cases", [])
    observed_p_ids: list[str] = []
    reg_p_private_count = 0
    reg_p_public_count = 0
    for row in reg_p_list:
        pid = row.get("regression_id")
        observed_p_ids.append(pid)
        disp = _validate_row(row, repo_root, errors, context=f"REG-P row {pid}", is_public_mode=is_public_mode)
        if pid:
            dispositions[pid] = disp or "unknown"
            if disp in PRIVATE_DISPOSITIONS:
                reg_p_private_count += 1
                private_only_count += 1
            elif disp == "public":
                reg_p_public_count += 1
                public_count += 1

    missing_p = set(EXPECTED_REG_P) - set(observed_p_ids)
    extra_p = set(observed_p_ids) - set(EXPECTED_REG_P)
    if missing_p:
        errors.append(f"Missing REG-P cases: {sorted(missing_p)}")
    if extra_p:
        errors.append(f"Unexpected extra REG-P cases: {sorted(extra_p)}")
    if len(observed_p_ids) != len(set(observed_p_ids)):
        errors.append("Duplicate regression IDs observed in reg_p_cases")

    # 3. Validate F1..F12 traceability
    f_list = data.get("f_traceability", [])
    observed_f_ids: list[str] = []
    all_known_reg_ids = set(observed_r_ids) | set(observed_p_ids)
    for row in f_list:
        fid = row.get("historical_source")
        observed_f_ids.append(fid)
        mapped = row.get("mapped_regression_ids", [])
        if not mapped or not isinstance(mapped, list):
            errors.append(f"F-traceability {fid} has missing or invalid mapped_regression_ids")
        for m in mapped:
            if m not in EXPECTED_REG_P and m not in EXPECTED_REG_R:
                errors.append(f"F-traceability {fid} references unknown regression ID: {m}")
            elif m not in all_known_reg_ids:
                errors.append(f"F-traceability {fid} references unmapped regression ID: {m}")
            elif is_public_mode:
                m_disp = dispositions.get(m)
                if not m_disp or m_disp not in VALID_DISPOSITIONS:
                    errors.append(
                        f"F-traceability {fid} maps to regression ID {m} without valid disposition"
                    )

    missing_f = set(EXPECTED_F) - set(observed_f_ids)
    extra_f = set(observed_f_ids) - set(EXPECTED_F)
    if missing_f:
        errors.append(f"Missing historical F cases: {sorted(missing_f)}")
    if extra_f:
        errors.append(f"Unexpected extra F cases: {sorted(extra_f)}")
    if len(observed_f_ids) != len(set(observed_f_ids)):
        errors.append("Duplicate historical F IDs observed in f_traceability")

    summary = {
        "f_count": len(observed_f_ids),
        "reg_p_count": len(observed_p_ids),
        "reg_r_count": len(observed_r_ids),
        "total_rules": len(observed_r_ids) + len(observed_p_ids) + len(observed_f_ids),
        "mode": "public" if is_public_mode else "private",
        "public_count": public_count,
        "private_only_count": private_only_count,
        "reg_r_private_count": reg_r_private_count,
        "reg_r_public_count": reg_r_public_count,
        "reg_p_private_count": reg_p_private_count,
        "reg_p_public_count": reg_p_public_count,
        "dispositions": dispositions,
    }

    return {
        "errors": errors,
        "status": "passed" if not errors else "failed",
        "summary": summary,
    }


def _validate_row(
    row: dict[str, Any],
    repo_root: Path,
    errors: list[str],
    context: str,
    *,
    is_public_mode: bool,
) -> str | None:
    for rf in REQUIRED_ROW_FIELDS:
        val = row.get(rf)
        if val is None or (isinstance(val, str) and not val.strip()):
            errors.append(f"{context} missing required field: {rf}")

    disposition = row.get("disposition")
    if disposition and disposition not in VALID_DISPOSITIONS:
        errors.append(
            f"{context} invalid disposition: '{disposition}'. Must be one of: {sorted(VALID_DISPOSITIONS)}"
        )

    evidence = row.get("public_evidence", "")
    expected_anchor = str(row.get("regression_id", "")).lower()
    if not isinstance(evidence, str) or evidence != f"testing/release/public-projection-contract.md#{expected_anchor}":
        errors.append(f"{context} invalid public evidence binding")
    else:
        evidence_path = repo_root / evidence.split("#")[0]
        if not evidence_path.is_file() or f"## {row.get('regression_id')}\n" not in evidence_path.read_text(encoding="utf-8"):
            errors.append(f"{context} missing public evidence section")

    owning_code = str(row.get("owning_code", "") or "")
    test_path = str(row.get("test_path", "") or "")
    test_command = str(row.get("test_command", "") or "")
    is_private_row = disposition in PRIVATE_DISPOSITIONS
    is_public_row = disposition == "public"

    # Enforce no private publication for public rows
    if is_public_mode and is_public_row:
        for field_name, val in [("owning_code", owning_code), ("test_path", test_path), ("test_command", test_command)]:
            if "private/" in val or val.startswith("private"):
                errors.append(f"{context} public row references private path in {field_name}: {val}")

    if not is_public_mode:
        # Full private mode: strict verification of all disk paths
        _validate_path_on_disk(owning_code, repo_root, errors, f"{context} owning_code")
        _validate_test_path_and_fixtures(test_path, row.get("fixture"), repo_root, errors, context)
        _validate_command_entrypoint(test_command, repo_root, errors, context)
    else:
        # Public projection mode:
        # - Public rows must strictly exist on disk
        # - Private-only rows require explicit disposition; public owning files must exist on disk,
        #   while private-excluded paths under private/ are not required on disk.
        # - Missing files without explicit private disposition fail-closed (no silent missing skip).
        if is_public_row:
            _validate_path_on_disk(owning_code, repo_root, errors, f"{context} owning_code")
            _validate_test_path_and_fixtures(test_path, row.get("fixture"), repo_root, errors, context)
            _validate_command_entrypoint(test_command, repo_root, errors, context)
        elif is_private_row:
            if owning_code and not owning_code.startswith("private/") and owning_code != "private":
                _validate_path_on_disk(owning_code, repo_root, errors, f"{context} owning_code")
            if test_path and not test_path.startswith("private/") and test_path != "private":
                _validate_test_path_and_fixtures(test_path, row.get("fixture"), repo_root, errors, context)
                _validate_command_entrypoint(test_command, repo_root, errors, context)
        else:
            errors.append(f"{context} unhandled row without valid disposition")

    return disposition if isinstance(disposition, str) else None


def _validate_path_on_disk(rel_path: str, repo_root: Path, errors: list[str], desc: str) -> None:
    if not rel_path:
        return
    path = repo_root / rel_path
    if not path.exists():
        errors.append(f"{desc} does not exist: {rel_path}")


def _validate_test_path_and_fixtures(
    test_path: str,
    fixture_spec: Any,
    repo_root: Path,
    errors: list[str],
    context: str,
) -> None:
    if not test_path:
        return
    path = repo_root / test_path
    if not path.exists():
        errors.append(f"{context} test_path does not exist: {test_path}")
        return
    if test_path.endswith(".py") and fixture_spec:
        try:
            content = path.read_text(encoding="utf-8")
            fixtures = [f.strip() for f in str(fixture_spec).split(",") if f.strip()]
            for fn in fixtures:
                if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", fn):
                    if not re.search(rf"\bdef\s+{re.escape(fn)}\b", content):
                        errors.append(
                            f"{context} fixture function '{fn}' not found in {test_path}"
                        )
        except Exception as err:
            errors.append(f"{context} error reading test_path {test_path}: {err}")


def _validate_command_entrypoint(cmd: str, repo_root: Path, errors: list[str], context: str) -> None:
    if not cmd.strip():
        errors.append(f"{context} test_command is empty")
        return
    parts = cmd.split()
    cmd_entry = None
    for part in parts:
        if "=" in part and not part.startswith("/"):
            continue
        cmd_entry = part
        break
    if cmd_entry and "/" in cmd_entry and not cmd_entry.startswith("/"):
        if not (repo_root / cmd_entry).exists() and not any(cmd_entry.startswith(k) for k in ("PYTHONPATH=", "GOWORK=")):
            errors.append(f"{context} test_command entrypoint not found: {cmd_entry}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mechanical release readiness regression matrix validator.")
    parser.add_argument(
        "--mode",
        choices=["private", "public", "public-projection"],
        default="private",
        help="Validation mode: 'private' (strict local checks) or 'public' (public projection contract).",
    )
    parser.add_argument(
        "--public",
        action="store_true",
        help="Alias for --mode public.",
    )
    parser.add_argument(
        "--matrix-path",
        type=Path,
        default=MATRIX_PATH,
        help="Path to release-readiness-matrix.json.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="Path to repository root.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    mode = "public" if args.public or args.mode in {"public", "public-projection"} else args.mode

    result = validate_matrix(args.matrix_path, args.repo_root, mode=mode)
    if result["status"] == "passed":
        summary = result["summary"]
        if mode == "public":
            print(f"PASS: Release readiness matrix valid (public projection mode: {summary['total_rules']} rows checked)")
            print(f"  REG-R: {summary['reg_r_count']}/13 ({summary['reg_r_private_count']} private-only disposition)")
            print(f"  REG-P: {summary['reg_p_count']}/13 ({summary['reg_p_private_count']} private-only disposition)")
            print(f"  F-Traceability: {summary['f_count']}/12")
        else:
            print(f"PASS: Release readiness matrix valid ({summary['total_rules']} rows checked)")
            print(f"  REG-R: {summary['reg_r_count']}/13")
            print(f"  REG-P: {summary['reg_p_count']}/13")
            print(f"  F-Traceability: {summary['f_count']}/12")
        return 0

    print("FAIL: Release readiness matrix validation failed:", file=sys.stderr)
    for err in result["errors"]:
        print(f"  - {err}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
