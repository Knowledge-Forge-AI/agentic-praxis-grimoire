"""Small pre-import boundary: pin Git code, then exec before loading dispatcher code."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from controller_generation import (
    LEASE_ENV, STARTUP_LOCK_TIMEOUT, activate, create_lease, read_record, observe_development,
    INSTALLED_MARKER, installed_runtime, observe_installed, verify_installed_digest,
)
from controller_generation_store import coordinate, materialize, resolve_controller_dir, validate_generation


def _active(root: Path) -> bool:
    configured = None
    if "APGR_ACTIVE_ROOT" in os.environ:
        val = os.environ["APGR_ACTIVE_ROOT"]
        if val:
            configured = val
    elif "AGENT_CENTRAL_ACTIVE_ROOT" in os.environ:
        val = os.environ["AGENT_CENTRAL_ACTIVE_ROOT"]
        if val:
            configured = val

    candidates = ([Path(configured).expanduser()] if configured else [
        Path.home() / ".local/nix-darwin/agentic-praxis-grimoire_dinas",
    ])
    return any(path.resolve() == root for path in candidates)


def _extract_apgr_home(arguments: list[str]) -> Path | None:
    for index, argument in enumerate(arguments):
        if argument == "--apgr-home":
            if index + 1 >= len(arguments):
                raise ValueError("--apgr-home requires an argument")
            val = arguments[index + 1]
        elif argument.startswith("--apgr-home="):
            val = argument.split("=", 1)[1]
        else:
            continue
        if not val or any(ord(c) < 32 or ord(c) == 127 for c in val):
            raise ValueError("--apgr-home contains invalid or control characters")
        p = Path(val).expanduser()
        if not p.is_absolute():
            raise ValueError("--apgr-home must be an absolute path")
        return p
    return None


def _prior_generations(arguments: list[str]) -> list[dict]:
    generations = []
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
        generation = state.get("controller_generation") if isinstance(state, dict) else None
        generations.append(generation if isinstance(generation, dict) else {})
    return generations


def _resume_commit(arguments: list[str], root: Path, apgr_home: Path | None = None) -> str | None:
    for generation in _prior_generations(arguments):
        if generation.get("safety_established") is True:
            if generation.get("controller_root") != str(root):
                raise RuntimeError("resume controller identity differs")
            ctrl_dir = resolve_controller_dir(
                root,
                apgr_home=apgr_home,
                lookup_only=True,
                commit=generation.get("commit"),
            )
            validate_generation(
                generation,
                ctrl_dir,
                apgr_home=apgr_home,
            )
            return generation["commit"]
    return None


def _enter_installed(root: Path, marker: dict) -> None:
    """Run a packaged immutable runtime in place: no Git, store or lease."""
    if any(item.get("safety_established") is True for item in _prior_generations(sys.argv[2:])):
        raise RuntimeError("installed runtime cannot resume a generation-pinned run")
    os.environ.pop(LEASE_ENV, None)  # A child cannot inherit its parent's identity.
    os.environ.pop("PYTHONPATH", None)
    os.environ.pop("PYTHONHOME", None)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    verify_installed_digest(root, marker)
    observe_installed(root, marker)


def enter(root: Path) -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in {"dispatch", "finalize", "ownership"} or "--help" in sys.argv[2:]:
        return
    apgr_home = _extract_apgr_home(sys.argv[1:])
    marker = installed_runtime(root)
    if marker is not None:
        _enter_installed(root, marker)
        return
    if os.path.lexists(root / INSTALLED_MARKER):
        raise RuntimeError(f"{INSTALLED_MARKER} is present but {root} is not a recognized "
                           "write-protected Nix store runtime; refusing checkout execution")
    path = os.environ.get(LEASE_ENV)
    if path:
        record = read_record(Path(path))
        if record.get("pid") == os.getpid():
            activate(root, Path(path))
            return
        os.environ.pop(LEASE_ENV, None)  # A child cannot inherit its parent's identity.
    # Validate and resolve historical resume commit BEFORE coordinate creates the new writable store
    resume_commit = _resume_commit(sys.argv[2:], root, apgr_home=apgr_home)
    with coordinate(root, apgr_home=apgr_home, timeout=STARTUP_LOCK_TIMEOUT) as store:
        dirty = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--untracked-files=normal"],
                               check=True, capture_output=True).stdout
        if dirty and not _active(root):
            # Source development retains worktree execution. Such a process has
            # no safety lease and still blocks updates; it cannot impersonate a
            # deployed Git generation.
            observe_development(root)
            return
        generation = materialize(root, store, resume_commit)
        pinned = Path(generation["generation_root"])
        if not (pinned / "libexec/controller_generation_bootstrap.py").is_file():
            raise RuntimeError("selected commit predates generation-safe startup")
        lease = create_lease(store, generation)
        environment = os.environ.copy()
        environment[LEASE_ENV] = str(lease)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        if apgr_home is not None:
            environment["APGR_HOME"] = str(apgr_home.resolve())
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
        # Help, dirty development and installed runtimes run in place.
        executable = controller / (
            "libexec/agent_phase/ownership_cli.py"
            if sys.argv[1] == "ownership"
            else "libexec/agent_phase/cli.py"
        )
        os.execv(sys.executable, [sys.executable, "-B", str(executable), *sys.argv[1:]])
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        sys.exit(f"agent-phase-dispatch: generation binding failed ({type(error).__name__})")
