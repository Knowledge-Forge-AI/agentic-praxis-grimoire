# Legacy Roadmap Closure

## Purpose

This ledger closes every former unnumbered candidate or explicitly deferred
v0.1 theme. Closure means that APG has accepted either a completed artifact, a
future active v0.2 owner, a conditional research boundary, or a terminal
rejection/project owner. Historical assignment to a later phase did not itself
mean the work was implemented; the ledger now records completed APG12 through
APG14 artifacts.

Stable legacy IDs preserve a one-to-one source identity even where older
roadmaps grouped several questions in one row. Composite themes retain explicit
sub-dispositions rather than being forced into a misleading single
implementation state.

## Disposition vocabulary

- `implemented`: the APG-owned question has an accepted current artifact;
- `implemented-by-APG11`: APG11 supplies the accepted artifact;
- `implemented-by-APG12`: APG12 supplies the accepted artifact;
- `implemented-by-APG13`: APG13 supplies the accepted artifact;
- `implemented-by-APG14`: APG14 supplies the accepted artifact;
- `future-active`: an accepted future v0.2 phase owns implementation;
- `conditional`: no implementation is promised unless the stated condition is
  met; and
- `rejected-or-project-owned`: APG does not intend another artifact.

Every row below is `closed` as a legacy-roadmap question. Future-active rows
remain incomplete as implementation.

## Terminal ledger

| ID | Original theme | Final APG11 disposition | Owner or artifact | Evidence | Rationale and reconsideration condition | Closed |
| --- | --- | --- | --- | --- | --- | --- |
| `LT01` | Publication-surface validation | `implemented-by-APG12` | [ADR 0009](adr/2026/07/0009-public-distribution-and-reproducible-release-validation.md), [release process](public-release-process.md), and `apg-public-release` | [APG12 evaluation](evaluations/apg12-public-distribution-and-release-validation.md) | Exact non-private projection, critical-owner policy, and executable regression now detect the public v0.1.0 omitted-wrapper class. | Yes |
| `LT02` | Skill authoring and bounded maintenance checks | `implemented-by-APG11` | [Authoring and maintenance guide](skill-authoring-and-maintenance.md), [ADR 0008](adr/2026/07/0008-skill-authoring-maintenance-and-mechanical-validation.md), and `apg-check-skill-library` | [APG11 evaluation](evaluations/apg11-skill-authoring-maintenance-and-roadmap-closure.md) | Repeated APG4-APG10 practice supports one maintainer procedure and narrow mechanical checker, not another skill or generalized framework. | Yes |
| `LT03` | Generalized prompt scoring | `conditional` | No active implementation owner | [ADR 0006](adr/2026/07/0006-v0-2-objectives-roadmap-and-maturity-promotion.md); [bootstrap model](bootstrap-v0.1.md) | Reconsider only when a supported isolated evaluation can freeze treatment, claims, scenarios, scoring, reviewer contract, variance handling, and rollback before results. | Yes |
| `LT04` | Systematic debugging and fresh verification | `implemented` | `debugging-systematically` and `reviewing-and-verifying-repository-work` | [Provenance](provenance.md); [APG9 evaluation](evaluations/apg9-v0-1-closeout-and-v0-2-roadmap.md) | The reusable procedures exist and have real-use evidence. APG13 reviews maturity rather than reimplementing them. | Yes |
| `LT05` | Planning and design | `implemented` | `planning-repository-work` and `designing-significant-changes` | [Provenance](provenance.md); [APG9 evaluation](evaluations/apg9-v0-1-closeout-and-v0-2-roadmap.md) | Existing leaves own dependent execution planning and consequential design. APG13 reviews maturity. | Yes |
| `LT06` | Implementation and proportional test discipline | `implemented` for the reusable procedure; universal runner, coverage, and duplicated language policy are `rejected-or-project-owned` | `implementing-with-test-discipline` plus repository policy | [Bootstrap model](bootstrap-v0.1.md); [APG10 evaluation](evaluations/apg10-karpathy-guidelines-evaluation.md) | The leaf owns proportional behavioral evidence. Exact runners, thresholds, and language policy remain repository-owned. | Yes |
| `LT07` | Review and generic delivery | `implemented` for evidence-first review; generic delivery is `rejected-or-project-owned` | `reviewing-and-verifying-repository-work`; native harness and project policy for delivery | [Superpowers transition](superpowers-transition.md); [bootstrap model](bootstrap-v0.1.md) | Review is implemented. Branch, pull-request, worktree, push, release, cleanup, and handoff mechanics do not justify one universal APG delivery workflow. | Yes |
| `LT08` | Language and project-standard profiles | `conditional` | No active implementation owner | [ADR 0006](adr/2026/07/0006-v0-2-objectives-roadmap-and-maturity-promotion.md) | Reconsider only after multiple validated skills demonstrate that repository instructions are repeatedly insufficient. | Yes |
| `LT09` | Repository-local Codex discovery | `implemented` | Checked-in `.agents/skills` projection from APG4A | [APG4A exit](status/2026/07/18/00007-apg4a-codex-repository-skill-discovery-exit.md) | Six relative links expose one canonical library without content duplication. | Yes |
| `LT10` | Opted-in project-local projection lifecycle | `implemented` | [ADR 0004](adr/2026/07/0004-project-local-skill-projection-and-rollback.md), `apg-project-skills`, and the [projection guide](project-skill-projection.md) | [APG7 evaluation](evaluations/apg7-project-local-projection-tooling.md); [APG7A exit](status/2026/07/19/00011-apg7a-idempotent-projection-compliance-correction-exit.md) | Install, adopt, check, uninstall, ownership, refusal, and rollback have executable evidence. | Yes |
| `LT11` | Public-sourced user-global integration | `implemented-by-APG12` | [User-scoped integration guide](user-scoped-skill-integration.md) and `apg-user-skills` | [ADR 0009](adr/2026/07/0009-public-distribution-and-reproducible-release-validation.md); [APG12 evaluation](evaluations/apg12-public-distribution-and-release-validation.md) | Verified public-source install, adopt, check, update, rollback, uninstall, restart, recovery, and duplicate-warning semantics are implemented; active migration remains separately authorized. | Yes |
| `LT12` | Additional harness adapters or packages | `conditional` | No active implementation owner | [Project model](project-model.md); [ADR 0006](adr/2026/07/0006-v0-2-objectives-roadmap-and-maturity-promotion.md) | Reconsider only when a named harness demonstrates a separate need, compatibility contract, rollback boundary, and authority. | Yes |
| `LT13` | Licensing and contribution governance | `implemented` | [ADR 0005](adr/2026/07/0005-public-license-and-contribution-governance.md) and aligned governance files | [Roadmap](roadmap.md) | The accepted public license, commercial option, CLA terms, notices, and contribution acknowledgment answer the APG-owned question. | Yes |
| `LT14` | Public repository creation | `implemented` | Public v0.1.0 repository projection | [APG9 evaluation](evaluations/apg9-v0-1-closeout-and-v0-2-roadmap.md); [APG9 exit](status/2026/07/19/00014-apg9-v0-1-release-decommission-and-v0-2-roadmap-exit.md) | Public v0.1.0 exists. Its wrapper omission is `LT01`, not a reason to reopen repository creation. | Yes |
| `LT15` | Public v0.2 projection | `implemented-by-APG14` | [APG14 evaluation](evaluations/apg14-v0-2-release-candidate-and-publication.md) and [release process](public-release-process.md) | [ADR 0006](adr/2026/07/0006-v0-2-objectives-roadmap-and-maturity-promotion.md) | APG14 builds and independently verifies the deterministic candidate, publishes one appended squashed release commit and annotated tag, and preserves the fresh-session application smoke as an external gate. | Yes |
| `LT16` | Release cadence | `rejected-or-project-owned` | Human maintainer | [ADR 0006](adr/2026/07/0006-v0-2-objectives-roadmap-and-maturity-promotion.md) | Cadence and version timing are publication choices, not a reusable APG procedure. | Yes |
| `LT17` | Hosted services | `conditional` | No active implementation owner | [ADR 0006](adr/2026/07/0006-v0-2-objectives-roadmap-and-maturity-promotion.md) | Reconsider only with a concrete service, safety model, operator, and explicit authority. | Yes |
| `LT18` | Autonomous worker infrastructure | `rejected-or-project-owned` | Native harness behavior and the [manager-worker protocol](manager-worker-protocol.md) | [Superpowers transition](superpowers-transition.md); [ADR 0006](adr/2026/07/0006-v0-2-objectives-roadmap-and-maturity-promotion.md) | APG does not need a scheduler, runtime, epic controller, or additional execution-controller skill. | Yes |
| `LT19` | Telemetry | `conditional` | No active implementation owner | [ADR 0006](adr/2026/07/0006-v0-2-objectives-roadmap-and-maturity-promotion.md) | Reconsider only with a concrete decision deficit, privacy-safe contract, retention rules, and explicit authority. | Yes |
| `LT20` | Wholesale source migration | `rejected-or-project-owned` | Selective APG evaluation and provenance policy | [Provenance](provenance.md); [ADR 0006](adr/2026/07/0006-v0-2-objectives-roadmap-and-maturity-promotion.md) | APG evaluates and selectively synthesizes practices; it does not migrate a source methodology wholesale. | Yes |
| `LT21` | Broader dogfooding and individual maturity | `implemented-by-APG13` | [ADR 0010](adr/2026/07/0010-six-skill-post-superpowers-stability-dispositions.md) and [APG13 evaluation](evaluations/apg13-six-skill-post-superpowers-stability-review.md) | Historical matrix, frozen applications, regressions, and final reviews | APG13 inventories each skill's evidence distribution and records six `stable` dispositions without treating distribution or non-triggers as positive use. | Yes |
| `LT22` | Clean baseline-versus-treatment comparison | `conditional` | No active implementation owner and not a `stable` prerequisite | [ADR 0006](adr/2026/07/0006-v0-2-objectives-roadmap-and-maturity-promotion.md); [bootstrap model](bootstrap-v0.1.md) | Reconsider only with supported baseline isolation, controlled candidate availability, observable invocation where claimed, sealed evidence, and a frozen evaluation contract. | Yes |
| `LT23` | Superpowers decommission, rollback, preservation, and bounded smoke | `implemented` with recorded limitations | Human decommission action, transition/runbook records, and APG9 smoke | [Superpowers transition](superpowers-transition.md); [APG9 evaluation](evaluations/apg9-v0-1-closeout-and-v0-2-roadmap.md) | Decommission, source preservation, rollback instructions, and bounded smoke are complete. Exhaustive inventory, universal workflow coverage, comparative superiority, and successful restoration remain unverified limitations rather than open implementation. | Yes |
| `LT24` | Post-Superpowers skill review | `implemented-by-APG13` | [ADR 0010](adr/2026/07/0010-six-skill-post-superpowers-stability-dispositions.md) and [APG13 evaluation](evaluations/apg13-six-skill-post-superpowers-stability-review.md) | Six post-Superpowers suitability reviews | Each current leaf has post-retirement positive or direct-review evidence and no retired-tool dependency. | Yes |

## Coverage and owner audit

The ledger contains 24 stable IDs and 24 rows. Each assignment theme appears
once. `LT21` and `LT24` remain distinct questions completed by one phase:
evidence breadth and maturity disposition versus explicit suitability after the
Superpowers transition. `LT06` and `LT07` retain their implemented and
project-owned sub-dispositions rather than implying universal test or delivery
machinery.

Category totals are nine `implemented`, one `implemented-by-APG11`, two
`implemented-by-APG12`, two `implemented-by-APG13`, one
`implemented-by-APG14`, six `conditional`, and three
`rejected-or-project-owned`. No future-active row remains and no duplicate
implementation artifact is introduced.

APG12A subsequently corrects the lineage and read-only enforcement of the
existing `LT01` and `LT11` artifacts. It does not add or reopen a ledger row,
change any disposition count, begin a future owner, or claim that the original
APG12 implementation already contained the correction.
