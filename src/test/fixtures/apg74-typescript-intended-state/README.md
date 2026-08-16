# APG74 TypeScript Intended-State Fixture

One APG-owned fixture project representing Theme Forge Terminal Nova's intended
TypeScript 7 product state under ADR 0043 (Accepted with amendment). Authored in
APG74 and hardened in APG75, it is the current maintained fixture owner and is
provisionally integrated after APG75A. Compiler-backed tests are current. No
target source is copied, and no generated output is committed.

## Shape

- `package.json` pins the exact selected stable compiler: `typescript@7.0.2`.
  No TypeScript 6 package is installed; `APG74-FX-010` records that
  disposition as `not-required` with its refresh condition.
- `tsconfig.json` is the main passing configuration with exact explicit
  option values (`strict`, `target`, `module`, `moduleResolution`, `types`,
  `verbatimModuleSyntax`, `exactOptionalPropertyTypes`,
  `noUncheckedIndexedAccess`, `allowJs`, `checkJs`, `jsx`, `noEmit`,
  `rootDir`). It includes `src/core`, `src/modules`, `src/declarations`,
  `src/ui`, and `src/checked` only.
- `tsconfig.declarations.json` is the separately evidenced declaration-only
  emit configuration. Emit runs only in a scratch copy; no generated output
  is ever committed.
- `src/embedded` and `src/unbound` are deliberately excluded from every
  configuration: they carry the embedded-host boundary case and the two
  unknown-state cases.
- `fixture-manifest.json` freezes the fourteen cases `APG74-FX-001` through
  `APG74-FX-014` with their decision scopes, role-identity state, active-role
  records, exact option facts, present/required evidence, and state labels.
  Active roles keep product intent separate from APG75 scratch invocation;
  an unresolved role has no invented role/package/version binding, and a
  not-required role has no active record. Case labels use closed value sets:
  `live_target_state` in current/historical/absent/unknown/not-applicable,
  `intended_product_state` in required/representative/boundary-only/
  not-applicable, and `temporary_compatibility` in required/not-required/
  unknown/not-applicable. `intended_product_state` classifies the case
  itself: for `APG74-FX-010`, `required` means the disposition case must
  always exist, while its `temporary_compatibility: not-required` records
  that TypeScript 6 itself is not needed. Known TypeScript 6 package
  candidates remain package evidence outside the unselected role record.

## Running the smoke checks

Copy this directory into invocation-owned scratch, install there with an
isolated npm cache, and run:

- `tsc --version` (expect `Version 7.0.2`),
- `tsc -p tsconfig.json` (expect exit 0),
- `tsc -p tsconfig.declarations.json` (declarations appear under the copy's
  `out/declarations` only).

Never run installs or emit inside the repository checkout. APG owns the
maintained compiler-backed tests; the smoke checks here remain bounded fixture
evidence only.

The standard repository runner requires an exact externally provisioned
`typescript@7.0.2` compiler. Install it only in invocation-owned scratch with an
isolated npm cache and no committed package lock, then set `APG_TYPESCRIPT_TSC`
to the absolute regular executable `node_modules/typescript/bin/tsc` path
outside the repository checkout. The runner rejects symlinks and checkout-local
executables and validates `Version 7.0.2` before collection. It does not install
from the network, populate this fixture, or accept a missing or different
compiler. Historical release and rollback inventories without compiler-backed
TypeScript test owners do not require this current-development prerequisite.
