#!/usr/bin/env python3
"""Integration tests for APG124 Vite 8.2.2 build and dev toolchain profile.

Executes real programmatic Vite 8.2.2 build, serve, HMR invalidation, preview,
and Rolldown compilation scenarios VITE01-VITE12 in owned scratch. Verifies zero
skipped, zero failed, exact toolchain identities, deterministic digest matching,
and fail-closed prerequisite validation.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
import pytest

from src.test.apg_test_support import repository_root

ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src/test/support"))

from apg124_vite import (  # noqa: E402
    ALL_SCENARIOS,
    EXPECTED_NODE_VERSION,
    EXPECTED_ROLLDOWN_VERSION,
    EXPECTED_VITE_VERSION,
    ViteHarnessConfig,
    ViteHarnessPrerequisiteError,
    ViteHarnessReceipt,
    execute_vite_harness,
    observe_vite_harness_config,
    validate_prerequisites,
)

FIXTURES_DIR = ROOT / "src/test/fixtures/apg124-toolchain/vite"


def test_vite_prerequisites_fail_closed_contract() -> None:
    """Validate that prerequisites fail closed and return verified toolchain metadata."""
    prereq = validate_prerequisites(ROOT)
    assert prereq["package_version"] == EXPECTED_VITE_VERSION
    assert prereq["rolldown_version"] == EXPECTED_ROLLDOWN_VERSION
    assert prereq["node_version"] == "v22.22.2"
    assert prereq["execution_verified"] is False


def test_vite_toolchain_full_suite_execution() -> None:
    """Execute full VITE01-VITE12 scenario suite and verify assertions."""
    config = observe_vite_harness_config(ROOT)
    receipt = execute_vite_harness(config, FIXTURES_DIR)

    # 1. Summary validation
    assert receipt.is_clean_pass, f"Expected clean pass, got summary: {receipt.summary}"
    assert receipt.total_count == 12
    assert receipt.passed_count == 12
    assert receipt.failed_count == 0
    assert receipt.skipped_count == 0

    # 2. Toolchain metadata validation
    toolchain = receipt.toolchain
    assert toolchain.get("vite_version") == EXPECTED_VITE_VERSION
    assert toolchain.get("node_version") == "v22.22.2"
    assert toolchain.get("node_identity") == EXPECTED_NODE_VERSION

    # 3. Assertions validation across all 12 scenarios
    for sc_id in ALL_SCENARIOS:
        sc = receipt.get_scenario(sc_id)
        assert sc is not None, f"Scenario {sc_id} missing from receipt"
        assert sc["status"] == "passed"
        assert sc["duration_ms"] >= 0
        assertion_names = [a["name"] for a in sc.get("assertions", [])]

        if sc_id == "VITE01":
            assert "resolved_root_exact" in assertion_names
            assert "base_normalized" in assertion_names
            assert "public_dir_resolved" in assertion_names
            assert "build_command_assigned" in assertion_names
        elif sc_id == "VITE02":
            assert "vite_prefix_env_exposed" in assertion_names
            assert "secret_env_suppressed" in assertion_names
            assert "client_bundle_secret_absent" in assertion_names
        elif sc_id == "VITE03":
            assert "alias_resolved_in_bundle" in assertion_names
            assert "public_asset_copied_verbatim" in assertion_names
            assert "css_processed_and_hashed" in assertion_names
        elif sc_id == "VITE04":
            assert "pre_plugin_ordered_before_post" in assertion_names
            assert "build_plugin_applied" in assertion_names
            assert "serve_plugin_skipped_in_build" in assertion_names
            assert "virtual_module_resolved" in assertion_names
        elif sc_id == "VITE05":
            assert "loopback_server_bound" in assertion_names
            assert "allowed_file_200_ok" in assertion_names
            assert "denied_file_403_forbidden" in assertion_names
            assert "outside_traversal_403_forbidden" in assertion_names
            assert "server_closed_cleanly" in assertion_names
        elif sc_id == "VITE06":
            assert "module_graph_entry_resolved" in assertion_names
            assert "module_invalidation_detected" in assertion_names
            assert "server_closed_cleanly" in assertion_names
        elif sc_id == "VITE07":
            assert "manifest_json_generated" in assertion_names
            assert "entry_mapped_to_hashed_chunk" in assertion_names
            assert "css_assets_tracked_in_manifest" in assertion_names
        elif sc_id == "VITE08":
            assert "dynamic_import_chunk_split" in assertion_names
            assert "lib_esm_format_generated" in assertion_names
            assert "lib_cjs_format_generated" in assertion_names
        elif sc_id == "VITE09":
            assert "sourcemap_enabled_generates_map" in assertion_names
            assert "sourcemap_disabled_omits_map" in assertion_names
        elif sc_id == "VITE10":
            assert "preview_loopback_bound" in assertion_names
            assert "preview_serves_build_200_ok" in assertion_names
            assert "preview_closed_cleanly" in assertion_names
        elif sc_id == "VITE11":
            assert "two_builds_file_manifest_identical" in assertion_names
            assert "two_builds_sha256_identical" in assertion_names
        elif sc_id == "VITE12":
            assert "missing_library_entry_refused" in assertion_names
            assert "misconfigured_input_refused" in assertion_names


def test_vite_toolchain_filtered_scenario_execution() -> None:
    """Execute a targeted subset of scenarios via filter."""
    config = observe_vite_harness_config(ROOT)
    selected = ("VITE01", "VITE05", "VITE11")
    receipt = execute_vite_harness(config, FIXTURES_DIR, scenario_filter=selected)

    assert receipt.is_clean_pass
    assert receipt.total_count == 3
    assert receipt.passed_count == 3
    for sc_id in selected:
        sc = receipt.get_scenario(sc_id)
        assert sc is not None
        assert sc["status"] == "passed"
    assert receipt.get_scenario("VITE02") is None
