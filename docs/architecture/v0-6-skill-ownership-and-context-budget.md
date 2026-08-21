# v0.6 Skill Ownership, Composition, and Context Budget

This document is the normative v0.6 architecture contract. It is decided by
[ADR 0047](../adr/2026/08/0047-v0-6-skill-scope-ownership-and-context-budget.md)
and consumed by APG86 through APG90. It authorizes no skill body, catalog row,
projection, version change, publication, or push.

It supplements rather than replaces the
[language profile contract](../language-profile-contract.md), which continues to
own warning levels, profile requirements, project precedence, artifact
classification, and process/domain pairing for every profile named here.

## 1. Frozen scope

The v0.6 skill expansion is exactly six domain profiles:

1. `astro-profile`
2. `jsx-language-profile`
3. `mdx-profile`
4. `react-component-profile`
5. `vitest-test-profile`
6. `gomock-test-profile`

No seventh profile is approved by implication. Renaming, merging, splitting, or
replacing any of the six requires a demonstrated contract defect and explicit
operator escalation.

Non-goals for v0.6, restating and extending the backlog boundary in
[the v0.6 scope record](../v0-6-roadmap.md): browser and DOM APIs, HTML,
accessibility, Starlight, Vite, bundler internals, package managers, Playwright,
Tailwind, CSS-in-JS, state-management libraries, server frameworks, and
additional Go testing libraries. None of the six may absorb these by treating
them as an adjacent concern.

Each of the six is a *candidate* until its own implementation phase authors it,
validates it, and integrates it. This contract fixes what each would own; it
does not assert that any of them exists.

## 2. Ownership matrix

Each profile states what it owns, what it explicitly does not own, and which
existing v0.5 profiles it composes with. "Composes with" means the two are
routinely applicable to the same task and must not contradict each other; it
does not mean either invokes the other.

### 2.1 `jsx-language-profile`

**Owns.** JSX as a syntax and transform surface: element, attribute, and child
grammar; expression containers; fragments; spread and key semantics at the
syntax level; escaping and text handling; the `jsx` and `jsxImportSource`
configuration axes; the automatic versus classic runtime distinction; and the
consequences of `.jsx` versus `.tsx` file kind on parsing.

**Does not own.** React component semantics, hooks, rendering behavior, or
reconciliation — those belong to `react-component-profile`. Type checking of
`.tsx` files, including generic components and JSX intrinsic element typing,
which belongs to `typescript-language-profile`. Bundler, dev-server, or
transpiler tool selection. Runtime behavior, which belongs to
`nodejs-runtime-profile`.

**Composes with.** `javascript-language-profile`, `typescript-language-profile`,
`nodejs-runtime-profile`.

**Boundary test.** A question answerable without naming any component library is
JSX's. A question whose answer changes depending on which library consumes the
JSX is not.

### 2.2 `react-component-profile`

**Owns.** Component and render semantics; state and effect models; hook rules
and their failure modes; component composition, context, and prop contracts;
re-render and memoization judgment; error boundaries; and the interaction
surface between component design and component testing.

**Does not own.** JSX syntax and transform configuration. Routing, data
fetching, server components as a meta-framework feature, and metaframework
conventions. Styling in any form. Accessibility. Bundling and build tooling.
Test-runner mechanics, which belong to `vitest-test-profile`.

**Composes with.** `jsx-language-profile`, `typescript-language-profile`,
`javascript-language-profile`, `vitest-test-profile`.

**Boundary test.** This profile must remain answerable for a React component
rendered by any host. The moment an answer depends on Astro, a router, or a
bundler, the question belongs to that owner.

### 2.3 `mdx-profile`

**Owns.** The document-to-component boundary: where Markdown content ends and
evaluated JSX begins; MDX imports and exports; expression evaluation inside
documents; component provider and mapping behavior; the compile-time versus
runtime distinction for MDX documents; and the failure modes specific to mixing
the two grammars.

**Does not own.** The Markdown dialect itself — headings, lists, links,
reference syntax, and CommonMark or GFM behavior belong to
`markdown-language-profile`. JSX grammar. React component semantics. Any
particular site framework's content pipeline.

**Composes with.** `markdown-language-profile`, `jsx-language-profile`,
`react-component-profile`, `astro-profile`.

**Boundary test.** If removing all JSX from the document leaves the question
intact, it is Markdown's. If the question is about what happens at the seam, it
is MDX's.

### 2.4 `astro-profile`

**Owns.** `.astro` component structure, including the frontmatter/template
execution split; islands and client directives; content collections and their
schemas; file-based routing and project conventions; the server-versus-client
execution boundary; and integration configuration as an Astro-level concern.

**Does not own.** React-specific semantics inside an island, which route to
`react-component-profile`. Starlight, which remains a backlog candidate. Vite
internals. Styling. MDX's document/component seam, which routes to
`mdx-profile`. Deployment and hosting.

**Composes with.** `mdx-profile`, `react-component-profile`,
`jsx-language-profile`, `typescript-language-profile`,
`nodejs-runtime-profile`.

**Boundary test.** Astro answers where and when code runs and how the project is
organized. It does not answer what a component library does once it is running.

### 2.5 `vitest-test-profile`

**Owns.** Vitest runner and configuration behavior after the project has already
selected Vitest: config resolution and workspace shape; environment selection;
the assertion surface and its failure output; mocking, spying, module mocking,
and timer control as Vitest features; concurrency and isolation modes; snapshot
behavior; and coverage-provider configuration.

**Does not own.** Whether to adopt Vitest, which is a project dependency
decision no profile makes. Generic test discipline — what to test, when a test
is sufficient, and how to sequence test work — which remains owned by
`implementing-with-test-discipline` and the project test strategy. React
component-testing semantics, which belong to `react-component-profile`.
Coverage policy and thresholds, which the project owns.

**Composes with.** `javascript-language-profile`, `typescript-language-profile`,
`react-component-profile`, `nodejs-runtime-profile`.

**Boundary test.** Vitest answers how the runner behaves. It does not answer
whether a test should exist.

### 2.6 `gomock-test-profile`

**Owns.** `mockgen` generation modes and their tradeoffs; generated-code
placement, packaging, and classification; controller lifecycle and cleanup;
expectation declaration, call counts, ordering, and matcher semantics; argument
matching and failure diagnosis; and the maintenance consequences of regenerating
mocks.

**Does not own.** The native `go test` lifecycle, subtests, table-driven
structure, and helper conventions, which belong to `go-test-profile`. Value
comparison and diffing, which belongs to `go-cmp-test-profile`. Go language
semantics and interface design, which belong to `go-language-profile`. Whether
to introduce a mocking dependency at all.

**Composes with.** `go-language-profile`, `go-test-profile`,
`go-cmp-test-profile`.

**Boundary test.** GoMock answers questions about the mock and its controller.
The test around it, and the comparison inside it, have other owners. This slots
into the existing owner graph in
[the Go testing component specification](../specs/go-testing-component-profiles.md)
without changing any owner already recorded there.

## 3. Composition

When more than one of these profiles is selected for one task:

1. **The narrowest applicable owner answers.** A question fully inside one
   profile's owned surface is answered by that profile alone.
2. **Ties resolve by layer order**, outermost first: document (`mdx-profile`),
   framework (`astro-profile`), component library (`react-component-profile`),
   syntax (`jsx-language-profile`), language (`javascript-language-profile`,
   `typescript-language-profile`), runtime (`nodejs-runtime-profile`), test
   runner (`vitest-test-profile`), mock library (`gomock-test-profile`).
   The outer layer states the constraint it imposes and defers the inner
   question rather than answering it.
3. **No profile silently invokes another.** A profile may name the correct owner
   for an out-of-scope question. It may not restate that owner's guidance.
4. **Generic process guidance is referenced, never restated.** The smallest
   sufficient process skill remains primary, per the process/domain pairing
   rule in the language profile contract. A domain profile that reproduces
   planning, review, or test-discipline procedure is defective.
5. **A contradiction between two owners is a contract defect**, not a
   preference. It is reported and escalated. This mirrors falsification
   condition 2 in the Go testing component specification and extends it to the
   four adjacent web profiles.

Worked example. An MDX document in an Astro content collection embeds a React
island written in `.tsx`, tested with Vitest. Where the Markdown ends and the
JSX begins is `mdx-profile`. Whether the island hydrates and under which client
directive is `astro-profile`. What the component's effect does on hydration is
`react-component-profile`. Whether the attribute spread is valid syntax is
`jsx-language-profile`. Whether the generic prop type checks is
`typescript-language-profile`. How the test environment is configured is
`vitest-test-profile`. Whether the test is worth writing is
`implementing-with-test-discipline`.

## 4. Context and discoverability budget

### 4.1 Baseline

The v0.5 installed baseline, measured by `apgr skills context-report`:

| Field | Value |
| --- | --- |
| `skill_count` | 33 |
| `discoverable_skill_count` | 33 |
| `total_description_bytes` | 7,967 |
| `total_description_characters` | 7,955 |
| malformed | 0 |

### 4.2 Reference population and derivation

The budget is derived from measured evidence, not chosen by intuition.

The reference population is the description size of every existing skill whose
canonical name ends in `-profile` — 22 descriptions totalling 6,133 bytes, from
173 (`markdown-language-profile`) to 553 (`nodejs-runtime-profile`). The six new
skills are all domain profiles, so the profile subcorpus rather than the mixed
33-skill corpus is the correct basis; the 11 process skills are structurally
shorter (105 to 238 bytes) and would bias the result downward.

**Outlier rule.** A description is a high outlier when it exceeds twice the
population minimum, that is, above 346 bytes. Exactly two qualify:
`javascript-language-profile` at 417 and `nodejs-runtime-profile` at 553. Both
are known-broad owners, which corroborates the rule rather than being assumed by
it. The remaining 20 descriptions are the **body**: minimum 173, maximum 326
(`nix-test-profile`), mean 258.15, median 258.5.

**Rounding convention.** All constants round to a 10-byte step: outward for
bounds, up for the mean.

| Constraint | Value | Derivation |
| --- | --- | --- |
| Per-profile floor | **170 bytes** | body minimum 173, rounded down |
| Per-profile ceiling | **330 bytes** | body maximum 326, rounded up |
| Aggregate v0.6 delta | **1,560 bytes** | 6 × 260, where 260 is body mean 258.15 rounded up |
| Post-v0.6 total | **≤ 9,527 bytes** over exactly 39 skills | 7,967 + 1,560 |

This derivation uses only sorting, counting, a minimum, a maximum, and a mean.
It deliberately avoids quartiles and standard deviations, because quartile
values here depend on the estimator chosen — the same corpus yields a third
quartile of 306 or 309 under inclusive versus exclusive methods — and a budget
that changes with an unstated estimator is not reproducible.

**Observed consequence, not an input:** 20 of the 22 existing profiles already
satisfy [170, 330]. The two that do not are the same two the outlier rule
excluded. The factor of two in the outlier rule is the smallest integral factor
that admits the corpus body; a factor of 1.5 would admit only 10 of 22 and would
therefore be describing a different population than the one that exists.

**The aggregate binds tighter than the ceiling.** Six profiles at the 330-byte
ceiling would total 1,980 bytes, which the 1,560-byte aggregate forbids. The six
cannot all be maximal. The expected post-v0.6 envelope is therefore **8,987 to
9,527 bytes over 39 skills**, with the floor case being all six at 170 bytes.

### 4.3 Unit

The budget is expressed in **UTF-8 bytes**. The binding fields are the per-skill
UTF-8 byte length of the `description` scalar and the aggregate
`total_description_bytes` reported by `context_footprint_report`. Byte length is
used because it tracks encoded context cost, and because the two units already
diverge in this repository: `css-language-profile` is 320 bytes and 316
characters.

Diagnostic APG014 in `libexec/apg_skill_library_check.py` independently caps
descriptions at 1,024 **characters** and requires the `Use when ` prefix. That
rule is unchanged and remains in force. The v0.6 budget is a second, tighter
constraint on a different unit, not a replacement.

### 4.4 Scope of the limits

The floor, ceiling, and aggregate bind **only the six new v0.6 profiles**.

Existing v0.5 descriptions are not rewritten to fit. Retro-applying the
330-byte ceiling would fail `javascript-language-profile` and
`nodejs-runtime-profile`, which would be an unauthorized v0.5 behavior change
made for the convenience of a new rule. Those two remain governed by APG014.

If a later phase demonstrates that an existing description is genuinely
defective, that is a separate correction with its own evidence and authority,
not a side effect of this budget.

### 4.5 Sufficiency and conservatism

*Sufficient for discoverability.* Every profile in the body expresses a
`Use when ` prefix, the governing technology, a positive trigger, and at least
one material non-trigger within the [170, 330] band today. The band is therefore
demonstrated by 20 working examples rather than asserted. The floor exists so
that a description cannot satisfy the ceiling by degenerating into a stub that
no router can select on.

*Conservative for context.* The permitted growth is 1,560 bytes, roughly 19.6
percent over the 7,967-byte baseline and on the order of 390 tokens added to an
approximately 2,000-token always-loaded surface. Growth is bounded before
authoring begins rather than discovered after six descriptions exist.

*Known tension.* The four adjacent web profiles each have three siblings to
disclaim, so their non-trigger prose is under more pressure than any previous
batch's. The stated resolution is to sharpen the ownership sentence, not to
widen the band. If sharpening genuinely fails, the correct response is the
amendment path in section 4.7, with the failing candidate text as evidence.

### 4.6 Enforcement ownership and failure behavior

There is exactly one measurement implementation:
`agentic_praxis_grimoire.skills.context_footprint_report`. The `blobs=` path
measures the canonical tree and the no-argument path measures the packaged
manifest. No phase may add a second context-report implementation.

| Concern | Owner | Rationale |
| --- | --- | --- |
| Measurement | `context_footprint_report` | already the sole implementation |
| Per-skill band | `libexec/apg_skill_library_check.py`, a new diagnostic alongside APG014 | already parses every canonical leaf and already fails closed with stable identifiers |
| Aggregate ceiling | same owner, computed once from the canonical tree | development-time detection precedes release-time discovery |
| Installed readback | `apgr skills context-report --json`, bound canonical-to-packaged by `assert_canonical_resource_sync` | proves the shipped artifact matches the checkout |

The aggregate gate **must call** `context_footprint_report(blobs=...)` and use
its returned totals. Re-summing description lengths inside the check would
constitute the second competing implementation this contract forbids, and could
silently disagree with the number the CLI reports.

Release checks own presence and identity; projection checks own link ownership.
Neither owns metadata size, so neither is the right home for this gate.

Note that `apgr skills context-report --json` already exists in v0.5. APG89
exercises it as the installed readback gate; APG89 does not add the command.

**Failure behavior.** A violation fails closed with a stable diagnostic
identifier and a nonzero exit. Specifically:

- a new v0.6 description below 170 or above 330 bytes fails;
- a total above 9,527 bytes fails;
- `discoverable_skill_count` not equal to `skill_count` fails;
- any malformed entry fails, regardless of totals.

There is no auto-truncation, no silent omission of a skill from discovery, and
no rewriting of an existing v0.5 description to create headroom. An overage is
resolved by shortening the new description within the band or by an explicit
operator budget amendment.

### 4.7 Amendment

The four constants are amended only by an accepted successor decision that
restates the measured population, the derivation, and the new values. A phase
may not raise the ceiling for its own convenience, and an amendment that
excludes an inconvenient description from the population without an independent
outlier rule is invalid.

## 5. Explicit selection and advisory discovery

Explicit project selection remains the authority boundary. `apgr skills project`
is the sole projection authority, and the ownership, conflict, and rollback
design in [ADR 0004](../adr/2026/07/0004-project-local-skill-projection-and-rollback.md)
and [the projection guide](../project-skill-projection.md) is unchanged by v0.6.

If a v0.6 phase proposes an advisory discovery or recommendation surface, it
must satisfy all of the following:

1. **Read-only.** It writes no projection state, no links, no exclusion block,
   and no configuration.
2. **Evidence separated from recommendation.** Observed repository facts are
   reported distinctly from the profiles those facts suggest, so an operator can
   disagree with the inference while still trusting the observation.
3. **Deterministic.** Identical inputs produce identical ordered output, so the
   behavior is testable rather than advisory in the untestable sense.
4. **Never implicit.** No detection runs inside install, adopt, check, or
   uninstall. An operator asks for a recommendation or does not receive one.
5. **Never authoritative.** A recommendation is an input to an operator
   decision. It does not select, install, project, or activate anything.

If APG86 through APG89 cannot deliver such a surface within these constraints,
none ships and v0.6 is explicit-selection-only. That is an acceptable outcome,
not a failure.

## 6. Implementation contract for APG86 through APG89

Each implementation phase, for each profile it authors, must produce:

1. a canonical leaf at `skills/<name>/SKILL.md` satisfying the language profile
   contract, with a `Use when ` description in [170, 330] UTF-8 bytes;
2. one catalog row in `skills/README.md`;
3. one projection under `.agents/skills/` with the exact relative target, so
   that `apgr check skill-library` reports matching canonical, catalog, and
   projection counts;
4. a regenerated `src/agentic_praxis_grimoire/resources/skill-metadata.json`
   with `assert_canonical_resource_sync` green;
5. an allocated ADR and exit record confirmed by `apgr check record-identity`;
   and
6. a green aggregate budget at that phase's intermediate skill count.

Objective checks later phases must add:

- a per-skill description-band diagnostic in `libexec/apg_skill_library_check.py`
  with a stable identifier, scoped to the six v0.6 names;
- an aggregate ceiling assertion in the same owner, sourced from
  `context_footprint_report(blobs=...)`;
- a fixture or test asserting the exact expected counts and the aggregate
  ceiling at each intermediate topology; and
- for any advisory surface, a determinism test and a non-mutation test proving
  that projection state, links, and exclusions are byte-identical before and
  after.

Expected topology, with all six entering as `provisional`:

| Phase | Profiles added | Canonical / catalog / projections |
| --- | --- | --- |
| APG86 | `gomock-test-profile`, `vitest-test-profile` | 35 / 35 / 35 |
| APG87 | `jsx-language-profile`, `react-component-profile` | 37 / 37 / 37 |
| APG88 | `mdx-profile`, `astro-profile` | 39 / 39 / 39 |

At v0.6 completion the library is 39 skills: 14 stable and 25 provisional.

Compatibility expectations. No breaking CLI change. No projection state schema
change; version-1 state remains valid and an existing explicit subset does not
expand implicitly. No automatic discovery mutation. No durable workflow engine
inside APG — it remains the reusable provider-neutral process and skill layer.

## 7. Bounded v0.6 roadmap

| Phase | Scope |
| --- | --- |
| `APG86` | GoMock and Vitest implementation |
| `APG87` | JSX and React implementation |
| `APG88` | MDX and Astro implementation |
| `APG89` | v0.6 dogfood, cross-profile composition, context and readiness gate |
| `APG90` | v0.6 publication |

This ordering is frozen. It places the two lowest-coupling profiles first, so
that the budget gate and the composition rules are exercised on an easier case
before the four interlocking web profiles arrive. An objective dependency that
requires a different order is an escalation, not a phase decision.

## 8. Prior evidence

[The web and Node profile family analysis](web-and-node-profile-family.md)
records earlier owner evidence for JSX, React, MDX, Astro, and Vitest. It is a
terminal record under Rejected ADR 0031 and is cited here as historical evidence
only. This contract does not reopen it, and nothing in it grants authority under
ADR 0047.
