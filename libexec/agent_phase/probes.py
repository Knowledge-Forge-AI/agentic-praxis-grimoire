"""Bounded on-demand operational probe collector for provider tooling.

Provides truthful, non-intrusive operational observations for dynamic routing
without background daemons, credential scraping, or token consumption.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
import shutil
import sqlite3
import subprocess
import time
from typing import Any

from .dynamic_router import OperationalObservation

PROBE_TIMEOUT_SECONDS = 5.0
PROBE_PRODUCER = "apgr_operational_probe"


def compute_observation_digest(
    observation_id: str,
    producer: str,
    observation_type: str,
    provider: str,
    state_value: str,
    profile: str | None = None,
    timestamp: float = 0.0,
    expires_at: float | None = None,
    detail: Mapping[str, Any] | None = None,
) -> str:
    """Compute deterministic canonical SHA-256 digest for an observation."""
    payload = {
        "detail": dict(detail) if detail else None,
        "expires_at": float(expires_at) if expires_at is not None else None,
        "observation_id": observation_id,
        "observation_type": observation_type,
        "producer": producer,
        "profile": profile,
        "provider": provider,
        "state_value": state_value,
        "timestamp": float(timestamp),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def probe_executable_version(
    provider: str,
    *,
    timeout: float = PROBE_TIMEOUT_SECONDS,
    executable_override: str | None = None,
    now: float | None = None,
) -> OperationalObservation:
    """Probe installed executable presence and version for a provider."""
    ref_now = time.time() if now is None else float(now)
    obs_id = f"obs-avail-{provider}-{int(ref_now * 1000)}"

    binary_candidates = {
        "codex": ["codex"],
        "claude": ["claude"],
        "antigravity": ["agy", "antigravity"],
    }

    resolved_bin: str | None = executable_override
    if resolved_bin is None:
        for name in binary_candidates.get(provider, [provider]):
            found = shutil.which(name)
            if found:
                resolved_bin = found
                break

    if resolved_bin is None:
        state_value = "unavailable"
        detail = {"reason": "executable_not_found", "candidates": binary_candidates.get(provider, [provider])}
        digest = compute_observation_digest(
            obs_id, PROBE_PRODUCER, "availability", provider, state_value,
            timestamp=ref_now, expires_at=ref_now + 60.0, detail=detail,
        )
        return OperationalObservation(
            observation_id=obs_id,
            producer=PROBE_PRODUCER,
            observation_type="availability",
            provider=provider,
            timestamp=ref_now,
            expires_at=ref_now + 60.0,
            state_value=state_value,
            detail=detail,
            digest=digest,
        )

    try:
        proc = subprocess.run(
            [resolved_bin, "--version"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if proc.returncode == 0:
            version_str = (proc.stdout or proc.stderr).strip().splitlines()[0] if (proc.stdout or proc.stderr) else "unknown"
            state_value = "available"
            detail = {"executable": resolved_bin, "version": version_str}
        else:
            state_value = "unavailable"
            detail = {"executable": resolved_bin, "exit_code": proc.returncode, "error": proc.stderr.strip()[:200]}
    except FileNotFoundError as exc:
        state_value = "unavailable"
        detail = {"executable": resolved_bin, "error": str(exc)}
    except (subprocess.SubprocessError, OSError) as exc:
        state_value = "unknown"
        detail = {"executable": resolved_bin, "error": str(exc)}

    expires = ref_now + 60.0
    digest = compute_observation_digest(
        obs_id, PROBE_PRODUCER, "availability", provider, state_value,
        timestamp=ref_now, expires_at=expires, detail=detail,
    )
    return OperationalObservation(
        observation_id=obs_id,
        producer=PROBE_PRODUCER,
        observation_type="availability",
        provider=provider,
        timestamp=ref_now,
        expires_at=expires,
        state_value=state_value,
        detail=detail,
        digest=digest,
    )


def probe_authentication(
    provider: str,
    *,
    timeout: float = PROBE_TIMEOUT_SECONDS,
    now: float | None = None,
) -> OperationalObservation:
    """Truthful, bounded probe of provider authentication / session usability.
    
    Never inspects private credential files, secret tokens, or keychain data.
    If no free non-substantive provider status query exists, returns 'unknown'.
    """
    ref_now = time.time() if now is None else float(now)
    obs_id = f"obs-auth-{provider}-{int(ref_now * 1000)}"
    state_value = "unknown"
    detail = {"reason": "no_non_intrusive_tokenless_auth_probe"}
    expires = ref_now + 60.0
    digest = compute_observation_digest(
        obs_id, PROBE_PRODUCER, "authentication", provider, state_value,
        timestamp=ref_now, expires_at=expires, detail=detail,
    )
    return OperationalObservation(
        observation_id=obs_id,
        producer=PROBE_PRODUCER,
        observation_type="authentication",
        provider=provider,
        timestamp=ref_now,
        expires_at=expires,
        state_value=state_value,
        detail=detail,
        digest=digest,
    )


def probe_quota_usage(
    provider: str,
    *,
    now: float | None = None,
) -> OperationalObservation:
    """Truthfully observe usage/quota state.
    
    No installed CLI provides a reliable, non-model-consuming remaining-quota query.
    Per ADR 0064, 'unknown' is a first-class truthful state that is admitted fail-open.
    """
    ref_now = time.time() if now is None else float(now)
    obs_id = f"obs-quota-{provider}-{int(ref_now * 1000)}"
    state_value = "unknown"
    detail = {"reason": "quota_unobservable_without_model_turn"}
    expires = ref_now + 60.0
    digest = compute_observation_digest(
        obs_id, PROBE_PRODUCER, "quota", provider, state_value,
        timestamp=ref_now, expires_at=expires, detail=detail,
    )
    return OperationalObservation(
        observation_id=obs_id,
        producer=PROBE_PRODUCER,
        observation_type="quota",
        provider=provider,
        timestamp=ref_now,
        expires_at=expires,
        state_value=state_value,
        detail=detail,
        digest=digest,
    )


def _parse_attempt_timestamp(val: Any) -> float:
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
            return dt.timestamp()
        except Exception:
            try:
                return float(val)
            except Exception:
                pass
    return 0.0


def probe_cooldown(
    provider: str,
    profile: str | None = None,
    conn: sqlite3.Connection | None = None,
    *,
    window_seconds: float = 300.0,
    now: float | None = None,
) -> OperationalObservation:
    """Probe recent failure history in dispatcher SQLite database for active cooldown."""
    ref_now = time.time() if now is None else float(now)
    obs_id = f"obs-cool-{provider}-{int(ref_now * 1000)}"
    active_cooldown = False
    cooldown_expires: float | None = None
    detail: dict[str, Any] = {"window_seconds": window_seconds}

    if conn is not None:
        try:
            cur = conn.cursor()
            query = (
                "SELECT started_at, completed_at, status FROM invocation_attempts "
                "WHERE provider = ? AND status = 'failed' "
                "ORDER BY started_at DESC LIMIT 1"
            )
            cur.execute(query, (provider,))
            row = cur.fetchone()
            if row:
                fail_ts = _parse_attempt_timestamp(row[1] or row[0])
                elapsed = ref_now - fail_ts
                if 0.0 <= elapsed < window_seconds:
                    active_cooldown = True
                    cooldown_expires = fail_ts + window_seconds
                    detail["last_failed_attempt"] = str(row[0])
                    detail["elapsed_seconds"] = elapsed
                else:
                    detail["last_failed_attempt_expired"] = str(row[0])
                    detail["elapsed_seconds"] = elapsed
        except Exception:
            pass

    state_value = "active_cooldown" if active_cooldown else "no_active_cooldown"
    expires = cooldown_expires if active_cooldown else (ref_now + 60.0)
    digest = compute_observation_digest(
        obs_id, PROBE_PRODUCER, "cooldown", provider, state_value,
        profile=profile, timestamp=ref_now, expires_at=expires, detail=detail,
    )
    return OperationalObservation(
        observation_id=obs_id,
        producer=PROBE_PRODUCER,
        observation_type="cooldown",
        provider=provider,
        profile=profile,
        timestamp=ref_now,
        expires_at=expires,
        state_value=state_value,
        detail=detail,
        digest=digest,
    )


def collect_operational_observations(
    conn: sqlite3.Connection | None = None,
    *,
    now: float | None = None,
    providers: Sequence[str] = ("codex", "claude", "antigravity"),
    injected: Sequence[OperationalObservation] = (),
) -> list[OperationalObservation]:
    """Collect bounded operational observations for dynamic routing."""
    ref_now = time.time() if now is None else float(now)
    results: list[OperationalObservation] = []
    seen_ids: set[str] = set()

    # 1. Injected observations take highest precedence (operator authority)
    for inj in injected:
        if inj.digest is None:
            computed = compute_observation_digest(
                inj.observation_id,
                inj.producer,
                inj.observation_type,
                inj.provider,
                inj.state_value,
                profile=inj.profile,
                timestamp=inj.timestamp,
                expires_at=inj.expires_at,
                detail=inj.detail,
            )
            inj = OperationalObservation(
                observation_id=inj.observation_id,
                producer=inj.producer,
                observation_type=inj.observation_type,
                provider=inj.provider,
                profile=inj.profile,
                timestamp=inj.timestamp,
                expires_at=inj.expires_at,
                state_value=inj.state_value,
                detail=inj.detail,
                digest=computed,
            )
        if inj.observation_id not in seen_ids:
            results.append(inj)
            seen_ids.add(inj.observation_id)

    injected_keys = {(obs.provider, obs.observation_type) for obs in injected}

    # 2. Active durable observations from SQLite
    if conn is not None:
        from .persistence_feedback import (
            get_active_operational_observations,
            row_to_operational_observation,
        )

        active_rows = get_active_operational_observations(conn, now=ref_now)
        for row in active_rows:
            obs = row_to_operational_observation(row)
            if obs.observation_id not in seen_ids:
                results.append(obs)
                seen_ids.add(obs.observation_id)

    # 3. Current bounded tokenless probes
    for p in providers:
        if (p, "availability") not in injected_keys:
            obs_avail = probe_executable_version(p, now=ref_now)
            if obs_avail.observation_id not in seen_ids:
                results.append(obs_avail)
                seen_ids.add(obs_avail.observation_id)
        if (p, "authentication") not in injected_keys:
            obs_auth = probe_authentication(p, now=ref_now)
            if obs_auth.observation_id not in seen_ids:
                results.append(obs_auth)
                seen_ids.add(obs_auth.observation_id)
        if (p, "quota") not in injected_keys:
            obs_quota = probe_quota_usage(p, now=ref_now)
            if obs_quota.observation_id not in seen_ids:
                results.append(obs_quota)
                seen_ids.add(obs_quota.observation_id)
        if (p, "cooldown") not in injected_keys:
            obs_cd = probe_cooldown(p, conn=conn, now=ref_now)
            if obs_cd.observation_id not in seen_ids:
                results.append(obs_cd)
                seen_ids.add(obs_cd.observation_id)

    results.sort(key=lambda o: (o.timestamp, o.observation_id))
    return results
