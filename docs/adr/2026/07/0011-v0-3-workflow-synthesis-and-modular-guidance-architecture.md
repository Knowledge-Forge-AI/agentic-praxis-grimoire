# ADR 0011: v0.3 Workflow, Synthesis, and Modular Guidance Architecture

## Status

Accepted

## Date

2026-07-20

## Acceptance authority

The human maintainer accepted the capability-oriented, synthesis-first
architecture through APG16 and authorized the public-router vertical slice.
Acceptance does not authorize guidance synthesis, a language profile, root
instruction migration, private-router cutover, maturity promotion, release, or
any phase after APG16.

## Context

APG v0.2.0 contains six stable, independently triggerable repository-process
skills. A private Codex integration skill currently routes tasks to those six
leaves, but it is machine-scoped, describes the earlier provisional catalog,
and depends on a private projection layout. APG has no public owner for routing
among its own leaves.

Codex VC also contains broad engineering guidance, project-specific skills,
machine policy, and maintainer preferences. Migrating those artifacts one for
one would confuse private integration with reusable procedure, duplicate
project policy, and create skills whose boundaries follow source files rather
than coherent problems. The root instruction file has accumulated reusable
language guidance alongside genuinely global authority, safety, privacy, and
machine-operation rules.

The v0.3 foundation therefore needs three distinct capabilities:

1. a public APG workflow router that selects an existing leaf without making a
   mandatory chain;
2. a synthesis procedure that classifies guidance from several sources into
   the smallest correct owner; and
3. independently triggerable language profiles that apply only when work in a
   supported language needs specialized judgment.

The profile warning contract is separately proposed in
[ADR 0012](0012-language-profile-contract-and-warning-levels.md).

## Decision

### Portfolio shape

The proposed v0.3 portfolio adds candidates by capability, not by source
artifact:

| Candidate family | Candidate owner | Purpose | Default disposition |
| --- | --- | --- | --- |
| APG routing | `agentic-praxis-grimoire-workflow` | Select the most specific applicable APG leaf and report material non-triggers or integration faults | Recommend APG16 evaluation |
| Guidance synthesis | `synthesizing-repository-guidance` | Classify dense or duplicated instructions into root rules, existing skills, language profiles, project policy, evidence, private overlays, or rejection | Evaluate after the router |
| Language profiles | Ten `<language>-language-profile` leaves | Supply language- or framework-specific judgment and warning levels after a matching language trigger | Candidate inventory only; each requires separate evidence |

No Codex VC skill receives a presumptive public counterpart. Existing APG
leaves remain unchanged unless a future phase demonstrates a specific gap in
their current procedure.

### Public workflow promotion

The public router preserves the generalized capability-selection function
while removing private integration assumptions. Its accepted contract is:

1. establish task authority, repository instructions, accepted decisions, and
   project-owned verification policy;
2. identify whether one APG leaf has the most specific satisfied trigger;
3. select only that leaf by default and read it completely;
4. combine it with separately applicable domain guidance;
5. use the review leaf only when review, disposition, or a completion claim is
   actually required; and
6. report material non-triggers, missing canonical content, and the reached
   authority boundary when they affect the outcome.

The router is optional discovery and selection guidance for ambiguity, routing
audit, or capability-health diagnosis. Clear native selection and explicit
applicable operator selection remain router non-triggers. The router does not
authorize action,
dispatch workers, create a workflow engine, require leaf chaining, duplicate
leaf procedures, or replace native harness behavior. It should retain the name
`agentic-praxis-grimoire-workflow` so the public and private discovery concepts
converge without an alias migration. A future implementation replaces the
private copy only after public-source integration and rollback are separately
validated.

APG16 implements the maintenance boundary as a schema-version-1, skill-local
capability map. The map contains only public names, capability classes, and
concise trigger summaries; excludes the router itself; and is covered by a
focused exact-catalog test. A catalog addition without an explicit map
disposition fails that test. The map is selection metadata, not a second owner
for leaf procedure.

Duplicate names are not a precedence mechanism. A routing claim that depends
on source must stop until the client supplies identifying scope or path
evidence. The public router may coexist with the private router, but APG16 does
not replace, redirect, or remove the private integration.

### Synthesis-first migration

`synthesizing-repository-guidance` is the preferred reusable owner when an
instruction corpus, root file, or private standards collection needs
modularization. Its proposed output is a disposition map, not rewritten policy.
For each guidance unit it should record:

- the concrete problem and applicability scope;
- source and rights status;
- current and proposed normative owner;
- `retain`, `synthesize`, `route`, `defer`, `reject`, or `keep-private`;
- conflict and override behavior;
- acceptance evidence and migration dependency; and
- rollback or restoration boundary.

The skill must prefer an existing owner, independently written synthesis, and
the smallest stable boundary. It must not treat repetition, source authority,
or a private artifact boundary as proof that a public skill is needed.

### Modular AGENTS.md migration

Root `AGENTS.md` remains the owner for concise instructions that apply to
nearly all repository work. Reusable guidance migrates only after a future
phase demonstrates its trigger and owner:

| Guidance class | Proposed owner |
| --- | --- |
| Authority, instruction precedence, privacy, destructive-action, and repository-wide stop rules | Root `AGENTS.md` |
| APG leaf selection | Public APG workflow router |
| Cross-source classification and modularization | Guidance-synthesis skill |
| Language-specific judgment and warning examples | Matching language profile |
| Exact commands, versions, frameworks, coverage gates, paths, deployment, and repository layout | Repository-local policy |
| Architecture rationale and warning semantics | Core APG documentation and ADRs |
| Source identity, license, derivation, and observed behavior | Provenance and evaluation records |
| Machine paths, installed-tool state, personal defaults, and private repository operations | Codex VC or another private overlay |

Migration is subtractive only after replacement discovery and behavior are
verified. During transition, root instructions may route to the new owner but
must not restate its procedure. A source rule is removed only when every
supported context has an equal or stronger owner and rollback can restore the
prior instruction bytes.

### Personal and private guidance boundary

The following classes remain outside public APG unless later evidence supports
an independently generalizable problem:

- local filesystem paths, usernames, hostnames, ports, browser executables,
  tool caches, and active integration state;
- personal language-selection preferences and subjective size thresholds;
- exact personal coverage percentages, migration naming schemes, preferred
  database or cloud products, and framework defaults;
- macOS bootstrap order, Nix-managed shell preferences, and machine activation
  commands;
- private RepoMap graph maintenance, storage, backup, and host-escalation
  registries;
- plugin, MCP, connector, and installed-tool routing for one Codex home;
- personal chat persona, artifact tone preferences, and flow-state support;
- private memory topology and user-authored canon boundaries; and
- project-specific test lanes, report commands, release procedures, and
  destructive-operation approvals.

General safety ideas may inform APG-native synthesis, but private expression,
local topology, and personal policy do not become public dependencies.

### Candidate skill inventory

The proposed inventory contains twelve new candidates:

| Candidate | Trigger boundary | Relationship |
| --- | --- | --- |
| `agentic-praxis-grimoire-workflow` | A task needs routing among APG's canonical leaves or an explanation or audit of that routing | Public synthesis of the private router; no leaf duplication |
| `synthesizing-repository-guidance` | A dense, duplicated, or mixed-scope guidance corpus needs owner and migration dispositions | Cross-cutting synthesis; not a general writing skill |
| `python-language-profile` | Python implementation, review, or design needs language-specific judgment beyond repository policy | Consumes ADR 0012 warning contract |
| `bash-language-profile` | Bash-specific script work needs Bash semantics or safety guidance | Does not own portable POSIX shell policy |
| `bats-language-profile` | Bats test design or review needs framework-specific isolation and assertion guidance | Complements, does not duplicate, Bash profile |
| `go-language-profile` | Go work needs package, error, concurrency, context, or performance guidance | Defers exact tooling and versions to the repository |
| `ruby-language-profile` | Ruby work needs language-specific object, exception, mutation, or test guidance | Does not prescribe one framework |
| `zsh-language-profile` | Native Zsh script or function work needs Zsh option, expansion, or startup guidance | Does not claim POSIX compatibility |
| `zunit-language-profile` | ZUnit test work needs framework-specific isolation and assertion guidance | Complements, does not duplicate, Zsh profile |
| `nix-language-profile` | Nix expression, module, flake, or evaluation design needs declarative or effect-boundary guidance | Does not authorize evaluation, builds, or host activation |
| `postgresql-language-profile` | PostgreSQL SQL, schema, transaction, concurrency, or query-plan work needs engine-specific guidance | Does not authorize migrations or live access |
| `sqlite-language-profile` | SQLite schema, transaction, concurrency, journaling, or query-plan work needs engine-specific guidance | Does not universalize WAL or one deployment model |

The inventory is not an implementation commitment. Every candidate must pass
the accepted new-skill threshold, including positive, non-trigger, edge or stop,
rights, removal, and independent-review evidence.

## Alternatives considered

### Keep the workflow router private

Viable for one machine but rejected as the preferred architecture. APG's public
users otherwise receive six leaves without APG-owned selection guidance, and
the private copy can drift from the public catalog.

### Add a mandatory end-to-end workflow

Rejected. The six stable leaves have distinct triggers and material
non-triggers. Mandatory design, planning, implementation, debugging, review, or
delegation steps would over-trigger and contradict accepted APG behavior.

### Migrate each Codex VC skill or standards document into APG

Rejected. Source-file boundaries do not establish reusable capability
boundaries. This option would publish machine policy, duplicate existing APG
owners, and create a large maintenance surface without independent evidence.

### Put all language guidance in one large skill

Rejected. A single trigger would either over-trigger for every language or
require an internal router as complex as the catalog. Independent language
profiles are removable, testable, and discoverable without loading unrelated
guidance.

### Put all language guidance in root instructions

Rejected. Routine loading would impose irrelevant context on most tasks and
would mix reusable procedure with project and machine policy.

### Publish the private standards largely unchanged

Rejected. They combine personal defaults, local paths, project layout,
framework choices, and broadly reusable engineering ideas. Public APG requires
independent synthesis and a public-safe owner for each retained practice.

## Consequences

- The public catalog may eventually grow from six to eighteen skills, but only
  through separately evidenced additions.
- The router becomes the optional ambiguity and audit entry point while leaves
  remain the procedure owners.
- Guidance migration becomes an explicit classification exercise rather than
  a source-copy project.
- Language profiles share one warning contract but retain independent triggers,
  content, evidence, and removal paths.
- Root instructions can become smaller without losing authority, safety, or
  local policy.
- Codex VC remains a supported private overlay rather than a backlog that APG
  is expected to absorb.
- A larger catalog increases discovery, overlap, and maintenance risk; later
  phases must measure those costs rather than assuming modularity is free.

## Migration and rollback boundaries

1. Implement and evaluate the public router before removing or redirecting the
   private router.
2. Implement the synthesis procedure before migrating broad root guidance.
3. Introduce profiles in bounded families with explicit overlap tests.
4. Keep source instructions until discovery and representative behavior pass
   from the intended public source.
5. Remove duplicated source text only in a separately authorized migration
   phase with exact restoration evidence.
6. Roll back a candidate by restoring prior instruction bytes, catalog and
   projection state, and private integration source while preserving ADR,
   evaluation, and exit history.

No migration changes the six existing leaves' maturity. New skills receive no
maturity disposition merely because this proposal names them.

## APG16 implementation scope

APG16 evaluates and implements the public
`agentic-praxis-grimoire-workflow` router as one new-skill vertical slice. It
freezes routing, non-trigger, stale-catalog, missing-leaf, and no-chain
scenarios; compares the private behavior and public candidate; adds only the
canonical leaf, discovery projection, catalog row, provenance, tests, and phase
records required by the accepted lifecycle; and leaves all language profiles,
guidance synthesis, root-instruction migration, maturity, private integration
replacement, and publication for later authorization.

## Deferred decisions

- final wording or implementation of guidance synthesis or any language
  profile;
- candidate maturity and release inclusion;
- deterministic support or catalog changes needed for profile metadata;
- private router removal and Codex VC migration;
- release version, release cadence, or public publication; and
- any profile beyond the candidate inventory and warning design.
