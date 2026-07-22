# ADR 0016: Nix and Relational-Engine Profile Ownership

## Status

Accepted

## Date

2026-07-21

## Acceptance authority

The human maintainer's APG20A-to-APG21 assignment authorizes this ownership decision after
current primary-source research, independent threshold and semantic analyses,
private-guidance synthesis, shared design criticism, frozen scenarios,
read-only dogfood, focused tests, and independent resulting-tree review. It
retains PostgreSQL and SQLite while deferring Nix. It does not authorize Nix
evaluation or activation, database access or mutation,
public release, application smoke, or APG22.

## Context

Nix needs language- and module-specific treatment of evaluation, purity,
derivations, the store, sources, overlays, locks, embedded shell, and activation
risk. PostgreSQL and SQLite share SQL vocabulary but differ materially in MVCC,
locking, concurrency, DDL, migration, backup, filesystem, and failure behavior.
A generic infrastructure or SQL owner would erase those boundaries and invite
unsafe transfer of operational assumptions.

ADR 0011 reserved provisional PostgreSQL and SQLite language-profile names.
APG21 resolves their canonical implementation names to
`postgresql-database-profile` and `sqlite-database-profile`; ADR 0011 remains
historical architecture evidence rather than the current naming owner.

## Decision

### Separate owners

- The reserved `nix-language-profile` owner would own Nix language, module,
  derivation, evaluation,
  purity, store, fetch, option, overlay, flake, shell-snippet, and activation-
  risk judgment.
- `postgresql-database-profile` owns PostgreSQL dialect and engine semantics,
  MVCC, transactions, locks, DDL, migrations, functions, procedures, triggers,
  security, backup/restore, replication, and operational stops.
- `sqlite-database-profile` owns SQLite dialect and engine semantics,
  transaction modes, single-writer behavior, file ownership, locking, rollback
  journals, WAL, schema rebuilds, pragmas, backup, extensions, and operational
  stops.
- No generic SQL profile, generic database-operations skill, or generic
  infrastructure profile is adopted.

PostgreSQL and SQLite remain separate because their concurrency, migration,
backup, restore, durability, security, and deployment boundaries differ
materially. Similar threshold bands are independent engine calibrations, not a
shared SQL default.

### Authority and project ownership

Exact versions, commands, drivers, ORMs, migration and schema tools,
deployment, credentials, environments, backup mechanisms, live facts, and
operational authority remain repository- or task-owned. Profiles classify and
recommend. They do not evaluate, fetch, build, activate, or mutate a Nix system
and do not open, query, migrate, back up, restore, maintain, replace, or delete
a database.

The profiles pair with existing process owners. Significant design, dependent
planning, implementation evidence, and acceptance review remain owned by their
corresponding APG process skills.

### Warning and artifact contract

All three profiles follow ADR 0012. Structural thresholds mainly govern
proposed growth in maintained hand-written files, expressions, modules,
derivations, queries, migrations, functions, and procedures. Generated,
vendored, lock, registry, snapshot, dump, schema, fixture, historical migration,
test-corpus, and machine-produced artifacts require classification. Their
producer and historical ownership prevent automatic hand refactoring, but
classification never suppresses semantic Red.

One Red remains Red. Three materially coupled Yellow signals normally justify
Orange. Two materially coupled Orange signals affecting one owner are
presumptively Red unless accepted cohesive evidence supports Orange. Existing
Red legacy may receive only the smallest safe fix without meaningful growth or
new responsibility. Repository policy may strengthen defaults and may relax
only a profile default through accepted scoped rationale, evidence, validation,
growth limits, and recovery. Superior safety, privacy, security, integrity,
destructive-action, and authority rules remain controlling.

Each retained profile begins provisional. Application smoke remains deferred
to APG23 and APG24.

## Alternatives considered

### One generic infrastructure profile

Rejected. It would combine unrelated language, engine, deployment, and
operational authority concerns.

### One generic SQL profile

Rejected. Shared syntax does not establish shared engine behavior.

### One relational profile with engine appendices

Rejected. The appendices would own most consequential behavior and routing
would still need the engine identity.

### Nix only

Rejected. Current PostgreSQL and SQLite evidence supports bounded independent
owners.

### Separate Nix, PostgreSQL, and SQLite owners

Accepted.

### Embed database behavior in project policy only

Rejected as the universal architecture. Projects retain exact policy, while
reusable engine semantics and stop boundaries benefit from separate profiles.

### Defer an engine with insufficient evidence

Accepted and applied to Nix after its corrected candidate exposed a second
material scenario contradiction.

## Consequences

Private development contains sixteen canonical skills and projections, six
stable process rows, ten provisional rows, and fifteen routable non-router
capabilities. The six v0.2 managed defaults, schema version 1, public v0.2.0,
and active integration remain unchanged.

The separation improves routing precision and safety at the cost of three
independent source-refresh and calibration obligations. Nix remains a reserved
owner with `deferred-material-defect` evidence and no operational leaf. The
decision does not claim comparative superiority or standardize project tooling.

## Migration and rollback

APG21 migrates or removes no root or private guidance. Each retained database
profile is independently reversible by removing its canonical leaf, relative
projection, catalog and capability-map row, known-unmanaged entry, and focused
tests while retaining this ADR, evaluation, exit, and provenance history. The
Nix candidate leaf, projection, route, known-unmanaged entry, and focused leaf
contract test are not retained. Removing either database profile does not
create a generic SQL owner. Private source restoration remains available until
any separately authorized cutover is accepted.

Public release, active integration, maturity promotion, application smoke, and
APG22 remain separate decisions.

## Subsequent APG21A disposition

APG21A preserves this ownership decision while correcting the Nix candidate's
structural/semantic merge contradiction and retaining the reconstructed Nix
leaf provisionally. Current development contains seventeen canonical skills
and projections, six stable rows, eleven provisional rows, and sixteen
routable non-router capabilities. One bounded PostgreSQL false-escalation
correction changes no engine ownership or live-operation authority. The six
v0.2 managed defaults, schema version 1, public v0.2.0, and active integration
remain unchanged.
