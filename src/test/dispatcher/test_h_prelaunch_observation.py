"""APG166W-H-PRELAUNCH1 settings/discovery prelaunch observation.

The calibration arm stopped after its context plan and before provider stdin
with only ``failure: ValueError``.  A read-only host observation of the
unchanged owner located a ``ValueError`` at the Codex global skill root, where
the strict manifest walk refuses a direct child symlink whose target is gone.

These tests build an accepted-source-shaped operator HOME in a temporary
directory: manifest-bound settings files, absolute managed-style directory
symlinks into a release tree (with a nested file link), a regular installer
state file, and one dangling top-level link.  Real static context preparation
and the real observation owner run.  Only the provider executable is a local
counting fake; decision, grant and custody records are temporary fixture
authority (``h_live_fixtures``), never the real campaign custody.
"""
from __future__ import annotations

import errno
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from testing.h_eval import assembly, execution, granted_execution, live_admission, runtime_manifest
from h_live_fixtures import ROOT, Authority, fake_provider, starts

UNIT = "scenario-01/static"
DANGLING = ".tmp-dryrun-flakes"


def _operator_home(tmp: Path, *, dangling: bool = True) -> Path:
    home = tmp / "home"
    release = tmp / "release" / "skills" / "managed-skill"
    release.mkdir(parents=True)
    (release / "SKILL.md").write_text("---\nname: managed-skill\n---\nbody\n")
    (release / "reference.md").symlink_to(release / "SKILL.md")
    root = home / ".agents" / "skills"
    root.mkdir(parents=True)
    (root / "managed-skill").symlink_to(release)
    (root / ".install-global-skills-state.json").write_text("{}\n")
    if dangling:
        (root / DANGLING).symlink_to(tmp / "retired-flakes")
    claude = home / ".claude" / "skills"
    claude.mkdir(parents=True)
    (claude / "managed-skill").symlink_to(release)
    operator = home / "operator"
    operator.mkdir()
    (operator / "settings.json").write_text('{"fixture": true}\n')
    (operator / "config.toml").write_text("fixture = true\n")
    return home


def _sealed(provider: Path, home: Path) -> dict:
    """``h_live_fixtures.sealed_runtime`` with real operator-settings files."""
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
        environment={"home": str(home), "temp_root": str(home)},
    ))


@pytest.fixture
def world(tmp_path, monkeypatch):
    home = _operator_home(tmp_path)
    return _world(tmp_path, monkeypatch, home)


def _world(tmp_path, monkeypatch, home, **provider_options):
    provider, counter = fake_provider(tmp_path / "fixture", **provider_options)
    runtime = _sealed(provider, home)
    return {"authority": Authority(tmp_path, monkeypatch, runtime), "runtime": runtime,
            "counter": counter, "tmp": tmp_path, "home": home,
            "skills": home / ".agents" / "skills"}


def _live_arm(world, authorization, name="arm", scenario_id="scenario-01", mode="static"):
    return execution.construct_arm(
        arm_dir=world["tmp"] / name, source_root=ROOT, scenario_id=scenario_id, mode=mode,
        execution="live", runtime_inputs=world["runtime"], live_authorization=authorization,
    )


def _oracle_double(monkeypatch):
    from testing.h_eval import oracles

    def evaluate(subject, returned, scenario):
        return {"schema": "apg.h-task-oracle/v1", "oracle": scenario["expected_outcome"]["quality_oracle"],
                "status": "fail", "evidence": [{"kind": "test-double", "sha256": "0" * 64, "bytes": 0}]}

    monkeypatch.setattr(oracles, "oracle_for", lambda scenario: evaluate)


def _entries(identity: dict) -> dict[str, dict]:
    return {entry["relative_path"]: entry for entry in identity["entries"]}


# --- reproduction and owner semantics -------------------------------------


def test_strict_manifest_walk_still_refuses_dangling_link(world):
    """The original mechanism: the default walk raises the observed literal."""
    with pytest.raises(ValueError, match="^runtime input is unavailable$") as caught:
        runtime_manifest._input(world["skills"])
    assert isinstance(caught.value.__cause__, OSError)


def test_begin_observation_accepts_dangling_global_skill_link(world, tmp_path):
    """Red on the unchanged owner: this exact call raised the host ValueError."""
    run = tmp_path / "run"
    run.mkdir()
    state = execution._begin_observation(run, {}, "static", ["codex"], "codex", world["runtime"])
    assert state["global_candidate"] == world["skills"]
    assert state["global_path"] == world["skills"] and state["global_absent"] == []
    assert [item["path"] for item in state["settings_before"]] == [
        str(world["home"] / "operator/config.toml"), str(world["home"] / "operator/settings.json")]
    receipt = execution._finish_observation(state)["discovery_receipt"]
    assert receipt["global_before"] == receipt["global_after"]


def test_dangling_link_identity_is_bound(world, tmp_path):
    identity = runtime_manifest._input(world["skills"], unresolved_links=True)
    entry = _entries(identity)[DANGLING]
    assert entry == {
        "kind": "symlink", "relative_path": DANGLING, "link_target": str(tmp_path / "retired-flakes"),
        "target_kind": "unresolved", "unresolved_errno": "ENOENT",
        "bytes": 0, "sha256": runtime_manifest.hashlib.sha256(b"").hexdigest(),
    }
    managed = _entries(identity)["managed-skill"]
    assert managed["target_kind"] == "directory"
    assert {e["relative_path"] for e in managed["target_identity"]["entries"]} == {"SKILL.md", "reference.md"}
    link = world["skills"] / DANGLING
    link.unlink()
    link.symlink_to(tmp_path / "other-retired")
    retargeted = runtime_manifest._input(world["skills"], unresolved_links=True)
    assert retargeted["sha256"] != identity["sha256"]
    (tmp_path / "other-retired").write_text("appeared\n")
    appeared = runtime_manifest._input(world["skills"], unresolved_links=True)
    assert appeared["sha256"] not in {identity["sha256"], retargeted["sha256"]}
    assert "target_kind" not in _entries(appeared)[DANGLING]


def test_notdir_and_loop_links_are_bound_without_version_specific_resolve(world, tmp_path):
    (tmp_path / "plain").write_text("x\n")
    (world["skills"] / "notdir").symlink_to(tmp_path / "plain" / "child")
    (world["skills"] / "loop-a").symlink_to(world["skills"] / "loop-b")
    (world["skills"] / "loop-b").symlink_to(world["skills"] / "loop-a")
    entries = _entries(runtime_manifest._input(world["skills"], unresolved_links=True))
    assert entries["notdir"]["unresolved_errno"] == "ENOTDIR"
    assert entries["loop-a"]["unresolved_errno"] == entries["loop-b"]["unresolved_errno"] == "ELOOP"


@pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses directory search permission")
def test_permission_denied_link_target_still_refuses(world, tmp_path):
    hidden = tmp_path / "hidden"
    (hidden / "skill").mkdir(parents=True)
    (world["skills"] / "hidden-skill").symlink_to(hidden / "skill")
    hidden.chmod(0)
    try:
        with pytest.raises(ValueError, match="^runtime input is unavailable$") as caught:
            runtime_manifest._input(world["skills"], unresolved_links=True)
        assert caught.value.__cause__.errno == errno.EACCES
    finally:
        hidden.chmod(0o700)


def test_nonregular_entry_still_refuses(world):
    os.mkfifo(world["skills"] / "pipe")
    with pytest.raises(ValueError, match="nonregular entry"):
        runtime_manifest._input(world["skills"], unresolved_links=True)


def test_tolerance_is_limited_to_the_global_discovery_root(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    (run / "provider-link").symlink_to(tmp_path / "absent")
    with pytest.raises(ValueError, match="^runtime input is unavailable$"):
        execution._observation_identity(run)
    assert execution._observation_identity(run, unresolved_links=True)["path"] == str(run)


# --- failure detail --------------------------------------------------------


def test_failure_detail_keeps_only_source_literal_reasons():
    try:
        runtime_manifest._physical("relative/path")
    except ValueError as error:
        literal = execution._failure_detail(error, "observation_begin")
    assert literal["schema"] == "apg.h-arm-failure/v1"
    assert literal["step"] == "observation_begin" and literal["type"] == "ValueError"
    assert literal["reason"] == "absolute runtime input required" and literal["reason_omitted"] is False
    assert literal["frames"][-1] == {"file": "testing/h_eval/runtime_manifest.py", "function": "_physical",
                                     "line": literal["frames"][-1]["line"]}
    try:
        live_admission._encoded_unit("scenario-99/secret-value")
    except ValueError as error:
        interpolated = execution._failure_detail(error, "runtime_transaction")
    assert interpolated["reason"] is None and interpolated["reason_omitted"] is True
    assert "secret-value" not in json.dumps(interpolated)
    foreign = execution._failure_detail(ValueError("/private/token=abc"), "provider_invoke")
    assert foreign["frames"] == [] and foreign["reason"] is None
    assert "token" not in json.dumps(foreign)


def test_failure_detail_records_symbolic_cause_errno(tmp_path):
    (tmp_path / "link").symlink_to(tmp_path / "gone")
    try:
        runtime_manifest._physical(tmp_path / "link")
    except ValueError as error:
        detail = execution._failure_detail(error, "observation_begin")
    assert detail["cause"] == {"type": "FileNotFoundError", "errno": "ENOENT"}
    assert str(tmp_path) not in json.dumps(detail)


# --- arm integration with the provider boundary as the only fake ----------


def test_good_operator_layout_completes_one_start(world, monkeypatch):
    _oracle_double(monkeypatch)
    result = _live_arm(world, world["authority"].grant([UNIT]))
    assert result["status"] == "complete", result.get("failure_detail")
    assert starts(world["counter"]) == 1 and result["provider_invocations"] == 1
    discovery = result["discovery_receipt"]
    assert discovery["global_path"] == str(world["skills"]) and discovery["global_absent"] == []
    assert discovery["global_before"] == discovery["global_after"]
    assert "failure" not in result and "failure_detail" not in result
    from testing.h_eval import oracles
    assert oracles._settings_isolation_check(result)[1]["global_equal"] is True


def test_provider_resolving_the_dangling_link_is_recorded_as_drift(tmp_path, monkeypatch):
    home = _operator_home(tmp_path)
    world = _world(tmp_path, monkeypatch, home, write=str(tmp_path / "retired-flakes"))
    _oracle_double(monkeypatch)
    result = _live_arm(world, world["authority"].grant([UNIT]))
    assert starts(world["counter"]) == 1
    discovery = result["discovery_receipt"]
    assert discovery["global_before"]["sha256"] != discovery["global_after"]["sha256"]
    from testing.h_eval import oracles
    passed, detail = oracles._settings_isolation_check(result)
    assert passed is False and detail["global_equal"] is False


def test_operator_settings_drift_refuses_after_provider(tmp_path, monkeypatch):
    home = _operator_home(tmp_path)
    world = _world(tmp_path, monkeypatch, home, write=str(home / "operator/settings.json"))
    result = _live_arm(world, world["authority"].grant([UNIT]))
    assert starts(world["counter"]) == 1
    assert result["status"] == "incomplete" and result["failure"] == "ValueError"
    detail = result["failure_detail"]
    assert detail["step"] == "observation_finish"
    assert detail["reason"] == "manifest-bound operator settings changed during arm"


def _fifo_world(tmp_path, monkeypatch):
    home = _operator_home(tmp_path)
    world = _world(tmp_path, monkeypatch, home)
    # Created after the manifest seal: the root is not a manifest input, which
    # is exactly why the historical check passed and the arm refused.
    os.mkfifo(world["skills"] / "pipe")
    return world


def test_prelaunch_refusal_consumes_unit_without_provider_call(tmp_path, monkeypatch):
    world = _fifo_world(tmp_path, monkeypatch)
    authorization = world["authority"].grant([UNIT])
    result = _live_arm(world, authorization)
    assert starts(world["counter"]) == 0
    assert result["status"] == "incomplete" and result["failure"] == "ValueError"
    assert result["provider_invocations"] == 0
    assert result["settings_receipt"] is None and result["discovery_receipt"] is None
    detail = result["failure_detail"]
    assert detail["step"] == "observation_begin"
    assert detail["reason"] == "runtime input directory contains a nonregular entry"
    assert detail["frames"][0]["function"] == "run_one_arm"
    arm = tmp_path / "arm"
    assert (arm / "run/attempt.context-plan.json").is_file()
    assert not (arm / "run/provider.stdin").exists()
    readback = execution.read_arm_result(arm)
    assert readback["failure_detail"] == detail
    assert live_admission.verify_receipt(readback["live_admission"], unit=UNIT)
    accounting = live_admission.accounting(ROOT, authorization, arm_receipts={UNIT: readback["live_admission"]})
    assert accounting["retained"] == 1 and accounting["provider_starts_by_accounting"] == 0
    with pytest.raises(ValueError, match="already consumed"):
        _live_arm(world, authorization, name="replay")
    assert starts(world["counter"]) == 0


def test_pair_stops_after_prelaunch_refusal_and_carries_step(tmp_path, monkeypatch):
    world = _fifo_world(tmp_path, monkeypatch)
    authorization = world["authority"].grant([UNIT, "scenario-01/adaptive"])
    record = granted_execution.run_granted_pair(
        pair_dir=tmp_path / "pair", source_root=ROOT, scenario_id="scenario-01",
        live_authorization=authorization, runtime_inputs=world["runtime"],
    )
    assert starts(world["counter"]) == 0
    assert set(record["arms"]) == {"static"} and "did not complete" in record["stopped"]
    assert record["arms"]["static"]["failure"] == "ValueError"
    assert record["arms"]["static"]["failure_detail"]["step"] == "observation_begin"
    assert not (tmp_path / "pair/adaptive").exists()
    assert live_admission.accounting(ROOT, authorization)["unconsumed"] == ["scenario-01/adaptive"]


def test_historical_failure_shape_without_detail_stays_readable(tmp_path, monkeypatch):
    world = _fifo_world(tmp_path, monkeypatch)
    _live_arm(world, world["authority"].grant([UNIT]))
    readback = execution.read_arm_result(tmp_path / "arm")
    historical = {key: value for key, value in readback.items() if key != "failure_detail"}
    assembled = assembly._receipt_arm(
        {"frozen_oracle": {}, "routes": {"static": {}}, "scenario_id": "scenario-01"},
        "static", {**historical, "_arm_dir": str(tmp_path / "arm")})
    assert assembled["coverage"]["source"] == "unavailable"


# --- non-consuming preflight ----------------------------------------------


def _forbid_subprocess(monkeypatch):
    """Patch after the fixture manifest is captured (capture probes versions)."""
    def refuse(*_args, **_kwargs):
        raise AssertionError("prelaunch check must not spawn a process")

    for name in ("run", "Popen", "check_output", "check_call", "call"):
        monkeypatch.setattr(subprocess, name, refuse)


def test_preflight_ready_reports_roots_without_consuming(world, monkeypatch):
    from testing.h_eval import prelaunch
    _forbid_subprocess(monkeypatch)
    report = prelaunch.check_observation(world["runtime"], source_root=ROOT)
    assert report["schema"] == prelaunch.SCHEMA and report["admission"] is False
    assert report["units"] == [f"{sid}/{mode}" for sid in live_admission.CALIBRATION
                               for mode in ("static", "adaptive")]
    providers = report["providers"]
    assert sorted(providers) == ["antigravity", "claude", "codex"]
    codex = providers["codex"]
    assert codex["status"] == "ready" and codex["global_path"] == str(world["skills"])
    assert codex["global_scope"] == "existing-root" and codex["settings_inputs"] == 2
    assert codex["unresolved_links"] == [{"relative_path": DANGLING, "errno": "ENOENT"}]
    assert providers["claude"]["global_path"] == str(world["home"] / ".claude/skills")
    # APG166W-H-RECOVERY1: an absent root is observed as absent, without opt-in
    # and without walking HOME; the missing parent is reported as a risk.
    gemini = providers["antigravity"]
    assert report["status"] == "ready" and gemini["status"] == "ready"
    assert gemini["global_scope"] == "absent-root"
    assert gemini["global_path"] == gemini["global_candidate"] == str(world["home"] / ".gemini/skills")
    assert gemini["absent"] == 2 and gemini["missing_parent"] is True
    assert gemini["settings_inputs"] == 2 and gemini["unresolved_link_count"] is None
    assert not (world["home"] / ".gemini").exists()
    ready = prelaunch.check_observation(world["runtime"], source_root=ROOT,
                                        scenario_ids=["scenario-01", "scenario-02"])
    assert ready["status"] == "ready" and "antigravity" not in ready["providers"]
    assert not (world["authority"].custody / live_admission.LEDGER).exists()
    assert starts(world["counter"]) == 0


def test_absent_root_is_observed_without_walking_home(world, monkeypatch):
    """No ancestor such as HOME is walked; its dangling link and FIFO are irrelevant."""
    from testing.h_eval import prelaunch
    _forbid_subprocess(monkeypatch)
    os.mkfifo(world["home"] / "pipe")
    state = execution._operator_observation(world["runtime"], provider_name="antigravity")
    assert state["global_scope"] == "absent-root" and state["global_path"] == state["global_candidate"]
    assert state["global_before"]["schema"] == execution.DISCOVERY_ABSENCE_SCHEMA
    report = prelaunch.check_observation(world["runtime"], source_root=ROOT, scenario_ids=["scenario-05"])
    gemini = report["providers"]["antigravity"]
    assert report["status"] == "ready" and gemini["status"] == "ready"
    assert gemini["unresolved_link_count"] is None and gemini["unresolved_links"] is None
    with pytest.raises(TypeError):
        prelaunch.check_observation(world["runtime"], source_root=ROOT,
                                    scenario_ids=["scenario-05"], allow_ancestor_walk=True)
    assert not (world["authority"].custody / live_admission.LEDGER).exists()
    assert starts(world["counter"]) == 0


def test_preflight_refuses_with_bounded_detail(tmp_path, monkeypatch):
    from testing.h_eval import prelaunch
    world = _fifo_world(tmp_path, monkeypatch)
    _forbid_subprocess(monkeypatch)
    report = prelaunch.check_observation(world["runtime"], source_root=ROOT, scenario_ids=["scenario-01"])
    assert report["status"] == "refused" and sorted(report["providers"]) == ["codex"]
    codex = report["providers"]["codex"]
    assert codex["status"] == "refused"
    assert codex["failure_detail"]["step"] == "global_observation"
    assert codex["failure_detail"]["reason"] == "runtime input directory contains a nonregular entry"
    assert str(tmp_path) not in json.dumps(codex["failure_detail"])
    assert not (world["authority"].custody / live_admission.LEDGER).exists()
    assert starts(world["counter"]) == 0


def test_preflight_refuses_unsealed_manifest(world):
    from testing.h_eval import prelaunch
    unsealed = {**world["runtime"], "lifecycle": {"state": "captured", "sealed_sha256": None}}
    report = prelaunch.check_observation(unsealed, source_root=ROOT, scenario_ids=["scenario-01"])
    assert report["status"] == "refused" and report["providers"] == {}
    assert report["failure_detail"]["step"] == "runtime_manifest"


def test_preflight_cli_exit_codes(world, tmp_path, capsys):
    from testing.h_eval import prelaunch
    manifest = tmp_path / "runtime-inputs.json"
    manifest.write_text(json.dumps(world["runtime"]))
    assert prelaunch.main(["--source-root", str(ROOT), "--runtime-inputs", str(manifest),
                           "--scenario", "scenario-01"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "ready"
    os.mkfifo(world["skills"] / "pipe")
    assert prelaunch.main(["--source-root", str(ROOT), "--runtime-inputs", str(manifest),
                           "--scenario", "scenario-01"]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "refused"
    assert prelaunch.main(["--source-root", str(ROOT), "--runtime-inputs", str(manifest),
                           "--scenario", "scenario-15"]) == 2
    assert prelaunch.main(["--runtime-inputs", str(manifest)]) == 2
    os.remove(world["skills"] / "pipe")
    (world["skills"] / DANGLING).unlink()
    assert prelaunch.main(["--source-root", str(ROOT), "--runtime-inputs", str(manifest),
                           "--scenario", "scenario-05"]) == 0
    assert json.loads(capsys.readouterr().out)["providers"]["antigravity"]["global_scope"] == "absent-root"
    # The retired opt-in is a usage error, never a silent no-op.
    assert prelaunch.main(["--source-root", str(ROOT), "--runtime-inputs", str(manifest),
                           "--scenario", "scenario-05", "--allow-ancestor-walk"]) == 2
