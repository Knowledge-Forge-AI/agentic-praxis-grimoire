# APGR npm distribution source

This directory owns the source templates and deterministic local packer for
the four official APGR npm packages:

- `@knowledge-forge-ai/apgr` — the dependency-free launcher;
- `@knowledge-forge-ai/apgr-darwin-arm64`;
- `@knowledge-forge-ai/apgr-linux-x64`; and
- `@knowledge-forge-ai/apgr-linux-arm64`.

This documentation covers 0.9.0. The previous published frozen release baseline
is **v0.8.1**. Once this version is published, packages are available on npm.
Prior to publication, test candidate features from an APGR Git checkout.

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

## Package contents and dispatch boundaries

The npm platform packages carry the standalone native Go binary (`bin/apgr`)
implementing runtime command families: `skills`, `footprint`, `env`, `analyze hotspots`,
`report`, and `response`.

The npm packages do **not** carry the repository test runner (`apgr test`), policy
validation, or test suites. `apgr test --summary-file` requires an APGR Git source
checkout and the developer toolchain (Python 3.11+, pytest, coverage, pytest-cov,
pytest-xdist, Git 2.40+, Go 1.25+).

## Platform support and qualification gate

Supported runtime targets:
- `darwin/arm64` (macOS Apple Silicon) -> `@knowledge-forge-ai/apgr-darwin-arm64`
- `linux/x64` (Linux x86_64) -> `@knowledge-forge-ai/apgr-linux-x64`
- `linux/arm64` (Linux aarch64) -> `@knowledge-forge-ai/apgr-linux-arm64`

Platform developer qualification gate status: Darwin arm64 is fully qualified (APG114 / Exit `00159`).
The Linux developer qualification gate is currently pending: the `policy` suite is
pending runner qualification, and `unit`/`integration`/`combined` suites are blocked
by whole-inventory preflight binding Darwin arm64 Nix store digests.

Package metadata declares the conservative API compatibility floor
`engines.node >=22.0.0`; local qualification used Node `v22.22.2`.
