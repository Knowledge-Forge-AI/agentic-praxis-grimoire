"""Provider-free operator adoption command."""

import argparse
import json
import os
from pathlib import Path

from . import adoption, gitstate, run
from .request import load_request


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agent-phase-adopt", allow_abbrev=False)
    parser.add_argument("--run", type=Path, required=True, help="exact sealed source run directory")
    parser.add_argument("--request", type=Path, required=True, help="new substantive request")
    parser.add_argument("--reason", required=True, help="operator adoption reason")
    parser.add_argument("--path", action="append", dest="paths", help="exact subset path; repeatable")
    parser.add_argument("--materialization-receipt", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        adoption.proof.require_standard_environment()
        root = gitstate.repository_root(Path.cwd()).resolve()
        if args.output.resolve().is_relative_to(root):
            raise adoption.AdoptionError("receipt must be outside the product repository")
        record = adoption.create(args.run, root, run.phase_id_from_request(args.request),
            load_request(args.request), reason=args.reason, paths=args.paths,
            materialization_receipt=args.materialization_receipt)
        if not args.dry_run:
            data = adoption.encoded(record) + b"\n"
            fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        print(json.dumps(record, sort_keys=True, indent=2))
        return 0
    except (ValueError, RuntimeError, OSError, TypeError, KeyError) as error:
        print(json.dumps({"schema": adoption.SCHEMA, "outcome": "refused",
            "code": getattr(error, "code", "ADOPTION_INVALID"), "provider_invocations": 0}))
        return 2
