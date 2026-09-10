"""Mechanical profile navigation and packaging contracts, not semantic proof."""
import json
from pathlib import Path
import re
from src.test.apg_test_support import repository_root

ROOT = repository_root(__file__)
NAME = 'npm-package-manager-profile'
PREFIX = 'NPM'


def test_clause_ids_and_scenario_navigation_are_complete() -> None:
    leaf = (ROOT / "skills" / NAME / "SKILL.md").read_text()
    clauses = re.findall(r"\*\*(" + PREFIX + r"-\d{2})-[A-Z-]+\.\*\*", leaf)
    assert clauses == [f"{PREFIX}-{number:02d}" for number in range(1, 13)]
    spec = (ROOT / "docs/specs" / f"{NAME}.md").read_text()
    for clause in clauses:
        assert clause in spec
    register = json.loads((ROOT / "src/test/fixtures/apg124-toolchain" / PREFIX.lower() / "scenarios.json").read_text())
    assert [row["id"] for row in register["scenarios"]] == [f"{PREFIX}{number:02d}" for number in range(1, 13)]


def test_profile_projection_and_packaged_metadata_are_source_bound() -> None:
    source = ROOT / "skills" / NAME / "SKILL.md"
    description = re.search(r"(?m)^description: (.+)$", source.read_text())[1]
    assert 0 < len(description.encode()) <= 330
    projection = ROOT / ".agents/skills" / NAME
    assert projection.is_symlink()
    assert projection.readlink() == Path(f"../../skills/{NAME}")
    metadata = json.loads((ROOT / "src/agentic_praxis_grimoire/resources/skill-metadata.json").read_text())
    row, = [row for row in metadata["skills"] if row["name"] == NAME]
    import hashlib
    assert row["description"] == description
    assert row["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
