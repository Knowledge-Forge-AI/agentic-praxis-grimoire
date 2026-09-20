"""Focused regression and policy verification tests for APG166ZO.

Validates:
- All six Codex parent profiles become gpt-6.1-sol/xhigh, Luna unchanged.
- Classification of Codex parent as codex_parent by role, legacy codex_astra compatibility.
- Generation 8->9 bump for all six bundle members.
- Generation-8/v1 bundle remains parseable for inspection.
- Worker v2 triple_pool_4x4x4 contract (4 Gemini, 4 Luna, 4 Sonnet claude-sonnet-5-5/high, no borrowing).
- Transport resolution: Sonnet claude_native for Claude parents, claude_external for Codex/Gemini.
- allowed_worker_kinds external facade: Codex (gemini, sonnet), Claude (gemini, luna), Gemini (gemini, luna, sonnet).
- Worker-disabled modes and legacy Gemini-only modes preserved.
- Claude model catalog worker role with Sonnet.
"""

from __future__ import annotations

import json
from pathlib import Path
import tomllib

import pytest

from agent_phase.bundle import (
    BUNDLE_GENERATION,
    BUNDLE_MEMBERS,
    capture_bundle,
    load_bundle,
)
from agent_phase.runtime_models import (
    classify_parent_family,
    parent_family_for_endpoint,
    selected_worker_profile,
)
from apgr_workers.policy import (
    TRIPLE_POOL,
    load_worker_policy,
    resolve_worker_capability,
    selected_capability,
)
from claude_model_catalog import load_catalog, resolve_role

ROOT = Path(__file__).resolve().parents[3]
CODEX_PARENT_PROFILES = (
    "architecture-docs-primary",
    "architecture-docs-review",
    "implementation-testing",
    "implementation-testing-review",
    "sysadmin-primary",
    "sysadmin-review",
)


def test_six_codex_parent_profiles_sol_xhigh():
    """All six Codex parent profiles must be gpt-6.1-sol/xhigh; Luna remains unchanged."""
    for profile in CODEX_PARENT_PROFILES:
        path = ROOT / "codex" / "profiles" / f"{profile}.config.toml"
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        assert data.get("model") == "gpt-6.1-sol", f"{profile} model mismatch"
        assert data.get("model_reasoning_effort") == "xhigh", f"{profile} effort mismatch"

    luna_path = ROOT / "codex" / "profiles" / "luna-worker.config.toml"
    luna_data = tomllib.loads(luna_path.read_text(encoding="utf-8"))
    assert luna_data.get("model") == "gpt-6-luna"
    assert luna_data.get("model_reasoning_effort") == "max"
    assert luna_data.get("agents", {}).get("enabled") is False

    models_path = ROOT / "common" / "dispatcher" / "models.toml"
    models_data = tomllib.loads(models_path.read_text(encoding="utf-8"))
    assert models_data["roles"]["codex"]["parent"] == "gpt-6.1-sol"
    assert models_data["roles"]["codex"]["worker"] == "gpt-6-luna"

    codex_providers = models_data["providers"]["codex"]
    for profile in CODEX_PARENT_PROFILES:
        entry = codex_providers[profile]
        assert entry["model"] == "gpt-6.1-sol"
        assert entry["effort"] == "xhigh"
        assert entry["role"] == "parent"


def test_classify_parent_family_truthful_and_legacy():
    """Verify truthful codex_parent classification by role and legacy codex_astra compatibility."""
    assert classify_parent_family("codex", "gpt-6.1-sol") is None
    assert classify_parent_family("codex", "gpt-6.1-sol", role="parent") == "codex_parent"
    assert classify_parent_family("codex", "any-custom-gpt", role="parent") == "codex_parent"

    # Legacy compatibility for historical astra models
    assert classify_parent_family("codex", "gpt-6-astra") is None
    assert classify_parent_family("codex", "gpt-7-astra", role="parent") == "codex_parent"

    # Non-parent codex models
    assert classify_parent_family("codex", "gpt-6-luna") is None
    assert classify_parent_family("codex", "gpt-6-luna", role="worker") is None
    assert classify_parent_family("codex", "gpt-4o") is None

    # Claude and Gemini parent classifications
    assert classify_parent_family("claude", "claude-opus-5-5") == "claude_opus"
    assert classify_parent_family("claude", "claude-fable-5-1") == "claude_fable"
    assert classify_parent_family("antigravity", "gemini-3.8-flash-high") == "gemini_flash"

    # Endpoints map to codex_parent
    bundle = load_bundle(repo_root=ROOT)
    for profile in CODEX_PARENT_PROFILES:
        assert parent_family_for_endpoint(ROOT, "codex", profile, bundle=bundle) == "codex_parent"


def test_bundle_members_generation_9_coherence():
    """All six bundle members must be bumped generation 8->9 once with coherent manifest."""
    assert BUNDLE_GENERATION == 9

    dispatcher_dir = ROOT / "common" / "dispatcher"
    for member_name in BUNDLE_MEMBERS:
        member_path = dispatcher_dir / member_name
        data = tomllib.loads(member_path.read_text(encoding="utf-8"))
        assert data.get("generation") == 9, f"{member_name} generation is not 9"

    members, manifest = capture_bundle(dispatcher_dir, expected_generation=9)
    assert manifest["generation"] == 9
    assert len(members) == 6
    for name, member in members.items():
        assert member.generation == 9


def test_legacy_generation_8_bundle_parseable_for_inspection(tmp_path):
    """A generation-8 dual-pool bundle must remain parseable by generic load_bundle for inspection."""
    gen8_dir = tmp_path / "gen8_bundle"
    gen8_dir.mkdir(parents=True)

    # Copy files from common/dispatcher and adapt to generation 8
    src_dir = ROOT / "common" / "dispatcher"
    for name in BUNDLE_MEMBERS:
        text = (src_dir / name).read_text(encoding="utf-8")
        text = text.replace("generation = 9", "generation = 8")
        if name == "workers.toml":
            text = text.replace("triple_pool_4x4x4", "dual_pool_4x4").replace("agent-worker-policy-v2", "agent-worker-policy-v1")
            text = text.replace("max_aggregate_workers_per_codex_parent = 12", "max_aggregate_workers_per_astra_parent = 8")
            text = text.split("[selections.dual_pool_4x4.sonnet_worker]")[0].replace("max_sonnet = 4\n", "")
        (gen8_dir / name).write_text(text, encoding="utf-8")

    members, manifest = capture_bundle(gen8_dir, expected_generation=8)
    assert manifest["generation"] == 8
    manifest_path = gen8_dir / "bundle.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    snapshot = load_bundle(target_override=gen8_dir, expected_generation=8)
    assert snapshot.generation == 8
    assert snapshot.worker_policy.name == "dual_pool_4x4"
    assert snapshot.worker_policy.max_gemini == 4
    assert snapshot.worker_policy.max_luna == 4
    assert snapshot.worker_policy.max_sonnet is None
    from agent_phase.bundle import BundleGenerationError, require_fresh_bundle
    with pytest.raises(BundleGenerationError, match="pinned controller"):
        require_fresh_bundle(snapshot)


def test_worker_v2_triple_pool_contract_exact():
    """Worker policy in workers.toml must define triple_pool_4x4x4 with 4 Gemini, 4 Luna, 4 Sonnet."""
    policy_data, rel_path, sha256 = load_worker_policy(ROOT)
    assert policy_data.get("generation") == 9
    assert policy_data["policy"]["name"] == "triple_pool_4x4x4"

    selection_data = policy_data["selections"]["triple_pool_4x4x4"]
    assert selection_data["max_gemini"] == 4
    assert selection_data["max_luna"] == 4
    assert selection_data["max_sonnet"] == 4
    assert selection_data["borrowing"] is False
    assert selection_data["leaf_only"] is True
    assert selection_data["parent_authority"] is True
    assert selection_data["mode_requirements"] == ["gemini_sub", "dynamic"]

    assert selection_data["gemini_worker"]["provider"] == "antigravity"
    assert selection_data["gemini_worker"]["profile"] == "gemini-3.8-flash-high"
    assert selection_data["luna_worker"]["provider"] == "codex"
    assert selection_data["luna_worker"]["profile"] == "luna-worker"
    assert selection_data["sonnet_worker"]["provider"] == "claude"
    assert selection_data["sonnet_worker"]["profile"] == "sonnet-worker"


def test_triple_pool_capability_transports_and_allowed_kinds():
    """Verify transport resolution and allowed_worker_kinds for all parent families."""
    policy_data, rel_path, sha256 = load_worker_policy(ROOT)

    # 1. Codex parent: allowed_worker_kinds = [gemini, sonnet]; Luna native, Sonnet external
    cap_codex = selected_capability(ROOT, "codex_parent", policy_data, rel_path, sha256, TRIPLE_POOL)
    assert cap_codex["allowed_worker_kinds"] == ["gemini", "sonnet"]
    assert cap_codex["luna_worker"]["transport"] == "codex_native"
    assert cap_codex["sonnet_worker"]["transport"] == "claude_external"
    assert cap_codex["sonnet_worker"]["model"] == "claude-sonnet-5-5"
    assert cap_codex["sonnet_worker"]["effort"] == "high"
    assert cap_codex["limits"]["max_gemini"] == 4
    assert cap_codex["limits"]["max_luna"] == 4
    assert cap_codex["limits"]["max_sonnet"] == 4
    assert cap_codex["borrowing"] is False
    assert cap_codex["native_worker"]["enabled"] is True

    # 2. Claude Opus / Fable parent: allowed_worker_kinds = [gemini, luna]; Luna external, Sonnet native
    cap_claude = selected_capability(ROOT, "claude_opus", policy_data, rel_path, sha256, TRIPLE_POOL)
    assert cap_claude["allowed_worker_kinds"] == ["gemini", "luna"]
    assert cap_claude["luna_worker"]["transport"] == "codex_external"
    assert cap_claude["sonnet_worker"]["transport"] == "claude_native"
    assert cap_claude["sonnet_worker"]["model"] == "claude-sonnet-5-5"
    assert cap_claude["sonnet_worker"]["effort"] == "high"
    assert cap_claude["native_worker"]["enabled"] is True

    cap_fable = selected_capability(ROOT, "claude_fable", policy_data, rel_path, sha256, TRIPLE_POOL)
    assert cap_fable["allowed_worker_kinds"] == ["gemini", "luna"]
    assert cap_fable["luna_worker"]["transport"] == "codex_external"
    assert cap_fable["sonnet_worker"]["transport"] == "claude_native"

    # 3. Gemini Flash parent: allowed_worker_kinds = [gemini, luna, sonnet]; Luna external, Sonnet external
    cap_gemini = selected_capability(ROOT, "gemini_flash", policy_data, rel_path, sha256, TRIPLE_POOL)
    assert cap_gemini["allowed_worker_kinds"] == ["gemini", "luna", "sonnet"]
    assert cap_gemini["luna_worker"]["transport"] == "codex_external"
    assert cap_gemini["sonnet_worker"]["transport"] == "claude_external"
    assert cap_gemini["native_worker"]["enabled"] is False


def test_intentional_worker_disabled_and_legacy_gemini_only_modes():
    """Worker-disabled modes return None; legacy Gemini-only modes return single-pool capability."""
    # Worker-disabled modes
    for disabled_mode in ("normal", "conserve_claude", "codex_only"):
        cap = resolve_worker_capability(ROOT, "codex", "implementation-testing", disabled_mode)
        assert cap is None, f"expected None for worker-disabled mode {disabled_mode}"

    # Legacy Gemini-only modes with gemini_flash parent
    for legacy_mode in ("gemini_opus", "gemini_fable"):
        cap = resolve_worker_capability(ROOT, "claude", "opus-high-plan", legacy_mode)
        assert cap is not None
        assert cap["parent_family"] == "claude_opus"
        assert "sonnet_worker" not in cap
        assert "luna_worker" not in cap
        assert "gemini_worker" in cap


def test_claude_model_catalog_worker_role():
    """Claude model catalog must include worker role mapped to claude-sonnet-5-5."""
    catalog = load_catalog(ROOT)
    assert "worker" in catalog.roles
    assert catalog.roles["worker"] == "sonnet-5-5"
    assert catalog.models["sonnet-5-5"].id == "claude-sonnet-5-5"

    resolved = resolve_role(catalog, "worker")
    assert resolved["resolved_model_id"] == "claude-sonnet-5-5"
    assert resolved["model_role"] == "worker"


def test_selected_worker_profile_resolution():
    """selected_worker_profile resolves profile for all worker kinds."""
    assert selected_worker_profile(ROOT, "gemini") == "gemini-3.8-flash-high"
    assert selected_worker_profile(ROOT, "luna") == "luna-worker"
    assert selected_worker_profile(ROOT, "sonnet") == "sonnet-worker"


@pytest.mark.parametrize("field,value", [
    ("max_gemini", 5), ("max_luna", 3), ("max_sonnet", True),
    ("max_sonnet", 5), ("borrowing", True), ("leaf_only", False),
    ("parent_authority", False),
])
def test_triple_policy_rejects_weakened_contract(field, value):
    from agent_phase.worker_policy_schema import parse_worker_policy
    from agent_phase.bundle import BundleError
    raw = tomllib.loads((ROOT / "common/dispatcher/workers.toml").read_text())
    raw["selections"]["triple_pool_4x4x4"][field] = value
    with pytest.raises(BundleError):
        parse_worker_policy(raw)



def test_mixed_generation_8_9_bundle_is_rejected(tmp_path):
    import shutil
    from agent_phase.bundle import BundleGenerationError
    source = tmp_path / "mixed"
    shutil.copytree(ROOT / "common/dispatcher", source)
    member = source / "capabilities.toml"
    member.write_text(member.read_text().replace("generation = 9", "generation = 8"))
    with pytest.raises(BundleGenerationError, match="generation"):
        capture_bundle(source)


@pytest.mark.parametrize("gen", [9, 10, 41, 99])
def test_require_fresh_bundle_accepts_current_and_future_generations_triple_pool(gen):
    """Generations 9, 10, 41, 99 with triple_pool_4x4x4 are accepted."""
    from types import SimpleNamespace
    from agent_phase.bundle import require_fresh_bundle
    bundle = SimpleNamespace(
        generation=gen,
        worker_policy=SimpleNamespace(name="triple_pool_4x4x4"),
    )
    require_fresh_bundle(bundle)


@pytest.mark.parametrize("gen", [9, 10, 41, 99])
def test_require_fresh_bundle_rejects_gen_gte_9_dual_pool(gen):
    """Generations >= 9 with legacy dual_pool_4x4 are strictly rejected."""
    from types import SimpleNamespace
    from agent_phase.bundle import BundleGenerationError, require_fresh_bundle
    bundle = SimpleNamespace(
        generation=gen,
        worker_policy=SimpleNamespace(name="dual_pool_4x4"),
    )
    with pytest.raises(BundleGenerationError, match="pinned controller"):
        require_fresh_bundle(bundle)


@pytest.mark.parametrize("gen", [1, 7, 8])
def test_require_fresh_bundle_rejects_gen_lt_9_triple_pool(gen):
    """Generations < 9 even with triple_pool_4x4x4 are rejected without controller pin."""
    from types import SimpleNamespace
    from agent_phase.bundle import BundleGenerationError, require_fresh_bundle
    bundle = SimpleNamespace(
        generation=gen,
        worker_policy=SimpleNamespace(name="triple_pool_4x4x4"),
    )
    with pytest.raises(BundleGenerationError, match="pinned controller"):
        require_fresh_bundle(bundle)


def test_require_fresh_bundle_rejects_invalid_shapes():
    """None, bool, and non-integer generation shapes are rejected."""
    from types import SimpleNamespace
    from agent_phase.bundle import BundleGenerationError, require_fresh_bundle
    with pytest.raises(BundleGenerationError, match="pinned controller"):
        require_fresh_bundle(None)
    with pytest.raises(BundleGenerationError, match="pinned controller"):
        require_fresh_bundle(SimpleNamespace(generation="9", worker_policy=SimpleNamespace(name="triple_pool_4x4x4")))
    with pytest.raises(BundleGenerationError, match="pinned controller"):
        require_fresh_bundle(SimpleNamespace(generation=True, worker_policy=SimpleNamespace(name="triple_pool_4x4x4")))


def test_gen8_dual_pool_inspection_settlement_and_fresh_refusal(tmp_path: Path):
    """Gen8 dual-pool bundle and ledger support inspection, settlement, and resume, but refuse fresh admission."""
    # 1. Bundle inspection succeeds for gen8 dual-pool
    gen8_dir = tmp_path / "gen8_bundle"
    gen8_dir.mkdir(parents=True)
    src_dir = ROOT / "common" / "dispatcher"
    for name in BUNDLE_MEMBERS:
        text = (src_dir / name).read_text(encoding="utf-8")
        text = text.replace("generation = 9", "generation = 8")
        if name == "workers.toml":
            text = text.replace("triple_pool_4x4x4", "dual_pool_4x4").replace("agent-worker-policy-v2", "agent-worker-policy-v1")
            text = text.replace("max_aggregate_workers_per_codex_parent = 12", "max_aggregate_workers_per_astra_parent = 8")
            text = text.split("[selections.dual_pool_4x4.sonnet_worker]")[0].replace("max_sonnet = 4\n", "")
        (gen8_dir / name).write_text(text, encoding="utf-8")

    members, manifest = capture_bundle(gen8_dir, expected_generation=8)
    assert manifest["generation"] == 8
    (gen8_dir / "bundle.json").write_text(json.dumps(manifest), encoding="utf-8")

    snapshot = load_bundle(target_override=gen8_dir, expected_generation=8)
    assert snapshot.generation == 8
    assert snapshot.worker_policy.name == "dual_pool_4x4"

    # Fresh bundle dispatch refuses gen8
    from agent_phase.bundle import BundleGenerationError, require_fresh_bundle
    with pytest.raises(BundleGenerationError, match="pinned controller"):
        require_fresh_bundle(snapshot)

    # 2. Historical gen8 dual-pool ledger supports inspection and settlement, but refuses fresh admission
    from apgr_workers.ledger import ParentLedger, PinnedControllerError
    from apgr_workers.native_capacity import PINNED_CONTROLLER_DIAGNOSTIC, SONNET_AGENT_TYPE
    from apgr_workers.inspection import inspect_parent
    from apgr_workers.settlement import close_settled

    ledger = ParentLedger("p_gen8_hist", state_dir=tmp_path / "state")
    ledger._write_data({
        "schema": "agent-worker-ledger-v1",
        "parent_id": "p_gen8_hist",
        "status": "active",
        "parent_family": "codex_astra",
        "workspace": str(tmp_path / "ws"),
        "task_authority": "mutation_capable",
        "worker_allowed": True,
        "policy_selection": "dual_pool_4x4",
        "policy": {"max_gemini": 4, "max_luna": 4, "max_aggregate": 8},
        "worker_capability": {"policy_selection": "dual_pool_4x4"},
        "allowed_worker_kinds": ["gemini"],
        "gemini_jobs": {},
        "native_agents": {},
    })

    # Inspection is valid
    view = inspect_parent("p_gen8_hist", state_dir=tmp_path / "state", root=tmp_path)
    assert "sonnet" not in view["pools"]
    assert "gemini" in view["pools"]
    assert "luna" in view["pools"]

    status = ledger.get_status()
    assert status["policy_selection"] == "dual_pool_4x4"

    # Fresh admission refused
    with pytest.raises(PinnedControllerError) as exc_info:
        ledger.reserve_worker("j_fail", "k_fail", "h" * 64, "mutation_capable", "/tmp/t", worker_kind="gemini")
    assert str(exc_info.value) == PINNED_CONTROLLER_DIAGNOSTIC

    with pytest.raises(PinnedControllerError) as exc_native:
        ledger.reserve_native_agent("native_fail", SONNET_AGENT_TYPE)
    assert str(exc_native.value) == PINNED_CONTROLLER_DIAGNOSTIC

    # Settlement is valid
    reconciled = close_settled(ledger, "settled historical test")
    assert reconciled["status"] == "closed"
    assert reconciled["reconciled"] is True


def test_manifest_generation_mismatch_is_rejected(tmp_path: Path):
    """Manifest generation differing from member generation is rejected."""
    import shutil
    from agent_phase.bundle import BundleGenerationError
    source = tmp_path / "manifest_mismatch"
    shutil.copytree(ROOT / "common/dispatcher", source)
    members, manifest = capture_bundle(source, expected_generation=9)
    manifest["generation"] = 8
    (source / "bundle.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(BundleGenerationError, match="generation"):
        load_bundle(target_override=source, expected_generation=9)


@pytest.mark.parametrize("authority,prefix", [("source_default", "common/dispatcher"), ("home_bundle", "dispatcher")])
def test_bundle_roster_provenance_uses_portable_member_paths(authority, prefix):
    from dataclasses import replace
    from agent_phase.roster import load_roster
    snapshot = load_roster(ROOT)
    bundle = replace(snapshot.bundle, manifest={**snapshot.bundle.manifest, "authority": authority})
    result = replace(snapshot, bundle=bundle).provenance()
    assert set(result["sources"]) == {name.removesuffix(".toml") for name in BUNDLE_MEMBERS}
    for name, member in bundle.members.items():
        assert result["sources"][name.removesuffix(".toml")] == {
            "path": f"{prefix}/{name}", "sha256": member.sha256,
        }
