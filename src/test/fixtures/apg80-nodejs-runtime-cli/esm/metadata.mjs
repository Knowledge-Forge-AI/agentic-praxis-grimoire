// APG80-FX-004 — Node ESM host metadata and the absence of CommonJS wrapper
// globals. `import.meta` fields are Node host inputs whose availability is
// version-specific; the module's binding semantics remain language-owned.

import { builtinBoundary } from './builtin-boundary.mjs';

export function hostMetadata() {
  return {
    urlProtocol: new URL(import.meta.url).protocol,
    dirnamePresent: typeof import.meta.dirname === 'string',
    filenamePresent: typeof import.meta.filename === 'string',
    resolvePresent: typeof import.meta.resolve === 'function',
  };
}

export function wrapperGlobalsAbsent() {
  return {
    require: typeof require === 'undefined',
    dirname: typeof __dirname === 'undefined',
    filename: typeof __filename === 'undefined',
    module: typeof module === 'undefined',
  };
}

/** Top-level `this` is `undefined` in an ECMAScript module. */
export const topLevelThis = this;

export { builtinBoundary };
