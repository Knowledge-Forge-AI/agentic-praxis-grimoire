# ADR 0073 — Unified Skill Catalog, Sources, Namespaces, and Deterministic Resolution

- Status: Accepted
- Date: 2026-09-20
- Phase: APG159 (Roadmap Stage: V0130-A)

## Context

In v0.12, skills exist as a static embedded corpus within the APGR repository (`skills/`), projected into discovery roots via `apg-project-skills` and `install-global-skills`. As APGR expands to support adaptive context delivery, projects and operators require the ability to define project-local skills (e.g. project-specific architectural conventions) or operator-global skills without mutating the canonical APGR codebase.

However, introducing multiple sources risks namespace collisions, unpredictable shadowing, non-deterministic skill selection, and untracked security risks. Furthermore, creating a fourth hand-maintained classification file would create maintenance divergence alongside `skill-metadata.json`, the maturity ledger, and the catalog table.

## Decision

### 1. Generated `SkillDescriptor` Metadata
APGR avoids hand-maintained classification files by generating `SkillDescriptor` directly from authoritative sources:
- Frontmatter `name` and `description` (positive triggers).
- Markdown section `## Do not use` (material non-triggers).
- Markdown section `## Project-owned parameters` (configurable knobs).
- Catalog `Trigger boundary` cell.
- `current_maturity` from `docs/governance/skill-maturity-ledger.json`.
- Measured body bytes and UTF-8 characters.

Generated descriptors are verified via drift-checking in CI.

### 2. Multi-Source Namespace Architecture
APGR establishes three explicit, non-crawling skill sources:
- `apgr:` — Canonical embedded skills distributed with APGR.
- `project:` — Project-local skills located at `<project>/.apgr/skills/<id>/SKILL.md`.
- `user:` — Operator-global skills located at `<APGR_HOME>/skills/<id>/SKILL.md`.

Arbitrary directory traversal, recursive filesystem crawling, and automated remote downloading are strictly prohibited.

### 3. Explicit Collision Policy
When a skill ID exists across multiple sources:
- **Default Policy (`supplement`)**: Both skills are retained under qualified namespace identifiers (`project:foo` and `apgr:foo`). Neither silently replaces the other.
- **Explicit Override (`replace`)**: A project may explicitly override an embedded skill only by declaring it in `.apgr/config.toml`:
  ```toml
  [skills.overrides]
  "apgr:go-language-profile" = "project:go-language-profile"
  ```
  Implicit shadowing is unconditionally rejected as an error.

### 4. Deterministic Resolution Engine
The broader architecture extends Go-owned skill selection. APG163 implements
`BuildCatalog` and `ResolveCatalog` for explicit qualified selection while leaving
V1 `Resolve` semantics unchanged. The following planning features belong to F/G:
- Planning is deterministic: identical inputs (run context, actor binding, attempt, available skills) produce byte-identical resolution plans.
- Ordering is strictly defined: priority tier > affinity score > lexical ID tie-break.
- Only explicitly typed, source-declared required dependencies are directed and cycle-checked in E. Existing `CompositionRules()` associations remain informational and never add bodies.
- Selected skill bodies are immutably bound by SHA-256 digest and snapshotted into the run directory (`NN-<stage>.skills/`).

## Consequences

- Teams can define local project skills with clean namespace isolation.
- Skill selection is 100% reproducible and auditable in run records.
- Canonical APGR skills cannot be silently overridden or subverted.

## APG163 implementation boundary

The provisional E interfaces, byte boundaries, generation owner, diagnostics,
configuration bridge and source confinement are specified in the
[skill catalog contract](../../../guides/skill-catalog.md). Generated descriptors
use `apg.skill-descriptor/v1`; catalog input/output uses `apg.skill-catalog/v1`
and explicit selection uses `apg.catalog-selection/v1`. V1 bundle schemas and
model mappings remain unchanged. E was accepted for local development by the September 23 manager amendment
disposition recorded in Exit 00219. The original provider checkpoint is distinct
from amended bytes, which have no second independent-review freshness. No external
consumer adoption is claimed. F owns ranking and
budget packing; G owns acquisition/MCP; H owns promotions and measured evaluation.
