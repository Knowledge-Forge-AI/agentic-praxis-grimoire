# APG58 CSS Language-Profile Pilot Authoring

## Outcome

APG58 is a fresh one-profile authoring cycle after the
[APG57 review](apg57-web-and-node-architecture-review.md) rejected ADR 0034.
Starting from the exact terminal APG57 input — ADR 0031 and
[ADR 0034](../adr/2026/07/0034-web-and-node-profile-family-reconstruction-and-authoring-sequence.md)
both Rejected, every numeric band and all authoring deferred — APG58 stops
the family-wide percentile-derivation cycle, isolates the
strongest-supported candidate, and authors exactly one CSS candidate:
`skills/css-language-profile/SKILL.md` with its then-current
`docs/specs/css-language-profile.md` candidate specification.
[ADR 0035](../adr/2026/07/0035-css-language-profile-and-policy-selected-structural-limits.md)
is **Proposed** and is not accepted in APG58. Nothing is integrated, and no
successor phase is authorized.

## Strategic reset: explicit policy, not statistical inference

Two consecutive independent reviews established that sampled corpus tails do
not yield acceptable normative growth thresholds. APG58 therefore treats
structural limits as an engineering policy for controlling future growth,
with the corpus and targets serving falsification and legacy evidence only.
The candidate growth policy is exact and policy-selected:

```text
counted unit: nonblank physical lines in an ordinary handwritten
              standalone CSS stylesheet
Green   < 300
Yellow  300–599
Orange  600–899
Red     >= 900
```

These are round maintainability limits, not P90/P95/P99 results and not an
industry distribution. They were frozen before target placement and were not
tuned afterward. This is a CSS-only pilot; generalization to any other
profile requires a later separate decision.

## Owner boundary

The candidate owns material CSS-language semantics — cascade and origins,
specificity, inheritance, custom properties, selectors, layers, nesting,
layout, conditional CSS, animations/transitions — plus stylesheet
responsibility, extraction seams, and CSS structural warning/crisis
guidance. It does not own visual design, brand or design-token product
policy, HTML semantics, browser runtime APIs, accessibility outcomes,
browser-support matrices, Astro/MDX/React host semantics, Starlight
conventions, or build/format/lint/deployment tooling. A custom property's
definition, cascade, inheritance, and fallback are CSS semantics; the
token's approved meaning or value remains project-owned. The leaf is
directly selectable with no mandatory skill chain.

## Target dogfood

All twelve tracked stylesheets in the pinned theme repository were reviewed
read-only at the exact commit. Nine classify Green, two Yellow, none Orange,
and the known 995-line cohesive stylesheet classifies legacy Red — exactly
the intended shape: ordinary files unblocked, attention without blockage in
the middle, and a real stop at the known monster. Recomputed median (199)
and maximum (995) nonblank lines reproduce the recorded APG52 values. The
pinned website tracks no CSS. Embedded Astro style blocks route to semantic
review with no additive count. Exact placements are recorded privately.

## Structural contracts

Semantic risk and growth remain separate axes; semantic levels come from
named non-size signals, never raw counts. Each physical host file is counted
at most once: standalone `.css`/`.module.css` files receive one whole-file
count, embedded CSS receives no additive count, and no scoped-style-block
band exists. Generated, vendored, minified, lock, snapshot, fixture/demo,
build-output, binary, symlink, submodule, and unsupported-encoding artifacts
are excluded from ordinary bands. Legacy Red artifacts admit smallest-safe
corrections without unrelated rewriting; material Red growth requires
decomposition or an explicit bounded human exception that is local,
non-precedential, and rollback-bearing. Project policy may be stricter;
weaker policy does not silently override.

## Scenarios and validation boundary

Thirty fresh frozen scenarios (`APG58-CSS-001`–`030`, nine fields each)
cover triggers, non-triggers, ownership boundaries, exclusions, every exact
band edge, legacy behavior, small semantic Red, one-count behavior, stricter
policy, the bounded exception, and candidate removal. No APG unit,
integration, combined, or Bats suite ran — no maintained executable
ownership changed — and no target install, build, test, lint, preview,
browser, or deployment command ran. Claude authoring review is recorded
privately; it is not independent validation. A separately authorized Codex
phase (recommended APG59) must verify the exact APG58 object, build
failing-first executable contracts, challenge the policy, apply at most one
coherent forward correction, and decide ADR 0035.

## Preservation

ADR 0031 and ADR 0034 remain Rejected; all ten former Web/Node candidates
remain deferred. Development remains 28 canonical skills, 28 catalog rows,
28 projections, fourteen stable and fourteen provisional; the candidate leaf
is unintegrated and adds no catalog row, projection, route, maturity row,
release row, executable test, or dependency. Corrected public and active
v0.4.0 are unchanged; no target repository was mutated or executed. No
APG59 or successor work begins in APG58.

## Subsequent APG59 disposition

APG59 preserves this authoring-time record and corrects forward. Independent
failing-first review reproduced projected/resulting-count, task-aggregation,
authority, accessibility, and custom-property defects. One coherent amendment
improves them, but corrected-state review finds material executable-contract
and removal defects; APG59 rejects ADR 0035 and removes the candidate. The
immutable APG58 commit changed 23 files (15 added, 8 modified), not the
22-file staged count stated in one private authoring review. Codex separately
delivered the exact previously unpushed APG58 branch; that later action is not
attributed to Claude.
