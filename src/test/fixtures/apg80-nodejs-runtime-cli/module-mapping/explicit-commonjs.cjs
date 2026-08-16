// APG80-FX-002 — `.cjs` maps to Node's CommonJS loader regardless of the
// enclosing `type: "module"` package scope. `.cjs` is a Node host mapping and
// is not a standardized ECMAScript parse goal.

exports.extensionEvidence = 'explicit-cjs';
