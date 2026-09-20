import { execFile, spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

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
  try {
    passOutput = await new Promise((resolve, reject) => {
      execFile(
        nodeBin,
        [cliPath, 'test', '--config=playwright.config.js', '-g', 'supervisor-pass', `--project=${browserName}`, '--reporter=json'],
        { cwd: scratchDir, env: baseEnv },
        (err, stdout, stderr) => {
          if (err) return reject({ err, stdout, stderr });
          resolve(stdout);
        }
      );
    });
  } catch (caught) {
    const stdout = caught.stdout ? caught.stdout.toString() : '';
    const stderr = caught.stderr ? caught.stderr.toString() : '';
    throw new Error(`Supervisor pass test failed for ${browserName}:\nSTDOUT:\n${stdout}\nSTDERR:\n${stderr}`);
  }
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
  let failOutput = '';
  let failExit = null;
  try {
    await new Promise((resolve, reject) => {
      execFile(
        nodeBin,
        [cliPath, 'test', '--config=playwright.config.js', '-g', 'supervisor-fail', `--project=${browserName}`, '--reporter=json'],
        { cwd: scratchDir, env: baseEnv },
        (err, stdout, stderr) => {
          if (err) return reject({ err, stdout, stderr });
          resolve({ stdout, stderr });
        }
      );
    });
    throw new Error('Controlled fail test was expected to fail with non-zero exit code');
  } catch (caught) {
    if (caught.stdout) {
      failOutput = caught.stdout.toString();
      failExit = caught.err?.code;
    } else if (caught.err && caught.err.message && caught.err.message.includes('expected to fail')) {
      throw caught.err;
    }
  }

  const report = JSON.parse(failOutput);
  if (failExit !== 1) throw new Error('Controlled failure exit must be exactly 1');
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

  await interruptReadyRunner(child, signalFile);

  return [
    { name: 'controlled_failure_status_exact', passed: true },
    { name: 'pass_artifacts_absent', passed: true },
    { name: 'failed_artifacts_retained', passed: true },
    { name: 'child_readiness_signaled', passed: true },
    { name: 'sigint_interruption_exit_130', passed: true },
    { name: 'browser_worker_cleanup_observed', passed: true },
  ];
}

// Signal the runner that owns Playwright teardown, rather than concurrently
// interrupting its workers and browser transports. Group signals are reserved
// for failed-run cleanup; a cleanup kill can never satisfy the exit-130 check.
export async function interruptReadyRunner(child, signalFile, {
  readinessMs = 15000, interruptionMs = 15000, cleanupMs = 1000,
  signalGroup = (pid, signal) => process.kill(pid, signal),
} = {}) {
  let stdout = '';
  let stderr = '';
  let terminal;
  let childError;
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
  const waitDead = async deadline => {
    while (alive()) {
      const remaining = deadline - performance.now();
      if (remaining <= 0) return false;
      await pause(Math.min(20, remaining));
    }
    return true;
  };
  const onParentExit = () => {
    try { killGroup(); }
    finally { fs.rmSync(signalFile, { force: true }); }
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
    const started = performance.now();
    child.kill('SIGINT');
    if (childError) throw childError;
    const result = await waitExit(started + interruptionMs);
    if (!result) throw new Error(`Supervisor runner interruption timed out after ${Math.round(performance.now() - started)}ms`);
    if (result.error) throw result.error;
    if (result.code !== 130 || result.signal !== null) {
      throw new Error(`Expected runner interruption exit 130, got code=${result.code}, signal=${result.signal}`);
    }
    cleanupDeadline = performance.now() + cleanupMs;
    if (!await waitDead(cleanupDeadline)) throw new Error('Browser or worker processes survived SIGINT interruption');
  } catch (error) {
    cleanupDeadline ??= performance.now() + cleanupMs;
    const failures = [];
    try { killGroup(); } catch (cleanupError) { failures.push(cleanupError.message); }
    // Node's exit observation reaps the directly owned child before a group
    // probe can encounter a zombie-only group. ESRCH alone is not reaping.
    if (!await waitExit(cleanupDeadline)) failures.push('child exit deadline exceeded');
    else {
      try {
        if (!await waitDead(cleanupDeadline)) failures.push('process group survived hard cleanup');
      } catch (cleanupError) { failures.push(cleanupError.message); }
    }
    const cleanup = failures.length ? `; cleanup failed: ${failures.join('; ')}` : '';
    throw new Error(`${error.message}${cleanup}. STDOUT:\n${stdout}\nSTDERR:\n${stderr}`, { cause: error });
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
