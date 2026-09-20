"""Synthetic native stream contracts; these cases never launch a live model."""
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from agent_phase.claude_read_observer import observe, capture_recovery, digest
from agent_phase.acquisition_records import delivery_entries
from testing.h_eval import claude_reads

SCOPE = dict(run_id="run", binding_id="review", attempt_id="one")


def encoded(events):
    return b"".join((json.dumps(e, ensure_ascii=False) + "\n").encode() for e in events)


@pytest.fixture
def case(tmp_path):
    path = tmp_path / "snapshots/skills/sentinel/SKILL.md"
    path.parent.mkdir(parents=True)
    payload = "sentinel é\nsecond line\n".encode()
    path.write_bytes(payload)
    row = dict(id="probe:sentinel", path=str(path.relative_to(tmp_path)),
               bytes=len(payload), sha256=digest(payload))
    prepared = dict(path=tmp_path / "one.context-plan.json", record={**SCOPE, "acquisition": {"recovery": [row]}},
                    reference={"path": "one.context-plan.json", "sha256": "a" * 64})
    use = dict(type="assistant", session_id="session", message={"content": [
        dict(type="tool_use", id="read1", name="Read", input={"file_path": str(path)}, caller={"type": "direct"})]})
    result = dict(type="user", session_id="session", message={"content": [
        dict(type="tool_result", tool_use_id="read1", content="1→sentinel é\n2→second line")]},
        tool_use_result={"type": "text", "file": dict(filePath=str(path), content=payload.decode(),
                                                      numLines=2, startLine=1, totalLines=2)})
    terminal = dict(type="result", subtype="success", session_id="session", is_error=False, result="DONE")
    return prepared, [use, result, terminal]


def parse(case, events=None, raw=None):
    prepared, default = case
    raw = encoded(default if events is None else events) if raw is None else raw
    return observe(raw, expected_sha256=digest(raw), captured=capture_recovery(prepared), scope=SCOPE)


def test_complete_visible_and_raw_separate_and_bridge(case):
    value = parse(case)
    read = value["reads"][0]
    assert read["caller"] == {"type": "direct"}
    assert read["caller_metadata"] == {"type": "direct"}
    assert read["input"] == case[1][0]["message"]["content"][0]["input"]
    assert read["result"]["visible_identity"] != read["result"]["raw_identity"]
    event = value["events"][0]
    assert event["observation_kind"] == "claude_stream_read"
    assert event["controlled_bytes"] == read["result"]["raw_identity"]["bytes"]
    assert event["provider_observed"] is event["model_observed"] is None
    bridge = delivery_entries(value["events"] * 2, **SCOPE)
    assert bridge["coverage"] == "complete" and len(bridge["deliveries"]) == 1


def test_multiple_repeated_and_unrelated_reads(case, tmp_path):
    use, result, terminal = copy.deepcopy(case[1])
    use["message"]["content"][0]["id"] = "read2"
    result["message"]["content"][0]["tool_use_id"] = "read2"
    other_use, other_result = copy.deepcopy([use, result])
    other_use["message"]["content"][0].update(id="other", input={"file_path": str(tmp_path / "other")})
    other_result["message"]["content"][0]["tool_use_id"] = "other"
    other_result["tool_use_result"]["file"]["filePath"] = str(tmp_path / "other")
    value = parse(case, [*case[1][:2], use, result, other_use, other_result, terminal])
    assert len(value["reads"]) == 3 and len(value["events"]) == 2
    assert len({e["event_id"] for e in value["events"]}) == 2
    assert parse(case, [*case[1][:2], use, result, other_use, other_result, terminal]) == value


def test_unrelated_tool_and_additive_event_and_no_read(case):
    use, result, terminal = copy.deepcopy(case[1])
    use["message"]["content"][0]["name"] = "Glob"
    result.pop("tool_use_result")
    assert parse(case, [dict(type="rate_limit_event", status="ok"), use, result, terminal])["reads"] == []
    assert parse(case, [terminal])["events"] == []


@pytest.mark.parametrize("mutation", [
    "before", "missing", "duplicate_use", "duplicate_result", "error", "content", "requested_path",
    "structured_path", "offset", "limit", "pages", "raw", "start", "count", "line_type", "unknown_envelope",
    "session", "missing_terminal", "after_terminal", "structured_type", "missing_raw", "missing_session",
])
def test_bad_read_fails_closed(case, mutation):
    events = copy.deepcopy(case[1])
    use = events[0]["message"]["content"][0]
    result = events[1]["message"]["content"][0]
    file = events[1]["tool_use_result"]["file"]
    if mutation == "before": events[:2] = reversed(events[:2])
    elif mutation == "missing": events.pop(1)
    elif mutation == "duplicate_use": events.insert(1, copy.deepcopy(events[0]))
    elif mutation == "duplicate_result": events.insert(2, copy.deepcopy(events[1]))
    elif mutation == "error": result["is_error"] = True
    elif mutation == "content": result["content"] = {}
    elif mutation == "requested_path": use["input"]["file_path"] += "-wrong"
    elif mutation == "structured_path": file["filePath"] += "-wrong"
    elif mutation in ("offset", "limit", "pages"): use["input"][mutation] = 1
    elif mutation == "raw": file["content"] += "wrong"
    elif mutation == "start": file["startLine"] = 2
    elif mutation == "count": file["numLines"] = 1
    elif mutation == "line_type": file["numLines"] = True
    elif mutation == "unknown_envelope": events[0]["type"] = "new-envelope"
    elif mutation == "session": events[1]["session_id"] = "other"
    elif mutation == "missing_session": events[1].pop("session_id")
    elif mutation == "missing_terminal": events.pop()
    elif mutation == "after_terminal": events.append(dict(type="system"))
    elif mutation == "structured_type": events[1]["tool_use_result"]["type"] = "image"
    elif mutation == "missing_raw": file.pop("content")
    with pytest.raises(ValueError): parse(case, events)


@pytest.mark.parametrize("raw", [b'{}\n', b'{"type":"system","type":"user"}\n', b'{"type":',
                                  b'\xff\n', b'[]\n', b'\n', b'{"type":"system","x":NaN}\n'])
def test_invalid_jsonl(case, raw):
    with pytest.raises((ValueError, UnicodeError)): parse(case, raw=raw)


def test_size_truncation_digest(case, monkeypatch):
    from agent_phase import claude_read_observer as owner
    raw = encoded(case[1])
    with pytest.raises(ValueError, match="truncated"): parse(case, raw=raw[:-1])
    with pytest.raises(ValueError, match="digest"):
        observe(raw, expected_sha256="b" * 64, captured={}, scope=SCOPE)
    monkeypatch.setattr(owner, "MAX_RECORD", 10)
    with pytest.raises(ValueError, match="oversized"): parse(case)
    monkeypatch.setattr(owner, "MAX_LOG", 10)
    with pytest.raises(ValueError, match="oversized"): parse(case)


def test_capture_authority_and_no_replay(case):
    prepared, _ = case
    argv = ["claude-profile", "normal-sysadmin-plan-review", "--read-only", "-p"]
    result = claude_reads.prepare(prepared, argv)
    assert result[:len(argv)] == argv and result[-2:] == ["--live-display", "raw"]
    with pytest.raises(ValueError, match="once"): claude_reads.prepare(prepared, argv)
    path = Path(next(iter(prepared["claude_read_capture"])))
    path.write_text("changed")
    with pytest.raises(ValueError, match="changed"): capture_recovery(prepared)


@pytest.mark.parametrize("read_snapshot", [True, False])
def test_durable_binding_and_recovery_gate(case, read_snapshot):
    from agent_phase.transmission import SCOPE_ENV
    from agent_phase.claude_read_observer import retain_completion
    from testing.h_eval.paired import require_recovery_coverage
    prepared, events = case
    if not read_snapshot:
        events = events[-1:]
    argv = claude_reads.prepare(prepared, ["claude-profile", "p", "--read-only", "-p"])
    path = Path(prepared["claude_read_stream"])
    path.write_bytes(encoded(events)); path.chmod(0o600)
    scope = dict(claude_read_stream=str(path), record=SCOPE, reference=prepared["reference"])
    env = {SCOPE_ENV: json.dumps(scope)}
    assert not retain_completion(env, path, complete=False)
    assert not path.with_suffix(".complete.json").exists()
    assert retain_completion(env, path, complete=True)
    returned = SimpleNamespace(stdout=path.read_bytes(), exit_code=0, truncated=False)
    observation = claude_reads.collect(prepared, returned)
    require_recovery_coverage("live", prepared, observation)
    assert len(observation["events"]) == int(read_snapshot)
    with pytest.raises(ValueError):
        require_recovery_coverage("live", prepared, {**observation, "scope": {**SCOPE, "attempt_id": "other"}})
    with pytest.raises(ValueError): require_recovery_coverage("live", prepared)
    path.write_bytes(path.read_bytes() + b'{}\n')
    with pytest.raises(ValueError, match="binding"): claude_reads.collect(prepared, returned)


@pytest.mark.parametrize("failure", [None, "nonzero", "signal", "timeout", "log_failure"])
def test_actual_profile_runner_raw_retention_and_archive(tmp_path, monkeypatch, failure):
    import os
    import sys
    import zipfile
    from agent_phase import provider, context_adapter
    from testing.h_eval.paired import _snapshot
    root = Path(__file__).resolve().parents[3]
    bindir = tmp_path / "bin"; bindir.mkdir()
    fake = bindir / "claude"
    fake.write_text("#!" + sys.executable + '''
import json,sys,pathlib
assert '--live-log' not in sys.argv and '--live-display' not in sys.argv
assert sys.argv[sys.argv.index('--output-format')+1] == 'stream-json'
assert 'Bash' not in sys.argv[sys.argv.index('--tools')+1].split(',')
assert sys.argv[sys.argv.index('--setting-sources')+1] == ''
value=json.loads(sys.stdin.read())
if value['failure'] == 'nonzero':
 print(json.dumps(dict(type='result', subtype='error', is_error=True, terminal_reason='api_error')), flush=True)
 sys.exit(7)
if value['failure'] == 'signal':
 import os,signal
 os.kill(os.getpid(),signal.SIGTERM)
if value['failure'] == 'timeout':
 import time
 time.sleep(60)
assert pathlib.Path(value['log']).exists(), 'raw log must exist before child start'
for event in value['events']: print(json.dumps(event), flush=True)
''')
    fake.chmod(0o700)
    monkeypatch.setenv("PATH", str(bindir) + os.pathsep + os.environ["PATH"])
    monkeypatch.delenv("AGENT_CENTRAL_WORKER_FACADE", raising=False)
    subject = tmp_path / "subject"; subject.mkdir()
    run = tmp_path / "run"; run.mkdir()
    sentinel = run / "snapshots/skills/sentinel/SKILL.md"; sentinel.parent.mkdir(parents=True)
    sentinel.write_text("sentinel\n")
    events = [
        dict(type="assistant", session_id="s", message={"content": [dict(type="tool_use", name="Read", id="one", input={"file_path": str(sentinel)})]}),
        dict(type="user", session_id="s", message={"content": [dict(type="tool_result", tool_use_id="one", content="1→sentinel")]},
             tool_use_result={"type": "text", "file": dict(filePath=str(sentinel), content="sentinel\n", startLine=1, numLines=1, totalLines=1)}),
        dict(type="result", session_id="s", subtype="success", is_error=False, result="DONE")]
    argv = provider.build_argv(provider.Endpoint("claude", "normal-final-review"), "reviewer", root)
    prompt = json.dumps(dict(log=str(run / "one.context-plan.claude-stream.jsonl"), events=events, failure=failure)).encode()
    argv, prompt, prepared = context_adapter.prepare(capture={"settings": {"mode": "static"}, "provenance": []},
        run_dir=run, prefix="one", run_id="run", binding_id="review", attempt_id="one", roles=["Work Review"],
        consumer="claude", argv=argv, prompt=prompt)
    # Instrumented authority only: not a live selective-projection qualification.
    prepared["record"]["acquisition"] = {"recovery": [dict(id="probe:sentinel", path=str(sentinel.relative_to(run)),
                                                           **__import__('agent_phase.claude_read_observer', fromlist=['identity']).identity(sentinel.read_bytes()))]}
    argv = claude_reads.prepare(prepared, argv)
    if failure == "log_failure":
        # Reproduce an unwritable log destination after admission, before launch.
        Path(prepared["claude_read_stream"]).mkdir()
    policy = provider.LivenessPolicy(outer_ceiling_seconds=1 if failure == "timeout" else 10,
                                     advisory_silence_seconds=None)
    if failure == "timeout":
        with pytest.raises(provider.ProviderLivenessExpired):
            context_adapter.invoke(prepared, provider.run, argv, prompt, subject, liveness_policy=policy)
        assert not Path(prepared["claude_read_stream"]).with_suffix(".complete.json").exists()
        return
    result = context_adapter.invoke(prepared, provider.run, argv, prompt, subject, liveness_policy=policy)
    if failure:
        assert result.exit_code != 0
        if failure == "nonzero": assert result.exit_code == 7
        if failure == "signal": assert result.exit_code == 143
        receipt_path = Path(prepared["claude_read_stream"]).with_suffix(".complete.json")
        if failure == "nonzero":
            receipt = json.loads(receipt_path.read_text())
            assert receipt["schema"] == "apg.claude-stream-completion/v2"
            assert receipt["process_status"] == 7
            assert b"live logging failed" not in result.stderr
        else:
            assert not receipt_path.exists()
        with pytest.raises(ValueError): claude_reads.collect(prepared, result)
        return
    assert result.exit_code == 0, result.stderr.decode()
    observation = claude_reads.collect(prepared, result)
    assert len(observation["events"]) == 1
    assert json.loads((run / "one.context-deliveries.json").read_bytes())["coverage"] == "complete"
    before = _snapshot(run)
    from agent_phase.archive import create
    archive = tmp_path / "evidence.zip"
    directory = SimpleNamespace(path=run, archive_path=archive, archive_temporary_path=tmp_path / "pending.zip", leaf="run")
    create(directory, purpose="APG166B-instrumented-native-read", required=())
    restored = tmp_path / "restored"
    with zipfile.ZipFile(archive) as z: z.extractall(restored)
    # The actual archive owner adds its manifest; every original byte survives.
    restored_files = _snapshot(restored / "run")
    restored_files.pop("TRANSPORT-MANIFEST.json")
    assert restored_files == before
    assert list(subject.iterdir()) == []
    with pytest.raises(ValueError, match="before launch"): claude_reads.prepare(prepared, argv)


@pytest.mark.parametrize("mutation", ["nested", "wire", "unknown_block", "missing_id", "bad_input", "relative",
                                      "no_message", "bad_blocks", "hidden_user", "ambiguous_results", "uuid"])
def test_envelope_ambiguity(case, mutation):
    events = copy.deepcopy(case[1])
    use = events[0]["message"]["content"][0]
    if mutation == "nested": events[0]["parent_tool_use_id"] = "other"
    elif mutation == "wire": events[0]["wire_tool_inputs"] = {"read1": {"file_path": "different", "offset": 1}}
    elif mutation == "unknown_block": use["type"] = "new_kind"
    elif mutation == "missing_id": use.pop("id")
    elif mutation == "bad_input": use["input"] = None
    elif mutation == "relative": use["input"]["file_path"] = "relative.md"
    elif mutation == "no_message": events[0].pop("message")
    elif mutation == "bad_blocks": events[0]["message"]["content"] = [{}]
    elif mutation == "hidden_user": events[1]["content"] = []
    elif mutation == "ambiguous_results": events[1]["message"]["content"] *= 2
    elif mutation == "uuid":
        for event in events: event["uuid"] = "duplicate"
    with pytest.raises(ValueError): parse(case, events)


def test_visible_text_blocks_wire_and_record_identity(case):
    events = copy.deepcopy(case[1])
    events[0]["uuid"] = "one"
    events[0]["wire_tool_inputs"] = {"read1": events[0]["message"]["content"][0]["input"]}
    events[1]["message"]["content"][0]["content"] = [{"type": "text", "text": "1→sentinel"}]
    value = parse(case, events)
    assert value["reads"][0]["record_id"] == "one"
    assert value["reads"][0]["result"]["visible_encoding"] == "json-text-blocks"


def test_read_scope_traversal_symlink_and_duplicate(case, tmp_path):
    prepared, _ = case
    row = prepared["record"]["acquisition"]["recovery"][0]
    original = dict(row)
    for path in ("../outside", "/outside", "snapshots//bad", "snapshots/./bad", "snapshots/../bad"):
        row["path"] = path
        with pytest.raises(ValueError): capture_recovery(prepared)
    row.update(original)
    prepared["record"]["acquisition"]["recovery"].append(dict(row))
    with pytest.raises(ValueError): capture_recovery(prepared)
    prepared["record"]["acquisition"]["recovery"].pop()
    path = prepared["path"].parent / row["path"]
    outside = tmp_path / "outside"; path.rename(outside); path.symlink_to(outside)
    with pytest.raises(ValueError): capture_recovery(prepared)


@pytest.mark.parametrize("argv", [["codex", "-p"], ["claude-profile", "p", "--read-only", "-p", "--output-format=json"],
                                  ["claude-profile", "p", "--read-only", "-p", "--live-log", "x"]])
def test_route_scope_refusal(case, argv):
    with pytest.raises(ValueError): claude_reads.prepare(case[0], argv)


def test_existing_log_refusal_and_durability_failure(case, monkeypatch):
    import os
    from agent_phase.claude_read_observer import retain_completion
    from agent_phase.transmission import SCOPE_ENV
    prepared, events = case
    argv = ["claude-profile", "p", "--read-only", "-p"]
    path = prepared["path"].with_suffix(".claude-stream.jsonl")
    path.write_bytes(encoded(events))
    with pytest.raises(ValueError, match="replay"): claude_reads.prepare(prepared, argv)
    env = {SCOPE_ENV: json.dumps(dict(claude_read_stream=str(path), reference=prepared["reference"], record=SCOPE))}
    path.chmod(0o644)
    assert not retain_completion(env, path, complete=True)
    path.chmod(0o600)
    monkeypatch.setattr(os, "fsync", lambda _: (_ for _ in ()).throw(OSError("durability failure")))
    assert not retain_completion(env, path, complete=True)
    assert not path.with_suffix(".complete.json").exists()
    assert retain_completion({}, path, complete=True)


def test_readiness_binds_probe_identity_and_never_h_gate():
    from testing.h_eval.readiness import make_seal, verify_seal
    root = Path(__file__).resolve().parents[3]
    # Synthetic schema qualification only; never retained as live readiness.
    proof = dict(probe_id="APG166B-PROBE-1", evidence_sha256="a" * 64, raw_stream_sha256="b" * 64,
                 cli_version="fixture", profile="normal-final-review", model="fixture", effort="high")
    seal = make_seal(root, proof)
    verify_seal(root, seal)
    assert not seal["prerequisites_ready"] and not seal["h_gate_established"]
    assert seal["blockers"] and "checkpoint" not in seal
    assert seal["live_pairs"] == seal["qualified_promotions"] == 0
    assert not make_seal(root)["prerequisites_ready"]
    with pytest.raises(ValueError): make_seal(root, {})
    with pytest.raises(ValueError): make_seal(root, {**proof, "profile": "other"})
    with pytest.raises(ValueError): make_seal(root, {**proof, "raw_stream_sha256": "bad"})
    seal["files"]["libexec/agent_phase/claude_read_observer.py"] = "0" * 64
    with pytest.raises(ValueError): verify_seal(root, seal)


@pytest.mark.parametrize("read_snapshot", [True, False])
def test_instrumented_live_branch_pair_import_bridge_and_resume(tmp_path, monkeypatch, read_snapshot):
    """Exercise live control flow using a fake CLI; never real H evidence."""
    import os
    import sys
    from test_h_pair_runner import inputs
    from testing.h_eval.paired import run_pair, read_pair
    from testing.h_eval.readiness import make_seal
    from agent_phase.claude_read_observer import identity
    config = inputs(tmp_path)
    fake = tmp_path / "claude"
    fake.write_text("#!" + sys.executable + '''
import json,sys,pathlib
text=sys.stdin.read()
def emit(event): print(json.dumps(dict(session_id='fake-session',**event)),flush=True)
emit(dict(type='system',subtype='init',claude_code_version='fixture',model='instrumented-model',permissionMode='plan',tools=['Read']))
if 'APGR late acquisition recovery:' in text:
 path=text.strip().splitlines()[-1]; raw=pathlib.Path(path).read_text()
 emit(dict(type='assistant',message={'content':[dict(type='tool_use',id='read',name='Read',input={'file_path':path})]}))
 emit(dict(type='user',message={'content':[dict(type='tool_result',tool_use_id='read',content='1→'+raw)]},tool_use_result={'type':'text','file':dict(filePath=path,content=raw,startLine=1,numLines=1,totalLines=1)}))
result=dict(schema='apg.instrumented-provider/v1',model='instrumented-model',producer_revisions=[],missing_guidance_findings=[],restart_required_incidents=[],model_observed=None)
emit(dict(type='result',subtype='success',is_error=False,result=json.dumps(result)))
''')
    if not read_snapshot:
        fake.write_text(fake.read_text().replace("if 'APGR late acquisition recovery:' in text:", "if False:"))
    fake.chmod(0o700)
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ["PATH"])
    monkeypatch.delenv("AGENT_CENTRAL_WORKER_FACADE", raising=False)
    for route in config["routes"].values():
        route.update(provider="claude", profile="normal-final-review", execution="live")
    config["executable_paths"] = {}
    config["capture"] = dict(settings={}, provenance=[], overrides=[], apgr_home=str(tmp_path))
    config["runtime_inputs"] = {}
    config["seal"] = make_seal(config["source_root"])
    with pytest.raises(ValueError, match="blocked"): run_pair(**config)
    proof = dict(probe_id="APG166B-PROBE-1", evidence_sha256="a" * 64, raw_stream_sha256="b" * 64,
                 cli_version="fixture", profile="normal-final-review", model="instrumented-model", effort="high")
    config["seal"] = make_seal(config["source_root"], proof)
    with pytest.raises(ValueError, match="blocked"): run_pair(**config)
    # Explicit test-only admission isolates the runner branch. The real seal
    # remains blocked: this stub cannot qualify an adaptive MCP launch.
    config["seal"]["prerequisites_ready"] = True
    monkeypatch.setattr("testing.h_eval.readiness.verify_seal", lambda *_: None)
    class Sentinel:
        def prepare(self, record, run, argv):
            path = run / "snapshots/skills/sentinel/SKILL.md"; path.parent.mkdir(parents=True)
            path.write_bytes(b"synthetic sentinel\n")
            return argv, {"recovery": [dict(id="probe:sentinel", path=str(path.relative_to(run)), **identity(path.read_bytes()))]}
        def finalize(self, record): pass
    config["projection"].acquisition = Sentinel()
    value = run_pair(**config)
    assert value["arms"]["static"]["exact_recovery"] == []
    assert len(value["arms"]["adaptive"]["exact_recovery"]) == int(read_snapshot)
    assert value["arms"]["adaptive"]["native_reads"]["read_count"] == int(read_snapshot)
    assert read_pair(config["pair_dir"]) == value
    with pytest.raises(FileExistsError): run_pair(**config)
    (config["pair_dir"] / "adaptive/run/attempt.context-plan.claude-stream.jsonl").unlink()
    with pytest.raises(ValueError): read_pair(config["pair_dir"])


def test_runtime_route_drift_rejected(case):
    from agent_phase.claude_read_observer import retain_completion
    from agent_phase.transmission import SCOPE_ENV
    prepared, events = case
    claude_reads.prepare(prepared, ["claude-profile", "p", "--read-only", "-p"],
                         qualification=dict(cli_version="fixture", model="fixture"))
    path = Path(prepared["claude_read_stream"])
    path.write_bytes(encoded(events)); path.chmod(0o600)
    scope = dict(claude_read_stream=str(path), record=SCOPE, reference=prepared["reference"])
    assert retain_completion({SCOPE_ENV: json.dumps(scope)}, path, complete=True)
    with pytest.raises(ValueError, match="runtime differs"):
        claude_reads.collect(prepared, SimpleNamespace(stdout=path.read_bytes(), exit_code=0, truncated=False))


@pytest.mark.parametrize("scope", [None, {}, {"claude_read_stream": None}, "malformed", [] , {"claude_read_stream": "requested"}])
def test_live_log_optional_observer_import_failure(tmp_path, scope):
    """A missing evaluation module must not crash completed ordinary launches."""
    import os
    import subprocess
    import sys
    script = '''
import builtins,json,os,sys
from pathlib import Path
from claude_vc_profile import run_live
from agent_phase.transmission import SCOPE_ENV
original=builtins.__import__
def guarded(name,*args,**kwargs):
 if name == 'agent_phase.claude_read_observer': raise ImportError('absent evaluation module')
 return original(name,*args,**kwargs)
builtins.__import__=guarded
env=dict(os.environ); env.pop(SCOPE_ENV,None)
scope=json.loads(sys.argv[2])
if scope is not None: env[SCOPE_ENV]=scope if isinstance(scope,str) else json.dumps(scope)
command=[sys.executable,'-c',"print('{\\\"type\\\":\\\"result\\\",\\\"subtype\\\":\\\"success\\\"}')"]
sys.exit(run_live(sys.executable,command,env,Path(sys.argv[1]),'raw','normal-final-review'))
'''
    result = subprocess.run([sys.executable, "-c", script, str(tmp_path / "raw.jsonl"), json.dumps(scope)],
                            capture_output=True, env=dict(os.environ), timeout=10)
    evaluation = isinstance(scope, dict) and scope.get("claude_read_stream") is not None
    assert result.returncode == int(evaluation), result.stderr.decode()
    assert b'Traceback' not in result.stderr
    assert (tmp_path / "raw.jsonl").read_bytes() == result.stdout


def test_repeated_read_stub_fails_closed(case):
    use, result, terminal = copy.deepcopy(case[1])
    use["message"]["content"][0]["id"] = "read2"
    result["message"]["content"][0]["tool_use_id"] = "read2"
    result["tool_use_result"] = {"type": "unchanged"}
    with pytest.raises(ValueError, match="structured text/file"):
        parse(case, [*case[1][:2], use, result, terminal])


def repeated_unchanged(case):
    first, full, terminal = copy.deepcopy(case[1])
    second = copy.deepcopy(first)
    second["message"]["content"][0]["id"] = "read2"
    repeated = copy.deepcopy(full)
    repeated["message"]["content"][0].update(tool_use_id="read2", content="Wasted call — file unchanged since your last Read. Refer to that earlier tool_result instead.")
    repeated["tool_use_result"] = {"type": "file_unchanged", "file": {"filePath": first["message"]["content"][0]["input"]["file_path"]}}
    return [first, full, second, repeated, terminal]


def test_current_cli_unchanged_has_observation_without_payload(case):
    result = parse(case, repeated_unchanged(case))
    assert len(result["reads"]) == 2 and len(result["events"]) == 1
    second = result["reads"][1]["result"]
    assert second["unchanged"] is True and second["new_controlled_payload_bytes"] == 0
    assert second["prior_full_tool_use_id"] == "read1"
    assert second["visible_content"] and second["raw_identity"] == result["reads"][0]["result"]["raw_identity"]
    assert sum(e["controlled_bytes"] for e in result["events"]) == second["raw_identity"]["bytes"]


@pytest.mark.parametrize("change", ["first", "path", "content", "session", "prior_partial", "prior_error", "shape", "alias", "concurrent", "symlink"])
def test_unchanged_incomplete_contract(case, change):
    events = repeated_unchanged(case)
    if change == "first": events = events[2:]
    elif change == "path": events[3]["tool_use_result"]["file"]["filePath"] += "other"
    elif change == "content": Path(events[0]["message"]["content"][0]["input"]["file_path"]).write_text("changed")
    elif change == "session": events[2]["session_id"] = "other-session"
    elif change == "prior_partial": events[1]["tool_use_result"]["file"]["numLines"] = 1
    elif change == "prior_error": events[1]["message"]["content"][0]["is_error"] = True
    elif change == "shape": events[3]["tool_use_result"]["extra"] = True
    elif change == "alias": events[3]["tool_use_result"]["type"] = "unchanged"
    elif change == "concurrent": events[1], events[2] = events[2], events[1]
    elif change == "symlink":
        p = Path(events[0]["message"]["content"][0]["input"]["file_path"])
        saved = p.with_suffix(".saved"); p.rename(saved); p.symlink_to(saved)
    with pytest.raises((ValueError, OSError)): parse(case, events)
