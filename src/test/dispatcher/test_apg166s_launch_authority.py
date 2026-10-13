"""APG166S captured model authority and non-degrading launch boundaries."""
import json
from pathlib import Path
import shutil

import pytest

from agent_phase.bundle import load_bundle, publish_bundle
from agent_phase.runtime_models import captured, launch_capture, selection
from agent_phase.provider import build_argv
from agent_phase.provider_environment import process_options
from agent_phase.roster import Endpoint, load_roster
from agent_phase.routing import resolve
from agent_phase.request import PhaseRequest
from agent_phase.worker_evidence import parent_observation, native_admissions

ROOT = Path(__file__).resolve().parents[3]


def test_home_selection_reaches_codex_and_claude_launch(tmp_path, monkeypatch):
    source, home = tmp_path / "source", tmp_path / "home"
    shutil.copytree(ROOT / "common/dispatcher", source)
    models = source / "models.toml"
    text = models.read_text().replace('model = "gpt-6.1-sol"', 'model = "gpt-6-sol"')
    text = text.replace('model = "claude-opus-5-5"', 'model = "claude-opus-5"')
    models.write_text(text)
    publish_bundle(source, home / "dispatcher")
    monkeypatch.setenv("APGR_HOME", str(home))
    bundle = load_bundle(apgr_home=home, repo_root=ROOT)
    with captured(bundle):
        argv = build_argv(Endpoint("codex", "implementation-testing"), "worker", ROOT,
                          codex_executable="/fake/codex")
        assert 'model="gpt-6-sol"' in argv
        from claude_vc_profile import resolve_profile
        assert resolve_profile(ROOT / "claude", "opus-high-review").resolved_model_id == "claude-opus-5"


def test_stage_capture_survives_home_model_change(tmp_path, monkeypatch):
    home = tmp_path / "home"
    publish_bundle(ROOT / "common/dispatcher", home / "dispatcher")
    monkeypatch.setenv("APGR_HOME", str(home))
    bundle = load_bundle(apgr_home=home, repo_root=ROOT)
    run = tmp_path / "run"
    run.mkdir()
    with launch_capture(bundle, run):
        (home / "dispatcher/models.toml").write_text("invalid after capture")
        assert selection(ROOT, "codex", "luna-worker")["model"] == "gpt-6-luna"
        # A child reads the capture without sharing the Python context variable.
        with captured(None):
            assert selection(ROOT, "codex", "luna-worker")["effort"] == "max"


def test_provider_session_context_is_observed_not_tool_arguments(tmp_path):
    from apgr_workers.model_observation import codex_session
    from apgr_workers.codex_external import parse_codex_events
    thread = "12345678-1234-1234-1234-123456789abc"
    folder = tmp_path / "sessions/2026/09/26"
    folder.mkdir(parents=True)
    path = folder / f"rollout-{thread}.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in [
        {"type": "session_meta", "payload": {"id": thread}},
        {"type": "response_item", "payload": {"model": "fake-requested-model"}},
        {"type": "turn_context", "payload": {"model": "gpt-6-luna", "effort": "max"}},
    ]))
    observed = codex_session(thread, tmp_path)
    assert observed["effective_model"] == "gpt-6-luna"
    assert observed["effective_effort"] == "max"
    assert observed["source"] == "codex_session_turn_context"
    parsed = parse_codex_events(json.dumps({"type": "item.completed", "item": {
        "type": "collab_tool_call", "tool": "spawn_agent", "model": "gpt-6-luna"}}))
    assert parsed["effective_model"] is None
    path.write_text(json.dumps({"type": "session_meta", "payload": {"id": "foreign"}}))
    assert codex_session(thread, tmp_path)["effective_model"] is None


def test_legacy_environment_never_reaches_provider(monkeypatch):
    monkeypatch.setenv("AGENT_CENTRAL_PARENT_ID", "foreign-parent")
    options, read_fd, write_fd = process_options(["provider"], None, None,
                                                managed=False, activity_key="unused")
    assert not any(key.startswith("AGENT_CENTRAL_") for key in options["env"])
    assert read_fd is write_fd is None


@pytest.mark.parametrize("phase", ["implementation_testing", "architecture_docs", "sysadmin"])
def test_required_five_stage_route_and_pools(phase, tmp_path, monkeypatch):
    monkeypatch.setenv("APGR_HOME", str(tmp_path / "home"))
    result = resolve(PhaseRequest(phase, "gemini_sub", "Inspect nonce fixture."), ROOT,
                     finalization_policy="checkpoint")
    for stage, record in result["stages"].items():
        claude = stage in {"plan", "plan_review", "final_review"}
        assert record["intelligence"]["model"] == ("claude-opus-5-5" if claude else "gpt-6.1-sol")
        assert record["intelligence"]["effort"] == ("high" if claude else "xhigh")
        cap = record["worker_capability"]
        assert cap["allowed"], cap
        assert cap["requirement"] == "required"
        assert cap["limits"]["max_gemini"] == cap["limits"]["max_luna"] == 4
        assert cap["luna_worker"]["model"] == "gpt-6-luna"
        assert cap["luna_worker"]["effort"] == "max"
        assert cap["luna_worker"]["transport"] == ("codex_external" if claude else "codex_native")


def test_prose_and_spawn_request_are_not_effective_model_evidence():
    raw = json.dumps({"type": "item.completed", "item": {
        "type": "agent_message", "text": "model gpt-6-luna effort max"}}).encode()
    assert parent_observation(raw)["model"] is None
    assert native_admissions(raw) == []
    spawn = json.dumps({"type": "item.completed", "item": {
        "type": "collab_tool_call", "tool": "spawn_agent", "model": "gpt-6-luna",
        "receiver_thread_ids": ["leaf"], "status": "completed"}}).encode()
    assert native_admissions(spawn)[0]["effective_model"] is None


def test_native_session_receipt_is_admission_not_effective_model(tmp_path, monkeypatch):
    from apgr_workers.model_observation import codex_session
    thread = "12345678-1234-1234-1234-123456789abc"
    folder = tmp_path / "sessions/2026/09/26"
    folder.mkdir(parents=True)
    rows = [
        {"type": "session_meta", "payload": {"id": thread}},
        {"type": "turn_context", "payload": {"model": "gpt-6.1-sol", "effort": "medium"}},
        {"type": "response_item", "payload": {"type": "function_call", "name": "spawn_agent",
            "call_id": "call-one", "arguments": json.dumps({"model": "gpt-6-luna", "reasoning_effort": "max"})}},
        {"type": "response_item", "payload": {"type": "function_call_output", "call_id": "call-one",
            "output": json.dumps({"task_name": "/root/leaf"})}},
    ]
    (folder / ("rollout-" + thread + ".jsonl")).write_text("\n".join(map(json.dumps, rows)))
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    raw = json.dumps({"type": "thread.started", "thread_id": thread}).encode()
    admission = native_admissions(raw)[0]
    assert admission["status"] == "admitted"
    assert admission["requested"]["model"] == "gpt-6-luna"
    assert admission["effective_model"] is None
    assert codex_session(thread)["effective_model"] == "gpt-6.1-sol"
