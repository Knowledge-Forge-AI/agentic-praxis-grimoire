# APG50 Web and Node Profile-Family Architecture

Phase ID: `APG50`

Evaluation date: 2026-07-27

## Objective and exact input

APG50 opens v0.5 Workstream 3. It verified the exact immutable APG49
input — the single-parent mainline object behind exit 00069 together
with its complete Git-show and associated operational records; exact
development identities remain managed or publication-excluded evidence —
and independently recomputed all namespaces: 28 canonical skills, 28 catalog rows, 28
projections, 14 stable / 14 provisional, 26 general routes, 1
ChatGPT-local route, 27 checked route edges, next ADR 0031, next exit
00070. The Go test-component workstream remains terminally closed for
v0.5 (ADR 0026 Accepted and controlling; ADR 0025, 0027, and 0030
Rejected; no matryer/is profile or testing stack exists).

## Target scope and access

The two Knowledge Forge AI repositories were inspected read-only at
exact recorded commits, with no execution, installation, build, test,
lint, preview, browser, or deployment command and no mutation. The
website repository's tip was verified equal to its public remote; the
theme repository carried a recorded access limitation and was inspected
from immutable commit objects only. A safe target-stack summary, the
complete extension inventory, a bounded 23-file deep-read sample (8 + 15,
within the 15/30 bounds), and all identity details are in the
publication-excluded APG50 evidence and summarized publicly in the
[family architecture document](../architecture/web-and-node-profile-family.md).

Safe stack summary: npm-managed Astro 7.1.3 + Starlight 0.41.4 website
(React 19.2.8 configuration-only; native TypeScript 7.0.2 peer; MDX
3.1.1 transitive; GitHub Pages) and a pnpm 10 workspace Starlight theme
(Node engines >=22.12.0, CI Node 24; TypeScript 5.9.3; twelve-file
layered CSS corpus; changesets release; Vitest, React, and standalone
JSX/TSX absent; recorded lockfile/workspace rename drift).

## Architecture dispositions

architecture-supported: `javascript-language-profile`,
`typescript-language-profile`, `nodejs-runtime-profile`,
`css-language-profile`, `markdown-language-profile`, `mdx-profile`,
`astro-profile`.
architecture-supported-with-target-evidence-gap: `jsx-language-profile`
(JSX exists only MDX-embedded; no standalone `.jsx`/`.tsx` artifact).
defer-missing-dogfood: `react-component-profile` (zero tracked component
use; configuration-only presence), `vitest-test-profile` (total target
absence).

No candidate is accepted, retained, integrated, stable, or compatible;
all dispositions await independent Codex review.

## Source and rights method

Every candidate has a ledger entry with its controlling primary source,
target-selected version, rights/document-use terms, reliable and
deliberately-not-generalized facts, source/runtime distinction, refresh
condition, clean-room mode, and Codex verification method. Material
pins: ES2026; the TypeScript 5.9.3/native-7.0.2 dual-line rule; Node
>=22.12 with 24 LTS CI; a dated bounded W3C CSS module set; CommonMark
0.31.2 + GFM + pipeline behavior; MDX 3.1.1; Astro 7.1.3 / Starlight
0.41.3–0.41.4; Vitest target absence. All guidance was independently
worded; no target or upstream expression was copied; no privacy or
personal-data leakage entered public artifacts.

## Owner graph and project-owned decisions

JavaScript, TypeScript, and Node.js are separate owners (Node never a
TypeScript prerequisite; browser JavaScript a Node non-trigger). JSX
owns syntax/transform; TypeScript owns TSX checking; React semantics are
conditional on real selection. Markdown and MDX are separate with
ordinary Markdown an MDX non-trigger; target MDX pairs with Astro
components, never React. Astro routes to language/CSS/content/framework/
Node owners and absorbs none. Vitest (deferred) owns runner semantics
only. All arrows are design inputs; selection is direct; no mandatory
chain exists; every owner is independently omittable. Package managers,
bundlers, lint/format, browser targets, CI/deployment, adapter
selection, Starlight adoption, and the JS-versus-TS utility preference
remain project-owned.

## Adjacent gaps

HTML semantics and the browser/DOM runtime are recorded, unowned
deferred adjacent candidates (never silently assigned); accessibility is
a deferred adjacent candidate no owner may imply; Starlight is
project-owned with a recorded evidence-backed deferred residual and no
profile; package managers, bundlers, lint/format, deployment, and
browser compatibility are project-owned for v0.5.

## Calibration, scenarios, and slices

The structural warning/crisis method makes every level a named-risk
statement: counts/size alone never create Red; Orange/Red requires a
concrete risk with evidence, smallest safe fix, and rollback; numeric
bands require measured corpus support; generated artifacts never
calibrate; large cohesive files can be Green and small false-evidence
files Red. Sixty architecture scenarios — APG50-WEB-001 through
APG50-WEB-060, six per candidate — are frozen in publication-excluded
evidence. Bounded later slices are proposed: A (JS/TS/Node), B
(CSS/Markdown, parallel with A), C (MDX plus conditional JSX), D
(Astro); React and Vitest are excluded from slicing until real target
evidence exists. No slice is authorized and no phase ID is allocated.

## ADR 0031 and review boundary

[ADR 0031](../adr/2026/07/0031-web-and-node-profile-family-ownership-and-authoring-sequence.md)
is Proposed. It governs architecture and sequence only and accepts no
skill leaf while Proposed or later Accepted. ADR 0029 is unchanged.
Author self-review ran adversarial lanes over the inventory, sources,
each boundary group, gaps, calibration, scenarios/slices, privacy, and
the complete diff; author self-review is not independent Codex review.
A complete APG51 peer-review handoff exists in publication-excluded
evidence, requiring challenge of every fact, boundary, gap, scenario,
and slice, one forward correction cycle, and the ADR 0031 decision,
with no skill integration.

## Unchanged state and boundary

APG50 authored no profile leaf, test, fixture, executable, dependency,
projection, catalog row, route, maturity state, release-policy row, or
integration change. Development remains 28/28/28 with 14/14; public and
active remain corrected v0.4.0 at 28/28/28; the Go workstream remains
closed; target repositories remain read-only and unexecuted; `main` did
not move. No successor phase is authorized by this evaluation.

## APG51 forward correction

APG51 preserves this document as the historical APG50 result while correcting
the architecture forward. APG50's semantic-only calibration, website
TypeScript compiler claim, approximate rights labels, implicit React/Vitest
policy, adjacent-gap dispositions, scenario outcomes, and proposed slices are
superseded by the
[APG51 peer review](apg51-web-and-node-architecture-peer-review.md).

Fresh APG51 corrected-state review found a false JSX rights classification and
a non-reproducible structural corpus record after the one authorized
correction. ADR 0031 is Rejected, all ten candidates are `defer`, and no
authoring slice is eligible. Candidate bands, consumer-specific TypeScript
evidence, Policy A, and browser/HTML/accessibility recommendations remain
review evidence only. No skill or slice was implemented.
