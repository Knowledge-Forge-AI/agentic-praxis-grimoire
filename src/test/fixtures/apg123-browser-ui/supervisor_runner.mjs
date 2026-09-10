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

  let childStdout = '';
  let childStderr = '';
  if (child.stdout) {
    child.stdout.on('data', (chunk) => { childStdout += chunk.toString(); });
  }
  if (child.stderr) {
    child.stderr.on('data', (chunk) => { childStderr += chunk.toString(); });
  }

  const childPid = child.pid;
  const terminateChild = () => {
    try { process.kill(-childPid, 'SIGKILL'); } catch (error) {
      if (error.code !== 'ESRCH') throw error;
    }
  };
  // The Python outer timeout signals this parent; its detached runner group
  // must be closed before the parent exits as well.
  const terminateWithParent = () => { terminateChild(); process.exit(143); };
  process.once('SIGTERM', terminateWithParent);
  process.once('exit', terminateChild);
  const deadline = Date.now() + 15000;
  while (!fs.existsSync(signalFile) && Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, 50));
  }
  if (!fs.existsSync(signalFile)) {
    try { process.kill(-childPid, 'SIGKILL'); } catch (_) {}
    throw new Error('Child process failed to signal readiness within 15s');
  }

  // Send SIGINT to process group
  const sigintSentAt = Date.now();
  process.kill(-childPid, 'SIGINT');

  const interruptionResult = await new Promise((resolve) => {
    const timer = setTimeout(() => {
      const elapsed = Date.now() - sigintSentAt;
      try { process.kill(-childPid, 'SIGKILL'); } catch (_) {}
      resolve({ timedOut: true, elapsed });
    }, 15000);
    child.on('exit', (code, signal) => {
      clearTimeout(timer);
      const elapsed = Date.now() - sigintSentAt;
      resolve({ code, signal, timedOut: false, elapsed });
    });
  });

  if (interruptionResult.timedOut) {
    throw new Error(`Supervisor runner interruption timed out after ${interruptionResult.elapsed}ms. STDOUT:\n${childStdout}\nSTDERR:\n${childStderr}`);
  }

  const exitCode = interruptionResult.code !== null ? interruptionResult.code : interruptionResult.signal;
  if (exitCode !== 130) {
    throw new Error(`Expected runner interruption exit 130, got: ${exitCode}. STDOUT:\n${childStdout}\nSTDERR:\n${childStderr}`);
  }

  // Bounded check for process group death
  await new Promise((r) => setTimeout(r, 100));
  let pgSurvives = true;
  try {
    process.kill(-childPid, 0);
  } catch (err) {
    if (err.code === 'ESRCH') {
      pgSurvives = false;
    }
  }
  if (pgSurvives) {
    try { process.kill(-childPid, 'SIGKILL'); } catch (_) {}
    throw new Error('Browser or worker processes survived SIGINT interruption');
  }
  process.removeListener('SIGTERM', terminateWithParent);
  process.removeListener('exit', terminateChild);

  if (fs.existsSync(signalFile)) {
    fs.unlinkSync(signalFile);
  }

  return [
    { name: 'controlled_failure_status_exact', passed: true },
    { name: 'pass_artifacts_absent', passed: true },
    { name: 'failed_artifacts_retained', passed: true },
    { name: 'child_readiness_signaled', passed: true },
    { name: 'sigint_interruption_exit_130', passed: true },
    { name: 'browser_worker_cleanup_observed', passed: true },
  ];
}
