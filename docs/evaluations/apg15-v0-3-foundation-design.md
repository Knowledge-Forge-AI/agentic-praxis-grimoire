# APG15 v0.3 Foundation Design

## Objective and authority

APG15 designs the v0.3 architecture for a public workflow router,
synthesis-first guidance migration, ten language profiles, and modular root
instructions. It may record proposed ADRs, evidence, risks, alternatives, and a
future roadmap. It does not implement a skill, change maturity, migrate active
guidance, replace private integration, or begin public release work.

[ADR 0011](../adr/2026/07/0011-v0-3-workflow-synthesis-and-modular-guidance-architecture.md)
owns the portfolio and migration proposal. [ADR
0012](../adr/2026/07/0012-language-profile-contract-and-warning-levels.md)
owns the profile and warning proposal. Both remain `Proposed`.

## Evidence basis

The design compares five evidence classes:

1. the accepted APG project model, six stable leaves, skill lifecycle,
   provenance policy, v0.2 roadmap, and APG14 terminal state;
2. the private APG workflow router currently used by Codex;
3. maintainer-authored private coding, test, security, database, and
   repository-operation guidance;
4. representative Python, Bash, Bats, Go, Ruby, Zsh, ZUnit, and Nix source and
   test practice in a maintainer repository, PostgreSQL schema and migration
   practice in RepoMap, and SQLite operational practice in a private workflow;
   and
5. primary upstream documentation for Python, Go, Ruby, Bash, Bats, Zsh,
   ZUnit, Nix, PostgreSQL, and SQLite inspected on 2026-07-20.

Public APG text uses independently written synthesis. No external or private
expression is copied or adapted. Exact private paths and source topology remain
in the publication-excluded APG15 evidence record. Before any candidate skill
is implemented, its phase must pin the relevant upstream versions, confirm
rights and notice duties, and freeze representative scenarios.

## Design disposition

APG15 recommends a capability portfolio rather than a Codex VC migration
portfolio:

- promote the private APG router into one public APG-owned routing skill;
- evaluate one cross-cutting guidance-synthesis skill;
- retain ten independently triggerable language or framework profiles as
  candidates;
- keep warning semantics in one architectural owner and examples in each
  profile;
- keep exact versions, commands, layout, migrations, deployment, and test
  policy repository-local; and
- keep personal, machine-specific, private-repository, and installed-tool
  guidance in Codex VC.

This design produces a candidate inventory of twelve new skills. It does not
declare any candidate necessary, implemented, accepted, stable, or releasable.

## Ownership matrix

| Concern | Normative owner | Consumers | Explicit exclusions |
| --- | --- | --- | --- |
| Task authority, instruction precedence, privacy, destructive actions, and universal repository stops | Root `AGENTS.md` and current task | Every skill and actor | Language procedure and private machine details |
| Selection among APG process leaves | `agentic-praxis-grimoire-workflow` candidate | Tasks needing APG routing | Leaf procedure, dispatch, workflow chaining, action authority |
| Classification and modularization of mixed guidance | `synthesizing-repository-guidance` candidate | Root, policy, profile, and private-overlay migrations | Writing arbitrary policy or presuming adoption |
| Warning-level meaning and profile contract | ADR 0012 and future core profile guide | All language profiles and reviewers | Language-specific examples and project permission |
| Language semantics and language-specific warning examples | Matching language profile candidate | Implementation, design, debugging, and review tasks in that language | Exact project versions, commands, frameworks, and compatibility promises |
| Test-framework isolation and assertion semantics | Bats or ZUnit profile candidate | Matching framework tasks | Production Bash or Zsh semantics unless separately material |
| Exact test, coverage, formatter, linter, migration, runtime, and deployment policy | Target repository | Profiles and APG process leaves | Universal APG defaults |
| Skill creation, correction, support, maturity, deprecation, and removal | Skill authoring and maintenance guide | Maintainers and future phases | Automatic authority or semantic enforcement |
| Source identity, derivation, rights, and observed evidence | Provenance and evaluation records | ADRs, maintainers, reviewers | Normative procedure |
| Stable structural invariants | Deterministic tooling when separately adopted | Catalog and projection maintenance | Warning classification or semantic quality |
| Personal preferences, private topology, and installed-tool state | Codex VC or another private overlay | The maintainer's Codex environment | Public APG dependencies |
| Historical phase outcome | Exit record | Future roadmap and review | Prospective authority |

## Candidate portfolio dependencies

```text
accepted APG leaf library
        |
        v
public APG workflow router
        |
        v
guidance-synthesis procedure
        |
        v
shared profile contract
        |
        +--> Python
        +--> Bash ----> Bats
        +--> Go
        +--> Ruby
        +--> Zsh -----> ZUnit
        +--> Nix
        +--> PostgreSQL
        +--> SQLite
        |
        v
bounded AGENTS.md migration and cross-repository dogfood
```

The arrows express evaluation and migration dependencies, not mandatory runtime
chaining. Language profiles remain independently removable. Bats and ZUnit may
consume their production-language companion only when both boundaries are
material to the task.

## AGENTS.md migration strategy

### Inventory

Split guidance into independently classifiable units. Record applicability,
authority, privacy, source rights, current owner, overlap, and project-specific
parameters. Do not start from a desired skill count.

### Synthesize

Compare each unit against existing APG leaves, native agent capability,
language profiles, core policy, and repository-local policy. Retain the
smallest owner that preserves the behavior. Use independently written APG text
and keep private expression out of public artifacts.

### Shadow

Add a concise route from root instructions to the new public owner while the
source guidance remains authoritative. Test discovery, positive behavior,
non-triggers, project overrides, and missing-owner failure behavior.

### Cut over

Only a separately authorized migration phase may remove duplicated root or
private guidance. The migration must prove that every supported context has an
equal or stronger owner and that the prior instruction bytes can be restored.

### Reconcile

Remove stale routes, update provenance and ownership documentation, run
repository and skill-library checks, and preserve historical records. Do not
delete private guidance whose personal or machine-specific function remains.

## Codex VC retention dispositions

| Guidance family | Disposition | Reason |
| --- | --- | --- |
| General idioms, explicit boundaries, input validation, error visibility, and language-specific risk patterns | Synthesize into profiles when evidence supports them | Reusable problem; expression and exact defaults still need independent ownership |
| Exact language-selection hierarchy | Keep private | Maintainer preference, not a universal procedure |
| File-size thresholds and abstraction preferences expressed as personal defaults | Keep private or project-local | Subjective calibration depends on codebase and team |
| Exact coverage percentage, test naming, directory layout, and preferred frameworks | Keep private or project-local | Project policy with ecosystem-specific variability |
| Liquibase preference and personal migration naming | Keep private or project-local | Tool and naming choice is not shared PostgreSQL or SQLite semantics |
| macOS bootstrap ordering and Nix-managed Bash or Zsh selection | Keep private | Machine and operating-system workflow |
| Local paths, ports, executables, user roots, graph names, and integration state | Keep private | Confidential or machine-scoped operational data |
| RepoMap graph maintenance and database lifecycle authority | Keep private or RepoMap-local | Product-specific operational policy |
| Plugin, MCP, connector, and host-escalation routing | Keep private | Installed-tool and host capability state |
| Personal security product preferences and trusted-terminal assumptions | Keep private | Personal threat model and deployment choice |
| Persona, artifact tone, and collaboration preferences | Keep private | User interaction policy, not repository procedure |

## Proposed APG15+ roadmap

| Phase | Scope | Entry condition | Exit boundary |
| --- | --- | --- | --- |
| APG15 | Record v0.3 architecture, inventory, ownership, migration, warning model, risks, and roadmap | Human-authorized design task | Proposal delivered; no implementation or acceptance |
| APG16 | Evaluate and optionally implement only the public APG workflow router | ADR 0011 accepted or bounded correction approved | Router disposition; no private cutover, profiles, maturity, or release |
| APG17 | Evaluate and optionally implement `synthesizing-repository-guidance` | APG16 accepted and routing behavior stable | Synthesis disposition and one bounded migration-plan dogfood; no root cutover |
| APG18 | Establish the accepted profile guide and evaluate the Python profile as the first vertical slice | ADR 0012 and APG17 accepted | One profile disposition; no automatic family rollout |
| APG19 | Evaluate Bash and Bats, then Zsh and ZUnit as two paired but individually dispositioned families | APG18 demonstrates viable profile shape | Four individual dispositions; no shared shell skill unless evidence requires it |
| APG20 | Evaluate Go and Ruby profiles with independent runtime and compatibility scenarios | Accepted profile shape and source snapshots | Two individual dispositions |
| APG21 | Evaluate Nix, PostgreSQL, and SQLite profiles with stronger operational, migration, and stop evidence | Prior profiles show warning calibration is usable | Three individual dispositions; no live mutation authority |
| APG22 | Dogfood the router, synthesis, and retained profiles across APG and at least one additional repository; propose bounded root-guidance cutovers | Candidate set is implemented and independently usable | Migration and overlap dispositions; personal Codex VC guidance preserved |
| APG23 | Review each new skill's evidence and v0.3 readiness without presuming maturity | APG22 complete | Individual maturity or deferral proposals; no publication |
| APG24 | Build and publish a v0.3 candidate only if separately authorized under accepted release policy | Accepted readiness disposition and explicit publication authority | Release or truthful stop; outside APG15 authority |

Every phase after APG15 remains unauthorized. Family phases must retain
per-skill stop, correction, rejection, rollback, and review dispositions rather
than treating a family as one maturity unit.

## Recommended APG16

APG16 should be the smallest architecture-valid vertical slice: public router
promotion only. It should compare ordinary selection, the current private
router, and the proposed public candidate against frozen scenarios covering:

- each of the six existing positive triggers;
- ambiguous overlap between two leaves;
- simple tasks that require no APG leaf;
- review as a real trigger and as a material non-trigger;
- delegation absent or unauthorized;
- a missing or stale canonical leaf;
- a stale catalog or maturity statement; and
- attempted mandatory chaining or invented action authority.

If retained, APG16 may add one canonical leaf, one discovery projection, one
catalog row, required structural checks, public provenance, evaluation, and an
exit record. It should not edit the six current leaves, change any maturity,
remove the private router, migrate root instructions, implement synthesis or
profiles, change distribution tooling, or publish a release.

## Risks and mitigations

| Risk | Consequence | Design mitigation |
| --- | --- | --- |
| Catalog expansion | Discovery noise and higher maintenance cost | Add candidates only through the accepted new-skill threshold; measure non-trigger and overlap behavior |
| Router becomes a mandatory workflow | Over-triggering and duplicated procedures | Router owns selection only; leaves retain procedure; explicit no-chain cases |
| Warning inflation | Ordinary work repeatedly stops at Orange or Red | Freeze false-escalation cases and require level-specific rationale |
| Color ambiguity or inaccessibility | Inconsistent interpretation | Text labels and shared semantics are mandatory; color is optional presentation |
| Stale language advice | Incorrect version or ecosystem assumptions | Pin upstream snapshots per implementation phase and record refresh triggers |
| Private guidance leakage | Public paths, identity, or preferences become dependencies | Two-level provenance and `keep-private` disposition; public text remains independently understandable |
| Project policy conflict | Profiles override established compatibility or commands | Repository policy supplies parameters and may strengthen levels; profiles do not invent exact policy |
| Duplicate shell or database guidance | Conflicting owners | Explicit language/framework and engine boundaries; overlap scenarios before retention |
| One-to-one migration pressure | Skill boundaries mirror private files | Synthesis skill outputs destination dispositions; no source artifact receives presumptive public ownership |
| Premature maturity or release | Design labels are treated as adoption | Both ADRs remain Proposed; later phases require individual evidence and authorization |

## Alternatives summary

APG15 considered retaining the private router, creating a mandatory workflow,
migrating Codex VC artifacts one for one, placing all language guidance in one
skill or root instructions, using binary or numeric warnings, and enforcing the
warning model mechanically. These options were rejected because they either
leave a public ownership gap, over-trigger, confuse source with capability,
load irrelevant context, collapse material distinctions, or claim deterministic
semantics that remain judgment-dependent.

## Completion boundary

APG15 is complete when the proposed ADRs, public evaluation, private source
classification, roadmap, provenance, and exit accurately describe the design;
all changed documentation passes repository checks; the worktree contains no
skill, maturity, distribution, or release implementation; and APG16 remains an
external decision.

## Subsequent external disposition

The maintainer accepted APG15 as `Complete — v0.3 foundation architecture
proposed`, accepted ADR 0011's capability-oriented, synthesis-first
architecture through APG16, and separately authorized APG16 as the public
router vertical slice. ADR 0012 remains `Proposed`. The disposition authorizes
no other v0.3 phase automatically.
