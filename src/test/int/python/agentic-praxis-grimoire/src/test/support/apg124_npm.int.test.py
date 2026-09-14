#!/usr/bin/env python3
"""Integration coverage for APG124 npm package manager profile harness (apg124_npm.py).

Executes the 12 maintained synthetic scenarios against qualified Node 22.22.2
and exact npm 12.0.2 inside owned scratch, verifying clean lockv3 ci, stale lock refusal,
lock update, workspaces, peer resolution/conflict, overrides, optional platform skip,
lifecycle suppression, pack tarball, config precedence, and exec --no.
"""

from __future__ import annotations

import sys
import pytest

from src.test.apg_test_support import repository_root

ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src/test/support"))

from apg124_npm import (  # noqa: E402
    ALL_SCENARIOS,
    DEPENDENCY_TOPOLOGY_SCENARIOS,
    EXPECTED_NPM_VERSION,
    LIFECYCLE_EXECUTION_SCENARIOS,
    MANIFEST_LOCK_SCENARIOS,
    NpmHarnessConfig,
    execute_npm_harness,
    observe_npm_harness_config,
)

FIXTURES_DIR = ROOT / "src/test/fixtures/apg124-toolchain/npm"


@pytest.fixture(scope="module")
def harness_config() -> NpmHarnessConfig:
    """Acquire and validate fail-closed npm harness configuration."""
    return observe_npm_harness_config(ROOT)


def test_full_npm_harness_all_twelve_scenarios(harness_config: NpmHarnessConfig) -> None:
    """Execute complete 12-scenario synthetic npm suite and verify receipt."""
    receipt = execute_npm_harness(harness_config, FIXTURES_DIR, scenarios=ALL_SCENARIOS)

    assert receipt.is_clean_pass
    assert receipt.total_count == 12
    assert receipt.passed_count == 12
    assert receipt.failed_count == 0
    assert receipt.skipped_count == 0
    assert receipt.executing_version == EXPECTED_NPM_VERSION
    assert len(receipt.scenarios) == 12

    # Verify each scenario passed with positive assertions
    for sc_id in ALL_SCENARIOS:
        sc = receipt.get_scenario(sc_id)
        assert sc is not None, f"Scenario {sc_id} must be in receipt"
        assert sc.get("status") == "passed"
        assert sc.get("executing_version") == EXPECTED_NPM_VERSION
        assertions = sc.get("assertions", [])
        assert len(assertions) > 0
        for a in assertions:
            assert a.get("passed") is True, f"Assertion {a} failed in {sc_id}"


def test_manifest_lock_scenarios_partition(harness_config: NpmHarnessConfig) -> None:
    """Execute manifest and lockfile partition (NPM01, NPM02, NPM03)."""
    receipt = execute_npm_harness(harness_config, FIXTURES_DIR, scenarios=MANIFEST_LOCK_SCENARIOS)

    assert receipt.is_clean_pass
    assert receipt.total_count == 3
    assert receipt.passed_count == 3
    assert receipt.failed_count == 0

    sc1 = receipt.get_scenario("NPM01")
    assert sc1 is not None
    assert any(a["name"] == "hidden_lockfile_created" and a["passed"] for a in sc1["assertions"])
    assert any(a["name"] == "lockfile_unmodified" and a["passed"] for a in sc1["assertions"])

    sc2 = receipt.get_scenario("NPM02")
    assert sc2 is not None
    assert any(a["name"] == "sync_error_reported" and a["passed"] for a in sc2["assertions"])

    sc3 = receipt.get_scenario("NPM03")
    assert sc3 is not None
    assert any(a["name"] == "lockfile_updated_with_new_dep" and a["passed"] for a in sc3["assertions"])


def test_dependency_topology_scenarios_partition(harness_config: NpmHarnessConfig) -> None:
    """Execute dependency topology partition (NPM04, NPM05, NPM06, NPM07, NPM08)."""
    receipt = execute_npm_harness(harness_config, FIXTURES_DIR, scenarios=DEPENDENCY_TOPOLOGY_SCENARIOS)

    assert receipt.is_clean_pass
    assert receipt.total_count == 5
    assert receipt.passed_count == 5
    assert receipt.failed_count == 0

    # NPM04 workspaces
    sc4 = receipt.get_scenario("NPM04")
    assert sc4 is not None
    assert any(a["name"] == "workspace_script_output_verified" and a["passed"] for a in sc4["assertions"])

    # NPM05 peer success
    sc5 = receipt.get_scenario("NPM05")
    assert sc5 is not None
    assert any(a["name"] == "peer_and_host_installed" and a["passed"] for a in sc5["assertions"])

    # NPM06 peer conflict
    sc6 = receipt.get_scenario("NPM06")
    assert sc6 is not None
    assert any(a["name"] == "eresolve_conflict_reported" and a["passed"] for a in sc6["assertions"])

    # NPM07 overrides
    sc7 = receipt.get_scenario("NPM07")
    assert sc7 is not None
    assert any(a["name"] == "override_applied_successfully" and a["passed"] for a in sc7["assertions"])
    assert any(a["name"] == "overridden_version_verified" and a["passed"] for a in sc7["assertions"])
    assert any(a["name"] == "overridden_content_verified" and a["passed"] for a in sc7["assertions"])

    # NPM08 optional platform
    sc8 = receipt.get_scenario("NPM08")
    assert sc8 is not None
    assert any(a["name"] == "supported_optional_installed" and a["passed"] for a in sc8["assertions"])
    assert any(a["name"] == "unsupported_optional_skipped" and a["passed"] for a in sc8["assertions"])


def test_lifecycle_execution_scenarios_partition(harness_config: NpmHarnessConfig) -> None:
    """Execute lifecycle and execution partition (NPM09, NPM10, NPM11, NPM12)."""
    receipt = execute_npm_harness(harness_config, FIXTURES_DIR, scenarios=LIFECYCLE_EXECUTION_SCENARIOS)

    assert receipt.is_clean_pass
    assert receipt.total_count == 4
    assert receipt.passed_count == 4
    assert receipt.failed_count == 0

    # NPM09 lifecycle execution, suppression, and pre/post hooks
    sc9 = receipt.get_scenario("NPM09")
    assert sc9 is not None
    assert any(a["name"] == "install_positive_lifecycle_executed" and a["passed"] for a in sc9["assertions"])
    assert any(a["name"] == "dependency_lifecycle_executed" and a["passed"] for a in sc9["assertions"])
    assert any(a["name"] == "install_lifecycle_suppressed" and a["passed"] for a in sc9["assertions"])
    assert any(a["name"] == "run_pre_post_order_verified" and a["passed"] for a in sc9["assertions"])
    assert any(a["name"] == "run_ignore_scripts_suppressed_hooks" and a["passed"] for a in sc9["assertions"])

    # NPM10 pack tarball
    sc10 = receipt.get_scenario("NPM10")
    assert sc10 is not None
    assert any(a["name"] == "pack_files_allowlist_verified" and a["passed"] for a in sc10["assertions"])
    assert any(a["name"] == "consumer_bin_and_module_installed" and a["passed"] for a in sc10["assertions"])

    # NPM11 config precedence across five layers via registry
    sc11 = receipt.get_scenario("NPM11")
    assert sc11 is not None
    assert any(a["name"] == "global_registry_read" and a["passed"] for a in sc11["assertions"])
    assert any(a["name"] == "user_overrides_global" and a["passed"] for a in sc11["assertions"])
    assert any(a["name"] == "project_overrides_user" and a["passed"] for a in sc11["assertions"])
    assert any(a["name"] == "env_overrides_project" and a["passed"] for a in sc11["assertions"])
    assert any(a["name"] == "cli_overrides_env" and a["passed"] for a in sc11["assertions"])

    # NPM12 exec --no
    sc12 = receipt.get_scenario("NPM12")
    assert sc12 is not None
    assert any(a["name"] == "local_exec_stdout_verified" and a["passed"] for a in sc12["assertions"])
    assert any(a["name"] == "missing_binary_fails_closed" and a["passed"] for a in sc12["assertions"])


def test_keep_scratch_retains_artifacts(harness_config: NpmHarnessConfig) -> None:
    """Verify keep_scratch parameter retains scratch run artifacts on disk."""
    receipt = execute_npm_harness(
        harness_config,
        FIXTURES_DIR,
        scenarios=("NPM01",),
        keep_scratch=True,
    )
    assert receipt.retained_on_disk
    assert receipt.is_clean_pass
