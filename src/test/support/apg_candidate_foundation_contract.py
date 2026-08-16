"""Versioned APG candidate foundation contracts shared by current schemas."""

from __future__ import annotations

from typing import Any, Callable, NoReturn

from apg_candidate_lifecycle_schema_contract import (
    DERIVED_SKILL_SET_CONTRACT,
    DYNAMIC_CONSUMER_ROOT_BINDING,
    SEMANTIC_ROLE_REGISTRY,
)


ExactKeys = Callable[[dict[str, Any], set[str], str], None]
Fail = Callable[[str], NoReturn]


def validate_foundation_closure_contracts(
    closure: dict[str, Any],
    *,
    exact_keys: ExactKeys,
    fail: Fail,
) -> None:
    """Validate APG60G runtime, set, and registry authority declarations."""

    dynamic_consumer = closure["dynamic_consumer"]
    exact_keys(
        dynamic_consumer,
        {
            "descriptor_cleanup",
            "root_binding",
            "root_entry_revalidation",
            "runtime_observation",
            "source_collection",
        },
        "dynamic-consumer closure",
    )
    if dynamic_consumer != {
        "descriptor_cleanup": "parent-and-worker-finally-close",
        "root_binding": DYNAMIC_CONSUMER_ROOT_BINDING,
        "root_entry_revalidation": "before-launch-during-worker-after-worker",
        "runtime_observation": "inherited-root-descriptor-fchdir-relative",
        "source_collection": "descriptor-relative-closed-transitive-import-set",
    }:
        fail("dynamic-consumer closure contract is invalid")

    derived_skill_set = closure["derived_skill_set"]
    exact_keys(
        derived_skill_set,
        {
            "candidate_diagnostic",
            "comparison",
            "expected_source",
            "name_grammar",
            "ordering",
        },
        "derived-skill-set closure",
    )
    if derived_skill_set != {
        "candidate_diagnostic": "explanatory-only",
        "comparison": "topology-library-installer-exact-set",
        "expected_source": "direct-canonical-leaves",
        "name_grammar": "lowercase-dash-safe-component",
        "ordering": "sorted-unique",
    }:
        fail("derived-skill-set closure contract is invalid")

    semantic_registry = closure["semantic_role_registry"]
    exact_keys(
        semantic_registry,
        {
            "authority",
            "extension_policy",
            "path",
            "required_role_count",
            "schema_version",
        },
        "semantic-role registry closure",
    )
    if semantic_registry != {
        "authority": SEMANTIC_ROLE_REGISTRY,
        "extension_policy": "additive-unrelated-no-shadow",
        "path": "src/test/support/apg_candidate_required_role_registry.py",
        "required_role_count": 52,
        "schema_version": 1,
    }:
        fail("semantic-role registry closure contract is invalid")
