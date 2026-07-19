# Agentic Praxis Grimoire

Agentic Praxis Grimoire (APG) is an early-stage, modular engineering operating
model for coding agents. It curates practices that improve planning,
implementation, testing, debugging, review, delivery, and coordination without
turning one source methodology into a universal workflow.

APG is not yet a production-ready skill library. APG0 through APG2A established
the project and accepted its first evaluation contract. APG3 then closed as
Blocked at its mandatory harness preflight without authoring a skill. APG4
accepted that environment finding while authoring six provisional APG v0.1
skill sources under an explicit maturity, rollback, and Superpowers coexistence
model. APG4A later added the checked-in Codex repository discovery projection
without changing the canonical skill content. APG5 and APG6 then recorded
successful use in APG and RepoMap. APG7 adds a tested, opt-in project-local
projection command and a human Superpowers decommission and rollback runbook;
APG7A corrects its idempotent compliance check. APG8 records the command's
first real-project managed adoption and check while preserving RepoMap's
tracked repository.

All six APG v0.1 skills are `provisional`. Their structural checks, public-safe
scenario walkthroughs, and independent reviews establish bounded behavior in
the recorded examples, not clean comparative superiority, production readiness,
or stable maturity. Discovery projection and projection-tool success do not
establish automatic invocation. Superpowers remains installed globally and is
reference evidence only for this repository; decommission readiness is false.

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
- [`docs/provenance.md`](docs/provenance.md) defines public and
  publication-excluded provenance responsibilities.
- [`docs/manager-worker-protocol.md`](docs/manager-worker-protocol.md) defines
  external authority, top-level management, internal delegation, evidence, and
  final reporting.
- [`docs/adr/`](docs/adr/README.md) records durable architecture decisions under
  an independent four-digit sequence.
- [`docs/status/`](docs/status/README.md) records truthful phase exits under an
  independent five-digit sequence.
- [`skills/`](skills/README.md) contains and indexes the six canonical
  provisional APG v0.1 skill sources.
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
- [`docs/superpowers-decommission-runbook.md`](docs/superpowers-decommission-runbook.md)
  records the human-owned future decommission and restoration sequence without
  authorizing plugin mutation.
- [`docs/evaluations/`](docs/evaluations/apg4-bootstrap-v0.1.md) records the
  public-safe APG4 scenario and review summary; the APG3 blocked record remains
  preserved separately.
- [`docs/roadmap.md`](docs/roadmap.md) records completed and closed phases,
  external review boundaries, and unnumbered candidate themes.
- `bin/` and `libexec/` contain the deterministic reporting tools and the
  dependency-free project-local APG projection command with non-executable
  helpers.

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

## Publication model

The canonical public identity is `agentic-praxis-grimoire`. Future public
releases may be filtered projections with squashed history. Publishable files
must be understandable on their own and must not expose or depend on excluded
development evidence. APG1 established that contract but did not create or
publish a public repository.

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
[manager-worker protocol](docs/manager-worker-protocol.md). APG3's blocked
experiment, APG4's bootstrap decision, APG4A's discovery correction, APG5 and
APG6 dogfooding, APG7 and APG7A's project-local deployment boundary, and APG8's
managed RepoMap adoption are described in the [roadmap](docs/roadmap.md).
