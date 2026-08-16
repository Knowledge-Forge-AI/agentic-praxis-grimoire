# APG80 Node.js runtime and CLI fixture

APG-owned, independently authored in APG80 and corrected into maintained
current evidence through APG81H for the provisionally integrated
[`nodejs-runtime-profile`](../../../../docs/specs/nodejs-runtime-profile.md)
candidate under ADR 0046, Accepted with amendment. It is not a normative oracle
or target-execution proof. Maintained APG81H contracts own its current schema,
hashes, exact runtime bindings, controlled qualification threat model, and
stops. Node lifecycle is `provisionally-integrated`; publication, deployment,
stable maturity, and target execution remain outside this fixture.

## What it is for

Fourteen cases, `APG80-FX-001` through `APG80-FX-014`, exercise the boundaries
the candidate claims to own and the boundaries it explicitly refuses. Each case
and each individual artifact is recorded separately in
[`fixture-manifest.json`](fixture-manifest.json): one artifact never inherits
another's module mapping, whole-file owner, runtime state, or execution state.

## Rules this fixture keeps

- **No installation.** The package graph in `resolution/` resolves from
  checked-in files using the nearest manifest's `name`, its `exports` map, and
  its `imports` map. There is no dependency, no lockfile, and no
  `node_modules` directory.
- **No network.** No case contacts an external service.
- **No shell.** The only child process is spawned directly through the running
  executable with `shell: false`, and it is an artifact of this fixture.
- **No target contact.** No target source, path, command body, or execution
  appears anywhere. `target-boundary/public-safe-runtime-role.json` holds
  summarized public-safe role facts only.
- **No real secrets.** Environment values are synthetic and plainly
  non-sensitive, and only allow-listed names are ever read back as values.
- **Controlled qualification scratch.** The parent creates one private unique
  invocation root and passes `process/filesystem.mjs` only its exact `fs-case`
  child. Ordinary preflight rejects relative, foreign, escaped, or pre-existing
  symlink paths. The fixture uses synthetic names and content. This is a
  correctness contract for trusted local or CI qualification, not hostile
  same-UID isolation or a security boundary.

## Ownership is not selection

Several artifacts are owned by someone other than the Node profile while the
Node profile is still `selected` for one bounded decision about them. A
standalone `.cjs` artifact's whole-file owner is `node-commonjs-owner`; a
package manifest belongs to `project-configuration-owner`; `cli/core.mjs` is
effect-free computation owned by the JavaScript language owner even though the
Node adapter beside it is Node-owned.

## The deliberately unresolved artifact

`module-mapping/typeless-package/goal-neutral.js` sits under a manifest that
declares no `type` and contains no syntax that would distinguish one module
system from the other. Nothing in the artifact settles its mapping — the answer
belongs to the exact Node version and flag set. It is therefore recorded as
`unresolved` and is never loaded. Making it load would destroy the case.

## Observations are bounded

Every executed observation belongs to one exact executable, version, V8 and
libuv version, platform, architecture, flag set, command, and input. APG81A
maintains distinct exact `v22.22.2` primary and `v24.19.0` secondary roles.
Each maintained invocation observes the configured direct executable before
and after use. Continuous executable identity is not claimed; concurrent
hostile same-UID mutation routes to a security, sandbox, CI-isolation, or
operating-system owner and stops when no receiver is present.
Contrasting controls retain the CommonJS namespace, flag, and TypeScript
stripping differences rather than flattening them. Two earlier cases also exist
specifically to stop over-generalization: `APG80-FX-013` schedules identical
work from an ECMAScript module entry and from a CommonJS entry and records that
the observed order differs, and `APG80-FX-007` records both successful static
named-export detection and its failure for computed export names.

Running a case proves that observed result. It never proves another Node
version, another platform, delivery of bytes, durability, authorization,
protocol success, target execution, or deployment.
