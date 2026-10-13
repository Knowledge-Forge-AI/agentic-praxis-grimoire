"""Provider-free end-to-end qualification of interrupted recovery (APG166ZF).

A separate dispatcher process runs the maintained CLI with real ``provider.run``
and a development controller generation recorded by the normal path. It is
SIGKILLed during the mutating ``work`` stage, and the run is then resumed
through the normal CLI into review, closeout and the ZE ownership lane.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess

import pytest

from agent_phase import cli as cli_module
from agent_phase import ownership_challenge, provider
from agent_phase.dispatch import Dispatcher
from interrupted_run_fixtures import tree_bytes
from provider_launch_fixtures import (
    LIFECYCLE,
    WORKER_ENV,
    clean_environment,
    kill_group,
    process_gone,
    read_record,
    run_driver,
    wait_until,
    write_executable,
)

ROOT = Path(__file__).resolve().parents[3]
PHASE = "APG166ZF-E2E"

DRIVER = r'''
import os, signal, sys
from pathlib import Path
root, repo, runs, home, fake, request, mode = sys.argv[1:8]
import controller_generation
controller_generation.observe_development(Path(root))
from agent_phase import cli, provider
from agent_phase.dispatch import Dispatcher

def factory(*args, **kwargs):
    return Dispatcher(Path(root), Path(repo), run_root=Path(runs), claude_launcher=fake, codex_executable=fake,
                      resolve_scanner=False, scanner_executable=None, runner=provider.run,
                      apgr_home=Path(home), project_root=Path(repo),
                      review_mutation_policy=kwargs.get("review_mutation_policy", "block"))

if mode == "before-proceed":
    def lose_before_proceed(process, argv, cwd, environment):
        # Dispatcher loss after the work gate reported durable facts but
        # before the proceed byte: the provider must never execute.
        if any(Path(runs).rglob("03-work.provider-launch.json")):
            Path(runs, "work-gate.pid").write_text(str(process.pid))
            os.kill(os.getpid(), signal.SIGKILL)
    provider.PROCESS_CREATION_HOOK.set(lose_before_proceed)
cli.Dispatcher = factory
os.chdir(repo)
sys.exit(cli.dispatch_main([request, "--finalization", "checkpoint", "--quiet"]))
'''


@pytest.fixture
def e2e(tmp_path, monkeypatch):
    for key in WORKER_ENV:
        monkeypatch.delenv(key, raising=False)
    repo = tmp_path / "repo"
    repo.mkdir()
    for arguments in (["init", "-q"], ["config", "user.email", "t@example.invalid"], ["config", "user.name", "T"]):
        subprocess.run(["git", *arguments], cwd=repo, check=True, capture_output=True)
    (repo / "README.md").write_text("# entry\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=repo, check=True, capture_output=True)
    home = tmp_path / "home"
    home.mkdir()
    (home / "config.toml").write_text("[integrations.rtk]\nenabled = false\n")
    provider_dir = tmp_path / "provider"
    provider_dir.mkdir()
    monkeypatch.setenv("FAKE_PROVIDER_DIR", str(provider_dir))
    fake = write_executable(tmp_path / "claude-profile", LIFECYCLE)
    request = tmp_path / f"{PHASE}.json"
    request.write_text(json.dumps({"schema": "agent-phase-request-v1", "phase_type": "implementation_testing",
                                   "execution_mode": "claude_only", "prompt": "Implement the fixture change."}))

    class E2E:
        def __init__(self) -> None:
            self.repo, self.home, self.fake, self.request = repo, home, fake, request
            self.provider_dir, self.runs = provider_dir, tmp_path / "runs"

        def drive(self, mode: str) -> subprocess.Popen:
            return run_driver(DRIVER, str(ROOT), str(repo), str(self.runs), str(home), str(fake),
                              str(request), mode, environment=clean_environment())

        def source(self) -> Path:
            (state,) = self.runs.rglob("state.json")
            return state.parent

        def calls(self) -> list[dict]:
            path = provider_dir / "calls.jsonl"
            return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

        def resume(self, source: Path, capsys) -> tuple[int, dict | None, str]:
            def factory(*_args, **kwargs):
                return Dispatcher(ROOT, repo, run_root=tmp_path / "resumed", claude_launcher=str(fake),
                                  codex_executable=str(fake), resolve_scanner=False, scanner_executable=None,
                                  runner=provider.run, apgr_home=home, project_root=repo,
                                  review_mutation_policy=kwargs.get("review_mutation_policy", "block"))

            monkeypatch.setattr(cli_module, "Dispatcher", factory)
            monkeypatch.chdir(repo)
            try:
                code = cli_module.dispatch_main([str(request), "--resume", str(source),
                                                 "--finalization", "checkpoint", "--quiet"])
            except SystemExit as exit_:
                code = exit_.code
            captured = capsys.readouterr()
            return code, (json.loads(captured.out) if code == 0 else None), captured.err

    return E2E()


def test_killed_mutating_stage_refuses_while_provider_lives_then_resumes_to_manager_lane(e2e, capsys):
    (e2e.provider_dir / "block-work").write_text("")
    driver = e2e.drive("after-start")
    ready = e2e.provider_dir / "ready"
    try:
        wait_until(lambda: ready.exists() or driver.poll() is not None, timeout=120)
        assert ready.exists(), driver.stderr.read().decode()
        provider_pid = int(ready.read_text())
        source = e2e.source()
        record = read_record(source / "03-work.provider-launch.json")
        assert record["phase"] == "exec_confirmed" and record["process"]["pid"] == provider_pid
        driver.send_signal(signal.SIGKILL)
        assert driver.wait(timeout=30) == -signal.SIGKILL
        assert not (source / "result.json").exists()
        state = json.loads((source / "state.json").read_bytes())
        assert state["controller_generation"]["pid"] == driver.pid
        assert state["stages_invoked"] == ["plan", "plan_review", "work"]

        before = tree_bytes(source)
        code, _state, err = e2e.resume(source, capsys)
        assert code == 2 and "provider_process_live" in err, err
        assert tree_bytes(source) == before
    finally:
        if driver.poll() is None:
            driver.kill()
            driver.wait()
        if ready.exists():
            kill_group(int(ready.read_text()))
    wait_until(lambda: process_gone(provider_pid))

    code, resumed, err = e2e.resume(source, capsys)
    assert code == 0, err
    recovery = json.loads((source / "interrupted-recovery.json").read_bytes())
    assert recovery["interrupted_stage"] == "work"
    assert recovery["provider_launch"]["records"][-1] == {
        "name": "03-work.provider-launch.json",
        "sha256": recovery["provider_launch"]["records"][-1]["sha256"],
        "phase": "exec_confirmed", "classification": "started"}
    assert resumed["resume"]["source_interrupted_recovery"]["interrupted_stage"] == "work"
    assert resumed["semantic_outcome"] == "completed"
    assert [call["stage"] for call in e2e.calls()] == [
        "plan", "plan_review", "work", "work", "final_review", "closeout"]
    # ZE's manager-only ownership lane owns the killed stage's residue; no
    # custom reconstruction is involved.
    assert resumed["completion_kind"] == "candidate_requires_manager_disposition"
    ownership_challenge.validate(e2e.repo, resumed)
    records = [r for r in resumed["ownership_challenges"]["records"]
               if ownership_challenge.statuses(resumed)[r["challenge_id"]] == "open"]
    assert [r["path"] for r in records] == ["interrupted-work.txt"]
    assert "work.txt" in resumed["phase_owned_paths"]
    resumed_dir = Path(resumed["run_directory"])
    assert resumed["provider_launches"] == ["03-work", "04-final-review", "05-closeout"]
    for prefix in resumed["provider_launches"]:
        assert read_record(resumed_dir / f"{prefix}.provider-launch.json")["phase"] == "returned"


def test_dispatcher_lost_before_proceed_never_runs_work_provider(e2e, capsys):
    driver = e2e.drive("before-proceed")
    assert driver.wait(timeout=120) == -signal.SIGKILL, driver.stderr.read().decode()
    source = e2e.source()
    gate = int((e2e.runs / "work-gate.pid").read_text())
    wait_until(lambda: process_gone(gate))
    assert [call["stage"] for call in e2e.calls()] == ["plan", "plan_review"]
    assert not (e2e.repo / "work.txt").exists() and not (e2e.repo / "interrupted-work.txt").exists()
    record = read_record(source / "03-work.provider-launch.json")
    assert record["phase"] == "awaiting_authorization" and record["process"]["pid"] == gate

    code, resumed, err = e2e.resume(source, capsys)
    assert code == 0, err
    recovery = json.loads((source / "interrupted-recovery.json").read_bytes())
    assert recovery["provider_launch"]["records"][-1]["classification"] == "not_authorized"
    assert resumed["semantic_outcome"] == "completed"
    assert [call["stage"] for call in e2e.calls()] == [
        "plan", "plan_review", "work", "final_review", "closeout"]
    assert not os.path.exists(e2e.repo / "interrupted-work.txt")
