// APG80-FX-008 — CommonJS and ESM cache or identity boundaries. Identity is a
// property of one Node process under exact specifier and loader facts. It is not
// a cross-process, deployment, or persistence guarantee.

import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);

/** CommonJS: repeated require of one resolved filename yields one instance. */
export function commonjsIdentity() {
  const first = require('./static-exports.cjs');
  const second = require('./static-exports.cjs');
  const cached = Object.keys(require.cache).some((key) => key.endsWith('static-exports.cjs'));
  return { sameInstance: first === second, presentInRequireCache: cached };
}

/** ESM: the specifier URL is the identity key, so a query suffix is a distinct key. */
export async function esmIdentity() {
  const plain = await import('./static-exports.cjs');
  const plainAgain = await import('./static-exports.cjs');
  const withQuery = await import('./static-exports.cjs?apg80=variant');
  return {
    samePlainNamespace: plain === plainAgain,
    queryProducesDistinctNamespace: plain !== withQuery,
    crossProcessGuarantee: false,
  };
}
