import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import fs from 'node:fs';
import path from 'node:path';
import { interruptReadyRunner } from './supervisor_runner.mjs';

// A scoped group-signal adapter models the kernel boundary without changing
// process.kill globally. Child events model Node's direct-child observation.
const scratch = process.argv[2];
const denied = () => Object.assign(new Error('kill EPERM'), { code: 'EPERM' });
const absent = () => { throw Object.assign(new Error('kill ESRCH'), { code: 'ESRCH' }); };
const outcomes = [];
for (const mode of ['reap-first', 'probe-denied', 'kill-denied', 'descendant',
  'no-exit', 'already-exited', 'spawn-error', 'sigint-error', 'forced-130']) {
  const child = new EventEmitter();
  child.pid = mode === 'spawn-error' ? undefined : 424242;
  child.exitCode = mode === 'already-exited' ? 1 : null;
  child.signalCode = null;
  child.stdout = new EventEmitter();
  child.stderr = new EventEmitter();
  child.kill = signal => {
    assert.equal(signal, 'SIGINT');
    if (mode === 'sigint-error') child.emit('error', new Error('direct SIGINT denied'));
    return mode !== 'sigint-error';
  };
  const ready = path.join(scratch, mode + '.signal');
  if (!['already-exited', 'spawn-error'].includes(mode)) fs.writeFileSync(ready, 'ready');
  const events = [];
  let reaped = mode === 'already-exited';
  let exitTimer;
  const signalGroup = (pid, signal) => {
    assert.equal(pid, -424242);
    events.push(signal === 0 ? 'probe' : signal);
    if (signal === 'SIGKILL') {
      if (mode === 'kill-denied') throw denied();
      if (!reaped && mode !== 'no-exit') {
        exitTimer = setTimeout(() => {
          reaped = true;
          events.push('exit');
          child.emit('exit', mode === 'forced-130' ? 130 : null, mode === 'forced-130' ? null : 'SIGKILL');
        }, 10);
      }
      return;
    }
    assert.equal(signal, 0);
    if (!reaped || mode === 'probe-denied') throw denied();
    if (mode === 'descendant') return;
    return absent();
  };
  // The old kill/probe ordering deterministically sees a transient EPERM.
  if (mode === 'reap-first') assert.throws(() => signalGroup(-child.pid, 0), { code: 'EPERM' });
  events.length = 0;
  const parentListeners = ['SIGTERM', 'exit'].map(name => process.listenerCount(name));
  const started = performance.now();
  const pending = interruptReadyRunner(child, ready, {
    readinessMs: 40, interruptionMs: 10, cleanupMs: 80, signalGroup,
  });
  if (mode === 'spawn-error') child.emit('error', Object.assign(new Error('spawn ENOENT'), { code: 'ENOENT' }));
  let failure;
  try { await pending; } catch (error) { failure = error.message; }
  finally { clearTimeout(exitTimer); }
  assert.ok(failure, mode + ': failure must not become success');
  if (mode === 'reap-first') {
    assert.deepEqual(events, ['SIGKILL', 'exit', 'probe'], failure);
  }
  assert.ok(performance.now() - started < 500, mode + ': unbounded cleanup');
  assert.equal(fs.existsSync(ready), false);
  assert.deepEqual(['SIGTERM', 'exit'].map(name => process.listenerCount(name)), parentListeners);
  for (const event of ['exit', 'error']) assert.equal(child.listenerCount(event), 0);
  assert.equal(child.stdout.listenerCount('data'), 0);
  assert.equal(child.stderr.listenerCount('data'), 0);
  if (mode === 'already-exited') assert.match(failure, /before readiness/);
  else if (mode === 'spawn-error') assert.match(failure, /spawn ENOENT/);
  else if (mode === 'sigint-error') assert.match(failure, /direct SIGINT denied/);
  else assert.match(failure, /interruption timed out/);
  if (mode === 'reap-first') {
    assert.deepEqual(events, ['SIGKILL', 'exit', 'probe']);
    assert.doesNotMatch(failure, /cleanup failed/);
  } else if (mode === 'probe-denied') assert.match(failure, /cleanup failed.*group probe.*EPERM/s);
  else if (mode === 'kill-denied') assert.match(failure, /cleanup failed.*SIGKILL.*EPERM/s);
  else if (mode === 'descendant') assert.match(failure, /cleanup failed.*group.*survived/s);
  else if (mode === 'no-exit') {
    assert.match(failure, /cleanup failed.*child exit.*deadline/s);
    assert.equal(events.includes('probe'), false);
  }
  outcomes.push({ mode, events, failure: failure.split('. STDOUT:')[0] });
}
console.log(JSON.stringify(outcomes));
