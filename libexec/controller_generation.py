"""Dispatcher generation leases. Records never contain argv or provider payloads."""
from __future__ import annotations

import atexit
import json
import os
from pathlib import Path
import stat
import time

from controller_generation_process import process_identity
from controller_generation_store import coordinate, validate_generation

SCHEMA = "controller-generation-lease-v1"
LEASE_ENV = "AGENT_CENTRAL_GENERATION_LEASE"
MAX_RECORD = 64 * 1024
STARTUP_LOCK_TIMEOUT = 300.0
_current: dict | None = None
_lease: Path | None = None
_development: dict | None = None


class GenerationError(RuntimeError):
    pass


class LeaseRetirementRequired(GenerationError):
    """An extinct incarnation requires explicit child-custody disposition."""


def read_record(path: Path) -> dict:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077 or info.st_size > MAX_RECORD):
            raise GenerationError("unsafe generation record")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(MAX_RECORD + 1)
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise GenerationError("duplicate generation record field")
                result[key] = value
            return result
        value = json.loads(raw, object_pairs_hook=unique)
        if not isinstance(value, dict):
            raise GenerationError("invalid generation record")
        return value
    finally:
        os.close(fd)


def write_record(path: Path, record: dict) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(record, stream, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def lease_directory(store: Path) -> Path:
    path = store / "leases"
    path.mkdir(mode=0o700, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise GenerationError("unsafe lease directory")
    return path


def create_lease(store: Path, generation: dict) -> Path:
    pid = os.getpid()
    identity = process_identity(pid)
    if identity is None:
        raise GenerationError("dispatcher process birth identity unavailable")
    path = lease_directory(store) / f"{pid}.json"
    if os.path.lexists(path):
        previous = read_record(path)
        if previous.get("status") != "finished" or previous.get("process_identity") == identity:
            raise LeaseRetirementRequired("existing lease requires agent-controller-generation retire-lease")
    write_record(path, {"schema": SCHEMA, "pid": pid, "process_identity": identity,
                        "created_at": time.time(), "run_id": None,
                        "status": "starting", "generation": generation})
    return path


def activate(root: Path, path: Path) -> None:
    global _current, _lease
    record = read_record(path)
    generation = record.get("generation", {})
    controller = Path(generation["controller_root"])
    with coordinate(controller, timeout=STARTUP_LOCK_TIMEOUT) as store:
        expected = lease_directory(store) / f"{os.getpid()}.json"
        if path != expected or root != Path(generation["generation_root"]):
            raise GenerationError("dispatcher generation root mismatch")
        if (record.get("schema") != SCHEMA or record.get("pid") != os.getpid()
                or record.get("process_identity") != process_identity(os.getpid())
                or record.get("status") != "starting"):
            raise GenerationError("dispatcher lease identity mismatch")
        validate_generation(generation, store)
        record["status"] = "running"
        write_record(path, record)
    _current, _lease = record, path
    atexit.register(finish)


def provenance(run_id: str | None = None) -> dict | None:
    if _current is None:
        return {**_development, "run_id": run_id} if _development is not None else None
    if run_id is not None and _current["run_id"] != run_id:
        _current["run_id"] = run_id
        write_record(_lease, _current)
    return {**_current["generation"], "pid": _current["pid"],
            "process_identity": _current["process_identity"],
            "created_at": _current["created_at"], "run_id": _current["run_id"]}


def observe_development(root: Path) -> None:
    """Record worktree execution explicitly; never advertise a safety lease."""
    global _development
    import subprocess
    values = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD", "HEAD^{tree}"],
                                     text=True).splitlines()
    _development = {"schema": "controller-generation-v1", "commit": values[0],
                    "tree": values[1], "controller_root": str(root),
                    "generation_root": None, "safety_established": False,
                    "reason": "source_development_worktree", "pid": os.getpid(),
                    "process_identity": process_identity(os.getpid()), "created_at": time.time()}


def finish() -> None:
    if _current is not None and _lease is not None:
        _current["status"] = "finished" if _current.get("run_complete") is True else "exited"
        try:
            write_record(_lease, _current)
        except OSError:
            pass  # A crash/stale record never becomes a live safe lease.


def note_state(payload: dict) -> None:
    if _current is not None:
        _current["run_complete"] = payload.get("complete") is True
        write_record(_lease, _current)


def binding_for_root(root: Path) -> dict | None:
    """Read inherited generation context for managed child wrappers, not liveness."""
    path = os.environ.get(LEASE_ENV)
    if not path:
        return None
    generation = read_record(Path(path)).get("generation", {})
    return generation if str(root) == generation.get("generation_root") else None


def operator_root(root: Path) -> Path:
    generation = binding_for_root(root)
    return Path(generation["controller_root"]) if generation else root


def codex_profile_arguments(root: Path, profile: str) -> list[str]:
    """Freeze source profile values while leaving vendor auth/base policy live."""
    if binding_for_root(root) is None:
        return ["--profile", profile]
    import re
    import tomllib
    if not re.fullmatch(r"[A-Za-z0-9_-]+", profile):
        raise GenerationError("invalid source profile")
    value = tomllib.loads((root / "codex/profiles" / f"{profile}.config.toml").read_text())
    result = []
    def flatten(table, prefix=""):
        for key, item in table.items():
            if not re.fullmatch(r"[A-Za-z0-9_-]+", key):
                raise GenerationError("invalid profile key")
            name = f"{prefix}.{key}" if prefix else key
            if isinstance(item, dict):
                flatten(item, name)
            elif isinstance(item, (str, bool, int)):
                result.extend(["-c", name + "=" + json.dumps(item)])
            else:
                # Source profiles currently use scalar strings, booleans and
                # integers only. New TOML types need explicit CLI serialization
                # and equivalence tests; never silently fall back to live profiles.
                raise GenerationError("unsupported pinned profile value")
    flatten(value)
    return result


def inspect_leases(store: Path) -> dict:
    """Unknown/malformed/reused identities block; dead records are only stale."""
    result = {"safe": [], "stale": [], "blockers": []}
    validated = set()
    paths = sorted(lease_directory(store).iterdir())
    if len(paths) > 4096:
        raise GenerationError("lease inventory exceeds bound")
    for path in paths:
        if not path.name.endswith(".json") or not path.stem.isdecimal():
            result["blockers"].append({"reason": "unexpected_lease_entry"})
            continue
        pid = int(path.stem)
        try:
            record = read_record(path)
            if (record.get("schema") != SCHEMA or record.get("pid") != pid
                    or not isinstance(record.get("process_identity"), str)
                    or not isinstance(record.get("generation"), dict)):
                raise GenerationError("invalid_lease")
            observed = process_identity(pid)
            if observed is None:
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    result["stale"].append({"pid": pid, "reason": "dead_process",
                        "status": record.get("status"),
                        "commit": record.get("generation", {}).get("commit")})
                    continue
                raise GenerationError("process_identity_unreadable")
            if observed != record["process_identity"]:
                raise GenerationError("process_identity_mismatch")
            if record.get("status") not in {"starting", "running"}:
                raise GenerationError("non_running_live_lease")
            generation = record.get("generation", {})
            if generation.get("safety_established") is not True:
                raise GenerationError("generation_not_safe")
            key = json.dumps(generation, sort_keys=True)
            if key not in validated:
                validate_generation(generation, store)
                validated.add(key)
            result["safe"].append({"pid": pid, "status": record["status"],
                                   "commit": generation["commit"], "tree": generation["tree"],
                                   "generation_root": generation["generation_root"],
                                   "process_identity": observed})
        except (OSError, ValueError, KeyError, TypeError, RuntimeError):
            result["blockers"].append({"pid": pid, "reason": "lease_validation_failed"})
    return result
