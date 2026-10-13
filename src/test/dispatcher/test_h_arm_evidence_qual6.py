"""APG166E single-arm source/evidence ownership tests.

All provider activity in this module is an explicit local fixture executable;
the live admission boundary is tested before any provider process can start.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from testing.h_eval import assembly, execution
from testing.h_eval.evaluate import load
from testing.h_eval.runtime_manifest import (
    REQUIRED_COMMANDS,
    REQUIRED_GROUPS,
    capture_complete,
    seal,
)

ROOT = Path(__file__).resolve().parents[3]


def test_route_retains_source_owned_read_only_tool_authority():
    bindings = load(ROOT / "testing/h_eval/scenario-bindings.json")
    row = next(item for item in bindings["scenarios"] if item["scenario_id"] == "scenario-11")
    route = row["routes"]["adaptive"]
    selected = execution._route(route, "adaptive", "instrumented")
    assert selected["role_binding"] == route["role_binding"]


def _source_copy(tmp_path: Path) -> Path:
    destination = tmp_path / "source"
    shutil.copytree(
        ROOT,
        destination,
        ignore=shutil.ignore_patterns(".git", ".venv", "node_modules", "__pycache__", ".pytest_cache"),
    )
    bindings_path = destination / "testing/h_eval/scenario-bindings.json"
    bindings = json.loads(bindings_path.read_text())
    manifest = destination / "testing/fixtures/context-eval/subjects/manifest.json"
    bindings["subject_manifest"]["sha256"] = hashlib.sha256(manifest.read_bytes()).hexdigest()
    bindings_path.write_text(json.dumps(bindings, indent=2, sort_keys=True) + "\n")
    return destination


def _scenario_and_route(root: Path, number: int = 1):
    scenario_path = next((root / "testing/fixtures/context-eval").glob(f"scenario-{number:02d}-*.json"))
    scenario = load(scenario_path)
    bindings = load(root / "testing/h_eval/scenario-bindings.json")
    row = next(item for item in bindings["scenarios"] if item["scenario_id"] == scenario["scenario_id"])
    return scenario, row, row["routes"]["static"]


def _provider(tmp_path: Path) -> Path:
    script = tmp_path / "instrumented-provider"
    script.write_text(
        f"#!{sys.executable}\n"
        "import json\n"
        "import sys\n"
        "sys.stdin.buffer.read()\n"
        "print(json.dumps({'schema': 'apg.instrumented-provider/v1', 'result': 'fixture', "
        "'producer_revisions': [], 'missing_guidance_findings': [], "
        "'restart_required_incidents': [], 'model_observed': None}))\n"
    )
    script.chmod(0o700)
    return script


def _review_provider(tmp_path: Path, response: dict[str, object]) -> Path:
    script = tmp_path / "instrumented-review-provider"
    payload = json.dumps(response, sort_keys=True)
    script.write_text(
        f"#!{sys.executable}\n"
        "import json\n"
        "import sys\n"
        "sys.stdin.buffer.read()\n"
        f"print(json.dumps({{'type': 'result', 'subtype': 'success', 'result': {payload}}}))\n"
    )
    script.chmod(0o700)
    return script


def _oracle(scenario):
    return {
        "schema": "apg.h-task-oracle/v1",
        "oracle": scenario["expected_outcome"]["quality_oracle"],
        "status": "pass",
        "evidence": [{"kind": "source-owned-test-fixture", "sha256": "0" * 64, "bytes": 0}],
    }


def _runtime(provider: Path, source: Path, tmp_path: Path):
    git = Path(shutil.which("git") or "/usr/bin/git")
    return seal(capture_complete(
        providers={name: (provider, ["--version"]) for name in ("codex", "claude", "antigravity")},
        commands={name: ((git, ["--version"]) if name == "git" else (provider, ["--version"]))
                  for name in REQUIRED_COMMANDS},
        groups={group: [source] for group in REQUIRED_GROUPS},
        routes={"fixture": "arm-evidence"},
        absent_settings=[tmp_path / "absent-setting"],
        environment={"home": str(tmp_path), "temp_root": str(tmp_path)},
    ))


def test_construct_arm_derives_source_contract_subject_route_and_receipts(tmp_path):
    root = _source_copy(tmp_path)
    provider = _provider(tmp_path)
    scenario, row, _route = _scenario_and_route(root)
    result = execution.construct_arm(
        arm_dir=tmp_path / "arm",
        source_root=root,
        scenario_id=scenario["scenario_id"],
        mode="static",
        executable_paths={"codex_executable": str(provider)},
        test_oracle=lambda subject, returned, value: _oracle(value),
    )
    assert result["status"] == "complete"
    assert result["provider_invocations"] == 1
    assert result["route"]["source_identity"]["scenario_sha256"] == row["scenario_sha256"]
    assert result["construction"]["schema"] == execution.CONSTRUCTION_SCHEMA
    assert result["construction"]["subject_factory"]["owner"] == "testing.h_eval.subjects"
    assert result["construction"]["task_contract"]["schema"] == "apg.h-task-contract/v1"
    assert result["construction"]["oracle"]["status"] == "instrumented-fixture"
    retained = execution.read_arm_result(tmp_path / "arm")
    assert retained["evidence_owner"]["path"] == "oracle-input/identity.json"
    assert retained["runtime_revalidation"] is not None
    assert (tmp_path / "arm/oracle-input/provider.stdout").stat().st_mode & 0o007 == 0


def test_construct_arm_real_source_oracle_retains_exact_context_bytes(tmp_path):
    root = _source_copy(tmp_path)
    scenario, _row, _route = _scenario_and_route(root, number=3)
    from testing.h_eval.oracles import _fixture_review_response
    response = _fixture_review_response(scenario["scenario_id"], True)
    provider = _review_provider(tmp_path, response)
    result = execution.construct_arm(
        arm_dir=tmp_path / "arm",
        source_root=root,
        scenario_id=scenario["scenario_id"],
        mode="static",
        executable_paths={"claude_launcher": str(provider)},
    )
    assert result["status"] == "complete", result
    retained = execution.read_arm_result(tmp_path / "arm")
    context_path = tmp_path / "arm/run/attempt.context-plan.json"
    oracle_context_path = tmp_path / "arm/oracle-input/context-plan.json"
    assert context_path.read_bytes() == oracle_context_path.read_bytes()
    assert retained["prepared"]["record"]["configuration"] == result["route"]["source_identity"]["identity_sources"]
    assert retained["task_oracle"]["status"] == "pass"


def test_native_instruction_argument_binds_rtk_component(tmp_path):
    from testing.h_eval import oracles
    provider = _provider(tmp_path)
    result = execution.construct_arm(
        arm_dir=tmp_path / "arm", source_root=ROOT,
        scenario_id="scenario-04", mode="static",
        executable_paths={"codex_executable": str(provider)},
        test_oracle=lambda subject, returned, value: _oracle(value),
    )
    assert result["status"] == "complete"
    run = tmp_path / "arm/run"
    context = json.loads((run / "attempt.context-plan.json").read_bytes())
    events = json.loads((run / "attempt.context-deliveries.json").read_bytes())["events"]
    assert oracles._instruction_delivery_check({"context": context, "events": events})[0]
    argument = next(index for index, value in enumerate(context["transport"]["argv"])
                    if value.startswith("developer_instructions="))
    context["transport"]["argv"][argument] += "changed"
    assert not oracles._instruction_delivery_check({"context": context, "events": events})[0]


def test_live_source_context_uses_the_same_projection_bridge(tmp_path):
    scenario, row, _ = _scenario_and_route(ROOT, number=11)
    route = {**row["routes"]["adaptive"], "execution": "live"}
    route["source_identity"] = execution._frozen_inputs(ROOT, "scenario-11", "adaptive")[3]
    prepared = execution._source_context_inputs(
        source_root=ROOT, subject=tmp_path, run=tmp_path, scenario=scenario,
        route=route, mode="adaptive", runtime_inputs=None,
    )
    assert prepared["projection"] is not None
    assert prepared["projection"].scenario_id == scenario["scenario_id"]


def test_instrumented_constructor_has_no_default_provider_path(tmp_path):
    root = _source_copy(tmp_path)
    scenario, _row, _route = _scenario_and_route(root)
    with pytest.raises(ValueError, match="explicit fake runner or executable"):
        execution.construct_arm(
            arm_dir=tmp_path / "arm",
            source_root=root,
            scenario_id=scenario["scenario_id"],
            mode="static",
            test_oracle=lambda subject, returned, value: _oracle(value),
        )
    assert not (tmp_path / "arm").exists()


def test_instrumented_constructor_rejects_external_task_executable(tmp_path):
    root = _source_copy(tmp_path)
    scenario, _row, _route = _scenario_and_route(root)
    external = tmp_path.parent / f"external-provider-{tmp_path.name}"
    external.write_text(f"#!{sys.executable}\nraise SystemExit(0)\n")
    external.chmod(0o700)
    try:
        with pytest.raises(ValueError, match="arm-owned"):
            execution.construct_arm(
                arm_dir=tmp_path / "arm",
                source_root=root,
                scenario_id=scenario["scenario_id"],
                mode="static",
                executable_paths={"codex_executable": str(external)},
                test_oracle=lambda subject, returned, value: _oracle(value),
            )
    finally:
        external.unlink()
    assert not (tmp_path / "arm").exists()


def test_arm_git_authority_uses_closed_test_environment_and_no_hooks(tmp_path, monkeypatch):
    root = _source_copy(tmp_path)
    provider = _provider(tmp_path)
    git = Path(shutil.which("git") or "/usr/bin/git").resolve()
    scenario, _row, _route = _scenario_and_route(root)
    calls = []
    original_run = execution.subprocess.run

    def observed_run(*args, **kwargs):
        argv = list(args[0])
        if Path(argv[0]).name == "git":
            calls.append((argv, dict(kwargs.get("env", {}))))
        return original_run(*args, **kwargs)

    monkeypatch.setattr(execution.subprocess, "run", observed_run)
    execution.construct_arm(
        arm_dir=tmp_path / "arm",
        source_root=root,
        scenario_id=scenario["scenario_id"],
        mode="static",
        executable_paths={"codex_executable": str(provider), "git_executable": str(git)},
        test_oracle=lambda subject, returned, value: _oracle(value),
    )
    assert calls
    for argv, environment in calls:
        assert ["-c", "core.hooksPath=/dev/null"] == argv[1:3]
        assert environment["GIT_CONFIG_NOSYSTEM"] == "1"
        assert environment["GIT_CONFIG_GLOBAL"] == "/dev/null"
        assert environment["GIT_CONFIG_SYSTEM"] == "/dev/null"
        assert environment["GIT_TERMINAL_PROMPT"] == "0"
        assert environment["PATH"] == str(git.parent)
        assert environment is not os.environ


def test_live_bindings_keep_source_wrappers_separate_from_provider_binaries(tmp_path):
    root = _source_copy(tmp_path)
    provider = _provider(tmp_path)
    runtime = _runtime(provider, root / "README.md", tmp_path)
    paths, bindings = execution._live_provider_bindings(root, runtime)
    assert paths["claude_launcher"] == str(root / "bin/claude-profile")
    assert paths["antigravity_launcher"] == str(root / "bin/antigravity-profile")
    assert paths["claude_launcher"] != paths["claude_executable"]
    assert paths["antigravity_launcher"] != paths["antigravity_executable"]
    assert bindings["launchers"]["claude"]["sha256"]
    assert bindings["launchers"]["antigravity"]["sha256"]
    assert bindings["provider_executables"]["claude"]["path"] == paths["claude_executable"]
    assert bindings["environment"]["source"] == "runtime-manifest"


def test_live_provider_runner_passes_bound_environment_without_mutating_process(tmp_path, monkeypatch):
    observed = {}

    def fake_provider(*args, **kwargs):
        observed["environment"] = kwargs.pop("environment")
        observed["args"] = args
        return "fixture-result"

    monkeypatch.setattr(execution.provider, "run", fake_provider)
    environment = {"PATH": str(tmp_path), "HOME": str(tmp_path), "GIT_CONFIG_NOSYSTEM": "1"}
    runner = execution._bound_provider_runner(environment)
    assert runner(["source-wrapper"], b"prompt", tmp_path) == "fixture-result"
    assert observed["environment"] == environment
    assert "PATH" not in observed["args"]


def test_assembly_accepts_only_a_post_revalidated_retained_arm(tmp_path):
    root = _source_copy(tmp_path)
    provider = _provider(tmp_path)
    scenario, row, _route = _scenario_and_route(root)
    runtime = _runtime(provider, root / "README.md", tmp_path)
    result = execution.construct_arm(
        arm_dir=tmp_path / "arm",
        source_root=root,
        scenario_id=scenario["scenario_id"],
        mode="static",
        executable_paths={"codex_executable": str(provider)},
        runtime_inputs=runtime,
        test_oracle=lambda subject, returned, value: _oracle(value),
    )
    assert result["runtime_revalidation"]["transaction"]["status"] == "owned"
    assert result["runtime_revalidation"]["transaction"]["close"] == "valid"
    assert result["runtime_revalidation"]["test_only"] is True
    result["_arm_dir"] = str(tmp_path / "arm")
    assembled = assembly._receipt_arm(row, "static", result)
    assert assembled["coverage"]["source"] == "unavailable"
    assert "qualification eligibility rejected" in assembled["coverage"]["reason"]


def test_readback_rejects_copied_task_oracle_and_delivery_claims(tmp_path):
    root = _source_copy(tmp_path)
    provider = _provider(tmp_path)
    scenario, _row, _route = _scenario_and_route(root)
    execution.construct_arm(
        arm_dir=tmp_path / "arm",
        source_root=root,
        scenario_id=scenario["scenario_id"],
        mode="static",
        executable_paths={"codex_executable": str(provider)},
        test_oracle=lambda subject, returned, value: _oracle(value),
    )
    result_path = tmp_path / "arm/result.json"
    original = json.loads(result_path.read_text())
    for field, message in (("task_oracle", "task oracle"), ("coverage", "delivery claims")):
        candidate = deepcopy(original)
        if field == "task_oracle":
            candidate[field]["oracle"] = {"forged": True}
        else:
            candidate[field] = "forged-complete"
        result_path.write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n")
        (tmp_path / "arm/integrity.json").unlink()
        execution._persist_integrity(tmp_path / "arm")
        with pytest.raises(ValueError, match=message):
            execution.read_arm_result(tmp_path / "arm")


def test_live_route_rejects_caller_injected_owners_before_provider(tmp_path):
    # Caller injection is refused structurally, before full grant admission,
    # so no decision or grant bytes are read or consumed for this refusal.
    scenario, _row, route = _scenario_and_route(ROOT)
    with pytest.raises(ValueError, match="caller injection"):
        execution.run_one_arm(
            arm_dir=tmp_path / "arm",
            source_root=ROOT,
            scenario=scenario,
            mode="static",
            route={**route, "execution": "live"},
            subject_files={"README.md": b"injected"},
            oracle=lambda *args, **kwargs: pytest.fail("oracle invoked"),
            runner=lambda *args, **kwargs: pytest.fail("provider invoked"),
            live_authorization={"decision_path": str(tmp_path / "decision.json"),
                                "grant_path": str(tmp_path / "grant.json")},
        )
    assert not (tmp_path / "arm").exists()
    assert not (tmp_path / "h-consumed").exists()


def test_exact_recovery_does_not_derive_from_native_read_coverage_alone():
    from testing.h_eval.execution_evidence import derive_exact_recovery

    scope = {"run_id": "run", "binding_id": "binding", "attempt_id": "one"}
    native = {
        "schema": "apg.claude-native-reads/v1",
        "coverage": "complete",
        "scope": scope,
        "session_id": "session",
        "raw_stream": {"bytes": 1, "sha256": "a" * 64},
        "reads": [],
        "events": [],
        "terminal": {"type": "result", "subtype": "success"},
        "recovery_authority": {
            "schema": "apg.h-recovery-authority/v1",
            "scope": scope,
            "session_id": "session",
            "prelaunch": {"status": "captured", "entries": []},
            "postrun": {"status": "verified", "entries": []},
        },
    }
    complete, evidence = derive_exact_recovery(
        {"cohorts": {"exact_recovery": True}},
        result={"replay_authorized": False},
        receipt={
            "route": {"execution": "live"},
            "context": scope,
            "activity": {"attempts": ["one"], "retries": 0, "restarts": 0, "native_reads": native},
            "authority": {
                "permitted": True, "unchanged": True,
                "directories_unchanged": True, "git_unchanged": True,
                "replay_authorized": False,
            },
            "provider_terminal": {"exit_code": 0, "truncated": False, "stderr_truncated": False},
            "acquisitions": [],
        },
    )
    assert complete is False
    assert evidence["value"] is False
    assert "delivery event" in evidence["reason"]


def _exact_recovery_fixture(content: str = "abc"):
    from testing.h_eval.execution_evidence import derive_exact_recovery

    scope = {"run_id": "run", "binding_id": "binding", "attempt_id": "one"}
    entry = {
        "id": "skill",
        "path": "docs/a",
        "bytes": len(content.encode()),
        "sha256": hashlib.sha256(content.encode()).hexdigest(),
    }
    stream_sha = "a" * 64
    read = {
        "id": "tool",
        "input": {"file_path": "/subject/docs/a"},
        "result": {
            "authorized_recovery": entry,
            "structured_file": {
                "filePath": "/subject/docs/a",
                "content": content,
                "startLine": 1,
                "numLines": 1,
                "totalLines": 1,
            },
            "raw_identity": {"bytes": entry["bytes"], "sha256": entry["sha256"]},
        },
    }
    event = {
        "event_id": hashlib.sha256(
            json.dumps([scope, stream_sha, "tool"], sort_keys=True).encode()
        ).hexdigest(),
        **scope,
        "kind": "recovery_read_observed",
        "phase": "late",
        "channel": "recovery_read",
        "controlled_bytes": entry["bytes"],
        "payload_sha256": entry["sha256"],
        "provenance": entry["path"],
        "recovery_entry": entry,
        "requested_path": "/subject/docs/a",
        "tool_use_id": "tool",
        "raw_stream_sha256": stream_sha,
    }
    native = {
        "schema": "apg.claude-native-reads/v1",
        "coverage": "complete",
        "scope": scope,
        "session_id": "session",
        "raw_stream": {"bytes": 10, "sha256": stream_sha},
        "reads": [read],
        "events": [event],
        "terminal": {"type": "result", "subtype": "success", "session_id": "session"},
        "recovery_authority": {
            "schema": "apg.h-recovery-authority/v1",
            "scope": scope,
            "session_id": "session",
            "prelaunch": {"status": "captured", "entries": [entry]},
            "postrun": {"status": "verified", "entries": [entry]},
        },
    }
    receipt = {
        "route": {"execution": "live"},
        "context": scope,
        "activity": {
            "attempts": ["one"], "retries": 0, "restarts": 0, "native_reads": native,
        },
        "authority": {
            "permitted": True, "unchanged": True,
            "directories_unchanged": True, "git_unchanged": True,
            "replay_authorized": False,
        },
        "provider_terminal": {"exit_code": 0, "truncated": False, "stderr_truncated": False},
        "acquisitions": [],
    }
    return native, receipt, {"replay_authorized": False}


def test_exact_recovery_rejects_same_length_payload_and_duplicate_ids():
    from testing.h_eval.execution_evidence import derive_exact_recovery

    native, receipt, result = _exact_recovery_fixture()
    assert derive_exact_recovery(
        {"cohorts": {"exact_recovery": True}}, result=result, receipt=receipt
    )[0] is True

    wrong = deepcopy(native)
    wrong["reads"][0]["result"]["structured_file"]["content"] = "abd"
    assert derive_exact_recovery(
        {"cohorts": {"exact_recovery": True}},
        result=result,
        receipt={**receipt, "activity": {**receipt["activity"], "native_reads": wrong}},
    )[0] is False

    duplicate = deepcopy(native)
    duplicate["reads"].append(deepcopy(duplicate["reads"][0]))
    assert derive_exact_recovery(
        {"cohorts": {"exact_recovery": True}},
        result=result,
        receipt={**receipt, "activity": {**receipt["activity"], "native_reads": duplicate}},
    )[0] is False


def test_qualification_rejects_test_only_and_arbitrary_runtime_identities():
    from testing.h_eval.execution_evidence import qualification_eligibility

    value = qualification_eligibility({
        "source_binding": {
            "schema": "apg.h-source-binding/v1", "owner": "testing.h_eval.preregistration",
            "scenario_id": "scenario-01", "mode": "static",
            "bindings_path": "testing/h_eval/scenario-bindings.json",
            "scenario_path": "testing/fixtures/context-eval/scenario-01.json",
            "bindings_sha256": "a" * 64, "scenario_sha256": "b" * 64,
            "route_sha256": "c" * 64, "source_sha256": {"route": "d" * 64},
            "identity_sources": ["common/dispatcher/routes.toml"],
        },
        "subject_factory": {
            "schema": "apg.h-subject-factory-identity/v1", "owner": "testing.h_eval.subjects",
        },
        "oracle_owner": {
            "schema": "apg.h-oracle-owner/v1", "owner": "testing.h_eval.oracles",
        },
        "task_contract": {"schema": "apg.h-task-contract/v1"},
        "source_seal": {"schema": "apg.h-readiness-seal/v1", "prerequisites_ready": True},
        "runtime": {"schema": "apg.h-runtime-observation/v1", "status": "valid"},
        "route": {"execution": "live"},
    })
    assert value["status"] == "ineligible"
    assert "runtime identity is unavailable or test-only" in value["reasons"]


def test_revision_and_restart_absence_is_explicit_not_success():
    from testing.h_eval.execution_evidence import observation_state

    value = observation_state(None, field="producer_revisions")
    assert value["status"] == "not_observed"
    assert value["value"] is None


def test_empty_directory_growth_is_rejected_by_arm_readback(tmp_path):
    root = _source_copy(tmp_path)
    provider = _provider(tmp_path)
    scenario, _row, _route = _scenario_and_route(root)
    execution.construct_arm(
        arm_dir=tmp_path / "arm",
        source_root=root,
        scenario_id=scenario["scenario_id"],
        mode="static",
        executable_paths={"codex_executable": str(provider)},
        test_oracle=lambda subject, returned, value: _oracle(value),
    )
    (tmp_path / "arm/subject/empty-directory").mkdir()
    with pytest.raises(ValueError, match="directory topology"):
        execution.read_arm_result(tmp_path / "arm")


def test_scenario12_requires_a_retained_recovery_receipt(tmp_path):
    root = _source_copy(tmp_path)
    provider = _provider(tmp_path)
    scenario, _row, route = _scenario_and_route(root, 12)
    provider_key = {"codex": "codex_executable", "claude": "claude_launcher",
                    "antigravity": "antigravity_launcher"}[route["provider"]]
    execution.construct_arm(
        arm_dir=tmp_path / "arm",
        source_root=root,
        scenario_id=scenario["scenario_id"],
        mode="static",
        executable_paths={provider_key: str(provider)},
        test_oracle=lambda subject, returned, value: _oracle(value),
    )
    with pytest.raises(ValueError, match="recovery receipt"):
        execution.read_arm_result(tmp_path / "arm")


def test_assembly_reads_retained_facts_and_rejects_copied_claims(tmp_path):
    root = _source_copy(tmp_path)
    provider = _provider(tmp_path)
    scenario, row, _route = _scenario_and_route(root)
    result = execution.construct_arm(
        arm_dir=tmp_path / "arm",
        source_root=root,
        scenario_id=scenario["scenario_id"],
        mode="static",
        executable_paths={"codex_executable": str(provider)},
        test_oracle=lambda subject, returned, value: _oracle(value),
    )
    result["_arm_dir"] = str(tmp_path / "arm")
    result["coverage"] = "injected-complete"
    assembled = assembly._receipt_arm(row, "static", result)
    assert assembled["coverage"]["source"] == "unavailable"
    assert "retained arm evidence invalid" in assembled["coverage"]["reason"]
