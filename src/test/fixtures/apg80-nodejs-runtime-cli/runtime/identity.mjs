// APG80-FX-001 — exact runtime identity, version, platform, architecture, flags.
// APG-owned. Reports the runtime that is actually executing; selects nothing.

/** Every field is an observation of this process, not a project runtime choice. */
export function runtimeIdentity() {
  return {
    version: process.version,
    v8: process.versions.v8,
    platform: process.platform,
    arch: process.arch,
    execPathIsAbsolute: process.execPath.startsWith('/'),
    execArgv: [...process.execArgv],
    hasStripTypesFlag: process.execArgv.some((flag) => flag.includes('strip-types')),
    nodeOptionsPresent: typeof process.env.NODE_OPTIONS === 'string',
  };
}

/** Feature availability is version-specific; presence is observed, never assumed. */
export function featureAvailability() {
  return {
    importMetaResolve: typeof import.meta.resolve === 'function',
    importMetaDirname: typeof import.meta.dirname === 'string',
    fetchExposed: typeof fetch === 'function',
    webStreamsExposed: typeof ReadableStream === 'function',
    abortSignalExposed: typeof AbortSignal === 'function',
  };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  console.log(JSON.stringify({ ...runtimeIdentity(), ...featureAvailability() }));
}
