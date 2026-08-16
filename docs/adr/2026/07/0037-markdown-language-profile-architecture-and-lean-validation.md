# ADR 0037: Markdown Language-Profile Architecture and Lean Validation

- Status: Accepted with amendment
- Date: 2026-07-31
- Proposed in: APG63
- Decided in: APG64 independent Codex peer review
- Relates to: ADR 0012 (Accepted; language-profile contract),
  ADR 0029 (Accepted with amendment; Policy A unchanged),
  ADR 0031 (Rejected; unchanged), ADR 0034 (Rejected; unchanged),
  ADR 0035 (Rejected; unchanged), ADR 0036 (Rejected; unchanged)

## Context

APG62 terminally rejected the CSS candidate: ADR 0031, ADR 0034, ADR 0035,
and ADR 0036 remain Rejected, no current CSS surface exists, and CSS is not
reopened by this proposal. The CSS sequence remains process evidence — most
directly that exact action lists become brittle when harmless bookkeeping
and ownership-bearing behavior are treated identically, and that corrected
candidate state must be preserved before terminal deletion.

Markdown is the strongest remaining independent authoring direction:
coherent selected-dialect document semantics, nineteen exact target Markdown
paths across both pinned target repositories, the widest remaining
multi-family corpus evidence, and exact separately pinned CommonMark and GFM
specification baselines. APG63
reverified both specification objects and their CC BY-SA 4.0 document
rights at exact objects, with implementation code terms recorded as
separate non-authority.

## APG63 proposal

Adopt the [Markdown language-profile architecture](../../../architecture/markdown-language-profile-architecture.md)
and the [lean validation contract](../../../specs/markdown-language-profile-lean-contract.md):

1. Owner: a reusable `markdown-language-profile` owning selected-dialect
   document semantics, narrowed as the architecture records (syntax and
   resolution owned; link-target validity, asset policy, fenced-content
   language, and tool selection excluded).
2. Explicit non-owners: editorial quality, content strategy, factual
   correctness, product policy, HTML semantics and accessibility outcomes,
   browser runtime, MDX and JSX, Astro and Starlight, frontmatter schema,
   plugin and pipeline selection, formatter/linter/link-checker choice,
   build, preview, deployment.
3. Dialect: CommonMark 0.31.2 base plus evidence-selected GFM extensions;
   the repository's actual parser always wins; unsupported syntax routes
   to its owner; MDX is a separate owner and non-trigger; frontmatter is a
   recognized boundary, not schema ownership.
4. Raw-HTML, frontmatter, and MDX/host boundaries as the architecture
   states: recognition and pass-through owned; semantics, schema, and
   whole-file MDX excluded; no HTML profile inside Markdown.
5. Structural policy: disposition C — qualitative structure-first, no
   numeric whole-file bands; named observable signals mapped to the shared
   warning levels; line count descriptive only; ten frozen purpose
   controls constrain application.
6. The rejected APG56 Markdown values are not reused: they were corpus
   percentile artifacts whose evidence package failed corrected-state
   review, and percentile derivation of normative policy is forbidden;
   target upper tails do not define maintainability policy.
7. Validation: a lean thirty-six-scenario invariant register
   (APG63-MD-001…036) with closed owner and response vocabularies —
   deliberately not CSS's sixty-row exact-action map. Ownership,
   permission/stop, and safety/rollback behavior are exact; benign
   bookkeeping is recommended-only unless consequence-bearing.
8. Generic candidate lifecycle stays outside Markdown semantic prose; the
   register's lifecycle group states only unintegrated-until-decision,
   retained-owner closure, and rejection-preserves-history.
9. Corrected-state evidence must be preserved in later review: corrected
   hashes, the exact correction patch, corrected tests or canonical
   vectors, and reviewer binding to those hashes; on rejection, a compact
   publication-excluded correction artifact survives terminal deletion.
10. Severity: material / ordinary / note with the one-correction rule;
    a genuinely new material defect after the sole correction rejects.

## APG64 corrected proposal under review

APG64's complete initial review found one coherent material defect set in the
proposal above. The sole permitted semantic correction makes these amendments
without creating a candidate skill or integration surface:

1. CommonMark 0.31.2 is the applicable base reference and GFM 0.29 is an
   extension reference for its five specified extension families; they are
   not represented as one synthetic version. The actual configured parser,
   exact version, and enabled extensions remain authoritative.
2. The target corpus is all nineteen tracked Markdown paths: three maintained,
   one generated, three tool-boilerplate, seven fixture/demo, three
   legal/governance, one agent-instruction, and one symlink. The former seven
   paths were a mixed convenience sample, not a canonical corpus.
3. Both targets configure the Astro 7 Satteri processor path and distinguish
   it from GitHub rendering. Theme lockfile/importer drift limits the claim to
   intended or resolved configuration; no runtime execution is inferred.
4. Selection, response severity, and routing are separate closed axes. Every
   register row has one exact primary owner, one unconditional primary
   decision, one of four response severities, and an exact receiving route or
   `not-applicable`.
5. Rows 001–034 are candidate-semantic scenarios. Rows 035–036 are review
   process invariants owned by `generic-lifecycle` and are not candidate
   obligations.
6. The fourteen structural signals carry explicit evidence classes and
   false-positive controls. `whole-document-review-boundary` is qualitative,
   and line count remains descriptive only.
7. Exactness is consequence-based: an omitted or extra observation is
   material only when it changes ownership, permission/stop, safety/rollback,
   rights/privacy/source integrity, structural completeness, or truthful
   completion.
8. The rights conclusion is bounded: no copied or adapted CommonMark, GFM, or
   target expression was identified. It is not legal advice or a universal
   future guarantee.
9. Corrected-state review binds independent results to the corrected core
   hashes, an exact full-index patch and digest, and canonical replay vectors.

## APG64 terminal disposition

Accepted with amendment. APG64 collected the complete initial material set,
applied the one coherent correction above, froze the corrected core and exact
full-index patch, and then obtained fresh non-author reviews. Independent
36/36 replay reproduced one ownership, selection, response, and routing tuple
per scenario; the source/rights/parser/target review independently confirmed
the corrected hierarchy and complete inventory. Neither lane found a new
material defect. The architecture is therefore the current accepted input,
with authoring eligibility `authoring-eligible-with-narrowing` and no skill,
integration, or successor authority.

The pre-disposition corrected hashes, exact patch digest, canonical vector,
reviewer bindings, and terminal-only delta are preserved in the
publication-excluded APG64 evidence bundle. The terminal status update changes
no semantic rule from the independently reviewed corrected state.

## Eligibility and phase boundary

- Authoring eligibility: authoring-eligible-with-narrowing. The smallest
  later slice is one Markdown leaf, one candidate specification, one
  compact invariant map or scenario link, and one architecture input — no
  MDX, HTML, or Starlight skill.
- APG63 authors no skill and integrates nothing: no catalog, maturity,
  route, projection, project, release, test, or active surface changes;
  development remains 28/28/28 with 14 stable / 14 provisional.
- APG64 independently reviewed this architecture and accepted it with the
  amendments above. APG63 did not decide it.
- A later Markdown candidate requires separate human authorization; this
  ADR grants none.

## Alternatives considered

- One numeric whole-file policy: rejected — no evidence-supported values
  exist; tight bands falsely escalate legitimate long-form documents,
  loose bands are vacuous, and prior review found Markdown line metrics
  unsuitable without separately frozen structure.
- Split numeric policy by document class: rejected now — some classes are
  deterministic, but per-class values lack evidence and class invention to
  obtain thresholds is the known failure mode.
- Recreating the CSS exact-action contract for Markdown: rejected — the
  sixty-row design's uniform exactness over bookkeeping actions caused the
  CSS rejection; the lean model prices exactness by consequence.
- Deferring Markdown entirely: rejected — owner coherence, sources,
  rights, boundaries, and a complete structural policy are all in hand.

## Consequences

- A later authoring phase has one frozen, candidate-independent contract
  to answer to, and a later review phase has an explicit evidence and
  severity model.
- Rejecting this ADR removes only APG63's architecture, contract, and
  register surfaces while preserving complete history (independent
  rollback); no maintained executable, test, catalog, release, target,
  public, or active surface depends on it.
- No implication is created for JavaScript, TypeScript, Node, JSX, React,
  MDX, Astro, or Vitest; React and Vitest remain under ADR 0029 Policy A.

## Deferred decisions

- Any Markdown candidate authoring, integration, maturity, publication, or
  deployment.
- Every other Web/Node candidate.
