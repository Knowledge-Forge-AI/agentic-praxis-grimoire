"""Unit contracts for the APGR package version authority."""

from __future__ import annotations

from pathlib import Path
import sys
try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 compatibility.
    import tomli as tomllib

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src"))

from agentic_praxis_grimoire import VERSION, __version__  # noqa: E402
from agentic_praxis_grimoire.version import version  # noqa: E402


def test_version_is_read_from_the_single_package_resource() -> None:
    resource = ROOT / "src/agentic_praxis_grimoire/VERSION"
    assert resource.read_text(encoding="utf-8") == "0.9.0\n"
    assert VERSION == "0.9.0"
    assert __version__ == VERSION
    assert version() == VERSION
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert metadata["project"]["dynamic"] == ["version"]
    assert metadata["tool"]["setuptools"]["dynamic"]["version"] == {
        "file": "src/agentic_praxis_grimoire/VERSION"
    }
