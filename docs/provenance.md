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
APG1 retained the pin but did not re-evaluate that source's license. Exact
maintainer-source snapshots and path mappings are retained only in
publication-excluded provenance.

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
| Human Superpowers decommission and rollback procedure | Accepted bootstrap decommission gate; transition map; APG6 restart observation; tested APG projection uninstall | Project-authored operational synthesis | `docs/superpowers-decommission-runbook.md` | Adopted as rollback-plan documentation only | None; decommission readiness remains false |

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
| Semantic compliance before idempotent projection success | Accepted ADR 0004; APG7 implementation and behavioral contract; reproduced Git local-exclude behavior | Project-authored correction | `libexec/apg_project_skills_commands.py`; `tests/test_apg_project_skills.py`; APG7 evaluation and projection guide | Adopted after failing baseline evidence, corrected behavioral tests, disposable recovery control, and independent review | None; all six skills remain `provisional` |

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

## APG license boundary

APG is licensed under the GNU Affero General Public License v3.0 or later, with
separate commercial licensing available from the Project Steward. The explicit
human-maintainer decision is recorded in
[ADR 0005](adr/2026/07/0005-public-license-and-contribution-governance.md).

The MIT License for Superpowers applies to Superpowers material, not
automatically to APG. Third-party material remains subject to its own license
and notice requirements. Future contributions are governed by
[`CONTRIBUTING.md`](../CONTRIBUTING.md) and [`CLA.md`](../CLA.md).
