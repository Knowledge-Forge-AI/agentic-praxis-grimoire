// @ts-check
// APG78-FX-013 — checked JavaScript. The directive above requests checking;
// it does not prove that a checker, version, configuration, or invocation was
// selected. The file stays JavaScript-owned as a whole. APG-owned.

/**
 * @param {ReadonlyArray<number>} values
 * @returns {{ total: number, count: number }}
 */
export function summarize(values) {
  const total = values.reduce((sum, value) => sum + value, 0);
  return { total, count: values.length };
}

/**
 * The ECMAScript question here is coercion; the checking question is the
 * annotation. Different owners, different answers.
 * @param {unknown} candidate
 * @returns {boolean}
 */
export function isNumericLike(candidate) {
  return candidate !== null && candidate !== '' && !Number.isNaN(Number(candidate));
}
