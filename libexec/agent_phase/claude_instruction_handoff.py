"""One-attempt run-owned instruction projection handoff for the Claude wrapper.

The dispatcher renders the stage projection of the wrapper root's
``CLAUDE.md`` into two exclusive mode-0600 run files (the projected body and
this handoff) and binds the handoff digest into the context plan and the
transport scope. The wrapper refuses before Claude starts unless the scope,
plan, handoff, projected body, live source, live manifest and its own read-only
capability all agree and a recomputation yields identical bytes; it then claims
the handoff once. The handoff has no tool, permission, MCP, directory or worker
field: it can only replace the standing-instruction text.
"""
from __future__ import annotations

import os
from pathlib import Path
import stat

from . import instruction_projection as ip
from .claude_context_acquisition import decode, identity
from .transmission import SCOPE_ENV, direct_bytes

OPTION = "--apgr-instruction-projection"
SCHEMA = "apg.claude-instruction-projection-handoff/v1"
HANDOFF_KEYS = frozenset({"schema", "scope", "projection", "source", "manifest", "selection"})
KEYS = ("run_id", "binding_id", "attempt_id")


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
                raise ValueError("ambiguous internal instruction projection option")
            selected = arguments[index + 1]
            index += 2
            continue
        clean.append(arg)
        index += 1
    return clean, selected


def launcher_root(launcher: str) -> Path:
    """The physical ``claude/`` root ``bin/claude-profile`` passes to the wrapper."""
    return Path(launcher).resolve(strict=True).parents[1] / "claude"


def _read(root: Path) -> tuple[bytes, bytes]:
    try:
        manifest = direct_bytes(root / ip.MANIFEST_NAME, max_bytes=ip.MAX_MANIFEST_BYTES)
    except (OSError, ValueError, UnicodeError) as error:
        raise ip.ProjectionError("instruction_manifest_unavailable", type(error).__name__) from error
    try:
        source = direct_bytes(root / ip.SOURCE_NAME, max_bytes=ip.MAX_SOURCE_BYTES)
    except (OSError, ValueError, UnicodeError) as error:
        raise ip.ProjectionError("instruction_source_unavailable", type(error).__name__) from error
    return source, manifest


def _write_exclusive(path: Path, raw: bytes) -> None:
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as error:
        raise ip.ProjectionError("instruction_projection_write_failed", type(error).__name__) from error


def prepare(record, run_dir, prefix, *, root, classes, ambient_tools, derived_from):
    """Dispatcher side. Returns ``(handoff_path, plan_view)`` or raises ``ProjectionError``."""
    from .context_adapter import canonical
    root, run_dir = Path(root), Path(run_dir)
    if root.resolve() != root or run_dir.resolve() != run_dir:
        raise ip.ProjectionError("instruction_source_unavailable", "roots must be physical")
    source_raw, manifest_raw = _read(root)
    result = ip.project(source_raw, manifest_raw, classes, {"ambient_tools": ambient_tools})
    body_path = run_dir / f"{prefix}.instruction-projection.md"
    handoff_path = run_dir / f"{prefix}.instruction-projection.json"
    source = {"path": str(root / ip.SOURCE_NAME), **result["source"]}
    manifest = {"path": str(root / ip.MANIFEST_NAME), **result["manifest"]}
    projection = {"path": str(body_path), **result["projection"], "projection_id": result["projection_id"]}
    selection = {"classes": result["classes"], "capabilities": result["capabilities"],
                 "selected": result["selected"], "omitted": result["omitted"]}
    _write_exclusive(body_path, result["body"])
    raw = canonical({"schema": SCHEMA, "scope": {k: record[k] for k in KEYS}, "projection": projection,
                     "source": source, "manifest": manifest, "selection": selection})
    _write_exclusive(handoff_path, raw)
    view = {"schema": ip.PROJECTION_SCHEMA, "status": "projected", "reason": None, "diagnostic": None,
            "selection": {**selection, "derived_from": dict(derived_from)},
            "source": source, "manifest": manifest,
            "fragments": result["fragments"], "projection": projection,
            "handoff": {"path": str(handoff_path), **identity(raw)},
            "comparison": result["comparison"], "measurement": "prospective"}
    return handoff_path, view


def _private(path: Path, max_bytes: int) -> bytes:
    raw = direct_bytes(path, utf8=False, max_bytes=max_bytes)
    if stat.S_IMODE(path.lstat().st_mode) != 0o600:
        raise ValueError("instruction projection input must be mode 0600")
    return raw


def consume(path, environment, *, root, ambient_tools) -> dict:
    """Wrapper side: validate every binding, recompute, claim once."""
    scope = decode(environment.get(SCOPE_ENV, "{}"))
    if not isinstance(scope, dict) or not isinstance(scope.get("instruction_projection"), dict):
        raise ValueError("missing APGR instruction projection scope")
    path, root = Path(path), Path(root)
    raw = _private(path, 1 << 20)
    if scope["instruction_projection"] != {"path": str(path), **identity(raw)}:
        raise ValueError("instruction projection handoff digest mismatch")
    value = decode(raw)
    if (not isinstance(value, dict) or set(value) != HANDOFF_KEYS or value["schema"] != SCHEMA
            or value["scope"] != scope.get("record")):
        raise ValueError("invalid instruction projection handoff contract")
    plan_path = Path(scope["path"])
    plan_raw = direct_bytes(plan_path)
    plan = decode(plan_raw)
    view = plan.get("instruction_projection") or {}
    if (plan_path.parent != path.parent or identity(plan_raw)["sha256"] != scope.get("reference", {}).get("sha256")
            or {k: plan.get(k) for k in KEYS} != value["scope"]
            or plan.get("requested_mode") != "adaptive" or plan.get("effective_mode") != "adaptive"
            or view.get("status") != "projected" or view.get("handoff") != {"path": str(path), **identity(raw)}):
        raise ValueError("instruction projection plan/scope mismatch")
    if (value["source"]["path"] != str(root / ip.SOURCE_NAME)
            or value["manifest"]["path"] != str(root / ip.MANIFEST_NAME)):
        raise ValueError("instruction projection source is not this launcher's root")
    body_path = Path(value["projection"]["path"])
    if body_path.parent != path.parent:
        raise ValueError("instruction projection body is outside the run")
    body = _private(body_path, ip.MAX_SOURCE_BYTES)
    selection = value["selection"]
    if selection.get("capabilities") != {"ambient_tools": ambient_tools}:
        raise ValueError("instruction projection capability differs from this launch")
    source_raw, manifest_raw = _read(root)
    result = ip.project(source_raw, manifest_raw, selection.get("classes"), {"ambient_tools": ambient_tools})
    if ({"path": value["source"]["path"], **result["source"]} != value["source"]
            or {"path": value["manifest"]["path"], **result["manifest"]} != value["manifest"]):
        raise ValueError("instruction projection source or manifest changed after preparation")
    expected = {"path": str(body_path), **result["projection"], "projection_id": result["projection_id"]}
    if (result["body"] != body or value["projection"] != expected
            or [result["selected"], result["omitted"]] != [selection.get("selected"), selection.get("omitted")]):
        raise ValueError("instruction projection body differs from a recomputation")
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
    return {"body": body.decode("utf-8"), "classes": result["classes"], "omitted": result["omitted"],
            "projection": {**result["projection"], "projection_id": result["projection_id"]},
            "source": result["source"], "source_text": source_raw.decode("utf-8")}
