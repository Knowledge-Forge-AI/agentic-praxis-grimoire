"""Shared policy builders for public-release integration fixtures."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

release = importlib.import_module("apg_public_release")


POLICY_VERSION = "0.9.0"


class APGPublicReleaseFixture:
    """Build historical policy variants without owning test assertions."""

    def initialize(self, path: Path) -> None:
        path.mkdir(parents=True)
        self.git(path, "init", "-q", "-b", "main")
        self.git(path, "config", "user.name", "APG Test")
        self.git(path, "config", "user.email", "apg-test@example.invalid")

    def commit_all(self, repo: Path, subject: str) -> str:
        self.git(repo, "add", "-A")
        self.git(repo, "commit", "-q", "-m", subject)
        return self.git(repo, "rev-parse", "HEAD").stdout.strip()

    def policy(self) -> dict[str, object]:
        # Disposable historical release fixtures use their audited surface,
        # never the expanding v0.10 development inventory.
        value = json.loads((REPOSITORY_ROOT / "release" / "public-surface.json").read_text())
        value.update({key: list(items) for key, items in release.audited_policy_surfaces(POLICY_VERSION)[0].items()})
        return value

    def write_policy(self, repo: Path, value: dict[str, object] | None = None) -> None:
        path = repo / "release" / "public-surface.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value or self.policy(), indent=2, sort_keys=True) + "\n")

    def historical_v02_policy(self) -> dict[str, object]:
        value = self.policy()
        value["critical_files"] = [
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
        ]
        value["required_helpers"] = [
            "libexec/agent-report/common.sh",
            "libexec/apg_project_skills_commands.py",
            "libexec/apg_project_skills_core.py",
            "libexec/apg_public_release.py",
            "libexec/apg_skill_library_check.py",
            "libexec/apg_user_skills.py",
        ]
        value["required_projections"] = [
            ".agents/skills/composing-bounded-worker-assignments",
            ".agents/skills/debugging-systematically",
            ".agents/skills/designing-significant-changes",
            ".agents/skills/implementing-with-test-discipline",
            ".agents/skills/planning-repository-work",
            ".agents/skills/reviewing-and-verifying-repository-work",
        ]
        value["required_skills"] = [
            "skills/composing-bounded-worker-assignments/SKILL.md",
            "skills/debugging-systematically/SKILL.md",
            "skills/designing-significant-changes/SKILL.md",
            "skills/implementing-with-test-discipline/SKILL.md",
            "skills/planning-repository-work/SKILL.md",
            "skills/reviewing-and-verifying-repository-work/SKILL.md",
        ]
        value["required_test_entrypoints"] = [
            "src/test/int/python/apg_check_skill_library.int.test.py",
            "src/test/int/python/apg_project_skills.int.test.py",
            "src/test/int/python/apg_public_release.int.test.py",
            "src/test/int/python/apg_user_skills.int.test.py",
            "src/test/unit/bash/append-operational-report.unit.test.bats",
            "src/test/unit/bash/git-show-report.unit.test.bats",
            "src/test/unit/python/apg_public_release.unit.test.py",
            "src/test/unit/python/apg_skill_library.unit.test.py",
            "src/test/unit/python/apg_user_skills.unit.test.py",
        ]
        value["required_wrappers"] = [
            "bin/apg-check-skill-library",
            "bin/apg-project-skills",
            "bin/apg-public-release",
            "bin/apg-user-skills",
            "bin/append-operational-report",
            "bin/git-show-report",
        ]
        value["validation_categories"] = [
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
            "skill-library",
        ]
        return value

    def historical_v03_policy(self) -> dict[str, object]:
        value = self.policy()
        for key, paths in release.audited_policy_surfaces("0.3.0")[0].items():
            value[key] = list(paths)
        return value

    def historical_v04_policy(self) -> dict[str, object]:
        value = self.policy()
        for key, paths in release.audited_policy_surfaces("0.4.0")[0].items():
            value[key] = list(paths)
        return value

    def historical_v05_policy(self) -> dict[str, object]:
        value = self.policy()
        for key, paths in release.audited_policy_surfaces("0.5.0")[0].items():
            value[key] = list(paths)
        return value
