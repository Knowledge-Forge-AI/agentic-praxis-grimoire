"""Immutable ownership observations and separate, closed resolution events.

Digests bind evidence, not hostile same-user authentication. No provider path
string grants destructive ownership. Worktree bytes are never restored here.
"""
from __future__ import annotations

from contextvars import ContextVar
from datetime import datetime, timezone
from functools import wraps
import hashlib
import json
import re

from . import gitstate
from .result import ResultError

SCHEMA = "agent-phase-ownership-challenges-v1"
RECORD_SCHEMA = "agent-phase-ownership-challenge-v1"
MAX_RECORDS = 1024
MAX_RECORD_BYTES = 32 * 1024
MAX_LEDGER_BYTES = 8 * 1024 * 1024
DECISIONS = {
    "unclaimed_tracked_deletion": ["phase_owned", "exclude_unrelated"],
    "entry_dirt_overlap": ["phase_owned"],
}


def invalid(detail):
    raise ResultError("OWNERSHIP_CHALLENGE_INVALID", detail)



def invalid_provider(detail):
    raise ResultError("OWNERSHIP_PROVIDER_RESOLUTION_INVALID", detail)


def validate_tree(tree):
    if not isinstance(tree, str) or not re.fullmatch(r"[0-9a-f]{40}", tree):
        invalid("ownership tree identity must be a lowercase 40-hex object ID")
    return tree


# Scope immutable Git facts to one public operation, including nested validation.
# Never retain facts across calls: removed/corrupted objects must be rechecked.
_facts = ContextVar("ownership_git_facts", default=None)


def _with_facts(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        if _facts.get() is not None:
            return function(*args, **kwargs)
        token = _facts.set({})
        try:
            return function(*args, **kwargs)
        finally:
            _facts.reset(token)
    return wrapped


def _phase_delta(root, before, after):
    validate_tree(before)
    validate_tree(after)
    cache = _facts.get()
    key = (str(root), "delta", before, after)
    if cache is None:
        return gitstate.phase_delta(root, before, after)
    if key not in cache:
        cache[key] = gitstate.phase_delta(root, before, after)
    return cache[key]


def _provider_eligible(record):
    return (record["boundary"] != "post_terminal"
            and record["reason"] != "entry_dirt_overlap")

def encoded(value):
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, UnicodeError):
        invalid("ownership evidence is not bounded UTF-8 JSON")


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def validate_path(root, path):
    from .path_disposition import validate_dispositions
    validate_dispositions([{"path": path, "disposition": "phase_owned"}])
    parent = (root / path).parent
    while parent != root:
        if parent.is_symlink():
            invalid("ownership path traverses a symlink")
        parent = parent.parent


def object_at(root, tree, path):
    validate_tree(tree)
    cache = _facts.get()
    key = (str(root), "object", tree, path)
    if cache is not None and key in cache:
        return cache[key]
    identity = gitstate.candidate_manifest(root, tree, tree, paths=[path])["paths"][path]
    # Include the native Git object ID as well as content/type/mode identity.
    value = gitstate._text(root, ["ls-tree", "-z", tree, "--",
                                gitstate.literal_pathspec(path)], "OWNERSHIP_CHALLENGE_INVALID")
    oid = value.split("\t", 1)[0].split(" ")[-1] if value else None
    value = {**identity, "oid": oid}
    if cache is not None:
        cache[key] = value
    return value


@_with_facts
def validate_record(root, record):
    fields = {"schema", "challenge_id", "repository", "project", "run_id",
              "controller_generation", "phase_id", "lifecycle", "stage", "boundary",
              "path", "reason", "status", "entry_tree", "base_head", "raw_tree",
              "entry_object", "current_object", "base_object", "ownership_context",
              "allowed_decisions", "created_at", "observation_sequence"}
    if not isinstance(record, dict) or set(record) != fields:
        invalid("invalid challenge fields")
    if len(encoded(record)) > MAX_RECORD_BYTES or record["schema"] != RECORD_SCHEMA:
        invalid("invalid challenge schema or size")
    payload = {k: v for k, v in record.items() if k != "challenge_id"}
    if record["challenge_id"] != "ownch1-" + digest(payload):
        invalid("challenge digest disagrees with immutable record")
    if type(record["observation_sequence"]) is not int or not 0 <= record["observation_sequence"] < MAX_RECORDS:
        invalid("invalid challenge observation sequence")
    validate_path(root, record["path"])
    if record["repository"] != str(root.resolve()):
        invalid("challenge repository differs")
    reason = record["reason"]
    if reason not in DECISIONS or record["allowed_decisions"] != DECISIONS[reason]:
        invalid("challenge reason or decisions are unsupported")
    for field in ("entry_tree", "raw_tree", "base_head"):
        validate_tree(record[field])
    for tree, obj in (("entry_tree", "entry_object"), ("raw_tree", "current_object"),
                      ("base_head", "base_object")):
        if object_at(root, record[tree], record["path"]) != record[obj]:
            invalid("challenge Git object evidence differs")
    delta = {c.path: c.status for c in _phase_delta(root, record["entry_tree"], record["raw_tree"])}
    if delta.get(record["path"]) != record["status"]:
        invalid("challenge status differs from Git evidence")
    if reason == "unclaimed_tracked_deletion" and (
            record["status"] != "D" or not record["entry_object"]["present"]):
        invalid("deletion challenge is not a tracked deletion")
    if reason == "entry_dirt_overlap" and record["entry_object"] == record["base_object"]:
        invalid("entry overlap lacks original dirty object")
    return record


def statuses(state):
    ledger = state.get("ownership_challenges") or {"records": [], "events": []}
    result = {r["challenge_id"]: "open" for r in ledger["records"]}
    for event in ledger["events"]:
        if event["kind"] != "shown":
            result[event["challenge_id"]] = event["kind"]
    return result


def _validate_ledger_shape(ledger):
    if (not isinstance(ledger, dict) or set(ledger) != {"schema", "records", "events"}
            or ledger["schema"] != SCHEMA or not isinstance(ledger["records"], list)
            or not isinstance(ledger["events"], list) or len(ledger["records"]) > MAX_RECORDS
            or len(ledger["events"]) > MAX_RECORDS * 16 or len(encoded(ledger)) > MAX_LEDGER_BYTES):
        invalid("invalid or oversized challenge ledger")


def _validate_resolution(root, event, record, status, shown):
    cid, kind = event['challenge_id'], event['kind']
    expected = {"challenge_id", "kind", "decision", "raw_tree",
                "stage" if kind == "resolved_by_provider" else "receipt_digest"}
    if set(event) != expected or status[cid] != "open" or event["decision"] not in record["allowed_decisions"]:
        invalid("invalid or duplicate challenge resolution")
    if object_at(root, event["raw_tree"], record["path"]) != record["current_object"]:
        invalid("resolution candidate object differs")
    if kind == "resolved_by_provider" and (cid, event["stage"]) not in shown:
        invalid("provider was not shown this challenge")
    if kind == 'resolved_by_manager' and not re.fullmatch(r'[0-9a-f]{64}', str(event['receipt_digest'])):
        invalid('manager receipt digest is invalid')


def _validate_events(root, ledger, records):
    status = {key: "open" for key in records}
    shown = set()
    for event in ledger["events"]:
        if not isinstance(event, dict) or event.get("challenge_id") not in records:
            invalid("event lacks a retained challenge")
        cid, kind = event["challenge_id"], event.get("kind")
        record = records[cid]
        if kind == "shown":
            if (set(event) != {"challenge_id", "kind", "stage"} or status[cid] != "open"
                    or not _provider_eligible(record)):
                invalid("invalid challenge presentation")
            from .lifecycle import get_lifecycle
            if event["stage"] != get_lifecycle(record["lifecycle"]).terminal_result_stage:
                invalid("only terminal stages can receive resolution authority")
            shown.add((cid, event["stage"]))
            continue
        if kind == "superseded":
            if set(event) != {"challenge_id", "kind", "raw_tree"} or status[cid] == "superseded":
                invalid("invalid supersession")
            if object_at(root, event["raw_tree"], record["path"]) == record["current_object"]:
                invalid("unchanged challenge cannot be superseded")
        elif kind in ("resolved_by_provider", "resolved_by_manager"):
            _validate_resolution(root, event, record, status, shown)
        else:
            invalid("unknown challenge event")
        status[cid] = kind


@_with_facts
def validate(root, state):
    ledger = state.get("ownership_challenges")
    if ledger is None:
        return
    _validate_ledger_shape(ledger)
    records = {}
    for sequence, record in enumerate(ledger["records"]):
        validate_record(root, record)
        if record["observation_sequence"] != sequence:
            invalid("challenge observation sequence differs from retained ledger")
        if record["challenge_id"] in records:
            invalid("duplicate challenge record")
        records[record["challenge_id"]] = record
    _validate_events(root, ledger, records)


def open_records(state):
    status = statuses(state)
    return [r for r in (state.get("ownership_challenges") or {}).get("records", [])
            if status[r["challenge_id"]] == "open"]


def decisions(state):
    ledger = state.get("ownership_challenges") or {"records": [], "events": []}
    active = statuses(state)
    paths = {r["challenge_id"]: r["path"] for r in ledger["records"]}
    return {paths[e["challenge_id"]]: e["decision"] for e in ledger["events"]
            if e["kind"] in ("resolved_by_provider", "resolved_by_manager")
            and active[e["challenge_id"]] == e["kind"]}


def _transition(state, path, before, after, transitions):
    if not before['present'] or not after['present'] or before['mode'] == after['mode']:
        return
    classification = 'object_type_change'
    if before['type'] == after['type'] == 'file':
        classification = ('executable_mode_only' if before['oid'] == after['oid']
                          else 'regular_file_mode_and_content')
    transitions.append({'path': path, 'classification': classification,
                        'before_mode': before['mode'], 'after_mode': after['mode']})
    state['ownership_type_transitions'] = transitions
    if classification == 'object_type_change':
        raise ResultError('OWNERSHIP_TYPE_CHANGE_UNSUPPORTED',
                          'file/symlink type transitions require repository resolution')


def _reason(root, entry, change, after, carried, inherited_deletions):
    path = change.path
    if path in entry.dirty and path not in carried and object_at(root, entry.tree, path) != after:
        return 'entry_dirt_overlap'
    if change.status == 'D' and path not in inherited_deletions:
        return 'unclaimed_tracked_deletion'
    if change.status in ('A', 'M') or path in carried:
        return None
    raise ResultError('OWNERSHIP_TYPE_CHANGE_UNSUPPORTED', 'unsupported destructive change status')


@_with_facts
def observe(root, state, entry, raw, stage, boundary):
    """Observe before parsing terminal output, never interpreting provider claims."""
    from . import adoption
    if state.get('ownership_challenges') is None:
        state['ownership_challenges'] = {"schema": SCHEMA, "records": [], "events": []}
    ledger = state['ownership_challenges']
    validate(root, state)
    base = (state.get("path_ownership") or {}).get("entry_tree", (state.get("resume") or {}).get("source_entry_tree", entry.tree))
    observed = _phase_delta(root, base, raw)
    carried = adoption.paths(state)
    # Only validated inherited provenance, not current mechanical failure capture.
    if state.get("resumed"):
        carried |= set((state.get("resume") or {}).get("candidate_manifest", {}).get("paths", {}))
    inherited_deletions = set()
    for manifest in ((state.get('adoption') or {}).get('candidate_manifest', {}),
                     state.get('inherited_candidate_manifest') or {},
                     (state.get('resume') or {}).get('candidate_manifest', {})):
        inherited_deletions.update(path for path, obj in manifest.get('paths', {}).items()
                                   if obj.get('present') is False)
    active = statuses(state)
    for record in ledger["records"]:
        if active[record["challenge_id"]] != "superseded" and object_at(root, raw, record["path"]) != record["current_object"]:
            ledger["events"].append({"challenge_id": record["challenge_id"], "kind": "superseded", "raw_tree": raw})
    active = statuses(state)
    existing = {r["path"] for r in ledger["records"] if active[r["challenge_id"]] != "superseded"}
    resolved = decisions(state)
    mechanical, transitions = [], []
    for change in observed:
        path = change.path
        validate_path(root, path)
        before, after = object_at(root, base, path), object_at(root, raw, path)
        _transition(state, path, before, after, transitions)
        # Resolved authority is exact-object authority and never survives drift.
        if path in resolved or path in existing:
            continue
        reason = _reason(root, entry, change, after, carried, inherited_deletions)
        if reason is None:
            mechanical.append(path)
            continue
        record = {"schema": RECORD_SCHEMA, "observation_sequence": len(ledger["records"]),
                  "repository": str(root.resolve()),
                  "project": state.get("project"), "run_id": state.get("run_id"),
                  "controller_generation": state.get("controller_generation"),
                  "phase_id": state.get("phase_id"), "lifecycle": state.get("lifecycle", "standard"),
                  "stage": stage, "boundary": boundary, "path": path, "reason": reason,
                  "status": change.status, "entry_tree": base, "base_head": entry.head,
                  "raw_tree": raw, "entry_object": before, "current_object": after,
                  "base_object": object_at(root, entry.head, path),
                  "ownership_context": {"entry_dirty": path in entry.dirty, "carried": path in carried,
                      "adoption_digest": digest(state.get("adoption")), "resume_source": (state.get("resume") or {}).get("source_run_id")},
                  "allowed_decisions": DECISIONS[reason],
                  "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        record["challenge_id"] = "ownch1-" + digest(record)
        if len(ledger['records']) >= MAX_RECORDS or len(encoded(record)) > MAX_RECORD_BYTES:
            invalid('challenge record count or size exceeds V1 bounds')
        ledger["records"].append(record)
        _validate_ledger_shape(ledger)
    state["mechanical_phase_owned_paths"] = sorted(mechanical)
    state["ownership_type_transitions"] = transitions
    validate(root, state)


@_with_facts
def prompt(root, state, stage):
    validate(root, state)
    from .lifecycle import get_lifecycle
    if stage != get_lifecycle(state.get('lifecycle', 'standard')).terminal_result_stage:
        invalid('only a terminal stage can receive challenge resolution authority')
    records = [r for r in open_records(state) if _provider_eligible(r)]
    text = "\nDispatcher-owned ownership challenges (immutable observations; separate resolution authority):\n" + encoded(records).decode()
    if len(text.encode()) > 128 * 1024:
        invalid("challenge prompt exceeds bound")
    for record in records:
        event = {"challenge_id": record["challenge_id"], "kind": "shown", "stage": stage}
        if event not in state["ownership_challenges"]["events"]:
            state["ownership_challenges"]["events"].append(event)
    return text + "\nOnly these IDs may be resolved through ownership_resolutions. Raw path claims confer no challenge authority.\n"


def validate_resolutions(value):
    if not isinstance(value, list) or len(value) > MAX_RECORDS or len(encoded(value)) > 128 * 1024:
        invalid_provider("invalid ownership_resolutions array")
    seen = set()
    for item in value:
        if (not isinstance(item, dict) or set(item) != {"challenge_id", "decision"}
                or not isinstance(item["challenge_id"], str)
                or not re.fullmatch(r"ownch1-[0-9a-f]{64}", item["challenge_id"])
                or item["decision"] not in ("phase_owned", "exclude_unrelated")
                or item["challenge_id"] in seen):
            invalid_provider("invalid or duplicate ownership resolution")
        seen.add(item["challenge_id"])
    return value


@_with_facts
def resolve_provider(root, state, stage, raw, supplied):
    validate(root, state)
    records = {r["challenge_id"]: r for r in open_records(state)}
    for item in validate_resolutions(list(supplied)):
        record = records.get(item["challenge_id"])
        shown = {"challenge_id": item["challenge_id"], "kind": "shown", "stage": stage}
        if (record is None or not _provider_eligible(record)
                or shown not in state["ownership_challenges"]["events"]
                or item["decision"] not in record["allowed_decisions"]
                or object_at(root, raw, record["path"]) != record["current_object"]):
            invalid_provider("provider resolution was not shown, is manager-only, or is stale")
    for item in supplied:
        state["ownership_challenges"]["events"].append({**item, "kind": "resolved_by_provider", "stage": stage, "raw_tree": raw})
    validate(root, state)


@_with_facts
def resolve_manager(root, state, challenge_id, decision, receipt_digest):
    validate(root, state)
    record = next((r for r in open_records(state) if r["challenge_id"] == challenge_id), None)
    raw = (state.get("raw_terminal_candidate") or state.get("terminal_candidate") or {})["tree"]
    if record is None or decision not in record["allowed_decisions"] or object_at(root, raw, record["path"]) != record["current_object"]:
        invalid("manager resolution is stale or unsupported")
    state["ownership_challenges"]["events"].append({"challenge_id": challenge_id, "kind": "resolved_by_manager", "decision": decision, "raw_tree": raw, "receipt_digest": receipt_digest})
    validate(root, state)


def capture_candidate(directory, entry, state, raw):
    """Retain reconstructable raw and original dirty objects without ownership."""
    from . import checkpoint
    records = {}
    for label, tree in (("entry", entry.tree), ("raw", raw)):
        paths = [c.path for c in gitstate.phase_delta(entry.root, entry.head, tree)]
        patch = checkpoint._git(entry.root, ["diff-tree", "-p", "--binary", "--full-index",
            "--no-renames", "--no-commit-id", entry.head, tree, "--"])
        reconstructed = checkpoint._reconstruct(entry.root, entry.head, patch,
                                                expected_tree=tree, paths=paths)
        if reconstructed != tree:
            invalid("ownership evidence reconstruction differs")
        name = f"ownership-{label}-candidate.patch"
        directory.write_bytes(name, patch)
        records[label] = {"tree": tree, "base_head": entry.head, "patch": name,
                          "sha256": hashlib.sha256(patch).hexdigest(), "bytes": len(patch),
                          "paths": paths, "reconstruction_verified": True}
    state['ownership_candidate_evidence'] = {
        'schema': 'agent-phase-ownership-candidate-evidence-v1',
        'authority': 'observation_only', **records,
    }
    directory.write_json('ownership-candidate-evidence.json', state['ownership_candidate_evidence'])
