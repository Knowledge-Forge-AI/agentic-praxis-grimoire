# npm package manager profile contract

Lifecycle: `provisionally-integrated`.
Lifecycle ADR: `Proposed`.

APG124 admits this provisional package manager owner for repository-selected npm,
with evaluated reference baseline npm 12.0.2. Consumer repositories establish their
own selected package manager version; adopting this profile does not mandate version 12
across all consumer repositories.

## Sources and compatibility

Primary documentation inspected 2026-09-09 is mutable. The npm CLI documentation
at [docs.npmjs.com](https://docs.npmjs.com/) and installed 12.0.2 package declarations
bound feature eligibility. The executing Node runtime must satisfy engine constraint
`^22.22.2 || ^24.15.0 || >=26.0.0`. The repository-qualified runtime is Node 22.22.2.

| Clauses | Primary source | Evidence boundary |
| --- | --- | --- |
| NPM-01 | [cli.js](https://docs.npmjs.com/cli/v12/commands), package manifest | Repository-selected npm (evaluated baseline: 12.0.2) invoked via `node /path/to/npm-cli.js`; Artistic-2.0 license |
| NPM-02 | [npmrc](https://docs.npmjs.com/cli/v12/configuring-npm/npmrc), [config](https://docs.npmjs.com/cli/v12/commands/npm-config) | CLI > env (`npm_config_*`) > project `.npmrc` > user `.npmrc` > global `.npmrc` > defaults; no secret leaks |
| NPM-03 | [package.json](https://docs.npmjs.com/cli/v12/configuring-npm/package-json), [package-lock.json](https://docs.npmjs.com/cli/v12/configuring-npm/package-lock-json) | LockfileVersion 3 with form-specific resolved/integrity fields; hidden lock freshness is conditional |
| NPM-04 | [npm-ci](https://docs.npmjs.com/cli/v12/commands/npm-ci), [npm-install](https://docs.npmjs.com/cli/v12/commands/npm-install) | `npm ci` fails closed on stale/missing lock; `npm install` updates lockfile when authorized |
| NPM-05 | [package-json#peerDependencies](https://docs.npmjs.com/cli/v12/configuring-npm/package-json#peerdependencies) | Strict peer dependency resolution; ERESOLVE on conflicts without force or legacy flags |
| NPM-06 | [package-json#overrides](https://docs.npmjs.com/cli/v12/configuring-npm/package-json#overrides) | Targeted transitive and direct dependency replacement; verified on installed version and content |
| NPM-07 | [workspaces](https://docs.npmjs.com/cli/v12/using-npm/workspaces) | Monorepo root workspaces array; hoisting, cross-links, and `--workspace` targeted scripts |
| NPM-08 | [scripts](https://docs.npmjs.com/cli/v12/using-npm/scripts), [npm-run-script](https://docs.npmjs.com/cli/v12/commands/npm-run-script) | Install lifecycle scripts suppressed via `--ignore-scripts`; explicit run executes with pre/post hook semantics |
| NPM-09 | [npm-exec](https://docs.npmjs.com/cli/v12/commands/npm-exec), [npx](https://docs.npmjs.com/cli/v12/commands/npx) | Local bin execution via `npm exec --no -- <cmd>`; download prevention without network |
| NPM-10 | [npm-pack](https://docs.npmjs.com/cli/v12/commands/npm-pack) | `npm pack --json` reports archive contents; verifies inclusion and bin behavior |
| NPM-11 | [npm-cache](https://docs.npmjs.com/cli/v12/commands/npm-cache) | Cacache integrity; isolated cache directories via `npm_config_cache`; offline operation |
| NPM-12 | [npm-publish](https://docs.npmjs.com/cli/v12/commands/npm-publish), [provenance](https://docs.npmjs.com/generating-provenance-statements) | Fail-closed `"private": true`; SLSA/Sigstore provenance; audit limits; zero token leaks |

The npm package is licensed under The Artistic License 2.0; retain its installed notices.
The harness dependency is test-only and scratch-installed with lifecycle scripts disabled.
No production dependency, global package installation, or repository dependency metadata
change is permitted.

## Install reproducibility semantics

Install reproducibility is bounded and contextual, not blanket deterministic.
Byte-for-byte identical installation cannot be assumed across heterogeneous platforms or environments.
Reproduction must account for:
1. Exact root lock bytes and lock-shaping flags; local/workspace entries need not have registry integrity fields.
2. Actual npm/Node/platform identities and lifecycle policy. Disabling scripts changes behavior and is not always compatible with the product.
3. Engine checks, omission options, peer policy and optional native dependencies.
4. Registry/cache availability, mutable Git/local sources, scripts and archive contents.
5. Runtime entrypoint interpretation remains with Node/browser owners; npm packaging does not prove runtime behavior.

## Maintained evidence

The [scenario register](../../src/test/fixtures/apg124-toolchain/npm/scenarios.json)
contains expected predicates, actions, and assertions. `src/test/support/apg124_npm.py`
executes scenarios against the exact scratch npm 12.0.2 installation and Node 22.22.2.
All scenarios operate offline with local file or tarball dependencies. No loopback registry
is required.

| Cases | Clause coverage | Adverse control / limitation |
| --- | --- | --- |
| NPM01 | NPM-03, NPM-04 | Clean lockfile v3 ci succeeds; hidden lockfile written; zero lockfile mutation |
| NPM02 | NPM-03, NPM-04 | Stale lockfile rejected by `npm ci` with non-zero exit and EUSAGE/sync error |
| NPM03 | NPM-03, NPM-04 | `npm install` updates `package-lock.json` to record newly declared dependency |
| NPM04 | NPM-07 | Root monorepo workspace links packages and executes targeted script via `--workspace` |
| NPM05 | NPM-05 | Compatible peer dependency resolves and installs successfully |
| NPM06 | NPM-05 | Incompatible peer dependency rejected with ERESOLVE dependency conflict error |
| NPM07 | NPM-06 | `overrides` forces replacement of conflicting peer; verified on installed version and content |
| NPM08 | NPM-05 | Incompatible platform on `optionalDependencies` is gracefully skipped without failure |
| NPM09 | NPM-08 | Lifecycle execution positive, `--ignore-scripts` suppression, and pre/post hook ordering |
| NPM10 | NPM-10 | `npm pack --json` archives allowlisted `files`/`bin`; consumer installs resulting `.tgz` |
| NPM11 | NPM-02 | Nonsecret config precedence across five layers: CLI > env > project > user > global |
| NPM12 | NPM-09 | `npm exec --no` runs local binary in `node_modules/.bin`; refuses remote download |

Receipts record each scenario's executing npm version, status, assertions, duration,
and artifacts. Missing, duplicate, skipped, or failed scenarios fail closed.
Receipts contain no executable paths, private directories, or credential tokens.

## Runner and context integration

The APG124 test harness (`src/test/support/apg124_npm.py`) enforces fail-closed
prerequisite checks before test execution:
1. `APG_JAVASCRIPT_NODE`: must be an absolute, non-symlink executable file outside
   the repository, with exact SHA-256 digest
   `b7fff29202c2d59eeff28c53588d2832323b45cb2e854ba29bea47ade37d8359` and runtime identity
   `v22.22.2|darwin/arm64|12.4.254.21-node.39|1.51.0`.
2. `APG_NPM_PACKAGE_ROOT`: must reside inside caller-owned external scratch root,
   contain `bin/npm-cli.js`, declare version `12.0.2` under `Artistic-2.0`, and output `12.0.2` upon invocation.
3. `APG_NPM_OWNED_SCRATCH_ROOT`: must be caller-owned with mode 0700 permissions outside
   the repository checkout, with no symlink ancestors.

Subprocesses run with isolated environment allowlists (`npm_config_cache`, `npm_config_userconfig`,
`npm_config_globalconfig`, `HOME`, `TMPDIR`, `NO_COLOR=1`), bounded execution timeouts (30s),
and automatic process group cleanup.
The description reservation is at most 330 UTF-8 bytes.

## Completion and rollback

Phase evaluation records executed receipts, scenario predicates, and toolchain limits.
Dispatcher pre-final review and closeout remain separate from work-stage evidence.
Rollback removes the profile and its tests while preserving other toolchain profiles
and repository history.


## Script approval and evidence limits

The profile distinguishes npm 12's default dependency-script blocking and
project `allowScripts` approval from `ignore-scripts` and explicit npm run.
The synthetic lifecycle fixture approves only the resolved source of its owned local dependency;
it does not bypass the policy globally. Scenario bodies live in
`src/test/support/apg124_npm_scenarios.py`; custody, version binding and receipt
validation remain in `apg124_npm.py`. This decomposition preserves the same
observable predicates while bounding the scenario dispatcher.

The [npm 12 script approval command](https://docs.npmjs.com/cli/v12/commands/npm-approve-scripts/)
and [configuration reference](https://docs.npmjs.com/cli/v12/using-npm/config/)
are primary sources for that distinction. Clauses are original operational
summaries, not copied documentation. Executable scenarios do not prove every
package form, publish service or runtime seam described by the profile.
