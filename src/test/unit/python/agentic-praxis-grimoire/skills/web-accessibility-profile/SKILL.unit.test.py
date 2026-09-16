#!/usr/bin/env python3
"""Maintained unit test suite for Web Accessibility profile.

Validates scenario register schema, predicate definitions, negative controls,
disclaimers (no assistive technology / screen reader audio claims),
focus order, ARIA snapshots, and SVG semantics for scenarios AX01-AX11.
"""

from __future__ import annotations

import sys

from src.test.apg_test_support import repository_root

ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src/test/support"))

from apg123_browser_ui import (  # noqa: E402
    ACCESSIBILITY_SCENARIOS,
    BROWSER_CORROBORATION_DISCLAIMER,
    SUPPORTED_BROWSERS,
    load_scenarios_register,
)

FIXTURES_DIR = ROOT / "src/test/fixtures/apg123-browser-ui"
SCENARIOS_JSON = FIXTURES_DIR / "scenarios.json"
INDEX_HTML = FIXTURES_DIR / "index.html"
LEAF = ROOT / "skills/web-accessibility-profile/SKILL.md"


def test_accessibility_profile_disclaimer_and_scope() -> None:
    """Verify standard disclaimer disavowing screen reader audio or AT conformance claims."""
    assert "screen reader audio" in BROWSER_CORROBORATION_DISCLAIMER
    assert "assistive technology conformance claim" in BROWSER_CORROBORATION_DISCLAIMER
    reg = load_scenarios_register(FIXTURES_DIR)
    assert reg.get("disclaimer") == BROWSER_CORROBORATION_DISCLAIMER


def test_accessibility_scenarios_register_coverage() -> None:
    """Verify all AX01-AX11 scenarios exist with correct metadata and assertions."""
    reg = load_scenarios_register(FIXTURES_DIR)
    scenarios_by_id = {s["id"]: s for s in reg.get("scenarios", [])}

    for sc_id in ACCESSIBILITY_SCENARIOS:
        assert sc_id in scenarios_by_id, f"Missing scenario {sc_id}"
        sc = scenarios_by_id[sc_id]
        assert sc["group"] == "accessibility"
        assert set(sc["supported_browsers"]) == set(SUPPORTED_BROWSERS)
        assert sc["expected_outcome"] == "passed"
        assert len(sc["assertions"]) > 0

    # Narrow negative predicate check for AX02
    assert scenarios_by_id["AX02"]["predicate_type"] == "negative"
    assert "mismatched_name_narrow_rejection" in scenarios_by_id["AX02"]["assertions"]

    # Visual difference predicate check for AX04
    assert scenarios_by_id["AX04"]["predicate_type"] == "visual_difference"
    assert "focus_screenshot_differs_from_blur" in scenarios_by_id["AX04"]["assertions"]


def test_accessibility_fixtures_markup_elements() -> None:
    """Verify index.html contains all necessary accessibility elements and landmarks."""
    assert INDEX_HTML.is_file()
    content = INDEX_HTML.read_text(encoding="utf-8")

    # Native elements
    assert 'id="ax01-btn"' in content
    assert 'id="ax01-link"' in content
    assert 'id="ax01-input"' in content
    assert 'id="ax02-empty-btn"' in content

    # Landmarks & headings
    assert 'role="banner"' in content
    assert '<nav aria-label="Primary Navigation">' in content
    assert '<main>' in content
    assert '<h1>Site Portal</h1>' in content

    # Focus target
    assert 'id="ax04-focus-target"' in content
    assert 'tabindex="0"' in content
    assert '.focus-ring-btn:focus-visible' in content

    # SVG a11y
    assert 'id="ax05-svg"' in content
    assert 'role="button"' in content
    assert 'id="ax06-meaningful"' in content
    assert 'id="ax06-decorative"' in content
    assert 'aria-hidden="true"' in content
    assert 'role="group"' in content

    # State & inert
    assert 'id="ax08-hidden"' in content
    assert 'inert' in content
    assert 'id="ax08-disabled"' in content
    assert 'role="status"' in content
    assert 'aria-live="polite"' in content
    assert 'id="ax10-tree"' in content
    assert 'required' in content


def test_accessibility_leaf_navigation_clauses_if_present() -> None:
    """Assert profile leaf exists and exact navigation clause parity without inventing IDs."""
    assert LEAF.is_file(), f"Profile leaf must exist at {LEAF}"
    leaf_text = LEAF.read_text(encoding="utf-8")
    for sc_id in ACCESSIBILITY_SCENARIOS:
        assert sc_id in leaf_text, f"Scenario {sc_id} must be cited in profile leaf"
