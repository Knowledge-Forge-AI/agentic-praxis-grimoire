# APG78 — Narrow JavaScript Core Candidate and Target-First Harness

## Status

Complete as an authoring phase. ADR 0045 is **Proposed**. The
`javascript-language-profile` candidate, its specification, its scenario
coverage, and its fourteen-case fixture exist on the Claude authoring branch
only. Nothing is integrated, and APG79 independently hardens the candidate and
terminally decides ADR 0045.

## Baseline

Exact APG77D: decision commit `38967535918d47af2ab6a1803b907a157776ca41`
(tree `47f26f736bcb28d4d5bf57df77f74597f1c2d9b1`) and terminal commit
`0b3682d8b3d42dec629912fceb6555ccc91eaa34`
(tree `9ceb35ff82691fe32ea231505c122618da3aa565`), each with one parent and the
exact recorded shape. The APG77D report parses through EOF as exactly four
ordered records. Local `main`, the local APG77D branch, and their last-fetched
remote-tracking refs all resolve to the terminal commit; live re-verification
was unavailable and is not claimed.

Current development at baseline: 31 canonical skills, 31 catalog rows, 31
projections; 14 stable and 17 provisional; 29 general, 1 ChatGPT-local, and 30
checked routes; `CSS-QD-001` through `CSS-QD-005` accepted with four Medium and
one Low; ADR 0042 Accepted, ADRs 0043 and 0044 Accepted with amendment, ADRs
0039, 0040, and 0041 Rejected; no `javascript-language-profile` anywhere.

## Why this line was attempted a third time

ADR 0039 and ADR 0040 were rejected for related reasons. Both bundled ECMAScript
semantics with a universal host architecture; both chose a qualitative
structural disposition backed by named signals, predicates, and false-positive
controls; and both grew four-layer decision models with typed authorities and
route algebras. In both reviews the material defects clustered in exactly that
machinery — signals contradicting their own defaults, routes that could not be
represented, context rules that no control activated, policy facts that stayed
in prose — while the mechanical checkers passed, because they could only prove
shape.

ADR 0042 changed the process rather than the ambition: authoring is separated
from independent hardening, a fresh repairable defect is repair-required rather
than fatal, and three hardening rounds are available. APG78 changes the scope to
match: the candidate is narrower, the structural machinery is absent rather than
redesigned, and structural policy is deferred outright.

## Sources and rights

ECMA-262 17th edition, ECMAScript 2026, remains the latest completed annual
edition. Its tag object and commit were read directly today, and no `es2027` tag
exists. The `es2026-errata` overlay remains non-semantic correspondence. The
living draft has advanced since the last recorded head and is retained as
refresh evidence only — **no candidate clause binds to it**.

Rights were separated by surface. The tc39/ecma262 licence and the Test262
licence were both fetched and their Git blob identities independently
reproduced. Specification prose is natural-language text under Ecma's text
policy and is not copied; only facts, identities, short names, hashes, and
independently derived consequences are recorded. Test262 remains BSD-licensed,
non-normative, and was consulted for rights only — no test was read, run, or
used as an oracle. The Ecma publication pages themselves were not reachable from
this session, so the rights boundary rests on the repository licence file, which
names the applicable policies; the no-copy rule applied here is stricter than
those policies require.

## Targets

Both read-only targets were freshly pinned and are unchanged from their recorded
orientation. The website pin was confirmed against a live unauthenticated read;
the theme repository is private and its freshness evidence is a local
remote-tracking ref rather than a live read, which is recorded rather than
papered over. No target command ran and no target changed.

Public-safe aggregates across both targets:

- exactly **one** whole-file JavaScript artifact — a checked `.mjs`
  configuration module;
- **two** host-embedded browser script regions, both inside host files whose
  whole-file ownership stays with the host;
- **zero** plain JavaScript utility or CLI source;
- **zero** generated, bundled, minified, vendored, or source-map JavaScript;
- one target declares a Node runtime family, a minimum version, and an exact
  package manager; the other declares none and delegates runtime selection to a
  third-party CI action.

That last point is a live instance of the unknown-host stop the candidate
defines. The first is why scenario `APG78-JS-022` and fixture case
`APG78-FX-013` are grounded in a real artifact rather than an invented one.

## The candidate

`skills/javascript-language-profile/SKILL.md` defines twenty-five stable
clauses. The specification carries the normative detail; the coverage record
maps twenty-four navigation scenarios to those clauses and, where one exists, to
a fixture case.

The owner is ECMAScript language semantics for an **established** JavaScript
source region — one whose bytes, parse goal, strictness state, edition
authority, whole-file owner, and consequence-bearing host inputs are already
established. Establishing the region is an input, not a result.

Explicit non-owners: Node.js and the CLI runtime; the browser and Web platform;
module resolution and loading; transformation and tooling; TypeScript, JSX,
React, MDX, and Astro; and project policy including the
JavaScript-versus-TypeScript choice itself.

Selection has four values and Response has four values, and the two vocabularies
are disjoint: `route-to-owner` is a selection and never a response. Routes are a
small ordered set with one item per consequence-bearing adjacent decision. There
is no route algebra, no effective-route union, and no obligation-provenance
structure — the ordered set is the whole mechanism.

Structural policy is **deferred**, which is a decision rather than an omission.
It is grounded twice: in the rejected history, where signal machinery produced
most of the material defects, and in the target evidence, where one configuration
module and two embedded regions cannot calibrate any numeric policy.

## The fixture

`src/test/fixtures/apg78-javascript-core/` carries fourteen cases across
seventeen APG-authored source files, with a canonical duplicate-refusing
manifest. Every manifest path exists and every source file is owned by at least
one case. There is no dependency, lockfile, `node_modules`, generated output,
bundled artifact, or source map, and no file performs a filesystem, network,
process, environment, signal, or exit-status operation.

The package declares one explicit module-mode boundary. The `.cjs` files remain
CommonJS by extension despite it — a host classification, not an ECMAScript
goal.

The CLI case demonstrates the product split without giving JavaScript ownership
of Node: the pure core receives argument values, environment values, and an
output interface as ordinary arguments and returns a structured result, while
the adapter file describes its concerns as data and performs none of them.

## Authoring smoke

A bounded scratch-only smoke ran against a copy of the fixture under one exact
engine. Thirteen of fourteen cases were evaluated; the `.cjs` case was
syntax-checked instead, because importing it from an ESM smoke would exercise
Node's CommonJS interop — host behavior outside the language question the case
exists to bound. Both goals were syntax-checked, and two negative controls
behaved as required.

Two observations bear on the candidate. First, checking a `.js` file succeeded
under the module goal because the engine consulted the package `type` field
rather than the extension — empirical support, under one engine, for the rule
that host evidence establishes the goal. Second, the `.cjs` file parsed
successfully under *both* goals, because its syntax is goal-neutral at parse
time; parsing therefore does not settle the goal, which is exactly why host
evidence is required.

The smoke proves only that engine's parse and observed evaluation results under
the exact commands, version, mode, and inputs recorded. It proves nothing about
universal ECMAScript semantics, target runtime selection, Node.js ownership,
browser behavior, or host completion.

## Preserved state and limitations

JavaScript current integration is absent. The APG78 branch carries 32 canonical
leaves against 31 catalog rows and 31 projections; that transitional shape is
expected and truthful, and the skill-library checker was not weakened to hide
it. Integrated `main` remains exact APG77D at 31/31/31, with 14 stable / 17
provisional and 29/1/30 routes. CSS known debt is exact and unchanged; CSS,
TypeScript, and Markdown remain provisional. Public and active corrected v0.4.0
and both targets are unchanged.

Named limitations: the candidate is unhardened; target dogfood is thin, and
neither `.js` goal resolution nor the `.cjs` boundary is exercised by any
target; several named receiving owners — node-runtime, browser-platform,
module-loader, jsx — do not yet exist, so a route to them is currently a stop
with a named addressee rather than a handoff; coverage is deliberately partial;
and the living draft is unused.

**Delivery limitation.** The candidate was authored but not committed by the
phase agent: this session's Git broker permits read-only Git only. No branch,
commit, push, Git-show report, or operational report exists for APG78, and no
remote parity or commit identity is claimed.

## Next boundary

Recommend, without beginning, APG79 — Codex JavaScript Core Iterative Hardening
and Provisional Integration, expected exit 00117 and the terminal ADR 0045
decision. APG79 must reconstruct all twenty-four scenarios and all fourteen
fixture cases independently, without using any APG78 artifact as an oracle. This
evaluation grants no APG79 authority.
