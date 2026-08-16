// APG78-FX-009 — cycle and TDZ boundary; APG-owned.
import { a } from './cycle-a.mjs';
export const b = a;
