from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys
from types import ModuleType

ROOT = Path(__file__).resolve().parents[3]
LIBEXEC = ROOT / "libexec"
if str(LIBEXEC) not in sys.path:
    sys.path.insert(0, str(LIBEXEC))


def load_module(relative_path: str, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


import pytest


LAUNCHER_SCRUB_PREFIXES = (
    "APGR_",
    "AGENT_CENTRAL_",
    "AGENT_WORKER_",
)

LAUNCHER_SCRUB_EXACT_KEYS = (
    "AGENT_PHASE_RUN_ROOT",
    "CODEX_THREAD_ID",
    "CODEX_SESSION_ID",
    "CODEX_CI",
    "CI",
)


def scrub_launcher_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Scrub ambient launcher and pipeline variables, preserving explicit APGR_GO_BINARY."""
    for key in list(os.environ):
        if key == "APGR_GO_BINARY":
            continue
        if (
            key.startswith(LAUNCHER_SCRUB_PREFIXES)
            or key in LAUNCHER_SCRUB_EXACT_KEYS
        ):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture(autouse=True)
def _isolate_operator_home(monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory) -> None:
    disposable_home = tmp_path_factory.mktemp("operator_home")
    monkeypatch.setenv("HOME", str(disposable_home))
    scrub_launcher_environment(monkeypatch)
