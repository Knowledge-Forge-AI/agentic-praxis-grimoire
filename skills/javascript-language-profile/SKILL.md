---
name: javascript-language-profile
description: Use when a material decision depends on ECMAScript language semantics — evaluation order, lexical scope and temporal dead zones, coercion and equality, prototypes and property descriptors, this binding, classes, iteration, completion values, promise and async semantics, or module live bindings — for an established JavaScript source region whose parse goal, strictness state, and whole-file owner are identified.
---

# JavaScript Language Profile

Normative detail:
[JavaScript Language Profile](../../docs/specs/javascript-language-profile.md).
Status: Provisionally integrated in APG79E under ADR 0045 after APG78
authoring, APG79 through APG79B hardening, APG79C human acceptance of
`JS-QD-001` through `JS-QD-004`, the APG79D Test262 source-role correction, and
APG79E human acceptance of `JS-QD-005` and provisional integration. All five
accepted Medium limitations block stable maturity. Test262 is
non-normative rights-only evidence and supplies no corpus or oracle input.
Lifecycle: `provisionally-integrated-with-known-debt`.
Lifecycle ADR: `Accepted with amendment`.

## Core principle

<!-- APG-CLAUSE: JS-TRIGGER -->
Apply ECMAScript judgment only when a current, consequence-bearing decision
materially depends on the language semantics of an **established** JavaScript
source region — one whose exact source bytes, parse goal, strictness state,
edition authority, whole-file owner, and consequence-bearing host inputs are
already identified. Establishing that region is an input to this profile, not a
result of it. A `.js` suffix alone establishes nothing.

<!-- APG-CLAUSE: JS-SELECTION -->
Keep three axes separate: selection (`selected`, `embedded-route`,
`route-to-owner`, or `non-trigger`), response, and a small ordered set of routes
or obligations with one item per simultaneous non-language decision. Selection
is decision-scoped and orthogonal to whole-file ownership. `selected` means this
profile answers the exact ECMAScript decision for an established region; it
does not say who owns the file. `embedded-route` is reserved for a JavaScript
region nested inside a different host file, such as an Astro script region,
while that host owner stays controlling.

<!-- APG-CLAUSE: JS-RESPONSE -->
Answer the one coherent current decision at the highest justified
`proceed-routine`, `inspect-before-judgment`, `bounded-local-decision`, or
`stop-and-escalate` response. Selection and response are disjoint:
`route-to-owner` is a selection, never a response. Routing never lowers the
response, and a routed stop stays stopped until its owner resolves it.

<!-- APG-CLAUSE: JS-ROUTES -->
Name the receiving owner exactly — `project-design-owner`,
`project-configuration-owner`, `node-runtime-owner`, `browser-platform-owner`,
`module-loader-owner`, `build-transform-owner`, `host-owner`, `typescript-owner`,
`jsx-owner`, `security-owner`, `performance-owner`, or `deployment-owner` — and
do not collapse two distinct decisions because they share one owner.

## Do not use

<!-- APG-CLAUSE: JS-NONTRIGGER -->
Do not use this profile for:

- Node.js: `process`, `Buffer`, `fs`, `path`, `os`, `stream`, `child_process`,
  `worker_threads`, signals, environment variables, exit codes, Node timers,
  Node event-loop phases, CommonJS wrapper bindings, `require` resolution,
  package exports, loader hooks, or Node security policy;
- the browser and Web platform: DOM, Web APIs, browser events, timers, `fetch`,
  storage, workers, rendering, browser module fetching, or compatibility policy;
- module *resolution* or loading: specifier resolution, package exports and
  imports, network fetching, filesystem lookup, CommonJS loading, bundler graph
  construction, or loader configuration;
- transformation and tooling: Babel, SWC, esbuild, Vite, or Astro transforms,
  minification, bundling, source maps, lint or formatter policy, engine
  selection, or build completion;
- adjacent languages and hosts: TypeScript static analysis, JSX syntax or
  transform, React component semantics, MDX or Astro whole-file semantics, CSS,
  HTML, or JSON as a data format; or
- project policy: JavaScript-versus-TypeScript choice, security approval,
  architectural decomposition, performance acceptance, deployment, or product
  behavior.

A non-trigger names the receiving owner exactly. When that receiver is absent,
the named obligation remains `stop-and-escalate`: it is not a live handoff and
does not claim completion. Adjacency to JavaScript never makes it a language
decision. An absent receiver is always a stopped obligation.

## Required evidence intake

<!-- APG-CLAUSE: JS-EVIDENCE -->
Before any language-owned conclusion, bind from evidence — and keep present
evidence strictly separate from evidence still required:

- the artifact class (handwritten `.js`/`.mjs`/`.cjs`/`.jsx`; TypeScript source;
  host file with an embedded script region; JavaScript configuration file;
  Node-oriented script or CLI entrypoint; browser-oriented script;
  package-script command; generated, bundled, minified, or vendor JavaScript;
  source map; JSON or data mistaken for JavaScript; documentation sample;
  fixture; or unknown);
- the whole-file owner and this profile's selection state for this one decision;
- the exact **parse goal**, **host context**, **language contexts**, and **goal
  evidence state**, then the strictness state (see below); these are separate
  fields;
- the exact ECMA-262 edition or draft governing the question, with its
  publication status;
- every consequence-bearing engine and host role independently and per decision
  — as `known`, `not-selected`, `not-required`, or `unresolved`, with exact
  executable, version, selection source, and invocation evidence when `known`.
  Package or lockfile presence never proves a role runs, a configuration option
  is not an invocation, and one role's evidence never satisfies another;
- the linking facts a module conclusion depends on, and the exact inputs an
  evaluation conclusion reads.

An option or feature name without its exact value is not a fact. When a required
input is missing, name it as required evidence rather than assuming a default.
Present and required evidence are disjoint sets.

## Parse goal, host context, language context, goal evidence, and strictness

<!-- APG-CLAUSE: JS-SOURCE-GOAL -->
Classify parse goal as ECMAScript `script`, ECMAScript `module`, or
`unresolved`. Separately classify host context, such as `standalone`,
`commonjs-wrapper`, `host-embedded`, or `host-transformed`; the nonempty set of
language contexts the current decision actually crosses, such as `global-code`,
`module-body`, `function-body`, `parameter-list`, `block`, or `class-body`; and
goal evidence state as `known` or `unresolved`. Configuration-module status is
an artifact role, not a host context. A host wrapper, language context,
embedded region, or unresolved evidence state
is not an ECMAScript parse goal.

Host-selected extensions and package settings are **evidence inputs**, not
ECMAScript-standard filename rules: `.mjs`, `.cjs`, and a package `type` field
are host and project facts whose language consequences this profile may consume.
`.cjs` is not a standardized ECMAScript goal; CommonJS wrapper bindings and
behavior remain Node-owned. Never flatten `.js`, `.mjs`, and `.cjs` into one
source kind. Source text containing `import` or `export` indicates a question
but does not replace exact host or parser evidence when classification is
disputed. An unresolved goal blocks every goal-sensitive conclusion and nothing
else.

<!-- APG-CLAUSE: JS-STRICTNESS -->
Module source is strict by language definition; Script source may be strict or
non-strict according to the exact directive and context. Strictness changes real
consequences — assignment failures, `delete` failures, `this` in ordinary calls,
duplicate parameter rules — so bind it before any dependent conclusion.

## Procedure

1. Classify the artifact, identify the whole-file owner, and set this
   decision's selection state.
2. Establish parse goal and strictness, then complete the evidence intake,
   listing what is present and what is still required.
3. Analyze only ECMAScript-owned semantics for the established region:
   <!-- APG-CLAUSE: JS-BINDINGS-SCOPE -->
   declaration instantiation for the exact global, module, function, parameter,
   block, and Annex B context; TDZ, block scope, and closure capture;
   <!-- APG-CLAUSE: JS-EVALUATION-ORDER -->
   evaluation order, completion records, short-circuit and `?.` boundaries;
   <!-- APG-CLAUSE: JS-COERCION-EQUALITY -->
   `ToPrimitive`/`ToNumber`/`ToString` and the four equality operations;
   <!-- APG-CLAUSE: JS-OBJECTS-PROTOTYPES -->
   object creation, prototype chains, and property lookup;
   <!-- APG-CLAUSE: JS-PROPERTIES -->
   property descriptors, assignment, deletion, strict-mode failures;
   <!-- APG-CLAUSE: JS-FUNCTIONS-THIS -->
   parameters, defaults, rest and spread, ordinary and arrow `this`;
   <!-- APG-CLAUSE: JS-CLASSES -->
   class construction, `super`, field order, and private elements;
   <!-- APG-CLAUSE: JS-ITERATION -->
   destructuring, the iteration protocol, and iterator closing;
   <!-- APG-CLAUSE: JS-ERRORS -->
   `throw`/`return`/`finally` completion interaction;
   <!-- APG-CLAUSE: JS-PROMISES-ASYNC -->
   promise reactions and async propagation, bounded to Jobs and exact host
   enqueue hooks such as `HostEnqueuePromiseJob`;
   <!-- APG-CLAUSE: JS-MODULES -->
   module declarations, live bindings, namespaces, and cyclic semantics
   **after** linking facts are established.
4. Route every simultaneous adjacent decision as one item in a small ordered
   set while leaving the language response unchanged.
5. Stop rather than infer when an artifact class, parse goal, strictness state,
   edition authority, engine role, or host input is missing, and separate
   syntax, language evaluation, host integration, and external operational
   effect in every report.

## Language and host boundary

<!-- APG-CLAUSE: JS-HOST-BOUNDARY -->
Keep four layers separate: syntax and early errors; ECMAScript evaluation
semantics; host and runtime integration; and external operational effect. A
promise reaction ordering claim may be bounded to Jobs and the requirements on
`HostEnqueuePromiseJob`, but ordering
relative to Node timers or browser tasks belongs to the host owner.

<!-- APG-CLAUSE: JS-STATIC-HOST-COMPLETION -->
A parser pass proves only that exact parser's result. One engine run proves only
that observed engine result under that exact command, version, mode, and input —
never universal ECMAScript semantics. An implementation's behavior is
observation, not normative authority, and a TC39 proposal is not current
ECMAScript semantics merely because an engine implements it. Language success
never proves build, module loading, I/O, user-visible, deployment, or security
completion.

### Module boundary

This profile may own ECMAScript module binding and evaluation semantics once the
module graph and linking facts are established. It does not own specifier
resolution, package exports and imports, network fetching, filesystem lookup,
CommonJS loading, bundler graph construction, or loader configuration. An
`import()` expression is a language construct whose resolution and loading route
to `module-loader-owner`.

### Checked JavaScript

<!-- APG-CLAUSE: JS-CHECKED-JS -->
Checked JavaScript — a JavaScript file for which a `// @ts-check` comment, a
project `checkJs` setting, or equivalent requests or selects checking — does not
acquire its whole-file owner from checked status. An ordinary checked
JavaScript source file may remain JavaScript-owned; a standalone JavaScript
configuration module may remain `project-configuration-owner` while this
profile is `selected` for its bounded ECMAScript decision. TypeScript
participates separately for the checking decision only when exact checker
selection and invocation evidence exists. A directive or configuration is not
checker invocation evidence: a checking conclusion also requires the exact
compiler, configuration, inclusion, invocation, and diagnostic result. A
TypeScript diagnostic neither transfers the file nor settles an ECMAScript,
configuration, loader, build, or deployment decision.

### Pure CLI core versus Node adapter

<!-- APG-CLAUSE: JS-CLI-BOUNDARY -->
A JavaScript CLI utility separates an effect-free ECMAScript computation from
its Node adapter and I/O shell. The core receives argument and environment
values as ordinary data, transforms them under ECMAScript semantics, and
returns a structured result including any message data. It does not call an
injected writer — that part may be language-owned.
Argument acquisition, `process.env`, stdout and stderr, the filesystem, the
network, signal handling, and exit status are Node-owned; every adapter decision
routes to `node-runtime-owner`. A correct core result is not a working command.

## Structural policy

<!-- APG-CLAUSE: JS-STRUCTURE-DEFERRED -->
JavaScript structural policy is **deferred**. No line-count band,
statement-count band, function-count threshold, cyclomatic-complexity threshold,
percentile, or accumulation score exists or may be introduced, and none
automatically selects TypeScript. No static or runtime finding automatically
orders migration, refactoring, or conversion to a Node package. The product
orientation — JavaScript preferred for short, simple user scripts and CLI
utility cores, TypeScript preferred for larger or more complicated utilities —
is recorded project context, not a profile trigger. Once an exact JavaScript
source region is established, it is analyzed as JavaScript.

Qualitative observations — host and language concerns entangled, implicit
mutable shared state, unclear module boundary, unbounded side effects, complex
error propagation, or runtime-dependent behavior hidden in a pure-looking core —
may route review to `project-design-owner`. Such an observation never decides
failure and never orders migration. Migration may be recommended only by a
separately authorized project-design decision with exact evidence.

## Project-owned parameters

The repository and project own: the JavaScript-versus-TypeScript choice; the
ECMAScript edition in scope; engine and runtime selection; package `type`,
extensions, and module configuration; package manager and resolution; build,
transform, lint, and formatter selection; host framework selection; security
approval; performance acceptance; deployment; structural and migration policy;
accepted exceptions; and any stricter repository policy, which always controls.

## Stop or escalate

<!-- APG-CLAUSE: JS-UNKNOWN-STOP -->
Apply these responses exactly:

- missing artifact class or whole-file owner: `inspect-before-judgment`;
- unresolved parse goal or strictness where the result depends on it:
  `stop-and-escalate` for that dependent conclusion only;
- missing exact edition or draft for a version-dependent result, or an
  unresolved engine or host role the result depends on: `stop-and-escalate`;
- module conclusion sought without established linking facts:
  `inspect-before-judgment`, or `stop-and-escalate` when a resolution or
  loading result would otherwise be asserted;
- language success offered as host, I/O, build, or deployment completion:
  `stop-and-escalate`;
- Node, browser, loader, build, TypeScript, JSX, security, or product-policy
  question: set selection to `route-to-owner` and keep the response at whatever
  the remaining language decision justifies — routing is not a response and
  never replaces one;
- established language question with complete inputs: `proceed-routine`.

This profile is deliberately partial. Questions about `Proxy`, `Reflect`, the
memory model, `SharedArrayBuffer` and shared memory, ECMA-402, regular expression
semantics, or unlisted built-ins stop at the established local consequence and
require a separate exact source-backed decision before extension. Partial
coverage never implies comprehensive JavaScript ownership.

## Evidence and completion

Before a material repair, record what rollback needs: the exact prior source
bytes, the parse goal and strictness the conclusion rested on, the artifact
class and provenance, and the engine and host evidence. Report the selection
state, the response, the evidence bindings, each exact route, and the rollback
boundary. Never claim completion while required evidence is missing, while a
routed stop is unresolved, or in terms that let a language result stand in for a
host or operational one.

## Common mistakes

- Inferring JavaScript execution, or a parse goal, from a `.js` suffix alone; or
  treating `.cjs` as a standardized goal or CommonJS bindings as language.
- Reading module syntax as module resolution or loading, or asserting a
  live-binding or namespace result without established linking.
- Assigning `process`, the filesystem, or DOM APIs to JavaScript, or claiming
  promise ordering against Node timers or browser tasks without the host owner.
- Transferring whole-file ownership of a checked JavaScript file to TypeScript,
  or treating a CLI adapter as part of the pure core.
- Presenting a clean parse or one engine run as universal ECMAScript proof, or a
  correct core result as a working command.
- Introducing a numeric complexity threshold, or recommending a
  JavaScript-to-TypeScript migration, under language authority.
