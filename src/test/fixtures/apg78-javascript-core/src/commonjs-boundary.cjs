// APG78-FX-011 — `.cjs` CommonJS and Node host boundary.
// `.cjs` is a HOST classification, not a standardized ECMAScript goal. The
// wrapper bindings named below are Node's, not ECMA-262's; all questions about
// them route to node-runtime-owner. No require, filesystem, network, process,
// or environment operation is performed. APG-owned.

'use strict';

function wrapperBindingNames() {
  return ['module', 'exports', 'require', '__filename', '__dirname'];
}

function observeWrapper() {
  return {
    hasModule: typeof module !== 'undefined',
    hasRequire: typeof require === 'function',
    owner: 'node-runtime-owner',
  };
}

/** Ordinary ECMAScript evaluation inside a host-classified CommonJS file. */
function languageOwnedRemainder(values) {
  return values.reduce((total, value) => total + value, 0);
}

module.exports = { wrapperBindingNames, observeWrapper, languageOwnedRemainder };
