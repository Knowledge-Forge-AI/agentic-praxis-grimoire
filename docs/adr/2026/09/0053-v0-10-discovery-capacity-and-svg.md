# ADR 0053: v0.10 Discovery Capacity and SVG

## Status

Accepted with amendment

Acceptance records the manager's APG122 foundation disposition. The APG123
Browser/UI amendment below is a work-stage candidate pending dispatcher review.

## Decision date

2026-09-08 (foundation accepted); 2026-09-09 (browser-ui amendment)

## Context

APG122 starts v0.10 visual-web development after public v0.9.0 publication.
The maintained context report observes 39 leaves, 9,504 UTF-8 description
bytes, and 9,492 description characters. The historical integrity allowance is
9,527 bytes, leaving 23 bytes. Full `SKILL.md` files total 495,319 bytes;
that file sum is neither provider tokens nor a materialized bundle measurement.
Historical release evidence remains unchanged.

## Alternatives

| Alternative | Cost and disposition |
| --- | --- |
| Retain 9,527 by meaningful description compression | Six estimated 200–330-byte descriptions require reclaiming 1,177–1,957 bytes. This would change discovery for many existing owners and require semantic regression evidence. Deferred. |
| Versioned bounded discovery allowance | Preserve existing descriptions and reserve capacity for exact named candidates. Selected for this phase. |
| Composition and references | Explicit subsets already reduce selected context. References do not reduce description bytes by themselves; arbitrary support files are not embedded skill leaves. Preserve selection architecture and defer a new loader. |

## Candidate decision

The v0.10 policy reserves six 330-byte descriptions above the historical
9,527-byte allowance: a maximum of 11,507 UTF-8 description bytes. Eligible
identities are exactly `svg-language-profile`, `playwright-test-profile`,
`web-accessibility-profile`, `browser-runtime-profile`,
`npm-package-manager-profile`, and `vite-build-profile`.

APG122 admitted SVG alone, with a historical 9,857-byte maximum (40 leaves).
APG123 amends current admission to include `playwright-test-profile` and
`web-accessibility-profile` alongside SVG under the new current policy identity
`v0.10-browser-ui`. The historical `v0.10` policy retains explicit 39-leaf
baseline and 40-leaf SVG history. Development contains exactly 42 canonical
leaves, catalog rows, and projections (14 stable and 28 provisional). Original
39 identities and descriptions, as well as SVG's description, remain untouched
and <= 330 UTF-8 bytes each. The current admission ceiling expands to 10,517
bytes (9,527 + 3*330), while the overall six-candidate reservation ceiling
remains unchanged at 11,507 bytes. Unused reservations cannot be consumed by
another leaf.

Policy values and the baseline binding live in Go source under `skills/` and
the Python checker, with parity tests. Go/Python parity is maintained at the
constant level; Go policy constants match Python checker constants without Go
performing filesystem selector I/O. The Python checker reads the strict selector
at `testing/apg-discovery-policy.json` (`v0.10-browser-ui`), requiring exactly 42
leaves, while explicit baseline tests preserve 39-leaf and 40-leaf history.
Historical `GlobalDescriptionLimit` and v0.6 control meanings remain historical.
Current policy has a distinct identity. Malformed metadata, wrong identities,
duplicates, unadmitted candidates, reservation theft and overflow must fail closed.

SVG retains its 20,480-byte complete-file authoring ceiling (SVG only). The two
new leaves have no added numeric complete-file ceiling, and caller bundle
budgets and provider-overhead accounting remain unchanged (an explicit policy
choice). The SVG ceiling constrains APGR context, never the size or complexity
of user SVG documents.

SVG, Playwright, and Web Accessibility profiles are selected through
`explicit_skill_ids`. The unchanged v1 structured-fact table rejects
`languages: ["svg"]` as an unknown identifier; it does not return an empty
selection. Any future structured rule needs its own versioned decision.
Explicit CSS/JSX/React composition adds no adjacent skills implicitly.

## Maturity, evidence and rollback

Manager accepted the APG122 foundation. APG123's browser-ui integration is a
pre-final candidate, not self-accepted. SVG, Playwright, and Web Accessibility
begin provisionally integrated only after capacity prerequisites and bounded
contract checks pass. The browser UI harness uses project-owned synthetic fixtures
and bounded semantic predicates across Chromium, Firefox, and WebKit; it makes
no screen reader audio or assistive technology conformance claim.

If APG123 is rejected, remove its two new leaves, catalog/projection/route/
metadata/current-inventory additions and candidate tests together. Preserve SVG,
its historical admission policy, this ADR and all prior phase evidence.
Restore the SVG-only admission forward without rewriting releases.
Future browser-runtime remains absent; CSS, JS, TS, JSX, and React component
profiles remain unchanged. Dispatcher pre-final review and final verification
remain pending; this candidate does not grant publication, deployment, consumer
mutation, or successor authority.


## APG124 Toolchain admission amendment

The authorized Toolchain implementation introduces `v0.10-toolchain` as the
current policy, preserving historical `v0.10` and `v0.10-browser-ui` meanings.
Exactly Vite and npm join the prior 42 identities, producing 44 leaves and
14 stable / 30 provisional. Each new description is bounded at 330 UTF-8 bytes;
all prior descriptions are byte-identical. The current ceiling is 11,177 bytes;
the overall six-candidate ceiling remains 11,507. Only browser-runtime remains
reserved and unadmitted. This amendment grants no successor or release authority.
Implementation evidence and dispatcher disposition belong to APG124.

## APG125 final browser-runtime admission amendment

APG125 introduces current policy `v0.10-browser-runtime`, admitting exactly the
sixth named candidate. Historical v0.10, Browser/UI and Toolchain policies keep
their meanings. Current topology is 45 leaves, 14 stable / 31 provisional.
All 44 prior descriptions are frozen byte-for-byte, including Vite and npm;
the new browser-runtime description is at most 330 UTF-8 bytes. The current
ceiling is 9,527 + 6*330 = 11,507 bytes, equal to the overall reservation.
Keeping both checks is intentionally redundant. No named reservation remains
unused: unknown future leaves fail identity admission regardless of spare bytes.
No further v0.10 capability leaf is allocated. Readiness and release remain
separately authorized. This amendment does not impose a new browser-runtime
file-size ceiling or alter caller-selected context budgets.
