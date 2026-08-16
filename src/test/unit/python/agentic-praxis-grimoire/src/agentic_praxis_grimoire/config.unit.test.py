"""Unit contracts for APGR declarative configuration precedence."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src"))

from agentic_praxis_grimoire import config


def write_config(path: Path, outbox_root: Path) -> None:
    path.parent.mkdir(parents=True)
    path.write_text(f'outbox_root = "{outbox_root}"\n', encoding="utf-8")


def test_outbox_root_precedence_is_explicit_project_global_default(
    tmp_path: Path,
) -> None:
    global_home = tmp_path / "global"
    project_root = tmp_path / "project"
    global_value = tmp_path / "global-outbox"
    project_value = tmp_path / "project-outbox"
    explicit_value = tmp_path / "explicit-outbox"
    write_config(global_home / "config.toml", global_value)
    write_config(project_root / ".apgr" / "config.toml", project_value)

    assert (
        config.resolve_outbox_root(
            apgr_home=global_home,
            project_root=project_root,
        )
        == project_value
    )
    assert (
        config.resolve_outbox_root(
            apgr_home=global_home,
            project_root=project_root,
            explicit=explicit_value,
        )
        == explicit_value
    )
    assert (
        config.resolve_outbox_root(apgr_home=global_home)
        == global_value
    )
    assert (
        config.resolve_outbox_root(
            apgr_home=tmp_path / "missing-global",
            home=tmp_path / "operator-home",
        )
        == tmp_path / "operator-home" / "Documents" / "agent" / "outbox"
    )


def test_project_root_discovery_stops_at_the_nearest_git_worktree(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    nested = repository / "src" / "nested"
    nested.mkdir(parents=True)
    (repository / ".git").mkdir()
    unrelated = tmp_path / ".git"
    unrelated.mkdir()
    assert config.discover_project_root(nested) == repository
    explicit = tmp_path / "synthetic"
    explicit.mkdir()
    assert config.discover_project_root(explicit=explicit) == explicit


def test_config_rejects_relative_or_unknown_outbox_values(tmp_path: Path) -> None:
    relative = tmp_path / "relative" / "config.toml"
    relative.parent.mkdir()
    relative.write_text('outbox_root = "reports"\n', encoding="utf-8")
    with pytest.raises(config.ConfigError, match="absolute"):
        config.load_config(relative)

    unknown = tmp_path / "unknown" / "config.toml"
    unknown.parent.mkdir()
    unknown.write_text('unexpected = "value"\n', encoding="utf-8")
    with pytest.raises(config.ConfigError, match="unsupported"):
        config.load_config(unknown)


@pytest.mark.parametrize("control", ("\\u0000", "\\u001f", "\\u007f"))
def test_config_rejects_control_bearing_outbox_paths(
    tmp_path: Path, control: str
) -> None:
    path = tmp_path / "control.toml"
    path.write_text(
        f'outbox_root = "{tmp_path}/unsafe{control}path"\n', encoding="utf-8"
    )

    with pytest.raises(config.ConfigError, match="control character"):
        config.load_config(path)


@pytest.mark.parametrize(
    "body,diagnostic",
    (
        ("outbox_root = 7\n", "non-empty string"),
        ("outbox_root = \"\"\n", "non-empty string"),
        ("outbox_root = [\n", "could not read"),
    ),
)
def test_config_rejects_invalid_toml_shapes(
    tmp_path: Path, body: str, diagnostic: str
) -> None:
    path = tmp_path / "config.toml"
    path.write_text(body, encoding="utf-8")
    with pytest.raises(config.ConfigError, match=diagnostic):
        config.load_config(path)


def test_config_absence_symlink_and_resolved_structure(tmp_path: Path) -> None:
    missing = tmp_path / "missing.toml"
    assert config.load_config(missing) == {}
    target = tmp_path / "target.toml"
    target.write_text(f'outbox_root = "{tmp_path / "outbox"}"\n', encoding="utf-8")
    link = tmp_path / "link.toml"
    link.symlink_to(target)
    with pytest.raises(config.ConfigError, match="ordinary file"):
        config.load_config(link)
    dangling = tmp_path / "dangling.toml"
    dangling.symlink_to(tmp_path / "absent-target.toml")
    with pytest.raises(config.ConfigError, match="ordinary file"):
        config.load_config(dangling)
    assert config.resolved_configuration(
        explicit=tmp_path / "explicit", apgr_home=tmp_path / "home"
    ) == {"outbox_root": tmp_path / "explicit"}


def test_start_discovers_project_configuration(tmp_path: Path) -> None:
    project = tmp_path / "project"
    nested = project / "nested"
    nested.mkdir(parents=True)
    (project / ".git").mkdir()
    selected = tmp_path / "selected"
    write_config(project / ".apgr" / "config.toml", selected)
    assert config.resolve_outbox_root(
        start=nested, apgr_home=tmp_path / "missing-home"
    ) == selected
