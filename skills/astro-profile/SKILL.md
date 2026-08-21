---
name: astro-profile
description: Use when Astro behavior hinges on .astro execution, islands/client directives, server/client boundaries, collections, routing, or integrations; not for React, JSX, MDX, TypeScript, Node, Vite, Starlight, CSS, accessibility, or deployment.
---

# Astro Profile

Lifecycle: `provisionally-integrated`.
Lifecycle ADR: `Accepted with amendment`.

## Core principle

Apply Astro-specific judgment only when a consequence-bearing decision depends
on `.astro` component structure, the frontmatter/template execution split,
islands and client directives, the server-versus-client boundary, content
collections, file-based routing, project conventions, or Astro integration
configuration. Use the highest justified `Green — routine`, `Yellow — caution`,
`Orange — warning`, or `Red — crisis / stop` response for the current decision.

Keep selection, response, and route separate. In the fixed composition order,
MDX owns the document seam, Astro owns the framework layer, React owns component
behavior, JSX owns syntax, language profiles own their languages, and Node owns
host/runtime behavior outside Astro's framework boundary. No owner is invoked
implicitly or reproduced here.

## Do not use

Do not use this profile for:

- React component, Hook, state, Effect, or render semantics inside an island,
  owned by `react-component-profile`;
- library-independent JSX grammar or transform behavior, owned by
  `jsx-language-profile`;
- the MDX document/component seam, owned by `mdx-profile`;
- TypeScript checking, owned by `typescript-language-profile`;
- generic Node host, package, process, or runtime semantics outside the
  Astro-owned execution boundary, owned by `nodejs-runtime-profile`;
- Vite internals, Starlight, styling or CSS strategy, accessibility acceptance,
  hosting, or deployment;
- generic web-framework or package-manager advice; or
- generic planning, debugging, review, and test-discipline procedure.

A non-trigger is an exact handoff, not a Green Astro decision. Astro answers
where code runs, when an island hydrates, and how Astro project, content, route,
and integration structure works. It does not answer what an embedded component
or language does after that framework handoff.

## Procedure

1. Establish task authority, repository policy, exact Astro version and output
   mode, adapter and integrations, route and content configuration, selected UI
   frameworks, validation boundary, protected-data boundary, and rollback.
2. State the exact consequence-bearing question. Select Astro only when the
   answer depends on an Astro framework, project, content, route, island, or
   execution contract; otherwise name the one receiving owner.
3. Classify the artifact as `.astro` component, page, layout, endpoint, content
   entry, content configuration, integration configuration, generated output,
   legacy artifact, or external input. Preserve its actual owner.
4. Separate frontmatter execution, template rendering, server output, client
   directive scheduling, hydrated component execution, and later browser or
   host behavior. Evidence from one layer does not prove the next.
5. Inspect only the relevant Astro surface: frontmatter/template placement,
   component props and slots at the Astro boundary, islands and directives,
   server/client placement, collection definition and schema, route generation,
   project conventions, rendering mode, adapter boundary, and integration
   configuration.
6. Route simultaneous decisions without answering them: React behavior to
   `react-component-profile`; JSX syntax to `jsx-language-profile`; MDX seams to
   `mdx-profile`; typing to `typescript-language-profile`; and generic host
   behavior to `nodejs-runtime-profile`. Route Vite, Starlight, styling,
   accessibility, hosting, and deployment to project-selected owners.
7. Assign the response. Green uses ordinary local framework evidence; Yellow
   requires the named config, route, directive, or execution facts; Orange
   requires a bounded framework design, adverse cases, and rollback; Red stops
   on unsafe placement, unresolved owner or version, or false host evidence.
8. Report selection, response, versions and mode, framework evidence, routes,
   limitations, checks, and rollback. Keep routed stops open.

### Ownership and semantic-risk checks

This profile owns Astro-specific placement and lifecycle questions: what runs
in component frontmatter versus the rendered template, which code is omitted
from the client, which directive schedules an island, how a content collection
and schema participate, how files become routes, and what an Astro integration
changes at the framework level. It does not own an integration's independent
library semantics or Vite internals.

Inspect for server-only values crossing into client output; absent or mismatched
client directives; hydration credited before the directive condition occurs;
route collisions or unexpected dynamic generation; content schema and source
identity mismatch; integration order or mode assumptions; adapter-dependent
behavior represented as portable; generated `.astro` state edited by hand;
React or JSX behavior attributed to Astro; Node behavior inferred outside the
framework boundary; and build success represented as deployment acceptance.

### Response guide

| Level | Astro signal | Required response |
| --- | --- | --- |
| Green — routine | selected version, mode, route, content, and island boundary are known and focused evidence observes the claimed layer | proceed with project checks and exact routes |
| Yellow — caution | directive timing, route generation, collection schema, integration order, adapter, or output placement needs local confirmation | inspect the named configuration or output before deciding |
| Orange — warning | custom integration, cross-mode behavior, adapter coupling, route migration, or server/client redesign is material | record a bounded design, adverse cases, validation, and rollback |
| Red — crisis / stop | protected server data can reach the client, owner/version is unresolved, hydration or host evidence is false, or deployment is inferred | stop until authority and the execution boundary are restored |

### Source and maintenance boundary

This profile is independently written from Astro 7.1.6 at annotated tag
`adbb7cbd12c47a869ad5008688209152e2362849` and exact commit
`9865d1c03af6d1a1f15c9811858778cc952ca4e4`, released 2026-07-29, plus the
official Astro component, islands, content-collection, and routing documentation
at exact docs commit `ad92aec16358fee8e85f0dcd3b1e6baa9fd039c8`. The sources were
inspected on 2026-08-20 and are MIT-licensed. They cover `.astro` structure,
server and client execution, directives, collections, routes, and integration
seams. APG copies no upstream prose, code, examples, tables, or diagnostics.

Astro framework and documentation behavior is mutable. Refresh before a
behavior-bearing correction, maturity review, or publication when the selected
Astro line, component compilation, rendering mode, directives, content APIs,
routing, adapter boundary, integration hooks, or security guidance changes.

Removal is candidate-independent: remove the canonical leaf, catalog row,
projection, capability route, packaged metadata row, current-development
inventory entries, focused tests, and boundary fixture rows; repair surviving
routes to the retained owner or project fallback; preserve ADR, evaluation,
exit, and provenance history.

## Project-owned parameters

The project owns whether Astro is selected; the exact Astro, adapter,
integration, UI-framework, TypeScript, and Node versions; rendering and output
mode; routes, content sources and schemas; directives and hydration policy;
server/client data policy; integration order; Vite and Starlight selection;
styling; accessibility; test environment; protected data; dependencies;
accepted exceptions; validation; rollback; publication; hosting; and
deployment. Stricter repository policy controls.

## Evidence and completion

Report the exact Astro version, output and rendering mode, artifact class,
frontmatter/template and server/client boundary, relevant directive, collection,
route, adapter and integration facts, response, adjacent routes, focused checks,
limitations, and rollback. Separate source review, static configuration,
framework build, server output, client hydration, emulated evidence, and real
host or deployment evidence.

Completion supports only the bounded Astro framework decision. It does not
prove React behavior, JSX parsing, MDX seams, TypeScript checking, generic Node
runtime behavior, Vite internals, Starlight, styling, accessibility, hosting,
deployment, or product acceptance. Keep unresolved routed obligations open.

## Stop or escalate

Stop when the Astro version, output mode, adapter, integration, content source,
route owner, directive, or server/client boundary is missing for a dependent
claim; protected server data can enter client output; an island is credited
with hydration absent its directive condition; generated output is edited
without its owner; framework build evidence is called deployment evidence; a
mock is called real host evidence; or React, JSX, MDX, TypeScript, Node, Vite,
Starlight, styling, accessibility, hosting, or deployment is absorbed under
Astro authority.

## Common mistakes

- Treating all code in an `.astro` file as client-side.
- Treating an island as hydrated without its selected client directive.
- Answering React component behavior from Astro placement facts.
- Answering JSX, MDX, TypeScript, or generic Node semantics under Astro.
- Treating an integration as ownership of its independent library internals.
- Assuming content schema, route, adapter, or output mode across projects.
- Treating a successful build as accessibility, hosting, or deployment proof.
- Calling emulated or mocked output real server/client evidence.
