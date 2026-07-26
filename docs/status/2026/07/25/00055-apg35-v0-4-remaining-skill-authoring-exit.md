# APG35 v0.4 Remaining-Skill Authoring Exit

Phase ID: `APG35`

Status date: 2026-07-25

Disposition: Complete — remaining v0.4 skill architecture authored; Codex integration and validation pending

## Scope and outcome

APG35 authors five remaining v0.4 candidate capabilities and their architecture
on the dedicated authoring branch `claude/apg35-v0.4-remaining-skill-authoring`.
It is an authoring phase. It integrates nothing, tests nothing, and adopts
nothing.

The five candidates are `go-test-profile`, which owns native Go `testing` and
`go test` semantics; `matryer-is-test-profile` and `go-cmp-test-profile`, which
own their libraries' specific behavior only after the target repository has
already selected the dependency; `go-testing-stack`, a thin optional composition
owner that forces no component and duplicates no component API; and
`nix-test-profile`, which routes among already-selected Nix testing surfaces and
keeps their evidence classes separate.

Primary-source calibration covers Go 1.26.0 and Go 1.25.0 with go1.26.5 and
go1.25.12 as current patch releases, matryer/is `v1.4.1` read at its tag,
google/go-cmp `v0.7.0`, and Nix source tag `2.35.1` with current Nixpkgs and
NixOS manual sources. Go and go-cmp are BSD-3-Clause; matryer/is is MIT; Nix
source and its bundled manual are LGPL-2.1-or-later; Nixpkgs and NixOS are MIT
subject to component-specific exceptions; independently authored nix.dev content
is CC BY-SA 4.0. These are calibration evidence, not project requirements. The
authored procedures are independently written synthesis with no copied or
adapted upstream expression.

One hundred fifty-four frozen scenario families were authored across the five
candidates, with identifier continuity verified. No candidate consumed its
behavior-bearing correction allowance.

## Resulting shape

- Authored candidate leaves: **five**, on the authoring branch only.
- Integrated development skills: **unchanged at 25** canonical skills, 25
  catalog rows, and 25 flat projections.
- Maturity rows: unchanged at fourteen stable and eleven provisional.
- Routers: unchanged at twenty-three general entries, one ChatGPT-local entry,
  and twenty-four checked route edges.
- Projections, routes, catalog rows, release policy, strict inventory,
  executable fixtures, and tests: **not added**.
- Public and active v0.3.0: **unchanged at 19/19/19**.
- ADR 0025 is created with status **Proposed**, not Accepted. No additional ADR
  was needed, because the Nix testing architecture is expressible in its
  specification without a separate consequential decision.
- Two proposed specifications are created under a new `docs/specs/` directory.
- No dependency, version, command, flag, coverage threshold, worker count,
  platform, CI workflow, external resource, release, publication, or deployment
  is selected.

Current checkers would not accept the five candidate leaves as integrated
library members, because the projections, catalog rows, router entries, release
policy, and inventory entries they require intentionally do not exist. That is
the expected consequence of an authoring-only phase. Codex must integrate each
candidate atomically before mainline adoption.

## Structural and semantic disposition

Each candidate that requires them defines concrete Green, Yellow, Orange, and
Red fallback bands: nine dimensions for native Go testing, six for matryer/is,
eight for go-cmp, and ten for Nix testing. `go-testing-stack` deliberately holds
four composition-only signals and no component dimensions. Every band set
defines measurement, coupling, generated and vendor treatment, project override,
legacy smallest-safe-fix behavior, and rollback. Bands are subordinate to
stricter project policy and are relaxable only through a bounded exception that
cannot touch safety stops.

Required Red stops number eleven, eight, ten, and twelve respectively, with the
stack carrying a nine-condition escalation contract instead. They cover
false-pass behavior, misleading failure attribution, resource leaks, unsafe
parallel sharing, uncontrolled nondeterminism, mocked behavior represented as
integrated, protected-data exposure, unsupported API or system claims,
comparer-property violations, hidden required behavior, evidence-class
confusion between evaluation and build and runtime and activation, unauthorized
destructive action, and crisis-level undecomposed ownership.

## Validation and review

| Gate | Result |
| --- | --- |
| Repository and branch state | Passed: clean tree from the remote-equal APG34 mainline baseline; new branch created without collision |
| Exact write-scope review | Passed: only authorized paths |
| Frontmatter name uniqueness | Passed: five unique names, no collision with the 25 existing leaves |
| Required headings | Passed: all eight canonical headings in each of the five candidates |
| Scenario count and identifier continuity | Passed: 36 + 24 + 30 + 24 + 40 = 154, no gaps or duplicates |
| Owner and trigger consistency | Passed: no duplicate owner or contradictory trigger |
| Proposed ADR structure and status | Passed: ADR 0025 is Proposed |
| Markdown structure and local links | Passed |
| Public-to-private dependency refusal | Passed: no public artifact references publication-excluded material |
| Privacy and confidentiality scan | Passed |
| Source, version, and license completeness | Passed for all four source families |
| Copied-expression review | Passed: independent synthesis throughout |
| Public current-state count claims | Passed: integrated development stated as 25 everywhere |
| Whitespace checks | Required before and after staging |
| Complete staged-diff review | Required before commit |
| Formal commit-message checker | Required before and after the APG35 commit |
| Fresh non-author review | **Not satisfied as specified.** Independent reviewers could not be spawned in this session; eight lanes were executed by the author as separate adversarial passes with primary-source re-checks. One factual error and two unverified claims were found and corrected. Codex must re-run at least the native Go testing, matryer/is, go-cmp, and privacy lanes independently before accepting ADR 0025. |
| Managed reports | One postcommit Git-show record and one explicitly associated operational record required |
| APG remote equality | Required after pushing the authoring branch |

Integration checkers whose failure would be caused solely by the intentionally
absent projections, catalog rows, routes, release policy, and inventory were
deliberately not run, because their failure would carry no information about the
candidates. `bin/apg-test`, pytest, Bats, coverage, lifecycle, release-candidate,
readiness, and smoke suites were not run for the same reason. No `go test`, Go
benchmark, or fuzz target ran, and no Nix evaluation, build, flake check, or
NixOS virtual-machine or container test ran, because APG35 authors procedure and
holds no execution authority over the technologies it describes.

## Unresolved questions

Recorded truthfully rather than resolved: the composition trigger's mechanical
condition is satisfied whenever any single optional component is selected, so
its discriminating weight rests on a judgment-based second condition; the
per-platform Nix sandbox defaults and relaxed-sandbox semantics were not read
from a primary source and no default is stated; the current NixOS and Nixpkgs
release series was not re-verified and is stated nowhere; two structural bands
have weaker calibration confidence; and the frontmatter description lengths were
not checked against any checker limit.

## Rollback and next boundary

Rollback before merge means deleting the local and remote authoring branch under
separate human authority. `main` is not rewritten. No mainline object depends on
the candidates, because no integration surface was added.

Each candidate is independently removable. Removing a component profile leaves
the others useful and leaves the stack composing what remains. Removing
`go-testing-stack` loses only explicit composition guidance. `nix-test-profile`
shares no dependency with the four Go candidates. If ADR 0025 is rejected rather
than accepted, rollback is deleting the four Go candidate leaves and abandoning
the branch.

No phase after APG35 is authorized. Native go-test integration, matryer/is
integration, go-cmp integration, Go stack integration and cross-component
dogfood, nix-test integration, cross-profile readiness, v0.4 pre-release smoke,
and v0.4 publication and local deployment each remain a separate future decision
requiring explicit maintainer authority. No candidate is claimed integrated,
tested, adopted, mature, published, or deployed.

## Subsequent APG36 disposition

APG36 verified the maintainer's manual push: the remote Claude branch resolves
to the exact accepted APG35 object, whose sole parent is the exact accepted
APG34 object. The APG35 Git-show integrity summary and explicitly associated
operational record passed. Claude's commit and branch were preserved without
rewriting or movement. Exact Git identities remain in managed and
publication-excluded evidence.

Fresh independent non-author reviews were rerun. `go-test-profile`,
`matryer-is-test-profile`, `go-cmp-test-profile`, and `nix-test-profile` each
needed more than one material behavior correction and are
`deferred-material-defect`; `go-testing-stack` is
`rejected-no-independent-value`. ADR 0025 is Rejected. APG36 converted all 154
families to transient fixtures, established failing-first contracts, ran a
disposable pinned Go compatibility harness, and removed every non-retained
candidate through a forward commit.

APG35 remains complete as an authoring phase. This subsequent evidence does not
rewrite its original result, report body, or historical scope as integration.
