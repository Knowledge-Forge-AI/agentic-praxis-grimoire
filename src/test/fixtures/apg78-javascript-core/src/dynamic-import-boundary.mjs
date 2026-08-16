// APG78-FX-009 — dynamic-import expression and host-load boundary; APG-owned.
export function load(specifier) {
  return import(specifier);
}
