// APG80-FX-002 — `.js` whose Node mapping comes from an explicit `type: "module"`
// package scope, not from the extension and not from ECMAScript grammar.

export const scopeEvidence = 'explicit-type-module';

export function wrapperGlobalsVisible() {
  return {
    require: typeof require !== 'undefined',
    dirname: typeof __dirname !== 'undefined',
    module: typeof module !== 'undefined',
  };
}
