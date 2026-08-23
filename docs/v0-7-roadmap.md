# APG v0.7 Roadmap

## Authority and outcome

APG94 freezes this dependency-ordered v0.7 sequence. Each successor requires
separate human authorization. A phase may not borrow work from its successor,
and a passing implementation phase is evidence rather than authorization to
continue.

The target release outcome is an embeddable, library-first Go toolkit with
compatible CLI/Python/npm distributions, deterministic task-scoped skill
context, portable curated environment snapshots, structural-hotspot analysis,
human-oriented documentation, cross-consumer readiness, and immutable release
readback.

## Frozen sequence

| Phase | Scope | Depends on | Must not absorb |
| --- | --- | --- | --- |
| APG94 | Architecture, ownership, APIs, schemas, migration/distribution matrices, context/env/hotspot contracts, README IA | Terminal v0.6 publication | Any Go, skill, migration, packaging, README rewrite, or release implementation |
| APG95 | Go reporting vertical slice for show, diff, operational, parsing, and in-memory results; Python golden parity; external Go import | APG94 | CLI-wide migration, resolver, environment, analyzer, packaging |
| APG96 | Root Go CLI foundation, report path/recovery adapters, version/build information, embedded-resource foundation, thin Python report delegation | APG95 | Skill selection, environment, analyzer, remaining command migration, npm publication |
| APG97 | Deterministic skill/context resolver, embedded canonical corpus, budget enforcement, isolated agent-scoped materialization | APG96 | Environment or hotspot implementation, global-root mutation |
| APG98 | Portable environment profile/capture/load/resolve/storage APIs, CLI adapters, `.flakes` parity and thin-hook migration contract | APG96; uses APG97 identity conventions where applicable | Unauthorized `.flakes`, Nix, shell, or active-host cutover |
| APG99 | Structural-hotspot library, capability matrix, deterministic JSON/human renderers, bounded repository dogfood | APG96 | Growth/churn history, AI-authored metric authority, unreviewed parser dependency |
| APG100 | Remaining portable Go CLI migration, Python platform wheels/sdist bridge, npm launcher/platform packages, response migration, coordinated build manifests | APG97-APG99 | README rewrite, consumer readiness claim, publication |
| APG101 | Human README rewrite and detailed-document restructuring with historical preservation | APG100 user-facing surfaces | Runtime behavior, packaging semantic change, release |
| APG102 | Cross-consumer dogfood/readiness: JACA direct imports, CLI/Python/npm parity, scoped skills, environment, hotspots, supported targets, rollback | APG95-APG101 | Publication, tag, version rewrite beyond already prepared candidate |
| APG103 | v0.7.0 publication, GitHub/Go/PyPI/npm immutable readback, Nix handoff | Terminal green APG102 | Deployment or host activation not separately authorized |

The ten-phase shape is retained because reporting establishes the first public
library contract; the CLI then supplies shared version/resources; resolver,
environment, and analyzer can be reviewed independently; packaging depends on
all portable commands; documentation follows the stable user surface; and
readiness remains separate from publication.

## APG94 — architecture freeze

APG94 accepts ADR 0051 and produces the normative architecture, integration
boundary, this roadmap, and phase records. It resolves the Go root-module and
npm naming questions, preserves current Python/JACA/`.flakes` evidence, and
leaves the repository at version 0.6.0 with 39/39/39 skills, 14 stable and 25
provisional, 9,504 description bytes, and 9,492 characters.

Exit condition: all v0.7 themes have a concrete owner, API/schema or migration
boundary, independently reviewable phase, and explicit non-goal. No successor
implementation exists.

## APG95 — reporting library vertical slice

Create the root Go module and the `schema` and `report` packages. Implement
native Git exact-argv collection, normalized models, canonical rendering and
parsing, in-memory show/diff/operational results, and optional publication
semantics needed for parity. Add `internal/gitexec` and only the atomic helpers
the slice requires.

The current Python corpus is the compatibility oracle. Differential fixtures
must cover ordinary/root/merge commits, names and binary patches, staged and
unstaged state, untracked and intent-to-add files, drift, unsafe indexes,
operational relations, paths, transactions, interruption, and stable exit/error
classes. A separate temporary consumer module must import APG `report` without
the CLI or Python.

Exit condition: accepted byte/schema/error parity for the three maintained
commands and a JACA-importable public package. Python remains the active CLI
adapter until APG96.

APG95 accepted status: terminally accepted at operator commit `04f13598...`,
tree `fe3ca7a...`, with a standard-library-only Go 1.25
module, 22 accepted exact-byte differential cases, 11 rejected failure-class
cases, publication safety/recovery coverage, and an executable external-module
import. The exact reviewed closeout tree was committed without source-byte
change after dispatcher finalization could not own the dirty entry. APG96 is
the active authorized successor.

## APG96 — Go CLI and migration bridge

Add `cmd/apgr` as a thin adapter over `report`, including canonical report path
and recovery actions. Establish build information, release-version injection,
supported-target reporting, exact embedded-corpus identity, and the CLI error/
stdout/stderr conventions. Change the Python report routes and historical report
command names to delegate to the Go binary with parity tests.

Exit condition: report behavior has one semantic Go owner; checkout and Python
compatibility names remain usable; direct Go library calls remain independent
of `cmd/apgr`.

APG96 terminal status: `cmd/apgr`, private CLI/build-information owners, the
release-like Go build helper, canonical Python report delegation, and all three
historical compatibility delegations are implemented and accepted. The frozen
Python owner is test-oracle-only. Final wheel/npm binary bundling remains
APG100 work.

## APG97 — deterministic skill and context bundles

Turn the canonical `skills/` directory into the Go `skills` package without
moving or duplicating Markdown. Implement request/result schema v1, versioned
rule tables, exact identities, deterministic reasons/conflicts/composition,
fail-closed byte budgets, bundle fingerprints, and isolated direct-regular
materialization.

Qualify explicit selection, set-order invariance, no implicit profile chain,
unknown/contradictory fact refusal, budget overage without truncation, embedded
and checkout identity, atomic cleanup, and an agent launch that receives only
the selected discovery root.

Exit condition: a structured request produces one reproducible minimal bundle,
and global 39-skill discovery is absent from the qualified target agent.

APG97 terminal status: the 39-leaf embedded corpus, strict request/result/
manifest schemas, versioned source-backed rule and composition inventories,
fail-closed budgets, isolated atomic materialization, Go CLI surfaces, Python
consumer delegation, external Go import, and selected-only Codex discovery are
implemented and preserved by APG98.

## APG98 — portable environment snapshots

Implement `envsnap` profile validation, capture from an explicit environment
map, canonical JSON snapshots, deterministic fingerprints, no-churn owner-only
atomic storage, staleness visibility, isolated/overlay resolution, value-safe
diagnostics, and CLI render/run adapters.

Reconstruct the current `.flakes` behavior in APG fixtures and run parity
against its committed source evidence. Produce a separately executable consumer
cutover contract: APG becomes portable semantic authority only after parity;
`.flakes` retains its profiles, hooks, installation, and activation. APG98 does
not modify `.flakes`, Nix, or live shell state unless a separate task grants
that exact authority.

Exit condition: JACA can load and resolve a curated snapshot in-process without
sourcing shell code, and sensitive-name/value tests fail closed.

APG98 terminal status: the public provider-neutral `envsnap` package, strict
profile and snapshot schemas, explicit-map capture, canonical fingerprints,
owner-only locked no-churn storage, verified load/staleness, isolated/overlay
resolution, Go CLI adapters, Python delegation, bounded `.flakes` parity, and
the unexecuted thin-hook contract are implemented and preserved by APG99.

## APG99 — structural-hotspot analyzer

Implement `hotspot` with bounded deterministic walking, the frozen v1 capability
matrix, Go semantic metrics, Markdown/hybrid and declarative structural metrics,
explicit unavailable reasons, confidence, relative risk ranking, canonical JSON,
terminal output, and detailed Markdown.

Dogfood APG and a read-only JACA source snapshot. Verify no source execution,
no symlink escape, bounded file/byte/time behavior, cancellation, deterministic
ordering/fingerprints, machine consumption without Markdown parsing, and honest
low-capability rows. Any parser dependency requires its own authorized review
inside APG99 and may not widen the frozen language claims silently.

Growth/churn remains deferred beyond v0.7.

Exit condition: operators, JACA, and CI can consume stable JSON and humans can
read deterministic summaries without confusing unavailable metrics with zero.

APG99 terminal status: the public provider-neutral `hotspot` package, exact
root-safe bounded walker, frozen capability matrix, Go AST metrics, honest
structural/unavailable language rows, canonical report and fingerprint,
report-local ranking, concise terminal and detailed Markdown renderers, Go and
Python CLI routes, external Go consumption, and repeatable APG/JACA read-only
dogfood are implemented and preserved by APG100.

## APG100 — Go completion and multi-ecosystem packaging

Migrate the remaining portable CLI actions, including response capture, and
complete the Python strangler boundary. Retain the explicitly classified
repository-maintenance Python actions without duplicated portable semantics.

Build platform-specific Python wheels containing the exact Go binary, preserve
the `apgr` console script and `python -m` behavior, and define the toolchain-
requiring sdist path. Build `@knowledge-forge-ai/apgr` plus the three same-version
platform packages. All wrappers verify version, target, corpus fingerprint, and
binary hash and perform no runtime download.

Exit condition: supported Python and npm installs are standalone; unsupported
targets fail clearly; one version authority and one binary identity bind every
artifact; migrated commands have no second Python/JavaScript implementation.

APG100 terminal status: version `0.7.0` is the single editable authority;
response capture is Go-owned; Python and npm are verified thin front doors;
three reproducible target binaries feed three platform wheels and three npm
platform packages; the Go-source sdist rebuilds the standalone host wheel; and
one coordinated manifest binds the local candidate. Historical v0.6 and the
39-skill corpus remain preserved. The operator accepted the reviewed and
corrected closeout source after a dispatcher result-fence recognition failure;
the failure changed no source bytes. APG101 subsequently began under separate
authorization.

## APG101 — human documentation restructuring

Rewrite the root README to the frozen landing-page order. Create the detailed
CLI, Go, bundle, environment, hotspot, distribution, and history owners; update
navigation; preserve chronological and release material outside the README; and
keep governance/status ledgers auditable.

Exit condition: a new user can understand, install, and choose a consumption
path from the README, while phase archaeology remains available under `docs/`
and no behavior claim exceeds accepted implementation evidence.

APG101 terminal status: the root README is a concise landing page in the
frozen order; task-oriented navigation and the frozen CLI, Go, skill-bundle,
environment, hotspot, distribution, integration, governance, release, and
history owners are linked from `docs/README.md`; and the former README
chronology is preserved under `docs/history/releases-and-phases.md`.
Published v0.6.0 and the unpublished, locally qualified v0.7.0 release
candidate are explicitly distinguished. No runtime, package, schema, skill,
maturity, Nix, JACA, publication, or readiness behavior changes. APG102 began
only under a separate dispatcher assignment.

## APG102 — cross-consumer dogfood and readiness

Qualify the exact release candidate across:

- a real JACA internal adapter importing APG public Go packages with no cycle;
- in-memory generation of all three report records without `apgr` or a shell;
- Go CLI, Python, and npm output/exit parity;
- a task-scoped agent seeing only its resolved skill bundle;
- in-process curated environment resolution with separate secret injection;
- hotspot JSON consumption and APG/JACA repository reports;
- supported OS/architecture builds and isolated installations; and
- rollback and historical v0.6 compatibility.

The phase records unresolved target-owned failures rather than bypassing them.
It cannot publish.

Exit condition: one terminal readiness disposition with exact candidate
artifacts, hashes, known limitations, and operator publication packet.

APG102 terminal status: the exact v0.7.0 release candidate is reproducible
across three Go targets, three Python wheels and one source distribution, and
the npm launcher plus three platform packages. Every target binary receives a
real disposable runtime smoke. Direct, Python, and npm host paths share one
binary; current JACA consumes the public Go packages in process; a real
selected-only Codex probe excludes the global APG corpus; exact v0.6
reconstruction and isolated rollback pass; and the canonical broad gate is
green. Publication-excluded packets bind the precise candidate and APG103
readback plan. APG102 publishes and deploys nothing.

## APG103 — publication and immutable readback

Publish only the terminal APG102 candidate through separately authorized
operator mechanisms. Verify the annotated Git tag and GitHub assets, Go module
proxy, isolated Go consumer, PyPI wheels and sdist, npm launcher/platform
packages, checksums, embedded version/corpus/schema identities, historical
release preservation, and Nix adapter handoff.

Deployment and active host mutation remain separate even when publication is
green.

## Cross-phase policies

- No phase adds a skill leaf or changes the 14/25 maturity split by implication.
- The 9,527-byte canonical discovery ceiling is not raised for convenience.
- `CSS-QD-001..005` and `JS-QD-001..005` remain until a phase materially touches
  their owner and has existing debt authority.
- New schemas are versioned before release; pre-release correction is forward
  within the owning phase, while accepted/public schema changes require a
  compatibility decision.
- Every public Go API change after APG95 records JACA compatibility and rollback.
- Parser, packaging, and runtime dependencies require the repository dependency
  policy; this roadmap does not pre-authorize them.
- APG102 readiness and APG103 publication remain separate regardless of earlier
  success.

## Current stop

APG97 is the current complete candidate under dispatcher-owned finalization.
It implements only the accepted deterministic skill/context bundle slice and
leaves version 0.6.0 and the 39/39/39, 14/25, 9,504-byte, 9,492-character, and
9,527-ceiling invariants unchanged. APG98 is the frozen next phase but begins
only under a separately authorized dispatcher assignment. No environment,
hotspot, response, final packaging, JACA, `.flakes`, Nix, release, publication,
or successor implementation is authorized by this record.
