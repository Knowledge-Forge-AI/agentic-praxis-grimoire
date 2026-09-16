#!/usr/bin/env python3
"""Integration tests for APG123 and APG125 browser UI support harness.

Validates the full matrix of 24 APG123 scenarios across Chromium, Firefox, and WebKit (72 executions),
and the matrix of 14 APG125 browser runtime scenarios across Chromium, Firefox, and WebKit (42 executions).
Also validates prerequisite refusal boundaries and evaluation receipt completeness.
"""

from __future__ import annotations

from pathlib import Path
import sys
import pytest

from src.test.apg_test_support import repository_root

ROOT = repository_root(__file__)
SUPPORT = ROOT / "src/test/support"
sys.path.insert(0, str(SUPPORT))

from apg123_browser_ui import (  # noqa: E402
    APG123_SCENARIOS,
    BROWSER_RUNTIME_SCENARIOS,
    BrowserHarnessConfig,
    BrowserHarnessPrerequisiteError,
    execute_browser_harness,
    observe_browser_harness_config,
    validate_browser_cache,
    validate_node_executable,
    validate_playwright_package,
    validate_scratch_root,
)

FIXTURES_DIR = ROOT / "src/test/fixtures/apg123-browser-ui"


@pytest.fixture
def harness_config() -> BrowserHarnessConfig:
    """Return validated BrowserHarnessConfig using caller environment without hardcoded fallbacks."""
    return observe_browser_harness_config(ROOT)


def test_browser_runtime_scenarios_matrix_distinct_verification(harness_config: BrowserHarnessConfig) -> None:
    """Distinctly verify all 14 APG125 browser runtime scenarios across Chromium, Firefox, and WebKit (42 executions)."""
    receipt = execute_browser_harness(
        config=harness_config,
        fixtures_dir=FIXTURES_DIR,
        browsers=("chromium", "firefox", "webkit"),
        group="browser_runtime",
    )

    assert receipt.is_clean_pass
    assert receipt.total_count == 42
    assert receipt.passed_count == 42
    assert receipt.failed_count == 0
    assert receipt.skipped_count == 0

    # Verify each of the 14 BR scenarios is present for all 3 browsers
    for sc_id in BROWSER_RUNTIME_SCENARIOS:
        for browser in ("chromium", "firefox", "webkit"):
            sc = receipt.get_scenario(sc_id, browser)
            assert sc is not None, f"Missing scenario {sc_id} for browser {browser}"
            assert sc.get("status") == "passed"
            assertions = sc.get("assertions", [])
            assert len(assertions) > 0, f"Scenario {sc_id} on {browser} has no assertions"
            for assertion in assertions:
                assert assertion.get("passed") is True, f"Assertion failed: {assertion} in {sc_id} on {browser}"

    # Verify browser environments metadata is present in raw receipt
    browser_envs = receipt.raw.get("browser_environments", {})
    assert set(browser_envs.keys()) == {"chromium", "firefox", "webkit"}
    for b in ("chromium", "firefox", "webkit"):
        env_meta = browser_envs[b]
        assert env_meta.get("headless") is True
        assert len(env_meta.get("user_agent", "")) > 0
        assert len(env_meta.get("arch", "")) > 0
        assert len(env_meta.get("os_release", "")) > 0
        assert env_meta.get("origin_role") == "primary"
        assert env_meta.get("features", {}).get("Worker") is True
        assert env_meta.get("features", {}).get("MutationObserver") is True
        assert env_meta.get("features", {}).get("customElements") is True
        assert env_meta.get("features", {}).get("shadowDOM") is True

    # Verify receipt runtime metadata binds runner_sha256, register_sha256, table_sha256, and authority
    runtime_meta = receipt.raw.get("runtime", {})
    runner_sha256 = runtime_meta.get("runner_sha256")
    assert runner_sha256 is not None
    assert len(runner_sha256) == 64
    register_sha256 = runtime_meta.get("register_sha256")
    assert register_sha256 is not None
    assert len(register_sha256) == 64
    table_sha256 = runtime_meta.get("table_sha256")
    assert table_sha256 is not None
    assert len(table_sha256) == 64
    assert receipt.raw.get("authority") == "APG125-BROWSER-RUNTIME-QUALIFIED-RECEIPT"


def test_apg123_scenarios_matrix_distinct_verification(harness_config: BrowserHarnessConfig) -> None:
    """Distinctly verify all 24 APG123 scenarios across Chromium, Firefox, and WebKit (72 executions)."""
    receipt = execute_browser_harness(
        config=harness_config,
        fixtures_dir=FIXTURES_DIR,
        browsers=("chromium", "firefox", "webkit"),
        group="apg123",
    )

    assert receipt.is_clean_pass
    assert receipt.total_count == 72
    assert receipt.passed_count == 72
    assert receipt.failed_count == 0
    assert receipt.skipped_count == 0

    # Verify each of the 24 APG123 scenarios is present for all 3 browsers
    for sc_id in APG123_SCENARIOS:
        for browser in ("chromium", "firefox", "webkit"):
            sc = receipt.get_scenario(sc_id, browser)
            assert sc is not None, f"Missing scenario {sc_id} for browser {browser}"
            assert sc.get("status") == "passed"

    # Verify receipt runtime metadata binds runner_sha256, register_sha256, table_sha256, and authority
    runtime_meta = receipt.raw.get("runtime", {})
    runner_sha256 = runtime_meta.get("runner_sha256")
    assert runner_sha256 is not None
    assert len(runner_sha256) == 64
    register_sha256 = runtime_meta.get("register_sha256")
    assert register_sha256 is not None
    assert len(register_sha256) == 64
    table_sha256 = runtime_meta.get("table_sha256")
    assert table_sha256 is not None
    assert len(table_sha256) == 64
    assert receipt.raw.get("authority") == "APG123-BROWSER-UI-QUALIFIED-RECEIPT"



def test_prerequisite_fail_closed_boundaries(tmp_path: Path) -> None:
    """Verify fail-closed refusal rules for missing or invalid prerequisites."""
    # 1. Missing node executable
    with pytest.raises(BrowserHarnessPrerequisiteError, match="must be an executable file"):
        validate_node_executable(tmp_path / "nonexistent-node", ROOT)

    # 2. Missing scratch directory
    with pytest.raises(BrowserHarnessPrerequisiteError, match="could not be resolved"):
        validate_scratch_root(tmp_path / "nonexistent-scratch", ROOT)

    # 3. Missing package root
    with pytest.raises(BrowserHarnessPrerequisiteError, match="Playwright packages not found"):
        validate_playwright_package(tmp_path, ROOT)

    # 4. Incomplete browser cache
    cache_dir = tmp_path / "cache"
    (cache_dir / "chromium-1234").mkdir(parents=True)
    with pytest.raises(BrowserHarnessPrerequisiteError, match="Missing browser binaries"):
        validate_browser_cache(cache_dir)
