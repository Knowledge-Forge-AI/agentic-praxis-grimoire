"""G controlled-channel conformance; instrumented actors are not live models."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import sqlite3
import subprocess

import pytest

from agent_phase import context_adapter
from agent_phase.acquisition_launch import AcquisitionLaunch, PROTOCOL
from agent_phase.acquisition_records import ingest, records, recovery_observation

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="session")
def binary(tmp_path_factory):
    value = os.environ.get("APG_ACQUISITION_BINARY")
    if value:
        assert Path(value).is_file(), "configured acquisition binary is missing"
        return value
    target = tmp_path_factory.mktemp("acquisition-build") / "apgr"
    result = subprocess.run(["go", "build", "-o", str(target), "./cmd/apgr"], cwd=ROOT,
                            capture_output=True, timeout=120, env={**os.environ, "GOPROXY": "off", "GOSUMDB": "off"})
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    return str(target)


def command(binary, run, *parts):
    return [binary, *parts, "--run-dir", str(run), "--run-id", "run", "--binding-id", "review", "--attempt-id", "attempt", "--consumer", "claude"]


def request(number, method, params=None):
    value = {"jsonrpc": "2.0", "id": number, "method": method}
    if params is not None:
        value["params"] = params
    return value


def initialize(version=PROTOCOL):
    return request(1, "initialize", {"protocolVersion": version, "capabilities": {}, "clientInfo": {"name": "fixture", "version": "1"}})


def rpc(binary, run, messages):
    wire = b"".join((json.dumps(value) + "\n").encode() if isinstance(value, dict) else value for value in messages)
    result = subprocess.run(command(binary, run, "mcp", "serve"), input=wire, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr
    return [json.loads(line) for line in result.stdout.splitlines()]


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.DEVNULL)


def subject(tmp_path):
    repo = tmp_path / "subject"
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / "source.go").write_text("package source\n")
    git(repo, "add", "source.go")
    git(repo, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture")
    return repo


def authority(repo):
    return (git(repo, "rev-parse", "HEAD"), (repo / ".git/index").read_bytes(),
            (repo / "source.go").read_bytes(), git(repo, "status", "--porcelain=v1", "--untracked-files=all"))


def scenario(number):
    return json.loads(next((ROOT / "testing/fixtures/context-eval").glob(f"scenario-{number}-*.json")).read_text())


def test_scenario10_cli_exact_materialization_repeat_and_index(binary, tmp_path):
    run = tmp_path / "run"; run.mkdir()
    fixture = scenario(10)
    skill = fixture["deliberately_withheld_skill"]["id"]
    result = subprocess.run(command(binary, run, "skills", "acquire", skill), capture_output=True, timeout=15)
    assert result.returncode == 0 and not result.stderr
    value = json.loads(result.stdout)
    body = base64.b64decode(value["selection"]["snapshot"]["body"])
    assert body == (ROOT / fixture["deliberately_withheld_skill"]["canonical_path"]).read_bytes()
    assert (run / value["materialized_path"] / "SKILL.md").read_bytes() == body
    again = subprocess.run(command(binary, run, "skills", "acquire", skill), capture_output=True, timeout=15)
    repeated = json.loads(again.stdout)
    assert repeated["event_id"] != value["event_id"] and repeated["is_repeat_delivery"]
    events = records(run, "run")
    delivered = [r["event"] for r in events if r["event"]["kind"] == "channel_delivered"]
    assert len(delivered) == 2 and sum(e["controlled_bytes"] for e in delivered) == len(result.stdout) + len(again.stdout)
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE artifacts (artifact_id TEXT PRIMARY KEY, run_id TEXT, artifact_name TEXT, relative_path TEXT, size_bytes INTEGER, sha256 TEXT, content_type TEXT, created_at TEXT)")
    assert ingest(conn, run, "run")["status"] == "indexed"
    assert ingest(conn, run, "run")["status"] == "indexed"
    assert conn.execute("SELECT count(*) FROM artifacts").fetchone()[0] == len(events)
    assert ingest(None, run, "run")["status"] == "failed"
    assert records(run, "run") == events


@pytest.mark.parametrize("number", [11, 14])
def test_mcp_frozen_readonly_acquisition(binary, tmp_path, number):
    fixture = scenario(number)
    repo = subject(tmp_path); before = authority(repo)
    run = tmp_path / "run"; run.mkdir()
    skill = fixture["acquisition"]["arguments"]["id"]
    argv, _, prepared = prepare(binary, run, candidates=[skill])
    assert prepared["record"]["effective_mode"] == "adaptive"
    tools = argv[argv.index("--tools") + 1].split(",")
    expected = {"mcp__apgr__skill_search", "mcp__apgr__skill_acquire", "mcp__apgr__context_explain"}
    assert set(tools) == {"Read", *expected}
    assert set(argv[argv.index("--allowed-tools")+1].split(",")) == expected
    launch = json.loads(Path(argv[argv.index("--mcp-config") + 1]).read_text())["mcpServers"]["apgr"]
    messages = [initialize(), {"jsonrpc": "2.0", "method": "notifications/initialized"},
        request(2, "tools/list"), request(3, "resources/templates/list"),
        request(4, "tools/call", {"name": "skill_acquire", "arguments": {"id": skill}}),
        request(5, "resources/read", {"uri": "apgr://skills/" + skill})]
    result = subprocess.run([launch["command"], *launch["args"]], input="".join(json.dumps(v)+"\n" for v in messages).encode(), cwd=repo, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr
    replies = [json.loads(line) for line in result.stdout.splitlines()]
    assert [t["name"] for t in replies[1]["result"]["tools"]] == ["skill_search", "skill_acquire", "context_explain"]
    assert len(replies[2]["result"]["resourceTemplates"]) == 2
    body = replies[3]["result"]["content"][0]["text"].encode()
    assert body == (ROOT / "skills" / skill.split(":")[1] / "SKILL.md").read_bytes()
    resource = json.loads(replies[4]["result"]["contents"][0]["text"])
    assert base64.b64decode(resource["selection"]["snapshot"]["body"]) == body
    assert authority(repo) == before
    assert "Bash" not in tools
    assert all(row["event"]["model_observed"] is None for row in records(run, "run"))


def prepare(binary, run, *, mode="adaptive", seam="claude-native-readonly", candidates=None):
    class Projection:
        acquisition = AcquisitionLaunch(binary=binary, catalog={"schema_version": "apg.skill-catalog/v1"},
            candidates=candidates or ["apgr:go-language-profile"], seam=seam, native_read_authorized=True)
        def qualification(self):
            return {"selective_projection": True, "independent_recovery": True, "evidence": "instrumented native argv fixture only"}
        def project(self, plan, argv, prompt):
            return argv, plan["payload"].encode()
    argv = ["instrumented-actor", "--tools", "Read"] if seam == "claude-native-readonly" else ["instrumented-actor", "-"]
    return context_adapter.prepare(capture={"settings": {"mode": mode}, "provenance": [], "overrides": [], "project_root": None, "apgr_home": "/absent"},
        run_dir=run, prefix="01-review", run_id="run", binding_id="review", attempt_id="attempt", roles=["work_review"],
        consumer="claude", argv=argv, prompt=b"Review only.", projection=Projection(),
        planner=lambda req, cap: {"effective_mode": "adaptive", "reasons": [], "payload": "Review only."})


def test_scenario12_midturn_failure_native_recovery_no_replay(binary, tmp_path):
    fixture = scenario(12)
    repo = subject(tmp_path); before = authority(repo)
    run = tmp_path / "run"; run.mkdir()
    argv, prompt, prepared = prepare(binary, run)
    assert prepared["record"]["effective_mode"] == "adaptive"
    tools = argv[argv.index("--tools") + 1].split(",")
    assert "Bash" not in tools and "Read" in tools and "mcp__apgr__skill_acquire" in tools
    launch = json.loads(Path(argv[argv.index("--mcp-config") + 1]).read_text())["mcpServers"]["apgr"]
    server = subprocess.Popen([launch["command"], *launch["args"]], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    calls = []
    def actor():
        calls.append(1)
        try:
            server.stdin.write((json.dumps(initialize()) + "\n").encode()); server.stdin.flush()
            assert json.loads(server.stdout.readline())["result"]["protocolVersion"] == PROTOCOL
            server.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
            # Close the response reader before a complete acquisition request.
            # The real engine accepts/materializes the request, then encounters
            # the injected broken transport while writing the tool response.
            server.stdout.close()
            server.stdin.write((json.dumps(request(2, "tools/call", {"name": "skill_acquire", "arguments": {"id": "apgr:go-language-profile"}})) + "\n").encode()); server.stdin.flush()
            assert server.wait(timeout=5) != 0
            observed = [row["event"] for row in records(run, "run") if row["event"]["channel"] == "mcp"]
            assert any(event["kind"] == "requested" for event in observed)
            assert not any(event["kind"] == "channel_delivered" for event in observed)
            recovery_observation(prepared, "mcp_failed", evidence="instrumented broken acquisition response transport")
            recovery = prepared["record"]["acquisition"]["recovery"][0]
            path = run / recovery["path"]
            assert str(path).encode() in prompt
            assert path.read_bytes() == (ROOT / fixture["withheld_skill"]["canonical_path"]).read_bytes()
            recovery_observation(prepared, "recovery_read_observed", controlled_bytes=len(path.read_bytes()), evidence="instrumented native read")
            assert ingest(None, run, "run")["status"] == "failed"
            return (0, b"Instrumented critique after native snapshot read", b"MCP terminated")
        finally:
            if server.poll() is None:
                server.kill(); server.wait(timeout=5)
            server.stdin.close(); server.stdout.close(); server.stderr.close()
    assert context_adapter.invoke(prepared, actor)[0] == 0
    assert calls == [1] and authority(repo) == before
    retained = json.loads(Path(prepared["record"]["acquisition"]["config"]).read_text())
    assert retained["context_plan"] == json.loads(prepared["path"].read_text())
    assert prepared["record"]["model_observed"] is None


@pytest.mark.parametrize("mode", ["static", "adaptive"])
def test_scenario13_missing_server_fallback(tmp_path, mode):
    argv, prompt, prepared = prepare(tmp_path / "missing", tmp_path, mode=mode)
    assert argv == ["instrumented-actor", "--tools", "Read"] and prompt == b"Review only."
    assert prepared["record"]["effective_mode"] == "static"
    assert not (tmp_path / "acquisitions").exists()


def test_codex_injection_is_additive(binary, tmp_path):
    argv, _, prepared = prepare(binary, tmp_path, seam="codex-native")
    assert argv[0] == "instrumented-actor" and argv[-1] == "-" and argv[1] == "-c"
    assert prepared["record"]["acquisition"]["live_provider_qualified"] is False


@pytest.mark.parametrize("wire", [b'{\n', b'[]\n', b'{"jsonrpc":"2.0","id":2,"id":3,"method":"ping"}\n'])
def test_real_protocol_malformed(binary, tmp_path, wire):
    reply = rpc(binary, tmp_path, [wire])[0]
    assert "error" in reply


def test_real_protocol_version_eof_bound_and_unknown_method(binary, tmp_path):
    replies = rpc(binary, tmp_path, [initialize("unsupported"), {"jsonrpc": "2.0", "method": "notifications/initialized"}, request(2, "shutdown")])
    assert replies[0]["result"]["protocolVersion"] == PROTOCOL
    assert replies[1]["error"]["code"] == -32601
    huge = subprocess.run(command(binary, tmp_path, "mcp", "serve"), input=b"x" * ((1 << 20) + 1), capture_output=True, timeout=10)
    assert huge.returncode != 0 and not huge.stdout and b"MCP_MESSAGE_TOO_LARGE" in huge.stderr
    eof = subprocess.run(command(binary, tmp_path, "mcp", "serve"), input=b"", capture_output=True, timeout=10)
    assert eof.returncode == 0 and not eof.stdout


@pytest.mark.parametrize("fault", ["wrong_revision", "malformed", "failed_start", "unexpected_exit"])
def test_prelaunch_faults_preserve_static_actor(binary, tmp_path, monkeypatch, fault):
    from agent_phase import acquisition_launch
    from types import SimpleNamespace
    real = acquisition_launch._capture
    def capture(argv, input_bytes=b""):
        if argv[1] == "skills":
            return real(argv, input_bytes)
        if fault == "failed_start":
            raise OSError("fixture start failure")
        if fault == "malformed":
            return SimpleNamespace(returncode=0, stdout=b'{"result":{},"result":{}}', stderr=b"")
        if fault == "unexpected_exit":
            return SimpleNamespace(returncode=7, stdout=b"", stderr=b"")
        return SimpleNamespace(returncode=0, stdout=b'{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"other"}}', stderr=b"")
    monkeypatch.setattr(acquisition_launch, "_capture", capture)
    argv, prompt, prepared = prepare(binary, tmp_path)
    assert argv == ["instrumented-actor", "--tools", "Read"] and prompt == b"Review only."
    assert prepared["record"]["effective_mode"] == "static"
    assert prepared["record"]["reason"] == "optional_plan_failed"
    assert all(row["event"]["channel"] == "preparation" for row in records(tmp_path, "run"))


def test_native_generation_contains_acquisition_owners(tmp_path):
    import shutil
    import sys
    from controller_generation_store import canonical_root_sha256, materialize
    fixture = tmp_path / "fixture"; fixture.mkdir()
    for name in ("__init__.py", "acquisition_launch.py", "acquisition_records.py", "context_adapter.py", "transmission.py", "claude_read_observer.py", "claude_acquisition_handoff.py", "claude_acquisition_argv.py", "claude_recovery_authority.py", "claude_acquisition_custody.py"):
        target = fixture / "libexec/agent_phase" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "libexec/agent_phase" / name, target)
    git(fixture, "init", "-q"); git(fixture, "add", "libexec")
    git(fixture, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture")
    store = tmp_path / "store" / canonical_root_sha256(fixture); store.parent.mkdir()
    generation = Path(materialize(fixture, store)["generation_root"])
    result = subprocess.run([sys.executable, "-c", "from agent_phase.acquisition_launch import PROTOCOL; from agent_phase.acquisition_records import records; from agent_phase import context_adapter, claude_acquisition_argv, claude_recovery_authority, claude_acquisition_custody; from agent_phase.claude_acquisition_handoff import TOOLS; from agent_phase.claude_read_observer import SCHEMA; assert len(TOOLS) == 3; assert SCHEMA == 'apg.claude-native-reads/v1'; assert PROTOCOL == '2025-11-25'"],
        cwd=tmp_path, env={**os.environ, "PYTHONPATH": str(generation / "libexec")}, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr


def test_failed_final_config_restores_measured_static_input(binary, tmp_path, monkeypatch):
    from agent_phase import acquisition_launch
    original = acquisition_launch._new
    def write(run, name, value):
        if name.startswith("acquisition-server-"):
            raise OSError("fixture final write failure")
        return original(run, name, value)
    monkeypatch.setattr(acquisition_launch, "_new", write)
    argv, prompt, prepared = prepare(binary, tmp_path)
    assert argv == ["instrumented-actor", "--tools", "Read"] and prompt == b"Review only."
    assert prepared["record"]["reason"] == "acquisition_config_failed"
    assert prepared["record"]["instruction_plan"]["runner_stdin"] == context_adapter.measured(prompt)


@pytest.mark.parametrize("fault", ["path_escape", "changed_snapshot"])
def test_prelaunch_verifies_recovery_bytes(binary, tmp_path, monkeypatch, fault):
    from agent_phase import acquisition_launch
    original = acquisition_launch._capture
    def capture(argv, input_bytes=b""):
        result = original(argv, input_bytes)
        if argv[1] == "skills":
            value = json.loads(result.stdout)
            if fault == "path_escape":
                value["materialized_path"] = "acquisitions/skills/../../outside"
                result.stdout = json.dumps(value).encode()
            else:
                (tmp_path / value["materialized_path"] / "SKILL.md").write_bytes(b"tampered fixture")
        return result
    monkeypatch.setattr(acquisition_launch, "_capture", capture)
    argv, prompt, prepared = prepare(binary, tmp_path)
    assert prepared["record"]["effective_mode"] == "static"
    assert argv == ["instrumented-actor", "--tools", "Read"] and prompt == b"Review only."


def test_prelaunch_is_not_agent_delivery(binary, tmp_path):
    argv, _, prepared = prepare(binary, tmp_path)
    events = [row["event"] for row in records(tmp_path, "run")]
    assert events and all(event["channel"] == "preparation" for event in events)
    assert not any(event["kind"] in ("requested", "channel_delivered") for event in events)
    launch = json.loads(Path(argv[argv.index("--mcp-config") + 1]).read_text())["mcpServers"]["apgr"]
    wire = [initialize(), {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {"_meta": {}}},
            request(2, "tools/call", {"name": "skill_acquire", "arguments": {"id": "apgr:go-language-profile"}, "_meta": {}})]
    result = subprocess.run([launch["command"], *launch["args"]], input="".join(json.dumps(v)+"\n" for v in wire).encode(), capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr
    envelope = json.loads(json.loads(result.stdout.splitlines()[-1])["result"]["content"][1]["text"])
    assert envelope["is_repeat_delivery"] is False
    assert "--allowed-tools" in argv
    assert set(argv[argv.index("--allowed-tools")+1].split(",")) == {"mcp__apgr__skill_search", "mcp__apgr__skill_acquire", "mcp__apgr__context_explain"}


@pytest.mark.parametrize("payload", [b'{', b'{}', b'[]'])
def test_optional_corrupt_event_does_not_block_collection(tmp_path, payload):
    (tmp_path / "state.json").write_text(json.dumps({"run_id": "run"}))
    store = tmp_path / "acquisitions"; store.mkdir()
    (store / ("event-" + "a"*64 + ".jsonl")).write_bytes(payload)
    with pytest.warns(RuntimeWarning, match="optional acquisition"):
        assert context_adapter.retained_records(tmp_path, "01-review", "review") == []
    assert (store / ("event-" + "a"*64 + ".jsonl")).read_bytes() == payload


def test_recovery_event_failed_sync_never_publishes(binary, tmp_path, monkeypatch):
    _, _, prepared = prepare(binary, tmp_path)
    before = records(tmp_path, "run")
    def fail_sync(fd):
        raise OSError("injected interrupted write")
    monkeypatch.setattr(os, "fsync", fail_sync)
    with pytest.raises(OSError, match="interrupted"):
        recovery_observation(prepared, "mcp_failed", evidence="fixture")
    assert records(tmp_path, "run") == before
    assert not list((tmp_path / "acquisitions").glob(".pending-*"))


def test_missing_event_scope_is_diagnostic(tmp_path):
    store = tmp_path / "acquisitions"; store.mkdir()
    name = "event-" + "a"*64 + ".jsonl"
    (store / name).write_text(json.dumps({"schema": "apg.acquisition-event/v1", "event_id": "a"*64, "run_id": "run"}))
    diagnostics = []
    assert records(tmp_path, "run", diagnostics=diagnostics) == []
    assert len(diagnostics) == 1
