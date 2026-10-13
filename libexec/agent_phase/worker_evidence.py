"""Provider-observed worker evidence, kept separate from requested settings."""
from __future__ import annotations

import json


def events(raw: bytes) -> list[dict]:
    result = []
    for line in raw.splitlines():
        try:
            event = json.loads(line)
        except (ValueError, UnicodeDecodeError):
            continue
        if isinstance(event, dict):
            result.append(event)
    return result


def parent_observation(raw: bytes) -> dict:
    models, efforts = set(), set()
    for event in events(raw):
        # Only provider metadata, never assistant prose, tool arguments or prompts.
        if (event.get("type") == "system" and event.get("subtype") == "init") or event.get("type") in {"session.started", "turn.started"}:
            if isinstance(event.get("model"), str) and event["model"].strip():
                models.add(event["model"].strip())
            if isinstance(event.get("effort"), str) and event["effort"].strip():
                efforts.add(event["effort"].strip())
        # Inspect genuine provider result and usage metadata
        if event.get("type") in {"result", "turn.completed", "usage"}:
            usage = event.get("usage")
            if isinstance(usage, dict):
                for key in ("effort", "reasoning_effort"):
                    val = usage.get(key)
                    if isinstance(val, str) and val.strip():
                        efforts.add(val.strip())
                for key in ("model",):
                    val = usage.get(key)
                    if isinstance(val, str) and val.strip():
                        models.add(val.strip())
            res = event.get("result")
            if isinstance(res, dict):
                for key in ("effort", "reasoning_effort"):
                    val = res.get(key)
                    if isinstance(val, str) and val.strip():
                        efforts.add(val.strip())
                for key in ("model",):
                    val = res.get(key)
                    if isinstance(val, str) and val.strip():
                        models.add(val.strip())
            if event.get("type") in {"result", "turn.completed"}:
                for key in ("effort", "reasoning_effort"):
                    val = event.get(key)
                    if isinstance(val, str) and val.strip():
                        efforts.add(val.strip())
                if isinstance(event.get("model"), str) and event["model"].strip():
                    models.add(event["model"].strip())

    sessions = [e.get("thread_id") for e in events(raw) if e.get("type") == "thread.started" and isinstance(e.get("thread_id"), str)]
    from apgr_workers.model_observation import codex_session, claude_session
    observations = [codex_session(thread) for thread in sessions]
    claude_ids = {e["session_id"] for e in events(raw)
                  if e.get("type") == "system" and e.get("subtype") == "init"
                  and isinstance(e.get("session_id"), str)}
    if not sessions and len(claude_ids) == 1:
        claude_observation = claude_session(next(iter(claude_ids)))
        observations.append(claude_observation)
        # Conflicts must remain visible even when the session has no consensus.
        for target, key in ((models, "observed_models"), (efforts, "observed_efforts")):
            values = claude_observation.get(key, [])
            if len(values) > 1:
                target.update(values)
    for observation in observations:
        if observation.get("effective_model"):
            models.add(observation["effective_model"])
        if observation.get("effective_effort"):
            efforts.add(observation["effective_effort"])
    observed_provider = "codex" if sessions else "claude" if any(e.get("type") == "system" and e.get("subtype") == "init" for e in events(raw)) else None
    return {"provider": observed_provider, "session_observations": observations, "model": next(iter(models)) if len(models) == 1 else None,
            "effort": next(iter(efforts)) if len(efforts) == 1 else None,
            "observed_models": sorted(models), "observed_efforts": sorted(efforts),
            "source": "provider_metadata" if models else "effective_model_unobservable"}


def native_admissions(raw: bytes, *, expected_nonce: str | None = None) -> list[dict]:
    admissions = []
    for event in events(raw):
        item = event.get("item", {})
        if not isinstance(item, dict) or item.get("type") != "collab_tool_call":
            continue
        if item.get("tool") != "spawn_agent" or event.get("type") != "item.completed":
            continue
        receivers = item.get("receiver_thread_ids", [])
        if not isinstance(receivers, list) or not receivers:
            continue
        admissions.append({"event": "item.completed:collab_tool_call:spawn_agent",
                           "receiver_thread_ids": receivers,
                           "effective_model": item.get("effective_model"),
                           "effective_effort": item.get("effective_effort"),
                           "status": item.get("status")})
    from apgr_workers.model_observation import codex_session
    for admission in admissions:
        observations = [codex_session(thread, expected_nonce=expected_nonce) for thread in admission["receiver_thread_ids"]]
        admission["session_observations"] = observations
        if len(observations) == 1:
            admission["effective_model"] = observations[0].get("effective_model") or admission["effective_model"]
            admission["effective_effort"] = observations[0].get("effective_effort") or admission["effective_effort"]
            if observations[0].get("terminal_status"):
                admission["terminal_status"] = observations[0]["terminal_status"]
    # Some runtimes omit spawn from stdout but retain a successful tool receipt
    # in the provider-issued parent session. Requested model remains separate.
    if not admissions:
        for event in events(raw):
            if event.get("type") == "thread.started" and isinstance(event.get("thread_id"), str):
                admissions.extend(codex_session(event["thread_id"], expected_nonce=expected_nonce).get("native_admissions", []))
    for admission in admissions:
        if "session_observations" not in admission:
            receivers = admission.get("receiver_thread_ids", [])
            if receivers:
                observations = [codex_session(thread, expected_nonce=expected_nonce) for thread in receivers]
                admission["session_observations"] = observations
                if len(observations) == 1:
                    admission["effective_model"] = observations[0].get("effective_model") or admission.get("effective_model")
                    admission["effective_effort"] = observations[0].get("effective_effort") or admission.get("effective_effort")
                    if observations[0].get("terminal_status"):
                        admission["terminal_status"] = observations[0]["terminal_status"]
            else:
                admission["session_observations"] = []
    return admissions


def disposition(capability: dict, ledger_status: dict | None, raw: bytes) -> dict:
    if not capability.get("allowed"):
        return {"status": "unavailable", "reason": capability.get("reason", "worker_unavailable")}
    jobs = (ledger_status or {}).get("gemini_jobs", {})
    native = native_admissions(raw)
    native_count = (
        len(native) if native
        else len((ledger_status or {}).get("native_agents", {})) if isinstance((ledger_status or {}).get("native_agents"), dict)
        else (ledger_status or {}).get("native_count", 0) or 0
    )
    if jobs or native or native_count:
        return {"status": "used", "external_admissions": len(jobs), "native_admissions": native_count}
    return {"status": "declined", "reason": "no admission requested",
            "native_observation": "no native admission observed in provider stream"}
