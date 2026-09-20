"""Scenario 15 run-owned projection construction; no native discovery claim."""
import hashlib
import json
from pathlib import Path

from .execution import _write_bytes, _write_json, snapshot_tree

SKILL = "typescript-language-profile"


def _directories(root):
    return sorted(str(path.relative_to(root)) for path in root.rglob("*") if path.is_dir())


def materialize(source_root, destination, plan):
    source_root, destination = Path(source_root), Path(destination)
    snapshots = plan.get("selected_snapshots")
    if not isinstance(snapshots, list) or [row.get("qualified_id") for row in snapshots] != ["apgr:" + SKILL]:
        raise ValueError("Scenario 15 projection requires exactly its selected skill")
    source = source_root / "skills" / SKILL
    before = snapshot_tree(source)
    selected = next((row for row in plan["decisions"]
                     if row.get("selected_id") == "apgr:" + SKILL and row.get("status") == "selected"), None)
    if selected is None or selected["whole_source"]["sha256"] != before["SKILL.md"]["sha256"]:
        raise ValueError("projected skill does not match native selection")
    tree = destination / ".claude/skills" / SKILL
    tree.mkdir(mode=0o700, parents=True)
    for name in before:
        path = tree / name
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        _write_bytes(path, (source / name).read_bytes())
    if snapshot_tree(source) != before:
        raise ValueError("projection source changed")
    actual = snapshot_tree(tree)
    if {k: (v["bytes"], v["sha256"]) for k, v in before.items()} != {
            k: (v["bytes"], v["sha256"]) for k, v in actual.items()}:
        raise ValueError("projected skill bytes differ")
    settings = destination / "isolated-claude-settings.json"
    _write_json(settings, {})
    receipt = {"schema": "apg.h-selective-projection/v1", "selected": ["apgr:" + SKILL],
               "files": snapshot_tree(destination), "settings": settings.name,
               "directories": _directories(destination),
               "source": before, "live_qualification": "contingent/unavailable"}
    _write_json(destination / "projection-receipt.json", receipt)
    return receipt


def verify(destination, receipt):
    destination = Path(destination)
    actual = snapshot_tree(destination)
    retained = actual.pop("projection-receipt.json", None)
    raw = (destination / "projection-receipt.json").read_bytes()
    if (retained is None or json.loads(raw) != receipt or actual != receipt["files"]
            or _directories(destination) != receipt["directories"]):
        raise ValueError("selective projection custody changed")
    return {"status": "complete", "sha256": hashlib.sha256(raw).hexdigest(),
            "selected": receipt["selected"], "live_qualification": "contingent/unavailable"}
