#!/usr/bin/env python3
"""Deterministic non-model fixture for the APGR native Codex argv contract."""
import json
import sys
import time
from pathlib import Path


def main():
    task = json.loads(sys.stdin.buffer.read().splitlines()[0])
    operation = task.get("operation", "success")
    if operation == "timeout":
        time.sleep(60)
    if operation == "nonzero":
        return 7
    if operation == "side-effect":
        Path("side-effect.txt").write_text("one invocation\n")
        return 7
    if operation == "evidence-symlink":
        Path("../run/provider.stdout").symlink_to(Path("source.txt").absolute())
    if operation == "malformed":
        print("not a provider result")
        return 0
    if operation in ("acquire", "recover"):
        declaration = next((a for a in sys.argv if a.startswith("mcp_servers.apgr=")), None)
        if declaration:
            import tomllib
            import subprocess
            launch = tomllib.loads(declaration)["mcp_servers"]["apgr"]
            config_path = Path(launch["args"][launch["args"].index("--config") + 1])
            authority = json.loads(config_path.read_bytes())
            if operation == "acquire":
                messages = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                    "protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "instrumented", "version": "1"}}},
                    {"jsonrpc": "2.0", "method": "notifications/initialized"},
                    {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
                        "name": "skill_acquire", "arguments": {"id": authority["allowed_ids"][0]}}}]
                subprocess.run([launch["command"], *launch["args"]],
                               input=b"".join((json.dumps(m)+"\n").encode() for m in messages),
                               capture_output=True, check=True, timeout=10)
            else:
                from agent_phase.acquisition_records import read_recovery, recovery_observation
                prepared = {"path": Path(authority["run_dir"]) / "attempt.context-plan.json", "record": authority["context_plan"]}
                recovery_observation(prepared, "mcp_failed", evidence="instrumented channel failure")
                read_recovery(prepared, authority["context_plan"]["acquisition"]["recovery"][0]["path"], len)
    print(json.dumps({"schema": "apg.instrumented-provider/v1", "model": "instrumented-model",
                      "producer_revisions": [], "missing_guidance_findings": [],
                      "restart_required_incidents": [], "model_observed": None}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
