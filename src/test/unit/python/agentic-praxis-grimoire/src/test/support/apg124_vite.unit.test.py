#!/usr/bin/env python3
"""Unit tests for APG124 Vite 8.2.2 support module (apg124_vite.py).

Validates fail-closed refusal contracts for Node identity, Vite/Rolldown package root,
scratch ownership boundaries, scenario register schema, and evaluation receipt completeness.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import pytest

from src.test.apg_test_support import repository_root

ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src/test/support"))

from apg124_vite import (  # noqa: E402
    ALL_SCENARIOS,
    EXPECTED_NODE_SHA256,
    EXPECTED_NODE_VERSION,
    EXPECTED_ROLLDOWN_VERSION,
    EXPECTED_VITE_VERSION,
    VITE_TOOLCHAIN_DISCLAIMER,
    ViteHarnessConfig,
    ViteHarnessError,
    ViteHarnessExecutionError,
    ViteHarnessPrerequisiteError,
    ViteHarnessReceipt,
    ViteHarnessValidationError,
    load_scenarios_register,
    observe_vite_harness_config,
    validate_node_executable,
    validate_prerequisites,
    validate_receipt,
    validate_scratch_root,
    validate_vite_package,
)

FIXTURES_DIR = ROOT / "src/test/fixtures/apg124-toolchain/vite"


def test_constants_and_scenario_registers() -> None:
    """Verify scenario registers and toolchain metadata constants."""
    assert len(ALL_SCENARIOS) == 12
    assert ALL_SCENARIOS == (
        "VITE01", "VITE02", "VITE03", "VITE04", "VITE05", "VITE06",
        "VITE07", "VITE08", "VITE09", "VITE10", "VITE11", "VITE12"
    )
    assert EXPECTED_VITE_VERSION == "8.2.2"
    assert EXPECTED_ROLLDOWN_VERSION == "1.2.7"
    assert EXPECTED_NODE_VERSION == "v22.22.2|darwin/arm64|12.4.254.21-node.39|1.51.0"
    assert EXPECTED_NODE_SHA256 == "b7fff29202c2d59eeff28c53588d2832323b45cb2e854ba29bea47ade37d8359"
    assert "Vite 8.2.2 toolchain scenarios" in VITE_TOOLCHAIN_DISCLAIMER


def test_load_scenarios_register_fixture() -> None:
    """Verify scenarios.json register fixture structure, clauses, and assertions."""
    reg = load_scenarios_register(FIXTURES_DIR)
    assert reg.get("schema_version") == "1.0.0"
    assert "disclaimer" in reg
    toolchain = reg.get("toolchain", {})
    assert toolchain.get("vite_version") == EXPECTED_VITE_VERSION
    assert toolchain.get("rolldown_version") == EXPECTED_ROLLDOWN_VERSION
    assert toolchain.get("node_version") == EXPECTED_NODE_VERSION

    scenarios = reg.get("scenarios", [])
    assert len(scenarios) == 12
    seen_ids = set()
    for sc in scenarios:
        sc_id = sc.get("id")
        assert sc_id in ALL_SCENARIOS
        assert sc_id not in seen_ids
        seen_ids.add(sc_id)
        assert len(sc.get("name", "")) > 0
        assert sc.get("clause_ref", "").startswith("VITE-")
        assert len(sc.get("description", "")) > 0
        assert len(sc.get("assertions", [])) > 0
        assert len(sc.get("adverse_control", "")) > 0
    assert seen_ids == set(ALL_SCENARIOS)


def test_validate_scratch_root_contracts(tmp_path: Path) -> None:
    """Verify strict fail-closed scratch root contracts."""
    # Relative path
    with pytest.raises(ViteHarnessPrerequisiteError, match="must be absolute"):
        validate_scratch_root(Path("relative/scratch"), ROOT)

    # Symlink
    symlink_path = tmp_path / "symlink_scratch"
    real_target = tmp_path / "real_scratch"
    real_target.mkdir(mode=0o700)
    symlink_path.symlink_to(real_target)
    with pytest.raises(ViteHarnessPrerequisiteError, match="must not be a symlink"):
        validate_scratch_root(symlink_path, ROOT)

    # Missing directory
    with pytest.raises(ViteHarnessPrerequisiteError, match="could not be resolved"):
        validate_scratch_root(tmp_path / "nonexistent_dir", ROOT)

    # Inside repository
    repo_sub = ROOT / "tmp_inside_repo"
    repo_sub.mkdir(exist_ok=True, mode=0o700)
    try:
        with pytest.raises(ViteHarnessPrerequisiteError, match="strictly outside the repository checkout"):
            validate_scratch_root(repo_sub, ROOT)
    finally:
        if repo_sub.exists():
            repo_sub.rmdir()

    # Valid external directory with 0700 permissions
    valid_scratch = tmp_path / "valid_scratch"
    valid_scratch.mkdir(mode=0o700)
    resolved = validate_scratch_root(valid_scratch, ROOT, private=True)
    assert resolved == valid_scratch.resolve()

    # Non-0700 permissions when private=True
    insecure_scratch = tmp_path / "insecure_scratch"
    insecure_scratch.mkdir(mode=0o777)
    with pytest.raises(ViteHarnessPrerequisiteError, match="mode 0700"):
        validate_scratch_root(insecure_scratch, ROOT, private=True)


def test_validate_node_executable_contracts(tmp_path: Path) -> None:
    """Verify strict Node binary identity and validation contracts."""
    # Relative path
    with pytest.raises(ViteHarnessPrerequisiteError, match="must be absolute"):
        validate_node_executable(Path("node"), ROOT)

    # Non-existent file
    with pytest.raises(ViteHarnessPrerequisiteError, match="must be an executable file"):
        validate_node_executable(tmp_path / "nonexistent_node", ROOT)

    # Symlink node
    fake_node = tmp_path / "fake_node"
    fake_node.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    fake_node.chmod(0o755)
    sym_node = tmp_path / "sym_node"
    sym_node.symlink_to(fake_node)
    with pytest.raises(ViteHarnessPrerequisiteError, match="must not be a symlink"):
        validate_node_executable(sym_node, ROOT)

    # Inside repo
    repo_node = ROOT / "fake_repo_node"
    repo_node.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    repo_node.chmod(0o755)
    try:
        with pytest.raises(ViteHarnessPrerequisiteError, match="outside repository checkout"):
            validate_node_executable(repo_node, ROOT)
    finally:
        if repo_node.exists():
            repo_node.unlink()

    # Digest mismatch
    with pytest.raises(ViteHarnessPrerequisiteError, match="SHA-256 mismatch"):
        validate_node_executable(fake_node, ROOT)

    # Node executable via explicit environment variable if set (no local default)
    env_node = os.environ.get("APG_JAVASCRIPT_NODE")
    if env_node and Path(env_node).is_file():
        identity = validate_node_executable(Path(env_node), ROOT)
        assert identity == EXPECTED_NODE_VERSION


def test_validate_vite_package_contracts(tmp_path: Path) -> None:
    """Verify strict Vite package validation contracts."""
    scratch = tmp_path / "scratch"
    scratch.mkdir(mode=0o700)

    # Not absolute
    with pytest.raises(ViteHarnessPrerequisiteError, match="must be absolute"):
        validate_vite_package(Path("vite_pkg"), scratch, ROOT)

    # Outside scratch
    outside = tmp_path / "outside"
    outside.mkdir(mode=0o700)
    with pytest.raises(ViteHarnessPrerequisiteError, match="inside owned scratch"):
        validate_vite_package(outside, scratch, ROOT)

    # Missing manifests
    pkg_dir = scratch / "vite"
    pkg_dir.mkdir(mode=0o700)
    with pytest.raises(ViteHarnessPrerequisiteError, match="Vite or Rolldown packages not found"):
        validate_vite_package(pkg_dir, scratch, ROOT)

    # Wrong Vite version
    vite_dir = pkg_dir / "node_modules" / "vite"
    vite_dir.mkdir(parents=True, mode=0o755)
    (vite_dir / "package.json").write_text(json.dumps({"name": "vite", "version": "7.0.0"}))

    rolldown_dir = pkg_dir / "node_modules" / "rolldown"
    rolldown_dir.mkdir(parents=True, mode=0o755)
    (rolldown_dir / "package.json").write_text(json.dumps({"name": "rolldown", "version": EXPECTED_ROLLDOWN_VERSION}))

    with pytest.raises(ViteHarnessPrerequisiteError, match="Vite version mismatch"):
        validate_vite_package(pkg_dir, scratch, ROOT)

    # Wrong Rolldown version
    (vite_dir / "package.json").write_text(json.dumps({"name": "vite", "version": EXPECTED_VITE_VERSION}))
    (rolldown_dir / "package.json").write_text(json.dumps({"name": "rolldown", "version": "0.9.0"}))
    with pytest.raises(ViteHarnessPrerequisiteError, match="Rolldown version mismatch"):
        validate_vite_package(pkg_dir, scratch, ROOT)

    # Valid package
    (rolldown_dir / "package.json").write_text(json.dumps({"name": "rolldown", "version": EXPECTED_ROLLDOWN_VERSION}))
    native_dir = pkg_dir / "node_modules" / "@rolldown" / "binding-darwin-arm64"
    native_dir.mkdir(parents=True, mode=0o755)
    (native_dir / "package.json").write_text(json.dumps({"version": EXPECTED_ROLLDOWN_VERSION}))

    info = validate_vite_package(pkg_dir, scratch, ROOT)
    assert info["vite_version"] == EXPECTED_VITE_VERSION
    assert info["rolldown_version"] == EXPECTED_ROLLDOWN_VERSION
    assert info["native_binding_present"] == "true"


def test_validate_prerequisites_fail_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Verify fail-closed prerequisites check mirroring apg_playwright_runtime.py."""
    # When APG_VITE_OWNED_SCRATCH_ROOT is unset
    monkeypatch.delenv("APG_VITE_OWNED_SCRATCH_ROOT", raising=False)
    with pytest.raises(ViteHarnessPrerequisiteError, match="set APG_VITE_OWNED_SCRATCH_ROOT"):
        validate_prerequisites(ROOT)

    scratch = tmp_path / "prereq_scratch"
    scratch.mkdir(mode=0o700)
    monkeypatch.setenv("APG_VITE_OWNED_SCRATCH_ROOT", str(scratch))

    # When APG_VITE_PACKAGE_ROOT is unset
    monkeypatch.delenv("APG_VITE_PACKAGE_ROOT", raising=False)
    with pytest.raises(ViteHarnessPrerequisiteError, match="set APG_VITE_PACKAGE_ROOT"):
        validate_prerequisites(ROOT)

    pkg_dir = scratch / "vite"
    pkg_dir.mkdir(mode=0o700)
    vite_dir = pkg_dir / "node_modules" / "vite"
    vite_dir.mkdir(parents=True, mode=0o755)
    (vite_dir / "package.json").write_text(json.dumps({"name": "vite", "version": EXPECTED_VITE_VERSION}))
    rolldown_dir = pkg_dir / "node_modules" / "rolldown"
    rolldown_dir.mkdir(parents=True, mode=0o755)
    (rolldown_dir / "package.json").write_text(json.dumps({"name": "rolldown", "version": EXPECTED_ROLLDOWN_VERSION}))
    monkeypatch.setenv("APG_VITE_PACKAGE_ROOT", str(pkg_dir))

    # When APG_JAVASCRIPT_NODE is unset
    monkeypatch.delenv("APG_JAVASCRIPT_NODE", raising=False)
    with pytest.raises(ViteHarnessPrerequisiteError, match="set APG_JAVASCRIPT_NODE"):
        validate_prerequisites(ROOT)


def test_observe_vite_harness_config_fail_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Verify independent fail-closed observe config checks for each required variable."""
    # When APG_VITE_OWNED_SCRATCH_ROOT is unset
    monkeypatch.delenv("APG_VITE_OWNED_SCRATCH_ROOT", raising=False)
    monkeypatch.delenv("APG_VITE_PACKAGE_ROOT", raising=False)
    monkeypatch.delenv("APG_JAVASCRIPT_NODE", raising=False)
    with pytest.raises(ViteHarnessPrerequisiteError, match="set APG_VITE_OWNED_SCRATCH_ROOT"):
        observe_vite_harness_config(ROOT)

    scratch = tmp_path / "obs_scratch"
    scratch.mkdir(mode=0o700)
    monkeypatch.setenv("APG_VITE_OWNED_SCRATCH_ROOT", str(scratch))

    # When APG_VITE_PACKAGE_ROOT is unset
    with pytest.raises(ViteHarnessPrerequisiteError, match="set APG_VITE_PACKAGE_ROOT"):
        observe_vite_harness_config(ROOT)

    pkg_dir = scratch / "vite"
    pkg_dir.mkdir(mode=0o700)
    vite_dir = pkg_dir / "node_modules" / "vite"
    vite_dir.mkdir(parents=True, mode=0o755)
    (vite_dir / "package.json").write_text(json.dumps({"name": "vite", "version": EXPECTED_VITE_VERSION}))
    rolldown_dir = pkg_dir / "node_modules" / "rolldown"
    rolldown_dir.mkdir(parents=True, mode=0o755)
    (rolldown_dir / "package.json").write_text(json.dumps({"name": "rolldown", "version": EXPECTED_ROLLDOWN_VERSION}))
    monkeypatch.setenv("APG_VITE_PACKAGE_ROOT", str(pkg_dir))

    # When APG_JAVASCRIPT_NODE is unset
    with pytest.raises(ViteHarnessPrerequisiteError, match="set APG_JAVASCRIPT_NODE"):
        observe_vite_harness_config(ROOT)


def test_validate_receipt_contracts() -> None:
    """Verify receipt validation logic and clean pass invariants."""
    # Schema mismatch
    with pytest.raises(ViteHarnessValidationError, match="Invalid receipt schema version"):
        validate_receipt({"schema_version": "2.0.0"})

    # Non-clean pass: failed > 0
    bad_summary = {
        "schema_version": "1.0.0",
        "summary": {"total": 1, "passed": 0, "failed": 1, "skipped": 0},
        "scenarios": [{"scenario_id": "VITE01", "status": "failed", "assertions": []}]
    }
    with pytest.raises(ViteHarnessValidationError, match="Receipt indicates non-clean pass"):
        validate_receipt(bad_summary)

    # Malformed integer in summary
    with pytest.raises(ViteHarnessValidationError, match="Invalid integer counter"):
        validate_receipt({
            "schema_version": "1.0.0",
            "summary": {"total": "1", "passed": 1, "failed": 0, "skipped": 0},
            "scenarios": []
        })

    # Malformed bool in assertion passed
    with pytest.raises(ViteHarnessValidationError, match="assertion failed or malformed bool"):
        validate_receipt({
            "schema_version": "1.0.0",
            "summary": {"total": 1, "passed": 1, "failed": 0, "skipped": 0},
            "scenarios": [
                {
                    "scenario_id": "VITE01",
                    "status": "passed",
                    "assertions": [{"name": "resolved_root_exact", "passed": "true"}]
                }
            ]
        })

    # Unknown scenario ID in receipt
    with pytest.raises(ViteHarnessValidationError, match="Unknown scenario ID"):
        validate_receipt({
            "schema_version": "1.0.0",
            "summary": {"total": 1, "passed": 1, "failed": 0, "skipped": 0},
            "scenarios": [
                {
                    "scenario_id": "VITE99",
                    "status": "passed",
                    "assertions": [{"name": "foo", "passed": True}]
                }
            ]
        })

    reg = load_scenarios_register(FIXTURES_DIR)
    v1_assertions = [{"name": a, "passed": True} for a in reg["scenarios"][0]["assertions"]]

    # Duplicate scenario in receipt
    with pytest.raises(ViteHarnessValidationError, match="Duplicate scenario ID"):
        validate_receipt({
            "schema_version": "1.0.0",
            "summary": {"total": 2, "passed": 2, "failed": 0, "skipped": 0},
            "scenarios": [
                {
                    "scenario_id": "VITE01",
                    "status": "passed",
                    "assertions": v1_assertions
                },
                {
                    "scenario_id": "VITE01",
                    "status": "passed",
                    "assertions": v1_assertions
                }
            ]
        }, fixtures_dir=FIXTURES_DIR)

    # Duplicate assertion name in scenario
    with pytest.raises(ViteHarnessValidationError, match="contains duplicate assertions"):
        validate_receipt({
            "schema_version": "1.0.0",
            "summary": {"total": 1, "passed": 1, "failed": 0, "skipped": 0},
            "scenarios": [
                {
                    "scenario_id": "VITE01",
                    "status": "passed",
                    "assertions": [
                        {"name": "resolved_root_exact", "passed": True},
                        {"name": "resolved_root_exact", "passed": True}
                    ]
                }
            ]
        }, fixtures_dir=FIXTURES_DIR)

    # Register assertion set mismatch (missing assertions from register)
    with pytest.raises(ViteHarnessValidationError, match="assertion set differs"):
        validate_receipt({
            "schema_version": "1.0.0",
            "summary": {"total": 1, "passed": 1, "failed": 0, "skipped": 0},
            "scenarios": [
                {
                    "scenario_id": "VITE01",
                    "status": "passed",
                    "assertions": [{"name": "resolved_root_exact", "passed": True}]
                }
            ]
        }, expected_scenarios=["VITE01"], fixtures_dir=FIXTURES_DIR)
    clean_raw = {
        "schema_version": "1.0.0",
        "toolchain": {"vite_version": "8.2.2", "node_version": "v22.22.2", "node_identity": EXPECTED_NODE_VERSION},
        "summary": {"total": 1, "passed": 1, "failed": 0, "skipped": 0},
        "scenarios": [
            {
                "scenario_id": "VITE01",
                "name": "resolved_config",
                "status": "passed",
                "assertions": v1_assertions
            }
        ],
        "retained_on_disk": False
    }

    # Scenario count mismatch
    with pytest.raises(ViteHarnessValidationError, match="Receipt scenario count mismatch"):
        validate_receipt(clean_raw, expected_scenarios=["VITE01", "VITE02"], fixtures_dir=FIXTURES_DIR)

    # Missing expected scenario
    with pytest.raises(ViteHarnessValidationError, match="Missing required scenarios"):
        validate_receipt(clean_raw, expected_scenarios=["VITE02"], fixtures_dir=FIXTURES_DIR)

    # Valid receipt pass
    receipt = validate_receipt(clean_raw, expected_scenarios=["VITE01"], fixtures_dir=FIXTURES_DIR)
    with pytest.raises(ViteHarnessValidationError, match="toolchain identity"):
        validate_receipt(dict(clean_raw, toolchain={"vite_version": "8.2.3"}), expected_scenarios=["VITE01"], fixtures_dir=FIXTURES_DIR)
    with pytest.raises(ViteHarnessValidationError, match="private paths"):
        validate_receipt(dict(clean_raw, unexpected_path="/" + "Users/synthetic/fixture"), expected_scenarios=["VITE01"], fixtures_dir=FIXTURES_DIR)
    assert receipt.is_clean_pass
    assert receipt.total_count == 1
    assert receipt.passed_count == 1
    assert receipt.failed_count == 0
    assert receipt.skipped_count == 0
    sc = receipt.get_scenario("VITE01")
    assert sc is not None
    assert sc["name"] == "resolved_config"
    assert receipt.get_scenario("VITE99") is None


@pytest.mark.parametrize("selected", [(), ("VITE01", "VITE01"), ("UNKNOWN",)])
def test_execution_filter_refuses_before_process_creation(selected):
    from apg124_vite import execute_vite_harness, ViteHarnessExecutionError
    with pytest.raises(ViteHarnessExecutionError, match="Scenario filter"):
        execute_vite_harness(None, FIXTURES_DIR, selected)


def test_child_environment_does_not_inherit_caller_secrets(monkeypatch, tmp_path):
    from types import SimpleNamespace
    import apg124_vite as harness
    captured = {}
    def refuse_spawn(*args, **kwargs):
        captured.update(kwargs["env"])
        raise RuntimeError("test stopped before spawn")
    monkeypatch.setenv("VITE_PRIVATE_TEST_SECRET", "must-not-inherit")
    monkeypatch.setenv("NODE_OPTIONS", "--require=unowned-hook")
    monkeypatch.setattr(harness.subprocess, "Popen", refuse_spawn)
    config = SimpleNamespace(node_executable=tmp_path / "node", scratch_root=tmp_path, package_root=tmp_path)
    with pytest.raises(RuntimeError, match="before spawn"):
        harness.execute_vite_harness(config, FIXTURES_DIR)
    assert "VITE_PRIVATE_TEST_SECRET" not in captured
    assert "NODE_OPTIONS" not in captured
    assert set(captured) == {"HOME", "TMPDIR", "PATH", "NO_COLOR", "APG_VITE_OWNED_SCRATCH_ROOT", "APG_VITE_PACKAGE_ROOT"}
