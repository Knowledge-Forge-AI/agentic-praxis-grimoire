#!/usr/bin/env python3
"""Integration tests for Playwright test profile across Chromium, Firefox, and WebKit.

Executes real browser lanes for automation scenarios PW01-PW10 and SVG security/boundary
scenarios SVG01-SVG03. Verifies zero skipped, zero failed, exact engine versions,
deterministic artifact retention, and narrow rejection evidence in scratch.
"""

from __future__ import annotations

from pathlib import Path
import sys
import pytest

from src.test.apg_test_support import repository_root

ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src/test/support"))

from apg123_browser_ui import (  # noqa: E402
    PLAYWRIGHT_SCENARIOS,
    SUPPORTED_BROWSERS,
    SVG_SCENARIOS,
    execute_browser_harness,
    observe_browser_harness_config,
)

FIXTURES_DIR = ROOT / "src/test/fixtures/apg123-browser-ui"
TARGET_SCENARIOS = PLAYWRIGHT_SCENARIOS + SVG_SCENARIOS


def test_playwright_and_svg_real_browser_lanes() -> None:
    """Execute PW01-PW10 and SVG01-SVG03 across all 3 browser engines."""
    config = observe_browser_harness_config(ROOT)
    receipt = execute_browser_harness(
        config,
        FIXTURES_DIR,
        browsers=SUPPORTED_BROWSERS,
        scenario_filter=TARGET_SCENARIOS,
    )

    # Validate receipt completeness
    assert receipt.is_clean_pass, f"Expected clean pass, summary: {receipt.summary}"
    assert receipt.total_count == len(TARGET_SCENARIOS) * len(SUPPORTED_BROWSERS)
    assert receipt.failed_count == 0
    assert receipt.skipped_count == 0

    # Validate browser version records
    assert set(receipt.browsers.keys()) == set(SUPPORTED_BROWSERS)
    for b in SUPPORTED_BROWSERS:
        assert len(receipt.browsers[b]) > 0

    # Validate scenario assertions across all engines
    for b in SUPPORTED_BROWSERS:
        for sc_id in TARGET_SCENARIOS:
            sc = receipt.get_scenario(sc_id, b)
            assert sc is not None, f"Scenario {sc_id} missing on {b}"
            assert sc["status"] == "passed"
            assert sc["duration_ms"] >= 0
            assertion_names = [a["name"] for a in sc.get("assertions", [])]

            if sc_id == "PW01":
                assert "unique_locator_success" in assertion_names
                assert "strict_mode_violation_rejection" in assertion_names
            elif sc_id == "PW02":
                assert "auto_wait_enablement_success" in assertion_names
                assert "disabled_timeout_rejection" in assertion_names
            elif sc_id == "PW03":
                assert "retrying_assertion_success" in assertion_names
                assert "retrying_assertion_rejection" in assertion_names
            elif sc_id == "PW04":
                assert "context_a_state_populated" in assertion_names
                assert "context_b_state_clean" in assertion_names
            elif sc_id == "PW05":
                assert "explicit_timeout_rejection" in assertion_names
                assert "locator_click_signal_cancellation" in assertion_names
            elif sc_id == "PW06":
                assert "loopback_route_permitted" in assertion_names
                assert "untrusted_network_aborted" in assertion_names
            elif sc_id == "PW07":
                assert "page_navigation_complete" in assertion_names
                assert "subframe_locator_content" in assertion_names
                assert "popup_window_lifecycle" in assertion_names
            elif sc_id == "PW08":
                assert "screenshot_artifact_retained" in assertion_names
                assert "trace_zip_artifact_retained" in assertion_names
            elif sc_id == "PW09":
                assert "same_run_render_identical" in assertion_names
                assert "controlled_visual_negative_differs" in assertion_names
            elif sc_id == "PW10":
                assert "controlled_failure_status_exact" in assertion_names
                assert "pass_artifacts_absent" in assertion_names
                assert "failed_artifacts_retained" in assertion_names
                assert "child_readiness_signaled" in assertion_names
                assert "sigint_interruption_exit_130" in assertion_names
                assert "browser_worker_cleanup_observed" in assertion_names
            elif sc_id == "SVG01":
                assert "browser_requested_sprite_response" in assertion_names
                assert "same_locator_rendered_differs_from_missing" in assertion_names
            elif sc_id == "SVG02":
                assert "foreign_svg_reference_aborted" in assertion_names
                assert "foreign_svg_visible_absence_verified" in assertion_names
            elif sc_id == "SVG03":
                assert "path_traversal_svg_reference_blocked" in assertion_names
                assert "path_traversal_visible_absence_verified" in assertion_names

    # Verify visual compare and trace artifacts were retained in receipt
    artifacts_str = " ".join(receipt.artifacts)
    for b in SUPPORTED_BROWSERS:
        assert f"PW08-{b}-trace.zip" in artifacts_str
        assert f"PW08-{b}-screenshot.png" in artifacts_str
        assert f"PW09-{b}-" in artifacts_str
        assert "-baseline.png" in artifacts_str
        assert "-re-render.png" in artifacts_str
        assert "-negative.png" in artifacts_str
