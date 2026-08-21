---
name: mdx-profile
description: Use when an MDX decision depends on the Markdown-to-JSX/component seam, imports/exports, expressions, provider mapping, or compile/runtime split; not for pure Markdown, JSX, React, TypeScript, JavaScript, or Astro.
---

# MDX Profile

Lifecycle: `provisionally-integrated`.
Lifecycle ADR: `Accepted with amendment`.

## Core principle

Apply MDX-specific judgment only when a consequence-bearing decision depends on
the document-to-component seam: where Markdown ends and evaluated JSX begins,
how MDX ESM or expressions participate, how components are supplied or mapped,
or which fact belongs to compilation versus later evaluation and rendering.
Use the highest justified `Green — routine`, `Yellow — caution`, `Orange —
warning`, or `Red — crisis / stop` response for the one current decision.

Keep selection, response, and route separate. The fixed composition order is
document, framework, component library, syntax, language, runtime, test runner,
then mock library. MDX is the document owner for its seam; it names adjacent
owners without invoking them or reproducing their guidance.

## Do not use

Do not use this profile for:

- pure Markdown headings, lists, links, references, or dialect behavior, owned
  by `markdown-language-profile`;
- library-independent JSX grammar or transform configuration, owned by
  `jsx-language-profile`;
- React component, Hook, state, Effect, or render behavior, owned by
  `react-component-profile`;
- TypeScript checking of `.tsx` or imported typed components, owned by
  `typescript-language-profile`;
- general JavaScript evaluation semantics, owned by
  `javascript-language-profile`;
- Astro collection, route, island, directive, project, or integration behavior,
  owned by `astro-profile`;
- a site's broader content pipeline, framework configuration, deployment, or
  publication; or
- generic planning, debugging, review, and test-discipline procedure.

A non-trigger is an exact handoff, not a Green MDX decision. If removing every
JSX element, component expression, import, export, and provider concern leaves
the question intact, route the surviving decision to Markdown or its other
actual owner.

## Procedure

1. Establish task authority, repository policy, the selected MDX implementation
   and version, integration or compiler, JSX runtime/provider, host framework,
   validation boundary, protected-data boundary, and rollback.
2. State the exact consequence-bearing question and decide whether it turns on
   the MDX document/component seam. If not, record the one receiving owner and
   stop MDX selection for that decision.
3. Classify the artifact as maintained source, generated output, legacy content,
   embedded fragment, or external input. Inspect the owner or generator rather
   than hand-editing generated output.
4. Separate four layers: Markdown token and block behavior; MDX parsing and
   compilation; emitted module and component mapping; later host evaluation and
   rendering. Do not use success at one layer as proof of another.
5. Inspect only the relevant MDX surface: ESM imports and exports, expressions,
   JSX/component boundaries, interleaving, component provider or mapping flow,
   compile options, generated module shape, and the host handoff.
6. Route simultaneous decisions without answering them: pure Markdown to
   `markdown-language-profile`; JSX syntax/transform to
   `jsx-language-profile`; component behavior to `react-component-profile`;
   typing to `typescript-language-profile`; general evaluation to
   `javascript-language-profile`; and Astro placement to `astro-profile`.
7. Assign the response. Green uses ordinary local evidence; Yellow requires the
   named compiler/provider/host facts; Orange requires a bounded design,
   adverse cases, and rollback; Red stops on an unresolved grammar crossing,
   unsafe evaluation, ambiguous authority, or false completion claim.
8. Report selection, response, exact source and host versions, seam evidence,
   routes, limitations, checks, and rollback. Keep routed stops open.

### Ownership and semantic-risk checks

This profile owns MDX-specific composition and failure modes: a Markdown region
being reinterpreted because it crosses into JSX, an MDX expression or ESM region
changing compilation, a component name resolving through local definition,
import, or mapping, and a compile-time output being confused with runtime host
behavior. It does not own the embedded language or component after the handoff.

Inspect for unsupported MDX syntax under the selected compiler; a pure Markdown
claim made from MDX behavior; invalid or ambiguous interleaving; expression or
ESM evaluation without an authorized trust boundary; missing component mapping;
provider assumptions that change by host; compile options inconsistent with the
selected JSX runtime; stale generated output; errors attributed to the wrong
layer; and mocked compilation or rendering represented as integrated evidence.

### Response guide

| Level | MDX signal | Required response |
| --- | --- | --- |
| Green — routine | selected version and host are known, the seam is local, and focused evidence observes the claimed layer | proceed with project checks and exact routes |
| Yellow — caution | compiler options, provider mapping, generated shape, or host handoff needs local confirmation | inspect the named configuration or output before deciding |
| Orange — warning | custom evaluation, cross-host mapping, generated-source ownership, or a multi-layer repair is material | record a bounded design, adverse cases, validation, and rollback |
| Red — crisis / stop | untrusted evaluation, unresolved grammar ownership, missing source authority, or compile/render success is falsely inferred | stop until the owner and evidence boundary are restored |

### Source and maintenance boundary

This profile is independently written from MDX 3.1.1 at exact repository object
`50aa8df0b027c893dec9f97a2b7c51539e9f1a4b`, released 2025-08-29, plus the
official MDX format, use, and extension documentation on the same repository's
main line at `685627a819567c0788eadb85f5f57065bcc81c2c`. The sources were inspected
on 2026-08-20 and are MIT-licensed. They cover Markdown/JSX interleaving, ESM,
expressions, compilation, component mapping, providers, and extension seams.
APG copies no upstream prose, code, examples, tables, or diagnostics.

Documentation and integrations are mutable. Refresh before a behavior-bearing
correction, maturity review, or publication when the selected MDX release,
syntax, compilation output contract, provider model, supported JSX runtimes,
plugin pipeline, or security guidance materially changes.

Removal is candidate-independent: remove the canonical leaf, catalog row,
projection, capability route, packaged metadata row, current-development
inventory entries, focused tests, and boundary fixture rows; repair surviving
routes to the retained owner or project fallback; preserve ADR, evaluation,
exit, and provenance history.

## Project-owned parameters

The project owns whether MDX is selected; the exact compiler, integration,
plugins, format and JSX-runtime options; enabled Markdown dialect; component
mapping and provider; host framework and content pipeline; module trust and
evaluation policy; generated-output ownership; TypeScript and JavaScript
policy; component library; test boundary; protected data; dependencies;
accepted exceptions; validation; rollback; publication; and deployment.
Stricter repository policy controls.

## Evidence and completion

Report the selected MDX version, compiler/integration and options, artifact
class, seam decision, compilation evidence, component mapping/provider and host
facts, response, each adjacent route, focused checks, limitations, and rollback.
Separate source inspection, compilation, emitted-module inspection, evaluation,
component rendering, mocked evidence, and real host evidence.

Completion supports only the bounded MDX seam decision. It does not prove the
Markdown dialect, JSX transform, React behavior, TypeScript checking,
JavaScript correctness, Astro content route, browser or Node host, build,
accessibility, deployment, or product requirement. Keep unresolved routes open.

## Stop or escalate

Stop when the selected compiler, format, JSX runtime, provider or host is
unknown for a dependent claim; the Markdown/JSX boundary is ambiguous;
untrusted content can reach evaluation; generated output is edited without its
owner; provider behavior is assumed across hosts; a compile-only observation is
called runtime or render evidence; a mock is called host integration; or pure
Markdown, JSX, React, TypeScript, JavaScript, or Astro behavior is absorbed
under MDX authority.

## Common mistakes

- Treating every `.mdx` question as MDX-owned instead of routing pure Markdown.
- Treating MDX syntax as ordinary JSX or HTML.
- Treating expression compilation as proof of safe evaluation.
- Assuming one provider or host mapping applies universally.
- Calling emitted JavaScript a rendered component.
- Answering embedded React, TypeScript, or JavaScript semantics from MDX facts.
- Absorbing Astro content collections, routing, or client directives.
- Calling a mocked compiler or renderer complete host evidence.
