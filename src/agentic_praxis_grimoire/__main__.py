"""Python module entry point for the canonical ``apgr`` executable."""

from __future__ import annotations

from collections.abc import Sequence


def main(arguments: Sequence[str] | None = None) -> int:
    """Delegate to the maintained APGR dispatcher."""

    from .cli import main as cli_main

    return cli_main(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
