"""Ordinary one-attempt context-acquisition handoff for the Claude wrapper.

The dispatcher creates the handoff after the run-owned MCP authority and final
plan record exist; the wrapper validates it against the digest in the existing
transport scope, claims it once, and composes the ``apgr`` server beside any
worker facade. It adds only the three existing APGR MCP tool names and exact
``Read(//file)`` permissions for prepared recovery copies. It never grants
shell, write or directory authority and is independent of the evaluation-only
``--apgr-acquisition-handoff`` contract, which is unchanged.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat

from .acquisition_records import _pairs
from .transmission import SCOPE_ENV, direct_bytes

OPTION = "--apgr-context-acquisition"
SCHEMA = "apg.claude-context-acquisition/v1"
TOOLS = ["mcp__apgr__skill_search", "mcp__apgr__skill_acquire", "mcp__apgr__context_explain"]
KEYS = ("run_id", "binding_id", "attempt_id")
SERVER_NAME = "apgr"
_UNREPRESENTABLE = ",()[]*?"


def identity(raw: bytes) -> dict:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def decode(raw):
    return json.loads(raw, object_pairs_hook=_pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("invalid constant")))


def representable(path: str) -> bool:
    """Same exact-rule restriction as the agent-worker source Read grant."""
    return Path(path).is_absolute() and not any(c.isspace() or c in _UNREPRESENTABLE for c in path)


def read_rule(path: str) -> str:
    return f"Read(/{path})"


def split_option(arguments):
    """Strip the wrapper-private option once, before any ``--`` task marker."""
    clean, selected = [], None
    index = 0
    while index < len(arguments):
        arg = arguments[index]
        if arg == "--":
            clean.extend(arguments[index:])
            break
        if arg.split("=", 1)[0] == OPTION:
            if selected is not None or "=" in arg or index + 1 == len(arguments):
                raise ValueError("ambiguous internal context acquisition option")
            selected = arguments[index + 1]
            index += 2
            continue
        clean.append(arg)
        index += 1
    return clean, selected


def _private(path: Path, *, max_bytes: int = 1 << 20) -> bytes:
    raw = direct_bytes(path, max_bytes=max_bytes)
    if stat.S_IMODE(path.lstat().st_mode) != 0o600:
        raise ValueError("context acquisition input must be mode 0600")
    return raw


def create(path, record, *, config: Path, binary: Path, server: list[str]) -> None:
    """Called last in plan finalization; the plan record must not change after."""
    from .context_adapter import canonical
    path, config, binary = Path(path), Path(config), Path(binary)
    if path.parent.resolve() != path.parent or config.parent != path.parent:
        raise ValueError("context acquisition handoff must be physically run-owned")
    recovery = []
    for row in record["acquisition"]["recovery"]:
        location = Path(row["absolute_path"])
        data = direct_bytes(location, utf8=False, max_bytes=1 << 20)
        if identity(data) != {"bytes": row["bytes"], "sha256": row["sha256"]}:
            raise ValueError("recovery copy differs from preparation")
        recovery.append({"id": row["id"], "path": str(location), **identity(data)})
    value = {"schema": SCHEMA, "scope": {k: record[k] for k in KEYS},
             "plan": identity(canonical(record)),
             "server": {"type": "stdio", "command": server[0], "args": server[1:]},
             "server_config": {"path": str(config), **identity(_private(config))},
             "binary": {"path": str(binary), **identity(direct_bytes(binary, utf8=False, max_bytes=128 << 20))},
             "tools": list(TOOLS), "recovery": recovery}
    raw = canonical(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def consume(path, environment) -> dict:
    """Validate the handoff against the attempt scope and claim it once."""
    scope = decode(environment.get(SCOPE_ENV, "{}"))
    if not isinstance(scope, dict) or not isinstance(scope.get("context_acquisition"), dict):
        raise ValueError("missing APGR context acquisition scope")
    path = Path(path)
    raw = _private(path)
    if scope["context_acquisition"] != {"path": str(path), **identity(raw)}:
        raise ValueError("context acquisition handoff digest mismatch")
    value = decode(raw)
    if (set(value) != {"schema", "scope", "plan", "server", "server_config", "binary", "tools", "recovery"}
            or value["schema"] != SCHEMA or value["tools"] != TOOLS or value["scope"] != scope.get("record")):
        raise ValueError("invalid context acquisition handoff contract")
    plan_path = Path(scope["path"])
    plan_raw = direct_bytes(plan_path)
    plan = decode(plan_raw)
    if (plan_path.parent != path.parent or identity(plan_raw) != value["plan"]
            or scope.get("reference", {}).get("sha256") != value["plan"]["sha256"]
            or {k: plan.get(k) for k in KEYS} != value["scope"]
            or plan.get("requested_mode") != "adaptive" or plan.get("effective_mode") != "adaptive"
            or plan.get("acquisition", {}).get("context_handoff") != str(path)):
        raise ValueError("context acquisition plan/scope mismatch")
    config = value["server_config"]
    config_path = Path(config["path"])
    if (config_path.parent != path.parent or set(config) != {"path", "bytes", "sha256"}
            or config != {"path": str(config_path), **identity(_private(config_path, max_bytes=1 << 20))}):
        raise ValueError("context acquisition server config mismatch")
    binary = value["binary"]
    binary_path = Path(binary["path"])
    if (binary != {"path": str(binary_path), **identity(direct_bytes(binary_path, utf8=False, max_bytes=128 << 20))}
            or not os.access(binary_path, os.X_OK)):
        raise ValueError("context acquisition executable changed")
    if value["server"] != {"type": "stdio", "command": str(binary_path),
                           "args": ["mcp", "serve", "--config", str(config_path)]}:
        raise ValueError("unrelated MCP server or command")
    root = path.parent / "acquisitions" / "skills"
    for row in value["recovery"]:
        location = Path(row["path"])
        if (set(row) != {"id", "path", "bytes", "sha256"} or not representable(str(location))
                or root not in location.parents
                or identity(direct_bytes(location, utf8=False, max_bytes=1 << 20)) != {"bytes": row["bytes"], "sha256": row["sha256"]}):
            raise ValueError("recovery copy is outside the run or changed")
    parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fd = os.open(path.name + ".consumed", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=parent)
        with os.fdopen(fd, "wb") as stream:
            stream.write(identity(raw)["sha256"].encode())
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(parent)
    return {"server": value["server"], "tools": list(TOOLS),
            "read_rules": [read_rule(row["path"]) for row in value["recovery"]],
            "summary": {"server": SERVER_NAME, "tools": list(TOOLS),
                        "recovery_reads": len(value["recovery"]), "handoff": path.name}}


def merge_mcp(existing: str | None, server: dict) -> str:
    """One --mcp-config value: the facade's servers (if any) plus ``apgr``."""
    payload = json.loads(existing) if existing else {"mcpServers": {}}
    servers = payload.get("mcpServers")
    if not isinstance(servers, dict) or SERVER_NAME in servers:
        raise ValueError("MCP configuration cannot compose the apgr server")
    servers[SERVER_NAME] = dict(server)
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)
