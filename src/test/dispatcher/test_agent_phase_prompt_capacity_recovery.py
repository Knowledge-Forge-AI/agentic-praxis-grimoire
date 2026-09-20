"""Whole-artifact prompt-capacity decisions for carried producer narrative."""

from __future__ import annotations

import hashlib

import pytest

from agent_phase import capacity as capacity_module
from agent_phase import envelope as envelope_module
from agent_phase.routing import Endpoint
from agent_phase.transport import PromptLimitError


def test_optional_narrative_is_omitted_whole_with_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    narrative = b"producer narrative\n" * 100

    def bounded(stage, endpoint, rendered):
        if len(rendered.data) > 600:
            raise PromptLimitError("fixture prompt limit")

    monkeypatch.setattr(capacity_module, "ensure_prompt_fits", bounded)
    rendered, record = capacity_module.fit_optional_narrative(
        "work_review",
        Endpoint("antigravity", "gemini-3.7-flash-high"),
        lambda material: envelope_module.render([
            envelope_module.Segment("envelope", b"mandatory review contract\n"),
            envelope_module.Segment("prior_material", material),
        ]),
        narrative,
        source_stage="produce",
        artifact_basename="01-produce.stdout.md",
        artifact_bytes=narrative,
        mandatory_sources=("original_scope", "producer_binding", "review_findings"),
    )
    assert record["decision"] == "omitted_whole"
    assert record["optional_source"] == "produce"
    assert record["mandatory_sources"] == [
        "original_scope", "producer_binding", "review_findings",
    ]
    assert record["mandatory_material_preserved"] is True
    assert record["omitted_sources"] == ["produce"]
    assert record["preserved_sources"] == [
        "original_scope", "producer_binding", "review_findings",
    ]
    assert record["omission_scope"] == "whole_optional_artifact_only"
    assert narrative[:40] not in rendered.data
    assert b"No prefix or summary was substituted" in rendered.data
    assert str(len(narrative)).encode() in rendered.data
    assert hashlib.sha256(narrative).hexdigest().encode() in rendered.data
    assert b"/private/" not in rendered.data


def test_optional_omission_never_drops_mandatory_material(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mandatory = b"M" * 700

    def bounded(stage, endpoint, rendered):
        if len(rendered.data) > 600:
            raise PromptLimitError("fixture prompt limit")

    monkeypatch.setattr(capacity_module, "ensure_prompt_fits", bounded)
    with pytest.raises(PromptLimitError):
        capacity_module.fit_optional_narrative(
            "revise_close",
            Endpoint("antigravity", "gemini-3.7-flash-high"),
            lambda material: envelope_module.render([
                envelope_module.Segment("envelope", mandatory),
                envelope_module.Segment("prior_material", material),
            ]),
            b"optional producer",
            source_stage="produce",
            artifact_basename="01-produce.stdout.md",
            artifact_bytes=b"optional producer",
        )
