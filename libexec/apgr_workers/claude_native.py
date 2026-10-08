"""Launcher-owned Claude native leaf definition and atomic foreground Agent hooks."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import stat
import sys
import time
from typing import Mapping

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from apgr_workers import ledger as ledger_owner
from apgr_workers import native_capacity
from apgr_workers.ledger import ACTIVE_NATIVE_STATES, ParentLedger, sanitize_parent_id

NATIVE_CAP = 4
LEAF_AGENT_NAME = "apgr-sonnet-leaf"
PLUGIN_NAME = "apgr-sonnet-leaf"
SCOPED_AGENT_NAME = f"{PLUGIN_NAME}:{LEAF_AGENT_NAME}"
NATIVE_MODEL = "claude-sonnet-5-5"
NATIVE_EFFORT = "high"
MUTATION_SCOPE_PREFIX = "APGR-MUTATION-SCOPE: "
TOOL_ALIAS_MODEL = "claude-task-agent-v1"
CLAUDE_TOOL_ALIASES = {"Task": "Agent"}
TOOL_LIST_FLAGS = {"--tools", "--disallowed-tools", "--disallowedTools"}
# Guard dependency loading and blocking flock/reaping before Claude's 15s
# hook timeout (which otherwise proceeds through ordinary permission flow).
HOOK_BOOTSTRAP = """import os, runpy, signal, sys
def deny(*args):
    os.write(2, b'APGR native hook failed or exceeded its deadline; admission denied\\n')
    os._exit(2)
try:
    signal.signal(signal.SIGALRM, deny)
    signal.setitimer(signal.ITIMER_REAL, 10)
    sys.argv = sys.argv[1:]
    runpy.run_path(sys.argv[0], run_name='__main__')
except SystemExit as error:
    if error.code not in (None, 0, 2):
        deny()
    raise
except BaseException:
    deny()
"""
READ_ONLY_LEAF_TOOLS = ("Read", "Glob", "Grep")
WRITER_LEAF_TOOLS = (*READ_ONLY_LEAF_TOOLS, "Edit", "Write")
HOOK_EVENT_PRE_TOOL = "PreToolUse"
HOOK_EVENT_POST_TOOL = "PostToolUse"
HOOK_EVENT_SUBAGENT_START = "SubagentStart"
HOOK_EVENT_SUBAGENT_STOP = "SubagentStop"


class ClaudeNativeError(ValueError):
    """The native binding is absent, changed, or unauthorized."""


def canonical_tool_name(name):
    base = name.split("(", 1)[0].strip()
    return CLAUDE_TOOL_ALIASES.get(base, base)


def _tool_tokens(values):
    # Commas/spaces inside an Agent(type, type) specifier are not separators.
    tokens, token, depth = [], "", 0
    for char in " ".join(values) + ",":
        if char in ", \t\n" and depth == 0:
            if token:
                tokens.append(canonical_tool_name(token))
                token = ""
        else:
            token += char
            depth += (char == "(") - (char == ")")
    if token:
        tokens.append(canonical_tool_name(token))
    return tokens


def _tool_flag_values(argv, flags):
    values, found, index = [], False, 0
    while index < len(argv) and argv[index] != "--":
        flag, equal, value = argv[index].partition("=")
        index += 1
        if flag not in flags:
            continue
        found = True
        if equal:
            values.append(value)
        else:
            while index < len(argv) and not argv[index].startswith("-"):
                values.append(argv[index])
                index += 1
    return found, _tool_tokens(values)


def effective_tool_names(argv, ambient=None):
    """Predict CLI alias filtering only; private/provider policy is unobserved."""
    explicit, tools = _tool_flag_values(argv, {"--tools"})
    if not explicit and ambient is None or "default" in tools:
        return None
    configured = set(tools if explicit else map(canonical_tool_name, ambient))
    _, denied = _tool_flag_values(argv, {"--disallowed-tools", "--disallowedTools"})
    return configured - set(denied)


def validate_profile_native_argv(argv, plugin):
    if plugin is None:
        return
    from claude_vc_profile import ProfileError
    effective = effective_tool_names(argv)
    _, denied = _tool_flag_values(argv, {"--disallowed-tools", "--disallowedTools"})
    if "Agent" in denied or effective is not None and "Agent" not in effective:
        raise ProfileError("native parent Agent route removed by CLI tool selection")


def compute_capability_digest(capability):
    return hashlib.sha256(json.dumps(dict(capability or {}), sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def get_plugin_dir(state_dir, parent_id):
    return Path(state_dir).resolve() / "claude_plugins" / f"{sanitize_parent_id(parent_id)}_sonnet_leaf"


def generate_plugin_manifest():
    return {"name": PLUGIN_NAME, "version": "1.0.0", "description": "Bounded APGR native Sonnet leaf"}


def generate_agent_definition(task_authority="mutation_capable"):
    if task_authority not in {"read_only", "mutation_capable"}:
        raise ClaudeNativeError("invalid task authority")
    tools = READ_ONLY_LEAF_TOOLS if task_authority == "read_only" else WRITER_LEAF_TOOLS
    return (f"---\nname: {LEAF_AGENT_NAME}\ndescription: Execute one bounded APGR leaf assignment.\n"
            f"model: {NATIVE_MODEL}\neffort: {NATIVE_EFFORT}\ntools:\n"
            + "".join(f"  - {tool}\n" for tool in tools)
            + "disallowedTools:\n  - Bash\n  - Agent\n  - Task\n  - mcp__*\n---\n"
            + "Follow the parent assignment and its write scope. Do not delegate, register parents, "
              "run tests or builds under read-only authority, or stage, commit or publish.\n")


def generate_hooks_configuration(source_root, parent_id, state_dir, capability_digest):
    script = Path(source_root).resolve() / "libexec/apgr_workers/claude_native.py"
    def hook(action, matcher=None):
        command = shlex.join([sys.executable, "-c", HOOK_BOOTSTRAP, str(script), action, "--parent-id", parent_id,
                              "--state-dir", str(Path(state_dir).resolve()),
                              "--capability-digest", capability_digest])
        return [{**({"matcher": matcher} if matcher else {}),
                 "hooks": [{"type": "command", "command": command, "timeout": 15}]}]
    return {"hooks": {
        "PreToolUse": hook("pre-tool", "Agent|Task"),
        "PostToolUse": hook("post-tool", "Agent|Task"),
        "PostToolUseFailure": hook("post-tool", "Agent|Task"),
        "SubagentStart": hook("subagent-start"),
        "SubagentStop": hook("subagent-stop"),
    }}


def _plugin_files(root, state, parent, authority, cap):
    return {
        ".claude-plugin/plugin.json": json.dumps(generate_plugin_manifest(), sort_keys=True) + "\n",
        f"agents/{LEAF_AGENT_NAME}.md": generate_agent_definition(authority),
        "hooks/hooks.json": json.dumps(generate_hooks_configuration(root, parent, state,
                                         compute_capability_digest(cap)), sort_keys=True) + "\n",
    }


def ensure_plugin_dir(source_root, state_dir, parent_id, task_authority="mutation_capable", capability=None):
    plugin = get_plugin_dir(state_dir, parent_id)
    root, state = Path(source_root).resolve(), Path(state_dir).resolve()
    for owner in (root,):
        if state == owner or owner in state.parents:
            raise ClaudeNativeError("native state must be outside source")
    for relative, body in _plugin_files(root, state, parent_id, task_authority, capability).items():
        target = plugin / relative
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if any(part.is_symlink() for part in [plugin, *target.parents] if part == state or state in part.parents):
            raise ClaudeNativeError("native plugin ancestry cannot be symlinked")
        try:
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        except FileExistsError:
            fd = os.open(target, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, "rb") as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode) or stream.read() != body.encode():
                    raise ClaudeNativeError("native plugin differs from its immutable binding")
        else:
            with os.fdopen(fd, "w") as stream:
                stream.write(body)
    return plugin


def _binding_ledger(parent_id, state_dir, digest):
    ledger = ParentLedger(parent_id, state_dir)
    _validate_binding(ledger.get_status(), digest)
    return ledger


def _validate_binding(status, digest):
    cap = status.get("worker_capability") or {}
    if (status.get("status") != "active" or status.get("parent_family") not in {"claude_opus", "claude_fable"}
            or cap.get("policy_selection") != "triple_pool_4x4x4"
            or cap.get("sonnet_worker", {}).get("transport") != "claude_native"
            or "sonnet" in cap.get("excluded_worker_kinds", [])
            or not digest or compute_capability_digest(cap) != digest):
        raise ClaudeNativeError("native hook requires the exact active triple-pool Claude binding")


def binding_for_facade(root, facade, read_only):
    if facade is None:
        return None
    ledger = facade.ledger
    status = ledger.get_status()
    cap = status.get("worker_capability") or {}
    if cap.get("policy_selection") != "triple_pool_4x4x4" or "sonnet" in cap.get("excluded_worker_kinds", []):
        return None
    _binding_ledger(facade.parent_id, facade.state_dir, compute_capability_digest(cap))
    authority = "read_only" if read_only else "mutation_capable"
    if status.get("task_authority") != authority:
        raise ClaudeNativeError("native task authority differs from the parent")
    state, workspace = Path(facade.state_dir).resolve(), Path(facade.workspace).resolve()
    if state == workspace or workspace in state.parents:
        raise ClaudeNativeError("native state must be outside the task workspace")
    return ensure_plugin_dir(root, facade.state_dir, facade.parent_id, authority, cap)


def native_readback(plugin, authority):
    agent = Path(plugin) / "agents" / f"{LEAF_AGENT_NAME}.md"
    return {"enabled": True, "agent": SCOPED_AGENT_NAME, "model": NATIVE_MODEL,
            "effort": NATIVE_EFFORT, "cap": 4, "transport": "claude_native",
            "definition_sha256": hashlib.sha256(agent.read_bytes()).hexdigest(),
            "hook_mode": "foreground Agent admission and terminal result",
            "parent_agent_tool": "argv_not_removed", "tool_evidence": "configured",
            "tool_alias_model": TOOL_ALIAS_MODEL,
            "leaf_tools": list(READ_ONLY_LEAF_TOOLS if authority == "read_only" else WRITER_LEAF_TOOLS)}


def _payload(raw):
    return dict(raw) if isinstance(raw, Mapping) else json.loads(raw)


def _decision(allow, reason=""):
    return (0 if allow else 2), {"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "allow" if allow else "deny",
        "permissionDecisionReason": reason}}


def handle_hook_pre_tool(raw_input, parent_id, state_dir, capability_digest=None):
    try:
        payload = _payload(raw_input)
        if canonical_tool_name(payload.get("tool_name", "")) != "Agent":
            return _decision(True)
        tool = payload.get("tool_input") or {}
        if tool.get("subagent_type") != SCOPED_AGENT_NAME:
            return _decision(False, "only the launcher-owned Sonnet leaf is permitted")
        if any(key in tool for key in ("model", "effort", "model_reasoning_effort", "resume", "tools", "permission_mode")):
            return _decision(False, "per-call model, effort and resume overrides are prohibited")
        if set(tool) - {"subagent_type", "description", "prompt", "run_in_background", "max_turns"}:
            return _decision(False, "caller isolation, team and unknown Agent overrides are prohibited")
        if tool.get("run_in_background") is not False:
            return _decision(False, "native workers require explicit run_in_background=false")
        tool_id = payload.get("tool_use_id")
        if not isinstance(tool_id, str) or not tool_id:
            return _decision(False, "native admission requires a provider tool-use identity")
        ledger = _binding_ledger(parent_id, state_dir, capability_digest)
        authority = ledger.get_status()["task_authority"]
        prompt = tool.get("prompt") or ""
        scope = json.loads(prompt.splitlines()[0][len(MUTATION_SCOPE_PREFIX):]) if prompt.startswith(MUTATION_SCOPE_PREFIX) else []
        if authority == "mutation_capable" and not scope:
            return _decision(False, "native writers require an APGR-MUTATION-SCOPE JSON array on the first prompt line")
        admitted, reason = ledger.reserve_native(tool_id, LEAF_AGENT_NAME,
                                                 task_authority=authority, mutation_scope=scope)
        return _decision(admitted and reason in {"admitted", "already_admitted"}, reason)
    except Exception as error:
        return _decision(False, "native admission failed: " + type(error).__name__)


def _model_observation(result, authority):
    model, effort = result.get("resolvedModel"), result.get("effort")
    model = model if isinstance(model, str) and 0 < len(model) <= 256 else None
    effort = effort if isinstance(effort, str) and 0 < len(effort) <= 64 else None
    used = result.get("modelsUsed")
    return {"requested_model": NATIVE_MODEL, "requested_effort": NATIVE_EFFORT,
            "configured_model": NATIVE_MODEL, "configured_effort": NATIVE_EFFORT,
            "configuration_source": "launcher agent definition",
            "definition_sha256": hashlib.sha256(generate_agent_definition(authority).encode()).hexdigest(),
            "effective_model": model, "effective_effort": effort,
            "model_status": "unknown" if model is None else "observed_match" if model == NATIVE_MODEL else "mismatch",
            "effort_status": "unknown" if effort is None else "observed_match" if effort == NATIVE_EFFORT else "mismatch",
            "models_used": [x for x in used[:32] if isinstance(x, str) and len(x) <= 256] if isinstance(used, list) else None,
            "source": "provider Agent terminal response"}


def _terminal_result(payload, result):
    if payload.get("hook_event_name") not in {None, "PostToolUse", "PostToolUseFailure"}:
        return None
    if payload.get("is_interrupt") or payload.get("interrupted"):
        return None
    tool = payload.get("tool_input") or {}
    if isinstance(tool, Mapping) and tool.get("run_in_background") is True:
        return None
    if isinstance(result, Mapping) and any(result.get(k) is True for k in ("run_in_background", "background", "detached")):
        return None
    if isinstance(result, Mapping) and result.get("status") == "completed":
        return "completed"
    if payload.get("hook_event_name") == "PostToolUseFailure":
        # A correlated foreground call has returned failure. Async/unknown
        # response shapes are not terminal evidence, even on failure events.
        if result is None or isinstance(result, Mapping) and result.get("status") in (None, "failed", "not_started"):
            return "failed"
    return None


def _failure_quota(payload, result):
    from apgr_workers.claude_events import classify_quota_evidence
    error = payload.get("error") or (result.get("error") if isinstance(result, Mapping) else None)
    if isinstance(error, str):
        error = {"message": error}
    return classify_quota_evidence(json.dumps({"type": "error", "error": error}))


def _retain_unreconciled(record, payload, result):
    known = {"async_launched", "background", "detached", "completed", "failed", "not_started"}
    status = result.get("status") if isinstance(result, Mapping) else None
    observations = record.setdefault("unreconciled_observations", [])
    observations.append({"event": "PostToolUseFailure" if payload.get("hook_event_name") == "PostToolUseFailure" else "PostToolUse",
                         "response_status": status if isinstance(status, str) and status in known else "unknown",
                         "interrupted": bool(payload.get("is_interrupt") or payload.get("interrupted")),
                         "observed_at": time.time()})
    del observations[:-8]


def handle_hook_post_tool(raw_input, parent_id, state_dir, capability_digest=None):
    payload = _payload(raw_input)
    if canonical_tool_name(payload.get("tool_name", "Agent")) != "Agent":
        return 0, {"continue": True}
    identity = payload.get("tool_use_id")
    if not isinstance(identity, str) or not identity:
        return 0, {"continue": True}
    ledger = _binding_ledger(parent_id, state_dir, capability_digest)
    result = payload.get("tool_response")
    terminal = _terminal_result(payload, result)
    with ledger._locked() as data:
        # Binding may change after the status read; this transaction owns the
        # terminal evidence, quota pause and capacity release together.
        _validate_binding(data, capability_digest)
        record = (data.get("native_agents") or {}).get(identity)
        if not record or record.get("status") not in ACTIVE_NATIVE_STATES:
            return 0, {"continue": True}
        if record.get("terminal_result"):
            if terminal:
                outcome = native_capacity.settle_native_sonnet(data, identity, {}, ACTIVE_NATIVE_STATES,
                    recovery={"trigger_event": payload.get("hook_event_name") or "PostToolUse",
                              "trigger_terminal": terminal,
                              "conflicting_trigger": terminal != record["terminal_result"],
                              "observed_at": time.time()})
                if outcome == "recovered" and terminal == record["terminal_result"] and record.get("error_class") == "quota_exhaustion":
                    pool = (data.get("pool_state") or {}).get("sonnet") or {}
                    # ZQ did not timestamp its terminal write. Any retained
                    # pause/resume history therefore prevents asserting that
                    # the old quota observation supersedes an operator action.
                    if pool.get("paused") is not True and not any(
                        key in pool for key in ("paused_at", "resumed_at", "resume_evidence")
                    ):
                        ledger_owner.apply_pool_pause(data, "sonnet", "explicit_quota_exhaustion",
                            {"source": "retained_native_terminal_record", "agent_id": identity,
                             "error_class": "quota_exhaustion"}, parent_id)
            return 0, {"continue": True}
        quota = None
        if payload.get("hook_event_name") == "PostToolUseFailure":
            quota = _failure_quota(payload, result)
        if quota and quota["exhausted"]:
            pool = (data.get("pool_state") or {}).get("sonnet") or {}
            record["quota_evidence"] = quota
            if pool.get("paused") is True:
                record["quota_pause"] = "pool_already_paused"
            else:
                ledger_owner.apply_pool_pause(data, "sonnet", "explicit_quota_exhaustion", quota, parent_id)
                record["quota_pause"] = "applied"
        if terminal:
            evidence = {"model_observation": _model_observation(
                            result if isinstance(result, Mapping) else {}, record.get("task_authority", "read_only")),
                        "terminal_result": terminal,
                        "terminal_evidence": "legacy_not_started" if isinstance(result, Mapping) and result.get("status") == "not_started" else "foreground_tool_return",
                        "cleanup_proven": True}
            if terminal == "failed":
                evidence["error_class"] = "quota_exhaustion" if quota and quota["exhausted"] else "provider_tool_failure"
            native_capacity.settle_native_sonnet(data, identity, evidence, ACTIVE_NATIVE_STATES)
        else:
            _retain_unreconciled(record, payload, result)
    return 0, {"continue": True}


def handle_hook_subagent_start(raw_input, parent_id, state_dir, capability_digest=None):
    # Provider SubagentStart identifiers are not tool-use identifiers. Never
    # create another slot or guess which concurrent invocation owns an event.
    _binding_ledger(parent_id, state_dir, capability_digest)
    return 0, {"continue": True}


def handle_hook_subagent_stop(raw_input, parent_id, state_dir, capability_digest=None):
    # Foreground PostToolUse is the correlated terminal evidence. A stop without
    # that response retains the reservation until observed parent-process exit.
    _binding_ledger(parent_id, state_dir, capability_digest)
    return 0, {"continue": True, "retained_until_correlated_terminal": True}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("pre-tool", "post-tool", "subagent-start", "subagent-stop"))
    parser.add_argument("--parent-id", required=True)
    parser.add_argument("--state-dir", required=True, type=Path)
    parser.add_argument("--capability-digest", required=True)
    args = parser.parse_args(argv)
    handlers = {"pre-tool": handle_hook_pre_tool, "post-tool": handle_hook_post_tool,
                "subagent-start": handle_hook_subagent_start, "subagent-stop": handle_hook_subagent_stop}
    try:
        code, result = handlers[args.action](sys.stdin.read(), args.parent_id, args.state_dir, args.capability_digest)
    except Exception as error:
        print("native hook failed: " + type(error).__name__, file=sys.stderr)
        return 2
    print(json.dumps(result))
    return code


if __name__ == "__main__":
    raise SystemExit(main())


def profile_plugin(root, facade, read_only, arguments=()):
    from claude_vc_profile import ProfileError
    try:
        options = list(arguments)
        if "--" in options:
            options = options[:options.index("--")]
        blocked = {"--safe-mode", "--bare", "--settings", "--managed-settings", "--setting-sources"}
        if (any(arg.split("=", 1)[0] in blocked for arg in options)
                or os.environ.get("CLAUDE_CODE_SAFE_MODE") == "1"
                or os.environ.get("CLAUDE_CODE_SIMPLE") == "1"):
            raise ClaudeNativeError("native worker hooks cannot compose with caller settings or hook-disabled modes")
        source = root.parent if (root.parent / "libexec").is_dir() else root
        plugin = binding_for_facade(source, facade, read_only)
        if plugin is not None and any(arg.split("=", 1)[0] in TOOL_LIST_FLAGS for arg in options):
            raise ClaudeNativeError("native parent tool selection is launcher-owned")
        return plugin
    except ValueError as error:
        raise ProfileError(str(error)) from error


def apply_profile_native_argv(argv, plugin, facade, read_only):
    if plugin is not None:
        print("claude-profile: native worker contract " + json.dumps(native_readback(
            plugin, "read_only" if read_only else "mutation_capable"), sort_keys=True), file=sys.stderr, flush=True)
        argv.extend(("--plugin-dir", str(plugin)))
        guidance = ("For native Sonnet use only " + SCOPED_AGENT_NAME
                    + " with run_in_background=false. Do not override model or effort. "
                    "For writing jobs the first prompt line must be APGR-MUTATION-SCOPE: "
                    '["repository/relative/path"], listing explicit disjoint owned paths. '
                    "Read-only jobs must not claim write scope. Native children are leaves.")
        if "--append-system-prompt" in argv:
            at = argv.index("--append-system-prompt") + 1
            argv[at] += "\n\n" + guidance
        else:
            argv.extend(("--append-system-prompt", guidance))
    elif facade is not None:
        argv.extend(("--disallowed-tools", "Agent,Task"))
    validate_profile_native_argv(argv, plugin)
