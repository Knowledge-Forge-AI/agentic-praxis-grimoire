"""Refusal evidence for the external Playwright prerequisite boundary."""

import json
from pathlib import Path
import sys

import pytest

from src.test.apg_test_support import repository_root

ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "libexec"))
import apg_playwright_runtime as subject


def environment(tmp_path, monkeypatch):
    repository = tmp_path / "repository"
    repository.mkdir()
    scratch = tmp_path / "browser"
    scratch.mkdir(mode=0o700)
    package = scratch / "runtime"
    package.mkdir()
    cache = tmp_path / "cache"
    cache.mkdir()
    for key, value in (("APG_PLAYWRIGHT_OWNED_SCRATCH_ROOT", scratch),
                       ("APG_PLAYWRIGHT_PACKAGE_ROOT", package),
                       ("PLAYWRIGHT_BROWSERS_PATH", cache)):
        monkeypatch.setenv(key, str(value))
    for name in ("@playwright/test", "playwright", "playwright-core"):
        manifest = package / "node_modules" / name / "package.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({"name": name, "version": subject.VERSION}))
    return repository, scratch, package, cache


def test_missing_scratch_fails_without_execution(tmp_path, monkeypatch):
    monkeypatch.delenv("APG_PLAYWRIGHT_OWNED_SCRATCH_ROOT", raising=False)
    with pytest.raises(subject.PlaywrightPrerequisiteError, match="set APG_PLAYWRIGHT"):
        subject.validate(tmp_path)


@pytest.mark.parametrize("defect", ["version", "name", "missing", "malformed", "symlink"])
def test_package_identity_is_selected_not_latest(tmp_path, monkeypatch, defect):
    repository, _, package, _ = environment(tmp_path, monkeypatch)
    manifest = package / "node_modules/playwright/package.json"
    if defect in ("version", "name"):
        data = json.loads(manifest.read_text())
        data[defect] = "1.63.0" if defect == "version" else "other-package"
        manifest.write_text(json.dumps(data))
    elif defect == "malformed":
        manifest.write_text("[]")
    else:
        manifest.unlink()
        if defect == "symlink":
            manifest.symlink_to(package / "node_modules/playwright-core/package.json")
    with pytest.raises(subject.PlaywrightPrerequisiteError, match="identity"):
        subject.validate(repository)


@pytest.mark.parametrize("defect", ["public", "repository", "outside", "symlink"])
def test_scratch_custody_is_required(tmp_path, monkeypatch, defect):
    repository, scratch, package, _ = environment(tmp_path, monkeypatch)
    if defect == "public":
        scratch.chmod(0o755)
    elif defect == "repository":
        monkeypatch.setenv("APG_PLAYWRIGHT_OWNED_SCRATCH_ROOT", str(repository))
    elif defect == "outside":
        monkeypatch.setenv("APG_PLAYWRIGHT_PACKAGE_ROOT", str(tmp_path))
    else:
        link = tmp_path / "linked"
        link.symlink_to(package, target_is_directory=True)
        monkeypatch.setenv("APG_PLAYWRIGHT_PACKAGE_ROOT", str(link))
    with pytest.raises(subject.PlaywrightPrerequisiteError):
        subject.validate(repository)


def test_missing_node_is_a_prerequisite_failure(tmp_path, monkeypatch):
    repository, _, _, _ = environment(tmp_path, monkeypatch)
    monkeypatch.delenv("APG_JAVASCRIPT_NODE", raising=False)
    with pytest.raises(subject.PlaywrightPrerequisiteError, match="Node executable"):
        subject.validate(repository)
