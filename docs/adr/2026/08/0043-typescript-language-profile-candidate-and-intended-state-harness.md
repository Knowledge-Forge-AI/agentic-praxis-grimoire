# ADR 0043: TypeScript Language-Profile Candidate and Intended-State Harness

## Status

Accepted with amendment (APG75). APG74 proposed one narrow TypeScript
language-profile candidate and one APG-owned TypeScript 7 intended-state
fixture harness. APG75 independently reconstructed the oracle, used three
separately preserved coherent correction rounds, closed every material
finding, and retained the corrected candidate provisionally.

## Context

APG73 accepted ADR 0042: language-profile production recovery with bounded
iterative hardening, human rejection authority, and TypeScript recorded as
essential with TypeScript 7 as the intended primary compiler generation.
ADR 0041 and the APG71/APG72 TypeScript architecture remain Rejected; that
history supplies falsification and source evidence only. No TypeScript
skill or integration owner exists. The current theme target checks its
TypeScript-family sources under an older compiler line, which is migration
baseline evidence, not the destination.

The candidate surfaces are the leaf
`skills/typescript-language-profile/SKILL.md`, the specification
`docs/specs/typescript-language-profile.md`, the navigation-only coverage
record `docs/specs/typescript-language-profile-scenario-coverage.md`, and
the fixture project `src/test/fixtures/apg74-typescript-intended-state/`.
All rights inputs are Apache-2.0 compiler packages, registry metadata, and
independently written fixture expression; no compiler, documentation,
target, or rejected-candidate text is copied.

## Decision

1. APG73 and accepted ADR 0042 are the governing baseline for this
   candidate; the rejected ADR 0041 architecture is not revived, copied, or
   adapted.
2. ADR 0041 remains Rejected.
3. TypeScript is essential to the product direction.
4. TypeScript 7 is the intended primary compiler generation.
5. The exact stable TypeScript 7 patch is selected fresh in APG74:
   `typescript@7.0.2` (npm `latest`; Apache-2.0; npm `gitHead` equal to the
   `microsoft/typescript-go` release tag `typescript/v7.0.2` commit), with
   rc, beta, next, and native-preview lines excluded.
6. TypeScript 6 compatibility is role-bound and conditional. The fixture's
   always-present disposition case records `not-required`: no exact APG74
   role independently requires a TypeScript 6 package, and a refresh
   condition is recorded for embedded checkers whose peer ranges exclude
   TypeScript 7.
7. The candidate owns narrow TypeScript-specific static semantics and
   type-erasure boundaries for an established source region, after exact
   compiler role, version, option values, project configuration, source
   kind, and declaration environment are established.
8. JavaScript source and runtime, JSX syntax and transform, embedded-host
   whole files, Node/browser/platform APIs, module loading, build and
   transform, compiler and configuration selection, and policy remain
   non-owners with exact routes.
9. Exact compiler roles and exact option values are required evidence; an
   option name without a value is not an option fact.
10. Package or lockfile presence never proves a compiler role is exercised.
11. Static success never proves emitted-JavaScript or runtime success.
12. Structural policy is deferred under ADR 0042: no numeric bands, no
    automatic JavaScript-to-TypeScript migration, and structural questions
    route to the project-design owner.
13. The candidate carries exactly twenty-four navigation scenarios,
    `APG74-TS-001` through `APG74-TS-024`, mapped to stable clauses in a
    navigation-only coverage record.
14. The intended-state fixture carries exactly fourteen target-facing
    cases, `APG74-FX-001` through `APG74-FX-014`, in one fixture project
    with a canonical manifest.
15. The TypeScript 6 compatibility-disposition case (`APG74-FX-010`) always
    exists and resolves to exactly `required` or `not-required`, never
    omitted and never implied from package presence.
16. The fixture distinguishes live target state from intended product state
    per case, with explicit `live_target_state`, `intended_product_state`,
    `temporary_compatibility`, and `retirement_condition` labels.
17. APG74's candidate remains exact authored history; APG75's Round 3 state is
    the provisionally integrated current candidate.
18. APG75 owns one catalog row, one relative projection, one general-router
    route, one project-selection entry, current-development release ownership,
    three maintained unit owners, and one integration owner.
19. APG75 used ADR 0042's iterative-hardening contract — candidate-independent
    reconstruction, failing-first maintained tests, three bounded rounds, and
    zero Critical/High before integration — and terminally accepts this ADR
    with amendment.
20. Public and active corrected v0.4.0 remain unchanged; APG75 current owners
    are explicitly excluded from historical v0.4 reconstruction.
21. TypeScript 6 remains `not-required` for the evidenced role set. A future
    exact role may bind a temporary TypeScript 6 compiler only with explicit
    product state, invocation evidence, retirement condition, and human-owned
    compatibility disposition.
22. APG75 grants no readiness, publication, deployment, stable-maturity,
    target-mutation, APG76, or successor authority.

## Consequences

- Development is 30 canonical skills, 30 catalog rows, 30 projections, 14
  stable and 16 provisional rows, 28 general routes, one ChatGPT-local route,
  and 29 checked edges.
- The fixture is executable authoring evidence: its scratch smoke checks
  (compiler version, clean project check, declaration-only emit, seeded
  defect failures) were run in APG74, while maintained failing-first tests
  remain APG75 work.
- The current theme target's migration delta (older compiler line, embedded
  checker peer ranges excluding TypeScript 7, desynchronized lockfile) is
  recorded evidence for the APG75 target gate, not a veto of the TypeScript
  7 destination.
- APG75's first two fresh reviews produced `repair-required`; Round 3 closed
  all remaining material proof defects. Terminal rejection or removal remains
  human authority under ADR 0042.
- If this ADR is rejected, the candidate and fixture remain preserved
  branch history, and no integrated state changes.

## APG75 amendment evidence

APG75 preserved exact APG74, rebuilt twenty-four semantic and fourteen fixture
vectors before candidate comparison, and applied three immutable corrections.
Fresh review after each round returned four High proof families, three High
proof families, and then zero findings respectively. The final exact
TypeScript 7 focused suite passed 78 tests. No Critical, High, Medium, or Low
debt is accepted.

The retained surface keeps `.tsx`, checked JavaScript, and embedded hosts under
their adjacent whole-file owners; separates package identity, role, product
state, and invocation evidence; treats TypeScript 7 as the Theme Forge product
destination rather than a reusable-profile default; and
does not infer TypeScript 6 compatibility from package presence. Integration
rollback removes only the TypeScript current owners and reconstructs the exact
pre-integration 29/29/29, 14/15, and 27/1/28 state while preserving APG74/APG75
history, this decision, Markdown, and corrected public and active v0.4.0.

## APG75A clarification

APG75A leaves this ADR Accepted with amendment and preserves the APG74 and
APG75 objects. The reusable profile consumes the exact compiler role, version,
and migration policy selected by a project; it does not choose TypeScript 7 or
any other destination generation. Theme Forge Terminal Nova retains its
project-specific TypeScript 7 destination and older-checker migration evidence.
Scenario 024 is project-neutral, while the separate target migration row keeps
that product decision explicit.

Selection and response remain independent axes. Responses are exactly
`proceed-routine`, `inspect-before-judgment`, `bounded-local-decision`, and
`stop-and-escalate`; `route-to-owner` remains a Selection token only. The
coverage record, maintained fixture README, and manifest now report the current
provisionally integrated lifecycle while preserving APG74 authorship. Standard
repository tests require an explicitly bound executable TypeScript 7.0.2
compiler and fail before test execution with an actionable prerequisite error
when it is absent or wrong. No compiler installation occurs as a test side
effect.
