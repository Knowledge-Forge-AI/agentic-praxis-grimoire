#!/usr/bin/env python3
"""Two-runtime qualification for the corrected Node.js candidate."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "libexec"))
sys.path.insert(0, str(ROOT / "src/test/support"))

import apg_test  # noqa: E402
from apg_nodejs_candidate_contract import load_scenarios, validate_candidate  # noqa: E402
from apg_nodejs_fixture_contract import (  # noqa: E402
    load_manifest,
    validate_fixture,
    validate_threat_model,
)


FIXTURE = ROOT / "src/test/fixtures/apg80-nodejs-runtime-cli"
SCENARIOS = ROOT / "src/test/fixtures/apg81-nodejs-runtime-profile-scenarios.json"
THREAT_MODEL = ROOT / "testing/nodejs-profile-qualification-threat-model.json"
ROLES = ("primary", "secondary")


def _invoke(role: str, arguments: list[str], contract: str, expected: object, **kwargs):
    with apg_test.node_profile_invocation(ROOT, contract) as invocation:
        return apg_test.invoke_node_profile_runtime(
            ROOT,
            role,
            arguments,
            invocation=invocation,
            output_contract_id=contract,
            expected_result=expected,
            **kwargs,
        )


def test_candidate_fixture_scenarios_and_two_runtime_roles_are_closed() -> None:
    validate_candidate(
        (ROOT / "skills/nodejs-runtime-profile/SKILL.md").read_text(encoding="utf-8"),
        (ROOT / "docs/specs/nodejs-runtime-profile.md").read_text(encoding="utf-8"),
        (ROOT / "docs/specs/nodejs-runtime-profile-scenario-coverage.md").read_text(encoding="utf-8"),
    )
    validate_fixture(FIXTURE, load_manifest(FIXTURE / "fixture-manifest.json"))
    validate_threat_model(load_manifest(THREAT_MODEL))
    scenarios = load_scenarios(SCENARIOS)
    assert [row["version"] for row in scenarios["authority"]["runtime_roles"]] == [
        "v22.22.2", "v24.19.0"
    ]
    assert apg_test.validate_node_profile_runtimes(ROOT) == (
        "v22.22.2|darwin/arm64|12.4.254.21-node.39|1.51.0",
        "v24.19.0|darwin/arm64|13.6.233.17-node.51|1.52.1",
    )


@pytest.mark.parametrize("role", ROLES)
def test_explicit_commonjs_refusal_and_no_manifest_detection(role: str) -> None:
    source = FIXTURE / "module-mapping/commonjs-package/module-only.js"
    _invoke(
        role,
        [os.fspath(source)],
        f"{role}-explicit-commonjs-refusal",
        None,
        expected_return_code=1,
        stdout_policy="empty",
        stderr_policy="discard",
    )
    contract = f"{role}-no-manifest-detection"
    with apg_test.node_profile_invocation(ROOT, contract) as invocation:
        unscoped = invocation.work / "module-only.js"
        shutil.copyfile(source, unscoped)
        observation = apg_test.invoke_node_profile_runtime(
            ROOT,
            role,
            [os.fspath(unscoped)],
            invocation=invocation,
            output_contract_id=contract,
            expected_result={"mapping": "module-only"},
        )
    assert observation.result == {"mapping": "module-only"}


@pytest.mark.parametrize("role", ROLES)
def test_typescript_stripping_and_nonerasable_control(role: str) -> None:
    assert _invoke(
        role,
        [os.fspath(FIXTURE / "typescript/erasable.ts")],
        f"{role}-typescript-erasable",
        {"label": "erasable"},
    ).result == {"label": "erasable"}
    _invoke(
        role,
        [os.fspath(FIXTURE / "typescript/nonerasable.ts")],
        f"{role}-typescript-nonerasable",
        None,
        expected_return_code=1,
        stdout_policy="empty",
        stderr_policy="discard",
    )


def test_version_sensitive_interop_and_flag_contrasts() -> None:
    module_uri = (FIXTURE / "interop/static-exports.cjs").as_uri()
    source = f"import * as value from {json.dumps(module_uri)}; console.log(JSON.stringify(Object.keys(value)))"
    assert _invoke(
        "primary", ["--input-type=module", "--eval", source],
        "primary-commonjs-namespace", ["alpha", "beta", "default"]
    ).result == ["alpha", "beta", "default"]
    assert _invoke(
        "secondary", ["--input-type=module", "--eval", source],
        "secondary-commonjs-namespace", ["alpha", "beta", "default", "module.exports"]
    ).result == ["alpha", "beta", "default", "module.exports"]
    flag_source = (
        "console.log(JSON.stringify({"
        "defaultType:process.allowedNodeEnvironmentFlags.has('--experimental-default-type')"
        "}))"
    )
    assert _invoke(
        "primary", ["--input-type=module", "--eval", flag_source],
        "primary-default-type-flag", {"defaultType": True}
    ).result == {"defaultType": True}
    assert _invoke(
        "secondary", ["--input-type=module", "--eval", flag_source],
        "secondary-default-type-flag", {"defaultType": False}
    ).result == {"defaultType": False}


@pytest.mark.parametrize("role", ROLES)
def test_filesystem_fixture_accepts_exact_invocation_case(role: str) -> None:
    module_uri = (FIXTURE / "process/filesystem.mjs").as_uri()
    expected = {
        "contentPreserved": True,
        "durabilityProven": False,
        "fileUrlProtocol": "file:",
        "missingCode": "ENOENT",
        "permissionPolicyProven": False,
        "roundTripEqual": True,
        "separator": "/",
    }
    contract = f"{role}-owned-scratch"
    with apg_test.node_profile_invocation(ROOT, contract) as invocation:
        success = (
            f"import {{filesystemBoundary}} from {json.dumps(module_uri)};"
            "console.log(JSON.stringify(await filesystemBoundary("
            f"{json.dumps(os.fspath(invocation.filesystem_case))})))"
        )
        observation = apg_test.invoke_node_profile_runtime(
            ROOT,
            role,
            ["--input-type=module", "--eval", success],
            invocation=invocation,
            output_contract_id=contract,
            expected_result=expected,
        )
        assert observation.result == expected


@pytest.mark.parametrize("role", ROLES)
def test_preexisting_filesystem_case_symlink_is_refused_before_node(
    role: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contract = f"{role}-scratch-symlink-refusal"
    outside = tmp_path / "outside"
    outside.mkdir()
    with apg_test.node_profile_invocation(ROOT, contract) as invocation:
        invocation.filesystem_case.rmdir()
        invocation.filesystem_case.symlink_to(outside, target_is_directory=True)
        runtime_calls = 0

        def runtime_must_not_start(*_args: object, **_kwargs: object):
            nonlocal runtime_calls
            runtime_calls += 1
            raise AssertionError("runtime identity probe started before scratch preflight")

        monkeypatch.setattr(apg_test, "_node_profile_runtime_binding", runtime_must_not_start)
        with pytest.raises(apg_test.ToolError, match="fs-case directory violates"):
            apg_test.invoke_node_profile_runtime(
                ROOT,
                role,
                ["--eval", "throw new Error('must-not-run')"],
                invocation=invocation,
                output_contract_id=contract,
                expected_result={"refused": True},
            )
        assert runtime_calls == 0
    assert list(outside.iterdir()) == []


def test_timeout_reaps_child_and_cleans_invocation_root() -> None:
    contract = "redaction-negative"
    with apg_test.node_profile_invocation(ROOT, contract) as invocation:
        invocation_root = invocation.root
        with pytest.raises(apg_test.NodeProfileQualificationError, match="TimeoutExpired"):
            apg_test.invoke_node_profile_runtime(
                ROOT,
                "primary",
                ["--eval", "setInterval(()=>{},1000)"],
                invocation=invocation,
                output_contract_id=contract,
                expected_result={"secret": "expected-safe-value"},
                timeout=1,
            )
    assert not invocation_root.exists()


def test_timeout_reaps_exact_started_process_before_cleanup() -> None:
    contract = "redaction-negative"
    with apg_test.node_profile_invocation(ROOT, contract) as invocation:
        pid_path = invocation.filesystem_case / "pid"
        script = (
            "require('node:fs').writeFileSync("
            f"{json.dumps(os.fspath(pid_path))},String(process.pid));"
            "setInterval(()=>{},1000)"
        )
        with pytest.raises(apg_test.NodeProfileQualificationError, match="TimeoutExpired"):
            apg_test.invoke_node_profile_runtime(
                ROOT,
                "primary",
                ["--eval", script],
                invocation=invocation,
                output_contract_id=contract,
                expected_result={"secret": "expected-safe-value"},
                timeout=1,
            )
        pid = int(pid_path.read_text(encoding="utf-8"))
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)


def test_closed_output_contract_redacts_raw_streams() -> None:
    sentinel = "synthetic-secret-sentinel"
    encoded = sentinel.encode("utf-8").hex()
    with pytest.raises(apg_test.NodeProfileQualificationError) as captured:
        _invoke(
            "primary",
            ["--input-type=module", "--eval", f"console.log(JSON.stringify({{secret:Buffer.from('{encoded}','hex').toString()}}))"],
            "redaction-negative",
            {"secret": "expected-safe-value"},
        )
    assert sentinel not in str(captured.value)
    traceback = captured.value.__traceback__
    while traceback is not None:
        if traceback.tb_frame.f_code.co_filename.endswith("libexec/apg_test.py"):
            assert sentinel not in repr(traceback.tb_frame.f_locals)
        traceback = traceback.tb_next
