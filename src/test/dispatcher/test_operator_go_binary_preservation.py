"""Operator binary input survives the dispatcher launcher-state isolation."""
import importlib.util
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('configured', [True, False])
def test_operator_binary_preserved_and_launcher_state_scrubbed(tmp_path, monkeypatch, configured):
    spec = importlib.util.spec_from_file_location('operator_binary_conftest', ROOT / 'src/test/dispatcher/conftest.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.syspath_prepend(str(ROOT / 'src'))
    from agentic_praxis_grimoire import go_bridge
    import test_agent_phase_context_route as route
    import test_agent_phase_context_claude_pilot as pilot

    executable = tmp_path / 'apgr'
    executable.write_text('#!/bin/sh\nexit 0\n')
    executable.chmod(0o700)
    keys = ['APGR_HOME', 'APGR_CUSTOM_RUN', 'AGENT_CENTRAL_ACTIVE_ROOT',
            'AGENT_WORKER_PARENT_ID', *module.LAUNCHER_SCRUB_EXACT_KEYS]
    for key in keys:
        monkeypatch.setenv(key, 'planted launcher state')
    monkeypatch.setenv('SAFE_PROCESS_VAR', 'preserved')
    monkeypatch.delenv('APG_CONTEXT_BINARY', raising=False)
    monkeypatch.delenv('APGR_GO_BINARY', raising=False)
    if configured:
        monkeypatch.setenv('APGR_GO_BINARY', str(executable))

    module.scrub_launcher_environment(monkeypatch)
    assert all(key not in os.environ for key in keys)
    assert os.environ['SAFE_PROCESS_VAR'] == 'preserved'
    if configured:
        assert os.environ['APGR_GO_BINARY'] == str(executable)
        assert route.built_binary() == pilot.built_binary() == executable
        invocation = go_bridge.locate()
        assert invocation.kind == 'override'
        assert invocation.argv == (str(executable),)
        assert invocation.cwd == Path.cwd()
    else:
        assert 'APGR_GO_BINARY' not in os.environ
