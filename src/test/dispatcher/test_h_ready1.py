"""Manager-carried D1 observations cannot become live readiness or rewritten history."""
import json
from pathlib import Path

import pytest

from testing.h_eval import readiness
from h_regression_fixtures import current_source

ROOT = Path(__file__).resolve().parents[3]


def test_current_source_round_trip_remains_non_authorizing():
    seal = readiness.make_ready1_seal(ROOT)
    readiness.verify_seal(ROOT, seal)
    assert seal["prerequisite_gates"]["bindings_current"]
    assert seal["prerequisite_gates"]["d1_carry_forward_recorded"]
    assert not seal["prerequisite_gates"]["provider_free_transaction"]
    for key in ("prerequisites_ready", "h_main_gate", "live_holdout_authorized", "h_gate_established"):
        assert seal[key] is False
    assert seal["qualified_promotions"] == seal["live_pairs"] == 0
    seal["prerequisites_ready"] = True
    with pytest.raises(ValueError, match="inputs changed"):
        readiness.verify_seal(ROOT, seal)


@pytest.mark.parametrize("key", ["independent_review", "manager_grant"])
def test_external_decision_cannot_be_injected(key):
    with pytest.raises(ValueError, match="custody belongs"):
        readiness.make_ready1_seal(ROOT, **{key: {"disposition": "accept"}})


@pytest.mark.parametrize("evidence", [
    {"manager_live_grant": True}, {"independent_review": "accept"},
    {"provider_free_transaction": True}, {"runtime_manifest_complete": True},
])
def test_caller_booleans_cannot_replace_readback(evidence):
    with pytest.raises(ValueError, match="retained mechanical"):
        readiness.make_ready1_seal(ROOT, evidence)


@pytest.mark.parametrize("change", ["live", "qualified", "status", "consumed", "self-approved"])
def test_carry_forward_rejects_rewritten_history(current_source, change):
    path = current_source / "testing/h_eval/d1-carry-forward.json"
    value = json.loads(path.read_bytes())
    if change == "live": value["replay"]["live_provider_run"] = True
    elif change == "qualified": value["live_qualified"] = True
    elif change == "status": value["attempts"]["D1-02"]["recorded_status"] = "qualified"
    elif change == "consumed": value["attempts"]["D1-01"]["consumed"] = False
    else: value["manager_decision"]["self_certified"] = True
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="historical boundary"):
        readiness.make_ready1_seal(current_source)


def test_missing_transaction_is_not_mechanical_success(tmp_path):
    with pytest.raises((ValueError, FileNotFoundError)):
        readiness.make_ready1_seal(ROOT, {"transaction_directory": str(tmp_path / "absent")})
