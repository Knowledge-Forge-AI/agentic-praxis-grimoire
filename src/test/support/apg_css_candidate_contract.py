"""Executable APG60 CSS pre-authoring contract; rejected evidence only."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from typing import Any, NoReturn

from apg_repository_path_contract import (
    RepositoryPathContract,
    RepositoryPathError,
)


class ContractError(ValueError):
    """A closed-schema or behavioral-contract failure."""


APG60_CONTRACT_SHA256 = (
    "d0847c10577ed59336693093dbaf422ac9944a4ab1631833ebf328680c283858"
)
TOP_KEYS = {
    "candidate",
    "cases",
    "contract_revision",
    "counting",
    "policy",
    "schema_version",
    "status",
    "supersedes_contract_sha256",
}
CASE_KEYS = {
    "actual_count",
    "artifact",
    "authority",
    "baseline_count",
    "current_count",
    "embedded_host",
    "established_requirements",
    "exception_grant_source",
    "exclusions",
    "expected",
    "family",
    "id",
    "input",
    "operation",
    "projected_count",
    "semantic_facts",
    "source_basis",
    "task_group",
}
INPUT_KEYS = {"control", "parts", "responsibility"}
EXPECTED_KEYS = {
    "forbidden_actions",
    "governing_state",
    "growth_level",
    "permitted",
    "required_actions",
    "rollback",
    "selected_owner",
    "semantic_level",
}
FAMILY_COUNTS = {
    "growth-transition": 8,
    "task-aggregation": 10,
    "authority": 8,
    "semantic-owner": 10,
    "one-count-exclusions": 12,
    "legacy-exception": 6,
    "lifecycle-removal": 6,
}
OPERATIONS = {
    "smallest-safe-correction",
    "material-new-behavior",
    "decomposition-or-removal",
    "non-growing-documentation",
}
REQUIRED_ACTIONS = {
    "record-growth-state",
    "proceed-project-conventions",
    "apply-yellow-response",
    "name-responsibility",
    "identify-extraction-seams",
    "bound-new-responsibility",
    "focused-validation",
    "apply-orange-response",
    "containment-or-decomposition-plan",
    "name-new-responsibility",
    "justify-isolation-order",
    "rollback-plan",
    "apply-red-response",
    "stop-material-growth",
    "decompose-first",
    "request-bounded-exception",
    "record-smallest-safe-correction",
    "post-change-verification",
    "stop-and-reauthorize",
    "rollback",
    "preserve-task-baseline",
    "aggregate-complete-task",
    "classify-independent-responsibilities",
    "explain-css-behavior",
    "escalate-project-acceptance",
    "restore-established-condition",
    "apply-repository-policy",
    "apply-task-instruction",
    "reject-incidental-override",
    "validate-bounded-exception",
    "host-one-count",
    "css-semantic-review",
    "exclude-artifact",
    "return-decision-to-project",
    "remove-current-owner",
    "repair-surviving-reference",
    "derive-counts-from-live-inventory",
    "preserve-historical-evidence",
}
FORBIDDEN_ACTIONS = {
    "unplanned-material-growth",
    "baseline-reset",
    "salami-slicing",
    "feature-as-correction",
    "implicit-weaker-convention",
    "invent-accessibility-requirement",
    "css-final-accessibility-acceptance",
    "global-scope-only-escalation",
    "token-value-ownership",
    "additive-embedded-count",
    "edit-excluded-artifact",
    "material-red-growth",
    "cohesion-as-exception",
    "exception-scope-overrun",
    "raw-historical-revert",
    "stale-current-reference",
    "delete-historical-evidence",
}
ACTION_VOCABULARY = frozenset(REQUIRED_ACTIONS | FORBIDDEN_ACTIONS)
LEVEL_ORDER = {"Green": 0, "Yellow": 1, "Orange": 2, "Red": 3}
EXCEPTION_GRANT_SOURCES = {"human-instruction", "repository-policy"}


def fail(message: str) -> NoReturn:
    raise ContractError(message)


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            fail(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def canonical_contract_bytes(value: dict[str, Any]) -> bytes:
    """Render the line-bounded canonical APG60 fixture representation."""
    validate_contract(value)
    lines = ["{", f'"candidate":{_compact(value["candidate"])},', '"cases":[']
    cases = value["cases"]
    lines.extend(
        _compact(case) + ("," if index + 1 < len(cases) else "")
        for index, case in enumerate(cases)
    )
    lines.extend(
        [
            "],",
            f'"contract_revision":{_compact(value["contract_revision"])},',
            f'"counting":{_compact(value["counting"])},',
            f'"policy":{_compact(value["policy"])},',
            f'"schema_version":{_compact(value["schema_version"])},',
            f'"status":{_compact(value["status"])},',
            (
                '"supersedes_contract_sha256":'
                f'{_compact(value["supersedes_contract_sha256"])}'
            ),
            "}",
        ]
    )
    return ("\n".join(lines) + "\n").encode("utf-8")


def _exact_keys(value: Any, expected: set[str], context: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        fail(f"{context} schema has unknown or missing keys")


def _string_list(value: Any, context: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        fail(f"{context} must be a string array")
    if value != sorted(set(value)):
        fail(f"{context} must be sorted and unique")
    return value


def _nonempty_string_sequence(value: Any, context: str) -> list[str]:
    if not isinstance(value, list) or not value:
        fail(f"{context} must be a nonempty string array")
    if any(not isinstance(item, str) or not item for item in value):
        fail(f"{context} must contain nonempty strings")
    if len(value) != len(set(value)):
        fail(f"{context} must contain unique strings")
    return value


def _validate_expected(value: Any, case_id: str) -> None:
    _exact_keys(value, EXPECTED_KEYS, f"{case_id} expected")
    for field in ("required_actions", "forbidden_actions"):
        actions = _string_list(value[field], f"{case_id} {field}")
        if not set(actions) <= ACTION_VOCABULARY:
            fail(f"{case_id} {field} uses an unknown action")
    if not isinstance(value["permitted"], bool) or not isinstance(value["rollback"], bool):
        fail(f"{case_id} expected booleans are invalid")
    for field in ("governing_state", "growth_level", "selected_owner", "semantic_level"):
        if not isinstance(value[field], str) or not value[field]:
            fail(f"{case_id} expected {field} is invalid")


def _validate_policy(value: Any) -> None:
    _exact_keys(value["policy"], {"bands", "frozen", "source"}, "policy")
    if value["policy"]["frozen"] is not True:
        fail("policy must remain frozen")
    bands = value["policy"]["bands"]
    _exact_keys(bands, {"Green", "Yellow", "Orange", "Red"}, "policy bands")
    expected_bands = {
        "Green": {"maximum": 299, "minimum": 0},
        "Yellow": {"maximum": 599, "minimum": 300},
        "Orange": {"maximum": 899, "minimum": 600},
        "Red": {"maximum": None, "minimum": 900},
    }
    if bands != expected_bands:
        fail("policy bands differ from frozen 300/600/900 values")


def _validate_counting(value: Any) -> None:
    _exact_keys(
        value["counting"],
        {"bom", "comments", "excluded", "final_segment", "newline", "one_count", "unit"},
        "counting",
    )
    exclusions = _string_list(value["counting"]["excluded"], "counting excluded")
    if set(exclusions) != {
        "generated", "minified", "vendored", "lock", "snapshot", "fixture",
        "demo", "build-output", "binary", "unsupported-encoding", "symlink", "submodule",
    }:
        fail("counting exclusion family is incomplete")


def _validate_task_aggregation_inputs(case: dict[str, Any]) -> None:
    if "baseline-reset-attempt" in case["semantic_facts"] and (
        not _several_conversational_turns(case["input"]["parts"])
        or not _several_tool_calls(case["input"]["parts"])
    ):
        fail(
            f"{case['id']} baseline-reset-attempt requires several tool calls "
            "and conversational turns"
        )


def _validate_case(case: Any) -> None:
    _exact_keys(case, CASE_KEYS, f"{case['id']} case")
    _exact_keys(case["input"], INPUT_KEYS, f"{case['id']} input")
    if case["operation"] not in OPERATIONS:
        fail(f"{case['id']} operation is invalid")
    _nonempty_string_sequence(case["input"]["parts"], f"{case['id']} input parts")
    for field in ("established_requirements", "exclusions", "semantic_facts"):
        _string_list(case[field], f"{case['id']} {field}")
    grant_source = case["exception_grant_source"]
    if grant_source is not None and grant_source not in EXCEPTION_GRANT_SOURCES:
        fail(f"{case['id']} exception grant source is invalid")
    if case["authority"] == "artifact-exception-valid":
        if grant_source not in EXCEPTION_GRANT_SOURCES:
            fail(f"{case['id']} artifact exception grant source is required")
    elif grant_source is not None:
        fail(f"{case['id']} exception grant source is not applicable")
    _validate_task_aggregation_inputs(case)
    for field in ("baseline_count", "current_count", "projected_count", "actual_count"):
        count = case[field]
        if count is not None and (
            isinstance(count, bool) or not isinstance(count, int) or count < 0
        ):
            fail(f"{case['id']} {field} is invalid")
    _validate_expected(case["expected"], case["id"])


def validate_contract(value: Any) -> dict[str, Any]:
    _exact_keys(value, TOP_KEYS, "contract")
    if (
        value["schema_version"] != 2
        or value["contract_revision"] != "APG60A"
        or value["supersedes_contract_sha256"] != APG60_CONTRACT_SHA256
        or value["candidate"] != "css-language-profile"
    ):
        fail("contract schema or candidate is invalid")
    if "pre-authoring contract" not in value["status"] or "not active guidance" not in value["status"]:
        fail("contract status boundary is invalid")
    _validate_policy(value)
    _validate_counting(value)
    cases = value["cases"]
    if not isinstance(cases, list) or len(cases) != 60:
        fail("contract must contain exactly sixty cases")
    expected_ids = [f"APG60-CSS-{number:03d}" for number in range(1, 61)]
    if [case.get("id") if isinstance(case, dict) else None for case in cases] != expected_ids:
        fail("case identifiers are not exact, continuous, and unique")
    for case in cases:
        _validate_case(case)
    if Counter(case["family"] for case in cases) != Counter(FAMILY_COUNTS):
        fail("case family counts differ from the frozen register")
    return value


def load_contract(path: Path, root: Path) -> dict[str, Any]:
    try:
        relative = path.relative_to(root).as_posix()
        with RepositoryPathContract(root) as repository:
            text = repository.read_text(relative)
        value = json.loads(text, object_pairs_hook=_strict_object)
    except (
        OSError,
        UnicodeError,
        ValueError,
        RepositoryPathError,
        json.JSONDecodeError,
    ) as error:
        fail(f"contract fixture is unreadable: {error}")
    validate_contract(value)
    return value


def classify_growth(count: int) -> str:
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        fail("growth count must be a nonnegative integer")
    if count < 300:
        return "Green"
    if count < 600:
        return "Yellow"
    if count < 900:
        return "Orange"
    return "Red"


def governing_growth(
    baseline: int | None,
    current: int | None,
    projected: int | None,
    actual: int | None,
) -> tuple[str, str]:
    states = (("actual", actual), ("projected", projected), ("current", current), ("baseline", baseline))
    available = [(name, classify_growth(count)) for name, count in states if count is not None]
    if not available:
        fail("at least one growth state is required")
    level = max((item[1] for item in available), key=LEVEL_ORDER.__getitem__)
    state = next(name for name, candidate in available if candidate == level)
    return level, state


def count_nonblank_css(content: bytes) -> int:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        fail("CSS content is not valid UTF-8")
    return sum(1 for line in text.splitlines() if line.strip())


def _result(
    growth: str,
    state: str,
    semantic: str,
    owner: str,
    permitted: bool,
    required: set[str],
    forbidden: set[str],
    rollback: bool,
) -> dict[str, Any]:
    return {
        "forbidden_actions": sorted(forbidden),
        "governing_state": state,
        "growth_level": growth,
        "permitted": permitted,
        "required_actions": sorted(required),
        "rollback": rollback,
        "selected_owner": owner,
        "semantic_level": semantic,
    }


def _projection_overrun(case: dict[str, Any]) -> bool:
    return (
        not case["exclusions"]
        and case["embedded_host"] is None
        and case["actual_count"] is not None
        and case["projected_count"] is not None
        and case["actual_count"] > case["projected_count"]
    )


def _projection_overrun_result(
    case: dict[str, Any], growth: str, state: str, semantic: str
) -> dict[str, Any]:
    forbidden = {"unplanned-material-growth"}
    if case["operation"] in {
        "non-growing-documentation",
        "smallest-safe-correction",
    }:
        forbidden.add("feature-as-correction")
    owner = "css-language-profile"
    if case["authority"] == "artifact-exception-valid":
        grant_source = case.get("exception_grant_source")
        if grant_source in EXCEPTION_GRANT_SOURCES:
            owner = grant_source
        forbidden.add("exception-scope-overrun")
    return _result(
        growth,
        state,
        semantic,
        owner,
        False,
        {"record-growth-state", "rollback", "stop-and-reauthorize"},
        forbidden,
        True,
    )


def _smallest_safe_response(
    case: dict[str, Any], growth: str
) -> tuple[set[str], set[str], bool, bool]:
    required = {
        "post-change-verification",
        "record-growth-state",
        "record-smallest-safe-correction",
    }
    forbidden: set[str] = set()
    rollback = growth in {"Orange", "Red"}
    if rollback:
        required |= {f"apply-{growth.lower()}-response", "rollback-plan"}
    if case["family"] == "growth-transition" and growth == "Red":
        forbidden.add("unplanned-material-growth")
    return required, forbidden, True, rollback


def _decomposition_response(
    growth: str,
) -> tuple[set[str], set[str], bool, bool]:
    required = {
        f"apply-{growth.lower()}-response",
        "post-change-verification",
        "record-growth-state",
    }
    if growth == "Red":
        required.add("decompose-first")
    return required, set(), True, growth in {"Orange", "Red"}


def _bounded_operation_response(
    case: dict[str, Any], growth: str
) -> tuple[set[str], set[str], bool, bool] | None:
    operation = case["operation"]
    if operation == "non-growing-documentation":
        return (
            {"post-change-verification", "record-growth-state"},
            {"feature-as-correction"}, True, False,
        )
    if operation == "smallest-safe-correction":
        return _smallest_safe_response(case, growth)
    if operation == "decomposition-or-removal":
        return _decomposition_response(growth)
    return None


def _material_growth_response(
    growth: str,
) -> tuple[set[str], set[str], bool, bool]:
    required = {"record-growth-state"}
    forbidden: set[str] = set()
    permitted, rollback = True, False
    if growth == "Green":
        required.add("proceed-project-conventions")
    elif growth == "Yellow":
        required |= {
            "apply-yellow-response", "bound-new-responsibility", "focused-validation",
            "identify-extraction-seams", "name-responsibility",
        }
    elif growth == "Orange":
        required |= {
            "apply-orange-response", "containment-or-decomposition-plan", "focused-validation",
            "justify-isolation-order", "name-new-responsibility", "rollback-plan",
        }
        forbidden.add("unplanned-material-growth")
        rollback = True
    else:
        required |= {
            "apply-red-response", "decompose-first", "request-bounded-exception",
            "stop-material-growth",
        }
        forbidden.add("material-red-growth")
        permitted, rollback = False, True
    return required, forbidden, permitted, rollback


def _growth_response(case: dict[str, Any], growth: str, state: str, semantic: str) -> dict[str, Any]:
    if _projection_overrun(case):
        return _projection_overrun_result(case, growth, state, semantic)
    response = _bounded_operation_response(case, growth)
    if response is None:
        response = _material_growth_response(growth)
    required, forbidden, permitted, rollback = response
    return _result(
        growth, state, semantic, "css-language-profile",
        permitted, required, forbidden, rollback,
    )


def _all_commit_parts(parts: list[str]) -> bool:
    return len(parts) > 1 and all(part.startswith("commit-") for part in parts)


def _cross_file_commits(parts: list[str]) -> bool:
    commits = sum(part.startswith("commit-") for part in parts)
    files = sum(part.startswith("file-") for part in parts)
    return commits > 1 and files > 1


def _several_conversational_turns(parts: list[str]) -> bool:
    return sum(part.startswith("conversation-turn-") for part in parts) > 1


def _several_tool_calls(parts: list[str]) -> bool:
    return sum(part.startswith("tool-call-") for part in parts) > 1


def _task_adjustments(
    case: dict[str, Any], required: set[str], forbidden: set[str]
) -> tuple[set[str], set[str]]:
    parts = case["input"]["parts"]
    responsibility = case["input"]["responsibility"]
    facts = set(case["semantic_facts"])
    if _all_commit_parts(parts):
        forbidden |= {"baseline-reset", "salami-slicing"}
        return required, forbidden
    if "claimed-fix" in parts and case["operation"] == "material-new-behavior":
        forbidden.add("feature-as-correction")
        return required, forbidden
    if (
        case["operation"] == "smallest-safe-correction"
        and responsibility == "correctness-repair"
    ):
        forbidden.add("feature-as-correction")
        return required, forbidden
    if responsibility == "two-independent-repairs":
        required.add("classify-independent-responsibilities")
        forbidden.add("baseline-reset")
        return required, forbidden
    if "formatting-churn" in parts:
        required = {"apply-orange-response", "post-change-verification", "preserve-task-baseline", "record-growth-state"}
        forbidden = {"baseline-reset"}
        return required, forbidden
    if "indirect-growth" in facts or _cross_file_commits(parts):
        forbidden.add("salami-slicing")
    return required, forbidden


def _task_result(case: dict[str, Any], growth: str, state: str, semantic: str) -> dict[str, Any]:
    facts = set(case["semantic_facts"])
    if "baseline-reset-attempt" in facts:
        return _result(
            growth, state, semantic, "css-language-profile", False,
            {"aggregate-complete-task", "preserve-task-baseline", "record-growth-state"},
            {"baseline-reset"}, True,
        )
    result = _growth_response(case, growth, state, semantic)
    required = set(result["required_actions"]) | {
        "aggregate-complete-task", "preserve-task-baseline"
    }
    forbidden = set(result["forbidden_actions"])
    required, forbidden = _task_adjustments(case, required, forbidden)
    result["required_actions"] = sorted(required)
    result["forbidden_actions"] = sorted(forbidden)
    return result


def _authority_result(case: dict[str, Any], growth: str, state: str) -> dict[str, Any]:
    authority = case["authority"]
    facts = set(case["semantic_facts"])
    if authority == "general-default":
        return _result(growth, state, "Green", "css-language-profile", True, {"proceed-project-conventions", "record-growth-state"}, set(), False)
    if authority in {"repository-stricter", "conflict-no-human-supersession"}:
        forbidden = {"unplanned-material-growth"} if authority == "repository-stricter" else {"implicit-weaker-convention"}
        return _result(growth, state, "Green", "repository-policy", False, {"apply-repository-policy", "record-growth-state", "stop-material-growth"}, forbidden, True)
    if authority == "repository-weaker-explicit":
        return _result(growth, state, "Green", "repository-policy", True, {"apply-repository-policy", "focused-validation", "record-growth-state", "rollback-plan"}, {"implicit-weaker-convention"}, True)
    if authority == "human-bounded-supersession" and "valid-exception" in facts:
        return _result(growth, state, "Green", "human-instruction", True, {"apply-task-instruction", "focused-validation", "record-growth-state", "rollback-plan", "validate-bounded-exception"}, {"exception-scope-overrun"}, True)
    if authority == "incidental-weaker":
        base = _growth_response(case, growth, state, "Green")
        base["required_actions"] = sorted(set(base["required_actions"]) | {"reject-incidental-override"})
        base["forbidden_actions"] = sorted(set(base["forbidden_actions"]) | {"implicit-weaker-convention"})
        return base
    if authority == "artifact-exception-valid" and "valid-exception" in facts:
        grant_source = case.get("exception_grant_source")
        if grant_source in EXCEPTION_GRANT_SOURCES:
            source_action = (
                "apply-repository-policy"
                if grant_source == "repository-policy"
                else "apply-task-instruction"
            )
            return _result(
                growth,
                state,
                "Green",
                grant_source,
                True,
                {
                    source_action,
                    "focused-validation",
                    "record-growth-state",
                    "rollback-plan",
                    "validate-bounded-exception",
                },
                {"exception-scope-overrun"},
                True,
            )
        return _result(
            growth,
            state,
            "Green",
            "css-language-profile",
            False,
            {"record-growth-state", "rollback", "stop-and-reauthorize"},
            {"implicit-weaker-convention"},
            True,
        )
    return _growth_response(case, growth, state, "Green")


SEMANTIC_RESULTS: dict[str, tuple[str, str, bool, set[str], set[str], bool]] = {
    "established-motion-bypass": ("Red", "css-language-profile", False, {"restore-established-condition", "rollback", "stop-material-growth"}, {"css-final-accessibility-acceptance"}, True),
    "unknown-accessibility-acceptance": ("Yellow", "css-language-profile", True, {"escalate-project-acceptance", "explain-css-behavior", "record-growth-state"}, {"css-final-accessibility-acceptance", "invent-accessibility-requirement"}, False),
    "established-focus-suppression": ("Red", "css-language-profile", False, {"restore-established-condition", "rollback", "stop-material-growth"}, {"css-final-accessibility-acceptance"}, True),
    "ordinary-transition": ("Green", "css-language-profile", True, {"explain-css-behavior", "proceed-project-conventions", "record-growth-state"}, {"invent-accessibility-requirement"}, False),
    "intentional-root-token": ("Green", "css-language-profile", True, {"proceed-project-conventions", "record-growth-state"}, {"global-scope-only-escalation"}, False),
    "component-token-widened": ("Orange", "css-language-profile", True, {"focused-validation", "name-responsibility", "record-growth-state", "rollback-plan"}, {"token-value-ownership"}, True),
    "global-token-value": ("NotApplicable", "project-policy", True, {"return-decision-to-project"}, {"token-value-ownership"}, False),
    "fallback-cascade-defect": ("Orange", "css-language-profile", True, {"focused-validation", "post-change-verification", "record-smallest-safe-correction", "rollback-plan"}, set(), True),
    "color-brand-choice": ("NotApplicable", "project-design", True, {"return-decision-to-project"}, {"token-value-ownership"}, False),
    "browser-support-choice": ("Yellow", "project-policy", True, {"explain-css-behavior", "return-decision-to-project"}, set(), False),
}


def _semantic_key(case: dict[str, Any]) -> str:
    facts = set(case["semantic_facts"])
    requirements = set(case["established_requirements"])
    if "bypasses-established-condition" in facts:
        if not requirements:
            return "unknown-accessibility-acceptance"
        if case["input"]["responsibility"] == "focus-style":
            return "established-focus-suppression"
        return "established-motion-bypass"
    fact_keys = {
        "accessibility-acceptance-unknown": "unknown-accessibility-acceptance",
        "ordinary-transition": "ordinary-transition",
        "documented-root-token": "intentional-root-token",
        "silent-global-ownership-move": "component-token-widened",
        "project-token-value": "global-token-value",
        "fallback-cascade-defect": "fallback-cascade-defect",
        "project-design-choice": "color-brand-choice",
        "project-browser-support": "browser-support-choice",
    }
    matches = [result for fact, result in fact_keys.items() if fact in facts]
    if len(matches) != 1:
        fail("semantic case facts do not select exactly one behavior")
    return matches[0]


def _semantic_result(case: dict[str, Any], growth: str, state: str) -> dict[str, Any]:
    semantic, owner, permitted, required, forbidden, rollback = SEMANTIC_RESULTS[_semantic_key(case)]
    return _result(growth, state, semantic, owner, permitted, required, forbidden, rollback)


def _count_result(case: dict[str, Any], growth: str, state: str) -> dict[str, Any]:
    if case["exclusions"]:
        return _result("Excluded", "exclusion", "NotApplicable", "css-language-profile", True, {"exclude-artifact"}, {"edit-excluded-artifact"}, False)
    if case["embedded_host"] is not None:
        return _result("NotApplicable", "host-one-count", "Green", "css-language-profile", True, {"css-semantic-review", "host-one-count"}, {"additive-embedded-count"}, False)
    return _result(growth, state, "Green", "css-language-profile", True, {"record-growth-state"}, set(), False)


def _legacy_result(case: dict[str, Any], growth: str, state: str) -> dict[str, Any]:
    facts = set(case["semantic_facts"])
    if "valid-exception" in facts and case["authority"] == "human-bounded-supersession":
        return _result(growth, state, "Green", "human-instruction", True, {"apply-task-instruction", "focused-validation", "record-growth-state", "rollback-plan", "validate-bounded-exception"}, {"exception-scope-overrun"}, True)
    if "exception-overrun" in facts:
        return _result(growth, state, "Green", "human-instruction", False, {"record-growth-state", "rollback", "stop-and-reauthorize"}, {"exception-scope-overrun", "material-red-growth"}, True)
    result = _growth_response(case, growth, state, "Yellow" if "named-correctness-defect" in facts else "Green")
    if "named-correctness-defect" in facts:
        result["forbidden_actions"] = ["feature-as-correction"]
    elif "cohesive" in facts:
        result["forbidden_actions"] = sorted(set(result["forbidden_actions"]) | {"cohesion-as-exception"})
    return result


LIFECYCLE_RESULTS: dict[str, tuple[bool, set[str], set[str], bool]] = {
    "retained-state": (True, {"derive-counts-from-live-inventory"}, set(), False),
    "rejected-state": (True, {"derive-counts-from-live-inventory", "preserve-historical-evidence", "remove-current-owner", "repair-surviving-reference"}, {"delete-historical-evidence", "raw-historical-revert", "stale-current-reference"}, False),
    "stale-project-owner": (False, {"remove-current-owner", "repair-surviving-reference"}, {"stale-current-reference"}, True),
    "stale-release-owner": (False, {"remove-current-owner", "repair-surviving-reference"}, {"stale-current-reference"}, True),
    "stale-current-owner": (False, {"remove-current-owner", "repair-surviving-reference"}, {"stale-current-reference"}, True),
    "history-preserved": (True, {"preserve-historical-evidence"}, {"delete-historical-evidence", "raw-historical-revert"}, False),
}


def _lifecycle_result(case: dict[str, Any]) -> dict[str, Any]:
    matches = [
        LIFECYCLE_RESULTS[fact]
        for fact in case["semantic_facts"]
        if fact in LIFECYCLE_RESULTS
    ]
    if len(matches) != 1:
        fail("lifecycle facts do not select exactly one behavior")
    permitted, required, forbidden, rollback = matches[0]
    return _result(
        "NotApplicable", "lifecycle", "NotApplicable", "removal-closure",
        permitted, required, forbidden, rollback,
    )


def _case_growth(case: dict[str, Any]) -> tuple[str, str]:
    if case["exclusions"]:
        return "Excluded", "exclusion"
    if case["embedded_host"] is not None:
        return "NotApplicable", "host-one-count"
    return governing_growth(
        case["baseline_count"], case["current_count"],
        case["projected_count"], case["actual_count"],
    )


def _dispatch_case(
    case: dict[str, Any], growth: str, state: str, semantic: str
) -> dict[str, Any]:
    dispatch = {
        "growth-transition": lambda: _growth_response(case, growth, state, semantic),
        "task-aggregation": lambda: _task_result(case, growth, state, semantic),
        "authority": lambda: _authority_result(case, growth, state),
        "semantic-owner": lambda: _semantic_result(case, growth, state),
        "one-count-exclusions": lambda: _count_result(case, growth, state),
        "legacy-exception": lambda: _legacy_result(case, growth, state),
    }
    handler = dispatch.get(case["family"])
    if handler is None:
        fail(f"unsupported case family: {case['family']}")
    return handler()


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one structured case without consulting its expected result."""
    if not isinstance(case, dict) or not CASE_KEYS <= set(case):
        fail("case schema is incomplete")
    _validate_task_aggregation_inputs(case)
    if case["family"] == "lifecycle-removal":
        return _lifecycle_result(case)
    growth, state = _case_growth(case)
    semantic = "Yellow" if "named-correctness-defect" in case["semantic_facts"] else "Green"
    if _projection_overrun(case) and "exception-overrun" not in case["semantic_facts"]:
        return _projection_overrun_result(case, growth, state, semantic)
    return _dispatch_case(case, growth, state, semantic)


def assert_case_expected(case: dict[str, Any]) -> None:
    if evaluate_case(case) != case.get("expected"):
        fail(f"{case.get('id', 'case')} expected result does not match executable behavior")


def validate_collected_case_ids(contract: dict[str, Any], collected: list[str]) -> None:
    expected = [case["id"] for case in contract["cases"]]
    if collected != expected:
        fail("case collection is incomplete, reordered, duplicated, or stale")
