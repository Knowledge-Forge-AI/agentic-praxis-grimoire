"""Native Claude admission uses real registered capability and provider hook identities."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import fcntl
import threading
import time

import pytest

from apgr_workers.claude_native import (
    SCOPED_AGENT_NAME, LEAF_AGENT_NAME, compute_capability_digest, ensure_plugin_dir,
    generate_hooks_configuration, generate_agent_definition, handle_hook_pre_tool,
    handle_hook_post_tool, handle_hook_subagent_start, handle_hook_subagent_stop,
    binding_for_facade, ClaudeNativeError,
)
from apgr_workers.facade_context import WorkerFacadeContext
from apgr_workers.ledger import ParentLedger
from apgr_workers.policy import resolve_worker_capability

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def bound(tmp_path, monkeypatch):
    monkeypatch.delenv("APGR_WORKER_LEAF", raising=False)
    state, workspace = tmp_path / "state", tmp_path / "workspace"
    workspace.mkdir()
    cap = resolve_worker_capability(ROOT, "claude", "opus-high-plan", "gemini_sub")
    cap.update(source_root=str(ROOT), lifecycle_generation="native-test", parent_profile="opus-high-plan")
    ledger = ParentLedger("native-test", state)
    ledger.initialize_parent("claude_opus", workspace=workspace, task_authority="read_only", worker_capability=cap)
    facade = WorkerFacadeContext("native-test", state, ROOT, workspace, "claude_opus", "read_only",
                                 "native-test", "opus-high-plan")
    return ledger, cap, facade


def request(identity="tool-1", **overrides):
    return {"tool_name": "Agent", "tool_use_id": identity,
            "tool_input": {"subagent_type": SCOPED_AGENT_NAME, "run_in_background": False, **overrides}}


def invoke(handler, bound, payload):
    ledger, cap, _ = bound
    return handler(payload, ledger.parent_id, ledger.base_dir.parent, compute_capability_digest(cap))[1]


def admitted(result):
    return result["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_five_concurrent_native_calls_admit_exactly_four(bound):
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(lambda i: invoke(handle_hook_pre_tool, bound, request(str(i))), range(5)))
    assert sum(map(admitted, results)) == 4
    assert bound[0].get_status()["sonnet_count"] == 4


@pytest.mark.parametrize("override", [
    {"subagent_type": "general-purpose"}, {"subagent_type": LEAF_AGENT_NAME},
    {"run_in_background": True}, {"model": "claude-sonnet-5-5"}, {"model": "opus"},
    {"effort": "high"}, {"resume": "old-child"},
    {"isolation": "worktree"}, {"team_name": "another-team"}, {"mode": "bypassPermissions"},
])
def test_native_override_escape_denied(bound, override):
    assert not admitted(invoke(handle_hook_pre_tool, bound, request(**override)))
    assert bound[0].get_status()["sonnet_count"] == 0


def test_missing_identity_or_changed_capability_denied(bound):
    payload = request()
    payload.pop("tool_use_id")
    assert not admitted(invoke(handle_hook_pre_tool, bound, payload))
    ledger, _, _ = bound
    _, result = handle_hook_pre_tool(request(), ledger.parent_id, ledger.base_dir.parent, "wrong")
    assert not admitted(result)


def test_correlated_completion_releases_once_and_retains_observations(bound):
    assert admitted(invoke(handle_hook_pre_tool, bound, request()))
    invoke(handle_hook_subagent_start, bound, {"agent_id": "provider-child"})
    assert bound[0].get_status()["sonnet_count"] == 1
    completed = {"tool_use_id": "tool-1", "tool_response": {"status": "completed",
        "resolvedModel": "claude-sonnet-5-5", "effort": "high"}}
    invoke(handle_hook_post_tool, bound, completed)
    invoke(handle_hook_post_tool, bound, completed)
    assert bound[0].get_status()["sonnet_count"] == 0
    record = json.loads(bound[0].data_path.read_text())["native_agents"]["tool-1"]
    assert record["model_observation"]["effective_model"] == "claude-sonnet-5-5"


def test_interrupt_keeps_slot_until_proven_parent_exit(bound):
    assert admitted(invoke(handle_hook_pre_tool, bound, request()))
    invoke(handle_hook_post_tool, bound, {"tool_use_id": "tool-1", "hook_event_name": "PostToolUseFailure", "is_interrupt": True})
    invoke(handle_hook_subagent_stop, bound, {"agent_id": "uncorrelated-child"})
    assert bound[0].get_status()["sonnet_count"] == 1
    drain = bound[0].drain_and_close(parent_exit_observed=True)
    assert not drain["uncertain_cleanup"]
    assert bound[0].get_status()["sonnet_count"] == 0


def test_failure_rollback_and_unproven_exit_retention(bound):
    assert admitted(invoke(handle_hook_pre_tool, bound, request()))
    invoke(handle_hook_post_tool, bound, {"tool_use_id": "tool-1", "hook_event_name": "PostToolUseFailure", "tool_response": {"status": "not_started"}})
    assert bound[0].get_status()["sonnet_count"] == 0
    assert admitted(invoke(handle_hook_pre_tool, bound, request("tool-2")))
    assert bound[0].drain_and_close()["uncertain_cleanup"]
    assert bound[0].get_status()["sonnet_count"] == 1


def test_plugin_is_bound_readonly_and_immutable(bound):
    ledger, cap, facade = bound
    plugin = binding_for_facade(ROOT, facade, True)
    definition = (plugin / "agents" / f"{LEAF_AGENT_NAME}.md").read_text()
    assert "model: claude-sonnet-5-5\neffort: high" in definition
    assert "  - Edit" not in definition and "  - Write" not in definition
    assert "disallowedTools:\n  - Bash\n  - Agent\n  - Task\n  - mcp__*" in definition
    assert binding_for_facade(ROOT, facade, True) == plugin
    (plugin / "agents" / f"{LEAF_AGENT_NAME}.md").write_text("modified")
    with pytest.raises(ClaudeNativeError, match="immutable"):
        ensure_plugin_dir(ROOT, ledger.base_dir.parent, ledger.parent_id, "read_only", cap)
    assert binding_for_facade(ROOT, None, False) is None
    assert "  - Edit" in generate_agent_definition("mutation_capable")


def test_explicit_hook_cli_works_without_parent_environment(bound):
    ledger, cap, _ = bound
    hooks = generate_hooks_configuration(ROOT, ledger.parent_id, ledger.base_dir.parent, compute_capability_digest(cap))
    assert "PostToolUseFailure" in hooks["hooks"]
    command = hooks["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    result = subprocess.run(shlex.split(command), input=json.dumps(request()), text=True, capture_output=True,
                            env={"PATH": "/usr/bin:/bin"})
    assert result.returncode == 0, result.stderr
    assert admitted(json.loads(result.stdout))


def _wrapper_argv(tmp_path, monkeypatch, profile, read_only, arguments=None):
    import claude_vc_profile as launcher
    import claude_model_catalog as catalog
    monkeypatch.delenv("APGR_WORKER_LEAF", raising=False)
    workspace, state = tmp_path / "workspace", tmp_path / "state"
    workspace.mkdir()
    authority = "read_only" if read_only else "mutation_capable"
    cap = resolve_worker_capability(ROOT, "claude", profile, "dynamic")
    family = cap["parent_family"]
    cap.update(source_root=str(ROOT), lifecycle_generation="wrapper-test", parent_profile=profile)
    ledger = ParentLedger("wrapper-test", state)
    ledger.initialize_parent(family, workspace=workspace, task_authority=authority, worker_capability=cap)
    facade = WorkerFacadeContext("wrapper-test", state, ROOT, workspace, family,
                                 authority, "wrapper-test", profile)
    monkeypatch.setattr(launcher, "_load_worker_facade", lambda *a, **kw: facade)
    settings = tmp_path / "synthetic-settings.json"
    settings.write_text("{}")
    monkeypatch.setattr(launcher, "canonical_settings_path", lambda root: settings)
    monkeypatch.setattr(launcher.shutil, "which", lambda name: "/fixture/claude")
    monkeypatch.setattr(catalog, "probe_claude_version", lambda exe: ("2.1.999", "available"))
    home, scratch = tmp_path / "home", tmp_path / "scratch"
    home.mkdir(mode=0o700)
    scratch.mkdir(mode=0o700)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("APGR_AGENT_SCRATCH_ROOT", str(scratch))
    calls = []
    monkeypatch.setattr(launcher.os, "execve", lambda *args: calls.append(args))
    launcher.launch(ROOT / "claude", profile, arguments or ["--print", "one bounded leaf"])
    return calls[0][1], settings


@pytest.mark.parametrize("profile,read_only", [
    ("opus-high-plan", True), ("opus-high-review", True),
    ("opus-high-sysadmin-review", True),
    ("claude-only-implementation-primary", False),
    ("claude-only-architecture-docs-primary", False),
    ("claude-only-sysadmin-primary", False),
    ("fable-architecture-docs-primary", False),
])
def test_actual_claude_wrapper_native_binding(tmp_path, monkeypatch, profile, read_only):
    import claude_vc_profile as launcher
    from apgr_workers.claude_native import effective_tool_names, native_readback
    argv, settings = _wrapper_argv(tmp_path, monkeypatch, profile, read_only)
    assert argv.count("--plugin-dir") == 1
    plugin = Path(argv[argv.index("--plugin-dir") + 1])
    definition = (plugin / "agents" / f"{LEAF_AGENT_NAME}.md").read_text()
    assert "model: claude-sonnet-5-5\neffort: high" in definition
    assert ("  - Edit" in definition) == (not read_only)
    allowed = argv[argv.index("--allowed-tools") + 1].split(",")
    assert "Agent" not in allowed
    assert any(tool.startswith("mcp__agent_worker__") for tool in allowed)
    if launcher.PROFILE_CONTRACTS[profile].isolated_settings:
        assert argv[argv.index("--settings") + 1] == str(settings)
    assert "--disallowed-tools" not in argv
    assert "--disallowedTools" not in argv
    if read_only:
        assert "Agent" in effective_tool_names(argv)
        assert "Bash" not in effective_tool_names(argv)
        assert "Edit" not in effective_tool_names(argv)
        assert "Write" not in effective_tool_names(argv)
    else:
        assert effective_tool_names(argv) is None
    assert native_readback(plugin, "read_only" if read_only else "mutation_capable")["parent_agent_tool"] == "argv_not_removed"


@pytest.mark.parametrize("arguments", [
    ["--disallowed-tools", "Task"], ["--disallowedTools", "Agent"],
    ["--disallowed-tools=Task"], ["--disallowedTools=Agent"],
    ["--disallowed-tools", "Read,Task"], ["--disallowedTools", "Read Task"],
    ["--disallowedTools", "Read", "Task"],
    ["--disallowed-tools", "Task(apgr-sonnet-leaf:apgr-sonnet-leaf)"],
    ["--disallowedTools=Agent(apgr-sonnet-leaf:apgr-sonnet-leaf)"],
    ["--tools", "Read"], ["--tools=Read,Agent"],
])
@pytest.mark.parametrize("read_only", [True, False])
def test_native_bound_caller_tool_overrides_refused_before_exec(tmp_path, monkeypatch, arguments, read_only):
    from claude_vc_profile import ProfileError
    profile = "opus-high-review" if read_only else "claude-only-implementation-primary"
    with pytest.raises(ProfileError, match="tool selection is launcher-owned"):
        _wrapper_argv(tmp_path, monkeypatch, profile, read_only, [*arguments, "--print", "fixture"])


@pytest.mark.parametrize("denied", [
    ["--disallowed-tools", "Task"], ["--disallowedTools=Task"],
    ["--disallowed-tools", "Read,Agent"], ["--disallowedTools", "Read Task"],
    ["--disallowedTools", "Read", "Task"],
    ["--disallowed-tools", "Task(worker, other)"],
    ["--disallowedTools=Agent(worker)"],
])
def test_final_argv_models_actual_alias_filtering_and_refuses_removed_native_tool(denied):
    from apgr_workers.claude_native import effective_tool_names, validate_profile_native_argv
    from claude_vc_profile import ProfileError
    argv = ["claude", "--tools", "Read,Agent", *denied]
    assert "Agent" not in effective_tool_names(argv)
    with pytest.raises(ProfileError, match="Agent route removed"):
        validate_profile_native_argv(argv, Path("fixture-plugin"))
    with pytest.raises(ProfileError, match="Agent route removed"):
        validate_profile_native_argv(["claude", *denied], Path("fixture-plugin"))


@pytest.mark.parametrize("authority", ["read_only", "mutation_capable"])
def test_leaf_alias_contract_and_non_native_facade_stay_worker_disabled(authority):
    from apgr_workers.claude_native import effective_tool_names, apply_profile_native_argv
    definition = generate_agent_definition(authority)
    tools, denied = definition.split("tools:\n", 1)[1].split("disallowedTools:\n", 1)
    tools = [row.strip()[2:] for row in tools.strip().splitlines()]
    denied = [row.strip()[2:] for row in denied.split("---", 1)[0].strip().splitlines()]
    effective = effective_tool_names(["--tools", ",".join(tools), "--disallowedTools", ",".join(denied)])
    assert not effective & {"Agent", "Task", "Bash"}
    argv = ["--tools", "Read,Agent"]
    apply_profile_native_argv(argv, None, object(), authority == "read_only")
    assert "Agent" not in effective_tool_names(argv)


def test_alias_hook_matchers_are_exact_alternatives(bound):
    ledger, cap, _ = bound
    hooks = generate_hooks_configuration(ROOT, ledger.parent_id, ledger.base_dir.parent, compute_capability_digest(cap))
    for event in ("PreToolUse", "PostToolUse", "PostToolUseFailure"):
        assert hooks["hooks"][event][0]["matcher"] == "Agent|Task"


def test_native_state_inside_workspace_is_denied(bound):
    _, _, facade = bound
    from dataclasses import replace
    with pytest.raises(ClaudeNativeError, match="outside the task workspace"):
        binding_for_facade(ROOT, replace(facade, workspace=facade.state_dir), True)



def test_native_quota_pauses_only_sonnet_and_settles_foreground_failure(bound):
    assert admitted(invoke(handle_hook_pre_tool, bound, request()))
    invoke(handle_hook_post_tool, bound, {"tool_use_id": "tool-1",
        "hook_event_name": "PostToolUseFailure", "error": {"code": "insufficient_quota"}})
    ledger = bound[0]
    assert ledger.get_status()["paused_pools"] == ["sonnet"]
    assert ledger.get_status()["sonnet_count"] == 0
    assert not admitted(invoke(handle_hook_pre_tool, bound, request("tool-2")))
    ledger.reserve_gemini("gemini-after-quota", "gemini-after-quota", "gemini-payload")
    ledger.reserve_gemini("luna-after-quota", "luna-after-quota", "luna-payload", worker_kind="luna")


def test_claude_mcp_submission_excludes_native_pool_but_can_pause_it(bound):
    from apgr_workers.mcp import WorkerMCPServer
    specs = {row["name"]: row for row in WorkerMCPServer(bound[2])._tool_specs()}
    assert specs["submit"]["inputSchema"]["properties"]["worker_kind"]["enum"] == ["gemini", "luna"]
    assert specs["pause_pool"]["inputSchema"]["properties"]["worker_kind"]["enum"] == ["gemini", "luna", "sonnet"]



def test_excluded_external_pools_stay_disabled_while_native_sonnet_remains(bound):
    from apgr_workers.mcp import WorkerMCPServer
    from apgr_workers.ledger import AuthorityViolationError
    ledger, _, facade = bound
    with ledger._locked() as data:
        data["allowed_worker_kinds"] = []
        data["worker_capability"]["allowed_worker_kinds"] = []
        data["worker_capability"]["excluded_worker_kinds"] = ["gemini", "luna"]
    specs = {row["name"]: row for row in WorkerMCPServer(facade)._tool_specs()}
    assert "submit" not in specs
    assert specs["pause_pool"]["inputSchema"]["properties"]["worker_kind"]["enum"] == ["sonnet"]
    with pytest.raises(AuthorityViolationError):
        ledger.reserve_gemini("excluded", "excluded", "payload")


@pytest.mark.parametrize("payload", [[], {"tool_name": "Agent", "tool_input": [1]}])
def test_malformed_admission_is_a_blocking_error(bound, payload):
    ledger, cap, _ = bound
    code, result = handle_hook_pre_tool(payload, ledger.parent_id, ledger.base_dir.parent,
                                        compute_capability_digest(cap))
    assert code == 2 and not admitted(result)
    assert ledger.get_status()["sonnet_count"] == 0


@pytest.mark.parametrize("error", [TypeError, KeyError, AttributeError, ImportError])
def test_unexpected_admission_exception_is_a_blocking_error(bound, monkeypatch, error):
    import apgr_workers.claude_native as native
    monkeypatch.setattr(native, "_binding_ledger", lambda *args: (_ for _ in ()).throw(error("fixture")))
    ledger, cap, _ = bound
    code, result = handle_hook_pre_tool(request(), ledger.parent_id, ledger.base_dir.parent,
                                        compute_capability_digest(cap))
    assert code == 2 and not admitted(result)


def test_omitted_foreground_flag_is_denied(bound):
    payload = request()
    payload["tool_input"].pop("run_in_background")
    assert not admitted(invoke(handle_hook_pre_tool, bound, payload))


def test_hook_lock_wait_returns_blocking_error_before_provider_timeout(bound):
    ledger, cap, _ = bound
    hooks = generate_hooks_configuration(ROOT, ledger.parent_id, ledger.base_dir.parent,
                                         compute_capability_digest(cap))
    hook = hooks["hooks"]["PreToolUse"][0]["hooks"][0]
    with ledger.lock_path.open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        started = time.monotonic()
        result = subprocess.run(shlex.split(hook["command"]), input=json.dumps(request()),
                                text=True, capture_output=True, timeout=hook["timeout"] - 1)
    assert result.returncode == 2 and time.monotonic() - started < hook["timeout"]
    assert ledger.get_status()["sonnet_count"] == 0


def test_hook_import_failure_is_a_blocking_error(bound, tmp_path):
    ledger, cap, _ = bound
    source = tmp_path / "missing-dependencies"
    script = source / "libexec/apgr_workers/claude_native.py"
    script.parent.mkdir(parents=True)
    script.write_text("raise ImportError('fixture dependency unavailable')\n")
    hook = generate_hooks_configuration(source, ledger.parent_id, ledger.base_dir.parent,
                                        compute_capability_digest(cap))["hooks"]["PreToolUse"][0]["hooks"][0]
    result = subprocess.run(shlex.split(hook["command"]), input=json.dumps(request()),
                            text=True, capture_output=True, timeout=hook["timeout"] - 1)
    assert result.returncode == 2


def writer_request(identity, scope):
    return request(identity, prompt="APGR-MUTATION-SCOPE: " + json.dumps(scope) + "\nOne bounded edit.")


def test_native_writers_register_disjoint_scope_across_transports(bound):
    from apgr_workers.ledger import AuthorityViolationError
    ledger, _, _ = bound
    with ledger._locked() as data:
        data["task_authority"] = "mutation_capable"
    assert not admitted(invoke(handle_hook_pre_tool, bound, request()))
    assert admitted(invoke(handle_hook_pre_tool, bound, writer_request("writer-1", ["libexec/owned.py"])))
    assert not admitted(invoke(handle_hook_pre_tool, bound, writer_request("writer-2", ["libexec"])))
    with pytest.raises(AuthorityViolationError, match="overlaps"):
        ledger.reserve_gemini("external-1", "external-1", "payload", "mutation_capable",
                              mutation_scope=["libexec/owned.py"])
    ledger.reserve_gemini("external-2", "external-2", "payload", "mutation_capable",
                          mutation_scope=["src/owned.py"])
    assert not admitted(invoke(handle_hook_pre_tool, bound, writer_request("writer-3", ["src"])))
    assert admitted(invoke(handle_hook_pre_tool, bound, writer_request("writer-4", ["docs/owned.md"])))
    records = json.loads(ledger.data_path.read_text())["native_agents"]
    assert records["writer-1"]["mutation_scope"] == ["libexec/owned.py"]
    assert records["writer-1"]["task_authority"] == "mutation_capable"
    assert not admitted(invoke(handle_hook_pre_tool, bound, writer_request("writer-1", ["changed.py"])))


def test_readonly_native_call_cannot_claim_write_scope(bound):
    assert not admitted(invoke(handle_hook_pre_tool, bound, writer_request("writer", ["owned.py"])))


@pytest.mark.parametrize("telemetry,model_status,effort_status", [
    ({"resolvedModel": "claude-sonnet-5-5", "effort": "high"}, "observed_match", "observed_match"),
    ({"resolvedModel": "claude-sonnet-5-5"}, "observed_match", "unknown"),
    ({}, "unknown", "unknown"),
    ({"resolvedModel": "sonnet", "effort": "low"}, "mismatch", "mismatch"),
    ({"resolvedModel": "claude-sonnet-5-5-20261001"}, "mismatch", "unknown"),
])
def test_terminal_lifecycle_is_independent_of_observed_model_and_effort(bound, telemetry, model_status, effort_status):
    assert admitted(invoke(handle_hook_pre_tool, bound, request()))
    invoke(handle_hook_post_tool, bound, {"tool_use_id": "tool-1", "tool_response": {"status": "completed", **telemetry}})
    record = json.loads(bound[0].data_path.read_text())["native_agents"]["tool-1"]
    assert record["status"] == "closed" and record["terminal_result"] == "completed"
    assert record["model_observation"]["model_status"] == model_status
    assert record["model_observation"]["effort_status"] == effort_status
    assert record["model_observation"]["requested_model"] == "claude-sonnet-5-5"
    assert record["model_observation"]["requested_effort"] == "high"
    assert len(record["model_observation"]["definition_sha256"]) == 64
    assert bound[0].get_status()["sonnet_count"] == 0


def test_terminal_replay_cannot_reserve_closed_identity_or_overwrite_evidence(bound):
    assert admitted(invoke(handle_hook_pre_tool, bound, request()))
    completed = {"tool_use_id": "tool-1", "tool_response": {"status": "completed", "resolvedModel": "claude-sonnet-5-5"}}
    invoke(handle_hook_post_tool, bound, completed)
    before = json.loads(bound[0].data_path.read_text())["native_agents"]["tool-1"]
    invoke(handle_hook_post_tool, bound, completed)
    invoke(handle_hook_post_tool, bound, {"tool_use_id": "tool-1", "hook_event_name": "PostToolUseFailure", "error": "fixture failure"})
    assert not admitted(invoke(handle_hook_pre_tool, bound, request()))
    assert json.loads(bound[0].data_path.read_text())["native_agents"]["tool-1"] == before
    assert bound[0].get_status()["sonnet_count"] == 0


@pytest.mark.parametrize("response", [None, {"status": "not_started"}])
def test_correlated_foreground_failure_retains_terminal_record(bound, response):
    assert admitted(invoke(handle_hook_pre_tool, bound, request()))
    invoke(handle_hook_post_tool, bound, {"tool_use_id": "tool-1", "hook_event_name": "PostToolUseFailure", "tool_response": response, "error": "fixture failure"})
    record = json.loads(bound[0].data_path.read_text())["native_agents"]["tool-1"]
    assert record["status"] == "closed" and record["terminal_result"] == "failed"
    assert record["model_observation"]["effort_status"] == "unknown"
    assert bound[0].get_status()["sonnet_count"] == 0


@pytest.mark.parametrize("event,response", [
    ("PostToolUse", {"status": "async_launched"}),
    ("PostToolUse", {}), ("PostToolUse", ["unknown"]),
    ("PostToolUseFailure", {"status": "async_launched"}),
    ("PostToolUseFailure", {"status": "background"}),
    ("PostToolUseFailure", {"status": "detached"}),
    ("PostToolUseFailure", {"run_in_background": True}),
    ("PostToolUseFailure", {"status": "future_status"}),
    ("PostToolUseFailure", ["unknown"]),
])
def test_ambiguous_or_background_work_retains_capacity_and_bounded_observation(bound, event, response):
    assert admitted(invoke(handle_hook_pre_tool, bound, request()))
    for _ in range(10):
        invoke(handle_hook_post_tool, bound, {"tool_use_id": "tool-1", "hook_event_name": event, "tool_response": response})
    record = json.loads(bound[0].data_path.read_text())["native_agents"]["tool-1"]
    assert record["status"] == "reserved" and "terminal_result" not in record
    assert len(record["unreconciled_observations"]) == 8
    assert bound[0].get_status()["sonnet_count"] == 1
    from apgr_workers.settlement import close_settled
    from apgr_workers.ledger import RecoveryConflictError
    with pytest.raises(RecoveryConflictError, match="not settled"):
        close_settled(bound[0], "fixture must remain accounted")
    assert not bound[0].drain_and_close(parent_exit_observed=True)["uncertain_cleanup"]


def test_four_slots_refuse_fifth_then_reuse_and_five_sequential_children(bound):
    ledger = bound[0]
    for cycle in range(2):
        ids = [f"cycle-{cycle}-{i}" for i in range(4)]
        assert all(admitted(invoke(handle_hook_pre_tool, bound, request(i))) for i in ids)
        assert not admitted(invoke(handle_hook_pre_tool, bound, request(f"refused-{cycle}")))
        for i in ids:
            invoke(handle_hook_post_tool, bound, {"tool_use_id": i, "tool_response": {"status": "completed"}})
        assert ledger.get_status()["sonnet_count"] == 0
    for i in range(5):
        identity = f"sequential-{i}"
        assert admitted(invoke(handle_hook_pre_tool, bound, request(identity)))
        assert ledger.get_status()["sonnet_count"] == 1
        invoke(handle_hook_post_tool, bound, {"tool_use_id": identity, "tool_response": {"status": "completed"}})
        assert ledger.get_status()["sonnet_count"] == 0
    status = ledger.get_status()
    assert (status["max_gemini"], status["max_luna"], status["max_sonnet"]) == (4, 4, 4)
    from apgr_workers.settlement import close_settled
    assert close_settled(ledger, "fixture foreground completion")["status"] == "closed"


@pytest.mark.parametrize("name", ["Agent", "Task"])
def test_hook_alias_cannot_bypass_bounded_admission(bound, name):
    payload = request(subagent_type="general-purpose")
    payload["tool_name"] = name
    assert not admitted(invoke(handle_hook_pre_tool, bound, payload))
    payload = request()
    payload["tool_name"] = name
    assert admitted(invoke(handle_hook_pre_tool, bound, payload))
    invoke(handle_hook_post_tool, bound, {"tool_name": name, "tool_use_id": "tool-1", "tool_response": {"status": "completed"}})
    assert bound[0].get_status()["sonnet_count"] == 0


def terminal_notification(identity="tool-1", terminal="completed"):
    return {"tool_use_id": identity,
            "hook_event_name": "PostToolUseFailure" if terminal == "failed" else "PostToolUse",
            "tool_response": {"status": terminal}}


def reopened_data(ledger):
    return ParentLedger(ledger.parent_id, ledger.base_dir.parent)._read_data()


def seed_zq_terminal(bound, identity="tool-1", **changes):
    ledger = bound[0]
    assert admitted(invoke(handle_hook_pre_tool, bound, request(identity)))
    with ledger._locked() as data:
        record = data["native_agents"][identity]
        record.update(terminal_result="completed", terminal_evidence="foreground_tool_return",
                      cleanup_proven=True, model_observation={"model_status": "unknown"})
        record.update(changes)
        return dict(record)


def assert_no_stranded_terminal(data):
    for record in data["native_agents"].values():
        if (record.get("terminal_result"), record.get("terminal_evidence")) in {
            ("completed", "foreground_tool_return"), ("failed", "foreground_tool_return"),
            ("failed", "legacy_not_started"),
        } and record.get("cleanup_proven") is True:
            assert record["status"] == "closed"


def test_zr_full_pool_completion_frees_slot_before_parent_exit(bound):
    ledger = bound[0]
    for i in range(4):
        assert admitted(invoke(handle_hook_pre_tool, bound, request(f"slot-{i}")))
    assert not admitted(invoke(handle_hook_pre_tool, bound, request("fifth")))
    invoke(handle_hook_post_tool, bound, terminal_notification("slot-0"))
    assert ledger.get_status()["sonnet_count"] == 3
    assert admitted(invoke(handle_hook_pre_tool, bound, request("distinct-new-child")))
    assert not admitted(invoke(handle_hook_pre_tool, bound, request("sixth")))
    assert reopened_data(ledger)["status"] == "active"


@pytest.mark.parametrize("quota", [False, True], ids=["completion", "quota-failure"])
def test_zr_terminal_state_and_pause_share_one_persistence(bound, monkeypatch, quota):
    assert admitted(invoke(handle_hook_pre_tool, bound, request()))
    writes = []
    original = ParentLedger._write_data
    def observe(self, data):
        # Binding status read persists too; count only writes carrying terminal evidence.
        if data["native_agents"]["tool-1"].get("terminal_result"):
            writes.append(json.loads(json.dumps(data)))
        return original(self, data)
    monkeypatch.setattr(ParentLedger, "_write_data", observe)
    payload = terminal_notification(terminal="failed" if quota else "completed")
    if quota:
        payload["error"] = {"code": "insufficient_quota"}
    invoke(handle_hook_post_tool, bound, payload)
    assert len(writes) == 1
    assert_no_stranded_terminal(writes[0])
    assert writes[0]["pool_state"]["sonnet"]["paused"] is quota


@pytest.mark.parametrize("quota", [False, True], ids=["completion", "quota-failure"])
def test_zr_old_split_boundary_is_absent(bound, monkeypatch, quota):
    assert admitted(invoke(handle_hook_pre_tool, bound, request()))
    def interrupted(*args, **kwargs):
        raise RuntimeError("old split transaction interrupted")
    monkeypatch.setattr(ParentLedger, "close_native", interrupted)
    monkeypatch.setattr(ParentLedger, "pause_pool", interrupted)
    payload = terminal_notification(terminal="failed" if quota else "completed")
    if quota:
        payload["error"] = {"code": "insufficient_quota"}
    invoke(handle_hook_post_tool, bound, payload)
    data = reopened_data(bound[0])
    assert_no_stranded_terminal(data)
    assert data["pool_state"]["sonnet"]["paused"] is quota


@pytest.mark.parametrize("fault", ["write", "close", "pause"])
def test_zr_failed_settlement_persistence_claims_no_close(bound, monkeypatch, fault):
    from apgr_workers import ledger as ledger_module
    from apgr_workers import native_capacity
    from apgr_workers.ledger import LedgerError
    ledger = bound[0]
    assert admitted(invoke(handle_hook_pre_tool, bound, request()))
    payload = terminal_notification(terminal="failed")
    payload["error"] = {"code": "insufficient_quota"}
    original = ParentLedger._write_data
    def fail_write(self, data):
        if data["native_agents"]["tool-1"].get("terminal_result"):
            raise LedgerError("injected persistence failure")
        return original(self, data)
    with monkeypatch.context() as patch:
        if fault == "write":
            patch.setattr(ParentLedger, "_write_data", fail_write)
        elif fault == "close":
            patch.setattr(native_capacity, "close_native_agent_slot", lambda *args: False)
        else:
            def fail_pause(*args):
                raise LedgerError("injected pause failure")
            patch.setattr(ledger_module, "apply_pool_pause", fail_pause)
        with pytest.raises(LedgerError):
            invoke(handle_hook_post_tool, bound, payload)
    data = reopened_data(ledger)
    assert data["native_agents"]["tool-1"]["status"] == "reserved"
    assert "terminal_result" not in data["native_agents"]["tool-1"]
    assert data["pool_state"]["sonnet"]["paused"] is False
    assert ledger.get_status()["sonnet_count"] == 1
    invoke(handle_hook_post_tool, bound, payload)
    assert_no_stranded_terminal(reopened_data(ledger))


@pytest.mark.parametrize("boundary", ["before", "after"])
@pytest.mark.parametrize("quota", [False, True], ids=["completion", "quota-failure"])
def test_zr_process_death_at_settlement_rename(bound, boundary, quota):
    ledger, cap, _ = bound
    assert admitted(invoke(handle_hook_pre_tool, bound, request()))
    payload = terminal_notification(terminal="failed" if quota else "completed")
    if quota:
        payload["error"] = {"code": "insufficient_quota"}
    script = '''
import json, os, sys
from pathlib import Path
from apgr_workers.claude_native import handle_hook_post_tool
payload, parent, state, digest, boundary = json.loads(sys.argv[1])
original = Path.replace
def interrupted(self, target):
    # Target the settlement rename, never the binding get_status() rename.
    data = json.loads(self.read_text())
    terminal = data["native_agents"]["tool-1"].get("terminal_result")
    if terminal and boundary == "before":
        os._exit(9)
    result = original(self, target)
    if terminal:
        os._exit(9)
    return result
Path.replace = interrupted
handle_hook_post_tool(payload, parent, state, digest)
'''
    result = subprocess.run([sys.executable, "-c", script, json.dumps([
        payload, ledger.parent_id, str(ledger.base_dir.parent), compute_capability_digest(cap), boundary,
    ])], env={**os.environ, "PYTHONPATH": str(ROOT / "libexec")}, capture_output=True, timeout=10, check=False)
    assert result.returncode == 9, result.stderr
    data = reopened_data(ledger)
    record = data["native_agents"]["tool-1"]
    assert_no_stranded_terminal(data)
    if boundary == "before":
        assert record["status"] == "reserved" and "terminal_result" not in record
        assert data["pool_state"]["sonnet"]["paused"] is False
    else:
        assert record["status"] == "closed"
        assert data["pool_state"]["sonnet"]["paused"] is quota


@pytest.mark.parametrize("trigger", ["completed", "failed"])
@pytest.mark.parametrize("status", ["reserved", "active", "uncertain"])
def test_zr_legacy_terminal_recovers_once_without_overwrite(bound, trigger, status):
    seed = seed_zq_terminal(bound, status=status)
    for i in range(3):
        assert admitted(invoke(handle_hook_pre_tool, bound, request(f"other-{i}")))
    assert not admitted(invoke(handle_hook_pre_tool, bound, request("fifth")))
    payload = terminal_notification(terminal=trigger)
    if trigger == "failed":
        payload["error"] = {"code": "insufficient_quota"}
    invoke(handle_hook_post_tool, bound, payload)
    ledger = bound[0]
    assert ledger.get_status()["sonnet_count"] == 3
    record = reopened_data(ledger)["native_agents"]["tool-1"]
    for key, value in seed.items():
        if key not in {"status", "updated_at"}:
            assert record[key] == value
    assert record["settlement"] == "recovered_split_transaction"
    assert record["settlement_recovery"]["conflicting_trigger"] is (trigger != "completed")
    assert ledger.get_status()["paused_pools"] == []
    for terminal in [trigger, "completed", "failed"]:
        invoke(handle_hook_post_tool, bound, terminal_notification(terminal=terminal))
    assert reopened_data(ledger)["native_agents"]["tool-1"] == record
    assert not admitted(invoke(handle_hook_pre_tool, bound, request()))
    assert admitted(invoke(handle_hook_pre_tool, bound, request("new-child")))
    assert ledger.get_status()["sonnet_count"] == 4


@pytest.mark.parametrize("legacy", [False, True], ids=["fresh", "legacy"])
def test_zr_concurrent_duplicates_release_only_one_slot(bound, legacy):
    if legacy:
        seed_zq_terminal(bound)
    else:
        assert admitted(invoke(handle_hook_pre_tool, bound, request()))
    for i in range(3):
        assert admitted(invoke(handle_hook_pre_tool, bound, request(f"other-{i}")))
    barrier = threading.Barrier(11)
    def notify(i):
        barrier.wait(timeout=10)
        if i < 8:
            invoke(handle_hook_post_tool, bound, terminal_notification())
            return False
        return admitted(invoke(handle_hook_pre_tool, bound, request(f"racing-{i}")))
    with ThreadPoolExecutor(max_workers=11) as pool:
        admissions = sum(pool.map(notify, range(11)))
    assert admissions <= 1
    ledger = bound[0]
    assert ledger.get_status()["sonnet_count"] == 3 + admissions
    if not admissions:
        assert admitted(invoke(handle_hook_pre_tool, bound, request("follow-up")))
    assert ledger.get_status()["sonnet_count"] == 4
    assert not admitted(invoke(handle_hook_pre_tool, bound, request("overflow")))
    data = reopened_data(ledger)
    assert sum("settlement" in r for r in data["native_agents"].values()) == 1
    assert_no_stranded_terminal(data)


@pytest.mark.parametrize("changes", [
    {"cleanup_proven": False}, {"cleanup_proven": 1}, {"terminal_evidence": "unknown"},
    {"terminal_result": "unknown"}, {"terminal_evidence": "legacy_not_started"},
    {"agent_id": "another-child"}, {"agent_type": "general-purpose"},
], ids=["no-cleanup", "nonboolean-cleanup", "unknown-evidence", "unknown-result",
        "impossible-pair", "wrong-id", "wrong-type"])
def test_zr_insufficient_legacy_evidence_retains_capacity(bound, changes):
    seed = seed_zq_terminal(bound, **changes)
    invoke(handle_hook_post_tool, bound, terminal_notification())
    assert reopened_data(bound[0])["native_agents"]["tool-1"] == seed
    assert bound[0].get_status()["sonnet_count"] == 1
    assert bound[0].drain_and_close()["uncertain_cleanup"]
    assert bound[0].get_status()["sonnet_count"] == 1
    assert not bound[0].drain_and_close(parent_exit_observed=True)["uncertain_cleanup"]


@pytest.mark.parametrize("changes", [
    {"is_interrupt": True}, {"tool_response": {"status": "async_launched"}},
    {"tool_response": {}}, {"hook_event_name": "SubagentStop"},
    {"tool_use_id": "uncorrelated"}, {"tool_response": {"status": "completed", "background": True}},
], ids=["interrupt", "async", "unknown", "stop", "uncorrelated", "background"])
def test_zr_nonterminal_duplicate_does_not_recover(bound, changes):
    seed = seed_zq_terminal(bound)
    invoke(handle_hook_post_tool, bound, {**terminal_notification(), **changes})
    invoke(handle_hook_subagent_stop, bound, {"agent_id": "tool-1"})
    assert reopened_data(bound[0])["native_agents"]["tool-1"] == seed
    assert bound[0].get_status()["sonnet_count"] == 1


@pytest.mark.parametrize("history", ["none", "paused", "resumed"])
def test_zr_legacy_quota_recovery_preserves_operator_pool_history(bound, history):
    seed_zq_terminal(bound, terminal_result="failed", error_class="quota_exhaustion")
    ledger = bound[0]
    if history != "none":
        ledger.pause_pool("sonnet", "operator_hold", {"operator": "pause"})
    if history == "resumed":
        # Represent the explicit operator resume state without expanding the
        # native pool's external-only resume API in this settlement repair.
        with ledger._locked() as data:
            data["pool_state"]["sonnet"].update(paused=False, resume_evidence={"operator": "resume"},
                                                resumed_at=time.time())
    before = reopened_data(ledger)["pool_state"]["sonnet"]
    invoke(handle_hook_post_tool, bound, terminal_notification(terminal="failed"))
    data = reopened_data(ledger)
    assert_no_stranded_terminal(data)
    pool = data["pool_state"]["sonnet"]
    if history == "none":
        assert pool["paused"] is True
        assert pool["evidence"]["source"] == "retained_native_terminal_record"
    else:
        assert pool == before
    assert admitted(invoke(handle_hook_pre_tool, bound, request("new-child"))) is (history == "resumed")
    ledger.reserve_gemini("gemini-independent", "g", "payload")
    ledger.reserve_gemini("luna-independent", "l", "payload", worker_kind="luna")


def test_zr_quota_while_already_paused_settles_preserving_cause(bound):
    ledger = bound[0]
    assert admitted(invoke(handle_hook_pre_tool, bound, request()))
    before = ledger.pause_pool("sonnet", "operator_hold", {"operator": "pause"})
    payload = terminal_notification(terminal="failed")
    payload["error"] = {"code": "insufficient_quota"}
    code, _ = handle_hook_post_tool(payload, ledger.parent_id, ledger.base_dir.parent,
                                    compute_capability_digest(bound[1]))
    assert code == 0
    data = reopened_data(ledger)
    assert data["pool_state"]["sonnet"] == before
    assert_no_stranded_terminal(data)


def test_zr_legacy_recovery_requires_binding_and_releases_writer_scope(bound):
    ledger = bound[0]
    seed_zq_terminal(bound)
    before = reopened_data(ledger)["native_agents"]
    with pytest.raises(ClaudeNativeError):
        handle_hook_post_tool(terminal_notification(), ledger.parent_id, ledger.base_dir.parent, "wrong")
    assert reopened_data(ledger)["native_agents"] == before
    assert not admitted(invoke(handle_hook_pre_tool, bound, writer_request("readonly", ["libexec/owned.py"])))
    with ledger._locked() as data:
        data["task_authority"] = "mutation_capable"
        data["native_agents"]["tool-1"].update(task_authority="mutation_capable", mutation_scope=["libexec/owned.py"])
    assert not admitted(invoke(handle_hook_pre_tool, bound, writer_request("writer", ["libexec"])))
    invoke(handle_hook_post_tool, bound, terminal_notification())
    assert admitted(invoke(handle_hook_pre_tool, bound, writer_request("writer", ["libexec"])))


@pytest.mark.parametrize("change", ["status", "parent", "capability"])
def test_zr_settlement_rechecks_binding_under_lock(bound, monkeypatch, change):
    import apgr_workers.claude_native as native
    ledger = bound[0]
    assert admitted(invoke(handle_hook_pre_tool, bound, request()))
    original = native._binding_ledger
    def changed_after_binding(*args):
        result = original(*args)
        with result._locked() as data:
            if change == "status":
                data["status"] = "closed"
            elif change == "parent":
                data["parent_family"] = "codex_parent"
            else:
                data["worker_capability"]["sonnet_worker"]["effort"] = "low"
        return result
    monkeypatch.setattr(native, "_binding_ledger", changed_after_binding)
    with pytest.raises(ClaudeNativeError):
        invoke(handle_hook_post_tool, bound, terminal_notification())
    assert "terminal_result" not in reopened_data(ledger)["native_agents"]["tool-1"]
