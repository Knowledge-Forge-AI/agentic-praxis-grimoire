"""Maintained structural contract for APG77A CSS evidence retention."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any, NoReturn

from apg_css_profile_fixture_contract import (
    FixtureError,
    validate_css_known_debt as validate_public_css_known_debt,
)


SELECTIONS = ("selected", "embedded-route", "route-to-owner", "non-trigger")
RESPONSES = (
    "proceed-routine",
    "inspect-before-judgment",
    "bounded-local-decision",
    "stop-and-escalate",
)
PURPOSE_IDS = (
    *(f"APG77-CSS-{index:03d}" for index in range(1, 25)),
    *(f"APG77-FX-{index:03d}" for index in range(1, 15)),
    *(f"APG77-TARGET-{index:03d}" for index in range(1, 8)),
)
TARGET_KEYS = {
    "commit",
    "commit_parent_count",
    "default_branch",
    "fetch_time_utc",
    "fetched_ref",
    "inventory_counts",
    "license_boundary",
    "lock_paths",
    "manifest_paths",
    "path_objects",
    "remote_identity",
    "repository_role",
    "script_sources",
    "target_key",
    "tracked_path_count",
    "tree",
}
IDENTITY_KEYS = {
    "byte_size",
    "format",
    "git_mode",
    "git_object",
    "git_type",
    "path",
    "semantic_role",
    "sha256",
}
PATH_KEYS = {
    "artifact_class",
    "byte_size",
    "git_mode",
    "git_object",
    "git_type",
    "inventory_relevance",
    "path",
    "sha256",
}
VECTOR_KEYS = {
    "artifact_class",
    "css_selection",
    "edit_permission",
    "id",
    "independent_reasoning_summary",
    "input_class",
    "nonowned_conclusion",
    "normative_authorities",
    "owned_conclusion",
    "present_evidence",
    "purpose",
    "required_evidence",
    "response",
    "rollback_or_provenance",
    "routes_or_obligations",
    "stop_or_completion_state",
    "tool_or_target_authorities",
    "uncertainty_or_limit",
    "whole_file_owner",
}
ARRAY_FIELDS = {
    "normative_authorities",
    "present_evidence",
    "required_evidence",
    "routes_or_obligations",
    "tool_or_target_authorities",
}
FORBIDDEN_LANE_PATTERNS = (
    r"\binherit(?:ed)? from (?:another|other|lane)\b",
    r"\bsame as lane [nt]\b",
    r"\bsame as other lane\b",
    r"\bsee other lane\b",
    r"\bditto\b",
    r"\bshared above\b",
    r"\bcommon fields\b",
    r"\buse canonical row\b",
    r"\bcopy from resolved vector\b",
)
HEX40 = re.compile(r"[0-9a-f]{40}")
HEX64 = re.compile(r"[0-9a-f]{64}")
MODE = re.compile(r"(?:100644|100755|120000|160000)")
TRACE_PREFIX = "<!-- APG77A-RESOLVED-TRACEABILITY:"
TRACE_SUFFIX = "-->"
PRIVATE_BINDING_PREFIX = "<!-- APG77D-PRIVATE-SOURCE-BINDINGS:"
PRIVATE_BINDING_SUFFIX = "-->"
PRIVATE_BINDING_COMMITMENT_SHA256 = (
    "bc1681fcc5bf27547544d3ab6e9994edc64c5b2a19bcb3fe61409333c0ea801e"
)
TRACE_SOURCES = {"N", "T", "A"}
REGISTRY_KEYS = {
    "boundary_definitions",
    "phase",
    "purpose_counts",
    "purposes",
    "registry_boundary",
    "schema_version",
    "source_registry",
    "target_fact_cards",
}
PURPOSE_KEYS = {
    "allowed_target_fact_card",
    "canonical_purpose",
    "copying_boundary",
    "id",
    "purpose_sha256",
    "required_identity_keys",
    "row_class",
    "source_class_boundary",
}
FACT_CARD_KEYS = {
    "artifact_class",
    "factual_observations",
    "host_embedded_region_class",
    "id",
    "identities",
    "purpose_id",
    "relevant_source_authority_questions",
    "repository_roots",
    "required_evidence_still_absent",
}
TOMBSTONE_KEYS = {
    "historical_commit",
    "historical_sha256",
    "historical_status",
    "phase",
    "reason",
    "replacement",
    "schema_version",
}
RESOLVED_TO_LANE_FIELD = {
    "artifact_class": "artifact_class",
    "authority": "normative_authorities",
    "conclusion": "owned_conclusion",
    "css_selection": "css_selection",
    "edit": "edit_permission",
    "forbid": "nonowned_conclusion",
    "id": "id",
    "present": "present_evidence",
    "purpose": "purpose",
    "required": "required_evidence",
    "response": "response",
    "routes": "routes_or_obligations",
    "whole_file_owner": "whole_file_owner",
}
UNPROJECTED_LANE_FIELDS = {
    "independent_reasoning_summary",
    "input_class",
    "rollback_or_provenance",
    "stop_or_completion_state",
    "tool_or_target_authorities",
    "uncertainty_or_limit",
}
class EvidenceContractError(ValueError):
    """The retained APG77A evidence is malformed or incomplete."""


def fail(message: str) -> NoReturn:
    raise EvidenceContractError(message)


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            fail(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def canonical_json(value: Any) -> str:
    """Return the compact canonical encoding owned by the APG77A evidence."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"


def load_json(path: Path) -> Any:
    """Load one direct regular canonical JSON evidence file."""
    if path.is_symlink() or not path.is_file():
        fail(f"evidence file is absent or not direct regular: {path.name}")
    try:
        text = path.read_text(encoding="utf-8")
        value = json.loads(text, object_pairs_hook=_strict_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        fail(f"evidence file is invalid: {error}")
    if text != canonical_json(value):
        fail("evidence file is not compact canonical JSON")
    return value


def validate_css_known_debt(value: Any) -> dict[str, int]:
    """Preserve the development API while delegating public debt validation."""
    try:
        return validate_public_css_known_debt(value)
    except FixtureError as error:
        fail(str(error))


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def value_sha256(value: Any) -> str:
    """Hash one value without adding a presentation-only trailing newline."""
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()


def load_traceability(path: Path) -> Any:
    """Load the one canonical JSON traceability record embedded in Markdown."""
    if path.is_symlink() or not path.is_file():
        fail("traceability record is absent or not direct regular")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        fail(f"traceability record is unreadable: {error}")
    records = [
        line[len(TRACE_PREFIX):-len(TRACE_SUFFIX)]
        for line in lines
        if line.startswith(TRACE_PREFIX) and line.endswith(TRACE_SUFFIX)
    ]
    if len(records) != 1:
        fail("traceability record count is not one")
    payload = records[0]
    try:
        value = json.loads(payload, object_pairs_hook=_strict_object)
    except json.JSONDecodeError as error:
        fail(f"traceability record is invalid: {error}")
    if payload != canonical_json(value).rstrip("\n"):
        fail("traceability record is not compact canonical JSON")
    return value


def _relative_path(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value:
        fail(f"{context} must be a nonempty path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "\\" in value:
        fail(f"{context} must be normalized and relative")
    if value != path.as_posix() or value.startswith(("Users/", "home/", "private/var/")):
        fail(f"{context} exposes an unsafe local path")
    return value


def _strings(value: Any, context: str, *, allow_empty: bool = False) -> list[str]:
    if (
        not isinstance(value, list)
        or (not allow_empty and not value)
        or any(not isinstance(item, str) or not item or item != item.strip() for item in value)
        or len(value) != len(set(value))
    ):
        fail(f"{context} must be a normalized duplicate-free string array")
    return value


def _source_basis(value: Any) -> None:
    if not isinstance(value, list) or not value:
        fail("lane source basis must be a nonempty array")
    records: list[str] = []
    for source in value:
        if not isinstance(source, dict) or not source:
            fail("lane source basis record is incomplete")
        _complete_value(source, "lane source basis record")
        records.append(canonical_json(source))
    if len(records) != len(set(records)):
        fail("lane source basis records are duplicated")


def _complete_value(value: Any, context: str) -> None:
    """Reject null or empty evidence while preserving lane-owned structure."""
    if isinstance(value, str):
        if not value.strip():
            fail(f"{context} contains an empty string")
        return
    if isinstance(value, bool) or isinstance(value, int):
        return
    if isinstance(value, list):
        if not value:
            fail(f"{context} contains an empty array")
        for item in value:
            _complete_value(item, context)
        return
    if isinstance(value, dict):
        if not value or any(not isinstance(key, str) or not key for key in value):
            fail(f"{context} contains an incomplete object")
        for item in value.values():
            _complete_value(item, context)
        return
    fail(f"{context} contains an unsupported value")


def iter_strings(value: Any) -> list[str]:
    """Collect string leaves for generalized clean-room overlap inspection."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for child in value for item in iter_strings(child)]
    if isinstance(value, dict):
        return [item for child in value.values() for item in iter_strings(child)]
    return []


def _decoded_candidate_forms(candidate: str) -> list[bytes]:
    """Decode exactly the maintained no-copy representation contract."""
    forms = [candidate.encode("utf-8")]
    try:
        if len(candidate) % 4 == 0:
            forms.append(base64.b64decode(candidate, validate=True))
    except (ValueError, binascii.Error):
        pass
    for token in re.findall(r"[A-Za-z0-9+/]{43,}={0,2}", candidate):
        try:
            forms.append(base64.b64decode(token, validate=True))
        except (ValueError, binascii.Error):
            pass
    try:
        if len(candidate) % 2 == 0:
            forms.append(bytes.fromhex(candidate))
    except ValueError:
        pass
    for token in re.findall(r"[0-9A-Fa-f]{64,}", candidate):
        try:
            forms.append(bytes.fromhex(token))
        except ValueError:
            pass
    for token in re.findall(r"(?:\\x[0-9A-Fa-f]{2}){16,}", candidate):
        forms.append(bytes(int(token[index + 2:index + 4], 16) for index in range(0, len(token), 4)))
    for token in re.findall(r"(?:\\u[0-9A-Fa-f]{4}){8,}", candidate):
        try:
            decoded = json.loads('"' + token + '"')
            forms.append(decoded.encode("utf-8"))
        except (json.JSONDecodeError, UnicodeEncodeError):
            pass
    return list(dict.fromkeys(forms))


def unapproved_target_overlaps(
    artifacts: dict[str, Any],
    target_blobs: dict[str, bytes],
    *,
    allowed_values: set[str],
    minimum_bytes: int = 32,
) -> list[tuple[str, str, str]]:
    """Return identities, not copied bytes, for unapproved target-string overlaps.

    This maintained primitive is exercised with synthetic blobs. The APG77B
    operational scan reads exact target Git objects outside the repository and
    retains only sanitized match identities and counts.
    """
    if minimum_bytes < 1:
        fail("clean-room overlap threshold must be positive")
    findings: list[tuple[str, str, str]] = []
    for artifact_id, artifact in artifacts.items():
        for candidate in iter_strings(artifact):
            encoded = candidate.encode("utf-8")
            if candidate in allowed_values:
                continue
            forms = _decoded_candidate_forms(candidate)
            for target_id, blob in target_blobs.items():
                if any(
                    window in blob
                    for form in forms
                    for window in (
                        form[offset:offset + minimum_bytes]
                        for offset in range(max(0, len(form) - minimum_bytes + 1))
                    )
                ):
                    findings.append(
                        (artifact_id, target_id, hashlib.sha256(encoded).hexdigest())
                    )
    return sorted(set(findings))


def _validate_object_identity(row: Any, context: str, *, path_row: bool) -> str:
    expected = PATH_KEYS if path_row else IDENTITY_KEYS
    if not isinstance(row, dict) or set(row) != expected:
        fail(f"{context} has unknown or missing identity fields")
    path = _relative_path(row["path"], f"{context} path")
    if not isinstance(row["byte_size"], int) or row["byte_size"] < 0:
        fail(f"{context} byte size is invalid")
    if not isinstance(row["git_mode"], str) or not MODE.fullmatch(row["git_mode"]):
        fail(f"{context} Git mode is invalid")
    if row["git_type"] != "blob" or not HEX40.fullmatch(row["git_object"]):
        fail(f"{context} Git object is invalid or not a retained blob")
    if not isinstance(row["sha256"], str) or not HEX64.fullmatch(row["sha256"]):
        fail(f"{context} SHA-256 must be full lowercase hexadecimal")
    extra = ("artifact_class", "inventory_relevance") if path_row else ("format", "semantic_role")
    for field in extra:
        if not isinstance(row[field], str) or not row[field].strip():
            fail(f"{context} {field} is empty")
    return path


def _inventory_digest(rows: list[dict[str, Any]]) -> str:
    payload = "\n".join(
        "\0".join(
            str(row[field])
            for field in ("git_mode", "git_type", "git_object", "byte_size", "sha256", "path")
        )
        for row in rows
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_target_ledger(value: Any) -> dict[str, Any]:
    """Validate exact target object, path, hash, and subset retention."""
    top = {"comparison", "generated_from", "phase", "privacy_boundary", "schema_version", "targets"}
    if not isinstance(value, dict) or set(value) != top:
        fail("target ledger top-level schema is invalid")
    if value["schema_version"] != 1 or value["phase"] != "APG77A":
        fail("target ledger identity is invalid")
    for field in ("generated_from", "comparison"):
        if not isinstance(value[field], dict) or not value[field]:
            fail(f"target ledger {field} is incomplete")
    if not isinstance(value["privacy_boundary"], str) or not value["privacy_boundary"]:
        fail("target ledger privacy boundary is empty")
    targets = value["targets"]
    if not isinstance(targets, list) or [item.get("target_key") for item in targets] != ["website", "theme"]:
        fail("target ledger targets are incomplete or unordered")
    comparison = value["comparison"]
    required_comparison = {"apg77_baseline", "apg77a_fresh", "drift_disposition", "path_inventory_sha256"}
    if set(comparison) != required_comparison:
        fail("target comparison schema is invalid")
    for target in targets:
        key = target["target_key"]
        if set(target) != TARGET_KEYS:
            fail(f"{key} target schema is invalid")
        if target["default_branch"] != "main" or target["fetched_ref"] != "refs/heads/main":
            fail(f"{key} branch identity is invalid")
        if not HEX40.fullmatch(target["commit"]) or not HEX40.fullmatch(target["tree"]):
            fail(f"{key} root Git identity is invalid")
        if not isinstance(target["commit_parent_count"], int) or target["commit_parent_count"] < 0:
            fail(f"{key} parent count is invalid")
        for field in ("remote_identity", "repository_role", "fetch_time_utc", "license_boundary"):
            if not isinstance(target[field], str) or not target[field].strip():
                fail(f"{key} {field} is empty")
        rows = target["path_objects"]
        if not isinstance(rows, list) or not rows:
            fail(f"{key} path inventory is empty")
        paths = [_validate_object_identity(row, f"{key} path row", path_row=True) for row in rows]
        if paths != sorted(paths) or len(paths) != len(set(paths)):
            fail(f"{key} paths are duplicated or unordered")
        if target["tracked_path_count"] != len(rows):
            fail(f"{key} tracked path count does not derive from rows")
        counts: dict[str, int] = {}
        for row in rows:
            counts[row["artifact_class"]] = counts.get(row["artifact_class"], 0) + 1
        if target["inventory_counts"] != dict(sorted(counts.items())):
            fail(f"{key} aggregate counts do not derive from path rows")
        by_path = {row["path"]: row for row in rows}
        for subset_name in ("manifest_paths", "lock_paths"):
            subset = target[subset_name]
            if not isinstance(subset, list) or not subset:
                fail(f"{key} {subset_name} is empty")
            subset_paths = [
                _validate_object_identity(row, f"{key} {subset_name} row", path_row=False)
                for row in subset
            ]
            if subset_paths != sorted(subset_paths) or len(subset_paths) != len(set(subset_paths)):
                fail(f"{key} {subset_name} paths are duplicated or unordered")
            for row in subset:
                retained = by_path.get(row["path"])
                if retained is None or any(retained[field] != row[field] for field in ("git_mode", "git_type", "git_object", "byte_size", "sha256")):
                    fail(f"{key} {subset_name} is not an exact path subset")
        scripts = target["script_sources"]
        if not isinstance(scripts, list) or not scripts:
            fail(f"{key} script sources are empty")
        script_paths: list[str] = []
        manifest_paths = {row["path"] for row in target["manifest_paths"]}
        for script in scripts:
            if not isinstance(script, dict) or set(script) != {"path", "script_names", "selection_role"}:
                fail(f"{key} script source schema is invalid")
            path = _relative_path(script["path"], f"{key} script source")
            if path not in manifest_paths:
                fail(f"{key} script source is not a retained manifest")
            _strings(script["script_names"], f"{key} script names")
            if not isinstance(script["selection_role"], str) or not script["selection_role"]:
                fail(f"{key} script selection role is empty")
            script_paths.append(path)
        if script_paths != sorted(script_paths) or len(script_paths) != len(set(script_paths)):
            fail(f"{key} script sources are duplicated or unordered")
        current = comparison["apg77a_fresh"].get(key)
        baseline = comparison["apg77_baseline"].get(key)
        expected = {"commit": target["commit"], "tracked_path_count": len(rows), "tree": target["tree"]}
        if current != expected or baseline != expected:
            fail(f"{key} root comparison and target identity disagree")
        if comparison["drift_disposition"].get(key) != "unchanged-exact-commit-and-tree":
            fail(f"{key} drift disposition is invalid")
        if comparison["path_inventory_sha256"].get(key) != _inventory_digest(rows):
            fail(f"{key} path inventory digest is unreconciled")
    return value


def validate_lane_tombstone(
    value: Any, *, expected_replacement: str
) -> dict[str, Any]:
    """Require the contaminated APG77A Lane T bytes to remain history-only."""
    if not isinstance(value, dict) or set(value) != TOMBSTONE_KEYS:
        fail("Lane T tombstone schema is invalid")
    if (
        value["schema_version"] != 1
        or value["phase"] != "APG77B"
        or value["historical_status"] != "superseded-contaminated-evidence"
        or value["replacement"] != expected_replacement
        or not HEX40.fullmatch(value["historical_commit"])
        or not HEX64.fullmatch(value["historical_sha256"])
        or not isinstance(value["reason"], str)
        or not value["reason"].strip()
    ):
        fail("Lane T tombstone identity is invalid")
    return value


def validate_purpose_registry(value: Any, ledger: Any) -> dict[str, Any]:
    """Validate the compact, non-expressive input registry for clean-room Lane T2."""
    validate_target_ledger(ledger)
    if not isinstance(value, dict) or set(value) != REGISTRY_KEYS:
        fail("purpose registry top-level schema is invalid")
    if value["schema_version"] != 1 or value["phase"] != "APG77B":
        fail("purpose registry identity is invalid")
    expected_counts = {"fixture": 14, "semantic": 24, "target": 7, "total": 45}
    if value["purpose_counts"] != expected_counts:
        fail("purpose registry counts are invalid")
    if not isinstance(value["registry_boundary"], str) or not value["registry_boundary"].strip():
        fail("purpose registry boundary is empty")
    boundaries = value["boundary_definitions"]
    expected_boundaries = {
        "fixture-purpose-input",
        "no-resolved-or-source-expression",
        "semantic-purpose-input",
        "target-identity-and-fact-input",
    }
    if not isinstance(boundaries, dict) or set(boundaries) != expected_boundaries:
        fail("purpose registry boundary definitions are incomplete")
    for boundary in boundaries.values():
        if not isinstance(boundary, str) or not boundary.strip():
            fail("purpose registry boundary definition is empty")

    sources = value["source_registry"]
    if not isinstance(sources, list) or len(sources) != 7:
        fail("purpose registry source set is incomplete")
    source_ids: list[str] = []
    for source in sources:
        if not isinstance(source, dict) or not {"id", "identity", "source_class"} <= set(source):
            fail("purpose registry source record is invalid")
        if set(source) not in ({"id", "identity", "source_class", "sha256"}, {"id", "identity", "locator", "source_class"}):
            fail("purpose registry source record has unknown fields")
        _complete_value(source, "purpose registry source record")
        if "sha256" in source and not HEX64.fullmatch(source["sha256"]):
            fail("purpose registry source hash is invalid")
        source_ids.append(source["id"])
    if len(source_ids) != len(set(source_ids)) or source_ids[-1] != "APG77A-H1-LEDGER":
        fail("purpose registry source identities are duplicated or unordered")
    if sources[-1].get("sha256") != hashlib.sha256(canonical_json(ledger).encode("utf-8")).hexdigest():
        fail("purpose registry does not bind the exact H1 ledger")

    targets = {target["target_key"]: target for target in ledger["targets"]}
    ledger_objects = {
        (target_key, row["path"], row["git_object"])
        for target_key, target in targets.items()
        for row in target["path_objects"]
    }
    cards = value["target_fact_cards"]
    if not isinstance(cards, list) or len(cards) != 7:
        fail("target fact-card set is incomplete")
    card_by_id: dict[str, dict[str, Any]] = {}
    for index, card in enumerate(cards, 1):
        expected_card_id = f"APG77B-TARGET-FACT-{index:03d}"
        expected_purpose_id = f"APG77-TARGET-{index:03d}"
        if not isinstance(card, dict) or set(card) != FACT_CARD_KEYS:
            fail(f"{expected_card_id} schema is invalid")
        if card["id"] != expected_card_id or card["purpose_id"] != expected_purpose_id:
            fail("target fact cards are incomplete or unordered")
        for field in (
            "factual_observations",
            "relevant_source_authority_questions",
            "required_evidence_still_absent",
        ):
            _strings(card[field], f"{expected_card_id} {field}")
        for field in ("artifact_class", "host_embedded_region_class"):
            if not isinstance(card[field], str) or not card[field].strip():
                fail(f"{expected_card_id} {field} is empty")
        identities = card["identities"]
        if not isinstance(identities, list) or not identities:
            fail(f"{expected_card_id} identities are empty")
        identity_keys: list[tuple[str, str, str]] = []
        for identity in identities:
            if not isinstance(identity, dict) or set(identity) != {"blob", "path", "repository"}:
                fail(f"{expected_card_id} identity schema is invalid")
            repository = identity["repository"]
            path = _relative_path(identity["path"], f"{expected_card_id} identity path")
            blob = identity["blob"]
            if repository not in targets or not isinstance(blob, str) or not HEX40.fullmatch(blob):
                fail(f"{expected_card_id} identity is invalid")
            identity_keys.append((repository, path, blob))
            if (repository, path, blob) not in ledger_objects:
                fail(f"{expected_card_id} identity is absent from H1")
        if len(identity_keys) != len(set(identity_keys)):
            fail(f"{expected_card_id} identities are duplicated")
        roots = card["repository_roots"]
        if not isinstance(roots, list) or not roots:
            fail(f"{expected_card_id} roots are empty")
        seen_roots: list[str] = []
        for root in roots:
            if not isinstance(root, dict) or set(root) != {"commit", "repository", "tree"}:
                fail(f"{expected_card_id} root schema is invalid")
            repository = root["repository"]
            if repository not in targets or root != {
                "commit": targets[repository]["commit"],
                "repository": repository,
                "tree": targets[repository]["tree"],
            }:
                fail(f"{expected_card_id} root disagrees with H1")
            seen_roots.append(repository)
        if seen_roots != sorted(set(repository for repository, _, _ in identity_keys)):
            fail(f"{expected_card_id} roots do not cover its identities exactly")
        card_by_id[card["id"]] = card

    purposes = value["purposes"]
    if not isinstance(purposes, list) or [row.get("id") for row in purposes if isinstance(row, dict)] != list(PURPOSE_IDS):
        fail("purpose registry rows are incomplete or unordered")
    derived_counts = {"fixture": 0, "semantic": 0, "target": 0}
    for row in purposes:
        if not isinstance(row, dict) or set(row) != PURPOSE_KEYS:
            fail("purpose registry row schema is invalid")
        row_id = row["id"]
        row_class = row["row_class"]
        if row_class not in derived_counts:
            fail(f"{row_id} class is invalid")
        derived_counts[row_class] += 1
        if not isinstance(row["canonical_purpose"], str) or not row["canonical_purpose"].strip():
            fail(f"{row_id} purpose is empty")
        if hashlib.sha256(row["canonical_purpose"].encode("utf-8")).hexdigest() != row["purpose_sha256"]:
            fail(f"{row_id} purpose digest is invalid")
        _strings(row["required_identity_keys"], f"{row_id} identity keys")
        if row["copying_boundary"] != "no-resolved-or-source-expression":
            fail(f"{row_id} copying boundary is invalid")
        expected_source_boundary = {
            "semantic": "semantic-purpose-input",
            "fixture": "fixture-purpose-input",
            "target": "target-identity-and-fact-input",
        }[row_class]
        if row["source_class_boundary"] != expected_source_boundary:
            fail(f"{row_id} source-class boundary is invalid")
        if row_class == "target":
            expected_card = f"APG77B-TARGET-FACT-{int(row_id.rsplit('-', 1)[1]):03d}"
            if row["allowed_target_fact_card"] != expected_card:
                fail(f"{row_id} target fact-card binding is invalid")
            required = set(row["required_identity_keys"])
            if (
                f"target_fact_card:{expected_card}" not in required
                or f"target_fact_card_sha256:{value_sha256(card_by_id[expected_card])}" not in required
            ):
                fail(f"{row_id} target fact-card digest is invalid")
        elif row["allowed_target_fact_card"] != "none":
            fail(f"{row_id} unexpectedly permits a target fact card")
    if derived_counts != {"fixture": 14, "semantic": 24, "target": 7}:
        fail("purpose registry row classes do not derive the declared counts")
    return value


def validate_lane(value: Any, expected_lane: str) -> dict[str, Any]:
    """Validate one independently complete purpose-by-purpose vector file."""
    top = {"authorship_boundary", "lane", "phase", "purpose_count", "schema_version", "source_basis", "vectors"}
    if not isinstance(value, dict) or set(value) != top:
        fail("lane top-level schema is invalid")
    if value["schema_version"] != 1 or value["phase"] != "APG77A" or value["lane"] != expected_lane:
        fail("lane identity is invalid")
    if not isinstance(value["authorship_boundary"], dict) or not value["authorship_boundary"]:
        fail("lane authorship boundary is incomplete")
    _complete_value(value["authorship_boundary"], "lane authorship boundary")
    if expected_lane == "T2":
        _strings(value["source_basis"], "Lane T2 source basis")
    else:
        _source_basis(value["source_basis"])
    vectors = value["vectors"]
    if value["purpose_count"] != len(PURPOSE_IDS) or not isinstance(vectors, list):
        fail("lane purpose count is invalid")
    if [row.get("id") for row in vectors if isinstance(row, dict)] != list(PURPOSE_IDS):
        fail("lane purposes are incomplete or unordered")
    serialized = canonical_json(value)
    for pattern in FORBIDDEN_LANE_PATTERNS:
        if re.search(pattern, serialized, re.IGNORECASE):
            fail("lane contains a cross-lane inheritance token")
    for row in vectors:
        if not isinstance(row, dict) or set(row) != VECTOR_KEYS:
            fail(f"lane vector {row.get('id', '<unknown>')} has unknown or missing fields")
        if row["css_selection"] not in SELECTIONS or row["response"] not in RESPONSES:
            fail(f"{row['id']} selection or response is invalid")
        for field in ARRAY_FIELDS:
            _strings(row[field], f"{row['id']} {field}")
        if set(row["present_evidence"]) & set(row["required_evidence"]):
            fail(f"{row['id']} present and required evidence overlap")
        for field in VECTOR_KEYS - ARRAY_FIELDS - {"id", "css_selection", "response"}:
            value = row[field]
            if isinstance(value, list):
                _strings(value, f"{row['id']} {field}")
            elif not isinstance(value, str) or not value.strip():
                fail(f"{row['id']} {field} is empty")
    return value


def validate_lane_pair(lane_n: Any, lane_t: Any) -> None:
    validate_lane(lane_n, "N")
    validate_lane(lane_t, "T")
    if [row["id"] for row in lane_n["vectors"]] != [row["id"] for row in lane_t["vectors"]]:
        fail("lane purpose order differs")
    if lane_n == lane_t or lane_n["vectors"] == lane_t["vectors"]:
        fail("independent lane content is copied wholesale")
    for normative, target in zip(lane_n["vectors"], lane_t["vectors"], strict=True):
        if normative == target:
            fail(f"{normative['id']} is copied wholesale across lanes")


def validate_clean_room_lane(
    value: Any,
    *,
    expected_lane: str,
    expected_phase: str,
    registry: Any,
) -> dict[str, Any]:
    """Validate one lane against every independently frozen registry purpose."""
    top_v1 = {"authorship_boundary", "lane", "phase", "purpose_count", "schema_version", "source_basis", "vectors"}
    top_v2 = top_v1 | {"purpose_registry_sha256"}
    if not isinstance(value, dict) or set(value) not in (top_v1, top_v2):
        fail("clean-room lane top-level schema is invalid")
    expected_version = 1
    if (
        value["schema_version"] != expected_version
        or value["phase"] != expected_phase
        or value["lane"] != expected_lane
        or value["purpose_count"] != len(PURPOSE_IDS)
    ):
        fail("clean-room lane identity is invalid")
    if set(value) == top_v2:
        registry_hash = hashlib.sha256(canonical_json(registry).encode("utf-8")).hexdigest()
        if value["purpose_registry_sha256"] != registry_hash:
            fail("clean-room lane registry binding is invalid")
    if not isinstance(value["authorship_boundary"], dict) or not value["authorship_boundary"]:
        fail("clean-room lane authorship boundary is incomplete")
    _complete_value(value["authorship_boundary"], "clean-room lane authorship boundary")
    if expected_lane == "T2":
        _strings(value["source_basis"], "Lane T2 source basis")
    else:
        _source_basis(value["source_basis"])
    vectors = value["vectors"]
    purposes = registry["purposes"]
    if not isinstance(vectors, list) or [row.get("id") for row in vectors if isinstance(row, dict)] != list(PURPOSE_IDS):
        fail("clean-room lane purposes are incomplete or unordered")
    serialized = canonical_json(value)
    for pattern in FORBIDDEN_LANE_PATTERNS:
        if re.search(pattern, serialized, re.IGNORECASE):
            fail("clean-room lane contains a cross-lane inheritance token")
    for row, purpose in zip(vectors, purposes, strict=True):
        if not isinstance(row, dict) or set(row) != VECTOR_KEYS:
            fail(f"clean-room lane vector {row.get('id', '<unknown>')} has unknown or missing fields")
        if row["id"] != purpose["id"] or row["purpose"] != purpose["canonical_purpose"]:
            fail(f"{purpose['id']} lane purpose is not bound to the registry")
        if row["css_selection"] not in SELECTIONS or row["response"] not in RESPONSES:
            fail(f"{row['id']} selection or response is invalid")
        for field in ARRAY_FIELDS:
            _strings(row[field], f"{row['id']} {field}", allow_empty=field in {"present_evidence", "required_evidence", "routes_or_obligations"})
        if set(row["present_evidence"]) & set(row["required_evidence"]):
            fail(f"{row['id']} present and required evidence overlap")
        for field in VECTOR_KEYS - ARRAY_FIELDS - {"id", "css_selection", "response"}:
            item = row[field]
            if isinstance(item, list):
                _strings(item, f"{row['id']} {field}")
            elif not isinstance(item, str) or not item.strip():
                fail(f"{row['id']} {field} is empty")
    return value


def validate_clean_room_lane_pair(lane_n: Any, lane_t2: Any, registry: Any) -> None:
    validate_clean_room_lane(
        lane_n, expected_lane="N", expected_phase="APG77A", registry=registry
    )
    validate_clean_room_lane(
        lane_t2, expected_lane="T2", expected_phase="APG77B", registry=registry
    )
    for normative, target in zip(lane_n["vectors"], lane_t2["vectors"], strict=True):
        if normative == target:
            fail(f"{normative['id']} is copied wholesale across clean-room lanes")


def _artifact_value_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _item_values(value: Any) -> list[Any]:
    return value if isinstance(value, list) else [value]


ROW_KEYS_V3 = {
    "adjudication_ids",
    "artifact_class",
    "completion_class",
    "css_selection",
    "edit_permission_class",
    "id",
    "normative_authority_ids",
    "purpose_sha256",
    "response",
    "route_obligations",
    "row_class",
    "structured_disposition",
    "tool_or_target_authority_ids",
    "whole_file_owner",
}
ADJUDICATION_KEYS_V3 = {
    "decision",
    "field",
    "id",
    "lane_n_value",
    "lane_t2_value",
    "reason",
    "resolved_value",
    "reviewer",
    "row_id",
    "source_ids",
}
ROUTE_KEYS_V3 = {"decision_scope", "obligation_id", "owner", "stop_state"}
SOURCE_BINDING_KEYS_V3 = {
    "h1_target_ledger",
    "lane_n",
    "lane_t",
    "lane_t2",
    "maintained_scenario_fixture",
    "normative_source_registry",
    "provenance_v2",
    "purpose_registry",
}
SOURCE_BINDING_CLASSES_V3 = {
    "purpose_registry": "retained-task-identity",
    "maintained_scenario_fixture": "current-product-semantics",
    "normative_source_registry": "current-primary-source-binding",
    "h1_target_ledger": "historical-retained-evidence",
    "lane_n": "historical-retained-evidence",
    "lane_t2": "historical-retained-evidence",
    "lane_t": "historical-superseded-evidence",
    "provenance_v2": "historical-non-current-review-evidence",
}
PRIVATE_BINDING_KEYS_V3 = {*SOURCE_BINDING_CLASSES_V3, "compact_v3"}


def private_source_binding_paths(
    root: Path, *, required: bool = True
) -> dict[str, str] | None:
    """Load exact private locators from their publication-excluded owner."""
    records: list[dict[str, str]] = []
    private_root = root / "private" / "evaluations"
    if private_root.is_dir() and not private_root.is_symlink():
        for path in private_root.rglob("*.md"):
            if path.is_symlink() or not path.is_file():
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeError):
                continue
            for line in lines:
                if line.startswith(PRIVATE_BINDING_PREFIX) and line.endswith(
                    PRIVATE_BINDING_SUFFIX
                ):
                    payload = line[
                        len(PRIVATE_BINDING_PREFIX) : -len(PRIVATE_BINDING_SUFFIX)
                    ]
                    try:
                        value = json.loads(payload, object_pairs_hook=_strict_object)
                    except (json.JSONDecodeError, EvidenceContractError):
                        fail("private source-binding owner is malformed")
                    records.append(value)
    if not records:
        if required:
            fail("private source-binding owner is unavailable")
        return None
    if len(records) != 1:
        fail("private source-binding owner is missing or duplicated")
    value = records[0]
    if not isinstance(value, dict) or set(value) != PRIVATE_BINDING_KEYS_V3:
        fail("private source-binding owner schema is invalid")
    paths: dict[str, str] = {}
    for key, item in value.items():
        paths[key] = _relative_path(item, f"private source binding {key}")
    if len(set(paths.values())) != len(paths):
        fail("private source-binding paths are duplicated")
    commitment = hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    if commitment != PRIVATE_BINDING_COMMITMENT_SHA256:
        fail("private source-binding owner commitment is invalid")
    return paths
AUTHORITY_IDS_V3 = {
    "CSS Syntax 3": ("css-syntax-3",),
    "Selectors 4": ("selectors-4",),
    "Cascade 5": ("css-cascade-5",),
    "Values and Units 4": ("css-values-4",),
    "Variables 1": ("css-variables-1",),
    "Conditional Rules 3": ("css-conditional-3",),
    "Media Queries 4": ("mediaqueries-4",),
    "Media Queries 5": ("mediaqueries-5",),
    "Nesting 1": ("css-nesting-1",),
    "Color 4": ("css-color-4",),
    "Logical Properties 1": ("css-logical-1",),
    "Pseudo-elements 4": ("css-pseudo-4",),
    "Generated Content 3": ("css-content-3",),
    "Box Model 4": ("css-box-4",),
    "SVG 2": ("svg2-20181004",),
    "SVG 2 Styling": ("svg2-20181004",),
    "Style Attributes": ("css-style-attr-20131107",),
    "construct-governing property module": ("question-specific-property-module",),
    "property-defining module": ("question-specific-property-module",),
    "construct-governing CSS modules": ("question-specific-css-modules",),
    "question-specific normative source": ("question-specific-module-unresolved",),
    "question-specific normative modules": ("question-specific-module-unresolved",),
}
TOOL_AUTHORITY_IDS_V3 = {
    "fresh target inventory": "fresh-target-inventory",
    "APG host-boundary contract": "apg-host-boundary-contract",
    "host documentation": "host-documentation",
    "Astro host documentation": "astro-documentation",
    "Astro styling documentation": "astro-documentation",
    "Astro documentation": "astro-documentation",
    "Vite documentation": "vite-documentation",
    "exact lock identities": "exact-lock-identities",
    "exact tool proof boundary": "exact-tool-proof-boundary",
}
ROUTE_SCOPES_V3 = {
    "DOM-owner": "document-shape-and-matching",
    "project-configuration": "source-level-and-tool-selection",
    "runtime-owner": "environment-and-runtime-state",
    "browser-compatibility-owner": "feature-availability-and-browser-support",
    "host-owner": "host-file-and-extraction",
    "build-transform-owner": "build-transformation",
    "generated-artifact-owner": "regeneration-and-provenance",
    "visual-validation-owner": "appearance-and-visual-acceptance",
}
COMPLETION_CLASSES_V3 = {
    "proceed-routine": "complete-static-claim",
    "inspect-before-judgment": "requires-inspection",
    "bounded-local-decision": "bounded-static-claim",
    "stop-and-escalate": "blocked-dependent-claim",
}
BANNED_PAYLOAD_FIELDS = {
    "target_excerpt",
    "source_excerpt",
    "raw_source",
    "source_body",
    "encoded_source",
    "compressed_source",
    "payload_bytes",
    "reconstruction_script",
}
FALSE_APG77B_DIFF_DIGEST = (
    "084b7448b2e6d918479491ef2afbe3e9457d82a36ba3864e381dbe7f754f5fcd"
)
EXPECTED_APG77B_PATCH = {
    "byte_size": 1058232,
    "name": "APG77B correction authoritative raw Git patch",
    "record_id": "GIT-SHOW-REPORT-2916b2867f18bafb82efca9d5c115777990a1fb3",
    "representation": "git-show-report-v2-patch-bytes",
    "sha256": "92c5b5f27f8d1277cf92c4890d710ccd9834e87233686e6a5cc917d0f2918082",
}


def _edit_permission_class(value: str) -> str:
    if value == "target read-only":
        return "read-only"
    if "forbidden" in value:
        return "forbidden-until-owner-resolves"
    if value.startswith("APG fixture"):
        return "apg-fixture-owner-permission-required"
    if value.startswith("host "):
        return "host-owner-permission-required"
    if value.startswith("repository "):
        return "repository-permission-required"
    return "artifact-owner-permission-required"


def _expected_authority_ids(
    row: dict[str, Any],
    row_class: str,
) -> tuple[list[str], list[str]]:
    normative: list[str] = []
    tools = ["maintained-scenario-fixture"]
    if row_class == "fixture":
        tools.append("apg76-fixture-manifest")
    if row_class == "target":
        tools.append("apg77a-h1-ledger")
    for authority in row["authority"]:
        if authority in AUTHORITY_IDS_V3:
            normative.extend(AUTHORITY_IDS_V3[authority])
        elif authority in TOOL_AUTHORITY_IDS_V3:
            tools.append(TOOL_AUTHORITY_IDS_V3[authority])
        else:
            fail(f"{row['id']} contains an unmapped source authority")
    return list(dict.fromkeys(normative)), list(dict.fromkeys(tools))


def _expected_routes(row: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "obligation_id": f"{row['id']}-ROUTE-{index:02d}",
            "owner": owner,
            "decision_scope": ROUTE_SCOPES_V3[owner],
            "stop_state": (
                "blocks-dependent-claim"
                if row["response"] == "stop-and-escalate"
                else "outside-bounded-css-claim"
            ),
        }
        for index, owner in enumerate(row["routes"], 1)
    ]


def validate_route_obligations(
    value: Any,
    *,
    expected: list[dict[str, str]] | None = None,
    context: str = "route obligations",
) -> list[dict[str, str]]:
    if not isinstance(value, list):
        fail(f"{context} must be an array")
    identities: set[str] = set()
    semantics: set[tuple[str, str, str]] = set()
    for obligation in value:
        if not isinstance(obligation, dict) or set(obligation) != ROUTE_KEYS_V3:
            fail(f"{context} schema is invalid")
        _complete_value(obligation, context)
        identity = obligation["obligation_id"]
        semantic = (
            obligation["owner"],
            obligation["decision_scope"],
            obligation["stop_state"],
        )
        if identity in identities or semantic in semantics:
            fail(f"{context} contains a duplicate or collapsed obligation")
        identities.add(identity)
        semantics.add(semantic)
    if expected is not None and value != expected:
        fail(f"{context} is incomplete or changes obligation identity")
    return value


def validate_no_opaque_payload_fields(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in BANNED_PAYLOAD_FIELDS:
                fail(f"banned opaque payload field: {key}")
            validate_no_opaque_payload_fields(child)
    elif isinstance(value, list):
        for child in value:
            validate_no_opaque_payload_fields(child)


def validate_diff_digest_claims(value: Any) -> None:
    """Require every patch or diff digest to name one exact byte stream."""
    if isinstance(value, dict):
        digest_keys = {
            key for key in value
            if isinstance(key, str)
            and re.search(r"(?:diff|patch).*sha256|sha256.*(?:diff|patch)", key)
        }
        if digest_keys and not {"name", "representation", "byte_size"} <= set(value):
            fail("diff digest has no matching named byte stream")
        for key, child in value.items():
            if key == "sha256" and child == FALSE_APG77B_DIFF_DIGEST:
                fail("historical false diff digest cannot remain current truth")
            validate_diff_digest_claims(child)
    elif isinstance(value, list):
        for child in value:
            validate_diff_digest_claims(child)


def validate_patch_representations(value: Any) -> None:
    if value != [EXPECTED_APG77B_PATCH]:
        fail("named patch representation is absent, unnamed, or mislabelled")
    validate_diff_digest_claims(value)


def validate_proportionality(
    artifacts: dict[str, bytes],
    *,
    compact_name: str = "resolved-structured-decisions-v3.json",
) -> dict[str, int]:
    if compact_name not in artifacts:
        fail("compact v3 is absent from current-authority evidence")
    sizes = {name: len(body) for name, body in artifacts.items()}
    if sizes[compact_name] > 120 * 1024:
        fail("compact v3 exceeds the 120 KiB hard limit")
    oversized = [name for name, size in sizes.items() if size > 150 * 1024]
    if oversized:
        fail("a current-authority machine artifact exceeds 150 KiB")
    if sum(sizes.values()) > 350 * 1024:
        fail("current-authority machine evidence exceeds 350 KiB")
    return sizes


def validate_declared_css_lifecycle_labels(
    lifecycle: str,
    *,
    adr_status: str,
    integrated: bool,
) -> None:
    """Check caller-provided labels only; this is not repository-state proof."""
    expected = {
        "corrected-awaiting-fresh-review": ("Proposed", False),
        "provisionally-integrated": ("Accepted with amendment", True),
    }
    if lifecycle not in expected or expected[lifecycle] != (adr_status, integrated):
        fail("declared CSS lifecycle, ADR status, and integration labels disagree")
    if adr_status == "Rejected":
        fail("APG77C has no CSS rejection authority")


def _validate_source_bindings(root: Path, value: Any) -> None:
    if not isinstance(value, dict) or set(value) != SOURCE_BINDING_KEYS_V3:
        fail("compact v3 source bindings are incomplete")
    source_paths = private_source_binding_paths(root)
    assert source_paths is not None
    for key, authority_class in SOURCE_BINDING_CLASSES_V3.items():
        expected_path = source_paths[key]
        record = value[key]
        if not isinstance(record, dict) or set(record) != {
            "authority_class", "path", "sha256"
        }:
            fail(f"compact v3 {key} source binding schema is invalid")
        if record["path"] != expected_path or record["authority_class"] != authority_class:
            fail(f"compact v3 {key} authority classification is invalid")
        path = root / expected_path
        if record["sha256"] != file_sha256(path):
            fail(f"compact v3 {key} source digest drifted")


def validate_resolved_structured_decisions_v3(
    root: Path,
    resolved: Any,
    lane_n: Any,
    lane_t2: Any,
    registry: Any,
    ledger: Any,
    compact: Any,
) -> dict[str, int]:
    """Validate APG77C's compact consequence-bearing current authority."""
    validate_target_ledger(ledger)
    validate_purpose_registry(registry, ledger)
    validate_no_opaque_payload_fields(compact)
    top = {
        "adjudications",
        "contract_boundary",
        "local_source_ids",
        "patch_representations",
        "phase",
        "proof_boundary",
        "rows",
        "schema_version",
        "source_bindings",
    }
    if not isinstance(compact, dict) or set(compact) != top:
        fail("compact v3 top-level schema is invalid")
    if compact["schema_version"] != 3 or compact["phase"] != "APG77C":
        fail("compact v3 identity is invalid")
    if compact["contract_boundary"] != (
        "compact consequence-bearing decisions; explanatory prose remains human-reviewed"
    ):
        fail("compact v3 machine and human proof boundary is invalid")
    _validate_source_bindings(root, compact["source_bindings"])
    source_paths = private_source_binding_paths(root)
    assert source_paths is not None
    if (
        resolved
        != json.loads(
            (root / source_paths["maintained_scenario_fixture"]).read_text(
                encoding="utf-8"
            )
        )
        or registry != load_json(root / source_paths["purpose_registry"])
        or ledger != load_json(root / source_paths["h1_target_ledger"])
        or lane_n != load_json(root / source_paths["lane_n"])
        or lane_t2 != load_json(root / source_paths["lane_t2"])
    ):
        fail("compact v3 supplied source values do not match their exact bindings")
    validate_patch_representations(compact["patch_representations"])
    if compact["proof_boundary"] != {
        "machine": [
            "ids",
            "closed-vocabularies",
            "source-ids",
            "route-obligations",
            "target-identities",
            "selection-response",
            "stop-completion-edit-classes",
            "lifecycle-release-rollback-ownership",
        ],
        "source_or_tool_tests": "only exact observed or cited behavior",
        "human_review": "explanatory prose accuracy and sufficiency",
    }:
        fail("compact v3 proof boundary is invalid")
    if (
        not isinstance(resolved, dict)
        or [row.get("id") for row in resolved.get("rows", [])] != list(PURPOSE_IDS)
    ):
        fail("maintained scenario rows are unavailable")
    if not isinstance(lane_n, dict) or not isinstance(lane_t2, dict):
        fail("historical lanes are unavailable for structured disagreements")
    lane_rows = {
        "N": {row["id"]: row for row in lane_n.get("vectors", [])},
        "T2": {row["id"]: row for row in lane_t2.get("vectors", [])},
    }
    if set(lane_rows["N"]) != set(PURPOSE_IDS) or set(lane_rows["T2"]) != set(PURPOSE_IDS):
        fail("historical lane row identities are incomplete")
    purposes = {row["id"]: row for row in registry["purposes"]}
    manifest = json.loads(
        (root / source_paths["normative_source_registry"]).read_text(
            encoding="utf-8"
        )
    )
    normative_ids = {
        source["shortname"] for source in manifest["source_bindings"]["modules"]
    }
    local_ids = compact["local_source_ids"]
    if not isinstance(local_ids, dict) or any(
        not isinstance(key, str)
        or not key
        or not isinstance(description, str)
        or not description.strip()
        for key, description in local_ids.items()
    ):
        fail("compact v3 local source IDs are invalid")
    available_sources = normative_ids | set(local_ids)
    rows = compact["rows"]
    if (
        not isinstance(rows, list)
        or [row.get("id") for row in rows if isinstance(row, dict)] != list(PURPOSE_IDS)
    ):
        fail("compact v3 rows are incomplete or unordered")

    adjudications = compact["adjudications"]
    if not isinstance(adjudications, list) or len(adjudications) >= 100:
        fail("compact v3 adjudication count is invalid")
    by_id: dict[str, dict[str, Any]] = {}
    by_row: dict[str, list[str]] = {row_id: [] for row_id in PURPOSE_IDS}
    for index, adjudication in enumerate(adjudications, 1):
        if not isinstance(adjudication, dict) or set(adjudication) != ADJUDICATION_KEYS_V3:
            fail("compact v3 adjudication schema is invalid")
        expected_id = f"APG77C-ADJ-{index:03d}"
        row_id = adjudication["row_id"]
        field = adjudication["field"]
        if (
            adjudication["id"] != expected_id
            or row_id not in by_row
            or field not in {"css_selection", "response"}
        ):
            fail("compact v3 adjudication identity is invalid")
        n_value = lane_rows["N"][row_id][field]
        t2_value = lane_rows["T2"][row_id][field]
        if n_value == t2_value:
            fail("compact v3 adjudicates lane agreement")
        if (
            adjudication["lane_n_value"] != n_value
            or adjudication["lane_t2_value"] != t2_value
        ):
            fail("compact v3 adjudication lane values are false")
        decision = adjudication["decision"]
        resolved_value = adjudication["resolved_value"]
        if decision == "retain-n":
            valid = resolved_value == n_value
        elif decision == "retain-t2":
            valid = resolved_value == t2_value
        elif decision == "synthesize":
            valid = resolved_value != n_value or resolved_value != t2_value
        else:
            valid = False
        if not valid:
            fail("compact v3 adjudication action semantics are false")
        reason = adjudication["reason"]
        reviewer = adjudication["reviewer"]
        source_ids = _strings(
            adjudication["source_ids"],
            f"{row_id} {field} adjudication source IDs",
        )
        if (
            not isinstance(reason, str)
            or row_id not in reason
            or field not in reason
            or not isinstance(reviewer, str)
            or not reviewer.strip()
            or not set(source_ids) <= available_sources
        ):
            fail("compact v3 synthesize reasoning or source binding is invalid")
        by_id[expected_id] = adjudication
        by_row[row_id].append(expected_id)

    for source_row, row in zip(resolved["rows"], rows, strict=True):
        row_id = source_row["id"]
        purpose = purposes[row_id]
        if not isinstance(row, dict) or set(row) != ROW_KEYS_V3:
            fail(f"{row_id} compact row schema is invalid")
        if (
            row["purpose_sha256"] != purpose["purpose_sha256"]
            or row["row_class"] != purpose["row_class"]
            or source_row["purpose"] != purpose["canonical_purpose"]
            or row["artifact_class"] != source_row["artifact_class"]
            or row["whole_file_owner"] != source_row["whole_file_owner"]
            or row["css_selection"] != source_row["css_selection"]
            or row["response"] != source_row["response"]
            or row["edit_permission_class"] != _edit_permission_class(source_row["edit"])
            or row["completion_class"] != COMPLETION_CLASSES_V3[source_row["response"]]
        ):
            fail(f"{row_id} compact structured field came from nowhere or drifted")
        expected_routes = _expected_routes(source_row)
        validate_route_obligations(
            row["route_obligations"],
            expected=expected_routes,
            context=f"{row_id} route obligations",
        )
        expected_normative, expected_tools = _expected_authority_ids(
            source_row, purpose["row_class"]
        )
        if (
            row["normative_authority_ids"] != expected_normative
            or row["tool_or_target_authority_ids"] != expected_tools
            or not set(expected_normative + expected_tools) <= available_sources
        ):
            fail(f"{row_id} source authority IDs are incomplete or invented")
        expected_adjudications = by_row[row_id]
        expected_disposition = (
            "adjudicated" if expected_adjudications else "lane-agreement"
        )
        if (
            row["adjudication_ids"] != expected_adjudications
            or row["structured_disposition"] != expected_disposition
        ):
            fail(f"{row_id} structured disposition is invalid")
        for adjudication_id in expected_adjudications:
            adjudication = by_id[adjudication_id]
            if adjudication["resolved_value"] != row[adjudication["field"]]:
                fail(f"{row_id} adjudication does not bind the compact row")
    return {
        "rows": len(rows),
        "row_fields": len(ROW_KEYS_V3),
        "adjudications": len(adjudications),
    }


def validate_current_contract(root: Path) -> dict[str, int]:
    """Load and validate the maintained APG77C current machine authority."""
    debt_metrics = validate_css_known_debt(
        load_json(root / "docs/governance/language-profile-known-debt.json")
    )
    source_paths = private_source_binding_paths(root)
    assert source_paths is not None
    resolved = json.loads(
        (root / source_paths["maintained_scenario_fixture"]).read_text(
            encoding="utf-8"
        )
    )
    registry = load_json(root / source_paths["purpose_registry"])
    ledger = load_json(root / source_paths["h1_target_ledger"])
    lane_n = load_json(root / source_paths["lane_n"])
    lane_t2 = load_json(root / source_paths["lane_t2"])
    validate_lane_tombstone(
        load_json(root / source_paths["lane_t"]),
        expected_replacement=source_paths["lane_t2"],
    )
    compact_path = root / source_paths["compact_v3"]
    compact = load_json(compact_path)
    metrics = validate_resolved_structured_decisions_v3(
        root, resolved, lane_n, lane_t2, registry, ledger, compact
    )
    current_machine = {
        "resolved-structured-decisions-v3.json": compact_path.read_bytes(),
        "maintained-scenario-fixture.json": (
            root / source_paths["maintained_scenario_fixture"]
        ).read_bytes(),
        "purpose-and-target-fact-registry.json": (
            root / source_paths["purpose_registry"]
        ).read_bytes(),
        "fixture-manifest.json": (
            root / source_paths["normative_source_registry"]
        ).read_bytes(),
    }
    sizes = validate_proportionality(current_machine)
    return {
        **metrics,
        **{f"known_debt_{key}": item for key, item in debt_metrics.items()},
        "bytes": sizes["resolved-structured-decisions-v3.json"],
        "current_machine_bytes": sum(sizes.values()),
    }
