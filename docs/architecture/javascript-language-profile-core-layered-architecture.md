# JavaScript Language-Profile Core Layered Architecture

- Phase: APG70 terminal rejected state
- Status: Rejected historical architecture under
  [ADR 0040](../adr/2026/08/0040-javascript-language-profile-core-and-layered-decision-model.md);
  not current authoring input; no candidate-authoring authority
- History: [ADR 0039](../adr/2026/08/0039-javascript-language-profile-architecture-and-lean-validation.md)
  remains Rejected and unchanged

## Purpose and non-inheritance

This architecture asks whether a reusable `javascript-language-profile` can
own one narrow problem: normative ECMAScript semantics for an already
classified concrete JavaScript region. It also defines how semantic,
structural, policy, and effective decisions preserve their distinct
authorities, obligations, severity, permission, and rollback.

It is a forward APG70 correction to the exact APG69 proposal. It does not reuse
ADR 0039's rejected flat register, single-route schema, composite authority, or
underclassified finalization behavior. APG69 and earlier history remain
immutable. No skill is authored and no integration surface changes.

## Sources, versions, rights, targets, and corpus

ECMA-262, 17th edition (ECMAScript 2026), published June 2026 and pinned to the
exact `es2026` annual object, is the normative language baseline. The exact
`es2026-errata` delta restores only source correspondence and is not normative
row authority. A later consequence-bearing corrigendum requires an explicit
dual-source disposition. The 2027 draft is moving evidence only. Test262 is
non-normative conformance/corpus evidence under its verified Ecma BSD-style
license.

Specification expression, embedded software/pseudocode, repository source,
contribution terms, Test262, both targets, and APG expression remain separate
rights classes. No specification grammar, algorithm, table, example, test, or
target expression is copied or adapted. The website supplies no root reuse
grant. Theme license surfaces use inconsistent version text, so the no-copy
boundary remains mandatory absent a path-specific rights disposition. These
are bounded clean-room findings, not universal legal guarantees.

The pinned website remains seventeen paths with one handwritten ESM
configuration. The pinned theme remains seventy-six paths, zero JavaScript
whole files, four substantive Astro TypeScript frontmatters, and two embedded
client scripts. APG52 remains descriptive: 1,892 JavaScript measurements and
4,365 exclusions, including build, vendored, snapshot, symlink, and minified
classes. No count, percentile, or target placement becomes structural policy.

## Narrow owner

After artifact class, region boundary, source goal, concrete host, emitted
bytes, and applicable implementation facts are established,
`javascript-language-profile` owns normative ECMAScript semantics for that
region. The boundary includes grammar; Script and Module semantics; strictness;
bindings, scope, closures, and evaluation order; expressions, statements,
completion, and exceptions; coercion and equality; objects, properties,
descriptors, prototypes, and classes; functions, calls, construction, `this`,
and arrow capture; iterators and generators; Promise and ECMAScript jobs;
language-level module linking/evaluation; `import()` expression semantics after
host input; the `import.meta` language hook; RegExp and Unicode semantics under
selected evidence; ECMA-262 built-ins; Proxy/Reflect; WeakRef and
FinalizationRegistry nondeterminism; SharedArrayBuffer/Atomics language
semantics; JSON built-ins; and Annex B only after applicability is established.

Conceptual owner tokens identify competence even when no APG skill exists.

## Non-owners and selection

The profile does not own source-goal selection, file/region classification,
feature availability, runtime conformance, host divergence, Node loading or
resolution, CommonJS, DOM/Web APIs, ECMA-402, TypeScript, JSX, host templates,
parser/transpiler/bundler output, build/regeneration, repository permission,
security acceptance, project support policy, or deployment.

Whole `.ts` and `.tsx` inputs route to the TypeScript owner; whole `.jsx`
inputs route to the JSX owner. JavaScript embedded in HTML, Astro, or MDX is
eligible only after an exact region boundary is established; the container
remains host-owned. Generated, bundled, minified, and vendored artifacts are
classified before judgment. Classification decides dispatch and edit policy,
not the meaning of observed ECMAScript bytes.

`NonOwners` in a semantic row applies only to its `PrimaryDecision`. A token
may therefore be a non-owner of that decision and still receive a distinct
bounded obligation. A genuine contradiction exists only when the same owner is
both primary owner and excluded from that same primary decision.

## Question-typed authority

Authorities prove consequences; routes name receivers of unresolved work.
They are never the same field.

- ECMA-262 annual controls normative language consequences.
- ECMA-402 plus exact implementation locale/Unicode data controls concrete
  internationalization consequences.
- extension, package, HTML, loader, and tool configuration establish source
  goal, region, and host mode.
- exact parser/transform output establishes emitted bytes; it does not prove
  runtime support.
- exact runtime and host version/configuration establish observed behavior.
- exact conformance evidence plus project support policy controls divergence
  and compatibility decisions.
- repository, project, security, or expressly scoped human authority controls
  permission and risk acceptance.

A pure owner-boundary classification may route without an irrelevant version
token. A positive host/runtime/output claim must carry the exact evidence that
controls it. Missing authority narrows the claim or stops it; it never becomes
a mismatch signal merely because evidence is absent.

## Script, Module, and CommonJS

ECMA-262 has Script and Module source goals. Script is not implicitly strict,
but a strict directive may make Script code strict; a row must state the actual
strictness premise. Module code is strict.

CommonJS is an exact Node host mode, not a third language goal. Wrapped
CommonJS JavaScript is judged under Script semantics while Node owns wrapper,
loading, resolution, cache, `require`, and `module.exports`. The file can route
a bounded embedded ECMAScript question without making the language owner the
whole-file owner.

Static import/export grammar and language linking/evaluation are ECMAScript.
Specifier resolution/loading is host-owned. `import()` supplies a
language-defined Promise-facing boundary after host input; host failure cause
remains host-owned. `import.meta` existence/hook is language-defined, while
property shape and values are host-defined.

## Adjacent authority boundaries

- Node APIs, loaders, resolution, CommonJS, and process behavior route to the
  exact Node host owner.
- DOM/Web APIs, worker creation, availability, and host task ordering route to
  the exact browser host owner.
- ECMA-402 owns internationalization semantics; concrete locale output also
  requires exact runtime locale and Unicode data.
- Parser acceptance, transform output, bundling, and minification route to the
  parser/build owner. Accepted or emitted syntax is not runtime support.
- Dynamic code, prototype mutation, and similar language mechanisms remain
  language questions, while permission to introduce them is a security-policy
  decision.
- JSON built-in semantics and JSON document/schema validity remain separate.

## Semantic signals

The layered contract owns seventeen signals with independent positive
predicates and false-positive controls. A signal names an established defect or
risk, not a topic being investigated. Evidence availability alone is neither
runtime divergence nor a version mismatch. Missing runtime evidence activates
`false-runtime-validation` only if a concrete runtime result is nevertheless
claimed. Iterator `return` is optional unless a separate resource/cleanup
contract makes cleanup consequential. A violated essential Proxy invariant and
correctness depending on finalization timing are Red stops.

## Qualitative structural policy

Disposition C remains selected: qualitative responsibility-and-complexity-first
judgment with no numeric whole-file bands. A large cohesive module may remain
routine; a small module with coequal runtime, orchestration, state, error, or
data-contract responsibilities may escalate. TypeScript migration remains a
project decision and is never inferred from size.

The ten signals remain distinct. `multiple-runtime-responsibilities` covers
coequal runtime-facing responsibilities within one or multiple hosts;
host/language and resolution/language mixing separately bind their exact host
or resolution owner. Async fanout with untraceable failure paths is Orange.
Data-shape pressure is Orange with restoration of the prior data-shape
contract. Generated/manual mixing stays structural Yellow; policy may raise a
direct edit to Red.

For multiple active signals, evaluate false positives first, then use the
highest structural response. Preserve every signal-owned obligation and
rollback in contract order. The receiver list may be deduplicated for display,
but obligation identity may not be deduplicated. An inactive signal cancels
only itself.

## Policy model

The accepted generic language-profile contract supplies the authority model:
applicable repository and security restrictions are conjunctive; stricter
repository policy controls; explicit human instruction supersedes only when
its authority and scope expressly cover the decision; and any bounded exception
records authority, scope, rationale, evidence, validation, and rollback.
Overrun stops.

Policy authorities are distinct from policy routes. Granted permission may
leave no policy route. Required acceptance leaves permission unresolved and
routes the open decision. Multiple authorities and their rollbacks remain
represented. No semantic or structural result can lower a policy stop.

## Four layers and exact composition

- **S — semantic:** primary decision, owner, selection, response, routes,
  signals, normative/context authorities, and rollback.
- **T — structural:** zero or more independently active signals, response
  maximum, context-resolved routes, obligations, and rollback union.
- **P — policy:** ordered authorities, decision, response, unresolved routes,
  permission, and rollback.
- **E — effective:** response maximum; ordered unique receiver summary S then T
  then P; complete provenance-bearing obligation list; ordered rollback union;
  and stopped/unresolved/proceed permission.

`EffectiveRoutes` is only a receiver summary. `EffectiveObligations` preserves
layer, source row/signal, and route position, so two different questions to the
same owner remain separately resolvable. Completion requires every obligation,
permission, and rollback to be resolved. No more severe layer discards a lower
layer's regeneration, restoration, or coordination duty.

Composition rows contain exact semantic IDs, structural signal arrays, typed
policy authorities/decisions, artifact class, and replayed results. Free-prose
relations are not evidence. Controls cover response maximum in both directions,
policy stop, multiple signals, active-plus-deactivated signals, multiple
policies, non-superseding human instruction, bounded exception scope,
same-owner distinct obligations, and produced-artifact permission.

## Process and evidence

Process invariants remain generic-lifecycle-owned and outside candidate prose.
The actual corrected full-index patch and exact hashes precede fresh review.
Retention binds accepted hashes to retained bytes; rejection preserves APG69
and APG70 history. Mechanical parsing can prove shape, vocabulary membership,
reference existence, response maximum, route summaries, and rollback unions,
but cannot prove factual semantics or owner coherence. Mutation-negative
controls are required before any mechanical claim.

## Corrected register scope and terminal eligibility

The corrected validation surface contains 33 semantic scenarios, 10 structural
signals, 15 composition controls, and 2 process invariants. S001-S024 retain
their stable IDs where the purpose survives. S025-S033 close critical
TypeScript/TSX, JSX, embedded-region, parser/runtime, dynamic-code/security, and
produced-artifact selection boundaries. C009-C015 close intralayer and policy
composition gaps without creating an exact-action map.

Fresh APG70 review found genuinely new material defects after the one permitted
correction. ADR 0040 is Rejected and eligibility is
`not-applicable-rejected`. This architecture and its corrected registers are
historical evidence only, not a current authoring input. APG71 is not
recommended; no candidate or successor authority exists.

## Rollback, refresh, and APG70 boundary

Rejecting ADR 0040 leaves this as historical corrected evidence and preserves
all APG69 history; no maintained executable, test, catalog, projection,
release, public, active, or target surface depends on it.

Reverify before reuse when the annual/errata state, consequence-bearing source,
Test262 rights, target trees, consuming toolchain evidence, or accepted generic
contract changes. APG70 alone may terminally decide ADR 0040 after fresh review.
No APG71, candidate authoring, integration, readiness, publication, deployment,
or successor begins here.
