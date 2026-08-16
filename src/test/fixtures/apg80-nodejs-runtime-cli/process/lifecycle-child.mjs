// APG80-FX-013 — an APG80-owned child. It installs one handler, reports that it
// is ready, and stays alive on a timer until its parent terminates it. It signals
// nothing and reaches nothing outside this process.

let handled = false;

process.on('SIGTERM', () => {
  handled = true;
  process.exitCode = 0;
  clearInterval(keepAlive);
});

const keepAlive = setInterval(() => {}, 25);

process.stdout.write(`${JSON.stringify({ ready: true, pid: process.pid > 0 })}\n`);

process.on('exit', () => {
  process.stdout.write(`${JSON.stringify({ handledSigterm: handled })}\n`);
});
