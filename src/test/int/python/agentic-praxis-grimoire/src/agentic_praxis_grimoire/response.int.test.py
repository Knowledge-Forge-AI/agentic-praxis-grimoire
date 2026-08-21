"""Real-process filesystem contracts for APGR response allocation."""

from __future__ import annotations

import os
from pathlib import Path
import stat
import subprocess
import sys

import pytest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
SOURCE_ROOT = REPOSITORY_ROOT / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from agentic_praxis_grimoire import response  # noqa: E402


def _child_environment() -> dict[str, str]:
    environment = os.environ.copy()
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = os.pathsep.join(
        value for value in (str(SOURCE_ROOT), existing) if value
    )
    return environment


def _run_child(
    outbox: Path, project: str, phase: str, body: bytes
) -> subprocess.Popen[bytes]:
    script = (
        "from pathlib import Path; "
        "import sys; "
        "from agentic_praxis_grimoire.response import capture_response; "
        "path = capture_response(outbox_root=Path(sys.argv[1]), project=sys.argv[2], "
        "phase=sys.argv[3], body=bytes.fromhex(sys.argv[4])); "
        "print(path, flush=True)"
    )
    return subprocess.Popen(
        [
            sys.executable,
            "-c",
            script,
            os.fspath(outbox),
            project,
            phase,
            body.hex(),
        ],
        cwd=REPOSITORY_ROOT,
        env=_child_environment(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def test_concurrent_processes_receive_unique_monotonic_numbers_and_exact_bodies(
    tmp_path: Path,
) -> None:
    outbox = tmp_path / "outbox"
    project = "synthetic-project"
    phase = "APG82"
    bodies = [f"response-{index:02d}\n".encode() for index in range(24)]
    processes = [_run_child(outbox, project, phase, body) for body in bodies]

    results = [process.communicate(timeout=20) for process in processes]
    for result in results:
        stdout, stderr = result
        assert stdout.strip(), stderr.decode()

    paths = [Path(stdout.decode().strip()) for stdout, _stderr in results]
    assert len(set(paths)) == len(bodies)
    assert sorted(path.name for path in paths) == [
        f"{phase}.{number:03d}.response.md" for number in range(1, len(bodies) + 1)
    ]
    assert {path.read_bytes() for path in paths} == set(bodies)

    phase_dir = outbox / project / phase
    assert stat.S_IMODE((phase_dir / ".response.lock").stat().st_mode) == 0o600
    assert not tuple(phase_dir.glob("*.reservation.*"))


def test_process_death_releases_phase_lock_for_recovery(tmp_path: Path) -> None:
    outbox = tmp_path / "outbox"
    script = (
        "from pathlib import Path; import sys, time; "
        "from agentic_praxis_grimoire.response import phase_directory, _phase_lock; "
        "directory = phase_directory(Path(sys.argv[1]), 'project', 'APG82'); "
        "context = _phase_lock(directory); context.__enter__(); "
        "print('locked', flush=True); time.sleep(60)"
    )
    holder = subprocess.Popen(
        [sys.executable, "-c", script, os.fspath(outbox)],
        cwd=REPOSITORY_ROOT,
        env=_child_environment(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert holder.stdout is not None
    assert holder.stdout.readline() == b"locked\n"
    holder.kill()
    holder.wait(timeout=10)

    recovered = _run_child(outbox, "project", "APG82", b"after-kill\n")
    stdout, stderr = recovered.communicate(timeout=20)
    assert recovered.returncode == 0, stderr.decode()
    created = Path(stdout.decode().strip())
    assert created.read_bytes() == b"after-kill\n"


def test_capture_retries_one_observed_phase_lock_contention(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0
    flock = response.fcntl.flock

    def contend_once(descriptor: int, operation: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise BlockingIOError
        flock(descriptor, operation)

    monkeypatch.setattr(response.fcntl, "flock", contend_once)
    monkeypatch.setattr(response.time, "sleep", lambda _seconds: None)

    created = response.capture_response(
        outbox_root=tmp_path / "outbox",
        project="project",
        phase="APG89",
        body=b"after-contention\n",
    )

    assert calls == 2
    assert created.read_bytes() == b"after-contention\n"


def test_next_capture_cleans_dead_process_body_and_rejects_relative_root(
    tmp_path: Path,
) -> None:
    outbox = tmp_path / "outbox"
    phase_dir = response.phase_directory(outbox, "project", "APG82")
    orphan = phase_dir / ".response-write.dead-process.tmp"
    orphan.write_bytes(b"partial sensitive body")
    orphan.chmod(0o600)

    created = response.capture_response(
        outbox_root=outbox,
        project="project",
        phase="APG82",
        body=b"complete\n",
    )

    assert created.read_bytes() == b"complete\n"
    assert not orphan.exists()
    with pytest.raises(response.ResponseUsageError, match="absolute"):
        response.capture_response(
            outbox_root="relative-outbox",
            project="project",
            phase="APG82",
            body=b"refused",
        )
