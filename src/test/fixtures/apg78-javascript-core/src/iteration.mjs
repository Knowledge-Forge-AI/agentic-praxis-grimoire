// APG78-FX-006 — destructuring, the iteration protocol, and iterator closing.
// APG-owned. No host, Node, or browser dependency.

/** An iterator that records whether it was closed early. */
export function observableIterator(trace, limit = 5) {
  let produced = 0;
  return {
    [Symbol.iterator]: () => ({
      next() {
        if (produced >= limit) return { value: undefined, done: true };
        produced += 1;
        trace.push(`next:${produced}`);
        return { value: produced, done: false };
      },
      return() {
        trace.push('return');
        return { value: undefined, done: true };
      },
    }),
  };
}

/** Variants used to qualify missing, non-callable, throwing, and non-object return. */
export function returnVariant(trace, variant) {
  const iterator = observableIterator(trace, 3)[Symbol.iterator]();
  if (variant === 'missing') delete iterator.return;
  if (variant === 'non-callable') iterator.return = 1;
  if (variant === 'throwing') iterator.return = () => { throw new RangeError('close'); };
  if (variant === 'non-object') iterator.return = () => 1;
  return { [Symbol.iterator]: () => iterator };
}

/** Consumes fewer values than the iterator can produce. */
export function partialDestructure(iterable) {
  const [first, second] = iterable;
  return { first, second };
}

/** Leaves a `for...of` loop early. */
export function earlyExit(iterable) {
  for (const value of iterable) {
    if (value >= 2) return { stoppedAt: value };
  }
  return { stoppedAt: null };
}

/** Continue to the same loop does not close; break does. */
export function continueThenBreak(iterable) {
  const seen = [];
  for (const value of iterable) {
    seen.push(value);
    if (value === 1) continue;
    break;
  }
  return seen;
}

/** An original throw remains the governing completion if closing also throws. */
export function throwingBody(iterable) {
  try {
    for (const value of iterable) {
      void value;
      throw new TypeError('body');
    }
  } catch (error) {
    return `${error.constructor.name}:${error.message}`;
  }
  return null;
}

/** Object destructuring with renaming, a default, and rest. */
export function objectPattern(subject) {
  const { present: renamed, absent = 'fallback', ...rest } = subject;
  return { renamed, absent, rest };
}
