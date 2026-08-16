// APG80-FX-005 and APG80-FX-006 — resolution under an APG-owned package graph.
// Built-in, relative, self-referencing package, subpath, `#imports`, and
// condition-selected specifiers all resolve from checked-in files with no
// installation, no lockfile, and no package-manager involvement.

import { basename } from 'node:path';
import { reachedVia as viaRelative } from './lib/public-entry.mjs';
import { reachedVia as viaSelf } from 'apg80-resolution-scope';
import { reachedVia as viaSubpath } from 'apg80-resolution-scope/subpath';
import { reachedVia as viaInternal } from '#internal';
import { selectedCondition } from '#conditional';

export function resolutionResults() {
  return {
    builtin: typeof basename === 'function',
    relative: viaRelative,
    selfReference: viaSelf,
    subpath: viaSubpath,
    internalImport: viaInternal,
    condition: selectedCondition,
    installPerformed: false,
  };
}

/** An unexported subpath is refused by the resolver, with a Node error code. */
export async function encapsulationRefusal() {
  try {
    await import('apg80-resolution-scope/lib/encapsulated.mjs');
    return { refused: false, code: null };
  } catch (error) {
    return { refused: true, code: error.code };
  }
}
