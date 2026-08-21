# APG85 v0.6 Architecture, Discoverability, and Context Budget

## Candidate result

APG85 is the first v0.6 phase and is architecture and documentation only. It
decides ADR 0047 and adds
`docs/architecture/v0-6-skill-ownership-and-context-budget.md` as the normative
contract that APG86 through APG90 consume.

The contract freezes the exact six-profile scope, gives each profile an owns,
does-not-own, and composes-with boundary, and adds a deterministic composition
rule: the narrowest applicable owner answers, ties resolve by a stated layer
order from document through mock library, no profile silently invokes another,
generic process guidance is referenced rather than restated, and a contradiction
between two owners is a reportable contract defect rather than a preference.

The four adjacent web profiles receive explicit anti-catch-all boundaries.
`jsx-language-profile` owns syntax and transform configuration but not React
semantics and not `.tsx` type checking. `react-component-profile` owns component
and hook semantics but disclaims routing, data fetching, metaframework
conventions, styling, accessibility, and bundling by name. `mdx-profile` owns
only the document-to-component seam, leaving the Markdown dialect with
`markdown-language-profile`. `astro-profile` owns execution location, islands,
content collections, and project conventions, and routes React-island semantics
to `react-component-profile`. `vitest-test-profile` owns runner behavior after
Vitest is already selected, leaving generic test discipline with
`implementing-with-test-discipline`. `gomock-test-profile` slots into the
existing Go owner graph without changing either owner recorded there.

## Context budget

The budget is derived from measured evidence rather than chosen by intuition.
The reference population is the 22 existing `-profile` descriptions. Two exceed
twice the population minimum of 173 bytes and are treated as high outliers:
`javascript-language-profile` at 417 and `nodejs-runtime-profile` at 553. The
remaining 20-profile body spans 173 to 326 bytes with a mean of 258.15.

| Constraint | Value | Derivation |
| --- | --- | --- |
| Per-profile floor | 170 bytes | body minimum 173, rounded down to a 10-byte step |
| Per-profile ceiling | 330 bytes | body maximum 326, rounded up |
| Aggregate v0.6 delta | 1,560 bytes | 6 × 260, the body mean rounded up |
| Post-v0.6 total | ≤ 9,527 bytes over 39 skills | 7,967 baseline + 1,560 |

The derivation deliberately uses only a minimum, a maximum, a mean, and a
counting rule. Quartile-based constants were rejected because the same corpus
yields a third quartile of 306 or 309 depending on the estimator, which makes
the resulting budget non-reproducible. As an observed consequence rather than an
input, 20 of the 22 existing profiles already satisfy the band, and the two that
do not are the same two the outlier rule excluded.

The aggregate binds tighter than six ceilings, so the six cannot all be maximal.
The expected post-v0.6 envelope is 8,987 to 9,527 bytes over exactly 39 skills.
Permitted growth is roughly 19.6 percent of the baseline, on the order of 390
tokens on an approximately 2,000-token always-loaded surface.

The budget is expressed in UTF-8 bytes, binding the per-skill description byte
length and `total_description_bytes`. Diagnostic APG014's `Use when ` prefix and
1,024-character cap are unchanged and remain independently in force; the two
rules measure different units, which already diverge in this repository.

The limits bind only the six new v0.6 profiles. Retro-applying the ceiling would
fail two existing descriptions, which would be an unauthorized v0.5 behavior
change made for the convenience of a new rule.

Enforcement has exactly one measurement implementation. The per-skill and
aggregate gates belong to `libexec/apg_skill_library_check.py`, and the
aggregate gate must obtain its totals by calling
`context_footprint_report(blobs=...)` rather than re-summing, so that no second
competing context report can silently disagree with the shipped one. Violations
fail closed with a stable diagnostic identifier and a nonzero exit; there is no
auto-truncation, no silent discovery omission, and no rewriting of a v0.5
description to buy headroom. `apgr skills context-report --json` already exists
in v0.5 and is exercised by APG89 as the installed readback gate rather than
added by it.

## Selection authority and successor sequence

Explicit project selection remains the sole projection authority. Any v0.6
advisory surface must be read-only, must separate observed evidence from
recommendation, must be deterministic, must never run implicitly inside install,
adopt, check, or uninstall, and must never write projection state, links,
exclusions, or configuration. If no such surface can be delivered within those
constraints, none ships and v0.6 remains explicit-selection-only.

The successor sequence is frozen as APG86 (GoMock and Vitest), APG87 (JSX and
React), APG88 (MDX and Astro), APG89 (dogfood, composition, and the context and
readiness gate), and APG90 (publication), with expected topology 35/35/35, then
37/37/37, then 39/39/39, and all six entering as provisional for a v0.6 library
of 14 stable and 25 provisional.

## Preserved product state

APG85 implements no skill body, adds no catalog row or projection, changes no
skill content, maturity, routing, or accepted debt, advances no version, and
performs no publication, deployment, target mutation, or push. Development
remains 33 canonical skills, 33 catalog rows, and 33 projections; 14 stable and
19 provisional. Context remains 33 skills, 7,967 UTF-8 description bytes, 7,955
characters, and zero malformed entries. Known debt remains exactly `CSS-QD-001`
through `CSS-QD-005` and `JS-QD-001` through `JS-QD-005`.

`docs/architecture/web-and-node-profile-family.md` is unchanged. It remains a
terminal record under Rejected ADR 0031 and is cited as historical evidence
only.

## Limitations

The contract is stated but not yet mechanically enforced. No description-band
diagnostic or aggregate assertion exists in the checkout; APG86 adds both. Until
then the budget is a normative table with named future owners, and the current
33-skill measurement is unaffected by it.

The per-profile band is demonstrated by 20 working examples, but none of those
examples had to disclaim three adjacent siblings in the same description. The
four web profiles are the first real test of whether 330 bytes suffices for that
shape. The stated resolution is to sharpen the ownership sentence rather than
widen the band, with the documented amendment path as the escape hatch and the
failing candidate text as the required evidence.

Ownership boundaries are argued from the technologies' structure and from prior
owner evidence, not yet from applied dogfood. APG89 is the phase that can
falsify them.
