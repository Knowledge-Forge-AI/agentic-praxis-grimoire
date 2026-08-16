"""Canonical APGR report routing and checkout-independent path inspection."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import contextmanager
import importlib
import os
from pathlib import Path
import sys

from .config import ConfigError, resolve_outbox_root
from .paths import PathContractError, outbox_phase_path, validate_identifier


class ReportRouteError(ValueError):
    """A canonical report command is malformed or lacks repository authority."""


KINDS = {
    "show": "git.show.report.txt",
    "diff": "git.diff.report.txt",
    "ops": "ops.report.txt",
}


@contextmanager
def _working_directory(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def report_path(outbox_root: Path, project: str, phase: str, kind: str) -> Path:
    """Return one canonical primary report path without creating it."""

    if kind not in KINDS:
        raise ReportRouteError("report kind must be show, diff, or ops")
    phase_name = validate_identifier(phase, "phase")
    directory = outbox_phase_path(outbox_root, project, phase_name)
    return directory / f"{phase_name}.{KINDS[kind]}"


def _parse_path(arguments: Sequence[str]) -> tuple[str, str]:
    values = list(arguments)
    phase: str | None = None
    kind: str | None = None
    while values:
        option = values.pop(0)
        if option == "--phase" and values and phase is None:
            phase = values.pop(0)
        elif option == "--kind" and values and kind is None:
            kind = values.pop(0)
        else:
            raise ReportRouteError(f"unknown or incomplete report path option: {option}")
    if phase is None or kind is None:
        raise ReportRouteError("report path requires --phase and --kind")
    return phase, kind


def _report_cli(repository_root: Path):
    if not (repository_root / "libexec" / "agent_report" / "cli.py").is_file():
        raise ReportRouteError("repository does not provide APG report owners")
    helper = os.fspath(repository_root / "libexec")
    if helper not in sys.path:
        sys.path.insert(0, helper)
    return importlib.import_module("agent_report.cli")


def _recover_phase(arguments: Sequence[str]) -> str:
    values = list(arguments)
    if len(values) != 2 or values[0] != "--phase":
        raise ReportRouteError("report recover requires --phase PHASE")
    return validate_identifier(values[1], "phase")


def main(
    options: Mapping[str, str],
    arguments: Sequence[str],
    repository_root: Path | None,
) -> int:
    """Route canonical report commands with resolved scalar configuration."""

    try:
        if not arguments:
            raise ReportRouteError(
                "report requires show, diff, operational, recover, or path"
            )
        action, *tail = arguments
        project = options.get("project")
        if project is None and repository_root is not None:
            project = repository_root.name
        if project is None:
            raise ReportRouteError("--project is required outside a repository")
        validate_identifier(project, "project")
        outbox = resolve_outbox_root(
            options.get("outbox_root"),
            project_root=repository_root,
            apgr_home=options.get("apgr_home"),
        )
        if action == "path":
            phase, kind = _parse_path(tail)
            print(report_path(outbox, project, phase, kind))
            return 0
        if repository_root is None:
            raise ReportRouteError(f"report {action} requires an APG repository")
        if options.get("project") is not None and project != repository_root.name:
            raise ReportRouteError(
                "--project must match the repository basename for report writes"
            )
        cli = _report_cli(repository_root)
        with _working_directory(repository_root):
            if action == "recover":
                phase = _recover_phase(tail)
                safety = importlib.import_module("agent_report.safety")
                try:
                    recovered = safety.Destination(
                        repository_root, phase, outbox_root=outbox
                    ).recover_transaction()
                except (safety.ReportError, safety.UsageError, OSError) as error:
                    raise ReportRouteError(str(error)) from error
                print("recovered" if recovered else "no transaction")
                return 0
            if action == "show":
                return cli.git_show_main(tail, outbox_root=outbox)
            if action == "diff":
                return cli.git_diff_main(tail, outbox_root=outbox)
            if action in {"operational", "ops"}:
                return cli.append_operational_main(tail, outbox_root=outbox)
        raise ReportRouteError(f"unknown report command: {action}")
    except (ConfigError, PathContractError, ReportRouteError) as error:
        print(f"apgr report: {error}", file=sys.stderr)
        return 2


__all__ = ["KINDS", "ReportRouteError", "main", "report_path"]
