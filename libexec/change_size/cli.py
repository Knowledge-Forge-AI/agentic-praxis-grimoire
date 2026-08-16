"""Command-line interface for APG change-size checking."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

from .checker import derive_changes, evaluate, render_json, render_text, tree_changes
from .git_adapter import GitError, GitRepository
from .policy import PolicyError, load_policy_bytes


POLICY_PATH = "testing/apg-change-size-policy.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="apg-check-change-size",
        description="Check staged, committed, or tree Git objects against APG size policy.",
        epilog=(
            "Forms: apg-check-change-size staged [--format text|json]; "
            "apg-check-change-size commit COMMIT [--format text|json]; "
            "apg-check-change-size tree [COMMIT] [--format text|json]"
        ),
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)
    staged = subparsers.add_parser("staged")
    staged.add_argument("--format", choices=("text", "json"), default="text")
    commit = subparsers.add_parser("commit")
    commit.add_argument("commit")
    commit.add_argument("--format", choices=("text", "json"), default="text")
    tree = subparsers.add_parser("tree")
    tree.add_argument("commit", nargs="?")
    tree.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def _selected_state(
    repository: GitRepository, arguments: argparse.Namespace
) -> tuple[str, str, dict, dict, list]:
    if arguments.mode == "staged":
        revision = repository.head()
        before = repository.tree_entries(revision)
        after = repository.index_entries()
        changes = derive_changes(before, after)
        policy_revision = ""
    elif arguments.mode == "commit":
        revision = repository.resolve_commit(arguments.commit)
        parent = repository.parent(revision)
        before = repository.tree_entries(parent) if parent else {}
        after = repository.tree_entries(revision)
        changes = derive_changes(before, after)
        policy_revision = revision
    else:
        revision = repository.resolve_commit(arguments.commit or "HEAD")
        before = {}
        after = repository.tree_entries(revision)
        changes = tree_changes(after)
        policy_revision = revision
    return revision, policy_revision, before, after, changes


def run(arguments: Sequence[str] | None = None) -> int:
    try:
        parsed = build_parser().parse_args(arguments)
        repository = GitRepository.discover(Path.cwd())
        revision, policy_revision, before, _after, changes = _selected_state(
            repository, parsed
        )
        policy = load_policy_bytes(repository.object_file(policy_revision, POLICY_PATH))
        result = evaluate(
            repository,
            policy,
            changes,
            mode=parsed.mode,
            revision=revision,
            before_entries=before,
        )
    except PolicyError as error:
        print(f"policy error: {error}", file=sys.stderr)
        return 2
    except GitError as error:
        print(f"Git error: {error}", file=sys.stderr)
        return 2
    output = render_json(result) if parsed.format == "json" else render_text(result)
    sys.stdout.write(output)
    return 1 if result["violations"] else 0


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
