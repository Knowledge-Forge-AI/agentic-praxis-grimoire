// APG80-FX-013 — errors, rejections, and an APG80-owned child lifecycle. The
// child is invoked directly through the exact running executable with no shell.
// Shell grammar, quoting, executable trust, and operating-system authorization
// are separate decisions and are not exercised here.

import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

/** A synchronous throw and a rejected promise are distinct failure channels. */
export function failureChannels() {
  let syncCode = null;
  try {
    throw new TypeError('apg80-synchronous');
  } catch (error) {
    syncCode = error.constructor.name;
  }
  return { syncCode, rejectionHandledLocally: true };
}

export async function rejectionBoundary() {
  try {
    await Promise.reject(new Error('apg80-rejection'));
    return { caught: null };
  } catch (error) {
    return { caught: error.message };
  }
}

/** Spawns, terminates, and reaps exactly one APG80-owned child. */
export async function ownedChildLifecycle() {
  const here = dirname(fileURLToPath(import.meta.url));
  const child = spawn(process.execPath, [join(here, 'lifecycle-child.mjs')], {
    stdio: ['ignore', 'pipe', 'pipe'],
    shell: false,
  });

  let output = '';
  let terminationRequested = false;
  child.stdout.setEncoding('utf8');
  child.stdout.on('data', (chunk) => {
    output += chunk;
    if (!terminationRequested && output.includes('"ready":true')) {
      terminationRequested = true;
      child.kill('SIGTERM');
    }
  });

  const closed = await new Promise((resolve) => {
    child.on('close', (code, signal) => resolve({ code, signal }));
  });

  return {
    shellUsed: false,
    childHandledTermination: output.includes('"handledSigterm":true'),
    close: closed,
    unrelatedProcessesSignalled: false,
  };
}
