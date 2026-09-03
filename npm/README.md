# APGR npm distribution source

This directory owns the source templates and deterministic local packer for
the four official v0.8.1 npm packages:

- `@knowledge-forge-ai/apgr` — the dependency-free launcher;
- `@knowledge-forge-ai/apgr-darwin-arm64`;
- `@knowledge-forge-ai/apgr-linux-x64`; and
- `@knowledge-forge-ai/apgr-linux-arm64`.

`libexec/apg_npm_distribution.py` renders package metadata from the single
`src/agentic_praxis_grimoire/VERSION` authority and consumes, without
rebuilding, one Go binary plus its `apg.binary-manifest/v1` companion per
target. The packer writes normalized `package/` tar members with zero epoch,
zero owner identity, and deterministic gzip metadata. Generated tarballs are
qualification output and are not source files.

The launcher selects only the exact `process.platform`/`process.arch` target,
verifies package identity, manifest identity, executable mode, size, and
SHA-256, then invokes the packaged binary with the caller's exact arguments,
inherited stdio, and `shell: false`. It has no install hook, download path, or
third-party JavaScript runtime dependency.

Package metadata declares the conservative API compatibility floor
`engines.node >=22.0.0`; local qualification used Node `v22.22.2`.
