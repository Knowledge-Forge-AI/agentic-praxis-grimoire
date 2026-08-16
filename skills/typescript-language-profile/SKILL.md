---
name: typescript-language-profile
description: Use when a material decision depends on TypeScript-specific static semantics or type-erasure boundaries for an established source region, after the exact compiler role, version, options, project, source kind, and declaration environment are evidenced.
---

# TypeScript Language Profile

Lifecycle: `provisionally-integrated`.
Lifecycle ADR: `Accepted with amendment`.

Normative detail:
[TypeScript Language Profile](../../docs/specs/typescript-language-profile.md).
Status: Provisionally integrated under ADR 0043 after APG75 iterative
hardening and APG75A scope correction. The profile consumes, but does not
select, the project's exact compiler generation.

## Core principle

<!-- APG-CLAUSE: TS-TRIGGER -->
Apply TypeScript-specific judgment only when a current, consequence-bearing
decision materially depends on TypeScript source syntax, static semantics, or
the type-erasure boundary of an established source region — and only after
the exact compiler role, compiler package and version, consequence-bearing
option values, project configuration, source kind, and declaration
environment are established from evidence. Use the highest justified
`proceed-routine`, `inspect-before-judgment`, `bounded-local-decision`, or
`stop-and-escalate` response for the one coherent current decision, exactly
as the accepted language-profile contract defines those levels.

Keep three axes separate for every decision: selection (`selected`,
`embedded-route`, `route-to-owner`, or `non-trigger`), response (the warning
severity), and a small ordered set of routes or obligations, one per
simultaneous non-TypeScript decision. Selection is decision-scoped and never
transfers whole-file ownership: `.tsx` and checked JavaScript use
`embedded-route` for bounded TypeScript analysis while their JSX/TSX and
JavaScript owners remain controlling. Routing never lowers severity.
The exact project-selected compiler role and version control the current
TypeScript conclusion. TypeScript 5.x, 6.x, 7.x, or another exact supported
line may be valid project input. This profile does not choose a destination
generation and does not label an older compiler a migration baseline unless a
separate exact project decision establishes that destination. Compiler
migration routes to project-design and compiler-configuration owners.

## Do not use

<!-- APG-CLAUSE: TS-NONTRIGGER -->
Do not use this profile for:

- JavaScript source-language semantics outside TypeScript-specific analysis,
  emitted-JavaScript behavior, runtime exceptions, or runtime validation;
- selecting the compiler package, role, version, tsconfig values, project
  references, file inclusion, module-resolution policy, or emit policy —
  those are consumed facts owned by project and compiler-configuration
  owners;
- JSX syntax or transform decisions, whole-file `.astro`/`.mdx`/Vue/Svelte
  host work, or extraction of embedded regions from a host;
- Node.js, browser, or platform API behavior — declarations describe them;
  this profile never decides them;
- type stripping, transpilation, bundling, build orchestration, or runtime
  module loading;
- structural decomposition policy, file-size judgment, or
  JavaScript-to-TypeScript migration decisions; or
- installing, upgrading, or configuring any tool.

A non-trigger is a routine handoff with the receiving owner named exactly;
it is not a TypeScript decision.

## Required evidence intake

<!-- APG-CLAUSE: TS-EVIDENCE -->
Before any TypeScript-owned conclusion, bind from evidence — and keep
present evidence separate from evidence still required:

- the source and artifact kind (`.ts`, `.mts`, `.cts`, `.tsx`, `.d.ts`
  family, checked JavaScript, host-embedded region, generated artifact);
- the whole-file owner and this profile's selection state;
- every consequence-bearing compiler role independently (see the role
  matrix), each with exact package, exact version, selection source, and
  invocation evidence — package or lockfile presence never proves a role is
  exercised, and one role's evidence never satisfies another;
- exact values for every option that controls the result (for example
  `strict=true`, `exactOptionalPropertyTypes=true`,
  `noUncheckedIndexedAccess=true`, `module="nodenext"`,
  `verbatimModuleSyntax=true`, `jsx="preserve"`, `noEmit=true`) —
  an option name without a value is not an option fact, and a default counts
  only with exact version evidence;
- the project graph, declaration environment, and lib/types surface.

## Compiler-role matrix

Treat each selected role as separately evidenced: `cli-checker`,
`declaration-emitter`, `programmatic-compiler-api`,
`editor-language-service`, `embedded-language-checker`,
`source-transformer-type-stripper`, `build-orchestrator`, `runtime-host`.
For each active role, record its product state (`intended`, `current`, or
`temporary`) separately from its invocation state (`invoked`, `not-invoked`,
or `unknown`), with a retirement condition whenever the product state is
`temporary`. `unknown` is an evidence state, never a role token. A role whose
identity is unresolved has no invented role, package, or version binding;
record the missing identity and required evidence instead. A role that is
`not-required` is absent from active role records, and any known package
candidate remains a separate availability fact. Bind every version-specific
conclusion to the exact project-selected compiler evidence. A second compiler
line or API is a separately bound compatibility role only where an exact role
independently requires it, with an owned retirement condition when temporary.

For target migration, an exercised embedded checker that excludes a separately
decided project destination creates a host/tool compatibility route. It does
not prove use of that destination or force a particular compatibility line:
the project owner may update the host tooling or select one exact temporary
compatibility role with retirement. A stale lock routes to the package owner,
configured declaration emit without invocation remains unknown, and static
evidence never proves build or runtime completion.

## Procedure

1. Classify the source and artifact kind, and identify the whole-file owner
   and selection state.
2. Complete the required evidence intake above; list what is present and
   what is still required.
3. Analyze only TypeScript-owned static semantics for the established
   region: assignability, narrowing and control flow, generics and
   inference, type operators, `any`/`unknown`/`never` distinctions,
   `satisfies` versus assertions, overload boundaries, strictness-option
   consequences, import/export and emit-bearing syntax distinctions,
   declaration-file meaning, and bounded checked-JavaScript analysis —
   each under the exact evidenced version and option values.
4. Route every simultaneous adjacent decision as one item in a small ordered
   route or obligation set while keeping the TypeScript response unchanged:
   compiler and tsconfig
   selection to the project/compiler-configuration owner, JSX syntax and
   transform to the JSX owner, host files to the host owner, module loading
   and build to the build owner, runtime and platform behavior to the
   runtime owner, and policy to the policy owner.
5. Stop rather than infer when role, version, option, source kind, or
   declaration evidence is missing.
6. Distinguish static success from emitted or runtime completion in every
   report, and preserve declaration and generated-artifact provenance.

## Static/runtime refusal

A clean check under an exact compiler proves only static consistency of the
checked region. Types are erased at emit: never present a clean check,
a successful declaration-only emit, or a type assertion as evidence of
runtime behavior, of emitted-JavaScript correctness, or of pipeline
completion. Claims about runtime shape require runtime-owner evidence.

## Declaration provenance

Handwritten declarations assert unverified runtime surfaces; treat them as
authored claims. Generated declarations are regenerated from their source
under an evidenced `declaration-emitter` role — never hand-edited — and a
declaration whose provenance is unknown blocks direct edits and regeneration
claims until its provenance is established.

## Structural-policy deferral

TypeScript structural policy is deferred under ADR 0042: line count is
descriptive only, numeric bands are forbidden, automatic
JavaScript-to-TypeScript migration is forbidden, and whole-file
decomposition judgment belongs to the project-design owner. This profile may
identify that a question is structural; it must route rather than judge.

## Project-owned parameters

The repository and project own: the compiler package, role, and exact
version selection; tsconfig values, project references, and file inclusion;
the declaration environment and lib/types surface; host and embedded
tooling and its compiler support line; build, emit, and module-loading
policy; structural and migration policy; artifact classifications and
accepted exceptions; and any stricter repository policy, which always
controls.

## Stop or escalate

<!-- APG-CLAUSE: TS-UNKNOWN-STOP -->
Apply these responses exactly:

- missing exact compiler role: `stop-and-escalate`;
- missing consequence-bearing option value: `inspect-before-judgment`, or
  `stop-and-escalate` when a result would otherwise be asserted;
- unknown source kind: `inspect-before-judgment`;
- unknown declaration provenance: stop before any direct edit or
  regeneration claim;
- static success offered as runtime proof: `stop-and-escalate`;
- host or runtime behavior requested: selection `route-to-owner`, response
  `proceed-routine`;
- ordinary established TypeScript static question: `proceed-routine`.

A routed stop remains stopped until the receiving owner resolves it.

## Evidence and completion

Before a material repair, record the pre-change state rollback needs: the
exact prior source region, the prior declaration bytes and their provenance,
and the configuration evidence the conclusion rested on. Report the
selection state, response, evidence bindings (roles, versions, option
values), each exact route, and the rollback boundary. Never claim completion
while required evidence is missing, while a routed stop is unresolved, or in
terms that conflate static success with runtime success.

## Common mistakes

- Treating package or lockfile presence as proof that a compiler role runs.
- Using one role's evidence (for example an editor check) to satisfy
  another (for example CLI or emit).
- Asserting an option-dependent result from an option name without its
  exact value.
- Collapsing `.mts` and `.cts` into one source kind, or treating `.tsx` as
  ordinary whole-file TypeScript.
- Treating an exact current compiler as a migration baseline or selecting a
  destination without a separate project-owned decision.
- Hand-editing a generated declaration, or editing a declaration with
  unknown provenance.
- Presenting a clean static check as runtime or pipeline success.
- Making structural or migration judgments under TypeScript authority.
