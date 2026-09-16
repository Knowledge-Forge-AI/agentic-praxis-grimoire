"""Unit tests for the standalone provider-result failure classifier."""

from __future__ import annotations

from datetime import datetime, timezone
import time

from agent_phase.failure_classifier import (
    CATEGORY_AUTHENTICATION_UNUSABLE,
    CATEGORY_QUOTA_EXHAUSTED,
    CATEGORY_RATE_LIMITED,
    CATEGORY_STARTUP_UNAVAILABLE,
    CATEGORY_TRANSPORT_FAILURE,
    CATEGORY_UNKNOWN_FAILURE,
    CONFIDENCE_EXACT,
    CONFIDENCE_FALLBACK,
    DEFAULT_QUOTA_FALLBACK_TTL,
    MAX_RESET_HORIZON_SECONDS,
    ROUTER_MAPPING_BY_CATEGORY,
    classify_provider_result,
    is_recognized_codex_quota_banner_only,
    parse_codex_reset_hint,
    sanitize_evidence,
)


CAPTURED_CODEX_FIXTURE = """
ERROR: You've hit your usage limit. Visit
https://chatgpt.com/codex/settings/usage to purchase more credits or try again
at Sep 19th, 2026 8:20 AM.
"""


def test_captured_codex_fixture_classification() -> None:
    now = time.time()
    stderr = CAPTURED_CODEX_FIXTURE.strip().encode("utf-8")
    stdout = b""

    classification = classify_provider_result(
        "codex",
        profile="primary",
        exit_code=1,
        stdout=stdout,
        stderr=stderr,
        attempt_id="att-test-1",
        now=now,
    )

    assert classification.category == CATEGORY_QUOTA_EXHAUSTED
    assert classification.confidence == CONFIDENCE_EXACT
    assert classification.provider == "codex"
    assert classification.profile is None  # Provider-wide exhaustion
    assert classification.is_provider_wide is True
    assert classification.is_pre_substantive_reroutable is True
    assert classification.exit_code == 1
    assert len(classification.observations_to_persist) == 1

    obs = classification.observations_to_persist[0]
    assert obs.observation_type == "quota"
    assert obs.provider == "codex"
    assert obs.profile is None
    assert obs.state_value == "exhausted"
    assert obs.digest is not None
    assert obs.expires_at is not None
    assert obs.expires_at > now
    assert obs.observation_id == "obs-result-quota_exhausted-codex-att-test-1"


def test_codex_reset_hint_ordinal_parsing() -> None:
    ref_now = datetime(2026, 9, 17, 0, 0, 0, tzinfo=timezone.utc).timestamp()
    hint = "Sep 19th, 2026 8:20 AM"

    ts, tz_assumption = parse_codex_reset_hint(hint, ref_now, tz=timezone.utc)
    assert ts is not None
    assert tz_assumption == "explicit_timezone:UTC"

    expected = datetime(2026, 9, 19, 8, 20, 0, tzinfo=timezone.utc).timestamp()
    assert ts == expected


def test_codex_reset_hint_boundary_conditions() -> None:
    ref_now = datetime(2026, 9, 17, 0, 0, 0, tzinfo=timezone.utc).timestamp()

    # Past timestamp -> rejected (returns None)
    past_hint = "Sep 10th, 2026 8:20 AM"
    ts_past, _ = parse_codex_reset_hint(past_hint, ref_now, tz=timezone.utc)
    assert ts_past is None

    # Over-horizon timestamp (> 7 days) -> capped at max horizon
    distant_hint = "Oct 25th, 2026 8:20 AM"
    ts_distant, _ = parse_codex_reset_hint(distant_hint, ref_now, tz=timezone.utc)
    assert ts_distant is not None
    assert ts_distant == ref_now + MAX_RESET_HORIZON_SECONDS

    # Unparseable timestamp -> returns None
    unparseable_hint = "next tuesday sometime"
    ts_invalid, _ = parse_codex_reset_hint(unparseable_hint, ref_now, tz=timezone.utc)
    assert ts_invalid is None


def test_unparseable_codex_hint_uses_fallback_ttl() -> None:
    now = time.time()
    stderr = b"ERROR: You've hit your usage limit. Visit https://chatgpt.com/codex/settings/usage to purchase more credits or try again at unknown."
    classification = classify_provider_result(
        "codex",
        profile="primary",
        exit_code=1,
        stdout=b"",
        stderr=stderr,
        attempt_id="att-test-fallback",
        now=now,
    )
    assert classification.category == CATEGORY_QUOTA_EXHAUSTED
    assert len(classification.observations_to_persist) == 1
    obs = classification.observations_to_persist[0]
    assert abs(obs.expires_at - (now + DEFAULT_QUOTA_FALLBACK_TTL)) < 2.0


def test_unverified_claude_errors_stay_unknown_fallback_and_non_reroutable() -> None:
    now = time.time()
    cls_quota = classify_provider_result(
        "claude",
        profile="review",
        exit_code=1,
        stdout=b"",
        stderr=b"Error: credit balance is too low to fulfill request",
        attempt_id="att-claude-1",
        now=now,
    )
    assert cls_quota.category == CATEGORY_UNKNOWN_FAILURE
    assert cls_quota.confidence == CONFIDENCE_FALLBACK
    assert cls_quota.is_pre_substantive_reroutable is False
    assert len(cls_quota.observations_to_persist) == 0


def test_unverified_antigravity_errors_stay_unknown_fallback_and_non_reroutable() -> None:
    now = time.time()
    cls_quota = classify_provider_result(
        "antigravity",
        profile="primary",
        exit_code=1,
        stdout=b"",
        stderr=b"status: RESOURCE_EXHAUSTED: Quota exceeded for project",
        attempt_id="att-agy-1",
        now=now,
    )
    assert cls_quota.category == CATEGORY_UNKNOWN_FAILURE
    assert cls_quota.confidence == CONFIDENCE_FALLBACK
    assert cls_quota.is_pre_substantive_reroutable is False
    assert len(cls_quota.observations_to_persist) == 0


def test_agent_controlled_stdout_cannot_forge_provider_authority() -> None:
    """Scope B / HIGH-1: Agent prose on stdout mentioning quota/limits is NOT provider authority."""
    now = time.time()
    # Stdout contains the quota banner string mixed with model reasoning
    forged_stdout = (
        b"Here is my explanation of the problem:\n"
        b"ERROR: You've hit your usage limit. Visit https://chatgpt.com/codex/settings/usage to purchase more credits\n"
        b"or try again at Sep 19th, 2026 8:20 AM.\n"
        b"We should fix this in code.\n"
    )
    classification = classify_provider_result(
        "codex",
        profile="primary",
        exit_code=1,
        stdout=forged_stdout,
        stderr=b"Exit with status 1",
        attempt_id="att-forge-1",
        now=now,
    )
    assert classification.category == CATEGORY_UNKNOWN_FAILURE
    assert classification.confidence == CONFIDENCE_FALLBACK
    assert classification.is_pre_substantive_reroutable is False
    assert len(classification.observations_to_persist) == 0


def test_non_operational_model_prose_does_not_classify() -> None:
    now = time.time()
    model_prose = b"I noticed your system has a quota limit on database connections. Let's optimize that."
    classification = classify_provider_result(
        "codex",
        profile="primary",
        exit_code=1,
        stdout=model_prose,
        stderr=b"Failed with error code 1",
        attempt_id="att-test-prose",
        now=now,
    )
    assert classification.category == CATEGORY_UNKNOWN_FAILURE
    assert classification.confidence == CONFIDENCE_FALLBACK
    assert classification.is_pre_substantive_reroutable is False
    assert len(classification.observations_to_persist) == 0


def test_sanitize_evidence_redacts_credentials() -> None:
    raw = "ERROR: Failed with sk-abc1234567890abcdef and Bearer eyJhbGciOiJIUzI1Ni. Token: secret='super_secret_123'"
    sanitized = sanitize_evidence(raw)
    assert "sk-abc1234567890abcdef" not in sanitized
    assert "sk-[REDACTED]" in sanitized
    assert "eyJhbGci" not in sanitized
    assert "Bearer [REDACTED]" in sanitized
    assert "super_secret_123" not in sanitized


def test_duplicate_error_lines_deduplicated_in_sanitized_excerpt() -> None:
    raw = "ERROR: You've hit your usage limit.\nERROR: You've hit your usage limit.\nERROR: You've hit your usage limit."
    sanitized = sanitize_evidence(raw)
    assert sanitized == "ERROR: You've hit your usage limit."


def test_scope_e_mapping_table_completeness() -> None:
    """Proves the classifier->router mapping table conforms to Scope E / Finding F6 and drives classifier."""
    assert ROUTER_MAPPING_BY_CATEGORY[CATEGORY_QUOTA_EXHAUSTED] == ("quota", "exhausted", True)
    assert ROUTER_MAPPING_BY_CATEGORY[CATEGORY_AUTHENTICATION_UNUSABLE] == ("authentication", "unusable", False)
    assert ROUTER_MAPPING_BY_CATEGORY[CATEGORY_STARTUP_UNAVAILABLE] == ("availability", "unavailable", False)
    assert ROUTER_MAPPING_BY_CATEGORY[CATEGORY_RATE_LIMITED] == ("cooldown", "active_cooldown", False)
    assert ROUTER_MAPPING_BY_CATEGORY[CATEGORY_TRANSPORT_FAILURE] == ("availability", "unavailable", False)
    assert ROUTER_MAPPING_BY_CATEGORY[CATEGORY_UNKNOWN_FAILURE] == ("unknown", "unknown", False)

    # Verify classify_provider_result actually derives observation values from ROUTER_MAPPING_BY_CATEGORY (MED-10)
    now = time.time()
    cls_exact = classify_provider_result(
        "codex", profile="primary", exit_code=1, stdout=b"",
        stderr=CAPTURED_CODEX_FIXTURE.strip().encode("utf-8"), attempt_id="att-map-1", now=now,
    )
    expected_type, expected_state, _ = ROUTER_MAPPING_BY_CATEGORY[cls_exact.category]
    assert cls_exact.observations_to_persist[0].observation_type == expected_type
    assert cls_exact.observations_to_persist[0].state_value == expected_state


def test_quota_banner_only_recognition_f1() -> None:
    """Finding F1: Proves banner-only stdout is identified as pre-substantive while banner-plus-output is substantive."""
    banner_only = b"ERROR: You've hit your usage limit. Visit https://chatgpt.com/codex/settings/usage to purchase more credits or try again at Sep 19th, 2026 8:20 AM."
    assert is_recognized_codex_quota_banner_only(banner_only) is True

    banner_with_agent_prose = banner_only + b"\nHere is the partial code I was writing:\ndef foo(): pass\n"
    assert is_recognized_codex_quota_banner_only(banner_with_agent_prose) is False

    empty_stdout = b""
    assert is_recognized_codex_quota_banner_only(empty_stdout) is False
