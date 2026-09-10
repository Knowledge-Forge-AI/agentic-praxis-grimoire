---
name: npm-package-manager-profile
description: Use when package management decisions depend on npm CLI contracts, package.json and lockfile v3 integrity, install versus ci execution, peer dependencies and overrides, workspaces, script lifecycle and ignore-scripts, local pack tarballs, caching, or publication provenance; not for Node host runtime or bundler transforms.
---

# npm Package Manager Profile

Lifecycle: `provisionally-integrated`.
Lifecycle ADR: `Proposed`.
Reference implementation: npm 12.0.2; evidence the repository's selected version.

## Core principle

Treat npm version, configuration, lockfile and execution policy as part of the
install contract. Own npm package-management semantics while preserving Node
runtime, generic SemVer, bundler, test-runner and registry-administration owners.
A lockfile can be readable across versions without producing identical behavior.

## Do not use

Do not select or upgrade npm merely to apply this profile. Do not administer
registry accounts, change credentials, publish packages or run unapproved code
because a package command supports it. Node resolution of `exports`, process
execution and language semantics remain with their existing profiles.

## Procedure

1. Establish selected npm executable/version, Node engine compatibility, package
   manager declaration, scripts, manifests, lockfiles and non-secret config.
2. Identify the command's mutation and execution boundary using the clauses below.
   Preserve project policy and exact lock bytes unless an update is authorized.
3. Verify actual dependency, lifecycle or archive outcomes in owned disposable
   fixtures when needed. Retain sanitized failures as well as passing results.
4. Report exact versions/options, changed artifacts and reproducibility limits;
   installation, testing and publication are distinct outcomes and authorities.

### Package-manager clauses

**NPM-01-IDENTITY.** npm 12.0.2 requires Node
`^22.22.2 || ^24.15.0 || >=26.0.0`. This is the reference, not a mandate to
replace a repository-selected npm version. Establish `npm --version`, executable
path and effective non-secret configuration; a missing `packageManager` field
must not be filled by assuming the current shell's npm is project policy.
LockfileVersion is a format identity, not an executing npm-version attestation.

**NPM-02-CONFIG.** CLI flags override `npm_config_*` environment, then project,
user and global npmrc, then built-in/default configuration. Project npmrc is not
applied in every global context. Resolve scoped registry routing separately from
authentication scope; auth entries must be restricted to the intended registry
host/path. Do not print auth values, environment dumps, full npmrc, debug logs or
credential-bearing URLs. Use synthetic non-secret registry URLs for precedence
proof. Owned userconfig/globalconfig/cache and an allowlisted environment prevent
qualification from inheriting unrelated user configuration.

**NPM-03-MANIFEST-LOCK.** Parse actual JSON and inspect name/version, dependency
and script fields as npm interprets them. Root package-lock records resolved
packages, integrity and installation topology; v3 omits older compatibility data.
`node_modules/.package-lock.json` is an optimization tied to the current install
tree and freshness checks, not a substitute for the committed root lock. Manual
node_modules edits can invalidate its assumptions. Registry, file/link and
workspace entries have different resolved/integrity shapes; not every entry has
a registry tarball integrity field. Preserve lock bytes during a frozen install.

**NPM-04-INSTALL-CI.** `npm install` may reconcile and write manifest/lock state;
`npm ci` requires a matching existing lock, removes existing node_modules and
refuses manifest/lock mismatch instead of updating it. It installs the project,
not an individual new dependency. Preserve lock-shaping flags such as
legacy-peer-deps/install-links when reproducing the lock. A successful ci is
bounded by selected npm/Node/platform/config, lifecycle execution, registry and
cache state; it is not universal byte-for-byte installation proof.

**NPM-05-DEPENDENCIES.** Distinguish dependency, dev, optional and peer roles.
Omission controls installed contents and can affect script environment; it is
not equivalent to removing resolution information from the lock. Peers constrain
the surrounding graph; inspect ERESOLVE and strict-peer-deps/legacy-peer-deps
rather than silently using force. Optional dependencies can be absent on unsupported
platforms without failing the whole install, so verify the needed native binding.
Registry versions/tags, aliases, local directories, file tarballs, remote tarballs
and Git dependencies have different fetch, link, preparation and mutability
boundaries. Git/local preparation may execute code. Pin and inspect the actual
selected form; generic SemVer reasoning is not owned here.

**NPM-06-OVERRIDES.** Root overrides alter dependency selection, including nested
rules and replacement packages. Overrides in dependencies are not root policy.
Direct-dependency spec restrictions can produce EOVERRIDE; `$` references can
reuse an existing direct spec. Inspect the resulting installed graph/content,
not just command exit zero. Overrides do not prove compatibility or authorize
changing the repository dependency policy.

**NPM-07-WORKSPACES.** Establish root workspace definitions and actual linked
packages. Install graph behavior differs from script command selection: use
`--workspace` or `--workspaces` deliberately, and observe include-workspace-root.
Run ordering follows declared workspace order, not an inferred dependency build
scheduler. Missing-script handling must not silently convert a required test into
a pass. Local workspace symlinks are not standalone published-package proof.

**NPM-08-LIFECYCLE.** Inspect root and dependency hooks before execution. npm 12
blocks dependency install scripts by default under `allowScripts`; explicit
approved/denied project entries and strict-allow-scripts affect outcomes. Do not
silently bypass the policy with dangerously-allow-all-scripts. This differs from
older npm-major assumptions. `ignore-scripts` suppresses lifecycle scripts and
npm extensions; explicitly requested `npm run`/test/start still execute their
main script but omit automatic pre/post hooks. Normal run order is pre-name,
name, post-name. Installation/packing hooks include prepare/prepack/postpack with
command-specific order; Git preparation has its own dependency-install context.
Scripts use a shell, package-root cwd and augmented PATH; inspect nested commands
and keep Node/process semantics with their owner. Installation script success
and explicitly invoked run success require separate witnesses.

**NPM-09-EXEC-NPX.** npm exec/npx can resolve local bins or acquire missing packages
into a cache and execute them. Evidence exact package/version/bin selection and
argument parsing (`--` with exec; npx flags precede positional arguments). `--yes`
is execution consent, not a harmless convenience. `--no` rejects an install
prompt; combine with owned cache and offline mode for a bounded missing-package
negative. Local/cache presence alone is not trust or permission to execute.

**NPM-10-PACK-TARBALL.** Use `npm pack --json` to inspect the actual file inventory,
size and integrity of the archive. `files`, npmignore rules and mandatory/excluded
entries interact; verify contents rather than relying on an allowlist alone.
`bin` creates executable links/shims but does not validate program behavior.
`exports` describes public entrypoints; it does not guarantee inclusion in the
archive. `os`/`cpu`/engines affect compatibility checks, with engines ordinarily
advisory unless stricter policy applies; devEngines is a distinct development
check. Inspect lifecycle side effects before packing, then install the local
tarball in an isolated consumer to prove included files and bins are usable.

**NPM-11-CACHE-INTEGRITY.** npm's cache is content-addressed and integrity-checked,
not a durable package archive or a source of execution authority. Prefer bounded
cache verification; remove only owned cache state when a concrete defect justifies
it. Offline refuses missing cache data, while prefer-offline can still fetch.
Integrity detects byte disagreement, not whether code is safe. Record platform,
registry responses, scripts and mutable dependency forms as reproducibility limits.

**NPM-12-PUBLISH-SUPPLYCHAIN.** `private: true` blocks npm publication; publishConfig
can affect registry/access/tag. Pack/dry-run evidence does not grant publish
authority. Provenance links artifacts to supported build/source attestations;
trusted publishing uses an authorized OIDC relationship instead of a long-lived
token. Neither guarantees harmless code or runtime correctness. This phase makes
no publish attempt. Audit reports are advisory package/version metadata, not proof
of reachable exploitation; audit fix can mutate the graph and run installation
behavior. Review disclosures, affected paths and remediation under project policy.

## Evidence and completion

Report exact npm/Node identity, selected config, dependency/lock/pack predicates,
lifecycle witnesses, sanitized diagnostics and cleanup. NPM01–NPM12 are bounded
synthetic scenarios; documentation-only guidance must not be called executed
coverage. Preserve failures when a smaller maintained consumer subset passes.

## Project-owned parameters

Selected npm/Node identities, lock-shaping flags, workspace selection, approved script source identities, registry routing and package-content expectations belong to the project.

## Common mistakes

Do not treat lockfile v3 as npm-version selection, a registry-name script approval as approval of a local source, or ignore-scripts as suppression of an explicitly requested script.

## Stop or escalate

Stop the affected command on unresolved selected version, unsafe script/fetch
scope, credential disclosure, unowned deletion or a required reproducibility
mismatch. Seek the existing project authority for broader changes; never silently
replace npm versions or weaken tests to obtain a passing install.
