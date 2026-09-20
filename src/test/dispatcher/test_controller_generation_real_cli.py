"""Qualify actual candidate CLI/modules from a disposable Git generation."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from controller_generation_store import coordinate, is_allowlisted, materialize

ROOT = Path(__file__).resolve().parents[3]


def candidate(root):
    root.mkdir()
    names = subprocess.check_output(["git", "-C", str(ROOT), "ls-files", "-z"], text=True).split("\0")
    names += subprocess.check_output(["git", "-C", str(ROOT), "ls-files", "--others", "--exclude-standard", "-z"], text=True).split("\0")
    for name in set(names):
        if name and is_allowlisted(name):
            source, target = ROOT / name, root / name
            assert source.is_file() and not source.is_symlink()
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    for args in (["init", "-q", "-b", "main"], ["config", "user.name", "Fixture"],
                 ["config", "user.email", "fixture@example.invalid"], ["add", "."],
                 ["commit", "-qm", "candidate"]):
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def test_actual_cli_smoke_and_pinned_immutable_review(tmp_path, monkeypatch):
    root = tmp_path / "controller"
    candidate(root)
    monkeypatch.setenv("AGENT_CENTRAL_GENERATION_STORE", str(tmp_path / "store"))
    monkeypatch.setenv("AGENT_CENTRAL_ACTIVE_ROOT", str(root))
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    sentinels = tmp_path / "provider-sentinels"
    sentinels.mkdir()
    marker = tmp_path / "provider-invoked"
    monkeypatch.setenv("PROVIDER_SENTINEL_MARKER", str(marker))
    for name in ("codex", "claude", "agy", "gemini"):
        command = sentinels / name
        command.write_text('#!/bin/sh\nprintf invoked >> "$PROVIDER_SENTINEL_MARKER"\nexit 97\n')
        command.chmod(0o700)
    monkeypatch.setenv("PATH", str(sentinels) + os.pathsep + os.environ["PATH"])
    # A negative control proves the shadow executable really records invocation.
    assert subprocess.run(["codex"], capture_output=True).returncode == 97
    assert marker.read_text() == "invoked"
    marker.unlink()
    request = tmp_path / "SMOKE.json"
    request.write_text(json.dumps({"schema": "agent-phase-request-v1", "phase_type": "implementation_testing",
                                  "execution_mode": "codex_only", "prompt": "Provider-free fixture"}))
    commands = [[str(root / "bin/agent-phase-dispatch"), "--help"],
                [str(root / "bin/agent-phase-resolve"), str(request), "--lifecycle", "work-reviewed", "--finalization", "checkpoint"],
                [str(root / "bin/agent-phase-dispatch"), str(request), "--dry-run", "--lifecycle", "work-reviewed", "--finalization", "checkpoint"]]
    for command in commands:
        result = subprocess.run(command, cwd=root, capture_output=True, timeout=60)
        assert result.returncode == 0, result.stderr.decode()
    with coordinate(root) as store:
        record = materialize(root, store)
    pinned = Path(record["generation_root"])
    smoke = subprocess.run([sys.executable, str(pinned / "tools/add_dispatcher_roster_operator_directions.py"),
                            "--root", str(pinned), "--check"], capture_output=True, timeout=30)
    assert smoke.returncode == 0, smoke.stderr.decode()
    for command in ("status", "gc"):
        result = subprocess.run([str(root / "bin/agent-controller-generation"), command,
                                 "--controller-root", str(root)], capture_output=True, timeout=30)
        assert result.returncode == 0, result.stderr.decode()
    # Exercise the real updater's smoke entrypoint against the materialized CLI.
    from controller_generation_fixtures import GUARDED
    GUARDED._smoke(pinned, request)
    assert not marker.exists(), "provider invoked by help/resolve/dry-run/status/GC/smoke"
    record_file = tmp_path / "generation.json"
    record_file.write_text(json.dumps(record))
    # Test-only provider injection exercises the real pinned lifecycle; it is
    # not an independent review and launches no vendor/model process.
    driver = r'''
import json, os, sys
from pathlib import Path
record = json.loads(Path(sys.argv[1]).read_text())
pinned = Path(record['generation_root'])
sys.path[:0] = [str(pinned / 'libexec'), sys.argv[2]]
import agent_phase.dispatch as product
assert Path(product.__file__).is_relative_to(pinned)
import test_agent_phase_lifecycle_dispatch as fixture
from controller_generation import create_lease, activate, LEASE_ENV
from controller_generation_store import coordinate
with coordinate(Path(record['controller_root'])) as store:
    lease = create_lease(store, record)
os.environ[LEASE_ENV] = str(lease)
activate(pinned, lease)
fixture.ROOT = pinned
base = Path(sys.argv[3]); workspace = base / 'workspace'; workspace.mkdir()
fixture.git(workspace, 'init', '-b', 'main')
fixture.git(workspace, 'config', 'user.name', 'Fixture')
fixture.git(workspace, 'config', 'user.email', 'fixture@example.invalid')
(workspace / 'file.txt').write_text('original')
fixture.git(workspace, 'add', '.'); fixture.git(workspace, 'commit', '-m', 'base')
def change(stage, cwd):
    if stage == 'work_review': (cwd / 'file.txt').write_text('concurrent mutation')
runner = fixture.LifecycleRunner(change)
try:
    fixture.dispatcher(workspace, base, runner).dispatch('PINNED', fixture.REQUEST, 'work-reviewed', 'checkpoint')
except product.DispatchError as error:
    assert error.code == 'READ_ONLY_STAGE_MUTATED_CANDIDATE'
else:
    raise AssertionError('pinned review incorrectly accepted drift')
state = json.loads((fixture.only_run(base / 'runs') / 'state.json').read_text())
assert state['controller_generation']['commit'] == record['commit']
assert state['controller_generation']['safety_established'] is True
assert state['checkpoints_completed'] == [] and not state.get('commit')
assert [call['stage'] for call in runner.calls] == ['produce', 'work_review']
'''
    result = subprocess.run([sys.executable, "-B", "-c", driver, str(record_file), str(ROOT / "tests"), str(tmp_path)],
                            capture_output=True, timeout=90)
    assert result.returncode == 0, result.stderr.decode()
    assert not marker.exists(), "test-only lifecycle injection escaped to a provider"
