# APG83 v0.5 Bounded Dogfood and Release Readiness

## Result

APG83 concludes `READY_FOR_APG84`. Bounded dogfood against the exact observed
Knowledge Forge site and Terminal Nova revisions found no material unaccepted
APG v0.5 defect. The site completed its locked installation and production
build. Terminal Nova's locked installation stopped on a pre-existing target
manifest/lockfile mismatch; the retained profiles diagnosed that target-owned
condition without claiming deferred framework ownership.

## Dogfood disposition

The compact twelve-row matrix produced eleven `PASS` dispositions and one
`DEFERRED_V06_OR_PROJECT_OWNER` disposition. JavaScript, TypeScript, Node.js,
CSS, and Markdown guidance was applied only where a genuine target artifact
existed. Astro and MDX semantics remained outside the frozen v0.5 profile set.
The representative multi-owner review in each repository found no false
ownership, material omission, or operational friction attributable to APG.

## Distribution readiness

The installed `agentic-praxis-grimoire` distribution operates outside an APG
checkout for consumer-safe CLI, configuration, path, response, and packaged
skill-metadata operations. Repository-maintenance commands fail clearly when
repository authority is absent. Every installed metadata row is bound to the
corresponding complete skill in the reconstructed public Git release.

The v0.5 deployment contract is therefore:

- the public Git release owns the complete public skill corpus, projections,
  and maintenance source; and
- the PyPI distribution owns the `apgr` CLI/runtime and exact skill metadata.

A downstream adapter can consume the exact versioned pair without mutable
development-checkout state.

## Deterministic correction

Two clean baseline builds exposed reproducible wheels but non-reproducible
sdists. Payloads were identical; generated tar member ownership, names, modes,
and timestamps were not normalized. APG83 adds a narrow standard-library sdist
normalizer and focused tests. The final wheel and normalized sdist are built
twice in disjoint roots and require exact filename, content, metadata, and
SHA-256 equality.

## Preserved boundaries

APG83 changes no profile semantics, maturity, routing, or accepted debt. The
library remains 33 canonical skills, 33 catalog rows, and 33 projections, with
14 stable and 19 provisional skills and 31 general, one ChatGPT-local, and 32
checked routes. Node and scratch debt remain zero; known debt remains exactly
`CSS-QD-001` through `CSS-QD-005` and `JS-QD-001` through `JS-QD-005`.
Corrected historical v0.4 remains exact and isolated.

APG83 performs no APG remote interaction, publication, PyPI upload, Nix deployment,
operator `~/.apgr` mutation, target commit or push, stable promotion, v0.6
implementation, or APG84 execution.
