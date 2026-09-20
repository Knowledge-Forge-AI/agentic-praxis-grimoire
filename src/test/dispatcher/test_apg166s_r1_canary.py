"""Tests for APG166S-R1 canary harness, budget, runtime identity, and qualification."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from agent_phase import worker_canary
from agent_phase.canary_budget import (
    DEFAULT_PHASE,
    LEGACY_CASES,
    SONNET_CASES,
    SONNET_PHASE,
    BudgetExhaustedError,
    CanaryBudget,
    CanaryBudgetError,
    InFlightCanaryError,
    PredecessorCleanupError,
    UnchangedCauseError,
    canonical_budget_path,
)
from agent_phase.runtime_identity import (
    classify_path,
    runtime_identity,
)
from agent_phase.worker_canary import (
    _prompt,
    clean_environment,
    extract_stream_init,
    normalize_native_model_observation,
    qualify,
    run_case,
)

ROOT = Path(__file__).resolve().parents[3]
SONNET_IDENTITY = {"candidate_source_identity": "a" * 64, "controller_identity": "a" * 64,
                   "controller_unchanged": True}


@pytest.fixture(autouse=True)
def fixture_budget_process_identity(monkeypatch):
    # Budget tests exercise bookkeeping, not host process-identity capability.
    from types import SimpleNamespace

    from agent_phase import canary_budget
    real_run = canary_budget.subprocess.run
    def run(command, *args, **kwargs):
        if command[0] == "ps":
            return SimpleNamespace(returncode=0, stdout="fixture process start\n", stderr="")
        return real_run(command, *args, **kwargs)
    monkeypatch.setattr(canary_budget.subprocess, "run", run)


# ---------------------------------------------------------------------------
# Canonical Budget Tests
# ---------------------------------------------------------------------------

def test_canonical_budget_path_structure(tmp_path):
    expected = (
        tmp_path
        / "Documents"
        / "agent"
        / "outbox"
        / "agentic-praxis-grimoire_dev"
        / "APG166S-R1"
        / "canary-budget.json"
    )
    assert canonical_budget_path(home=tmp_path) == expected


def test_budget_atomic_flock_and_first_reservation(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    budget = CanaryBudget(home=tmp_path)
    res = budget.reserve("codex-luna", cause="initial_run")
    assert res["attempt"] == 1
    assert res["status"] == "reserved"
    assert res["cause"] == "initial_run"
    assert res["cleanup_proven"] is False

    # Verify file is written
    assert budget.path.is_file()
    data = json.loads(budget.path.read_text())
    assert data["schema"] == "apgr.canary-budget/v1"
    assert data["phase"] == "APG166S-R1"
    assert len(data["cases"]["codex-luna"]["attempts"]) == 1

    # Record terminal disposition
    updated = budget.record_disposition("codex-luna", 1, status="passed", cleanup_proven=True)
    assert updated["status"] == "passed"
    assert updated["cleanup_proven"] is True


def test_budget_refusal_duplicate_inflight(tmp_path):
    budget = CanaryBudget(home=tmp_path)
    budget.reserve("claude-gemini", cause="initial_run")

    # Current process pgid is alive, so duplicate reservation must raise InFlightCanaryError
    with pytest.raises(InFlightCanaryError, match="already has active in-flight attempt"):
        budget.reserve("claude-gemini", cause="duplicate_call")


def test_budget_interruption_consumes_and_reconciles_proven_dead(tmp_path):
    budget = CanaryBudget(home=tmp_path)
    # Seed budget with dead pgid (non-existent process group)
    dead_pgid = 99999999
    budget.path.parent.mkdir(parents=True, exist_ok=True)
    seed = {
        "schema": "apgr.canary-budget/v1",
        "phase": "APG166S-R1",
        "cases": {
            "claude-luna": {
                "attempts": [
                    {
                        "attempt": 1,
                        "status": "in_flight",
                        "pgid": dead_pgid,
                        "cause": "initial_run",
                        "cleanup_proven": False,
                    }
                ]
            }
        },
    }
    budget.path.write_text(json.dumps(seed, indent=2))

    # Next reserve call must reconcile the dead pgid attempt as interrupted (cleanup unproven)
    # Because predecessor attempt 1 cleanup is unproven, second attempt must be refused!
    with pytest.raises(PredecessorCleanupError, match="predecessor attempt 1 cleanup not proven"):
        budget.reserve("claude-luna", cause="second_attempt")

    # Verify attempt 1 was consumed as interrupted
    data = json.loads(budget.path.read_text())
    att1 = data["cases"]["claude-luna"]["attempts"][0]
    assert att1["status"] == "interrupted"
    assert att1["cleanup_proven"] is False


def test_budget_second_attempt_requirements(tmp_path):
    budget = CanaryBudget(home=tmp_path)
    budget.reserve("codex-gemini", cause="attempt_one_seed")
    # Mark attempt 1 as failed, but with cleanup proven
    budget.record_disposition("codex-gemini", 1, status="failed", cleanup_proven=True)

    # 1. Unchanged cause must be refused
    with pytest.raises(UnchangedCauseError, match="requires changed remediation cause"):
        budget.reserve("codex-gemini", cause="attempt_one_seed")

    with pytest.raises(UnchangedCauseError, match="requires changed remediation cause"):
        budget.reserve("codex-gemini", cause=None)

    # 2. Changed cause succeeds as attempt 2
    res2 = budget.reserve("codex-gemini", cause="remediated_mcp_tool_allowlist")
    assert res2["attempt"] == 2
    assert res2["cause"] == "remediated_mcp_tool_allowlist"

    # Mark attempt 2 terminal
    budget.record_disposition("codex-gemini", 2, status="passed", cleanup_proven=True)

    # 3. Third attempt must be refused by 2-per-case limit
    with pytest.raises(BudgetExhaustedError, match="budget exhausted"):
        budget.reserve("codex-gemini", cause="third_attempt")


# ---------------------------------------------------------------------------
# Runtime Identity & Path Classification Tests
# ---------------------------------------------------------------------------

def test_classify_path_explicit():
    assert classify_path("docs/specs/test.md") == "doc"
    assert classify_path("docs/evaluations/apg166s.md") == "doc"
    assert classify_path("AGENTS.md") == "doc"
    assert classify_path("README.md") == "doc"
    assert classify_path("bin/agent-worker") == "runtime"
    assert classify_path("bin/apgr-worker-canary") == "runtime"
    assert classify_path("libexec/agent_phase/worker_canary.py") == "runtime"
    assert classify_path("common/dispatcher/policy.toml") == "runtime"
    assert classify_path("codex/profiles/luna-worker.config.toml") == "runtime"
    assert classify_path("claude/settings.json") == "runtime"
    assert classify_path("src/agentic_praxis_grimoire/cli.py") == "runtime"
    assert classify_path("src/test/dispatcher/test_canary.py") == "test"
    assert classify_path("testing/h_eval/readiness.py") == "runtime"


def test_runtime_identity_doc_edits_do_not_invalidate(tmp_path):
    # Construct a minimal repo tree
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "agent-worker").write_text("#!/bin/sh\n")
    (tmp_path / "libexec").mkdir()
    (tmp_path / "libexec" / "core.py").write_text("X = 1\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text("# Guide\n")

    id1 = runtime_identity(tmp_path)

    # Edit doc path
    (tmp_path / "docs" / "guide.md").write_text("# Guide Updated\n")
    (tmp_path / "docs" / "new_record.md").write_text("# New\n")

    id2 = runtime_identity(tmp_path)
    assert id1 == id2, "Documentation change must NOT alter runtime identity"

    # Edit runtime file
    (tmp_path / "libexec" / "core.py").write_text("X = 2\n")
    id3 = runtime_identity(tmp_path)
    assert id1 != id3, "Runtime file change MUST alter runtime identity"


# ---------------------------------------------------------------------------
# Environment Sanitization Tests
# ---------------------------------------------------------------------------

def test_clean_environment_inherits_auth_and_removes_bootstrap(monkeypatch):
    monkeypatch.setenv("HOME", "/custom/home")
    monkeypatch.setenv("SECURITYSESSIONID", "test-session")
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "fake-token")
    monkeypatch.setenv("APGR_MODEL_AUTHORITY", "source-defaults")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-secret")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-secret")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-secret")
    monkeypatch.setenv("CODEX_HOME", "/custom/codex")
    monkeypatch.setenv("PATH", "/usr/bin:/bin")

    # Bootstrap & authority leak attempts
    monkeypatch.setenv("AGENT_CENTRAL_PARENT_ID", "parent-123")
    monkeypatch.setenv("AGENT_CENTRAL_AUTH", "auth-token")
    monkeypatch.setenv("APGR_DISPATCH_ROOT", "/forbidden/dispatch")
    monkeypatch.setenv("APGR_AUTHORITY_ROLE", "admin")
    monkeypatch.setenv("PARENT_ID", "p-999")
    monkeypatch.setenv("WORKER_ID", "w-888")

    clean = clean_environment(apgr_home=Path("/tmp/apgr_home"))

    # Auth and essentials retained
    assert clean["HOME"] == "/custom/home"
    assert clean["SECURITYSESSIONID"] == "test-session"
    assert clean["CLAUDE_CODE_OAUTH_TOKEN"] == "fake-token"
    assert "APGR_MODEL_AUTHORITY" not in clean
    assert clean["ANTHROPIC_API_KEY"] == "sk-ant-secret"
    assert clean["OPENAI_API_KEY"] == "sk-proj-secret"
    assert clean["GEMINI_API_KEY"] == "gemini-secret"
    assert clean["CODEX_HOME"] == "/custom/codex"
    assert clean["PATH"] == "/usr/bin:/bin"
    assert clean["APGR_HOME"] == str(Path("/tmp/apgr_home").resolve())
    assert clean["PYTHONDONTWRITEBYTECODE"] == "1"

    # Authority and bootstrap stripped
    assert "AGENT_CENTRAL_PARENT_ID" not in clean
    assert "AGENT_CENTRAL_AUTH" not in clean
    assert "APGR_DISPATCH_ROOT" not in clean
    assert "APGR_AUTHORITY_ROLE" not in clean
    assert "PARENT_ID" not in clean
    assert "WORKER_ID" not in clean


# ---------------------------------------------------------------------------
# Prompt Generation Tests (Selected Worker Choices)
# ---------------------------------------------------------------------------

def test_prompt_generation_integrates_selected_worker_choice(tmp_path):
    fixture = tmp_path / "nonce.txt"
    # Codex + Luna with custom worker choice
    custom_choice = {"model": "gpt-6-luna-v2", "effort": "high"}
    prompt = _prompt(fixture, "codex", "luna", worker_choice=custom_choice)
    assert "model gpt-6-luna-v2 and high effort" in prompt
    assert "gpt-6-luna and max effort" not in prompt


# ---------------------------------------------------------------------------
# Pure Qualify Tests (All Dimensions, Fail-Closed)
# ---------------------------------------------------------------------------

def _valid_record():
    return {
        "case": "claude-luna", "candidate_unchanged": True, "bundle_unchanged": True,
        "parent": {"provider": "claude", "model": "claude-opus-5-5", "effort": "high"},
        "parent_observed": {"provider": "claude", "model": "claude-opus-5-5", "effort": "high"},
        "worker": {"kind": "luna", "requested": {"model": "gpt-6-luna", "effort": "max"}},
        "capability": {"allowed": True, "borrowing": False, "limits": {"max_gemini": 4, "max_luna": 4}},
        "capacity_receipt": {"max_gemini": 4, "max_luna": 4, "borrowing": False},
        "parent_id": "parent", "admission": {"job": {}},
        "worker_results": [{"worker_kind": "luna", "effective_model": "gpt-6-luna", "effective_effort": "max", "transport": "codex_external", "parent_id": "parent", "job_id": "job", "status": "completed", "cleanup_proven": True, "response": "nonce"}],
        "nonce": "nonce", "nonce_returned": True, "stage_ok": True,
        "parent_cleanup": {"cleanup_proven": True},
        "stage_meta": {"worker_drain": {"status": "closed", "uncertain_cleanup": False}},
    }


def test_complete_bound_evidence_passes():
    assert qualify(_valid_record())["passed"]


@pytest.mark.parametrize("path,value", [
    (("authentication_failed",), True),
    (("capability", "allowed"), False),
    (("parent_observed", "effort"), None),
    (("parent_observed", "provider"), None),
    (("worker_results", 0, "effective_model"), None),
    (("worker_results", 0, "effective_effort"), None),
    (("worker_results", 0, "cleanup_proven"), None),
    (("worker_results", 0, "cleanup_proven"), False),
    (("worker_results", 0, "response"), "absent"),
    (("worker_results", 0, "parent_id"), None),
    (("worker_results", 0, "transport"), None),
    (("worker_results", 0, "status"), "admitted"),
    (("parent_cleanup", "cleanup_proven"), False),
    (("stage_meta", "worker_drain", "status"), None),
    (("nonce_returned",), False),
    (("candidate_unchanged",), False),
    (("bundle_unchanged",), False),
    (("capability", "borrowing"), True),
    (("capacity_receipt", "max_luna"), 3),
    (("stage_ok",), None),
])
def test_missing_required_dimension_never_passes(path, value):
    record = _valid_record()
    target = record
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    assert not qualify(record)["passed"]


def test_native_admission_and_parent_nonce_are_not_child_completion():
    record = _valid_record()
    record["case"] = "codex-luna"
    record["worker_results"] = []
    record["native_admission"] = [{"effective_model": "gpt-6-luna", "effective_effort": "max", "status": "admitted"}]
    result = qualify(record)
    assert not result["passed"]
    assert not result["dimensions"]["nonce_worker_and_parent"]
    assert not result["dimensions"]["proven_cleanup"]


def test_invalid_budget_does_not_reset(tmp_path):
    budget = CanaryBudget(home=tmp_path)
    budget.path.parent.mkdir(parents=True)
    budget.path.write_text('{"schema":"wrong","cases":{}}')
    with pytest.raises(CanaryBudgetError, match="refusing reset"):
        budget.reserve("codex-luna")


def test_budget_home_environment_cannot_reset(monkeypatch, tmp_path):
    before = canonical_budget_path()
    monkeypatch.setenv("HOME", str(tmp_path))
    assert canonical_budget_path() == before
    with pytest.raises(CanaryBudgetError):
        canonical_budget_path(phase="other")


def test_runtime_manifest_binds_non_python_policy_mode_and_guidance(tmp_path):
    for name in ["libexec/launch.sh", "common/workers/policy.json", "codex/AGENTS.md"]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("one")
        before = runtime_identity(tmp_path)
        path.write_text("two")
        assert runtime_identity(tmp_path) != before
        before = runtime_identity(tmp_path)
        path.chmod(0o700)
        assert runtime_identity(tmp_path) != before
        assert classify_path(name) == "runtime"


def test_run_case_budget_refusal_before_provider(tmp_path, monkeypatch):
    from test_apg166s_r1_home_path import _home_bundle
    home = _home_bundle(tmp_path)
    budget = CanaryBudget(home=tmp_path)
    budget.reserve("codex-luna")
    monkeypatch.setattr(worker_canary, "CanaryBudget", lambda **kwargs: budget)
    monkeypatch.setattr(worker_canary, "resolve_worker_capability", lambda *a, **k: {
        "allowed": True, "interface": "native", "allowed_worker_kinds": ["gemini", "sonnet"],
        "luna_worker": {"model": "fixture", "effort": "max", "transport": "codex_native"}})
    result = run_case(ROOT, home, tmp_path / "output", "codex-luna",
                      runner=lambda *a, **k: pytest.fail("provider invoked before budget refusal"))
    assert result["error_type"] == "InFlightCanaryError"


def test_parent_nonce_in_tool_arguments_is_not_returned():
    raw = json.dumps({"type": "item.completed", "item": {"type": "mcp_tool_call", "arguments": {"nonce": "secret-nonce"}}}).encode()
    assert not worker_canary.parent_nonce_returned(raw, "secret-nonce")
    raw = json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "secret-nonce"}}).encode()
    assert worker_canary.parent_nonce_returned(raw, "secret-nonce")


def test_bound_native_completion_is_distinct_from_removal():
    record = _valid_record()
    record["case"] = "codex-luna"
    record["parent"] = {"provider": "codex", "model": "gpt-6-astra", "effort": "medium"}
    record["parent_observed"] = {**record["parent"], "session_observations": [{"thread_id": "parent-thread"}]}
    child = {"thread_id": "child-thread", "parent_thread_id": "parent-thread", "source": "codex_session_turn_context", "nonce_returned": True, "terminal_status": "completed", "active": False, "native_thread_removal": "not_observable"}
    record["native_admission"] = [{"status": "admitted", "effective_model": "gpt-6-luna", "effective_effort": "max", "session_observations": [child]}]
    assert qualify(record)["passed"]
    child["active"] = None
    assert not qualify(record)["passed"]
    child["active"] = False
    child["parent_thread_id"] = "unrelated"
    assert not qualify(record)["passed"]


# ---------------------------------------------------------------------------
# Sonnet Budget Phase & Separation Tests
# ---------------------------------------------------------------------------

def test_sonnet_budget_phase_and_case_separation(tmp_path):
    expected = (
        tmp_path
        / "Documents"
        / "agent"
        / "outbox"
        / "agentic-praxis-grimoire_dev"
        / SONNET_PHASE
        / "canary-budget.json"
    )
    assert canonical_budget_path(home=tmp_path, phase=SONNET_PHASE) == expected

    legacy_budget = CanaryBudget(home=tmp_path, phase=DEFAULT_PHASE)
    for sonnet_case in SONNET_CASES:
        with pytest.raises(CanaryBudgetError, match="requires Sonnet budget phase"):
            legacy_budget.reserve(sonnet_case)

    sonnet_budget = CanaryBudget(home=tmp_path, phase=SONNET_PHASE)
    for legacy_case in LEGACY_CASES:
        with pytest.raises(CanaryBudgetError, match="requires legacy budget phase"):
            sonnet_budget.reserve(legacy_case)

    with pytest.raises(CanaryBudgetError, match="unknown canary case"):
        sonnet_budget.reserve("unknown-case")

    res = sonnet_budget.reserve("claude-sonnet-native", cause="initial_sonnet_run")
    assert res["attempt"] == 1
    assert res["status"] == "reserved"
    assert res["cause"] == "initial_sonnet_run"
    assert res["cleanup_proven"] is False

    with pytest.raises(InFlightCanaryError, match="already has active in-flight attempt"):
        sonnet_budget.reserve("claude-sonnet-native")

    sonnet_budget.record_disposition("claude-sonnet-native", 1, status="failed", cleanup_proven=True)

    with pytest.raises(UnchangedCauseError, match="requires changed remediation cause"):
        sonnet_budget.reserve("claude-sonnet-native", cause="initial_sonnet_run")

    res2 = sonnet_budget.reserve("claude-sonnet-native", cause="remediated_native_hook")
    assert res2["attempt"] == 2
    sonnet_budget.record_disposition("claude-sonnet-native", 2, status="passed", cleanup_proven=True)

    with pytest.raises(BudgetExhaustedError, match="budget exhausted"):
        sonnet_budget.reserve("claude-sonnet-native", cause="third_attempt")


# ---------------------------------------------------------------------------
# Stream Init & Model Observation Normalization Tests
# ---------------------------------------------------------------------------

def test_extract_stream_init_narrow_facts():
    raw_with_agent = (
        json.dumps({
            "type": "system",
            "subtype": "init",
            "model": "claude-opus-5-5",
            "claude_code_version": "2.1.281",
            "tools": ["Read", "Glob", "Grep", "Agent"],
            "permissionMode": "plan",
            "mcp_servers": ["some_private_server_data_that_should_not_be_archived"],
        }) + "\n"
    ).encode()
    obs = extract_stream_init(raw_with_agent)
    assert obs is not None
    assert obs["agent_tool_present"] is True
    assert obs["claude_code_version"] == "2.1.281"
    assert obs["model"] == "claude-opus-5-5"
    assert obs["tools"] == ["Agent", "Glob", "Grep", "Read"]
    assert "mcp_servers" not in obs
    assert "permissionMode" not in obs

    raw_without_agent = (
        json.dumps({
            "type": "system",
            "subtype": "init",
            "tools": ["Read", "Glob"],
            "version": "2.1.280",
        }) + "\n"
    ).encode()
    obs_no_agent = extract_stream_init(raw_without_agent)
    assert obs_no_agent is not None
    assert obs_no_agent["agent_tool_present"] is False
    assert obs_no_agent["claude_code_version"] == "2.1.280"

    raw_empty = json.dumps({"type": "result", "result": "ok"}).encode()
    assert extract_stream_init(raw_empty) is None


def test_normalize_native_model_observation_statuses():
    obs = normalize_native_model_observation(
        {"effective_model": "claude-sonnet-5-5", "effective_effort": "high"},
        "claude-sonnet-5-5",
        "high",
    )
    assert obs["model_status"] == "observed_match"
    assert obs["effort_status"] == "observed_match"
    assert obs["effective_model"] == "claude-sonnet-5-5"
    assert obs["effective_effort"] == "high"

    obs_no_effort = normalize_native_model_observation(
        {"effective_model": "claude-sonnet-5-5", "effective_effort": None},
        "claude-sonnet-5-5",
        "high",
    )
    assert obs_no_effort["model_status"] == "observed_match"
    assert obs_no_effort["effort_status"] == "unknown"
    assert obs_no_effort["effective_effort"] is None

    obs_no_model = normalize_native_model_observation(
        {"effective_model": None, "effective_effort": "high"},
        "claude-sonnet-5-5",
        "high",
    )
    assert obs_no_model["model_status"] == "unknown"
    assert obs_no_model["effort_status"] == "observed_match"

    obs_bad_model = normalize_native_model_observation(
        {"effective_model": "claude-opus-5-5", "effective_effort": "high"},
        "claude-sonnet-5-5",
        "high",
    )
    assert obs_bad_model["model_status"] == "mismatch"

    obs_bad_effort = normalize_native_model_observation(
        {"effective_model": "claude-sonnet-5-5", "effective_effort": "low"},
        "claude-sonnet-5-5",
        "high",
    )
    assert obs_bad_effort["effort_status"] == "mismatch"


# ---------------------------------------------------------------------------
# Prompt Generation for Sonnet Cases
# ---------------------------------------------------------------------------

def test_prompt_generation_sonnet_cases(tmp_path):
    fixture = tmp_path / "nonce.txt"
    worker_choice = {"model": "claude-sonnet-5-5", "effort": "high"}

    prompt_native = _prompt(fixture, "claude", "sonnet", worker_choice=worker_choice, case="claude-sonnet-native")
    assert "apgr-sonnet-leaf:apgr-sonnet-leaf" in prompt_native
    assert "run_in_background=false" in prompt_native
    assert "Use one leaf only" in prompt_native
    assert "Delegate exactly one read-only leaf task" in prompt_native

    prompt_reuse = _prompt(fixture, "claude", "sonnet", worker_choice=worker_choice, case="claude-sonnet-native-reuse")
    assert "apgr-sonnet-leaf:apgr-sonnet-leaf" in prompt_reuse
    assert "Delegate 5 sequential read-only leaf tasks" in prompt_reuse
    assert "5 sequential foreground leaf tasks one after another" in prompt_reuse

    prompt_codex = _prompt(fixture, "codex", "sonnet", worker_choice=worker_choice, case="codex-sonnet")
    assert "worker_kind=sonnet" in prompt_codex
    assert "agent_worker server submit tool" in prompt_codex

    prompt_gemini = _prompt(fixture, "antigravity", "sonnet", worker_choice=worker_choice,
                           case="gemini-sonnet", worker_entrypoint=ROOT / "bin/agent-worker")
    assert "--worker-kind sonnet" in prompt_gemini
    assert "job launch" in prompt_gemini
    assert "--outcome accepted" in prompt_gemini


# ---------------------------------------------------------------------------
# Claude Native Sonnet Qualification Tests
# ---------------------------------------------------------------------------

def _complete_native_coverage(leaves):
    ids = sorted(c["agent_id"] for c in leaves)
    return {"schema": "apgr.native-call-coverage/v1", "status": "complete",
            "parent_id": "parent-work-1",
            "parent_session_id": "11111111-2222-4333-8444-555555555555", "parent_session_bound": True,
            "ledger_ids": ids, "invocation_ids": ids, "result_ids": ids, "matched_ids": ids,
            "ledger_only": [], "tool_only": [], "duplicate_ids": [], "conflicting_provider_ids": [],
            "malformed_invocations": 0, "unmatched": []}


def _valid_claude_sonnet_native_record():
    record = {
        **SONNET_IDENTITY,
        "case": "claude-sonnet-native",
        "phase": "APG166ZQ",
        "candidate_unchanged": True,
        "bundle_unchanged": True,
        "parent": {"provider": "claude", "model": "claude-opus-5-5", "effort": "high"},
        "parent_observed": {"provider": "claude", "model": "claude-opus-5-5", "effort": "high"},
        "worker": {"kind": "sonnet", "requested": {"model": "claude-sonnet-5-5", "effort": "high"}},
        "capability": {
            "allowed": True,
            "borrowing": False,
            "policy_selection": "triple_pool_4x4x4",
            "limits": {"max_gemini": 4, "max_luna": 4, "max_sonnet": 4, "max_aggregate": 12},
        },
        "capacity_receipt": {"max_gemini": 4, "max_luna": 4, "max_sonnet": 4, "borrowing": False},
        "parent_id": "parent-work-1",
        "native_sonnet_count": 0,
        "stream_init": {
            "agent_tool_present": True,
            "tools": ["Agent", "Glob", "Grep", "Read"],
            "claude_code_version": "2.1.281",
        },
        "native_admission": [
            {
                "agent_id": "agent-tool-use-1",
                "agent_type": "apgr-sonnet-leaf",
                "parent_id": "parent-work-1",
                "status": "closed",
                "terminal_result": "completed",
                "model_observation": {
                    "effective_model": "claude-sonnet-5-5",
                    "effective_effort": "high",
                    "source": "provider Agent terminal response",
                },
                "effective_model": "claude-sonnet-5-5",
                "effective_effort": "high",
                "cleanup_proven": True,
                "nonce_returned": True,
                "transport": "claude_native",
                "tool_correlation": {"matched": True, "tool_use_id": "agent-tool-use-1",
                    "parent_session_id": "11111111-2222-4333-8444-555555555555",
                    "provider_agent_id": "abcdef1234567890"},
            }
        ],
        "nonce": "nonce-secret-token",
        "nonce_returned": True,
        "stage_ok": True,
        "parent_cleanup": {"cleanup_proven": True},
        "stage_meta": {"worker_drain": {"status": "closed", "uncertain_cleanup": False}},
    }
    record["native_unmatched"] = []
    record["native_call_coverage"] = _complete_native_coverage(record["native_admission"])
    return record


def test_claude_sonnet_native_qualification_passes():
    record = _valid_claude_sonnet_native_record()
    res = qualify(record)
    assert res["passed"] is True
    assert res["status"] == "passed"
    assert res["dimensions"]["transport"] is True
    assert res["dimensions"]["native_tool_invoked"] is True
    assert res["dimensions"]["admission_capacity"] is True
    assert res["dimensions"]["parent_child_binding"] is True
    assert res["dimensions"]["proven_cleanup"] is True


def test_claude_sonnet_native_missing_effort_is_partial_never_pass():
    record = _valid_claude_sonnet_native_record()
    record["native_admission"][0]["effective_effort"] = None
    record["native_admission"][0]["model_observation"]["effective_effort"] = None

    res = qualify(record)
    assert res["passed"] is False
    assert res["status"] == "partial"
    assert "worker_effort_unknown" in res["diagnostics"]["unknowns"]
    assert "worker_kind_model_effort" in res["reasons"]
    assert record["native_admission"][0]["terminal_result"] == "completed"
    assert record["native_admission"][0]["effort_status"] == "unknown"
    assert res["dimensions"]["terminal"] is True


def test_claude_sonnet_native_model_effort_mismatches_fail():
    record = _valid_claude_sonnet_native_record()
    record["native_admission"][0]["effective_model"] = "claude-opus-5-5"
    record["native_admission"][0]["model_observation"]["effective_model"] = "claude-opus-5-5"
    res = qualify(record)
    assert res["passed"] is False
    assert res["status"] == "partial"
    assert record["native_admission"][0]["model_status"] == "mismatch"

    record2 = _valid_claude_sonnet_native_record()
    record2["native_admission"][0]["effective_effort"] = "low"
    record2["native_admission"][0]["model_observation"]["effective_effort"] = "low"
    res2 = qualify(record2)
    assert res2["passed"] is False
    assert res2["status"] == "partial"
    assert record2["native_admission"][0]["effort_status"] == "mismatch"


def test_claude_sonnet_native_init_advertisement_is_informational():
    record = _valid_claude_sonnet_native_record()
    record["stream_init"] = {
        "agent_tool_present": False,
        "tools": ["Read", "Glob", "Grep"],
        "claude_code_version": "2.1.281",
    }
    res = qualify(record)
    assert res["passed"] is True
    assert res["dimensions"]["native_tool_invoked"] is True
    assert res["functional"]["tool_advertised"] is False


# ---------------------------------------------------------------------------
# Claude Native Sonnet Reuse (5 Sequential Foreground Leaves) Tests
# ---------------------------------------------------------------------------

def _valid_claude_sonnet_native_reuse_record():
    base = _valid_claude_sonnet_native_record()
    base["case"] = "claude-sonnet-native-reuse"
    leaves = []
    for i in range(5):
        leaves.append({
            "agent_id": f"agent-tool-{i}",
            "agent_type": "apgr-sonnet-leaf",
            "parent_id": "parent-work-1",
            "status": "closed",
            "terminal_result": "completed",
            "model_observation": {
                "effective_model": "claude-sonnet-5-5",
                "effective_effort": "high",
                "source": "provider Agent terminal response",
            },
            "effective_model": "claude-sonnet-5-5",
            "effective_effort": "high",
            "created_at": 100.0 + i * 10.0,
            "updated_at": 100.0 + i * 10.0 + 8.0,
            "cleanup_proven": True,
            "nonce_returned": True,
            "transport": "claude_native",
            "tool_correlation": {"matched": True, "tool_use_id": f"agent-tool-{i}",
                "parent_session_id": "11111111-2222-4333-8444-555555555555",
                "provider_agent_id": f"abcdef123456789{i}"},
        })
    base["native_admission"] = leaves
    base["native_call_coverage"] = _complete_native_coverage(leaves)
    return base


def test_claude_sonnet_native_reuse_5_sequential_leaves_passes():
    record = _valid_claude_sonnet_native_reuse_record()
    res = qualify(record)
    assert res["passed"] is True
    assert res["status"] == "passed"
    assert res["dimensions"]["sequential_non_overlap"] is True
    assert res["dimensions"]["admission_capacity"] is True


def test_claude_sonnet_native_reuse_overlapping_leaves_refused():
    record = _valid_claude_sonnet_native_reuse_record()
    record["native_admission"][1]["created_at"] = 105.0
    res = qualify(record)
    assert res["passed"] is False
    assert res["dimensions"]["sequential_non_overlap"] is False
    assert "sequential_non_overlap" in res["reasons"]


def test_claude_sonnet_native_reuse_fewer_leaves_refused():
    record = _valid_claude_sonnet_native_reuse_record()
    record["native_admission"] = record["native_admission"][:4]
    res = qualify(record)
    assert res["passed"] is False
    assert res["dimensions"]["admission_capacity"] is False


@pytest.mark.parametrize("mutation,dimension", [
    ("missing_invocation", "native_tool_invoked"),
    ("unsettled_slot", "native_pool_settled"),
    ("controller_mismatch", "source_controller_bound"),
    ("cleanup_unknown", "proven_cleanup"),
    ("closed_failure", "terminal"),
    ("live_completion", "terminal"),
])
def test_native_canary_never_infers_unobserved_contracts(mutation, dimension):
    record = _valid_claude_sonnet_native_record()
    child = record["native_admission"][0]
    if mutation == "missing_invocation":
        child.pop("tool_correlation")
    elif mutation == "unsettled_slot":
        record["native_sonnet_count"] = 1
    elif mutation == "controller_mismatch":
        record["controller_identity"] = "b" * 64
    elif mutation == "cleanup_unknown":
        child.pop("cleanup_proven")
    elif mutation == "closed_failure":
        child["terminal_result"] = "failed"
    elif mutation == "live_completion":
        child["status"] = "active"
    result = qualify(record)
    assert not result["passed"]
    assert not result["dimensions"][dimension]


@pytest.mark.parametrize("mutation", ["missing_start", "missing_end", "duplicate_identity"])
def test_native_reuse_requires_each_distinct_observed_interval(mutation):
    record = _valid_claude_sonnet_native_reuse_record()
    child = record["native_admission"][1]
    if mutation == "missing_start":
        child.pop("created_at")
    elif mutation == "missing_end":
        child.pop("updated_at")
    else:
        child["agent_id"] = record["native_admission"][0]["agent_id"]
    result = qualify(record)
    assert not result["passed"]
    assert not result["dimensions"]["sequential_non_overlap"]


def test_native_nonce_requires_correlated_child_result():
    nonce = "fixture-child-nonce"
    raw = b'\n'.join(json.dumps(event).encode() for event in [
        {"type": "assistant", "session_id": "fixture-parent", "message": {"content": [
            {"type": "text", "text": nonce},
            {"type": "tool_use", "name": "Agent", "id": "call-1", "input": {
                "subagent_type": "apgr-sonnet-leaf:apgr-sonnet-leaf", "run_in_background": False}},
        ]}},
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "other-call", "content": nonce},
        ]}},
    ])
    assert not worker_canary.native_nonce_returns(raw, nonce).get("call-1", False)
    result = {"type": "user", "tool_use_result": {"status": "completed", "agentId": "abcdef1234567890"}, "message": {"content": [
        {"type": "tool_result", "tool_use_id": "call-1", "content": nonce},
    ]}}
    assert worker_canary.native_nonce_returns(raw + b'\n' + json.dumps(result).encode(), nonce)["call-1"]


def test_canary_agy_runner_preserves_maintained_transport_arguments(monkeypatch, tmp_path):
    actual = []
    marker = object()
    monkeypatch.setattr(worker_canary.provider, "run", lambda *a, **k: marker)
    argv = ["agy-profile", "--evidence-prefix", str(tmp_path / "observation")]
    assert worker_canary._runner(actual)(argv, "bounded", tmp_path, 1024) is marker
    assert actual == [argv]


# ---------------------------------------------------------------------------
# Independent Caps 4/4/4 and Borrowing Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("dim,key,value", [
    ("limits", "max_sonnet", 3),
    ("capacity_receipt", "max_sonnet", 3),
    ("limits", "max_gemini", 3),
    ("capacity_receipt", "max_gemini", 3),
    ("limits", "max_luna", 3),
    ("capacity_receipt", "max_luna", 3),
    ("capability", "borrowing", True),
    ("capacity_receipt", "borrowing", True),
])
def test_independent_caps_4_4_4_enforcement(dim, key, value):
    record = _valid_claude_sonnet_native_record()
    if dim == "capability":
        record["capability"][key] = value
    elif dim == "limits":
        record["capability"]["limits"][key] = value
    else:
        record[dim][key] = value
    res = qualify(record)
    assert res["passed"] is False
    assert res["dimensions"]["admission_capacity"] is False


# ---------------------------------------------------------------------------
# External Sonnet Cases (Codex & Gemini) Tests
# ---------------------------------------------------------------------------

def test_qualify_codex_sonnet_external_passes():
    record = {
        **SONNET_IDENTITY,
        "case": "codex-sonnet",
        "phase": "APG166ZQ",
        "candidate_unchanged": True,
        "bundle_unchanged": True,
        "parent": {"provider": "codex", "model": "gpt-6.1-sol", "effort": "xhigh"},
        "parent_observed": {"provider": "codex", "model": "gpt-6.1-sol", "effort": "xhigh"},
        "worker": {"kind": "sonnet", "requested": {"model": "claude-sonnet-5-5", "effort": "high"}},
        "capability": {
            "allowed": True,
            "borrowing": False,
            "limits": {"max_gemini": 4, "max_luna": 4, "max_sonnet": 4, "max_aggregate": 12},
        },
        "capacity_receipt": {"max_gemini": 4, "max_luna": 4, "max_sonnet": 4, "borrowing": False},
        "parent_id": "parent-1",
        "admission": {"job-sonnet-1": {}},
        "worker_results": [
            {
                "worker_kind": "sonnet",
                "effective_model": "claude-sonnet-5-5",
                "effective_effort": "high",
                "transport": "claude_external",
                "parent_id": "parent-1",
                "job_id": "job-sonnet-1",
                "status": "completed",
                "cleanup_proven": True,
                "response": "nonce-token-xyz",
            }
        ],
        "nonce": "nonce-token-xyz",
        "nonce_returned": True,
        "stage_ok": True,
        "parent_cleanup": {"cleanup_proven": True},
        "stage_meta": {"worker_drain": {"status": "closed", "uncertain_cleanup": False}},
    }
    res = qualify(record)
    assert res["passed"] is True
    assert res["dimensions"]["transport"] is True

    record["worker_results"][0]["transport"] = "codex_native"
    res_bad = qualify(record)
    assert res_bad["passed"] is False
    assert res_bad["dimensions"]["transport"] is False


def test_gemini_sonnet_unsupported_blocks_canary(tmp_path, monkeypatch):
    from test_apg166s_r1_home_path import _home_bundle
    home = _home_bundle(tmp_path)
    budget = CanaryBudget(home=home, phase=SONNET_PHASE)
    monkeypatch.setattr(worker_canary, "CanaryBudget", lambda *a, **k: budget)
    monkeypatch.setattr(
        worker_canary,
        "resolve_worker_capability",
        lambda *a, **k: {"allowed": False, "reason": "worker executable agy not found on PATH"},
    )
    res = run_case(ROOT, home, tmp_path / "output", "gemini-sonnet")
    assert res["status"] == "blocked"
    assert res["preflight_refusal"] is True
    assert "worker_unavailable" in res["diagnostic"]
    assert res["cleanup_proven"] is False

    case_entry = budget.get_case("gemini-sonnet")
    assert len(case_entry["attempts"]) == 0
    assert res["budget_reservation"] is None


def test_qualify_gemini_sonnet_observation_only_cannot_pass():
    record = {
        **SONNET_IDENTITY,
        "case": "gemini-sonnet",
        "phase": "APG166ZQ",
        "candidate_unchanged": True,
        "bundle_unchanged": True,
        "parent": {"provider": "antigravity", "model": "gemini-3.8-flash-high", "effort": "high"},
        "parent_observed": {"provider": "antigravity", "model": "gemini-3.8-flash-high", "effort": "high"},
        "worker": {"kind": "sonnet", "requested": {"model": "claude-sonnet-5-5", "effort": "high"}},
        "capability": {
            "allowed": True,
            "borrowing": False,
            "limits": {"max_gemini": 4, "max_luna": 4, "max_sonnet": 4, "max_aggregate": 12},
        },
        "capacity_receipt": {"max_gemini": 4, "max_luna": 4, "max_sonnet": 4, "borrowing": False},
        "parent_id": "parent-gemini-1",
        "admission": {"job-gemini-sonnet-1": {}},
        "worker_results": [
            {
                "worker_kind": "sonnet",
                "effective_model": "claude-sonnet-5-5",
                "effective_effort": "high",
                "transport": "claude_external",
                "parent_id": "parent-gemini-1",
                "job_id": "job-gemini-sonnet-1",
                "status": "completed",
                "cleanup_proven": True,
                "response": "nonce-token-g",
            }
        ],
        "nonce": "nonce-token-g",
        "nonce_returned": True,
        "stage_ok": True,
        "parent_cleanup": {"cleanup_proven": True},
        "stage_meta": {"worker_drain": {"status": "closed", "uncertain_cleanup": False}},
    }
    res = qualify(record)
    # A requested or fabricated stream identity is insufficient for Antigravity.
    # APG166ZW exercises the positive path through the actual dispatcher stage.
    assert res["passed"] is False
    assert res["dimensions"]["parent_model_effort"] is False
    assert res["dimensions"]["transport"] is True


# ---------------------------------------------------------------------------
# Runtime & Bundle Identity Tests for Sonnet Run
# ---------------------------------------------------------------------------

def test_run_case_freeze_mismatch_refuses_before_budget(tmp_path, monkeypatch):
    from test_apg166s_r1_home_path import _home_bundle
    home = _home_bundle(tmp_path)
    freeze_file = tmp_path / "freeze.json"
    freeze_file.write_text(json.dumps({
        "runtime_identity": "tampered_identity_hash",
        "bundle_sha256": "tampered_bundle_sha",
    }))
    monkeypatch.setattr(
        "sys.argv",
        [
            "apgr-worker-canary",
            "claude-sonnet-native",
            "--apgr-home", str(home),
            "--output", str(tmp_path / "output"),
            "--freeze", str(freeze_file),
        ],
    )
    with pytest.raises(ValueError, match="canary freeze mismatch before budget reservation"):
        worker_canary.main()
