// APG80-FX-002 — genuinely unresolved mapping variant.
//
// The nearest controlling manifest declares no `type`, and this source contains
// no import, export, or CommonJS-only construct. Nothing in the artifact settles
// whether Node maps it to CommonJS or to ESM: the answer depends on the exact
// Node version's typeless-scope policy and on the selected runtime flags. This
// file is therefore never loaded by the fixture's own smoke.

const goalNeutralValue = 'settled-by-runtime-not-by-source';

globalThis.APG80_GOAL_NEUTRAL = goalNeutralValue;
