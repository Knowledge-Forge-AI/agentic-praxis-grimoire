// APG80-FX-002 corrected by APG81 — explicit CommonJS package scope wins over
// module-only syntax, so the exact runtime must refuse this artifact.
export const mapping = 'module-only';
console.log(JSON.stringify({ mapping }));
