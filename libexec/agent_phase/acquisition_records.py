"""Optional artifact projection. Raw acquisition records remain canonical."""
from __future__ import annotations

import hashlib
import fcntl
import json
import os
import re
import stat
import uuid

EVENT = re.compile(r"event-([0-9a-f]{64})\.jsonl\Z")
MAX_EVENTS = 4096


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate acquisition field")
        result[key] = value
    return result


def records(run_dir, run_id, *, diagnostics=None):
    """Bounded direct reads; no catalog access and no historical re-planning."""
    root = os.open(run_dir, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        try:
            owner = os.open("acquisitions", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root)
        except FileNotFoundError:
            return []
        try:
            names = []
            with os.scandir(owner) as entries:
                for entry in entries:
                    names.append(entry.name)
                    if len(names) > MAX_EVENTS + 2:
                        raise ValueError("acquisition event limit")
            result = []
            for name in sorted(names):
                match = EVENT.fullmatch(name)
                if not match:
                    continue
                try:
                    before = os.stat(name, dir_fd=owner, follow_symlinks=False)
                    if not stat.S_ISREG(before.st_mode) or before.st_size > 8192:
                        raise ValueError("unsafe acquisition event")
                    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=owner)
                    with os.fdopen(fd, "rb") as stream:
                        opened = os.fstat(stream.fileno())
                        data = stream.read(8193)
                        after = os.fstat(stream.fileno())
                    entry = os.stat(name, dir_fd=owner, follow_symlinks=False)
                    key = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
                    if len(data) > 8192 or not key(before) == key(opened) == key(after) == key(entry):
                        raise ValueError("acquisition event changed")
                    value = json.loads(data, object_pairs_hook=_pairs)
                    if not isinstance(value, dict) or not all(isinstance(value.get(key), str) and value[key] for key in ("binding_id", "attempt_id")) or value.get("schema") != "apg.acquisition-event/v1" or value.get("event_id") != match[1] or value.get("run_id") != run_id:
                        raise ValueError("acquisition event identity mismatch")
                    result.append({"event": value, "path": "acquisitions/" + name,
                                   "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
                except (OSError, ValueError, TypeError) as error:
                    if diagnostics is not None:
                        diagnostics.append({"path": "acquisitions/" + name, "diagnostic": type(error).__name__})
                    continue
            return result
        finally:
            os.close(owner)
    finally:
        os.close(root)


def ingest(conn, run_dir, run_id):
    """Idempotent event-identity index at a safe lifecycle boundary.

    Failures return a diagnostic; neither an index row nor its absence changes
    channel delivery or model observation. No database migration is necessary.
    """
    try:
        from .persistence import record_artifact
        diagnostics = []
        rows = records(run_dir, run_id, diagnostics=diagnostics)
        for row in rows:
            artifact_id = "acquisition:" + row["event"]["event_id"]
            previous = conn.execute("SELECT run_id, relative_path, size_bytes, sha256 FROM artifacts WHERE artifact_id = ?", (artifact_id,)).fetchone()
            expected = (run_id, row["path"], row["bytes"], row["sha256"])
            if previous is not None:
                if tuple(previous) != expected:
                    raise ValueError("acquisition index identity collision")
                continue
            record_artifact(conn, artifact_id=artifact_id, run_id=run_id,
                            artifact_name="acquisition-event", relative_path=row["path"],
                            size_bytes=row["bytes"], sha256=row["sha256"],
                            content_type="application/x-ndjson")
        return {"status": "partial" if diagnostics else "indexed", "events": len(rows), "diagnostics": diagnostics, "model_observed": None}
    except Exception as error:
        return {"status": "failed", "diagnostic": type(error).__name__, "model_observed": None}


def observe_index(conn, run_dir, run_id):
    observation = ingest(conn, run_dir, run_id)
    try:
        root = os.open(run_dir, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            name = "acquisition-index-" + uuid.uuid4().hex + ".json"
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=root)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(observation, stream, sort_keys=True)
                stream.write("\n")
        finally:
            os.close(root)
    except OSError:
        pass
    return observation


def recovery_observation(prepared, status, *, controlled_bytes=0, evidence, payload=None):
    """Append an explicitly witnessed failure/read, never infer model behavior.

    Callers must own the observation (for example an instrumented native reader).
    A readable file alone must not call this with recovery_read_observed.
    """
    root = os.open(prepared["path"].parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        owner = os.open("acquisitions", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root)
        try:
            lock = os.open(".lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=owner)
            try:
                if not stat.S_ISREG(os.fstat(lock).st_mode):
                    raise ValueError("unsafe acquisition lock")
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return _recovery_observation(prepared, status, controlled_bytes=controlled_bytes, evidence=evidence, payload=payload)
            finally:
                os.close(lock)
        finally:
            os.close(owner)
    finally:
        os.close(root)


def _recovery_observation(prepared, status, *, controlled_bytes, evidence, payload=None):
    if status not in ("mcp_failed", "recovery_read_observed") or not 0 <= controlled_bytes <= 1 << 20 or not evidence or len(evidence) > 256:
        raise ValueError("invalid recovery observation")
    record = prepared["record"]
    previous = records(prepared["path"].parent, record["run_id"])
    if len(previous) >= MAX_EVENTS or sum(row["event"]["binding_id"] == record["binding_id"] for row in previous) >= 256:
        raise ValueError("acquisition event limit")
    repeated = status == "recovery_read_observed" and any(
        row["event"].get("kind") == status and row["event"].get("binding_id") == record["binding_id"]
        and row["event"].get("attempt_id") == record["attempt_id"] for row in previous)
    scope = [record[key] for key in ("run_id", "binding_id", "attempt_id")]
    event_id = hashlib.sha256(json.dumps([*scope, uuid.uuid4().hex, 1]).encode()).hexdigest()
    event = {"schema": "apg.acquisition-event/v1", "event_id": event_id,
             **dict(zip(("run_id", "binding_id", "attempt_id"), scope)),
             "sequence": 1, "kind": status, "channel": "recovery_read",
             "is_repeat_delivery": repeated, "controlled_bytes": controlled_bytes,
             "index_state": "not_observed", "provider_observed": None,
             "model_observed": None, "tokens": None, "diagnostic": evidence}
    if payload is not None:
        if status != "recovery_read_observed" or len(payload) != controlled_bytes:
            raise ValueError("invalid recovery payload")
        payload.decode("utf-8")
        event.update(payload_sha256=hashlib.sha256(payload).hexdigest(), phase="late",
                     provenance=evidence, observation_kind="witnessed_recovery_read")
    root = os.open(prepared["path"].parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        owner = os.open("acquisitions", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root)
        try:
            temporary = ".pending-" + event_id
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=owner)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as stream:
                    json.dump(event, stream, sort_keys=True)
                    stream.write("\n")
                    stream.flush()
                    os.fsync(stream.fileno())
                os.link(temporary, "event-" + event_id + ".jsonl", src_dir_fd=owner, dst_dir_fd=owner, follow_symlinks=False)
                os.fsync(owner)
            finally:
                os.unlink(temporary, dir_fd=owner)
        finally:
            os.close(owner)
    finally:
        os.close(root)
    return event_id


def read_recovery(prepared, relative, deliver):
    """Evaluation-only native-read seam. Count after a witnessed complete handoff.

    This does not observe filesystem reads made outside this seam. The caller
    supplies an independently authorized native reader; no shell is introduced.
    """
    allowed = {r["path"]: r for r in prepared["record"].get("acquisition", {}).get("recovery", [])}
    if relative not in allowed or any(p in ("", ".", "..") or "\\" in p for p in relative.split("/")):
        raise ValueError("recovery read outside captured authority")
    owner = os.open(prepared["path"].parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        parts = relative.split("/")
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=owner)
            os.close(owner)
            owner = child
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=owner)
        with os.fdopen(fd, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError("nonregular recovery read")
            payload = stream.read((1 << 20) + 1)
        if len(payload) > 1 << 20:
            raise ValueError("recovery read exceeds bound")
        payload.decode("utf-8")
        if (allowed[relative].get("sha256") != hashlib.sha256(payload).hexdigest()
                or allowed[relative].get("bytes") != len(payload)):
            raise ValueError("recovery source identity missing or changed")
        if deliver(payload) != len(payload):
            raise ValueError("incomplete recovery handoff")
        return recovery_observation(prepared, "recovery_read_observed", controlled_bytes=len(payload),
                                    evidence=relative, payload=payload)
    finally:
        os.close(owner)


def delivery_entries(events, *, run_id, binding_id, attempt_id):
    """Deterministic H bridge over canonical raw observations; SQLite is optional.

    Coverage here concerns supplied successful transmissions only. The evaluator
    must additionally prove trace completeness at each required launch boundary.
    """
    deliveries, seen, diagnostics = {}, {}, []
    kinds = {"channel_delivered", "response_delivered", "recovery_read_observed", "initial_delivered"}
    channels = {"prompt", "instructions", "mcp_configuration", "mcp", "cli", "recovery_read"}
    for event in events:
        if (event.get("run_id"), event.get("binding_id"), event.get("attempt_id")) != (run_id, binding_id, attempt_id):
            continue
        if event.get("channel") == "preparation" or event.get("kind", "").startswith("preparation_"):
            continue
        if event.get("kind") not in kinds:
            continue
        identity = event.get("event_id")
        try:
            if not isinstance(identity, str) or not re.fullmatch("[0-9a-f]{64}", identity):
                raise ValueError("missing transmission identity")
            if identity in seen and seen[identity] != event:
                raise ValueError("conflicting transmission views")
            seen[identity] = event
            if (not isinstance(event.get("payload_sha256"), str)
                    or not re.fullmatch("[0-9a-f]{64}", event["payload_sha256"])
                    or event.get("phase") not in ("initial", "late")
                    or event.get("channel") not in channels
                    or type(event.get("controlled_bytes")) is not int or event["controlled_bytes"] < 0
                    or not event.get("provenance") or not event.get("observation_kind")):
                raise ValueError("incomplete transmission evidence")
            deliveries[identity] = {"id": identity, "phase": event["phase"], "bytes": event["controlled_bytes"],
                                    "sha256": event["payload_sha256"], "channel": event["channel"], "source": "measured"}
        except ValueError as error:
            diagnostics.append(str(error))
    return {"deliveries": [deliveries[key] for key in sorted(deliveries)],
            "coverage": "incomplete" if diagnostics else "complete", "diagnostics": sorted(set(diagnostics))}
