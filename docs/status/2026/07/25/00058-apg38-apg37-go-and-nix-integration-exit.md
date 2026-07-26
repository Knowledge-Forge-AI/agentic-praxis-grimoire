# APG38 APG37 Go and Nix Integration Exit

Phase ID: `APG38`

Status: **Complete — two APG37 Go component profiles integrated provisionally,
the matryer/is and Nix candidates deferred, and ADR 0026 accepted**

Date: 2026-07-25

## Outcome

APG38 accepts APG37 as a complete immutable authoring phase, independently
reviews all four redesigned candidates, converts their 130 scenario families
into executable fixtures, establishes failing-first evidence, performs one
coherent correction cycle per candidate, and gives every candidate a terminal
disposition.

| Candidate | Scenario families | Disposition |
| --- | ---: | --- |
| `go-test-profile` | 36 | `retained-provisional` |
| `matryer-is-test-profile` | 24 | `deferred-material-defect` |
| `go-cmp-test-profile` | 30 | `retained-provisional` |
| `nix-test-profile` | 40 | `deferred-material-defect` |

The native Go and go-cmp fixtures and their 66 families are integrated. The
matryer/is and Nix leaves, fixtures, focused tests, projections, catalog rows,
routes, current release-policy entries, and inventory entries are removed
forward from the resulting tree. Their APG37 authoring forms remain in
immutable history, and their terminal dispositions remain in the APG38
evaluation.

## Authoring adoption

The APG37 branch already existed remotely at the expected immutable authoring
object, with APG36 as its sole parent. Its Git-show record and explicitly
associated operational record passed integrity review, so APG38 performed no
authoring-branch push. Claude's commit and branch were not rewritten or moved.
All candidate corrections are forward changes in APG38.

## Architecture and current state

[ADR 0026](../../../../adr/2026/07/0026-go-testing-component-profiles-without-a-stack-owner.md)
is **Accepted** for two independent, directly triggerable Go component owners.
Native testing owns lifecycle where material; the exact-version go-cmp owner
remains optional and requires prior project dependency selection.
Representative composed tasks exposed no residual recurring coordination
owner.

[ADR 0025](../../../../adr/2026/07/0025-go-testing-component-and-stack-ownership.md)
remains **Rejected**. No `go-testing-stack` leaf, specification, projection,
fixture, test, route, or router subgraph exists.

The resulting development state is:

```text
canonical skills / catalog rows / flat projections:
  27 / 27 / 27

maturity:
  14 stable / 13 provisional

general-router / ChatGPT-local entries / checked route edges:
  25 / 1 / 26

public and active v0.3.0:
  unchanged at 19 / 19 / 19
```

## Candidate evidence

The native Go procedure passed current primary-source review and disposable Go
1.25.10 compatibility probes covering `TestMain`, effective file language
versions, goroutine reporting and resource ownership, bounded fuzzing and
replay, helper attribution, cleanup, isolation, selection, and caching.

The exact google/go-cmp v0.7.0 procedure passed canonical-source, rights, and
disposable compatibility review. Its probes covered equality and diff,
ordering, option obligations, unexported values, approximation and panic
boundaries, and protected-data rendering.

The corrected matryer/is candidate passed isolated compatibility probes, but
terminal corrected-state review found two new behavior defects: nested
registered wrappers can preserve caller attribution, and repeated relaxed-mode
continuations do not justify count-only severity escalation. Its correction
cycle was already exhausted, so it was deferred rather than corrected again.

Independent reviewers applied the categorical Go structural model to a bounded
mixed corpus without escalating ordinary maintained tests on physical size.
Every Orange or Red required a concrete ownership, truthfulness, safety, or
maintainability risk.

The corrected Nix source-only model passed inter-reviewer structural
consistency, but fresh corrected-state review found a new material platform
fact: the selected Nix release enables sandboxing by default on FreeBSD as well
as Linux. The candidate had already used its one correction cycle, so it was
deferred rather than corrected a second time. No Nix command or execution
surface ran.

## Validation

| Gate | Result |
| --- | --- |
| Retained fixtures and focused contracts | Passed: 66 continuous families; 10 tests and 35 subtests |
| Skill library | Passed in text and JSON at 27/27/27 |
| Full unit component | Passed: 308 tests; statements 4315/5042; branches 1544/1928 |
| Full integration component | Passed: 271 tests and 2 expected skips; statements 4426/5042; branches 1544/1928 |
| Project lifecycle, routers, release policy, and strict inventory | Passed for the 27-skill development set |
| Public v0.3 compatibility | Passed unchanged at 19/19/19 |
| Python, shell, help, Markdown, links, privacy, provenance, identity, and whitespace | Passed |
| Disposable current-development v0.4.0 candidate | Built and checked without publication |
| Fresh terminal independent review | Passed all ten required surfaces |
| External-state preservation | Passed for public, active, reference, RepoMap, personal, and target boundaries |

No combined suite, race suite, broad benchmark or fuzz suite, second Go
toolchain, Nix execution, target-repository test, readiness check, smoke test,
release, publication, deployment, or successor phase ran.

## Division-of-labor assessment

The second trial is **supported with revised guardrails**. APG37 used the APG36
defect dossier effectively and materially reduced source and structural
defects, but all four candidates still required one behavior correction cycle
and matryer/is and Nix exposed new post-correction defects. Immutable author history,
forward-only corrections, exact version bounds, independent corpus review, no
retention prediction during authoring, no composition owner without residual
work, and Codex ownership of fixtures, compatibility, integration, final
records, and operations remain necessary. Two trials do not establish a
permanent universal organization policy.

## Delivery and stop boundary

Mainline adoption preserves the exact APG37 object followed by one formal
APG38 forward commit, using fast-forward-only adoption and one normal push.
Neither Claude authoring branch is moved.

No retained candidate is promoted beyond provisional. No public or active
v0.3.0 object, target repository, Nix state, external service, or deployment
changes. No phase after APG38 is authorized. Readiness, smoke, v0.4 release,
publication, deployment, and any successor phase require a fresh maintainer
request.

## Subsequent APG39 authoring

A separately authorized APG39 authoring phase later re-authors the two
deferred candidates from this exit's corrected-state defects on a Claude
authoring branch. This exit's status, dispositions, and counts are
unchanged; APG39 records its own result in exit 00059.
