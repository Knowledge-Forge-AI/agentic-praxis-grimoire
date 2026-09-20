"""Provider-free generation status and explicit, conservative garbage collection."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess

from controller_generation import GenerationError, SCHEMA, inspect_leases, lease_directory, read_record
from controller_generation_process import identity_supersedes, process_identity
from controller_generation_store import (
    coordinate, no_symlinks, validate_generation, _safe_remove_tree,
)


def inventory(store: Path) -> list[dict]:
    objects = store / "objects"
    if not objects.exists():
        return []
    no_symlinks(objects)
    paths = list(objects.iterdir())
    if len(paths) > 512:
        raise GenerationError("generation inventory exceeds bound")
    result = []
    for path in paths:
        if not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", path.name):
            raise GenerationError("unexpected generation entry; manual inspection required")
        record = read_record(store / "records" / (path.name + ".json"))
        validate_generation(record, store)
        result.append({"record": record, "retained_at": path.stat().st_mtime_ns})
    return sorted(result, key=lambda item: item["retained_at"], reverse=True)


def inspect(root: Path, *, gc: bool = False, apply: bool = False, keep: int = 3) -> dict:
    if keep < 3:
        raise GenerationError("keep must be at least three")
    root = root.resolve(strict=True)
    with coordinate(root) as store:
        leases = inspect_leases(store)
        if leases["blockers"]:
            raise GenerationError("ambiguous leases prevent generation administration")
        head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
        items = inventory(store)
        protected = {head, *(item["commit"] for item in leases["safe"])}
        # A crashed dispatcher could have surviving children. Retain its code
        # without pretending PID death proves provider/worker cleanup.
        protected.update(item["commit"] for item in leases["stale"] if item["status"] != "finished")
        protected.update(item["record"]["commit"] for item in items[:keep])
        candidates = [item["record"] for item in items if item["record"]["commit"] not in protected]
        report = {"schema": "controller-generation-status-v1", "active_commit": head,
                  "leases": leases, "generations": [item["record"]["commit"] for item in items],
                  "provider_invocations": 0, "gc": {"apply": gc and apply,
                      "keep": keep, "eligible": [item["commit"] for item in candidates], "deleted": []}}
        if gc and apply:
            _delete(store, candidates, report)
            for item in leases["stale"]:
                if item["status"] == "finished":
                    (store / "leases" / f"{item['pid']}.json").unlink()
        return report


def _delete(store: Path, candidates: list[dict], report: dict) -> None:
    for record in candidates:
        commit = record["commit"]
        target = store / "objects" / commit
        if str(target) != record["generation_root"] or target.parent != store / "objects":
            raise GenerationError("GC exact-root mismatch")
        validate_generation(record, store)
        _safe_remove_tree(target)
        (store / "records" / (commit + ".json")).unlink()
        (store / "manifests" / (commit + ".json")).unlink()
        report["gc"]["deleted"].append(commit)


def retire_lease(root: Path, pid: int, identity: str, *, apply: bool = False,
                 confirm_child_cleanup: bool = False) -> dict:
    """Retire one extinct incarnation after explicit operator child-custody confirmation.

    This path deliberately precedes whole-store inspection: an unrelated recycled
    PID must not make the only recovery command inaccessible. No generation is
    deleted here, and no current process receives a safety assertion.
    """
    if type(pid) is not int or pid <= 0 or not identity:
        raise GenerationError("invalid lease identity")
    if apply and not confirm_child_cleanup:
        raise GenerationError("explicit child cleanup confirmation is required")
    with coordinate(root.resolve(strict=True)) as store:
        path = lease_directory(store) / f"{pid}.json"
        record = read_record(path)
        if (record.get("schema") != SCHEMA or record.get("pid") != pid
                or record.get("process_identity") != identity
                or not isinstance(record.get("generation"), dict)):
            raise GenerationError("lease identity does not match requested retirement")
        observed = process_identity(pid)
        if observed == identity:
            raise GenerationError("leased process is still alive")
        if observed is None:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                reason = "dead_process"
            else:
                raise GenerationError("process identity is unreadable")
        elif identity_supersedes(pid, identity, observed):
            reason = "replaced_process"
        else:
            raise GenerationError("process identity is ambiguous")
        if apply:
            # Recheck the selected record under the shared startup/GC lock.
            if read_record(path) != record:
                raise GenerationError("lease changed during retirement")
            path.unlink()
        return {"schema": "controller-generation-retirement-v1", "pid": pid,
                "status": "retired" if apply else "eligible", "reason": reason,
                "child_cleanup_confirmed": confirm_child_cleanup,
                "provider_invocations": 0}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("command", choices=("status", "gc", "retire-lease"))
    parser.add_argument("--controller-root", type=Path, required=True)
    parser.add_argument("--apply", action="store_true", help="apply gc or one lease retirement")
    parser.add_argument("--keep", type=int, default=3)
    parser.add_argument("--pid", type=int)
    parser.add_argument("--identity", help="exact birth identity from the selected private lease")
    parser.add_argument("--confirm-child-cleanup", action="store_true",
                        help="operator has verified all children of the extinct lease are finished")
    args = parser.parse_args()
    if args.apply and args.command == "status":
        parser.error("--apply requires gc or retire-lease")
    if args.command == "retire-lease" and (args.pid is None or args.identity is None):
        parser.error("retire-lease requires --pid and --identity")
    if args.command != "retire-lease" and (args.pid is not None or args.identity is not None
                                          or args.confirm_child_cleanup):
        parser.error("lease selection and cleanup confirmation require retire-lease")
    try:
        if args.command == "retire-lease":
            result = retire_lease(args.controller_root, args.pid, args.identity,
                                  apply=args.apply, confirm_child_cleanup=args.confirm_child_cleanup)
        else:
            result = inspect(args.controller_root, gc=args.command == "gc", apply=args.apply, keep=args.keep)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(json.dumps({"schema": "controller-generation-status-v1", "status": "blocked",
                          "error": type(error).__name__, "provider_invocations": 0}))
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0
