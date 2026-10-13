"""Pre-live inventories cannot be mistaken for completed execution evidence."""
import json
from pathlib import Path

import pytest

from testing.h_eval import preregistration as owner, readiness, runtime_manifest
from h_regression_fixtures import current_source

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def copied(current_source):
    return current_source


def test_subject_factory_manifest_is_bound(copied):
    path = copied / "testing/fixtures/context-eval/subjects/manifest.json"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="manifest binding"):
        owner.verify_bindings(copied)


def test_provider_free_preflight_and_blocked_seal(tmp_path, monkeypatch, current_source):
    from agent_phase import provider
    monkeypatch.setattr(provider, "run", lambda *a, **k: pytest.fail("provider invoked by preflight"))
    result = owner.preflight(current_source, tmp_path / "preflight")
    assert result == {"records": 15, "live_results": 0, "complete_execution_package": False}
    assert len(list((tmp_path / "preflight").glob("*.json"))) == 15
    for path in (tmp_path / "preflight").glob("*.json"):
        record = json.loads(path.read_bytes())
        assert record["status"] == "unavailable" and record["provider_invocations"] == 0
        assert not record["subject_materialized"] and not record["oracle_executed"]
    seal = readiness.make_qual4_seal(current_source)
    readiness.verify_seal(current_source, seal)
    assert not seal["prerequisites_ready"] and not seal["h_gate_established"]
    assert seal["live_pairs"] == seal["qualified_promotions"] == 0
    with pytest.raises(FileExistsError): owner.preflight(current_source, tmp_path / "preflight")


@pytest.mark.parametrize("change", ["hash", "route", "mode", "cohort", "contingency", "duplicate", "oracle",
                                   "missing-source", "missing-models", "model", "effort", "native-effort"])
def test_binding_drift_rejected(copied, change):
    owner.verify_bindings(copied)
    path = copied / "testing/h_eval/scenario-bindings.json"
    value = json.loads(path.read_bytes()); row = value["scenarios"][0]
    if change == "hash": row["scenario_sha256"] = "0" * 64
    elif change == "route": row["routes"]["adaptive"]["model"] = "other"
    elif change == "mode": row["routes"]["adaptive"]["requested_mode"] = "static"
    elif change == "cohort": row["cohorts"]["savings"] = True
    elif change == "contingency": value["scenarios"][-1]["contingency"] = "qualified"
    elif change == "duplicate": value["scenarios"][-1] = row
    elif change == "oracle": row["frozen_oracle"]["command"] = "true"
    elif change in {"missing-source", "missing-models", "model", "effort"}:
        for route in row["routes"].values():
            if change == "missing-source": route["source_sha256"].pop(route["identity_sources"][0])
            elif change == "missing-models":
                route["identity_sources"].remove("common/dispatcher/models.toml")
                route["source_sha256"].pop("common/dispatcher/models.toml")
            elif change == "model": route["model"] = "other-roster"
            else: route["effort"] = "low"
    elif change == "native-effort":
        native = copied / "codex/profiles/implementation-testing.config.toml"
        native.write_text(native.read_text().replace('"medium"', '"low"'))
        for route in row["routes"].values():
            route["source_sha256"][str(native.relative_to(copied))] = owner.sha(native.read_bytes())
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="cohort or contingency changed" if change == "contingency" else None):
        owner.verify_bindings(copied)


@pytest.mark.parametrize("change", ["body", "criteria", "task", "count", "reserve", "rubric"])
def test_promotion_drift_rejected(copied, change):
    path = copied / "testing/h_eval/promotion-preregistration.json"
    value = json.loads(path.read_bytes()); row = value["skills"][0]
    if change == "body": (copied / row["source_path"]).write_text("changed")
    elif change == "criteria": row["maturity_entry"]["current_maturity"] = "stable"
    elif change == "task": row["cases"][0]["prompt"] += " changed"
    elif change == "count": row["cases"] = row["cases"][:2]
    elif change == "reserve": value["reserve_substitution"] = True
    elif change == "rubric": row["review_rubric"]["promotion_authorized"] = True
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError): owner.verify_promotions(copied)


def test_runtime_identity_drift(tmp_path):
    executable = tmp_path / "provider"; executable.write_bytes(b"runtime")
    value = {"schema": runtime_manifest.SCHEMA, "files": {str(executable): runtime_manifest.file_identity(executable)},
             "providers": {"claude": {"executable": str(executable), "version_stdout": "fixture"}},
             "routes": {"test": "fixture"}}
    assert runtime_manifest.verify(value) == value
    executable.write_bytes(b"changed")
    with pytest.raises(ValueError, match="drift"): runtime_manifest.verify(value)
