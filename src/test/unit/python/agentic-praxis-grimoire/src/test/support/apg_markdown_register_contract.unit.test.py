#!/usr/bin/env python3
"""Mutation controls for the APG64 register-to-fixture projection."""

from __future__ import annotations

from copy import deepcopy
import json
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src/test/support"))

from apg_markdown_register_contract import (  # noqa: E402
    REGISTER_BLOB_OID,
    REGISTER_FIELDS,
    RegisterContractError,
    git_blob_oid,
    parse_register,
    project_semantic_rows,
    verify_fixture_projection,
    verify_register_blob,
)


REGISTER_SOURCE = ROOT / "src/test/fixtures/apg64-markdown-scenario-register.md"
REGISTER_DATA = REGISTER_SOURCE.read_bytes()
REGISTER_TEXT = REGISTER_DATA.decode("utf-8")
FIXTURE = json.loads(
    (ROOT / "src/test/fixtures/apg66-markdown-language-profile-scenarios.json")
    .read_text(encoding="utf-8")
)


def test_exact_register_blob_and_fixture_projection_pass() -> None:
    assert git_blob_oid(REGISTER_DATA) == REGISTER_BLOB_OID
    assert verify_register_blob(REGISTER_DATA) == REGISTER_BLOB_OID
    verify_fixture_projection(REGISTER_DATA, FIXTURE)


def test_wrong_register_blob_fails_before_projection() -> None:
    with pytest.raises(RegisterContractError, match="blob identity"):
        verify_fixture_projection(REGISTER_DATA + b"\n", FIXTURE)


def test_register_has_36_contiguous_closed_rows() -> None:
    rows = parse_register(REGISTER_TEXT)
    assert [row["id"] for row in rows] == [
        f"APG63-MD-{index:03d}" for index in range(1, 37)
    ]
    assert all(tuple(key for key in row if key != "id") == REGISTER_FIELDS for row in rows)
    assert len(project_semantic_rows(rows, FIXTURE["vocabulary"])) == 34
    assert [row["id"] for row in rows[34:]] == ["APG63-MD-035", "APG63-MD-036"]


def test_duplicate_scenario_id_is_rejected() -> None:
    changed = REGISTER_TEXT.replace("### APG63-MD-002", "### APG63-MD-001", 1)
    with pytest.raises(RegisterContractError, match="contiguous"):
        parse_register(changed)


def test_duplicate_register_field_is_rejected() -> None:
    changed = REGISTER_TEXT.replace(
        "- Owner: markdown-language-profile\n",
        "- Owner: markdown-language-profile\n- Owner: parser-tool-owner\n",
        1,
    )
    with pytest.raises(RegisterContractError, match="duplicate field: Owner"):
        parse_register(changed)


def test_missing_register_field_is_rejected() -> None:
    changed = REGISTER_TEXT.replace("- Owner: markdown-language-profile\n", "", 1)
    with pytest.raises(RegisterContractError, match="missing field: Owner"):
        parse_register(changed)


@pytest.mark.parametrize(
    ("field", "replacement", "diagnostic"),
    (
        ("Owner", "unknown-owner", "unknown owner"),
        ("Selection", "unknown-selection", "unknown selection"),
        ("Response", "unknown-response", "unknown response"),
        ("Route", "unknown-route", "unknown route"),
        ("Structural", "unknown-structural-signal", "unknown structural_signals"),
        ("Semantic", "unknown-semantic-signal", "unknown semantic_signals"),
    ),
)
def test_unknown_projected_token_is_rejected(
    field: str, replacement: str, diagnostic: str
) -> None:
    rows = [dict(row) for row in parse_register(REGISTER_TEXT)]
    rows[0][field] = replacement
    with pytest.raises(RegisterContractError, match=diagnostic):
        project_semantic_rows(tuple(rows), FIXTURE["vocabulary"])


def test_fixture_row_changed_independently_is_rejected() -> None:
    changed = deepcopy(FIXTURE)
    changed["rows"][0]["owner"] = "parser-tool-owner"
    with pytest.raises(RegisterContractError, match="fixture rows disagree"):
        verify_fixture_projection(REGISTER_DATA, changed)


def test_process_row_cannot_leak_into_fixture() -> None:
    changed = deepcopy(FIXTURE)
    process = dict(changed["rows"][-1])
    process["id"] = "APG63-MD-035"
    changed["rows"][-1] = process
    with pytest.raises(RegisterContractError, match="fixture rows disagree"):
        verify_fixture_projection(REGISTER_DATA, changed)


def test_fixture_vocabulary_is_closed() -> None:
    changed = deepcopy(FIXTURE)
    changed["vocabulary"]["extra"] = []
    with pytest.raises(RegisterContractError, match="accepted vocabulary"):
        verify_fixture_projection(REGISTER_DATA, changed)
