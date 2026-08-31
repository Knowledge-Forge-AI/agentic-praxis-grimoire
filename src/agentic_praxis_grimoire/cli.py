"""Canonical APGR command routing and maintained compatibility adapters."""

from __future__ import annotations

from contextlib import contextmanager
import importlib
import os
from pathlib import Path
import subprocess
import sys
from typing import Callable, Iterator, Sequence

from .version import version


COMMAND = "apgr"
FAMILIES = (
    "build-info",
    "check",
    "skills",
    "footprint",
    "test",
    "env",
    "analyze",
    "report",
    "response",
    "release",
)
_ENV_STORAGE_COMMANDS = frozenset({"snapshot", "show", "resolve", "run"})
HELP = """usage: apgr [global-options] <command> ...

Agentic Praxis Grimoire command line interface.

global options:
  --help                 show this help
  --version              show the APGR version
  --apgr-home PATH       override APGR_HOME for report/response/environment configuration
  --project-root PATH    select an APG Git worktree
  --outbox-root PATH     override configured report/response outbox root
  --project NAME         explicit report/response project identity

commands:
  build-info             show the packaged Go runtime identity
  check                  repository policy checks
  skills                 skill discovery, context, and projection commands
  footprint              context-footprint measurement, comparison, and projection commands
  test                   configured repository test runner
  env                    portable environment profile and snapshot commands
  analyze                read-only structural hotspot analysis
  report                 terminal Git and operational report publication;
                         a new primary type supersedes the prior current primary
  response               immutable numbered response capture
  release                repository release maintenance
"""


class CliError(ValueError):
    """A bounded APGR invocation error."""


@contextmanager
def _working_directory(path: Path) -> Iterator[None]:
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def discover_repository(start: Path) -> Path | None:
    """Return the containing Git worktree, or None without Git authority."""

    completed = subprocess.run(
        ["git", "-C", os.fspath(start), "rev-parse", "--show-toplevel"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0", "GIT_NO_REPLACE_OBJECTS": "1"},
    )
    if completed.returncode != 0:
        return None
    candidate = Path(completed.stdout.rstrip("\n"))
    try:
        return candidate.resolve(strict=True)
    except OSError:
        return None


def _load(repository_root: Path, module_name: str):
    helper_root = repository_root / "libexec"
    relative = Path(*module_name.split("."))
    module_path = helper_root / relative.with_suffix(".py")
    package_path = helper_root / relative / "__init__.py"
    if not module_path.is_file() and not package_path.is_file():
        raise CliError("Git worktree is not an Agentic Praxis Grimoire repository")
    helper = os.fspath(helper_root)
    if helper not in sys.path:
        sys.path.insert(0, helper)
    try:
        return importlib.import_module(module_name)
    except (ImportError, ModuleNotFoundError) as error:
        raise CliError("APGR repository maintenance owner could not be loaded") from error


def legacy_main(
    command: str,
    arguments: Sequence[str] | None = None,
    repository_root: Path | None = None,
) -> int:
    """Invoke one maintained historical command in-process."""

    values = list(arguments or [])
    report_commands = {
        "git-show-report",
        "git-diff-report",
        "append-operational-report",
    }
    root = repository_root or discover_repository(Path.cwd())
    if root is None:
        if command in report_commands:
            print(f"{command}: not inside a git repository", file=sys.stderr)
            return 1
        raise CliError(f"{command} requires an Agentic Praxis Grimoire repository")
    if command in report_commands:
        from . import go_bridge

        try:
            return go_bridge.run(
                go_bridge.legacy_arguments(command, root, values),
                repository_root=root,
            )
        except go_bridge.GoBridgeError as error:
            print(f"{command}: {error}", file=sys.stderr)
            return 1
    owners: dict[str, tuple[str, str]] = {
        "apg-check-change-size": ("change_size.cli", "run"),
        "apg-check-phase-commit-message": ("apg_phase_commit_message", "main"),
        "apg-check-record-identity": ("apg_record_identity", "main"),
        "apg-check-skill-library": ("apg_skill_library_check", "main"),
        "apg-build-python-release-bundle": ("apg_python_publication", "main"),
        "apg-normalize-python-sdist": ("apg_python_distribution", "main"),
        "apg-project-skills": ("apg_project_skills_commands", "main"),
        "apg-public-release": ("apg_public_release", "main"),
        "apg-test": ("apg_test", "main"),
        "apg-user-skills": ("apg_user_skills", "main"),
        "install-global-skills": ("install_global_skills", "main"),
        "flatten-skill-symlinks": ("flatten_skill_symlinks", "main"),
    }
    try:
        module_name, function_name = owners[command]
    except KeyError as error:
        raise ValueError(f"unknown compatibility command: {command}") from error
    function: Callable[[Sequence[str] | None], int] = getattr(
        _load(root, module_name), function_name
    )
    return function(values)


def compatibility_main(command: str, repository_root: Path) -> int:
    """Entry used by checkout-local legacy wrapper scripts."""

    return legacy_main(command, sys.argv[1:], repository_root)


def _global_options(arguments: list[str]) -> tuple[dict[str, str], list[str]]:
    options: dict[str, str] = {}
    while arguments and arguments[0].startswith("--"):
        option = arguments.pop(0)
        if option in {"--help", "--version"}:
            options[option[2:].replace("-", "_")] = "1"
            continue
        key_by_option = {
            "--apgr-home": "apgr_home",
            "--project-root": "project_root",
            "--outbox-root": "outbox_root",
            "--project": "project",
        }
        key = key_by_option.get(option)
        if key is None:
            raise CliError(f"unknown global option: {option}")
        if not arguments:
            raise CliError(f"{option} requires a value")
        if key in options:
            raise CliError(f"{option} may be specified only once")
        options[key] = arguments.pop(0)
    return options, arguments


def _repository_root(options: dict[str, str]) -> Path | None:
    explicit = options.get("project_root")
    if explicit is not None:
        try:
            candidate = Path(explicit).expanduser().resolve(strict=True)
        except (OSError, RuntimeError, ValueError) as error:
            raise CliError(
                "--project-root must name the exact Git worktree root"
            ) from error
        discovered = discover_repository(candidate)
        if discovered != candidate:
            raise CliError("--project-root must name the exact Git worktree root")
        return candidate
    return discover_repository(Path.cwd())


def _repository_route(
    command: str,
    tail: list[str],
    options: dict[str, str],
) -> int:
    root = _repository_root(options)
    if root is None:
        raise CliError("command requires an Agentic Praxis Grimoire repository")
    with _working_directory(root):
        return legacy_main(command, tail, root)


def _environment_has_storage_root(arguments: Sequence[str]) -> bool:
    """Return whether env-owned options already contain a storage root."""

    for argument in arguments:
        if argument == "--":
            return False
        if argument == "--storage-root":
            return True
    return False


def _environment_route(options: dict[str, str], arguments: list[str]) -> int:
    """Delegate environment commands to Go with an explicit storage root."""

    if not arguments:
        raise CliError("env requires a command")

    values = list(arguments)
    if values[0] in _ENV_STORAGE_COMMANDS and not _environment_has_storage_root(values):
        from .paths import PathContractError, resolve_global_home

        try:
            storage_root = resolve_global_home(options.get("apgr_home"))
        except PathContractError as error:
            raise CliError("environment storage root is invalid") from error
        values[1:1] = ["--storage-root", os.fspath(storage_root)]

    from . import go_bridge

    try:
        return go_bridge.run(["env", *values], repository_root=None)
    except go_bridge.GoBridgeError:
        # Do not surface source-checkout/compiler details at the environment
        # boundary: the Go owner is responsible for values-safe diagnostics.
        print("apgr env: Go environment bridge unavailable", file=sys.stderr)
        return 1


def _dispatch_analyze(options: dict[str, str], arguments: list[str]) -> int:
    if not arguments or arguments[0] != "hotspots":
        raise CliError("analyze requires the hotspots command")
    if any(key in options for key in ("apgr_home", "outbox_root", "project")):
        raise CliError("analyze accepts only --project-root from Python global options")
    explicit = options.get("project_root")
    if explicit is None:
        try:
            root = Path.cwd().resolve(strict=True)
        except (OSError, RuntimeError, ValueError) as error:
            raise CliError("analysis root is unavailable") from error
        if not root.is_dir():
            raise CliError("analysis root must be a directory")
    else:
        root = _repository_root(options)
        if root is None:
            raise CliError("analysis root is unavailable")
    from . import go_bridge

    return go_bridge.run(
        ["--repository", os.fspath(root), "analyze", *arguments],
        repository_root=root,
    )


def _dispatch(options: dict[str, str], arguments: list[str]) -> int:
    if not arguments:
        raise CliError("a command is required")
    family = arguments.pop(0)
    if family not in FAMILIES:
        raise CliError(f"unknown command family: {family}")

    if family == "build-info":
        if arguments:
            raise CliError("build-info takes no arguments")
        from . import go_bridge

        return go_bridge.run(["build-info"], repository_root=None)

    if family == "check":
        if not arguments:
            raise CliError("check requires a command")
        owner = {
            "change-size": "apg-check-change-size",
            "phase-commit-message": "apg-check-phase-commit-message",
            "record-identity": "apg-check-record-identity",
            "skill-library": "apg-check-skill-library",
        }.get(arguments.pop(0))
        if owner is None:
            raise CliError("unknown check command")
        return _repository_route(owner, arguments, options)

    if family == "skills":
        if not arguments:
            raise CliError("skills requires a command")
        action = arguments.pop(0)
        if action in {"list", "context-report", "resolve", "materialize", "verify-corpus"}:
            from . import go_bridge

            return go_bridge.run(
                ["skills", action, *arguments],
                repository_root=None,
            )
        owner = {
            "project": "apg-project-skills",
            "user": "apg-user-skills",
            "install-global": "install-global-skills",
            "flatten": "flatten-skill-symlinks",
        }.get(action)
        if owner is None:
            raise CliError("unknown skills command")
        return _repository_route(owner, arguments, options)

    if family == "footprint":
        from . import go_bridge

        return go_bridge.run(["footprint", *arguments], repository_root=None)

    if family == "test":
        return _repository_route("apg-test", arguments, options)
    if family == "env":
        return _environment_route(options, arguments)
    if family == "analyze":
        return _dispatch_analyze(options, arguments)
    if family == "release":
        if not arguments or arguments.pop(0) != "public":
            raise CliError("release requires the public command")
        return _repository_route("apg-public-release", arguments, options)
    if family == "report":
        from . import reports

        return reports.main(options, arguments, _repository_root(options))
    if family == "response":
        from . import response

        return response.main(options, arguments, _repository_root(options))
    raise AssertionError(f"unhandled command family: {family}")


def main(arguments: Sequence[str] | None = None) -> int:
    """Run APGR with bounded diagnostics and stable exit classes."""

    values = list(sys.argv[1:] if arguments is None else arguments)
    try:
        options, tail = _global_options(values)
        if options.get("help"):
            sys.stdout.write(HELP)
            return 0
        if options.get("version"):
            print(f"{COMMAND} {version()}")
            return 0
        return _dispatch(options, tail)
    except (CliError, FileNotFoundError, NotADirectoryError, OSError) as error:
        print(f"{COMMAND}: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
