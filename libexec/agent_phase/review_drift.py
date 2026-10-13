"""Unified review drift observation and configurable mutation policy evaluator.

Observes working tree, staged index, and HEAD drift across V1 and V2 review seams.
Applies the tri-state policy (block | warn | allow) for working tree changes while
keeping index mutations and HEAD movements strictly fail-closed.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import candidate as candidate_module
from . import gitstate as gitstate_module
from .config_routing import (
    DEFAULT_REVIEW_MUTATION_WORKTREE,
    DEFAULT_REVIEW_MUTATION_GIT,
    SUPPORTED_POLICY_GENERATION,
    SUPPORTED_WORKTREE_POLICIES,
    ReviewMutationPolicy,
)

logger = logging.getLogger(__name__)

REVIEW_MUTATION_OBSERVATION_SCHEMA = "agent-phase-review-mutation-observation-v1"

# Canonical diagnostic codes
READ_ONLY_STAGE_MUTATED_CANDIDATE = "READ_ONLY_STAGE_MUTATED_CANDIDATE"
READ_ONLY_STAGE_MUTATED_INDEX = "READ_ONLY_STAGE_MUTATED_INDEX"
READ_ONLY_STAGE_MUTATED_HEAD = "READ_ONLY_STAGE_MUTATED_HEAD"

# Canonical policy evaluation actions
ACTION_BLOCKED = "blocked"
ACTION_WARNED = "warned"
ACTION_ALLOWED = "allowed"
ACTION_NONE = "none"


class ReviewObservation:
    """Captured drift observation and policy evaluation record."""

    def __init__(
        self,
        *,
        stage: str,
        policy: Mapping[str, Any] | ReviewMutationPolicy,
        subject_drift_observed: bool,
        worktree_drift: bool,
        index_drift: bool,
        head_drift: bool,
        worktree_paths: Sequence[str] | None = None,
        index_paths: Sequence[str] | None = None,
        expected_tree: str | None = None,
        observed_tree: str | None = None,
        expected_index: Mapping[str, Any] | str | None = None,
        observed_index: Mapping[str, Any] | str | None = None,
        expected_head: str | None = None,
        observed_head: str | None = None,
        diagnostic_code: str | None = None,
        action_taken: str = ACTION_NONE,
        detail: str | None = None,
        transport: Mapping[str, Any] | None = None,
        observation_limitations: Sequence[Mapping[str, Any]] | None = None,
        candidate_observation_unavailable: bool = False,
        index_observation_unavailable: bool = False,
        head_observation_unavailable: bool = False,
        paths_complete: bool = True,
        role: str | None = None,
        subject_kind: str | None = None,
        sequence: int = 0,
        schema: str = REVIEW_MUTATION_OBSERVATION_SCHEMA,
        attempt_id: str | None = None,
        binding_id: str | None = None,
        attempt_number: int | None = None,
        policy_generation: int = SUPPORTED_POLICY_GENERATION,
        raw_stdout_artifact: str | None = None,
        raw_stderr_artifact: str | None = None,
    ) -> None:
        self.stage = stage
        if isinstance(policy, ReviewMutationPolicy):
            self.policy = policy.as_dict()
        elif isinstance(policy, str):
            self.policy = ReviewMutationPolicy(worktree=policy).as_dict()
        elif isinstance(policy, Mapping):
            self.policy = dict(policy)
        else:
            self.policy = _default_policy().as_dict()
        self.subject_drift_observed = bool(subject_drift_observed)
        self.worktree_drift = bool(worktree_drift)
        self.index_drift = bool(index_drift)
        self.head_drift = bool(head_drift)
        self.worktree_paths = list(worktree_paths or [])
        self.index_paths = list(index_paths or [])
        self.expected_tree = expected_tree or ""
        self.observed_tree = observed_tree or ""
        self.expected_index = expected_index
        self.observed_index = observed_index
        self.expected_head = expected_head or ""
        self.observed_head = observed_head or ""
        self.diagnostic_code = diagnostic_code or ""
        self.action_taken = action_taken
        self.detail = detail or ""
        self.transport = dict(transport) if transport is not None else None
        self.observation_limitations = list(observation_limitations or [])
        self.candidate_observation_unavailable = candidate_observation_unavailable
        self.index_observation_unavailable = index_observation_unavailable
        self.head_observation_unavailable = head_observation_unavailable
        self.paths_complete = paths_complete
        self.role = role
        self.subject_kind = subject_kind
        self.sequence = sequence
        self.schema = schema
        self.attempt_id = attempt_id
        self.binding_id = binding_id
        self.attempt_number = attempt_number
        self.policy_generation = policy_generation
        self.raw_stdout_artifact = raw_stdout_artifact
        self.raw_stderr_artifact = raw_stderr_artifact

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema": self.schema,
            "stage": self.stage,
            "policy": self.policy,
            "subject_drift_observed": self.subject_drift_observed,
            "worktree_drift": self.worktree_drift,
            "index_drift": self.index_drift,
            "head_drift": self.head_drift,
            "paths": list(self.worktree_paths),
            "worktree_paths": list(self.worktree_paths),
            "index_paths": list(self.index_paths),
            "expected_tree": self.expected_tree,
            "observed_tree": self.observed_tree,
            "expected_index": self.expected_index,
            "observed_index": self.observed_index,
            "expected_head": self.expected_head,
            "observed_head": self.observed_head,
            "code": self.diagnostic_code,
            "diagnostic_code": self.diagnostic_code,
            "action_taken": self.action_taken,
            "detail": self.detail,
            "paths_complete": self.paths_complete,
            "candidate_observation_unavailable": bool(self.candidate_observation_unavailable),
            "index_observation_unavailable": bool(self.index_observation_unavailable),
            "head_observation_unavailable": bool(self.head_observation_unavailable),
            "observation_limitations": list(self.observation_limitations),
            "limitations": list(self.observation_limitations),
            "sequence": self.sequence,
            "attempt_id": self.attempt_id,
            "binding_id": self.binding_id,
            "attempt_number": self.attempt_number,
            "policy_generation": self.policy_generation,
            "raw_stdout_artifact": self.raw_stdout_artifact,
            "raw_stderr_artifact": self.raw_stderr_artifact,
        }
        if self.role is not None:
            result["role"] = self.role
        if self.subject_kind is not None:
            result["subject_kind"] = self.subject_kind
        if self.transport is not None:
            result["transport"] = self.transport
        return result


def _default_policy() -> ReviewMutationPolicy:
    return ReviewMutationPolicy(
        worktree=DEFAULT_REVIEW_MUTATION_WORKTREE,
        index=DEFAULT_REVIEW_MUTATION_GIT,
        head=DEFAULT_REVIEW_MUTATION_GIT,
        generation=SUPPORTED_POLICY_GENERATION,
    )


def observe_review_drift(
    root: Path | str,
    stage: str,
    before: Mapping[str, Any] | str,
    after: Mapping[str, Any] | str | None = None,
    expected_index: Mapping[str, Any] | str | None = None,
    observed_index: Mapping[str, Any] | str | None = None,
    expected_head: str | None = None,
    observed_head: str | None = None,
    transport: Mapping[str, Any] | None = None,
    policy: ReviewMutationPolicy | Mapping[str, Any] | None = None,
    state: dict[str, Any] | None = None,
    role: str | None = None,
    subject_kind: str | None = None,
    attempt_id: str | None = None,
    binding_id: str | None = None,
    attempt_number: int | None = None,
    raw_stdout_artifact: str | None = None,
    raw_stderr_artifact: str | None = None,
    sequence: int = 0,
) -> ReviewObservation:
    """Observe drift across worktree, index, and head for a review stage."""
    root_path = Path(root)

    # Do not infer role/subject_kind from stage substrings; resolve from explicit binding if available
    if role is None and state is not None and isinstance(state.get("immutable_review_bindings"), Mapping):
        binding = state["immutable_review_bindings"].get(stage)
        if isinstance(binding, Mapping):
            role = binding.get("role")
    if subject_kind is None and state is not None and isinstance(state.get("immutable_review_bindings"), Mapping):
        binding = state["immutable_review_bindings"].get(stage)
        if isinstance(binding, Mapping):
            subject_kind = binding.get("subject_kind")

    # Resolve expected tree, head, and index from before
    if isinstance(before, Mapping):
        if "repository" in before and isinstance(before["repository"], Mapping):
            repo_before = before["repository"]
            exp_tree = repo_before.get("tree", "")
            exp_head = expected_head or repo_before.get("head", "")
            if expected_index is None:
                expected_index = before.get("index")
        else:
            exp_tree = before.get("tree", "")
            exp_head = expected_head or before.get("head", "")
            if expected_index is None:
                expected_index = before.get("index")
    else:
        exp_tree = str(before)
        exp_head = expected_head or ""

    if not exp_head and state and isinstance(state.get("entry"), Mapping):
        exp_head = state["entry"].get("head", "")
    elif not exp_head and state and hasattr(state.get("entry"), "head"):
        exp_head = getattr(state["entry"], "head", "")

    # Resolve observed after
    candidate_unavailable = False
    if after is None:
        try:
            after_ident = candidate_module.tree_identity(root_path)
            obs_tree = after_ident.get("tree", "")
            obs_head = after_ident.get("head", "")
        except candidate_module.CandidateError:
            obs_tree = ""
            obs_head = ""
            candidate_unavailable = True
    elif isinstance(after, Mapping):
        obs_tree = after.get("tree", "")
        obs_head = after.get("head", "")
        candidate_unavailable = bool(after.get("observation_unavailable"))
    else:
        obs_tree = str(after)
        obs_head = ""

    obs_head = observed_head or obs_head
    head_unavailable = False
    if not obs_head:
        try:
            obs_head = gitstate_module.current_head(root_path)
        except Exception:
            obs_head = ""
            head_unavailable = True

    # Resolve index identity
    index_unavailable = False
    if observed_index is None:
        try:
            observed_index = gitstate_module.index_identity(root_path)
        except Exception:
            observed_index = None
            index_unavailable = True

    if expected_index is None:
        if isinstance(before, Mapping):
            expected_index = before.get("index")
        if expected_index is None and state and isinstance(state.get("immutable_review_bindings"), Mapping):
            binding = state["immutable_review_bindings"].get(stage)
            if isinstance(binding, Mapping):
                expected_index = binding.get("index")
        if expected_index is None and state and isinstance(state.get("entry"), Mapping):
            expected_index = state["entry"].get("index")
        elif expected_index is None and state and hasattr(state.get("entry"), "index_identity"):
            expected_index = state["entry"].index_identity

    # Check drift across the 3 axes
    worktree_drift = bool(exp_tree and obs_tree and obs_tree != exp_tree)
    if index_unavailable or (expected_index is None and observed_index is not None):
        index_drift = False
    else:
        index_drift = bool(observed_index is not None and expected_index is not None and observed_index != expected_index)
    head_drift = bool(exp_head and obs_head and obs_head != exp_head)

    # Collect path deltas and limitations
    limitations: list[dict[str, Any]] = []
    worktree_paths: list[str] = []
    paths_complete = True

    if head_unavailable:
        limitations.append({"kind": "head_observation_unavailable"})
        paths_complete = False

    if index_unavailable:
        limitations.append({"kind": "index_observation_unavailable"})
        paths_complete = False

    if expected_index is None:
        limitations.append({"kind": "expected_index_unavailable"})
        paths_complete = False

    if candidate_unavailable:
        limitations.append({"kind": "candidate_observation_unavailable"})
        paths_complete = False
    elif worktree_drift and exp_tree and obs_tree:
        try:
            worktree_paths = candidate_module.tree_delta(root_path, str(exp_tree), str(obs_tree))
        except candidate_module.CandidateError:
            limitations.append({"kind": "product_paths_unavailable"})
            paths_complete = False

    index_paths: list[str] = []
    if index_drift:
        from .stage_delta import inspect_index_changes
        obs_info: dict[str, Any] = {}
        index_paths = sorted({
            item["path"] for item in inspect_index_changes(root_path, observation=obs_info)
        })
        if obs_info.get("observation_limitations"):
            limitations.extend(obs_info["observation_limitations"])
            paths_complete = False

    # Resolve effective policy
    effective_policy = policy
    if effective_policy is None and state is not None:
        effective_policy = state.get("review_mutation_policy")
    if effective_policy is None:
        effective_policy = _default_policy()

    # Resolve effective transport
    effective_transport = transport
    if effective_transport is None and state is not None:
        effective_transport = state.get("stage_transport_outcomes", {}).get(stage)

    subject_drift_observed = bool(worktree_drift or index_drift or head_drift)

    return ReviewObservation(
        stage=stage,
        policy=effective_policy,
        subject_drift_observed=subject_drift_observed,
        worktree_drift=worktree_drift,
        index_drift=index_drift,
        head_drift=head_drift,
        worktree_paths=worktree_paths,
        index_paths=index_paths,
        expected_tree=exp_tree,
        observed_tree=obs_tree,
        expected_index=expected_index,
        observed_index=observed_index,
        expected_head=exp_head,
        observed_head=obs_head,
        transport=effective_transport,
        observation_limitations=limitations,
        candidate_observation_unavailable=candidate_unavailable,
        index_observation_unavailable=index_unavailable,
        head_observation_unavailable=head_unavailable,
        paths_complete=paths_complete,
        role=role,
        subject_kind=subject_kind,
        sequence=sequence,
        attempt_id=attempt_id,
        binding_id=binding_id,
        attempt_number=attempt_number,
        raw_stdout_artifact=raw_stdout_artifact,
        raw_stderr_artifact=raw_stderr_artifact,
    )


def apply_review_mutation_policy(
    obs: ReviewObservation,
    policy: ReviewMutationPolicy | Mapping[str, Any] | None = None,
    state: dict[str, Any] | None = None,
    *,
    raise_on_block: bool = True,
) -> ReviewObservation:
    """Evaluate policy against observed drift, updating state and raising if blocked."""
    effective_policy = policy or obs.policy
    if isinstance(effective_policy, ReviewMutationPolicy):
        wt_policy = effective_policy.worktree
        idx_policy = effective_policy.index
        hd_policy = effective_policy.head
    elif isinstance(effective_policy, str):
        wt_policy = effective_policy
        idx_policy = DEFAULT_REVIEW_MUTATION_GIT
        hd_policy = DEFAULT_REVIEW_MUTATION_GIT
    elif isinstance(effective_policy, Mapping):
        wt_policy = effective_policy.get("worktree", DEFAULT_REVIEW_MUTATION_WORKTREE)
        idx_policy = effective_policy.get("index", DEFAULT_REVIEW_MUTATION_GIT)
        hd_policy = effective_policy.get("head", DEFAULT_REVIEW_MUTATION_GIT)
    else:
        wt_policy = DEFAULT_REVIEW_MUTATION_WORKTREE
        idx_policy = DEFAULT_REVIEW_MUTATION_GIT
        hd_policy = DEFAULT_REVIEW_MUTATION_GIT

    if state is not None:
        prior_obs = state.get("review_mutation_observations", {}).get(obs.stage)
        is_same_attempt = False
        if prior_obs and obs.attempt_id and prior_obs.get("attempt_id") and obs.attempt_id == prior_obs.get("attempt_id"):
            is_same_attempt = True

        if is_same_attempt:
            # Recheck of same attempt: retain prior cumulative drift and limitations
            if prior_obs.get("subject_drift_observed"):
                obs.subject_drift_observed = True
            if prior_obs.get("worktree_drift"):
                obs.worktree_drift = True
            if prior_obs.get("index_drift"):
                obs.index_drift = True
            if prior_obs.get("head_drift"):
                obs.head_drift = True
            if prior_obs.get("candidate_observation_unavailable"):
                obs.candidate_observation_unavailable = True
            if prior_obs.get("index_observation_unavailable"):
                obs.index_observation_unavailable = True
            if prior_obs.get("head_observation_unavailable"):
                obs.head_observation_unavailable = True
            if prior_obs.get("worktree_paths"):
                obs.worktree_paths = sorted(set(obs.worktree_paths) | set(prior_obs.get("worktree_paths") or []))
            if prior_obs.get("index_paths"):
                obs.index_paths = sorted(set(obs.index_paths) | set(prior_obs.get("index_paths") or []))
            prior_limits = prior_obs.get("observation_limitations") or prior_obs.get("limitations") or []
            if prior_limits:
                existing_kinds = {lim.get("kind") for lim in obs.observation_limitations if isinstance(lim, Mapping)}
                for plim in prior_limits:
                    if isinstance(plim, Mapping) and plim.get("kind") not in existing_kinds:
                        obs.observation_limitations.append(plim)
                        existing_kinds.add(plim.get("kind"))

    # Unavailability evaluates directly to ACTION_BLOCKED without being folded into drift
    if obs.head_drift or obs.head_observation_unavailable:
        obs.action_taken = ACTION_BLOCKED
        obs.diagnostic_code = READ_ONLY_STAGE_MUTATED_HEAD
        if obs.head_observation_unavailable or any(lim.get("kind") == "head_observation_unavailable" for lim in obs.observation_limitations):
            obs.detail = f"HEAD observation unavailable during read-only stage {obs.stage}: expected {obs.expected_head}"
        else:
            obs.detail = (
                f"HEAD movement observed during read-only stage {obs.stage}: "
                f"expected {obs.expected_head}, observed {obs.observed_head}"
            )
    elif obs.index_drift or obs.index_observation_unavailable:
        obs.action_taken = ACTION_BLOCKED
        obs.diagnostic_code = READ_ONLY_STAGE_MUTATED_INDEX
        if obs.index_observation_unavailable or any(lim.get("kind") == "index_observation_unavailable" for lim in obs.observation_limitations):
            obs.detail = f"staged index observation unavailable during read-only stage {obs.stage}"
        else:
            obs.detail = f"staged index changes observed during read-only stage {obs.stage}"
    elif obs.candidate_observation_unavailable:
        obs.action_taken = ACTION_BLOCKED
        obs.diagnostic_code = READ_ONLY_STAGE_MUTATED_CANDIDATE
        obs.detail = f"candidate observation unavailable during read-only stage {obs.stage}"
    elif obs.worktree_drift:
        if wt_policy == "block":
            obs.action_taken = ACTION_BLOCKED
            obs.diagnostic_code = READ_ONLY_STAGE_MUTATED_CANDIDATE
            obs.detail = (
                f"worktree mutation observed during read-only stage {obs.stage}: "
                f"{obs.worktree_paths}"
            )
        elif wt_policy == "warn":
            obs.action_taken = ACTION_WARNED
            obs.diagnostic_code = READ_ONLY_STAGE_MUTATED_CANDIDATE
            obs.detail = (
                f"worktree mutation observed during read-only stage {obs.stage} (warned): "
                f"{obs.worktree_paths}"
            )
        elif wt_policy == "allow":
            obs.action_taken = ACTION_ALLOWED
            obs.diagnostic_code = ""
            obs.detail = (
                f"worktree mutation observed during read-only stage {obs.stage} (allowed): "
                f"{obs.worktree_paths}"
            )
        else:
            obs.action_taken = ACTION_BLOCKED
            obs.diagnostic_code = READ_ONLY_STAGE_MUTATED_CANDIDATE
            obs.detail = f"unrecognized worktree policy {wt_policy!r}"
    else:
        obs.action_taken = ACTION_NONE
        obs.diagnostic_code = ""
        obs.detail = f"no review mutation drift observed during stage {obs.stage}"

    # Record into state without sticky drift overwriting: keep observations immutable
    if state is not None:
        obs_dict = obs.as_dict()
        observations_by_stage = state.setdefault("review_mutation_observations", {})
        observations_by_stage[obs.stage] = obs_dict
        state[f"{obs.stage}_mutation"] = obs_dict
        state.setdefault("review_mutation_observation_history", []).append(obs_dict)

        if obs.subject_drift_observed:
            state["subject_drift_observed"] = True

        if obs.worktree_paths:
            surviving = state.get("review_window_mutation_paths") or []
            state["review_window_mutation_paths"] = sorted(set(surviving) | set(obs.worktree_paths))

    if obs.action_taken == ACTION_BLOCKED:
        if state is not None:
            inval = obs.as_dict()
            binding = state.get("immutable_review_bindings", {}).get(obs.stage, {})
            if "subject" in binding:
                inval.setdefault("candidate_binding", binding["subject"])
                inval.setdefault("subject_binding", binding["subject"])
            elif obs.stage == "plan_review":
                inval.setdefault("candidate_binding", state.get("plan_candidate"))
                inval.setdefault("subject_binding", state.get("proposal_binding", state.get("plan_candidate")))
            elif obs.stage == "work_review":
                inval.setdefault("candidate_binding", state.get("produced_candidate"))
                inval.setdefault("subject_binding", state.get("produced_candidate"))
            normalizations = state.get("index_normalizations", [])
            latest = next((item for item in reversed(normalizations)
                           if item.get("stage") == obs.stage), {})
            if latest.get("reason"):
                inval.setdefault("index_normalization_reason", latest.get("reason"))
            state.setdefault("review_binding_invalidations", {})[obs.stage] = inval
            state["blocking_reason"] = {"code": obs.diagnostic_code, "detail": obs.detail}
            state["outcome"] = "blocked"

        if raise_on_block:
            from .dispatch import DispatchError
            from .failure_boundary import record_manager_attention

            if state is not None:
                record_manager_attention(
                    state,
                    reason="review_binding_invalidated",
                    detail=obs.detail + "; repository/candidate resolution and fresh review required",
                    paths=sorted(set(obs.worktree_paths + obs.index_paths)),
                    candidate_tree=obs.observed_tree,
                )
            raise DispatchError(obs.detail, obs.diagnostic_code)

    return obs


def derive_final_candidate_freshness(
    *,
    work_review_observation: ReviewObservation | Mapping[str, Any] | None,
    work_review_candidate_tree: str | None,
    terminal_candidate_tree: str | None,
    has_verified_receipt: bool = False,
    closer_mutated: bool = False,
) -> bool:
    """Derive truthful candidate freshness per ADR 0070 §2.4 (Manager Disposition M1).

    Freshness restoration is derived strictly from verified structured receipts verifying:
    1. Role Authority: Authorized independent work review role (Work Review / final_review).
       Plan Review never certifies work candidates per M1. Enforced at both caller boundary
       and observation-carried role/subject-kind. Requires positive work review role and subject kind.
    2. Exact Work Subject Identity: match all 4 candidate tree hashes:
       work_review_candidate_tree == terminal_candidate_tree == expected_tree == observed_tree.
    3. Zero Drift: Zero worktree, index, or HEAD drift occurred during that qualifying review turn.
       Rejects allow-mode drift.
    4. Observation Availability: Reject on any observation unavailability or review coverage limitation.
    5. Verified Structured Receipt: has_verified_receipt must be explicitly True.
    """
    if not has_verified_receipt:
        return False
    if not work_review_observation:
        return False
    if closer_mutated:
        return False

    obs_stage = (
        getattr(work_review_observation, "stage", None)
        if isinstance(work_review_observation, ReviewObservation)
        else work_review_observation.get("stage")
    )
    obs_role = (
        getattr(work_review_observation, "role", None)
        if isinstance(work_review_observation, ReviewObservation)
        else work_review_observation.get("role")
    )
    obs_subject_kind = (
        getattr(work_review_observation, "subject_kind", None)
        if isinstance(work_review_observation, ReviewObservation)
        else work_review_observation.get("subject_kind")
    )

    # Reject plan review
    if obs_stage in ("plan_review", "turn-02-plan-review"):
        return False

    # Positive requirement for work review role and subject kind
    role_norm = str(obs_role or "").strip().lower().replace(" ", "_")
    subject_norm = str(obs_subject_kind or "").strip().lower().replace(" ", "_")
    if role_norm not in ("work_reviewer", "reviewer"):
        return False
    if subject_norm not in ("work", "work_product"):
        return False

    # Extract observation candidate trees
    obs_exp_tree = (
        getattr(work_review_observation, "expected_tree", None)
        if isinstance(work_review_observation, ReviewObservation)
        else work_review_observation.get("expected_tree")
    )
    obs_obs_tree = (
        getattr(work_review_observation, "observed_tree", None)
        if isinstance(work_review_observation, ReviewObservation)
        else work_review_observation.get("observed_tree")
    )

    # Match all 4 candidate tree hashes
    if not work_review_candidate_tree or not terminal_candidate_tree or not obs_exp_tree or not obs_obs_tree:
        return False
    if not (str(work_review_candidate_tree) == str(terminal_candidate_tree) == str(obs_exp_tree) == str(obs_obs_tree)):
        return False

    # Observation unavailability checks
    cand_unavail = (
        getattr(work_review_observation, "candidate_observation_unavailable", False)
        if isinstance(work_review_observation, ReviewObservation)
        else work_review_observation.get("candidate_observation_unavailable", False)
    )
    idx_unavail = (
        getattr(work_review_observation, "index_observation_unavailable", False)
        if isinstance(work_review_observation, ReviewObservation)
        else work_review_observation.get("index_observation_unavailable", False)
    )
    hd_unavail = (
        getattr(work_review_observation, "head_observation_unavailable", False)
        if isinstance(work_review_observation, ReviewObservation)
        else work_review_observation.get("head_observation_unavailable", False)
    )
    paths_complete = (
        getattr(work_review_observation, "paths_complete", True)
        if isinstance(work_review_observation, ReviewObservation)
        else work_review_observation.get("paths_complete", True)
    )
    if cand_unavail or idx_unavail or hd_unavail or not paths_complete:
        return False

    # Review coverage limitations check
    limitations = (
        getattr(work_review_observation, "observation_limitations", [])
        if isinstance(work_review_observation, ReviewObservation)
        else (work_review_observation.get("limitations") or work_review_observation.get("observation_limitations") or [])
    )
    if limitations:
        return False

    # Git drift observation fields must be explicitly present and evaluated
    if isinstance(work_review_observation, Mapping):
        required_keys = (
            "subject_drift_observed",
            "worktree_drift",
            "index_drift",
            "head_drift",
            "expected_head",
            "observed_head",
            "expected_index",
            "observed_index",
        )
        if any(k not in work_review_observation or work_review_observation[k] is None for k in required_keys):
            return False

    obs_exp_head = (
        getattr(work_review_observation, "expected_head", None)
        if isinstance(work_review_observation, ReviewObservation)
        else work_review_observation.get("expected_head")
    )
    obs_obs_head = (
        getattr(work_review_observation, "observed_head", None)
        if isinstance(work_review_observation, ReviewObservation)
        else work_review_observation.get("observed_head")
    )
    obs_exp_idx = (
        getattr(work_review_observation, "expected_index", None)
        if isinstance(work_review_observation, ReviewObservation)
        else work_review_observation.get("expected_index")
    )
    obs_obs_idx = (
        getattr(work_review_observation, "observed_index", None)
        if isinstance(work_review_observation, ReviewObservation)
        else work_review_observation.get("observed_index")
    )

    # HEAD axis: require positive expected and observed evidence on both sides
    if not obs_exp_head or not obs_obs_head or not str(obs_exp_head).strip() or not str(obs_obs_head).strip():
        return False
    if str(obs_exp_head) != str(obs_obs_head):
        return False

    # Index axis: require positive expected and observed evidence on both sides
    # A characterized explicit index-absence value is evidence; None/missing is not.
    if obs_exp_idx is None or obs_obs_idx is None:
        return False
    if obs_exp_idx == "" or obs_obs_idx == "" or obs_exp_idx == {} or obs_obs_idx == {}:
        return False

    def _normalize_index_val(val: Any) -> Any:
        if isinstance(val, str):
            try:
                return json.loads(val)
            except Exception:
                return val
        return val

    if _normalize_index_val(obs_exp_idx) != _normalize_index_val(obs_obs_idx):
        return False

    # Drift checks: zero drift required, and reject allow-mode drift
    subj_drift = (
        getattr(work_review_observation, "subject_drift_observed", False)
        if isinstance(work_review_observation, ReviewObservation)
        else work_review_observation.get("subject_drift_observed", False)
    )
    wt_drift = (
        getattr(work_review_observation, "worktree_drift", False)
        if isinstance(work_review_observation, ReviewObservation)
        else work_review_observation.get("worktree_drift", False)
    )
    idx_drift = (
        getattr(work_review_observation, "index_drift", False)
        if isinstance(work_review_observation, ReviewObservation)
        else work_review_observation.get("index_drift", False)
    )
    hd_drift = (
        getattr(work_review_observation, "head_drift", False)
        if isinstance(work_review_observation, ReviewObservation)
        else work_review_observation.get("head_drift", False)
    )
    action_taken = (
        getattr(work_review_observation, "action_taken", ACTION_NONE)
        if isinstance(work_review_observation, ReviewObservation)
        else work_review_observation.get("action_taken", ACTION_NONE)
    )
    diag_code = (
        getattr(work_review_observation, "diagnostic_code", "")
        if isinstance(work_review_observation, ReviewObservation)
        else work_review_observation.get("diagnostic_code", "")
    )

    if subj_drift or wt_drift or idx_drift or hd_drift:
        return False
    if action_taken not in (ACTION_NONE, "none", ""):
        return False
    if diag_code:
        return False

    return True
