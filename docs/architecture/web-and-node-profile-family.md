# Web and Node Profile Family

APG50 proposed this v0.5 family. APG51 independently reviewed it, applied one
forward correction, and then found material corrected-state rights and corpus
defects. [ADR 0031](../adr/2026/07/0031-web-and-node-profile-family-ownership-and-authoring-sequence.md)
is Rejected. No candidate exists as a skill or is eligible for authoring from
this decision.

## Terminal dispositions

| Candidate | APG51 disposition |
| --- | --- |
| javascript-language-profile | defer |
| typescript-language-profile | defer |
| nodejs-runtime-profile | defer |
| css-language-profile | defer |
| markdown-language-profile | defer |
| jsx-language-profile | defer |
| react-component-profile | defer |
| mdx-profile | defer |
| astro-profile | defer |
| vitest-test-profile | defer |

The eight non-React/Vitest deferrals preserve plausible owner evidence without
granting authoring eligibility. React and Vitest also fail ADR 0029 Policy A
dogfood.

## Reviewed owner evidence

The direct graph survived review as evidence:

- JavaScript owns ECMAScript semantics in any host; TypeScript owns
  type-system and compile-time behavior; Node.js owns runtime and CLI behavior
  for either language. A typed Node CLI selects all three directly. Browser
  JavaScript is a Node non-trigger; Node is never a TypeScript prerequisite.
- JSX owns syntax and transform configuration; TypeScript owns TSX checking;
  React would own component/hook behavior only after real selection. `.tsx`
  does not imply React.
- Markdown owns the selected dialect and pass-through boundary; MDX owns
  executable embedding; ordinary Markdown is an MDX non-trigger.
- Astro retains independent frontmatter/template execution, component,
  build/client, routing/content, integration, and environment questions while
  routing embedded languages/styles/content to their candidate owners.

All arrows describe analysis and direct routing, never a mandatory chain.
These boundaries are non-normative until a later decision accepts them.

## TypeScript and rights evidence

The theme's tracked Astro-check command is a verified TypeScript 5.9.3
diagnostic consumer. The website lock contains native TypeScript 7.0.2 and a
compiler bin, but no tracked project command, Astro-check path, ordinary Astro
build, MDX path, or editor/compiler service was verified to consume it.
Future claims must name the exact version and consumer.

The final rights correction records the pinned canonical JSX repository under
CC BY 4.0 through its README. Other reviewed baselines include ECMA-262 17th
edition, TypeScript source Apache-2.0 and handbook CC BY 4.0, Node source/docs
MIT, current CSS drafts under the W3C Software and Document License,
CommonMark/GFM specifications CC BY-SA 4.0, React source MIT and react.dev CC
BY 4.0, and MDX/Astro/Starlight/Vitest repositories under MIT terms. Future
work must repin each source and may not copy expression beyond its terms.

## Non-normative growth evidence

APG51 measured these candidate thresholds before corrected-state review:

| Artifact | Yellow | Orange | Red |
| --- | ---: | ---: | ---: |
| JavaScript module/script | 401 | 701 | 1001 |
| TypeScript `.ts` module | 401 | 701 | 1001 |
| Handwritten `.d.ts` | 501 | 901 | 1401 |
| TypeScript configuration source | 151 | 301 | 501 |
| Node CLI/script/runtime adapter | 301 | 501 | 801 |
| CSS standalone stylesheet | 401 | 701 | 1001 |
| CSS component/scoped block | 151 | 251 | 401 |
| Markdown authored document | 301 | 601 | 1001 |
| JSX/TSX standalone module | 251 | 451 | 801 |
| MDX document | 301 | 601 | 1001 |
| Astro component/page/layout | 201 | 351 | 601 |

The structural corpus record did not retain exact reproducible artifact
membership, sample rules, counts, and calculations, so these values are not
accepted policy. A successor must reproduce them before acceptance.

The reviewed response model remains evidence: semantic risk and growth are
independent; Yellow records pressure; Orange requires an accepted containment
or decomposition plan with focused validation and rollback; Red stops material
growth except a smallest-safe correction or explicit human-approved bounded
exception. A size crossing does not prove a defect or force unrelated legacy
cleanup.

Handwritten counting should use physical nonblank lines after universal
newline decoding, counting comments and a final non-empty unterminated line.
Generated, vendored, minified, lock, snapshot, fixture, and build-output
artifacts should be excluded. `.tsx`, `.mdx`, and `.astro` should each receive
one whole-file count, with embedded languages used only for semantic routing.
These are reviewed recommendations, not current APG rules.

## Policy, gaps, and authority

React and Vitest retain Policy A: real behavioral use in one of the two named
targets before authoring. Policy B or C would amend ADR 0029 and requires
separate maintainer authority.

Browser runtime, HTML, and accessibility remain recommended subjects for
separate future evidence phases. Generic HTML, browser/DOM behavior, and
accessibility are not silently assigned to language, content, or framework
owners. Starlight, package managers, Vite/bundlers, lint/format, deployment,
browser support floors, and visual design remain project-owned. No Starlight
profile is recommended.

There is no eligible or recommended authoring slice. CSS-only was the strongest
initial candidate, but the rejected family package cannot supply authoring
input. Development remains 28/28/28 with fourteen stable and fourteen
provisional skills; public and active remain corrected v0.4.0. A fresh
architecture cycle requires separate maintainer authority.

## Subsequent APG56 reconstruction

A separately authorized fresh cycle later reconstructed the family from
APG52's reproducible evidence without reopening this record; see the
[reconstruction document](web-and-node-profile-family-reconstruction.md)
and terminal
[ADR 0034](../adr/2026/07/0034-web-and-node-profile-family-reconstruction-and-authoring-sequence.md).
APG57 rejects ADR 0034 after corrected-state defects; every band and all
authoring remain deferred. ADR 0031 remains Rejected and every terminal
statement above is unchanged.
