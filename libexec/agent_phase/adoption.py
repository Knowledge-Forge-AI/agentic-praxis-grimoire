"""Explicit operator selection of sealed objects for a new substantive request.

Receipts are bounded, checksummed local authority records, not signatures or
hostile-same-user confinement. Historical evidence is verified independently.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from . import archive_verify, finalization_proof as proof, gitstate, path_disposition, run


SCHEMA = "agent-phase-adoption-v1"
MAX_BYTES = 1024 * 1024
MAX_PATHS = 1024
FIELDS = frozenset({
    "schema", "repository", "branch", "base_head", "base_tree", "source_run",
    "source_run_id", "source_manifest", "source_entry", "source_candidate_manifest",
    "source_candidate_manifest_sha256", "source_path_ownership", "adopted_paths",
    "candidate_manifest", "unselected_source_paths", "inherited_excluded_paths",
    "unrelated_committed_paths_not_adopted", "observed_entry", "observed_dirty",
    "excluded_unrelated_paths", "reason", "phase_id", "timestamp", "continuation_run_id",
    "request_sha256", "materialization", "materialization_receipt", "provider_invocations",
    "lineage_depth", "sha256",
})


class AdoptionError(ValueError):
    def __init__(self, detail: str) -> None:
        self.code, self.detail = "ADOPTION_INVALID", detail
        super().__init__(f"{self.code}: {detail}")


def encoded(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(encoded(value)).hexdigest()


def repository_identity(root: Path) -> dict:
    info = root.stat()
    return {"root": str(root), "device": info.st_dev, "inode": info.st_ino,
            "context": "."}


def canonical_paths(paths: list[str]) -> list[str]:
    if not paths or len(paths) > MAX_PATHS:
        raise AdoptionError("adoption requires 1..1024 explicitly selected paths")
    path_disposition.validate_dispositions([
        {"path": p, "disposition": "phase_owned"} for p in paths])
    selected = sorted(paths)
    if any(proof.overlaps(a, b) for a, b in zip(selected, selected[1:])):
        raise AdoptionError("selected paths have overlapping object boundaries")
    return selected


def require_paths(root: Path, selected: list[str], dirty: dict) -> None:
    for path in selected:
        target = root / path
        if target.is_dir() and not target.is_symlink():
            raise AdoptionError("adopted object is occupied by a directory")
        for parent in target.parents:
            if parent == root:
                break
            if parent.is_symlink():
                raise AdoptionError("adopted path traverses a symlink alias")
        if any(p != path and proof.overlaps(p, path) for p in dirty):
            raise AdoptionError("entry dirt overlaps an adopted object boundary")


def _source_fields(proven: proof.Proof, selected: list[str]) -> dict:
    if not set(selected) <= set(proven.manifest["paths"]):
        raise AdoptionError("selected paths are outside the sealed publication candidate")
    return {
        **({"source_controller_generation": proven.state["controller_generation"]}
           if proven.state.get("controller_generation") is not None else {}),
        "source_run": str(proven.source), "source_run_id": proven.state["run_id"],
        "source_manifest": proven.source_manifest,
        "source_entry": proven.entry.as_dict(),
        "source_candidate_manifest": proven.manifest,
        "source_candidate_manifest_sha256": digest(proven.manifest),
        "source_path_ownership": proven.state["path_ownership"],
        "adopted_paths": selected,
        "candidate_manifest": gitstate.candidate_manifest(proven.current.root,
            proven.manifest["entry_tree"], proven.manifest["candidate_tree"], paths=selected),
        "unselected_source_paths": sorted(set(proven.manifest["paths"]) - set(selected)),
        "inherited_excluded_paths": proven.state["excluded_paths"],
        "unrelated_committed_paths_not_adopted": proven.extras,
    }


def require_source_objects(source: Path, root: Path) -> None:
    """Fail before worktree capture can recreate a missing historical blob."""
    proof._repository_guard(root)
    archive_verify.verify_source_archive(source)
    from .resume_validation import load_json
    state = load_json(source, "state.json")
    manifest = gitstate.validate_candidate_manifest(state["candidate_manifest"])
    ownership = state["path_ownership"]
    trees = {manifest["entry_tree"], manifest["candidate_tree"],
             ownership["entry_tree"], ownership["raw_tree"], ownership["publication_tree"]}
    for tree in trees:
        gitstate._tree_identities(root, tree)
    if gitstate.candidate_manifest(root, manifest["entry_tree"], manifest["candidate_tree"],
            paths=list(manifest["paths"])) != manifest:
        raise AdoptionError("sealed source objects disagree with candidate manifest")


def create(source: Path, root: Path, phase_id: str, request: Any, *, reason: str,
           paths: list[str] | None = None, materialization_receipt: Path | None = None) -> dict:
    proof.require_standard_environment()
    root = gitstate.repository_root(root).resolve()
    if source.resolve().is_relative_to(root):
        raise AdoptionError("source evidence must be outside the product repository")
    if not isinstance(reason, str) or not reason.strip() or len(reason.encode()) > 4096:
        raise AdoptionError("a bounded operator reason is required")
    run.safe_component(phase_id, "continuation phase")
    require_source_objects(source, root)
    resolution_paths = _resolution_paths(materialization_receipt)
    proven = (proof.inspect(source, root, ownership_resolutions=resolution_paths)
              if resolution_paths else proof.inspect(source, root))
    selected = canonical_paths(list(proven.manifest["paths"]) if paths is None else paths)
    require_paths(root, selected, proven.current.dirty)
    if gitstate.candidate_manifest_conflicts(root, proven.current.tree,
            gitstate.candidate_manifest(root, proven.manifest["entry_tree"],
                proven.manifest["candidate_tree"], paths=selected)):
        raise AdoptionError("current adopted objects differ from the sealed candidate")
    timestamp = run.run_timestamp()
    record = {
        "schema": SCHEMA, "repository": repository_identity(root),
        "branch": proven.current.branch, "base_head": proven.current.head,
        "base_tree": gitstate._text(root, ["rev-parse", "HEAD^{tree}"], "ADOPTION_INVALID"),
        **_source_fields(proven, selected),
        "observed_entry": proven.current.as_dict(),
        "observed_dirty": proven.current.dirty,
        "excluded_unrelated_paths": sorted(set(proven.current.dirty) - set(selected)),
        "reason": reason, "phase_id": phase_id, "timestamp": timestamp,
        "continuation_run_id": run.v2_run_id(run.project_name(root), phase_id, run.v2_leaf(phase_id, timestamp)),
        "request_sha256": digest(request.as_dict()),
        "materialization": {"action": proven.action, "observed_head": proven.current.head},
        "materialization_receipt": materialization_reference(materialization_receipt, proven),
        "provider_invocations": 0,
        "lineage_depth": (proven.state.get("adoption") or {}).get("lineage_depth", 0) + 1,
    }
    record["sha256"] = digest(record)
    validate_record(record)
    proof.revalidate(proven)
    return record


def read(path: Path) -> dict:
    record = read_json(path)
    validate_record(record)
    return record


def read_json(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise AdoptionError("receipt must be an exact regular file")
    with path.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise AdoptionError("receipt exceeds one MiB")
    try:
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise AdoptionError("receipt repeats a JSON key")
                result[key] = value
            return result
        record = json.loads(data, object_pairs_hook=unique)
        if not isinstance(record, dict):
            raise AdoptionError("receipt must be a JSON object")
        return record
    except (UnicodeError, TypeError, KeyError, json.JSONDecodeError) as error:
        raise AdoptionError("invalid adoption receipt") from error


def materialization_reference(path: Path | None, proven: proof.Proof) -> dict | None:
    if path is None:
        return None
    record = read_json(path)
    final = record.get("finalization", {})
    commit = final.get("commit")
    if (record.get("schema") != "agent-phase-finalization-recovery-v1"
            or record.get("dry_run") is not False
            or final.get("outcome") not in ("materialized", "reused")
            or record.get("source_run_id") != proven.state["run_id"]
            or record.get("source_manifest") != proven.source_manifest
            or record.get("candidate_manifest") != proven.manifest
            or record.get("path_ownership") != proven.state["path_ownership"]
            or not isinstance(commit, str)
            or not gitstate.is_ancestor(proven.current.root, commit, proven.current.head)
            or gitstate.candidate_manifest_conflicts(proven.current.root, commit, proven.manifest)):
        raise AdoptionError("materialization receipt does not prove the selected source candidate")
    return {"path": str(path.resolve()), "sha256": digest(record), "record": record}


def _resolution_paths(path: Path | None) -> list[Path]:
    """Carry already-materialized grants through the explicit receipt surface."""
    if path is None:
        return []
    record = read_json(path)
    summaries = record.get('ownership_resolutions', [])
    if not summaries:
        return []
    if (record.get('schema') != 'agent-phase-finalization-recovery-v1'
            or record.get('dry_run') is not False
            or (record.get('finalization') or {}).get('outcome') not in ('materialized', 'reused')
            or not isinstance(summaries, list) or len(summaries) > 1024):
        raise AdoptionError('ownership grants require a completed materialization receipt')
    from . import ownership_cli
    paths = []
    for item in summaries:
        name = item.get('filename') if isinstance(item, dict) else None
        if not isinstance(name, str) or not re.fullmatch(r'ownership-resolution-[1-9][0-9]*\.json', name):
            raise AdoptionError('materialization receipt lacks exact copied ownership evidence')
        target = path.parent / name
        receipt = ownership_cli.read(target)
        if receipt['sha256'] != item.get('receipt_sha256'):
            raise AdoptionError('copied ownership receipt digest differs')
        paths.append(target)
    return paths


def validate_record(record: dict) -> None:
    if (not isinstance(record, dict)
            or set(record) not in (FIELDS, FIELDS | {"source_controller_generation"})
            or record.get("schema") != SCHEMA):
        raise AdoptionError("unsupported adoption schema")
    if len(encoded(record)) > MAX_BYTES or record.get("sha256") != digest(
            {k: v for k, v in record.items() if k != "sha256"}):
        raise AdoptionError("adoption checksum differs")
    run.safe_component(record["phase_id"], "continuation phase")
    if (not isinstance(record["timestamp"], str)
            or not re.fullmatch(r"[0-9]{8}T[0-9]{12}Z", record["timestamp"])
            or type(record["lineage_depth"]) is not int or not 1 <= record["lineage_depth"] <= 8
            or type(record["provider_invocations"]) is not int or record["provider_invocations"] != 0):
        raise AdoptionError("invalid continuation identity or lineage bound")
    if (not isinstance(record["reason"], str) or not record["reason"].strip()
            or len(record["reason"].encode()) > 4096):
        raise AdoptionError("invalid operator reason")
    for key, length in (("base_head", 40), ("base_tree", 40), ("request_sha256", 64)):
        if not isinstance(record[key], str) or not re.fullmatch(f"[0-9a-f]{{{length}}}", record[key]):
            raise AdoptionError("invalid object or request identity")
    selected = canonical_paths(record["adopted_paths"])
    if selected != record["adopted_paths"]:
        raise AdoptionError("adopted paths are not canonical")
    manifest = gitstate.validate_candidate_manifest(record["candidate_manifest"])
    if selected != sorted(manifest["paths"]):
        raise AdoptionError("adoption paths and objects disagree")
    source_manifest = gitstate.validate_candidate_manifest(record["source_candidate_manifest"])
    if (digest(source_manifest) != record["source_candidate_manifest_sha256"]
            or any(manifest["paths"][p] != source_manifest["paths"].get(p) for p in selected)):
        raise AdoptionError("adoption objects disagree with source candidate")


def validate_retained(root: Path, record: dict) -> None:
    """Validate archived authority without requiring old worktree bytes today."""
    validate_record(record)
    if repository_identity(root) != record["repository"]:
        raise AdoptionError("repository identity differs from adoption")
    source = Path(record["source_run"])
    archive_verify.verify_source_archive(source)
    if archive_verify.source_manifest(source) != record["source_manifest"]:
        raise AdoptionError("source run evidence changed")
    from .resume_validation import load_json, load_core
    from .request import load_request
    state = load_json(source, "state.json")
    if record.get("source_controller_generation") != state.get("controller_generation"):
        raise AdoptionError("source controller generation changed")
    reference = record.get('materialization_receipt')
    if reference is not None:
        retained = read_json(Path(reference['path']))
        if retained != reference['record'] or digest(retained) != reference['sha256']:
            raise AdoptionError('materialization receipt changed')
        resolutions = _resolution_paths(Path(reference['path']))
        if resolutions:
            from copy import deepcopy
            from . import ownership_cli, resume
            from .lifecycle import get_lifecycle
            _, original, _, _, entry, completed = load_core(
                source, state['phase_id'], load_request(source / 'request.json'), root, state['project'])
            state = deepcopy(original)
            ownership_cli.apply_receipts(root, source, state, record['source_manifest'], resolutions)
            terminal = resume._terminal_result(source, original, completed, get_lifecycle(state['lifecycle']))
            if terminal is None or not terminal.completed:
                raise AdoptionError('materialization lacks completed provider semantics')
            proof._ownership(state, entry, terminal, retained_state=original)
    if (state["run_id"] != record["source_run_id"]
            or state["candidate_manifest"] != record["source_candidate_manifest"]
            or state["path_ownership"] != record["source_path_ownership"]):
        raise AdoptionError("source candidate binding changed")
    if record["lineage_depth"] != (state.get("adoption") or {}).get("lineage_depth", 0) + 1:
        raise AdoptionError("adoption lineage is inconsistent")
    load_core(source, state["phase_id"], load_request(source / "request.json"), root, state["project"])
    manifest = record["candidate_manifest"]
    if gitstate.candidate_manifest(root, manifest["entry_tree"], manifest["candidate_tree"],
            paths=record["adopted_paths"]) != manifest:
        raise AdoptionError("adopted Git objects are unavailable or differ")


def validate_state(state: dict, request: Any, entry: Any) -> None:
    record = state["adoption"]
    validate_record(record)
    if record["phase_id"] != state["phase_id"] or record["request_sha256"] != digest(request.as_dict()):
        raise AdoptionError("adoption is bound to a different substantive request")
    expected_v2_id = run.v2_run_id(state["project"], record["phase_id"], run.v2_leaf(record["phase_id"], record["timestamp"]))
    expected_v1_id = f"{state['project']}/{record['phase_id']}--{record['timestamp']}"
    if record["continuation_run_id"] == expected_v2_id:
        expected_id = expected_v2_id
    elif record["continuation_run_id"] == expected_v1_id:
        expected_id = expected_v1_id
    else:
        raise AdoptionError("continuation run identity is inconsistent")
    if not state.get("resumed") and (state["run_id"] != expected_id
            or entry.as_dict() != record["observed_entry"]):
        raise AdoptionError("new phase entry differs from its adoption receipt")


def _prepare(path: Path, root: Path, phase_id: str, request: Any) -> dict:
    """Re-prove the closed source and current boundary before granting ownership."""
    if path.resolve().is_relative_to(root):
        raise AdoptionError("adoption authority must be outside the product repository")
    record = read(path)
    validate_retained(root, record)
    proof._repository_guard(root)
    gitstate.require_no_active_git_operations(root)
    current_dirty = {p: gitstate._identity(root, p) for p in gitstate.dirty_paths(root)}
    if (current_dirty != record["observed_dirty"]
            or gitstate.current_head(root) != record["base_head"]
            or gitstate.current_branch(root) != record["branch"]
            or gitstate.index_identity(root) != record["observed_entry"]["index"]):
        raise AdoptionError("repository changed since adoption creation")
    fresh = create(Path(record["source_run"]), root, phase_id, request,
                   reason=record["reason"], paths=record["adopted_paths"],
                   materialization_receipt=(Path(record["materialization_receipt"]["path"])
                       if record.get("materialization_receipt") else None))
    # Creation fixes the future run identity. Validation never mints another one.
    for key in ("timestamp", "continuation_run_id", "sha256"):
        fresh[key] = record[key]
    if fresh != record:
        raise AdoptionError("adoption receipt is stale or differs from proven authority")
    return record


def prepare(path: Path, root: Path, phase_id: str, request: Any) -> dict:
    try:
        proof.require_standard_environment()
        return _prepare(path, root, phase_id, request)
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as error:
        raise AdoptionError("continuation authority validation failed: " + str(error)) from error


def paths(state: dict | None) -> set[str]:
    if state is None:
        return set()
    result = set((state.get("adoption") or {}).get("adopted_paths", []))
    if "entry_adoption" in state and isinstance(state["entry_adoption"], dict):
        result |= set(state["entry_adoption"].get("adopted_paths", []))
    return result


def protected_paths(record: dict) -> set[str]:
    return (set(record.get("excluded_unrelated_paths", [])) | set(record.get("inherited_excluded_paths", []))
            | set(record.get("unselected_source_paths", [])))


def guard_owned(state: dict, proposed: Any) -> None:
    record = state.get("adoption")
    if record and any(proof.overlaps(p, q) for p in proposed for q in protected_paths(record)):
        raise AdoptionError("candidate ownership includes an unadopted object boundary")
    entry_rec = state.get("entry_adoption")
    if entry_rec:
        unadopted = set(entry_rec.get("unadopted_dirty_paths", []))
        if any(proof.overlaps(p, q) for p in proposed for q in unadopted):
            raise AdoptionError("candidate ownership includes an unadopted object boundary")


def guard_boundary(state: dict, root: Path, raw: str, supplied: Any = ()) -> None:
    record = state.get("adoption")
    if record is not None:
        validate_retained(root, record)
        selected = record["adopted_paths"]
        require_paths(root, selected, gitstate.dirty_paths(root))
        protected = protected_paths(record)
        for item in supplied:
            if any(proof.overlaps(item["path"], p) for p in protected):
                raise AdoptionError("provider disposition overlaps unadopted authority")
        expected = gitstate.candidate_manifest(root, record["observed_entry"]["tree"],
            record["observed_entry"]["tree"], paths=sorted(protected))
        changed = gitstate.phase_delta(root, record["observed_entry"]["tree"], raw)
        if any(proof.overlaps(c.path, p) for c in changed for p in protected):
            raise AdoptionError("phase change overlaps an unadopted object boundary")
        if gitstate.candidate_manifest_conflicts(root, raw, expected):
            raise AdoptionError("unadopted or excluded entry objects changed")

    entry_rec = state.get("entry_adoption")
    if entry_rec is not None:
        from . import entry_adoption as entry_adopt_module
        entry_adopt_module.validate_retained_entry(root, entry_rec)
        unadopted = set(entry_rec.get("unadopted_dirty_paths", []))
        for item in supplied:
            p = item.get("path") if isinstance(item, dict) else getattr(item, "path", None)
            if p and any(proof.overlaps(p, u) for u in unadopted):
                raise AdoptionError("provider disposition overlaps unadopted authority")
        if unadopted:
            entry_dirty = state.get("entry_dirt_identities")
            if not isinstance(entry_dirty, dict):
                entry_dirty = (
                    state.get("entry", {}).get("dirty", {})
                    if isinstance(state.get("entry", {}).get("dirty"), dict)
                    else state.get("entry_adoption", {}).get("unadopted_path_metadata", {})
                )
            for u in unadopted:
                curr = gitstate._identity(root, u)
                if isinstance(entry_dirty, dict) and u in entry_dirty:
                    if curr != entry_dirty[u]:
                        raise AdoptionError("unadopted or excluded entry objects changed")


def prompt_context(record: dict | None) -> str:
    if record is None:
        return ""
    return ("\n\nDispatcher-owned adoption provenance (separate from task scope and model prose):\n"
            + encoded({"receipt_sha256": record["sha256"], "source_run_id": record["source_run_id"],
                       "candidate_manifest": record["candidate_manifest"]}).decode()
            + "\nThis is a NEW phase. No historical stages are inherited. Only these exact "
              "prior objects are adopted; provider output cannot expand this selection.\n")
