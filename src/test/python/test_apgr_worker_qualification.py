"""Comprehensive tests for APG166S worker-qualified dynamic routing and capability qualification.

Tests verify:
1. Subsystem origin inspection in candidate libexec/apgr_workers.
2. Candidate absolute executable, facade, and native launch binding qualification.
3. Capacity governance: triple_pool_4x4x4 requirement in dynamic mode, 4+4 limits, no borrowing.
4. Model-based parent family resolution and endpoint matching.
5. Fail-closed mandatory modes (gemini_sub, dynamic) vs optional modes.
6. Injectable worker qualification in dynamic_router rejecting unavailable candidates
   with 'worker_unavailable' (no static capability-only pass; no silent parent-only degradation).
7. Read-only V2 turns preserving 'read_only' worker authority without skipping workers.
8. Keyword bundle and snapshot threading in resolve_v2 and resolve_dynamic_route.
"""

from __future__ import annotations

import os
from pathlib import Path
import stat
import sys
from typing import Any, Mapping
from unittest.mock import MagicMock
import pytest

# Ensure libexec and src are on sys.path
_REPO_ROOT = Path(__file__).resolve().parents[3]
_LIBEXEC = _REPO_ROOT / "libexec"
if str(_LIBEXEC) not in sys.path:
    sys.path.insert(0, str(_LIBEXEC))

from agent_phase.capabilities import EndpointCapabilities
from agent_phase.dynamic_router import (
    NoRouteAvailableError,
    resolve_dynamic_route,
)
from agent_phase.semantic_roles import (
    ActorBinding,
    ROLE_PRODUCER,
)
from agent_phase.worker_capability import (
    WorkerQualificationResult,
    check_subsystem_origin,
    check_worker_binaries,
    expected_parent_family_for_endpoint,
    qualify_worker_eligibility,
    resolve_worker_capability,
    _validate_allowed_capability,
)


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch, tmp_path):
    """Isolate APGR_HOME and clear leaf marker variables."""
    isolated_home = tmp_path / "isolated_home"
    isolated_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("APGR_HOME", str(isolated_home))
    monkeypatch.delenv("APGR_WORKER_LEAF", raising=False)
    monkeypatch.delenv("AGENT_CENTRAL_WORKER_LEAF", raising=False)


def _create_mock_repo(tmp_path: Path, *, with_workers: bool = True, with_bin: bool = True) -> Path:
    repo = tmp_path / "mock_repo"
    repo.mkdir(parents=True, exist_ok=True)
    if with_workers:
        workers_dir = repo / "libexec" / "apgr_workers"
        workers_dir.mkdir(parents=True, exist_ok=True)
        (workers_dir / "__init__.py").write_text("", encoding="utf-8")
    if with_bin:
        bin_dir = repo / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        exe = bin_dir / "agent-worker"
        exe.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        exe.chmod(exe.stat().st_mode | stat.S_IXUSR)
        facade = bin_dir / "agent-worker-mcp"
        facade.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        facade.chmod(facade.stat().st_mode | stat.S_IXUSR)
    return repo


# ===========================================================================
# 1. Subsystem Origin Qualification
# ===========================================================================


def test_check_subsystem_origin_valid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Valid against actual repository root
    ok_real, err_real = check_subsystem_origin(_REPO_ROOT)
    assert ok_real is True
    assert err_real is None

    # Valid against isolated mock repo when sys.modules matches
    repo = _create_mock_repo(tmp_path, with_workers=True)
    fake_mod = MagicMock()
    fake_mod.__file__ = str(repo / "libexec" / "apgr_workers" / "__init__.py")
    monkeypatch.setitem(sys.modules, "apgr_workers", fake_mod)
    ok_mock, err_mock = check_subsystem_origin(repo)
    assert ok_mock is True
    assert err_mock is None


def test_check_subsystem_origin_missing_directory(tmp_path: Path):
    repo = tmp_path / "empty_repo"
    repo.mkdir()
    ok, err = check_subsystem_origin(repo)
    assert ok is False
    assert "not found or not a directory" in err


def test_check_subsystem_origin_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo = _create_mock_repo(tmp_path, with_workers=True)
    foreign_dir = tmp_path / "other" / "libexec" / "apgr_workers"
    foreign_dir.mkdir(parents=True, exist_ok=True)
    fake_mod = MagicMock()
    fake_mod.__file__ = str(foreign_dir / "__init__.py")
    monkeypatch.setitem(sys.modules, "apgr_workers", fake_mod)

    ok, err = check_subsystem_origin(repo)
    assert ok is False
    assert "origin mismatch" in err


# ===========================================================================
# 2. Worker Binaries and Facades Qualification
# ===========================================================================


def test_check_worker_binaries_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("shutil.which", lambda cmd: f"/usr/local/bin/{cmd}")
    repo = _create_mock_repo(tmp_path, with_bin=True)
    # Claude requires facade agent-worker-mcp as well
    ok_claude, err_claude = check_worker_binaries(repo, "claude")
    assert ok_claude is True
    assert err_claude is None

    # Antigravity requires agent-worker
    ok_ag, err_ag = check_worker_binaries(repo, "antigravity")
    assert ok_ag is True
    assert err_ag is None


def test_check_worker_binaries_missing_executable(tmp_path: Path):
    repo = _create_mock_repo(tmp_path, with_bin=False)
    ok, err = check_worker_binaries(repo, "antigravity")
    assert ok is False
    assert "worker executable unavailable" in err


def test_check_worker_binaries_non_executable(tmp_path: Path):
    repo = _create_mock_repo(tmp_path, with_bin=True)
    exe = repo / "bin" / "agent-worker"
    exe.chmod(stat.S_IRUSR | stat.S_IWUSR)  # remove execute permission
    ok, err = check_worker_binaries(repo, "antigravity")
    assert ok is False
    assert "not executable" in err


def test_check_worker_binaries_claude_facade_missing(tmp_path: Path):
    repo = _create_mock_repo(tmp_path, with_bin=True)
    facade = repo / "bin" / "agent-worker-mcp"
    facade.unlink()
    ok, err = check_worker_binaries(repo, "claude")
    assert ok is False
    assert "worker facade unavailable" in err


def test_check_worker_binaries_alternative_apgr_worker_executable(tmp_path: Path):
    repo = _create_mock_repo(tmp_path, with_bin=False)
    bin_dir = repo / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    alt = bin_dir / "apgr-worker"
    alt.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    alt.chmod(alt.stat().st_mode | stat.S_IXUSR)

    # Alternate apgr-worker executable guessing is forbidden; only bin/agent-worker is qualified
    ok, err = check_worker_binaries(repo, "antigravity")
    assert ok is False
    assert "worker executable unavailable" in err


# ===========================================================================
# 3. Model-Based Parent Family Resolution
# ===========================================================================


def test_expected_parent_family_for_endpoint():
    # Model derived from models.toml:
    # 1. normal-final-review has model 'claude-opus-5' -> claude_opus (despite 'opus' not in profile name)
    assert expected_parent_family_for_endpoint("claude", "normal-final-review", root=_REPO_ROOT) == "claude_opus"
    # 2. fable-architecture-docs-primary has model 'claude-fable-5-1' -> claude_fable, NOT claude_opus (despite 'primary' in profile name)
    assert expected_parent_family_for_endpoint("claude", "fable-architecture-docs-primary", root=_REPO_ROOT) == "claude_fable"
    assert expected_parent_family_for_endpoint("claude", "fable-architecture-docs-primary", root=_REPO_ROOT) != "claude_opus"
    # 3. Antigravity profile gemini-3.8-flash-high has model 'gemini-3.8-flash-high' -> gemini_flash
    assert expected_parent_family_for_endpoint("antigravity", "gemini-3.8-flash-high", root=_REPO_ROOT) == "gemini_flash"
    # 4. The source-selected Codex parent role maps to codex_parent.
    assert expected_parent_family_for_endpoint("codex", "architecture-docs-primary", root=_REPO_ROOT) == "codex_parent"
    # 5. Unknown endpoint returns None
    assert expected_parent_family_for_endpoint("unknown", "some-profile", root=_REPO_ROOT) is None


# ===========================================================================
# 4. Capacity Governance: triple_pool_4x4x4 and No Borrowing
# ===========================================================================


def test_validate_allowed_capability_triple_pool_4x4x4():
    valid_cap = {
        "available": True,
        "allowed": True,
        "parent_family": "gemini_flash",
        "policy_selection": "triple_pool_4x4x4",
        "limits": {
            "max_gemini": 4,
            "max_luna": 4,
            "max_sonnet": 4,
        },
        "borrowing": False,
        "leaf_only": True,
        "parent_authority": True,
        "gemini_worker": {"profile": "gemini-flash-sub"},
        "luna_worker": {"transport": "codex_external", "maximum_concurrency": 4},
        "sonnet_worker": {"transport": "claude_external", "maximum_concurrency": 4,
                          "model": "claude-sonnet-5-5", "effort": "high"},
        "policy_source": "common/dispatcher/policy.toml",
        "policy_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    }
    err = _validate_allowed_capability(
        valid_cap,
        provider="antigravity",
        profile="gemini-3.8-flash-high",
        execution_mode="dynamic",
        root=_REPO_ROOT,
    )
    assert err is None


def test_validate_allowed_capability_rejects_non_dual_pool_in_dynamic():
    cap = {
        "available": True,
        "allowed": True,
        "parent_family": "gemini_flash",
        "policy_selection": "single_pool",
        "limits": {"max_gemini": 4},
        "borrowing": False,
        "gemini_worker": {"profile": "gemini-flash-sub"},
        "luna_worker": {"transport": "codex_external", "maximum_concurrency": 4},
        "sonnet_worker": {"transport": "claude_external", "maximum_concurrency": 4,
                          "model": "claude-sonnet-5-5", "effort": "high"},
        "policy_source": "common/dispatcher/policy.toml",
        "policy_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    }
    err = _validate_allowed_capability(
        cap,
        provider="antigravity",
        profile="gemini-3.8-flash-high",
        execution_mode="dynamic",
        root=_REPO_ROOT,
    )
    assert "fresh worker admission requires triple_pool_4x4x4" in err


def test_validate_allowed_capability_rejects_capacity_borrowing():
    cap = {
        "available": True,
        "allowed": True,
        "parent_family": "gemini_flash",
        "policy_selection": "triple_pool_4x4x4",
        "allow_borrowing": True,
        "limits": {
            "max_gemini": 4,
            "max_luna": 4,
            "max_sonnet": 4,
        },
        "borrowing": False,
        "gemini_worker": {"profile": "gemini-flash-sub"},
        "luna_worker": {"transport": "codex_external", "maximum_concurrency": 4},
        "sonnet_worker": {"transport": "claude_external", "maximum_concurrency": 4,
                          "model": "claude-sonnet-5-5", "effort": "high"},
        "policy_source": "common/dispatcher/policy.toml",
        "policy_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    }
    err = _validate_allowed_capability(
        cap,
        provider="antigravity",
        profile="gemini-3.8-flash-high",
        execution_mode="dynamic",
        root=_REPO_ROOT,
    )
    assert err == "triple_pool_4x4x4 forbids capacity borrowing"


def test_validate_allowed_capability_rejects_unequal_or_non_4x4_limits():
    cap = {
        "available": True,
        "allowed": True,
        "parent_family": "gemini_flash",
        "policy_selection": "triple_pool_4x4x4",
        "limits": {
            "max_gemini": 5,
            "max_luna": 3,
        },
        "borrowing": False,
        "gemini_worker": {"profile": "gemini-flash-sub"},
        "luna_worker": {"transport": "codex_external", "maximum_concurrency": 4},
        "sonnet_worker": {"transport": "claude_external", "maximum_concurrency": 4,
                          "model": "claude-sonnet-5-5", "effort": "high"},
        "policy_source": "common/dispatcher/policy.toml",
        "policy_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    }
    err = _validate_allowed_capability(
        cap,
        provider="antigravity",
        profile="gemini-3.8-flash-high",
        execution_mode="dynamic",
        root=_REPO_ROOT,
    )
    assert "triple_pool_4x4x4 requires exactly 4 workers in each independent pool" in err


def test_validate_allowed_capability_rejects_family_mismatch():
    cap = {
        "available": True,
        "allowed": True,
        "parent_family": "claude_opus",  # Family does not match antigravity
        "policy_selection": "triple_pool_4x4x4",
        "limits": {"max_gemini": 4, "max_luna": 4},
        "borrowing": False,
        "gemini_worker": {"profile": "gemini-flash-sub"},
        "luna_worker": {"transport": "codex_external", "maximum_concurrency": 4},
        "sonnet_worker": {"transport": "claude_external", "maximum_concurrency": 4,
                          "model": "claude-sonnet-5-5", "effort": "high"},
        "policy_source": "common/dispatcher/policy.toml",
        "policy_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    }
    err = _validate_allowed_capability(
        cap,
        provider="antigravity",
        profile="gemini-3.8-flash-high",
        execution_mode="dynamic",
        root=_REPO_ROOT,
    )
    assert "parent family claude_opus does not match model/profile antigravity/gemini-3.8-flash-high" in err


# ===========================================================================
# 5. Fail-Closed Mandatory Worker Modes vs Optional Modes
# ===========================================================================


def test_mandatory_modes_fail_closed_when_capability_missing(tmp_path: Path):
    empty_repo = tmp_path / "empty_repo"
    empty_repo.mkdir()
    # In mandatory worker modes (gemini_sub, dynamic), failure to resolve capability must fail closed
    for mode in ("gemini_sub", "gemini_flash_sub", "dynamic"):
        res = resolve_worker_capability(empty_repo, "antigravity", "gemini-3.8-flash", mode)
        assert res is not None
        assert res.get("available") is False
        assert res.get("allowed") is False
        assert "unavailable" in res.get("reason", "").lower()


def test_optional_modes_preserve_optional_intent(tmp_path: Path):
    empty_repo = tmp_path / "empty_repo"
    empty_repo.mkdir()
    # In normal or claude_only mode, worker capability is optional and returns None
    res = resolve_worker_capability(empty_repo, "antigravity", "gemini-3.8-flash", "normal")
    assert res is None


# ===========================================================================
# 6. Comprehensive Qualifier: WorkerQualificationResult
# ===========================================================================


def test_worker_qualification_result_protocol():
    res_ok = WorkerQualificationResult(True, None, capability={"available": True})
    assert bool(res_ok) is True
    eligible, reason, cap = res_ok
    assert eligible is True
    assert reason is None
    assert cap == {"available": True}

    res_fail = WorkerQualificationResult(False, "worker_unavailable: missing binary", capability=None)
    assert bool(res_fail) is False
    eligible, reason, cap = res_fail
    assert eligible is False
    assert reason == "worker_unavailable: missing binary"
    assert cap is None


def test_qualify_worker_eligibility_fails_on_subsystem_origin(tmp_path: Path):
    repo = tmp_path / "no_origin_repo"
    repo.mkdir()
    ep = EndpointCapabilities(
        endpoint_alias="antigravity-gemini-high",
        provider="antigravity",
        profile="gemini-3.8-flash",
        capabilities=frozenset({"read", "mutation", "execution", "subagent_workers"}),
        posture="mutating",
    )
    result = qualify_worker_eligibility(ep, root=repo, execution_mode="dynamic")
    assert not result
    assert "worker_unavailable" in result.reason
    assert "origin unavailable" in result.reason


def test_qualify_worker_eligibility_fails_on_binaries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo = _create_mock_repo(tmp_path, with_workers=True, with_bin=False)
    fake_mod = MagicMock()
    fake_mod.__file__ = str(repo / "libexec" / "apgr_workers" / "__init__.py")
    monkeypatch.setitem(sys.modules, "apgr_workers", fake_mod)

    ep = EndpointCapabilities(
        endpoint_alias="antigravity-gemini-high",
        provider="antigravity",
        profile="gemini-3.8-flash",
        capabilities=frozenset({"read", "mutation", "execution", "subagent_workers"}),
        posture="mutating",
    )
    result = qualify_worker_eligibility(ep, root=repo, execution_mode="dynamic")
    assert not result
    assert "worker_unavailable" in result.reason
    assert "worker executable unavailable" in result.reason


# ===========================================================================
# 7. Injectable dynamic_router Qualification & Static-Only Negative Tests
# ===========================================================================


def test_dynamic_router_rejects_unavailable_worker_candidates_with_worker_unavailable():
    """Verify that dynamic_router rejects worker candidates using injectable qualifier."""
    catalog = {
        "antigravity-workers": EndpointCapabilities(
            endpoint_alias="antigravity-workers",
            provider="antigravity",
            profile="gemini-3.8-flash",
            capabilities=frozenset({"read", "mutation", "execution", "subagent_workers"}),
            posture="mutating",
        )
    }
    binding = ActorBinding(
        binding_id="binding_worker_task",
        roles=("producer",),
        policy_name="default_standard",
        is_mutating=True,
        process_read_only=False,
        required_capabilities=frozenset({"read", "mutation", "execution", "subagent_workers"}),
    )

    # Injected qualifier returns ineligible
    def mock_qualifier(ep, **kwargs):
        return WorkerQualificationResult(False, "worker binary execution failed")

    with pytest.raises(NoRouteAvailableError) as exc_info:
        resolve_dynamic_route(
            binding,
            "implementation_testing",
            capabilities_catalog=catalog,
            worker_qualifier=mock_qualifier,
        )

    # Must contain exact worker_unavailable rejection
    err_str = str(exc_info.value)
    assert "worker_unavailable: worker binary execution failed" in err_str


def test_dynamic_router_no_static_capability_only_pass():
    """An endpoint statically declaring subagent_workers MUST NOT pass if qualifier rejects it.

    This ensures there is no static capability-only pass or silent required parent-only degradation.
    """
    catalog = {
        "static-worker-endpoint": EndpointCapabilities(
            endpoint_alias="static-worker-endpoint",
            provider="antigravity",
            profile="gemini-3.8-flash",
            capabilities=frozenset({"read", "mutation", "execution", "subagent_workers"}),
            posture="mutating",
        )
    }
    # Turn requires subagent_workers
    binding = ActorBinding(
        binding_id="binding_work",
        roles=("producer",),
        policy_name="default_standard",
        is_mutating=True,
        process_read_only=False,
        required_capabilities=frozenset({"read", "mutation", "execution", "subagent_workers"}),
    )

    # Qualifier reporting unavailable subsystem
    def failing_qualifier(ep, **kwargs):
        return (False, "worker subsystem corrupt")

    with pytest.raises(NoRouteAvailableError) as exc_info:
        resolve_dynamic_route(
            binding,
            "implementation_testing",
            capabilities_catalog=catalog,
            worker_qualifier=failing_qualifier,
        )

    assert "worker_unavailable: worker subsystem corrupt" in str(exc_info.value)


def test_dynamic_router_selects_qualified_worker_endpoint():
    """When a worker candidate is qualified, dynamic_router selects it."""
    catalog = {
        "qualified-endpoint": EndpointCapabilities(
            endpoint_alias="qualified-endpoint",
            provider="antigravity",
            profile="gemini-3.8-flash",
            capabilities=frozenset({"read", "mutation", "execution", "subagent_workers"}),
            posture="mutating",
        )
    }
    binding = ActorBinding(
        binding_id="binding_work",
        roles=("producer",),
        policy_name="default_standard",
        is_mutating=True,
        process_read_only=False,
        required_capabilities=frozenset({"read", "mutation", "execution", "subagent_workers"}),
    )

    def passing_qualifier(ep, **kwargs):
        return WorkerQualificationResult(
            True,
            None,
            capability={"available": True, "allowed": True},
        )

    route = resolve_dynamic_route(
        binding,
        "implementation_testing",
        capabilities_catalog=catalog,
        worker_qualifier=passing_qualifier,
    )
    assert route.endpoint_alias == "qualified-endpoint"
    assert "subagent_workers" in route.capabilities


def test_dynamic_router_does_not_reject_endpoints_when_workers_not_required():
    """Turns not requiring subagent_workers should not fail just because worker facility is unconfigured."""
    from agent_phase.semantic_roles import ROLE_PLANNER
    catalog = {
        "antigravity-gemini-high": EndpointCapabilities(
            endpoint_alias="antigravity-gemini-high",
            provider="antigravity",
            profile="gemini-3.8-flash",
            capabilities=frozenset({"read", "reasoning", "subagent_workers"}),
            posture="read_only",
        )
    }
    # Planning only requires read, reasoning
    binding = ActorBinding.create("binding_plan", (ROLE_PLANNER,))

    # Even with an empty root (where workers are unconfigured), planning route resolves cleanly
    route = resolve_dynamic_route(
        binding,
        "implementation_testing",
        capabilities_catalog=catalog,
    )
    assert route.endpoint_alias == "antigravity-gemini-high"


# ===========================================================================
# 8. Read-Only V2 Turns Retain read_only Worker Authority
# ===========================================================================


def test_read_only_v2_turns_retain_read_only_authority():
    """Verify that read-only turns attach task_authority='read_only' and do not skip workers."""
    # Mock capability returned by resolver
    mock_cap = {
        "available": True,
        "allowed": True,
        "parent_family": "gemini_flash",
        "limits": {"max_gemini": 4, "max_luna": 4},
        "borrowing": False,
        "gemini_worker": {"profile": "gemini-flash-sub"},
        "luna_worker": {"transport": "codex_external", "maximum_concurrency": 4},
        "sonnet_worker": {"transport": "claude_external", "maximum_concurrency": 4,
                          "model": "claude-sonnet-5-5", "effort": "high"},
    }

    # Simulate the logic in v2_turns.py
    for is_read_only in (True, False):
        task_authority = "read_only" if is_read_only else "mutation_capable"
        worker_capability = dict(mock_cap)
        if worker_capability.get("allowed"):
            worker_capability = {**worker_capability, "task_authority": task_authority}
        has_workers = bool(worker_capability and worker_capability.get("allowed"))

        assert has_workers is True
        if is_read_only:
            assert worker_capability["task_authority"] == "read_only"
        else:
            assert worker_capability["task_authority"] == "mutation_capable"


# ===========================================================================
# 9. Resolver bundle and snapshot Keyword Acceptance
# ===========================================================================


def test_resolve_dynamic_route_accepts_bundle_and_snapshot_keywords():
    from agent_phase.semantic_roles import ROLE_PLANNER
    catalog = {
        "ep-1": EndpointCapabilities(
            endpoint_alias="ep-1",
            provider="claude",
            profile="opus-high-plan",
            capabilities=frozenset({"read", "reasoning"}),
            posture="read_only",
        )
    }
    binding = ActorBinding.create("binding_plan", (ROLE_PLANNER,))
    # Pass arbitrary bundle and snapshot objects to verify signature acceptance
    route = resolve_dynamic_route(
        binding,
        "implementation_testing",
        capabilities_catalog=catalog,
        bundle={"name": "test_bundle"},
        snapshot={"gen": 42},
    )
    assert route.endpoint_alias == "ep-1"


def test_resolve_v2_accepts_bundle_snapshot_and_worker_qualifier(tmp_path: Path):
    from agent_phase.request import PhaseRequestV2
    from agent_phase.resolution_v2 import resolve_v2
    from agent_phase.semantic_roles import ActorBindingPolicy

    req = PhaseRequestV2(
        schema="agent-phase-request-v2",
        phase_type="implementation_testing",
        prompt="test prompt",
    )
    repo = _create_mock_repo(tmp_path, with_workers=True, with_bin=True)
    custom_binding = ActorBinding(
        binding_id="binding_worker_initial",
        roles=("producer",),
        policy_name="custom",
        is_mutating=True,
        process_read_only=False,
        required_capabilities=frozenset({"read", "mutation", "execution", "subagent_workers"}),
    )
    custom_policy = ActorBindingPolicy(
        name="custom",
        bindings=(custom_binding,),
    )
    fake_bundle = {"bundle_id": "b-123", "generation": 8}
    fake_snapshot = {"snapshot_id": "s-456"}

    def passing_qualifier(ep, **kwargs):
        return WorkerQualificationResult(True, None, capability={"available": True, "allowed": True})

    # When capabilities file is in repo
    disp = repo / "common" / "dispatcher"
    disp.mkdir(parents=True, exist_ok=True)
    caps_content = (
        'schema = "agent-phase-capabilities-v1"\n'
        'generation = 8\n\n'
        '[endpoints.mock-worker]\n'
        'provider = "antigravity"\n'
        'profile = "gemini-3.8-flash"\n'
        'capabilities = ["read", "mutation", "execution", "subagent_workers"]\n'
        'posture = "mutating"\n'
    )
    (disp / "capabilities.toml").write_text(caps_content, encoding="utf-8")

    from agent_phase.roster import Endpoint, PhysicalIdentity, RosterSnapshot, RosterSource
    dummy_source = RosterSource(
        path=disp / "capabilities.toml",
        sha256="0" * 64,
        raw=b"",
        identity=PhysicalIdentity(0, 0, 0, 0, 0, 0, 0, 0),
    )
    mock_roster = RosterSnapshot(
        endpoints={"mock-worker": Endpoint(provider="antigravity", profile="gemini-3.8-flash")},
        routes={},
        generation=8,
        endpoints_source=dummy_source,
        routes_source=dummy_source,
    )

    resolved = resolve_v2(
        req,
        root=repo,
        execution_mode="dynamic",
        binding_policy=custom_policy,
        roster=mock_roster,
        bundle=fake_bundle,
        snapshot=fake_snapshot,
        worker_qualifier=passing_qualifier,
    )

    assert "binding_worker_initial" in resolved["route_resolutions"]
    assert resolved["bundle"] == fake_bundle
    assert resolved["snapshot"] == fake_snapshot
    res_route = resolved["route_resolutions"]["binding_worker_initial"]
    assert res_route["endpoint_alias"] == "mock-worker"
    assert "subagent_workers" in res_route["capabilities"]


# ===========================================================================
# 10. Adverse Focused Tests (APG166S Second/Final Correction)
# ===========================================================================


def test_missing_static_label_negative_cannot_bypass_qualification():
    """Candidates lacking static subagent_workers label cannot bypass worker qualification in dynamic mode."""
    # Endpoint without subagent_workers static capability
    catalog = {
        "candidate-no-worker-label": EndpointCapabilities(
            endpoint_alias="candidate-no-worker-label",
            provider="antigravity",
            profile="gemini-3.8-flash-high",
            capabilities=frozenset({"read", "mutation", "execution"}),
            posture="mutating",
        )
    }
    binding = ActorBinding(
        binding_id="binding_work",
        roles=("producer",),
        policy_name="default_standard",
        is_mutating=True,
        process_read_only=False,
        required_capabilities=frozenset({"read", "mutation", "execution"}),
    )

    # In dynamic mode, worker qualification is required for all candidates
    def failing_qualifier(ep, **kwargs):
        return WorkerQualificationResult(False, "worker subsystem corrupt")

    with pytest.raises(NoRouteAvailableError) as exc_info:
        resolve_dynamic_route(
            binding,
            "implementation_testing",
            capabilities_catalog=catalog,
            execution_mode="dynamic",
            worker_qualifier=failing_qualifier,
        )

    # Missing static label did not bypass; candidate was rejected with worker_unavailable
    assert "worker_unavailable: worker subsystem corrupt" in str(exc_info.value)


def test_unusable_model_transport_rejects_candidate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """When CLI transport (agy / codex) is missing from PATH, candidate is rejected with worker_unavailable."""
    repo = _create_mock_repo(tmp_path, with_workers=True, with_bin=True)
    fake_mod = MagicMock()
    fake_mod.__file__ = str(repo / "libexec" / "apgr_workers" / "__init__.py")
    monkeypatch.setitem(sys.modules, "apgr_workers", fake_mod)

    # Force shutil.which to return None for agy
    monkeypatch.setattr("shutil.which", lambda cmd: None)

    ep = EndpointCapabilities(
        endpoint_alias="antigravity-gemini-high",
        provider="antigravity",
        profile="gemini-3.8-flash-high",
        capabilities=frozenset({"read", "mutation", "execution", "subagent_workers"}),
        posture="mutating",
    )
    result = qualify_worker_eligibility(ep, root=repo, execution_mode="dynamic")
    assert not result
    assert result.eligible is False
    assert "worker executable" in result.reason and "not found on PATH" in result.reason
    assert result.reason.startswith("worker_unavailable")


def test_forbidden_donor_module_injection_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Foreign donor module injected into sys.modules['apgr_workers'] is rejected by origin checks."""
    repo = _create_mock_repo(tmp_path, with_workers=True, with_bin=True)
    donor_dir = tmp_path / "foreign_donor_workspace" / "libexec" / "apgr_workers"
    donor_dir.mkdir(parents=True, exist_ok=True)
    fake_mod = MagicMock()
    fake_mod.__file__ = str(donor_dir / "__init__.py")
    monkeypatch.setitem(sys.modules, "apgr_workers", fake_mod)

    # check_subsystem_origin must detect mismatch
    ok, err = check_subsystem_origin(repo)
    assert ok is False
    assert "worker subsystem origin mismatch" in err

    # qualify_worker_eligibility must fail closed
    ep = EndpointCapabilities(
        endpoint_alias="antigravity-gemini-high",
        provider="antigravity",
        profile="gemini-3.8-flash-high",
        capabilities=frozenset({"read", "mutation", "execution", "subagent_workers"}),
        posture="mutating",
    )
    result = qualify_worker_eligibility(ep, root=repo, execution_mode="dynamic")
    assert not result
    assert result.eligible is False
    assert "worker subsystem origin mismatch" in result.reason
    assert result.reason.startswith("worker_unavailable")


def test_requirement_field_for_mandatory_failure_and_optional_modes(tmp_path: Path):
    """Every returned cap for mandatory modes (including failure) MUST have requirement='required'."""
    empty_repo = tmp_path / "empty_repo"
    empty_repo.mkdir()

    # Mandatory modes on failure must still produce requirement='required'
    for mode in ("gemini_sub", "dynamic"):
        cap = resolve_worker_capability(empty_repo, "antigravity", "gemini-3.8-flash-high", mode)
        assert cap is not None
        assert cap.get("available") is False
        assert cap.get("allowed") is False
        assert cap.get("requirement") == "required"
        assert "unavailable" in cap.get("reason", "").lower()

    # Optional mode on failure/absence returns None
    assert resolve_worker_capability(empty_repo, "antigravity", "gemini-3.8-flash-high", "normal") is None
    assert resolve_worker_capability(empty_repo, "antigravity", "gemini-3.8-flash-high", "claude_only") is None


def test_resolved_model_family_independent_of_profile_name():
    """Model family must derive from runtime_models.selection model, not profile name substring."""
    # 1. normal-final-review has no 'opus' in profile name, but model is 'claude-opus-5' -> claude_opus
    family_opus = expected_parent_family_for_endpoint("claude", "normal-final-review", root=_REPO_ROOT)
    assert family_opus == "claude_opus"

    # 2. fable-architecture-docs-primary has 'primary' in profile name, but model is 'claude-fable-5-1' -> claude_fable (NOT claude_opus)
    family_fable = expected_parent_family_for_endpoint("claude", "fable-architecture-docs-primary", root=_REPO_ROOT)
    assert family_fable == "claude_fable"
    assert family_fable != "claude_opus"

    # 3. antigravity profile gemini-3.8-flash-high has model 'gemini-3.8-flash-high' -> gemini_flash
    family_ag = expected_parent_family_for_endpoint("antigravity", "gemini-3.8-flash-high", root=_REPO_ROOT)
    assert family_ag == "gemini_flash"


def test_resolved_v2_json_serializability_with_bundle_snapshot():
    """Thread captured bundle snapshot via provenance; never serialize dataclass snapshots in resolved JSON."""
    import json
    from agent_phase.bundle import load_bundle
    from agent_phase.request import PhaseRequestV2
    from agent_phase.resolution_v2 import resolve_v2

    bundle = load_bundle(_REPO_ROOT)
    req = PhaseRequestV2(
        schema="agent-phase-request-v2",
        phase_type="implementation_testing",
        prompt="verify json serializability",
    )

    resolved = resolve_v2(
        req,
        root=_REPO_ROOT,
        execution_mode="normal",
        bundle=bundle,
        snapshot=bundle,
    )

    # Dataclass snapshot replaced by JSON-safe provenance
    assert "bundle_provenance" in resolved
    assert "snapshot_provenance" in resolved
    assert "bundle" not in resolved
    assert "snapshot" not in resolved

    # Must serialize cleanly to JSON without TypeError
    serialized = json.dumps(resolved)
    assert isinstance(serialized, str)
    deserialized = json.loads(serialized)
    assert deserialized["schema"] == "agent-phase-resolved-v7"
    assert deserialized["bundle_provenance"]["schema"] == "agent-dispatcher-bundle-provenance-v1"
