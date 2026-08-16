// APG80-FX-009 — effect-free language core. Same inputs, same result, no
// process, filesystem, network, stream, or exit effect. Nothing here is a
// Node-owned decision.

/** Splits already-acquired argument values. Acquisition itself is the adapter's job. */
export function parseArguments(argumentValues) {
  const flags = new Set();
  const operands = [];
  for (const value of argumentValues) {
    if (value.startsWith('--')) {
      flags.add(value.slice(2));
    } else {
      operands.push(value);
    }
  }
  return { flags, operands };
}

/**
 * Computes a result from argument and environment values supplied as ordinary
 * data. It returns message data; it never writes and never exits.
 */
export function run(argumentValues, environmentValues) {
  const { flags, operands } = parseArguments(argumentValues);
  const verbose = flags.has('verbose') || environmentValues.APG80_VERBOSE === '1';
  const totals = operands
    .map((operand) => Number(operand))
    .filter((value) => !Number.isNaN(value));
  return {
    total: totals.reduce((sum, value) => sum + value, 0),
    operandCount: operands.length,
    numericCount: totals.length,
    verbose,
    messages: verbose ? [`operands:${operands.length}`] : [],
    status: totals.length === operands.length ? 'computed' : 'computed-with-skipped-operands',
  };
}
