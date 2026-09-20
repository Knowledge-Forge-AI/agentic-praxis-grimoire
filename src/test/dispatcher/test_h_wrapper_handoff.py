"""Instrumented profile composition; no model or holdout invocation."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from agent_phase import context_adapter, provider
from agent_phase.acquisition_launch import AcquisitionLaunch
from agent_phase.claude_acquisition_handoff import OPTION, TOOLS, consume, identity
from agent_phase.transmission import Transport, SCOPE_ENV
from test_agent_phase_acquisition import binary

ROOT = Path(__file__).resolve().parents[3]


def prepared_launch(binary, tmp_path, scope=None):
    run = tmp_path / "run"
    run.mkdir()
    class Projection:
        acquisition = AcquisitionLaunch(binary=binary, catalog={"schema_version": "apg.skill-catalog/v1"},
            candidates=["apgr:go-language-profile"], seam="claude-profile-readonly", native_read_authorized=True)
        def qualification(self):
            return {"selective_projection": True, "independent_recovery": True, "evidence": "instrumented only"}
        def project(self, plan, argv, prompt):
            return argv, plan["payload"].encode()
    argv = provider.build_argv(provider.Endpoint("claude", "normal-final-review"), "reviewer", ROOT)
    argv, prompt, prepared = context_adapter.prepare(
        capture={"settings": {"mode": "adaptive"}, "provenance": [], "overrides": [], "apgr_home": "/absent"},
        run_dir=run, prefix="one", **(scope or dict(run_id="run", binding_id="review", attempt_id="attempt")), roles=["Work Review"],
        consumer="claude", argv=argv, prompt=b"Instrumented sentinel only.", projection=Projection(),
        planner=lambda req, cap: {"effective_mode": "adaptive", "reasons": [], "payload": "Instrumented sentinel only."})
    assert prepared["record"]["effective_mode"] == "adaptive", prepared["record"].get("diagnostic")
    return argv, prompt, prepared


def environment(argv, prepared):
    return Transport(prepared).environment(argv, {})


def test_scope_config_and_one_use(binary, tmp_path):
    argv, _, prepared = prepared_launch(binary, tmp_path)
    path = argv[argv.index(OPTION) + 1]
    assert "--tools" not in argv and "--mcp-config" not in argv
    env = environment(argv, prepared)
    result = consume(path, env)
    assert result["tools"] == ["Read", *TOOLS]
    assert result["allowed_tools"] == TOOLS
    with pytest.raises(FileExistsError):
        consume(path, env)


@pytest.mark.parametrize("change", ["missing", "run", "binding", "attempt", "digest", "config", "symlink", "escape", "tool", "server"])
def test_refusals(binary, tmp_path, change):
    argv, _, prepared = prepared_launch(binary, tmp_path)
    path = Path(argv[argv.index(OPTION) + 1])
    env = environment(argv, prepared)
    scope = json.loads(env[SCOPE_ENV])
    value = json.loads(path.read_bytes())
    if change == "missing": env = {}
    elif change in ("run", "binding", "attempt"):
        scope["record"][change + "_id"] = "another"
    elif change == "digest": scope["handoff"]["sha256"] = "0" * 64
    elif change == "config": Path(value["config"]["path"]).write_text("{}")
    elif change == "symlink":
        renamed = path.with_suffix(".saved"); path.rename(renamed); path.symlink_to(renamed)
    elif change == "escape": path = path.parent / ".." / "run" / path.name
    elif change in ("tool", "server"):
        if change == "tool": value["tools"].append("Bash")
        else:
            config = Path(value["config"]["path"])
            config.write_text(json.dumps({"mcpServers": {"other": {"command": "/bin/true"}}}))
            value["config"].update(identity(config.read_bytes()))
        path.write_text(json.dumps(value)); scope["handoff"].update(identity(path.read_bytes()))
    if change != "missing": env[SCOPE_ENV] = json.dumps(scope)
    with pytest.raises((ValueError, OSError)):
        consume(str(path), env)


def test_real_profile_native_argv(binary, tmp_path, monkeypatch):
    from testing.h_eval import claude_reads
    argv, prompt, prepared = prepared_launch(binary, tmp_path)
    argv = claude_reads.prepare(prepared, argv)
    bindir = tmp_path / "bin"; bindir.mkdir()
    fake = bindir / "claude"
    fake.write_text("#!" + sys.executable + "\nimport sys,json\nsys.stdin.read()\nprint(json.dumps(dict(type='result',subtype='success',result=json.dumps(sys.argv[1:]))))\n")
    fake.chmod(0o700)
    env = {**os.environ, **environment(argv, prepared), "PATH": str(bindir) + os.pathsep + os.environ["PATH"]}
    env.pop("AGENT_CENTRAL_WORKER_FACADE", None)
    result = subprocess.run(argv, input=prompt, capture_output=True, env=env, timeout=30)
    assert result.returncode == 0, result.stderr.decode()
    native = json.loads(json.loads(result.stdout)["result"])
    assert OPTION not in native
    assert native[native.index("--tools") + 1].split(",") == ["Read", *TOOLS]
    assert native[native.index("--allowed-tools") + 1].split(",") == TOOLS
    assert native.count("--mcp-config") == 1 and native.count("--strict-mcp-config") == 1
    assert native[native.index("--setting-sources") + 1] == ""
    assert native[native.index("--permission-mode") + 1] == "default"
    assert native.count("--add-dir") == 1
    assert native[native.index("--add-dir") + 1] == str(prepared["path"].parent / "acquisitions/skills")
    assert not {"Bash", "Write", "Edit", "Agent"} & set(native[native.index("--tools") + 1].split(","))


@pytest.mark.parametrize("option", ["--tools", "--allowed-tools", "--allowedTools", "--mcp-config", "--strict-mcp-config"])
def test_readonly_owner_rejects_raw_override(option):
    from claude_vc_profile import reject_profile_overrides, reject_read_only_overrides, ProfileError
    with pytest.raises(ProfileError):
        reject_read_only_overrides([option, "arbitrary"])


@pytest.mark.parametrize("option", ["--model", "--effort", "--settings", "--managed-settings", "--permission-mode", "--add-dir"])
def test_profile_owner_rejects_raw_override(option):
    from claude_vc_profile import reject_profile_overrides, ProfileError
    with pytest.raises(ProfileError):
        reject_profile_overrides("normal-sysadmin-plan-review", [option, "arbitrary"])


@pytest.mark.parametrize("surface", ["valid", "missing", "extra_tool", "permission", "server"])
def test_instrumented_profile_mcp_and_repeated_read(binary, tmp_path, monkeypatch, surface):
    from testing.h_eval import claude_reads
    from agent_phase.acquisition_records import records, delivery_entries
    argv, prompt, prepared = prepared_launch(binary, tmp_path)
    bindir = tmp_path / "bin"; bindir.mkdir()
    fake = bindir / "claude"
    fake.write_text("#!" + sys.executable + r'''
import json, sys, pathlib, subprocess
sys.stdin.read()
config=json.loads(pathlib.Path(sys.argv[sys.argv.index('--mcp-config')+1]).read_bytes())['mcpServers']['apgr']
authority=json.loads(pathlib.Path(config['args'][-1]).read_bytes())
path=pathlib.Path(authority['run_dir']) / authority['context_plan']['acquisition']['recovery'][0]['path']
assert sys.argv.count('--add-dir') == 1
allowed=pathlib.Path(sys.argv[sys.argv.index('--add-dir')+1])
assert allowed == pathlib.Path(authority['run_dir']) / 'acquisitions/skills'
assert path.is_relative_to(allowed) and not path.is_relative_to(pathlib.Path.cwd())
def emit(value): print(json.dumps(dict(session_id='instrumented',**value)),flush=True)
def use(name,tid,args): emit(dict(type='assistant',message=dict(content=[dict(type='tool_use',name=name,id=tid,input=args)])))
def result(tid,content,structured): emit(dict(type='user',message=dict(content=[dict(type='tool_result',tool_use_id=tid,content=content)]),tool_use_result=structured))
emit(dict(type='system',subtype='init',model='instrumented',permissionMode='default',tools=['Read','mcp__apgr__skill_search','mcp__apgr__skill_acquire','mcp__apgr__context_explain'],mcp_servers=[dict(name='apgr',status='connected',source='dynamic')]))
messages=[dict(jsonrpc='2.0',id=1,method='initialize',params=dict(protocolVersion='2025-11-25',capabilities={},clientInfo=dict(name='instrumented',version='1'))),dict(jsonrpc='2.0',method='notifications/initialized'),dict(jsonrpc='2.0',id=2,method='tools/call',params=dict(name='context_explain',arguments={}))]
use('mcp__apgr__context_explain','mcp1',{})
r=subprocess.run([config['command'],*config['args']],input=''.join(json.dumps(m)+'\n' for m in messages).encode(),capture_output=True,check=True,timeout=15)
responses=[json.loads(l) for l in r.stdout.splitlines()]
assert len(responses)==2 and 'result' in responses[1]
result('mcp1',json.dumps(responses[1]['result']),responses[1]['result'])
use('Read','read1',dict(file_path=str(path)))
text=path.read_text(); lines=len(text.splitlines())
result('read1',text,dict(type='text',file=dict(filePath=str(path),content=text,startLine=1,numLines=lines,totalLines=lines)))
use('Read','read2',dict(file_path=str(path)))
result('read2','Wasted call — file unchanged since your last Read. Refer to that earlier tool_result instead.',dict(type='file_unchanged',file=dict(filePath=str(path))))
emit(dict(type='result',subtype='success',is_error=False,result='INSTRUMENTED_ONLY'))
''')
    source = fake.read_text()
    if surface == "missing":
        source = "\n".join(line for line in source.splitlines() if not line.startswith("emit(dict(type='system'")) + "\n"
    elif surface == "extra_tool": source = source.replace("tools=['Read',", "tools=['Bash','Read',")
    elif surface == "permission": source = source.replace("permissionMode='default'", "permissionMode='plan'")
    elif surface == "server": source = source.replace("name='apgr',status", "name='other',status")
    fake.write_text(source)
    fake.chmod(0o700)
    monkeypatch.setenv("PATH", str(bindir) + os.pathsep + os.environ["PATH"])
    monkeypatch.delenv("AGENT_CENTRAL_WORKER_FACADE", raising=False)
    argv = claude_reads.prepare(prepared, argv)
    subject = tmp_path / "subject"; subject.mkdir()
    returned = context_adapter.invoke(prepared, provider.run, argv, prompt, subject,
                                      liveness_policy=provider.LivenessPolicy(outer_ceiling_seconds=30, advisory_silence_seconds=None))
    assert returned.exit_code == 0, returned.stderr.decode()
    if surface != "valid":
        with pytest.raises(ValueError, match="runtime acquisition"):
            claude_reads.collect(prepared, returned)
        return
    observed = claude_reads.collect(prepared, returned)
    assert len(observed["reads"]) == 2 and len(observed["events"]) == 1
    trace = json.loads((prepared["path"].parent / "one.context-deliveries.json").read_bytes())
    events = [r["event"] for r in records(prepared["path"].parent, "run")]
    bridge = delivery_entries([*trace["events"], *events, *observed["events"]],run_id="run",binding_id="review",attempt_id="attempt")
    assert trace["coverage"] == bridge["coverage"] == "complete"
    assert any(e["phase"] == "late" and e["channel"] != "recovery_read" for e in bridge["deliveries"])
    assert sum(e["channel"] == "recovery_read" for e in bridge["deliveries"]) == 1
