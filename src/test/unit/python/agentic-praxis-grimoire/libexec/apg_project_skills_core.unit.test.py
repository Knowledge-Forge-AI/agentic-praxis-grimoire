"""Branch-focused unit tests for project-skill state and exclusion policy."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from unittest import mock

import pytest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import apg_project_skills_core as core  # noqa: E402


APG_ROOT = Path("/apg")
TARGET_ROOT = Path("/target")


def state_value() -> dict[str, object]:
    return {
        "format_version": 1,
        "apg_root": str(APG_ROOT),
        "target_root": str(TARGET_ROOT),
        "managed_skills": [core.EXPECTED_SKILLS[0]],
        "created_containers": [],
        "exclude_separator_added": False,
    }


def encoded(value: object) -> bytes:
    return json.dumps(value, sort_keys=True).encode()


def test_state_parser_accepts_canonical_state_and_rejects_bounds_and_schema() -> None:
    parsed = core.parse_state(encoded(state_value()), APG_ROOT, TARGET_ROOT)
    assert parsed.managed_skills == (core.EXPECTED_SKILLS[0],)
    for content in (b"", b"x" * (core.MAX_STATE_BYTES + 1), b"{", b"[]"):
        with pytest.raises(core.ToolError):
            core.parse_state(content, APG_ROOT, TARGET_ROOT)


def test_state_parser_rejects_each_identity_and_collection_failure() -> None:
    cases: list[tuple[dict[str, object], str]] = []
    value = state_value()
    value["format_version"] = True
    cases.append((value, "format version"))
    value = state_value()
    value["apg_root"] = "relative"
    cases.append((value, "APG root is malformed"))
    value = state_value()
    value["apg_root"] = "/other"
    cases.append((value, "different APG root"))
    value = state_value()
    value["target_root"] = "relative"
    cases.append((value, "target root is malformed"))
    value = state_value()
    value["target_root"] = "/other"
    cases.append((value, "different target"))
    for managed in ([], [1], [core.EXPECTED_SKILLS[1], core.EXPECTED_SKILLS[0]], ["unknown"]):
        value = state_value()
        value["managed_skills"] = managed
        cases.append((value, "managed skill list"))
    value = state_value()
    value["created_containers"] = [".agents"]
    cases.append((value, "container ownership"))
    value = state_value()
    value["exclude_separator_added"] = 1
    cases.append((value, "exclude metadata"))
    for value, message in cases:
        with pytest.raises(core.ToolError, match=message):
            core.parse_state(encoded(value), APG_ROOT, TARGET_ROOT)


def test_exclude_parser_accepts_absent_and_canonical_blocks() -> None:
    absent = core.parse_exclude(b"local rule\n")
    assert not absent.present and absent.prefix == b"local rule\n"
    skills = core.EXPECTED_SKILLS[:2]
    content = b"prefix\n" + core.build_exclude_block(skills) + b"suffix\n"
    parsed = core.parse_exclude(content)
    assert parsed.present and parsed.entries == skills
    assert parsed.prefix == b"prefix\n" and parsed.suffix == b"suffix\n"


def test_exclude_parser_rejects_malformed_markers_bodies_and_entries() -> None:
    known = core.EXPECTED_SKILLS[0]
    cases = (
        b"x" * (core.MAX_EXCLUDE_BYTES + 1),
        core.BEGIN_TOKEN + b" malformed\n",
        core.END_TOKEN + b" malformed\n",
        core.END_LINE + core.BEGIN_LINE,
        core.BEGIN_LINE + b"unterminated" + core.END_LINE,
        core.BEGIN_LINE + b"not-a-projection\n" + core.END_LINE,
        core.BEGIN_LINE + core.PROJECTION_PREFIX.encode() + b"unknown\n" + core.END_LINE,
        core.build_exclude_block((known, known)),
    )
    for content in cases:
        with pytest.raises(core.ToolError):
            core.parse_exclude(content)


def test_updated_exclude_handles_insert_replace_and_remove() -> None:
    snapshot = core.FileSnapshot(True, b"prefix", 0o600)
    absent = core.parse_exclude(snapshot.content)
    inserted, added = core.updated_exclude(snapshot, absent, core.EXPECTED_SKILLS[:1], False)
    assert added and inserted.startswith(b"prefix\n")
    present = core.parse_exclude(inserted)
    replaced, unchanged = core.updated_exclude(
        core.FileSnapshot(True, inserted, 0o600), present, core.EXPECTED_SKILLS[:2], added
    )
    assert unchanged and core.parse_exclude(replaced).entries == core.EXPECTED_SKILLS[:2]
    removed, added = core.updated_exclude(
        core.FileSnapshot(True, replaced, 0o600), core.parse_exclude(replaced), (), added
    )
    assert removed == b"prefix" and not added
    original, flag = core.updated_exclude(snapshot, absent, (), True)
    assert original == snapshot.content and flag


def test_regular_file_snapshot_handles_missing_safe_and_unsafe_paths(tmp_path: Path) -> None:
    missing = core.regular_file_bytes(tmp_path / "missing", maximum=10, label="test")
    assert not missing.existed
    path = tmp_path / "state"
    path.write_bytes(b"data")
    path.chmod(0o640)
    snapshot = core.regular_file_bytes(path, maximum=10, label="test")
    assert snapshot.content == b"data" and snapshot.mode == 0o640
    with pytest.raises(core.ToolError, match="oversized"):
        core.regular_file_bytes(path, maximum=3, label="test")
    path.unlink()
    path.mkdir()
    with pytest.raises(core.ToolError, match="ordinary file"):
        core.regular_file_bytes(path, maximum=10, label="test")


def test_frontmatter_and_canonical_skill_discovery_enforce_exact_catalog(tmp_path: Path) -> None:
    leaf = tmp_path / "skill"
    leaf.mkdir()
    skill_file = leaf / "SKILL.md"
    skill_file.write_text("---\nname: skill\ndescription: test\n---\nbody\n")
    assert core.frontmatter_name(skill_file) == "skill"
    for content in ("body\n", "---\nname: skill\n", "---\nname: bad name\n---\n"):
        skill_file.write_text(content)
        with pytest.raises(core.ToolError, match="metadata is malformed"):
            core.frontmatter_name(skill_file)

    skills_root = tmp_path / "skills"
    skills_root.mkdir()
    for name in (*core.EXPECTED_SKILLS, *core.KNOWN_UNMANAGED_SKILLS):
        path = skills_root / name
        path.mkdir()
        (path / "SKILL.md").write_text(f"---\nname: {name}\n---\n")
    discovered = core.canonical_skills(tmp_path)
    assert tuple(discovered) == core.EXPECTED_SKILLS
    go_source = skills_root / "corpus.go"
    go_source.write_text("package skills\n")
    assert tuple(core.canonical_skills(tmp_path)) == core.EXPECTED_SKILLS
    go_source.unlink()
    go_target = tmp_path / "outside.go"
    go_target.write_text("package skills\n")
    go_source.symlink_to(go_target)
    with pytest.raises(core.ToolError, match="unsupported owner or depth"):
        core.canonical_skills(tmp_path)
    go_source.unlink()
    extra = skills_root / "unexpected"
    extra.mkdir()
    with pytest.raises(core.ToolError, match="unsupported owner or depth"):
        core.canonical_skills(tmp_path)


def test_canonical_skill_discovery_resolves_declared_direct_and_chatgpt_paths(
    tmp_path: Path,
) -> None:
    assert len(core.EXPECTED_SKILLS) == 39
    assert "chatgpt-manager-workflow" in core.EXPECTED_SKILLS
    assert "dockerfile-profile" in core.EXPECTED_SKILLS
    assert "go-cmp-test-profile" in core.EXPECTED_SKILLS
    assert "gomock-test-profile" in core.EXPECTED_SKILLS
    assert "go-test-profile" in core.EXPECTED_SKILLS
    assert "minitest-test-profile" in core.EXPECTED_SKILLS
    assert "markdown-language-profile" in core.EXPECTED_SKILLS
    assert "nodejs-runtime-profile" in core.EXPECTED_SKILLS
    assert "vitest-test-profile" in core.EXPECTED_SKILLS
    assert "css-language-profile" in core.EXPECTED_SKILLS
    assert "vagrantfile-profile" in core.EXPECTED_SKILLS
    nested = {
        "chatgpt-manager-workflow",
        "composing-approved-roadmap-assignments",
    }
    for name in core.EXPECTED_SKILLS:
        relative = Path("chatgpt") / name if name in nested else Path(name)
        leaf = tmp_path / "skills" / relative
        leaf.mkdir(parents=True, exist_ok=True)
        (leaf / "SKILL.md").write_text(
            f"---\nname: {name}\n---\n",
            encoding="utf-8",
        )

    discovered = core.canonical_skills(tmp_path)

    assert tuple(discovered) == core.EXPECTED_SKILLS
    for name in nested:
        assert discovered[name] == (
            tmp_path / "skills" / "chatgpt" / name
        ).resolve()

    deeper = tmp_path / "skills/chatgpt/group/deeper"
    deeper.mkdir(parents=True)
    (deeper / "SKILL.md").write_text(
        "---\nname: deeper\n---\n",
        encoding="utf-8",
    )
    with pytest.raises(core.ToolError, match="canonical skill"):
        core.canonical_skills(tmp_path)

    shutil.rmtree(tmp_path / "skills/chatgpt/group")
    nested_owner = (
        tmp_path
        / "skills/chatgpt/composing-approved-roadmap-assignments/nested-owner"
    )
    nested_owner.mkdir()
    (nested_owner / "SKILL.md").write_text(
        "---\nname: nested-owner\n---\n",
        encoding="utf-8",
    )
    with pytest.raises(core.ToolError, match="unsupported owner or depth"):
        core.canonical_skills(tmp_path)


def test_git_adapter_sanitizes_environment_and_bounds_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def successful(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, "ok\n", "")

    monkeypatch.setenv("GIT_DIR", "unsafe")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "unsafe")
    monkeypatch.setattr(subprocess, "run", successful)
    result = core.run_git("repo", ["status"])
    assert result.stdout == "ok\n"
    assert "GIT_DIR" not in calls[0][1]["env"]  # type: ignore[operator]
    assert calls[0][0] == ["git", "-C", "repo", "status"]

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, "", "failed"),
    )
    assert core.run_git("repo", ["status"], allow_failure=True).returncode == 1
    with pytest.raises(core.ToolError, match="failed"):
        core.run_git("repo", ["status"])


def test_target_resolution_and_projection_queries_use_bounded_git_contracts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    def fake_git(directory: Path | str, arguments: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        del directory, kwargs
        values = {
            ("rev-parse", "--show-toplevel"): str(tmp_path),
            ("rev-parse", "--is-inside-work-tree"): "true",
            ("rev-parse", "--is-bare-repository"): "false",
            ("rev-parse", "--git-path", core.STATE_RELATIVE_PATH): str(git_dir / "state"),
            ("rev-parse", "--git-path", core.EXCLUDE_RELATIVE_PATH): str(git_dir / "exclude"),
        }
        return subprocess.CompletedProcess(arguments, 0, values.get(tuple(arguments), "") + "\n", "")

    monkeypatch.setattr(core, "run_git", fake_git)
    repository = core.resolve_target(str(tmp_path))
    assert repository == core.TargetRepository(tmp_path, git_dir / "state", git_dir / "exclude")
    assert core.git_resolved_path(tmp_path, core.STATE_RELATIVE_PATH) == git_dir / "state"
    assert core.relative_projection("one") == ".agents/skills/one"
    assert core.projection_path(repository, "one") == tmp_path / ".agents/skills/one"

    results = iter((0, 1, 2))
    monkeypatch.setattr(
        core,
        "run_git",
        lambda *args, **kwargs: subprocess.CompletedProcess([], next(results), "", ""),
    )
    assert core.is_tracked(repository, "one")
    assert not core.is_tracked(repository, "one")
    with pytest.raises(core.ToolError, match="tracked-path"):
        core.is_tracked(repository, "one")


def test_projection_parent_and_exact_link_contracts(tmp_path: Path) -> None:
    repository = core.TargetRepository(tmp_path, tmp_path / "state", tmp_path / "exclude")
    created = core.create_projection_parents(repository)
    assert created == [".agents", ".agents/skills"]
    assert core.create_projection_parents(repository) == []
    core.validate_projection_parents(repository)

    name = core.EXPECTED_SKILLS[0]
    canonical = tmp_path / "canonical" / name
    canonical.mkdir(parents=True)
    (canonical / "SKILL.md").write_text(f"---\nname: {name}\n---\n")
    link = core.projection_path(repository, name)
    link.symlink_to(canonical, target_is_directory=True)
    core.require_exact_link(repository, {name: canonical}, name, missing_context="managed")
    link.unlink()
    with pytest.raises(core.ToolError, match="missing"):
        core.require_exact_link(repository, {name: canonical}, name, missing_context="managed")
    link.write_text("conflict")
    with pytest.raises(core.ToolError, match="not a symbolic link"):
        core.require_exact_link(repository, {name: canonical}, name, missing_context="managed")


def test_state_serialization_readback_and_locked_descriptor_contracts(tmp_path: Path) -> None:
    state = core.LocalState(
        str(APG_ROOT),
        str(TARGET_ROOT),
        (core.EXPECTED_SKILLS[0],),
        (".agents", ".agents/skills"),
        True,
    )
    raw = core.serialize_state(state)
    assert core.parse_state(raw, APG_ROOT, TARGET_ROOT) == state
    path = tmp_path / "state"
    assert core.read_state(path, APG_ROOT, TARGET_ROOT) is None
    path.write_bytes(raw)
    path.chmod(0o600)
    assert core.read_state(path, APG_ROOT, TARGET_ROOT) == state
    path.chmod(0o644)
    with pytest.raises(core.ToolError, match="permissions"):
        core.read_state(path, APG_ROOT, TARGET_ROOT)

    path.chmod(0o600)
    descriptor = os.open(path, os.O_RDWR)
    try:
        assert core.read_locked_state(
            descriptor,
            created_placeholder=False,
            apg_root=APG_ROOT,
            target_root=TARGET_ROOT,
        ) == state
    finally:
        os.close(descriptor)
    empty = tmp_path / "empty"
    empty.touch(mode=0o600)
    descriptor = os.open(empty, os.O_RDWR)
    try:
        assert core.read_locked_state(
            descriptor,
            created_placeholder=True,
            apg_root=APG_ROOT,
            target_root=TARGET_ROOT,
        ) is None
    finally:
        os.close(descriptor)


def test_atomic_replace_restore_and_mutation_lock_preserve_owned_files(tmp_path: Path) -> None:
    path = tmp_path / "state"
    core.atomic_replace(path, b"first", 0o600)
    assert path.read_bytes() == b"first" and (path.stat().st_mode & 0o777) == 0o600
    snapshot = core.FileSnapshot(True, b"original", 0o640)
    core.restore_snapshot(path, snapshot)
    assert path.read_bytes() == b"original" and (path.stat().st_mode & 0o777) == 0o640
    core.restore_snapshot(path, core.FileSnapshot(False, b"", 0o600))
    assert not path.exists()

    lock = tmp_path / "lock"
    with core.mutation_lock(lock) as (descriptor, created):
        assert created and core.inode_matches(lock, descriptor)
        assert lock.exists()
    assert not lock.exists()
    lock.write_bytes(b"owned")
    lock.chmod(0o600)
    with core.mutation_lock(lock) as (_, created):
        assert not created
    assert lock.read_bytes() == b"owned"


def test_state_exclude_and_owned_projection_validation_report_each_mismatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    absent = core.ExcludeBlock(False, (), b"", b"")
    core.validate_state_and_exclude(None, absent)
    with pytest.raises(core.ToolError, match="without valid ownership"):
        core.validate_state_and_exclude(None, core.ExcludeBlock(True, (), b"", b""))
    state = core.LocalState("/apg", "/target", (core.EXPECTED_SKILLS[0],), (), False)
    with pytest.raises(core.ToolError, match="no APG exclude"):
        core.validate_state_and_exclude(state, absent)
    with pytest.raises(core.ToolError, match="disagrees"):
        core.validate_state_and_exclude(
            state,
            core.ExcludeBlock(True, (core.EXPECTED_SKILLS[1],), b"", b""),
        )

    repository = core.TargetRepository(tmp_path, tmp_path / "state", tmp_path / "exclude")
    (tmp_path / ".agents/skills").mkdir(parents=True)
    monkeypatch.setattr(core, "is_tracked", lambda *args: True)
    with pytest.raises(core.ToolError, match="tracked"):
        core.validate_owned_projections(repository, {}, state)
