// APG80-FX-013 — the contrasting control for the module entry. The same five
// scheduling calls are made from a CommonJS entry point on the same runtime with
// the same flags, so any difference in observed order is attributable to the
// entry's module system alone.

const trace = [];

setTimeout(() => trace.push('timeout-0'), 0);
setImmediate(() => trace.push('immediate'));
process.nextTick(() => trace.push('next-tick'));
queueMicrotask(() => trace.push('microtask'));
Promise.resolve().then(() => trace.push('promise'));
trace.push('synchronous');

process.on('beforeExit', () => {
  console.log(JSON.stringify({ entryModuleSystem: 'commonjs', order: trace }));
});
