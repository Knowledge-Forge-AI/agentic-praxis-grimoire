"""APG166W-H-POSTRUN1: keep failed provider-return evidence before post-run checks.

CALIBRATION2 returned from its runner with exit 1, empty stdout and 850
stderr bytes.  The arm then refused at ``observation_finish`` because a
manifest-bound operator settings file changed, and the unchanged owner wrote
the raw streams only after that check, so only their digests survived.  Strict
readback later refused current runtime drift and consumers kept only that
refusal.

These tests reproduce that loss and exercise the corrected owner through the
real live arm path: a temporary operator HOME with manifest-bound settings
files, disposable decision/grant/custody records (``h_live_fixtures``), the
real ``construct_arm``/``provider.run``/observation/runtime owners and a local
counting fake provider that emits raw stdout/stderr and performs one planned
filesystem mutation.  Nothing reads or writes the operator's real settings,
custody or historical arms.  New owners are looked up at call time so the
reproduction test collects on the unchanged entry source.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from agent_phase.provider import MAX_STAGE_OUTPUT_BYTES
from testing.h_eval import execution, granted_execution, live_admission, runtime_manifest
from h_live_fixtures import ROOT, Authority, binary_pattern, fake_provider, starts

UNIT, ADAPTIVE = "scenario-01/static", "scenario-01/adaptive"
PAYLOAD = b"FIXTURE-STDERR-MARKER provider diagnostic \xff\xfe raw bytes\n" * 17
FOREIGN = b"FIXTURE-FOREIGN-BYTES planted before retention\n"
EMPTY_SHA = hashlib.sha256(b"").hexdigest()
DRIFT_REASON = "manifest-bound operator settings changed during arm"
TARGET_DRIFT = "runtime file or executable target drift"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _home(tmp: Path) -> Path:
    home = tmp / "home"
    (home / ".agents" / "skills").mkdir(parents=True)
    operator = home / "operator"
    operator.mkdir()
    for name, text in (("settings.json", '{"fixture": true}\n'), ("config.toml", "fixture = true\n")):
        (operator / name).write_text(text)
        (operator / name).chmod(0o644)
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


def _world(tmp_path, monkeypatch, **provider_options) -> dict:
    home = tmp_path / "home"
    options = {key: (value(home) if callable(value) else value) for key, value in provider_options.items()}
    _home(tmp_path)
    provider, counter = fake_provider(tmp_path / "fixture", **options)
    runtime = _sealed(provider, home)
    return {"authority": Authority(tmp_path, monkeypatch, runtime), "runtime": runtime, "counter": counter,
            "tmp": tmp_path, "home": home, "settings": home / "operator/settings.json",
            "config": home / "operator/config.toml"}


def _settings(home: Path) -> str:
    return str(home / "operator/settings.json")


def _identity(path: Path) -> tuple:
    info = path.lstat()
    return path.read_bytes(), info.st_ino, stat.S_IMODE(info.st_mode)


def _custody(world) -> dict:
    root = world["authority"].custody
    return {str(path.relative_to(root)): (stat.S_IMODE(path.lstat().st_mode),
                                          path.read_bytes() if path.is_file() else None)
            for path in sorted(root.rglob("*"))}


def _run(world, name="arm", *, oracle=None, monkeypatch=None) -> tuple[dict, dict, dict]:
    authorization = world["authority"].grant([UNIT])
    before = {"custody": _custody(world), "settings": _identity(world["settings"]),
              "config": _identity(world["config"])}
    if oracle is not None:
        from testing.h_eval import oracles
        monkeypatch.setattr(oracles, "oracle_for", lambda scenario: oracle)
    result = execution.construct_arm(
        arm_dir=world["tmp"] / name, source_root=ROOT, scenario_id="scenario-01", mode="static",
        execution="live", runtime_inputs=world["runtime"], live_authorization=authorization,
    )
    return result, authorization, before


def _oracle(subject, returned, scenario):
    return {"schema": "apg.h-task-oracle/v1", "oracle": scenario["expected_outcome"]["quality_oracle"],
            "status": "fail", "evidence": [{"kind": "test-double", "sha256": "0" * 64, "bytes": 0}]}


def _one_start_no_replay(world, result, authorization, before, *, planned: bytes | None = None,
                         name="arm", refusal: str = "already consumed") -> None:
    """Shared invariants: one start, no retry, no replay, no custody rewrite.

    While runtime drift persists the replay is refused by the runtime guard
    before the ledger is consulted; ``refusal`` names that exact reason.
    """
    assert starts(world["counter"]) == 1
    assert (result["provider_invocations"], result["retries"], result["restarts"]) == (1, 0, 0)
    if result["status"] != "complete":
        assert result["failure_detail"]["step"] not in live_admission.PRE_PROVIDER_STEPS
    custody = _custody(world)
    ledger = str(live_admission._ledger_path(world["authority"].custody, UNIT).relative_to(
        world["authority"].custody))
    assert set(custody) - set(before["custody"]) == {live_admission.LEDGER, ledger}
    assert all(custody[key] == value for key, value in before["custody"].items())
    assert not (world["authority"].custody / live_admission.REPLACEMENT_LEDGER).exists()
    with pytest.raises(ValueError, match=refusal):
        execution.construct_arm(
            arm_dir=world["tmp"] / f"{name}-replay", source_root=ROOT, scenario_id="scenario-01",
            mode="static", execution="live", runtime_inputs=world["runtime"],
            live_authorization=authorization,
        )
    assert not (world["tmp"] / f"{name}-replay").exists()
    assert starts(world["counter"]) == 1 and _custody(world) == custody
    assert _identity(world["config"]) == before["config"]
    if planned is None:
        assert _identity(world["settings"]) == before["settings"]
    else:
        assert world["settings"].read_bytes() == planned
    retained = (world["tmp"] / name / "result.json").read_bytes()
    for marker in (b"FIXTURE-STDERR-MARKER", b"FIXTURE-FOREIGN", b"edited by fake provider", b'"fixture": true'):
        assert marker not in retained


def _stream(world, name, stream) -> bytes:
    return (world["tmp"] / name / "run" / f"provider.{stream}").read_bytes()


def _forbid_subprocess(monkeypatch):
    def refuse(*_args, **_kwargs):
        raise AssertionError("diagnostic readback must not spawn a process")

    for name in ("run", "Popen", "check_output", "check_call", "call"):
        monkeypatch.setattr(subprocess, name, refuse)


def _reseal(arm_dir: Path, change) -> None:
    result = json.loads((arm_dir / "result.json").read_text())
    change(result)
    (arm_dir / "result.json").unlink()
    execution._write_json(arm_dir / "result.json", result)
    (arm_dir / "integrity.json").unlink()
    execution._persist_integrity(arm_dir)


def _drift_world(tmp_path, monkeypatch, **options):
    return _world(tmp_path, monkeypatch, write=_settings, exit_code=1, stdout=False, stderr=PAYLOAD, **options)


# --- reproduction: the incident shape -------------------------------------


def test_settings_drift_retains_known_stderr(tmp_path, monkeypatch):
    """Red on the entry owner: exit 1, empty stdout, stderr, then settings drift."""
    world = _drift_world(tmp_path, monkeypatch)
    result, authorization, before = _run(world)
    assert starts(world["counter"]) == 1
    assert result["status"] == "incomplete" and result["failure"] == "ValueError"
    assert result["failure_detail"]["step"] == "observation_finish"
    assert result["failure_detail"]["reason"] == DRIFT_REASON
    assert result["provider_terminal"]["exit_code"] == 1
    arm = tmp_path / "arm"
    assert (arm / "run/provider.stderr").is_file(), "provider stderr was not retained before the settings check"
    assert _stream(world, "arm", "stderr") == PAYLOAD
    assert _stream(world, "arm", "stdout") == b""
    terminal = result["provider_terminal"]
    assert terminal["stderr"] == {"bytes": len(PAYLOAD), "sha256": _sha(PAYLOAD)}
    assert terminal["stdout"] == {"bytes": 0, "sha256": EMPTY_SHA}
    checks = result["postrun_checks"]
    assert checks["schema"] == "apg.h-arm-postrun/v1"
    assert "Neither value is a validated model start" in checks["invocation_semantics"]
    provider_return = checks["provider_return"]
    assert provider_return["status"] == "retained" and provider_return["event"] == "runner_returned"
    assert provider_return["model_start"] == "not_established"
    # The transport failure is recorded although the settings refusal came first.
    assert (provider_return["exit_code"], provider_return["transport"]) == (1, "failed")
    assert provider_return["streams"]["stderr"] == {
        "path": "run/provider.stderr", "bytes": len(PAYLOAD), "sha256": _sha(PAYLOAD),
        "truncated": False, "status": "retained"}
    # Both independent failures survive together.
    observation = checks["observation"]
    assert observation["status"] == "drift" and observation["refusing"] == ["settings"]
    assert observation["failure_detail"]["reason"] == DRIFT_REASON
    assert observation["settings"]["compared"] == 2
    [row] = observation["settings"]["changed"]
    assert row["path"] == str(world["settings"])
    assert {"bytes", "sha256"} <= set(row["changed_fields"]) <= {"bytes", "sha256", "inode"}
    assert row["after"]["sha256"] == _sha(b"edited by fake provider\n")
    assert [item["component"] for item in observation["informational"]] == ["run_root"]
    # The failed post-run runtime check no longer looks pre-run valid/pending.
    runtime = result["runtime_revalidation"]
    assert (runtime["status"], runtime["pre_run"], runtime["post_run"]) == ("invalid", "valid", "failed")
    assert runtime["transaction"]["revalidate"] == "failed"
    assert runtime["failure_detail"]["reason"] == "runtime file or executable target drift"
    assert [row["path"] for row in runtime["drift"]["rows"]] == [str(world["settings"])]
    assert checks["runtime_close"]["status"] == "failed"
    assert result["settings_receipt"] is None
    _one_start_no_replay(world, result, authorization, before, planned=b"edited by fake provider\n",
                         refusal=TARGET_DRIFT)


def test_content_drift_after_clean_exit_keeps_streams(tmp_path, monkeypatch):
    world = _world(tmp_path, monkeypatch, write=_settings, stderr=PAYLOAD)
    result, authorization, before = _run(world)
    assert result["failure_detail"]["step"] == "observation_finish"
    assert result["provider_terminal"]["exit_code"] == 0
    assert b"thread.started" in _stream(world, "arm", "stdout")
    assert _stream(world, "arm", "stderr") == PAYLOAD
    provider_return = result["postrun_checks"]["provider_return"]
    assert (provider_return["exit_code"], provider_return["transport"]) == (0, "ok")
    [row] = result["postrun_checks"]["observation"]["settings"]["changed"]
    assert {"bytes", "sha256"} <= set(row["changed_fields"])
    _one_start_no_replay(world, result, authorization, before, planned=b"edited by fake provider\n",
                         refusal=TARGET_DRIFT)


@pytest.mark.parametrize("kind", ["replace", "chmod"])
def test_metadata_only_settings_change_still_refuses(tmp_path, monkeypatch, kind):
    option = {"replace": _settings} if kind == "replace" else {"chmod": lambda home: (_settings(home), 0o600)}
    world = _world(tmp_path, monkeypatch, **option)
    original = world["settings"].read_bytes()
    result, authorization, before = _run(world)
    assert result["status"] == "incomplete"
    assert result["failure_detail"]["reason"] == DRIFT_REASON
    [row] = result["postrun_checks"]["observation"]["settings"]["changed"]
    assert row["changed_fields"] == (["inode"] if kind == "replace" else ["mode"])
    assert world["settings"].read_bytes() == original
    if kind == "chmod":
        assert row["before"]["mode"] == 0o644 and row["after"]["mode"] == 0o600
    _one_start_no_replay(world, result, authorization, before, planned=original, refusal=TARGET_DRIFT)


def test_empty_stdout_nonzero_exit_is_retained(tmp_path, monkeypatch):
    world = _world(tmp_path, monkeypatch, exit_code=1, stdout=False)
    result, authorization, before = _run(world)
    assert result["failure_detail"]["step"] == "provider_terminal"
    assert result["failure_detail"]["reason"] == "provider transport did not complete"
    assert _stream(world, "arm", "stdout") == b"" and _stream(world, "arm", "stderr") == b""
    assert result["provider_terminal"]["stdout"] == {"bytes": 0, "sha256": EMPTY_SHA}
    checks = result["postrun_checks"]
    assert (checks["provider_return"]["exit_code"], checks["provider_return"]["transport"]) == (1, "failed")
    assert checks["observation"]["status"] == "valid" and checks["observation"]["refusing"] == []
    assert checks["runtime_close"]["status"] == "valid"
    assert result["runtime_revalidation"]["post_run"] == "valid"
    _one_start_no_replay(world, result, authorization, before)


def test_truncated_binary_stderr_keeps_exact_head(tmp_path, monkeypatch):
    size = MAX_STAGE_OUTPUT_BYTES + 1
    world = _world(tmp_path, monkeypatch, exit_code=1, stderr_bytes=size)
    result, authorization, before = _run(world)
    head = binary_pattern(size)[:MAX_STAGE_OUTPUT_BYTES]
    assert _stream(world, "arm", "stderr") == head
    terminal = result["provider_terminal"]
    assert terminal["stderr_truncated"] is True and terminal["stderr"]["sha256"] == _sha(head)
    stream = result["postrun_checks"]["provider_return"]["streams"]["stderr"]
    assert stream["truncated"] is True and stream["status"] == "retained"
    assert result["postrun_checks"]["provider_return"]["transport"] == "failed"
    assert result["failure_detail"]["step"] == "provider_terminal"
    _one_start_no_replay(world, result, authorization, before)


def test_failure_after_observation_keeps_all_postrun_outcomes(tmp_path, monkeypatch):
    world = _world(tmp_path, monkeypatch, stdout=False, stderr=PAYLOAD)
    result, authorization, before = _run(world)
    assert result["failure_detail"]["step"] == "provider_import"
    assert result["failure_detail"]["reason"] == "provider terminal result is not importable"
    assert _stream(world, "arm", "stdout") == b"" and _stream(world, "arm", "stderr") == PAYLOAD
    checks = result["postrun_checks"]
    assert checks["provider_return"]["status"] == "retained"
    assert checks["observation"]["status"] == "valid"
    assert checks["runtime_close"] == {"status": "valid", "revalidate": "valid", "close": "valid"}
    _one_start_no_replay(world, result, authorization, before)


def test_runtime_close_failure_replaces_pre_run_record(tmp_path, monkeypatch):
    world = _world(tmp_path, monkeypatch, create=lambda home: (str(home / "absent-setting"), b"x\n"))
    result, authorization, before = _run(world)
    assert result["failure_detail"]["step"] == "runtime_close"
    assert result["failure_detail"]["reason"] == "previously absent runtime setting appeared"
    runtime = result["runtime_revalidation"]
    assert (runtime["status"], runtime["pre_run"], runtime["post_run"]) == ("invalid", "valid", "failed")
    assert runtime["transaction"]["close"] == "failed"
    rows = runtime["drift"]["rows"]
    assert {"path": str(world["home"] / "absent-setting"), "groups": ["absent_settings"],
            "status": "appeared"} in rows
    checks = result["postrun_checks"]
    assert checks["observation"]["status"] == "valid" and checks["runtime_close"]["status"] == "failed"
    assert checks["provider_return"]["status"] == "retained"
    _one_start_no_replay(world, result, authorization, before,
                         refusal="previously absent runtime setting appeared")


def test_retention_failure_stays_visible(tmp_path, monkeypatch):
    world = _world(tmp_path, monkeypatch, stderr=PAYLOAD, create=("../run/provider.stderr", FOREIGN))
    result, authorization, before = _run(world)
    assert _stream(world, "arm", "stderr") == FOREIGN  # never overwritten or removed
    provider_return = result["postrun_checks"]["provider_return"]
    assert provider_return["status"] == "partial"
    assert (provider_return["exit_code"], provider_return["transport"]) == (0, "ok")
    stderr = provider_return["streams"]["stderr"]
    assert stderr["status"] == "write_failed" and stderr["failure_detail"]["type"] == "FileExistsError"
    assert stderr["sha256"] == _sha(PAYLOAD)  # the returned identity, not the foreign file
    assert provider_return["streams"]["stdout"]["status"] == "retained"
    assert result["failure_detail"]["step"] == "provider_terminal"
    assert result["failure_detail"]["reason"] == "provider return was not fully retained"
    assert result["postrun_checks"]["observation"]["status"] == "valid"
    _one_start_no_replay(world, result, authorization, before)


@pytest.mark.parametrize("where", ["provider_environment", "provider_invoke"])
def test_runner_that_never_returned_is_not_a_provider_return(tmp_path, monkeypatch, where):
    world = _world(tmp_path, monkeypatch)

    def refused(_environment):
        if where == "provider_environment":
            raise ValueError("fixture provider runner unavailable")

        def run(*_args, **_kwargs):
            raise OSError("fixture runner refused")

        return run

    monkeypatch.setattr(execution, "_bound_provider_runner", refused)
    result, _authorization, _before = _run(world)
    assert result["failure_detail"]["step"] == where
    assert result["provider_invocations"] == 1 and starts(world["counter"]) == 0
    checks = result["postrun_checks"]
    assert checks["provider_return"] == {"status": "not_run"}
    assert checks["observation"] == {"status": "not_run"}
    assert checks["runtime_close"]["status"] == "valid"
    assert "provider_terminal" not in result
    assert not (tmp_path / "arm/run/provider.stdout").exists()
    assert not (tmp_path / "arm/run/provider.stderr").exists()


def test_clean_success_retains_exact_streams(tmp_path, monkeypatch):
    stderr = b"\x00\xffbinary-ok\n"
    world = _world(tmp_path, monkeypatch, stderr=stderr)
    result, authorization, before = _run(world, oracle=_oracle, monkeypatch=monkeypatch)
    assert result["status"] == "complete", result.get("failure_detail")
    arm = tmp_path / "arm"
    assert _stream(world, "arm", "stderr") == stderr
    assert (arm / "oracle-input/provider.stderr").read_bytes() == stderr
    assert (arm / "oracle-input/provider.stdout").read_bytes() == _stream(world, "arm", "stdout")
    checks = result["postrun_checks"]
    assert checks["provider_return"]["status"] == "retained"
    assert checks["observation"]["status"] == "valid"
    assert checks["runtime_close"]["status"] == "valid"
    readback = execution.read_arm_result(arm)
    assert readback["qualification_eligibility"]["status"] == "eligible"
    with pytest.raises(ValueError, match="limited to incomplete"):
        execution.read_arm_diagnostic(arm)
    _one_start_no_replay(world, result, authorization, before)


# --- diagnostic failed-evidence readback ----------------------------------


def test_diagnostic_reads_failed_arm_despite_current_drift(tmp_path, monkeypatch):
    world = _drift_world(tmp_path, monkeypatch)
    _run(world)
    arm = tmp_path / "arm"
    with pytest.raises(ValueError, match="runtime file or executable target drift"):
        execution.read_arm_result(arm)
    count = starts(world["counter"])
    _forbid_subprocess(monkeypatch)
    diagnostic = execution.read_arm_diagnostic(arm)
    assert diagnostic["schema"] == "apg.h-arm-diagnostic/v1"
    assert diagnostic["qualification"] == {"status": "not_qualification", "eligible": False,
                                           "aggregation": "excluded"}
    assert diagnostic["result_is_current"] is False
    assert diagnostic["strict_readback"] == "not_performed_by_diagnostic_reader"
    assert diagnostic["outcome"]["status"] == "incomplete"
    assert diagnostic["outcome"]["failure_detail"]["step"] == "observation_finish"
    assert diagnostic["outcome"]["provider_invocations"] == 1
    stderr = diagnostic["raw_streams"]["stderr"]
    assert stderr["status"] == "retained" and stderr["matches_terminal"] is True
    assert stderr["sha256"] == _sha(PAYLOAD)
    assert diagnostic["runtime_post_run"] == "failed_at_run" and diagnostic["missing_evidence"] == []
    current = diagnostic["current_runtime"]
    assert current["status"] == "observed" and "not the historical" in current["scope"]
    assert [row["path"] for row in current["report"]["rows"]] == [str(world["settings"])]
    assert starts(world["counter"]) == count
    assert b"FIXTURE-STDERR-MARKER" not in json.dumps(diagnostic).encode()


@pytest.mark.parametrize("tamper", ["bytes", "mode", "delete", "result"])
def test_diagnostic_refuses_changed_retained_evidence(tmp_path, monkeypatch, tamper):
    world = _drift_world(tmp_path, monkeypatch)
    _run(world)
    arm = tmp_path / "arm"
    stderr = arm / "run/provider.stderr"
    if tamper == "bytes":
        stderr.write_bytes(PAYLOAD[:-1] + b"?")
    elif tamper == "mode":
        stderr.chmod(0o644)
    elif tamper == "delete":
        stderr.unlink()
    else:
        path = arm / "result.json"
        path.write_bytes(path.read_bytes().replace(b'"incomplete"', b'"incomplete" '))
    with pytest.raises(ValueError, match="changed|lost"):
        execution.read_arm_diagnostic(arm)


def test_diagnostic_refuses_success_claims(tmp_path, monkeypatch):
    world = _drift_world(tmp_path, monkeypatch)
    _run(world)
    arm = tmp_path / "arm"
    _reseal(arm, lambda value: value.update(qualification_eligibility={"status": "eligible"}))
    with pytest.raises(ValueError, match="claims qualification"):
        execution.read_arm_diagnostic(arm)
    _reseal(arm, lambda value: value.update(qualification_eligibility=None, status="complete"))
    with pytest.raises(ValueError, match="limited to incomplete"):
        execution.read_arm_diagnostic(arm)
    _reseal(arm, lambda value: value.update(status="incomplete", failure=None))
    with pytest.raises(ValueError, match="no failure"):
        execution.read_arm_diagnostic(arm)


@pytest.mark.parametrize("runtime_retained", [True, False])
def test_diagnostic_discloses_historical_shape(tmp_path, monkeypatch, runtime_retained):
    """The CALIBRATION2 shape: streams absent and a stale pre-run-valid record."""
    world = _drift_world(tmp_path, monkeypatch)
    _run(world)
    arm = tmp_path / "arm"
    for name in ("stdout", "stderr"):
        (arm / f"run/provider.{name}").unlink()
    if not runtime_retained:
        (arm / "runtime-inputs.json").unlink()

    def historical(value):
        value.pop("postrun_checks")
        value["runtime_revalidation"] = {key: value["runtime_revalidation"][key]
                                         for key in ("lifecycle", "manifest_sha256", "schema", "test_only")}
        value["runtime_revalidation"].update(status="valid", pre_run="valid", post_run="pending")
        value["authority"] = {"read_only": False, "unchanged": True}

    _reseal(arm, historical)
    _forbid_subprocess(monkeypatch)
    diagnostic = execution.read_arm_diagnostic(arm)
    stderr = diagnostic["raw_streams"]["stderr"]
    assert stderr == {"status": "absent_original_not_retained",
                      "expected": {"bytes": len(PAYLOAD), "sha256": _sha(PAYLOAD)}}
    assert diagnostic["postrun_checks"] is None
    assert diagnostic["runtime_post_run"] == "unverified"
    assert diagnostic["runtime_revalidation"]["status"] == "valid"  # retained, not re-labelled
    joined = "\n".join(diagnostic["missing_evidence"])
    assert "run/provider.stderr: original bytes were not retained" in joined
    assert "postrun_checks: not_recorded" in joined and "pre-run observation only" in joined
    assert diagnostic["qualification"]["eligible"] is False
    if runtime_retained:
        assert diagnostic["current_runtime"]["status"] == "observed"
        assert diagnostic["current_runtime"]["report"]["different"] == 1
    else:
        assert diagnostic["current_runtime"]["status"] == "not_observed"


def test_pair_keeps_failed_arm_explanation_beside_strict_refusal(tmp_path, monkeypatch):
    world = _drift_world(tmp_path, monkeypatch)
    authorization = world["authority"].grant([UNIT, ADAPTIVE])
    record = granted_execution.run_granted_pair(
        pair_dir=tmp_path / "pair", source_root=ROOT, scenario_id="scenario-01",
        live_authorization=authorization, runtime_inputs=world["runtime"],
    )
    assert starts(world["counter"]) == 1 and set(record["arms"]) == {"static"}
    static = record["arms"]["static"]
    assert static["status"] == "readback-invalid"
    assert static["error"] == "ValueError: runtime file or executable target drift"
    diagnostic = static["diagnostic"]
    assert diagnostic["status"] == "retained" and diagnostic["qualification"]["eligible"] is False
    assert diagnostic["failure_detail"]["step"] == "observation_finish"
    assert diagnostic["provider_terminal"]["exit_code"] == 1
    assert diagnostic["raw_streams"]["stderr"]["status"] == "retained"
    assert diagnostic["postrun_checks"]["runtime_close"]["status"] == "failed"
    assert not (tmp_path / "pair/adaptive").exists()
    assert json.loads((tmp_path / "pair/pair.json").read_text()) == record
    assert live_admission.accounting(ROOT, authorization)["unconsumed"] == [ADAPTIVE]
    assert not (world["authority"].custody / live_admission.REPLACEMENT_LEDGER).exists()


def test_runtime_drift_report_is_bounded_and_does_not_execute(tmp_path, monkeypatch):
    world = _world(tmp_path, monkeypatch)
    world["settings"].write_text('{"fixture": false}\n')
    (world["home"] / "absent-setting").write_text("x\n")
    _forbid_subprocess(monkeypatch)
    report = runtime_manifest.drift_report(world["runtime"])
    assert report["schema"] == "apg.h-runtime-drift/v1" and report["versions"] == "not_probed"
    assert (report["different"], report["appeared"], report["unavailable"]) == (1, 1, 0)
    settings = next(row for row in report["rows"] if row["path"] == str(world["settings"]))
    assert settings["groups"] == ["operator_settings"] and settings["status"] == "different"
    assert {"bytes", "sha256"} <= set(settings["changed_fields"]) <= {"bytes", "sha256", "inode"}
    assert set(settings["before"]) == set(settings["after"]) == set(settings["changed_fields"])
    assert b'"fixture": false' not in json.dumps(report).encode()
    with pytest.raises(ValueError, match="previously absent runtime setting appeared"):
        runtime_manifest.verify_complete(world["runtime"])
