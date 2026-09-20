from __future__ import annotations

import os
from pathlib import Path
import sys

import pytest

_LIBEXEC = Path(__file__).resolve().parents[3] / "libexec"
if str(_LIBEXEC) not in sys.path:
    sys.path.insert(0, str(_LIBEXEC))


@pytest.fixture(autouse=True)
def _isolate_launcher_environment(monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory) -> None:
    disposable_home = tmp_path_factory.mktemp("operator_home")
    monkeypatch.setenv("HOME", str(disposable_home))
    for key in list(os.environ):
        if (
            key.startswith(("APGR_", "AGENT_CENTRAL_", "AGENT_WORKER_"))
            or key in (
                "AGENT_PHASE_RUN_ROOT",
                "CODEX_THREAD_ID",
                "CODEX_SESSION_ID",
                "CODEX_CI",
                "CI",
            )
        ):
            monkeypatch.delenv(key, raising=False)
