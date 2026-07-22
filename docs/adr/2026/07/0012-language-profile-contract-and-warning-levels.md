# ADR 0012: Language Profile Contract and Warning Levels

## Status

Accepted

## Date

2026-07-20

## Acceptance date

2026-07-21

## Acceptance authority

The human maintainer's APG18 assignment accepts this decision after bounded
contract correction, source calibration, one Python candidate, twenty-four
frozen scenarios, read-only real-code dogfood, and fresh independent review.
Acceptance authorizes the normative language-profile contract and one
provisional Python profile in private development. It does not authorize
another profile, source migration, root reduction, private skill removal,
public distribution, maturity promotion, publication, or APG19.

## Context

Language guidance currently appears in root instructions, private maintainer
standards, project-local documentation, and real repository practice. Some
guidance is a safe default, some depends on version or deployment context, some
marks a consequential design boundary, and some should stop an agent until
explicit authority or safety conditions are satisfied.

A flat list of "best practices" cannot express those differences. Strong words
such as "always" and "never" also tend to erase project compatibility and task
authority. APG needs a shared, accessible warning model that profiles can apply
without becoming linters, permissions systems, maturity scores, or substitutes
for repository policy.

## Decision

### Shared warning semantics

Every profile uses the following four textual levels:

| Level | Meaning | Required response |
| --- | --- | --- |
| `Green — routine` | Idiomatic, low-risk default when the profile trigger and task authority are already satisfied | Apply or recommend normally; verify with project-owned checks |
| `Yellow — caution` | Context-sensitive choice with meaningful version, compatibility, performance, or maintainability tradeoffs | Inspect local conventions and relevant evidence before choosing |
| `Orange — warning` | Consequential behavior, migration, concurrency, operational, compatibility, or rollback boundary | Continue only after an explicit local decision, bounded scope, rationale, rollback, and focused validation |
| `Red — crisis / stop` | Unsafe action, crisis growth, unresolved compatibility break, or authority boundary the profile cannot resolve | Stop; identify the safer design, accepted bounded exception, or governing authority required to continue |

The complete labels must always appear as text. Color presentation is optional
and may not be the only signal. Levels classify one coherent current decision
or proposed change, not the skill's maturity, the quality of an author, or the
overall risk of a repository. When several materially applicable signals
govern that decision, the highest justified level controls the response.

No level grants implementation, migration, destructive-action, publication,
exception, or successor-phase authority. Green is routine only inside
authority already supplied by the task and repository. Orange permits bounded
continuation only when the local decision is within that authority. Red stops
the unsafe action or proposed growth until its stated condition is resolved.

Stricter applicable repository policy controls. A repository may relax only a
profile default, not a superior safety, privacy, compatibility,
destructive-action, or task-authority rule. Relaxation requires an explicit
rationale accepted through the repository's governing decision process,
bounded scope, supporting evidence, focused validation, and rollback. When
authority or acceptance is unclear, retain the stricter response.

### Profile contract

Each language profile should contain:

1. a precise positive trigger and material non-triggers;
2. supported language, dialect, engine, or framework scope;
3. project-policy inputs such as version, compatibility, formatter, test,
   migration, deployment, and runtime constraints;
4. a compact Green/Yellow/Orange/Red table;
5. a procedure for applying the warnings to the current task;
6. explicit authority, safety, privacy, and destructive-action stops;
7. evidence expectations proportional to the highest relevant warning;
8. upstream and project-evidence provenance; and
9. maintenance, version-refresh, deprecation, and removal boundaries.

The normative operational contract is
[`docs/language-profile-contract.md`](../../../language-profile-contract.md). A
profile must also classify generated, vendored, protocol, migration, snapshot,
machine-produced, test, and legacy artifacts before applying hand-written-code
structural defaults. Classification never suppresses a semantic Red stop.

Structural warnings govern proposed growth rather than demanding retrospective
wholesale refactoring. An existing Red legacy artifact may receive the
smallest safe fix under repository authority when it adds no independent
responsibility and avoids meaningful growth. A major feature or new
responsibility remains Red until decomposition or an accepted architecture
exception resolves it. One metric does not mechanically select an architecture.

Profiles do not select project architecture, dependencies, formatters, test
frameworks, coverage thresholds, migrations, database access, live commands,
or deployment policy. They consume those decisions when present and identify
when they are missing.

### Language warning design

The following tables define the intended semantic coverage. They are design
inputs for later skill evaluations, not implemented instructions.

#### Python

| Level | Candidate guidance |
| --- | --- |
| `Green` | Prefer idiomatic, direct functions and ordinary data structures; keep parsing and serialization boundaries explicit; use project-supported typing and path APIs; preserve public imports unless change is authorized. |
| `Yellow` | Introduce dataclasses, protocols, async code, decorators, metaprogramming, or additional abstraction only when the local problem and supported Python versions justify them. |
| `Orange` | Change public APIs, serialization formats, concurrency models, packaging, interpreter support, or dependency boundaries only with compatibility and rollback evidence. |
| `Red` | Do not execute untrusted code, deserialize unsafe payloads, expose secrets or private paths, or suppress broad failures without an explicit safe contract. |

#### Bash

| Level | Candidate guidance |
| --- | --- |
| `Green` | Use a clear Bash shebang, quote expansions by default, prefer arrays for command construction, validate inputs at the edge, isolate external calls, and use temporary resources with cleanup. |
| `Yellow` | Treat strict mode, subshells, pipelines, traps, globbing, process substitution, and Bash-version features as contextual choices whose failure semantics must be tested. |
| `Orange` | Require explicit design and host-safe tests for privilege, parallelism, signal handling, machine-state mutation, complex parsing, or scripts whose state model is outgrowing shell. |
| `Red` | Do not use `eval` or concatenated untrusted commands, silently ignore command failures, expose secret-bearing expansions, or run destructive host actions without exact authority and target checks. |

#### Bats

| Level | Candidate guidance |
| --- | --- |
| `Green` | Use isolated fixtures, framework temporary directories, explicit status and output assertions, fake external commands, and behavior-focused test names. |
| `Yellow` | Verify helper loading, setup and teardown scope, skipped tests, platform assumptions, and parallel execution against the pinned Bats version. |
| `Orange` | Treat shared state, timing-sensitive tests, real network or daemon dependencies, coverage wrappers, and host-specific integration fixtures as explicit test-architecture decisions. |
| `Red` | Do not let tests mutate non-disposable host state, depend on real credentials or private data, or pass without an observable assertion or justified framework outcome. |

#### Go

| Level | Candidate guidance |
| --- | --- |
| `Green` | Keep packages focused; format with project-standard Go tooling; handle returned errors; wrap errors with useful context; give goroutines deterministic ownership and cancellation. |
| `Yellow` | Introduce interfaces, generics, reflection, channels, custom errors, or worker pools only when the concrete contract and supported Go version justify them. |
| `Orange` | Require lifecycle and race evidence for concurrency changes, public API or module changes, unsafe operations, cgo, or performance-specific allocation strategies. |
| `Red` | Do not discard material errors, leak goroutines or blocked sends, expose secrets in diagnostics, or use unsafe or host-mutating behavior outside explicit authority and tests. |

#### Ruby

| Level | Candidate guidance |
| --- | --- |
| `Green` | Prefer clear objects, modules, enumerable operations, explicit boundaries, idiomatic naming, and project-local test conventions; make mutation visible when it matters. |
| `Yellow` | Evaluate mixins, dynamic dispatch, blocks, refinements, DSLs, callbacks, and implicit returns for readability, version support, and local convention. |
| `Orange` | Require compatibility evidence for monkey patching, global state, runtime metaprogramming, public gem APIs, serialization changes, or dependency and interpreter changes. |
| `Red` | Do not evaluate untrusted Ruby, deserialize unsafe objects, leak secrets, silently rescue broad failures, or redefine core behavior without explicit bounded authority. |

#### Zsh

| Level | Candidate guidance |
| --- | --- |
| `Green` | Use a native Zsh shebang for Zsh code, quote expansions deliberately, localize variables and options, isolate external calls, and test startup or function behavior in controlled environments. |
| `Yellow` | Verify option state, array indexing, glob qualifiers, parameter expansion, autoloading, and emulation behavior against the supported Zsh version and invocation mode. |
| `Orange` | Treat startup-file changes, completion systems, global option mutation, privilege, signal handling, and machine bootstrap behavior as explicit operational design. |
| `Red` | Do not claim POSIX or Bash compatibility for native Zsh behavior, source untrusted content, expose secrets, or mutate host startup state without exact authority and rollback. |

#### ZUnit

| Level | Candidate guidance |
| --- | --- |
| `Green` | Use the required runner declaration, unique test names, isolated setup, explicit assertions, controlled script loading, and assertions over command state and output. |
| `Yellow` | Verify helper semantics, risky-test policy, path resolution, setup and teardown scope, skips, and framework behavior against the pinned ZUnit version. |
| `Orange` | Treat shared fixtures, timing, real startup files, platform commands, or integration with live shell state as explicit test-architecture decisions. |
| `Red` | Do not allow assertion-free false positives, mutate real shell configuration, consume credentials or private data, or execute destructive host actions in tests. |

#### Nix

| Level | Candidate guidance |
| --- | --- |
| `Green` | Prefer small declarative modules, explicit imports, clear option ownership, extracted source files, and static evidence that distinguishes known outputs from weak category inference. |
| `Yellow` | Verify language, nixpkgs, module-system, platform, and flake-version assumptions; treat overlays, overrides, string contexts, and embedded scripts as context-sensitive. |
| `Orange` | Require explicit authority and rollback for evaluation, dependency fetching, lock changes, derivation builds, store interaction, activation plans, or configuration migrations. |
| `Red` | Do not expose secrets in expressions or outputs, fabricate identities from weak evidence, perform host activation or destructive store actions without exact authority, or treat evaluation as read-only by default. |

#### PostgreSQL

| Level | Candidate guidance |
| --- | --- |
| `Green` | Use driver-supported parameters, explicit transaction boundaries, bounded result handling, sanitized diagnostics, and query plans for demonstrated performance questions. |
| `Yellow` | Verify server version, planner statistics, isolation, search path, indexes, prepared-plan behavior, and extension availability before depending on them. |
| `Orange` | Require explicit migration, lock, rollout, rollback, and realistic-data evidence for DDL, large updates, concurrency changes, partitioning, replication, or query-plan interventions. |
| `Red` | Do not expose credentials or private identifiers, concatenate untrusted SQL, access live data without authority, or run unbacked destructive DDL or data changes. |

#### SQLite

| Level | Candidate guidance |
| --- | --- |
| `Green` | Use parameters, explicit transactions for grouped writes, enabled and tested integrity constraints, bounded queries, and query-plan inspection for demonstrated performance questions. |
| `Yellow` | Verify SQLite and driver versions, journaling mode, busy handling, foreign-key configuration, in-memory behavior, and filesystem semantics for the deployment. |
| `Orange` | Require explicit migration, backup, concurrency, rollback, and compatibility evidence for schema rebuilds, WAL adoption, multi-process writes, file replacement, or large data changes. |
| `Red` | Do not concatenate untrusted SQL, store secrets unintentionally, delete or replace a database without exact backup and target authority, or assume network-filesystem and multi-writer safety. |

### Profile interaction

Bats may invoke the Bash profile when production Bash semantics are material;
ZUnit may invoke the Zsh profile when production Zsh semantics are material.
The framework profile remains the owner of test isolation, runner behavior, and
assertions. The language profile remains the owner of language semantics. The
router should select the most specific primary profile and load a companion
only when the task crosses both boundaries.

PostgreSQL and SQLite profiles are engine profiles rather than generic SQL
style guides. Shared relational guidance should remain in project policy or a
future demonstrated synthesis owner; the two profiles must not pretend their
locking, migration, planner, or deployment behavior is interchangeable.

## Alternatives considered

### Binary allowed and forbidden labels

Rejected. Most language choices are contextual rather than universally safe or
unsafe, and a binary model would collapse compatibility and operational risk.

### Three levels

Rejected. Combining contextual choices with consequential migration or
operational boundaries would make ordinary tradeoffs too alarming or serious
changes too easy to proceed with.

### Numeric severity scores

Rejected. Numbers imply precision and aggregation that the evidence does not
support. They also encourage scoring whole repositories instead of responding
to a concrete decision.

### Language-specific meanings for each color

Rejected. Shared semantics are necessary for predictable routing, review, and
migration. Profiles specialize examples and evidence, not the meaning of a
level.

### Treat Red as an absolute universal prohibition

Rejected. Some red items are absolute under superior safety rules; others are
authorized only by an explicit task and governing policy. The profile must stop
and identify the authority condition rather than claiming to own it.

### Encode the levels in deterministic lint rules

Rejected for v0.3 foundation. Most classifications require context and
judgment. Later tooling may check stable structure or explicit metadata but may
not claim semantic enforcement without separate evidence.

## Consequences

- Users receive a consistent response expectation across ten profiles.
- Profiles can distinguish idiomatic advice from decisions requiring a design
  or authority checkpoint.
- Text labels keep the contract accessible without relying on color.
- The warning model adds review and maintenance work; version-sensitive items
  require periodic source refresh.
- Overuse of Orange or Red would make profiles obstructive. Scenario evidence
  must include false-escalation and non-trigger cases.
- A profile cannot convert a warning level into permission, maturity, or a
  deterministic policy claim.

## Migration and rollback

APG18 changes no root or private source guidance. If the provisional Python
candidate becomes unsound, remove its canonical leaf, checked projection,
catalog and capability-map entries, and focused compatibility tests; restore
the prior eight-skill private-development shape and preserve this ADR,
evaluation, and exit history.

If the shared contract becomes unsound, supersede it through a later accepted
decision and disposition dependent profiles rather than rewriting accepted
history. Restore prior root or private guidance bytes only when a later,
separately authorized migration actually changed them.

Fresh-session application discovery and explicit-use smoke for the v0.3
catalog are intentionally deferred. APG23 owns aggregate readiness smoke, and
APG24 owns public-candidate and active-integration release-preparation smoke.
APG18 records no application-smoke observation.

## Deferred decisions

- implementation of Bash, Bats, Go, Ruby, Zsh, ZUnit, Nix, PostgreSQL, or
  SQLite profiles;
- future profile prose, upstream refreshes, licenses, and scenario suites;
- profile ordering, catalog presentation, and any optional metadata;
- deterministic structure validation;
- migration, maturity, distribution, or publication;
- whether later evidence justifies a shared relational or shell-family owner.
