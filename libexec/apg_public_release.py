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
    "bin/apg-check-record-identity",
    "bin/apg-check-skill-library",
    "bin/apg-project-skills",
    "bin/apg-public-release",
    "bin/apg-user-skills",
    "bin/append-operational-report",
    "bin/git-show-report",
)
AUDITED_HELPERS = (
    "libexec/agent-report/common.sh",
    "libexec/apg_project_skills_commands.py",
    "libexec/apg_project_skills_core.py",
    "libexec/apg_public_release.py",
    "libexec/apg_record_identity.py",
    "libexec/apg_skill_library_check.py",
    "libexec/apg_user_skills.py",
)
AUDITED_TESTS = (
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
AUDITED_LICENSING = (
    "CLA.md",
    "COMMERCIAL-LICENSE.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "NOTICE",
)
AUDITED_SKILLS = tuple(f"skills/{name}/SKILL.md" for name in (
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
))
AUDITED_PROJECTIONS = tuple(path.replace("skills/", ".agents/skills/", 1).removesuffix("/SKILL.md") for path in AUDITED_SKILLS)
LOCAL_PATH_MARKERS = ("/" + "Users" + "/", "file:" + "///")
AUDITED_CRITICAL = (
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

    current = {
        "required_helpers": AUDITED_HELPERS,
        "required_licensing_files": AUDITED_LICENSING,
        "required_projections": AUDITED_PROJECTIONS,
        "required_skills": AUDITED_SKILLS,
        "required_test_entrypoints": AUDITED_TESTS,
        "required_wrappers": AUDITED_WRAPPERS,
        "critical_files": AUDITED_CRITICAL,
        "validation_categories": tuple(sorted(ALLOWED_CATEGORIES)),
    }
    core = version.split("+", 1)[0].split("-", 1)[0]
    major, minor, _patch = core.split(".")
    if (major, minor) != ("0", "2"):
        return (current,)
    historical = {
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
    return (historical,)


def load_policy(
    repository: Repository,
    *,
    expected_surfaces: Sequence[dict[str, tuple[str, ...]]] | None = None,
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
    allowed_surfaces = tuple(expected_surfaces or audited_policy_surfaces("0.3.0"))
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


def build_manifest(repository: Repository) -> dict[str, object]:
    policy = load_policy(repository)
    entries = tree_entries(repository, excluded_prefix=b"private/")
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
    entries = tree_entries(repository)
    if any(entry.path == b"private" or entry.path.startswith(b"private/") for entry in entries):
        fail("public release must not track private/")
    validate_critical(entries, policy)
    validate_public_symlinks(repository, entries)


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
    )
    entries = tree_entries(source, excluded_prefix=b"private/")
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
        detail = result.stderr.decode("utf-8", "replace").strip()
        fail(f"configured validation failed: {' '.join(arguments)}: {detail}")


def validate_categories(
    candidate: Repository,
    base: Repository,
    policy: dict[str, object],
    environment: dict[str, str],
) -> None:
    categories = set(policy["validation_categories"])  # type: ignore[arg-type]
    if "skill-library" in categories:
        run_checked_command([str(candidate.root / "bin" / "apg-check-skill-library"), "--root", str(candidate.root), "--format", "json"], candidate.root, environment)
    if "record-identity" in categories:
        run_checked_command([str(candidate.root / "bin" / "apg-check-record-identity"), "--root", str(candidate.root), "--format", "json"], candidate.root, environment)
    if "command-help" in categories:
        for wrapper in AUDITED_WRAPPERS:
            run_checked_command([str(candidate.root / wrapper), "--help"], candidate.root, environment)
    if "bash-syntax" in categories:
        paths = [*AUDITED_WRAPPERS, *AUDITED_HELPERS]
        for path in paths:
            entry = next(item for item in tree_entries(candidate) if item.display_path == path)
            first_line = entry_bytes(candidate, entry).splitlines()[:1]
            if first_line and (b"/sh" in first_line[0] or b"/bash" in first_line[0]):
                run_checked_command(["bash", "-n", path], candidate.root, environment)
    if "python-compile" in categories:
        run_checked_command([sys.executable, "-m", "compileall", "-q", "libexec", "src/test"], candidate.root, environment)
    if "configured-tests" in categories:
        tests = AUDITED_TESTS
        bash_tests = [path for path in tests if path.endswith(".bats")]
        python_tests = [path for path in tests if path.endswith(".py")]
        if bash_tests:
            run_checked_command(["bats", *bash_tests], candidate.root, environment)
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
        "PYTHONPYCACHEPREFIX": root / "pycache",
    }
    for path in locations.values():
        path.mkdir(parents=True)
    environment = git_environment({name: str(path) for name, path in locations.items()})
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
    )
    source_entries = tree_entries(source, excluded_prefix=b"private/")
    candidate_entries = tree_entries(candidate)
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
            sys.stdout.write(render_manifest(build_manifest(repository), arguments.format))
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
