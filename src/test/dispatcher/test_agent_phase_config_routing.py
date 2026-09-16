from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import pytest

from agent_phase.config_routing import (
    DEFAULT_EXECUTION_MODE,
    ROUTING_MODES,
    ConfigError,
    load_config_file,
    resolve_execution_mode,
)


def test_supported_execution_modes() -> None:
    assert DEFAULT_EXECUTION_MODE == "dynamic"
    assert "dynamic" in ROUTING_MODES
    assert "normal" in ROUTING_MODES
    assert "codex_only" in ROUTING_MODES
    assert "gemini_sub" in ROUTING_MODES


def test_load_valid_config(tmp_path: Path) -> None:
    cfg = tmp_path / "config.toml"
    cfg.write_text("""
outbox_root = "/tmp/outbox"

[dispatcher.routing]
execution_mode = "conserve_claude"
""")
    loaded = load_config_file(cfg)
    assert loaded["outbox_root"] == "/tmp/outbox"
    assert loaded["dispatcher"]["routing"]["execution_mode"] == "conserve_claude"


def test_load_empty_or_nonexistent_config(tmp_path: Path) -> None:
    nonexistent = tmp_path / "does_not_exist.toml"
    assert load_config_file(nonexistent) == {}


def test_reject_unknown_root_key(tmp_path: Path) -> None:
    cfg = tmp_path / "config.toml"
    cfg.write_text("unknown_root_key = 'bad'\n")
    with pytest.raises(ConfigError, match="unsupported configuration key"):
        load_config_file(cfg)


def test_reject_unknown_dispatcher_key(tmp_path: Path) -> None:
    cfg = tmp_path / "config.toml"
    cfg.write_text("""
[dispatcher]
unknown_section = true
""")
    with pytest.raises(ConfigError, match="unsupported key in \\[dispatcher\\]"):
        load_config_file(cfg)


def test_reject_unknown_routing_key(tmp_path: Path) -> None:
    cfg = tmp_path / "config.toml"
    cfg.write_text("""
[dispatcher.routing]
execution_mode = "dynamic"
unknown_field = "oops"
""")
    with pytest.raises(ConfigError, match="unsupported key in \\[dispatcher.routing\\]"):
        load_config_file(cfg)


def test_reject_unsupported_execution_mode(tmp_path: Path) -> None:
    cfg = tmp_path / "config.toml"
    cfg.write_text("""
[dispatcher.routing]
execution_mode = "unsupported_futuristic_mode"
""")
    with pytest.raises(ConfigError, match="unsupported execution_mode"):
        load_config_file(cfg)


def test_reject_non_string_execution_mode(tmp_path: Path) -> None:
    cfg = tmp_path / "config.toml"
    cfg.write_text("""
[dispatcher.routing]
execution_mode = 42
""")
    with pytest.raises(ConfigError, match="execution_mode.*must be a string"):
        load_config_file(cfg)


def test_precedence_tier_1_cli_wins(tmp_path: Path) -> None:
    # Setup project config and global config
    project_dir = tmp_path / "project"
    project_apgr = project_dir / ".apgr"
    project_apgr.mkdir(parents=True)
    (project_apgr / "config.toml").write_text("""
[dispatcher.routing]
execution_mode = "claude_only"
""")

    global_dir = tmp_path / "global_home"
    global_dir.mkdir(parents=True)
    (global_dir / "config.toml").write_text("""
[dispatcher.routing]
execution_mode = "codex_only"
""")

    # Explicit CLI argument must win
    res = resolve_execution_mode(
        explicit="normal",
        project_root=project_dir,
        apgr_home=global_dir,
    )
    assert res.execution_mode == "normal"
    assert res.winner.source_type == "cli"
    assert res.winner.precedence_rank == 1
    assert res.winner.is_winner is True
    assert res.winner.resolved_mode == "normal"


def test_precedence_tier_2_project_config_wins(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_apgr = project_dir / ".apgr"
    project_apgr.mkdir(parents=True)
    cfg_file = project_apgr / "config.toml"
    cfg_content = """
[dispatcher.routing]
execution_mode = "conserve_claude"
"""
    cfg_file.write_text(cfg_content)
    digest = hashlib.sha256(cfg_content.encode("utf-8")).hexdigest()

    global_dir = tmp_path / "global_home"
    global_dir.mkdir(parents=True)
    (global_dir / "config.toml").write_text("""
[dispatcher.routing]
execution_mode = "codex_only"
""")

    res = resolve_execution_mode(
        project_root=project_dir,
        apgr_home=global_dir,
    )
    assert res.execution_mode == "conserve_claude"
    assert res.winner.source_type == "project_config"
    assert res.winner.source_path == str(cfg_file)
    assert res.winner.content_digest == digest
    assert res.winner.precedence_rank == 2
    assert res.winner.is_winner is True


def test_precedence_tier_3_global_config_wins(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    # No .apgr in project

    global_dir = tmp_path / "global_home"
    global_dir.mkdir(parents=True)
    cfg_file = global_dir / "config.toml"
    cfg_content = """
[dispatcher.routing]
execution_mode = "gemini_sub"
"""
    cfg_file.write_text(cfg_content)
    digest = hashlib.sha256(cfg_content.encode("utf-8")).hexdigest()

    res = resolve_execution_mode(
        project_root=project_dir,
        apgr_home=global_dir,
    )
    assert res.execution_mode == "gemini_sub"
    assert res.winner.source_type == "global_config"
    assert res.winner.source_path == str(cfg_file)
    assert res.winner.content_digest == digest
    assert res.winner.precedence_rank == 3
    assert res.winner.is_winner is True


def test_precedence_tier_4_default_dynamic(tmp_path: Path) -> None:
    empty_project = tmp_path / "project"
    empty_project.mkdir()
    empty_global = tmp_path / "global"
    empty_global.mkdir()

    res = resolve_execution_mode(
        project_root=empty_project,
        apgr_home=empty_global,
    )
    assert res.execution_mode == "dynamic"
    assert res.winner.source_type == "default"
    assert res.winner.source_path is None
    assert res.winner.content_digest is None
    assert res.winner.precedence_rank == 4
    assert res.winner.is_winner is True


def test_cli_rejects_execution_mode_for_v1(tmp_path: Path) -> None:
    from agent_phase.cli import resolve_main

    v1_file = tmp_path / "req_v1.json"
    v1_file.write_text(json.dumps({
        "schema": "agent-phase-request-v1",
        "phase_type": "implementation_testing",
        "execution_mode": "normal",
        "prompt": "test prompt",
    }))

    # Invoking resolve_main with --execution-mode and a V1 request must exit with code 2
    with pytest.raises(SystemExit) as exc_info:
        resolve_main([str(v1_file), "--execution-mode", "conserve_claude"])
    assert exc_info.value.code == 2


def test_config_parity_between_package_and_dispatcher(tmp_path: Path) -> None:
    src_dir = str(Path(__file__).resolve().parents[3] / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    from agentic_praxis_grimoire import config as pkg_config
    import agent_phase.config_routing as disp_config

    # Mode collections parity
    assert set(pkg_config.ROUTING_MODES) == set(disp_config.ROUTING_MODES)
    assert pkg_config.DEFAULT_EXECUTION_MODE == disp_config.DEFAULT_EXECUTION_MODE
    assert set(pkg_config.RETAINED_STATIC_MODES) == set(disp_config.RETAINED_STATIC_MODES)

    # Valid config resolution parity across tiers
    proj_dir = tmp_path / "proj"
    proj_apgr = proj_dir / ".apgr"
    proj_apgr.mkdir(parents=True)
    (proj_apgr / "config.toml").write_text("""
[dispatcher.routing]
execution_mode = "gemini_opus"
""")
    global_dir = tmp_path / "global"
    global_dir.mkdir(parents=True)
    (global_dir / "config.toml").write_text("""
[dispatcher.routing]
execution_mode = "codex_only"
""")

    # Tier 1 parity: explicit CLI
    res_pkg_1 = pkg_config.resolve_execution_mode("normal", project_root=proj_dir, apgr_home=global_dir)
    res_disp_1 = disp_config.resolve_execution_mode("normal", project_root=proj_dir, apgr_home=global_dir)
    assert res_pkg_1.execution_mode == res_disp_1.execution_mode == "normal"
    assert res_pkg_1.winner.as_dict() == res_disp_1.winner.as_dict()

    # Tier 2 parity: project config
    res_pkg_2 = pkg_config.resolve_execution_mode(project_root=proj_dir, apgr_home=global_dir)
    res_disp_2 = disp_config.resolve_execution_mode(project_root=proj_dir, apgr_home=global_dir)
    assert res_pkg_2.execution_mode == res_disp_2.execution_mode == "gemini_opus"
    assert res_pkg_2.winner.as_dict() == res_disp_2.winner.as_dict()

    # Tier 3 parity: global config
    empty_proj = tmp_path / "empty_proj"
    empty_proj.mkdir()
    res_pkg_3 = pkg_config.resolve_execution_mode(project_root=empty_proj, apgr_home=global_dir)
    res_disp_3 = disp_config.resolve_execution_mode(project_root=empty_proj, apgr_home=global_dir)
    assert res_pkg_3.execution_mode == res_disp_3.execution_mode == "codex_only"
    assert res_pkg_3.winner.as_dict() == res_disp_3.winner.as_dict()

    # Tier 4 parity: default dynamic
    empty_global = tmp_path / "empty_global"
    empty_global.mkdir()
    res_pkg_4 = pkg_config.resolve_execution_mode(project_root=empty_proj, apgr_home=empty_global)
    res_disp_4 = disp_config.resolve_execution_mode(project_root=empty_proj, apgr_home=empty_global)
    assert res_pkg_4.execution_mode == res_disp_4.execution_mode == "dynamic"
    assert res_pkg_4.winner.as_dict() == res_disp_4.winner.as_dict()

    # Error classification parity on invalid keys
    bad_cfg = tmp_path / "bad.toml"
    bad_cfg.write_text("invalid_key = 123\n")
    with pytest.raises(pkg_config.ConfigError):
        pkg_config.load_config(bad_cfg)
    with pytest.raises(disp_config.ConfigError):
        disp_config.load_config_file(bad_cfg)

    # Error classification parity on invalid execution_mode
    bad_mode_cfg = tmp_path / "bad_mode.toml"
    bad_mode_cfg.write_text("""
[dispatcher.routing]
execution_mode = "totally_bogus"
""")
    with pytest.raises(pkg_config.ConfigError):
        pkg_config.load_config(bad_mode_cfg)
    with pytest.raises(disp_config.ConfigError):
        disp_config.load_config_file(bad_mode_cfg)

