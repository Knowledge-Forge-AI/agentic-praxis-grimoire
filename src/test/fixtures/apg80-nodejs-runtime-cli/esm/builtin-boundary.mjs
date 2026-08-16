// APG80-FX-004 — `node:` built-in specifiers. Importing a built-in proves the
// specifier resolved on this runtime. It proves no filesystem, network, or
// operating-system outcome.

import { fileURLToPath } from 'node:url';
import { basename } from 'node:path';

export function builtinBoundary() {
  const thisFile = fileURLToPath(import.meta.url);
  return {
    builtinSpecifiersResolved: true,
    basenameComputed: basename(thisFile),
    filesystemAccessPerformed: false,
    networkAccessPerformed: false,
  };
}
