"""APG166S-R1 runtime authority repairs, provider-free alternate and negative tests."""
import json
import os
from pathlib import Path
import shutil
import tomllib
from unittest.mock import patch

import pytest

from agent_phase.bundle import load_bundle, publish_bundle
from agent_phase.runtime_models import (
    apply_selection,
    captured,
    classify_parent_family,
    launch_capture,
    parent_family_for_endpoint,
    selection,
    source_defaults,
)
from agent_phase.request import PhaseRequest
from agent_phase.roster import Endpoint
from agent_phase.routing import claude_intelligence, resolve
from agent_phase.worker_capability import (
    resolve_worker_capability as phase_resolve_worker_capability,
)
from apgr_workers.codex_external import (
    CodexExternalError,
    LunaProfile,
    build_codex_exec_argv,
    load_luna_profile,
)
from apgr_workers.native_launch import (
    NativeLaunchBinding,
    NativeLaunchError,
    apply_native_binding,
    build_native_argv,
    load_native_worker_source,
    prepare_native_binding,
)
from apgr_workers.policy import (
    _qualified_flash_profile,
    identify_parent_family,
    resolve_worker_capability as policy_resolve_worker_capability,
)
from claude_model_catalog import CatalogData, CatalogProvenance, ModelRecord
from claude_vc_profile import ProfileError, resolve_profile

ROOT = Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------------------
# 1. Central provider-aware parent family classifier, effort separate
# ---------------------------------------------------------------------------

def test_central_classify_parent_family_positive():
    # Antigravity / Gemini
    assert classify_parent_family("antigravity", "gemini-3.8-flash-high") == "gemini_flash"
    assert classify_parent_family("antigravity", "gemini-flash-1.5") == "gemini_flash"
    assert classify_parent_family("antigravity", "  GEMINI-3.8-FLASH-HIGH  ") == "gemini_flash"

    # Claude / Opus and Fable
    assert classify_parent_family("claude", "claude-opus-5-5") == "claude_opus"
    assert classify_parent_family("claude", "claude-opus-5") == "claude_opus"
    assert classify_parent_family("claude", "claude-fable-1") == "claude_fable"

    # Codex parent role
    assert classify_parent_family("codex", "gpt-6.1-sol", role="parent") == "codex_parent"
    assert classify_parent_family("codex", "gpt-7-anything", role="parent") == "codex_parent"


def test_central_classify_parent_family_negative_and_mismatch():
    # Provider mismatches
    assert classify_parent_family("codex", "claude-opus-5-5") is None
    assert classify_parent_family("claude", "gpt-6.1-sol") is None
    assert classify_parent_family("antigravity", "claude-opus-5-5") is None
    assert classify_parent_family("codex", "gemini-3.8-flash-high") is None

    # Unknown models
    assert classify_parent_family("codex", "gpt-4o") is None
    assert classify_parent_family("claude", "claude-haiku-3") is None
    assert classify_parent_family("antigravity", "gemini-pro-1.5") is None
    assert classify_parent_family("unknown_provider", "gpt-6.1-sol") is None

    # Empty or non-string inputs
    assert classify_parent_family("", "") is None
    assert classify_parent_family(None, "gpt-6.1-sol") is None
    assert classify_parent_family("codex", None) is None
    assert classify_parent_family("codex", "") is None


def test_parent_family_for_endpoint_and_policy_integration():
    # Derives family via selection without needing profile name literal
    assert parent_family_for_endpoint(ROOT, "codex", "implementation-testing") == "codex_parent"
    assert parent_family_for_endpoint(ROOT, "claude", "opus-high-review") == "claude_opus"
    assert identify_parent_family(ROOT, "codex", "implementation-testing") == "codex_parent"
    assert identify_parent_family(ROOT, "claude", "opus-high-review") == "claude_opus"

    # Invalid profile / endpoint
    assert parent_family_for_endpoint(ROOT, "codex", "nonexistent-profile") is None
    assert identify_parent_family(ROOT, "invalid provider!", "profile") is None


# ---------------------------------------------------------------------------
# 2. One selected captured inventory drives consumers & alternate models/efforts
# ---------------------------------------------------------------------------

def test_alternate_captured_inventory_drives_all_consumers(tmp_path, monkeypatch):
    source, home = tmp_path / "source", tmp_path / "home"
    shutil.copytree(ROOT / "common/dispatcher", source)
    models_file = source / "models.toml"
    text = models_file.read_text()
    text = text.replace('model = "gpt-6.1-sol"\neffort = "xhigh"',
                        'model = "gpt-7-astra"\neffort = "high"')
    text = text.replace('model = "claude-opus-5-5"\neffort = "high"',
                        'model = "claude-opus-5"\neffort = "medium"')
    text = text.replace('model = "gpt-6-luna"\neffort = "max"',
                        'model = "gpt-6-luna-alt"\neffort = "high"')
    models_file.write_text(text)

    publish_bundle(source, home / "dispatcher")
    monkeypatch.setenv("APGR_HOME", str(home))

    bundle = load_bundle(apgr_home=home, repo_root=ROOT)
    with captured(bundle):
        # 1. selection() reflects alternate model and effort
        codex_sel = selection(ROOT, "codex", "implementation-testing")
        assert codex_sel["model"] == "gpt-7-astra"
        assert codex_sel["effort"] == "high"

        # 2. Claude resolve_profile and claude_intelligence reflect alternate model and effort
        resolved_claude = resolve_profile(ROOT / "claude", "opus-high-review")
        assert resolved_claude.resolved_model_id == "claude-opus-5"
        assert resolved_claude.source_profile["effort"] == "medium"
        claude_intel = claude_intelligence(ROOT, "opus-high-review")
        assert claude_intel["model"] == "claude-opus-5"
        assert claude_intel["effort"] == "medium"

        # 3. apply_selection writes alternate model and effort
        endpoint = Endpoint("codex", "implementation-testing")
        argv = apply_selection(["codex", "exec", "-"], endpoint, ROOT)
        assert '-c' in argv
        assert 'model="gpt-7-astra"' in argv
        assert 'model_reasoning_effort="high"' in argv

        # 4. Luna worker source reflects alternate Luna model and effort
        luna_native = load_native_worker_source(ROOT, "luna-worker")
        assert luna_native.model == "gpt-6-luna-alt"
        assert luna_native.effort == "high"

        luna_external = load_luna_profile(ROOT, "luna-worker")
        assert luna_external.model == "gpt-6-luna-alt"
        assert luna_external.effort == "high"

        luna_argv = build_codex_exec_argv(luna_external, tmp_path, "read_only")
        assert "--skip-git-repo-check" in luna_argv
        assert "--ephemeral" not in luna_argv
        assert luna_argv[luna_argv.index("--sandbox") + 1] == "read-only"
        assert 'model="gpt-6-luna-alt"' in luna_argv
        assert 'model_reasoning_effort="high"' in luna_argv


# ---------------------------------------------------------------------------
# 3. Removal of model/effort literals as authorities, fixed 4+4 remains
# ---------------------------------------------------------------------------

def test_removal_of_model_effort_literals_and_fixed_4x4_pools(tmp_path, monkeypatch):
    source, home = tmp_path / "source", tmp_path / "home"
    shutil.copytree(ROOT / "common/dispatcher", source)
    models_file = source / "models.toml"
    text = models_file.read_text()
    # Use a non-default Codex parent model and effort with an explicit role.
    text = text.replace('model = "gpt-6.1-sol"', 'model = "gpt-8-astra"')
    text = text.replace('effort = "xhigh"', 'effort = "low"')
    models_file.write_text(text)

    publish_bundle(source, home / "dispatcher")
    monkeypatch.setenv("APGR_HOME", str(home))
    bundle = load_bundle(apgr_home=home, repo_root=ROOT)

    with captured(bundle):
        # Native parent profile loader accepts alternate model/effort because literals are removed
        from apgr_workers.native_launch import _load_parent_profile
        model, effort, rel, sha = _load_parent_profile(ROOT, "implementation-testing")
        assert model == "gpt-8-astra"
        assert effort == "low"

        # Worker capability resolution preserves fixed 4+4 pools in policy layer
        cap = policy_resolve_worker_capability(ROOT, "codex", "implementation-testing", "gemini_sub")
        assert cap is not None
        assert cap["allowed"] is True
        assert cap["limits"]["max_gemini"] == 4
        assert cap["limits"]["max_luna"] == 4
        assert cap["borrowing"] is False

        # Phase-level worker capability resolution in dynamic mode also preserves 4+4 pools
        phase_cap = phase_resolve_worker_capability(ROOT, "codex", "implementation-testing", "dynamic", bundle=bundle)
        assert phase_cap is not None
        assert phase_cap["allowed"] is True
        assert phase_cap["limits"]["max_gemini"] == 4
        assert phase_cap["limits"]["max_luna"] == 4


# ---------------------------------------------------------------------------
# 4. Explicit source_defaults context manager vs ambient APGR_MODEL_AUTHORITY
# ---------------------------------------------------------------------------

def test_explicit_source_defaults_always_honored_via_contextvar(tmp_path, monkeypatch):
    source, home = tmp_path / "source", tmp_path / "home"
    shutil.copytree(ROOT / "common/dispatcher", source)
    models_file = source / "models.toml"
    models_file.write_text(models_file.read_text().replace('model = "gpt-6.1-sol"', 'model = "gpt-6.1-sol-home"'))
    publish_bundle(source, home / "dispatcher")
    monkeypatch.setenv("APGR_HOME", str(home))
    bundle = load_bundle(apgr_home=home, repo_root=ROOT)

    with captured(bundle):
        # Under capture without context manager, home selection is returned
        assert selection(ROOT, "codex", "implementation-testing")["model"] == "gpt-6.1-sol-home"

        # Explicit source_defaults() context manager is always honored even under capture
        with source_defaults():
            assert selection(ROOT, "codex", "implementation-testing")["model"] == "gpt-6.1-sol"


def test_ambient_source_defaults_conflicts_with_captured_bundle(tmp_path, monkeypatch):
    source, home = tmp_path / "source", tmp_path / "home"
    shutil.copytree(ROOT / "common/dispatcher", source)
    publish_bundle(source, home / "dispatcher")
    bundle = load_bundle(apgr_home=home, repo_root=ROOT)

    monkeypatch.setenv("APGR_MODEL_AUTHORITY", "source-defaults")
    # In-memory captured bundle conflict
    with pytest.raises(ValueError, match="ambient APGR_MODEL_AUTHORITY=source-defaults conflicts with captured model authority"):
        with captured(bundle):
            selection(ROOT, "codex", "implementation-testing")


def test_ambient_source_defaults_conflicts_with_dispatch_capture_env(tmp_path, monkeypatch):
    home = tmp_path / "home"
    publish_bundle(ROOT / "common/dispatcher", home / "dispatcher")
    bundle = load_bundle(apgr_home=home, repo_root=ROOT)
    run = tmp_path / "run"
    run.mkdir()

    with launch_capture(bundle, run):
        # launch_capture sets APGR_DISPATCH_MODELS
        monkeypatch.setenv("APGR_MODEL_AUTHORITY", "source-defaults")
        with captured(None):  # clear in-memory contextvar
            with pytest.raises(ValueError, match="ambient APGR_MODEL_AUTHORITY=source-defaults conflicts with captured model authority"):
                selection(ROOT, "codex", "implementation-testing")


def test_ambient_source_defaults_conflicts_with_required_home_authority(tmp_path, monkeypatch):
    # This case selects home authority; captured authority is tested separately.
    monkeypatch.delenv("APGR_DISPATCH_MODELS", raising=False)
    monkeypatch.delenv("APGR_DISPATCH_MODELS_SHA256", raising=False)
    home = tmp_path / "home"
    publish_bundle(ROOT / "common/dispatcher", home / "dispatcher")
    (home / "config.toml").write_text("[dispatcher.bundle]\nrequired = true\n")
    monkeypatch.setenv("APGR_HOME", str(home))
    monkeypatch.setenv("APGR_MODEL_AUTHORITY", "source-defaults")

    with pytest.raises(ValueError, match="ambient APGR_MODEL_AUTHORITY=source-defaults conflicts with selected home model authority"):
        selection(ROOT, "codex", "implementation-testing")


def test_ambient_source_defaults_without_capture_or_required_home_succeeds(monkeypatch):
    # When neither capture nor required home is present, ambient source-defaults falls back cleanly
    monkeypatch.delenv("APGR_HOME", raising=False)
    monkeypatch.delenv("APGR_DISPATCH_MODELS", raising=False)
    monkeypatch.setenv("APGR_MODEL_AUTHORITY", "source-defaults")

    sel = selection(ROOT, "codex", "implementation-testing")
    assert sel["model"] == "gpt-6.1-sol"
    assert sel["effort"] == "xhigh"


# ---------------------------------------------------------------------------
# 5. apply_selection is SOLE parent Codex model argv writer
# ---------------------------------------------------------------------------

def test_apply_selection_sole_parent_codex_writer(tmp_path):
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    binding = prepare_native_binding(
        ROOT,
        parent_id="test-parent-sole-writer",
        parent_profile="implementation-testing",
        workspace=workspace,
        state_dir=state_dir,
        task_authority="read_only",
    )

    # 1. config_overrides contains only subagent and MCP keys; no parent model/effort
    overrides = binding.config_overrides()
    for override in overrides:
        key = override.split("=", 1)[0]
        assert key.startswith("agents.") or key.startswith("mcp_servers."), f"Unexpected key in config_overrides: {key}"
        assert not key.startswith("model"), f"Model key present in config_overrides: {key}"

    # 2. build_native_argv delegates to apply_selection, which is sole model writer
    argv = build_native_argv(binding, codex_executable="/fake/codex")
    model_entries = [arg for arg in argv if arg.startswith("model=")]
    effort_entries = [arg for arg in argv if arg.startswith("model_reasoning_effort=")]
    assert len(model_entries) == 1
    assert model_entries[0] == 'model="gpt-6.1-sol"'
    assert len(effort_entries) == 1
    assert effort_entries[0] == 'model_reasoning_effort="xhigh"'

    # 3. apply_native_binding rejects caller-supplied model
    with pytest.raises(NativeLaunchError, match="caller-supplied model is not allowed"):
        apply_native_binding(["codex", "exec", "--model", "custom-model", "-"], binding)
    with pytest.raises(NativeLaunchError, match="caller-supplied model is not allowed"):
        apply_native_binding(["codex", "exec", "-m", "custom-model", "-"], binding)

    # 4. apply_native_binding rejects caller-supplied agents/mcp config overrides
    with pytest.raises(NativeLaunchError, match="caller-supplied agents.enabled override is not allowed"):
        apply_native_binding(["codex", "exec", "-c", "agents.enabled=true", "-"], binding)


# ---------------------------------------------------------------------------
# 6. Selected Luna profile comes from captured worker policy
# ---------------------------------------------------------------------------

def test_luna_profile_from_captured_worker_policy(tmp_path):
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Bind the selected Luna profile for the Codex native worker facility.
    capability = {
        "policy_selection": "triple_pool_4x4x4",
        "gemini_worker": {"profile": "gemini-3.8-flash-high"},
        "luna_worker": {"profile": "luna-worker", "model": "gpt-6-luna", "effort": "max"},
        "allowed_worker_kinds": ["gemini"],
    }
    binding = prepare_native_binding(
        ROOT,
        parent_id="test-parent-luna-pol",
        parent_profile="implementation-testing",
        workspace=workspace,
        state_dir=state_dir,
        task_authority="read_only",
        capability=capability,
    )
    assert binding.native_model == "gpt-6-luna"
    assert binding.native_effort == "max"

    # Capability omitting luna_worker defaults gracefully to luna-worker profile
    binding_default = prepare_native_binding(
        ROOT,
        parent_id="test-parent-luna-def",
        parent_profile="implementation-testing",
        workspace=workspace,
        state_dir=state_dir,
        task_authority="read_only",
        capability={"policy_selection": "triple_pool_4x4x4", "gemini_worker": {"profile": "gemini-3.8-flash-high"}},
    )
    assert binding_default.native_model == "gpt-6-luna"


# ---------------------------------------------------------------------------
# 7. Validate referenced entries only
# ---------------------------------------------------------------------------

def test_validate_referenced_entries_only(tmp_path):
    source = tmp_path / "source"
    shutil.copytree(ROOT / "common/dispatcher", source)
    models_file = source / "models.toml"

    # Append a completely invalid entry to models.toml
    bad_toml = '\n[providers.codex.broken_profile]\nmodel = ""\neffort = "invalid_effort"\n'
    models_file.write_text(models_file.read_text() + bad_toml)

    home = tmp_path / "home"
    publish_bundle(source, home / "dispatcher")
    bundle = load_bundle(apgr_home=home, repo_root=ROOT)

    # Valid referenced entry succeeds despite unreferenced broken_profile
    with captured(bundle):
        valid = selection(ROOT, "codex", "implementation-testing")
        assert valid["model"] == "gpt-6.1-sol"

        # Referencing the broken entry fails with invalid selected model
        with pytest.raises(Exception, match="invalid.*model"):
            selection(ROOT, "codex", "broken_profile")

        # Missing profile fails
        with pytest.raises(Exception, match="no model mapping found|missing model selection"):
            selection(ROOT, "codex", "nonexistent")


# ---------------------------------------------------------------------------
# 8. Claude metadata by selected model ID & negative cases
# ---------------------------------------------------------------------------

def test_claude_metadata_resolution_and_defaults():
    # Standard resolution uses selected model id
    resolved = resolve_profile(ROOT / "claude", "opus-high-review")
    assert resolved.resolved_model_id == "claude-opus-5-5"
    assert resolved.source_profile["effort"] == "high"

    # Optional fields missing default cleanly to None and False
    fake_catalog = CatalogData(
        schema="apgr-claude-model-catalog-v1",
        roles={"opus": "test_record"},
        models={
            "test_record": ModelRecord(
                id="claude-opus-5-5",
                # minimum_claude_code_version and adaptive_thinking omitted
            )
        },
        provenance=CatalogProvenance("apgr-claude-model-catalog-v1", "claude/model-catalog-v1.json", 123, "fake-sha"),
    )
    with patch("claude_model_catalog.load_catalog", return_value=fake_catalog):
        mock_resolved = resolve_profile(ROOT / "claude", "opus-high-review")
        assert mock_resolved.minimum_version is None
        assert mock_resolved.adaptive_thinking is False


def test_claude_metadata_missing_model_in_catalog_fails():
    fake_catalog = CatalogData(
        schema="apgr-claude-model-catalog-v1",
        roles={"opus": "other_record"},
        models={
            "other_record": ModelRecord(
                id="claude-unrelated-model",
            )
        },
        provenance=CatalogProvenance("apgr-claude-model-catalog-v1", "claude/model-catalog-v1.json", 123, "fake-sha"),
    )
    with patch("claude_model_catalog.load_catalog", return_value=fake_catalog):
        with pytest.raises(ProfileError, match="missing model 'claude-opus-5-5' in catalog for profile opus-high-review"):
            resolve_profile(ROOT / "claude", "opus-high-review")


def test_claude_metadata_duplicate_model_in_catalog_fails():
    fake_catalog = CatalogData(
        schema="apgr-claude-model-catalog-v1",
        roles={"opus": "dup1"},
        models={
            "dup1": ModelRecord(
                id="claude-opus-5-5",
            ),
            "dup2": ModelRecord(
                id="claude-opus-5-5",
            ),
        },
        provenance=CatalogProvenance("apgr-claude-model-catalog-v1", "claude/model-catalog-v1.json", 123, "fake-sha"),
    )
    with patch("claude_model_catalog.load_catalog", return_value=fake_catalog):
        with pytest.raises(ProfileError, match="duplicate model 'claude-opus-5-5' in catalog for profile opus-high-review"):
            resolve_profile(ROOT / "claude", "opus-high-review")


def test_claude_metadata_invalid_selected_effort_fails(tmp_path, monkeypatch):
    source, home = tmp_path / "source", tmp_path / "home"
    shutil.copytree(ROOT / "common/dispatcher", source)
    models_file = source / "models.toml"
    # Write invalid effort string
    models_file.write_text(models_file.read_text().replace('model = "claude-opus-5-5"\neffort = "high"',
                                                           'model = "claude-opus-5-5"\neffort = "turbo"'))
    publish_bundle(source, home / "dispatcher")
    monkeypatch.setenv("APGR_HOME", str(home))
    bundle = load_bundle(apgr_home=home, repo_root=ROOT)

    with captured(bundle):
        with pytest.raises(ProfileError, match="invalid selected effort"):
            resolve_profile(ROOT / "claude", "opus-high-review")


# ---------------------------------------------------------------------------
# 9. _qualified_flash_profile worker qualification separate & selection-derived
# ---------------------------------------------------------------------------

def test_qualified_flash_profile_selection_derived(tmp_path, monkeypatch):
    # Standard source defaults qualification returns True for gemini-3.8-flash-high
    assert _qualified_flash_profile(ROOT, "gemini-3.8-flash-high") is True

    # When selection resolves a non-flash-high model, qualification returns False
    source, home = tmp_path / "source", tmp_path / "home"
    shutil.copytree(ROOT / "common/dispatcher", source)
    models_file = source / "models.toml"
    models_file.write_text(models_file.read_text().replace('model = "gemini-3.8-flash-high"',
                                                           'model = "gemini-1.5-pro"'))
    publish_bundle(source, home / "dispatcher")
    monkeypatch.setenv("APGR_HOME", str(home))
    bundle = load_bundle(apgr_home=home, repo_root=ROOT)

    with captured(bundle):
        assert _qualified_flash_profile(ROOT, "gemini-3.8-flash-high") is False
        assert _qualified_flash_profile(ROOT, "nonexistent-profile") is False


# ---------------------------------------------------------------------------
# 10. Default five parents / Luna route preserved
# ---------------------------------------------------------------------------

def test_default_five_parents_and_luna_route_preserved():
    result = resolve(
        PhaseRequest("implementation_testing", "gemini_sub", "Default authority validation."),
        ROOT,
        finalization_policy="checkpoint",
    )
    assert len(result["stages"]) == 5
    for stage, record in result["stages"].items():
        is_claude = stage in {"plan", "plan_review", "final_review"}
        assert record["intelligence"]["model"] == ("claude-opus-5-5" if is_claude else "gpt-6.1-sol")
        assert record["intelligence"]["effort"] == ("high" if is_claude else "xhigh")

        cap = record["worker_capability"]
        assert cap["allowed"] is True
        assert cap["limits"]["max_gemini"] == 4
        assert cap["limits"]["max_luna"] == 4
        assert cap["luna_worker"]["model"] == "gpt-6-luna"
        assert cap["luna_worker"]["effort"] == "max"
        assert cap["luna_worker"]["transport"] == ("codex_external" if is_claude else "codex_native")
