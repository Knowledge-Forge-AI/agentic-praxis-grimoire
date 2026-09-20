"""Oracle admission evidence; full positive/negative qualification is incomplete."""
import copy

import pytest

from testing.h_eval import oracles, subjects


@pytest.mark.parametrize("scenario_id", subjects.all_scenario_ids())
def test_oracle_resolves_exact_frozen_contract_and_refuses_substitution(scenario_id):
    scenario = subjects.load_scenario(scenario_id)
    assert oracles.oracle_for(scenario).expected == scenario["expected_outcome"]["quality_oracle"]
    changed = copy.deepcopy(scenario)
    changed["expected_outcome"]["quality_oracle"]["assertions"] = "provider exit zero suffices"
    with pytest.raises(ValueError, match="changed"):
        oracles.oracle_for(changed)


def test_empty_authority_is_not_unchanged_evidence():
    with pytest.raises(oracles._Incomplete):
        oracles._authority_check("scenario-03", {"authority": {}})


def test_acquisition_claim_is_not_captured_delivery():
    with pytest.raises(oracles._Incomplete):
        oracles._acquisition_check("scenario-11", {"acquisition": {
            "status": "success", "channel": "mcp_result",
            "acquisition_status": "success", "body_returned_in_tool_result": True,
            "body_sha256_matches_canonical": True, "event_emitted": "claimed"}})
