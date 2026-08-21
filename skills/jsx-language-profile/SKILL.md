---
name: jsx-language-profile
description: Use when JSX-specific judgment is material to element, attribute, child, expression, fragment, spread, file-kind, or transform semantics; not for React behavior, TypeScript checking, JavaScript evaluation, runtime hosts, MDX, Astro, or build tools.
---

# JSX Language Profile

Lifecycle: `provisionally-integrated`.
Lifecycle ADR: `Accepted with amendment`.

## Core principle

Apply JSX judgment only when a current decision materially depends on JSX as a
library-independent syntax or transform surface. Own element, attribute, and
child grammar; expression containers; fragments; spread; syntax-facing `key`
handling; escaping and text handling; `.jsx` versus `.tsx` parsing
consequences; and the `jsx`, `jsxImportSource`, classic-runtime, and
automatic-runtime transform axes.

Use the boundary test literally: a question answerable without naming a
component library is a JSX candidate. If the answer changes because React or
another library consumes the result, route that decision to the library owner.
JSX has syntax but no library-independent component or runtime semantics.

For one coherent decision, report the highest justified `Green — routine`,
`Yellow — caution`, `Orange — warning`, or `Red — crisis / stop` response.
Selection never implies that another owner ran, and a transform result never
proves type checking, JavaScript evaluation, host execution, build completion,
or user-visible behavior.

## Do not use

Do not use this profile for:

- React components, hooks, rendering, reconciliation, state, effects, context,
  or library-facing `key` behavior; route to `react-component-profile`;
- TypeScript checking of `.tsx`, generic component typing, prop typing, or
  intrinsic-element declarations; route to `typescript-language-profile`;
- JavaScript evaluation, coercion, scope, modules, promises, or runtime values;
  route to `javascript-language-profile`;
- Node package mapping, loaders, process state, filesystem, timers, or other
  host behavior; route to `nodejs-runtime-profile`;
- bundler, dev-server, minifier, compiler-package, or transpiler selection and
  build orchestration;
- the MDX document/component seam or Astro component, island, routing, and
  project semantics; route to `mdx-profile` or `astro-profile`;
- generic planning, debugging, review, or test discipline; or
- styling, accessibility, browser behavior, product design, deployment, or
  dependency adoption.

A routed owner remains independently selected. This profile does not invoke or
reproduce that owner's guidance.

## Procedure

1. Establish the exact source region, file kind, whole-file owner, parser or
   transform role, selected tool and version, complete consequence-bearing
   options, invocation evidence, and project authority. A suffix, dependency,
   or configuration entry alone does not prove the role ran.
2. Classify the question as syntax/grammar, transform configuration,
   library-consumer behavior, type checking, language evaluation, host runtime,
   document/framework behavior, build tooling, or project policy. Select this
   profile only for the first two classes.
3. For syntax, inspect the exact element names, attributes, spread placement,
   children, expression-container boundaries, fragments, text, entities, and
   source goal. Keep the embedded JavaScript expression's internal semantics
   with `javascript-language-profile`.
4. For transformation, bind the selected `jsx` mode and every applicable
   factory, fragment, or `jsxImportSource` value. Distinguish preserved syntax,
   classic factory calls, automatic production runtime, and automatic
   development runtime. A mode label without its value and invocation is not
   transform evidence.
5. For `.tsx`, keep parsing/file-kind consequences separate from TypeScript's
   JSX namespace, intrinsic-element, prop, generic, and assignability checks.
   Static success does not prove emitted or runtime behavior.
6. Treat syntax-facing spread and `key` facts narrowly. Property evaluation
   belongs to JavaScript; the meaning React gives `key` belongs to React.
7. Route each simultaneous non-JSX decision explicitly to its narrowest owner,
   preserving the document → framework → component library → syntax → language
   → runtime → test runner order without silently invoking any route.
8. Verify with the exact selected parser or transform where relevant, record
   what that observation proves, and stop before widening it into a universal
   syntax, type, runtime, build, or component claim.

### Response model

| Level | JSX condition | Required response |
| --- | --- | --- |
| Green — routine | exact region, file kind, selected parser/transform, complete options, library-independent question | make the bounded syntax or transform judgment and run focused checks |
| Yellow — caution | version-sensitive grammar, ambiguous text/escaping, spread or key boundary, or multiple transform modes | inspect exact source, version, options, and output |
| Orange — warning | generated input, mixed host grammar, custom factory/runtime, transform disagreement, or unclear whole-file owner | require an accepted bounded interpretation, adverse cases, and rollback |
| Red — crisis / stop | source region, parser/transform role, file kind, required option, or receiving owner is unresolved and a dependent conclusion would be asserted | stop the dependent conclusion and name the missing evidence |

### Source and maintenance boundary

This profile is independently written from the draft JSX grammar in the
`react/jsx` repository, inspected at its 2026-08-20 `main` state, and the
official TypeScript JSX and TSConfig documentation inspected on the same date.
The JSX specification and TypeScript documentation prose are CC-BY-4.0;
TypeScript website code is MIT-licensed, and TypeScript compiler source is
Apache-2.0. APG copies no source prose, grammar, code, examples, or tables.
Names such as `jsxImportSource`, `react-jsx`, and `react-jsxdev` are factual
interface identifiers.

The draft JSX source is mutable and defines syntax rather than runtime
semantics. TypeScript documentation describes one implementation and cannot
establish every transformer's behavior. Refresh before a behavior-bearing
correction, maturity review, or publication when the JSX grammar, selected
transform line, TypeScript JSX modes, import-source rules, or file-kind
handling changes.

Removal is candidate-independent: remove the canonical leaf, catalog row,
projection, capability route, packaged metadata row, current-development
inventory entries, focused tests, and boundary fixture rows; repair surviving
routes to the retained owner or project fallback; preserve ADR, evaluation,
exit, and provenance history.

## Project-owned parameters

The project owns the parser and transform package, exact versions and
invocations, file extensions and source ownership, `jsx` mode,
`jsxImportSource`, factories and fragment factories, import/export and module
policy, TypeScript project and checking options, component library and runtime,
bundler and build pipeline, generated-artifact policy, formatting, security,
accessibility, performance, test strategy, accepted exceptions, deployment,
publication, and rollback. Stricter repository policy controls.

## Evidence and completion

Report the exact source region, whole-file owner, file kind, selected parser or
transform role and version, option values, invocation, syntax or transform
claim, response level, every adjacent route, focused checks, limitations, and
rollback. Separate normative source facts from one tool's observation.

Completion means only that the bounded JSX syntax or transform decision is
supported. It does not mean that TypeScript checked, JavaScript evaluated, a
host loaded, React rendered, tests sufficed, a bundle built, or an application
worked. Keep every unresolved routed obligation open.

## Stop or escalate

Stop when the source region, whole-file owner, file kind, parser/transform role,
exact version, invocation, or consequence-bearing option is missing for the
claim; syntax and consumer semantics are being collapsed; `.tsx` parsing is
offered as type-checking proof; a transform output is offered as runtime or
build completion; an embedded JavaScript result is guessed; an MDX or Astro
question is absorbed because its future owner is absent; or a requested change
would select a dependency, rewrite project policy, or exceed task authority.

## Common mistakes

- Treating JSX as React or giving JSX library-independent runtime semantics.
- Answering TypeScript intrinsic-element or prop typing under syntax authority.
- Inferring a transform from a file suffix or configuration key without the
  selected role and invocation.
- Treating automatic and classic runtimes as interchangeable.
- Assigning JavaScript expression evaluation or Node loading to JSX.
- Treating syntax-facing `key` handling as React reconciliation guidance.
- Absorbing MDX, Astro, build-tool, styling, or accessibility concerns.
- Calling a successful parse or emit complete application behavior.
