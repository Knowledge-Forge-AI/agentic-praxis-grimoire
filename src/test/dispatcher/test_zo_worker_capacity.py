"""APG166ZO worker capacity, triple-pool 4x4x4, and native Sonnet lifecycle tests."""

from __future__ import annotations

import concurrent.futures
from pathlib import Path

import pytest

from apgr_workers.inspection import inspect_parent
from apgr_workers.ledger import (
    CapacityExceededError,
    ParentLedger,
    PinnedControllerError,
    PoolPausedError,
)
from apgr_workers.native_capacity import (
    NativeHookContract,
    PINNED_CONTROLLER_DIAGNOSTIC,
    SONNET_AGENT_TYPE,
    TRIPLE_POOL,
)
from apgr_workers.settlement import close_settled


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APGR_WORKER_LEAF", raising=False)


def _init_ledger(tmp_path: Path, parent_id: str, family: str = "codex_parent", policy: str = TRIPLE_POOL) -> ParentLedger:
    ledger = ParentLedger(parent_id, state_dir=tmp_path / "state")
    from apgr_workers.policy import resolve_worker_capability
    endpoint = {"codex_parent": ("codex", "implementation-testing"),
                "claude_opus": ("claude", "opus-high-plan"),
                "claude_fable": ("claude", "fable-architecture-docs-primary"),
                "gemini_flash": ("antigravity", "gemini-3.8-flash-high")}[family]
    cap = resolve_worker_capability(Path(__file__).resolve().parents[3], *endpoint, "gemini_flash_sub")
    cap.update(lifecycle_generation=parent_id)
    ledger.initialize_parent(
        family,
        workspace=tmp_path / "ws",
        task_authority="mutation_capable",
        worker_capability=cap,
    )
    return ledger


def test_concurrent_admission_cap_4(tmp_path: Path) -> None:
    ledger = _init_ledger(tmp_path, "p_concurrent", "claude_opus")
    admitted: list[str] = []
    rejected: list[str] = []

    def _reserve(idx: int) -> None:
        try:
            res = ledger.reserve_native_agent(f"agent_{idx}", SONNET_AGENT_TYPE)
            if res.get("status") == "reserved":
                admitted.append(f"agent_{idx}")
        except CapacityExceededError:
            rejected.append(f"agent_{idx}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(_reserve, i) for i in range(5)]
        concurrent.futures.wait(futures)

    assert len(admitted) == 4
    assert len(rejected) == 1
    status = ledger.get_status()
    assert status["native_count"] == 4


def test_independent_triple_pool_caps_and_no_borrowing(tmp_path: Path) -> None:
    ledger = _init_ledger(tmp_path, "p_independent", "gemini_flash")
    # Admit 4 Gemini
    for i in range(4):
        ledger.reserve_worker(f"g_{i}", f"k_g_{i}", "h" * 64, "mutation_capable", f"/tmp/g_{i}", worker_kind="gemini")
    with pytest.raises(CapacityExceededError, match="Gemini capacity limit reached"):
        ledger.reserve_worker("g_4", "k_g_4", "h" * 64, "mutation_capable", "/tmp/g_4", worker_kind="gemini")

    # Admit 4 Luna (Gemini being full does not block Luna)
    for i in range(4):
        ledger.reserve_worker(f"l_{i}", f"k_l_{i}", "h" * 64, "mutation_capable", f"/tmp/l_{i}", worker_kind="luna")
    with pytest.raises(CapacityExceededError, match="Luna capacity limit reached"):
        ledger.reserve_worker("l_4", "k_l_4", "h" * 64, "mutation_capable", "/tmp/l_4", worker_kind="luna")

    # Admit 4 Sonnet (Gemini and Luna being full does not block Sonnet)
    for i in range(4):
        ledger.reserve_worker(f"s_{i}", f"k_s_{i}", "h" * 64, "mutation_capable", f"/tmp/s_{i}", worker_kind="sonnet")
    with pytest.raises(CapacityExceededError, match="Sonnet capacity limit reached"):
        ledger.reserve_worker("s_4", "k_s_4", "h" * 64, "mutation_capable", "/tmp/s_4", worker_kind="sonnet")

    status = ledger.get_status()
    assert status["gemini_count"] == 4
    assert status["luna_count"] == 4
    assert status["sonnet_count"] == 4
    assert status["aggregate_count"] == 12
    assert status["aggregate_remaining"] == 0


def test_historical_dual_pool_read_drain_refuses_fresh_admission(tmp_path: Path) -> None:
    ledger = ParentLedger("p_historical", state_dir=tmp_path / "state")
    ledger._write_data({"schema": "agent-worker-ledger-v1", "parent_id": "p_historical",
        "status": "active", "parent_family": "codex_astra", "workspace": str(tmp_path / "ws"),
        "task_authority": "mutation_capable", "worker_allowed": True,
        "policy_selection": "dual_pool_4x4", "policy": {"max_gemini": 4, "max_luna": 4, "max_aggregate": 8},
        "worker_capability": {"policy_selection": "dual_pool_4x4"},
        "allowed_worker_kinds": ["gemini"], "gemini_jobs": {}, "native_agents": {}})

    # 1. Inspect readable and never claims Sonnet
    view = inspect_parent("p_historical", state_dir=tmp_path / "state", root=tmp_path)
    assert "sonnet" not in view["pools"]
    assert "gemini" in view["pools"]
    assert "luna" in view["pools"]
    assert "launch_binding_not_recorded" in view["limitations"]

    # 2. Status readable
    status = ledger.get_status()
    assert status["policy_selection"] == "dual_pool_4x4"
    assert "sonnet_count" not in status

    # 3. Fresh reservation strictly refused with PinnedControllerError
    with pytest.raises(PinnedControllerError) as exc_info:
        ledger.reserve_worker("j_fail", "k_fail", "h" * 64, "mutation_capable", "/tmp/t", worker_kind="gemini")
    assert str(exc_info.value) == PINNED_CONTROLLER_DIAGNOSTIC

    with pytest.raises(PinnedControllerError) as exc_native:
        ledger.reserve_native_agent("native_fail", SONNET_AGENT_TYPE)
    assert str(exc_native.value) == PINNED_CONTROLLER_DIAGNOSTIC

    # 4. Settle readable
    reconciled = close_settled(ledger, "settled historical test")
    assert reconciled["status"] == "closed"
    assert reconciled["reconciled"] is True

    # 5. Drain readable
    drain_res = ledger.drain_and_close()
    assert drain_res["status"] == "closed"


def test_pool_quota_pause_independent(tmp_path: Path) -> None:
    ledger = _init_ledger(tmp_path, "p_pause", "gemini_flash")

    # Pause Gemini
    ledger.pause_pool("gemini", "quota exhausted", {"quota_reset": 12345})
    with pytest.raises(PoolPausedError, match="gemini worker pool is paused"):
        ledger.reserve_worker("g_p", "k_g_p", "h" * 64, "mutation_capable", "/tmp/g", worker_kind="gemini")

    # Luna and Sonnet remain unpaused
    res_luna = ledger.reserve_worker("l_p", "k_l_p", "h" * 64, "mutation_capable", "/tmp/l", worker_kind="luna")
    assert res_luna["status"] == "reserved"
    res_sonnet = ledger.reserve_worker("s_p", "k_s_p", "h" * 64, "mutation_capable", "/tmp/s", worker_kind="sonnet")
    assert res_sonnet["status"] == "reserved"

    # Resume Gemini
    ledger.resume_pool("gemini", {"operator_unpause": True})
    res_gemini = ledger.reserve_worker("g_ok", "k_g_ok", "h" * 64, "mutation_capable", "/tmp/g_ok", worker_kind="gemini")
    assert res_gemini["status"] == "reserved"


def test_native_sonnet_claude_lifecycle_and_restrictions(tmp_path: Path) -> None:
    # 1. Rejects non-Claude parent
    codex_ledger = _init_ledger(tmp_path, "p_codex", "codex_parent")
    # For Codex parent, native admission is owned by codex_runtime
    res = codex_ledger.reserve_native_agent("luna_codex", "luna")
    assert res["admission_owner"] == "codex_runtime"

    # 2. Claude parent accepts native Sonnet
    claude_ledger = _init_ledger(tmp_path, "p_claude", "claude_opus")
    # Rejects invalid agent type
    with pytest.raises(CapacityExceededError, match="invalid_agent_type"):
        claude_ledger.reserve_native_agent("invalid_agent", "luna")

    # Reserve valid Sonnet
    admit_res = claude_ledger.reserve_native_agent("s_agent_1", SONNET_AGENT_TYPE)
    assert admit_res["status"] == "reserved"
    assert admit_res["admission_owner"] == "ledger"

    # Activate
    ok, act_reason = claude_ledger.activate_native("s_agent_1", SONNET_AGENT_TYPE)
    assert ok is True
    assert act_reason == "activated"

    # Close
    assert claude_ledger.close_native("s_agent_1") is True

    # Rollback of reserved
    claude_ledger.reserve_native_agent("s_agent_roll", SONNET_AGENT_TYPE)
    assert claude_ledger.rollback_native("s_agent_roll") is True


def test_no_double_release_and_interrupted_retention_until_drain(tmp_path: Path) -> None:
    ledger = _init_ledger(tmp_path, "p_drain", "claude_fable")
    ledger.reserve_native_agent("s_close", SONNET_AGENT_TYPE)
    assert ledger.close_native("s_close") is True
    # Double release prevention: second close returns False
    assert ledger.close_native("s_close") is False

    # Interrupted native child: reserved/active slot remains retained
    ledger.reserve_native_agent("s_interrupted", SONNET_AGENT_TYPE)
    ledger.activate_native("s_interrupted", SONNET_AGENT_TYPE)
    status_before = ledger.get_status()
    assert status_before["native_count"] == 1

    # Drain on parent exit: retains slot until observed parent-exit drain,
    # then transitions to closed with uncertain_cleanup = True
    drain_summary = ledger.drain_and_close()
    assert drain_summary["status"] == "closed"
    assert drain_summary["uncertain_cleanup"] is True


def test_native_hook_contract_and_admission_validation() -> None:
    contract = NativeHookContract()
    assert contract.policy_selection == TRIPLE_POOL
    assert contract.max_concurrency == 4

    # Valid
    valid, msg = contract.validate_request({"agent_type": SONNET_AGENT_TYPE})
    assert valid is True
    assert msg == "valid"

    # Model override disallowed
    valid, msg = contract.validate_request({"agent_type": SONNET_AGENT_TYPE, "model": "claude-opus-4"})
    assert valid is False
    assert "per_call_model_override_disallowed" in msg

    # Background disallowed
    valid, msg = contract.validate_request({"agent_type": SONNET_AGENT_TYPE, "background": True})
    assert valid is False
    assert "background_disallowed" in msg

    # Invalid agent type
    valid, msg = contract.validate_request({"agent_type": "apgr-luna-worker"})
    assert valid is False
    assert "invalid_agent_type" in msg



@pytest.mark.parametrize("schema,selection", [
    ("agent-worker-ledger-v1", "triple_pool_4x4x4"),
    ("agent-worker-ledger-v2", "dual_pool_4x4"),
])
def test_old_and_new_artifact_shapes_cannot_exchange_authority(tmp_path, schema, selection):
    from apgr_workers.ledger import LedgerError
    ledger = ParentLedger("spoof-test", state_dir=tmp_path / "state")
    ledger._write_data({"schema": schema, "parent_id": "spoof-test", "status": "active",
                        "policy_selection": selection, "parent_family": "codex_parent"})
    with pytest.raises(LedgerError):
        ledger.get_status()


def test_empty_external_allowlist_is_not_defaulted(tmp_path):
    from apgr_workers.policy import resolve_worker_capability
    from apgr_workers.ledger import AuthorityViolationError
    cap = resolve_worker_capability(Path(__file__).resolve().parents[3], "claude", "opus-high-plan", "gemini_sub")
    cap["allowed_worker_kinds"] = []
    cap["excluded_worker_kinds"] = ["gemini", "luna"]
    ledger = ParentLedger("native-only", state_dir=tmp_path / "state")
    ledger.initialize_parent("claude_opus", workspace=tmp_path / "workspace",
                             task_authority="read_only", worker_capability=cap)
    assert ledger.get_status()["allowed_worker_kinds"] == []
    with pytest.raises(AuthorityViolationError):
        ledger.reserve_gemini("excluded", "excluded", "payload")
    assert ledger.reserve_native("sonnet-leaf", SONNET_AGENT_TYPE)[0]
