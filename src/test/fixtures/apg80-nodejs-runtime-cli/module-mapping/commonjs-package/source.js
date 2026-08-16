// APG80-FX-002 — `.js` whose Node mapping comes from an explicit
// `type: "commonjs"` package scope. An explicit scope is not overridden by the
// file's own syntax on the observed runtime.

exports.scopeEvidence = 'explicit-type-commonjs';

exports.wrapperGlobalsVisible = function wrapperGlobalsVisible() {
  return {
    require: typeof require !== 'undefined',
    dirname: typeof __dirname !== 'undefined',
    module: typeof module !== 'undefined',
  };
};
