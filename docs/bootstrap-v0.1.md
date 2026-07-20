# APG v0.1 Bootstrap Model

## Purpose

APG v0.1 is the historical bootstrap model for a small engineering-loop skill
bundle. It was designed for bounded dogfooding during Superpowers coexistence
and provides six independently removable procedures for worker assignments,
significant-change design, repository planning, implementation evidence,
debugging, and review and verification.

The bootstrap phase did not itself publish a release, establish a final
taxonomy or compatibility framework, or prove APG superior to ordinary Codex
or Superpowers. Public v0.1.0 was subsequently published with intentionally
squashed history. The maintainer later decommissioned Superpowers and accepted
a bounded post-decommission RepoMap smoke. Those later facts do not rewrite the
bootstrap evidence. APG13 subsequently promoted the current six leaves under a
separate individual review.

## APG13 subsequent disposition

APG13 accepts ADR 0010 and promotes all six current catalog entries to
`stable`. Each leaf has repeated positive real use, representative
non-triggers, edge or stop evidence, post-Superpowers suitability, a supported
rollback owner, current mechanical regression, and a fresh non-author final
review. No APG13 procedure correction was required, so all six `SKILL.md` files
remain byte-identical to the APG12A baseline. Historical provisional statements
below retain their phase meaning; public v0.1.0 and active public-backed
integration remained unchanged until APG14. APG14 publishes the six stable
leaves as public v0.2.0 and fast-forwards the existing public-backed source
without rewriting this historical bootstrap model.

## APG9 subsequent disposition

APG0 through APG8 are the closed v0.1 epic, with APG3's blocked terminal
outcome preserved. APG-TEST0 is the first
post-release development foundation. All six skills remain `provisional` until
the individual APG13 post-Superpowers review defined by ADR 0006. The public
release and user-global integration are distribution evidence, not maturity by
themselves.

## APG10 subsequent disposition

APG10 retained the six-skill bootstrap shape and all six `provisional`
maturity states. Concealed-source scenarios found the existing design,
planning, and review boundaries adequate for assumptions, alternatives,
traceability, speculative scope, proportional reversible progress, and
project-owned policy. Two independent scenarios demonstrated one implementation
completion gap for locally owned code or test artifacts made unnecessary solely
by the authorized change. One bounded implementation-leaf correction closed the
gap without changing its trigger, test proportionality, unrelated-cleanup
boundary, or project-owned removal policy.

This evidence remains bounded textual validation. It does not promote the
implementation skill, alter the APG13 stability gate, add a seventh skill, or
establish clean comparative improvement.

## APG11 subsequent disposition

APG11 formalizes skill-specific authoring and maintenance in the
[maintainer guide](skill-authoring-and-maintenance.md), accepts ADR 0008, adds a
read-only dependency-free mechanical skill-library checker, and closes the
legacy candidate-theme queue. The checker passed the six-skill development and
public v0.1.0 library shapes, but that structural result does not prove semantic
quality, client discovery, publication completeness, maturity, or stability.

The acceptance requirements below remain the historical v0.1 bootstrap basis.
The maintainer guide now owns future proportional application, correction,
deprecation, and removal. APG11 changes no skill leaf or maturity state; all six
remain `provisional`, and APG13 remains the only individual maturity phase.

## APG12 subsequent disposition

APG12 accepts ADR 0009 and adds exact public projection, reproducible local
candidate validation, and a verified public-sourced user-link lifecycle. Its
tests and disposable dogfood add distribution and rollback evidence without
changing any canonical leaf or checked-in projection. Release-tool success,
user-scope lifecycle success, and public availability are not semantic skill
evaluation or maturity evidence by themselves. All six remain `provisional`,
and APG13 retains all individual stability authority.

## Maturity states

| State | Meaning | Minimum transition evidence |
| --- | --- | --- |
| `bootstrap` | The procedure is being authored or corrected and is not yet accepted for routine use. | Coherent draft, known owner, and bounded evaluation plan. |
| `provisional` | The procedure may be used within recorded limits. | Valid leaf structure, positive and non-trigger scenarios, edge or escalation coverage, independent review, provenance, and a removal path. |
| `evaluated` | The procedure has completed an explicit evaluation under recorded conditions. | Accepted evaluation contract, reproducible evidence, stated limitations, and a recorded disposition. |
| `stable` | The procedure has survived repeated real use and transition review. | Repeated real use, representative non-triggers, no unresolved material authority, privacy, safety, or procedure defect, supported removal or rollback, and explicit post-Superpowers review. |
| `deprecated` | New use should stop while migration or removal completes. | Successor or removal guidance, affected references, and retained historical evidence. |

Maturity does not grant action authority. A stable skill still cannot exceed
the current human-authorized task or repository policy.

ADR 0006 refines the bootstrap table for v0.2. Cross-repository breadth remains
valuable evidence and must be reviewed per skill, but absence of a positive use
in a second repository or of clean A/B superiority is not by itself a material
defect. APG13 must record the actual evidence distribution and may block a skill
only on an unresolved material defect under the accepted v0.2 policy.

## Provisional evidence boundary

Provisional validation may establish that a skill:

- has valid metadata and a direct-child leaf;
- states a precise trigger and non-trigger boundary;
- produces a useful artifact or stop disposition in recorded examples;
- preserves authority, privacy, and project-policy boundaries;
- avoids unnecessary ceremony in its sampled non-trigger cases;
- records evidence, escalation, and rollback expectations; and
- survived independent review in the recorded repository state.

It does not establish:

- clean causal improvement over a baseline;
- statistical reliability or universal trigger precision;
- production readiness or stable maturity;
- fitness for every repository, model, harness, or risk class;
- absence of Superpowers from model context; or
- readiness to decommission Superpowers.

## Skill acceptance requirements

A v0.1 skill is retained as `provisional` only when it:

1. solves one coherent, reusable problem;
2. has valid `name` and trigger-focused `description` frontmatter;
3. defines explicit positive and negative activation boundaries;
4. states one core principle and a concise procedure;
5. separates reusable procedure from project-owned parameters;
6. defines evidence or completion expectations;
7. identifies stop and escalation conditions;
8. addresses common mistakes without copying repository-wide policy;
9. passes one positive, one non-trigger, and one edge or escalation scenario;
10. survives independent review for authority, proportionality, privacy,
    provenance, rollback, and source-expression independence; and
11. remains removable without a runtime, registry, adapter, or dependent
    compatibility layer.

A skill needing more than one bounded correction during APG4 is omitted and
recorded as deferred rather than expanded into an open-ended rewrite.

These requirements accept canonical procedure content. A skill is usable in a
target harness only after that harness has a supported discovery projection or
installation method that resolves to the accepted canonical leaf. Projection
availability does not by itself establish invocation success or dogfooding.

## Public and publication-excluded evidence

Publishable APG files identify generalized maintainer-authored evidence,
RepoMap, public specifications, and Superpowers under the MIT License where
material. They record derivation mode, maturity, validation class, limits, and
disposition without exposing private repositories, source topology, local
paths, private commits, or managed-report destinations.

Publication-excluded records retain exact source snapshots, path mappings,
scenario inputs and results, reviewer dispositions, correction counts, and
private provenance. Public files remain complete without those records and do
not link into them.

## Project-owned parameters

The six skills provide reusable procedure. Each target repository or current
assignment owns concrete values such as:

- authority and decision owners;
- source and write scopes;
- architecture and compatibility contracts;
- risk, privacy, and destructive-action boundaries;
- test levels, commands, coverage policy, and evidence thresholds;
- branch, worktree, commit, review, push, and publication workflows;
- artifact destinations and durable record formats; and
- retry, rollback, escalation, and stop limits.

A skill must elicit or consume these parameters, not invent them.

## Rollback expectations

The [skill authoring and maintenance guide](skill-authoring-and-maintenance.md)
is the normative owner for future skill rollback and removal. The historical
v0.1 expectations below remain accurate context.

Each skill is one direct-child leaf. Removal requires:

1. stop new use and mark the skill `deprecated` when migration is needed;
2. identify active references, evaluation claims, and successor behavior;
3. remove every discovery projection for the leaf, then remove or replace the
   canonical leaf without weakening repository safety policy;
4. update the skill index, provenance, transition map, roadmap, and affected
   evaluations;
5. preserve the historical decision and evidence; and
6. run proportional structural and scenario checks against the resulting
   state.

Immediate removal is appropriate when a provisional skill expands authority,
leaks private material, depends on unsupported machinery, or repeatedly
misroutes work. APG v0.1 has no skill runtime or registry. For opted-in separate
Git worktrees, `apg-project-skills uninstall` supplies a tested local projection
rollback; canonical skill removal still requires the complete recorded process.

Removing a discovery projection disables that harness path but does not erase
historical evaluation, review, provenance, or maturity evidence. Removing a
canonical skill requires removal of every projection that resolves to it so no
broken or stale discovery entry remains.

## Dogfooding plan

Dogfooding proceeds in bounded observations rather than an automatic workflow:

For Codex, dogfooding begins only in a new session that can load the committed
repository projection. Projection validation and the session that creates it
are integration evidence, not dogfooding observations.

1. deliberately select a skill only when its trigger appears to match;
2. record the repository class, task class, trigger decision, artifact or stop
   disposition, correction needed, and unrun checks;
3. include real non-trigger observations instead of recording only successes;
4. review authority, privacy, ceremony, and project-parameter separation;
5. use all retained skills in APG work where naturally applicable;
6. repeat in at least one additional real repository with its own policy; and
7. promote, revise, deprecate, or remove each skill through an explicit later
   decision.

Scenario walkthroughs in APG4 seed this record but do not substitute for real
repository use.

APG5 records the first real explicit-use observation: a fresh Codex application
session discovered six of six repository skills and explicitly applied
`reviewing-and-verifying-repository-work` to a bounded read-only integration and
completion-evidence review with terminal result `pass`. That single observation
does not measure automatic selection, promote maturity, establish comparison or
stability, or satisfy the additional-repository requirement.

APG6 records the first successful cross-repository use in RepoMap. A read-only
migration-design observation used `designing-significant-changes` and
`reviewing-and-verifying-repository-work`; the accepted documentation-only
implementation and closeout used `planning-repository-work` and the review
skill. Material non-trigger decisions remained proportional, and no authority,
privacy, destructive-action, or completion-evidence regression was observed in
these samples. A full Codex application restart was needed before the linked
skills appeared in the observed macOS environment; this is a sampled bootstrap
fact rather than a universal refresh guarantee. All six skills remain
`provisional`.

APG7 records one real executable implementation observation for
`implementing-with-test-discipline`. A focused behavioral test failed before the
command existed, the complete 26-family suite passed after implementation and a
structure-only refactor, and a separate disposable install, adopt, check, and
uninstall lifecycle passed without tracked or global-state mutation. Design,
planning, and review procedures were selected proportionally; systematic
debugging remained a non-trigger because no unexplained failure occurred. This
tooling evidence does not establish automatic skill selection, comparative
improvement, production readiness, or stable maturity. All six skills remain
`provisional`.

APG7A records one real correction observation using `debugging-systematically`,
`implementing-with-test-discipline`, and
`reviewing-and-verifying-repository-work`. The reported install/check
inconsistency was reproduced for install and adopt, competing explanations were
separated, two focused tests failed against APG7 production, the narrow guard
made them pass, and the corrected 28-family suite plus disposable recovery
control passed. Planning and significant-change design remained non-triggers
because the accepted architecture and one-step correction did not change. This
correction evidence does not promote a skill or establish automatic selection,
comparative benefit, stable maturity, or decommission readiness.

APG8 records the first real-project managed projection adoption. The corrected
command adopted RepoMap's six existing compatible manual links without changing
their identity or targets, preserved unrelated Git-local exclusion bytes, and
made default and explicit checks pass while RepoMap's tracked tree and index
remained unchanged. Planning and review applied; significant-change design,
implementation test discipline, and systematic debugging remained material
non-triggers. This deployment evidence does not establish Codex discovery after
restart, invocation, automatic selection, comparative benefit, stable maturity,
or decommission readiness.

## Superpowers decommission gate

Superpowers may be considered for decommissioning only when all of these are
true:

1. every materially used Superpowers workflow has a mapped APG replacement or
   an explicit native-Codex or repository-policy disposition;
2. APG has been used successfully in this repository;
3. APG has been used successfully in at least one additional real project;
4. no unresolved authority, privacy, destructive-action, or completion-
   evidence regression remains;
5. an uninstall rollback plan exists;
6. a Superpowers source and provenance snapshot is preserved;
7. the human maintainer explicitly decides to decommission; and
8. post-decommission smoke validation passes.

At APG8 close, evidence supported material workflow mapping, successful use in
APG and RepoMap, source preservation, tested project-local lifecycle behavior,
one real-project managed adoption and check, and the rollback runbook. The
maintainer subsequently supplied the explicit decommission decision and
completed the action. A bounded fresh RepoMap smoke then discovered all six
skills, successfully applied the review skill, passed managed checks, preserved
the tracked repository, and did not use Superpowers as workflow authority.

APG9 accepts decommission closeout through the explicit human decision,
completed action, and bounded smoke rather than retroactively claiming that
every historical readiness dimension was exhaustively proven. Active-project
inventory completeness, universal workflow coverage, automatic selection,
comparative superiority, and successful restoration remain unverified. These
limits do not reverse the human decommission disposition or promote a skill.
Preserved Superpowers source remains reference evidence. APG13 completed the
individual post-Superpowers skill review without restoring or depending on it.

## Later clean-evaluation gate

A later clean comparative evaluation may begin only when the environment can
record the model, harness, instructions, tools, and skill-discovery state;
provide a supported baseline profile; control candidate availability and
deliberate loading; expose an observable invocation event where activation is
claimed; preserve sealed evidence; and keep the candidate as the sole intended
treatment difference.

That evaluation must freeze its claims, scenarios, scoring, reviewer contract,
variance handling, and rollback before candidate results are known. APG4's
walkthroughs are not reused as clean comparative evidence.
