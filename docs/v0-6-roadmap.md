# Agentic Praxis Grimoire v0.6 Scope Record

Status: APG90 publication preparation in progress. APG85 through APG89 are
accepted under their phase records; see [the v0.6 architecture
contract](architecture/v0-6-skill-ownership-and-context-budget.md).

## Purpose

This record freezes the bounded candidate scope that may be considered after
the separately authorized v0.5 readiness and publication phases. It is an
input to later planning, not authority to author, integrate, publish, project,
or deploy any profile or infrastructure change.

## Approved domain-profile candidates

The complete approved v0.6 domain-profile candidate set is:

- `astro-profile`
- `jsx-language-profile`
- `mdx-profile`
- `react-component-profile`
- `vitest-test-profile`
- `gomock-test-profile`

No seventh profile is approved by implication. Each named candidate still
requires source, rights, purpose, ownership, contract, validation, maturity,
and phase authority under the repository's ordinary lifecycle.

## Approved infrastructure workstream

One infrastructure workstream may be planned later:

- govern the discoverable skill and context footprint using measured evidence;
- make explicit project-selected profile projection the intended scaling
  direction; and
- preserve explicit project choice as authority rather than silently changing
  active skills through repository inference.

Advisory suggestions may be considered in later authorized work, but they may
not select, install, project, or activate profiles without an explicit project
selection. APG82 records a read-only context-footprint baseline only; it does
not implement selective projection or a context-budget threshold.

## Backlog boundary

Browser/DOM, HTML, accessibility, Starlight, Vite, package-manager profiles,
Playwright, Tailwind, additional Go testing libraries, and other plausible
owners remain backlog candidates. They require evidence and new human
authorization and are not part of the approved v0.6 scope above.

## Phase boundary

APG82 establishes the APGR distribution, configuration, artifact, response,
and measurement foundation only. APG83 is the next recommended, separately
authorized v0.5 readiness phase; APG84 is the later separately authorized v0.5
publication phase. Neither APG82 nor this scope record begins those phases or
any v0.6 implementation.

## APG85 architecture contract and frozen successor sequence

APG85 is architecture and documentation only. Under ADR 0047 it freezes the
exact six-profile scope above, states each profile's owns, does-not-own, and
composes-with boundary, adds a deterministic composition rule, derives a
measurable context and discoverability budget from the existing profile corpus,
and confirms that explicit project selection remains the sole projection
authority with any advisory surface non-mutating. It implements no skill body,
adds no catalog row or projection, advances no version, and publishes nothing.

The successor sequence is frozen as:

- `APG86` — GoMock and Vitest implementation
- `APG87` — JSX and React implementation
- `APG88` — MDX and Astro implementation
- `APG89` — v0.6 dogfood, cross-profile composition, context and readiness gate
- `APG90` — v0.6 publication

An objective dependency requiring a different order is escalated rather than
silently reshaped. The no-seventh-profile rule and the backlog boundary above
remain unchanged.

## APG86 implementation state

APG86 provisionally integrates `gomock-test-profile` and
`vitest-test-profile` and activates the APG85 context-budget checks. Current
development is 35 canonical skills, 35 catalog rows, 35 projections, 35
discoverable entries, 14 stable rows, and 21 provisional rows. The two
descriptions add 569 bytes to the v0.5 baseline for 8,536 total, leaving 991
bytes below the full-v0.6 ceiling.

The checker remains relational and topology-agnostic; exact APG86 counts are
phase evidence. Explicit project selection remains authoritative, existing
subsets do not expand, and no advisory discovery, version, publication,
deployment, target mutation, or APG87 work is included.

## APG87 implementation state

APG87 provisionally integrates `jsx-language-profile` and
`react-component-profile`. Current development is 37 canonical skills, 37
catalog rows, 37 projections, 37 discoverable entries, 14 stable rows, and 23
provisional rows. JSX uses 248 description bytes and React uses 268; the pair
adds 516 bytes for 9,052 total and leaves 475 bytes below the full-v0.6 ceiling.

The checker remains relational and topology-agnostic; exact APG87 counts and
the conservation result are phase evidence. Explicit selection remains
authoritative, existing subsets do not expand, and no MDX/Astro implementation,
APG88, advisory discovery, version, publication, deployment, target mutation,
or remote push is included.

## APG88 implementation state

APG88 provisionally integrates `mdx-profile` and `astro-profile`. Current
development is 39 canonical skills, 39 catalog rows, 39 projections, 39
discoverable entries, 14 stable rows, and 25 provisional rows. MDX uses 214
description bytes and Astro uses 238; the pair adds 452 bytes for 9,504 total
and leaves 23 bytes below the full-v0.6 ceiling.

The checker remains relational and topology-agnostic; exact APG88 counts and
terminal arithmetic are phase evidence. Explicit selection remains
authoritative, existing subsets do not expand, all six frozen profiles are now
authored and provisionally integrated, and no APG89, advisory discovery,
version, publication, deployment, active projection mutation, provider Git
publication, or successor work is included.

## APG89 readiness state

APG89 retains the exact APG88 skill state while exercising real web and Go
targets, deterministic cross-profile composition, isolated explicit project
selection, installed context identity, package reproducibility, and coverage
determinism. The topology remains 39/39/39 with 14 stable / 25 provisional,
39 discoverable, zero malformed, 9,504 bytes, 9,492 characters, and 23 bytes
below the 9,527 ceiling. The six frozen v0.6 profiles remain the complete set;
there is no seventh profile or implicit selection path.

The external APG89 supervisory review accepted the exact readiness candidate
with C0/H0/M0/L0 findings and terminalized it as `READY_FOR_APG90`. APG89
itself performed no version advance, public release construction, tag, upload,
deployment, active projection mutation, or successor work.

## APG90 publication preparation state

APG90 advances the canonical package version to 0.6.0, freezes a distinct v0.6
release epoch while preserving v0.5 reconstruction, separates the digest-
pinned historical thirty-three-skill v0.5 policy from the thirty-nine-skill
v0.6 policy, and qualifies exact release notes, workflow assets, distribution
artifacts, and installed context. The six v0.6 profiles remain provisional and
explicit project selection remains authoritative.

Provider work does not stage, commit, tag, push, publish, deploy, or mutate
active APGR state. If public GitHub and PyPI finalization remains outside the
dispatcher boundary, the APG90 tracked result is an exact same-phase external-
publication handoff rather than a publication claim. No APG91 or v0.7 work is
authorized.
