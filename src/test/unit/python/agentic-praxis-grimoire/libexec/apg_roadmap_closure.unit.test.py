#!/usr/bin/env python3
"""Unit tests for libexec/apg_roadmap_closure.py."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from src.test.apg_test_support import repository_root

REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import apg_roadmap_closure as closure  # noqa: E402
import apg_roadmap_contract as contract  # noqa: E402


class APG139MaturityUnitTests(unittest.TestCase):
    """Individual lifecycle links and absence observations never confer review authority."""

    def test_pending_candidate_is_not_terminal_receipt(self):
        candidate = closure.load_json(REPOSITORY_ROOT / "docs/governance/maturity/apg139/astro-profile.json")
        self.assertTrue(closure.matches(candidate, contract.maturity_candidate_schema()))
        self.assertFalse(closure.matches(candidate, contract.decision_schema()))
        candidate["independent_review"] = "skills/README.md"
        self.assertFalse(closure.matches(candidate, contract.maturity_candidate_schema()))

    def test_complete_debt_view_cannot_hide_nonblocking_or_resolved_debt(self):
        records, errors = closure.load_records(REPOSITORY_ROOT)
        self.assertEqual(errors, [])
        maintenance = closure.check_maintenance(REPOSITORY_ROOT, records, [])
        for identity, field, hidden in (
            ("css-language-profile", "active_debts", "CSS-QD-005"),
            ("javascript-language-profile", "resolved_debts", "JS-QD-001"),
        ):
            damaged = copy.deepcopy(records)
            leaf = next(r for r in damaged["maturity"]["skills"] if r["skill_id"] == identity)
            leaf[field].remove(hidden)
            errors = []
            closure.check_maturity(REPOSITORY_ROOT, damaged, maintenance, errors)
            self.assertIn("maturity: path/projection/debt/evidence mismatch", errors)

    def test_pending_leaf_cannot_borrow_trigger_or_claim_review(self):
        records, _ = closure.load_records(REPOSITORY_ROOT)
        triggers = closure.check_maintenance(REPOSITORY_ROOT, records, [])
        leaf = next(r for r in records["maturity"]["skills"] if r["skill_id"] == "astro-profile")
        # Reconstruct the pending state explicitly from the terminal leaf.
        leaf.update(disposition_status="PENDING_V0110_B", independent_review=None)
        self.assertTrue(closure.maturity_decision_valid(REPOSITORY_ROOT, leaf, triggers))
        for key, value in (("maintenance_ref", "MATURITY:jsx-language-profile"),
                           ("next_lifecycle_trigger", "Review later"),
                           ("independent_review", "skills/README.md")):
            damaged = copy.deepcopy(leaf)
            damaged[key] = value
            self.assertFalse(closure.maturity_decision_valid(REPOSITORY_ROOT, damaged, triggers))

    def test_trigger_and_absence_observation_bind_the_actual_leaf(self):
        records, _ = closure.load_records(REPOSITORY_ROOT)
        trigger = next(r for r in records["maintenance"]["triggers"]
                       if r["trigger_id"] == "MATURITY:astro-profile")
        debts = {r["debt_id"]: r for r in closure.load_json(REPOSITORY_ROOT / contract.DEBT_AUTHORITY)["debts"]}
        self.assertTrue(closure.maturity_trigger_valid(REPOSITORY_ROOT, trigger, debts))
        damaged = copy.deepcopy(trigger)
        damaged["refresh_condition"] = "Gather more evidence"
        self.assertFalse(closure.maturity_trigger_valid(REPOSITORY_ROOT, damaged, debts))
        candidate = closure.load_json(REPOSITORY_ROOT / trigger["state_evidence"][0])
        for key, value in (("skill_id", "jsx-language-profile"),
                           ("controlling_debt_ids", ["JS-QD-005"]),
                           ("next_lifecycle_trigger", "Review later")):
            bad = copy.deepcopy(candidate)
            bad[key] = value
            with mock.patch.object(closure, "load_json", return_value=bad):
                self.assertFalse(closure.maturity_trigger_valid(REPOSITORY_ROOT, trigger, debts))
        with mock.patch.object(closure, "load_json", side_effect=ValueError("malformed")):
            self.assertFalse(closure.maturity_trigger_valid(REPOSITORY_ROOT, trigger, debts))


class TestJsonAndSchemaPrimitives(unittest.TestCase):
    """Test low-level JSON parsing, duplicate key rejection, and schema matcher."""

    def test_unique_object_detects_duplicate_keys(self) -> None:
        pairs = [("a", 1), ("b", 2)]
        self.assertEqual(closure.unique_object(pairs), {"a": 1, "b": 2})

        dup_pairs = [("a", 1), ("b", 2), ("a", 3)]
        with self.assertRaises(ValueError) as ctx:
            closure.unique_object(dup_pairs)
        self.assertIn("duplicate JSON key", str(ctx.exception))

    def test_load_json_regular_duplicate_symlink_and_size_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "record.json"
            path.write_text('{"key": "value"}')
            self.assertEqual(closure.load_json(path), {"key": "value"})
            for raw in ('{"dup": 1, "dup": 2}', 'x' * (513 * 1024)):
                path.write_text(raw)
                with self.assertRaises(ValueError):
                    closure.load_json(path)
            link = Path(temporary) / "linked.json"
            link.symlink_to(path)
            with self.assertRaises(ValueError):
                closure.load_json(link)

    def test_matches_types_and_values(self) -> None:
        # String type and minLength
        str_shape = {"type": "string", "minLength": 1}
        self.assertTrue(closure.matches("hello", str_shape))
        self.assertFalse(closure.matches("", str_shape))
        self.assertFalse(closure.matches("   ", str_shape))
        self.assertFalse(closure.matches(123, str_shape))

        # Const shape
        const_shape = {"type": "string", "const": "v0.11"}
        self.assertTrue(closure.matches("v0.11", const_shape))
        self.assertFalse(closure.matches("v0.12", const_shape))

        # Enum shape
        enum_shape = {"type": "string", "enum": ["OPEN", "DELIVERED"]}
        self.assertTrue(closure.matches("OPEN", enum_shape))
        self.assertTrue(closure.matches("DELIVERED", enum_shape))
        self.assertFalse(closure.matches("REJECTED", enum_shape))

        # Nullable shape (anyOf)
        nullable_shape = {"anyOf": [{"type": "string"}, {"type": "null"}]}
        self.assertTrue(closure.matches("text", nullable_shape))
        self.assertTrue(closure.matches(None, nullable_shape))
        self.assertFalse(closure.matches(123, nullable_shape))

        # Boolean shape
        bool_shape = {"type": "boolean"}
        self.assertTrue(closure.matches(True, bool_shape))
        self.assertTrue(closure.matches(False, bool_shape))
        self.assertFalse(closure.matches("True", bool_shape))

        # Array shape with uniqueItems
        arr_shape = {"type": "array", "items": {"type": "string"}}
        self.assertTrue(closure.matches(["a", "b", "c"], arr_shape))
        self.assertFalse(closure.matches(["a", "b", "a"], arr_shape))  # duplicate
        self.assertFalse(closure.matches(["a", 123], arr_shape))  # item type mismatch

        # Dict shape with properties
        dict_shape = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "active": {"type": "boolean"},
            },
        }
        self.assertTrue(closure.matches({"id": "1", "active": True}, dict_shape))
        self.assertFalse(closure.matches({"id": "1"}, dict_shape))  # missing key
        self.assertFalse(closure.matches({"id": "1", "active": True, "extra": 2}, dict_shape))  # extra key
        self.assertFalse(closure.matches({"id": "1", "active": "yes"}, dict_shape))  # type mismatch


class TestPathAndRefValidation(unittest.TestCase):
    """Test public_ref and refs_valid path checking."""

    def test_public_ref_valid_and_anchors(self) -> None:
        self.assertTrue(closure.public_ref(REPOSITORY_ROOT, "skills/README.md"))
        self.assertTrue(closure.public_ref(REPOSITORY_ROOT, "skills/README.md#anchor"))

    def test_public_ref_adverse_cases(self) -> None:
        # Non-existent file
        self.assertFalse(closure.public_ref(REPOSITORY_ROOT, "nonexistent.md"))

        # Directory instead of file
        self.assertFalse(closure.public_ref(REPOSITORY_ROOT, "docs"))

        # Absolute path
        self.assertFalse(closure.public_ref(REPOSITORY_ROOT, "/etc/passwd"))

        # Upwards traversal '..'
        self.assertFalse(closure.public_ref(REPOSITORY_ROOT, "../outside.md"))

        # Empty reference
        self.assertFalse(closure.public_ref(REPOSITORY_ROOT, ""))

        # Private path
        self.assertFalse(closure.public_ref(REPOSITORY_ROOT, "private/secret.md"))

    def test_refs_valid(self) -> None:
        self.assertFalse(closure.refs_valid(REPOSITORY_ROOT, []))
        self.assertTrue(closure.refs_valid(REPOSITORY_ROOT, ["skills/README.md", "README.md"]))
        self.assertFalse(closure.refs_valid(REPOSITORY_ROOT, ["skills/README.md", "nonexistent.md"]))


class TestRecordLoading(unittest.TestCase):
    """Test load_records against disk and simulated errors."""


    def test_load_records_schema_tamper(self) -> None:
        records, errors = closure.load_records(REPOSITORY_ROOT)
        with mock.patch("apg_roadmap_closure.load_json") as mock_load:
            def fake_load(path: Path) -> dict:
                data = json.loads(path.read_text(encoding="utf-8"))
                if path.name.endswith(".schema.json"):
                    data["properties"]["release"]["const"] = "v0.99"
                return data
            mock_load.side_effect = fake_load
            recs, errs = closure.load_records(REPOSITORY_ROOT)
            self.assertTrue(any("schema differs from maintained contract" in e for e in errs))

    def test_load_records_invalid_shape(self) -> None:
        with mock.patch("apg_roadmap_closure.load_json") as mock_load:
            def fake_load(path: Path) -> dict:
                data = json.loads(path.read_text(encoding="utf-8"))
                if path.name == "maintenance-triggers.json":
                    data["triggers"] = [{"not_a_valid": "trigger"}]
                return data
            mock_load.side_effect = fake_load
            recs, errs = closure.load_records(REPOSITORY_ROOT)
            self.assertTrue(any("maintenance: invalid record shape" in e for e in errs))

    def test_load_records_duplicate_or_unordered_identities(self) -> None:
        with mock.patch("apg_roadmap_closure.load_json") as mock_load:
            def fake_load(path: Path) -> dict:
                data = json.loads(path.read_text(encoding="utf-8"))
                if path.name == "maintenance-triggers.json":
                    # reverse triggers list to break sorting
                    data["triggers"] = list(reversed(data["triggers"]))
                return data
            mock_load.side_effect = fake_load
            recs, errs = closure.load_records(REPOSITORY_ROOT)
            self.assertTrue(any("maintenance: duplicate or unordered identities" in e for e in errs))

    def test_load_records_unreadable_file_handling(self) -> None:
        with mock.patch("apg_roadmap_closure.load_json", side_effect=OSError("Disk error")):
            recs, errs = closure.load_records(REPOSITORY_ROOT)
            self.assertTrue(any("unreadable or malformed JSON" in e for e in errs))


class TestMaintenanceValidation(unittest.TestCase):
    """Test check_maintenance and fail-closed trigger verification."""


    def test_check_maintenance_identity_mismatch(self) -> None:
        records, _ = closure.load_records(REPOSITORY_ROOT)
        tampered = copy.deepcopy(records)
        # Remove a trigger
        tampered["maintenance"]["triggers"] = tampered["maintenance"]["triggers"][:-1]
        errors: list[str] = []
        closure.check_maintenance(REPOSITORY_ROOT, tampered, errors)
        self.assertIn("maintenance: frozen trigger identity mismatch", errors)

    def test_check_maintenance_binding_tamper(self) -> None:
        records, _ = closure.load_records(REPOSITORY_ROOT)
        tampered = copy.deepcopy(records)
        # Modify refresh_condition of first trigger
        tampered["maintenance"]["triggers"][0]["refresh_condition"] = "tampered condition"
        errors: list[str] = []
        closure.check_maintenance(REPOSITORY_ROOT, tampered, errors)
        self.assertIn("maintenance: trigger/source/state binding mismatch", errors)

    def test_check_maintenance_unknown_state_and_state_evidence(self) -> None:
        records, _ = closure.load_records(REPOSITORY_ROOT)
        # When current_state is UNKNOWN, state_evidence does not need to be valid refs
        tampered = copy.deepcopy(records)
        for trig in tampered["maintenance"]["triggers"]:
            if trig["trigger_id"] == "JS-QD-005":
                trig["current_state"] = "UNKNOWN"
                trig["state_evidence"] = []  # empty is allowed when UNKNOWN
        errors: list[str] = []
        closure.check_maintenance(REPOSITORY_ROOT, tampered, errors)
        # No errors for empty state_evidence on UNKNOWN trigger
        self.assertEqual(errors, [])

        # But when current_state is FALSE or TRUE, state_evidence must be valid refs
        tampered["maintenance"]["triggers"][0]["current_state"] = "FALSE"
        tampered["maintenance"]["triggers"][0]["state_evidence"] = ["nonexistent-evidence.md"]
        errors = []
        closure.check_maintenance(REPOSITORY_ROOT, tampered, errors)
        self.assertIn("maintenance: trigger/source/state binding mismatch", errors)

    def test_check_maintenance_js_qd_005_interpretation_ruling(self) -> None:
        records, _ = closure.load_records(REPOSITORY_ROOT)
        tampered = copy.deepcopy(records)
        for trig in tampered["maintenance"]["triggers"]:
            if trig["trigger_id"] == "JS-QD-005":
                trig["interpretation"] = "WRONG_INTERPRETATION"
        errors: list[str] = []
        closure.check_maintenance(REPOSITORY_ROOT, tampered, errors)
        self.assertIn("maintenance: trigger/source/state binding mismatch", errors)


class TestCompatibilityValidation(unittest.TestCase):
    """Test check_compatibility and overclaim rejection."""


    def test_check_compatibility_identity_mismatch(self) -> None:
        records, _ = closure.load_records(REPOSITORY_ROOT)
        tampered = copy.deepcopy(records)
        tampered["compatibility"]["watches"] = tampered["compatibility"]["watches"][:-1]
        errors: list[str] = []
        closure.check_compatibility(REPOSITORY_ROOT, tampered, errors)
        self.assertIn("compatibility: required watch identity mismatch", errors)

    def test_check_compatibility_watch_overclaim(self) -> None:
        records, _ = closure.load_records(REPOSITORY_ROOT)
        # Status WATCH cannot claim supported_cases or qualification_evidence
        tampered = copy.deepcopy(records)
        for watch in tampered["compatibility"]["watches"]:
            if watch["status"] == "WATCH":
                watch["supported_cases"] = ["some-case"]
                break
        errors: list[str] = []
        closure.check_compatibility(REPOSITORY_ROOT, tampered, errors)
        self.assertIn("compatibility: unavailable evidence or unsupported qualification claim", errors)

    def test_check_compatibility_invalid_observation_date(self) -> None:
        records, _ = closure.load_records(REPOSITORY_ROOT)
        tampered = copy.deepcopy(records)
        tampered["compatibility"]["watches"][0]["observation_date"] = "09/12/2026"
        errors: list[str] = []
        closure.check_compatibility(REPOSITORY_ROOT, tampered, errors)
        self.assertIn("compatibility: unavailable evidence or unsupported qualification claim", errors)

    def test_check_compatibility_fixture_identity_checksum(self) -> None:
        records, _ = closure.load_records(REPOSITORY_ROOT)
        tampered = copy.deepcopy(records)
        # Create valid fixture identity
        real_file = "docs/architecture/jaca-ci-handoff.md"
        real_sha = hashlib.sha256((REPOSITORY_ROOT / real_file).read_bytes()).hexdigest()
        for watch in tampered["compatibility"]["watches"]:
            if watch["watch_id"] == "JACA-CI":
                watch["status"] = "HANDOFF_CLOSED"
                watch["qualification_evidence"] = [real_file]
                watch["fixture_identity"] = {"path": real_file, "sha256": real_sha}
                break
        errors: list[str] = []
        closure.check_compatibility(REPOSITORY_ROOT, tampered, errors)
        self.assertEqual(errors, [])

        # Corrupted sha256
        tampered["compatibility"]["watches"][1]["fixture_identity"]["sha256"] = "0" * 64
        errors = []
        closure.check_compatibility(REPOSITORY_ROOT, tampered, errors)
        self.assertIn("compatibility: unavailable evidence or unsupported qualification claim", errors)

        # Non-existent fixture path (public_ref is False)
        tampered["compatibility"]["watches"][1]["fixture_identity"]["path"] = "docs/nonexistent.json"
        errors = []
        closure.check_compatibility(REPOSITORY_ROOT, tampered, errors)
        self.assertIn("compatibility: unavailable evidence or unsupported qualification claim", errors)


class TestCatalogAndMaturityDecision(unittest.TestCase):
    """Test catalog parsing and maturity_decision_valid logic."""

    def test_catalog_parses_real_skills_readme(self) -> None:
        cat = closure.catalog(REPOSITORY_ROOT)
        self.assertEqual(len(cat), 45)
        self.assertIn("python-language-profile", cat)
        self.assertEqual(cat["python-language-profile"][1], "stable")
        self.assertEqual(cat["css-language-profile"][1], "provisional")

    def test_catalog_detects_duplicate_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir) / "skills"
            skills_dir.mkdir()
            readme = skills_dir / "README.md"
            readme.write_text(
                "## Current development catalog\n\n"
                "| [`dup-skill`](dup/SKILL.md) | desc | `stable` |\n"
                "| [`dup-skill`](dup/SKILL.md) | desc | `stable` |\n\n"
                "## Next section\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError) as ctx:
                closure.catalog(Path(tmpdir))
            self.assertIn("duplicate catalog skill", str(ctx.exception))

    def test_maturity_decision_valid_rules(self) -> None:
        maintenance = {"MATURITY:css-language-profile": {"current_state": "FALSE", "affected_skills": ["css-language-profile"], "refresh_condition": "fixture refresh"}}

        # EXISTING_STABLE valid when current_maturity is stable
        row_es = {"disposition_status": "EXISTING_STABLE", "current_maturity": "stable"}
        self.assertTrue(closure.maturity_decision_valid(REPOSITORY_ROOT, row_es, maintenance))
        row_es_bad = {"disposition_status": "EXISTING_STABLE", "current_maturity": "provisional"}
        self.assertFalse(closure.maturity_decision_valid(REPOSITORY_ROOT, row_es_bad, maintenance))

        # PENDING_V0110_B valid when current_maturity is provisional
        row_pending = {"disposition_status": "PENDING_V0110_B", "current_maturity": "provisional"}
        self.assertTrue(closure.maturity_decision_valid(REPOSITORY_ROOT, row_pending, maintenance))
        row_pending_bad = {"disposition_status": "PENDING_V0110_B", "current_maturity": "stable"}
        self.assertFalse(closure.maturity_decision_valid(REPOSITORY_ROOT, row_pending_bad, maintenance))

        # Missing independent review
        row_no_rev = {
            "disposition_status": "STABLE",
            "current_maturity": "stable",
            "independent_review": None,
            "evidence": {k: ["skills/README.md"] for k in contract.EVIDENCE_CATEGORIES},
            "blocking_debts": [],
        }
        self.assertFalse(closure.maturity_decision_valid(REPOSITORY_ROOT, row_no_rev, maintenance))

        # STABLE blocked if blocking_debts non-empty (debt cannot promote to stable!)
        row_blocked = {
            "disposition_status": "STABLE",
            "current_maturity": "stable",
            "independent_review": "skills/README.md",
            "evidence": {k: ["skills/README.md"] for k in contract.EVIDENCE_CATEGORIES},
            "blocking_debts": ["CSS-QD-001"],
        }
        self.assertFalse(closure.maturity_decision_valid(REPOSITORY_ROOT, row_blocked, maintenance))

        # STABLE valid when debt empty and maturity stable
        row_stable = {
            "disposition_status": "STABLE",
            "current_maturity": "stable",
            "independent_review": "skills/README.md",
            "evidence": {k: ["skills/README.md"] for k in contract.EVIDENCE_CATEGORIES},
            "blocking_debts": [],
        }
        self.assertTrue(closure.maturity_decision_valid(REPOSITORY_ROOT, row_stable, maintenance))

        # PROVISIONAL_MAINTENANCE requires trigger current_state == FALSE
        row_pm = {
            "disposition_status": "PROVISIONAL_MAINTENANCE",
            "current_maturity": "provisional",
            "independent_review": "skills/README.md",
            "evidence": {k: ["skills/README.md"] for k in contract.EVIDENCE_CATEGORIES},
            "maintenance_ref": "MATURITY:css-language-profile", "skill_id": "css-language-profile",
            "next_lifecycle_trigger": "fixture refresh",
        }
        self.assertTrue(closure.maturity_decision_valid(REPOSITORY_ROOT, row_pm, maintenance))

        # If maintenance trigger state is TRUE or missing, PROVISIONAL_MAINTENANCE fails
        maint_true = {"MATURITY:css-language-profile": {"current_state": "TRUE"}}
        self.assertFalse(closure.maturity_decision_valid(REPOSITORY_ROOT, row_pm, maint_true))

        # DEPRECATED_OR_SUPERSEDED requires current_maturity deprecated
        row_dep = {
            "disposition_status": "DEPRECATED_OR_SUPERSEDED",
            "current_maturity": "deprecated",
            "independent_review": "skills/README.md",
            "evidence": {k: ["skills/README.md"] for k in contract.EVIDENCE_CATEGORIES},
        }
        self.assertTrue(closure.maturity_decision_valid(REPOSITORY_ROOT, row_dep, maintenance))

        # Invalid ref in evidence category fails
        row_bad_ev = {
            "disposition_status": "STABLE",
            "current_maturity": "stable",
            "independent_review": "skills/README.md",
            "evidence": {k: (["skills/README.md"] if k != "rollback" else ["docs/nonexistent.md"]) for k in contract.EVIDENCE_CATEGORIES},
            "blocking_debts": [],
        }
        self.assertFalse(closure.maturity_decision_valid(REPOSITORY_ROOT, row_bad_ev, maintenance))


class TestMaturityValidation(unittest.TestCase):
    """Test check_maturity and projection symlink verification."""

    def test_check_maturity_valid_on_repository(self) -> None:
        records, _ = closure.load_records(REPOSITORY_ROOT)
        errors: list[str] = []
        maintenance = closure.check_maintenance(REPOSITORY_ROOT, records, errors)
        rows = closure.check_maturity(REPOSITORY_ROOT, records, maintenance, errors)
        self.assertEqual(errors, [])
        self.assertEqual(len(rows), 45)

    def test_check_maturity_provisional_faking_existing_stable(self) -> None:
        records, _ = closure.load_records(REPOSITORY_ROOT)
        tampered = copy.deepcopy(records)
        for s in tampered["maturity"]["skills"]:
            if s["skill_id"] in contract.PROVISIONAL:
                s["disposition_status"] = "EXISTING_STABLE"
                s["current_maturity"] = "stable"
                break
        errors: list[str] = []
        closure.check_maturity(REPOSITORY_ROOT, tampered, {}, errors)
        self.assertIn("maturity: path/projection/debt/evidence mismatch", errors)

    def test_check_maturity_identity_and_projection_mismatches(self) -> None:
        records, _ = closure.load_records(REPOSITORY_ROOT)
        # 1. Skill row removed -> count != 45
        tampered = copy.deepcopy(records)
        tampered["maturity"]["skills"].pop()
        errors: list[str] = []
        closure.check_maturity(REPOSITORY_ROOT, tampered, {}, errors)
        self.assertIn("maturity: canonical/catalog/ledger identity mismatch", errors)

        # 2. Projection inventory mismatch
        with mock.patch("pathlib.Path.iterdir") as mock_iter:
            mock_iter.return_value = [Path("only-one-link")]
            errors = []
            closure.check_maturity(REPOSITORY_ROOT, records, {}, errors)
            self.assertIn("maturity: projection inventory mismatch", errors)


class TestDispositionValidation(unittest.TestCase):
    """Test disposition_valid for various lifecycle transitions."""

    def test_disposition_valid_open(self) -> None:
        row_open = {"status": "OPEN", "disposition": None}
        self.assertTrue(closure.disposition_valid(REPOSITORY_ROOT, row_open, ({}, {}, {})))

        row_open_bad = {"status": "OPEN", "disposition": {"decision_ref": "some.md"}}
        self.assertFalse(closure.disposition_valid(REPOSITORY_ROOT, row_open_bad, ({}, {}, {})))

    def test_disposition_valid_delivered_and_rejected(self) -> None:
        disp = {
            "decision_ref": "skills/README.md",
            "review_ref": "skills/README.md",
            "qualification_refs": ["skills/README.md"],
            "rationale": "Valid delivery",
            "maintenance_ref": None,
            "compatibility_ref": None,
            "maturity_ref": None,
        }
        row_delivered = {
            "status": "DELIVERED",
            "allowed_outcomes": ["DELIVERED", "REJECTED"],
            "inherited_class": "EXTERNAL_GATE",
            "disposition": disp,
        }
        self.assertTrue(closure.disposition_valid(REPOSITORY_ROOT, row_delivered, ({}, {}, {})))

        row_rejected = {
            "status": "REJECTED",
            "allowed_outcomes": ["DELIVERED", "REJECTED"],
            "inherited_class": "EXTERNAL_GATE",
            "disposition": disp,
        }
        self.assertTrue(closure.disposition_valid(REPOSITORY_ROOT, row_rejected, ({}, {}, {})))

        # Status not in allowed_outcomes fails
        row_not_allowed = copy.deepcopy(row_delivered)
        row_not_allowed["allowed_outcomes"] = ["REJECTED"]
        self.assertFalse(closure.disposition_valid(REPOSITORY_ROOT, row_not_allowed, ({}, {}, {})))

    def test_disposition_valid_maintenance_trigger(self) -> None:
        disp = {
            "decision_ref": "skills/README.md",
            "review_ref": "skills/README.md",
            "qualification_refs": ["skills/README.md"],
            "rationale": "Trigger verified clear",
            "maintenance_ref": "CSS-QD-001",
            "compatibility_ref": None,
            "maturity_ref": None,
        }
        row = {
            "status": "MAINTENANCE_TRIGGER",
            "allowed_outcomes": ["MAINTENANCE_TRIGGER", "REJECTED"],
            "trigger_ref": "CSS-QD-001",
            "inherited_class": "CONDITION_TRIGGERED",
            "disposition": disp,
        }
        maint_ok = {"CSS-QD-001": {"current_state": "FALSE"}}
        self.assertTrue(closure.disposition_valid(REPOSITORY_ROOT, row, (maint_ok, {}, {})))

        # If trigger current_state is TRUE, disposition fails
        maint_bad = {"CSS-QD-001": {"current_state": "TRUE"}}
        self.assertFalse(closure.disposition_valid(REPOSITORY_ROOT, row, (maint_bad, {}, {})))

    def test_disposition_valid_consumer_handoff(self) -> None:
        disp = {
            "decision_ref": "skills/README.md",
            "review_ref": "skills/README.md",
            "qualification_refs": ["skills/README.md"],
            "rationale": "Consumer handoff complete",
            "maintenance_ref": None,
            "compatibility_ref": "JACA-CI",
            "maturity_ref": None,
        }
        row = {
            "item_id": "APGR-CI-QUAL",
            "status": "CONSUMER_HANDOFF_CLOSED",
            "allowed_outcomes": ["CONSUMER_HANDOFF_CLOSED", "REJECTED"],
            "inherited_class": "EXTERNAL_GATE",
            "disposition": disp,
        }
        compat_ok = {"JACA-CI": {"status": "HANDOFF_CLOSED", "inherited_item_ids": ["APGR-CI-QUAL"]}}
        self.assertTrue(closure.disposition_valid(REPOSITORY_ROOT, row, ({}, compat_ok, {})))

        compat_bad = {"JACA-CI": {"status": "WATCH", "inherited_item_ids": ["APGR-CI-QUAL"]}}
        self.assertFalse(closure.disposition_valid(REPOSITORY_ROOT, row, ({}, compat_bad, {})))

        # Also test when item_id is not in inherited_item_ids
        compat_unmatched = {"JACA-CI": {"status": "HANDOFF_CLOSED", "inherited_item_ids": ["OTHER-ITEM"]}}
        self.assertFalse(closure.disposition_valid(REPOSITORY_ROOT, row, ({}, compat_unmatched, {})))

    def test_disposition_valid_provisional_maturity(self) -> None:
        disp = {
            "decision_ref": "skills/README.md",
            "review_ref": "skills/README.md",
            "qualification_refs": ["skills/README.md"],
            "rationale": "Maturity stabilized",
            "maintenance_ref": None,
            "compatibility_ref": None,
            "maturity_ref": "css-language-profile",
        }
        row = {
            "item_id": "MATURITY:css-language-profile",
            "status": "STABLE",
            "allowed_outcomes": ["STABLE", "PROVISIONAL_MAINTENANCE", "DEPRECATED_OR_SUPERSEDED"],
            "inherited_class": "PROVISIONAL_MATURITY",
            "disposition": disp,
        }
        maturity_ok = {"css-language-profile": {"disposition_status": "STABLE",
                       "independent_review": "skills/README.md", "maintenance_ref": None}}
        self.assertTrue(closure.disposition_valid(REPOSITORY_ROOT, row, ({}, {}, maturity_ok)))

        maturity_bad = {"css-language-profile": {"disposition_status": "PENDING_V0110_B"}}
        self.assertFalse(closure.disposition_valid(REPOSITORY_ROOT, row, ({}, {}, maturity_bad)))

    def test_disposition_valid_empty_qualification_refs(self) -> None:
        disp = {
            "decision_ref": "skills/README.md",
            "review_ref": "skills/README.md",
            "qualification_refs": [],
            "rationale": "Empty qualification refs",
            "maintenance_ref": None,
            "compatibility_ref": None,
            "maturity_ref": None,
        }
        row = {
            "item_id": "APGR-CI-QUAL",
            "status": "DELIVERED",
            "allowed_outcomes": ["DELIVERED"],
            "inherited_class": "EXTERNAL_GATE",
            "disposition": disp,
        }
        self.assertFalse(closure.disposition_valid(REPOSITORY_ROOT, row, ({}, {}, {})))


class TestClosureValidation(unittest.TestCase):
    """Test check_closure logic and totals calculation."""

    def test_check_closure_valid_55_terminal_zero_open(self) -> None:
        records, _ = closure.load_records(REPOSITORY_ROOT)
        errors: list[str] = []
        m = closure.check_maintenance(REPOSITORY_ROOT, records, errors)
        comp = closure.check_compatibility(REPOSITORY_ROOT, records, errors)
        mat = closure.check_maturity(REPOSITORY_ROOT, records, m, errors)
        totals = closure.check_closure(REPOSITORY_ROOT, records, (m, comp, mat), errors)

        self.assertEqual(errors, [])
        self.assertEqual(totals["expected_total"], 55)
        self.assertEqual(totals["total_inherited_rows"], 55)
        self.assertEqual((totals["terminal_rows"], totals["open_rows"], totals["invalid_rows"]),
                         (55, 0, 0))
        self.assertEqual(totals["unknown_rows"], 0)
        self.assertEqual(totals["missing_rows"], 0)

    def test_check_closure_historical_exclusions_mismatch(self) -> None:
        records, _ = closure.load_records(REPOSITORY_ROOT)
        tampered = copy.deepcopy(records)
        tampered["closure"]["historical_exclusions"] = []
        errors: list[str] = []
        closure.check_closure(REPOSITORY_ROOT, tampered, ({}, {}, {}), errors)
        self.assertIn("closure: historical exclusion mismatch", errors)

    def test_check_closure_item_metadata_tamper(self) -> None:
        records, _ = closure.load_records(REPOSITORY_ROOT)
        tampered = copy.deepcopy(records)
        tampered["closure"]["items"][0]["closure_phase"] = "V0110-E"
        errors: list[str] = []
        totals = closure.check_closure(REPOSITORY_ROOT, tampered, ({}, {}, {}), errors)
        self.assertIn("closure: invalid frozen metadata or disposition evidence", errors)
        self.assertGreater(totals["invalid_rows"], 0)

    def test_check_closure_unknown_and_missing_identities(self) -> None:
        records, _ = closure.load_records(REPOSITORY_ROOT)
        m = closure.check_maintenance(REPOSITORY_ROOT, records, [])
        comp = closure.check_compatibility(REPOSITORY_ROOT, records, [])
        mat = closure.check_maturity(REPOSITORY_ROOT, records, m, [])

        # Missing identity
        tampered = copy.deepcopy(records)
        tampered["closure"]["items"].pop()
        errors: list[str] = []
        totals = closure.check_closure(REPOSITORY_ROOT, tampered, (m, comp, mat), errors)
        self.assertIn("closure: frozen inherited identity mismatch", errors)
        self.assertEqual(totals["missing_rows"], 1)

        # Trigger ref not in linked[0]
        tampered2 = copy.deepcopy(records)
        tampered2["closure"]["items"][0]["trigger_ref"] = "UNKNOWN-TRIGGER"
        errors = []
        totals = closure.check_closure(REPOSITORY_ROOT, tampered2, (m, comp, mat), errors)
        self.assertIn("closure: invalid frozen metadata or disposition evidence", errors)
        self.assertGreater(totals["invalid_rows"], 0)


class TestCheckRoadmapClosureApiAndCli(unittest.TestCase):
    """Test top-level API check_roadmap_closure and main CLI."""

    def test_check_roadmap_closure_missing_foundation_files(self) -> None:
        orig_pref = closure.public_ref
        with mock.patch("apg_roadmap_closure.public_ref") as mock_pref:
            def fake_pref(root: Path, ref: str) -> bool:
                if ref in contract.FOUNDATION_FILES:
                    return False
                return orig_pref(root, ref)
            mock_pref.side_effect = fake_pref
            res = closure.check_roadmap_closure(REPOSITORY_ROOT)
            self.assertFalse(res["valid"])
            self.assertIn("foundation: missing or nonpublic required authority", res["diagnostics"])

    def test_check_roadmap_closure_exception_handling(self) -> None:
        with mock.patch("apg_roadmap_closure.check_maintenance", side_effect=KeyError("unexpected key")):
            res = closure.check_roadmap_closure(REPOSITORY_ROOT)
            self.assertFalse(res["valid"])
            self.assertIn("source: unavailable or malformed governance authority", res["diagnostics"])

    def test_check_roadmap_closure_api(self) -> None:
        # Both modes pass on the current terminal ledger
        res = closure.check_roadmap_closure(REPOSITORY_ROOT, require_zero=False)
        self.assertTrue(res["valid"])
        self.assertTrue(res["passed"])
        self.assertEqual(res["open_rows"], 0)
        self.assertEqual(res["inherited_roadmap_open_items"], 0)
        self.assertEqual(res["zero_backlog_qualified"], res["open_rows"] == 0)
        self.assertEqual(res["diagnostics"], [])

        # Explicit zero mode qualifies the current accounting
        res_zero = closure.check_roadmap_closure(REPOSITORY_ROOT, require_zero=True)
        self.assertTrue(res_zero["valid"])
        self.assertEqual(res_zero["passed"], res_zero["open_rows"] == 0)
        self.assertEqual(res_zero["open_rows"], 0)
        self.assertEqual(res_zero["zero_backlog_qualified"], res_zero["open_rows"] == 0)

    def test_check_roadmap_closure_error_accumulation(self) -> None:
        with tempfile.TemporaryDirectory() as empty_dir:
            res = closure.check_roadmap_closure(Path(empty_dir))
            self.assertFalse(res["valid"])
            self.assertFalse(res["passed"])
            self.assertIsNone(res["inherited_roadmap_open_items"])
            self.assertFalse(res["zero_backlog_qualified"])
            self.assertTrue(len(res["diagnostics"]) > 0)

    def test_terminal_receipt_requires_item_bound_outcome_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "evidence.md").write_text("Fixture evidence only.")
            receipt_path = root / "decision.json"
            row = {"item_id": "APGR-CXT2B", "status": "REJECTED",
                   "closure_phase": "V0110-D", "disposition": {"decision_ref": "decision.json"}}
            receipt = {"schema_version": "apg.roadmap-decision/v1", "item_id": row["item_id"],
                       "outcome": "REJECTED", "closure_phase": "V0110-D", "author": "author",
                       "reviewer": "reviewer", "evidence": {
                           "evaluation": ["evidence.md"], "rejection_rationale": ["evidence.md"]}}
            receipt_path.write_text(json.dumps(receipt))
            self.assertTrue(closure.receipt_valid(root, row))
            for field, value in (("item_id", "unrelated"), ("outcome", "DELIVERED"),
                                 ("closure_phase", "V0110-C"), ("reviewer", " AUTHOR "),
                                 ("evidence", {"evaluation": [], "rejection_rationale": ["evidence.md"]}),
                                 ("evidence", {"evaluation": ["missing.md"], "rejection_rationale": ["evidence.md"]})):
                with self.subTest(field=field, value=value):
                    damaged = copy.deepcopy(receipt)
                    damaged[field] = value
                    receipt_path.write_text(json.dumps(damaged))
                    self.assertFalse(closure.receipt_valid(root, row))
            receipt_path.write_text("Ordinary prose is not a typed decision receipt.")
            self.assertFalse(closure.receipt_valid(root, row))

    def test_main_cli_execution_matrix(self) -> None:
        # Success with default arguments
        self.assertEqual(closure.main(["--root", str(REPOSITORY_ROOT)]), 0)

        # --json flag prints json
        with mock.patch("builtins.print") as mock_print:
            code = closure.main(["--root", str(REPOSITORY_ROOT), "--json"])
            self.assertEqual(code, 0)
            mock_print.assert_called_once()
            output = mock_print.call_args[0][0]
            parsed = json.loads(output)
            self.assertTrue(parsed["passed"])

        # --require-zero exits 1 if open_rows > 0, else 0
        records, _ = closure.load_records(REPOSITORY_ROOT)
        open_items = [r for r in records["closure"]["items"] if r["status"] == "OPEN"]
        code_zero = closure.main(["--root", str(REPOSITORY_ROOT), "--require-zero"])
        self.assertEqual(code_zero, 0 if not open_items else 1)

    def test_maintenance_trigger_receipt_validation_positive_and_refusals(self) -> None:
        """Exercise positive FALSE and refused TRUE/UNKNOWN/mismatched maintenance trigger receipts."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            obs_file = root / "obs.md"
            obs_file.write_text("Trigger state observation evidence.")
            proc_file = root / "proc.md"
            proc_file.write_text("Refresh procedure documentation.")
            rev_file = root / "review.md"
            rev_file.write_text("Independent review.")
            receipt_path = root / "decision.json"

            item_id = "APGR-CXT-BUDGET-COMPRESSION"
            trig_id = "APGR-CXT-BUDGET-COMPRESSION"
            trigger = {
                "trigger_id": trig_id,
                "current_state": "FALSE",
                "state_evidence": ["obs.md"],
                "owner": "APGR",
                "refresh_condition": "cond",
                "repair_condition": "repair",
                "affected_behavior": "beh",
                "affected_skills": [],
                "blocks_stable": False,
                "evidence_required": ["obs.md"],
                "refresh_procedure": "proc",
                "source_authority": ["obs.md"],
            }
            linked = ({trig_id: trigger}, {}, {})

            row = {
                "item_id": item_id,
                "status": "MAINTENANCE_TRIGGER",
                "closure_phase": "V0110-E",
                "trigger_ref": trig_id,
                "allowed_outcomes": ["DELIVERED", "MAINTENANCE_TRIGGER"],
                "inherited_class": "CONDITION_TRIGGERED",
                "disposition": {
                    "decision_ref": "decision.json",
                    "review_ref": "review.md",
                    "maintenance_ref": trig_id,
                    "qualification_refs": ["obs.md", "proc.md"],
                    "rationale": "Valid maintenance trigger disposition",
                    "compatibility_ref": None,
                    "maturity_ref": None,
                },
            }

            receipt = {
                "schema_version": "apg.roadmap-decision/v1",
                "item_id": item_id,
                "outcome": "MAINTENANCE_TRIGGER",
                "closure_phase": "V0110-E",
                "author": "author",
                "reviewer": "reviewer",
                "evidence": {
                    "trigger_observation": ["obs.md"],
                    "refresh_procedure": ["proc.md"],
                    "independent_review": ["review.md"],
                },
            }
            receipt_path.write_text(json.dumps(receipt))

            # Positive validation with FALSE state
            self.assertTrue(closure.receipt_valid(root, row, linked[2], linked[0]))
            self.assertTrue(closure.disposition_valid(root, row, linked))

            # An accepted observation survives later evidence and ordering changes.
            later = root / "later.md"
            later.write_text("Later independent maintenance observation.")
            trigger["state_evidence"] = ["later.md", "obs.md"]
            self.assertTrue(closure.receipt_valid(root, row, linked[2], linked[0]))
            trigger["state_evidence"].reverse()
            self.assertTrue(closure.receipt_valid(root, row, linked[2], linked[0]))
            trigger["state_evidence"] = ["later.md"]
            self.assertFalse(closure.receipt_valid(root, row, linked[2], linked[0]))
            trigger["state_evidence"] = ["obs.md"]

            # Refusal when trigger state is TRUE or UNKNOWN
            for bad_state in ("TRUE", "UNKNOWN"):
                trigger["current_state"] = bad_state
                self.assertFalse(closure.receipt_valid(root, row, linked[2], linked[0]))
                self.assertFalse(closure.disposition_valid(root, row, linked))
            trigger["current_state"] = "FALSE"

            # Refusal on mismatched trigger_observation (e.g. borrowed from elsewhere)
            bad_receipt = copy.deepcopy(receipt)
            bad_receipt["evidence"]["trigger_observation"] = ["proc.md"]
            receipt_path.write_text(json.dumps(bad_receipt))
            self.assertFalse(closure.receipt_valid(root, row, linked[2], linked[0]))
            receipt_path.write_text(json.dumps(receipt))

            # Refusal on mismatched independent_review
            bad_receipt = copy.deepcopy(receipt)
            bad_receipt["evidence"]["independent_review"] = ["proc.md"]
            receipt_path.write_text(json.dumps(bad_receipt))
            self.assertFalse(closure.receipt_valid(root, row, linked[2], linked[0]))
            receipt_path.write_text(json.dumps(receipt))

            # Refusal when qualification_refs does not include observation or refresh procedure
            bad_row = copy.deepcopy(row)
            bad_row["disposition"]["qualification_refs"] = ["proc.md"]
            self.assertFalse(closure.receipt_valid(root, bad_row, linked[2], linked[0]))
            bad_row["disposition"]["qualification_refs"] = ["obs.md"]
            self.assertFalse(closure.receipt_valid(root, bad_row, linked[2], linked[0]))

            # Refusal on mismatched / borrowed maintenance_ref in disposition
            bad_row = copy.deepcopy(row)
            bad_row["disposition"]["maintenance_ref"] = "CSS-QD-001"
            self.assertFalse(closure.receipt_valid(root, bad_row, linked[2], linked[0]))
            self.assertFalse(closure.disposition_valid(root, bad_row, linked))

            # Refusal on missing trigger in maintenance
            empty_linked = ({}, {}, {})
            self.assertFalse(closure.receipt_valid(root, row, empty_linked[2], empty_linked[0]))
            self.assertFalse(closure.disposition_valid(root, row, empty_linked))

            # Refusal when author == reviewer
            bad_receipt = copy.deepcopy(receipt)
            bad_receipt["reviewer"] = " AUTHOR "
            receipt_path.write_text(json.dumps(bad_receipt))
            self.assertFalse(closure.receipt_valid(root, row, linked[2], linked[0]))
            receipt_path.write_text(json.dumps(receipt))

    def test_eight_exact_maintenance_trigger_id_mappings(self) -> None:
        """Verify the eight exact ID mappings between closure ledger items and maintenance triggers."""
        records, _ = closure.load_records(REPOSITORY_ROOT)
        v0110_e_items = {r["item_id"]: r for r in records["closure"]["items"] if r["closure_phase"] == "V0110-E"}
        expected_mappings = {
            "APGR-CXT-BUDGET-COMPRESSION": "APGR-CXT-BUDGET-COMPRESSION",
            "APGR-DEBT-CSS-QD-001": "CSS-QD-001",
            "APGR-DEBT-CSS-QD-002": "CSS-QD-002",
            "APGR-DEBT-CSS-QD-003": "CSS-QD-003",
            "APGR-DEBT-CSS-QD-004": "CSS-QD-004",
            "APGR-DEBT-CSS-QD-005": "CSS-QD-005",
            "APGR-DEBT-JS-QD-005": "JS-QD-005",
            "APGR-REPORT-PUREGO-GIT": "APGR-REPORT-PUREGO-GIT",
        }
        self.assertEqual(set(v0110_e_items.keys()), set(expected_mappings.keys()))
        self.assertEqual(len(v0110_e_items), 8)

        m = closure.check_maintenance(REPOSITORY_ROOT, records, [])
        for item_id, trig_id in expected_mappings.items():
            item = v0110_e_items[item_id]
            self.assertEqual(item["trigger_ref"], trig_id)
            self.assertIn("MAINTENANCE_TRIGGER", item["allowed_outcomes"])
            self.assertEqual(item["closure_phase"], "V0110-E")
            self.assertEqual(item["inherited_class"], "CONDITION_TRIGGERED")
            self.assertIn(trig_id, m)

    def test_inherited_population_and_consequence_integrity(self) -> None:
        """Verify 55 inherited items and failure on deleted row or modified consequence."""
        records, _ = closure.load_records(REPOSITORY_ROOT)
        m = closure.check_maintenance(REPOSITORY_ROOT, records, [])
        comp = closure.check_compatibility(REPOSITORY_ROOT, records, [])
        mat = closure.check_maturity(REPOSITORY_ROOT, records, m, [])
        linked = (m, comp, mat)

        items = records["closure"]["items"]
        self.assertEqual(len(items), 55)

        # Deleting any inherited item produces frozen identity mismatch
        for idx in (0, 10, 25, 40, 54):
            tampered = copy.deepcopy(records)
            tampered["closure"]["items"].pop(idx)
            errors: list[str] = []
            totals = closure.check_closure(REPOSITORY_ROOT, tampered, linked, errors)
            self.assertIn("closure: frozen inherited identity mismatch", errors)
            self.assertEqual(totals["missing_rows"], 1)

        # Tampering with consequence invalidates item metadata fingerprint
        for target_id in ("APGR-CXT-BUDGET-COMPRESSION", "APGR-DEBT-CSS-QD-001", "APGR-DEBT-JS-QD-005"):
            tampered = copy.deepcopy(records)
            target_row = next(r for r in tampered["closure"]["items"] if r["item_id"] == target_id)
            target_row["consequence"] = "Tampered consequence description"
            errors = []
            totals = closure.check_closure(REPOSITORY_ROOT, tampered, linked, errors)
            self.assertIn("closure: invalid frozen metadata or disposition evidence", errors)
            self.assertGreater(totals["invalid_rows"], 0)


if __name__ == "__main__":
    unittest.main()
