# ADR 0048: GoMock and Vitest Profiles with Context-Budget Enforcement

## Status

Accepted with amendment

## Decision date

2026-08-20

## Context

ADR 0047 freezes six v0.6 profile owners, their composition boundaries, a
170-to-330 UTF-8 byte description band, a 9,527-byte full-library ceiling, and
explicit project selection as the only projection authority. APG86 is
authorized to implement only the first pair, `gomock-test-profile` and
`vitest-test-profile`, and to activate the deferred budget enforcement.

The interrupted first APG86 work process ended with a provider transport
failure after writing a partial working tree. This decision applies to the
replacement candidate reconstructed from those surviving bytes; the failed
process is execution history, not acceptance evidence.

## Decision

1. Integrate `gomock-test-profile` provisionally as the owner of GoMock v0.6.0
   generation modes, generated-mock classification, controller lifetime,
   expectations, counts, ordering, matchers, actions, and GoMock diagnosis
   after a project has already selected that dependency.
2. Preserve `go-test-profile`, `go-cmp-test-profile`, and
   `go-language-profile` as direct independently selectable siblings. No Go
   testing stack or composition owner is created.
3. Integrate `vitest-test-profile` provisionally as the owner of Vitest 4.1.x
   runner configuration, projects, environments, assertions, mocks, timers,
   concurrency, isolation, snapshots, and coverage-provider mechanics after a
   project has already selected Vitest.
4. Keep JavaScript and TypeScript semantics, Node host behavior, React
   component behavior, generic test sufficiency, coverage policy, dependency
   choice, and release policy with their existing or named future owners.
5. Add diagnostics APG039 and APG040 to
   `libexec/apg_skill_library_check.py`. APG039 applies the frozen byte band
   only to the six v0.6 names. APG040 obtains the canonical report through
   `context_footprint_report(blobs=...)` and fails on an aggregate over 9,527
   bytes, relational discoverability disagreement, or malformed metadata.
6. Keep the shipped checker topology-agnostic. Exact APG86 topology belongs to
   tests and phase evidence; no 35-skill constant, 7,967-byte baseline, or
   340-to-660 delta rule is added to the generic checker.
7. Integrate the canonical leaves, catalog rows and prose, exact relative
   projections, capability routes, packaged metadata, current project and
   release inventories, focused fixtures and tests, and current documentation
   as one phase. Existing explicit managed subsets remain unchanged.
8. Record 276 GoMock bytes, 293 Vitest bytes, 8,536 total description bytes, a
   569-byte delta from 7,967, and 991 bytes of remaining headroom under 9,527.

## Alternatives considered

- Hard-code 35 canonical and 35 discoverable skills in the shipped checker:
  rejected because APG87 and APG88 must change topology without changing the
  relational budget contract.
- Enforce a 340-to-660 APG86 delta from 7,967: rejected because the per-profile
  band already implies it and a generic baseline would obstruct an authorized
  correction to an existing description.
- Spend both 330-byte maxima: rejected to conserve the aggregate budget for
  the four more tightly coupled web profiles.
- Add runtime dependencies or execute target GoMock and Vitest projects:
  rejected as unnecessary and outside this profile-integration phase.

## Consequences

Development becomes 35 canonical skills, 35 catalog rows, 35 projections, and
35 discoverable entries, with 14 stable and 21 provisional rows. The v0.6
budget is mechanically fail-closed without changing APG014 or retroactively
constraining v0.5 profiles. New default project installation sees 35 skills,
while explicit existing subsets retain only their recorded membership.

The profiles are source-qualified guidance, not proof that any target project
uses the named dependencies or that a runner, generator, snapshot, coverage
provider, or integration boundary executed. Stable maturity, advisory
discovery, APG87, version advancement, publication, deployment, target
mutation, and remote push remain outside this decision.
