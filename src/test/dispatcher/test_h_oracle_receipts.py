"""Provider-free H oracle/importer custody contracts."""
from __future__ import annotations

import hashlib
import json

import pytest

from testing.h_eval import importers, oracles, response_contract


def _review_response(scenario_id: str) -> dict[str, object]:
    return {
        "schema": response_contract.SCHEMA,
        "scenario_id": scenario_id,
        "summary": "Fixture review.",
        "findings": [{
            "path": "README.md",
            "category": "fixture",
            "summary": "Observed fixture fact.",
            "evidence": ["fixture evidence"],
        }],
        "limitations": [],
    }


def test_response_contract_is_symmetric_and_hides_expected_facts():
    value = _review_response("scenario-03")
    assert response_contract.validate(value, scenario_id="scenario-03")["findings"][0]["path"] == "README.md"
    with pytest.raises(response_contract.ResponseContractError):
        response_contract.validate({**value, "authority_preserved": True})
    with pytest.raises(response_contract.ResponseContractError):
        response_contract.validate({**value, "findings": [{"path": "README.md"}]})
    assert "broken-link" not in response_contract.instructions()
    assert "README.md" not in response_contract.instructions()


@pytest.mark.parametrize("provider", sorted(importers.PROVIDERS))
@pytest.mark.parametrize("scenario_id", [f"scenario-{number:02d}" for number in range(1, 16)])
def test_each_provider_importer_has_positive_negative_and_live_fake_qualification(provider, scenario_id):
    result = importers.qualify_importer(provider, scenario_id)
    assert result["schema"] == importers.QUALIFICATION_SCHEMA
    assert result["status"] == "complete", result
    assert result["provider_invocations"] == 0
    assert result["good"]["raw"]["bytes"] > 0
    assert result["bad"]["raw"]["bytes"] > 0
    assert result["live_fake"]["parse_status"] == "malformed"


def test_live_import_rejects_nested_instrumented_envelope():
    raw = (json.dumps({
        "type": "result",
        "subtype": "success",
        "result": {"answer": {"schema": "apg.instrumented-provider/v1", "model_observed": True}},
    }) + "\n").encode()
    imported = importers.import_claude(raw, {"provider": "claude", "execution": "live"})
    assert imported["parse_status"] == "malformed"
    assert imported["session"] is None
    assert imported["model_observed"] is None


@pytest.mark.parametrize("scenario_id", ["scenario-03", "scenario-11", "scenario-12", "scenario-14"])
def test_review_requires_source_fact_semantics_after_path_category_match(scenario_id):
    response = oracles._fixture_review_response(scenario_id, True)
    qualified, facts = oracles._review_check(scenario_id, {"review_response": response}, {})
    assert qualified is True, facts

    changed = json.loads(json.dumps(response))
    finding = changed["findings"][0]
    # Preserve the exact source-owned path and category while replacing the
    # semantic content.  The oracle must reject this model-authored-looking
    # placeholder rather than treating tuple identity as substantive evidence.
    finding["summary"] = "A review finding was observed."
    finding["evidence"] = ["The source was inspected."]
    qualified, facts = oracles._review_check(scenario_id, {"review_response": changed}, {})
    assert qualified is False, facts
    assert any(value["matches"] is False for value in facts["semantic_facts"])
    assert json.loads(json.dumps(facts))["semantic_facts"] == facts["semantic_facts"]


def test_oracle_requires_execution_owned_receipt_bundle(tmp_path):
    subject = tmp_path / "subject"
    subject.mkdir(mode=0o700)
    (subject / "README.md").write_text("fixture\n")
    before = {"README.md": {"bytes": 8, "sha256": "0" * 64, "mode": 0o600}}
    result = oracles.oracle_for("scenario-03").evaluate(
        "scenario-03", subject, before=before,
        arm_evidence={"authority": {"unchanged": True}},
        provider_result={"terminal": {"exit_code": 0}},
    )
    assert result["status"] == "unavailable"
    assert "receipt root" in result["evidence"][0]["kind"] or result["evidence"]


def test_oracle_fixture_exercise_requires_sealed_runtime(tmp_path):
    source = tmp_path / "source"
    source.mkdir(mode=0o700)
    scratch = tmp_path / "scratch"
    scratch.mkdir(mode=0o700)
    result = oracles.exercise_oracle(source, "scenario-01", fixture_root=tmp_path / "fixtures")
    assert result["status"] == "incomplete"
    assert result["good"] is False and result["bad"] is False
    assert "runtime manifest" in result["reason"]


def test_native_plan_derivation_refuses_recursive_claims():
    with pytest.raises(oracles._Incomplete):
        oracles._plan({"schema": "apg.invocation-context/v1", "selected_skills": ["apgr:go-language-profile"]})
    with pytest.raises(oracles._Incomplete):
        oracles._selected({"selected_skills": ["apgr:go-language-profile"]})


def test_instruction_delivery_requires_native_component_and_event():
    evidence = oracles._fixture_evidence("scenario-04", True)
    context = evidence["context"]
    component = context["instruction_plan"]["components"][0]
    payload = context["transport"]["argv"][-1].encode()
    event = {
        "schema": "apg.acquisition-event/v1", "event_id": "a" * 64,
        "run_id": context["run_id"], "binding_id": context["binding_id"], "attempt_id": "one",
        "kind": "initial_delivered", "channel": "instructions", "phase": "initial",
        "controlled_bytes": len(payload), "payload_sha256": hashlib.sha256(payload).hexdigest(),
    }
    assert oracles._instruction_delivery_check({"context": context, "events": [event]})[0] is True
    event["payload_sha256"] = component["rtk_slice_sha256"]
    event["controlled_bytes"] = component["rtk_slice_bytes"]
    assert oracles._instruction_delivery_check({"context": context, "events": [event]})[0] is False
    with pytest.raises(oracles._Incomplete):
        oracles._instruction_delivery_check({"instruction_delivery": {"slice_id": "rtk-instructions-slice"}})


def test_settings_isolation_requires_typed_private_identities():
    activity = oracles._fixture_evidence("scenario-15", True)["activity"]
    assert oracles._settings_isolation_check(activity)[0] is True
    changed = json.loads(json.dumps(activity))
    changed["settings_receipt"]["after"]["sha256"] = "0" * 64
    assert oracles._settings_isolation_check(changed)[0] is False
    with pytest.raises(oracles._Incomplete):
        oracles._settings_isolation_check({"nested": {"before": {"sha256": "1" * 64}, "after": {"sha256": "1" * 64}}})


def test_read_only_scope_binds_source_route_and_actual_native_argv():
    evidence = oracles._fixture_evidence("scenario-11", True)
    route = {
        "provider": "claude",
        "profile": "fixture-review",
        "binding_id": "fixture-binding",
        "role_binding": {
            "binding_id": "fixture-binding",
            "roles": ["Work Review"],
            "allowed_tools": ["view_file", "skill_search", "skill_acquire", "context_explain"],
        },
        "source_identity": {
            "schema": "apg.h-source-binding/v1",
            "owner": "testing.h_eval.preregistration",
            "scenario_id": "scenario-11",
            "bindings_path": "testing/h_eval/scenario-bindings.json",
            "route_sha256": "a" * 64,
            "source_sha256": {"claude/profiles/normal-final-review.json": "b" * 64},
            "identity_sources": ["claude/profiles/normal-final-review.json"],
        },
    }
    bundle = {"context": evidence["context"], "route": route}
    qualified, facts = oracles._read_only_scope_check("scenario-11", bundle)
    assert qualified is True
    assert facts["argv_read_only"] is True
    assert facts["scope_matches"] is True

    changed = json.loads(json.dumps(bundle))
    changed["route"]["role_binding"]["allowed_tools"].append("bash")
    assert oracles._read_only_scope_check("scenario-11", changed)[0] is False

    changed = json.loads(json.dumps(bundle))
    changed["context"]["transport"]["argv"].remove("--read-only")
    assert oracles._read_only_scope_check("scenario-11", changed)[0] is False

    with pytest.raises(oracles._Incomplete):
        oracles._read_only_scope_check("scenario-11", {"context": evidence["context"], "route": {}})


def test_static_delivery_uses_native_custody_without_adaptive_plan_claims(tmp_path):
    evidence = oracles._fixture_evidence("scenario-11", True)
    context = evidence["context"]
    context["requested_mode"] = "static"
    context["effective_mode"] = "static"
    context["planned"] = False
    context["prospective_plan"] = None
    route = {
        "provider": "claude",
        "profile": "fixture-review",
        "model": "fixture-model",
        "binding_id": "fixture-binding",
        "roles": ["Work Review"],
        "role_binding": {
            "binding_id": "fixture-binding",
            "roles": ["Work Review"],
            "allowed_tools": ["view_file", "skill_search", "skill_acquire", "context_explain"],
        },
        "source_identity": {
            "schema": "apg.h-source-binding/v1",
            "owner": "testing.h_eval.preregistration",
            "scenario_id": "scenario-11",
            "bindings_path": "testing/h_eval/scenario-bindings.json",
            "bindings_sha256": "a" * 64,
            "route_sha256": "b" * 64,
            "source_sha256": {"claude/profiles/normal-final-review.json": "c" * 64},
            "identity_sources": [
                "testing/h_eval/scenario-bindings.json",
                "claude/profiles/normal-final-review.json",
            ],
        },
    }
    event = {
        "schema": "apg.acquisition-event/v1",
        "event_id": "d" * 64,
        "run_id": context["run_id"],
        "binding_id": context["binding_id"],
        "attempt_id": context["attempt_id"],
        "kind": "initial_delivered",
        "channel": "prompt",
        "phase": "initial",
    }
    bundle = {"context": context, "route": route, "events": [event], "acquisitions": []}
    qualified, facts = oracles._static_delivery_check("scenario-11", bundle)
    assert qualified is True
    assert facts["prospective_plan_present"] is False
    assert facts["evaluation_contract_matches"] is True

    bundle["authority"] = {
        "git_before": {"head": "fixture"},
        "git_after": {"head": "fixture"},
        "git_unchanged": True,
        "unchanged": True,
    }
    bundle["review"] = oracles._fixture_review_response("scenario-11", True)
    raw = b"fixture-provider-result"
    provider_result = {
        "schema": "apg.h-provider-import/v1",
        "raw": {"bytes": len(raw), "sha256": oracles._sha256(raw)},
        "route": {"provider": "claude"},
        "terminal": {"exit_code": 0},
        "parse_status": "structured",
        "review_response_status": "accepted",
        "review_response": bundle["review"],
    }
    status, _ = oracles._assertion_evaluate(
        oracles.oracle_for("scenario-11"), tmp_path, {}, {}, provider_result, bundle
    )
    assert status == "pass"

    changed = json.loads(json.dumps(bundle))
    changed["context"]["configuration"].append("ambient/profile.json")
    assert oracles._static_delivery_check("scenario-11", changed)[0] is False

    changed = json.loads(json.dumps(bundle))
    changed["context"]["instruction_plan"]["components"] = [
        component for component in changed["context"]["instruction_plan"]["components"]
        if component.get("id") != "evaluation-response-contract"
    ]
    assert oracles._static_delivery_check("scenario-11", changed)[0] is False

    changed = json.loads(json.dumps(bundle))
    changed["context"]["prospective_plan"] = {"selected_skills": ["apgr:go-language-profile"]}
    assert oracles._static_delivery_check("scenario-11", changed)[0] is False

    changed = json.loads(json.dumps(bundle))
    changed["events"] = []
    assert oracles._static_delivery_check("scenario-11", changed)[0] is False

    changed["authority"] = bundle["authority"]
    changed["review"] = bundle["review"]
    status, _ = oracles._assertion_evaluate(
        oracles.oracle_for("scenario-11"), tmp_path, {}, {}, provider_result, changed
    )
    assert status == "fail"


def test_scenario10_static_does_not_require_late_acquisition():
    evidence = oracles._fixture_evidence("scenario-10", True)
    context = evidence["context"]
    context["requested_mode"] = "static"
    context["effective_mode"] = "static"
    context["planned"] = False
    context["prospective_plan"] = None
    route = {
        "provider": "codex",
        "profile": "fixture-producer",
        "model": "fixture-model",
        "binding_id": "fixture-binding",
        "roles": ["Work Review"],
        "role_binding": {
            "binding_id": "fixture-binding",
            "roles": ["Work Review"],
            "allowed_tools": ["view_file"],
        },
        "source_identity": {
            "schema": "apg.h-source-binding/v1",
            "owner": "testing.h_eval.preregistration",
            "scenario_id": "scenario-10",
            "bindings_path": "testing/h_eval/scenario-bindings.json",
            "bindings_sha256": "a" * 64,
            "route_sha256": "b" * 64,
            "source_sha256": {"claude/profiles/normal-final-review.json": "c" * 64},
            "identity_sources": [
                "testing/h_eval/scenario-bindings.json",
                "claude/profiles/normal-final-review.json",
            ],
        },
    }
    event = {
        "schema": "apg.acquisition-event/v1",
        "event_id": "e" * 64,
        "run_id": context["run_id"],
        "binding_id": context["binding_id"],
        "attempt_id": context["attempt_id"],
        "kind": "initial_delivered",
        "channel": "prompt",
        "phase": "initial",
    }
    qualified, facts = oracles._acquisition_check(
        "scenario-10", {"context": context, "route": route, "events": [event], "acquisitions": []}
    )
    assert qualified is True
    assert facts["acquisition_required"] is False
    assert facts["late_mcp_required"] is False


def test_reviewer_fixture_requires_adaptive_delivery():
    plan = oracles._fixture_plan("scenario-11", True)
    assert plan["effective_mode"] == "adaptive"
