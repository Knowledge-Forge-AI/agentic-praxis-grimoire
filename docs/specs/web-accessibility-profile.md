# Web accessibility profile contract

Lifecycle: `provisionally-integrated`.
Lifecycle ADR: `Proposed`.

APG123 admits a provisional implementation and evidence-hierarchy owner.
Standards status is part of the contract. Original synthesis and references do
not copy upstream wording or consumer artwork; no upstream license is assigned
to APGR-authored guidance merely because it cites that source.

## Dated source register

Sources below were inspected 2026-09-09. Dated specification URLs freeze the
reported status; living documents and guidance can change. Drafts are evidence
for interpretation and target questions, not promoted Recommendations.

| Source | Exact status/date used | Clauses and limitation |
| --- | --- | --- |
| [WCAG 2.2](https://www.w3.org/TR/2024/REC-WCAG22-20241212/) | Recommendation, 2024-12-12 | AX-01–AX-11; criterion-specific scope, levels and exceptions apply |
| [WAI-ARIA 1.2](https://www.w3.org/TR/2023/REC-wai-aria-1.2-20230606/) | Recommendation, 2023-06-06 | AX-01–AX-09; roles do not implement interaction |
| [ARIA in HTML](https://www.w3.org/TR/2026/REC-html-aria-20260811/) | Recommendation, 2026-08-11 | AX-01–AX-04; permitted native/ARIA combinations |
| [WAI-ARIA 1.3](https://www.w3.org/TR/2026/WD-wai-aria-1.3-20260604/) | Working Draft, 2026-06-04 | Future mapping/feature context only |
| [Accessible Name and Description 1.2](https://www.w3.org/TR/2026/WD-accname-1.2-20260827/) | Working Draft, 2026-08-27 | AX-02, AX-05; computed outcomes require target checks |
| [HTML-AAM 1.0](https://www.w3.org/TR/2026/WD-html-aam-1.0-20260829/) | Working Draft, 2026-08-29 | AX-01–AX-09 mapping research, not universal target behavior |
| [SVG-AAM 1.0](https://www.w3.org/TR/2026/WD-svg-aam-1.0-20260827/) | Working Draft, 2026-08-27 | Mapping research only: source explicitly warns against implementation based on this outdated draft |
| [Media Queries 5](https://www.w3.org/TR/2026/WD-mediaqueries-5-20260219/) | Working Draft, 2026-02-19 | AX-10; preference features need target support evidence |
| [HTML interaction](https://html.spec.whatwg.org/multipage/interaction.html) | Living Standard, inspected 2026-09-09 | AX-01, AX-06–AX-08; native focus and inert behavior |
| [WAI complex images](https://www.w3.org/WAI/tutorials/images/complex/) | WAI tutorial guidance, inspected 2026-09-09 | AX-05; equivalent information exceeds a short name |

SVG-AAM's warning is a substantive limitation. This profile uses established
native semantics, WCAG requirements and observed browser behavior; it does not
instruct implementers to adopt that draft's mappings. Real assistive technology
remains necessary for claims about announcements and task experience.

## Evidence contract

The [maintained register](../../src/test/fixtures/apg123-browser-ui/scenarios.json)
binds AX01–AX11 to concrete assertions and engine lanes. The leaf's references
are navigation coverage only. Browser assertions are deliberately narrower than
the complete implementation guidance. Clause IDs use hyphens and descriptive
suffixes: `AX-07-WIDGETS` owns widget interaction guidance, while scenario `AX07`
tests complex alternatives. Cite full clause IDs and use the table below for
scenario coverage; matching numeric portions imply no equivalence. No dedicated
scenario qualifies the dialogs, popovers or menus guidance in clause AX-07.

| Cases | Guidance clauses | Evidence and residual |
| --- | --- | --- |
| AX01–AX02 | AX-01–AX-02 | Native names and intentional missing-name failure; no human clarity assessment |
| AX03 | AX-03 | Observed heading/landmark hierarchy, not whole-document usability |
| AX04–AX05 | AX-06 | Actual keyboard focus/activation and rendered focus difference; no contrast-ratio claim |
| AX06–AX07 | AX-05 | Meaningful/decorative SVG and structured complex alternative; equivalent meaning still requires review |
| AX08 | AX-08 | Hidden/inert/disabled observations; not every widget transition |
| AX09 | AX-09 | Status attributes and dynamic text; no announcement claim |
| AX10 | AX-11 | Playwright ARIA snapshot; not a screen reader |
| AX11 | AX-03–AX-04, AX-10 | Native validation, headers and reduced-motion emulation; not complete forms/motion compliance |

Source/DOM, semantic tree, keyboard interaction, rendered measurement, manual
review and real assistive technology are separate layers. Passing automated
checks is not WCAG conformance proof. Contrast, zoom/reflow, content meaning,
complex widget usability, touch interaction and assistive-technology acceptance
remain explicitly outside this representative matrix unless separately tested.

The selected Playwright role locator includes the fixture's inert button even
while pointer activation and focus are refused. This is a maintained limitation
of using its DOM-derived semantic lookup as evidence: it is not a query of the
platform accessibility tree and cannot establish inert exposure to assistive
technology. The harness preserves both observations rather than erasing the
distinction with a passing attribute-only check.

## Composition and admission

SVG owns vector language and authoring; this owner decides accessible meaning
and the testing hierarchy. Playwright owns its mechanisms and artifact lifecycle.
CSS, JS, TS, JSX, React and Node ownership remains unchanged. Future browser-runtime
work is not installed or implicitly selected. Both new owners are explicit
resolver selections and introduce no new structured fact vocabulary.

The description has an identity-specific 330-byte reservation. There is no new
numeric body ceiling for this leaf; SVG's existing ceiling remains SVG-specific.
Combined context budgets apply to actual selected bodies and fail closed.
Current qualification and rollback are recorded in the APG123 evaluation.
