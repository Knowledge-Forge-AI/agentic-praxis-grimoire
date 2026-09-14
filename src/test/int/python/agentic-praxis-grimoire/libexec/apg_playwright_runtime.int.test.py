"""Exercise the selected real package and browser-cache prerequisite."""

import sys

import pytest

from src.test.apg_test_support import repository_root

ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "libexec"))
import apg_playwright_runtime as subject  # noqa: E402


def test_installed_package_and_all_engine_paths():
    assert subject.validate(ROOT) == {
        "package_version": "1.62.1",
        "engines": ["chromium", "firefox", "webkit"],
        "launch_verified": False,
    }


def test_empty_cache_refuses_instead_of_downloading(tmp_path, monkeypatch):
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path))
    with pytest.raises(subject.PlaywrightPrerequisiteError, match="cache is unavailable"):
        subject.validate(ROOT)
    assert not list(tmp_path.iterdir())
