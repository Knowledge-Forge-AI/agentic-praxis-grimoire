# ADR 0006: v0.2 Objectives, Roadmap, and Maturity Promotion

## Status

Accepted

## Date

2026-07-19

## Acceptance authority

The human maintainer's APG9 assignment accepts this decision. It authorizes
v0.1 closeout, current-document reconciliation, and a bounded v0.2 roadmap. It
does not authorize APG10, skill edits or promotion, public-repository changes,
Superpowers restoration, or v0.2 publication.

## Context

APG v0.1.0 has been published through one intentionally squashed public commit.
The public checkout supplies the maintainer's user-global Codex integration.
The private development history remains distinct and has advanced through
APG-TEST0, which established the project test layout and the 22-family Bats and
28-family Python integration suites.

The maintainer has decommissioned Superpowers. A fresh post-decommission
RepoMap session discovered all six APG skills, explicitly selected and applied
the review skill, passed the default and explicit managed checks, preserved a
clean RepoMap worktree, and did not use Superpowers as workflow authority. The
preserved Superpowers source remains historical external evidence.

The public v0.1.0 projection also exposes a release-process defect: it documents
the project-local projection command and contains its implementation modules,
but omits the tracked `bin/apg-project-skills` wrapper. APG9 records that
limitation without modifying or republishing v0.1.0. A validated public
projection and release process must prevent this class of omission in v0.2.

The six current skills remain `provisional`. Their accumulated scenario,
real-use, non-trigger, correction, regression, rollback, and post-decommission
evidence warrants an individual stability review. It does not authorize
promotion during APG9. Clean baseline-versus-treatment superiority evidence is
absent, but that absence is not itself a promotion blocker.

The current roadmap also contains unnumbered themes whose original questions
have been answered by v0.1 artifacts, remain project-owned, need a concrete
v0.2 owner, or require an explicit reconsideration condition. Leaving that
section open would obscure completion of the v0.1 epic.

## Decision

### v0.1 closure

1. Public v0.1.0 is accepted as published through intentionally squashed public
   history, distinct from private development history.
2. The public repository is the canonical source for the maintainer's
   user-global APG integration.
3. Superpowers decommission is accepted as an explicit human decision, with
   bounded post-decommission APG and RepoMap smoke passed.
4. This APG9 human mandate supplies APG8's requested final external acceptance.
   APG0 through APG8 form the closed v0.1 development epic, with APG3's blocked
   terminal outcome and all other historical dispositions preserved. Historical
   coexistence, provisional, readiness, and next-gate statements remain true
   for their recorded phase state and are not rewritten as current policy.
5. APG-TEST0 is the first post-v0.1 development-foundation phase.
6. The omitted public command wrapper is a recorded v0.1 limitation and an
   APG12 release-validation requirement, not authority for an APG9 public fix.

### v0.2 objectives

v0.2 must:

1. evaluate and selectively integrate useful Karpathy Guidelines ideas without
   adding a seventh overlapping skill by default;
2. close every remaining legacy roadmap theme through implementation,
   satisfaction, formalization, conditional deferral, or rejection;
3. formalize public-sourced user-global install, update, check, uninstall,
   rollback, restart, and duplicate-name behavior;
4. implement public-projection and squashed-release validation, including
   executable-wrapper, licensing, notice, test, link, and metadata checks;
5. establish one minimal reusable skill-authoring and maintenance procedure;
6. perform an individual post-Superpowers review of all six skills;
7. promote every passing skill to `stable`, leaving only a skill with an
   unresolved material defect non-stable under a recorded correction condition;
8. publish and verify a public v0.2.0 projection; and
9. preserve public-safe history and publication-excluded exact evidence.

### Maturity promotion policy

`stable` requires repeated real use, representative non-triggers, no unresolved
material authority, privacy, safety, or procedure defect, an explicit
post-Superpowers review, and a supported removal or rollback path. Publication
and global installation are useful integration evidence but do not independently
establish maturity.

This decision refines ADR 0003's bootstrap minimum for v0.2: cross-repository
breadth remains material evidence to inspect and report, but the absence of a
positive use in a second repository is not independently a material defect.
Repeated positive use may be established within APG, in additional
repositories, or through both. Representative non-triggers remain a separate
requirement and do not count as positive use. This refinement follows the
human mandate to target all six for stability while permitting only a concrete
material defect to block an individual skill.

Each skill receives an individual APG13 disposition. One bounded correction per
skill may be made and its affected scenarios and regression gates rerun. A
skill that still has a material defect remains non-stable with a concrete
correction condition. `stable` does not mean universal applicability,
production warranty, automatic selection, or comparative superiority. Clean
A/B evidence may be pursued under the existing isolation conditions, but it is
not a prerequisite for promotion.

### Karpathy Guidelines policy

The tracked Karpathy Guidelines source remains experimental evidence until
APG10. APG will synthesize rather than copy by default. The source's declared
MIT frontmatter does not replace exact upstream provenance, license, and notice
review before any copied or adapted use.

The likely destination is a targeted refinement to an existing owner or a
small cross-cutting project standard. Source packaging does not justify a
seventh broad coding-guidelines skill. APG10 owns the final adopt, defer, or
reject disposition, including the tension between mandatory escalation for
every ambiguity and APG's proportional progress under reversible uncertainty.

### Accepted sequence

#### APG10 — Karpathy evaluation and selective integration

Compare the experimental source with current APG policy and the six skills,
test actual gaps, and make only supported targeted corrections. At most one
correction per skill is allowed. A seventh skill requires a separate
consequential decision. APG10 owns final adopt, defer, and reject dispositions.

#### APG11 — Skill authoring, maintenance, and legacy-roadmap closure

Evaluate and formalize the existing lifecycle, provenance, scenario,
maintenance, and rollback practices as a minimal reusable procedure, justified
by their repeated use across APG4 through APG9. This does not require a new
skill. Add deterministic checks
only for stable mechanical invariants demonstrated by repeated work. Record a
terminal disposition for every legacy theme and close the candidate-theme
section without building a generalized evaluator or prompt-scoring framework.

#### APG12 — Public distribution and release validation

Formalize public-sourced global integration and its update, check, uninstall,
rollback, restart, and duplicate-scope behavior. Implement a public-projection
validator and reproducible squashed-release process. The validator must detect
the v0.1 omitted-wrapper class and verify licensing, notices, tests, release
metadata, public/private separation, and the intended tracked surface.

#### APG13 — Six-skill post-Superpowers stability review

Review each skill separately with positive, non-trigger, edge or stop, and
real-repository evidence. APG10 owns Karpathy-derived deltas; APG13 may correct
only a residual material defect exposed by maturity review. Permit one bounded
material correction per skill,
promote passing skills to `stable`, record a correction condition for any
blocked skill, and produce the release-candidate maturity matrix.

#### APG14 — v0.2.0 release candidate and publication

Run the complete gates, verify public global integration against the candidate,
create and verify the squashed public v0.2.0 projection, and record release
closeout. APG14 does not begin until separately authorized.

No phase begins automatically. This sequence is not a preapproved roadmap
envelope: APG10, APG11, APG12, APG13, and APG14 each require a separate human
assignment before work begins.

### Legacy-theme ownership and disposition

| Theme | Preliminary terminal disposition |
| --- | --- |
| Publication-surface validation | Implement in APG12. |
| Skill authoring and bounded mechanical maintenance checks | Formalize and implement in APG11. |
| Generalized prompt scoring | Defer until a supported isolated evaluation can freeze treatment and scoring before results. |
| Debugging, verification, planning, design, implementation discipline, and evidence-first review | Satisfied by the six current skills; APG13 reviews maturity rather than reimplementing them. |
| General test runner, universal coverage threshold, and duplicated language policy | Reject as unnecessary or project-owned. |
| Generic delivery workflow and autonomous worker infrastructure | Reject as native or project-owned; no additional execution-controller skill is justified. |
| Language or project-standard profiles | Defer until multiple validated skills show repository instructions are repeatedly insufficient. |
| Repository-local Codex projection and project-local lifecycle | Satisfied by APG4A and ADR 0004. |
| Public-sourced maintainer global integration | Formalize in APG12. |
| Additional non-Codex harness adapters or packages | Defer until a named harness demonstrates a separate need and rollback contract. |
| Licensing and contribution governance | Satisfied by ADR 0005 and the aligned governance files. |
| Public repository creation | Satisfied by v0.1.0 publication. |
| Public v0.2.0 projection | Implement in APG14. |
| Release cadence | Reject as a maintainer-owned publication choice. |
| Hosted services | Defer pending a concrete service, safety model, operator, and explicit authority. |
| Telemetry | Defer pending a decision deficit, privacy-safe contract, retention rules, and explicit authority. |
| Wholesale source migration | Reject; APG selectively evaluates and synthesizes practices. |
| Broader dogfooding and individual maturity dispositions | Implement in APG13. |
| Clean baseline-versus-treatment comparison | Conditionally defer; it is not a stability prerequisite. |
| Superpowers decommission, rollback plan, source preservation, and bounded smoke | Satisfied by the human action and existing records; APG9 reconciles current state. |
| Post-Superpowers skill review | Implement in APG13. |

## Alternatives considered

### Promote all six skills immediately

Rejected. Current evidence makes all six credible candidates but APG13 still
owes individual review, final correction handling, rollback confirmation, and
explicit dispositions.

### Require clean A/B superiority before promotion

Rejected as a mandatory gate. The supported harness has not yet supplied the
necessary isolation and invocation evidence, and absence of that comparison is
not a material authority, privacy, safety, or procedure defect.

### Add the Karpathy Guidelines unchanged as a seventh skill

Rejected. It overlaps current owners, includes absolute guidance that conflicts
with proportional escalation, and would require complete provenance and notice
review for copied or adapted expression.

### Evaluate targeted integration

Accepted. APG10 can preserve useful principles while placing each gap in the
artifact that owns it and avoiding duplicated workflow policy.

### Keep installation project-local only

Rejected as the complete v0.2 distribution model because the maintainer now
uses a public-sourced global integration. Project-local projection remains
supported for repository-specific discovery and rollback.

### Formalize public global integration

Accepted for APG12. The current practice must become reproducible and
verifiable without turning `apg-project-skills` into a global installer.

### Continue manual releases without a validator

Rejected. The v0.1 wrapper omission demonstrates that documentation review and
an otherwise valid public surface do not prove projection completeness.

### Adopt a validated release pipeline

Accepted for APG12 and APG14. It must remain narrow, deterministic, and owned
by demonstrated projection and release invariants rather than becoming a
general framework.

### Leave the old roadmap open

Rejected. Its broad headings now mix satisfied questions, project-owned policy,
conditional deferrals, and concrete v0.2 work.

### Close the old roadmap under a bounded v0.2 sequence

Accepted. APG10 through APG14 give every remaining theme an owner or terminal
disposition while preserving separate phase authorization.

## Consequences

- APG0 through APG8 can be treated as the closed v0.1 epic without rewriting
  their historical exits or contemporaneous state claims.
- APG-TEST0 remains the first post-v0.1 development foundation.
- All six skills remain `provisional` until APG13.
- APG12 must correct the public release-process gap demonstrated by v0.1.
- Karpathy material remains experimental and cannot enter APG by packaging or
  familiarity alone.
- The public and private histories remain independent, and exact operational
  evidence remains publication excluded.

## Deferred decisions

- the APG10 adopt, defer, and reject results;
- the exact APG11 reusable procedure and mechanical checks;
- the APG12 validator interface and distribution commands;
- every APG13 individual maturity disposition;
- the APG14 release candidate and publication operation;
- clean comparative evaluation until its isolation requirements are met; and
- any additional skill, harness adapter, hosted service, telemetry system, or
  release cadence.
