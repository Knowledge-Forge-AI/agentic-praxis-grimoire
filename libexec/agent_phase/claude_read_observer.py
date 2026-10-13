"""Strict evaluation-only Claude native Read evidence; never model-use evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .acquisition_records import _pairs
from .transmission import direct_bytes

MAX_LOG = 64 << 20
MAX_RECORD = 4 << 20
SCHEMA = "apg.claude-native-reads/v1"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def identity(data):
    return {"bytes": len(data), "sha256": digest(data)}


def decode(data):
    return json.loads(data.decode("utf-8"), object_pairs_hook=_pairs,
                      parse_constant=lambda _: fail("non-finite JSON"))


def fail(message):
    raise ValueError(message)


def capture_recovery(prepared):
    """Capture exact authorized source bytes before launch, without granting access."""
    root = prepared["path"].parent
    captured = {}
    for row in prepared["record"].get("acquisition", {}).get("recovery", []):
        relative = row["path"]
        if not isinstance(relative, str) or any(p in ("", ".", "..") or "\\" in p for p in relative.split("/")):
            fail("unsafe recovery path")
        path = root / relative
        if str(path) in captured or not row.get("id"):
            fail("ambiguous recovery authority")
        data = direct_bytes(path, max_bytes=1 << 20)
        if identity(data) != {k: row[k] for k in ("bytes", "sha256")}:
            fail("recovery source identity changed")
        captured[str(path)] = {"entry": dict(row), "payload": data,
                               "scope": {k: prepared["record"][k] for k in ("run_id", "binding_id", "attempt_id")}}
    return captured


def _records(raw):
    if not raw or len(raw) > MAX_LOG or not raw.endswith(b"\n"):
        fail("empty, oversized or truncated stream")
    for number, line in enumerate(raw.split(b"\n")[:-1], 1):
        if not line or len(line) > MAX_RECORD:
            fail("empty or oversized stream record")
        value = decode(line)
        if not isinstance(value, dict) or not isinstance(value.get("type"), str):
            fail("invalid event envelope")
        yield number, line, value


def _hidden_tool(value):
    if isinstance(value, dict):
        return (value.get("type") in ("tool_use", "tool_result", "assistant", "user")
                or any(k in value for k in ("tool_use_id", "tool_use_result"))
                or any(_hidden_tool(v) for v in value.values()))
    return isinstance(value, list) and any(_hidden_tool(v) for v in value)


def _blocks(event):
    message = event.get("message")
    if not isinstance(message, dict):
        fail("missing message envelope")
    content = message.get("content")
    if isinstance(content, str) and event["type"] == "user":
        return []
    if not isinstance(content, list) or any(not isinstance(b, dict) or not isinstance(b.get("type"), str) for b in content):
        fail("malformed message content")
    return content


def _visible(content):
    if isinstance(content, str):
        return content.encode("utf-8"), "utf8-string"
    if (not isinstance(content, list) or not content
            or any(not isinstance(b, dict) or set(b) != {"type", "text"}
                   or b["type"] != "text" or not isinstance(b["text"], str) for b in content)):
        fail("malformed visible Read result")
    # Arrays have no single text byte representation. Retain the exact value
    # and label its deterministic serialization; the raw record is authoritative.
    return json.dumps(content, ensure_ascii=False, separators=(",", ":")).encode(), "json-text-blocks"


def _read_result(use, block, event, captured):
    if block.get("is_error", False) is not False:
        fail("Read error result")
    visible, encoding = _visible(block.get("content"))
    result = event.get("tool_use_result")
    if not isinstance(result, dict) or result.get("type") != "text" or not isinstance(result.get("file"), dict):
        fail("missing structured text/file Read result")
    file = result["file"]
    requested = use["input"]["file_path"]
    actual = file.get("filePath")
    if not isinstance(actual, str) or not Path(actual).is_absolute() or actual != requested:
        fail("Read requested/result path mismatch")
    if not isinstance(file.get("content"), str):
        fail("missing raw file content")
    payload = file["content"].encode("utf-8")
    if any(type(file.get(k)) is not int for k in ("startLine", "numLines", "totalLines")):
        fail("invalid line metadata")
    if file["startLine"] != 1 or file["numLines"] != file["totalLines"] or file["numLines"] < 0:
        fail("partial Read line metadata")
    authority = captured.get(requested)
    if authority is not None:
        if payload != authority["payload"]:
            fail("raw recovery content mismatch")
        # Refuse changed/symlinked snapshots, even if the stream claims old bytes.
        if direct_bytes(Path(requested), max_bytes=1 << 20) != payload:
            fail("recovery snapshot changed after launch")
    return {"visible_content": block["content"], "visible_identity": identity(visible),
            "visible_encoding": encoding, "raw_identity": identity(payload),
            "structured_file": file, "authorized_recovery": authority["entry"] if authority else None}


def _unchanged_result(use, block, event, reads, captured):
    """Claude Code 2.1.281 file_unchanged: reference, not payload delivery."""
    if block.get("is_error", False) is not False:
        fail("Read error result")
    visible, encoding = _visible(block.get("content"))
    requested = use["input"]["file_path"]
    authority = captured.get(requested)
    if authority is None:
        fail("unchanged Read requires captured recovery authority")
    if event.get("tool_use_result") != {"type": "file_unchanged", "file": {"filePath": requested}}:
        fail("unsupported unchanged Read shape/path")
    prior = [r for r in reads if r["input"]["file_path"] == requested and "result" in r
             and not r["result"].get("unchanged", False) and r["result"]["record"] < use["record"]]
    if not prior:
        fail("unchanged Read without prior complete result")
    previous = prior[-1]
    payload = previous["result"]["structured_file"]["content"].encode("utf-8")
    if (payload != authority["payload"] or previous["result"]["authorized_recovery"] != authority["entry"]
            or identity(payload) != {k: authority["entry"][k] for k in ("bytes", "sha256")}):
        fail("unchanged Read differs from captured authority")
    if direct_bytes(Path(requested), max_bytes=MAX_RECORD) != payload:
        fail("unchanged Read source differs from prior full result")
    return {"visible_content": block["content"], "visible_identity": identity(visible),
            "visible_encoding": encoding, "raw_identity": identity(payload),
            "structured_file": event["tool_use_result"]["file"], "unchanged": True,
            "prior_full_tool_use_id": previous["id"], "new_controlled_payload_bytes": 0,
            "authorized_recovery": previous["result"]["authorized_recovery"]}


class _Observer:
    def __init__(self, captured):
        self.captured = captured
        self.uses = {}
        self.results = set()
        self.reads = []
        self.session = None
        self.record_ids = set()
        self.terminal = None

    def session_id(self, event):
        value = event.get("session_id")
        if not isinstance(value, str) or not value:
            fail("missing session identity")
        if self.session is not None and self.session != value:
            fail("ambiguous session identity")
        self.session = value

    def assistant(self, event, number, line):
        if any(k in event for k in ("content", "tool_use_result")) or event.get("parent_tool_use_id") is not None:
            fail("ambiguous or nested assistant envelope")
        blocks = _blocks(event)
        wire = event.get("wire_tool_inputs")
        if wire is not None and wire != {b.get("id"): b.get("input") for b in blocks if b["type"] == "tool_use"}:
            fail("wire tool input mismatch")
        for index, block in enumerate(blocks):
            if block["type"] != "tool_use":
                if block["type"] not in ("text", "thinking", "redacted_thinking") or _hidden_tool(block):
                    fail("hidden or malformed assistant tool envelope")
                continue
            tool_id = block.get("id")
            if not isinstance(tool_id, str) or not tool_id or tool_id in self.uses:
                fail("duplicate or missing tool-use ID")
            if not isinstance(block.get("name"), str) or not isinstance(block.get("input"), dict):
                fail("malformed tool use")
            use = {**block, "record": number, "block": index, "record_sha256": digest(line),
                   "record_id": event.get("uuid"), "parent_tool_use_id": event.get("parent_tool_use_id"),
                   "caller_metadata": block.get("caller"), "wire_tool_inputs": wire}
            self.uses[tool_id] = use
            if block["name"] == "Read":
                if set(block["input"]) != {"file_path"}:
                    fail("partial or unrecognized Read arguments")
                path = block["input"]["file_path"]
                if not isinstance(path, str) or not Path(path).is_absolute():
                    fail("invalid requested Read path")
                self.reads.append(use)

    def user(self, event, number, line):
        if "content" in event or event.get("parent_tool_use_id") is not None:
            fail("ambiguous or nested user envelope")
        blocks = _blocks(event)
        results = [b for b in blocks if b["type"] == "tool_result"]
        if "tool_use_result" in event and len(results) != 1:
            fail("ambiguous structured tool result")
        for block in blocks:
            if block["type"] != "tool_result":
                if block["type"] != "text" or not isinstance(block.get("text"), str) or _hidden_tool(block):
                    fail("hidden or malformed user tool envelope")
                continue
            tool_id = block.get("tool_use_id")
            if not isinstance(tool_id, str) or tool_id not in self.uses or tool_id in self.results:
                fail("result before use, duplicate or missing ID")
            self.results.add(tool_id)
            use = self.uses[tool_id]
            if use["name"] == "Read":
                result = event.get("tool_use_result")
                observed = (_unchanged_result(use, block, event, self.reads, self.captured)
                            if isinstance(result, dict) and result.get("type") == "file_unchanged"
                            else _read_result(use, block, event, self.captured))
                use["result"] = {**observed,
                                 "record": number, "record_sha256": digest(line), "record_id": event.get("uuid")}

    def accept(self, event, number, line):
        if self.terminal is not None:
            fail("event after terminal result")
        record_id = event.get("uuid")
        if record_id is not None:
            if not isinstance(record_id, str) or not record_id or record_id in self.record_ids:
                fail("ambiguous record identity")
            self.record_ids.add(record_id)
        kind = event["type"]
        if "session_id" in event or kind in ("assistant", "user", "result"):
            self.session_id(event)
        if kind == "assistant":
            self.assistant(event, number, line)
        elif kind == "user":
            self.user(event, number, line)
        elif kind == "result":
            if event.get("subtype") != "success" or event.get("is_error", False) is not False or _hidden_tool(event):
                fail("unsuccessful or malformed terminal result")
            self.terminal = event
        elif _hidden_tool(event) or any(k in event for k in ("message", "content")):
            fail("unknown event may hide tool activity")


def observe(raw, *, expected_sha256, captured, scope):
    """Enumerate every native Read and derive each authorized delivery once."""
    if digest(raw) != expected_sha256:
        fail("raw stream digest mismatch")
    if set(scope) != {"run_id", "binding_id", "attempt_id"} or not all(isinstance(v, str) and v for v in scope.values()):
        fail("invalid observation scope")
    for path, authority in captured.items():
        if (authority.get("scope") != scope
                or identity(authority["payload"]) != {k: authority["entry"][k] for k in ("bytes", "sha256")}
                or direct_bytes(Path(path), max_bytes=1 << 20) != authority["payload"]):
            fail("captured recovery scope or source changed")
    observer = _Observer(captured)
    for number, line, event in _records(raw):
        observer.accept(event, number, line)
    if observer.terminal is None or any("result" not in r for r in observer.reads):
        fail("missing terminal or Read result")
    events = []
    for read in observer.reads:
        row = read["result"]["authorized_recovery"]
        if row is None or read["result"].get("unchanged", False):
            continue
        event_id = digest(json.dumps([scope, expected_sha256, read["id"]], sort_keys=True).encode())
        events.append({"schema": "apg.acquisition-event/v1", **scope, "event_id": event_id,
                       "kind": "recovery_read_observed", "phase": "late", "channel": "recovery_read",
                       "controlled_bytes": row["bytes"], "payload_sha256": row["sha256"],
                       "provenance": row["path"], "skill_id": row["id"], "recovery_entry": row,
                       "requested_path": read["input"]["file_path"], "tool_use_id": read["id"],
                       "raw_stream_sha256": expected_sha256, "observation_kind": "claude_stream_read",
                       "provider_observed": None, "model_observed": None})
    return {"schema": SCHEMA, "coverage": "complete", "scope": scope, "raw_stream": identity(raw),
            "session_id": observer.session, "reads": observer.reads, "events": events,
            "terminal": observer.terminal, "model_observed": None}


def retain_completion(environment, log_path, *, complete, process_status=0):
    """Called only by the live-log owner after drain and fsync; absent on normal launches."""
    from .transmission import SCOPE_ENV
    from .context_adapter import _write_new
    import os
    import stat
    try:
        scope = decode(environment.get(SCOPE_ENV, "{}").encode())
        expected = scope.get("claude_read_stream")
        if expected is None:
            return True
        if str(log_path) != expected or not complete:
            return False
        if isinstance(process_status, bool) or not isinstance(process_status, int):
            return False
        raw = direct_bytes(log_path, max_bytes=MAX_LOG)
        # A drained pipe can still contain truncated or invalid provider JSONL.
        # Capture completeness never certifies such bytes as a complete stream.
        for _record in _records(raw):
            pass
        if stat.S_IMODE(log_path.stat().st_mode) != 0o600:
            return False
        # The directory entry, not just file contents, must be durable.
        fd = os.open(log_path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        _write_new(log_path.with_suffix(".complete.json"),
                   {"schema": "apg.claude-stream-completion/v2", "plan": scope["reference"],
                    "scope": scope["record"], "raw_stream": identity(raw),
                    "durable": True, "stream_enabled_before_start": True,
                    "process_status": process_status})
        return True
    except (OSError, ValueError, KeyError, TypeError):
        return False
