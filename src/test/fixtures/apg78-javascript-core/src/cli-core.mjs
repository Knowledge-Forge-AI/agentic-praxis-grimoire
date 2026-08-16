// APG78-FX-014 — the pure ECMAScript core of a CLI utility.
// Argument and environment values arrive as ordinary data. No process,
// filesystem, network, output writer, signal, or exit status.
// Returns a structured result and never performs it. APG-owned.

/** Parses already-acquired argument values; acquisition is the adapter's job. */
export function parseArguments(argumentValues) {
  const flags = new Set();
  const operands = [];
  for (const value of argumentValues) {
    if (value.startsWith('--')) flags.add(value.slice(2));
    else operands.push(value);
  }
  return { flags, operands };
}

/** Same inputs, same returned data, and no injected or external effect. */
export function run(argumentValues, environmentValues) {
  const { flags, operands } = parseArguments(argumentValues);
  const verbose = flags.has('verbose') || environmentValues.VERBOSE === '1';
  const messages = verbose ? [`operands:${operands.length}`] : [];
  const total = operands
    .map((operand) => Number(operand))
    .filter((value) => !Number.isNaN(value))
    .reduce((sum, value) => sum + value, 0);
  return { total, operandCount: operands.length, verbose, messages, status: 'computed' };
}
