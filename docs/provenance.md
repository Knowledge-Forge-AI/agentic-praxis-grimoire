# Reference and Provenance Policy

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
