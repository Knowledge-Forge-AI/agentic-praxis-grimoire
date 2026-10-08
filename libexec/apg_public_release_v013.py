"""Audited v0.13.0 public-surface additions and release-authority constants, kept as data outside the orchestrator.

The v0.13.0 surface is the complete v0.12.0 surface plus exactly these owners.
``apg_public_release`` composes them; this module imports nothing from it, so
historical v0.12.0-and-earlier surfaces cannot change through this file.
"""

from __future__ import annotations


# First-party Nix publication owners. They mirror the
# ``publication.critical_files`` declared by ``nix/distribution.json``; a
# focused test keeps the two lists equal.
V013_NIX_CRITICAL_FILES = (
    "flake.lock",
    "flake.nix",
    "nix/checks.nix",
    "nix/distribution.json",
    "nix/package.nix",
    "nix/source.nix",
)

V013_SKILL_ADDITIONS = ("skills/rtk-command-proxy/SKILL.md",)
V013_PROJECTION_ADDITIONS = (".agents/skills/rtk-command-proxy",)

# Commands whose ``--help`` must succeed in the isolated public validation.
V013_WRAPPER_ADDITIONS = (
    "bin/agent-phase-dispatch",
    "bin/agent-phase-resolve",
    "bin/apg-qualify-nix",
    "bin/apgr-dispatcher-bundle",
)

V013_HELPER_ADDITIONS = (
    "libexec/apg_nix_distribution.py",
    "libexec/apg_nix_qualification.py",
    "libexec/apg_nix_smoke.py",
    "libexec/apg_public_release_v013.py",
    "libexec/controller_generation.py",
    "libexec/controller_generation_bootstrap.py",
    "tools/ci/mypy_identity.py",
)

# Only mirrored ``/agentic-praxis-grimoire/`` pytest files may enter the
# audited selection; dedicated dispatcher suites are qualified separately.
V013_TEST_ADDITIONS = (
    "src/test/int/python/agentic-praxis-grimoire/libexec/apg_nix_distribution.int.test.py",
    "src/test/int/python/agentic-praxis-grimoire/libexec/apg_nix_qualification.int.test.py",
    "src/test/int/python/agentic-praxis-grimoire/libexec/apg_nix_smoke.int.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/flake.nix.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/libexec/apg_nix_distribution.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/libexec/apg_nix_qualification.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/libexec/apg_nix_smoke.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/libexec/apg_public_release_v013.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/tools/ci/python_type_check.unit.test.py",
)

# Installed-runtime authority files named by ``nix/distribution.json`` outside
# bin/, libexec/ and the package. Per-provider profile files are left to the
# flake's installed-runtime completeness check.
V013_RUNTIME_AUTHORITY_FILES = (
    "antigravity/GEMINI.md",
    "claude/CLAUDE.md",
    "claude/instruction-fragments-v1.json",
    "claude/model-catalog-v1.json",
    "codex/AGENTS.md",
    "codex/config.d/170-subagents.toml",
    "common/dispatcher/README.md",
    "common/dispatcher/capabilities.toml",
    "common/dispatcher/endpoints.toml",
    "common/dispatcher/models.toml",
    "common/dispatcher/policy.toml",
    "common/dispatcher/routes.toml",
    "common/dispatcher/workers.toml",
    "common/skills/agent-worker/SKILL.md",
    "common/skills/agent-worker/WORKER-RECOVERY.md",
    "tools/add_dispatcher_roster_operator_directions.py",
)

V013_CRITICAL_ADDITIONS = (
    *V013_NIX_CRITICAL_FILES,
    *V013_RUNTIME_AUTHORITY_FILES,
    "bin/agent-phase-adopt",
    "bin/agent-phase-adopt-entry",
    "bin/agent-phase-finalize",
    "bin/agent-phase-observations",
    "bin/agent-phase-ownership",
    "docs/adr/2026/09/0076-first-party-nix-flake-publication-target.md",
    "docs/guides/nix-flake.md",
    "docs/v0-13-roadmap.md",
    "release/v0.13.0-notes.md",
)

# Public main may carry untagged commits after the previous release tag.
ADVANCED_HEAD_VERSIONS = frozenset({"0.12.0", "0.13.0"})

# Public main may also carry untagged commits between tagged releases (v0.12.0
# was tagged after an untagged public-main commit). Each release commit is still
# a tagged single-parent link; v0.12.0 keeps its stricter tail-only rule.
INTERLEAVED_UNTAGGED_VERSIONS = frozenset({"0.13.0"})

# Merged-source verification: release version -> accepted predecessor release.
MERGED_CHECK_PREDECESSORS = {"0.11.0": "0.10.0", "0.12.0": "0.11.0", "0.13.0": "0.12.0"}

# Pinned cryptographic digest and provenance authority for the v0.13.0 grandfathered
# Ruff lint baseline (tools/ci/ruff_baseline.json). Changes to the baseline or provenance
# require an intentional update to this versioned release authority.
V013_RUFF_BASELINE_SCHEMA = "apg-ruff-baseline-v2"
V013_RUFF_BASELINE_ORIGIN_COMMIT = "129a29590b0ab73f3d5a72afff8cbd406accce63"
V013_RUFF_BASELINE_ORIGIN_TREE = "0f5381be0a7bab42da533861c0657cbf593538d9"
V013_RUFF_BASELINE_COUNT = 512
V013_RUFF_BASELINE_DIGEST = "36d541c85278990540a181e4bc307ae7306f6547b34b8c9b1a9ac1e1b3c01770"
