#!/usr/bin/env python3
"""Unit tests for libexec/apg_roadmap_contract.py."""

from __future__ import annotations

import re
import sys
import unittest

from src.test.apg_test_support import repository_root

REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import apg_roadmap_contract as contract  # noqa: E402


class APGRoadmapContractUnitTests(unittest.TestCase):
    """Exercise frozen contract definitions, schema vocabularies, and hashing."""

    def test_frozen_provisional_skills_inventory(self) -> None:
        self.assertEqual(len(contract.PROVISIONAL), 31)
        self.assertEqual(len(set(contract.PROVISIONAL)), 31)
        self.assertEqual(contract.PROVISIONAL, tuple(sorted(contract.PROVISIONAL)))
        for skill in contract.PROVISIONAL:
            self.assertIsInstance(skill, str)
            self.assertTrue(len(skill) > 0)
        self.assertIn("css-language-profile", contract.PROVISIONAL)
        self.assertIn("javascript-language-profile", contract.PROVISIONAL)
        self.assertIn("typescript-language-profile", contract.PROVISIONAL)
        self.assertIn("browser-runtime-profile", contract.PROVISIONAL)

    def test_frozen_historical_exclusions_inventory(self) -> None:
        self.assertEqual(len(contract.HISTORICAL_EXCLUSIONS), 18)
        self.assertEqual(len(set(contract.HISTORICAL_EXCLUSIONS)), 18)
        self.assertEqual(contract.HISTORICAL_EXCLUSIONS, tuple(sorted(contract.HISTORICAL_EXCLUSIONS)))
        for item in contract.HISTORICAL_EXCLUSIONS:
            self.assertIsInstance(item, str)
            self.assertTrue(len(item) > 0)
        self.assertIn("APGR-CAP1", contract.HISTORICAL_EXCLUSIONS)
        self.assertIn("APGR-DEBT-JS-QD-001", contract.HISTORICAL_EXCLUSIONS)
        self.assertIn("SKILL-A11Y", contract.HISTORICAL_EXCLUSIONS)

    def test_frozen_evidence_categories_inventory(self) -> None:
        expected = (
            "repeated_positive_use",
            "representative_non_triggers",
            "defect_debt_disposition",
            "rollback",
            "provenance",
            "independent_review",
            "current_validation",
        )
        self.assertEqual(contract.EVIDENCE_CATEGORIES, expected)
        self.assertEqual(len(contract.EVIDENCE_CATEGORIES), 7)

    def test_frozen_foundation_files_inventory(self) -> None:
        self.assertEqual(len(contract.FOUNDATION_FILES), 5)
        for path in contract.FOUNDATION_FILES:
            self.assertIsInstance(path, str)
            self.assertTrue(path.startswith("docs/"))

    def test_frozen_item_bindings_inventory_and_hash_format(self) -> None:
        self.assertEqual(len(contract.ITEM_BINDINGS), 55)
        sha256_pattern = re.compile(r"^[0-9a-f]{64}$")
        for item_id, digest in contract.ITEM_BINDINGS.items():
            self.assertIsInstance(item_id, str)
            self.assertTrue(sha256_pattern.match(digest), f"Invalid digest format for {item_id}: {digest}")

        # Verify maturity items exactly map to the 31 provisional skills
        maturity_items = {k for k in contract.ITEM_BINDINGS if k.startswith("MATURITY:")}
        self.assertEqual(len(maturity_items), 31)
        expected_maturity = {f"MATURITY:{skill}" for skill in contract.PROVISIONAL}
        self.assertEqual(maturity_items, expected_maturity)

        # Verify roadmap item groupings
        rm_items = {k for k in contract.ITEM_BINDINGS if k.startswith("RM-S")}
        self.assertEqual(rm_items, {"RM-S0", "RM-S1", "RM-S2", "RM-S3", "RM-S4", "RM-S5"})

        apgr_items = {k for k in contract.ITEM_BINDINGS if k.startswith("APGR-")}
        self.assertEqual(len(apgr_items), 15)

        skill_items = {k for k in contract.ITEM_BINDINGS if k.startswith("SKILL-")}
        self.assertEqual(len(skill_items), 3)

    def test_frozen_trigger_bindings_inventory_and_hash_format(self) -> None:
        self.assertEqual(len(contract.TRIGGER_BINDINGS), 9)
        sha256_pattern = re.compile(r"^[0-9a-f]{64}$")
        for trigger_id, digest in contract.TRIGGER_BINDINGS.items():
            self.assertIsInstance(trigger_id, str)
            self.assertTrue(sha256_pattern.match(digest), f"Invalid digest format for {trigger_id}: {digest}")

        expected_triggers = {
            "CSS-QD-001",
            "CSS-QD-002",
            "CSS-QD-003",
            "CSS-QD-004",
            "CSS-QD-005",
            "JS-QD-005",
            "APGR-REPORT-PUREGO-GIT",
            "SKILL-MIGRATION",
            "APGR-CXT-BUDGET-COMPRESSION",
        }
        self.assertEqual(set(contract.TRIGGER_BINDINGS), expected_triggers)

    def test_fingerprint_determinism_and_key_order_invariance(self) -> None:
        dict_a = {"b": 2, "a": 1, "nested": {"z": 10, "y": 20}}
        dict_b = {"nested": {"y": 20, "z": 10}, "a": 1, "b": 2}
        self.assertEqual(contract.fingerprint(dict_a), contract.fingerprint(dict_b))

        # Different values produce different digests
        dict_c = {"a": 1, "b": 3, "nested": {"y": 20, "z": 10}}
        self.assertNotEqual(contract.fingerprint(dict_a), contract.fingerprint(dict_c))

        # Unicode preservation (ensure_ascii=False)
        unicode_dict = {"msg": "grimoire \u2014 praxis \u2714"}
        fp1 = contract.fingerprint(unicode_dict)
        self.assertEqual(len(fp1), 64)

    def test_schema_vocabulary_helpers(self) -> None:
        # obj helper
        props = {"k1": {"type": "string"}, "k2": {"type": "number"}}
        o = contract.obj(props)
        self.assertEqual(o["type"], "object")
        self.assertEqual(o["properties"], props)
        self.assertEqual(o["required"], ["k1", "k2"])
        self.assertFalse(o["additionalProperties"])

        # array helper
        arr = contract.array({"type": "string"})
        self.assertEqual(arr["type"], "array")
        self.assertEqual(arr["items"], {"type": "string"})
        self.assertTrue(arr["uniqueItems"])

        # enum helper
        e = contract.enum("A", "B", "C")
        self.assertEqual(e["type"], "string")
        self.assertEqual(e["enum"], ["A", "B", "C"])

        # nullable helper
        n = contract.nullable({"type": "string"})
        self.assertIn("anyOf", n)
        self.assertEqual(n["anyOf"], [{"type": "string"}, {"type": "null"}])

    def test_files_mapping(self) -> None:
        self.assertEqual(
            contract.FILES,
            {
                "closure": ("v0-11-closure-ledger", "items", "item_id"),
                "maintenance": ("maintenance-triggers", "triggers", "trigger_id"),
                "compatibility": ("external-compatibility", "watches", "watch_id"),
                "maturity": ("skill-maturity-ledger", "skills", "skill_id"),
            },
        )

    def test_schema_generator_for_all_valid_kinds(self) -> None:
        for kind in ("closure", "maintenance", "compatibility", "maturity"):
            s = contract.schema(kind)
            self.assertEqual(s["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertEqual(s["title"], contract.FILES[kind][0])
            self.assertEqual(s["type"], "object")
            self.assertFalse(s["additionalProperties"])
            self.assertEqual(s["properties"]["release"], {"const": "v0.11", "type": "string"})
            self.assertEqual(s["properties"]["schema_version"], {"const": f"apg.{kind}-ledger/v1", "type": "string"})
            self.assertEqual(s["properties"]["owner_phase"], contract.TEXT)

            key = contract.FILES[kind][1]
            self.assertIn(key, s["properties"])
            self.assertEqual(s["properties"][key]["type"], "array")
            self.assertTrue(s["properties"][key]["uniqueItems"])

            if kind == "closure":
                self.assertIn("historical_exclusions", s["properties"])
                self.assertEqual(s["properties"]["historical_exclusions"], contract.TEXTS)
            else:
                self.assertNotIn("historical_exclusions", s["properties"])

    def test_schema_generator_unknown_kind_raises_key_error(self) -> None:
        with self.assertRaises(KeyError):
            contract.schema("unknown_kind")

    def test_row_schemas_integrity(self) -> None:
        for kind in ("closure", "maintenance", "compatibility", "maturity"):
            self.assertIn(kind, contract.ROW_SCHEMAS)
            row_schema = contract.ROW_SCHEMAS[kind]
            self.assertEqual(row_schema["type"], "object")
            self.assertFalse(row_schema["additionalProperties"])
            self.assertIsInstance(row_schema["properties"], dict)
            self.assertEqual(row_schema["required"], list(row_schema["properties"].keys()))

        # Verify specific fields in closure
        closure_props = contract.ROW_SCHEMAS["closure"]["properties"]
        self.assertEqual(
            closure_props["status"]["enum"],
            [
                "OPEN",
                "DELIVERED",
                "REJECTED",
                "CONSUMER_HANDOFF_CLOSED",
                "MAINTENANCE_TRIGGER",
                "STABLE",
                "PROVISIONAL_MAINTENANCE",
                "DEPRECATED_OR_SUPERSEDED",
            ],
        )

        # Verify specific fields in maintenance
        maint_props = contract.ROW_SCHEMAS["maintenance"]["properties"]
        self.assertEqual(maint_props["current_state"]["enum"], ["FALSE", "TRUE", "UNKNOWN"])
        self.assertEqual(maint_props["blocks_stable"], contract.BOOL)

        # Verify specific fields in compatibility
        compat_props = contract.ROW_SCHEMAS["compatibility"]["properties"]
        self.assertEqual(compat_props["status"]["enum"], ["WATCH", "QUALIFIED", "HANDOFF_CLOSED"])
        self.assertEqual(compat_props["adoption_claimed"], {"const": False, "type": "boolean"})

        # Verify specific fields in maturity
        maturity_props = contract.ROW_SCHEMAS["maturity"]["properties"]
        self.assertEqual(maturity_props["current_maturity"]["enum"], ["stable", "provisional", "deprecated"])
        self.assertEqual(
            maturity_props["disposition_status"]["enum"],
            [
                "EXISTING_STABLE",
                "PENDING_V0110_B",
                "STABLE",
                "PROVISIONAL_MAINTENANCE",
                "DEPRECATED_OR_SUPERSEDED",
            ],
        )

    def test_outcome_evidence_and_decision_schema_maintenance_trigger(self) -> None:
        expected = ("trigger_observation", "refresh_procedure", "independent_review")
        self.assertEqual(contract.OUTCOME_EVIDENCE["MAINTENANCE_TRIGGER"], expected)

        schema = contract.decision_schema()
        self.assertIn("anyOf", schema)
        maint_choice = next(
            (c for c in schema["anyOf"] if c["properties"]["outcome"].get("const") == "MAINTENANCE_TRIGGER"),
            None,
        )
        self.assertIsNotNone(maint_choice)
        evidence_props = maint_choice["properties"]["evidence"]["properties"]
        self.assertEqual(set(evidence_props.keys()), set(expected))
        self.assertEqual(maint_choice["properties"]["evidence"]["required"], list(expected))


if __name__ == "__main__":
    unittest.main()
