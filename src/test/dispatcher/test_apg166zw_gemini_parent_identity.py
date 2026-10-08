"""Provider-free qualification through the executed dispatcher stage boundary."""
from __future__ import annotations

import json
import os
import time
from copy import deepcopy
from pathlib import Path

import pytest
import test_apg166zt_qualifier_repair as qualifier_repair
from agent_phase import worker_canary as canary
from agent_phase.bundle import load_bundle
from agent_phase.dispatch import Dispatcher
from agent_phase.provider import Result
from antigravity_profile import StreamObserver
from antigravity_terminal_evidence import StderrCapture, write_terminal_evidence
from apgr_workers.ledger import ParentLedger
from test_agent_phase_antigravity import write_fake_evidence
from test_apg166zu_qualifier_correction import (
    correlated_record,
    isolated_budgets,
    observe_preflight,
)

ROOT = Path(__file__).resolve().parents[3]
FENCE = "0123456789abcdef0123456789abcdef"
canary_stage_environment = qualifier_repair.canary_stage_environment


def _write_executed_evidence(argv, *, status="SUCCESS", fence=True, model=None,
                             profile=None, response_source="nested", failure_after_fence=False,
                             response="provider-free executed-stage result", child_exit_code=0):
    """Use the maintained observer and v6 writer, without a provider process."""
    prefix = Path(argv[argv.index("--evidence-prefix") + 1])
    observer = StreamObserver(fence_nonce=FENCE)
    payload = {"status": status, "response": response}
    result = {"event": "result", "result": payload} if response_source == "nested" else {"event": "result", **payload}
    completion = {"event": "step_update", "step_update": {
        "step_type": "agent_response", "text_delta": f"<<<AGENT-CENTRAL-COMPLETE {FENCE}>>>\n"}}
    rows = ([completion, result] if failure_after_fence else [result, completion]) if fence else [result]
    for row in rows:
        observer.feed(json.dumps(row).encode() + b"\n")
    cleanup = {
        "schema": "antigravity-process-group-cleanup-v1", "reason": "fixture-cleanup",
        "attempted": True, "term_status": "absent", "kill_status": "not_attempted",
        "group_absent": True, "group_state": "absent", "parent_reaped": True,
        "stdout_reader_joined": True, "stderr_reader_joined": True, "readers_joined": True,
        "cleanup_complete": True, "failure_class": None,
    }
    exit_code = 0 if observer.transport_success else 1
    write_terminal_evidence(
        prefix, profile=profile or argv[1], model=model or argv[1],
        reviewer="--reviewer" in argv, command=["fixture-agy"], observer=observer,
        stderr_capture=StderrCapture.create(), started_at="2026-10-03T00:00:00+00:00",
        ended_at="2026-10-03T00:00:01+00:00", duration_seconds=1.0,
        child_started=True, child_exit_code=child_exit_code, wrapper_exit_code=exit_code,
        received_signals=[], signal_events=[], child_exit_monotonic=time.monotonic(),
        process_group_cleanup=cleanup, version_probe_cleanup=cleanup,
    )
    return exit_code


def _run_gemini(tmp_path, monkeypatch, environment, *, evidence="valid", meta_mutation=None):
    home, _ = environment
    order = []
    budgets = isolated_budgets(tmp_path, monkeypatch, order)
    observe_preflight(monkeypatch, order)
    if meta_mutation:
        stage = Dispatcher._stage
        def tamper(self, *args, **kwargs):
            result, meta = stage(self, *args, **kwargs)
            meta_mutation(meta, args[0])
            return result, meta
        monkeypatch.setattr(Dispatcher, "_stage", tamper)
    def runner(argv, prompt, cwd, maximum, on_output=None):
        order.append("runner")
        exit_code = 0
        if evidence == "missing" or evidence == "forged-stream":
            pass
        elif evidence == "v2":
            write_fake_evidence(argv, 0)
        else:
            launch = list(argv)
            if evidence in {"wrong-prefix", "wrong-run"}:
                index = launch.index("--evidence-prefix") + 1
                prefix = Path(launch[index])
                if evidence == "wrong-run":
                    prefix = prefix.parent.parent / "foreign-run" / prefix.name
                    prefix.parent.mkdir(mode=0o700)
                else:
                    prefix = prefix.with_name("02-work")
                launch[index] = str(prefix)
            kwargs = {"response": (cwd / "nonce.txt").read_text().strip()}
            if evidence == "stale-terminal-response":
                kwargs["response"] = "nonce-from-a-prior-canary"
            if evidence == "wrong-model":
                kwargs["model"] = "wrong-model"
            if evidence == "wrong-profile":
                kwargs["profile"] = "wrong-profile"
            if evidence in {"provider-failure", "failure-after-fence"}:
                kwargs["status"] = "ERROR"
            if evidence == "failure-after-fence":
                kwargs["failure_after_fence"] = True
            if evidence == "no-fence":
                kwargs["fence"] = False
            if evidence == "event-response":
                kwargs["response_source"] = "event"
            if evidence == "post-fence-child-exit":
                kwargs["child_exit_code"] = -15
            exit_code = _write_executed_evidence(launch, **kwargs)
            if evidence == "malformed":
                Path(launch[-1] + ".antigravity-terminal-result.json").write_text("{invalid")
            if evidence == "v3":
                path = Path(launch[-1] + ".antigravity-terminal-result.json")
                value = json.loads(path.read_text())
                value.update(schema="antigravity-terminal-evidence-v3", version=3)
                path.write_text(json.dumps(value))
        raw = b"parent output has no model observation"
        if evidence == "forged-stream":
            raw = json.dumps({"type": "system", "subtype": "init",
                              "model": "gemini-3.8-flash-high", "effort": "high"}).encode()
        now = time.time()
        cleanup = {key: True for key in ("cleanup_proven", "outer_group_absent", "nested_groups_absent", "verified_absence", "reaped")}
        return Result(exit_code, raw, b"", False, now, now,
                      cleanup={**cleanup, "failure_reasons": []})
    record = canary.run_case(ROOT, home, tmp_path / "case", "gemini-sonnet", runner=runner)
    assert order == ["preflight", "reserve", "runner"]
    assert record["provider_invocations"] == 1
    assert budgets[canary.SONNET_PHASE].get_case("gemini-sonnet")["attempts"][0]["attempt"] == 1
    return record


def test_launch_bound_identity_passes_without_parent_stream_observation(tmp_path, monkeypatch, canary_stage_environment):
    record = _run_gemini(tmp_path, monkeypatch, canary_stage_environment)
    assert not record["parent_observed"].get("model")
    assert not record["parent_observed"].get("effort")
    assert record["qualification"]["dimensions"]["parent_model_effort"] is True, json.dumps({
        key: record["parent_identity"].get(key) for key in ("status", "checks", "diagnostic")})
    receipt = record["parent_identity"]
    assert receipt["status"] == receipt["basis"] == "launch_bound_match"
    assert receipt["runtime_effective_observation"] is False
    assert receipt["effort_observed"] is False
    assert all(value is True for value in receipt["checks"].values())
    assert record["status"] == "partial"  # No child is simulated in this parent-identity case.


@pytest.mark.parametrize("evidence", [
    "missing", "malformed", "wrong-prefix", "wrong-run", "wrong-model", "wrong-profile",
    "provider-failure", "failure-after-fence", "no-fence", "event-response", "v2", "v3", "forged-stream", "stale-terminal-response",
])
def test_invalid_or_unvalidated_transport_cannot_prove_parent(tmp_path, monkeypatch, canary_stage_environment, evidence):
    record = _run_gemini(tmp_path, monkeypatch, canary_stage_environment, evidence=evidence)
    assert record["qualification"]["dimensions"]["parent_model_effort"] is False
    assert record["parent_identity"]["status"] != "launch_bound_match"
    if evidence in {"provider-failure", "failure-after-fence"}:
        assert record["stage_meta"]["antigravity_evidence"]["validation"] == "validated"
        assert record["stage_meta"]["antigravity_evidence"]["provider_status"] == "error"
        assert record["parent_identity"]["checks"]["terminal_success"] is False


def test_post_fence_child_termination_is_not_parent_transport_failure(tmp_path, monkeypatch, canary_stage_environment):
    record = _run_gemini(tmp_path, monkeypatch, canary_stage_environment, evidence="post-fence-child-exit")
    assert record["stage_meta"]["antigravity_evidence"]["child_exit_code"] == -15
    assert record["qualification"]["dimensions"]["parent_model_effort"] is True


def _meta_change(field):
    def mutate(meta, directory):
        if field in {"stage", "role", "profile", "provider"}:
            meta[field] = "wrong-" + field
        elif field == "argv-prefix":
            meta["argv"][-1] = str(directory.path.parent / "foreign-run" / "01-work")
        elif field == "argv-launcher":
            meta["argv"][0] = "/fixture/wrong-launcher"
        elif field == "argv-reviewer":
            meta["argv"].remove("--reviewer")
        elif field == "stored-validation":
            meta["antigravity_evidence"]["provider_status"] = "success-forged"
        elif field == "stale-summary":
            path = directory.path / "01-work.antigravity-terminal-result.json"
            summary = json.loads(path.read_text())
            summary["ended_at"] = "stale-stage"
            path.write_text(json.dumps(summary))
        elif field in {"cap-model", "cap-effort", "cap-profile", "cap-mode"}:
            key = "execution_mode" if field == "cap-mode" else "parent_" + field.removeprefix("cap-")
            meta["worker_capability"][key] = "wrong-" + field
    return mutate


@pytest.mark.parametrize("field", ["stage", "role", "profile", "provider", "argv-prefix",
                                  "argv-launcher", "argv-reviewer", "stored-validation", "stale-summary",
                                  "cap-model", "cap-effort", "cap-profile", "cap-mode"])
def test_executed_stage_identity_is_bound(tmp_path, monkeypatch, canary_stage_environment, field):
    record = _run_gemini(tmp_path, monkeypatch, canary_stage_environment, meta_mutation=_meta_change(field))
    assert record["qualification"]["dimensions"]["parent_model_effort"] is False


@pytest.mark.parametrize("field", ["provider", "model", "effort", "profile", "parent_id", "route-mode", "route-slot",
                                  "resolved-endpoint", "roster-provenance", "candidate", "controller", "bundle", "request-only",
                                  "coordinated-effort", "registration-run", "registration-mode", "run-id", "run-directory", "nonce"])
def test_qualification_rejects_tampered_executed_receipt(tmp_path, monkeypatch, canary_stage_environment, field):
    record = _run_gemini(tmp_path, monkeypatch, canary_stage_environment)
    assert record["qualification"]["dimensions"]["parent_model_effort"] is True
    altered = deepcopy(record)
    if field in {"provider", "model", "effort", "profile"}:
        altered["parent"][field] = "claude" if field == "provider" else "wrong-" + field
    elif field == "parent_id":
        altered["parent_id"] = "foreign-parent"
    elif field == "route-mode":
        altered["route_provenance"]["execution_mode"] = "gemini_sub"
    elif field == "route-slot":
        altered["route_provenance"]["endpoint_slot"] = "plan_review"
    elif field == "resolved-endpoint":
        altered["route_provenance"]["resolved_endpoint"]["profile"] = "wrong-profile"
    elif field == "roster-provenance":
        altered["route_provenance"]["roster"]["generation"] = "stale-generation"
    elif field == "candidate":
        altered["candidate_source_identity"] = "wrong-candidate"
    elif field == "controller":
        altered["controller_identity"] = "wrong-controller"
    elif field == "bundle":
        altered["bundle"]["manifest_sha256"] = "wrong-bundle"
    elif field == "request-only":
        altered.pop("parent_identity")
    elif field == "coordinated-effort":
        altered["parent"]["effort"] = altered["parent_identity"]["parent"]["effort"] = "wrong-effort"
    elif field == "registration-run":
        altered["registered_parent_capability"]["parent_run_id"] = "foreign-run"
    elif field == "registration-mode":
        altered["registered_parent_capability"]["execution_mode"] = "gemini_sub"
    elif field == "run-id":
        altered["run_id"] = "foreign-run"
    elif field == "run-directory":
        altered["run_directory"] = "/fixture/foreign-run"
    elif field == "nonce":
        altered["nonce"] = "challenge-from-a-different-run"
    # A matching requested/stream identity cannot substitute for the executed receipt,
    # including when the record's provider is relabelled to select a different branch.
    altered["parent_observed"] = {key: altered["parent"][key] for key in ("provider", "model", "effort")}
    assert canary.qualify(altered)["dimensions"]["parent_model_effort"] is False


@pytest.mark.parametrize("mutation", ["slot", "mode", "profile", "capability", "profile-model"])
def test_preflight_refusal_spends_no_attempt_or_provider(tmp_path, monkeypatch, canary_stage_environment, mutation):
    home, _ = canary_stage_environment
    order = []
    budgets = isolated_budgets(tmp_path, monkeypatch, order)
    if mutation == "slot":
        monkeypatch.setitem(canary.CASE_ROUTES, "gemini-sonnet", ("implementation_testing", "gemini_flash_sub", "plan_review"))
    elif mutation == "mode":
        monkeypatch.setitem(canary.CASE_ROUTES, "gemini-sonnet", ("implementation_testing", "gemini_sub", "work"))
    elif mutation == "profile":
        monkeypatch.setitem(canary.CASES, "gemini-sonnet", ("antigravity", "gemini-3.1-pro-preview", "sonnet"))
    elif mutation == "profile-model":
        monkeypatch.setattr(canary, "antigravity_intelligence", lambda *a: {"model": "wrong-profile-file-model"})
    else:
        monkeypatch.setattr(canary, "resolve_worker_capability", lambda *a, **k: {"allowed": False, "reason": "injected preflight mismatch"})
    record = canary.run_case(ROOT, home, tmp_path / "case", "gemini-sonnet",
                            runner=lambda *a, **k: pytest.fail("preflight refusal invoked provider"))
    assert record["preflight_refusal"] is True
    assert record["provider_invocations"] == 0 and record["budget_reservation"] is None
    assert not budgets and not order
    assert not (tmp_path / "isolated-budget").exists()


def test_codex_keeps_provider_stream_identity(tmp_path, monkeypatch, canary_stage_environment):
    home, _ = canary_stage_environment
    order = []
    isolated_budgets(tmp_path, monkeypatch, order)
    selected = load_bundle(repo_root=ROOT, apgr_home=home, required=True).select_model("codex", "implementation-testing").as_dict()
    def runner(argv, prompt, cwd, maximum, on_output=None):
        now = time.time()
        raw = b'\n'.join(json.dumps(row).encode() for row in [
            {"type": "thread.started", "thread_id": "fixture-codex-thread"},
            {"type": "turn.started", "model": selected["model"], "effort": selected["effort"]},
        ])
        return Result(0, raw, b"", False, now, now,
                      cleanup={"cleanup_proven": True, "outer_group_absent": True, "nested_groups_absent": True,
                               "verified_absence": True, "reaped": True, "failure_reasons": []})
    record = canary.run_case(ROOT, home, tmp_path / "case", "codex-sonnet", runner=runner)
    assert record["qualification"]["dimensions"]["parent_model_effort"] is True
    assert "parent_identity" not in record
    record["parent_identity"] = {"status": "launch_bound_match"}
    record["parent_observed"] = {}
    assert canary.qualify(record)["dimensions"]["parent_model_effort"] is False


@pytest.mark.parametrize("case", ["gemini-sonnet", "codex-sonnet"])
def test_external_sonnet_qualification_through_executed_stage(tmp_path, monkeypatch, canary_stage_environment, case):
    home, _ = canary_stage_environment
    isolated_budgets(tmp_path, monkeypatch, [])
    family, profile, _ = canary.CASES[case]
    selected = load_bundle(repo_root=ROOT, apgr_home=home, required=True).select_model(family, profile).as_dict()
    def runner(argv, prompt, cwd, maximum, on_output=None):
        nonce = (cwd / "nonce.txt").read_text().strip()
        ledger = ParentLedger(os.environ["APGR_PARENT_ID"], Path(os.environ["APGR_WORKER_STATE_DIR"]))
        cap = ledger.get_status()["worker_capability"]
        requested = cap["sonnet_worker"]
        job = "injected-sonnet-result"
        ledger.reserve_external(job, job, "fixture-payload", worker_kind="sonnet")
        child = {"parent_id": ledger.parent_id, "job_id": job, "worker_kind": "sonnet",
                 "effective_model": requested["model"], "effective_effort": requested["effort"],
                 "transport": "claude_external", "status": "completed", "cleanup_proven": True, "response": nonce}
        assert ledger.update_gemini_status(job, "completed", result=child, cleanup_proven=True)
        (ledger.base_dir / (job + ".result.json")).write_text(json.dumps(child))
        if family == "antigravity":
            assert _write_executed_evidence(argv, response=nonce) == 0
            raw = nonce.encode()  # No Claude/Codex-style model event.
        else:
            raw = b'\n'.join(json.dumps(row).encode() for row in [
                {"type": "thread.started", "thread_id": "fixture-codex-thread"},
                {"type": "turn.started", "model": selected["model"], "effort": selected["effort"]},
                {"type": "item.completed", "item": {"type": "agent_message", "text": nonce}},
            ])
        now = time.time()
        return Result(0, raw, b"", False, now, now,
                      cleanup={"cleanup_proven": True, "outer_group_absent": True, "nested_groups_absent": True,
                               "verified_absence": True, "reaped": True, "failure_reasons": []})
    record = canary.run_case(ROOT, home, tmp_path / "case", case, runner=runner)
    assert record["provider_invocations"] == 1
    assert record["qualification"]["passed"] is True, record["qualification"]["reasons"]
    if family == "antigravity":
        assert record["parent_identity"]["status"] == "launch_bound_match"
        assert not record["parent_observed"].get("model")
    else:
        assert "parent_identity" not in record


@pytest.mark.parametrize("count", [1, 5])
def test_claude_function_and_reuse_keep_unknown_child_effort(tmp_path, count):
    record, _ = correlated_record(tmp_path, count=count)
    for child in record["native_admission"]:
        child["model_observation"]["effective_effort"] = None
        child["model_observation"]["configured_effort"] = "high"
    record["parent_identity"] = {"status": "launch_bound_match", "effort": "high"}
    q = canary.qualify(record)
    assert q["dimensions"]["parent_model_effort"] is True
    assert q["functional"]["effort"] == "unknown"
    assert not q["dimensions"]["worker_kind_model_effort"]
    assert q["functional"]["child_admitted"] == count
    assert q["functional"]["call_coverage"] == "complete"
    assert q["dimensions"]["sequential_non_overlap"] is True
    if count == 1:
        assert canary.native_reuse_ready(q)
