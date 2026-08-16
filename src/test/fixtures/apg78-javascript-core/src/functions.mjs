// APG78-FX-005 — functions, closures, `this`, parameters, rest, and spread.
// APG-owned. No host, Node, or browser dependency.

/** Ordinary-function `this` versus lexically captured arrow `this`. */
export function bindingPair() {
  const lexicalThis = this;
  const holder = {
    label: 'holder',
    ordinary() {
      return this?.label;
    },
    arrow: () => lexicalThis?.label,
  };
  const detached = holder.ordinary;
  return { called: holder.ordinary(), detached: detached(), arrow: holder.arrow() };
}

/** Default-parameter evaluation timing and its access to earlier parameters. */
export function defaults(trace, first = mark(trace, 'first', 1), second = first + 1) {
  return { first, second };
}

function mark(trace, label, value) {
  trace.push(label);
  return value;
}

/** Rest collection, spread expansion, and a closure over a mutated binding. */
export function restSpreadAndCapture(head, ...tail) {
  let counter = 0;
  const read = () => counter;
  counter += 1;
  const collect = (...values) => values;
  const source = Object.create({ inherited: 'excluded' });
  source.head = head;
  source.own = 'included';
  const copied = { ...source };
  return {
    head,
    tail,
    widened: [head, ...tail],
    called: collect(head, ...tail),
    copied,
    captured: read(),
  };
}

/** Later arguments are not evaluated after an earlier abrupt completion. */
export function abruptArguments(trace) {
  const thrower = () => {
    trace.push('throw');
    throw new TypeError('argument');
  };
  const later = () => trace.push('later');
  try {
    (() => undefined)(thrower(), later());
  } catch (error) {
    return error.constructor.name;
  }
  return null;
}
