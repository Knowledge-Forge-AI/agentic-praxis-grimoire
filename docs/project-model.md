# APG Project Model

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

The [skill authoring and maintenance guide](skill-authoring-and-maintenance.md)
is the normative owner for applying this general lifecycle to new skills,
frontmatter or procedure corrections, support additions, maturity-only
dispositions, deprecation, and removal. The guide does not redefine the general
destination model or grant action authority.

## Modularity and skill categories

An APG skill is the smallest independently triggerable procedure with a coherent
purpose and validation surface. Skills do not repeat repository rules or embed
unrelated project standards. Shared behavior becomes a separate skill or helper
only after repeated use demonstrates a stable boundary.

No category taxonomy is adopted. Catalog labels may help discovery later, but
real skills must test those boundaries before labels become directories or
routing rules. A cross-cutting skill retains one canonical implementation and
may receive several catalog labels if evaluation supports them.

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

Record mechanics are owned by the
[phase and record identity guide](phase-and-record-identity.md),
[ADR index](adr/README.md), and [exit-record index](status/README.md). Phase IDs
are semantic and globally unique; ADR and exit sequences are independently
allocated. Current owners, evaluations, exits, and indexes are finalized before
commit, while exact Git evidence remains in post-commit managed reports. The
direct-child skill shape is documented
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
