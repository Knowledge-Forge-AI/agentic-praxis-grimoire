from __future__ import annotations

import pytest

from agent_phase.semantic_roles import (
    CANONICAL_RESPONSIBILITIES,
    ROLE_CLOSEOUT_AGENT,
    ROLE_MUTATING,
    ROLE_PLAN_REVIEW_DISPOSITION,
    ROLE_PLAN_REVIEWER,
    ROLE_PLANNER,
    ROLE_PRODUCER,
    ROLE_READ_ONLY,
    ROLE_REQUIRED_CAPABILITIES,
    ROLE_REVISER,
    ROLE_WORK_REVIEW_DISPOSITION,
    ROLE_WORK_REVIEWER,
    ActorBinding,
    CloseoutReceiptRecord,
    PlanDispositionRecord,
    PlanProposalRecord,
    PlanReviewRecord,
    ProducerCandidateRecord,
    RevisionRecord,
    WorkDispositionRecord,
    WorkReviewRecord,
    create_default_binding_policy,
    create_unmerged_binding_policy,
)


def test_canonical_responsibilities_completeness() -> None:
    expected = {
        ROLE_PLANNER,
        ROLE_PLAN_REVIEWER,
        ROLE_PLAN_REVIEW_DISPOSITION,
        ROLE_PRODUCER,
        ROLE_WORK_REVIEWER,
        ROLE_WORK_REVIEW_DISPOSITION,
        ROLE_REVISER,
        ROLE_CLOSEOUT_AGENT,
    }
    assert set(CANONICAL_RESPONSIBILITIES) == expected
    assert len(CANONICAL_RESPONSIBILITIES) == 8


def test_responsibility_capability_requirements() -> None:
    for role in CANONICAL_RESPONSIBILITIES:
        assert role in ROLE_REQUIRED_CAPABILITIES
        caps = ROLE_REQUIRED_CAPABILITIES[role]
        assert isinstance(caps, frozenset)
        assert len(caps) > 0

    assert "read" in ROLE_REQUIRED_CAPABILITIES[ROLE_PLANNER]
    assert "reasoning" in ROLE_REQUIRED_CAPABILITIES[ROLE_PLANNER]
    assert "mutation" in ROLE_REQUIRED_CAPABILITIES[ROLE_PRODUCER]
    assert "execution" in ROLE_REQUIRED_CAPABILITIES[ROLE_PRODUCER]
    assert "reasoning" in ROLE_REQUIRED_CAPABILITIES[ROLE_WORK_REVIEWER]


def test_mutating_and_read_only_invariants() -> None:
    assert ROLE_MUTATING[ROLE_PLANNER] is False
    assert ROLE_MUTATING[ROLE_PLAN_REVIEWER] is False
    assert ROLE_MUTATING[ROLE_PRODUCER] is True
    assert ROLE_MUTATING[ROLE_REVISER] is True

    assert ROLE_READ_ONLY[ROLE_PLANNER] is True
    assert ROLE_READ_ONLY[ROLE_PLAN_REVIEWER] is True
    assert ROLE_READ_ONLY[ROLE_WORK_REVIEWER] is True
    assert ROLE_READ_ONLY[ROLE_PRODUCER] is False


def test_capability_union_for_merged_binding() -> None:
    # Merging ROLE_PLAN_REVIEW_DISPOSITION and ROLE_PRODUCER
    roles = (ROLE_PLAN_REVIEW_DISPOSITION, ROLE_PRODUCER)
    binding = ActorBinding.create("binding_work", roles)
    expected_caps = ROLE_REQUIRED_CAPABILITIES[ROLE_PLAN_REVIEW_DISPOSITION] | ROLE_REQUIRED_CAPABILITIES[ROLE_PRODUCER]
    assert binding.required_capabilities == expected_caps
    assert binding.is_mutating is True
    assert binding.process_read_only is False

    b_dict = binding.as_dict()
    assert b_dict["binding_id"] == "binding_work"
    assert b_dict["roles"] == list(roles)
    assert b_dict["is_mutating"] is True


def test_default_standard_binding_policy() -> None:
    policy = create_default_binding_policy()
    assert policy.name == "default_standard"
    bindings = policy.bindings
    # Standard groups into 5 turns
    assert len(bindings) == 5
    assert policy.binding_ids == (
        "binding_plan",
        "binding_plan_review",
        "binding_work",
        "binding_work_review",
        "binding_closeout",
    )

    plan_binding = policy.get_binding("binding_plan")
    assert plan_binding.roles == (ROLE_PLANNER,)
    assert plan_binding.is_mutating is False
    assert plan_binding.process_read_only is True

    work_binding = policy.get_binding("binding_work")
    assert ROLE_PRODUCER in work_binding.roles
    assert work_binding.is_mutating is True

    with pytest.raises(ValueError, match="unknown actor binding"):
        policy.get_binding("nonexistent_binding")


def test_unmerged_8_turn_policy() -> None:
    policy = create_unmerged_binding_policy()
    assert policy.name == "unmerged_discrete"
    bindings = policy.bindings
    assert len(bindings) == 8
    for binding in bindings:
        assert len(binding.roles) == 1
        assert binding.roles[0] in CANONICAL_RESPONSIBILITIES


def test_decoupled_record_dataclasses() -> None:
    plan_prop = PlanProposalRecord(
        run_id="run-123",
        started_at="2026-09-16T12:00:00Z",
        completed_at="2026-09-16T12:01:00Z",
        candidate_id="cand-001",
    )
    p_dict = plan_prop.as_dict()
    assert p_dict["record_type"] == "plan_proposal"
    assert p_dict["candidate_id"] == "cand-001"

    plan_rev = PlanReviewRecord(
        run_id="run-123",
        review_id="rev-001",
        reviewer_provider="codex",
        reviewer_profile="gpt-5-codex",
        findings_count=0,
        outcome="accepted",
    )
    assert plan_rev.as_dict()["outcome"] == "accepted"

    plan_disp = PlanDispositionRecord(
        run_id="run-123",
        review_id="rev-001",
        disposition_outcome="accept",
        rationale="All clean",
    )
    assert plan_disp.as_dict()["disposition_outcome"] == "accept"

    prod_cand = ProducerCandidateRecord(
        run_id="run-123",
        candidate_id="cand-002",
        tree_sha="abc123tree",
        head_sha="abc123head",
        manifest_json="{}",
    )
    assert prod_cand.as_dict()["tree_sha"] == "abc123tree"

    work_rev = WorkReviewRecord(
        run_id="run-123",
        review_id="rev-002",
        reviewer_provider="claude",
        reviewer_profile="claude-3-7-sonnet",
        findings_count=1,
        outcome="amend_requested",
    )
    assert work_rev.as_dict()["findings_count"] == 1

    work_disp = WorkDispositionRecord(
        run_id="run-123",
        review_id="rev-002",
        disposition_outcome="amend",
        rationale="Follow review suggestions",
    )
    assert work_disp.as_dict()["disposition_outcome"] == "amend"

    rev_rec = RevisionRecord(
        run_id="run-123",
        candidate_id="cand-003",
        revised_tree_sha="def456tree",
        rationale="Applied review amendment",
    )
    assert rev_rec.as_dict()["revised_tree_sha"] == "def456tree"

    closeout = CloseoutReceiptRecord(
        run_id="run-123",
        phase_id="phase-001",
        commit_sha="commit123",
        final_head="main",
        finalization_policy="publish",
        finalization_outcome="success",
    )
    assert closeout.as_dict()["commit_sha"] == "commit123"
