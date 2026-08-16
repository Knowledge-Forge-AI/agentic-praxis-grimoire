# APG73 Language-Profile Production Recovery Charter

## Outcome

APG73 is complete as a governance correction. ADR 0042 is Accepted. The
[production recovery charter](../governance/language-profile-production-recovery-charter.md)
and [iterative hardening contract](../specs/language-profile-iterative-hardening-contract.md)
replace automatic rejection after one correction with bounded iterative
hardening for future production-recovery phases.

No CSS, JavaScript, TypeScript, JSX, or adjacent profile was authored or
integrated. APG74 and every successor remain unbegun and require separate
human authority.

## Baseline and historical preservation

APG73 began from exact APG72 after fresh ancestry, tree, managed-report,
branch-parity, record-identity, integration-count, decision-state, release, and
read-only target verification. APG72 and earlier commits and reports are
unchanged.

ADRs 0031, 0034, 0035, 0036, 0039, 0040, and 0041 remain Rejected. Their
findings remain valid evidence. The new charter changes the future disposition
rule; it does not say that an earlier reviewer was wrong under the earlier
rule, amend a rejected ADR, or silently reactivate a candidate.

Markdown remains retained provisional under ADR 0037 and ADR 0038, both
Accepted with amendment. Development remains 29 canonical skills, 29 catalog
rows, and 29 projections; 14 stable and 15 provisional rows; 27 general routes,
one ChatGPT-local route, and 28 checked edges. CSS, JavaScript, and TypeScript
skills remain absent. Corrected public and active v0.4.0 and both read-only
targets remain unchanged.

## Why the experimental rule changed

The one-correction rule was useful experimentally. It forced an architecture
to expose its initial material defect family, limited hidden oracle tuning,
and made a fresh review genuinely independent. Across CSS, JavaScript, and
TypeScript it also preserved valuable corrections and precise failure
evidence.

For production recovery, the rule made finding order terminal. A fresh
repairable defect after the sole correction forced rejection even when the
candidate had improved, remained useful, and had not been shown fundamentally
unfit. Rejection therefore did not prove that CSS, JavaScript, or TypeScript
profiles were impossible or valueless.

The production rule preserves evidence discipline while changing disposition:
one coherent correction is still the unit of one round, but a new material
defect normally produces `repair-required`. Up to three separately evidenced
rounds are available by default. If Critical or High defects remain after the
third round, a human chooses whether to continue, narrow, defer, declare
fundamental unfitness, or abandon.

## Authority and dispositions

The human product owner controls priority, acceptable scope, release intent,
Medium or Low debt acceptance, additional rounds, narrowing, fundamental
unfitness, abandonment, and rejection. Codex controls evidence truth, test and
target results, consequence-based severity, integration gates, rollback
availability, and technical repair recommendations.

Codex may block integration for Critical or High defects. That block is not
terminal rejection. Codex may recommend
`fundamentally-unfit-pending-human-decision`, but only the human product owner
may make the terminal product decision.

The review dispositions are `ready-for-provisional-integration`,
`accepted-with-known-debt`, `repair-required`, and
`fundamentally-unfit-pending-human-decision`. Provisional integration requires
zero Critical and High defects. Medium and Low debt may remain only when each
item is explicit, safely bounded, owned, refreshable, rollback-aware, and
human accepted.

## Product priorities and TypeScript intent

TypeScript is essential. CSS and JavaScript are desirable and do not block
TypeScript delivery. JSX is deferred.

The maintained theme target's current older TypeScript snapshot is the
migration baseline, not the intended final generation. TypeScript 7 is the
intended primary compiler generation. A future implementation phase freshly
selects the exact current TypeScript 7 patch and separately records every
compiler role. Temporary TypeScript 6 compatibility is permitted only for an
exact role that still requires the older API or embedded integration and has a
retirement condition.

The role model separates the CLI checker, declaration emitter, programmatic
compiler API, editor or language service, embedded-language checker, source
transformer or type stripper, build orchestrator, and runtime host. Package or
lockfile presence never proves that any role executed, and one role never
proves another. APG73 does not claim that either live target already uses
TypeScript 7.

## Target-first acceptance

Future acceptance prioritizes target usefulness, safe and truthful
uncertainty, common semantic correctness, owner and route correctness, rollback
and debt transparency, representative breadth, and finally exhaustive theory.
Unknown compiler, configuration, option, owner, or runtime state stops or
routes the affected claim.

The first TypeScript production slice covers ordinary `.ts`, `.mts`, `.cts`,
handwritten and generated declarations, `.tsx`, embedded TypeScript, checked
JavaScript, exact compiler roles and option values, CLI versus embedded
checking, declaration-only emit, emitted JavaScript, and the static/runtime
boundary. Structural policy, numeric bands, automatic JavaScript-to-TypeScript
migration, complete compiler API and editor modeling, and universal historical
generation coverage are excluded initially.

An intended-state fixture may model the planned TypeScript 7 product while the
live target remains older only when intended state, live state, temporary
compatibility, and retirement conditions are explicit. Future phases freshly
pin current target objects.

## Retrospective

- CSS was rejected after its sole correction introduced an overbroad six-case
  `record-growth-state` obligation. It was not proven fundamentally unfit.
- JavaScript preserved useful corrections and was rejected because fresh
  review found more material defects after the sole allowed correction. It was
  not proven valueless.
- APG72 materially improved TypeScript role, option, evidence, source-kind,
  artifact, route, and signal modeling. Fresh review found further repairable
  defects. TypeScript was not proven unwanted or impossible.

The shared terminal pattern reflects the review lifecycle as much as product
quality. Future recovery preserves evidence discipline and changes the
automatic terminal disposition.

## Roadmap without execution authority

The intended order is APG74 for a Claude TypeScript candidate and
intended-state target harness, APG75 for Codex iterative hardening and possible
provisional integration, APG76 for CSS recovery, and APG77 for a narrow
JavaScript core candidate. APG74 uses exit 00107 and proposes ADR 0043; APG75
uses exit 00108 and decides it; APG76 uses exit 00109 and ADR 0044; APG77 uses
exit 00110 and ADR 0045.

Those are roadmap identities only. APG73 recommends APG74 but grants no APG74
or successor authority.

## Verification boundary

Fresh resulting-state checks cover APG72 identity and its exact four-record
omnibus, fetched main and APG72 branch equality, immutable rejected ADR and
Markdown fingerprints, development counts and routes, profile absence, ADR
0042 and record identity, charter/contract/ADR consistency, product priority,
TypeScript 7 and temporary TypeScript 6 wording, round budget, severity and
debt gates, human rejection authority, roadmap state, public and active
fingerprints, read-only target objects, links, privacy, rights, structure,
change size, whitespace, complete diff, formal commit message, managed report,
and final fetched parity.

No maintained executable, fixture, support, or test owner changed, so the full
APG regression suite was not run. No target command, profile authoring,
candidate test, integration, release, readiness, publication, deployment,
APG74, or successor work ran.
