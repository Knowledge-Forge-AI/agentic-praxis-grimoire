// APG78-FX-010 — `.mjs` established module-goal boundary.
// The host classification is the extension; the ECMAScript consequence is the
// Module goal, which is strict by language definition. Recording the extension
// and recording that consequence are separate acts. APG-owned.

/** Module-goal strictness is not opt-in and cannot be waived here. */
export function strictnessIsIntrinsic() {
  try {
    undeclaredIdentifier = 'assigned';
    return { threw: null };
  } catch (error) {
    return { threw: error.constructor.name };
  }
}

/** The value of `this` at module top level, captured as written. */
export const topLevelThis = this;

/** Whether that captured value is the global object. */
export const topLevelThisIsGlobal = topLevelThis === globalThis;

export const goalMarker = 'module';
