"""Evaluation-only opt-in through the actual profile/runner; no launch replay."""
from pathlib import Path

from agent_phase.claude_read_observer import capture_recovery, decode, direct_bytes, identity, observe, MAX_LOG
from agent_phase.context_adapter import _write_new


def prepare(prepared, argv, *, qualification=None):
    if prepared.get("invoked") or prepared.get("claude_read_stream"):
        raise ValueError("native Read observation must be enabled once before launch")
    if Path(argv[0]).name != "claude-profile" or "--read-only" not in argv or "-p" not in argv:
        raise ValueError("native Read observation requires Claude read-only profile builder")
    forbidden = ("--live-log", "--live-display", "--output-format", "--resume", "--continue")
    if any(a.split("=", 1)[0] in forbidden for a in argv):
        raise ValueError("ambiguous native Read launch")
    path = prepared["path"].with_suffix(".claude-stream.jsonl")
    if path.exists() or path.is_symlink() or path.with_suffix(".complete.json").exists():
        raise ValueError("raw stream exists; replay refused")
    captured = capture_recovery(prepared)
    from agent_phase.claude_acquisition_custody import capture_prepared
    prepared["claude_acquisition_custody"] = capture_prepared(prepared)
    prepared["evaluation_transport"] = True
    prepared["claude_read_stream"] = str(path)
    prepared["claude_read_capture"] = captured
    prepared["claude_read_qualification"] = qualification
    return [*argv, "--live-log", str(path), "--live-display", "raw"]


def collect(prepared, returned):
    from agent_phase.claude_acquisition_custody import verify_after
    if (prepared["record"].get("acquisition", {}).get("wrapper_handoff")
            and not isinstance(prepared.get("claude_acquisition_custody"), dict)):
        raise ValueError("missing prelaunch acquisition custody")
    custody = verify_after(prepared, prepared.get("claude_acquisition_custody"))
    if returned.exit_code != 0 or returned.truncated:
        raise ValueError("incomplete Claude runner result")
    path = Path(prepared["claude_read_stream"])
    raw = direct_bytes(path, max_bytes=MAX_LOG)
    receipt = decode(direct_bytes(path.with_suffix(".complete.json")))
    scope = {k: prepared["record"][k] for k in ("run_id", "binding_id", "attempt_id")}
    expected = {"schema": "apg.claude-stream-completion/v2", "plan": prepared["reference"],
                "scope": scope, "raw_stream": identity(raw), "durable": True,
                "stream_enabled_before_start": True, "process_status": 0}
    if receipt != expected or returned.stdout != raw:
        raise ValueError("raw stream durability or runner binding mismatch")
    observation = observe(raw, expected_sha256=receipt["raw_stream"]["sha256"],
                          captured=prepared["claude_read_capture"], scope=scope)
    if custody is not None:
        observation["acquisition_custody"] = custody
    qualification = prepared.get("claude_read_qualification")
    internal = bool(prepared["record"].get("acquisition", {}).get("wrapper_handoff"))
    if qualification is not None or internal:
        initial = [decode(line) for line in raw.splitlines() if decode(line).get("type") == "system" and decode(line).get("subtype") == "init"]
        if internal:
            from agent_phase.claude_acquisition_handoff import TOOLS
            if (len(initial) != 1
                    or initial[0].get("permissionMode") != "default"
                    or sorted(initial[0].get("tools", [])) != sorted(["Read", *TOOLS])
                    or initial[0].get("mcp_servers") != [{"name": "apgr", "status": "connected", "source": "dynamic"}]):
                raise ValueError("runtime acquisition tool/server/permission set differs from handoff")
        if qualification is not None and (len(initial) != 1 or initial[0].get("claude_code_version") != qualification["cli_version"]
                or initial[0].get("model") != qualification["model"]
                or initial[0].get("permissionMode") != ("default" if prepared["record"].get("acquisition", {}).get("wrapper_handoff") else "plan")
                or "Read" not in initial[0].get("tools", [])
                or {"Bash", "Write", "Edit", "Agent"} & set(initial[0].get("tools", []))):
            raise ValueError("runtime differs from qualified native Read binding")
    _write_new(path.with_suffix(".observation.json"), observation)
    return observation
