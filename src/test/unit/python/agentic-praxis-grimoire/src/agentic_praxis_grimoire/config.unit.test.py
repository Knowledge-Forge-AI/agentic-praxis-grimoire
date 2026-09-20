"""Unit contracts for APGR declarative configuration precedence."""

from __future__ import annotations

from pathlib import Path
import hashlib
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src"))

from agentic_praxis_grimoire import config  # noqa: E402


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


@pytest.mark.parametrize("body, diagnostic", (
    ('dispatcher = "command"', "dispatcher configuration must be a TOML table"),
    ('[dispatcher]\ncommand = "run"', "unsupported dispatcher configuration key"),
    ('[dispatcher]\nrouting = []', "dispatcher.routing configuration must be a TOML table"),
    ('[dispatcher.routing]\nprovider = "custom"', "unsupported routing configuration key"),
    ('[dispatcher.routing]\nexecution_mode = 7', "execution_mode must be a non-empty string"),
    ('[dispatcher.routing]\nexecution_mode = ""', "execution_mode must be a non-empty string"),
    ('[dispatcher.routing]\nexecution_mode = "unknown"', "unsupported execution_mode"),
))
def test_routing_schema_refuses_invalid_values(tmp_path, body, diagnostic):
    path = tmp_path / "config.toml"
    path.write_text(body, encoding="utf-8")
    with pytest.raises(config.ConfigError, match=diagnostic):
        config.load_config(path)


@pytest.mark.parametrize("body", ("", "[dispatcher]", "[dispatcher.routing]"))
def test_empty_optional_routing_tables_fall_through(tmp_path, body):
    project = tmp_path / "project"
    project_config = project / ".apgr/config.toml"
    project_config.parent.mkdir(parents=True)
    project_config.write_text(body, encoding="utf-8")
    global_home = tmp_path / "global"
    global_home.mkdir()
    global_config = global_home / "config.toml"
    global_config.write_text(body, encoding="utf-8")

    result = config.resolve_execution_mode(project_root=project, apgr_home=global_home)
    assert result.execution_mode == "dynamic"
    assert result.winner.source_type == "default"
    assert [item.source_type for item in result.provenance_chain] == [
        "project_config", "global_config", "default"
    ]
    assert [item.is_winner for item in result.provenance_chain] == [False, False, True]
    assert [item.precedence_rank for item in result.provenance_chain] == [2, 3, 4]
    for item, path in zip(result.provenance_chain, (project_config, global_config)):
        assert item.resolved_mode == ""
        assert item.source_path == str(path)
        assert item.content_digest == hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("mode", config.ROUTING_MODES)
def test_supported_modes_have_explicit_and_file_provenance(tmp_path, mode):
    project = tmp_path / "project"
    path = project / ".apgr/config.toml"
    path.parent.mkdir(parents=True)
    path.write_text(f'[dispatcher.routing]\nexecution_mode = "{mode}"\n', encoding="utf-8")
    assert config.load_config(path) == {"dispatcher": {"routing": {"execution_mode": mode}}}
    # A project winner prevents a malformed lower-precedence config from being read.
    global_home = tmp_path / "global"
    global_home.mkdir()
    (global_home / "config.toml").write_text("malformed = [", encoding="utf-8")
    result = config.resolve_execution_mode(project_root=project, apgr_home=global_home)
    assert result.execution_mode == mode
    assert result.provenance_chain == (result.winner,)
    assert result.winner.as_dict() == {
        "source_type": "project_config", "source_path": str(path),
        "content_digest": hashlib.sha256(path.read_bytes()).hexdigest(),
        "resolved_mode": mode, "is_winner": True, "precedence_rank": 2,
    }
    path.write_text("also malformed = [", encoding="utf-8")
    explicit = config.resolve_execution_mode(mode, project_root=project, apgr_home=global_home)
    assert explicit.execution_mode == mode
    assert explicit.provenance_chain == (explicit.winner,)
    assert explicit.winner.as_dict() == {
        "source_type": "cli", "source_path": None, "content_digest": None,
        "resolved_mode": mode, "is_winner": True, "precedence_rank": 1,
    }


def test_routing_global_winner_discovery_and_home_aliases(tmp_path):
    project = tmp_path / "project"
    nested = project / "nested"
    nested.mkdir(parents=True)
    (project / ".git").mkdir()
    path = project / ".apgr/config.toml"
    path.parent.mkdir()
    path.write_text("[dispatcher.routing]\n", encoding="utf-8")
    global_home = tmp_path / "global"
    global_home.mkdir()
    global_config = global_home / "config.toml"
    global_config.write_text('[dispatcher.routing]\nexecution_mode = "codex_only"\n', encoding="utf-8")
    for alias in ("cli_home", "apgr_home", "global_home"):
        result = config.resolve_execution_mode(start=nested, **{alias: global_home})
        assert result.execution_mode == "codex_only"
        assert [item.is_winner for item in result.provenance_chain] == [False, True]
        assert result.winner.as_dict() == {
            "source_type": "global_config", "source_path": str(global_config),
            "content_digest": hashlib.sha256(global_config.read_bytes()).hexdigest(),
            "resolved_mode": "codex_only", "is_winner": True, "precedence_rank": 3,
        }
    path.unlink()
    assert config.resolve_execution_mode(project_root=project, cli_home=global_home,
        apgr_home=tmp_path / "ignored", global_home=tmp_path / "also-ignored").execution_mode == "codex_only"
    global_config.unlink()
    result = config.resolve_execution_mode(project_root=project, apgr_home=global_home)
    assert result.provenance_chain == (result.winner,)
    assert result.winner.source_type == "default"


def test_invalid_explicit_mode_and_malformed_project_do_not_fall_back(tmp_path):
    with pytest.raises(config.ConfigError, match="unsupported execution_mode"):
        config.resolve_execution_mode("unknown")
    path = tmp_path / ".apgr/config.toml"
    path.parent.mkdir()
    path.write_text('[dispatcher.routing]\nexecution_mode = "unknown"\n', encoding="utf-8")
    with pytest.raises(config.ConfigError, match="unsupported execution_mode"):
        config.resolve_execution_mode(project_root=tmp_path, apgr_home=tmp_path / "global")


def test_empty_project_config_preserves_global_outbox_and_binary_path_is_refused(tmp_path):
    project = tmp_path / "project"
    path = project / ".apgr/config.toml"
    path.parent.mkdir(parents=True)
    path.write_text("[dispatcher]\n", encoding="utf-8")
    global_home = tmp_path / "global"
    value = tmp_path / "outbox"
    write_config(global_home / "config.toml", value)
    assert config.resolve_outbox_root(project_root=project, global_home=global_home) == value
    with pytest.raises(config.ConfigError, match="not a valid path"):
        config.load_config(b"/binary-path")
