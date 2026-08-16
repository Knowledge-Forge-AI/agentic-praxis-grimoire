"""Mechanical APG81 contract for the Node.js candidate and scenario owner."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any, NoReturn


SELECTIONS = {"selected", "embedded-route", "route-to-owner", "non-trigger"}
RESPONSES = {
    "proceed-routine",
    "inspect-before-judgment",
    "bounded-local-decision",
    "stop-and-escalate",
}
COMPLETION_STATES = {
    "owned-complete",
    "owned-complete-nonowned-routes-open",
    "stopped-required-evidence",
}
ABSENT_RECEIVERS = {
    "browser-platform-owner",
    "build-transform-owner",
    "deployment-owner",
    "filesystem-owner",
    "network-owner",
    "operating-system-owner",
    "package-manager-owner",
    "performance-owner",
    "security-owner",
    "service-supervisor-owner",
    "shell-owner",
    "test-owner",
}
SCENARIO_IDS = tuple(f"APG80-NODE-{index:03d}" for index in range(1, 25))
CLAUSE_RE = re.compile(r"<!-- APG-CLAUSE: (NODE-[A-Z0-9-]+) -->")
SCENARIO_PROJECTION_SHA256 = "e72cd3464027f4a34b60bf5c9e4edcd63e1105977ea3a5d31bcde2ffa62e0f34"
COVERAGE_CLAUSE_PROJECTION = (
    ("APG80-NODE-001", ("NODE-TRIGGER", "NODE-SELECTION", "NODE-RESPONSE")),
    ("APG80-NODE-002", ("NODE-RUNTIME-ROLE", "NODE-FLAGS-PERMISSIONS")),
    ("APG80-NODE-003", ("NODE-MODULE-MAPPING",)),
    ("APG80-NODE-004", ("NODE-MODULE-MAPPING", "NODE-COMMONJS")),
    ("APG80-NODE-005", ("NODE-PACKAGE-SCOPE",)),
    ("APG80-NODE-006", ("NODE-PACKAGE-SCOPE", "NODE-MODULE-MAPPING")),
    ("APG80-NODE-007", ("NODE-MODULE-MAPPING", "NODE-UNKNOWN-STOP")),
    ("APG80-NODE-008", ("NODE-COMMONJS",)),
    ("APG80-NODE-009", ("NODE-ESM",)),
    ("APG80-NODE-010", ("NODE-RESOLUTION",)),
    ("APG80-NODE-011", ("NODE-RESOLUTION", "NODE-ESM")),
    ("APG80-NODE-012", ("NODE-INTEROP",)),
    ("APG80-NODE-013", ("NODE-CACHE",)),
    ("APG80-NODE-014", ("NODE-PACKAGE-MANAGER-BOUNDARY",)),
    ("APG80-NODE-015", ("NODE-PACKAGE-MANAGER-BOUNDARY", "NODE-NONTRIGGER")),
    ("APG80-NODE-016", ("NODE-CLI-ENTRY",)),
    ("APG80-NODE-017", ("NODE-PROCESS-STATE", "NODE-EVIDENCE")),
    ("APG80-NODE-018", ("NODE-STDIO-STREAMS", "NODE-ERRORS-EXIT")),
    ("APG80-NODE-019", ("NODE-FILESYSTEM",)),
    ("APG80-NODE-020", ("NODE-ERRORS-EXIT", "NODE-SIGNALS-LIFECYCLE")),
    ("APG80-NODE-021", ("NODE-EVENT-LOOP",)),
    ("APG80-NODE-022", ("NODE-CHILD-PROCESS", "NODE-WORKERS")),
    ("APG80-NODE-023", ("NODE-NETWORK-WEBAPI", "NODE-ROUTES")),
    ("APG80-NODE-024", ("NODE-STATIC-RUNTIME-COMPLETION", "NODE-STRUCTURE-DEFERRED")),
)
ROLLBACK_LIFECYCLE = "accepted-integration-rolled-back"
ACCEPTED_ADR_STATUS = "Accepted with amendment"
ROLLBACK_INTEGRATION_OWNERS = {
    "capability_route",
    "catalog",
    "current_development_release",
    "maintained_integration_test",
    "maturity",
    "project_selection",
    "projection",
    "test_inventory",
}


class ContractError(ValueError):
    """A maintained Node candidate surface is malformed."""


def fail(message: str) -> NoReturn:
    raise ContractError(message)


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            fail(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def load_scenarios(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_object)
    validate_scenarios(value)
    return value


def validate_scenarios(value: Any) -> None:
    if not isinstance(value, dict) or set(value) != {
        "authority", "receivers", "rows", "schema_version"
    }:
        fail("Node scenario top-level schema is invalid")
    if value["schema_version"] != 1:
        fail("Node scenario schema version is invalid")
    projection = json.dumps(
        value, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    if hashlib.sha256(projection).hexdigest() != SCENARIO_PROJECTION_SHA256:
        fail("Node scenario exact authority projection is invalid")
    authority = value["authority"]
    if not isinstance(authority, dict) or authority.get("scenario_purposes") != 24:
        fail("Node scenario purpose authority is invalid")
    if authority.get("fixture_cases") != 14:
        fail("Node fixture-case authority is invalid")
    if authority.get("candidate_state") != "provisionally-integrated":
        fail("Node candidate lifecycle state is invalid")
    if authority.get("current_phase_id") != "APG81H":
        fail("Node current correction phase is invalid")
    if authority.get("round_state") != "terminal-repair-checkpoint-complete":
        fail("Node correction round state is invalid")
    runtimes = authority.get("runtime_roles")
    if not isinstance(runtimes, list) or [item.get("role") for item in runtimes] != [
        "primary", "secondary"
    ]:
        fail("Node runtime roles are not exact and ordered")
    expected_versions = ["v22.22.2", "v24.19.0"]
    if [item.get("version") for item in runtimes] != expected_versions:
        fail("Node runtime versions are invalid")
    expected_runtime_states = [
        ("exact-closed-synthetic-allowlist", "observed-exact-pre-and-post-runtime", "existing-exact-path"),
        ("exact-closed-synthetic-allowlist", "observed-exact-pre-and-post-runtime", "preinstalled-nvm-exact-version"),
    ]
    if [
        (item.get("invocation_environment"), item.get("invocation_state"), item.get("selection_source"))
        for item in runtimes
    ] != expected_runtime_states:
        fail("Node runtime observation boundary is invalid")
    targets = authority.get("target_pins")
    if not isinstance(targets, list) or [item.get("tracked_leaf_entries") for item in targets] != [17, 69]:
        fail("fresh target tracked-leaf facts are invalid")
    if any(item.get("target_execution_state") != "not-observed" for item in targets):
        fail("target execution must remain unobserved")
    receivers = value["receivers"]
    if not isinstance(receivers, list) or {item.get("owner") for item in receivers} != ABSENT_RECEIVERS:
        fail("absent receiver owner set is invalid")
    for receiver in receivers:
        if set(receiver) != {"availability", "owner", "required_evidence", "scope", "stop_state"}:
            fail("receiver state schema is invalid")
        if receiver["availability"] != "absent" or receiver["stop_state"] != "stopped-required-evidence":
            fail("an absent receiver is presented as live or complete")
        if not receiver["required_evidence"]:
            fail("an absent receiver lacks required evidence")
    rows = value["rows"]
    if not isinstance(rows, list) or tuple(row.get("id") for row in rows) != SCENARIO_IDS:
        fail("Node scenario row identities are invalid")
    for row in rows:
        if set(row) != {
            "completion_state", "fixture_case", "id", "response", "selection", "whole_file_owner"
        }:
            fail(f"Node scenario row schema is invalid: {row.get('id')}")
        if row["selection"] not in SELECTIONS or row["response"] not in RESPONSES:
            fail(f"Node scenario state vocabulary is invalid: {row['id']}")
        if row["completion_state"] not in COMPLETION_STATES:
            fail(f"Node scenario completion state is invalid: {row['id']}")
        if row["response"] == "stop-and-escalate" and row["completion_state"] != "stopped-required-evidence":
            fail(f"stopped Node scenario appears complete: {row['id']}")


def validate_candidate(leaf: str, specification: str, coverage: str) -> None:
    if leaf.count("name: nodejs-runtime-profile") != 1:
        fail("Node leaf name is missing or duplicated")
    clauses = CLAUSE_RE.findall(leaf)
    if len(clauses) != 30 or len(set(clauses)) != 30:
        fail("Node leaf must retain 30 unique stable clauses")
    required_spec_tokens = (
        "e4bf922d83b877a116763e2f83d2d9b6701871f9",
        "3a6af719fb943a16a672eeb81dec0a04500d7a59",
        "v24.19.0",
        "27db838bb204ef7c21df2931f5656e4c8fb32e6e947f363a402b49714d32b5b1",
        "8294b7aa9b03997481c06babf1e8b270c859358f27da57a11509afe537ac381d",
        "69 recursive tracked leaf",
        "Rollback is history preserving",
        "ADR 0046, APG80/APG81/APG81A commits and records",
    )
    for token in required_spec_tokens:
        if token not in specification:
            fail(f"Node specification omits corrected contract: {token}")
    forbidden = (
        "with 71 tracked paths",
        "Removing those paths removes the candidate",
    )
    for token in forbidden:
        if token in specification:
            fail(f"Node specification retains rejected contract: {token}")
    coverage_ids = tuple(re.findall(r"^\| `(APG80-NODE-[0-9]{3})` \|", coverage, re.MULTILINE))
    if coverage_ids != SCENARIO_IDS:
        fail("Node coverage navigation identities are invalid")
    clause_projection = []
    for line in coverage.splitlines():
        if not line.startswith("| `APG80-NODE-"):
            continue
        cells = tuple(cell.strip() for cell in line.strip().strip("|").split("|"))
        clause_projection.append(
            (cells[0].strip("`"), tuple(re.findall(r"`(NODE-[A-Z0-9-]+)`", cells[2])))
        )
    if tuple(clause_projection) != COVERAGE_CLAUSE_PROJECTION:
        fail("Node coverage scenario-to-clause projection is invalid")
    coverage_clauses = set(re.findall(r"`(NODE-[A-Z0-9-]+)`", coverage))
    if coverage_clauses != set(clauses):
        fail("Node coverage clauses do not match the exact leaf marker set")
    if "NODE-ROLLBACK" not in coverage or "operational-only" not in coverage:
        fail("Node operational-only rollback clause is unowned")


def validate_rollback_lifecycle(value: Any) -> None:
    """Validate one observed candidate-preserving post-acceptance rollback."""

    if not isinstance(value, dict) or set(value) != {
        "adr_file_status",
        "adr_index_status",
        "candidate_lifecycle",
        "candidate_present",
        "counts",
        "historical_proposed_provenance_present",
        "integration_owners",
        "schema_version",
    }:
        fail("Node rollback lifecycle schema is invalid")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        fail("Node rollback lifecycle schema version is invalid")
    if value["adr_file_status"] != ACCEPTED_ADR_STATUS or value["adr_index_status"] != ACCEPTED_ADR_STATUS:
        fail("Node rollback must preserve the accepted ADR decision")
    if value["candidate_present"] is not True:
        fail("Node rollback must retain the candidate")
    lifecycle = value["candidate_lifecycle"]
    if not isinstance(lifecycle, dict) or set(lifecycle) != {
        "fixture_manifest", "leaf", "scenario_authority", "specification"
    }:
        fail("Node rollback candidate lifecycle surfaces are invalid")
    if set(lifecycle.values()) != {ROLLBACK_LIFECYCLE}:
        fail("Node rollback candidate lifecycle surfaces disagree")
    owners = value["integration_owners"]
    if not isinstance(owners, dict) or set(owners) != ROLLBACK_INTEGRATION_OWNERS:
        fail("Node rollback integration-owner projection is invalid")
    if any(owner_present is not False for owner_present in owners.values()):
        fail("Node rollback retains a current integration owner")
    counts = value["counts"]
    expected_counts = {
        "canonical": 33,
        "catalog": 32,
        "chatgpt_local_routes": 1,
        "checked_routes": 31,
        "general_routes": 30,
        "projections": 32,
        "provisional": 18,
        "stable": 14,
    }
    if (
        not isinstance(counts, dict)
        or set(counts) != set(expected_counts)
        or any(type(count) is not int for count in counts.values())
        or counts != expected_counts
    ):
        fail("Node rollback resulting counts are invalid")
    if value["historical_proposed_provenance_present"] is not True:
        fail("Node rollback loses historical Proposed provenance")


def validate_review_sequence(value: Any) -> None:
    """Validate staged review without requiring a tree to attest to itself."""

    if not isinstance(value, dict) or set(value) != {
        "commit_message_review_claim",
        "external_review_identity",
        "external_review_state",
        "repository_review_state",
        "schema_version",
        "staged_identity",
    }:
        fail("Node staged-review sequencing schema is invalid")
    if (
        type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or value["repository_review_state"] != "review-target-frozen"
    ):
        fail("Node repository review target is not frozen")
    staged_identity = value["staged_identity"]
    if not isinstance(staged_identity, str) or re.fullmatch(r"[0-9a-f]{64}", staged_identity) is None:
        fail("Node staged-review identity is invalid")
    state = value["external_review_state"]
    identity = value["external_review_identity"]
    message_claim = value["commit_message_review_claim"]
    if state == "not-run":
        if identity is not None or message_claim is not False:
            fail("Node message claims review completion before external review")
        return
    if state != "zero-findings" or identity != staged_identity or message_claim is not True:
        fail("Node external staged-review binding is invalid")
