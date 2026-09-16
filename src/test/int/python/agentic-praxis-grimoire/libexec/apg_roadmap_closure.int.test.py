#!/usr/bin/env python3
"""Integration tests for bin/apg-check-roadmap-closure and libexec/apg_roadmap_closure.py."""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from src.test.apg_test_support import repository_root

REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import apg_roadmap_closure as closure  # noqa: E402
import apg_roadmap_contract as contract  # noqa: E402



def create_fixture_repository(target: Path) -> None:
    """Build a minimal valid repository fixture without cloning the giant repository."""
    shutil.copytree(REPOSITORY_ROOT / "docs", target / "docs")
    shutil.copytree(REPOSITORY_ROOT / "libexec", target / "libexec")
    shutil.copytree(REPOSITORY_ROOT / "bin", target / "bin")
    shutil.copytree(REPOSITORY_ROOT / ".agents", target / ".agents", symlinks=True)
    shutil.copytree(REPOSITORY_ROOT / "report", target / "report")

    # Copy catalog README and all 45 canonical SKILL.md files
    (target / "skills").mkdir(parents=True, exist_ok=True)
    shutil.copy(REPOSITORY_ROOT / "skills/README.md", target / "skills/README.md")
    for skill_path in (REPOSITORY_ROOT / "skills").rglob("SKILL.md"):
        rel_path = skill_path.relative_to(REPOSITORY_ROOT)
        dest_path = target / rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(skill_path, dest_path)

    # Evidence references are real source files, not executed fixture substitutes.
    def copy_public_ref(reference: str) -> None:
        path = Path(reference.split("#", 1)[0])
        if path.parts and path.parts[0] in ("src", "testing") and ".." not in path.parts:
            src = REPOSITORY_ROOT / path
            if src.is_file():
                destination = target / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(src, destination)

    def scan_refs(value: object) -> None:
        if isinstance(value, str):
            if value.startswith("src/") or value.startswith("testing/"):
                copy_public_ref(value)
        elif isinstance(value, list):
            for item in value:
                scan_refs(item)
        elif isinstance(value, dict):
            for item in value.values():
                scan_refs(item)

    for gov_file in (target / "docs/governance").rglob("*.json"):
        try:
            scan_refs(json.loads(gov_file.read_text(encoding="utf-8")))
        except (OSError, ValueError, UnicodeError):
            pass

    # Optional external compatibility fixtures for APG140
    compat_fixtures = REPOSITORY_ROOT / "testing/fixtures/external_compatibility/apg140"
    if compat_fixtures.exists():
        dest_compat = target / "testing/fixtures/external_compatibility/apg140"
        dest_compat.parent.mkdir(parents=True, exist_ok=True)
        if compat_fixtures.is_dir():
            shutil.copytree(compat_fixtures, dest_compat, dirs_exist_ok=True)
        else:
            shutil.copy(compat_fixtures, dest_compat)

    # Historical accounting/adverse cases start at the APG139 entry state.
    ledger_path = target / "docs/governance/v0-11-closure-ledger.json"
    ledger = json.loads(ledger_path.read_text())
    for row in ledger["items"]:
        if row["closure_phase"] in ("V0110-C", "V0110-D", "V0110-E"):
            row["status"] = "OPEN"
            row["disposition"] = None
    ledger_path.write_text(json.dumps(ledger))

    # Make bin executable
    cli_bin = target / "bin" / "apg-check-roadmap-closure"
    cli_bin.chmod(0o755)


def run_cli(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Execute the real bin/apg-check-roadmap-closure executable in a subprocess."""
    cli_bin = REPOSITORY_ROOT / "bin" / "apg-check-roadmap-closure"
    cmd = [str(cli_bin), "--root", str(root), *arguments]
    return subprocess.run(
        cmd,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=REPOSITORY_ROOT,
        env=os.environ.copy(),
    )


class APGRoadmapClosureIntegrationTests(unittest.TestCase):
    """Exercise real CLI subprocess and adverse filesystem permutations."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(prefix="apgr-governance-")
        self.fixture_root = Path(self.tmpdir.name).resolve() / "public-source"
        self.fixture_root.mkdir()
        create_fixture_repository(self.fixture_root)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_individual_maturity_closure_requires_actual_review_receipts(self):
        """Synthetic review fixture proves accounting; it does not review APG139."""
        root = self.fixture_root
        gov = root / "docs/governance"
        mat = json.loads((gov / "skill-maturity-ledger.json").read_text())
        ledger = json.loads((gov / "v0-11-closure-ledger.json").read_text())
        reviews = "docs/governance/synthetic-review.md"
        (root / reviews).write_text("Synthetic fixture review only; no real maturity acceptance.\n")
        receipts = gov / "fixture-decisions"
        receipts.mkdir()
        leaves = {r["skill_id"]: r for r in mat["skills"]}
        for item in ledger["items"]:
            if item["inherited_class"] != "PROVISIONAL_MATURITY":
                continue
            leaf = leaves[item["item_id"].removeprefix("MATURITY:")]
            leaf.update(disposition_status="PROVISIONAL_MAINTENANCE", independent_review=reviews)
            leaf["evidence"]["independent_review"] = [reviews]
            ref = f"docs/governance/fixture-decisions/{leaf['skill_id']}.json"
            receipt = dict(schema_version="apg.roadmap-decision/v1", item_id=item["item_id"],
                           outcome="PROVISIONAL_MAINTENANCE", closure_phase="V0110-B",
                           author="synthetic producer", reviewer="synthetic reviewer", evidence=leaf["evidence"])
            (root / ref).write_text(json.dumps(receipt))
            item.update(status="PROVISIONAL_MAINTENANCE", disposition=dict(
                decision_ref=ref, qualification_refs=[leaf["source_references"][-1]], review_ref=reviews,
                rationale="Synthetic individual maintenance fixture", maintenance_ref=leaf["maintenance_ref"],
                compatibility_ref=None, maturity_ref=leaf["skill_id"]))
        (gov / "skill-maturity-ledger.json").write_text(json.dumps(mat))
        (gov / "v0-11-closure-ledger.json").write_text(json.dumps(ledger))
        proc = run_cli(root, "--json")
        result = json.loads(proc.stdout)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertEqual((result["terminal_rows"], result["open_rows"], result["invalid_rows"]), (31, 24, 0))
        self.assertEqual(run_cli(root, "--json", "--require-zero").returncode, 1)
        item = next(r for r in ledger["items"] if r["inherited_class"] == "PROVISIONAL_MATURITY")
        original = item["disposition"]["review_ref"]
        item["disposition"]["review_ref"] = "skills/README.md"
        (gov / "v0-11-closure-ledger.json").write_text(json.dumps(ledger))
        self.assertEqual(run_cli(root, "--json").returncode, 1)
        item["disposition"]["review_ref"] = original
        (gov / "v0-11-closure-ledger.json").write_text(json.dumps(ledger))
        (root / reviews).unlink()
        self.assertEqual(run_cli(root, "--json").returncode, 1)

    def test_qualified_watch_requires_matching_fixture_and_valid_observation_date(self) -> None:
        path = self.fixture_root / "docs/governance/external-compatibility.json"
        data = json.loads(path.read_text())
        watch = data["watches"][0]
        fixture = "docs/governance/fixture-contract.txt"
        (self.fixture_root / fixture).write_text("Disposable consumer fixture, not adoption.\n")
        watch.update(status="QUALIFIED", observed_revision="fixture revision",
                     observed_contract="fixture contract", observation_date="2026-09-12",
                     fixture_identity={"path": fixture, "sha256": hashlib.sha256(
                         (self.fixture_root / fixture).read_bytes()).hexdigest()},
                     supported_cases=["fixture-only case"], qualification_evidence=[fixture])
        path.write_text(json.dumps(data))
        proc = run_cli(self.fixture_root, "--json")
        self.assertEqual(proc.returncode, 0, proc.stdout)
        for date_value, digest in (("2026-99-12", watch["fixture_identity"]["sha256"]),
                                   ("2026-09-12", "0" * 64)):
            watch["observation_date"] = date_value
            watch["fixture_identity"]["sha256"] = digest
            path.write_text(json.dumps(data))
            proc = run_cli(self.fixture_root, "--json")
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIsNone(json.loads(proc.stdout)["inherited_roadmap_open_items"])

    def test_decision_schema_drift_and_removal_invalidate_authority(self) -> None:
        path = self.fixture_root / "docs/governance/schemas/roadmap-decision.schema.json"
        path.write_text('{}')
        proc = run_cli(self.fixture_root, "--json")
        self.assertEqual(proc.returncode, 1)
        self.assertIsNone(json.loads(proc.stdout)["inherited_roadmap_open_items"])
        path.unlink()
        proc = run_cli(self.fixture_root, "--json")
        self.assertEqual(proc.returncode, 1)
        self.assertIsNone(json.loads(proc.stdout)["inherited_roadmap_open_items"])

    def test_cli_current_31_terminal_24_open_and_require_zero(self) -> None:
        # Default require_zero=False passes on 31 terminal and 24 OPEN
        proc_json = run_cli(self.fixture_root, "--json")
        self.assertEqual(proc_json.returncode, 0, proc_json.stderr)
        data = json.loads(proc_json.stdout)
        self.assertTrue(data["valid"])
        self.assertTrue(data["passed"])
        self.assertEqual(data["open_rows"], 24)
        self.assertEqual(data["terminal_rows"], 31)
        self.assertEqual(data["inherited_roadmap_open_items"], 24)
        self.assertFalse(data["zero_backlog_qualified"])
        self.assertEqual(data["diagnostics"], [])

        # Plain text output
        proc_text = run_cli(self.fixture_root)
        self.assertEqual(proc_text.returncode, 0)
        self.assertTrue(proc_text.stdout.startswith("PASS roadmap closure: "))

        # require_zero=True fails because backlog is 24
        proc_zero = run_cli(self.fixture_root, "--require-zero", "--json")
        self.assertEqual(proc_zero.returncode, 1)
        data_zero = json.loads(proc_zero.stdout)
        self.assertTrue(data_zero["valid"])
        self.assertFalse(data_zero["passed"])
        self.assertEqual(data_zero["open_rows"], 24)
        self.assertEqual(data_zero["inherited_roadmap_open_items"], 24)
        self.assertFalse(data_zero["zero_backlog_qualified"])

        # require_zero text output
        proc_zero_text = run_cli(self.fixture_root, "--require-zero")
        self.assertEqual(proc_zero_text.returncode, 1)
        self.assertTrue(proc_zero_text.stdout.startswith("FAIL roadmap closure: "))

    def test_cli_adverse_duplicate_json_keys(self) -> None:
        closure_path = self.fixture_root / "docs/governance/v0-11-closure-ledger.json"
        content = closure_path.read_text(encoding="utf-8")
        # Inject duplicate key
        corrupted = content.replace('"release": "v0.11",', '"release": "v0.11",\n  "release": "v0.11",')
        closure_path.write_text(corrupted, encoding="utf-8")

        proc = run_cli(self.fixture_root, "--json")
        self.assertEqual(proc.returncode, 1)
        data = json.loads(proc.stdout)
        self.assertFalse(data["valid"])
        self.assertFalse(data["passed"])
        self.assertIsNone(data["inherited_roadmap_open_items"])
        self.assertTrue(any("unreadable or malformed JSON" in d for d in data["diagnostics"]))

    def test_cli_adverse_malformed_json_and_symlinks(self) -> None:
        # Non-regular file (symlink)
        maint_path = self.fixture_root / "docs/governance/maintenance-triggers.json"
        real_maint = self.fixture_root / "docs/governance/maintenance-real.json"
        shutil.move(maint_path, real_maint)
        maint_path.symlink_to(real_maint)

        proc = run_cli(self.fixture_root, "--json")
        self.assertEqual(proc.returncode, 1)
        data = json.loads(proc.stdout)
        self.assertFalse(data["valid"])
        self.assertTrue(any("unreadable or malformed JSON" in d for d in data["diagnostics"]))

    def test_cli_adverse_schema_tampering(self) -> None:
        schemas_dir = self.fixture_root / "docs/governance/schemas"

        # Tamper closure schema
        closure_schema = schemas_dir / "v0-11-closure-ledger.schema.json"
        s_data = json.loads(closure_schema.read_text(encoding="utf-8"))
        s_data["properties"]["release"]["const"] = "v0.12"
        closure_schema.write_text(json.dumps(s_data), encoding="utf-8")

        proc = run_cli(self.fixture_root, "--json")
        self.assertEqual(proc.returncode, 1)
        data = json.loads(proc.stdout)
        self.assertFalse(data["valid"])
        self.assertTrue(any("closure: schema differs from maintained contract" in d for d in data["diagnostics"]))

    def test_cli_adverse_closure_ledger_missing_and_unknown_identities(self) -> None:
        closure_path = self.fixture_root / "docs/governance/v0-11-closure-ledger.json"
        data = json.loads(closure_path.read_text(encoding="utf-8"))

        # Remove an item -> missing_rows = 1
        data["items"].pop()
        closure_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        proc = run_cli(self.fixture_root, "--json")
        self.assertEqual(proc.returncode, 1)
        res = json.loads(proc.stdout)
        self.assertFalse(res["valid"])
        self.assertEqual(res["missing_rows"], 1)
        self.assertTrue(any("closure: frozen inherited identity mismatch" in d for d in res["diagnostics"]))

        # Add unknown item -> unknown_rows = 1
        data["items"].append(
            {
                "item_id": "APGR-INVENTED-ITEM",
                "sources": ["docs/README.md"],
                "inherited_class": "EXTERNAL_GATE",
                "closure_phase": "V0110-B",
                "allowed_outcomes": ["DELIVERED"],
                "prerequisites": [],
                "trigger_ref": None,
                "consequence": "Invented consequence",
                "status": "OPEN",
                "disposition": None,
            }
        )
        data["items"].sort(key=lambda x: x["item_id"])
        closure_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        proc_unknown = run_cli(self.fixture_root, "--json")
        self.assertEqual(proc_unknown.returncode, 1)
        res_unknown = json.loads(proc_unknown.stdout)
        self.assertFalse(res_unknown["valid"])
        self.assertEqual(res_unknown["unknown_rows"], 1)

    def test_cli_adverse_closure_ledger_duplicate_identity(self) -> None:
        closure_path = self.fixture_root / "docs/governance/v0-11-closure-ledger.json"
        data = json.loads(closure_path.read_text(encoding="utf-8"))
        data["items"][1]["item_id"] = data["items"][0]["item_id"]
        closure_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        proc = run_cli(self.fixture_root, "--json")
        self.assertEqual(proc.returncode, 1)
        res = json.loads(proc.stdout)
        self.assertFalse(res["valid"])
        self.assertTrue(any("duplicate or unordered identities" in d for d in res["diagnostics"]))

    def test_cli_adverse_historical_exclusions_mismatch(self) -> None:
        closure_path = self.fixture_root / "docs/governance/v0-11-closure-ledger.json"
        data = json.loads(closure_path.read_text(encoding="utf-8"))
        data["historical_exclusions"] = []
        closure_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        proc = run_cli(self.fixture_root, "--json")
        self.assertEqual(proc.returncode, 1)
        res = json.loads(proc.stdout)
        self.assertFalse(res["valid"])
        self.assertTrue(any("closure: historical exclusion mismatch" in d for d in res["diagnostics"]))

    def test_cli_adverse_closure_metadata_and_terminal_tampering(self) -> None:
        closure_path = self.fixture_root / "docs/governance/v0-11-closure-ledger.json"
        data = json.loads(closure_path.read_text(encoding="utf-8"))

        # Tamper closure_phase (items[0] is V0110-C, tamper to V0110-E)
        data["items"][0]["closure_phase"] = "V0110-E"
        closure_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        proc = run_cli(self.fixture_root, "--json")
        self.assertEqual(proc.returncode, 1)
        res = json.loads(proc.stdout)
        self.assertFalse(res["valid"])
        self.assertGreater(res["invalid_rows"], 0)
        self.assertTrue(any("closure: invalid frozen metadata or disposition evidence" in d for d in res["diagnostics"]))

        # Invent terminal state: status DELIVERED with decision None
        shutil.copy(REPOSITORY_ROOT / "docs/governance/v0-11-closure-ledger.json", closure_path)
        data = json.loads(closure_path.read_text(encoding="utf-8"))
        data["items"][0]["status"] = "DELIVERED"
        data["items"][0]["disposition"] = None
        closure_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        proc_term = run_cli(self.fixture_root, "--json")
        self.assertEqual(proc_term.returncode, 1)
        res_term = json.loads(proc_term.stdout)
        self.assertFalse(res_term["valid"])
        self.assertGreater(res_term["invalid_rows"], 0)

        # Status DELIVERED with non-existent evidence reference
        data["items"][0]["disposition"] = {
            "decision_ref": "docs/nonexistent.md",
            "review_ref": "docs/README.md",
            "qualification_refs": ["docs/README.md"],
            "rationale": "Delivered with missing evidence",
            "maintenance_ref": None,
            "compatibility_ref": None,
            "maturity_ref": None,
        }
        closure_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        proc_ev = run_cli(self.fixture_root, "--json")
        self.assertEqual(proc_ev.returncode, 1)
        res_ev = json.loads(proc_ev.stdout)
        self.assertFalse(res_ev["valid"])
        self.assertGreater(res_ev["invalid_rows"], 0)

    def test_cli_adverse_maintenance_triggers_mutations(self) -> None:
        maint_path = self.fixture_root / "docs/governance/maintenance-triggers.json"
        data = json.loads(maint_path.read_text(encoding="utf-8"))

        # Tamper refresh_condition vs repair_condition
        data["triggers"][0]["refresh_condition"] = "tampered condition"
        maint_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        proc = run_cli(self.fixture_root, "--json")
        self.assertEqual(proc.returncode, 1)
        res = json.loads(proc.stdout)
        self.assertFalse(res["valid"])
        self.assertTrue(any("maintenance: trigger/source/state binding mismatch" in d for d in res["diagnostics"]))

        # Restore clean file and tamper blocks_stable
        shutil.copy(REPOSITORY_ROOT / "docs/governance/maintenance-triggers.json", maint_path)
        data = json.loads(maint_path.read_text(encoding="utf-8"))
        data["triggers"][0]["blocks_stable"] = True
        maint_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        proc_debt = run_cli(self.fixture_root, "--json")
        self.assertEqual(proc_debt.returncode, 1)

        # Confirm clean baseline with UNKNOWN triggers passes (verifying UNKNOWN is not treated as false/failure)
        shutil.copy(REPOSITORY_ROOT / "docs/governance/maintenance-triggers.json", maint_path)
        proc_clean = run_cli(self.fixture_root, "--json")
        self.assertEqual(proc_clean.returncode, 0)
        res_clean = json.loads(proc_clean.stdout)
        self.assertTrue(res_clean["valid"])

    def test_cli_adverse_compatibility_overclaims(self) -> None:
        compat_path = self.fixture_root / "docs/governance/external-compatibility.json"
        data = json.loads(compat_path.read_text(encoding="utf-8"))

        # Status WATCH cannot claim supported_cases
        for w in data["watches"]:
            if w["status"] == "WATCH":
                w["supported_cases"] = ["overclaimed_case"]
                break
        compat_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        proc = run_cli(self.fixture_root, "--json")
        self.assertEqual(proc.returncode, 1)
        res = json.loads(proc.stdout)
        self.assertFalse(res["valid"])
        self.assertTrue(any("compatibility: unavailable evidence or unsupported qualification claim" in d for d in res["diagnostics"]))

    def test_cli_adverse_maturity_and_projections(self) -> None:
        # Break projection symlink
        proj_link = self.fixture_root / ".agents/skills/python-language-profile"
        proj_link.unlink()
        (self.fixture_root / ".agents/skills/python-language-profile").mkdir()

        proc = run_cli(self.fixture_root, "--json")
        self.assertEqual(proc.returncode, 1)
        res = json.loads(proc.stdout)
        self.assertFalse(res["valid"])
        self.assertTrue(any("maturity: path/projection/debt/evidence mismatch" in d for d in res["diagnostics"]))

        # Restore symlink
        (self.fixture_root / ".agents/skills/python-language-profile").rmdir()
        proj_link.symlink_to("../../skills/python-language-profile")

        # Provisional skill faking existing stable
        mat_path = self.fixture_root / "docs/governance/skill-maturity-ledger.json"
        m_data = json.loads(mat_path.read_text(encoding="utf-8"))
        for s in m_data["skills"]:
            if s["skill_id"] in contract.PROVISIONAL:
                s["disposition_status"] = "EXISTING_STABLE"
                s["current_maturity"] = "stable"
                break
        mat_path.write_text(json.dumps(m_data, indent=2), encoding="utf-8")

        proc_fake = run_cli(self.fixture_root, "--json")
        self.assertEqual(proc_fake.returncode, 1)
        res_fake = json.loads(proc_fake.stdout)
        self.assertFalse(res_fake["valid"])

    def test_cli_valid_zero_backlog_qualification_e2e(self) -> None:
        """Construct fully dispositioned valid terminal states and verify --require-zero passes."""
        ev_file = "docs/evaluations/apg138-v0-11-foundation-closure.md"

        # 1. Update maintenance triggers to FALSE with valid evidence
        maint_path = self.fixture_root / "docs/governance/maintenance-triggers.json"
        m_data = json.loads(maint_path.read_text(encoding="utf-8"))
        for t in m_data["triggers"]:
            if t["trigger_id"] in contract.MATURITY_TRIGGER_BINDINGS:
                continue
            t["current_state"] = "FALSE"
            t["state_evidence"] = [ev_file]
        maint_path.write_text(json.dumps(m_data, indent=2), encoding="utf-8")

        # 2. Update compatibility watches to HANDOFF_CLOSED with valid evidence
        compat_path = self.fixture_root / "docs/governance/external-compatibility.json"
        c_data = json.loads(compat_path.read_text(encoding="utf-8"))
        for w in c_data["watches"]:
            w["status"] = "HANDOFF_CLOSED"
            w["qualification_evidence"] = [ev_file]
        compat_path.write_text(json.dumps(c_data, indent=2), encoding="utf-8")

        # 3. Update skill maturity ledger for provisional skills to PROVISIONAL_MAINTENANCE
        mat_path = self.fixture_root / "docs/governance/skill-maturity-ledger.json"
        s_data = json.loads(mat_path.read_text(encoding="utf-8"))
        for s in s_data["skills"]:
            if s["current_maturity"] == "provisional":
                s["disposition_status"] = "PROVISIONAL_MAINTENANCE"
                s["maintenance_ref"] = "CSS-QD-001"
                s["independent_review"] = ev_file
                s["evidence"] = {k: [ev_file] for k in s["evidence"]}
        mat_path.write_text(json.dumps(s_data, indent=2), encoding="utf-8")

        # 4. Update closure ledger items to terminal status (DELIVERED, REJECTED, HANDOFF, MAINTENANCE, PROVISIONAL_MAINTENANCE)
        closure_path = self.fixture_root / "docs/governance/v0-11-closure-ledger.json"
        cl_data = json.loads(closure_path.read_text(encoding="utf-8"))
        for item in cl_data["items"]:
            item_id = item["item_id"]
            outcomes = item["allowed_outcomes"]
            if item["inherited_class"] == "PROVISIONAL_MATURITY":
                item["status"] = "PROVISIONAL_MAINTENANCE"
                item["disposition"] = {
                    "decision_ref": ev_file,
                    "review_ref": ev_file,
                    "qualification_refs": [ev_file],
                    "rationale": "Provisional maintenance qualified",
                    "maintenance_ref": None,
                    "compatibility_ref": None,
                    "maturity_ref": item_id.removeprefix("MATURITY:"),
                }
            elif item_id == "APGR-CI-QUAL":
                item["status"] = "CONSUMER_HANDOFF_CLOSED"
                item["disposition"] = {
                    "decision_ref": ev_file,
                    "review_ref": ev_file,
                    "qualification_refs": [ev_file],
                    "rationale": "Consumer handoff closed",
                    "maintenance_ref": None,
                    "compatibility_ref": "JACA-CI",
                    "maturity_ref": None,
                }
            elif item.get("trigger_ref") and "MAINTENANCE_TRIGGER" in outcomes:
                item["status"] = "MAINTENANCE_TRIGGER"
                item["disposition"] = {
                    "decision_ref": ev_file,
                    "review_ref": ev_file,
                    "qualification_refs": [ev_file],
                    "rationale": "Maintenance trigger dispositioned",
                    "maintenance_ref": item["trigger_ref"],
                    "compatibility_ref": None,
                    "maturity_ref": None,
                }
            elif "DELIVERED" in outcomes:
                item["status"] = "DELIVERED"
                item["disposition"] = {
                    "decision_ref": ev_file,
                    "review_ref": ev_file,
                    "qualification_refs": [ev_file],
                    "rationale": "Delivered successfully",
                    "maintenance_ref": None,
                    "compatibility_ref": None,
                    "maturity_ref": None,
                }
            else:
                item["status"] = "REJECTED"
                item["disposition"] = {
                    "decision_ref": ev_file,
                    "review_ref": ev_file,
                    "qualification_refs": [ev_file],
                    "rationale": "Rejected under governance",
                    "maintenance_ref": None,
                    "compatibility_ref": None,
                    "maturity_ref": None,
                }
        closure_path.write_text(json.dumps(cl_data, indent=2), encoding="utf-8")

        # Arbitrary existing prose and one unrelated trigger for all leaves cannot
        # manufacture terminal authority, even though all row labels are terminal.
        proc = run_cli(self.fixture_root, "--require-zero", "--json")
        self.assertEqual(proc.returncode, 1)
        self.assertIsNone(json.loads(proc.stdout)["inherited_roadmap_open_items"])

        # A synthetic complete decision fixture: retire each provisional leaf
        # individually, with explicit item-bound non-author receipts. This is
        # parser qualification, not a decision about the actual skill corpus.
        catalog_path = self.fixture_root / "skills/README.md"
        catalog_path.write_text(catalog_path.read_text().replace("| `provisional` |", "| `deprecated` |"))
        for leaf in s_data["skills"]:
            if leaf["skill_id"] in contract.PROVISIONAL:
                leaf["current_maturity"] = "deprecated"
                leaf["disposition_status"] = "DEPRECATED_OR_SUPERSEDED"
                leaf["maintenance_ref"] = None
        mat_path.write_text(json.dumps(s_data, indent=2))
        decision_dir = self.fixture_root / "docs/governance/decisions"
        decision_dir.mkdir()
        for number, item in enumerate(cl_data["items"]):
            if item["inherited_class"] == "PROVISIONAL_MATURITY":
                item["status"] = "DEPRECATED_OR_SUPERSEDED"
            relative = f"docs/governance/decisions/fixture-{number}.json"
            receipt = {
                "schema_version": "apg.roadmap-decision/v1",
                "item_id": item["item_id"], "outcome": item["status"],
                "closure_phase": item["closure_phase"],
                "author": "fixture author", "reviewer": "fixture independent reviewer",
                "evidence": {key: [ev_file] for key in contract.OUTCOME_EVIDENCE[item["status"]]},
            }
            (self.fixture_root / relative).write_text(json.dumps(receipt))
            item["disposition"]["decision_ref"] = relative
        closure_path.write_text(json.dumps(cl_data, indent=2))
        proc = run_cli(self.fixture_root, "--require-zero", "--json")
        self.assertEqual(proc.returncode, 0, proc.stdout)
        result = json.loads(proc.stdout)

        self.assertTrue(result["valid"])
        self.assertTrue(result["passed"])
        self.assertEqual(result["open_rows"], 0)
        self.assertEqual(result["terminal_rows"], 55)
        self.assertEqual(result["invalid_rows"], 0)
        self.assertEqual(result["inherited_roadmap_open_items"], 0)
        self.assertTrue(result["zero_backlog_qualified"])
        self.assertEqual(result["diagnostics"], [])

        # Also run text mode
        proc_text = run_cli(self.fixture_root, "--require-zero")
        self.assertEqual(proc_text.returncode, 0)
        self.assertTrue(proc_text.stdout.startswith("PASS roadmap closure: "))

    def test_v0110_c_terminalization_accounting_and_refusals(self) -> None:
        """Meaningful synthetic V0110-C terminalization test covering all 12 exact identities."""
        root = self.fixture_root
        gov = root / "docs/governance"
        ledger_path = gov / "v0-11-closure-ledger.json"
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        initial_items = copy.deepcopy(ledger["items"])

        # Setup synthetic review file
        reviews = "docs/governance/synthetic-v0110c-review.md"
        (root / reviews).write_text("Synthetic V0110-C review and evidence document.\n")

        # Setup fixture decision receipts directory
        receipts_dir = gov / "fixture-decisions-v0110c"
        receipts_dir.mkdir(parents=True, exist_ok=True)

        # 12 exact identities partitioned into:
        # - 3 JACA CONSUMER_HANDOFF_CLOSED
        # - RM-S0/S4/S5 DELIVERED
        # - RM-S1/S2/S3 and three SKILL rows REJECTED
        v0110_c_outcomes: dict[str, tuple[str, str | None]] = {
            "APGR-CI-QUAL": ("CONSUMER_HANDOFF_CLOSED", "JACA-CI"),
            "APGR-REPORT-OUTBOX": ("CONSUMER_HANDOFF_CLOSED", "JACA-OUTBOX"),
            "APGR-XO-COMPAT": ("CONSUMER_HANDOFF_CLOSED", "JACA-XO"),
            "RM-S0": ("DELIVERED", None),
            "RM-S4": ("DELIVERED", None),
            "RM-S5": ("DELIVERED", None),
            "RM-S1": ("REJECTED", None),
            "RM-S2": ("REJECTED", None),
            "RM-S3": ("REJECTED", None),
            "SKILL-KG-QUALITY": ("REJECTED", None),
            "SKILL-MIGRATION": ("REJECTED", None),
            "SKILL-VER-PROTO": ("REJECTED", None),
        }

        # Verify exact membership matches all V0110-C items in ledger
        c_items_in_ledger = {item["item_id"] for item in ledger["items"] if item["closure_phase"] == "V0110-C"}
        self.assertEqual(set(v0110_c_outcomes), c_items_in_ledger)
        self.assertEqual(len(v0110_c_outcomes), 12)

        # Update external compatibility matrix for HANDOFF_CLOSED JACA rows with explicit membership
        compat_path = gov / "external-compatibility.json"
        compat = json.loads(compat_path.read_text(encoding="utf-8"))
        jaca_membership = {
            "JACA-CI": ["APGR-CI-QUAL"],
            "JACA-OUTBOX": ["APGR-REPORT-OUTBOX"],
            "JACA-XO": ["APGR-XO-COMPAT"],
        }
        for watch in compat["watches"]:
            if watch["watch_id"] in jaca_membership:
                watch["status"] = "HANDOFF_CLOSED"
                watch["qualification_evidence"] = [reviews]
                watch["inherited_item_ids"] = jaca_membership[watch["watch_id"]]
        compat_path.write_text(json.dumps(compat, indent=2), encoding="utf-8")

        # Emit frozen outcome typed receipts with synthetic author/reviewer and update items
        for item in ledger["items"]:
            if item["closure_phase"] != "V0110-C":
                continue
            item_id = item["item_id"]
            status, compat_ref = v0110_c_outcomes[item_id]
            receipt_rel = f"docs/governance/fixture-decisions-v0110c/{item_id}.json"
            receipt = {
                "schema_version": "apg.roadmap-decision/v1",
                "item_id": item_id,
                "outcome": status,
                "closure_phase": "V0110-C",
                "author": "synthetic producer",
                "reviewer": "synthetic reviewer",
                "evidence": {category: [reviews] for category in contract.OUTCOME_EVIDENCE[status]},
            }
            (root / receipt_rel).write_text(json.dumps(receipt, indent=2), encoding="utf-8")
            item.update(
                status=status,
                disposition={
                    "decision_ref": receipt_rel,
                    "qualification_refs": [reviews],
                    "review_ref": reviews,
                    "rationale": f"Synthetic V0110-C terminalization receipt for {item_id}",
                    "maintenance_ref": None,
                    "compatibility_ref": compat_ref,
                    "maturity_ref": None,
                },
            )
        ledger_path.write_text(json.dumps(ledger, indent=2), encoding="utf-8")

        # 1. Assert 55/43/12/0 accounting success
        proc = run_cli(root, "--json")
        self.assertEqual(proc.returncode, 0, proc.stdout + "\n" + proc.stderr)
        result = json.loads(proc.stdout)
        self.assertTrue(result["valid"])
        self.assertTrue(result["passed"])
        self.assertEqual(
            (result["total_inherited_rows"], result["terminal_rows"], result["open_rows"], result["invalid_rows"]),
            (55, 43, 12, 0),
        )
        self.assertEqual(result["inherited_roadmap_open_items"], 12)
        self.assertFalse(result["zero_backlog_qualified"])
        self.assertEqual(result["diagnostics"], [])

        # 2. Preserve 31 APG139 rows and 12 D/E rows byte-value unchanged
        current_v0110b = [item for item in ledger["items"] if item["closure_phase"] == "V0110-B"]
        initial_v0110b = [item for item in initial_items if item["closure_phase"] == "V0110-B"]
        self.assertEqual(len(current_v0110b), 31)
        self.assertEqual(current_v0110b, initial_v0110b)
        self.assertEqual(
            [json.dumps(x, sort_keys=True) for x in current_v0110b],
            [json.dumps(x, sort_keys=True) for x in initial_v0110b],
        )

        current_de = [item for item in ledger["items"] if item["closure_phase"] in ("V0110-D", "V0110-E")]
        initial_de = [item for item in initial_items if item["closure_phase"] in ("V0110-D", "V0110-E")]
        self.assertEqual(len(current_de), 12)
        self.assertEqual(current_de, initial_de)
        self.assertEqual(
            [json.dumps(x, sort_keys=True) for x in current_de],
            [json.dumps(x, sort_keys=True) for x in initial_de],
        )

        # 3. --require-zero refuses because 12 open D/E items remain
        proc_zero = run_cli(root, "--require-zero", "--json")
        self.assertEqual(proc_zero.returncode, 1)
        data_zero = json.loads(proc_zero.stdout)
        self.assertTrue(data_zero["valid"])
        self.assertFalse(data_zero["passed"])
        self.assertEqual(data_zero["terminal_rows"], 43)
        self.assertEqual(data_zero["open_rows"], 12)
        self.assertEqual(data_zero["inherited_roadmap_open_items"], 12)
        self.assertFalse(data_zero["zero_backlog_qualified"])

        # 4. Refusals: missing review
        (root / reviews).unlink()
        self.assertEqual(run_cli(root, "--json").returncode, 1)
        (root / reviews).write_text("Synthetic V0110-C review reinstated.\n")
        self.assertEqual(run_cli(root, "--json").returncode, 0)

        # Refusals: invalid / non-existent review_ref
        sample_item = next(item for item in ledger["items"] if item["item_id"] == "APGR-CI-QUAL")
        sample_item["disposition"]["review_ref"] = "docs/governance/nonexistent-review.md"
        ledger_path.write_text(json.dumps(ledger, indent=2), encoding="utf-8")
        self.assertEqual(run_cli(root, "--json").returncode, 1)
        sample_item["disposition"]["review_ref"] = reviews
        ledger_path.write_text(json.dumps(ledger, indent=2), encoding="utf-8")
        self.assertEqual(run_cli(root, "--json").returncode, 0)

        # Refusals: missing evidence in decision receipt
        sample_receipt_path = root / "docs/governance/fixture-decisions-v0110c/RM-S0.json"
        sample_receipt_orig = sample_receipt_path.read_text(encoding="utf-8")
        sample_receipt_data = json.loads(sample_receipt_orig)
        sample_receipt_data["evidence"]["implementation"] = ["docs/governance/nonexistent-evidence.md"]
        sample_receipt_path.write_text(json.dumps(sample_receipt_data, indent=2), encoding="utf-8")
        self.assertEqual(run_cli(root, "--json").returncode, 1)
        sample_receipt_path.write_text(sample_receipt_orig, encoding="utf-8")
        self.assertEqual(run_cli(root, "--json").returncode, 0)

        # Refusals: mismatched handoff linkage (wrong watch referenced)
        sample_item["disposition"]["compatibility_ref"] = "JACA-XO"
        ledger_path.write_text(json.dumps(ledger, indent=2), encoding="utf-8")
        self.assertEqual(run_cli(root, "--json").returncode, 1)
        sample_item["disposition"]["compatibility_ref"] = "JACA-CI"
        ledger_path.write_text(json.dumps(ledger, indent=2), encoding="utf-8")
        self.assertEqual(run_cli(root, "--json").returncode, 0)

        # Refusals: mismatched handoff linkage (watch status is WATCH instead of HANDOFF_CLOSED)
        for watch in compat["watches"]:
            if watch["watch_id"] == "JACA-CI":
                watch["status"] = "WATCH"
                watch["qualification_evidence"] = []
        compat_path.write_text(json.dumps(compat, indent=2), encoding="utf-8")
        self.assertEqual(run_cli(root, "--json").returncode, 1)
        for watch in compat["watches"]:
            if watch["watch_id"] == "JACA-CI":
                watch["status"] = "HANDOFF_CLOSED"
                watch["qualification_evidence"] = [reviews]
        compat_path.write_text(json.dumps(compat, indent=2), encoding="utf-8")
        self.assertEqual(run_cli(root, "--json").returncode, 0)

        # Refusals: mismatched handoff linkage (item missing from watch inherited_item_ids)
        for watch in compat["watches"]:
            if watch["watch_id"] == "JACA-CI":
                watch["inherited_item_ids"] = []
        compat_path.write_text(json.dumps(compat, indent=2), encoding="utf-8")
        self.assertEqual(run_cli(root, "--json").returncode, 1)
        for watch in compat["watches"]:
            if watch["watch_id"] == "JACA-CI":
                watch["inherited_item_ids"] = ["APGR-CI-QUAL"]
        compat_path.write_text(json.dumps(compat, indent=2), encoding="utf-8")
        self.assertEqual(run_cli(root, "--json").returncode, 0)


    def test_terminal_apg140_apg141_apg142_receipts_and_accounting(self):
        """Check actual terminal receipts separately from historical disposable cases."""
        result = run_cli(REPOSITORY_ROOT, "--json")
        self.assertEqual(result.returncode, 0, result.stdout)
        value = json.loads(result.stdout)
        self.assertEqual((value["terminal_rows"], value["open_rows"], value["invalid_rows"]),
                         (55, 0, 0))
        ledger = json.loads((REPOSITORY_ROOT / "docs/governance/v0-11-closure-ledger.json").read_text())
        for row in ledger["items"]:
            if row["closure_phase"] in ("V0110-C", "V0110-D"):
                self.assertTrue(closure.receipt_valid(REPOSITORY_ROOT, row))
                self.assertIn("/decisions/", row["disposition"]["decision_ref"])
                broken = copy.deepcopy(row)
                broken["disposition"]["decision_ref"] = (
                    ("docs/governance/external/apg140" if row["closure_phase"] == "V0110-C"
                     else "docs/governance/optional/apg141") + "/candidates/" + row["item_id"] + ".json")
                self.assertFalse(closure.receipt_valid(REPOSITORY_ROOT, broken))

    def test_terminal_apg142_receipts_bind_actual_review(self):
        records, errors = closure.load_records(REPOSITORY_ROOT)
        maintenance = closure.check_maintenance(REPOSITORY_ROOT, records, errors)
        self.assertEqual(errors, [])
        rows = [r for r in records["closure"]["items"] if r["closure_phase"] == "V0110-E"]
        self.assertEqual(len(rows), 8)
        for row in rows:
            self.assertEqual(row["status"], "MAINTENANCE_TRIGGER")
            self.assertIn("/decisions/", row["disposition"]["decision_ref"])
            self.assertTrue(closure.receipt_valid(REPOSITORY_ROOT, row, maintenance=maintenance))
            self.assertEqual(row["disposition"]["review_ref"],
                             "docs/governance/maintenance/apg142/work-review.md")
        result = run_cli(REPOSITORY_ROOT, "--json", "--require-zero")
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_actual_apg140_candidate_payloads_require_review_binding(self):
        """Use real candidate bytes with synthetic review ONLY in a disposable root."""
        root = self.fixture_root
        base = "docs/governance/external/apg140"
        index = json.loads((root / base / "candidates.json").read_text())
        ledger_path = root / "docs/governance/v0-11-closure-ledger.json"
        ledger = json.loads(ledger_path.read_text())
        actual = {row["item_id"]: row for row in ledger["items"]}
        self.assertEqual({row["item_id"] for row in index["candidates"]},
                         {row["item_id"] for row in ledger["items"] if row["closure_phase"] == "V0110-C"})
        review = base + "/synthetic-review.txt"
        (root / review).write_text("Synthetic fixture reviewer only; not actual APG140 review.\n")
        for entry in index["candidates"]:
            candidate = json.loads((root / entry["candidate_ref"]).read_text())
            self.assertEqual(candidate["review_status"], "PENDING_DISPATCHER_PRE_FINAL")
            self.assertIsNone(candidate["review_sha256"])
            self.assertIsNone(candidate["receipt"]["reviewer"])
            row = actual[entry["item_id"]]
            self.assertEqual(row["status"], "OPEN")
            row["status"] = entry["outcome"]
            row["disposition"] = candidate["proposed_disposition"]
            # The wrapper is not a terminal receipt, even though it exists.
            self.assertFalse(closure.receipt_valid(root, row))
            receipt = candidate["receipt"]
            receipt["reviewer"] = "synthetic fixture reviewer"
            (root / entry["candidate_ref"]).write_text(json.dumps(receipt))
            row["disposition"]["review_ref"] = review
        ledger_path.write_text(json.dumps(ledger))
        result = run_cli(root, "--json")
        self.assertEqual(result.returncode, 0, result.stdout)
        value = json.loads(result.stdout)
        self.assertEqual((value["terminal_rows"], value["open_rows"], value["invalid_rows"]), (43, 12, 0))
        self.assertEqual(run_cli(root, "--json", "--require-zero").returncode, 1)

    def test_apg141_candidates_refuse_until_review_then_preserve_eight_open(self):
        """Synthetic review tests receipt mechanics; it is not APG141 acceptance."""
        root = self.fixture_root
        base = "docs/governance/optional/apg141"
        index = json.loads((root / base / "candidates.json").read_text())
        ledger_path = root / "docs/governance/v0-11-closure-ledger.json"
        ledger = json.loads((REPOSITORY_ROOT / "docs/governance/v0-11-closure-ledger.json").read_text())
        # Reconstruct producer entry; current repository now has terminal receipts.
        for row in ledger["items"]:
            if row["closure_phase"] in ("V0110-D", "V0110-E"):
                row.update(status="OPEN", disposition=None)
        protected = [copy.deepcopy(row) for row in ledger["items"] if row["closure_phase"] != "V0110-D"]
        rows = {row["item_id"]: row for row in ledger["items"]}
        self.assertEqual({entry["item_id"] for entry in index["candidates"]},
                         {row["item_id"] for row in ledger["items"] if row["closure_phase"] == "V0110-D"})
        review = base + "/synthetic-review.txt"
        (root / review).write_text("Synthetic fixture only, no actual independent review.\n")
        for entry in index["candidates"]:
            candidate = json.loads((root / entry["candidate_ref"]).read_text())
            self.assertIsNone(candidate["receipt"]["reviewer"])
            self.assertIsNone(candidate["review_ref"])
            self.assertIsNone(candidate["review_sha256"])
            row = rows[entry["item_id"]]
            self.assertEqual(row["status"], "OPEN")
            row.update(status=entry["outcome"], disposition=candidate["proposed_disposition"])
            self.assertFalse(closure.receipt_valid(root, row))
            receipt = candidate["receipt"]
            receipt["reviewer"] = "synthetic fixture reviewer"
            for refs in receipt["evidence"].values():
                for ref in refs:
                    source = REPOSITORY_ROOT / ref
                    target = root / ref
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
            (root / entry["candidate_ref"]).write_text(json.dumps(receipt))
            row["disposition"]["review_ref"] = review
        ledger_path.write_text(json.dumps(ledger))
        result = run_cli(root, "--json")
        self.assertEqual(result.returncode, 0, result.stdout)
        data = json.loads(result.stdout)
        self.assertEqual((data["terminal_rows"], data["open_rows"], data["invalid_rows"]), (47, 8, 0))
        self.assertEqual([row for row in ledger["items"] if row["closure_phase"] != "V0110-D"], protected)
        zero = run_cli(root, "--json", "--require-zero")
        self.assertEqual(zero.returncode, 1)
        self.assertEqual(json.loads(zero.stdout)["open_rows"], 8)
        (root / review).unlink()
        self.assertEqual(run_cli(root, "--json").returncode, 1)

    def test_apg142_maintenance_trigger_receipt_validation_and_refusals(self) -> None:
        """Verify APG142 MAINTENANCE_TRIGGER receipts, 8 exact ID mappings, and refusals."""
        root = self.fixture_root
        gov = root / "docs/governance"
        ledger_path = gov / "v0-11-closure-ledger.json"
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        maint_path = gov / "maintenance-triggers.json"
        maint = json.loads(maint_path.read_text(encoding="utf-8"))
        triggers = {t["trigger_id"]: t for t in maint["triggers"]}

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
        v0110_e_items = {item["item_id"]: item for item in ledger["items"] if item["closure_phase"] == "V0110-E"}
        self.assertEqual(set(v0110_e_items.keys()), set(expected_mappings.keys()))
        for item_id, expected_trig in expected_mappings.items():
            self.assertEqual(v0110_e_items[item_id]["trigger_ref"], expected_trig)
            self.assertIn("MAINTENANCE_TRIGGER", v0110_e_items[item_id]["allowed_outcomes"])

        # Setup synthetic review and refresh documentation files
        review_file = "docs/governance/synthetic-apg142-review.md"
        (root / review_file).write_text("Synthetic independent review for APG142 maintenance trigger receipts.\n")
        refresh_file = "docs/governance/synthetic-refresh-procedure.md"
        (root / refresh_file).write_text("Synthetic refresh procedure documentation.\n")
        obs_file = "docs/governance/synthetic-observation.md"
        (root / obs_file).write_text("Synthetic trigger state observation evidence.\n")

        # Set all 8 triggers to FALSE with valid state evidence in the fixture
        for trig_id in expected_mappings.values():
            triggers[trig_id]["current_state"] = "FALSE"
            triggers[trig_id]["state_evidence"] = [obs_file]
        maint_path.write_text(json.dumps(maint, indent=2), encoding="utf-8")

        receipts_dir = gov / "fixture-decisions-apg142"
        receipts_dir.mkdir(parents=True, exist_ok=True)

        records, _ = closure.load_records(root)
        m = closure.check_maintenance(root, records, [])
        comp = closure.check_compatibility(root, records, [])
        mat = closure.check_maturity(root, records, m, [])
        linked = (m, comp, mat)

        for item_id, trig_id in expected_mappings.items():
            row = copy.deepcopy(v0110_e_items[item_id])
            decision_path = f"docs/governance/fixture-decisions-apg142/{item_id}.json"
            receipt = {
                "schema_version": "apg.roadmap-decision/v1",
                "item_id": item_id,
                "outcome": "MAINTENANCE_TRIGGER",
                "closure_phase": "V0110-E",
                "author": "synthetic producer",
                "reviewer": "synthetic reviewer",
                "evidence": {
                    "trigger_observation": [obs_file],
                    "refresh_procedure": [refresh_file],
                    "independent_review": [review_file],
                },
            }
            (root / decision_path).write_text(json.dumps(receipt, indent=2))
            row["status"] = "MAINTENANCE_TRIGGER"
            row["disposition"] = {
                "decision_ref": decision_path,
                "qualification_refs": [obs_file, refresh_file],
                "review_ref": review_file,
                "rationale": f"Synthetic maintenance trigger receipt for {item_id}",
                "maintenance_ref": trig_id,
                "compatibility_ref": None,
                "maturity_ref": None,
            }

            # Positive FALSE: valid receipt with FALSE trigger state
            self.assertTrue(closure.receipt_valid(root, row, linked[2], linked[0]))
            self.assertTrue(closure.disposition_valid(root, row, linked))

            # Refusal on TRUE/UNKNOWN trigger state
            for bad_state in ("TRUE", "UNKNOWN"):
                m[trig_id]["current_state"] = bad_state
                self.assertFalse(closure.receipt_valid(root, row, linked[2], linked[0]))
                self.assertFalse(closure.disposition_valid(root, row, linked))
            m[trig_id]["current_state"] = "FALSE"

            # Refusal on mismatched trigger_observation (not matching state_evidence)
            bad_receipt = copy.deepcopy(receipt)
            bad_receipt["evidence"]["trigger_observation"] = [refresh_file]
            (root / decision_path).write_text(json.dumps(bad_receipt))
            self.assertFalse(closure.receipt_valid(root, row, linked[2], linked[0]))
            (root / decision_path).write_text(json.dumps(receipt))

            # Refusal on mismatched independent_review
            bad_receipt = copy.deepcopy(receipt)
            bad_receipt["evidence"]["independent_review"] = [refresh_file]
            (root / decision_path).write_text(json.dumps(bad_receipt))
            self.assertFalse(closure.receipt_valid(root, row, linked[2], linked[0]))
            (root / decision_path).write_text(json.dumps(receipt))

            # Refusal on qualification_refs missing observation or refresh procedure
            bad_row = copy.deepcopy(row)
            bad_row["disposition"]["qualification_refs"] = [refresh_file]
            self.assertFalse(closure.receipt_valid(root, bad_row, linked[2], linked[0]))
            bad_row["disposition"]["qualification_refs"] = [obs_file]
            self.assertFalse(closure.receipt_valid(root, bad_row, linked[2], linked[0]))

            # Refusal on borrowed/mismatched maintenance_ref
            bad_row = copy.deepcopy(row)
            bad_row["disposition"]["maintenance_ref"] = "APGR-REPORT-PUREGO-GIT" if trig_id != "APGR-REPORT-PUREGO-GIT" else "CSS-QD-001"
            self.assertFalse(closure.receipt_valid(root, bad_row, linked[2], linked[0]))

    def test_apg142_actual_candidates_require_review_and_preserve_debts(self):
        """Actual candidate bytes cross the public CLI only with SYNTHETIC review."""
        root = self.fixture_root
        ledger_path = root / "docs/governance/v0-11-closure-ledger.json"
        ledger = json.loads((REPOSITORY_ROOT / "docs/governance/v0-11-closure-ledger.json").read_text())
        for row in ledger["items"]:
            if row["closure_phase"] == "V0110-E":
                row.update(status="OPEN", disposition=None)
        # Preserve prior delivered implementation references in the real-file fixture.
        for row in ledger["items"]:
            if row["status"] == "OPEN":
                continue
            receipt = json.loads((REPOSITORY_ROOT / row["disposition"]["decision_ref"]).read_text())
            for refs in receipt["evidence"].values():
                for ref in refs:
                    source = REPOSITORY_ROOT / ref
                    target = root / ref
                    if not target.exists():
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(source, target)
        prior = copy.deepcopy([r for r in ledger["items"] if r["closure_phase"] != "V0110-E"])
        debt_path = root / "docs/governance/language-profile-known-debt.json"
        debt_bytes = debt_path.read_bytes()
        expected_blocks = {**{f"CSS-QD-{i:03d}": i < 5 for i in range(1, 6)}, "JS-QD-005": True}
        self.assertEqual({d["debt_id"]: d["blocks_stable"] for d in json.loads(debt_bytes)["debts"]}, expected_blocks)
        index = json.loads((root / "docs/governance/maintenance/apg142/candidates.json").read_text())
        self.assertIsNone(index["actual_review_ref"])
        review = "docs/governance/SYNTHETIC-apg142-review.md"
        (root / review).write_text("SYNTHETIC test evidence only, never actual review.\n")
        rows = {r["item_id"]: r for r in ledger["items"]}
        for entry in index["candidates"]:
            wrapper = json.loads((root / entry["candidate_ref"]).read_text())
            self.assertIsNone(wrapper["review_ref"])
            row = rows[entry["item_id"]]
            row.update(status="MAINTENANCE_TRIGGER", disposition=wrapper["proposed_disposition"])
            receipt = wrapper["receipt"]
            self.assertIsNone(receipt["reviewer"])
            dest = "docs/governance/SYNTHETIC-" + row["item_id"] + ".json"
            row["disposition"].update(decision_ref=dest, review_ref=review)
            records, errors = closure.load_records(root)
            maintenance = closure.check_maintenance(root, records, errors)
            self.assertEqual(errors, [])
            (root / dest).write_text(json.dumps(receipt))
            self.assertFalse(closure.receipt_valid(root, row, maintenance=maintenance))
            receipt["reviewer"] = "SYNTHETIC independent reviewer"
            (root / dest).write_text(json.dumps(receipt))
            # Valid shape and all other bindings still refuse absent review evidence.
            self.assertTrue(closure.matches(receipt, contract.decision_schema()))
            self.assertFalse(closure.receipt_valid(root, row, maintenance=maintenance))
            receipt["evidence"]["independent_review"] = [review]
            (root / dest).write_text(json.dumps(receipt))
            self.assertTrue(closure.receipt_valid(root, row, maintenance=maintenance))
        ledger_path.write_text(json.dumps(ledger))
        result = run_cli(root, "--json", "--require-zero")
        self.assertEqual(result.returncode, 0, result.stdout)
        data = json.loads(result.stdout)
        self.assertEqual((data["terminal_rows"], data["open_rows"], data["invalid_rows"]), (55, 0, 0))
        self.assertEqual([r for r in ledger["items"] if r["closure_phase"] != "V0110-E"], prior)
        self.assertEqual(debt_path.read_bytes(), debt_bytes)
        # Later valid observation accumulation must not invalidate a phase receipt.
        maintenance_path = root / "docs/governance/maintenance-triggers.json"
        register = json.loads(maintenance_path.read_text())
        first_trigger = index["candidates"][0]["trigger_id"]
        trigger = next(t for t in register["triggers"] if t["trigger_id"] == first_trigger)
        original_evidence = list(trigger["state_evidence"])
        later = "docs/governance/SYNTHETIC-later-observation.md"
        (root / later).write_text("SYNTHETIC later FALSE observation.\n")
        trigger["state_evidence"] = [later, *reversed(original_evidence)]
        maintenance_path.write_text(json.dumps(register))
        result = run_cli(root, "--json", "--require-zero")
        self.assertEqual(result.returncode, 0, result.stdout)
        trigger["state_evidence"] = [later]
        maintenance_path.write_text(json.dumps(register))
        self.assertEqual(run_cli(root, "--json").returncode, 1)
        trigger["state_evidence"] = original_evidence
        maintenance_path.write_text(json.dumps(register))
        # A borrowed existing observation must fail even when paths all exist.
        first, second = index["candidates"][:2]
        decision = root / rows[first["item_id"]]["disposition"]["decision_ref"]
        original = decision.read_bytes()
        receipt = json.loads(original)
        receipt["evidence"]["trigger_observation"] = [second["audit_ref"]]
        decision.write_text(json.dumps(receipt))
        self.assertEqual(run_cli(root, "--json").returncode, 1)
        decision.write_bytes(original)
        # Removing the actual linked review is a public CLI refusal.
        (root / review).unlink()
        self.assertEqual(run_cli(root, "--json").returncode, 1)


if __name__ == "__main__":
    unittest.main()
