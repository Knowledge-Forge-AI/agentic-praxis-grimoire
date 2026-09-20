import { execFile, spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import { createRequire } from 'node:module';
import os from 'node:os';
import path from 'node:path';

const PROCESS_SNAPSHOT_TIMEOUT_MS = 2000;
const MAX_OWNED_PROCESSES = 64;
export const CONTROLLED_RUN_MS = 30000;
export const CONTROLLED_CLEANUP_MS = 5000;

export function publishReadiness(signalFile, payload) {
  const temporary = `${signalFile}.${process.pid}.tmp`;
  try {
    fs.writeFileSync(temporary, JSON.stringify(payload), { flag: 'wx' });
    fs.renameSync(temporary, signalFile);
  } finally { fs.rmSync(temporary, { force: true }); }
}

// Both controlled runs have a watchdog independent of Playwright's own test
// timeout. A watchdog result is always failure, with bounded drain/reaping.
export function runControlledSupervisor(nodeBin, args, {
  cwd, env, label, timeoutMs = CONTROLLED_RUN_MS, cleanupMs = CONTROLLED_CLEANUP_MS,
}) {
  for (const [name, value, maximum] of [
    ['timeoutMs', timeoutMs, CONTROLLED_RUN_MS], ['cleanupMs', cleanupMs, CONTROLLED_CLEANUP_MS],
  ]) {
    if (!Number.isFinite(value) || value <= 0 || value > maximum) {
      throw new RangeError(`${name} must be positive and at most ${maximum}ms`);
    }
  }
  return new Promise((resolve, reject) => {
    const child = spawn(nodeBin, args, { cwd, env, detached: true, stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = '', stderr = '', failure, terminal, drainTimer, settled = false;
    const kill = () => {
      if (!child.pid) return;
      try { process.kill(-child.pid, 'SIGKILL'); }
      catch (error) { if (error.code !== 'ESRCH') failure += `; group cleanup: ${error.message}`; }
    };
    const parentTermination = () => { process.exit(143); };
    const finish = () => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      clearTimeout(drainTimer);
      process.removeListener('exit', kill);
      process.removeListener('SIGTERM', parentTermination);
      if (failure) reject(new Error(`${label}: ${failure}; child_reaped=${Boolean(terminal)}. STDOUT:\n${stdout}\nSTDERR:\n${stderr}`));
      else resolve({ ...terminal, stdout, stderr });
    };
    const boundDrain = () => {
      drainTimer ??= setTimeout(() => {
        failure ||= 'stream drain deadline exceeded';
        kill();
        child.stdout.destroy();
        child.stderr.destroy();
        finish();
      }, cleanupMs);
    };
    const fail = message => {
      if (settled) return;
      failure ||= message;
      kill();
      boundDrain();
    };
    const timer = setTimeout(() => fail(`controlled run timed out after ${timeoutMs}ms`), timeoutMs);
    process.once('exit', kill);
    process.once('SIGTERM', parentTermination);
    child.stdout.on('data', chunk => {
      stdout += chunk.toString();
      if (stdout.length > 2 * 1024 * 1024) { stdout = stdout.slice(-2 * 1024 * 1024); fail('stdout exceeded its bound'); }
    });
    child.stderr.on('data', chunk => {
      stderr += chunk.toString();
      if (stderr.length > 2 * 1024 * 1024) { stderr = stderr.slice(-2 * 1024 * 1024); fail('stderr exceeded its bound'); }
    });
    child.once('error', error => fail(`child error: ${error.message}`));
    child.once('exit', (code, signal) => { terminal = { code, signal }; boundDrain(); });
    child.once('close', finish);
  });
}

export function deriveInterruptionMs({ passRunMs, failRunMs }) {
  for (const [name, value] of Object.entries({ passRunMs, failRunMs })) {
    if (!Number.isFinite(value) || value < 0) {
      throw new TypeError(`${name} must be a finite non-negative number`);
    }
  }
  return Math.min(45000, Math.max(15000, Math.ceil(1.5 * Math.max(passRunMs, failRunMs))));
}

export function parseProcessSnapshot(output) {
  const rows = [];
  for (const line of output.split(/\r?\n/)) {
    if (!line.trim()) continue;
    const pidMatch = line.match(/^\s*(\d+)\s*(.*)$/);
    // Other system processes may have unavailable command/start fields. Keep
    // their topology, but validate identities only if custody depends on them.
    if (!pidMatch) continue;
    const ids = pidMatch[2].match(/^(\d+)\s+(.*)$/);
    const match = ids?.[2].match(/^(\S+)\s+((?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\d{4})\s+(.+)$/);
    rows.push({
      pid: Number(pidMatch[1]),
      ppid: ids ? Number(ids[1]) : null,
      state: match?.[1] || '',
      started: match?.[2].replace(/\s+/g, ' ') || '',
      command: match?.[3].trim() || '',
      invalid: match ? null : 'unrecognized ps fields',
    });
  }
  if (!rows.length) throw new Error('process snapshot was empty');
  const pids = new Set();
  for (const row of rows) {
    if (!Number.isSafeInteger(row.pid) || row.pid <= 0 || !Number.isSafeInteger(row.ppid) || row.ppid < 0) row.invalid = 'invalid topology';
    if (pids.has(row.pid)) {
      row.invalid = 'duplicate process identity';
      rows.find(previous => previous.pid === row.pid).invalid = row.invalid;
    }
    pids.add(row.pid);
  }
  return rows;
}

function runPsSnapshotSync() {
  const result = spawnSync('ps', ['-axo', 'pid=,ppid=,stat=,lstart=,command='], {
    encoding: 'utf8',
    maxBuffer: 2 * 1024 * 1024,
    timeout: PROCESS_SNAPSHOT_TIMEOUT_MS,
    killSignal: 'SIGKILL',
    env: { ...process.env, LC_ALL: 'C' },
  });
  if (result.error) throw new Error(`process snapshot failed: ${result.error.message}`, { cause: result.error });
  if (result.status !== 0) throw new Error(`process snapshot failed with status ${result.status}`);
  return parseProcessSnapshot(result.stdout || '');
}

export function readProcessSnapshot() {
  return new Promise((resolve, reject) => {
    execFile('ps', ['-axo', 'pid=,ppid=,stat=,lstart=,command='], {
      encoding: 'utf8',
      maxBuffer: 2 * 1024 * 1024,
      timeout: PROCESS_SNAPSHOT_TIMEOUT_MS,
      killSignal: 'SIGKILL',
      env: { ...process.env, LC_ALL: 'C' },
    }, (error, stdout) => {
      if (error) return reject(new Error(`process snapshot failed: ${error.message}`, { cause: error }));
      try { resolve(parseProcessSnapshot(stdout || '')); }
      catch (parseError) { reject(parseError); }
    });
  });
}

function processIdentity(row) {
  return `${row.pid}\0${row.started}`;
}

function processKind(command, browserExecutables) {
  if (/workerProcessEntry\.js/.test(command) ||
      /node_modules\/(?:@playwright\/test|playwright)\/.*\btest-worker\b/.test(command)) return 'worker';
  return browserExecutables.some(executable => command === executable || command.startsWith(`${executable} `))
    ? 'browser' : 'other';
}

function ownedDescendants(snapshot, runnerPid, browserExecutables, readyPid) {
  const descendants = [];
  const fail = message => {
    const error = new Error(message);
    error.ownedDescendants = descendants.slice(0, MAX_OWNED_PROCESSES);
    throw error;
  };
  const byPid = new Map(snapshot.map(row => [row.pid, row]));
  if (!byPid.has(runnerPid)) fail('process snapshot did not contain the Playwright runner');
  if (byPid.get(runnerPid).invalid) fail('process snapshot contains an invalid runner identity');
  const queue = [runnerPid];
  for (let index = 0; index < queue.length; index += 1) {
    const parentPid = queue[index];
    for (const row of snapshot) {
      if (row.ppid !== parentPid || row.pid === runnerPid) continue;
      if (row.invalid) fail('process snapshot contains an invalid owned process identity');
      if (queue.includes(row.pid)) fail('process snapshot contains a descendant cycle');
      queue.push(row.pid);
      const kind = row.pid === readyPid ? 'worker' : processKind(row.command, browserExecutables);
      descendants.push({ ...row, kind, identity: processIdentity(row) });
      if (descendants.length > MAX_OWNED_PROCESSES) {
        fail(`process snapshot exceeded ${MAX_OWNED_PROCESSES} owned descendants`);
      }
    }
  }
  if (!descendants.some(row => row.pid === readyPid && row.kind === 'worker')) {
    fail('process snapshot did not capture the readiness-signaling Playwright worker');
  }
  if (!descendants.some(row => row.kind === 'browser')) {
    fail('process snapshot did not capture the selected browser executable');
  }
  return descendants;
}

function liveIdentityRows(snapshot, owned) {
  if (snapshot.some(row => row.invalid && owned.some(captured => captured.pid === row.pid))) {
    throw new Error('process snapshot cannot establish a captured process identity');
  }
  const current = new Map(snapshot.map(row => [processIdentity(row), row]));
  return owned.filter(row => current.has(row.identity));
}

function processTreeDiagnostic(snapshot, runnerPid, owned, browserExecutables) {
  const selected = new Map();
  const byPid = new Map(snapshot.map(row => [row.pid, row]));
  if (byPid.has(runnerPid)) {
    const queue = [runnerPid];
    selected.set(runnerPid, byPid.get(runnerPid));
    for (let index = 0; index < queue.length; index += 1) {
      for (const row of snapshot) {
        if (row.ppid === queue[index] && !selected.has(row.pid)) {
          selected.set(row.pid, row);
          queue.push(row.pid);
        }
      }
    }
  }
  const ownedByIdentity = new Map(owned.map(row => [row.identity, row]));
  for (const row of snapshot) {
    const captured = ownedByIdentity.get(processIdentity(row));
    if (captured) selected.set(row.pid, { ...row, kind: captured.kind });
  }
  return [...selected.values()].slice(0, MAX_OWNED_PROCESSES + 1).map(row => ({
    pid: row.pid,
    ppid: row.ppid,
    state: row.state,
    kind: row.kind || processKind(row.command, browserExecutables),
  }));
}

function parseReadiness(signalFile, browserName, browserExecutables) {
  let ready;
  try { ready = JSON.parse(fs.readFileSync(signalFile, 'utf8')); }
  catch (error) { throw new Error(`Child readiness payload is invalid: ${error.message}`, { cause: error }); }
  if (!Number.isSafeInteger(ready?.pid) || ready.pid <= 0 || ready.browserName !== browserName ||
      JSON.stringify(ready.browserExecutables) !== JSON.stringify(browserExecutables)) {
    throw new Error('Child readiness payload does not bind its worker PID to the selected browser executable');
  }
  return ready;
}

export function selectedBrowserExecutables(browserName, browserExecutable, platform = process.platform) {
  // WebKit's public executablePath is a launcher script; custody must match
  // the native runtime it starts, not the wrapper itself.
  const executablePaths = browserName === 'webkit' ? [] : [browserExecutable];
  if (browserName === 'chromium') {
    const revisionMatch = browserExecutable.match(/[\\/]chromium-(\d+)(?:[\\/])/);
    if (revisionMatch) {
      const cacheRoot = path.resolve(browserExecutable.slice(0, revisionMatch.index));
      const shellRoot = path.join(cacheRoot, `chromium_headless_shell-${revisionMatch[1]}`);
      if (fs.existsSync(shellRoot)) {
        for (const entry of fs.readdirSync(shellRoot, { withFileTypes: true })) {
          if (!entry.isDirectory()) continue;
          for (const name of ['chrome-headless-shell', 'headless_shell']) {
            const candidate = path.join(shellRoot, entry.name, name);
            if (fs.existsSync(candidate)) executablePaths.push(candidate);
          }
        }
      }
    }
  }
  if (browserName === 'webkit') {
    const cacheRoot = path.dirname(browserExecutable);
    const runtimeCandidates = platform === 'darwin'
      ? [
        path.join(cacheRoot, 'Playwright.app', 'Contents', 'MacOS', 'Playwright'),
        path.join(cacheRoot, 'WebKitBuild', 'Release', 'Playwright.app', 'Contents', 'MacOS', 'Playwright'),
      ]
      : platform === 'linux'
        ? [
          path.join(cacheRoot, 'minibrowser-wpe', 'MiniBrowser'),
          path.join(cacheRoot, 'MiniBrowser'),
          path.join(cacheRoot, 'WebKitBuild', 'WPE', 'Release', 'bin', 'MiniBrowser'),
        ]
        : [];
    const installedRuntimes = runtimeCandidates.filter(candidate => {
      try { return fs.statSync(candidate).isFile(); } catch { return false; }
    });
    if (!installedRuntimes.length) {
      throw new Error('Playwright WebKit launcher has no selected headless runtime executable in its browser cache');
    }
    executablePaths.push(...installedRuntimes);
  }
  return [...new Set(executablePaths.map(candidate => fs.realpathSync(candidate)))];
}

export function validateSupervisorReport(report, browserName, title, failed) {
  const specs = [];
  const visit = suites => {
    for (const suite of suites) {
      specs.push(...(suite.specs || []));
      visit(suite.suites || []);
    }
  };
  visit(report.suites);
  const test = specs[0]?.tests?.[0];
  const result = test?.results?.[0];
  if (report.stats.expected !== (failed ? 0 : 1) || report.stats.unexpected !== (failed ? 1 : 0) ||
      report.stats.skipped !== 0 || report.stats.flaky !== 0 || report.errors.length !== 0 ||
      specs.length !== 1 || specs[0].title !== title || specs[0].tests.length !== 1 ||
      test.projectName !== browserName || test.results.length !== 1 ||
      test.status !== (failed ? 'unexpected' : 'expected') || result.status !== (failed ? 'failed' : 'passed')) {
    throw new Error('Supervisor report does not contain exactly the intended test result');
  }
  if (failed && (!result.error?.message.includes('CONTROLLED_FAILURE_INTENTIONAL_MISMATCH') ||
      !result.error.message.includes('toHaveText'))) {
    throw new Error('Controlled failure did not arise from the intended text assertion');
  }
}

export async function runPlaywrightSupervisor(browserName, scratchDir, serverOrigin) {
  const nodeBin = process.execPath;
  const packageRoot = process.env.APG_PLAYWRIGHT_PACKAGE_ROOT || path.resolve(scratchDir, 'node_modules');
  let cliPath = path.resolve(scratchDir, 'node_modules/@playwright/test/cli.js');
  if (!fs.existsSync(cliPath)) {
    cliPath = path.resolve(packageRoot, 'node_modules/@playwright/test/cli.js');
  }
  if (!fs.existsSync(cliPath)) {
    throw new Error(`Playwright Test CLI not found at ${cliPath}`);
  }
  let browserExecutable;
  try { browserExecutable = createRequire(cliPath)('playwright')[browserName]?.executablePath(); }
  catch (error) { throw new Error(`Playwright executable discovery failed for ${browserName}: ${error.message}`, { cause: error }); }
  if (typeof browserExecutable !== 'string' || !path.isAbsolute(browserExecutable)) {
    throw new Error(`Playwright did not provide an absolute executable for ${browserName}`);
  }
  const browserExecutables = selectedBrowserExecutables(browserName, browserExecutable);

  const nodeModulesPath = path.resolve(packageRoot, 'node_modules');
  const baseEnv = Object.assign({}, process.env, {
    APG_SERVER_ORIGIN: serverOrigin,
    NODE_PATH: nodeModulesPath,
    PLAYWRIGHT_BROWSERS_PATH: process.env.PLAYWRIGHT_BROWSERS_PATH,
    NO_COLOR: '1',
  });

  const testResultsDir = path.join(scratchDir, 'test-results');

  // Clean test-results before runs
  if (fs.existsSync(testResultsDir)) {
    fs.rmSync(testResultsDir, { recursive: true, force: true });
  }

  // Phase 1: Pass run - verify pass artifacts are ABSENT
  let passOutput;
  const passStarted = performance.now();
  try {
    const result = await runControlledSupervisor(nodeBin,
      [cliPath, 'test', '--config=playwright.config.js', '-g', 'supervisor-pass', `--project=${browserName}`, '--reporter=json'], {
        cwd: scratchDir, env: baseEnv, label: `Supervisor pass ${browserName}`,
    });
    if (result.code !== 0 || result.signal !== null) throw new Error(`Unexpected controlled pass exit ${result.code}/${result.signal}. ${result.stderr}`);
    passOutput = result.stdout;
  } catch (caught) {
    throw new Error(`Supervisor pass test failed for ${browserName}: ${caught.message}`, { cause: caught });
  }
  const passRunMs = performance.now() - passStarted;
  const passReport = JSON.parse(passOutput);
  validateSupervisorReport(passReport, browserName, 'supervisor-pass', false);

  let passArtifactsAbsent = true;
  if (fs.existsSync(testResultsDir)) {
    const checkDir = (dir) => {
      for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          checkDir(full);
        } else if (entry.name.endsWith('.png') || entry.name.endsWith('.zip')) {
          passArtifactsAbsent = false;
        }
      }
    };
    checkDir(testResultsDir);
  }
  if (!passArtifactsAbsent) {
    throw new Error('Pass run generated retention artifacts unexpectedly');
  }

  // Phase 2: Controlled Fail run - verify exact failed status and retention of screenshot and trace
  const failStarted = performance.now();
  const failed = await runControlledSupervisor(nodeBin,
    [cliPath, 'test', '--config=playwright.config.js', '-g', 'supervisor-fail', `--project=${browserName}`, '--reporter=json'], {
      cwd: scratchDir, env: baseEnv, label: `Supervisor controlled failure ${browserName}`,
  });
  const failRunMs = performance.now() - failStarted;

  if (failed.code !== 1 || failed.signal !== null) throw new Error('Controlled failure exit must be exactly 1');
  const report = JSON.parse(failed.stdout);
  validateSupervisorReport(report, browserName, 'supervisor-fail', true);

  // Verify retained failure artifacts in test-results
  let failedScreenshotFound = false;
  let failedTraceFound = false;
  if (fs.existsSync(testResultsDir)) {
    const scanDir = (dir) => {
      for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          scanDir(full);
        } else {
          const stat = fs.statSync(full);
          if (stat.size > 0) {
            if (entry.name.endsWith('.png')) failedScreenshotFound = true;
            if (entry.name.endsWith('.zip')) failedTraceFound = true;
          }
        }
      }
    };
    scanDir(testResultsDir);
  }
  if (!failedScreenshotFound || !failedTraceFound) {
    throw new Error(`Controlled failure artifacts missing: screenshot=${failedScreenshotFound}, trace=${failedTraceFound}`);
  }

  // Phase 3: Actual SIGINT interruption
  if (fs.existsSync(testResultsDir)) {
    fs.rmSync(testResultsDir, { recursive: true, force: true });
  }

  const signalFile = path.join(scratchDir, 'ready.signal');
  if (fs.existsSync(signalFile)) fs.unlinkSync(signalFile);

  const interruptEnv = Object.assign({}, baseEnv, { APG_SIGNAL_FILE: signalFile });
  interruptEnv.APG_BROWSER_NAME = browserName;
  interruptEnv.APG_BROWSER_EXECUTABLES = JSON.stringify(browserExecutables);
  interruptEnv.APG_INTERRUPT_HOLD_MS = '70000';
  const child = spawn(
    nodeBin,
    [cliPath, 'test', '--config=playwright.config.js', '-g', 'supervisor-interrupt', `--project=${browserName}`],
    {
      cwd: scratchDir,
      env: interruptEnv,
      detached: true,
      stdio: ['ignore', 'pipe', 'pipe'],
    }
  );

  const interruptionDeadlineMs = deriveInterruptionMs({ passRunMs, failRunMs });
  const interruption = await interruptReadyRunner(child, signalFile, {
    browserName,
    browserExecutables,
    interruptionMs: interruptionDeadlineMs,
    readinessMs: interruptionDeadlineMs,
    timingEvidence: {
      pass_run_ms: Math.round(passRunMs),
      fail_run_ms: Math.round(failRunMs),
      interruption_deadline_ms: interruptionDeadlineMs,
      readiness_deadline_ms: interruptionDeadlineMs,
      controlled_run_deadline_ms: CONTROLLED_RUN_MS,
    },
  });

  return [
    { name: 'controlled_failure_status_exact', passed: true },
    { name: 'pass_artifacts_absent', passed: true },
    { name: 'failed_artifacts_retained', passed: true },
    { name: 'child_readiness_signaled', passed: true },
    {
      name: 'sigint_interruption_exit_130',
      passed: true,
      pass_run_ms: Math.round(passRunMs),
      fail_run_ms: Math.round(failRunMs),
      interruption_deadline_ms: interruptionDeadlineMs,
      readiness_deadline_ms: interruptionDeadlineMs,
      controlled_run_deadline_ms: CONTROLLED_RUN_MS,
      sigint_to_exit_ms: interruption.sigintToExitMs,
      captured_process_count: interruption.capturedProcessCount,
    },
    { name: 'browser_worker_cleanup_observed', passed: true },
  ];
}

// Signal the runner that owns Playwright teardown, rather than concurrently
// interrupting its workers and browser transports. Group signals are reserved
// for failed-run cleanup; a cleanup kill can never satisfy the exit-130 check.
export async function interruptReadyRunner(child, signalFile, {
  browserName = 'chromium', browserExecutables, readinessMs = 15000, interruptionMs = 15000, cleanupMs = 5000,
  signalGroup = (pid, signal) => process.kill(pid, signal),
  signalOwnedProcess = (pid, signal) => process.kill(pid, signal),
  processSnapshot = readProcessSnapshot,
  timingEvidence = {},
} = {}) {
  if (!['chromium', 'firefox', 'webkit'].includes(browserName)) throw new TypeError('Unsupported selected browser');
  if (!Array.isArray(browserExecutables) || !browserExecutables.length ||
      browserExecutables.some(executable => typeof executable !== 'string' || !path.isAbsolute(executable))) {
    throw new TypeError('browserExecutables must contain absolute selected-browser executable paths');
  }
  for (const [name, value] of Object.entries({ readinessMs, interruptionMs, cleanupMs })) {
    if (!Number.isFinite(value) || value <= 0) throw new TypeError(`${name} must be a finite positive number`);
  }
  if (cleanupMs > 5000) throw new RangeError('cleanupMs must not exceed 5000ms');
  if (readinessMs > 45000 || interruptionMs > 45000) throw new RangeError('readiness and interruption must not exceed 45000ms');
  let stdout = '';
  let stderr = '';
  let terminal;
  let childError;
  let capturedOwned = [];
  let sigintToExitMs = null;
  let resolveExit;
  const exited = new Promise(resolve => { resolveExit = resolve; });
  const onExit = (code, signal) => { terminal = { code, signal }; resolveExit(terminal); };
  const onError = error => {
    childError = error;
    // A failed spawn has no child to reap. Other errors do not prove exit.
    if (!child.pid) { terminal = { error }; resolveExit(terminal); }
  };
  const onStdout = chunk => { stdout += chunk.toString(); };
  const onStderr = chunk => { stderr += chunk.toString(); };
  child.once('exit', onExit);
  child.on('error', onError);
  if (child.exitCode != null || child.signalCode != null) onExit(child.exitCode, child.signalCode);
  child.stdout?.on('data', onStdout);
  child.stderr?.on('data', onStderr);
  const alive = () => {
    if (!child.pid) return false;
    try { signalGroup(-child.pid, 0); return true; }
    catch (error) {
      if (error.code === 'ESRCH') return false;
      throw new Error(`group probe: ${error.message}`, { cause: error });
    }
  };
  const killGroup = () => {
    if (!child.pid) return;
    try { signalGroup(-child.pid, 'SIGKILL'); }
    catch (error) {
      if (error.code !== 'ESRCH') throw new Error(`group SIGKILL: ${error.message}`, { cause: error });
    }
  };
  const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
  const waitExit = async deadline => {
    if (terminal) return terminal;
    let timer;
    try {
      return await Promise.race([
        exited,
        new Promise(resolve => { timer = setTimeout(() => resolve(null), Math.max(0, deadline - performance.now())); }),
      ]);
    } finally { clearTimeout(timer); }
  };
  const killCaptured = snapshot => {
    const failures = [];
    if (!snapshot) return failures;
    let live;
    try { live = liveIdentityRows(snapshot, capturedOwned); }
    catch (error) { return [`owned identity cleanup refused: ${error.message}`]; }
    for (const row of live) {
      try { signalOwnedProcess(row.pid, 'SIGKILL'); }
      catch (error) {
        if (error.code !== 'ESRCH') failures.push(`owned PID ${row.pid} SIGKILL: ${error.message}`);
      }
    }
    return failures;
  };
  const onParentExit = () => {
    try {
      if (processSnapshot === readProcessSnapshot && capturedOwned.length) {
        const snapshot = runPsSnapshotSync();
        for (const row of liveIdentityRows(snapshot, capturedOwned)) {
          try { process.kill(row.pid, 'SIGKILL'); } catch { /* Parent-exit cleanup is best effort. */ }
        }
      }
    } catch { /* The owned process group remains the bounded fallback. */ }
    try { killGroup(); } catch { /* Parent-exit cleanup is best effort. */ }
    try { fs.rmSync(signalFile, { force: true }); } catch { /* Process exit is already in progress. */ }
  };
  const onParentTermination = () => { process.exit(143); };
  process.once('SIGTERM', onParentTermination);
  process.once('exit', onParentExit);
  let cleanupDeadline;
  try {
    const deadline = performance.now() + readinessMs;
    while (!fs.existsSync(signalFile) && performance.now() < deadline && !terminal && !childError) await pause(20);
    if (childError) throw childError;
    if (terminal) throw new Error('Child exited before readiness');
    if (!fs.existsSync(signalFile)) throw new Error('Child failed to signal readiness');
    const ready = parseReadiness(signalFile, browserName, browserExecutables);
    const readinessSnapshot = await processSnapshot();
    try { capturedOwned = ownedDescendants(readinessSnapshot, child.pid, browserExecutables, ready.pid); }
    catch (error) {
      if (Array.isArray(error.ownedDescendants)) capturedOwned = error.ownedDescendants;
      throw error;
    }
    const started = performance.now();
    const delivered = child.kill('SIGINT');
    if (childError) throw childError;
    if (!delivered) throw new Error('SIGINT delivery to Playwright runner failed');
    const result = await waitExit(started + interruptionMs);
    if (!result) throw new Error(`Supervisor runner interruption timed out after ${Math.round(performance.now() - started)}ms`);
    if (result.error) throw result.error;
    sigintToExitMs = Math.round(performance.now() - started);
    if (result.code !== 130 || result.signal !== null) {
      throw new Error(`Expected runner interruption exit 130, got code=${result.code}, signal=${result.signal}`);
    }
    cleanupDeadline = performance.now() + cleanupMs;
    while (true) {
      const afterExit = await processSnapshot();
      const survivors = liveIdentityRows(afterExit, capturedOwned);
      if (!survivors.length && !alive()) break;
      const remaining = cleanupDeadline - performance.now();
      if (remaining <= 0) {
        const survivorText = survivors.map(row => `${row.kind}:${row.pid}`).join(',');
        throw new Error(`Known browser or worker descendants survived SIGINT interruption${survivorText ? `: ${survivorText}` : ''}`);
      }
      await pause(Math.min(50, remaining));
    }
    return { sigintToExitMs, capturedProcessCount: capturedOwned.length };
  } catch (error) {
    const failures = [];
    let diagnosticSnapshot;
    let diagnosticSnapshotError;
    try { diagnosticSnapshot = await processSnapshot(); }
    catch (snapshotError) { diagnosticSnapshotError = snapshotError; }
    const diagnostics = {
      process_tree: diagnosticSnapshot
        ? processTreeDiagnostic(diagnosticSnapshot, child.pid, capturedOwned, browserExecutables)
        : [],
      process_snapshot_error: diagnosticSnapshotError?.message || null,
      load_average: os.loadavg(),
      available_parallelism: typeof os.availableParallelism === 'function' ? os.availableParallelism() : os.cpus().length,
      timing: { ...timingEvidence, sigint_to_exit_ms: sigintToExitMs },
    };
    const diagnosticText = `; failure diagnostics: ${JSON.stringify(diagnostics)}`;
    if (diagnosticSnapshotError) failures.push(`pre-cleanup process snapshot: ${diagnosticSnapshotError.message}`);
    failures.push(...killCaptured(diagnosticSnapshot));
    cleanupDeadline ??= performance.now() + cleanupMs;
    try { killGroup(); } catch (cleanupError) { failures.push(cleanupError.message); }
    // Node's exit observation reaps the directly owned child before a group
    // probe can encounter a zombie-only group. ESRCH alone is not reaping.
    if (!await waitExit(cleanupDeadline)) failures.push('child exit deadline exceeded');
    while (true) {
      try {
        const afterCleanup = await processSnapshot();
        const survivors = liveIdentityRows(afterCleanup, capturedOwned);
        if (!survivors.length && !alive()) break;
        const remaining = cleanupDeadline - performance.now();
        if (remaining <= 0) {
          if (survivors.length) failures.push(`owned processes survived hard cleanup: ${survivors.map(row => row.pid).join(',')}`);
          else failures.push('process group survived hard cleanup');
          break;
        }
      } catch (cleanupError) {
        failures.push(`post-cleanup process snapshot: ${cleanupError.message}`);
        break;
      }
      await pause(Math.min(50, Math.max(0, cleanupDeadline - performance.now())));
    }
    const cleanup = failures.length ? `; cleanup failed: ${failures.join('; ')}` : '';
    throw new Error(`${error.message}${diagnosticText}${cleanup}. STDOUT:\n${stdout}\nSTDERR:\n${stderr}`, { cause: error });
  } finally {
    process.removeListener('SIGTERM', onParentTermination);
    process.removeListener('exit', onParentExit);
    child.removeListener('exit', onExit);
    child.removeListener('error', onError);
    child.stdout?.removeListener('data', onStdout);
    child.stderr?.removeListener('data', onStderr);
    if (fs.existsSync(signalFile)) fs.unlinkSync(signalFile);
  }
}
