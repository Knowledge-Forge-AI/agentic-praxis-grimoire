# APG86 GoMock and Vitest Profiles with Context-Budget Enforcement Exit

Phase ID: `APG86`

## Status

The replacement-work candidate accepts ADR 0048 with amendment, provisionally integrates
`gomock-test-profile` and `vitest-test-profile`, and activates the APG85 budget
contract. The candidate disposition is
`GOMOCK_VITEST_PROVISIONALLY_INTEGRATED`; dispatcher-owned pre-final review is
an external gate and is not self-attested by this record.

The original work process ended in `PROVIDER_TRANSPORT_FAILED` after planning
and post-plan review had completed. Its partial working-tree bytes were
recovered inside the same APG86 phase; no plan or reviewer was repeated.

## Result

1. GoMock v0.6.0 generation, controller, expectation, count, ordering,
   matcher, action, and diagnostic behavior has one direct component owner.
   Native Go testing, go-cmp, and Go language semantics retain their existing
   independent owners; no stack owner exists.
2. Vitest 4.1.x configuration, project, environment, assertion, mock, timer,
   concurrency, isolation, snapshot, and coverage-provider mechanics have one
   runner owner after project selection. Language, Node, React, test
   sufficiency, coverage policy, and dependency adoption remain outside it.
3. Diagnostics APG039 and APG040 enforce the v0.6 per-profile byte band and
   aggregate/discoverability/malformed contract through the canonical context
   report. APG014 is unchanged.
4. The checker remains topology-agnostic and contains no 35/35 constant, no
   7,967 enforcement baseline, and no 340-to-660 delta rule.
5. Catalog rows and prose, projections, routes, project and release
   inventories, packaged metadata, public-safe scenarios, tests, and current
   documentation are integrated together.

## Resulting state

- topology: 35 canonical / 35 catalog / 35 projections;
- discovery: 35 measured / 35 discoverable / zero malformed;
- maturity: 14 stable / 21 provisional;
- GoMock description: 276 UTF-8 bytes;
- Vitest description: 293 UTF-8 bytes;
- total description bytes: 8,536;
- delta from 7,967: 569 bytes; and
- remaining headroom under 9,527: 991 bytes.

## Verification

Focused budget, profile, component-owner, metadata, release-surface, and
explicit-selection checks pass. `apgr check skill-library`, `apgr check
record-identity --expect-allocated APG86`, canonical/package synchronization,
packaged context readback, the configured unit, integration, and combined
unit-integration gates, `git diff --check`, and the bounded scope audit pass
from the replacement candidate state.

## Limitations and stop

APG86 adds reusable guidance and APG-owned fixtures only. It adds no dependency
or lockfile, runs no target GoMock generator or Vitest suite, changes no package
version or publication identity, and supplies no advisory discovery surface.

No remote push, publication, deployment, target mutation, APG87, JSX, React,
MDX, Astro, or seventh v0.6 profile ran. APG87 remains separately authorized
only by a new maintainer assignment after APG86 disposition.
