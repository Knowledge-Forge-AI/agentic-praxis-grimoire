"""Mechanical contract for the APG79 JavaScript candidate and oracle fixture."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import re
from typing import Any, NoReturn


CLAUSE_RE = re.compile(r"<!-- APG-CLAUSE: (JS-[A-Z0-9-]+) -->")
SELECTIONS = ("selected", "embedded-route", "route-to-owner", "non-trigger")
RESPONSES = (
    "proceed-routine",
    "inspect-before-judgment",
    "bounded-local-decision",
    "stop-and-escalate",
)
PARSE_GOALS = ("script", "module", "unresolved")
GOAL_STATES = ("known", "unresolved")
HOST_CONTEXTS = (
    "standalone",
    "commonjs-wrapper",
    "host-embedded",
    "host-transformed",
    "none",
)
LANGUAGE_CONTEXTS = (
    "expression-region",
    "global-code",
    "module-body",
    "function-body",
    "parameter-list",
    "block",
    "class-body",
    "module-graph",
    "unknown",
)
ARTIFACT_CLASSES = (
    "astro-script-region",
    "dynamic-import-module",
    "established-javascript-region",
    "extension-neutral-source-text",
    "handwritten-cjs",
    "handwritten-js",
    "handwritten-js-checked",
    "handwritten-mjs",
    "handwritten-mjs-configuration",
    "host-mapped-source",
    "mapped-source-text",
    "mixed-boundary",
    "module-control",
    "module-graph",
    "nonexecuted-javascript-source-text",
    "nonexecuted-source-text",
    "ordinary-object-region",
    "script-control",
    "top-level-await-module",
    "unknown-or-partial",
)
WHOLE_FILE_OWNERS = (
    "astro-host-owner",
    "javascript-language-profile",
    "node-commonjs-owner",
    "per-artifact",
    "per-host-artifact",
    "per-module-javascript",
    "project-configuration-owner",
    "unresolved-until-host-mapping",
)
STRICTNESS_STATES = (
    "strict",
    "non-strict",
    "per-variant",
    "unresolved",
    "explicit-directive-bounded-region",
    "intended-after-transform-only",
)
ROLE_STATES = ("known", "not-selected", "not-required", "unresolved")
QUALIFICATION_STATES = (
    "not-required",
    "not-invoked",
    "observed-exact-engine",
    "observed-syntax-only",
)
AUTHORITY_IDS = (
    "ecma262-es2026",
    "node-v22.22.2-darwin-arm64-bounded-observation",
)
LIFECYCLE_STATES = (
    "repair-required-after-apg79b",
    "provisionally-integrated-with-known-debt",
)
PROVENANCE_CLASSES = ("apg-original", "read-only-target-observation")
EDIT_PERMISSIONS = ("apg-maintainer-editable", "read-only-no-copy-no-edit")
COMPLETION_STATES = (
    "owned-complete",
    "owned-complete-nonowned-routes-open",
    "stopped-required-evidence",
)
ROUTE_OWNERS = (
    "browser-platform-owner",
    "build-transform-owner",
    "deployment-owner",
    "host-owner",
    "jsx-owner",
    "module-loader-owner",
    "node-runtime-owner",
    "performance-owner",
    "project-configuration-owner",
    "project-design-owner",
    "security-owner",
    "typescript-owner",
)
ROUTE_RE = re.compile(
    rf"^(?:{'|'.join(re.escape(owner) for owner in ROUTE_OWNERS)})::[^:].+$"
)
VARIANT_KEYS = {
    "artifact_class",
    "goal_state",
    "host_context",
    "host_role_state",
    "javascript_selection",
    "label",
    "language_contexts",
    "parse_goal",
    "qualification_engine_state",
    "response",
    "strictness",
    "whole_file_owner",
}
ROW_KEYS = {
    "authority_ids",
    "artifact_class",
    "fact_summary",
    "forbid",
    "goal_state",
    "host_context",
    "host_role_state",
    "id",
    "input_class",
    "javascript_selection",
    "language_contexts",
    "completion_state",
    "edit_permission",
    "lifecycle_state",
    "nonowned_conclusion_id",
    "nonowned_conclusion_note",
    "owned_conclusion_id",
    "owned_conclusion_note",
    "parse_goal",
    "present_evidence",
    "required_evidence",
    "response",
    "qualification_engine_state",
    "routes_or_obligations",
    "strictness",
    "provenance_class",
    "source_binding_id",
    "whole_file_owner",
}

SCENARIO_IDS = (
    tuple(f"APG78-JS-{index:03d}" for index in range(1, 25))
    + tuple(f"APG78-FX-{index:03d}" for index in range(1, 15))
    + ("APG79-TARGET-001", "APG79-TARGET-002", "APG79-TARGET-003")
)
SOURCE_BINDING_IDS = tuple(f"source::{row_id}" for row_id in SCENARIO_IDS)
OWNED_CONCLUSION_IDS = tuple(f"owned::{row_id}" for row_id in SCENARIO_IDS)
NONOWNED_CONCLUSION_IDS = tuple(f"nonowned::{row_id}" for row_id in SCENARIO_IDS)
JAVASCRIPT_QUALIFICATION_PYTHON_PATHS = (
    "src/test/int/python/agentic-praxis-grimoire/skills/javascript-language-profile/SKILL.int.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/libexec/apg_test.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/skills/javascript-language-profile/SKILL.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_javascript_candidate_contract.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_javascript_fixture_contract.unit.test.py",
    "src/test/support/apg_javascript_candidate_contract.py",
    "src/test/support/apg_javascript_fixture_contract.py",
)
TEST262_SOURCE_ROLE_KEYS = {
    "blocking_change_classes",
    "compatibility_oracle",
    "corpus_copied",
    "corpus_executed",
    "corpus_path_inventory_retained",
    "corpus_read",
    "corpus_vendored",
    "current_authority",
    "default_branch",
    "fresh_head_observation",
    "fresh_head_tree",
    "head_equality_required",
    "historical_false_identity",
    "historical_false_identity_disposition",
    "historical_review_pin",
    "historical_review_tree",
    "implementation_authority",
    "license_blob",
    "license_path",
    "license_role",
    "normative_authority",
    "refresh_condition",
    "repository",
    "role",
    "schema_version",
    "semantic_oracle",
    "source_id",
    "test_body_read_for_expected_behavior",
}


class ContractError(ValueError):
    """A maintained JavaScript contract surface is malformed."""


def fail(message: str) -> NoReturn:
    raise ContractError(message)


def _is_process_callable(name: str) -> bool:
    return (
        name in {
            "asyncio.create_subprocess_exec",
            "asyncio.create_subprocess_shell",
            "multiprocessing.Process",
            "os.popen",
            "os.system",
            "subprocess.Popen",
            "subprocess.call",
            "subprocess.check_call",
            "subprocess.check_output",
            "subprocess.run",
        }
        or name.startswith("os.spawn")
    )


class _ProcessInvocationVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.aliases: dict[str, str] = {}
        self.violations: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for item in node.names:
            if item.name in {"asyncio", "multiprocessing", "os", "subprocess"}:
                self.aliases[item.asname or item.name] = item.name
                if item.name == "subprocess":
                    self.violations.append(f"line {node.lineno}: import subprocess")

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        if module not in {"asyncio", "multiprocessing", "os", "subprocess"}:
            return
        for item in node.names:
            qualified = f"{module}.{item.name}"
            self.aliases[item.asname or item.name] = qualified
            if _is_process_callable(qualified):
                self.violations.append(f"line {node.lineno}: import {qualified}")

    def visit_Assign(self, node: ast.Assign) -> None:
        qualified = self._qualified(node.value)
        if qualified and _is_process_callable(qualified):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.aliases[target.id] = qualified
                    self.violations.append(f"line {node.lineno}: alias {qualified}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        qualified = self._qualified(node.func)
        if qualified and _is_process_callable(qualified):
            self.violations.append(f"line {node.lineno}: call {qualified}")
        if isinstance(node.func, ast.Name) and node.func.id == "__import__":
            imported = self._constant_string(node.args[0]) if node.args else None
            if imported == "subprocess":
                self.violations.append(f"line {node.lineno}: dynamic import subprocess")
        self.generic_visit(node)

    def _qualified(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return self.aliases.get(node.id)
        if isinstance(node, ast.Attribute):
            base = self._qualified(node.value)
            return f"{base}.{node.attr}" if base else None
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "__import__":
                imported = self._constant_string(node.args[0]) if node.args else None
                return imported
            if isinstance(node.func, ast.Name) and node.func.id == "getattr" and len(node.args) >= 2:
                base = self._qualified(node.args[0])
                attribute = self._constant_string(node.args[1])
                if base and attribute:
                    return f"{base}.{attribute}"
        return None

    @staticmethod
    def _constant_string(node: ast.AST) -> str | None:
        return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def javascript_process_invocation_violations(source: str) -> tuple[str, ...]:
    """Close named static Python process forms without claiming dynamic completeness."""
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        fail(f"maintained JavaScript Python owner has invalid syntax: {error}")
    visitor = _ProcessInvocationVisitor()
    visitor.visit(tree)
    return tuple(visitor.violations)


def validate_javascript_process_invocation_owners(root: Path) -> None:
    """Require maintained JavaScript owners to use the one repository wrapper."""
    for relative in JAVASCRIPT_QUALIFICATION_PYTHON_PATHS:
        source = (root / relative).read_text(encoding="utf-8")
        violations = javascript_process_invocation_violations(source)
        if violations:
            fail(f"{relative} bypasses the JavaScript invocation owner: {violations[0]}")
    runner = (root / "libexec/apg_test.py").read_text(encoding="utf-8")
    tree = ast.parse(runner)
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    wrapper = functions.get("_run_javascript_process")
    if wrapper is None:
        fail("JavaScript process wrapper is missing")
    visitor = _ProcessInvocationVisitor()
    visitor.aliases["subprocess"] = "subprocess"
    visitor.visit(wrapper)
    calls = [item for item in visitor.violations if "call subprocess.run" in item]
    if len(calls) != 1:
        fail("JavaScript process wrapper must contain one approved process call site")
    for owner in ("_javascript_engine_binding", "invoke_javascript_engine"):
        node = functions.get(owner)
        if node is None:
            fail(f"JavaScript invocation owner is missing: {owner}")
        nested = _ProcessInvocationVisitor()
        nested.aliases["subprocess"] = "subprocess"
        nested.visit(node)
        if nested.violations:
            fail(f"{owner} contains a second direct process invocation site")
        if not any(
            isinstance(call.func, ast.Name) and call.func.id == "_run_javascript_process"
            for call in ast.walk(node)
            if isinstance(call, ast.Call)
        ):
            fail(f"{owner} does not use the approved JavaScript process wrapper")


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            fail(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _strings(value: Any, context: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        fail(f"{context} must be a string array")
    if len(value) != len(set(value)):
        fail(f"{context} contains duplicates")
    return value


def load_scenario_fixture(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_object)
    validate_scenario_fixture(value)
    return value


def load_test262_source_role(path: Path) -> dict[str, Any]:
    """Load the canonical duplicate-refusing APG79D Test262 role record."""
    raw = path.read_text(encoding="utf-8")
    value = json.loads(raw, object_pairs_hook=_strict_object)
    validate_test262_source_role(value)
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
    if raw != canonical:
        fail("Test262 source-role JSON is not canonical")
    return value


def validate_test262_source_role(value: Any) -> dict[str, str | bool]:
    """Close Test262's rights-only role without pinning a mutable head."""
    if not isinstance(value, dict) or set(value) != TEST262_SOURCE_ROLE_KEYS:
        fail("Test262 source-role schema is invalid")
    _validate_test262_fixed_fields(value)
    _validate_test262_roles(value)
    _validate_test262_observation(value)
    return {
        "corpus_use": False,
        "head_drift": "freshness-only-non-blocking",
        "normative": False,
        "rights": "unchanged",
    }


def _validate_test262_fixed_fields(value: dict[str, Any]) -> None:
    expected_scalars = {
        "schema_version": 1,
        "source_id": "test262",
        "repository": "https://github.com/tc39/test262",
        "default_branch": "main",
        "role": "non-normative-rights-only",
        "historical_review_pin": "be13516fb6441b950ba8a3df97eb34062c186972",
        "historical_review_tree": "e68a5c15a290b98d7b6b43b874d981df5d152d23",
        "license_path": "LICENSE",
        "license_blob": "a56b038f0e01b05b004d92097d4601ba629afdf3",
        "license_role": "copying-and-rights-boundary",
        "historical_false_identity": "be135ec02b6ae31ebdb99a1d550355f66af1f195",
        "historical_false_identity_disposition": (
            "unresolvable-official-object; historical-source-identity-transcription-defect; "
            "immutable-report-preserved; superseded-as-current-authority; not-accepted-debt"
        ),
        "current_authority": "APG79D source-role record plus exact rights object",
        "refresh_condition": (
            "refresh default-branch head, tree, and LICENSE blob; ordinary head drift is "
            "freshness-only when the rights blob and no-corpus role are unchanged"
        ),
    }
    diagnostics = {
        "historical_review_pin": "Test262 historical review pin is invalid",
        "license_blob": "Test262 license blob is invalid",
        "historical_false_identity_disposition": (
            "Test262 historical false identity disposition is invalid"
        ),
        "current_authority": (
            "Test262 historical false identity cannot become current authority"
        ),
        "refresh_condition": "Test262 refresh condition is invalid",
    }
    for field, expected in expected_scalars.items():
        if value[field] != expected:
            fail(diagnostics.get(field, f"Test262 {field.replace('_', ' ')} is invalid"))


def _validate_test262_roles(value: dict[str, Any]) -> None:
    false_roles = {
        "normative_authority": "normative authority",
        "semantic_oracle": "semantic oracle",
        "compatibility_oracle": "compatibility oracle",
        "implementation_authority": "implementation authority",
    }
    for field, label in false_roles.items():
        if value[field] is not False:
            fail(f"Test262 {label} must be false")
    corpus_fields = (
        "corpus_read",
        "corpus_copied",
        "corpus_executed",
        "corpus_vendored",
        "corpus_path_inventory_retained",
        "test_body_read_for_expected_behavior",
    )
    if any(value[field] is not False for field in corpus_fields):
        fail("Test262 corpus use must remain false")
    if value["head_equality_required"] is not False:
        fail("Test262 mutable head equality must not be required")
    if value["blocking_change_classes"] != [
        "copied-expression-change",
        "corpus-use-change",
        "license-blob-change",
        "rights-role-change",
    ]:
        fail("Test262 blocking change classes are invalid")


def _validate_test262_observation(value: dict[str, Any]) -> None:
    observation = value["fresh_head_observation"]
    if not isinstance(observation, dict) or set(observation) != {
        "commit", "method", "observed_at", "relation_to_historical_review_pin"
    }:
        fail("Test262 fresh-head observation schema is invalid")
    if not isinstance(observation["commit"], str) or not re.fullmatch(
        r"[0-9a-f]{40}", observation["commit"]
    ):
        fail("Test262 fresh-head commit is invalid")
    if observation["method"] != "GitHub REST default-branch ref and Git commit/tree reads":
        fail("Test262 fresh-head observation method is invalid")
    if not isinstance(observation["observed_at"], str) or not re.fullmatch(
        r"20[0-9]{2}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z",
        observation["observed_at"],
    ):
        fail("Test262 fresh-head observation time is invalid")
    expected_relation = (
        "equal-to-historical-review-pin"
        if observation["commit"] == value["historical_review_pin"]
        else "advanced-from-historical-review-pin"
    )
    if observation["relation_to_historical_review_pin"] != expected_relation:
        fail("Test262 fresh-head relationship is invalid")
    if not isinstance(value["fresh_head_tree"], str) or not re.fullmatch(
        r"[0-9a-f]{40}", value["fresh_head_tree"]
    ):
        fail("Test262 fresh-head tree is invalid")


def validate_scenario_fixture(value: Any) -> None:
    if not isinstance(value, dict) or set(value) != {
        "authority", "rows", "schema_version", "vocabulary"
    }:
        fail("scenario fixture top-level schema is invalid")
    if value["schema_version"] != 2:
        fail("scenario fixture schema version is invalid")
    if value["vocabulary"] != {
        "artifact_classes": list(ARTIFACT_CLASSES),
        "authority_ids": list(AUTHORITY_IDS),
        "completion_states": list(COMPLETION_STATES),
        "conclusion_id_scheme": "row-qualified-v1",
        "edit_permissions": list(EDIT_PERMISSIONS),
        "goal_states": list(GOAL_STATES),
        "host_contexts": list(HOST_CONTEXTS),
        "language_contexts": list(LANGUAGE_CONTEXTS),
        "parse_goals": list(PARSE_GOALS),
        "lifecycle_states": list(LIFECYCLE_STATES),
        "provenance_classes": list(PROVENANCE_CLASSES),
        "qualification_states": list(QUALIFICATION_STATES),
        "responses": list(RESPONSES),
        "role_states": list(ROLE_STATES),
        "selections": list(SELECTIONS),
        "strictness_states": list(STRICTNESS_STATES),
        "source_binding_id_scheme": "row-qualified-v1",
        "whole_file_owners": list(WHOLE_FILE_OWNERS),
    }:
        fail("scenario fixture vocabulary is invalid")
    if set(SELECTIONS) & set(RESPONSES):
        fail("selection and response vocabularies overlap")
    authority = value["authority"]
    if authority != {
        "authored_phase_id": "APG78",
        "candidate_decision_id": "ADR-0045",
        "candidate_state": "provisionally-integrated-with-known-debt",
        "current_phase_id": "APG79E",
        "fixture_purposes": 14,
        "governing_decision_id": "ADR-0042",
        "implementation_authority_ids": ["node-v22.22.2-darwin-arm64-bounded-observation"],
        "normative_authority_ids": ["ecma262-es2026"],
        "semantic_purposes": 24,
        "target_rows": 3,
    }:
        fail("scenario fixture authority is invalid")
    rows = value["rows"]
    if not isinstance(rows, list) or len(rows) != 41:
        fail("scenario fixture must contain 41 rows")
    expected = list(SCENARIO_IDS)
    if [row.get("id") for row in rows if isinstance(row, dict)] != expected:
        fail("scenario IDs are not complete and ordered")
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            fail("scenario row schema is invalid")
        target_row = row["id"].startswith("APG79-TARGET-")
        expected_keys = ROW_KEYS | ({"target_binding_commitment"} if target_row else set())
        if "variants" in row:
            expected_keys |= {"variants"}
        if set(row) != expected_keys:
            fail(f"{row['id']} scenario row schema is invalid for its row class")
        if target_row and not re.fullmatch(r"[0-9a-f]{64}", row["target_binding_commitment"]):
            fail(f"{row['id']} target binding commitment is invalid")
        for field in (
            "forbid", "present_evidence", "required_evidence", "routes_or_obligations",
        ):
            _strings(row[field], f"{row['id']} {field}")
        expected_authorities = ["ecma262-es2026"]
        vectors = row.get("variants", [row])
        if any(vector["qualification_engine_state"].startswith("observed-") for vector in vectors):
            expected_authorities.append("node-v22.22.2-darwin-arm64-bounded-observation")
        if row["authority_ids"] != expected_authorities:
            fail(f"{row['id']} authority IDs are not exact for the row")
        if row["source_binding_id"] != f"source::{row['id']}":
            fail(f"{row['id']} source binding is not exact for the row")
        if row["provenance_class"] != (
            "read-only-target-observation" if target_row else "apg-original"
        ):
            fail(f"{row['id']} provenance class is invalid")
        if row["edit_permission"] != (
            "read-only-no-copy-no-edit" if target_row else "apg-maintainer-editable"
        ):
            fail(f"{row['id']} edit permission is invalid")
        if row["lifecycle_state"] != authority["candidate_state"]:
            fail(f"{row['id']} lifecycle state is stale")
        if row["owned_conclusion_id"] != f"owned::{row['id']}":
            fail(f"{row['id']} owned conclusion ID is invalid")
        if row["nonowned_conclusion_id"] != f"nonowned::{row['id']}":
            fail(f"{row['id']} nonowned conclusion ID is invalid")
        for note in ("owned_conclusion_note", "nonowned_conclusion_note"):
            if not isinstance(row[note], str) or not row[note].strip():
                fail(f"{row['id']} explanatory conclusion note is invalid")
        if "variants" in row:
            if not isinstance(vectors, list) or len(vectors) < 2:
                fail(f"{row['id']} variants are incomplete")
            if (
                row["artifact_class"] != "per-variant"
                or row["whole_file_owner"] != "per-variant"
                or row["parse_goal"] != "unresolved"
                or row["host_context"] != "none"
                or row["language_contexts"] != ["unknown"]
                or row["goal_state"] != "unresolved"
                or row["strictness"] != "per-variant"
                or row["javascript_selection"] != "per-variant"
                or row["host_role_state"] != "unresolved"
                or row["qualification_engine_state"] != "per-variant"
                or row["response"] != "per-variant"
            ):
                fail(f"{row['id']} aggregate vector invents a shared state")
        for vector in vectors:
            if "variants" in row and (not isinstance(vector, dict) or set(vector) != VARIANT_KEYS):
                fail(f"{row['id']} variant schema is invalid")
            context = f"{row['id']} {vector.get('label', 'row')}"
            if vector["javascript_selection"] not in SELECTIONS:
                fail(f"{context} has an unknown selection")
            if vector["response"] not in RESPONSES:
                fail(f"{context} has an unknown response")
            if vector["parse_goal"] not in PARSE_GOALS:
                fail(f"{context} has an invalid parse goal")
            if vector["host_context"] not in HOST_CONTEXTS:
                fail(f"{context} has an invalid host context")
            language_contexts = vector["language_contexts"]
            if (
                not isinstance(language_contexts, list)
                or not language_contexts
                or any(item not in LANGUAGE_CONTEXTS for item in language_contexts)
                or len(language_contexts) != len(set(language_contexts))
            ):
                fail(f"{context} has an invalid language context")
            if vector["artifact_class"] not in ARTIFACT_CLASSES:
                fail(f"{context} has an invalid artifact class")
            if vector["whole_file_owner"] not in WHOLE_FILE_OWNERS:
                fail(f"{context} has an invalid whole-file owner")
            if vector["goal_state"] not in GOAL_STATES:
                fail(f"{context} has an invalid goal state")
            if vector["strictness"] not in STRICTNESS_STATES:
                fail(f"{context} has an invalid strictness state")
            if vector["host_role_state"] not in ROLE_STATES:
                fail(f"{context} has an invalid host role state")
            if vector["qualification_engine_state"] not in QUALIFICATION_STATES:
                fail(f"{context} has an invalid qualification state")
            if (vector["parse_goal"] == "unresolved") != (vector["goal_state"] == "unresolved"):
                fail(f"{context} parse goal and goal evidence disagree")
            if vector["parse_goal"] == "module" and vector["strictness"] != "strict":
                fail(f"{context} Module vector is not strict")
            if vector["host_role_state"] == "unresolved" and (
                not row["routes_or_obligations"] or not row["required_evidence"]
            ):
                fail(f"{context} unresolved host role lacks a stopped obligation")
        if set(row["present_evidence"]) & set(row["required_evidence"]):
            fail(f"{row['id']} copies present evidence into required evidence")
        effective_responses = [vector["response"] for vector in vectors]
        if "stop-and-escalate" in effective_responses and not row["routes_or_obligations"]:
            fail(f"{row['id']} stops without a named obligation")
        if any(not ROUTE_RE.fullmatch(route) for route in row["routes_or_obligations"]):
            fail(f"{row['id']} route lacks an exact owner and decision scope")
        expected_completion = (
            "stopped-required-evidence"
            if "stop-and-escalate" in effective_responses
            else "owned-complete-nonowned-routes-open"
            if row["routes_or_obligations"]
            else "owned-complete"
        )
        if row["completion_state"] != expected_completion:
            fail(f"{row['id']} completion state contradicts response and routes")

    by_id = {row["id"]: row for row in rows}
    commonjs = by_id["APG78-FX-011"]
    if commonjs["whole_file_owner"] != "node-commonjs-owner":
        fail("CommonJS whole-file ownership is not host-owned")
    if commonjs["parse_goal"] != "unresolved" or commonjs["host_context"] != "commonjs-wrapper":
        fail("CommonJS goal and host context are conflated")
    if commonjs["qualification_engine_state"] != "observed-syntax-only":
        fail("CommonJS syntax is promoted to wrapper execution")
    if commonjs["javascript_selection"] != "selected":
        fail("CommonJS decision-scoped JavaScript Selection is not selected")
    strictness = by_id["APG78-JS-005"]
    if len(strictness.get("variants", [])) != 3:
        fail("strictness purpose collapses Script and Module variants")
    if [variant["label"] for variant in strictness["variants"]] != [
        "sloppy-script", "strict-script", "module",
    ]:
        fail("strictness purpose loses an exact variant")
    if [
        (variant["parse_goal"], variant["strictness"], variant["language_contexts"])
        for variant in strictness["variants"]
    ] != [
        ("script", "non-strict", ["global-code"]),
        ("script", "strict", ["global-code"]),
        ("module", "strict", ["module-body"]),
    ]:
        fail("strictness purpose changes an exact variant")
    goals = by_id["APG78-JS-018"]
    if len(goals.get("variants", [])) != 3:
        fail("goal-mapping purpose collapses known and unresolved variants")
    if [variant["label"] for variant in goals["variants"]] != [
        "known-script", "known-module", "unresolved",
    ]:
        fail("goal-mapping purpose loses an exact variant")
    if [
        (variant["parse_goal"], variant["goal_state"], variant["strictness"])
        for variant in goals["variants"]
    ] != [
        ("script", "known", "non-strict"),
        ("module", "known", "strict"),
        ("unresolved", "unresolved", "unresolved"),
    ]:
        fail("goal-mapping purpose changes an exact variant")
    unknown = by_id["APG78-FX-012"]
    if [variant["label"] for variant in unknown.get("variants", [])] != [
        "unresolved-source-text", "known-module-control",
        "sloppy-script-control", "strict-script-control",
    ]:
        fail("unknown-goal purpose loses its known or unresolved variant")
    if {variant["goal_state"] for variant in unknown["variants"]} != {"known", "unresolved"}:
        fail("unknown-goal control is not unresolved")
    checked = by_id["APG78-FX-013"]
    if "checker invocation" not in " ".join(checked["required_evidence"]):
        fail("checked JavaScript invents a checker result")
    cli = by_id["APG78-FX-014"]
    if len(cli.get("variants", [])) != 2:
        fail("CLI purpose conflates core and adapter vectors")
    if "returned message data" not in cli["owned_conclusion_note"]:
        fail("CLI core is not effect-free")
    cli_variants = {variant["label"]: variant for variant in cli["variants"]}
    if cli_variants["commonjs-node-adapter"]["qualification_engine_state"] != "observed-syntax-only":
        fail("CLI adapter syntax is promoted to wrapper execution")
    if cli_variants["commonjs-node-adapter"]["javascript_selection"] != "selected":
        fail("CLI CommonJS adapter decision-scoped JavaScript Selection is not selected")
    module_fixture = by_id["APG78-FX-009"]
    if {variant["label"] for variant in module_fixture.get("variants", [])} != {
        "authored-static-graph", "dynamic-import", "top-level-await",
    }:
        fail("module fixture collapses distinct observations")
    if any(
        variant["qualification_engine_state"] != "observed-exact-engine"
        for variant in module_fixture["variants"]
    ):
        fail("module fixture claims an unobserved exact-engine result")
    routes = by_id["APG78-JS-023"]
    if routes["response"] != "stop-and-escalate":
        fail("absent receivers are not stopped")
    if len(routes["routes_or_obligations"]) < 4:
        fail("absent receiver set is incomplete")
    target_module = by_id["APG79-TARGET-001"]
    if (
        target_module["whole_file_owner"] != "project-configuration-owner"
        or target_module["javascript_selection"] != "selected"
        or target_module["host_role_state"] != "unresolved"
        or target_module["qualification_engine_state"] != "not-invoked"
    ):
        fail("checked target module invents an owner, region selection, or observed host role")
    expected_target_commitments = {
        "APG79-TARGET-001": "435c697c524e6af3c06f0475f2f429204e418a11adc29b4ad1913f24795013be",
        "APG79-TARGET-002": "650ab09f089b7141398be250f62d6aa3f15c6b127af99348025e76732f1e6c94",
        "APG79-TARGET-003": "fb734c14b59d5de56649bb01d02129cf645ce72cfe7aa180c5a439cdb258576a",
    }
    if {
        target_id: by_id[target_id].get("target_binding_commitment")
        for target_id in expected_target_commitments
    } != expected_target_commitments:
        fail("fresh target rows are not bound to exact retained evidence")
    for target_id in ("APG79-TARGET-002", "APG79-TARGET-003"):
        target = by_id[target_id]
        if (
            target["parse_goal"] != "unresolved"
            or target["goal_state"] != "unresolved"
            or target["strictness"] != "unresolved"
            or target["host_role_state"] != "unresolved"
            or target["qualification_engine_state"] != "not-invoked"
        ):
            fail("Astro target promotes intended processing to observed state")


def validate_candidate(leaf: str, specification: str, coverage: str, *, integrated: bool) -> None:
    clauses = CLAUSE_RE.findall(leaf)
    if len(clauses) != 25 or len(clauses) != len(set(clauses)):
        fail("candidate must have 25 unique stable clauses")
    candidate = " ".join((leaf + "\n" + specification).split()).lower()
    for marker in (
        "parse goal", "host context", "language contexts", "goal evidence state", "continuous optional chain",
        "HostEnqueuePromiseJob", "CommonJS", "@ts-check", "absent receiver",
        "Proxy", "SharedArrayBuffer", "structural policy is deferred",
    ):
        if marker.lower() not in candidate:
            fail(f"candidate is missing boundary marker: {marker}")
    forbidden = (
        "ECMAScript job queue",
        "remainder of the chain",
        "routine handoff",
        "@ts-check directive makes TypeScript",
    )
    for marker in forbidden:
        if marker.lower() in candidate:
            fail(f"candidate retains false boundary marker: {marker}")
    if "navigation-only" not in coverage.lower():
        fail("coverage must remain navigation-only")
    lifecycle = (
        "provisionally-integrated-with-known-debt"
        if integrated
        else "repair-required-after-apg79b"
    )
    if lifecycle not in (leaf + "\n" + specification + "\n" + coverage):
        fail("candidate lifecycle is inconsistent")
