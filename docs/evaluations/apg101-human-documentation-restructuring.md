# APG101 Human Documentation and README Restructuring

## Result

APG101 replaces the root phase ledger with a concise human landing page for
the v0.7.0 release candidate. The README explains APG's provider-neutral
toolkit boundary, concrete uses, safe current quick start, supported
consumption shapes, core concepts, JACA boundary, documentation routes,
release status, and contribution/licensing terms.

Candidate terminal disposition:
`V07_HUMAN_DOCUMENTATION_READY_FOR_APG102`.

Dispatcher-owned pre-final review, staging, commit, push, closeout
verification, and final acceptance remain outside provider work.

## APG100 reconciliation

The operator accepted APG100's exact reviewed and corrected closeout source.
Its dispatcher stopped after closeout because it did not recognize the result
fence; that operational failure changed no source bytes or accepted product
state. Public documents record this semantic disposition without publishing
development commit or tree identities.

APG100 therefore supplies the terminal runtime and packaging baseline for this
documentation-only phase.

## Landing page and current availability

The hidden `APG-CANDIDATE-STATE` marker remains exactly once in the root
README. Its former visible machine-contract explanation is removed from the
onboarding flow.

The README follows the ten-part order frozen by Accepted ADR 0051 and the v0.7
architecture:

1. product definition;
2. objectives and value;
3. concrete use cases;
4. quick start;
5. install and consumption choices;
6. core concepts;
7. JACA and library integration;
8. detailed-document navigation;
9. current project status; and
10. contribution and licensing.

The status and examples distinguish the published v0.6.0 release from the
locally qualified, unpublished v0.7.0 release candidate. The source-checkout
quick start uses read-only corpus and hotspot commands. No command claims that
v0.7 packages are available from PyPI or npm.

## Documentation ownership

`docs/README.md` is the task-oriented index. It routes readers to the
architecture-frozen detailed owners:

- `docs/reference/cli.md`;
- `docs/reference/go-library.md`;
- `docs/guides/skill-context-bundles.md`;
- `docs/guides/environment-snapshots.md`;
- `docs/guides/hotspot-analysis.md`;
- `docs/distribution.md`;
- `docs/architecture/apg-jaca-integration.md`;
- `docs/public-release-process.md`; and
- the project-model, roadmap, status, ADR, and history owners.

Small navigation stubs preserve the four superseded interim documentation
paths. They identify the frozen current owner and do not compete with it.

The former root README chronology is preserved at
`docs/history/releases-and-phases.md`. Its relative links are remapped for
the new depth, its duplicated machine marker is removed, and the v0.6
publication and APG94–APG100 chronology close the former stale APG90 ending.
The document is explicitly labeled archaeology rather than current
onboarding.

## Product and integration boundaries

The README and detailed navigation state that APG provides deterministic Go
library primitives, the `apgr` adapter, task-scoped skills, reporting,
environment snapshots, hotspot analysis, and compatibility/distribution
adapters. APG does not own provider selection, attempts, retries, review
cadence, authorization, or roadmap advancement.

JACA is a consumer and orchestrator. It imports APG public packages through a
JACA-owned adapter; APG never imports JACA. Real JACA direct-import and
cross-consumer qualification remains APG102 work and is not performed here.

## Public and historical boundaries

The v0.7 public projection includes tracked non-private documentation by
default, so the new README, index, reference, guide, history, evaluation, and
exit paths require no new allowlist or runtime-policy branch. Prospective-tree
checks verify their inclusion and changed-document link closure while
preserving exclusion of private evidence and generated/local artifacts.

Historical v0.6 reconstruction remains bound to its frozen surface and digest;
the APG101 documents are v0.7-only source additions. No public v0.6 byte is
rewritten.

The repository-wide prospective link gate also reproduces one unchanged
baseline failure: `hotspot/testdata/classification/sample.md` links to a
fixture-relative `target` path that is absent from the projected tree. APG101
does not change that test fixture or the public-projection filter. APG102 must
disposition the existing projection/readiness defect before release; all 19
APG101-changed public Markdown documents pass the same link-resolution rules
against the complete projected path set.

## Preserved state

APG101 changes documentation and documentation navigation only:

- version remains `0.7.0`;
- skills remain 39 canonical, 39 catalog, 39 projections, and 39 discoverable;
- maturity remains 14 stable and 25 provisional;
- description metrics remain 9,504 bytes and 9,492 characters beneath the
  9,527-byte ceiling;
- the canonical corpus fingerprint remains
  `0509803b3c12e0366917a341c9d56945d7966897953415acf0c997254e1331c1`;
- report, skill-bundle, environment, hotspot, response, and distribution
  contracts remain unchanged; and
- `CSS-QD-001` through `CSS-QD-005` and `JS-QD-001` through
  `JS-QD-005` remain unchanged.

No runtime API, CLI syntax, schema, package manifest, version, skill body,
maturity, Nix, `.flakes`, JACA, deployment, active integration, tag, or
publication state changes.

## Verification

Focused verification covers Markdown and relative-link structure; root marker
contracts; README and documentation navigation; prospective v0.7 public
projection and private-path exclusion; frozen v0.6 reconstruction; record
identity; the canonical skill library and Go corpus; context-report metrics;
README command truth; changed-tree whitespace; and three bounded navigation
probes for a new user, Go/JACA integrator, and maintainer.

Observed resulting-state evidence:

- record identity passes with 51 ADRs, 150 exits, 150 phase IDs, and next exit
  00151;
- skill-library validation passes at 39 canonical, 39 catalog, and 39
  projections; Go corpus verification passes;
- context reporting returns 39 skills, 39 discoverable, zero malformed, 9,504
  description bytes, and 9,492 description characters;
- build information reports the preserved embedded corpus fingerprint;
- 38 focused candidate-marker and Markdown-profile contract tests pass;
- clean prospective-source v0.6 and v0.7 public manifests both reconstruct;
- all 19 changed public Markdown documents resolve links against 1,028
  prospective public paths, with required APG101 docs present and private
  paths absent;
- worktree, index, and prospective-tree whitespace checks pass, and the real
  index remains empty; and
- the README help, skill-list, context-report, corpus-verification, and bounded
  hotspot examples execute successfully from source.

The published v0.6.0 source tag was obtained read-only for the stronger
historical Python-bundle rebuild. That rebuild stopped at its prerequisite
check because the available verification Python does not provide the
`python -m build` frontend. APG101 does not add or install a build dependency.
The frozen v0.6 public-surface manifest reconstructs successfully, and the
accepted APG100 artifact qualification remains the evidence owner for the
historical bundle.

The probes pass:

- a new user can explain APG from the opening, run a safe first command, and
  distinguish published v0.6.0 from candidate v0.7.0;
- a Go/JACA integrator can find the module path, five public packages,
  reporting/skills/environment/hotspot owners, and the one-way integration
  boundary from the README and docs index; and
- a maintainer can reach governance, maturity/debt, release process, current
  status, ADRs, evaluations, roadmaps, and phase archaeology without using the
  root README as a ledger.

APG102 remains separately authorized.
