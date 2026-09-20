"""APG166Z-CONTEXT1 ordinary route: support matrix, prelaunch fallbacks, wrapper refusals."""
from __future__ import annotations

import functools
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from agent_phase import context_adapter, context_route
from agent_phase.claude_context_acquisition import OPTION, TOOLS, identity
from agent_phase.transmission import SCOPE_ENV, Transport

ROOT = Path(__file__).resolve().parents[3]
LAUNCHER = str(ROOT / "bin/claude-profile")
PROMPT = b"Mandatory task and role envelope."


def built_binary() -> Path:
    value = os.environ.get("APG_CONTEXT_BINARY") or os.environ.get("APGR_GO_BINARY")
    if not value or not Path(value).is_file():
        pytest.skip("explicit built CLI binary required (APG_CONTEXT_BINARY)")
    return Path(value)


@pytest.mark.parametrize("provider,profile,argv,code", [
    ("codex", "implementation-testing-review", ["/x/codex", "exec", "-"], "provider_not_in_pilot"),
    ("antigravity", "gemini-3.8-flash-high", ["/x/antigravity-profile", "g", "-p"], "provider_not_in_pilot"),
    ("claude", "opus-high-review", ["/fake/claude", "opus-high-review", "--read-only", "-p"], "launcher_not_claude_profile"),
    ("claude", "opus-high-review", [LAUNCHER, "opus-high-review", "--read-only", "-p", "--live-log", "x"], "argv_shape"),
    ("claude", "normal-sysadmin-plan-review", [LAUNCHER, "normal-sysadmin-plan-review", "--read-only", "-p"],
     "isolated_settings_profile"),
    ("claude", "no-such-profile", [LAUNCHER, "no-such-profile", "-p"], "profile_unknown"),
    ("claude", "opus-high-plan", [LAUNCHER, "opus-high-plan", "-p"], None),
    ("claude", "opus-high-review", [LAUNCHER, "opus-high-review", "--read-only", "-p"], None),
    ("claude", "claude-only-implementation-primary", [LAUNCHER, "claude-only-implementation-primary", "-p"], None),
])
def test_route_support_matrix(provider, profile, argv, code):
    support = context_route.route_support(provider, profile, argv)
    assert support["supported"] is (code is None) and support["code"] == code


def stub_plan(prompt: bytes, deferred=("apgr:vagrantfile-profile",)):
    def planner(request, capture):
        assert request["qualification"]["selective_projection"] is True
        return {"effective_mode": "adaptive", "reasons": [], "catalog": {"overrides": []},
                "payload": prompt.decode() + "\n<apgr-skills>\n[]\n</apgr-skills>\n", "selected_snapshots": [],
                "decisions": [{"requested_id": i, "selected_id": i, "status": "deferred",
                               "reason": "required_closure_exceeds_budget", "required": False} for i in deferred]}
    return planner


def prepare(run_dir: Path, binary: Path, *, profile="opus-high-review", read_only=True, prefix="01-review", planner=None):
    run_dir.mkdir(parents=True, exist_ok=True)
    argv = [LAUNCHER, profile, *(["--read-only"] if read_only else []), "-p"]
    return context_adapter.prepare(
        capture={"settings": {"mode": "adaptive"}, "provenance": [], "overrides": [], "project_root": None,
                 "apgr_home": "/absent"},
        run_dir=run_dir.resolve(), prefix=prefix, run_id="run", binding_id="review", attempt_id="att-1", roles=["review"],
        consumer="claude", argv=argv, prompt=PROMPT, planner=planner or stub_plan(PROMPT),
        postures=["review"], work_tree=None,
        route=lambda: context_route.ordinary_projection(provider="claude", profile=profile, argv=argv, prefix=prefix))


@pytest.fixture
def binary(monkeypatch):
    value = built_binary()
    monkeypatch.setenv("APGR_GO_BINARY", str(value))
    return value


def test_ordinary_prepare_projects_payload_and_compact_authority(tmp_path, binary):
    argv, prompt, state = prepare(tmp_path / "run", binary)
    record = state["record"]
    assert record["effective_mode"] == "adaptive", record.get("diagnostic")
    assert argv[:4] == [LAUNCHER, "opus-high-review", "--read-only", "-p"] and argv[4] == OPTION
    assert prompt.startswith(PROMPT + b"\n<apgr-skills>\n")
    assert b"mcp__apgr__skill_acquire" in prompt and b"apgr:vagrantfile-profile: /" in prompt
    config = json.loads(Path(record["acquisition"]["config"]).read_bytes())
    compact = config["context_plan"]
    assert compact["view"].startswith("compact") and "payload" not in compact
    assert PROMPT.decode() not in json.dumps(compact) and "attempted_request" not in compact
    assert config["allowed_ids"] == ["apgr:vagrantfile-profile"] and "project_root" not in config
    handoff = json.loads(Path(record["acquisition"]["context_handoff"]).read_bytes())
    assert handoff["plan"] == identity(state["path"].read_bytes())
    assert handoff["tools"] == TOOLS and len(handoff["recovery"]) == 1


def test_project_and_overridden_skills_are_not_acquirable():
    plan = {"catalog": {"overrides": [{"requested": "apgr:go-language-profile", "selected": "project:go"}]},
            "decisions": [
                {"requested_id": "project:house", "selected_id": "project:house", "status": "deferred",
                 "reason": "required_closure_exceeds_budget"},
                {"requested_id": "apgr:go-language-profile", "selected_id": "project:go", "status": "deferred",
                 "reason": "required_closure_exceeds_budget"},
                {"requested_id": "apgr:bats-test-profile", "selected_id": "apgr:bats-test-profile", "status": "deferred",
                 "reason": "applicability_unknown_no_positive_fact"},
                {"requested_id": "apgr:x", "selected_id": "apgr:x", "status": "unavailable", "reason": "cycle"}]}
    assert context_route.acquirable(plan) == (["apgr:bats-test-profile"], [])


def static_equal(argv, prompt, profile="opus-high-review", read_only=True):
    assert argv == [LAUNCHER, profile, *(["--read-only"] if read_only else []), "-p"] and prompt == PROMPT


def test_prelaunch_acquisition_failure_is_static(tmp_path, binary, monkeypatch):
    broken = tmp_path / "apgr-broken"
    broken.write_text("#!/bin/sh\nexit 3\n")
    broken.chmod(0o700)
    monkeypatch.setattr(context_route, "persistent_binary", lambda: broken)
    argv, prompt, state = prepare(tmp_path / "run", binary)
    static_equal(argv, prompt)
    assert state["record"]["reason"] == "acquisition_prelaunch_failed"
    assert state["record"]["acquisition"] if "acquisition" in state["record"] else True


def test_unrepresentable_recovery_path_is_static(tmp_path, binary):
    argv, prompt, state = prepare(tmp_path / "run with space", binary)
    static_equal(argv, prompt)
    assert state["record"]["reason"] == "recovery_path_unrepresentable"


def test_final_probe_timeout_is_static_not_stage_failure(tmp_path, binary, monkeypatch):
    def timeout(self, record):
        raise subprocess.TimeoutExpired("apgr", 10)
    monkeypatch.setattr(context_route.OrdinaryAcquisition, "finalize", timeout)
    argv, prompt, state = prepare(tmp_path / "run", binary)
    static_equal(argv, prompt)
    assert state["record"]["reason"] == "acquisition_config_failed"
    assert state["record"]["acquisition"]["status"] == "not_used_static_fallback"


def test_transport_overflow_marks_prepared_acquisition_unused(tmp_path, binary):
    run = tmp_path / "run"
    run.mkdir()
    argv = [LAUNCHER, "opus-high-review", "--read-only", "-p"]
    _, prompt, state = context_adapter.prepare(
        capture={"settings": {"mode": "adaptive", "max_initial_context_bytes": 400}, "provenance": [], "overrides": [],
                 "project_root": None, "apgr_home": "/absent"},
        run_dir=run.resolve(), prefix="01", run_id="run", binding_id="review", attempt_id="att", roles=["review"],
        consumer="claude", argv=argv, prompt=PROMPT, planner=stub_plan(PROMPT), postures=["review"],
        route=lambda: context_route.ordinary_projection(provider="claude", profile="opus-high-review", argv=argv, prefix="01"))
    assert state["record"]["reason"] == "transport_overhead_overflow" and prompt == PROMPT
    assert state["record"]["acquisition"]["status"] == "not_used_static_fallback"


def test_same_attempt_prepared_twice_falls_back_without_error(tmp_path, binary):
    first = prepare(tmp_path / "run", binary)[2]
    assert first["record"]["effective_mode"] == "adaptive"
    argv, prompt, second = prepare(tmp_path / "run", binary)
    static_equal(argv, prompt)
    assert second["record"] is None and second["reason"] == "plan_persistence_failed"
    retry = prepare(tmp_path / "run", binary, prefix="01-review.review-retry")[2]
    assert retry["record"]["effective_mode"] == "adaptive", "retry prefix owns distinct artifacts"


FAKE = "#!" + sys.executable + r'''
import json, os, sys
if "--version" in sys.argv[1:]:
    print("2.1.999 (Claude Code)"); sys.exit(0)
sys.stdin.read()
with open(os.environ["FAKE_CLAUDE_LOG"], "a") as stream:
    stream.write(json.dumps(sys.argv[1:]) + "\n")
print("ok")
'''


def wrapper_env(tmp_path, argv, state):
    bindir = tmp_path / "fake-bin"
    bindir.mkdir(exist_ok=True)
    fake = bindir / "claude"
    fake.write_text(FAKE)
    fake.chmod(0o700)
    base = {k: v for k, v in os.environ.items() if not k.startswith(("APGR_WORKER", "APGR_PARENT", "AGENT_CENTRAL_"))}
    base.update(PATH=str(bindir) + os.pathsep + os.environ["PATH"], FAKE_CLAUDE_LOG=str(tmp_path / "fake.log"))
    return Transport(state).environment(argv, base)


def run_wrapper(argv, env, prompt, cwd):
    return subprocess.run(argv, input=prompt, env=env, cwd=cwd, capture_output=True, timeout=60)


@pytest.mark.parametrize("read_only", [True, False])
def test_wrapper_composes_exact_grants(tmp_path, binary, read_only):
    profile = "opus-high-review" if read_only else "claude-only-implementation-primary"
    argv, prompt, state = prepare(tmp_path / "run", binary, profile=profile, read_only=read_only)
    assert state["record"]["effective_mode"] == "adaptive", state["record"].get("diagnostic")
    env = wrapper_env(tmp_path, argv, state)
    result = run_wrapper(argv, env, prompt, tmp_path)
    assert result.returncode == 0, result.stderr.decode()
    (native,) = [json.loads(line) for line in (tmp_path / "fake.log").read_text().splitlines()]
    config = json.loads(native[native.index("--mcp-config") + 1])
    assert list(config["mcpServers"]) == ["apgr"]
    recovery = state["record"]["acquisition"]["recovery"][0]["absolute_path"]
    assert native[native.index("--allowed-tools") + 1].split(",") == [*TOOLS, "Read(/" + recovery + ")"]
    assert "--add-dir" not in native and native.count("--allowed-tools") == 1
    if read_only:
        assert native[native.index("--tools") + 1].split(",") == ["Read", "Glob", "Grep", "WebFetch", "WebSearch", *TOOLS]
        assert native[native.index("--permission-mode") + 1] == "default"
        assert "--strict-mcp-config" in native
        assert b'"context_acquisition"' in result.stderr
    else:
        assert "--tools" not in native and "--permission-mode" not in native and "--strict-mcp-config" not in native
    with pytest.raises(FileExistsError):
        Path(state["record"]["acquisition"]["context_handoff"] + ".consumed").open("x")


@pytest.mark.parametrize("change", ["digest", "duplicate", "evaluation_option", "isolated_profile", "tool", "server",
                                    "recovery_drift", "second_use", "no_scope", "caller_mcp"])
def test_wrapper_refuses_before_claude_starts(tmp_path, binary, change):
    argv, prompt, state = prepare(tmp_path / "run", binary)
    env = wrapper_env(tmp_path, argv, state)
    handoff = Path(state["record"]["acquisition"]["context_handoff"])
    value = json.loads(handoff.read_bytes())
    scope = json.loads(env[SCOPE_ENV])

    def rewrite():
        handoff.write_text(json.dumps(value))
        scope["context_acquisition"].update(identity(handoff.read_bytes()))
    if change == "digest":
        scope["context_acquisition"]["sha256"] = "0" * 64
    elif change == "duplicate":
        argv = [*argv, OPTION, str(handoff)]
    elif change == "evaluation_option":
        argv = [*argv, "--apgr-acquisition-handoff", str(handoff)]
    elif change == "isolated_profile":
        argv = [argv[0], "normal-sysadmin-plan-review", *argv[2:]]
    elif change == "tool":
        value["tools"] = [*TOOLS, "Bash"]
        rewrite()
    elif change == "server":
        value["server"]["args"] = ["mcp", "serve", "--config", "/etc/passwd"]
        rewrite()
    elif change == "recovery_drift":
        Path(value["recovery"][0]["path"]).write_text("changed")
    elif change == "second_use":
        first = run_wrapper(argv, env, prompt, tmp_path)
        assert first.returncode == 0, first.stderr.decode()
        (tmp_path / "fake.log").unlink()
    elif change == "no_scope":
        scope.pop("context_acquisition")
    elif change == "caller_mcp":
        argv = [*argv, "--mcp-config", "{}"]
    env[SCOPE_ENV] = json.dumps(scope)
    result = run_wrapper(argv, env, prompt, tmp_path)
    assert result.returncode == 2, result.stderr.decode()
    assert not (tmp_path / "fake.log").exists(), "claude must not start"


def test_cancellation_after_start_is_not_replayed(tmp_path, monkeypatch):
    """Liveness expiry after the child starts: one call, partial transport, consumed handoff."""
    from test_agent_phase_context_claude_pilot import FAKE_CLAUDE, git
    from agent_phase import provider
    from agent_phase.dispatch import DispatchError, Dispatcher
    from agent_phase.request import PhaseRequest
    binary = built_binary()
    monkeypatch.setenv("APGR_GO_BINARY", str(binary))
    bindir = tmp_path / "fake-bin"
    bindir.mkdir()
    fake = bindir / "claude"
    fake.write_text(FAKE_CLAUDE.format(python=sys.executable).replace(
        'stage = re.search', 'import time\ntime.sleep(float(os.environ.get("FAKE_HANG", "0")))\nstage = re.search', 1))
    fake.chmod(0o700)
    monkeypatch.setenv("PATH", str(bindir) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("FAKE_CLAUDE_LOG", str(tmp_path / "log.jsonl"))
    monkeypatch.setenv("FAKE_HANG", "30")
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "t@example.invalid")
    git(repo, "config", "user.name", "T")
    (repo / "file.txt").write_text("x\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "init")
    home = tmp_path / "home"
    home.mkdir()
    (home / "config.toml").write_text('[dispatcher.context]\nmode = "adaptive"\n[integrations.rtk]\nenabled = false\n')
    runner = functools.partial(provider.run, liveness_policy=provider.LivenessPolicy(outer_ceiling_seconds=4))
    dispatcher = Dispatcher(ROOT, repo, run_root=tmp_path / "runs", claude_launcher=LAUNCHER, resolve_scanner=False,
                            runner=runner, apgr_home=home, project_root=repo)
    with pytest.raises(DispatchError):
        dispatcher.dispatch("CANCEL", PhaseRequest("implementation_testing", "claude_only", "Implement it."),
                            lifecycle="solo", finalization_policy="checkpoint")
    calls = (tmp_path / "log.jsonl").read_text().splitlines()
    assert len(calls) == 1, "provider attempt is never replayed"
    run_dir = next((tmp_path / "runs").rglob("state.json")).parent
    (plan_path,) = run_dir.glob("*.context-plan.json")
    record = json.loads(plan_path.read_bytes())
    assert record["effective_mode"] == "adaptive"
    transport = json.loads(plan_path.with_name(plan_path.name.replace("context-plan", "context-transport")).read_bytes())
    assert transport["status"] == "partial_or_unknown"
    assert Path(record["acquisition"]["context_handoff"] + ".consumed").is_file()
    drains = list(run_dir.glob("*.worker-drain.json"))
    assert drains and all(json.loads(p.read_bytes()).get("uncertain_cleanup") in (False, None) for p in drains)
