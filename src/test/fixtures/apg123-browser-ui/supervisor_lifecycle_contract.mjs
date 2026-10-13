import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import fs from 'node:fs';
import path from 'node:path';
import { deriveInterruptionMs, interruptReadyRunner, parseProcessSnapshot } from './supervisor_runner.mjs';

const scratch = process.argv[2];
const outcomes = [];
const runnerPid = 424242;
const workerPid = 424243;
const browserPid = 424244;
const workerCommand = '/repo/node_modules/@playwright/test/cli.js test-worker';
const browserCommand = '/cache/chromium/chrome --no-sandbox';
const row = (pid, ppid, command, state = 'S') => ({
  pid, ppid, state, started: 'Mon Oct 12 12:00:00 2026', command,
});

assert.equal(deriveInterruptionMs({ passRunMs: 1000, failRunMs: 10000 }), 15000);
assert.equal(deriveInterruptionMs({ passRunMs: 0, failRunMs: 10000.1 }), 15001);
assert.equal(deriveInterruptionMs({ passRunMs: 20000, failRunMs: 10000 }), 30000);
assert.equal(deriveInterruptionMs({ passRunMs: 40000, failRunMs: 10000 }), 45000);
for (const input of [
  { passRunMs: -1, failRunMs: 0 },
  { passRunMs: 0, failRunMs: Infinity },
  { passRunMs: NaN, failRunMs: 0 },
]) assert.throws(() => deriveInterruptionMs(input), /finite non-negative/);
outcomes.push({ mode: 'derived-deadline-bounds-and-validation', passed: true });

async function runCase(mode, { delayMs = 5, interruptionMs = 160, cleanupMs = 80, browserName = 'chromium' } = {}) {
  const readyPath = path.join(scratch, `${mode}.signal`);
  const browserExecutable = mode === 'browser-space-path'
    ? '/cache/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'
    : mode === 'webkit-script-launcher'
      ? '/cache/webkit-2336/pw_run.sh'
      : browserCommand.split(' ')[0];
  const browserExecutables = mode === 'webkit-script-launcher'
    ? ['/cache/webkit-2336/Playwright.app/Contents/MacOS/Playwright']
    : [browserExecutable];
  if (!['already-exited', 'spawn-error'].includes(mode)) {
    fs.writeFileSync(readyPath, JSON.stringify({ pid: workerPid, browserName, browserExecutables }));
  }
  const events = [];
  let rows = [
    row(runnerPid, 400000, '/node /repo/node_modules/@playwright/test/cli.js test'),
    row(workerPid, runnerPid, workerCommand),
    ...(mode === 'webkit-script-launcher'
      ? [
        row(browserPid, workerPid, '/bin/bash /cache/webkit-2336/pw_run.sh --headless'),
        row(browserPid + 1, browserPid, `${browserExecutables[0]} --headless`),
      ]
      : [row(browserPid, workerPid, mode === 'missing-browser-role'
        ? '/usr/bin/unrelated-helper --owned'
        : mode === 'browser-space-path'
        ? `${browserExecutable} --no-sandbox` : browserCommand)]),
  ];
  if (mode === 'unrelated-malformed') rows.push(...parseProcessSnapshot('999999 1 Z unavailable\n'));
  if (mode === 'owned-malformed') rows[1] = parseProcessSnapshot(`${workerPid} ${runnerPid} S unavailable\n`)[0];
  let groupAlive = true;
  let reaped = false;
  let exitTimer;
  let snapshots = 0;
  const child = new EventEmitter();
  child.pid = mode === 'spawn-error' ? undefined : runnerPid;
  child.exitCode = mode === 'already-exited' ? 1 : null;
  child.signalCode = null;
  child.stdout = new EventEmitter();
  child.stderr = new EventEmitter();
  child.kill = signal => {
    assert.equal(signal, 'SIGINT');
    events.push('SIGINT');
    if (mode === 'sigint-not-delivered') {
      reaped = true;
      rows = [];
      groupAlive = false;
      events.push('exit:130-before-delivery');
      child.emit('exit', 130, null);
      return false;
    }
    if (mode === 'snapshot-failure' || mode === 'reap-first' || mode === 'probe-denied' ||
        mode === 'kill-denied' || mode === 'no-exit' || mode === 'forced-130' || mode === 'cleanup-only-130') return true;
    if (mode === 'sigint-error') {
      child.emit('error', new Error('direct SIGINT denied'));
      return false;
    }
    const exit = () => {
      reaped = true;
      if (mode === 'detached-descendant' || mode === 'descendant' || mode === 'process-title-changed' || mode === 'zombie-survivor') {
        const browser = row(browserPid, 1, mode === 'process-title-changed' ? '/renamed/chromium-instance --no-sandbox' : browserCommand,
          mode === 'zombie-survivor' ? 'Z' : 'S');
        rows = [browser];
        groupAlive = false;
      } else if (mode === 'pid-reused') {
        rows = [row(browserPid, 1, '/usr/bin/unrelated-helper', 'S')];
        rows[0].started = 'Mon Oct 12 12:01:00 2026';
        groupAlive = false;
      } else if (mode === 'captured-malformed') {
        rows = parseProcessSnapshot(`${browserPid} 1 S unavailable\n`);
        groupAlive = false;
      } else {
        rows = [];
        groupAlive = false;
      }
      const code = mode === 'wrong-exit' ? 0 : 130;
      events.push(`exit:${code}`);
      child.emit('exit', code, null);
    };
    if (mode === 'timeout' || mode === 'cleanup-only-130') return true;
    exitTimer = setTimeout(exit, delayMs);
    return true;
  };
  const processSnapshot = async () => {
    snapshots += 1;
    events.push(`snapshot:${snapshots}`);
    if (mode === 'snapshot-failure' && snapshots === 1) throw new Error('synthetic ps denied');
    if (mode === 'missing-browser-role' && snapshots === 2) {
      rows = [row(browserPid, 1, '/usr/bin/unrelated-helper --owned')];
    }
    return rows.map(item => ({ ...item }));
  };
  const signalGroup = (pid, signal) => {
    if (!child.pid) throw Object.assign(new Error('no child process group'), { code: 'ESRCH' });
    assert.equal(pid, -runnerPid);
    if (signal === 0) {
      events.push('group-probe');
      if (mode === 'probe-denied') throw Object.assign(new Error('kill EPERM'), { code: 'EPERM' });
      if (mode === 'reap-first' && !reaped) throw Object.assign(new Error('transient kill EPERM'), { code: 'EPERM' });
      if (groupAlive) return true;
      throw Object.assign(new Error('kill ESRCH'), { code: 'ESRCH' });
    }
    assert.equal(signal, 'SIGKILL');
    events.push('group-SIGKILL');
    if (mode === 'kill-denied') throw Object.assign(new Error('group SIGKILL EPERM'), { code: 'EPERM' });
    if (mode === 'no-exit') return true;
    groupAlive = false;
    if (!reaped) {
      exitTimer = setTimeout(() => {
        reaped = true;
        rows = [];
        if (mode === 'forced-130') {
          events.push('exit:130-cleanup');
          child.emit('exit', 130, null);
        } else {
          events.push('exit:SIGKILL');
          child.emit('exit', null, 'SIGKILL');
        }
      }, 2);
    }
    return true;
  };
  const signalOwnedProcess = (pid, signal) => {
    assert.equal(signal, 'SIGKILL');
    events.push(`owned-SIGKILL:${pid}`);
    rows = rows.filter(item => item.pid !== pid);
  };
  const listeners = ['SIGTERM', 'exit'].map(name => process.listenerCount(name));
  const childPid = child.pid;
  const started = performance.now();
  let result;
  let failure;
  try {
    if (mode === 'reap-first') {
      assert.throws(() => signalGroup(-runnerPid, 0), { code: 'EPERM' });
      events.length = 0;
    }
    const pending = interruptReadyRunner(child, readyPath, {
      browserName,
      browserExecutables,
      readinessMs: 50,
      interruptionMs,
      cleanupMs,
      signalGroup,
      signalOwnedProcess,
      processSnapshot,
      timingEvidence: { pass_run_ms: 4, fail_run_ms: 8, interruption_deadline_ms: interruptionMs },
    });
    if (mode === 'spawn-error') {
      setTimeout(() => child.emit('error', Object.assign(new Error('spawn ENOENT'), { code: 'ENOENT' })), 1);
    }
    result = await pending;
  } catch (error) { failure = error.message; }
  finally {
    clearTimeout(exitTimer);
    fs.rmSync(readyPath, { force: true });
  }
  assert.ok(performance.now() - started < 1000, `${mode}: bounded lifecycle`);
  assert.equal(fs.existsSync(readyPath), false);
  assert.deepEqual(['SIGTERM', 'exit'].map(name => process.listenerCount(name)), listeners);
  for (const event of ['exit', 'error']) assert.equal(child.listenerCount(event), 0);
  assert.equal(child.stdout.listenerCount('data'), 0);
  assert.equal(child.stderr.listenerCount('data'), 0);
  assert.equal(child.pid, childPid);
  return { result, failure, events, snapshots };
}

const success = await runCase('proper-disappearance');
assert.equal(success.failure, undefined, success.failure);
assert.ok(success.events.indexOf('snapshot:1') < success.events.indexOf('SIGINT'), 'custody snapshot precedes SIGINT');
assert.ok(success.result.sigintToExitMs >= 0);
assert.equal(success.result.capturedProcessCount, 2);
assert.equal(success.events.some(event => event.includes('SIGKILL')), false, 'success never uses cleanup kill');
outcomes.push({ mode: 'proper-descendant-disappearance', passed: true });

const unrelatedMalformed = await runCase('unrelated-malformed');
assert.equal(unrelatedMalformed.failure, undefined, unrelatedMalformed.failure);
outcomes.push({ mode: 'unrelated-malformed-row-does-not-block-custody', passed: true });

const ownedMalformed = await runCase('owned-malformed');
assert.match(ownedMalformed.failure, /invalid owned process identity/);
assert.equal(ownedMalformed.events.includes('SIGINT'), false);
outcomes.push({ mode: 'owned-malformed-row-fails-before-signal', passed: true });

const capturedMalformed = await runCase('captured-malformed');
assert.match(capturedMalformed.failure, /cannot establish a captured process identity/);
assert.match(capturedMalformed.failure, /owned identity cleanup refused/);
assert.equal(capturedMalformed.events.some(event => event.startsWith('owned-SIGKILL')), false);
outcomes.push({ mode: 'unreadable-captured-identity-cannot-prove-disappearance', passed: true });

const slow = await runCase('slow-graceful', { delayMs: 45, interruptionMs: 180 });
assert.equal(slow.failure, undefined, slow.failure);
assert.ok(slow.result.sigintToExitMs >= 35, `slow exit timing=${slow.result.sigintToExitMs}`);
outcomes.push({ mode: 'slow-graceful-exit-130', passed: true, sigint_to_exit_ms: slow.result.sigintToExitMs });

const notDelivered = await runCase('sigint-not-delivered');
assert.match(notDelivered.failure, /SIGINT delivery to Playwright runner failed/);
assert.ok(notDelivered.events.includes('exit:130-before-delivery'));
outcomes.push({ mode: 'exit-130-without-signal-delivery-fails', passed: true });

const detached = await runCase('detached-descendant', { delayMs: 4, cleanupMs: 60 });
assert.match(detached.failure, /Known browser or worker descendants survived SIGINT interruption/);
assert.ok(detached.events.includes(`owned-SIGKILL:${browserPid}`), 'cleanup revalidates and kills only captured browser identity');
assert.ok(detached.events.indexOf('snapshot:2') < detached.events.indexOf(`owned-SIGKILL:${browserPid}`), 'post-exit snapshot precedes cleanup kill');
outcomes.push({ mode: 'detached-descendant-survives-130-fails', passed: true });

const changedTitle = await runCase('process-title-changed', { delayMs: 4, cleanupMs: 60 });
assert.match(changedTitle.failure, /Known browser or worker descendants survived SIGINT interruption/);
assert.ok(changedTitle.events.includes(`owned-SIGKILL:${browserPid}`), 'PID/start identity survives process-title changes');
outcomes.push({ mode: 'renamed-process-remains-owned', passed: true });

const zombie = await runCase('zombie-survivor', { delayMs: 4, cleanupMs: 60 });
assert.match(zombie.failure, /Known browser or worker descendants survived SIGINT interruption/);
outcomes.push({ mode: 'zombie-descendant-is-not-absent', passed: true });

const reusedPid = await runCase('pid-reused', { delayMs: 4 });
assert.equal(reusedPid.failure, undefined, reusedPid.failure);
assert.equal(reusedPid.events.some(event => event.startsWith(`owned-SIGKILL:${browserPid}`)), false);
outcomes.push({ mode: 'reused-pid-with-new-start-identity-is-ignored', passed: true });

const browserSpacePath = await runCase('browser-space-path', { delayMs: 4 });
assert.equal(browserSpacePath.failure, undefined, browserSpacePath.failure);
outcomes.push({ mode: 'selected-browser-path-with-spaces', passed: true });

const webkitLauncher = await runCase('webkit-script-launcher', { delayMs: 4, browserName: 'webkit' });
assert.equal(webkitLauncher.failure, undefined, webkitLauncher.failure);
assert.equal(webkitLauncher.result.capturedProcessCount, 3, 'captures worker, script launcher, and exact WebKit runtime');
assert.equal(webkitLauncher.events.some(event => event.includes('SIGKILL')), false);
outcomes.push({ mode: 'webkit-script-launcher-with-selected-runtime-descendant', passed: true });

const wrongExit = await runCase('wrong-exit', { delayMs: 4 });
assert.match(wrongExit.failure, /Expected runner interruption exit 130/);
assert.ok(wrongExit.events.indexOf('snapshot:2') < wrongExit.events.indexOf('group-SIGKILL'), 'failure snapshot precedes cleanup kill');
outcomes.push({ mode: 'wrong-exit-diagnostic-before-cleanup', passed: true });

const timeout = await runCase('timeout', { interruptionMs: 35, cleanupMs: 60 });
assert.match(timeout.failure, /interruption timed out/);
assert.match(timeout.failure, /process_tree/);
assert.match(timeout.failure, /available_parallelism/);
assert.match(timeout.failure, /interruption_deadline_ms/);
assert.ok(timeout.events.indexOf('snapshot:2') < timeout.events.indexOf('group-SIGKILL'), 'timeout snapshot precedes cleanup kill');
outcomes.push({ mode: 'timeout-diagnostics-before-cleanup', passed: true });

const snapshotFailure = await runCase('snapshot-failure');
assert.match(snapshotFailure.failure, /synthetic ps denied/);
assert.equal(snapshotFailure.events.includes('SIGINT'), false, 'snapshot failure must fail closed before SIGINT');
outcomes.push({ mode: 'snapshot-failure-is-closed', passed: true });

const missingBrowser = await runCase('missing-browser-role', { cleanupMs: 60 });
assert.ok(missingBrowser.failure.startsWith('process snapshot did not capture the selected browser executable'),
  'the original missing-browser proof failure remains primary');
assert.ok(missingBrowser.events.includes(`owned-SIGKILL:${browserPid}`), 'detached discovered identity is cleaned after proof failure');
assert.ok(missingBrowser.events.indexOf('snapshot:2') < missingBrowser.events.indexOf(`owned-SIGKILL:${browserPid}`),
  'secondary snapshot revalidates the detached identity before cleanup');
outcomes.push({ mode: 'missing-browser-proof-retains-detached-cleanup-identities', passed: true });

const cleanupOnly = await runCase('cleanup-only-130', { interruptionMs: 30, cleanupMs: 60 });
assert.match(cleanupOnly.failure, /interruption timed out/);
assert.ok(cleanupOnly.events.includes('exit:SIGKILL'));
outcomes.push({ mode: 'cleanup-kill-cannot-satisfy-exit-130', passed: true });

const legacyCases = [
  ['reap-first', /interruption timed out/],
  ['probe-denied', /EPERM/],
  ['kill-denied', /EPERM/],
  ['descendant', /Known browser or worker descendants survived SIGINT interruption/],
  ['no-exit', /interruption timed out/],
  ['already-exited', /before readiness/],
  ['spawn-error', /spawn ENOENT/],
  ['sigint-error', /direct SIGINT denied/],
  ['forced-130', /interruption timed out/],
];
for (const [mode, expected] of legacyCases) {
  const result = await runCase(mode, { interruptionMs: 35, cleanupMs: 55 });
  assert.match(result.failure, expected, `${mode}: ${result.failure}`);
  if (mode === 'forced-130') assert.ok(result.events.includes('exit:130-cleanup'));
  outcomes.push({ mode: `retained-${mode}`, passed: true });
}

console.log(JSON.stringify(outcomes));
