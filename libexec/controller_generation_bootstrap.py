"""Small pre-import boundary: pin Git code, then exec before loading dispatcher code."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from controller_generation import (
    LEASE_ENV, STARTUP_LOCK_TIMEOUT, activate, create_lease, read_record, observe_development,
)
from controller_generation_store import coordinate, materialize, resolve_controller_dir, validate_generation


def _active(root: Path) -> bool:
    configured = os.environ.get("AGENT_CENTRAL_ACTIVE_ROOT")
    candidates = ([Path(configured).expanduser()] if configured else [
        Path.home() / ".local/nix-darwin/agent-central_dinas",
        Path.home() / "ai/agent-central",
    ])
    return any(path.resolve() == root for path in candidates)


def _resume_commit(arguments: list[str], root: Path) -> str | None:
    for index, argument in enumerate(arguments):
        if argument in {"--resume", "--run"} and index + 1 < len(arguments):
            prior = Path(arguments[index + 1])
        elif argument.startswith(("--resume=", "--run=")):
            prior = Path(argument.split("=", 1)[1])
        else:
            continue
        # Historical state is input evidence, never a lease or a command path.
        import json
        state = json.loads((prior / "state.json").read_bytes())
        generation = state.get("controller_generation")
        if generation and generation.get("safety_established") is True:
            if generation.get("controller_root") != str(root):
                raise RuntimeError("resume controller identity differs")
            validate_generation(generation, resolve_controller_dir(root))
            return generation["commit"]
    return None


def enter(root: Path) -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in {"dispatch", "finalize", "ownership"} or "--help" in sys.argv[2:]:
        return
    path = os.environ.get(LEASE_ENV)
    if path:
        record = read_record(Path(path))
        if record.get("pid") == os.getpid():
            activate(root, Path(path))
            return
        os.environ.pop(LEASE_ENV, None)  # A child cannot inherit its parent's identity.
    with coordinate(root, timeout=STARTUP_LOCK_TIMEOUT) as store:
        dirty = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--untracked-files=normal"],
                               check=True, capture_output=True).stdout
        if dirty and not _active(root):
            # Source development retains worktree execution. Such a process has
            # no safety lease and still blocks updates; it cannot impersonate a
            # deployed Git generation.
            observe_development(root)
            return
        generation = materialize(root, store, _resume_commit(sys.argv[2:], root))
        pinned = Path(generation["generation_root"])
        if not (pinned / "libexec/controller_generation_bootstrap.py").is_file():
            raise RuntimeError("selected commit predates generation-safe startup")
        lease = create_lease(store, generation)
        environment = os.environ.copy()
        environment[LEASE_ENV] = str(lease)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        # A source checkout on ambient PYTHONPATH must never win a later import.
        environment.pop("PYTHONPATH", None)
        environment.pop("PYTHONHOME", None)
        # Put pinned helper commands first without moving credential homes.
        environment["PATH"] = str(Path(generation["generation_root"]) / "bin") + os.pathsep + environment.get("PATH", "")
        executable = Path(generation["generation_root"]) / (
            "libexec/agent_phase/ownership_cli.py"
            if sys.argv[1] == "ownership"
            else "libexec/agent_phase/cli.py"
        )
    os.execve(sys.executable, [sys.executable, "-B", str(executable), *sys.argv[1:]], environment)


if __name__ == "__main__":
    controller = Path(__file__).resolve().parents[1]
    try:
        enter(controller)
        # Help and dirty development preserve their ordinary worktree behavior.
        executable = controller / (
            "libexec/agent_phase/ownership_cli.py"
            if sys.argv[1] == "ownership"
            else "libexec/agent_phase/cli.py"
        )
        os.execv(sys.executable, [sys.executable, "-B", str(executable), *sys.argv[1:]])
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        sys.exit(f"agent-phase-dispatch: generation binding failed ({type(error).__name__})")
