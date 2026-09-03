"""Deterministic local APG public projection and candidate validation."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import NoReturn, Sequence
from urllib.parse import unquote, urlsplit


COMMAND = "apg-public-release"
POLICY_PATH = "release/public-surface.json"
PUBLIC_V01_COMMIT = "f53342d4e5079ff2a73c0a107777a92910d016a1"
PUBLIC_V01_TREE = "0163a2931e65eb822f44a41d6cd0105e671015ad"
POLICY_KEYS = {
    "canonical_public_identity",
    "critical_files",
    "excluded_prefix",
    "required_helpers",
    "required_licensing_files",
    "required_projections",
    "required_skills",
    "required_test_entrypoints",
    "required_wrappers",
    "schema_version",
    "validation_categories",
}
PRIVATE_POLICY_KEYS = {"schema_version", "forbidden_text_patterns"}
ARRAY_KEYS = POLICY_KEYS - {
    "canonical_public_identity",
    "excluded_prefix",
    "schema_version",
}
ALLOWED_CATEGORIES = {
    "bash-syntax",
    "command-help",
    "confidentiality",
    "configured-tests",
    "critical-paths",
    "history",
    "licensing",
    "local-links",
    "markdown",
    "projection",
    "python-compile",
    "record-identity",
    "skill-library",
}
AUDITED_WRAPPERS = (
    "bin/apg-check-change-size",
    "bin/apg-check-record-identity",
    "bin/apg-check-skill-library",
    "bin/apg-project-skills",
    "bin/apg-public-release",
    "bin/apg-test",
    "bin/apg-user-skills",
    "bin/append-operational-report",
    "bin/flatten-skill-symlinks",
    "bin/git-diff-report",
    "bin/git-show-report",
    "bin/install-global-skills",
)
AUDITED_HELPERS = (
    "libexec/agent_report/__init__.py",
    "libexec/agent_report/cli.py",
    "libexec/agent_report/diff.py",
    "libexec/agent_report/git_adapter.py",
    "libexec/agent_report/models.py",
    "libexec/agent_report/operational.py",
    "libexec/agent_report/rendering.py",
    "libexec/agent_report/safety.py",
    "libexec/agent_report/show.py",
    "libexec/apg_project_skills_commands.py",
    "libexec/apg_project_skills_core.py",
    "libexec/apg_public_release.py",
    "libexec/apg_record_identity.py",
    "libexec/apg_skill_library_check.py",
    "libexec/apg_skill_topology.py",
    "libexec/apg_test.py",
    "libexec/apg_user_skills.py",
    "libexec/change_size/__init__.py",
    "libexec/change_size/checker.py",
    "libexec/change_size/cli.py",
    "libexec/change_size/git_adapter.py",
    "libexec/change_size/inspection.py",
    "libexec/change_size/policy.py",
    "libexec/flatten_skill_symlinks.py",
    "libexec/global_skills_inventory.py",
    "libexec/global_skills_state.py",
    "libexec/global_skills_transaction.py",
    "libexec/install_global_skills.py",
    "libexec/skill_projection_state.py",
)
AUDITED_TESTS = tuple(sorted((
    "src/test/int/python/agentic-praxis-grimoire/bin/apg-check-change-size.int.test.py",
    "src/test/int/python/agentic-praxis-grimoire/bin/apg-check-phase-commit-message.int.test.py",
    "src/test/int/python/agentic-praxis-grimoire/bin/apg-check-record-identity.int.test.py",
    "src/test/int/python/agentic-praxis-grimoire/bin/apg-check-skill-library.int.test.py",
    "src/test/int/python/agentic-praxis-grimoire/bin/apg-project-skills.int.test.py",
    "src/test/int/python/agentic-praxis-grimoire/bin/apg-public-release.int.test.py",
    "src/test/int/python/agentic-praxis-grimoire/bin/apg-test.int.test.py",
    "src/test/int/python/agentic-praxis-grimoire/bin/apg-user-skills.int.test.py",
    "src/test/int/python/agentic-praxis-grimoire/bin/append-operational-report.int.test.py",
    "src/test/int/python/agentic-praxis-grimoire/bin/flatten-skill-symlinks.int.test.py",
    "src/test/int/python/agentic-praxis-grimoire/bin/git-diff-report.int.test.py",
    "src/test/int/python/agentic-praxis-grimoire/bin/git-show-report.int.test.py",
    "src/test/int/python/agentic-praxis-grimoire/bin/install-global-skills.int.test.py",
    "src/test/int/python/agentic-praxis-grimoire/libexec/apg_project_skills_commands.int.test.py",
    "src/test/int/python/agentic-praxis-grimoire/libexec/apg_project_skills_core.int.test.py",
    "src/test/int/python/agentic-praxis-grimoire/libexec/apg_public_release.int.test.py",
    "src/test/int/python/agentic-praxis-grimoire/libexec/apg_skill_topology.int.test.py",
    "src/test/int/python/agentic-praxis-grimoire/libexec/apg_test.int.test.py",
    "src/test/int/python/agentic-praxis-grimoire/libexec/apg_user_skills.int.test.py",
    "src/test/int/python/agentic-praxis-grimoire/libexec/global_skills_inventory.int.test.py",
    "src/test/int/python/agentic-praxis-grimoire/libexec/global_skills_state.int.test.py",
    "src/test/int/python/agentic-praxis-grimoire/libexec/global_skills_transaction.int.test.py",
    "src/test/int/python/agentic-praxis-grimoire/skills/javascript-language-profile/SKILL.int.test.py",
    "src/test/int/python/agentic-praxis-grimoire/skills/markdown-language-profile/SKILL.int.test.py",
    "src/test/int/python/agentic-praxis-grimoire/skills/nodejs-runtime-profile/SKILL.int.test.py",
    "src/test/int/python/agentic-praxis-grimoire/skills/typescript-language-profile/SKILL.int.test.py",
    "src/test/unit/bash/append-operational-report.unit.test.bats",
    "src/test/unit/bash/git-show-report.unit.test.bats",
    "src/test/unit/python/agentic-praxis-grimoire/docs/evaluations/apg41-v0-4-readiness-and-pre-release-smoke.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/docs/evaluations/apg42-v0-4-release-publication-and-active-deployment.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/docs/specs/go-testing-component-profiles.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/libexec/agent_report/cli.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/libexec/agent_report/operational.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/libexec/agent_report/rendering.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/libexec/agent_report/safety.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/libexec/agent_report/show.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/libexec/apg_phase_commit_message.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/libexec/apg_project_skills_commands.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/libexec/apg_project_skills_core.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/libexec/apg_public_release.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/libexec/apg_record_identity.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/libexec/apg_skill_library_check.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/libexec/apg_skill_topology.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/libexec/apg_test.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/libexec/apg_user_skills.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/libexec/change_size/checker.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/libexec/change_size/cli.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/libexec/change_size/git_adapter.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/libexec/change_size/policy.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/libexec/flatten_skill_symlinks.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/libexec/global_skills_inventory.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/libexec/global_skills_state.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/libexec/global_skills_transaction.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/libexec/install_global_skills.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/skills/chatgpt/chatgpt-manager-workflow/SKILL.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/skills/chatgpt/composing-approved-roadmap-assignments/SKILL.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/skills/css-language-profile/SKILL.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/skills/dockerfile-profile/SKILL.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/skills/go-cmp-test-profile/SKILL.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/skills/go-test-profile/SKILL.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/skills/implementing-with-test-discipline/SKILL.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/skills/javascript-language-profile/SKILL.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/skills/markdown-language-profile/SKILL.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/skills/minitest-test-profile/SKILL.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/skills/nix-test-profile/SKILL.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/skills/nodejs-runtime-profile/SKILL.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/skills/planning-repository-work/SKILL.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/skills/pytest-test-profile/SKILL.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/skills/reviewing-and-verifying-repository-work/SKILL.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/skills/typescript-language-profile/SKILL.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/skills/vagrantfile-profile/SKILL.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_markdown_candidate_contract.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_css_candidate_contract.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_css_profile_candidate_contract.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_css_profile_fixture_contract.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_javascript_candidate_contract.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_javascript_fixture_contract.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_markdown_clause_guard_contract.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_markdown_polarity_guard_contract.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_markdown_register_contract.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_markdown_token_guard_contract.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_markdown_vocabulary_contract.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_nodejs_candidate_contract.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_nodejs_fixture_contract.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_repository_import_cache_contract.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_typescript_candidate_contract.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_typescript_fixture_contract.unit.test.py",
)))
AUDITED_LICENSING = (
    "CLA.md",
    "COMMERCIAL-LICENSE.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "NOTICE",
)
AUDITED_SKILLS = tuple(sorted((
    "skills/agentic-praxis-grimoire-workflow/SKILL.md",
    "skills/bash-language-profile/SKILL.md",
    "skills/bats-test-profile/SKILL.md",
    "skills/chatgpt/chatgpt-manager-workflow/SKILL.md",
    "skills/chatgpt/composing-approved-roadmap-assignments/SKILL.md",
    "skills/composing-bounded-worker-assignments/SKILL.md",
    "skills/converting-bash-scripts-to-python/SKILL.md",
    "skills/css-language-profile/SKILL.md",
    "skills/debugging-systematically/SKILL.md",
    "skills/designing-significant-changes/SKILL.md",
    "skills/dockerfile-profile/SKILL.md",
    "skills/go-cmp-test-profile/SKILL.md",
    "skills/go-language-profile/SKILL.md",
    "skills/go-test-profile/SKILL.md",
    "skills/implementing-with-test-discipline/SKILL.md",
    "skills/javascript-language-profile/SKILL.md",
    "skills/markdown-language-profile/SKILL.md",
    "skills/minitest-test-profile/SKILL.md",
    "skills/nix-language-profile/SKILL.md",
    "skills/nix-test-profile/SKILL.md",
    "skills/nodejs-runtime-profile/SKILL.md",
    "skills/planning-repository-work/SKILL.md",
    "skills/postgresql-database-profile/SKILL.md",
    "skills/pytest-test-profile/SKILL.md",
    "skills/python-language-profile/SKILL.md",
    "skills/reviewing-and-verifying-repository-work/SKILL.md",
    "skills/ruby-language-profile/SKILL.md",
    "skills/sqlite-database-profile/SKILL.md",
    "skills/synthesizing-repository-guidance/SKILL.md",
    "skills/typescript-language-profile/SKILL.md",
    "skills/vagrantfile-profile/SKILL.md",
    "skills/zsh-language-profile/SKILL.md",
    "skills/zunit-test-profile/SKILL.md",
)))
AUDITED_PROJECTIONS = tuple(sorted(
    f".agents/skills/{PurePosixPath(path).parent.name}"
    for path in AUDITED_SKILLS
))
LOCAL_PATH_MARKERS = ("/" + "Users" + "/", "file:" + "///")
AUDITED_CRITICAL = tuple(sorted((
    ".coveragerc",
    ".github/pull_request_template.md",
    ".gitignore",
    "AGENTS.md",
    "README.md",
    "pytest.ini",
    "requirements/test.txt",
    "src/test/apg_public_release_cases.py",
    "src/test/apg_skill_library_cases.py",
    "src/test/apg_test_support.py",
    "src/test/apg_user_skills_cases.py",
    "src/test/install_global_skills_cases.py",
    "src/test/fixtures/apg26-scenario-families.json",
    "src/test/fixtures/apg32-minitest-scenario-families.json",
    "src/test/fixtures/apg33-dockerfile-scenario-families.json",
    "src/test/fixtures/apg34-vagrantfile-scenario-families.json",
    "src/test/fixtures/apg37-go-cmp-scenario-families.json",
    "src/test/fixtures/apg37-go-test-scenario-families.json",
    "src/test/fixtures/apg39-nix-test-scenario-families.json",
    "src/test/fixtures/apg41-provisional-readiness-cases.json",
    "src/test/fixtures/apg64-markdown-scenario-register.md",
    "src/test/fixtures/apg66-markdown-language-profile-scenarios.json",
    "src/test/fixtures/apg75-typescript-language-profile-scenarios.json",
    "src/test/fixtures/apg77-css-language-profile-scenarios.json",
    "src/test/fixtures/apg79-javascript-language-profile-scenarios.json",
    "src/test/fixtures/apg76-css-target-first/README.md",
    "src/test/fixtures/apg76-css-target-first/fixture-manifest.json",
    "src/test/fixtures/apg76-css-target-first/src/base.css",
    "src/test/fixtures/apg76-css-target-first/src/cascade.css",
    "src/test/fixtures/apg76-css-target-first/src/conditions.css",
    "src/test/fixtures/apg76-css-target-first/src/custom-properties.css",
    "src/test/fixtures/apg76-css-target-first/src/generated-boundary.css",
    "src/test/fixtures/apg76-css-target-first/src/host-boundary.astro",
    "src/test/fixtures/apg76-css-target-first/src/nesting.css",
    "src/test/fixtures/apg76-css-target-first/src/units-and-color.css",
    "src/test/fixtures/apg76-css-target-first/src/unknown-environment.css",
    "src/test/fixtures/apg78-javascript-core/README.md",
    "src/test/fixtures/apg78-javascript-core/fixture-manifest.json",
    "src/test/fixtures/apg78-javascript-core/package.json",
    "src/test/fixtures/apg78-javascript-core/src/async.mjs",
    "src/test/fixtures/apg78-javascript-core/src/checked.js",
    "src/test/fixtures/apg78-javascript-core/src/cli-core.mjs",
    "src/test/fixtures/apg78-javascript-core/src/cli-node-adapter-boundary.cjs",
    "src/test/fixtures/apg78-javascript-core/src/coercion.mjs",
    "src/test/fixtures/apg78-javascript-core/src/commonjs-boundary.cjs",
    "src/test/fixtures/apg78-javascript-core/src/dynamic-import-boundary.mjs",
    "src/test/fixtures/apg78-javascript-core/src/errors.mjs",
    "src/test/fixtures/apg78-javascript-core/src/evaluation.mjs",
    "src/test/fixtures/apg78-javascript-core/src/functions.mjs",
    "src/test/fixtures/apg78-javascript-core/src/iteration.mjs",
    "src/test/fixtures/apg78-javascript-core/src/mode-selected.js",
    "src/test/fixtures/apg78-javascript-core/src/module-boundary.mjs",
    "src/test/fixtures/apg78-javascript-core/src/modules/consumer.mjs",
    "src/test/fixtures/apg78-javascript-core/src/modules/counter.mjs",
    "src/test/fixtures/apg78-javascript-core/src/modules/cycle-a.mjs",
    "src/test/fixtures/apg78-javascript-core/src/modules/cycle-b.mjs",
    "src/test/fixtures/apg78-javascript-core/src/modules/top-level-await.mjs",
    "src/test/fixtures/apg78-javascript-core/src/objects.mjs",
    "src/test/fixtures/apg78-javascript-core/src/scope.mjs",
    "src/test/fixtures/apg78-javascript-core/unbound/mode-neutral.js.txt",
    "src/test/fixtures/apg78-javascript-core/unbound/sloppy-script.js.txt",
    "src/test/fixtures/apg78-javascript-core/unbound/strict-script.js.txt",
    "src/test/fixtures/apg74-typescript-intended-state/README.md",
    "src/test/fixtures/apg74-typescript-intended-state/fixture-manifest.json",
    "src/test/fixtures/apg74-typescript-intended-state/package.json",
    "src/test/fixtures/apg74-typescript-intended-state/src/checked/config-loader.js",
    "src/test/fixtures/apg74-typescript-intended-state/src/core/inventory.ts",
    "src/test/fixtures/apg74-typescript-intended-state/src/core/runtime-boundary.ts",
    "src/test/fixtures/apg74-typescript-intended-state/src/declarations/host-metrics.d.ts",
    "src/test/fixtures/apg74-typescript-intended-state/src/embedded/widget.astro",
    "src/test/fixtures/apg74-typescript-intended-state/src/modules/legacy.cts",
    "src/test/fixtures/apg74-typescript-intended-state/src/modules/loader.mts",
    "src/test/fixtures/apg74-typescript-intended-state/src/ui/badge.tsx",
    "src/test/fixtures/apg74-typescript-intended-state/src/ui/jsx-host.d.ts",
    "src/test/fixtures/apg74-typescript-intended-state/src/unbound/option-state-unknown.ts",
    "src/test/fixtures/apg74-typescript-intended-state/src/unbound/orphan-role-unknown.ts",
    "src/test/fixtures/apg74-typescript-intended-state/tsconfig.declarations.json",
    "src/test/fixtures/apg74-typescript-intended-state/tsconfig.json",
    "src/test/support/apg_markdown_candidate_contract.py",
    "src/test/support/apg_css_candidate_contract.py",
    "src/test/support/apg_css_profile_candidate_contract.py",
    "src/test/support/apg_css_profile_fixture_contract.py",
    "src/test/support/apg_javascript_candidate_contract.py",
    "src/test/support/apg_javascript_fixture_contract.py",
    "src/test/support/apg_markdown_clause_guard_contract.py",
    "src/test/support/apg_markdown_polarity_guard_contract.py",
    "src/test/support/apg_markdown_register_contract.py",
    "src/test/support/apg_markdown_token_guard_contract.py",
    "src/test/support/apg_markdown_vocabulary_contract.py",
    "src/test/support/apg_repository_import_cache_contract.py",
    "src/test/support/apg_typescript_candidate_contract.py",
    "src/test/support/apg_typescript_fixture_contract.py",
    "testing/apg-change-size-policy.json",
    "testing/apg-test-inventory.json",
    "docs/adr/2026/07/0005-public-license-and-contribution-governance.md",
    "docs/adr/2026/07/0009-public-distribution-and-reproducible-release-validation.md",
    "docs/adr/2026/07/0010-six-skill-post-superpowers-stability-dispositions.md",
    "docs/adr/2026/07/0011-v0-3-workflow-synthesis-and-modular-guidance-architecture.md",
    "docs/adr/2026/07/0012-language-profile-contract-and-warning-levels.md",
    "docs/adr/2026/07/0013-repository-guidance-synthesis-and-migration-dispositions.md",
    "docs/adr/2026/07/0014-shell-language-and-shell-test-profile-ownership.md",
    "docs/adr/2026/07/0015-semantic-phase-identity-and-record-finalization.md",
    "docs/adr/2026/07/0016-nix-and-relational-engine-profile-ownership.md",
    "docs/adr/2026/07/0017-approved-roadmap-manager-assignment-ownership.md",
    "docs/adr/2026/07/0018-v0-3-readiness-maturity-and-release-inclusion.md",
    "docs/adr/2026/07/0019-v0-3-release-distribution-and-variable-skill-set-lifecycle.md",
    "docs/adr/2026/07/0032-agent-report-storage-project-identity-and-change-size-policy.md",
    "docs/adr/2026/07/0033-multi-repository-global-skill-installation.md",
    "docs/adr/2026/07/0038-markdown-language-profile-candidate.md",
    "docs/adr/2026/08/0043-typescript-language-profile-candidate-and-intended-state-harness.md",
    "docs/adr/2026/08/0044-css-language-profile-candidate-and-target-first-harness.md",
    "docs/adr/2026/08/0045-javascript-language-profile-candidate-and-target-first-harness.md",
    "docs/adr/README.md",
    "docs/bootstrap-v0.1.md",
    "docs/evaluations/apg12-public-distribution-and-release-validation.md",
    "docs/evaluations/apg12a-public-lineage-and-read-only-validation-correction.md",
    "docs/evaluations/apg13-six-skill-post-superpowers-stability-review.md",
    "docs/evaluations/apg14-v0-2-release-candidate-and-publication.md",
    "docs/evaluations/apg15-v0-3-foundation-design.md",
    "docs/evaluations/apg16-public-workflow-router.md",
    "docs/evaluations/apg17-repository-guidance-synthesis.md",
    "docs/evaluations/apg18-python-language-profile.md",
    "docs/evaluations/apg19-shell-and-shell-test-profiles.md",
    "docs/evaluations/apg19a-semantic-phase-identity-and-apg19-reconciliation.md",
    "docs/evaluations/apg20-go-and-ruby-language-profiles.md",
    "docs/evaluations/apg20a-go-and-ruby-profile-corrections.md",
    "docs/evaluations/apg21-nix-postgresql-and-sqlite-profiles.md",
    "docs/evaluations/apg21a-nix-profile-correction.md",
    "docs/evaluations/apg22-cross-repository-dogfood-and-guidance-migration.md",
    "docs/evaluations/apg22a-approved-roadmap-manager-assignments.md",
    "docs/evaluations/apg22b-version-bounded-zunit-profile.md",
    "docs/evaluations/apg22c-zunit-startup-isolation-evidence-correction.md",
    "docs/evaluations/apg23-v0-3-readiness-maturity-and-application-smoke.md",
    "docs/evaluations/apg24-v0-3-release-candidate-and-publication.md",
    "docs/evaluations/apg41-v0-4-readiness-and-pre-release-smoke.md",
    "docs/evaluations/apg42-v0-4-release-publication-and-active-deployment.md",
    "docs/evaluations/apg54-global-skill-installer-integration.md",
    "docs/evaluations/apg55-global-skill-installer-transaction-hardening.md",
    "docs/evaluations/apg66-markdown-language-profile-validation-and-integration.md",
    "docs/evaluations/apg66a-markdown-replay-evidence-truth.md",
    "docs/evaluations/apg66b-markdown-register-vocabulary-and-guard-exactness.md",
    "docs/evaluations/apg66c-markdown-clause-polarity-and-predicate-binding.md",
    "docs/evaluations/apg66d-repository-import-cache-entry-presence.md",
    "docs/evaluations/apg75-typescript-iterative-hardening-and-integration.md",
    "docs/evaluations/apg75a-typescript-scope-and-lifecycle-closure.md",
    "docs/evaluations/apg76-css-language-profile-candidate-recovery.md",
    "docs/evaluations/apg77-css-iterative-hardening-and-integration.md",
    "docs/evaluations/apg77a-css-evidence-retention-closure-and-integration.md",
    "docs/evaluations/apg77b-css-traceability-clean-room-closure-and-integration.md",
    "docs/evaluations/apg77c-css-evidence-proportionality-and-integration.md",
    "docs/evaluations/apg77d-css-known-debt-and-provisional-integration.md",
    "docs/evaluations/apg78-javascript-core-candidate.md",
    "docs/evaluations/apg79-javascript-core-iterative-hardening-and-integration.md",
    "docs/evaluations/apg79a-javascript-terminal-proof-closure-and-integration.md",
    "docs/evaluations/apg79b-javascript-contract-harness-closure-and-integration.md",
    "docs/evaluations/apg79c-javascript-known-debt-and-provisional-integration.md",
    "docs/evaluations/apg79d-test262-source-evidence-and-javascript-integration.md",
    "docs/evaluations/apg79e-javascript-report-binding-debt-and-provisional-integration.md",
    "docs/governance/language-profile-known-debt.json",
    "docs/governance/language-profile-known-debt.md",
    "docs/language-profile-contract.md",
    "docs/legacy-roadmap-closure.md",
    "docs/manager-worker-protocol.md",
    "docs/phase-and-record-identity.md",
    "docs/project-model.md",
    "docs/project-skill-projection.md",
    "docs/provenance.md",
    "docs/public-release-process.md",
    "docs/roadmap.md",
    "docs/skill-authoring-and-maintenance.md",
    "docs/specs/markdown-language-profile-scenario-coverage.md",
    "docs/specs/markdown-language-profile.md",
    "docs/specs/typescript-language-profile-scenario-coverage.md",
    "docs/specs/typescript-language-profile.md",
    "docs/specs/css-language-profile-scenario-coverage.md",
    "docs/specs/css-language-profile.md",
    "docs/specs/javascript-language-profile-scenario-coverage.md",
    "docs/specs/javascript-language-profile.md",
    "docs/status/2026/07/20/00018-apg12-public-distribution-and-release-validation-exit.md",
    "docs/status/2026/07/20/00019-apg12a-public-lineage-and-read-only-validation-correction-exit.md",
    "docs/status/2026/07/20/00020-apg13-six-skill-post-superpowers-stability-review-exit.md",
    "docs/status/2026/07/20/00021-apg14-v0-2-release-candidate-and-publication-exit.md",
    "docs/status/2026/07/20/00022-apg15-v0-3-foundation-design-exit.md",
    "docs/status/2026/07/20/00023-apg16-public-workflow-router-exit.md",
    "docs/status/2026/07/20/00024-apg17-repository-guidance-synthesis-exit.md",
    "docs/status/2026/07/21/00025-apg17a-public-release-identity-evidence-correction-exit.md",
    "docs/status/2026/07/21/00026-apg18-language-profile-contract-and-python-vertical-slice-exit.md",
    "docs/status/2026/07/21/00027-apg18a-python-profile-current-state-documentation-correction-exit.md",
    "docs/status/2026/07/21/00028-apg19-shell-and-shell-test-profiles-exit.md",
    "docs/status/2026/07/21/00029-apg19a-semantic-phase-identity-and-apg19-reconciliation-exit.md",
    "docs/status/2026/07/21/00030-apg20-go-and-ruby-language-profiles-exit.md",
    "docs/status/2026/07/21/00031-apg20a-go-and-ruby-profile-corrections-exit.md",
    "docs/status/2026/07/21/00032-apg21-nix-postgresql-and-sqlite-profiles-exit.md",
    "docs/status/2026/07/21/00033-apg21a-nix-profile-correction-exit.md",
    "docs/status/2026/07/21/00034-apg22-cross-repository-dogfood-and-guidance-migration-exit.md",
    "docs/status/2026/07/21/00035-apg22a-approved-roadmap-manager-assignments-exit.md",
    "docs/status/2026/07/21/00036-apg22b-version-bounded-zunit-profile-exit.md",
    "docs/status/2026/07/21/00037-apg22c-zunit-startup-isolation-evidence-correction-exit.md",
    "docs/status/2026/07/21/00038-apg23-v0-3-readiness-maturity-and-application-smoke-exit.md",
    "docs/status/2026/07/22/00039-apg24-v0-3-release-candidate-and-publication-exit.md",
    "docs/status/2026/07/26/00062-apg42-v0-4-release-publication-and-active-deployment-exit.md",
    "docs/status/2026/07/28/00074-apg54-global-skill-installer-integration-exit.md",
    "docs/status/2026/07/29/00075-apg55-global-skill-installer-transaction-hardening-exit.md",
    "docs/status/2026/08/01/00095-apg66-markdown-language-profile-validation-and-integration-exit.md",
    "docs/status/2026/08/01/00096-apg66a-markdown-replay-evidence-truth-exit.md",
    "docs/status/2026/08/01/00097-apg66b-markdown-register-vocabulary-and-guard-exactness-exit.md",
    "docs/status/2026/08/01/00098-apg66c-markdown-clause-polarity-and-predicate-binding-exit.md",
    "docs/status/2026/08/01/00099-apg66d-repository-import-cache-entry-presence-exit.md",
    "docs/status/2026/08/03/00108-apg75-typescript-iterative-hardening-and-integration-exit.md",
    "docs/status/2026/08/03/00109-apg75a-typescript-scope-and-lifecycle-closure-exit.md",
    "docs/status/2026/08/04/00110-apg76-css-language-profile-candidate-recovery-exit.md",
    "docs/status/2026/08/04/00111-apg77-css-iterative-hardening-and-integration-exit.md",
    "docs/status/2026/08/06/00112-apg77a-css-evidence-retention-closure-and-integration-exit.md",
    "docs/status/2026/08/06/00113-apg77b-css-traceability-clean-room-closure-and-integration-exit.md",
    "docs/status/2026/08/07/00114-apg77c-css-evidence-proportionality-and-integration-exit.md",
    "docs/status/2026/08/08/00115-apg77d-css-known-debt-and-provisional-integration-exit.md",
    "docs/status/2026/08/08/00116-apg78-javascript-core-candidate-exit.md",
    "docs/status/2026/08/08/00117-apg79-javascript-core-iterative-hardening-and-integration-exit.md",
    "docs/status/2026/08/08/00118-apg79a-javascript-terminal-proof-closure-and-integration-exit.md",
    "docs/status/2026/08/08/00119-apg79b-javascript-contract-harness-closure-and-integration-exit.md",
    "docs/status/2026/08/08/00120-apg79c-javascript-known-debt-and-provisional-integration-exit.md",
    "docs/status/2026/08/08/00121-apg79d-test262-source-evidence-and-javascript-integration-exit.md",
    "docs/status/2026/08/09/00122-apg79e-javascript-report-binding-debt-and-provisional-integration-exit.md",
    "docs/adr/2026/08/0046-nodejs-runtime-and-cli-stack-candidate-and-target-first-harness.md",
    "docs/evaluations/apg80-nodejs-runtime-and-cli-stack-candidate.md",
    "docs/evaluations/apg81-nodejs-runtime-cli-iterative-hardening-and-integration.md",
    "docs/evaluations/apg81a-nodejs-qualification-threat-model-and-harness-simplification.md",
    "docs/evaluations/apg81b-nodejs-integration-contract-clarification-and-provisional-adoption.md",
    "docs/evaluations/apg81c-nodejs-lifecycle-test-and-scratch-closure.md",
    "docs/evaluations/apg81d-nodejs-provisional-integration.md",
    "docs/evaluations/apg81e-nodejs-final-integration-closure.md",
    "docs/evaluations/apg81f-nodejs-actual-test-projection-and-integration-closure.md",
    "docs/evaluations/apg81g-nodejs-selector-release-and-integration-closure.md",
    "docs/evaluations/apg81h-nodejs-reviewable-qualification-and-integration-closure.md",
    "docs/specs/nodejs-runtime-profile-scenario-coverage.md",
    "docs/specs/nodejs-runtime-profile.md",
    "docs/status/2026/08/09/00123-apg80-nodejs-runtime-and-cli-stack-candidate-exit.md",
    "docs/status/2026/08/10/00124-apg81-nodejs-runtime-cli-iterative-hardening-and-integration-exit.md",
    "docs/status/2026/08/10/00125-apg81a-nodejs-qualification-threat-model-and-harness-simplification-exit.md",
    "docs/status/2026/08/10/00126-apg81b-nodejs-integration-contract-clarification-and-provisional-adoption-exit.md",
    "docs/status/2026/08/10/00127-apg81c-nodejs-lifecycle-test-and-scratch-closure-exit.md",
    "docs/status/2026/08/10/00128-apg81d-nodejs-provisional-integration-exit.md",
    "docs/status/2026/08/11/00129-apg81e-nodejs-final-integration-closure-exit.md",
    "docs/status/2026/08/11/00130-apg81f-nodejs-actual-test-projection-and-integration-closure-exit.md",
    "docs/status/2026/08/11/00131-apg81g-nodejs-selector-release-and-integration-closure-exit.md",
    "docs/status/2026/08/11/00132-apg81h-nodejs-reviewable-qualification-and-integration-closure-exit.md",
    "src/test/fixtures/apg80-nodejs-runtime-cli/README.md",
    "src/test/fixtures/apg80-nodejs-runtime-cli/cli/adapter.mjs",
    "src/test/fixtures/apg80-nodejs-runtime-cli/cli/core.mjs",
    "src/test/fixtures/apg80-nodejs-runtime-cli/commonjs/local-dependency.cjs",
    "src/test/fixtures/apg80-nodejs-runtime-cli/commonjs/wrapper-boundary.cjs",
    "src/test/fixtures/apg80-nodejs-runtime-cli/esm/builtin-boundary.mjs",
    "src/test/fixtures/apg80-nodejs-runtime-cli/esm/metadata.mjs",
    "src/test/fixtures/apg80-nodejs-runtime-cli/fixture-manifest.json",
    "src/test/fixtures/apg80-nodejs-runtime-cli/interop/dynamic-exports.cjs",
    "src/test/fixtures/apg80-nodejs-runtime-cli/interop/esm-consumer.mjs",
    "src/test/fixtures/apg80-nodejs-runtime-cli/interop/identity.mjs",
    "src/test/fixtures/apg80-nodejs-runtime-cli/interop/require-esm.cjs",
    "src/test/fixtures/apg80-nodejs-runtime-cli/interop/static-exports.cjs",
    "src/test/fixtures/apg80-nodejs-runtime-cli/module-mapping/commonjs-package/module-only.js",
    "src/test/fixtures/apg80-nodejs-runtime-cli/module-mapping/commonjs-package/package.json",
    "src/test/fixtures/apg80-nodejs-runtime-cli/module-mapping/commonjs-package/source.js",
    "src/test/fixtures/apg80-nodejs-runtime-cli/module-mapping/explicit-commonjs.cjs",
    "src/test/fixtures/apg80-nodejs-runtime-cli/module-mapping/explicit-module.mjs",
    "src/test/fixtures/apg80-nodejs-runtime-cli/module-mapping/module-package/package.json",
    "src/test/fixtures/apg80-nodejs-runtime-cli/module-mapping/module-package/source.js",
    "src/test/fixtures/apg80-nodejs-runtime-cli/module-mapping/typeless-package/detected-module.js",
    "src/test/fixtures/apg80-nodejs-runtime-cli/module-mapping/typeless-package/goal-neutral.js",
    "src/test/fixtures/apg80-nodejs-runtime-cli/module-mapping/typeless-package/package.json",
    "src/test/fixtures/apg80-nodejs-runtime-cli/package.json",
    "src/test/fixtures/apg80-nodejs-runtime-cli/process/event-loop-entry.cjs",
    "src/test/fixtures/apg80-nodejs-runtime-cli/process/event-loop.mjs",
    "src/test/fixtures/apg80-nodejs-runtime-cli/process/filesystem.mjs",
    "src/test/fixtures/apg80-nodejs-runtime-cli/process/inputs.mjs",
    "src/test/fixtures/apg80-nodejs-runtime-cli/process/lifecycle-child.mjs",
    "src/test/fixtures/apg80-nodejs-runtime-cli/process/lifecycle-parent.mjs",
    "src/test/fixtures/apg80-nodejs-runtime-cli/process/stdio.mjs",
    "src/test/fixtures/apg80-nodejs-runtime-cli/resolution/entry.mjs",
    "src/test/fixtures/apg80-nodejs-runtime-cli/resolution/lib/condition-custom.mjs",
    "src/test/fixtures/apg80-nodejs-runtime-cli/resolution/lib/condition-default.mjs",
    "src/test/fixtures/apg80-nodejs-runtime-cli/resolution/lib/encapsulated.mjs",
    "src/test/fixtures/apg80-nodejs-runtime-cli/resolution/lib/internal-only.mjs",
    "src/test/fixtures/apg80-nodejs-runtime-cli/resolution/lib/public-entry.mjs",
    "src/test/fixtures/apg80-nodejs-runtime-cli/resolution/lib/public-subpath.mjs",
    "src/test/fixtures/apg80-nodejs-runtime-cli/resolution/package.json",
    "src/test/fixtures/apg80-nodejs-runtime-cli/runtime/identity.mjs",
    "src/test/fixtures/apg80-nodejs-runtime-cli/target-boundary/public-safe-runtime-role.json",
    "src/test/fixtures/apg80-nodejs-runtime-cli/typescript/erasable.ts",
    "src/test/fixtures/apg80-nodejs-runtime-cli/typescript/nonerasable.ts",
    "src/test/fixtures/apg81-nodejs-runtime-profile-scenarios.json",
    "src/test/support/apg_nodejs_candidate_contract.py",
    "src/test/support/apg_nodejs_fixture_contract.py",
    "testing/nodejs-profile-qualification-threat-model.json",
    "docs/status/README.md",
    "docs/user-scoped-skill-integration.md",
    "docs/v0-3-guidance-migration-proposal.md",
    "docs/v0-3-readiness-matrix.md",
    "docs/v0-3-release-scope-closure.md",
    "release/public-surface.json",
    "skills/README.md",
    "skills/agentic-praxis-grimoire-workflow/references/capability-map.json",
    "skills/chatgpt/chatgpt-manager-workflow/references/capability-map.json",
)))

HISTORICAL_V02_WRAPPERS = (
    "bin/apg-check-skill-library",
    "bin/apg-project-skills",
    "bin/apg-public-release",
    "bin/apg-user-skills",
    "bin/append-operational-report",
    "bin/git-show-report",
)
HISTORICAL_V02_HELPERS = (
    "libexec/agent-report/common.sh",
    "libexec/apg_project_skills_commands.py",
    "libexec/apg_project_skills_core.py",
    "libexec/apg_public_release.py",
    "libexec/apg_skill_library_check.py",
    "libexec/apg_user_skills.py",
)
HISTORICAL_V02_TESTS = (
    "src/test/int/python/apg_check_skill_library.int.test.py",
    "src/test/int/python/apg_project_skills.int.test.py",
    "src/test/int/python/apg_public_release.int.test.py",
    "src/test/int/python/apg_user_skills.int.test.py",
    "src/test/unit/bash/append-operational-report.unit.test.bats",
    "src/test/unit/bash/git-show-report.unit.test.bats",
    "src/test/unit/python/apg_public_release.unit.test.py",
    "src/test/unit/python/apg_skill_library.unit.test.py",
    "src/test/unit/python/apg_user_skills.unit.test.py",
)
HISTORICAL_V02_LICENSING = (
    "CLA.md",
    "COMMERCIAL-LICENSE.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "NOTICE",
)
HISTORICAL_V02_SKILLS = tuple(
    f"skills/{name}/SKILL.md"
    for name in (
        "composing-bounded-worker-assignments",
        "debugging-systematically",
        "designing-significant-changes",
        "implementing-with-test-discipline",
        "planning-repository-work",
        "reviewing-and-verifying-repository-work",
    )
)
HISTORICAL_V02_PROJECTIONS = tuple(
    path.replace("skills/", ".agents/skills/", 1).removesuffix("/SKILL.md")
    for path in HISTORICAL_V02_SKILLS
)
HISTORICAL_V02_CRITICAL = (
    ".github/pull_request_template.md",
    ".gitignore",
    "AGENTS.md",
    "README.md",
    "docs/adr/2026/07/0005-public-license-and-contribution-governance.md",
    "docs/adr/2026/07/0009-public-distribution-and-reproducible-release-validation.md",
    "docs/adr/2026/07/0010-six-skill-post-superpowers-stability-dispositions.md",
    "docs/adr/README.md",
    "docs/bootstrap-v0.1.md",
    "docs/evaluations/apg12-public-distribution-and-release-validation.md",
    "docs/evaluations/apg12a-public-lineage-and-read-only-validation-correction.md",
    "docs/evaluations/apg13-six-skill-post-superpowers-stability-review.md",
    "docs/evaluations/apg14-v0-2-release-candidate-and-publication.md",
    "docs/legacy-roadmap-closure.md",
    "docs/manager-worker-protocol.md",
    "docs/project-model.md",
    "docs/project-skill-projection.md",
    "docs/provenance.md",
    "docs/public-release-process.md",
    "docs/roadmap.md",
    "docs/skill-authoring-and-maintenance.md",
    "docs/status/2026/07/20/00018-apg12-public-distribution-and-release-validation-exit.md",
    "docs/status/2026/07/20/00019-apg12a-public-lineage-and-read-only-validation-correction-exit.md",
    "docs/status/2026/07/20/00020-apg13-six-skill-post-superpowers-stability-review-exit.md",
    "docs/status/2026/07/20/00021-apg14-v0-2-release-candidate-and-publication-exit.md",
    "docs/status/README.md",
    "docs/user-scoped-skill-integration.md",
    "release/public-surface.json",
    "skills/README.md",
)
APG53_V05_WRAPPERS = frozenset(
    {"bin/apg-check-change-size", "bin/flatten-skill-symlinks"}
)
APG53_V05_HELPERS = frozenset(
    {
        "libexec/change_size/__init__.py",
        "libexec/change_size/checker.py",
        "libexec/change_size/cli.py",
        "libexec/change_size/git_adapter.py",
        "libexec/change_size/inspection.py",
        "libexec/change_size/policy.py",
        "libexec/flatten_skill_symlinks.py",
        "libexec/skill_projection_state.py",
    }
)
APG53_V05_TESTS = frozenset(
    {
        "src/test/int/python/agentic-praxis-grimoire/bin/apg-check-change-size.int.test.py",
        "src/test/int/python/agentic-praxis-grimoire/bin/flatten-skill-symlinks.int.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/libexec/change_size/checker.unit.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/libexec/change_size/cli.unit.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/libexec/change_size/git_adapter.unit.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/libexec/change_size/policy.unit.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/libexec/flatten_skill_symlinks.unit.test.py",
    }
)
APG53_V05_CRITICAL = frozenset(
    {
        "docs/adr/2026/07/0032-agent-report-storage-project-identity-and-change-size-policy.md",
        "testing/apg-change-size-policy.json",
    }
)
APG54_V05_WRAPPERS = frozenset({"bin/install-global-skills"})
APG54_V05_HELPERS = frozenset(
    {
        "libexec/global_skills_inventory.py",
        "libexec/global_skills_state.py",
        "libexec/global_skills_transaction.py",
        "libexec/install_global_skills.py",
    }
)
APG54_V05_TESTS = frozenset(
    {
        "src/test/int/python/agentic-praxis-grimoire/bin/install-global-skills.int.test.py",
        "src/test/int/python/agentic-praxis-grimoire/libexec/global_skills_inventory.int.test.py",
        "src/test/int/python/agentic-praxis-grimoire/libexec/global_skills_state.int.test.py",
        "src/test/int/python/agentic-praxis-grimoire/libexec/global_skills_transaction.int.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/libexec/global_skills_inventory.unit.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/libexec/global_skills_state.unit.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/libexec/global_skills_transaction.unit.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/libexec/install_global_skills.unit.test.py",
    }
)
APG54_V05_CRITICAL = frozenset(
    {
        "docs/adr/2026/07/0033-multi-repository-global-skill-installation.md",
        "docs/evaluations/apg54-global-skill-installer-integration.md",
        "docs/status/2026/07/28/00074-apg54-global-skill-installer-integration-exit.md",
        "src/test/install_global_skills_cases.py",
    }
)
APG55_V05_CRITICAL = frozenset(
    {
        "docs/evaluations/apg55-global-skill-installer-transaction-hardening.md",
        "docs/status/2026/07/29/00075-apg55-global-skill-installer-transaction-hardening-exit.md",
    }
)
APG66_V05_SKILLS = frozenset(
    {"skills/markdown-language-profile/SKILL.md"}
)
APG66_V05_PROJECTIONS = frozenset(
    {".agents/skills/markdown-language-profile"}
)
APG66_V05_TESTS = frozenset(
    {
        "src/test/int/python/agentic-praxis-grimoire/skills/markdown-language-profile/SKILL.int.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/skills/markdown-language-profile/SKILL.unit.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_markdown_candidate_contract.unit.test.py",
    }
)
APG66_V05_CRITICAL = frozenset(
    {
        "docs/adr/2026/07/0038-markdown-language-profile-candidate.md",
        "docs/evaluations/apg66-markdown-language-profile-validation-and-integration.md",
        "docs/specs/markdown-language-profile-scenario-coverage.md",
        "docs/specs/markdown-language-profile.md",
        "docs/status/2026/08/01/00095-apg66-markdown-language-profile-validation-and-integration-exit.md",
        "src/test/fixtures/apg66-markdown-language-profile-scenarios.json",
        "src/test/support/apg_markdown_candidate_contract.py",
    }
)
APG66A_V05_TESTS = frozenset(
    {"src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_markdown_register_contract.unit.test.py"}
)
APG66A_V05_CRITICAL = frozenset(
    {
        "docs/evaluations/apg66a-markdown-replay-evidence-truth.md",
        "docs/status/2026/08/01/00096-apg66a-markdown-replay-evidence-truth-exit.md",
        "src/test/fixtures/apg64-markdown-scenario-register.md",
        "src/test/support/apg_markdown_register_contract.py",
    }
)
APG66B_V05_TESTS = frozenset(
    {
        "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_markdown_polarity_guard_contract.unit.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_markdown_token_guard_contract.unit.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_markdown_vocabulary_contract.unit.test.py",
    }
)
APG66B_V05_CRITICAL = frozenset(
    {
        "docs/evaluations/apg66b-markdown-register-vocabulary-and-guard-exactness.md",
        "docs/status/2026/08/01/00097-apg66b-markdown-register-vocabulary-and-guard-exactness-exit.md",
        "src/test/support/apg_markdown_polarity_guard_contract.py",
        "src/test/support/apg_markdown_token_guard_contract.py",
        "src/test/support/apg_markdown_vocabulary_contract.py",
    }
)
APG66C_V05_TESTS = frozenset(
    {
        "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_markdown_clause_guard_contract.unit.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_repository_import_cache_contract.unit.test.py",
    }
)
APG66C_V05_CRITICAL = frozenset(
    {
        "docs/evaluations/apg66c-markdown-clause-polarity-and-predicate-binding.md",
        "docs/status/2026/08/01/00098-apg66c-markdown-clause-polarity-and-predicate-binding-exit.md",
        "src/test/support/apg_markdown_clause_guard_contract.py",
        "src/test/support/apg_repository_import_cache_contract.py",
    }
)
APG66D_V05_CRITICAL = frozenset(
    {
        "docs/evaluations/apg66d-repository-import-cache-entry-presence.md",
        "docs/status/2026/08/01/00099-apg66d-repository-import-cache-entry-presence-exit.md",
    }
)
APG75_V05_SKILLS = frozenset(
    {"skills/typescript-language-profile/SKILL.md"}
)
APG75_V05_PROJECTIONS = frozenset(
    {".agents/skills/typescript-language-profile"}
)
APG75_V05_TESTS = frozenset(
    {
        "src/test/int/python/agentic-praxis-grimoire/skills/typescript-language-profile/SKILL.int.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/skills/typescript-language-profile/SKILL.unit.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_typescript_candidate_contract.unit.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_typescript_fixture_contract.unit.test.py",
    }
)
APG75_V05_CRITICAL = frozenset(
    {
        "docs/adr/2026/08/0043-typescript-language-profile-candidate-and-intended-state-harness.md",
        "docs/evaluations/apg75-typescript-iterative-hardening-and-integration.md",
        "docs/specs/typescript-language-profile-scenario-coverage.md",
        "docs/specs/typescript-language-profile.md",
        "docs/status/2026/08/03/00108-apg75-typescript-iterative-hardening-and-integration-exit.md",
        "src/test/fixtures/apg75-typescript-language-profile-scenarios.json",
        "src/test/fixtures/apg74-typescript-intended-state/README.md",
        "src/test/fixtures/apg74-typescript-intended-state/fixture-manifest.json",
        "src/test/fixtures/apg74-typescript-intended-state/package.json",
        "src/test/fixtures/apg74-typescript-intended-state/src/checked/config-loader.js",
        "src/test/fixtures/apg74-typescript-intended-state/src/core/inventory.ts",
        "src/test/fixtures/apg74-typescript-intended-state/src/core/runtime-boundary.ts",
        "src/test/fixtures/apg74-typescript-intended-state/src/declarations/host-metrics.d.ts",
        "src/test/fixtures/apg74-typescript-intended-state/src/embedded/widget.astro",
        "src/test/fixtures/apg74-typescript-intended-state/src/modules/legacy.cts",
        "src/test/fixtures/apg74-typescript-intended-state/src/modules/loader.mts",
        "src/test/fixtures/apg74-typescript-intended-state/src/ui/badge.tsx",
        "src/test/fixtures/apg74-typescript-intended-state/src/ui/jsx-host.d.ts",
        "src/test/fixtures/apg74-typescript-intended-state/src/unbound/option-state-unknown.ts",
        "src/test/fixtures/apg74-typescript-intended-state/src/unbound/orphan-role-unknown.ts",
        "src/test/fixtures/apg74-typescript-intended-state/tsconfig.declarations.json",
        "src/test/fixtures/apg74-typescript-intended-state/tsconfig.json",
        "src/test/support/apg_typescript_candidate_contract.py",
        "src/test/support/apg_typescript_fixture_contract.py",
    }
)
APG75A_V05_CRITICAL = frozenset(
    {
        "docs/evaluations/apg75a-typescript-scope-and-lifecycle-closure.md",
        "docs/status/2026/08/03/00109-apg75a-typescript-scope-and-lifecycle-closure-exit.md",
    }
)
APG77D_V05_SKILLS = frozenset(
    {"skills/css-language-profile/SKILL.md"}
)
APG77D_V05_PROJECTIONS = frozenset(
    {".agents/skills/css-language-profile"}
)
APG77D_V05_TESTS = frozenset(
    {
        "src/test/unit/python/agentic-praxis-grimoire/skills/css-language-profile/SKILL.unit.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_css_candidate_contract.unit.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_css_profile_candidate_contract.unit.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_css_profile_fixture_contract.unit.test.py",
    }
)
APG77D_V05_CRITICAL = frozenset(
    {
        "docs/adr/2026/08/0044-css-language-profile-candidate-and-target-first-harness.md",
        "docs/evaluations/apg76-css-language-profile-candidate-recovery.md",
        "docs/evaluations/apg77-css-iterative-hardening-and-integration.md",
        "docs/evaluations/apg77a-css-evidence-retention-closure-and-integration.md",
        "docs/evaluations/apg77b-css-traceability-clean-room-closure-and-integration.md",
        "docs/evaluations/apg77c-css-evidence-proportionality-and-integration.md",
        "docs/evaluations/apg77d-css-known-debt-and-provisional-integration.md",
        "docs/governance/language-profile-known-debt.json",
        "docs/governance/language-profile-known-debt.md",
        "docs/specs/css-language-profile-scenario-coverage.md",
        "docs/specs/css-language-profile.md",
        "docs/status/2026/08/04/00110-apg76-css-language-profile-candidate-recovery-exit.md",
        "docs/status/2026/08/04/00111-apg77-css-iterative-hardening-and-integration-exit.md",
        "docs/status/2026/08/06/00112-apg77a-css-evidence-retention-closure-and-integration-exit.md",
        "docs/status/2026/08/06/00113-apg77b-css-traceability-clean-room-closure-and-integration-exit.md",
        "docs/status/2026/08/07/00114-apg77c-css-evidence-proportionality-and-integration-exit.md",
        "docs/status/2026/08/08/00115-apg77d-css-known-debt-and-provisional-integration-exit.md",
        "src/test/fixtures/apg76-css-target-first/README.md",
        "src/test/fixtures/apg76-css-target-first/fixture-manifest.json",
        "src/test/fixtures/apg76-css-target-first/src/base.css",
        "src/test/fixtures/apg76-css-target-first/src/cascade.css",
        "src/test/fixtures/apg76-css-target-first/src/conditions.css",
        "src/test/fixtures/apg76-css-target-first/src/custom-properties.css",
        "src/test/fixtures/apg76-css-target-first/src/generated-boundary.css",
        "src/test/fixtures/apg76-css-target-first/src/host-boundary.astro",
        "src/test/fixtures/apg76-css-target-first/src/nesting.css",
        "src/test/fixtures/apg76-css-target-first/src/units-and-color.css",
        "src/test/fixtures/apg76-css-target-first/src/unknown-environment.css",
        "src/test/fixtures/apg77-css-language-profile-scenarios.json",
        "src/test/support/apg_css_candidate_contract.py",
        "src/test/support/apg_css_profile_candidate_contract.py",
        "src/test/support/apg_css_profile_fixture_contract.py",
    }
)
APG79E_V05_SKILLS = frozenset(
    {"skills/javascript-language-profile/SKILL.md"}
)
APG79E_V05_PROJECTIONS = frozenset(
    {".agents/skills/javascript-language-profile"}
)
APG79E_V05_TESTS = frozenset(
    {
        "src/test/int/python/agentic-praxis-grimoire/skills/javascript-language-profile/SKILL.int.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/skills/javascript-language-profile/SKILL.unit.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_javascript_candidate_contract.unit.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_javascript_fixture_contract.unit.test.py",
    }
)
APG79E_V05_CRITICAL = frozenset(
    {
        "docs/adr/2026/08/0045-javascript-language-profile-candidate-and-target-first-harness.md",
        "docs/evaluations/apg78-javascript-core-candidate.md",
        "docs/evaluations/apg79-javascript-core-iterative-hardening-and-integration.md",
        "docs/evaluations/apg79a-javascript-terminal-proof-closure-and-integration.md",
        "docs/evaluations/apg79b-javascript-contract-harness-closure-and-integration.md",
        "docs/evaluations/apg79c-javascript-known-debt-and-provisional-integration.md",
        "docs/evaluations/apg79d-test262-source-evidence-and-javascript-integration.md",
        "docs/evaluations/apg79e-javascript-report-binding-debt-and-provisional-integration.md",
        "docs/specs/javascript-language-profile-scenario-coverage.md",
        "docs/specs/javascript-language-profile.md",
        "docs/status/2026/08/08/00116-apg78-javascript-core-candidate-exit.md",
        "docs/status/2026/08/08/00117-apg79-javascript-core-iterative-hardening-and-integration-exit.md",
        "docs/status/2026/08/08/00118-apg79a-javascript-terminal-proof-closure-and-integration-exit.md",
        "docs/status/2026/08/08/00119-apg79b-javascript-contract-harness-closure-and-integration-exit.md",
        "docs/status/2026/08/08/00120-apg79c-javascript-known-debt-and-provisional-integration-exit.md",
        "docs/status/2026/08/08/00121-apg79d-test262-source-evidence-and-javascript-integration-exit.md",
        "docs/status/2026/08/09/00122-apg79e-javascript-report-binding-debt-and-provisional-integration-exit.md",
        "src/test/fixtures/apg79-javascript-language-profile-scenarios.json",
        "src/test/fixtures/apg78-javascript-core/README.md",
        "src/test/fixtures/apg78-javascript-core/fixture-manifest.json",
        "src/test/fixtures/apg78-javascript-core/package.json",
        "src/test/fixtures/apg78-javascript-core/src/async.mjs",
        "src/test/fixtures/apg78-javascript-core/src/checked.js",
        "src/test/fixtures/apg78-javascript-core/src/cli-core.mjs",
        "src/test/fixtures/apg78-javascript-core/src/cli-node-adapter-boundary.cjs",
        "src/test/fixtures/apg78-javascript-core/src/coercion.mjs",
        "src/test/fixtures/apg78-javascript-core/src/commonjs-boundary.cjs",
        "src/test/fixtures/apg78-javascript-core/src/dynamic-import-boundary.mjs",
        "src/test/fixtures/apg78-javascript-core/src/errors.mjs",
        "src/test/fixtures/apg78-javascript-core/src/evaluation.mjs",
        "src/test/fixtures/apg78-javascript-core/src/functions.mjs",
        "src/test/fixtures/apg78-javascript-core/src/iteration.mjs",
        "src/test/fixtures/apg78-javascript-core/src/mode-selected.js",
        "src/test/fixtures/apg78-javascript-core/src/module-boundary.mjs",
        "src/test/fixtures/apg78-javascript-core/src/modules/consumer.mjs",
        "src/test/fixtures/apg78-javascript-core/src/modules/counter.mjs",
        "src/test/fixtures/apg78-javascript-core/src/modules/cycle-a.mjs",
        "src/test/fixtures/apg78-javascript-core/src/modules/cycle-b.mjs",
        "src/test/fixtures/apg78-javascript-core/src/modules/top-level-await.mjs",
        "src/test/fixtures/apg78-javascript-core/src/objects.mjs",
        "src/test/fixtures/apg78-javascript-core/src/scope.mjs",
        "src/test/fixtures/apg78-javascript-core/unbound/mode-neutral.js.txt",
        "src/test/fixtures/apg78-javascript-core/unbound/sloppy-script.js.txt",
        "src/test/fixtures/apg78-javascript-core/unbound/strict-script.js.txt",
        "src/test/support/apg_javascript_candidate_contract.py",
        "src/test/support/apg_javascript_fixture_contract.py",
    }
)
APG81H_V05_SKILLS = frozenset(
    {"skills/nodejs-runtime-profile/SKILL.md"}
)
APG81H_V05_PROJECTIONS = frozenset(
    {".agents/skills/nodejs-runtime-profile"}
)
APG81H_V05_TESTS = frozenset(
    {
        "src/test/int/python/agentic-praxis-grimoire/skills/nodejs-runtime-profile/SKILL.int.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/skills/nodejs-runtime-profile/SKILL.unit.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_nodejs_candidate_contract.unit.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_nodejs_fixture_contract.unit.test.py",
    }
)
APG81H_V05_CRITICAL = frozenset(
    {
        "docs/adr/2026/08/0046-nodejs-runtime-and-cli-stack-candidate-and-target-first-harness.md",
        "docs/evaluations/apg80-nodejs-runtime-and-cli-stack-candidate.md",
        "docs/evaluations/apg81-nodejs-runtime-cli-iterative-hardening-and-integration.md",
        "docs/evaluations/apg81a-nodejs-qualification-threat-model-and-harness-simplification.md",
        "docs/evaluations/apg81b-nodejs-integration-contract-clarification-and-provisional-adoption.md",
        "docs/evaluations/apg81c-nodejs-lifecycle-test-and-scratch-closure.md",
        "docs/evaluations/apg81d-nodejs-provisional-integration.md",
        "docs/evaluations/apg81e-nodejs-final-integration-closure.md",
        "docs/evaluations/apg81f-nodejs-actual-test-projection-and-integration-closure.md",
        "docs/evaluations/apg81g-nodejs-selector-release-and-integration-closure.md",
        "docs/evaluations/apg81h-nodejs-reviewable-qualification-and-integration-closure.md",
        "docs/specs/nodejs-runtime-profile-scenario-coverage.md",
        "docs/specs/nodejs-runtime-profile.md",
        "docs/status/2026/08/09/00123-apg80-nodejs-runtime-and-cli-stack-candidate-exit.md",
        "docs/status/2026/08/10/00124-apg81-nodejs-runtime-cli-iterative-hardening-and-integration-exit.md",
        "docs/status/2026/08/10/00125-apg81a-nodejs-qualification-threat-model-and-harness-simplification-exit.md",
        "docs/status/2026/08/10/00126-apg81b-nodejs-integration-contract-clarification-and-provisional-adoption-exit.md",
        "docs/status/2026/08/10/00127-apg81c-nodejs-lifecycle-test-and-scratch-closure-exit.md",
        "docs/status/2026/08/10/00128-apg81d-nodejs-provisional-integration-exit.md",
        "docs/status/2026/08/11/00129-apg81e-nodejs-final-integration-closure-exit.md",
        "docs/status/2026/08/11/00130-apg81f-nodejs-actual-test-projection-and-integration-closure-exit.md",
        "docs/status/2026/08/11/00131-apg81g-nodejs-selector-release-and-integration-closure-exit.md",
        "docs/status/2026/08/11/00132-apg81h-nodejs-reviewable-qualification-and-integration-closure-exit.md",
        "src/test/fixtures/apg80-nodejs-runtime-cli/README.md",
        "src/test/fixtures/apg80-nodejs-runtime-cli/cli/adapter.mjs",
        "src/test/fixtures/apg80-nodejs-runtime-cli/cli/core.mjs",
        "src/test/fixtures/apg80-nodejs-runtime-cli/commonjs/local-dependency.cjs",
        "src/test/fixtures/apg80-nodejs-runtime-cli/commonjs/wrapper-boundary.cjs",
        "src/test/fixtures/apg80-nodejs-runtime-cli/esm/builtin-boundary.mjs",
        "src/test/fixtures/apg80-nodejs-runtime-cli/esm/metadata.mjs",
        "src/test/fixtures/apg80-nodejs-runtime-cli/fixture-manifest.json",
        "src/test/fixtures/apg80-nodejs-runtime-cli/interop/dynamic-exports.cjs",
        "src/test/fixtures/apg80-nodejs-runtime-cli/interop/esm-consumer.mjs",
        "src/test/fixtures/apg80-nodejs-runtime-cli/interop/identity.mjs",
        "src/test/fixtures/apg80-nodejs-runtime-cli/interop/require-esm.cjs",
        "src/test/fixtures/apg80-nodejs-runtime-cli/interop/static-exports.cjs",
        "src/test/fixtures/apg80-nodejs-runtime-cli/module-mapping/commonjs-package/module-only.js",
        "src/test/fixtures/apg80-nodejs-runtime-cli/module-mapping/commonjs-package/package.json",
        "src/test/fixtures/apg80-nodejs-runtime-cli/module-mapping/commonjs-package/source.js",
        "src/test/fixtures/apg80-nodejs-runtime-cli/module-mapping/explicit-commonjs.cjs",
        "src/test/fixtures/apg80-nodejs-runtime-cli/module-mapping/explicit-module.mjs",
        "src/test/fixtures/apg80-nodejs-runtime-cli/module-mapping/module-package/package.json",
        "src/test/fixtures/apg80-nodejs-runtime-cli/module-mapping/module-package/source.js",
        "src/test/fixtures/apg80-nodejs-runtime-cli/module-mapping/typeless-package/detected-module.js",
        "src/test/fixtures/apg80-nodejs-runtime-cli/module-mapping/typeless-package/goal-neutral.js",
        "src/test/fixtures/apg80-nodejs-runtime-cli/module-mapping/typeless-package/package.json",
        "src/test/fixtures/apg80-nodejs-runtime-cli/package.json",
        "src/test/fixtures/apg80-nodejs-runtime-cli/process/event-loop-entry.cjs",
        "src/test/fixtures/apg80-nodejs-runtime-cli/process/event-loop.mjs",
        "src/test/fixtures/apg80-nodejs-runtime-cli/process/filesystem.mjs",
        "src/test/fixtures/apg80-nodejs-runtime-cli/process/inputs.mjs",
        "src/test/fixtures/apg80-nodejs-runtime-cli/process/lifecycle-child.mjs",
        "src/test/fixtures/apg80-nodejs-runtime-cli/process/lifecycle-parent.mjs",
        "src/test/fixtures/apg80-nodejs-runtime-cli/process/stdio.mjs",
        "src/test/fixtures/apg80-nodejs-runtime-cli/resolution/entry.mjs",
        "src/test/fixtures/apg80-nodejs-runtime-cli/resolution/lib/condition-custom.mjs",
        "src/test/fixtures/apg80-nodejs-runtime-cli/resolution/lib/condition-default.mjs",
        "src/test/fixtures/apg80-nodejs-runtime-cli/resolution/lib/encapsulated.mjs",
        "src/test/fixtures/apg80-nodejs-runtime-cli/resolution/lib/internal-only.mjs",
        "src/test/fixtures/apg80-nodejs-runtime-cli/resolution/lib/public-entry.mjs",
        "src/test/fixtures/apg80-nodejs-runtime-cli/resolution/lib/public-subpath.mjs",
        "src/test/fixtures/apg80-nodejs-runtime-cli/resolution/package.json",
        "src/test/fixtures/apg80-nodejs-runtime-cli/runtime/identity.mjs",
        "src/test/fixtures/apg80-nodejs-runtime-cli/target-boundary/public-safe-runtime-role.json",
        "src/test/fixtures/apg80-nodejs-runtime-cli/typescript/erasable.ts",
        "src/test/fixtures/apg80-nodejs-runtime-cli/typescript/nonerasable.ts",
        "src/test/fixtures/apg81-nodejs-runtime-profile-scenarios.json",
        "src/test/support/apg_nodejs_candidate_contract.py",
        "src/test/support/apg_nodejs_fixture_contract.py",
        "testing/nodejs-profile-qualification-threat-model.json",
    }
)
APG82_V05_WRAPPERS = frozenset({"bin/apgr"})
APG82_V05_HELPERS = frozenset(
    {
        "src/agentic_praxis_grimoire/__init__.py",
        "src/agentic_praxis_grimoire/__main__.py",
        "src/agentic_praxis_grimoire/cli.py",
        "src/agentic_praxis_grimoire/config.py",
        "src/agentic_praxis_grimoire/paths.py",
        "src/agentic_praxis_grimoire/reports.py",
        "src/agentic_praxis_grimoire/resources/__init__.py",
        "src/agentic_praxis_grimoire/response.py",
        "src/agentic_praxis_grimoire/skills.py",
        "src/agentic_praxis_grimoire/version.py",
    }
)
APG82_V05_TESTS = frozenset(
    {
        "src/test/int/python/agentic-praxis-grimoire/src/agentic_praxis_grimoire/cli.int.test.py",
        "src/test/int/python/agentic-praxis-grimoire/src/agentic_praxis_grimoire/reports.int.test.py",
        "src/test/int/python/agentic-praxis-grimoire/src/agentic_praxis_grimoire/response.int.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/src/agentic_praxis_grimoire/cli.unit.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/src/agentic_praxis_grimoire/config.unit.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/src/agentic_praxis_grimoire/paths.unit.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/src/agentic_praxis_grimoire/reports.unit.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/src/agentic_praxis_grimoire/response.unit.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/src/agentic_praxis_grimoire/skills.unit.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/src/agentic_praxis_grimoire/version.unit.test.py",
    }
)
APG82_PACKAGE_RESOURCES = frozenset(
    {"src/agentic_praxis_grimoire/resources/skill-metadata.json"}
)
APG82_V05_CRITICAL = frozenset(
    {
        "docs/evaluations/apg82-apgr-cli-distribution-configuration-and-artifact-contract-foundation.md",
        "docs/status/2026/08/15/00133-apg82-apgr-cli-distribution-configuration-and-artifact-contract-foundation-exit.md",
        "docs/v0-6-roadmap.md",
        "pyproject.toml",
        "src/agentic_praxis_grimoire/VERSION",
    }
) | APG82_PACKAGE_RESOURCES

APG83_V05_WRAPPERS = frozenset({"bin/apg-normalize-python-sdist"})
APG83_V05_HELPERS = frozenset({"libexec/apg_python_distribution.py"})
APG83_V05_TESTS = frozenset(
    {
        "src/test/int/python/agentic-praxis-grimoire/bin/apg-normalize-python-sdist.int.test.py",
        "src/test/int/python/agentic-praxis-grimoire/libexec/apg_python_distribution.int.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/libexec/apg_python_distribution.unit.test.py",
    }
)
APG83_V05_CRITICAL = frozenset(
    {
        "docs/evaluations/apg83-v0-5-bounded-dogfood-and-release-readiness.md",
        "docs/status/2026/08/16/00134-apg83-v0-5-bounded-dogfood-and-release-readiness-exit.md",
    }
)

APG84_V05_WRAPPERS = frozenset({"bin/apg-build-python-release-bundle"})
APG84_V05_HELPERS = frozenset({"libexec/apg_python_publication.py"})
APG84_V05_TESTS = frozenset(
    {
        "src/test/int/python/agentic-praxis-grimoire/bin/apg-build-python-release-bundle.int.test.py",
        "src/test/int/python/agentic-praxis-grimoire/.github/workflows/release.yml.int.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/.github/workflows/release.yml.unit.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/libexec/apg_python_publication.unit.test.py",
    }
)
APG84_V05_CRITICAL = frozenset(
    {
        ".github/workflows/release.yml",
        "docs/evaluations/apg84-v0-5-public-github-and-pypi-publication.md",
        "docs/status/2026/08/16/00135-apg84-v0-5-public-github-and-pypi-publication-exit.md",
        "release/v0.5.0-notes.md",
    }
)

APG86_V06_SKILLS = frozenset(
    {
        "skills/gomock-test-profile/SKILL.md",
        "skills/vitest-test-profile/SKILL.md",
    }
)
APG86_V06_PROJECTIONS = frozenset(
    {
        ".agents/skills/gomock-test-profile",
        ".agents/skills/vitest-test-profile",
    }
)
APG86_V06_TESTS = frozenset(
    {
        "src/test/unit/python/agentic-praxis-grimoire/skills/gomock-test-profile/SKILL.unit.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/skills/vitest-test-profile/SKILL.unit.test.py",
    }
)
APG86_V06_CRITICAL = frozenset(
    {
        "docs/adr/2026/08/0048-gomock-vitest-profiles-and-context-budget-enforcement.md",
        "docs/evaluations/apg86-gomock-vitest-profiles-and-context-budget-enforcement.md",
        "docs/status/2026/08/20/00137-apg86-gomock-vitest-profiles-and-context-budget-enforcement-exit.md",
        "src/test/fixtures/apg86-profile-boundary-scenarios.json",
    }
)

APG87_V06_SKILLS = frozenset(
    {
        "skills/jsx-language-profile/SKILL.md",
        "skills/react-component-profile/SKILL.md",
    }
)
APG87_V06_PROJECTIONS = frozenset(
    {
        ".agents/skills/jsx-language-profile",
        ".agents/skills/react-component-profile",
    }
)
APG87_V06_TESTS = frozenset(
    {
        "src/test/unit/python/agentic-praxis-grimoire/skills/jsx-language-profile/SKILL.unit.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/skills/react-component-profile/SKILL.unit.test.py",
    }
)
APG87_V06_CRITICAL = frozenset(
    {
        "docs/adr/2026/08/0049-jsx-react-profiles-and-apg88-headroom-conservation.md",
        "docs/evaluations/apg87-jsx-react-profiles-and-apg88-headroom-conservation.md",
        "docs/status/2026/08/20/00138-apg87-jsx-react-profiles-and-apg88-headroom-conservation-exit.md",
        "src/test/fixtures/apg87-profile-boundary-scenarios.json",
    }
)

APG88_V06_SKILLS = frozenset(
    {
        "skills/astro-profile/SKILL.md",
        "skills/mdx-profile/SKILL.md",
    }
)
APG88_V06_PROJECTIONS = frozenset(
    {
        ".agents/skills/astro-profile",
        ".agents/skills/mdx-profile",
    }
)
APG88_V06_TESTS = frozenset(
    {
        "src/test/unit/python/agentic-praxis-grimoire/skills/astro-profile/SKILL.unit.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/skills/mdx-profile/SKILL.unit.test.py",
    }
)
APG88_V06_CRITICAL = frozenset(
    {
        "docs/adr/2026/08/0050-mdx-astro-profiles-and-v0-6-authoring-completion.md",
        "docs/evaluations/apg88-mdx-astro-profiles-and-v0-6-authoring-completion.md",
        "docs/status/2026/08/20/00139-apg88-mdx-astro-profiles-and-v0-6-authoring-completion-exit.md",
        "src/test/fixtures/apg88-profile-boundary-scenarios.json",
    }
)

APG89_V06_CRITICAL = frozenset(
    {
        "docs/evaluations/apg89-v0-6-dogfood-composition-context-and-readiness.md",
        "docs/status/2026/08/20/00140-apg89-v0-6-dogfood-composition-context-and-readiness-exit.md",
        "src/test/fixtures/apg89-profile-composition-scenarios.json",
    }
)

APG90_V06_CRITICAL = frozenset(
    {
        "docs/evaluations/apg90-v0-6-publication-preparation-and-public-release-handoff.md",
        "docs/status/2026/08/21/00141-apg90-v0-6-publication-preparation-and-public-release-handoff-exit.md",
        "release/v0.6.0-notes.md",
    }
)

AUDITED_SKILLS = tuple(
    sorted(
        set(AUDITED_SKILLS)
        | APG86_V06_SKILLS
        | APG87_V06_SKILLS
        | APG88_V06_SKILLS
    )
)
AUDITED_PROJECTIONS = tuple(
    sorted(
        set(AUDITED_PROJECTIONS)
        | APG86_V06_PROJECTIONS
        | APG87_V06_PROJECTIONS
        | APG88_V06_PROJECTIONS
    )
)

AUDITED_WRAPPERS = tuple(
    sorted(
        set(AUDITED_WRAPPERS)
        | APG82_V05_WRAPPERS
        | APG83_V05_WRAPPERS
        | APG84_V05_WRAPPERS
    )
)
AUDITED_HELPERS = tuple(
    sorted(
        set(AUDITED_HELPERS)
        | APG82_V05_HELPERS
        | APG83_V05_HELPERS
        | APG84_V05_HELPERS
    )
)
AUDITED_TESTS = tuple(
    sorted(
        set(AUDITED_TESTS)
        | APG82_V05_TESTS
        | APG83_V05_TESTS
        | APG84_V05_TESTS
        | APG86_V06_TESTS
        | APG87_V06_TESTS
        | APG88_V06_TESTS
    )
)
AUDITED_CRITICAL = tuple(
    sorted(
        set(AUDITED_CRITICAL)
        | APG82_V05_CRITICAL
        | APG83_V05_CRITICAL
        | APG84_V05_CRITICAL
        | APG86_V06_CRITICAL
        | APG87_V06_CRITICAL
        | APG88_V06_CRITICAL
        | APG89_V06_CRITICAL
        | APG90_V06_CRITICAL
    )
)

# Keep the published v0.6 surface independent from the mutable current
# development surface.  The v0.6 policy is historical evidence, not the
# authority for the v0.7 source candidate.
HISTORICAL_V06_WRAPPERS = tuple(AUDITED_WRAPPERS)
HISTORICAL_V06_HELPERS = tuple(AUDITED_HELPERS)
HISTORICAL_V06_TESTS = tuple(AUDITED_TESTS)
HISTORICAL_V06_CRITICAL = tuple(AUDITED_CRITICAL)
HISTORICAL_V06_LICENSING = tuple(AUDITED_LICENSING)
HISTORICAL_V06_PROJECTIONS = tuple(AUDITED_PROJECTIONS)
HISTORICAL_V06_SKILLS = tuple(AUDITED_SKILLS)
HISTORICAL_V06_CATEGORIES = tuple(sorted(ALLOWED_CATEGORIES))
HISTORICAL_V06_SURFACE_SHA256 = (
    "40edfbe25f52fae4f15f2801525ce2c50cee5f360b02191393a431ca25f76b51"
)

# These are retained compatibility wrappers, not the old Python report
# implementation.  The latter is deliberately omitted from the v0.7 source
# projection and remains available only in the development checkout/tests.
V07_WRAPPERS = tuple(HISTORICAL_V06_WRAPPERS)
V07_HELPERS = tuple(
    sorted(
        {
            *(
                path
                for path in HISTORICAL_V06_HELPERS
                if not path.startswith("libexec/agent_report/")
                and path != "src/agentic_praxis_grimoire/skills.py"
            ),
            # v0.7's source distribution, Go build, and npm packer are release
            # maintenance owners, not runtime semantic implementations.
            "libexec/apg_distribution_candidate.py",
            "libexec/apg_distribution_candidate_archives.py",
            "libexec/apg_distribution_candidate_contract.py",
            "libexec/apg_go_build.py",
            "libexec/apg_npm_distribution.py",
            "libexec/apg_phase_commit_message.py",
            "libexec/apg_python_build_backend.py",
            "src/agentic_praxis_grimoire/go_bridge.py",
        }
    )
)
V07_TESTS = tuple(
    sorted(
        {
            *(
                path
                for path in HISTORICAL_V06_TESTS
                if not (
                    path.startswith("src/test/unit/python/agentic-praxis-grimoire/libexec/agent_report/")
                    or path.startswith("src/test/int/python/agentic-praxis-grimoire/libexec/agent_report/")
                    or path.startswith("src/test/unit/bash/append-operational-report.")
                    or path.startswith("src/test/unit/bash/git-show-report.")
                    or path in {
                        "src/test/int/python/agentic-praxis-grimoire/bin/append-operational-report.int.test.py",
                        "src/test/int/python/agentic-praxis-grimoire/bin/git-diff-report.int.test.py",
                        "src/test/int/python/agentic-praxis-grimoire/bin/git-show-report.int.test.py",
                        "src/test/int/python/agentic-praxis-grimoire/src/agentic_praxis_grimoire/reports.int.test.py",
                        "src/test/int/python/agentic-praxis-grimoire/libexec/apg_test.int.test.py",
                        "src/test/unit/python/agentic-praxis-grimoire/src/agentic_praxis_grimoire/skills.unit.test.py",
                    }
                )
            ),
            "npm/test/launcher.test.cjs",
            "src/test/int/python/agentic-praxis-grimoire/bin/apg-build-go-cli.int.test.py",
            "src/test/int/python/agentic-praxis-grimoire/docs/environment-snapshots.int.test.py",
            "src/test/int/python/agentic-praxis-grimoire/skills/css-language-profile/SKILL.int.test.py",
            "src/test/int/python/agentic-praxis-grimoire/src/test/support/apg_css_candidate_contract.int.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/docs/evaluations/apg98-portable-environment-snapshots-and-resolution.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/docs/provenance.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/libexec/apg_distribution_candidate.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/libexec/apg_go_build.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/libexec/apg_npm_distribution.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/agentic_praxis_grimoire/go_bridge.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/fixtures/apg60-css-reentry-contract.json.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_actual_retained_surface_contract.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_candidate_actual_lifecycle_contract.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_candidate_current_state_contract.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_candidate_decision_contract.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_candidate_history_contract.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_candidate_lifecycle_schema_contract.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_candidate_narrative_state_contract.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_candidate_phase_history_contract.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_candidate_required_role_registry.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_candidate_surface_contract.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_candidate_traceability_contract.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_css_evidence_retention_contract.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_exact_read_contract.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_live_owner_binding_contract.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_pinned_root_contract.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_python_source_binding_contract.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_repository_absence_contract.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_repository_import_contract.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_repository_import_descriptor_contract.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_repository_path_contract.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_repository_projection_contract.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_repository_snapshot_contract.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_skill_set_contract.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_worker_temp_cleanup_contract.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_worker_temp_contract.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_worker_temp_root_binding_contract.unit.test.py",
        }
    )
)
# These exact public-projected tests consume publication-excluded development
# history or private source oracles. The private canonical gate continues to
# run them; the release-shaped candidate cannot truthfully reconstruct those
# inputs. Keep this node-level list narrower than the public test entrypoints.
V07_PUBLIC_VALIDATION_DESELECTIONS = tuple(
    sorted(
        {
            "src/test/int/python/agentic-praxis-grimoire/skills/css-language-profile/SKILL.int.test.py::test_candidate_fixture_debt_and_repository_lifecycle_agree",
            "src/test/int/python/agentic-praxis-grimoire/skills/css-language-profile/SKILL.int.test.py::test_disposable_rollback_reconstructs_preintegration_owners",
            "src/test/int/python/agentic-praxis-grimoire/src/agentic_praxis_grimoire/cli.int.test.py::test_python_skill_bridge_matches_oracle_and_routes_new_go_surfaces",
            "src/test/int/python/agentic-praxis-grimoire/src/test/support/apg_css_candidate_contract.int.test.py::test_apg59_and_live_counts_preserve_css_rejection_across_growth",
            "src/test/int/python/agentic-praxis-grimoire/src/test/support/apg_css_candidate_contract.int.test.py::test_apg60a_revision_preserves_exact_unrelated_contract_semantics",
            "src/test/int/python/agentic-praxis-grimoire/src/test/support/apg_css_candidate_contract.int.test.py::test_exact_apg58_apg59_history_and_live_integrated_surface",
            "src/test/int/python/agentic-praxis-grimoire/src/test/support/apg_css_candidate_contract.int.test.py::test_raw_apg59_revert_restores_candidate_and_fails_closure",
        }
    )
)
V07_CRITICAL = tuple(
    sorted(
        set(HISTORICAL_V06_CRITICAL)
        | {
            "cmd/apgr/main.go",
            "go.mod",
            "internal/atomicfile/atomicfile.go",
            "internal/buildinfo/buildinfo.go",
            "internal/cli/analyze.go",
            "internal/cli/cli.go",
            "internal/cli/env.go",
            "internal/cli/legacy.go",
            "internal/cli/operational.go",
            "internal/cli/publication.go",
            "internal/cli/report.go",
            "internal/cli/skills.go",
            "internal/cli/source.go",
            "internal/gitexec/gitexec.go",
            "internal/response/response.go",
            "libexec/apg_go_build.py",
            "npm/README.md",
            "npm/templates/launcher/index.js",
            "npm/templates/launcher/package.json",
            "npm/templates/platform/package.json",
            "report/append.go",
            "report/doc.go",
            "report/service.go",
            "src/agentic_praxis_grimoire/go_bridge.py",
        }
    )
)
V07_LICENSING = tuple(HISTORICAL_V06_LICENSING)
V07_PROJECTIONS = tuple(HISTORICAL_V06_PROJECTIONS)
V07_SKILLS = tuple(HISTORICAL_V06_SKILLS)
V07_CATEGORIES = tuple(HISTORICAL_V06_CATEGORIES)

# v0.8 is an additive source candidate.  These policy tuples intentionally
# have their own identity instead of mutating the v0.7 snapshot or reusing its
# candidate-path oracle.  The v0.7 wrappers, helpers, skills, projections, and
# validation categories remain unchanged; only the v0.8 footprint owners and
# release-facing records are added to the critical-file contract.
V08_WRAPPERS = tuple(V07_WRAPPERS)
V08_HELPERS = tuple(V07_HELPERS)
V08_TESTS = tuple(
    sorted(
        set(V07_TESTS)
        | {
            "footprint/comparison_test.go",
            "footprint/flow_test.go",
            "footprint/footprint_test.go",
            "footprint/json_test.go",
            "footprint/projection_test.go",
            "footprint/registry_test.go",
            "internal/cli/footprint_test.go",
            "skills/footprint_test.go",
            "testing/fixtures/external_consumer/consumer_test.go",
        }
    )
)
V08_CRITICAL = tuple(
    sorted(
        set(V07_CRITICAL)
        | {
            "docs/adr/2026/08/0052-v0-8-context-footprint-and-skill-inventory.md",
            "docs/architecture/v0-8-context-footprint-and-skill-inventory.md",
            "docs/evaluations/apg104-v0-8-context-footprint-and-skill-inventory.md",
            "docs/reference/cli.md",
            "docs/reference/go-library.md",
            "docs/distribution.md",
            "docs/v0-8-roadmap.md",
            "docs/status/2026/08/30/00152-apg103-v0-7-public-publication-and-readback-exit.md",
            "docs/status/2026/08/30/00153-apg104-v0-8-context-footprint-implementation-candidate-exit.md",
            "footprint/compare.go",
            "footprint/doc.go",
            "footprint/errors.go",
            "footprint/json.go",
            "footprint/measure.go",
            "footprint/project.go",
            "footprint/testdata/record.golden.json",
            "footprint/types.go",
            "footprint/validation.go",
            "internal/cli/footprint.go",
            "skills/footprint.go",
            "release/v0.8.0-notes.md",
            "testing/fixtures/external_consumer/README.md",
            "testing/fixtures/external_consumer/fixture-go.mod",
            "testing/fixtures/external_consumer/main.go",
        }
    )
)
V08_LICENSING = tuple(V07_LICENSING)
V08_PROJECTIONS = tuple(V07_PROJECTIONS)
V08_SKILLS = tuple(V07_SKILLS)
V08_CATEGORIES = tuple(V07_CATEGORIES)

V081_WRAPPERS = tuple(V08_WRAPPERS)
V081_HELPERS = tuple(V08_HELPERS)
V081_TESTS = tuple(V08_TESTS)
V081_CRITICAL = tuple(
    sorted(
        set(V08_CRITICAL)
        | {
            "docs/status/2026/09/03/00154-apg107-108-v081-qualification-and-recovery-exit.md",
            "npm/templates/launcher/README.md",
            "npm/templates/platform/README.md",
            "release/v0.8.1-notes.md",
        }
    )
)
V081_LICENSING = tuple(V08_LICENSING)
V081_PROJECTIONS = tuple(V08_PROJECTIONS)
V081_SKILLS = tuple(V08_SKILLS)
V081_CATEGORIES = tuple(V08_CATEGORIES)

# Source-only test oracles and generated/local output never enter the
# release-shaped v0.7 candidate. The compatibility wrappers above are not
# excluded because they invoke the Go owner through the normal bridge.
V07_EXCLUDED_PREFIXES = (
    "libexec/agent_report/",
    "report/testdata/",
    "src/test/int/python/agentic-praxis-grimoire/libexec/agent_report/",
    "src/test/unit/python/agentic-praxis-grimoire/libexec/agent_report/",
)
V07_EXCLUDED_PATHS = frozenset(
    {
        "src/test/int/python/agentic-praxis-grimoire/bin/append-operational-report.int.test.py",
        "src/test/int/python/agentic-praxis-grimoire/bin/git-diff-report.int.test.py",
        "src/test/int/python/agentic-praxis-grimoire/bin/git-show-report.int.test.py",
        "src/test/int/python/agentic-praxis-grimoire/src/agentic_praxis_grimoire/reports.int.test.py",
        "src/test/int/python/agentic-praxis-grimoire/libexec/apg_test.int.test.py",
        "src/agentic_praxis_grimoire/skills.py",
        "src/test/unit/python/agentic-praxis-grimoire/src/agentic_praxis_grimoire/skills.unit.test.py",
        "src/test/unit/bash/append-operational-report.unit.test.bats",
        "src/test/unit/bash/git-show-report.unit.test.bats",
    }
)
V07_GENERATED_PATHS = frozenset(
    {
        "bin/apgr-darwin-arm64",
        "bin/apgr-linux-amd64",
        "bin/apgr-linux-arm64",
    }
)
V07_GENERATED_PREFIXES = (
    ".scratch/",
    ".venv/",
    ".pytest_cache/",
    "build/",
    "dist/",
    "node_modules/",
)
V07_GENERATED_SUFFIXES = (
    ".pyc",
    ".pyo",
    ".whl",
    ".tar",
    ".tar.gz",
    ".tgz",
    ".zip",
)

POST_V04_WRAPPERS = (
    APG53_V05_WRAPPERS | APG54_V05_WRAPPERS | APG82_V05_WRAPPERS
    | APG83_V05_WRAPPERS | APG84_V05_WRAPPERS
)
POST_V04_HELPERS = (
    APG53_V05_HELPERS | APG54_V05_HELPERS | APG82_V05_HELPERS
    | APG83_V05_HELPERS | APG84_V05_HELPERS
)
POST_V04_TESTS = (
    APG53_V05_TESTS | APG54_V05_TESTS | APG66_V05_TESTS | APG75_V05_TESTS
    | APG77D_V05_TESTS | APG79E_V05_TESTS | APG81H_V05_TESTS
    | APG66A_V05_TESTS | APG66B_V05_TESTS | APG66C_V05_TESTS
    | APG82_V05_TESTS | APG83_V05_TESTS | APG84_V05_TESTS
    | APG86_V06_TESTS
    | APG87_V06_TESTS
    | APG88_V06_TESTS
)
POST_V04_CRITICAL = (
    APG53_V05_CRITICAL
    | APG54_V05_CRITICAL
    | APG55_V05_CRITICAL
    | APG66_V05_CRITICAL
    | APG66A_V05_CRITICAL
    | APG66B_V05_CRITICAL
    | APG66C_V05_CRITICAL
    | APG66D_V05_CRITICAL
    | APG75_V05_CRITICAL
    | APG75A_V05_CRITICAL
    | APG77D_V05_CRITICAL
    | APG79E_V05_CRITICAL
    | APG81H_V05_CRITICAL
    | APG82_V05_CRITICAL
    | APG83_V05_CRITICAL
    | APG84_V05_CRITICAL
    | APG86_V06_CRITICAL
    | APG87_V06_CRITICAL
    | APG88_V06_CRITICAL
    | APG89_V06_CRITICAL
    | APG90_V06_CRITICAL
)
HISTORICAL_V04_WRAPPERS = tuple(
    item for item in AUDITED_WRAPPERS if item not in POST_V04_WRAPPERS
)
HISTORICAL_V04_HELPERS = tuple(
    item for item in AUDITED_HELPERS if item not in POST_V04_HELPERS
)
HISTORICAL_V04_TESTS = tuple(
    item for item in AUDITED_TESTS if item not in POST_V04_TESTS
)
HISTORICAL_V04_CRITICAL = tuple(
    item for item in AUDITED_CRITICAL if item not in POST_V04_CRITICAL
)
HISTORICAL_V04_LICENSING = tuple(AUDITED_LICENSING)
HISTORICAL_V04_PROJECTIONS = tuple(
    item for item in AUDITED_PROJECTIONS
    if item not in (
        APG66_V05_PROJECTIONS | APG75_V05_PROJECTIONS | APG77D_V05_PROJECTIONS
        | APG79E_V05_PROJECTIONS | APG81H_V05_PROJECTIONS
        | APG86_V06_PROJECTIONS
        | APG87_V06_PROJECTIONS
        | APG88_V06_PROJECTIONS
    )
)
HISTORICAL_V04_SKILLS = tuple(
    item for item in AUDITED_SKILLS
    if item not in (
        APG66_V05_SKILLS | APG75_V05_SKILLS | APG77D_V05_SKILLS
        | APG79E_V05_SKILLS | APG81H_V05_SKILLS | APG86_V06_SKILLS
        | APG87_V06_SKILLS
        | APG88_V06_SKILLS
    )
)
HISTORICAL_V04_CATEGORIES = tuple(sorted(ALLOWED_CATEGORIES))
HISTORICAL_V04_FORBIDDEN_FUTURE_OWNERS = tuple(
    sorted(
        APG53_V05_WRAPPERS
        | APG53_V05_HELPERS
        | APG53_V05_TESTS
        | APG53_V05_CRITICAL
        | APG54_V05_WRAPPERS
        | APG54_V05_HELPERS
        | APG54_V05_TESTS
        | APG54_V05_CRITICAL
        | APG55_V05_CRITICAL
        | APG66_V05_SKILLS
        | APG66_V05_PROJECTIONS
        | APG66_V05_TESTS
        | APG66_V05_CRITICAL
        | APG66A_V05_TESTS
        | APG66A_V05_CRITICAL
        | APG66B_V05_TESTS
        | APG66B_V05_CRITICAL
        | APG66C_V05_TESTS
        | APG66C_V05_CRITICAL
        | APG66D_V05_CRITICAL
        | APG75_V05_SKILLS
        | APG75_V05_PROJECTIONS
        | APG75_V05_TESTS
        | APG75_V05_CRITICAL
        | APG75A_V05_CRITICAL
        | APG77D_V05_SKILLS
        | APG77D_V05_PROJECTIONS
        | APG77D_V05_TESTS
        | APG77D_V05_CRITICAL
        | APG79E_V05_SKILLS
        | APG79E_V05_PROJECTIONS
        | APG79E_V05_TESTS
        | APG79E_V05_CRITICAL
        | APG81H_V05_SKILLS
        | APG81H_V05_PROJECTIONS
        | APG81H_V05_TESTS
        | APG81H_V05_CRITICAL
        | APG82_V05_WRAPPERS
        | APG82_V05_HELPERS
        | APG82_V05_TESTS
        | APG82_V05_CRITICAL
        | APG83_V05_WRAPPERS
        | APG83_V05_HELPERS
        | APG83_V05_TESTS
        | APG83_V05_CRITICAL
        | APG84_V05_WRAPPERS
        | APG84_V05_HELPERS
        | APG84_V05_TESTS
        | APG84_V05_CRITICAL
        | APG86_V06_SKILLS
        | APG86_V06_PROJECTIONS
        | APG86_V06_TESTS
        | APG86_V06_CRITICAL
        | APG87_V06_SKILLS
        | APG87_V06_PROJECTIONS
        | APG87_V06_TESTS
        | APG87_V06_CRITICAL
        | APG88_V06_SKILLS
        | APG88_V06_PROJECTIONS
        | APG88_V06_TESTS
        | APG88_V06_CRITICAL
        | APG89_V06_CRITICAL
        | APG90_V06_CRITICAL
    )
)
HISTORICAL_V04_SURFACE_SHA256 = (
    "4bc8571149c708023712f3963e81e0594d46a9a78da74ac48d8dba3e4b73a083"
)

V06_ONLY_SKILLS = APG86_V06_SKILLS | APG87_V06_SKILLS | APG88_V06_SKILLS
V06_ONLY_PROJECTIONS = (
    APG86_V06_PROJECTIONS | APG87_V06_PROJECTIONS | APG88_V06_PROJECTIONS
)
V06_ONLY_TESTS = APG86_V06_TESTS | APG87_V06_TESTS | APG88_V06_TESTS
V06_ONLY_CRITICAL = (
    APG86_V06_CRITICAL
    | APG87_V06_CRITICAL
    | APG88_V06_CRITICAL
    | APG89_V06_CRITICAL
    | APG90_V06_CRITICAL
)
HISTORICAL_V05_WRAPPERS = tuple(AUDITED_WRAPPERS)
HISTORICAL_V05_HELPERS = tuple(AUDITED_HELPERS)
HISTORICAL_V05_TESTS = tuple(
    item for item in AUDITED_TESTS if item not in V06_ONLY_TESTS
)
HISTORICAL_V05_CRITICAL = tuple(
    item for item in AUDITED_CRITICAL if item not in V06_ONLY_CRITICAL
)
HISTORICAL_V05_LICENSING = tuple(AUDITED_LICENSING)
HISTORICAL_V05_PROJECTIONS = tuple(
    item for item in AUDITED_PROJECTIONS if item not in V06_ONLY_PROJECTIONS
)
HISTORICAL_V05_SKILLS = tuple(
    item for item in AUDITED_SKILLS if item not in V06_ONLY_SKILLS
)
HISTORICAL_V05_CATEGORIES = tuple(sorted(ALLOWED_CATEGORIES))
HISTORICAL_V05_FORBIDDEN_FUTURE_OWNERS = tuple(
    sorted(
        V06_ONLY_SKILLS
        | V06_ONLY_PROJECTIONS
        | V06_ONLY_TESTS
        | V06_ONLY_CRITICAL
    )
)
HISTORICAL_V05_SURFACE_SHA256 = (
    "9f20ad43ffd4f4eeb72fe4cfe4aeb1cbe6449e5993bc641563f36a99a378bbef"
)

HISTORICAL_V03_WRAPPERS = (
    "bin/apg-check-record-identity",
    "bin/apg-check-skill-library",
    "bin/apg-project-skills",
    "bin/apg-public-release",
    "bin/apg-user-skills",
    "bin/append-operational-report",
    "bin/git-show-report",
)
HISTORICAL_V03_HELPERS = (
    "libexec/agent-report/common.sh",
    "libexec/apg_project_skills_commands.py",
    "libexec/apg_project_skills_core.py",
    "libexec/apg_public_release.py",
    "libexec/apg_record_identity.py",
    "libexec/apg_skill_library_check.py",
    "libexec/apg_user_skills.py",
)
HISTORICAL_V03_TESTS = (
    "src/test/int/python/apg_check_skill_library.int.test.py",
    "src/test/int/python/apg_project_skills.int.test.py",
    "src/test/int/python/apg_public_release.int.test.py",
    "src/test/int/python/apg_public_release_v03_policy.int.test.py",
    "src/test/int/python/apg_record_identity.int.test.py",
    "src/test/int/python/apg_user_skills.int.test.py",
    "src/test/int/python/apg_user_skills_variable_sets.int.test.py",
    "src/test/unit/bash/append-operational-report.unit.test.bats",
    "src/test/unit/bash/git-show-report.unit.test.bats",
    "src/test/unit/python/apg_public_release.unit.test.py",
    "src/test/unit/python/apg_skill_library.unit.test.py",
    "src/test/unit/python/apg_user_skills.unit.test.py",
)
HISTORICAL_V03_LICENSING = (
    "CLA.md",
    "COMMERCIAL-LICENSE.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "NOTICE",
)
HISTORICAL_V03_SKILLS = tuple(
    f"skills/{name}/SKILL.md"
    for name in (
        "agentic-praxis-grimoire-workflow",
        "bash-language-profile",
        "bats-test-profile",
        "composing-approved-roadmap-assignments",
        "composing-bounded-worker-assignments",
        "debugging-systematically",
        "designing-significant-changes",
        "go-language-profile",
        "implementing-with-test-discipline",
        "nix-language-profile",
        "planning-repository-work",
        "postgresql-database-profile",
        "python-language-profile",
        "reviewing-and-verifying-repository-work",
        "ruby-language-profile",
        "sqlite-database-profile",
        "synthesizing-repository-guidance",
        "zsh-language-profile",
        "zunit-test-profile",
    )
)
HISTORICAL_V03_PROJECTIONS = tuple(
    path.replace("skills/", ".agents/skills/", 1).removesuffix("/SKILL.md")
    for path in HISTORICAL_V03_SKILLS
)
HISTORICAL_V03_CRITICAL = (
    ".github/pull_request_template.md",
    ".gitignore",
    "AGENTS.md",
    "README.md",
    "docs/adr/2026/07/0005-public-license-and-contribution-governance.md",
    "docs/adr/2026/07/0009-public-distribution-and-reproducible-release-validation.md",
    "docs/adr/2026/07/0010-six-skill-post-superpowers-stability-dispositions.md",
    "docs/adr/2026/07/0011-v0-3-workflow-synthesis-and-modular-guidance-architecture.md",
    "docs/adr/2026/07/0012-language-profile-contract-and-warning-levels.md",
    "docs/adr/2026/07/0013-repository-guidance-synthesis-and-migration-dispositions.md",
    "docs/adr/2026/07/0014-shell-language-and-shell-test-profile-ownership.md",
    "docs/adr/2026/07/0015-semantic-phase-identity-and-record-finalization.md",
    "docs/adr/2026/07/0016-nix-and-relational-engine-profile-ownership.md",
    "docs/adr/2026/07/0017-approved-roadmap-manager-assignment-ownership.md",
    "docs/adr/2026/07/0018-v0-3-readiness-maturity-and-release-inclusion.md",
    "docs/adr/2026/07/0019-v0-3-release-distribution-and-variable-skill-set-lifecycle.md",
    "docs/adr/README.md",
    "docs/bootstrap-v0.1.md",
    "docs/evaluations/apg12-public-distribution-and-release-validation.md",
    "docs/evaluations/apg12a-public-lineage-and-read-only-validation-correction.md",
    "docs/evaluations/apg13-six-skill-post-superpowers-stability-review.md",
    "docs/evaluations/apg14-v0-2-release-candidate-and-publication.md",
    "docs/evaluations/apg15-v0-3-foundation-design.md",
    "docs/evaluations/apg16-public-workflow-router.md",
    "docs/evaluations/apg17-repository-guidance-synthesis.md",
    "docs/evaluations/apg18-python-language-profile.md",
    "docs/evaluations/apg19-shell-and-shell-test-profiles.md",
    "docs/evaluations/apg19a-semantic-phase-identity-and-apg19-reconciliation.md",
    "docs/evaluations/apg20-go-and-ruby-language-profiles.md",
    "docs/evaluations/apg20a-go-and-ruby-profile-corrections.md",
    "docs/evaluations/apg21-nix-postgresql-and-sqlite-profiles.md",
    "docs/evaluations/apg21a-nix-profile-correction.md",
    "docs/evaluations/apg22-cross-repository-dogfood-and-guidance-migration.md",
    "docs/evaluations/apg22a-approved-roadmap-manager-assignments.md",
    "docs/evaluations/apg22b-version-bounded-zunit-profile.md",
    "docs/evaluations/apg22c-zunit-startup-isolation-evidence-correction.md",
    "docs/evaluations/apg23-v0-3-readiness-maturity-and-application-smoke.md",
    "docs/evaluations/apg24-v0-3-release-candidate-and-publication.md",
    "docs/language-profile-contract.md",
    "docs/legacy-roadmap-closure.md",
    "docs/manager-worker-protocol.md",
    "docs/phase-and-record-identity.md",
    "docs/project-model.md",
    "docs/project-skill-projection.md",
    "docs/provenance.md",
    "docs/public-release-process.md",
    "docs/roadmap.md",
    "docs/skill-authoring-and-maintenance.md",
    "docs/status/2026/07/20/00018-apg12-public-distribution-and-release-validation-exit.md",
    "docs/status/2026/07/20/00019-apg12a-public-lineage-and-read-only-validation-correction-exit.md",
    "docs/status/2026/07/20/00020-apg13-six-skill-post-superpowers-stability-review-exit.md",
    "docs/status/2026/07/20/00021-apg14-v0-2-release-candidate-and-publication-exit.md",
    "docs/status/2026/07/20/00022-apg15-v0-3-foundation-design-exit.md",
    "docs/status/2026/07/20/00023-apg16-public-workflow-router-exit.md",
    "docs/status/2026/07/20/00024-apg17-repository-guidance-synthesis-exit.md",
    "docs/status/2026/07/21/00025-apg17a-public-release-identity-evidence-correction-exit.md",
    "docs/status/2026/07/21/00026-apg18-language-profile-contract-and-python-vertical-slice-exit.md",
    "docs/status/2026/07/21/00027-apg18a-python-profile-current-state-documentation-correction-exit.md",
    "docs/status/2026/07/21/00028-apg19-shell-and-shell-test-profiles-exit.md",
    "docs/status/2026/07/21/00029-apg19a-semantic-phase-identity-and-apg19-reconciliation-exit.md",
    "docs/status/2026/07/21/00030-apg20-go-and-ruby-language-profiles-exit.md",
    "docs/status/2026/07/21/00031-apg20a-go-and-ruby-profile-corrections-exit.md",
    "docs/status/2026/07/21/00032-apg21-nix-postgresql-and-sqlite-profiles-exit.md",
    "docs/status/2026/07/21/00033-apg21a-nix-profile-correction-exit.md",
    "docs/status/2026/07/21/00034-apg22-cross-repository-dogfood-and-guidance-migration-exit.md",
    "docs/status/2026/07/21/00035-apg22a-approved-roadmap-manager-assignments-exit.md",
    "docs/status/2026/07/21/00036-apg22b-version-bounded-zunit-profile-exit.md",
    "docs/status/2026/07/21/00037-apg22c-zunit-startup-isolation-evidence-correction-exit.md",
    "docs/status/2026/07/21/00038-apg23-v0-3-readiness-maturity-and-application-smoke-exit.md",
    "docs/status/2026/07/22/00039-apg24-v0-3-release-candidate-and-publication-exit.md",
    "docs/status/README.md",
    "docs/user-scoped-skill-integration.md",
    "docs/v0-3-guidance-migration-proposal.md",
    "docs/v0-3-readiness-matrix.md",
    "docs/v0-3-release-scope-closure.md",
    "release/public-surface.json",
    "skills/README.md",
    "skills/agentic-praxis-grimoire-workflow/references/capability-map.json",
)
HISTORICAL_V03_FORBIDDEN_REPORT_OWNERS = (
    "bin/git-diff-report",
    "libexec/agent_report/__init__.py",
    "libexec/agent_report/cli.py",
    "libexec/agent_report/diff.py",
    "libexec/agent_report/git_adapter.py",
    "libexec/agent_report/models.py",
    "libexec/agent_report/operational.py",
    "libexec/agent_report/rendering.py",
    "libexec/agent_report/safety.py",
    "libexec/agent_report/show.py",
    "src/test/int/python/agent_report.int.test.py",
    "src/test/int/python/agent_report_parity.int.test.py",
    "src/test/unit/python/agent_report.unit.test.py",
)
SEMVER = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
EMAIL = re.compile(r"^[^\s<>@]+@[^\s<>@]+$")
RFC3339 = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T"
    r"(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]"
    r"(?:\.[0-9]{1,6})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])$"
)
GIT_ENV_NAMES = {
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR",
    "GIT_CONFIG",
    "GIT_CONFIG_COUNT",
    "GIT_CONFIG_PARAMETERS",
    "GIT_DIR",
    "GIT_GRAFT_FILE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_PREFIX",
    "GIT_SHALLOW_FILE",
    "GIT_WORK_TREE",
}


class ToolError(Exception):
    """A candidate, source, or policy noncompliance."""


class InvocationError(Exception):
    """An unsafe or malformed invocation."""


@dataclass(frozen=True)
class Entry:
    """One committed Git tree entry."""

    mode: str
    kind: str
    oid: str
    path: bytes

    @property
    def display_path(self) -> str:
        return self.path.decode("utf-8", "surrogateescape")


@dataclass(frozen=True)
class Repository:
    """A clean non-bare Git repository snapshot."""

    root: Path
    head: str
    tree: str


@dataclass(frozen=True)
class ReleaseIdentity:
    """One accepted public release commit and its version tag."""

    version: str
    tag: str
    commit: str
    tree: str


@dataclass(frozen=True)
class RepositoryFingerprint:
    """Mutable Git state that validation must not change."""

    head: str
    tree: str
    references: tuple[tuple[str, str], ...]
    index: bytes
    index_flags: bytes
    status: bytes


def fail(message: str) -> NoReturn:
    raise ToolError(message)


def unsafe(message: str) -> NoReturn:
    raise InvocationError(message)


def git_environment(extra: dict[str, str] | None = None) -> dict[str, str]:
    environment = os.environ.copy()
    for name in tuple(environment):
        if name in GIT_ENV_NAMES or name.startswith("GIT_CONFIG_KEY_") or name.startswith("GIT_CONFIG_VALUE_"):
            environment.pop(name)
    environment["GIT_CONFIG_NOSYSTEM"] = "1"
    environment["GIT_CONFIG_GLOBAL"] = os.devnull
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    environment["GIT_TERMINAL_PROMPT"] = "0"
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    if extra:
        environment.update(extra)
    return environment


def run_git(
    repo: Path,
    arguments: Sequence[str],
    *,
    input_bytes: bytes | None = None,
    allow_failure: bool = False,
    extra_environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    try:
        result = subprocess.run(
            [
                "git",
                "-c",
                "core.fsmonitor=false",
                "-c",
                f"core.hooksPath={os.devnull}",
                "-C",
                str(repo),
                *arguments,
            ],
            input=input_bytes,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=git_environment(extra_environment),
        )
    except OSError as error:
        fail(f"Git could not be executed: {error.strerror}")
    if result.returncode and not allow_failure:
        detail = result.stderr.decode("utf-8", "replace").strip() or "Git returned no diagnostic"
        fail(f"Git operation failed: {detail}")
    return result


def text_git(repo: Path, arguments: Sequence[str], **kwargs: object) -> str:
    result = run_git(repo, arguments, **kwargs)
    return result.stdout.decode("utf-8", "strict").strip()


def resolve_repository(requested: str | Path, label: str, *, require_clean: bool = True) -> Repository:
    path = Path(requested)
    result = run_git(path, ["rev-parse", "--show-toplevel"], allow_failure=True)
    if result.returncode:
        fail(f"{label} is not a Git worktree")
    try:
        root = Path(result.stdout.decode().strip()).resolve(strict=True)
    except (OSError, UnicodeError):
        fail(f"{label} root cannot be resolved safely")
    if text_git(root, ["rev-parse", "--is-inside-work-tree"]) != "true":
        fail(f"{label} must be a non-bare Git worktree")
    if require_clean:
        status_bytes = run_git(root, ["status", "--porcelain=v1", "-z", "--untracked-files=all"]).stdout
        if status_bytes:
            fail(f"{label} repository must be clean")
        for record in run_git(root, ["ls-files", "-v", "-z"]).stdout.split(b"\0"):
            if record and not record.startswith(b"H "):
                fail(f"{label} repository has unsupported index flags")
    head = text_git(root, ["rev-parse", "HEAD^{commit}"])
    tree = text_git(root, ["rev-parse", "HEAD^{tree}"])
    return Repository(root, head, tree)


def committed_bytes(repository: Repository, path: str) -> bytes:
    result = run_git(repository.root, ["show", f"{repository.head}:{path}"], allow_failure=True)
    if result.returncode:
        fail(f"required committed path is missing: {path}")
    return result.stdout


def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, member in pairs:
        if key in value:
            raise ValueError(f"duplicate key: {key}")
        value[key] = member
    return value


def safe_policy_path(value: str) -> bool:
    if not value or "\x00" in value or "\\" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and not any(part in {"", ".", ".."} for part in path.parts)


def audited_policy_surfaces(version: str) -> tuple[dict[str, tuple[str, ...]], ...]:
    """Return exact policy surfaces allowed for one public release version."""

    historical_v06 = {
        "required_helpers": HISTORICAL_V06_HELPERS,
        "required_licensing_files": HISTORICAL_V06_LICENSING,
        "required_projections": HISTORICAL_V06_PROJECTIONS,
        "required_skills": HISTORICAL_V06_SKILLS,
        "required_test_entrypoints": HISTORICAL_V06_TESTS,
        "required_wrappers": HISTORICAL_V06_WRAPPERS,
        "critical_files": HISTORICAL_V06_CRITICAL,
        "validation_categories": HISTORICAL_V06_CATEGORIES,
    }
    historical_v06_digest = hashlib.sha256(
        json.dumps(
            historical_v06,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    if historical_v06_digest != HISTORICAL_V06_SURFACE_SHA256:
        fail("historical public v0.6.0 policy surface changed")
    current_v07 = {
        "required_helpers": V07_HELPERS,
        "required_licensing_files": V07_LICENSING,
        "required_projections": V07_PROJECTIONS,
        "required_skills": V07_SKILLS,
        "required_test_entrypoints": V07_TESTS,
        "required_wrappers": V07_WRAPPERS,
        "critical_files": V07_CRITICAL,
        "validation_categories": V07_CATEGORIES,
    }
    current_v08 = {
        "required_helpers": V08_HELPERS,
        "required_licensing_files": V08_LICENSING,
        "required_projections": V08_PROJECTIONS,
        "required_skills": V08_SKILLS,
        "required_test_entrypoints": V08_TESTS,
        "required_wrappers": V08_WRAPPERS,
        "critical_files": V08_CRITICAL,
        "validation_categories": V08_CATEGORIES,
    }
    current_v081 = {
        "required_helpers": V081_HELPERS,
        "required_licensing_files": V081_LICENSING,
        "required_projections": V081_PROJECTIONS,
        "required_skills": V081_SKILLS,
        "required_test_entrypoints": V081_TESTS,
        "required_wrappers": V081_WRAPPERS,
        "critical_files": V081_CRITICAL,
        "validation_categories": V081_CATEGORIES,
    }
    if not SEMVER.fullmatch(version):
        fail("public release policy identity is malformed or unsupported")
    core = version.split("+", 1)[0].split("-", 1)[0]
    if core == "0.8.1":
        return (current_v081,)
    if core == "0.8.0":
        return (current_v08,)
    if core == "0.7.0":
        return (current_v07,)
    if core == "0.6.0":
        return (historical_v06,)
    if core == "0.5.0":
        historical_v05 = {
            "required_helpers": HISTORICAL_V05_HELPERS,
            "required_licensing_files": HISTORICAL_V05_LICENSING,
            "required_projections": HISTORICAL_V05_PROJECTIONS,
            "required_skills": HISTORICAL_V05_SKILLS,
            "required_test_entrypoints": HISTORICAL_V05_TESTS,
            "required_wrappers": HISTORICAL_V05_WRAPPERS,
            "critical_files": HISTORICAL_V05_CRITICAL,
            "validation_categories": HISTORICAL_V05_CATEGORIES,
        }
        historical_v05_digest = hashlib.sha256(
            json.dumps(
                historical_v05,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        if historical_v05_digest != HISTORICAL_V05_SURFACE_SHA256:
            fail("historical public v0.5.0 policy surface changed")
        return (historical_v05,)
    if core == "0.4.0":
        historical_v04 = {
            "required_helpers": HISTORICAL_V04_HELPERS,
            "required_licensing_files": HISTORICAL_V04_LICENSING,
            "required_projections": HISTORICAL_V04_PROJECTIONS,
            "required_skills": HISTORICAL_V04_SKILLS,
            "required_test_entrypoints": HISTORICAL_V04_TESTS,
            "required_wrappers": HISTORICAL_V04_WRAPPERS,
            "critical_files": HISTORICAL_V04_CRITICAL,
            "validation_categories": HISTORICAL_V04_CATEGORIES,
        }
        historical_v04_digest = hashlib.sha256(
            json.dumps(
                historical_v04,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        if historical_v04_digest != HISTORICAL_V04_SURFACE_SHA256:
            fail("historical public v0.4.0 policy surface changed")
        return (historical_v04,)
    if core == "0.3.0":
        historical_v03 = {
            "required_helpers": HISTORICAL_V03_HELPERS,
            "required_licensing_files": HISTORICAL_V03_LICENSING,
            "required_projections": HISTORICAL_V03_PROJECTIONS,
            "required_skills": HISTORICAL_V03_SKILLS,
            "required_test_entrypoints": HISTORICAL_V03_TESTS,
            "required_wrappers": HISTORICAL_V03_WRAPPERS,
            "critical_files": HISTORICAL_V03_CRITICAL,
            "validation_categories": tuple(sorted(ALLOWED_CATEGORIES)),
        }
        return (historical_v03,)
    if core != "0.2.0":
        fail("public release policy identity is malformed or unsupported")
    historical_v02 = {
        "required_helpers": HISTORICAL_V02_HELPERS,
        "required_licensing_files": HISTORICAL_V02_LICENSING,
        "required_projections": HISTORICAL_V02_PROJECTIONS,
        "required_skills": HISTORICAL_V02_SKILLS,
        "required_test_entrypoints": HISTORICAL_V02_TESTS,
        "required_wrappers": HISTORICAL_V02_WRAPPERS,
        "critical_files": HISTORICAL_V02_CRITICAL,
        "validation_categories": tuple(
            sorted(ALLOWED_CATEGORIES - {"record-identity"})
        ),
    }
    return (historical_v02,)


def load_policy(
    repository: Repository,
    *,
    expected_surfaces: Sequence[dict[str, tuple[str, ...]]] | None = None,
    allow_v07_compatibility: bool = False,
    allow_v08_compatibility: bool = False,
) -> dict[str, object]:
    raw = committed_bytes(repository, POLICY_PATH)
    if len(raw) > 256 * 1024:
        fail("public release policy is oversized")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
    except (UnicodeError, json.JSONDecodeError, ValueError):
        fail("public release policy is malformed")
    if not isinstance(value, dict) or set(value) != POLICY_KEYS:
        fail("public release policy schema is malformed or unsupported")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        fail("public release policy schema version is unsupported")
    if value["canonical_public_identity"] != "agentic-praxis-grimoire":
        fail("public release policy canonical identity is invalid")
    if value["excluded_prefix"] != "private/":
        fail("public release policy excluded prefix must be private/")
    for key in ARRAY_KEYS:
        member = value[key]
        if not isinstance(member, list) or any(not isinstance(item, str) for item in member):
            fail(f"public release policy {key} must be a string array")
        if member != sorted(set(member)):
            fail(f"public release policy {key} must be sorted and unique")
        if key != "validation_categories" and any(not safe_policy_path(item) for item in member):
            fail(f"public release policy {key} contains an unsafe path")
        if key != "validation_categories" and any(item == "private" or item.startswith("private/") for item in member):
            fail(f"public release policy {key} may not name private paths")
    if not set(value["validation_categories"]).issubset(ALLOWED_CATEGORIES):
        fail("public release policy contains an unknown validation category")
    allowed_surfaces = tuple(expected_surfaces or audited_policy_surfaces("0.6.0"))
    if allow_v07_compatibility and any(
        surface == audited_policy_surfaces("0.6.0")[0]
        for surface in allowed_surfaces
    ):
        allowed_surfaces = (*allowed_surfaces, audited_policy_surfaces("0.7.0")[0])
    if allow_v08_compatibility and any(
        surface in (audited_policy_surfaces("0.7.0")[0], audited_policy_surfaces("0.8.0")[0])
        for surface in allowed_surfaces
    ):
        allowed_surfaces = (
            *allowed_surfaces,
            audited_policy_surfaces("0.8.0")[0],
            audited_policy_surfaces("0.8.1")[0],
        )
    if not any(
        all(tuple(value[key]) == expected for key, expected in surface.items())
        for surface in allowed_surfaces
    ):
        for key in next(iter(allowed_surfaces)):
            if all(tuple(value[key]) != surface[key] for surface in allowed_surfaces):
                fail(f"public release policy {key} differs from the audited schema-1 surface")
        else:
            fail("public release policy combines incompatible audited schema-1 surfaces")
    return value


def tree_entries(repository: Repository, *, excluded_prefix: bytes = b"") -> tuple[Entry, ...]:
    output = run_git(repository.root, ["ls-tree", "-rz", repository.head]).stdout
    entries: list[Entry] = []
    seen: set[bytes] = set()
    for record in output.split(b"\0"):
        if not record:
            continue
        try:
            metadata, path = record.split(b"\t", 1)
            mode_bytes, kind_bytes, oid_bytes = metadata.split(b" ", 2)
        except ValueError:
            fail("Git returned malformed tree metadata")
        if path in seen or path.startswith(b"/") or b"\0" in path or any(part in {b"", b".", b".."} for part in path.split(b"/")):
            fail("Git tree contains an unsafe or duplicate path")
        seen.add(path)
        if excluded_prefix and path.startswith(excluded_prefix):
            continue
        mode = mode_bytes.decode("ascii")
        kind = kind_bytes.decode("ascii")
        oid = oid_bytes.decode("ascii")
        if kind != "blob" or mode not in {"100644", "100755", "120000"}:
            fail(f"unsupported public Git entry: {path.decode('utf-8', 'replace')}")
        entries.append(Entry(mode, kind, oid, path))
    return tuple(sorted(entries, key=lambda entry: entry.path))


def is_v07_candidate_path(path: str | bytes) -> bool:
    """Return whether one source path belongs in the v0.7 public candidate."""

    display = (
        path.decode("utf-8", "surrogateescape")
        if isinstance(path, bytes)
        else path
    )
    if (
        display == "private"
        or display.startswith("private/")
        or display in V07_EXCLUDED_PATHS
        or display in V07_GENERATED_PATHS
    ):
        return False
    if any(display.startswith(prefix) for prefix in V07_EXCLUDED_PREFIXES):
        return False
    if any(display.startswith(prefix) for prefix in V07_GENERATED_PREFIXES):
        return False
    if display.endswith(V07_GENERATED_SUFFIXES):
        return False
    if any(part == "__pycache__" or part.endswith(".egg-info") for part in display.split("/")):
        return False
    return True


def is_v08_candidate_path(path: str | bytes) -> bool:
    """Return whether one source path belongs in the v0.8 public candidate."""

    display = (
        path.decode("utf-8", "surrogateescape")
        if isinstance(path, bytes)
        else path
    )
    if (
        display == "private"
        or display.startswith("private/")
        or display in V07_EXCLUDED_PATHS
        or display in V07_GENERATED_PATHS
    ):
        return False
    if any(display.startswith(prefix) for prefix in V07_EXCLUDED_PREFIXES):
        return False
    if any(display.startswith(prefix) for prefix in V07_GENERATED_PREFIXES):
        return False
    if display.endswith(V07_GENERATED_SUFFIXES):
        return False
    if any(part == "__pycache__" or part.endswith(".egg-info") for part in display.split("/")):
        return False
    return True


def public_candidate_entries(
    repository: Repository,
    version: str,
    *,
    excluded_prefix: bytes = b"",
) -> tuple[Entry, ...]:
    """Return the exact tree entries eligible for one source candidate."""

    entries = tree_entries(repository, excluded_prefix=excluded_prefix)
    core = version.split("+", 1)[0].split("-", 1)[0]
    if core in {"0.8.0", "0.8.1"}:
        return tuple(entry for entry in entries if is_v08_candidate_path(entry.path))
    if core != "0.7.0":
        return entries
    return tuple(entry for entry in entries if is_v07_candidate_path(entry.path))


def entry_bytes(repository: Repository, entry: Entry) -> bytes:
    return run_git(repository.root, ["cat-file", "blob", entry.oid]).stdout


def validate_critical(entries: Sequence[Entry], policy: dict[str, object]) -> None:
    present = {entry.display_path for entry in entries}
    keys = (
        "critical_files",
        "required_helpers",
        "required_licensing_files",
        "required_projections",
        "required_skills",
        "required_test_entrypoints",
        "required_wrappers",
    )
    for key in keys:
        for path in policy[key]:  # type: ignore[index]
            if path not in present:
                fail(f"required public path is missing: {path}")


def validate_public_symlinks(repository: Repository, entries: Sequence[Entry]) -> None:
    paths = {entry.path for entry in entries}
    entry_by_path = {entry.path: entry for entry in entries}
    targets: dict[bytes, bytes] = {}

    def normalize(path: PurePosixPath, display_path: str) -> bytes:
        components: list[str] = []
        for component in path.parts:
            if component in ("", "."):
                continue
            if component == "..":
                if not components:
                    fail(f"public symlink target escapes the repository: {display_path}")
                components.pop()
            else:
                components.append(component)
        normalized = "/".join(components)
        if not normalized or normalized == "private" or normalized.startswith("private/"):
            fail(f"public symlink target escapes or enters private/: {display_path}")
        return normalized.encode("utf-8")

    for entry in entries:
        if entry.mode != "120000":
            continue
        try:
            target = entry_bytes(repository, entry).decode("utf-8", "strict")
        except UnicodeError:
            fail(f"public symlink target is not UTF-8: {entry.display_path}")
        if not target or "\\" in target or PurePosixPath(target).is_absolute():
            fail(f"public symlink target is unsafe: {entry.display_path}")
        combined = PurePosixPath(entry.display_path).parent / PurePosixPath(target)
        targets[entry.path] = normalize(combined, entry.display_path)

    def resolve_committed(path: bytes, seen: frozenset[bytes]) -> None:
        parts = path.split(b"/")
        for index in range(1, len(parts) + 1):
            prefix = b"/".join(parts[:index])
            target_entry = entry_by_path.get(prefix)
            if target_entry is None or target_entry.mode != "120000":
                continue
            if prefix in seen:
                fail(f"public symlink graph is cyclic: {target_entry.display_path}")
            replacement = targets[prefix]
            remainder = parts[index:]
            combined = PurePosixPath(replacement.decode("utf-8"))
            if remainder:
                combined /= PurePosixPath(b"/".join(remainder).decode("utf-8"))
            resolve_committed(
                normalize(combined, target_entry.display_path),
                seen | {prefix},
            )
            return
        if path not in paths and not any(member.startswith(path + b"/") for member in paths):
            fail(f"public symlink target is missing from the projection: {path.decode('utf-8')}")

    for entry_path, target_path in targets.items():
        resolve_committed(target_path, frozenset({entry_path}))


def repository_version(repository: Repository) -> str:
    """Read the editable version when present, with fixture-safe fallback."""

    try:
        value = committed_bytes(
            repository,
            "src/agentic_praxis_grimoire/VERSION",
        ).decode("ascii").strip()
        validate_version(value)
    except (ToolError, InvocationError, UnicodeDecodeError):
        return "0.6.0"
    return value


def build_manifest(
    repository: Repository,
    version: str | None = None,
) -> dict[str, object]:
    selected_version = version or repository_version(repository)
    policy = load_policy(
        repository,
        expected_surfaces=audited_policy_surfaces(selected_version),
        allow_v07_compatibility=True,
        allow_v08_compatibility=True,
    )
    entries = public_candidate_entries(
        repository,
        selected_version,
        excluded_prefix=b"private/",
    )
    validate_critical(entries, policy)
    validate_public_symlinks(repository, entries)
    rendered: list[dict[str, object]] = []
    for entry in entries:
        content = entry_bytes(repository, entry)
        item: dict[str, object] = {
            "mode": entry.mode,
            "path": entry.display_path,
            "sha256": hashlib.sha256(content).hexdigest(),
            "type": "symlink" if entry.mode == "120000" else "file",
        }
        if entry.mode == "120000":
            item["symlink_target"] = content.decode("utf-8", "surrogateescape")
        rendered.append(item)
    return {
        "canonical_public_identity": policy["canonical_public_identity"],
        "entries": rendered,
        "excluded_prefix": "private/",
        "schema_version": 1,
    }


def validate_public_release_surface(repository: Repository, version: str) -> None:
    """Validate the strict policy and complete tree of a later public release."""

    policy = load_policy(
        repository,
        expected_surfaces=audited_policy_surfaces(version),
    )
    all_entries = tree_entries(repository)
    validate_versioned_policy_exclusions(all_entries, version)
    if any(
        entry.path == b"private" or entry.path.startswith(b"private/")
        for entry in all_entries
    ):
        fail("public release must not track private/")
    entries = public_candidate_entries(repository, version)
    validate_critical(entries, policy)
    validate_public_symlinks(repository, entries)


def validate_versioned_policy_exclusions(
    entries: Sequence[Entry],
    version: str,
) -> None:
    """Reject future owners from immutable historical public trees."""

    core = version.split("+", 1)[0].split("-", 1)[0]
    if core in {"0.8.0", "0.8.1"}:
        for entry in entries:
            if not is_v08_candidate_path(entry.path):
                fail(
                    f"public v{version} contains a publication-excluded path: "
                    + entry.display_path
                )
        return
    if core == "0.7.0":
        for entry in entries:
            if not is_v07_candidate_path(entry.path):
                fail(
                    "public v0.7.0 contains a publication-excluded path: "
                    + entry.display_path
                )
        return
    if core == "0.5.0":
        paths = {entry.display_path for entry in entries}
        for path in HISTORICAL_V05_FORBIDDEN_FUTURE_OWNERS:
            if path in paths:
                fail(f"public v0.5.0 contains unsupported future owner: {path}")
        return
    if core == "0.4.0":
        paths = {entry.display_path for entry in entries}
        for path in HISTORICAL_V04_FORBIDDEN_FUTURE_OWNERS:
            if path in paths:
                fail(f"public v0.4.0 contains unsupported future owner: {path}")
        return
    if core != "0.3.0":
        return
    paths = {entry.display_path for entry in entries}
    for path in HISTORICAL_V03_FORBIDDEN_REPORT_OWNERS:
        if path in paths:
            fail(f"public v0.3.0 contains unsupported future owner: {path}")


def render_manifest(manifest: dict[str, object], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(manifest, ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n"
    lines = ["APG public manifest v1"]
    for entry in manifest["entries"]:  # type: ignore[assignment]
        lines.append(f"{entry['mode']} {entry['sha256']} {entry['path']}")
    return "\n".join(lines) + "\n"


def validate_version(value: str) -> str:
    if not SEMVER.fullmatch(value):
        unsafe("version must be a valid SemVer value without a leading v")
    prerelease = value.split("+", 1)[0].partition("-")[2]
    if prerelease and any(
        identifier.isdigit() and len(identifier) > 1 and identifier.startswith("0")
        for identifier in prerelease.split(".")
    ):
        unsafe("version must be a valid SemVer value without a leading v")
    return value


def validate_date(value: str) -> datetime:
    if not RFC3339.fullmatch(value):
        unsafe("release date must be RFC3339 with an explicit offset")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        unsafe("release date must be RFC3339 with an explicit offset")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        unsafe("release date must include an explicit offset")
    return parsed


def validate_identity(name: str, email: str) -> None:
    if not name.strip() or any(ord(character) < 32 or ord(character) == 127 for character in name) or any(
        character in name for character in "<>"
    ):
        unsafe("author name is invalid")
    if any(ord(character) < 32 or ord(character) == 127 for character in email) or not EMAIL.fullmatch(email):
        unsafe("author email is invalid")


def validate_repository_separation(*repositories: Repository) -> None:
    roots = [repository.root for repository in repositories]
    for index, first in enumerate(roots):
        for second in roots[index + 1 :]:
            if first == second or first in second.parents or second in first.parents:
                unsafe("source, base, and candidate repositories must be physically disjoint")


def validate_output_path(output: Path, source: Path, base: Path) -> None:
    absolute = Path(os.path.abspath(output))
    if os.path.lexists(absolute) and stat.S_ISLNK(absolute.lstat().st_mode):
        unsafe("output has a symlinked or non-directory ancestor")
    current = absolute.parent
    allowed_system_aliases = {
        (Path("/tmp"), Path("/private/tmp")),
        (Path("/var"), Path("/private/var")),
    }
    while True:
        if os.path.lexists(current):
            metadata = current.lstat()
            if stat.S_ISLNK(metadata.st_mode):
                try:
                    alias = (current, current.resolve(strict=True))
                except OSError:
                    unsafe("output has a broken symlink ancestor")
                if alias not in allowed_system_aliases:
                    unsafe("output has a symlinked or non-directory ancestor")
            elif not stat.S_ISDIR(metadata.st_mode):
                unsafe("output has a symlinked or non-directory ancestor")
        if current == current.parent:
            break
        current = current.parent
    try:
        physical = (
            absolute.resolve(strict=True)
            if os.path.lexists(absolute)
            else absolute.parent.resolve(strict=True) / absolute.name
        )
    except OSError:
        unsafe("output parent cannot be resolved safely")
    if (
        physical in {source, base}
        or source in physical.parents
        or base in physical.parents
        or physical in source.parents
        or physical in base.parents
    ):
        unsafe("output must be disjoint from source and base")
    if os.path.lexists(absolute):
        metadata = absolute.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            unsafe("output path already exists with an unsafe type")
        if any(absolute.iterdir()):
            unsafe("output path already exists and is nonempty")


def import_object(source: Repository, destination: Path, oid: str) -> None:
    kind = text_git(source.root, ["cat-file", "-t", oid])
    content = run_git(source.root, ["cat-file", kind, oid]).stdout
    written = text_git(destination, ["hash-object", "-w", "-t", kind, "--stdin"], input_bytes=content)
    if written != oid:
        fail("Git object identity changed during local copy")


def reachable_objects(repository: Repository) -> tuple[str, ...]:
    result = run_git(repository.root, ["rev-list", "--objects", "--all", "--no-object-names"])
    values = {line.decode("ascii") for line in result.stdout.splitlines() if line}
    for line in run_git(repository.root, ["for-each-ref", "--format=%(objectname)", "refs/tags"]).stdout.splitlines():
        if line:
            values.add(line.decode("ascii"))
    return tuple(sorted(values))


def reference_map(repository: Repository, prefix: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in run_git(
        repository.root,
        ["for-each-ref", "--format=%(refname)%00%(objectname)", prefix],
    ).stdout.splitlines():
        if not line:
            continue
        name, object_id = line.split(b"\0", 1)
        values[name.decode("utf-8", "strict")] = object_id.decode("ascii")
    return values


def repository_fingerprint(repository: Repository) -> RepositoryFingerprint:
    return RepositoryFingerprint(
        head=text_git(repository.root, ["rev-parse", "HEAD^{commit}"]),
        tree=text_git(repository.root, ["rev-parse", "HEAD^{tree}"]),
        references=tuple(sorted(reference_map(repository, "refs").items())),
        index=run_git(repository.root, ["ls-files", "--stage", "-z"]).stdout,
        index_flags=run_git(repository.root, ["ls-files", "-v", "-z"]).stdout,
        status=run_git(
            repository.root,
            ["status", "--porcelain=v1", "-z", "--untracked-files=all"],
        ).stdout,
    )


def require_unchanged(
    repository: Repository,
    expected: RepositoryFingerprint,
    label: str,
) -> None:
    if repository_fingerprint(repository) != expected:
        fail(f"{label} repository changed during validation")


def semver_release_tags(repository: Repository) -> dict[str, list[tuple[str, str]]]:
    tags: dict[str, list[tuple[str, str]]] = {}
    for raw_tag in run_git(repository.root, ["tag", "--list", "v*"]).stdout.splitlines():
        tag = raw_tag.decode("utf-8", "strict")
        version = tag.removeprefix("v")
        try:
            validate_version(version)
        except (ToolError, InvocationError):
            continue
        resolved = run_git(
            repository.root,
            ["rev-parse", f"refs/tags/{tag}^{{commit}}"],
            allow_failure=True,
        )
        if resolved.returncode:
            fail(f"public release tag cannot be resolved: {tag}")
        commit = resolved.stdout.decode("ascii").strip()
        tags.setdefault(commit, []).append((tag, version))
    for values in tags.values():
        values.sort()
    return tags


def verify_public_release_lineage(
    repository: Repository,
    *,
    accepted_commit: str,
    accepted_tree: str,
) -> tuple[ReleaseIdentity, ...]:
    """Verify the exact v0.1 identity and every later linear release commit."""

    accepted_tag = run_git(
        repository.root,
        ["rev-parse", "refs/tags/v0.1.0"],
        allow_failure=True,
    )
    if accepted_tag.returncode or accepted_tag.stdout.decode("ascii").strip() != accepted_commit:
        if repository.head == accepted_commit:
            fail("accepted public v0.1.0 tag identity is invalid")
        fail("public release history does not preserve the accepted public v0.1.0 tag")
    accepted_object = run_git(
        repository.root,
        ["rev-parse", f"{accepted_commit}^{{commit}}"],
        allow_failure=True,
    )
    if accepted_object.returncode:
        fail("public release history does not contain accepted public v0.1.0")
    if text_git(repository.root, ["rev-parse", f"{accepted_commit}^{{tree}}"]) != accepted_tree:
        fail("accepted public v0.1.0 tree identity is invalid")

    tags_by_commit = semver_release_tags(repository)
    accepted_tags = tags_by_commit.get(accepted_commit, [])
    if accepted_tags != [("v0.1.0", "0.1.0")]:
        fail("accepted public v0.1.0 tag identity is invalid")
    identities = [
        ReleaseIdentity("0.1.0", "v0.1.0", accepted_commit, accepted_tree)
    ]
    if repository.head == accepted_commit:
        if repository.tree != accepted_tree:
            fail("accepted public v0.1.0 tree identity is invalid")
        if set(tags_by_commit) != {accepted_commit}:
            fail("public release tags include history outside the accepted release chain")
        return tuple(identities)

    ancestor = run_git(
        repository.root,
        ["merge-base", "--is-ancestor", accepted_commit, repository.head],
        allow_failure=True,
    )
    if ancestor.returncode:
        fail("public release history does not descend from accepted public v0.1.0")
    records = run_git(
        repository.root,
        ["rev-list", "--reverse", "--parents", f"{accepted_commit}..{repository.head}"],
    ).stdout.decode("ascii").splitlines()
    previous = accepted_commit
    accepted_commits = {accepted_commit}
    for record in records:
        fields = record.split()
        if len(fields) != 2 or fields[1] != previous:
            fail("public release history must be a strict single-parent release chain")
        commit = fields[0]
        matching = tags_by_commit.get(commit, [])
        if len(matching) != 1:
            fail("each public release commit must have exactly one matching v<semver> release tag")
        tag, version = matching[0]
        if text_git(repository.root, ["cat-file", "-t", f"refs/tags/{tag}"]) != "tag":
            fail("each later public release tag must be annotated")
        if text_git(repository.root, ["log", "-1", "--format=%s", commit]) != f"Release v{version}":
            fail("public release commit subject does not match its version tag")
        tree = text_git(repository.root, ["rev-parse", f"{commit}^{{tree}}"])
        identities.append(ReleaseIdentity(version, tag, commit, tree))
        accepted_commits.add(commit)
        previous = commit
    if previous != repository.head:
        fail("public release history is truncated or does not reach HEAD")
    if set(tags_by_commit) != accepted_commits:
        fail("public release tags include history outside the accepted release chain")
    validate_public_release_surface(repository, identities[-1].version)
    return tuple(identities)


def initialize_candidate(output: Path, base: Repository) -> None:
    output.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["git", "init", "-q", "-b", "main", str(output)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=git_environment(),
    )
    if result.returncode:
        fail(f"candidate Git repository could not be initialized: {result.stderr.decode('utf-8', 'replace').strip()}")
    for oid in reachable_objects(base):
        import_object(base, output, oid)
    run_git(output, ["update-ref", "refs/heads/main", base.head])
    for line in run_git(
        base.root,
        ["for-each-ref", "--format=%(refname)%00%(objectname)", "refs/tags"],
    ).stdout.splitlines():
        if not line:
            continue
        ref_bytes, oid_bytes = line.split(b"\0", 1)
        run_git(output, ["update-ref", ref_bytes.decode("utf-8"), oid_bytes.decode("ascii")])


def initialize_validation_copy(output: Path, repository: Repository) -> Repository:
    output.mkdir(parents=True)
    result = subprocess.run(
        ["git", "init", "-q", "-b", "main", str(output)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=git_environment(),
    )
    if result.returncode:
        fail(
            "validation repository could not be initialized: "
            + result.stderr.decode("utf-8", "replace").strip()
        )
    for oid in reachable_objects(repository):
        import_object(repository, output, oid)
    for name, oid in reference_map(repository, "refs").items():
        run_git(output, ["update-ref", name, oid])
    symbolic = run_git(repository.root, ["symbolic-ref", "-q", "HEAD"], allow_failure=True)
    if symbolic.returncode:
        run_git(output, ["checkout", "-q", "--detach", repository.head])
    else:
        run_git(output, ["symbolic-ref", "HEAD", symbolic.stdout.decode("utf-8").strip()])
        run_git(output, ["reset", "-q", "--hard", repository.head])
    return resolve_repository(output, "validation copy")


def deterministic_tagger(parsed: datetime) -> str:
    offset = parsed.strftime("%z")
    return f"{int(parsed.timestamp())} {offset}"


def build_candidate(
    source: Repository,
    base: Repository,
    output: Path,
    version: str,
    release_date: str,
    author_name: str,
    author_email: str,
) -> tuple[str, str, str]:
    validate_repository_separation(source, base)
    verify_public_release_lineage(
        base,
        accepted_commit=PUBLIC_V01_COMMIT,
        accepted_tree=PUBLIC_V01_TREE,
    )
    policy = load_policy(
        source,
        expected_surfaces=audited_policy_surfaces(version),
        allow_v07_compatibility=True,
        allow_v08_compatibility=True,
    )
    entries = public_candidate_entries(source, version, excluded_prefix=b"private/")
    validate_versioned_policy_exclusions(entries, version)
    validate_critical(entries, policy)
    validate_public_symlinks(source, entries)
    validate_output_path(output, source.root, base.root)
    parsed_date = validate_date(release_date)
    validate_identity(author_name, author_email)
    tag_name = f"v{version}"
    if not run_git(base.root, ["show-ref", "--verify", "--quiet", f"refs/tags/{tag_name}"], allow_failure=True).returncode:
        fail(f"public base already contains release tag {tag_name}")
    if not run_git(base.root, ["show-ref", "--verify", "--quiet", f"refs/heads/release/{version}"], allow_failure=True).returncode:
        fail(f"public base already contains release branch release/{version}")
    if os.path.lexists(output):
        output.rmdir()
    initialize_candidate(output, base)
    run_git(output, ["config", "user.name", author_name])
    run_git(output, ["config", "user.email", author_email])
    for entry in entries:
        import_object(source, output, entry.oid)
    with tempfile.NamedTemporaryFile(prefix="apg-public-index-", delete=False) as index_file:
        index_path = Path(index_file.name)
    index_path.unlink()
    try:
        payload = b"".join(
            entry.mode.encode("ascii") + b" " + entry.oid.encode("ascii") + b"\t" + entry.path + b"\0"
            for entry in entries
        )
        environment = {"GIT_INDEX_FILE": str(index_path)}
        run_git(output, ["update-index", "-z", "--index-info"], input_bytes=payload, extra_environment=environment)
        tree = text_git(output, ["write-tree"], extra_environment=environment)
    finally:
        index_path.unlink(missing_ok=True)
    identity_environment = {
        "GIT_AUTHOR_NAME": author_name,
        "GIT_AUTHOR_EMAIL": author_email,
        "GIT_AUTHOR_DATE": release_date,
        "GIT_COMMITTER_NAME": author_name,
        "GIT_COMMITTER_EMAIL": author_email,
        "GIT_COMMITTER_DATE": release_date,
    }
    subject = f"Release v{version}"
    commit = text_git(
        output,
        ["commit-tree", tree, "-p", base.head, "-m", subject],
        extra_environment=identity_environment,
    )
    branch = f"release/{version}"
    run_git(output, ["update-ref", f"refs/heads/{branch}", commit])
    run_git(output, ["symbolic-ref", "HEAD", f"refs/heads/{branch}"])
    run_git(output, ["reset", "--hard", commit])
    tag_body = (
        f"object {commit}\n"
        "type commit\n"
        f"tag {tag_name}\n"
        f"tagger {author_name} <{author_email}> {deterministic_tagger(parsed_date)}\n\n"
        f"{subject}\n"
    ).encode("utf-8")
    tag_object = text_git(output, ["mktag"], input_bytes=tag_body)
    run_git(output, ["update-ref", f"refs/tags/{tag_name}", tag_object])
    if run_git(source.root, ["status", "--porcelain=v1", "-z", "--untracked-files=all"]).stdout:
        fail("source changed during candidate construction")
    if run_git(base.root, ["status", "--porcelain=v1", "-z", "--untracked-files=all"]).stdout:
        fail("base changed during candidate construction")
    return tree, commit, tag_object


MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)|!\[[^\]]*\]\(([^)]+)\)")
HUMAN_MARKDOWN_LINK_EXCLUDED_PREFIXES = (b"hotspot/testdata/classification/",)


def validate_markdown_links(repository: Repository) -> None:
    entries = tree_entries(repository)
    paths = {entry.path for entry in entries}
    for entry in entries:
        if not entry.path.endswith(b".md"):
            continue
        try:
            content = entry_bytes(repository, entry).decode("utf-8")
        except UnicodeError:
            fail(f"public Markdown is not UTF-8: {entry.display_path}")
        parent = PurePosixPath(entry.display_path).parent
        for match in MARKDOWN_LINK.finditer(content):
            target = match.group(1) or match.group(2)
            target = target.strip().split(maxsplit=1)[0].strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or target.startswith("#") or not parsed.path:
                continue
            decoded = unquote(parsed.path)
            resolved = parent.joinpath(decoded)
            normalized: list[str] = []
            for part in resolved.parts:
                if part in {"", "."}:
                    continue
                if part == "..":
                    if not normalized:
                        fail(f"public Markdown link escapes root: {entry.display_path}")
                    normalized.pop()
                else:
                    normalized.append(part)
            destination = "/".join(normalized)
            if destination == "private" or destination.startswith("private/"):
                fail(f"public Markdown links into private/: {entry.display_path}")
            if entry.path.startswith(HUMAN_MARKDOWN_LINK_EXCLUDED_PREFIXES):
                continue
            prefix = destination.rstrip("/").encode("utf-8", "surrogateescape")
            if prefix not in paths and not any(path.startswith(prefix + b"/") for path in paths):
                fail(f"broken public Markdown link in {entry.display_path}: {decoded}")


def validate_private_policy(repository: Repository, path: str | None) -> None:
    if path is None:
        return
    candidate = Path(path)
    try:
        raw = candidate.read_bytes()
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        fail("private validation policy is malformed")
    if not isinstance(value, dict) or set(value) != PRIVATE_POLICY_KEYS or value["schema_version"] != 1:
        fail("private validation policy schema is malformed")
    patterns = value["forbidden_text_patterns"]
    if not isinstance(patterns, list) or patterns != sorted(set(patterns)) or any(not isinstance(item, str) or not item for item in patterns):
        fail("private validation patterns must be sorted unique nonempty strings")
    for entry in tree_entries(repository):
        content = entry_bytes(repository, entry)
        try:
            text = content.decode("utf-8")
        except UnicodeError:
            continue
        for pattern in patterns:
            if pattern in text:
                fail(f"private validation pattern matched public path: {entry.display_path}")


def run_checked_command(arguments: Sequence[str], cwd: Path, environment: dict[str, str] | None = None) -> None:
    try:
        result = subprocess.run(
            list(arguments),
            cwd=cwd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment or os.environ.copy(),
        )
    except OSError as error:
        fail(f"configured validation could not run: {error.strerror}")
    if result.returncode:
        detail = (result.stderr + result.stdout)[-8192:].decode("utf-8", "replace").strip()
        fail(f"configured validation failed: {' '.join(arguments)}: {detail}")


def validate_categories(
    candidate: Repository,
    base: Repository,
    policy: dict[str, object],
    environment: dict[str, str],
) -> None:
    categories = set(policy["validation_categories"])  # type: ignore[arg-type]
    wrappers = tuple(policy["required_wrappers"])  # type: ignore[arg-type]
    helpers = tuple(policy["required_helpers"])  # type: ignore[arg-type]
    tests = tuple(policy["required_test_entrypoints"])  # type: ignore[arg-type]
    if "skill-library" in categories:
        run_checked_command([str(candidate.root / "bin" / "apg-check-skill-library"), "--root", str(candidate.root), "--format", "json"], candidate.root, environment)
    if "record-identity" in categories:
        run_checked_command([str(candidate.root / "bin" / "apg-check-record-identity"), "--root", str(candidate.root), "--format", "json"], candidate.root, environment)
    if "command-help" in categories:
        for wrapper in wrappers:
            run_checked_command([str(candidate.root / wrapper), "--help"], candidate.root, environment)
    if "bash-syntax" in categories:
        paths = [*wrappers, *helpers]
        for path in paths:
            entry = next(item for item in tree_entries(candidate) if item.display_path == path)
            first_line = entry_bytes(candidate, entry).splitlines()[:1]
            if first_line and (b"/sh" in first_line[0] or b"/bash" in first_line[0]):
                run_checked_command(["bash", "-n", path], candidate.root, environment)
    if "python-compile" in categories:
        run_checked_command([sys.executable, "-m", "compileall", "-q", "libexec", "src/test"], candidate.root, environment)
    if "configured-tests" in categories:
        bash_tests = [path for path in tests if path.endswith(".bats")]
        python_tests = [path for path in tests if path.endswith(".py")]
        if bash_tests:
            run_checked_command(["bats", *bash_tests], candidate.root, environment)
        if python_tests and all(
            "/agentic-praxis-grimoire/" in path for path in python_tests
        ):
            deselections = (
                V07_PUBLIC_VALIDATION_DESELECTIONS
                if tuple(python_tests)
                == tuple(path for path in V07_TESTS if path.endswith(".py"))
                else ()
            )
            run_checked_command(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    "--import-mode=importlib",
                    "-o",
                    "python_files=*.test.py",
                    *(
                        argument
                        for node_id in deselections
                        for argument in ("--deselect", node_id)
                    ),
                    *python_tests,
                ],
                candidate.root,
                environment,
            )
        else:
            for path in python_tests:
                run_checked_command([sys.executable, path], candidate.root, environment)
    if "confidentiality" in categories:
        for entry in tree_entries(candidate):
            try:
                content = entry_bytes(candidate, entry).decode("utf-8")
            except UnicodeError:
                continue
            if any(marker in content for marker in LOCAL_PATH_MARKERS):
                fail(f"generic local-path confidentiality check failed: {entry.display_path}")


def isolated_validation_environment(
    root: Path,
    candidate: Repository,
    base: Repository,
) -> dict[str, str]:
    locations = {
        "HOME": root / "home",
        "XDG_CONFIG_HOME": root / "xdg-config",
        "XDG_CACHE_HOME": root / "xdg-cache",
        "XDG_DATA_HOME": root / "xdg-data",
        "XDG_RUNTIME_DIR": root / "xdg-runtime",
        "XDG_STATE_HOME": root / "xdg-state",
        "TMPDIR": root / "tmp",
        "PYTEST_DEBUG_TEMPROOT": root / "pytest",
        "PYTHONPYCACHEPREFIX": root / "pycache",
    }
    for path in locations.values():
        path.mkdir(parents=True)
    environment = git_environment({name: str(path) for name, path in locations.items()})
    for name in tuple(environment):
        if (
            name.startswith("PYTHON")
            or name.startswith("APG_TEST_")
            or name.startswith("COVERAGE_")
            or name.startswith("COV_CORE_")
            or name.startswith("PYTEST_")
        ):
            environment.pop(name)
    environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    environment["PYTEST_DEBUG_TEMPROOT"] = str(
        locations["PYTEST_DEBUG_TEMPROOT"]
    )
    environment["PYTHONPYCACHEPREFIX"] = str(locations["PYTHONPYCACHEPREFIX"])
    inherited_site_packages = [
        p
        for p in sys.path
        if p
        and not any(
            p.startswith(str(prefix))
            for prefix in (candidate.root, base.root)
        )
    ]
    try:
        import pytest  # type: ignore[import-not-found]

        pytest_dir = str(Path(pytest.__file__).resolve().parent.parent)
        if pytest_dir not in inherited_site_packages:
            inherited_site_packages.append(pytest_dir)
    except Exception:
        pass
    environment["PYTHONPATH"] = os.pathsep.join(
        (str(candidate.root / "src"), str(candidate.root), *inherited_site_packages)
    )
    environment["PWD"] = str(candidate.root)
    environment.pop("OLDPWD", None)
    environment["APG12_PUBLIC_V01_ROOT"] = str(base.root)
    environment["LC_ALL"] = "C"
    environment["LANG"] = "C"
    return environment


def validate_categories_in_isolation(
    candidate: Repository,
    base: Repository,
    policy: dict[str, object],
) -> None:
    with tempfile.TemporaryDirectory(prefix="apg-public-validation-") as temporary:
        root = Path(temporary)
        validation_candidate = initialize_validation_copy(root / "candidate", candidate)
        validation_base = initialize_validation_copy(root / "base", base)
        candidate_before = repository_fingerprint(validation_candidate)
        base_before = repository_fingerprint(validation_base)
        environment = isolated_validation_environment(
            root / "environment",
            validation_candidate,
            validation_base,
        )
        validation_error: ToolError | None = None
        try:
            validate_categories(
                validation_candidate,
                validation_base,
                policy,
                environment,
            )
        except ToolError as error:
            validation_error = error
        if repository_fingerprint(validation_candidate) != candidate_before:
            fail("configured validation modified the disposable candidate repository")
        if repository_fingerprint(validation_base) != base_before:
            fail("configured validation modified the disposable base repository")
        if validation_error is not None:
            raise validation_error


def check_candidate(
    source: Repository,
    base: Repository,
    candidate: Repository,
    version: str,
    private_policy: str | None,
) -> dict[str, object]:
    validate_repository_separation(source, base, candidate)
    verify_public_release_lineage(
        base,
        accepted_commit=PUBLIC_V01_COMMIT,
        accepted_tree=PUBLIC_V01_TREE,
    )
    policy = load_policy(
        source,
        expected_surfaces=audited_policy_surfaces(version),
        allow_v07_compatibility=True,
        allow_v08_compatibility=True,
    )
    source_entries = public_candidate_entries(
        source, version, excluded_prefix=b"private/"
    )
    candidate_entries = public_candidate_entries(candidate, version)
    core = version.split("+", 1)[0].split("-", 1)[0]
    if core == "0.7.0":
        # The development source may retain publication-excluded oracle files,
        # but a v0.7 release candidate must not project them.  Inspect the
        # unfiltered candidate tree so the check cannot pass merely because
        # the projection filter hid an excluded path.
        candidate_all_entries = tree_entries(candidate)
        validate_versioned_policy_exclusions(candidate_all_entries, version)
    else:
        validate_versioned_policy_exclusions(source_entries, version)
        validate_versioned_policy_exclusions(candidate_entries, version)
    validate_critical(source_entries, policy)
    validate_critical(candidate_entries, policy)
    validate_public_symlinks(source, source_entries)
    validate_public_symlinks(candidate, candidate_entries)
    source_map = {entry.path: (entry.mode, entry_bytes(source, entry)) for entry in source_entries}
    candidate_map = {entry.path: (entry.mode, entry_bytes(candidate, entry)) for entry in candidate_entries}
    if source_map.keys() != candidate_map.keys():
        missing = sorted(source_map.keys() - candidate_map.keys())
        extra = sorted(candidate_map.keys() - source_map.keys())
        detail = ""
        if missing:
            detail += f" missing {missing[0].decode('utf-8', 'replace')}"
        if extra:
            detail += f" extra {extra[0].decode('utf-8', 'replace')}"
        fail(f"candidate projected path set differs from source:{detail}")
    for path, expected in source_map.items():
        if candidate_map[path] != expected:
            fail(f"candidate mode, bytes, or symlink target differs: {path.decode('utf-8', 'replace')}")
    if text_git(candidate.root, ["rev-parse", "HEAD^"]) != base.head:
        fail("candidate release commit does not have the public base as sole parent")
    parent_record = text_git(candidate.root, ["rev-list", "--parents", "-n", "1", "HEAD"]).split()
    if len(parent_record) != 2 or parent_record[1] != base.head:
        fail("candidate release commit must have exactly one parent equal to the public base")
    if text_git(candidate.root, ["rev-list", "--count", f"{base.head}..HEAD"]) != "1":
        fail("candidate history must add exactly one commit after the public base")
    expected_branch = f"release/{version}"
    if text_git(candidate.root, ["branch", "--show-current"]) != expected_branch:
        fail("candidate is on the wrong release branch")
    if text_git(candidate.root, ["log", "-1", "--format=%s"]) != f"Release v{version}":
        fail("candidate release subject is incorrect")
    tag = f"v{version}"
    if text_git(candidate.root, ["cat-file", "-t", f"refs/tags/{tag}"]) != "tag":
        fail("candidate release tag must be an annotated tag with explicit metadata")
    tag_result = run_git(candidate.root, ["rev-parse", f"{tag}^{{commit}}"], allow_failure=True)
    if tag_result.returncode or tag_result.stdout.decode().strip() != candidate.head:
        fail("candidate release tag is missing or mismatched")
    commit_metadata = text_git(
        candidate.root,
        ["show", "-s", "--format=%an%x00%ae%x00%aI%x00%cn%x00%ce%x00%cI", "HEAD"],
    ).split("\x00")
    if len(commit_metadata) != 6 or commit_metadata[:3] != commit_metadata[3:]:
        fail("candidate author and committer metadata must be explicit and identical")
    tag_metadata = text_git(
        candidate.root,
        [
            "for-each-ref",
            "--format=%(taggername)%00%(taggeremail:trim)%00%(taggerdate:iso-strict)%00%(contents:subject)",
            f"refs/tags/{tag}",
        ],
    ).split("\x00")
    if len(tag_metadata) != 4 or tag_metadata != [commit_metadata[0], commit_metadata[1], commit_metadata[2], f"Release v{version}"]:
        fail("candidate annotated-tag metadata differs from the release commit metadata")
    candidate_heads = reference_map(candidate, "refs/heads")
    expected_heads = {
        "refs/heads/main": base.head,
        f"refs/heads/release/{version}": candidate.head,
    }
    if candidate_heads != expected_heads:
        fail("candidate local branch set or identity differs from the release contract")
    candidate_tags = reference_map(candidate, "refs/tags")
    expected_tags = reference_map(base, "refs/tags")
    expected_tags[f"refs/tags/{tag}"] = text_git(candidate.root, ["rev-parse", f"refs/tags/{tag}"])
    if candidate_tags != expected_tags:
        fail("candidate does not preserve the exact public base tags plus the release tag")
    if reference_map(candidate, "refs") != {**expected_heads, **expected_tags}:
        fail("candidate contains an unexpected public history reference")
    validate_markdown_links(candidate)
    validate_private_policy(candidate, private_policy)
    source_before = repository_fingerprint(source)
    base_before = repository_fingerprint(base)
    candidate_before = repository_fingerprint(candidate)
    try:
        validate_categories_in_isolation(candidate, base, policy)
    finally:
        require_unchanged(source, source_before, "source")
        require_unchanged(base, base_before, "base")
        require_unchanged(candidate, candidate_before, "candidate")
    return {
        "candidate_commit": candidate.head,
        "candidate_tree": candidate.tree,
        "schema_version": 1,
        "status": "pass",
        "tag": tag,
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog=COMMAND,
        description="Build and validate local APG public release candidates without network or push.",
    )
    subcommands = root.add_subparsers(dest="operation", required=True)
    manifest = subcommands.add_parser("manifest", help="render the committed non-private projection manifest")
    manifest.add_argument("--source", default=str(Path(__file__).resolve().parent.parent))
    manifest.add_argument("--version")
    manifest.add_argument("--format", choices=("text", "json"), default="text")
    build = subcommands.add_parser("build", help="build one deterministic local squashed candidate")
    for option in ("source", "base", "output", "version", "release-date", "author-name", "author-email"):
        build.add_argument(f"--{option}", required=True)
    check = subcommands.add_parser("check", help="validate an existing local candidate read-only")
    for option in ("source", "base", "candidate", "version"):
        check.add_argument(f"--{option}", required=True)
    check.add_argument("--private-policy")
    check.add_argument("--format", choices=("text", "json"), default="text")
    return root


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        if arguments.operation == "manifest":
            repository = resolve_repository(arguments.source, "source")
            sys.stdout.write(
                render_manifest(
                    build_manifest(repository, arguments.version), arguments.format
                )
            )
            return 0
        version = validate_version(arguments.version)
        source = resolve_repository(arguments.source, "source")
        base = resolve_repository(arguments.base, "base")
        if arguments.operation == "build":
            output = Path(os.path.abspath(arguments.output))
            tree, commit, tag = build_candidate(
                source,
                base,
                output,
                version,
                arguments.release_date,
                arguments.author_name,
                arguments.author_email,
            )
            print(f"PASS built local candidate v{version}: tree {tree}, commit {commit}, tag {tag}")
            return 0
        candidate = resolve_repository(arguments.candidate, "candidate")
        result = check_candidate(source, base, candidate, version, arguments.private_policy)
        if arguments.format == "json":
            print(json.dumps(result, separators=(",", ":"), sort_keys=True))
        else:
            print(f"PASS candidate v{version}: {candidate.head}")
        return 0
    except InvocationError as error:
        print(f"{COMMAND}: {error}", file=sys.stderr)
        return 2
    except ToolError as error:
        print(f"{COMMAND}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
