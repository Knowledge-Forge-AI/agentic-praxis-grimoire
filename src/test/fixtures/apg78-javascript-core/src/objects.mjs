// APG78-FX-004 — objects, prototypes, property descriptors, and classes.
// APG-owned. No host, Node, or browser dependency.

/** A two-link prototype chain with a shadowed property. */
export function chain() {
  const base = { kind: 'base', shared: 'from-base' };
  const derived = Object.create(base);
  derived.kind = 'derived';
  const own = (key) => Object.prototype.hasOwnProperty.call(derived, key);
  return { derived, ownKind: own('kind'), ownShared: own('shared') };
}

/** A non-writable, non-configurable own property. */
export function fixedProperty() {
  const subject = {};
  Object.defineProperty(subject, 'fixed', {
    value: 'original',
    writable: false,
    configurable: false,
    enumerable: true,
  });
  return subject;
}

/** An inherited setter observes the actual receiver. */
export function inheritedSetter() {
  const base = {
    set value(next) {
      this.observed = next;
    },
  };
  const subject = Object.create(base);
  subject.value = 7;
  return { observed: subject.observed, ownsValue: Object.hasOwn(subject, 'value') };
}

/** Strict assignment to an inherited non-writable data property throws. */
export function inheritedNonWritable() {
  const base = {};
  Object.defineProperty(base, 'fixed', {
    value: 'base',
    writable: false,
    configurable: true,
  });
  const subject = Object.create(base);
  try {
    subject.fixed = 'replacement';
    return { threw: null, value: subject.fixed, owns: Object.hasOwn(subject, 'fixed') };
  } catch (error) {
    return {
      threw: error.constructor.name,
      value: subject.fixed,
      owns: Object.hasOwn(subject, 'fixed'),
    };
  }
}

/** Assigns and deletes under this module's strict-mode rules. */
export function writeAndDelete(subject) {
  const attempt = (action) => {
    try {
      return { threw: null, result: action() };
    } catch (error) {
      return { threw: error.constructor.name, result: undefined };
    }
  };
  return {
    assign: attempt(() => {
      subject.fixed = 'replacement';
    }),
    remove: attempt(() => delete subject.fixed),
    value: subject.fixed,
  };
}

/** Class construction order, `super`, fields, and a private element. */
export class Base {
  static tag = 'base';
  #secret = 'base-private';

  constructor(trace) {
    trace.push('base-constructor');
    this.trace = trace;
  }

  reveal() {
    return this.#secret;
  }

  static holds(candidate) {
    return #secret in candidate;
  }
}

export class Derived extends Base {
  static trace = ['static-field'];

  static {
    this.trace.push('static-block');
  }

  field = (this.trace.push('derived-field'), 'derived-field');
  #derivedSecret = 'derived-private';

  constructor(trace) {
    super(trace);
    trace.push('derived-after-super');
  }

  get secret() {
    return this.#derivedSecret;
  }
}
