// APG74-FX-008: checked JavaScript. checkJs=true applies bounded,
// non-additive analysis to this JavaScript source; the file keeps its
// JavaScript source-language owner.

/**
 * @param {string} raw
 * @returns {{ retries: number }}
 */
export function parseRetries(raw) {
  const retries = Number.parseInt(raw, 10);
  return { retries: Number.isNaN(retries) ? 0 : retries };
}
