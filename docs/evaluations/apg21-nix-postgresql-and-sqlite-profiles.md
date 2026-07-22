# APG21 Nix, PostgreSQL, and SQLite Profiles

Phase ID: `APG21`

## Outcome

Partial — PostgreSQL and SQLite profiles implemented; Nix deferred.

APG21 accepts three independent ownership boundaries under ADR 0016 and retains
two provisional profiles. It adopts no generic SQL or database-operations skill
and grants no Nix evaluation, build, activation, database access, migration,
backup, restore, or destructive authority.

| Candidate | Disposition | New corrections | Source basis |
| --- | --- | ---: | --- |
| `nix-language-profile` | `deferred-material-defect` | 1 | Nix 2.35.2 manual, separately versioned Nix 2.35.1 source calibration, NixOS/Nixpkgs 26.05 |
| `postgresql-database-profile` | `retained-provisional` | 1 | PostgreSQL 18.4 with supported-major context for 18 through 14 |
| `sqlite-database-profile` | `retained-provisional` | 1 | SQLite 3.53.3, released 2026-06-26 |

SQLite's one correction preserves the frozen `>= 13` rebuild-step Red boundary
and permits Orange only through the ordinary accepted bounded-exception
contract. It resolves the initial contradiction without automatically
downgrading a syntactically complete rebuild.

Nix's one correction makes valid function-pattern and attribute-set counting
exact and corrects source-version and rights wording. It does not change a
threshold or semantic response. Fresh re-review then finds a second behavior-
bearing contradiction: the frozen closed dynamic-attribute-merge scenario is
Orange, while the corrected leaf makes one closed merge family Green and
provides no controlling escalation. The correction allowance is exhausted, so
the Nix leaf, projection, route, and known-unmanaged entry are not retained.

PostgreSQL's one correction makes the routine-body span exact at its 140/141
boundary and records decision/complexity measures as unresolved when no
supported configured parser is available. It changes no threshold value.

## Ownership and authority

The reserved Nix owner covers Nix-specific expression, module, derivation,
purity, source, store, overlay, flake, shell, and activation-risk judgment but
has no retained leaf. The
PostgreSQL profile owns PostgreSQL MVCC, transactions, locks, DDL, migrations,
routines, security, backup/restore, replication, and maintenance judgment. The
SQLite profile owns SQLite transaction modes, single-writer behavior, busy
handling, journals, WAL, schema rebuilds, pragmas, file ownership, backup,
integrity, and extension judgment.

Exact versions, tools, drivers, migration frameworks, commands, live facts,
environments, credentials, deployment, backup mechanisms, and operational
authority remain project- or task-owned. Existing APG process skills retain
design, planning, implementation, and review procedure.

## Frozen structural thresholds

### Nix

| Signal | Green | Yellow | Orange | Red |
| --- | ---: | ---: | ---: | ---: |
| File physical lines | `<= 200` | `201–350` | `351–500` | `>= 501` |
| Function formals | `<= 6` | `7–12` | `13–20` | `>= 21` |
| Direct `let` bindings | `<= 8` | `9–16` | `17–28` | `>= 29` |
| Direct attribute-set breadth | `<= 12` | `13–24` | `25–40` | `>= 41` |
| Attribute-definition depth | `<= 3` | `4` | `5–6` | `>= 7` |
| Direct imports | `<= 5` | `6–10` | `11–18` | `>= 19` |
| Module option leaf paths | `<= 8` | `9–16` | `17–28` | `>= 29` |
| Merge/override mechanism families | `<= 1` | `2` | `3` | `>= 4` |
| Direct derivation attributes | `<= 15` | `16–25` | `26–40` | `>= 41` |
| Direct flake inputs | `<= 6` | `7–12` | `13–20` | `>= 21` |
| Direct derivation input dependencies | `<= 10` | `11–20` | `21–35` | `>= 36` |
| Direct outputs | `<= 2` | `3–4` | `5–7` | `>= 8` |
| Embedded shell physical lines | `<= 20` | `21–40` | `41–80` | `>= 81` |
| Independent responsibility families | `1` | `2` | `3` | `>= 4` |

### PostgreSQL

| Signal | Green | Yellow | Orange | Red |
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

### SQLite

| Signal | Green | Yellow | Orange | Red |
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

The leaves define reproducible parser/fallback measurement and correlation
rules. Generated and historical artifacts keep their producer ownership. One
Red remains Red; classification does not suppress semantic stops.

## Operational and security stops

Nix stops protected values entering durable store outputs, untrusted shell
interpretation, mutable supply-chain boundaries, undeclared material impurity,
unauthorized import-from-derivation, invariant-bypassing overrides, unsafe
string-context removal, unauthorized remote building or activation, and
unauthorized garbage collection or deletion.

PostgreSQL stops injected SQL, unresolved live lock/rewrite risk, unbounded
transactions or backfills, RLS or privilege bypass, unsafe `SECURITY DEFINER`
or `search_path`, false semantic labels, partial/corrupt migrations without
recovery, destructive work justified by an untested backup, credential or
protected-data leakage, and unauthorized live access.

SQLite stops injected grammar or extensions, unsafe writer/retry assumptions,
WAL/network and sidecar hazards, disabled foreign-key or integrity protection,
unsafe rebuilds, false row identity, unsafe durability pragmas, unintended
URI/path/`ATTACH` access, destructive replacement justified by an untested
backup, protected-data leakage, and unauthorized live access.

## Scenarios and read-only dogfood

All fifteen shared scenarios and 20 of 21 Nix scenarios pass; the closed
dynamic-merge scenario fails and controls Nix deferral. All fifteen shared and
all 25 PostgreSQL and 25 SQLite required scenarios pass. Process/domain pairing
leaves the process owner primary. Trivial non-triggers remain excluded. Three coupled Yellow signals,
two coupled Orange signals, smallest-safe-fix, new-responsibility, project-
override, and classified-artifact outcomes match ADR 0012.

Dogfood used only public maintained source, official documentation examples,
and public-safe synthetic operational cases. Nix calibration spans small Green,
Yellow, Orange, maintained Red, generated lock, semantic activation/security,
and synthetic legacy cases. PostgreSQL calibration includes parameterization,
an extension migration, lock/rewrite/constraint cases, routines/triggers/
security, restore evidence, destructive operations, and generated dumps.
SQLite calibration includes parameterization, transactions and locks, WAL,
rebuilds, backup/integrity, destructive synthetic cases, and generated/test
artifacts. No Nix evaluation or build and no database open or execution
occurred.

## Integration and distribution

Private development contains 16 canonical leaves, 16 relative projections, 6
stable rows, 10 provisional rows, and 15 routable non-router capability-map
entries. PostgreSQL and SQLite are known-unmanaged development skills; Nix is
not integrated. Project,
user, and public-release schema version 1 and the six managed v0.2 defaults are
unchanged. Public v0.2.0 and active integration remain 6/6/6.

## Validation and boundary

Profile-contract, routing, project, checker, release, user, report, identity,
documentation, privacy, link, syntax, help, schema, mode, whitespace, and
complete-diff review gates accept the retained profiles and Nix deferral.
Preexisting skill bytes
remain unchanged except for the bounded workflow-router wording required to
route current domain profiles. No root guidance or private skill was removed, and no ZUnit,
manager-prompt, dependency, plugin, public release, active-integration change,
application smoke, or APG22 work occurred.

## Subsequent APG21A disposition

[APG21A](apg21a-nix-profile-correction.md) uses this phase's complete Nix
defect ledger as its corrected baseline. It separates structural merge-family
breadth from semantic collision, precedence, ownership, and consumer risk and
retains `nix-language-profile` provisionally after all prior and focused merge
scenarios pass. APG21A also applies one bounded PostgreSQL false-escalation
correction; SQLite and router behavior remain accepted. The current development
shape is 17/17/17 with 6 stable rows, 11 provisional rows, and 16 routes. This
subsequent result does not rewrite APG21's truthful partial outcome.
