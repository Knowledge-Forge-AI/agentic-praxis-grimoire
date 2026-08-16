// APG80-FX-012 — filesystem, path, and file-URL contracts. The base directory is
// is the one exact APG-created fs-case directory for this invocation. Node owns
// its documented API result. This controlled fixture does not
// prove permission policy, cross-filesystem atomicity, durability, or business
// authorization.

import { lstat, mkdtemp, readFile, realpath, rename, rm, stat, writeFile } from 'node:fs/promises';
import { isAbsolute, join, resolve, sep } from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';

const SYNTHETIC_CONTENT = 'apg80-synthetic-fixture-content\n';

export async function filesystemBoundary(filesystemCaseDirectory) {
  if (!isAbsolute(filesystemCaseDirectory)) {
    throw new Error('APG81A filesystem case rejected');
  }
  const filesystemCase = resolve(filesystemCaseDirectory);
  const [canonicalFilesystemCase, filesystemCaseIdentity] = await Promise.all([
    realpath(filesystemCaseDirectory),
    lstat(filesystemCaseDirectory),
  ]);
  if (
    canonicalFilesystemCase !== filesystemCase
    || filesystemCaseIdentity.isSymbolicLink()
    || !filesystemCaseIdentity.isDirectory()
  ) {
    throw new Error('APG81A filesystem case rejected');
  }

  let base = null;

  try {
    base = await mkdtemp(join(filesystemCase, 'apg80-fx012-'));
    const original = join(base, 'original.txt');
    const renamed = join(base, 'renamed.txt');
    await writeFile(original, SYNTHETIC_CONTENT, 'utf8');
    const url = pathToFileURL(original);
    const roundTripEqual = fileURLToPath(url) === original;

    await rename(original, renamed);
    const contentAfterRename = await readFile(renamed, 'utf8');

    let missingCode = null;
    try {
      await stat(original);
    } catch (error) {
      missingCode = error.code;
    }

    return {
      fileUrlProtocol: url.protocol,
      roundTripEqual,
      contentPreserved: contentAfterRename === SYNTHETIC_CONTENT,
      missingCode,
      separator: sep,
      durabilityProven: false,
      permissionPolicyProven: false,
    };
  } finally {
    if (base !== null) {
      await rm(base, { recursive: true, force: true });
    }
  }
}
