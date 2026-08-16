// APG80-FX-010 — argv, environment, cwd, platform, and the secret boundary.
// Environment values are external inputs. Reading one never authorizes logging,
// persisting, or publishing it, so this artifact reports only presence and a
// synthetic allow-list value.

const SYNTHETIC_ALLOWED = ['APG80_VERBOSE', 'APG80_LABEL'];

export function acquiredInputs(processLike) {
  return {
    argvAfterEntry: processLike.argv.slice(2),
    execArgv: [...processLike.execArgv],
    entryPointPresent: typeof processLike.argv[1] === 'string',
    cwdPresent: processLike.cwd().length > 0,
    platform: processLike.platform,
    arch: processLike.arch,
  };
}

/** Only names on the synthetic allow-list are ever read back as values. */
export function environmentBoundary(environmentValues) {
  const readable = {};
  for (const name of SYNTHETIC_ALLOWED) {
    readable[name] = environmentValues[name] ?? null;
  }
  return {
    readable,
    otherNamesObservedCount: Object.keys(environmentValues).length,
    otherValuesRetained: false,
  };
}
