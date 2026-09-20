#!/usr/bin/env python3
"""Maintained unit test suite for Playwright test profile.

Validates scenario register schema, predicate definitions, negative controls,
synthetic HTML/SVG fixture integrity, cancellation and isolation contracts
for scenarios PW01-PW10 and SVG01-SVG03.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from src.test.apg_test_support import repository_root

ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src/test/support"))

from apg123_browser_ui import (  # noqa: E402
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



def test_supervisor_process_contract(tmp_path: Path) -> None:
    """Exercise the actual Node supervisor with real signals and a hard-hang control."""
    import json
    import os
    import shutil
    import subprocess

    node = os.environ.get("APG_JAVASCRIPT_NODE") or shutil.which("node")
    assert node, "Node is required for the supervisor process contract"
    module = (ROOT / "src/test/fixtures/apg123-browser-ui/supervisor_runner.mjs").as_uri()
    script = r"""
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
const { interruptReadyRunner } = await import(process.argv[1]);
const scratch = process.argv[2];
const cases = [
  ['graceful', "process.on('SIGINT', () => process.exit(130));", null],
  ['hang', "process.on('SIGINT', () => {});", 'timed out'],
  ['wrong-exit', "process.on('SIGINT', () => process.exit(0));", 'exit 130'],
  ['raw-signal', '', 'exit 130'],
  ['premature', 'process.exit(1);', 'before readiness'],
];
const outcomes = [];
for (const [name, handler, expected] of cases) {
  const ready = path.join(scratch, name + '.signal');
  const program = "const fs = require('node:fs');" + handler +
    "fs.writeFileSync(process.argv[1], 'ready'); setInterval(() => {}, 100);";
  const child = spawn(process.execPath, ['-e', program, ready], {
    detached: true, stdio: ['ignore', 'pipe', 'pipe'],
  });
  const exited = new Promise(resolve => child.once('exit', resolve));
  const emergencyCleanup = () => {
    try { process.kill(-child.pid, 'SIGKILL'); }
    catch (error) { if (error.code !== 'ESRCH') throw error; }
  };
  process.once('exit', emergencyCleanup);
  let failure;
  const started = Date.now();
  try {
  try { await interruptReadyRunner(child, ready, { readinessMs: 2000, interruptionMs: 200, cleanupMs: 2000 }); }
  catch (error) { failure = error.message; }
  if (expected ? !failure?.includes(expected) : failure) throw new Error(name + ': ' + failure);
  let dead = false;
  try { process.kill(-child.pid, 0); } catch (error) { dead = error.code === 'ESRCH'; }
  if (!dead) throw new Error(name + ': group survived');
  if (fs.existsSync(ready)) throw new Error(name + ': readiness file survived');
  if (Date.now() - started > 5000) throw new Error(name + ': cleanup was unbounded');
  outcomes.push(name);
  } finally {
    try {
      emergencyCleanup();
      let timer;
      try {
        await Promise.race([exited, new Promise((_, reject) => {
          timer = setTimeout(() => reject(new Error(name + ': emergency reap timed out')), 2000);
        })]);
      } finally { clearTimeout(timer); }
    } finally {
      process.removeListener('exit', emergencyCleanup);
      fs.rmSync(ready, { force: true });
    }
  }
}
console.log(JSON.stringify(outcomes));
"""
    result = subprocess.run(
        [node, "--input-type=module", "-e", script, module, str(tmp_path)],
        capture_output=True, text=True, timeout=30, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == ["graceful", "hang", "wrong-exit", "raw-signal", "premature"]


def test_supervisor_lifecycle_ordering_and_cleanup_errors(tmp_path: Path) -> None:
    """Exercise bounded cleanup with explicit child and group observations."""
    import os
    import shutil
    import subprocess

    node = os.environ.get("APG_JAVASCRIPT_NODE") or shutil.which("node")
    assert node, "Node is required for the supervisor lifecycle contract"
    result = subprocess.run(
        [node, str(FIXTURES_DIR / "supervisor_lifecycle_contract.mjs"), str(tmp_path)],
        capture_output=True, text=True, timeout=10, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert len(json.loads(result.stdout)) == 9
