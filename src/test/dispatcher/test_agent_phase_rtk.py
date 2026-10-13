from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest import mock
from typing import Any
import pytest

_SRC_DIR = str(Path(__file__).resolve().parents[3] / "src")
_REPO_ROOT = Path(__file__).resolve().parents[3]
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from agentic_praxis_grimoire.config import (
    ConfigError,
    load_config,
    resolve_rtk_configuration,
)
from agentic_praxis_grimoire.rtk import (
    RTKResolution,
    run_rtk_probes,
    check_claude_hook_registration,
    inspect_canonical_skill,
    doctor_report,
    render_doctor_report,
)
from agentic_praxis_grimoire import cli

sys.path.insert(0, str(_REPO_ROOT / "libexec"))
import agent_source_guidance as asg
from agent_phase import config_routing


# ==============================================================================
# Cluster D1: Closed Configuration and Resolution Tests
# ==============================================================================

def test_rtk_config_defaults(tmp_path: Path) -> None:
    res = resolve_rtk_configuration(
        project_root=tmp_path / "proj",
        apgr_home=tmp_path / "home",
        environment={"CLAUDE_CONFIG_DIR": str(tmp_path / "claude")},
    )
    assert isinstance(res, RTKResolution)
    assert res.config.required is False
    assert res.config.enabled is False
    assert res.config.executable is None
    assert res.status in ("unavailable", "disabled")


def test_rtk_config_custom_file(tmp_path: Path) -> None:
    cfg = tmp_path / "config.toml"
    cfg.write_text("""
[integrations.rtk]
enabled = true
required = false
executable = "/usr/local/bin/rtk"

[integrations.rtk.providers]
claude = "hook"
codex = "instructions"
antigravity = "instructions"
""")
    loaded = load_config(cfg)
    assert "integrations" in loaded
    rtk = loaded["integrations"]["rtk"]
    assert rtk["enabled"] is True
    assert rtk["required"] is False
    assert rtk["executable"] == Path("/usr/local/bin/rtk")
    assert rtk["providers"]["claude"] == "hook"


def test_rtk_config_rejection_required_true(tmp_path: Path) -> None:
    cfg = tmp_path / "config.toml"
    cfg.write_text("""
[integrations.rtk]
required = true
""")
    with pytest.raises(ConfigError) as exc_info:
        load_config(cfg)
    assert "strict rtk required=true is deferred; required must be false" in str(exc_info.value)


def test_rtk_config_closed_keys(tmp_path: Path) -> None:
    cfg = tmp_path / "config.toml"
    cfg.write_text("""
[integrations.rtk]
unknown_field = "invalid"
""")
    with pytest.raises(ConfigError) as exc_info:
        load_config(cfg)
    assert "unsupported integrations.rtk configuration key: unknown_field" in str(exc_info.value)


def test_rtk_config_invalid_mode(tmp_path: Path) -> None:
    cfg = tmp_path / "config.toml"
    cfg.write_text("""
[integrations.rtk.providers]
claude = "invalid_mode"
""")
    with pytest.raises(ConfigError) as exc_info:
        load_config(cfg)
    assert "unsupported integrations.rtk.providers.claude mode" in str(exc_info.value)


def test_rtk_config_non_absolute_executable(tmp_path: Path) -> None:
    cfg = tmp_path / "config.toml"
    cfg.write_text("""
[integrations.rtk]
executable = "relative/path/rtk"
""")
    with pytest.raises(ConfigError) as exc_info:
        load_config(cfg)
    assert "must be an absolute path" in str(exc_info.value)


def test_config_routing_validation(tmp_path: Path) -> None:
    valid_data = {
        "integrations": {
            "rtk": {
                "required": False,
                "executable": "/usr/local/bin/rtk",
            }
        }
    }
    config_routing._validate_closed_table(valid_data, tmp_path / "cfg.toml")

    invalid_data = {
        "integrations": {
            "rtk": {
                "required": True,
            }
        }
    }
    with pytest.raises(config_routing.ConfigError) as exc_info:
        config_routing._validate_closed_table(invalid_data, tmp_path / "cfg.toml")
    assert "strict rtk required=true is deferred" in str(exc_info.value)


# ==============================================================================
# Cluster D2: Read-Only Doctor and Probe Tests
# ==============================================================================

def test_run_rtk_probes_mock_success() -> None:
    with mock.patch("agentic_praxis_grimoire.rtk._execute_bounded_probe") as mock_probe:
        mock_probe.side_effect = [
            (0, "rtk 0.43.0", "", False, []),
            (0, "hook active", "", False, []),
        ]

        res = run_rtk_probes("/mock/bin/rtk", minimum_version="0.43.0")
        assert res["all_ok"] is True
        assert res["version"]["ok"] is True
        assert res["hook_check"]["ok"] is True
        assert res["observed_version"] == "0.43.0"


def test_run_rtk_probes_version_failure() -> None:
    with mock.patch("agentic_praxis_grimoire.rtk._execute_bounded_probe") as mock_probe:
        mock_probe.return_value = (1, "", "command failed", False, [])

        res = run_rtk_probes("/mock/bin/rtk", minimum_version="0.43.0")
        assert res["all_ok"] is False
        assert res["version"]["ok"] is False


def test_inspect_claude_settings(tmp_path: Path) -> None:
    # Nonexistent settings
    res_missing = check_claude_hook_registration(
        project_root=tmp_path / "proj",
        global_home=tmp_path / "home",
        environment={"CLAUDE_CONFIG_DIR": str(tmp_path / "claude")},
    )
    assert res_missing["claude"]["registered"] is False

    # Active hook in claude settings
    settings_file = tmp_path / "home" / "claude" / "settings.json"
    settings_file.parent.mkdir(parents=True)
    settings_file.write_text(json.dumps({
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [{"command": "rtk hook claude"}]
                }
            ]
        }
    }))

    res_active = check_claude_hook_registration(
        project_root=None,
        global_home=tmp_path / "home",
        environment={"CLAUDE_CONFIG_DIR": str(tmp_path / "nonexistent")},
    )
    assert res_active["claude"]["registered"] is True


def test_inspect_canonical_skill() -> None:
    res = inspect_canonical_skill(_REPO_ROOT)
    assert res["name"] == "rtk-command-proxy"
    assert res["discoverable"] is True
    assert res["path"] is not None
    assert res["projection_path"] is not None


def test_doctor_report_json_and_text(tmp_path: Path) -> None:
    proj = tmp_path / "project"
    proj.mkdir()
    (proj / ".git").mkdir()
    report = doctor_report(
        project_root=proj,
        apgr_home=tmp_path / "home",
        environment={"CLAUDE_CONFIG_DIR": str(tmp_path / "claude")},
    )
    assert report["doctor_version"] == "apgr-rtk-doctor-v1"
    assert "status" in report
    assert "configuration_sources" in report
    assert "canonical_skill" in report

    # Render JSON
    rendered_json = render_doctor_report(report, json_output=True)
    parsed = json.loads(rendered_json)
    assert parsed["doctor_version"] == "apgr-rtk-doctor-v1"

    # Render Text
    rendered_text = render_doctor_report(report, json_output=False)
    assert "apgr rtk doctor:" in rendered_text
    assert f"status: {report['status']}" in rendered_text


def test_cli_rtk_doctor_dispatch(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    proj = tmp_path / "project"
    proj.mkdir()
    (proj / ".git").mkdir()
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "claude"))
    code = cli.main(["--apgr-home", str(tmp_path / "home"), "--project-root", str(proj), "integrations", "rtk", "doctor"])
    assert code in (0, 1)
    captured = capsys.readouterr()
    assert "apgr rtk doctor:" in captured.out

    code_json = cli.main(["--apgr-home", str(tmp_path / "home"), "--project-root", str(proj), "integrations", "rtk", "doctor", "--json"])
    assert code_json in (0, 1)
    captured_json = capsys.readouterr()
    parsed = json.loads(captured_json.out)
    assert parsed["doctor_version"] == "apgr-rtk-doctor-v1"


# ==============================================================================
# Cluster D3: Conditional Instruction Slices & No-RTK Golden Baselines
# ==============================================================================

def test_render_rtk_slice() -> None:
    for provider in ("codex", "claude", "antigravity"):
        slice_text = asg.render_rtk_slice(provider, mode="off", executable=None)
        assert slice_text == ""

    slice_claude = asg.render_rtk_slice("claude", mode="instructions", executable="/usr/local/bin/rtk")
    assert "/usr/local/bin/rtk" in slice_claude
    assert "$rtk-command-proxy" in slice_claude

    slice_gemini = asg.render_rtk_slice("antigravity", mode="instructions", executable="/usr/local/bin/rtk")
    assert "RTK shell-output efficiency" in slice_gemini

    slice_hook = asg.render_rtk_slice("claude", mode="hook", executable="rtk")
    assert "PreToolUse hook is registered and targeted" in slice_hook
    assert "without manual RTK prefixing" in slice_hook


def test_no_rtk_golden_baselines() -> None:
    codex_file = _REPO_ROOT / "codex" / "AGENTS.md"
    claude_file = _REPO_ROOT / "claude" / "CLAUDE.md"
    gemini_file = _REPO_ROOT / "antigravity" / "GEMINI.md"

    assert len(codex_file.read_bytes()) == 8527
    assert len(claude_file.read_bytes()) == 12326
    assert len(gemini_file.read_bytes()) == 3524

    assert "The Bash hook is `rtk hook claude`" in claude_file.read_text(encoding="utf-8")
    assert "RTK shell-output efficiency" not in codex_file.read_text(encoding="utf-8")
    assert "RTK shell-output efficiency" not in gemini_file.read_text(encoding="utf-8")


def test_source_guidance_backward_compatibility() -> None:
    guidance = asg.source_guidance(_REPO_ROOT, [], workers=False, instruction_file="codex/AGENTS.md", provider="codex")
    prompt, perms = guidance
    assert isinstance(prompt, str)
    assert isinstance(perms, list)

    assert hasattr(guidance, "source_digest")
    assert hasattr(guidance, "rendered_digest")
    assert len(guidance.source_digest) == 64
    assert len(guidance.rendered_digest) == 64
    assert guidance.source_digest == guidance.rendered_digest


# ==============================================================================
# Cluster D4: Canonical Skill and Discovery Ceiling
# ==============================================================================

def test_rtk_skill_properties() -> None:
    skill_file = _REPO_ROOT / "skills" / "rtk-command-proxy" / "SKILL.md"
    assert skill_file.is_file()
    content = skill_file.read_text(encoding="utf-8")

    lines = content.splitlines()
    desc_line = [l for l in lines if l.startswith("description: ")][0]
    description = desc_line.removeprefix("description: ")
    assert len(description.encode("utf-8")) == 268
    assert description == (
        "Use when Codex or Claude Code needs to run, choose, verify, troubleshoot, "
        "or explain shell commands through RTK, including ordinary command execution, "
        "raw-output fallbacks, RTK meta commands, installation checks, name collisions, "
        "or Claude PreToolUse rewrite behavior."
    )

    h2_sections = [l.removeprefix("## ").strip() for l in lines if l.startswith("## ")]
    expected_sections = [
        "Core principle",
        "Do not use",
        "Procedure",
        "Project-owned parameters",
        "Evidence and completion",
        "Stop or escalate",
        "Common mistakes",
    ]
    assert h2_sections == expected_sections


# ==============================================================================
# Cluster D5: Bounded Probes, Hook Targeting, Transport Delivery, & Isolation
# ==============================================================================

def test_run_rtk_probes_oversize_output() -> None:
    with mock.patch("agentic_praxis_grimoire.rtk._execute_bounded_probe") as mock_probe:
        oversize_str = "x" * 65536
        mock_probe.return_value = (
            0,
            f"rtk 0.43.0 {oversize_str[:60000]}",
            "",
            True,
            ["rtk --version probe output exceeded 65536 bytes and was truncated"],
        )

        res = run_rtk_probes("/mock/bin/rtk", minimum_version="0.43.0")
        assert len(res["version"]["stdout"]) <= 64 * 1024
        assert any("exceeded 65536 bytes and was truncated" in d for d in res["diagnostics"])


def test_run_rtk_probes_timeout() -> None:
    with mock.patch("agentic_praxis_grimoire.rtk._execute_bounded_probe") as mock_probe:
        mock_probe.return_value = (
            None,
            "",
            "",
            False,
            ["rtk --version probe timed out waiting for exit"],
        )

        res = run_rtk_probes("/mock/bin/rtk", minimum_version="0.43.0")
        assert res["all_ok"] is False
        assert any("timed out" in d for d in res["diagnostics"])


def test_run_rtk_probes_injected_executables(tmp_path: Path) -> None:
    # 1. Non-executable file
    non_exec = tmp_path / "non_exec_rtk"
    non_exec.write_text("#!/bin/sh\necho rtk 0.43.0\n")
    non_exec.chmod(0o644)
    (tmp_path / ".apgr").mkdir(exist_ok=True)
    cfg_file = tmp_path / ".apgr" / "config.toml"
    cfg_file.write_text(f"""
[integrations.rtk]
enabled = true
executable = "{non_exec}"
""")
    res_non_exec = resolve_rtk_configuration(
        project_root=tmp_path,
        apgr_home=tmp_path / "home",
        environment={"CLAUDE_CONFIG_DIR": str(tmp_path / "claude")},
    )
    assert res_non_exec.status == "unavailable"
    assert any("not executable" in d for d in res_non_exec.diagnostics)

    # 2. Executable returning old version
    old_exec = tmp_path / "old_rtk.sh"
    old_exec.write_text("#!/bin/sh\nif [ \"$1\" = \"--version\" ]; then echo \"rtk 0.40.0\"; else exit 0; fi\n")
    old_exec.chmod(0o755)
    probe_old = run_rtk_probes(str(old_exec), minimum_version="0.43.0")
    assert probe_old["all_ok"] is False
    assert probe_old["version"]["ok"] is False
    assert any("older than minimum 0.43.0" in d for d in probe_old["diagnostics"])

    # 3. Symlink chain (Nix-like)
    real_exec = tmp_path / "real_rtk.sh"
    real_exec.write_text("#!/bin/sh\nif [ \"$1\" = \"--version\" ]; then echo \"rtk 0.43.0\"; else exit 0; fi\n")
    real_exec.chmod(0o755)
    link1 = tmp_path / "link1_rtk"
    link2 = tmp_path / "link2_rtk"
    link1.symlink_to(real_exec)
    link2.symlink_to(link1)

    cfg_symlink = tmp_path / "cfg_symlink.toml"
    cfg_symlink.write_text(f"""
[integrations.rtk]
enabled = true
executable = "{link2}"
""")
    # Overwrite project config
    (tmp_path / ".apgr").mkdir(exist_ok=True)
    (tmp_path / ".apgr" / "config.toml").write_text(f"""
[integrations.rtk]
enabled = true
executable = "{link2}"
""")
    res_sym = resolve_rtk_configuration(
        project_root=tmp_path,
        apgr_home=tmp_path / "home",
        environment={"CLAUDE_CONFIG_DIR": str(tmp_path / "claude")},
        run_probes=True,
    )
    assert res_sym.status == "available"
    assert res_sym.resolved_executable == str(real_exec.resolve())
    assert res_sym.configured_executable == str(link2)

    # 4. Path with spaces
    space_dir = tmp_path / "dir with spaces"
    space_dir.mkdir()
    space_exec = space_dir / "rtk.sh"
    space_exec.write_text("#!/bin/sh\nif [ \"$1\" = \"--version\" ]; then echo \"rtk 0.43.0\"; else exit 0; fi\n")
    space_exec.chmod(0o755)
    (tmp_path / ".apgr" / "config.toml").write_text(f"""
[integrations.rtk]
enabled = true
executable = "{space_exec}"
""")
    res_space = resolve_rtk_configuration(
        project_root=tmp_path,
        apgr_home=tmp_path / "home",
        environment={"CLAUDE_CONFIG_DIR": str(tmp_path / "claude")},
        run_probes=True,
    )
    assert res_space.status == "available"
    assert res_space.resolved_executable == str(space_exec.resolve())


def test_claude_hook_targeting_bare_and_matched(tmp_path: Path) -> None:
    claude_dir = tmp_path / "claude"
    claude_dir.mkdir(parents=True)
    settings_file = claude_dir / "settings.json"

    # Case A: Bare rtk hook
    settings_file.write_text(json.dumps({
        "hooks": {
            "PreToolUse": [{"matcher": "Bash", "hooks": [{"command": "rtk hook claude"}]}]
        }
    }))
    res_bare = check_claude_hook_registration(
        project_root=None,
        global_home=tmp_path / "home",
        environment={"CLAUDE_CONFIG_DIR": str(claude_dir)},
        configured_executable="/custom/bin/rtk",
    )
    assert res_bare["claude"]["registered"] is True
    assert res_bare["claude"]["targeting"] == "bare_rtk_unresolved"

    # Case B: Matched executable
    settings_file.write_text(json.dumps({
        "hooks": {
            "PreToolUse": [{"matcher": "Bash", "hooks": [{"command": "/custom/bin/rtk hook claude"}]}]
        }
    }))
    res_matched = check_claude_hook_registration(
        project_root=None,
        global_home=tmp_path / "home",
        environment={"CLAUDE_CONFIG_DIR": str(claude_dir)},
        configured_executable="/custom/bin/rtk",
        resolved_executable="/custom/bin/rtk",
    )
    assert res_matched["claude"]["registered"] is True
    assert res_matched["claude"]["targeting"] == "matches_configured_executable"

    # Case C: Mismatched executable
    settings_file.write_text(json.dumps({
        "hooks": {
            "PreToolUse": [{"matcher": "Bash", "hooks": [{"command": "/other/bin/rtk hook claude"}]}]
        }
    }))
    res_mismatch = check_claude_hook_registration(
        project_root=None,
        global_home=tmp_path / "home",
        environment={"CLAUDE_CONFIG_DIR": str(claude_dir)},
        configured_executable="/custom/bin/rtk",
        resolved_executable="/custom/bin/rtk",
    )
    assert res_mismatch["claude"]["registered"] is True
    assert res_mismatch["claude"]["targeting"] == "mismatched_executable"


def test_claude_hook_launch_arguments(tmp_path: Path) -> None:
    custom_settings = tmp_path / "launch_settings.json"
    custom_settings.write_text(json.dumps({
        "hooks": {
            "PreToolUse": [{"matcher": "Bash", "hooks": [{"command": "rtk hook claude"}]}]
        }
    }))

    res = check_claude_hook_registration(
        project_root=None,
        global_home=tmp_path / "home",
        environment={"CLAUDE_CONFIG_DIR": str(tmp_path / "empty_claude")},
        launch_arguments=["--settings", str(custom_settings)],
    )
    assert res["claude"]["registered"] is True
    assert res["claude"]["source_file"] == str(custom_settings)


def test_transport_slice_delivery_and_exact_advertised_digest(tmp_path: Path) -> None:
    # 1. RTK Disabled / Off: advertised digest == source digest == rendered digest
    guidance_off = asg.source_guidance(
        _REPO_ROOT,
        [],
        workers=False,
        instruction_file="codex/AGENTS.md",
        provider="codex",
        rtk=None,
    )
    prompt_off = guidance_off[0]
    assert guidance_off.source_digest == guidance_off.rendered_digest
    assert f"sha256={guidance_off.rendered_digest}" in prompt_off
    assert "RTK shell-output efficiency" not in prompt_off

    # 2. RTK Enabled with instructions mode: advertised digest == rendered digest != source digest
    mock_rtk = mock.MagicMock()
    mock_rtk.configured_executable = "/usr/local/bin/rtk"
    mock_rtk.resolved_executable = "/usr/local/bin/rtk"
    mock_rtk.providers = {"codex": {"effective_mode": "instructions"}}

    guidance_on = asg.source_guidance(
        _REPO_ROOT,
        [],
        workers=False,
        instruction_file="codex/AGENTS.md",
        provider="codex",
        rtk=mock_rtk,
    )
    prompt_on = guidance_on[0]
    assert guidance_on.rendered_digest != guidance_on.source_digest
    assert f"sha256={guidance_on.rendered_digest}" in prompt_on
    assert f"sha256={guidance_on.source_digest}" not in prompt_on
    assert "RTK shell-output efficiency" in prompt_on
    assert "/usr/local/bin/rtk" in prompt_on


def test_claude_and_codex_transport_wiring(tmp_path: Path) -> None:
    # Test Codex guidance overrides with RTK
    mock_rtk = mock.MagicMock()
    mock_rtk.configured_executable = "/usr/local/bin/rtk"
    mock_rtk.resolved_executable = "/usr/local/bin/rtk"
    mock_rtk.providers = {"codex": {"effective_mode": "instructions"}}

    overrides = asg.codex_guidance_overrides(_REPO_ROOT, workers=False, rtk=mock_rtk)
    assert len(overrides) >= 1
    dev_instr = overrides[-1]
    assert "developer_instructions=" in dev_instr
    assert "RTK shell-output efficiency" in dev_instr
    assert "/usr/local/bin/rtk" in dev_instr

    # Test Antigravity source guidance with RTK
    mock_rtk.providers = {"antigravity": {"effective_mode": "instructions"}}
    ag_guidance = asg.source_guidance(
        _REPO_ROOT / "antigravity",
        [],
        workers=True,
        instruction_file="GEMINI.md",
        rtk=mock_rtk,
        provider="antigravity",
    )
    assert "RTK shell-output efficiency" in ag_guidance[0]
    assert f"sha256={ag_guidance.rendered_digest}" in ag_guidance[0]


def test_doctor_report_non_mutation(tmp_path: Path) -> None:
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / ".apgr").mkdir()
    cfg = proj / ".apgr" / "config.toml"
    cfg.write_text("[integrations.rtk]\nenabled = false\n")

    home = tmp_path / "home"
    home.mkdir()
    claude_dir = tmp_path / "claude"
    claude_dir.mkdir()

    # Capture state before
    def tree_state(root: Path) -> dict[str, str]:
        state = {}
        for p in root.rglob("*"):
            if p.is_file():
                state[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
        return state

    before = tree_state(tmp_path)
    doctor_report(
        project_root=proj,
        apgr_home=home,
        environment={"CLAUDE_CONFIG_DIR": str(claude_dir)},
    )
    after = tree_state(tmp_path)
    assert before == after


def test_selected_home_vs_ambient_isolation(tmp_path: Path) -> None:
    mock_bin = tmp_path / "bin" / "rtk"
    mock_bin.parent.mkdir(parents=True, exist_ok=True)
    mock_bin.write_text("#!/bin/sh\necho 'rtk 0.43.0'\n", encoding="utf-8")
    mock_bin.chmod(0o755)

    home_a = tmp_path / "home_a"
    home_a.mkdir()
    (home_a / "config.toml").write_text(f"""
[integrations.rtk]
enabled = true
executable = "{mock_bin}"
""")
    home_b = tmp_path / "home_b"
    home_b.mkdir()
    (home_b / "config.toml").write_text("""
[integrations.rtk]
enabled = false
""")
    res_a = resolve_rtk_configuration(
        project_root=tmp_path / "nonexistent",
        apgr_home=home_a,
        environment={"CLAUDE_CONFIG_DIR": str(tmp_path / "c_a")},
    )
    assert res_a.config.enabled is True
    assert res_a.status == "available"

    res_b = resolve_rtk_configuration(
        project_root=tmp_path / "nonexistent",
        apgr_home=home_b,
        environment={"CLAUDE_CONFIG_DIR": str(tmp_path / "c_b")},
    )
    assert res_b.config.enabled is False
    assert res_b.status == "disabled"
    assert res_b.hook_registration["claude"]["targeting"] == "uninspected"
    assert not (tmp_path / "c_b").exists()


# ==============================================================================
# Cluster D6: Ordinary Path Semantics & Tilde Compatibility (M1 / F4)
# ==============================================================================

def test_config_tilde_outbox_expansion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agentic_praxis_grimoire import config as canonical_config
    from agent_phase import config_routing as native_config

    home = tmp_path / "user_home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))

    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text('outbox_root = "~/Documents/agent/outbox"\n', encoding="utf-8")

    # 1. Canonical config loader (expands ~ into Path object)
    loaded_canonical = canonical_config.load_config(cfg_file)
    assert isinstance(loaded_canonical["outbox_root"], Path)
    assert loaded_canonical["outbox_root"] == (home / "Documents" / "agent" / "outbox").resolve()

    # Canonical config outbox resolver with home expansion
    resolved_canonical = canonical_config.resolve_outbox_root(
        apgr_home=tmp_path / "home",
        home=home,
        project_root=tmp_path / "proj",
        explicit="~/Documents/agent/outbox",
    )
    assert resolved_canonical == (home / "Documents" / "agent" / "outbox").resolve()

    # 2. Native config loader and resolver
    loaded_native = native_config.load_config_file(cfg_file)
    assert loaded_native["outbox_root"] == "~/Documents/agent/outbox"

    resolved_native = native_config.resolve_outbox_root(
        explicit="~/Documents/agent/outbox",
        project_root=tmp_path / "proj",
        apgr_home=tmp_path / "home",
        environment={"HOME": str(home)},
        home=home,
    )
    assert resolved_native == (home / "Documents" / "agent" / "outbox").resolve()

    # 3. Disabled RTK preserves tilde outbox
    cfg_with_rtk_off = tmp_path / "rtk_off.toml"
    cfg_with_rtk_off.write_text("""
outbox_root = "~/Documents/agent/outbox"
[integrations.rtk]
enabled = false
""", encoding="utf-8")
    loaded_rtk_off = canonical_config.load_config(cfg_with_rtk_off)
    assert loaded_rtk_off["outbox_root"] == Path("~/Documents/agent/outbox").expanduser().resolve()

    # 4. Enabled RTK with valid executable preserves tilde outbox
    cfg_with_rtk_on = tmp_path / "rtk_on.toml"
    cfg_with_rtk_on.write_text("""
outbox_root = "~/Documents/agent/outbox"
[integrations.rtk]
enabled = true
executable = "/usr/local/bin/rtk"
""", encoding="utf-8")
    loaded_rtk_on = canonical_config.load_config(cfg_with_rtk_on)
    assert loaded_rtk_on["outbox_root"] == Path("~/Documents/agent/outbox").expanduser().resolve()


def test_config_rtk_executable_strict_rejection(tmp_path: Path) -> None:
    from agentic_praxis_grimoire import config as canonical_config
    from agent_phase import config_routing as native_config

    # Rejection of tilde in executable
    tilde_cfg = tmp_path / "tilde_exe.toml"
    tilde_cfg.write_text("""
[integrations.rtk]
enabled = true
executable = "~/bin/rtk"
""", encoding="utf-8")
    with pytest.raises(canonical_config.ConfigError, match=r"~|tilde"):
        canonical_config.load_config(tilde_cfg)

    with pytest.raises(native_config.ConfigError, match=r"~|tilde"):
        native_config.load_config_file(tilde_cfg)

    # Rejection of dollar in executable
    dollar_cfg = tmp_path / "dollar_exe.toml"
    dollar_cfg.write_text("""
[integrations.rtk]
enabled = true
executable = "$HOME/bin/rtk"
""", encoding="utf-8")
    with pytest.raises(canonical_config.ConfigError, match=r"variable|\$"):
        canonical_config.load_config(dollar_cfg)

    with pytest.raises(native_config.ConfigError, match=r"variable|\$"):
        native_config.load_config_file(dollar_cfg)

    # Rejection of relative path in outbox
    rel_cfg = tmp_path / "rel_outbox.toml"
    rel_cfg.write_text('outbox_root = "relative/outbox"\n', encoding="utf-8")
    with pytest.raises(canonical_config.ConfigError, match="absolute"):
        canonical_config.load_config(rel_cfg)


# ==============================================================================
# Cluster D7: Provider Seams & Instrumented Transport Verification (M2 / F5)
# ==============================================================================

def test_claude_launcher_isolated_settings_and_argv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import claude_vc_profile as launcher
    import shlex

    mock_bin = tmp_path / "bin" / "rtk"
    mock_bin.parent.mkdir(parents=True, exist_ok=True)
    mock_bin.write_text("#!/bin/sh\necho 'rtk 0.43.0'\n", encoding="utf-8")
    mock_bin.chmod(0o755)

    home = tmp_path / "user_home"
    home.mkdir(mode=0o700)
    claude_home = home / "claude"
    claude_home.mkdir()
    settings_file = claude_home / "settings.json"
    settings_file.write_text(json.dumps({
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [{"type": "command", "command": f"{mock_bin} hook claude"}]
                }
            ]
        }
    }), encoding="utf-8")

    apgr_home = tmp_path / "apgr_home"
    apgr_home.mkdir(mode=0o700)
    (apgr_home / "claude").mkdir()
    (apgr_home / "claude" / "settings.json").write_text("{}", encoding="utf-8")
    (apgr_home / "config.toml").write_text(f"""
[integrations.rtk]
enabled = true
executable = "{mock_bin}"
providers.claude = "instructions"
""", encoding="utf-8")

    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".git").mkdir()
    (project_root / ".apgr").mkdir()
    (project_root / ".apgr" / "config.toml").write_text(f"""
[integrations.rtk]
enabled = true
executable = "{mock_bin}"
providers.claude = "instructions"
""", encoding="utf-8")

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("APGR_HOME", str(apgr_home))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(claude_home))
    monkeypatch.setenv("AGENT_CENTRAL_MANAGED_PARENT", "1")
    monkeypatch.setattr(launcher.shutil, "which", lambda name: "/fake/claude")
    import claude_model_catalog as catalog
    monkeypatch.setattr(catalog, "probe_claude_version", lambda executable: ("2.1.999", "available"))
    monkeypatch.delenv(launcher.WORKER_FACADE_MARKER, raising=False)

    execve_calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(launcher.os, "execve", lambda exe, argv, env: execve_calls.append((exe, argv, env)))

    claude_root = _REPO_ROOT / "claude"
    launcher.launch(claude_root, "normal-sysadmin-plan-review", ["--print", "hello task"])

    assert len(execve_calls) == 1
    exe, argv, env = execve_calls[0]
    assert exe == "/fake/claude"
    assert isinstance(argv, list)

    # Verify isolated settings arguments in argv
    assert "--settings" in argv
    assert "--setting-sources" in argv
    idx_sources = argv.index("--setting-sources")
    assert argv[idx_sources + 1] == ""

    # Verify appended system prompt contains RTK instruction slice
    assert "--append-system-prompt" in argv
    idx_prompt = argv.index("--append-system-prompt")
    prompt_text = argv[idx_prompt + 1]
    assert "RTK shell-output efficiency" in prompt_text
    assert shlex.quote(str(mock_bin)) in prompt_text


def test_claude_launcher_unavailability_diagnostic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    import claude_vc_profile as launcher
    import claude_model_catalog as catalog

    home = tmp_path / "user_home"
    home.mkdir(mode=0o700)
    apgr_home = tmp_path / "apgr_home"
    apgr_home.mkdir(mode=0o700)
    (apgr_home / "claude").mkdir()
    (apgr_home / "claude" / "settings.json").write_text("{}", encoding="utf-8")

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("APGR_HOME", str(apgr_home))
    monkeypatch.setenv("AGENT_CENTRAL_MANAGED_PARENT", "1")
    monkeypatch.setattr(launcher.shutil, "which", lambda name: "/fake/claude")
    monkeypatch.setattr(catalog, "probe_claude_version", lambda executable: ("2.1.999", "available"))
    monkeypatch.delenv(launcher.WORKER_FACADE_MARKER, raising=False)

    # Force an exception during rtk resolution
    def _raise(*args: object, **kwargs: object) -> object:
        raise RuntimeError("simulated resolver failure")

    monkeypatch.setattr("agentic_praxis_grimoire.rtk.resolve_rtk_configuration", _raise)

    execve_calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(launcher.os, "execve", lambda exe, argv, env: execve_calls.append((exe, argv, env)))

    claude_root = _REPO_ROOT / "claude"
    launcher.launch(claude_root, "normal-sysadmin-plan-review", ["--print", "task text"])

    assert len(execve_calls) == 1
    # Check that visible unavailability diagnostic was printed to stderr
    captured = capsys.readouterr()
    assert "claude-profile: rtk resolution unavailable: simulated resolver failure" in captured.err


def test_dispatcher_ensure_rtk_resolution_seam(tmp_path: Path) -> None:
    from agent_phase.dispatch import Dispatcher

    worktree = tmp_path / "worktree"
    worktree.mkdir()
    (worktree / ".git").mkdir()
    apgr_home = tmp_path / "apgr_home"
    apgr_home.mkdir()

    disp = Dispatcher(root=_REPO_ROOT, cwd=worktree, apgr_home=apgr_home)
    assert not disp._rtk_resolved

    sys_path_before = list(sys.path)
    res = disp._ensure_rtk_resolution()
    assert disp._rtk_resolved
    assert res is not None
    assert hasattr(res, "status")
    assert sys.path == sys_path_before


def test_v2_dispatch_and_turns_rtk_guidance_helper(tmp_path: Path) -> None:
    import agent_source_guidance as asg
    from types import SimpleNamespace

    mock_res = SimpleNamespace(
        status="available",
        configured_executable="/custom/bin/rtk",
        resolved_executable="/custom/bin/rtk",
        providers={
            "claude": {"effective_mode": "instructions"},
            "codex": {"effective_mode": "instructions"},
            "antigravity": {"effective_mode": "instructions"},
        },
    )

    claude_guidance, _ = asg.source_guidance(_REPO_ROOT / "claude", ["--print", "prompt"], workers=False, rtk=mock_res, provider="claude")
    assert "RTK shell-output efficiency" in claude_guidance
    assert "/custom/bin/rtk" in claude_guidance

    codex_overrides = asg.codex_guidance_overrides(_REPO_ROOT, workers=False, rtk=mock_res)
    assert any("RTK shell-output efficiency" in o for o in codex_overrides)


def test_materialized_generation_rtk_isolated(tmp_path: Path) -> None:
    from controller_generation_store import canonical_root_sha256, is_allowlisted, materialize
    import shutil

    fixture_repo = tmp_path / "fixture_repo"
    fixture_repo.mkdir()
    for rel in (
        "src/agentic_praxis_grimoire/__init__.py",
        "src/agentic_praxis_grimoire/paths.py",
        "src/agentic_praxis_grimoire/config.py",
        "src/agentic_praxis_grimoire/rtk.py",
        "src/agentic_praxis_grimoire/version.py",
        "src/agentic_praxis_grimoire/VERSION",
        "README.md",
    ):
        src_file = _REPO_ROOT / rel
        if src_file.is_file():
            dst_file = fixture_repo / rel
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)

    git_env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Fixture",
        "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
        "GIT_COMMITTER_NAME": "Fixture",
        "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
    }
    subprocess.run(["git", "-C", str(fixture_repo), "init", "-q"], check=True, env=git_env)
    subprocess.run(["git", "-C", str(fixture_repo), "add", "-A"], check=True, env=git_env)
    subprocess.run(["git", "-C", str(fixture_repo), "commit", "-qm", "fixture commit"], check=True, env=git_env)

    store_dir = tmp_path / "store" / canonical_root_sha256(fixture_repo)
    store_dir.parent.mkdir(parents=True, exist_ok=True)

    record = materialize(fixture_repo, store_dir)
    gen_root = Path(record["generation_root"])

    rtk_file = gen_root / "src/agentic_praxis_grimoire/rtk.py"
    config_file = gen_root / "src/agentic_praxis_grimoire/config.py"
    init_file = gen_root / "src/agentic_praxis_grimoire/__init__.py"
    paths_file = gen_root / "src/agentic_praxis_grimoire/paths.py"
    version_file = gen_root / "src/agentic_praxis_grimoire/version.py"
    version_res = gen_root / "src/agentic_praxis_grimoire/VERSION"

    assert rtk_file.is_file()
    assert config_file.is_file()
    assert init_file.is_file()
    assert paths_file.is_file()
    assert version_file.is_file()
    assert version_res.is_file()

    code = """
import sys
from pathlib import Path
import agentic_praxis_grimoire
import agentic_praxis_grimoire.version
assert agentic_praxis_grimoire.VERSION == "0.13.0"
assert agentic_praxis_grimoire.__version__ == "0.13.0"
assert agentic_praxis_grimoire.version.version() == "0.13.0"
from agentic_praxis_grimoire.rtk import resolve_rtk_configuration
res = resolve_rtk_configuration(project_root=Path.cwd(), run_probes=False)
assert res is not None
print("RTK_RESOLVED_OK")
"""
    env = {
        "PATH": os.environ["PATH"],
        "PYTHONPATH": str(gen_root / "src"),
        "HOME": str(tmp_path / "home"),
    }
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"STDOUT: {proc.stdout}\nSTDERR: {proc.stderr}"
    assert "RTK_RESOLVED_OK" in proc.stdout


# ==============================================================================
# Cluster D8: Boundary2 Corrections (R1, R2, R3)
# ==============================================================================

@pytest.mark.parametrize("resource", [None, "not-a-version\n"])
def test_materialized_generation_rejects_invalid_version(tmp_path: Path, resource: str | None) -> None:
    from controller_generation_store import canonical_root_sha256, materialize
    import shutil

    fixture = tmp_path / "source"
    package = fixture / "src/agentic_praxis_grimoire"
    package.mkdir(parents=True)
    for name in ("__init__.py", "version.py"):
        shutil.copy2(_REPO_ROOT / "src/agentic_praxis_grimoire" / name, package / name)
    if resource is not None:
        (package / "VERSION").write_text(resource)
    env = {**os.environ, "GIT_AUTHOR_NAME": "Fixture", "GIT_COMMITTER_NAME": "Fixture",
           "GIT_AUTHOR_EMAIL": "fixture@example.invalid", "GIT_COMMITTER_EMAIL": "fixture@example.invalid"}
    for args in (["init", "-q"], ["add", "src"], ["commit", "-qm", "fixture"]):
        subprocess.run(["git", "-C", str(fixture), *args], env=env, check=True)
    store = tmp_path / "store" / canonical_root_sha256(fixture)
    store.parent.mkdir()
    generation = Path(materialize(fixture, store)["generation_root"])
    proc = subprocess.run(
        [sys.executable, "-c", "import agentic_praxis_grimoire"], cwd=tmp_path,
        env={"PATH": os.environ["PATH"], "HOME": str(tmp_path / "home"),
             "PYTHONPATH": str(generation / "src")}, capture_output=True, text=True,
    )
    assert proc.returncode != 0
    assert ("FileNotFoundError" if resource is None else "not a release version") in proc.stderr


def test_version_authority_missing_and_malformed() -> None:
    import agentic_praxis_grimoire.version as ver_module

    # Standard reading returns current release version
    assert ver_module._read_version() == "0.13.0"

    # Malformed versions rejection
    for malformed in ("0.13", "0.13.0-dev", "v0.12.0", "1.2.3.4", "", "   ", "beta"):
        with mock.patch("importlib.resources.files") as mock_files:
            mock_res = mock.MagicMock()
            mock_res.joinpath.return_value.read_text.return_value = malformed
            mock_files.return_value = mock_res
            with pytest.raises(RuntimeError, match="not a release version"):
                ver_module._read_version()

    # Missing VERSION rejection
    with mock.patch("importlib.resources.files") as mock_files:
        mock_res = mock.MagicMock()
        mock_res.joinpath.return_value.read_text.side_effect = FileNotFoundError("VERSION")
        mock_files.return_value = mock_res
        with pytest.raises(FileNotFoundError):
            ver_module._read_version()


def test_claude_hook_matcher_patterns(tmp_path: Path) -> None:
    from agentic_praxis_grimoire.rtk import _matcher_matches_bash, check_claude_hook_registration

    # 1. Exact string matches
    assert _matcher_matches_bash("Bash") is True
    assert _matcher_matches_bash("^Bash$") is True
    assert _matcher_matches_bash("Bash|Read") is True
    assert _matcher_matches_bash("Read|Bash") is True
    assert _matcher_matches_bash("Bash|Edit|Write") is True

    # 2. Non-matching tools
    assert _matcher_matches_bash("Read") is False
    assert _matcher_matches_bash("Write") is False
    assert _matcher_matches_bash("Glob|Grep") is False

    # 3. Invalid/unsupported regex pattern handling
    assert _matcher_matches_bash("[unclosed(") is None

    # 4. Diagnostic emission for unsupported matcher in hook check
    claude_dir = tmp_path / "claude"
    claude_dir.mkdir()
    settings_file = claude_dir / "settings.json"
    settings_file.write_text(json.dumps({
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "[unclosed(",
                    "hooks": [{"command": "rtk hook claude"}]
                }
            ]
        }
    }))
    res = check_claude_hook_registration(
        project_root=None,
        global_home=tmp_path / "home",
        environment={"CLAUDE_CONFIG_DIR": str(claude_dir)},
    )
    assert res["claude"]["registered"] is False
    assert any("is unknown or unsupported" in d for d in res["claude"]["diagnostics"])


def test_rtk_hook_fallback_to_off_and_double_wrap_prevention(tmp_path: Path) -> None:
    mock_bin = tmp_path / "bin" / "rtk"
    mock_bin.parent.mkdir(parents=True, exist_ok=True)
    mock_bin.write_text("#!/bin/sh\necho 'rtk 0.43.0'\n", encoding="utf-8")
    mock_bin.chmod(0o755)

    home = tmp_path / "user_home"
    home.mkdir()
    claude_dir = home / "claude"
    claude_dir.mkdir()

    # Case 1: Claude configured with hook mode, but no hook registered in settings -> falls back to off (never instructions)
    proj1 = tmp_path / "proj1"
    proj1.mkdir()
    (proj1 / ".apgr").mkdir()
    (proj1 / ".apgr" / "config.toml").write_text(f"""
[integrations.rtk]
enabled = true
executable = "{mock_bin}"
providers.claude = "hook"
""")
    res1 = resolve_rtk_configuration(
        project_root=proj1,
        apgr_home=home,
        environment={"CLAUDE_CONFIG_DIR": str(claude_dir)},
    )
    assert res1.providers["claude"]["effective_mode"] == "off"
    assert any("hook fallback to off" in d for d in res1.diagnostics)

    # Case 2: Codex configured with hook mode falls back to off
    proj2 = tmp_path / "proj2"
    proj2.mkdir()
    (proj2 / ".apgr").mkdir()
    (proj2 / ".apgr" / "config.toml").write_text(f"""
[integrations.rtk]
enabled = true
executable = "{mock_bin}"
providers.codex = "hook"
""")
    res2 = resolve_rtk_configuration(
        project_root=proj2,
        apgr_home=home,
        environment={"CLAUDE_CONFIG_DIR": str(claude_dir)},
    )
    assert res2.providers["codex"]["effective_mode"] == "off"
    assert any("codex provider does not support hook mode" in d for d in res2.diagnostics)

    # Case 3: Antigravity configured with hook mode falls back to off
    proj3 = tmp_path / "proj3"
    proj3.mkdir()
    (proj3 / ".apgr").mkdir()
    (proj3 / ".apgr" / "config.toml").write_text(f"""
[integrations.rtk]
enabled = true
executable = "{mock_bin}"
providers.antigravity = "hook"
""")
    res3 = resolve_rtk_configuration(
        project_root=proj3,
        apgr_home=home,
        environment={"CLAUDE_CONFIG_DIR": str(claude_dir)},
    )
    assert res3.providers["antigravity"]["effective_mode"] == "off"
    assert any("antigravity provider does not support hook mode" in d for d in res3.diagnostics)

    # Case 4: Claude configured with instructions mode, but matching hook is active -> switch to hook to avoid double wrap
    (claude_dir / "settings.json").write_text(json.dumps({
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [{"command": f"{mock_bin} hook claude"}]
                }
            ]
        }
    }))
    proj4 = tmp_path / "proj4"
    proj4.mkdir()
    (proj4 / ".apgr").mkdir()
    (proj4 / ".apgr" / "config.toml").write_text(f"""
[integrations.rtk]
enabled = true
executable = "{mock_bin}"
providers.claude = "instructions"
""")
    res4 = resolve_rtk_configuration(
        project_root=proj4,
        apgr_home=home,
        environment={"CLAUDE_CONFIG_DIR": str(claude_dir)},
    )
    assert res4.providers["claude"]["effective_mode"] == "hook"
    assert any("switching claude to hook mode to prevent double-wrapping" in d for d in res4.diagnostics)


def test_target_vs_controller_contradictory_config_isolation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agent_phase.dispatch import Dispatcher
    import claude_vc_profile as launcher

    mock_bin_target = tmp_path / "bin" / "rtk_target"
    mock_bin_target.parent.mkdir(parents=True, exist_ok=True)
    mock_bin_target.write_text("#!/bin/sh\necho 'rtk 0.43.0'\n", encoding="utf-8")
    mock_bin_target.chmod(0o755)

    controller_root = tmp_path / "controller"
    controller_root.mkdir()
    (controller_root / ".git").mkdir()
    (controller_root / ".apgr").mkdir()
    (controller_root / ".apgr" / "config.toml").write_text("""
[integrations.rtk]
enabled = false
""", encoding="utf-8")

    sibling_root = tmp_path / "target_sibling"
    sibling_root.mkdir()
    (sibling_root / ".git").mkdir()
    (sibling_root / ".apgr").mkdir()
    (sibling_root / ".apgr" / "config.toml").write_text("""
[integrations.rtk]
enabled = false
""", encoding="utf-8")

    target_root = tmp_path / "target"
    target_root.mkdir()
    (target_root / ".git").mkdir()
    (target_root / ".apgr").mkdir()
    (target_root / ".apgr" / "config.toml").write_text(f"""
[integrations.rtk]
enabled = true
executable = "{mock_bin_target}"
providers.claude = "instructions"
providers.codex = "instructions"
""", encoding="utf-8")

    apgr_home = tmp_path / "home"
    apgr_home.mkdir()
    (apgr_home / "claude").mkdir()
    (apgr_home / "claude" / "settings.json").write_text("{}", encoding="utf-8")

    # 1. Direct resolution on target_root: target's enabled setting wins
    res_direct = resolve_rtk_configuration(
        project_root=target_root,
        apgr_home=apgr_home,
        run_probes=False,
    )
    assert res_direct.config.enabled is True
    assert res_direct.configured_executable == str(mock_bin_target)

    # 2. V1 Dispatcher with controller as root and target as cwd (worktree)
    disp = Dispatcher(root=controller_root, cwd=target_root, apgr_home=apgr_home)
    res_disp = disp._ensure_rtk_resolution()
    assert res_disp.config.enabled is True
    assert res_disp.configured_executable == str(mock_bin_target)

    # 3. Claude profile launcher using dedicated RTK target authority
    user_home = tmp_path / "user_home"
    user_home.mkdir()
    monkeypatch.setenv("HOME", str(user_home))
    monkeypatch.setenv("APGR_TARGET_PROJECT_ROOT", str(target_root))
    monkeypatch.setenv("APGR_HOME", str(apgr_home))
    monkeypatch.setenv("AGENT_CENTRAL_MANAGED_PARENT", "1")
    monkeypatch.setattr(launcher.shutil, "which", lambda name: "/fake/claude")
    import claude_model_catalog as catalog
    monkeypatch.setattr(catalog, "probe_claude_version", lambda executable: ("2.1.999", "available"))
    monkeypatch.delenv(launcher.WORKER_FACADE_MARKER, raising=False)

    execve_calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(launcher.os, "execve", lambda exe, argv, env: execve_calls.append((exe, argv, env)))
    launcher.launch(_REPO_ROOT / "claude", "normal-sysadmin-plan-review", ["--print", "hello"])
    assert len(execve_calls) == 1
    exe, argv, env = execve_calls[0]
    prompt_arg = argv[argv.index("--append-system-prompt") + 1]
    assert "RTK shell-output efficiency" in prompt_arg
    assert str(mock_bin_target) in prompt_arg

    # 4. Reverse contradictory: target has enabled=false, controller has enabled=true
    mock_bin_ctrl = tmp_path / "bin" / "rtk_ctrl"
    mock_bin_ctrl.parent.mkdir(parents=True, exist_ok=True)
    mock_bin_ctrl.write_text("#!/bin/sh\necho 'rtk 0.43.0'\n", encoding="utf-8")
    mock_bin_ctrl.chmod(0o755)

    ctrl2 = tmp_path / "ctrl2"
    ctrl2.mkdir()
    (ctrl2 / ".git").mkdir()
    (ctrl2 / ".apgr").mkdir()
    (ctrl2 / ".apgr" / "config.toml").write_text(f"""
[integrations.rtk]
enabled = true
executable = "{mock_bin_ctrl}"
""", encoding="utf-8")

    target2 = tmp_path / "target2"
    target2.mkdir()
    (target2 / ".git").mkdir()
    (target2 / ".apgr").mkdir()
    (target2 / ".apgr" / "config.toml").write_text("""
[integrations.rtk]
enabled = false
""", encoding="utf-8")

    disp2 = Dispatcher(root=ctrl2, cwd=target2, apgr_home=apgr_home)
    res_disp2 = disp2._ensure_rtk_resolution()
    assert res_disp2.config.enabled is False
    assert res_disp2.status == "disabled"


def write_fake_evidence(argv: list[str], exit_code: int) -> None:
    if "--evidence-prefix" not in argv:
        return
    prefix = Path(argv[argv.index("--evidence-prefix") + 1])
    summary = prefix.with_name(f"{prefix.name}.antigravity-terminal-result.json")
    summary.parent.mkdir(parents=True, exist_ok=True)
    summary.write_text(json.dumps({"exit_code": exit_code, "status": "COMPLETED"}), encoding="utf-8")


def test_v1_dispatcher_runner_boundary_captures_argv_and_prompt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agent_phase.dispatch import Dispatcher
    from agent_phase.routing import Endpoint
    from agent_phase.envelope import Segment, render, SEGMENT_TASK_PROMPT
    from agent_phase.run import RunDirectory
    from agent_phase import provider as provider_module
    import time

    mock_bin = tmp_path / "bin" / "rtk"
    mock_bin.parent.mkdir(parents=True, exist_ok=True)
    mock_bin.write_text("#!/bin/sh\necho 'rtk 0.43.0'\n", encoding="utf-8")
    mock_bin.chmod(0o755)

    controller_root = _REPO_ROOT
    target_repo = tmp_path / "target_repo"
    target_repo.mkdir()
    (target_repo / ".git").mkdir()
    (target_repo / ".apgr").mkdir()
    (target_repo / ".apgr" / "config.toml").write_text(f"""
[integrations.rtk]
enabled = true
executable = "{mock_bin}"
providers.claude = "instructions"
providers.codex = "instructions"
providers.antigravity = "instructions"
""", encoding="utf-8")

    apgr_home = tmp_path / "home"
    apgr_home.mkdir()

    captured_runs: list[dict[str, Any]] = []

    def mock_runner(argv, prompt_bytes, cwd, max_bytes, on_output=None):
        write_fake_evidence(list(argv), 0)
        captured_runs.append({
            "argv": list(argv),
            "prompt_bytes": prompt_bytes,
            "cwd": cwd,
        })
        now = time.time()
        return provider_module.Result(0, b"turn output", b"", False, now, now)

    run_dir = RunDirectory(tmp_path / "runs", "v1-runner-test", "work-reviewed")
    prompt = render([Segment(SEGMENT_TASK_PROMPT, "Task instructions for test.")])

    # Variant A: No workers (workers=False)
    disp_noworker = Dispatcher(
        root=controller_root,
        cwd=target_repo,
        apgr_home=apgr_home,
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=mock_runner,
    )
    res_a, meta_a = disp_noworker._stage(
        directory=run_dir,
        index=1,
        stage="produce",
        prefix="V0130",
        role="Worker",
        endpoint=Endpoint("codex", "implementation-testing"),
        rendered=prompt,
        binding=None,
        worker_capability={"allowed": False},
    )
    assert res_a.exit_code == 0
    assert len(captured_runs) == 1
    call_a = captured_runs[0]
    assert call_a["cwd"] == target_repo
    assert prompt.data in call_a["prompt_bytes"]
    has_rtk_a = any("RTK shell-output efficiency" in a for a in call_a["argv"])
    assert has_rtk_a
    assert str(mock_bin) in " ".join(call_a["argv"])
    has_workers_a = any("Launcher-advertised guidance" in a for a in call_a["argv"] if "developer_instructions=" in a)
    assert not has_workers_a

    # Variant B: Workers allowed (worker variant)
    captured_runs.clear()
    disp_worker = Dispatcher(
        root=controller_root,
        cwd=target_repo,
        apgr_home=apgr_home,
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=mock_runner,
    )
    res_b, meta_b = disp_worker._stage(
        directory=run_dir,
        index=2,
        stage="produce",
        prefix="V0130-B",
        role="Worker",
        endpoint=Endpoint("codex", "implementation-testing"),
        rendered=prompt,
        binding=None,
        worker_capability=__import__("apgr_workers.policy", fromlist=["resolve_worker_capability"]).resolve_worker_capability(
            controller_root, "codex", "implementation-testing", "gemini_sub"),
    )
    assert res_b.exit_code == 0
    assert len(captured_runs) == 1
    call_b = captured_runs[0]
    assert prompt.data in call_b["prompt_bytes"]
    has_rtk_b = any("RTK shell-output efficiency" in a for a in call_b["argv"])
    assert has_rtk_b
    assert str(mock_bin) in " ".join(call_b["argv"])
    has_workers_b = any("Launcher-advertised guidance" in a for a in call_b["argv"] if "developer_instructions=" in a)
    assert has_workers_b


@pytest.mark.parametrize("mode,provider", [
    ("gemini_sub", "codex"),
    ("gemini_flash_sub", "antigravity"),
    ("gemini_flash_opus_sub", "antigravity"),
])
@pytest.mark.parametrize("facility", ["allowed", "denied", "missing", "broken"])
@pytest.mark.parametrize("rtk_enabled", [True, False])
def test_v2_dispatcher_runner_boundary_captures_argv_and_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str,
    provider: str, facility: str, rtk_enabled: bool,
) -> None:
    from agent_phase.v2_dispatch import dispatch_v2
    from agent_phase.request import parse_request_v2
    from agent_phase import result as result_module

    mock_bin = tmp_path / "bin" / "rtk"
    mock_bin.parent.mkdir(parents=True, exist_ok=True)
    mock_bin.write_text("#!/bin/sh\necho 'rtk 0.43.0'\n", encoding="utf-8")
    mock_bin.chmod(0o755)

    controller_root = _REPO_ROOT
    target_repo = tmp_path / "target_repo"
    target_repo.mkdir()
    subprocess.run(["git", "init", "-q", str(target_repo)], check=True)
    subprocess.run(["git", "-C", str(target_repo), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(target_repo), "config", "user.name", "Test"], check=True)
    (target_repo / "README.md").write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(target_repo), "add", "README.md"], check=True)
    subprocess.run(["git", "-C", str(target_repo), "commit", "-q", "-m", "init"], check=True)

    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
    subprocess.run(["git", "-C", str(target_repo), "remote", "add", "origin", str(remote)], check=True)
    subprocess.run(["git", "-C", str(target_repo), "push", "-q", "--set-upstream", "origin", "HEAD"], check=True)

    (target_repo / ".apgr").mkdir()
    (target_repo / ".apgr" / "config.toml").write_text(f"""
[integrations.rtk]
enabled = {str(rtk_enabled).lower()}
executable = "{mock_bin}"
providers.claude = "instructions"
providers.codex = "instructions"
providers.antigravity = "instructions"
""", encoding="utf-8")

    apgr_home = tmp_path / "home"
    apgr_home.mkdir()

    raw_req = json.dumps({
        "schema": "agent-phase-request-v2",
        "phase_type": "implementation_testing",
        "prompt": "Test prompt for V2 runner boundary",
    }).encode("utf-8")
    req = parse_request_v2(raw_req)

    from agent_phase import worker_capability as wc, v2_turns
    from agent_phase.roster import load_roster

    calls = []
    real_resolve = wc.resolve_worker_capability
    def policy(root, actual_provider, profile, execution_mode, **kwargs):
        calls.append((root, actual_provider, profile, execution_mode))
        cap = real_resolve(root, actual_provider, profile, execution_mode, **kwargs)
        if facility != "allowed":
            return {"allowed": False, "available": False, "reason": "fixture " + facility}
        return cap
    monkeypatch.setattr(wc, "resolve_worker_capability", policy)
    monkeypatch.setattr(v2_turns, "resolve_worker_capability", policy)
    captured = {}
    roster = load_roster(controller_root)
    def runner(*, run_id, binding, route, run_dir, argv=None, prompt_bytes=None, nonce=None):
        endpoint = roster.endpoints[route.endpoint_alias]
        captured[binding.binding_id] = (endpoint, argv, prompt_bytes, binding.process_read_only)
        if binding.binding_id == "binding_work":
            (target_repo / "work_output.txt").write_text("done\n")
        if binding.binding_id == "binding_closeout":
            begin, end = result_module.markers(nonce)
            payload = {"version": 1, "stage": "closeout", "outcome": "completed",
                       "body": "done", "commit_message": None}
            return f"{begin}\n{json.dumps(payload)}\n{end}\n".encode()
        return None
    if mode == "gemini_sub" and facility != "allowed":
        from agent_phase.v2_dispatch import V2DispatchError
        with pytest.raises(V2DispatchError, match="worker_unavailable"):
            dispatch_v2(controller_root, target_repo, req, raw_req, execution_mode=mode,
                        apgr_home=apgr_home, outbox_root=tmp_path / "outbox", runner=runner,
                        finalization_policy="checkpoint", roster=roster)
        assert captured == {}
        return
    result = dispatch_v2(
        controller_root, target_repo, req, raw_req, execution_mode=mode,
        apgr_home=apgr_home, outbox_root=tmp_path / "outbox", runner=runner,
        finalization_policy="checkpoint", roster=roster,
    )
    assert result["status"] == "completed"
    assert set(captured) == {"binding_plan", "binding_plan_review", "binding_work",
                             "binding_work_review", "binding_closeout"}
    for binding_id in ("binding_plan", "binding_work", "binding_closeout"):
        endpoint, argv, prompt, read_only = captured[binding_id]
        expected_provider = "claude" if mode == "gemini_sub" and binding_id == "binding_plan" else provider
        assert endpoint.provider == expected_provider, binding_id
        assert read_only is (binding_id == "binding_plan")
        if read_only:
            if expected_provider == "claude":
                assert "--read-only" in argv
            elif provider == "codex":
                assert argv[argv.index("-s") + 1] == "read-only"
            else:
                assert "--reviewer" in argv
        delivered = "\n".join(argv) + prompt.decode()
        if expected_provider != "claude":
            assert ("RTK shell-output efficiency" in delivered) is rtk_enabled, binding_id
        marker = "Optional shared local workers" if expected_provider == "claude" else "Launcher-advertised guidance"
        assert (marker in delivered) is (facility == "allowed"), binding_id
        if facility != "missing" and not read_only:
            assert (controller_root, expected_provider, endpoint.profile, mode) in calls
    for binding_id in ("binding_plan_review", "binding_work_review"):
        endpoint, argv, prompt, read_only = captured[binding_id]
        assert endpoint.provider == "claude", binding_id
        assert read_only
        assert "--read-only" in argv
        assert "--allowed-tools" not in argv
        assert "Bash" not in argv
        assert ("Optional shared local workers" in prompt.decode()) is (facility == "allowed")
    assert any(c[1] == "claude" for c in calls)


def test_rtk_unavailable_status_diagnostics_at_consumers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    from agent_phase.dispatch import Dispatcher
    from agent_phase.display import Display
    from agent_phase.v2_dispatch import dispatch_v2
    from agent_phase.request import parse_request_v2
    apgr_home = tmp_path / "home"
    apgr_home.mkdir()
    target_repo = tmp_path / "target_repo"
    target_repo.mkdir()
    subprocess.run(["git", "init", "-q", str(target_repo)], check=True)
    (target_repo / ".apgr").mkdir()
    # Configure an unexecutable path so status becomes unavailable
    bad_bin = tmp_path / "not_executable_rtk"
    bad_bin.write_text("not a binary\n")
    bad_bin.chmod(0o644)
    (target_repo / ".apgr" / "config.toml").write_text(f"""
[integrations.rtk]
enabled = true
executable = "{bad_bin}"
""")

    # 1. V1 Dispatcher emits stage notice on unavailable status
    notices: list[tuple[str, str]] = []
    class NoticeDisplay(Display):
        def stage_notice(self, stage: str, message: str) -> None:
            notices.append((stage, message))

    disp = Dispatcher(
        root=_REPO_ROOT,
        cwd=target_repo,
        apgr_home=apgr_home,
        codex_executable="/fake/codex",
    )
    res = disp._ensure_rtk_resolution()
    assert res.status == "unavailable"
    captured_v1 = capsys.readouterr()
    assert "agent-phase: rtk unavailable:" in captured_v1.err

    # 2. V2 Dispatcher surfaces diagnostic on unavailable status
    raw_req = json.dumps({
        "schema": "agent-phase-request-v2",
        "phase_type": "implementation_testing",
        "prompt": "Test prompt",
    }).encode("utf-8")
    req = parse_request_v2(raw_req)

    def quick_runner(*, run_id: str, binding: Any, route: Any, run_dir: Path, nonce: str | None = None, **kw: Any) -> bytes | None:
        if binding.binding_id == "binding_closeout" and nonce:
            from agent_phase import result as rm
            begin, end = rm.markers(nonce)
            return f"{begin}\n{{\"version\": 1, \"stage\": \"closeout\", \"outcome\": \"completed\", \"body\": \"ok\", \"commit_message\": {{\"subject\": \"s\", \"body\": \"b\"}}}}\n{end}\n".encode("utf-8")
        return None

    # Init git repo with origin for v2
    subprocess.run(["git", "-C", str(target_repo), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(target_repo), "config", "user.name", "Test"], check=True)
    (target_repo / "init.txt").write_text("init\n")
    subprocess.run(["git", "-C", str(target_repo), "add", "init.txt"], check=True)
    subprocess.run(["git", "-C", str(target_repo), "commit", "-q", "-m", "init"], check=True)
    rem = tmp_path / "rem.git"
    subprocess.run(["git", "init", "--bare", "-q", str(rem)], check=True)
    subprocess.run(["git", "-C", str(target_repo), "remote", "add", "origin", str(rem)], check=True)
    subprocess.run(["git", "-C", str(target_repo), "push", "-q", "--set-upstream", "origin", "HEAD"], check=True)

    dispatch_v2(
        _REPO_ROOT,
        target_repo,
        req,
        raw_req,
        execution_mode="dynamic",
        apgr_home=apgr_home,
        outbox_root=tmp_path / "outbox_unavail",
        runner=quick_runner,
    )
    captured_v2 = capsys.readouterr()
    assert "agent-phase: v2 rtk unavailable:" in captured_v2.err



def test_probe_execution_timeout_records_executed_and_partial_output() -> None:
    from agentic_praxis_grimoire.rtk import _execute_bounded_probe, run_rtk_probes, ProbeExecutionResult
    import time

    cmd = [
        sys.executable,
        "-c",
        "import sys, time; sys.stdout.write('partial version probe stdout'); sys.stdout.flush(); time.sleep(2)",
    ]
    res = _execute_bounded_probe(cmd, deadline=time.monotonic() + 0.2, max_bytes=1024)
    assert isinstance(res, ProbeExecutionResult)
    assert isinstance(res, tuple)
    assert res.started is True
    assert res.timed_out is True
    assert res.returncode is None
    assert res.stdout == "partial version probe stdout"
    assert any("probe timed out" in d for d in res.diagnostics)

    # Tuple unpacking compatibility
    code, out, err, trunc, diags = res
    assert code is None
    assert out == "partial version probe stdout"

    # run_rtk_probes with mocked probe timeout
    with mock.patch("agentic_praxis_grimoire.rtk._execute_bounded_probe", return_value=res):
        probes = run_rtk_probes("/mock/bin/rtk", minimum_version="0.43.0")
        assert probes["all_ok"] is False
        assert probes["version"]["executed"] is True
        assert probes["version"]["started"] is True
        assert probes["version"]["timed_out"] is True
        assert probes["version"]["ok"] is False
        assert probes["version"]["stdout"] == "partial version probe stdout"
