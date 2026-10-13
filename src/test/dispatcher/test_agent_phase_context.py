"""APG164 optional context boundary: transport observations are not model use."""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import pytest
from agent_phase import context_adapter as adapter
from agent_phase.context_config import capture_context_config
from agent_phase.config_routing import ConfigError, load_config_file


@pytest.fixture(autouse=True)
def isolated_provider_version_probes(tmp_path, monkeypatch):
    """Context fixtures must never inspect an installed provider executable."""
    import sys
    from agent_phase import probes

    executable = tmp_path / "provider-version-fixture"
    executable.write_text(
        f"#!{sys.executable}\nimport sys\n"
        "assert sys.argv[1:] == ['--version']\nprint('context-fixture 1')\n")
    executable.chmod(0o700)
    # v2 resolves executable identity before calling its injected runner.
    bindir = tmp_path / "fake-bin"
    bindir.mkdir()
    (bindir / "codex").symlink_to(executable)
    monkeypatch.setenv("PATH", str(bindir) + os.pathsep + os.environ["PATH"])
    original = probes.probe_executable_version

    def bounded(provider, **kwargs):
        kwargs["executable_override"] = str(executable)
        return original(provider, **kwargs)

    monkeypatch.setattr(probes, "probe_executable_version", bounded)


def built_context_binary(root):
    binary = Path(os.environ.get("APG_CONTEXT_BINARY", root / "build/apgr-context"))
    if not binary.is_file():
        pytest.skip("explicit built CLI qualification binary required")
    return binary


def capture(mode="static"):
    return {"settings": {"mode": mode}, "provenance": [], "overrides": [], "project_root": None, "apgr_home": "/missing"}


def prepare(tmp_path, config=None, **options):
    return adapter.prepare(capture=config or capture(), run_dir=tmp_path, prefix="01-work",
                           run_id="run", binding_id="work", attempt_id="att-1", roles=["work", "review"],
                           consumer="codex", argv=["provider", "--readonly"], prompt="task é".encode(), **options)


def test_static_does_not_call_optional(tmp_path):
    def fail(*args): raise AssertionError("optional facility used")
    argv, prompt, state = prepare(tmp_path, planner=fail)
    assert argv == ["provider", "--readonly"] and prompt == "task é".encode()
    before = state["path"].read_bytes()
    assert state["record"]["planned"] is False
    result = adapter.invoke(state, lambda: (0, b"result", b""))
    assert result[0] == 0 and state["path"].read_bytes() == before
    obs = json.loads((tmp_path/"01-work.context-transport.json").read_bytes())
    assert obs["transport_delivered"] is None and obs["model_observed"] is None
    assert obs["status"] == "runner_returned"


@pytest.mark.parametrize("reason", ["mandatory_overflow", "selective_projection_unqualified", "independent_recovery_unqualified"])
def test_adaptive_fallback_preserves_transport(tmp_path, reason):
    def planner(request, config):
        assert request["mandatory"][0]["text"] == "task é"
        return {"effective_mode": "static", "reasons": [reason]}
    argv, prompt, state = prepare(tmp_path, capture("adaptive"), planner=planner)
    assert prompt == "task é".encode() and argv[-1] == "--readonly"
    assert state["record"]["effective_mode"] == "static" and state["record"]["reason"] == reason


def test_optional_failure_write_failure_and_historical_readback(tmp_path, monkeypatch):
    def fail(*args): raise RuntimeError("optional failure")
    argv, prompt, state = prepare(tmp_path, capture("adaptive"), planner=fail)
    assert state["record"]["reason"] == "optional_plan_failed"
    old = state["path"].read_bytes()
    _, _, collision = prepare(tmp_path)
    assert collision["reference"] is None and state["path"].read_bytes() == old
    with pytest.raises(FileNotFoundError): adapter.invoke(state, lambda: (_ for _ in ()).throw(FileNotFoundError()))
    obs = json.loads((tmp_path/"01-work.context-transport.json").read_bytes())
    assert obs["status"] == "partial_or_unknown"


@pytest.mark.parametrize("value", ['mode="bad"', 'max_initial_context_bytes=-1', 'max_initial_context_bytes=true', 'unknown=1', 'max_initial_context_characters="1"'])
def test_closed_configuration_both_owners(tmp_path, value):
    from agentic_praxis_grimoire.config import load_config, ConfigError as PublicError
    p=tmp_path/"config.toml"; p.write_text("[dispatcher.context]\n"+value+"\n")
    with pytest.raises(ConfigError): load_config_file(p)
    with pytest.raises(PublicError): load_config(p)


def test_context_home_target_precedence_zero_and_capture(tmp_path, monkeypatch):
    project=tmp_path/"project"; (project/".git").mkdir(parents=True); (project/".apgr").mkdir()
    nested=project/"nested"; nested.mkdir(); selected=tmp_path/"selected";selected.mkdir()
    ambient=tmp_path/"ambient";ambient.mkdir();monkeypatch.setenv("APGR_HOME",str(ambient))
    (ambient/"config.toml").write_text('[dispatcher.context]\nmode="static"\n')
    (selected/"config.toml").write_text('[dispatcher.context]\nmode="adaptive"\nmax_initial_context_bytes=42\n')
    (project/".apgr/config.toml").write_text('[dispatcher.context]\nmax_initial_context_bytes=0\n')
    c=capture_context_config(start=nested,apgr_home=selected)
    assert c["settings"] == {"mode":"adaptive","max_initial_context_bytes":0}
    assert c["project_root"]==str(project) and len(c["provenance"])==2
    empty=tmp_path/"empty";empty.mkdir()
    assert capture_context_config(project_root=empty,start=nested,apgr_home=selected)["settings"]["max_initial_context_bytes"]==42


class Projection:
    def qualification(self): return {"selective_projection":True,"independent_recovery":True,"evidence":"fixture only"}
    def project(self, plan, argv, prompt): return argv, plan["payload"].encode()


def test_projection_reconciles_runner_payload_and_overhead(tmp_path):
    def planner(request, config):
        return {"effective_mode":"adaptive","reasons":[],"payload":request["mandatory"][0]["text"]+"\nskill"}
    c=capture("adaptive");c["settings"]["max_initial_context_bytes"]=1000
    argv,prompt,state=prepare(tmp_path,c,planner=planner,projection=Projection())
    assert state["record"]["effective_mode"]=="adaptive" and prompt.endswith(b"skill")
    assert state["record"]["controlled_total"]["bytes"]==len(adapter.canonical(argv))+len(prompt)
    smaller=tmp_path/"small";smaller.mkdir();c["settings"]["max_initial_context_bytes"]=len(prompt)
    argv,prompt,state=prepare(smaller,c,planner=planner,projection=Projection())
    assert state["record"]["reason"]=="transport_overhead_overflow" and prompt=="task é".encode()


@pytest.mark.parametrize("prior_bytes", [b"prior result", b"prior result \xff"] )
@pytest.mark.parametrize("provider", ["codex", "claude", "antigravity"])
@pytest.mark.parametrize("mode", ["static", "adaptive"])
@pytest.mark.parametrize("planner_state", ["missing", "native"])
def test_actual_v1_context_transport(tmp_path, monkeypatch, provider, mode, planner_state, prior_bytes):
    import time
    from agent_phase.dispatch import Dispatcher
    from agent_phase.envelope import render, Segment, SEGMENT_TASK_PROMPT, SEGMENT_PRIOR_MATERIAL
    from agent_phase.routing import Endpoint
    from agent_phase.run import RunDirectory
    from agent_phase.provider import Result
    root=Path(__file__).resolve().parents[3]
    from test_agent_phase_v2_full_execution import _init_repo
    target=_init_repo(tmp_path/"target");(target/".apgr").mkdir()
    (target/".apgr/config.toml").write_text(f'[dispatcher.context]\nmode="{mode}"\n[integrations.rtk]\nenabled=false\n')
    home=tmp_path/"selected";home.mkdir(); ambient=tmp_path/"ambient";ambient.mkdir()
    monkeypatch.setenv("APGR_HOME",str(ambient))
    def broken(*args): raise ImportError("optional planner absent")
    if planner_state == "missing":
        monkeypatch.setattr(adapter,"native_plan",broken)
    else:
        monkeypatch.setenv("APGR_GO_BINARY", str(built_context_binary(root)))
    seen=[]
    def runner(argv,prompt,cwd,limit,output):
        from test_agent_phase_result_repair import write_antigravity_evidence
        write_antigravity_evidence(list(argv), response_bytes=b"ok")
        seen.append((list(argv),prompt))
        return Result(0,b"ok",b"",False,time.time(),time.time())
    d=Dispatcher(root,target,project_root=target,apgr_home=home,run_root=tmp_path/"runs",
                 runner=runner,resolve_scanner=False,codex_executable="/fake/codex",
                 claude_launcher="/fake/claude",antigravity_launcher="/fake/antigravity")
    directory=RunDirectory(tmp_path/"runs","context","work-reviewed")
    # Current implementation-testing read-only endpoint in the selected route bundle.
    d._stage(directory,1,"work_review","01-work_review","reviewer",
             Endpoint(provider,"gemini-3.8-flash-high" if provider=="antigravity" else "normal-sysadmin-plan-review" if provider=="claude" else "implementation-testing-review"),
             render([Segment(SEGMENT_TASK_PROMPT,"exact mandatory task é"), Segment(SEGMENT_PRIOR_MATERIAL, prior_bytes)]),None,
             read_only=True,worker_capability={"allowed":False})
    assert len(seen)==1
    record=json.loads((directory.path/"01-work_review.context-plan.json").read_bytes())
    assert record["effective_mode"]=="static" and record["requested_mode"]==mode
    assert record["transport"]["argv"]==seen[0][0]
    assert record["transport"]["stdin"] == adapter.measured(seen[0][1])
    assert prior_bytes in seen[0][1]
    if b"\xff" in prior_bytes:
        assert record["transport"]["stdin"]["characters"] is None
    assert record["planned"] is (mode == "adaptive" and planner_state == "native" and b"\xff" not in prior_bytes)
    assert record["roles"]==["work_review"] and record["attempt_id"].endswith("-work_review-1")
    assert "exact mandatory task é".encode() in seen[0][1]
    if provider=="claude":
        assert "--read-only" in seen[0][0] and "--add-dir" not in seen[0][0]
    if provider in ("codex","antigravity"):
        components=record["instruction_plan"]["components"]
        assert len(components)==1 and components[0]["source_sha256"]==components[0]["rendered_sha256"]


@pytest.mark.parametrize("planner_state", ["missing", "native"])
def test_actual_v2_each_binding_artifact_and_archive(tmp_path,monkeypatch,planner_state):
    import zipfile
    from test_agent_phase_v2_full_execution import _init_repo, _repo_root, _make_v2_request_bytes, _make_closeout_output
    from agent_phase.request import parse_request_v2
    from agent_phase.v2_dispatch import dispatch_v2
    repo=_init_repo(tmp_path/"repo");home=tmp_path/"selected-home"
    (repo/".apgr").mkdir();(repo/".apgr/config.toml").write_text('[dispatcher.context]\nmode="adaptive"\n')
    if planner_state == "missing":
        monkeypatch.setattr(adapter,"native_plan",lambda *args: (_ for _ in ()).throw(ImportError("absent")))
    else:
        monkeypatch.setenv("APGR_GO_BINARY", str(built_context_binary(_repo_root())))
    seen=[]
    def runner(*,run_id,binding,route,run_dir,prompt_bytes,argv,nonce):
        plans=list(run_dir.glob("*.context-plan.json"))
        record=next(json.loads(p.read_bytes()) for p in plans if json.loads(p.read_bytes())["binding_id"]==binding.binding_id)
        assert record["roles"]==sorted(binding.roles)
        assert record["transport"]["argv"]==argv
        assert record["transport"]["stdin"] == adapter.measured(prompt_bytes)
        # APG166Z-CONTEXT1: Claude bindings on the ordinary claude-profile seam
        # become adaptive with the explicit built binary; others stay static.
        supported = (record.get("route_support") or {}).get("supported") is True
        assert record["effective_mode"] == ("adaptive" if planner_state == "native" and supported else "static")
        if planner_state == "native" and not supported:
            assert record["reason"].startswith("route_unsupported:")
        assert record["planned"] is (planner_state == "native")
        seen.append(record["attempt_id"])
        if binding.binding_id=="binding_closeout": return _make_closeout_output(nonce)
        return None
    raw=_make_v2_request_bytes()
    result=dispatch_v2(_repo_root(),repo,parse_request_v2(raw),raw,execution_mode="gemini_sub",apgr_home=home,outbox_root=tmp_path/"outbox",runner=runner)
    assert result["status"]=="completed" and len(seen)==5 and len(set(seen))==5
    with zipfile.ZipFile(result["archive_path"]) as archive:
        plans=[n for n in archive.namelist() if n.endswith(".context-plan.json")]
        transports=[n for n in archive.namelist() if n.endswith(".context-transport.json")]
        assert len(plans)==len(transports)==5


def test_native_bridge_built_binary_and_captured_sources(tmp_path, monkeypatch):
    root=Path(__file__).resolve().parents[3]
    binary=built_context_binary(root)
    monkeypatch.setenv("APGR_GO_BINARY",str(binary))
    home=tmp_path/"home";home.mkdir();project=tmp_path/"project";project.mkdir()
    c=capture("adaptive");c.update(apgr_home=str(home),project_root=str(project))
    c["settings"]["max_initial_context_bytes"]=100000
    argv,prompt,state=prepare(tmp_path,c,facts=[{"kind":"language","value":"go"},{"kind":"test_framework","value":"go-native"}])
    record=state["record"]
    assert record["planned"] and record["effective_mode"]=="static"
    plan=record["prospective_plan"]
    assert {s["qualified_id"] for s in plan["selected_snapshots"]}=={"apgr:go-language-profile","apgr:go-test-profile"}
    assert not plan["catalog"]["snapshots"]
    assert plan["budget"]["max_initial_context_bytes"]==100000-len(adapter.canonical(argv))
    assert prompt=="task é".encode()
    assert list(home.iterdir())==[] and list(project.iterdir())==[]


def test_partial_observation_index_failure_and_retry(tmp_path,monkeypatch):
    from agent_phase import persistence
    _,_,first=prepare(tmp_path)
    before=first["path"].read_bytes()
    monkeypatch.setattr(persistence,"record_artifact",lambda *a,**k: (_ for _ in ()).throw(RuntimeError("index unavailable")))
    adapter.index_reference(first,object(),"run","att-1")
    assert first["path"].read_bytes()==before
    assert list(tmp_path.glob("*.index-failure.json"))
    with pytest.raises(RuntimeError):
        adapter.invoke(first,lambda: (_ for _ in ()).throw(RuntimeError("partial write")))
    obs=json.loads((tmp_path/"01-work.context-transport.json").read_bytes())
    assert obs["status"]=="partial_or_unknown" and obs["transport_delivered"] is None
    second=adapter.prepare(capture=capture(),run_dir=tmp_path,prefix="02-work-attempt-2",
                           run_id="run",binding_id="work",attempt_id="att-2",roles=["work"],
                           consumer="codex",argv=["provider"],prompt=b"new attempt")[2]
    assert second["reference"]["path"]!=first["reference"]["path"]
    assert first["path"].read_bytes()==before


def test_real_process_start_failure_has_no_delivery(tmp_path):
    from agent_phase import provider
    _,_,state=prepare(tmp_path)
    with pytest.raises(provider.ProviderStartFailed):
        adapter.invoke(state,provider.run,[str(tmp_path/"missing-provider")],b"task",tmp_path,1024,None)
    observed=json.loads((tmp_path/"01-work.context-transport.json").read_bytes())
    assert observed["status"]=="start_failed" and observed["transport_delivered"] is False


def test_projection_cannot_fabricate_qualification_or_change_permissions(tmp_path):
    class Unqualified(Projection):
        def qualification(self): return {"selective_projection":True,"independent_recovery":False,"evidence":"fixture"}
    class Expanded(Projection):
        def project(self,plan,argv,prompt): return argv+["--add-dir","/"],prompt
    def planner(request,capture): return {"effective_mode":"adaptive","reasons":[],"payload":"task é"}
    for index,projection in enumerate((Unqualified(),Expanded())):
        root=tmp_path/str(index);root.mkdir()
        argv,prompt,state=prepare(root,capture("adaptive"),planner=planner,projection=projection)
        assert argv==["provider","--readonly"] and prompt=="task é".encode()
        assert state["record"]["effective_mode"]=="static" and state["record"]["reason"]=="optional_plan_failed"


def test_f_fixture_accounting_reproduces_current_sources(tmp_path):
    import subprocess
    import sys
    root=Path(__file__).resolve().parents[3]
    result=subprocess.run([sys.executable,str(root/"testing/fixtures/context-eval/measure_f.py"),
                           "--root",str(root),"--binary",str(built_context_binary(root))],capture_output=True,check=True)
    frozen=json.loads((root/"testing/fixtures/context-eval/f-context1-accounting.json").read_bytes())
    # Current-source regression input is separate from the sealed F acceptance baseline.
    expected=json.loads((root/"src/test/fixtures/context-current/f-context1-accounting.json").read_bytes())
    assert {k: v for k, v in expected.items() if k != "rows"} == {k: v for k, v in frozen.items() if k != "rows"}
    assert len(expected["rows"]) == len(frozen["rows"])
    source_dependent = {"standing_source", "mandatory_cost", "payload_cost", "content_identity"}
    for current, historical in zip(expected["rows"], frozen["rows"]):
        assert {k: v for k, v in current.items() if k not in source_dependent} == {
            k: v for k, v in historical.items() if k not in source_dependent}
    assert json.loads(result.stdout)==expected
    row=next(r for r in expected["rows"] if r["scenario_id"]=="scenario-03")
    assert row["budget"]["max_initial_controlled_bytes"]==30000
    assert row["effective_mode"]=="static" and "required_skills_unsatisfied" in row["reasons"]
    assert expected["historical_scenario_03"]["adaptive_fit"] is False


def test_retained_plan_identity_and_no_replanning(tmp_path, monkeypatch):
    _,_,state=prepare(tmp_path)
    (tmp_path/"state.json").write_text(json.dumps({"context_plans":[state["reference"]]}))
    monkeypatch.setattr(adapter,"native_plan",lambda *a: (_ for _ in ()).throw(AssertionError("historical replan")))
    records=adapter.retained_records(tmp_path,"01-work","work")
    assert len(records)==1 and records[0]["sha256"]==state["reference"]["sha256"]
    state["path"].write_bytes(state["path"].read_bytes()+b" ")
    with pytest.raises(ValueError,match="reference differs"):
        adapter.retained_records(tmp_path,"01-work","work")


def test_context_discovery_uses_apgr_owner_across_git_boundary(tmp_path):
    outer = tmp_path / "outer"
    (outer / ".git").mkdir(parents=True)
    project = outer / "project"
    (project / ".apgr").mkdir(parents=True)
    nested = project / "nested"
    (nested / ".git").mkdir(parents=True)
    (project / ".apgr/config.toml").write_text('[dispatcher.context]\nmode="adaptive"\n')
    result = capture_context_config(start=nested, apgr_home=tmp_path / "home")
    assert result["project_root"] == str(project)
    assert result["settings"]["mode"] == "adaptive"


def test_unqualified_adapter_cannot_report_qualified_projection(tmp_path):
    def planner(request, config):
        return {"effective_mode": "adaptive", "reasons": [], "payload": "task é"}
    _, _, state = prepare(tmp_path, capture("adaptive"), planner=planner)
    assert state["record"]["effective_mode"] == "static"
    assert state["record"]["reason"] == "projection_adapter_unavailable"


def test_static_record_does_not_duplicate_large_prompt(tmp_path):
    prompt = b"x" * (adapter.MAX_PLAN_BYTES + 1)
    _, actual, state = adapter.prepare(
        capture=capture(), run_dir=tmp_path, prefix="large", run_id="run",
        binding_id="work", attempt_id="one", roles=["work"], consumer="codex",
        argv=["provider"], prompt=prompt,
    )
    assert actual == prompt
    assert state["reference"] is not None
    assert "stdin_text" not in state["record"]["transport"]
    assert state["reference"]["bytes"] < 4096
