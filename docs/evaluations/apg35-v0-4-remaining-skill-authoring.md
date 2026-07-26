# APG35 v0.4 Remaining-Skill Authoring Evaluation

Phase ID: `APG35`

Evaluation date: 2026-07-25

## Authoring objective

APG35 authors the remaining v0.4 skill and architecture artifacts on a dedicated
authoring branch. It is an authoring phase, not an integration phase. It trials
the intended division of labor in which Claude authors skill procedures,
specifications, ADRs, ownership models, source and rights analysis, frozen
scenario contracts, structural thresholds, and the integration handoff, while
Codex owns fixtures, tests, integration, corrections, acceptance, adoption,
readiness, publication, and deployment.

Five candidate capabilities were authored: `go-test-profile`,
`matryer-is-test-profile`, `go-cmp-test-profile`, `go-testing-stack`, and
`nix-test-profile`.

## Candidate dispositions

| Candidate | Authoring disposition | Scenarios | Behavior corrections |
| --- | --- | ---: | ---: |
| `go-test-profile` | authoring-ready | 36 | 0 |
| `matryer-is-test-profile` | authoring-ready | 24 | 0 |
| `go-cmp-test-profile` | authoring-ready | 30 | 0 |
| `go-testing-stack` | authoring-ready | 24 | 0 |
| `nix-test-profile` | authoring-ready | 40 | 0 |

All five reached the authoring-ready threshold. None required a second material
correction, so no candidate is recorded as `deferred-material-defect` and all
five canonical leaves are present on the authoring branch. Each candidate
retains its single unused behavior-correction allowance.

The phase disposition is:

```text
authoring-complete-pending-codex-integration
```

## Proposed ADR status

ADR 0025, Go Testing Component and Stack Ownership, is **Proposed**. It is not
Accepted. It proposes thirteen decisions establishing native Go testing as the
permanent lifecycle owner, two optional component owners triggered only after
project dependency selection, and one thin composition owner that forces no
component and duplicates no component API. It records six alternatives, the
overlap risks, maintenance cost, rollback, and deferred decisions.

Acceptance requires Codex integration and validation. No additional ADR was
created: the Nix testing architecture is expressible in its specification
without a consequential decision that an ADR would be needed to record.

Two proposed specifications accompanied the APG35 authoring object. APG36
removed both after terminal review; APG37 later re-authored the Nix proposal,
and APG38 removed it after a new post-correction material defect. Their exact
authored forms remain available in immutable phase history.

## Source and rights classes

| Source family | Calibration | Rights |
| --- | --- | --- |
| Go source and source-derived `testing` package documentation | Go 1.26.0 and Go 1.25.0 supported; go1.26.5 and go1.25.12 current patches | BSD-3-Clause |
| General go.dev site prose and release history | Current official Go release pages | CC BY 4.0 except where noted |
| matryer/is | Release `v1.4.1`, read at tag | MIT |
| google/go-cmp | Release `v0.7.0` | BSD-3-Clause |
| Nix source and bundled reference manual | Source tag `2.35.1` | LGPL-2.1-or-later |
| Nixpkgs and NixOS source | Current manual sources | MIT, subject to component-specific exceptions |
| nix.dev independently authored content | Current tutorial | CC BY-SA 4.0 |

Versions are calibration evidence, not project requirements or a compatibility
matrix. No upstream prose, source, example, table, option list, or prompt
wording was copied or adapted. Every procedure is independently written
synthesis. Where a candidate refers to an upstream API, it does so as a factual
interface name.

## Scenario counts

One hundred fifty-four frozen scenario families were authored across the five
candidates, with identifier continuity verified and no gaps or duplicates. The
scenario tables are the authoritative frozen record for this phase because APG35
deliberately adds no executable fixture. The integration handoff names the
public-safe fixture Codex must create from each table.

## Correction counts

No candidate consumed its behavior-bearing correction allowance. Three changes
were made during review, none of which altered candidate behavior: a cleanup
ordering claim was verified against a primary source and found correct; the
matryer/is calibration was re-read at its release tag rather than the default
branch, with an identical result; and one publication-excluded release date was
corrected with a source discrepancy recorded rather than reconciled.

## Cross-skill review

Eight review lanes were executed covering native Go testing semantics,
matryer/is source and rights, go-cmp source and rights, the Go owner graph and
stack thinness, Nix testing taxonomy and evidence hierarchy, structural
thresholds and Red stops, the public and private and copied-expression boundary,
and the complete authoring diff. Fourteen integrated review questions were
answered.

**Review limitation, disclosed.** The assignment calls for fresh non-author
reviewers. This session's operating constraints prohibited spawning independent
reviewer agents, so every lane was executed by the same author as a separate
adversarial pass with each claim re-checked against a primary source. The passes
found and corrected one factual error and two unverified claims, so they were
not merely confirmatory, but they are not equivalent to independent review. This
materially weakens the review contract. Codex should re-run at least the native
Go testing, matryer/is, go-cmp, and privacy lanes with genuinely independent
reviewers before accepting ADR 0025.

Three ambiguities are disclosed rather than resolved: the composition trigger's
mechanical breadth, two deliberately unclosed Nix sandbox and release-series
gaps, and weaker calibration confidence in two structural bands.

## Explicit absence of integration and testing

APG35 added no flat projection, catalog row, router entry, release-policy entry,
strict inventory entry, executable fixture, or test. It changed no Python or
shell code and no excluded integration surface.

It ran no `bin/apg-test`, pytest, Bats, unit, integration, coverage, lifecycle,
release-candidate, readiness, or smoke check; no `go test`, Go benchmark, or
fuzz target; and no Nix evaluation, build, flake check, or NixOS virtual-machine
or container test.

Skill-library checks requiring integrated projections, catalog rows, and routes
were deliberately not run. Current checkers would not accept the five candidate
leaves as integrated library members today, because the surfaces they require
intentionally do not exist. That rejection is the expected consequence of an
authoring-only phase, not a defect in the candidates.

Only authoring-safe gates were run: repository and branch state, write-scope
review, frontmatter uniqueness, required headings, scenario count and identifier
continuity, ownership and trigger consistency, proposed ADR structure and status,
Markdown structure, local links, public-to-private dependency refusal, privacy
scan, source and rights completeness, copied-expression review, current-state
count claims, whitespace checks, complete staged-diff review, and the formal
commit-message checker.

## Branch-only delivery

The phase was delivered on `claude/apg35-v0.4-remaining-skill-authoring`, an
authorized deviation from APG's normal mainline development because the commit
intentionally contains unintegrated candidate leaves and no executable
integration. `main` was not moved. No merge, rebase, amend, or force push
occurred. Mainline adoption remains Codex- and maintainer-owned, and Codex
corrects the artifacts through forward commits rather than by rewriting the
authoring commit.

## Codex handoff

A publication-excluded Codex handoff records, for each candidate, its canonical
path, exact frontmatter, proposed `provisional` maturity, authoring disposition,
source and rights summary, owner and overlap, scenario count, structural
signals, Red stops, capability class and route trigger, proposed catalog and
projection data, the public-safe fixture and mirrored test owner Codex should
create, release-policy and inventory additions, expected count deltas, focused
test suggestions, uncertainties, rollback, correction allowance state, and ADR
dependency. All information needed to understand APG35's public boundary
remains in this evaluation and the exit; no public artifact depends on the
publication-excluded destination.

## Public, active, and target preservation

Public APG, the active public-backed v0.3.0 checkout, the reference repository,
RepoMap, personal skills, Codex configuration, and all target repositories are
unchanged. No Go module outside APG, Nix state, database, graph, container, VM,
deployment, or external service was touched.

Integrated development remains **25 canonical skills, 25 catalog rows, and 25
flat projections**, with fourteen stable and eleven provisional rows,
twenty-three general-router entries, one ChatGPT-local router entry, and
twenty-four checked route edges. Public and active v0.3.0 remain 19/19/19.

The five authored candidate leaves are candidate sources on an authoring branch.
They are not integrated library members, and none is claimed to be integrated,
tested, adopted, mature, published, or deployed.

## Next authorization boundary

No phase after APG35 is authorized. Native go-test integration, matryer/is
integration, go-cmp integration, Go stack integration and cross-component
dogfood, nix-test integration, cross-profile readiness, v0.4 pre-release smoke,
and v0.4 publication and local deployment each remain a separate future decision
requiring explicit maintainer authority.

## Subsequent APG36 disposition

APG36 verified that the maintainer's manual push placed the exact accepted
APG35 object on the remote Claude branch with the exact accepted APG34 object
as its sole parent. Its Git-show and associated operational records passed
integrity checks. APG36 preserved that commit and branch without amend, rebase,
squash, replacement, or movement. Exact Git identities remain outside public
project identity.

Fresh independent non-author review was rerun. It found more than one material
behavior correction in `go-test-profile`, `matryer-is-test-profile`,
`go-cmp-test-profile`, and `nix-test-profile`; each is
`deferred-material-defect`. `go-testing-stack` is
`rejected-no-independent-value` because its required native owner is not
retained and its trigger, thinness, duplicate-owner response, and degradation
contract need multiple corrections. ADR 0025 is Rejected.

APG35 remains a complete authoring phase. APG36's results do not rewrite it as
integration and do not retroactively change its authoring disposition.
