// APG78-FX-002 — lexical scope, temporal dead zone, and hoisting boundary.
// APG-owned. No host, Node, or browser dependency.

/** Reads a `let` binding before its declaration is evaluated. */
export function touchBeforeDeclaration() {
  let observed;
  try {
    observed = { read: later };
  } catch (error) {
    observed = { threw: error.constructor.name };
  }
  let later = 'initialized';
  return { observed, after: later };
}

/** `var` and function declarations instantiated before evaluation. */
export function hoistingBoundary() {
  const varBefore = typeof hoistedVar;
  const fnBefore = typeof hoistedFn;
  var hoistedVar = 'assigned';
  function hoistedFn() {
    return 'callable';
  }
  return { varBefore, fnBefore, varAfter: hoistedVar, fnAfter: typeof hoistedFn };
}

/** Per-iteration `let` bindings versus one shared `var` binding. */
export function perIterationBindings() {
  const fromLet = [];
  const fromVar = [];
  for (let i = 0; i < 3; i += 1) fromLet.push(() => i);
  for (var j = 0; j < 3; j += 1) fromVar.push(() => j);
  return { fromLet: fromLet.map((f) => f()), fromVar: fromVar.map((f) => f()) };
}
