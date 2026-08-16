# ADR 0029: v0.5 Evidence, Go Testing, and Web Profile Roadmap

- Status: Accepted with amendment
- Date: 2026-07-26
- Proposed in: APG44
- Decided in: APG45
- Relates to: ADR 0025 (Rejected), ADR 0026 (Accepted and controlling),
  ADR 0027 (Rejected), APG44 fact-check comparative analysis

## Context

The maintainer approved a v0.5 agenda with three workstreams: analysis of
the external `petar-nauka/fact-check-skill` repository for evidence and
review improvements; reconsideration of the matryer/is Go test component
and Go stack question; and a web/Node profile family dogfooded against two
Knowledge Forge AI repositories. APG44 performed the fact-check analysis,
froze ten clean-room recommendations with author dispositions, and recorded
the roadmap. Consequential ordering and ownership questions require a
durable decision record: what depends on what, which additions are
evidence-tested rather than predetermined, and where the Node.js runtime
boundary sits relative to the JavaScript and TypeScript language owners.

## Decision

1. **Dependency order.** v0.5 proceeds as: APG44 fact-check analysis → APG45
   independent review and terminal dispositions → separately authorized
   implementation of only accepted recommendations; then Go test-component
   dogfood and reconsideration under the improved evidence rules; then bounded
   web and Node owner design and dogfood; then separately authorized readiness
   and publication. Analysis, review, implementation, and release remain
   distinct authority boundaries.
2. **Evidence-tested Go retention.** matryer/is and any stack owner remain
   evidence-tested candidates, not predetermined additions. Retention
   requires that the three named dogfood repositories expose recurring
   composition work not already owned by `go-test-profile`,
   `go-cmp-test-profile`, project-local conventions, or a corrected
   matryer/is profile. ADR 0025, ADR 0026, and ADR 0027 dispositions stand
   unless a later authorized phase decides otherwise on that evidence.
3. **Node.js runtime as a separate owner.** `nodejs-runtime-profile` owns
   Node-specific runtime and CLI behavior for either language.
   `javascript-language-profile` and `typescript-language-profile` own
   their actual artifact semantics. The maintainer's
   JavaScript-for-simple/TypeScript-for-complicated preference is project
   policy, not an APG-owned complexity threshold.
4. **Web-family design graph.** JavaScript supplies a design input to
   independent TypeScript, Node.js runtime, and JSX owners. TypeScript has no
   Node.js semantic dependency; it connects to JSX for the TSX boundary and to
   Node.js only when runtime behavior is material. CSS, Markdown, and React are
   independent candidate roots. JSX-to-React, React-to-MDX, and React-to-Astro
   relationships are conditional integrations: React can be used without JSX,
   and MDX or Astro can be used without React. Vitest combines applicable
   JavaScript or TypeScript semantics with Node.js runtime behavior. Arrows
   express analysis and design inputs only; direct selection and no mandatory
   profile chain are preserved.
5. **Bounded dogfood gates retention.** Every web profile is retained only
   on bounded dogfood evidence in the two named repositories. No
   Starlight-specific profile is created unless that dogfood demonstrates a
   coherent owner not covered by Astro, Markdown/MDX, React, CSS, and
   project policy.
6. **No decision by implication.** This ADR accepts no profile and no maturity
   or release decision. APG45 recommendation dispositions are implementation
   inputs, not current behavior. A roadmap entry allocates no phase ID and
   authorizes no execution.

## Consequences and boundary

Later authorized v0.5 phases inherit a stable ordering rationale and owner
boundaries without re-deriving them, and disputes about matryer/is or a
Starlight profile resolve against recorded evidence rules rather than
preference. APG45's accepted recommendations remain pending implementation.
Exact adapters, build tools, package managers, browser environments, and target
frameworks remain project-owned.

## Alternatives considered

* Web profiles before the Go reconsideration: rejected — the smaller Go
  workstream exercises the improved evidence rules first and avoids two
  concurrent dogfood efforts.
* One combined JavaScript/TypeScript/Node owner: rejected — it would blur
  runtime versus language semantics and force browser-context JavaScript
  through Node guidance.
* Predetermined matryer/is retention (or removal): rejected — both
  directions have failed evidence review before (ADR 0025, 0027); only
  fresh bounded dogfood should decide.
* A Starlight-specific profile in the initial family: rejected pending
  dogfood evidence of a coherent uncovered owner.
* No ADR (roadmap document only): rejected — the ordering and the
  Node/JavaScript/TypeScript boundary are consequential architecture
  decisions that later phases will otherwise re-litigate.
* Linear JavaScript → Node.js → TypeScript → JSX ordering: rejected in APG45
  because it falsely implies a Node dependency for TypeScript semantics and
  omits the TSX boundary.
* Universal React ownership for JSX, MDX, or Astro: rejected in APG45 because
  those are conditional integrations, not universal triggers.
