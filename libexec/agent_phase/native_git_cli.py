"""Provider-free operator native Git authorization command."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from . import gitstate, native_git


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agent-phase-native-git", allow_abbrev=False
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    auth_parser = subparsers.add_parser("authorize", allow_abbrev=False)
    auth_parser.add_argument(
        "--request", type=Path, required=True, help="exact substantive request"
    )
    auth_parser.add_argument(
        "--stage", required=True, help="authorized mutating stage name (e.g. work)"
    )
    auth_parser.add_argument(
        "--path",
        "--paths",
        action="append",
        dest="paths",
        required=True,
        help="authorized canonical path; repeatable",
    )
    auth_parser.add_argument(
        "--max-commits",
        type=int,
        default=1,
        help="maximum commits permitted (default: 1)",
    )
    auth_parser.add_argument(
        "--reason", required=True, help="operator authority reason"
    )
    auth_parser.add_argument(
        "--plan-digest", default=None, help="optional bound plan digest"
    )
    auth_parser.add_argument(
        "--result-digest", default=None, help="optional bound result digest"
    )
    auth_parser.add_argument(
        "--commit-tree", default=None, help="optional bound commit tree SHA"
    )
    auth_parser.add_argument(
        "--output", type=Path, required=True, help="output authority receipt path"
    )
    auth_parser.add_argument(
        "--phase-id", default=None, help="optional explicit phase id"
    )
    auth_parser.add_argument(
        "--dry-run", action="store_true", help="dry-run without writing output"
    )

    args = parser.parse_args(argv)

    if args.command == "authorize":
        try:
            root = gitstate.repository_root(Path.cwd()).resolve()
            out_path = args.output.resolve()
            if out_path.is_relative_to(root):
                raise native_git.NativeGitError(
                    "NATIVE_GIT_AUTHORITY_INVALID",
                    "receipt must be outside the product repository",
                )

            record = native_git.create_authority(
                args.request.resolve(),
                root,
                args.stage,
                args.paths,
                max_commits=args.max_commits,
                reason=args.reason,
                plan_digest=args.plan_digest,
                result_digest=args.result_digest,
                commit_tree=args.commit_tree,
                phase_id=args.phase_id,
            )

            if not args.dry_run:
                data = native_git.encoded(record) + b"\n"
                fd = os.open(
                    args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
                )
                with os.fdopen(fd, "wb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())

            print(json.dumps(record, sort_keys=True, indent=2))
            return 0
        except (native_git.NativeGitError, ValueError, RuntimeError, OSError) as error:
            code = getattr(error, "code", "NATIVE_GIT_AUTHORITY_INVALID")
            print(
                json.dumps(
                    {
                        "schema": native_git.SCHEMA,
                        "outcome": "refused",
                        "code": code,
                        "provider_invocations": 0,
                    }
                )
            )
            return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
