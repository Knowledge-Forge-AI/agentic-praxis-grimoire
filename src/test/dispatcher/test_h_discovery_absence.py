"""APG166W-H-RECOVERY1 Decision A: an absent discovery root is observed as absent.

An absent provider global skill root used to be replaced by a recursive
inventory of its nearest existing ancestor, which may be HOME or a vendor
store.  The shared observation owner now records only the named root and the
identity metadata of its lexical path components.  These tests exercise the
real ``_discovery_root_state``/``_operator_observation``/``_begin_observation``/
``_finish_observation`` owners, the prelaunch check and one real live arm with
fake operator layouts in temporary directories.  No real HOME is traversed;
the provider is a local counting fake and all authority is disposable fixture
authority (``h_live_fixtures``).
"""
from __future__ import annotations

import errno
import json
import os
import shutil
import stat
import sys
from pathlib import Path

import pytest

from testing.h_eval import execution, execution_evidence, live_admission, prelaunch, runtime_manifest
from h_live_fixtures import ROOT, Authority, fake_provider, starts

UNIT = "scenario-01/static"


def _home(tmp: Path, *, agents: bool = True, gemini: bool = False) -> Path:
    home = tmp / "home"
    operator = home / "operator"
    operator.mkdir(parents=True)
    (operator / "settings.json").write_text('{"fixture": true}\n')
    (operator / "config.toml").write_text("fixture = true\n")
    if agents:
        (home / ".agents" / "skills").mkdir(parents=True)
        (home / ".agents" / "skills" / "SKILL.md").write_text("skill\n")
    (home / ".claude" / "skills").mkdir(parents=True)
    if gemini:
        (home / ".gemini").mkdir()
    return home


def _sealed(provider: Path, home: Path, **environment) -> dict:
    git = Path(shutil.which("git") or "/usr/bin/git")
    tool = provider.parent / "fake-tool"
    tool.write_text(f"#!{sys.executable}\nprint('fake-tool 0.0-test')\n")
    tool.chmod(0o700)
    groups = {group: [ROOT / "README.md"] for group in runtime_manifest.REQUIRED_GROUPS}
    groups["operator_settings"] = [home / "operator/settings.json", home / "operator/config.toml"]
    return runtime_manifest.seal(runtime_manifest.capture_complete(
        providers={name: (provider, ["--version"]) for name in ("codex", "claude", "antigravity")},
        commands={name: ((git, ["--version"]) if name == "git" else (tool, ["--version"]))
                  for name in runtime_manifest.REQUIRED_COMMANDS},
        groups=groups,
        routes={"fixture": "granted-live"},
        absent_settings=[home / "absent-setting"],
        environment={"home": str(home), "temp_root": str(home), **environment},
    ))


def _world(tmp_path, monkeypatch, *, provider_options=None, authority=False, environment=None, **layout):
    home = _home(tmp_path, **layout)
    provider, counter = fake_provider(tmp_path / "fixture", **(provider_options or {}))
    runtime = _sealed(provider, home, **(environment or {}))
    world = {"tmp": tmp_path, "home": home, "runtime": runtime, "counter": counter}
    if authority:
        world["authority"] = Authority(tmp_path, monkeypatch, runtime)
    return world


def _run(tmp: Path) -> Path:
    run = tmp / "run"
    run.mkdir()
    return run


def _begin(world, provider="antigravity"):
    return execution._begin_observation(_run(world["tmp"]), {}, "static", [provider], provider, world["runtime"])


def _oracle_double(monkeypatch):
    from testing.h_eval import oracles

    def evaluate(subject, returned, scenario):
        return {"schema": "apg.h-task-oracle/v1", "oracle": scenario["expected_outcome"]["quality_oracle"],
                "status": "fail", "evidence": [{"kind": "test-double", "sha256": "0" * 64, "bytes": 0}]}

    monkeypatch.setattr(oracles, "oracle_for", lambda scenario: evaluate)


def _live_arm(world, authorization, name="arm"):
    return execution.construct_arm(
        arm_dir=world["tmp"] / name, source_root=ROOT, scenario_id="scenario-01", mode="static",
        execution="live", runtime_inputs=world["runtime"], live_authorization=authorization,
    )


# --- owner classification ----------------------------------------------------


def test_existing_root_keeps_v1_receipt_shape(tmp_path, monkeypatch):
    world = _world(tmp_path, monkeypatch)
    state = _begin(world, "codex")
    assert state["global_scope"] == "existing-root" and state["global_absent"] == []
    receipt = execution._finish_observation(state)["discovery_receipt"]
    assert set(receipt) == {"schema", "run_root", "global_before", "global_after", "scoped_to_run",
                            "run_root_after", "global_path", "global_candidate", "global_absent"}
    assert receipt["schema"] == execution.DISCOVERY_RECEIPT_SCHEMA
    assert receipt["global_path"] == receipt["global_candidate"] == str(world["home"] / ".agents/skills")
    assert execution_evidence.discovery_scope(receipt) == "existing-root"


def test_empty_existing_root_is_distinct_from_missing_root(tmp_path, monkeypatch):
    world = _world(tmp_path, monkeypatch, gemini=True)
    root = world["home"] / ".gemini/skills"
    root.mkdir()
    empty = execution._operator_observation(world["runtime"], provider_name="antigravity")
    assert empty["global_scope"] == "existing-root" and "schema" not in empty["global_before"]
    root.rmdir()
    missing = execution._operator_observation(world["runtime"], provider_name="antigravity")
    assert missing["global_scope"] == "absent-root"
    assert missing["global_before"]["schema"] == execution.DISCOVERY_ABSENCE_SCHEMA
    assert missing["global_before"]["kind"] == "absent"


def test_missing_root_and_missing_parent_record_only_the_named_path(tmp_path, monkeypatch):
    world = _world(tmp_path, monkeypatch, gemini=True)
    home = world["home"]
    state, record = execution._discovery_root_state(home / ".gemini/skills")
    assert state == "absent" and record["missing"] == [str(home / ".gemini/skills")]
    assert record["existing_prefix"] == str(home / ".gemini")
    assert record["lexical_root"] == str(home / ".gemini/skills")
    assert [item["path"] for item in record["components"]][-2:] == [str(home), str(home / ".gemini")]
    assert record["components"][0]["path"] == "/"
    assert record["sha256"] == execution.discovery_absence_digest(record)
    assert not any(key in json.dumps(record) for key in ("mtime", "size", "nlink", "entries"))
    (home / ".gemini").rmdir()
    state, deeper = execution._discovery_root_state(home / ".gemini/skills")
    assert deeper["missing"] == [str(home / ".gemini"), str(home / ".gemini/skills")]
    assert deeper["existing_prefix"] == str(home)
    assert not (home / ".gemini").exists()  # nothing is created


def test_appearance_of_root_after_begin_refuses(tmp_path, monkeypatch):
    world = _world(tmp_path, monkeypatch, gemini=True)
    state = _begin(world)
    assert state["global_absent"] == [str(world["home"] / ".gemini/skills")]
    (world["home"] / ".gemini/skills").mkdir()
    with pytest.raises(ValueError, match="^global discovery absence assertion changed during arm$"):
        execution._finish_observation(state)
    (world["home"] / ".gemini/skills").rmdir()
    (world["home"] / ".gemini/skills").write_text("a file also appears\n")
    with pytest.raises(ValueError, match="^global discovery absence assertion changed during arm$"):
        execution._finish_observation(state)


def test_missing_parent_appearing_without_root_refuses(tmp_path, monkeypatch):
    """Recorded, conservative risk: a missing parent that appears changes the record."""
    world = _world(tmp_path, monkeypatch)
    state = _begin(world)
    (world["home"] / ".gemini").mkdir()
    with pytest.raises(ValueError, match="^global discovery absent path changed during arm$"):
        execution._finish_observation(state)


def test_parent_directory_replacement_refuses(tmp_path, monkeypatch):
    world = _world(tmp_path, monkeypatch, gemini=True)
    state = _begin(world)
    (world["home"] / ".gemini").rename(world["home"] / ".gemini-old")
    (world["home"] / ".gemini").mkdir()
    with pytest.raises(ValueError, match="^global discovery absent path changed during arm$"):
        execution._finish_observation(state)


def test_relevant_symlink_retarget_refuses(tmp_path, monkeypatch):
    world = _world(tmp_path, monkeypatch)
    first, second = tmp_path / "vendor-a", tmp_path / "vendor-b"
    first.mkdir()
    second.mkdir()
    (world["home"] / ".gemini").symlink_to(first)
    state = _begin(world)
    link = state["global_before"]["components"][-1]
    assert link["kind"] == "symlink" and link["link_text"] == str(first)
    assert set(link["target"]) == {"device", "inode", "mode"}
    (world["home"] / ".gemini").unlink()
    (world["home"] / ".gemini").symlink_to(second)
    with pytest.raises(ValueError, match="^global discovery absent path changed during arm$"):
        execution._finish_observation(state)


def test_broken_link_or_nondirectory_component_is_never_absent(tmp_path, monkeypatch):
    world = _world(tmp_path, monkeypatch)
    gemini = world["home"] / ".gemini"
    gemini.symlink_to(tmp_path / "gone")
    with pytest.raises(ValueError, match="^discovery root path link is unresolved$") as caught:
        execution._operator_observation(world["runtime"], provider_name="antigravity")
    assert caught.value.__cause__.errno == errno.ENOENT
    gemini.unlink()
    gemini.write_text("not a directory\n")
    with pytest.raises(ValueError, match="^discovery root path component is not a directory$"):
        execution._operator_observation(world["runtime"], provider_name="antigravity")
    gemini.unlink()
    gemini.mkdir()
    (gemini / "skills").symlink_to(tmp_path / "gone")
    with pytest.raises(ValueError, match="^discovery root is not a physical directory$"):
        execution._operator_observation(world["runtime"], provider_name="antigravity")
    with pytest.raises(ValueError, match="absolute lexical path"):
        execution._discovery_root_state(Path("relative/skills"))


@pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses directory search permission")
def test_permission_refusal_is_not_absence(tmp_path, monkeypatch):
    world = _world(tmp_path, monkeypatch, gemini=True)
    gemini = world["home"] / ".gemini"
    gemini.chmod(0)
    try:
        with pytest.raises(ValueError, match="^discovery root path component is not observable$") as caught:
            execution._operator_observation(world["runtime"], provider_name="antigravity")
        assert caught.value.__cause__.errno == errno.EACCES
        detail = execution._failure_detail(caught.value, "observation_begin")
        assert detail["cause"] == {"type": "PermissionError", "errno": "EACCES"}
        assert detail["reason"] == "discovery root path component is not observable"
    finally:
        gemini.chmod(0o700)


def test_absent_root_never_walks_its_parent(tmp_path, monkeypatch):
    world = _world(tmp_path, monkeypatch, gemini=True)
    home, gemini = world["home"], world["home"] / ".gemini"
    for parent in (home, gemini):
        os.mkfifo(parent / "pipe")
        (parent / "dangling").symlink_to(tmp_path / "gone")
        for index in range(40):
            (parent / f"entry-{index}").write_text("x\n")
    touched: list[str] = []
    real_input, real_scandir, real_listdir = runtime_manifest._input, os.scandir, os.listdir

    def spy(real):
        def wrapped(path=".", *args, **kwargs):
            if str(path).startswith(str(home)):
                touched.append(str(path))
            return real(path, *args, **kwargs)
        return wrapped

    monkeypatch.setattr(runtime_manifest, "_input", spy(real_input))
    monkeypatch.setattr(os, "scandir", spy(real_scandir))
    monkeypatch.setattr(os, "listdir", spy(real_listdir))
    state = execution._operator_observation(world["runtime"], provider_name="antigravity")
    assert state["global_scope"] == "absent-root"
    report = prelaunch.check_observation(world["runtime"], source_root=ROOT, scenario_ids=["scenario-05"])
    assert report["providers"]["antigravity"]["status"] == "ready"
    # Only the manifest-bound settings files are read; no HOME directory is
    # listed or inventoried.
    settings = {str(home / "operator/settings.json"), str(home / "operator/config.toml")}
    assert touched and set(touched) <= settings
    assert not any(Path(path).is_dir() for path in touched)


def test_unrelated_sibling_churn_is_not_a_root_change(tmp_path, monkeypatch):
    world = _world(tmp_path, monkeypatch, gemini=True)
    home, gemini = world["home"], world["home"] / ".gemini"
    (gemini / "settings.json").write_text("{}\n")
    state = _begin(world)
    (gemini / "settings.json").write_text('{"changed": true}\n')
    (gemini / "antigravity").mkdir()
    (gemini / "antigravity" / "session.db").write_text("session\n")
    (home / "new-sibling").mkdir()
    (home / ".gemini-cache").write_text("cache\n")
    receipt = execution._finish_observation(state)["discovery_receipt"]
    assert receipt["global_before"] == receipt["global_after"]
    assert receipt["schema"] == execution.DISCOVERY_ABSENT_RECEIPT_SCHEMA


@pytest.mark.parametrize("layout", ["existing", "absent-root", "absent-config"])
def test_claude_config_dir_selection_uses_the_same_owner(tmp_path, monkeypatch, layout):
    config = tmp_path / "claude-config"
    if layout != "absent-config":
        config.mkdir()
    if layout == "existing":
        (config / "skills").mkdir()
    world = _world(tmp_path, monkeypatch, environment={"CLAUDE_CONFIG_DIR": str(config)})
    state = _begin(world, "claude")
    assert state["global_candidate"] == config / "skills"
    receipt = execution._finish_observation(state)["discovery_receipt"]
    if layout == "existing":
        assert receipt["schema"] == execution.DISCOVERY_RECEIPT_SCHEMA
    else:
        missing = [str(config / "skills")] if layout == "absent-root" else [str(config), str(config / "skills")]
        assert receipt["global_absent"] == missing
        assert execution_evidence.discovery_scope(receipt) == "absent-root"
    assert not (world["home"] / ".claude/skills/SKILL.md").exists()


# --- receipt validation and history -----------------------------------------


def _v2_receipt(tmp_path, monkeypatch) -> dict:
    world = _world(tmp_path, monkeypatch, gemini=True)
    return execution._finish_observation(_begin(world))["discovery_receipt"]


def test_v2_receipt_validates_and_rejects_tampering(tmp_path, monkeypatch):
    receipt = _v2_receipt(tmp_path, monkeypatch)
    assert execution_evidence._discovery_observation(receipt) == receipt
    assert execution_evidence.discovery_scope(receipt) == "absent-root"

    def mutate(change):
        value = json.loads(json.dumps(receipt))
        change(value)
        return value

    bad = [
        mutate(lambda v: v["global_after"].update(missing=[v["global_candidate"] + "x"])),
        mutate(lambda v: v["global_after"].update(sha256="0" * 64)),
        mutate(lambda v: v.update(global_absent=[])),
        mutate(lambda v: v.update(global_path=str(Path(v["global_candidate"]).parent))),
        mutate(lambda v: v.update(scoped_to_run=False)),
        mutate(lambda v: v.pop("run_root_after")),
        mutate(lambda v: v.update(extra=True)),
        mutate(lambda v: v.update(global_scope="existing-root")),
        mutate(lambda v: v["global_before"]["components"].pop(0)),
    ]
    for value in bad:
        with pytest.raises(ValueError):
            execution_evidence._discovery_observation(value)
    # A re-digested but inconsistent record still refuses on its structure.
    forged = mutate(lambda v: v["global_after"]["components"][-1].update(inode=1))
    forged["global_after"]["sha256"] = execution.discovery_absence_digest(forged["global_after"])
    with pytest.raises(ValueError, match="changed during arm"):
        execution_evidence._discovery_observation(forged)


def test_v1_receipt_cannot_claim_absence_and_legacy_ancestor_stays_legacy(tmp_path, monkeypatch):
    world = _world(tmp_path, monkeypatch)
    receipt = execution._finish_observation(_begin(world, "codex"))["discovery_receipt"]
    with pytest.raises(ValueError, match="cannot claim an absence scope"):
        execution_evidence._discovery_observation({**receipt, "global_scope": "absent-root"})
    # Historical shape: an existing ancestor was fully inventoried for an
    # absent candidate.  It stays readable and is never relabelled.
    legacy = {**receipt, "global_candidate": str(world["home"] / ".gemini/skills"),
              "global_absent": [str(world["home"] / ".gemini/skills"), str(world["home"] / ".gemini")]}
    assert execution_evidence._discovery_observation(legacy) == legacy
    assert execution_evidence.discovery_scope(legacy) == "legacy-ancestor-inventory"


def test_scenario15_isolation_oracle_conservatively_refuses_v2(tmp_path, monkeypatch):
    from testing.h_eval import oracles
    receipt = _v2_receipt(tmp_path, monkeypatch)
    settings = {"schema": "apg.h-settings-observation/v1", "before": receipt["run_root"],
                "after": receipt["run_root"]}
    with pytest.raises(oracles._Incomplete):
        oracles._settings_isolation_check({"settings_receipt": settings, "discovery_receipt": receipt})


# --- one real live arm with an absent codex root ----------------------------


def test_live_arm_with_absent_root_completes_with_v2_receipt(tmp_path, monkeypatch):
    world = _world(tmp_path, monkeypatch, agents=False, authority=True)
    (world["home"] / ".agents").mkdir()
    _oracle_double(monkeypatch)
    result = _live_arm(world, world["authority"].grant([UNIT]))
    assert result["status"] == "complete", result.get("failure_detail")
    assert starts(world["counter"]) == 1
    receipt = result["discovery_receipt"]
    assert receipt["schema"] == execution.DISCOVERY_ABSENT_RECEIPT_SCHEMA
    assert receipt["global_absent"] == [str(world["home"] / ".agents/skills")]
    readback = execution.read_arm_result(tmp_path / "arm")
    assert readback["qualification_eligibility"]["status"] == "eligible", readback["qualification_eligibility"]
    activity = json.loads((tmp_path / "arm/oracle-input/activity.json").read_text())
    assert activity["discovery_receipt"] == receipt
    assert not (world["home"] / ".agents/skills").exists()


def test_root_appearing_during_live_arm_refuses_after_the_one_start(tmp_path, monkeypatch):
    home_skills = tmp_path / "home" / ".agents" / "skills"
    world = _world(tmp_path, monkeypatch, agents=False, authority=True,
                   provider_options={"write": str(home_skills)})
    (world["home"] / ".agents").mkdir()
    result = _live_arm(world, world["authority"].grant([UNIT]))
    assert starts(world["counter"]) == 1
    assert result["status"] == "incomplete" and result["failure"] == "ValueError"
    assert result["failure_detail"]["step"] == "observation_finish"
    assert result["failure_detail"]["reason"] == "global discovery absence assertion changed during arm"
    readback = execution.read_arm_result(tmp_path / "arm")
    assert readback["provider_invocations"] == 1
    assert live_admission.verify_receipt(readback["live_admission"], unit=UNIT)


def test_preflight_reports_single_missing_root_without_parent_risk(tmp_path, monkeypatch):
    world = _world(tmp_path, monkeypatch, gemini=True)
    report = prelaunch.check_observation(world["runtime"], source_root=ROOT, scenario_ids=["scenario-05"])
    gemini = report["providers"]["antigravity"]
    assert report["schema"] == "apg.h-prelaunch-observation-check/v2"
    assert gemini["status"] == "ready" and gemini["global_scope"] == "absent-root"
    assert gemini["absent"] == 1 and gemini["missing_parent"] is False
    assert stat.S_ISDIR(os.lstat(world["home"] / ".gemini").st_mode)
    assert starts(world["counter"]) == 0
