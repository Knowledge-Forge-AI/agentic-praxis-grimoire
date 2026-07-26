"""Unit tests for project-skill command selection and state comparison."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import apg_project_skills_commands as commands  # noqa: E402
import apg_project_skills_core as core  # noqa: E402
from apg_project_skills_core import (  # noqa: E402
    ExcludeBlock,
    FileSnapshot,
    LocalState,
    TargetRepository,
    ToolError,
)


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    value.exit = lambda status=0, message=None: (_ for _ in ()).throw(  # type: ignore[method-assign]
        ValueError(message or status)
    )
    return value


def test_selected_skills_defaults_sorts_and_rejects_unknown_or_duplicate() -> None:
    assert commands.selected_skills(parser(), None) == ()
    selected = [commands.EXPECTED_SKILLS[1], commands.EXPECTED_SKILLS[0]]
    assert commands.selected_skills(parser(), selected) == tuple(sorted(selected))
    with pytest.raises(ValueError, match="unknown"):
        commands.selected_skills(parser(), ["unknown"])
    with pytest.raises(ValueError, match="only once"):
        commands.selected_skills(parser(), [selected[0], selected[0]])


def test_state_content_match_handles_absent_regular_symlink_and_read_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "state"
    assert commands.state_content_matches(path, None)
    assert not commands.state_content_matches(path, b"data")
    path.write_bytes(b"data")
    assert not commands.state_content_matches(path, None)
    assert commands.state_content_matches(path, b"data")
    assert not commands.state_content_matches(path, b"other")
    target = tmp_path / "target"
    target.write_bytes(b"data")
    path.unlink()
    path.symlink_to(target)
    assert not commands.state_content_matches(path, b"data")
    monkeypatch.setattr(Path, "read_bytes", lambda _self: (_ for _ in ()).throw(OSError()))
    assert not commands.state_content_matches(target, b"data")


def repository(tmp_path: Path) -> TargetRepository:
    root = tmp_path / "repo"
    root.mkdir()
    git = root / ".git"
    git.mkdir()
    return TargetRepository(root, git / "apg-state.json", git / "info/exclude")


def test_idempotent_status_rejects_visible_projection(monkeypatch: pytest.MonkeyPatch) -> None:
    target = TargetRepository(Path("repo"), Path("state"), Path("exclude"))
    monkeypatch.setattr(commands, "managed_status", lambda *_args: "visible")
    with pytest.raises(ToolError, match="visible in normal Git status"):
        commands.require_idempotent_status_compliance(target, ("skill",))
    monkeypatch.setattr(commands, "managed_status", lambda *_args: "")
    commands.require_idempotent_status_compliance(target, ("skill",))


def test_rollback_install_restores_snapshot_links_and_empty_containers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = repository(tmp_path)
    canonical_root = tmp_path / "canonical"
    canonical_root.mkdir()
    skill = commands.EXPECTED_SKILLS[0]
    canonical = canonical_root / skill
    canonical.mkdir()
    projection = target.root / ".agents/skills" / skill
    projection.parent.mkdir(parents=True)
    projection.symlink_to(canonical, target_is_directory=True)
    restored: list[object] = []
    monkeypatch.setattr(commands, "projection_path", lambda *_args: projection)
    monkeypatch.setattr(
        commands,
        "restore_snapshot",
        lambda path, snapshot: restored.append((path, snapshot)),
    )
    commands.rollback_install(
        target,
        {skill: canonical},
        [skill],
        [".agents", ".agents/skills"],
        FileSnapshot(False, b"", 0o600),
    )
    assert not projection.exists()
    assert not (target.root / ".agents").exists()
    assert restored


def test_rollback_install_reports_concurrent_change_and_restore_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = repository(tmp_path)
    skill = commands.EXPECTED_SKILLS[0]
    path = target.root / "conflict"
    path.write_text("conflict", encoding="utf-8")
    monkeypatch.setattr(commands, "projection_path", lambda *_args: path)
    monkeypatch.setattr(
        commands,
        "restore_snapshot",
        lambda *_args: (_ for _ in ()).throw(OSError("restore")),
    )
    with pytest.raises(ToolError, match="rollback was incomplete"):
        commands.rollback_install(
            target,
            {skill: tmp_path / "canonical"},
            [skill],
            [],
            FileSnapshot(False, b"", 0o600),
        )


def test_check_distinguishes_uninstalled_unmanaged_and_managed_states(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    target = repository(tmp_path)
    snapshot = FileSnapshot(False, b"", 0o600)
    monkeypatch.setattr(commands, "regular_file_bytes", lambda *_args, **_kwargs: snapshot)
    monkeypatch.setattr(commands, "parse_exclude", lambda _content: ExcludeBlock(False, (), b"", b""))
    monkeypatch.setattr(commands, "validate_state_and_exclude", lambda *_args: None)
    monkeypatch.setattr(commands, "read_state", lambda *_args: None)
    monkeypatch.setattr(commands.os.path, "lexists", lambda _path: False)
    commands.check(target, {}, (), tmp_path)
    assert "compliant uninstalled" in capsys.readouterr().out
    monkeypatch.setattr(commands.os.path, "lexists", lambda _path: True)
    commands.check(target, {}, (), tmp_path)
    assert "unmanaged projection paths" in capsys.readouterr().out
    with pytest.raises(ToolError, match="not locally managed"):
        commands.check(target, {}, (commands.EXPECTED_SKILLS[0],), tmp_path)

    skill = commands.EXPECTED_SKILLS[0]
    state = LocalState(str(tmp_path), str(target.root), (skill,), (), False)
    monkeypatch.setattr(commands, "read_state", lambda *_args: state)
    monkeypatch.setattr(commands, "validate_owned_projections", lambda *_args: None)
    monkeypatch.setattr(commands, "managed_status", lambda *_args: "")
    commands.check(target, {skill: tmp_path / skill}, (), tmp_path)
    assert "1 managed skill" in capsys.readouterr().out
    with pytest.raises(ToolError, match="not in local ownership"):
        commands.check(target, {}, (commands.EXPECTED_SKILLS[1],), tmp_path)
    monkeypatch.setattr(commands, "managed_status", lambda *_args: "dirty")
    with pytest.raises(ToolError, match="not clean"):
        commands.check(target, {}, (), tmp_path)


def test_recreate_removed_links_restores_owned_paths_and_reports_conflicts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = repository(tmp_path)
    skill = commands.EXPECTED_SKILLS[0]
    canonical = tmp_path / "canonical"
    canonical.mkdir()
    projection = target.root / ".agents/skills" / skill
    monkeypatch.setattr(commands, "projection_path", lambda *_args: projection)
    assert commands.recreate_removed_links(
        target,
        {skill: canonical},
        [skill],
        [".agents", ".agents/skills"],
    ) == []
    assert projection.resolve() == canonical
    projection.unlink()
    projection.write_text("conflict", encoding="utf-8")
    errors = commands.recreate_removed_links(target, {skill: canonical}, [skill], [])
    assert errors == [f"link changed concurrently: {skill}"]


def test_uninstall_no_state_is_a_truthful_noop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    target = repository(tmp_path)

    @contextmanager
    def lock(_path: Path):
        yield 1, False

    monkeypatch.setattr(commands, "mutation_lock", lock)
    monkeypatch.setattr(commands, "read_locked_state", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        commands,
        "regular_file_bytes",
        lambda *_args, **_kwargs: FileSnapshot(False, b"", 0o600),
    )
    monkeypatch.setattr(commands, "parse_exclude", lambda _content: ExcludeBlock(False, (), b"", b""))
    monkeypatch.setattr(commands, "validate_state_and_exclude", lambda *_args: None)
    monkeypatch.setattr(commands.os.path, "lexists", lambda _path: False)
    commands.uninstall(target, {}, (), tmp_path)
    assert "already fully uninstalled" in capsys.readouterr().out
    monkeypatch.setattr(commands.os.path, "lexists", lambda _path: True)
    commands.uninstall(target, {}, (), tmp_path)
    assert "unmanaged projection paths" in capsys.readouterr().out


def test_parser_and_main_route_each_operation(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    parser_value = commands.build_parser()
    assert parser_value.parse_args(["check"]).command == "check"
    monkeypatch.setattr(commands, "physical_apg_root", lambda: Path("apg"))
    monkeypatch.setattr(commands, "canonical_skills", lambda _root: {})
    assert commands.main(["list"]) == 0
    assert commands.EXPECTED_SKILLS[0] in capsys.readouterr().out
    with pytest.raises(SystemExit):
        commands.main(["check", "--repo", "one", "--repo", "two"])
    target = TargetRepository(Path("repo"), Path("state"), Path("exclude"))
    monkeypatch.setattr(commands, "resolve_target", lambda _path: target)
    monkeypatch.setattr(commands, "install_signal_handlers", lambda: None)
    observed: list[str] = []
    for name in ("install", "adopt", "check", "uninstall"):
        monkeypatch.setattr(
            commands,
            name,
            lambda *_args, selected=name: observed.append(selected),
        )
    for name in ("install", "adopt", "check", "uninstall"):
        assert commands.main([name]) == 0
    assert observed == ["install", "adopt", "check", "uninstall"]
    assert commands.main(["check", "--repo", "chosen"]) == 0
    assert observed[-1] == "check"


def test_real_filesystem_install_check_uninstall_and_adopt_lifecycles(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(commands, "is_tracked", lambda *_args: False)
    monkeypatch.setattr(commands, "managed_status", lambda *_args: "")
    monkeypatch.setattr(core, "is_tracked", lambda *_args: False)
    skill, second_skill = commands.EXPECTED_SKILLS[:2]
    canonical: dict[str, Path] = {}
    for name in (skill, second_skill):
        path = tmp_path / "canonical" / name
        path.mkdir(parents=True)
        (path / "SKILL.md").write_text(
            f"---\nname: {name}\n---\n",
            encoding="utf-8",
        )
        canonical[name] = path.resolve()
    canonical_path = canonical[skill]

    install_root = tmp_path / "install-target"
    install_root.mkdir()
    install_target = repository(install_root)
    install_target.exclude_path.parent.mkdir()
    commands.install(install_target, canonical, (skill, second_skill), tmp_path)
    assert commands.projection_path(install_target, skill).resolve() == canonical_path
    assert install_target.state_path.is_file()
    commands.install(install_target, canonical, (), tmp_path)
    commands.check(install_target, canonical, (), tmp_path)
    commands.uninstall(install_target, canonical, (skill,), tmp_path)
    assert commands.projection_path(install_target, second_skill).exists()
    commands.uninstall(install_target, canonical, (), tmp_path)
    assert not install_target.state_path.exists()

    adopt_root = tmp_path / "adopt-target"
    adopt_root.mkdir()
    adopt_target = repository(adopt_root)
    adopt_target.exclude_path.parent.mkdir()
    projection = commands.projection_path(adopt_target, skill)
    projection.parent.mkdir(parents=True)
    projection.symlink_to(canonical_path, target_is_directory=True)
    commands.adopt(adopt_target, canonical, (skill,), tmp_path)
    assert adopt_target.state_path.is_file()
    assert "managed 1 skill" in capsys.readouterr().out


def test_signal_handlers_translate_process_signals_to_bounded_tool_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handlers: dict[int, object] = {}
    monkeypatch.setattr(commands.signal, "signal", lambda number, handler: handlers.setdefault(number, handler))
    commands.install_signal_handlers()
    handler = handlers[commands.signal.SIGINT]
    with pytest.raises(ToolError, match="SIGINT"):
        handler(commands.signal.SIGINT, None)  # type: ignore[operator]
    monkeypatch.delattr(commands.signal, "SIGHUP")
    commands.install_signal_handlers()

def test_recreate_removed_links_reports_concurrent_container_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = repository(tmp_path)
    conflict = target.root / ".agents"
    conflict.write_text("not a directory")
    errors = commands.recreate_removed_links(target, {}, (), (".agents",))
    assert errors == ["container changed concurrently: .agents"]
