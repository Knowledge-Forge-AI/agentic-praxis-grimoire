"""Real executable tripwires, without invoking installed model providers."""
import hashlib
import json
import subprocess

import pytest

from testing.h_eval import dry_run
from testing.h_eval.provider_free import LaunchGuard, ProviderInvocationError


@pytest.mark.parametrize("provider", ["codex", "claude", "antigravity"])
def test_actual_task_executable_retains_durable_sentinel(tmp_path, provider):
    guard = LaunchGuard(tmp_path / "guard")
    executable = guard.executable(provider, "fixture-profile")
    payload = b"private task input\n"
    result = subprocess.run([executable, "task"], input=payload, capture_output=True, cwd=tmp_path, check=False)
    assert result.returncode == 97
    records = list(guard.events.iterdir())
    assert len(records) == 1
    receipt = json.loads(records[0].read_bytes())
    assert receipt["provider"] == provider
    assert receipt["profile"] == "fixture-profile"
    assert receipt["stdin"] == {"status": "complete", "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
    assert receipt["cwd"]["inode"] == tmp_path.stat().st_ino
    assert records[0].stat().st_mode & 0o777 == 0o600
    with pytest.raises(ProviderInvocationError, match="sentinel"):
        guard.assert_clean()


def test_tripwire_does_not_allow_version_bypass(tmp_path):
    guard = LaunchGuard(tmp_path / "guard")
    executable = guard.executable("claude", "test")
    assert subprocess.run([executable, "--version"], input=b"", capture_output=True, check=False).returncode == 97
    with pytest.raises(ProviderInvocationError):
        guard.assert_clean()


def test_guard_detects_replacement_and_unexpected_growth(tmp_path):
    guard = LaunchGuard(tmp_path / "guard")
    executable = guard.executable("codex", "test")
    from pathlib import Path
    Path(executable).write_text("tampered")
    with pytest.raises(ProviderInvocationError):
        guard.assert_clean()


def test_dry_run_routes_use_tripwires_not_runtime_versions(tmp_path):
    with LaunchGuard(tmp_path / "guard") as guard:
        for provider in ("codex", "claude", "antigravity"):
            route = {"provider": provider, "profile": "fixture"}
            argv = dry_run._route_argv(tmp_path, route, {"task_input": {"task_authority": "read_only"}}, "static")
            assert argv[0] == guard.executable(provider, "fixture")
        assert len(guard.assert_clean()["routes"]) == 3


def test_sentinel_survives_process_killed_before_stdin_eof(tmp_path):
    import time
    guard = LaunchGuard(tmp_path / "guard")
    process = subprocess.Popen([guard.executable("codex", "fixture")], stdin=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 5
        while not list(guard.events.iterdir()) and time.monotonic() < deadline:
            time.sleep(0.01)
        assert list(guard.events.iterdir())
    finally:
        process.kill()
        process.wait(timeout=5)
        process.stdin.close()
    with pytest.raises(ProviderInvocationError, match="sentinel"):
        guard.assert_clean()


def test_dry_run_refuses_real_tripwire_attempt(tmp_path, monkeypatch):
    from testing.h_eval.provider_free import ACTIVE_GUARD
    def attempt(*args, **kwargs):
        guard = ACTIVE_GUARD.get()
        subprocess.run([guard.executable("claude", "fixture")], input=b"task", check=False)
        return {"status": "complete"}
    monkeypatch.setattr(dry_run, "_dry_run_all", attempt)
    with pytest.raises(ProviderInvocationError, match="sentinel"):
        from pathlib import Path
        dry_run.dry_run_all(Path(__file__).resolve().parents[3], tmp_path / "result")
    assert list((tmp_path / "result/provider-guard/sentinels").iterdir())
