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
| Maintainer-authored agent and engineering practices | Generalize the source family publicly; retain exact unpublished identity and paths only in publication-excluded provenance. Ownership supplies adoption authority, not a public license grant. |
| RepoMap | Use the canonical public identity `repo-map`; cite public-intended architecture and contributor practices without exposing its private development lineage. Do not infer a license from an ADR or ownership alone. |
| Superpowers | External source under the MIT License. Preserve the included copyright and license notice for copied or adapted material. Synthesized or inspired use still records provenance. |
| Experimental Karpathy Guidelines | Reference evidence whose inspected frontmatter declares MIT. Treat that declaration separately from verified upstream identity, immutable version, copyright, full license text, and notice obligations. APG10 must complete that review before copied or adapted use. |
| Agent Skills specification | Genuinely public compatibility evidence. Retain a verified public immutable pin when it materially defines the supported leaf shape. |
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
public_source_version: <immutable-public-version-or-not-applicable>
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

The Agent Skills compatibility basis remains pinned to the public
[`agentskills/agentskills` specification](https://github.com/agentskills/agentskills/blob/38a2ff82958afee88dadf4831509e6f7e9d8ef4e/docs/specification.mdx).
APG11 re-evaluated the immutable source's rights boundary. The specification is
documentation under the repository's
[`docs/LICENSE`](https://github.com/agentskills/agentskills/blob/38a2ff82958afee88dadf4831509e6f7e9d8ef4e/docs/LICENSE),
which contains Creative Commons Attribution 4.0 International; repository code
is separately Apache-2.0. APG copies or adapts no specification expression or
upstream code. It independently implements compatible format facts and
project-authored constraints, with the pin providing source and license
attribution. No bundled third-party notice is required for that synthesized
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
evidence with incomplete copied-or-adapted reuse evidence. The captured file is
byte-identical to
[`multica-ai/andrej-karpathy-skills`](https://github.com/multica-ai/andrej-karpathy-skills)
at immutable commit
[`64723a49ea6117894304eb491f0d32a60570bf45`](https://github.com/multica-ai/andrej-karpathy-skills/commit/64723a49ea6117894304eb491f0d32a60570bf45).
The leaf and README declare MIT, but that tree contains no complete license
text, explicit copyright notice, or notice file.

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
It copies or adapts no external skill-authoring methodology. The pinned Agent
Skills specification informs only compatible metadata, name, directory, and
relative-reference constraints; APG's additional leaf headings, catalog, and
projection rules are project-authored requirements.

The specification path is CC BY 4.0 documentation, while upstream repository
code is Apache-2.0. APG11 imports neither expressive documentation nor code;
the public immutable pin and license link identify the influence. No bundled
license or notice text is added for the independently written compatibility
implementation.

| Practice | Public source families | Mode | Destination | Lifecycle status | Maturity effect |
| --- | --- | --- | --- | --- | --- |
| Skill-specific authoring and maintenance lifecycle | APG4 bootstrap; APG6 frontmatter correction; APG7/APG7A executable work; APG9 reconciliation; APG10 behavior correction; project model and provenance policy | Synthesized project procedure | ADR 0008; `docs/skill-authoring-and-maintenance.md` | Adopted after independent lifecycle, invariant, ledger, design, and resulting-state review | None; all six skills remain `provisional` |
| Mechanical APG skill-library validation | Repeated canonical shape, metadata, headings, catalog, link-containment, and checked-in projection checks; pinned Agent Skills specification | Project-authored implementation | `bin/apg-check-skill-library`; standard-library helper; focused unit and integration tests | Adopted for mechanical invariants after failing-first evidence, correction, and development/public dogfood | None |
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
