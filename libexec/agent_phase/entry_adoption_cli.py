"""Provider-free operator entry-candidate adoption command."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from . import entry_adoption, gitstate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agent-phase-adopt-entry", allow_abbrev=False
    )
    parser.add_argument(
        "--request", type=Path, required=True, help="exact substantive request"
    )
    parser.add_argument(
        "--path",
        "--paths",
        action="append",
        dest="paths",
        required=True,
        help="exact adopted path in worktree; repeatable",
    )
    parser.add_argument(
        "--reason", required=True, help="operator adoption reason"
    )
    parser.add_argument(
        "--output", type=Path, required=True, help="output entry adoption receipt path"
    )
    parser.add_argument(
        "--phase-id", default=None, help="optional explicit phase id"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="dry-run without writing output"
    )

    args = parser.parse_args(argv)

    try:
        root = gitstate.repository_root(Path.cwd()).resolve()
        out_path = args.output.resolve()
        if out_path.is_relative_to(root):
            raise entry_adoption.EntryAdoptionError(
                "ENTRY_ADOPTION_INVALID",
                "receipt must be outside the product repository",
            )

        record = entry_adoption.create(
            args.request.resolve(),
            root,
            args.paths,
            reason=args.reason,
            phase_id=args.phase_id,
        )

        if not args.dry_run:
            data = entry_adoption.encoded(record) + b"\n"
            fd = os.open(
                args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
            )
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())

        print(json.dumps(record, sort_keys=True, indent=2))
        return 0
    except (
        entry_adoption.EntryAdoptionError,
        ValueError,
        RuntimeError,
        OSError,
    ) as error:
        code = getattr(error, "code", "ENTRY_ADOPTION_INVALID")
        print(
            json.dumps(
                {
                    "schema": entry_adoption.SCHEMA,
                    "outcome": "refused",
                    "code": code,
                    "provider_invocations": 0,
                }
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
