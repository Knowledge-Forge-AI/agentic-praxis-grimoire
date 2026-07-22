---
name: sqlite-database-profile
description: Use when SQLite-specific judgment is material to SQL, transaction modes, single-writer concurrency, busy handling, journal or WAL behavior, schema rebuilds, pragmas, affinity, file ownership, backup and integrity, extensions, or warning and crisis thresholds beyond repository policy.
---

# SQLite Database Profile

## Core principle

Apply SQLite-specific judgment only when it is material. Establish the SQLite
library version, driver, filesystem and deployment model, schema and migration
ownership, connection policy, protected-data boundary, and task authority
before recommending a construct or response. Use the highest justified
`Green — routine`, `Yellow — caution`, `Orange — warning`, or
`Red — crisis / stop` response for one coherent current decision.

Keep writer, transaction, journal, checkpoint, sidecar, file, and recovery
ownership explicit. Static structure warns about proposed growth; it cannot
establish live contention, journal state, filesystem safety, or recoverability.
This provisional profile classifies and recommends and does not grant authority
to open or operate on a database.

## Do not use

Do not use this profile for:

- a comment, typo, formatting-only edit, or ordinary parameterized query with
  no material SQLite-specific judgment;
- generic design, planning, implementation, debugging, or review procedure;
- selecting an SQLite version, driver, ORM, migration framework, journal mode,
  backup tool, VFS, filesystem, deployment, or connection-pool policy;
- authorizing a database open, query, `ATTACH`, pragma change, migration,
  checkpoint, backup, restore, replacement, extension load, or deletion;
- automatically rewriting historical migrations or existing Red owners;
- treating generated schemas, dumps, snapshots, fixtures, test corpora, or
  framework output as maintained source before classification; or
- inferring live writer contention, lock duration, database size, journal
  state, filesystem behavior, or restore success from SQL text.

## Procedure

1. Establish task authority, repository instructions, actual SQLite library
   version, driver semantics, schema and migration ownership, connection and
   transaction policy, filesystem and process topology, journal and checkpoint
   ownership, protected data, backup and restore requirements, and recovery
   boundary.
2. Classify each artifact as maintained query, schema, migration, trigger,
   test, legacy, generated, dump, snapshot, fixture, framework output, or other
   machine-produced material. Classification never suppresses semantic Red.
3. Use the repository's configured SQLite-aware parser when present and record
   its name, version, settings, and dialect. Otherwise use the fallback lexical
   rules below. Do not open or query a database to obtain a static count.
4. Measure migration directions separately and the current and projected
   owner. Mark dynamic or generated SQL unresolved when its possible structure
   cannot be established statically.
5. Assign the highest justified response. Three materially coupled Yellow signals
   normally justify Orange. Two materially coupled Orange signals over one
   owner are presumptively Red unless accepted cohesive evidence supports
   Orange. One Red signal remains Red. Correlated rebuild, object, trigger, and
   data-movement measures are not independent escalation evidence.
6. Proceed proportionally for Green; inspect policy and evidence for Yellow;
   require an explicit local decision, bounded target, recovery or truthful
   forward correction, and focused validation for Orange; stop Red growth or
   unsafe behavior pending decomposition, an accepted bounded exception, or
   governing authority.
7. Inspect parameterization, transaction modes, single-writer and busy behavior,
   rollback journals, WAL and checkpoints, foreign keys, schema rebuilds,
   affinity and STRICT tables, row identity, triggers, pragmas, extensions,
   paths and URI options, `ATTACH`, backup, integrity, filesystems, permissions,
   protected data, and live authority independently of structure.
8. Pair separately with the applicable process capability.
   `implementing-with-test-discipline` may remain primary for an authorized
   behavior or migration change; `reviewing-and-verifying-repository-work` may
   remain primary for acceptance review. This profile supplies SQLite judgment
   without silently invoking either.
9. Preserve stricter project policy. Relax only a profile default through an
   accepted scoped rationale, evidence, validation, growth limit, and rollback;
   never relax superior injection, integrity, durability, privacy, destructive-
   action, or authority stops.
10. Report the level, structural and semantic signals, artifact class, library
    and parser basis, known and unknown live facts, required response, focused
    validation, and recovery or decomposition boundary.

### Structural threshold contract

These defaults apply mainly to proposed growth in maintained hand-written
SQLite SQL and migrations. They are review signals, not runtime, contention,
durability, or migration-safety claims.

| Signal | Green — routine | Yellow — caution | Orange — warning | Red — crisis / stop |
| --- | ---: | ---: | ---: | ---: |
| SQL or migration physical lines | `<= 200` | `201–350` | `351–600` | `>= 601` |
| Top-level statements per migration direction | `<= 8` | `9–16` | `17–30` | `>= 31` |
| Distinct tables, indexes, triggers, or views touched | `<= 3` | `4–7` | `8–12` | `>= 13` |
| Join edges in one statement | `<= 2` | `3–5` | `6–8` | `>= 9` |
| Maximum CTE/subquery depth | `<= 1` | `2` | `3–4` | `>= 5` |
| Ordered schema-rebuild steps | `0` | `1–5` | `6–12` | `>= 13` |
| State-mutating PRAGMA families | `0` | `1–2` | `3–4` | `>= 5` |
| Transaction/attached-database families | `0–1` | `2` | `3` | `>= 4` |
| Trigger definitions affecting one owner | `0–1` | `2–3` | `4–6` | `>= 7` |
| Top-level body actions in one trigger | `0–3` | `4–6` | `7–10` | `>= 11` |
| Independent data-copy/backfill families | `0` | `1` | `2–3` | `>= 4` |
| Independent responsibility families | `0–1` | `2` | `3` | `>= 4` |

Count physical lines after universal-newline decoding; blanks, comments,
strings, quoted identifiers, embedded data, and a final non-empty unterminated
segment count. Measure `up` and `down` migration directions independently and
disclose the combined file result.

Count top-level statements with an SQLite-aware parser or lexical scanner.
Ignore semicolons in comments, strings, quoted identifiers, and trigger bodies.
A complete `CREATE TRIGGER ... BEGIN ... END;` is one outer statement; measure
its top-level body actions separately. Count each distinct schema object once
per direction when it is a DDL target, DML source or target in data movement,
or explicitly recreated dependent object. Do not count aliases or CTE names.

Join edges are explicit joins plus comma-join sources after the first across
the complete nested query tree; record the maximum one-statement result. Query
depth starts at zero and adds one for each CTE body, scalar subquery, `EXISTS`,
`IN`, or parenthesized query. Compound arms remain at their containing depth;
recursive iterations do not increase static depth.

Rebuild steps include explicit transaction and foreign-key setup/restoration,
replacement-table creation, data copy, old-table removal, rename, dependent
index/trigger/view recreation, checks, commit, and schema capture. The table is
literal: `>= 13` is Red. A cohesive canonical rebuild may remain Orange only
through the ordinary accepted bounded exception with explicit rationale, no
other Red, exact transaction and integrity evidence, focused validation,
growth bound, and truthful recovery or forward correction. Syntactic
completeness never automatically downgrades Red.

Count each distinct state-changing PRAGMA name once. Read-only inspection forms
and `foreign_key_check` do not count as mutation but remain validation evidence.
Repeated off/on changes are one family with the transition disclosed.
Transaction/attached-database families are transaction lifecycle, explicit
`DEFERRED`/`IMMEDIATE`/`EXCLUSIVE` selection, savepoint lifecycle,
`ATTACH`/`DETACH`, and cross-database atomicity coordination.

Trigger breadth is owner-scoped. Use the higher result from affected trigger
definitions and maximum top-level body actions; disclose indirect writes and
read dependencies. A data-copy/backfill family is one independently reversible
source-to-target, transformation, population, cleanup, import/export, or table-
copy contract. Responsibilities are independently changeable schema, integrity,
data movement, compatibility, trigger, connection/journal, attached-database,
performance, and recovery concerns.

Object and statement breadth, rebuild and data movement, trigger definitions
and actions, and joins and query depth often describe the same change. Disclose
correlation rather than stacking them automatically.

### Classification and proportional exceptions

Historical migrations, generated schemas, dumps, snapshots, fixtures,
framework output, and maintained conformance corpora keep their producer and
historical ownership. Do not rewrite, squash, split, or hand-refactor them
solely because they exceed a threshold. Repeated dump inserts normally form one
data family. Measure embedded SQL units where useful and review generator
reproducibility, consumer compatibility, restore behavior, and protected-data
exposure.

An existing Red legacy artifact may receive the smallest safe fix when current
authority permits it, the change adds no independent responsibility, and it
avoids meaningful growth. Record the preserved boundary. New responsibility
or major feature growth remains Red. A classified cohesive artifact changes a
Red response only through an accepted bounded exception; semantic Red remains
Red.

### Semantic response guide

- Native bind parameters protect values, not identifiers or SQL grammar.
  Closed identifier allowlists can be Yellow. Project-generated grammar is
  Orange. Stop when untrusted input reaches SQL grammar, PRAGMAs, URI options,
  `ATTACH`, extension names, or filesystem paths.
- Short transactions under an established policy are Green or Yellow.
  `DEFERRED` can fail on read-to-write upgrade; `IMMEDIATE` reserves write
  capability at start; rollback-mode `EXCLUSIVE` also blocks readers. Long or
  material concurrency changes are Orange. Unknown state, unsafe non-idempotent
  retry, or unbounded duration is Red.
- SQLite has one writer. Bounded `SQLITE_BUSY` handling is Yellow. Writer-
  ownership redesign is Orange. Assuming simultaneous writers, ignoring busy,
  or retrying forever is Red.
- Existing rollback-journal or WAL policy can be Yellow when owner, sidecars,
  and checkpoint behavior are known. Adopting WAL or changing durability is
  Orange. Stop when WAL is proposed on a network filesystem, checkpoint
  ownership is absent, WAL growth is unbounded, a live database is copied
  without required sidecars, or journals/`-wal`/`-shm` are manipulated
  independently.
- Foreign keys require per-connection enablement and validation. A controlled
  rebuild that temporarily disables enforcement is Orange. Stop when
  foreign-key enforcement is assumed, silently disabled, toggled inside an active
  transaction as if effective, or replaced by `integrity_check` alone.
- A supported simple `ALTER TABLE` is Yellow on controlled data and Orange live.
  A generalized rebuild is Orange only under the bounded structural contract.
  An unsafe rename-old-first sequence, partial replacement, or uncontrolled
  `writable_schema` editing is Red.
- Ordinary affinity is not rigid typing. `STRICT` adoption is Yellow after
  minimum-version and driver checks and Orange for conversion. Correctness that
  falsely depends on rigid ordinary declared types is Red.
- Explicit `INTEGER PRIMARY KEY` identity can be Green. `AUTOINCREMENT` is
  Yellow only for a documented never-reuse requirement. Implicit `ROWID`
  stability across rebuild or `VACUUM` is not a durable external contract.
- Simple compatible generated columns or `AFTER` triggers can be Yellow.
  Hidden multi-table side effects are Orange. Undefined `BEFORE` trigger
  behavior, unsafe unqualified TEMP trigger targets, or unresolved reader
  incompatibility is Red.
- Mutating `journal_mode`, `synchronous`, extension, URI, or `ATTACH` behavior
  overrides lower structural counts. Durability-policy change is Orange. For
  authoritative persistent data, `journal_mode=OFF`, `journal_mode=MEMORY`, or
  `synchronous=OFF` is Red.
- Runtime extension loading is Orange only for an exact trusted binary, ABI,
  entry point, provenance, temporary enablement, and subsequent disablement.
  Untrusted or insufficiently identified loading is Red.
- Fixed owner-controlled local paths are Green or Yellow. Changed URI, VFS, or
  open-mode semantics are Orange. Untrusted path, traversal, symlink target,
  URI option, VFS, mode, attachment, or output destination is Red.
- Controlled `ATTACH` with qualified names can be Yellow or Orange. Assuming
  cross-file atomicity when the main database is WAL or in-memory is Red.
- Online backup, restore, `VACUUM INTO`, or replacement is Orange with exact
  authority, target, busy, space, permission, and recovery evidence. A backup-
  API completion, copy, checksum, or integrity result is not a tested restore.
  An untested backup used to justify destructive file replacement is Red.
- Completion requires successful restore evidence plus `integrity_check`,
  `foreign_key_check`, and relevant application-level semantic validation.
  `quick_check` or one integrity result alone is not complete proof.
- Filesystem, directory, database, journal, WAL, SHM, backup, and dump
  permissions are material. Unverified shared/network operation where
  corruption is possible or protected artifacts are overbroadly readable is
  Red.
- Protected rows, `.fullschema` statistics, dumps, paths, backups, logs, and
  errors must remain within authorized minimized sinks. Leakage is Red.

## Project-owned parameters

The repository owns the SQLite library and driver versions, build options,
connection and pool policy, migration framework, schema and compatibility,
transaction and busy policy, journal and checkpoint mode, filesystem and
process topology, VFS and URI policy, extensions, file ownership and
permissions, backup mechanism, validation, deployment, tests, and exceptions.
The current task owns whether any database may be opened, queried, attached,
checkpointed, migrated, backed up, restored, replaced, or deleted. This profile
does not grant live database access.

## Evidence and completion

Report the actual SQLite library and parser basis, artifact classification,
structural measurements, connection/journal/filesystem assumptions, known and
unknown live facts, protected-data boundary, highest response, focused
validation, and truthful recovery or forward-correction plan. Static review
cannot establish writer contention, lock state, journal state, database size,
filesystem guarantees, permissions, or restore success.

This provisional profile was inspected on 2026-07-21 against SQLite 3.53.3,
released 2026-06-26. SQLite states that its core code and documentation are
dedicated to the public domain; adjacent build tooling, wrappers, extensions,
and proprietary offerings can have different terms. This profile uses
independently written synthesis. Refresh for a later release, materially
different driver/build configuration, changed WAL guidance, or changed rights
boundary.

## Stop or escalate

Stop for any Red signal, including injected grammar or extension loading,
unsafe writer or retry assumptions, WAL/network or sidecar hazards, silently
disabled integrity, unsafe rebuilds, false row identity, unsafe durability
PRAGMAs, unintended URI/path/`ATTACH` access, an untested backup used for
destruction, protected-data leakage, destructive file replacement, or live
database access without exact authority. Meaningful crisis-level structural
growth also stops pending decomposition or an accepted bounded exception.

## Common mistakes

- Treating bind parameters as protection for identifiers, paths, or PRAGMAs.
- Assuming concurrent writers or retrying `SQLITE_BUSY` indefinitely.
- Copying a live WAL database without its required sidecar state.
- Assuming foreign keys are enabled by default on every connection.
- Automatically downgrading a complete rebuild despite a Red step count.
- Treating ordinary type names as rigid enforcement or implicit `ROWID` as a
  durable external identity.
- Changing `journal_mode` or `synchronous` as if it were ordinary query text.
- Calling a backup verified without a successful restore and integrity and
  application validation.
- Universalizing one driver's defaults, migration framework, filesystem,
  journal policy, or private operational command.

Removal is bounded: remove this leaf, its relative projection, catalog and
capability-map rows, known-unmanaged entry, and focused tests while retaining
the historical ADR, evaluation, exit, and provenance record.
