"""Semantic responsibility model and flexible actor binding policies.

Decouples invariant semantic obligations (ADR 0059) from operational
invocation turns and process groupings.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


ROLE_PLANNER = "Planner"
ROLE_PLAN_REVIEWER = "Plan Reviewer"
ROLE_PLAN_REVIEW_DISPOSITION = "Plan Review Disposition"
ROLE_PRODUCER = "Producer"
ROLE_WORK_REVIEWER = "Work Reviewer"
ROLE_WORK_REVIEW_DISPOSITION = "Work Review Disposition"
ROLE_REVISER = "Reviser"
ROLE_CLOSEOUT_AGENT = "Closeout Agent"

CANONICAL_RESPONSIBILITIES = (
    ROLE_PLANNER,
    ROLE_PLAN_REVIEWER,
    ROLE_PLAN_REVIEW_DISPOSITION,
    ROLE_PRODUCER,
    ROLE_WORK_REVIEWER,
    ROLE_WORK_REVIEW_DISPOSITION,
    ROLE_REVISER,
    ROLE_CLOSEOUT_AGENT,
)

RESPONSIBILITY_STATUS_PENDING = "pending"
RESPONSIBILITY_STATUS_STAGED = "staged"
RESPONSIBILITY_STATUS_RUNNING = "running"
RESPONSIBILITY_STATUS_RETRY_PENDING = "retry_pending"
RESPONSIBILITY_STATUS_COMPLETED = "completed"
RESPONSIBILITY_STATUS_FAILED = "failed"

SEMANTIC_RESPONSIBILITY_STATUSES = (
    RESPONSIBILITY_STATUS_PENDING,
    RESPONSIBILITY_STATUS_STAGED,
    RESPONSIBILITY_STATUS_RUNNING,
    RESPONSIBILITY_STATUS_RETRY_PENDING,
    RESPONSIBILITY_STATUS_COMPLETED,
    RESPONSIBILITY_STATUS_FAILED,
)

ROLE_REQUIRED_CAPABILITIES: Mapping[str, frozenset[str]] = {
    ROLE_PLANNER: frozenset({"read", "reasoning"}),
    ROLE_PLAN_REVIEWER: frozenset({"read", "reasoning"}),
    ROLE_PLAN_REVIEW_DISPOSITION: frozenset({"read"}),
    ROLE_PRODUCER: frozenset({"read", "mutation", "execution"}),
    ROLE_WORK_REVIEWER: frozenset({"read", "reasoning"}),
    ROLE_WORK_REVIEW_DISPOSITION: frozenset({"read"}),
    ROLE_REVISER: frozenset({"read", "mutation", "execution"}),
    ROLE_CLOSEOUT_AGENT: frozenset({"read", "execution"}),
}

ROLE_MUTATING: Mapping[str, bool] = {
    ROLE_PLANNER: False,
    ROLE_PLAN_REVIEWER: False,
    ROLE_PLAN_REVIEW_DISPOSITION: False,
    ROLE_PRODUCER: True,
    ROLE_WORK_REVIEWER: False,
    ROLE_WORK_REVIEW_DISPOSITION: False,
    ROLE_REVISER: True,
    ROLE_CLOSEOUT_AGENT: True,
}

ROLE_READ_ONLY: Mapping[str, bool] = {
    ROLE_PLANNER: True,
    ROLE_PLAN_REVIEWER: True,
    ROLE_PLAN_REVIEW_DISPOSITION: False,
    ROLE_PRODUCER: False,
    ROLE_WORK_REVIEWER: True,
    ROLE_WORK_REVIEW_DISPOSITION: False,
    ROLE_REVISER: False,
    ROLE_CLOSEOUT_AGENT: False,
}


@dataclass(frozen=True)
class ActorBinding:
    binding_id: str
    roles: tuple[str, ...]
    policy_name: str
    is_mutating: bool
    process_read_only: bool
    required_capabilities: frozenset[str]

    @classmethod
    def create(
        cls,
        binding_id: str,
        roles: tuple[str, ...],
        policy_name: str = "default_standard",
    ) -> ActorBinding:
        capabilities: set[str] = set()
        for role in roles:
            capabilities.update(ROLE_REQUIRED_CAPABILITIES.get(role, set()))
        mutating = any(ROLE_MUTATING.get(role, False) for role in roles)
        read_only = all(ROLE_READ_ONLY.get(role, False) for role in roles)
        return cls(
            binding_id=binding_id,
            roles=roles,
            policy_name=policy_name,
            is_mutating=mutating,
            process_read_only=read_only,
            required_capabilities=frozenset(capabilities),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            "roles": list(self.roles),
            "policy_name": self.policy_name,
            "is_mutating": self.is_mutating,
            "process_read_only": self.process_read_only,
            "required_capabilities": sorted(self.required_capabilities),
        }


@dataclass(frozen=True)
class ActorBindingPolicy:
    name: str
    bindings: tuple[ActorBinding, ...]

    def get_binding(self, binding_id: str) -> ActorBinding:
        for binding in self.bindings:
            if binding.binding_id == binding_id:
                return binding
        raise ValueError(f"unknown actor binding {binding_id!r} in policy {self.name!r}")

    @property
    def binding_ids(self) -> tuple[str, ...]:
        return tuple(binding.binding_id for binding in self.bindings)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "bindings": [binding.as_dict() for binding in self.bindings],
        }


def create_default_binding_policy() -> ActorBindingPolicy:
    """Standard 5-turn grouping merging adjacent responsibilities."""
    return ActorBindingPolicy(
        name="default_standard",
        bindings=(
            ActorBinding.create("binding_plan", (ROLE_PLANNER,), policy_name="default_standard"),
            ActorBinding.create("binding_plan_review", (ROLE_PLAN_REVIEWER,), policy_name="default_standard"),
            ActorBinding.create("binding_work", (ROLE_PLAN_REVIEW_DISPOSITION, ROLE_PRODUCER), policy_name="default_standard"),
            ActorBinding.create("binding_work_review", (ROLE_WORK_REVIEWER,), policy_name="default_standard"),
            ActorBinding.create("binding_closeout", (ROLE_WORK_REVIEW_DISPOSITION, ROLE_REVISER, ROLE_CLOSEOUT_AGENT), policy_name="default_standard"),
        ),
    )


def create_unmerged_binding_policy() -> ActorBindingPolicy:
    """Discrete 8-turn unmerged topology."""
    return ActorBindingPolicy(
        name="unmerged_discrete",
        bindings=tuple(
            ActorBinding.create(f"binding_{role.lower().replace(' ', '_')}", (role,), policy_name="unmerged_discrete")
            for role in CANONICAL_RESPONSIBILITIES
        ),
    )


@dataclass(frozen=True)
class PlanProposalRecord:
    run_id: str
    started_at: str
    completed_at: str
    candidate_id: str
    outcome: str = "completed"

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_type": "plan_proposal",
            "run_id": self.run_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "candidate_id": self.candidate_id,
            "outcome": self.outcome,
        }


@dataclass(frozen=True)
class PlanReviewRecord:
    run_id: str
    review_id: str
    reviewer_provider: str
    reviewer_profile: str
    findings_count: int
    outcome: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_type": "plan_review",
            "run_id": self.run_id,
            "review_id": self.review_id,
            "reviewer_provider": self.reviewer_provider,
            "reviewer_profile": self.reviewer_profile,
            "findings_count": self.findings_count,
            "outcome": self.outcome,
        }


@dataclass(frozen=True)
class PlanDispositionRecord:
    run_id: str
    review_id: str
    disposition_outcome: str
    rationale: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_type": "plan_disposition",
            "run_id": self.run_id,
            "review_id": self.review_id,
            "disposition_outcome": self.disposition_outcome,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class ProducerCandidateRecord:
    run_id: str
    candidate_id: str
    tree_sha: str
    head_sha: str
    manifest_json: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_type": "producer_candidate",
            "run_id": self.run_id,
            "candidate_id": self.candidate_id,
            "tree_sha": self.tree_sha,
            "head_sha": self.head_sha,
            "manifest_json": self.manifest_json,
        }


@dataclass(frozen=True)
class WorkReviewRecord:
    run_id: str
    review_id: str
    reviewer_provider: str
    reviewer_profile: str
    findings_count: int
    outcome: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_type": "work_review",
            "run_id": self.run_id,
            "review_id": self.review_id,
            "reviewer_provider": self.reviewer_provider,
            "reviewer_profile": self.reviewer_profile,
            "findings_count": self.findings_count,
            "outcome": self.outcome,
        }


@dataclass(frozen=True)
class WorkDispositionRecord:
    run_id: str
    review_id: str
    disposition_outcome: str
    rationale: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_type": "work_disposition",
            "run_id": self.run_id,
            "review_id": self.review_id,
            "disposition_outcome": self.disposition_outcome,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class RevisionRecord:
    run_id: str
    candidate_id: str
    revised_tree_sha: str
    rationale: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_type": "revision",
            "run_id": self.run_id,
            "candidate_id": self.candidate_id,
            "revised_tree_sha": self.revised_tree_sha,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class CloseoutReceiptRecord:
    run_id: str
    phase_id: str
    commit_sha: str
    final_head: str
    finalization_policy: str
    finalization_outcome: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_type": "closeout_receipt",
            "run_id": self.run_id,
            "phase_id": self.phase_id,
            "commit_sha": self.commit_sha,
            "final_head": self.final_head,
            "finalization_policy": self.finalization_policy,
            "finalization_outcome": self.finalization_outcome,
        }
