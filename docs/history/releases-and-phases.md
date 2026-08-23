# APG Development Releases and Phases

This document preserves the former root README chronology as development
archaeology. It records historical phase dispositions and release narrative;
it is not the current onboarding or product-status owner. Start with the
[human documentation index](../README.md), the
[current roadmap](../v0-7-roadmap.md), or the
[status index](../status/README.md).

# Former root README chronology

Agentic Praxis Grimoire (APG) is a modular engineering operating
model for coding agents. It curates practices that improve planning,
implementation, testing, debugging, review, delivery, and coordination without
turning one source methodology into a universal workflow.

Public APG v0.4.0 contains twenty-eight skills, projection and reporting
components, source-specific release and user-lifecycle validation, governance,
and licensing terms. Fourteen catalog rows are stable and fourteen remain
provisional; release inclusion does not change maturity. v0.4.0 appends one
intentionally squashed release commit and an annotated tag to the preserved
v0.1.0 through v0.3.0 history. Its canonical public
checkout supplies the maintainer's separately managed user-global Codex
integration. Private development history remains distinct.

APG49 independently validates the APG48 matryer/is v1.4.1 candidate but does
not retain it: fresh review after the single correction pass finds new
material source, trigger, structural, and scenario-continuity defects. ADR
0030 is Rejected, ADR 0026 remains the controlling two-component no-stack Go
architecture, and development remains 28/28/28. See the
[APG49 evaluation](../evaluations/apg49-matryer-is-validation-and-integration.md).

APG59 independently validates and amends the APG58 CSS pilot, but corrected-
state review finds material executable-contract and removal defects after the
single correction pass. ADR 0035 is Rejected, all candidate surfaces are
removed, and development remains 28/28/28 with fourteen stable and fourteen
provisional rows. Corrected public and active v0.4.0 remain unchanged.

APG60 now freezes the rejected-evidence behavior before any re-authoring:
sixty structured CSS response cases, a deterministic reference evaluator, and
a generic candidate-removal model exercise every current owner and preserve
history. It authors no skill, leaves ADR 0036 unused, and grants no successor
authority.

APG0 through APG8 are the closed v0.1 development epic, with each historical
terminal outcome preserved, including APG3's blocked result. The epic established
the project, bootstrap maturity model, six skills, repository discovery,
dogfooding, project-local projection and rollback, and RepoMap managed adoption.
The maintainer subsequently decommissioned Superpowers, and a bounded fresh
RepoMap smoke passed after decommission. APG9 closes that epic, reconciles
current state, and accepts the APG10 through APG14 v0.2 roadmap in
[ADR 0006](../adr/2026/07/0006-v0-2-objectives-roadmap-and-maturity-promotion.md).

APG10 accepts that closeout, resolves the experimental guideline source's
provenance and reuse boundary, and records its final dispositions in
[ADR 0007](../adr/2026/07/0007-experimental-karpathy-guidelines-disposition.md).
Frozen scenarios found current assumption, alternative, traceability, and
speculative-scope behavior adequate. They demonstrated one narrow gap for
locally owned code or test artifacts made unnecessary by the authorized change,
which received one independently reviewed implementation-discipline correction.
No seventh skill or maturity change was introduced.

APG11 accepts
[ADR 0008](../adr/2026/07/0008-skill-authoring-maintenance-and-mechanical-validation.md),
establishes the [skill authoring and maintenance guide](../skill-authoring-and-maintenance.md),
adds a dependency-free read-only mechanical skill-library checker, and closes the
former candidate-theme queue through the
[legacy roadmap ledger](../legacy-roadmap-closure.md). It changes no skill
leaf or maturity state. APG11A's accepted lexical correction then closes
required-key shadowing and fenced-code false negatives without changing that
architecture.

APG12 accepts [ADR 0009](../adr/2026/07/0009-public-distribution-and-reproducible-release-validation.md),
adds an exact non-private [public surface policy](../../release/public-surface.json),
and supplies separate dependency-free commands for reproducible local public
candidates and state-owned user-scope skill links. Its executable regression
detects the public v0.1.0 omitted-wrapper class. Disposable candidate and user
lifecycle dogfood leave the public repository and active integration unchanged.
APG12A subsequently corrects public-lineage and read-only validation defects
without reopening that architecture.

APG13 accepts [ADR 0010](../adr/2026/07/0010-six-skill-post-superpowers-stability-dispositions.md)
after individual historical inventories, frozen current applications, complete
regression, and fresh non-author reviews. All six current catalog entries are
`stable`; every canonical leaf remains byte-identical to the APG12A baseline.
APG14 corrects two APG9 evidence labels without changing those dispositions,
publishes the exact non-private v0.2.0 projection, and fast-forwards the active
public-backed source without changing its integration ownership shape. Public
v0.1.0 remains historical and unchanged. Stability and publication do not
establish clean comparative superiority, production warranty, universal
applicability, or automatic invocation. Superpowers remains retired. The
maintainer subsequently completed the requested full Codex restart and
fresh-session discovery smoke and reported that it passed.

APG15's capability-oriented, synthesis-first v0.3 architecture is accepted in
[ADR 0011](../adr/2026/07/0011-v0-3-workflow-synthesis-and-modular-guidance-architecture.md).
APG16 adds one provisional public workflow router for ambiguous selection,
routing audit, and capability-health diagnosis. It routes to one smallest
sufficient stable process leaf or none; it is not a session bootstrap,
mandatory chain, action authority, or procedure owner. The maintainer's later
fresh-session observation closes its duplicate-name discovery request.

APG17 accepts
[ADR 0013](../adr/2026/07/0013-repository-guidance-synthesis-and-migration-dispositions.md)
and adds one provisional `synthesizing-repository-guidance` leaf. It classifies
mixed guidance into bounded owners, rights, privacy, migration, and rollback
dispositions before any rewrite. It does not author the resulting artifact,
mirror private sources, migrate root guidance, remove private skills, or grant
implementation authority. APG18 accepts
[ADR 0012](../adr/2026/07/0012-language-profile-contract-and-warning-levels.md),
adds the normative language-profile contract and one provisional
`python-language-profile`, and preserves the six-skill public v0.2 lifecycle.
APG19 accepts separate shell-language and test-harness ownership, adds
provisional Bash, Bats, and Zsh profiles, and defers ZUnit on current
source/runtime evidence.

APG19A accepts that substantive result and adopts semantic phase identity,
independent ADR and exit sequences, semantic durable references, and precommit
record finalization in
[ADR 0015](../adr/2026/07/0015-semantic-phase-identity-and-record-finalization.md).
Its focused audit corrects Bats test counting for the runner-supported comment
function form without changing thresholds, maturity, catalog shape, the
six-skill v0.2 lifecycle, or the APG23/APG24 smoke deferral.

APG20 truthfully defers independent Go and Ruby profile candidates after fresh
review identifies material semantic, measurement, source-license, and dogfood
defects beyond its correction allowance. APG20A accepts that defect ledger,
corrects the report-lock race exposed by APG20's retry, and retains corrected
Go and Ruby profiles as provisional development skills. APG21 accepts separate
Nix, PostgreSQL, and SQLite ownership under
[ADR 0016](../adr/2026/07/0016-nix-and-relational-engine-profile-ownership.md)
and retains PostgreSQL and SQLite as provisional profiles. Nix is
`deferred-material-defect` after its corrected candidate exposes a second
behavior-bearing contradiction. APG21A corrects that retained defect ledger,
retains Nix provisionally, and applies one bounded PostgreSQL false-escalation
correction. Private development now contains nineteen skills and projections:
six stable process skills and thirteen provisional v0.3 skills before APG23. The router map
contains eighteen routable non-router entries. No generic SQL owner,
root or private cutover, or v0.3 release is implemented.

APG22 records 35/35 matched read-only router, retained-profile, and guidance-
synthesis dogfood cases across APG, RepoMap, and public-safe synthetic
boundaries. It finds no behavior-bearing APG defect and proposes no APG root
reduction. The [guidance-migration proposal](../v0-3-guidance-migration-proposal.md)
keeps target-specific and private guidance with its current owner and requires
distribution, shadow, discovery, override, rollback, and target acceptance
before any later cutover. The [v0.3 release-scope ledger](../v0-3-release-scope-closure.md)
records APG22A's retained approved-roadmap manager-assignment owner and
APG22B's exact ZUnit v0.8.2 with Zsh 5.9.2 profile. The unsupported 5.3.1 pair
and every unverified range remain excluded. No cutover, decommission, public
release, active-integration change, or application smoke occurs.

APG22C subsequently corrects the ZUnit harness's selected user-startup
evidence. Matched positive, negative, and in-runner controls retain the exact
5.9.2 support boundary and the 5.3.1 unsupported result without changing a
skill, maturity row, catalog shape, public v0.2, or active integration.

APG23 completes the required fresh-session discovery and explicit-use smoke,
records independent maturity and release-inclusion decisions for all thirteen
v0.3 skills, and accepts all thirteen for v0.3. Eight rows are promoted to
stable and five remain provisional, producing fourteen stable and five
provisional development rows. Public v0.2, schemas, managed defaults, and the
active integration remain unchanged. APG24 is the only remaining v0.3 phase
and separately owns candidate construction and publication.

APG24 accepts
[ADR 0019](../adr/2026/07/0019-v0-3-release-distribution-and-variable-skill-set-lifecycle.md),
publishes all nineteen skills as v0.3.0, expands new project defaults and
source-specific user transitions while retaining schema version 1, and
fast-forwards the active public-backed source without changing its aggregate
link ownership. Public v0.2.0 remains unchanged. The personal same-name router
remains installed for a source-qualified fresh-session shadow; no root/private
cutover, router decommission, or successor phase is authorized.

APG24A records the maintainer-reported successful public-v0.3 fresh-session
shadow and the later personal-router decommission performed under separate
human authority. Focused verification confirms unchanged public and active
v0.3.0 state, nineteen aggregate skills, preserved personal transition targets,
and an exact private restoration source. v0.3 is terminal; APG24A changes only
documentation and publication-excluded evidence.

APG25 accepts [structured project defaults](../structured-project-phase-defaults.md),
[testing and coverage policy](../testing-and-coverage-policy.md), a
[Python-first reporting architecture](../agent-reporting-architecture.md),
[ChatGPT-manager topology](../chatgpt-manager-skill-topology.md), and the
[v0.4 roadmap](../v0-4-roadmap.md) through ADRs 0020-0022. One bounded
correction makes approved-roadmap assignments consume repository defaults and
state deviations rather than repeat ordinary procedure. No skill is added,
tool is converted, test is migrated, ChatGPT leaf is moved, personal skill is
changed, or release is begun.

APG26 adds provisional `pytest-test-profile` and
`converting-bash-scripts-to-python` private-development capabilities after
current-source calibration, sixty frozen scenario families, failing-first
focused tests, read-only report-tool dogfood, and fresh review. Development is
now 21 canonical skills, 21 catalog rows, 21 relative projections, 14 stable
rows, 7 provisional rows, and 20 routable non-router capabilities. Public and
active v0.3.0 remain unchanged at nineteen skills; no report tool is converted,
no `git-diff-report` is implemented, and no test is migrated.

APG26A records that APG26's formal-phase commit contains only its subject and
corrects forward without rewriting APG26. The dependency-free Python
`apg-check-phase-commit-message` command rejects that regression and validates
the required phase subject plus ordered `Scope`, `Result`, `Verification`, and
`Not run` sections before and after new APG formal-phase commits. No skill,
maturity, release, active integration, report executable, or report format
changes in APG26A.

APG27 accepts the design in
[ADR 0023](../adr/2026/07/0023-python-agent-report-formats-and-git-record-association.md)
and produces a partial, uncommitted standard-library `libexec/agent_report`
candidate. The Python
`git-show-report` preserves version-2 bytes on the characterized POSIX
platform, `git-diff-report` adds deterministic drift-checked uncommitted state
evidence through a private index, and `append-operational-report` enforces exact
same-report Git show/diff association. The phase stops partial before commit
because the development release checker does not retain immutable v0.3.0
policy as a historical surface and the Python profile retains a Red branch
signal. GitPython is not selected, the pytest migration remains deferred, and
the published and active v0.3.0 objects remain unchanged.

APG27A preserves that partial result, freezes immutable v0.3.0 policy
independently from the current development inventory, decomposes the Red path-
safety owner without changing diagnostics, and adopts the corrected report
core. Focused parity, safety, association, historical-release, and independent
review gates pass. APG27A does not begin the pytest migration or change public
or active v0.3.0.

APG28A subsequently adopts the corrected pytest migration after preserving
APG28's Partial result, and APG29 aligns the affected process owners with the
adopted structured-project and test defaults.

APG30 implements ADR 0022's first actor-qualified namespace. The new
provisional `chatgpt-manager-workflow` subrouter and the unchanged
`composing-approved-roadmap-assignments` leaf are canonical under
`skills/chatgpt/`, while both retain flat `.agents/skills/<name>` discovery
links. Development is 22/22/22 with fourteen stable and eight provisional
rows. The general map has nineteen ordinary non-ChatGPT leaves plus the
subrouter; the ChatGPT-local map has the one manager leaf. Public and active
v0.3.0 remain immutable at 19/19/19. Application discovery and every personal
skill transition remain behind APG31's mandatory restart gate.

APG31 passes that fresh-session topology gate and independently shadows three
personal hygiene capabilities against current APG and repository owners. The
personal docs-only capability is decommissioned after replacement,
restoration, and non-author review. Git-history scope reduction and RepoMap
phase-hygiene decommissioning remain deferred because their current private
routing boundaries cannot be corrected within APG31 authority. Development
remains 22/22/22, router maps remain exact, and public and active v0.3.0 remain
unchanged. A fresh-session post-transition discovery smoke is still required.

APG31A records that later smoke as passed while preserving APG31's historical
Partial result. It completes the two deferred dispositions:
`git-history-hygiene` is scope-reduced after generalized behavior returns to
APG and repository owners, and `repomap-phase-hygiene` is decommissioned after
generalized behavior returns to current RepoMap owners. APG development and
public/active v0.3.0 remain unchanged.

APG32 retains the provisional `minitest-test-profile` after current Minitest,
Ruby, and extracted mock calibration; thirty-six frozen trigger, non-trigger,
semantic, structural, and stop families; a failing-first mirrored contract; and
fresh non-author review. One bounded correction makes fixture alternatives and
Minitest-specific boundary effects explicit while preserving existing general,
Ruby, and repository owners. Development becomes 23/23/23 with fourteen stable
and nine provisional rows. The general map has twenty-one edges; the
ChatGPT-local map remains one edge. Public and active v0.3.0 remain immutable
at 19/19/19. No dependency, framework selection, readiness, smoke, release,
publication, or successor phase is included.

APG33 retains the provisional `dockerfile-profile` after current Dockerfile
frontend, BuildKit, Docker documentation, and OCI image-configuration
calibration; forty frozen trigger, non-trigger, semantic, structural, and stop
families; a failing-first mirrored contract; and fresh non-author review. The
profile owns Dockerfile-specific parser, stage, instruction, context, copy,
mount, cache, user, metadata, and platform judgment while preserving image,
dependency, runtime, release, and live-operation authority. Development becomes
24/24/24 with fourteen stable and ten provisional rows. The general map has
twenty-two edges; the ChatGPT-local map remains one edge. Public and active
v0.3.0 remain immutable at 19/19/19. No Docker build, container, daemon,
registry, readiness, smoke, release, or publication action is included.

APG34 retains the provisional `vagrantfile-profile` after current Vagrant
source and documentation, configuration-load, Ruby-compatibility, box,
provider, plugin, network, synced-folder, provisioner, trigger, and state
calibration; forty frozen trigger, non-trigger, semantic, structural, and stop
families; a failing-first mirrored contract; one bounded source-semantics and
machine-measurement correction; and fresh non-author review. The profile owns
Vagrantfile-specific configuration judgment while preserving provider, box,
plugin, host, network, filesystem, command, lifecycle, release, and
live-operation authority. Development becomes 25/25/25 with fourteen stable
and eleven provisional rows. The general map has twenty-three edges; the
ChatGPT-local map remains one edge. Public and active v0.3.0 remain immutable
at 19/19/19. No Vagrantfile evaluation, box or plugin mutation, provider
contact, machine lifecycle, readiness, smoke, release, or publication action
is included.

APG38 retains provisional `go-test-profile` and `go-cmp-test-profile` after
independent current-source review, 66 public-safe
scenario families, categorical corpus calibration, isolated Go 1.25.10
compatibility probes, and fresh corrected-state review. ADR 0026 accepts two
directly triggerable Go component owners without a stack owner.
`matryer-is-test-profile` and `nix-test-profile` are deferred and absent after
new post-correction attribution/false-escalation and FreeBSD sandbox-default
defects. Development becomes 27/27/27 with fourteen stable and thirteen
provisional rows. The general map has twenty-five edges; the
ChatGPT-local map remains one edge. Public and active v0.3.0 remain immutable
at 19/19/19. No Nix execution, target-repository test, readiness, smoke,
release, publication, deployment, or successor phase is included.

APG40 independently integrates the APG39 replacements. `nix-test-profile`
passes exact Nix 2.35.1 and pinned Nixpkgs/NixOS 26.05 source review, forty
corrected public-safe scenarios, source-only structural calibration, one
coherent correction cycle, and fresh non-author review, then begins
`provisional`. `matryer-is-test-profile` is `deferred-material-defect` after
corrected-state review finds its equality mechanism still inaccurate. ADR
0027 is Rejected; ADR 0026 remains Accepted and controlling; no
`go-testing-stack` exists. Development becomes 28/28/28 with fourteen stable
and fourteen provisional rows, twenty-six general-map entries, one
ChatGPT-local entry, and twenty-seven checked route edges. Public and active
v0.3.0 remain immutable at 19/19/19.

APG41 closes the v0.4 development surface with all fourteen provisional rows
retained and unpromoted. Cross-profile dogfood preserves direct owner
selection and no mandatory chain; one bounded correction makes the Minitest,
Dockerfile, and Vagrantfile removal descriptions candidate-independent. Two
disposable exact v0.4.0 candidates and isolated lifecycle smoke pass on the
current host. The terminal result is
`ready-for-publication-with-provisional-limitations`; it publishes and deploys
nothing, and it authorizes no successor phase. Public and active v0.3.0 remain
19/19/19.

## Authority

The human maintainer retains ultimate project, roadmap, publication, license,
and destructive-action authority. ChatGPT manages planning and review only
within a human-authorized task, phase, or preapproved roadmap envelope.
Top-level Codex executes bounded ChatGPT assignments and manages internal Codex
workers. Evidence and recommendations do not expand any actor's authority. The
[manager-worker protocol](../manager-worker-protocol.md) defines the complete
chain and stop boundaries.

## Intended audience

APG is for maintainers who design agent workflows, agents that implement or
review those workflows, and contributors evaluating whether a practice improves
correctness, safety, maintainability, or delivery outcomes at an acceptable
cost.

## Project structure

- [`AGENTS.md`](../../AGENTS.md) contains the small set of repository-wide rules that
  should apply to nearly all work.
- [`docs/project-model.md`](../project-model.md) defines artifact ownership,
  evidence domains, and the candidate-to-adoption lifecycle.
- [`docs/skill-authoring-and-maintenance.md`](../skill-authoring-and-maintenance.md)
  owns the APG skill-specific authoring, correction, support, maturity,
  deprecation, and removal procedure.
- [`docs/provenance.md`](../provenance.md) defines public and
  publication-excluded provenance responsibilities.
- [`docs/manager-worker-protocol.md`](../manager-worker-protocol.md) defines
  external authority, top-level management, internal delegation, evidence, and
  final reporting.
- [`docs/structured-project-phase-defaults.md`](../structured-project-phase-defaults.md)
  defines formal and non-phase commit, status, ADR, docs-only, scoped-test, and
  manager-assignment compression defaults.
- [`docs/testing-and-coverage-policy.md`](../testing-and-coverage-policy.md)
  defines scoped tests, coverage remediation, mock boundaries, and the adopted
  APG pytest architecture.
- [`docs/agent-reporting-architecture.md`](../agent-reporting-architecture.md)
  defines the Python-first Git-show, Git-diff, and operational-report
  ownership and format boundaries.
- [`docs/chatgpt-manager-skill-topology.md`](../chatgpt-manager-skill-topology.md)
  defines implemented nested ChatGPT canonical owners, flat discovery,
  subrouting, and personal transition gates.
- [`docs/adr/`](../adr/README.md) records durable architecture decisions under
  an independent four-digit sequence.
- [`docs/status/`](../status/README.md) records truthful phase exits under an
  independent five-digit sequence.
- [`skills/`](../../skills/README.md) contains and indexes thirty-nine canonical skills:
  fourteen stable rows and twenty-five provisional manager-assignment,
  language, database, test-profile, or conversion rows.
- [`.agents/skills/`](../../.agents/skills/) is the checked-in Codex repository
  discovery projection; its thirty-nine relative symbolic links contain no
  independent skill content.
- [`docs/bootstrap-v0.1.md`](../bootstrap-v0.1.md) defines maturity,
  provisional evidence, rollback, dogfooding, and decommission gates.
- [`docs/superpowers-transition.md`](../superpowers-transition.md) maps
  materially relevant Superpowers workflows to APG, native Codex, project
  policy, deferral, or rejection.
- [`docs/project-skill-projection.md`](../project-skill-projection.md)
  documents opt-in cross-repository installation, adoption, verification, and
  rollback.
- [`docs/public-release-process.md`](../public-release-process.md) documents
  exact projection, deterministic candidate construction, validation, and the
  v0.2.0 and v0.3.0 publication records.
- [`docs/user-scoped-skill-integration.md`](../user-scoped-skill-integration.md)
  documents direct public-sourced user links, state, lifecycle, restart, and
  migration boundaries.
- [`docs/superpowers-decommission-runbook.md`](../superpowers-decommission-runbook.md)
  preserves the human-owned decommission and rollback sequence after the
  completed operation without authorizing restoration.
- [`docs/evaluations/`](../evaluations/apg4-bootstrap-v0.1.md) records the
  public-safe APG4 scenario and review summary; the APG3 blocked record remains
  preserved separately, and the
  [APG10 evaluation](../evaluations/apg10-karpathy-guidelines-evaluation.md)
  records the experimental-source dispositions.
- [`docs/roadmap.md`](../roadmap.md) records the closed v0.1 and v0.2
  sequences, the completed v0.3 sequence, APG25's v0.4 foundation, APG26's
  initial enabling capabilities, and APG26A's formal-commit correction. The
  [detailed v0.4 roadmap](../v0-4-roadmap.md) owns the dependency-ordered
  future slices without allocating phase IDs.
- [`docs/legacy-roadmap-closure.md`](../legacy-roadmap-closure.md) gives every
  former candidate or deferred theme a terminal owner or condition.
- `bin/` and `libexec/` contain deterministic reporting and change-size tools,
  the dependency-free project-local, user-scoped, and flat shared-skill
  projection commands, the
  read-only skill-library, record-identity, and formal-phase commit-message
  checkers, and the local-only public candidate builder/checker with
  non-executable helpers.
- `src/test/unit/python/agentic-praxis-grimoire/` and
  `src/test/int/python/agentic-praxis-grimoire/` mirror production owners for
  isolated unit tests and real-boundary integration tests. Test filenames use
  `.unit.test.py` or `.int.test.py` suffixes.

## Testing

The repository separates tests by level and implementation language:

```text
src/test/unit/<language>/
src/test/int/<language>/
```

APG28A adopts the corrected pytest migration. The repository interfaces are:

```sh
bin/apg-test unit
bin/apg-test integration
bin/apg-test unit-integration
```

Each command defaults to eight xdist workers. The strict source and mirror
inventory is recorded in `testing/apg-test-inventory.json`; exact integer
statement and branch counts enforce 80/80 component and 85/85 union gates.
Run-scoped manifests account for xdist workers, collection, terminal results,
and required Python-child coverage. Both report-tool Bats files remain.

Validate the current canonical skill library and checked-in Codex projection
without mutation:

```sh
bin/apg-check-skill-library [--root <path>] [--format text|json]
bin/apg-check-record-identity [--root <path>] [--format text|json] \
  [--expect-available <phase>] [--expect-allocated <phase>]
bin/apg-check-phase-commit-message --phase <PHASE-ID> \
  (--message-file <path> | --commit <revision>) [--format text|json]
bin/apg-check-change-size staged [--format text|json]
bin/apg-check-change-size commit <commit> [--format text|json]
bin/apg-check-change-size tree [<commit>] [--format text|json]
```

These commands validate only their adopted mechanical APG subsets. They do not
prove semantic quality, imperative mood, authority, privacy, provenance,
client discovery, maturity, release completeness, record truth, or stable
behavior.

The adopted Python reporting interfaces are:

```text
bin/git-show-report <phase-id> <commit> <status-doc> <result> <final-gate>
bin/git-diff-report <phase-id> <result> <final-gate> [--status-doc <path>]
bin/append-operational-report <phase-id> <absolute-body-path> <result> <final-gate> [options]
```

The three compatibility report commands and canonical `apgr report` routes
default to one current primary under
`~/Documents/agent/outbox/<project>/<phase>/<phase>.<kind>.report.txt`.
`GIT_SHOW_REPORT_ROOT` remains an explicit legacy-omnibus override for the
compatibility commands, but cannot redirect canonical `apgr report` routes;
historical reports under the earlier default are not migrated.
`apgr report recover --phase <phase>` provides bounded interrupted-transaction
recovery; repository-backed writes reject an explicit project identifier that
does not match the repository basename.

`bin/flatten-skill-symlinks INPUT OUTPUT` creates a flat, owner-state-backed
symlink projection from nested skill roots. It supports deterministic
collision handling, `--dry-run`, `--check`, state-owned `--replace` and
`--clean`, and refuses overlap, symlinked output ancestry, unmanaged
collisions, and indirect marker files. APG53 did not mutate a live Claude
installation.

`bin/install-global-skills AGENT [REPOSITORY ...]` projects one complete set of
local skill repositories into a Codex or Claude personal skill root. With no
repository arguments it uses the installed APG repository. Explicit
repositories replace that default; `--include-apg` adds APG to an explicit
set. Codex defaults to `$HOME/.agents/skills`, Claude defaults to
`${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills`, and `--skills-root` overrides
the destination exactly. Duplicate names, unmanaged collisions, and other
command owners fail closed. `--check`, `--dry-run`, and exact owned
`--uninstall` are supported. This is local symlink projection, not package,
plugin, trust, release, or runtime-discovery validation.

`bin/apg-check-change-size` reads index, commit, or tree Git objects. The
versioned policy in `testing/apg-change-size-policy.json` limits ordinary
blobs to 256 KiB, generated-derived evidence blobs to 128 KiB, generated
evidence added per change to 512 KiB, and text lines to 64 KiB. Archives are
rejected by default and binary assets require exact identity-bound exceptions.

On Windows invoke the entry point through an interpreter, for example
`python bin/git-diff-report --help`. Report replacement fails closed there
until native sharing, reparse, and replacement safety is characterized. A Git
record must exist before its associated operational append. Standalone
operational records are accepted only when the canonical phase report contains
no Git show or diff record.

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
[skill authoring and maintenance guide](../skill-authoring-and-maintenance.md)
owns its proportional application to skill changes.

## Publication model

The canonical public identity is `agentic-praxis-grimoire`. Public v0.1.0 was
published as a filtered projection with one intentionally squashed commit and
historically omitted the documented `bin/apg-project-skills` wrapper. ADR 0009
replaces manual selection with an exact projection of every tracked path except
`private/`, plus critical-owner checks that detect deletion from source.
Public v0.2.0, v0.3.0, and v0.4.0 each append one deterministic squashed
release commit and annotated tag while preserving the preceding public release
as sole parent. v0.4.0 publishes twenty-eight skill owners with fourteen stable
and fourteen provisional rows, then advances the aggregate-owned active source
by exact fast-forward. Future publication remains a separately authorized
human decision.

## License

Agentic Praxis Grimoire is licensed under the GNU Affero General Public License
v3.0 or later. See [LICENSE](../../LICENSE).

Commercial licenses are available for proprietary terms, including
closed-source embedding, private service deployments, OEM use, support,
warranty, indemnity, and custom commercial terms. See
[COMMERCIAL-LICENSE.md](../../COMMERCIAL-LICENSE.md).

Contributions are accepted under the terms in
[CONTRIBUTING.md](../../CONTRIBUTING.md) and [CLA.md](../../CLA.md).

## Where to begin

Agents should read [`AGENTS.md`](../../AGENTS.md), then the focused owner for the task.
Maintainers evaluating source-derived policy should begin with the
[project model](../project-model.md), [provenance policy](../provenance.md),
and the [ADR index](../adr/README.md). The reviewed but rejected Web and Node
candidate boundaries and non-normative growth evidence are summarized in the
[Web and Node profile-family architecture](../architecture/web-and-node-profile-family.md).
Its repaired reproducibility foundation and named insufficient evidence
classes are recorded in the
[APG52 evaluation](../evaluations/apg52-reproducible-web-node-evidence-foundation.md);
that evidence accepts no threshold or profile.
A later fresh reconstruction on that foundation produced
[ADR 0034](../adr/2026/07/0034-web-and-node-profile-family-reconstruction-and-authoring-sequence.md)
with separate owner, authoring, and growth-band decisions; see the
[APG56 evaluation](../evaluations/apg56-web-and-node-architecture-reconstruction.md)
and the
[reconstruction architecture document](../architecture/web-and-node-profile-family-reconstruction.md).
The [APG57 independent review](../evaluations/apg57-web-and-node-architecture-review.md)
rejects ADR 0034 after material corrected-state defects, leaves every numeric
band and all authoring deferred, and changes no skill surface.
The [APG58 CSS pilot](../evaluations/apg58-css-language-profile-pilot-authoring.md)
authors one unintegrated `css-language-profile` candidate under explicit
policy-selected structural limits. The
[APG59 independent validation](../evaluations/apg59-css-language-profile-validation-and-integration.md)
closes projected/resulting-count and incremental-growth loopholes and narrows
authority and semantic boundaries, but corrected-state review finds material
verification and removal defects. It rejects
[ADR 0035](../adr/2026/07/0035-css-language-profile-and-policy-selected-structural-limits.md)
and removes the candidate from current development.
The
[APG60 foundation](../evaluations/apg60-css-reentry-contract-and-removal-foundation.md)
then freezes sixty candidate-independent response cases and a complete
retained/rejected removal-closure model before any future author may write
candidate prose. It creates no CSS surface and does not authorize APG61.
The current multi-repository installer and its forward transaction hardening
are recorded in the
[APG54 integration](../evaluations/apg54-global-skill-installer-integration.md)
and
[APG55 correction](../evaluations/apg55-global-skill-installer-transaction-hardening.md).
Delegated work should follow the
[manager-worker protocol](../manager-worker-protocol.md). The completed v0.1
epic, post-release APG-TEST0 foundation, and completed APG10 through APG14 v0.2
sequence are described in the [roadmap](../roadmap.md). No successor roadmap
epic begins automatically.
## APG60A CSS foundation correction

APG60A corrects the APG60 pre-authoring oracle forward without restoring the
rejected CSS candidate. Projection overruns are operation-independent,
artifact exceptions retain their real authority source, broken symlink
residue is lexical, and later retained integration must pass an actual-tree
closure gate. The 60-case register and 300/600/900 policy are unchanged.

See
[APG60A CSS Contract Foundation Hardening](../evaluations/apg60a-css-contract-foundation-hardening.md).
APG61 remains recommended, not authorized.

## APG60B traceability and decision closure

[APG60B](../evaluations/apg60b-css-traceability-and-decision-closure.md)
closes five additional pre-authoring false-pass classes without changing the
accepted CSS behavior contract. Future contract maps must agree exactly with
all sixty cases and reachable clause anchors; narrative state, Python owner
variables, derived release values, and ADR 0036 lifecycle state are checked
against their real owners. No CSS candidate or ADR 0036 is created, and no
successor is authorized.

## APG60C runtime and terminal lifecycle closure

[APG60C](../evaluations/apg60c-css-runtime-and-terminal-lifecycle-closure.md)
preserves accepted APG60B and records the owner-source finality claim later
narrowed forward by APG60D. APG60C keeps exact marker state separate
from bounded prose diagnostics, positively gates the authored Proposed but
unintegrated state, requires preserved history for terminal rejection, and
rejects symlinked or malformed current survivor owners. The sixty-case behavior
contract and 28/28/28 development state remain unchanged; APG61 is recommended
only and is not begun or authorized.

## APG60D source-binding and phase-history closure

[APG60D](../evaluations/apg60d-css-source-binding-and-history-closure.md)
preserves accepted APG60C while replacing its overstrong runtime/call claim
with truthful static source-binding integrity. Exact APG58 through APG60D
foundation bundles are mandatory; authored state requires APG61, and retained
or rejected state requires APG61 plus APG62. All repository history is exact,
direct regular, nonempty UTF-8, and no-follow. The CSS contract and 28/28/28
development state remain unchanged. APG61 uses future exit 00085, is
recommended only, and is not begun or authorized.

## APG60E repository-path and candidate-surface closure

[APG60E](../evaluations/apg60e-css-repository-path-and-candidate-surface-closure.md)
preserves accepted APG60D and closes lifecycle authority, authored-owner, and
retained-owner ancestor-symlink false passes through one physical-root,
descriptor-relative no-follow read contract. The expected projection remains
an exact relative symlink whose parent and canonical target provenance are now
closed. The CSS behavior contract and 28/28/28 development state remain
unchanged. APG61 uses future exit 00086, is recommended only, and is not begun
or authorized.

## APG60F import, owner, and projection closure

[APG60F](../evaluations/apg60f-css-import-owner-and-projection-closure.md)
preserves accepted APG60E while closing repository-local transitive import and
cache isolation, making all 52 lifecycle roles and cross-references exact, and
revalidating the expected projection and canonical target as one bounded
observation. APG58 through APG60F are the foundation. CSS remains absent, ADR
0036 remains unused, and development, public, and active state remain
unchanged. APG61 uses exit 00087, remains recommended only, and is not begun
or authorized.

## APG60G snapshot, role, and derived-set closure

[APG60G](../evaluations/apg60g-css-snapshot-role-and-derived-set-closure.md)
preserves accepted APG60F while binding dynamic consumers to one pinned
repository object, comparing complete exact derived skill sets, freezing the
52 required semantic roles in a code-owned registry, and making authoritative
regular reads observe the same final repository entry before and after the
read. APG58 through APG60G are now the foundation. CSS remains absent, ADR
0035 remains Rejected, ADR 0036 remains unused, and development, public, and
active state remain unchanged. APG61 uses exit 00088 and APG62 uses 00089;
APG61 remains recommended only and is not begun or authorized.

## APG60H snapshot and full-path binding closure

[APG60H](../evaluations/apg60h-css-snapshot-and-full-path-binding-closure.md)
preserves the immutable Claude object and completes worker scratch, exact
snapshot, full-path presence and absence, final root binding, and projection
identity verification. APG58 through APG60H are foundation; future exits are
00089 and 00090. Candidate, public, active, target, and successor state remain
unchanged.

## APG60I worker temporary-root binding and cleanup closure

[APG60I](../evaluations/apg60i-worker-temp-binding-and-cleanup-closure.md)
preserves APG60H's adopted-with-exceptions history and corrects its two known
worker temporary-storage defects forward. Child creation is bound to an
already-opened no-follow root and cleanup owns the lifecycle before creation.
APG58 through APG60I are foundation; future exits are 00090 and 00091. CSS,
ADR 0036, public, active, target, and successor state remain unchanged.

## APG61 CSS language-profile authoring

[APG61](../evaluations/apg61-css-language-profile-authoring-from-frozen-contract.md)
authors one fresh `css-language-profile` candidate from the frozen APG60A
contract on the preserved Claude authoring branch — leaf, specification, and
sixty-case traceability map — and proposes
[ADR 0036](../adr/2026/07/0036-css-language-profile-from-frozen-contract.md).
The candidate is not integrated: current candidate-state markers remain
absent, integrated counts remain 28/28/28, development `main` remains at
exact APG60I, and public, active, and target state are unchanged. APG62
validation at exit 00091 is recommended but separately authorized.

## APG62 CSS language-profile validation and rejection

[APG62](../evaluations/apg62-css-language-profile-validation-and-integration.md)
independently reconstructs the frozen sixty-case oracle and validates the
exact delivered APG61 candidate. Seven initial semantic-navigation defects
receive the one permitted coherent correction; fresh corrected-state review
then finds a new material six-case `record-growth-state` overreach. ADR 0036
is therefore Rejected and all current candidate surfaces are removed.
Development remains 28/28/28 with 14 stable / 14 provisional, current markers
remain absent, APG61 history is preserved, and public, active, and target state
is unchanged. No successor is authorized.

## APG63 Markdown architecture and lean contract

[APG63](../evaluations/apg63-markdown-language-profile-architecture.md)
moves to Markdown after the terminal CSS rejection without retrying
`css-language-profile`. From exact APG62 it reverifies CommonMark 0.31.2,
the pinned GFM specification, CC BY-SA 4.0 document rights, and the seven
target Markdown documents; defines a narrowed coherent Markdown owner with
closed raw-HTML, frontmatter, and MDX/host boundaries; selects qualitative
structure-first structural policy (no numeric whole-file bands) under ten
pre-frozen purpose controls; freezes a lean thirty-six-scenario
candidate-independent contract; and proposes
[ADR 0037](../adr/2026/07/0037-markdown-language-profile-architecture-and-lean-validation.md).
No skill is authored and nothing is integrated: development remains
28/28/28 with 14 stable / 14 provisional, ADR 0036 stays Rejected, and
public, active, and target state are unchanged. Codex peer review
(recommended APG64) terminally decides ADR 0037 and is separately
authorized.

## APG64 Markdown architecture peer review

[APG64](../evaluations/apg64-markdown-architecture-peer-review.md)
delivers and independently reviews exact APG63. It reproduces seven material
architecture defects, applies one coherent forward correction, preserves
exact corrected-state evidence, and accepts
[ADR 0037](../adr/2026/07/0037-markdown-language-profile-architecture-and-lean-validation.md)
with amendment after fresh 36/36 replay and source/target review. The accepted
architecture remains authoring-eligible-with-narrowing, but no Markdown skill
is authored or integrated. Development remains 28/28/28 with 14 stable / 14
provisional; CSS stays absent; public, active, and target state is unchanged;
and no successor is authorized.

## APG65 Markdown language-profile candidate authoring

[APG65](../evaluations/apg65-markdown-language-profile-authoring.md)
authors one fresh branch-only `markdown-language-profile` candidate from the
accepted
[ADR 0037](../adr/2026/07/0037-markdown-language-profile-architecture-and-lean-validation.md)
architecture: leaf, candidate specification, and navigation-only
scenario-coverage record, with
[ADR 0038](../adr/2026/07/0038-markdown-language-profile-candidate.md)
Proposed. The candidate is branch-only, Proposed, unintegrated, and pending
separately authorized APG66 validation; it contains no numeric whole-file
band and creates no current integration owner. Integrated development
remains 28/28/28 with 14 stable / 14 provisional; CSS stays absent; public,
active, and target state is unchanged; and no successor is authorized.

## APG66 Markdown language-profile validation and integration

[APG66](../evaluations/apg66-markdown-language-profile-validation-and-integration.md)
delivers exact APG65, independently replays the accepted 34-scenario oracle,
freezes one coherent correction before fresh non-author review, and accepts
[ADR 0038](../adr/2026/07/0038-markdown-language-profile-candidate.md) with
amendment. The profile is retained provisionally with every current owner:
development is 29/29/29, 14 stable / 15 provisional, with 27 general routes,
one ChatGPT-local route, and 28 checked edges. ADR 0037 and APG65 authorship
are preserved. Public and active corrected v0.4.0 and the read-only targets
remain unchanged; no readiness, publication, deployment, APG67, or successor
begins.

## APG67 JavaScript language-profile architecture

[APG67](../evaluations/apg67-javascript-language-profile-architecture.md)
proposes the JavaScript language-profile architecture and
candidate-independent lean validation contract under
[ADR 0039](../adr/2026/08/0039-javascript-language-profile-architecture-and-lean-validation.md)
(Proposed): the exact ECMAScript 2026 annual source is the stable
reference, JavaScript, TypeScript, and Node.js remain separate owners,
structural policy is qualitative with no numeric whole-file bands, and a
frozen forty-row register binds future authoring and review. No JavaScript
skill exists; development remains 29/29/29 with 14 stable / 15 provisional
and 27/1/28 routes; Markdown remains retained provisional; corrected
public and active v0.4.0 and the read-only targets are unchanged. APG68 is
recommended but not begun.

## APG68 JavaScript architecture peer review

[APG68](../evaluations/apg68-javascript-architecture-peer-review.md)
normally delivers and preserves exact APG67, independently reconstructs and
replays the JavaScript architecture, and applies one coherent correction.
[ADR 0039](../adr/2026/08/0039-javascript-language-profile-architecture-and-lean-validation.md)
is Rejected after fresh review finds material defects in the sole corrected
state; eligibility is `not-applicable-rejected`. No JavaScript skill is
authored or integrated; development remains 29/29/29, 14/15, and 27/1/28.
APG69 is not recommended or begun.

## APG69 JavaScript core architecture reset

[APG69](../evaluations/apg69-javascript-core-layered-architecture.md)
exercises new human authority to propose
[ADR 0040](../adr/2026/08/0040-javascript-language-profile-core-and-layered-decision-model.md)
(Proposed): a narrower ECMAScript-core owner with question-specific
typed authorities, a four-layer semantic/structural/policy/effective
decision model with an ordered effective route union, and independent
semantic, structural, composition, and process registers. ADR 0039
remains Rejected and unchanged; no JavaScript skill is authored or
integrated; development remains 29/29/29, 14/15, and 27/1/28.
Separately authorized APG70 terminally decides ADR 0040.

## APG70 JavaScript core layered-architecture peer review

[APG70](../evaluations/apg70-javascript-core-layered-architecture-peer-review.md)
normally delivers exact APG69, independently reproduces the initial material
defects, applies one coherent correction, and preserves its actual patch.
Fresh non-author review then finds new material source-identity,
signal-predicate, context-route, policy-typing, checker, and owner-binding
defects. [ADR 0040](../adr/2026/08/0040-javascript-language-profile-core-and-layered-decision-model.md)
is Rejected; eligibility is `not-applicable-rejected`; no current JavaScript
architecture input, skill, or integration owner exists. Development remains
29/29/29, 14/15, and 27/1/28. APG71 is not recommended or begun.

## APG71 TypeScript architecture and compiler-generation boundary

[APG71](../evaluations/apg71-typescript-language-profile-architecture.md),
under separate new human authority for TypeScript architecture only,
proposes
[ADR 0041](../adr/2026/08/0041-typescript-language-profile-architecture-and-compiler-generation-boundary.md)
(Proposed): a narrow TypeScript static-semantics owner under
project-selected exact compiler authority, a first-class TypeScript 6/7
compiler-generation boundary, closed source-kind and embedded-host
boundaries, structural disposition D, and eligibility
`authoring-eligible-with-narrowing` with no candidate-authoring authority.
ADR 0039 and ADR 0040 remain Rejected; no TypeScript skill or integration
owner exists; development remains 29/29/29, 14/15, and 27/1/28. Separately
authorized APG72 terminally decides ADR 0041.

## APG72 TypeScript architecture peer review

[APG72](../evaluations/apg72-typescript-architecture-peer-review.md)
preserves exact APG71, independently rebuilds the oracle, freezes the complete
initial set, and applies one coherent correction. Two fresh non-author lanes
find new material owner/route, role-state, source-kind, and evidence-state
defects. ADR 0041 is Rejected; eligibility is `not-applicable-rejected`; no
current TypeScript architecture input or skill exists. Development remains
29/29/29, 14/15, and 27/1/28. APG73 is not recommended or begun.

## APG73 language-profile production recovery charter

[APG73](../evaluations/apg73-language-profile-production-recovery-charter.md)
records new human product authority and accepts
[ADR 0042](../adr/2026/08/0042-language-profile-production-recovery-and-iterative-hardening.md).
The controlling
[production recovery charter](../governance/language-profile-production-recovery-charter.md)
and [iterative hardening contract](../specs/language-profile-iterative-hardening-contract.md)
replace automatic rejection after one correction with up to three separately
evidenced hardening rounds by default. Critical and High defects still block
integration; explicit human acceptance is required for Medium or Low debt and
for terminal rejection or removal. TypeScript is essential, CSS and JavaScript
are desirable, JSX is deferred, TypeScript 7 is the intended primary
generation, and temporary TypeScript 6 is permitted only for an exact required
role. No profile is authored or integrated. Development stays 29/29/29,
14/15, and 27/1/28; Markdown, rejected ADRs, public/active v0.4.0, and targets
remain unchanged. APG74 is recommended but not begun.

## APG74 TypeScript language-profile candidate

[APG74](../evaluations/apg74-typescript-language-profile-candidate.md)
authors the first ADR 0042 product-recovery candidate: the
[TypeScript language-profile leaf](../../skills/typescript-language-profile/SKILL.md),
its [candidate specification](../specs/typescript-language-profile.md) and
[scenario coverage](../specs/typescript-language-profile-scenario-coverage.md),
and the
[TypeScript 7 intended-state fixture](../../src/test/fixtures/apg74-typescript-intended-state/README.md),
proposing
[ADR 0043](../adr/2026/08/0043-typescript-language-profile-candidate-and-intended-state-harness.md).
The exact stable compiler is freshly selected (`typescript@7.0.2`); the
TypeScript 6 compatibility disposition is `not-required` with a recorded
refresh condition; and the freshly pinned targets show the live theme
checking under `typescript@5.9.3` — migration baseline, not the
destination. The candidate is authored-proposed-unintegrated: the APG74
branch carries a transitional 30/29/29 shape while integrated development
remains exact APG73 at 29/29/29, 14/15, and 27/1/28. Markdown, rejected
ADRs, public/active v0.4.0, and targets remain unchanged. APG75 owns
iterative hardening and the terminal ADR 0043 decision; it is recommended
but not begun.

## APG75 TypeScript iterative hardening and provisional integration

[APG75](../evaluations/apg75-typescript-iterative-hardening-and-integration.md)
normally delivers exact APG74, independently rebuilds its 24 semantic and 14
fixture vectors, and uses three separately preserved hardening rounds. The
final exact-TypeScript-7 suite passes 78 focused tests and fresh review finds
zero Critical, High, Medium, or Low defects. [ADR 0043](../adr/2026/08/0043-typescript-language-profile-candidate-and-intended-state-harness.md)
is Accepted with amendment and `typescript-language-profile` is retained
provisionally. Development is 30/30/30, 14/16, and 28/1/29. A disposable
rollback restores 29/29/29, 14/15, and 27/1/28 while preserving history,
decisions, Markdown, and corrected public and active v0.4.0. APG75 performs no
target mutation, readiness, publication, deployment, stable-maturity, APG76,
or successor work.

## APG75A TypeScript scope and lifecycle closure

[APG75A](../evaluations/apg75a-typescript-scope-and-lifecycle-closure.md)
closes five post-integration defects without rewriting APG74 or APG75. The
reusable profile is compiler-generation-neutral and consumes exact
project-selected evidence; Theme Forge Terminal Nova retains its separate
TypeScript 7 product destination. Response has exactly four values and remains
disjoint from Selection. Coverage, fixture, manifest, and parser lifecycle now
agree on provisional integration, and standard runners fail early unless exact
TypeScript 7.0.2 is explicitly bound. ADR 0043 remains Accepted with amendment;
development remains 30/30/30, 14/16, and 28/1/29; public/active corrected
v0.4.0 and targets are unchanged. APG76 is recommended but not begun.
## APG76 CSS language-profile candidate recovery

APG76 proposes ADR 0044 on the Claude authoring branch: one reusable CSS
semantics profile, one navigation-only twenty-four-scenario coverage record,
and one fourteen-case target-first fixture. CSS remains unintegrated, with no
catalog row, projection, maturity row, route, project selection, release owner,
or maintained test owner. TypeScript and Markdown remain retained provisional
and JavaScript remains absent. Published and active corrected v0.4.0 and both
read-only targets are unchanged and unexecuted. APG77 Codex CSS iterative
hardening is recommended but not begun.

## APG77 CSS iterative hardening repair checkpoint

[APG77](../evaluations/apg77-css-iterative-hardening-and-integration.md)
preserves three immutable correction rounds and the APG76 candidate. Fresh
terminal review finds two High retained-evidence defects, so
[ADR 0044](../adr/2026/08/0044-css-language-profile-candidate-and-target-first-harness.md)
remains Proposed and CSS remains unintegrated. Development stays 30/30/30,
14/16, and 28/1/29; public and active corrected v0.4.0 and both read-only
targets are unchanged. Further repair requires a human continuation decision.

## APG77A CSS evidence-retention repair checkpoint

[APG77A](../evaluations/apg77a-css-evidence-retention-closure-and-integration.md)
preserves the explicitly authorized target-identity and independent-vector
correction. Fresh review finds three High defects, including a wrong SVG
authority, false-pass H2 qualification, and copied target bytes. ADR 0044 stays
Proposed and CSS remains unintegrated at 30/30/30, 14/16, and 28/1/29. Main,
corrected public/active v0.4.0, and both targets are unchanged. APG78 is not
recommended; a new human decision is required.

## APG77B CSS traceability and clean-room repair checkpoint

[APG77B](../evaluations/apg77b-css-traceability-clean-room-closure-and-integration.md)
preserves the explicitly authorized H3-H5 correction. Fresh four-lane review
finds four High and two Medium defects in qualification, generated-report and
escaped-copy boundaries, immutable diff binding, and artifact proportionality.
No debt is accepted. ADR 0044 stays Proposed and CSS remains unintegrated at
30/30/30, 14/16, and 28/1/29. Main, corrected public/active v0.4.0, and both
targets are unchanged. APG78 is not recommended; a new human decision is
required.

## APG77C CSS evidence-proportionality repair checkpoint

[APG77C](../evaluations/apg77c-css-evidence-proportionality-and-integration.md)
preserves the human-authorized P1-P6 correction, makes exact private deletion
patches a narrow historical exception, and replaces exhaustive current prose
provenance with compact consequence-bearing evidence. Fresh review finds six
Medium and one Low unaccepted qualification defects. ADR 0044 stays Proposed
and CSS remains unintegrated at 30/30/30, 14/16, and 28/1/29. Main, corrected
public/active v0.4.0, provisional TypeScript and Markdown, and both targets are
unchanged. APG78 is not recommended; a new human decision is required.

## APG77D CSS known debt and provisional integration

[APG77D](../evaluations/apg77d-css-known-debt-and-provisional-integration.md)
records explicit human acceptance of exactly four Medium and one Low
qualification limitations, accepts no Critical/High or semantic/source/target/
runtime/release/rollback debt, and closes proportionality, live lifecycle,
release, historical-exclusion, and disposable-rollback gates. ADR 0044 is
Accepted with amendment and CSS is provisionally integrated with known debt at
31/31/31, 14/17, and 29/1/30. TypeScript and Markdown remain provisional;
public/active corrected v0.4.0 and both unexecuted targets remain unchanged.
APG78 is recommended but not begun.

## APG79 JavaScript repair checkpoint

[APG79](../evaluations/apg79-javascript-core-iterative-hardening-and-integration.md)
preserves three correction rounds and independently validates the APG78
candidate, fixture, exact engine, sources, rights, and target bindings. Terminal
review finds zero Critical, two High, two Medium, and zero Low material defects,
with no accepted JavaScript debt. ADR 0045 remains Proposed and JavaScript is
`repair-required-after-round-3` without integration. Development remains exact
APG77D at 31/31/31, 14/17, and 29/1/30; CSS known debt, provisional CSS,
TypeScript and Markdown, corrected public/active v0.4.0, and targets remain
unchanged. APG80 is not recommended; a human continuation decision is required.

## APG79A JavaScript terminal-proof repair checkpoint

[APG79A](../evaluations/apg79a-javascript-terminal-proof-closure-and-integration.md)
preserves one separately authorized immutable correction for APG79's four
terminal findings. Four fresh non-author lanes find five Medium material defects
and no Critical, High, or Low finding; no JavaScript debt is accepted. ADR 0045
remains Proposed and JavaScript is `repair-required-after-apg79a` without
integration. Development remains exact APG77D at 31/31/31, 14/17, and 29/1/30;
CSS known debt, provisional CSS/TypeScript/Markdown, corrected public/active
v0.4.0, and both targets remain unchanged. APG80 is not recommended and a new
human decision is required.


## APG79B JavaScript contract and harness repair checkpoint

[APG79B](../evaluations/apg79b-javascript-contract-harness-closure-and-integration.md)
preserves one separately authorized immutable correction for APG79A's five
Medium findings. Five fresh non-author lanes find four unique Medium material
defects and no Critical, High, or Low finding; no JavaScript debt is accepted.
ADR 0045 remains Proposed and JavaScript is `repair-required-after-apg79b`
without integration. Development remains exact APG77D at 31/31/31, 14/17, and
29/1/30; CSS debt, public/active corrected v0.4.0, and both targets remain
unchanged. APG80 is not recommended and a new human decision is required.

## APG79C JavaScript human-debt decision and integration checkpoint

[APG79C](../evaluations/apg79c-javascript-known-debt-and-provisional-integration.md)
accepts exactly four Medium JavaScript qualification limitations for
provisional use, with zero Critical or High and no semantic, source, target,
owner, release, or rollback debt accepted. A separate unaccepted Medium
Test262 identity discrepancy blocks integration. ADR 0045 remains Proposed and
JavaScript remains `repair-required-after-apg79b` and unintegrated. Development
stays exact APG77D at 31/31/31, 14/17, and 29/1/30; APG80 is not recommended.

## APG79E JavaScript report-binding debt and provisional integration

[APG79E](../evaluations/apg79e-javascript-report-binding-debt-and-provisional-integration.md)
accepts `JS-QD-005` as one additional Medium supporting qualification
limitation and directly verifies the current APG79B report rather than claiming
the maintained proxy is repaired. With zero Critical, High, or unaccepted
Medium/Low findings and every product gate green, ADR 0045 is Accepted with
amendment and JavaScript is provisionally integrated under exactly
`JS-QD-001` through `JS-QD-005`. Development is 32/32/32, 14/18, and 30/1/31.
Public and active corrected v0.4.0 and both read-only targets remain unchanged;
APG80 is recommended but not begun.
[APG80](../evaluations/apg80-nodejs-runtime-and-cli-stack-candidate.md)
authors a narrow reusable `nodejs-runtime-profile` candidate with a
twenty-four-scenario navigation record, a fourteen-case APG-owned target-first
fixture, and Proposed ADR 0046. The candidate consumes runtime roles rather than
selecting them, because fresh target evidence shows the exact Node version is
never resolvable from project evidence alone in either read-only target. Nothing
is integrated: mainline development remains 32/32/32, 14/18, and 30/1/31, known
debt remains exactly `CSS-QD-001` through `CSS-QD-005` and `JS-QD-001` through
`JS-QD-005`, and public and active corrected v0.4.0 and both targets are
unchanged. APG81 is recommended but not begun.

## APG81 Node.js hardening repair checkpoint

[APG81](../evaluations/apg81-nodejs-runtime-cli-iterative-hardening-and-integration.md)
preserves three immutable correction rounds and completes the required terminal
review. The final ledger is zero Critical, three High, two Medium, and zero Low;
no Node debt is accepted. ADR 0046 remains Proposed and
`nodejs-runtime-profile` remains branch-only,
`repair-required-after-round-3`, and unintegrated. Main remains exact APG79E at
32/32/32, 14/18, and 30/1/31; the candidate branch remains 33/32/32. Existing
CSS/JavaScript debt, corrected public/active v0.4.0, and both unexecuted targets
are unchanged. A new human continuation decision is required.

## APG81A Node.js threat-model correction checkpoint

[APG81A](../evaluations/apg81a-nodejs-qualification-threat-model-and-harness-simplification.md)
preserves a zero-finding correction that retires immutable-flag and copied-
runtime sealing claims in favor of a controlled local-or-CI qualification
contract with direct runtime pre/post observation. Terminal integration review
finds one High rollback defect and one Medium contradictory ADR-index lifecycle
defect in the proposed integration state, so those bytes are not retained. ADR
0046 remains Proposed, Node remains corrected, repair-required, and unintegrated
with zero Node debt, and main remains 32/32/32, 14/18, and 30/1/31. A new human
decision is required; no successor is authorized.

## APG81B Node.js integration-contract clarification checkpoint

[APG81B](../evaluations/apg81b-nodejs-integration-contract-clarification-and-provisional-adoption.md)
clarifies that candidate-preserving rollback targets 33/32/32. Review of the
complete reconstructed integration candidate finds three Medium defects and no
Critical, High, or Low finding, with zero Node debt. The candidate's rollback
lifecycle was contradictory, its pending review records contradicted its
proposed message, and one test-only xdist repair exceeded integration authority.
The attempted integration is discarded. ADR 0046 remains Proposed and Node
remains corrected, repair-required, and unintegrated at branch shape 33/32/32;
main remains 32/32/32, 14/18, and 30/1/31. A new human decision is required.

## APG81C Node.js lifecycle, test, and scratch repair checkpoint

[APG81C](../evaluations/apg81c-nodejs-lifecycle-test-and-scratch-closure.md)
retains the integration-support correction for rollback lifecycle, external
review sequencing, per-invocation xdist cleanup, and ignored machine-local
scratch. Fresh precommit review passes with zero findings and zero Node debt,
but immutable review finds one Medium contradiction in retained pending-review
prose. Integration stops. ADR 0046 remains Proposed, Node remains corrected,
repair-required, and unintegrated at 33/32/32, and exact APG79E main remains
32/32/32, 14/18, and 30/1/31. No successor is authorized.

## APG81D Node.js repo-local scratch integration checkpoint

[APG81D](../evaluations/apg81d-nodejs-provisional-integration.md) reconstructs
the complete Node provisional-integration candidate and temporary ignored
repo-local scratch contract. Final staged review finds one High rollback test-
contract defect and three Medium specification, fail-closed query, and cleanup-
evidence defects. The attempted integration is discarded without product
repair. ADR 0046 remains Proposed; Node remains repair-required and
unintegrated at branch shape 33/32/32; exact APG79E main remains 32/32/32,
14/18, and 30/1/31. No Node or scratch debt is accepted and no successor is
authorized.

## APG81E Node.js final-integration review checkpoint

[APG81E](../evaluations/apg81e-nodejs-final-integration-closure.md)
reconstructs the complete Node integration candidate and closes the APG81D
scratch-cleanup proof before review. Final staged review nevertheless finds one
High incomplete rollback test-owner projection and two Medium chronology and
fresh release-schedule evidence defects. The attempted integration is
discarded. ADR 0046 remains Proposed; Node remains repair-required and
unintegrated at branch shape 33/32/32; exact APG79E main remains 32/32/32,
14/18, and 30/1/31. No Node or scratch debt is accepted and no successor is
authorized.

## APG81F Node.js actual-test-projection repair checkpoint

[APG81F](../evaluations/apg81f-nodejs-actual-test-projection-and-integration-closure.md)
attempts the one authorized actual-test-projection, chronology, and source-
evidence correction. Fresh review finds three High and two Medium defects, so
all attempted runner, test, and correction bytes are discarded. ADR 0046
remains Proposed; Node remains retained, repair-required, and unintegrated at
33/32/32. Exact APG79E main and all public, active, target, and debt state remain
unchanged. No successor is authorized.

## APG81G Node.js selector, release, and integration closure

[APG81G](../evaluations/apg81g-nodejs-selector-release-and-integration-closure.md)
attempted the one authorized correction of APG81F's five findings. Fresh review
found two High and four Medium defects, so all attempted implementation and test
bytes are discarded. ADR 0046 remains Proposed and Node remains retained,
repair-required, and unintegrated at 33/32/32. No Node or scratch debt is
accepted, and no successor is authorized.

## APG81H Node.js reviewable qualification and integration closure

[APG81H](../evaluations/apg81h-nodejs-reviewable-qualification-and-integration-closure.md)
is the explicit human continuation after APG81G. Fresh review of its one
correction found that the frozen topology evidence did not bind the complete
actual language-profile lifecycle map. The attempted implementation and test
bytes were discarded before commit. ADR 0046 remains Proposed and Node remains
retained, repair-required, and unintegrated at 33/32/32. No integration,
rejection, removal, debt acceptance, or successor work occurred.

The resumed APG81H recovery isolates the generic change-size negative in a real
bare-repository fixture and provisionally integrates the retained Node.js
profile. Development is 33/33/33, 14/19, and 31/1/32; Node lifecycle is
`provisionally-integrated` and ADR 0046 is Accepted with amendment. Node and
scratch debt are zero. Public and active corrected v0.4.0 remain unchanged, and
no stable maturity, readiness, publication, deployment, APG81I, APG82, or
successor work is implied.

## APG82 APGR CLI and distribution foundation

[APG82](../evaluations/apg82-apgr-cli-distribution-configuration-and-artifact-contract-foundation.md)
establishes the publishable `agentic-praxis-grimoire` Python distribution, the
`agentic_praxis_grimoire` import package, and the canonical `apgr` executable.
Installed consumer commands use a packaged, source-digest-bound skill-metadata
manifest without an APG source checkout. Full skill content and projection
remain repository-maintenance operations, which fail clearly when repository
authority is absent. Maintained historical executable names remain thin
compatibility shims over the same owners.

APGR resolves `--apgr-home` over `APGR_HOME` over `~/.apgr`. Declarative global
and project configuration use `config.toml` beneath the resolved APGR home and
`<project-root>/.apgr/`, with scalar precedence of explicit CLI, project,
global, then built-in default. The reserved future adapter checkout is
`~/.apgr/agentic-praxis-grimoire-nd/`; APG82 creates no adapter or Nix
deployment.

New terminal artifacts use
`~/Documents/agent/outbox/<project>/<phase>/`: exactly one current Git-show,
Git-diff, or ops-only primary plus immutable numbered final responses. The
`apgr skills context-report` measurement reports exact discoverable-description
bytes and characters without imposing a budget threshold. APG82 publishes
nothing and starts no successor. APG83 bounded dogfood and release readiness is
recommended next under separate authority.

## APG83 v0.5 release readiness

[APG83](../evaluations/apg83-v0-5-bounded-dogfood-and-release-readiness.md)
dogfoods the retained v0.5 product against exact revisions of the two approved
Knowledge Forge repositories and qualifies APGR from fresh outside-checkout
installs. The compact matrix produces eleven passes, one truthful deferred-v0.6
boundary, and no material APG blocker. One deterministic sdist archive-metadata
defect is corrected and covered before the final release rebuild.

APG83 proves the v0.5 distribution contract: the public Git release carries
the complete skill corpus, projections, and maintenance owners, while the PyPI
distribution carries the checkout-independent `apgr` runtime and exact skill
metadata. The pair is version-bound and reproducibly consumable without mutable
development-checkout state. APG84 publication is recommended but separately
authorized and is not begun here.

## APG87 JSX and React profile integration

[APG87](../evaluations/apg87-jsx-react-profiles-and-apg88-headroom-conservation.md)
provisionally integrates one library-independent JSX syntax/transform owner and
one host-independent React component/render owner. Objective boundary fixtures
keep TypeScript, JavaScript, Node, Vitest, generic test discipline, and the
future MDX/Astro owners separate. Development is 37/37/37 and 14/23, with 37
discoverable entries and zero malformed metadata.

The 248-byte JSX and 268-byte React descriptions consume 516 bytes, producing
9,052 total and retaining 475 bytes for APG88. The generic APG039/APG040 checker
is unchanged and topology-agnostic. Public and active v0.5.0 remain unchanged;
no MDX/Astro implementation, APG88, advisory discovery, version change,
publication, deployment, target mutation, or remote push occurs.

## APG88 MDX and Astro profile integration

[APG88](../evaluations/apg88-mdx-astro-profiles-and-v0-6-authoring-completion.md)
provisionally integrates one MDX document/component-seam owner and one Astro
framework/project/execution owner. Objective boundary fixtures keep Markdown,
JSX, React, TypeScript, JavaScript, Node, Vite, Starlight, styling,
accessibility, and deployment concerns separate. Development is 39/39/39 and
14/25, with 39 discoverable entries and zero malformed metadata.

The 214-byte MDX and 238-byte Astro descriptions consume 452 bytes, producing
9,504 total and retaining 23 bytes beneath 9,527. All six frozen v0.6 profiles
are authored and provisionally integrated. The generic APG039/APG040 checker is
unchanged and topology-agnostic, and explicit project subsets do not expand.
Public and active v0.5.0 remain unchanged; no APG89, advisory discovery,
version change, release publication, deployment, active projection mutation,
provider Git publication, or successor work occurs.

## APG89 v0.6 readiness

[APG89](../evaluations/apg89-v0-6-dogfood-composition-context-and-readiness.md)
qualifies the 39-skill tree through read-only target dogfood, sibling-owner
composition, exact project-selected subsets, installed context readback,
reproducible packages, and deterministic coverage evidence. Its external
supervisory review returned **ACCEPT** with C0/H0/M0/L0 findings and
terminalized the phase as `READY_FOR_APG90`.

## APG90 v0.6 publication preparation

APG90 advances the package version to 0.6.0 and prepares the exact public
release while preserving historical v0.5.0. v0.6 contains 39 skills, 39
projections, 14 stable and 25 provisional rows, and 9,504 description bytes.
Explicit project selection remains authoritative; no automatic profile chain
or seventh v0.6 profile ships.

Tracked preparation and an exact public-publication handoff do not themselves
claim that the public tag, GitHub Release, Trusted Publishing workflow, or PyPI
version exists. No Nix deployment or active APGR projection mutation is part
of APG90.

## APG91–APG93 v0.6 publication and readback

APG91 diagnosed the initial publication runner's environment binding. APG92
proved the frozen APG90 release content exact, hardened the operator
publication path, and preserved the release bytes. APG93 then published and
read back v0.6.0 through the authorized public GitHub and PyPI surfaces. The
terminal public state contains 39 skills with 14 stable and 25 provisional
rows; no v0.7 implementation or host activation was part of that publication.
See the [APG93 evaluation](../evaluations/apg93-v0-6-public-github-and-pypi-publication.md).

## APG94 v0.7 embeddable toolkit architecture

APG94 accepts the library-first Go architecture, public API and schema
boundaries, distribution model, task-scoped context, environment, hotspot,
documentation, and APG–JACA ownership contracts for v0.7. It changes no
runtime, version, package, skill, maturity, or deployment state. See the
[APG94 evaluation](../evaluations/apg94-v0-7-embeddable-toolkit-architecture.md).

## APG95 Go reporting library

APG95 implements the first embeddable Go vertical slice: public `schema` and
`report` packages, in-memory Show, Diff, and Operational records, exact
compatibility bytes, bounded native Git execution, and optional safe
publication. See the
[APG95 evaluation](../evaluations/apg95-go-reporting-library-vertical-slice.md).

## APG96 Go CLI and report bridge

APG96 adds `cmd/apgr`, build information, report path/recovery adapters, and
thin Python delegation while preserving the Python implementation only as a
test oracle. It does not publish or change the v0.6 release. See the
[APG96 evaluation](../evaluations/apg96-go-cli-foundation-and-python-report-migration-bridge.md).

## APG97 deterministic skill context bundles

APG97 embeds the canonical 39-skill corpus in Go and adds strict, deterministic
bundle resolution, byte budgets, fingerprints, and isolated materialization.
It changes no skill body or maturity. See the
[APG97 evaluation](../evaluations/apg97-deterministic-skill-context-bundles-and-agent-scoped-materialization.md).

## APG98 portable environment snapshots

APG98 adds strict environment profiles, explicit-map capture, canonical
snapshots, safe no-churn storage, and isolated or overlay resolution. It does
not modify `.flakes`, Nix, shell hooks, or live host state. See the
[APG98 evaluation](../evaluations/apg98-portable-environment-snapshots-and-resolution.md).

## APG99 structural hotspot analyzer

APG99 adds bounded, provider-neutral hotspot analysis with deep Go metrics,
honest structural or unavailable capability levels, stable JSON and
fingerprints, deterministic rankings, and terminal/Markdown renderers. Git
growth and churn remain deferred. See the
[APG99 evaluation](../evaluations/apg99-structural-hotspot-analyzer.md).

## APG100 complete Go strangler and multi-ecosystem distribution

APG100 moves response capture and every portable command family to one Go
semantic owner, retains explicitly classified Python maintenance behavior,
and completes the locally qualified three-target Go, Python, and npm
distribution architecture. The operator accepted its reviewed and corrected
closeout source after a dispatcher result-fence recognition failure; the
failure changed no source bytes. v0.7.0 remained an unpublished release
candidate. See the
[APG100 evaluation](../evaluations/apg100-complete-go-strangler-and-multi-ecosystem-distribution.md).

## APG101 human documentation restructuring

APG101 replaces the phase-ledger root README with a concise landing page,
creates the frozen task-oriented reference and guide owners, and preserves
this chronology outside onboarding. It distinguishes published v0.6.0 from
the locally qualified, unpublished v0.7.0 release candidate and changes no
runtime, package, version, skill, maturity, JACA, Nix, or publication state.
See the
[APG101 evaluation](../evaluations/apg101-human-documentation-restructuring.md).
