import { SUBMODULE_LOADED, SUBMODULE_VALUE, multiply } from './submodule.js';

export const MODULE_LOADED = true;
export const COMPUTE_RESULT = multiply(SUBMODULE_VALUE, 2);

export function getGreeting(name) {
  return `Hello, ${name}! Module active, submodule loaded: ${SUBMODULE_LOADED}`;
}
