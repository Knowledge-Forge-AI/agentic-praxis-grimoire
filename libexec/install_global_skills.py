"""CLI for one owned multi-repository Codex or Claude skill projection."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
from typing import Mapping, Sequence

from global_skills_inventory import (
    Inventory,
    InventoryError,
    build_inventory,
    destination_for,
    source_values,
)
from global_skills_state import (
    STATE_NAME,
    StateError,
    check_apg_user_skills_owner,
)
from global_skills_transaction import (
    OperationResult,
    TransactionError,
    apply,
    inspect,
    uninstall,
)


COMMAND = "install-global-skills"
NOTES = {
    "codex": (
        "Codex changes should be detected automatically; restart when not visible."
    ),
    "claude": (
        "Claude changes in an existing watched skills directory are detected live; "
        "creating the top-level skills directory after session start may require a restart."
    ),
}


class InstallError(RuntimeError):
    """The requested CLI operation is contradictory or unsafe."""


@dataclass(frozen=True, slots=True)
class Request:
    agent: str
    mode: str
    output_format: str
    destination: Path
    inventory: Inventory | None
    environment: Mapping[str, str] | None = None


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog=COMMAND,
        usage="install-global-skills AGENT [REPOSITORY ...] [options]",
        description=(
            "Project local skill repositories as one owned flat personal skill set."
        ),
    )
    root.add_argument("agent", choices=("codex", "claude"))
    root.add_argument(
        "repositories",
        nargs="*",
        type=Path,
        metavar="REPOSITORY",
        help="local repository root containing skills/",
    )
    root.add_argument(
        "--include-apg",
        action="store_true",
        help="include the resolved APG repository with explicit repositories",
    )
    root.add_argument(
        "--apg-root",
        type=Path,
        help="exact APG repository override",
    )
    root.add_argument(
        "--skills-root",
        type=Path,
        help="exact personal skill destination override",
    )
    root.add_argument(
        "--check",
        action="store_true",
        help="report drift without mutation; exit 1 when not current",
    )
    root.add_argument(
        "--dry-run",
        action="store_true",
        help="render the exact planned transaction without mutation",
    )
    root.add_argument(
        "--uninstall",
        action="store_true",
        help="remove exact state-owned links and empty owned containers",
    )
    root.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="deterministic output format (default: text)",
    )
    return root


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return parser().parse_args(argv)


def resolve_request(
    arguments: argparse.Namespace,
    environment: Mapping[str, str],
) -> Request:
    selected = sum((arguments.check, arguments.dry_run, arguments.uninstall))
    if selected > 1:
        raise InstallError("--check, --dry-run, and --uninstall cannot be combined")
    destination = destination_for(
        arguments.agent, arguments.skills_root, environment
    )
    check_apg_user_skills_owner(destination, environment)
    if arguments.uninstall:
        if arguments.repositories or arguments.include_apg or arguments.apg_root:
            raise InstallError("--uninstall does not accept source repositories or APG options")
        return Request(
            arguments.agent,
            "uninstall",
            arguments.format,
            destination,
            None,
            dict(environment),
        )
    repositories = source_values(
        arguments.repositories,
        arguments.include_apg,
        arguments.apg_root,
        environment,
    )
    inventory = build_inventory(repositories, destination)
    mode = "check" if arguments.check else "dry-run" if arguments.dry_run else "apply"
    return Request(
        arguments.agent,
        mode,
        arguments.format,
        destination,
        inventory,
        dict(environment),
    )


def source_records(inventory: Inventory | None) -> list[dict[str, str]]:
    if inventory is None:
        return []
    return [
        {
            "repository": str(source.repository),
            "skills_root": str(source.skills_root),
        }
        for source in inventory.sources
    ]


def skill_records(inventory: Inventory | None) -> list[dict[str, str]]:
    if inventory is None:
        return []
    return [
        {
            "name": skill.name,
            "relative_path": skill.relative_path,
            "repository": str(skill.repository),
            "skill_sha256": skill.skill_sha256,
            "source": str(skill.source),
        }
        for skill in inventory.skills
    ]


def result_document(result: OperationResult) -> dict[str, object]:
    sources = source_records(result.inventory)
    skills = skill_records(result.inventory)
    return {
        "agent": result.agent,
        "changed": result.changed,
        "created": result.created,
        "destination": str(result.destination),
        "mode": result.mode,
        "post_action_discovery_note": NOTES[result.agent],
        "removed": result.removed,
        "replaced": result.replaced,
        "schema_version": 1,
        "skill_count": len(skills),
        "skills": skills,
        "source_repository_count": len(sources),
        "sources": sources,
        "state_path": str(result.destination / STATE_NAME),
        "unchanged": result.unchanged,
    }


def render(result: OperationResult, output_format: str) -> str:
    document = result_document(result)
    if output_format == "json":
        return (
            json.dumps(
                document,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            + "\n"
        )
    ordered = (
        "agent",
        "destination",
        "source_repository_count",
        "skill_count",
        "created",
        "replaced",
        "removed",
        "unchanged",
        "state_path",
        "mode",
        "post_action_discovery_note",
    )
    return "\n".join(f"{key}: {document[key]}" for key in ordered) + "\n"


def execute(request: Request) -> OperationResult:
    if request.mode == "uninstall":
        return uninstall(
            request.agent, request.destination, request.environment
        )
    if request.inventory is None:
        raise InstallError("source inventory is absent")
    if request.mode == "apply":
        return apply(
            request.agent, request.inventory, request.environment
        )
    return inspect(request.agent, request.inventory, request.mode)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        arguments = parse_args(argv)
        request = resolve_request(arguments, os.environ)
        result = execute(request)
        sys.stdout.write(render(result, request.output_format))
        for warning in result.warnings:
            print(f"{COMMAND}: warning: {warning}", file=sys.stderr)
        if request.mode == "check" and result.changed:
            return 1
        return 0
    except (InstallError, InventoryError, StateError, TransactionError, OSError) as error:
        print(f"{COMMAND}: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
