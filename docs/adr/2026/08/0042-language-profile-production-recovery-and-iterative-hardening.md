# ADR 0042: Language-Profile Production Recovery and Iterative Hardening

## Status

Accepted

## Context

APG72 is the accepted baseline. ADRs 0031, 0034, 0035, 0036, 0039, 0040, and
0041 remain Rejected and historically truthful. Those reviews exposed real
source, rights, owner, route, compiler-role, signal, option, artifact, and
evidence defects and preserved useful corrections. Their shared terminal
pattern also reflected an experimental lifecycle in which a fresh material
finding after the sole correction forced rejection.

That bounded rule was useful for testing whether a proposed architecture could
survive one independent correction. It is unsuitable as the controlling
production-recovery lifecycle because another repairable defect can block
integration without proving a product unwanted, impossible, or fundamentally
unfit. New human product authority makes TypeScript essential, CSS and
JavaScript desirable, JSX deferred, and TypeScript 7 the intended primary
compiler generation. The maintained theme target's older TypeScript snapshot
is migration evidence, not the destination.

APG73 therefore adopts a production recovery charter and an iterative
hardening contract. It authors and integrates no language profile.

## Decision

1. APG72 is the baseline.
2. All rejected CSS, JavaScript, and TypeScript ADRs remain Rejected.
3. One-correction automatic rejection is retired for production recovery.
4. One coherent correction remains the unit of one hardening round.
5. Three rounds are allowed by default.
6. A new material defect normally produces `repair-required`.
7. Human authority controls priority, debt acceptance, continuation,
   narrowing, unfitness, abandonment, and rejection.
8. Codex controls evidence truth, severity, gates, rollback, and technical
   recommendations.
9. Critical and High defects block integration.
10. Medium and Low debt may be accepted only explicitly.
11. Terminal rejection and removal require human authority.
12. TypeScript is essential.
13. CSS and JavaScript are desirable.
14. The older theme TypeScript snapshot is migration evidence.
15. TypeScript 7 is the intended primary generation.
16. TypeScript 6 compatibility is role-bound and temporary.
17. Package presence never proves role execution.
18. Target-first validation outranks exhaustive theory.
19. Structural policy is deferred for the first TypeScript and JavaScript
    product slices.
20. APG74 through APG77 are the intended sequence.
21. APG73 integrates no profile.
22. No successor execution authority is granted.
23. Evidence is consequence-bearing and proportionate; independent free-form
    review prose is not a product API or routine release owner.
24. Machine checks own closed structured consequences and executable behavior;
    human review owns explanatory prose sufficiency.
25. Exact structured disagreements receive compact adjudication, while
    equivalent prose requires no item-level provenance.
26. Historical phase evidence remains auditable without remaining current
    release authority, and disproportionate proof mechanisms are narrowed or
    retired.
27. Current authored evidence, public output, and new records contain no copied
    target expression. Exact private Git patches may preserve removed bytes as
    historical forensic evidence without making them current authority or
    permitting their reuse.

The controlling public owners are the
[language-profile production recovery charter](../../../governance/language-profile-production-recovery-charter.md)
and the
[iterative hardening contract](../../../specs/language-profile-iterative-hardening-contract.md).

## Consequences

- A repairable Critical or High defect blocks integration and normally
  preserves the candidate in `repair-required`.
- `fundamentally-unfit-pending-human-decision` is a technical recommendation,
  not automatic rejection or removal.
- A provisionally integrated profile has zero Critical and High defects,
  current target evidence, proven rollback, and explicit human acceptance of
  every remaining Medium or Low debt.
- Package or lockfile presence cannot stand in for an invoked compiler role.
  Each role records its exact version, selection, invocation evidence, state,
  and retirement condition.
- TypeScript 6 may remain temporarily only for a concrete role that still
  requires it. It is not the universal compatibility target.
- Provisional integration does not confer stable maturity.
- Proportionate evidence keeps exact source, target, semantic, route, stop,
  lifecycle, release, and rollback gates while retiring exhaustive prose
  provenance as a routine integration dependency.
- An authoritative private Git-show remains exact even when its deletion patch
  contains removed historical bytes; it is not a source for new evidence.
- CSS and JavaScript recovery use new ADRs and preserve rejected history.
- APG74 is recommended as a separately authorized TypeScript candidate and
  intended-state harness phase. This ADR does not begin it.

## Alternatives rejected

### Keep automatic rejection after one correction

Rejected because it confuses an integration block with terminal product
disposition and gives review order more authority than defect consequence.

### Allow unlimited correction within one round

Rejected because it hides oracle drift, correction history, and reviewer
independence. Corrections remain bounded by separate rounds.

### Let Codex waive High defects for an essential product

Rejected. Essential priority affects sequencing, not evidence truth or safety.

### Treat the current older compiler snapshot as the destination

Rejected. It is a migration baseline; future work selects an exact current
TypeScript 7 patch and records any independently required temporary TypeScript
6 role.

## Verification boundary

APG73 verifies exact APG72 ancestry, report completeness, fetched branch
parity, rejected ADR and Markdown preservation, current integration counts,
profile absence, public and active release identity, read-only target identity,
record identity, links, privacy, rights, structure, change size, whitespace,
and the complete diff. It does not run profile tests, target commands, the full
APG regression suite, integration, readiness, publication, deployment, APG74,
or another successor.
