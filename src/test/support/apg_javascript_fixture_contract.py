"""Mechanical contract for the APG78/APG79 JavaScript fixture."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import stat
from typing import Any, NoReturn

from apg_javascript_candidate_contract import (
    AUTHORITY_IDS,
    COMPLETION_STATES,
    ContractError,
    EDIT_PERMISSIONS,
    ARTIFACT_CLASSES,
    GOAL_STATES,
    HOST_CONTEXTS,
    LANGUAGE_CONTEXTS,
    LIFECYCLE_STATES,
    PARSE_GOALS,
    PROVENANCE_CLASSES,
    QUALIFICATION_STATES,
    ROLE_STATES,
    ROUTE_RE,
    SELECTIONS,
    STRICTNESS_STATES,
    WHOLE_FILE_OWNERS,
    _strings,
    _strict_object,
)


GOAL_EVIDENCE_OWNERS = (
    "exact-node-package-mapping",
    "exact-node-qualification-host",
    "exact-node-vm-script-qualification",
    "node-runtime-owner",
    "project-configuration-owner",
)
MANIFEST_ARTIFACT_PATHS = (
    "src/evaluation.mjs",
    "src/scope.mjs",
    "src/coercion.mjs",
    "src/objects.mjs",
    "src/functions.mjs",
    "src/iteration.mjs",
    "src/errors.mjs",
    "src/async.mjs",
    "src/modules/counter.mjs",
    "src/modules/consumer.mjs",
    "src/modules/cycle-a.mjs",
    "src/modules/cycle-b.mjs",
    "src/modules/top-level-await.mjs",
    "src/dynamic-import-boundary.mjs",
    "src/module-boundary.mjs",
    "src/commonjs-boundary.cjs",
    "src/mode-selected.js",
    "unbound/mode-neutral.js.txt",
    "unbound/sloppy-script.js.txt",
    "unbound/strict-script.js.txt",
    "src/checked.js",
    "src/cli-core.mjs",
    "src/cli-node-adapter-boundary.cjs",
)
CASE_IDS = tuple(f"APG78-FX-{index:03d}" for index in range(1, 15))
CASE_SOURCE_BINDING_IDS = tuple(f"source::{case_id}" for case_id in CASE_IDS)
CASE_OWNED_CONCLUSION_IDS = tuple(f"owned::{case_id}" for case_id in CASE_IDS)
CASE_NONOWNED_CONCLUSION_IDS = tuple(f"nonowned::{case_id}" for case_id in CASE_IDS)
TOP_LEVEL_KEYS = {
    "authority", "cases", "fixture", "lifecycle", "schema_version", "source_bindings",
    "vocabulary",
}
CASE_KEYS = {
    "artifacts", "authority_ids", "completion_state", "edit_permission", "id",
    "lifecycle_state", "nonowned_conclusion_id", "nonowned_conclusion_note",
    "owned_conclusion_id", "owned_conclusion_note", "present_evidence",
    "provenance_class", "purpose", "required_evidence", "routes_or_obligations",
    "source_binding_id",
}


def fail(message: str) -> NoReturn:
    raise ContractError(message)


def load_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_object)
    validate_manifest(value, fixture_root=path.parent)
    return value


def validate_manifest(value: Any, *, fixture_root: Path | None = None) -> None:
    if not isinstance(value, dict) or set(value) != TOP_LEVEL_KEYS or value.get("schema_version") != 4:
        fail("fixture manifest must use schema version 4")
    if value["authority"] != {
        "authored_phase_id": "APG78",
        "candidate_decision_id": "ADR-0045",
        "candidate_state": "provisionally-integrated-with-known-debt",
        "current_phase_id": "APG79E",
        "governing_decision_id": "ADR-0042",
        "implementation_authority_ids": ["node-v22.22.2-darwin-arm64-bounded-observation"],
        "normative_authority_ids": ["ecma262-es2026"],
    }:
        fail("fixture authority is invalid")
    if value["fixture"] != {
        "edit_permission": "apg-maintainer-editable",
        "fixture_id": "apg78-javascript-core",
        "provenance_class": "apg-original",
    }:
        fail("fixture provenance or edit permission is invalid")
    if value["source_bindings"] != {
        "case_binding_ids": list(CASE_SOURCE_BINDING_IDS),
        "implementation_source_id": "node-v22.22.2-darwin-arm64-bounded-observation",
        "normative_source_id": "ecma262-es2026",
    }:
        fail("fixture source bindings are invalid")
    if value["vocabulary"] != {
        "authority_ids": list(AUTHORITY_IDS),
        "completion_states": list(COMPLETION_STATES),
        "conclusion_id_scheme": "row-qualified-v1",
        "edit_permissions": list(EDIT_PERMISSIONS),
        "lifecycle_states": list(LIFECYCLE_STATES),
        "provenance_classes": list(PROVENANCE_CLASSES),
        "source_binding_id_scheme": "row-qualified-v1",
    }:
        fail("fixture closed vocabulary is invalid")
    cases = value.get("cases")
    if not isinstance(cases, list) or len(cases) != 14:
        fail("fixture manifest must preserve 14 purposes")
    expected = list(CASE_IDS)
    if [case.get("id") for case in cases if isinstance(case, dict)] != expected:
        fail("fixture case IDs are incomplete or reordered")
    for case in cases:
        expected_case_keys = CASE_KEYS | ({"typescript_checker_state"} if case.get("id") == "APG78-FX-013" else set())
        if set(case) != expected_case_keys:
            fail(f"{case.get('id', '<unknown>')} case schema is invalid")
        for field in ("present_evidence", "required_evidence", "routes_or_obligations"):
            _strings(case[field], f"{case['id']} {field}")
        if any(
            artifact.get("qualification_engine_state") not in QUALIFICATION_STATES
            for artifact in case["artifacts"]
            if isinstance(artifact, dict)
        ):
            fail(f"{case['id']} has an invalid qualification-engine state")
        expected_authorities = ["ecma262-es2026"]
        if any(
            artifact["qualification_engine_state"].startswith("observed-")
            for artifact in case["artifacts"]
        ):
            expected_authorities.append("node-v22.22.2-darwin-arm64-bounded-observation")
        if case["authority_ids"] != expected_authorities:
            fail(f"{case['id']} authority IDs are not exact for the case")
        if case["source_binding_id"] != f"source::{case['id']}":
            fail(f"{case['id']} source binding is not exact for the case")
        if case["provenance_class"] != "apg-original":
            fail(f"{case['id']} provenance class is invalid")
        if case["edit_permission"] != "apg-maintainer-editable":
            fail(f"{case['id']} edit permission is invalid")
        if case["lifecycle_state"] != value["authority"]["candidate_state"]:
            fail(f"{case['id']} lifecycle state is stale")
        if case["owned_conclusion_id"] != f"owned::{case['id']}":
            fail(f"{case['id']} owned conclusion ID is invalid")
        if case["nonowned_conclusion_id"] != f"nonowned::{case['id']}":
            fail(f"{case['id']} nonowned conclusion ID is invalid")
        for note in ("owned_conclusion_note", "nonowned_conclusion_note"):
            if not isinstance(case[note], str) or not case[note].strip():
                fail(f"{case['id']} explanatory conclusion note is invalid")
        if set(case["present_evidence"]) & set(case["required_evidence"]):
            fail(f"{case['id']} copies present evidence into required evidence")
        if not isinstance(case.get("artifacts"), list) or not case["artifacts"]:
            fail(f"{case['id']} must contain per-path artifact vectors")
        for artifact in case["artifacts"]:
            if set(artifact) != {
                "artifact_class", "goal_evidence_owner", "goal_state", "host_context",
                "host_role_state", "javascript_selection", "language_contexts", "parse_goal", "path",
                "qualification_engine_state", "strictness_state", "whole_file_owner",
                "scenario_variant", "content_sha256",
            }:
                fail(f"{case['id']} artifact schema is invalid")
            if artifact["parse_goal"] not in PARSE_GOALS:
                fail(f"{case['id']} has an invalid parse goal")
            if artifact["host_context"] not in HOST_CONTEXTS:
                fail(f"{case['id']} has an invalid host context")
            language_contexts = artifact["language_contexts"]
            if (
                not isinstance(language_contexts, list)
                or not language_contexts
                or any(item not in LANGUAGE_CONTEXTS for item in language_contexts)
                or len(language_contexts) != len(set(language_contexts))
            ):
                fail(f"{case['id']} has an invalid language context")
            if artifact["artifact_class"] not in ARTIFACT_CLASSES:
                fail(f"{case['id']} has an invalid artifact class")
            if artifact["whole_file_owner"] not in WHOLE_FILE_OWNERS:
                fail(f"{case['id']} has an invalid whole-file owner")
            if artifact["goal_evidence_owner"] not in GOAL_EVIDENCE_OWNERS:
                fail(f"{case['id']} has an invalid goal-evidence owner")
            if not isinstance(artifact["scenario_variant"], str) or not artifact["scenario_variant"]:
                fail(f"{case['id']} has an invalid scenario variant")
            if (
                not isinstance(artifact["content_sha256"], str)
                or len(artifact["content_sha256"]) != 64
                or any(character not in "0123456789abcdef" for character in artifact["content_sha256"])
            ):
                fail(f"{case['id']} has an invalid artifact content binding")
            if artifact["goal_state"] not in GOAL_STATES:
                fail(f"{case['id']} has an invalid goal state")
            if (artifact["parse_goal"] == "unresolved") != (
                artifact["goal_state"] == "unresolved"
            ):
                fail(f"{case['id']} parse goal and evidence state disagree")
            if artifact["host_role_state"] not in ROLE_STATES:
                fail(f"{case['id']} has an invalid host role state")
            if artifact["strictness_state"] not in STRICTNESS_STATES:
                fail(f"{case['id']} has an invalid strictness state")
            if artifact["javascript_selection"] not in SELECTIONS:
                fail(f"{case['id']} has an invalid JavaScript selection")
            if artifact["qualification_engine_state"] not in QUALIFICATION_STATES:
                fail(f"{case['id']} has an invalid qualification-engine state")
            if artifact["parse_goal"] == "module" and artifact["strictness_state"] != "strict":
                fail(f"{case['id']} Module artifact is not strict")
            if artifact["host_role_state"] == "unresolved" and (
                not case["routes_or_obligations"] or not case["required_evidence"]
            ):
                fail(f"{case['id']} unresolved host role does not retain a stopped obligation")
        routes = case.get("routes_or_obligations")
        if not isinstance(routes, list) or any(
            not isinstance(route, str) or not ROUTE_RE.fullmatch(route) for route in routes
        ):
            fail(f"{case['id']} route lacks an exact owner and decision scope")
        expected_completion = (
            "stopped-required-evidence"
            if any(artifact["host_role_state"] == "unresolved" for artifact in case["artifacts"])
            else "owned-complete-nonowned-routes-open"
            if routes
            else "owned-complete"
        )
        if case["completion_state"] != expected_completion:
            fail(f"{case['id']} completion state contradicts evidence and routes")
    by_id = {case["id"]: case for case in cases}
    if len(by_id["APG78-FX-012"]["artifacts"]) < 2:
        fail("FX-012 does not preserve separate goal variants")
    if len(by_id["APG78-FX-014"]["artifacts"]) != 2:
        fail("FX-014 does not preserve separate core and adapter owners")
    commonjs = by_id["APG78-FX-011"]["artifacts"][0]
    if commonjs["whole_file_owner"] != "node-commonjs-owner":
        fail("CommonJS whole-file owner is incorrect")
    if commonjs["javascript_selection"] != "selected":
        fail("CommonJS decision-scoped JavaScript Selection is not selected")
    cli_adapter = by_id["APG78-FX-014"]["artifacts"][1]
    if cli_adapter["javascript_selection"] != "selected":
        fail("CLI CommonJS adapter decision-scoped JavaScript Selection is not selected")
    unknown = [
        item for item in by_id["APG78-FX-012"]["artifacts"]
        if item["goal_state"] == "unresolved"
    ]
    if len(unknown) != 1 or not unknown[0]["path"].startswith("unbound/"):
        fail("unknown-goal control is physically resolved")
    checked = by_id["APG78-FX-013"]
    if checked.get("typescript_checker_state") != "not-invoked":
        fail("@ts-check is promoted to checker invocation")
    lifecycle = value.get("lifecycle", {})
    if lifecycle != {
        "authored_by_phase_id": "APG78",
        "corrected_by_phase_ids": [
            "APG79-R1", "APG79-R2", "APG79-R3", "APG79A", "APG79B",
        ],
        "current_phase_id": "APG79E",
        "is_maintained_test_owner": True,
        "is_oracle": False,
        "state": "provisionally-integrated-with-known-debt",
    }:
        fail("fixture lifecycle is stale or open")
    artifact_paths = [artifact["path"] for case in cases for artifact in case["artifacts"]]
    if tuple(artifact_paths) != MANIFEST_ARTIFACT_PATHS or len(artifact_paths) != len(set(artifact_paths)):
        fail("fixture artifact paths are incomplete, reordered, or duplicated")
    if fixture_root is not None:
        resolved_root = fixture_root.resolve(strict=True)
        for relative in artifact_paths:
            candidate = fixture_root / relative
            try:
                metadata = candidate.lstat()
                resolved = candidate.resolve(strict=True)
            except OSError as error:
                fail(f"fixture artifact path is unreadable: {relative}: {error}")
            if (
                not stat.S_ISREG(metadata.st_mode)
                or resolved != candidate.absolute()
                or resolved == resolved_root
                or resolved_root not in resolved.parents
            ):
                fail(f"fixture artifact is not a direct regular file: {relative}")
            if hashlib.sha256(candidate.read_bytes()).hexdigest() != next(
                artifact["content_sha256"]
                for case in cases
                for artifact in case["artifacts"]
                if artifact["path"] == relative
            ):
                fail(f"fixture artifact content binding changed: {relative}")


def validate_fixture_projection(manifest: dict[str, Any], scenarios: dict[str, Any]) -> None:
    fixture_ids = [case["id"] for case in manifest["cases"]]
    scenario_ids = [row["id"] for row in scenarios["rows"] if row["id"].startswith("APG78-FX-")]
    if fixture_ids != scenario_ids:
        fail("fixture and independent scenario purposes diverge")
    scenario_by_id = {row["id"]: row for row in scenarios["rows"]}
    field_pairs = (
        ("artifact_class", "artifact_class"),
        ("whole_file_owner", "whole_file_owner"),
        ("parse_goal", "parse_goal"),
        ("host_context", "host_context"),
        ("language_contexts", "language_contexts"),
        ("goal_state", "goal_state"),
        ("strictness_state", "strictness"),
        ("javascript_selection", "javascript_selection"),
        ("host_role_state", "host_role_state"),
        ("qualification_engine_state", "qualification_engine_state"),
    )
    for case in manifest["cases"]:
        row = scenario_by_id[case["id"]]
        variants = {variant["label"]: variant for variant in row.get("variants", [])}
        for artifact in case["artifacts"]:
            label = artifact["scenario_variant"]
            vector = row if label == "row" else variants.get(label)
            if vector is None:
                fail(f"{case['id']} artifact has no exact scenario variant: {label}")
            for artifact_field, scenario_field in field_pairs:
                if artifact[artifact_field] != vector[scenario_field]:
                    fail(
                        f"{case['id']} {label} diverges at {artifact_field}"
                    )
