"""Shared stage-boundary evidence and operational metadata classification.

Captures consecutive stage deltas, classifies changes as product versus
operational metadata, and manages safe index normalization when a provider
contaminates the Git index.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
from typing import Any

from .metadata_policy import OPERATIONAL_METADATA_ROOTS, is_metadata_pattern
from . import gitstate as gitstate_module

STAGE_DELTA_SCHEMA = "agent-phase-stage-delta-v1"

MAX_STAGE_INLINE_DELTAS = 256
MAX_RUN_INLINE_DELTAS = 1024
MAX_PROMPT_DELTAS = 80
MAX_PROMPT_BYTES = 16 * 1024
MAX_OVERFLOW_CHUNK_BYTES = 1024 * 1024
MAX_OVERFLOW_AGGREGATE_BYTES = 32 * 1024 * 1024



def _error_record(error: BaseException) -> dict[str, str]:
    """Return bounded, serializable error evidence for a stage boundary."""
    return {
        "code": str(getattr(error, "code", type(error).__name__)),
        "detail": str(error)[:2000],
    }


def _append_stage_observation_limitation(
    state: dict[str, Any], stage_name: str, limitation: dict[str, Any]
) -> None:
    """Retain bounded observation limits even when ledger capture cannot finish."""
    records = state.setdefault("stage_observation_limitations", [])
    if not isinstance(records, list):
        records = []
        state["stage_observation_limitations"] = records
    record = {"stage": stage_name, **limitation}
    if record not in records:
        records.append(record)


def is_tracked(root: Path, path: str) -> bool:
    """Check if a path is tracked in the repository index or HEAD."""
    completed = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", gitstate_module.literal_pathspec(path)],
        cwd=root,
        capture_output=True,
        check=False,
    )
    return completed.returncode == 0


def _tracked_path_set(
    root: Path, *, observation: dict[str, Any] | None = None
) -> set[str] | None:
    """Read the index path set once for bounded metadata classification.

    Metadata scans are already bounded, but checking each observed path with a
    separate ``git ls-files`` invocation made stage entry and close needlessly
    expensive.  A NUL-delimited listing preserves arbitrary Git path names and
    lets callers perform membership checks without following filesystem links.
    ``None`` means the listing was unavailable and callers should retain the
    older per-path fallback together with an observation limitation.
    """
    completed = subprocess.run(
        ["git", "ls-files", "-z", "--"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        if observation is not None:
            observation.setdefault("observation_limitations", []).append(
                {
                    "kind": "tracked_path_set_unavailable",
                    "exit_code": completed.returncode,
                }
            )
        return None
    paths = {
        token.decode("utf-8", "surrogateescape")
        for token in completed.stdout.split(b"\0")
        if token
    }
    if observation is not None:
        observation["tracked_path_set"] = {
            "method": "git_ls_files",
            "count": len(paths),
        }
    return paths


def _metadata_path_is_tracked(
    root: Path, path: str, tracked_paths: set[str] | None
) -> bool:
    """Use a boundary cache when available, preserving the fallback contract."""
    if tracked_paths is not None:
        return path in tracked_paths
    return is_tracked(root, path)


def _overflow_infos(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the latest bounded overflow record for each run-relative name.

    Stage-delta and index-normalization evidence share the same aggregate byte
    ceiling.  A normalization record is present both at run scope and, after
    stage capture, inside its stage record, so names are deduplicated here.
    Later records win when recovery rewrites a run-owned artifact name.
    """
    by_name: dict[str, dict[str, Any]] = {}
    anonymous: list[dict[str, Any]] = []
    anonymous_keys: set[str] = set()

    def add(info: Any) -> None:
        if not isinstance(info, dict):
            return
        name = info.get("name")
        if isinstance(name, str) and name:
            by_name[name] = info
            return
        # Failed or unavailable artifact writes have no usable name, but they
        # still make the bounded evidence incomplete.  Keep one copy of an
        # aliased record so refresh preserves that truncation signal.
        try:
            key = json.dumps(info, sort_keys=True, default=str)
        except (TypeError, ValueError):
            key = repr(sorted((str(k), repr(v)) for k, v in info.items()))
        if key not in anonymous_keys:
            anonymous_keys.add(key)
            anonymous.append(info)

    ledger = state.get("stage_delta_ledger")
    stages = ledger.get("stages", {}) if isinstance(ledger, dict) else {}
    if isinstance(stages, dict):
        for stage_info in stages.values():
            if not isinstance(stage_info, dict):
                continue
            add(stage_info.get("overflow"))
            add(stage_info.get("overflow_artifact"))
            stage_normalizations = stage_info.get("index_normalizations", [])
            if isinstance(stage_normalizations, list):
                for record in stage_normalizations:
                    if isinstance(record, dict):
                        add(record.get("overflow"))
                        add(record.get("overflow_artifact"))

    # Run-level records are appended for every normalization attempt.  Process
    # them last so a repeated stage/index artifact rewrite wins over the older
    # copy retained in that stage's previous record.
    normalizations = state.get("index_normalizations", [])
    if isinstance(normalizations, list):
        for record in normalizations:
            if isinstance(record, dict):
                add(record.get("overflow"))
                add(record.get("overflow_artifact"))
    return [*by_name.values(), *anonymous]


def _overflow_bytes_in_use(
    state: dict[str, Any], *, exclude_names: set[str] | None = None
) -> int:
    """Return shared overflow bytes already accounted for in this run."""
    excluded = exclude_names or set()
    infos = [info for info in _overflow_infos(state) if info.get("name") not in excluded]
    if infos:
        total = 0
        for info in infos:
            try:
                total += max(0, int(info.get("bytes", 0)))
            except (TypeError, ValueError):
                continue
        return min(total, MAX_OVERFLOW_AGGREGATE_BYTES)

    # A resumed or repaired legacy state may carry only the aggregate summary.
    # Keep that spent budget conservatively when no per-artifact records exist.
    ledger = state.get("stage_delta_ledger")
    aggregate = ledger.get("overflow_aggregate") if isinstance(ledger, dict) else None
    if isinstance(aggregate, dict):
        try:
            return min(
                MAX_OVERFLOW_AGGREGATE_BYTES,
                max(0, int(aggregate.get("bytes", 0))),
            )
        except (TypeError, ValueError):
            pass
    return 0


def _refresh_overflow_aggregate(state: dict[str, Any]) -> dict[str, Any]:
    """Rebuild the one shared overflow budget from stage and index evidence."""
    ledger = state.setdefault(
        "stage_delta_ledger",
        {"schema": STAGE_DELTA_SCHEMA, "deltas": [], "stages": {}},
    )
    if not isinstance(ledger, dict):
        raise TypeError("stage_delta_ledger must be a mapping")
    infos = _overflow_infos(state)
    if infos:
        bytes_total = 0
        truncated = False
        for info in infos:
            try:
                bytes_total += max(0, int(info.get("bytes", 0)))
            except (TypeError, ValueError):
                pass
            if info.get("truncated") or info.get("artifact_written") is False:
                truncated = True
        aggregate = {
            "bytes": min(bytes_total, MAX_OVERFLOW_AGGREGATE_BYTES),
            "limit_bytes": MAX_OVERFLOW_AGGREGATE_BYTES,
            "artifact_count": len(infos),
            "truncated": truncated,
        }
    else:
        previous = ledger.get("overflow_aggregate")
        if isinstance(previous, dict):
            try:
                previous_bytes = min(
                    MAX_OVERFLOW_AGGREGATE_BYTES,
                    max(0, int(previous.get("bytes", 0))),
                )
            except (TypeError, ValueError):
                previous_bytes = 0
            try:
                previous_artifact_count = max(
                    0, int(previous.get("artifact_count", 0) or 0)
                )
            except (TypeError, ValueError):
                previous_artifact_count = 0
            aggregate = {
                "bytes": previous_bytes,
                "limit_bytes": MAX_OVERFLOW_AGGREGATE_BYTES,
                "artifact_count": previous_artifact_count,
                "truncated": bool(previous.get("truncated")),
            }
        else:
            aggregate = {
                "bytes": 0,
                "limit_bytes": MAX_OVERFLOW_AGGREGATE_BYTES,
                "artifact_count": 0,
                "truncated": False,
            }
    ledger["overflow_aggregate"] = aggregate
    return aggregate


def is_tracked_in_tree(root: Path, treeish: str, path: str) -> bool:
    """Check if a path exists in a specific treeish."""
    if not treeish:
        return False
    completed = subprocess.run(
        ["git", "cat-file", "-e", f"{treeish}:{path}"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    return completed.returncode == 0


def observe_git_authority(root: Path) -> dict[str, Any]:
    """Capture current branch/detached state, HEAD, active operations, and index identity."""
    try:
        branch = gitstate_module.current_branch(root)
    except Exception:
        branch = "unknown"
    try:
        head = gitstate_module.current_head(root)
    except Exception:
        head = "unknown"
    try:
        ops = list(gitstate_module.active_git_operations(root))
    except Exception:
        ops = []
    try:
        idx = gitstate_module.index_identity(root)
    except Exception:
        idx = {}
    return {
        "branch": branch,
        "head": head,
        "active_operations": ops,
        "index": idx,
    }


def inspect_index_changes(
    root: Path, *, observation: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """Capture machine-readable index observations including renames, intent-to-add, and modes."""
    res = subprocess.run(
        ["git", "status", "--porcelain=v2", "-z", "--untracked-files=no"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if res.returncode != 0:
        if observation is not None:
            observation.setdefault("observation_limitations", []).append(
                {"kind": "index_status_unavailable", "exit_code": res.returncode}
            )
        return []
    tokens = res.stdout.split(b"\0")
    staged: list[dict[str, Any]] = []
    i = 0
    while i < len(tokens) and tokens[i]:
        item = tokens[i].decode("utf-8", "surrogateescape")
        tag = item[:1]
        if tag == "1":
            parts = item.split(" ", 8)
            if len(parts) == 9:
                _, xy, sub, mH, mI, mW, hH, hI, path = parts
                if len(xy) < 2:
                    if observation is not None:
                        observation.setdefault("observation_limitations", []).append(
                            {"kind": "malformed_index_status", "record": tag}
                        )
                elif xy == ".A":
                    staged.append({
                        "path": path,
                        "status": "intent_to_add",
                        "type": "intent_to_add",
                        "intent_to_add": True,
                        "mode": mI,
                        "head_mode": mH,
                        "blob_sha": hI,
                        "head_blob_sha": hH,
                    })
                elif xy[0] in ("A", "M", "D", "T"):
                    status_str = xy[0]
                    change_type = (
                        "addition" if status_str == "A"
                        else "deletion" if status_str == "D"
                        else "type_change" if status_str == "T"
                        else "mode_change" if (mH != mI and mH != "000000" and mI != "000000")
                        else "modification"
                    )
                    staged.append({
                        "path": path,
                        "status": status_str,
                        "type": change_type,
                        "intent_to_add": False,
                        "mode": mI,
                        "head_mode": mH,
                        "blob_sha": hI,
                        "head_blob_sha": hH,
                    })
            elif observation is not None:
                observation.setdefault("observation_limitations", []).append(
                    {"kind": "malformed_index_status", "record": tag}
                )
            i += 1
        elif tag == "2":
            parts = item.split(" ", 9)
            if len(parts) == 10:
                _, xy, sub, mH, mI, mW, hH, hI, score, path = parts
                i += 1
                orig_path = tokens[i].decode("utf-8", "surrogateescape") if i < len(tokens) else ""
                staged.append({
                    "path": orig_path,
                    "status": "D",
                    "type": "deletion",
                    "renamed_to": path,
                    "intent_to_add": False,
                })
                staged.append({
                    "path": path,
                    "status": "A",
                    "type": "addition",
                    "orig_path": orig_path,
                    "renamed": True,
                    "intent_to_add": False,
                    "mode": mI,
                    "head_mode": mH,
                    "blob_sha": hI,
                    "head_blob_sha": hH,
                })
            elif observation is not None:
                observation.setdefault("observation_limitations", []).append(
                    {"kind": "malformed_index_status", "record": tag}
                )
            i += 1
        elif tag == "u":
            parts = item.split(" ", 10)
            path = parts[10] if len(parts) > 10 else ""
            if not path and observation is not None:
                observation.setdefault("observation_limitations", []).append(
                    {"kind": "malformed_index_status", "record": tag}
                )
            staged.append({
                "path": path,
                "status": "unmerged",
                "type": "unmerged",
                "intent_to_add": False,
            })
            i += 1
        else:
            i += 1
    return staged


def _ignored(root: Path, path: str) -> bool | None:
    result = subprocess.run(
        ["git", "check-ignore", "-q", "--", path], cwd=root, capture_output=True
    )
    return result.returncode == 0 if result.returncode in (0, 1) else None


def scan_operational_metadata(
    root: Path, limit_per_root: int = 50, *, observation: dict[str, Any] | None = None
) -> dict[str, dict[str, Any]]:
    """Observe at most 50 directory entries per root, without following symlinks.

    Stat changes are evidence, not proof of content changes. No cache contents
    are read. Inaccessible, external and omitted entries remain unobserved.
    """
    results: dict[str, dict[str, Any]] = {}
    limits = observation if observation is not None else {}
    limits.update(entry_limit_per_root=limit_per_root, depth_limit=4, omitted_roots=[])
    for root_name in OPERATIONAL_METADATA_ROOTS:
        target = root / root_name
        # A nested built-in root must not traverse an external ancestor.
        if any(parent.is_symlink() for parent in target.parents if parent != root and root in parent.parents):
            limits["omitted_roots"].append(root_name)
            continue
        pending = [(target, 0)]
        count = 0
        while pending and count < limit_per_root:
            current, depth = pending.pop()
            try:
                st = current.lstat()
                if not stat.S_ISDIR(st.st_mode):
                    results[current.relative_to(root).as_posix()] = {
                        "exists": True,
                        "type": "symlink" if stat.S_ISLNK(st.st_mode) else "file",
                        "size_bytes": st.st_size,
                        "mtime": st.st_mtime_ns,
                    }
                    continue
                if depth >= 4:
                    limits["omitted_roots"].append(root_name)
                    continue
                with os.scandir(current) as entries:
                    sorted_entries = sorted(entries, key=lambda e: e.name)
                    for item in sorted_entries:
                        if count >= limit_per_root:
                            limits["omitted_roots"].append(root_name)
                            break
                        count += 1
                        path = Path(item.path)
                        if item.is_dir(follow_symlinks=False):
                            pending.append((path, depth + 1))
                        else:
                            fst = item.stat(follow_symlinks=False)
                            results[path.relative_to(root).as_posix()] = {
                                "exists": True,
                                "type": "symlink" if stat.S_ISLNK(fst.st_mode) else "file",
                                "size_bytes": fst.st_size,
                                "mtime": fst.st_mtime_ns,
                            }
            except FileNotFoundError:
                continue
            except OSError:
                limits["omitted_roots"].append(root_name)
        if pending:
            limits["omitted_roots"].append(root_name)
    limits["omitted_roots"] = sorted(set(limits["omitted_roots"]))
    return results


def normalize_index_if_needed(
    root: Path,
    expected_index_or_entry: Any,
    arg3: Any = None,
    arg4: Any = None,
    *,
    in_failure_path: bool = False,
    directory: Any = None,
    **kwargs: Any,
) -> dict[str, Any] | None:
    """Safely restore clean index posture if provider polluted index during stage.

    When entry index was clean and dispatcher can restore without changing worktree:
    - inspect complete machine-readable staged changes including intent-to-add and renames;
    - restore dispatcher-owned safe index posture;
    - return bounded normalization record with total and omitted counts.
    """
    if isinstance(arg3, dict):
        state = arg3
        stage_name = str(arg4 or kwargs.get("stage_name", ""))
    elif isinstance(arg3, str):
        stage_name = arg3
        state = arg4 if isinstance(arg4, dict) else kwargs.get("state", {})
    else:
        state = kwargs.get("state") if isinstance(kwargs.get("state"), dict) else {}
        stage_name = str(kwargs.get("stage_name", ""))
    if directory is None and "directory" in kwargs:
        directory = kwargs["directory"]
    expected_index = (
        expected_index_or_entry.index_identity
        if hasattr(expected_index_or_entry, "index_identity")
        else expected_index_or_entry
    )

    native_transition = state.get("native_git_transition")
    if (
        native_transition
        and isinstance(native_transition, dict)
        and native_transition.get("status") == "accepted"
    ):
        commit_tree = native_transition.get("commit_tree") or native_transition.get("commit")
        if commit_tree:
            native_tree_index = gitstate_module.index_identity_for_tree(
                root, commit_tree
            )
            if native_tree_index:
                expected_index = native_tree_index

    current_index = gitstate_module.index_identity(root)
    if current_index == expected_index:
        return None

    # Inspect all staged changes before reset.  Keep parser/transport limits
    # alongside the normalization record instead of silently treating an
    # unavailable status listing as an empty index.
    index_observation: dict[str, Any] = {}
    staged_changes = inspect_index_changes(root, observation=index_observation)
    index_limitations = list(index_observation.get("observation_limitations", []))
    all_unmerged_paths = [
        c["path"] for c in staged_changes
        if c.get("status") == "unmerged" or c.get("type") == "unmerged"
    ]
    all_staged_paths = [c["path"] for c in staged_changes if isinstance(c.get("path"), str)]
    all_intent_to_add_paths = [
        c["path"] for c in staged_changes
        if c.get("intent_to_add") and isinstance(c.get("path"), str)
    ]

    status_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}
    for c in staged_changes:
        st = str(c.get("status", "unknown"))
        tp = str(c.get("type", "unknown"))
        status_counts[st] = status_counts.get(st, 0) + 1
        type_counts[tp] = type_counts.get(tp, 0) + 1

    # Check active git operations
    active_ops = gitstate_module.active_git_operations(root)
    expected_head = getattr(expected_index_or_entry, "head", None)
    entry_record = state.get("entry", {})
    if expected_head is None and isinstance(entry_record, dict):
        expected_head = entry_record.get("head")

    if (
        native_transition
        and isinstance(native_transition, dict)
        and native_transition.get("status") == "accepted"
    ):
        expected_head = native_transition["commit"]

    head_moved = bool(expected_head and gitstate_module.current_head(root) != expected_head)

    # Independent reviews may normalize only newly indexed operational metadata.
    # Product/protected entries remain untouched as evidence for manager resolution.
    from . import review_binding
    protected_review_index = review_binding.is_review(state, stage_name) and (
        index_limitations or not staged_changes
        or gitstate_module.index_identity_for_tree(root, "HEAD") != expected_index
        or any(c.get("status") not in ("A", "intent_to_add")
               or not is_metadata_pattern(c["path"]) for c in staged_changes)
    )

    # Determine safety from complete observations
    unsafe_reason = None
    if active_ops:
        unsafe_reason = f"active git operations: {', '.join(active_ops)}"
    elif all_unmerged_paths:
        shown = ", ".join(f"`{p}`" for p in all_unmerged_paths[:8])
        if len(all_unmerged_paths) > 8:
            shown += f", +{len(all_unmerged_paths) - 8} more"
        unsafe_reason = f"unmerged paths: {shown}"
    elif head_moved:
        unsafe_reason = "unaccounted HEAD change"
    elif protected_review_index:
        unsafe_reason = "protected review index mutation; normalization not attempted"

    # Bound inline lists and compute counts
    inline_staged_changes = staged_changes[:MAX_STAGE_INLINE_DELTAS]
    inline_staged_paths = all_staged_paths[:MAX_STAGE_INLINE_DELTAS]
    inline_intent_to_add_paths = all_intent_to_add_paths[:MAX_STAGE_INLINE_DELTAS]
    inline_unmerged_paths = all_unmerged_paths[:MAX_STAGE_INLINE_DELTAS]

    omitted_changes_count = max(0, len(staged_changes) - len(inline_staged_changes))
    omitted_paths_count = max(0, len(all_staged_paths) - len(inline_staged_paths))
    omitted_intent_count = max(0, len(all_intent_to_add_paths) - len(inline_intent_to_add_paths))
    omitted_unmerged_count = max(0, len(all_unmerged_paths) - len(inline_unmerged_paths))

    overflow_info: dict[str, Any] | None = None
    if omitted_changes_count > 0:
        tail_changes = staged_changes[MAX_STAGE_INLINE_DELTAS:]
        overflow_name = f"{stage_name}.index_normalizations.jsonl"
        if directory is None:
            overflow_info = {
                "name": None,
                "requested_name": overflow_name,
                "bytes": 0,
                "sha256": hashlib.sha256(b"").hexdigest(),
                "omitted_inline_count": omitted_changes_count,
                "written_count": 0,
                "omitted_overflow_count": len(tail_changes),
                "truncated": True,
                "artifact_written": False,
                "format": "jsonl",
                "observation_limitation": "run_directory_unavailable",
            }
        else:
            prior_overflow_bytes = _overflow_bytes_in_use(
                state, exclude_names={overflow_name}
            )
            available_aggregate = max(0, MAX_OVERFLOW_AGGREGATE_BYTES - prior_overflow_bytes)
            chunk_budget = min(MAX_OVERFLOW_CHUNK_BYTES, available_aggregate)

            payload_lines: list[bytes] = []
            payload_bytes = 0
            truncation_reason: str | None = None
            for item in tail_changes:
                try:
                    line = (json.dumps(item, sort_keys=True) + "\n").encode("utf-8")
                except (TypeError, ValueError, UnicodeError) as error:
                    truncation_reason = "serialization_error"
                    state.setdefault("stage_delta_overflow_errors", []).append(
                        {"stage": stage_name, **_error_record(error)}
                    )
                    break
                if len(line) > MAX_OVERFLOW_CHUNK_BYTES:
                    truncation_reason = "record_exceeds_chunk_limit"
                    break
                if payload_bytes + len(line) > chunk_budget:
                    truncation_reason = (
                        "aggregate_limit"
                        if available_aggregate < MAX_OVERFLOW_CHUNK_BYTES
                        else "chunk_limit"
                    )
                    break
                payload_lines.append(line)
                payload_bytes += len(line)

            overflow_bytes = b"".join(payload_lines)
            written_count = len(payload_lines)
            omitted_overflow_count = max(0, len(tail_changes) - written_count)
            truncated = omitted_overflow_count > 0
            if truncated and truncation_reason is None:
                truncation_reason = "bounded_limit"
            try:
                directory.write_bytes(overflow_name, overflow_bytes)
            except BaseException as error:
                state.setdefault("stage_delta_overflow_errors", []).append(
                    {"stage": stage_name, **_error_record(error)}
                )
                overflow_info = {
                    "name": None,
                    "requested_name": overflow_name,
                    "bytes": 0,
                    "sha256": hashlib.sha256(b"").hexdigest(),
                    "omitted_inline_count": omitted_changes_count,
                    "written_count": 0,
                    "omitted_overflow_count": len(tail_changes),
                    "truncated": True,
                    "artifact_written": False,
                    "format": "jsonl",
                    "observation_limitation": "artifact_persistence_failed",
                }
            else:
                overflow_info = {
                    "name": overflow_name,
                    "bytes": len(overflow_bytes),
                    "sha256": hashlib.sha256(overflow_bytes).hexdigest(),
                    "omitted_inline_count": omitted_changes_count,
                    "written_count": written_count,
                    "omitted_overflow_count": omitted_overflow_count,
                    "truncated": truncated,
                    "artifact_written": True,
                    "format": "jsonl",
                    "chunk_limit_bytes": MAX_OVERFLOW_CHUNK_BYTES,
                    "aggregate_limit_bytes": MAX_OVERFLOW_AGGREGATE_BYTES,
                    "aggregate_bytes_before": prior_overflow_bytes,
                    "aggregate_bytes_after": prior_overflow_bytes + len(overflow_bytes),
                }
                if truncation_reason is not None:
                    overflow_info["truncation_reason"] = truncation_reason

    def _base_record() -> dict[str, Any]:
        rec: dict[str, Any] = {
            "stage": stage_name,
            "staged_changes": inline_staged_changes,
            "staged_changes_total_count": len(staged_changes),
            "staged_changes_inline_count": len(inline_staged_changes),
            "staged_changes_omitted_count": omitted_changes_count,
            "staged_paths": inline_staged_paths,
            "staged_paths_total_count": len(all_staged_paths),
            "staged_paths_inline_count": len(inline_staged_paths),
            "staged_paths_omitted_count": omitted_paths_count,
            "intent_to_add_paths": inline_intent_to_add_paths,
            "intent_to_add_paths_total_count": len(all_intent_to_add_paths),
            "intent_to_add_paths_inline_count": len(inline_intent_to_add_paths),
            "intent_to_add_paths_omitted_count": omitted_intent_count,
            "unmerged_paths": inline_unmerged_paths,
            "unmerged_paths_total_count": len(all_unmerged_paths),
            "unmerged_paths_inline_count": len(inline_unmerged_paths),
            "unmerged_paths_omitted_count": omitted_unmerged_count,
            "status_counts": status_counts,
            "type_counts": type_counts,
        }
        if overflow_info is not None:
            rec["overflow"] = overflow_info
            rec["overflow_artifact"] = overflow_info
        return rec

    if unsafe_reason:
        record = {
            **_base_record(),
            "before_index": current_index,
            "after_index": current_index,
            "restored_clean": False,
            "safety": "unsafe",
            "reason": unsafe_reason,
            "observation_limitations": {
                "normalization": "unsafe_not_attempted",
                "reason": unsafe_reason,
                "index": index_limitations,
            },
        }
        state.setdefault("index_normalizations", []).append(record)
        _refresh_overflow_aggregate(state)
        if not in_failure_path and not protected_review_index:
            if active_ops:
                raise gitstate_module.GitStateError(
                    "ENTRY_ACTIVE_GIT_OPERATION",
                    f"cannot normalize index: active git operations: {', '.join(active_ops)}",
                )
            if all_unmerged_paths:
                raise gitstate_module.GitStateError(
                    "ENTRY_UNMERGED",
                    f"cannot normalize index with unmerged paths: {all_unmerged_paths[0]}",
                )
            if head_moved:
                raise gitstate_module.GitStateError(
                    "HEAD_MOVED_WITHOUT_COMMIT",
                    "cannot normalize index after an unaccounted HEAD change; preserve current state",
                )
        return record

    # Safe to reset index back to HEAD without modifying worktree
    reset_res = subprocess.run(
        ["git", "reset", "-q", "HEAD", "--", ":/"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if reset_res.returncode != 0:
        err_msg = reset_res.stderr.decode("utf-8", "replace").strip()
        record = {
            **_base_record(),
            "before_index": current_index,
            "after_index": gitstate_module.index_identity(root),
            "restored_clean": False,
            "safety": "reset_command_failed",
            "observation_limitations": {"error": err_msg, "index": index_limitations},
        }
        state.setdefault("index_normalizations", []).append(record)
        _refresh_overflow_aggregate(state)
        if not in_failure_path:
            raise gitstate_module.GitStateError("INDEX_NORMALIZATION_FAILED", f"git reset failed: {err_msg}")
        return record

    restored_index = gitstate_module.index_identity(root)
    record = {
        **_base_record(),
        "before_index": current_index,
        "after_index": restored_index,
        "restored_clean": restored_index == expected_index,
        "safety": "safe_restored",
        "observation_limitations": {"index": index_limitations},
    }
    state.setdefault("index_normalizations", []).append(record)
    _refresh_overflow_aggregate(state)
    if not record["restored_clean"] and not in_failure_path:
        raise gitstate_module.GitStateError(
            "INDEX_NORMALIZATION_FAILED", "index could not be restored to the safe entry posture"
        )
    return record


def _status_name(status_char: str) -> str:
    mapping = {
        "A": "added",
        "M": "modified",
        "D": "deleted",
        "T": "type_changed",
        "R": "renamed",
    }
    if status_char in mapping:
        return mapping[status_char]
    if status_char in mapping.values():
        return status_char
    return "unknown"


def _record_deltas_to_ledger(
    state: dict[str, Any],
    stage_name: str,
    before_tree_sha: str,
    after_tree_sha: str,
    before_index: Any,
    after_index: Any,
    stage_deltas: list[dict[str, Any]],
    metadata_scan: dict[str, Any],
    directory: Any = None,
    before_authority: dict[str, Any] | None = None,
    after_authority: dict[str, Any] | None = None,
    raw_after_index: Any = None,
    raw_after_authority: dict[str, Any] | None = None,
    boundary_observation_limitations: list[dict[str, Any]] | None = None,
) -> None:
    """Store bounded deltas in the ledger and write bounded overflow evidence."""
    ledger = state.setdefault(
        "stage_delta_ledger",
        {"schema": STAGE_DELTA_SCHEMA, "deltas": [], "stages": {}},
    )
    if not isinstance(ledger, dict):
        raise TypeError("stage_delta_ledger must be a mapping")
    stages = ledger.setdefault("stages", {})
    if not isinstance(stages, dict):
        raise TypeError("stage_delta_ledger.stages must be a mapping")

    total_count = len(stage_deltas)
    inline_deltas = stage_deltas[:MAX_STAGE_INLINE_DELTAS]
    omitted_count = max(0, total_count - len(inline_deltas))

    overflow_info: dict[str, Any] | None = None
    overflow_name = f"{stage_name}.deltas.jsonl"
    tail_deltas = stage_deltas[MAX_STAGE_INLINE_DELTAS:]

    # A stage may be re-captured during recovery.  Exclude its prior artifact
    # from the aggregate budget because the run-owned name is replaced below.
    # Index-normalization artifacts are included in the same shared budget.
    prior_overflow_bytes = _overflow_bytes_in_use(
        state, exclude_names={overflow_name}
    )
    available_aggregate = max(
        0, MAX_OVERFLOW_AGGREGATE_BYTES - prior_overflow_bytes
    )

    if omitted_count > 0:
        if directory is None:
            overflow_info = {
                "name": None,
                "requested_name": overflow_name,
                "bytes": 0,
                "sha256": hashlib.sha256(b"").hexdigest(),
                "omitted_inline_count": omitted_count,
                "written_count": 0,
                "omitted_overflow_count": len(tail_deltas),
                "truncated": True,
                "artifact_written": False,
                "format": "jsonl",
                "observation_limitation": "run_directory_unavailable",
            }
        else:
            # Emit complete JSON objects only.  A byte slice of a serialized
            # stream can leave an unparsable tail and is therefore not valid
            # bounded evidence.  The first records are retained deterministically.
            payload_lines: list[bytes] = []
            payload_bytes = 0
            truncation_reason: str | None = None
            chunk_budget = min(MAX_OVERFLOW_CHUNK_BYTES, available_aggregate)
            for delta in tail_deltas:
                try:
                    line = (json.dumps(delta, sort_keys=True) + "\n").encode("utf-8")
                except (TypeError, ValueError, UnicodeError) as error:
                    truncation_reason = "serialization_error"
                    state.setdefault("stage_delta_overflow_errors", []).append(
                        {"stage": stage_name, **_error_record(error)}
                    )
                    break
                if len(line) > MAX_OVERFLOW_CHUNK_BYTES:
                    truncation_reason = "record_exceeds_chunk_limit"
                    break
                if payload_bytes + len(line) > chunk_budget:
                    truncation_reason = (
                        "aggregate_limit"
                        if available_aggregate < MAX_OVERFLOW_CHUNK_BYTES
                        else "chunk_limit"
                    )
                    break
                payload_lines.append(line)
                payload_bytes += len(line)

            overflow_bytes = b"".join(payload_lines)
            written_count = len(payload_lines)
            omitted_overflow_count = max(0, len(tail_deltas) - written_count)
            truncated = omitted_overflow_count > 0
            if truncated and truncation_reason is None:
                truncation_reason = "bounded_limit"
            try:
                directory.write_bytes(overflow_name, overflow_bytes)
            except BaseException as error:
                state.setdefault("stage_delta_overflow_errors", []).append(
                    {"stage": stage_name, **_error_record(error)}
                )
                overflow_info = {
                    "name": None,
                    "requested_name": overflow_name,
                    "bytes": 0,
                    "sha256": hashlib.sha256(b"").hexdigest(),
                    "omitted_inline_count": omitted_count,
                    "written_count": 0,
                    "omitted_overflow_count": len(tail_deltas),
                    "truncated": True,
                    "artifact_written": False,
                    "format": "jsonl",
                    "observation_limitation": "artifact_persistence_failed",
                }
            else:
                overflow_info = {
                    "name": overflow_name,
                    "bytes": len(overflow_bytes),
                    "sha256": hashlib.sha256(overflow_bytes).hexdigest(),
                    "omitted_inline_count": omitted_count,
                    "written_count": written_count,
                    "omitted_overflow_count": omitted_overflow_count,
                    "truncated": truncated,
                    "artifact_written": True,
                    "format": "jsonl",
                    "chunk_limit_bytes": MAX_OVERFLOW_CHUNK_BYTES,
                    "aggregate_limit_bytes": MAX_OVERFLOW_AGGREGATE_BYTES,
                    "aggregate_bytes_before": prior_overflow_bytes,
                    "aggregate_bytes_after": prior_overflow_bytes + len(overflow_bytes),
                }
                if truncation_reason is not None:
                    overflow_info["truncation_reason"] = truncation_reason

    status_counts: dict[str, int] = {}
    classification_counts: dict[str, int] = {}
    classification_status_counts: dict[str, dict[str, int]] = {}
    for d in stage_deltas:
        st = str(d.get("status", "unknown"))
        cl = str(d.get("classification", "unknown"))
        status_counts[st] = status_counts.get(st, 0) + 1
        classification_counts[cl] = classification_counts.get(cl, 0) + 1
        cl_dict = classification_status_counts.setdefault(cl, {})
        cl_dict[st] = cl_dict.get(st, 0) + 1

    product_all = [
        d["path"] for d in stage_deltas if d.get("classification") == "product" and isinstance(d.get("path"), str)
    ]
    meta_all = [
        d["path"] for d in stage_deltas if d.get("classification") == "operational_metadata" and isinstance(d.get("path"), str)
    ]
    git_all = [
        d["path"] for d in stage_deltas if d.get("classification") == "git_authority" and isinstance(d.get("path"), str)
    ]

    inline_product_paths = product_all[:MAX_STAGE_INLINE_DELTAS]
    inline_meta_paths = meta_all[:MAX_STAGE_INLINE_DELTAS]
    inline_git_paths = git_all[:MAX_STAGE_INLINE_DELTAS]

    metadata_scan = metadata_scan if isinstance(metadata_scan, dict) else {}
    omitted_roots = metadata_scan.get("omitted_roots", [])
    if not isinstance(omitted_roots, list):
        omitted_roots = list(omitted_roots) if isinstance(omitted_roots, (tuple, set)) else []
    omitted_roots = sorted({str(root) for root in omitted_roots})
    boundary_limitations = [
        item for item in (boundary_observation_limitations or [])
        if isinstance(item, dict)
    ]
    observation_completeness = (
        "truncated"
        if omitted_count > 0 or omitted_roots or boundary_limitations
        else "bounded"
    )

    stage_normalizations = [
        record
        for record in state.get("index_normalizations", [])
        if isinstance(record, dict) and record.get("stage") == stage_name
    ]
    stage_record = {
        "stage": stage_name,
        "before_tree": before_tree_sha,
        "after_tree": after_tree_sha,
        "before_index": before_index,
        "after_index": after_index,
        "raw_after_index": after_index if raw_after_index is None else raw_after_index,
        "deltas": inline_deltas,
        "total_deltas_count": total_count,
        "inline_deltas_count": len(inline_deltas),
        "omitted_deltas_count": omitted_count,
        "status_counts": status_counts,
        "classification_counts": classification_counts,
        "classification_status_counts": classification_status_counts,
        "product_paths": inline_product_paths,
        "product_paths_total_count": len(product_all),
        "product_paths_inline_count": len(inline_product_paths),
        "product_paths_omitted_count": max(0, len(product_all) - len(inline_product_paths)),
        "operational_metadata_paths": inline_meta_paths,
        "operational_metadata_paths_total_count": len(meta_all),
        "operational_metadata_paths_inline_count": len(inline_meta_paths),
        "operational_metadata_paths_omitted_count": max(0, len(meta_all) - len(inline_meta_paths)),
        "git_authority_paths": inline_git_paths,
        "git_authority_paths_total_count": len(git_all),
        "git_authority_paths_inline_count": len(inline_git_paths),
        "git_authority_paths_omitted_count": max(0, len(git_all) - len(inline_git_paths)),
        "overflow": overflow_info,
        "overflow_artifact": overflow_info,
        "before_git_authority": before_authority or {},
        "after_git_authority": after_authority or {},
        "raw_after_git_authority": raw_after_authority or after_authority or {},
        "index_normalizations": stage_normalizations,
        "index_normalization": stage_normalizations[-1] if stage_normalizations else None,
        "index_normalization_count": len(stage_normalizations),
        "observation_completeness": observation_completeness,
        "observation_limitations": {
            "classification": "external_or_unobserved",
            "scope": "Git product paths and bounded built-in metadata roots only",
            "metadata_change_basis": "stat observations; touch may register a change",
            "metadata_scan": metadata_scan,
            "omitted_metadata_roots": omitted_roots,
            "omitted_metadata_roots_count": len(omitted_roots),
            "omitted_stage_deltas_count": omitted_count,
            "boundary": boundary_limitations,
        },
    }
    if stage_name in stages:
        from .metadata_noop import retain_observation
        retain_observation(state, stage_name, stages[stage_name])
    stages[stage_name] = stage_record

    # Rebuild the whole-run inline view from stage records.  The stage records
    # retain complete counts and bounded per-stage prefixes, so finalization
    # never depends on this capped convenience list.
    run_inline: list[dict[str, Any]] = []
    total_deltas_count = 0
    total_stage_inline_count = 0
    total_stage_omitted_count = 0
    run_status_counts: dict[str, int] = {}
    run_classification_counts: dict[str, int] = {}
    run_classification_status_counts: dict[str, dict[str, int]] = {}
    run_stage_counts: dict[str, int] = {}
    run_omitted_by_stage: dict[str, int] = {}
    metadata_omitted_by_stage: dict[str, list[str]] = {}
    for prior_stage, prior_info in stages.items():
        if not isinstance(prior_info, dict):
            continue
        prior_inline = prior_info.get("deltas", [])
        if not isinstance(prior_inline, list):
            prior_inline = []
        try:
            prior_total = max(0, int(prior_info.get("total_deltas_count", len(prior_inline))))
        except (TypeError, ValueError):
            prior_total = len(prior_inline)
        prior_stage_inline = min(prior_total, len(prior_inline))
        prior_stage_omitted = max(0, prior_total - prior_stage_inline)
        total_deltas_count += prior_total
        total_stage_inline_count += prior_stage_inline
        total_stage_omitted_count += prior_stage_omitted
        run_stage_counts[prior_stage] = prior_total
        prior_status_counts = prior_info.get("status_counts", {})
        if isinstance(prior_status_counts, dict):
            for status, count in prior_status_counts.items():
                try:
                    key = str(status)
                    run_status_counts[key] = run_status_counts.get(key, 0) + max(0, int(count))
                except (TypeError, ValueError):
                    continue
        prior_classification_counts = prior_info.get("classification_counts", {})
        if isinstance(prior_classification_counts, dict):
            for classification, count in prior_classification_counts.items():
                try:
                    key = str(classification)
                    run_classification_counts[key] = run_classification_counts.get(key, 0) + max(0, int(count))
                except (TypeError, ValueError):
                    continue
        prior_csc = prior_info.get("classification_status_counts", {})
        if isinstance(prior_csc, dict):
            for cl_name, st_map in prior_csc.items():
                if isinstance(st_map, dict):
                    cl_acc = run_classification_status_counts.setdefault(str(cl_name), {})
                    for st_name, count in st_map.items():
                        try:
                            cl_acc[str(st_name)] = cl_acc.get(str(st_name), 0) + max(0, int(count))
                        except (TypeError, ValueError):
                            continue
        metadata_limitations = prior_info.get("observation_limitations", {})
        if isinstance(metadata_limitations, dict):
            roots = metadata_limitations.get("omitted_metadata_roots", [])
            if roots:
                metadata_omitted_by_stage[prior_stage] = list(roots)
        included = 0
        for delta in prior_inline:
            if len(run_inline) >= MAX_RUN_INLINE_DELTAS:
                break
            if isinstance(delta, dict):
                run_inline.append(delta)
                included += 1
        prior_info["run_inline_deltas_count"] = included
        prior_info["run_inline_omitted_count"] = max(0, prior_stage_inline - included)
        run_omitted_by_stage[prior_stage] = max(0, prior_total - included)

    run_omitted_count = max(0, total_deltas_count - len(run_inline))
    run_inline_omitted_count = max(0, total_stage_inline_count - len(run_inline))
    ledger["deltas"] = run_inline
    ledger["total_deltas_count"] = total_deltas_count
    ledger["inline_deltas_count"] = len(run_inline)
    ledger["omitted_deltas_count"] = run_omitted_count
    ledger["stage_inline_omitted_deltas_count"] = total_stage_omitted_count
    ledger["run_inline_omitted_deltas_count"] = run_inline_omitted_count
    ledger["status_counts"] = run_status_counts
    ledger["classification_counts"] = run_classification_counts
    ledger["classification_status_counts"] = run_classification_status_counts
    ledger["stage_counts"] = run_stage_counts
    ledger["omitted_deltas_by_stage"] = run_omitted_by_stage

    # Keep the aggregate derived from both stage-delta and index-normalization
    # artifacts.  The shared helper also sees run-level normalization records
    # that are not yet attached to a stage record.
    shared_overflow = _refresh_overflow_aggregate(state)
    overflow_truncated = bool(shared_overflow.get("truncated"))
    stage_truncated = any(
        isinstance(info, dict) and info.get("observation_completeness") == "truncated"
        for info in stages.values()
    )
    ledger["observation_completeness"] = (
        "truncated"
        if run_omitted_count > 0 or stage_truncated or overflow_truncated
        else "bounded"
    )
    ledger["observation_limitations"] = {
        "classification": "external_or_unobserved",
        "scope": "Git product paths and bounded built-in metadata roots only",
        "total_deltas_count": total_deltas_count,
        "omitted_deltas_count": run_omitted_count,
        "stage_inline_omitted_deltas_count": total_stage_omitted_count,
        "run_inline_omitted_deltas_count": run_inline_omitted_count,
        "omitted_metadata_roots_by_stage": metadata_omitted_by_stage,
        "overflow_aggregate": ledger["overflow_aggregate"],
    }


def capture_stage_boundary(
    root: Path,
    *args: Any,
    stage: str | None = None,
    stage_name: str | None = None,
    before_tree: Any = None,
    after_tree: Any = None,
    before_index: Any = None,
    after_index: Any = None,
    state: dict[str, Any] | None = None,
    entry: Any = None,
    record_mutation_alias: bool = True,
    directory: Any = None,
    before_authority: dict[str, Any] | None = None,
    after_authority: dict[str, Any] | None = None,
    raw_after_index: Any = None,
    raw_after_authority: dict[str, Any] | None = None,
    boundary_observation_limitations: list[dict[str, Any]] | None = None,
    replace_existing: bool = False,
    before_metadata: dict[str, dict[str, Any]] | None = None,
    before_metadata_scan: dict[str, Any] | None = None,
    tracked_paths: set[str] | None = None,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """Capture consecutive boundary deltas for a stage and update the ledger."""
    if args:
        if isinstance(args[0], dict):
            state = args[0]
            if len(args) > 1 and isinstance(args[1], str):
                stage = args[1]
        elif isinstance(args[0], str):
            stage_name = args[0]
            if len(args) > 1:
                before_tree = args[1]
            if len(args) > 2:
                before_index = args[2]
            if len(args) > 3:
                after_tree = args[3]
            if len(args) > 4:
                after_index = args[4]
            if len(args) > 5 and isinstance(args[5], dict):
                state = args[5]

    if state is None:
        state = kwargs.get("state", {})

    actual_stage = stage or stage_name or "unknown"
    stage_name = actual_stage

    # Check if stage was already closed by an active boundary in this attempt
    ledger = state.get("stage_delta_ledger")
    if (
        isinstance(ledger, dict)
        and stage_name in ledger.get("stages", {})
        and not replace_existing
    ):
        existing = ledger["stages"][stage_name].get("deltas", [])
        if existing is not None:
            return list(existing)

    if isinstance(before_tree, dict):
        before_tree_sha = str(before_tree.get("tree", ""))
    elif isinstance(before_tree, str):
        before_tree_sha = before_tree
    elif entry is not None:
        before_tree_sha = str(getattr(entry, "tree", ""))
    else:
        before_tree_sha = ""

    if isinstance(after_tree, dict):
        after_tree_sha = str(after_tree.get("tree", ""))
    elif isinstance(after_tree, str):
        after_tree_sha = after_tree
    else:
        from . import candidate as candidate_module
        after_tree_sha = str(candidate_module.tree_identity(root)["tree"])

    if before_index is not None:
        before_idx = before_index
    elif entry is not None:
        before_idx = getattr(entry, "index_identity", {})
    else:
        before_idx = {}

    if after_index is not None:
        after_idx = after_index
    else:
        after_idx = gitstate_module.index_identity(root)

    before_index = before_idx
    after_index = after_idx
    stage_deltas: list[dict[str, Any]] = []

    # 1. Product changes
    if before_tree_sha and after_tree_sha and before_tree_sha != after_tree_sha:
        try:
            changes = gitstate_module.phase_delta(root, before_tree_sha, after_tree_sha)
        except gitstate_module.GitStateError as error:
            # Ensure rolling metadata baseline updates even if phase_delta fails early
            try:
                state["_previous_operational_metadata"] = scan_operational_metadata(root)
                state["_last_closed_stage"] = stage_name
            except BaseException:
                pass
            from .dispatch import DispatchError
            raise DispatchError(error.detail, error.code) from error
        for change in changes:
            status = _status_name(change.status)
            path = change.path
            tracked_before = is_tracked_in_tree(root, before_tree_sha, path)
            tracked_after = is_tracked_in_tree(root, after_tree_sha, path)
            delta_record = {
                "stage": stage_name,
                "path": path,
                "source_path": None,
                "status": status,
                "classification": "product",
                "tracked_before": tracked_before,
                "tracked_after": tracked_after,
                "ignored_when_observable": False,
                "introduced_by_stage": stage_name,
                "included_in_product_candidate": True,
                "included_in_finalization": None,
                "enforcement_outcome": "admitted",
            }
            stage_deltas.append(delta_record)

    # 2. Operational metadata changes
    observation: dict[str, Any] = {}
    current_metadata = scan_operational_metadata(root, observation=observation)
    metadata_tracked_paths = tracked_paths
    if metadata_tracked_paths is None:
        metadata_tracked_paths = _tracked_path_set(root, observation=observation)
    previous_metadata = (
        before_metadata
        if before_metadata is not None
        else state.get("_previous_operational_metadata", {})
    )

    for path, info in sorted(current_metadata.items()):
        if _metadata_path_is_tracked(root, path, metadata_tracked_paths):
            continue
        if path not in previous_metadata:
            stage_deltas.append({
                "stage": stage_name,
                "path": path,
                "source_path": None,
                "status": "added",
                "classification": "operational_metadata",
                "tracked_before": False,
                "tracked_after": False,
                "ignored_when_observable": _ignored(root, path),
                "introduced_by_stage": stage_name,
                "included_in_product_candidate": False,
                "included_in_finalization": False,
                "enforcement_outcome": "retained_metadata",
            })
        else:
            prev = previous_metadata[path]
            if (
                info.get("size_bytes") != prev.get("size_bytes")
                or info.get("mtime") != prev.get("mtime")
            ):
                stage_deltas.append({
                    "stage": stage_name,
                    "path": path,
                    "source_path": None,
                    "status": "modified",
                    "classification": "operational_metadata",
                    "tracked_before": False,
                    "tracked_after": False,
                    "ignored_when_observable": _ignored(root, path),
                    "introduced_by_stage": stage_name,
                    "included_in_product_candidate": False,
                    "included_in_finalization": False,
                    "enforcement_outcome": "retained_metadata",
                })

    for path in sorted(previous_metadata):
        if _metadata_path_is_tracked(root, path, metadata_tracked_paths):
            continue
        if path not in current_metadata and not os.path.lexists(root / path):
            stage_deltas.append({
                "stage": stage_name,
                "path": path,
                "source_path": None,
                "status": "deleted",
                "classification": "operational_metadata",
                "tracked_before": False,
                "tracked_after": False,
                "ignored_when_observable": _ignored(root, path),
                "introduced_by_stage": stage_name,
                "included_in_product_candidate": False,
                "included_in_finalization": False,
                "enforcement_outcome": "retained_metadata",
            })

    state["_previous_operational_metadata"] = current_metadata
    state["_last_closed_stage"] = stage_name

    # 3. Git authority changes
    if before_authority and after_authority:
        if before_authority.get("branch") != after_authority.get("branch"):
            stage_deltas.append({
                "stage": stage_name,
                "path": "git:branch",
                "source_path": None,
                "status": "modified",
                "classification": "git_authority",
                "tracked_before": False,
                "tracked_after": False,
                "ignored_when_observable": False,
                "introduced_by_stage": stage_name,
                "included_in_product_candidate": False,
                "included_in_finalization": False,
                "enforcement_outcome": "observed_authority_change",
                "authority_event": {
                    "kind": "branch_change",
                    "before": before_authority.get("branch"),
                    "after": after_authority.get("branch"),
                },
            })
        if before_authority.get("head") != after_authority.get("head"):
            stage_deltas.append({
                "stage": stage_name,
                "path": "git:head",
                "source_path": None,
                "status": "modified",
                "classification": "git_authority",
                "tracked_before": False,
                "tracked_after": False,
                "ignored_when_observable": False,
                "introduced_by_stage": stage_name,
                "included_in_product_candidate": False,
                "included_in_finalization": False,
                "enforcement_outcome": "observed_authority_change",
                "authority_event": {
                    "kind": "head_change",
                    "before": before_authority.get("head"),
                    "after": after_authority.get("head"),
                },
            })
        if before_authority.get("active_operations") != after_authority.get("active_operations"):
            stage_deltas.append({
                "stage": stage_name,
                "path": "git:active_operations",
                "source_path": None,
                "status": "modified" if after_authority.get("active_operations") else "deleted",
                "classification": "git_authority",
                "tracked_before": False,
                "tracked_after": False,
                "ignored_when_observable": False,
                "introduced_by_stage": stage_name,
                "included_in_product_candidate": False,
                "included_in_finalization": False,
                "enforcement_outcome": "observed_authority_change",
                "authority_event": {
                    "kind": "active_operations_change",
                    "before": before_authority.get("active_operations"),
                    "after": after_authority.get("active_operations"),
                },
            })

    # 4. Add to ledger
    _record_deltas_to_ledger(
        state,
        stage_name,
        before_tree_sha,
        after_tree_sha,
        before_index,
        after_index,
        stage_deltas,
        observation,
        directory=directory,
        before_authority=before_authority,
        after_authority=after_authority,
        raw_after_index=raw_after_index,
        raw_after_authority=raw_after_authority,
        boundary_observation_limitations=boundary_observation_limitations,
    )

    # 5. Record backward-compatible mutation keys if stage changed product
    if record_mutation_alias and stage_name in (
        "plan", "plan_review", "final_review", "work_review"
    ):
        prod_paths = [
            d["path"] for d in stage_deltas if d["classification"] == "product"
        ]
        if prod_paths or before_index != after_index:
            state[f"{stage_name}_mutation"] = {
                "expected_tree": before_tree_sha,
                "observed_tree": after_tree_sha,
                "paths": prod_paths,
                "expected_index": before_index,
                "observed_index": after_index,
            }

    return stage_deltas


class StageBoundary:
    """Coherent stage boundary manager recording pre- and post-invocation observations."""

    def __init__(
        self,
        root: Path,
        stage_name: str,
        state: dict[str, Any],
        entry: Any = None,
        directory: Any = None,
    ) -> None:
        self.root = root
        self.stage_name = stage_name
        self.state = state
        self.entry = entry
        self.directory = directory
        self.closed = False

        ledger = state.get("stage_delta_ledger")
        self.replace_existing = bool(
            isinstance(ledger, dict)
            and isinstance(ledger.get("stages"), dict)
            and stage_name in ledger["stages"]
        )

        from . import candidate as candidate_module
        try:
            self.before_tree = candidate_module.tree_identity(root)
        except BaseException as error:
            self.before_tree = {
                "tree": getattr(entry, "tree", ""),
                "observation_unavailable": True,
            }
            _append_stage_observation_limitation(
                state,
                stage_name,
                {"kind": "before_tree_unavailable", **_error_record(error)},
            )
        try:
            self.before_index = gitstate_module.index_identity(root)
        except BaseException as error:
            self.before_index = getattr(entry, "index_identity", {})
            _append_stage_observation_limitation(
                state,
                stage_name,
                {"kind": "before_index_unavailable", **_error_record(error)},
            )
        self.before_authority = observe_git_authority(root)
        obs: dict[str, Any] = {}
        self.before_metadata = scan_operational_metadata(root, observation=obs)
        self.before_tracked_paths = _tracked_path_set(root, observation=obs)
        self.before_metadata_scan = obs

        # Detect between-stages metadata deltas if prior baseline exists
        prior_metadata = state.get("_previous_operational_metadata")
        if isinstance(prior_metadata, dict):
            interstage_deltas: list[dict[str, Any]] = []
            for path, info in sorted(self.before_metadata.items()):
                if _metadata_path_is_tracked(root, path, self.before_tracked_paths):
                    continue
                if path not in prior_metadata:
                    interstage_deltas.append({
                        "path": path,
                        "status": "added",
                        "classification": "operational_metadata",
                    })
                else:
                    prev = prior_metadata[path]
                    if (
                        info.get("size_bytes") != prev.get("size_bytes")
                        or info.get("mtime") != prev.get("mtime")
                    ):
                        interstage_deltas.append({
                            "path": path,
                            "status": "modified",
                            "classification": "operational_metadata",
                        })
            for path in sorted(prior_metadata):
                if _metadata_path_is_tracked(root, path, self.before_tracked_paths):
                    continue
                if path not in self.before_metadata and not os.path.lexists(root / path):
                    interstage_deltas.append({
                        "path": path,
                        "status": "deleted",
                        "classification": "operational_metadata",
                    })
            if interstage_deltas:
                preceding = state.get("_last_closed_stage")
                rec = {
                    "kind": "between_stages",
                    "preceding_stage": preceding,
                    "following_stage": stage_name,
                    "deltas": interstage_deltas[:MAX_STAGE_INLINE_DELTAS],
                    "total_deltas_count": len(interstage_deltas),
                    "inline_deltas_count": min(len(interstage_deltas), MAX_STAGE_INLINE_DELTAS),
                    "omitted_deltas_count": max(0, len(interstage_deltas) - MAX_STAGE_INLINE_DELTAS),
                    "paths": [d["path"] for d in interstage_deltas[:MAX_STAGE_INLINE_DELTAS]],
                    "paths_total_count": len(interstage_deltas),
                    "paths_inline_count": min(len(interstage_deltas), MAX_STAGE_INLINE_DELTAS),
                    "paths_omitted_count": max(0, len(interstage_deltas) - MAX_STAGE_INLINE_DELTAS),
                }
                state.setdefault("interstage_observations", []).append(rec)

    def close(
        self,
        *,
        ok: bool = True,
        error: Any = None,
        exit_code: int | None = None,
    ) -> list[dict[str, Any]]:
        """Close boundary on success or failure, normalizing index safely."""
        transport_error = error
        if self.closed:
            return self.state.get("stage_delta_ledger", {}).get("stages", {}).get(self.stage_name, {}).get("deltas", [])
        self.closed = True

        from . import candidate as candidate_module

        # 1. Inspect raw post-execution state
        try:
            raw_after_index = gitstate_module.index_identity(self.root)
        except BaseException as error:
            raw_after_index = self.before_index
            _append_stage_observation_limitation(
                self.state,
                self.stage_name,
                {"kind": "raw_after_index_unavailable", **_error_record(error)},
            )
        raw_after_authority = observe_git_authority(self.root)

        # 2. Normalize index safely if needed
        norm_record = None
        normalization_error: BaseException | None = None
        try:
            expected = getattr(self.entry, "index_identity", self.before_index)
            norm_record = normalize_index_if_needed(
                self.root,
                expected,
                stage_name=self.stage_name,
                state=self.state,
                in_failure_path=not ok,
                directory=self.directory,
            )
        except BaseException as norm_err:
            normalization_error = norm_err
            self.state["index_normalization_error"] = {
                "stage": self.stage_name,
                **_error_record(norm_err),
            }
            _append_stage_observation_limitation(
                self.state,
                self.stage_name,
                {"kind": "index_normalization_failed", **_error_record(norm_err)},
            )

        # 3. Post-normalization observations
        after_tree_error: BaseException | None = None
        try:
            after_tree = candidate_module.tree_identity(self.root)
        except BaseException as error:
            after_tree_error = error
            # An empty tree identity is explicit evidence that the candidate
            # could not be observed; reusing before_tree would falsely report
            # unchanged product bytes.
            after_tree = {
                "tree": "",
                "observation_unavailable": True,
            }
            _append_stage_observation_limitation(
                self.state,
                self.stage_name,
                {"kind": "after_tree_unavailable", **_error_record(error)},
            )
        after_index_observed = True
        try:
            after_index = gitstate_module.index_identity(self.root)
        except BaseException as error:
            after_index_observed = False
            after_index = raw_after_index
            _append_stage_observation_limitation(
                self.state,
                self.stage_name,
                {"kind": "after_index_unavailable", **_error_record(error)},
            )
        after_authority = observe_git_authority(self.root)

        if isinstance(norm_record, dict):
            norm_record["raw_after_index"] = raw_after_index
            norm_record["raw_after_git_authority"] = raw_after_authority
            norm_record["after_git_authority"] = after_authority

        boundary_observations = self.state.setdefault(
            "stage_boundary_observations", {}
        )
        if not isinstance(boundary_observations, dict):
            boundary_observations = {}
            self.state["stage_boundary_observations"] = boundary_observations
        boundary_observations[self.stage_name] = {
            "before_tree": self.before_tree,
            "after_tree": after_tree,
            "before_index": self.before_index,
            "raw_after_index": raw_after_index,
            "after_index": after_index,
            "before_git_authority": self.before_authority,
            "raw_after_git_authority": raw_after_authority,
            "after_git_authority": after_authority,
            "observation_limitations": [
                record
                for record in self.state.get("stage_observation_limitations", [])
                if isinstance(record, dict) and record.get("stage") == self.stage_name
            ],
        }

        # 4. Capture boundary deltas
        capture_error: BaseException | None = None
        try:
            deltas = capture_stage_boundary(
                self.root,
                stage=self.stage_name,
                before_tree=self.before_tree,
                after_tree=after_tree,
                before_index=self.before_index,
                after_index=after_index,
                state=self.state,
                entry=self.entry,
                directory=self.directory,
                before_authority=self.before_authority,
                after_authority=after_authority,
                raw_after_index=raw_after_index,
                raw_after_authority=raw_after_authority,
                boundary_observation_limitations=boundary_observations[self.stage_name].get(
                    "observation_limitations", []
                ),
                replace_existing=self.replace_existing,
                before_metadata=self.before_metadata,
                before_metadata_scan=self.before_metadata_scan,
                tracked_paths=(
                    self.before_tracked_paths
                    if after_index_observed and after_index == self.before_index
                    else None
                ),
            )
        except BaseException as error:
            capture_error = error
            evidence = {"stage": self.stage_name, **_error_record(error)}
            self.state["stage_delta_capture_error"] = evidence
            self.state.setdefault("stage_delta_capture_errors", []).append(evidence)
            _append_stage_observation_limitation(
                self.state,
                self.stage_name,
                {"kind": "stage_delta_capture_failed", **_error_record(error)},
            )
            deltas = []

        # Review drift is fatal even when transport failed. Raw provider evidence
        # remains transport evidence and cannot satisfy a semantic checkpoint.
        from . import review_binding
        review_binding.verify(
            self.root, self.state, self.stage_name, after_tree, after_index,
            transport={"ok": ok, "exit_code": exit_code, "error": _error_record(transport_error) if transport_error else None},
        )

        # 5. On failure, update candidate accounting and monotonic manager disposition
        if not ok:
            from . import failure_boundary as failure_boundary_module
            try:
                failure_boundary_module.record_mutating_failure(
                    self.state,
                    self.entry,
                    stage_name=self.stage_name,
                    after_tree=after_tree,
                    after_index=after_index,
                )
            except Exception as fb_err:
                self.state["failure_boundary_error"] = {
                    "code": getattr(fb_err, "code", type(fb_err).__name__),
                    "detail": str(fb_err),
                }

        # Failure-path callers must retain the provider's primary transport or
        # interruption exception.  Success-path normalization/capture errors
        # are deferred until the best bounded boundary evidence is recorded.
        if ok:
            if capture_error is not None:
                raise capture_error
            if normalization_error is not None:
                raise normalization_error
            if after_tree_error is not None:
                # Candidate observation failure is an actual boundary failure,
                # while its limitation remains in the captured stage record.
                raise after_tree_error

        return deltas


def open_stage_boundary(
    root: Path,
    stage_name: str,
    state: dict[str, Any],
    entry: Any = None,
    directory: Any = None,
) -> StageBoundary:
    """Factory creating and arming a stage boundary prior to provider invocation."""
    return StageBoundary(
        root=root,
        stage_name=stage_name,
        state=state,
        entry=entry,
        directory=directory,
    )


def _bounded_view_counts(
    record: dict[str, Any], values_key: str
) -> tuple[int | None, int, int | None]:
    """Read total, inline, and omitted counts for a bounded list view."""
    values = record.get(values_key)
    inline_fallback = len(values) if isinstance(values, list) else 0

    def count(key: str) -> int | None:
        value = record.get(key)
        if isinstance(value, bool):
            return int(value)
        try:
            return max(0, int(value)) if value is not None else None
        except (TypeError, ValueError):
            return None

    total = count(f"{values_key}_total_count")
    inline = count(f"{values_key}_inline_count")
    omitted = count(f"{values_key}_omitted_count")
    if inline is None:
        inline = inline_fallback
    if total is None and omitted is not None:
        total = inline + omitted
    if omitted is None and total is not None:
        omitted = max(0, total - inline)
    return total, inline, omitted


def _bounded_count_text(
    total: int | None, inline: int, omitted: int | None
) -> str:
    """Format bounded counts without treating an unknown total as complete."""
    if total is None:
        return f"{inline} inline path(s); total unavailable"
    suffix = f"{inline} inline"
    if omitted is not None:
        suffix += f", {omitted} omitted"
    return f"{total} path(s) ({suffix})"


def format_stage_deltas_summary(state: dict[str, Any]) -> str:
    """Format human-meaningful stage-delta summary for prompt injection."""
    ledger = state.get("stage_delta_ledger")
    deltas = ledger.get("deltas", []) if isinstance(ledger, dict) else []
    if not isinstance(deltas, list):
        deltas = []
    normalizations = state.get("index_normalizations", [])
    if not isinstance(normalizations, list):
        normalizations = []
    if not normalizations and isinstance(ledger, dict):
        for stage_info in (ledger.get("stages", {}) or {}).values():
            if not isinstance(stage_info, dict):
                continue
            stage_norms = stage_info.get("index_normalizations", [])
            if isinstance(stage_norms, list):
                normalizations.extend(
                    item for item in stage_norms if isinstance(item, dict)
                )
    if not deltas and not normalizations:
        return "No stage deltas recorded."
    # Put index anomalies first so a large product delta cannot hide evidence
    # needed by the next dispositioner.
    observations: list[str] = []
    for normalization in normalizations:
        if not isinstance(normalization, dict):
            continue
        stage = normalization.get("stage", "unknown")
        safety = normalization.get("safety", "observed")
        staged_values = normalization.get("staged_changes", [])
        if not isinstance(staged_values, list):
            staged_values = []
        staged = [
            item.get("path", "")
            for item in staged_values
            if isinstance(item, dict)
        ]
        intent_values = normalization.get("intent_to_add_paths", [])
        if not isinstance(intent_values, list):
            intent_values = []
        intent = [
            str(path)
            for path in intent_values
        ]
        staged_total, staged_inline, staged_omitted = _bounded_view_counts(
            normalization, "staged_changes"
        )
        intent_total, intent_inline, intent_omitted = _bounded_view_counts(
            normalization, "intent_to_add_paths"
        )
        detail = (
            f"- [{stage}] index normalization {safety}: "
            f"{_bounded_count_text(staged_total, staged_inline, staged_omitted)}"
        )
        overflow = normalization.get("overflow")
        if not isinstance(overflow, dict):
            overflow = normalization.get("overflow_artifact")
        if isinstance(overflow, dict):
            written = overflow.get("written_count")
            omitted_overflow = overflow.get("omitted_overflow_count")
            try:
                written = max(0, int(written)) if written is not None else None
            except (TypeError, ValueError):
                written = None
            try:
                omitted_overflow = (
                    max(0, int(omitted_overflow))
                    if omitted_overflow is not None
                    else None
                )
            except (TypeError, ValueError):
                omitted_overflow = None
            if written is not None or omitted_overflow is not None:
                detail += (
                    "; overflow JSONL: "
                    f"{written if written is not None else 'unknown'} written, "
                    f"{omitted_overflow if omitted_overflow is not None else 'unknown'} omitted"
                )
            elif overflow.get("artifact_written") is False:
                detail += "; overflow JSONL: unavailable"
        if staged:
            shown = ", ".join(f"`{path}`" for path in staged[:8])
            if len(staged) > 8:
                shown += f", +{len(staged) - 8} more"
            detail += f" ({shown})"
        if intent or (intent_total is not None and intent_total > 0):
            detail += (
                "; intent-to-add: "
                f"{_bounded_count_text(intent_total, intent_inline, intent_omitted)}"
            )
            shown_intent = ", ".join(f"`{path}`" for path in intent[:8])
            if len(intent) > 8:
                shown_intent += f", +{len(intent) - 8} more"
            if shown_intent:
                detail += f" [{shown_intent}]"
        observations.append(detail)

    product_observations = []
    metadata_observations = []
    for d in deltas:
        if not isinstance(d, dict):
            continue
        stage = d.get("stage", "unknown")
        path = d.get("path", "")
        status = d.get("status", "")
        classification = d.get("classification", "")
        line = f"- [{stage}] {status} {classification}: `{path}`"
        if classification == "operational_metadata":
            metadata_observations.append(line)
        else:
            product_observations.append(line)

    from .publication_summary import cumulative_lines
    observations.extend(cumulative_lines(state, MAX_PROMPT_DELTAS // 2))
    observations.append("Operational metadata observations — informational only; not disposition targets")
    metadata_limit = MAX_PROMPT_DELTAS // 8
    observations.extend(metadata_observations[:metadata_limit] or ["No inline metadata observations."])
    if len(metadata_observations) > metadata_limit:
        observations.append(
            f"{len(metadata_observations) - metadata_limit} metadata observations omitted for prompt capacity."
        )
    observations.append("Historical stage observations — verify against the cumulative Git delta above")
    observations.extend(product_observations)

    selected = observations[:MAX_PROMPT_DELTAS]
    omitted = max(0, len(observations) - len(selected))
    root_omitted = 0
    if isinstance(ledger, dict):
        try:
            root_omitted = max(0, int(ledger.get("omitted_deltas_count", 0)))
        except (TypeError, ValueError):
            root_omitted = 0
    omitted_roots_by_stage: dict[str, Any] = {}
    if isinstance(ledger, dict):
        limits = ledger.get("observation_limitations", {})
        if isinstance(limits, dict):
            roots = limits.get("omitted_metadata_roots_by_stage", {})
            if isinstance(roots, dict):
                omitted_roots_by_stage = roots

    root_notes: list[str] = []
    if root_omitted:
        root_notes.append(f"{root_omitted} ledger deltas omitted from the bounded run view")
    if omitted_roots_by_stage:
        shown_roots: list[str] = []
        for stage, roots in list(omitted_roots_by_stage.items())[:8]:
            if isinstance(roots, (list, tuple, set)):
                shown_roots.extend(f"{stage}:{root}" for root in list(roots)[:4])
        if shown_roots:
            root_notes.append(
                "metadata roots omitted from bounded scan: " + ", ".join(shown_roots[:12])
            )

    def footer() -> str:
        notes = list(root_notes)
        if omitted:
            notes.insert(0, f"{omitted} additional deltas omitted for prompt capacity")
        return f"  ({'; '.join(notes)})" if notes else ""

    # Reserve room for the omission note so the prompt itself remains bounded.
    while selected and len(("\n".join(["Observed stage changes:", *selected, footer()])).encode("utf-8")) > MAX_PROMPT_BYTES:
        selected.pop()
        omitted += 1
    lines = ["Observed stage changes:", *selected]
    note = footer()
    if note:
        lines.append(note)
    return "\n".join(lines)


def finalize_stage_deltas(state: dict[str, Any], finalized_paths: list[str]) -> None:
    """Update included_in_finalization on all ledger records after finalization."""
    ledger = state.get("stage_delta_ledger")
    if not isinstance(ledger, dict):
        return
    finalized_set = set(finalized_paths)
    for delta in ledger.get("deltas", []):
        if not isinstance(delta, dict):
            continue
        if delta.get("classification") == "product":
            delta["included_in_finalization"] = delta.get("path") in finalized_set
        else:
            delta["included_in_finalization"] = False
    for stage_info in ledger.get("stages", {}).values():
        if isinstance(stage_info, dict):
            for delta in stage_info.get("deltas", []):
                if isinstance(delta, dict):
                    if delta.get("classification") == "product":
                        delta["included_in_finalization"] = delta.get("path") in finalized_set
                    else:
                        delta["included_in_finalization"] = False
