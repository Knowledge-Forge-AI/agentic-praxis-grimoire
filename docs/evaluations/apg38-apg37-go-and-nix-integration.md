# APG38 APG37 Go and Nix Integration

## Outcome

APG38 accepts APG37 as a complete immutable authoring phase and integrates two
of its four replacement candidates after independent review and one coherent
correction cycle per candidate.

| Candidate | Outcome |
| --- | --- |
| `go-test-profile` | `retained-provisional` |
| `matryer-is-test-profile` | `deferred-material-defect` |
| `go-cmp-test-profile` | `retained-provisional` |
| `nix-test-profile` | `deferred-material-defect` |

ADR 0026 is Accepted for two directly triggerable Go component owners.
ADR 0025 remains Rejected. `go-testing-stack` remains rejected and absent.

## Authoring adoption

APG38 independently verified that the local and remote APG37 authoring branch
named the expected immutable authoring object, that its sole parent was APG36,
and that its managed Git and associated operational records were complete and
integral. The exact branch already existed remotely, so APG38 performed no
authoring-branch push and made no change to Claude's commit or branch.

All corrections are forward changes in APG38.

## Independent review and correction

### Native Go

Initial review corrected effective per-file language versions, `TestMain`
cleanup around explicit process exit, result-bearing versus resource-owning
goroutines, fuzz-cache versus repository-corpus ownership, retained artifacts,
benchmark version support, package-wide structural owners, adverse subject
versus harness classification, and source-expression wording.

The corrected procedure passed current Go source review and isolated Go 1.25.10
compatibility evidence. The 36 APG37 families remain ordered and continuous in
the executable fixture, with seven explicit APG38 outcome corrections.

### matryer/is

The exact v1.4.1 correction improved one-sided nil rendering, best-effort source
diagnostics, legitimate simple exact structured equality, one instance per
subtest, concurrent output ordering, adverse subject versus harness
classification, and removal fallback. Isolated probes exercised strict and
relaxed modes, all four assertion families, typed nil, custom helper
registration, diagnostics, and parallel subtests.

Fresh corrected-state review then found two material behavior defects. Nested
registered wrappers can preserve caller attribution, so nesting alone cannot
justify Orange. Repeated relaxed-mode continuations likewise cannot manufacture
Orange when the leaf's own rule says counts alone do not escalate severity.
Because the candidate had already used its correction cycle, APG38 deferred it.
Its current-tree leaf, fixture, focused test, route, projection, catalog,
policy, and inventory surfaces are absent.

### go-cmp

The exact v0.7.0 correction covers negative and NaN approximation parameters,
exact identity versus standard error matching, protected comparison versus diff
rendering, unexported-field ownership, adverse option tests, source-expression
wording, and removal fallback. Isolated probes exercised equality, diff,
sorting, comparer and transformer obligations, filters, ignore, unexported
responses, approximation, errors, time, panic, and protected diagnostics.

The 30 APG37 families remain ordered and continuous, with six explicit APG38
outcome corrections.

### Nix

The initial correction substantially improved cross-target phase gating,
loopback versus external network claims, package-associated test ownership,
tester/helper roles, mixed virtual-machine and container claims, physical
accounting, generated matrices, and capacity escalation. Two reviewers could
apply the corrected source-only structural model consistently.

Fresh corrected-state review then found a new material fact: Nix 2.35.1 enables
sandboxing by default on FreeBSD as well as Linux, while the candidate stated
that every non-Linux platform defaulted disabled. Because the candidate had
already used its one correction cycle, APG38 did not correct it again.
`nix-test-profile` is deferred and its current-tree leaf, fixture, focused
test, route, projection, catalog, policy, and inventory surfaces are absent.
No Nix command or execution surface ran.

## Structural calibration

Two independent Go reviewers classified a bounded corpus spanning a small
assertion library, a comparison library, a large parallel/integration-heavy
repository, and a goroutine-focused repository. Size alone never justified
Orange or Red. The corrected model:

- measures the real file, cross-file, or package lifecycle owner;
- separates the adverse subject from its test harness;
- permits isolated attributable responsibility families; and
- requires every Orange or Red to name a concrete risk.

Two independent Nix reviewers applied a representative source-only corpus.
They separated constructor role from evidence surface, physical accounting from
semantic dimensions, source-arm maximum from consumer co-scheduling, and
ordinary disclosed cost from concrete capacity risk.

## Owner graph

Representative native-only, assertion-only, comparison-only, and mixed tasks
produced no residual recurring composition work. Each retained profile is
directly selectable. Optional dependency owners require prior project
selection but do not require the native owner or each other. Cross-references
state ownership without sequencing invocation.

Candidate-independent removal deletes every integration surface and repairs
surviving references to a retained owner or project-owned fallback. No stack
leaf, specification, projection, fixture, test, route, or router subgraph
exists.

## Integrated state

Development contains:

- 27 canonical skills;
- 27 catalog rows;
- 27 checked flat projections;
- 14 stable and 13 provisional rows;
- 25 general-router entries;
- 1 ChatGPT-local entry; and
- 26 checked route edges.

Current-development release policy and strict inventory contain the two
retained profiles, their 66 fixture families, two focused contracts, and the
shared owner-graph contract. Immutable public and active v0.3.0 remain
19/19/19. A disposable v0.4.0 candidate is built and checked only as local
validation; it is not published.

## Second division-of-labor trial

The APG37 redesign substantially reduced the APG35 source-error burden and used
the APG36 dossier effectively, but APG38 still needed behavior correction in
all four candidates. Native Go and go-cmp corrections were bounded enough to
retain; matryer/is and Nix each exposed new post-correction behavior defects and
were deferred. Categorical calibration improved, but independent corpus review
remained essential.

The immutable authoring object and forward-only correction model preserved
authorship and shortened orientation. The trial is **supported with revised
guardrails**:

- provide the complete Codex defect dossier before redesign;
- make no authoring-phase retention prediction;
- require independent corpus review for categorical structural rules;
- keep exact-version bounds for third-party component profiles;
- allow one complete correction cycle rather than one-defect accounting;
- create no composition owner without demonstrated residual work; and
- leave fixtures, compatibility, integration, final records, and operations to
  Codex.

Two trials do not establish a permanent universal organization policy.

## Boundary

No retained candidate is promoted beyond provisional. No public or active
v0.3.0 object, target repository, Nix state, external service, or deployment is
changed. No readiness, smoke, release, publication, deployment, or successor
phase begins. No phase after APG38 is authorized.

## Subsequent APG39 authoring

A separately authorized APG39 authoring phase later re-authors the two
deferred candidates from the corrected-state defects this evaluation
records, on a Claude authoring branch, without changing this phase's
dispositions, the retained profiles, ADR 0025, ADR 0026, or the integrated
27/27/27 state. APG38 remains a complete integration phase whose terminal
dispositions are historical truth.
