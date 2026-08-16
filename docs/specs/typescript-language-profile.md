# TypeScript Language Profile

Lifecycle: `provisionally-integrated`.
Lifecycle ADR: `Accepted with amendment`.

## Status and authority

- Status: Provisionally integrated specification after APG75 iterative
  hardening and APG75A scope correction.
- Authority: accepted
  [ADR 0042](../adr/2026/08/0042-language-profile-production-recovery-and-iterative-hardening.md)
  governs the recovery lifecycle; Accepted with amendment
  [ADR 0043](../adr/2026/08/0043-typescript-language-profile-candidate-and-intended-state-harness.md)
  governs this retained profile. Rejected ADR 0041 and the APG71/APG72 architecture
  registers remain historical falsification evidence, not governing
  authority.
- Candidate leaf:
  [skills/typescript-language-profile/SKILL.md](../../skills/typescript-language-profile/SKILL.md).
- Navigation record:
  [scenario coverage](typescript-language-profile-scenario-coverage.md).
- Intended-state harness:
  [`src/test/fixtures/apg74-typescript-intended-state/`](../../src/test/fixtures/apg74-typescript-intended-state/README.md).

This specification is the provisionally integrated APG75 result. APG75
independently hardened the APG74 candidate through three separately preserved
rounds, closed all material findings, and accepted ADR 0043 with amendment.

## Scope

The profile owns one narrow problem: TypeScript-specific source syntax,
static semantics, and type-erasure boundaries for an established source
region, after the exact compiler role, compiler version, option values,
project configuration, source kind, and declaration environment are
established. It does not claim that every TypeScript feature is covered, and
it never substitutes for the compiler: the evidenced compiler's behavior at
its exact version controls wherever prose and compiler disagree.

## Trigger and selection

TypeScript judgment participates only when a current, consequence-bearing
decision materially depends on TypeScript-owned semantics. Selection takes
exactly one state per decision and is orthogonal to the recorded whole-file
owner:

- `selected` — the current decision concerns an established
  TypeScript-owned region under evidenced configuration;
- `embedded-route` — another owner keeps the whole file while TypeScript
  participates in a bounded static-analysis decision, including `.tsx`,
  checked JavaScript, or a host-supplied embedded region;
- `route-to-owner` — the decision belongs to an adjacent owner;
- `non-trigger` — TypeScript judgment does not participate; the handoff
  names the receiving owner exactly.

Responses use the accepted generic order `proceed-routine`,
`inspect-before-judgment`, `bounded-local-decision`, `stop-and-escalate`.
Routing never lowers severity, and a routed stop remains stopped until the
receiving owner resolves it. `selected` never implies whole-file ownership;
the separately recorded owner controls that fact. When one analysis exposes
several adjacent decisions, report a small ordered route or obligation set,
one item per consequence-bearing decision; never collapse JSX, host,
configuration, declaration-provenance, build, and runtime obligations into
one receiving owner.

## Owner

The owned areas include: TypeScript-only syntax; structural assignability;
narrowing and control-flow analysis; generic type relationships; type
operators; union and intersection static consequences; overloads and the
implementation-signature boundary; strictness and selected option
consequences; optional-property and indexed-access consequences; `any`,
`unknown`, and `never` static distinctions; `satisfies` and assertion
static consequences; type-only imports and emit-related static
distinctions; enum and const-enum static/emit boundaries; decorator static
interpretation under an exact regime; declaration-file static meaning; the
generated-declaration provenance boundary; bounded non-additive
checked-JavaScript analysis; TypeScript-specific module source-kind
consequences; and the declaration-only emit boundary.

## Compiler generations and project intent

<!-- APG-CLAUSE: TS-COMPILER-GENERATION -->
The exact project-selected compiler role and version control the current
TypeScript conclusion. TypeScript 5.x, 6.x, 7.x, or another exact supported
line may be valid project input. The profile does not choose a destination
generation and does not label an older compiler a migration baseline unless a
separate exact project decision establishes that destination. Compiler
migration routes to project-design and compiler-configuration owners.
Version-specific behavior remains bound to exact compiler evidence. A second
compiler line or API is a separately bound compatibility role only where one
exact role independently requires it, with a recorded retirement condition
when temporary and an explicit `not-required` disposition when no role does.

### Target-migration boundary

An exercised embedded checker whose declared compiler support excludes a
separately decided project destination creates a compatibility/migration route,
not a claim that the target already uses that destination and not an automatic
demand for another compiler line. The project and host-tool owners choose
either compatible tooling or one exact temporary compatibility role with a
retirement condition. Package or lock presence does not select a role; a stale
lock routes regeneration to the project/package owner; configured declaration
emit without invocation remains unknown; and static target evidence never
proves build or runtime completion.

## Non-owners

### JavaScript source and runtime

TypeScript does not own JavaScript source-language semantics outside
TypeScript-specific analysis, emitted-JavaScript behavior, runtime
exceptions, runtime module loading, runtime host APIs, or runtime
validation. Checked JavaScript keeps a conceptual JavaScript
source-language owner; no accepted JavaScript skill currently exists, and
none is implied.

### Compiler and project configuration

TypeScript consumes but never selects: the compiler package, compiler role,
exact version, tsconfig values, project references, file inclusion, the
declaration environment, module-resolution policy, and emit policy. These
route to the exact project and compiler-configuration owners.

### JSX, hosts, platforms, build

`.tsx` is not ordinary whole-file TypeScript; JSX syntax and transform
remain separate. `.astro`, `.mdx`, Vue, Svelte, and similar host files keep
their host whole-file owners. Node, browser, and platform API behavior
belongs to the platform; declarations describe it without deciding it. Type
stripping, transpilation, bundling, declaration-generation orchestration,
and runtime execution remain tool, build, and host concerns.

## Compiler-role model

<!-- APG-CLAUSE: TS-COMPILER-ROLES -->
Every selected consequence-bearing compiler role is identified and evidenced
independently, using exactly these role names: `cli-checker`,
`declaration-emitter`, `programmatic-compiler-api`,
`editor-language-service`, `embedded-language-checker`,
`source-transformer-type-stripper`, `build-orchestrator`, `runtime-host`.
Each active role record contains the role, package, exact version, selection
source, product state (`intended`, `current`, or `temporary`), invocation
state (`invoked`, `not-invoked`, or `unknown`), invocation evidence, and a
retirement condition when temporary. `unknown` is an evidence state, never a
role identity. When role identity is unresolved, record no invented role,
package, or version; record the missing identity and required evidence. A
not-required role is absent from active role records, and a known package
candidate is recorded separately from role selection. One package may serve
several roles only when each role is independently evidenced; one role's
evidence never satisfies another.
Package or lockfile presence never proves a role is exercised — an
auto-installed or transitively resolved compiler with no invocation
evidence is presence, not execution.

## Exact-version model

A version fact is an exact resolved version bound to a role, not a range,
dist-tag, or manifest specifier alone. Version-dependent conclusions name
the exact version they rest on. Where behavior may differ across compiler
generations, the generation is part of the version fact; compatibility
between generations is never assumed
(`ts6-ts7-compat-assumption` is a defect, not a default).

## Option-fact model

<!-- APG-CLAUSE: TS-OPTIONS -->
When an option controls the result, the decision requires its exact value:
for example `strict=true`, `strictFunctionTypes=false`,
`exactOptionalPropertyTypes=true`, `noUncheckedIndexedAccess=true`,
`types=[]`, `module="nodenext"`, `moduleResolution="nodenext"`,
`target="es2024"`, `verbatimModuleSyntax=true`,
`experimentalDecorators=false`, `preserveConstEnums=false`,
`isolatedModules=true`, `noEmit=true`, `emitDeclarationOnly=true`. An
option name without a value is not an option fact. Distinguish exactly:
explicit `true`; explicit `false`; explicit string/array value; an
inherited or default value backed by exact version evidence; absent and not
controlling; unknown; and required but unavailable. No complete tsconfig
mirror is kept — only consequence-bearing options enter the decision.

## Present versus required evidence

Every analysis separates the evidence already present (pins, explicit
option values, invocation records) from the evidence still required
(missing roles, versions, values, provenance). The two sets are disjoint;
moving an item from required to present takes new evidence, not restatement.

## Source kinds

<!-- APG-CLAUSE: TS-SOURCE-KIND -->
Source kind is established before analysis and is never collapsed:

- `.ts` — ordinary TypeScript; module format follows configuration and the
  surrounding package context;
- `.mts` — always an ECMAScript module, regardless of package `type`;
- `.cts` — always CommonJS; under `verbatimModuleSyntax=true` its
  value-bearing imports and exports must be CommonJS-shaped
  (`import x = require(...)`, `export =`), while type-only import/export
  declarations remain legal and are erased;
- `.tsx` — JSX-bearing; see the TSX boundary;
- `.d.ts` / `.d.mts` / `.d.cts` — declaration files; see declarations;
- checked JavaScript (`.js`/`.mjs`/`.cjs` under `allowJs`/`checkJs`) — see
  checked JavaScript;
- host-embedded regions — see embedded hosts.

Declaration emit preserves source kind (`.d.mts` from `.mts`, `.d.cts` from
`.cts`); a source-kind conclusion for one kind never transfers to another.

## Ordinary static semantics

<!-- APG-CLAUSE: TS-ASSIGNABILITY -->
Assignability is structural: compatibility follows member shape, not
declared name or intuition about nominal identity. Fresh object literals
receive excess-property checking that aliased values do not; `readonly`
modifiers constrain write sites, not runtime mutability. A structural
conclusion holds only under the evidenced option values — strictness
options change assignability outcomes.

<!-- APG-CLAUSE: TS-NARROWING -->
Narrowing is control-flow analysis over the checked region: discriminated
unions, `typeof`/`in`/equality guards, user-defined type predicates, and
assertion functions narrow within evidenced flow only. Exhaustiveness is
proven with a `never`-typed unreachable arm, not assumed from a switch's
current cases. Narrowing conclusions do not survive aliasing, mutation, or
asynchronous boundaries the analysis cannot see, and a user-written
predicate is an authored claim: the profile checks its declared
consequence, not its runtime truth.

<!-- APG-CLAUSE: TS-GENERICS -->
Generic conclusions — inference, constraint satisfaction, variance
behavior, distribution over unions, and conditional/mapped type results —
are bound to the exact compiler version that produced them. Inference
outcomes may differ between versions and generations; a remembered result
from another version is not evidence.

<!-- APG-CLAUSE: TS-OVERLOADS -->
Overload resolution uses the complete ordered declared-signature set at each
call site. Ordering is consequence-bearing, but literal-specialized and other
applicability rules mean there is no universal "first matching signature"
shortcut. The implementation signature is checked against the overload list
and is not itself callable. A call conclusion names the exact applicable
declared signature; a conclusion about the implementation body uses the
implementation signature. Utility-type inference over an overloaded function
uses the last declared signature rather than call-resolution behavior.

<!-- APG-CLAUSE: TS-TYPE-OPERATORS -->
`any` disables checking wherever it flows; `unknown` requires narrowing
before use; `never` marks unreachable or uninhabited positions. `satisfies`
checks an expression against a target without replacing its resulting type
with that target, but the target can still contextually type the expression
and affect inference or literal widening. Ordinary `as` assertions remain
subject to the compiler's related-type checks; a double assertion through
`unknown` can bypass more checking. Assertions have no runtime effect and are
erased at emit. `keyof`, indexed access, mapped, conditional, and template-literal
types are evaluated under the exact version's rules. An assertion is an
authored claim; `satisfies` is a checked claim — the distinction is owned
and reported.

## Strict-option consequences

<!-- APG-CLAUSE: TS-STRICT-OPTIONS -->
Strictness families change results and are consumed as exact values:
`strict` is an umbrella whose constituent flags may be individually
overridden, so the effective per-flag value is the fact;
`strictFunctionTypes` controls parameter bivariance for function-typed
positions (method-syntax positions stay bivariant even when it is `true`);
`exactOptionalPropertyTypes` distinguishes an absent optional property from
one explicitly set to `undefined`; `noUncheckedIndexedAccess` widens
index-signature and array-element reads to include `undefined`. A
consequence claimed under one value set does not transfer to another.

## Imports and emit-bearing syntax

<!-- APG-CLAUSE: TS-IMPORT-EMIT -->
Type-only imports and exports (`import type`, `export type`) are erased at
emit; `verbatimModuleSyntax=true` makes import/export emit shape explicit
and rejects value-bearing ECMAScript-module syntax in CommonJS-emitting
files, while type-only import/export declarations remain legal there and
are erased. Most TypeScript syntax erases, but some constructs are
emit-bearing — `enum`, `const enum` (with isolated-module analysis disabled,
member references are inlined whether or not `preserveConstEnums` retains an
enum object; `isolatedModules=true` preserves the object, prevents that
substitution, and rejects ambient const-enum member access),
namespaces with runtime members, class fields under
`useDefineForClassFields`, and legacy decorator output. A claim that a
change is "types-only" requires checking the construct against this
boundary under the exact option values.

## Decorators

<!-- APG-CLAUSE: TS-DECORATORS -->
Decorator meaning is regime-bound: standard ECMAScript decorators versus
the legacy `experimentalDecorators=true` regime differ in placement rules,
signatures, metadata, and emit. No decorator conclusion exists without the
exact regime, compiler version, and option values; mixing evidence across
regimes is a defect.

## Declarations

<!-- APG-CLAUSE: TS-DECLARATIONS -->
Declaration files carry static meaning only: a handwritten `.d.ts` asserts
a runtime surface without verifying it, and its claims bind checking
exactly as written. The declaration environment (`lib`, `types`, ambient
declarations, module augmentations) is established evidence, not
background: `types=[]` excludes automatic type packages, and a conclusion
that depends on an ambient surface names the declaration that supplies it.
Module augmentation applies only within the project graph that includes it.

<!-- APG-CLAUSE: TS-GENERATED-DECLARATIONS -->
Generated declarations are compiler output under an evidenced
`declaration-emitter` role: they are regenerated from source, never
hand-edited, and never committed by this candidate's harness. Declaration
provenance — handwritten versus generated versus unknown — is established
before any edit; unknown provenance blocks direct edits and regeneration
claims. Declaration-only emit (`emitDeclarationOnly=true`) produces no
JavaScript: its success is not emit-pipeline or runtime success.

## Checked JavaScript

<!-- APG-CLAUSE: TS-CHECKED-JS -->
Under `allowJs=true`/`checkJs=true` (or per-file `// @ts-check`),
TypeScript applies bounded, non-additive analysis to JavaScript sources
using JSDoc annotations. The file keeps its conceptual JavaScript
source-language owner and the TypeScript selection is `embedded-route`; this
profile owns only the analysis boundary: which
types were inferred or annotated, under which exact options, and what the
analysis cannot see. Checked-JavaScript analysis never rewrites the file
into TypeScript and never implies a migration recommendation.

## TSX

<!-- APG-CLAUSE: TS-TSX -->
A `.tsx` file is not ordinary whole-file TypeScript: the JSX
syntax/transform owner and the exact compiler configuration (`jsx` value,
factory or import source, and the JSX namespace in scope) establish the
region first; TypeScript participates through `embedded-route` and then owns
static typing of the expressions,
attributes, and declarations inside it. Under `jsx="preserve"` the
transform is explicitly external. Element-type checking follows the JSX
namespace actually in scope — a local minimal host declaration is
sufficient evidence and React is not assumed.

## Embedded hosts

<!-- APG-CLAUSE: TS-EMBEDDED-HOST -->
An `.astro`, `.mdx`, Vue, Svelte, or similar file keeps its host
whole-file owner. TypeScript receives a bounded embedded static-analysis
region only after the host or its tooling supplies the exact extracted or
virtual source, the compiler role (normally `embedded-language-checker`
through host tooling such as an Astro checker with an embedded TypeScript
API), and the effective options. The embedded tool's own compiler
selection is a consumed fact: its supported compiler line may lag the
intended primary generation, and that gap is recorded, not papered over.
Without host-supplied extraction evidence, the selection is
`embedded-route` with the analysis not yet performable.

## Static/runtime boundary

<!-- APG-CLAUSE: TS-STATIC-RUNTIME -->
Types are erased at emit. A clean check under an exact compiler proves
static consistency of the checked region and nothing further: not
emitted-JavaScript correctness, not runtime behavior, not host or platform
behavior, and not pipeline completion. Assertions and declaration files are
authored claims that the runtime never validates. Any claim that crosses
from static success to runtime success is refused and routed to the runtime
owner with `stop-and-escalate` when it would otherwise be asserted.

## Unknown-state rules

Missing exact compiler role: `stop-and-escalate`. Missing
consequence-bearing option value: `inspect-before-judgment`, or
`stop-and-escalate` when a result would otherwise be asserted. Unknown
source kind: `inspect-before-judgment`. Unknown declaration provenance:
stop before any direct edit or regeneration claim. Static success offered
as runtime proof: `stop-and-escalate`. Host or runtime behavior requested:
selection `route-to-owner`, response `proceed-routine`. Ordinary established
TypeScript static question:
`proceed-routine`. Stopping rather than inferring is the required behavior
whenever role, version, option, source-kind, or declaration evidence is
missing.

## Structural-policy deferral

<!-- APG-CLAUSE: TS-STRUCTURE-DEFERRED -->
TypeScript structural policy is deferred under ADR 0042. Line count is
descriptive only; numeric line, file, or statement bands are forbidden;
automatic JavaScript-to-TypeScript migration is forbidden; and whole-file
decomposition judgment belongs to the project-design owner. The profile may
identify that a question is structural and must route it rather than judge
it. No structural signal table exists in this candidate.

## Provenance and rollback

<!-- APG-CLAUSE: TS-ROLLBACK-AND-PROVENANCE -->
Before a material repair, record the pre-change state rollback needs: the
exact prior source region; for declaration work, the prior declaration
bytes and their provenance class; and the exact configuration and version
evidence the conclusion rested on. Regenerable artifacts are rolled back by
regeneration from recorded source state; authored artifacts are rolled back
by restoring recorded bytes. A repair without a recorded rollback boundary
is incomplete.

## Completion criteria

A TypeScript-owned decision is complete when: the selection state,
response, and routes are reported; every consequence-bearing role, version,
and option value used is named; present and required evidence are listed
disjointly; static conclusions are stated as static; provenance and
rollback boundaries are recorded where material; and no routed stop remains
unresolved. Completion is never claimed on inferred evidence.

## Refresh conditions

Re-establish evidence when: the resolved compiler version or generation
changes for any bound role; tsconfig values change for a consequence-bearing
option; the project graph, lib, or declaration environment changes; host
tooling changes its embedded compiler selection or supported compiler line;
or a project-owned compatibility disposition's refresh condition fires
(an exercised embedded checker whose exact peer range excludes the selected
project destination). The fixture's pinned compiler is refreshed only by a later
phase's fresh selection, not by drift.

## Known limitations

- The candidate constrains judgment; it cannot execute the compiler, so
  every version-bound behavioral claim ultimately defers to the evidenced
  compiler run.
- Coverage is deliberately narrow: language features outside the owned
  areas (for example full JSX typing regimes, project-reference build
  semantics, or a compiler-version-specific API surface) are routed, not
  owned.
- The Astro embedded boundary in the harness is a nonexecuted host fixture;
  exercising a real embedded checker is APG75-or-later work.
- Checked-JavaScript analysis quality depends on JSDoc fidelity the profile
  does not control.

## Current lifecycle boundary

APG74 remains the exact authored, Proposed, branch-only historical object.
APG75 independently reconstructed expected behavior, built maintained
failing-first tests, validated the fixture against targets, accepted ADR 0043
with amendment, and provisionally integrated the profile. APG75A corrects the
reusable compiler-generation boundary, response vocabulary, lifecycle
surfaces, and clean-runner prerequisite without changing that provisional
status. No readiness, publication, deployment, stable-maturity, target
migration, CSS, or successor authority follows from this specification.
