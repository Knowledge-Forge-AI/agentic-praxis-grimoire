# APG69 — JavaScript Core Architecture Reset and Layered Decision Contract

APG69 exercises new human authority after APG68 rejected ADR 0039. It
proposes a fresh, narrower JavaScript core architecture and a layered
validation contract under
[ADR 0040](../adr/2026/08/0040-javascript-language-profile-core-and-layered-decision-model.md),
preserves ADR 0039 as Rejected historical evidence without repairing or
reviving it, authors no skill, changes no integration owner, and leaves
development main at exact APG68. Separately authorized APG70
independently reviews and terminally decides ADR 0040.

## Baseline and source verification

- Exact APG68 baseline verified: commit, tree, sole APG67 parent, the
  four-record report omnibus, and local/cached-remote parity for main
  and both preserved branches.
- ECMA-262 es2026 annual tag, errata tag, es2026 branch head, and the
  moving 2027 draft were reverified live by read-only remote query; the
  draft had not moved past the APG68 observation.
- The exact annual specification, annual license, errata-changed
  specification, and Test262 license blobs were refetched at their exact
  commits and hash-verified against the APG68-recorded identities.
- Test262 remains non-normative conformance and corpus evidence under
  its verified Ecma BSD-style license. Rights remain distinct across
  specification text, repository source, embedded software,
  contribution terms, Test262, targets, and APG expression; the
  clean-room result is bounded and recorded in the
  publication-excluded bundle.

## Target and corpus evidence

Both pinned read-only targets were verified unchanged at their exact
commits and trees and were not installed, built, tested, linted,
previewed, or executed. The APG52 corpus facts (1,892 JavaScript
modules; 4,365 exclusions; two measured `.cjs` instances; no separate
CommonJS class) remain descriptive only. No statistic became a
threshold.

## Fresh architecture

The [core layered architecture](../architecture/javascript-language-profile-core-layered-architecture.md)
defines a narrower owner — normative ECMAScript language semantics for
a concrete JavaScript region after source goal, concrete host, emitted
bytes, and implementation facts are established — with explicit
non-owners, question-specific typed authorities, and separated Script/
Module/CommonJS, ESM-resolution, TypeScript/JSX, Node, browser/DOM,
ECMA-402, tool, and policy boundaries. Four decision layers (semantic,
structural, policy, effective) replace the rejected flat model: the
effective response is the maximum active severity, typed per-layer
routes form an ordered effective route union, a policy stop survives
routine semantics, and no layer silently overwrites another.

## Layered contract and registers

The [layered contract](../specs/javascript-language-profile-layered-contract.md)
owns every closed vocabulary and the three register schemas. The frozen
publication-excluded registers hold exactly twenty-four semantic rows
(APG69-JS-S001–S024, seventeen fields, concrete host or explicit
not-applicable per row), ten structural signals (nine fields with
testable false-positive controls), eight composition rows
(APG69-JS-C001–C008) that alone test severity precedence and
simultaneous routing, and two process rows (APG69-JS-P001–P002) outside
candidate prose. Finalization-timing dependence is fixed at Red.
Structural policy is qualitative disposition C, selected on fresh
grounds with no numeric whole-file bands.

## Eligibility and handoff

Authoring eligibility is `authoring-eligible-with-narrowing`, with the
exact narrowings recorded in the architecture; no candidate-authoring
authority is granted. The publication-excluded handoff recommends
APG70 — Codex JavaScript core and layered-contract peer review,
expected exit 00103 — which terminally decides ADR 0040. APG69 grants
it no authority.

## State

- ADR 0039: Rejected and unchanged; ADR 0040: Proposed
- JavaScript skill and integration owners: absent and unchanged
- Development: 29/29/29; 14 stable / 15 provisional; 27 general,
  1 ChatGPT-local, 28 checked routes
- Markdown: retained provisional; ADR 0037/0038 Accepted with amendment
- CSS: absent; ADRs 0031/0034/0035/0036 Rejected
- Public/active: corrected v0.4.0 unchanged; targets unchanged and
  unexecuted
- Exit: [00102](../status/2026/08/02/00102-apg69-javascript-core-layered-architecture-exit.md)

## APG70 forward review note

APG70 preserved and delivered exact APG69, then reproduced material defects in
the proposal's authority typing, source-goal/host model, intralayer
aggregation, composition binding, obligation and rollback preservation,
policy permission, deterministic rows, and adjacent-boundary coverage. The
historical counts and eligibility above describe the authored APG69 proposal.
APG70 used its one permitted forward correction; the corrected review state
contains 33 semantic, 10 structural, 15 composition, and 2 process rows. Fresh
review found new material defects after the sole correction. ADR 0040 is
Rejected, eligibility is `not-applicable-rejected`, the architecture is
historical evidence only, and APG71 is not recommended.
