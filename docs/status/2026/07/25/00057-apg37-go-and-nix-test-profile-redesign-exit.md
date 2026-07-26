# APG37 Go and Nix Test Profile Redesign Exit

Phase ID: `APG37`

Status: **Complete — four replacement test-profile candidates authored from the
APG36 defect dossier; Codex integration pending**

Date: 2026-07-25

## Outcome

APG37 accepts APG36's dispositions, redesigns the four deferred candidates from
the publication-excluded defect dossier against reverified current primary
sources, proposes a component-only Go testing architecture with no composition
owner, freezes 130 scenario families, measures structural calibration, and
hands a complete integration package to a later separately authorized Codex
phase.

```text
candidate leaves authored:
  4

integrated current skills:
  25

catalog/routes/projections/tests:
  unchanged / not added

go-testing-stack:
  remains rejected and absent

ADR 0025:
  remains Rejected

ADR 0026:
  Proposed

public and active v0.3.0:
  unchanged
```

## Candidate results

| Candidate | Scenario families | APG36 families closed or removed | Authoring disposition |
| --- | ---: | ---: | --- |
| `go-test-profile` | 36 | 5 | `authored-pending-independent-review` |
| `matryer-is-test-profile` | 24 | 5 | `authored-pending-independent-review` |
| `go-cmp-test-profile` | 30 | 6 | `authored-pending-independent-review` |
| `nix-test-profile` | 40 | 5 | `authored-pending-independent-review` |
| `go-testing-stack` | — | — | `not-redesigned` |

All 24 APG36 material findings have a terminal authoring disposition: 22
closed in redesign and 2 removed as invalid requirements. None is unresolved
and none blocks authoring. No candidate is validated and no retention is
predicted.

## Architecture

[ADR 0026](../../../../adr/2026/07/0026-go-testing-component-profiles-without-a-stack-owner.md)
is **Proposed**: three independent Go testing owners, no composition owner,
no mandatory chain, and direct component triggers bounded by prior dependency
selection and an exact calibrated release.

[ADR 0025](../../../../adr/2026/07/0025-go-testing-component-and-stack-ownership.md)
remains **Rejected** and is not modified, superseded, or reopened. No
`go-testing-stack` leaf, specification, route, or subgraph exists.

Two specifications accompanied the APG37 authoring object. APG38 retained the
[Go testing component profile](../../../../specs/go-testing-component-profiles.md)
and removed the Nix proposal from the current tree after a new post-correction
material defect. The exact Nix authoring form remains in immutable APG37
history.

## Validation

Only authoring-safe checks ran.

| Gate | Result |
| --- | --- |
| Clean, remote-equal APG36 base and exact new branch | Passed |
| Write scope confined to authorized paths | Passed |
| Four unique candidate frontmatter names matching directories | Passed |
| Canonical heading shape: one H1 and one each of seven H2 owners | Passed |
| APG36 defect-closure matrix completeness | Passed: 24 findings, all terminal |
| Scenario counts and ID continuity | Passed: 36, 24, 30, 40 |
| APG35-to-APG37 scenario mapping completeness | Passed: all 130 predecessors mapped |
| No stack leaf, specification, or route | Passed |
| ADR 0025 Rejected; ADR 0026 Proposed | Passed |
| Source, version, and rights completeness | Passed for six source families |
| Structural calibration evidence | Passed with two declared sampling limits |
| Copied-expression review | Passed: no upstream expression reproduced |
| Public-to-private independence | Passed: no public file references a publication-excluded path |
| Current integrated count claims remain 25/25/25 | Passed |
| Markdown, local links, whitespace, privacy | Passed |
| Staged diff inspection and formal commit-message check | Passed |

Integration checkers whose expected failure would arise solely from absent
projections, catalog rows, routes, or tests were deliberately not run.

## Structural calibration result

The complete Go 1.25.10 standard-library and toolchain test corpus of 1,673
test files was measured directly. The APG35 numeric bands escalate 9.7% of
maintained upstream test files to crisis on line count alone and mark 50 files
as crisis-level on two signals at once, none of them defective. Every numeric
crisis cutoff was removed across all four candidates and replaced with
categorical conditions tied to ownership, truthfulness, safety, or
maintainability risk.

Two limits are recorded rather than concealed: the broader public-repository Go
sample was not obtainable in this environment, and no Nix test corpus was
measured, so the Nix structural signals rest on principle rather than evidence.

## Review limitation

The APG37 review was an adversarial **author self-review**, not an independent
non-author review. It corrected three defects in its own drafts and makes no
retention prediction. Codex must rerun full independent source, ownership,
structure, privacy, and rights review, create executable fixtures and
compatibility probes, and decide ADR 0026 before retaining any candidate. The
APG36 one-behavior-correction allowance and forward-only correction rule remain
in force.

## Not run

No project test, `bin/apg-test`, pytest, Bats, coverage, library integration
checker, lifecycle test, readiness check, smoke test, or release build ran. No
`go test`, benchmark, fuzz, race, or coverage run occurred. No Nix parse,
evaluation, build, flake check, package test, or NixOS test occurred. Source
inspection is not executable compatibility evidence.

## Delivery and stop boundary

APG37 delivers one formal authoring commit on
`claude/apg37-v0.4-go-nix-redesign`. `main` was not moved, merged, rebased,
amended, squashed, or force pushed, and no earlier phase history was rewritten.
The exact push and remote-equality result is recorded in the APG37 phase report
and its associated operational record.

No public, active, reference, RepoMap, personal, or target repository object
changed. Integrated development remains 25 canonical skills, 25 catalog rows,
and 25 flat projections; public and active v0.3.0 remain 19/19/19.

No phase after APG37 is authorized. Independent review, fixtures, probes, the
ADR 0026 decision, integration, dogfood, readiness, smoke, v0.4 publication,
deployment, and any successor phase each require a fresh maintainer request.
## Subsequent APG38 disposition

APG38 preserved the exact APG37 authoring commit and branch and made every
correction forward. The native Go and go-cmp candidates are retained
provisionally; matryer/is and Nix are deferred after new post-correction
behavior defects. ADR 0026 is Accepted without a stack owner. APG37's original
author self-review limitation and authoring-only outcome remain unchanged.
