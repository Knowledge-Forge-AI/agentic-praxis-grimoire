"""Metadata-only historical joins and truthful terminal layer labels."""
import hashlib
import json

import pytest

from apgr_workers.model_observation import claude_session, gemini_terminal_layers
from agent_phase.worker_evidence import parent_observation

SESSION = "00000000-1111-2222-3333-444444444444"


def record(**values):
    return {"type": "assistant", "sessionId": SESSION, "isSidechain": False,
            "message": {"model": "claude-opus-5-5", "content": "private transcript"},
            "effort": "high", "perTurnEffort": "high", **values}


def transcript(home, records, project="project"):
    path = home / "projects" / project / f"{SESSION}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n")
    return path


def test_claude_exact_join_and_config_home(tmp_path, monkeypatch):
    path = transcript(tmp_path, [record(), record(isSidechain=True, effort="low")])
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    raw = json.dumps({"type": "system", "subtype": "init", "session_id": SESSION,
                      "model": "claude-opus-5-5"}).encode()
    result = parent_observation(raw)
    assert result["effort"] == "high"
    assert result["model"] == "claude-opus-5-5"
    observation = result["session_observations"][0]
    assert observation["session_id"] == SESSION
    assert observation["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert observation["assistant_count"] == 1
    assert "private transcript" not in json.dumps(result)
    assert str(tmp_path) not in json.dumps(result)


@pytest.mark.parametrize("records", [
    [record(effort="low")],
    [record(), record(perTurnEffort="low", effort="low")],
    [record(effort=None, perTurnEffort=None)],
    [{k: v for k, v in record().items() if k not in {"effort", "perTurnEffort"}}],
])
def test_missing_or_conflicting_effort_stays_unknown(tmp_path, records):
    transcript(tmp_path, records)
    result = claude_session(SESSION, tmp_path)
    assert result["effective_effort"] is None
    assert result["limitation"] == "missing_or_conflicting_metadata"


def test_conflicting_models_stay_unknown(tmp_path):
    transcript(tmp_path, [record(), record(message={"model": "other"})])
    assert claude_session(SESSION, tmp_path)["effective_model"] is None


@pytest.mark.parametrize("kind", ["wrong_id", "missing_id", "malformed", "symlink", "ambiguous", "missing"])
def test_claude_invalid_session_is_not_observation(tmp_path, kind):
    path = transcript(tmp_path, [record()])
    if kind == "wrong_id":
        transcript(tmp_path, [record(sessionId="another")])
    elif kind == "missing_id":
        transcript(tmp_path, [{k: v for k, v in record().items() if k != "sessionId"}])
    elif kind == "malformed":
        path.write_text("not json\n")
    elif kind == "symlink":
        target = path.with_suffix(".saved")
        path.rename(target)
        path.symlink_to(target)
    elif kind == "ambiguous":
        transcript(tmp_path, [record()], project="other")
    else:
        path.unlink()
    result = claude_session(SESSION, tmp_path)
    assert result["effective_model"] is None
    assert result["effective_effort"] is None


def test_multiple_stream_ids_do_not_pick_a_session(tmp_path, monkeypatch):
    transcript(tmp_path, [record()])
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    raw = "\n".join(json.dumps({"type": "system", "subtype": "init", "session_id": sid})
                    for sid in [SESSION, "00000000-1111-2222-3333-555555555555"]).encode()
    result = parent_observation(raw)
    assert result["session_observations"] == []
    assert result["effort"] is None


def test_stream_session_conflict_is_not_silently_overridden(tmp_path, monkeypatch):
    transcript(tmp_path, [record()])
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    raw = json.dumps({"type": "system", "subtype": "init", "session_id": SESSION,
                      "model": "other", "effort": "low"}).encode()
    result = parent_observation(raw)
    assert result["model"] is None
    assert result["effort"] is None


def test_session_internal_conflict_is_not_hidden_by_stream(tmp_path, monkeypatch):
    transcript(tmp_path, [record(), record(effort="low", perTurnEffort="low")])
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    raw = json.dumps({"type": "system", "subtype": "init", "session_id": SESSION,
                      "effort": "high"}).encode()
    assert parent_observation(raw)["effort"] is None


def test_incomplete_session_consensus_is_not_promoted(tmp_path, monkeypatch):
    transcript(tmp_path, [record(), record(effort=None, perTurnEffort=None)])
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    raw = json.dumps({"type": "system", "subtype": "init", "session_id": SESSION}).encode()
    assert parent_observation(raw)["effort"] is None


def test_fence_delivery_is_separate_from_provider_interruption():
    summary = {"raw_status": "ERROR", "reason_fields": {"error": {"text": "interrupted"}},
               "child_exited_naturally": False, "completion_fence_observed": True,
               "completion_fence_sequence": 14, "terminal_result_sequence": 15,
               "completion_fence_monotonic": 1.0, "terminal_result_monotonic": 3.0,
               "wrapper_signal_events": [{"action": "SIGTERM", "monotonic": 2.0,
                                          "reason": "completion-fence-observed"}],
               "transport_success": True}
    result = gemini_terminal_layers(summary, "exited_success")
    assert result["wrapper_exit_status"] == "exited_success"
    assert result["provider_raw_status"] == "ERROR"
    assert result["provider_raw_error"] == "interrupted"
    assert result["provider_natural_exit"] is False
    assert result["completion_contract"] == "completion_fence"
    chronology = result["terminal_chronology"]
    assert chronology["completion_fence_monotonic"] < chronology["wrapper_signal_events"][0]["monotonic"] < chronology["terminal_result_monotonic"]


def test_missing_terminal_evidence_does_not_claim_natural_success():
    result = gemini_terminal_layers({}, "exited_success")
    assert result["provider_natural_exit"] is None
    assert result["provider_raw_status"] is None
    assert result["completion_contract"] is None
    assert gemini_terminal_layers({"child_exited_naturally": True,
                                   "terminal_result_observed": True}, "exited_success")["completion_contract"] == "natural_terminal_result"


def test_supervisor_retains_gemini_layers(tmp_path, monkeypatch):
    """The real result assembler consumes the existing wrapper evidence schema."""
    from apgr_workers.supervisor import run_supervisor

    class FakeProcess:
        pid = 99999
        returncode = 0
        stdin = stdout = stderr = None

        def __init__(self, *args, **kwargs):
            pass

        def poll(self):
            return 0

        def wait(self, timeout=None):
            return 0

        def communicate(self, input=None):
            return b"fixture delivery", b""

    monkeypatch.setattr("subprocess.Popen", FakeProcess)
    monkeypatch.setattr("os.getpgid", lambda pid: pid)
    monkeypatch.setattr("os.killpg", lambda *args: None)
    monkeypatch.setattr("apgr_workers.supervisor._call_ledger", lambda *args, **kwargs: True)
    out = tmp_path / "out"
    out.mkdir()
    task = tmp_path / "task.json"
    task.write_text(json.dumps({"workspace": str(tmp_path), "task_authority": "read_only",
                               "worker_kind": "gemini", "profile": "gemini-3.8-flash-high",
                               "acceptance_criteria": "fixture", "task": "fixture",
                               "output_dir": str(out)}))
    summary = {"process_group_cleanup": {"cleanup_complete": True},
               "version_probe_cleanup": {"cleanup_complete": True},
               "raw_status": "ERROR", "reason_fields": {"error": {"text": "interrupted"}},
               "child_exited_naturally": False, "completion_fence_observed": True,
               "completion_fence_sequence": 14, "terminal_result_sequence": 15,
               "transport_success": True}
    (out / "fixture.antigravity.antigravity-terminal-result.json").write_text(json.dumps(summary))
    run_supervisor(parent_id="fixture-parent", job_id="fixture", task_file=task,
                   state_dir=tmp_path / "state")
    result = json.loads((out / "fixture.result.json").read_text())
    assert result["provider_terminal_status"] == result["wrapper_exit_status"] == "exited_success"
    assert result["provider_raw_status"] == "ERROR"
    assert result["provider_raw_error"] == "interrupted"
    assert result["provider_natural_exit"] is False
    assert result["completion_contract"] == "completion_fence"
    assert result["effective_model"] is result["effective_effort"] is None
