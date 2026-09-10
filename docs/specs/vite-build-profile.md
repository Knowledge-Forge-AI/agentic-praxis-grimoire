# Vite Build profile contract

Lifecycle: `provisionally-integrated`.
Lifecycle ADR: `Proposed`.

APG124 admits this provisional build and dev server toolchain owner for the
consumer-selected exact `vite` 8.2.2 package. The task does not authorize an upgrade.
This is original guidance, not copied upstream prose or consumer artwork.

## Sources and compatibility

Primary documentation inspected 2026-09-09 is mutable. The
[Vite documentation](https://vite.dev/guide/) and the installed 8.2.2 package
declarations bound feature eligibility. The Vite 8 series integrates the
[Rolldown](https://rolldown.rs/) bundler for optimized production compilation while
maintaining native ESM serving during development. Node.js ^20.19.0 || >=22.12.0 is required;
APG124 uses the qualified Node v22.22.2 runtime.

| Clauses | Primary source | Evidence boundary |
| --- | --- | --- |
| VITE-01 | [Releases](https://github.com/vitejs/vite/releases), installed package | Package revision 8.2.2 and Rolldown native bindings control |
| VITE-02 | [Config](https://vite.dev/config/), CLI options | Resolved config root, base, and publicDir control discovery |
| VITE-03 | [Env and Modes](https://vite.dev/guide/env-and-mode) | Default `VITE_` user-variable exposure plus built-ins; inspect custom prefixes/replacements |
| VITE-04 | [Server Options](https://vite.dev/config/server-options#server-fs-strict) | Loopback serving; strict fs allow/deny blocks traversal |
| VITE-05 | [HMR API](https://vite.dev/guide/api-hmr) | Module graph invalidation on loopback dev server |
| VITE-06 | [Plugins API](https://vite.dev/guide/api-plugin) | Enforce pre/post ordering and apply build/serve segregation |
| VITE-07 | [Asset Handling](https://vite.dev/guide/assets), [Features](https://vite.dev/guide/features) | Aliases resolved; publicDir copied verbatim; CSS processed |
| VITE-08 | [Build Options](https://vite.dev/config/build-options), Rolldown engine | Rolldown production bundling, tree-shaking, and chunking |
| VITE-09 | [Manifest](https://vite.dev/config/build-options#build-manifest), [Library](https://vite.dev/guide/build#library-mode) | .vite/manifest.json and dynamic code-splitting verified |
| VITE-10 | [Sourcemaps](https://vite.dev/config/build-options#build-sourcemap) | Explicit sourcemap generation and leak prevention |
| VITE-11 | [Preview](https://vite.dev/guide/static-deploy#testing-the-app-locally) | Preview server for local-only non-production verification |
| VITE-12 | [Build Determinism](https://vite.dev/guide/build) | Two-build digest matching and misconfiguration refusal |

The Vite core package is MIT licensed (VoidZero Inc. & Vite contributors). Rolldown
is MIT licensed. Underlying LightningCSS is MPL-2.0 licensed, and PostCSS is MIT
licensed. Installed notices are preserved. The toolchain dependency is test-only
and scratch-installed with lifecycle scripts disabled (`--ignore-scripts`). No production
dependency, global package installation, or repository package manifest mutation is
permitted.

## Maintained evidence

The [scenario register](../../src/test/fixtures/apg124-toolchain/vite/scenarios.json)
contains expected predicates, assertion lists, and adverse controls. `runner.mjs`
exercises the selected library via programmatic Node.js execution. The Python
supervisor in `src/test/support/apg124_vite.py` validates prerequisites, executes
the harness, and asserts clean evaluation receipts.

Clause IDs contain a hyphen and a descriptive suffix (for example, `VITE-03-ENV`);
scenario IDs do not (`VITE02` tests environment secrecy).

| Cases | Clause coverage | Adverse control / limitation |
| --- | --- | --- |
| VITE01 | VITE-02 | Unnormalized base path normalized; outDir resolved cleanly |
| VITE02 | VITE-03 | Unprefixed private environment secrets suppressed from client |
| VITE03 | VITE-07 | Alias target content observed; public assets copied, imported asset URLs inspected |
| VITE04 | VITE-06 | Plugin pre/post ordering verified; build plugin runs, serve skips |
| VITE05 | VITE-04 | Loopback bound; denied file and external traversal return HTTP 403 |
| VITE06 | VITE-05 | Module graph invalidation clears cache; dev server cleanly closes |
| VITE07 | VITE-08, VITE-09 | .vite/manifest.json maps input source to hashed chunk output |
| VITE08 | VITE-09 | Dynamic import splits chunks; library mode produces ESM + CJS |
| VITE09 | VITE-10 | Sourcemap enabled creates .map; disabled emits zero .map files |
| VITE10 | VITE-11 | Preview serves production output locally; non-production only |
| VITE11 | VITE-08, VITE-12 | Two consecutive builds produce identical file manifests and SHA-256 |
| VITE12 | VITE-02, VITE-12 | Missing library entry and misconfigured input cleanly rejected |

The evaluation requires zero failures and zero skips across all 12 scenarios.
The suite does not exhaust third-party framework plugins (React, Vue, Svelte) or
remote deployment providers; those remain consumer project evidence.

## Runner and context integration

The pytest test suite features a fail-closed Vite prerequisite contract mirroring
`apg_playwright_runtime.py`. It requires explicit environment variables:
- `APG_VITE_OWNED_SCRATCH_ROOT`: external caller-owned direct directory, mode 0700.
- `APG_VITE_PACKAGE_ROOT`: location of acquired Vite 8.2.2 within owned scratch.
- `APG_JAVASCRIPT_NODE`: path to qualified Node v22.22.2 binary.

Missing or non-matching prerequisites fail closed immediately without skipping.
Select the profile explicitly through the repository skills catalog. The description
reservation is bounded at <= 330 UTF-8 bytes.

## Completion and rollback

The phase evaluation owns executed versions, receipts, and limitations. Rollback
removes the Vite profile skill, specification, fixture, support code, and tests
while preserving existing unrelated toolchains and historical records.


## Composition and evidence limits

The operational leaf separates project authority from Vite semantics, uses the
correct Node engine range, and does not promise universal deterministic outputs.
It distinguishes mode/NODE_ENV, env load timing and client replacement, publicDir
serving, pre/post plugin ordering, dev/build hook availability, Rolldown optimizer
and build behavior, worker/library/SSR seams and hidden source-map disclosure.
These source-derived clauses extend guidance; executable scenario coverage stays
limited to the named predicates in the register.

Additional primary owners are [configuration](https://vite.dev/config/),
[shared options](https://vite.dev/config/shared-options),
[Vite 8 migration](https://vite.dev/guide/migration),
[dependency optimization](https://vite.dev/guide/dep-pre-bundling),
[features](https://vite.dev/guide/features) and
[SSR](https://vite.dev/guide/ssr). The prose is an original operational summary;
no upstream implementation is copied into the profile.

Closeout also consulted [Environment instances](https://vite.dev/guide/api-environment-instances)
and [SSR options](https://vite.dev/config/ssr-options) for VITE-02 and VITE-09.
Per-environment configuration, separate dev module graphs and SSR externalization
are source-derived guidance, not additional executable scenario claims.
