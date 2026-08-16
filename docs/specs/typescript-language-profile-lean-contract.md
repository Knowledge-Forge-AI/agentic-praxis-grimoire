# TypeScript Language-Profile Lean Contract

## Status

Proposed under [ADR 0041](../adr/2026/08/0041-typescript-language-profile-architecture-and-compiler-generation-boundary.md)
(APG71), corrected once and then Rejected by fresh independent APG72 review.
This contract is historical evidence, not current authoring input.
Candidate-independent: no `typescript-language-profile` or JavaScript
skill exists, no integration owner changes, and this contract grants no
candidate-authoring or successor authority.

The design has one primary decision per row, typed compiler-role bindings,
typed unresolved route obligations, and no layer arithmetic, policy subsystem,
exact-action map, register-owned vocabulary, or numeric structural policy.

## Source labels and authority roles

Public records use stable labels. Full source identities, npm integrity values,
and package relationships remain in publication-excluded evidence and managed
reports.

- **TS7-SOURCE** — exact native Go compiler source and package evidence for
  `typescript@7.0.2`.
- **TS6-SOURCE** — exact legacy compiler source and package evidence for
  `typescript@6.0.2` and `typescript@6.0.3`.
- **TS59-SOURCE** — exact legacy compiler source and package evidence for
  `typescript@5.9.3`; TypeScript 6 source is not implementation truth for this
  version.
- **TS6-COMPAT-PKG** — `@typescript/typescript6@6.0.2`, a wrapper exposing
  `tsc6` and re-exporting `@typescript/old` through an
  `npm:typescript@^6` alias. The wrapper has no registry `gitHead`, and its
  version does not bind the resolved compiler or its source.
- **TS-DOCS** — moving handbook and TSConfig explanation, never exact-version
  authority by itself.
- **TS-RELEASE-NOTES** — version-scoped release notes for their named release
  only.

Exact compiler source and package evidence control exact-version
implementation claims. Exact project configuration, graph, role invocation,
and declaration environment control target claims. Moving documentation is
explanatory only.

## Closed vocabularies

This contract, never a register, owns the following exact ordered arrays. No
addition, removal, alias, case variant, or register-only token is permitted.
Vocabulary membership authorizes spelling only, not factual semantics. An
owner token is conceptual and does not imply an installed skill.

- **ScenarioKinds** — `semantic`, `boundary`, `process`
- **Owners** — `typescript-static-semantics-owner`,
  `typescript-declaration-owner`, `javascript-source-language-owner`,
  `javascript-runtime-owner`, `tsx-composition-owner`,
  `jsx-syntax-transform-owner`, `host-language-owner`,
  `compiler-toolchain-owner`, `project-configuration-owner`,
  `module-resolution-owner`, `declaration-environment-owner`,
  `module-runtime-loader-owner`, `build-transform-owner`,
  `editor-tooling-owner`, `package-provenance-owner`,
  `repository-policy-owner`, `security-policy-owner`,
  `generic-lifecycle-owner`
- **Selection** — `selected`, `bounded-route`, `routed-to-owner`,
  `non-trigger`
- **Responses** — `proceed-routine`, `inspect-before-judgment`,
  `verify-exact-evidence`, `stop-missing-evidence`, `stop-and-route`
- **DecisionClasses** — `stable-semantic-rule`,
  `exact-version-meta-rule`, `boundary-rule`
- **CompilerFamilies** — `legacy-js-compiler`, `native-go-compiler`,
  `project-selected`, `non-typescript-transformer`, `unknown`, `none`
- **CompilerRoles** — `cli-checker`, `declaration-emitter`,
  `javascript-emitter`, `programmatic-api`, `editor-language-service`,
  `embedded-host-checker`, `transpiler-type-stripper`, `project-builder`,
  `none`
- **SelectionSources** — `project-config`, `manifest-direct`,
  `manifest-alias`, `lock-direct`, `lock-peer`, `script-invocation`,
  `api-import`, `editor-config`, `host-integration`, `bundled-tool`,
  `unknown`, `none`
- **RoleStates** — `configured`, `resolved-only`, `available-only`, `absent`,
  `required`, `unknown`, `none`
- **EvidenceStates** — `source-bound`, `package-only`, `required`,
  `unavailable`, `none`
- **SourceKinds** — `ts-module`, `mts-module`, `cts-module`, `tsx-module`,
  `handwritten-dts`, `generated-dts`, `checked-js`, `embedded-ts-region`,
  `emitted-js`, `config-state`, `none`
- **ArtifactClasses** — `handwritten-source`, `handwritten-declaration`,
  `generated-declaration`, `checked-javascript`, `host-artifact`,
  `emitted-javascript`, `project-config`, `role-matrix`, `module-reference`,
  `declaration-environment`, `project-graph`, `none`
- **OptionKeys** — `strict`, `strictFunctionTypes`,
  `exactOptionalPropertyTypes`, `noUncheckedIndexedAccess`, `types`,
  `preserveConstEnums`, `isolatedModules`, `experimentalDecorators`,
  `emitDecoratorMetadata`, `useDefineForClassFields`,
  `verbatimModuleSyntax`, `noEmit`, `skipLibCheck`, `allowJs`, `checkJs`,
  `jsx`, `jsxFactory`, `jsxImportSource`, `module`, `moduleResolution`,
  `target`, `lib`, `declaration`, `emitDeclarationOnly`, `composite`
- **RouteObligations** — `runtime-behavior`, `compiler-identity`,
  `effective-options`, `project-membership`, `module-resolution`,
  `declaration-environment`, `jsx-semantics`, `host-integration`,
  `package-source-binding`, `build-emission`, `editor-role`, `runtime-api`,
  `acceptance-policy`, `security-policy`, `generated-provenance`,
  `runtime-loading`
- **AuthorityTokens** — `exact-compiler-source`, `exact-package-metadata`,
  `exact-project-config`, `exact-project-graph`,
  `exact-declaration-environment`, `exact-role-invocation`,
  `version-scoped-release-notes`, `moving-docs-explanatory`,
  `exact-emitted-artifact`, `runtime-host-observation`,
  `apg-authority-contract`, `generator-provenance`
- **Signals** — `static-runtime-conflation`, `version-dependent-result`,
  `open-world-exhaustiveness`, `type-instantiation-tractability`,
  `exact-option-missing`, `declaration-runtime-mismatch`,
  `unsafe-assertion`, `generated-artifact-drift`, `compiler-role-split`,
  `source-kind-ambiguity`, `decorator-regime-unknown`, `false-completion`
- **RollbackClasses** — `withdraw-unsupported-claim`, `reroute-to-owner`,
  `reverify-exact-evidence`, `regenerate-from-source`,
  `no-action-required`

Empty arrays are written exactly `[]`. There is no `not-applicable` token.
Fields that do not need a compiler, source kind, or artifact use the closed
`none` token where their vocabulary permits it.

## Compiler-binding grammar

Every `CompilerBindings` item has this exact form:

```text
role=<role>;family=<family>;version=<exact semver|exact-required|unknown|none>;
selection=<selection-source>;state=<role-state>;evidence=<evidence-state>
```

Each item aligns exactly one role, family, version, selection source, role
state, and evidence state. A row may carry multiple items only when the
decision genuinely compares or composes those roles. One role never proves
another. Package presence, a peer lock resolution, a wrapper version, and an
editor role never become a CLI, API, emitter, builder, or embedded-checker
role without the corresponding exact binding.

`project-selected` does not supply an exact version. A version-dependent row
using it must require the missing exact binding and stop until it is present.

## Option-fact grammar

Each `OptionFacts` item is exactly `key=json-value`, where `key` belongs to
**OptionKeys**. Boolean, string, and array values retain their JSON spelling;
an empty array is `types=[]`.

Absence, unknown state, a required value, and an inherited default are not
option facts. They belong in `RequiredAuthorities`. Thus
`experimentalDecorators=true`, `experimentalDecorators=false`, an absent key,
an unknown effective value, and a required exact value remain distinct.

## Route grammar and activation

Each `Routes` item is exactly:

```text
<owner>|<obligation>
```

Both components must belong to their closed vocabularies. Routes contain only
active unresolved obligations. Resolved premises, evidence owners, general
competencies, and bare repetition of `PrimaryDecisionOwner` are forbidden.
An empty route set is `[]`. Routing never changes the row's response or
transfers the primary decision.

## Signal definitions

Signals are independent of registers. Each definition supplies the exact
positive-evidence condition and false-positive boundary:

- **`static-runtime-conflation`** — positive when a static TypeScript fact is
  used to conclude emitted or runtime behavior without exact emitted-artifact
  and runtime evidence; false when the row states only static meaning and
  routes runtime behavior.
- **`version-dependent-result`** — positive when the claimed result is known
  to vary by compiler version and an exact aligned version controls the
  decision; false when a stable semantic rule is explicitly version-invariant
  or the row merely requests version evidence.
- **`open-world-exhaustiveness`** — positive when exhaustiveness is claimed
  while augmentation, declaration merging, an open union, or an unknown
  project graph can add cases; false for a closed discriminated set whose
  closed-world evidence is present.
- **`type-instantiation-tractability`** — positive when recursive,
  distributive, mapped, or template-literal instantiation has evidenced
  compiler tractability or termination consequences; false from generic or
  conditional syntax alone.
- **`exact-option-missing`** — positive when an option value controls the
  current consequence and the exact effective value is absent; false when the
  exact value is present or the option does not control this decision.
- **`declaration-runtime-mismatch`** — positive when a declaration claim is
  treated as runtime availability or conflicts with exact runtime-host
  observation; false when the row is limited to static declaration meaning.
- **`unsafe-assertion`** — positive when an assertion suppresses a presently
  evidenced incompatible or unverified boundary; false from assertion syntax
  alone when exact evidence establishes the asserted invariant.
- **`generated-artifact-drift`** — positive when generated output differs from
  its bound generator/input or provenance is missing for a consequence-
  bearing generated claim; false for handwritten artifacts or exact generated
  output bound to current provenance.
- **`compiler-role-split`** — positive when a claim transfers evidence from
  one compiler role to another or multiple roles disagree materially; false
  merely because several aligned roles are present.
- **`source-kind-ambiguity`** — positive when admitted inputs have different
  source-kind consequences but the row records no exact kind or collapses
  them; false when each admitted input has an aligned exact source kind.
- **`decorator-regime-unknown`** — positive when decorator typing or emit is
  consequence-bearing and the exact compiler plus effective
  `experimentalDecorators`, `emitDecoratorMetadata`, and relevant class-field
  regime are not established; false when no decorator decision is made or the
  complete exact regime is present.
- **`false-completion`** — positive when static, editor, package, or partial-
  role success is cited as completion of an unobserved build, emit, API,
  loader, or runtime obligation; false when completion is scoped to the exact
  observed role and unresolved obligations remain explicit.

`ActiveSignals` contains only signals whose positive condition is evidenced
for the exact row. Topic relevance, investigation, a risk-family mention, or
token occurrence is not activation.

## Semantic-row schema

The semantic register retains IDs `APG71-TS-S001` through
`APG71-TS-S022`, exactly 22 rows with `Kind: semantic`. Every row has exactly
20 fields in this order:

`ID`, `Kind`, `In`, `DecisionClass`, `SourceKind`, `WholeFileOwner`,
`PrimaryDecisionOwner`, `Selection`, `Response`, `CompilerBindings`,
`OptionFacts`, `PrimaryDecision`, `Routes`, `NonOwners`, `ActiveSignals`,
`PresentAuthorities`, `RequiredAuthorities`, `Invariant`, `Forbid`,
`Rollback`.

`DecisionClass` is either `stable-semantic-rule` or
`exact-version-meta-rule`. A stable rule states its semantic invariant without
inventing a target result. A meta-rule requires the exact compiler and inputs
before stating a concrete version-dependent result. `PresentAuthorities` lists
only evidence actually present; missing evidence appears only in
`RequiredAuthorities`.

## Boundary-row schema

The boundary register retains `APG71-TS-B001` through `APG71-TS-B012` and
adds `APG71-TS-B013` for `.cts` and `APG71-TS-B014` for generated
declarations: exactly 14 rows with `Kind: boundary`. Every row has exactly 21
fields in this order:

`ID`, `Kind`, `In`, `DecisionClass`, `ArtifactClass`, `SourceKind`,
`WholeFileOwner`, `PrimaryDecisionOwner`, `Selection`, `Response`,
`CompilerBindings`, `OptionFacts`, `PrimaryDecision`, `Routes`, `NonOwners`,
`ActiveSignals`, `PresentAuthorities`, `RequiredAuthorities`, `Invariant`,
`Forbid`, `Rollback`.

`DecisionClass` is exactly `boundary-rule`. Boundary rows distinguish
whole-file ownership, the primary static decision, host or JSX composition,
compiler role, active unresolved obligation, source kind, and artifact class.
Checked JavaScript uses
`javascript-source-language-owner` for whole-file ownership and may route
runtime behavior separately. Emitted JavaScript is `emitted-js` /
`emitted-javascript`. Generated declarations are `generated-dts` /
`generated-declaration` and require `generator-provenance`.

## Process-row schema

The boundary register additionally carries exactly two process rows,
`APG71-TS-P001` and `APG71-TS-P002`, with `Kind: process` and exactly 5 fields
in this order:

`ID`, `Kind`, `ProcessOwner`, `Invariant`, `Forbid`.

`ProcessOwner` is exactly `generic-lifecycle-owner`. Process rows bind the
generic evidence lifecycle and sole-correction boundary; they never become
candidate prose and never use a free-prose owner.

## Row invariants

- `WholeFileOwner` and `PrimaryDecisionOwner` are separate typed owners.
- `NonOwners` excludes conceptual owners from the primary decision only; it
  is not a route list.
- `CompilerBindings`, `OptionFacts`, `Routes`, `NonOwners`, `ActiveSignals`,
  `PresentAuthorities`, and `RequiredAuthorities` are exact arrays; empty is
  `[]`.
- A row states one unconditional `PrimaryDecision`. Missing evidence that
  controls that primary decision selects a stop response rather than a
  conditional or invented result. Evidence required only for an explicit
  unresolved adjacent route remains in `RequiredAuthorities` without changing
  an otherwise complete primary decision into a stop.
- S010, S011, S012, and S021 store consequence-bearing booleans exactly. S012
  limits added `undefined` to undeclared indexed access.
- S019 is one missing-decorator-regime stop, not simultaneous unknown and
  asserted evidence.
- S014 and S017 use an empty active-signal array.
- S004 requires closed-world evidence; S015 records augmentation limits; S016
  separates inclusion, module/global status, and runtime; S018 binds enum kind
  and emit options; S020 qualifies contextual typing; and S022 binds each
  exercised role separately while listing absent build, emit, or runtime
  evidence only as required.
- B008 aligns CLI, API, editor, and embedded roles structurally. B012 types
  emitted JavaScript. B013 separates `.cts` from `.mts`. B014 types generated
  declarations and provenance.
- No row claims runtime, build, emit, API, editor, loader, or completion success
  from static success or package presence.

## Source-authority and structural dispositions

Source authority is amended disposition **B**: role-selected, claim-specific
exact compiler authority composed from aligned role, family, version,
selection, option, project, source-kind, environment, package, source, and
artifact evidence. No single source token is universal.

Structural policy is disposition **D — deferred**. Rows and a future candidate
make no structural judgment. Numeric whole-file bands, percentiles,
length-selected language choice, and corpus-derived policy are forbidden.

## Severity and one-correction boundary

- **material** — wrong owner, role, family, exact version, option/evidence
  state, source kind, artifact class, signal activation, source authority,
  runtime claim, boundary, route obligation, or omitted consequence-bearing
  evidence;
- **ordinary** — a bounded defect that changes no adjacent decision; and
- **note** — wording or formatting.

APG72 may apply at most one coherent architecture correction. This contract is
part of that terminal-neutral correction. The actual corrected patch, exact
corrected hashes, identity evidence, replay vectors, and reviewer bindings
must exist before fresh corrected-state review. A genuinely new material
defect after correction requires rejection, not a second semantic correction.

## Machine-versus-human proof boundary

Mechanical checks may prove exact token membership, grammar conformance,
schema field presence and order, ID continuity, array form, row counts, and
cross-reference existence. Mutation-negative demonstrations must show each
mechanical guard fails on its seeded defect before the guard is trusted.

Only independent human review may prove semantic correctness, boundary fit,
role truth, option consequence, signal activation, compatibility scope, source
authority, or rights conclusions. Token occurrence is never semantic coverage.

## Forbidden evidence patterns

Forbidden: fixture self-authorization; expected and actual values copied from
one source; global token presence as local evidence; substring token matching;
positive-marker-only polarity; lost subjects across coordinated predicates;
order-dependent module-cache proof; missing-versus-present-`None` conflation;
free-prose cross-register linkage claimed as exact; aggregate fields hiding
per-role or per-authority outcomes; false full identities; manual hash-prefix
expansion; bounded parsing claimed as complete prose equivalence; package
presence claimed as role execution; and vocabulary occurrence claimed as
coverage.

## Register independence and eligibility

The semantic and boundary registers are independently owned records. Neither
authorizes vocabulary, extends a schema, defines a signal, or binds the other
through prose. Cross-register references use exact row IDs.

The terminal result is `not-applicable-rejected`. Fresh APG72 review replayed
all 22 semantic, 14 boundary, and 2 process rows and found new material
owner/route, role-state, source-kind, and evidence-state defects. ADR 0041 is
Rejected; this contract grants no candidate authority.

## Known limitations

The rejected contract remains unexercised by a candidate. The website proves TypeScript
7 package availability but no compiler role. Theme role evidence is qualified
by a stale lock. TS6-COMPAT-PKG lacks an exact wrapper-to-resolved-compiler
source binding. Moving documentation is not exact-version authority. TypeScript
structural policy was deferred. Fresh corrected-state review terminally
rejected this proposal.
