"""Read model metadata only for provider-issued worker session identifiers."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from collections import Counter

_UUID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\Z")


def _read_metadata_line(path: Path) -> dict | None:
    """Read only the first line session_meta for candidate session files."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as stream:
            first_line = stream.readline(64 * 1024)
            if not first_line:
                return None
            event = json.loads(first_line)
            if isinstance(event, dict) and event.get("type") == "session_meta":
                payload = event.get("payload")
                if isinstance(payload, dict):
                    return payload
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        pass
    return None


def _read_session(path: Path) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > 32 * 1024 * 1024:
            raise ValueError("invalid session size/type")
        raw = stream.read(32 * 1024 * 1024 + 1)
        after = os.fstat(stream.fileno())
    def identity(st):
        return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
    if identity(before) != identity(after) or len(raw) != before.st_size:
        raise ValueError("session changed during observation")
    return raw


def claude_session(session_id: str, home: Path | None = None) -> dict:
    """Read exact provider session metadata, never assistant content.

    The caller's Claude config directory is the launch authority. Missing,
    ambiguous, malformed or conflicting observations do not become settings.
    """
    result = {"session_id": session_id, "effective_model": None,
              "effective_effort": None, "source": "effective_model_unobservable",
              "scope": "provider runtime assistant configuration"}
    if not isinstance(session_id, str) or not _UUID.fullmatch(session_id):
        return {**result, "limitation": "invalid_session_id"}
    home = home or Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude")))
    paths = list((home / "projects").glob(f"*/{session_id}.jsonl"))
    if not paths:
        paths = list((home / "sessions").glob(f"*{session_id}.jsonl"))
    if not paths:
        paths = list((home / "sessions").glob(f"*/*/*/*{session_id}.jsonl"))
    if not paths:
        paths = list(home.glob(f"*{session_id}.jsonl"))
    if len(paths) != 1:
        return {**result, "limitation": "missing_or_ambiguous_session"}
    try:
        path = paths[0]
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("session must be a regular file")
        raw = _read_session(path)
        after = path.lstat()
        def identity(st):
            return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
        if identity(before) != identity(after):
            raise ValueError("session entry changed")
        records = [json.loads(line) for line in raw.splitlines() if line.strip()]
        if any(not isinstance(r, dict) or ("sessionId" in r and r["sessionId"] != session_id)
               for r in records):
            raise ValueError("session identity mismatch")
        assistants = [r for r in records if r.get("type") == "assistant" and not r.get("isSidechain")]
        if not assistants or any(r.get("sessionId") != session_id for r in assistants):
            raise ValueError("unbound assistant metadata")
        models, efforts = set(), set()
        missing_model = missing_effort = False
        for record in assistants:
            message = record.get("message")
            model = message.get("model") if isinstance(message, dict) else None
            if isinstance(model, str) and model.strip():
                models.add(model.strip())
            else:
                missing_model = True
            values = [record[k] for k in ("effort", "perTurnEffort") if k in record]
            if not values or any(not isinstance(v, str) or not v.strip() for v in values):
                missing_effort = True
            efforts.update(v.strip() for v in values if isinstance(v, str) and v.strip())
        result.update(source="claude_session_assistant_metadata", sha256=hashlib.sha256(raw).hexdigest(),
                      size_bytes=len(raw), record_count=len(records), assistant_count=len(assistants),
                      event_types=dict(Counter(r.get("type", "unknown") for r in records)),
                      observed_models=sorted(models), observed_efforts=sorted(efforts),
                      effective_model=next(iter(models)) if len(models) == 1 and not missing_model else None,
                      effective_effort=next(iter(efforts)) if len(efforts) == 1 and not missing_effort else None)
        result["limitation"] = None if result["effective_model"] and result["effective_effort"] else "missing_or_conflicting_metadata"
    except (OSError, ValueError, TypeError):
        result["limitation"] = "unreadable_unstable_or_invalid_session"
    return result


_HEX_ID = re.compile(r"[0-9a-f]{8,64}\Z")


def claude_native_child_session(parent_session_id: str, child_agent_id: str, home: Path | None = None) -> dict:
    """Export bounded metadata only from exact correlated provider child records."""
    result = {"parent_session_id": parent_session_id, "child_agent_id": child_agent_id,
              "session_id": parent_session_id, "agent_id": child_agent_id,
              "effective_model": None, "effective_effort": None,
              "effort_semantics": "unestablished", "effort_observation_status": "absent",
              "source": "effective_model_unobservable", "scope": "provider runtime native child configuration"}
    if not isinstance(parent_session_id, str) or not _UUID.fullmatch(parent_session_id):
        return {**result, "limitation": "invalid_session_id"}
    if not isinstance(child_agent_id, str) or not _HEX_ID.fullmatch(child_agent_id):
        return {**result, "limitation": "invalid_child_agent_id"}
    home = Path(home or os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude")))
    projects = home / "projects"
    child_paths = list(projects.glob(f"*/{parent_session_id}/subagents/agent-{child_agent_id}.jsonl"))
    parent_paths = list(projects.glob(f"*/{parent_session_id}.jsonl"))
    if len(child_paths) > 1 or len(parent_paths) > 1:
        return {**result, "limitation": "missing_or_ambiguous_session"}

    def read_source(path: Path, fallback: bool) -> dict | None:
        before = path.lstat()
        current = path
        while current != current.parent:
            if current.is_symlink():
                raise ValueError("indirect metadata path")
            if current == home:
                break
            current = current.parent
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("nonregular metadata")
        raw = _read_session(path)

        def identity(st):
            return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)

        if identity(before) != identity(path.lstat()):
            raise ValueError("metadata entry changed")
        records = [json.loads(line) for line in raw.splitlines() if line.strip()]
        if any(not isinstance(r, dict) for r in records):
            raise ValueError("invalid metadata record")
        if fallback:
            records = [r for r in records if r.get("agentId") == child_agent_id]
            if not records:
                return None
        if any(("sessionId" in r and r["sessionId"] != parent_session_id)
               or ("agentId" in r and r["agentId"] != child_agent_id)
               or ("isSidechain" in r and r["isSidechain"] is not True) for r in records):
            raise ValueError("unbound child metadata")
        assistants = [r for r in records if r.get("type") == "assistant"]
        if not assistants or any(r.get("sessionId") != parent_session_id
                or r.get("agentId") != child_agent_id or r.get("isSidechain") is not True for r in assistants):
            raise ValueError("missing bound assistant metadata")
        models, efforts = set(), set()
        missing_model = missing_effort = False
        for r in assistants:
            msg = r.get("message")
            model = msg.get("model") if isinstance(msg, dict) else None
            if isinstance(model, str) and 0 < len(model.strip()) <= 256:
                models.add(model.strip())
            else:
                missing_model = True
            values = [r[k] for k in ("effort", "perTurnEffort") if k in r]
            if not values or any(not isinstance(v, str) or not 0 < len(v.strip()) <= 64 for v in values):
                missing_effort = True
            efforts.update(v.strip() for v in values if isinstance(v, str) and 0 < len(v.strip()) <= 64)
        if len(models) > 32 or len(efforts) > 32:
            raise ValueError("metadata cardinality exceeded")
        effort_status = ("absent" if not efforts else "multiple_values" if len(efforts) > 1
                         else "partial" if missing_effort else "single_value")
        return {"source": "claude_sidechain_assistant_metadata" if fallback else "claude_native_child_session_metadata",
                "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw),
                "record_count": len(records), "assistant_count": len(assistants),
                "observed_models": sorted(models), "observed_efforts": sorted(efforts),
                "effective_model": next(iter(models)) if len(models) == 1 and not missing_model else None,
                "effective_effort": None, "effort_semantics": "unestablished",
                "effort_observation_status": effort_status}
    try:
        sources = []
        if child_paths:
            sources.append(read_source(child_paths[0], False))
        if parent_paths:
            fallback = read_source(parent_paths[0], True)
            if fallback:
                sources.append(fallback)
        if not sources:
            return {**result, "limitation": "missing_or_ambiguous_session"}
        observation = dict(sources[0])
        if len(sources) == 2:
            observation["corroborating_source"] = sources[1]
            for effective, observed in (("effective_model", "observed_models"), ("effective_effort", "observed_efforts")):
                values = sorted(set(sources[0][observed]) | set(sources[1][observed]))
                observation[observed] = values[:32]
                if sources[0][effective] != sources[1][effective] or len(values) != 1:
                    observation[effective] = None
            observation["effort_observation_status"] = (
                "absent" if not observation["observed_efforts"] else
                "multiple_values" if len(observation["observed_efforts"]) > 1 else
                "partial" if any(s["effort_observation_status"] in {"absent", "partial"} for s in sources) else
                "single_value")
        result.update(observation)
        result["limitation"] = None if result["effective_model"] else "missing_or_conflicting_metadata"
    except (OSError, ValueError, TypeError):
        result["limitation"] = "unreadable_unstable_or_invalid_session"
    return result



def gemini_terminal_layers(summary: dict, wrapper_status: str) -> dict:
    """Name wrapper delivery and provider exit separately; preserve unknowns."""
    reasons = summary.get("reason_fields")
    reason = reasons.get("error", {}) if isinstance(reasons, dict) else {}
    return {
        "wrapper_exit_status": wrapper_status,
        "provider_raw_status": summary.get("raw_status"),
        "provider_raw_error": reason.get("text") if isinstance(reason, dict) else None,
        "provider_natural_exit": summary.get("child_exited_naturally"),
        "completion_contract": (
            "completion_fence" if summary.get("completion_fence_observed") is True
            else "natural_terminal_result" if summary.get("child_exited_naturally") is True
            and summary.get("terminal_result_observed") is True else None),
        "terminal_chronology": {key: summary.get(key) for key in (
            "completion_fence_sequence", "completion_fence_monotonic",
            "wrapper_signal_events", "terminal_result_sequence", "terminal_result_monotonic",
            "child_exit_monotonic", "wrapper_signal_preceded_result",
            "terminal_result_after_completion_fence", "transport_success")},
    }


def codex_session(thread_id: str, home: Path | None = None, *, expected_nonce: str | None = None, _children: bool = True) -> dict:
    """Extract runtime metadata and digest only; never retain session text.

    Child discovery reads metadata lines only in dates spanned by the bound
    parent record. Full reads require a unique exact parent/task relationship.
    """
    result = {"thread_id": thread_id, "effective_model": None, "effective_effort": None,
              "source": "effective_model_unobservable", "scope": "provider runtime turn configuration"}
    if not isinstance(thread_id, str) or not _UUID.fullmatch(thread_id):
        return result
    home = home or Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    paths = list((home / "sessions").glob(f"*/*/*/*{thread_id}.jsonl"))
    if len(paths) != 1:
        return result
    try:
        raw = _read_session(paths[0])
        records = [json.loads(line) for line in raw.splitlines() if line.strip()]
        metas = [e.get("payload") for e in records if e.get("type") == "session_meta"]
        if len(metas) != 1 or metas[0].get("id") != thread_id:
            return result
        meta = metas[0]
        turns = [e.get("payload", {}) for e in records if e.get("type") == "turn_context"]
        models = {t.get("model") for t in turns}
        efforts = {t.get("effort", t.get("reasoning_effort")) for t in turns}
        model = next(iter(models)) if len(models) == 1 and None not in models else None
        effort = next(iter(efforts)) if len(efforts) == 1 and None not in efforts else None
        terminal, active, deleted, nonce_returned = None, None, False, False
        for event in records:
            payload = event.get("payload", {})
            kind = payload.get("type") if event.get("type") == "event_msg" else event.get("type")
            if kind == "task_started":
                active, terminal = True, None
            elif kind in {"task_complete", "task.completed", "thread.completed"}:
                terminal, active = "completed", False
                if expected_nonce and expected_nonce in str(payload.get("last_agent_message", "")):
                    nonce_returned = True
            elif kind in {"task_deleted", "thread_deleted", "deleted", "thread.deleted", "task.deleted"}:
                deleted, active = True, False
                if terminal is None:
                    terminal = "deleted"
            elif kind in {"task_failed", "task_aborted", "turn_aborted", "error"}:
                terminal, active = "failed", False
        result.update(effective_model=model, effective_effort=effort, source="codex_session_turn_context",
                      sha256=hashlib.sha256(raw).hexdigest(), parent_thread_id=meta.get("parent_thread_id"),
                      agent_path=meta.get("source", {}).get("subagent", {}).get("thread_spawn", {}).get("agent_path") if isinstance(meta.get("source"), dict) else None,
                      observed_models=sorted(m for m in models if isinstance(m, str)),
                      observed_efforts=sorted(e for e in efforts if isinstance(e, str)), terminal_status=terminal,
                      active=active, native_thread_removal="observed_deleted" if deleted else "not_observable",
                      nonce_returned=nonce_returned if expected_nonce else None)
        calls, admissions = {}, []
        for event in records:
            payload = event.get("payload", {})
            if event.get("type") != "response_item":
                continue
            if payload.get("type") == "function_call" and payload.get("name") == "spawn_agent":
                args = json.loads(payload.get("arguments", "{}"))
                calls[payload.get("call_id")] = {k: args.get(k) for k in ("model", "reasoning_effort", "task_name")}
            elif payload.get("type") == "function_call_output" and payload.get("call_id") in calls:
                output = json.loads(payload.get("output", "{}"))
                if isinstance(output, dict) and isinstance(output.get("task_name"), str) and not output.get("error"):
                    admissions.append({"event": "session:function_call_output:spawn_agent", "call_id": payload["call_id"],
                        "parent_thread_id": thread_id, "task_name": output["task_name"], "status": "admitted",
                        "requested": calls[payload["call_id"]], "receiver_thread_ids": [],
                        "effective_model": None, "effective_effort": None, "terminal_status": "unknown",
                        "diagnostic": "native child runtime model metadata unavailable"})
        if _children and admissions:
            dates = {str(e.get("timestamp", ""))[:10] for e in records}
            directories = {paths[0].parent}
            for day in dates:
                if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", day):
                    directories.add(home / "sessions" / day.replace("-", "/"))
            candidates = [(p, _read_metadata_line(p)) for directory in sorted(directories)
                          for p in directory.glob("*.jsonl") if p != paths[0] and not p.is_symlink()]
            for admission in admissions:
                matches = []
                for path, child_meta in candidates:
                    if not child_meta or child_meta.get("parent_thread_id") != thread_id:
                        continue
                    source = child_meta.get("source", {})
                    spawn = source.get("subagent", {}).get("thread_spawn", {}) if isinstance(source, dict) else {}
                    if spawn.get("agent_path") == admission["task_name"]:
                        matches.append(child_meta)
                if len(matches) == 1:
                    child = codex_session(matches[0].get("id"), home, expected_nonce=expected_nonce, _children=False)
                    if child.get("parent_thread_id") == thread_id and child.get("agent_path") == admission["task_name"]:
                        admission.update(receiver_thread_ids=[child["thread_id"]], child_observation=child,
                            effective_model=child["effective_model"], effective_effort=child["effective_effort"],
                            child_sha256=child.get("sha256"), terminal_status=child.get("terminal_status"),
                            observed_models=child.get("observed_models", []), observed_efforts=child.get("observed_efforts", []),
                            diagnostic=None if child.get("effective_model") and child.get("effective_effort") else "native child runtime model metadata unavailable")
                elif len(matches) > 1:
                    admission["diagnostic"] = "ambiguous child session metadata: multiple matching sessions"
        result["native_admissions"] = admissions
    except (OSError, ValueError, AttributeError, TypeError):
        return {"thread_id": thread_id, "effective_model": None, "effective_effort": None, "source": "effective_model_unobservable"}
    return result


def external_events(kind, stdout):
    """Merge observed session facts into provider events without filling requested values."""
    if kind == "sonnet":
        from .claude_events import parse_claude_events
        events = parse_claude_events(stdout)
        ids = events.get("provider_identifiers") or {}
        observation = claude_session(ids.get("session_id", ids.get("sessionId", ids.get("uuid", ""))))
    else:
        from .codex_external import parse_codex_events
        events = parse_codex_events(stdout)
        ids = events.get("provider_identifiers") or {}
        observation = codex_session(ids.get("thread_id", ids.get("session_id", "")))
    events["session_model_observation"] = observation
    for key in ("effective_model", "effective_effort"):
        if events.get(key) is None:
            events[key] = observation.get(key)
    return events
