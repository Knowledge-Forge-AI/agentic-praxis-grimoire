# APG41 v0.4 Readiness and Pre-Release Smoke

## Objective and entry

APG41 accepts exact APG40 and closes the v0.4 development surface by reviewing
all retained provisional owners, exercising representative cross-profile
routing, checking compatibility and packaging, constructing a disposable exact
v0.4.0 candidate, and smoking that candidate in isolated roots. APG41 does not
publish, deploy, promote maturity, mutate a target repository, or authorize a
successor phase.

Entry verification reproduced APG40's Git-show and associated operational
records byte for byte from the live Git object and supplied report. Local and
remote development mainlines were equal, APG40 had exact APG39 as its sole
parent, historical authoring branches were unchanged, and record namespaces
made APG41 and exit 00061 available. No ADR 0028 is needed.

## Current surface and architecture

The retained surface is 28 canonical skills, 28 catalog rows, and 28 relative
projections: 14 stable and 14 provisional. The general router has 26 direct
entries, the ChatGPT-local router has one entry, and the checker owns 27 route
edges. Cross-profile use remains independent and creates no mandatory chain.

ADR 0025 remains Rejected, ADR 0026 remains Accepted and controlling, and
ADR 0027 remains Rejected. `go-test-profile` and `go-cmp-test-profile` therefore
remain direct component owners. `go-testing-stack` remains absent.
`matryer-is-test-profile` remains a historical deferred candidate, is not in
v0.4.0, and is not a pending APG41 item.

## Provisional readiness

The public readiness fixture owns one trigger, non-trigger, owner-boundary,
project-input, adverse-or-stop, evidence-class, limitation, disposition, and
removal case for every provisional row.

| Provisional skill | APG41 disposition | Principal release-note limitation |
| --- | --- | --- |
| `chatgpt-manager-workflow` | `ready-provisional-with-limitation` | Repeated fresh-client use remains limited |
| `composing-approved-roadmap-assignments` | `ready-provisional-with-limitation` | Ordinary use beyond prepared APG assignments remains limited |
| `converting-bash-scripts-to-python` | `ready-provisional-with-limitation` | No live target conversion or cutover |
| `dockerfile-profile` | `ready-provisional-with-limitation` | Static review only; no daemon, build, registry, or runtime |
| `go-cmp-test-profile` | `ready-provisional-with-limitation` | Exact v0.7.0 source and fixture review; no target dependency execution |
| `go-language-profile` | `ready-provisional-with-limitation` | No target build, race, fuzz, cgo, or platform matrix |
| `go-test-profile` | `ready-provisional-with-limitation` | No target module test or broad Go runtime suite |
| `minitest-test-profile` | `ready-provisional-with-limitation` | Static fixture review; no target Ruby or Minitest execution |
| `nix-test-profile` | `ready-provisional-with-limitation` | Source and fixture review only; no Nix execution |
| `postgresql-database-profile` | `ready-provisional-with-limitation` | No database connection or operational probe |
| `pytest-test-profile` | `ready-provisional` | APG current-host execution does not imply universal compatibility |
| `ruby-language-profile` | `ready-provisional-with-limitation` | No target Ruby or engine matrix execution |
| `sqlite-database-profile` | `ready-provisional-with-limitation` | No database open or runtime probe |
| `vagrantfile-profile` | `ready-provisional-with-limitation` | Static review only; no evaluation, provider, or machine operation |

No row is promoted. Representative process-only, language-only, domain-only,
mixed-owner, project-policy, and non-trigger cases preserve direct routing,
project authority, and evidence-class boundaries. The six newer v0.4 profiles
also pass their deeper static or current-host dogfood lanes.

Dogfood found one coherent release-readiness wording defect: the Minitest,
Dockerfile, and Vagrantfile removal sections did not all remove their public
scenario fixtures and the latter two embedded obsolete historical catalog
counts. APG41 corrected those candidate-independent removal descriptions and
their focused contracts. Fresh corrected-state review found no remaining
material defect. No behavior correction, owner redesign, new skill, or ADR was
needed.

## Candidate, compatibility, and smoke

Repository-owned release tooling constructs two independently built disposable
v0.4.0 candidates with identical declared manifests, trees, release commits,
annotated tags, references, modes, and projection targets. Each candidate
contains all and only the current public surface: 28 canonical skills and 28
projections, required licensing and provenance payloads, no `private/`, no
development-only absolute path or Git identity, and neither excluded candidate.
Immutable v0.1.0 through v0.3.0 reconstruction remains valid.

On the current macOS host, Python entry points compile and report help,
configured Bats owners execute, relative projections resolve, deterministic
sorting and manifests agree, executable modes survive candidate construction,
local links resolve, and release identity parses as v0.4.0. Current wrappers
and helpers are Python, so no `/sh` or `/bash` launcher enters the release
checker's shell-syntax branch. Cross-platform behavior, target-language
runtimes, container or virtual-machine operation, Nix execution, and external
services were not run and are not claimed.

From an unpacked candidate using isolated HOME, XDG, cache, project, install,
and log roots, public-surface and skill-library checks pass in text and JSON.
General and ChatGPT-local routes validate. Full, repeated, and subset project
projection; invalid-skill refusal; empty-input behavior; removal; and
user-scoped install, check, and uninstall pass without using the active v0.3.0
checkout. Temporary roots are removed after evidence capture and no residue is
left outside them.

## Validation and disposition

Focused correction and APG41 readiness contracts pass. The configured unit,
integration, and combined suites pass with their owned expected fixture skips
and coverage thresholds. Current skill-library, public-release, record
identity, privacy, provenance, rights, Markdown, local-link, whitespace,
Python-compilation, shell-syntax, command-help, project-lifecycle, and strict
inventory gates pass. Public and active v0.3.0 remain unchanged at 19/19/19.

The terminal APG41 disposition is
`ready-for-publication-with-provisional-limitations`. The retained surface has
no material release blocker, while its explicitly recorded source-only and
unrun-runtime evidence limits should remain visible in release notes. This
disposition is evidence for a separate maintainer decision; it grants no
publication, active deployment, signing, announcement, or successor authority.

## No publication or active deployment

No publication or active deployment occurs in APG41. The v0.4.0 candidate is
disposable, no public tag or release is created, active public-backed v0.3.0 is
not used as a candidate base, and no target repository or external service is
mutated.
