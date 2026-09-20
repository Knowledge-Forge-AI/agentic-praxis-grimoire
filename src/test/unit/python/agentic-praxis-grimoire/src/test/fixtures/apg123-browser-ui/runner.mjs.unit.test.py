#!/usr/bin/env python3
"""Deterministic unit tests for APG123 browser UI runner lifecycle contracts.

Validates:
- Primary error is never replaced by context/browser cleanup or receipt persistence.
- Secondary cleanup errors are preserved separately with persisted scenario receipt.
- Cleanup-only failures and abrupt engine closes fail with attributable retained evidence.
- Context creation, newPage, and UA setup failures are covered via engine diagnostics.
- Sanitized monotonic append-only progress.jsonl across all phases.
- writeReceiptFile compatibility with optional engine_errors.
"""

from __future__ import annotations

import json
import os
import importlib
from pathlib import Path
import subprocess
import sys
import tempfile

import pytest

from src.test.apg_test_support import repository_root

ROOT = repository_root(__file__)
FIXTURES_DIR = ROOT / "src/test/fixtures/apg123-browser-ui"
RUNNER_MJS = FIXTURES_DIR / "runner.mjs"


def resolve_node() -> str:
    return os.environ["APG_JAVASCRIPT_NODE"]


def run_node_eval(script: str, args: list[str] | None = None, timeout: int = 15) -> subprocess.CompletedProcess[str]:
    cmd = [resolve_node(), "--input-type=module", "-e", script] + (args or [])
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def test_primary_and_cleanup_retains_both_separately() -> None:
    """Verify primary error is not replaced by context cleanup error, and both are retained."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        script = f"""
import {{ runScenarioLifecycle }} from {json.dumps(RUNNER_MJS.as_uri())};

const fakeContext = {{
  async newPage() {{
    return {{}};
  }},
  async close() {{
    throw new Error('Secondary context close crash');
  }}
}};

const outcome = await runScenarioLifecycle({{
  scenario: {{ id: 'PW01', group: 'playwright' }},
  browserName: 'chromium',
  context: fakeContext,
  executeFn: async () => {{
    throw new Error('Primary assertion failed: expected 42 but got 0');
  }},
  scratchDir: {json.dumps(tmp_dir)},
}});

console.log(JSON.stringify(outcome));
"""
        proc = run_node_eval(script)
        assert proc.returncode == 0, f"Node script failed: {proc.stderr}\n{proc.stdout}"
        outcome = json.loads(proc.stdout.strip().splitlines()[-1])

        assert outcome["status"] == "failed"
        assert "Primary assertion failed" in outcome["error"]
        assert outcome["error_details"]["message"] == outcome["error"]
        assert outcome["cleanup_error"] is not None
        assert "Secondary context close crash" in outcome["cleanup_error"]
        assert outcome["cleanup_error_details"] is not None
        assert outcome["cleanup_only"] is False


def test_cleanup_only_failure_fails_with_attributable_evidence() -> None:
    """Verify cleanup-only failure marks scenario failed and attributes engine error."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        script = f"""
import {{ runScenarioLifecycle }} from {json.dumps(RUNNER_MJS.as_uri())};

const fakeContext = {{
  async newPage() {{
    return {{}};
  }},
  async close() {{
    throw new Error('Cleanup-only context close failure');
  }}
}};

const outcome = await runScenarioLifecycle({{
  scenario: {{ id: 'PW02', group: 'playwright' }},
  browserName: 'firefox',
  context: fakeContext,
  executeFn: async () => {{
    return {{ assertions: [{{ name: 'test_pass', passed: true }}], artifacts: [] }};
  }},
  scratchDir: {json.dumps(tmp_dir)},
}});

console.log(JSON.stringify(outcome));
"""
        proc = run_node_eval(script)
        assert proc.returncode == 0, f"Node script failed: {proc.stderr}\n{proc.stdout}"
        outcome = json.loads(proc.stdout.strip().splitlines()[-1])

        assert outcome["status"] == "failed"
        assert outcome["cleanup_only"] is True
        assert "Cleanup-only context close failure" in outcome["error"]
        assert outcome["engine_error"] is not None
        assert outcome["engine_error"]["stage"] == "cleanup_only"
        assert outcome["engine_error"]["phase"] == "context cleanup"


def test_abrupt_browser_disconnect_observed_and_attributed() -> None:
    """Verify abrupt browser disconnect during execution is observed and attributed."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        script = f"""
import {{ runScenarioLifecycle }} from {json.dumps(RUNNER_MJS.as_uri())};

let disconnected = false;
const fakeContext = {{
  async newPage() {{
    return {{}};
  }},
  async close() {{
    return;
  }}
}};

const outcome = await runScenarioLifecycle({{
  scenario: {{ id: 'PW03', group: 'playwright' }},
  browserName: 'webkit',
  context: fakeContext,
  executeFn: async () => {{
    disconnected = true;
    return {{ assertions: [], artifacts: [] }};
  }},
  scratchDir: {json.dumps(tmp_dir)},
  checkAbruptDisconnect: () => disconnected ? new Error('Browser webkit abruptly disconnected') : null,
}});

console.log(JSON.stringify(outcome));
"""
        proc = run_node_eval(script)
        assert proc.returncode == 0, f"Node script failed: {proc.stderr}\n{proc.stdout}"
        outcome = json.loads(proc.stdout.strip().splitlines()[-1])

        assert outcome["status"] == "failed"
        assert "abruptly disconnected" in outcome["error"]
        assert outcome["engine_error"] is not None
        assert outcome["engine_error"]["stage"] == "abrupt_disconnect"


def test_browser_close_preserves_initiating_error_separately() -> None:
    """Verify closeBrowserSafe suppresses browser close error when initiating error exists."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        script = f"""
import {{ closeBrowserSafe }} from {json.dumps(RUNNER_MJS.as_uri())};

const fakeBrowser = {{
  async close() {{
    throw new Error('Browser close target crashed');
  }}
}};

const initiatingErr = new Error('Scenario assertion failed');
const res = await closeBrowserSafe(fakeBrowser, initiatingErr, {{
  scratchDir: {json.dumps(tmp_dir)},
  browserName: 'chromium',
}});

console.log(JSON.stringify({{
  success: res.success,
  preservedSeparately: res.preservedSeparately,
  errorMessage: res.error.message,
}}));
"""
        proc = run_node_eval(script)
        assert proc.returncode == 0, f"Node script failed: {proc.stderr}\n{proc.stdout}"
        res = json.loads(proc.stdout.strip().splitlines()[-1])

        assert res["success"] is False
        assert res["preservedSeparately"] is True
        assert "Browser close target crashed" in res["errorMessage"]


def test_browser_close_cleanup_only_failure_not_suppressed() -> None:
    """Verify closeBrowserSafe does NOT mark preservedSeparately when initiating error is null."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        script = f"""
import {{ closeBrowserSafe }} from {json.dumps(RUNNER_MJS.as_uri())};

const fakeBrowser = {{
  async close() {{
    throw new Error('Browser close failed abruptly in cleanup-only');
  }}
}};

const res = await closeBrowserSafe(fakeBrowser, null, {{
  scratchDir: {json.dumps(tmp_dir)},
  browserName: 'chromium',
}});

console.log(JSON.stringify({{
  success: res.success,
  preservedSeparately: res.preservedSeparately,
  errorMessage: res.error.message,
}}));
"""
        proc = run_node_eval(script)
        assert proc.returncode == 0, f"Node script failed: {proc.stderr}\n{proc.stdout}"
        res = json.loads(proc.stdout.strip().splitlines()[-1])

        assert res["success"] is False
        assert res["preservedSeparately"] is False
        assert "cleanup-only" in res["errorMessage"]


def test_receipt_persistence_error_does_not_replace_primary() -> None:
    """Verify persistReceiptSafe preserves primary error when writing receipt fails."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Invalid receipt path to trigger write error
        invalid_path = Path(tmp_dir) / "nonexistent_dir" / "sub" / "receipt.json"
        script = f"""
import {{ persistReceiptSafe }} from {json.dumps(RUNNER_MJS.as_uri())};

const primaryErr = new Error('Original primary failure');
const res = persistReceiptSafe(
  {json.dumps(str(invalid_path))},
  [{{ scenario_id: 'PW01', group: 'playwright', browser: 'chromium', status: 'failed' }}],
  {{ chromium: '151.0' }},
  Date.now() - 500,
  null,
  [],
  {{
    primaryError: primaryErr,
    scratchDir: {json.dumps(tmp_dir)},
    browserName: 'chromium',
    scenarioId: 'PW01',
  }}
);

console.log(JSON.stringify({{
  success: res.success,
  preservedSeparately: res.preservedSeparately,
  hasError: Boolean(res.error),
}}));
"""
        proc = run_node_eval(script)
        assert proc.returncode == 0, f"Node script failed: {proc.stderr}\n{proc.stdout}"
        res = json.loads(proc.stdout.strip().splitlines()[-1])

        assert res["success"] is False
        assert res["preservedSeparately"] is True
        assert res["hasError"] is True


def test_context_creation_and_newpage_failures_attributed() -> None:
    """Verify context creation and newPage failures are captured via engine diagnostics."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        script = f"""
import {{ runScenarioLifecycle }} from {json.dumps(RUNNER_MJS.as_uri())};

// 1. Context creation failure
const outcome1 = await runScenarioLifecycle({{
  scenario: {{ id: 'PW01', group: 'playwright' }},
  browserName: 'chromium',
  createContextFn: async () => {{
    throw new Error('Sandbox denied context creation');
  }},
  executeFn: async () => {{}},
  scratchDir: {json.dumps(tmp_dir)},
}});

// 2. newPage failure with context close
let contextClosed = false;
const fakeContext = {{
  async newPage() {{
    throw new Error('Page creation allocation failure');
  }},
  async close() {{
    contextClosed = true;
  }}
}};

const outcome2 = await runScenarioLifecycle({{
  scenario: {{ id: 'PW02', group: 'playwright' }},
  browserName: 'chromium',
  context: fakeContext,
  executeFn: async () => {{}},
  scratchDir: {json.dumps(tmp_dir)},
}});

console.log(JSON.stringify({{
  o1: outcome1,
  o2: outcome2,
  contextClosed,
}}));
"""
        proc = run_node_eval(script)
        assert proc.returncode == 0, f"Node script failed: {proc.stderr}\n{proc.stdout}"
        data = json.loads(proc.stdout.strip().splitlines()[-1])

        o1 = data["o1"]
        assert o1["status"] == "failed"
        assert "Sandbox denied context creation" in o1["error"]
        assert o1["engine_error"]["stage"] == "context_creation"

        o2 = data["o2"]
        assert o2["status"] == "failed"
        assert "Page creation allocation failure" in o2["error"]
        assert o2["engine_error"]["stage"] == "page_creation"
        assert data["contextClosed"] is True


def test_monotonic_sanitized_progress_logging() -> None:
    """Verify progress.jsonl records append-only monotonic timestamps across required phases."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        progress_file = Path(tmp_dir) / "progress.jsonl"
        script = f"""
import {{ recordProgress, resetProgressMonotonicForTesting }} from {json.dumps(RUNNER_MJS.as_uri())};

resetProgressMonotonicForTesting();

recordProgress({json.dumps(tmp_dir)}, {{ phase: 'launch', engine: 'chromium', scenario: null }});
recordProgress({json.dumps(tmp_dir)}, {{ phase: 'execution', engine: 'chromium', scenario: 'PW01' }});
recordProgress({json.dumps(tmp_dir)}, {{ phase: 'context cleanup', engine: 'chromium', scenario: 'PW01' }});
recordProgress({json.dumps(tmp_dir)}, {{ phase: 'receipt persistence', engine: 'chromium', scenario: 'PW01' }});
recordProgress({json.dumps(tmp_dir)}, {{ phase: 'browser cleanup', engine: 'chromium', scenario: null }});
"""
        proc = run_node_eval(script)
        assert proc.returncode == 0, f"Node script failed: {proc.stderr}\n{proc.stdout}"

        assert progress_file.is_file()
        lines = [json.loads(line) for line in progress_file.read_text(encoding="utf-8").strip().splitlines()]
        assert len(lines) == 5

        expected_phases = ["launch", "execution", "context cleanup", "receipt persistence", "browser cleanup"]
        last_ms = -1.0
        for entry, expected_phase in zip(lines, expected_phases):
            assert entry["phase"] == expected_phase
            assert entry["engine"] == "chromium"
            assert "monotonic_ms" in entry
            ms = float(entry["monotonic_ms"])
            assert ms >= last_ms, f"Monotonicity violation: {ms} < {last_ms}"
            last_ms = ms


def test_write_receipt_file_compatible_with_optional_engine_errors() -> None:
    """Verify writeReceiptFile supports optional engine_errors and preserves existing schema when omitted."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        r1 = Path(tmp_dir) / "receipt_standard.json"
        r2 = Path(tmp_dir) / "receipt_with_errors.json"
        r3 = Path(tmp_dir) / "receipt_empty_scenarios.json"

        script = f"""
import {{ writeReceiptFile }} from {json.dumps(RUNNER_MJS.as_uri())};

const scPassed = [{{ scenario_id: 'PW01', group: 'playwright', browser: 'chromium', status: 'passed' }}];

// 1. Without engineErrors: existing contract, no engine_errors key
writeReceiptFile({json.dumps(str(r1))}, scPassed, {{ chromium: '151.0' }}, Date.now() - 100, null, []);

// 2. With engineErrors: engine_errors present, summary reflects failure if cleanup-only
const engineErrors = [{{ phase: 'context cleanup', engine: 'chromium', scenario: 'PW01', error: {{ message: 'cleanup failed' }} }}];
writeReceiptFile({json.dumps(str(r2))}, scPassed, {{ chromium: '151.0' }}, Date.now() - 100, null, [], null, null, null, null, null, engineErrors);

// 3. With empty scenarios and resolved authority
    writeReceiptFile({json.dumps(str(r3))}, [], {{ chromium: '151.0' }}, Date.now() - 100, null, [], null, null, 'APG123-BROWSER-UI-QUALIFIED-RECEIPT', null, null, [{{ phase: 'launch', error: {{ message: 'launch failed' }}, target_scenarios: ['PW01'] }}]);
"""
        proc = run_node_eval(script)
        assert proc.returncode == 0, f"Node script failed: {proc.stderr}\n{proc.stdout}"

        d1 = json.loads(r1.read_text(encoding="utf-8"))
        assert "engine_errors" not in d1
        assert d1["summary"]["passed"] == 1
        assert d1["summary"]["failed"] == 0

        d2 = json.loads(r2.read_text(encoding="utf-8"))
        assert "engine_errors" in d2
        assert len(d2["engine_errors"]) == 1
        assert d2["summary"]["failed"] > 0

        d3 = json.loads(r3.read_text(encoding="utf-8"))
        assert "engine_errors" in d3
        assert d3["authority"] == "APG123-BROWSER-UI-QUALIFIED-RECEIPT"
        assert d3["summary"]["failed"] == 1


def test_pending_primary_receipt_survives_cleanup_and_secondary_browser_error(tmp_path):
    """The actual writer persists before context close and retains both errors."""
    receipt = tmp_path / "receipt.json"
    script = f"""
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {{ runScenarioLifecycle, closeBrowserSafe, persistReceiptSafe }} from {json.dumps(RUNNER_MJS.as_uri())};
const receiptPath = {json.dumps(str(receipt))};
const records = [], engineErrors = [];
const primary = Object.assign(new Error('primary assertion'), {{ name: 'AssertionError' }});
const context = {{ newPage: async () => ({{}}), close: async () => {{
  assert.equal(JSON.parse(fs.readFileSync(receiptPath)).scenarios[0].error, 'primary assertion');
  throw new Error('secondary context');
}} }};
const persist = error => persistReceiptSafe(receiptPath, records, {{ webkit: 'test' }}, Date.now(), null, [],
  {{ engineErrors, primaryError: error, scratchDir: {json.dumps(str(tmp_path))} }});
const outcome = await runScenarioLifecycle({{ scenario: {{id: 'PW01', group: 'playwright'}},
  browserName: 'webkit', context, scratchDir: {json.dumps(str(tmp_path))},
  executeFn: async () => {{throw primary;}},
  persistPending: record => {{ records[0] = record; persist(primary); }} }});
assert.equal(outcome.primary_error, primary);
records[0] = outcome;
persist(primary);
const closed = await closeBrowserSafe({{close: async () => {{throw new Error('secondary browser');}}}}, primary);
engineErrors.push({{stage: 'browser_close_secondary', error: {{message: closed.error.message}}}});
persist(primary);
assert.equal(closed.preservedSeparately, true);
"""
    result = run_node_eval(script)
    assert result.returncode == 0, result.stderr
    evidence = json.loads(receipt.read_text())
    assert evidence["scenarios"][0]["error_details"]["class"] == "AssertionError"
    assert evidence["scenarios"][0]["cleanup_error"] == "secondary context"
    assert evidence["engine_errors"][0]["error"]["message"] == "secondary browser"
    progress = [json.loads(line) for line in (tmp_path / "progress.jsonl").read_text().splitlines()]
    assert progress[0]["boundary"] == "start"
    assert any(row["phase"] == "context cleanup" and row["boundary"] == "error" for row in progress)


@pytest.fixture
def main_process(tmp_path):
    """Run the real entrypoint with fake browser packages and socket servers.

    This proves main's process exit, writer and diagnostic wiring; it does not
    exercise real browser engines, sockets or the Playwright assertion API.
    """
    scratch = tmp_path.resolve()
    scratch.chmod(0o700)
    packages = scratch / "node_modules"
    playwright = packages / "playwright"
    playwright.mkdir(parents=True)
    (playwright / "index.js").write_text(r"""
const mode = process.env.APG_TEST_RUNNER_MODE;
exports.chromium = exports.firefox = exports.webkit = {
  async launch() {
    let connected = true, contexts = 0;
    const events = {};
    const browser = {
      version: () => 'synthetic-browser',
      isConnected: () => connected,
      on: (event, callback) => { events[event] = callback; },
      disconnect: () => { connected = false; events.disconnected?.(); },
      async newContext() {
        const ua = ++contexts === 1;
        return {
          route: async () => {},
          newPage: async () => ({
            goto: async () => {},
            evaluate: async () => {
              if (mode === 'ua_failure') throw new Error('primary UA probe failure');
              return {userAgent: 'synthetic', windowOrigin: 'http://127.0.0.1:12345', features: {}};
            },
            locator: selector => ({
              async click() {
                if (selector === '#single-btn' && mode.startsWith('primary')) {
                  const error = new Error('primary scenario assertion');
                  error.name = 'AssertionError';
                  throw error;
                }
                if (selector === '.dup-btn') throw new Error('strict mode violation resolved to 2 elements');
              },
            }),
          }),
          async close() {
            if (!ua && mode === 'cleanup_crash') {
              browser.disconnect();
              throw new Error('context close after disconnect');
            }
            if ((!ua && mode.startsWith('primary')) || (ua && mode === 'ua_failure')) {
              throw new Error('secondary context close failure');
            }
          },
        };
      },
      async close() {
        if (mode === 'browser_close' || mode.startsWith('primary')) {
          throw new Error('secondary browser close failure');
        }
        connected = false;
        events.disconnected?.();
      },
    };
    globalThis.apgTestBrowser = browser;
    return browser;
  },
};
""")
    assertions = packages / "@playwright/test"
    assertions.mkdir(parents=True)
    (assertions / "index.js").write_text("exports.expect = () => ({toHaveCount: async () => {}});\n")
    preload = scratch / "preload.mjs"
    preload.write_text(r"""
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import {EventEmitter} from 'node:events';
http.createServer = () => {
  const server = new EventEmitter();
  server.listen = (port, host, callback) => queueMicrotask(callback);
  server.address = () => ({port: 12345});
  server.close = callback => queueMicrotask(callback);
  return server;
};
const write = fs.writeFileSync;
fs.writeFileSync = function(file, data, ...args) {
  if (path.basename(String(file)) === 'receipt.json') {
    const receipt = JSON.parse(data);
    fs.appendFileSync(path.join(path.dirname(file), 'writes.jsonl'), data.replace(/\n/g, '') + '\n');
    if (process.env.APG_TEST_RUNNER_MODE === 'primary_receipt_failure') {
      throw new Error('secondary receipt persistence failure');
    }
    if (process.env.APG_TEST_RUNNER_MODE === 'late_disconnect' &&
        receipt.scenarios[0]?.status === 'passed') globalThis.apgTestBrowser.disconnect();
  }
  return write.call(this, file, data, ...args);
};
""")

    def run(mode):
        env = dict(os.environ, APG_TEST_RUNNER_MODE=mode,
                   APG_PLAYWRIGHT_PACKAGE_ROOT=str(scratch), APG_REPOSITORY_ROOT=str(ROOT))
        result = subprocess.run(
            [resolve_node(), "--import", str(preload), str(RUNNER_MJS),
             "--scratch", str(scratch), "--browsers", "webkit", "--scenarios", "PW01"],
            env=env, cwd=scratch, capture_output=True, text=True, timeout=15)
        receipt_path = scratch / "receipt.json"
        receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else None
        writes = [json.loads(line) for line in (scratch / "writes.jsonl").read_text().splitlines()]
        return result, receipt, writes

    return run


@pytest.mark.parametrize("mode,stage", [
    ("browser_close", "browser_close_cleanup_only"),
    ("late_disconnect", "abrupt_disconnect"),
    ("ua_failure", "ua_setup"),
])
def test_main_process_engine_failures_exit_nonzero_and_retain_receipt(main_process, mode, stage):
    result, receipt, writes = main_process(mode)
    assert result.returncode == 1, result.stderr
    assert "Runner fatal error:" in result.stderr
    assert receipt["summary"]["failed"] > 0
    assert any(item["engine"] == "webkit" and item["stage"] == stage for item in receipt["engine_errors"])
    if mode == "ua_failure":
        assert receipt["scenarios"] == []
        assert any(item["stage"] == "ua_context_cleanup_secondary" for item in receipt["engine_errors"])
        assert "primary UA probe failure" in result.stderr
    else:
        assert receipt["scenarios"][0]["status"] == "passed"
        assert writes[0]["scenarios"][0]["status"] == "pending_cleanup"


@pytest.mark.parametrize("mode", ["primary", "primary_receipt_failure"])
def test_main_process_primary_error_survives_cleanup_and_writer_failure(main_process, mode):
    result, receipt, writes = main_process(mode)
    assert result.returncode == 1
    fatal = json.loads(result.stderr.split("Runner fatal error: ")[-1])
    assert fatal["class"] == "AssertionError"
    assert "Scenario PW01 failed on webkit" in fatal["message"]
    assert "primary scenario assertion" in fatal["message"]
    assert "secondary browser close failure" in result.stderr
    assert "secondary context close failure" in result.stderr
    assert writes[0]["scenarios"][0]["error_details"]["class"] == "AssertionError"
    if mode == "primary_receipt_failure":
        assert receipt is None
        assert "Secondary receipt persistence error:" in result.stderr
    else:
        assert receipt["scenarios"][0]["error"] == "primary scenario assertion"
        assert receipt["scenarios"][0]["cleanup_error"] == "secondary context close failure"
        assert receipt["engine_errors"][0]["stage"] == "browser_close_secondary"


def test_main_process_repeated_writes_finish_pending_record_and_succeed(main_process):
    result, receipt, writes = main_process("success")
    assert result.returncode == 0, result.stderr
    assert len(writes) >= 3
    assert writes[0]["scenarios"][0]["status"] == "pending_cleanup"
    assert writes[-1] == receipt
    assert receipt["summary"] == {"total": 1, "passed": 1, "failed": 0, "skipped": 0}
    assert len(receipt["scenarios"][0]["assertions"]) == 2
    assert "engine_errors" not in receipt


def test_main_process_cleanup_crash_retains_disconnect_separately(main_process):
    result, receipt, _ = main_process("cleanup_crash")
    assert result.returncode == 1, result.stderr
    assert receipt["scenarios"][0]["status"] == "failed"
    errors = receipt["engine_errors"]
    assert [(item["engine"], item["scenario"], item["stage"]) for item in errors] == [
        ("webkit", "PW01", "cleanup_only"),
        ("webkit", "PW01", "abrupt_disconnect_secondary"),
    ]
    assert receipt["summary"] == {"total": 3, "passed": 0, "failed": 3, "skipped": 0}
    fatal = json.loads(result.stderr.split("Runner fatal error: ")[-1])
    assert "context close after disconnect" in fatal["message"]


def test_main_process_pending_receipt_cannot_validate_as_success(main_process):
    sys.path.insert(0, str(ROOT / "src/test/support"))
    harness = importlib.import_module("apg123_browser_ui")
    result, receipt, writes = main_process("success")
    assert result.returncode == 0, result.stderr
    assert receipt == writes[-1]
    harness.validate_receipt(receipt, ("webkit",), ("PW01",))
    with pytest.raises(harness.BrowserHarnessValidationError, match="Incomplete or failed scenario run"):
        harness.validate_receipt(writes[0], ("webkit",), ("PW01",))


def test_disconnect_during_context_cleanup_is_failure():
    script = f"""
import assert from 'node:assert/strict';
import {{runScenarioLifecycle}} from {json.dumps(RUNNER_MJS.as_uri())};
let connected = true;
const result = await runScenarioLifecycle({{scenario: {{id: 'PW01'}}, browserName: 'webkit',
  browser: {{isConnected: () => connected}}, context: {{newPage: async () => ({{}}), close: async () => {{connected=false;}}}},
  executeFn: async () => ({{assertions: [], artifacts: []}})}});
assert.equal(result.status, 'failed');
assert.equal(result.error_details.class, 'BrowserDisconnectError');
"""
    result = run_node_eval(script)
    assert result.returncode == 0, result.stderr


def test_pending_mixed_receipt_binds_full_selection_and_refuses_foreign_ids(tmp_path):
    script = f"""
import assert from 'node:assert/strict';
import {{writeReceiptFile}} from {json.dumps(RUNNER_MJS.as_uri())};
const scenarios = [{{scenario_id: 'PW01', status: 'pending_cleanup'}}];
const receipt = writeReceiptFile({json.dumps(str(tmp_path / 'receipt.json'))}, scenarios, {{}}, Date.now(), null, [],
  null, null, 'APG125-BROWSER-MIXED-QUALIFIED-RECEIPT', null, null, [], ['PW01','BR01']);
assert.equal(receipt.summary.passed, 0);
assert.equal(receipt.authority, 'APG125-BROWSER-MIXED-QUALIFIED-RECEIPT');
assert.throws(() => writeReceiptFile({json.dumps(str(tmp_path / 'foreign.json'))}, scenarios, {{}}, Date.now(), null, [],
  null, null, null, null, null, [], ['BR01']), /outside selected target/);
assert.throws(() => writeReceiptFile({json.dumps(str(tmp_path / 'unbound.json'))}, [], {{}}, Date.now(), null, [],
  null, null, 'forged', null, null, [{{error: 'launch failure'}}]), /must not be empty/);
"""
    result = run_node_eval(script)
    assert result.returncode == 0, result.stderr
