# ADR 0039: JavaScript Language-Profile Architecture and Lean Validation

## Status

Rejected (APG68). Two independent semantic lanes found genuinely material
defects after the sole correction. Eligibility is
`not-applicable-rejected`; APG69 is not recommended. This ADR grants no
candidate-authoring, readiness, publication, deployment, or successor
authority.

## Context

APG66D is the exact baseline: the Markdown language profile remains
retained provisional under ADR 0037 and ADR 0038 (both Accepted with
amendment), the CSS decisions of ADR 0031, 0034, 0035, and 0036 remain
Rejected with no CSS surface present, and development stands at 29
canonical skills, 29 catalog rows, 29 projections, 14 stable and 15
provisional maturity rows, and 27 general, 1 ChatGPT-local, and 28
checked routes. APG67 begins the JavaScript profile line with
architecture only: it authors no skill, changes no integration owner,
and leaves development main at exact APG66D.

Exact-source verification established ECMA-262, 17th edition —
ECMAScript 2026, published June 2026 with the HTML render normative — as
the stable annual reference, pinned to the `es2026` tag of the tc39
source repository. The live repository head has advanced to the
ECMAScript 2027 draft and is moving refresh evidence only. Test262 is
bounded validation and corpus evidence under its verified Ecma BSD-style
license (not the CC0 orientation the assignment expected) and is never
normative authority. The two pinned read-only targets contain exactly
one whole-file JavaScript artifact — a small handwritten ESM
configuration module — so target dogfood cannot calibrate numeric
structural policy, and the APG52 corpus supplies descriptive breadth
only.

## Decision

1. A reusable `javascript-language-profile` owns ECMAScript language
   semantics only after the effective source-text goal and
   implementation context are established.
2. JavaScript, TypeScript, and Node.js are separate owners and are never
   collapsed. TypeScript and JSX remain whole-file adjacent owners:
   `.ts`, `.tsx`, and `.jsx` files are JavaScript whole-file
   non-triggers.
3. Authority is question-specific. The ECMAScript 2026 annual HTML
   controls covered normative semantics; exact host configuration
   establishes source goal; exact parser, runtime, and transpiler evidence
   establishes availability and observation; owner evidence establishes
   divergence; and project, repository, and security policy establish
   support and permission. Annex B applies only under an established
   context; later drafts have no authority without explicit selection plus
   implementation evidence. The exact ES2026 errata is a non-semantic
   correspondence overlay; a later consequence-bearing corrigendum stops
   for explicit dual-source disposition.
4. ECMAScript module syntax and evaluation are separate from host
   resolution and loading. CommonJS is Node/runtime-owned and is not
   ECMA-262 module semantics. Browser, DOM, and Web APIs are not
   ECMAScript built-ins.
5. Structural policy has one exact disposition: qualitative
   responsibility-and-complexity-first (disposition C), with fifteen
   named signals, sixteen purpose controls retained as an exact canonical
   preimage and digest, no numeric whole-file bands, and line count as descriptive
   input only. No numeric policy is inherited from the rejected APG50
   and APG57 work, and no threshold is derived from corpus percentiles.
6. The lean validation contract owns closed owner, selection, response,
   route, rollback, source-boundary, structural-signal, and semantic-signal
   vocabularies; the frozen
   register contains exactly forty rows — thirty-eight candidate-semantic
   scenarios and two review-process invariants — in a sixteen-field
   schema. Selection, response, and route are separate axes, routing
   never lowers severity, and the register does not authorize its own
   vocabulary.
7. Full prose sufficiency remains human review: machine-checkable claims
   stay narrower than semantic review and every future scripted check
   must be mutation-negative, inheriting the Markdown evidence
   corrections.
8. Authoring eligibility is `not-applicable-rejected`. The ten proposed
   narrowings remain historical evidence only and grant no future contract.
9. APG67 authors no skill and no integration owner: no
   `javascript-language-profile` skill, projection, catalog, maturity,
   route, project, release, fixture, or test surface exists or changes.
10. APG68 independently reverified exact source, rights, target, and corpus
    objects; replayed all thirty-eight semantic rows and both process
    invariants; applied one coherent correction; froze the corrected bytes
    before fresh review; and terminally rejected this ADR when fresh review
    found material response, route, signal, and source-boundary defects.

## Consequences

- The JavaScript architecture, lean contract, and frozen register are
  historical rejected evidence, not current architecture inputs;
  development advances through exact APG67 and APG68 while
  integration counts remain 29/29/29 with 14 stable / 15 provisional
  maturity and 27/1/28 routes.
- The Markdown candidate, its ADRs, the CSS rejections, and corrected
  public and active v0.4.0 are unchanged.
- The user's JavaScript/TypeScript/Node division — JavaScript for short
  simple utilities, TypeScript for larger contract-heavy utilities,
  Node.js for runtime and script concerns — is incorporated as project
  input, never as a numeric language law; the profile identifies
  pressure and routes migration to project design.
- APG69 is not recommended. Any future architecture requires new human
  authority rather than inheriting the rejected contract. APG68 authors no
  skill and changes no catalog, maturity, projection, route, release,
  fixture, or test owner.
- Thin target dogfood and descriptive-only corpus breadth remain named
  limitations. APG68 closed the APG67 tree-hash limitation by fetching and
  reading the exact annual, errata, and Test262 Git objects.
