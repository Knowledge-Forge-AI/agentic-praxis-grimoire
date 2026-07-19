# ADR 0002: First Implementation Sequence and Evaluation Baseline

## Status

Accepted

## Date

2026-07-18

## Context

APG has governance, provenance, delegation, reporting, record, and publication
boundaries but no production skill. APG1 established a public-projection
contract and corrected the public surface manually; it did not implement a
publication validator. A reusable skill-authoring and evaluation foundation may
eventually be useful, but APG has not yet evaluated one real APG skill from
baseline through disposition.

The first implementation should maximize learning about APG's core purpose
without assuming that a framework, validator, or skill is already necessary.
Current Codex can often compose good internal assignments without specialized
guidance. At the same time, source evidence demonstrates both under-specified
assignments and long work orders that duplicate policy, drift, or add ceremony.
The project therefore needs an evaluation-first vertical slice that can reject
its own implementation when ordinary behavior is already sufficient.

Codex may recommend an implementation sequence and commit the proposal. It
cannot externally accept that sequence or authorize implementation. Human
authority and delegated ChatGPT review remain governed by the
[manager-worker protocol](../../../manager-worker-protocol.md).

## Decision criteria

APG2 compared every candidate against the same criteria:

1. demonstrated problem severity rather than hypothetical possibility;
2. dependency necessity and whether a manual gate remains safe;
3. immediate value to APG's purpose;
4. observable success and baseline comparison;
5. activation precision and over-trigger cost;
6. stability of any mechanical rule;
7. compatibility with the public/private boundary;
8. source ownership, license, and derivation provenance;
9. continuing maintenance cost;
10. removal, replacement, and compatibility consequences;
11. overlap with capable default Codex behavior; and
12. evidence generated for subsequent roadmap decisions.

Source frequency, document length, prior nomination, and enthusiasm are not
decision scores.

## Decision

Authorize exactly one next implementation phase with the identity **APG3**.

### Objective

Evaluate whether ordinary Codex assignment composition has a material deficit
and, only when the frozen baseline-adequacy rule demonstrates that deficit,
author and evaluate at most one narrowly triggered, reversible skill
provisionally named `composing-bounded-worker-assignments`. The skill would turn
an already authorized objective into one proportional internal worker
assignment after a manager has independently decided that delegation is
permitted and useful.

APG3 tests whether that skill produces a material improvement over ordinary
Codex behavior. Skill authoring and adoption are not foregone: APG3 may stop at
the baseline, adopt, perform at most one bounded correction and re-evaluation,
reject, defer, or stop the candidate based on evidence.

### Concrete problem

Internal assignments can fail in two directions. They may omit source scope,
write ownership, material constraints, evidence, acceptance, or handoff terms.
They may also grow into repeated project policy, stale commands, copied context,
and reporting ceremony. The candidate should improve scope precision and
proportionality without deciding whether delegation is authorized or useful.

### Expected tracked artifacts

When APG3 begins under this authorization, it is expected to produce:

- at most one direct-child candidate skill leaf at
  `skills/composing-bounded-worker-assignments/SKILL.md`, and only when the
  calibration baseline demonstrates a material deficit;
- a public-safe evaluation summary containing the pre-authored scenarios,
  rubric, baseline-adequacy disposition, maintenance triggers, and disposition;
- matched comparison results and independent confirmation review when a leaf is
  actually authored;
- publication-excluded exact scenario provenance and source mappings;
- updated public provenance and skill-index status; and
- one truthful APG3 exit record.

APG3 must not create supporting scripts, assets, a registry, a category
directory, a reusable evaluation framework, or another skill unless a later
authorization separately establishes that need.

### Source families and provenance

Material source families are:

- the public APG manager-worker protocol and project model;
- generalized maintainer-authored orchestration examples;
- representative RepoMap work orders;
- Superpowers delegation and skill-authoring evidence under the MIT License;
- the public Agent Skills compatibility specification; and
- matched observations of ordinary and skill-assisted Codex behavior.

Public text must use APG-native synthesis and remain independently
understandable. Exact non-public identities, snapshots, paths, scenario details,
and source topology remain in publication-excluded provenance. Copied or adapted
external expression requires confirmed need and preservation of applicable
notices; APG3 should not require it.

### Trigger boundary

The candidate may trigger only when all of these conditions hold:

- the current authority model already permits internal delegation;
- a manager has separately decided that a worker is useful; and
- scope, ownership, evidence, acceptance, or handoff boundaries make a
  non-trivial assignment valuable.

It must not trigger merely because a task exists. Non-trigger cases include:

- delegation is not authorized or has not been selected;
- the work is trivial, direct, or clearer for the top-level manager to perform;
- the objective, design, roadmap, or authority remains unresolved;
- candidate tasks share write state or require whole-system context;
- an adequate assignment already exists; or
- the request concerns external human instructions, scheduling, monitoring,
  managed reports, or a general-purpose manager runtime.

The skill must not authorize delegation, invent authority, reopen an approved
design or roadmap, encode project-specific policy, force delegation, or require
managed reports from internal workers.

### Minimal output contract

The skill produces exactly one ready-to-send internal worker assignment. Every
assignment carries the following semantic core; compact assignments may combine
fields and need not use eight headings:

1. worker identity or role and one objective;
2. source scope;
3. write scope or explicit read-only status;
4. material prohibited actions;
5. required evidence;
6. concrete deliverable;
7. observable acceptance criteria; and
8. normal agent-harness return method.

If a core field has no task-specific content, the assignment states that
briefly or references its governing source once. It does not omit the field or
repeat repository-wide policy. Exact snapshots, exclusive ownership,
invariants, validation commands, commit authority, privacy handling, stop
conditions, cleanup, and rollback appear only when an observable task condition
makes them material. The skill does not dispatch the worker or execute the task.

### Evaluation baseline

Before authoring the skill, an evaluator who does not author the candidate must
freeze a public-safe environment inventory, rubric, sampling bounds, execution
subset, reviewer contract, calibration cases, sealed confirmation cases, and
the baseline-adequacy rule. The plan also freezes a finite list of behavior
families, an overall sample maximum, and at most one reserve case for each
affected family within that maximum. The candidate author may inspect the rubric
and calibration cases but not the sealed confirmation or reserve inputs or their
evaluation prompts until the candidate is frozen.

The baseline-adequacy rule must name the binary failures and anchored-score
deficits that permit authoring. A material deficit exists only when the frozen
rule is met by either an authority, reporting, ownership, publication-safety,
or other named binary failure that satisfies the plan's recurrence or variance
rule, or by anchored quality scores below the frozen acceptability threshold
across the predeclared share of eligible cases or behavior families. The latter
must include at least two named quality dimensions or a manager-acceptability
label of `major rewrite` or `unsafe or unusable`. A lone outlier, a `minor
correction` label, greater brevity, or greater length is not a material deficit.

APG3 first runs the no-skill calibration baseline. If that baseline shows no
material assignment deficit, the phase stops without authoring a leaf and
records rejection or deferral. Otherwise, calibration evidence may guide the
initial candidate and its one permitted correction. Final disposition uses the
untouched matched confirmation cases. Confirmation failure cannot trigger
another correction; a pre-frozen reserve case is used only under the declared
variance or reviewer-disagreement rule.

The baseline and candidate conditions use the same current model, harness,
repository instructions, overlapping installed skills, input, and allowed
tools. Candidate availability or deliberate loading is the sole intended
treatment difference. Evaluation prompts and reviewer contracts may not be
produced with the candidate under evaluation.

All results are bound to the recorded model, harness, instruction, skill-
discovery, and tool snapshots. A material change to any of them requires a new
comparison rather than reuse of the earlier outcome as current evidence.

Activation and composition are tested separately. Activation cases make the
candidate available but do not force its use, and the harness must expose an
observable invocation event. Forced invocation does not count as trigger
success. Composition cases state that delegation is already authorized and
selected, then deliberately load the candidate to evaluate assignment quality.

The set must include:

- a small eligible read-only assignment;
- a medium bounded implementation or review assignment;
- a contract-sensitive or higher-risk assignment;
- independently selected parallel workers with exclusive scopes;
- trivial direct work that must not trigger;
- coupled work that should not be delegated as independent slices;
- unresolved or ambiguous delegation authority; and
- a partial or blocked worker outcome.

Each behavior family must have distinct calibration and confirmation evidence.
The frozen plan declares a bounded minimum and maximum matched sample count and
preselects any reserve cases before results are known. All reserve cases
collectively form one expansion, remain within the overall sample maximum, and
add at most one case to each affected behavior family. The evaluation reports
sample-bound observations, including zero observed violations, rather than
statistical or universal claims. Two independent reviewers are required at the
sealed confirmation gate; calibration does not require duplicate review.

Review observable assignment outcomes:

- correct trigger and non-trigger behavior;
- no invented authority or delegation decision;
- no managed worker-report requirement;
- coverage of the complete semantic core without fabricated constraints;
- precise source and write ownership;
- observable evidence and acceptance;
- proportional length without copied policy;
- correct harness-return expectations;
- assignment-level executability; and
- manager first-pass acceptability.

Downstream worker compliance is a separate execution claim. Before authoring,
the plan selects at least one eligible read-only case, one isolated-write case,
and one blocked-or-needs-context case for matched execution. It adds a
two-worker disjoint-scope fixture only if APG3 intends to claim parallel-
ownership behavior. A preselected baseline-generated and candidate-generated
assignment is sent to separate fresh workers in synthetic, public-safe,
disposable workspaces that begin at identical snapshots and expose the same
model, harness, instructions, and tools. The run records only bounded
observables: terminal status, path manifest, command categories and exit states,
required evidence, questions or escalation, and authority, reporting, scope,
or ownership violations. Reviewer prediction from assignment text is not
compliance evidence. If safe execution is unavailable, downstream compliance is
marked not observed and cannot count as an advantage.

Required safety conditions are zero observed negative-scenario activations,
authority expansions, forced delegations, overlapping write ownership,
publication-boundary leaks, and managed-report requirements for ordinary
internal workers across the predeclared samples.

The frozen evaluation plan must define these mechanics before skill authoring:

- two independent reviewers who did not author the candidate;
- condition labels concealed from reviewers and paired outputs presented in a
  randomized order, with any unavoidable disclosure recorded;
- binary trigger, authority, reporting, ownership, and publication-safety
  checks;
- anchored quality scores for scope precision, semantic-core coverage,
  evidence and acceptance clarity, proportionality, assignment-level
  executability, observed downstream compliance where run, and manager
  acceptability;
- manager acceptability labels of `ready to send`, `minor correction`, `major
  rewrite`, or `unsafe or unusable`;
- per-scenario and aggregate comparison rules; and
- disagreement and variance handling.

The candidate must pass every binary safety check. At the sealed confirmation
gate, both reviewers must independently identify the same substantive advantage
in at least one named rubric dimension, and aggregate anchored scores must
improve on at least two quality dimensions without regressing another. Greater
length or more headings is not an advantage. A tie, no clear advantage, or
disagreement or variance that remains after the allowed predeclared reserve
cases are exhausted requires rejection or deferral. The reviewers are
independently contextualized, not statistically independent, and APG3 records
that limitation.

APG3 may make at most one bounded skill correction from calibration evidence
and must then rerun the complete calibration set before freezing the candidate
for confirmation. A second correction need, confirmation failure, a new problem
class, or a required rubric change ends the vertical slice as rejected,
deferred, blocked, or stopped rather than expanding it into iterative framework
construction.

Focused mechanical checks validate frontmatter, direct-child shape, metadata,
local links, public/private separation, and the absence of unused support
directories. If the skill uses progressive disclosure, evaluation must confirm
that needed support is discoverable and unrelated material need not be loaded.

### Independent review and final verification

APG3 requires independent review of:

- trigger and non-trigger coverage;
- rubric neutrality and matched comparison;
- authority and reporting boundaries;
- proportionality and Codex capability overlap;
- public/private and source-expression leakage;
- maintenance and rollback; and
- the complete finished diff.

The final gate must run all applicable skill and documentation checks, the
complete public-surface confidentiality and link scan, and Git whitespace
checks. Commands not run must be reported truthfully.

### Rollback and removal boundary

If the calibration baseline is already adequate, APG3 authors no leaf and
records that negative result. If a later candidate fails the rubric,
over-triggers, expands authority, leaks private conventions, or supplies no
material confirmation advantage, APG3 removes the leaf before adoption and
records the negative result. If later adopted, the skill remains removable as
one leaf plus its index and provenance references. No runtime protocol,
registry, category taxonomy, or public compatibility layer may depend on it
during APG3.

### Dependencies

APG3 depends on:

- the accepted status of this ADR and the recorded APG3 authorization;
- one bounded APG3 assignment inside the human-approved roadmap envelope;
- the accepted manager-worker and publication boundaries;
- separable evaluator, candidate-author, and confirmation-reviewer roles;
- an available current harness that exposes skill invocation and supports
  isolated matched worker runs without an adapter; and
- the manual APG3 public-surface validation gate.

An executable publication validator and reusable evaluation framework are not
dependencies.

### Explicit non-goals

APG3 does not:

- decide whether delegation is authorized or necessary;
- create a manager runtime, scheduler, registry, or autonomous epic controller;
- create a general work-order or external-prompt generator;
- replace repository instructions or approved designs;
- create a reusable skill-authoring/evaluation skill or fixture framework;
- implement a publication validator;
- adopt a taxonomy or harness adapter;
- add dependencies;
- select project license or publication terms; or
- implement any other roadmap theme.

### Stop conditions

APG3 stops and reports rather than broadening if:

- the accepted authority envelope is absent or ambiguous;
- a new epic, destructive action, publication decision, license decision, or
  material scope expansion is required;
- baseline behavior shows no concrete problem for the skill to solve;
- the evaluation cannot keep model, harness, instructions, or tools comparable;
- candidate invocation cannot be observed or sealed confirmation cannot remain
  unavailable to the candidate author;
- public/private provenance cannot be preserved;
- the candidate requires another skill, framework, dependency, or runtime; or
- the single vertical slice cannot reach a truthful adopted, revised, rejected,
  blocked, or stopped disposition;
- calibration still fails after its one permitted correction; or
- the frozen candidate fails sealed confirmation.

### Acceptance evidence

APG2A accepted this decision after review of this ADR, the candidate comparison,
roadmap entry, APG2 exit, independent review findings, validation results, and
the exact APG2 Git and operational evidence. The acceptance confirmed the skill
identity, objective, evaluation contract, non-goals, stop conditions, and
authority envelope without starting APG3.

## Alternatives considered

### Candidate B — Publication-surface validator first

Deferred as a later candidate, not rejected. APG1 exposed real confidentiality
and record-hygiene risk, but the current public surface remains small and clean,
and the next phase can use an explicit manual gate. Several valuable checks are
mechanical, while private identity, source topology, license, provenance, and
authorization truth still require classification and judgment. Encoding them
now would risk false positives, false negatives, or a public dependency on
private policy.

Reconsider the validator before any public projection, after any repeated
confidentiality or record-grammar defect, when a second substantive skill creates
repeated enforcement need, or at the next roadmap re-planning after APG3. A
future tool should operate on an explicit Git tree or projection root, use no
new dependency, keep private deny patterns outside public code, and bound and
sanitize diagnostics.

### Candidate C — Skill-authoring and evaluation foundation first

Deferred as a standalone foundation, not rejected. A minimum evaluation
contract is required and is embedded in APG3. A reusable evaluation skill,
fixture tool, generalized scorer, or full imported ceremony would be circular
before APG has evaluated one real skill. It would also overlap ordinary Codex
capabilities and establish maintenance vocabulary without demonstrated reuse.

Reconsider a reusable authoring/evaluation procedure after one completed
vertical slice and a second skill evaluation demonstrate the same judgment-heavy
need. Reconsider fixture tooling when scenario setup or result normalization is
repeated and manual execution becomes materially error-prone.

### Additional prerequisite

No fourth implementation prerequisite is justified. The authority-model
correction is directly authorized documentation work inside APG2. The minimum
evaluation contract and manual publication gate fit inside one APG3 vertical
slice without becoming separate implementation projects.

## Consequences

- APG3 can produce the first causal evidence about whether an APG skill improves
  agent work beyond capable baseline behavior.
- The skill's upstream position gives its results high sequence leverage for
  later evaluations, while its strict negative triggers limit ceremony.
- APG3 introduces maintenance for one leaf and its evaluation/provenance record
  only if evidence supports adoption.
- Exact source and scenario evidence remains publication excluded; the skill and
  public evaluation remain independently understandable.
- The chosen order risks spending one phase to learn that ordinary Codex is
  already adequate. That is an acceptable and useful rejection result.
- Delaying the validator preserves a manual-audit burden and leaves human
  classification error possible. The APG3 gate and reconsideration triggers
  bound that risk.
- Delaying a reusable evaluation foundation may duplicate some setup in APG3,
  but avoids a framework whose requirements are not yet known.
- The next roadmap re-planning decision will use APG3 trigger results, baseline
  comparison, maintenance evidence, and disposition to choose among skill
  evaluation foundations, publication validation, another domain skill, or no
  further implementation.

## Acceptance

- **Acceptance date:** 2026-07-18
- **External disposition:** Accept ADR 0002 and authorize the bounded APG3
  objective and evaluation contract.
- **Authority basis:** ChatGPT reviewed the APG2 evidence inside its delegated
  planning and review envelope. The human maintainer then explicitly authorized
  this acceptance record and the bounded APG3 phase. Human project and roadmap
  authority remains ultimate.
- **Accepted basis:** This acceptance applies to the corrected APG2 state
  documented by the forward-correction validation in the
  [APG2 exit](../../../status/2026/07/18/00003-apg2-roadmap-reconciliation-proposal-exit.md),
  not to the pre-correction proposal alone.
- **Accepted boundary:** APG3 evaluates ordinary Codex assignment composition
  against the frozen baseline-adequacy rule and authors at most one
  `composing-bounded-worker-assignments` leaf only when that rule demonstrates a
  material deficit. Delegation must already be authorized and independently
  selected before the candidate can apply.
- **Implementation state:** APG3 is authorized but has not started. No skill,
  evaluator, fixture, validator, framework, dependency, or runtime was
  implemented by APG2A.
- **No-leaf outcome:** Baseline adequacy is a successful APG3 result and closes
  the phase without authoring a skill leaf.
- **Scope limit:** This acceptance authorizes only the bounded vertical slice in
  this ADR. It authorizes no additional epic, skill, framework, validator,
  runtime, dependency, publication decision, license decision, or destructive
  action.
- **Stop boundary:** Every stop condition in this ADR remains active. APG3 may
  narrow or stop for safety or evidence but may not broaden its authorization.

The [APG2A acceptance exit](../../../status/2026/07/18/00004-apg2a-first-implementation-sequence-acceptance-exit.md)
records this disposition. Authorization does not imply implementation,
validation, or adoption of the candidate skill.

## APG3 result

APG3 later closed as **Blocked** at its mandatory harness preflight. The current
internal-agent environment could not isolate active overlapping skill behavior
or expose the required skill-invocation event and treatment controls without an
adapter, profile construction, or global mutation. The
[public evaluation summary](../../../evaluations/apg3-composing-bounded-worker-assignments.md)
and [APG3 exit](../../../status/2026/07/18/00005-apg3-bounded-worker-assignment-skill-evaluation-exit.md)
record that result.

No evaluation plan or cases were frozen, no baseline was run, and no candidate
was authored. This later result does not change this ADR's Accepted status or
rewrite its decision; it applies the decision's existing stop conditions.
