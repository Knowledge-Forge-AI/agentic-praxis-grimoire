#!/usr/bin/env python3
"""Fast-forward a dirty active Agent-Central checkout without clobbering it.

This helper is deliberately provider-free.  It permits only the remote fetch,
one ``git merge --ff-only origin/main``, and three read-only smoke commands.
Every local unstaged or untracked path is recorded outside the active checkout
by content hash, type, and mode before the merge and checked again afterwards.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import stat
import subprocess
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "libexec"))
from controller_generation import inspect_leases, read_record, write_record
from controller_generation_store import coordinate, materialize
from controller_generation_process import process_identity

SCHEMA = "guarded-active-checkout-update-v1"
REPORT_NAME = "guarded-active-checkout-update.json"
GIT_TIMEOUT_SECONDS = 120
MAX_SMOKE_REQUEST_BYTES = 1024 * 1024
_GIT_OPERATION_MARKERS = (
    "MERGE_HEAD",
    "CHERRY_PICK_HEAD",
    "REVERT_HEAD",
    "BISECT_LOG",
    "BISECT_START",
    "BISECT_HEAD",
    "rebase-merge",
    "rebase-apply",
    "sequencer",
    "index.lock",
    "HEAD.lock",
    "FETCH_HEAD.lock",
    "packed-refs.lock",
    "config.lock",
    "shallow.lock",
)


class GuardError(RuntimeError):
    """A fail-closed active-checkout guard or verification failure."""

    def __init__(self, code: str, detail: str, *, blockers: list[dict] | None = None,
                 smoke: list[dict] | None = None) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.blockers = blockers
        self.smoke = smoke


def _decode(data: bytes) -> str:
    return data.decode("utf-8", "replace").strip()


def _safe_detail(data: bytes) -> str:
    detail = _decode(data)
    return re.sub(r"(://)[^/\s@]+@", r"\1<redacted>@", detail)


def _run(
    argv: list[str],
    *,
    cwd: Path | None = None,
    timeout: int = GIT_TIMEOUT_SECONDS,
) -> subprocess.CompletedProcess[bytes]:
    environment = os.environ.copy()
    environment["GIT_TERMINAL_PROMPT"] = "0"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        return subprocess.run(
            argv,
            cwd=cwd,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError) as error:
        command = argv[0] if argv else "command"
        raise GuardError(
            "COMMAND_INVOCATION_FAILED",
            f"{command} could not be invoked ({type(error).__name__})",
        ) from error


def _git(root: Path, arguments: list[str], code: str) -> bytes:
    completed = _run(["git", *arguments], cwd=root)
    if completed.returncode != 0:
        detail = _safe_detail(completed.stderr) or "git command failed"
        raise GuardError(code, detail)
    return completed.stdout


def _git_text(root: Path, arguments: list[str], code: str) -> str:
    value = _decode(_git(root, arguments, code))
    if not value:
        raise GuardError(code, "git returned no value")
    return value


def _canonical_root(value: Path) -> Path:
    try:
        root = value.expanduser().resolve(strict=True)
    except OSError as error:
        raise GuardError("ACTIVE_ROOT_INVALID", f"cannot resolve active root ({error})") from error
    if not root.is_dir():
        raise GuardError("ACTIVE_ROOT_INVALID", "active root is not a directory")
    reported = Path(_git_text(root, ["rev-parse", "--show-toplevel"], "NOT_A_WORKTREE"))
    try:
        git_root = reported.resolve(strict=True)
    except OSError as error:
        raise GuardError("NOT_A_WORKTREE", f"cannot resolve Git root ({error})") from error
    if git_root != root:
        raise GuardError("ACTIVE_ROOT_NOT_GIT_ROOT", "active root is not the Git worktree root")
    return root


def _dispatcher_command(command: str) -> bool:
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    if not tokens:
        return False
    executable = Path(tokens[0]).name
    if executable in {"agent-phase-dispatch", "agent-phase-finalize"}:
        return True
    if (
        executable in {"bash", "sh", "zsh"}
        and len(tokens) > 1
        and Path(tokens[1]).name in {"agent-phase-dispatch", "agent-phase-finalize"}
    ):
        return True
    return bool(
        executable.startswith("python")
        and any((token.endswith("agent_phase/cli.py") or token == "agent_phase.cli") and index + 1 < len(tokens)
                and tokens[index + 1] in {"dispatch", "finalize"}
                for index, token in enumerate(tokens[1:], 1))
    )


def _read_process_records() -> bytes:
    completed = _run(["ps", "-ww", "-axo", "pid=,ppid=,command="], timeout=30)
    if completed.returncode != 0:
        raise GuardError("DISPATCHER_STATE_UNREADABLE", _safe_detail(completed.stderr))

    return completed.stdout


def _classify_process_records(records: bytes, *, self_pid: int, safe: dict | None = None) -> None:
    """Match using argv privately; retain only a bounded safe structural receipt.

    Two-column injected/legacy records remain readable. Never serialize argv,
    shell command text, prompts or environment. Source context is a fixed suffix,
    not an arbitrary path obtained from the command line.
    """
    blockers = []
    for line in records.decode("utf-8", "replace").splitlines():
        fields = line.strip().split(None, 2)
        if len(fields) < 2:
            continue
        try:
            pid = int(fields[0])
        except ValueError:
            continue
        ppid = int(fields[1]) if fields[1].isdigit() and len(fields) == 3 else None
        command = fields[2] if ppid is not None else " ".join(fields[1:])
        if pid == self_pid or not _dispatcher_command(command):
            continue
        try:
            tokens = shlex.split(command)
        except ValueError:
            tokens = command.split()
        lease = (safe or {}).get(pid)
        if lease is not None and lease["status"] == "running":
            expected = str(Path(lease["generation_root"]) / "libexec/agent_phase/cli.py")
            if (expected in tokens and tokens[tokens.index(expected) + 1:][:1] in (["dispatch"], ["finalize"])
                    and process_identity(pid) == lease["process_identity"]):
                continue
        executable = Path(tokens[0]).name
        safe_executable = (executable if executable in {"bash", "sh", "zsh", "agent-phase-dispatch"}
                           else "python")
        context = "libexec/agent_phase/cli.py" if executable.startswith("python") else "bin/agent-phase-dispatch"
        blockers.append({"pid": pid, "ppid": ppid, "executable": safe_executable,
                         "source_context": context, "source_context_observed": False, "cwd": None})
        if len(blockers) == 16:
            break
    if blockers:
        detail = "an agent-phase-dispatch process is active; matching processes: " + json.dumps(blockers, ensure_ascii=True)
        raise GuardError("ACTIVE_DISPATCHER", detail, blockers=blockers)


def _require_no_dispatcher(process_reader: Callable[[], bytes]) -> None:
    records = process_reader()
    _classify_process_records(records, self_pid=os.getpid())


def _require_safe_dispatchers(process_reader: Callable[[], bytes], store: Path) -> dict:
    leases = inspect_leases(store)
    if leases["blockers"]:
        raise GuardError("ACTIVE_DISPATCHER", "dispatcher lease validation failed",
                         blockers=leases["blockers"])
    _classify_process_records(process_reader(), self_pid=os.getpid(),
                              safe={item["pid"]: item for item in leases["safe"]})
    return leases


def _git_path(root: Path, marker: str) -> Path:
    value = Path(_git_text(root, ["rev-parse", "--git-path", marker], "GIT_OPERATION_STATE_UNREADABLE"))
    return value if value.is_absolute() else root / value


def _require_no_git_operation(root: Path) -> None:
    marker_paths = {marker: _git_path(root, marker) for marker in _GIT_OPERATION_MARKERS}
    active = [marker for marker, path in marker_paths.items() if os.path.lexists(path)]
    try:
        git_dir = Path(_git_text(root, ["rev-parse", "--absolute-git-dir"], "GIT_OPERATION_STATE_UNREADABLE"))
        active.extend(
            "lock:" + os.fspath(path.relative_to(git_dir))
            for path in sorted(git_dir.rglob("*.lock"))
            if path not in marker_paths.values()
        )
    except OSError as error:
        raise GuardError("GIT_OPERATION_STATE_UNREADABLE", f"cannot inspect Git locks ({error})") from error
    if active:
        raise GuardError("ACTIVE_GIT_OPERATION", "Git operation state is active: " + ", ".join(active))


def _require_branch_and_upstream(root: Path) -> tuple[str, str, str]:
    branch = _git_text(root, ["symbolic-ref", "--quiet", "--short", "HEAD"], "BRANCH_UNREADABLE")
    if branch != "main":
        raise GuardError("BRANCH_NOT_MAIN", f"active branch is {branch!r}")
    upstream = _git_text(
        root,
        ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"],
        "UPSTREAM_UNREADABLE",
    )
    if upstream != "origin/main":
        raise GuardError("UPSTREAM_NOT_ORIGIN_MAIN", f"configured upstream is {upstream!r}")
    head = _git_text(root, ["rev-parse", "--verify", "HEAD"], "HEAD_UNREADABLE")
    return branch, upstream, head


def _index_identity(root: Path) -> dict[str, Any]:
    listing = _git(root, ["ls-files", "--stage", "-z", "--", ":/"], "INDEX_UNREADABLE")
    return {
        "kind": "git_ls_files_stage_v1",
        "sha256": hashlib.sha256(listing).hexdigest(),
        "size_bytes": len(listing),
        "entry_count": len([entry for entry in listing.split(b"\0") if entry]),
    }


def _staged_paths(root: Path) -> list[str]:
    completed = _run(
        ["git", "diff", "--cached", "--name-only", "-z", "HEAD", "--"],
        cwd=root,
    )
    if completed.returncode != 0:
        raise GuardError("INDEX_UNREADABLE", _safe_detail(completed.stderr))
    return [os.fsdecode(path) for path in completed.stdout.split(b"\0") if path]


def _relative_path(raw: bytes | str) -> str:
    value = os.fsdecode(raw) if isinstance(raw, bytes) else raw
    pure = PurePosixPath(value)
    if not value or pure.is_absolute() or ".." in pure.parts:
        raise GuardError("UNSAFE_PATH", "Git reported an unsafe relative path")
    return pure.as_posix()


def _status_paths(root: Path, *, ignored_only: bool = False) -> list[str]:
    arguments = [
        "git", "status", "--porcelain=v2", "-z", "--untracked-files=all",
    ]
    if ignored_only:
        arguments.append("--ignored=matching")
    arguments.append("--")
    completed = _run(
        arguments,
        cwd=root,
    )
    if completed.returncode != 0:
        raise GuardError("STATUS_FAILED", _safe_detail(completed.stderr))
    records = completed.stdout.split(b"\0")
    paths: list[str] = []
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        if record.startswith((b"? ", b"! ")):
            if record.startswith(b"! ") == ignored_only:
                paths.append(_relative_path(record[2:]))
        elif record.startswith((b"1 ", b"u ")):
            fields = record.split(b" ", 8)
            if len(fields) != 9:
                raise GuardError("STATUS_FAILED", "malformed Git status record")
            if not ignored_only:
                paths.append(_relative_path(fields[8]))
        elif record.startswith(b"2 "):
            fields = record.split(b" ", 9)
            if len(fields) != 10:
                raise GuardError("STATUS_FAILED", "malformed Git rename status record")
            if not ignored_only:
                paths.append(_relative_path(fields[9]))
            if index < len(records) and records[index]:
                if not ignored_only:
                    paths.append(_relative_path(records[index]))
                index += 1
        else:
            raise GuardError("STATUS_FAILED", "unknown Git status record")
    return sorted(set(paths))


def _path_overlap(left: list[str], right: list[str]) -> list[str]:
    overlap: set[str] = set()
    for local in left:
        local_parts = PurePosixPath(local).parts
        for incoming in right:
            incoming_parts = PurePosixPath(incoming).parts
            shared = min(len(local_parts), len(incoming_parts))
            if local_parts[:shared] == incoming_parts[:shared]:
                overlap.add(local)
                break
    return sorted(overlap)


def _incoming_paths(root: Path) -> list[str]:
    output = _git(
        root,
        ["diff", "--name-only", "-z", "--no-renames", "HEAD..origin/main", "--"],
        "INCOMING_DIFF_FAILED",
    )
    return sorted({_relative_path(path) for path in output.split(b"\0") if path})


def _safe_target(root: Path, relative: str) -> Path:
    target = root
    parts = PurePosixPath(relative).parts
    for index, component in enumerate(parts):
        target /= component
        if index < len(parts) - 1:
            try:
                if stat.S_ISLNK(os.lstat(target).st_mode):
                    raise GuardError("LOCAL_PATH_UNSAFE", f"path ancestor is a symlink: {relative}")
            except FileNotFoundError:
                break
            except OSError as error:
                raise GuardError("LOCAL_PATH_UNREADABLE", f"cannot inspect {relative}: {error}") from error
    return target


def _stat_signature(info: os.stat_result) -> tuple[int, ...]:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _snapshot(root: Path, relative: str) -> dict[str, Any]:
    target = _safe_target(root, relative)
    try:
        before = os.lstat(target)
    except FileNotFoundError:
        return {
            "type": "absent",
            "mode": None,
            "mode_octal": None,
            "size_bytes": None,
            "sha256": None,
        }
    except OSError as error:
        raise GuardError("LOCAL_PATH_UNREADABLE", f"cannot inspect {relative}: {error}") from error
    mode = stat.S_IMODE(before.st_mode)
    if stat.S_ISLNK(before.st_mode):
        try:
            data = os.fsencode(os.readlink(target))
        except OSError as error:
            raise GuardError("LOCAL_PATH_UNREADABLE", f"cannot read {relative}: {error}") from error
        kind = "symlink"
    elif stat.S_ISREG(before.st_mode):
        try:
            data = target.read_bytes()
        except OSError as error:
            raise GuardError("LOCAL_PATH_UNREADABLE", f"cannot read {relative}: {error}") from error
        kind = "file"
    else:
        raise GuardError("LOCAL_PATH_UNSUPPORTED", f"preserved path is not a file or symlink: {relative}")
    try:
        after = os.lstat(target)
    except OSError as error:
        raise GuardError("LOCAL_PATH_CHANGED", f"preserved path disappeared: {relative}") from error
    if _stat_signature(before) != _stat_signature(after):
        raise GuardError("LOCAL_PATH_CHANGED", f"preserved path changed while reading: {relative}")
    return {
        "type": kind,
        "mode": mode,
        "mode_octal": format(mode, "#o"),
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _validate_evidence_dir(value: Path, active_root: Path) -> Path:
    candidate = value.expanduser()
    try:
        if candidate.is_symlink():
            raise GuardError("EVIDENCE_DIR_INVALID", "evidence directory must not be a symlink")
    except OSError as error:
        raise GuardError("EVIDENCE_DIR_INVALID", f"cannot inspect evidence directory ({error})") from error
    try:
        evidence = candidate.resolve(strict=False)
        root = active_root.resolve(strict=True)
        evidence.relative_to(root)
    except ValueError:
        pass
    except OSError as error:
        raise GuardError("EVIDENCE_DIR_INVALID", f"cannot resolve evidence directory ({error})") from error
    else:
        raise GuardError("EVIDENCE_DIR_NOT_EXTERNAL", "evidence directory must be outside active root")
    try:
        evidence.mkdir(parents=True, exist_ok=True)
        if not evidence.is_dir() or evidence.is_symlink():
            raise GuardError("EVIDENCE_DIR_INVALID", "evidence path is not a real directory")
    except OSError as error:
        raise GuardError("EVIDENCE_DIR_INVALID", f"cannot create evidence directory ({error})") from error
    report = evidence / REPORT_NAME
    if report.exists() or report.is_symlink():
        raise GuardError("EVIDENCE_EXISTS", f"evidence report already exists: {REPORT_NAME}")
    return evidence


def _write_report(evidence: Path, report: dict[str, Any]) -> None:
    try:
        (evidence / REPORT_NAME).write_text(
            json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as error:
        raise GuardError("EVIDENCE_WRITE_FAILED", f"cannot write evidence report ({error})") from error


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


def _reject_duplicate(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_strict_json(path: Path) -> tuple[bytes, dict[str, Any]]:
    candidate = path.expanduser()
    try:
        if candidate.is_symlink():
            raise GuardError("SMOKE_REQUEST_INVALID", "smoke request must not be a symlink")
    except OSError as error:
        raise GuardError("SMOKE_REQUEST_INVALID", f"cannot inspect smoke request ({error})") from error
    try:
        named = candidate.resolve(strict=True)
        info = os.lstat(named)
    except OSError as error:
        raise GuardError("SMOKE_REQUEST_INVALID", f"cannot inspect smoke request ({error})") from error
    if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
        raise GuardError("SMOKE_REQUEST_INVALID", "smoke request must be a regular non-symlink file")
    if info.st_size > MAX_SMOKE_REQUEST_BYTES:
        raise GuardError("SMOKE_REQUEST_INVALID", "smoke request exceeds the size bound")
    try:
        data = named.read_bytes()
        after = os.lstat(named)
    except OSError as error:
        raise GuardError("SMOKE_REQUEST_INVALID", f"cannot read smoke request ({error})") from error
    if _stat_signature(info) != _stat_signature(after):
        raise GuardError("SMOKE_REQUEST_INVALID", "smoke request changed while being read")
    try:
        decoded = data.decode("utf-8")
        parsed = json.loads(
            decoded,
            object_pairs_hook=_reject_duplicate,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise GuardError("SMOKE_REQUEST_INVALID", f"smoke request is not strict JSON ({error})") from error
    if not isinstance(parsed, dict):
        raise GuardError("SMOKE_REQUEST_INVALID", "smoke request must contain a JSON object")
    return data, parsed


def _smoke(root: Path, request: Path) -> list[dict[str, Any]]:
    commands = [
        ("dispatcher-help", [os.fspath(root / "bin/agent-phase-dispatch"), "--help"]),
        (
            "resolver",
            [
                os.fspath(root / "bin/agent-phase-resolve"),
                os.fspath(request),
                "--lifecycle",
                "standard",
                "--finalization",
                "publish",
            ],
        ),
        (
            "roster-directions-check",
            [
                "python3",
                os.fspath(root / "tools/add_dispatcher_roster_operator_directions.py"),
                "--root",
                os.fspath(root),
                "--check",
            ],
        ),
    ]
    results: list[dict[str, Any]] = []
    for label, argv in commands:
        completed = _run(argv, cwd=root)
        result = {
            "name": label,
            "returncode": completed.returncode,
            "stdout_sha256": hashlib.sha256(completed.stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(completed.stderr).hexdigest(),
        }
        results.append(result)
        if completed.returncode != 0:
            raise GuardError("SMOKE_FAILED", f"{label} exited {completed.returncode}", smoke=results)
    return results


def _locked_update_active_checkout(
    active_root: Path,
    evidence_dir: Path,
    smoke_request: Path,
    *,
    process_reader: Callable[[], bytes],
    store: Path,
) -> dict[str, Any]:
    """Run the guarded update with an explicitly supplied process reader."""
    root = _canonical_root(active_root)
    evidence = _validate_evidence_dir(evidence_dir, root)
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "preflight",
        "active_root": os.fspath(root),
        "managed_link_reconciliation": "not_applicable_to_source_fast_forward",
        "fetch_command": ["git", "fetch", "origin", "main"],
        "merge_command": ["git", "merge", "--ff-only", "origin/main"],
        "cutover_lock": "acquired",
        "provider_invocations": 0,
    }
    try:
        request_bytes, _ = _read_strict_json(smoke_request)
        report["dispatcher_generations"] = _require_safe_dispatchers(process_reader, store)
        _require_no_git_operation(root)
        branch, upstream, initial_head = _require_branch_and_upstream(root)
        report["active_generation_before"] = {"commit": initial_head,
            "tree": _git_text(root, ["rev-parse", "HEAD^{tree}"], "HEAD_UNREADABLE")}
        movement = store / "last-cutover.json"
        report["unsupervised_movement"] = (read_record(movement).get("commit") != initial_head
                                             if movement.exists() else "not_previously_observed")
        index_before = _index_identity(root)
        if (staged := _staged_paths(root)):
            raise GuardError("INDEX_STAGED_CHANGES", "staged paths are present: " + ", ".join(staged))
        local_paths = _status_paths(root)
        ignored_paths = _status_paths(root, ignored_only=True)
        preserved = {path: _snapshot(root, path) for path in local_paths}
        report.update(
            {
                "status": "preflight-complete",
                "branch": branch,
                "upstream": upstream,
                "initial_head": initial_head,
                "index_before_fetch": index_before,
                "local_paths": local_paths,
                "ignored_paths": ignored_paths,
                "preserved_paths": preserved,
                "smoke_request_sha256": hashlib.sha256(request_bytes).hexdigest(),
                "smoke_request_size_bytes": len(request_bytes),
            }
        )
        _write_report(evidence, report)
        _git(root, ["fetch", "origin", "main"], "FETCH_FAILED")
        if _index_identity(root) != index_before:
            raise GuardError("INDEX_CHANGED", "real Git index changed during fetch")
        if _git_text(root, ["rev-parse", "--verify", "HEAD"], "HEAD_UNREADABLE") != initial_head:
            raise GuardError("HEAD_CHANGED", "active HEAD changed during fetch")
        if _status_paths(root) != local_paths:
            raise GuardError("LOCAL_STATE_CHANGED", "local paths changed during fetch")
        if _status_paths(root, ignored_only=True) != ignored_paths:
            raise GuardError("LOCAL_STATE_CHANGED", "ignored paths changed during fetch")
        if any(_snapshot(root, path) != value for path, value in preserved.items()):
            raise GuardError("LOCAL_STATE_CHANGED", "preserved path bytes changed during fetch")
        fetched_head = _git_text(root, ["rev-parse", "--verify", "origin/main"], "REMOTE_HEAD_UNREADABLE")
        fetch_head = _git_text(root, ["rev-parse", "--verify", "FETCH_HEAD"], "REMOTE_HEAD_UNREADABLE")
        if fetch_head != fetched_head:
            raise GuardError("REMOTE_HEAD_UNREADABLE", "FETCH_HEAD does not match origin/main")
        incoming_paths = _incoming_paths(root)
        overlap = _path_overlap(local_paths, incoming_paths)
        ignored_overlap = _path_overlap(ignored_paths, incoming_paths)
        report.update({"fetched_origin_main": fetched_head, "incoming_paths": incoming_paths})
        report["incoming_tree"] = _git_text(root, ["rev-parse", fetched_head + "^{tree}"], "REMOTE_HEAD_UNREADABLE")
        if overlap or ignored_overlap:
            conflicts = sorted(set(overlap + ignored_overlap))
            raise GuardError(
                "PATH_OVERLAP",
                "local and incoming paths intersect: " + ", ".join(conflicts),
            )

        report["dispatcher_generations"] = _require_safe_dispatchers(process_reader, store)
        _require_no_git_operation(root)
        if _index_identity(root) != index_before:
            raise GuardError("INDEX_CHANGED", "real Git index changed before merge")
        current_branch, current_upstream, current_head = _require_branch_and_upstream(root)
        if (current_branch, current_upstream, current_head) != (branch, upstream, initial_head):
            raise GuardError("REPOSITORY_STATE_CHANGED", "branch, upstream, or HEAD changed before merge")
        if _status_paths(root) != local_paths:
            raise GuardError("LOCAL_STATE_CHANGED", "local paths changed before merge")
        if _status_paths(root, ignored_only=True) != ignored_paths:
            raise GuardError("LOCAL_STATE_CHANGED", "ignored paths changed before merge")
        if any(_snapshot(root, path) != value for path, value in preserved.items()):
            raise GuardError("LOCAL_STATE_CHANGED", "preserved path bytes changed before merge")
        if _git_text(root, ["rev-parse", "--verify", "origin/main"], "REMOTE_HEAD_UNREADABLE") != fetched_head:
            raise GuardError("REMOTE_HEAD_CHANGED", "fetched origin/main changed before merge")
        if _git_text(root, ["rev-parse", "--verify", "HEAD"], "HEAD_UNREADABLE") != initial_head:
            raise GuardError("HEAD_CHANGED", "active HEAD changed before merge")
        merge = _run(["git", "merge", "--ff-only", "origin/main"], cwd=root)
        if merge.returncode != 0:
            raise GuardError("MERGE_FAILED", _safe_detail(merge.stderr) or "fast-forward merge failed")
        report["final_head"] = _git_text(root, ["rev-parse", "HEAD"], "HEAD_UNREADABLE")
        report["active_generation_after"] = {"commit": report["final_head"],
            "tree": _git_text(root, ["rev-parse", "HEAD^{tree}"], "HEAD_UNREADABLE")}
        write_record(movement, {"schema": "controller-cutover-v1", "commit": report["final_head"]})
        if _git_text(root, ["rev-parse", "--verify", "HEAD"], "HEAD_UNREADABLE") != fetched_head:
            raise GuardError("REMOTE_PARITY_FAILED", "HEAD does not equal fetched origin/main")
        after_merge = {path: _snapshot(root, path) for path in local_paths}
        if after_merge != preserved:
            raise GuardError("PRESERVED_PATH_CHANGED", "a preserved local path changed after merge")
        index_after_merge = _index_identity(root)
        generation = materialize(root, store)
        report["smoke_generation"] = generation
        smoke = _smoke(Path(generation["generation_root"]), smoke_request.expanduser().resolve(strict=True))
        request_after, _ = _read_strict_json(smoke_request)
        if request_after != request_bytes:
            raise GuardError("SMOKE_REQUEST_CHANGED", "smoke request changed during checks")
        after_smoke = {path: _snapshot(root, path) for path in local_paths}
        if after_smoke != preserved:
            raise GuardError("PRESERVED_PATH_CHANGED", "a smoke command changed a local path")
        if _index_identity(root) != index_after_merge:
            raise GuardError("INDEX_CHANGED", "real Git index changed during smoke checks")
        report.update(
            {
                "status": "completed",
                "final_head": fetched_head,
                "index_after_merge": index_after_merge,
                "smoke": smoke,
            }
        )
    except (OSError, ValueError, RuntimeError) as error:
        if not isinstance(error, GuardError):
            error = GuardError("GENERATION_BINDING_FAILED", type(error).__name__)
        report.update({"status": "blocked", "error_code": error.code, "error": error.detail})
        if report.get("active_generation_after"):
            report["status"] = "updated_verification_failed"
            report["recovery"] = "inspect active HEAD; repair forward and rerun provider-free smoke; do not reset or terminate pinned runs"
        if error.blockers is not None:
            report["active_dispatchers"] = error.blockers
        if error.smoke is not None:
            report["smoke"] = error.smoke
        _write_report(evidence, report)
        raise error
    _write_report(evidence, report)
    return report


def _update_active_checkout(active_root: Path, evidence_dir: Path, smoke_request: Path,
                            *, process_reader: Callable[[], bytes]) -> dict[str, Any]:
    root = _canonical_root(active_root)
    try:
        with coordinate(root) as store:
            return _locked_update_active_checkout(root, evidence_dir, smoke_request,
                                                  process_reader=process_reader, store=store)
    except GuardError:
        raise
    except (OSError, ValueError, RuntimeError) as error:
        guard = GuardError("CUTOVER_LOCK_FAILED", type(error).__name__)
        evidence = _validate_evidence_dir(evidence_dir, root)
        _write_report(evidence, {"schema": SCHEMA, "status": "blocked",
                               "error_code": guard.code, "cutover_lock": "unavailable",
                               "provider_invocations": 0})
        raise guard from error


def update_active_checkout(
    active_root: Path,
    evidence_dir: Path,
    smoke_request: Path,
) -> dict[str, Any]:
    """Production adapter using the real process table at both guard points."""

    return _update_active_checkout(
        active_root,
        evidence_dir,
        smoke_request,
        process_reader=_read_process_records,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Guard and fast-forward a dirty active Agent-Central checkout.",
        allow_abbrev=False,
    )
    parser.add_argument("--active-root", "--root", dest="active_root", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--smoke-request", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        report = update_active_checkout(
            arguments.active_root,
            arguments.evidence_dir,
            arguments.smoke_request,
        )
    except GuardError as error:
        print(f"guarded-active-checkout-update: {error}", file=sys.stderr)
        return 2
    print(f"guarded-active-checkout-update: {report['final_head']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
