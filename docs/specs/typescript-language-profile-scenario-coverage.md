# TypeScript Language Profile — Scenario Coverage

## Status and scope

- Current lifecycle: provisionally integrated after APG75 and APG75A
- ADR 0043: Accepted with amendment
- Historical authoring phase: APG74
- Coverage role: navigation-only
- Semantic authority: maintained scenario fixture plus human/compiler review
- Status: navigation record for the provisionally integrated profile under
  [ADR 0043](../adr/2026/08/0043-typescript-language-profile-candidate-and-intended-state-harness.md)
- Candidate:
  [skills/typescript-language-profile/SKILL.md](../../skills/typescript-language-profile/SKILL.md)
  and the [candidate specification](typescript-language-profile.md)
- Fixture:
  [`src/test/fixtures/apg74-typescript-intended-state/`](../../src/test/fixtures/apg74-typescript-intended-state/README.md)

This record is navigation-only: it maps each scenario to the stable clauses
a reviewer should read and, where applicable, to the fixture case that
represents it. It states no expected consequences and is not a behavior
oracle. The maintained scenario fixture plus human/compiler review owns
semantic conclusions; a row here proves only that the supporting clauses can
be found.

## Clause inventory

Twenty-four stable clause IDs exist, each exactly once across the candidate
leaf and specification. Leaf clauses: `TS-TRIGGER`, `TS-NONTRIGGER`,
`TS-EVIDENCE`, `TS-UNKNOWN-STOP`. Specification clauses:
`TS-COMPILER-GENERATION`, `TS-COMPILER-ROLES`, `TS-OPTIONS`,
`TS-SOURCE-KIND`, `TS-ASSIGNABILITY`, `TS-NARROWING`, `TS-GENERICS`,
`TS-OVERLOADS`, `TS-TYPE-OPERATORS`, `TS-STRICT-OPTIONS`,
`TS-IMPORT-EMIT`, `TS-DECORATORS`, `TS-DECLARATIONS`,
`TS-GENERATED-DECLARATIONS`, `TS-CHECKED-JS`, `TS-TSX`,
`TS-EMBEDDED-HOST`, `TS-STATIC-RUNTIME`, `TS-STRUCTURE-DEFERRED`,
`TS-ROLLBACK-AND-PROVENANCE`.

`TS-NONTRIGGER` and `TS-STRUCTURE-DEFERRED` are operational-only clauses:
they bound every scenario's handling rather than support a numbered
scenario, and no row references them.

## Scenario-to-clause map

| Scenario | Short purpose | Supporting clause IDs | Fixture case |
| --- | --- | --- | --- |
| APG74-TS-001 | Ordinary `.ts` under exact CLI checker, version, project, and option evidence | `TS-TRIGGER`, `TS-EVIDENCE`, `TS-OPTIONS` | APG74-FX-001 |
| APG74-TS-002 | Structural assignability versus nominal intuition | `TS-ASSIGNABILITY` | APG74-FX-001 |
| APG74-TS-003 | Union narrowing and exhaustiveness | `TS-NARROWING` | APG74-FX-001 |
| APG74-TS-004 | Generic inference under an exact compiler version | `TS-GENERICS`, `TS-EVIDENCE` | — |
| APG74-TS-005 | `strictFunctionTypes` exact-value consequence | `TS-STRICT-OPTIONS`, `TS-OPTIONS` | — |
| APG74-TS-006 | `exactOptionalPropertyTypes` exact-value consequence | `TS-STRICT-OPTIONS`, `TS-OPTIONS` | — |
| APG74-TS-007 | `noUncheckedIndexedAccess` exact-value consequence | `TS-STRICT-OPTIONS`, `TS-OPTIONS` | APG74-FX-002 |
| APG74-TS-008 | `any`, `unknown`, and `never` static distinction | `TS-TYPE-OPERATORS` | — |
| APG74-TS-009 | `satisfies` versus type assertion | `TS-TYPE-OPERATORS`, `TS-STATIC-RUNTIME` | APG74-FX-001 |
| APG74-TS-010 | Overload signatures and implementation signature | `TS-OVERLOADS` | — |
| APG74-TS-011 | Type-only imports and `verbatimModuleSyntax` | `TS-IMPORT-EMIT` | APG74-FX-003 |
| APG74-TS-012 | Enum or const-enum static/emit boundary | `TS-IMPORT-EMIT`, `TS-STATIC-RUNTIME` | — |
| APG74-TS-013 | Decorators under exact compiler and exact regime | `TS-DECORATORS`, `TS-OPTIONS` | — |
| APG74-TS-014 | Unknown compiler role or exact version | `TS-UNKNOWN-STOP`, `TS-COMPILER-ROLES` | APG74-FX-013 |
| APG74-TS-015 | Unknown consequence-bearing option value | `TS-UNKNOWN-STOP`, `TS-OPTIONS` | APG74-FX-014 |
| APG74-TS-016 | `.mts` source kind | `TS-SOURCE-KIND` | APG74-FX-002 |
| APG74-TS-017 | `.cts` source kind | `TS-SOURCE-KIND` | APG74-FX-003 |
| APG74-TS-018 | Handwritten declaration file | `TS-DECLARATIONS` | APG74-FX-004 |
| APG74-TS-019 | Generated declaration provenance and edit boundary | `TS-GENERATED-DECLARATIONS`, `TS-ROLLBACK-AND-PROVENANCE` | APG74-FX-005 |
| APG74-TS-020 | Checked JavaScript bounded analysis | `TS-CHECKED-JS` | APG74-FX-008 |
| APG74-TS-021 | `.tsx` whole-file and JSX boundary | `TS-TSX` | APG74-FX-006 |
| APG74-TS-022 | Embedded TypeScript in Astro or another host | `TS-EMBEDDED-HOST` | APG74-FX-007 |
| APG74-TS-023 | Declaration-only emit, emitted JavaScript, and runtime false-completion | `TS-STATIC-RUNTIME`, `TS-GENERATED-DECLARATIONS` | APG74-FX-011, APG74-FX-012 |
| APG74-TS-024 | Project-selected primary compiler role plus conditional compatibility role | `TS-COMPILER-GENERATION`, `TS-COMPILER-ROLES` | APG74-FX-009, APG74-FX-010 |

## Fixture-case column

A fixture case in the final column is the intended-state harness artifact
that represents the scenario's shape, together with that case's manifest
row (compiler roles, exact option facts, present/required evidence, and
state labels). A dash means the scenario is exercised through clause prose
alone in APG74: those scenarios (generic inference, `strictFunctionTypes`,
`exactOptionalPropertyTypes`, `any`/`unknown`/`never`, overloads, enums,
and decorators) use compiled counterexamples in the maintained failing-first
tests, where each expected consequence is reconstructed independently rather
than copied from this profile. No
process-invariant rows exist here: the generic iterative-hardening
contract of ADR 0042 owns review process, round budget, and severity
handling, and this record deliberately restates none of it.

## Reachability

Every clause ID is referenced by at least one row above or named an
operational-only clause; no row names an unknown clause. Coverage is 24/24
scenarios, each exactly once. Fixture cases APG74-FX-001 through
APG74-FX-014 all appear in the fixture manifest, and every one of the
fourteen is cited by at least one row above.

## Limitation

A row says where to look, not that the destination suffices. APG74's historical
author review checked navigation and clause presence only. Current semantic
authority remains the maintained scenario fixture plus human/compiler review.
