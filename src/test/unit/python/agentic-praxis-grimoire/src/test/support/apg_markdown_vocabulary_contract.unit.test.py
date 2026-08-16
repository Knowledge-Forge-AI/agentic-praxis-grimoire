#!/usr/bin/env python3
"""Exact accepted-vocabulary controls for APG66B Markdown."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src/test/support"))

from apg_markdown_register_contract import (  # noqa: E402
    RegisterContractError,
    verify_fixture_projection,
)
from apg_markdown_vocabulary_contract import (  # noqa: E402
    ACCEPTED_VOCABULARY_SOURCE_SHA256,
)


REGISTER_DATA = (ROOT / "src/test/fixtures/apg64-markdown-scenario-register.md").read_bytes()
FIXTURE = json.loads(
    (ROOT / "src/test/fixtures/apg66-markdown-language-profile-scenarios.json")
    .read_text(encoding="utf-8")
)
FAMILIES = tuple(FIXTURE["vocabulary"])
UNUSED_ACCEPTED = {
    "owners": "generic-lifecycle",
    "structural_signals": "code-prose-responsibility-mixing",
    "semantic_signals": "false-completion",
}
USED_ACCEPTED = {
    "owners": "markdown-language-profile",
    "selections": "selected",
    "responses": "proceed-routine",
    "structural_signals": "multiple-independent-audiences",
    "semantic_signals": "normative-contradiction",
    "rollback_classes": "none",
    "source_boundary_classes": "actual-parser-configuration",
}


def _changed() -> dict[str, object]:
    return deepcopy(FIXTURE)


def test_vocabulary_authority_hashes_bind_accepted_apg64_inputs() -> None:
    paths = {
        "architecture": ROOT / "docs/architecture/markdown-language-profile-architecture.md",
        "lean_contract": ROOT / "docs/specs/markdown-language-profile-lean-contract.md",
        "register": ROOT / "src/test/fixtures/apg64-markdown-scenario-register.md",
    }
    assert {
        name: hashlib.sha256(path.read_bytes()).hexdigest()
        for name, path in paths.items()
    } == ACCEPTED_VOCABULARY_SOURCE_SHA256


@pytest.mark.parametrize("family", FAMILIES, ids=FAMILIES)
def test_each_vocabulary_rejects_added_unused_token(family: str) -> None:
    changed = _changed()
    changed["vocabulary"][family].append("unused-near-miss-token")
    with pytest.raises(RegisterContractError, match="accepted vocabulary"):
        verify_fixture_projection(REGISTER_DATA, changed)


@pytest.mark.parametrize("family", FAMILIES, ids=FAMILIES)
def test_each_vocabulary_rejects_removed_used_token(family: str) -> None:
    changed = _changed()
    changed["vocabulary"][family].remove(USED_ACCEPTED[family])
    with pytest.raises(RegisterContractError):
        verify_fixture_projection(REGISTER_DATA, changed)


@pytest.mark.parametrize("family", tuple(UNUSED_ACCEPTED), ids=tuple(UNUSED_ACCEPTED))
def test_unused_accepted_vocabulary_tokens_remain_required(family: str) -> None:
    changed = _changed()
    changed["vocabulary"][family].remove(UNUSED_ACCEPTED[family])
    with pytest.raises(RegisterContractError, match="accepted vocabulary"):
        verify_fixture_projection(REGISTER_DATA, changed)


@pytest.mark.parametrize("family", FAMILIES, ids=FAMILIES)
@pytest.mark.parametrize("mutation", ("near-miss", "duplicate", "reorder"))
def test_each_vocabulary_rejects_nonexact_array(family: str, mutation: str) -> None:
    changed = _changed()
    items = changed["vocabulary"][family]
    if mutation == "near-miss":
        items[0] = f"{items[0]}-ish"
    elif mutation == "duplicate":
        items.append(items[0])
    else:
        items[0], items[1] = items[1], items[0]
    with pytest.raises(RegisterContractError, match="accepted vocabulary"):
        verify_fixture_projection(REGISTER_DATA, changed)
