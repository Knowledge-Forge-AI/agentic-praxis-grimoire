#!/usr/bin/env python3
"""Integration tests for libexec/apg_roadmap_contract.py against repository governance files."""

from __future__ import annotations

import copy
import json
import sys
import unittest

from src.test.apg_test_support import repository_root

REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import apg_roadmap_closure as closure  # noqa: E402
import apg_roadmap_contract as contract  # noqa: E402


class APGRoadmapContractIntegrationTests(unittest.TestCase):
    """Exercise contract definitions against actual files on disk."""

    def test_disk_schemas_match_contract_definitions(self) -> None:
        governance = REPOSITORY_ROOT / "docs" / "governance"
        schemas_dir = governance / "schemas"
        self.assertTrue(schemas_dir.is_dir())

        for kind, (filename, _, _) in contract.FILES.items():
            schema_path = schemas_dir / f"{filename}.schema.json"
            self.assertTrue(schema_path.is_file(), f"Missing schema file: {schema_path}")
            on_disk = json.loads(schema_path.read_text(encoding="utf-8"))
            expected = contract.schema(kind)
            self.assertEqual(
                on_disk,
                expected,
                f"Schema for {kind} on disk differs from contract.schema({kind})",
            )

    def test_adverse_schema_tampering_detected(self) -> None:
        for kind in contract.FILES:
            expected = contract.schema(kind)
            # Tamper release
            tampered = copy.deepcopy(expected)
            tampered["properties"]["release"]["const"] = "v0.12"
            self.assertNotEqual(tampered, expected)

            # Tamper schema_version
            tampered = copy.deepcopy(expected)
            tampered["properties"]["schema_version"]["const"] = "apg.wrong/v1"
            self.assertNotEqual(tampered, expected)

            # Tamper additionalProperties
            tampered = copy.deepcopy(expected)
            tampered["additionalProperties"] = True
            self.assertNotEqual(tampered, expected)

    def test_closure_ledger_historical_exclusions_match_contract(self) -> None:
        closure_path = REPOSITORY_ROOT / "docs/governance/v0-11-closure-ledger.json"
        data = json.loads(closure_path.read_text(encoding="utf-8"))
        self.assertIn("historical_exclusions", data)
        self.assertEqual(data["historical_exclusions"], list(contract.HISTORICAL_EXCLUSIONS))

        # Adverse check: modifying an exclusion causes mismatch
        tampered_exclusions = list(contract.HISTORICAL_EXCLUSIONS) + ["EXTRA-EXCLUSION"]
        self.assertNotEqual(tampered_exclusions, list(contract.HISTORICAL_EXCLUSIONS))

    def test_closure_ledger_item_bindings_match_contract(self) -> None:
        closure_path = REPOSITORY_ROOT / "docs/governance/v0-11-closure-ledger.json"
        data = json.loads(closure_path.read_text(encoding="utf-8"))
        items = data["items"]
        self.assertEqual(len(items), 55)

        item_ids = {item["item_id"] for item in items}
        self.assertEqual(item_ids, set(contract.ITEM_BINDINGS))

        for item in items:
            item_id = item["item_id"]
            metadata = {k: v for k, v in item.items() if k not in ("status", "disposition")}
            computed_fp = contract.fingerprint(metadata)
            expected_fp = contract.ITEM_BINDINGS[item_id]
            self.assertEqual(
                computed_fp,
                expected_fp,
                f"Item binding mismatch for {item_id}: computed {computed_fp} != expected {expected_fp}",
            )

            # Adverse test: tampering metadata changes fingerprint
            tampered_meta = copy.deepcopy(metadata)
            tampered_meta["closure_phase"] = "V0110-E" if tampered_meta.get("closure_phase") != "V0110-E" else "V0110-B"
            self.assertNotEqual(contract.fingerprint(tampered_meta), expected_fp)

    def test_maintenance_triggers_bindings_match_contract(self) -> None:
        maint_path = REPOSITORY_ROOT / "docs/governance/maintenance-triggers.json"
        data = json.loads(maint_path.read_text(encoding="utf-8"))
        triggers = data["triggers"]
        self.assertEqual(len(triggers), 9 + len(contract.MATURITY_TRIGGER_BINDINGS))

        trigger_ids = {t["trigger_id"] for t in triggers}
        self.assertEqual(trigger_ids, set(contract.TRIGGER_BINDINGS) | set(contract.MATURITY_TRIGGER_BINDINGS))

        fields = (
            "owner",
            "source_authority",
            "refresh_condition",
            "repair_condition",
            "affected_behavior",
            "blocks_stable",
            "evidence_required",
            "refresh_procedure",
        )
        for trigger in triggers:
            trigger_id = trigger["trigger_id"]
            if trigger_id in contract.MATURITY_TRIGGER_BINDINGS:
                self.assertEqual(contract.fingerprint(trigger), contract.MATURITY_TRIGGER_BINDINGS[trigger_id])
                continue
            bound_data = {field: trigger[field] for field in fields}
            computed_fp = contract.fingerprint(bound_data)
            expected_fp = contract.TRIGGER_BINDINGS[trigger_id]
            self.assertEqual(
                computed_fp,
                expected_fp,
                f"Trigger binding mismatch for {trigger_id}: computed {computed_fp} != expected {expected_fp}",
            )

            # Adverse check: tampering refresh_condition changes fingerprint
            tampered = copy.deepcopy(bound_data)
            tampered["refresh_condition"] = "tampered refresh condition"
            self.assertNotEqual(contract.fingerprint(tampered), expected_fp)

    def test_skill_maturity_ledger_inventory_and_provisional_bindings(self) -> None:
        maturity_path = REPOSITORY_ROOT / "docs/governance/skill-maturity-ledger.json"
        data = json.loads(maturity_path.read_text(encoding="utf-8"))
        skills = data["skills"]
        self.assertEqual(len(skills), 45)

        provisional_in_ledger = {s["skill_id"] for s in skills if s["current_maturity"] == "provisional"}
        self.assertEqual(provisional_in_ledger, set(contract.PROVISIONAL))

        # Check required evidence categories on all skills
        for skill in skills:
            self.assertEqual(skill["required_evidence_categories"], list(contract.EVIDENCE_CATEGORIES))
            self.assertEqual(set(skill["evidence"].keys()), set(contract.EVIDENCE_CATEGORIES))

    def test_known_debt_consistency_with_maintenance_triggers(self) -> None:
        debt_path = REPOSITORY_ROOT / "docs/governance/language-profile-known-debt.json"
        maint_path = REPOSITORY_ROOT / "docs/governance/maintenance-triggers.json"
        debts = {d["debt_id"]: d for d in json.loads(debt_path.read_text(encoding="utf-8"))["debts"]}
        triggers = {t["trigger_id"]: t for t in json.loads(maint_path.read_text(encoding="utf-8"))["triggers"]}

        debt_fields = ("owner", "refresh_condition", "repair_condition", "blocks_stable")
        for debt_id, debt_row in debts.items():
            if debt_id in triggers:
                trig_row = triggers[debt_id]
                for field in debt_fields:
                    self.assertEqual(
                        trig_row[field],
                        debt_row[field],
                        f"Field {field} mismatch between trigger and known debt for {debt_id}",
                    )

        # Confirm specific debt invariants
        self.assertTrue(debts["CSS-QD-001"]["blocks_stable"])
        self.assertTrue(debts["CSS-QD-002"]["blocks_stable"])
        self.assertTrue(debts["CSS-QD-003"]["blocks_stable"])
        self.assertTrue(debts["CSS-QD-004"]["blocks_stable"])
        self.assertFalse(debts["CSS-QD-005"]["blocks_stable"])
        self.assertTrue(debts["JS-QD-005"]["blocks_stable"])

    def test_all_actual_governance_ledgers_conform_to_contract_schemas(self) -> None:
        governance = REPOSITORY_ROOT / "docs/governance"
        for kind, (filename, _, _) in contract.FILES.items():
            ledger_path = governance / f"{filename}.json"
            data = json.loads(ledger_path.read_text(encoding="utf-8"))
            expected_schema = contract.schema(kind)
            self.assertTrue(
                closure.matches(data, expected_schema),
                f"Ledger {filename}.json does not conform to contract schema for {kind}",
            )


    def test_foundation_files_exist_and_public(self) -> None:
        self.assertEqual(len(contract.FOUNDATION_FILES), 5)
        for rel_path in contract.FOUNDATION_FILES:
            full_path = REPOSITORY_ROOT / rel_path
            self.assertTrue(full_path.is_file(), f"Missing required foundation file: {rel_path}")
            self.assertGreater(full_path.stat().st_size, 0, f"Empty foundation file: {rel_path}")
            self.assertTrue(closure.public_ref(REPOSITORY_ROOT, rel_path))

    def test_roadmap_decision_disk_schema_matches_contract(self) -> None:
        schema_path = REPOSITORY_ROOT / "docs/governance/schemas/roadmap-decision.schema.json"
        self.assertTrue(schema_path.is_file())
        on_disk = json.loads(schema_path.read_text(encoding="utf-8"))
        expected = contract.decision_schema()
        self.assertEqual(on_disk, expected)

    def test_v0110_e_exact_eight_trigger_mappings(self) -> None:
        closure_path = REPOSITORY_ROOT / "docs/governance/v0-11-closure-ledger.json"
        data = json.loads(closure_path.read_text(encoding="utf-8"))
        items = {item["item_id"]: item for item in data["items"] if item["closure_phase"] == "V0110-E"}
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
        self.assertEqual(set(items.keys()), set(expected_mappings.keys()))
        self.assertEqual(len(items), 8)
        for item_id, expected_trigger in expected_mappings.items():
            self.assertEqual(items[item_id]["trigger_ref"], expected_trigger)
            self.assertIn("MAINTENANCE_TRIGGER", items[item_id]["allowed_outcomes"])


if __name__ == "__main__":
    unittest.main()
