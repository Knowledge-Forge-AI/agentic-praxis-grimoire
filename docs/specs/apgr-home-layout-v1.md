# Specification: APGR Home Directory Layout Contract (`apgr-home-layout-v1`)

- **Status**: Authoritative Technical Specification
- **Version**: 1.2.0 (inspection CLI, schema v5 baseline, and Go hosting contracts qualified under APG161 / V0130-C)
- **Governing ADR**: [ADR 0071](../adr/2026/09/0071-apgr-home-layout-and-portable-hosting-seams.md)
- **Phase**: APG159 (Milestone V0130-A); amended by APG159A (Milestone V0130-A-CORR1) and APG161 (Milestone V0130-C)

---

## 1. Overview and Design Objectives

The `apgr-home-layout-v1` specification formalizes the filesystem directory structure, path resolution precedence, security permissions, and lifecycle rules for the APGR operator home directory.

Design goals:
1. **Relocatability**: Complete independence from hardcoded user home locations, enabling portable hosting by orchestrators like JACA.
2. **Product Independence**: Complete isolation from foreign environment variables (specifically `JACA_HOME`).
3. **Operator Settings Isolation**: Clear separation between operator-managed settings (`claude/settings.json`) and machine-managed state (`state/dispatcher.sqlite3`).
4. **Deterministic Precedence**: Explicit resolution rules with full configuration provenance tracking.

---

## 2. Directory Hierarchy

```text
<APGR_HOME>/
  config.toml                 Operator configuration (closed keys)
  dispatcher/                 Canonical operator dispatcher bundle:
    bundle.json               Complete generation and member hashes
    models.toml               Runtime model and effort selections
    workers.toml              Worker requirements and capacity
    routes.toml               Execution routes
    endpoints.toml            Provider endpoint configurations
    capabilities.toml         Provider model capabilities
    policy.toml               Lifecycle assurance and mutation policies
  claude/
    settings.json             Operator-owned Claude isolated settings (READ-ONLY to APGR)
  state/
    workers/                  Private standalone worker custody (0700)
    dispatcher.sqlite3        Canonical persistence database (strictly Python dispatcher owned)
    dispatcher.sqlite3-wal    SQLite write-ahead log
    dispatcher.sqlite3-shm    SQLite shared memory index
  generations/
    <hash>/                   Controller generation store (immutable cached bundles)
  scratch/                    Transient working directory for phase execution
  skills/
    <skill_id>/
      SKILL.md                User-global skill definitions (user: namespace)
```

---

## 3. Path Resolution and Precedence

The effective APGR home root is resolved via a three-tier hierarchy strictly preserving the existing contract implemented in `libexec/agent_phase/config_routing.py`:

1. **Explicit CLI Flag**: `--apgr-home <path>` passed to APGR executables or dispatch entrypoints.
2. **Environment Variable**: `APGR_HOME` set in the ambient environment.
3. **Default Fallback**: `~/.apgr` in the invoking user's home directory.

### Invariants and Path Validation
- **No `JACA_HOME` Derivation**: APGR never inspects, infers, or resolves paths from `JACA_HOME`. If a hosting runtime embeds APGR within a JACA workspace, the caller must set `APGR_HOME` explicitly (e.g. `export APGR_HOME="$JACA_HOME/apgr"`).
- **Preserved User-Home Expansion**: Paths undergo standard user-home expansion via `Path(value).expanduser()`.
- **Absolute Path Requirement**: The resolved candidate must be an absolute path (`candidate.is_absolute()`). Relative paths (including cwd-relative paths) are strictly rejected with `ConfigError`.
- **No Side-Effect Mutation**: Resolving paths never creates directories or writes files as an unprompted side effect.
- **Environment Variables and Compatibility Aliases**:
  - `APGR_RUN_ROOT` retains the `AGENT_PHASE_RUN_ROOT` compatibility alias.
  - `APGR_GENERATION_STORE` supports the legacy `AGENT_CENTRAL_GENERATION_STORE`
    environment variable alias under strict key-presence precedence: explicit `store` >
    `APGR_GENERATION_STORE` > legacy `AGENT_CENTRAL_GENERATION_STORE` (only when the
    `APGR_GENERATION_STORE` key is absent from the environment) > maintained default
    home store (`<APGR_HOME>/generations/<digest>`). An explicit `APGR_GENERATION_STORE`
    variable that is present but empty suppresses the legacy alias and selects the
    maintained default. Explicit legacy environment stores are permitted to write
    via `coordinate`.
  - `APGR_ACTIVE_ROOT` supports the legacy `AGENT_CENTRAL_ACTIVE_ROOT` environment
    variable alias under identical key-presence precedence: `APGR_ACTIVE_ROOT` >
    legacy `AGENT_CENTRAL_ACTIVE_ROOT` (only when the `APGR_ACTIVE_ROOT` key is absent) >
    maintained default active root (`~/.local/nix-darwin/agentic-praxis-grimoire_dinas`).
    A present but empty `APGR_ACTIVE_ROOT` suppresses the legacy alias and selects
    the maintained default.
  - **Default Legacy Readback**: In default home configurations (`source == "default"`),
    lookup-only readback from `~/.local/state/agent-central/generations/<digest>` is
    restored with a legacy directory existence precondition and commit-aware selection.
    Legacy readback is strictly lookup-only: no writes, copies, merges, or legacy-byte
    rewrites occur; new coordination and materialization stay fully isolated in the
    current APGR generation store. Explicitly relocated homes (`APGR_HOME` or
    `--apgr-home`) never inspect the default legacy state directory.
  - Emergency dispatch remains an explicit operator selection with separate mutable authority.

### 3.1 Non-Mutating Layout Inspection (`apgr home show`)

The CLI command `apgr home show` (and its JSON variant `apgr home show --json`) provides programmatic and operator inspection of the resolved APGR home directory:
- Implemented with truthful scope labeling: Python (`src/agentic_praxis_grimoire/home.py`, `cli.py`) owns full configuration resolution and emits `scope: "resolved_config"`, whereas standalone Go (`internal/cli/home.go`) provides path-only inspection (`scope: "paths_only"`), or consumes and renders a Python-produced resolved view via `--from-json <path>`.
- Reports resolved `home_root`, `scope` (`resolved_config` or `paths_only`), resolution `provenance` (`flag`, `env`, or `default`), whether `home_root` exists, and the existence of each canonical subdirectory and configuration file.
- Inspecting a nonexistent home root reports status cleanly with zero filesystem side effects; missing directories are never created during inspection.

---

## 4. Permissions and Security Boundaries

To protect cryptographic keys, run logs, and execution state:
- `<APGR_HOME>/state/`: Directory mode must be strictly `0700` (`drwx------`). Files within this directory (`dispatcher.sqlite3`, WAL, SHM) are created with mode `0600` (`-rw-------`).
- `<APGR_HOME>/`: Root directory mode is `0755` (`drwxr-xr-x`) or `0700`.
- **No-Follow Descent**: Inspection and loading of roster files within `<APGR_HOME>/dispatcher/` must enforce `O_NOFOLLOW` / `os.O_NOFOLLOW` and verify single-link regular file ownership matching the current effective UID (`euid`).

---

## 5. Subsystem Details

### 5.1 Operator Configuration (`config.toml`)
Contains closed keys governing dispatcher behavior, outbox routing, integrations, and policy overrides:
- **Top-Level `outbox_root`**: Preserved existing top-level setting:
  ```toml
  outbox_root = "~/Documents/agent/outbox"
  ```
- **Current vs Approved Additive Keys**:
  - **Current Root Keys (v0.12)**: `outbox_root` and `[dispatcher]` (`[dispatcher.routing]`).
  - **Approved Additive Keys (v0.13)**: `[integrations]` (e.g. `[integrations.rtk]`) and `[skills]` (e.g. `[skills.overrides]`).
- **No `[provenance]` Configuration Table**: Provenance is generated runtime evidence emitted in execution logs and run manifests, never an operator-supplied configuration table.
- **Closed Schema Enforcement**: Any key outside the allowed set causes immediate `ConfigError` to prevent silent misconfiguration.

### 5.2 Operator Dispatcher Bundle (`dispatcher/`)
- The six TOML members and `bundle.json` form one coherent positive generation.
  See [the bundle contract](apgr-dispatcher-bundle-v1.md).
- Existing four-file bundles require explicit migration; no automatic conversion
  or source/home mixing occurs. Missing optional bundles may use source defaults.
- `[dispatcher.bundle] required = true` refuses an absent bundle.
- Model and effort reach launchers from the captured bundle. Provider-specific
  files own permissions and tools; they cannot override captured selections.
- Deployment verifies a staged complete bundle before atomic activation. APGR
  has no DINAS runtime dependency and this phase performs no host deployment.

### 5.3 Operator Claude Settings (`claude/settings.json`)
- `<APGR_HOME>/claude/settings.json` is the canonical location for isolated Claude settings used during `--setting-sources` launches.
- **Strict Read-Only Invariant**: APGR reads this file when constructing isolated profile arguments. APGR NEVER writes, edits, replaces, or unlinks this file.

### 5.4 State and Persistence Ownership
- Persistence database resides at `<APGR_HOME>/state/dispatcher.sqlite3`.
- **Strict Native Ownership**: The SQLite persistence database is owned and managed exclusively by the existing Python dispatcher persistence owner (`libexec/agent_phase/persistence.py`).
- **No Shared Database / No Go Driver**: APGR does not introduce a Go SQLite driver, an external service daemon, or a shared database with JACA. Sibling databases exchange versioned JSON event artifacts.

### 5.5 User Skill Namespace (`skills/`)
- User-global skill definitions located under `<APGR_HOME>/skills/<skill_id>/SKILL.md` are loaded into the explicit **`user:<skill_id>`** namespace.
- Distinct from canonical package skills (**`apgr:<skill_id>`**) and local repository skills (**`project:<skill_id>`**).
- Default collision policy is `supplement`; explicit overrides require configuration in `[skills.overrides]`.

---

## 6. Migration, Schema Manifest, and Go Hosting Contracts

- The SQLite database schema is defined and migrated exclusively in `libexec/agent_phase/persistence.py`.
- **Current Baseline**: `SCHEMA_VERSION = 5` (version 1: initial schema; version 2: run records; version 3: review mutation observations; version 4: review mutation policies; version 5: legacy quarantine observations and policies).
- **Allocation Rule**: Schema migration versions are allocated sequentially. The next migration will be allocated as `SCHEMA_VERSION = 6` only when substantive schema changes are implemented in milestone V0130-D or later. No future migration versions are pre-allocated or reserved.
- **Rollback Policy**: If a migration fails or an older APGR version reads a newer database (`db_version > code_version`), dispatch halts immediately with a clear diagnostic indicating incompatible forward schema.
- **Canonical Schema Manifest**: The normalized SQLite schema manifest is exported to [`docs/architecture/dispatcher-sqlite-schema-v5.json`](../architecture/dispatcher-sqlite-schema-v5.json) and mechanically validated against live migrations by `libexec/agent_phase/schema_manifest.py`.
- **Go Hosting Contracts**: Typed Go DTOs and manifest validators reside in package `schema` (`schema/manifest.go`, `schema/records.go`), allowing external orchestrators (such as JACA) to validate database structure and marshal persisted records without embedding a SQLite driver.
