# ADR 0071 — APGR Home Layout, Relocatable Configuration and State, and Portable Hosting Seams

- Status: Accepted (Amended under APG159A / V0130-A-CORR1; Qualified under APG161 / V0130-C)
- Date: 2026-09-20
- Phase: APG159A (Roadmap Stage: V0130-A-CORR1); Phase APG161 (Roadmap Stage: V0130-C)

## Context

As APGR matures into an independently hostable single-phase dispatcher, external orchestrators (such as JACA) require well-defined filesystem contracts, relocatable state, and typed Go contracts to embed APGR primitives.

However, past designs risked overreaching:
1. Proposing that APGR infer configuration paths from `JACA_HOME`, violating APGR's product independence.
2. Proposing a custom, handwritten Go TOML subset parser (H3) to maintain zero external dependencies, introducing high maintenance and conformance risks.
3. Proposing a shared SQLite database runtime between APGR and JACA with mixed-owner tables (`ext_*`), coupling migration lifecycles across independent projects.

APGR v0.13 resolves these needs with lean, clean-room boundaries.

## Decision

### 1. `apgr-home-layout-v1` Contract
APGR defines a standardized, relocatable home layout:

```text
<APGR_HOME>/
  config.toml                 operator configuration (closed keys)
  dispatcher/                 optional operator roster root:
    routes.toml               routes / endpoints / capabilities / policy .toml
    endpoints.toml            (all four or none; one shared generation)
    capabilities.toml
    policy.toml
  claude/settings.json        operator-owned Claude isolated settings (never written by APGR)
  state/dispatcher.sqlite3    canonical machine state (strictly Python dispatcher owned)
  generations/<hash>/         controller generation store
  scratch/                    transient scratch root
  skills/<id>/SKILL.md        user-global skill source (user:<skill_id> namespace)
```

### 2. Resolution Precedence, Path Contract, and Isolation
- **Precedence**: `--apgr-home` CLI flag > `APGR_HOME` environment variable > `~/.apgr` fallback.
- **Preserved Path Contract**: Paths undergo standard user-home expansion (`Path(value).expanduser()`) and MUST resolve to an absolute path (`candidate.is_absolute()`). Relative paths (including cwd-relative paths) are strictly rejected with `ConfigError`.
- **Closed Configuration Schema**:
  - Top-level `outbox_root` is preserved: `outbox_root = "~/Documents/agent/outbox"`.
  - Current v0.12 keys: `outbox_root` and `[dispatcher]` (`[dispatcher.routing]`).
  - Approved additive v0.13 keys: `[integrations]` and `[skills]`.
  - No `[provenance]` operator configuration table: provenance is generated runtime evidence, not operator config.
- **Zero `JACA_HOME` Coupling**: APGR never inspects, infers, or resolves paths from `JACA_HOME`. A hosting system such as JACA must explicitly set `APGR_HOME` or pass `--apgr-home`.
- **Operator Claude Settings Isolation**: `<APGR_HOME>/claude/settings.json` is recognized as the canonical isolated operator settings path. APGR reads it when configuring isolated provider launches but NEVER mutates, overwrites, or manages this file.
- **Environment Variable Aliases & Legacy Generation Isolation**:
  - `APGR_RUN_ROOT` (historical alias: `AGENT_PHASE_RUN_ROOT`)
  - `APGR_GENERATION_STORE` (historical alias: `AGENT_CENTRAL_GENERATION_STORE`)
  - `APGR_ACTIVE_ROOT` (historical alias: `AGENT_CENTRAL_ACTIVE_ROOT`)
  Conflicting inputs resolve deterministically with new names taking precedence and both inputs recorded. When APGR home is explicitly relocated via `--apgr-home` or `APGR_HOME`, generation store lookup is strictly isolated to `<effective_home>/generations` and never searches the default user's legacy generation store (`~/.local/state/agent-central/generations`).
- **Dynamic Routing Fail-Closed**: An absent `capabilities.toml` fails closed whenever dynamic routing is requested (resolving Discrepancy D5). Fallback to fixed-mode execution must be explicit and recorded in provenance.

### 3. Deferral of Custom Go TOML Parser (H3)
APGR defers the authoring of a custom Go TOML subset parser. Hosting consumers importing APGR Go packages pass explicit, typed in-process values or validated JSON documents. Consumers utilizing their own TOML parsers remain responsible for their own dependencies.

### 4. SQLite Schema Contract & Migration Allocation Rule
- **DDL Contract**: The dispatcher SQLite schema is documented as a versioned manifest generated from `libexec/agent_phase/persistence.py`.
- **Baseline Allocation**: Migrations are strictly sequential. Schema version 5 is established as the baseline under V0130-B/V0130-C (`SCHEMA_VERSION = 5` in `persistence.py:21`), incorporating migrations for run records (v2), review mutation observations (v3), review mutation policies (v4), and legacy quarantine observations/policies (v5). Future migrations will allocate `SCHEMA_VERSION = 6` sequentially when required. No migration version is pre-reserved.
- **Exported Manifest**: The normalized SQLite schema manifest is exported to `docs/architecture/dispatcher-sqlite-schema-v5.json` and validated by `libexec/agent_phase/schema_manifest.py`.
- **Separate Database Ownership**: APGR and JACA maintain separate SQLite databases. APGR never creates or accesses `ext_*` tables, and does not require a shared `schema_migrations.owner` column. Cross-system integration occurs via explicit record exchange.

### 5. Typed Go Hosting Contracts and Consumer Fixtures
APGR maintains small, dependency-free Go DTOs in `phase`, `routing`, `evidence`, and `schema`. The `schema` package exports `DispatcherSchemaManifest` validators and typed SQLite row DTOs (`RunRecord`, `RouteResolutionRecord`, `InvocationAttemptRecord`, `OperationalObservationRecord`, `ReviewMutationObservationRecord`, `ReviewMutationPolicyRecord`, `LegacyQuarantineObservationRecord`, `LegacyQuarantinePolicyRecord`). All Go interfaces ship with immutable golden vectors and substantive consumer fixtures in `testing/fixtures/jaca_consumer/` verifying zero type leaks (`schema.` prohibited) and zero subprocess execution.

## Consequences

- Hosting orchestrators can embed and relocate APGR state without side effects.
- APGR retains zero runtime dependencies in Go and avoids building an unmaintainable TOML parser.
- Database lifecycles remain completely decoupled between APGR and external consumers.
