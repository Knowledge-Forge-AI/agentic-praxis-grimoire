"""Failing-first pin of the ZE ``launch_facts`` gap (APG166ZF test 1).

ZE proved the source controller ended but accepted an interrupted stage whose
optional ``context-launcher-deliveries.json`` recorded no provider facts. A
provider that outlived its dispatcher on such a route was invisible.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from agent_phase import interrupted_recovery
from agent_phase.resume_validation import ResumeError
from interrupted_run_fixtures import interrupted_source, read_state, tree_bytes, write_state
from test_agent_phase_disposition_flow import repository as _repository

repository = _repository


def modify(cwd):
    (cwd / "README.md").write_text("# Interrupted phase edit\n")


def test_live_provider_without_launch_facts_is_not_guessed_recoverable(repository, tmp_path):
    source = interrupted_source(repository, tmp_path, modify)
    state = read_state(source)
    # A source that cannot say whether launch evidence was required: the
    # pre-ZF shape, with no optional context-launcher facts at all.
    state.pop("provider_launch_contract", None)
    state.pop("provider_launches", None)
    write_state(source, state)
    for path in source.glob("*.provider-launch.json"):
        path.unlink()
    assert not (source / "03-work.context-launcher-deliveries.json").exists()
    survivor = subprocess.Popen([sys.executable, "-c", "import sys; sys.stdin.read()"],
                                stdin=subprocess.PIPE, start_new_session=True)
    try:
        before = tree_bytes(source)
        with pytest.raises(ResumeError) as caught:
            interrupted_recovery.ensure(source)
        assert caught.value.code == "RESUME_RECOVERY_REFUSED"
        assert "provider_launch_contract_absent" in caught.value.detail
        assert tree_bytes(source) == before
    finally:
        survivor.communicate(b"")
