# Language-Profile Production Recovery Charter

## Authority and scope

This charter is current and controlling for future CSS, JavaScript,
TypeScript, and adjacent language-profile recovery. It remains controlling
until a later Accepted ADR changes it. ADR 0042 accepts the charter through
new human product and governance authority; it does not reopen or rewrite any
rejected ADR.

This charter governs how APG develops, reviews, repairs, accepts, and
provisionally integrates production-oriented language profiles. It authorizes
no profile, integration, release, target mutation, or successor phase by
itself.

## Product priorities

The ordered product priorities are:

1. **Essential — TypeScript.** TypeScript must not be indefinitely displaced
   by another adjacent profile.
2. **Desirable — CSS.** CSS does not block TypeScript delivery.
3. **Desirable — JavaScript.** JavaScript does not block TypeScript delivery.
4. **Deferred — JSX.** No JSX work begins under this charter.

The maintained theme target's older TypeScript snapshot is migration evidence,
not the intended destination. TypeScript 7 is the intended primary compiler
generation. A future implementation phase freshly selects and pins the exact
current TypeScript 7 patch. TypeScript 6 may coexist temporarily only for a
separately identified role that still requires its older compiler API or an
embedded-language integration, with an explicit retirement condition.

## Human product authority and Codex reviewer role

```text
The human product owner decides:
  product priority
  acceptable scope
  release intent
  whether Medium/Low debt is acceptable
  whether to continue another hardening round
  whether to narrow the profile
  whether a candidate is fundamentally unfit
  whether to abandon or reject

Codex decides:
  whether evidence is truthful
  whether tests and target gates pass
  defect severity
  whether integration gates are met
  whether rollback is available
  what repair is technically recommended

Codex does not decide:
  that the product must never ship solely because another repairable defect
  appears after one correction
```

Critical or High defects block integration. Blocking integration is not
terminal rejection. Codex may recommend
`fundamentally-unfit-pending-human-decision`, but that disposition neither
removes nor rejects the candidate.

## Candidate lifecycle

The closed lifecycle vocabulary is:

```text
authored-proposed-unintegrated
reviewing
repair-required
ready-for-provisional-integration
provisionally-integrated-with-known-debt
provisionally-integrated
stable
fundamentally-unfit-pending-human-decision
rejected-preserved
```

`repair-required` preserves the candidate, exact input, findings, correction
evidence, and rollback while authorizing no integration.
`fundamentally-unfit-pending-human-decision` also preserves the candidate and
requires a human disposition. `rejected-preserved` requires explicit human
rejection authority and complete preserved history. Provisional integration
requires rollback and current release ownership. Stable maturity requires a
later, separately authorized maturity phase.

## Hardening rounds

One coherent correction remains the unit of one hardening round. A new
material defect found after that correction normally yields `repair-required`,
not rejection. The default budget is up to three hardening rounds. Each round
has a separate exact input, finding ledger, correction patch, corrected
hashes, fresh reviewers, and result. Rounds are not squashed, and an oracle is
not tuned invisibly after results are known.

After three rounds with Critical or High defects remaining, work stops for one
human choice: continue, narrow scope, defer, declare fundamentally unfit, or
abandon. The normative round mechanics are in the
[iterative hardening contract](../specs/language-profile-iterative-hardening-contract.md).

## Consequence-based severity

### Critical

Critical defects include data loss, credential exposure, security bypass,
unsafe irreversible action, a rights or source-integrity falsehood affecting
use, repository corruption, or deployment-damaging guidance. They block
integration.

### High

High defects include wrong guidance for a common in-scope target task, false
completion, a wrong owner that drops a required route, an invented or omitted
compiler role controlling behavior, a common target-scenario failure, an
unknown silently treated as known, or materially unavailable rollback. They
block integration.

### Medium

Medium defects include a bounded edge-case defect, an incomplete noncritical
route, a known unsupported scenario that fails safely, a secondary coverage
gap, or a noncritical evidence gap. They may remain only as explicit,
human-accepted debt.

### Low

Low defects include wording, navigation, metadata, bookkeeping, or
nonconsequential redundancy. They may remain only as explicit debt.

Severity follows consequence, not finding order, novelty, or review round.

## Review dispositions

The review dispositions are:

```text
ready-for-provisional-integration
accepted-with-known-debt
repair-required
fundamentally-unfit-pending-human-decision
```

`ready-for-provisional-integration` requires zero Critical and zero High
defects, passing target gates, safe stop or routing for unknowns, truthful
rights and source evidence, available rollback, and no false completion.

`accepted-with-known-debt` requires zero Critical and zero High defects and
only explicit Medium or Low debt. Every accepted debt has a named owner,
consequence, workaround or safe stop, repair and refresh conditions, rollback,
and explicit human acceptance.

`repair-required` preserves the candidate and blocks integration without
rejecting it.

`fundamentally-unfit-pending-human-decision` is reserved for a candidate with
no coherent owner, unsafe construction, a repair that would replace rather
than correct it, source or rights integrity that cannot be established, a
target that cannot exercise the product, common work routinely misrouted even
after narrowing, or repair cost disproportionate to product value. It is a
recommendation, not automatic deletion.

## Target-first validation

Acceptance priorities are ordered:

1. target usefulness;
2. safety and truthful uncertainty;
3. common semantic correctness;
4. owner and route correctness;
5. rollback and debt transparency;
6. representative breadth; and
7. exhaustive theoretical completeness.

A provisional profile need not model every language feature. It must be useful
and correct in its stated scope and stop or route outside that scope. Future
validation uses actual target-facing scenarios, APG-owned representative
fixtures, negative and near-miss cases, unknown-state controls, and rollback
controls. An intended-state fixture may model the planned TypeScript 7 target
while the live target remains older, but it must label that distinction and
must not claim that the live target has migrated. Every future phase freshly
pins current target objects.

## Proportionate evidence and historical patches

Evidence must be consequence-bearing and proportionate. Independent review
lanes establish independent reconstruction, but their free-form prose does not
become a product API or a routine release owner. Machine checks own closed
vocabularies, identities, exact source bindings, consequence-bearing routes,
stop conditions, lifecycle, and executable product behavior. Human review owns
the accuracy and sufficiency of explanatory prose. Compact explicit
adjudication is required for exact structured disagreements; equivalent prose
does not require item-level provenance.

Historical phase evidence remains auditable without remaining current release
authority. An evidence mechanism materially larger or more complex than the
product surface it protects is narrowed or retired instead of automatically
expanded. This proportionality rule changes no severity, source, target,
semantic, release, debt, or rollback gate.

Current authored evidence and public output contain no copied target
expression, and no phase may newly introduce one. Exact commits, exact patches,
and exact private Git-show reports are the narrow historical exception: they
may preserve bytes removed by an immutable correction as forensic evidence.
That exception does not make the bytes valid current evidence and does not
permit copying them into summaries, replacement lanes, fixtures, tests, or new
records. Exact reports containing removed historical bytes remain private and
must not be sanitized or falsified.

## Safe uncertainty, routing, and compiler roles

Unknown compiler roles, selected versions, consequence-bearing option values,
configuration, ownership, or runtime consequences stop the affected claim or
route it to the selecting owner. Package or lockfile presence does not prove
execution. One role does not prove another.

The compiler-role vocabulary is:

```text
CLI checker
declaration emitter
programmatic compiler API
editor/language service
embedded-language checker
source transformer or type stripper
build orchestrator
runtime host
```

Every future role record includes the role, selected package, exact version,
selection source, whether it is invoked, evidence, target or temporary state,
and retirement condition. Temporary TypeScript 6 compatibility is permitted
only when an exact role independently requires it.

## Minimum TypeScript production slice

The first TypeScript candidate covers ordinary `.ts` static semantics, `.mts`
and `.cts` boundaries, handwritten and generated declarations, the `.tsx`
ownership boundary, an Astro or equivalent embedded TypeScript boundary,
checked JavaScript as bounded TypeScript analysis, exact compiler roles and
versions, exact consequence-bearing option values, CLI versus embedded
checking, declaration-only emit, emitted JavaScript, the static/runtime
boundary, and safe stop or routing for unknown compiler or configuration
state.

Its initial exclusions are numeric structural policy, automatic
JavaScript-to-TypeScript migration, complete compiler-API modeling, complete
editor integration modeling, every historical compiler generation, and
runtime correctness beyond explicit boundaries. Structural policy remains
deferred.

## Intended-state TypeScript fixture

APG74 creates an APG-owned representative fixture containing:

```text
ordinary .ts
.mts
.cts
handwritten .d.ts
generated declaration
.tsx ownership boundary
Astro frontmatter or equivalent embedded TypeScript
checked JavaScript
TypeScript 7 CLI role
TypeScript 6 compatibility disposition case
declaration-only emit
emitted-JavaScript/runtime boundary
unknown compiler-role case
unknown option-state case
```

The TypeScript 6 compatibility-disposition case always exists. It records
either an independently required bounded TypeScript 6 role with its retirement
condition or explicit `not-required`/absent evidence and non-applicability.
Actual TypeScript 6 use remains conditional and role-bound.

The fixture labels intended product state, live target state, temporary
compatibility, and retirement condition. It does not copy target source.

## TypeScript provisional-integration gate

TypeScript provisional integration requires a green target-facing TypeScript
suite and intended-state fixture; zero Critical and High defects; stop or
route behavior for an unknown compiler role or option value; rejection of
static-to-runtime false completion; preserved declaration provenance; an
explicit, bounded temporary TypeScript 6 role when independently required;
proven rollback; and explicit human acceptance of every remaining Medium or
Low debt. Essential priority never waives Critical or High defects.

## Known-debt gate

Every provisionally integrated profile with debt records:

```text
debt ID
severity
affected scope
known consequence
why integration remains safe
workaround or stop behavior
owner
repair condition
refresh condition
rollback relevance
target impact
human acceptance reference
```

No Critical or High debt may enter provisional integration. Debt is current
and discoverable without requiring a large generic tracker.

The current bounded register, when debt exists, is
[`language-profile-known-debt.json`](language-profile-known-debt.json), with a
public-safe explanation in
[`language-profile-known-debt.md`](language-profile-known-debt.md).

## Provisional integration and maturity

A provisionally integrated profile requires a canonical leaf, catalog row,
projection, provisional maturity, bounded routes, project ownership only when
selected, current release ownership, focused tests, test inventory, rollback,
target acceptance evidence, and a known-debt record when applicable.
Provisional does not mean complete or stable. Stable maturity requires a later
phase.

## Corrected-state preservation, rejection, and rollback

Every hardening round preserves its exact input, complete material findings,
actual correction patch, corrected hashes, fresh review, and result. A blocked
integration does not authorize removal. Future rejection requires explicit
human authority.

Before removal, preserve the candidate commit, final correction patch, tests
and target evidence needed to understand the result, rejection reason,
removal patch, rollback, and complete history. Never raw-revert history to
erase an evidence-bearing candidate.

Rollback must identify the exact integrated surfaces, restore the prior
current release and routing state, preserve unrelated work, and have evidence
proportional to the integration claim.

## Recovery boundaries for CSS and JavaScript

CSS and JavaScript remain absent. Rejected ADRs remain rejected. A future CSS
candidate uses a new ADR and may reuse historical evidence without silently
reactivating rejected ADR 0036 or its universal `record-growth-state`
obligation. A future JavaScript candidate is a narrow ECMAScript-language
owner for an established `.js`, `.mjs`, or `.cjs` region; Node, browser,
TypeScript/JSX, loading, security policy, and transformation remain adjacent
owners. The first JavaScript slice does not recreate the comprehensive APG67
or APG69 architecture. Structural policy remains deferred.

## Future phase sequence

The intended roadmap identities are:

- APG74 — Claude TypeScript Language-Profile Candidate and Intended-State
  Target Harness; exit 00107; ADR 0043 Proposed; no integration.
- APG75 — Codex TypeScript Iterative Hardening and Provisional Integration;
  exit 00108; decide ADR 0043; up to three rounds.
- APG76 — CSS Candidate Recovery and Provisional Integration; exit 00109;
  ADR 0044.
- APG77 — Narrow JavaScript Core Candidate and Provisional Integration; exit
  00110; ADR 0045.

These are roadmap identities only. Each phase requires separate human
authorization. APG73 begins none of them.

## Refresh and supersession

Each recovery phase freshly verifies its predecessor, current target objects,
compiler-role selections, exact compiler versions, rights, release ownership,
and rollback surface. Drift stops the phase until disposition. A later charter
or exception supersedes this one only through explicit human authority and a
later Accepted ADR that names the changed rule and preserved history.
