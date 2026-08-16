# APG74 TypeScript Language-Profile Candidate

## Outcome

APG74 is complete as candidate authoring. One narrow TypeScript
language-profile candidate — the leaf
[skills/typescript-language-profile/SKILL.md](../../skills/typescript-language-profile/SKILL.md),
the [candidate specification](../specs/typescript-language-profile.md), and
the navigation-only
[scenario coverage](../specs/typescript-language-profile-scenario-coverage.md)
— and one APG-owned TypeScript 7 intended-state fixture
([`src/test/fixtures/apg74-typescript-intended-state/`](../../src/test/fixtures/apg74-typescript-intended-state/README.md))
are authored on the APG74 branch.
[ADR 0043](../adr/2026/08/0043-typescript-language-profile-candidate-and-intended-state-harness.md)
is Proposed. Nothing is integrated: the candidate is
authored-proposed-unintegrated, and APG75 — separately authorized —
owns iterative hardening and the terminal ADR 0043 decision.

## Baseline and preservation

APG74 began from exact APG73 (`c50e578…`) after object, tree, parent,
two-record managed-omnibus, branch-parity, record-identity,
integration-count, decision-state, release-fingerprint, and target
verification. ADR 0042 remains Accepted and governing; ADRs 0031, 0034,
0035, 0036, 0039, 0040, and 0041 remain Rejected; Markdown remains
retained provisional. Integrated development remains 29 canonical skills /
29 catalog rows / 29 projections, 14 stable / 15 provisional, and
27 general / 1 ChatGPT-local / 28 checked routes; the corrected public and
active v0.4.0 identity was reverified live against the published v0.4.0
object. The APG74 branch alone carries the transitional thirtieth leaf.

## Compiler selection and roles

The exact stable TypeScript 7 patch was selected fresh: `typescript@7.0.2`
(npm `latest`, published 2026-07-08, Apache-2.0), whose registry `gitHead`
equals the `microsoft/typescript-go` release-tag commit for
`typescript/v7.0.2` — the native Go compiler line, not the historical
`microsoft/TypeScript` repository the package's metadata still names. The
scratch smoke run verified `tsc --version` = 7.0.2, a clean strict project
check, declaration-only emit with source-kind-preserving declaration
names, an `--lsp` stdio surface in the same binary, no stable programmatic
API entry in the npm package, and seeded-defect failures proving the
checks can fail. Compiler roles are modeled as independently evidenced
(`cli-checker`, `declaration-emitter`, `editor-language-service`,
`embedded-language-checker`, and others); package presence is never role
execution.

The TypeScript 6 compatibility disposition is `not-required`: no exact
APG74 role independently requires `@typescript/typescript6` (registry
latest 6.0.2, `tsc6`, re-exported TypeScript 6 API), and the fixture
installs no TypeScript 6 package. The recorded refresh condition covers
embedded checkers whose exact peer ranges exclude TypeScript 7.

## Targets: current versus intended

Both targets were freshly pinned. The website object is unchanged from the
APG72 pin. The theme repository's remote main was rebuilt after APG72 as a
three-commit history (upstream `starlight-theme-terminal` v1.3.0 import,
AGPL-3.0 relicensing boundary, identity transition); the current pin is
that new head. Its evidence: TypeScript-family sources checked via
`astro check` (an embedded-language-checker role) against resolved
`typescript@5.9.3`; a `@astrojs/check@0.9.9` peer range of
`^5.0.0 || ^6.0.0` that excludes TypeScript 7; a lockfile desynchronized
from the renamed workspace; and no evidenced direct `tsc` invocation. That
is migration-baseline evidence for the APG75 target gate — the live theme
does not use TypeScript 7, and no record claims it does.

## Candidate and fixture shape

The candidate owns TypeScript-specific static semantics and type-erasure
boundaries after exact evidence is established, with explicit non-owners,
role and option-fact models, present-versus-required evidence, source-kind
separation, declaration provenance, unknown-state stops, a static/runtime
refusal, and structural policy deferred with no numeric bands. Twenty-four
scenarios (`APG74-TS-001`–`024`) map to twenty-four stable clauses;
coverage is navigation-only. The fixture freezes fourteen cases
(`APG74-FX-001`–`014`) with exact option facts and live/intended/
compatibility labels; its generated smoke output stayed in scratch, and no
target source was copied.

## Boundary

APG74 ran author-side review only; it does not substitute for APG75's
independent reconstruction. The transitional APG74 branch shape — thirty
canonical leaves against twenty-nine catalog rows and projections, with the
mechanical library gate reporting exactly the three expected
bijection/router diagnostics for the uncataloged candidate — is recorded
truthfully rather than hidden by check modification. No CSS, JavaScript, JSX, Node, React, MDX,
Astro, or Vitest profile work occurred; targets were read as exact Git
objects only and never executed or modified; public and active surfaces
are unchanged; and no successor phase began.
