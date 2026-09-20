"""Tests for APGR Generation 8 dispatcher configuration bundle.

Covers:
- Canonical model/worker inventory in models.toml and workers.toml
- Immutable bundle loader and atomic projection/verification
- Precedence, override, tamper, and legacy migration error handling
- CLI tool execution
- Adverse cases: nested mutation, required config absent, home model override,
  wrong bool/type, generation 42, returned bytes after tampering, overwrite atomic
  behavior or honest refusal, dangling symlink root.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import tomllib
from typing import Any
import unittest
from unittest import mock

# Ensure libexec is on sys.path
_REPO_ROOT = Path(__file__).resolve().parents[3]
_LIBEXEC = _REPO_ROOT / "libexec"
if str(_LIBEXEC) not in sys.path:
    sys.path.insert(0, str(_LIBEXEC))

from agent_phase.bundle import (
    BUNDLE_GENERATION,
    BUNDLE_MEMBERS,
    BUNDLE_SCHEMA,
    LEGACY_MEMBERS,
    MANIFEST_FILENAME,
    BundleError,
    BundleGenerationError,
    BundleNotFoundError,
    BundleTamperError,
    LegacyBundleError,
    capture_bundle,
    load_bundle,
    publish_bundle,
    verify_bundle,
)
import agent_phase.bundle as bundle_mod


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _create_mock_gen8_source(source_dir: Path, *, generation: int = 8, agg_limit: int = 8) -> None:
    """Create a complete valid 6-file source bundle for testing."""
    # models.toml
    models_content = (
        'schema = "agent-phase-models-v1"\n'
        f'generation = {generation}\n\n'
        '[roles.claude]\n'
        'primary = "claude-opus-5"\n'
        'review = "claude-fable-5-1"\n'
        'opus = "claude-opus-5-5"\n\n'
        '[roles.codex]\n'
        'parent = "gpt-6-astra"\n'
        'worker = "gpt-6-luna"\n\n'
        '[roles.antigravity]\n'
        'worker = "gemini-3.8-flash-high"\n\n'
        '[providers.claude.opus-high-plan]\n'
        'model = "claude-opus-5-5"\n'
        'effort = "high"\n'
        'role = "opus"\n\n'
        '[providers.codex.luna-worker]\n'
        'model = "gpt-6-luna"\n'
        'effort = "max"\n'
        'role = "worker"\n\n'
        '[providers.antigravity."gemini-3.8-flash-high"]\n'
        'model = "gemini-3.8-flash-high"\n'
        'effort = "high"\n'
        'role = "worker"\n'
    )
    _write_file(source_dir / "models.toml", models_content)

    # workers.toml
    workers_content = (
        'schema = "agent-worker-policy-v1"\n'
        f'generation = {generation}\n\n'
        '[limits]\n'
        'max_gemini_workers_per_parent = 4\n'
        f'max_aggregate_workers_per_astra_parent = {agg_limit}\n\n'
        '[gemini_worker]\n'
        'provider = "antigravity"\n'
        'profile = "gemini-3.8-flash-high"\n\n'
        '[policy]\n'
        'name = "dual_pool_4x4"\n'
        'borrowing = false\n'
        'leaf_only = true\n'
        'parent_authority = true\n'
        'mode_requirements = ["gemini_sub", "dynamic"]\n\n'
        '[selections.dual_pool_4x4]\n'
        'max_gemini = 4\n'
        'max_luna = 4\n'
        'borrowing = false\n'
        'leaf_only = true\n'
        'parent_authority = true\n'
        'mode_requirements = ["gemini_sub", "dynamic"]\n\n'
        '[selections.dual_pool_4x4.gemini_worker]\n'
        'provider = "antigravity"\n'
        'profile = "gemini-3.8-flash-high"\n\n'
        '[selections.dual_pool_4x4.luna_worker]\n'
        'provider = "codex"\n'
        'profile = "luna-worker"\n'
    )
    _write_file(source_dir / "workers.toml", workers_content)

    # endpoints.toml
    endpoints_content = (
        'schema = "agent-phase-endpoints-v1"\n'
        f'generation = {generation}\n\n'
        '[endpoints.antigravity-gemini-high]\n'
        'provider = "antigravity"\n'
        'profile = "gemini-3.8-flash-high"\n\n'
        '[endpoints.claude-opus-high-plan]\n'
        'provider = "claude"\n'
        'profile = "opus-high-plan"\n'
    )
    _write_file(source_dir / "endpoints.toml", endpoints_content)

    # routes.toml
    routes_content = (
        'schema = "agent-phase-routes-v1"\n'
        f'generation = {generation}\n\n'
        '[routes.software_unit.dynamic]\n'
        'plan = "claude-opus-high-plan"\n'
        'plan_review = "claude-opus-high-plan"\n'
        'work = "antigravity-gemini-high"\n'
        'final_review = "claude-opus-high-plan"\n'
        'closeout = "antigravity-gemini-high"\n'
    )
    _write_file(source_dir / "routes.toml", routes_content)

    # capabilities.toml
    capabilities_content = (
        'schema = "agent-phase-capabilities-v1"\n'
        f'generation = {generation}\n\n'
        '[endpoints.antigravity-gemini-high]\n'
        'provider = "antigravity"\n'
        'profile = "gemini-3.8-flash-high"\n'
        'capabilities = ["read", "mutation", "execution"]\n'
        'posture = "mutating"\n'
    )
    _write_file(source_dir / "capabilities.toml", capabilities_content)

    # policy.toml
    policy_content = (
        'schema = "agent-phase-policy-v1"\n'
        f'generation = {generation}\n\n'
        '[review_mutation]\n'
        'worktree = "warn"\n'
        'index = "block"\n'
        'head = "block"\n'
    )
    _write_file(source_dir / "policy.toml", policy_content)


class TestDispatcherBundleInventory(unittest.TestCase):
    """Test canonical models.toml and workers.toml inventories in repository."""

    def test_canonical_models_toml(self) -> None:
        path = _REPO_ROOT / "common" / "dispatcher" / "models.toml"
        self.assertTrue(path.is_file(), "common/dispatcher/models.toml must exist")
        data = tomllib.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(data.get("schema"), "agent-phase-models-v1")
        self.assertEqual(data.get("generation"), 9)

        # Check Claude roles
        roles = data.get("roles", {})
        claude_roles = roles.get("claude", {})
        self.assertEqual(claude_roles.get("primary"), "claude-opus-5-5")
        self.assertEqual(claude_roles.get("opus"), "claude-opus-5-5")

        # Check Claude profiles
        claude_profiles = data.get("providers", {}).get("claude", {})
        self.assertEqual(claude_profiles.get("opus-high-plan", {}).get("model"), "claude-opus-5-5")
        self.assertEqual(claude_profiles.get("opus-high-plan", {}).get("effort"), "high")
        self.assertEqual(claude_profiles.get("opus-high-plan", {}).get("role"), "opus")

        self.assertEqual(claude_profiles.get("opus-high-review", {}).get("model"), "claude-opus-5-5")
        self.assertEqual(claude_profiles.get("opus-high-sysadmin-review", {}).get("model"), "claude-opus-5-5")

        # Check Codex profiles
        codex_profiles = data.get("providers", {}).get("codex", {})
        self.assertEqual(codex_profiles.get("luna-worker", {}).get("model"), "gpt-6-luna")
        self.assertEqual(codex_profiles.get("luna-worker", {}).get("effort"), "max")
        self.assertEqual(codex_profiles.get("luna-worker", {}).get("role"), "worker")

        # Check Antigravity profiles
        ag_profiles = data.get("providers", {}).get("antigravity", {})
        self.assertEqual(ag_profiles.get("gemini-3.8-flash-high", {}).get("model"), "gemini-3.8-flash-high")

    def test_canonical_workers_toml(self) -> None:
        path = _REPO_ROOT / "common" / "dispatcher" / "workers.toml"
        self.assertTrue(path.is_file(), "common/dispatcher/workers.toml must exist")
        data = tomllib.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(data.get("schema"), "agent-worker-policy-v2")
        self.assertEqual(data.get("generation"), 9)

        # Check limits: strict 4 + 8 (old 10 removed)
        limits = data.get("limits", {})
        self.assertEqual(limits.get("max_gemini_workers_per_parent"), 4)
        self.assertEqual(limits.get("max_aggregate_workers_per_codex_parent"), 12)

        # Check gemini worker
        gemini_w = data.get("gemini_worker", {})
        self.assertEqual(gemini_w.get("provider"), "antigravity")
        self.assertEqual(gemini_w.get("profile"), "gemini-3.8-flash-high")

        # Check selections triple_pool_4x4x4
        dp = data.get("selections", {}).get("triple_pool_4x4x4", {})
        self.assertEqual(dp.get("max_gemini"), 4)
        self.assertEqual(dp.get("max_luna"), 4)
        self.assertEqual(dp.get("max_sonnet"), 4)
        self.assertFalse(dp.get("borrowing"))
        self.assertTrue(dp.get("leaf_only"))
        self.assertTrue(dp.get("parent_authority"))
        self.assertEqual(dp.get("mode_requirements"), ["gemini_sub", "dynamic"])

        luna_w = dp.get("luna_worker", {})
        self.assertEqual(luna_w.get("provider"), "codex")
        self.assertEqual(luna_w.get("profile"), "luna-worker")


class TestDispatcherBundleOperations(unittest.TestCase):
    """Test bundle capture, atomic projection, verification, and tamper detection."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.scratch = Path(self.temp_dir.name)
        self.source_dir = self.scratch / "source"
        self.target_dir = self.scratch / "target" / "dispatcher"
        _create_mock_gen8_source(self.source_dir, generation=8, agg_limit=8)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_capture_bundle_success(self) -> None:
        members, manifest = capture_bundle(self.source_dir, expected_generation=8)
        self.assertEqual(len(members), 6)
        self.assertEqual(set(members), set(BUNDLE_MEMBERS))
        self.assertEqual(manifest["schema"], BUNDLE_SCHEMA)
        self.assertEqual(manifest["generation"], 8)
        for name in BUNDLE_MEMBERS:
            self.assertIn(name, manifest["files"])
            self.assertEqual(members[name].sha256, manifest["files"][name]["sha256"])

    def test_publish_bundle_atomic_replacement(self) -> None:
        # First publish: target does not exist yet
        snapshot1 = publish_bundle(self.source_dir, self.target_dir, expected_generation=8)
        self.assertEqual(snapshot1.generation, 8)
        self.assertTrue((self.target_dir / MANIFEST_FILENAME).is_file())
        for name in BUNDLE_MEMBERS:
            self.assertTrue((self.target_dir / name).is_file())

        # Second publish: target already exists and is non-empty; tests atomic exchange
        snapshot2 = publish_bundle(self.source_dir, self.target_dir, expected_generation=8)
        self.assertEqual(snapshot2.generation, 8)
        self.assertTrue((self.target_dir / MANIFEST_FILENAME).is_file())

    def test_publish_bundle_is_owner_private_under_permissive_umask(self) -> None:
        previous = os.umask(0)
        try:
            publish_bundle(self.source_dir, self.target_dir, expected_generation=8)
            publish_bundle(self.source_dir, self.target_dir, expected_generation=8)
        finally:
            os.umask(previous)
        self.assertEqual(stat.S_IMODE(self.target_dir.stat().st_mode), 0o700)
        for name in (*BUNDLE_MEMBERS, MANIFEST_FILENAME):
            self.assertEqual(stat.S_IMODE((self.target_dir / name).stat().st_mode), 0o600, name)
        self.assertEqual(verify_bundle(self.target_dir, expected_generation=8)["generation"], 8)
        self.assertEqual(set(capture_bundle(self.target_dir)[0]), set(BUNDLE_MEMBERS))

    def test_verify_bundle_success(self) -> None:
        publish_bundle(self.source_dir, self.target_dir, expected_generation=8)
        manifest = verify_bundle(self.target_dir, expected_generation=8)
        self.assertEqual(manifest["generation"], 8)
        self.assertEqual(len(manifest["files"]), 6)

    def test_manifest_tamper_fails_closed(self) -> None:
        publish_bundle(self.source_dir, self.target_dir, expected_generation=8)

        # Tamper with models.toml content
        models_file = self.target_dir / "models.toml"
        models_file.write_text(models_file.read_text(encoding="utf-8") + "\n# corrupted", encoding="utf-8")

        with self.assertRaises(BundleTamperError) as ctx:
            verify_bundle(self.target_dir, expected_generation=8)
        self.assertIn("manifest tamper", str(ctx.exception))

    def test_missing_manifest_fails_closed(self) -> None:
        publish_bundle(self.source_dir, self.target_dir, expected_generation=8)
        (self.target_dir / MANIFEST_FILENAME).unlink()

        with self.assertRaises(BundleTamperError) as ctx:
            verify_bundle(self.target_dir, expected_generation=8)
        self.assertIn("manifest missing", str(ctx.exception))

    def test_partial_generation_mismatch_fails_closed(self) -> None:
        # Change generation in one file in source
        policy_file = self.source_dir / "policy.toml"
        policy_file.write_text(policy_file.read_text().replace("generation = 8", "generation = 7"))

        with self.assertRaises(BundleGenerationError):
            capture_bundle(self.source_dir, expected_generation=8)

    def test_legacy_four_file_migration_error(self) -> None:
        legacy_dir = self.scratch / "legacy"
        # Only create the legacy 4 files with generation 7
        for name in LEGACY_MEMBERS:
            _write_file(legacy_dir / name, f'schema = "agent-phase-{name.split(".")[0]}-v1"\ngeneration = 7\n')

        with self.assertRaises(LegacyBundleError) as ctx:
            verify_bundle(legacy_dir, expected_generation=8)
        self.assertIn("legacy four-file dispatcher configuration detected", str(ctx.exception))
        self.assertIn("migration to six-file bundle (generation 9) required", str(ctx.exception))

    def test_runtime_authority_home_bundle_precedence(self) -> None:
        mock_home = self.scratch / "mock_apgr_home"
        mock_home_disp = mock_home / "dispatcher"

        # Publish bundle to mock_home_disp
        publish_bundle(self.source_dir, mock_home_disp, expected_generation=8)

        # Load bundle specifying apgr_home
        snapshot = load_bundle(apgr_home=mock_home, repo_root=self.scratch)
        self.assertEqual(snapshot.bundle_dir, mock_home_disp)
        self.assertEqual(snapshot.generation, 8)

    def test_home_bundle_required_flag(self) -> None:
        empty_home = self.scratch / "empty_home"
        empty_home.mkdir()

        # required=True must raise BundleNotFoundError when home bundle is absent
        with self.assertRaises(BundleNotFoundError):
            load_bundle(apgr_home=empty_home, repo_root=self.scratch, required=True)

    def test_profile_model_selection_api(self) -> None:
        publish_bundle(self.source_dir, self.target_dir, expected_generation=8)
        snapshot = load_bundle(target_override=self.target_dir)

        # Model selection for Claude opus-high-plan
        sel_claude = snapshot.select_model("claude", "opus-high-plan")
        self.assertEqual(sel_claude.model, "claude-opus-5-5")
        self.assertEqual(sel_claude.effort, "high")
        self.assertEqual(sel_claude.role, "opus")

        # Model selection for Codex luna-worker
        sel_luna = snapshot.select_model("codex", "luna-worker")
        self.assertEqual(sel_luna.model, "gpt-6-luna")
        self.assertEqual(sel_luna.effort, "max")
        self.assertEqual(sel_luna.role, "worker")

        # Role model selection
        self.assertEqual(snapshot.select_role_model("claude", "primary"), "claude-opus-5")
        self.assertEqual(snapshot.select_role_model("claude", "opus"), "claude-opus-5-5")
        self.assertEqual(snapshot.select_role_model("codex", "worker"), "gpt-6-luna")

        # Worker policy access
        wp = snapshot.get_worker_policy()
        self.assertEqual(wp.max_gemini, 4)
        self.assertEqual(wp.max_luna, 4)
        self.assertFalse(wp.borrowing)
        self.assertTrue(wp.leaf_only)
        self.assertTrue(wp.parent_authority)
        self.assertTrue(snapshot.validate_mode_requirements("gemini_sub"))
        self.assertTrue(snapshot.validate_mode_requirements("dynamic"))
        self.assertFalse(snapshot.validate_mode_requirements("unknown_mode"))

        # Endpoints and routes lookup
        ep = snapshot.get_endpoint("antigravity-gemini-high")
        self.assertEqual(ep.provider, "antigravity")
        self.assertEqual(ep.profile, "gemini-3.8-flash-high")

        routes = snapshot.route_aliases("software_unit", "dynamic")
        self.assertEqual(routes["plan"], "claude-opus-high-plan")
        self.assertEqual(routes["work"], "antigravity-gemini-high")

    def test_symlink_defense_fails_closed(self) -> None:
        symlink_source = self.scratch / "symlink_source"
        _create_mock_gen8_source(symlink_source)
        real_file = self.scratch / "external_models.toml"
        real_file.write_text((symlink_source / "models.toml").read_text(encoding="utf-8"), encoding="utf-8")
        (symlink_source / "models.toml").unlink()
        (symlink_source / "models.toml").symlink_to(real_file)

        with self.assertRaises(BundleError) as ctx:
            capture_bundle(symlink_source, expected_generation=8)
        self.assertIn("symlink", str(ctx.exception).lower())

    def test_manifest_hash_tamper_in_bundle_json(self) -> None:
        publish_bundle(self.source_dir, self.target_dir, expected_generation=8)
        manifest_file = self.target_dir / MANIFEST_FILENAME
        manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
        manifest_data["files"]["models.toml"]["sha256"] = "0" * 64
        manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

        with self.assertRaises(BundleTamperError) as ctx:
            verify_bundle(self.target_dir, expected_generation=8)
        self.assertIn("manifest tamper", str(ctx.exception))

    def test_source_defaults_fallback_when_home_absent(self) -> None:
        empty_home = self.scratch / "fallback_home"
        empty_home.mkdir()
        snapshot = load_bundle(apgr_home=empty_home, repo_root=_REPO_ROOT, required=False)
        self.assertEqual(snapshot.generation, 9)
        self.assertEqual(snapshot.bundle_dir, _REPO_ROOT / "common" / "dispatcher")
        self.assertEqual(snapshot.manifest.get("authority"), "source_default")
        self.assertTrue(snapshot.manifest.get("source_default"))

    def test_snapshot_immutability(self) -> None:
        publish_bundle(self.source_dir, self.target_dir, expected_generation=8)
        snapshot = load_bundle(target_override=self.target_dir)

        with self.assertRaises(TypeError):
            snapshot.members["models.toml"] = None  # type: ignore[index]

        with self.assertRaises(TypeError):
            snapshot.models_catalog["roles"] = {}  # type: ignore[index]

        with self.assertRaises(TypeError):
            snapshot.endpoints["test"] = None  # type: ignore[index]

    def test_cli_execution(self) -> None:
        bin_path = _REPO_ROOT / "bin" / "apgr-dispatcher-bundle"
        self.assertTrue(bin_path.is_file(), "bin/apgr-dispatcher-bundle must exist")

        # 1. Project via CLI
        target = self.scratch / "cli_target" / "dispatcher"
        proc = subprocess.run(
            [
                sys.executable,
                str(bin_path),
                "project",
                "--source-dir",
                str(self.source_dir),
                "--target-dir",
                str(target),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, f"project failed: {proc.stderr}")
        self.assertIn("Atomically projected bundle", proc.stdout)

        # 2. Verify via CLI
        proc_v = subprocess.run(
            [
                sys.executable,
                str(bin_path),
                "verify",
                "--bundle-dir",
                str(target),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc_v.returncode, 0, f"verify failed: {proc_v.stderr}")
        self.assertIn("Verified bundle", proc_v.stdout)

        # 3. Show via CLI (JSON)
        proc_s = subprocess.run(
            [
                sys.executable,
                str(bin_path),
                "show",
                "--bundle-dir",
                str(target),
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc_s.returncode, 0, f"show failed: {proc_s.stderr}")
        data = json.loads(proc_s.stdout)
        self.assertEqual(data["generation"], 8)
        self.assertEqual(data["worker_policy"]["name"], "dual_pool_4x4")


class TestDispatcherBundleAdverse(unittest.TestCase):
    """Adverse tests for APG166S bounded corrections:

    - Recursive nested immutability
    - Required config absent
    - Home model override without whole catalog equality
    - Wrong bool and type validation
    - Coherent arbitrary positive generation 42
    - Returned bytes verification without TOCTOU
    - Overwrite atomic behavior or honest refusal
    - Dangling symlink root defense
    - Manifest authority identity
    """

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.scratch = Path(self.temp_dir.name)
        self.source_dir = self.scratch / "source"
        self.target_dir = self.scratch / "target" / "dispatcher"
        _create_mock_gen8_source(self.source_dir, generation=8, agg_limit=8)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_nested_mutation_fails_closed(self) -> None:
        """True recursive immutability: deep nested mutations must raise TypeError."""
        publish_bundle(self.source_dir, self.target_dir, expected_generation=8)
        snapshot = load_bundle(target_override=self.target_dir)

        # 1. Nested models catalog
        with self.assertRaises(TypeError):
            snapshot.models_catalog["roles"]["claude"] = "corrupt"  # type: ignore[index]
        with self.assertRaises(TypeError):
            snapshot.models_catalog["providers"]["claude"]["opus-high-plan"]["model"] = "corrupt"  # type: ignore[index]

        # 2. Nested bundle member parsed dictionary
        with self.assertRaises(TypeError):
            snapshot.members["models.toml"].parsed["roles"] = {}  # type: ignore[index]
        with self.assertRaises(TypeError):
            snapshot.members["models.toml"].parsed["roles"]["claude"] = "corrupt"  # type: ignore[index]

        # 3. Nested manifest
        with self.assertRaises(TypeError):
            snapshot.manifest["files"]["models.toml"]["sha256"] = "corrupt"  # type: ignore[index]

        # 4. Worker policy limits and worker mappings
        with self.assertRaises(TypeError):
            snapshot.worker_policy.limits["max_gemini_workers_per_parent"] = 10  # type: ignore[index]
        with self.assertRaises(TypeError):
            snapshot.worker_policy.gemini_worker["profile"] = "corrupt"  # type: ignore[index]
        with self.assertRaises(TypeError):
            snapshot.worker_policy.luna_worker["profile"] = "corrupt"  # type: ignore[index]

        # 5. Nested routes
        with self.assertRaises(TypeError):
            snapshot.routes[("software_unit", "dynamic")]["plan"] = "corrupt"  # type: ignore[index]

    def test_required_config_absent_home_bundle_fails(self) -> None:
        """Honor dispatcher.bundle.required from <APGR_HOME>/config.toml even if home bundle is absent."""
        mock_home = self.scratch / "cfg_home"
        mock_home.mkdir()
        config_path = mock_home / "config.toml"
        config_path.write_text(
            '[dispatcher.bundle]\nrequired = true\n', encoding="utf-8"
        )

        # Even with required=False explicitly passed, config.toml setting must enforce required!
        with self.assertRaises(BundleNotFoundError) as ctx:
            load_bundle(apgr_home=mock_home, repo_root=self.scratch, required=False)
        self.assertIn("authoritative home dispatcher bundle not found", str(ctx.exception))
        self.assertIn("required", str(ctx.exception))

    def test_home_model_override_without_whole_catalog_equality(self) -> None:
        """Home bundle can define custom models; select_model works without unused catalog equality gates."""
        custom_home = self.scratch / "custom_home"
        custom_disp = custom_home / "dispatcher"
        _create_mock_gen8_source(self.scratch / "custom_src", generation=8, agg_limit=8)

        # Override models.toml with a custom provider and profile only
        custom_models = (
            'schema = "agent-phase-models-v1"\n'
            'generation = 8\n\n'
            '[roles.operator]\n'
            'custom_role = "custom-role-model-v1"\n\n'
            '[providers.custom_provider.custom_profile]\n'
            'model = "operator-fine-tune-7b"\n'
            'effort = "max"\n'
            'role = "worker"\n'
        )
        _write_file(self.scratch / "custom_src" / "models.toml", custom_models)

        publish_bundle(self.scratch / "custom_src", custom_disp, expected_generation=8)
        snapshot = load_bundle(apgr_home=custom_home, repo_root=self.scratch)

        # Successfully selects custom model
        sel = snapshot.select_model("custom_provider", "custom_profile")
        self.assertEqual(sel.model, "operator-fine-tune-7b")
        self.assertEqual(sel.effort, "max")
        self.assertEqual(sel.role, "worker")

        # Successfully selects custom role model
        self.assertEqual(snapshot.select_role_model("operator", "custom_role"), "custom-role-model-v1")

    def test_wrong_bool_and_type_validation(self) -> None:
        """Adverse cases: reject invalid types without coercion (int, bool, str, effort)."""
        bad_src = self.scratch / "bad_src"

        # 1. String "false" for borrowing
        _create_mock_gen8_source(bad_src, generation=8, agg_limit=8)
        w_path = bad_src / "workers.toml"
        w_path.write_text(w_path.read_text().replace("borrowing = false", 'borrowing = "false"'))
        with self.assertRaises(BundleError) as ctx:
            capture_bundle(bad_src, expected_generation=8)
        self.assertIn("borrowing must be boolean False", str(ctx.exception))

        # 2. Boolean True for borrowing (no borrowing!)
        _create_mock_gen8_source(bad_src, generation=8, agg_limit=8)
        w_path = bad_src / "workers.toml"
        w_path.write_text(w_path.read_text().replace("borrowing = false", "borrowing = true"))
        with self.assertRaises(BundleError) as ctx:
            capture_bundle(bad_src, expected_generation=8)
        self.assertIn("borrowing must be boolean False", str(ctx.exception))

        # 3. String "4" for max_gemini
        _create_mock_gen8_source(bad_src, generation=8, agg_limit=8)
        w_path = bad_src / "workers.toml"
        w_path.write_text(w_path.read_text().replace("max_gemini = 4", 'max_gemini = "4"'))
        with self.assertRaises(BundleError) as ctx:
            capture_bundle(bad_src, expected_generation=8)
        self.assertIn("max_gemini must be integer 4", str(ctx.exception))

        # 4. Old aggregate limit 10 instead of 8
        _create_mock_gen8_source(bad_src, generation=8, agg_limit=10)
        with self.assertRaises(BundleError) as ctx:
            capture_bundle(bad_src, expected_generation=8)
        self.assertIn("max_aggregate_workers_per_astra_parent must be integer 8", str(ctx.exception))

        # 5. String "true" for dispatcher.bundle.required in config.toml
        cfg_home = self.scratch / "bad_cfg_home"
        cfg_home.mkdir()
        (cfg_home / "config.toml").write_text('[dispatcher.bundle]\nrequired = "true"\n')
        with self.assertRaises(BundleError) as ctx:
            load_bundle(apgr_home=cfg_home, repo_root=self.scratch)
        self.assertIn("invalid non-boolean dispatcher.bundle.required", str(ctx.exception))

        # 6. Non-string model ID (integer 123) in models.toml: select_model must reject without str() coercion
        _create_mock_gen8_source(bad_src, generation=8, agg_limit=8)
        m_path = bad_src / "models.toml"
        m_path.write_text(m_path.read_text().replace('model = "claude-opus-5-5"', 'model = 123'))
        publish_bundle(bad_src, self.target_dir, expected_generation=8)
        snap = load_bundle(target_override=self.target_dir)
        with self.assertRaises(BundleError) as ctx:
            snap.select_model("claude", "opus-high-plan")
        self.assertIn("invalid model ID", str(ctx.exception))

        # 7. Non-string effort (boolean True) in models.toml: select_model must reject without str() coercion
        _create_mock_gen8_source(bad_src, generation=8, agg_limit=8)
        m_path = bad_src / "models.toml"
        m_path.write_text(m_path.read_text().replace('effort = "high"', 'effort = true'))
        publish_bundle(bad_src, self.target_dir, expected_generation=8)
        snap = load_bundle(target_override=self.target_dir)
        with self.assertRaises(BundleError) as ctx:
            snap.select_model("claude", "opus-high-plan")
        self.assertIn("invalid effort", str(ctx.exception))

    def test_generation42_coherent_home_override(self) -> None:
        """Coherent arbitrary positive operator generation (e.g. 42) must succeed without source-default 8 requirement."""
        gen42_src = self.scratch / "gen42_src"
        _create_mock_gen8_source(gen42_src, generation=42, agg_limit=8)

        gen42_home = self.scratch / "gen42_home"
        gen42_disp = gen42_home / "dispatcher"

        # Publish without forcing expected_generation=8
        snapshot = publish_bundle(gen42_src, gen42_disp)
        self.assertEqual(snapshot.generation, 42)
        self.assertEqual(snapshot.manifest["generation"], 42)
        for member in snapshot.members.values():
            self.assertEqual(member.generation, 42)

        # Load home bundle without specifying expected_generation
        loaded = load_bundle(apgr_home=gen42_home, repo_root=self.scratch)
        self.assertEqual(loaded.generation, 42)
        self.assertEqual(loaded.select_model("claude", "opus-high-plan").model, "claude-opus-5-5")

    def test_returned_bytes_after_verify_tampering(self) -> None:
        """Verify-and-capture in a single pass: disk tampering after load does not corrupt snapshot."""
        publish_bundle(self.source_dir, self.target_dir, expected_generation=8)
        snapshot = load_bundle(target_override=self.target_dir)

        initial_raw = snapshot.members["models.toml"].raw
        initial_sha = snapshot.members["models.toml"].sha256

        # Tamper with models.toml on disk
        disk_models = self.target_dir / "models.toml"
        disk_models.write_text(disk_models.read_text() + "\n# disk_tamper\n")

        # Verification and subsequent loads fail closed immediately
        with self.assertRaises(BundleTamperError):
            verify_bundle(self.target_dir, expected_generation=8)
        with self.assertRaises(BundleTamperError):
            load_bundle(target_override=self.target_dir)

        # But the returned snapshot retains its verified in-memory bytes intact
        self.assertEqual(snapshot.members["models.toml"].raw, initial_raw)
        self.assertEqual(snapshot.members["models.toml"].sha256, initial_sha)

    def test_overwrite_atomic_behavior_or_honest_refusal(self) -> None:
        """Test atomic replacement without absent window, and honest refusal when unsupported."""
        # 1. Initial publish
        publish_bundle(self.source_dir, self.target_dir, expected_generation=8)
        self.assertTrue((self.target_dir / MANIFEST_FILENAME).is_file())

        # 2. Overwrite publish with updated endpoints
        updated_src = self.scratch / "updated_src"
        _create_mock_gen8_source(updated_src, generation=8, agg_limit=8)
        ep_file = updated_src / "endpoints.toml"
        ep_file.write_text(
            'schema = "agent-phase-endpoints-v1"\n'
            'generation = 8\n\n'
            '[endpoints.updated-ep]\n'
            'provider = "antigravity"\n'
            'profile = "gemini-3.8-flash-high"\n'
        )

        updated_snap = publish_bundle(updated_src, self.target_dir, expected_generation=8)
        self.assertIn("updated-ep", updated_snap.endpoints)
        self.assertTrue((self.target_dir / MANIFEST_FILENAME).is_file())

        # 3. Honest refusal test: simulate platform where atomic exchange is unsupported
        with mock.patch("agent_phase.bundle_io.atomic_exchange_directories") as mock_ex:
            mock_ex.side_effect = BundleError(
                "atomic directory exchange overwrite is unsupported on this platform; "
                "overwrite rejected without absent target window"
            )
            with self.assertRaises(BundleError) as ctx:
                publish_bundle(updated_src, self.target_dir, expected_generation=8)
            self.assertIn("overwrite rejected without absent target window", str(ctx.exception))

            # Target directory remains intact with the previous valid content
            self.assertTrue((self.target_dir / MANIFEST_FILENAME).is_file())
            current_snap = load_bundle(target_override=self.target_dir)
            self.assertIn("updated-ep", current_snap.endpoints)

    def test_dangling_symlink_root_fails_closed(self) -> None:
        """Dangling symlink root must be rejected as a symlink, not misclassified as absent."""
        dangling_root = self.scratch / "dangling_symlink"
        dangling_root.symlink_to(self.scratch / "nonexistent_target_dir")

        with self.assertRaises(BundleError) as ctx:
            capture_bundle(dangling_root)
        self.assertIn("symlink", str(ctx.exception).lower())

        with self.assertRaises(BundleError) as ctx:
            verify_bundle(dangling_root)
        self.assertIn("symlink", str(ctx.exception).lower())

    def test_manifest_authority_records(self) -> None:
        """Manifest records authority ('home' vs 'source_default') and source_default boolean."""
        mock_home = self.scratch / "auth_home"
        mock_disp = mock_home / "dispatcher"
        publish_bundle(self.source_dir, mock_disp, expected_generation=8)

        # Home bundle snapshot
        snap_home = load_bundle(apgr_home=mock_home, repo_root=self.scratch)
        self.assertEqual(snap_home.manifest.get("authority"), "home")
        self.assertFalse(snap_home.manifest.get("source_default"))

        # Source default fallback snapshot
        empty_home = self.scratch / "empty_auth_home"
        empty_home.mkdir()
        snap_default = load_bundle(apgr_home=empty_home, repo_root=_REPO_ROOT, required=False)
        self.assertEqual(snap_default.manifest.get("authority"), "source_default")
        self.assertTrue(snap_default.manifest.get("source_default"))


if __name__ == "__main__":
    unittest.main()
