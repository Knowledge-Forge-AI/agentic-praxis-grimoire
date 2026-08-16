---
name: nodejs-runtime-profile
description: Use when a material decision depends on Node.js-specific host behavior — package scope and module mapping, CommonJS wrapper bindings, ESM host metadata, specifier resolution and package exports, module identity, process and CLI state, stdio and exit status, filesystem and path APIs, errors, signals, timers and the event loop, child processes and workers, or Node's exposure of network and Web-compatible APIs — for an established Node execution role whose exact version, platform, flags, package scope, loader, and whole-file owner are identified.
---

# Node.js Runtime Profile

Normative detail:
[Node.js Runtime Profile](../../docs/specs/nodejs-runtime-profile.md).
Status: Provisionally integrated in APG81H under ADR 0046, Accepted with
amendment.
Lifecycle: `provisionally-integrated`.
Lifecycle ADR: `Accepted with amendment`.

## Core principle

<!-- APG-CLAUSE: NODE-TRIGGER -->
Apply Node judgment only when a current, consequence-bearing decision materially
depends on Node-specific host behavior for an **established** Node execution
role — one whose exact runtime version, platform, architecture, flags, package
scope, module mapping, loader identity, invocation, and whole-file owner are
already identified. Establishing that role is an input to this profile, not a
result of it. The presence of JavaScript or TypeScript source establishes
nothing, and neither does an installed Node executable.

<!-- APG-CLAUSE: NODE-SELECTION -->
Keep three axes separate: selection (`selected`, `embedded-route`,
`route-to-owner`, or `non-trigger`), response, and a small ordered set of routes
or obligations with one item per simultaneous non-Node decision. Selection is
decision-scoped and orthogonal to whole-file ownership. `selected` means this
profile answers the exact Node decision for an established role; it does not say
who owns the file. A standalone `.cjs` artifact is not `embedded-route` merely
because CommonJS is a host wrapper — record its whole-file owner separately and
reserve `embedded-route` for Node source genuinely nested in another host file.

<!-- APG-CLAUSE: NODE-RESPONSE -->
Answer the one coherent current decision at the highest justified
`proceed-routine`, `inspect-before-judgment`, `bounded-local-decision`, or
`stop-and-escalate` response. Selection and response are disjoint:
`route-to-owner` is a selection, never a response. Routing never lowers the
response, and a routed stop stays stopped until its owner resolves it.

<!-- APG-CLAUSE: NODE-ROUTES -->
Name the receiving owner exactly — `javascript-language-owner`,
`typescript-owner`, `project-design-owner`, `project-configuration-owner`,
`package-manager-owner`, `shell-owner`, `operating-system-owner`,
`filesystem-owner`, `network-owner`, `browser-platform-owner`,
`build-transform-owner`, `test-owner`, `security-owner`, `performance-owner`,
`deployment-owner`, or `service-supervisor-owner` — and do not collapse two
distinct decisions because they share one owner.

## Do not use

<!-- APG-CLAUSE: NODE-NONTRIGGER -->
Do not use this profile for:

- ECMAScript language semantics: scope, coercion, ordinary object semantics,
  functions, classes, iteration, Promise language semantics, or module binding
  and evaluation. Node may supply host inputs such as parse-goal mapping,
  linking, loading, or `HostEnqueuePromiseJob`; host input transfers no language
  authority;
- TypeScript: parsing, checking, inference, declaration emit, compiler options,
  source transformation, or JavaScript-versus-TypeScript migration;
- package managers: npm, pnpm, Yarn, or Bun installation, registry selection,
  lockfile generation, workspace filtering, dependency solving, lifecycle-script
  orchestration, publication, or supply-chain approval;
- shell and operating system: tokenization, quoting, expansion, pipelines,
  redirection, globbing, kernel scheduling, permissions, durability beyond the
  Node API contract, service supervision, or container behavior;
- network and security: DNS correctness, HTTP application correctness, TLS
  policy, remote-service behavior, credential approval, threat acceptance, or
  deployment exposure;
- the browser and Web platform: DOM, rendering, storage, navigation, or browser
  compatibility; or
- build, test, and product policy: bundlers and transforms, lint policy,
  test-framework semantics, release approval, readiness, publication,
  deployment, or product architecture.

A non-trigger names the receiving owner exactly. When that receiver is absent,
the named obligation remains `stop-and-escalate`: it is not a live handoff and
does not claim completion. Adjacency to Node never makes it a Node decision.

## Required evidence intake

<!-- APG-CLAUSE: NODE-EVIDENCE -->
Before any Node-owned conclusion, bind from evidence — and keep present evidence
strictly separate from evidence still required:

- the artifact class and the whole-file owner, then this profile's selection
  state for this one decision;
- the runtime role (see below), and the exact package scope, module mapping,
  loader identity, and condition set the conclusion depends on;
- the installed filesystem and package-graph facts, current working directory,
  environment inputs, standard-stream and terminal state, parent or supervisor
  state, and any filesystem, network, signal, or lifecycle state in scope;
- build or transform provenance when the artifact was generated;
- the target pin and its execution state when a target conclusion is sought.

An option, field, package, API, or flag name without its exact value is not a
fact. One role's evidence never satisfies another. Package presence, a lockfile,
a manifest range, or a package-manager declaration is never module loading and
never runtime invocation. Unknown consequence-bearing evidence stops only the
dependent conclusion. Present and required evidence are disjoint sets.

<!-- APG-CLAUSE: NODE-RUNTIME-ROLE -->
Record every consequence-bearing runtime role separately: role identity, runtime
family, exact version or `unresolved`, executable identity, selection source,
product state (`intended`, `current`, `temporary`, `unresolved`), invocation
state (`invoked`, `not-invoked`, `unresolved`), platform, architecture, flags,
and any retirement condition. A version range, a package-manager declaration, a
continuous-integration release line, an installed executable, a selected
executable, an invoked executable, and the local authoring engine are seven
different facts. Never invent a role, version, flag, or execution occasion.

## Procedure

1. Classify the artifact, identify the whole-file owner, and set this decision's
   selection state.
2. Establish the runtime role and the package, mapping, and loader facts the
   question depends on, listing what is present and what is still required.
3. Analyze only Node-owned host behavior for the established role:
   <!-- APG-CLAUSE: NODE-PACKAGE-SCOPE -->
   the nearest controlling manifest and the package scope it establishes, which
   never leaks across an independently established package boundary;
   <!-- APG-CLAUSE: NODE-MODULE-MAPPING -->
   Node's mapping of `.mjs`, `.cjs`, `.js`, standard input, and evaluated input
   under the exact version and flags — mapping is Node host behavior, never
   ECMAScript grammar authority, and source syntax participates only where the
   exact version establishes that it does;
   <!-- APG-CLAUSE: NODE-COMMONJS -->
   CommonJS wrapper bindings, wrapper scope and top-level `this`, the
   `module.exports` and `exports` alias boundary, `require` loading, and cycle
   and error boundaries;
   <!-- APG-CLAUSE: NODE-ESM -->
   Node ESM host metadata, URL-based module identity, `node:` built-in
   specifiers, the absence of wrapper globals, and dynamic-import host loading;
   <!-- APG-CLAUSE: NODE-RESOLUTION -->
   specifier resolution, package `exports` and `imports`, condition selection,
   self-reference, and encapsulation refusal;
   <!-- APG-CLAUSE: NODE-INTEROP -->
   version-sensitive interoperability, including default-export mapping, static
   named-export detection and its failure modes, and requiring a module;
   <!-- APG-CLAUSE: NODE-CACHE -->
   module identity and cache behavior under exact specifier and loader facts;
   <!-- APG-CLAUSE: NODE-CLI-ENTRY -->
   entrypoint selection, `process.execPath`, `process.execArgv`, `process.argv`,
   and working directory;
   <!-- APG-CLAUSE: NODE-PROCESS-STATE -->
   `process.env`, platform, architecture, and process state as external inputs
   that authorize no logging, persistence, or publication;
   <!-- APG-CLAUSE: NODE-STDIO-STREAMS -->
   standard streams, terminal state, encoding, write results, and backpressure;
   <!-- APG-CLAUSE: NODE-FILESYSTEM -->
   filesystem, path, and file-URL API contracts;
   <!-- APG-CLAUSE: NODE-ERRORS-EXIT -->
   thrown errors, callback errors, rejections, warnings, and exit status;
   <!-- APG-CLAUSE: NODE-SIGNALS-LIFECYCLE -->
   signal events, signal-derived termination, and shutdown boundaries;
   <!-- APG-CLAUSE: NODE-EVENT-LOOP -->
   `process.nextTick`, microtask integration, timers, immediates, and event-loop
   phases, always bounded to the exact scheduling context;
   <!-- APG-CLAUSE: NODE-CHILD-PROCESS -->
   `child_process` API contracts and local child lifecycle;
   <!-- APG-CLAUSE: NODE-WORKERS -->
   `worker_threads` availability, entrypoint selection, message passing, and
   termination state;
   <!-- APG-CLAUSE: NODE-NETWORK-WEBAPI -->
   Node's exposure and local lifecycle of network and Web-compatible APIs;
   <!-- APG-CLAUSE: NODE-FLAGS-PERMISSIONS -->
   runtime flags, `NODE_OPTIONS`, custom loaders, the permission model, and
   diagnostics, each of which is part of the evidence rather than an assumption.
4. Route every simultaneous adjacent decision as one item in a small ordered set
   while leaving the Node response unchanged.
5. Stop rather than infer when a runtime role, package scope, mapping, loader,
   invocation, or host input is missing, and separate source-language semantics,
   transformation, Node mapping, resolution and loading, ECMAScript evaluation,
   Node runtime behavior, external operational effect, and product readiness in
   every report.

## Package-manager and shell boundary

<!-- APG-CLAUSE: NODE-PACKAGE-MANAGER-BOUNDARY -->
Node may execute an entrypoint that another tool selected. It owns none of that
selection. Keep the package-manager identity and version, workspace selection,
lockfile and install graph, script name, script command, the shell the package
manager chose, environment and `PATH` mutations, the Node executable the command
named, the invocation, and the resulting process status as separate facts. A
`packageManager` field selects a package-manager role, not a Node process. A
dependency's engine constraint may bound an install graph without becoming the
project's runtime selection. A script body is command configuration, not proof
that it ran.

## Runtime and completion boundary

<!-- APG-CLAUSE: NODE-STATIC-RUNTIME-COMPLETION -->
One runtime observation proves only that observed result under that exact
executable, version, platform, architecture, flag set, command, input, and
filesystem state. It is never universal Node behavior across versions,
platforms, flags, loaders, or package states. A clean parse or a resolved
specifier is not evaluation. A successful evaluation is not an external effect.
A write call is not delivery. A filesystem call is not durability or
authorization. A socket is not protocol, remote-system, security, or deployment
success. A correct CLI core result is not a working command, and a working
command is not readiness, publication, or deployment.

## Structural policy

<!-- APG-CLAUSE: NODE-STRUCTURE-DEFERRED -->
Node structural policy is **deferred**. No threshold exists or may be introduced
for file size, statement or function count, dependency count, number of side
effects, child processes or workers, cyclomatic complexity, latency,
throughput, memory, or package size, and none automatically selects a runtime,
an architecture, or a migration.

Qualitative observations — language core and Node adapter entangled, implicit
process-global state, unbounded filesystem or network effects, ambiguous
shutdown, shell invocation hidden behind a helper, runtime selection hidden in
package-manager behavior, an unclear module-system boundary, synchronous
blocking on a server or interactive path, or unowned worker and child lifecycle
— may route review to `project-design-owner`. Such an observation never decides
failure, migration, or architecture.

## Project-owned parameters

The repository and project own: the JavaScript-versus-TypeScript choice; runtime
family, version, platform, and flag selection; package shape, `type`,
extensions, `exports`, and conditions; package-manager and workspace selection;
build, transform, lint, and test selection; service, daemon, worker, and
child-process architecture; security approval; performance acceptance;
deployment; structural and migration policy; accepted exceptions; and any
stricter repository policy, which always controls.

## Stop or escalate

<!-- APG-CLAUSE: NODE-UNKNOWN-STOP -->
Apply these responses exactly:

- missing artifact class or whole-file owner: `inspect-before-judgment`;
- unresolved package scope, module mapping, or loader identity where the result
  depends on it: `stop-and-escalate` for that dependent conclusion only;
- unresolved exact version, platform, or flag set for a version-dependent
  result, or an unresolved runtime role the result depends on:
  `stop-and-escalate`;
- a range, `packageManager` field, lockfile, script definition, or
  continuous-integration configuration offered as an exact runtime or an
  invocation: `stop-and-escalate`;
- a Node result offered as ECMAScript evaluation, external I-O, protocol,
  security, or deployment completion: `stop-and-escalate`;
- language, TypeScript, package-manager, shell, operating-system, network,
  browser, build, security, or product-policy question: set selection to
  `route-to-owner` and keep the response at whatever the remaining Node decision
  justifies — routing is not a response and never replaces one;
- established Node question with complete inputs: `proceed-routine`.

This profile is deliberately partial. Native addons and N-API, WASI, `vm` and
policy sandboxes, `cluster`, the inspector protocol, the full crypto surface,
all diagnostic channels, all experimental APIs, and all platform differences
stop at the established local boundary and require separate source-backed
extension. Partial coverage never implies comprehensive Node ownership.

## Evidence and completion

<!-- APG-CLAUSE: NODE-ROLLBACK -->
Before a material repair, record what rollback needs: the exact prior bytes, the
runtime role and flags the conclusion rested on, the package scope, mapping, and
loader facts, the artifact class and provenance, and any external state the
change touched. Report the selection state, the response, the evidence
bindings, each exact route, and the rollback boundary. Never claim completion
while required evidence is missing, while a routed stop is unresolved, or in
terms that let a Node result stand in for a language, operational, or product
one.

Rollback is history preserving: deactivate only current integration owners.
Preserve the candidate, ADR, phase commits and records, evidence history, and
unrelated known debt. Never describe deletion of those records as rollback.

## Common mistakes

- Selecting Node because JavaScript or TypeScript source exists, or promoting
  one observed runtime into a universal or reusable runtime choice.
- Reading a manifest range, `packageManager` field, or lockfile as an exact
  runtime version or as an invocation.
- Mapping `.js` without the nearest package scope, flattening `.mjs`, `.cjs`,
  and `.js` into one mapping, or promoting an unresolved mapping to a known one.
- Presenting a Node mapping or loader result as ECMAScript authority, or moving
  a standalone CommonJS artifact's whole-file ownership to the language owner.
- Treating static named-export detection as a live-binding guarantee, or stating
  one universal interoperability rule across Node versions.
- Assigning package installation, shell grammar, or operating-system policy to
  Node, or reading an environment value and then logging or retaining it.
- Presenting a stdout write as delivery, a filesystem call as durability or
  authorization, a spawned child as shell safety, or a network call as remote
  success.
- Reusing an event-loop ordering observation without its exact scheduling
  context, entry module system, version, and flags.
- Introducing a structural threshold, or recommending a runtime or architecture
  migration, under Node authority.
