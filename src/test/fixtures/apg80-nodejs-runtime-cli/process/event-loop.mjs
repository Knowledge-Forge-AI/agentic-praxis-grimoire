// APG80-FX-013 — scheduling order observed from an ECMAScript module entry.
// The paired CommonJS entry schedules the same work from a CommonJS entry point.
// Comparing the two is the point: a relative ordering claim is only meaningful
// with its exact scheduling context, module system, runtime version, and flags.

export function scheduleProbe(record) {
  setTimeout(() => record('timeout-0'), 0);
  setImmediate(() => record('immediate'));
  process.nextTick(() => record('next-tick'));
  queueMicrotask(() => record('microtask'));
  Promise.resolve().then(() => record('promise'));
  record('synchronous');
}

const trace = [];
scheduleProbe((label) => trace.push(label));
process.on('beforeExit', () => {
  console.log(JSON.stringify({ entryModuleSystem: 'esm', order: trace }));
});
