---
name: vite-build-profile
description: Use when a project selects Vite for dev serving or production building and decisions depend on root, base, publicDir, mode, env prefixes, loopback fs limits, Rolldown bundling, alias/CSS/plugin hooks, SSR seams, or preview.
---

# Vite Build Profile

Lifecycle: `provisionally-integrated`.
Lifecycle ADR: `Proposed`.
Reference implementation: Vite 8.2.2; repository selection remains explicit.

## Core principle

Identify the selected Vite version, config and execution environment before
reasoning about builds or serving. Own Vite tooling semantics; preserve Node,
browser, language, framework and package-manager ownership. A successful build
proves its asserted outputs, not runtime correctness or universal reproducibility.

## Do not use

Do not select or install Vite merely to apply this profile. TypeScript checking,
JavaScript semantics, React/JSX, Astro/MDX, Node process behavior, browser DOM,
accessibility standards and Playwright automation retain their respective owners.
Tailwind/shadcn integration is consumer composition, not additional profile scope.

## Procedure

1. Establish repository-selected Vite/Node identities, manifest/lock/scripts,
   config files, plugins, target environment and authorized output locations.
2. Resolve the relevant clauses below. Distinguish dev, build and preview, and
   separate executable fixture observations from source-derived guidance.
3. Use bounded, owned fixtures for destructive cache/output experiments. Bind
   receipts to exact inputs, versions, options, outcome predicates and cleanup.
4. Report remaining runtime/framework evidence and any nondeterminism without
   expanding dependency, serving, publication or deployment authority.

### Toolchain clauses

**VITE-01-IDENTITY.** The reference is Vite 8.2.2, whose Node engine is
`^20.19.0 || >=22.12.0`; APG's fixture qualifies Node 22.22.2. Verify installed
Vite, resolved Rolldown and platform-native optional bindings from the lock and
package manifests. A newer docs page or a transitive test dependency is not
proof that the project selects Vite for its application build.

**VITE-02-CONFIG.** Establish root, `base`, `publicDir`, `envDir`, config path
and resolved output paths. Config executes code: identify the selected loader
(default bundled config uses Rolldown; native loading has different
syntax and dependency behavior). Native loading depends on host support and
changes to imported config modules may require restart. Config callbacks receive
`command`, `mode`, `isSsrBuild` and `isPreview`; handle optional flags explicitly.
`serve` versus `build` is distinct from mode and from `NODE_ENV`. Dev normally
uses development mode and build production mode; `--mode staging` selects env
files without making a build a dev server. Inspect resolved config through the
selected public API; do not serialize secrets from the whole config.
Inspect `environments.client` and `environments.ssr` when per-environment
configuration is present: shared defaults and environment-specific resolution,
optimization and build options must be evaluated for the intended environment.
These environments are distinct from `.env` files and command/mode flags.
Dev environments have separate module graphs; plugin environment context must
match the graph being transformed. Check the selected version's Environment API
stability before relying on experimental hooks.

**VITE-03-ENV.** Env files load after config resolution; use `loadEnv` explicitly
when config needs them. Generic `.env`/`.env.local` and mode-specific files
compose, with mode-specific values taking priority and existing process env
winning. Restart after env-file changes. `envPrefix` defaults to `VITE_`; exposed
custom values are strings, so parse booleans/numbers deliberately. An empty
prefix is rejected. Prefixes do not protect values manually exposed by plugins
or `define`. `MODE` and `BASE_URL` are strings; `DEV`, `PROD`, `SSR` are booleans.
Dev provides env constants; builds replace them statically. Prefer literal
property access; dynamic computed lookup is not a portable replacement contract.
Never put secrets in client-exposed values; inspect emitted bundles/source maps.

**VITE-04-FS.** Observe actual listen address and port. This phase's fixtures
bind `127.0.0.1`; broader host binding requires the consumer's explicit authority.
`host: true`/`0.0.0.0` expands exposure. Keep allowedHosts and CORS narrow; a
wildcard host policy can enable source disclosure through DNS rebinding. Ports
may advance unless strictPort is selected. `server.fs.strict` restricts serving,
`allow` affects workspace discovery, and `deny` has priority for restricted file
patterns. These are dev-serving controls, not OS confinement. PublicDir files
are served/copied outside the ordinary transform path; do not put secrets there
or assume the fs deny rules protect public assets. Test exact allowed/denied URLs.

**VITE-05-HMR.** Identify the affected environment/module graph and acceptance
boundary. Use `import.meta.hot` guards, acceptance, disposal and invalidation
according to the HMR API; dispose side effects to avoid accumulation. A module
invalidation observation does not prove browser state preservation or framework
Fast Refresh. Await deterministic file/transform observations instead of sleeping.
Close servers/watchers and owned sockets on success, error and cancellation.

**VITE-06-PLUGINS.** Separate plugin ordering from hook ordering. User plugins
with `enforce: pre` precede ordinary plugins; `post` follows them, interleaved
with Vite's documented core/build plugins. `post` does not mean every hook runs
after bundling. `apply` selects serve/build or a predicate. `configResolved`
observes resolved options; `configureServer` owns dev middleware, not production
serving. Dev invokes resolution/load/transform hooks on requests without an output
bundle, so output-generation hooks are build-only (closeBundle is an exception).
Do not assume full module information or Rollup context availability in dev.
Virtual modules, environment state and hook filters must match the selected API.

**VITE-07-RESOLVE.** Use absolute filesystem alias replacements and inspect
`resolve.conditions`, package exports, dedupe and symlink identity; an alias is
not TypeScript path checking or npm installation. Vite 8 uses Rolldown for dev
dependency optimization as well as production bundling. Entry discovery, linked
dependencies, include/exclude and newly discovered imports can trigger optimization
and reloads; inspect `optimizeDeps` for the selected version rather than assuming
Vite 7's esbuild optimizer. JS CSS imports participate in HMR and build CSS output;
preprocessors require selected dependencies. PostCSS and optional Lightning CSS
configuration are separate choices, not an assumption that all CSS uses one engine.

**VITE-08-ROLLDOWN.** Vite 8 uses the unified Rolldown pipeline. Prefer current
`build.rolldownOptions`; Rollup-compatible options/plugins remain compatibility
surfaces with documented differences, not proof of complete Rollup parity.
Transformation/minification behavior and targets must be read for Vite 8, not
copied from Vite 7's Rollup/esbuild architecture. Build target transformation is
not automatic API polyfilling or TypeScript typechecking. Preserve a separate
selected typecheck command when required.

**VITE-09-OUTPUTS.** Imported assets become URLs and can be hashed or inlined;
`publicDir` assets retain names and are copied verbatim. `base` rewrites supported
HTML, CSS and imported asset references; use `import.meta.env.BASE_URL` for
constructed URLs where needed. Static `new URL(..., import.meta.url)` patterns
can be transformed, while arbitrary dynamic paths and SSR URL semantics differ.
Inspect manifest entries and emitted assets rather than assuming filename shape.
Dynamic imports may split chunks; constrained dynamic patterns need their own
proof. Worker entry patterns such as `new Worker(new URL(..., import.meta.url),
{type: 'module'})` have Vite-specific recognition and worker plugin configuration.
Library mode owns configured entry/formats/external dependencies and CSS output;
UMD/IIFE globals and package exports remain explicit packaging decisions.
For SSR builds, establish `build.ssr` and inspect `ssr.external` versus
`ssr.noExternal`: external dependencies use the runtime loader, while bundled
dependencies pass through Vite. Verify resolution conditions on both sides.
SSR externalization, conditions and module loading need server-runtime/framework
evidence; a client bundle or local SSR build alone cannot qualify that seam.

**VITE-10-SOURCEMAPS.** Select `build.sourcemap` deliberately: true emits a map,
inline embeds one, hidden omits the reference comment but still emits a map.
Inspect actual files and serving/upload policy. Hidden maps can still expose
source content and paths; minification is not secrecy. Preserve useful private
debugging evidence without publishing credentials or private source topology.

**VITE-11-PREVIEW.** `vite preview` locally serves an existing build for checking;
it is not a production server claim. Verify actual loopback binding, base URL,
response and owned shutdown. Preview success does not prove production hosting,
TLS, caching, authentication or runtime compatibility.

**VITE-12-DETERMINISM.** Identify `cacheDir` (normally node_modules/.vite), lock,
config, mode, environment and plugin inputs. Use `--force` or remove only the
owned relevant cache when a stale-cache hypothesis justifies it. Inspect outDir
before emptying it, especially outside root. Compare two controlled builds by
file set and content digest; record timestamps, generated IDs, platform-native
tools, dependency drift and plugin ordering as possible nondeterminism sources.
Do not guarantee reproducibility from one passing comparison.

## Evidence and completion

Report selected identities, resolved non-secret options, observed output/serving
predicates and cleanup. VITE01–VITE12 in the APG124 scenario register are bounded
synthetic evidence; clause coverage includes documentation-only guidance.
The project owns build budgets, dependency selection and release policy.

## Project-owned parameters

Selected Vite/Node versions, root/base/mode, config loader, serving allowlist, plugin set, build target and output disclosure policy belong to the project.

## Common mistakes

Do not apply Vite 7 bundler assumptions, expose server secrets through VITE_ names, equate post plugins with post-bundle hooks, or call preview a production server.

## Stop or escalate

Stop the affected action on missing prerequisites, unintended secret exposure,
unowned output/cache deletion or serving outside authorized scope. Report the
specific failure and retained evidence. Broader remediation needs its own authority.
