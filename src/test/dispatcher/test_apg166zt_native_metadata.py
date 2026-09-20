"""Adversarial and provider-free verification for native Claude child metadata."""
import hashlib
import json
from pathlib import Path

import pytest

from apgr_workers.model_observation import claude_native_child_session

PARENT_SESSION = "11111111-2222-4333-8444-555555555555"
CHILD_AGENT = "abcdef1234567890"


def test_two_supported_sources_conflicting_effort_is_unknown(tmp_path):
    create_subagent_transcript(tmp_path, [child_record()])
    create_parent_transcript(tmp_path, [child_record(effort="low", perTurnEffort="low")])
    result = claude_native_child_session(PARENT_SESSION, CHILD_AGENT, home=tmp_path)
    assert result["effective_effort"] is None
    assert result["observed_efforts"] == ["high", "low"]


def test_fallback_cannot_discard_mismatched_session_for_matching_child(tmp_path):
    create_parent_transcript(tmp_path, [child_record(), child_record(sessionId="wrong")])
    result = claude_native_child_session(PARENT_SESSION, CHILD_AGENT, home=tmp_path)
    assert result["effective_model"] is None
    assert result["effective_effort"] is None


def test_two_supported_sources_agree(tmp_path):
    create_subagent_transcript(tmp_path, [child_record()])
    create_parent_transcript(tmp_path, [child_record()])
    result = claude_native_child_session(PARENT_SESSION, CHILD_AGENT, home=tmp_path)
    assert result["effective_effort"] is None
    assert result["effort_semantics"] == "unestablished"
    assert result["effective_model"] == "claude-sonnet-5-5"


def child_record(**overrides):
    base = {
        "sessionId": PARENT_SESSION,
        "agentId": CHILD_AGENT,
        "isSidechain": True,
        "type": "assistant",
        "message": {
            "model": "claude-sonnet-5-5",
            "content": "CONFIDENTIAL_CHILD_CONTENT_12345",
        },
        "effort": "high",
        "perTurnEffort": "high",
        "uuid": "40da9b78-0497-49bf-a579-82c73f8ba170",
    }
    base.update(overrides)
    return base


def create_subagent_transcript(home: Path, records: list[dict], project: str = "test-project") -> Path:
    path = home / "projects" / project / PARENT_SESSION / "subagents" / f"agent-{CHILD_AGENT}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(json.dumps(r) for r in records) + "\n"
    path.write_text(content)
    return path


def create_parent_transcript(home: Path, records: list[dict], project: str = "test-project") -> Path:
    path = home / "projects" / project / f"{PARENT_SESSION}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(json.dumps(r) for r in records) + "\n"
    path.write_text(content)
    return path


def test_matching_native_child_subagent_file(tmp_path):
    user_turn = {
        "sessionId": PARENT_SESSION,
        "agentId": CHILD_AGENT,
        "isSidechain": True,
        "type": "user",
        "message": {"role": "user", "content": "SECRET_USER_PROMPT_XYZ"},
    }
    rec1 = child_record()
    rec2 = child_record(uuid="0ed84ebf-9d3a-41ac-af86-344be73cb0b1")
    path = create_subagent_transcript(tmp_path, [user_turn, rec1, rec2])

    result = claude_native_child_session(PARENT_SESSION, CHILD_AGENT, home=tmp_path)

    assert result["parent_session_id"] == PARENT_SESSION
    assert result["child_agent_id"] == CHILD_AGENT
    assert result["effective_model"] == "claude-sonnet-5-5"
    assert result["effective_effort"] is None
    assert result["effort_observation_status"] == "single_value"
    assert result["limitation"] is None
    assert result["source"] == "claude_native_child_session_metadata"
    assert result["scope"] == "provider runtime native child configuration"
    assert result["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert result["size_bytes"] == len(path.read_bytes())
    assert result["record_count"] == 3
    assert result["assistant_count"] == 2
    assert result["observed_models"] == ["claude-sonnet-5-5"]
    assert result["observed_efforts"] == ["high"]


def test_matching_correlated_sidechain_fallback(tmp_path):
    parent_turn = {
        "sessionId": PARENT_SESSION,
        "isSidechain": False,
        "type": "assistant",
        "message": {"model": "claude-opus-5-5", "content": "parent transcript"},
        "effort": "high",
        "perTurnEffort": "high",
    }
    child_turn = child_record()
    path = create_parent_transcript(tmp_path, [parent_turn, child_turn])

    result = claude_native_child_session(PARENT_SESSION, CHILD_AGENT, home=tmp_path)

    assert result["parent_session_id"] == PARENT_SESSION
    assert result["child_agent_id"] == CHILD_AGENT
    assert result["effective_model"] == "claude-sonnet-5-5"
    assert result["effective_effort"] is None
    assert result["effort_semantics"] == "unestablished"
    assert result["limitation"] is None
    assert result["source"] == "claude_sidechain_assistant_metadata"
    assert result["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert result["size_bytes"] == len(path.read_bytes())
    assert result["record_count"] == 1
    assert result["assistant_count"] == 1
    assert result["observed_models"] == ["claude-sonnet-5-5"]
    assert result["observed_efforts"] == ["high"]


@pytest.mark.parametrize("invalid_parent", [
    "not-a-uuid",
    "0064f8d8-16db-4b9a-a741",
    "0064F8D8-16DB-4B9A-A741-ECCDA91B351E",
    "",
    12345,
    None,
])
def test_invalid_parent_uuid_rejected(tmp_path, invalid_parent):
    create_subagent_transcript(tmp_path, [child_record()])
    result = claude_native_child_session(invalid_parent, CHILD_AGENT, home=tmp_path)
    assert result["effective_model"] is None
    assert result["effective_effort"] is None
    assert result["limitation"] == "invalid_session_id"


@pytest.mark.parametrize("invalid_child", [
    "toolu_014D7ULk2E2KsWerjnYuSsEu",
    "agent-12345",
    "aaa8e6dc6e58298df!",
    "abc",
    "",
    12345,
    None,
])
def test_invalid_child_hex_id_rejected(tmp_path, invalid_child):
    create_subagent_transcript(tmp_path, [child_record()])
    result = claude_native_child_session(PARENT_SESSION, invalid_child, home=tmp_path)
    assert result["effective_model"] is None
    assert result["effective_effort"] is None
    assert result["limitation"] == "invalid_child_agent_id"


def test_absent_session_returns_none(tmp_path):
    result = claude_native_child_session(PARENT_SESSION, CHILD_AGENT, home=tmp_path)
    assert result["effective_model"] is None
    assert result["effective_effort"] is None
    assert result["limitation"] == "missing_or_ambiguous_session"


def test_fallback_with_child_absent_in_parent(tmp_path):
    parent_turn = {
        "sessionId": PARENT_SESSION,
        "isSidechain": False,
        "type": "assistant",
        "message": {"model": "claude-opus-5-5"},
        "effort": "high",
    }
    other_child_turn = child_record(agentId="bbb8e6dc6e58298df")
    create_parent_transcript(tmp_path, [parent_turn, other_child_turn])

    result = claude_native_child_session(PARENT_SESSION, CHILD_AGENT, home=tmp_path)
    assert result["effective_model"] is None
    assert result["effective_effort"] is None
    assert result["limitation"] == "missing_or_ambiguous_session"


def test_ambiguous_subagent_files_returns_none(tmp_path):
    create_subagent_transcript(tmp_path, [child_record()], project="project-one")
    create_subagent_transcript(tmp_path, [child_record()], project="project-two")

    result = claude_native_child_session(PARENT_SESSION, CHILD_AGENT, home=tmp_path)
    assert result["effective_model"] is None
    assert result["effective_effort"] is None
    assert result["limitation"] == "missing_or_ambiguous_session"


def test_symlinked_session_file_rejected(tmp_path):
    real_path = tmp_path / "actual.jsonl"
    real_path.write_text(json.dumps(child_record()) + "\n")
    subagent_path = tmp_path / "projects" / "test-project" / PARENT_SESSION / "subagents" / f"agent-{CHILD_AGENT}.jsonl"
    subagent_path.parent.mkdir(parents=True, exist_ok=True)
    subagent_path.symlink_to(real_path)

    result = claude_native_child_session(PARENT_SESSION, CHILD_AGENT, home=tmp_path)
    assert result["effective_model"] is None
    assert result["effective_effort"] is None
    assert result["limitation"] == "unreadable_unstable_or_invalid_session"


def test_symlinked_subagents_directory_rejected(tmp_path):
    real_dir = tmp_path / "actual_dir"
    real_dir.mkdir(parents=True, exist_ok=True)
    (real_dir / f"agent-{CHILD_AGENT}.jsonl").write_text(json.dumps(child_record()) + "\n")

    parent_dir = tmp_path / "projects" / "test-project" / PARENT_SESSION
    parent_dir.mkdir(parents=True, exist_ok=True)
    (parent_dir / "subagents").symlink_to(real_dir)

    result = claude_native_child_session(PARENT_SESSION, CHILD_AGENT, home=tmp_path)
    assert result["effective_model"] is None
    assert result["effective_effort"] is None
    assert result["limitation"] == "unreadable_unstable_or_invalid_session"


@pytest.mark.parametrize("mismatch_override", [
    {"sessionId": "11111111-2222-3333-4444-555555555555"},
    {"agentId": "bbb8e6dc6e58298df"},
    {"isSidechain": False},
])
def test_subagent_record_mismatch_rejected(tmp_path, mismatch_override):
    record = child_record(**mismatch_override)
    create_subagent_transcript(tmp_path, [record])

    result = claude_native_child_session(PARENT_SESSION, CHILD_AGENT, home=tmp_path)
    assert result["effective_model"] is None
    assert result["effective_effort"] is None
    assert result["limitation"] == "unreadable_unstable_or_invalid_session"


def test_conflicting_models_yield_none(tmp_path):
    rec1 = child_record(message={"model": "claude-sonnet-5-5"})
    rec2 = child_record(message={"model": "claude-opus-5-5"})
    create_subagent_transcript(tmp_path, [rec1, rec2])

    result = claude_native_child_session(PARENT_SESSION, CHILD_AGENT, home=tmp_path)
    assert result["effective_model"] is None
    assert result["effective_effort"] is None
    assert result["limitation"] == "missing_or_conflicting_metadata"


def test_conflicting_efforts_yield_none(tmp_path):
    rec1 = child_record(effort="high", perTurnEffort="high")
    rec2 = child_record(effort="low", perTurnEffort="low")
    create_subagent_transcript(tmp_path, [rec1, rec2])

    result = claude_native_child_session(PARENT_SESSION, CHILD_AGENT, home=tmp_path)
    assert result["effective_model"] == "claude-sonnet-5-5"
    assert result["effective_effort"] is None
    assert result["limitation"] is None
    assert result["effort_observation_status"] == "multiple_values"


@pytest.mark.parametrize("bad_effort", [
    {"effort": None, "perTurnEffort": None},
    {"effort": "", "perTurnEffort": ""},
    {},
])
def test_no_configured_or_parent_effort_fallback(tmp_path, bad_effort):
    rec = child_record()
    for k in ("effort", "perTurnEffort"):
        rec.pop(k, None)
    rec.update(bad_effort)

    parent_rec = {
        "sessionId": PARENT_SESSION,
        "isSidechain": False,
        "type": "assistant",
        "message": {"model": "claude-opus-5-5"},
        "effort": "high",
        "perTurnEffort": "high",
    }
    create_parent_transcript(tmp_path, [parent_rec])
    create_subagent_transcript(tmp_path, [rec])

    result = claude_native_child_session(PARENT_SESSION, CHILD_AGENT, home=tmp_path)
    assert result["effective_model"] == "claude-sonnet-5-5"
    assert result["effective_effort"] is None
    assert result["limitation"] is None
    assert result["effort_observation_status"] == "absent"


def test_no_content_exported(tmp_path):
    secret_marker_1 = "SECRET_TASK_INSTRUCTION_NONCE_998877"
    secret_marker_2 = "CONFIDENTIAL_PRIVATE_ASSISTANT_REPLY"
    secret_marker_3 = "/path/to/private/operator/workspace"
    records = [
        {
            "sessionId": PARENT_SESSION,
            "agentId": CHILD_AGENT,
            "isSidechain": True,
            "type": "user",
            "message": {"role": "user", "content": secret_marker_1},
        },
        {
            "sessionId": PARENT_SESSION,
            "agentId": CHILD_AGENT,
            "isSidechain": True,
            "type": "assistant",
            "message": {"model": "claude-sonnet-5-5", "content": secret_marker_2},
            "effort": "high",
            "perTurnEffort": "high",
            "cwd": secret_marker_3,
        },
    ]
    create_subagent_transcript(tmp_path, records)

    result = claude_native_child_session(PARENT_SESSION, CHILD_AGENT, home=tmp_path)
    serialized = json.dumps(result)

    assert secret_marker_1 not in serialized
    assert secret_marker_2 not in serialized
    assert secret_marker_3 not in serialized

    allowed_keys = {
        "parent_session_id",
        "child_agent_id",
        "session_id",
        "agent_id",
        "effective_model",
        "effective_effort",
        "source",
        "scope",
        "sha256",
        "size_bytes",
        "record_count",
        "assistant_count",
        "event_types",
        "observed_models",
        "observed_efforts",
        "limitation",
        "effort_semantics",
        "effort_observation_status",
    }
    assert set(result.keys()).issubset(allowed_keys)
