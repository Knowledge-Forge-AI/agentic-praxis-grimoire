"""Disposable current-source H scaffolding; never a qualifying experiment binding."""
import hashlib
import json
from pathlib import Path
import shutil

import pytest

ROOT = Path(__file__).resolve().parents[3]
BINDINGS = "testing/h_eval/scenario-bindings.json"


@pytest.fixture
def current_source(tmp_path):
    """Rebind only copied route digests; retain frozen tasks, oracles and budgets."""
    original = (ROOT / BINDINGS).read_bytes()
    root = tmp_path / "current-source"
    for prefix in ("testing/h_eval", "testing/fixtures/context-eval", "docs/governance",
                   "docs/evaluations/apg166/promotions", "common/dispatcher", "codex/profiles",
                   "claude/profiles", "antigravity/profiles", "skills"):
        shutil.copytree(ROOT / prefix, root / prefix, ignore=shutil.ignore_patterns("__pycache__"))
    for name in ("claude/model-catalog-v1.json", "codex/AGENTS.md", "claude/CLAUDE.md",
                 "antigravity/GEMINI.md"):
        shutil.copy2(ROOT / name, root / name)
    value = json.loads(original)
    for row in value["scenarios"]:
        for route in row["routes"].values():
            route["source_sha256"] = {
                name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                for name in route["identity_sources"]}
    (root / BINDINGS).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    try:
        yield root
    finally:
        assert (ROOT / BINDINGS).read_bytes() == original
