# JavaScript Language-Profile Architecture

- Phase: APG67 proposal corrected and terminally reviewed by APG68
- Status: Rejected under ADR 0039 after fresh APG68 review; historical
  corrected-proposal evidence only; no candidate-authoring authority
- Decision record: [ADR 0039](../adr/2026/08/0039-javascript-language-profile-architecture-and-lean-validation.md)

## Purpose

This architecture answers whether a reusable `javascript-language-profile`
owns one coherent problem, which exact ECMAScript source is the stable
reference, how actual parser/runtime configuration relates to that
reference, where JavaScript ends and TypeScript, Node.js, browser/DOM, JSX,
host, module-resolution, toolchain, and security owners begin, how
JavaScript structure should be governed, and what lean candidate-independent
contract a later authoring phase must answer to. APG67 authors no skill and
integrates nothing. The Markdown candidate remains retained provisional
under ADR 0037 and ADR 0038; the CSS rejections recorded by ADR 0031, 0034,
0035, and 0036 remain terminal and are not reopened.

## Sources, versions, and rights

- ECMA-262, 17th edition — ECMAScript 2026 — is the stable annual
  reference. The Ecma publication page states "ECMAScript® 2026 language
  specification, 17th edition, June 2026" with the HTML version normative
  and the PDF derived. The fixed annual HTML snapshot is published under
  the tc39.es ecma262 2026 path.
- The exact annual repository source is the `es2026` tag of the tc39
  ecma262 repository. The tagged source self-describes as the seventeenth
  edition and titles itself "ECMAScript® 2026 Language Specification"; its
  ecmarkup metadata carries `status: draft` as a repository-source
  convention, because the repository holds the processed source while the
  annual render is the published form. Its tag object is
  `f7db29f16c5175a93f0d6e8fb27a8e3cb9b97a9e`, its commit is
  `0248456c758431e4bb8e5d26333ff1865123c9cd`, and its tree is
  `02137fef007dced3167756ba3dbd3e11306ad4bf`.
- The editor-signed `es2026-errata` tag object
  `5ebd9700730a7d3b833af8f10793d76443803c0c` resolves to commit
  `d89c03f2db8a597bc915b363a6518d0cc8acdbc0` and tree
  `9e4b9d538cef2863b67bef26d7b414f9a3384ca6`. Its sole change adds the
  omitted, non-normative ES2026 feature-summary paragraph to the
  introduction. The official annual HTML remains the normative semantic
  baseline; this exact errata is a non-semantic source-correspondence
  overlay. Every later candidate refresh compares the latest annual errata.
  A consequence-bearing corrigendum stops for explicit dual-source
  disposition; it never silently rewrites the annual rule.
- The live tc39 ecma262 `main` document has advanced past the annual tag
  and is the ECMAScript 2027 draft. It is moving-draft refresh evidence,
  useful for detecting post-annual drift, and has no stable architecture
  authority. A project may adopt a later implemented feature only through
  version-bound runtime, parser, or tool evidence, never by citing the
  draft as if it were the selected baseline.
- Rights are separated rather than collapsed. At the source repository,
  natural-language
  specification text is under the Ecma text copyright policy's alternative
  copyright notice; source code is under Ecma's MIT-style software
  submission, inclusion, and licensing policy; contributions require the
  TC39 contributor form or Ecma member representation. The exact annual
  publication separately carries its alternative text notice and BSD
  conditions for embedded software or pseudocode. The exact annual
  snapshot's notices were verified rather than assumed from the current
  repository head.
- Test262, the official conformance suite, is bounded validation and
  corpus evidence only. Its verified LICENSE is the Ecma BSD-style license
  (Copyright 2012 Ecma International), not CC0; the assignment's expected
  CC0 orientation did not survive exact verification and the verified
  terms are recorded instead. Test262 tracks the living specification and
  staged proposals continuously and is not tagged per annual edition; it
  never becomes the normative language authority, and no test, expected
  value, harness code, prose, or algorithm is copied from it.
- No copied or adapted specification, algorithm, grammar production,
  table, example, test, implementation, or target expression was
  identified in APG67. This is a bounded factual and clean-room
  conclusion, not a universal legal guarantee.
- Exact tag, commit, tree, and license-object identities remain in the
  publication-excluded evidence bundle. APG68 independently fetched the
  primary objects and closed APG67's honestly recorded tree-hash limitation.

## Target and corpus evidence

The two pinned read-only targets were verified at their exact commits and
trees and were not installed, built, tested, linted, previewed, or
executed. Their complete tracked JavaScript-family inventory is:

- Website: exactly one primary JavaScript-family path, a handwritten
  ESM configuration module of roughly thirty-four lines that configures
  the Astro/Starlight integration set. Its package manifest declares
  `"type": "module"`, and the `.mjs` extension makes the Module parse goal
  explicit. It is real semantic dogfood: it controls integrations and
  deployment-facing build behavior, and its import-specifier resolution is
  host/tool-owned while its syntax and bindings are ECMAScript. The
  remaining inventory is one TypeScript content-configuration module, two
  MDX documents, two Markdown documents, JSON and lockfile configuration,
  and one CI workflow. No `.js`, `.cjs`, `.jsx`, `.tsx`, `.astro`, or
  inline-script HTML template exists at the pinned tree.
- Theme: zero primary JavaScript-family paths among 76 tracked paths.
  Adjacent evidence is four TypeScript modules (two Astro configs, one
  build script, one package entry), one handwritten declaration file, and
  five Astro components. Four Astro files have substantive TypeScript
  frontmatter; `ProgressScroll.astro` has empty frontmatter. Both
  `ProgressScroll.astro` and `ThemeSelect.astro` contain embedded client
  scripts while remaining Astro/host-owned whole files. MDX/Markdown
  documentation, a Python brand CLI, twelve CSS files, and JSON/YAML
  configuration remain adjacent evidence.

Whole-file JavaScript dogfood at the pinned targets is therefore a single
small configuration module. Browser scripts, CommonJS artifacts, Node CLIs,
generated bundles, and minified or vendored JavaScript are absent from the
targets, so target evidence alone cannot calibrate those classes and no
numeric structural claim may be target-calibrated.

The APG52 compact corpus supplies descriptive breadth only: 1,892
JavaScript modules across six families, three hundred-plus Node runtime/CLI
artifacts, and parallel TypeScript, declaration, configuration, JSX/TSX,
MDX, and Astro classes. The exact 4,365 observed exclusions are 3,742
fixture/demo, 507 unrelated path/type, 44 build output, 31 vendored, 28
snapshot, 11 symlink, and 2 minified; generated and lockfile exclusions
remain rules with zero observed rows. CommonJS has no separate corpus class,
but two measured `.cjs` files are classified as JavaScript modules. The
corpus is family-imbalanced (React supplies most JavaScript), which
independently prevents treating artifact-weighted values as universal
policy; no corpus percentile becomes policy.

## Owner

A reusable `javascript-language-profile` owns one coherent problem:
ECMAScript language semantics after the effective source-text goal and
implementation context are established. Within that boundary it owns:

- lexical grammar and syntax, including hashbang comments, which the
  selected annual grammar recognizes;
- Script and Module source-text semantics once the goal is established;
- strict-mode language effects;
- declarations, bindings, scope, closures, and evaluation order;
- expressions, statements, completion, and exception semantics;
- ECMAScript language types, coercion, and equality/relational semantics;
- objects, properties, descriptors, prototypes, and classes, including
  private names and class elements;
- functions, calls, construction, `this`, and arrow lexical capture;
- iteration and async iteration protocols, generators, and async
  generators;
- Promise semantics and ECMAScript job semantics (not host scheduling);
- language-level module linking and evaluation semantics, the dynamic
  import expression after host resolution input, and the `import.meta`
  syntactic boundary;
- RegExp grammar and ECMAScript RegExp semantics as version-bound facts;
- the standard built-ins ECMA-262 defines, as specification semantics —
  implementation conformance is never asserted from source-syntax
  resemblance;
- Proxy and Reflect semantics, including essential internal-method
  invariants;
- WeakRef and FinalizationRegistry with their specified nondeterminism
  preserved — the profile never promises collection or cleanup timing;
- SharedArrayBuffer and Atomics language and memory-model semantics
  (agent/worker creation stays host-owned);
- `JSON.parse` and `JSON.stringify` as ECMAScript built-ins (JSON
  documents and schemas stay data-language-owned);
- Annex B and normative-optional behavior only when the selected
  implementation context establishes applicability.

Partial-ownership boundaries recur deliberately: jobs versus host task
ordering, module semantics versus host resolution, `import.meta` syntax
versus host-supplied values, built-in specification semantics versus
implementation conformance, and memory-model semantics versus worker
creation. Each pairs one owned language fact with one routed owner fact.

## Non-owners

- TypeScript owns TypeScript-only syntax, static type semantics, erasure
  and emit, compiler options, declaration files, type acquisition, and
  `.ts`/`.tsx` whole-file decisions. JavaScript may own a bounded
  runtime-semantics question about emitted or embedded JavaScript only
  after the TypeScript/tool owner establishes the relevant bytes and
  source map. No file-size threshold mandates TypeScript.
- Node.js owns runtime version and flags, CommonJS, `require`, the module
  wrapper, package `type`/`exports`/`imports`, file-extension module
  selection, ESM resolution and loading, loaders and hooks, `process`,
  filesystem, streams, Node buffers, environment variables, signals,
  child processes, CLI behavior, shebang execution, and user-script
  installation and invocation. ECMAScript module syntax and evaluation
  remain distinguishable from Node's resolution and loading policy, and
  CommonJS is not ECMA-262 module semantics.
- Browser/platform owners own Window and global-environment integration,
  the DOM, events, timers, fetch and Web APIs, Web-standard URL APIs,
  workers, storage, navigation, CSP, HTML script-element behavior, and
  classic-versus-module script selection. ECMAScript owns only the
  language consequences after the host establishes the source-text goal
  and host hooks. Browser and DOM APIs are not ECMAScript built-ins.
- JSX owns JSX syntax and transformation. A `.jsx` file is not an
  ordinary whole-file JavaScript trigger merely because its expressions
  contain JavaScript.
- Astro, MDX, and HTML hosts retain whole-file ownership of their
  artifacts; JavaScript may participate as a bounded embedded route.
- ECMA-402 is a separate standards owner. The boundary is three-way:
  ECMA-262 language and built-in semantics; ECMA-402 Intl behavior; and
  host locale and data availability. Intl outcomes are never asserted
  from ECMA-262 alone.
- `runtime-implementation-owner` supplies exact non-Node engine version,
  Unicode-data, implementation-divergence, and observed-runtime facts.
  `parser-tool-owner` is limited to parser, transpiler, and source-transform
  facts. `build-tool-owner` owns generator, bundler, minifier, and produced
  output facts. Formatter, linter, test-runner, package-manager, and build
  selection remain `project-policy`; Node package resolution remains
  `node-runtime-owner`. None becomes JavaScript-language ownership.
- Security acceptance and project permission route to their owners: the
  profile may explain mechanisms such as `eval`, `Function` construction,
  prototype mutation, coercion, property lookup, dynamic import, Proxy,
  and regular-expression behavior without accepting the risk decision.
- Prose quality, product policy, deployment, and stricter repository
  rules remain outside JavaScript ownership; repository policy always
  controls.

## Source authority and observed behavior

One universal precedence order cannot answer different questions. APG68
therefore binds each question to its consequence-bearing authority:

1. **Normative ECMAScript semantics:** the official ECMA-262 2026 annual
   HTML answers the language rule it covers. The reviewed non-semantic
   errata overlay corrects source correspondence without changing that rule.
2. **Source-goal and host selection:** exact extension, package, HTML,
   loader, or tool configuration establishes whether concrete bytes are
   Script, Module, CommonJS, JSX, TypeScript, or an embedded region.
3. **Feature availability:** the exact parser, runtime, and transpiler
   versions, flags, enabled syntax, and emitted bytes establish whether the
   project can use a feature.
4. **Observed behavior:** the selected runtime and host establish what the
   concrete pipeline actually does. Observation is not a normative rewrite.
5. **Implementation divergence:** a difference from the annual rule is a
   version-bound conformance or compatibility fact owned by the runtime or
   tool owner; it never becomes JavaScript-language semantics.
6. **Project support and permission:** project, repository, and security
   policy decide support ceilings, risk acceptance, and deployment use.

Annex B and normative-optional behavior apply only when the established
context makes them applicable. Implementation-defined,
implementation-approximated, and host-defined behavior requires
version-bound owner evidence. Later drafts and proposals remain moving
refresh evidence with no authority unless explicitly selected and evidenced
as implemented. Syntax accepted by a parser, syntax emitted by a
transpiler, semantics supplied by a runtime, semantics supplied by a host,
and project compatibility policy remain distinct. A passing parse never
proves conformant evaluation.

## Source-text goals and module boundaries

- **Script versus Module:** ECMAScript owns the language distinction once
  the parse goal is established; the host or tool owner establishes how a
  concrete artifact receives its goal (extension policy, package `type`,
  script-element type, tool configuration).
- **Static imports and exports:** JavaScript owns syntax, bindings,
  live-binding semantics, module-namespace semantics, and the
  language-level linking and evaluation model. Host, runtime, and tool
  owners own specifier interpretation, URL or package resolution,
  fetching and loading, extension policy, package conditions, loader
  hooks, and network or filesystem access.
- **Dynamic import:** JavaScript owns the expression and its
  Promise-facing language behavior; host resolution and loading remain
  routed.
- **import.meta:** JavaScript owns the syntactic and language boundary;
  the host owns supplied properties and values.
- **CommonJS:** CommonJS is not ECMA-262 module semantics. A `.cjs` or
  `require` decision routes to Node/runtime ownership while bounded
  ECMAScript expression semantics still participate as an embedded route.
- **Hashbang:** the selected annual grammar recognizes hashbang comments
  as language syntax; execution, interpreter selection, and CLI
  installation remain host and Node facts.
- **JSX, TypeScript, embedded, generated:** JSX and TypeScript are
  whole-file non-triggers; embedded JavaScript in Astro, MDX, or HTML
  retains host whole-file ownership with a bounded embedded route; and
  generated, bundled, minified, or vendored JavaScript is classified
  before any structural judgment.

## Runtime and asynchronous boundaries

ECMAScript defines Promise reaction jobs and job ordering constraints;
hosts define task and event-loop integration. Timers, I/O completion,
browser event dispatch, Node event-loop phases, and worker or thread
creation are host facts. The colloquial word "microtask" never collapses
into one universal host model. WeakRef and FinalizationRegistry keep their
specified nondeterminism: garbage collection and finalization timing are
never promised. SharedArrayBuffer and Atomics memory-model semantics are
language-owned; agent creation and host process lifetime are not.

## Semantic-risk model

Semantic risk is independent of physical size: a tiny script may be
semantic Red, and a large cohesive module may remain routine when no risk
or structural signal fires. No numeric risk score exists. The closed
semantic-signal vocabulary in the lean contract covers: source-goal
mismatch; strict-mode mismatch; unsupported or divergent syntax (including
runtime-version mismatch and transpiler/runtime divergence); coercion or
equality ambiguity; property-model surprise (descriptor and
prototype-chain behavior); the prototype-pollution mechanism; binding and
capture mismatch (`this`, arrow capture, closure capture and mutation);
evaluation-order side effects; iterator or generator protocol violation;
async propagation risk (Promise rejection paths and host-event-loop
assumptions); module-semantics misunderstanding (live bindings, cycles,
CommonJS/ESM boundary, dynamic-import and `import.meta` host assumptions);
RegExp or Unicode-version mismatch; Proxy invariant violation;
finalization-timing claims; shared-memory ordering assumptions;
dynamic-code policy; and false runtime validation. The profile uses the
shared warning contract's Green/Yellow/Orange/Red levels exactly as the
accepted language-profile contract defines them; the highest justified
level controls, and no semantic issue is forced into a structural level.

## Structural-policy disposition

APG67 selected and APG68's fresh review independently supports, as
historical evidence only, disposition C: a qualitative
responsibility-and-complexity-first policy with no numeric whole-file
bands. APG67's historical digest did not have a durable committed preimage.
APG68 therefore commits the exact sixteen-control canonical preimage in the
lean contract, records its provenance and SHA-256, and uses those immutable
bytes to constrain every application of the policy.

- One numeric whole-file policy (A) fails its own allowance conditions:
  the pinned targets provide one thirty-four-line calibration point, the
  corpus is family-imbalanced and purpose-heterogeneous, percentile
  derivation is forbidden, and the numeric values rejected with APG50 and
  APG57 may not be inherited. Any values would be invented.
- Split numeric policies (B) fail because, although generated, minified,
  vendored, and configuration classes are deterministic before size
  inspection, no per-class numeric value has an independent evidence base
  at the pinned targets, and inventing classes to reach preferred values
  is the exact failure this phase must avoid.
- Deferral (D) is unnecessary because C is complete and testable now.

Under C, each named signal has a frozen evidence class (mechanically
observable, bounded reviewer judgment, or project input), observable
evidence with a decision scope, a default response and receiving route, and
a false-positive control:

| Signal token | Evidence class | Observable evidence and decision scope | Default response and route | False-positive control |
| --- | --- | --- | --- | --- |
| `multiple-runtime-responsibilities` | project input plus bounded reviewer judgment | one changed module serves named coequal CLI, library, and build/tool duties | `bounded-local-decision`; `project-design` chooses the split | one entry point delegating to one library responsibility does not fire |
| `host-language-responsibility-mixing` | bounded reviewer judgment | named owners cannot review interleaved host-API orchestration and language-pure transformation as one responsibility | `bounded-local-decision`; route the seam to `project-design` | host calls serving one cohesive purpose do not fire |
| `module-resolution-language-mixing` | bounded reviewer judgment | the changed code treats specifier-resolution or loading policy as portable language behavior | `inspect-before-judgment`; `project-design` separates the structural seam while a concrete scenario routes semantics to its exact host owner | using resolved imports without depending on resolution policy does not fire |
| `side-effect-and-pure-transform-mixing` | mechanically observable plus bounded reviewer judgment | located import-time side effects interleave with pure computation in the changed scope | `bounded-local-decision`; `project-design` accepts an extraction seam | a module whose single purpose is its side effect does not fire |
| `implicit-shared-state` | bounded reviewer judgment | located module-scope mutable state is shared across named consumers without an owning contract | `bounded-local-decision`; `project-design` assigns the owner | module-scope constants and single-consumer caches do not fire |
| `mutation-and-aliasing-pressure` | bounded reviewer judgment | the changed scope mutates arguments or aliased structures that named callers still observe | `bounded-local-decision`; `project-design` chooses copy or contract | documented in-place mutation as the function's purpose does not fire |
| `async-control-flow-fanout` | bounded reviewer judgment | named reviewers cannot trace completion and rejection paths of interleaved async chains in the changed scope | `bounded-local-decision`; `project-design` chooses the flow shape | sequential awaited steps with one rejection path do not fire |
| `error-contract-scattering` | bounded reviewer judgment | one changed API surface mixes throw, rejection, and sentinel-return styles without a stated contract | `bounded-local-decision`; `project-design` states the contract | boundary translation between styles at one seam does not fire |
| `data-shape-contract-pressure` | project input | named growing public data shapes or cross-module invariants exceed what untyped review can hold | `bounded-local-decision`; `project-design` decides the TypeScript route with `typescript-owner` as the named competence | local object literals with one consumer do not fire |
| `dynamic-code-generation` | mechanically observable | `eval`, `Function` construction, or equivalent dynamic evaluation appears in the changed scope | `inspect-before-judgment`; route acceptance to `security-owner`; an explicit policy makes the stop exact | data-only dynamic property access does not fire |
| `prototype-or-metaobject-complexity` | mechanically observable plus bounded reviewer judgment | prototype mutation, descriptor manipulation, or Proxy trap logic concentrates in the changed scope | `inspect-before-judgment`; containment seam to `project-design` | ordinary class declarations and frozen objects do not fire |
| `compatibility-branching` | mechanically observable | runtime- or feature-detection branches multiply in the changed scope | `inspect-before-judgment`; route the support matrix to `project-policy` | one guarded fallback with evidenced support policy does not fire |
| `generated-manual-mixing` | project input plus mechanically observable edit | generator ownership and a located hand edit inside a generated, bundled, or minified artifact are both evidenced | `stop-and-escalate`; `repository-policy` controls direct-edit permission and `build-tool-owner` supplies the regeneration path | a generated file with no hand edit is classified, not escalated |
| `test-seam-absence` | bounded reviewer judgment | changed behavior has no named executable observation seam and reviewers cannot state how it would be observed | `bounded-local-decision`; `project-design` chooses the seam | small declarative configuration modules do not fire |
| `whole-module-review-boundary` | bounded reviewer judgment | despite navigation, named maintainers cannot review the proposed change against one coherent whole-module responsibility | `bounded-local-decision`; `project-design` chooses partition or an accepted bounded exception | length, export count, or reviewer preference alone does not fire |

The suggested `javascript-typescript-boundary-pressure` signal was
evaluated and merged into `data-shape-contract-pressure`, which is the one
JavaScript-to-TypeScript pressure signal. For every signal the decision
scope is the current proposed growth or edit, never a retrospective file
score. Co-firing precedence is exact: semantic Red or an explicit policy
stop controls first; otherwise the highest response severity controls;
routing is simultaneous and never lowers severity; signals at one severity
do not aggregate into a score. Legacy JavaScript applies purpose control
16: smallest-safe change and evidenced bounded exceptions, never automatic
broad rewrite. Line count is descriptive inspection input only: it may
prompt a named signal review but cannot fire a signal or select an
architecture by itself.

## Project-owned parameters

Projects own: the actual runtime, parser, and transpiler selection and
versions; compatibility policy; module and package layout; dynamic-code
and security policy ceilings (with `repository-policy` always
controlling); tool selection; and the JavaScript-versus-TypeScript
division. The user's stated division — JavaScript for short, comparatively
simple utilities; TypeScript for larger or contract-heavy utilities;
Node.js concerns for user scripts, CLI utilities, and runtime, module,
process, and filesystem matters — is incorporated as project input, not as
a numeric language law. It translates into project-owned evidence such as
public data-shape contracts, cross-module invariants, refactoring
pressure, independently evolving consumers, discriminated states, and
deployment or maintenance constraints. "Large" is never defined by an
invented line threshold, and the profile identifies pressure and routes to
`project-design` and `typescript-owner`; it never decides migration.

## Lean validation model

The candidate-independent contract is a scenario and invariant register,
deliberately not an exact-action map. Thirty-eight candidate-semantic
scenarios (APG67-JS-001 through APG67-JS-038) each carry one public-safe
input, source-goal and host facts, one primary consequence-bearing
decision, one exact owner, selection state, response severity, one exact
route, explicit non-owners, closed structural and semantic signals, a
required invariant, a forbidden outcome, one exact rollback class, and one
exact source-boundary class. APG67-JS-039 and 040 are separately typed
review-process invariants owned by `generic-lifecycle`; a future
JavaScript candidate does not satisfy or explain them. Exactness is
tiered exactly as the lean contract states. `NonOwners` is scoped only to
the primary Decision/Owner tuple; it never contradicts ownership of a
separately named routed consequence. The contract independently owns exact
ordered structural and semantic token arrays and its inherited
evidence rules forbid the automated-evidence overclaims corrected in the
Markdown line.

## Corrected-state evidence

APG68 collected the complete initial material set, applied one coherent
source-authority, vocabulary, routing, scenario, and evidence-truth
correction, and preserved the corrected artifact hashes and exact full-index
patch before fresh review. The publication-excluded APG68 evidence binds the
reviewers to those hashes. A genuinely new material defect after this sole
correction requires rejection; the original APG67 object remains immutable.

## Rejected authoring state

APG68 result: `not-applicable-rejected`. The corrected proposal is not a
current architecture input and grants no candidate-authoring eligibility.
The following proposed narrowings remain historical review evidence only:

1. question-specific authority: normative semantics come from the annual
   standard, while goal, availability, observation, divergence, and policy
   use their exact owners; no conformance claim follows from syntax alone;
2. no Node, browser/DOM, or toolchain ownership; host APIs route exactly;
3. no TypeScript, JSX, or `.ts`/`.tsx`/`.jsx` whole-file selection;
4. no numeric structural bands; line count stays descriptive;
5. no automatic JavaScript-to-TypeScript migration; pressure routes to
   `project-design`;
6. no target-calibrated structural claim: target dogfood is one small
   configuration module, and corpus evidence stays descriptive;
7. Annex B and normative-optional behavior only under an established
   implementation context;
8. no promised host task ordering and no promised collection or
   finalization timing;
9. row 023 is browser-page-specific; another host requires its own exact
   owner and source evidence rather than conditional reuse; and
10. generated, bundled, minified, and vendored direct-edit permission stays
    repository-owned, with exact provenance and regeneration ownership.

Fresh review found genuinely new material defects after the sole correction:
the register underclassifies finalization-timing dependence; several rows
fire Orange structural signals while returning Yellow; the single-route
schema cannot represent the architecture's claimed simultaneous structural
and semantic routes; some fired signals violate their false-positive
controls; and several source-boundary tokens omit consequence-bearing
runtime, host, or ECMA-262 authorities. Under the one-correction rule these
defects reject the architecture rather than authorize another repair.

No APG69 authoring phase is recommended. A future architecture phase would
require new human authority and a fresh contract rather than treating these
narrowings as accepted input.

## Rollback

This architecture is independently rollback-safe: rejecting ADR 0039
removes only APG67's architecture, contract, and register surfaces while
preserving APG67 history. No maintained executable, test, catalog,
projection, route, maturity, release, target, public, or active surface
depends on it.

## Refresh conditions

Reverify before reuse when any of the following changes: a newer annual
ECMA-262 edition is approved; the annual tag, errata state, or rights
notice of the pinned source changes; Test262 rights change; the pinned
target repositories' JavaScript-family inventory or toolchain evidence
changes; or the accepted language-profile contract changes.

## Open adjacent gaps

TypeScript remains a broader multi-class problem with no architecture
phase; JSX and MDX retain evidence gaps; React and Vitest remain under ADR
0029 Policy A; Node.js as a runtime profile, browser/DOM runtime, generic
HTML, and accessibility remain separate evidence gaps; ECMA-402 has no
profile. Generated-bundle, minified, CommonJS, and browser-script dogfood
is absent from the pinned targets. The corpus contains two measured `.cjs`
modules but no separate CommonJS class. APG68 decides none of these
candidates.
