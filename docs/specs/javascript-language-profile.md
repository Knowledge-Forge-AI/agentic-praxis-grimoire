# JavaScript Language Profile

## Status and authority

Provisionally integrated in APG79E after APG78 authoring, APG79 hardening round
3, and terminal-proof correction under separate APG79A human continuation authority.
Fresh APG79A review found five Medium material defects with no accepted
JavaScript debt. APG79B uses a separately authorized bounded correction for
those five findings. Fresh review found four unique Medium qualification
defects. APG79C human-accepts exactly those four for provisional use under
their safe restrictions. APG79D corrects the separate Test262 source-identity
defect but leaves a report-binding limitation. APG79E human-accepts that exact
fifth Medium item, directly verifies the report, and passes the ordinary
product gates. All five block stable maturity. ADR 0045 is **Accepted
with amendment**. The lifecycle is
`provisionally-integrated-with-known-debt`; catalog, projection, maturity,
capability route, project selection, release, and test owners are current.
Lifecycle: `provisionally-integrated-with-known-debt`.
Lifecycle ADR: `Accepted with amendment`.

Governing authority is
[ADR 0042](../adr/2026/08/0042-language-profile-production-recovery-and-iterative-hardening.md)
(Accepted), the
[language-profile production-recovery charter](../governance/language-profile-production-recovery-charter.md),
and the
[iterative-hardening contract](language-profile-iterative-hardening-contract.md).

ADR 0039 and ADR 0040 remain **Rejected**. Their architectures, contracts, and
registers are historical falsification evidence. This candidate inherits no
contract from them and revives no mechanism they defined.

APG79 independently hardened this candidate and preserved its repair checkpoint.
APG79A and APG79B each failed their zero-debt review gate. APG79C and APG79E
supply the two human debt decisions, APG79D owns the separately authorized
source-evidence correction, and APG79E owns integration closure. APG78 grants
none of those phases authority.

The candidate leaf is
[`skills/javascript-language-profile/SKILL.md`](../../skills/javascript-language-profile/SKILL.md).
Navigation coverage is
[the scenario-coverage record](javascript-language-profile-scenario-coverage.md).

## Scope

This profile owns **ECMAScript language semantics for an established JavaScript
source region** — a region whose exact source bytes, parse goal, strictness
state, edition or draft authority, whole-file owner, and consequence-bearing
host inputs are already established.

Establishing the region is an input, not a result. The project-design owner
chooses whether a utility is JavaScript or TypeScript. Once an exact JavaScript
source region exists, this profile answers only the bounded ECMAScript language
question about it.

Node.js remains a later, separate runtime and stack owner. No part of this
candidate creates, implies, or reserves a Node profile.

The candidate does not cover every built-in, syntax form, or proposal, and does
not claim to. It covers the semantic areas below and stops elsewhere.

## Trigger and selection

<!-- clause: JS-TRIGGER -->
The profile triggers when a current, consequence-bearing decision materially
depends on the language semantics of an established JavaScript region. It does
not trigger on file extension, on the presence of a package, or on the mere
existence of JavaScript in a repository.

<!-- clause: JS-SELECTION -->
Selection is one of exactly four values:

| Value | Meaning |
| --- | --- |
| `selected` | this profile answers the exact ECMAScript decision for an established region; whole-file ownership is recorded separately |
| `embedded-route` | a bounded JavaScript region inside a host file; the host owner keeps the file |
| `route-to-owner` | the question belongs to a named non-language owner |
| `non-trigger` | the question is not a JavaScript question at all |

Selection is **decision-scoped**. It never transfers whole-file ownership, and
the same file may carry different selections for different decisions.

Worked examples:

- an ordinary established `.mjs` language question → `selected`;
- a bounded ECMAScript decision in a standalone JavaScript configuration module
  whose file is project-configuration-owned → `selected`;
- a JavaScript region embedded in an Astro host → `embedded-route`;
- a Node filesystem question → `route-to-owner`;
- a TypeScript or JSX source question → `non-trigger` or `route-to-owner`
  according to the exact decision.

<!-- clause: JS-RESPONSE -->
Response is one of exactly four values: `proceed-routine`,
`inspect-before-judgment`, `bounded-local-decision`, `stop-and-escalate`.

**Selection and Response are disjoint vocabularies.** `route-to-owner` is a
selection and is never a response. Routing never lowers a response, and a routed
stop remains stopped until its owner resolves it.

<!-- clause: JS-ROUTES -->
Routes or obligations form a small ordered set with **one item per
consequence-bearing adjacent decision**. Receiving owners are:
`project-design-owner`, `project-configuration-owner`, `node-runtime-owner`,
`browser-platform-owner`, `module-loader-owner`, `build-transform-owner`,
`host-owner`, `typescript-owner`, `jsx-owner`, `security-owner`,
`performance-owner`, `deployment-owner`.

Two distinct decisions are never collapsed because they share one owner. No
route algebra, effective-route union, or obligation-provenance structure exists;
the ordered set is the whole mechanism.

## Owner

The profile may own, for an established region with its inputs bound:

- lexical grammar and early errors;
- Script versus Module language-goal consequences, after the goal is
  established;
- strict-mode language consequences;
- lexical environments, declarations, temporal dead zones, and closures;
- expression evaluation order and completion records;
- primitive conversion, equality, and comparison semantics;
- objects, prototypes, property access, descriptors, assignment, and deletion;
- functions, parameters, ordinary `this` binding, arrow functions, closures;
- class and private-element language semantics;
- destructuring, iteration, iterator closing, spread, and rest;
- exceptions and the interaction of `return`, `throw`, and `finally`
  completions;
- Promise and async-function semantics that ECMA-262 itself defines;
- ECMAScript module declarations, live bindings, namespace objects, and cyclic
  language semantics, after host linking inputs are established;
- standard built-in semantics when the exact language edition and inputs are
  bound.

## Non-owners

<!-- clause: JS-NONTRIGGER -->

### Node.js and CLI runtime

JavaScript does not own `process`, `Buffer`, `fs`, `path`, `os`, `stream`,
`child_process`, `worker_threads`, signals, environment variables, exit codes,
Node timers, Node event-loop phases, CommonJS wrapper bindings, `require`
resolution, package exports, loader hooks, or Node security policy.

### Browser and Web platform

JavaScript does not own the DOM, Web APIs, browser events, timers, `fetch`,
storage, workers, rendering, browser module fetching, or browser compatibility
policy.

### Module loading and packages

JavaScript may own ECMAScript module binding and evaluation semantics after the
module graph and linking facts are established. It does not own specifier
resolution, package exports and imports, network fetching, filesystem lookup,
CommonJS loading, bundler graph construction, or loader configuration.

### Transformation and tooling

JavaScript does not own Babel, SWC, esbuild, Vite, or Astro transformations,
minification, bundling, source maps, lint or formatter policy, engine selection,
or build completion.

### Adjacent languages and hosts

JavaScript does not own TypeScript static analysis, JSX syntax or transform,
React component semantics, MDX or Astro whole-file semantics, CSS, HTML, or JSON
as a data format.

### Project policy

JavaScript does not decide JavaScript-versus-TypeScript migration, security
approval, architectural decomposition, performance acceptance, deployment, or
product behavior.

## Parse-goal, host-context, language-context, and evidence-state model

<!-- clause: JS-SOURCE-GOAL -->
Four independent axes exist and must never be collapsed:

| Axis | Closed values | Meaning |
| --- | --- | --- |
| parse goal | `script`, `module`, `unresolved` | ECMAScript grammar goal, or absence of established goal |
| host context | `standalone`, `commonjs-wrapper`, `host-embedded`, `host-transformed`, `none` | host or integration context |
| language contexts | a nonempty duplicate-free set drawn from `expression-region`, `global-code`, `module-body`, `function-body`, `parameter-list`, `block`, `class-body`, `module-graph`, `unknown` | every ECMAScript syntactic or evaluation context the current decision crosses |
| goal evidence state | `known`, `unresolved` | whether exact host or parser evidence establishes the goal |

Rules:

1. Module source is strict by language definition.
2. Script source may be strict or non-strict according to the exact directive
   and context.
3. Host-selected extensions and package settings are **evidence inputs**, not
   ECMAScript-standard filename rules. `.mjs`, `.cjs`, and a package `type`
   field are host and project facts whose language consequences this profile may
   consume.
4. `.cjs` is **not** a standardized ECMAScript goal. CommonJS wrapper bindings
   and behavior remain Node-owned.
5. Source text containing `import` or `export` indicates a question but does not
   replace exact host or parser evidence when classification is disputed.
6. An unresolved goal blocks goal-sensitive conclusions and nothing else.
7. `commonjs-wrapper`, `host-embedded`, and `host-transformed` are host
   contexts, never ECMAScript parse goals.
8. `function-body`, `parameter-list`, `block`, `class-body`, and
   `module-graph` are language contexts, never host contexts or parse goals.
9. Configuration-module status is an artifact role and whole-file ownership
   input, never a host context.

`.js`, `.mjs`, and `.cjs` are never flattened into one source kind.

## Strictness model

<!-- clause: JS-STRICTNESS -->
Strictness must be bound before any conclusion that depends on it, because it
changes real consequences: assignment to a non-writable property or to an
undeclared identifier, `delete` of a non-configurable property, the value of
`this` in an ordinary call, duplicate parameter names, and several early-error
conditions.

Strictness is derived from the goal and the exact directive context, not
guessed. A `module` goal implies strict; a `script` goal requires the exact
directive evidence. An unresolved strictness state blocks strictness-sensitive
conclusions only.

## Evidence model

<!-- clause: JS-EVIDENCE -->
Every material conclusion separates **present evidence** from **required
evidence**. The two sets are disjoint. One role's evidence never satisfies
another.

Present evidence may include: exact source bytes; artifact class; whole-file
owner; parse goal; strictness state; the exact ECMA-262 edition or draft
binding; host classification; package `type` or extension evidence; module graph
facts; engine identity, version, and invocation; runtime inputs; observed
output; and target pin.

Required evidence may include: a host-selected parse goal; module linking or
resolution result; Node or browser runtime state; DOM state; I/O inputs;
timer or event-loop state; engine feature support; build transformation;
security policy; and a project migration decision.

Engine and host roles are recorded per decision in exactly four closed states:

| Role state | Meaning |
| --- | --- |
| `known` | exact executable, version, selection source, and invocation evidence are bound |
| `not-selected` | the role is not selected for this decision |
| `not-required` | the conclusion does not depend on the role |
| `unresolved` | the role is consequence-bearing and unestablished |

A concrete engine, host, version, or invocation is **never** bound to a
`not-selected` or `unresolved` role. Package or lockfile presence never proves a
role runs, and a configuration option is not an invocation.

Unknown consequence-bearing evidence stops **only the dependent conclusion**,
not every conclusion about the region.

The maintained APG qualification records close only consequence-bearing
identifiers and structures: authority IDs, exact row source-binding IDs,
lifecycle states, provenance and edit-permission classes, completion states,
and row-bound owned and non-owned conclusion IDs. Fixture artifacts additionally
bind exact relative paths and content digests; target rows bind opaque exact
commitments and never contain target source. Purpose, fact, evidence, forbid,
route explanation, and conclusion-note prose is explicitly explanatory and
non-authoritative. The checker validates its structure where applicable but
does not claim that arbitrary prose wording is mechanically closed; primary
source and non-author review own semantic sufficiency.

## Bindings and scope

<!-- clause: JS-BINDINGS-SCOPE -->
The profile reasons about lexical environments and declaration instantiation
only after binding the exact global Script, Module, function body, parameter,
block, and Annex B context. In maintained function-body controls, `var` and
function declarations are instantiated before their source positions; `let`
and `const` bindings are created but uninitialized, producing a temporal dead
zone until declaration evaluation. Block-scoped environments and closures that
capture bindings rather than values are separately bounded. There is no one
universal "hoisting" result.

Whether a given hoisting or TDZ consequence is reachable depends on the parse
goal and strictness, so both are bound first.

## Evaluation order

<!-- clause: JS-EVALUATION-ORDER -->
The profile reasons about the specified evaluation order of operands and
arguments, about completion records as the mechanism that carries normal,
`break`, `continue`, `return`, and `throw` outcomes, and about the short-circuit
boundaries of `&&`, `||`, `??`, and optional chaining — including the fact that
short-circuiting suppresses evaluation of the skipped operand entirely, and that
optional chaining short-circuits the remainder of one **continuous optional
chain** rather than only the adjacent access. Grouping ends that chain. Exact
controls bind computed-key and argument suppression and preserve the reference
receiver for an optional method call.

## Coercion and equality

<!-- clause: JS-COERCION-EQUALITY -->
The profile reasons about `ToPrimitive` with its hint, `ToNumber`, `ToString`,
and the observable method calls those abstract operations may perform on an
object; and about the four distinct equality operations — strict equality,
abstract equality, `SameValue`, and `SameValueZero` — including their differing
treatment of `NaN` and of positive and negative zero.

A coercion conclusion that depends on a user-defined conversion method requires
that method's exact source as present evidence.

## Objects and prototypes

<!-- clause: JS-OBJECTS-PROTOTYPES -->
The profile reasons about object creation, prototype chains, and property
lookup, including lookup proceeding along the chain, shadowing, and the
distinction between an own property and an inherited one.

These are ordinary-object conclusions. `Proxy`, module namespace and other
exotic objects, and host exotics require their exact algorithms and stop here.

## Properties and descriptors

<!-- clause: JS-PROPERTIES -->
The profile reasons about data and accessor descriptors and their attributes;
about assignment semantics, including assignment through an inherited accessor
and assignment to a non-writable inherited data property; about `delete` and its
result; and about the strict-mode failure modes of each, which throw where
non-strict code fails silently.

`Reflect` operations and Proxy traps are separate questions; ordinary
assignment or deletion results are not promoted to them.

## Functions and this

<!-- clause: JS-FUNCTIONS-THIS -->
The profile reasons about parameter lists, default-value evaluation and its
timing, rest parameters, spread in calls and array literals, and the difference
between an ordinary function's `this` — determined by the call — and an arrow
function's lexically captured `this`.

A `this` conclusion for an ordinary function requires the call form as present
evidence; source alone does not settle it.

## Classes

<!-- clause: JS-CLASSES -->
The profile reasons about class construction order, derived-class `super`
requirements before `this` is available, instance and static field
initialization order, and private-element semantics including their brand check
and the fact that a private name is not a string-keyed property.

## Iteration and destructuring

<!-- clause: JS-ITERATION -->
The profile reasons about the iteration protocol, array destructuring, and
iterable spread; object spread instead enumerates own enumerable properties.
Iterator closing depends on the exact completion and iterator state: a missing
`return` is allowed; non-callable, throwing, or non-object-returning `return`
variants differ; a same-loop `continue` does not close; and completion
precedence can retain an original throw even when closing also throws. Never
replace these cases with a broad "early termination always calls return" rule.

## Exceptions and completions

<!-- clause: JS-ERRORS -->
The profile reasons about `throw`, `try`/`catch`/`finally`, and specifically
about how a `finally` block's own abrupt completion — a `return`, `throw`,
`break`, or `continue` inside `finally` — replaces the completion that was in
flight, including a pending exception.

## Promises and async

<!-- clause: JS-PROMISES-ASYNC -->
The profile reasons about promise reaction semantics, resolution and rejection,
`await` suspension and resumption, and error propagation out of async functions
— bounded to Jobs and requirements on host hooks such as
`HostEnqueuePromiseJob`. ECMA-262 does not define one generic
ECMAScript-owned job queue.

Ordering of language jobs relative to Node timers, Node event-loop phases, or
browser tasks is **not** owned. Such a claim routes to `node-runtime-owner` or
`browser-platform-owner` and the language response is unchanged by that routing.

## Modules and live bindings

<!-- clause: JS-MODULES -->
After the module graph and linking facts are established, the profile reasons
about import and export declarations, live bindings — an imported binding
observing a later mutation performed in the exporting module — module namespace
exotic objects and their properties, cyclic-module TDZ, and top-level-await
asynchronous module evaluation after exact linking facts are established.

Without established linking facts, a live-binding or namespace conclusion is
`inspect-before-judgment`, and `stop-and-escalate` when a resolution or loading
result would otherwise be asserted.

## Dynamic import and loader boundary

An `import()` expression is a language construct. Its **resolution and loading**
are not language semantics: specifier resolution, package exports and imports,
filesystem lookup, network fetching, and loader configuration route to
`module-loader-owner`.

The profile may state that `import()` produces a promise, that successful host
loading and evaluation fulfills it with a namespace object, and that failure
rejects it. It may not state which module that specifier resolves to, whether
the load succeeds, or when it completes relative to host work.

## The `.js`, `.mjs`, and `.cjs` host boundary

These are **host and project classifications**, consumed as evidence:

| Artifact | Host classification | ECMAScript consequence |
| --- | --- | --- |
| `.mjs` | host-selected module file | `module` goal; strict by definition |
| `.cjs` | host-selected CommonJS file | **not** a standardized ECMAScript goal; wrapper bindings and behavior are Node-owned |
| `.js` | depends on the nearest package `type` and host configuration | `module` or `script` according to that exact evidence; `unresolved` without it |

Recording an extension classification and recording its ECMAScript consequence
are two separate acts, and the second requires the first as evidence.

## Checked JavaScript

<!-- clause: JS-CHECKED-JS -->
Checked JavaScript is JavaScript for which a `// @ts-check` comment, project
`checkJs` setting, or equivalent requests or selects checking. That source or
configuration fact is not evidence that any checker was invoked.

Checked status does not choose the whole-file owner. An ordinary checked source
may remain JavaScript-owned. A standalone JavaScript configuration module may
remain project-configuration-owned while JavaScript is `selected` for its
bounded ECMAScript decision. TypeScript participates separately for the checking
decision only when exact compiler, configuration, inclusion, checker invocation,
and diagnostic evidence exists. It neither transfers the file nor settles an
ECMAScript, configuration, loader, build, or deployment question.

The reverse also holds — an ECMAScript semantic conclusion about the file does
not settle a TypeScript checking question.

## Host-embedded regions

A JavaScript region inside an Astro, MDX, HTML, or comparable host file uses
`embedded-route`. The host owner keeps the file and owns extraction, processing,
transformation, and whether the region runs at all.

The profile may reason about the region's language semantics once its exact
bytes, goal, and strictness are established. It may not infer a browser context,
a module goal, or an execution occasion from the host file type.

## Pure CLI core versus Node adapter

<!-- clause: JS-CLI-BOUNDARY -->
A JavaScript CLI utility separates two things:

- an **effect-free ECMAScript computation** that receives argument and
  environment values as ordinary data, transforms them, and returns a
  structured result including any message data without calling an injected
  writer — this may be language-owned; and
- a **Node adapter and I/O shell** covering `process.argv`, `process.env`,
  stdout and stderr, the filesystem, the network, signal handling, and exit
  status — every decision here routes to `node-runtime-owner`.

A correct core result is not a working command. This separation is the shape the
product orientation implies, and it is the reason a short JavaScript utility can
have a language-owned centre without JavaScript owning Node.js.

## Implementation-evidence boundary

<!-- clause: JS-STATIC-HOST-COMPLETION -->
Four layers stay separate: syntax and early errors; ECMAScript evaluation
semantics; host and runtime integration; and external operational effect.

- A parser pass proves only that exact parser's result.
- One engine run proves only that observed engine result, under that exact
  command, version, mode, and input.
- Every maintained semantic and syntax-check subprocess uses one repository
  invocation owner that validates the approved direct executable immediately
  before invocation, executes through that exact resolved path, revalidates the
  path, metadata, digest, and public identity immediately after invocation, and
  returns the subprocess result with the bounded binding used. This is pre/post
  identity evidence, not a claim of continuous identity during execution.
- An implementation's behavior is **observation**, not normative authority.
- A TC39 proposal is not current ECMAScript semantics merely because an engine
  implements it.
- Language success never proves build, module loading, I/O, user-visible,
  deployment, or security completion.

The normative authority is the completed annual ECMA-262 edition. A living draft
is used only when the candidate or target materially depends on a newer
incorporated semantic, and that dependence is then labelled exactly.

## Unknown-state rules

<!-- clause: JS-UNKNOWN-STOP -->

| Condition | Response |
| --- | --- |
| missing artifact class or whole-file owner | `inspect-before-judgment` |
| unresolved parse goal, result is goal-sensitive | `stop-and-escalate`, dependent conclusion only |
| unresolved strictness, result is strictness-sensitive | `stop-and-escalate`, dependent conclusion only |
| missing exact edition or draft for a version-dependent result | `stop-and-escalate` |
| unresolved engine or host role the result depends on | `stop-and-escalate` |
| module conclusion without established linking facts | `inspect-before-judgment`, or `stop-and-escalate` if a resolution or loading result would be asserted |
| language success offered as host, I/O, build, or deployment completion | `stop-and-escalate` |
| Node, browser, loader, build, TypeScript, JSX, security, or product question | selection `route-to-owner`; response unchanged by the routing |
| established language question, complete inputs | `proceed-routine` |

## Structural-policy deferral

<!-- clause: JS-STRUCTURE-DEFERRED -->
**JavaScript structural policy is deferred.** This is a decision, not an
omission.

Forbidden: line-count bands; statement-count bands; function-count thresholds;
cyclomatic-complexity thresholds as automatic language selection; percentile
thresholds; accumulation scores; automatic refactoring; automatic
JavaScript-to-TypeScript migration; automatic Node package conversion.

The product orientation — JavaScript preferred for short, simple user scripts
and CLI utility cores, TypeScript preferred for larger or more complicated
utilities — is recorded project context. It is **not** a language-profile
trigger and carries no numeric threshold. The profile states, normatively:

- an established JavaScript source question is analyzed as JavaScript;
- no line count, function count, cyclomatic score, file count, or repository
  size automatically selects TypeScript;
- no static or runtime finding automatically orders migration;
- migration may be recommended only by a separately authorized project-design
  decision with exact evidence.

Qualitative observations — host and language concerns entangled, implicit
mutable shared state, unclear module boundary, unbounded side effects, complex
error propagation, or runtime-dependent behavior hidden in a pure-looking core —
may route review to `project-design-owner`. They never decide failure and never
order migration.

The deferral is also evidence-grounded: across both freshly pinned targets there
is exactly one whole-file JavaScript artifact and two host-embedded regions.
That is not a population from which any numeric policy could be calibrated.

## Provenance and rollback

Authored JavaScript may be edited under this profile once its owner and
permission are bound. A read-only language conclusion over generated, bundled,
minified, or vendor bytes may still be selected when the exact bytes and the
governing edition are known — but that diagnosis grants no edit permission.
Generated and bundled output is regenerated under an evidenced build role;
vendor JavaScript remains third-party input; provenance owners decide every
change. Unknown provenance blocks edits and regeneration claims, not a safely
bounded read-only observation.

Before a material repair, record what rollback needs: the exact prior source
bytes, the parse goal and strictness the conclusion rested on, the artifact
class and provenance, and the engine and host evidence.

## Completion criteria

A JavaScript-owned conclusion is complete when the artifact class, whole-file
owner, and selection state are recorded; the parse goal and strictness are
bound; the governing edition is named; every consequence-bearing engine and host
role carries a role state; present and required evidence are listed and
disjoint; the response is stated; each route names its receiving owner; and the
rollback boundary is recorded.

Never claim completion while required evidence is missing, while a routed stop
is unresolved, or in terms that let a language result stand in for a host or
operational one.

## Refresh conditions

Refresh this specification when: ECMA-262 publishes a new completed annual
edition or a consequence-bearing corrigendum; a target's JavaScript-bearing
inventory materially changes; a Node runtime or browser-platform owner is
established, which would move currently routed decisions to a real receiver; the
TypeScript profile's `embedded-route` analysis changes shape; or the
project-design owner issues a structural or migration policy, which would end
the deferral.

## Known limitations

1. **APG79B remains repair-required.** Its immutable correction attempted only
   the five retained Medium contract and harness defects. Fresh review found
   four unique Medium defects in CommonJS invariants, traceback privacy, static
   alias enforcement, and root-scalar output mutations. Integration evidence
   does not exist and no debt is accepted.
2. **Target dogfood is thin.** One checked `.mjs` configuration module and two
   host-embedded browser regions across both pinned targets. Neither `.js` goal
   resolution nor `.cjs`/CommonJS boundaries are exercised by any target; both
   are carried entirely by the APG-owned fixture.
3. **Several receiving owners do not exist yet.** `node-runtime-owner`,
   `browser-platform-owner`, `module-loader-owner`, and `jsx-owner` are named
   destinations without current profiles. A route to them is currently a stop
   with a named addressee, not a handoff to a live owner.
4. **Coverage is deliberately partial and operationally stopped.** `Proxy`,
   `Reflect`, the memory model, `SharedArrayBuffer` and shared memory,
   `Intl`/ECMA-402, regular expression semantics, and unlisted built-ins require
   a separate exact source-backed decision. No broad trigger implies their
   coverage.
5. **The living draft is unused.** No clause binds to the moving ECMA-262 draft.
   If a future candidate question needs a post-2026 incorporated semantic, that
   dependence must be labelled exactly rather than assumed.
6. **Source and rights are current.** APG79 directly refreshed the annual
   publication, repository licence, software/text policy, errata, moving draft,
   and Test262 licence. No external expression was copied, and Test262 remains
   non-normative and unused as an oracle.

## APG79A boundary

APG79 independently reconstructed all twenty-four navigation scenarios and all
fourteen fixture cases, preserved three correction rounds, and terminally left
ADR 0045 Proposed at a repair checkpoint. APG79A preserves that history and
corrects only H1, H2, M1, and M2 under explicit human continuation authority.

APG79A owns maintained failing-first tests and exact engine-backed tests only
where they prove a bounded implementation fact. Its three default correction
rounds remain immutable; this one correction is `repair-required-after-apg79a`.

Four fresh lanes found five Medium defects: CommonJS Selection contradicts the
nested-host-only `embedded-route` definition; a target-only commitment field is
accepted on non-target rows; actual pytest diagnostics can reflect engine
streams; wrapper-bypass enforcement misses common aliases; and required
path/output mutation evidence is incomplete. No finding is accepted as debt and
APG79A has no post-review correction authority.

APG79B exercises a separate human continuation decision for exactly those five
findings. Standalone CommonJS artifacts remain Node-owned while using
decision-scoped `selected`; target commitments are target-row-only; raw engine
streams remain local to one invocation owner; maintained static process forms
are AST-checked; and actual post-run path replacement plus closed per-field
output mutations are rejecting controls. The correction is
`repair-required-after-apg79b`; it does not itself integrate the profile or
decide ADR 0045.

Fresh APG79B review found that those controls are incomplete: both CommonJS
stop vectors are not fully frozen; raw streams remain reachable through
traceback locals and exception context; annotated aliases and module rebinding
bypass the AST gate; and four root-scalar contracts lack same-type wrong-value
mutations. The unique result is 0 Critical, 0 High, 4 Medium, and 0 Low. APG79B
permits no second correction and APG80 is not recommended.

A fresh repairable material defect found by APG79 is **repair-required**, not
automatic rejection. Zero Critical and zero High findings are required before
integration; any remaining Medium or Low debt requires explicit human
acceptance. `CSS-QD-001` through `CSS-QD-005` are preserved unchanged
throughout.

APG78 grants APG79 no authority. No Node profile, JSX, React, MDX,
Astro-language, or stable-maturity work is authorized by this document.

## APG79C human debt and blocked preflight

`JS-QD-001` through `JS-QD-004` are human-accepted Medium qualification debt
for provisional use only. Qualification machinery remains supporting rather
than sufficient semantic or source authority. CommonJS questions retain their
Node-owned stop, harness inputs remain APG-owned and non-sensitive, process
changes require human diff review, and root-scalar changes require source-backed
non-author review. The current source-identity discrepancy is not accepted
debt. Integration did not open, stable maturity remains blocked, ADR 0045 stays
Proposed, and the lifecycle remains `repair-required-after-apg79b`.

## APG79D Test262 source-role correction

Test262 is non-normative rights-only evidence. ECMA-262 remains normative
authority; Test262 is neither a semantic or compatibility oracle nor an
implementation authority. The APG79 reviewed pin is immutable historical
evidence, while a fresh default-branch head and tree are separately observed
mutable freshness evidence. Head equality is not required.

No Test262 test body is read for expected behavior, copied, executed, vendored,
or retained as a path inventory. Ordinary upstream-head drift is therefore not
semantic, target, engine, release, or product drift when the exact licence
object and no-corpus role remain unchanged. A licence-object or rights-role
change, copied external expression, or any corpus use blocks for fresh review.
The false APG79B object assertion remains in its immutable historical report;
APG79D supersedes it as current authority and does not classify it as debt.
Fresh immutable correction review returned zero unaccepted findings, but
terminal integration review found the maintained report-binding limitation.
APG79D therefore left ADR 0045 Proposed and JavaScript unintegrated.

## APG79E report-binding debt and integration

`JS-QD-005` records that the maintained proxy does not directly bind the APG79B
managed-report path, record identities, or full-file digest. APG79E accepts this
exact Medium supporting qualification limitation under explicit human
authority and directly verifies the current report through EOF, regenerated
Git-show payloads, operational associations, and full-file digest. The report
remains immutable historical evidence rather than semantic or product
authority, and the maintained proxy is not claimed repaired.

With zero Critical, High, or unaccepted Medium/Low findings and all ordinary
product gates green, ADR 0045 is Accepted with amendment and JavaScript is
`provisionally-integrated-with-known-debt`. Test262 remains non-normative
rights-only evidence, structural policy remains deferred, and stable maturity
is blocked by `JS-QD-001` through `JS-QD-005`.
