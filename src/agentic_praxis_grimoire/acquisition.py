"""Python configuration capture for the native, shared acquisition channels."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import fcntl
import hashlib
import stat
import re

if __package__:
    from . import go_bridge
    from .skill_catalog import capture_catalog


def run_channel(family, action, arguments, options):
    # Captured authority is also accepted directly for per-run provider launch.
    # Prelaunch preparation (``skills acquire TARGET --prepare-only ...``) is a
    # native-only shape and is forwarded verbatim to the same native parser.
    prepare_only = family == "skills" and action == "acquire" and list(arguments[1:2]) == ["--prepare-only"]
    if "--config" in arguments or prepare_only:
        return go_bridge.run([family, action, *arguments], repository_root=None)
    parser = argparse.ArgumentParser(prog=f"apgr {family} {action}")
    if family == "skills":
        parser.add_argument("target")
    for field in ("run-dir", "run-id", "binding-id", "attempt-id"):
        parser.add_argument("--" + field, required=True)
    parser.add_argument("--consumer", choices=("codex", "claude", "go_library", "chatgpt"), default="go_library")
    parser.add_argument("--project-root", default=options.get("project_root"))
    parser.add_argument("--apgr-home", default=options.get("apgr_home"))
    parser.add_argument("--start", type=Path, default=Path.cwd())
    args = parser.parse_args(arguments)
    catalog, capture_argv = capture_catalog(args.start, args.project_root, args.apgr_home)
    authority = {"run_dir": args.run_dir, "run_id": args.run_id,
                 "binding_id": args.binding_id, "attempt_id": args.attempt_id,
                 "consumer": args.consumer, "catalog": catalog}
    for option, field in (("--project-root", "project_root"), ("--apgr-home", "apgr_home")):
        if option in capture_argv:
            authority[field] = capture_argv[capture_argv.index(option) + 1]
    run = Path(args.run_dir)
    if not run.is_absolute():
        raise ValueError("acquisition requires an absolute existing run directory")
    name = retain_authority(run, authority)
    native = [family, action]
    if family == "skills":
        native.append(args.target)
    return go_bridge.run([*native, "--config", str(run / name)], repository_root=None)


MAX_AUTHORITIES = 64
MAX_AUTHORITY_BYTES = 1 << 20


def retain_authority(run, authority, *, alias=None):
    """Retain immutable content-addressed authority, at most 64 MiB per run.

    No canonical record is removed. A single unpublished staging inode is reused
    under the run lock, so termination at any write boundary adds at most one
    bounded pending file. Existing legacy UUID records count against the limit.
    """
    if alias is not None and not re.fullmatch(r"acquisition-server-[0-9a-f]{64}\.json", alias):
        raise ValueError("invalid acquisition authority alias")
    if Path(run).resolve() != Path(run):
        raise ValueError("acquisition authority requires a physical absolute root")
    raw = (json.dumps(authority, sort_keys=True) + "\n").encode("utf-8")
    if len(raw) > MAX_AUTHORITY_BYTES:
        raise ValueError("acquisition authority byte limit")
    name = "acquisition-authority-" + hashlib.sha256(raw).hexdigest() + ".json"
    root = os.open(Path(run).anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in Path(run).parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root)
            os.close(root)
            root = child
    except BaseException:
        os.close(root)
        raise
    lock = None
    try:
        try:
            lock = os.open(".acquisition-authority.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=root)
        except FileNotFoundError:
            # A competing initial creator can win while this open reports
            # absence. Retry once as existing-only; never replace the lock.
            lock = os.open(".acquisition-authority.lock", os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root)
        if not stat.S_ISREG(os.fstat(lock).st_mode):
            raise ValueError("unsafe acquisition authority lock")
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            existing = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root)
        except FileNotFoundError:
            existing = None
        if existing is not None:
            with os.fdopen(existing, "rb") as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode) or stream.read(MAX_AUTHORITY_BYTES + 1) != raw:
                    raise ValueError("acquisition authority identity mismatch")
            return _retain_alias(root, name, alias)
        count = 0
        with os.scandir(root) as entries:
            for entry in entries:
                if entry.name.startswith(("acquisition-authority-", "acquisition-prelaunch-", "acquisition-server-", "acquisition-mcp-")) and entry.name.endswith(".json"):
                    count += 1
                    if count + (1 if alias else 0) >= MAX_AUTHORITIES:
                        raise ValueError("acquisition authority retention limit; retain audit records and use a new run")
        pending = ".acquisition-authority.pending"
        # A crash between link and unlink leaves the pending name pointing at
        # a published immutable inode. Remove only that verified extra name.
        try:
            pending_info = os.stat(pending, dir_fd=root, follow_symlinks=False)
        except FileNotFoundError:
            pending_info = None
        if pending_info is not None and pending_info.st_nlink > 1:
            pending_fd = os.open(pending, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root)
            with os.fdopen(pending_fd, "rb") as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    raise ValueError("unsafe acquisition authority staging file")
                prior = stream.read(MAX_AUTHORITY_BYTES + 1)
            prior_name = "acquisition-authority-" + hashlib.sha256(prior).hexdigest() + ".json"
            published = os.stat(prior_name, dir_fd=root, follow_symlinks=False)
            if (published.st_dev, published.st_ino) != (pending_info.st_dev, pending_info.st_ino):
                raise ValueError("unsafe acquisition authority staging link")
            os.unlink(pending, dir_fd=root)
        output = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=root)
        with os.fdopen(output, "wb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ValueError("unsafe acquisition authority staging file")
            stream.truncate(0)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(pending, name, src_dir_fd=root, dst_dir_fd=root, follow_symlinks=False)
        os.unlink(pending, dir_fd=root)
        os.fsync(root)
        return _retain_alias(root, name, alias)
    finally:
        if lock is not None:
            os.close(lock)
        os.close(root)


def _retain_alias(root, canonical, alias):
    if alias is None:
        return canonical
    try:
        existing = os.stat(alias, dir_fd=root, follow_symlinks=False)
    except FileNotFoundError:
        existing = None
    retained = os.stat(canonical, dir_fd=root, follow_symlinks=False)
    if existing is not None:
        if not stat.S_ISREG(existing.st_mode) or (existing.st_dev, existing.st_ino) != (retained.st_dev, retained.st_ino):
            raise ValueError("conflicting acquisition attempt authority")
    else:
        count = sum(e.name.startswith(("acquisition-authority-", "acquisition-prelaunch-", "acquisition-server-", "acquisition-mcp-")) and e.name.endswith(".json") for e in os.scandir(root))
        if count >= MAX_AUTHORITIES:
            raise ValueError("acquisition authority retention limit")
        os.link(canonical, alias, src_dir_fd=root, dst_dir_fd=root, follow_symlinks=False)
        os.fsync(root)
    return alias
