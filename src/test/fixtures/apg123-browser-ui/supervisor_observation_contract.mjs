import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import {
  CONTROLLED_RUN_MS, CONTROLLED_CLEANUP_MS, parseProcessSnapshot,
  readProcessSnapshot, publishReadiness, selectedBrowserExecutables,
  runControlledSupervisor,
} from './supervisor_runner.mjs';

const scratch = process.argv[2];
const outcomes = [];

// Sanitized, representative Darwin/Linux ps layouts; variable day spacing and
// command names containing spaces must preserve the same start-time identity.
const darwin = parseProcessSnapshot(' 101 1 Ss Mon Oct  5 12:00:00 2026 /cache/Google Chrome for Testing --headless\n');
const linux = parseProcessSnapshot('101 1 Sl Mon Oct 5 12:00:00 2026 /cache/Google Chrome for Testing --headless\r\n');
assert.equal(darwin[0].state, 'Ss');
assert.equal(linux[0].state, 'Sl');
assert.deepEqual(darwin[0], { ...linux[0], state: 'Ss' });
assert.equal(darwin[0].started, 'Mon Oct 5 12:00:00 2026');
assert.equal(darwin[0].command, '/cache/Google Chrome for Testing --headless');
assert.equal(darwin[0].invalid, null);
assert.throws(() => parseProcessSnapshot(''), /empty/);
assert.equal(parseProcessSnapshot('101 1 Z unavailable\n')[0].invalid, 'unrecognized ps fields');
assert.ok(parseProcessSnapshot('101 1 Z unavailable\n101 1 Z unavailable\n').every(row => row.invalid));
outcomes.push('portable-process-parser');

// Exercise the un-injected command/parser adapter using a source fixture ps.
// Actual operating-system ps access remains a hosted qualification boundary.
const bin = path.join(scratch, 'bin');
fs.mkdirSync(bin);
fs.writeFileSync(path.join(bin, 'ps'), `#!${process.execPath}
if (process.env.LC_ALL !== 'C' || process.argv.slice(2).join(' ') !== '-axo pid=,ppid=,stat=,lstart=,command=') process.exit(1);
console.log('101 1 Ss Mon Oct  5 12:00:00 2026 /synthetic/runner');
`, { mode: 0o700 });
const previousPath = process.env.PATH;
try {
  process.env.PATH = bin;
  const snapshot = await readProcessSnapshot();
  assert.equal(snapshot.length, 1);
  assert.equal(snapshot[0].pid, 101);
  assert.equal(snapshot[0].invalid, null);
} finally { process.env.PATH = previousPath; }
outcomes.push('source-ps-command-adapter');

const physical = path.join(scratch, 'cache');
const linked = path.join(scratch, 'linked-cache');
fs.mkdirSync(physical);
fs.symlinkSync(physical, linked, 'dir');
const file = relative => {
  const target = path.join(physical, relative);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, 'synthetic executable fixture\n');
  return fs.realpathSync(target);
};
const chromium = file('chromium-123/chrome-mac/Google Chrome for Testing');
const headless = file('chromium_headless_shell-123/chrome-headless-shell-mac/headless_shell');
assert.deepEqual(selectedBrowserExecutables('chromium', path.join(linked, 'chromium-123/chrome-mac/Google Chrome for Testing')),
  [chromium, headless]);
const firefox = file('firefox-456/firefox/firefox');
assert.deepEqual(selectedBrowserExecutables('firefox', path.join(linked, 'firefox-456/firefox/firefox')), [firefox]);
file('webkit-789/pw_run.sh');
const macRuntime = file('webkit-789/Playwright.app/Contents/MacOS/Playwright');
const linuxRuntime = file('webkit-789/minibrowser-wpe/MiniBrowser');
assert.deepEqual(selectedBrowserExecutables('webkit', path.join(linked, 'webkit-789/pw_run.sh'), 'darwin'), [macRuntime]);
assert.deepEqual(selectedBrowserExecutables('webkit', path.join(linked, 'webkit-789/pw_run.sh'), 'linux'), [linuxRuntime]);
file('webkit-999/pw_run.sh');
assert.throws(() => selectedBrowserExecutables('webkit', path.join(linked, 'webkit-999/pw_run.sh'), 'darwin'), /no selected headless runtime/);
outcomes.push('canonical-browser-cache-discovery');

const ready = path.join(scratch, 'atomic.signal');
publishReadiness(ready, { value: 1 });
assert.deepEqual(JSON.parse(fs.readFileSync(ready, 'utf8')), { value: 1 });
// A separate writer repeatedly publishes a large payload while this reader
// observes the final path. Atomic visibility is a real filesystem boundary.
const program = `import { publishReadiness } from ${JSON.stringify(new URL('./supervisor_runner.mjs', import.meta.url).href)};
for (let value = 2; value <= 30; value++) {
  publishReadiness(process.argv[1], { value, content: 'x'.repeat(65536) });
  await new Promise(resolve => setTimeout(resolve, 2));
}`;
const writer = spawn(process.execPath, ['--input-type=module', '-e', program, ready], { stdio: ['ignore', 'pipe', 'pipe'] });
let terminal;
let writerError;
writer.on('error', error => { writerError = error; });
const closed = new Promise(resolve => writer.once('close', code => { terminal = code; resolve(); }));
const until = performance.now() + 3000;
try {
  let observations = 0;
  while (terminal === undefined && !writerError && performance.now() < until) {
    const payload = JSON.parse(fs.readFileSync(ready, 'utf8'));
    assert.ok(Number.isInteger(payload.value));
    if (payload.content) { assert.equal(payload.content.length, 65536); observations++; }
    await new Promise(resolve => setTimeout(resolve, 1));
  }
  assert.ifError(writerError);
  assert.equal(terminal, 0, 'readiness publisher must close within the bound');
  assert.ok(observations > 0);
  assert.equal(JSON.parse(fs.readFileSync(ready, 'utf8')).value, 30);
  assert.equal(fs.existsSync(`${ready}.${writer.pid}.tmp`), false);
} finally {
  if (terminal === undefined && writer.pid) writer.kill('SIGKILL');
  let timer;
  try { await Promise.race([closed, new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('publisher reap deadline')), 1000); })]); }
  finally { clearTimeout(timer); }
}
outcomes.push('atomic-readiness-visibility');

assert.equal(CONTROLLED_RUN_MS, 30000);
assert.equal(CONTROLLED_CLEANUP_MS, 5000);
for (const code of [0, 1]) {
  const result = await runControlledSupervisor(process.execPath, ['-e', `console.log('controlled'); process.exit(${code});`],
    { cwd: scratch, env: process.env, label: 'synthetic controlled', timeoutMs: 2000 });
  assert.equal(result.code, code);
  assert.equal(result.signal, null);
  assert.equal(result.stdout.trim(), 'controlled');
}
await assert.rejects(runControlledSupervisor('/nonexistent/apg-fixture-node', [],
  { cwd: scratch, env: process.env, label: 'synthetic spawn', timeoutMs: 200 }), /child error:.*ENOENT/);
const childPidFile = path.join(scratch, 'controlled.pid');
const started = performance.now();
await assert.rejects(runControlledSupervisor(process.execPath,
  ['-e', "require('node:fs').writeFileSync(process.argv[1], String(process.pid)); setInterval(() => {}, 10);", childPidFile],
  { cwd: scratch, env: process.env, label: 'synthetic hang', timeoutMs: 300, cleanupMs: 500 }),
  /synthetic hang: controlled run timed out after 300ms; child_reaped=true/);
assert.ok(performance.now() - started < 2000);
const childPid = Number(fs.readFileSync(childPidFile, 'utf8'));
assert.throws(() => process.kill(-childPid, 0), { code: 'ESRCH' });
assert.throws(() => runControlledSupervisor(process.execPath, [],
  { cwd: scratch, env: process.env, timeoutMs: 30001 }), /at most 30000/);
outcomes.push('controlled-run-status-watchdog-and-reaping');

console.log(JSON.stringify(outcomes));
