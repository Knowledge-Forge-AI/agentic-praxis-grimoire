"""Unit tests for Request V2 dynamic reroute, failure handling, and retry bounds."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from agent_phase.capabilities import EndpointCapabilities
from agent_phase.dynamic_router import OperationalObservation
from agent_phase.failure_classifier import CATEGORY_QUOTA_EXHAUSTED
from agent_phase.persistence import (
    get_invocation_attempts,
    get_semantic_responsibilities,
    record_invocation_attempt,
    open_dispatcher_db,
    record_run,
    record_semantic_responsibility,
)
from agent_phase.persistence_feedback import (
    get_active_operational_observations,
    get_invocation_observation_relations,
)
from agent_phase.semantic_roles import ActorBinding, ROLE_PRODUCER
from agent_phase.v2_reroute import (
    SCHEMA_PROVIDER_FAILURE,
    SCHEMA_ROUTE_DECISION,
    handle_turn_failure,
    is_substantive_failure,
    orchestrate_dynamic_retry,
    validate_provider_failure_payload,
    validate_route_decision_payload,
)

CAPTURED_CODEX_BANNER = (
    b"ERROR: You've hit your usage limit. Visit "
    b"https://chatgpt.com/codex/settings/usage to purchase more credits "
    b"or try again at Sep 19th, 2026 8:20 AM.\n"
)


def _make_ep(alias: str, provider: str, profile: str) -> EndpointCapabilities:
    return EndpointCapabilities(
        endpoint_alias=alias,
        provider=provider,
        profile=profile,
        capabilities=frozenset({"read", "mutation", "execution", "reasoning"}),
        posture="mutating",
    )


def test_substantive_banner_differentiation() -> None:
    """Finding F1: Pure banner on stdout is pre-substantive; banner + output is substantive."""
    tree_clean = "tree-clean-sha"
    tree_dirty = "tree-dirty-sha"

    # Pure quota banner on stdout
    assert is_substantive_failure(tree_clean, tree_clean, CAPTURED_CODEX_BANNER) is False

    # Banner plus model output / agent prose
    mixed_stdout = CAPTURED_CODEX_BANNER + b"\ndef main():\n    print('hello world')\n"
    assert is_substantive_failure(tree_clean, tree_clean, mixed_stdout) is True

    # Empty stdout with tree mutation
    assert is_substantive_failure(tree_clean, tree_dirty, b"") is True

    # Quota banner with tree mutation
    assert is_substantive_failure(tree_clean, tree_dirty, CAPTURED_CODEX_BANNER) is True


def test_quota_failure_dynamic_reroute(tmp_path: Path) -> None:
    """Turn failure with quota exhaustion persists failure artifact and reroutes to fallback."""
    db_path = tmp_path / "test.db"
    conn = open_dispatcher_db(db_path)
    run_id = "run-reroute-1"
    run_dir = tmp_path / "run_dir"
    run_dir.mkdir()

    record_run(
        conn,
        run_id=run_id,
        project="test",
        request_schema="agent-phase-request-v2",
        request_digest="dig1",
        lifecycle="default_v012",
        execution_mode="dynamic",
    )
    record_semantic_responsibility(
        conn,
        id=f"sem-{run_id}-producer",
        run_id=run_id,
        responsibility_name="producer",
        binding_id="binding_work",
        status="running",
    )

    binding = ActorBinding.create("binding_work", (ROLE_PRODUCER,))
    catalog = {
        "codex-ep": _make_ep("codex-ep", "codex", "gpt-5-codex"),
        "claude-ep": _make_ep("claude-ep", "claude", "claude-3-7-sonnet"),
    }

    # Step 1: Record running attempt and handle turn failure
    attempt_id_1 = f"att-{run_id}-binding_work-1"
    record_invocation_attempt(
        conn, attempt_id=attempt_id_1, run_id=run_id, binding_id=binding.binding_id,
        attempt_number=1, provider="codex", profile="gpt-5-codex", endpoint_alias="codex-ep",
        status="running",
    )
    disp = handle_turn_failure(
        conn,
        run_id=run_id,
        run_dir=run_dir,
        binding=binding,
        attempt_id=attempt_id_1,
        attempt_number=1,
        provider="codex",
        profile="gpt-5-codex",
        endpoint_alias="codex-ep",
        exit_code=1,
        stdout_bytes=CAPTURED_CODEX_BANNER,
        stderr_bytes=b"",
        tree_before="tree-init",
        tree_after="tree-init",
        now=1000.0,
    )

    assert disp.substantive is False
    assert disp.retryable is True
    assert disp.category == CATEGORY_QUOTA_EXHAUSTED
    assert Path(disp.artifact_path).exists()

    # Verify failure artifact JSON conforms to closed schema and includes digests/expirations (Scope K)
    fail_data = json.loads(Path(disp.artifact_path).read_text(encoding="utf-8"))
    assert fail_data["schema"] == SCHEMA_PROVIDER_FAILURE
    assert fail_data["retryable"] is True
    assert fail_data["provider"] == "codex"
    assert isinstance(fail_data["observation_digests"], dict)
    assert len(fail_data["observation_digests"]) == 1
    assert isinstance(fail_data["observation_expirations"], dict)
    assert len(fail_data["observation_expirations"]) == 1

    # Verify operational observation persisted in SQLite and relation written (LOW-15)
    active_obs = get_active_operational_observations(conn, now=1000.0)
    assert any(o["provider"] == "codex" and o["state_value"] == "exhausted" for o in active_obs)
    relations = get_invocation_observation_relations(conn, attempt_id=attempt_id_1)
    assert len(relations) == 1
    assert relations[0]["relation_type"] == "produced_by"

    # Step 2: Orchestrate dynamic retry
    rerouted, next_route, next_attempt = orchestrate_dynamic_retry(
        conn,
        run_id=run_id,
        run_dir=run_dir,
        phase_type="implementation_testing",
        execution_mode="dynamic",
        binding=binding,
        current_attempt_number=1,
        current_attempt_id=f"att-{run_id}-binding_work-1",
        caps_catalog=catalog,
        injected_observations=(),
        prior_resolutions={},
        disposition=disp,
        now=1000.0,
    )

    assert rerouted is True
    assert next_route is not None
    assert next_route.provider == "claude"
    assert next_attempt == 2

    # Verify decision artifact JSON conforms to closed schema
    dec_file = run_dir / "route-decision-binding_work-attempt-2.json"
    assert dec_file.exists()
    dec_data = json.loads(dec_file.read_text(encoding="utf-8"))
    assert dec_data["schema"] == SCHEMA_ROUTE_DECISION
    assert dec_data["outcome"] == "rerouted"
    assert dec_data["selected_provider"] == "claude"
    assert dec_data["predecessor_attempt_id"] == f"att-{run_id}-binding_work-1"

    # Verify invocation attempts lineage in SQLite
    attempts = get_invocation_attempts(conn, run_id, binding_id="binding_work")
    assert len(attempts) == 2
    assert attempts[0]["status"] == "failed"
    assert attempts[1]["status"] == "staged"
    assert attempts[1]["predecessor_attempt_id"] == attempts[0]["attempt_id"]


def test_static_mode_does_not_dynamically_reroute(tmp_path: Path) -> None:
    """Retained static modes do not dynamically reroute on failure."""
    db_path = tmp_path / "test.db"
    conn = open_dispatcher_db(db_path)
    run_id = "run-static-fail"
    run_dir = tmp_path / "run_dir"
    run_dir.mkdir()

    record_run(
        conn,
        run_id=run_id,
        project="test",
        request_schema="agent-phase-request-v2",
        request_digest="dig1",
        lifecycle="default_v012",
        execution_mode="direct_static",
    )
    binding = ActorBinding.create("binding_work", (ROLE_PRODUCER,))
    catalog = {
        "codex-ep": _make_ep("codex-ep", "codex", "gpt-5-codex"),
        "claude-ep": _make_ep("claude-ep", "claude", "claude-3-7-sonnet"),
    }

    attempt_id_1 = f"att-{run_id}-binding_work-1"
    record_invocation_attempt(
        conn, attempt_id=attempt_id_1, run_id=run_id, binding_id=binding.binding_id,
        attempt_number=1, provider="codex", profile="gpt-5-codex", endpoint_alias="codex-ep",
        status="running",
    )
    disp = handle_turn_failure(
        conn,
        run_id=run_id,
        run_dir=run_dir,
        binding=binding,
        attempt_id=attempt_id_1,
        attempt_number=1,
        provider="codex",
        profile="gpt-5-codex",
        endpoint_alias="codex-ep",
        exit_code=1,
        stdout_bytes=CAPTURED_CODEX_BANNER,
        stderr_bytes=b"",
        tree_before="t1",
        tree_after="t1",
        now=1000.0,
    )

    rerouted, next_route, _ = orchestrate_dynamic_retry(
        conn,
        run_id=run_id,
        run_dir=run_dir,
        phase_type="implementation_testing",
        execution_mode="direct_static",
        binding=binding,
        current_attempt_number=1,
        current_attempt_id=f"att-{run_id}-binding_work-1",
        caps_catalog=catalog,
        injected_observations=(),
        prior_resolutions={},
        disposition=disp,
        now=1000.0,
    )

    assert rerouted is False
    assert next_route is None

    # Scope I: feedback is persisted in SQLite for future runs even though static mode does not reroute
    active_obs = get_active_operational_observations(conn, now=1000.0)
    assert any(o["provider"] == "codex" and o["state_value"] == "exhausted" for o in active_obs)


def test_retry_bound_m_min_three_routes(tmp_path: Path) -> None:
    """Finding F14: Retry ceiling is M = min(3, |routes|)."""
    db_path = tmp_path / "test.db"
    conn = open_dispatcher_db(db_path)
    run_id = "run-bounds"
    run_dir = tmp_path / "run_dir"
    run_dir.mkdir()

    record_run(
        conn,
        run_id=run_id,
        project="test",
        request_schema="agent-phase-request-v2",
        request_digest="dig1",
        lifecycle="default_v012",
        execution_mode="dynamic",
    )
    binding = ActorBinding.create("binding_work", (ROLE_PRODUCER,))

    # Case A: Only 1 capable endpoint -> M = min(3, 1) = 1. Cannot retry attempt 1!
    catalog_single = {"codex-ep": _make_ep("codex-ep", "codex", "gpt-5-codex")}
    attempt_id_1 = f"att-{run_id}-binding_work-1"
    record_invocation_attempt(
        conn, attempt_id=attempt_id_1, run_id=run_id, binding_id=binding.binding_id,
        attempt_number=1, provider="codex", profile="gpt-5-codex", endpoint_alias="codex-ep",
        status="running",
    )
    disp1 = handle_turn_failure(
        conn,
        run_id=run_id,
        run_dir=run_dir,
        binding=binding,
        attempt_id=attempt_id_1,
        attempt_number=1,
        provider="codex",
        profile="gpt-5-codex",
        endpoint_alias="codex-ep",
        exit_code=1,
        stdout_bytes=CAPTURED_CODEX_BANNER,
        stderr_bytes=b"",
        tree_before="t1",
        tree_after="t1",
        now=1000.0,
    )
    rerouted1, _, _ = orchestrate_dynamic_retry(
        conn,
        run_id=run_id,
        run_dir=run_dir,
        phase_type="implementation_testing",
        execution_mode="dynamic",
        binding=binding,
        current_attempt_number=1,
        current_attempt_id=f"att-{run_id}-binding_work-1",
        caps_catalog=catalog_single,
        injected_observations=(),
        prior_resolutions={},
        disposition=disp1,
        now=1000.0,
    )
    assert rerouted1 is False

    # Case B: 2 capable endpoints -> M = min(3, 2) = 2. Attempt 2 cannot retry further!
    catalog_two = {
        "codex-ep": _make_ep("codex-ep", "codex", "gpt-5-codex"),
        "claude-ep": _make_ep("claude-ep", "claude", "claude-3-7-sonnet"),
    }
    attempt_id_2 = f"att-{run_id}-binding_work-2"
    record_invocation_attempt(
        conn, attempt_id=attempt_id_2, run_id=run_id, binding_id=binding.binding_id,
        attempt_number=2, provider="claude", profile="claude-3-7-sonnet", endpoint_alias="claude-ep",
        status="running",
    )
    disp2 = handle_turn_failure(
        conn,
        run_id=run_id,
        run_dir=run_dir,
        binding=binding,
        attempt_id=attempt_id_2,
        attempt_number=2,
        provider="claude",
        profile="claude-3-7-sonnet",
        endpoint_alias="claude-ep",
        exit_code=1,
        stdout_bytes=b"",
        stderr_bytes=b"Connection error",
        tree_before="t1",
        tree_after="t1",
        now=1050.0,
    )
    rerouted2, _, _ = orchestrate_dynamic_retry(
        conn,
        run_id=run_id,
        run_dir=run_dir,
        phase_type="implementation_testing",
        execution_mode="dynamic",
        binding=binding,
        current_attempt_number=2,
        current_attempt_id=f"att-{run_id}-binding_work-2",
        caps_catalog=catalog_two,
        injected_observations=(),
        prior_resolutions={},
        disposition=disp2,
        now=1050.0,
    )
    assert rerouted2 is False


def test_no_route_available_records_exhausted_decision_artifact(tmp_path: Path) -> None:
    """Scope H / LOW-15: When all routes are excluded, records typed 'exhausted' decision artifact."""
    db_path = tmp_path / "test.db"
    conn = open_dispatcher_db(db_path)
    run_id = "run-no-route"
    run_dir = tmp_path / "run_dir"
    run_dir.mkdir()

    record_run(
        conn,
        run_id=run_id,
        project="test",
        request_schema="agent-phase-request-v2",
        request_digest="dig1",
        lifecycle="default_v012",
        execution_mode="dynamic",
    )
    record_semantic_responsibility(
        conn,
        id=f"sem-{run_id}-{ROLE_PRODUCER}",
        run_id=run_id,
        responsibility_name=ROLE_PRODUCER,
        binding_id="binding_work",
        status="running",
    )
    binding = ActorBinding.create("binding_work", (ROLE_PRODUCER,))
    # Two capable endpoints in catalog, but both will be excluded
    catalog = {
        "codex-ep": _make_ep("codex-ep", "codex", "gpt-5-codex"),
        "claude-ep": _make_ep("claude-ep", "claude", "claude-3-7-sonnet"),
    }
    # Pre-inject claude exhaustion so no eligible fallback remains when codex fails
    claude_exhausted = OperationalObservation(
        observation_id="inj-claude-exhausted",
        producer="operator_manual",
        observation_type="quota",
        provider="claude",
        state_value="exhausted",
        timestamp=1000.0,
        expires_at=2000.0,
    )

    attempt_id = f"att-{run_id}-binding_work-1"
    record_invocation_attempt(
        conn, attempt_id=attempt_id, run_id=run_id, binding_id=binding.binding_id,
        attempt_number=1, provider="codex", profile="gpt-5-codex", endpoint_alias="codex-ep",
        status="running",
    )
    disp = handle_turn_failure(
        conn,
        run_id=run_id,
        run_dir=run_dir,
        binding=binding,
        attempt_id=attempt_id,
        attempt_number=1,
        provider="codex",
        profile="gpt-5-codex",
        endpoint_alias="codex-ep",
        exit_code=1,
        stdout_bytes=CAPTURED_CODEX_BANNER,
        stderr_bytes=b"",
        tree_before="t1",
        tree_after="t1",
        now=1000.0,
    )
    rerouted, next_route, next_attempt = orchestrate_dynamic_retry(
        conn,
        run_id=run_id,
        run_dir=run_dir,
        phase_type="implementation_testing",
        execution_mode="dynamic",
        binding=binding,
        current_attempt_number=1,
        current_attempt_id=attempt_id,
        caps_catalog=catalog,
        injected_observations=(claude_exhausted,),
        prior_resolutions={},
        disposition=disp,
        now=1000.0,
    )
    assert rerouted is False
    assert next_route is None

    # Verify decision artifact was written with outcome="exhausted"
    dec_file = run_dir / "route-decision-binding_work-attempt-2.json"
    assert dec_file.exists()
    dec_data = json.loads(dec_file.read_text(encoding="utf-8"))
    assert dec_data["schema"] == SCHEMA_ROUTE_DECISION
    assert dec_data["outcome"] == "exhausted"
    assert dec_data["selected_provider"] is None

    # Verify semantic responsibilities transitioned to failed
    responsibilities = get_semantic_responsibilities(conn, run_id)
    assert any(r["status"] == "failed" for r in responsibilities)


def test_closed_schema_validation_rejects_extra_or_missing_keys() -> None:
    """Scope K / MED-5: Both provider failure and route decision schemas are strictly closed."""
    valid_failure = {
        "attempt_id": "att-1",
        "attempt_number": 1,
        "binding_id": "b1",
        "confidence": "exact_signature_match",
        "detail": {},
        "endpoint_alias": "ep1",
        "error_message": "err",
        "exit_code": 1,
        "failure_category": "quota_exhausted",
        "failure_id": "fail-att-1",
        "match_basis": "basis",
        "observation_digests": {},
        "observation_expirations": {},
        "observation_ids": [],
        "observed_at": 1000.0,
        "profile": "primary",
        "provider": "codex",
        "reset_hint": None,
        "reset_timestamp": None,
        "retryable": True,
        "run_id": "run-1",
        "schema": SCHEMA_PROVIDER_FAILURE,
        "stderr_sha256": "abc",
        "stdout_sha256": "def",
        "substantive": False,
        "timezone_assumption": None,
    }
    # Valid passes
    validate_provider_failure_payload(valid_failure)

    # Extra key rejected
    extra = dict(valid_failure, unauthorized_field="bad")
    with pytest.raises(ValueError, match="Closed schema violation"):
        validate_provider_failure_payload(extra)

    # Missing key rejected
    missing = {k: v for k, v in valid_failure.items() if k != "attempt_id"}
    with pytest.raises(ValueError, match="Closed schema violation"):
        validate_provider_failure_payload(missing)

    # Invalid schema rejected
    wrong_schema = dict(valid_failure, schema="wrong-schema-v1")
    with pytest.raises(ValueError, match="Invalid schema"):
        validate_provider_failure_payload(wrong_schema)

    valid_decision = {
        "attempt_number": 1,
        "binding_id": "b1",
        "decision_id": "dec-1",
        "decision_timestamp": 1000.0,
        "observation_ids": [],
        "outcome": "rerouted",
        "predecessor_attempt_id": None,
        "rejections": {},
        "run_id": "run-1",
        "schema": SCHEMA_ROUTE_DECISION,
        "selected_endpoint_alias": "ep1",
        "selected_profile": "primary",
        "selected_provider": "codex",
        "selection_rationale": "ok",
    }
    # Valid passes
    validate_route_decision_payload(valid_decision)

    # Extra key rejected
    extra_dec = dict(valid_decision, extra_key="invalid")
    with pytest.raises(ValueError, match="Closed schema violation"):
        validate_route_decision_payload(extra_dec)

    # Missing key rejected
    missing_dec = {k: v for k, v in valid_decision.items() if k != "outcome"}
    with pytest.raises(ValueError, match="Closed schema violation"):
        validate_route_decision_payload(missing_dec)


def test_substantive_stdout_with_quota_text_does_not_persist_or_reroute(tmp_path: Path) -> None:
    """Scope B / HIGH-1: Model prose on stdout quoting quota text cannot forge durable exclusions."""
    db_path = tmp_path / "test.db"
    conn = open_dispatcher_db(db_path)
    run_id = "run-forged"
    run_dir = tmp_path / "run_dir"
    run_dir.mkdir()

    record_run(
        conn,
        run_id=run_id,
        project="test",
        request_schema="agent-phase-request-v2",
        request_digest="dig1",
        lifecycle="default_v012",
        execution_mode="dynamic",
    )
    binding = ActorBinding.create("binding_work", (ROLE_PRODUCER,))
    attempt_id = f"att-{run_id}-binding_work-1"
    record_invocation_attempt(
        conn, attempt_id=attempt_id, run_id=run_id, binding_id=binding.binding_id,
        attempt_number=1, provider="codex", profile="gpt-5-codex", endpoint_alias="codex-ep",
        status="running",
    )

    forged_stdout = (
        CAPTURED_CODEX_BANNER
        + b"\nI encountered an error above, but here is my partial answer:\ndef solve(): pass\n"
    )
    disp = handle_turn_failure(
        conn,
        run_id=run_id,
        run_dir=run_dir,
        binding=binding,
        attempt_id=attempt_id,
        attempt_number=1,
        provider="codex",
        profile="gpt-5-codex",
        endpoint_alias="codex-ep",
        exit_code=1,
        stdout_bytes=forged_stdout,
        stderr_bytes=b"",
        tree_before="t1",
        tree_after="t1",
        now=1000.0,
    )
    assert disp.substantive is True
    assert disp.retryable is False
    assert disp.observation_ids == ()

    # Verify NO operational observations were persisted to SQLite
    active_obs = get_active_operational_observations(conn, now=1000.0)
    assert len(active_obs) == 0

    # Verify failure artifact records substantive=True and empty observation_ids
    fail_data = json.loads(Path(disp.artifact_path).read_text(encoding="utf-8"))
    assert fail_data["substantive"] is True
    assert fail_data["retryable"] is False
    assert fail_data["observation_ids"] == []
    assert fail_data["observation_digests"] == {}

