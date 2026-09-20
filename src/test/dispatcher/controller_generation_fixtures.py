from __future__ import annotations

from collections.abc import Callable
import importlib.util
import inspect as inspect
import json
import os
from pathlib import Path
import shutil
import stat as stat
import subprocess
import sys
import time
from typing import Any
import uuid

import pytest

if str(Path(__file__).resolve().parents[3] / "libexec") not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "libexec"))

import controller_generation as controller_generation
import controller_generation_bootstrap as controller_generation_bootstrap
import controller_generation_process as controller_generation_process
import controller_generation_store as controller_generation_store

ROOT = Path(__file__).resolve().parents[3]
CANDIDATE_LIBEXEC_DIRS = [ROOT / "libexec"]
TOOL = ROOT / "tools/guarded_active_checkout_update.py"
MODULE_SPEC = importlib.util.spec_from_file_location("guarded_active_checkout_update", TOOL)
if MODULE_SPEC is None or MODULE_SPEC.loader is None:
    raise RuntimeError("unable to import guarded active checkout update tool")
GUARDED = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(GUARDED)

FIXTURE_CLI_CODE = """#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys
import time

_LIBEXEC_DIR = str(Path(__file__).resolve().parents[1])
if _LIBEXEC_DIR not in sys.path:
    sys.path.insert(0, _LIBEXEC_DIR)

from controller_generation_bootstrap import enter

root = Path(__file__).resolve().parents[2]
enter(root)

if "--help" in sys.argv:
    sys.stdout.write("agent-phase-dispatch help\\n")
    sys.exit(0)

ready_gate: Path | None = None
release_gate: Path | None = None
output_file: Path | None = None

for idx, arg in enumerate(sys.argv):
    if arg == "--ready-gate" and idx + 1 < len(sys.argv):
        ready_gate = Path(sys.argv[idx + 1])
    elif arg == "--release-gate" and idx + 1 < len(sys.argv):
        release_gate = Path(sys.argv[idx + 1])
    elif arg == "--output-file" and idx + 1 < len(sys.argv):
        output_file = Path(sys.argv[idx + 1])

if ready_gate is not None:
    ready_gate.write_text(f"ready:{os.getpid()}\\n", encoding="utf-8")

if release_gate is not None:
    deadline = time.time() + 25.0
    while not release_gate.exists() and time.time() < deadline:
        time.sleep(0.02)

helper_path = Path(__file__).resolve().parents[1] / "helper.py"
spec = importlib.util.spec_from_file_location("fixture_helper", helper_path)
if spec is not None and spec.loader is not None:
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    data = helper.get_bytes()
    import late_import
    assert late_import.get_bytes() == data
    import subprocess
    later = subprocess.check_output([sys.executable, "-B", "-c",
        "import runpy,sys; sys.stdout.buffer.write(runpy.run_path(sys.argv[1])['get_bytes']())",
        str(helper_path)])
    assert later == data
else:
    data = b"fallback-helper-bytes\\n"

if output_file is not None:
    output_file.write_bytes(data)
else:
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()
"""

FIXTURE_DISPATCH_CODE = """#!/bin/sh
if [ "$1" = "--help" ]; then
    echo "agent-phase-dispatch help"
    exit 0
fi
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
if [ "$1" = "dispatch" ] || [ "$1" = "finalize" ]; then
    exec python3 -B "$REPO_ROOT/libexec/agent_phase/cli.py" "$@"
else
    exec python3 -B "$REPO_ROOT/libexec/agent_phase/cli.py" dispatch "$@"
fi
"""


def find_core_module(filename: str) -> Path:
    for d in CANDIDATE_LIBEXEC_DIRS:
        candidate = d / filename
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Cannot find core module {filename}")


def git(cwd: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check:
        assert completed.returncode == 0, f"git command failed ({completed.returncode}): {completed.stderr}"
    return completed


def _write_executable(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def safe_rmtree(path: Path) -> None:
    if not path.exists():
        return
    for root, dirs, files in os.walk(path, topdown=True):
        for d in dirs:
            try:
                os.chmod(os.path.join(root, d), 0o700)
            except OSError:
                pass
        for f in files:
            try:
                os.chmod(os.path.join(root, f), 0o600)
            except OSError:
                pass
    try:
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass


def load_evidence(directory: Path) -> dict[str, Any]:
    return json.loads((directory / "guarded-active-checkout-update.json").read_text(encoding="utf-8"))


def make_process_reader(pids: set[int]) -> Callable[[], bytes]:
    def reader() -> bytes:
        completed = subprocess.run(
            ["ps", "-ww", "-axo", "pid=,ppid=,command="],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        lines = []
        for line in completed.stdout.splitlines():
            parts = line.strip().split(None, 2)
            if parts and parts[0].isdigit() and int(parts[0]) in pids:
                lines.append(line)
        return b"\n".join(lines) + (b"\n" if lines else b"")
    return reader


class ProcessManager:
    """Bounded, owned process supervisor ensuring cleanup of test child processes only."""

    def __init__(self) -> None:
        self.processes: list[subprocess.Popen] = []

    def spawn(self, *args: Any, **kwargs: Any) -> subprocess.Popen:
        proc = subprocess.Popen(*args, **kwargs)
        self.processes.append(proc)
        return proc

    def cleanup(self) -> None:
        for proc in self.processes:
            if proc.poll() is None:
                try:
                    proc.terminate()
                except ProcessLookupError:
                    pass
        deadline = time.time() + 2.0
        for proc in self.processes:
            if proc.poll() is None:
                try:
                    proc.wait(timeout=max(0.1, deadline - time.time()))
                except subprocess.TimeoutExpired:
                    try:
                        proc.kill()
                        proc.wait(timeout=1.0)
                    except (ProcessLookupError, subprocess.TimeoutExpired):
                        pass


def make_cutover_fixture(scratch_dir: Path) -> dict[str, Any]:
    remote = scratch_dir / "remote.git"
    seed = scratch_dir / "seed"
    active = scratch_dir / "active"
    store = scratch_dir / "store"
    evidence = scratch_dir / "evidence"
    request = scratch_dir / "smoke-request.json"

    store.mkdir(parents=True, exist_ok=True, mode=0o700)
    evidence.mkdir(parents=True, exist_ok=True, mode=0o700)
    request.write_text('{"phase":"smoke"}\n', encoding="utf-8")

    git(scratch_dir, "init", "--bare", "-q", remote)
    seed.mkdir(mode=0o700)
    git(seed, "init", "-q", "-b", "main")
    git(seed, "config", "user.email", "test@example.invalid")
    git(seed, "config", "user.name", "Cutover Test")

    seed_libexec = seed / "libexec"
    seed_libexec.mkdir(parents=True, exist_ok=True, mode=0o700)
    for mod_name in (
        "controller_generation.py",
        "controller_generation_bootstrap.py",
        "controller_generation_store.py",
        "controller_generation_process.py",
    ):
        src = find_core_module(mod_name)
        dst = seed_libexec / mod_name
        dst.write_bytes(src.read_bytes())
        dst.chmod(0o600)

    seed_agent_phase = seed_libexec / "agent_phase"
    seed_agent_phase.mkdir(parents=True, exist_ok=True, mode=0o700)
    _write_executable(seed_agent_phase / "cli.py", FIXTURE_CLI_CODE)

    (seed_libexec / "helper.py").write_text(
        "def get_bytes() -> bytes:\n    return b'generation-v1-bytes\\n'\n", encoding="utf-8"
    )
    (seed_libexec / "late_import.py").write_bytes((seed_libexec / "helper.py").read_bytes())

    _write_executable(seed / "bin/agent-phase-dispatch", FIXTURE_DISPATCH_CODE)
    _write_executable(seed / "bin/agent-phase-resolve", "#!/bin/sh\nexit 0\n")
    _write_executable(
        seed / "tools/add_dispatcher_roster_operator_directions.py",
        "#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n",
    )

    git(seed, "add", ".")
    git(seed, "commit", "-qm", "base-gen1")
    git(seed, "remote", "add", "origin", os.fspath(remote))
    git(seed, "push", "-qu", "origin", "main")

    git(scratch_dir, "clone", "-q", "-b", "main", os.fspath(remote), os.fspath(active))
    git(active, "config", "user.email", "test@example.invalid")
    git(active, "config", "user.name", "Cutover Test")

    return {
        "remote": remote,
        "seed": seed,
        "active": active,
        "store": store,
        "evidence": evidence,
        "request": request,
        "base_commit": git(active, "rev-parse", "HEAD").stdout.strip(),
    }


def publish_remote_change(
    layout: dict[str, Any],
    helper_bytes: bytes = b"generation-v2-bytes\n",
    extra_files: dict[str, str | bytes] | None = None,
) -> str:
    seed = layout["seed"]
    (seed / "libexec/helper.py").write_bytes(
        f"def get_bytes() -> bytes:\n    return {repr(helper_bytes)}\n".encode("utf-8")
    )
    (seed / "libexec/late_import.py").write_bytes((seed / "libexec/helper.py").read_bytes())
    if extra_files:
        for rel_path, content in extra_files.items():
            target = seed / rel_path
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if isinstance(content, str):
                target.write_text(content, encoding="utf-8")
            else:
                target.write_bytes(content)
            if rel_path.startswith("bin/") or rel_path.endswith(".py"):
                target.chmod(0o755)
    git(seed, "add", ".")
    git(seed, "commit", "-qm", "remote change")
    git(seed, "push", "-q", "origin", "main")
    return git(seed, "rev-parse", "HEAD").stdout.strip()


def start_fixture_dispatcher(
    layout: dict[str, Any],
    *,
    extra_args: list[str] | None = None,
    wait_ready: bool = True,
    ready_timeout: float = 12.0,
    bootstrap: bool = False,
    operation: str = "dispatch",
) -> tuple[subprocess.Popen, Path, Path, Path]:
    scratch_dir = layout["scratch_dir"]
    proc_id = uuid.uuid4().hex[:8]
    ready_gate = scratch_dir / f"ready_{proc_id}.gate"
    release_gate = scratch_dir / f"release_{proc_id}.gate"
    output_file = scratch_dir / f"output_{proc_id}.bin"

    env = os.environ.copy()
    env["AGENT_CENTRAL_GENERATION_STORE"] = str(layout["store"])
    env["AGENT_CENTRAL_ACTIVE_ROOT"] = str(layout["active"])
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    cmd = [
        sys.executable,
        "-B",
        str(layout["active"] / ("libexec/controller_generation_bootstrap.py" if bootstrap else "libexec/agent_phase/cli.py")),
        operation,
        "--ready-gate",
        str(ready_gate),
        "--release-gate",
        str(release_gate),
        "--output-file",
        str(output_file),
    ]
    if extra_args:
        cmd.extend(extra_args)

    proc = layout["proc_mgr"].spawn(
        cmd,
        cwd=str(layout["active"]),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if wait_ready:
        deadline = time.time() + ready_timeout
        while not ready_gate.exists() and time.time() < deadline:
            if proc.poll() is not None:
                stderr = proc.stderr.read().decode("utf-8", "replace") if proc.stderr else ""
                raise RuntimeError(
                    f"Dispatcher process {proc.pid} exited prematurely with {proc.returncode}: {stderr}"
                )
            time.sleep(0.05)
        if not ready_gate.exists():
            raise TimeoutError(f"Dispatcher process {proc.pid} failed to signal ready within {ready_timeout}s")

    return proc, ready_gate, release_gate, output_file


@pytest.fixture
def cutover_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Any:
    scratch_dir = tmp_path.resolve() / "process-tests"
    scratch_dir.mkdir(mode=0o700)
    proc_mgr = ProcessManager()

    layout = make_cutover_fixture(scratch_dir)
    monkeypatch.setenv("AGENT_CENTRAL_GENERATION_STORE", str(layout["store"]))
    monkeypatch.setenv("AGENT_CENTRAL_ACTIVE_ROOT", str(layout["active"]))
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")

    layout["proc_mgr"] = proc_mgr
    layout["scratch_dir"] = scratch_dir

    try:
        yield layout
    finally:
        proc_mgr.cleanup()
        safe_rmtree(scratch_dir)
