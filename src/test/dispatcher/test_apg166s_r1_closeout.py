"""Narrow regressions for the dispatcher-supplied work-review findings."""
from pathlib import Path
import json
import subprocess

import pytest

from agent_phase import worker_canary
from agent_phase.canary_budget import CanaryBudget
from agent_phase.provider import Result
from apgr_workers.codex_external import LunaProfile, build_codex_exec_argv
from test_apg166s_r1_home_path import _home_bundle

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("authority,sandbox,skip", [
    ("read_only", "read-only", True),
    ("mutation_capable", "workspace-write", False),
])
def test_non_git_exception_is_read_only(tmp_path, authority, sandbox, skip):
    profile = LunaProfile("leaf", "selected-model", "high", False, "fixture", "digest")
    argv = build_codex_exec_argv(profile, tmp_path, authority)
    assert ("--skip-git-repo-check" in argv) is skip
    assert argv[argv.index("--sandbox") + 1] == sandbox
    assert "agents.enabled=false" in argv


def test_inherited_parent_context_is_removed_without_changing_auth(monkeypatch):
    names = ("APG166S_BOOTSTRAP_REQUIRED_WORKERS", "CODEX_THREAD_ID", "CODEX_SESSION_ID", "CODEX_CI")
    for name in names:
        monkeypatch.setenv(name, "inherited")
    monkeypatch.setenv("SECURITYSESSIONID", "auth-context")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", "/fixture/auth-home")
    clean = worker_canary.clean_environment()
    assert not set(names).intersection(clean)
    assert clean["SECURITYSESSIONID"] == "auth-context"
    assert clean["CLAUDE_CONFIG_DIR"] == "/fixture/auth-home"


@pytest.mark.parametrize("auth_failure", [True, False])
def test_run_case_consumes_failed_admission_without_false_success(tmp_path, monkeypatch, auth_failure):
    """Real harness and budget, fake provider boundary; absent tools cannot pass."""
    real_run = subprocess.run

    def fixture_process_identity(argv, *args, **kwargs):
        if argv[0] == "ps":
            return subprocess.CompletedProcess(argv, 0, "fixture-process-start\n", "")
        return real_run(argv, *args, **kwargs)

    # Provider-free budget bookkeeping has a stable fixture process identity.
    monkeypatch.setattr("agent_phase.canary_budget.subprocess.run", fixture_process_identity)
    home = _home_bundle(tmp_path)
    budget = CanaryBudget(home=tmp_path)
    monkeypatch.setattr(worker_canary, "CanaryBudget", lambda **kwargs: budget)
    events = [{"type": "system", "subtype": "init", "model": "claude-fable-5-1", "tools": []}]
    if auth_failure:
        events.append({"type": "assistant", "error": "authentication_failed"})
    raw = "\n".join(json.dumps(event) for event in events).encode()
    result = Result(1 if auth_failure else 0, raw, b"", False, 1, 2,
                    cleanup={"cleanup_proven": True})
    # Keep real roster/capability resolution; double only the provider stage.
    monkeypatch.setattr(worker_canary.Dispatcher, "_stage", lambda *a, **k: (
        result, {"worker_drain": {"status": "closed", "uncertain_cleanup": False}}))
    record = worker_canary.run_case(ROOT, home, tmp_path / "output", "claude-gemini")
    assert record["authentication_failed"] is auth_failure
    assert record["status"] == ("blocked" if auth_failure else "partial")
    assert not record["qualification"]["passed"]
    assert not record["qualification"]["dimensions"]["admission_capacity"]
    attempts = json.loads(budget.path.read_text())["cases"]["claude-gemini"]["attempts"]
    assert len(attempts) == 1
    assert attempts[0]["status"] == record["status"]
