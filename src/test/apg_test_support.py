"""Shared path discovery for mirrored APG tests."""

from __future__ import annotations

from pathlib import Path


def repository_root(test_file: str) -> Path:
    """Find the APG root without depending on mirrored test depth."""
    resolved = Path(test_file).resolve()
    for parent in resolved.parents:
        if (parent / "AGENTS.md").is_file() and (
            parent / "release" / "public-surface.json"
        ).is_file():
            return parent
    raise RuntimeError(f"could not locate APG repository root for {resolved.name}")
