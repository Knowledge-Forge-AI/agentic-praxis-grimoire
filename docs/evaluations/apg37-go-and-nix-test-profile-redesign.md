# APG37 Go and Nix Test Profile Redesign Evaluation

Phase ID: `APG37`

Evaluation date: 2026-07-25

## Objective and accepted starting state

APG37 redesigns the four candidates APG36 deferred, proposes a component-only
Go testing architecture without a composition owner, and hands a complete
integration package to a later separately authorized Codex phase. It is an
authoring phase: it integrates nothing, runs no project or upstream test suite,
and validates no candidate.

APG36 is accepted as complete and correct. Its dispositions are retained
unchanged:

| Candidate | APG36 disposition | APG37 treatment |
| --- | --- | --- |
| `go-test-profile` | `deferred-material-defect` | redesigned |
| `matryer-is-test-profile` | `deferred-material-defect` | redesigned |
| `go-cmp-test-profile` | `deferred-material-defect` | redesigned |
| `nix-test-profile` | `deferred-material-defect` | redesigned |
| `go-testing-stack` | `rejected-no-independent-value` | **not redesigned** |

`go-testing-stack` remains rejected and absent. No stack leaf, specification,
route, router subgraph, or successor was created. **ADR 0025 remains
Rejected**; APG37 does not modify, supersede, or reopen it.

The distinction APG37 relies on is that a deferral records a defective authored
contract while the stack's rejection records an absent capability. Component
ideas may therefore be redesigned; the composition owner may not.

## Four replacement candidates

Each candidate was rewritten from the APG36 defect dossier against reverified
current primary sources, not edited from its APG35 text.

| Candidate | Scenario families | Authoring disposition |
| --- | ---: | --- |
| `go-test-profile` | 36 | `authored-pending-independent-review` |
| `matryer-is-test-profile` | 24 | `authored-pending-independent-review` |
| `go-cmp-test-profile` | 30 | `authored-pending-independent-review` |
| `nix-test-profile` | 40 | `authored-pending-independent-review` |

All 130 frozen families map to APG35 predecessors, and every APG36-affected
family is explicitly corrected. Leaf lengths are 243–275 lines; none requires a
decomposition justification.

The most consequential corrections are:

- the native profile no longer states that the API requires a package-level
  test hook to call the runner, and instead separates normal lifecycle,
  intentional project-owned suppression, and accidental omission, the last of
  which reports success with nothing executed;
- language semantics derive from the module directive and per-file build
  constraints rather than from the installed toolchain;
- the fuzzing surfaces — setup and seed registration, target execution,
  transient generated inputs, and durable persisted failures — are separated;
- the universal goroutine-join rule is deleted and replaced by a bounded
  truthfulness contract plus the actual method restrictions;
- the matryer/is profile reverses its typed-nil claim, because that library
  treats two nil-like operands as equal, and restores the library's own helper
  registry while stating that it is not the native mechanism;
- the go-cmp profile separates the two sorting contracts, since slice sorting
  is explicitly not required to be total while map sorting is;
- the Nix profile replaces a scalar evidence hierarchy with a claim-relative
  decision matrix, and corrects flake-check, sandbox, phase-default, and
  consumer overclaims.

## Proposed ADR 0026

[ADR 0026](../adr/2026/07/0026-go-testing-component-profiles-without-a-stack-owner.md)
proposes three independent Go testing owners and **no** composition owner. It
remains `Proposed`; deciding it belongs to Codex.

Two specifications accompanied the APG37 authoring object. APG38 retained the
[Go testing component profile](../specs/go-testing-component-profiles.md) and
removed the Nix proposal from the current tree after a new post-correction
material defect. The exact Nix authoring form remains in immutable APG37
history.

## Source and rights

| Family | State | Rights |
| --- | --- | --- |
| Go standard library and toolchain | 1.25.10 | BSD-licensed source and source-derived package documentation; general site prose separately licensed |
| matryer/is | `v1.4.1` | MIT |
| google/go-cmp | `v0.7.0` | BSD-3-Clause |
| Nix | 2.35 reference | LGPL-2.1-or-later |
| Nixpkgs and NixOS | 26.05 | MIT, subject to component exceptions |

Every source was inspected on 2026-07-25 and recorded with its facts used,
facts rejected from APG35, facts deliberately not generalized, and refresh
condition. The Go rights split between source-derived material and general site
prose is recorded rather than collapsed into one class, and the mutable Nix,
Nixpkgs, and NixOS sources carry exact locators with the inspection date as
their controlling state marker.

All APG text is independently written synthesis. No upstream prose, code,
example, table, or diagnostic text is copied or adapted; API identifiers are
used descriptively as facts.

## Defect closure

| Group | Families | Closed in redesign | Removed as invalid | Unresolved |
| --- | ---: | ---: | ---: | ---: |
| `go-test-profile` | 5 | 4 | 1 | 0 |
| `matryer-is-test-profile` | 5 | 4 | 1 | 0 |
| `go-cmp-test-profile` | 6 | 6 | 0 | 0 |
| `nix-test-profile` | 5 | 5 | 0 | 0 |
| Cross-cutting privacy and ledger | 3 | 3 | 0 | 0 |
| **Total** | **24** | **22** | **2** | **0** |

The two removed requirements were APG35 rules that current source does not
support: the universal goroutine-join rule and an assertion-family crisis band
that could not be reached without the calibration already being invalid. No
defect is unresolved and none blocks authoring.

The stack's own correction families are out of scope rather than closed,
because the stack is not redesigned.

## Structural calibration

APG36 found the APG35 structural bands uncalibrated and false-escalating.
APG37 tested that by measurement rather than by intuition, using the complete
Go 1.25.10 standard-library and toolchain test corpus of 1,673 test files.

Applying the APG35 native bands to that corpus escalates 9.7% of maintained
upstream test files to crisis on physical line count alone and 3.7% on
test-function count. Fifty files are simultaneously crisis-level on both
signals, including some of the most carefully maintained test files in the
language. None of them is defective.

Every numeric crisis cutoff was therefore **removed** rather than retuned,
across all four candidates, and replaced with categorical conditions that
escalate on ownership, truthfulness, safety, or maintainability risk. A
structural finding must now name the risk a count stands for.

Two calibration limits are recorded rather than concealed: the broader
public-repository Go sample was not obtainable in this environment, and no Nix
test corpus was measured at all, so the Nix structural signals rest on
principle rather than evidence.

## Review limitation

The APG37 review was an **adversarial author self-review, not an independent
non-author review**. The same agent authored the redesign, froze the scenarios,
measured the calibration, and reviewed the result.

It found and corrected three defects in its own drafts: an unsupported
corpus-based claim in the Nix leaf and specification, three over-long trigger
descriptions, and a refresh condition omitting a component the profile depends
on. It makes **no retention prediction**. APG35's self-review predicted five
retentions and all five failed independent review, primarily on primary-source
errors.

Codex must rerun full independent source, ownership, structure, privacy, and
rights review before retaining any candidate.

## Not run

No project test, library integration checker, lifecycle test, readiness check,
smoke test, or release build ran. No `go test`, benchmark, fuzz, race, or
coverage run occurred, and no Nix parse, evaluation, build, flake check,
package test, or NixOS test occurred.

Static inspection of a local read-only Go installation and of tagged upstream
sources is recorded as source evidence, not as executable compatibility
evidence. No candidate carries executable evidence of any kind.

## Delivery and integration boundary

APG37 delivers one formal authoring commit on
`claude/apg37-v0.4-go-nix-redesign`. `main` was not moved, merged, rebased, or
amended, and no earlier phase history was rewritten. The exact push result is
recorded in the APG37 phase report and its associated operational record.

A publication-excluded integration handoff records, for each candidate, the
proposed catalog wording, router entry, projection, fixture, mirrored test
owner, compatibility probe, release-policy and inventory additions, expected
count delta, uncertainties, rollback, and correction allowance. Public APG
records do not depend on that material.

If Codex later retains all four candidates, integrated development would become
29 skills, 29 catalog rows, and 29 projections with 15 provisional rows, 27
general-router entries, and 28 checked route edges. Those are predictions about
a possible later state, not current facts.

## Current state preserved

Integrated development remains **25 canonical skills, 25 catalog rows, and 25
flat projections**, with fourteen stable and eleven provisional rows,
twenty-three general-router entries, one ChatGPT-local entry, and twenty-four
checked route edges. The authoring branch carries four candidate leaf
directories that are deliberately not integrated, so no projection, catalog
row, router entry, maturity row, release-policy owner, test-inventory entry, or
fixture was added.

Public and active v0.3.0 remain **19/19/19** and unchanged. No public, active,
reference, RepoMap, personal, or target repository object was modified.

No candidate is integrated, adopted, mature, compatible, published, or
deployed.

## Next authorization boundary

APG37 authorizes nothing further. Independent review, executable fixtures,
compatibility probes, the ADR 0026 decision, integration, dogfood, readiness,
smoke, v0.4 publication, deployment, and any successor phase each require fresh
maintainer authority.
## Subsequent APG38 disposition

APG38 preserved and adopted the exact APG37 authoring object, independently
reviewed all four candidates, and corrected forward without rewriting APG37.
`go-test-profile` and `go-cmp-test-profile` are retained provisionally.
`matryer-is-test-profile` and `nix-test-profile` are deferred after new
post-correction behavior defects. ADR 0026 is Accepted for the two retained Go
component owners; ADR 0025 remains Rejected; `go-testing-stack` remains absent.
APG37 remains a complete authoring phase whose self-review limitation is
historical truth.
