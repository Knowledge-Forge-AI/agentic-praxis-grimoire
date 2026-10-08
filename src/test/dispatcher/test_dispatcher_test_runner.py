"""Explicit pytest node selections must not expand to the default dispatcher suite."""
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("targets", [
    [], ["-q"],
    ["src/test/dispatcher/test_zo_routes.py"],
    ["src/test/dispatcher/test_zo_routes.py::test_selected_route"],
    ["src/test/dispatcher/test_agent_phase_roster.py::test_node[socket]"],
])
def test_maintained_runner_preserves_exact_node_targets(monkeypatch, targets):
    module = runpy.run_path(str(ROOT / "bin/apg-test-dispatcher"))
    calls = []
    def record(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(module["subprocess"], "run", record)
    monkeypatch.setattr(sys, "argv", ["apg-test-dispatcher", *targets])
    assert module["main"]() == 0
    default = str(ROOT / "src/test/dispatcher")
    assert (default in calls[0]) == (not targets or targets == ["-q"])
    assert calls[0][-len(targets):] == targets if targets else True
