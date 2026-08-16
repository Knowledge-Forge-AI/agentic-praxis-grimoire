// APG78-FX-009 — the importing side of an APG-owned live binding.
// Linking is performed by the host; this file states language shape only.
// APG-owned. No host, Node, or browser dependency.

import { count, increment } from './counter.mjs';
import * as namespace from './counter.mjs';

/** Reads the imported binding before and after the exporter mutates it. */
export function observeLiveBinding() {
  const before = count;
  increment();
  return { before, after: count };
}

/** Reads the same binding through the module namespace object. */
export function observeNamespace() {
  return {
    label: namespace.label,
    count: namespace.count,
    keys: Object.keys(namespace).sort(),
    tag: Object.prototype.toString.call(namespace),
  };
}

/** Attempts to write through the namespace object. */
export function attemptNamespaceWrite() {
  try {
    namespace.count = 99;
    return { threw: null };
  } catch (error) {
    return { threw: error.constructor.name };
  }
}
