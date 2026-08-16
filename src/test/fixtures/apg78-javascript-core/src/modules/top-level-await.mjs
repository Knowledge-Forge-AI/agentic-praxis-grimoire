// APG78-FX-009 — asynchronous module-evaluation boundary; APG-owned.
export const value = await Promise.resolve(1);
