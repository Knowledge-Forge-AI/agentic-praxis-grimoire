"""Focused APG166T-R1 provider-error importer contracts."""
from __future__ import annotations

import json

import pytest

from testing.h_eval import importers


def _jsonl(*events: dict[str, object]) -> bytes:
    return b"".join(json.dumps(event, sort_keys=True).encode() + b"\n" for event in events)


def _claude_route() -> dict[str, str]:
    return {"provider": "claude", "execution": "live"}


def test_retained_authentication_error_keeps_raw_success_subtype_and_error_fields() -> None:
    raw = _jsonl(
        {"type": "system", "subtype": "init", "tools": ["Read"], "model": "claude-opus-5"},
        {
            "type": "assistant",
            "error": "authentication_failed",
            "is_api_error_message": True,
        },
        {
            "type": "result",
            "subtype": "success",
            "is_error": True,
            "terminal_reason": "api_error",
            "api_error_status": None,
            "result": "Not logged in",
        },
    )

    imported = importers.import_claude(raw, _claude_route(), terminal={"exit_code": 1})

    assert imported["provider_terminal_status"] == "success"
    assert imported["provider_error"] == {
        "is_error": True,
        "terminal_reason": "api_error",
        "api_error_status": None,
        "assistant_errors": ["authentication_failed"],
    }
    assert imported["provider_outcome"] == "error"


def test_nonzero_process_is_error_even_when_provider_result_looks_successful() -> None:
    raw = _jsonl(
        {"type": "system", "subtype": "init", "tools": ["Read"]},
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "terminal_reason": "completed",
            "api_error_status": 0,
            "result": "done",
        },
    )

    imported = importers.import_claude(raw, _claude_route(), terminal={"exit_code": 7})

    assert imported["provider_terminal_status"] == "success"
    assert imported["provider_error"]["is_error"] is False
    assert imported["provider_outcome"] == "error"


def test_malformed_or_unrecognized_stream_has_no_provider_outcome() -> None:
    imported = importers.import_claude(
        b'{"type":"result","subtype":"success"',
        _claude_route(),
        terminal={"exit_code": 0},
    )

    assert imported["parse_status"] == "text"
    assert imported["provider_terminal_status"] is None
    assert imported["provider_error"] == {
        "is_error": None,
        "terminal_reason": None,
        "api_error_status": None,
        "assistant_errors": [],
    }
    assert imported["provider_outcome"] is None


def test_success_requires_supported_claude_terminal_and_no_error_signals() -> None:
    raw = _jsonl(
        {"type": "system", "subtype": "init", "tools": ["Read"]},
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "terminal_reason": "completed",
            "api_error_status": 0,
            "result": "done",
        },
    )

    imported = importers.import_claude(raw, _claude_route(), terminal={"exit_code": 0})

    assert imported["provider_terminal_status"] == "success"
    assert imported["provider_error"] == {
        "is_error": False,
        "terminal_reason": "completed",
        "api_error_status": 0,
        "assistant_errors": [],
    }
    assert imported["provider_outcome"] == "success"


@pytest.mark.parametrize("terminal", [
    {"exit_code": 0, "timeout": True},
    {"exit_code": 0, "truncated": True},
    {"exit_code": 0, "signal": "SIGTERM"},
])
def test_capture_process_failures_cannot_be_provider_success(terminal: dict[str, object]) -> None:
    raw = _jsonl(
        {"type": "system", "subtype": "init", "tools": ["Read"]},
        {"type": "result", "subtype": "success", "is_error": False, "result": "done"},
    )

    imported = importers.import_claude(raw, _claude_route(), terminal=terminal)

    assert imported["provider_outcome"] == "error"


@pytest.mark.parametrize(
    ("provider", "raw", "status"),
    [
        (
            "codex",
            _jsonl({"type": "thread.started", "thread_id": "fixture-thread"},
                   {"type": "result", "status": "completed", "result": "done"}),
            "completed",
        ),
        (
            "antigravity",
            _jsonl({"type": "result", "status": "completed", "output": "done"}),
            "completed",
        ),
    ],
)
def test_existing_provider_routes_get_additive_outcome_fields(
    provider: str, raw: bytes, status: str,
) -> None:
    imported = importers.importer_for(provider)(
        raw, {"provider": provider, "execution": "instrumented"}, terminal={"exit_code": 0}
    )

    assert imported["provider_terminal_status"] == status
    assert imported["provider_error"] == {
        "is_error": None,
        "terminal_reason": None,
        "api_error_status": None,
        "assistant_errors": [],
    }
    assert imported["provider_outcome"] == "success"
