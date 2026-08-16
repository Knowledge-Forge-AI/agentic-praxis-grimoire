// APG80-FX-003 — Node's CommonJS wrapper bindings and the exports/module alias
// boundary. Whole-file host ownership is Node's; the ordinary ECMAScript
// expressions inside remain a separate, language-owned decision.

const dependency = require('./local-dependency.cjs');

/** The five wrapper bindings are supplied by Node's module wrapper, not by ECMAScript. */
function wrapperBindings() {
  return {
    exports: typeof exports,
    require: typeof require,
    module: typeof module,
    filename: typeof __filename,
    dirname: typeof __dirname,
  };
}

/** Top-level `this` in a CommonJS module is the initial `module.exports`. */
const topLevelThisIsModuleExports = this === module.exports;

/** `exports` aliases the initial `module.exports` object before any reassignment. */
const aliasHeldBeforeReassignment = exports === module.exports;

/** Repeated `require` of one resolved filename yields one cached instance. */
function cacheIdentity() {
  return require('./local-dependency.cjs') === dependency;
}

module.exports = {
  wrapperBindings,
  topLevelThisIsModuleExports,
  aliasHeldBeforeReassignment,
  cacheIdentity,
  dependencyLabel: dependency.label,
};

// Reassigning `module.exports` breaks the alias; `exports` still names the old object.
module.exports.aliasHeldAfterReassignment = exports === module.exports;
