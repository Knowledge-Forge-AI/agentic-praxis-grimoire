#!/usr/bin/env python3
"""Integration tests for Web Accessibility profile across Chromium, Firefox, and WebKit.

Executes real browser lanes for accessibility scenarios AX01-AX11.
Verifies accessible name calculation, narrow intentional name failure rejection,
visible focus screenshot rendering differences, ARIA snapshots, live-region DOM updates,
and AT disclaimer preservation in scratch.
"""

from __future__ import annotations

from pathlib import Path
import sys
import pytest

from src.test.apg_test_support import repository_root

ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src/test/support"))

from apg123_browser_ui import (  # noqa: E402
    ACCESSIBILITY_SCENARIOS,
    SUPPORTED_BROWSERS,
    execute_browser_harness,
    observe_browser_harness_config,
)

FIXTURES_DIR = ROOT / "src/test/fixtures/apg123-browser-ui"


def test_web_accessibility_real_browser_lanes() -> None:
    """Execute AX01-AX11 across all 3 browser engines."""
    config = observe_browser_harness_config(ROOT)
    receipt = execute_browser_harness(
        config,
        FIXTURES_DIR,
        browsers=SUPPORTED_BROWSERS,
        group="accessibility",
    )

    # Validate receipt completeness
    assert receipt.is_clean_pass, f"Expected clean pass, summary: {receipt.summary}"
    assert receipt.total_count == len(ACCESSIBILITY_SCENARIOS) * len(SUPPORTED_BROWSERS)
    assert receipt.failed_count == 0
    assert receipt.skipped_count == 0

    # Validate browser version records
    assert set(receipt.browsers.keys()) == set(SUPPORTED_BROWSERS)
    for b in SUPPORTED_BROWSERS:
        assert len(receipt.browsers[b]) > 0

    # Validate scenario assertions across all engines
    for b in SUPPORTED_BROWSERS:
        for sc_id in ACCESSIBILITY_SCENARIOS:
            sc = receipt.get_scenario(sc_id, b)
            assert sc is not None, f"Scenario {sc_id} missing on {b}"
            assert sc["status"] == "passed"
            assert sc["duration_ms"] >= 0
            assertion_names = [a["name"] for a in sc.get("assertions", [])]

            if sc_id == "AX01":
                assert "button_accessible_name" in assertion_names
                assert "link_aria_label" in assertion_names
                assert "input_label_association" in assertion_names
            elif sc_id == "AX02":
                assert "empty_name_verified" in assertion_names
                assert "mismatched_name_narrow_rejection" in assertion_names
            elif sc_id == "AX03":
                assert "heading_levels_resolved" in assertion_names
                assert "landmarks_resolved" in assertion_names
            elif sc_id == "AX04":
                assert "focus_screenshot_differs_from_blur" in assertion_names
                assert "tab_navigation_advances" in assertion_names
            elif sc_id == "AX05":
                assert "svg_accessible_name" in assertion_names
                assert "svg_keyboard_focus" in assertion_names
                assert "svg_enter_space_activation" in assertion_names
            elif sc_id == "AX06":
                assert "meaningful_svg_role_and_name" in assertion_names
                assert "decorative_svg_hidden_and_empty" in assertion_names
            elif sc_id == "AX07":
                assert "figure_group_labelled" in assertion_names
                assert "svg_image_labelled" in assertion_names
                assert "table_data_headers_accessible" in assertion_names
            elif sc_id == "AX08":
                assert "element_hidden_verified" in assertion_names
                assert "element_disabled_verified" in assertion_names
                assert "inert_interaction_rejected" in assertion_names
            elif sc_id == "AX09":
                assert "live_region_role_attributes" in assertion_names
                assert "dynamic_message_text_updated" in assertion_names
                # Check disclaimer preservation
                for a in sc.get("assertions", []):
                    if a["name"] == "dynamic_message_text_updated":
                        assert "screen reader" in a.get("disclaimer", "")
            elif sc_id == "AX10":
                assert "aria_snapshot_structure_matches" in assertion_names
            elif sc_id == "AX11":
                assert "form_constraint_validation" in assertion_names
                assert "table_headers_accessible" in assertion_names
                assert "reduced_motion_emulation" in assertion_names

    # Verify visible focus screenshot artifacts
    artifacts_str = " ".join(receipt.artifacts)
    for b in SUPPORTED_BROWSERS:
        assert f"AX04-{b}-" in artifacts_str
        assert "-blur.png" in artifacts_str
        assert "-focus.png" in artifacts_str
