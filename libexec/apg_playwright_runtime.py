"""APG123's explicit, scratch-only Playwright prerequisite boundary.

This module neither installs packages nor launches a browser. Runtime tests
own launch and semantic qualification; cache presence alone is insufficient.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import subprocess


VERSION = "1.62.1"
ENGINES = ("chromium", "firefox", "webkit")
TEST_PATHS = frozenset(
    f"src/test/int/python/agentic-praxis-grimoire/skills/{name}/SKILL.int.test.py"
    for name in ("playwright-test-profile", "web-accessibility-profile")
)


class PlaywrightPrerequisiteError(ValueError):
    """A required runtime is absent or outside its declared ownership."""


def _directory(name: str, repository: Path, *, private: bool = False) -> Path:
    raw = os.environ.get(name, "")
    path = Path(raw)
    if not raw or not path.is_absolute():
        raise PlaywrightPrerequisiteError(f"set {name} to an external direct directory")
    try:
        resolved = path.resolve(strict=True)
        info = path.lstat()
    except OSError as error:
        raise PlaywrightPrerequisiteError(f"{name} is unavailable") from error
    if (resolved != path or not stat.S_ISDIR(info.st_mode)
            or resolved == repository or repository in resolved.parents):
        raise PlaywrightPrerequisiteError(f"{name} must be an external direct directory")
    if private and (info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077):
        raise PlaywrightPrerequisiteError(f"{name} must be caller-owned and mode 0700")
    return resolved


def validate(repository: Path) -> dict[str, object]:
    """Fail closed before pytest; never install, download, or borrow a session."""
    repository = repository.resolve(strict=True)
    scratch = _directory("APG_PLAYWRIGHT_OWNED_SCRATCH_ROOT", repository, private=True)
    package = _directory("APG_PLAYWRIGHT_PACKAGE_ROOT", repository)
    cache = _directory("PLAYWRIGHT_BROWSERS_PATH", repository)
    if scratch not in package.parents:
        raise PlaywrightPrerequisiteError("Playwright package must be inside owned scratch")
    for name in ("@playwright/test", "playwright", "playwright-core"):
        manifest = package / "node_modules" / name / "package.json"
        try:
            if manifest.resolve(strict=True) != manifest or not manifest.is_file():
                raise ValueError("indirect package manifest")
            data = json.loads(manifest.read_text(encoding="utf-8"))
            if data.get("version") != VERSION or data.get("name") != name:
                raise ValueError("selected package mismatch")
        except (OSError, ValueError, AttributeError) as error:
            raise PlaywrightPrerequisiteError("Playwright package identity must be exactly 1.62.1") from error
    node = Path(os.environ.get("APG_JAVASCRIPT_NODE", ""))
    if not node.is_absolute() or not node.is_file() or not os.access(node, os.X_OK):
        raise PlaywrightPrerequisiteError("set APG_JAVASCRIPT_NODE to the qualified Node executable")
    script = (
        "const p=require('playwright');"
        "process.stdout.write(JSON.stringify(['chromium','firefox','webkit']"
        ".map(n=>[n,p[n].executablePath()])));"
    )
    try:
        result = subprocess.run(
            [str(node), "-e", script], cwd=package, env=os.environ.copy(),
            capture_output=True, text=True, timeout=15, check=True,
        )
        identities = json.loads(result.stdout)
        if not isinstance(identities, list) or len(identities) != 3:
            raise ValueError("invalid engine inventory")
        for expected, row in zip(ENGINES, identities, strict=True):
            if not isinstance(row, list) or len(row) != 2 or row[0] != expected:
                raise ValueError("invalid engine identity")
            executable = Path(row[1]).resolve(strict=True)
            if cache not in executable.parents or not executable.is_file() or not os.access(executable, os.X_OK):
                raise ValueError("engine unavailable")
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as error:
        raise PlaywrightPrerequisiteError("required Chromium/Firefox/WebKit cache is unavailable") from error
    return {"package_version": VERSION, "engines": list(ENGINES), "launch_verified": False}
