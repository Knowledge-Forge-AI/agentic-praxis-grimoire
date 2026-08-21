# ADR 0049: JSX and React Profiles with APG88 Headroom Conservation

## Status

Accepted with amendment

## Decision date

2026-08-20

## Context

ADR 0047 freezes `jsx-language-profile` and `react-component-profile` as the
second v0.6 implementation pair. JSX owns library-independent syntax and
transform configuration; React owns host-independent component and render
semantics. APG86 leaves 991 bytes beneath the 9,527-byte aggregate ceiling.
The formal APG87 contract permits this pair to consume 340 through 651 bytes,
but using the full allowance would leave APG88's MDX and Astro descriptions at
their exact 170-byte floors with no slack.

Dispatcher-owned post-planning review identified that readiness risk. The
accepted APG85 derivation uses a 260-byte body mean, so APG87 treats 651 as a
hard ceiling rather than a target and conserves practical APG88 headroom.

## Decision

1. Provisionally integrate `jsx-language-profile` as the owner of
   library-independent JSX element, attribute, child, expression-container,
   fragment, spread, escaping, file-kind, and transform-runtime questions.
2. Keep React component behavior, TypeScript `.tsx` checking, JavaScript
   evaluation, Node host behavior, build tools, and future MDX/Astro concerns
   with their exact existing, reserved, or project-owned receivers.
3. Provisionally integrate `react-component-profile` as the owner of
   host-independent component composition, props, render and re-render, state,
   Effects, Hook rules, context, memoization, error boundaries, and the
   component-design side of component testing.
4. Keep JSX syntax, JavaScript and TypeScript semantics, Vitest mechanics,
   generic test sufficiency, routing, styling, accessibility, MDX, Astro,
   server/data frameworks, build tooling, and deployment outside React.
5. Preserve the APG85 composition order and independent selection rule. No
   profile silently invokes or reproduces another owner.
6. Use 248 UTF-8 description bytes for JSX and 268 for React: 516 combined,
   9,052 total, a 1,085-byte full-v0.6 delta from 7,967, and 475 bytes remaining
   under 9,527 for APG88.
7. Keep `libexec/apg_skill_library_check.py` unchanged. Diagnostics APG039 and
   APG040 remain topology-agnostic and own only the frozen six-name band,
   aggregate ceiling, discoverability agreement, and malformed fail-closed
   behavior.
8. Integrate canonical leaves, catalog rows, exact relative projections,
   capability routes, generated metadata, current-development project and
   release inventories, boundary fixtures, focused tests, and phase records as
   one local phase. Existing explicit project subsets remain unchanged.
9. Do not implement MDX or Astro, begin APG88, add advisory discovery, change a
   dependency, lockfile, package version, publication or deployment surface, or
   push remotely.

## Alternatives considered

- Consume the full 651-byte phase ceiling: rejected because it would reserve
  only the exact two-profile floor for APG88 despite the adjacent-owner
  non-trigger pressure recorded by ADR 0047.
- Require exactly 520 bytes: rejected because 260 bytes per profile is a budget
  derivation, not an individual wording mandate; the independently written
  248/268 descriptions satisfy discovery needs while conserving four more
  bytes.
- Merge JSX and React: rejected because ADR 0047 fixes separate syntax and
  component-library owners and treats contradiction as a contract defect.
- Add MDX or Astro now: rejected as APG88 scope and an explicit task boundary.

## Consequences

Development becomes 37 canonical skills, 37 catalog rows, 37 exact relative
projections, and 37 discoverable metadata rows, with 14 stable and 23
provisional skills and zero malformed metadata. The two profiles are directly
selectable siblings. An MDX or Astro route remains a reserved, unresolved
obligation until its separately authorized owner exists.

The current v0.6 total is 9,052 bytes, leaving 475 bytes for the final two
profiles. That is 135 bytes more than APG88's absolute two-profile floor and
does not amend any generic budget constant. Public and active v0.5.0 remain
unchanged. APG88, readiness, publication, deployment, advisory discovery, and
remote push remain outside this decision.
