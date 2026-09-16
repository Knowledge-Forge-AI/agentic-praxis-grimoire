"""Exact runtime pruning and durable custody fences on resume."""
import json
import os

import pytest
from agent_phase.resume_validation import require_source, ResumeError
from agent_phase.worker_recovery import verify_retained_cleanup
from test_agent_phase_resume import repository as _repository, failed_source, dispatcher, Runner, PHASE, REQUEST

repository = _repository


@pytest.mark.parametrize("where", ["workers/parent/serena-home", "elsewhere", "state.json", "04-final-review.stdout.md"])
def test_runtime_pruning_is_exact_and_no_follow(tmp_path, monkeypatch, where):
    source = tmp_path / "source"
    source.mkdir()
    node = source / where
    node.parent.mkdir(parents=True, exist_ok=True)
    node.symlink_to(tmp_path / "unreadable-target")
    real_stat = os.stat
    def guarded(path, *args, **kwargs):
        assert "unreadable-target" not in str(path)
        assert not str(path).endswith("serena-home")
        return real_stat(path, *args, **kwargs)
    monkeypatch.setattr(os, "stat", guarded)
    excluded = []
    if where == "workers/parent/serena-home":
        assert require_source(source, excluded) == source
        assert excluded[0]["path"] == where
    else:
        with pytest.raises(ResumeError):
            require_source(source, excluded)


@pytest.mark.parametrize("uncertain", [True, False])
def test_retained_stage_drain_checked_without_global_marker(tmp_path, uncertain):
    drain = {"status": "closed" if not uncertain else "stopping", "uncertain_cleanup": uncertain}
    (tmp_path / "03-work.worker-drain.json").write_text(json.dumps(drain))
    (tmp_path / "03-work.meta.json").write_text(json.dumps({"worker_drain": drain}))
    if uncertain:
        with pytest.raises(ValueError, match="custody"):
            verify_retained_cleanup(tmp_path, {})
    else:
        verify_retained_cleanup(tmp_path, {})


def test_pending_marker_blocks_without_proven_ledger(tmp_path):
    with pytest.raises(ValueError, match="custody"):
        verify_retained_cleanup(tmp_path, {"worker_cleanup_pending": {"status": "incomplete"}})


def test_resume_final_review_skips_runtime_and_inherits_producer(repository, tmp_path):
    source = failed_source(repository, tmp_path, 3)
    runtime = source / "workers" / "parent" / "serena-home"
    runtime.parent.mkdir(parents=True)
    runtime.symlink_to(tmp_path / "never-read")
    runner = Runner()
    state = dispatcher(repository, tmp_path / "resumed", runner).resume(
        PHASE, REQUEST, source, "final_review"
    )
    assert state["resume"]["inherited_stages"] == ["plan", "plan_review", "work"]
    assert len(runner.calls) == 2
    assert state["resume"]["excluded_source_paths"][0]["path"] == "workers/parent/serena-home"
    assert runtime.is_symlink()
