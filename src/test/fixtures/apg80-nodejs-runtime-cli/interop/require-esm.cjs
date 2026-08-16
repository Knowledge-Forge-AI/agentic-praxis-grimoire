// APG80-FX-007 — whether CommonJS may `require` an ECMAScript module is a
// version- and flag-sensitive Node capability. This artifact records the
// observed result on the runtime that actually executed it and asserts nothing
// about any other Node version.

function requireOfEsm() {
  try {
    const namespace = require('../esm/builtin-boundary.mjs');
    return { supported: true, exportNames: Object.keys(namespace).sort(), code: null };
  } catch (error) {
    return { supported: false, exportNames: [], code: error.code };
  }
}

module.exports = { requireOfEsm };
