# APG Project Model

<!-- APG-CANDIDATE-STATE: css-language-profile retained-provisional -->

The marker above is the mechanical current-state authority. Bounded
contradiction diagnostics cover only their frozen vocabulary; arbitrary prose
still requires human review.

## Purpose

APG separates routinely loaded rules, triggerable procedures, durable decisions,
phase history, executable checks, and source evidence. Each artifact has one
normative owner and a validation burden suited to its effect.

## Authority model

Artifact ownership does not grant action authority. The human maintainer retains
ultimate project, roadmap, publication, license, and destructive-action
authority. ChatGPT manages planning and review only inside a human-authorized
task, phase, or preapproved roadmap envelope. Top-level Codex executes a bounded
ChatGPT assignment and manages internal Codex workers; each lower layer may
narrow but not expand its assignment.

The [manager-worker protocol](manager-worker-protocol.md) is the normative owner
of this delegation chain, its stop boundaries, worker-result dispositions, and
final report direction. ADRs and roadmap entries record decisions and proposals;
they do not grant an actor authority beyond the human-approved envelope.

## Artifact ownership

| Surface | Normative role | Content boundary |
| --- | --- | --- |
| Root `AGENTS.md` | Repository-wide triggers and rules | Concise rules that apply to nearly all repository work, plus routes to focused owners. |
| Canonical skill leaf | Triggerable procedure | Reusable work requiring judgment or specialized knowledge; the leaf owns its procedure after it triggers. |
| Skill supporting file | Skill-local support | Heavy references, examples, templates, scripts, or assets needed only by one skill. |
| Harness discovery projection | Client-specific discovery layout | Links or metadata that expose canonical content to one supported harness without copying or redefining the procedure. |
| Core documentation | Focused policy and rationale | Project model, skill maintenance, provenance, coordination, evaluation, and roadmap guidance. |
| ADR | Durable architecture decision | Context, decision, alternatives, consequences, and later supersession. |
| Exit record | Bounded phase history | Truthful disposition, scope, outcome, validation, deferrals, and next authorization. |
| Deterministic tooling | Mechanical enforcement or transformation | Stable invariants with executable acceptance evidence. |
| Evidence record | Observation, not policy | Source maps, contradictions, uncertainties, evaluations, and recommendations. |

When a concept appears in more than one place, the table's owning surface
remains normative. Root instructions route to focused policy; evidence supports
it; exit records describe one application. Secondary references must not
silently redefine the owner.

## Evidence domains

APG distinguishes five domains:

1. **Public APG artifacts.** Publishable instructions, skills, documentation,
   decisions, exits, and tools that must be understandable on their own.
2. **Publication-excluded development evidence.** Dated semantic source
   identities, phase-local evidence IDs, bounded path mappings, and private
   analysis retained for maintainers but omitted from public projections.
   Exact Git objects remain in managed reports or transient verification
   evidence rather than tracked documents.
3. **Maintainer-authored source material.** Standards, skills, examples, and
   project practices that may inform APG but remain evidence until adopted.
4. **Public external sources.** Third-party projects and specifications whose
   identity, version, license, and attribution requirements can be stated
   publicly.
5. **Public projections.** Filtered, squashed releases of the public APG
   surface that exclude development-only evidence. Public v0.1.0 is the first
   such release; future projections retain the same independence contract.

Evidence location, source ownership, publication eligibility, and license are
independent facts. Public files do not link to publication-excluded material;
excluded evidence may point to its public APG destination.

## Destination decision

| Destination | Appropriate content |
| --- | --- |
| Root `AGENTS.md` | A concise repository-wide rule whose routine activation is justified. |
| Skill | A reusable, triggerable procedure that benefits from guided judgment. |
| Skill supporting file | Detail or deterministic support needed only after one skill triggers. |
| Core documentation | Architecture, rationale, provenance, roadmap, or maintainer-facing governance. |
| ADR | A consequential, durable decision with meaningful alternatives or later supersession needs. |
| Exit record | The terminal truth of one bounded phase. |
| Deterministic tooling | A mechanical constraint or transformation with an executable acceptance test. |
| Reference only | Useful evidence that has not passed APG evaluation and adoption. |
| Reject | Material that conflicts with APG goals, adds unjustified ceremony, lacks usable provenance, or is too project-specific for the proposed owner. |

These destinations are not ranks. A concise instruction may route to a skill;
the skill may use a deterministic helper; documentation may explain why that
combination was adopted.

## Practice lifecycle

1. **Inventory.** Record a dated evidence snapshot, exact source scope in the
   appropriate provenance level, ownership, publication status, and known
   licensing.
2. **Evaluate.** Identify the concrete problem, evidence strength, generality,
   existing agent capability, trigger precision, expected benefit, ceremony,
   maintenance cost, safety impact, and reversibility.
3. **Propose.** Choose the owning destination, derivation mode, observable
   acceptance criteria, and rollback boundary.
4. **Validate.** Use representative scenarios, deterministic checks, review, or
   other evidence proportional to the claim. Source frequency is not
   validation.
5. **Decide.** Record `adopted`, `deferred`, `rejected`, or `superseded` with a
   rationale and evidence.
6. **Maintain.** Keep the artifact, tests or evaluation evidence, documentation,
   and provenance consistent. Supersede decisions explicitly rather than
   rewriting history.

Observation and decision remain separate throughout this lifecycle. A source
can be described accurately and still be rejected as APG policy.

An accepted profile-family architecture is still design evidence, not a skill.
Candidate approval for later authoring creates no canonical leaf, catalog row,
projection, route, maturity state, or release entry. Those surfaces change
only in a separately authorized implementation and validation cycle. Rejected
ADR 0031 illustrates the stronger boundary: reviewed candidate evidence does
not authorize authoring after a terminal design defect.

The [skill authoring and maintenance guide](skill-authoring-and-maintenance.md)
is the normative owner for applying this general lifecycle to new skills,
frontmatter or procedure corrections, support additions, maturity-only
dispositions, deprecation, and removal. The guide does not redefine the general
destination model or grant action authority.

## Structured project and executable defaults

The [structured project phase defaults](structured-project-phase-defaults.md)
own APG's ordinary formal and non-phase commit, status, ADR, docs-only, scoped-
test, managed-report, and manager-assignment compression conventions. They are
project parameters rather than reusable action authority and yield to a target
repository's more specific owner.

The [testing and coverage policy](testing-and-coverage-policy.md) owns APG's
scoped-test default, coverage-remediation design, real-boundary rule, and
adopted pytest architecture. Accepted ADR 0024 records the APG test runner,
mirrored paths, source inventory, exact gates, and retained Bats boundary. The
[agent reporting architecture](agent-reporting-architecture.md) owns the
Python-first executable decision and the accepted Git show, Git diff, and
operational-report component design. ADR 0023 owns the proposed formats,
state-evidence identity, canonical association, supported POSIX write boundary,
and rollback. APG27 remains a partial precursor; APG27A corrects and adopts its
Python reporting implementation. APG28 stops Partial; APG28A preserves that
result and adopts the corrected pytest path and runner migration. APG29 aligns
the existing planning, implementation, review, and roadmap-assignment leaves
with those project defaults without adding a duplicate skill or changing
maturity, routing, or release state. APG30 implements the accepted
ChatGPT-manager namespace and subrouter while preserving flat Codex discovery
and historical direct-child release policy.

## Modularity and skill categories

An APG skill is the smallest independently triggerable procedure with a coherent
purpose and validation surface. Skills do not repeat repository rules or embed
unrelated project standards. Shared behavior becomes a separate skill or helper
only after repeated use demonstrates a stable boundary.

A broad category taxonomy is not adopted. Catalog labels may help discovery,
but real skills must test those boundaries before labels become directories or
routing rules. ADR 0022 and APG30 implement one actor-qualified
`skills/chatgpt/` owner and dedicated subrouter for ChatGPT-manager leaves; the
topology does not classify
ordinary process or technical skills by category. A cross-cutting skill retains
one canonical implementation and may receive several catalog labels if
evaluation supports them.

## Harness and projection boundaries

Canonical skill content expresses procedure, boundaries, and evidence without
depending on one client. A harness-specific discovery projection may add only
the layout or metadata needed to expose that content. It does not duplicate
policy or procedure and may not weaken the canonical authority, safety,
privacy, evidence, or stop boundaries.

APG's Codex repository projection lives under `.agents/skills/` as relative
symbolic links to the canonical leaves under `skills/`. It is not a plugin,
runtime, registry, adapter process, second canonical copy, or separate skill.
For an opted-in separate Git worktree, `apg-project-skills` may create local
absolute links to the same canonical leaves. Strict Git-local state owns those
links and an exact local exclusion block; it does not modify tracked target
files or global Codex state. [ADR 0004](adr/2026/07/0004-project-local-skill-projection-and-rollback.md)
owns that command and rollback boundary. Other harness projections require
their own evidence and explicit authority.

Public v0.1.0 was produced as a squashed filtered projection, but its tracked
surface omitted one documented executable wrapper. Accepted ADR 0009 now owns
the correction: every tracked path outside `private/` is projected exactly,
while a strict critical policy detects removal of public owners from source.
`apg-public-release` builds and checks one local squashed candidate over the
previous public base without network, push, or publication. It is a bounded
release adapter, not a general packaging framework. APG14 used that accepted
boundary to publish v0.2.0 as one appended release commit and annotated tag.

User-scoped distribution is separate from both release construction and
project-local projection. `apg-user-skills` validates a tagged public checkout,
manages the source release's exact direct-link set under the documented user
root, and records exact
user-local ownership and previous-source state. It does not write repository
exclusions, target repositories, Codex configuration, or plugin state.

APG53 adds a third, harness-neutral projection utility:
`flatten-skill-symlinks`. It discovers direct regular `SKILL.md` markers in a
nested source and creates one flat output link per skill. Exact owner state,
a destination lock, atomic link replacement, state-last commit, and rollback
protect `--replace` and `--clean`; unmanaged entries are never adopted or
removed. The command does not choose a Claude root, mutate a live integration,
install packages, execute skill content, or become a universal package
manager.

APG54 adds `install-global-skills` without merging those contracts. It chooses
the documented Codex or Claude personal skill root and projects one complete
set of caller-supplied local repositories, or installed APG by default. All
sources are inventoried before mutation; duplicate basenames fail; one
command-specific state and lock own update, stale cleanup, rollback, check,
dry-run, and uninstall. The desired source set may change within one
installation identity, but another owner, schema, agent, destination, or
unmanaged link is never adopted. Arbitrary repositories receive structural
projection checks only, not public-release or trust validation. ADR 0033 owns
this boundary.

Generated evidence follows a compact-record boundary. Complete membership,
exclusion, measurement, replay, and equivalent datasets regenerate into an
explicit empty untracked root outside the repository. Git retains manifests,
rules, source and rights identities, hashes, summaries, review samples,
tooling, tests, and reproduction narratives. The deterministic change-size
policy checks staged, committed, and complete-tree Git objects; exceptions are
exact-path, exact-object, mode-bounded, owned, reasoned, and review/expiry
conditioned.

APG16 expands the private development catalog with one provisional workflow
router, APG17 adds one provisional guidance-synthesis leaf, APG18 adds one
provisional Python language profile, and APG19 adds provisional Bash, Bats,
and Zsh profiles while historically deferring ZUnit. APG20 evaluates but
defers Go and Ruby; APG20A corrects the recorded defects and retains both profiles. APG21 accepts
separate Nix, PostgreSQL, and SQLite ownership, retains provisional PostgreSQL
and SQLite profiles, and defers Nix after a second material candidate defect.
APG21A corrects that Nix defect and retains the reconstructed profile, while
one bounded PostgreSQL false-escalation correction leaves SQLite and router
behavior unchanged. No generic SQL owner is added. The resulting development
catalog contains six stable process leaves and thirteen provisional skills.
The router's schema-version-1 skill-local
capability map is selection metadata owned by that leaf; a focused exact-set
test keeps its eighteen entries aligned with the routable catalog while
excluding the router itself. Through APG23, the accepted v0.2 project- and
user-scope commands and public release policy remain six-skill lifecycle
contracts. ADR 0019 owns the later explicit v0.3 distribution decision; adding
a development skill alone never broadens lifecycle or release semantics.

APG19A preserves that catalog shape while correcting the Bats fallback test
count for runner-supported comment function declarations. ADR 0015 and the
phase-identity guide govern its semantic identifiers and precommit record
finalization; neither changes skill maturity or lifecycle scope.

APG20 preserves semantic identity and the six-skill v0.2 lifecycle while
deferring both candidates. APG20A retains the corrected Go and Ruby leaves,
catalog rows, projections, map entries, tests, and known-unmanaged handling. It
creates no architecture ADR, state schema, distribution owner, or application-
smoke observation.

APG21 accepts ADR 0016 and adds PostgreSQL and SQLite leaves, catalog rows,
projections, map entries, tests, and known-unmanaged handling. Nix evidence
remains durable but its candidate leaf and integration are removed after
`deferred-material-defect`. Engine profiles conform to the warning contract
without becoming generic language, SQL, migration, or database-operations
owners. Exact live facts and authority remain project- and task-owned.

APG21A uses the durable Nix evidence as a corrected baseline and adds one Nix
leaf, projection, catalog row, map entry, test contract, and known-unmanaged
name. One focused PostgreSQL correction scopes tested restoration to changes
that rely on it for recovery. Project, user, and public lifecycle ownership
remains the six stable v0.2 leaves under schema version 1.

APG22 applies the router, synthesis leaf, and all nine retained profiles to a
frozen read-only cross-repository matrix. All 35 cases match with no APG
behavior correction. Its migration design keeps APG's concise root, preserves
target-project and private overlays, and makes future shadow, discovery,
override, target acceptance, and restoration evidence prerequisites rather
than implicit effects of skill availability. APG22A adds the provisional
`composing-approved-roadmap-assignments` owner after 30 frozen cases and an
ordinary-prompting baseline. The leaf owns only authority-preserving
composition; planning, worker assignment, routing, review, acceptance,
dispatch, and execution remain separate. APG22B subsequently retains a
version-bounded ZUnit owner for exactly v0.8.2 with Zsh 5.9.2 after direct
compatibility evidence; 5.3.1 and every unverified pair stop. The six-skill
lifecycle, schemas, public source, and active integration do not change.

APG22C subsequently corrects the selected user-startup path in the disposable
ZUnit harness and requires matched positive, negative, and in-runner controls.
The exact support disposition is retained without changing any canonical leaf,
projection, catalog row, capability-map entry, maturity row, lifecycle schema,
public source, or active integration. Fresh-session application smoke remained
owned by APG23 after the required full application restart.

APG23 directly discovers all nineteen repository skills, source-qualifies the
duplicate workflow router, applies every provisional owner and required
process/domain pairing, and records independent maturity and inclusion
dispositions. Eight v0.3 rows become stable; five remain provisional and all
thirteen are release-ready. No skill procedure, public v0.2 owner, lifecycle
schema, managed default, external target, or active integration changes.

APG24 accepts ADR 0019 and publishes the exact nineteen-skill v0.3.0
projection. User lifecycle derives each managed set from its independently
verified release identity, enabling exact six-to-nineteen update and
nineteen-to-six rollback under schema version 1. New project installs default
to nineteen while existing explicit subsets remain authoritative. The active
integration advances by source fast-forward without aggregate-link or ownership
migration, and the personal router remains for external shadow observation.

APG24A records the human-reported successful external shadow and the separately
authorized personal-router decommission. The public-backed aggregate remains
the active owner with nineteen skills, the former personal router remains
exactly restorable from private history, and no other personal skill changes.
This closes v0.3 semantically without changing a skill, release, lifecycle,
active source, or target repository.

APG25 accepts structured defaults, Python-first report and pytest architecture,
the future ChatGPT-manager namespace/subrouter, and evidence-gated personal
hygiene transition. One bounded assignment-composition correction consumes the
new defaults. The direct-child 19/19/19 development shape, fourteen-stable/
five-provisional maturity split, public v0.3.0, active integration, report
executables, tests, and personal sources remain unchanged.

APG26 retains two provisional direct-child capabilities:
`pytest-test-profile` for pytest-specific collection, fixture, mock, xdist,
coverage, and structural judgment, and
`converting-bash-scripts-to-python` for compatible migration of an existing
Bash executable or script family. The private-development shape becomes
21/21/21 with fourteen stable rows, seven provisional rows, and twenty routable
non-router entries. Public and active v0.3.0 remain 19/19/19; no report
executable, test tree, managed default, release schema, ChatGPT owner, or
personal skill changes.

APG30 implements the accepted nested owner and subrouter. Canonical discovery
supports exactly direct leaves and `skills/chatgpt/<name>` leaves, with global
frontmatter-name uniqueness and flat projections. The general router owns
nineteen ordinary non-ChatGPT edges plus one subrouter edge; the
ChatGPT-local map owns the manager-assignment edge. Development is 22/22/22
with fourteen stable and eight provisional rows. Public and active v0.3.0
remain 19/19/19, and no personal skill changes.

APG31 verifies that topology through direct fresh-session client evidence and
applies the evidence-gated personal transition model independently. The
personal docs-only capability is decommissioned because current APG and
repository owners replace every coherent unit and exact restoration remains
available. Git-history and RepoMap phase-hygiene transitions defer because
their current private caller boundaries cannot be corrected within the
authorized target-only scope. APG skills, catalog, projections, maturity,
router maps, public and active v0.3.0, and target repositories remain
unchanged.

APG31A records the later application smoke as passed while preserving APG31's
historical Partial disposition. Publication-excluded transition review supports
scope reduction of `git-history-hygiene` after generalized behavior returns to
APG and repository owners, and decommission of `repomap-phase-hygiene` after
generalized behavior returns to current RepoMap owners. APG topology, maturity,
catalog, projections, router maps, and immutable release surfaces remain
unchanged.

APG32 applies the new-skill lifecycle to one direct-child
`minitest-test-profile`. The provisional owner supplies Minitest-specific test
and spec organization, lifecycle, assertion, mock and stub, isolation,
parallel, filter, runner, plugin, reporter, fixture-alternative, boundary-effect,
and structural judgment while preserving general implementation, review,
Ruby-language, project-test, repository-isolation, and authority owners.
Development becomes 23/23/23 with fourteen stable and nine provisional rows.
The general router contains twenty-one edges, the ChatGPT-local router remains
one edge, and public and active v0.3.0 remain 19/19/19.

APG33 applies the same lifecycle to one direct-child `dockerfile-profile`. The
provisional owner supplies Dockerfile-specific parser-directive, stage,
instruction-form, variable-scope, context, ignore, copy, add, mount, cache,
ownership, runtime-default, and platform judgment while preserving base-image,
dependency, shell-language, runtime, release, and live-operation owners.
Development becomes 24/24/24 with fourteen stable and ten provisional rows.
The general router contains twenty-two edges, the ChatGPT-local router remains
one edge, and public and active v0.3.0 remain 19/19/19.

APG34 applies the same lifecycle to one direct-child `vagrantfile-profile`.
The provisional owner supplies Vagrantfile-specific configuration-version,
load-order, machine, box, provider, network, synced-folder, provisioner,
trigger, state, host-dependent, and structural judgment while preserving
general Ruby and shell, provider, host, dependency, network, filesystem,
lifecycle, release, and live-operation owners. One bounded source-semantics and
machine-measurement correction qualifies forwarded-port behavior and prevents
implicit-default overcount. Development becomes 25/25/25 with fourteen stable
and eleven provisional rows. The general router contains twenty-three edges,
the ChatGPT-local router remains one edge, and public and active v0.3.0 remain
19/19/19.

APG38 applies the lifecycle to the APG37 replacement candidates. Independent
review and isolated compatibility evidence retain `go-test-profile` and
`go-cmp-test-profile` provisionally, with one coherent correction cycle
each. Corrected-state review finds new material defects in
`matryer-is-test-profile` and `nix-test-profile`; the one-cycle rule defers both
candidates and removes their current-tree surfaces. ADR 0026 accepts two
independently triggerable Go component owners and no stack owner. Development
becomes 27/27/27 with fourteen stable and thirteen provisional rows. The
general router contains twenty-five edges, the
ChatGPT-local router remains one edge, and public and active v0.3.0 remain
19/19/19.

APG39 authors final replacement candidates for the two APG38-deferred
profiles on a Claude authoring branch, closing the registered-wrapper,
relaxed-mode, and sandbox-platform corrected-state defects from reverified
exact sources, proposing ADR 0027 conditionally, and handing integration to
a later separately authorized Codex phase. Nothing is integrated: development
remains 27/27/27 with the same maturity, router, and edge counts, and public
and active v0.3.0 remain 19/19/19.

APG40 preserves the exact APG39 authoring object and independently reviews,
corrects, and dispositions both candidates. `nix-test-profile` is
`retained-provisional` after exact-source and rights review, forty corrected
public-safe scenarios, source-corpus calibration, one coherent correction
cycle, and fresh non-author review. `matryer-is-test-profile` is
`deferred-material-defect` after corrected-state review finds its equality
mechanism still inaccurate, so its current surfaces are forward removed. ADR
0027 is Rejected, ADR 0026 remains Accepted and controlling, and the stack
remains absent. Development becomes 28/28/28 with fourteen stable and fourteen
provisional rows, twenty-six general-router entries, one ChatGPT-local entry,
and twenty-seven checked edges. Public and active v0.3.0 remain 19/19/19.

APG41 reviews every retained provisional owner without changing maturity,
preserves direct cross-profile selection without a mandatory chain, and
corrects only candidate-independent removal wording for the Minitest,
Dockerfile, and Vagrantfile profiles. Repository-owned disposable v0.4.0
candidate construction and isolated lifecycle smoke pass on the current host.
The result is `ready-for-publication-with-provisional-limitations`: release
fitness evidence for a separate maintainer decision, not publication,
deployment, promotion, or successor authority.

APG42 applies that accepted release decision. It projects the exact committed
non-private source into one squashed public v0.4.0 commit whose sole parent is
v0.3.0, adds one annotated tag, verifies a fresh public checkout, and advances
the aggregate-owned active public source by exact fast-forward. The result
remains 28/28/28, fourteen stable and fourteen provisional, with twenty-six
general routes, one ChatGPT-local route, and no mandatory chain. APG42 changes
no skill procedure or maturity row and authorizes no successor phase.

APG43 records the one-time maintainer-authorized correction of a release-
blocking unrelated project identity in `NOTICE`. The corrected APG42 source,
public v0.4.0, and active public-backed source converge without changing the
v0.4.0 surface, maturity, routing, metadata, or historical v0.1.0-v0.3.0
objects. Future publication remains append-only, and v0.5 requires separate
authority.

APG49 preserves the exact APG48 authoring input and independently runs
byte-level source review, dogfood reverification, failing-first contracts,
isolated runtime probes, one correction pass, and fresh review. New
corrected-state behavior defects force `deferred-material-defect`; current
candidate surfaces are forward removed. ADR 0030 is Rejected, ADR 0026 remains
Accepted and controlling, no stack exists, and development remains 28/28/28.

APG52 adds a publication-excluded evidence implementation without changing
the public skill model. Exact source, rights, artifact, exclusion, measurement,
sample, statistics, and comparison records are generated from immutable Git
objects and reproduce byte-for-byte from disjoint acquisitions. Evidence
sufficiency is separate from profile disposition: named insufficient corpus
classes do not become skills, while sufficient distributions do not become
thresholds. ADR 0031 remains Rejected, all ten Web and Node candidates remain
deferred, and development, public, and active skill surfaces remain unchanged.

APG54 adds one current-development local repository-set projector under
Accepted ADR 0033. APG55 forward-hardens only its implementation boundary:
partial container creation is rollback-owned, replacement mutations have
explicit stages, private state reads prove exact EOF and stable metadata, and
source identities are revalidated around mutation. The public command, source
set, ownership model, 28/28/28 skill surface, fourteen/fourteen maturity, and
corrected public/active v0.4.0 remain unchanged.

APG56 reconstructs the Web and Node candidate architecture from the APG52
reproducible evidence and proposes ADR 0034 without authoring, accepting, or
integrating any skill. It separates owner validity, authoring eligibility,
and growth-band eligibility per candidate, freezes its band-derivation method
before calculation, and keeps insufficient artifact classes non-normative.
Proposed architecture records remain design evidence under the practice
lifecycle: they change no canonical leaf, catalog row, projection, route,
maturity state, test inventory, release object, or active installation, and
rejected ADR 0031 remains the terminal record of the prior family decision.

APG57 independently reviews that fresh reconstruction and rejects ADR 0034
after material corrected-state numerical-evidence, one-count-ledger, and
scenario defects. Every numeric band and all authoring remain deferred, no
authoring slice is eligible, and rejected ADR 0031 remains unchanged. This
terminal rejection changes no canonical leaf, catalog row, projection, route,
maturity state, test inventory, release object, or active installation.

APG58 pilots a different authority model on one candidate only: explicit
policy-selected structural limits (300/600/900) for CSS, with corpus and
target evidence demoted to falsification and legacy classification. It
authors the unintegrated `css-language-profile` candidate leaf and
specification, proposes ADR 0035, and defers the decision to a separately
authorized independent Codex validation. Candidate records remain design
evidence under the practice lifecycle: no canonical leaf integration,
catalog row, projection, route, maturity state, test inventory, release
object, or active installation changes, and both rejected Web/Node ADRs
remain terminal records.

APG59 independently validates that pilot and applies one forward correction.
Growth uses the highest task-baseline, current, projected, and actual-result
level across the complete authorized task or formal phase; salami-slicing and
feature-as-correction cannot evade a response. Repository and human authority,
accessibility acceptance, and token meaning remain project-owned while CSS
retains its language semantics. Corrected-state review then finds material
executable-contract and removal defects. The one-correction rule requires
rejection and current-surface cleanup: ADR 0035 is Rejected, the CSS leaf is
absent, and development remains 28/28/28, fourteen stable and fourteen
provisional, with twenty-six general routes and one ChatGPT-local route.
Corrected public and active v0.4.0 remain unchanged.

APG60 addresses the resulting foundation defect without retrying the
candidate. A closed 60-case pre-authoring fixture and deterministic
standard-library evaluator assert exact growth, task, authority, semantic,
counting, exclusion, legacy, exception, and lifecycle outcomes. A generic
candidate-surface manifest distinguishes 40 current subowners from public,
publication-excluded, and managed-report history; synthetic retained and
rejected lifecycles independently falsify every current omission and stale
owner. The CSS leaf, specification, projection, catalog, route, maturity,
release, and active surfaces remain absent. ADR 0035 remains Rejected, ADR
0036 remains unused, and corrected public/active v0.4.0 remain unchanged.

Record mechanics are owned by the
[phase and record identity guide](phase-and-record-identity.md),
[ADR index](adr/README.md), and [exit-record index](status/README.md). Phase IDs
are semantic and globally unique; ADR and exit sequences are independently
allocated. Current owners, evaluations, exits, and indexes are finalized before
commit, while exact Git evidence remains in post-commit managed reports. The
direct-and-ChatGPT-nested skill shape is documented
in [`skills/README.md`](../skills/README.md); the proportional maintenance
procedure is owned by the
[skill authoring and maintenance guide](skill-authoring-and-maintenance.md).

`apg-check-skill-library` enforces only the adopted mechanical leaf, catalog,
link-containment, and checked-in projection invariants. It does not assess
semantic quality, authority, privacy, provenance, discovery, maturity, release
completeness, or stability. ADR 0008 owns that boundary.

ADR 0010 separately records the semantic maturity disposition for the six
process leaves. All are `stable` for routine bounded use under their triggers;
that disposition grants no action, publication, destructive, or successor
authority. APG16 adds one provisional router, APG17 adds one provisional
guidance-synthesis leaf, APG18 adds one provisional Python profile, and APG19
adds three provisional shell or shell-test profiles without changing those
dispositions. APG20A retains two provisional Go and Ruby profiles without
changing stable maturity. APG21 retains two provisional relational-engine
profiles and defers Nix without changing stable maturity. APG14 separately
exercised the authorized v0.2.0
publication;
no successor roadmap epic is implied.

APG21A retains the corrected Nix profile provisionally and changes no stable
maturity disposition or v0.2 distribution contract.
APG22 changes no leaf or maturity disposition. Its explicit-use dogfood is
semantic evidence, not fresh-session application discovery or readiness.
## APG60A correction boundary

APG60A preserves APG60 as an immutable historical phase and advances only the
current executable contract. A retained candidate must agree exactly across
the declared owner manifest, live dynamic inventories, public release owners,
tests, inventory, and current narratives. This is integration closure, not a
semantic approval mechanism. Candidate authoring and ADR 0036 remain outside
the phase.

## APG60B exact-owner closure

APG60B keeps the APG60A behavior contract byte-identical and strengthens only
future candidate closure. A retained candidate must provide an exact
contract-bound traceability map with unique reachable clause anchors, one
maturity-derived current-state marker in every narrative owner, exact declared
Python mirror values, isolated actual release projections, and a terminal
ADR 0036 whose index entry agrees. Rejected state preserves a Rejected ADR
while removing current candidate surfaces. Pre-authoring state has no ADR
0036. These gates establish ownership and navigation closure, not semantic
approval of candidate prose.

## APG60C runtime-truth closure

APG60C strengthens the pre-authoring model without changing candidate
semantics. Its historical owner-source finality claim is narrowed forward by
APG60D; exact markers own mechanical current state while bounded diagnostics
remain advisory for prose; actual
pre-authoring, authored-unintegrated, retained, and rejected-preserved states
are mutually exclusive; and current survivor owners must be direct regular
files with strict declared-type parsing. The APG60A behavior contract remains
unchanged, and no candidate or ADR is created.

## APG60D source-binding and exact-history closure

APG60D makes the static proof boundary explicit: exact immutable declaration
and refusal of mechanically identifiable protected-name writes. Runtime
values, general library-mediated reflective call effects, and
arbitrary caller or callback behavior are not closure authority. A closed
phase-history manifest owns exact APG58 through APG62 public and
publication-excluded bundles; selected repository owners must be direct
regular, UTF-8, nonempty, and no-follow. Candidate lifecycle gates combine
those bundles with their existing current-state and decision owners. No
candidate or ADR is created.

## APG60E repository-path ownership closure

APG60E makes physical repository residence part of lifecycle authority.
Repository-relative owners are traversed from one resolved physical root
through no-follow directory descriptors. Authoritative regular files are read
completely from the already-open direct object with bounded size and stable
metadata checks. Candidate, project, release, test, narrative, decision, and
history owners cannot be supplied through symlinked ancestors.

The expected projection leaf remains one exact relative symlink. Its
ancestors, resolved canonical target ancestors, and target leaf must remain
direct repository owners. APG58 through APG60E form the current foundation;
APG61 and APG62 retain their authored and terminal roles at exits 00086 and
00087.

## APG60F import, required-role, and projection closure

APG60F keeps the APG60E physical-root contract and adds a closed
repository-import boundary for live dynamic consumers. Parent import caches,
external dependencies, and a different repository root cannot satisfy current
owners.

The candidate-surface manifest declares all 52 required roles, and every
authored, traceability, decision, Python-binding, dynamic, narrative,
historical, and report reference resolves exactly once. Projection validation
re-inspects the expected link and direct canonical target after the target
read; its claim is bounded to that observation. APG58 through APG60F form the
foundation, with APG61 and APG62 at exits 00087 and 00088.

## APG60G snapshot, role, and derived-set closure

APG60G preserves APG60F and adds a pinned-root descriptor contract for live
dynamic consumers. Source collection and worker evaluation use the same
physical repository object, with root-entry revalidation and descriptor cleanup
on exceptional paths. Topology, library, and installer observations compare a
complete exact sorted set derived independently from direct canonical leaves.

Required lifecycle roles reproduce a code-owned generic semantic registry, so
coherent edits to the manifest and removal plan cannot redefine a role's
meaning. Direct regular authority reads now compare the final directory entry
with the opened descriptor both before and after a bounded complete read.
APG58 through APG60G form the foundation; APG61 and APG62 advance to exits
00088 and 00089. No CSS candidate or successor is authorized.

## APG60H snapshot and full-path binding closure

APG60H adds caller-controlled external worker temporary storage with parent
cleanup, exact snapshot cleanup, double-observed absence, stable path errors,
final pinned-root binding, and retained projection identity. The foundation
now ends at APG60H; future exits are 00089 and 00090.

## APG60I worker temporary-root binding and cleanup closure

APG60I replaces path-separated temporary validation and creation with a
retained no-follow root descriptor, descriptor-relative exclusive child
creation, and complete path-chain revalidation. Cleanup ownership encloses the
first create attempt and proves lexical absence while preserving primary body
failures. The foundation now ends at APG60I; future APG61 and APG62 exits are
00090 and 00091.

## APG61 CSS language-profile authoring

APG61 consumes exit 00090: one fresh `css-language-profile` candidate —
leaf, specification, and sixty-case traceability map — authored from the
frozen APG60A contract on the preserved Claude authoring branch, with
ADR 0036 Proposed. The candidate is not integrated: current candidate-state
markers remain absent, integrated counts remain 28/28/28, and development
`main` remains at exact APG60I. APG62 keeps its terminal validation role at
exit 00091 and remains separately authorized.

## APG62 CSS language-profile validation and rejection

APG62 consumes exit 00091 and terminates the APG61 candidate lifecycle as
rejected-preserved. Independent sixty-case reconstruction and semantic review
find seven initial defects; the one permitted correction is followed by a new
material six-case action overreach. ADR 0036 is Rejected, the candidate leaf,
specification, map, and validation-only test surfaces are absent, and every
current owner remains at the established 28/28/28 and 14 stable / 14
provisional state. APG61 authoring history remains immutable; no successor is
authorized.

## APG63 Markdown architecture and lean contract

APG63 consumes exit 00092: a docs-only architecture phase that begins the
Markdown profile line after the terminal CSS rejection, without touching
any CSS decision or artifact. It produces the Markdown architecture
document, the lean thirty-six-scenario validation contract, Proposed
ADR 0037, and the APG63 evidence bundle on the preserved Claude
architecture branch. No skill, catalog, maturity, route, projection,
project, release, test, or active surface changes; every current owner
remains at the established 28/28/28 and 14 stable / 14 provisional state;
development `main` remains at exact APG62. Codex peer review (recommended
APG64) keeps the terminal ADR 0037 decision role and remains separately
authorized.

## APG64 Markdown architecture peer review

APG64 consumes exit 00093 and the immutable APG63 Claude object. It performs
the terminal independent review, one permitted forward architecture
correction, exact corrected-state preservation, and fresh full review. ADR
0037 is Accepted with amendment; the corrected architecture is current and
authoring-eligible-with-narrowing, while candidate authoring remains separate.
No integrated owner changes: the model stays 28 canonical skills, 28 catalog
rows, 28 projections, fourteen stable, and fourteen provisional.

## APG65 Markdown language-profile candidate authoring

APG65 consumes exit 00093 and the accepted ADR 0037 architecture, then
authors the branch-only Markdown candidate with ADR 0038 Proposed. The
authoring branch truthfully carries the transitional physical shape of
twenty-nine canonical leaves over twenty-eight catalog rows and twenty-eight
projections, while integrated development `main` remains 28 canonical
skills, 28 catalog rows, 28 projections, fourteen stable, and fourteen
provisional. The candidate is unintegrated design evidence pending
separately authorized APG66 validation, which terminally decides ADR 0038.

## APG66 Markdown retained-provisional integration

APG66 independently validates exact APG65 against the accepted APG64 oracle,
applies and freezes one coherent correction, and accepts ADR 0038 with
amendment after fresh corrected-state review finds no new material defect.
The canonical leaf, catalog, relative projection, capability route,
project-skill set, release surfaces, fixture, focused unit and integration
tests, inventory, and current narratives agree on retained-provisional.
Development becomes 29 canonical skills, 29 catalog rows, 29 projections,
fourteen stable and fifteen provisional; public and active corrected v0.4.0
remain unchanged.

## APG67 JavaScript architecture proposal

APG67 proposes the JavaScript language-profile architecture and lean
validation contract under ADR 0039 (Proposed) as a branch-only proposal:
ECMAScript 2026 is the stable annual reference, JavaScript, TypeScript, and
Node.js are separate owners, structural policy is qualitative disposition C,
and a frozen forty-row register binds one future authoring phase and one
future review. Authoring eligibility is `authoring-eligible-with-narrowing`.
No JavaScript skill, projection, catalog, maturity, route, project, release,
or test surface exists; development remains 29/29/29 with fourteen stable
and fifteen provisional rows and 27/1/28 routes pending separately
authorized APG68 review.

## APG68 JavaScript architecture rejection

APG68 preserves the corrected JavaScript architecture as historical rejected
evidence under ADR 0039. Fresh review finds material response, route, signal,
host, and source-boundary defects after the sole correction. No current
JavaScript architecture input, skill, or integration artifact exists. APG69
candidate authoring is not recommended.

## APG69 JavaScript core architecture proposal

APG69, under new human authority, proposes a fresh branch-only
JavaScript core architecture and layered contract under ADR 0040
(Proposed) while preserving ADR 0039 Rejected. The proposed owner is a
narrower ECMAScript core with separated semantic, structural, policy,
and effective decisions. No skill, projection, catalog, maturity,
route, project, release, fixture, or test owner is created; development
remains 29/29/29, 14/15, and 27/1/28. APG70 review is recommended but
not begun.

## APG70 JavaScript core architecture rejection

APG70 preserves exact APG69, independently reconstructs and reviews every
layer, uses the one permitted correction, and preserves the corrected patch.
Fresh review finds new material defects, so ADR 0040 is Rejected and the fresh
architecture is historical evidence rather than a current project input.
JavaScript skill, projection, catalog, maturity, route, project, release,
fixture, and test ownership remain absent. APG71 is not recommended.

## APG71 TypeScript architecture proposal

APG71, under separate new human authority for TypeScript architecture only,
proposes ADR 0041: a narrow TypeScript static-semantics owner whose
effective authority is the consuming project's exact selected compiler,
with the TypeScript 7 native line and TypeScript 6 legacy line as separate
pinned source generations, closed source-kind and embedded-host boundaries,
structural policy deferred, and eligibility
`authoring-eligible-with-narrowing` granting no candidate authority.
JavaScript's rejected architectures remain historical evidence; TypeScript
skill, projection, catalog, maturity, route, project, release, fixture, and
test ownership remain absent. Separately authorized APG72 terminally
decides ADR 0041.

## APG72 TypeScript architecture rejection

APG72 independently reviews exact APG71, preserves one corrected 22/14/2
state, and rejects ADR 0041 after fresh non-author review finds new material
owner/route, role-state, source-kind, and evidence-state defects. Eligibility
is `not-applicable-rejected`; the architecture and registers are historical
evidence rather than current project input. TypeScript skill, projection,
catalog, maturity, route, project, release, fixture, and test ownership remain
absent. APG73 is not recommended.

## APG73 production recovery governance

APG73 changes the future language-profile production lifecycle under new
human authority. ADR 0042 accepts the production recovery charter and its
iterative hardening contract. One correction remains the unit of one round,
but a repairable material defect normally preserves the candidate as
`repair-required`; up to three independently evidenced rounds are available by
default. Critical and High defects block integration, while Medium and Low
debt requires an explicit bounded record and human acceptance. Human authority
owns priority, continuation, narrowing, unfitness, abandonment, rejection,
and removal; Codex owns evidence truth, consequence-based severity, gate and
rollback verification, and technical repair recommendations.

TypeScript is essential, CSS and JavaScript are desirable, and JSX is deferred.
TypeScript 7 is the intended primary generation; the older target snapshot is
migration evidence, and temporary TypeScript 6 is permitted only for a
separately identified role with a retirement condition. APG73 adds no skill,
catalog, projection, maturity, route, project, release, fixture, test, or
inventory owner. Existing integration and release state remain unchanged.

APG74 executes the first recovery authoring phase under that charter. It
authors the TypeScript language-profile candidate (leaf, specification, and
navigation-only scenario coverage) and the fourteen-case TypeScript 7
intended-state fixture on the APG74 branch, proposes ADR 0043, and
integrates nothing: the branch's transitional 30/29/29 shape is expected,
while integrated development remains exact APG73 at 29/29/29 with 14/15
maturity and 27/1/28 routes. The exact compiler is freshly selected
(`typescript@7.0.2`) and TypeScript 6 compatibility is recorded as
`not-required` with a refresh condition. APG74 adds no skill, catalog,
projection, maturity, route, project, release, test, or inventory owner;
APG75 owns hardening and the terminal ADR 0043 decision.

## APG75 retained TypeScript owner

APG75 completes the iterative-hardening lifecycle and retains the corrected
TypeScript profile provisionally. Current development owns the leaf,
specification, navigation record, TypeScript 7 fixture, maintained contracts,
catalog row, route, projection, project selection, and current-release entries.
ADR 0043 is Accepted with amendment. Development is 30/30/30, 14/16, and
28/1/29; historical corrected v0.4 and public/active v0.4.0 are unchanged.

## APG75A reusable/project boundary

APG75A clarifies that TypeScript 7 is Theme Forge Terminal Nova's product
destination, not a universal reusable-profile selection. The generic profile
consumes exact project compiler and migration decisions; exact supported 5.x,
6.x, 7.x, or another line may therefore be valid input. Current TypeScript
ownership and provisional maturity do not change. Standard qualification binds
an exact TypeScript 7.0.2 compiler because the maintained intended-state fixture
tests the Theme Forge destination, not because the generic profile selects it.
## APG76 CSS candidate authoring boundary

APG76 keeps candidate authoring separate from hardening under ADR 0042. The
authoring phase proposes an ADR, ships candidate surfaces and an APG-owned
fixture on a branch, and takes no integration owner; the hardening phase
reconstructs every expectation independently and holds the terminal decision.
A candidate's own coverage record, prose, and fixture manifest are navigation
and authoring provenance, never an oracle for the phase that reviews them.

## APG77 CSS repair checkpoint

APG77 exercises the three-round recovery lifecycle without reaching the
integration gate. The candidate and all immutable rounds are preserved, but
two High evidence defects remain after terminal review. ADR 0044 stays
Proposed; no CSS current owner is added and development remains 30/30/30,
14/16, and 28/1/29. Human authority owns any continuation, while rejection and
removal remain unperformed.

## APG77D CSS provisional owner

APG77D exercises ADR 0042's human-debt authority for exactly four Medium and
one Low qualification limitations and integrates CSS provisionally after all
ordinary product gates pass. The current owner set includes the CSS leaf,
specification, navigation coverage, target-first fixture, semantic scenarios,
known-debt register, catalog, projection, provisional maturity, route, project,
release, tests, and disposable rollback. Development is 31/31/31, 14/17, and
29/1/30. Stable maturity remains blocked by accepted Medium debt.

## APG79 JavaScript repair checkpoint

APG79 adds maintained candidate and qualification evidence on its branch but no
current integration owner. Three immutable corrections exhaust the default ADR
0042 budget; terminal review leaves two High and two Medium material defects.
ADR 0045 remains Proposed and the candidate is preserved
`repair-required-after-round-3`. Catalog, projection, maturity, route, project,
release, and test-inventory ownership remain the exact APG77D set.

## APG79A JavaScript repair checkpoint

APG79A adds one immutable correction and its terminal evidence, but no current
integration owner. Fresh review leaves five Medium defects, so ADR 0045 remains
Proposed and the candidate becomes `repair-required-after-apg79a`. Catalog,
projection, maturity, route, project, release, and test-inventory ownership
remain the exact APG77D set. Correction and checkpoint objects remain historical
evidence; they do not create current product ownership.


## APG79B JavaScript repair checkpoint

APG79B adds one immutable correction and terminal review evidence, but no
current integration owner. Fresh review leaves four unique Medium defects, so
ADR 0045 remains Proposed and the candidate becomes
`repair-required-after-apg79b`. Catalog, projection, maturity, route, project,
release, and test-inventory ownership remain the exact APG77D set. Correction
and checkpoint objects remain historical evidence and accept no JavaScript
debt.

## APG79C JavaScript decision and blocked integration

APG79C adds current human-accepted qualification-debt ownership for exactly
`JS-QD-001` through `JS-QD-004` while preserving all five CSS objects. That
decision does not create a JavaScript integration owner. A separate unaccepted
Medium source-identity defect blocks integration, so catalog, projection,
maturity, route, project, release, and test-inventory ownership remain the
exact APG77D set. ADR 0045 stays Proposed and the candidate remains
`repair-required-after-apg79b` and unintegrated.

## APG79E JavaScript current ownership

APG79E adds `JS-QD-005` to the canonical human-accepted qualification-debt
owner and installs the complete JavaScript current-owner set: catalog, relative
projection, provisional maturity, general route, project selection, current-
development release, focused tests, inventory, source-role association, known-
debt association, and rollback. ADR 0045 is Accepted with amendment and the
lifecycle is `provisionally-integrated-with-known-debt`. Corrected historical,
published, and active v0.4.0 exclude every APG78 through APG79E current-only
owner.
APG80 adds no current owner of any kind. The `nodejs-runtime-profile` candidate
is authored branch-only under Proposed ADR 0046 with the lifecycle
`authored-proposed-unintegrated`: no catalog row, relative projection, maturity
row, capability route, project selection, release owner, maintained test owner,
or test-inventory row is created. The candidate branch therefore carries 33
canonical leaves against 32 catalog rows and 32 projections, which is the
expected transitional shape for an uncataloged candidate rather than a defect.
Corrected historical, published, and active v0.4.0 exclude every APG80 path.

APG81H installs Node's complete current owner set: catalog, relative
projection, provisional maturity, general route, project selection,
current-development release, maintained tests, inventory, and independent
lifecycle ownership. Node lifecycle is `provisionally-integrated`, ADR 0046 is
Accepted with amendment, and the current surface is 33/33/33. Corrected
historical, published, and active v0.4.0 continue to exclude every APG80 and
APG81H current-only owner.

## APG86 GoMock and Vitest current ownership

APG86 installs the complete current owner set for `gomock-test-profile` and
`vitest-test-profile`: canonical leaves, catalog maturity rows, capability
routes, exact relative projections, default project selection, current release
policy, packaged metadata, public-safe scenarios, focused tests, inventory,
ADR 0048, evaluation, and exit. Both lifecycle states are
`provisionally-integrated` and both maturity rows are `provisional`.

Development is 35/35/35 and 14/21. The context-budget checker owns only the
six-name byte band and relational aggregate contract; phase topology and
historical deltas remain fixture and record evidence. Historical public and
active releases exclude APG86-only owners, and explicit project subsets remain
membership-stable.

## APG87 JSX and React current ownership

APG87 installs the complete current owner sets for `jsx-language-profile` and
`react-component-profile`: canonical leaves, catalog rows, exact relative
projections, general capability routes, provisional maturity, project default
membership, current-development release audit entries, packaged metadata,
boundary fixtures, focused tests, test inventory, ADR 0049, evaluation, and
exit. Both lifecycle states are `provisionally-integrated`.

The owners remain direct independently selectable siblings. JSX owns
library-independent syntax and transforms; React owns host-independent
component and render behavior. The project model creates no web-stack owner,
and reserved MDX/Astro routes are not installed owners. Development is
37/37/37 and 14/23; public and active v0.5.0 exclude APG87-only owners, and
explicit project subsets remain membership-stable.

## APG88 MDX and Astro current ownership

APG88 installs the complete current owner sets for `mdx-profile` and
`astro-profile`: canonical leaves, catalog rows, exact relative projections,
general capability routes, provisional maturity, project default membership,
current-development release audit entries, packaged metadata, boundary
fixtures, focused tests, test inventory, ADR 0050, evaluation, and exit. Both
lifecycle states are `provisionally-integrated`.

The owners are direct independently selectable siblings. MDX owns the
document/component seam and Astro owns framework/project/execution placement;
adjacent Markdown, JSX, React, TypeScript, JavaScript, and Node regions remain
independent. Development is 39/39/39 and 14/25; public and active v0.5.0 exclude
APG88-only owners, and explicit project subsets remain membership-stable.
