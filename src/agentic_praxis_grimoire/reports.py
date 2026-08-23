"""Canonical APGR report routing and checkout-independent path inspection."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
import sys

from . import go_bridge
from .config import ConfigError, resolve_outbox_root
from .paths import PathContractError, outbox_phase_path, validate_identifier


class ReportRouteError(ValueError):
    """A canonical report command is malformed or lacks repository authority."""


KINDS = {
    "show": "git.show.report.txt",
    "diff": "git.diff.report.txt",
    "ops": "ops.report.txt",
}


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
        if action not in {"show", "diff", "operational", "ops", "recover", "path"}:
            raise ReportRouteError(f"unknown report command: {action}")
        if action == "path":
            _parse_path(tail)
        if action != "path" and repository_root is None:
            raise ReportRouteError(f"report {action} requires an APG repository")
        if (
            repository_root is not None
            and options.get("project") is not None
            and project != repository_root.name
        ):
            raise ReportRouteError(
                "--project must match the repository basename for report writes"
            )
        return go_bridge.run(
            go_bridge.canonical_arguments(
                repository_root=repository_root,
                outbox_root=outbox,
                project=project,
                action=action,
                arguments=tail,
            ),
            repository_root=repository_root,
        )
    except (ConfigError, PathContractError, ReportRouteError) as error:
        print(f"apgr report: {error}", file=sys.stderr)
        return 2
    except go_bridge.GoBridgeError as error:
        print(f"apgr report: {error}", file=sys.stderr)
        return 1


__all__ = ["KINDS", "ReportRouteError", "main", "report_path"]
