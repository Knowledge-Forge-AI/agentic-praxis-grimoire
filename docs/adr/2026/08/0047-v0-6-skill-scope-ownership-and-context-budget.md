# ADR 0047: v0.6 Skill Scope, Ownership, and Context Budget

## Status

Accepted

## Context

v0.5 is terminally published. `docs/v0-6-roadmap.md` records a human-approved
candidate scope of exactly six domain profiles — `astro-profile`,
`jsx-language-profile`, `mdx-profile`, `react-component-profile`,
`vitest-test-profile`, and `gomock-test-profile` — plus one infrastructure
workstream governing the discoverable skill and context footprint under
explicit project-selected projection. That record grants no implementation
authority and defines no ownership boundaries, no measurable budget, and no
successor sequence.

Three properties of the current repository make those omissions consequential.

First, the six candidates overlap far more than any previous batch. JSX, React,
MDX, and Astro are four owners over one adjacent technology stack, and a
document written in MDX inside an Astro project rendering a React island
through JSX syntax can plausibly select four of the six at once. Without a
stated ownership matrix and a deterministic composition rule, two owners will
answer the same question differently, which
`docs/specs/go-testing-component-profiles.md` already identifies as the
falsification condition for a multi-owner split.

Second, every skill description is always-loaded discovery metadata. The v0.5
installed baseline is 33 skills, 33 discoverable, 7,967 UTF-8 description bytes,
7,955 characters, and zero malformed entries. Adding six profiles grows that
surface by roughly a fifth. The only current mechanical constraint is diagnostic
APG014 in `libexec/apg_skill_library_check.py`, which requires a `Use when `
prefix and at most 1,024 characters. The largest existing description is 553
bytes, so APG014 permits nearly fourfold growth per skill and no aggregate
growth limit at all. It is a well-formedness rule, not a context budget.

Third, `apgr skills context-report` already measures this surface, and
`agentic_praxis_grimoire.skills.context_footprint_report` is its sole
implementation. A budget that re-sums descriptions anywhere else would create a
second competing measurement that can silently disagree with the shipped one.

APG85 therefore fixes the contract that APG86 through APG90 consume. It
implements no skill body, advances no version, and publishes nothing.

## Decision

**1. The v0.6 skill scope is exactly the six named profiles.** No seventh
profile is approved by implication. Renaming, merging, splitting, or replacing
any of the six requires a demonstrated contract defect and explicit operator
escalation, not phase discretion.

**2. Each profile has a stated owns / does-not-own / composes-with boundary.**
`docs/architecture/v0-6-skill-ownership-and-context-budget.md` is the normative
matrix. `jsx-language-profile` owns JSX syntax and transform configuration, not
React semantics. `react-component-profile` owns component, render, state,
effect, and hook semantics, and is explicitly not a general frontend-framework
owner. `mdx-profile` owns the document-to-component boundary, not the Markdown
dialect and not JSX syntax. `astro-profile` owns `.astro` execution, islands,
content collections, and project conventions, and routes React-island semantics
to `react-component-profile`. `vitest-test-profile` owns runner, configuration,
assertion, mock, environment, and coverage-provider behavior after the project
has already selected Vitest. `gomock-test-profile` owns generation, controller
lifecycle, and expectation semantics, distinct from `go-test-profile` and
`go-cmp-test-profile`.

**3. Composition is deterministic.** When several profiles are selected
together, the narrowest applicable owner answers. Ties resolve by the stated
layer order: document, framework, component library, syntax, language, runtime,
test runner, mock library. No profile silently invokes another, and generic
process guidance owned by existing workflow and test-discipline skills is
referenced rather than restated.

**4. The context budget is derived from the measured existing profile corpus,
in UTF-8 bytes.** The reference population is the 22 existing descriptions whose
skill name ends in `-profile`. Two are high outliers under the stated rule that
an outlier exceeds twice the corpus minimum of 173 bytes:
`javascript-language-profile` at 417 and `nodejs-runtime-profile` at 553. The
remaining 20-profile body spans 173 to 326 bytes with a mean of 258.15.
Rounding to 10-byte steps —
outward for bounds, up for the mean — yields:

| Constraint | Value | Derived from |
| --- | --- | --- |
| Per-profile floor | 170 bytes | body minimum 173, rounded down |
| Per-profile ceiling | 330 bytes | body maximum 326, rounded up |
| Aggregate v0.6 delta | 1,560 bytes | 6 × 260, where 260 is body mean 258.15 rounded up |
| Post-v0.6 total ceiling | 9,527 bytes over 39 skills | 7,967 baseline + 1,560 |

The aggregate binds more tightly than six ceilings (1,980 bytes), so the six
cannot all sit at the maximum. The expected post-v0.6 envelope is 8,987 to
9,527 bytes.

**5. The budget binds only the six new v0.6 profiles.** Existing v0.5
descriptions remain governed by APG014 and are not rewritten to fit. Twenty of
the 22 existing profiles already satisfy [170, 330]; the two that do not are
the same two outliers the derivation excludes.

**6. Enforcement is fail-closed and has exactly one measurement owner.** The
per-skill and aggregate gates belong to `libexec/apg_skill_library_check.py`,
which already parses every canonical leaf and already runs under `apgr check
skill-library`. The aggregate gate must obtain its totals by calling
`agentic_praxis_grimoire.skills.context_footprint_report(blobs=...)` rather than
re-summing descriptions. A violation produces a stable diagnostic identifier and
a nonzero exit. There is no auto-truncation, no silent omission of a skill from
discovery, and no rewriting of a v0.5 description to buy headroom.

**7. Explicit project selection remains the authority.** `apgr skills project`
stays the sole projection authority. Any v0.6 advisory discovery surface must be
read-only, must separate observed evidence from recommendation, must be
deterministic, and must never write projection state, links, exclusions, or
configuration. No detection may run implicitly inside install, adopt, check, or
uninstall. If APG86 through APG89 cannot deliver an advisory surface within
those constraints, none ships and v0.6 remains explicit-selection-only.

**8. The successor sequence is frozen** as APG86 (GoMock and Vitest), APG87
(JSX and React), APG88 (MDX and Astro), APG89 (dogfood, cross-profile
composition, and the context/readiness gate), and APG90 (v0.6 publication). An
objective dependency that requires reordering is an escalation, not a phase
decision.

## Consequences

The six profiles gain an ownership contract before any of them is authored, so
APG86 through APG88 implement against a fixed boundary rather than negotiating
scope per phase. Overlap questions have a stated answer, and the go-testing
falsification conditions extend to the new owners.

Discovery metadata acquires its first real growth limit. The always-loaded
surface can grow by at most 1,560 bytes across v0.6 — roughly 390 tokens on an
approximately 2,000-token surface — and that limit is checked at development
time by an existing owner rather than discovered at release time.

The per-profile band is deliberately narrow. A profile author who cannot state
ownership, positive trigger, and at least one non-trigger within 330 bytes must
either sharpen the boundary or escalate for a budget amendment. Every existing
non-outlier profile does this today, so the band is demonstrated rather than
assumed, but it will constrain the four adjacent web profiles more than any
previous batch because each must also disclaim three siblings.

Binding the budget in bytes while APG014 caps characters means the two rules
measure different units. This is intentional: byte length tracks encoded context
cost, and `css-language-profile` already demonstrates divergence at 320 bytes
versus 316 characters. Both rules remain independently in force.

Accepting this ADR in-phase follows the APG73 and ADR 0042 governance
precedent rather than the candidate-architecture precedent of a Proposed ADR
decided by a later review phase. The operator assignment itself freezes the
six-profile scope and the successor sequence, and APG86 is an implementation
phase rather than an architecture review, so leaving the contract Proposed would
strand it with no phase authorized to decide it.

This decision grants no authority to author a skill body, add a catalog row,
install a projection, advance a version, publish, or push. Development topology
remains 33 canonical skills, 33 catalog rows, and 33 projections at the APG85
terminal.
