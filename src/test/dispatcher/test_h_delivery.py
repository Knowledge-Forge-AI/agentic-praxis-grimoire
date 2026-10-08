"""APG166A mechanism evidence only; no live provider or benefit observations."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest

from agent_phase import context_adapter, provider
from agent_phase.acquisition_records import delivery_entries, read_recovery, records
from test_agent_phase_acquisition import binary, command, prepare, initialize, request
from agentic_praxis_grimoire.acquisition import retain_authority, MAX_AUTHORITIES


def bridge(events):
    return delivery_entries(events, run_id="run", binding_id="review", attempt_id="attempt")


def test_real_cli_bridge_and_repeated_transmissions(binary, tmp_path):
    outputs = []
    for _ in range(2):
        result = subprocess.run(command(binary, tmp_path, "skills", "acquire", "apgr:go-test-profile"),
                                capture_output=True, check=True)
        outputs.append(result.stdout)
    events = [r["event"] for r in records(tmp_path, "run")]
    value = bridge(events + events)
    assert value["coverage"] == "complete"
    assert len(value["deliveries"]) == 2
    assert sorted(d["sha256"] for d in value["deliveries"]) == sorted(hashlib.sha256(b).hexdigest() for b in outputs)
    assert sum(d["bytes"] for d in value["deliveries"]) == sum(map(len, outputs))
    assert bridge(list(reversed(events))) == value


def test_legacy_missing_digest_and_conflicting_views_fail_closed(binary, tmp_path):
    subprocess.run(command(binary, tmp_path, "skills", "search", "go"), capture_output=True, check=True)
    events = [r["event"] for r in records(tmp_path, "run")]
    event = next(e for e in events if e["kind"] == "response_delivered")
    legacy = {k: v for k, v in event.items() if k != "payload_sha256"}
    assert bridge([legacy])["coverage"] == "incomplete"
    assert bridge([event, {**event, "controlled_bytes": 1}])["coverage"] == "incomplete"
    assert bridge([{**event, "channel": "preparation"}])["deliveries"] == []


def test_exact_mcp_frames_and_preparation_excluded(binary, tmp_path):
    argv, _, prepared = prepare(binary, tmp_path)
    assert bridge([r["event"] for r in records(tmp_path, "run")])["deliveries"] == []
    declaration = json.loads(Path(argv[argv.index("--mcp-config")+1]).read_bytes())["mcpServers"]["apgr"]
    messages = [initialize(), {"jsonrpc": "2.0", "method": "notifications/initialized"}, request(2, "tools/list")]
    result = subprocess.run([declaration["command"], *declaration["args"]],
                            input=b"".join((json.dumps(m)+"\n").encode() for m in messages), capture_output=True, check=True)
    deliveries = bridge([r["event"] for r in records(tmp_path, "run")])["deliveries"]
    assert sorted(d["sha256"] for d in deliveries) == sorted(hashlib.sha256(b).hexdigest() for b in result.stdout.splitlines(keepends=True))


def test_witnessed_recovery_only_and_short_read_handoff(binary, tmp_path):
    _, _, prepared = prepare(binary, tmp_path)
    relative = prepared["record"]["acquisition"]["recovery"][0]["path"]
    with pytest.raises(ValueError, match="incomplete"):
        read_recovery(prepared, relative, lambda data: len(data)-1)
    assert bridge([r["event"] for r in records(tmp_path, "run")])["deliveries"] == []
    observed = []
    def receive(data):
        observed.append(data)
        return len(data)
    read_recovery(prepared, relative, receive)
    read_recovery(prepared, relative, receive)
    deliveries = bridge([r["event"] for r in records(tmp_path, "run")])["deliveries"]
    assert len(deliveries) == 2 and all(d["channel"] == "recovery_read" and d["phase"] == "late" for d in deliveries)
    assert all(d["sha256"] == hashlib.sha256(observed[0]).hexdigest() for d in deliveries)
    with pytest.raises(ValueError):
        read_recovery(prepared, "../outside", receive)


def launch(tmp_path, *, argv=None, prompt=b"task \xc3\xa9", mode="static"):
    argv = argv or [sys.executable, "-c", "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())"]
    argv, prompt, prepared = context_adapter.prepare(
        capture={"settings": {"mode": mode}, "provenance": []}, run_dir=tmp_path, prefix="test",
        run_id="run", binding_id="review", attempt_id="attempt", roles=["work_review"],
        consumer="codex", argv=argv, prompt=prompt)
    return argv, prompt, prepared


def test_initial_actual_process_writes_and_argv_only_once(tmp_path):
    script = "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())"
    config = tmp_path / "mcp.json"; config.write_text('{"mcpServers":{}}\n')
    argv, prompt, prepared = launch(tmp_path, argv=[sys.executable, "-c", script, "developer_instructions=\"readonly\"", "--mcp-config", str(config)])
    assert not (tmp_path / "test.context-deliveries.json").exists()
    result = context_adapter.invoke(prepared, provider.run, argv, prompt, tmp_path)
    assert result.stdout == prompt
    trace = json.loads((tmp_path / "test.context-deliveries.json").read_bytes())
    assert trace["coverage"] == "complete" and trace["model_observed"] is None
    value = bridge(trace["events"] * 2)
    assert len(value["deliveries"]) == 3
    assert {d["channel"] for d in value["deliveries"]} == {"prompt", "instructions", "mcp_configuration"}
    assert sum(d["bytes"] for d in value["deliveries"]) == len(prompt) + len(argv[3].encode()) + config.stat().st_size
    config_event = next(e for e in trace["events"] if e["channel"] == "mcp_configuration")
    assert config_event["observation_kind"] == "process_path_handoff"


def test_mock_runner_and_failed_start_do_not_claim_transport(tmp_path):
    argv, prompt, prepared = launch(tmp_path)
    context_adapter.invoke(prepared, lambda *a: (0, b"", b""), argv, prompt, tmp_path)
    trace = json.loads((tmp_path / "test.context-deliveries.json").read_bytes())
    assert trace["coverage"] == "incomplete" and not trace["events"]


def test_observation_failure_preserves_static_availability(tmp_path, monkeypatch):
    argv, prompt, prepared = launch(tmp_path)
    monkeypatch.setattr(context_adapter, "_write_new", lambda *a: (_ for _ in ()).throw(OSError("unavailable")))
    assert context_adapter.invoke(prepared, provider.run, argv, prompt, tmp_path).stdout == prompt


@pytest.mark.parametrize("consumer,profile", [("claude", "normal-sysadmin-plan-review"), ("antigravity", "gemini-3.8-flash-high")])
def test_actual_repository_launcher_additions(tmp_path, monkeypatch, consumer, profile):
    root = Path(__file__).resolve().parents[3]
    fake_bin = tmp_path / "bin"; fake_bin.mkdir()
    executable = fake_bin / ("claude" if consumer == "claude" else "agy")
    executable.write_text("#!" + sys.executable + "\nimport sys,json\n"
                          "if '--version' in sys.argv: print('9.0.0'); sys.exit(0)\n"
                          "print(json.dumps({'type':'result','subtype':'success','result':'instrumented'}))\n")
    executable.chmod(0o700)
    monkeypatch.setenv("PATH", str(fake_bin) + os.pathsep + os.environ["PATH"])
    home = tmp_path / "operator"; (home / "claude").mkdir(parents=True)
    (home / "claude/settings.json").write_text("{}\n")
    monkeypatch.setenv("APGR_HOME", str(home))
    argv = provider.build_argv(provider.Endpoint(consumer, profile), "reviewer", root)
    argv, prompt, prepared = launch(tmp_path, argv=argv)
    prepared["evaluation_transport"] = True
    prepared["record"]["instruction_plan"]["components"] = [{"kind": "mandatory-instruction", "sha256": hashlib.sha256(prompt).hexdigest(), "bytes": len(prompt)}]
    context_adapter.invoke(prepared, provider.run, argv, prompt, tmp_path)
    trace = json.loads((tmp_path / "test.context-deliveries.json").read_bytes())
    assert trace["coverage"] == "complete", trace
    nested = json.loads((tmp_path / "test.context-launcher-deliveries.json").read_bytes())
    assert all(e["model_observed"] is None for e in nested["events"])
    prompts = [e for e in trace["events"] if e["channel"] == "prompt"]
    assert len(prompts) == 1
    if consumer == "claude":
        assert prompts[0]["controlled_bytes"] == len(prompt)
        assert {e["channel"] for e in trace["events"]} == {"instructions", "mcp_configuration", "prompt"}
        settings_event = next(e for e in trace["events"] if e.get("reference", "").endswith("settings.json"))
        assert settings_event["channel"] == "instructions"
    else:
        assert prompts[0]["controlled_bytes"] > len(prompt)
        assert prompts[0]["provenance"] == "rendered-native-argv"
        assert any(c["kind"] == "mandatory-instruction" for c in prompts[0]["components"])
        assert any(c["kind"] == "launcher-instructions-source-view" for c in prompts[0]["components"])


def test_launcher_reuses_exact_preflight_and_server_artifacts(binary, tmp_path):
    from agent_phase.acquisition_launch import AcquisitionLaunch
    record = {"run_id": "run", "binding_id": "review", "attempt_id": "attempt"}
    launch = AcquisitionLaunch(binary=binary, catalog={"schema_version": "apg.skill-catalog/v1"},
        candidates=["apgr:go-test-profile"], seam="claude-native-readonly", native_read_authorized=True)
    paths = None
    for _ in range(4):
        argv, info = launch.prepare(record, tmp_path, ["fixture", "--tools", "Read"])
        launch.finalize(record)
        current = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in tmp_path.glob("acquisition-*.json")}
        if paths is not None:
            assert current == paths
        paths = current
    assert len(paths) == 4  # prelaunch, MCP config, server canonical and alias
    assert not list(tmp_path.glob("acquisition-prelaunch-*"))


def test_parallel_authority_scopes_and_cap(tmp_path):
    def retain(n):
        scope = {"run_id": "run", "binding_id": f"binding-{n}", "attempt_id": "one"}
        alias = "acquisition-server-" + hashlib.sha256(str(n).encode()).hexdigest() + ".json"
        return retain_authority(tmp_path, scope, alias=alias)
    with ThreadPoolExecutor(max_workers=4) as pool:
        names = list(pool.map(retain, range(12)))
    assert len(set(names)) == 12
    assert {json.loads((tmp_path / n).read_bytes())["binding_id"] for n in names} == {f"binding-{i}" for i in range(12)}
    for i in range(MAX_AUTHORITIES - 24):
        retain_authority(tmp_path, {"extra": i})
    with pytest.raises(ValueError, match="retention limit"):
        retain_authority(tmp_path, {"excess": True})
    assert len(list(tmp_path.glob("acquisition-*.json"))) == MAX_AUTHORITIES
    assert retain(0) == names[0]


def test_killed_authority_writer_recovers_one_pending_file(tmp_path):
    script = """import os,sys
from pathlib import Path
from agentic_praxis_grimoire import acquisition
original = os.fsync
def stop(fd):
    print('pending', flush=True)
    import time
    time.sleep(60)
acquisition.os.fsync = stop
acquisition.retain_authority(Path(sys.argv[1]), {'attempt_id':'killed'})
"""
    child = subprocess.Popen([sys.executable, "-c", script, str(tmp_path)], stdout=subprocess.PIPE,
                             env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[3] / "src")})
    try:
        import selectors
        with selectors.DefaultSelector() as selector:
            selector.register(child.stdout, selectors.EVENT_READ)
            assert selector.select(10), "writer never reached pending boundary"
            assert child.stdout.readline() == b"pending\n"
        child.kill(); child.wait(timeout=5)
    finally:
        if child.poll() is None:
            child.kill(); child.wait(timeout=5)
        child.stdout.close()
    assert len(list(tmp_path.glob(".acquisition-authority.pending"))) == 1
    retained = retain_authority(tmp_path, {"attempt_id": "resumed"})
    assert json.loads((tmp_path / retained).read_bytes()) == {"attempt_id": "resumed"}
    assert not list(tmp_path.glob(".acquisition-authority.pending"))


def test_authority_symlink_and_conflicting_alias_refused(tmp_path):
    outside = tmp_path / "outside"; outside.mkdir()
    linked = tmp_path / "link"; linked.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        retain_authority(linked, {})
    alias = "acquisition-server-" + "a" * 64 + ".json"
    retain_authority(outside, {"attempt_id": "one"}, alias=alias)
    before = (outside / alias).read_bytes()
    with pytest.raises(ValueError, match="conflicting"):
        retain_authority(outside, {"attempt_id": "two"}, alias=alias)
    assert (outside / alias).read_bytes() == before


def test_v1_real_runner_emits_one_initial_prompt(tmp_path, monkeypatch):
    from agent_phase.dispatch import Dispatcher
    from agent_phase.envelope import render, Segment, SEGMENT_TASK_PROMPT
    from agent_phase.run import RunDirectory
    from test_agent_phase_v2_full_execution import _init_repo
    root = Path(__file__).resolve().parents[3]
    subject = _init_repo(tmp_path / "subject")
    home = tmp_path / "home"; home.mkdir()
    fake = tmp_path / "codex-fixture"
    fake.write_text("#!" + sys.executable + "\nimport sys\nsys.stdin.buffer.read()\nprint('instrumented')\n")
    fake.chmod(0o700)
    dispatcher = Dispatcher(root, subject, project_root=subject, apgr_home=home,
                            run_root=tmp_path / "runs", runner=provider.run,
                            resolve_scanner=False, codex_executable=str(fake))
    directory = RunDirectory(tmp_path / "runs", "mechanism", "work-reviewed")
    dispatcher._stage(directory, 1, "work_review", "01-work_review", "reviewer",
                      provider.Endpoint("codex", "default"), render([Segment(SEGMENT_TASK_PROMPT, "mechanism only")]),
                      None, read_only=True, worker_capability={"allowed": False})
    trace = json.loads((directory.path / "01-work_review.context-deliveries.json").read_bytes())
    assert trace["coverage"] == "complete"
    assert sum(e["channel"] == "prompt" for e in trace["events"]) == 1


def test_v2_instrumented_process_traces_survive_real_archive(tmp_path, monkeypatch):
    import zipfile
    from test_agent_phase_v2_full_execution import _init_repo, _repo_root, _make_v2_request_bytes, _make_closeout_output
    from agent_phase.request import parse_request_v2
    from agent_phase.v2_dispatch import dispatch_v2
    from agent_phase import probes
    version_executable = tmp_path / "provider-version-fixture"
    version_executable.write_text(
        f"#!{sys.executable}\nimport sys\n"
        "assert sys.argv[1:] == ['--version']\nprint('archive-fixture 1')\n")
    version_executable.chmod(0o700)
    version_probe = probes.probe_executable_version
    def bounded_version(provider, **kwargs):
        kwargs["executable_override"] = str(version_executable)
        return version_probe(provider, **kwargs)
    monkeypatch.setattr(probes, "probe_executable_version", bounded_version)
    repo = _init_repo(tmp_path / "repo")
    def runner(*, run_id, binding, route, run_dir, prompt_bytes, argv, nonce):
        # Instrumented executable, real APGR process owner and exact payload.
        provider.run([sys.executable, "-c", "import sys; sys.stdin.buffer.read()", *argv[1:]], prompt_bytes, repo)
        if binding.binding_id == "binding_closeout":
            return _make_closeout_output(nonce)
        return None
    raw = _make_v2_request_bytes()
    result = dispatch_v2(_repo_root(), repo, parse_request_v2(raw), raw, execution_mode="gemini_sub",
                         apgr_home=tmp_path / "home", outbox_root=tmp_path / "outbox", runner=runner)
    assert result["status"] == "completed"
    with zipfile.ZipFile(result["archive_path"]) as archive:
        names = [n for n in archive.namelist() if n.endswith(".context-deliveries.json")]
        assert len(names) == 5
        for name in names:
            trace = json.loads(archive.read(name))
            assert trace["coverage"] == "complete"
            assert sum(e["channel"] == "prompt" for e in trace["events"]) == 1


def test_native_selected_bodies_are_verified_component_views(binary, tmp_path, monkeypatch):
    monkeypatch.setenv("APGR_GO_BINARY", binary)
    class Projection:
        def qualification(self):
            return {"selective_projection": True, "independent_recovery": True, "evidence": "instrumented transport only"}
        def project(self, plan, argv, prompt):
            return argv, plan["payload"].encode()
    argv, prompt, prepared = context_adapter.prepare(
        capture={"settings": {"mode": "adaptive"}, "provenance": [], "overrides": [], "project_root": None, "apgr_home": str(tmp_path)},
        run_dir=tmp_path, prefix="selected", run_id="run", binding_id="review", attempt_id="attempt", roles=["work_review"],
        consumer="codex", argv=[sys.executable, "-c", "import sys; sys.stdin.buffer.read()"], prompt=b"Review task",
        facts=[{"kind": "language", "value": "go"}], projection=Projection())
    assert prepared["record"]["effective_mode"] == "adaptive"
    context_adapter.invoke(prepared, provider.run, argv, prompt, tmp_path)
    trace = json.loads((tmp_path / "selected.context-deliveries.json").read_bytes())
    assert trace["coverage"] == "complete"
    assert len(trace["events"]) == 1
    assert trace["events"][0]["controlled_bytes"] == len(prompt)
    views = [v for v in trace["events"][0]["components"] if v["kind"] == "selected-skill-source-view"]
    assert any(v["id"] == "apgr:go-language-profile" for v in views)


@pytest.mark.parametrize("signum", [15, 9])
def test_observed_claude_exec_preserves_signal_exit(tmp_path, signum):
    root = Path(__file__).resolve().parents[3]
    code = "from agent_phase.transmission import run_observed_inherited; import os,sys; sys.exit(run_observed_inherited(sys.executable,[sys.executable,'-c','import os; os.kill(os.getpid()," + str(signum) + ")'],dict(os.environ)))"
    result = subprocess.run([sys.executable, "-c", code], cwd=tmp_path,
                            env={**os.environ, "PYTHONPATH": str(root / "libexec")}, capture_output=True, timeout=10)
    assert result.returncode == -signum


def test_ordinary_static_does_not_enable_native_supervision(tmp_path):
    from agent_phase.transmission import Transport, SCOPE_ENV
    argv, _, prepared = launch(tmp_path, argv=["claude-profile", "fixture"])
    trace = Transport(prepared)
    assert SCOPE_ENV not in trace.environment(argv, {SCOPE_ENV: "unrelated"})
    prepared["evaluation_transport"] = True
    assert SCOPE_ENV in Transport(prepared).environment(argv, {})


def test_claude_settings_are_instruction_configuration(tmp_path):
    from agent_phase.transmission import Transport
    settings = tmp_path / "settings.json"
    settings.write_text('{"permissions":{"allow":["Read"]}}')
    argv, _, prepared = launch(tmp_path, argv=["fixture", "--settings", str(settings)])
    trace = Transport(prepared)
    trace.environment(argv, {})
    trace.process_started(argv)
    assert len(trace.events) == 1
    event = trace.events[0]
    assert event["channel"] == "instructions"
    assert event["payload_sha256"] == hashlib.sha256(settings.read_bytes()).hexdigest()
    assert event["observation_kind"] == "process_path_handoff"
