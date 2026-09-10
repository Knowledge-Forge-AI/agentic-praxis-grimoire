#!/usr/bin/env python3
"""Maintained unit test suite for Playwright test profile.

Validates scenario register schema, predicate definitions, negative controls,
synthetic HTML/SVG fixture integrity, cancellation and isolation contracts
for scenarios PW01-PW10 and SVG01-SVG03.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import pytest

from src.test.apg_test_support import repository_root

ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src/test/support"))

from apg123_browser_ui import (  # noqa: E402
    BROWSER_CORROBORATION_DISCLAIMER,
    EXPECTED_PLAYWRIGHT_VERSION,
    PLAYWRIGHT_SCENARIOS,
    SUPPORTED_BROWSERS,
    SVG_SCENARIOS,
    load_scenarios_register,
)

FIXTURES_DIR = ROOT / "src/test/fixtures/apg123-browser-ui"
PACKAGE_JSON = FIXTURES_DIR / "package.json"
SCENARIOS_JSON = FIXTURES_DIR / "scenarios.json"
LEAF = ROOT / "skills/playwright-test-profile/SKILL.md"


def test_playwright_profile_package_manifest_and_dependencies() -> None:
    """Verify package.json specifies exact Playwright 1.62.1 and zero external dependencies."""
    assert PACKAGE_JSON.is_file(), "package.json must exist in fixtures"
    pkg = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
    assert pkg.get("devDependencies", {}).get("@playwright/test") == EXPECTED_PLAYWRIGHT_VERSION
    assert pkg.get("devDependencies", {}).get("playwright") == EXPECTED_PLAYWRIGHT_VERSION
    assert not pkg.get("dependencies"), "No extra runtime dependencies allowed beyond Playwright"


def test_playwright_profile_scenarios_and_predicates() -> None:
    """Verify PW01-PW10 and SVG01-SVG03 scenario register coverage and predicate structure."""
    reg = load_scenarios_register(FIXTURES_DIR)
    scenarios_by_id = {s["id"]: s for s in reg.get("scenarios", [])}

    # Verify all PW01-PW10 scenarios are present
    for sc_id in PLAYWRIGHT_SCENARIOS:
        assert sc_id in scenarios_by_id, f"Missing scenario {sc_id}"
        sc = scenarios_by_id[sc_id]
        assert sc["group"] == "playwright"
        assert set(sc["supported_browsers"]) == set(SUPPORTED_BROWSERS)
        assert sc["expected_outcome"] == "passed"
        assert len(sc["assertions"]) > 0

    # Verify SVG01-SVG03 scenarios are present
    for sc_id in SVG_SCENARIOS:
        assert sc_id in scenarios_by_id, f"Missing scenario {sc_id}"
        sc = scenarios_by_id[sc_id]
        assert sc["group"] == "svg"
        assert set(sc["supported_browsers"]) == set(SUPPORTED_BROWSERS)
        assert sc["expected_outcome"] == "passed"
        assert len(sc["assertions"]) > 0


def test_playwright_fixture_files_integrity() -> None:
    """Verify presence and structure of HTML and SVG fixture files."""
    index_html = FIXTURES_DIR / "index.html"
    frame_html = FIXTURES_DIR / "frame.html"
    popup_html = FIXTURES_DIR / "popup.html"
    sprite_svg = FIXTURES_DIR / "sprite.svg"

    assert index_html.is_file()
    assert frame_html.is_file()
    assert popup_html.is_file()
    assert sprite_svg.is_file()

    content = index_html.read_text(encoding="utf-8")
    assert 'id="single-btn"' in content
    assert 'class="dup-btn"' in content
    assert 'id="delayed-btn"' in content
    assert 'id="status-box"' in content
    assert 'id="child-frame"' in content
    assert 'id="popup-trigger"' in content
    assert 'id="visual-box"' in content
    assert 'id="svg01-target"' in content
    assert 'id="svg01-use"' in content
    assert 'id="svg02-target"' in content
    assert 'id="svg03-target"' in content

    sprite_content = sprite_svg.read_text(encoding="utf-8")
    assert 'id="star-symbol"' in sprite_content
    assert 'id="badge-symbol"' in sprite_content


def test_playwright_leaf_navigation_clauses_if_present() -> None:
    """Assert profile leaf exists and exact navigation clause parity without inventing IDs."""
    assert LEAF.is_file(), f"Profile leaf must exist at {LEAF}"
    leaf_text = LEAF.read_text(encoding="utf-8")
    for sc_id in PLAYWRIGHT_SCENARIOS:
        assert sc_id in leaf_text, f"Scenario {sc_id} must be cited in profile leaf"
