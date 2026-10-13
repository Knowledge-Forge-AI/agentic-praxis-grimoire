"""Wrapper-owned, one-attempt APGR MCP handoff; never a general argv override.

The trusted acquisition owner creates the file. The process owner supplies its
digest in the existing transport scope. This is an internal same-user contract,
not authentication against an operator able to replace APGR source/environment.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat

from .acquisition_records import _pairs
from .transmission import SCOPE_ENV, direct_bytes

OPTION = "--apgr-acquisition-handoff"
SCHEMA = "apg.claude-acquisition-handoff/v2"
TOOLS = ["mcp__apgr__skill_search", "mcp__apgr__skill_acquire", "mcp__apgr__context_explain"]
KEYS = ("run_id", "binding_id", "attempt_id")


def identity(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def decode(raw):
    return json.loads(raw, object_pairs_hook=_pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("invalid constant")))


def split_option(arguments):
    """Strip the private wrapper option, rejecting duplicates and task placement."""
    clean, selected = [], None
    index = 0
    while index < len(arguments):
        arg = arguments[index]
        if arg.split("=", 1)[0] == OPTION:
            if selected is not None or "--" in clean or "=" in arg or index + 1 == len(arguments):
                raise ValueError("ambiguous internal acquisition option")
            selected = arguments[index + 1]
            index += 2
        else:
            clean.append(arg)
            index += 1
    return clean, selected


def _private(path):
    raw = direct_bytes(path, max_bytes=1 << 20)
    if stat.S_IMODE(Path(path).lstat().st_mode) != 0o600:
        raise ValueError("handoff input must be mode 0600")
    return raw


def create(path, record, config, binary):
    """Called only after acquisition authority and final plan content exist."""
    from .context_adapter import canonical
    path, config, binary = Path(path), Path(config), Path(binary)
    if path.parent.resolve() != path.parent or config.parent != path.parent:
        raise ValueError("handoff must be physically run-owned")
    from .claude_recovery_authority import verify
    recovery = verify(path.parent, record["acquisition"]["recovery_authority"])
    value = {"schema": SCHEMA, "scope": {k: record[k] for k in KEYS},
             "plan": identity(canonical(record)), "config": {"path": str(config), **identity(_private(config))},
             "binary": {"path": str(binary), **identity(direct_bytes(binary, utf8=False, max_bytes=128 << 20))},
             "tools": ["Read", *TOOLS], "allowed_tools": TOOLS,
             "recovery_authority": recovery}
    raw = canonical(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def consume(path, environment):
    """Validate exact plan/config/authority and claim the attempt before launch."""
    scope = decode(environment.get(SCOPE_ENV, "{}"))
    if not isinstance(scope, dict) or not scope.get("handoff"):
        raise ValueError("missing APGR acquisition scope")
    path = Path(path)
    raw = _private(path)
    if scope["handoff"] != {"path": str(path), **identity(raw)}:
        raise ValueError("acquisition handoff digest mismatch")
    value = decode(raw)
    if (set(value) != {"schema", "scope", "plan", "config", "binary", "tools", "allowed_tools", "recovery_authority"}
            or value["schema"] != SCHEMA or value["tools"] != ["Read", *TOOLS]
            or value["allowed_tools"] != TOOLS or value["scope"] != scope.get("record")):
        raise ValueError("invalid acquisition handoff contract")
    plan_path = Path(scope["path"])
    plan_raw = direct_bytes(plan_path)
    plan = decode(plan_raw)
    reference = scope["reference"]
    if (path.parent != plan_path.parent or reference.get("path") != plan_path.name
            or identity(plan_raw) != value["plan"]
            or any(reference.get(k) != v for k, v in identity(plan_raw).items())
            or value["scope"] != {k: plan[k] for k in KEYS}
            or plan.get("requested_mode") != "adaptive" or plan.get("effective_mode") != "adaptive"
            or plan.get("acquisition", {}).get("wrapper_handoff") != str(path)):
        raise ValueError("acquisition handoff plan/scope mismatch")
    config = value["config"]
    config_path = Path(config["path"])
    config_raw = _private(config_path)
    if (config_path.parent != path.parent or set(config) != {"path", "bytes", "sha256"}
            or config != {"path": str(config_path), **identity(config_raw)}):
        raise ValueError("acquisition MCP config mismatch")
    binary = value["binary"]
    binary_path = Path(binary["path"])
    if (binary != {"path": str(binary_path), **identity(direct_bytes(binary_path, utf8=False, max_bytes=128 << 20))}
            or not os.access(binary_path, os.X_OK)):
        raise ValueError("acquisition executable changed")
    server = Path(plan["acquisition"]["config"])
    expected = {"mcpServers": {"apgr": {"command": str(binary_path),
                "args": ["mcp", "serve", "--config", str(server)]}}}
    if decode(config_raw) != expected or server.parent != path.parent:
        raise ValueError("unrelated MCP server or command")
    authority = decode(_private(server))
    if (authority.get("context_plan") != plan or authority.get("consumer") != "claude"
            or authority.get("run_dir") != str(path.parent)
            or any(authority.get(k) != value["scope"][k] for k in KEYS)
            or authority.get("preparation", False) is not False):
        raise ValueError("MCP authority mismatch")
    from .claude_recovery_authority import verify
    if value["recovery_authority"] != plan["acquisition"].get("recovery_authority"):
        raise ValueError("recovery authority differs from plan")
    verify(path.parent, value["recovery_authority"])
    # Direct parent descriptor prevents a symlink leaf and exclusive creation
    # makes a failed/abandoned attempt non-replayable too.
    parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fd = os.open(path.name + ".consumed", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=parent)
        with os.fdopen(fd, "wb") as stream:
            stream.write(identity(raw)["sha256"].encode())
            stream.flush()
            os.fsync(stream.fileno())
        os.fsync(parent)
    finally:
        os.close(parent)
    from .claude_acquisition_custody import retain_before
    retain_before(path, value, plan_path, server)
    return value
