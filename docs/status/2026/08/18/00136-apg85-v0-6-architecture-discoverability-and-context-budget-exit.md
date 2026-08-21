# APG85 v0.6 Architecture, Discoverability, and Context-Budget Exit

Phase ID: `APG85`

## Status

The exact tracked candidate decides ADR 0047 as Accepted and adds the normative
v0.6 architecture contract. APG85 is architecture and documentation only: it
implements no skill body, adds no catalog row or projection, advances no
version, and performs no publication, deployment, target mutation, or remote
push. The disposition is `V06_ARCHITECTURE_CONTRACT_ACCEPTED`.

## Architecture decisions

1. The v0.6 skill scope is exactly `astro-profile`, `jsx-language-profile`,
   `mdx-profile`, `react-component-profile`, `vitest-test-profile`, and
   `gomock-test-profile`. No seventh profile is approved by implication, and
   renaming, merging, splitting, or replacing any of the six requires a
   demonstrated contract defect and explicit operator escalation.
2. Each profile has a stated owns, does-not-own, and composes-with boundary, with
   explicit anti-catch-all disclaimers for the four adjacent web profiles.
3. Composition is deterministic: the narrowest applicable owner answers, ties
   resolve by the layer order document, framework, component library, syntax,
   language, runtime, test runner, mock library, no profile silently invokes
   another, generic process guidance is referenced rather than restated, and an
   owner contradiction is a reportable contract defect.
4. The context budget is derived from the measured existing profile corpus in
   UTF-8 bytes: a per-profile band of 170 to 330 bytes, an aggregate v0.6 delta
   of at most 1,560 bytes, and a post-v0.6 total of at most 9,527 bytes over
   exactly 39 skills. The expected envelope is 8,987 to 9,527 bytes.
5. The budget binds only the six new profiles. Existing descriptions are
   unchanged and remain governed by diagnostic APG014's `Use when ` prefix and
   1,024-character cap.
6. Enforcement is fail-closed with exactly one measurement owner. The per-skill
   and aggregate gates belong to `libexec/apg_skill_library_check.py`, and the
   aggregate gate must call `context_footprint_report(blobs=...)` rather than
   re-summing descriptions.
7. Explicit project selection remains the sole projection authority. Any
   advisory surface must be read-only, non-mutating, deterministic, and never
   implicit; if none can be delivered within those constraints, none ships.
8. The successor sequence APG86 through APG90 is frozen, and reordering is an
   escalation rather than a phase decision.

## Measured expected context envelope

The v0.5 baseline is 33 skills, 33 discoverable, 7,967 UTF-8 description bytes,
7,955 characters, and zero malformed entries. That baseline is unchanged by
APG85, which adds no skill.

At v0.6 completion the surface is expected to be exactly 39 skills, 39
discoverable, between 8,987 and 9,527 description bytes, and zero malformed
entries. The ceiling permits roughly 19.6 percent growth over the baseline, on
the order of 390 tokens on an approximately 2,000-token always-loaded surface.

## Unresolved questions

The contract is stated but not yet mechanically enforced; no description-band
diagnostic or aggregate assertion exists in the checkout. Whether 330 bytes
suffices for a description that must disclaim three adjacent siblings is
untested, since no existing profile has that shape; the documented amendment
path requires the failing candidate text as evidence rather than phase
convenience. Whether the ownership boundaries hold under real tasks is
answerable only by applied dogfood, which is APG89's job. Whether any advisory
discovery surface ships at all remains open by design.

## What APG86 is authorized to implement

Nothing in this exit grants that authority; APG86 requires separate
authorization. When authorized, its bounded scope is `gomock-test-profile` and
`vitest-test-profile` only: two canonical leaves with descriptions in the 170 to
330 byte band, two catalog rows, two projections reaching 35 canonical, 35
catalog rows, and 35 projections, a regenerated resource manifest with
`assert_canonical_resource_sync` green, allocated ADR and exit records, the
per-skill description-band diagnostic and the aggregate ceiling assertion in
`libexec/apg_skill_library_check.py`, and a fixture asserting the expected
counts and ceiling at that intermediate topology. Both profiles enter as
provisional.

## Preserved state and stop

Development remains 33 canonical skills, 33 catalog rows, and 33 projections;
14 stable and 19 provisional. Context, maturity, routing, and the ten accepted
CSS and JavaScript debt entries are unchanged. Published v0.5 and corrected
historical v0.4 remain exact and untouched.

APG85 does not begin APG86, author any of the six profiles, implement a budget
check, add an advisory discovery surface, advance the version, publish, deploy,
mutate any target repository, push any remote, or start Nix deployment,
`agentic-praxis-grimoire-nd`, or `composition-nd`.
