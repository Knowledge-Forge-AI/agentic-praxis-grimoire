# APG124 synthetic npm package manager qualification fixtures

These APGR-owned fixtures contain no consumer artwork, external network dependencies,
or private credentials. The maintained register defines 12 mechanical scenarios
exercising npm 12.0.2 under Node 22.22.2:
- NPM01: Clean lockfile v3 `npm ci`
- NPM02: Stale lockfile refusal under `npm ci`
- NPM03: Lockfile update under `npm install`
- NPM04: Monorepo workspaces install and targeted `--workspace` execution
- NPM05: Compatible peer dependency resolution
- NPM06: Incompatible peer dependency conflict refusal (`ERESOLVE`)
- NPM07: Dependency override resolution via `overrides` with installed version and content verification
- NPM08: Optional dependency platform filtering (`os` mismatch skip)
- NPM09: Lifecycle script installation execution, `--ignore-scripts` suppression, and pre/post hook ordering
- NPM10: Local tarball packaging via `npm pack --json` and archive consumption
- NPM11: Nonsecret configuration precedence (CLI > env > project > user > global) via `registry`
- NPM12: Local binary execution via `npm exec --no` with download prevention

## Reproduction

Reproduction requires explicit environment variables pointing to qualified binaries and owned scratch roots (no default paths are assumed):
- `APG_JAVASCRIPT_NODE`: Absolute path to verified Node binary
- `APG_NPM_PACKAGE_ROOT`: Absolute path to verified npm package directory containing `bin/npm-cli.js`
- `APG_NPM_OWNED_SCRATCH_ROOT`: Absolute path to caller-owned scratch directory (mode 0700, no symlink ancestors)

All operations run strictly offline using local `file:` or tarball dependencies.
No external network calls or loopback registries are required.
Subprocesses execute inside caller-owned scratch directories with mode 0700 permissions
and isolated environment allowlists (no inherited npm authentication or ambient configs).
Receipts record sanitized outcomes without executable paths or credentials and attest
the executing npm version for each scenario.
