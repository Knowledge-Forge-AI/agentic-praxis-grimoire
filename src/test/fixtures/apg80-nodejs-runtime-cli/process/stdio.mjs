// APG80-FX-011 — streams, backpressure, and exit status. A write call is an
// acceptance signal from one local stream. It is not proof that a terminal, a
// file, a pipe consumer, or a remote system received or retained the bytes.

import { Writable } from 'node:stream';

/** Classifies the real standard streams without writing uncontrolled output. */
export function standardStreamShape(processLike) {
  return {
    stdoutIsTty: processLike.stdout.isTTY === true,
    stderrIsTty: processLike.stderr.isTTY === true,
    stdinReadable: typeof processLike.stdin.read === 'function',
    deliveryProven: false,
  };
}

/** Demonstrates backpressure on an in-memory sink with a deliberately small buffer. */
export async function backpressureBoundary() {
  const received = [];
  const sink = new Writable({
    highWaterMark: 8,
    write(chunk, _encoding, callback) {
      received.push(chunk.length);
      setImmediate(callback);
    },
  });

  const firstAccepted = sink.write(Buffer.alloc(4));
  const secondAccepted = sink.write(Buffer.alloc(64));
  const drained = await new Promise((resolve) => sink.once('drain', () => resolve(true)));
  sink.end();

  return { firstAccepted, secondAccepted, drained, chunksObserved: received.length };
}

/** `process.exitCode` records an intent; `process.exit` truncates pending work. */
export function exitStatusBoundary(result) {
  return {
    statusToRecord: result.numericCount === result.operandCount ? 0 : 1,
    forcedExitUsed: false,
    pendingWorkFlushProven: false,
  };
}
