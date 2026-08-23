"""Mechanical and compiler-backed contract for the APG75 TypeScript fixture."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, NoReturn


ROLE_TOKENS = {
    "cli-checker",
    "declaration-emitter",
    "programmatic-compiler-api",
    "editor-language-service",
    "embedded-language-checker",
    "source-transformer-type-stripper",
    "build-orchestrator",
    "runtime-host",
}
SELECTION_TOKENS = {"selected", "embedded-route", "route-to-owner", "non-trigger"}
IDENTITY_STATES = {"known", "not-required", "unresolved"}
PRODUCT_STATES = {"current", "intended", "temporary"}
INVOCATION_STATES = {"invoked", "not-invoked", "unknown"}
CASE_KEYS = {
    "artifact_class",
    "compiler_roles",
    "expected_boundary",
    "id",
    "intended_product_state",
    "live_target_state",
    "option_facts",
    "paths",
    "present_evidence",
    "purpose",
    "required_evidence",
    "retirement_condition",
    "role_identity_state",
    "source_kind",
    "temporary_compatibility",
    "typescript_decision_scope",
    "typescript_selection",
    "whole_file_owner",
}
ROLE_KEYS = {
    "exact_version",
    "invocation_evidence",
    "invocation_state",
    "package",
    "product_state",
    "retirement_condition",
    "role",
    "selection_source",
}
EXPECTED_CASE_PATHS = {
    "APG74-FX-001": ("src/core/inventory.ts", "tsconfig.json"),
    "APG74-FX-002": ("src/modules/loader.mts",),
    "APG74-FX-003": ("src/modules/legacy.cts",),
    "APG74-FX-004": ("src/declarations/host-metrics.d.ts",),
    "APG74-FX-005": ("tsconfig.declarations.json", "src/core/inventory.ts"),
    "APG74-FX-006": ("src/ui/badge.tsx", "src/ui/jsx-host.d.ts"),
    "APG74-FX-007": ("src/embedded/widget.astro",),
    "APG74-FX-008": ("src/checked/config-loader.js",),
    "APG74-FX-009": ("package.json", "tsconfig.json"),
    "APG74-FX-010": ("package.json", "fixture-manifest.json"),
    "APG74-FX-011": ("tsconfig.declarations.json",),
    "APG74-FX-012": ("src/core/runtime-boundary.ts",),
    "APG74-FX-013": ("src/unbound/orphan-role-unknown.ts",),
    "APG74-FX-014": ("src/unbound/option-state-unknown.ts",),
}
EXPECTED_FIXTURE_FILES = {
    "README.md",
    "fixture-manifest.json",
    "package.json",
    "src/checked/config-loader.js",
    "src/core/inventory.ts",
    "src/core/runtime-boundary.ts",
    "src/declarations/host-metrics.d.ts",
    "src/embedded/widget.astro",
    "src/modules/legacy.cts",
    "src/modules/loader.mts",
    "src/ui/badge.tsx",
    "src/ui/jsx-host.d.ts",
    "src/unbound/option-state-unknown.ts",
    "src/unbound/orphan-role-unknown.ts",
    "tsconfig.declarations.json",
    "tsconfig.json",
}


class FixtureError(ValueError):
    """The maintained TypeScript fixture is malformed or contradicts its role state."""


def fail(message: str) -> NoReturn:
    raise FixtureError(message)


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            fail(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _string_array(value: Any, context: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        fail(f"{context} must be a string array")
    if len(value) != len(set(value)):
        fail(f"{context} contains duplicates")
    return value


def load_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_object)
    validate_manifest(value, path.parent)
    return value


def validate_manifest(value: Any, fixture_root: Path) -> None:
    if not isinstance(value, dict) or set(value) != {
        "authority", "authored_phase", "cases", "current_phase", "fixture",
        "lifecycle", "primary_compiler", "typescript6_disposition",
    }:
        fail("manifest top-level schema is invalid")
    if value["fixture"] != "apg74-typescript-intended-state":
        fail("manifest historical identity is invalid")
    if value["authored_phase"] != "APG74":
        fail("manifest authorship identity is invalid")
    if value["current_phase"] != "APG75A" or value["lifecycle"] != "provisionally-integrated":
        fail("manifest current lifecycle is invalid")
    if value["authority"] != "ADR 0042 Accepted; ADR 0043 Accepted with amendment":
        fail("manifest current authority is invalid")
    if value["primary_compiler"] != {
        "package": "typescript",
        "exact_version": "7.0.2",
        "selection_source": "package.json devDependencies exact pin",
        "generation": "TypeScript 7 native compiler (intended primary generation)",
    }:
        fail("primary compiler identity is invalid")
    if value["typescript6_disposition"] != "not-required (see APG74-FX-010)":
        fail("TypeScript 6 disposition is invalid")

    cases = value["cases"]
    if not isinstance(cases, list) or len(cases) != 14:
        fail("manifest must contain fourteen cases")
    expected_ids = [f"APG74-FX-{index:03d}" for index in range(1, 15)]
    if [case.get("id") for case in cases if isinstance(case, dict)] != expected_ids:
        fail("manifest case IDs are incomplete or unordered")

    for case in cases:
        if not isinstance(case, dict) or set(case) != CASE_KEYS:
            fail("manifest case schema is invalid")
        case_id = case["id"]
        if case["typescript_selection"] not in SELECTION_TOKENS:
            fail(f"{case_id} has an unknown selection")
        if case["role_identity_state"] not in IDENTITY_STATES:
            fail(f"{case_id} has an unknown role identity state")
        for field in ("option_facts", "paths", "present_evidence", "required_evidence"):
            _string_array(case[field], f"{case_id} {field}")
        if tuple(case["paths"]) != EXPECTED_CASE_PATHS[case_id]:
            fail(f"{case_id} fixture path identity changed")
        for relative in case["paths"]:
            path = Path(relative)
            if path.is_absolute() or ".." in path.parts or not (fixture_root / path).is_file():
                fail(f"{case_id} references an unsafe or missing path: {relative}")
        if any("=" not in fact for fact in case["option_facts"]):
            fail(f"{case_id} has an option name without a value")
        if set(case["present_evidence"]) & set(case["required_evidence"]):
            fail(f"{case_id} copies present evidence into required evidence")
        roles = case["compiler_roles"]
        if not isinstance(roles, list):
            fail(f"{case_id} compiler roles must be an array")
        if case["role_identity_state"] != "known" and roles:
            fail(f"{case_id} invents a role for a non-known identity")
        if case["role_identity_state"] == "known" and not roles:
            fail(f"{case_id} omits its known role")
        seen_roles: set[str] = set()
        for role in roles:
            if not isinstance(role, dict) or set(role) != ROLE_KEYS:
                fail(f"{case_id} compiler role schema is invalid")
            if role["role"] not in ROLE_TOKENS or role["role"] in seen_roles:
                fail(f"{case_id} has an unknown or duplicate role")
            seen_roles.add(role["role"])
            if role["package"] != "typescript" or role["exact_version"] != "7.0.2":
                fail(f"{case_id} conflates a role with another package identity")
            if role["product_state"] not in PRODUCT_STATES:
                fail(f"{case_id} has an unknown product state")
            if role["invocation_state"] not in INVOCATION_STATES:
                fail(f"{case_id} has an unknown invocation state")
            if role["invocation_state"] == "invoked" and not role["invocation_evidence"]:
                fail(f"{case_id} lacks invocation evidence")
            if role["product_state"] == "temporary":
                if role["retirement_condition"] in ("", "not-applicable"):
                    fail(f"{case_id} temporary role lacks a retirement condition")
            elif role["retirement_condition"] != "not-applicable":
                fail(f"{case_id} permanent role has a retirement condition")

    by_id = {case["id"]: case for case in cases}
    for case_id in ("APG74-FX-006", "APG74-FX-008"):
        if by_id[case_id]["typescript_selection"] != "embedded-route":
            fail(f"{case_id} must preserve embedded ownership")
    if [role["role"] for role in by_id["APG74-FX-009"]["compiler_roles"]] != ["cli-checker"]:
        fail("APG74-FX-009 must not infer an editor or API role from package surface")
    for case_id in ("APG74-FX-007", "APG74-FX-010", "APG74-FX-013", "APG74-FX-014"):
        if by_id[case_id]["compiler_roles"]:
            fail(f"{case_id} must not bind a concrete compiler role")
    if by_id["APG74-FX-010"]["role_identity_state"] != "not-required":
        fail("APG74-FX-010 must retain the not-required TypeScript 6 disposition")
    if any("unknown" in role for case in cases for role in case["compiler_roles"]):
        fail("unknown is evidence state, not a role token")
    actual_files = {
        path.relative_to(fixture_root).as_posix()
        for path in fixture_root.rglob("*")
        if path.is_file()
    }
    if actual_files != EXPECTED_FIXTURE_FILES:
        fail("fixture file set contains missing, substituted, or generated artifacts")
    for path in fixture_root.rglob("*"):
        relative = path.relative_to(fixture_root)
        if {"node_modules", "out"} & set(relative.parts):
            fail(f"generated or installed output is present: {relative}")
        if path.is_file() and path.suffix == ".tsbuildinfo":
            fail(f"generated compiler state is present: {relative}")


def validate_fixture_readme(text: str) -> None:
    required = (
        "Authored in APG74 and hardened in APG75",
        "current maintained fixture owner",
        "provisionally integrated after APG75A",
        "compiler-backed tests are current",
        "No target source is copied",
        "no generated output is committed",
    )
    lower = " ".join(text.lower().split())
    if any(marker.lower() not in lower for marker in required):
        fail("fixture README lifecycle is stale or incomplete")
    for stale in ("branch-only", "not integrated", "not a maintained test owner"):
        if stale in lower:
            fail("fixture README retains unintegrated lifecycle text")


def validate_fixture_projection(
    manifest: dict[str, Any], scenario_fixture: dict[str, Any]
) -> None:
    """Bind the 14 independent fixture vectors to consequence-bearing facts."""
    cases = {case["id"]: case for case in manifest["cases"]}
    rows = {
        row["id"]: row
        for row in scenario_fixture["rows"]
        if row["id"].startswith("APG74-FX-")
    }
    if set(rows) != set(cases):
        fail("scenario projection does not cover the exact fixture IDs")
    required_markers = {
        "APG74-FX-001": ("ordinary TypeScript", "project configuration"),
        "APG74-FX-002": (".mts", "ECMAScript-module"),
        "APG74-FX-003": (".cts", "CommonJS"),
        "APG74-FX-004": ("runtime verification", "handwritten"),
        "APG74-FX-005": ("regeneration provenance", "generated declarations"),
        "APG74-FX-006": ("JSX transform", "TSX"),
        "APG74-FX-007": ("host-extracted or virtual source", "embedded check"),
        "APG74-FX-008": ("checked-JavaScript", "language conversion"),
        "APG74-FX-009": ("CLI-checker", "editor API"),
        "APG74-FX-010": ("not required", "refresh condition"),
        "APG74-FX-011": ("declaration source-kind suffixes", "no JavaScript"),
        "APG74-FX-012": ("runtime execution evidence", "parsed runtime value"),
        "APG74-FX-013": ("unresolved role", "version-dependent"),
        "APG74-FX-014": ("indexed-access", "unresolved option"),
    }
    for case_id, case in cases.items():
        row = rows[case_id]
        roles = [role["role"] for role in case["compiler_roles"]]
        if row["required_roles"] != roles:
            fail(f"{case_id} scenario projection loses or invents a role")
        if case_id != "APG74-FX-014" and row["required_option_facts"] != case["option_facts"]:
            fail(f"{case_id} scenario projection loses exact option facts")
        if case["required_evidence"] and not row["required_evidence"]:
            fail(f"{case_id} scenario projection drops required evidence")
        if not row["present_evidence"] or not row["rollback_or_provenance"]:
            fail(f"{case_id} scenario projection loses evidence or provenance")
        if set(row["present_evidence"]) & set(row["required_evidence"]):
            fail(f"{case_id} scenario projection conflates evidence sets")
        for marker in required_markers.get(case_id, ()):
            combined = " ".join(
                (
                    *row["present_evidence"],
                    *row["required_evidence"],
                    row["owned_conclusion"],
                    row["nonowned_conclusion"],
                    row["rollback_or_provenance"],
                )
            )
            if marker not in combined:
                fail(f"{case_id} scenario projection loses {marker}")


def compiler_command(fixture_root: Path) -> tuple[str, ...]:
    override = os.environ.get("APG_TYPESCRIPT_TSC") or shutil.which("tsc")
    executable = Path(override) if override else fixture_root / "node_modules/.bin/tsc"
    if not executable.is_file():
        pytest_mod = sys.modules.get("pytest")
        if pytest_mod is not None:
            pytest_mod.skip("exact TypeScript compiler is unavailable; set APG_TYPESCRIPT_TSC")
        fail("exact TypeScript compiler is unavailable; set APG_TYPESCRIPT_TSC")
    return (str(executable),)


def run_compiler(
    fixture_root: Path,
    *arguments: str,
    expected_exit: int = 0,
) -> subprocess.CompletedProcess[str]:
    command_arguments = arguments
    has_source_file = any(
        argument.endswith((".ts", ".tsx", ".mts", ".cts", ".js", ".jsx"))
        for argument in arguments
    )
    if has_source_file and "-p" not in arguments and "--project" not in arguments:
        command_arguments = ("--ignoreConfig", *arguments)
    result = subprocess.run(
        (*compiler_command(fixture_root), *command_arguments),
        cwd=fixture_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        env={**os.environ, "NO_COLOR": "1"},
    )
    if result.returncode != expected_exit:
        fail(
            f"compiler exit {result.returncode}, expected {expected_exit}: "
            f"{' '.join(command_arguments)}\n{result.stdout}"
        )
    return result


def validate_compiler_version(fixture_root: Path) -> str:
    result = run_compiler(fixture_root, "--version")
    version = result.stdout.strip()
    if version != "Version 7.0.2":
        fail(f"unexpected compiler version: {version}")
    return version
