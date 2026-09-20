from __future__ import annotations

import json
from pathlib import Path
import pytest

from agent_phase.adoption import AdoptionError
from agent_phase.archive import ArchiveError
from agent_phase.candidate import CandidateError
from agent_phase.finalization import FinalizationError
from agent_phase.lifecycle import LIFECYCLE_STANDARD, LifecycleError, get_lifecycle
from agent_phase.request import (
    EXECUTION_MODES,
    PHASE_TYPES,
    PhaseRequest,
    RequestError,
    parse_request,
)
from agent_phase.roster import RosterError, load_roster
from agent_phase.routing import RoutingError, describe, route

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures/parity_golden_corpus.json"


@pytest.fixture(scope="module")
def golden_corpus() -> dict:
    raw = FIXTURE_PATH.read_text(encoding="utf-8")
    return json.loads(raw)


def test_parity_corpus_route_matrix_completeness(golden_corpus: dict) -> None:
    roster = load_roster(ROOT)
    routes = golden_corpus["routes"]
    assert len(routes) == 30
    assert golden_corpus["route_count"] == 30

    covered_keys = set()
    for route_def in routes:
        pt = route_def["phase_type"]
        em = route_def["execution_mode"]
        covered_keys.add((pt, em))

        req = PhaseRequest(pt, em, "parity test prompt")
        routed = route(req, root=ROOT, roster=roster)
        aliases = roster.route_aliases(pt, em)

        expected_stages = route_def["stages"]
        assert set(routed.keys()) == set(expected_stages.keys())

        for stage_name, ep in routed.items():
            expected = expected_stages[stage_name]
            assert ep.provider == expected["provider"]
            assert ep.profile == expected["profile"]
            assert aliases[stage_name] == expected["alias"]

    all_expected_keys = {
        (pt, em) for pt in PHASE_TYPES for em in EXECUTION_MODES
    }
    assert covered_keys == all_expected_keys


def test_parity_corpus_lifecycle_topology(golden_corpus: dict) -> None:
    lifecycle = get_lifecycle(LIFECYCLE_STANDARD)
    expected_stages = golden_corpus["lifecycle_stages"]
    assert len(lifecycle.stages) == len(expected_stages)

    for actual, expected in zip(lifecycle.stages, expected_stages, strict=True):
        assert actual.name == expected["name"]
        assert actual.role == expected["role"]
        assert actual.routing_slot == expected["routing_slot"]
        assert actual.prefix == expected["prefix"]
        assert actual.candidate_key == expected["candidate_key"]
        assert actual.checkpoint == expected["checkpoint"]
        assert actual.is_mutating == expected["is_mutating"]
        assert actual.process_read_only == expected["process_read_only"]


def test_parity_corpus_request_grammar_valid(golden_corpus: dict) -> None:
    for sample in golden_corpus["valid_request_samples"]:
        raw_bytes = json.dumps(sample).encode("utf-8")
        req = parse_request(raw_bytes)
        assert req.phase_type == sample["phase_type"]
        assert req.execution_mode == sample["execution_mode"]
        assert req.prompt == sample["prompt"]


def test_parity_corpus_request_grammar_invalid(golden_corpus: dict) -> None:
    for sample in golden_corpus["invalid_request_samples"]:
        raw_bytes = json.dumps(sample["input"]).encode("utf-8")
        with pytest.raises(RequestError) as exc_info:
            parse_request(raw_bytes)
        assert sample["expected_error"] in str(exc_info.value)


def test_parity_corpus_error_classifications() -> None:
    standard_errors = [
        RequestError,
        RosterError,
        RoutingError,
        LifecycleError,
        CandidateError,
        AdoptionError,
    ]
    for err_cls in standard_errors:
        assert issubclass(err_cls, Exception)
        instance = err_cls("test error message")
        assert "test error message" in str(instance)

    for coded_cls in [ArchiveError, FinalizationError]:
        assert issubclass(coded_cls, RuntimeError)
        instance = coded_cls("TEST_CODE", "test error detail")
        assert "TEST_CODE: test error detail" in str(instance)
        assert instance.code == "TEST_CODE"
        assert instance.detail == "test error detail"

    archive_err = ArchiveError("ARCHIVE_VERIFICATION_FAILED", "snapshot mismatch")
    assert str(archive_err) == "ARCHIVE_VERIFICATION_FAILED: snapshot mismatch"
    assert archive_err.code == "ARCHIVE_VERIFICATION_FAILED"

    final_err = FinalizationError("COMMIT_FAILED", "working tree dirty")
    assert str(final_err) == "COMMIT_FAILED: working tree dirty"
    assert final_err.code == "COMMIT_FAILED"


def test_parity_corpus_intelligence_readback(golden_corpus: dict) -> None:
    assert golden_corpus["baseline_commit"] == "56e9bb039536dfc8893e61a431681d6a32167b6f"
    roster = load_roster(ROOT)
    req = PhaseRequest("implementation_testing", "normal", "test prompt")
    routed = route(req, root=ROOT, roster=roster)

    expected_intel = {
        "plan": ("codex", "architecture-docs-primary", "gpt-6-astra", "medium"),
        "plan_review": ("claude", "normal-plan-review", "claude-fable-5-1", "high"),
        "work": ("antigravity", "gemini-3.8-flash-high", "gemini-3.8-flash-high", None),
        "final_review": ("claude", "normal-final-review", "claude-opus-5", "high"),
        "closeout": ("codex", "implementation-testing", "gpt-6-astra", "medium"),
    }

    for stage_name, (exp_prov, exp_prof, exp_model, exp_effort) in expected_intel.items():
        endpoint = routed[stage_name]
        desc = describe(ROOT, stage_name, endpoint)
        assert desc["provider"] == exp_prov
        assert desc["profile"] == exp_prof
        intel = desc["intelligence"]
        assert intel["model"] == exp_model
        if exp_effort is not None:
            assert intel.get("effort") == exp_effort

