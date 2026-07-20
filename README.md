# Agentic Praxis Grimoire

Agentic Praxis Grimoire (APG) is a modular engineering operating
model for coding agents. It curates practices that improve planning,
implementation, testing, debugging, review, delivery, and coordination without
turning one source methodology into a universal workflow.

Public APG v0.2.0 contains six stable skills, projection and reporting
components, corrected release and user-lifecycle validation, governance, and
licensing terms. It appends one intentionally squashed release commit and an
annotated tag to the preserved public v0.1.0 history. Its canonical public
checkout supplies the maintainer's separately managed user-global Codex
integration. Private development history remains distinct.

APG0 through APG8 are the closed v0.1 development epic, with each historical
terminal outcome preserved, including APG3's blocked result. The epic established
the project, bootstrap maturity model, six skills, repository discovery,
dogfooding, project-local projection and rollback, and RepoMap managed adoption.
The maintainer subsequently decommissioned Superpowers, and a bounded fresh
RepoMap smoke passed after decommission. APG9 closes that epic, reconciles
current state, and accepts the APG10 through APG14 v0.2 roadmap in
[ADR 0006](docs/adr/2026/07/0006-v0-2-objectives-roadmap-and-maturity-promotion.md).

APG10 accepts that closeout, resolves the experimental guideline source's
provenance and reuse boundary, and records its final dispositions in
[ADR 0007](docs/adr/2026/07/0007-experimental-karpathy-guidelines-disposition.md).
Frozen scenarios found current assumption, alternative, traceability, and
speculative-scope behavior adequate. They demonstrated one narrow gap for
locally owned code or test artifacts made unnecessary by the authorized change,
which received one independently reviewed implementation-discipline correction.
No seventh skill or maturity change was introduced.

APG11 accepts
[ADR 0008](docs/adr/2026/07/0008-skill-authoring-maintenance-and-mechanical-validation.md),
establishes the [skill authoring and maintenance guide](docs/skill-authoring-and-maintenance.md),
adds a dependency-free read-only mechanical skill-library checker, and closes the
former candidate-theme queue through the
[legacy roadmap ledger](docs/legacy-roadmap-closure.md). It changes no skill
leaf or maturity state. APG11A's accepted lexical correction then closes
required-key shadowing and fenced-code false negatives without changing that
architecture.

APG12 accepts [ADR 0009](docs/adr/2026/07/0009-public-distribution-and-reproducible-release-validation.md),
adds an exact non-private [public surface policy](release/public-surface.json),
and supplies separate dependency-free commands for reproducible local public
candidates and state-owned user-scope skill links. Its executable regression
detects the public v0.1.0 omitted-wrapper class. Disposable candidate and user
lifecycle dogfood leave the public repository and active integration unchanged.
APG12A subsequently corrects public-lineage and read-only validation defects
without reopening that architecture.

APG13 accepts [ADR 0010](docs/adr/2026/07/0010-six-skill-post-superpowers-stability-dispositions.md)
after individual historical inventories, frozen current applications, complete
regression, and fresh non-author reviews. All six current catalog entries are
`stable`; every canonical leaf remains byte-identical to the APG12A baseline.
APG14 corrects two APG9 evidence labels without changing those dispositions,
publishes the exact non-private v0.2.0 projection, and fast-forwards the active
public-backed source without changing its integration ownership shape. Public
v0.1.0 remains historical and unchanged. Stability and publication do not
establish clean comparative superiority, production warranty, universal
applicability, or automatic invocation. Superpowers remains retired. A full
Codex restart and fresh-session discovery smoke remain an external application
observation after the source update.

## Authority

The human maintainer retains ultimate project, roadmap, publication, license,
and destructive-action authority. ChatGPT manages planning and review only
within a human-authorized task, phase, or preapproved roadmap envelope.
Top-level Codex executes bounded ChatGPT assignments and manages internal Codex
workers. Evidence and recommendations do not expand any actor's authority. The
[manager-worker protocol](docs/manager-worker-protocol.md) defines the complete
chain and stop boundaries.

## Intended audience

APG is for maintainers who design agent workflows, agents that implement or
review those workflows, and contributors evaluating whether a practice improves
correctness, safety, maintainability, or delivery outcomes at an acceptable
cost.

## Project structure

- [`AGENTS.md`](AGENTS.md) contains the small set of repository-wide rules that
  should apply to nearly all work.
- [`docs/project-model.md`](docs/project-model.md) defines artifact ownership,
  evidence domains, and the candidate-to-adoption lifecycle.
- [`docs/skill-authoring-and-maintenance.md`](docs/skill-authoring-and-maintenance.md)
  owns the APG skill-specific authoring, correction, support, maturity,
  deprecation, and removal procedure.
- [`docs/provenance.md`](docs/provenance.md) defines public and
  publication-excluded provenance responsibilities.
- [`docs/manager-worker-protocol.md`](docs/manager-worker-protocol.md) defines
  external authority, top-level management, internal delegation, evidence, and
  final reporting.
- [`docs/adr/`](docs/adr/README.md) records durable architecture decisions under
  an independent four-digit sequence.
- [`docs/status/`](docs/status/README.md) records truthful phase exits under an
  independent five-digit sequence.
- [`skills/`](skills/README.md) contains and indexes the six canonical stable
  APG skill sources.
- [`.agents/skills/`](.agents/skills/) is the checked-in Codex repository
  discovery projection; its six relative symbolic links contain no independent
  skill content.
- [`docs/bootstrap-v0.1.md`](docs/bootstrap-v0.1.md) defines maturity,
  provisional evidence, rollback, dogfooding, and decommission gates.
- [`docs/superpowers-transition.md`](docs/superpowers-transition.md) maps
  materially relevant Superpowers workflows to APG, native Codex, project
  policy, deferral, or rejection.
- [`docs/project-skill-projection.md`](docs/project-skill-projection.md)
  documents opt-in cross-repository installation, adoption, verification, and
  rollback.
- [`docs/public-release-process.md`](docs/public-release-process.md) documents
  exact projection, deterministic candidate construction, validation, and the
  v0.2.0 publication record.
- [`docs/user-scoped-skill-integration.md`](docs/user-scoped-skill-integration.md)
  documents direct public-sourced user links, state, lifecycle, restart, and
  migration boundaries.
- [`docs/superpowers-decommission-runbook.md`](docs/superpowers-decommission-runbook.md)
  preserves the human-owned decommission and rollback sequence after the
  completed operation without authorizing restoration.
- [`docs/evaluations/`](docs/evaluations/apg4-bootstrap-v0.1.md) records the
  public-safe APG4 scenario and review summary; the APG3 blocked record remains
  preserved separately, and the
  [APG10 evaluation](docs/evaluations/apg10-karpathy-guidelines-evaluation.md)
  records the experimental-source dispositions.
- [`docs/roadmap.md`](docs/roadmap.md) records the closed v0.1 epic and the
  bounded APG10 through APG14 v0.2 sequence.
- [`docs/legacy-roadmap-closure.md`](docs/legacy-roadmap-closure.md) gives every
  former candidate or deferred theme a terminal owner or condition.
- `bin/` and `libexec/` contain deterministic reporting tools, the
  dependency-free project-local and user-scoped projection commands, the
  read-only mechanical skill-library checker, and the local-only public
  candidate builder/checker with non-executable helpers.
- `src/test/unit/<language>/` and `src/test/int/<language>/` contain isolated
  unit tests and connected integration tests, respectively. Test filenames use
  `.unit.test.<ext>` or `.int.test.<ext>` suffixes.

## Testing

The repository separates tests by level and implementation language:

```text
src/test/unit/<language>/
src/test/int/<language>/
```

The report-tool unit suite requires Bats 1.5.0 or newer. The Python unit and
integration suites use the standard-library `unittest` runner. Run the current
suites from the repository root:

```sh
bats src/test/unit/bash/*.unit.test.bats
python3 src/test/unit/python/apg_skill_library.unit.test.py
python3 src/test/unit/python/apg_public_release.unit.test.py
python3 src/test/unit/python/apg_user_skills.unit.test.py
python3 src/test/int/python/apg_project_skills.int.test.py
python3 src/test/int/python/apg_check_skill_library.int.test.py
python3 src/test/int/python/apg_public_release.int.test.py
python3 src/test/int/python/apg_user_skills.int.test.py
```

Validate the current canonical skill library and checked-in Codex projection
without mutation:

```sh
bin/apg-check-skill-library [--root <path>] [--format text|json]
```

This command validates only the adopted mechanical APG subset. It does not
prove semantic quality, authority, privacy, provenance, client discovery,
maturity, release completeness, or stable behavior.

## From source to APG practice

A candidate practice moves through a bounded lifecycle:

1. inventory dated source evidence and its ownership, publication, and license
   status;
2. evaluate the concrete problem, evidence strength, generality, activation
   risk, maintenance cost, and appropriate destination;
3. propose an APG-native change with provenance and observable validation
   criteria;
4. validate the change proportionally, including representative non-trigger and
   failure cases where relevant;
5. adopt, defer, reject, or supersede it with a recorded rationale; and
6. keep the adopted artifact, evaluation evidence, documentation, and provenance
   consistent.

Copied or adapted expression requires confirmed reuse rights and any required
notice. Synthesized or inspired practices still retain useful provenance.
Source inclusion, frequency, ownership, or apparent authority is not itself an
adoption decision.

The project model owns this general lifecycle. The
[skill authoring and maintenance guide](docs/skill-authoring-and-maintenance.md)
owns its proportional application to skill changes.

## Publication model

The canonical public identity is `agentic-praxis-grimoire`. Public v0.1.0 was
published as a filtered projection with one intentionally squashed commit and
historically omitted the documented `bin/apg-project-skills` wrapper. ADR 0009
replaces manual selection with an exact projection of every tracked path except
`private/`, plus critical-owner checks that detect deletion from source. Public
v0.2.0 appends one deterministic squashed release commit and annotated tag,
includes the omitted wrapper, and preserves v0.1.0 as its sole parent. Future
publication remains a separately authorized human decision.

## License

Agentic Praxis Grimoire is licensed under the GNU Affero General Public License
v3.0 or later. See [LICENSE](LICENSE).

Commercial licenses are available for proprietary terms, including
closed-source embedding, private service deployments, OEM use, support,
warranty, indemnity, and custom commercial terms. See
[COMMERCIAL-LICENSE.md](COMMERCIAL-LICENSE.md).

Contributions are accepted under the terms in
[CONTRIBUTING.md](CONTRIBUTING.md) and [CLA.md](CLA.md).

## Where to begin

Agents should read [`AGENTS.md`](AGENTS.md), then the focused owner for the task.
Maintainers evaluating source-derived policy should begin with the
[project model](docs/project-model.md), [provenance policy](docs/provenance.md),
and the [ADR index](docs/adr/README.md).
Delegated work should follow the
[manager-worker protocol](docs/manager-worker-protocol.md). The completed v0.1
epic, post-release APG-TEST0 foundation, and completed APG10 through APG14 v0.2
sequence are described in the [roadmap](docs/roadmap.md). No successor roadmap
epic begins automatically.
