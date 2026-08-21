# Reference and Provenance Policy

<!-- APG-CANDIDATE-STATE: css-language-profile retained-provisional -->

The marker above is the mechanical current-state authority. Bounded
contradiction diagnostics cover only their frozen vocabulary; arbitrary prose
still requires human review.

## Purpose

Provenance connects a materially source-derived APG practice to dated evidence,
lawful reuse, an explicit disposition, and validation. It does not make a source
authoritative and does not replace technical evaluation.

## Separate provenance facts

Record these facts independently:

- **Evidence location:** where APG inspected the material and at what version.
- **Source identity and ownership:** who authored or owns the underlying work.
- **Publication eligibility:** whether exact evidence may appear in a public
  projection.
- **License:** what reuse permission and notice obligations apply.
- **Derivation mode:** how APG used the source.
- **Adoption status:** what APG decided and why.

Ownership does not imply public eligibility or a license grant. A public source
is not automatically adopted. A compatible source license does not choose APG's
own distribution license.

Public readability is not reuse permission. When source code, a specification,
and associated documentation use different terms, record each artifact's
license separately; do not collapse them into labels such as `public`,
`MIT-adjacent`, or `docs/source licensed`. If the inspected artifact grants no
reuse license, copied and adapted expression are blocked even when factual
clean-room analysis remains possible. Search the complete source record for
inline grants as well as standalone license files and package metadata.

## Two-level provenance

### Public record

Publishable provenance contains:

- a stable practice identifier;
- a generalized maintainer-authored source family or a genuinely public source
  identity;
- an immutable public upstream version when useful and verified;
- public source paths when they are independently resolvable;
- source license and notice requirements when relevant;
- derivation mode, APG destination, adoption status, rationale, and validation;
  and
- supersession history.

Public records do not expose unpublished repository identities, private source
topology, private snapshots, development commits, local paths, or private report
destinations.

### Publication-excluded record

The tracked `private/` area may retain exact collection repositories, historical
and current snapshots, source paths, object mappings, ownership and publication
classifications, license evidence, and migration history. Historical paths stay
tied to the snapshot where APG actually observed them; current mappings are
recorded alongside rather than substituted into history.

Public artifacts remain complete without that record and do not link to it.

## Source classes and current license facts

| Source class | Public treatment |
| --- | --- |
| Maintainer-authored agent and engineering practices | Generalize the source family publicly; use semantic source classes and phase-local evidence IDs in tracked publication-excluded provenance. Exact Git identities remain report or transient evidence. Ownership supplies adoption authority, not a public license grant. |
| RepoMap | Use the canonical public identity `repo-map`; cite public-intended architecture and contributor practices without exposing its private development lineage. Do not infer a license from an ADR or ownership alone. |
| Superpowers | External source under the MIT License. Preserve the included copyright and license notice for copied or adapted material. Synthesized or inspired use still records provenance. |
| Experimental Karpathy Guidelines | Reference evidence whose inspected frontmatter declares MIT. Treat that declaration separately from verified upstream identity, semantic revision, copyright, full license text, and notice obligations. APG10 must complete that review before copied or adapted use. |
| Agent Skills specification | Genuinely public compatibility evidence. Record a semantic revision when published; otherwise use a phase-local source ID, public locator, inspection date, and mutability limitation. |
| Official Codex skill documentation | Genuinely public harness evidence. Record the inspection date when current discovery behavior materially defines a projection. |
| APG's own tools and documents | Project-authored material distributed under AGPL-3.0-or-later, with separate commercial licensing available from the Project Steward. |

The current APG foundation contains no material classified as copied or adapted
from Superpowers, so it does not require a bundled Superpowers notice. That
classification must be revisited if recognizable expression or structure is
introduced later.

## Derivation modes

| Mode | Meaning | Reuse requirement |
| --- | --- | --- |
| `copied` | Source expression is reproduced substantially verbatim. | Confirm compatible rights and preserve required notices and attribution. |
| `adapted` | Source expression or structure is recognizably modified for APG. | Confirm compatible rights and preserve required notices and attribution. |
| `synthesized` | APG-native expression combines observations or principles without retaining protected source expression. | Cite material evidence and explain the resulting decision. |
| `inspired` | A source prompted an independently developed idea without supplying material expression or structure. | Cite the influence when material to the decision. |

`Copied` and `adapted` are blocked when source identity, permission, or notice
requirements are unresolved. APG may still record an observation and develop an
independent synthesis when it can do so without copying protected expression.

## Conflicts, status, and supersession

Conflicting sources are recorded as conflicts, not silently merged. The adoption
record identifies which evidence was accepted, rejected, or left unresolved and
why. A source's age, location, or filename is not sufficient to declare it
superseded.

Adoption statuses are:

- `candidate`: inventoried but not evaluated;
- `proposed`: designed with acceptance evidence pending;
- `adopted`: accepted into the named APG destination with validation evidence;
- `deferred`: potentially useful but awaiting evidence or authority;
- `rejected`: considered and intentionally excluded with rationale; or
- `superseded`: replaced by a later recorded decision without erasing history.

Promotion requires a concrete problem, source and license review, destination
decision, benefit and cost analysis, trigger-risk analysis, compatibility and
rollback consideration, and validation proportional to the claim. Preference or
source frequency alone is insufficient.

## Claim-relative source authority

Weigh material evidence by how directly its inspectable basis bears on the
exact claim under evaluation, not by a universal source rank or document
count. APG adopts no universal source tiers and no source-count minimum.

A first-party source may settle its own formal record — for example a release
tag, a specification, statute text, a configured default, or a currently
published price. A first-party or otherwise interested source does not
automatically control conclusions about impact, reliability, safety, quality,
disputed interpretation, or contested real-world behavior; those conclusions
may need independently produced evidence.

Separate URLs, articles, or artifacts that reuse one underlying evidentiary
basis — the same upstream announcement, dataset, report, or origin post — are
one corroborating lineage, not independent confirmation. Weigh origins, not
restatements; a derivative summary may still aid discovery of the origin it
summarizes.

The amount of corroboration remains claim- and project-owned. A narrow formal
fact may be settled by one authoritative source. A disputed or consequential
claim may require searching for the opposing claim and weighing independently
produced evidence before disposition.

## Material access limitations

When incomplete access to evidence could materially affect a conclusion,
record the limitation in the provenance prose: what inspection was
unavailable or constrained — for example a partial or truncated view, a
search-result snippet without the full text, a paywall or other block, or
only an archived copy — and how that limitation constrained validation,
confidence, or the terminal claim. Describe the boundary without exposing
protected content, credentials, private paths, machine topology, or
confidential source details.

Omit the note when access was complete or when the limitation was immaterial
to the conclusion. This guidance adds no required field, key, schema, or
validator, and existing free-prose provenance records remain valid. A
sufficient note can be one sentence, for example: the upstream manual was
truncated at its public preview boundary, so defaults beyond the inspected
sections were not verified and the compatibility claim covers only those
sections.

## Public provenance template

Use one record per source family and destination artifact or materially distinct
derived section. Use additional records when licenses or derivation modes differ.

```yaml
practice_id: <stable-semantic-id>
source_family: <public-source-or-generalized-maintainer-family>
public_source_identity: <owner/repository-or-not-public>
public_source_version: <semantic-public-version-or-not-applicable>
phase_local_source_id: <stable-phase-local-id-or-not-applicable>
inspection_date: <YYYY-MM-DD>
revision_limitations: <mutability-or-unversioned-limitation-or-none>
public_source_paths:
  - <publicly-resolvable-path-or-not-applicable>
source_ownership: <maintainer-authored|external>
source_license: <license-and-public-evidence-or-not-applicable>
derivation_mode: <copied|adapted|synthesized|inspired>
apg_destination: <repository-relative-public-path-or-section>
adoption_status: <candidate|proposed|adopted|deferred|rejected|superseded>
rationale: <problem-addressed-and-decision>
validation_evidence:
  - <test-review-status-or-evaluation-reference>
supersedes: <practice-id-or-none>
private_evidence_retained: <yes|no>
```

## APG0 public disposition summary

| Practice | Public source families | Mode | Destination | Status |
| --- | --- | --- | --- | --- |
| Concise repository instruction boundary | Maintainer-authored agent instructions; RepoMap examples | Synthesized | `AGENTS.md` | Adopted |
| Artifact ownership model | RepoMap architecture; maintainer-authored orchestration examples; Superpowers skill-authoring evidence | Synthesized | `docs/project-model.md` | Adopted |
| Provenance and promotion policy | RepoMap documentation and decision practices | Synthesized | `docs/provenance.md` | Adopted |
| Executable reporting contract | APG report executables | Synthesized from executable behavior | `docs/manager-worker-protocol.md` | Adopted |
| Manager-worker coordination | Maintainer-authored orchestration examples; RepoMap bounded work orders | Synthesized | `docs/manager-worker-protocol.md` | Adopted and corrected by ADR 0001 |
| Agent skill leaf compatibility | Agent Skills specification | Synthesized | `skills/README.md` | Adopted |

The Agent Skills compatibility basis is `APG0-AGENT-SKILLS-SOURCE-01`, the
public [Agent Skills specification](https://agentskills.io/specification),
inspected on 2026-07-18. The source publishes no semantic specification
revision, so the phase-local ID and inspection date identify APG's evidence
without claiming that the public page is immutable. APG11 re-evaluated its
rights boundary. The specification is documentation under the repository's
[`docs/LICENSE`](https://github.com/agentskills/agentskills/blob/main/docs/LICENSE),
which contains Creative Commons Attribution 4.0 International; repository code
is separately Apache-2.0. APG copies or adapts no specification expression or
upstream code. It independently implements compatible format facts and
project-authored constraints, with the phase-local source ID, locator, date,
and license link providing source and rights attribution. No bundled
third-party notice is required for that synthesized
use. Future copied or adapted use must separately satisfy the applicable
license and attribution duties. Exact maintainer-source snapshots and path
mappings remain publication excluded.

## APG2 public disposition summary

| Practice | Public source families | Mode | Destination | Status |
| --- | --- | --- | --- | --- |
| Human, ChatGPT, top-level Codex, and internal-worker authority chain | APG governance; generalized maintainer-authored orchestration evidence | Synthesized | `AGENTS.md`; `docs/manager-worker-protocol.md`; `docs/project-model.md`; ADR 0001 clarification | Adopted under explicit APG2 authority |
| First-implementation sequence and conditional worker-assignment evaluation | APG manager-worker protocol; generalized maintainer-authored orchestration; RepoMap work orders; Superpowers delegation and skill-authoring evidence; current Codex behavior | Synthesized | ADR 0002; `docs/roadmap.md`; `skills/README.md` | Accepted sequence; candidate skill absent and not adopted |
| Embedded minimum skill-evaluation contract | APG practice lifecycle; Superpowers baseline-first skill-authoring evidence; current Codex evaluation capability | Synthesized | ADR 0002 APG3 contract | Accepted for APG3; no evaluator or tooling adopted |
| Publication-validator deferral and manual gate | APG public-projection policy and repository history | Synthesized | ADR 0002 alternatives; `docs/roadmap.md` | Validator deferred; manual gate retained |

APG2 copied or adapted no Superpowers expression. Superpowers materially
informed the comparison under its MIT License, while APG2 retained only
independently written synthesis. Exact maintainer-source identities, snapshots,
paths, scenario mappings, and worker findings remain publication excluded.

APG2A accepted the corrected first-implementation sequence and APG3 evaluation
contract. That acceptance authorizes the bounded evaluation phase; it does not
adopt the absent candidate skill, claim that evaluation occurred, or introduce
copied or adapted Superpowers expression. APG licensing remains deferred.

## APG3 public disposition summary

| Practice | Public source families | Mode | Destination | Status |
| --- | --- | --- | --- | --- |
| Comparable skill-evaluation preflight | Accepted APG governance; current Codex harness and tool observations; Superpowers overlap evidence | Synthesized | `docs/evaluations/apg3-composing-bounded-worker-assignments.md`; APG3 exit | Blocked before plan freeze or baseline execution |
| Conditional bounded-assignment candidate | APG manager-worker protocol; Accepted ADR 0002; generalized maintainer-authored orchestration; RepoMap work orders; Superpowers delegation and skill-authoring evidence | No candidate expression produced | No skill destination | Not authored, validated, adopted, rejected, or deferred |

Superpowers remained external MIT-licensed evidence. APG3 observed that its
active bootstrap and delegation procedures materially overlapped the proposed
target behavior, but introduced no copied or adapted Superpowers expression.
The phase did not author an APG skill or evaluation prompt, and no Superpowers
notice obligation was newly created.

The blocked disposition is supported by the
[public evaluation summary](evaluations/apg3-composing-bounded-worker-assignments.md)
and [APG3 exit](status/2026/07/18/00005-apg3-bounded-worker-assignment-skill-evaluation-exit.md).
Exact environment and source evidence remains publication excluded. APG
licensing remains deferred.

## APG4 public disposition summary

APG4 accepts bootstrap authorship before clean comparative evaluation under
[ADR 0003](adr/2026/07/0003-bootstrap-maturity-and-superpowers-coexistence.md).
All retained skills use independently written APG-native synthesis.

| Practice | Public source families | Mode | Destination | Lifecycle status | Maturity |
| --- | --- | --- | --- | --- | --- |
| Bounded internal worker assignment composition | APG manager-worker protocol; generalized maintainer-authored orchestration; RepoMap work orders; Superpowers delegation evidence under MIT | Synthesized | `skills/composing-bounded-worker-assignments/SKILL.md` | Adopted | `provisional` |
| Significant-change design | APG project model; generalized maintainer design evidence; RepoMap design boundaries; Superpowers brainstorming evidence under MIT | Synthesized | `skills/designing-significant-changes/SKILL.md` | Adopted | `provisional` |
| Repository work planning | APG governance; generalized maintainer planning evidence; RepoMap phase practices; Superpowers planning evidence under MIT | Synthesized | `skills/planning-repository-work/SKILL.md` | Adopted | `provisional` |
| Implementation test discipline | Generalized maintainer testing standards; RepoMap testing practices; Superpowers TDD evidence under MIT | Synthesized | `skills/implementing-with-test-discipline/SKILL.md` | Adopted | `provisional` |
| Systematic debugging | Generalized maintainer correction evidence; RepoMap testing and correction practices; Superpowers debugging evidence under MIT | Synthesized | `skills/debugging-systematically/SKILL.md` | Adopted | `provisional` |
| Review and completion verification | APG manager-worker protocol; generalized maintainer review evidence; RepoMap review practices; Superpowers review and verification evidence under MIT | Synthesized | `skills/reviewing-and-verifying-repository-work/SKILL.md` | Adopted | `provisional` |
| Bootstrap maturity and Superpowers transition | APG3 evidence; APG governance; Superpowers skill-authoring and workflow evidence under MIT; Agent Skills specification | Synthesized | ADR 0003; `docs/bootstrap-v0.1.md`; `docs/superpowers-transition.md` | Adopted | Applies to provisional bundle |

Structural checks, 18 public-safe scenario walkthroughs, and fresh independent
review support provisional retention. That evidence does not establish clean
causal comparison, statistical reliability, production readiness, stable
maturity, or decommission readiness.

APG4 copies or adapts no Superpowers expression. It preserves no source
template, slogan, diagram, rationalization table, fixed skill chain, or
project-specific command. Superpowers remains external MIT-licensed evidence;
because APG4 uses synthesis rather than copied or adapted expression, it creates
no new bundled-notice requirement. Exact source snapshots, private mappings,
scenario artifacts, and reviewer evidence remain publication excluded.

APG's own distribution license remains deferred.

## APG4A public disposition summary

APG4A preserves the six canonical APG destinations under `skills/` and adds the
Codex repository discovery projection required to expose them from
`.agents/skills/`.

| Practice | Public source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Codex repository skill discovery | Official Codex skill documentation inspected 2026-07-18; APG canonical skill leaves | Synthesized | `.agents/skills/` | Adopted | None; all six skills remain `provisional` |

The projection is APG-authored integration layout consisting only of six
relative symbolic links. It contains no independent procedure and copies or
adapts no Superpowers expression. Canonical documentation, provenance,
evaluation, and maturity records continue to identify `skills/`.

## APG5 public disposition summary

APG5 records a human-accepted Codex application observation and independently
reproduced repository facts without adopting new external procedure or source
expression.

| Practice | Public source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| First explicit Codex dogfooding observation | APG4 bootstrap and discovery records; accepted application observation; APG repository state | Project-authored evidence | `docs/evaluations/apg5-first-codex-dogfooding.md` | Adopted | None; all six skills remain `provisional` |
| Commit-message construction hygiene | APG managed-report contract; exact Git and report-byte investigation | Synthesized from project behavior | `docs/manager-worker-protocol.md` | Adopted | None |

The dogfooding record claims explicit selection only. It does not claim
automatic selection, comparative advantage, stable maturity, production
readiness, or Superpowers decommission readiness. The hygiene rule changes no
report executable or format and introduces no external expression or notice
requirement.

## APG6 public disposition summary

APG6 records two accepted RepoMap observations and one bounded APG correction.
It adopts no external procedure or source expression and does not modify
RepoMap.

| Practice | Public source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Cross-repository design and implementation dogfooding | APG4 bootstrap records; APG skill leaves; accepted RepoMap design and DOC-LAYOUT0 evidence | Project-authored evidence | `docs/evaluations/apg6-repomap-cross-repository-dogfooding.md` | Adopted | None; all six skills remain `provisional` |
| Bounded repository-artifact review discovery | Accepted design-artifact use; existing APG review procedure | Synthesized from project behavior | `skills/reviewing-and-verifying-repository-work/SKILL.md` frontmatter and `skills/README.md` | Adopted after proportional scenario and independent review | None; the review skill remains `provisional` |
| Cross-repository linked-skill restart observation | Accepted Codex macOS application observation; locally verified linked leaves | Project-authored evidence | APG6 evaluation and bootstrap guidance | Adopted as sampled environment evidence | None |

The correction makes design records, plans, reports, and other bounded
repository artifacts discoverable without changing the review procedure,
inventing review authority, or converting ideation into a formal trigger. APG6
claims neither automatic selection nor comparative, causal, stable,
production-ready, or decommission-ready evidence. Exact checkout identities,
snapshots, report identifiers, hashes, scenario returns, and reviewer evidence
remain publication excluded.

## APG7 public disposition summary

APG7 adopts one project-local deployment tool, its behavioral evidence, and one
human Superpowers decommission and rollback runbook. It copies or adapts no
Superpowers expression and performs no global plugin action.

| Practice | Public source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Project-local APG skill projection ownership and rollback | APG4A projection architecture; APG5 and APG6 discovery observations; APG project policy; Git worktree and local-exclude behavior | Project-authored implementation | ADR 0004; `bin/apg-project-skills`; non-executable helpers; `docs/project-skill-projection.md` | Adopted after behavioral tests, disposable dogfood, and independent review | None; all six skills remain `provisional` |
| Executable implementation test discipline | Existing provisional implementation skill; APG7 accepted command contract and behavioral suite | Project-authored evidence | `docs/evaluations/apg7-project-local-projection-tooling.md` | Adopted as one real APG executable observation | None; the implementation skill remains `provisional` |
| Human Superpowers decommission and rollback procedure | Accepted bootstrap decommission gate; transition map; APG6 restart observation; tested APG projection uninstall | Project-authored operational synthesis | `docs/superpowers-decommission-runbook.md` | Adopted as rollback-plan documentation only | None at APG7 close; later action and smoke are recorded by APG9 |

The command uses Python 3.10+ standard-library and Git behavior rather than external
source expression. Public artifacts contain placeholder paths and bounded
results. Exact checkout identities, snapshots, temporary commands, hashes,
reviewer returns, and managed-report identities remain publication excluded.
The runbook does not grant a human decision, remove Superpowers, or establish
post-decommission smoke.

## APG7A public disposition summary

APG7A corrects one project-authored idempotent compliance omission without
adopting external expression or changing the accepted APG7 architecture.

| Practice | Public source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Semantic compliance before idempotent projection success | Accepted ADR 0004; APG7 implementation and behavioral contract; reproduced Git local-exclude behavior | Project-authored correction | `libexec/apg_project_skills_commands.py`; `src/test/int/python/apg_project_skills.int.test.py`; APG7 evaluation and projection guide | Adopted after failing baseline evidence, corrected behavioral tests, disposable recovery control, and independent review | None; all six skills remain `provisional` |

The correction reuses the existing managed-status query and changes no command,
state schema, exclusion grammar, ownership model, dependency, source expression,
or global plugin behavior. Exact development commits, local paths, disposable
commands, hashes, and reviewer returns remain publication excluded. APG
licensing and Superpowers decommission readiness remain unchanged.

## APG8 public disposition summary

APG8 adopts no external expression. It records one project-authored deployment
observation of the accepted APG7A command in RepoMap.

| Practice | Public source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Real-project managed projection adoption and verification | Accepted ADR 0004 and APG7A command; existing RepoMap manual projection; APG rollout and decommission gates | Project-authored deployment evidence | `docs/evaluations/apg8-repomap-managed-projection-adoption.md`; projection guide; bootstrap and decommission records | Adopted after exact before/after comparison, managed checks, tracked-state preservation, and independent review | None; all six skills remain `provisional` |

The observation preserves one canonical APG source, existing link identity,
user-owned local exclusion bytes, RepoMap's tracked repository, and global
plugin state. Exact paths, commits, link targets, inodes, hashes, state,
exclusion bytes, and reviewer snapshots remain publication excluded. It makes
no invocation, automatic-selection, comparative, stable, production-ready,
publication-ready, license, or decommission-ready claim.

## APG9 public disposition summary

APG9 adopts no external procedure or copied expression. It reconciles the
maintainer-authorized release, global integration, decommission, and smoke
facts; records one release-process limitation; and accepts a bounded v0.2
roadmap through ADR 0006.

| Practice | Public source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| v0.1 publication and squashed-history closeout | Public APG v0.1.0; private development release evidence | Project-authored reconciliation | README; roadmap; APG9 evaluation and exit | Adopted as current state with the omitted public command wrapper assigned to APG12 | None; all six skills remain `provisional` |
| Public-sourced maintainer global integration | Maintainer-authorized operation; public APG checkout; current discovery observation | Project-authored operational synthesis | APG9 evaluation; project-skill projection guide | Adopted as generalized current state; formalization assigned to APG12 | None |
| Superpowers decommission and bounded smoke | Maintainer-authorized decision and smoke; preserved transition and rollback evidence | Project-authored operational synthesis | Transition map; decommission runbook; APG9 evaluation | Adopted for v0.1 closeout; preserved source remains external evidence | Post-Superpowers evidence only; no promotion |
| v0.2 objectives, maturity policy, and APG10–APG14 sequence | APG evidence through APG-TEST0; six-skill review; legacy-theme audit; experimental Karpathy source | Synthesized | ADR 0006; roadmap | Accepted | Promotion remains deferred to APG13 |

The experimental Karpathy source informed roadmap scope only. APG9 copies or
adapts none of its headings, slogans, examples, templates, or heuristics. Its
declared MIT frontmatter is not treated as complete upstream provenance or
notice evidence. APG10 must verify those facts before copied or adapted use and
should prefer independently written synthesis.

Exact repository identities, commits, local paths, link targets, object
comparisons, plugin observations, smoke evidence, worker findings, and report
identities remain publication excluded. The public APG9 evaluation is complete
without those records.

## APG10 public disposition summary

APG10 resolves the experimental Karpathy Guidelines source as public external
evidence with incomplete copied-or-adapted reuse evidence.
`APG10-KARPATHY-SOURCE-01` identifies the captured source inspected on
2026-07-19 at the public
[`multica-ai/andrej-karpathy-skills`](https://github.com/multica-ai/andrej-karpathy-skills)
repository. That source had no semantic release or stable specification
revision, so the repository locator is mutable and the phase-local ID does not
claim immutability. The inspected leaf and README declared MIT, but the source
contained no complete license text, explicit copyright notice, or notice file.

| Practice | Public source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Experimental guideline overlap and idea dispositions | Experimental Karpathy Guidelines; existing APG owners | Synthesized evaluation | ADR 0007; APG10 evaluation | Already covered, project-owned, rejected, or adopted as recorded | None |
| Current-change cleanup completion boundary | Experimental Karpathy Guidelines as material influence; frozen APG10 scenarios; current implementation owner | Synthesized | `skills/implementing-with-test-discipline/SKILL.md` | Adopted after two baseline gaps, positive/non-trigger/edge rerun, and non-author review | None; the skill remains `provisional` |

APG10 copies or adapts none of the source's headings, slogans, examples,
heuristics, template, fixed sequence, or recognizable structure. The one
correction is independently written from current APG ownership and frozen
scenario evidence. Because no copied or adapted material enters APG and the
source supplies no complete notice payload, APG10 adds no third-party notice.
Copied or adapted future use remains blocked pending a new complete rights and
notice review.

Exact captured repository, path, blob, contributor history, worker returns,
hashes, and review evidence remain publication excluded. The public evaluation
and ADR are complete without them.

## APG11 public disposition summary

APG11 synthesizes repeated project-authored practice from APG4 through APG10.
It copies or adapts no external skill-authoring methodology.
`APG0-AGENT-SKILLS-SOURCE-01`, its public locator, inspection date, and stated
revision limitation inform only compatible metadata, name, directory, and
relative-reference constraints; APG's additional leaf headings, catalog, and
projection rules are project-authored requirements.

The specification path is CC BY 4.0 documentation, while upstream repository
code is Apache-2.0. APG11 imports neither expressive documentation nor code;
the phase-local source ID, public locator, inspection date, limitation, and
license link identify the influence. No bundled license or notice text is added
for the independently written compatibility implementation.

| Practice | Public source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Skill-specific authoring and maintenance lifecycle | APG4 bootstrap; APG6 frontmatter correction; APG7/APG7A executable work; APG9 reconciliation; APG10 behavior correction; project model and provenance policy | Synthesized project procedure | ADR 0008; `docs/skill-authoring-and-maintenance.md` | Adopted after independent lifecycle, invariant, ledger, design, and resulting-state review | None; all six skills remain `provisional` |
| Mechanical APG skill-library validation | Repeated canonical shape, metadata, headings, catalog, link-containment, and checked-in projection checks; `APG0-AGENT-SKILLS-SOURCE-01` compatibility evidence | Project-authored implementation | `bin/apg-check-skill-library`; standard-library helper; focused unit and integration tests | Adopted for mechanical invariants after failing-first evidence, correction, and development/public dogfood | None |
| Legacy roadmap terminal ledger | Pre-APG9 candidate and deferred themes; ADR 0006 owners and terminal conditions; APG9/APG10 outcomes | Synthesized reconciliation | `docs/legacy-roadmap-closure.md`; APG11 evaluation and exit | Adopted with 24 stable identities and explicit composite sub-dispositions | None |

The checker does not establish source rights, provenance truth, semantic
quality, authority, privacy, scenario adequacy, discovery, maturity, release
completeness, or stable behavior. Its parser is an explicitly narrow APG lexical
subset, not a general YAML, Markdown, Agent Skills, or publication validator.
Exact checkout paths, snapshots, hashes, failing-first output, worker returns,
and reviewer evidence remain publication excluded.

## APG11A public disposition summary

APG11A is a project-authored forward correction to APG11's mechanical checker.
It uses no new external expression, parser, dependency, or source family.

| Practice | Public source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Top-level frontmatter-key and fenced-code lexical correction | Accepted ADR 0008; reproduced APG11 behavior; project-authored tests and helper | Project-authored correction | `libexec/apg_skill_library_check.py`; checker unit and integration tests; reconciled APG11 records | Adopted after failing-first evidence, full regression, generated dogfood, and independent review | None; all six skills remain `provisional` |

The correction retains APG's independently written lexical subset. It copies
or adapts no YAML, Markdown, or Agent Skills parser expression and creates no
new license or notice requirement. Exact reproductions, tree fingerprints,
test chronology, and reviewer returns remain publication excluded.

## APG12 public disposition summary

APG12 synthesizes project-owned release and user-lifecycle mechanics from the
accepted APG publication boundary, public v0.1.0 history, the reproduced wrapper
omission, the existing project-local ownership model, and current official
Codex discovery documentation inspected on 2026-07-20.

| Practice | Public source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Exact non-private public projection and one-commit candidate validation | ADRs 0001, 0005, and 0006; public v0.1.0; reproduced omitted-wrapper behavior | Project-authored architecture and implementation | ADR 0009; public-surface policy; `apg-public-release`; release guide and tests | Adopted after failing-first evidence, deterministic candidate dogfood, omission regression, and independent review | None |
| Public-sourced user-scope link lifecycle | Official Codex skill discovery documentation; accepted project-local ownership principles; read-only active integration observation | Synthesized compatibility boundary with project-authored implementation | ADR 0009; `apg-user-skills`; user integration guide and tests | Adopted for six direct user links and strict local state; active migration remains separately authorized | None; all six skills remain `provisional` |

The official documentation supplies current location, symlink, duplicate-name,
refresh, restart, and plugin-distribution facts. APG copies or adapts no OpenAI
documentation expression or implementation. Exact local paths, private commits,
candidate identities, state, link targets, command output, and reviewer returns
remain publication excluded. No third-party code, runtime dependency, or notice
payload enters APG12.

## APG13 maturity disposition summary

APG13 synthesizes no new procedure text. It classifies project-authored APG4
through APG12A evidence, applies the unchanged current leaves to frozen cases,
and records independent maturity dispositions under ADRs 0006 and 0010.

| Practice | Public source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Six individual post-Superpowers maturity dispositions | APG4-APG12A scenario, real-use, non-trigger, correction, review, rollback, distribution, and regression records | Synthesized evidence disposition; no copied or adapted expression | ADR 0010; APG13 evaluation; catalog | Accepted after six current applications, zero procedure corrections, complete regression, and six final non-author reviews | All six current catalog rows become `stable` |

Exact hashes, repository identities, worker returns, and detailed evidence
classifications remain publication excluded. APG13 adds no external source,
dependency, code, notice duty, or license obligation.

## APG license boundary

APG is licensed under the GNU Affero General Public License v3.0 or later, with
separate commercial licensing available from the Project Steward. The explicit
human-maintainer decision is recorded in
[ADR 0005](adr/2026/07/0005-public-license-and-contribution-governance.md).

The MIT License for Superpowers applies to Superpowers material, not
automatically to APG. Third-party material remains subject to its own license
and notice requirements. Future contributions are governed by
[`CONTRIBUTING.md`](../CONTRIBUTING.md) and [`CLA.md`](../CLA.md).

## APG12A correction provenance

APG12A is a forward correction based on externally reported behavior and
independent local reproduction of the committed APG12 tools. It introduces no
third-party source, copied expression, dependency, or license obligation. The
accepted public v0.1.0 commit, tree, and tag remain the local mechanical trust
anchor; this establishes lineage integrity but does not add cryptographic
publisher authentication. The original APG12 evidence remains historical and
is not rewritten to claim that it contained the correction.

## APG14 release disposition summary

APG14 adds no external source, copied expression, dependency, or notice duty.
It applies the project-authored release, lineage, user-lifecycle, licensing,
and maturity decisions already accepted in ADRs 0005, 0006, 0009, and 0010.

| Practice | Public source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Deterministic public v0.2.0 publication and active-source fast-forward | Accepted public v0.1.0 lineage; APG12/APG12A release and user validation; APG13 stable dispositions | Application of accepted project procedure | APG14 evaluation and exit; public v0.2.0 release commit and annotated tag | Adopted after deterministic rebuild, independent review, atomic publication, fresh-checkout validation, and unchanged integration ownership | None; all six skills remain `stable` |

The APG13 evidence-classification correction changes project records only and
copies no expression. Exact private source, public object, link, command, and
report identities remain publication excluded. The full-restart fresh-session
smoke is an external application observation and is not inferred from
shell-level release evidence.

## APG15 proposal provenance

APG15 proposes architecture and candidate owners without implementing or
adopting source-derived procedure. It synthesizes from accepted APG policy and
history, a private maintainer-authored APG router and engineering guidance,
representative multi-language repository practice, and primary upstream
language, framework, and database documentation inspected on 2026-07-20.

| Practice | Public source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Public APG routing and synthesis-first guidance migration | Accepted APG leaf, ownership, lifecycle, and provenance policy; generalized private integration behavior | Independently written proposal synthesis | ADR 0011 and APG15 evaluation | ADR 0011 accepted; router and synthesis later adopted separately through APG16 and APG17 | None |
| Shared profile contract and Green, Yellow, Orange, and Red warning semantics | Maintainer-authored guidance; representative real repository practice; primary upstream documentation | Independently written proposal synthesis | Proposed ADR 0012 and APG15 evaluation | Proposed; no profile implemented | None |
| Ten language and framework profile candidates | Python, Bash, Bats, Go, Ruby, Zsh, ZUnit, Nix, PostgreSQL, and SQLite primary documentation plus generalized local practice | Candidate inventory; no retained procedure text | Proposed ADRs 0011 and 0012 | Inventory only; each needs separate evaluation | None |

Exact private paths, repository identities, machine policy, and source topology
remain publication excluded. APG15 copies or adapts no external or private
expression, introduces no code or dependency, and creates no notice payload.
Future implementation phases must record relevant semantic source versions or
dated phase-local source IDs with explicit limitations and complete rights
review for their actual derivation mode.

## APG16 public-router disposition summary

APG16 uses independently written public expression. Generalized
maintainer-authored private routing practice informed the problem statement and
candidate requirements, but no private wording, path, repository identity,
topology, installed-tool state, or personal guidance is copied or exposed.

Current official Codex skill documentation was inspected on 2026-07-20 at
[`learn.chatgpt.com/docs/build-skills.md`](https://learn.chatgpt.com/docs/build-skills.md).
It informs repository- and user-scoped discovery, explicit and model-selected
skill use, symlink support, duplicate-name non-merging, and refresh or restart
behavior. APG copies or adapts no OpenAI documentation expression or
implementation.

| Practice | Public source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Optional APG ambiguity, routing-audit, and capability-health selection | Accepted ADR 0011; six stable APG trigger boundaries; frozen APG16 native and private capability baselines | Independently written synthesis | `skills/agentic-praxis-grimoire-workflow/SKILL.md`; APG16 evaluation | Adopted after 21 frozen applications, exact-map validation, and independent review | New router begins `provisional`; six stable leaves unchanged |
| Schema-version-1 skill-local capability map | Current public APG catalog and accepted support-file ownership | Project-authored deterministic metadata | Router `references/capability-map.json`; focused standard-library unit test | Adopted with exact current routable-catalog coverage and self-exclusion | None |

Exact private source identity, hashes, source topology, worker returns, and
duplicate-name observations remain publication excluded. The public skill has
no third-party code, dependency, runtime, notice payload, or private evidence
dependency.

## APG17 guidance-synthesis disposition summary

APG17 uses independently written public expression. A bounded sample of
maintainer-authored private guidance and historic prompts supplied problem,
privacy, ownership, and migration evidence without contributing copied wording
or a public dependency on private topology. Raw sensitive guidance was neither
inspected for content nor retained.

Current official Codex skill documentation was inspected on 2026-07-20 at
[`learn.chatgpt.com/docs/build-skills.md`](https://learn.chatgpt.com/docs/build-skills.md).
It informs the technical authoring, repository discovery, symlink, explicit
selection, refresh, and focused-skill boundary. Native technical skill
authoring and APG lifecycle governance remain distinct from pre-rewrite corpus
classification. APG copies or adapts no OpenAI documentation expression or
implementation.

| Practice | Public source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Mixed-guidance decomposition and bounded disposition before rewrite | Accepted APG project model, provenance policy, authoring lifecycle, sixteen frozen APG17 families, and sanitized maintainer-authored source classifications | Independently written synthesis | `skills/synthesizing-repository-guidance/SKILL.md`; ADR 0013; APG17 evaluation | Adopted after frozen applications, bounded 34-unit dogfood, exact-map validation, and independent review | New synthesis leaf begins `provisional`; existing maturities unchanged |
| Seven-entry routable capability map | Current eight-row development catalog and accepted router support-file ownership | Project-authored deterministic metadata | Router `references/capability-map.json`; focused standard-library tests | Adopted with exact routable-catalog coverage, self-exclusion, and a mixed-guidance route | None |

The historic manager-prompt corpus supports only a future-candidate
recommendation; no final skill name, prompt, or implementation is derived from
it. Language-specific units remain profile candidates while ADR 0012 is
`Proposed`. Exact private source identities, hashes, unit ledgers, and worker
returns remain publication excluded. APG17 adds no third-party code,
dependency, runtime, notice payload, source migration, or private cutover.

## APG17A record-correction provenance

APG17A corrects two publication-excluded public-release identity fields from
APG17 using the accepted APG14 record, live public refs, a fresh checkout, and
the unchanged active public-backed checkout. The public release is unchanged,
and the correction introduces no source expression, dependency, notice duty,
skill change, maturity change, migration, or external mutation.

The corresponding publishable notes contain no private object identities. The
maintainer's smoke deferral is recorded as a subsequent external disposition,
not as new technical evidence or a reversal of APG17 acceptance.

## APG18 Python-profile disposition summary

APG18 uses independently written public expression. Current Python 3.14.6
language and standard-library documentation, PEPs, the Python Packaging User
Guide, Pylint 4.0.6, current Ruff settings, Radon 6.0.1, generalized
maintainer-authored guidance, and read-only code distributions supplied
semantic and calibration evidence. No external or private wording, table
structure, or code was copied or adapted.

Python documentation is available under the PSF License Version 2, with
documentation examples additionally available under 0BSD. The inspected PEPs
state public-domain or current PEP reuse terms. The Python Packaging User Guide
is CC BY-SA 3.0. Pylint is GPL-2.0, Ruff is MIT, and Radon is MIT. APG cites
facts and produces independent synthesis; it incorporates no third-party code,
runtime dependency, or notice payload.

| Practice | Public source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Accessible language-profile warning and project-precedence contract | Accepted APG architecture; generalized maintainer evidence; false-escalation review | Independently written synthesis | ADR 0012; `docs/language-profile-contract.md` | Accepted after bounded correction, frozen scenarios, and independent review | None |
| Python structural thresholds and semantic response procedure | Python 3.14.6 documentation and PEPs; Pylint 4.0.6; current Ruff settings; Radon 6.0.1; generalized real-code distributions | Independently written synthesis | `skills/python-language-profile/SKILL.md`; APG18 evaluation | Adopted after 24/24 corrected-candidate scenarios, seven-case read-only dogfood, focused tests, and independent review | New Python profile begins `provisional`; existing maturities unchanged |
| Eight-entry routable capability map | Current nine-row development catalog and accepted router support-file ownership | Project-authored deterministic metadata | Router `references/capability-map.json`; focused standard-library tests | Adopted with exact routable-catalog coverage, self-exclusion, Python route, and process/domain pairing | None |

Exact private source identities, local paths, private preference values,
distribution hashes, file-level dogfood, and worker returns remain publication
excluded. Framework, formatter, linter, type checker, test runner, Python
version, package manager, deployment, dependencies, and accepted exceptions
remain target-repository policy. APG18 performs no source migration, root
cutover, private skill removal, public release, or fresh-session application
smoke.

## APG19 Shell-profile disposition summary

APG19 uses independently written expression. GNU Bash 5.3 documentation and
patches, ShellCheck 0.11.0 factual rule evidence, bats-core 1.13.0 documentation
and source, the official Zsh 5.9.2 release and manual, ZUnit v0.8.2 historical
source and documentation, generalized private guidance classifications, and
read-only code/test distributions supplied semantic and calibration evidence.
No external or private wording, code, table structure, project command, or
machine state was copied or adapted.

Bash is GPL-3.0-or-later and its manual is GFDL-1.3-or-later without invariant
sections or cover texts. ShellCheck is GPL-3.0. bats-core and ZUnit are MIT.
Zsh uses its permissive distribution notice with file-specific terms for some
contributions. These sources are factual evidence, not dependencies or
mandated project tools.

| Practice | Public source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Separate shell-language and test-harness ownership | Current Bash, Bats, Zsh, and historical ZUnit semantics; APG warning contract; private-guidance classification | Independently written synthesis | ADR 0014; APG19 evaluation | Bash, Bats, and Zsh retained; ZUnit deferred on source/version evidence | Three new profiles begin `provisional` |
| Bash structural and semantic response procedure | GNU Bash 5.3; current patches; ShellCheck 0.11.0 facts; read-only distributions | Independently written synthesis | `skills/bash-language-profile/SKILL.md` | Adopted after frozen scenarios, one correction, dogfood, focused tests, and review | Existing maturities unchanged |
| Bats structural and harness response procedure | bats-core 1.13.0 documentation/source; read-only suites | Independently written synthesis | `skills/bats-test-profile/SKILL.md` | Adopted after frozen scenarios, one correction, dogfood, focused tests, and review | Existing maturities unchanged |
| Zsh structural and semantic response procedure | Official Zsh 5.9.2 manual/release; read-only distributions | Independently written synthesis | `skills/zsh-language-profile/SKILL.md` | Adopted after tightened thresholds, frozen scenarios, one correction, dogfood, focused tests, and review | Existing maturities unchanged |
| ZUnit ownership reservation and re-entry condition | Canonical v0.8.2 and historical Zsh support evidence | Factual disposition only | ADR 0014; APG19 evaluation | `deferred-source-or-version`; no skill artifact | None |
| Eleven-entry routable capability map | Current twelve-row development catalog and accepted router support-file ownership | Project-authored deterministic metadata | Router `references/capability-map.json`; focused standard-library tests | Exact routable-catalog coverage and self-exclusion | None |

Exact private paths, hashes, worker returns, local version state, and file-level
dogfood remain publication excluded. Exact interpreters, runners, tools,
commands, platforms, CI, coverage, and accepted exceptions remain repository
policy. APG19 performs no private-source migration, root reduction, public
release, active-integration change, dependency addition, or application smoke.

## APG19A semantic-identity reconciliation summary

APG19A accepts APG19's substantive dispositions and adopts ADR 0015. Tracked
public and publication-excluded records now use semantic phase, ADR, exit,
release, source-version, and phase-local evidence identities. Exact Git objects
remain owned by managed reports and transient verification output.

One reproduced Bats defect required a forward correction: the structural test
count now includes the supported comment function form as runner-recognized
tests without authorizing target evaluation merely to count them. Bash and Zsh
remain byte-identical; ZUnit remains `deferred-source-or-version`. The
correction uses independently written expression based on bats-core v1.13.0
documentation and changes no license, dependency, maturity, catalog shape,
distribution contract, or application-smoke boundary.

The public source basis for APG's identity policy is project-authored governance
and historical APG record practice. The policy, guide, standard-library checker,
tests, evaluation, and exit copy or adapt no third-party expression.

| Practice | Public source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Semantic phase identity, independent record sequences, durable references, and precommit finalization | APG governance and historical record practice | Project-authored policy synthesis | ADR 0015; phase and record identity guide; instructions and current owners | Adopted by APG19A after identity audit and non-author review | None |
| Deterministic phase and record identity validation | ADR 0015 mechanical invariants; existing standard-library command conventions | Project-authored implementation | `apg-check-record-identity`; helper; focused integration tests; public-release validation | Adopted after failing-first evidence and resulting-tree validation | None |
| Supported Bats comment-form test counting | bats-core v1.13.0 documentation; APG19 Bats profile and frozen evidence | Independently written correction | `skills/bats-test-profile/SKILL.md`; APG19A evaluation | One forward correction after reproduced undercount and focused review | Existing `provisional` maturity unchanged |

## APG20 Go and Ruby profile disposition summary

APG20 uses independently written expression. Go 1.26.5, the Go 1.26 language
specification, compatibility and memory-model documents, standard-library and
module documentation, and first-party parser, vet, testing, and diagnostics
supplied Go facts. Ruby 4.0.6, Ruby 4.0 language/core/standard-library/security
documentation, maintenance and compatibility material, and RubyGems/Bundler
4.0.16 supplied Ruby facts. golangci-lint v2.12.2 and RuboCop 1.87 were factual
threshold-calibration evidence only. Generalized private guidance and read-only
Go 1.26.5 and Ruby 4.0.6 distributions supplied false-escalation and semantic
evidence. No external or private wording, code, or table structure was copied
or adapted.

Ordinary Go website prose is generally available under CC BY 4.0 except where
noted; displayed code and Go source-distribution content use BSD terms;
third-party modules retain their own licenses. golangci-lint code is GPL-3.0.
Ruby is available under the Ruby License or 2-clause BSD subject to
file-specific `LEGAL` exceptions; RubyGems/Bundler source is available under
MIT or its Ruby-like terms; RuboCop documentation is CC BY-SA 4.0. These are
evidence sources, not runtime dependencies or mandated project tools.

| Practice | Public source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Proposed Go language-profile ownership | Go 1.26.5 semantics, compatibility, memory model, modules, standard library, diagnostics, and calibrated real-code distributions | Independently written evaluation evidence | APG20 evaluation and publication-excluded calibration | `deferred-material-defect` after one correction and additional material final-review findings; no leaf retained | None |
| Proposed Ruby language-profile ownership | Ruby 4.0.6 semantics, compatibility, RubyGems/Bundler, security guidance, and calibrated real-code distributions | Independently written evaluation evidence | APG20 evaluation and publication-excluded calibration | `deferred-material-defect` after one correction and additional material final-review findings; no leaf retained | None |
| Unchanged eleven-entry routable capability map | Current twelve-row development catalog and accepted router support-file ownership | Project-authored deterministic metadata | Existing router capability map and focused standard-library tests | Temporary candidate entries removed; resulting map remains exact | None |

Exact private paths, source hashes, worker returns, local runtime state, and
file-level dogfood remain publication excluded. Exact formatters, analyzers,
test runners, commands, versions, engines, frameworks, platforms, CI,
coverage, and accepted exceptions remain repository policy. APG20 performs no
private-source migration, root reduction, public release, active-integration
change, dependency addition, schema change, or application smoke.

## APG20A Go and Ruby correction summary

APG20A uses independently written synthesis and the same semantic Go 1.26.5,
Ruby 4.0.6, and RubyGems/Bundler 4.0.16 source families after refreshing their
current status and license boundaries. It copies no external code, prose, or
table structure. Read-only maintained sources provide factual line, API,
ownership, and classification evidence; public-safe synthetic cases provide
truthful legacy-minimal-fix evidence where no owner-classified real source is
available.

| Practice | Public source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Corrected Go language-profile ownership | Go 1.26.5 specification, compatibility, memory model, packages, source and site rights, and maintained calibration sources | Independently written synthesis | `go-language-profile`; APG20A evaluation | `retained-provisional` after one APG20A correction and fresh acceptance | New provisional leaf |
| Corrected Ruby language-profile ownership | Ruby 4.0.6 language, core, maintenance, security, RubyGems/Bundler 4.0.16, distribution `LEGAL`, and maintained calibration sources | Independently written synthesis | `ruby-language-profile`; APG20A evaluation | `retained-provisional` after one APG20A correction and fresh acceptance | New provisional leaf |
| Report append-lock release-race correction | POSIX filesystem behavior and project-authored report contract | Project-authored implementation and deterministic regression | report helper and Bats test | Reproduced defect corrected and independently accepted | None |

APG20A performs no source migration, dependency addition, public release,
active-integration mutation, schema change, or application smoke.

## APG21 Nix and relational-engine profile summary

APG21 uses independently written synthesis from current official sources and
read-only maintained or documentation-derived examples. Private guidance
contributes only generalized problem and false-escalation evidence; exact
commands, topology, machine state, frameworks, preferences, credentials, and
protected data remain private or project-owned.

| Practice | Public source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Nix language-profile ownership | Nix 2.35.2 manual, separately versioned Nix 2.35.1 source calibration, NixOS/Nixpkgs 26.05 modules and maintained source | Independently written evaluation evidence | APG21 evaluation and publication-excluded calibration | `deferred-material-defect` after one correction and a second material scenario contradiction; no leaf retained | None |
| PostgreSQL database-profile ownership | PostgreSQL 18.4 SQL, MVCC, transaction, lock, DDL, routine, security, backup, replication, and maintenance documentation and maintained source | Independently written synthesis | `postgresql-database-profile`; APG21 evaluation | `retained-provisional` after fresh acceptance | New provisional leaf |
| SQLite database-profile ownership | SQLite 3.53.3 SQL, transaction, lock, WAL, migration, pragma, backup, integrity, extension, path, and filesystem documentation and maintained tests | Independently written synthesis | `sqlite-database-profile`; APG21 evaluation | `retained-provisional` after one APG21 correction and fresh acceptance | New provisional leaf |
| Separate relational-engine ownership | Current PostgreSQL and SQLite engine semantics | Project-authored decision | ADR 0016 | Accepted; no generic SQL profile | None |

Nix source/reference material uses LGPL-2.1-or-later, Nixpkgs/NixOS code uses MIT with
component-specific exceptions, PostgreSQL source/documentation uses the
PostgreSQL License, and SQLite core source/documentation is dedicated to the
public domain with adjacent-component exceptions. APG21 copies no external
code or prose and adds no runtime dependency.

APG21 performs no source migration, root reduction, private decommission,
public release, active-integration mutation, schema change, Nix evaluation,
database operation, or application smoke.

## APG21A Nix correction summary

APG21A uses independently written synthesis from the same semantic Nix source
families after a current source and rights refresh. The mutable Nix 2.35.2
manual remains distinct from the public Nix 2.35.1 source tag and the mutable
NixOS/Nixpkgs 26.05 series. Nix and its bundled manual use
LGPL-2.1-or-later; Nixpkgs/NixOS source uses MIT with component-specific
exceptions; independently authored nix.dev site material uses CC BY-SA 4.0.
APG copies no source expression or code.

| Practice | Public source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Corrected Nix language-profile ownership | Nix 2.35.2 manual; Nix 2.35.1 source; NixOS/Nixpkgs 26.05 merge, module, purity, store, and activation semantics | Independently written synthesis | `nix-language-profile`; APG21A evaluation | `retained-provisional` after all prior and ten focused merge scenarios, read-only dogfood, and non-author review | New provisional leaf |
| PostgreSQL restore-scope correction | PostgreSQL 18.4 recovery and operation-specific forward-correction semantics | Independently written correction | `postgresql-database-profile`; APG21A evaluation | Corrected after failing evidence and focused re-review | Existing provisional maturity unchanged |

Exact source paths, worker returns, environment details, and operational
identities remain publication excluded. APG21A adds no runtime dependency,
notice payload, source migration, root cutover, public release, active-
integration mutation, schema change, Nix or database operation, or application
smoke.

## APG22 dogfood and migration-design summary

APG22 uses project-authored APG artifacts, bounded read-only APG and RepoMap
guidance, classified private guidance, historic manager prompts, current
official ZUnit source metadata, and public-safe synthetic cases. Private and
historic sources supply evidence only. No private prose, prompt, path,
topology, or personal guidance is copied into public APG.

| Practice | Source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Cross-repository router/profile/synthesis dogfood | Current APG owners; bounded APG and RepoMap artifacts; classified private guidance; public-safe synthetic boundaries | Project-authored evaluation | APG22 public evaluation and publication-excluded matrix | 35/35 expected dispositions matched after one evidence-record correction; no behavior correction | None |
| Guidance-migration design | APG and RepoMap root/scoped guidance; classified private global and skill guidance | Independently written synthesis | v0.3 guidance-migration proposal and private ledgers | Proposal complete; no cutover or decommission | None |
| Native authoring coexistence | Current Codex native authoring boundary and APG lifecycle owners | Project-authored disposition | APG22 evaluation | No separate public writing skill justified | None |
| Manager-assignment candidate | Historic publication-excluded prompts; current planning, worker, router, and protocol owners | Independently written candidate analysis | `APG22-MANAGER-ASSIGNMENT-CANDIDATE-01` evidence | Superseded by terminal APG22A evaluation | None |
| Legacy ZUnit scope | ZUnit v0.8.2 release and canonical repository history; historical Zsh support claims; current Zsh 5.9.2 release | Independently written source/runtime disposition | APG22 scope evidence | Legacy-only version-bounded profile may be evaluated only after maintainer authorization | None |

ZUnit is MIT-licensed. APG22 copies no ZUnit or target source and establishes no
current ZUnit compatibility. It adds no dependency, notice payload, skill,
fixture, schema, migration, root change, target mutation, public release,
active-integration mutation, application smoke, Nix operation, database
operation, or graph operation.

## APG22A approved-roadmap assignment summary

APG22A uses current official OpenAI documentation for Codex skills,
`AGENTS.md`, subagents, long-running work, and projects; current APG governance
and procedure owners; an exhaustive publication-excluded 63-artifact historic
prompt inventory; and independently written public-safe scenarios. Official
documentation was inspected on 2026-07-21 and is treated as mutable current
capability evidence rather than an immutable product contract.

| Practice | Source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Approved-roadmap manager-assignment composition | Official current Codex capability documentation; APG manager-worker, identity, planning, worker-assignment, routing, and review owners; generalized functional observations from publication-excluded historic prompts | Independently written clean-room synthesis | `composing-approved-roadmap-assignments`; ADR 0017; APG22A evaluation | `retained-provisional` after ordinary baseline, 30/30 frozen cases, focused tests, and non-author review | New provisional leaf |

No historic prompt expression, private path, private identity, target detail,
or notice payload is copied. APG22A adds no dependency, public release,
user-managed name, active-integration mutation, schema change, source cutover,
application smoke, or successor-phase authority.

## APG22B version-bounded ZUnit summary

APG22B uses the ZUnit v0.8.2 release, tagged source, documentation, runner,
assertions, hooks, configuration, output, tests, historical CI, and MIT license;
Revolver v0.2.4 under MIT; and official Zsh 5.3.1 and 5.9.2 release sources,
notes, manuals, and distribution terms. APG copies no upstream expression and
adds no runtime dependency.

| Practice | Source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Exact version-bounded ZUnit test profile | ZUnit v0.8.2; Revolver v0.2.4; official Zsh 5.3.1 and 5.9.2 | Independently written synthesis and disposable compatibility evidence | `zunit-test-profile`; ADR 0014; APG22B evaluation | Exact 5.9.2 pair retained; 5.3.1 unsupported on tested environment; no range claim | New provisional leaf |
| ZUnit compatibility fixtures | Tagged upstream tests and project-authored public-safe cases | Project-authored harness and fixtures | Publication-excluded APG22B evidence | 98 upstream and 7 focused tests pass for 5.9.2; adverse and cleanup cases pass | None |

The harness uses canonical public sources, unprivileged temporary prefixes, a
credential-free environment, startup isolation, bounded execution, and exact
cleanup. Official signatures were present, but no OpenPGP verifier was
available, so signature validation is not claimed. No root/private migration,
public release, active-integration mutation, schema change, Nix operation,
application smoke, or APG23 work occurs.

## APG22C ZUnit startup-isolation evidence correction

APG22C uses the same official ZUnit v0.8.2, Revolver v0.2.4, and Zsh 5.3.1 and
5.9.2 source families. It copies no external expression and adds no dependency.

| Practice | Source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Selected user-startup positive and negative controls | Official Zsh startup semantics; project-authored APG22B fixture | Project-authored harness correction and executable evidence | Publication-excluded APG22C evidence; APG22B harness | Corrected after reproduced path mismatch; exact 5.9.2 support retained | None |
| Corrected exact ZUnit compatibility disposition | ZUnit v0.8.2; Revolver v0.2.4; official Zsh 5.3.1 and 5.9.2 | Forward evaluation disposition | APG22C evaluation; ADR 0014 subsequent disposition | 5.9.2 retained; 5.3.1 unsupported; no range claim | None |

The correction proves isolation only from the selected user `.zshenv` under
the recorded runner invocations. It claims no control over unavoidable global
or platform startup behavior. No skill expression, source identity, rights
classification, notice payload, root/private migration, public release,
active-integration mutation, schema, Nix operation, application smoke, or
APG23 work changed during APG22C.

## APG23 readiness and maturity disposition

APG23 adds no external expression and no runtime dependency. It reuses the
accepted phase-local source records for each current leaf, checks their refresh
boundaries, and records fresh application and non-author review evidence.

| Practice | Source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Fresh selector and explicit-use smoke | Client-supplied repository skill inventory; current APG leaves and map | Direct application evidence | APG23 public-safe evaluation and publication-excluded ledger | Passed for all 13 v0.3 skills | Supports individual dispositions only |
| Individual maturity and release inclusion | APG16 through APG22C evidence; current source/version boundaries | Independent review and manager disposition | ADR 0018; readiness matrix; APG23 records | No material defect; all 13 included | Eight promotions; five retained provisional |

Exact current byte identity was transient verification only. APG23 does not
copy private source expression, refresh external source code, publish, migrate
guidance, or change public/reference/target repositories or active integration.

## APG24 v0.3.0 distribution summary

APG24 adds no external expression and no runtime dependency. It applies the
project-authored release and lifecycle architecture to the APG23-included
nineteen-skill set.

| Practice | Source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Nineteen-skill public distribution | ADRs 0009, 0018, and 0019; current APG catalog and projections | Project-authored release mechanics | Public policy; v0.3.0 candidate and records | Exact non-private projection with nineteen critical skills and projections | None |
| Variable user release transitions | Existing version-1 source identity and state; ADR 0019 | Project-authored lifecycle correction | `apg-user-skills`; integration guide | Exact source-specific update, rollback, and recovery | None |
| Current project release set with legacy subsets | Existing version-1 managed-subset state; ADR 0019 | Project-authored lifecycle correction | `apg-project-skills`; projection guide | New default nineteen; existing subsets preserved | None |

Release inclusion remains independent of the fourteen-stable/five-provisional
maturity split. Exact ZUnit support remains limited to v0.8.2 with Zsh 5.9.2
under the recorded startup boundary. APG24 copies no private evidence into the
public surface, adds no source notice, and grants no Nix or database operational
authority. Exact Git, manifest, remote, link, and report evidence remains
publication excluded.

## APG24A external closeout summary

APG24A adds no external expression, dependency, or skill content. It records
the human maintainer's successful public-v0.3 fresh-session smoke observation
and separately authorized personal-router decommission, then verifies the
resulting state through project-authored Git, link, catalog, and byte checks.

| Practice | Source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| External public-router smoke disposition | Human maintainer observation; current public and active release state | Recorded observation plus focused resulting-state verification | APG24A evaluation and exit | Passed; public v0.3.0 unchanged | None |
| Personal-router transition closeout | Separate human authority; private tracked restoration source | Read-only private-skill diff and recovery inspection | Publication-excluded APG24A evidence | Decommissioned; exact restoration owner retained | None |

No private skill expression, configuration body, credential, or unrelated
worktree payload enters the public surface. APG24A does not claim provenance
for the external action beyond the supplied human authority and directly
observed resulting state.

## APG25 structured-work architecture summary

APG25 uses current project-authored APG procedures and tools, a designated
read-only RepoMap prototype, current official pytest/pytest-xdist/pytest-cov,
coverage.py, Python, and Git documentation, and bounded classifications of
three private personal skills. Private and RepoMap wording is not copied.

| Practice | Source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Structured formal/non-phase defaults and prompt compression | Current APG manager-worker, identity, assignment-composition, planning, implementation, and review owners; public-safe frozen assignments | Independently written project convention and one bounded correction | Structured defaults; ADR 0020; assignment-composition leaf | Accepted after failing-first focused evidence and non-author review | Existing provisional maturity unchanged |
| Scoped testing, coverage remediation, and real-boundary policy | Current APG test owners; designated RepoMap prototype; official pytest guidance | Independently written synthesis | Testing and coverage policy; ADR 0021 | Architecture accepted; process correction and migration deferred | None |
| xdist coverage architecture | Official pytest-cov, coverage.py, pytest-xdist, and pytest sources inspected 2026-07-22 | Independently written synthesis | Testing and coverage policy; v0.4 roadmap | pytest-cov selected as future default; no dependency added | None |
| Python-first Git show/diff/operational architecture | Current APG report scripts and tests; official Python subprocess/os and Git add/diff documentation | Independently written design | Reporting architecture; ADR 0021 | Accepted; implementation deferred | None |
| ChatGPT-manager namespace and subrouting | Current APG actor/trigger evidence, catalog, checker, lifecycle, projection, and router owners | Project-authored topology design | ChatGPT topology; ADR 0022 | Accepted by APG25; implemented by APG30 | One new provisional subrouter |
| Personal hygiene transition ledger | Three classified private personal skills; current APG and RepoMap owners | Publication-excluded coherent-unit synthesis | Private APG25 ledger and public bounded summary | Two decommission candidates and one scope-reduction candidate; no private edit | None |

Mutable external documentation records its inspection date and must be refreshed
before dependency/version selection or implementation. APG25 adds no copied
expression, notice payload, runtime dependency, package metadata, executable,
test framework, test move, public candidate, active-integration mutation, or
personal-skill change. Exact private source locations and restoration evidence
remain publication excluded.

## APG26 pytest and Bash-to-Python capability summary

APG26 uses current official pytest, pytest-xdist, pytest-cov, coverage.py,
Python, Git, and GitPython sources inspected on 2026-07-22 together with
project-authored APG lifecycle, language profiles, reporting architecture,
report executables, and tests. The two leaves and their scenario/threshold
contracts are independently written synthesis. No external code, source
expression, notice payload, private skill wording, or report payload is copied.

| Practice | Source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Pytest collection, fixture, assertion, mock, xdist, coverage, and warning judgment | pytest 9.1.1 (MIT); pytest-xdist 3.8.0 (MIT); pytest-cov 7.1.0 (MIT); coverage.py 7.15.2 (Apache-2.0); Python 3.14.6 docs (PSF-2.0, examples also 0BSD) | Independently written synthesis | `pytest-test-profile`; APG26 evaluation and private calibration | Retained after thirty frozen scenarios, failing-first focused contracts, and fresh review | New row begins `provisional` |
| Existing Bash-to-Python compatibility migration | Python 3.14.6 docs; current Git CLI docs and GPL-2.0-only source boundary; GitPython 3.1.54 security release (BSD-3-Clause); APG Bash/Python profiles; current project-owned report family | Independently written synthesis | `converting-bash-scripts-to-python`; APG26 evaluation and private calibration | Retained after thirty frozen scenarios, one option-injection correction, read-only dogfood, focused contracts, and fresh review | New row begins `provisional` |
| Report-family migration map | Current APG report scripts, shared Bash owner, Bats tests, and accepted Python-first architecture | Project-authored read-only classification | Publication-excluded APG26 dogfood record | Future core/adapters mapped; no source or test conversion | None |

The source versions are calibration evidence, not project requirements or
adopted dependencies. GitPython 3.1.54 hardens unsafe Git option validation;
the delta reinforces the fixed-vector baseline. GitPython is permitted for
later bounded evaluation but is not selected or added. Refresh an affected source boundary before a later
behavior-bearing correction, maturity review, or publication when upstream
semantics or rights materially change. Public and active v0.3.0 remain
unchanged.

## APG27 and APG27A Python agent-reporting implementation summary

The APG27 candidate and APG27A adoption apply project-authored ADR 0021, the current APG report executables and
tests, the retained conversion procedure, and the Python and Git source
boundaries already evaluated by APG25 and APG26. The implementation is
independently written project code. It copies no external code or expression
and adds no third-party package, notice payload, or runtime dependency.

| Practice | Source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Importable Python report core and exact Git-show conversion | Project-authored Bash report family and Bats contracts; ADR 0021; Python standard library; fixed-vector Git CLI | Compatible project-authored conversion | `libexec/agent_report`; Python entry points; ADR 0023 | Adopted by APG27A after APG27 partial | None |
| Temporary-index Git-diff state evidence | ADR 0021; official Git add/diff/status semantics; Python subprocess, temporary-file, hashing, and replacement primitives | Independently written implementation | `git-diff-report` format version 1; reporting architecture | Adopted for characterized POSIX local filesystems | None |
| Existing-record operational association | Existing common envelope and operational format; project-authored canonical phase-report convention | Independently written compatible extension | Operational validator and association owner; ADR 0023 | Adopted by APG27A | None |
| GitPython disposition | APG26 GitPython 3.1.54 calibration and fixed-vector comparison | Re-evaluated dependency disposition | ADR 0023; APG27 evaluation | Not selected; no measured advantage or dependency authority | None |

The prior Bash implementation remains available through Git history as the
rollback source. Windows report replacement and network-filesystem semantics
remain unsupported rather than inferred from Python portability. Public and
active v0.3.0 release artifacts remain unchanged. APG27A independently freezes
historical v0.3.0 policy and adopts the corrected development checker; it does
not publish v0.4.0.

## APG28 and APG28A pytest migration

APG28 refreshes official pytest 9.1.1, pytest-xdist 3.8.0, pytest-cov 7.1.0,
and coverage.py 7.15.2 documentation and independently implements the APG
runner and inventory candidate. Pytest, pytest-xdist, and pytest-cov are MIT-licensed;
coverage.py is Apache-2.0 licensed. The exact pins are development-only and add
no runtime dependency. Project-authored tests, configuration, and documentation
copy no external expression. The dependency declaration remains uncommitted
because APG28 stopped Partial. Public and active v0.3.0 remain unchanged.

APG28A preserves that partial result and adopts the same exact dependency set
after runner, release-policy, process-accounting, artifact, Bats-disposition,
and coverage corrections pass review. The dependencies remain development-only;
no external expression is copied. Public and active v0.3.0 remain unchanged.

## APG29 process-skill alignment

APG29 uses project-authored ADRs 0020, 0021, 0023, and 0024; the adopted APG28A
runner and evidence; existing APG process leaves; and fifty-one public-safe
project scenarios. It copies no external expression and adds no source,
dependency, license, notice, or private-skill wording.

| Practice | Source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Useful-contract coverage remediation and scoped evidence | APG testing policy, APG28A runner evidence, existing implementation and planning leaves | Project-authored bounded correction | `implementing-with-test-discipline`; `planning-repository-work` | Accepted after frozen cases, focused tests, and fresh review | None |
| Mock, real-boundary, coverage, and report verification | APG testing policy, reporting architecture, existing review leaf | Project-authored bounded correction | `reviewing-and-verifying-repository-work` | Accepted after frozen cases, focused tests, and fresh review | None |
| Structured manager-assignment compression | Structured defaults, manager-worker protocol, existing roadmap-assignment leaf | Project-authored bounded correction | `composing-approved-roadmap-assignments` | Accepted after frozen cases, focused tests, and fresh review | Existing provisional maturity unchanged |

Names, triggers, catalog descriptions, capability-map entries, projections,
and maturity rows remain unchanged. Public and active v0.3.0, personal skills,
target repositories, and future ChatGPT topology remain unchanged.

## APG30 ChatGPT-manager topology and subrouter

APG30 uses project-authored ADR 0022, the APG25 topology design, current APG
checker and lifecycle owners, the unchanged manager-assignment leaf, and
thirty public-safe topology scenarios. It copies no external or private skill
expression and adds no third-party dependency, license, or notice payload.

| Practice | Source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Nested ChatGPT-manager canonical ownership with flat discovery | ADR 0022; APG checker, catalog, project/user lifecycle, and release owners | Project-authored implementation | `skills/chatgpt/`; lifecycle and release modules | Accepted after failing-first direct/nested and historical-source evidence | None |
| ChatGPT-manager capability selection | ADR 0022; general router contract; manager-assignment trigger evidence | Independently written project skill and local map | `chatgpt-manager-workflow` | Retained provisional after thirty frozen cases and focused review | New row begins `provisional` |
| Manager-assignment canonical move | Existing project-authored leaf and exact pre-move bytes | Pure canonical relocation with source-declared path updates | `skills/chatgpt/composing-approved-roadmap-assignments` | Procedure and provisional maturity unchanged | None |

Historical v0.1.0 through v0.3.0 direct-child policy remains version-bounded.
Public and active v0.3.0, personal skills, target repositories, and application
configuration remain unchanged. Post-restart discovery evidence is deferred to
APG31.

## APG31 personal-hygiene shadow and conditional transition

APG31 uses project-authored ADR 0022, current APG structured defaults and
review owners, current source-qualified repository policies, direct
post-restart client discovery, and publication-excluded private coherent-unit
and restoration evidence. It copies no private skill expression into public
APG and adds no external source, dependency, license, or notice payload.

| Practice | Source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Fresh-session ChatGPT-manager discovery and routing | Current APG catalog, flat projections, canonical router owners, and client-supplied source paths | Read-only project verification | APG31 evaluation and exit | Passed; no APG30 correction | None |
| Personal docs-only replacement and transition | APG structured defaults, repository-owned docs-only policy, and private exact restoration evidence | Publication-excluded classification and independently authorized private decommission | Public aggregate records and private exact ledger | Decommissioned; external discovery smoke pending | None |
| Git-history retained-private boundary | APG structured Git defaults, repository conventions, and private source-qualified routing evidence | Publication-excluded classification | Public aggregate records and private exact ledger | Scope reduction deferred unchanged | None |
| RepoMap phase replacement | Current RepoMap contributor owners, APG structured defaults, and private source-qualified routing evidence | Read-only cross-repository shadow | Public aggregate records and private exact ledger | Decommission deferred unchanged | None |

APG development, catalog, projections, maturity, routing, public and active
v0.3.0, reference evidence, and target repositories remain unchanged.

## APG31A personal-hygiene transition completion

APG31A uses the maintainer-reported external smoke result, current APG and
repository owners, fresh private caller classification, and
publication-excluded restoration evidence. It copies no private expression
into public APG and adds no external source, dependency, license, or notice
payload.

| Practice | Source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| APG31 external-smoke closeout | Maintainer report plus current client catalog | Subsequent observation with bounded corroboration | APG31 evaluation and exit; APG31A records | Passed without rewriting APG31 Partial | None |
| Git-history scope reduction | APG structured defaults, repository Git owners, and publication-excluded transition evidence | Private transition with public aggregate disposition | Current generalized owners and scope-reduced target | Scope-reduced after non-author review | None |
| RepoMap phase decommission | Current RepoMap instructions and contributor owners plus publication-excluded transition evidence | Private transition with public aggregate disposition | Current RepoMap owners | Decommissioned after non-author review | None |

APG development and public/active v0.3.0 remain unchanged. Exact private
delivery, restoration, caller, and machine evidence remains
publication-excluded.

## APG32 Minitest test profile

APG32 uses current official Minitest, `minitest-mock`, RubyGems, and Ruby
sources inspected on 2026-07-23 together with project-authored APG lifecycle,
test, Ruby-language, router, catalog, projection, release-policy, and inventory
owners. The leaf, thresholds, scenarios, evaluation, and tests are
independently written synthesis. No external code, source expression, example,
table, notice payload, or private skill wording is copied or adapted.

| Practice | Source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Minitest test/spec, assertion, lifecycle, fixture-alternative, isolation, parallel, filter, runner, plugin, reporter, boundary-effect, and structural judgment | Minitest 6.0.6 tagged source and documentation (MIT); RubyGems release metadata | Independently written synthesis | `minitest-test-profile`; APG32 evaluation and private calibration | Retained after thirty-six frozen scenarios, failing-first focused evidence, one bounded ownership correction, and fresh review | New row begins `provisional` |
| Versioned mock and stub boundary | `minitest-mock` 5.27.0 tagged source and documentation (MIT); Minitest 6.0.0 removal record | Independently written synthesis | Minitest profile mock/stub procedure and stops | Retained as version-sensitive guidance; no dependency selected | None |
| Ruby calibration and rights boundary | Ruby 4.0.6 official release facts; Ruby License or two-clause BSD subject to file-specific `LEGAL` terms | Independently summarized facts and rights calibration | APG32 source record and profile maintenance boundary | Calibration only; no compatibility matrix or project version selected | None |

Minitest 6.0.6, `minitest-mock` 5.27.0, and Ruby 4.0.6 are calibration
evidence, not project requirements or a verified universal combination.
Refresh affected sources before a later behavior-bearing correction, maturity
review, or publication when discovery, lifecycle, empty-run, parallel, plugin,
reporter, mock, stub, or supported-Ruby semantics materially change. Public and
active v0.3.0 remain unchanged.

## APG33 Dockerfile profile

APG33 uses current official Docker documentation, Dockerfile frontend,
BuildKit, and OCI Image Spec sources inspected on 2026-07-24 together with
project-authored APG lifecycle, language, router, catalog, projection,
release-policy, and inventory owners. The leaf, thresholds, scenarios,
evaluation, and tests are independently written synthesis. No external code,
source expression, example, table, notice payload, or private skill wording is
copied or adapted.

| Practice | Source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Dockerfile parser, stage, instruction-form, variable-scope, context, copy, add, mount, cache, user, runtime-default, platform, and structural judgment | Docker documentation and Dockerfile frontend 1.25.0 sources (Apache-2.0); BuildKit 0.31.2 sources (Apache-2.0) | Independently written synthesis | `dockerfile-profile`; APG33 evaluation and private calibration | Retained after forty frozen scenarios, failing-first focused evidence, one bounded boundary and measurement correction, and fresh review | New row begins `provisional` |
| Image-configuration boundary | OCI Image Spec 1.1.1 (Apache-2.0) | Independently summarized facts and boundary calibration | Dockerfile profile runtime-default procedure and stops | Calibration only; Docker-specific health, downstream-build, exporter, and runtime behavior remains separately owned | None |
| Shell and live-operation boundary | Official Dockerfile shell, exec, builder, and platform semantics; existing APG language and authority owners | Project-authored ownership synthesis | Dockerfile profile pairing and authority stops | Retained without selecting a shell, build command, image, platform, builder, runtime, or live operation | None |

Dockerfile frontend 1.25.0, BuildKit 0.31.2, and OCI Image Spec 1.1.1 are
calibration evidence, not project requirements or a verified universal
combination. Refresh affected sources before a later behavior-bearing
correction, maturity review, or publication when parser, instruction, context,
cache, mount, Windows, platform, provenance, or image-configuration semantics
materially change. Public and active v0.3.0 remain unchanged.

## APG34 Vagrantfile profile

APG34 uses current official Vagrant source and documentation and current
official Ruby release and licensing sources inspected on 2026-07-24 together
with project-authored APG lifecycle, language, router, catalog, projection,
release-policy, and inventory owners. The leaf, thresholds, scenarios,
evaluation, and tests are independently written synthesis. No external code,
source expression, example, table, notice payload, or private skill wording is
copied or adapted.

| Practice | Source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Vagrantfile configuration-version, load-order, machine, box, provider, plugin, network, synced-folder, provisioner, trigger, state, host-dependent, and structural judgment | Vagrant 2.4.9 tagged source and current official documentation; current development source | Independently written synthesis | `vagrantfile-profile`; APG34 evaluation and private calibration | Retained after forty frozen scenarios, failing-first focused evidence, one bounded source-semantics and machine-measurement correction, and fresh review | New row begins `provisional` |
| Vagrant and documentation rights boundary | Vagrant and current official documentation source under Business Source License 1.1 with MPL 2.0 as the change license | Independently summarized facts and rights calibration | APG34 source record and profile maintenance boundary | Calibration only; no upstream expression or notice payload copied | None |
| Ruby and live-operation boundary | Ruby 4.0.6 official release and licensing sources; Vagrant 2.4.9 declared Ruby `>= 3.0` and `< 3.5`; existing APG language and authority owners | Project-authored ownership synthesis | Vagrantfile profile Ruby, shell, state, and authority stops | Retained without selecting a Ruby runtime, provider, box, plugin, host, command, or live operation | None |

Vagrant 2.4.9, current development source, current documentation, and Ruby
4.0.6 are calibration evidence, not project requirements or a verified
universal combination. Refresh affected sources before a later
behavior-bearing correction, maturity review, or publication when
configuration loading, box metadata, provider or plugin behavior, network,
synced-folder, provisioner, trigger, state, Ruby compatibility, licensing, or
representative false-escalation evidence materially changes. Public and active
v0.3.0 remain unchanged.

## APG35 remaining v0.4 skill authoring

APG35 uses current official Go `testing` and release documentation, the
canonical matryer/is repository source and license read at its release tag,
official google/go-cmp package documentation and repository release metadata,
and current Nix, Nixpkgs, and NixOS manual sources, all inspected on 2026-07-25,
together with project-authored APG lifecycle, language, ownership, and
structural owners. The five candidate leaves, thresholds, scenarios,
specifications, proposed ADR, evaluation, and exit are independently written
synthesis. No external code, source expression, example, option list, table,
notice payload, or private skill wording is copied or adapted.

| Practice | Source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Native Go test placement, subtest, attribution, cleanup, isolation, entry-point, parallel, goroutine, example, benchmark, fuzz, selection, caching, and structural judgment | Official Go source-derived `testing` package documentation plus separately classified go.dev release history; Go 1.26.0 and Go 1.25.0 supported, go1.26.5 and go1.25.12 current patches | Independently written synthesis | APG35 candidate and evaluation | Authored only; not integrated or adopted | None |
| matryer/is instance mode, assertion-family, equality, typed-nil, diagnostic, and attribution judgment | Canonical matryer/is repository source and license read at release tag `v1.4.1` | Independently written synthesis | `matryer-is-test-profile`; APG35 evaluation and private calibration | Authored only; not integrated, tested, or adopted | None; a proposed row would begin `provisional` |
| google/go-cmp equality-versus-diff, option-composition, comparer, transformer, filter, ignoring, unexported-field, tolerance, ambiguity, and ordering judgment | Official `cmp` and `cmp/cmpopts` package documentation and canonical repository release metadata at `v0.7.0` | Independently written synthesis | `go-cmp-test-profile`; APG35 evaluation and private calibration | Authored only; not integrated, tested, or adopted | None; a proposed row would begin `provisional` |
| Thin composition ownership across already-selected Go testing components | The three component calibrations above; no independent API calibration by design | Project-authored ownership synthesis | APG35 stack candidate and rejected ADR 0025 | Authored only; rejected by APG36 | None |
| Nix testing surface taxonomy, evidence hierarchy, platform-matrix, purity, sandbox, store, remote-builder, cache, and structural judgment | Nix 2.35.2 reference manual; Nixpkgs/NixOS 26.05 manuals; nix.dev integration-testing tutorial | Independently written synthesis | APG35 candidate and evaluation | Authored only; deferred by APG36 | None |
| Source rights boundary | Go source and source-derived package documentation and google/go-cmp under BSD-3-Clause; general go.dev site prose under CC BY 4.0 except where noted; matryer/is under MIT; Nix source and its bundled reference manual under LGPL-2.1-or-later; Nixpkgs and NixOS under MIT subject to component-specific exceptions; independently authored nix.dev content under CC BY-SA 4.0 | Independently summarized facts and rights calibration | APG35 source ledger and APG36 review | Calibration only; no upstream expression or notice payload copied | None |

These releases and source tags are calibration evidence, not project
requirements, supported-version promises, or a verified universal combination.
APG36 subsequently closed the two Nix source gaps: sandbox defaults and relaxed
behavior are documented in the Nix 2.35.2 manual, and the current stable
Nixpkgs/NixOS series is 26.05. Those facts exposed additional behavior defects
rather than validating the candidate.

Refresh affected sources before a later behavior-bearing correction, maturity
review, or publication when the supported Go release pair or a `testing`
restriction changes, the matryer/is assertion surface or attribution behavior
changes, the go-cmp option set or documented comparer obligations change, the
Nix flake-check output set, check-phase contract, pass-through convention,
testers surface, driver surface, or sandbox boundary changes, or any license
boundary changes.

APG36 independently re-read the source families, created transient public-safe
fixtures for all 154 frozen scenarios, and ran a disposable Go 1.25.10 harness
against matryer/is `v1.4.1` and google/go-cmp `v0.7.0`. It found multiple
behavior corrections per component and no viable retained stack. All five
candidates were removed through the APG36 forward commit; ADR 0025 was
Rejected. No copied expression or additional notice obligation was found.

Integrated development remains 25 canonical skills, 25 catalog rows, and 25 flat
projections. Public and active v0.3.0 remain unchanged at 19/19/19. No APG35
candidate is integrated, adopted, mature, published, or deployed.

APG37 re-inspected all six source families on 2026-07-25 while redesigning the
four deferred candidates on an authoring branch. The Go family was read from a
local read-only Go 1.25.10 installation covering the `testing` and `cmd/go`
sources, the specification appendix on language versions, and the
build-constraint reference; matryer/is `v1.4.1` and google/go-cmp `v0.7.0` were
read from canonical tagged sources including the build-tagged matryer/is helper
file; and the Nix, Nixpkgs, and NixOS families were read from the versioned
2.35 reference and the 26.05 release-branch documentation. The rights boundary
recorded above is unchanged, and APG37 records the Go split between
source-derived material and general site prose rather than one class. The Nix,
Nixpkgs, and NixOS sources are mutable, so the inspection date is their
controlling state marker.

APG37 reversed several APG35 facts against those sources: matryer/is treats two
nil-like operands as equal so a typed nil equals an untyped nil, and it
provides its own helper registry rather than the native mechanism; go-cmp
requires a total order only for map sorting and explicitly not for slice
sorting; the Go API does not require a package-level test hook to call the
runner; language semantics follow the module directive and per-file build
constraints rather than the toolchain; flake checking builds only the checks
output; and sandbox defaults are platform-dependent. No copied expression or
additional notice obligation was found. All APG37 text is independently written
synthesis.

Integrated development still remains 25/25/25 and public and active v0.3.0
remain 19/19/19. No APG37 candidate is integrated, adopted, mature, published,
or deployed, and none carries executable evidence.

## APG38 integration provenance

| Practice | Current sources | Derivation | Result | Rights and refresh |
| --- | --- | --- | --- | --- |
| Native Go test lifecycle and structure | Go 1.26.5 and 1.25.12 source and documentation; installed Go 1.25.10 compatibility harness; bounded maintained Go corpus | Independently worded synthesis with executable public-safe fixtures | `go-test-profile` retained `provisional` after one correction cycle and fresh review | Go source and source-derived package docs BSD-3-Clause; refresh on supported-release, `testing`, fuzz, artifact, language-version, or corpus change |
| matryer/is assertion behavior | canonical matryer/is `v1.4.1`, commit `02e4121244e0f9e27b5ebdade62f5da7b7a42f23` | Independently worded exact-version synthesis and isolated probe | `matryer-is-test-profile` deferred after post-correction attribution and escalation defects; current leaf absent | MIT; differing selected release is a stop and refresh |
| google/go-cmp comparison behavior | canonical google/go-cmp `v0.7.0`, commit `9b12f366a942ebc7254abc7f32ca05068b455fb7` | Independently worded exact-version synthesis and isolated probe | `go-cmp-test-profile` retained `provisional` | BSD-3-Clause; differing selected release is a stop and refresh |
| Nix testing taxonomy candidate | Nix 2.35.1 commit `85855aacbf5659dd85a8a290c2532d5dc6196555`; Nixpkgs/NixOS 26.05 commit `597283ad8aa0b331c788e97c4c262d58877074ef`; inspected 2026-07-25 | Source-only independent review and corpus classification | `nix-test-profile` deferred after a post-correction FreeBSD sandbox-default defect; current leaf absent | Nix LGPL-2.1-or-later; Nixpkgs/NixOS MIT subject to component exceptions; exact source revision required before re-authoring |

Initial rights review found that native cleanup/fuzz wording and multiple
go-cmp comparer, transformer, filter, sorting, diff, and fixture passages
tracked upstream expression too closely for APG37's categorical no-adaptation
claim. APG38 independently rewrote those passages and required a final
source-expression re-review. No public file depends on publication-excluded
evidence or contains a development Git identity, local path, credential,
personal detail, or private topology.

## APG39 authoring provenance

APG39 re-inspected the matryer/is, Nix, Nixpkgs, and NixOS families on
2026-07-26 while authoring final replacement candidates for the two
APG38-deferred profiles on an authoring branch. matryer/is was read at
canonical lightweight tag `v1.4.1` (MIT; reverified as the newest upstream
tag), which resolves to a commit dated 2022-05-16; the GitHub release was
published 2023-02-23, and that publication date is not the tag commit date.
The reviewed corpus covered the
primary assertion source, the build-constrained helper-registry source, the
release's own tests, and the license. Nix was read at canonical tag `2.35.1`
(LGPL-2.1-or-later; reverified as the newest upstream release), covering the
local store settings implementation, the flake-check command documentation
source, and the 2.35 release notes; the sandbox default is enabled on Linux
and FreeBSD and disabled elsewhere, and the setting's stale descriptive text
is recorded as a discrepancy with the implementation and release notes
controlling. Nixpkgs and NixOS 26.05 were read at the exact APG38-pinned
commit for phase defaults, target fallback, cross-compilation gating, and
package-associated tests, so the pinned commit is the controlling state
marker. All APG39 text is independently written synthesis; no copied
expression or additional notice obligation was found.

Integrated development remains 27/27/27 and public and active v0.3.0 remain
19/19/19. The two APG39 candidate leaves exist only on the authoring branch;
neither is integrated, adopted, mature, published, or deployed, and neither
carries executable evidence.

## APG40 integration provenance

APG40 independently reverified exact matryer/is `v1.4.1` and MIT rights, exact
Nix 2.35.1 and LGPL-2.1-or-later rights, and the pinned Nixpkgs/NixOS 26.05
state and MIT-with-component-exceptions boundary. The matryer/is lightweight
tag resolves to its 2022-05-16 commit; the 2023-02-23 date is the GitHub
release publication date. All APG40 text is independently written factual
synthesis; no copied expression or additional notice obligation was found.

The Nix profile is retained provisionally after source-only review, forty
corrected public-safe scenarios, one coherent correction pass, and fresh
non-author review. No Nix parse, evaluation, build, store/cache operation,
container, virtual machine, activation, deployment, or external operation was
run. The matryer/is profile is deferred and absent because corrected-state
review found a remaining equality source-fact defect after its one permitted
behavior correction. ADR 0027 is Rejected and ADR 0026 remains Accepted.

Integrated development is 28/28/28. Public and active v0.3.0 remain 19/19/19.

## APG41 readiness provenance

APG41 derives its readiness decisions from the existing public skill
procedures, accepted ADRs, frozen public-safe scenario fixtures,
repository-owned executable contracts, and independently written
publication-excluded dogfood records. It copies no external expression and
adds no dependency or notice obligation. Exact local objects, source paths,
commands, candidate fingerprints, environment facts, reviewer returns, and
managed-report identities remain publication excluded.

The retained Go and Nix source/version and rights boundaries remain those
recorded by APG38 through APG40. APG41 does not refresh, broaden, or universalize
them: native Go, go-cmp v0.7.0, Nix 2.35.1, and pinned Nixpkgs/NixOS 26.05
dogfood is source or fixture evidence unless the readiness record explicitly
reports current-host repository execution. Public and active v0.3.0 remain
19/19/19. The v0.4.0 candidate result is pre-release evidence, not publication,
deployment, stable maturity, or external compatibility evidence.

## APG42 release provenance

APG42 derives no new skill expression and adds no external dependency or notice
obligation. It projects the APG41-accepted skills, records release/current-state
policy, and retains the exact canonical NOTICE blob
`d622b081f4cf109501d03bbfebd1224a3ecbcf33` from the verified historical
repository object. An unrelated project identity is not part of the release.
Existing source-version and rights boundaries remain unchanged.

Public and active v0.4.0 contain the same 28/28/28 surface as the accepted
development source. Publication does not transform source/fixture-reviewed
Go, go-cmp, Ruby, Minitest, Dockerfile, Vagrantfile, Nix, PostgreSQL, SQLite,
manager, or conversion evidence into universal runtime compatibility.
Postcommit object identities, local evidence paths, reviewer returns, and
deployment fingerprints remain publication excluded or managed operational
evidence.

## APG43 correction provenance

APG43 records a one-time maintainer-authorized correction of a release-blocking
unrelated project identity in the v0.4.0 `NOTICE`. The canonical historical
NOTICE bytes were restored in amended APG42, then projected into the corrected
public release and active public-backed source. No skill expression,
dependency, maturity, routing, release metadata, or historical v0.1.0-v0.3.0
object changed. Exact old/new objects, leases, and managed-report evidence are
publication excluded under `private/evaluations/apg43/`. Future releases are
append-only; v0.5 requires separate authority.

## APG44 analysis provenance

APG44 inspects one external source family: `petar-nauka/fact-check-skill`,
default branch `main` at `ebfde09a28b5547cbed29f5f66ddfd3595e64ade` (MIT), with
a local clone verified clean at exact remote parity on 2026-07-26. Every APG44
adopted boundary is independently written synthesis from observable facts
(derivation mode: synthesized); no external table, taxonomy, schema, code,
scoring formula, or output structure is adopted. APG45 later found short
source-shaped phrases in publication-excluded authoring analysis,
independently re-expressed them, and confirmed no material external expression
remains in the resulting state. Nothing is adopted in APG44.

The three Go dogfood clones and two Knowledge Forge AI repositories named in
the [v0.5 roadmap](v0-5-roadmap.md) were inspected only enough to validate
roadmap owner boundaries; that inspection is not dogfood, compatibility, or
adoption evidence. Exact local identities, the recommendation ledger, frozen
scenarios, and the Codex handoff remain publication excluded under
`private/evaluations/apg44/`. Development, public, and active surfaces remain
28/28/28.

## APG45 peer-review provenance

APG45 independently reverifies the same exact external source and its declared
MIT license, corrects the tracked source count to 26, and records static
schema/validator, package-license, and renderer URL-boundary findings. A bounded
disposable standard-library characterization runs without installation or
network and proves only external structure and arithmetic behavior.

REC-01 through REC-04 are accepted or accepted with narrowing as clean-room
future contracts; REC-05 and REC-07 through REC-10 are rejected; REC-06 is
deferred. No recommendation is implemented. ADR 0029 is Accepted with
amendment. Exact APG44/APG45 objects, reports, local source paths, reviewer
returns, and probe details remain publication excluded. Development, public,
and active surfaces remain 28/28/28.

## APG46 authoring provenance

APG46 authors the candidate guidance for accepted REC-01 through REC-04 from
the APG45 clean-room contracts without returning to the external source for
wording. The review-skill and provenance-policy additions — including the
claim-relative source authority and material access-limitation sections above
— are independently written synthesis (derivation mode: synthesized). No
external table, tier ordering, schema, score, mode taxonomy, template, or
output structure is adopted, and no rejected or deferred recommendation is
implemented. The candidate changes are authored on a Claude branch and remain
pending separately authorized Codex validation and integration; integrated
development, public, and active surfaces remain 28/28/28.

## APG47 integration provenance

APG47 preserves the exact APG46 authoring object, records failing-first
semantic evidence before correction, and independently retains REC-01 through
REC-04 after one forward review-skill correction. `docs/provenance.md` remains
the sole normative source-authority owner; the synthesis path required no
additional pointer.

The correction and its tests are independently written project synthesis.
Fresh comparison with the external fact-check corpus found no exact sequence of
five or more normalized tokens and no copied or recognizably adapted table,
taxonomy, score, mode, schema, template, ledger, renderer, or result structure.
No new notice obligation arises.

Development remains 28/28/28 with unchanged 14/14 maturity and routing. Public
and active tracked corrected-v0.4.0 fingerprints remain unchanged. Exact
objects, report identities, external comparison evidence, reviewer returns,
and operational details remain managed or publication excluded.

## APG48 dogfood and authoring provenance

APG48 inspects five public Go repositories read-only as dogfood evidence —
conduitio-labs/conduit-connector-http, esnet/gdg, blockvisionhq/sui-go-sdk,
kubernetes-sigs/bom, and apache/skywalking-mcp (Apache-2.0 and a BSD-style
LBNL variant) — and reverifies the canonical matryer/is `v1.4.1` tag (MIT)
and the go-cmp `v0.7.0` version identity (BSD-3-Clause). Derivation mode for
every APG48 artifact is independently written synthesis from observed facts:
no target test code, upstream prose, table, example, or diagnostic text was
copied or adapted, and no notice obligation arises. Factual API identifiers
are used as facts.

One material access limitation is recorded under the access-limitations
policy: canonical matryer/is sources were read through a fetch-summarized
channel rather than byte-level files, converging with the prior exact-source
and runtime records; byte-level re-reading is a required later Codex step.
Negative dogfood findings are scoped to the inspected samples and
inventories.

The authored `matryer-is-test-profile` candidate and its specification are
candidates pending Codex review, not integrated behavior. Development remains
28/28/28 with unchanged maturity and routing; public and active remain
corrected v0.4.0. Exact clone commits, local paths, and operational details
remain publication excluded.

## APG49 validation provenance

APG49 closes APG48's byte-access limitation with a clean exact `v1.4.1`
source read, module checksum verification, selected-build-file inspection, and
isolated runtime probes. It independently re-reads the five dogfood
repositories at their recorded commits. Exact local paths, private APG commit
and report identities, raw module output, and probe transcripts remain
publication excluded.

The correction guidance, public-safe scenarios, tests, evaluation, and
decision language are independently written synthesis. Fresh comparison found
no material sequence of five or more normalized tokens shared with upstream
source or the APG48 private scenario ledger. Factual API names, versions,
reflection kinds, and minimal call shapes do not copy protectable expression.
No source or license text enters the public artifacts and no new notice duty
arises.

The candidate is terminally deferred after fresh corrected-state review and
its current public candidate surfaces are forward removed. The exact source,
runtime, dogfood, rights, and defect evidence remains publication excluded;
it is evidence for a possible separately authorized future attempt, not a
retained skill or compatibility claim.

## APG52 evidence-foundation provenance

APG52 independently reproduces the APG51 evidence defect, resolves every named
abbreviated source identity without substitution, and selects a new corpus
before accepted measurement. Publication-excluded manifests pin full commits,
trees, roots, rights blobs, classification and exclusion rules, artifacts,
measurements, samples, exact statistics, and hypothesis comparisons. Two
disjoint acquisitions produce byte-identical canonical evidence.

The rights ledger separates source code, specification, documentation, README
grant, and package-metadata absence controls. It rechecks ECMA-262 document and
embedded-software terms separately; TypeScript source and website terms; Node,
CSSWG, CommonMark, GFM, JSX, React/react.dev, MDX, Astro, Starlight, and Vitest
terms. APG52 performs factual measurement only, copies no upstream or target
expression, and exposes no private path or personal identifier in canonical
output. Exact target and source objects, local acquisitions, and detailed
machine evidence remain publication excluded. No evidence label constitutes a
license conclusion beyond its exact row, architecture decision, candidate
approval, or authoring authority.

## APG53 operational-tooling provenance

| Practice | Source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Flat shared-skill symlink projection | Exact maintainer-supplied `flatten-skill-symlinks` input, SHA-256 `b8b9ef833465ba01485d635db7eb1cd7bda2b65b191c633952bfabe47d150c00`; APG53 integration authority | Supplied expression retained and adapted, then independently hardened for owner state, overlap, marker, lock, no-overwrite installation, transactional rollback, and race checks | `bin/flatten-skill-symlinks`; `libexec/flatten_skill_symlinks.py`; `libexec/skill_projection_state.py` | Current development and future v0.5 public candidate; not yet published | Input has no embedded third-party notice or license marker; record as maintainer-supplied and integration-authorized, not APG-authored |
| Preventive Git change-size policy | APG52 blob/report measurements; official GitHub repository limits, large-file guidance, and generated-file display guidance reviewed 2026-07-28 | Independently written standard-library Git-object checker and APG-specific policy | `bin/apg-check-change-size`; `testing/apg-change-size-policy.json`; ADR 0032 | Adopted for current development and future public candidates | APG limits are stricter preventive and review-usability controls, not GitHub platform limits |

APG53's disposable Claude-shaped filesystem dogfood verifies the projection
layout and command behavior. The reviewed Claude documentation does not
explicitly guarantee directory-symlink discovery, so APG53 makes no
Claude-runtime recognition claim and does not mutate a live integration.

## APG54 global-installer provenance

| Practice | Source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Multi-repository personal skill projection | Exact 944-byte maintainer-supplied Bash prototype identity; official Codex and Claude skill-root documentation reviewed 2026-07-28; existing APG projection contracts | Intended convenience behavior retained; production expression independently implemented with Python standard library, combined inventory/state, collision refusal, state-last transaction, rollback, and uninstall | `bin/install-global-skills`; maintained inventory, state, transaction, and CLI helpers; ADR 0033 | Current development and future v0.5 public candidate; not published or live-installed | No skill, catalog, projection, route, or maturity change |

The local corroborating Bash bytes match the declared supplied identity,
remain publication excluded, and are recorded as maintainer-supplied rather
than APG-authored. The uploaded attachment was not materialized separately in
the APG54 session. The Python implementation does not translate the loop
literally and copies no third-party expression.
Official documentation contributes current compatibility facts only. Exact
local intake paths, user-local state, scratch targets, and operational
transcripts remain publication excluded. Disposable filesystem dogfood proves
link and ownership behavior, not live Codex or Claude runtime discovery.

## APG55 transaction-hardening provenance

APG55 is an independently implemented correction derived from the APG54
codebase, maintainer-declared defect cases, POSIX filesystem behavior, and the
Python standard library. It adds no third-party source corpus, dependency, or
copied expression. Functional metadata names, transaction stages, and
fault-injection cases carry no new attribution or notice duty.

Exact development identities, external fingerprints, local paths, temporary
names, and test transcripts remain publication excluded. Public guidance
contains only generalized behavior. No skill, catalog, projection, route,
maturity, release, or active-deployment provenance changes.

## APG56 reconstruction provenance

APG56 synthesizes a fresh Web and Node owner architecture from the verified
APG52 compact evidence, the exact pinned target objects, and the APG50/51
records as prior art and falsification history. Its band derivation consumes
only committed APG52 statistics through a frozen method and a deterministic
publication-excluded tool; no bulk dataset is regenerated and no APG51
hypothesis value contributes to any anchor.

Rights facts are restated from the APG52 exact ledger with every distinction
preserved (ECMA document versus embedded-software terms; TypeScript Apache-2.0
source versus CC BY 4.0 handbook; Node MIT; W3C document license;
CommonMark/GFM CC BY-SA 4.0; the canonical JSX repository's inline README
CC BY 4.0 grant; React MIT source and CC BY 4.0 react.dev; MDX, Astro,
Starlight, and Vitest MIT repository terms; and target rights controls).
APG57 subsequently narrows the theme statement: its original baseline carries
`LICENSE-MIT`, exact post-baseline additions and modifications carry an
AGPL-3.0 notice, package metadata says
AGPL-3.0-or-later, and commercial/NOTICE/CLA surfaces remain separate. No
standards, documentation, code, example, table, or upstream structure is
copied or adapted into APG56
guidance; every record uses independently authored expression
(`synthesized`). Proposed ADR 0034 and its records are design evidence only:
no skill, catalog, projection, route, maturity, release, or
active-deployment provenance changes, and exact development identities and
local paths remain publication excluded.

## APG57 independent-review provenance

APG57 uses exact APG56 and APG52 compact records, exact read-only target
objects, primary source/right records, and an independently implemented
standard-library reviewer. The reviewer method was frozen and approved before
output; it reproduces the historical APG56 values and emits only compact
family, anchor, target-placement, threshold, purpose, and robustness results.
It copies no source or target expression and introduces no dependency.
Corrected-state review finds material compact-interval, target-completeness,
and exact-reproduction-gate defects in that reviewer. Its generated output is
therefore preserved as publication-excluded failure evidence and is not an
accepted measurement surface.

APG57's rejected ADR expression is independently synthesized. Historical
APG56 values and the attempted APG57 ledger/scenarios remain evidence, not
accepted policy. Exact commits,
trees, hashes, local acquisitions, operational reports, and detailed review
output remain publication excluded. No skill, catalog, projection, route,
maturity, release, public, active-deployment, or target provenance changes.

## APG58 CSS-pilot provenance

APG58 authors one candidate CSS leaf and specification from independently
written behavioral synthesis. Its structural limits (300/600/900) are
explicit engineering policy selected before target placement — not derived
from, and never described as, corpus percentiles; the APG52 corpus, the
rejected APG56/APG57 numeric outputs, and the pinned targets serve only as
falsification history and legacy classification evidence. The CSS-language
basis is the CSSWG draft set pinned by the APG52 exact rights ledger (W3C
Software and Document License, document-specific headers respected); target
facts come from live read-only inspection of the exact pinned commits. No
specification wording, source comment, example, target CSS, selector, or
target layout is copied into any APG58 artifact. Proposed ADR 0035 and the
candidate records are design evidence under the practice lifecycle: no
skill-catalog, projection, route, maturity, release, public,
active-deployment, or target provenance changes, and exact development
identities, placements, and local paths remain publication excluded.

## APG59 CSS validation and integration provenance

APG59 independently reverifies the exact CSSWG source and rights pin and the
two exact read-only target trees, then expresses its correction and executable
contracts independently. The transient public-safe fixture contained scenario
identities, policy transitions, and synthetic obligations only; it contained
no target CSS, selector, layout, source comment, local path, or private payload.
Exact object identities, acquisition details, local paths, and reviewer
evidence remain publication excluded.

The proposed limits remain explicit APG maintainability-policy evidence rather
than a corpus statistic. APG59 adds no browser-support claim and does not absorb
design, HTML, browser runtime, accessibility acceptance, Astro/MDX/React host
semantics, Starlight, or tooling ownership. Corrected-state executable and
removal defects require Rejected ADR 0035 and candidate cleanup; development,
public, and active remain 28/28/28.

## APG60 CSS contract-foundation provenance

APG60 derives its behavior only from the accepted APG59 correction and exact
APG58/APG59 history. Its independently written fixtures contain synthetic
counts, labels, authority facts, action tokens, and relative owner locators;
they copy no CSSWG wording, code, selector, example, target source, target
layout, or third-party implementation structure.

The generic surface manifest names public, publication-excluded, and managed-
report owner classes without exposing private payloads or local report
identities. The executable tests use disposable synthetic trees and read-only
Git objects, require no target content or command, and introduce no dependency.
The 300/600/900 values remain rejected-evidence pre-authoring policy, not
current guidance or a corpus statistic. No skill, ADR 0036, catalog,
projection, route, maturity, release, public, active-deployment, or target
provenance changes.
## APG60A provenance

APG60A derives from exact APG60 and preserves the original APG60 fixture as the
named superseded object. The v2 fixture records the forward revision and real
exception grant source. No third-party implementation or prose is copied.
Future CSS evidence remains pinned to the CSSWG commit, tree, license blob,
and right recorded in the publication-excluded handoff.

## APG60B provenance

APG60B is a clean-room forward correction derived from the accepted APG60A
contract and independently reproduced false-pass shapes. Its traceability,
narrative, Python-binding, isolated derivation, and ADR-lifecycle fixtures use
synthetic values and disposable trees. They copy no CSSWG prose, target CSS,
selector, layout, comment, or private payload, and introduce no dependency.
Exact source and target pins remain unchanged and publication excluded where
required. The candidate stays absent; no target command or mutation occurs.

## APG60C provenance

APG60C is a clean-room forward correction derived from accepted APG60B and
independently reproduced synthetic final-value, narrative, history-removal,
and survivor-replacement false passes. It copies no CSSWG prose or target
source, uses Python standard library only, and preserves the frozen CSS
behavior fixture byte-for-byte.

## APG60D provenance

APG60D is an independently written clean-room forward correction derived from
accepted APG60C and synthetic callback, namespace-write, wildcard-history, and
symlink counterexamples. It copies no CSSWG prose, target CSS, selector,
layout, source comment, or third-party implementation expression. The exact
phase manifest contains semantic phase IDs and repository-relative record
paths only. It adds no dependency and changes no source, rights, target,
release, publication, deployment, or active-state provenance.

## APG60E provenance

APG60E is an independently written clean-room forward correction derived from
accepted APG60D and synthetic ancestor-symlink, projection, replacement, and
short-read counterexamples. It copies no CSSWG prose, target CSS, selector,
layout, source comment, private target content, or third-party implementation
expression. The repository-path owner uses Python standard library facilities
only. The frozen CSS behavior fixture, source and rights pins, targets,
release, publication, deployment, and active state remain unchanged.

## APG60F provenance

APG60F is an independently written clean-room forward correction derived from
accepted APG60E behavior and synthetic failing-first import, authority-graph,
and projection-race controls. It adds no third-party dependency and copies no
CSS specification wording, target source, selector, layout, or private payload
into public artifacts.

The repository import boundary, required-role declaration, and coherent
projection observation use Python standard-library facilities and
repository-owned contracts. The APG60E phase-history fixture remains immutable;
the APG60F manifest versions current foundation and future exit identities
forward. CSS behavior, sources, rights, targets, release, publication,
deployment, and active state remain unchanged.

## APG60G provenance

APG60G is an independently written clean-room forward correction derived from
accepted APG60F and synthetic root-replacement, duplicate-derived-set,
semantic-role-redirection, and stale-authority-read controls. It adds no
third-party dependency and copies no CSS specification wording, target source,
selector, layout, or private payload into public artifacts.

The pinned-root, exact-set, code-owned role registry, and entry/descriptor
authority-read contracts use Python standard-library facilities and
repository-owned evidence. APG60F history and reports remain immutable; the
current lifecycle artifacts advance through APG60G. CSS behavior, sources,
rights, targets, release, publication, deployment, and active state remain
unchanged.

## APG60H provenance

APG60H is an independently written forward correction over repository-owned
Python and synthetic tests. It preserves Claude's immutable object, copies no
external expression, adds no dependency, and changes no rights, notice,
target, release, publication, deployment, or active state.

## APG60I provenance

APG60I is an independently written clean-room forward correction derived from
the adopted APG60H object and deterministic synthetic substitution and cleanup
controls. Its descriptor-bound implementation uses Python standard-library
facilities only. It copies no target or third-party source, adds no dependency,
and changes no rights, notice, target, release, publication, deployment, or
active state.

## APG61 provenance

APG61 is independently written clean-room authoring: the candidate leaf,
specification, traceability map, ADR 0036, and records were synthesized from
the frozen APG60A contract, with the CSSWG rights identities reverified from
the repository-owned APG52 ledger and both targets read only as exact Git
objects. It copies no CSSWG, target, or APG58/APG59 candidate expression,
adds no dependency, integrates no surface, and changes no rights, notice,
target, release, publication, deployment, or active state.

## APG62 provenance

APG62 is independently written validation and terminal-disposition work over
the immutable APG61 object and repository-owned frozen APG60A contract. Its
oracle, tests, semantic ledger, correction, and rejection records copy no
CSSWG, target, or rejected-pilot expression and add no dependency. Exact
CSSWG rights identities and both read-only target objects were reverified;
neither target was executed or mutated. Removing the rejected current
candidate changes no rights, notice, public release, active deployment, or
target state.

## APG63 provenance

APG63 is independently written clean-room architecture work: the Markdown
architecture, lean validation contract, ADR 0037, scenario register, and
records were synthesized from repository-owned evidence, with CommonMark
0.31.2 and pinned GFM specification identities and their CC BY-SA 4.0
document rights reverified at exact objects and both targets read only as
exact Git objects. It copies no specification, implementation, or target
expression, adds no dependency, authors no skill, integrates no surface,
and changes no rights, notice, target, release, publication, deployment,
or active state.

## APG64 provenance

APG64 is independently written clean-room review and forward-correction work
over the immutable APG63 object. Exact CommonMark, GFM, target, rights,
configuration, and inventory facts were reverified from primary objects; no
specification, implementation, target, or reviewer expression was copied.
Corrected bytes, exact patch identities, replay vectors, and non-author review
bindings are preserved in publication-excluded evidence. No dependency,
license, NOTICE, target, release, publication, deployment, or active state
changed.

## APG65 provenance

APG65 is independently written clean-room candidate authoring from the
accepted APG64 architecture, lean contract, and corrected scenario register.
The pinned CommonMark 0.31.2 and GFM 0.29 specification objects and their
rights were reverified at exact objects as evidence only; no specification,
implementation, target, APG63, or APG64 expression was copied, and the
rejected CSS candidate prose was not reused. The candidate is synthesized
APG-native expression. No dependency, license, NOTICE, target, release,
publication, deployment, or active state changed.

## APG66 Markdown validation and integration provenance

APG66 independently derives its 34-row executable vector from the accepted
APG64 register and uses exact CommonMark 0.31.2, GFM 0.29, website, and theme
Git objects only as bounded read-only evidence. The retained leaf,
specification, coverage, fixture, tests, integration owners, evaluation, and
exit are independently written APG expression. No CommonMark, GFM,
implementation, test, target, or reviewer expression is copied or adapted.
Specification-document CC BY-SA 4.0 rights remain distinct from identified
BSD-2-Clause/MIT implementation, test, and derived-code regions. This is a
bounded clean-room finding, not legal advice. No dependency, license, NOTICE,
target, publication, deployment, or active-state change occurred.

## APG67 JavaScript architecture provenance

APG67 uses the exact ECMA-262 `es2026` annual tag (ECMAScript 2026, 17th
edition), the live 2027 draft head as moving evidence only, Test262 under its
verified Ecma BSD-style license, and the two pinned target objects as bounded
read-only evidence. The architecture, lean contract, scenario register, ADR
0039, and records are independently written APG expression: no specification
algorithm, grammar production, table, example, Test262 case, or target
expression is copied or adapted. Ecma's natural-language text rights,
MIT-style source-code policy, and TC39 contribution policy are recorded
separately; this is a bounded clean-room finding, not legal advice. No
dependency, license, NOTICE, target, publication, deployment, or
active-state change occurred.

## APG68 JavaScript architecture review provenance

APG68 independently fetched and read exact ECMA-262 annual and errata Git
objects, Test262 objects, and the two pinned target trees. It separates
specification-text, repository-source, annual embedded-software,
contribution, Test262, and target rights. The correction and records are
independently written APG expression: no specification algorithm, grammar,
table, example, Test262 case, source, or target expression is copied or
adapted. The clean-room result is bounded, not legal advice.

## APG69 JavaScript architecture reset provenance

APG69 reverified the exact es2026 annual tag, errata tag, moving-draft
head, and Test262 identities by read-only remote query and refetched the
annual specification, annual license, errata-changed specification, and
Test262 license blobs at their exact commits with matching hashes. Both
pinned target trees were verified unchanged by exact object read. The
fresh architecture, contract, registers, and records are independently
written APG expression: no specification algorithm, grammar, table,
example, Test262 case, source, target, or rejected-APG67/APG68
expression is copied or adapted. The clean-room result is bounded, not
legal advice.

## APG79 JavaScript hardening provenance

APG79 independently reconstructs 24 semantic purposes, 14 fixture purposes,
and three target rows from ECMA-262 17th edition, exact source and rights
objects, read-only target objects, an exact bounded engine observation, and
independently authored APG controls. No specification, Test262, engine-test,
target, or rejected-candidate expression is copied. Three correction rounds are
preserved. Terminal review leaves material proof and ownership defects, so the
candidate remains Proposed and unintegrated. This is bounded factual evidence,
not legal advice.

## APG77D CSS integration provenance

APG77D derives its human-debt and integration records from the preserved
APG76 through APG77C objects, exact W3C source identities, read-only target Git
objects, independently authored APG scenarios and fixtures, and repository-
owned lifecycle, release, test, and rollback checks. It copies no target or
specification expression. Compact v3 remains supporting evidence only. Public
records exclude private topology, local scratch paths, and private payloads.
This is bounded factual evidence, not legal advice.

## APG70 JavaScript architecture review provenance

APG70 independently reverified the exact annual, errata, draft, Test262,
target, rights, and corpus identities; used source expression only as read-only
evidence; and wrote its vectors, correction, reviews, and records as APG
expression. No specification algorithm, grammar, table, example, Test262 case,
source, or target expression was copied or adapted. Fresh review found false
source hashes in the corrected APG70 public snapshot; the preserved snapshot is
Rejected evidence and the terminal record restores the verified identities.
The clean-room/privacy boundary otherwise passes and remains bounded, not legal
advice.

## APG71 TypeScript architecture provenance

APG71 independently verified the TypeScript 7 native release (tag, peeled
commit, tree, license blob, npm version, integrity, and package-to-source
binding), the TypeScript 6 legacy 6.0 patch-line tags and packages, the
`@typescript/typescript6` package (whose exact source relation is recorded
as unavailable), and documentation rights (prose CC-BY-4.0, website code
MIT, compiler repositories Apache-2.0), all from exact objects. Full source
identities live in the single private APG71 identity record and the managed
report; public records use stable labels. Both targets were read as exact
Git objects only. No compiler, baseline, test, diagnostic, documentation,
release-note, target, or rejected-JavaScript-architecture expression was
copied or adapted; every APG71 record is APG expression. The
clean-room/privacy review passes and remains bounded factual evidence, not
legal advice.

## APG72 TypeScript architecture peer-review provenance

APG72 independently reverified the exact TypeScript 7.0.2, 6.0.2/6.0.3, and
5.9.3 package/source bindings, the TypeScript 6 compatibility wrapper's absent
source binding, documentation rights and version scope, and both exact target
objects. Full identities remain publication-excluded; public records use
stable labels. No compiler, package, documentation, target, register, or
rejected-architecture expression was copied or adapted. The website's absent
reuse grant and theme's qualified rights remain non-blocking because no target
expression was reused. The clean-room/privacy conclusion passes as bounded
factual evidence, not legal advice.

## APG73 production recovery governance provenance

APG73 derives product priority, TypeScript 7 destination intent, the bounded
iterative-hardening lifecycle, authority split, debt gate, and future sequence
from explicit human product and governance authority. Existing APG58 through
APG72 records supply historical evidence about the one-correction lifecycle and
its CSS, JavaScript, and TypeScript results; they do not supply the new product
priority or terminal-disposition authority. No target, compiler,
specification, documentation, package, test, or third-party expression was
copied or adapted. Public records omit unpublished target identity and private
topology. Target and corrected release objects were read only for preservation;
no target command ran. The clean-room, rights, privacy, and personal-data
review is bounded factual evidence, not legal advice.

## APG75 TypeScript hardening provenance

APG75 independently reconstructs candidate-semantic, fixture, compiler, target,
rights, and lifecycle evidence before comparing candidate prose. Three
separately preserved correction rounds are independently written APG expression.
No compiler implementation, test or baseline, documentation passage, target
source, or rejected-architecture expression is copied. Maintained fixture and
scenario changes remain original test expression. Public records exclude local
paths, private topology, and personal data. The result is bounded clean-room,
rights, privacy, and personal-data evidence, not legal advice.

## APG74 TypeScript candidate provenance

APG74 derives the candidate and fixture from accepted ADR 0042 product
intent plus fresh primary evidence: npm registry metadata and dist-tags for
`typescript@7.0.2` and `@typescript/typescript6@6.0.2`, the
`microsoft/typescript-go` release-tag source binding, freshly pinned
read-only target objects, and scratch-run compiler observations. The
rejected APG71/APG72 architecture supplied historical defect evidence only;
none of its prose, registers, or vocabularies was copied or revived. No
compiler implementation, compiler test or baseline, documentation passage,
or target source was copied; fixture sources are independently written.
Public records omit private topology and the absolute scratch path. Targets
and corrected release objects were read as exact Git objects only; no
target command ran. The clean-room, rights, privacy, and personal-data
review is bounded factual evidence, not legal advice.

## APG75A TypeScript scope and lifecycle provenance

APG75A derives its correction from the accepted project/compiler ownership
model, the maintained scenario and fixture data, exact APG75 Git/report
objects, and clean-checkout runner observations. The reusable neutrality,
axis, lifecycle, and prerequisite controls are independently authored APG
expression. Theme Forge intent is retained as project metadata without copying
target source. No compiler implementation or documentation text, target source,
private payload, local path, or rejected-candidate expression is copied. Exact
TypeScript 7.0.2 executes only from invocation-owned scratch under its existing
Apache-2.0 rights record. This is bounded factual evidence, not legal advice.
## APG76 CSS candidate provenance

APG76 derives its candidate from freshly read W3C module snapshots under the
W3C Software and Document License, a live pin of the CSS Working Group drafts
repository, and read-only inspection of both targets at exact Git objects. The
profile text, the scenario coverage, and every fixture file are independently
authored APG expression. No specification prose, algorithm, table, example, or
test, no CSS Working Group or browser test, no target stylesheet, and no APG58,
APG59, or APG61 candidate expression is copied; the rejected CSS candidates were
verified by object identity alone. This is bounded factual evidence, not legal
advice.

## APG77 CSS hardening provenance

APG77 independently reconstructs candidate and fixture consequences from dated
W3C modules, exact read-only target objects, official Astro/Vite role
documentation, and independently authored APG tests. Three correction rounds
remain separately committed. No specification, WPT, BCD, package, target, or
rejected-candidate expression is copied. Terminal review leaves two proof-
retention defects, so the clean-room candidate remains Proposed and
unintegrated pending human continuation. This is bounded factual evidence, not
legal advice.

## APG79A JavaScript correction provenance

APG79A preserves the exact APG78/APG79 chain and independently authored APG
correction expression over retained ECMA-262, Test262 rights, bounded exact
engine, and read-only target identities. It copies no specification, test,
engine, or target expression and adds no dependency or notice obligation. Fresh
review leaves five Medium APG contract/evidence defects, so the corrected bytes
remain unintegrated historical evidence and ADR 0045 remains Proposed. This is
bounded factual evidence, not legal advice.

## APG86 GoMock and Vitest provenance

APG86 independently writes `gomock-test-profile` from the official Uber GoMock
v0.6.0 tagged README, changelog, `mockgen` sources, and `gomock` package source
and documentation. The upstream repository is Apache-2.0. APG copies no prose,
code, example, table, generated mock, or diagnostic expression; factual API
identifiers and versioned behavior are used as facts. Refresh is required when
the selected release, generator modes, controller cleanup, expectation counts
or order, matchers, actions, or failure behavior changes.

APG86 independently writes `vitest-test-profile` from official Vitest 4.1
documentation and tagged v4.1.7 repository sources for configuration,
projects, environments, assertions, mocking, timers, pools and isolation,
snapshots, and coverage. Vitest is MIT licensed; its published package records
separately licensed bundled dependencies. APG copies no upstream prose, code,
example, table, snapshot, or diagnostic expression. Refresh is required when
the selected Vitest line or those runner behaviors materially change.

The APG86 boundary fixture, checker diagnostics, integration expression, ADR,
evaluation, and exit are independently authored APG material. No upstream
source is vendored, no dependency or lockfile is added, and no notice
obligation changes. This is bounded factual evidence, not legal advice.

## APG87 JSX and React provenance

APG87 independently writes `jsx-language-profile` from the CC-BY-4.0 draft JSX
specification at `react/jsx` commit
`d614ce76e6ea996ea6dfa122f2a7be71ed96e6eb`, official CC-BY-4.0 TypeScript
JSX/TSConfig documentation, MIT-licensed TypeScript website code, and
Apache-2.0 TypeScript compiler source, all inspected 2026-08-20. JSX grammar is
mutable, defines no runtime semantics, and TypeScript evidence describes one
implementation. APG copies no source prose, grammar, code, examples, or tables;
factual syntax and configuration identifiers are used under clean-room
synthesis.

APG87 independently writes `react-component-profile` from CC-BY-4.0 official
React documentation and MIT-licensed repository tag `v19.2.6`, annotated object
`2fcbe419ed90f863e6f67ce5b9738f38dbec640b`, commit
`eaf3e95ca92be7a23d3c9cc8ffd6f199a40be401`, released 2026-05-06 and
inspected 2026-08-20. APG copies no upstream prose, code, examples, tables, or
diagnostics. Mutable documentation, canary features, and framework-integrated
features do not silently extend the host-independent owner.

Refresh JSX when the grammar, selected transform modes, import-source behavior,
or file-kind handling changes. Refresh React when the selected release line,
render/state model, Effect or Hook rules, context, memoization/compiler
relationship, or error-boundary behavior changes. Removal preserves ADR,
evaluation, exit, and source facts as historical provenance. This is bounded
factual evidence, not legal advice.


## APG79B JavaScript correction provenance

APG79B preserves the exact APG78 through APG79A chain and independently authored
APG correction expression over retained ECMA-262, Test262 rights, bounded exact
engine, and read-only target identities. It copies no specification, test,
engine, target, or rejected-candidate expression and adds no dependency or
notice obligation. Fresh review leaves four Medium APG contract/evidence
defects, so the corrected bytes remain unintegrated historical evidence and ADR
0045 remains Proposed. This is bounded factual evidence, not legal advice.

## APG79C JavaScript decision provenance

APG79C independently records the maintainer's four-item qualification-debt
decision and references exact retained ECMA-262, Test262 rights, Node, target,
and predecessor identities. It copies no specification, test, engine, target,
fixture-output, or third-party source expression and adds no dependency or
notice obligation. Fresh source preflight records one unaccepted Medium
Test262 identity discrepancy and blocks integration without treating Test262 as
semantic authority. This is bounded factual evidence, not legal advice.

## APG79D Test262 source-role correction provenance

APG79D directly re-reads the official Test262 repository identity,
default-branch ref, commit and tree metadata, and top-level licence object. It
preserves the APG79 reviewed pin and the false APG79B assertion as distinct
historical evidence, while making the current authority role-specific and
consequence-bearing. Test262 remains non-normative and no test body, path
inventory, expected result, or other corpus expression is read, copied,
executed, or vendored. The compact exact source-role record and development
evidence stay publication-excluded; public-safe upstream object identities may
appear in lifecycle records without exposing corpus content or private
topology. The correction is independently authored APG expression and adds no
dependency or notice obligation. This is bounded factual evidence, not legal
advice.

## APG79E JavaScript decision and integration provenance

APG79E independently records the maintainer's `JS-QD-005` decision and directly
reverifies the immutable APG79B managed report without copying its body. It
preserves the APG79D source-role correction and Test262's non-normative rights-
only, no-corpus, no-oracle role. Current integration expression is independently
authored APG material; no Test262 test body, engine output, target expression,
or managed-report body is copied. No dependency or notice obligation is added.
This is bounded factual evidence, not legal advice.
## APG80 Node.js candidate provenance

APG80 records fresh Node.js release-schedule, versioned-API-documentation, and
license identities without copying documentation prose, examples, source, tests,
or generated API data. Node repository source and tests are treated as
implementation evidence rather than as a copying license or a public-contract
override. ECMA-262 remains the authority for ECMAScript semantics and is routed
rather than restated, and Test262 is neither needed nor read. All candidate,
fixture, and record expression is independently authored APG material; no target
source, path, command body, package-manager expression, or managed-report body
is copied. No dependency or notice obligation is added. This is bounded factual
evidence, not legal advice.

APG81H integration adds no new external source, copied expression, dependency,
or notice obligation. It retains APG80's independently authored candidate and
the subsequently hardened APG fixture and harness, while current catalog,
projection, route, release, test, and inventory expression remains
independently authored APG material. The exact Node runtimes and TypeScript
compiler are qualification tools, not redistributed release inputs. This is
bounded factual evidence, not legal advice.

## APG88 MDX and Astro integration provenance

APG88 independently synthesizes MDX guidance from exact MDX 3.1.1 object
`50aa8df0b027c893dec9f97a2b7c51539e9f1a4b` and official documentation object
`685627a819567c0788eadb85f5f57065bcc81c2c`, inspected 2026-08-20. The MDX
repository and documentation are MIT-licensed. No upstream prose, source,
examples, tables, fixtures, or diagnostics are copied.

Astro guidance is independently synthesized from Astro 7.1.6 annotated tag
`adbb7cbd12c47a869ad5008688209152e2362849`, exact commit
`9865d1c03af6d1a1f15c9811858778cc952ca4e4`, and official docs object
`ad92aec16358fee8e85f0dcd3b1e6baa9fd039c8`, inspected 2026-08-20. The Astro
and docs repositories are MIT-licensed. No upstream prose, code, examples,
tables, fixtures, or diagnostics are copied. Source versions are calibration
evidence rather than project dependency requirements; mutable behavior is
refresh-gated in each leaf. No dependency or notice obligation is added. This
is bounded factual evidence, not legal advice.
