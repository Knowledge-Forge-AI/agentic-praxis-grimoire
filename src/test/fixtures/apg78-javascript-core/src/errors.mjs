// APG78-FX-007 — exceptions and `finally` completion interaction.
// APG-owned. No host, Node, or browser dependency.

/** A `finally` block that returns while an exception is in flight. */
export function finallyReplacesThrow() {
  try {
    throw new RangeError('in-flight');
  } finally {
    return 'from-finally';
  }
}

/** A `finally` block that runs without altering the completion. */
export function finallyPreservesThrow(trace) {
  try {
    throw new TypeError('preserved');
  } finally {
    trace.push('finally');
  }
}

/** A `finally` block that overrides a pending `return`. */
export function finallyOverridesReturn() {
  try {
    return 'from-try';
  } finally {
    return 'from-finally';
  }
}
