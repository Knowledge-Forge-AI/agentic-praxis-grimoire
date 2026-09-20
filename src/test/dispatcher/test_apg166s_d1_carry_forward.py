"""Historical source-default D1 regression; not current home-path qualification."""
from pathlib import Path
import shutil

from agent_phase.bundle import publish_bundle
from testing.h_eval import d1_qualification as d1
from test_h_d1_seam import _valid_authority

ROOT = Path(__file__).resolve().parents[3]


def test_d1_isolated_lifecycle_under_required_home_bundle(tmp_path, monkeypatch):
    source, home = tmp_path / "source", tmp_path / "home"
    shutil.copytree(ROOT / "common/dispatcher", source)
    models = source / "models.toml"
    models.write_text(models.read_text().replace('model = "claude-opus-5-5"', 'model = "claude-opus-5"'))
    publish_bundle(source, home / "dispatcher")
    (home / "config.toml").write_text("[dispatcher.bundle]\nrequired = true\n")
    monkeypatch.setenv("APGR_HOME", str(home))
    custody = tmp_path / "custody"
    evidence = custody / "evidence"
    record = d1.run_instrumented_d1_lifecycle(ROOT, evidence, _valid_authority(evidence, custody_dir=custody))
    assert record["provider_free_d1_seam_qualified"] is True
    assert record["route"]["model"] == "claude-opus-5-5"
    assert record["d1_status"] == "not-run"
    assert d1.readback_d1_record(evidence, ROOT)["record_digest"] == record["record_digest"]
