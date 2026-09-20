"""Closed, typed lifecycle and Git-finalization policy registry."""

from __future__ import annotations

from dataclasses import dataclass


LIFECYCLE_STANDARD = "standard"
LIFECYCLE_SOLO = "solo"
LIFECYCLE_PLAN_REVIEWED = "plan-reviewed"
LIFECYCLE_WORK_REVIEWED = "work-reviewed"

FINALIZATION_PUBLISH = "publish"
FINALIZATION_COMMIT_LOCAL = "commit-local"
FINALIZATION_CHECKPOINT = "checkpoint"
FINALIZATION_POLICIES = (
    FINALIZATION_PUBLISH,
    FINALIZATION_COMMIT_LOCAL,
    FINALIZATION_CHECKPOINT,
)


class LifecycleError(ValueError):
    """An operator-selected lifecycle or finalization policy is invalid."""


@dataclass(frozen=True)
class StageSpec:
    name: str
    prefix: str
    role: str
    is_mutating: bool
    routing_slot: str
    checkpoint: str | None = None
    process_read_only: bool = False
    candidate_key: str | None = None
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class LifecycleSpec:
    name: str
    stages: tuple[StageSpec, ...]
    terminal_result_stage: str

    @property
    def stage_names(self) -> tuple[str, ...]:
        return tuple(stage.name for stage in self.stages)

    @property
    def checkpoints(self) -> tuple[str, ...]:
        return tuple(
            stage.checkpoint for stage in self.stages if stage.checkpoint is not None
        )

    @property
    def expected_provider_invocations(self) -> int:
        return len(self.stages)

    @property
    def expected_review_count(self) -> int:
        return len(self.checkpoints)

    @property
    def prefixes(self) -> dict[str, str]:
        return {stage.name: stage.prefix for stage in self.stages}

    @property
    def checkpoint_by_stage(self) -> dict[str, str]:
        return {
            stage.name: stage.checkpoint
            for stage in self.stages
            if stage.checkpoint is not None
        }

    @property
    def valid_resume_aliases(self) -> dict[str, str]:
        aliases = {"auto": "auto", "finalize": "finalize"}
        for stage in self.stages:
            aliases[stage.name] = stage.name
            aliases[stage.name.replace("_", "-")] = stage.name
            aliases.update({alias: stage.name for alias in stage.aliases})
        return aliases

    def stage(self, name: str) -> StageSpec:
        for stage in self.stages:
            if stage.name == name:
                return stage
        raise LifecycleError(f"unknown stage {name!r} for lifecycle {self.name!r}")


def _stage(
    name: str,
    prefix: str,
    role: str,
    mutating: bool,
    routing_slot: str,
    checkpoint: str | None = None,
    process_read_only: bool = False,
    candidate_key: str | None = None,
) -> StageSpec:
    return StageSpec(
        name, prefix, role, mutating, routing_slot, checkpoint, process_read_only,
        candidate_key,
    )


LIFECYCLES: dict[str, LifecycleSpec] = {
    LIFECYCLE_STANDARD: LifecycleSpec(
        LIFECYCLE_STANDARD,
        (
            _stage("plan", "01-plan", "primary", False, "plan", None, True),
            _stage(
                "plan_review", "02-plan-review", "reviewer", False,
                "plan_review", "post_planning", True,
            ),
            _stage(
                "work", "03-work", "primary", True, "work", None, False,
                "pre_final_candidate",
            ),
            _stage(
                "final_review", "04-final-review", "reviewer", False,
                "final_review", "pre_final", True,
            ),
            _stage(
                "closeout", "05-closeout", "primary", True, "closeout", None,
                False, "closeout_candidate",
            ),
        ),
        "closeout",
    ),
    LIFECYCLE_SOLO: LifecycleSpec(
        LIFECYCLE_SOLO,
        (_stage(
            "solo", "01-solo", "primary", True, "work", None, False,
            "solo_candidate",
        ),),
        "solo",
    ),
    LIFECYCLE_PLAN_REVIEWED: LifecycleSpec(
        LIFECYCLE_PLAN_REVIEWED,
        (
            _stage("plan", "01-plan", "primary", False, "plan", None, True),
            _stage(
                "plan_review", "02-plan-review", "reviewer", False,
                "plan_review", "post_planning", True,
            ),
            _stage(
                "produce_close", "03-produce-close", "primary", True, "work",
                None, False, "produce_close_candidate",
            ),
        ),
        "produce_close",
    ),
    LIFECYCLE_WORK_REVIEWED: LifecycleSpec(
        LIFECYCLE_WORK_REVIEWED,
        (
            _stage(
                "produce", "01-produce", "primary", True, "work", None, False,
                "produced_candidate",
            ),
            _stage(
                "work_review", "02-work-review", "reviewer", False,
                "final_review", "post_work", True,
            ),
            _stage(
                "revise_close", "03-revise-close", "primary", True, "work",
                None, False, "revise_close_candidate",
            ),
        ),
        "revise_close",
    ),
}

LIFECYCLE_NAMES = tuple(LIFECYCLES)


def get_lifecycle(name: str) -> LifecycleSpec:
    try:
        return LIFECYCLES[name]
    except KeyError as error:
        raise LifecycleError(
            f"unknown lifecycle {name!r}; expected one of {list(LIFECYCLE_NAMES)}"
        ) from error


def validate_finalization(policy: str) -> str:
    if policy not in FINALIZATION_POLICIES:
        raise LifecycleError(
            f"unknown finalization policy {policy!r}; expected one of "
            f"{list(FINALIZATION_POLICIES)}"
        )
    return policy
