"""Qualification tests for bounded on-demand operational probes."""

from __future__ import annotations

from pathlib import Path
import sqlite3
import sys
import time

from agent_phase.dynamic_router import OperationalObservation
from agent_phase.probes import (
    compute_observation_digest,
    probe_executable_version,
    probe_authentication,
    probe_quota_usage,
    probe_cooldown,
    collect_operational_observations,
)


def test_compute_observation_digest_deterministic() -> None:
    now = 1726500000.0
    d1 = compute_observation_digest(
        "obs-1",
        "probe",
        "availability",
        "codex",
        "available",
        profile="profile-a",
        timestamp=now,
        expires_at=now + 60.0,
        detail={"version": "1.0"},
    )
    d2 = compute_observation_digest(
        "obs-1",
        "probe",
        "availability",
        "codex",
        "available",
        profile="profile-a",
        timestamp=now,
        expires_at=now + 60.0,
        detail={"version": "1.0"},
    )
    assert d1 == d2
    assert len(d1) == 64

    # Changing any field changes the digest
    d3 = compute_observation_digest(
        "obs-2",
        "probe",
        "availability",
        "codex",
        "available",
        profile="profile-a",
        timestamp=now,
        expires_at=now + 60.0,
        detail={"version": "1.0"},
    )
    assert d1 != d3


def test_probe_executable_version_found_and_not_found(tmp_path: Path) -> None:
    # 1a. Binary candidate not found in PATH
    obs_not_in_path = probe_executable_version("unknown-provider-xyz")
    assert obs_not_in_path.state_value == "unavailable"
    assert obs_not_in_path.observation_type == "availability"
    assert obs_not_in_path.detail is not None
    assert obs_not_in_path.detail.get("reason") == "executable_not_found"

    # 1b. Non-existent binary override
    obs_not_found = probe_executable_version(
        "unknown-provider-xyz",
        executable_override=str(tmp_path / "non_existent_binary_12345"),
    )
    assert obs_not_found.state_value == "unavailable"
    assert obs_not_found.detail is not None
    assert "error" in obs_not_found.detail

    # 2. Existing binary using python3 executable override
    python_bin = sys.executable
    obs_found = probe_executable_version("codex", executable_override=python_bin)
    assert obs_found.state_value == "available"
    assert obs_found.detail is not None
    assert "Python" in obs_found.detail.get("version", "")
    assert obs_found.digest is not None

    # 3. Failing binary (returns non-zero exit code)
    bad_script = tmp_path / "bad_bin.sh"
    bad_script.write_text("#!/bin/sh\nexit 2\n")
    bad_script.chmod(0o755)
    obs_failed = probe_executable_version("claude", executable_override=str(bad_script))
    assert obs_failed.state_value == "unavailable"
    assert obs_failed.detail is not None
    assert obs_failed.detail.get("exit_code") == 2


def test_probe_authentication_unknown_and_non_intrusive() -> None:
    obs = probe_authentication("codex")
    assert obs.observation_type == "authentication"
    assert obs.state_value == "unknown"
    assert obs.detail is not None
    assert obs.detail.get("reason") == "no_non_intrusive_tokenless_auth_probe"
    assert obs.digest is not None


def test_probe_quota_usage_unknown_truthful() -> None:
    obs = probe_quota_usage("antigravity")
    assert obs.observation_type == "quota"
    assert obs.state_value == "unknown"
    assert obs.detail is not None
    assert obs.detail.get("reason") == "quota_unobservable_without_model_turn"
    assert obs.digest is not None


def test_probe_cooldown_with_and_without_failures(tmp_path: Path) -> None:
    # 1. No connection
    obs_no_conn = probe_cooldown("codex", conn=None)
    assert obs_no_conn.state_value == "no_active_cooldown"

    # 2. With connection but empty table
    db_path = tmp_path / "test_dispatcher.sqlite3"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE invocation_attempts (
            attempt_id TEXT PRIMARY KEY,
            run_id TEXT,
            provider TEXT,
            started_at REAL,
            completed_at REAL,
            status TEXT
        )
        """
    )
    conn.commit()

    obs_clean = probe_cooldown("codex", conn=conn)
    assert obs_clean.state_value == "no_active_cooldown"

    # 3. With failed attempt within window
    now = time.time()
    cur.execute(
        "INSERT INTO invocation_attempts VALUES ('att-1', 'run-1', 'codex', ?, ?, 'failed')",
        (now - 10.0, now - 5.0),
    )
    conn.commit()

    obs_failed = probe_cooldown("codex", conn=conn, window_seconds=300.0)
    assert obs_failed.state_value == "active_cooldown"
    assert obs_failed.expires_at is not None
    assert obs_failed.expires_at > now
    assert obs_failed.detail is not None
    assert "last_failed_attempt" in obs_failed.detail

    # 4. Failed attempt older than window_seconds does NOT trigger cooldown
    obs_expired = probe_cooldown("codex", conn=conn, window_seconds=3.0)
    assert obs_expired.state_value == "no_active_cooldown"

    # 5. Schema with TEXT ISO timestamps (as in real persistence.py)
    cur.execute(
        "INSERT INTO invocation_attempts VALUES ('att-2', 'run-2', 'claude', '2020-01-01T00:00:00Z', '2020-01-01T00:01:00Z', 'failed')"
    )
    conn.commit()
    obs_old_iso = probe_cooldown("claude", conn=conn, window_seconds=300.0)
    assert obs_old_iso.state_value == "no_active_cooldown"


def test_collect_operational_observations_default_and_injected() -> None:
    # By default, collects 4 observations for each of (codex, claude, antigravity) = 12
    observations = collect_operational_observations()
    assert len(observations) == 12
    for obs in observations:
        assert obs.digest is not None

    # Injected observation overrides probed one and receives computed digest
    injected_obs = OperationalObservation(
        observation_id="custom-1",
        producer="manual_test",
        observation_type="availability",
        provider="codex",
        timestamp=time.time(),
        expires_at=time.time() + 100.0,
        state_value="available",
        detail={"source": "test"},
    )
    assert injected_obs.digest is not None

    collected = collect_operational_observations(
        providers=["codex"],
        injected=[injected_obs],
    )
    # codex has injected availability, plus probed auth, quota, cooldown -> total 4
    assert len(collected) == 4
    inj_retrieved = next(o for o in collected if o.observation_type == "availability")
    assert inj_retrieved.observation_id == "custom-1"
    assert inj_retrieved.digest is not None
