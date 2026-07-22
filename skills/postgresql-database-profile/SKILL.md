---
name: postgresql-database-profile
description: Use when PostgreSQL-specific judgment is material to SQL, schemas, MVCC, transactions, locks, DDL, migrations, routines, triggers, security, backup and restore, replication, maintenance, or warning and crisis thresholds beyond repository policy.
---

# PostgreSQL Database Profile

## Core principle

Apply PostgreSQL-specific judgment only when it is material. Establish the
supported PostgreSQL majors and minor releases, driver and migration policy,
schema and compatibility ownership, environment evidence, protected-data
boundary, and task authority before recommending a construct or response. Use
the highest justified `Green — routine`, `Yellow — caution`,
`Orange — warning`, or `Red — crisis / stop` response for one coherent current
decision.

Keep transaction, lock, privilege, data-movement, and recovery ownership
explicit. Static structure warns about proposed growth; it cannot establish
live relation size, blocking, write rate, replication state, or restore
success. This provisional profile classifies and recommends and does not grant
database access or mutation authority.

## Do not use

Do not use this profile for:

- a comment, typo, formatting-only edit, or ordinary parameterized query with
  no material PostgreSQL-specific judgment;
- generic design, planning, implementation, debugging, or review procedure;
- selecting a PostgreSQL version, driver, ORM, migration framework, schema
  tool, formatter, backup product, replication topology, or deployment policy;
- authorizing a connection, query, migration, backup, restore, maintenance,
  role change, extension, or destructive action;
- automatically rewriting historical migrations or existing Red owners;
- treating generated schemas, dumps, snapshots, fixtures, extension scripts,
  or framework output as maintained source before classification; or
- inferring production row counts, relation size, lock duration, transaction
  age, WAL volume, lag, privileges, RPO/RTO, or restore duration from SQL text.

## Procedure

1. Establish task authority, repository instructions, supported PostgreSQL
   versions, driver parameter semantics, schema and migration ownership,
   transaction and deployment policy, live environments, protected data,
   backup and restore requirements, and rollback or forward-correction bounds.
2. Classify each artifact as maintained query, schema, migration, routine,
   test, legacy, generated, dump, snapshot, fixture, extension script,
   framework output, or other machine-produced material. Classification never
   suppresses semantic Red.
3. Use the repository's configured PostgreSQL-aware parser when present and
   record its name, version, settings, and supported dialect. Otherwise use the
   fallback lexical rules below. Do not connect to a database to obtain a
   static count.
4. Measure migration directions separately and the current and projected
   owner. Mark dynamic or generated SQL unresolved when its possible structure
   cannot be established statically.
5. Assign the highest justified response. Three materially coupled Yellow signals
   normally justify Orange. Two materially coupled Orange signals over one
   owner are presumptively Red unless accepted cohesive evidence supports
   Orange. One Red signal remains Red. Correlated size, decision, and ownership
   measures are not independent escalation evidence.
6. Proceed proportionally for Green; inspect policy and evidence for Yellow;
   require an explicit local decision, bounded target, rollout, truthful
   recovery or forward correction, and focused validation for Orange; stop Red
   growth or unsafe behavior pending decomposition, an accepted bounded
   exception, or governing authority.
7. Inspect parameterization, MVCC, isolation, locks, DDL and rewrite behavior,
   constraints, indexes, backfills, routines, triggers, RLS, privileges,
   extensions, partitioning, replication, vacuum, backup, restore, protected
   data, and live authority independently of structure.
8. Pair separately with the applicable process capability.
   `implementing-with-test-discipline` may remain primary for an authorized
   behavior or migration change; `reviewing-and-verifying-repository-work` may
   remain primary for acceptance review. This profile supplies PostgreSQL
   judgment without silently invoking either.
9. Preserve stricter project policy. Relax only a profile default through an
   accepted scoped rationale, evidence, validation, growth limit, and rollback;
   never relax superior injection, security, privacy, integrity, destructive-
   action, or authority stops.
10. Report the level, structural and semantic signals, artifact class, version
    and parser basis, known and unknown live facts, required response, focused
    validation, and recovery or decomposition boundary.

### Structural threshold contract

These defaults apply mainly to proposed growth in maintained hand-written
PostgreSQL SQL, migrations, functions, and procedures. They are review signals,
not planner, lock, runtime, or migration-safety claims.

| Signal | Green — routine | Yellow — caution | Orange — warning | Red — crisis / stop |
| --- | ---: | ---: | ---: | ---: |
| SQL or migration physical lines | `<= 200` | `201–350` | `351–600` | `>= 601` |
| Top-level statements per migration direction | `<= 8` | `9–20` | `21–40` | `>= 41` |
| Distinct relation owners touched | `<= 2` | `3–5` | `6–10` | `>= 11` |
| Columns, indexes, or constraints changed | `<= 6` | `7–15` | `16–30` | `>= 31` |
| Join edges in one query | `<= 3` | `4–6` | `7–10` | `>= 11` |
| Maximum CTE/subquery depth | `<= 2` | `3` | `4–5` | `>= 6` |
| PL/pgSQL routine-body physical span | `<= 40` | `41–80` | `81–140` | `>= 141` |
| PL/pgSQL explicit decisions | `<= 5` | `6–10` | `11–16` | `>= 17` |
| PL/pgSQL cyclomatic complexity | `1–6` | `7–12` | `13–20` | `>= 21` |
| Owned trigger, policy, function, or procedure families | `<= 2` | `3–5` | `6–10` | `>= 11` |
| Lock/transaction boundary families | `<= 1` | `2` | `3–4` | `>= 5` |
| Data-movement/backfill families | `0` | `1` | `2` | `>= 3` |
| Independent responsibility families | `1` | `2` | `3` | `>= 4` |

Count physical lines after universal-newline decoding; blanks, comments,
strings, dollar-quoted bodies, embedded data, and a final non-empty
unterminated segment count. Measure each migration direction independently and
disclose the combined file result.

Count top-level statements with a PostgreSQL-aware parser or lexical scanner.
Ignore semicolons in comments, quoted identifiers, strings, dollar quotes, and
routine bodies. Treat one `COPY ... FROM STDIN` plus its terminated data as one
statement. Record psql meta-commands separately because server SQL parsing does
not define their behavior. A routine declaration is one outer statement and
its PL/pgSQL body receives separate span, decision, and complexity measures.

Normalize each table, view, materialized view, sequence, partition, or other
relation identity under the repository's name-resolution policy. Count a
relation once when it is a DDL target, material DML source or target, lock
target, or explicitly changed dependency. Count each changed column, index, or
constraint contract once. Join edges are explicit joins plus comma-join sources
after the first across the complete query tree; record the maximum one-query
result. Query depth starts at zero and adds one for each nested CTE body,
subquery, scalar query, `EXISTS`, or query-bearing expression.

For a `LANGUAGE plpgsql` routine, count physical source lines containing any
part of the body-string payload between its opening and closing quote or
dollar-quote delimiters. Exclude the outer declaration, the delimiters, and the
terminating semicolon. Count a physical line once when body payload shares it
with either delimiter; blanks and comments wholly inside the payload count.
The 140-line boundary is Orange and the 141-line boundary is Red.

PL/pgSQL complexity starts at one and adds conditional branches, loops,
exception handlers, and Boolean short-circuit decisions according to a
configured parser whose rules are named in the evidence. Explicit decisions
omit the extra Boolean operands. Without a supported configured parser, record
both decision measures as unresolved, do not infer a threshold band for them,
and inspect those forms in the semantic review; all other measured signals and
semantic stops still control. Record dynamic `EXECUTE` separately; static
structure cannot prove its possible SQL.

Owned routine and policy breadth counts independently changeable trigger,
policy, function, and procedure behavior families, not every repeated
declaration. Lock/transaction families include transaction lifecycle,
isolation, explicit relation/advisory/row locks, timeout or wait policy, and
nontransactional or multi-phase operations. A data-movement family is one
independently resumable source-to-target, transformation, population, cleanup,
or backfill contract. Responsibilities are independently changeable schema,
integrity, data movement, compatibility, security, routine, performance,
replication, or recovery concerns.

Lines, statements, relation/member breadth, decision/complexity, and lock or
backfill measures often describe the same change. Disclose their correlation
instead of stacking them automatically.

### Classification and proportional exceptions

Historical migrations, generated schemas, dumps, snapshots, fixtures,
extension scripts, and framework output keep their producer and historical
ownership. Do not rewrite, squash, split, or hand-refactor them solely because
they exceed a threshold. Measure the proposed current migration and review
generator reproducibility, consumer compatibility, restore behavior, and
protected-data exposure. A structurally Green extension migration can still be
operationally Orange if applied.

An existing Red legacy artifact may receive the smallest safe fix when current
authority permits it, the change adds no independent responsibility, and it
avoids meaningful growth. Record the preserved boundary. New responsibility
or major feature growth remains Red. A cohesive data or compatibility artifact
can change only a line-count response through an accepted bounded exception;
semantic Red remains Red.

### Semantic response guide

- Native driver parameters for values are Green or Yellow. Identifiers require
  a closed allowlist, normalization, and correct identifier quoting. Stop at
  Red when untrusted input reaches generated SQL interpretation, identifiers,
  ordering, operators, or other command structure.
- A short explicit transaction is Green when its invariants match the accepted
  isolation level. Snapshot or retry dependencies are Yellow. A changed
  concurrency protocol is Orange. Incorrect serial assumptions or omitted
  whole-transaction retry needed for correctness are Red.
- An intentionally long live transaction is Orange only with duration,
  timeout, monitoring, batching, and abort/recovery ownership. Unbounded or
  idle live transactions are Red.
- Row, advisory, and explicit lock behavior needs exact ordering and timeout
  review. Live DDL or explicit relation locks are Orange. An
  unresolved lock or table-rewrite risk on a consequential live relation is
  Red.
- Exact `ALTER TABLE` subforms differ. Metadata-only behavior must be proven for
  the supported version. A live rewrite or validation scan is Orange after its
  lock, disk, time, visibility, and recovery risks are resolved; otherwise Red.
- `CREATE INDEX CONCURRENTLY` is Orange and separately owned: no surrounding
  transaction block, invalid-index cleanup, uniqueness timing, and partition
  restrictions must be addressed. `NOT VALID` followed by separately scheduled
  validation is operationally Orange; an unvalidated constraint is not proof
  of established integrity.
- A live bounded backfill is Orange with a stable key or predicate, bounded
  batches, idempotence, checkpoints, throttling, observability, and recovery.
  An unbounded live backfill is Red.
- Destructive DDL is Orange only with exact authority and target, dependency
  analysis, a successful tested restore, and truthful recovery. Missing any
  prerequisite is Red. Transactional rollback does not recreate transformed or
  externally lost data.
- Small `SECURITY INVOKER` routines can be Green or Yellow. State-changing
  procedures, triggers, C/native routines, cross-table side effects, or changed
  volatility are Orange. False volatility, leakproof, or parallel-safety
  promises that can produce wrong results or bypass security are Red.
- An RLS change is Orange with role, owner, `BYPASSRLS`, command, and policy
  matrix tests. An RLS bypass or false coverage assumption is Red.
- `SECURITY DEFINER` is Orange even when justified. Require a fixed safe
  `search_path`, no untrusted-writable schema, `pg_temp` last, qualified
  objects, least-privileged ownership, and controlled execution privilege.
  Unsafe resolution or privilege escalation is Red.
- Extension installation or update, partition lifecycle, replication topology,
  autovacuum policy, and rewrite-class maintenance are Orange with their exact
  compatibility, privilege, capacity, lock, and recovery evidence. Unvetted
  privileged code, uncontrolled slot/WAL growth, wraparound risk, or missing
  live authority is Red.
- A backup, manifest, checksum, or `pg_verifybackup` result is not a tested
  restore. A consequential change that relies on restoration as its recovery boundary requires
  a successful version-compatible test restore plus integrity and application/data
  validation. An untested backup used to authorize destructive work is Red.
- Use rollback only when it truthfully restores prior state. Nontransactional,
  destructive, or multi-phase work may require forward correction and tested
  restoration. A plan that can leave partial or corrupt state without recovery
  is Red.
- Credentials, connection strings, protected rows, dumps, diagnostics, private
  identifiers, and secret-bearing errors must stay within authorized minimized
  sinks. Uncontrolled disclosure is Red.

## Project-owned parameters

The repository owns supported PostgreSQL versions, extensions, drivers, ORM
and migration tools, schemas, identifiers, compatibility, transaction and lock
policy, batch size, timeouts, deployment topology, environments, credentials,
privileges, RPO/RTO, backup mechanism, maintenance policy, replication, test
commands, rollout, and accepted exceptions. The current task owns whether any
connection, query, migration, backup, restore, maintenance, or destructive
operation is authorized. No response level grants live database access.

## Evidence and completion

Report the PostgreSQL version and parser basis, artifact classification,
structural measurements, exact command subform, known and unknown environment
facts, privilege and protected-data boundary, highest response, rollout,
focused validation, and truthful recovery or forward-correction plan. Static
review cannot establish production sizes, locks, transaction age, write rate,
WAL, lag, storage headroom, runtime privileges, RPO/RTO, or restore success.

This provisional profile was inspected on 2026-07-21 against PostgreSQL 18.4,
with supported-major compatibility context for 18, 17, 16, 15, and 14. Source
and documentation are under the PostgreSQL License; copied material requires
its notice, while this profile uses independently written synthesis and public
locators. Refresh for a later current minor, a new supported major, changed
engine semantics, or changed license boundary.

## Stop or escalate

Stop for any Red signal, including injected SQL, unresolved live lock/rewrite
risk, unbounded backfill or transaction growth, RLS or privilege bypass, unsafe
`SECURITY DEFINER` or `search_path`, false semantic labels, partial/corrupt
migration without recovery, destructive work backed only by an untested
backup, protected-data leakage, unsafe extension or replication behavior, or
live database access without exact authority. Meaningful crisis-level
structural growth also stops pending decomposition or an accepted bounded
exception.

## Common mistakes

- Treating value parameters as a way to bind identifiers or SQL grammar.
- Assuming every `ALTER TABLE` form is metadata-only or transaction-safe.
- Running concurrent index creation inside an ordinary migration transaction.
- Calling `NOT VALID` established integrity before validation succeeds.
- Inferring live row counts, locks, lag, or restore duration from static SQL.
- Calling a backup verified when only creation, checksum, manifest, or
  `pg_verifybackup` completed.
- Promising rollback for destroyed data or nontransactional phases.
- Treating generated dumps as harmless because they are not maintained source.
- Universalizing one migration framework, deployment method, batch size, or
  private operational command.

Removal is bounded: remove this leaf, its relative projection, catalog and
capability-map rows, known-unmanaged entry, and focused tests while retaining
the historical ADR, evaluation, exit, and provenance record.
