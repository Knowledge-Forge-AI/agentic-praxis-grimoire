# APG57 Web and Node Architecture Review

## Outcome

APG57 independently verified APG56, applied one coherent correction, and
submitted the corrected package to fresh non-author review. That review found
material architecture and numerical-evidence defects. Under the one-correction
contract, [ADR
0034](../adr/2026/07/0034-web-and-node-profile-family-reconstruction-and-authoring-sequence.md)
is **Rejected**. ADR 0031 remains Rejected, all candidates and bands remain
deferred, no skill was authored or integrated, and no successor began.

## Evidence and factual corrections

The exact APG56 object, parent, managed reports, and delivered Claude branch
were verified. Every consumed APG52 compact file matched its committed hash;
schema-bearing files use version one, the rules file is intentionally
schema-less, and the two-run result remains byte-identical. Both pinned target
commits and trees were re-inspected read-only and were neither executed nor
mutated.

APG56's table contained six proposed-authoring-eligible and four deferred
candidates, despite repeated five/five prose. Both targets resolve Astro
7.1.3; the website declares `^7.0.2`. The theme's original baseline, exact
post-baseline AGPL notice scope, package metadata, and
commercial/NOTICE/CLA surfaces remain distinct. TypeScript source and docs,
JSX, CommonMark/GFM, React source/docs, and CSSWG/W3C rights boundaries were
separately reverified.

## Growth review and corrected-state defects

An independent standard-library reviewer reproduced the APG56 thresholds and
examined purpose fit, tail support, family size, dominance, and
leave-one-family-out behavior. The substantive class review found:

| Class | APG56 values | Reviewed result |
| --- | --- | --- |
| JavaScript module | 399/1061/3402 | method fails the 1,000-line purpose control |
| TypeScript module | 180/1604/1942 | method fails purpose and anchor-removal controls |
| TypeScript declaration | 140/890/1453 | one tail dominates; unstable |
| TypeScript configuration | 10/25/26 | physical lines are unsuitable |
| Node runtime/CLI | 174/861/1462 | method fails the 800-line purpose control |
| CSS stylesheet | 133/663/929 | family robustness fails |
| Markdown document | 164/1432/3474 | ordinary and long-form structure is conflated |
| Astro component | 133/169/390 | small-family and anchor sensitivity fail |
| Scoped CSS section | none | insufficient evidence |
| JSX/TSX | none | insufficient evidence |
| MDX document | none | insufficient balanced evidence |

No band was accepted and no replacement value was calculated. TypeScript
configuration option D—project-owned structural growth with TypeScript
semantic ownership—was the reviewed direction.

Fresh corrected-state review then found the reviewer package itself
unacceptable:

- several partial target samples claim individual completeness while exact
  placement is unavailable;
- threshold intervals omit logically mandatory minimum/maximum bounds and can
  report zero artifacts above a threshold even when the observed maximum is
  above it;
- the executable reproduction gate compares only thresholds or base
  ineligibility, not the complete APG56 class projection; and
- focused tests omit those truthfulness branches.

The quantitative output is therefore failure evidence, not accepted policy.

## Candidate, scenario, and slice review

The attempted corrected ledger derived zero eligible, eight
deferred-evidence, and two deferred-policy candidates. Corrected-state review
found that it assigned the single JSX/TSX whole-file class to both TypeScript
and JSX rows without clearly distinguishing TypeScript's non-additive
semantic route. The ledger is not accepted.

The eighty APG56 IDs remain unique and continuous candidate-boundary evidence.
The five APG57 supplemental entries are not accepted scenarios because they
omit the established scenario fields; the broad-owner entry also names no
concrete owner. One-count, semantic-risk, exclusions, legacy-fix,
adjacent-gap, and Policy A constraints remain prior boundaries.

W1–W4 are deferred. W3 is not authorized as a combined
JavaScript/TypeScript/Node batch. There is no eligible first slice.

## Preservation and boundary

Development remains 28 canonical skills, 28 catalog rows, 28 projections,
fourteen stable and fourteen provisional. Corrected public and active v0.4.0
remain unchanged. No catalog row, route, maturity state, dependency, fixture,
executable, release row, target repository, or active installation changed.
Further evidence, architecture, authoring, readiness, publication, deployment,
or successor work requires separate maintainer authority.
