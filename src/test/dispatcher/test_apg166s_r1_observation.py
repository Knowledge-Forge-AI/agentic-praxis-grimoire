"""Provider-free real-shape and negative tests for APG166S-R1 R2 observation."""
import hashlib
import json
from pathlib import Path
import pytest

from apgr_workers.model_observation import codex_session
from agent_phase.worker_evidence import parent_observation, native_admissions
from apgr_workers.supervisor import run_supervisor


PARENT_THREAD = "01a0e03f-fdbd-72b3-834e-d2bdfadd02a3"
CHILD_THREAD = "01a0e040-2ed7-7a73-8b9c-028a1d843191"
CHILD_THREAD_2 = "01a0e040-93f1-7560-bff7-1280378e4028"


def _make_parent_session(
    folder: Path,
    thread_id: str = PARENT_THREAD,
    task_name: str = "/root/nonce_leaf",
    call_id: str = "call_lpQ4e5WYo5do76hHqZYFAdLi",
    requested_task_name: str = "nonce_leaf",
) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"rollout-2026-09-26T20-24-45-{thread_id}.jsonl"
    rows = [
        {"timestamp": "2026-09-27T00:24:45.000Z", "type": "session_meta", "payload": {"id": thread_id}},
        {"timestamp": "2026-09-27T00:24:46.000Z", "type": "turn_context", "payload": {
            "model": "gpt-6-astra", "effort": "medium"
        }},
        {"timestamp": "2026-09-27T00:24:57.000Z", "type": "response_item", "payload": {
            "type": "function_call", "id": "fc_001", "name": "spawn_agent",
            "call_id": call_id,
            "arguments": json.dumps({"model": "gpt-6-luna", "reasoning_effort": "max", "task_name": requested_task_name})
        }},
        {"timestamp": "2026-09-27T00:24:57.100Z", "type": "response_item", "payload": {
            "type": "function_call_output", "call_id": call_id,
            "output": json.dumps({"task_name": task_name})
        }},
        {"timestamp": "2026-09-27T00:25:22.000Z", "type": "event_msg", "payload": {
            "type": "task_complete", "duration_ms": 36944
        }}
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return path


def _make_child_session(
    folder: Path,
    child_id: str = CHILD_THREAD,
    parent_id: str = PARENT_THREAD,
    agent_path: str = "/root/nonce_leaf",
    model: str = "gpt-6-luna",
    effort: str = "max",
    terminal_event: str = "task_complete",
    corrupt_trailing: bool = False,
) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"rollout-2026-09-26T20-24-57-{child_id}.jsonl"
    rows = [
        {
            "timestamp": "2026-09-27T00:24:57.818Z",
            "type": "session_meta",
            "payload": {
                "id": child_id,
                "parent_thread_id": parent_id,
                "source": {
                    "subagent": {
                        "thread_spawn": {
                            "parent_thread_id": parent_id,
                            "depth": 1,
                            "agent_path": agent_path,
                            "agent_nickname": "Hume",
                            "agent_role": "default"
                        }
                    }
                }
            }
        },
        {
            "timestamp": "2026-09-27T00:24:58.711Z",
            "type": "turn_context",
            "payload": {
                "model": model,
                "effort": effort,
                "collaboration_mode": {
                    "settings": {
                        "model": model,
                        "reasoning_effort": effort
                    }
                }
            }
        },
        {
            "timestamp": "2026-09-27T00:25:19.203Z",
            "type": "event_msg",
            "payload": {
                "type": terminal_event,
                "last_agent_message": "child finished"
            }
        }
    ]
    content = "\n".join(json.dumps(r) for r in rows) + "\n"
    if corrupt_trailing:
        content += "NOT_VALID_JSON_AT_ALL\n"
    path.write_text(content, encoding="utf-8")
    return path


def test_child_resolution_unique_exact_match(tmp_path):
    """Retained shape: exact parent_thread_id + agent_path resolves unique child session."""
    session_dir = tmp_path / "sessions/2026/09/26"
    _make_parent_session(session_dir)
    child_path = _make_child_session(session_dir)
    child_bytes = child_path.read_bytes()
    expected_sha256 = hashlib.sha256(child_bytes).hexdigest()

    result = codex_session(PARENT_THREAD, home=tmp_path)
    assert result["effective_model"] == "gpt-6-astra"
    assert result["effective_effort"] == "medium"
    assert result["terminal_status"] == "completed"

    admissions = result["native_admissions"]
    assert len(admissions) == 1
    adm = admissions[0]
    assert adm["status"] == "admitted"
    assert adm["task_name"] == "/root/nonce_leaf"
    assert adm["receiver_thread_ids"] == [CHILD_THREAD]
    assert adm["effective_model"] == "gpt-6-luna"
    assert adm["effective_effort"] == "max"
    assert adm["terminal_status"] == "completed"
    assert adm["diagnostic"] is None
    assert adm["child_sha256"] == expected_sha256
    # Never retain raw child transcript
    assert "child_raw" not in adm
    assert "transcript" not in adm
    assert "last_agent_message" not in adm


def test_child_resolution_completed_vs_deleted_distinct(tmp_path):
    """Terminal status distinguishes completed vs deleted."""
    session_dir = tmp_path / "sessions/2026/09/26"
    _make_parent_session(session_dir)
    _make_child_session(session_dir, terminal_event="task_deleted")

    result = codex_session(PARENT_THREAD, home=tmp_path)
    adm = result["native_admissions"][0]
    assert adm["terminal_status"] == "deleted"
    assert adm["effective_model"] == "gpt-6-luna"
    assert adm["effective_effort"] == "max"


def test_child_resolution_ambiguous_sessions_fail_closed(tmp_path):
    """Multiple matching child sessions must remain unknown / fail-closed."""
    session_dir = tmp_path / "sessions/2026/09/26"
    _make_parent_session(session_dir)
    _make_child_session(session_dir, child_id=CHILD_THREAD)
    _make_child_session(session_dir, child_id=CHILD_THREAD_2)

    result = codex_session(PARENT_THREAD, home=tmp_path)
    adm = result["native_admissions"][0]
    assert adm["receiver_thread_ids"] == []
    assert adm["effective_model"] is None
    assert adm["effective_effort"] is None
    assert adm["terminal_status"] == "unknown"
    assert adm["diagnostic"] == "ambiguous child session metadata: multiple matching sessions"


def test_child_resolution_no_match_truthful_unknown(tmp_path):
    """Missing child session preserves truthful unknowns with no manufactured receiver IDs."""
    session_dir = tmp_path / "sessions/2026/09/26"
    _make_parent_session(session_dir)
    # No child session created

    result = codex_session(PARENT_THREAD, home=tmp_path)
    adm = result["native_admissions"][0]
    assert adm["receiver_thread_ids"] == []
    assert adm["effective_model"] is None
    assert adm["effective_effort"] is None
    assert adm["terminal_status"] == "unknown"
    assert adm["diagnostic"] == "native child runtime model metadata unavailable"


def test_date_scoped_search_only_reads_metadata_lines_unrelated(tmp_path):
    """Unrelated sessions only have their first metadata line read; corrupted later lines ignored."""
    session_dir = tmp_path / "sessions/2026/09/26"
    _make_parent_session(session_dir)
    _make_child_session(session_dir)

    # Add unrelated session with broken content after line 1
    unrelated_id = "01a0e053-1c47-71b0-9e74-06393e0f85af"
    unrelated_path = session_dir / f"rollout-2026-09-26T20-45-38-{unrelated_id}.jsonl"
    unrelated_path.write_text(
        json.dumps({"type": "session_meta", "payload": {"id": unrelated_id, "parent_thread_id": None}}) + "\n"
        + "GARBAGE NOT JSON TRUNCATED\n"
        + "MORE GARBAGE\n",
        encoding="utf-8"
    )

    result = codex_session(PARENT_THREAD, home=tmp_path)
    adm = result["native_admissions"][0]
    assert adm["receiver_thread_ids"] == [CHILD_THREAD]
    assert adm["effective_model"] == "gpt-6-luna"


def test_child_conflicting_turn_context_no_consensus(tmp_path):
    """Conflicting models or efforts in child turn_context fail-closed to None."""
    session_dir = tmp_path / "sessions/2026/09/26"
    _make_parent_session(session_dir)

    # Write child with two different models in turn_context
    child_path = session_dir / f"rollout-2026-09-26T20-24-57-{CHILD_THREAD}.jsonl"
    rows = [
        {
            "type": "session_meta",
            "payload": {
                "id": CHILD_THREAD,
                "parent_thread_id": PARENT_THREAD,
                "source": {"subagent": {"thread_spawn": {"agent_path": "/root/nonce_leaf"}}}
            }
        },
        {"type": "turn_context", "payload": {"model": "gpt-6-luna", "effort": "max"}},
        {"type": "turn_context", "payload": {"model": "gpt-6-other", "effort": "low"}},
        {"type": "event_msg", "payload": {"type": "task_complete"}}
    ]
    child_path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    result = codex_session(PARENT_THREAD, home=tmp_path)
    adm = result["native_admissions"][0]
    assert adm["effective_model"] is None
    assert adm["effective_effort"] is None
    assert adm["observed_models"] == ["gpt-6-luna", "gpt-6-other"]
    assert adm["observed_efforts"] == ["low", "max"]
    assert adm["diagnostic"] == "native child runtime model metadata unavailable"


def test_native_admissions_integration_with_child_resolution(tmp_path, monkeypatch):
    """worker_evidence.native_admissions receives enriched child evidence."""
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    session_dir = tmp_path / "sessions/2026/09/26"
    _make_parent_session(session_dir)
    _make_child_session(session_dir)

    raw_stdout = json.dumps({"type": "thread.started", "thread_id": PARENT_THREAD}).encode("utf-8")
    admissions = native_admissions(raw_stdout)
    assert len(admissions) == 1
    adm = admissions[0]
    assert adm["effective_model"] == "gpt-6-luna"
    assert adm["effective_effort"] == "max"
    assert adm["receiver_thread_ids"] == [CHILD_THREAD]
    assert adm["terminal_status"] == "completed"
    assert adm["child_sha256"] is not None


def test_parent_observation_inspects_result_usage_effort():
    """parent_observation inspects provider result/usage effort if genuine."""
    # Genuine turn.completed with usage reasoning_effort
    raw = json.dumps({
        "type": "turn.completed",
        "usage": {"effort": "high", "reasoning_effort": "high"}
    }).encode("utf-8")
    obs = parent_observation(raw)
    assert obs["effort"] == "high"

    # Genuine result event with usage dict
    raw2 = json.dumps({
        "type": "result",
        "subtype": "success",
        "usage": {"effort": "max"}
    }).encode("utf-8")
    obs2 = parent_observation(raw2)
    assert obs2["effort"] == "max"

    # Genuine result event with result dict
    raw3 = json.dumps({
        "type": "result",
        "result": {"effort": "medium", "model": "claude-opus-5-5"}
    }).encode("utf-8")
    obs3 = parent_observation(raw3)
    assert obs3["effort"] == "medium"
    assert obs3["model"] == "claude-opus-5-5"


def test_parent_observation_rejects_argv_prose_and_tool_args():
    """Prose, tool calls, and command execution argv are never observed."""
    raw = "\n".join([
        json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "model gpt-6-luna effort max"}}),
        json.dumps({"type": "item.started", "item": {"type": "command_execution", "command": "run -m gpt-6-luna --effort max"}}),
        json.dumps({"type": "item.completed", "item": {"type": "collab_tool_call", "tool": "spawn_agent", "model": "gpt-6-luna", "reasoning_effort": "max"}})
    ]).encode("utf-8")
    obs = parent_observation(raw)
    assert obs["model"] is None
    assert obs["effort"] is None
    assert obs["source"] == "effective_model_unobservable"


def test_supervisor_missing_profile_raises_explicit_error(tmp_path):
    """Supervisor rejects missing profile with explicit error instead of hardcoded fallback."""
    state_dir = tmp_path / "state"
    output_dir = tmp_path / "out"
    task_file = tmp_path / "task.json"
    task_payload = {
        "workspace": str(tmp_path),
        "task_authority": "read_only",
        "worker_kind": "gemini",
        "acceptance_criteria": "pass",
        "task": "do work",
        "output_dir": str(output_dir),
        # "profile" deliberately missing
    }
    task_file.write_text(json.dumps(task_payload), encoding="utf-8")

    exit_code = run_supervisor(
        parent_id="test-parent",
        job_id="test-job-missing-profile",
        task_file=task_file,
        state_dir=state_dir,
    )
    assert exit_code == 1
    # Check that supervisor did not fall back or run
    assert not (output_dir / "test-job-missing-profile.result.json").exists()


def test_supervisor_gemini_effective_fields_genuine_or_unknown(tmp_path, monkeypatch):
    """Gemini effective fields only populate from genuine provider terminal metadata, else unknown."""
    from apgr_workers.supervisor import run_supervisor

    # Mock Popen to simulate provider run
    class FakeProc:
        def __init__(self, *args, **kwargs):
            self.pid = 99999
            self.returncode = 0
            self.stdin = None
            self.stdout = None
            self.stderr = None
        def poll(self):
            return 0
        def wait(self, timeout=None):
            return 0
        def communicate(self, input=None):
            return (b"fake output\n", b"")

    monkeypatch.setattr("subprocess.Popen", FakeProc)
    monkeypatch.setattr("os.getpgid", lambda pid: pid)
    monkeypatch.setattr("os.killpg", lambda pgid, sig: None)
    monkeypatch.setattr("apgr_workers.supervisor._call_ledger", lambda *args, **kwargs: True)

    # 1. Without raw terminal metadata -> effective_model is None, source is not_observed
    state_dir = tmp_path / "state"
    output_dir = tmp_path / "out"
    output_dir.mkdir(parents=True, exist_ok=True)
    task_file = tmp_path / "task.json"
    task_payload = {
        "workspace": str(tmp_path),
        "task_authority": "read_only",
        "worker_kind": "gemini",
        "profile": "gemini-3.8-flash-high",
        "acceptance_criteria": "pass",
        "task": "do work",
        "output_dir": str(output_dir),
    }
    task_file.write_text(json.dumps(task_payload), encoding="utf-8")

    # Create dummy cleanup evidence summary without raw terminal model
    evidence_prefix = output_dir / "job1.antigravity"
    summary_path = output_dir / "job1.antigravity.antigravity-terminal-result.json"
    summary_path.write_text(json.dumps({
        "process_group_cleanup": {"cleanup_complete": True},
        "version_probe_cleanup": {"cleanup_complete": True},
        "raw_result_artifact": None,
    }), encoding="utf-8")

    run_supervisor(
        parent_id="test-parent",
        job_id="job1",
        task_file=task_file,
        state_dir=state_dir,
    )
    res_path = output_dir / "job1.result.json"
    assert res_path.exists()
    res = json.loads(res_path.read_text(encoding="utf-8"))
    assert res["effective_model"] is None
    assert res["effective_effort"] is None
    assert res["model_evidence"]["effective"]["source"] == "not_observed"
    assert res["model_evidence"]["match"] is None

    # 2. With genuine raw terminal result containing model and effort
    raw_path = output_dir / "job2.antigravity.antigravity-terminal-result.raw.json"
    raw_path.write_text(json.dumps({
        "type": "result",
        "result": {
            "model": "gemini-3.8-flash-high",
            "effort": "high"
        }
    }), encoding="utf-8")
    summary_path2 = output_dir / "job2.antigravity.antigravity-terminal-result.json"
    summary_path2.write_text(json.dumps({
        "process_group_cleanup": {"cleanup_complete": True},
        "version_probe_cleanup": {"cleanup_complete": True},
        "raw_result_artifact": raw_path.name,
        "raw_result_sha256": __import__("hashlib").sha256(raw_path.read_bytes()).hexdigest(),
    }), encoding="utf-8")

    run_supervisor(
        parent_id="test-parent",
        job_id="job2",
        task_file=task_file,
        state_dir=state_dir,
    )
    res_path2 = output_dir / "job2.result.json"
    assert res_path2.exists()
    res2 = json.loads(res_path2.read_text(encoding="utf-8"))
    assert res2["effective_model"] == "gemini-3.8-flash-high"
    assert res2["effective_effort"] == "high"
    assert res2["model_evidence"]["effective"]["source"] == "provider_terminal_metadata"


def test_child_nonce_bound_to_terminal_record_and_inactive(tmp_path):
    session_dir = tmp_path / "sessions/2026/09/26"
    _make_parent_session(session_dir)
    _make_child_session(session_dir)
    child_path = next(session_dir.glob("*" + CHILD_THREAD + ".jsonl"))
    rows = [json.loads(line) for line in child_path.read_text().splitlines()]
    for event in rows:
        if event.get("payload", {}).get("type") == "task_complete":
            event["payload"]["last_agent_message"] = "bound-nonce"
    child_path.write_text("\n".join(json.dumps(event) for event in rows) + "\n")
    result = codex_session(PARENT_THREAD, home=tmp_path, expected_nonce="bound-nonce")
    child = result["native_admissions"][0]["child_observation"]
    assert child["parent_thread_id"] == PARENT_THREAD
    assert child["nonce_returned"] is True
    assert child["active"] is False
    assert child["native_thread_removal"] == "not_observable"
    assert "bound-nonce" not in json.dumps(child)
    assert codex_session(PARENT_THREAD, home=tmp_path, expected_nonce="wrong")["native_admissions"][0]["child_observation"]["nonce_returned"] is False
