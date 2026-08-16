"""The one package version authority and its small public API."""

from __future__ import annotations

from importlib import resources
import re


_VERSION_PATTERN = re.compile(r"\A(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\Z")


def _read_version() -> str:
    value = resources.files("agentic_praxis_grimoire").joinpath("VERSION").read_text(
        encoding="utf-8"
    ).strip()
    if not _VERSION_PATTERN.fullmatch(value):
        raise RuntimeError("agentic_praxis_grimoire/VERSION is not a release version")
    return value


VERSION = _read_version()
__version__ = VERSION


def version() -> str:
    """Return the package version from the package-owned ``VERSION`` resource."""

    return VERSION


__all__ = ["VERSION", "__version__", "version"]
