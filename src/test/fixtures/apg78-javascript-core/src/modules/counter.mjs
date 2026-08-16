// APG78-FX-009 — the exporting side of an APG-owned live binding.
// APG-owned. No host, Node, or browser dependency.

export let count = 0;

export const label = 'counter';

export function increment() {
  count += 1;
  return count;
}
