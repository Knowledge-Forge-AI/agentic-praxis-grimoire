# APG76 CSS Target-First Fixture

One historical APG76 fixture carrying fourteen CSS decision scopes drawn from
freshly pinned targets and the candidate scope. APG77 is the maintained test
owner. The fixture is independently authored and contains no target source.

## What this fixture is and is not

Every file here is independently written APG expression. No target stylesheet,
specification example, CSS Working Group test, or browser-documentation sample
was copied. The pinned targets informed **which** decision scopes are worth
carrying; they supplied no bytes.

The fixture contains no generated output, no build output, no source map, no
package manifest, no lockfile, and no `node_modules`. Nothing here is installed,
compiled, transformed, or rendered by APG76.

## Shape

- `fixture-manifest.json` freezes the fourteen cases `APG76-FX-001` through
  `APG76-FX-014` with their paths, artifact class, whole-file owner, selection
  state, decision scope, three tool-role states, present and required evidence,
  owned and non-owned conclusions, routes, provenance, and the authoring
  boundary APG76 chose.
- `src/base.css` — `APG76-FX-001`.
- `src/cascade.css` — `APG76-FX-002` through `APG76-FX-005`.
- `src/custom-properties.css` — `APG76-FX-006` and `APG76-FX-007`.
- `src/conditions.css` — `APG76-FX-008`.
- `src/nesting.css` — `APG76-FX-009`.
- `src/units-and-color.css` — `APG76-FX-010` and `APG76-FX-011`.
- `src/host-boundary.astro` — `APG76-FX-012`.
- `src/generated-boundary.css` — `APG76-FX-013`.
- `src/unknown-environment.css` — `APG76-FX-014`.

Every manifest path exists and every file is owned by at least one case.
Several cases share one file because they name distinct decision scopes within
it; that is deliberate compactness, not overlap.

## Closed state vocabularies

`css_selection` is one of `selected`, `embedded-route`, `route-to-owner`, or
`non-trigger`. Each of `parser_role_state`, `transform_role_state`, and
`browser_role_state` is one of `known`, `not-selected`, `not-required`, or
`unresolved`, and they mean different things:

- `known` — the role is selected and identified; only then may an exact
  package, version, or invocation be bound to it;
- `not-selected` — no such role is selected, and the case's owned conclusion
  does not need one;
- `not-required` — the role exists in the wider picture but this case's owned
  conclusion is independent of it;
- `unresolved` — the case's decision depends on the role and its identity is
  unknown, which is itself the finding.

No case binds a concrete parser, transformer, browser, version, or invocation
to a `not-selected` or `unresolved` role. Role state is decision-scoped: a
browser required for a render observation does not block an independent static
conclusion.

## Why no parser smoke ran

APG77 freshly established a framework-selected pipeline: Astro 7.1.3 selects
Vite 8.1.5, whose documented default CSS transformer is PostCSS and whose
production CSS minifier is Lightning CSS. Package presence alone is not proof,
and no target build ran, so actual invocation and emitted output remain
unobserved. The browser remains unresolved. The twenty-one source modules are
question-specific normative authorities, not project compiler options.

Current lifecycle: `provisionally-integrated-with-known-debt` after APG77D; the
profile is provisionally integrated and remains below stable maturity.
APG76 remains the historical author and the APG77 maintained test owner remains
controlling, with APG77A through APG77C qualification history preserved. ADR 0044 is
Accepted with amendment. The fixture is maintained current evidence; compact
v3 is supporting qualification evidence only. Four accepted Medium
qualification limitations block stable maturity, but no semantic, target,
runtime, release, or rollback debt is accepted.

## `expected_authoring_boundary` is not an oracle

That field records what APG76 chose while authoring a case and why — for
example, declaring no writing mode so a logical mapping stays required
evidence. It is authoring provenance. APG77 reconstructs every semantic and
fixture expectation independently and must not read this field, the manifest,
or the candidate prose as an expected result.
