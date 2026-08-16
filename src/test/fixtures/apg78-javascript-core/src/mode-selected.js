// APG78-FX-012 — a `.js` file whose goal IS established by host evidence.
//
// Decision scope: this file as consumed inside this fixture package, whose
// `package.json` declares `"type": "module"`. That declaration is the present
// evidence establishing the Module goal. The bytes below do not establish it.
//
// APG-owned. No host, Node, or browser dependency.

export const goalEvidence = 'nearest package.json "type" field';

/** Constructs valid under either goal; the goal comes from elsewhere. */
export function neutralComputation(values) {
  return values.filter((value) => value > 0).map((value) => value * 2);
}
