"""Bounded navigation and packaging checks; executed browser predicates live in the harness."""
import hashlib
import json
from pathlib import Path
import re
from src.test.apg_test_support import repository_root

ROOT = repository_root(__file__)
NAME = "browser-runtime-profile"


def test_clause_navigation_matches_maintained_browser_register():
    leaf = (ROOT / "skills" / NAME / "SKILL.md").read_text()
    clauses = re.findall(r"\*\*(BR-\d{2}-[A-Z-]+)\.\*\*", leaf)
    assert len(clauses) == 16
    assert len(set(clauses)) == 16
    spec = (ROOT / "docs/specs/browser-runtime-profile.md").read_text()
    assert all(clause in spec for clause in clauses)
    register = json.loads((ROOT / "src/test/fixtures/apg123-browser-ui/scenarios.json").read_text())
    runtime = [row for row in register["scenarios"] if row["group"] == "browser_runtime"]
    assert [row["id"] for row in runtime] == [f"BR{i:02d}" for i in range(1, 15)]
    for row in runtime:
        assert set(row["supported_browsers"]) == {"chromium", "firefox", "webkit"}
        assert row["assertions"]
        assert row["id"] in spec


def test_projection_and_metadata_bind_exact_profile_source():
    source = ROOT / "skills" / NAME / "SKILL.md"
    description = re.search(r"(?m)^description: (.+)$", source.read_text())[1]
    assert 0 < len(description.encode()) <= 330
    projection = ROOT / ".agents/skills" / NAME
    assert projection.is_symlink()
    assert projection.readlink() == Path(f"../../skills/{NAME}")
    data = json.loads((ROOT / "src/agentic_praxis_grimoire/resources/skill-metadata.json").read_text())
    row, = [r for r in data["skills"] if r["name"] == NAME]
    assert row["description"] == description
    assert row["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()


def test_bounded_evidence_and_resource_guidance_guards():
    leaf = " ".join((ROOT / "skills" / NAME / "SKILL.md").read_text().split())
    # These are local wording guards, not an automated semantic review.
    for phrase in (
        "ordinary browser engines do not qualify actual",
        "not port-isolated origin scoping",
        "custom reasons can differ",
        "not automatically at image load or download initiation",
        "query` observes state; it does not request permission",
        "only executed receipts qualify them",
    ):
        assert phrase in leaf.lower()
    assert "private/" not in leaf
    assert "verified engines" not in leaf.lower()
