#!/usr/bin/env python3
"""Unit tests for APG123 browser UI support module (apg123_browser_ui.py).

Validates fail-closed refusal contracts for Node identity, Playwright package root,
scratch ownership boundaries, browser cache validation, scenario register schema,
and evaluation receipt completeness.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import subprocess
import pytest

from src.test.apg_test_support import repository_root

ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src/test/support"))

from apg123_browser_ui import (  # noqa: E402
    ACCESSIBILITY_SCENARIOS, ALL_SCENARIOS,
    APG123_BROWSER_UI_AUTHORITY, APG125_BROWSER_MIXED_AUTHORITY,
    APG125_BROWSER_RUNTIME_AUTHORITY,
    APG123_SCENARIOS,
    BROWSER_CORROBORATION_DISCLAIMER,
    BROWSER_RUNTIME_SCENARIOS,
    EXPECTED_NODE_VERSION,
    EXPECTED_PLAYWRIGHT_VERSION,
    FAMILY_TABLE_AUTHORITY,
    FAMILY_TABLE_SCHEMA_VERSION,
    PLAYWRIGHT_SCENARIOS,
    SCENARIO_GROUPS,
    SUPPORTED_BROWSERS,
    SVG_SCENARIOS,
    BrowserHarnessConfig,
    BrowserHarnessExecutionError,
    BrowserHarnessPrerequisiteError,
    BrowserHarnessValidationError,
    cleanup_retained_failure_evidence,
    execute_browser_harness,
    load_family_table,
    load_scenarios_register,
    observe_browser_harness_config,
    resolve_scenario_family_authority,
    retain_failure_evidence,
    sanitize_evidence_text,
    validate_browser_cache,
    validate_family_table,
    validate_family_table_and_register,
    validate_node_executable,
    validate_playwright_package,
    validate_receipt,
    validate_scratch_root,
)

FIXTURES_DIR = ROOT / "src/test/fixtures/apg123-browser-ui"


@pytest.mark.parametrize("failed", [False, True])
@pytest.mark.parametrize("mutation", ["none", "skip", "wrong-project", "wrong-title", "extra-result", "global-error", "unrelated-failure"])
def test_supervisor_report_rejects_unrelated_or_incomplete_results(failed: bool, mutation: str) -> None:
    title = "supervisor-fail" if failed else "supervisor-pass"
    result = {"status": "failed" if failed else "passed", "error": {"message": "toHaveText CONTROLLED_FAILURE_INTENTIONAL_MISMATCH"}}
    test = {"projectName": "chromium", "status": "unexpected" if failed else "expected", "results": [result]}
    spec = {"title": title, "tests": [test]}
    report = {"stats": {"expected": int(not failed), "unexpected": int(failed), "skipped": 0, "flaky": 0}, "errors": [], "suites": [{"specs": [spec]}]}
    if mutation == "skip":
        report["stats"]["skipped"] = 1
    elif mutation == "wrong-project":
        test["projectName"] = "webkit"
    elif mutation == "wrong-title":
        spec["title"] = "unrelated"
    elif mutation == "extra-result":
        test["results"].append(result.copy())
    elif mutation == "global-error":
        report["errors"].append({"message": "fixture failed"})
    elif mutation == "unrelated-failure":
        result["status"] = "failed"
        result["error"]["message"] = "navigation timeout"
    script = "import {validateSupervisorReport as check} from " + json.dumps((FIXTURES_DIR / "supervisor_runner.mjs").as_uri()) + "; try { check(JSON.parse(process.argv[1]), 'chromium', process.argv[2], process.argv[3] === 'true'); } catch { process.exitCode = 1; }"
    observed = subprocess.run([os.environ["APG_JAVASCRIPT_NODE"], "--input-type=module", "-e", script, json.dumps(report), title, str(failed).lower()], capture_output=True, text=True, timeout=10)
    assert observed.returncode == (0 if mutation == "none" else 1), observed.stderr


def test_scenario_register_and_partition_constants() -> None:
    """Verify scenario registers and metadata constants."""
    assert len(PLAYWRIGHT_SCENARIOS) == 10
    assert len(ACCESSIBILITY_SCENARIOS) == 11
    assert len(SVG_SCENARIOS) == 3
    assert len(APG123_SCENARIOS) == 24
    assert len(BROWSER_RUNTIME_SCENARIOS) == 14
    assert len(ALL_SCENARIOS) == 38
    assert set(PLAYWRIGHT_SCENARIOS) & set(ACCESSIBILITY_SCENARIOS) == set()
    assert set(PLAYWRIGHT_SCENARIOS) & set(SVG_SCENARIOS) == set()
    assert set(ACCESSIBILITY_SCENARIOS) & set(SVG_SCENARIOS) == set()
    assert set(APG123_SCENARIOS) & set(BROWSER_RUNTIME_SCENARIOS) == set()
    assert set(APG123_SCENARIOS) | set(BROWSER_RUNTIME_SCENARIOS) == set(ALL_SCENARIOS)

    assert set(SUPPORTED_BROWSERS) == {"chromium", "firefox", "webkit"}
    assert set(SCENARIO_GROUPS) == {"all", "playwright", "accessibility", "svg", "browser_runtime", "browser-runtime", "apg123"}
    assert EXPECTED_PLAYWRIGHT_VERSION == "1.62.1"
    assert "screen reader audio" in BROWSER_CORROBORATION_DISCLAIMER


def test_scenario_register_fixture_file() -> None:
    """Verify scenarios.json fixture structure, descriptions, and supported engines."""
    reg = load_scenarios_register(FIXTURES_DIR)
    assert reg.get("schema_version") == "1.0.0"
    assert "disclaimer" in reg
    scenarios = reg.get("scenarios", [])
    assert len(scenarios) == 38

    seen_ids = set()
    for sc in scenarios:
        sc_id = sc.get("id")
        seen_ids.add(sc_id)
        assert sc.get("group") in ("playwright", "accessibility", "svg", "browser_runtime")
        assert len(sc.get("title", "")) > 0
        assert len(sc.get("description", "")) > 0
        assert sc.get("predicate_type") in ("positive", "negative", "paired", "visual_difference")
        assert sc.get("supported_browsers") == ["chromium", "firefox", "webkit"]
        assert sc.get("expected_outcome") == "passed"
        assert len(sc.get("assertions", [])) > 0

    assert seen_ids == set(ALL_SCENARIOS)


def test_scratch_root_validation_success_and_refusals(tmp_path: Path) -> None:
    """Validate scratch boundary enforcement and refusal rules."""
    external_scratch = tmp_path / "valid-scratch"
    external_scratch.mkdir()
    validated = validate_scratch_root(external_scratch, ROOT)
    assert validated == external_scratch.resolve()

    with pytest.raises(BrowserHarnessPrerequisiteError, match="must be absolute"):
        validate_scratch_root(Path("relative/path"), ROOT)

    with pytest.raises(BrowserHarnessPrerequisiteError, match="could not be resolved"):
        validate_scratch_root(tmp_path / "non-existent", ROOT)

    fake_file = tmp_path / "file.txt"
    fake_file.write_text("data")
    with pytest.raises(BrowserHarnessPrerequisiteError, match="must be an existing directory"):
        validate_scratch_root(fake_file, ROOT)

    symlink_scratch = tmp_path / "symlink-scratch"
    symlink_scratch.symlink_to(external_scratch)
    with pytest.raises(BrowserHarnessPrerequisiteError, match="must not be a symlink"):
        validate_scratch_root(symlink_scratch, ROOT)

    repo_internal = ROOT / "src/test/fixtures"
    with pytest.raises(BrowserHarnessPrerequisiteError, match="strictly outside the repository checkout"):
        validate_scratch_root(repo_internal, ROOT)


def test_node_executable_validation_success_and_refusals(tmp_path: Path) -> None:
    """Validate Node binary identity checks, sha256 digest, and refusal rules."""
    raw_node = os.environ.get("APG_JAVASCRIPT_NODE")
    assert raw_node, "APG_JAVASCRIPT_NODE must be set in test environment"
    direct_node = Path(raw_node)
    assert direct_node.is_file()
    identity = validate_node_executable(direct_node, ROOT)
    assert identity == EXPECTED_NODE_VERSION

    with pytest.raises(BrowserHarnessPrerequisiteError, match="must be absolute"):
        validate_node_executable(Path("node"), ROOT)

    with pytest.raises(BrowserHarnessPrerequisiteError, match="must be an executable file"):
        validate_node_executable(tmp_path / "missing-node", ROOT)

    not_exec = tmp_path / "not_exec.sh"
    not_exec.write_text("#!/bin/sh\n")
    not_exec.chmod(0o644)
    with pytest.raises(BrowserHarnessPrerequisiteError, match="must be an executable file"):
        validate_node_executable(not_exec, ROOT)

    symlink_node = tmp_path / "symlink_node"
    symlink_node.symlink_to(direct_node)
    with pytest.raises(BrowserHarnessPrerequisiteError, match="must not be a symlink"):
        validate_node_executable(symlink_node, ROOT)

    fake_repository = tmp_path / "repository"
    fake_repository.mkdir()
    internal_fake = fake_repository / "fake-node"
    try:
        internal_fake.write_text("#!/bin/sh\n")
        internal_fake.chmod(0o755)
        with pytest.raises(BrowserHarnessPrerequisiteError, match="outside repository checkout"):
            validate_node_executable(internal_fake, fake_repository)
    finally:
        if internal_fake.exists():
            internal_fake.unlink()

    fake_exec = tmp_path / "fake_node"
    fake_exec.write_text("#!/bin/sh\necho test\n")
    fake_exec.chmod(0o755)
    with pytest.raises(BrowserHarnessPrerequisiteError, match="SHA-256 mismatch"):
        validate_node_executable(fake_exec, ROOT)


def test_playwright_package_validation_success_and_refusals(tmp_path: Path) -> None:
    """Validate package root checks and version parity."""
    pkg_dir = tmp_path / "valid_pkg"
    pw_test_dir = pkg_dir / "node_modules" / "@playwright" / "test"
    pw_dir = pkg_dir / "node_modules" / "playwright"
    pw_test_dir.mkdir(parents=True)
    pw_dir.mkdir(parents=True)
    (pw_test_dir / "package.json").write_text(
        json.dumps({"name": "@playwright/test", "version": "1.62.1"}), encoding="utf-8"
    )
    (pw_dir / "package.json").write_text(
        json.dumps({"name": "playwright", "version": "1.62.1"}), encoding="utf-8"
    )

    ver = validate_playwright_package(pkg_dir, ROOT)
    assert ver == "1.62.1"

    bad_pkg = tmp_path / "bad_pkg"
    bad_pkg.mkdir()
    with pytest.raises(BrowserHarnessPrerequisiteError, match="Playwright packages not found"):
        validate_playwright_package(bad_pkg, ROOT)

    mismatch_pkg = tmp_path / "mismatch_pkg"
    mismatch_pw_test = mismatch_pkg / "node_modules" / "@playwright" / "test"
    mismatch_pw = mismatch_pkg / "node_modules" / "playwright"
    mismatch_pw_test.mkdir(parents=True)
    mismatch_pw.mkdir(parents=True)
    (mismatch_pw_test / "package.json").write_text(
        json.dumps({"name": "@playwright/test", "version": "1.50.0"}), encoding="utf-8"
    )
    (mismatch_pw / "package.json").write_text(
        json.dumps({"name": "playwright", "version": "1.50.0"}), encoding="utf-8"
    )
    with pytest.raises(BrowserHarnessPrerequisiteError, match="Playwright version mismatch"):
        validate_playwright_package(mismatch_pkg, ROOT)


def test_browser_cache_validation_success_and_refusals(tmp_path: Path) -> None:
    """Validate cache discovery and detection of missing browsers."""
    cache_dir = tmp_path / "cache"
    (cache_dir / "chromium-1234").mkdir(parents=True)
    (cache_dir / "firefox-1538").mkdir(parents=True)
    (cache_dir / "webkit-2336").mkdir(parents=True)

    found = validate_browser_cache(cache_dir)
    assert set(found.keys()) == {"chromium", "firefox", "webkit"}

    incomplete_cache = tmp_path / "incomplete_cache"
    (incomplete_cache / "chromium-1234").mkdir(parents=True)
    (incomplete_cache / "firefox-1538").mkdir(parents=True)
    with pytest.raises(BrowserHarnessPrerequisiteError, match="Missing browser binaries"):
        validate_browser_cache(incomplete_cache)


def test_missing_environment_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify observe_browser_harness_config fails closed when required environment is missing."""
    monkeypatch.delenv("APG_PLAYWRIGHT_OWNED_SCRATCH_ROOT", raising=False)
    with pytest.raises(BrowserHarnessPrerequisiteError, match="APG_PLAYWRIGHT_OWNED_SCRATCH_ROOT"):
        observe_browser_harness_config(ROOT)


def test_receipt_validation_rules() -> None:
    """Verify evaluation receipt schema, zero-skip, zero-failure, and scenario checks."""
    valid_receipt = {
        "schema_version": "1.0.0",
        "authority": "APG123-BROWSER-UI-QUALIFIED-RECEIPT",
        "package": {"name": "@playwright/test", "version": "1.62.1"},
        "browsers": {"chromium": "151.0", "firefox": "153.0", "webkit": "26.5"},
        "summary": {"total": 3, "passed": 3, "failed": 0, "skipped": 0},
        "scenarios": [
            {
                "scenario_id": "PW01",
                "group": "playwright",
                "browser": "chromium",
                "status": "passed",
                "assertions": [{"name": "unique_locator_success", "passed": True}, {"name": "strict_mode_violation_rejection", "passed": True}],
            },
            {
                "scenario_id": "PW01",
                "group": "playwright",
                "browser": "firefox",
                "status": "passed",
                "assertions": [{"name": "unique_locator_success", "passed": True}, {"name": "strict_mode_violation_rejection", "passed": True}],
            },
            {
                "scenario_id": "PW01",
                "group": "playwright",
                "browser": "webkit",
                "status": "passed",
                "assertions": [{"name": "unique_locator_success", "passed": True}, {"name": "strict_mode_violation_rejection", "passed": True}],
            },
        ],
        "artifacts": ["PW09-chromium-darwin-baseline.png"],
    }

    receipt = validate_receipt(
        valid_receipt,
        expected_browsers=("chromium", "firefox", "webkit"),
        expected_scenarios=("PW01",),
    )
    assert receipt.is_clean_pass
    assert receipt.total_count == 3
    assert receipt.passed_count == 3
    assert receipt.failed_count == 0
    assert receipt.skipped_count == 0
    assert receipt.raw.get("authority") == APG123_BROWSER_UI_AUTHORITY

    # Refusal: missing authority label (missing label)
    missing_auth = dict(valid_receipt)
    del missing_auth["authority"]
    with pytest.raises(BrowserHarnessValidationError, match="Receipt missing authority"):
        validate_receipt(missing_auth, ("chromium", "firefox", "webkit"), ("PW01",))

    # Refusal: empty authority label (missing label)
    empty_auth = dict(valid_receipt, authority="")
    with pytest.raises(BrowserHarnessValidationError, match="Receipt missing authority"):
        validate_receipt(empty_auth, ("chromium", "firefox", "webkit"), ("PW01",))

    # Refusal: APG123 authority incorrectly on runtime scenario (APG123 incorrectly on runtime)
    bad_runtime_auth = dict(
        valid_receipt,
        authority=APG123_BROWSER_UI_AUTHORITY,
        scenarios=[
            {
                "scenario_id": "BR01",
                "group": "browser_runtime",
                "browser": b,
                "status": "passed",
                "assertions": [
                    {"name": "document_readystate_order_verified", "passed": True},
                    {"name": "lifecycle_events_deterministic_order", "passed": True},
                    {"name": "visibility_state_active", "passed": True},
                ],
            }
            for b in ("chromium", "firefox", "webkit")
        ],
    )
    with pytest.raises(BrowserHarnessValidationError, match="Receipt authority mismatch"):
        validate_receipt(bad_runtime_auth, ("chromium", "firefox", "webkit"), ("BR01",))

    # Positive: correct runtime authority on runtime scenario (correct runtime)
    valid_runtime_auth = dict(
        bad_runtime_auth,
        authority=APG125_BROWSER_RUNTIME_AUTHORITY,
    )
    receipt_rt = validate_receipt(valid_runtime_auth, ("chromium", "firefox", "webkit"), ("BR01",))
    assert receipt_rt.is_clean_pass
    assert receipt_rt.raw.get("authority") == APG125_BROWSER_RUNTIME_AUTHORITY

    # Explicitly mixed behavior: positive mixed authority on mixed scenario family
    valid_mixed_receipt = dict(
        valid_receipt,
        authority=APG125_BROWSER_MIXED_AUTHORITY,
        summary={"total": 6, "passed": 6, "failed": 0, "skipped": 0},
        scenarios=valid_receipt["scenarios"] + [
            {
                "scenario_id": "BR01",
                "group": "browser_runtime",
                "browser": b,
                "status": "passed",
                "assertions": [
                    {"name": "document_readystate_order_verified", "passed": True},
                    {"name": "lifecycle_events_deterministic_order", "passed": True},
                    {"name": "visibility_state_active", "passed": True},
                ],
            }
            for b in ("chromium", "firefox", "webkit")
        ],
    )
    receipt_mixed = validate_receipt(valid_mixed_receipt, ("chromium", "firefox", "webkit"), ("PW01", "BR01"))
    assert receipt_mixed.is_clean_pass
    assert receipt_mixed.raw.get("authority") == APG125_BROWSER_MIXED_AUTHORITY

    # Explicitly mixed behavior refusal: APG123 authority rejected on mixed scenario family
    bad_mixed_apg123 = dict(valid_mixed_receipt, authority=APG123_BROWSER_UI_AUTHORITY)
    with pytest.raises(BrowserHarnessValidationError, match="Receipt authority mismatch"):
        validate_receipt(bad_mixed_apg123, ("chromium", "firefox", "webkit"), ("PW01", "BR01"))

    # Explicitly mixed behavior refusal: runtime authority rejected on mixed scenario family
    bad_mixed_runtime = dict(valid_mixed_receipt, authority=APG125_BROWSER_RUNTIME_AUTHORITY)
    with pytest.raises(BrowserHarnessValidationError, match="Receipt authority mismatch"):
        validate_receipt(bad_mixed_runtime, ("chromium", "firefox", "webkit"), ("PW01", "BR01"))

    # Refusal: bad schema version
    bad_schema = dict(valid_receipt, schema_version="2.0.0")
    with pytest.raises(BrowserHarnessValidationError, match="Unsupported receipt schema_version"):
        validate_receipt(bad_schema, ("chromium", "firefox", "webkit"), ("PW01",))

    # Refusal: package mismatch
    bad_pkg = dict(valid_receipt, package={"name": "@playwright/test", "version": "1.50.0"})
    with pytest.raises(BrowserHarnessValidationError, match="Receipt package identity mismatch"):
        validate_receipt(bad_pkg, ("chromium", "firefox", "webkit"), ("PW01",))

    # Refusal: count mismatch
    bad_count = dict(valid_receipt, summary={"total": 2, "passed": 2, "failed": 0, "skipped": 0})
    with pytest.raises(BrowserHarnessValidationError, match="Receipt scenario count mismatch"):
        validate_receipt(bad_count, ("chromium", "firefox", "webkit"), ("PW01",))

    # Refusal: boolean numeric counter
    bad_bool_counter = dict(valid_receipt, summary={"total": True, "passed": 3, "failed": 0, "skipped": 0})
    with pytest.raises(BrowserHarnessValidationError, match="Invalid integer counter"):
        validate_receipt(bad_bool_counter, ("chromium", "firefox", "webkit"), ("PW01",))

    # Refusal: nonzero failed or skipped
    failed_receipt = dict(valid_receipt, summary={"total": 3, "passed": 2, "failed": 1, "skipped": 0})
    with pytest.raises(BrowserHarnessValidationError, match="Incomplete or failed scenario run"):
        validate_receipt(failed_receipt, ("chromium", "firefox", "webkit"), ("PW01",))

    # Refusal: empty filter
    with pytest.raises(BrowserHarnessValidationError, match="Filter expected_browsers and expected_scenarios must not be empty"):
        validate_receipt(valid_receipt, (), ("PW01",))

    # Refusal: duplicate scenario entry
    duplicate_sc = dict(
        valid_receipt,
        scenarios=[
            {
                "scenario_id": "PW01",
                "group": "playwright",
                "browser": "chromium",
                "status": "passed",
                "assertions": [{"name": "a", "passed": True}],
            },
            {
                "scenario_id": "PW01",
                "group": "playwright",
                "browser": "chromium",
                "status": "passed",
                "assertions": [{"name": "a", "passed": True}],
            },
            {
                "scenario_id": "PW01",
                "group": "playwright",
                "browser": "firefox",
                "status": "passed",
                "assertions": [{"name": "a", "passed": True}],
            },
        ]
    )
    with pytest.raises(BrowserHarnessValidationError, match="Duplicate scenario entry"):
        validate_receipt(duplicate_sc, ("chromium", "firefox", "webkit"), ("PW01",))

    # Refusal: unknown scenario ID
    unknown_sc = dict(
        valid_receipt,
        scenarios=[
            {
                "scenario_id": "UNKNOWN_ID",
                "group": "playwright",
                "browser": "chromium",
                "status": "passed",
                "assertions": [{"name": "a", "passed": True}],
            },
            {
                "scenario_id": "PW01",
                "group": "playwright",
                "browser": "firefox",
                "status": "passed",
                "assertions": [{"name": "a", "passed": True}],
            },
            {
                "scenario_id": "PW01",
                "group": "playwright",
                "browser": "webkit",
                "status": "passed",
                "assertions": [{"name": "a", "passed": True}],
            },
        ]
    )
    with pytest.raises(BrowserHarnessValidationError, match="Unknown scenario ID in receipt"):
        validate_receipt(unknown_sc, ("chromium", "firefox", "webkit"), ("PW01",))

    # Refusal: missing scenario group in receipt
    missing_group_sc = dict(
        valid_receipt,
        scenarios=[
            {
                "scenario_id": "PW01",
                "browser": "chromium",
                "status": "passed",
                "assertions": [{"name": "a", "passed": True}],
            },
            {
                "scenario_id": "PW01",
                "group": "playwright",
                "browser": "firefox",
                "status": "passed",
                "assertions": [{"name": "a", "passed": True}],
            },
            {
                "scenario_id": "PW01",
                "group": "playwright",
                "browser": "webkit",
                "status": "passed",
                "assertions": [{"name": "a", "passed": True}],
            },
        ],
    )
    with pytest.raises(BrowserHarnessValidationError, match="recorded group mismatch"):
        validate_receipt(missing_group_sc, ("chromium", "firefox", "webkit"), ("PW01",))

    # Refusal: mismatched scenario group in receipt (pair mismatch)
    mismatched_group_sc = dict(
        valid_receipt,
        scenarios=[
            {
                "scenario_id": "PW01",
                "group": "accessibility",  # Mismatch: PW01 belongs to playwright
                "browser": "chromium",
                "status": "passed",
                "assertions": [{"name": "a", "passed": True}],
            },
            {
                "scenario_id": "PW01",
                "group": "playwright",
                "browser": "firefox",
                "status": "passed",
                "assertions": [{"name": "a", "passed": True}],
            },
            {
                "scenario_id": "PW01",
                "group": "playwright",
                "browser": "webkit",
                "status": "passed",
                "assertions": [{"name": "a", "passed": True}],
            },
        ],
    )
    with pytest.raises(BrowserHarnessValidationError, match="recorded group mismatch"):
        validate_receipt(mismatched_group_sc, ("chromium", "firefox", "webkit"), ("PW01",))

    # Refusal: invalid/empty assertion
    bad_assertion_receipt = dict(
        valid_receipt,
        scenarios=[
            {
                "scenario_id": "PW01",
                "group": "playwright",
                "browser": "chromium",
                "status": "passed",
                "assertions": [],
            },
            {
                "scenario_id": "PW01",
                "group": "playwright",
                "browser": "firefox",
                "status": "passed",
                "assertions": [{"name": "a", "passed": True}],
            },
            {
                "scenario_id": "PW01",
                "group": "playwright",
                "browser": "webkit",
                "status": "passed",
                "assertions": [{"name": "a", "passed": True}],
            },
        ]
    )
    with pytest.raises(BrowserHarnessValidationError, match="has empty assertions"):
        validate_receipt(bad_assertion_receipt, ("chromium", "firefox", "webkit"), ("PW01",))


def test_standalone_runner_missing_custody_refusals() -> None:
    """Verify standalone runner refuses execution when explicit scratch directory is absent."""
    node_bin = os.environ["APG_JAVASCRIPT_NODE"]
    runner_path = os.fspath(FIXTURES_DIR / "runner.mjs")

    # Refusal: omitted --scratch
    res1 = subprocess.run([node_bin, runner_path], capture_output=True, text=True, timeout=10)
    assert res1.returncode != 0
    assert "Explicit --scratch directory is required" in (res1.stdout + res1.stderr)

    # Refusal: empty string --scratch
    res2 = subprocess.run([node_bin, runner_path, "--scratch", ""], capture_output=True, text=True, timeout=10)
    assert res2.returncode != 0
    assert "Explicit --scratch directory is required" in (res2.stdout + res2.stderr)


def test_standalone_runner_unsafe_scratch_refusals(tmp_path: Path) -> None:
    """Verify standalone runner refuses relative, non-existent, symlink, non-0700, or repo paths."""
    node_bin = os.environ["APG_JAVASCRIPT_NODE"]
    runner_path = os.fspath(FIXTURES_DIR / "runner.mjs")

    # Refusal: relative scratch
    res_rel = subprocess.run(
        [node_bin, runner_path, "--scratch", "relative/scratch"],
        capture_output=True, text=True, timeout=10,
    )
    assert res_rel.returncode != 0
    assert "must be an absolute path" in (res_rel.stdout + res_rel.stderr)

    # Refusal: non-existent scratch
    res_missing = subprocess.run(
        [node_bin, runner_path, "--scratch", os.fspath(tmp_path / "nonexistent-dir")],
        capture_output=True, text=True, timeout=10,
    )
    assert res_missing.returncode != 0
    assert "does not exist" in (res_missing.stdout + res_missing.stderr)

    # Refusal: symlink scratch
    real_dir = tmp_path / "real-scratch"
    real_dir.mkdir(mode=0o700)
    real_dir.chmod(0o700)
    symlink_dir = tmp_path / "symlink-scratch"
    symlink_dir.symlink_to(real_dir, target_is_directory=True)

    res_sym = subprocess.run(
        [node_bin, runner_path, "--scratch", os.fspath(symlink_dir)],
        capture_output=True, text=True, timeout=10,
    )
    assert res_sym.returncode != 0
    assert "must not be a symlink" in (res_sym.stdout + res_sym.stderr) or "contains symlinks" in (res_sym.stdout + res_sym.stderr)

    # Refusal: non-0700 mode (e.g. 0755)
    bad_mode = tmp_path / "mode-755-scratch"
    bad_mode.mkdir(mode=0o755)
    bad_mode.chmod(0o755)
    res_mode = subprocess.run(
        [node_bin, runner_path, "--scratch", os.fspath(bad_mode)],
        capture_output=True, text=True, timeout=10,
    )
    assert res_mode.returncode != 0
    assert "must be mode 0700" in (res_mode.stdout + res_mode.stderr)

    # Refusal: scratch inside repository checkout
    repo_internal = ROOT / "tmp_repo_scratch_test"
    repo_internal.mkdir(mode=0o700)
    try:
        res_repo = subprocess.run(
            [node_bin, runner_path, "--scratch", os.fspath(repo_internal)],
            capture_output=True, text=True, timeout=10,
        )
        assert res_repo.returncode != 0
        assert "strictly outside repository checkout" in (res_repo.stdout + res_repo.stderr)
    finally:
        if repo_internal.exists():
            repo_internal.rmdir()


def test_standalone_runner_escaping_destinations_refusals(tmp_path: Path) -> None:
    """Verify standalone runner rejects escaping or symlinked receipt and artifact paths."""
    node_bin = os.environ["APG_JAVASCRIPT_NODE"]
    runner_path = os.fspath(FIXTURES_DIR / "runner.mjs")

    valid_scratch = tmp_path / "valid-custody-scratch"
    valid_scratch.mkdir(mode=0o700)
    valid_scratch.chmod(0o700)

    # Refusal: escaping receipt path (absolute outside scratch)
    res_rec_abs = subprocess.run(
        [node_bin, runner_path, "--scratch", os.fspath(valid_scratch), "--receipt", "/tmp/escape-receipt.json"],
        capture_output=True, text=True, timeout=10,
    )
    assert res_rec_abs.returncode != 0
    assert "Receipt destination escapes scratch directory" in (res_rec_abs.stdout + res_rec_abs.stderr)

    # Refusal: escaping receipt path (relative .. outside scratch)
    res_rec_rel = subprocess.run(
        [node_bin, runner_path, "--scratch", os.fspath(valid_scratch), "--receipt", os.fspath(valid_scratch / "../escape.json")],
        capture_output=True, text=True, timeout=10,
    )
    assert res_rec_rel.returncode != 0
    assert "Receipt destination escapes scratch directory" in (res_rec_rel.stdout + res_rec_rel.stderr)

    # Refusal: symlink receipt destination
    sym_receipt = valid_scratch / "symlink-receipt.json"
    target_file = tmp_path / "target.json"
    target_file.write_text("{}")
    sym_receipt.symlink_to(target_file)
    res_rec_sym = subprocess.run(
        [node_bin, runner_path, "--scratch", os.fspath(valid_scratch), "--receipt", os.fspath(sym_receipt)],
        capture_output=True, text=True, timeout=10,
    )
    assert res_rec_sym.returncode != 0
    assert "path contains symlink" in (res_rec_sym.stdout + res_rec_sym.stderr)

    # Refusal: escaping artifacts path
    res_art_abs = subprocess.run(
        [node_bin, runner_path, "--scratch", os.fspath(valid_scratch), "--artifacts", "/tmp/outside-artifacts"],
        capture_output=True, text=True, timeout=10,
    )
    assert res_art_abs.returncode != 0
    assert "Artifacts destination escapes scratch directory" in (res_art_abs.stdout + res_art_abs.stderr)

    # Refusal: symlink artifacts directory
    sym_art = valid_scratch / "symlink-artifacts"
    target_dir = tmp_path / "target_artifacts"
    target_dir.mkdir(mode=0o700)
    sym_art.symlink_to(target_dir, target_is_directory=True)
    res_art_sym = subprocess.run(
        [node_bin, runner_path, "--scratch", os.fspath(valid_scratch), "--artifacts", os.fspath(sym_art)],
        capture_output=True, text=True, timeout=10,
    )
    assert res_art_sym.returncode != 0
    assert "path contains symlink" in (res_art_sym.stdout + res_art_sym.stderr)


def test_standalone_runner_valid_custody(tmp_path: Path) -> None:
    """Verify valid mode 0700 external scratch passes custody checks before browser use."""
    node_bin = os.environ["APG_JAVASCRIPT_NODE"]
    valid_scratch = tmp_path / "valid-pass-scratch"
    valid_scratch.mkdir(mode=0o700)
    valid_scratch.chmod(0o700)

    script = (
        "import { validateRunnerCustody } from "
        + json.dumps((FIXTURES_DIR / "runner.mjs").as_uri())
        + "; const res = validateRunnerCustody(['--scratch', process.argv[1]]); "
        + "console.log(JSON.stringify(res));"
    )
    res = subprocess.run(
        [node_bin, "--input-type=module", "-e", script, os.fspath(valid_scratch)],
        capture_output=True, text=True, timeout=10,
    )
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout.strip())
    assert data["scratchDir"] == os.fspath(valid_scratch.resolve())
    assert data["receiptPath"] == os.fspath(valid_scratch.resolve() / "receipt.json")
    assert data["artifactsDir"] == os.fspath(valid_scratch.resolve() / "artifacts")


def test_validate_scratch_root_private_mode_and_ownership(tmp_path: Path) -> None:
    """Verify validate_scratch_root enforces mode 0700 and ownership when private=True."""
    valid_scratch = tmp_path / "valid-priv-scratch"
    valid_scratch.mkdir(mode=0o700)
    valid_scratch.chmod(0o700)
    validated = validate_scratch_root(valid_scratch, ROOT, private=True)
    assert validated == valid_scratch.resolve()

    bad_mode = tmp_path / "bad-priv-scratch"
    bad_mode.mkdir(mode=0o755)
    bad_mode.chmod(0o755)
    with pytest.raises(BrowserHarnessPrerequisiteError, match="must be mode 0700"):
        validate_scratch_root(bad_mode, ROOT, private=True)


def test_sanitize_evidence_text_redaction_and_bounding(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Verify sanitize_evidence_text redacts home and scratch roots and bounds length."""
    home_dir = "/" + "Users/dummy-operator"
    scratch_dir = "/synthetic/scratch/dummy-run"
    monkeypatch.setenv("HOME", home_dir)
    monkeypatch.setenv("APG_PLAYWRIGHT_OWNED_SCRATCH_ROOT", scratch_dir)

    raw = f"Error at {home_dir}/file.js in {scratch_dir}/subpath: test failure"
    sanitized = sanitize_evidence_text(raw)
    assert home_dir not in sanitized
    assert scratch_dir not in sanitized
    assert "<HOME>" in sanitized
    assert "<SCRATCH_ROOT>" in sanitized

    long_str = "x" * 3000
    bounded = sanitize_evidence_text(long_str, max_len=2000)
    assert len(bounded) < 2050
    assert bounded.endswith("...[truncated]")


def test_supervisor_failure_diagnostic_survival_strictness_and_cancellation(tmp_path: Path) -> None:
    """Verify supervisor retains sanitized failure evidence with preserved class/message before cleanup."""
    fake_scratch = tmp_path / "fake-scratch"
    fake_scratch.mkdir(mode=0o700)
    fake_scratch.chmod(0o700)

    config = BrowserHarnessConfig(
        repo_root=ROOT,
        scratch_root=fake_scratch,
        node_executable=Path(os.environ["APG_JAVASCRIPT_NODE"]),
        node_identity=EXPECTED_NODE_VERSION,
        package_root=tmp_path / "fake-pkg",
        package_version=EXPECTED_PLAYWRIGHT_VERSION,
        browsers_path=tmp_path / "fake-browsers",
    )

    # 1. Simulate strictness failure
    fixtures_strict = tmp_path / "fixtures-strict"
    fixtures_strict.mkdir(mode=0o700)
    (fixtures_strict / "scenarios.json").write_text((FIXTURES_DIR / "scenarios.json").read_text(encoding="utf-8"), encoding="utf-8")
    (fixtures_strict / "family_table.json").write_text((FIXTURES_DIR / "family_table.json").read_text(encoding="utf-8"), encoding="utf-8")
    strict_receipt = {
        "schema_version": "1.0.0",
        "authority": "APG123-BROWSER-UI-QUALIFIED-RECEIPT",
        "summary": {"total": 1, "passed": 0, "failed": 1, "skipped": 0},
        "scenarios": [
            {
                "scenario_id": "PW01",
                "group": "playwright",
                "browser": "chromium",
                "status": "failed",
                "error": "strict mode violation: locator('.dup-btn') resolved to 2 elements",
                "error_details": {
                    "class": "Error",
                    "message": "strict mode violation: locator('.dup-btn') resolved to 2 elements",
                    "cause": None,
                },
            }
        ],
    }
    fake_strict_runner = fixtures_strict / "runner.mjs"
    fake_strict_runner.write_text(
        "import fs from 'node:fs';\n"
        "const args = process.argv.slice(2);\n"
        "const rec = args[args.indexOf('--receipt') + 1];\n"
        f"fs.writeFileSync(rec, JSON.stringify({json.dumps(strict_receipt)}), 'utf-8');\n"
        "console.error('Runner fatal error: ' + JSON.stringify({class: 'Error', message: 'strict mode violation'}));\n"
        "process.exit(1);\n"
    )

    with pytest.raises(BrowserHarnessExecutionError) as exc_strict:
        execute_browser_harness(
            config,
            fixtures_strict,
            browsers=("chromium",),
            scenario_filter=("PW01",),
        )

    # Verify diagnostic survival
    err_strict = exc_strict.value
    assert err_strict.original_class == "Error"
    assert "strict mode violation" in str(err_strict.original_message)
    assert err_strict.retained_path is not None
    assert err_strict.retained_path.is_file()
    assert err_strict.failure_evidence is not None
    assert err_strict.failure_evidence["error_class"] == "Error"
    assert "strict mode violation" in err_strict.failure_evidence["error_message"]

    # Verify supervisor cleaned up run directory
    remaining_runs = [p for p in fake_scratch.iterdir() if p.is_dir() and p.name.startswith("run-")]
    assert len(remaining_runs) == 0, "run directory must be deleted during supervisor cleanup"

    # 2. Simulate cancellation failure
    fixtures_cancel = tmp_path / "fixtures-cancel"
    fixtures_cancel.mkdir(mode=0o700)
    (fixtures_cancel / "scenarios.json").write_text((FIXTURES_DIR / "scenarios.json").read_text(encoding="utf-8"), encoding="utf-8")
    (fixtures_cancel / "family_table.json").write_text((FIXTURES_DIR / "family_table.json").read_text(encoding="utf-8"), encoding="utf-8")
    cancel_receipt = {
        "schema_version": "1.0.0",
        "authority": "APG123-BROWSER-UI-QUALIFIED-RECEIPT",
        "summary": {"total": 1, "passed": 0, "failed": 1, "skipped": 0},
        "scenarios": [
            {
                "scenario_id": "PW05",
                "group": "playwright",
                "browser": "chromium",
                "status": "failed",
                "error": "locator.click: Test Operation Cancelled",
                "error_details": {
                    "class": "AbortError",
                    "message": "locator.click: Test Operation Cancelled",
                    "cause": "AbortController.signal cancellation",
                },
            }
        ],
    }
    fake_cancel_runner = fixtures_cancel / "runner.mjs"
    fake_cancel_runner.write_text(
        "import fs from 'node:fs';\n"
        "const args = process.argv.slice(2);\n"
        "const rec = args[args.indexOf('--receipt') + 1];\n"
        f"fs.writeFileSync(rec, JSON.stringify({json.dumps(cancel_receipt)}), 'utf-8');\n"
        "console.error('Runner fatal error: ' + JSON.stringify({class: 'AbortError', message: 'Test Operation Cancelled', cause: 'AbortController.signal cancellation'}));\n"
        "process.exit(1);\n"
    )

    with pytest.raises(BrowserHarnessExecutionError) as exc_cancel:
        execute_browser_harness(
            config,
            fixtures_cancel,
            browsers=("chromium",),
            scenario_filter=("PW05",),
        )

    err_cancel = exc_cancel.value
    assert err_cancel.original_class == "AbortError"
    assert "Test Operation Cancelled" in str(err_cancel.original_message)
    assert err_cancel.bounded_cause == "AbortController.signal cancellation"
    assert err_cancel.retained_path is not None
    assert err_cancel.retained_path.is_file()

    # Verify cleanup of retained failure evidence with exact run_id
    removed_strict = cleanup_retained_failure_evidence(fake_scratch, run_id=err_strict.failure_evidence["run_id"])
    assert removed_strict == 1
    assert not err_strict.retained_path.exists()

    removed_cancel = cleanup_retained_failure_evidence(fake_scratch, run_id=err_cancel.failure_evidence["run_id"])
    assert removed_cancel == 1
    assert not err_cancel.retained_path.exists()
    assert not (fake_scratch / "evidence").exists()

    # Verify refusal on invalid or empty run_id
    with pytest.raises(BrowserHarnessPrerequisiteError, match="run_id must be a non-empty string"):
        cleanup_retained_failure_evidence(fake_scratch, "")
    with pytest.raises(BrowserHarnessPrerequisiteError, match="Invalid run_id"):
        cleanup_retained_failure_evidence(fake_scratch, "../escape")


def test_runner_mjs_writes_failure_receipt_before_throwing(tmp_path: Path) -> None:
    """Verify runner.mjs writeReceiptFile writes valid JSON receipt even on scenario failure."""
    node_bin = os.environ["APG_JAVASCRIPT_NODE"]
    receipt_file = tmp_path / "failure_receipt.json"

    script = (
        "import { writeReceiptFile } from "
        + json.dumps((FIXTURES_DIR / "runner.mjs").as_uri())
        + "; "
        + "const scenarios = [{"
        + "  scenario_id: 'PW01', group: 'playwright', browser: 'chromium', status: 'failed',"
        + "  duration_ms: 12, assertions: [], artifacts: [],"
        + "  error: 'strict mode violation', error_details: { class: 'Error', message: 'strict mode violation', cause: null }"
        + "}];"
        + "writeReceiptFile(process.argv[1], scenarios, { chromium: '151.0' }, Date.now() - 100, null, [], null);"
    )
    res = subprocess.run([node_bin, "--input-type=module", "-e", script, os.fspath(receipt_file)], capture_output=True, text=True, timeout=10)
    assert res.returncode == 0, res.stderr
    assert receipt_file.is_file()
    data = json.loads(receipt_file.read_text(encoding="utf-8"))
    assert data["summary"]["failed"] == 1
    assert data["summary"]["passed"] == 0
    assert data["scenarios"][0]["error_details"]["class"] == "Error"
    assert data["scenarios"][0]["error_details"]["message"] == "strict mode violation"


def test_runner_cause_cycle_and_depth_bounding() -> None:
    """Verify runner.mjs sanitizeCause and sanitizeError bound depth and handle cycles without throwing."""
    node_bin = os.environ["APG_JAVASCRIPT_NODE"]

    script = (
        "import { sanitizeCause, sanitizeError } from "
        + json.dumps((FIXTURES_DIR / "runner.mjs").as_uri())
        + "; "
        + "const selfErr = new Error('self cyclic');"
        + "selfErr.cause = selfErr;"
        + "const resSelf = sanitizeError(selfErr);"
        + "if (resSelf.cause !== '[Circular]') process.exit(2);"
        + "const errA = new Error('error A');"
        + "const errB = new Error('error B');"
        + "errA.cause = errB;"
        + "errB.cause = errA;"
        + "const resMutual = sanitizeError(errA);"
        + "if (!resMutual.cause || resMutual.cause.cause !== '[Circular]') process.exit(3);"
        + "let root = new Error('level 0');"
        + "let curr = root;"
        + "for (let i = 1; i <= 10; i++) { curr.cause = new Error('level ' + i); curr = curr.cause; }"
        + "const resDeep = sanitizeError(root);"
        + "let depth = 0; let c = resDeep.cause; while (c && typeof c === 'object') { depth++; c = c.cause; }"
        + "if (c !== '[MaxCauseDepthExceeded]') process.exit(4);"
        + "console.log(JSON.stringify({ self: resSelf, mutual: resMutual, depthBound: c }));"
    )
    res = subprocess.run([node_bin, "--input-type=module", "-e", script], capture_output=True, text=True, timeout=10)
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout.strip())
    assert data["self"]["cause"] == "[Circular]"
    assert data["self"]["class"] == "Error"
    assert data["self"]["message"] == "self cyclic"
    assert data["mutual"]["cause"]["cause"] == "[Circular]"
    assert data["depthBound"] == "[MaxCauseDepthExceeded]"


def test_evidence_nested_credential_redaction(tmp_path: Path) -> None:
    """Verify credentials and URL userinfo are redacted in strings and nested receipts."""
    # 1. String-level redactions
    sample_text = (
        "Failed connecting to https://admin:supersecret123@api.internal.org/v1/auth "
        "with token=\"bearer-token-abc\" and password: 'my-password-456' "
        "and auth_token=raw_secret_789 and Bearer secret_bearer_jwt."
    )
    sanitized = sanitize_evidence_text(sample_text)
    assert "supersecret123" not in sanitized
    assert "bearer-token-abc" not in sanitized
    assert "my-password-456" not in sanitized
    assert "raw_secret_789" not in sanitized
    assert "secret_bearer_jwt" not in sanitized
    assert "https://<REDACTED>@api.internal.org" in sanitized
    assert 'token="<REDACTED>"' in sanitized
    assert "password: '<REDACTED>'" in sanitized
    assert "auth_token=<REDACTED>" in sanitized
    assert "Bearer <REDACTED>" in sanitized

    # 2. Retain failure evidence nested receipt sanitization
    fake_scratch = tmp_path / "fake-scratch"
    fake_scratch.mkdir(mode=0o700)
    fake_scratch.chmod(0o700)

    config = BrowserHarnessConfig(
        repo_root=ROOT,
        scratch_root=fake_scratch,
        node_executable=Path(os.environ["APG_JAVASCRIPT_NODE"]),
        node_identity=EXPECTED_NODE_VERSION,
        package_root=tmp_path / "fake-pkg",
        package_version=EXPECTED_PLAYWRIGHT_VERSION,
        browsers_path=tmp_path / "fake-browsers",
    )

    receipt_file = fake_scratch / "secret_receipt.json"
    nested_receipt = {
        "schema_version": "1.0.0",
        "authority": "APG123-BROWSER-UI-QUALIFIED-RECEIPT",
        "scenarios": [
            {
                "scenario_id": "PW01",
                "browser": "chromium",
                "status": "failed",
                "error": "Error at http://user:pass123@host:8000/ with token=leak_token",
                "error_details": {
                    "class": "Error",
                    "message": 'credentials leaked: password="leak_pass"',
                    "cause": "nested Bearer leak_bearer_val",
                },
                "nested_data": {
                    "api_key": "raw_secret_key",
                },
            }
        ],
    }
    receipt_file.write_text(json.dumps(nested_receipt), encoding="utf-8")

    evidence, retained_path = retain_failure_evidence(
        config=config,
        run_id="run-secret-test",
        receipt_file=receipt_file,
        returncode=1,
        stdout='stdout line token="stdout_tok"',
        stderr="stderr line password='stderr_pass'",
        error_msg="failed",
    )

    retained_text = retained_path.read_text(encoding="utf-8")
    for secret in ("pass123", "leak_token", "leak_pass", "leak_bearer_val", "stdout_tok", "stderr_pass", "raw_secret_key"):
        assert secret not in retained_text, f"Secret {secret} found unredacted in retained failure evidence"
        assert secret not in str(evidence), f"Secret {secret} found unredacted in returned failure evidence"

    assert "<REDACTED>" in retained_text
    assert evidence["error_class"] == "Error"


def test_runner_dangling_symlink_refusal(tmp_path: Path) -> None:
    """Verify runner.mjs rejects dangling symlinks for receipt and artifact paths."""
    node_bin = os.environ["APG_JAVASCRIPT_NODE"]
    runner_path = os.fspath(FIXTURES_DIR / "runner.mjs")

    valid_scratch = tmp_path / "scratch"
    valid_scratch.mkdir(mode=0o700)
    valid_scratch.chmod(0o700)

    # 1. Dangling receipt symlink
    dangling_receipt = valid_scratch / "dangling-receipt.json"
    dangling_receipt.symlink_to(valid_scratch / "nonexistent-target.json")

    res_rec = subprocess.run(
        [node_bin, runner_path, "--scratch", os.fspath(valid_scratch), "--receipt", os.fspath(dangling_receipt)],
        capture_output=True, text=True, timeout=10,
    )
    assert res_rec.returncode != 0
    assert "path contains symlink" in (res_rec.stdout + res_rec.stderr)

    # 2. Dangling artifacts symlink
    dangling_artifacts = valid_scratch / "dangling-artifacts"
    dangling_artifacts.symlink_to(valid_scratch / "nonexistent-artifacts-dir")

    res_art = subprocess.run(
        [node_bin, runner_path, "--scratch", os.fspath(valid_scratch), "--artifacts", os.fspath(dangling_artifacts)],
        capture_output=True, text=True, timeout=10,
    )
    assert res_art.returncode != 0
    assert "path contains symlink" in (res_art.stdout + res_art.stderr)


def test_diagnostic_survives_cleanup_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Verify original diagnostic is never destroyed if cleanup or evidence retention fails."""
    fake_scratch = tmp_path / "fake-scratch"
    fake_scratch.mkdir(mode=0o700)
    fake_scratch.chmod(0o700)

    config = BrowserHarnessConfig(
        repo_root=ROOT,
        scratch_root=fake_scratch,
        node_executable=Path(os.environ["APG_JAVASCRIPT_NODE"]),
        node_identity=EXPECTED_NODE_VERSION,
        package_root=tmp_path / "fake-pkg",
        package_version=EXPECTED_PLAYWRIGHT_VERSION,
        browsers_path=tmp_path / "fake-browsers",
    )

    fixtures_fail = tmp_path / "fixtures-fail"
    fixtures_fail.mkdir(mode=0o700)
    (fixtures_fail / "scenarios.json").write_text((FIXTURES_DIR / "scenarios.json").read_text(encoding="utf-8"), encoding="utf-8")
    (fixtures_fail / "family_table.json").write_text((FIXTURES_DIR / "family_table.json").read_text(encoding="utf-8"), encoding="utf-8")
    fail_receipt = {
        "schema_version": "1.0.0",
        "authority": "APG123-BROWSER-UI-QUALIFIED-RECEIPT",
        "summary": {"total": 1, "passed": 0, "failed": 1, "skipped": 0},
        "scenarios": [
            {
                "scenario_id": "PW01",
                "group": "playwright",
                "browser": "chromium",
                "status": "failed",
                "error": "Initial diagnostic message: element not found",
                "error_details": {
                    "class": "CustomElementNotFoundError",
                    "message": "Initial diagnostic message: element not found",
                    "cause": "Underlying DOM timeout",
                },
            }
        ],
    }
    fake_runner = fixtures_fail / "runner.mjs"
    fake_runner.write_text(
        "import fs from 'node:fs';\n"
        "const args = process.argv.slice(2);\n"
        "const rec = args[args.indexOf('--receipt') + 1];\n"
        f"fs.writeFileSync(rec, JSON.stringify({json.dumps(fail_receipt)}), 'utf-8');\n"
        "console.error('Runner fatal error: ' + JSON.stringify({class: 'CustomElementNotFoundError', message: 'Initial diagnostic message: element not found'}));\n"
        "process.exit(1);\n"
    )

    import shutil
    def failing_rmtree(path, *args, **kwargs):
        raise OSError("Simulated hardware disk I/O cleanup failure")

    monkeypatch.setattr(shutil, "rmtree", failing_rmtree)

    with pytest.raises(BrowserHarnessExecutionError) as exc_info:
        execute_browser_harness(
            config,
            fixtures_fail,
            browsers=("chromium",),
            scenario_filter=("PW01",),
        )

    err = exc_info.value
    assert err.original_class == "CustomElementNotFoundError"
    assert "Initial diagnostic message: element not found" in str(err.original_message)
    assert err.bounded_cause == "Underlying DOM timeout"


def test_extract_observed_request_sanitizes_credentials_and_bounds_metadata() -> None:
    """Verify extractObservedRequest in runner.mjs sanitizes credentials and preserves bounded metadata."""
    node_bin = os.environ["APG_JAVASCRIPT_NODE"]
    script = (
        "import { extractObservedRequest } from "
        + json.dumps((FIXTURES_DIR / "runner.mjs").as_uri())
        + ";\n"
        + "const mockReq = {\n"
        + "  url: '/cors-preflight-allow?secret_token=supersecret123&user=admin',\n"
        + "  method: 'OPTIONS',\n"
        + "  headers: {\n"
        + "    origin: 'http://127.0.0.1:8080',\n"
        + "    'access-control-request-method': 'PUT',\n"
        + "    'access-control-request-headers': 'Content-Type, X-Sensitive-Header',\n"
        + "    cookie: 'session_id=ultra_secret_cookie; apg_auth_cred=synthetic_token_125',\n"
        + "    authorization: 'Bearer secret_bearer_token',\n"
        + "    'x-sensitive-header': 'classified_secret',\n"
        + "  },\n"
        + "};\n"
        + "const res1 = extractObservedRequest(mockReq, 'http://127.0.0.1:8080');\n"
        + "const res2 = extractObservedRequest(mockReq, 'http://127.0.0.1:9090');\n"
        + "const mockNoSynthetic = {\n"
        + "  url: '/test',\n"
        + "  method: 'GET',\n"
        + "  headers: { cookie: 'session_id=123' },\n"
        + "};\n"
        + "const res3 = extractObservedRequest(mockNoSynthetic, null);\n"
        + "console.log(JSON.stringify({ res1, res2, res3 }));\n"
    )
    proc = subprocess.run([node_bin, "--input-type=module", "-e", script], capture_output=True, text=True, timeout=10)
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout.strip())

    res1 = data["res1"]
    assert res1["path"] == "/cors-preflight-allow"
    assert res1["method"] == "OPTIONS"
    assert res1["originMatch"] is True
    assert res1["preflightMethod"] == "PUT"
    assert res1["preflightHeaders"] == ["content-type", "x-sensitive-header"]
    assert "access-control-request-headers" in res1["headerNames"]
    assert "authorization" in res1["headerNames"]
    assert "cookie" in res1["headerNames"]
    assert res1["hasSyntheticCookie"] is True
    assert isinstance(res1["timestamp"], int) and res1["timestamp"] > 0

    # Ensure sensitive strings are completely absent
    serialized = json.dumps(res1)
    for secret in ("supersecret123", "ultra_secret_cookie", "secret_bearer_token", "classified_secret", "admin"):
        assert secret not in serialized, f"Found secret '{secret}' in extracted request: {serialized}"

    # Origin mismatch
    res2 = data["res2"]
    assert res2["originMatch"] is False

    # No synthetic cookie
    res3 = data["res3"]
    assert res3["hasSyntheticCookie"] is False
    assert res3["path"] == "/test"
    assert res3["method"] == "GET"


def test_write_receipt_file_runner_sha256_binding(tmp_path: Path) -> None:
    """Verify writeReceiptFile binds the runner_sha256 digest of runner.mjs and browser environments."""
    import hashlib
    node_bin = os.environ["APG_JAVASCRIPT_NODE"]
    receipt_file = tmp_path / "test_receipt.json"

    expected_sha256 = hashlib.sha256((FIXTURES_DIR / "runner.mjs").read_bytes()).hexdigest()

    script = (
        "import { writeReceiptFile } from "
        + json.dumps((FIXTURES_DIR / "runner.mjs").as_uri())
        + ";\n"
        + "const scenarios = [{\n"
        + "  scenario_id: 'BR01', group: 'browser_runtime', browser: 'chromium', status: 'passed',\n"
        + "  duration_ms: 50, assertions: [{ name: 'test_assert', passed: true }], artifacts: []\n"
        + "}];\n"
        + "const browserVersions = { chromium: '151.0' };\n"
        + "const browserEnvironments = {\n"
        + "  chromium: {\n"
        + "    engine: 'chromium',\n"
        + "    version: '151.0',\n"
        + "    platform: 'darwin',\n"
        + "    arch: 'arm64',\n"
        + "    os_release: '23.6.0',\n"
        + "    origin_role: 'primary',\n"
        + "    window_origin_role: 'primary',\n"
        + "    window_origin: 'http://127.0.0.1:8000',\n"
        + "    headless: true,\n"
        + "    features: { customElements: true, shadowDOM: true, Worker: true }\n"
        + "  }\n"
        + "};\n"
        + "writeReceiptFile(process.argv[1], scenarios, browserVersions, Date.now() - 500, null, [], null, browserEnvironments);\n"
    )
    proc = subprocess.run([node_bin, "--input-type=module", "-e", script, os.fspath(receipt_file)], capture_output=True, text=True, timeout=10)
    assert proc.returncode == 0, proc.stderr
    assert receipt_file.is_file()

    receipt_data = json.loads(receipt_file.read_text(encoding="utf-8"))
    assert receipt_data["runtime"]["runner_sha256"] == expected_sha256
    assert receipt_data["summary"]["passed"] == 1
    assert receipt_data["summary"]["failed"] == 0
    chromium_env = receipt_data["browser_environments"]["chromium"]
    assert chromium_env["origin_role"] == "primary"
    assert chromium_env["window_origin_role"] == "primary"
    assert chromium_env["arch"] == "arm64"
    assert chromium_env["features"]["Worker"] is True


@pytest.mark.parametrize("env_var", [
    "APG_PLAYWRIGHT_OWNED_SCRATCH_ROOT",
    "APG_JAVASCRIPT_NODE",
    "APG_PLAYWRIGHT_PACKAGE_ROOT",
    "PLAYWRIGHT_BROWSERS_PATH",
])
def test_observe_browser_harness_config_missing_env_fails_closed(monkeypatch: pytest.MonkeyPatch, env_var: str) -> None:
    """Verify observe_browser_harness_config fails closed with PrerequisiteError for each required environment variable."""
    monkeypatch.delenv(env_var, raising=False)
    with pytest.raises(BrowserHarnessPrerequisiteError, match=env_var):
        observe_browser_harness_config(ROOT)


def test_runner_server_cleanup_preserves_failure_and_drains_resources() -> None:
    """Exercise the actual cleanup owner with real and failing acquired servers."""
    script = (
        "import { startServer, closeServers } from "
        + json.dumps((FIXTURES_DIR / "runner.mjs").as_uri())
        + ";\n"
        + "const {server} = await startServer();\n"
        + "const initiating = new Error('primary failure');\n"
        + "const cleanup = new Error('Authorization=fixture-secret');\n"
        + "const broken = {close(callback) { callback(cleanup); }};\n"
        + "await closeServers([server, null, broken], initiating);\n"
        + "await closeServers([]);\n"
        + "let standalonePreserved = false;\n"
        + "try { await closeServers([broken]); } catch (error) { standalonePreserved = error === cleanup; }\n"
        + "console.log(JSON.stringify({closed: !server.listening, standalonePreserved}));\n"
    )
    proc = subprocess.run(
        [os.environ["APG_JAVASCRIPT_NODE"], "--input-type=module", "-e", script],
        capture_output=True, text=True, timeout=10,
    )
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout) == {"closed": True, "standalonePreserved": True}
    assert "fixture-secret" not in proc.stderr
    assert "<REDACTED>" in proc.stderr


def test_family_table_structure_and_constants() -> None:
    """Verify family table constants, schema version, authority, aliases, and 38 entries."""
    assert FAMILY_TABLE_SCHEMA_VERSION == "1.0.0"
    assert FAMILY_TABLE_AUTHORITY == "APG129-BROWSER-FAMILY-TABLE"

    table = load_family_table(FIXTURES_DIR)
    assert table["schema_version"] == "1.0.0"
    assert table["authority"] == "APG129-BROWSER-FAMILY-TABLE"
    assert len(table["entries"]) == 38

    # Families is a list of family rows
    assert isinstance(table["families"], list)
    fam_ids = [f["id"] for f in table["families"]]
    assert fam_ids == ["apg123", "apg125"]

    # All 38 frozen identities present
    entry_ids = [e["id"] for e in table["entries"]]
    assert entry_ids == list(ALL_SCENARIOS)

    # 7 subset CLI aliases present
    aliases = table.get("aliases", {})
    for alias_name in ("all", "apg123", "browser_runtime", "browser-runtime", "playwright", "accessibility", "svg"):
        assert alias_name in aliases, f"Missing CLI alias: {alias_name}"
    assert aliases["all"] == list(ALL_SCENARIOS)
    assert aliases["apg123"] == list(APG123_SCENARIOS)
    assert aliases["browser_runtime"] == list(BROWSER_RUNTIME_SCENARIOS)
    assert aliases["browser-runtime"] == list(BROWSER_RUNTIME_SCENARIOS)
    assert aliases["playwright"] == list(PLAYWRIGHT_SCENARIOS)
    assert aliases["accessibility"] == list(ACCESSIBILITY_SCENARIOS)
    assert aliases["svg"] == list(SVG_SCENARIOS)

    # Validates without error
    validated = validate_family_table(table)
    assert validated["authority"] == FAMILY_TABLE_AUTHORITY


def test_family_table_schema_version_fail_closed_python() -> None:
    """Category 1 (Python): Unsupported family table schema version fails closed."""
    table = load_family_table(FIXTURES_DIR)
    bad_schema = dict(table, schema_version="2.0.0")
    with pytest.raises(BrowserHarnessValidationError, match="Unsupported family table schema_version"):
        validate_family_table(bad_schema)


def test_family_table_duplicates_fail_closed_python() -> None:
    """Category 2 (Python): Duplicate family, entry, mix, or alias registrations fail closed."""
    table = load_family_table(FIXTURES_DIR)

    # Duplicate family in families
    bad_families = dict(table, families=table["families"] + [table["families"][0]])
    with pytest.raises(BrowserHarnessValidationError, match="Duplicate family registration in family table: apg123"):
        validate_family_table(bad_families)

    # Duplicate scenario ID in entries
    bad_entries = dict(table, entries=table["entries"] + [{"id": "PW01", "group": "playwright", "family": "apg123"}])
    with pytest.raises(BrowserHarnessValidationError, match="Duplicate scenario ID in family table: PW01"):
        validate_family_table(bad_entries)

    # Duplicate mix in supported_mixes
    bad_mixes = dict(table, supported_mixes=table["supported_mixes"] + [table["supported_mixes"][0]])
    with pytest.raises(BrowserHarnessValidationError, match="Duplicate mix registration in family table"):
        validate_family_table(bad_mixes)

    # Duplicate scenario ID in aliases
    bad_aliases = dict(table, aliases=dict(table["aliases"], playwright=table["aliases"]["playwright"] + ["PW01"]))
    with pytest.raises(BrowserHarnessValidationError, match="Duplicate scenario ID in alias playwright: PW01"):
        validate_family_table(bad_aliases)


def test_family_table_singleton_mix_ambiguity_fail_closed_python() -> None:
    """Category 3 (Python): Singleton mix in supported_mixes causes ambiguity and fails closed."""
    table = load_family_table(FIXTURES_DIR)

    bad_singleton_mix = dict(
        table,
        supported_mixes=[{"families": ["apg123"], "authority": "APG123-BROWSER-UI-QUALIFIED-RECEIPT"}],
    )
    with pytest.raises(BrowserHarnessValidationError, match="singleton mix for family 'apg123'"):
        validate_family_table(bad_singleton_mix)


def test_family_table_unknown_members_fail_closed_python() -> None:
    """Category 4 (Python): Unknown group, unknown family, and unknown ID variations fail closed."""
    table = load_family_table(FIXTURES_DIR)
    register = load_scenarios_register(FIXTURES_DIR)

    # Register unknown group + familiar id PW01
    reg_unk_grp = dict(
        register,
        scenarios=[dict(s) if s["id"] != "PW01" else dict(s, group="unknown_group") for s in register["scenarios"]],
    )
    with pytest.raises(BrowserHarnessValidationError, match="disagree on group for PW01"):
        validate_family_table_and_register(table, reg_unk_grp)

    # Register unknown ID PW999 + familiar group playwright
    reg_unk_id = dict(
        register,
        scenarios=register["scenarios"] + [{"id": "PW999", "group": "playwright", "assertions": []}],
    )
    with pytest.raises(BrowserHarnessValidationError, match="disagree on scenario IDs"):
        validate_family_table_and_register(table, reg_unk_id)

    # Unknown group + unknown ID in register
    reg_unk_both = dict(
        register,
        scenarios=register["scenarios"] + [{"id": "PW999", "group": "unknown_group", "assertions": []}],
    )
    with pytest.raises(BrowserHarnessValidationError, match="disagree on scenario IDs"):
        validate_family_table_and_register(table, reg_unk_both)

    # Valid known + unknown mixed selection
    with pytest.raises(BrowserHarnessValidationError, match="Unknown scenario ID in selection: UNKNOWN99"):
        resolve_scenario_family_authority(table, ("PW01", "UNKNOWN99"))


def test_family_table_supported_mixes_empty_fail_closed_python() -> None:
    """Category 5 (Python): Empty supported_mixes with mixed selection PW01+BR01 fails closed before receipt."""
    table = load_family_table(FIXTURES_DIR)
    table_empty_mix = dict(table, supported_mixes=[])

    # Empty target selection
    with pytest.raises(BrowserHarnessValidationError, match="Target scenarios must not be empty"):
        resolve_scenario_family_authority(table_empty_mix, ())

    # Mixed selection PW01 + BR01 fails closed when supported_mixes is empty
    with pytest.raises(BrowserHarnessValidationError, match="Unsupported scenario family mix: \\['apg123', 'apg125'\\]"):
        resolve_scenario_family_authority(table_empty_mix, ("PW01", "BR01"))


def test_altered_table_authority_consumed_consistently_python(tmp_path: Path) -> None:
    """Mechanically demonstrate no hardcoded fallback: altered table authority is consumed consistently."""
    table = load_family_table(FIXTURES_DIR)
    register = load_scenarios_register(FIXTURES_DIR)

    # Create altered table with custom authorities
    altered_families = [
        dict(table["families"][0], authority="CUSTOM-APG123-RECEIPT"),
        table["families"][1],
    ]
    altered_mixes = [
        {"families": ["apg123", "apg125"], "authority": "CUSTOM-MIXED-RECEIPT"}
    ]
    altered_table = dict(table, families=altered_families, supported_mixes=altered_mixes)

    # 1. Authority resolution directly consumes altered table authority
    auth_single = resolve_scenario_family_authority(altered_table, ("PW01",))
    assert auth_single == "CUSTOM-APG123-RECEIPT"

    auth_mix = resolve_scenario_family_authority(altered_table, ("PW01", "BR01"))
    assert auth_mix == "CUSTOM-MIXED-RECEIPT"

    # 2. validate_receipt enforces altered authority and refuses the old hardcoded string
    fake_fixtures = tmp_path / "fake-fixtures"
    fake_fixtures.mkdir(mode=0o700)
    (fake_fixtures / "family_table.json").write_text(json.dumps(altered_table), encoding="utf-8")
    (fake_fixtures / "scenarios.json").write_text(json.dumps(register), encoding="utf-8")
    (fake_fixtures / "runner.mjs").write_text((FIXTURES_DIR / "runner.mjs").read_text(encoding="utf-8"), encoding="utf-8")

    valid_custom_receipt = {
        "schema_version": "1.0.0",
        "authority": "CUSTOM-APG123-RECEIPT",
        "package": {"name": "@playwright/test", "version": "1.62.1"},
        "browsers": {"chromium": "151.0"},
        "summary": {"total": 1, "passed": 1, "failed": 0, "skipped": 0},
        "scenarios": [
            {
                "scenario_id": "PW01",
                "group": "playwright",
                "browser": "chromium",
                "status": "passed",
                "assertions": [{"name": "unique_locator_success", "passed": True}, {"name": "strict_mode_violation_rejection", "passed": True}],
            },
        ],
    }

    # Succeeds with altered authority
    receipt = validate_receipt(
        valid_custom_receipt,
        expected_browsers=("chromium",),
        expected_scenarios=("PW01",),
        fixtures_dir=fake_fixtures,
    )
    assert receipt.raw["authority"] == "CUSTOM-APG123-RECEIPT"

    # Fails when old hardcoded authority is supplied
    old_receipt = dict(valid_custom_receipt, authority=APG123_BROWSER_UI_AUTHORITY)
    with pytest.raises(BrowserHarnessValidationError, match="Receipt authority mismatch: expected CUSTOM-APG123-RECEIPT"):
        validate_receipt(
            old_receipt,
            expected_browsers=("chromium",),
            expected_scenarios=("PW01",),
            fixtures_dir=fake_fixtures,
        )


def test_receipt_hash_binding_and_table_register_agreement_python(tmp_path: Path) -> None:
    """Verify validate_receipt checks hash digest equality and table/register agreement."""
    import hashlib
    load_family_table(FIXTURES_DIR)
    register = load_scenarios_register(FIXTURES_DIR)

    fake_fixtures = tmp_path / "fixtures-hash"
    fake_fixtures.mkdir(mode=0o700)
    runner_content = (FIXTURES_DIR / "runner.mjs").read_bytes()
    register_content = (FIXTURES_DIR / "scenarios.json").read_bytes()
    table_content = (FIXTURES_DIR / "family_table.json").read_bytes()

    (fake_fixtures / "runner.mjs").write_bytes(runner_content)
    (fake_fixtures / "scenarios.json").write_bytes(register_content)
    (fake_fixtures / "family_table.json").write_bytes(table_content)

    runner_sha = hashlib.sha256(runner_content).hexdigest()
    register_sha = hashlib.sha256(register_content).hexdigest()
    table_sha = hashlib.sha256(table_content).hexdigest()

    base_receipt = {
        "schema_version": "1.0.0",
        "authority": APG123_BROWSER_UI_AUTHORITY,
        "package": {"name": "@playwright/test", "version": "1.62.1"},
        "browsers": {"chromium": "151.0"},
        "summary": {"total": 1, "passed": 1, "failed": 0, "skipped": 0},
        "scenarios": [
            {
                "scenario_id": "PW01",
                "group": "playwright",
                "browser": "chromium",
                "status": "passed",
                "assertions": [{"name": "unique_locator_success", "passed": True}, {"name": "strict_mode_violation_rejection", "passed": True}],
            },
        ],
        "runtime": {
            "runner_sha256": runner_sha,
            "register_sha256": register_sha,
            "table_sha256": table_sha,
        },
        "table": {
            "schema_version": "1.0.0",
            "sha256": table_sha,
        },
    }

    # 1. Valid receipt with matching hashes passes
    r = validate_receipt(base_receipt, ("chromium",), ("PW01",), fixtures_dir=fake_fixtures)
    assert r.is_clean_pass

    # 2. Mismatched runner hash fails
    bad_runner = json.loads(json.dumps(base_receipt))
    bad_runner["runtime"]["runner_sha256"] = "a" * 64
    with pytest.raises(BrowserHarnessValidationError, match="Receipt runtime.runner_sha256 digest mismatch"):
        validate_receipt(bad_runner, ("chromium",), ("PW01",), fixtures_dir=fake_fixtures)

    # 3. Mismatched register hash fails
    bad_reg = json.loads(json.dumps(base_receipt))
    bad_reg["runtime"]["register_sha256"] = "b" * 64
    with pytest.raises(BrowserHarnessValidationError, match="Receipt runtime.register_sha256 digest mismatch"):
        validate_receipt(bad_reg, ("chromium",), ("PW01",), fixtures_dir=fake_fixtures)

    # 4. Mismatched table hash fails
    bad_tbl = json.loads(json.dumps(base_receipt))
    bad_tbl["runtime"]["table_sha256"] = "c" * 64
    with pytest.raises(BrowserHarnessValidationError, match="Receipt runtime.table_sha256 digest mismatch"):
        validate_receipt(bad_tbl, ("chromium",), ("PW01",), fixtures_dir=fake_fixtures)

    # 5. Table and register agreement: mismatched group in register inside fixtures_dir fails
    bad_fixtures = tmp_path / "fixtures-disagree"
    bad_fixtures.mkdir(mode=0o700)
    (bad_fixtures / "runner.mjs").write_bytes(runner_content)
    (bad_fixtures / "family_table.json").write_bytes(table_content)
    disagree_register = dict(
        register,
        scenarios=[dict(s) if s["id"] != "PW01" else dict(s, group="accessibility") for s in register["scenarios"]],
    )
    (bad_fixtures / "scenarios.json").write_text(json.dumps(disagree_register), encoding="utf-8")

    with pytest.raises(BrowserHarnessValidationError, match="disagree on group for PW01"):
        validate_receipt(base_receipt, ("chromium",), ("PW01",), fixtures_dir=bad_fixtures)


def test_real_js_consumer_fail_closed_negative_categories(tmp_path: Path) -> None:
    """Verify real JS consumer (runner.mjs) refuses execution with exit code 1 and writes NO receipt for all negative categories."""
    node_bin = os.environ["APG_JAVASCRIPT_NODE"]
    real_scratch = Path(os.path.realpath(tmp_path / "js-scratch"))
    real_scratch.mkdir(mode=0o700)

    base_table = json.loads((FIXTURES_DIR / "family_table.json").read_text(encoding="utf-8"))
    base_reg = json.loads((FIXTURES_DIR / "scenarios.json").read_text(encoding="utf-8"))

    reg_file = real_scratch / "scenarios.json"
    reg_file.write_text(json.dumps(base_reg), encoding="utf-8")

    cases = [
        # 1. Unknown schema version
        ("schema_version", dict(base_table, schema_version="9.9.9"), base_reg, None, "Unsupported family table schema_version: 9.9.9"),
        # 2. Duplicate family in table
        ("duplicate_family", dict(base_table, families=base_table["families"] + [base_table["families"][0]]), base_reg, None, "Duplicate family registration in family table"),
        # 3. Duplicate entry in table
        ("duplicate_entry", dict(base_table, entries=base_table["entries"] + [base_table["entries"][0]]), base_reg, None, "Duplicate scenario ID in family table"),
        # 4. Duplicate mix in table
        ("duplicate_mix", dict(base_table, supported_mixes=base_table["supported_mixes"] + [base_table["supported_mixes"][0]]), base_reg, None, "Duplicate mix registration in family table"),
        # 5. Singleton mix ambiguity in table
        ("singleton_mix", dict(base_table, supported_mixes=[{"families": ["apg123"], "authority": "APG123-BROWSER-UI-QUALIFIED-RECEIPT"}]), base_reg, None, "singleton mix for family 'apg123'"),
        # 6. Duplicate in alias
        ("duplicate_alias", dict(base_table, aliases=dict(base_table["aliases"], playwright=base_table["aliases"]["playwright"] + ["PW01"])), base_reg, None, "Duplicate scenario ID in alias playwright"),
        # 7. Unknown group in table entry
        ("unknown_group", dict(base_table, entries=[dict(e) if e["id"] != "PW01" else dict(e, group="invalid_group") for e in base_table["entries"]]), base_reg, None, "Unknown group in family table"),
        # 8. Register unknown group + familiar id PW01
        ("reg_unknown_group_familiar_id", base_table, dict(base_reg, scenarios=[dict(s) if s["id"] != "PW01" else dict(s, group="unknown_group") for s in base_reg["scenarios"]]), None, "disagree on group for PW01"),
        # 9. Register unknown ID PW999 + familiar group playwright
        ("reg_unknown_id_familiar_group", base_table, dict(base_reg, scenarios=base_reg["scenarios"] + [{"id": "PW999", "group": "playwright", "assertions": []}]), None, "disagree on scenario IDs"),
        # 10. Unknown group + unknown ID in register
        ("unknown_group_unknown_id", base_table, dict(base_reg, scenarios=base_reg["scenarios"] + [{"id": "PW999", "group": "unknown_group", "assertions": []}]), None, "disagree on scenario IDs"),
        # 11. Valid known + unknown mixed CLI filter
        ("valid_known_unknown_mixed_filter", base_table, base_reg, "PW01,UNKNOWN99", "Unknown scenario ID: UNKNOWN99"),
        # 12. Duplicate in CLI filter
        ("duplicate_filter", base_table, base_reg, "PW01,PW01", "Duplicate scenario ID in filter: PW01"),
        # 13. Table vs register disagreement (missing scenario)
        ("table_register_missing_sc", base_table, dict(base_reg, scenarios=[s for s in base_reg["scenarios"] if s["id"] != "PW01"]), None, "disagree on scenario IDs"),
        # 14. Supported_mixes empty with PW01+BR01 selection => refuse before receipt
        ("empty_mixes_mixed_selection", dict(base_table, supported_mixes=[]), base_reg, "PW01,BR01", "Unsupported scenario family mix"),
    ]

    for label, table_data, register_data, filter_arg, expected_err_substr in cases:
        tbl_file = real_scratch / f"table_{label}.json"
        tbl_file.write_text(json.dumps(table_data), encoding="utf-8")

        rg_file = real_scratch / f"reg_{label}.json"
        rg_file.write_text(json.dumps(register_data), encoding="utf-8")

        rec_file = real_scratch / f"receipt_{label}.json"

        cmd = [
            node_bin,
            os.fspath(FIXTURES_DIR / "runner.mjs"),
            "--scratch", os.fspath(real_scratch),
            "--receipt", os.fspath(rec_file),
            "--table", os.fspath(tbl_file),
            "--register", os.fspath(rg_file),
        ]
        if filter_arg:
            cmd.extend(["--scenarios", filter_arg])

        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        assert proc.returncode == 1, f"Expected non-zero exit code for {label}, got {proc.returncode}. stdout: {proc.stdout}, stderr: {proc.stderr}"
        assert expected_err_substr in proc.stderr, f"Expected '{expected_err_substr}' in stderr for {label}, got: {proc.stderr}"
        assert not rec_file.exists(), f"Receipt file must NOT be written when execution is refused for {label}"


def test_real_js_consumer_altered_authority_and_no_hardcoded_fallback(tmp_path: Path) -> None:
    """Verify real JS consumer mechanically consumes altered table authority without hardcoded fallback."""
    node_bin = os.environ["APG_JAVASCRIPT_NODE"]
    scratch = Path(os.path.realpath(tmp_path / "js-altered-scratch"))
    scratch.mkdir(mode=0o700)

    base_table = json.loads((FIXTURES_DIR / "family_table.json").read_text(encoding="utf-8"))
    altered_families = [
        dict(base_table["families"][0], authority="CUSTOM-JS-APG123-RECEIPT"),
        base_table["families"][1],
    ]
    altered_mixes = [
        {"families": ["apg123", "apg125"], "authority": "CUSTOM-JS-MIXED-RECEIPT"}
    ]
    altered_table = dict(base_table, families=altered_families, supported_mixes=altered_mixes)

    tbl_file = scratch / "altered_table.json"
    tbl_file.write_text(json.dumps(altered_table), encoding="utf-8")

    # Run JS script to verify resolveScenarioAuthority and writeReceiptFile fallback consume altered authority
    script = f"""
    import {{ resolveScenarioAuthority, writeReceiptFile }} from {json.dumps((FIXTURES_DIR / 'runner.mjs').as_uri())};
    import fs from 'node:fs';

    const table = JSON.parse(fs.readFileSync({json.dumps(str(tbl_file))}, 'utf-8'));
    const auth1 = resolveScenarioAuthority(table, ['PW01']);
    if (auth1 !== 'CUSTOM-JS-APG123-RECEIPT') {{
      throw new Error('resolveScenarioAuthority did not consume altered single family authority: ' + auth1);
    }}

    const authMix = resolveScenarioAuthority(table, ['PW01', 'BR01']);
    if (authMix !== 'CUSTOM-JS-MIXED-RECEIPT') {{
      throw new Error('resolveScenarioAuthority did not consume altered mix authority: ' + authMix);
    }}

    // Verify writeReceiptFile fallback also uses validated table source
    const receiptPath = {json.dumps(str(scratch / 'fallback_receipt.json'))};
    const scenarios = [{{ scenario_id: 'PW01', group: 'playwright', browser: 'chromium', status: 'passed', assertions: [{{ name: 'test', passed: true }}] }}];
    writeReceiptFile(receiptPath, scenarios, {{ chromium: '151.0' }}, Date.now() - 100, null, [], null, null, null, {json.dumps(str(tbl_file))});

    const written = JSON.parse(fs.readFileSync(receiptPath, 'utf-8'));
    if (written.authority !== 'CUSTOM-JS-APG123-RECEIPT') {{
      throw new Error('writeReceiptFile fallback did not consume altered table authority: ' + written.authority);
    }}

    process.stdout.write(JSON.stringify({{ success: true }}));
    """

    proc = subprocess.run([node_bin, "--input-type=module", "-e", script], capture_output=True, text=True, timeout=10)
    assert proc.returncode == 0, f"JS execution failed: {proc.stderr}"
    res = json.loads(proc.stdout)
    assert res.get("success") is True


@pytest.mark.parametrize("fault", ["empty", "missing_ids", "malformed_table", "missing_table", "authority_mismatch"])
def test_receipt_writer_refuses_unbound_authority(tmp_path: Path, fault: str) -> None:
    receipt = tmp_path / "refused.json"
    table = tmp_path / "table.json"
    table.write_text("{malformed" if fault == "malformed_table" else
                     (FIXTURES_DIR / "family_table.json").read_text(), encoding="utf-8")
    if fault == "missing_table":
        table.unlink()
    scenarios = ([{"scenario_id": "PW01", "status": "passed"}] if fault in ("malformed_table", "missing_table", "authority_mismatch")
                 else [{}] if fault == "missing_ids" else [])
    authority = "incorrect-authority" if fault == "authority_mismatch" else None
    script = f"""
    import {{ writeReceiptFile }} from {json.dumps((FIXTURES_DIR / 'runner.mjs').as_uri())};
    import fs from 'node:fs';
    let refused = false;
    try {{
      writeReceiptFile({json.dumps(str(receipt))}, {json.dumps(scenarios)}, {{}}, Date.now(),
                       null, [], null, null, {json.dumps(authority)}, {json.dumps(str(table))});
    }} catch (error) {{ refused = true; }}
    if (!refused || fs.existsSync({json.dumps(str(receipt))})) throw new Error('unbound receipt accepted');
    """
    result = subprocess.run([os.environ["APG_JAVASCRIPT_NODE"], "--input-type=module", "-e", script],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
