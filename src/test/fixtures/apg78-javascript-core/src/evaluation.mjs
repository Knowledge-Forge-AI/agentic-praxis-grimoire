// APG78-FX-001 — ordinary evaluation order.
// APG-owned. No host, Node, or browser dependency.

/** Records the order in which its arguments were evaluated. */
export function order(trace) {
  const mark = (label, value) => {
    trace.push(label);
    return value;
  };
  return mark('left', 1) + mark('right', 2);
}

/** Short-circuit, optional chaining, and nullish coalescing boundaries. */
export function shortCircuit(trace, subject) {
  const side = (label, value) => {
    trace.push(label);
    return value;
  };
  const conjunction = subject.flag && side('and-right', 'r');
  const disjunction = subject.flag || side('or-right', 'r');
  const coalesced = subject.absent ?? side('coalesce-right', 'r');
  const chained = subject.nested?.[side('computed-key', 'deep')]?.value;
  const receiver = {
    value: 4,
    read(addend) {
      return this.value + addend;
    },
  };
  const optionalCall = receiver.read?.(side('optional-argument', 2));
  let grouped;
  try {
    grouped = (subject.nested?.deep).value;
  } catch (error) {
    grouped = error.constructor.name;
  }
  return { conjunction, disjunction, coalesced, chained, grouped, optionalCall };
}
