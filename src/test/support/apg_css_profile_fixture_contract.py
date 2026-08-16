"""Maintained APG77 contract for the APG76 CSS target-first fixture."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn


ROLE_STATES = {"known", "not-selected", "not-required", "unresolved"}
SELECTIONS = {"selected", "embedded-route", "route-to-owner", "non-trigger"}
SOURCE_KEYS = {
    "level", "normative_consequence", "publication_date", "published_uri",
    "refresh_condition", "rights", "shortname", "status",
}
AUXILIARY_KEYS = {
    "name", "normative_consequence", "publication_date", "published_uri",
    "refresh_condition", "rights", "status",
}
CSS_KNOWN_DEBT_IDS = tuple(f"CSS-QD-{index:03d}" for index in range(1, 6))
JAVASCRIPT_KNOWN_DEBT_IDS = tuple(f"JS-QD-{index:03d}" for index in range(1, 6))
KNOWN_DEBT_IDS = CSS_KNOWN_DEBT_IDS + JAVASCRIPT_KNOWN_DEBT_IDS
APG79C_KNOWN_DEBT_SHA256 = (
    "af23e96bba3c689d061e8486e5436405377558bc051bd5679e1e8dad33d4a4d4"
)
KNOWN_DEBT_ENTRY_SHA256 = {
    "CSS-QD-001": "14ffb223fd18dbb1bcb38fc25d289f70ee78d9551680b7bd5dca5413f517883c",
    "CSS-QD-002": "7680530fac6bd2ac51d1c85b58bc8ab7a29df231fff3a1a8682299ce5bc47ea8",
    "CSS-QD-003": "c2358e2da7bcdb04cd92984848dfcc31cdf4ab93d42902442b213f6279e9bf78",
    "CSS-QD-004": "9bd91683df9dcbb2d29a7ded7393bc76d194b5916851db5563486bb42c6e334e",
    "CSS-QD-005": "90e6d4d9de0be0bd43e12babe604bc4db03d3d94e92c6fbc4e82996d0496d53c",
    "JS-QD-001": "855d8d6555bab4bd73c20190ce8900c1c4d9d3e71a71aeed110ffa2151149aaa",
    "JS-QD-002": "9d93d85bb02ce09f28adf0c6530aa38a628bd5b82a997433690be266d6835f99",
    "JS-QD-003": "7351a67245165d4a95d0e878f259502fc172f3cac13e4fd956bee3cca103fced",
    "JS-QD-004": "f69e2dad60efe59e5ce086d7ff221fc08ebf745768f326afd812274c8b1b4073",
    "JS-QD-005": "f7ba6098693eabc834e17c27ac5c6729b00fff3ea900eda00ae657c92966e33d",
}
KNOWN_DEBT_KEYS = {
    "accepted_phase",
    "affected_scope",
    "blocks_provisional",
    "blocks_stable",
    "debt_id",
    "human_acceptance",
    "known_consequence",
    "owner",
    "profile",
    "refresh_condition",
    "repair_condition",
    "rollback_relevance",
    "severity",
    "status",
    "target_impact",
    "why_integration_remains_safe",
    "workaround_or_stop_behavior",
}


class FixtureError(ValueError):
    """The CSS target-first fixture is malformed or stale."""


def fail(message: str) -> NoReturn:
    raise FixtureError(message)


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            fail(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_object)
    validate_manifest(value, path.parent)
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"


def load_known_debt(path: Path) -> dict[str, Any]:
    """Load the direct regular canonical public known-debt owner."""
    if path.is_symlink() or not path.is_file():
        fail(f"known-debt file is absent or not direct regular: {path.name}")
    try:
        text = path.read_text(encoding="utf-8")
        value = json.loads(text, object_pairs_hook=_strict_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        fail(f"known-debt file is invalid: {error}")
    if text != _canonical_json(value):
        fail("known-debt file is not compact canonical JSON")
    validate_language_profile_known_debt(value)
    return value


def load_known_debt_summary(
    path: Path, value: Any, public_sha256: str
) -> dict[str, Any]:
    """Load and bind the direct regular publication-excluded debt summary."""

    if path.is_symlink() or not path.is_file():
        fail(f"known-debt summary is absent or not direct regular: {path.name}")
    try:
        text = path.read_text(encoding="utf-8")
        summary = json.loads(text, object_pairs_hook=_strict_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        fail(f"known-debt summary is invalid: {error}")
    if text != _canonical_json(summary):
        fail("known-debt summary is not compact canonical JSON")
    validate_known_debt_summary(summary, value, public_sha256)
    return summary


def known_debt_entry_sha256(value: dict[str, Any]) -> str:
    """Hash one canonical debt entry without presentation-only whitespace."""

    return hashlib.sha256(_canonical_json(value).rstrip("\n").encode("utf-8")).hexdigest()


def validate_language_profile_known_debt(value: Any) -> dict[str, int]:
    """Validate the exact APG77D CSS and APG79C/APG79E JavaScript debt set."""
    if not isinstance(value, dict) or set(value) != {
        "debts",
        "phase",
        "profile",
        "schema_version",
        "status",
    }:
        fail("known-debt top-level schema is invalid")
    if (
        type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or value["phase"] != "APG79E"
        or value["profile"] != "language-profiles"
        or value["status"] != "current-human-accepted-qualification-debt"
        or not isinstance(value["debts"], list)
    ):
        fail("known-debt identity or status is invalid")
    expected_severities = (
        "Medium", "Medium", "Medium", "Medium", "Low",
        "Medium", "Medium", "Medium", "Medium", "Medium",
    )
    observed_ids: list[str] = []
    for index, (debt, expected_id, expected_severity) in enumerate(
        zip(value["debts"], KNOWN_DEBT_IDS, expected_severities, strict=False)
    ):
        if not isinstance(debt, dict) or set(debt) != KNOWN_DEBT_KEYS:
            fail(f"known-debt entry {index} schema is invalid")
        for key in KNOWN_DEBT_KEYS - {"blocks_provisional", "blocks_stable"}:
            if not isinstance(debt[key], str) or not debt[key]:
                fail(f"known-debt entry {index} field {key} must be a nonempty string")
        if (
            type(debt["blocks_provisional"]) is not bool
            or type(debt["blocks_stable"]) is not bool
        ):
            fail(f"known-debt entry {index} blocking fields must be booleans")
        observed_ids.append(debt["debt_id"])
        css_entry = expected_id in CSS_KNOWN_DEBT_IDS
        expected_phase = "APG77D" if css_entry else "APG79C"
        if expected_id == "JS-QD-005":
            expected_phase = "APG79E"
        expected_profile = "css-language-profile" if css_entry else "javascript-language-profile"
        expected_blocks_stable = expected_severity == "Medium" or not css_entry
        if (
            debt["debt_id"] != expected_id
            or debt["severity"] != expected_severity
            or debt["accepted_phase"] != expected_phase
            or debt["profile"] != expected_profile
            or debt["status"] != "accepted-for-provisional-integration"
            or debt["blocks_provisional"]
            or debt["blocks_stable"] != expected_blocks_stable
        ):
            fail(f"known-debt entry {index} acceptance contract is invalid")
        if known_debt_entry_sha256(debt) != KNOWN_DEBT_ENTRY_SHA256[expected_id]:
            fail(f"known-debt entry {index} content drift")
    if len(value["debts"]) != len(KNOWN_DEBT_IDS):
        fail("known-debt set is incomplete or contains extra entries")
    if len(observed_ids) != len(set(observed_ids)):
        fail("duplicate known-debt ID")
    if tuple(observed_ids) != KNOWN_DEBT_IDS:
        fail("known-debt ID set is invalid")
    return {
        "debts": len(observed_ids),
        "css": len(CSS_KNOWN_DEBT_IDS),
        "javascript": len(JAVASCRIPT_KNOWN_DEBT_IDS),
        "low": expected_severities.count("Low"),
        "medium": expected_severities.count("Medium"),
    }


def validate_css_known_debt(value: Any) -> dict[str, int]:
    """Validate the complete register and return the preserved CSS subset."""

    validate_language_profile_known_debt(value)
    return {"debts": 5, "low": 1, "medium": 4}


def validate_known_debt_markdown(text: str, value: Any) -> None:
    """Require public prose to expose every current debt and lifecycle boundary."""

    metrics = validate_language_profile_known_debt(value)
    normalized = " ".join(text.split())
    expected_rows = (
        "| `CSS-QD-001` | Medium | Independent TARGET-007 source guard | Does not block under the explicit APG77D decision | Blocks until repaired or separately re-evaluated |",
        "| `CSS-QD-002` | Medium | Exhaustive disagreement enforcement | Does not block | Blocks |",
        "| `CSS-QD-003` | Medium | Adjudication-source relevance | Does not block | Blocks |",
        "| `CSS-QD-004` | Medium | Conflicting route-stop qualification | Does not block | Blocks |",
        "| `CSS-QD-005` | Low | Empty adjudication arrays | Does not block | Does not block by itself |",
        "| `JS-QD-001` | Medium | supporting CommonJS qualification machinery only | Does not block under the explicit APG79C decision | Blocks until repaired or separately re-evaluated |",
        "| `JS-QD-002` | Medium | JavaScript qualification harness diagnostics only | Does not block under the APG-owned non-sensitive fixture restriction | Blocks |",
        "| `JS-QD-003` | Medium | supporting static process-invocation qualification only | Does not block with mandatory human diff review | Blocks |",
        "| `JS-QD-004` | Medium | supporting output-contract qualification only | Does not block with exact-value and non-author review | Blocks |",
        "| `JS-QD-005` | Medium | supporting Test262 source-role and historical managed-report integrity qualification only | Does not block under the explicit APG79E decision and direct current-report verification | Blocks |",
    )
    if tuple(row.split("`")[1] for row in expected_rows) != KNOWN_DEBT_IDS:
        fail("known-debt Markdown row owner is incomplete")
    observed_rows = tuple(
        " ".join(line.split())
        for line in text.splitlines()
        if line.lstrip().startswith("| `") and "-QD-" in line
    )
    if observed_rows != expected_rows:
        fail("known-debt Markdown rows are absent, extra, duplicated, or inexact")
    required = (
        "zero Critical or High JavaScript debt",
        "blocks stable JavaScript maturity",
        "APG-owned non-sensitive fixtures",
        "9b56d503039c2907d371b37b72451b6e0b71cca41aa0cd23c074453229698827",
        "maintained proxy does not directly bind the APG79B managed-report bytes",
        "profile rollback deactivates only that profile's current entries",
    )
    if any(marker not in normalized for marker in required):
        fail("known-debt Markdown lifecycle boundary is incomplete")
    if metrics != {"debts": 10, "css": 5, "javascript": 5, "low": 1, "medium": 9}:
        fail("known-debt Markdown metrics are inconsistent")


def validate_known_debt_summary(summary: Any, value: Any, public_sha256: str) -> None:
    """Bind one publication-excluded summary to the public canonical owner."""

    validate_language_profile_known_debt(value)
    if public_sha256 != APG79C_KNOWN_DEBT_SHA256:
        fail("historical known-debt summary owner digest is invalid")
    expected = {
        "accepted_debt_ids": list(KNOWN_DEBT_IDS[:-1]),
        "accepted_severities": {"Low": 1, "Medium": 8},
        "critical_accepted": 0,
        "entry_sha256": {
            debt_id: KNOWN_DEBT_ENTRY_SHA256[debt_id]
            for debt_id in KNOWN_DEBT_IDS[:-1]
        },
        "high_accepted": 0,
        "phase": "APG79C",
        "public_owner_path": "docs/governance/language-profile-known-debt.json",
        "public_owner_sha256": APG79C_KNOWN_DEBT_SHA256,
        "schema_version": 1,
        "unaccepted_findings": 1,
    }
    if summary != expected:
        fail("public/private known-debt summary disagreement")


def validate_known_debt_profile_deactivation(
    value: Any, profile: str, remaining_debts: Any
) -> None:
    """Require rollback to deactivate only the selected profile's current debt."""

    validate_language_profile_known_debt(value)
    if profile not in {"css-language-profile", "javascript-language-profile"}:
        fail("known-debt rollback profile is invalid")
    if not isinstance(remaining_debts, list) or any(
        not isinstance(debt, dict) for debt in remaining_debts
    ):
        fail("known-debt rollback debt list is invalid")
    expected = [
        debt for debt in value["debts"] if debt["profile"] != profile
    ]
    if remaining_debts != expected:
        fail("known-debt rollback changed another profile's debt")


def validate_manifest(value: Any, fixture_root: Path) -> None:
    if not isinstance(value, dict) or set(value) != {
        "authored_phase", "authority", "cases", "fixture", "lifecycle",
        "source_bindings", "target_orientation",
    }:
        fail("manifest top-level schema is invalid")
    if value["fixture"] != "apg76-css-target-first" or value["authored_phase"] != "APG76":
        fail("fixture historical identity is invalid")
    authority = value["authority"]
    if authority.get("adr") != "0044" or authority.get("governing_adr") != "0042":
        fail("fixture authority is invalid")
    if authority.get("hardening_phase") != "APG77":
        fail("fixture hardening phase is invalid")
    if (
        authority.get("adr_status") != "Accepted with amendment"
        or authority.get("qualification_phases") != ["APG77A", "APG77B", "APG77C"]
        or authority.get("human_integration_phase") != "APG77D"
    ):
        fail("fixture current decision authority is invalid")
    if value["lifecycle"] != {
        "integrated": True,
        "state": "provisionally-integrated-with-known-debt",
        "catalog_row": "present",
        "projection": "present",
        "maturity_row": "provisional",
        "capability_route": "present",
        "project_selection": "present",
        "release_owner": "present",
        "maintained_test_owner": "apg77d-provisional-integration",
    }:
        fail("fixture current lifecycle is invalid")
    source_bindings = value["source_bindings"]
    if set(source_bindings) != {"auxiliary_authorities", "modules", "note", "rights"}:
        fail("source binding schema is invalid")
    modules = source_bindings.get("modules")
    if not isinstance(modules, list) or len(modules) != 21:
        fail("source module count drift")
    if len({module.get("shortname") for module in modules}) != 21:
        fail("source module identities are not unique")
    for module in modules:
        if not isinstance(module, dict) or set(module) != SOURCE_KEYS:
            fail("source module schema is incomplete")
        if not module["published_uri"].startswith("https://www.w3.org/TR/"):
            fail("source module URI is not an exact W3C publication")
        if module["publication_date"].replace("-", "") not in module["published_uri"]:
            fail("source module date and URI disagree")
        for field in ("normative_consequence", "refresh_condition", "rights"):
            if not module[field]:
                fail(f"source module lacks {field}")
    auxiliary = source_bindings["auxiliary_authorities"]
    if not isinstance(auxiliary, list) or len(auxiliary) != 2:
        fail("auxiliary normative authorities are incomplete")
    if any(not isinstance(item, dict) or set(item) != AUXILIARY_KEYS for item in auxiliary):
        fail("auxiliary authority schema is incomplete")
    cases = value["cases"]
    expected_ids = [f"APG76-FX-{index:03d}" for index in range(1, 15)]
    if not isinstance(cases, list) or [case.get("id") for case in cases] != expected_ids:
        fail("fixture cases are not complete and ordered")
    declared_paths: set[str] = set()
    for case in cases:
        selection = case.get("css_selection")
        if selection not in SELECTIONS:
            fail(f"{case['id']} has an unknown selection")
        for role in ("parser_role_state", "transform_role_state", "browser_role_state"):
            if case.get(role) not in ROLE_STATES:
                fail(f"{case['id']} has an unknown role state")
        present = case.get("present_evidence")
        required = case.get("required_evidence")
        if not isinstance(present, list) or not isinstance(required, list):
            fail(f"{case['id']} evidence arrays are invalid")
        if set(present) & set(required):
            fail(f"{case['id']} copies present evidence into required evidence")
        for path_text in case.get("paths", []):
            path = PurePosixPath(path_text)
            if path.is_absolute() or ".." in path.parts:
                fail(f"{case['id']} has an unsafe path")
            if not (fixture_root / path).is_file():
                fail(f"{case['id']} path is missing")
            declared_paths.add(path.as_posix())
    actual_paths = {
        path.relative_to(fixture_root).as_posix()
        for path in fixture_root.rglob("*") if path.is_file()
    }
    if actual_paths != declared_paths | {"README.md", "fixture-manifest.json"}:
        fail("fixture file ownership is incomplete")
    by_id = {case["id"]: case for case in cases}
    if "unknown" not in by_id["APG76-FX-008"]["owned_conclusion"]:
        fail("FX-008 collapses unknown media to false")
    if "stronger than token parsing" not in by_id["APG76-FX-008"]["owned_conclusion"]:
        fail("FX-008 reduces supports to parsing")
    if "same element" not in by_id["APG76-FX-010"]["owned_conclusion"]:
        fail("FX-010 invents an element-specific math result")
    if "distinct descendant color" not in by_id["APG76-FX-011"]["owned_conclusion"]:
        fail("FX-011 does not demonstrate currentColor re-resolution")
    if "read-only" not in by_id["APG76-FX-013"]["owned_conclusion"]:
        fail("FX-013 forbids semantic reading solely because edits are routed")
    if "framework-selected" not in value["target_orientation"]["tool_roles"]:
        fail("target tool role ignores the framework-selected pipeline")
    target = value["target_orientation"]
    if target["theme"]["host_components_with_style_regions"] != 4:
        fail("theme host style-region count drift")
    if "embedded style region" not in target["website"]["css_relevance"]:
        fail("website embedded SVG CSS is omitted")
    conditions = (fixture_root / "src/conditions.css").read_text(encoding="utf-8")
    for marker in (
        "(width: unknown)", "not (min-widht: 48rem)",
        "(min-widht: 48rem), (min-width: 64rem)", "(width >= )",
        "not unknown-medium",
    ):
        if marker not in conditions:
            fail(f"media-query control is missing: {marker}")


def validate_fixture_readme(text: str, *, integrated: bool) -> None:
    normalized = " ".join(text.split()).lower()
    required = (
        "historical apg76 fixture",
        "apg77 maintained test owner",
        "twenty-one source modules",
        "framework-selected",
        "browser remains unresolved",
    )
    if any(marker not in normalized for marker in required):
        fail("fixture README lacks current APG77 ownership or evidence")
    lifecycle = "provisionally integrated" if integrated else "repair-required"
    if lifecycle not in normalized:
        fail("fixture README lifecycle is stale")
