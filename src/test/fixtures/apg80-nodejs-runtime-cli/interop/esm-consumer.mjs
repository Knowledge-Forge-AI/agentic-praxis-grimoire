// APG80-FX-007 — ESM importing CommonJS under the selected exact runtime.
// Default-export mapping, static named-export detection, and its failure mode
// are all Node loading results. None of them is an ECMAScript live binding.

import staticDefault, { alpha } from './static-exports.cjs';
import * as staticNamespace from './static-exports.cjs';
import dynamicDefault from './dynamic-exports.cjs';
import * as dynamicNamespace from './dynamic-exports.cjs';

export function interopShape() {
  return {
    staticDefaultKeys: Object.keys(staticDefault).sort(),
    staticNamedDetected: alpha,
    staticNamespaceKeys: Object.keys(staticNamespace).sort(),
    dynamicDefaultKeys: Object.keys(dynamicDefault).sort(),
    dynamicNamespaceKeys: Object.keys(dynamicNamespace).sort(),
  };
}

/** Dynamic import returns the same namespace for the same specifier. */
export async function dynamicImportIdentity() {
  const first = await import('./static-exports.cjs');
  const second = await import('./static-exports.cjs');
  return { sameSpecifierSameNamespace: first === second };
}
