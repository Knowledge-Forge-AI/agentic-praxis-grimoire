#!/usr/bin/env python3
"""Unit tests for APG124 npm package manager support module (apg124_npm.py).

Validates fail-closed refusal contracts for Node identity, npm package root,
scratch ownership boundaries, scenario register schema, and evaluation receipt completeness.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import pytest

from src.test.apg_test_support import repository_root

ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src/test/support"))

from apg124_npm import (  # noqa: E402
    ALL_SCENARIOS,
    DEPENDENCY_TOPOLOGY_SCENARIOS,
    EXPECTED_NODE_ENGINES,
    EXPECTED_NODE_VERSION,
    EXPECTED_NPM_LICENSE,
    EXPECTED_NPM_VERSION,
    LIFECYCLE_EXECUTION_SCENARIOS,
    MANIFEST_LOCK_SCENARIOS,
    NPM_CORROBORATION_DISCLAIMER,
    REGISTERED_SCENARIO_ASSERTIONS,
    SCENARIO_GROUPS,
    NpmHarnessConfig,
    NpmHarnessExecutionError,
    NpmHarnessPrerequisiteError,
    NpmHarnessValidationError,
    load_scenarios_register,
    observe_npm_harness_config,
    run_npm_subprocess,
    validate_node_executable,
    validate_npm_package,
    validate_receipt,
    validate_scratch_root,
)

FIXTURES_DIR = ROOT / "src/test/fixtures/apg124-toolchain/npm"


def test_constants_and_partitions() -> None:
    """Verify package manager constants, engine specifications, and scenario partitions."""
    assert EXPECTED_NPM_VERSION == "12.0.2"
    assert EXPECTED_NPM_LICENSE == "Artistic-2.0"
    assert EXPECTED_NODE_ENGINES == "^22.22.2 || ^24.15.0 || >=26.0.0"
    assert len(MANIFEST_LOCK_SCENARIOS) == 3
    assert len(DEPENDENCY_TOPOLOGY_SCENARIOS) == 5
    assert len(LIFECYCLE_EXECUTION_SCENARIOS) == 4
    assert len(ALL_SCENARIOS) == 12
    assert set(MANIFEST_LOCK_SCENARIOS) & set(DEPENDENCY_TOPOLOGY_SCENARIOS) == set()
    assert set(MANIFEST_LOCK_SCENARIOS) & set(LIFECYCLE_EXECUTION_SCENARIOS) == set()
    assert set(DEPENDENCY_TOPOLOGY_SCENARIOS) & set(LIFECYCLE_EXECUTION_SCENARIOS) == set()
    assert set(SCENARIO_GROUPS) == {"all", "manifest_lock", "dependency_topology", "lifecycle_execution"}
    assert "CLI and dependency solver" in NPM_CORROBORATION_DISCLAIMER
    assert len(REGISTERED_SCENARIO_ASSERTIONS) == 12


def test_load_scenarios_register() -> None:
    """Verify scenarios.json fixture loading, schema version, and scenario presence."""
    reg = load_scenarios_register(FIXTURES_DIR)
    assert reg.get("schema_version") == "1.0.0"
    assert reg.get("authority") == "APG124-NPM-TOOLCHAIN-SCENARIO-REGISTER"
    scenarios = reg.get("scenarios", [])
    assert len(scenarios) == 12
    seen_ids = [s.get("id") for s in scenarios]
    assert sorted(seen_ids) == sorted(ALL_SCENARIOS)

    for sc in scenarios:
        assert sc.get("clause", "").startswith("NPM-")
        assert sc.get("expected_outcome") == "passed"
        assert len(sc.get("assertions", [])) > 0
        assert tuple(sc.get("assertions", [])) == REGISTERED_SCENARIO_ASSERTIONS[sc["id"]]


def test_load_scenarios_register_refusals(tmp_path: Path) -> None:
    """Verify scenarios register loader rejects missing or corrupt files."""
    with pytest.raises(NpmHarnessValidationError, match="not found"):
        load_scenarios_register(tmp_path / "missing")

    bad_json = tmp_path / "bad"
    bad_json.mkdir()
    (bad_json / "scenarios.json").write_text("invalid json", encoding="utf-8")
    with pytest.raises(NpmHarnessValidationError, match="Invalid scenarios.json"):
        load_scenarios_register(bad_json)

    wrong_count = tmp_path / "wrong_count"
    wrong_count.mkdir()
    (wrong_count / "scenarios.json").write_text(
        json.dumps({"schema_version": "1.0.0", "scenarios": [{"id": "NPM01"}]}),
        encoding="utf-8"
    )
    with pytest.raises(NpmHarnessValidationError, match="Scenario register mismatch"):
        load_scenarios_register(wrong_count)


def test_validate_scratch_root_success_and_refusals(tmp_path: Path) -> None:
    """Verify scratch root validation, ownership, permissions, and containment checks."""
    valid_scratch = tmp_path / "scratch"
    valid_scratch.mkdir(mode=0o700)
    # Ensure mode 0700 explicitly in case umask altered it
    os.chmod(valid_scratch, 0o700)
    res = validate_scratch_root(valid_scratch, ROOT)
    assert res == valid_scratch.resolve()

    with pytest.raises(NpmHarnessPrerequisiteError, match="must be absolute"):
        validate_scratch_root(Path("relative/scratch"), ROOT)

    with pytest.raises(NpmHarnessPrerequisiteError, match="must be an existing directory"):
        validate_scratch_root(tmp_path / "nonexistent", ROOT)

    symlink_scratch = tmp_path / "symlink_scratch"
    symlink_scratch.symlink_to(valid_scratch)
    with pytest.raises(NpmHarnessPrerequisiteError, match="must not be a symlink"):
        validate_scratch_root(symlink_scratch, ROOT)

    # Ancestor symlink refusal
    parent_dir = tmp_path / "parent_real"
    parent_dir.mkdir(mode=0o700)
    sym_parent = tmp_path / "parent_sym"
    sym_parent.symlink_to(parent_dir)
    child_in_sym = sym_parent / "child"
    child_in_sym.mkdir(mode=0o700)
    with pytest.raises(NpmHarnessPrerequisiteError, match="ancestor must not be a symlink"):
        validate_scratch_root(child_in_sym, ROOT)

    # Wrong mode refusal (e.g. 0500: owner-only read/execute, not 0700)
    bad_mode_scratch = tmp_path / "scratch_bad_mode"
    bad_mode_scratch.mkdir(mode=0o700)
    try:
        os.chmod(bad_mode_scratch, 0o500)
        with pytest.raises(NpmHarnessPrerequisiteError, match="must be mode 0700"):
            validate_scratch_root(bad_mode_scratch, ROOT)
    finally:
        os.chmod(bad_mode_scratch, 0o700)

    repo_internal = ROOT / "src/test/fixtures"
    with pytest.raises(NpmHarnessPrerequisiteError, match="strictly outside the repository checkout"):
        validate_scratch_root(repo_internal, ROOT)


def test_validate_node_executable_success_and_refusals(tmp_path: Path) -> None:
    """Verify Node binary identity checks, sha256 digest, and refusal rules."""
    raw_node = os.environ.get("APG_JAVASCRIPT_NODE")
    if not raw_node:
        pytest.fail("APG_JAVASCRIPT_NODE environment variable not set")
    node_path = Path(raw_node)
    assert node_path.is_file(), f"Qualified node path {node_path} must exist"

    identity = validate_node_executable(node_path, ROOT)
    assert identity == EXPECTED_NODE_VERSION

    with pytest.raises(NpmHarnessPrerequisiteError, match="must be absolute"):
        validate_node_executable(Path("node"), ROOT)

    with pytest.raises(NpmHarnessPrerequisiteError, match="must be an executable file"):
        validate_node_executable(tmp_path / "missing-node", ROOT)

    not_exec = tmp_path / "not_exec.sh"
    not_exec.write_text("#!/bin/sh\n", encoding="utf-8")
    not_exec.chmod(0o644)
    with pytest.raises(NpmHarnessPrerequisiteError, match="must be an executable file"):
        validate_node_executable(not_exec, ROOT)

    symlink_node = tmp_path / "symlink_node"
    symlink_node.symlink_to(node_path)
    with pytest.raises(NpmHarnessPrerequisiteError, match="must not be a symlink"):
        validate_node_executable(symlink_node, ROOT)

    fake_repo = tmp_path / "repo"
    fake_repo.mkdir()
    internal_node = fake_repo / "node"
    internal_node.write_text("#!/bin/sh\n", encoding="utf-8")
    internal_node.chmod(0o755)
    with pytest.raises(NpmHarnessPrerequisiteError, match="outside repository checkout"):
        validate_node_executable(internal_node, fake_repo)

    fake_exec = tmp_path / "fake_node"
    fake_exec.write_text("#!/bin/sh\necho test\n", encoding="utf-8")
    fake_exec.chmod(0o755)
    with pytest.raises(NpmHarnessPrerequisiteError, match="SHA-256 mismatch"):
        validate_node_executable(fake_exec, ROOT)


def test_validate_npm_package_success_and_refusals(tmp_path: Path) -> None:
    """Verify npm package validation inside scratch root and version parity."""
    scratch = tmp_path / "scratch"
    scratch.mkdir(mode=0o700)
    os.chmod(scratch, 0o700)

    # Valid npm package fixture inside scratch
    pkg_dir = scratch / "npm"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "bin").mkdir()
    (pkg_dir / "bin" / "npm-cli.js").write_text("#!/usr/bin/env node\n", encoding="utf-8")
    (pkg_dir / "bin" / "npm-cli.js").chmod(0o755)
    (pkg_dir / "package.json").write_text(
        json.dumps({"name": "npm", "version": "12.0.2", "license": "Artistic-2.0"}),
        encoding="utf-8"
    )

    ver = validate_npm_package(pkg_dir, scratch)
    assert ver == "12.0.2"

    with pytest.raises(NpmHarnessPrerequisiteError, match="must be absolute"):
        validate_npm_package(Path("npm"), scratch)

    with pytest.raises(NpmHarnessPrerequisiteError, match="must be an existing directory"):
        validate_npm_package(scratch / "missing_npm", scratch)

    # Outside scratch
    outside = tmp_path / "outside_npm"
    outside.mkdir()
    with pytest.raises(NpmHarnessPrerequisiteError, match="inside owned scratch root"):
        validate_npm_package(outside, scratch)

    # Missing bin/npm-cli.js
    bad_bin = scratch / "bad_bin"
    bad_bin.mkdir()
    (bad_bin / "package.json").write_text(
        json.dumps({"name": "npm", "version": "12.0.2", "license": "Artistic-2.0"}),
        encoding="utf-8"
    )
    with pytest.raises(NpmHarnessPrerequisiteError, match="npm CLI entrypoint missing"):
        validate_npm_package(bad_bin, scratch)

    # Missing package.json
    bad_pkg = scratch / "bad_pkg"
    bad_pkg.mkdir()
    (bad_pkg / "bin").mkdir()
    (bad_pkg / "bin" / "npm-cli.js").write_text("#!/usr/bin/env node\n", encoding="utf-8")
    with pytest.raises(NpmHarnessPrerequisiteError, match="npm package.json missing"):
        validate_npm_package(bad_pkg, scratch)

    # Version mismatch
    mismatch_pkg = scratch / "mismatch_pkg"
    mismatch_pkg.mkdir()
    (mismatch_pkg / "bin").mkdir()
    (mismatch_pkg / "bin" / "npm-cli.js").write_text("#!/usr/bin/env node\n", encoding="utf-8")
    (mismatch_pkg / "package.json").write_text(
        json.dumps({"name": "npm", "version": "11.0.0", "license": "Artistic-2.0"}),
        encoding="utf-8"
    )
    with pytest.raises(NpmHarnessPrerequisiteError, match="npm manifest mismatch"):
        validate_npm_package(mismatch_pkg, scratch)

    # License mismatch
    license_mismatch = scratch / "license_mismatch"
    license_mismatch.mkdir()
    (license_mismatch / "bin").mkdir()
    (license_mismatch / "bin" / "npm-cli.js").write_text("#!/usr/bin/env node\n", encoding="utf-8")
    (license_mismatch / "package.json").write_text(
        json.dumps({"name": "npm", "version": "12.0.2", "license": "GPL-3.0"}),
        encoding="utf-8"
    )
    with pytest.raises(NpmHarnessPrerequisiteError, match="npm license mismatch"):
        validate_npm_package(license_mismatch, scratch)


def test_observe_npm_harness_config_missing_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Verify observe_npm_harness_config fails closed when required environment variables are absent."""
    valid_scratch = tmp_path / "valid_scratch"
    valid_scratch.mkdir(mode=0o700)
    os.chmod(valid_scratch, 0o700)

    monkeypatch.delenv("APG_NPM_OWNED_SCRATCH_ROOT", raising=False)
    monkeypatch.delenv("APG_JAVASCRIPT_NODE", raising=False)
    monkeypatch.delenv("APG_NPM_PACKAGE_ROOT", raising=False)

    with pytest.raises(NpmHarnessPrerequisiteError, match="APG_NPM_OWNED_SCRATCH_ROOT"):
        observe_npm_harness_config(ROOT)

    monkeypatch.setenv("APG_NPM_OWNED_SCRATCH_ROOT", os.fspath(valid_scratch))
    with pytest.raises(NpmHarnessPrerequisiteError, match="APG_JAVASCRIPT_NODE"):
        observe_npm_harness_config(ROOT)

    real_node = os.environ.get("APG_JAVASCRIPT_NODE")
    if real_node:
        monkeypatch.setenv("APG_JAVASCRIPT_NODE", real_node)
        with pytest.raises(NpmHarnessPrerequisiteError, match="APG_NPM_PACKAGE_ROOT"):
            observe_npm_harness_config(ROOT)


def test_observe_npm_harness_config_with_explicit_env() -> None:
    """Verify observe_npm_harness_config resolves successfully with valid explicit environment."""
    if not os.environ.get("APG_NPM_OWNED_SCRATCH_ROOT") or not os.environ.get("APG_JAVASCRIPT_NODE") or not os.environ.get("APG_NPM_PACKAGE_ROOT"):
        pytest.fail("Prerequisite environment variables not fully configured")

    cfg = observe_npm_harness_config(ROOT)
    assert isinstance(cfg, NpmHarnessConfig)
    assert cfg.npm_version == "12.0.2"
    assert cfg.node_identity == EXPECTED_NODE_VERSION
    assert cfg.npm_cli_path.is_file()


def test_validate_receipt_rules() -> None:
    """Verify evaluation receipt schema, zero-skip, zero-failure, and scenario checks."""
    valid_receipt_data = {
        "schema_version": "1.0.0",
        "authority": "APG124-NPM-QUALIFIED-RECEIPT",
        "disclaimer": NPM_CORROBORATION_DISCLAIMER,
        "package": {
            "name": "npm",
            "version": "12.0.2",
            "license": "Artistic-2.0",
        },
        "node": {
            "identity": EXPECTED_NODE_VERSION,
        },
        "executing_version": "12.0.2",
        "summary": {
            "total": 2,
            "passed": 2,
            "failed": 0,
            "skipped": 0,
        },
        "scenarios": [
            {
                "scenario_id": "NPM01",
                "status": "passed",
                "executing_version": "12.0.2",
                "duration_ms": 100,
                "assertions": [{"name": a, "passed": True} for a in REGISTERED_SCENARIO_ASSERTIONS["NPM01"]],
            },
            {
                "scenario_id": "NPM02",
                "status": "passed",
                "executing_version": "12.0.2",
                "duration_ms": 110,
                "assertions": [{"name": a, "passed": True} for a in REGISTERED_SCENARIO_ASSERTIONS["NPM02"]],
            },
        ],
        "artifacts": ["NPM01_output", "NPM02_output"],
    }

    receipt = validate_receipt(valid_receipt_data, expected_scenarios=("NPM01", "NPM02"))
    assert receipt.is_clean_pass
    assert receipt.total_count == 2
    assert receipt.passed_count == 2
    assert receipt.failed_count == 0
    assert receipt.skipped_count == 0
    assert receipt.get_scenario("NPM01") is not None
    assert receipt.get_scenario("NPM99") is None

    # Refusal: schema version mismatch
    bad_schema = dict(valid_receipt_data, schema_version="2.0.0")
    with pytest.raises(NpmHarnessValidationError, match="Unsupported receipt schema_version"):
        validate_receipt(bad_schema, expected_scenarios=("NPM01", "NPM02"))

    # Refusal: package identity mismatch
    bad_pkg = dict(valid_receipt_data, package={"name": "yarn", "version": "1.22.0"})
    with pytest.raises(NpmHarnessValidationError, match="Receipt package identity mismatch"):
        validate_receipt(bad_pkg, expected_scenarios=("NPM01", "NPM02"))

    # Refusal: executing version mismatch
    bad_ver = dict(valid_receipt_data, executing_version="11.0.0")
    with pytest.raises(NpmHarnessValidationError, match="Receipt executing version mismatch"):
        validate_receipt(bad_ver, expected_scenarios=("NPM01", "NPM02"))

    # Refusal: non-zero failed count
    failed_summary = dict(valid_receipt_data, summary={"total": 2, "passed": 1, "failed": 1, "skipped": 0})
    with pytest.raises(NpmHarnessValidationError, match="Incomplete or failed scenario run"):
        validate_receipt(failed_summary, expected_scenarios=("NPM01", "NPM02"))

    # Refusal: non-zero skipped count
    skipped_summary = dict(valid_receipt_data, summary={"total": 2, "passed": 2, "failed": 0, "skipped": 1})
    with pytest.raises(NpmHarnessValidationError, match="Incomplete or failed scenario run"):
        validate_receipt(skipped_summary, expected_scenarios=("NPM01", "NPM02"))

    # Refusal: scenario status failed
    failed_sc = json.loads(json.dumps(valid_receipt_data))
    failed_sc["scenarios"][0]["status"] = "failed"
    with pytest.raises(NpmHarnessValidationError, match="did not pass"):
        validate_receipt(failed_sc, expected_scenarios=("NPM01", "NPM02"))

    # Refusal: scenario assertion failed
    failed_assert = json.loads(json.dumps(valid_receipt_data))
    failed_assert["scenarios"][0]["assertions"][0]["passed"] = False
    with pytest.raises(NpmHarnessValidationError, match="invalid assertion record"):
        validate_receipt(failed_assert, expected_scenarios=("NPM01", "NPM02"))

    # Refusal: unknown scenario ID
    unknown_sc = json.loads(json.dumps(valid_receipt_data))
    unknown_sc["scenarios"][0]["scenario_id"] = "NPM99"
    with pytest.raises(NpmHarnessValidationError, match="Unknown scenario ID"):
        validate_receipt(unknown_sc, expected_scenarios=("NPM01", "NPM02"))

    # Refusal: duplicate scenario entry
    dup_sc = json.loads(json.dumps(valid_receipt_data))
    dup_sc["scenarios"][1]["scenario_id"] = "NPM01"
    with pytest.raises(NpmHarnessValidationError, match="Duplicate scenario entry"):
        validate_receipt(dup_sc, expected_scenarios=("NPM01", "NPM02"))

    # Refusal: empty filter
    with pytest.raises(NpmHarnessValidationError, match="must not be empty"):
        validate_receipt(valid_receipt_data, expected_scenarios=())

    # Refusal: duplicate filter
    with pytest.raises(NpmHarnessValidationError, match="duplicate scenario IDs"):
        validate_receipt(valid_receipt_data, expected_scenarios=("NPM01", "NPM01"))

    # Refusal: unknown filter
    with pytest.raises(NpmHarnessValidationError, match="unknown scenario ID"):
        validate_receipt(valid_receipt_data, expected_scenarios=("NPM99",))

    # Refusal: unknown assertion name in scenario
    unknown_assert_sc = json.loads(json.dumps(valid_receipt_data))
    unknown_assert_sc["scenarios"][0]["assertions"].append({"name": "nonexistent_assertion", "passed": True})
    with pytest.raises(NpmHarnessValidationError, match="unknown assertion name"):
        validate_receipt(unknown_assert_sc, expected_scenarios=("NPM01", "NPM02"))

    # Refusal: duplicate assertion name in scenario
    dup_assert_sc = json.loads(json.dumps(valid_receipt_data))
    dup_assert_sc["scenarios"][0]["assertions"].append(
        {"name": dup_assert_sc["scenarios"][0]["assertions"][0]["name"], "passed": True}
    )
    with pytest.raises(NpmHarnessValidationError, match="duplicate assertion name"):
        validate_receipt(dup_assert_sc, expected_scenarios=("NPM01", "NPM02"))

    # Refusal: missing registered assertion
    missing_assert_sc = json.loads(json.dumps(valid_receipt_data))
    missing_assert_sc["scenarios"][0]["assertions"].pop()
    with pytest.raises(NpmHarnessValidationError, match="assertion set mismatch"):
        validate_receipt(missing_assert_sc, expected_scenarios=("NPM01", "NPM02"))

    # Refusal: receipt contains node executable path
    exec_path_sc = json.loads(json.dumps(valid_receipt_data))
    exec_path_sc["node"]["executable"] = "/bin/node"
    with pytest.raises(NpmHarnessValidationError, match="must not expose node executable"):
        validate_receipt(exec_path_sc, expected_scenarios=("NPM01", "NPM02"))

    # Refusal: receipt contains prohibited private path
    private_path_sc = json.loads(json.dumps(valid_receipt_data))
    private_path_sc["artifacts"].append("/" + "Users/foo/bar")
    with pytest.raises(NpmHarnessValidationError, match="prohibited path reference"):
        validate_receipt(private_path_sc, expected_scenarios=("NPM01", "NPM02"))


def test_subprocess_credential_rejection(tmp_path: Path) -> None:
    """Verify run_npm_subprocess rejects disallowed credential tokens in environment."""
    cfg = NpmHarnessConfig(
        repo_root=ROOT,
        scratch_root=tmp_path,
        node_executable=Path("/bin/node"),
        node_identity="test",
        npm_package_root=tmp_path / "npm",
        npm_cli_path=tmp_path / "npm" / "bin" / "npm-cli.js",
        npm_version="12.0.2",
    )
    with pytest.raises(NpmHarnessExecutionError, match="Disallowed credential"):
        run_npm_subprocess(cfg, ["--version"], tmp_path, tmp_path / "cache", extra_env={"NPM_TOKEN": "secret123"})

    with pytest.raises(NpmHarnessExecutionError, match="Disallowed credential"):
        run_npm_subprocess(cfg, ["--version"], tmp_path, tmp_path / "cache", extra_env={"NODE_AUTH_TOKEN": "secret123"})


def test_empty_execution_selection_fails_before_scratch_creation():
    from apg124_npm import execute_npm_harness, NpmHarnessExecutionError
    with pytest.raises(NpmHarnessExecutionError, match="must not be empty"):
        execute_npm_harness(None, Path("unused"), scenarios=())


def test_synthetic_fixture_identities_and_dependency_keys() -> None:
    """Verify synthetic package identities and dependency keys/assertions remain consistent."""
    # Verify config package identity
    config_pkg_path = FIXTURES_DIR / "projects" / "config" / "package.json"
    assert config_pkg_path.is_file(), f"Fixture {config_pkg_path} must exist"
    config_pkg = json.loads(config_pkg_path.read_text(encoding="utf-8"))
    assert config_pkg.get("name") == "apgr-apg124-fixture-config"
    assert config_pkg.get("version") == "1.0.0"

    # Verify dep-b package identity and exported module name
    dep_b_pkg_path = FIXTURES_DIR / "packages" / "dep-b" / "package.json"
    assert dep_b_pkg_path.is_file(), f"Fixture {dep_b_pkg_path} must exist"
    dep_b_pkg = json.loads(dep_b_pkg_path.read_text(encoding="utf-8"))
    assert dep_b_pkg.get("name") == "apgr-apg124-fixture-dep-b"
    assert dep_b_pkg.get("version") == "1.0.0"

    dep_b_idx_path = FIXTURES_DIR / "packages" / "dep-b" / "index.js"
    assert dep_b_idx_path.is_file(), f"Fixture {dep_b_idx_path} must exist"
    dep_b_idx = dep_b_idx_path.read_text(encoding="utf-8")
    assert 'name: "apgr-apg124-fixture-dep-b"' in dep_b_idx

    # Verify stale-lock dependencies key and path
    stale_pkg_path = FIXTURES_DIR / "projects" / "stale-lock" / "package.json"
    assert stale_pkg_path.is_file(), f"Fixture {stale_pkg_path} must exist"
    stale_pkg = json.loads(stale_pkg_path.read_text(encoding="utf-8"))
    assert "apgr-apg124-fixture-dep-b" in stale_pkg.get("dependencies", {})
    assert "dep-b" not in stale_pkg.get("dependencies", {})
    assert stale_pkg["dependencies"]["apgr-apg124-fixture-dep-b"] == "file:../dep-b"

    # Verify install-update dependencies key and path
    update_pkg_path = FIXTURES_DIR / "projects" / "install-update" / "package.json"
    assert update_pkg_path.is_file(), f"Fixture {update_pkg_path} must exist"
    update_pkg = json.loads(update_pkg_path.read_text(encoding="utf-8"))
    assert "apgr-apg124-fixture-dep-b" in update_pkg.get("dependencies", {})
    assert "dep-b" not in update_pkg.get("dependencies", {})
    assert update_pkg["dependencies"]["apgr-apg124-fixture-dep-b"] == "file:../dep-b"

    # Verify physical directories remain stable
    assert (FIXTURES_DIR / "packages" / "dep-b").is_dir()
    assert (FIXTURES_DIR / "projects" / "config").is_dir()
