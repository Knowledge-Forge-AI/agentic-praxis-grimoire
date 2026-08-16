# TypeScript Language-Profile Architecture

## Status and phase boundary

Proposed under [ADR 0041](../adr/2026/08/0041-typescript-language-profile-architecture-and-compiler-generation-boundary.md)
(APG71), corrected once and then Rejected by fresh independent APG72 review.
This corrected design is historical evidence, not current architecture input.
No
`typescript-language-profile` or JavaScript skill exists, no integration owner
changes, and no candidate authoring or successor phase is authorized.

## Rejected JavaScript architectures are not inherited

ADR 0039 and ADR 0040 remain Rejected historical evidence. This architecture
is an independent TypeScript line, not a JavaScript repair. It inherits no
layer arithmetic, numeric structural value, composite authority token, or
register-owned vocabulary from the rejected designs. A conceptual
`javascript-source-language-owner` or `javascript-runtime-owner` identifies a
decision boundary only; neither token implies an accepted JavaScript
architecture or installed skill.

## Purpose

Answer one narrow question: can a reusable TypeScript profile own
TypeScript-specific syntax, static semantics, and type-erasure boundaries for
a concrete source region after the exact compiler role, compiler family,
compiler version, selection source, option state, project graph, source kind,
and declaration environment are established?

The answer remains a corrected proposal. Compiler operation, option choice,
JavaScript source and runtime semantics, JSX transformation, host integration,
build behavior, editor behavior, package installation, runtime loading, and
project acceptance policy remain separate decisions.

## Exact source families and documentation roles

TypeScript has no ECMA-style formal standard in this architecture. Exact
source objects, package identities, integrity values, and rights evidence live
in the publication-excluded identity record and managed evidence. Public text
uses stable labels and roles, not internal Git identities.

- **TS7-SOURCE** is the native Go compiler line for exact
  `typescript@7.0.2`. Its CLI package and source release are bound by exact
  registry and release evidence. TypeScript 7.0 has no supported programmatic
  compiler API; the stated TypeScript 7.1 API expectation is moving evidence,
  not current authority. Package metadata and repository metadata remain
  separate evidence because their repository fields and release assembly are
  not interchangeable.
- **TS6-SOURCE** is the legacy JavaScript-implemented compiler line for exact
  `typescript@6.0.2` and `typescript@6.0.3`. These exact package and source
  releases are independently bound. They may explain only those exact
  versions and do not explain a 5.9.3 result.
- **TS59-SOURCE** is the same legacy implementation lineage at exact
  `typescript@5.9.3`, independently bound to its own package, release, source,
  tree, and license evidence. TypeScript 6 changed material defaults, so the
  exact 5.9.3 object controls 5.9.3 implementation truth.
- **TS6-COMPAT-PKG** is `@typescript/typescript6@6.0.2`, a wrapper that exposes
  `tsc6` and re-exports `@typescript/old`, with that dependency resolving from
  the alias `npm:typescript@^6`. The wrapper has no registry `gitHead`; its
  version does not bind the resolved compiler package or establish a
  one-to-one package-to-source relation. Claims needing that relation remain
  stopped.
- **TS-DOCS** is moving explanatory handbook and TSConfig prose. It is not
  exact-version authority merely because a page discusses an older feature.
  Version-scoped release notes may explain a named release. Exact compiler
  source and package evidence control historical implementation behavior, and
  exact target evidence controls a target result.

The TypeScript 7 development line and repository heads remain refresh evidence
only.

## Rights and clean-room boundary

Rights classes remain separately verified: compiler source and npm package
metadata under Apache-2.0; documentation prose under CC-BY-4.0 and website code
under MIT; target repositories under their own terms; and APG expression as
original work. Compiler tests, baselines, diagnostics, documentation, target
expression, and rejected JavaScript expression are not copied or adapted.
Read-only factual inspection is not a reuse-rights conclusion, and the bounded
clean-room conclusion is not legal advice.

## Target compiler-role reconstruction

Package presence and compiler execution are separate facts. Each target role
is stated through the contract's aligned compiler-binding grammar; one role
never proves another.

### Website

The exact website lock resolves `typescript@7.0.2` as a peer-marked package.
No manifest directly selects TypeScript, no script invokes `tsc`, Astro itself
does not declare a TypeScript dependency, and the exact target establishes no
CLI checker, declaration emitter, JavaScript emitter, programmatic API,
editor-language-service, embedded-host checker, type-stripper, or project
builder consumer. The truthful result is an available lock resolution with no
established effective compiler role. Editor-only use remains a possibility,
not present evidence.

### Theme

The theme manifest selects the legacy line at `^5.9.3`, and its lock contains
literal `typescript@5.9.3` resolutions used by the configured checker and
language-service graph. The build script runs under `tsx`; `tsx` is the
transpiler/type-strip runner for that script, not proof of a TypeScript compiler
role. The script separately invokes `tsc`, which performs checking and
declaration-only emit under the target configuration. These are distinct
`cli-checker` and `declaration-emitter` roles. No evidence establishes a
programmatic compiler API or JavaScript-emitter role for that build.

The target manifests and lock are desynchronized. Literal lock entries prove
historical exact resolutions and configuration evidence; they do not prove a
reproducible current install graph. Any present-result claim must re-establish
the exact selected package and invocation rather than treating the stale lock
as a live installation oracle.

### Cross-target conclusion

The project graph controls which compiler packages and roles are available or
selected; framework version alone does not. The two targets do not establish
different *effective* compilers merely because the same Astro version appears
beside different lockfile packages: the website has TypeScript 7 available
without an exercised role, while the theme configures legacy 5.9.3 checking,
language-service, and declaration-emission roles subject to the stale-lock
qualification.

Target and corpus counts remain descriptive evidence only. No percentile,
line count, or package count becomes policy.

## Source-authority disposition

Disposition **B — role-selected, claim-specific exact compiler authority**.
Authority is composed per consequence-bearing claim:

1. bind the exact compiler role to one compiler family and exact version;
2. bind how the role was selected and whether it is configured, resolved,
   merely available, absent, required, or unknown;
3. bind the exact option facts, project graph, source kind, and declaration
   environment that control the result;
4. use the exact package and source object for version-specific implementation
   truth;
5. use version-scoped release notes only for their named release and moving
   documentation only as explanation; and
6. route emitted behavior to the exact artifact, runtime host, and loader.

No family token, package presence, lock entry, compiler role, or documentation
page is universal authority. `project-selected` is a family placeholder, not
an exact compiler result. A missing exact binding forces
`stop-missing-evidence` for a version-dependent decision.

Alternatives remain rejected: a universal TypeScript 7 baseline contradicts
the 5.9.3 target; a universal legacy baseline misstates TypeScript 7 projects;
and a bare family split fails to type roles, options, and evidence. Structural
disposition D is independent of this source-authority choice.

## Narrow TypeScript static owner

`typescript-static-semantics-owner` owns TypeScript-specific syntax and static
meaning for an established source region under exact inputs. It may decide:

- annotations, erasure boundaries, aliases, interfaces, structural
  assignability, literal/union/intersection types, narrowing, discriminated
  unions, generics, constraints, inference, queries, conditional/mapped/
  template-literal types, overload selection, and exact option-controlled
  variance;
- static distinctions among `any`, `unknown`, `never`, `void`, `undefined`,
  and `null`; optional-property and indexed-access consequences under exact
  boolean option facts; class compatibility; declarations, merging, and
  augmentation; and assertion and `satisfies` consequences; and
- the static side of type-only imports, enums, decorators, and emit-sensitive
  features only when the controlling compiler and option facts are exact.

It does not choose compiler options, infer missing evidence, decide runtime
behavior, accept risk, or claim that a successful static result proves build,
emit, editor, API, loader, or runtime success.

`typescript-declaration-owner` owns declaration-specific static shape and
environment questions. Generated declarations additionally require exact
generator provenance; they are not treated as handwritten declarations.

## Explicit adjacent owners

- `javascript-source-language-owner` keeps whole-file ownership of checked
  JavaScript. TypeScript checking is a bounded, non-additive static route;
  JavaScript source semantics do not become TypeScript semantics.
- `javascript-runtime-owner` owns evaluation and emitted-code behavior under
  an exact runtime and host.
- `compiler-toolchain-owner` owns CLI, API, watch, incremental, diagnostics,
  caching, performance, and compiler execution.
- `project-configuration-owner` chooses compiler options and project
  membership; the TypeScript owner explains exact consequences afterward.
- `module-resolution-owner` owns static resolution under exact configuration;
  `module-runtime-loader-owner` separately owns runtime loading.
- `declaration-environment-owner` owns `lib`, `@types`, and ambient environment
  selection. A declaration never proves a runtime API exists.
- `tsx-composition-owner` and `jsx-syntax-transform-owner` own TSX composition
  and JSX syntax/transform decisions.
- `host-language-owner` owns Astro, MDX, and other host files; an embedded
  TypeScript region requires an exact host boundary and host integration.
- `build-transform-owner`, `editor-tooling-owner`,
  `package-provenance-owner`, `repository-policy-owner`, and
  `security-policy-owner` keep their exact adjacent obligations.

Routes contain only unresolved obligations in the contract grammar. A resolved
premise, evidence source, competency, or repetition of the primary owner is
not a route.

## Compiler-role and option-state model

Each consequence-bearing compiler role uses one aligned binding:

```text
role=<role>;family=<family>;version=<exact semver|exact-required|unknown|none>;
selection=<selection-source>;state=<role-state>;evidence=<evidence-state>
```

Compiler family, exact version, role, selection source, role state, and
evidence state are independent axes. A `lock-peer` binding in
`available-only` state does not become a checker. A configured editor role
does not become a CLI or declaration-emitter role. A wrapper version does not
bind the aliased compiler it loads.

Compiler option facts use exact `key=json-value` entries. `strict=false`,
`strict=true`, an absent key, an inherited default, and an unknown value are
distinct states. Arrays retain JSON form, including `types=[]`. Missing,
unknown, required, and inherited-default states are placed in
`RequiredAuthorities`; they are never fabricated as option facts.

## Source kinds and artifact boundaries

- `.ts` is `ts-module`; `.mts` is `mts-module`; `.cts` is `cts-module`.
  `.mts` and `.cts` have distinct exact outcomes and never share one stored
  source-kind token.
- `.tsx` is `tsx-module`, with TSX composition and JSX transformation typed
  separately from TypeScript static expression reasoning.
- Handwritten `.d.ts`, `.d.mts`, and `.d.cts` use
  `handwritten-declaration`; generated declarations use `generated-dts` and
  `generated-declaration`, with generator provenance required.
- checked `.js` is `checked-js` and `checked-javascript`; its whole-file owner
  is the JavaScript source-language owner.
- embedded TypeScript uses `embedded-ts-region` inside a `host-artifact` whose
  whole-file owner remains the host.
- emitted JavaScript is `emitted-js` and `emitted-javascript`; static TypeScript
  evidence does not decide its runtime behavior.
- configuration and role matrices use typed non-source classes rather than
  pretending to be language source.

Source kind is established by extension, host boundary, configuration, and
provenance evidence, never content resemblance alone.

## Semantic-risk model

The contract owns twelve independent signals. Each signal has positive
evidence and a false-positive boundary. A row's `ActiveSignals` contains only
signals whose positive evidence is present for that exact decision; topical
relevance, an investigation, or a vocabulary occurrence does not activate a
signal. `[]` means none active.

Signals cover static/runtime conflation; version-dependent results; false
closed-world exhaustiveness; type-instantiation tractability; missing exact
options; declaration/runtime mismatch; unsafe assertions; generated-artifact
drift; compiler-role splits; source-kind ambiguity; unknown decorator regime;
and false completion. Exact definitions live in the lean contract.

Static-semantic risk remains size-independent and non-numeric. A tiny source
region may stop, and a large cohesive module may remain routine.

## Scenario and boundary model

The corrected proposal retains 22 semantic IDs, expands the boundary set to
14 IDs, and retains 2 process invariants:

- semantic rows: `APG71-TS-S001` through `APG71-TS-S022`;
- boundary rows: `APG71-TS-B001` through `APG71-TS-B014`, with B013 adding the
  distinct `.cts` outcome and B014 adding generated declarations; and
- process rows: `APG71-TS-P001` and `APG71-TS-P002`, owned exactly by
  `generic-lifecycle-owner`.

The contract, not a register, owns all vocabularies, grammars, field order,
and signal definitions. Registers carry facts under that contract and cannot
authorize new tokens.

## Structural-policy disposition

Disposition **D — deferred**. The available targets and descriptive corpus do
not justify a qualitative TypeScript structural policy across representative
source families. The proposed candidate scope therefore makes no structural
judgment about module size, decomposition, contract surface, or migration. No
numeric whole-file band, percentile, length trigger, or JavaScript-versus-
TypeScript threshold exists.

The user's project preference for JavaScript in short, comparatively simple
utilities and TypeScript in larger or contract-heavy utilities remains project
input. Project owners may consider evolving public data contracts, consumers,
invariants, discriminated state, refactoring pressure, declaration publishing,
toolchain constraints, and maintenance needs. The profile never converts
those considerations into language law.

## Terminal eligibility

Terminal result: **not-applicable-rejected**. The corrected proposal had been
`authoring-eligible-with-narrowing` pending fresh review, but that provisional
result did not survive review and grants no candidate-authoring authority. Its
historical mandatory narrowings were:

1. static semantics, declaration boundaries, and typed adjacent routes only;
   structural judgment remains absent;
2. every version-dependent result requires aligned exact compiler-role,
   family, version, selection, option, project, source-kind, and environment
   evidence;
3. package presence, a lock entry, an editor role, and a wrapper version never
   prove an exercised compiler role;
4. `.tsx` and embedded TypeScript keep composition or host ownership, with a
   bounded TypeScript static role only after exact boundaries are known;
5. checked JavaScript keeps the conceptual JavaScript source-language owner;
6. emitted JavaScript and generated declarations use their typed artifact
   boundaries, and generated output requires provenance;
7. missing exact options, decorator regime, role identity, package/source
   relation, or required evidence stops the affected claim;
8. moving documentation remains explanatory; exact source/package and target
   evidence control exact-version and target results; and
9. no runtime, build, emit, API, editor, or completion conclusion follows from
   static success or another compiler role.

Fresh APG72 review replayed all 22 semantic, 14 boundary, and 2 process rows
from the hash-bound corrected state. Two non-author lanes found genuinely new
material owner/route, role-state, source-kind, and present/required-evidence
defects. The one-correction boundary therefore requires rejection rather than
another semantic correction.

## Rollback and preservation

Rejecting ADR 0041 leaves this corrected proposal as history and retains no
current TypeScript architecture input. There is no executable surface to
unwind: no skill, projection, catalog row, maturity row, route, fixture,
maintained test, or release owner changed. APG71 authorship and earlier history
remain preserved either way.

## Refresh conditions

Reverify before reuse when a stable TypeScript release changes; a TypeScript
7 programmatic API becomes available; TS6-COMPAT-PKG metadata or alias
resolution changes; target manifests, locks, scripts, configuration, or exact
objects change; an embedded-tooling compiler role changes; or source/package/
documentation rights change. A refresh does not authorize a candidate or
successor phase.

## Known limitations

The rejected proposal was grounded in two small first-party targets and one descriptive
corpus. The website establishes TypeScript 7 package availability, not an
exercised role. The theme role conclusion is qualified by a stale lock.
TS6-COMPAT-PKG lacks an exact wrapper-to-resolved-compiler source binding.
Moving docs cannot decide historical compiler behavior. Structural policy is
deferred. No candidate exercised the contract. Fresh corrected-state APG72
review terminally rejected the proposal.

## APG72 boundary

APG72 independently delivered, corrected once, freshly reviewed, and rejected
this proposal. No TypeScript or JavaScript skill, integration, readiness,
publication, deployment, APG73, or successor work is authorized here.
