"""APG166Z-CONTEXT1 structured context inputs: closed config, precedence, manifests."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from agent_phase import context_inputs as inputs
from agent_phase.config_routing import ConfigError, load_config_file


def capture(home=None, project=None, **settings):
    provenance = []
    if home is not None:
        provenance.append({"source": "home", "context": home})
    if project is not None:
        provenance.append({"source": "project", "context": project})
    return {"settings": {"mode": "adaptive", **settings}, "provenance": provenance}


@pytest.mark.parametrize("value", [
    'manifest_facts = "yes"', 'skills = "apgr:x"', 'skills = ["bad-id"]', 'skills = ["apgr:x", "apgr:x"]',
    'skills = [{id = "apgr:x", stages = ["closeout"]}]', 'skills = [{id = "apgr:x", stages = []}]',
    'skills = [{id = "apgr:x", required = "yes"}]', 'skills = [{id = "apgr:x", extra = 1}]',
    'facts = {work_class = ["planning"]}', 'facts = {framework = ["pytest"]}', 'facts = {language = "python"}',
    'facts = {language = ["Python"]}', 'facts = {language = ["go", "go"]}',
    'instructions = "minimal"', 'instructions = true',
])
def test_both_closed_owners_reject_the_same_values(tmp_path, value):
    from agentic_praxis_grimoire.config import ConfigError as PublicError, load_config
    path = tmp_path / "config.toml"
    path.write_text("[dispatcher.context]\n" + value + "\n")
    with pytest.raises(ConfigError):
        load_config_file(path)
    with pytest.raises(PublicError):
        load_config(path)


def test_both_owners_accept_the_documented_example(tmp_path):
    from agentic_praxis_grimoire.config import load_config
    path = tmp_path / "config.toml"
    path.write_text('[dispatcher.context]\nmode = "adaptive"\nmanifest_facts = false\ninstructions = "static"\n'
                    'skills = ["apgr:pytest-test-profile", {id = "project:house-style", required = true, stages = ["work"]}]\n'
                    '[dispatcher.context.facts]\nlanguage = ["python"]\ntest_framework = []\n')
    assert load_config_file(path)["dispatcher"]["context"] == load_config(path)["dispatcher"]["context"]


def test_owner_constants_are_identical():
    from agentic_praxis_grimoire import config
    assert config._CONTEXT_KEYS == inputs.CONTEXT_KEYS
    assert config._CONTEXT_INSTRUCTION_MODES == inputs.INSTRUCTION_MODES
    assert config._CONTEXT_FACT_KINDS == inputs.FACT_KINDS and config._CONTEXT_STAGES == inputs.STAGES
    assert config._CONTEXT_SKILL_ID.pattern == inputs.SKILL_ID.pattern
    assert config._CONTEXT_FACT_VALUE.pattern == inputs.FACT_VALUE.pattern


def test_precedence_is_per_kind_task_project_home_manifest(tmp_path):
    (tmp_path / "go.mod").write_text("module x\n")
    (tmp_path / "pyproject.toml").write_text("[tool.pytest.ini_options]\n")
    with inputs.scoped_task_inputs([("language", "zsh")]):
        facts, requests, record = inputs.resolve(
            capture(home={"facts": {"language": ["ruby"], "runtime": ["nodejs"]}},
                    project={"facts": {"language": ["go"], "capability": []}}),
            postures=["work"], work_tree=tmp_path)
    by = {(f["kind"], f["value"], f["source"]): f["status"] for f in record["facts"]}
    assert by[("language", "zsh", "task")] == "supplied"
    assert by[("language", "go", "project")] == "overridden"
    assert by[("language", "ruby", "home")] == "overridden"
    assert by[("language", "go", "manifest:go.mod")] == "conflicting"
    assert by[("language", "python", "manifest:pyproject.toml")] == "conflicting"
    assert by[("runtime", "nodejs", "home")] == "supplied"
    # The manifest decides a kind only where no configuration declares it.
    assert by[("test_framework", "go-native", "manifest:go.mod")] == "supplied"
    assert by[("test_framework", "pytest", "manifest:pyproject.toml")] == "supplied"
    assert {"kind": "language", "value": "zsh"} in facts
    assert {"kind": "language", "value": "go"} not in facts and {"kind": "language", "value": "python"} not in facts
    # "capability = []" declares none: no manifest or lower source fills it.
    assert not any(f["kind"] == "capability" for f in facts)
    assert record["task_source"] == "dispatch_command" and requests == []


def test_requests_union_replacement_and_posture(tmp_path):
    home = {"skills": ["apgr:bats-test-profile"]}
    project = {"skills": [{"id": "apgr:pytest-test-profile", "stages": ["review"]}, "project:house"]}
    with inputs.scoped_task_inputs([], ["project:house", "apgr:zsh-language-profile"]):
        _, requests, record = inputs.resolve(capture(home=home, project=project, manifest_facts=False),
                                             postures=["work"], work_tree=tmp_path)
    rows = {r["id"]: r for r in record["requests"]}
    assert "apgr:bats-test-profile" not in rows, "project list replaces the home list"
    assert rows["apgr:pytest-test-profile"]["applies"] is False and rows["apgr:pytest-test-profile"]["status"] == "not_applicable"
    assert rows["project:house"]["source"] == "task"
    assert requests == [{"id": "apgr:zsh-language-profile", "required": False}, {"id": "project:house", "required": False}]
    assert record["manifest"]["enabled"] is False


def test_manifest_statuses_never_execute_or_follow(tmp_path):
    (tmp_path / "setup.py").write_text("raise SystemExit('must never run')\n")
    (tmp_path / "Dockerfile").symlink_to(tmp_path / "setup.py")
    (tmp_path / "pyproject.toml").write_text("not = [valid\n")
    (tmp_path / "Gemfile").mkdir()
    facts, files = inputs.manifest_facts(tmp_path)
    statuses = {f["file"]: (f["status"], f.get("reason")) for f in files}
    assert statuses["Dockerfile"] == ("unknown", "symlink_ignored")
    assert statuses["pyproject.toml"] == ("unknown", "unparseable")
    assert statuses["Gemfile"] == ("unknown", "not_regular_file")
    assert statuses["setup.py"][0] == "read" and ("language", "python", "setup.py") in facts
    big = tmp_path / "big"
    big.mkdir()
    (big / "pyproject.toml").write_bytes(b"#" * (inputs.MAX_MANIFEST_BYTES + 1))
    assert inputs.manifest_facts(big)[1] == [{"file": "pyproject.toml", "status": "unknown", "reason": "oversized"}]
    assert inputs.manifest_facts(None)[1][0]["reason"] == "no_working_tree"


def test_unknown_manifest_value_reaches_planner_as_unknown_fact(tmp_path):
    (tmp_path / "Cargo.toml").write_text("[package]\n")
    facts, _, _ = inputs.resolve(capture(), postures=["work"], work_tree=tmp_path)
    assert facts == [{"kind": "language", "value": "rust"}]


@pytest.mark.parametrize("text", ["language", "language=Python", "work_class=planning", "framework=pytest", "language="])
def test_task_fact_parser_rejects(text):
    with pytest.raises(inputs.InputError):
        inputs.parse_task_fact(text)


def test_task_scope_is_eager_and_reset():
    with pytest.raises(inputs.InputError):
        inputs.scoped_task_inputs([], ["apgr:x", "apgr:x"])
    with inputs.scoped_task_inputs([("language", "go")], []):
        assert inputs.TASK_INPUTS.get()["facts"] == [("language", "go")]
    assert inputs.TASK_INPUTS.get() is None


def test_dispatch_cli_rejects_task_inputs_on_resume_and_bad_values(tmp_path, capsys):
    from agent_phase.cli import dispatch_main
    request = tmp_path / "request.json"
    request.write_text("{}")
    with pytest.raises(SystemExit) as raised:
        dispatch_main([str(request), "--resume", str(tmp_path), "--context-fact", "language=go"])
    assert raised.value.code == 2 and "fresh dispatches only" in capsys.readouterr().err
    with pytest.raises(SystemExit) as raised:
        dispatch_main([str(request), "--context-fact", "work_class=planning"])
    assert raised.value.code == 2 and "--context-fact must be" in capsys.readouterr().err
    with pytest.raises(SystemExit) as raised:
        dispatch_main([str(request), "--context-skill", "not-qualified"])
    assert raised.value.code == 2 and "invalid qualified skill ID" in capsys.readouterr().err


def test_static_mode_records_ignored_task_inputs(tmp_path):
    from agent_phase import context_adapter
    static = {"settings": {"mode": "static"}, "provenance": []}
    with inputs.scoped_task_inputs([("language", "go")], ["apgr:go-test-profile"]):
        argv, prompt, state = context_adapter.prepare(
            capture=static, run_dir=tmp_path, prefix="01-work", run_id="run", binding_id="work",
            attempt_id="att-1", roles=["work"], consumer="claude", argv=["provider"], prompt=b"task",
            postures=["work"], route=lambda: pytest.fail("static must not classify the route"))
    assert argv == ["provider"] and prompt == b"task"
    record = state["record"]
    assert record["effective_mode"] == "static" and "inputs" not in record
    assert record["task_inputs_ignored"] == {"reason": "static_mode", "facts": ["language=go"],
                                             "skills": ["apgr:go-test-profile"]}
    _, _, plain = context_adapter.prepare(
        capture=static, run_dir=tmp_path, prefix="02-work", run_id="run", binding_id="work",
        attempt_id="att-2", roles=["work"], consumer="claude", argv=["provider"], prompt=b"task",
        postures=["work"])
    assert "task_inputs_ignored" not in plain["record"]
