from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import pytest

from agent_phase.bundle import publish_bundle

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


def test_resolve_review_mutation_policy_all_tiers(tmp_path: Path) -> None:
    from agent_phase.config_routing import resolve_review_mutation_policy

    repo_root = Path(__file__).resolve().parents[3]
    op_home = tmp_path / "operator_home"
    disp = op_home / "dispatcher"
    disp.mkdir(parents=True)

    source = tmp_path / "source"
    shutil.copytree(repo_root / "common" / "dispatcher", source)
    gen = 42
    for name in ("routes.toml", "endpoints.toml", "capabilities.toml", "policy.toml", "models.toml", "workers.toml"):
        p = source / name
        content = p.read_text(encoding="utf-8")
        content = re.sub(r"generation = \d+", f"generation = {gen}", content)
        if name == "policy.toml":
            content = re.sub(r'worktree = "[^"]+"', 'worktree = "warn"', content)
        p.write_text(content, encoding="utf-8")
    publish_bundle(source, disp, expected_generation=gen)

    # Tier 4: Operator bundle generation 42
    res_tier4 = resolve_review_mutation_policy(
        repository_root=str(repo_root),
        apgr_home=str(op_home),
    )
    assert res_tier4.policy.generation == 42
    assert res_tier4.policy.worktree == "warn"
    assert res_tier4.winner.source_type == "operator_default"
    assert res_tier4.winner.resolved_mode == "warn"

    # Tier 3: Global config.toml overrides operator bundle
    (op_home / "config.toml").write_text("""
[dispatcher.review_mutation]
worktree = "block"
index = "block"
head = "block"
""")
    res_tier3 = resolve_review_mutation_policy(
        repository_root=str(repo_root),
        apgr_home=str(op_home),
    )
    assert res_tier3.policy.worktree == "block"
    assert res_tier3.winner.source_type == "global_config"
    assert res_tier3.winner.resolved_mode == "block"

    # Tier 2: Project config.toml overrides global config
    proj_dir = tmp_path / "proj"
    (proj_dir / ".apgr").mkdir(parents=True)
    (proj_dir / ".apgr" / "config.toml").write_text("""
[dispatcher.review_mutation]
worktree = "allow"
index = "block"
head = "block"
""")
    res_tier2 = resolve_review_mutation_policy(
        project_root=str(proj_dir),
        repository_root=str(repo_root),
        apgr_home=str(op_home),
    )
    assert res_tier2.policy.worktree == "allow"
    assert res_tier2.winner.source_type == "project_config"
    assert res_tier2.winner.resolved_mode == "allow"

    # Tier 1: Explicit CLI overrides project config
    res_tier1 = resolve_review_mutation_policy(
        explicit="warn",
        project_root=str(proj_dir),
        repository_root=str(repo_root),
        apgr_home=str(op_home),
    )
    assert res_tier1.policy.worktree == "warn"
    assert res_tier1.winner.source_type == "cli"
    assert res_tier1.winner.resolved_mode == "warn"


def test_resolve_review_mutation_policy_operator_generation_mismatch_fails(tmp_path: Path) -> None:
    from agent_phase.config_routing import resolve_review_mutation_policy, ConfigError

    repo_root = Path(__file__).resolve().parents[3]
    op_home = tmp_path / "operator_home"
    disp = op_home / "dispatcher"
    source = tmp_path / "source"
    shutil.copytree(repo_root / "common" / "dispatcher", source)

    publish_bundle(source, disp, expected_generation=9)

    policy_file = disp / "policy.toml"
    policy_file.write_text(
        re.sub(r"generation = \d+", "generation = 999", policy_file.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    manifest_path = disp / "bundle.json"
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest_data.get("files") or manifest_data.get("members")
    files["policy.toml"]["sha256"] = hashlib.sha256(policy_file.read_bytes()).hexdigest()
    files["policy.toml"]["bytes"] = policy_file.stat().st_size
    manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    with pytest.raises(ConfigError, match="generation mismatch"):
        resolve_review_mutation_policy(
            repository_root=str(repo_root),
            apgr_home=str(op_home),
        )


def test_resolve_review_mutation_policy_invalid_policy_axis_fails(tmp_path: Path) -> None:
    from agent_phase.config_routing import resolve_review_mutation_policy, ConfigError

    repo_root = Path(__file__).resolve().parents[3]
    op_home = tmp_path / "operator_home"
    disp = op_home / "dispatcher"
    source = tmp_path / "source"
    shutil.copytree(repo_root / "common" / "dispatcher", source)

    publish_bundle(source, disp, expected_generation=9)

    policy_file = disp / "policy.toml"
    policy_file.write_text(
        re.sub(r'worktree = "[^"]+"', 'worktree = "invalid_axis"', policy_file.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    manifest_path = disp / "bundle.json"
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest_data.get("files") or manifest_data.get("members")
    files["policy.toml"]["sha256"] = hashlib.sha256(policy_file.read_bytes()).hexdigest()
    files["policy.toml"]["bytes"] = policy_file.stat().st_size
    manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    with pytest.raises(ConfigError, match="unsupported worktree"):
        resolve_review_mutation_policy(
            repository_root=str(repo_root),
            apgr_home=str(op_home),
        )


def test_config_symlink_rejection_parity(tmp_path: Path) -> None:
    import agentic_praxis_grimoire.config as pkg_config
    import agent_phase.config_routing as disp_config

    real_file = tmp_path / "real.toml"
    real_file.write_text("[dispatcher.routing]\nexecution_mode = 'normal'\n")
    sym_file = tmp_path / "symlink.toml"
    sym_file.symlink_to(real_file)

    with pytest.raises(pkg_config.ConfigError, match="not an ordinary file"):
        pkg_config.load_config(sym_file)

    with pytest.raises(disp_config.ConfigError, match="not an ordinary file"):
        disp_config.load_config_file(sym_file)


def test_scoped_home_and_dispatcher_reject_relative_path(tmp_path: Path) -> None:
    from agent_phase.dispatch import Dispatcher, _scoped_apgr_home

    repo_root = Path(__file__).resolve().parents[3]

    with pytest.raises(ValueError, match="absolute path"):
        with _scoped_apgr_home("relative/path"):
            pass

    with pytest.raises(ValueError, match="absolute path"):
        Dispatcher(
            root=repo_root,
            cwd=tmp_path,
            apgr_home="relative/path",
            resolve_scanner=False,
        )


def test_outbox_projection_in_generation_shaped_closure_without_src(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import shutil

    gen_root = tmp_path / "gen_root"
    shutil.copytree("libexec", gen_root / "libexec")

    custom_home = tmp_path / "custom_home"
    custom_home.mkdir()
    custom_outbox = tmp_path / "configured_outbox"
    (custom_home / "config.toml").write_text(f'outbox_root = "{custom_outbox}"\n')

    # Ensure gen_root has NO src directory
    assert not (gen_root / "src").exists()

    monkeypatch.delenv("APGR_OUTBOX_ROOT", raising=False)
    monkeypatch.delenv("APGR_RUN_ROOT", raising=False)
    monkeypatch.delenv("AGENT_PHASE_RUN_ROOT", raising=False)

    saved_path = list(sys.path)
    clean_path = [str(gen_root / "libexec")] + [p for p in sys.path if not p.endswith("/src") and not p.endswith("\\src") and p != "src"]
    monkeypatch.setattr(sys, "path", clean_path)

    for mod_name in list(sys.modules.keys()):
        if mod_name.startswith(("agentic_praxis_grimoire", "agent_phase")):
            monkeypatch.delitem(sys.modules, mod_name, raising=False)

    import agent_phase.outbox_projection as proj
    resolved = proj.resolve_outbox_root(apgr_home=custom_home)
    assert resolved == custom_outbox.resolve()



def test_run_default_root_precedence_and_error_propagation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agent_phase import run as run_module
    from agent_phase.config_routing import ConfigError

    project_dir = tmp_path / "project"
    project_apgr = project_dir / ".apgr"
    project_apgr.mkdir(parents=True)
    proj_outbox = tmp_path / "project_outbox"
    (project_apgr / "config.toml").write_text(f'outbox_root = "{proj_outbox}"\n')

    global_home = tmp_path / "global_home"
    global_home.mkdir()
    global_outbox = tmp_path / "global_outbox"
    (global_home / "config.toml").write_text(f'outbox_root = "{global_outbox}"\n')

    env_outbox = tmp_path / "env_outbox"
    monkeypatch.delenv("APGR_OUTBOX_ROOT", raising=False)
    monkeypatch.setenv("APGR_RUN_ROOT", str(env_outbox))
    monkeypatch.setenv("AGENT_PHASE_RUN_ROOT", str(tmp_path / "legacy_env_outbox"))

    # Project config wins over global config and APGR_RUN_ROOT
    assert run_module.default_root(apgr_home=global_home, project_root=project_dir) == proj_outbox.resolve()

    # Global config wins over APGR_RUN_ROOT when project config has no outbox_root
    (project_apgr / "config.toml").write_text("[dispatcher.routing]\nexecution_mode = 'dynamic'\n")
    assert run_module.default_root(apgr_home=global_home, project_root=project_dir) == global_outbox.resolve()

    # APGR_RUN_ROOT wins over AGENT_PHASE_RUN_ROOT when neither config has outbox_root
    (global_home / "config.toml").write_text("[dispatcher.routing]\nexecution_mode = 'dynamic'\n")
    assert run_module.default_root(apgr_home=global_home, project_root=project_dir) == env_outbox.resolve()

    # Malformed config raises ConfigError rather than being swallowed into default
    (project_apgr / "config.toml").write_text("invalid TOML content [[\n")
    with pytest.raises(ConfigError):
        run_module.default_root(apgr_home=global_home, project_root=project_dir)


def test_global_outbox_precedence_value_independent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agent_phase import run as run_module
    from agent_phase.config_routing import resolve_outbox_root, default_outbox_root

    fake_home = tmp_path / "fake_home"
    global_apgr = fake_home / ".apgr"
    global_apgr.mkdir(parents=True)
    def_outbox = default_outbox_root(home=fake_home)
    # Configure global config outbox_root to explicitly match the default path
    (global_apgr / "config.toml").write_text(f'outbox_root = "{def_outbox}"\n', encoding="utf-8")

    env_outbox = tmp_path / "env_outbox"
    monkeypatch.setenv("APGR_RUN_ROOT", str(env_outbox))
    monkeypatch.setenv("AGENT_PHASE_RUN_ROOT", str(tmp_path / "legacy_env"))

    # Global config MUST win over APGR_RUN_ROOT even when its value coincides with default_outbox_root
    resolved = resolve_outbox_root(home=fake_home)
    assert resolved == def_outbox.resolve()
    assert resolved != env_outbox.resolve()

    # Verify no-home path with APGR_HOME set
    monkeypatch.setenv("APGR_HOME", str(global_apgr))
    resolved_no_home = resolve_outbox_root()
    assert resolved_no_home == def_outbox.resolve()


def test_v1_cli_dispatcher_reuses_policy_roster(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agent_phase.cli import dispatch_main
    from agent_phase.dispatch import Dispatcher
    import agent_phase.dispatch as dispatch_module

    req_file = tmp_path / "req.json"
    req_file.write_text(json.dumps({
        "schema": "agent-phase-request-v1",
        "phase_type": "implementation_testing",
        "execution_mode": "codex_only",
        "prompt": "V1 roster reuse test",
    }), encoding="utf-8")

    dispatched_rosters = []
    orig_init = Dispatcher.__init__

    def spy_init(self, *args, **kwargs):
        orig_init(self, *args, **kwargs)
        dispatched_rosters.append(self._roster)

    monkeypatch.setattr(Dispatcher, "__init__", spy_init)

    ret = dispatch_main(["--dry-run", str(req_file)])
    assert ret == 0
    assert len(dispatched_rosters) == 1
    # Verify Dispatcher received the pre-resolved roster directly from policy resolution
    assert dispatched_rosters[0] is not None



def test_catalog_declaration_does_not_gate_static_dispatch(tmp_path):
    project = tmp_path / "project"
    (project / ".apgr").mkdir(parents=True)
    (project / ".git").mkdir()
    config = project / ".apgr/config.toml"
    config.write_text('[dispatcher.routing]\nexecution_mode = "gemini_sub"\n[skills.overrides]\n"apgr:go-language-profile" = "project:missing"\n')
    (project / ".apgr/skills").write_text("unusable optional source")
    # No local source is required and no provider/worker is contacted by routing.
    assert load_config_file(config)["skills"]["overrides"]
    resolved = resolve_execution_mode(project_root=project, apgr_home=tmp_path / "absent")
    assert resolved.execution_mode == "gemini_sub"
