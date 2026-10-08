import hashlib
from pathlib import Path

import pytest

from testing.h_eval.projection_qualification import SKILL, materialize, verify

ROOT = Path(__file__).resolve().parents[3]


def plan():
    raw = (ROOT / "skills" / SKILL / "SKILL.md").read_bytes()
    return {"selected_snapshots": [{"qualified_id": "apgr:" + SKILL}],
            "decisions": [{"selected_id": "apgr:" + SKILL, "status": "selected",
                           "whole_source": {"sha256": hashlib.sha256(raw).hexdigest()}}]}


def test_selected_projection_retains_real_source_without_live_claim(tmp_path):
    receipt = materialize(ROOT, tmp_path / "projection", plan())
    assert verify(tmp_path / "projection", receipt)["status"] == "complete"
    assert receipt["live_qualification"] == "contingent/unavailable"
    source = ROOT / "skills" / SKILL / "SKILL.md"
    assert (tmp_path / "projection/.claude/skills" / SKILL / "SKILL.md").read_bytes() == source.read_bytes()


@pytest.mark.parametrize("fault", ["source", "extra", "directory", "changed"])
def test_projection_refuses_identity_and_discovery_growth(tmp_path, fault):
    selected = plan()
    if fault == "source":
        selected["decisions"][0]["whole_source"]["sha256"] = "0" * 64
        with pytest.raises(ValueError, match="selection"):
            materialize(ROOT, tmp_path / "projection", selected)
        return
    destination = tmp_path / "projection"
    receipt = materialize(ROOT, destination, selected)
    if fault == "extra":
        (destination / "unselected.md").write_text("unrelated")
    elif fault == "directory":
        (destination / "unselected").mkdir()
    else:
        (destination / "isolated-claude-settings.json").write_text('{"changed":true}')
    with pytest.raises(ValueError, match="custody"):
        verify(destination, receipt)
