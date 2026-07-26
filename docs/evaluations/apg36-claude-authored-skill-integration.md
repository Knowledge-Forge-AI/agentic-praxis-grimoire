# APG36 Claude-Authored Skill Integration Evaluation

Phase ID: `APG36`

Evaluation date: 2026-07-25

## Objective and immutable adoption

APG36 independently evaluates the five APG35 candidates, preserves Claude's
exact authoring commit, integrates only candidates that meet the one-correction
and evidence gates, decides ADR 0025, and adopts the exact two-commit APG35 then
APG36 history only after the resulting tree passes.

The remote Claude branch was verified at the exact accepted APG35 object with
the exact accepted APG34 object as its sole parent. APG35's Git-show integrity
summary and explicitly associated operational record matched the fetched
object. The maintainer's manual push is accepted as verified external delivery,
not a defect. The authoring commit and branch are unchanged. Exact development
Git identities remain in managed and publication-excluded evidence.

## Independent candidate dispositions

| Candidate | Current source and rights | Fixture and compatibility evidence | Behavior corrections | Disposition |
| --- | --- | --- | ---: | --- |
| `go-test-profile` | Go release and `testing` sources; BSD source/package-doc and CC BY 4.0 site-prose split | 36 continuous families; native lifecycle harness passed | 5 | `deferred-material-defect` |
| `matryer-is-test-profile` | canonical `v1.4.1`, MIT; typed-nil and custom `Helper` claims contradicted | 24 continuous families; pinned constructor/mode/nil/helper harness passed | at least 5 | `deferred-material-defect` |
| `go-cmp-test-profile` | canonical `v0.7.0`, BSD-3-Clause; sorting and option claims contradicted | 30 continuous families; pinned equality/options/panic/redaction harness passed | 6 | `deferred-material-defect` |
| `go-testing-stack` | project-owned architecture; no independent upstream rights payload | 24 continuous families; cross-owner contract exposed trigger/thinness defects | at least 4 plus failed precondition | `rejected-no-independent-value` |
| `nix-test-profile` | Nix 2.35.2 and Nixpkgs/NixOS 26.05; rights classes confirmed | 40 continuous families; source/static only, no Nix execution | 5 | `deferred-material-defect` |

The 154 frozen scenario families were mechanically converted into five
public-safe JSON fixtures before integration surfaces existed. ID continuity,
uniqueness, order, and content passed. Mirrored contracts then produced the
intended failing-first evidence: fixture contracts passed, while projections
and routes were absent and the stack's cross-owner contract failed.

The fixtures and tests are not retained because the candidates are not
retained. Independent-review records identify every known affected family
rather than silently rewriting authored outcomes.

## Source and behavior findings

The native profile needs independent changes to `TestMain`, effective language
version, fuzzing, goroutine policy, and structural calibration. The matryer/is
profile reverses typed-nil behavior and omits `(*I).Helper`, then adds separate
trigger, diagnostic, and structural defects. The go-cmp profile incorrectly
requires total ordering for `SortSlices` and needs separate transformer,
unexported, approximation, diagnostic, and structural repairs.

The Nix profile incorrectly says flake checking builds all derivation-valued
outputs, treats unlike evidence surfaces as a scalar hierarchy, overgeneralizes
sandbox and package defaults, and contains contradictory structure
measurement. The stack cannot survive without its required native owner, and
ordinary native-plus-one-component work does not establish a residual
composition problem.

No copied or adapted upstream expression was found. A literal
publication-excluded destination was removed from the APG35 public evaluation,
and the Go rights class was split between source-derived material and general
site prose.

## ADR and resulting architecture

ADR 0025 is **Rejected**. The proposed split itself is not adopted because all
three component contracts require redesign, while the stack has no viable
retained graph and requires multiple independent corrections. This is a
resolved negative decision rather than an unresolved architecture question.

Existing language, repository, testing-process, and project-policy owners remain
unchanged. Development remains:

```text
25 canonical skills
25 catalog rows
25 flat projections
14 stable rows
11 provisional rows
23 general-router entries
1 ChatGPT-local entry
24 checked route edges
```

No APG35 candidate receives a projection, catalog row, route, release-policy
entry, strict inventory entry, maturity row, or current fixture. Public and
active v0.3.0 remain immutable at 19/19/19.

## Disposable execution

A fully temporary Go module used Go 1.25.10 with dedicated home, cache, module
cache, workspace-off, working, and output roots. Exact matryer/is `v1.4.1` and
go-cmp `v0.7.0` were pinned. Native lifecycle, cleanup, temp/environment,
working-directory, parallel stop, `TestMain`, matryer/is failure mode and typed
nil, and go-cmp option, panic, sorting, and redaction cases passed. The entire
temporary root was removed.

No Nix evaluation or build ran. The installed Nix was older than the reviewed
source, candidate source review had already failed retention, and creating
store/cache effects would not improve the terminal decision. No target
repository test ran.

## Division-of-labor trial

The APG35 handoff was materially useful: immutable authorship, candidate
boundaries, source families, complete scenario IDs, thresholds, rollback, and
integration-surface predictions made independent review efficient. Its
self-review did not reliably validate source semantics or structural
false-escalation; all five retention predictions failed.

The bounded trial result is:

```text
supported with required guardrails
```

Another bounded trial may use the same division only with immutable author
history, independent Codex review, Codex-owned fixtures, one correction
allowance, forward-only correction, individual dispositions, no adoption
before a passing resulting tree, and Codex-owned final tests, status, reports,
publication, and deployment. This is not a permanent universal policy.

## Scope boundary

APG36 performs integration disposition and historical adoption only. It does
not start readiness, smoke, release, publication, deployment, or a successor
phase. Deferred candidates and any future Go or Nix redesign require fresh
maintainer authority.

## Subsequent authoring note

APG37 used this evaluation and its publication-excluded records as the
controlling defect dossier and redesigned the four deferred candidates on an
authoring branch. It did not revive `go-testing-stack` or reopen ADR 0025, both
of which remain rejected. APG36's dispositions above are unchanged, and APG37
integrated nothing. See the
[APG37 evaluation](apg37-go-and-nix-test-profile-redesign.md).
