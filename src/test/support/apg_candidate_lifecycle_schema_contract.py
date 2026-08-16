"""Closed schema validation for the APG60I candidate lifecycle."""

from __future__ import annotations

from typing import Any, Callable, NoReturn


Fail = Callable[[str], NoReturn]
ExactKeys = Callable[[dict[str, Any], set[str], str], None]

ACTUAL_STATES = [
    "pre-authoring-absent",
    "authored-proposed-unintegrated",
    "retained-provisional",
    "retained-stable",
    "rejected-preserved",
]
FOUNDATION_HISTORY = [
    "APG58",
    "APG59",
    "APG60",
    "APG60A",
    "APG60B",
    "APG60C",
    "APG60D",
    "APG60E",
    "APG60F",
    "APG60G",
    "APG60H",
    "APG60I",
]
AUTHORING_HISTORY = ["APG61"]
TERMINAL_HISTORY = ["APG62"]
PHASE_HISTORY_MANIFEST = "src/test/fixtures/apg60i-css-phase-history.json"
REPOSITORY_PATH_OWNERSHIP = (
    "physical-root-direct-ancestors-descriptor-relative-no-follow"
)
PROJECTION_OWNERSHIP = (
    "exact-relative-leaf-direct-ancestors-direct-canonical-target"
)
DYNAMIC_CONSUMER_ROOT_BINDING = (
    "pinned-root-descriptor-fchdir-parent-entry-revalidation"
)
DERIVED_SKILL_SET_CONTRACT = "exact-sorted-unique-direct-canonical-owner-set"
SEMANTIC_ROLE_REGISTRY = (
    "code-owned-registry-v1-independent-of-co-mutable-authority"
)
AUTHORITATIVE_REGULAR_FILE_READ = (
    "entry-descriptor-entry-bounded-complete-stable-open-object"
)
WORKER_TEMPORARY_STORAGE = (
    "caller-controlled-no-follow-open-root-descriptor-relative-child-"
    "parent-owned-cleanup"
)
SNAPSHOT_READ = "exact-declared-bytes-explicit-eof"
SNAPSHOT_CLEANUP = "lexical-absence-no-follow-parent-owned-timeout-cleanup"
PATH_ABSENCE_OBSERVATION = "missing-component-before-revalidate-after"
PINNED_ROOT_FINAL_BINDING = "before-and-immediately-before-success"
PROJECTION_IDENTITY = "retained-no-follow-handle-platform-fail-closed"


def validate_manifest_lifecycle_schema(
    lifecycle: dict[str, Any],
    *,
    exact_keys: ExactKeys,
    fail: Fail,
) -> None:
    """Validate the manifest's closed APG60I lifecycle declaration."""
    exact_keys(
        lifecycle,
        {
            "authoritative_regular_file_read",
            "actual_states",
            "current_survivor_ownership",
            "derived_skill_set_contract",
            "dynamic_consumer_root_binding",
            "history_requirement",
            "narrative_authority",
            "narrative_diagnostics",
            "python_arbitrary_caller_mutation",
            "python_reflective_call_effects",
            "python_runtime_value_authority",
            "python_source_binding",
            "projection_ownership",
            "projection_identity",
            "path_absence_observation",
            "pinned_root_final_binding",
            "repository_path_ownership",
            "semantic_role_registry",
            "snapshot_cleanup",
            "snapshot_read",
            "worker_temporary_storage",
        },
        "manifest lifecycle contracts",
    )
    if lifecycle != {
        "authoritative_regular_file_read": AUTHORITATIVE_REGULAR_FILE_READ,
        "actual_states": ACTUAL_STATES,
        "current_survivor_ownership": "direct-regular-no-follow",
        "derived_skill_set_contract": DERIVED_SKILL_SET_CONTRACT,
        "dynamic_consumer_root_binding": DYNAMIC_CONSUMER_ROOT_BINDING,
        "history_requirement": "closed-exact-phase-bundles-direct-regular-no-follow",
        "narrative_authority": "exact-marker",
        "narrative_diagnostics": "bounded-vocabulary-human-review-required",
        "python_arbitrary_caller_mutation": "outside-static-source-proof",
        "python_reflective_call_effects": "outside-static-syntactic-proof",
        "python_runtime_value_authority": "not-used",
        "python_source_binding": (
            "exact-static-declaration-mechanical-write-refusal"
        ),
        "projection_ownership": PROJECTION_OWNERSHIP,
        "projection_identity": PROJECTION_IDENTITY,
        "path_absence_observation": PATH_ABSENCE_OBSERVATION,
        "pinned_root_final_binding": PINNED_ROOT_FINAL_BINDING,
        "repository_path_ownership": REPOSITORY_PATH_OWNERSHIP,
        "semantic_role_registry": SEMANTIC_ROLE_REGISTRY,
        "snapshot_cleanup": SNAPSHOT_CLEANUP,
        "snapshot_read": SNAPSHOT_READ,
        "worker_temporary_storage": WORKER_TEMPORARY_STORAGE,
    }:
        fail("manifest APG60I lifecycle contracts are invalid")


def validate_actual_lifecycle_schema(
    lifecycle: dict[str, Any],
    *,
    exact_keys: ExactKeys,
    fail: Fail,
) -> None:
    """Validate the closed actual-state and history schema."""
    exact_keys(
        lifecycle,
        {
            "authored_owner_ids",
            "authoritative_regular_file_read",
            "authoring_history",
            "current_survivor_ownership",
            "derived_skill_set_contract",
            "dynamic_consumer_root_binding",
            "history_requirement",
            "integrated_count",
            "foundation_history",
            "phase_history_manifest",
            "path_absence_observation",
            "pinned_root_final_binding",
            "projection_identity",
            "projection_ownership",
            "repository_path_ownership",
            "semantic_role_registry",
            "snapshot_cleanup",
            "snapshot_read",
            "states",
            "terminal_history",
            "worker_temporary_storage",
        },
        "actual lifecycle closure",
    )
    if (
        lifecycle["authoritative_regular_file_read"]
        != AUTHORITATIVE_REGULAR_FILE_READ
        or lifecycle["derived_skill_set_contract"]
        != DERIVED_SKILL_SET_CONTRACT
        or lifecycle["dynamic_consumer_root_binding"]
        != DYNAMIC_CONSUMER_ROOT_BINDING
        or lifecycle["states"] != ACTUAL_STATES
        or lifecycle["authored_owner_ids"]
        != [
            "canonical-leaf",
            "candidate-contract-map",
            "candidate-specification",
        ]
        or lifecycle["current_survivor_ownership"]
        != "direct-regular-no-follow"
        or lifecycle["history_requirement"] != "closed-exact-phase-bundles"
        or lifecycle["integrated_count"] != 28
        or lifecycle["phase_history_manifest"] != PHASE_HISTORY_MANIFEST
        or lifecycle["projection_ownership"] != PROJECTION_OWNERSHIP
        or lifecycle["projection_identity"] != PROJECTION_IDENTITY
        or lifecycle["path_absence_observation"]
        != PATH_ABSENCE_OBSERVATION
        or lifecycle["pinned_root_final_binding"]
        != PINNED_ROOT_FINAL_BINDING
        or lifecycle["repository_path_ownership"]
        != REPOSITORY_PATH_OWNERSHIP
        or lifecycle["semantic_role_registry"] != SEMANTIC_ROLE_REGISTRY
        or lifecycle["snapshot_cleanup"] != SNAPSHOT_CLEANUP
        or lifecycle["snapshot_read"] != SNAPSHOT_READ
        or lifecycle["worker_temporary_storage"]
        != WORKER_TEMPORARY_STORAGE
    ):
        fail("APG60I actual lifecycle closure contract is invalid")
    expected_history = {
        "foundation_history": FOUNDATION_HISTORY,
        "authoring_history": AUTHORING_HISTORY,
        "terminal_history": TERMINAL_HISTORY,
    }
    for group, expected in expected_history.items():
        if lifecycle[group] != expected:
            fail(f"{group} lifecycle history is not contract-exact")


def validate_narrative_schema(
    narrative: dict[str, Any],
    *,
    exact_keys: ExactKeys,
    fail: Fail,
) -> None:
    """Validate exact marker authority and truthful diagnostic scope."""
    exact_keys(
        narrative,
        {
            "current_state",
            "diagnostic_scope",
            "human_review",
            "marker_syntax",
            "mechanical_authority",
            "states",
        },
        "narrative-state closure",
    )
    if narrative != {
        "current_state": "absent",
        "diagnostic_scope": "frozen-bounded-vocabulary",
        "human_review": "required-for-arbitrary-prose",
        "marker_syntax": (
            "<!-- APG-CANDIDATE-STATE: {candidate_id} {state} -->"
        ),
        "mechanical_authority": "exact-marker",
        "states": [
            "absent",
            "retained-provisional",
            "retained-stable",
        ],
    }:
        fail("narrative-state closure contract is invalid")


def validate_python_source_binding_schema(
    source_binding: dict[str, Any],
    *,
    fail: Fail,
) -> None:
    """Validate the truthful static source-binding declaration."""
    if source_binding != {
        "arbitrary_caller_mutation_scope": "outside-static-source-proof",
        "assignment_count": 1,
        "binding_scope": "module-and-nested-syntactic-bindings",
        "collection": "immutable-static",
        "dynamic_write_policy": "reject-mechanically-identifiable",
        "projection_derivation": "exact-audited-skills",
        "proof_scope": (
            "exact static owner declaration and mechanically identifiable "
            "protected-name write refusal"
        ),
        "reflective_call_effect_scope": "outside-static-syntactic-proof",
        "runtime_value_authority": "not-used",
    }:
        fail("Python source-binding closure contract is invalid")
