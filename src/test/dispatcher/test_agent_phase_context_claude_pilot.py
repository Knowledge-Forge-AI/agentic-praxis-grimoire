"""APG166Z-CONTEXT1 ordinary adaptive route through the real dispatcher and wrapper.

Every provider here is a counting fake ``claude`` executable on PATH reached
through the real ``Dispatcher`` -> ``provider.run`` -> ``bin/claude-profile``
chain. These are fixture/test examples, not live model evidence.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

from agent_phase import context_adapter
from agent_phase.dispatch import Dispatcher
from agent_phase.provider import run as production_run
from agent_phase.request import PhaseRequest

ROOT = Path(__file__).resolve().parents[3]
CONTEXT_TOOLS = ["mcp__apgr__skill_search", "mcp__apgr__skill_acquire", "mcp__apgr__context_explain"]

FAKE_CLAUDE = r'''#!{python}
import hashlib, json, os, pathlib, re, subprocess, sys
if "--version" in sys.argv[1:]:
    print("2.1.999 (Claude Code)")
    sys.exit(0)
argv = sys.argv[1:]
prompt = sys.stdin.read()
record = {{"argv": argv, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
          "prompt_bytes": len(prompt.encode()), "skills_block": "\n<apgr-skills>\n" in prompt}}
if "--mcp-config" in argv:
    config = json.loads(argv[argv.index("--mcp-config") + 1])
    record["mcp_servers"] = sorted(config["mcpServers"])
    server = config["mcpServers"].get("apgr")
    want = os.environ.get("FAKE_ACQUIRE")
    if server and want:
        messages = [dict(jsonrpc="2.0", id=1, method="initialize", params=dict(protocolVersion="2025-11-25",
                    capabilities={{}}, clientInfo=dict(name="fake", version="1"))),
                    dict(jsonrpc="2.0", method="notifications/initialized"),
                    dict(jsonrpc="2.0", id=2, method="tools/call", params=dict(name="skill_acquire", arguments=dict(id=want)))]
        result = subprocess.run([server["command"], *server["args"]], capture_output=True, timeout=20,
                                input="".join(json.dumps(m) + "\n" for m in messages).encode())
        replies = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        final = replies[-1] if replies else {{}}
        record["acquire"] = {{"returncode": result.returncode, "ok": "result" in final and not final["result"].get("isError"),
                              "text": json.dumps(final.get("result"))[:400]}}
if os.environ.get("FAKE_RECOVERY_READ"):
    allowed = argv[argv.index("--allowed-tools") + 1].split(",") if "--allowed-tools" in argv else []
    rows = []
    for identifier, path in re.findall(r"^(apgr:[A-Za-z0-9._-]+): (/\S+/SKILL\.md)$", prompt, re.MULTILINE):
        rows.append({{"id": identifier, "path": path, "allowed": "Read(/" + path + ")" in allowed,
                      "sha256": hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()}})
    record["recovery"] = rows
if os.environ.get("FAKE_KEEP_PROMPT"):
    record["prompt"] = prompt
with open(os.environ["FAKE_CLAUDE_LOG"], "a", encoding="utf-8") as stream:
    stream.write(json.dumps(record) + "\n")
stage = re.search(r"^stage: ([a-z_]+)$", prompt, re.MULTILINE).group(1)
phase = re.search(r"<<<AGENT-PHASE-RESULT ([0-9a-f]{{32}})>>>", prompt)
review = re.search(r"<<<AGENT-REVIEW-RESULT ([0-9a-f]{{32}})>>>", prompt)
if phase:
    token = phase.group(1)
    payload = dict(version=1, stage=stage, outcome="completed", body="fake completed",
                   commit_message=dict(subject="Fake change", body=""))
    print(f"<<<AGENT-PHASE-RESULT {{token}}>>>\n{{json.dumps(payload)}}\n<<<END-AGENT-PHASE-RESULT {{token}}>>>")
elif review:
    token = review.group(1)
    payload = dict(version=1, stage=stage, outcome="reviewed_with_no_findings", body="fake review")
    print(f"<<<AGENT-REVIEW-RESULT {{token}}>>>\n{{json.dumps(payload)}}\n<<<END-AGENT-REVIEW-RESULT {{token}}>>>")
else:
    print(f"{{stage}} fake output")
'''


def built_binary() -> Path:
    value = os.environ.get("APG_CONTEXT_BINARY") or os.environ.get("APGR_GO_BINARY")
    if not value or not Path(value).is_file():
        pytest.skip("explicit built CLI binary required (APG_CONTEXT_BINARY)")
    return Path(value)


def git(cwd: Path, *arguments: str) -> None:
    subprocess.run(["git", *arguments], cwd=cwd, capture_output=True, check=True)


@pytest.fixture
def pilot(tmp_path, monkeypatch):
    """Disposable repository, APGR home, fake claude and built binary."""
    binary = built_binary()
    monkeypatch.setenv("APGR_GO_BINARY", str(binary))
    bindir = tmp_path / "fake-bin"
    bindir.mkdir()
    fake = bindir / "claude"
    fake.write_text(FAKE_CLAUDE.format(python=sys.executable))
    fake.chmod(0o700)
    monkeypatch.setenv("PATH", str(bindir) + os.pathsep + os.environ["PATH"])
    log = tmp_path / "fake-claude.jsonl"
    monkeypatch.setenv("FAKE_CLAUDE_LOG", str(log))
    for key in ("APGR_WORKER_FACADE", "APGR_DISPATCH_WORKERS", "APGR_PARENT_ID", "APGR_WORKER_STATE_DIR",
                "FAKE_ACQUIRE", "FAKE_RECOVERY_READ", "FAKE_KEEP_PROMPT", "APGR_DISPATCH_OBSERVATIONS"):
        monkeypatch.delenv(key, raising=False)
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "config", "user.name", "Test")
    (repo / "pyproject.toml").write_text('[project]\nname = "demo"\n[tool.pytest.ini_options]\naddopts = "-q"\n')
    (repo / "file.txt").write_text("one\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "initial")
    home = tmp_path / "home"
    home.mkdir()

    class Pilot:
        root = ROOT

        def configure(self, text: str | None) -> None:
            path = home / "config.toml"
            if text is None:
                path.unlink(missing_ok=True)
            else:
                path.write_text(text + "\n[integrations.rtk]\nenabled = false\n")

        def dispatch(self, phase="PILOT", lifecycle="standard", runs="runs"):
            log.unlink(missing_ok=True)
            dispatcher = Dispatcher(ROOT, repo, run_root=tmp_path / runs, claude_launcher=str(ROOT / "bin/claude-profile"),
                                    resolve_scanner=False, runner=production_run, apgr_home=home, project_root=repo)
            state = dispatcher.dispatch(phase, PhaseRequest("implementation_testing", "claude_only", "Implement it."),
                                        lifecycle=lifecycle, finalization_policy="checkpoint")
            calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
            return state, calls, Path(state["run_directory"])

    value = Pilot()
    value.repo, value.home, value.binary, value.tmp = repo, home, binary, tmp_path
    return value


def plans(run_dir: Path) -> dict[str, dict]:
    return {p.name.split(".")[0]: json.loads(p.read_bytes()) for p in sorted(run_dir.glob("*.context-plan.json"))}


def option(argv, name):
    return argv[argv.index(name) + 1] if name in argv else None


def selected(plan):
    return sorted(s["qualified_id"] for s in plan["prospective_plan"]["selected_snapshots"])


def test_five_stage_adaptive_route_reaches_native_child(pilot):
    pilot.configure('[dispatcher.context]\nmode = "adaptive"')
    state, calls, run_dir = pilot.dispatch()
    assert state["outcome"] == "completed"
    assert len(calls) == 5, "one fake native child per stage"
    records = plans(run_dir)
    assert sorted(records) == ["01-plan", "02-plan-review", "03-work", "04-final-review", "05-closeout"]
    expected_postures = {"01-plan": ["plan"], "02-plan-review": ["review"], "03-work": ["work"],
                         "04-final-review": ["review"], "05-closeout": ["work"]}
    work_class = {"plan": "apgr:planning-repository-work", "review": "apgr:reviewing-and-verifying-repository-work",
                  "work": "apgr:implementing-with-test-discipline"}
    for (prefix, record), call in zip(sorted(records.items()), calls):
        assert record["effective_mode"] == "adaptive", (prefix, record["reason"], record.get("diagnostic"))
        assert record["route_support"]["supported"] is True
        assert record["inputs"]["postures"] == expected_postures[prefix]
        posture = expected_postures[prefix][0]
        assert selected(record) == sorted([work_class[posture], "apgr:pytest-test-profile", "apgr:python-language-profile"])
        # Mandatory prompt bytes are byte-identical; the optional block follows.
        static_prompt = (run_dir / f"{prefix}.prompt.md").read_bytes()
        payload = record["prospective_plan"]["payload"].encode()
        assert payload.startswith(static_prompt) and payload != static_prompt
        assert call["skills_block"] is True
        assert call["prompt_sha256"] == record["transport"]["stdin"]["sha256"]
        argv = call["argv"]
        assert "--apgr-context-acquisition" not in argv
        assert option(argv, "--model") == "claude-opus-5-5" and option(argv, "--effort") == "high"
        assert "--add-dir" not in argv and "--dangerously-skip-permissions" not in argv
        # The real worker facade and the run-owned APGR server share one config.
        assert {"agent_worker", "apgr"} <= set(call["mcp_servers"])
        allowed = option(argv, "--allowed-tools").split(",")
        assert all(tool in allowed for tool in CONTEXT_TOOLS)
        assert "mcp__agent_worker__submit" in allowed
        if posture in ("plan", "review"):
            tools = option(argv, "--tools").split(",")
            assert tools[:5] == ["Read", "Glob", "Grep", "WebFetch", "WebSearch"]
            assert tools[-3:] == CONTEXT_TOOLS and "mcp__agent_worker__submit" in tools
            assert option(argv, "--permission-mode") == "default"
            assert "--strict-mcp-config" in argv
        else:
            assert "--tools" not in argv and "--permission-mode" not in argv
        assert not {"Bash", "Write", "Edit"} & set(allowed)
        transport = json.loads((run_dir / f"{prefix}.context-transport.json").read_bytes())
        assert transport["status"] == "runner_returned"
        assert (Path(record["acquisition"]["context_handoff"]).with_name(
            Path(record["acquisition"]["context_handoff"]).name + ".consumed")).is_file()


def _normalized(calls, run_dir):
    text = json.dumps([c["argv"] for c in calls]).replace(str(run_dir), "<RUN>")
    text = re.sub(r"[A-Z]+-dispatch--\d{8}T\d+Z", "<LEAF>", text)
    return re.sub(r"[0-9a-f]{64}", "<HEX>", text)


@pytest.mark.parametrize("variant", ["absent", "static", "adaptive_planner_broken", "static_observation_failure"])
def test_static_default_and_fallback_keep_original_transport(pilot, monkeypatch, variant):
    pilot.configure(None)
    _, baseline, baseline_run = pilot.dispatch(phase="BASE", runs="base-runs")
    if variant == "static":
        pilot.configure('[dispatcher.context]\nmode = "static"')
    elif variant == "adaptive_planner_broken":
        pilot.configure('[dispatcher.context]\nmode = "adaptive"')
        monkeypatch.setattr(context_adapter, "native_plan", lambda *a: (_ for _ in ()).throw(RuntimeError("absent")))
    elif variant == "static_observation_failure":
        from agent_phase import observations
        monkeypatch.setattr(observations, "write_event", lambda *a, **k: (_ for _ in ()).throw(OSError("full")))
    state, calls, run_dir = pilot.dispatch(phase="BASE", runs="variant-runs")
    assert state["outcome"] == "completed" and len(calls) == len(baseline) == 5
    assert _normalized(calls, run_dir) == _normalized(baseline, baseline_run)
    for prefix, record in plans(run_dir).items():
        assert record["effective_mode"] == "static"
        assert (run_dir / f"{prefix}.prompt.md").read_bytes().decode() and record["transport"]["stdin"]["sha256"] == \
            hashlib.sha256((run_dir / f"{prefix}.prompt.md").read_bytes()).hexdigest()
        if variant == "adaptive_planner_broken":
            assert record["reason"] == "optional_plan_failed" and "acquisition" not in record
    assert all(not c["skills_block"] and "apgr" not in c.get("mcp_servers", []) for c in calls)


def test_missing_persistent_binary_falls_back_with_reason(pilot, monkeypatch):
    pilot.configure('[dispatcher.context]\nmode = "adaptive"')
    monkeypatch.delenv("APGR_GO_BINARY")
    from agent_phase import context_route
    monkeypatch.setattr(context_route, "persistent_binary", lambda: (_ for _ in ()).throw(OSError("no binary")))
    # The planner itself still uses the explicit binary; only the persistent MCP executable is missing.
    original = context_adapter.native_plan

    def planner(request, capture):
        os.environ["APGR_GO_BINARY"] = str(pilot.binary)
        try:
            return original(request, capture)
        finally:
            os.environ.pop("APGR_GO_BINARY", None)
    monkeypatch.setattr(context_adapter, "native_plan", planner)
    state, calls, run_dir = pilot.dispatch(lifecycle="solo")
    assert state["outcome"] == "completed" and len(calls) == 1
    (record,) = plans(run_dir).values()
    assert record["effective_mode"] == "static" and record["reason"] == "acquisition_binary_unavailable"
    assert record["planned"] is True and not calls[0]["skills_block"]


def budget_config():
    return ('[dispatcher.context]\nmode = "adaptive"\nmanifest_facts = false\nmax_initial_context_bytes = 60000\n'
            'skills = ["apgr:dockerfile-profile", "apgr:vagrantfile-profile"]')


@pytest.mark.parametrize("channel", ["mcp", "recovery_read"])
def test_withheld_request_is_reachable_without_replay_or_permission_growth(pilot, monkeypatch, channel):
    pilot.configure(budget_config())
    if channel == "mcp":
        monkeypatch.setenv("FAKE_ACQUIRE", "apgr:vagrantfile-profile")
    else:
        monkeypatch.setenv("FAKE_RECOVERY_READ", "1")
    state, calls, run_dir = pilot.dispatch(lifecycle="solo")
    assert state["outcome"] == "completed" and len(calls) == 1
    (record,) = plans(run_dir).values()
    assert record["effective_mode"] == "adaptive", (record["reason"], record.get("diagnostic"))
    decisions = {d["selected_id"]: d for d in record["prospective_plan"]["decisions"]}
    assert decisions["apgr:dockerfile-profile"]["status"] == "selected"
    assert decisions["apgr:vagrantfile-profile"]["status"] == "deferred"
    assert decisions["apgr:vagrantfile-profile"]["reason"] == "required_closure_exceeds_budget"
    acquisition = record["acquisition"]
    assert "apgr:vagrantfile-profile" in acquisition["allowed_ids"]
    assert [r["id"] for r in acquisition["recovery"]] == ["apgr:vagrantfile-profile"]
    call = calls[0]
    assert "--add-dir" not in call["argv"] and "Bash" not in option(call["argv"], "--allowed-tools")
    body = (ROOT / "skills/vagrantfile-profile/SKILL.md").read_bytes()
    if channel == "mcp":
        assert call["acquire"]["ok"] is True, call["acquire"]
        from agent_phase.acquisition_records import records
        events = [r["event"] for r in records(run_dir, record["run_id"])]
        kinds = {e["kind"] for e in events if e["attempt_id"] == record["attempt_id"]}
        assert {"materialized", "response_delivered"} & kinds, kinds
    else:
        (row,) = call["recovery"]
        assert row["id"] == "apgr:vagrantfile-profile" and row["allowed"] is True
        assert row["sha256"] == hashlib.sha256(body).hexdigest()


def test_mandatory_overflow_is_static(pilot):
    pilot.configure('[dispatcher.context]\nmode = "adaptive"\nmax_initial_context_bytes = 100')
    state, calls, run_dir = pilot.dispatch(lifecycle="solo")
    (record,) = plans(run_dir).values()
    assert record["effective_mode"] == "static" and "mandatory_overflow" in record["reason"]
    assert not calls[0]["skills_block"] and "apgr" not in calls[0].get("mcp_servers", [])


def test_task_inputs_explicit_precedence_and_role_sensitive_requests(pilot):
    from agent_phase.context_inputs import scoped_task_inputs
    pilot.configure('[dispatcher.context]\nmode = "adaptive"\n'
                    'skills = [{id = "apgr:bats-test-profile", stages = ["review"]}, "project:absent-house-style"]\n'
                    '[dispatcher.context.facts]\nlanguage = ["go"]')
    with scoped_task_inputs([("test_framework", "go-native")], ["apgr:zsh-language-profile"]):
        state, calls, run_dir = pilot.dispatch()
    assert state["outcome"] == "completed"
    records = plans(run_dir)
    work = records["03-work"]
    facts = {(f["kind"], f["value"]): f for f in work["inputs"]["facts"]}
    assert facts[("language", "go")]["status"] == "supplied" and facts[("language", "go")]["source"] == "home"
    assert facts[("language", "python")]["status"] == "conflicting"
    assert facts[("test_framework", "go-native")]["source"] == "task"
    assert facts[("test_framework", "pytest")]["status"] == "conflicting"
    requests = {r["id"]: r for r in work["inputs"]["requests"]}
    assert requests["apgr:bats-test-profile"]["applies"] is False
    assert requests["apgr:zsh-language-profile"]["source"] == "task"
    assert "apgr:bats-test-profile" in selected(records["02-plan-review"])
    assert "apgr:bats-test-profile" not in selected(work)
    assert {"apgr:go-language-profile", "apgr:go-test-profile", "apgr:zsh-language-profile"} <= set(selected(work))
    unavailable = [d for d in work["prospective_plan"]["decisions"] if d["requested_id"] == "project:absent-house-style"]
    assert unavailable and unavailable[0]["status"] == "unavailable"
    assert not any(d["selected_id"] == "apgr:absent-house-style" for d in work["prospective_plan"]["decisions"])


def test_v2_claude_bindings_use_shared_seam(tmp_path, monkeypatch):
    from test_agent_phase_v2_full_execution import _init_repo, _repo_root, _make_v2_request_bytes, _make_closeout_output
    from agent_phase.request import parse_request_v2
    from agent_phase.v2_dispatch import dispatch_v2
    monkeypatch.setenv("APGR_GO_BINARY", str(built_binary()))
    repo = _init_repo(tmp_path / "repo")
    (repo / ".apgr").mkdir()
    (repo / ".apgr/config.toml").write_text('[dispatcher.context]\nmode="adaptive"\n')
    seen = {}

    def runner(*, run_id, binding, route, run_dir, prompt_bytes, argv, nonce):
        record = next(json.loads(p.read_bytes()) for p in run_dir.glob("*.context-plan.json")
                      if json.loads(p.read_bytes())["binding_id"] == binding.binding_id)
        seen[binding.binding_id] = (record, list(argv), prompt_bytes)
        if binding.binding_id == "binding_closeout":
            return _make_closeout_output(nonce)
        return None
    raw = _make_v2_request_bytes()
    result = dispatch_v2(_repo_root(), repo, parse_request_v2(raw), raw, execution_mode="gemini_sub",
                         apgr_home=tmp_path / "home", outbox_root=tmp_path / "outbox", runner=runner)
    assert result["status"] == "completed" and len(seen) == 5
    providers = {b: r["route_support"]["provider"] for b, (r, _, _) in seen.items()}
    assert "claude" in providers.values() and set(providers.values()) - {"claude"}, providers
    for binding, (record, argv, prompt) in seen.items():
        support = record["route_support"]
        if support["provider"] == "claude":
            assert support["supported"] is True
            assert record["effective_mode"] == "adaptive", (binding, record["reason"])
            assert "--apgr-context-acquisition" in argv
            assert prompt.decode().startswith(record["attempted_request"]["mandatory"][0]["text"])
        else:
            assert record["effective_mode"] == "static"
            assert record["reason"] == "route_unsupported:provider_not_in_pilot"
            assert record["planned"] is True
