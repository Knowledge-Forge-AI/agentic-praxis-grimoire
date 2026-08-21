---
name: react-component-profile
description: Use when React component judgment is material to composition, props, rendering, state, effects, hooks, context, memoization, error boundaries, or component testing; not for JSX syntax, language typing, runner mechanics, routing, styling, MDX, Astro, or metaframeworks.
---

# React Component Profile

Lifecycle: `provisionally-integrated`.
Lifecycle ADR: `Accepted with amendment`.

## Core principle

Apply React-specific judgment only when a current decision materially depends
on host-independent component semantics: component composition and prop
contracts; render and re-render behavior; state identity and updates; the
Effect model; the Rules of Hooks and their failure modes; context;
memoization; error boundaries; or the interaction between component design and
component testing.

Keep the boundary test literal: the answer must remain valid for a React
component rendered by any host. If the answer depends on Astro, MDX, a router,
bundler, server/data framework, browser API, or deployment platform, route that
decision to the narrowest accepted owner or the project-owned fallback.

For one coherent React decision, report the highest justified `Green —
routine`, `Yellow — caution`, `Orange — warning`, or `Red — crisis / stop`
response. React judgment never silently selects JSX, TypeScript, JavaScript,
Vitest, a host, or a process skill, and a rendered component is not proof of
host, accessibility, integration, or product completion.

## Do not use

Do not use this profile for:

- JSX grammar, attributes, fragments, spread syntax, escaping, or transform
  configuration; route to `jsx-language-profile`;
- JavaScript evaluation or TypeScript prop, generic, and intrinsic-element
  checking; route to `javascript-language-profile` or
  `typescript-language-profile`;
- Vitest configuration, mocks, fake timers, environment, isolation, snapshots,
  or runner mechanics; route to `vitest-test-profile`;
- deciding what to test, whether evidence is sufficient, or how implementation
  proceeds; route to `implementing-with-test-discipline`;
- routing, data loading, server components as metaframework behavior, bundling,
  build tools, styling, accessibility, browser APIs, or deployment;
- Astro projects and island directives or the MDX document/component seam;
  route to `astro-profile` or `mdx-profile`; or
- dependency adoption, generic frontend architecture, product behavior, or
  performance acceptance.

The word “React” in a framework feature does not transfer ownership. A routed
question remains open until its independently selected owner resolves it.

## Procedure

1. Establish task authority, the exact React package and version, renderer and
   host role, component region and owner, relevant props/state/context, render
   tree position and keys, Hook calls, Effect dependencies, test boundary,
   invocation or observation evidence, and project policy. Package presence
   does not prove a component rendered.
2. Classify the question as composition/props, render purity, state/update,
   Effect synchronization, Hook ordering, context, memoization, error boundary,
   component-test interaction, or a non-React route. Select this profile only
   for the React-owned decision.
3. Treat each render as using its own props, state, context, and closures.
   Separate render calculation from commit and external effects. A state setter
   requests later work; it does not mutate the current render's snapshot.
4. Bind state identity to component type, tree position, and keys. Distinguish
   preserving state from intentionally resetting it, and keep JSX syntax-level
   `key` questions with `jsx-language-profile`.
5. Keep rendering pure and idempotent for the same inputs. Place external
   synchronization in an Effect only when an external system exists; inspect
   setup, dependency identity, cleanup, development replay, and stale-closure
   risks without assigning browser or Node behavior to React.
6. Apply the Rules of Hooks under the exact React line. Ordinary Hooks stay at
   the top level of React functions and in stable order; bind any documented
   special case, such as `use`, to its exact version and conditions rather than
   generalizing it to every Hook.
7. For context and memoization, distinguish subscription-driven re-renders,
   prop comparison, local state, and optimization from correctness. `memo`,
   `useMemo`, and `useCallback` are performance tools, not semantic guarantees.
8. For error boundaries, establish which descendant render/lifecycle failures
   the selected boundary can observe and which event, asynchronous, server, or
   boundary-self failures belong elsewhere. Do not replace framework or host
   error handling with a component claim.
9. For component testing, state the React behavior and observable contract.
   Leave runner mechanics to `vitest-test-profile`, sufficiency to
   `implementing-with-test-discipline`, and DOM/accessibility truth to their
   owners. A mocked or emulated host remains mocked or emulated.
10. Route simultaneous decisions in the fixed document → framework → component
    library → syntax → language → runtime → test runner order, without invoking
    or reproducing another owner's procedure.

### Response model

| Level | React condition | Required response |
| --- | --- | --- |
| Green — routine | exact version and renderer, host-independent component question, clear tree/state/effect evidence | make the bounded judgment and run focused component evidence |
| Yellow — caution | dependency identity, context fan-out, memoization, development replay, or version-sensitive Hook behavior matters | inspect exact inputs, version, render sequence, and adverse case |
| Orange — warning | state identity is ambiguous, Effects entangle external systems, custom comparison risks stale behavior, or error ownership crosses boundaries | require a bounded design, adverse cases, cleanup, and rollback |
| Red — crisis / stop | Hook order can vary, render performs unsafe effects, stale or racing work is claimed correct, boundary evidence is missing, or host/framework success is inferred | stop until ownership and truthfulness are restored |

### Source and maintenance boundary

This profile is independently written from official React documentation and
the React repository tag `v19.2.6`, released 2026-05-06, inspected on
2026-08-20. The source covers component purity, state snapshots and tree
identity, Effects, Hook rules, context, memoization, and class error boundaries.
React documentation prose is CC-BY-4.0, and React repository source is
MIT-licensed. APG copies no upstream prose, code, examples, tables, or
diagnostics; API and rule names are used as factual identifiers.

React documentation is mutable, and canary or framework-integrated features do
not become stable host-independent component semantics merely because they
appear on the site. Refresh before a behavior-bearing correction, maturity
review, or publication when the selected React line, render semantics, Effect
guidance, Hook rules, context propagation, compiler/memoization relationship,
or error-boundary behavior changes.

Removal is candidate-independent: remove the canonical leaf, catalog row,
projection, capability route, packaged metadata row, current-development
inventory entries, focused tests, and boundary fixture rows; repair surviving
routes to the retained owner or project fallback; preserve ADR, evaluation,
exit, and provenance history.

## Project-owned parameters

The project owns whether React is selected; exact React, renderer, host, and
compiler versions; component boundaries and prop contracts; state placement;
context design; Effect policy; allowed Hooks; memoization and performance
acceptance; error reporting; test renderer and environment; runner and mock
policy; router and metaframework; server/data boundaries; styling;
accessibility; browser and runtime support; protected data; dependencies;
accepted exceptions; validation; rollback; publication; and deployment.
Stricter repository policy controls.

## Evidence and completion

Report the exact React and renderer versions, host role, component and render
boundary, relevant props/state/context and tree identity, Hook and Effect
evidence, response level, component-test observation, each adjacent route,
focused checks, limitations, and rollback. Separate static source review,
renderer observation, mocked or emulated evidence, and real host evidence.

Completion means only that the bounded React component decision is supported.
It does not mean JSX parsed, TypeScript checked, JavaScript semantics were
proven, Vitest was configured correctly, the browser or Node host worked,
accessibility passed, a framework route loaded, or the product requirement was
met. Keep unresolved routed obligations open.

## Stop or escalate

Stop when the React or renderer role and version, host boundary, component
owner, tree identity, relevant props/state/context, Hook order, Effect inputs,
or observation evidence is missing for a dependent claim; rendering performs
unbounded side effects; a Hook is conditionally reordered without an exact
documented exception; cleanup can leak or race; memoization is required for
correctness; an error boundary is credited with failures outside its scope; a
mocked component test is called host integration; or Astro, MDX, routing,
styling, accessibility, build, server/data, or deployment behavior is absorbed
under React authority.

## Common mistakes

- Treating React as the owner of JSX grammar or TypeScript prop checking.
- Reading state immediately after a setter as the next render's value.
- Moving event-driven logic into an Effect without an external synchronization
  need, or omitting required cleanup.
- Calling ordinary Hooks conditionally or after an early return.
- Treating `memo`, `useMemo`, or `useCallback` as correctness guarantees.
- Expecting context updates to be blocked by component memoization.
- Assuming an error boundary catches every event, asynchronous, server, or
  self-originating failure.
- Letting runner mocks or timers decide component semantics.
- Absorbing Astro, MDX, routing, styling, accessibility, or metaframework work.
- Calling one render or emulated test complete host or product evidence.
