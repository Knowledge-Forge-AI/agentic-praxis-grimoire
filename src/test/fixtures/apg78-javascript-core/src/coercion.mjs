// APG78-FX-003 — coercion and equality contrasts.
// APG-owned. No host, Node, or browser dependency.

/** An object whose conversion is observable through its own methods. */
export function convertible(trace) {
  return {
    [Symbol.toPrimitive](hint) {
      trace.push(hint);
      if (hint === 'number') return 42;
      if (hint === 'string') return 'forty-two';
      return 'default';
    },
  };
}

/** Exercises the conversion paths that reach the object above. */
export function conversions(subject) {
  return { number: +subject, string: `${subject}`, loose: subject == 'default' };
}

/** The four distinct equality operations over the same operand pairs. */
export function equalities(left, right) {
  return {
    strict: left === right,
    abstract: left == right,
    sameValue: Object.is(left, right),
    sameValueZero: [left].includes(right),
  };
}
