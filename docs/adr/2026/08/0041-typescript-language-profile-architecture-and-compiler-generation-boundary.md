# ADR 0041: TypeScript Language-Profile Architecture and Compiler-Generation Boundary

## Status

Rejected (APG72). APG72 used the sole permitted correction, then two fresh
non-author lanes found genuinely new material owner/route, role-state,
source-kind, and present/required-evidence defects. No second semantic
correction is permitted. This status grants no candidate-authoring, APG73, or
successor authority.

## Context

ADR 0039 and ADR 0040 remain Rejected. APG71 exercised separate human
authority for an independent TypeScript architecture line on the exact APG70
baseline; it did not repair or reactivate either JavaScript design. Markdown
remains retained provisional under ADR 0037 and ADR 0038, both Accepted with
amendment. CSS remains absent with ADR 0031, ADR 0034, ADR 0035, and ADR 0036
Rejected. Integrated counts, routes, public and active v0.4.0, and both
read-only targets remain unchanged.

APG72 independently reconstructed the proposal before correction and found
one coherent material family: compiler family, exact version, compiler role,
selection, option, evidence, source-kind, artifact, signal, authority, and
route state were conflated or left as free prose. The initial design also
treated package presence as compiler execution, used TypeScript 6 source to
explain a 5.9.3 result, assigned checked JavaScript only to a runtime owner,
collapsed `.mts` and `.cts`, omitted generated-declaration coverage, and
treated moving documentation as exact-version authority.

The sole correction addressed that complete initial material set while
remaining terminal-neutral. Fresh corrected-state semantic, boundary, process,
source, rights, and target review then terminally decided this ADR.

## APG72 terminal decision

ADR 0041 is **Rejected**. Both fresh lanes independently found B005/B006 route
obligations paired with the wrong owner and B008 configured-role assertions
not established by its disjunctive input. One lane also found that declaration
source kinds collapse `.d.ts`, `.d.mts`, and `.d.cts`, and that B001 records
input-present compiler/config evidence as still required. Another found an
unsupported editor-role upgrade in the target conclusion. These are new
material defects after the sole correction.

The corrected architecture, contract, and 22/14/2 registers remain historical
evidence only. Eligibility is `not-applicable-rejected`. Source disposition B
and structural disposition D remain defensible in isolation but do not rescue
the rejected design. No TypeScript candidate or skill exists. APG73 is not
recommended or begun.

## Corrected proposal decision

1. APG70 remains the baseline; ADR 0039 and ADR 0040 remain Rejected and
   unchanged. This is independent TypeScript architecture, not JavaScript
   repair. Conceptual JavaScript owners do not imply an accepted JavaScript
   architecture or skill.
2. The corrected
   [TypeScript language-profile architecture](../../../architecture/typescript-language-profile-architecture.md)
   and
   [lean contract](../../../specs/typescript-language-profile-lean-contract.md)
   form the proposal subject to fresh APG72 review.
3. The narrow owner is `typescript-static-semantics-owner`: TypeScript-specific
   syntax, static semantics, and type-erasure boundaries for an established
   source region under exact compiler-role, family, version, selection,
   option, project-graph, source-kind, and declaration-environment inputs.
   Declaration-specific decisions may use `typescript-declaration-owner`.
4. JavaScript whole-file source semantics and JavaScript runtime behavior are
   distinct conceptual owners. Checked JavaScript keeps
   `javascript-source-language-owner`; static checking is a bounded,
   non-additive route. Static success never proves emitted or runtime behavior.
5. TypeScript has no assumed formal standard. Source authority is amended
   disposition B: **role-selected, claim-specific exact compiler authority**.
   Each claim composes exact role, family, version, selection, option, project,
   environment, package, source, and artifact evidence rather than treating
   any family or package token as universal.
6. The exact compiler families remain distinct:
   - TypeScript 7 native Go compiler source and `typescript@7.0.2` package;
   - the legacy compiler at exact `typescript@6.0.2` and `6.0.3`; and
   - the legacy compiler at exact `typescript@5.9.3`, bound to its own source
     and package object rather than explained by TypeScript 6 source.
7. `@typescript/typescript6@6.0.2` is a wrapper exposing `tsc6` and
   re-exporting `@typescript/old` through an `npm:typescript@^6` alias. Its
   missing registry `gitHead` and version do not establish the resolved
   compiler or a one-to-one package-to-source relation; dependent claims stop
   until exact binding evidence exists.
8. Current handbook and TSConfig prose is moving explanatory evidence.
   Version-scoped release notes explain only their named release. Exact
   compiler source/package evidence controls historical implementation claims,
   and exact target evidence controls target results.
9. Every consequence-bearing compiler role uses one aligned binding of role,
   family, exact version, selection source, role state, and evidence state.
   Package presence and one compiler role never prove another role.
10. The website's TypeScript 7 peer-marked lock resolution is package
    availability only: no direct manifest selection or exact target evidence
    establishes CLI, API, editor, embedded-checker, emitter, transformer, or
    builder execution.
11. The theme configures legacy 5.9.3 checking and language-service roles.
    Its build script runs under `tsx`, then separately invokes `tsc` for
    checking and declaration-only emit. The manifest/lock desynchronization
    means literal lock resolutions are historical evidence, not proof of a
    reproducible current install graph.
12. The corrected cross-target conclusion is that the project graph controls
    available and selected compiler roles; framework version alone does not.
    Different lock packages do not prove different effective compilers without
    exact invoked roles.
13. Compiler option facts use exact `key=json-value` entries. Boolean values,
    arrays such as `types=[]`, absence, inherited defaults, unknown values, and
    required values remain distinct. Missing facts appear in required evidence,
    never as invented option facts.
14. `PresentAuthorities` contains only present evidence;
    `RequiredAuthorities` contains evidence still required. Routes use the
    closed `<owner>|<obligation>` grammar and contain only active unresolved
    obligations, not resolved premises, competencies, or repeated primary
    owners.
15. The contract independently defines twelve semantic signals with positive
    evidence and false-positive boundaries. A register activates a signal only
    from present row-specific evidence. Topic relevance, investigation, and
    token occurrence do not activate it; no active signal is `[]`.
16. Source kinds and artifact classes are typed separately. `.mts` and `.cts`
    have distinct rows; emitted JavaScript is a typed emitted artifact; and a
    generated declaration has a dedicated boundary with generator provenance.
17. The lean contract owns all closed vocabularies, grammars, signal
    definitions, and schema field order. Neither register may authorize a
    token, extend a schema, or define evidence semantics.
18. The corrected registers contain exactly 22 semantic rows
    (`APG71-TS-S001`–`S022`), 14 boundary rows
    (`APG71-TS-B001`–`B014`), and 2 process invariants
    (`APG71-TS-P001`–`P002`). B013 adds `.cts`; B014 adds generated
    declarations. Process ownership is exactly `generic-lifecycle-owner`.
19. Structural policy remains disposition D — deferred. Candidate prose makes
    no structural judgment; numeric whole-file bands, percentiles, length-
    selected language choice, and target/corpus-derived policy remain
    forbidden.
20. At the corrected-proposal checkpoint, eligibility was
    `authoring-eligible-with-narrowing` pending fresh APG72 review. That was not
    terminal acceptance, granted no candidate-authoring authority, and is
    superseded by the terminal rejection above.
21. APG72 has at most one coherent semantic architecture correction. A new
    material defect after this correction requires ADR 0041 Rejected, not a
    second correction.
22. APG71 and APG72 author no TypeScript or JavaScript skill and change no
    projection, catalog, maturity, route, project, release, fixture, maintained
    test, or integration owner.

## Historical corrected-proposal narrowings

Before rejection, any later authoring recommendation would have required fresh
APG72 review to retain all of these narrowings:

1. static semantics, declaration boundaries, and typed routes only; structural
   judgment remains absent;
2. exact aligned compiler-role, version, option, project, source-kind, and
   environment evidence for every version-dependent result;
3. no role-execution claim from package presence, lock resolution, wrapper
   version, or another role;
4. host or TSX composition ownership for embedded and `.tsx` inputs;
5. JavaScript source ownership for checked `.js`;
6. typed emitted-JavaScript and generated-declaration boundaries, including
   generator provenance;
7. a stop for missing option state, decorator regime, exact role identity,
   package/source binding, or other required evidence;
8. moving documentation as explanation only; and
9. no runtime, build, emit, API, editor, loader, or completion conclusion from
   static success.

## Terminal consequences

Fresh APG72 review replayed all 22 semantic, 14 boundary, and 2 process rows
and independently tested compiler roles, exact-version authority, options,
present/required evidence, routes, signals, source kinds, artifacts, rights,
and target conclusions. Its new material findings require rejection. The
corrected architecture remains historical rather than current authoring input,
and no second semantic correction is permitted.

Either result preserves repository state: 29 canonical skills, 29 catalog
rows, 29 projections, 14 stable / 15 provisional, 27 general / 1 ChatGPT-local
/ 28 checked routes, Markdown retained provisional, CSS absent, rejected
JavaScript and CSS ADRs unchanged, public and active v0.4.0 unchanged, and
targets unchanged and unexecuted.

No TypeScript architecture is accepted, no candidate exists, and no APG73 or
successor work is authorized.
