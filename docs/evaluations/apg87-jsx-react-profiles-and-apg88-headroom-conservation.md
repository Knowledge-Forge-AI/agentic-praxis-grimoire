# APG87 JSX and React Profiles with APG88 Headroom Conservation

## Candidate result

APG87 accepts ADR 0049 with amendment and provisionally integrates exactly
`jsx-language-profile` and `react-component-profile`. Candidate development is
37 canonical skills, 37 catalog rows, 37 exact relative projections, and 37
discoverable entries, with 14 stable and 23 provisional rows and zero malformed
metadata. Dispatcher-owned pre-final review remains external to this candidate
and is not self-attested here.

## Profile boundaries and source basis

The JSX profile owns library-independent syntax and transformation only. Its
grammar source is the `react/jsx` draft at exact commit
`d614ce76e6ea996ea6dfa122f2a7be71ed96e6eb`; the source is CC-BY-4.0 and was
inspected on 2026-08-20. Official TypeScript JSX and TSConfig documentation was
inspected on the same date for `.tsx`, `jsx`, classic versus automatic modes,
and `jsxImportSource`. TypeScript documentation prose is CC-BY-4.0, website code
is MIT-licensed, and compiler source is Apache-2.0. JSX grammar is mutable and
defines no runtime semantics; TypeScript is one implementation rather than a
universal transform oracle. APG copies no upstream prose, grammar, code,
examples, or tables.

The React profile is calibrated to official React documentation and exact tag
`v19.2.6`, annotated object `2fcbe419ed90f863e6f67ce5b9738f38dbec640b`
and commit `eaf3e95ca92be7a23d3c9cc8ffd6f199a40be401`, released 2026-05-06 and
inspected 2026-08-20. React documentation prose is CC-BY-4.0, and repository
source is MIT-licensed. The profile synthesizes component purity, render/state
snapshots, tree-position identity, Effects, Hook rules, context, memoization,
and error-boundary facts without copying upstream prose, code, examples,
tables, or diagnostics. Mutable documentation, canary APIs, and
framework-integrated features require refresh before a behavior-bearing
correction, maturity review, or publication.

## Objective boundary evidence

The APG87 public-safe fixture separates all required owners. JSX retains
element/attribute/child, fragment, spread, expression-container boundary,
file-kind, and transform questions. TypeScript retains `.tsx` checking;
JavaScript retains expression evaluation; React retains render, Hook, and
reconciliation behavior; Node retains host loading. React retains state,
Effects, Hook rules, render/re-render, context, memoization, error boundaries,
and component-design test interactions. JSX, TypeScript, Vitest, and generic
test discipline remain independently selected siblings.

`mdx-profile` and `astro-profile` appear only as reserved route names in
falsification evidence and profile non-triggers. No canonical leaf, catalog row,
projection, metadata row, or capability route exists for either one. An absent
receiver remains an open project-owned obligation rather than a successful
handoff.

## Budget and plan-review disposition

Post-planning review found that spending the formal 651-byte maximum would
leave APG88 exactly 340 bytes, forcing both remaining profiles to the floor.
The corrected implementation targets the APG85 260-byte body mean instead:

| Measurement | Bytes |
| --- | ---: |
| JSX description | 248 |
| React description | 268 |
| APG87 pair | 516 |
| Post-APG87 total | 9,052 |
| Full-v0.6 delta from 7,967 | 1,085 |
| Remaining headroom to 9,527 | 475 |

Each description remains inside [170, 330], the pair remains inside [340,
651], the total remains below both 9,187 and 9,527, and APG88 retains 135 bytes
above its absolute floor. `libexec/apg_skill_library_check.py` is byte-identical
to APG86. APG039/APG040 remain relational and topology-agnostic; APG87 counts
and conservation values belong only to focused tests and phase evidence.

## Integration and compatibility

Canonical metadata is regenerated through the repository parser and stable
serialization shape and is source-digest-bound to all 37 leaves. Catalog,
projections, general capability routes, project default membership,
current-development public-surface audit inventories, focused tests, and test
inventory include both profiles. Historical public surfaces remain
version-bounded, and existing explicit project subsets do not gain JSX or React
implicitly.

Public and active v0.5.0, package version, dependencies, lockfiles, release
tags, publication configuration, and deployment state remain unchanged. No
advisory discovery or target mutation occurs.

## Verification

Failing-first focused tests initially failed on the absent leaves and
projections, then passed after implementation. Candidate verification covers
the profile and boundary contracts, description budget, topology and maturity,
metadata/resource synchronization, project membership and explicit-subset
preservation, current-development release surface, historical exclusion,
configured repository gates, record identity, change size, whitespace, and
the prohibited-scope audit. Exact observed commands and results belong to the
candidate handoff and later terminal operational record rather than being
invented here before they run.

## Limitations and stop

This phase validates reusable APG guidance and APG-owned fixtures. It does not
execute a target JSX transform or React renderer, mutate a component project,
establish browser or framework behavior, or prove an arbitrary target's
versions and options. No MDX/Astro implementation, APG88, advisory discovery,
version advancement, publication, deployment, remote push, or external target
mutation is authorized or performed.
