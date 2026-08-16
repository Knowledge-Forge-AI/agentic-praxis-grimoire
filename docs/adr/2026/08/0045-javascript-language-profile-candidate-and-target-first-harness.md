# ADR 0045: Narrow JavaScript Core Candidate and Target-First Harness

## Status

Accepted with amendment. APG78 authored one narrow reusable `javascript-language-profile`
candidate, its specification, a navigation-only twenty-four-scenario coverage
record, and a fourteen-case APG-owned target-first fixture. APG79 preserved all
three default correction rounds, but terminal review found two High and two
Medium material defects with no accepted debt. The candidate is
preserved by APG79. APG79A supplied the required separate human continuation
decision and one terminal-proof correction for those four findings. Four-lane
fresh review found zero Critical, zero High, five Medium, and zero Low material
defects with no accepted JavaScript debt. APG79B exercises a separate human
continuation decision and preserves one bounded correction for those five
findings. The candidate is `repair-required-after-apg79b` and nothing is
integrated. APG79C now records the product owner's explicit acceptance of
exactly `JS-QD-001` through `JS-QD-004` as Medium qualification debt for
provisional integration only. That human decision accepts no Critical or High
debt and no language-semantic, normative-source, target-fact, whole-file-owner,
host-result, release, or rollback debt. Fresh APG79C preflight found one separate
unaccepted Medium Test262 identity discrepancy, so integration stopped. This
ADR remained Proposed at that checkpoint. APG79D corrected the source-role
defect but terminal review found the separate report-binding limitation.
APG79E accepts only that exact fifth Medium qualification item and directly
verifies the report. Every ordinary product gate passes with zero Critical,
High, or unaccepted Medium/Low findings. JavaScript is provisionally integrated;
this decision grants no stable maturity, readiness, publication, deployment,
or successor authority.

## Context

APG77D is the exact baseline: `css-language-profile` is provisionally
integrated with human-accepted known debt `CSS-QD-001` through `CSS-QD-005`,
ADR 0044 is Accepted with amendment, and current development stands at 31
canonical skills, 31 catalog rows, 31 projections, 14 stable and 17 provisional
maturity rows, and 29 general, 1 ChatGPT-local, and 30 checked routes.

JavaScript has been attempted twice and rejected twice. ADR 0039 (APG67,
rejected by APG68) and ADR 0040 (APG69, rejected by APG70) both bundled
ECMAScript semantics with a universal host architecture, both selected a
qualitative structural disposition with named signals, and both accumulated
machinery faster than the evidence that could validate it. Their registers ran
to forty and then to thirty-three semantic rows plus ten structural signals,
fifteen composition controls, and four decision layers. In both cases the
material defects clustered in exactly that machinery, and the one-correction
rule then required rejection.

ADR 0042 changed the process that made those outcomes inevitable: candidate
authoring is separated from independent hardening, a repairable material defect
is repair-required rather than automatically fatal, and up to three separately
preserved hardening rounds are available by default.

Freshly verified sources: ECMA-262 17th edition, ECMAScript 2026, remains the
latest completed annual edition — tag object `f7db29f16c5175a93f0d6e8fb27a8e3cb9b97a9e`,
commit `0248456c758431e4bb8e5d26333ff1865123c9cd`; no `es2027` tag exists. The
`es2026-errata` overlay remains non-semantic. The living draft has advanced and
is recorded as refresh evidence only; no candidate clause binds to it. Test262
remains BSD-licensed, non-normative, and was consulted for rights only.

Both read-only targets were freshly pinned and are unchanged. Across both there
is exactly one whole-file JavaScript artifact — a checked `.mjs` configuration
module — plus two host-embedded browser script regions, and zero plain
JavaScript utility or CLI source. That is not a population from which any
numeric structural policy could be calibrated.

## Decision

1. Exact APG77D — decision `38967535918d47af2ab6a1803b907a157776ca41` and
   terminal `0b3682d8b3d42dec629912fceb6555ccc91eaa34` — is the governing
   baseline.
2. ADR 0042 governs this recovery line, including its hardening budget and its
   repair-required rule.
3. ADR 0039 and ADR 0040 remain **Rejected**. Nothing here revives them.
4. APG67 through APG70 remain immutable historical falsification evidence,
   usable as source leads, known-risk hypotheses, and process lessons — never as
   candidate text, oracle, or authority.
5. JavaScript is the next candidate priority after TypeScript and CSS.
6. The product orientation favours JavaScript for short, simple utilities and
   TypeScript for larger or more complicated ones, but **project design — not
   the language profile — chooses between them**.
7. Node.js remains a later, separate runtime and stack owner. This ADR creates,
   implies, and reserves no Node profile.
8. The candidate owns narrow ECMAScript language semantics for an **established**
   JavaScript source region, and establishing that region is an input rather
   than a result.
9. Parse goal, strictness state, edition or draft authority, whole-file owner,
   and consequence-bearing host inputs must all be evidenced before a dependent
   conclusion.
10. Node, browser, DOM and Web APIs, module loading and resolution, build and
    transformation, TypeScript, JSX, React, MDX, Astro, security, architecture,
    and deployment remain explicit non-owners with named receiving owners.
11. Selection (`selected`, `embedded-route`, `route-to-owner`, `non-trigger`)
    and the exact four-value Response axis (`proceed-routine`,
    `inspect-before-judgment`, `bounded-local-decision`, `stop-and-escalate`)
    remain disjoint vocabularies. `route-to-owner` is never a response.
12. Script and Module language semantics are separate from host filename and
    package selection. Extensions and a package `type` field are evidence
    inputs, not ECMAScript rules.
13. `.cjs` and CommonJS remain Node-defined boundaries. `.cjs` is not a
    standardized ECMAScript source goal, and wrapper bindings are Node-owned.
14. ECMAScript module binding and evaluation semantics are separate from
    specifier resolution and loading, which route to the module-loader owner.
15. Checked status does not choose or transfer whole-file ownership. An ordinary
    checked JavaScript source may remain JavaScript-owned; a standalone
    JavaScript configuration module may remain project-configuration-owned while
    JavaScript is selected for its bounded ECMAScript decision. TypeScript joins
    only the checking decision after exact selection and invocation evidence.
16. A pure ECMAScript CLI core is separate from its Node adapters and I/O; a
    correct core result is not a working command.
17. **Structural policy is deferred.** This is a decision, and it is grounded in
    the thin target evidence as well as in the rejected history.
18. No numeric file, line, statement, function, complexity, or percentile
    threshold is authorized, and no automatic migration in either direction.
19. The candidate has exactly twenty-four navigation scenarios,
    `APG78-JS-001` through `APG78-JS-024`, mapped to twenty-five stable clauses.
20. The APG-owned fixture has exactly fourteen cases, `APG78-FX-001` through
    `APG78-FX-014`, over seventeen source files with no unowned file.
21. APG78 adds **no** current integration owner: no catalog row, projection,
    maturity row, capability route, project selection, release owner, or
    maintained test owner.
22. CSS known debt `CSS-QD-001` through `CSS-QD-005` remains exact and
    unchanged, and stable CSS maturity remains blocked by its four Medium items.
23. APG79 independently hardens this candidate and preserves its repair
    checkpoint, reconstructing all scenarios and fixture cases without using
    APG78 artifacts as an oracle.
24. APG78 grants APG79 no authority.
25. APG79A used separate explicit human continuation authority for exactly H1,
    H2, M1, and M2. Its immutable correction improved those surfaces, but fresh
    review found five Medium defects across CommonJS Selection, target-only
    schema fields, diagnostic privacy, wrapper-bypass enforcement, and required
    path/output mutation evidence. No post-review correction is authorized.
26. APG79B uses separate explicit human continuation authority for exactly
    those five findings. Standalone CommonJS artifacts remain Node-owned with
    decision-scoped JavaScript `selected`; target commitments are target-row
    only; one process owner validates closed output contracts without returning
    raw streams; named maintained process forms are AST-checked; and post-run
    resolved-path replacement plus every material output field have rejecting
    mutations. Fresh immutable-correction review remains required.
27. APG79B fresh immutable review found four unique Medium defects: incomplete
    two-artifact CommonJS invariant closure; raw streams reachable through
    traceback locals and exception context; annotated-alias and module-rebinding
    process bypasses; and missing same-type wrong-value mutations for four
    root-scalar output contracts. No debt is accepted. Integration is blocked,
    this ADR remains Proposed, and the candidate is repair-required without
    rejection or removal.
28. APG79C exercises ADR 0042's existing human-debt authority for exactly those
    four qualification limitations. They are current and discoverable as
    `JS-QD-001` through `JS-QD-004`; all block stable maturity but do not block
    provisional integration under their exact safe operating restrictions.
    JavaScript remains unintegrated and this ADR remains Proposed until the
    ordinary source, target, product, regression, release, and rollback gates
    pass. No further proof-of-proof correction is authorized by this decision.
29. APG79C source preflight found current official Test262 `main` differs from
    the APG79B terminal and APG79C baseline identity. Test262 is non-normative,
    rights-only evidence and unused as an oracle, so the discrepancy has no
    semantic, target, owner, or execution consequence. It remains one separate
    unaccepted Medium source-evidence blocker. Integration stops, this ADR stays
    Proposed, JavaScript remains repair-required and unintegrated, and APG80 is
    not recommended.

## Consequences

- The `javascript-language-profile` leaf, specification, coverage record, and
  fixture are provisionally integrated through the existing product owners at
  32 canonical skills, 32 catalog rows, and 32 relative projections. The
  preserved APG78 branch remains historical evidence of its truthful
  transitional 32/31/31 authored state.
- Maturity is 14 stable and 18 provisional; routes are 30 general, one
  ChatGPT-local, and 31 checked. CSS, TypeScript, and Markdown remain
  provisional, and JavaScript cannot advance to stable while any of
  `JS-QD-001` through `JS-QD-005` remains current.
- Deferring structural policy leaves a real gap: the profile can observe that a
  utility entangles host and language concerns but cannot say when that warrants
  restructuring. That gap is deliberate, and closing it requires separate human
  authority and better evidence than one configuration module provides.
- Several named receiving owners — node-runtime, browser-platform,
  module-loader, jsx — do not yet exist. Until they do, a route to them is a
  stop with a named addressee rather than a handoff to a live owner. This is the
  candidate's most significant practical limitation.
- Corrected historical, published, and active v0.4.0 and both read-only targets
  are unchanged and unexecuted.
- Before the APG79D source-role correction and APG79E human-debt decision,
  APG79 used all three default hardening rounds. APG79A exercised a new human
  continuation decision and preserved one immutable correction. Fresh review
  left five Medium material defects. APG79B exercises a new bounded continuation
  and preserves the five-finding correction. Fresh review found four unique
  Medium material defects, so the candidate is
  `repair-required-after-apg79b`; ADR 0045 remains Proposed, and no
  JavaScript integration is accepted by those phases. APG79C human-accepts only
  the four named Medium qualification limitations for possible provisional integration;
  the candidate remains repair-required and unintegrated while this ADR is
  Proposed. APG79C preflight found one separate unaccepted Medium source-fact
  blocker, so the product gates did not open and integration remains absent.

## APG79D source-role correction

APG79D corrects that source-evidence model forward without rewriting the
APG79B report. The APG79 reviewed object remains the historical pin; a fresh
default-branch head is mutable refresh evidence; and the exact Test262 licence
object owns the copying-and-rights boundary. Test262 is not normative,
semantic, compatibility, or implementation authority, and no Test262 corpus
body is read, copied, executed, vendored, or retained as a path inventory.
Ordinary head drift is non-blocking while the rights object and no-corpus role
remain unchanged. A rights-role, licence-object, copied-expression, or corpus-
use change blocks for fresh review. The false APG79B object assertion is
preserved as historical evidence, superseded as current authority, and is not
accepted debt. Terminal review finds that the maintained historical-report-
rewrite mutation does not bind the managed report bytes. This ADR remains
Proposed, JavaScript remains repair-required and unintegrated, and further
correction requires a new human decision.

## APG79E human-debt decision

APG79E exercises ADR 0042 human product authority for exactly one additional
Medium qualification limitation, `JS-QD-005`. The maintained historical-
report-rewrite mutation does not bind the APG79B managed-report path, record
identities, or full-file digest. The canonical report is nevertheless directly
verified through EOF at SHA-256
`9b56d503039c2907d371b37b72451b6e0b71cca41aa0cd23c074453229698827`,
including regenerated Git-show payloads and associated operational records.
The report remains immutable historical evidence rather than semantic, source,
target, runtime, release, or deployment authority.

`JS-QD-005` blocks stable maturity but does not block provisional integration
under the exact direct-verification workaround in the current known-debt owner.
It does not repair the maintained proxy. APG79E accepts no Critical or High
debt and no JavaScript semantic, normative-source, target, owner, host-result,
release, rollback, Test262-rights, or Test262-corpus debt. `JS-QD-001` through
`JS-QD-004` and `CSS-QD-001` through `CSS-QD-005` remain exact.

Every ordinary integration, regression, release, historical-exclusion,
public-preservation, and disposable rollback gate passes with zero Critical,
High, or unaccepted Medium/Low findings. ADR 0045 is therefore Accepted with
amendment and JavaScript is `provisionally-integrated-with-known-debt` under
exactly `JS-QD-001` through `JS-QD-005`. Stable maturity remains blocked;
structural policy remains deferred; APG80 is recommended but not begun.
