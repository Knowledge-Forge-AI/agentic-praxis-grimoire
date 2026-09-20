"""Exact disposable runtime boundary shared by evidence consumers."""

from pathlib import Path


def disposable_runtime(relative: Path) -> str | None:
    parts = relative.parts
    if len(parts) >= 3 and parts[0] == "workers" and parts[2] == "serena-home":
        return "per-parent Serena runtime; descendants not observed"
    return None
