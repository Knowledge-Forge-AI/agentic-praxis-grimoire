# ADR 0031: Web and Node Profile-Family Ownership and Authoring Sequence

- Status: Rejected
- Date: 2026-07-27
- Proposed in: APG50
- Decided in: APG51
- Relates to: ADR 0029 (Accepted with amendment; unchanged)

## Context

APG50 proposed ten web and Node profile owners, source baselines, sixty
scenarios, structural calibration, adjacent-gap dispositions, and authoring
slices. APG51 independently reverified the exact targets and primary sources,
traced TypeScript consumers, measured calibration corpora, and applied the one
authorized forward architecture-correction pass.

That pass produced a substantially stronger candidate design: direct owner
selection, consumer-specific TypeScript evidence, separate semantic-risk and
handwritten-growth axes, one-count mixed artifacts, Policy A for React and
Vitest, separate browser/HTML/accessibility recommendations, and a CSS-only
first-slice proposal.

Fresh corrected-state review then found two material defects:

1. the pinned canonical JSX repository states CC BY 4.0 in its README, while
   the corrected package falsely classified the repository as granting no
   reuse license; and
2. the structural corpus record retained only abbreviated identities,
   aggregates, approximate percentiles, and no reproducible artifact
   inventory/sample rule, despite claiming exact reproducible corpus evidence.

The APG51 one-cycle rule forbids a second material architecture correction.
ADR 0031 therefore cannot be accepted.

## Decision

ADR 0031 is **Rejected**. All ten candidates are terminally `defer` for this
phase:

| Candidate | APG51 disposition | Reason |
| --- | --- | --- |
| `javascript-language-profile` | `defer` | Owner boundary survived review, but the rejected family package cannot authorize authoring. |
| `typescript-language-profile` | `defer` | Consumer-specific narrowing survived, but family acceptance and reproducible calibration did not. |
| `nodejs-runtime-profile` | `defer` | Distinct runtime owner survived, but the rejected package cannot authorize authoring. |
| `css-language-profile` | `defer` | Strong target evidence survived, but the corpus record is not reproducible enough to accept its growth policy. |
| `markdown-language-profile` | `defer` | Dialect boundary survived, but family acceptance and reproducible calibration did not. |
| `jsx-language-profile` | `defer` | Target-limited owner remains plausible; the corrected-state rights defect is material. |
| `react-component-profile` | `defer` | Policy A remains unmet: configuration-only presence is not behavioral dogfood. |
| `mdx-profile` | `defer` | Embedding/trust owner survived, but family acceptance and reproducible calibration did not. |
| `astro-profile` | `defer` | Independent Astro semantics survived the collapse attempt, but the family package is rejected. |
| `vitest-test-profile` | `defer` | Policy A remains unmet: neither target contains Vitest behavior. |

`defer` is not rejection of each underlying owner. It is the safe
phase-terminal result after the family decision failed its corrected-state
gate. No candidate is eligible authoring input from APG51.

## Retained review evidence

The following findings remain evidence for a later separately authorized
architecture phase, not accepted policy:

- JavaScript owns ECMAScript; TypeScript owns compile-time/type behavior;
  Node.js owns its runtime/CLI behavior. Selection is direct, browser
  JavaScript is a Node non-trigger, and Node is not a TypeScript prerequisite.
- JSX syntax/transform, React semantics, Markdown dialect, MDX executable
  embedding, and Astro execution/integration remain distinct candidate
  boundaries. No runtime skill chain is implied.
- The theme directly selects TypeScript 5.9.3 and its tracked Astro-check
  command is a verified diagnostic consumer. Website TypeScript 7.0.2 is
  lock/package-present with a compiler bin, but its project/compiler-service
  consumer is unverified.
- The pinned canonical JSX repository's README licenses the work under CC BY
  4.0. React source is MIT and react.dev is CC BY 4.0.
- React and Vitest retain Policy A under ADR 0029. Policy B or C would require
  a separately authorized amendment.
- Browser runtime, HTML, and accessibility remain recommended subjects for
  separate future evidence phases. Starlight, package managers, bundlers,
  lint/format, deployment, browser support floors, and visual design remain
  project-owned.

The measured candidate bands below are retained only as non-normative review
evidence because the exact reproducibility record failed review:

| Artifact | Green | Yellow | Orange | Red |
| --- | ---: | ---: | ---: | ---: |
| JavaScript module/script | <=400 | 401-700 | 701-1000 | >=1001 |
| TypeScript `.ts` module | <=400 | 401-700 | 701-1000 | >=1001 |
| Handwritten `.d.ts` | <=500 | 501-900 | 901-1400 | >=1401 |
| TypeScript configuration source | <=150 | 151-300 | 301-500 | >=501 |
| Node CLI/script/runtime adapter | <=300 | 301-500 | 501-800 | >=801 |
| CSS standalone stylesheet | <=400 | 401-700 | 701-1000 | >=1001 |
| CSS component/scoped block | <=150 | 151-250 | 251-400 | >=401 |
| Markdown authored document | <=300 | 301-600 | 601-1000 | >=1001 |
| JSX/TSX standalone module | <=250 | 251-450 | 451-800 | >=801 |
| MDX document | <=300 | 301-600 | 601-1000 | >=1001 |
| Astro component/page/layout | <=200 | 201-350 | 351-600 | >=601 |

A successor must reproduce exact corpus membership, selection rules, counts,
and calculations before accepting or changing any threshold. It must preserve
the proposed two-axis response: Yellow records pressure; Orange requires an
accepted containment/decomposition plan with validation and rollback; Red
stops material growth except a smallest-safe correction or explicit
human-approved bounded exception. Size does not determine semantic risk, and a
legacy Red artifact does not require unrelated cleanup.

Mixed `.tsx`, `.mdx`, and `.astro` files should still be counted once under
their whole-file owner, with embedded languages used only for semantic
routing. Generated, vendored, minified, lock, snapshot, fixture, and
build-output artifacts should be excluded before banding. These are reviewed
recommendations, not accepted policy under this rejected ADR.

## Authoring and authority consequence

There is no recommended or eligible Claude authoring slice after APG51.
CSS-only was the strongest candidate during initial review, but the material
corrected-state defect and unreproducible corpus prevent it from becoming
authoring input. A fresh, separately authorized architecture phase must
re-establish exact rights, reproducible corpus evidence, dispositions, bands,
and slicing before any leaf is authored.

No ADR 0032 is created. Development remains 28/28/28 with fourteen stable and
fourteen provisional skills. No skill, catalog row, projection, route, test
inventory, maturity state, dependency, release, public object, or active
installation changes.

## Alternatives considered

- Accept after correcting the README license and expanding the corpus record:
  rejected because that would be a prohibited second material architecture
  correction.
- Accept the owner graph while treating rights/corpus as editorial: rejected
  because exact rights and empirically reviewable thresholds are hard gates.
- Reject individual owner value: rejected because the fresh review did not
  falsify every boundary; phase-level deferral preserves that evidence without
  granting authoring eligibility.
- Begin the CSS slice anyway: rejected because a slice may not proceed from a
  rejected family decision.

## Re-entry

A new maintainer instruction may authorize a fresh architecture cycle. It
should begin from the exact APG51 evidence, verify the JSX README license,
publish a reproducible private corpus inventory and deterministic sample
method, independently re-review every threshold and scenario, and then issue a
new terminal decision. APG51 itself authorizes no successor.
