from __future__ import annotations

from agent_phase import envelope


def test_planning_and_review_envelopes_prohibit_side_effectful_commands() -> None:
    for text in (envelope.PLAN_ENVELOPE, envelope.REVIEWER_ENVELOPE):
        assert "pytest/test runners" in text
        assert "builds" in text
        assert "compilers" in text
        assert "generators" in text
        assert "reconcilers" in text
        assert "installers" in text
        assert "formatters/fixers" in text
        assert "uncertain repository/global side effects" in text
        assert "read-only source inspection" in text


def test_plan_review_guidance_binds_embedded_plan_and_git_tree_candidates() -> None:
    assert "authoritative `plan_bytes` candidate is the exact embedded material" in (
        envelope.REVIEWER_ENVELOPE
    )
    assert "Git-tree candidates remain repository-bound" in envelope.REVIEWER_ENVELOPE


def test_lifecycle_envelopes_keep_scope_bindings_and_review_roles_separate() -> None:
    assert "exact bound plan proposal" in envelope.WORK_ENVELOPE
    for disposition in ("accept", "amend", "reject", "defer", "supersede"):
        assert disposition in envelope.WORK_ENVELOPE
        assert disposition in envelope.PLAN_REVIEWED_PRODUCE_CLOSE_ENVELOPE
    for label in (
        "Disposition:",
        "Rationale:",
        "Qualification evidence:",
        "Unresolved concerns:",
    ):
        assert label in envelope.CLOSEOUT_ENVELOPE
    assert "producer narrative is optional" in envelope.WORK_REVIEWED_REVISE_CLOSE_ENVELOPE
    assert "binding, original scope, and review findings are mandatory" in (
        envelope.WORK_REVIEWED_REVISE_CLOSE_ENVELOPE
    )
    assert "There is no second independent review after your revision" in (
        envelope.WORK_REVIEWED_REVISE_CLOSE_ENVELOPE
    )
    assert "Findings are advisory" in envelope.REVIEWER_ENVELOPE
