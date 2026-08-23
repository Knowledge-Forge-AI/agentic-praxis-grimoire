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


def test_real_go_response_bridge_preserves_exact_bytes_and_modes(tmp_path: Path) -> None:
    outbox = tmp_path / "outbox"
    body = b"# exact\n\x00\xff\n"
    process = _run_child(outbox, "synthetic-project", "APG100", body)
    stdout, stderr = process.communicate(timeout=60)
    assert process.returncode == 0, stderr.decode()
    created = Path(stdout.decode().strip())
    assert created.read_bytes() == body
    assert stat.S_IMODE(created.stat().st_mode) == 0o600
    assert stat.S_IMODE(created.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(created.parent.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE((created.parent / response.LOCK_NAME).stat().st_mode) == 0o600


def test_real_go_response_bridge_concurrent_allocations_are_unique_and_exact(
    tmp_path: Path,
) -> None:
    outbox = tmp_path / "outbox"
    project = "synthetic-project"
    phase = "APG100"
    bodies = [f"response-{index:02d}\n".encode() for index in range(12)]
    processes = [_run_child(outbox, project, phase, body) for body in bodies]

    results = [process.communicate(timeout=60) for process in processes]
    for process, (_stdout, stderr) in zip(processes, results):
        assert process.returncode == 0, stderr.decode()
    paths = [Path(stdout.decode().strip()) for stdout, _stderr in results]
    assert len(set(paths)) == len(bodies)
    assert sorted(path.name for path in paths) == [
        f"{phase}.{number:03d}.response.md" for number in range(1, len(bodies) + 1)
    ]
    assert {path.read_bytes() for path in paths} == set(bodies)
    phase_dir = outbox / project / phase
    assert stat.S_IMODE((phase_dir / response.LOCK_NAME).stat().st_mode) == 0o600
    assert not tuple(phase_dir.glob("*.reservation.*"))


def test_real_go_response_bridge_file_alias_uses_same_capture_owner(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_bytes(b"file input\x00\xff\n")
    outbox = tmp_path / "outbox"
    script = (
        "from pathlib import Path; "
        "import sys; "
        "from agentic_praxis_grimoire.response import main; "
        "raise SystemExit(main({'project': 'project', 'outbox_root': sys.argv[1]}, "
        "['record', '--phase', 'APG100', '--file', sys.argv[2]]))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script, os.fspath(outbox), os.fspath(source)],
        cwd=REPOSITORY_ROOT,
        env=_child_environment(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr.decode()
    assert Path(completed.stdout.decode().strip()).read_bytes() == source.read_bytes()
