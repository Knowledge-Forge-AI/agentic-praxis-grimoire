// APG80-FX-009 and APG80-FX-010 — the Node adapter. Everything the core refuses
// to touch lives here: argument acquisition, environment reading, working
// directory, stream writes, and exit status. A successful adapter run proves a
// local process result, not delivery, persistence, or user-visible completion.

import { run } from './core.mjs';

/** Acquires process inputs. Environment values are read, never logged wholesale. */
export function acquireInputs(processLike) {
  return {
    argumentValues: processLike.argv.slice(2),
    environmentValues: {
      APG80_VERBOSE: processLike.env.APG80_VERBOSE ?? null,
    },
    cwd: processLike.cwd(),
    platform: processLike.platform,
  };
}

/** Applies the core result to injected streams and returns the exit status only. */
export function applyResult(result, streams) {
  for (const message of result.messages) {
    streams.err.write(`${message}\n`);
  }
  streams.out.write(`${JSON.stringify({ total: result.total, status: result.status })}\n`);
  return result.numericCount === result.operandCount ? 0 : 1;
}

export function main(processLike, streams) {
  const inputs = acquireInputs(processLike);
  const result = run(inputs.argumentValues, inputs.environmentValues);
  return { exitStatus: applyResult(result, streams), cwdObserved: inputs.cwd.length > 0 };
}
