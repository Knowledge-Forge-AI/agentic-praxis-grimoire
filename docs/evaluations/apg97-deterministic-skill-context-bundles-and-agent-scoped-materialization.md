# APG97 Deterministic Skill Context Bundles and Agent-Scoped Materialization

## Result

APG97 implements accepted ADR 0051's task-scoped context slice. The canonical
39 Markdown leaves remain in place and are embedded by the new public Go
`skills` package with both flat and ChatGPT-nested patterns. Reconstructed
embedded metadata converges on the existing transitive corpus fingerprint
`0509803b3c12e0366917a341c9d56945d7966897953415acf0c997254e1331c1`.

The public package supplies `Corpus`, `Metadata`, `Resolve`, `Materialize`, and
enumerable rule/edge inventories. Strict request, result, and manifest v1
contracts use canonical JSON and deterministic SHA-256 identities. Selection
is structured, model-free, source-table-backed, and minimal. Composition is
informational and never selects siblings or adjacent profiles.

## Resolver and budget behavior

Explicit selections and unique structured facts form one sorted union. Exact
facts without a unique owner are recorded as exclusions. Consumer-specific
conflicts are represented in results and refused. Unknown fields, duplicate
JSON keys, unknown identifiers, duplicate set members, contradictory facts,
unsupported forms, and invalid budgets fail closed.

Result identity includes reasons, source facts, exclusions, conflicts, and
selected-only composition edges. Every set-input permutation produces the same
normalized request and bundle fingerprints. Body, description, and
initial-context budgets retain exact measured and limit facts. A failed limit
never causes truncation, dropping, substitution, or partial materialization.

## Materialization result

Materialization verifies rather than reruns a prior result. It reads only
embedded body bytes and publishes a private staging view atomically under an
absolute physical caller-owned parent. Directories are 0700 and files are
0600. Each selected ID receives one flattened direct regular `SKILL.md`; one
canonical manifest records source and materialized identities without local
path, time, or host data.

The full bundle fingerprint names the final root. Exact verified roots are
idempotently reusable; mismatched roots, symlinked parents, tampered results,
stale corpus identities, unsafe owners/modes, and ambiguous collisions are
refused. Cancellation removes only invocation-owned staging state and exposes
no partial final root.

## Consumer and discovery qualifications

A disposable external Go module imported only
`github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/skills` through an exact
local replacement. It enumerated 39 embedded leaves, resolved the same request
twice to one bundle, materialized in process, and verified exact body readback.
Its dependency list contained the public `skills` package and no APG internal
package or `cmd/apgr` process.

The external qualification selected `planning-repository-work`, with bundle
fingerprint
`f31a12a15c7aaa0a9e5000578b6970c16306196e252a02a3259846b388ae9481`
and manifest fingerprint
`afc7c5e5fa44b573d42ebca3c43376930477e0d4d86d465cc29575cf34926bfb`.

A real Codex 0.147 app-server launch used a disposable HOME, CODEX_HOME, and
project. Its project discovery surface received only that materialized root.
The intersection of returned skills with the canonical APG 39-ID set was
exactly `planning-repository-work`; no non-selected APG ID or operator global
APG root appeared. Codex built-in system skills were present independently and
are not APG corpus entries. The installed protocol's generated `skills/list`
schema lacked the documented newer extra-user-root field, so qualification used
Codex's supported isolated project discovery surface instead.

## CLI and bridge result

Go `skills list` and `skills context-report` preserve the Python text and JSON
oracle forms while using embedded authority. `skills resolve` consumes only a
strict file or explicit stdin request, and `skills materialize` consumes only a
prior result and explicit destination parent.

Normal Python list/context routes now delegate to Go. Resolve/materialize are
new Go-backed Python convenience routes. Python retains project, user,
install-global, flatten, configuration, and selection-file maintenance. There
is no migrated-route semantic fallback.

Build information now reports injected expected and embedded actual corpus
fingerprints plus their equality. A release-like mismatch fails closed; source
defaults remain truthful development state.

## Preserved boundaries

Version remains 0.6.0. Skills remain 39 canonical, 39 catalog rows, 39
projections, and 39 discoverable, with 14 stable / 25 provisional, zero
malformed, 9,504 description bytes, 9,492 characters, and the 9,527-byte
ceiling. No skill body or maturity changes. Current v0.6 artifacts remain
immutable.

APG97 changes no live/global skill root, environment snapshot, hotspot,
response, JACA, `.flakes`, Nix, final wheel/npm package, public release, or
version. APG98 remains separately authorized.

## Verification and disposition

Focused implementation evidence covers corpus reconstruction, nested paths,
strict parsing, mapping/refusal/no-chain matrices, set permutations, budget
boundaries, result tampering, materialization identity/modes/links/collision/
concurrency/cancellation, Go CLI behavior, Python bridge parity, external Go
consumption, real isolated Codex discovery, build-information convergence, and
the preserved APG96 report/CLI surface. Exact final command counts and the
accepted tree belong to the APG97 dispatcher handoff evidence.

Terminal disposition:
`V07_SKILL_CONTEXT_BUNDLES_READY_FOR_APG98`.

APG98 was separately authorized and preserves this result.
