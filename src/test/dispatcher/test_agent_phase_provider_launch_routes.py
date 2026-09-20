"""Route coverage for durable provider-launch evidence (APG166ZF tests 10-12).

Claude runs through the real ``Dispatcher -> provider.run -> bin/claude-profile``
chain with a fake native ``claude``; Codex runs the dispatcher's ``codex exec``
argv against a fake executable. The shared launch gate is the same code on
both routes; these tests prove each route actually passes through it.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest

from agent_phase import provider, provider_launch
from agent_phase.dispatch import Dispatcher
from agent_phase.lifecycle import get_lifecycle
from agent_phase.request import PhaseRequest
from agent_phase.route_provenance import stage_effective_route
from provider_launch_fixtures import LIFECYCLE, WORKER_ENV, read_record, write_executable
from test_agent_phase_context_claude_pilot import FAKE_CLAUDE, ROOT, pilot as _pilot

pilot = _pilot
PREFIXES = ["01-plan", "02-plan-review", "03-work", "04-final-review", "05-closeout"]
STANDARD = get_lifecycle("standard")


def launch_view(run_dir: Path, state: dict) -> dict:
    resolved = json.loads((run_dir / "resolved.json").read_bytes())
    proof = provider_launch.recovery_proof(
        run_dir, state, None, lifecycle=STANDARD, routes=lambda name: stage_effective_route(resolved, name))
    return {record["name"]: (record["phase"], record["classification"]) for record in proof["records"]}


def require_gated(run_dir: Path, state: dict, calls: list[dict], provider_name: str, executable: str) -> None:
    assert state["provider_launch_contract"] == provider_launch.SCHEMA
    assert state["provider_launches"] == PREFIXES
    for prefix, call in zip(PREFIXES, calls, strict=True):
        record = read_record(run_dir / f"{prefix}.provider-launch.json")
        meta = json.loads((run_dir / f"{prefix}.meta.json").read_bytes())
        assert record["phase"] == "returned" and record["terminal"] == {"exit_code": 0, "reaped": True}
        assert record["binding"]["route"] == {"provider": provider_name, "profile": meta["profile"]}
        assert record["exec"] == {
            "executable": executable,
            "argv_sha256": hashlib.sha256(json.dumps(meta["argv"]).encode()).hexdigest(),
        }
        facts = record["process"]
        # The native child ran inside the gated process group; recovery's
        # group proof therefore covers it.
        assert call["pgid"] == facts["process_group"] == facts["pid"], prefix


@pytest.fixture
def claude_pids(pilot):
    fake = pilot.tmp / "fake-bin" / "claude"
    text = FAKE_CLAUDE.format(python=__import__("sys").executable)
    marker = 'record = {"argv": argv,'
    assert text.count(marker) == 1
    fake.write_text(text.replace(marker, 'record = {"pid": os.getpid(), "pgid": os.getpgid(0), "argv": argv,'))
    return pilot


@pytest.mark.parametrize("mode", ["static", "adaptive"])
def test_claude_parent_route_launches_behind_gate(claude_pids, mode):
    pilot = claude_pids
    pilot.configure(f'[dispatcher.context]\nmode = "{mode}"')
    state, calls, run_dir = pilot.dispatch(phase=f"ZF-{mode.upper()}", runs=f"runs-{mode}")
    assert state["outcome"] == "completed" and len(calls) == 5
    require_gated(run_dir, state, calls, "claude", str(ROOT / "bin/claude-profile"))
    for prefix in PREFIXES:
        # The dispatcher Claude route never selects the wrapper's live-log
        # owner, whose run_live starts native Claude in a nested session.
        assert "--live-log" not in json.loads((run_dir / f"{prefix}.meta.json").read_bytes())["argv"]
    if mode == "static":
        for prefix, call in zip(PREFIXES, calls):
            # Static launches execve the wrapper into native Claude: same pid.
            assert call["pid"] == read_record(run_dir / f"{prefix}.provider-launch.json")["process"]["pid"]


def test_static_and_adaptive_context_share_one_safety_contract(claude_pids):
    pilot = claude_pids
    views = {}
    for mode in ("static", "adaptive"):
        pilot.configure(f'[dispatcher.context]\nmode = "{mode}"')
        state, _calls, run_dir = pilot.dispatch(phase=f"ZF-{mode.upper()}", runs=f"same-{mode}")
        keys = {prefix: sorted(read_record(run_dir / f"{prefix}.provider-launch.json")) for prefix in PREFIXES}
        views[mode] = (keys, launch_view(run_dir, state))
        if mode == "adaptive":
            launcher = sorted(run_dir.glob("*.context-launcher-deliveries.json"))
            assert launcher, "adaptive mode mirrors optional launcher facts"
            for path in launcher:
                path.unlink()
            # Optional context/observability evidence is not the authority.
            assert launch_view(run_dir, state) == views[mode][1]
    assert views["static"] == views["adaptive"]
    assert set(views["static"][1].values()) == {("returned", "returned")}


def test_codex_parent_route_launches_behind_gate(tmp_path, monkeypatch):
    for key in WORKER_ENV:
        monkeypatch.delenv(key, raising=False)
    fake = write_executable(tmp_path / "codex", LIFECYCLE)
    provider_dir = tmp_path / "provider"
    provider_dir.mkdir()
    monkeypatch.setenv("FAKE_PROVIDER_DIR", str(provider_dir))
    repo = tmp_path / "repo"
    repo.mkdir()
    for arguments in (["init", "-q"], ["config", "user.email", "t@example.invalid"], ["config", "user.name", "T"]):
        subprocess.run(["git", *arguments], cwd=repo, check=True, capture_output=True)
    (repo / "file.txt").write_text("one\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=repo, check=True, capture_output=True)
    home = tmp_path / "home"
    home.mkdir()
    (home / "config.toml").write_text("[integrations.rtk]\nenabled = false\n")
    dispatcher = Dispatcher(ROOT, repo, run_root=tmp_path / "runs", codex_executable=str(fake),
                            claude_launcher=str(fake), resolve_scanner=False, scanner_executable=None,
                            runner=provider.run, apgr_home=home, project_root=repo,
                            review_mutation_policy="block")
    state = dispatcher.dispatch("ZF-CODEX", PhaseRequest("implementation_testing", "codex_only", "Implement it."),
                                finalization_policy="checkpoint")
    run_dir = Path(state["run_directory"])
    calls = [json.loads(line) for line in (provider_dir / "calls.jsonl").read_text().splitlines()]
    assert state["outcome"] == "completed" and len(calls) == 5
    assert all(call["argv"][1] == "exec" and call["argv"][-1] == "-" for call in calls)
    require_gated(run_dir, state, calls, "codex", str(fake))
    for prefix, call in zip(PREFIXES, calls):
        assert call["pid"] == read_record(run_dir / f"{prefix}.provider-launch.json")["process"]["pid"]
    assert set(launch_view(run_dir, state).values()) == {("returned", "returned")}
    assert not os.environ.get("APGR_PARENT_ID")
