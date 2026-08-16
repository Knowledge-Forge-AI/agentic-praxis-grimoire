"""Mechanical APG81 contract for the Node.js fixture and artifact projection."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, NoReturn


class ContractError(ValueError):
    """A maintained Node fixture surface is malformed."""


MANIFEST_PROJECTION_SHA256 = "a78ace8c41d7bfcd907d92f8f66e84702bfb159da110ed6c5b7efcfd8e45ca0c"
THREAT_MODEL_PROJECTION_SHA256 = "2d101e04d010dd277e6f0b2acff51834fe702c282be9382ed055145c92a5a21a"


def fail(message: str) -> NoReturn:
    raise ContractError(message)


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            fail(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def load_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_object)
    if not isinstance(value, dict):
        fail("Node fixture manifest is not an object")
    return value


def validate_threat_model(value: dict[str, Any]) -> None:
    """Require the exact controlled-qualification threat-model projection."""
    projection = json.dumps(
        value, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    if hashlib.sha256(projection).hexdigest() != THREAT_MODEL_PROJECTION_SHA256:
        fail("Node qualification threat-model projection is invalid")
    required = {
        "execution_context": "controlled-local-or-ci-qualification",
        "trusted_fixture_provenance": "apg-owned-reviewed",
        "runtime_binding": "exact-pre-and-post-observation",
        "runtime_acquisition": "exact-existing-or-preinstalled-nvm",
        "continuous_identity_claim": "none",
        "same_uid_adversary": "excluded-route-to-security-owner",
        "security_boundary": "none",
        "shell": "prohibited-for-maintained-fixture-invocation",
        "fixture_network": "prohibited",
        "application_package_installation": "prohibited",
        "scratch_owner": "assignment-owned-external-direct-directory",
        "symlink_policy": "refuse-preexisting-at-preflight",
        "environment_policy": "exact-closed-synthetic-allowlist",
        "cleanup_policy": "attempt-all-and-verify-before-success",
        "failure_policy": "fail-closed-with-redacted-contract-id",
    }
    if value.get("schema_version") != 1 or any(value.get(key) != item for key, item in required.items()):
        fail("Node qualification threat-model closed value is invalid")
    forbidden = set(value.get("forbidden_input_classes", []))
    if forbidden != {
        "credential-bearing-code-or-data",
        "secret-bearing-code-or-data",
        "target-code",
        "untrusted-fixture",
        "user-code",
    }:
        fail("Node qualification forbidden input classes are invalid")


def validate_fixture(root: Path, manifest: dict[str, Any]) -> None:
    if set(manifest) != {
        "artifacts", "authority", "cases", "documentation_artifacts", "fixture",
        "invariants", "lifecycle", "schema_version", "vocabulary"
    }:
        fail("Node fixture top-level schema is invalid")
    if manifest["schema_version"] != 1:
        fail("Node fixture schema version is invalid")
    projection = json.dumps(
        manifest, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    if hashlib.sha256(projection).hexdigest() != MANIFEST_PROJECTION_SHA256:
        fail("Node fixture exact authority projection is invalid")
    artifacts = manifest["artifacts"]
    cases = manifest["cases"]
    vocabulary = manifest["vocabulary"]
    if not isinstance(artifacts, list) or len(artifacts) != 41:
        fail("Node fixture must own exactly 41 substantive artifacts")
    if not isinstance(cases, list) or [case.get("id") for case in cases] != [
        f"APG80-FX-{index:03d}" for index in range(1, 15)
    ]:
        fail("Node fixture must retain 14 ordered case identities")
    artifact_ids = [row.get("artifact_id") for row in artifacts]
    paths = [row.get("relative_path") for row in artifacts]
    if len(set(artifact_ids)) != len(artifact_ids) or len(set(paths)) != len(paths):
        fail("Node fixture artifact ownership is duplicated")
    case_ownership = Counter(
        artifact_id for case in cases for artifact_id in case.get("artifact_ids", [])
    )
    if case_ownership != Counter({artifact_id: 1 for artifact_id in artifact_ids}):
        fail("Node fixture artifacts must have exact single-case ownership")
    for row in artifacts:
        relative = row.get("relative_path")
        expected_hash = row.get("content_sha256")
        if not isinstance(relative, str) or Path(relative).is_absolute() or ".." in Path(relative).parts:
            fail("Node fixture artifact path escapes its root")
        path = root / relative
        if not path.is_file() or path.is_symlink():
            fail(f"Node fixture artifact is not a direct regular file: {relative}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected_hash:
            fail(f"Node fixture artifact digest mismatch: {relative}")
        if row.get("rollback") != "preserve-with-candidate-history":
            fail(f"Node fixture artifact rollback is not history preserving: {relative}")
        vocabulary_fields = {
            "artifact_class": "artifact_classes",
            "exact_runtime_binding_state": "exact_runtime_binding_states",
            "external_effect_class": "external_effect_classes",
            "invocation_state": "invocation_states",
            "loader_role_state": "loader_role_states",
            "mapping_evidence_state": "mapping_evidence_states",
            "module_mapping": "module_mappings",
            "package_manager_role_state": "package_manager_role_states",
            "runtime_role_state": "runtime_role_states",
            "whole_file_owner": "whole_file_owners",
        }
        for field, vocabulary_field in vocabulary_fields.items():
            if row.get(field) not in vocabulary.get(vocabulary_field, []):
                fail(f"Node fixture artifact has an unowned {field}: {relative}")
    substantive = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name not in {"README.md", "fixture-manifest.json"}
    }
    if substantive != set(paths):
        fail("Node fixture artifact projection is incomplete or contains foreign files")
    documentation = manifest["documentation_artifacts"]
    if not isinstance(documentation, list) or len(documentation) != 2:
        fail("Node fixture documentation projection is invalid")
    if any(row.get("rollback") != "preserve-with-candidate-history" for row in documentation):
        fail("Node fixture documentation rollback is not history preserving")
    lifecycle = manifest["lifecycle"]
    if lifecycle != {
        "authored_by_phase_id": "APG80",
        "candidate_state": "provisionally-integrated",
        "current_phase_id": "APG81H",
        "is_maintained_test_owner": True,
        "is_oracle": False,
        "round_state": "terminal-repair-checkpoint-complete",
    }:
        fail("Node fixture lifecycle and correction-round states are invalid")
    readme = next(row for row in documentation if row["artifact_id"] == "fixture-readme")
    if hashlib.sha256((root / "README.md").read_bytes()).hexdigest() != readme["content_sha256"]:
        fail("Node fixture README digest mismatch")
    mapping = next(case for case in cases if case["id"] == "APG80-FX-002")
    states = mapping.get("artifact_states")
    if not isinstance(states, list) or {item.get("artifact_id") for item in states} != set(mapping["artifact_ids"]):
        fail("Node mapping case lacks exact per-artifact states")
    unresolved = next(item for item in states if item["artifact_id"] == "mapping-typeless-goal-neutral")
    if unresolved != {
        "artifact_id": "mapping-typeless-goal-neutral",
        "availability": "present",
        "mapping_state": "unresolved",
        "response": "stop-and-escalate",
        "selection": "selected",
    }:
        fail("goal-neutral mapping does not remain an explicit stop")
    if mapping["completion_state"] != "stopped-required-evidence" or mapping["response"] != "stop-and-escalate":
        fail("mixed mapping case is flattened into false completion")
    required = {
        "mapping-commonjs-scope-module-only",
        "typescript-erasable",
        "typescript-nonerasable",
    }
    if not required <= set(artifact_ids):
        fail("Node contrasting mapping or TypeScript artifacts are absent")
    filesystem = (root / "process/filesystem.mjs").read_text(encoding="utf-8")
    for token in (
        "filesystemCaseDirectory",
        "realpath(filesystemCaseDirectory)",
        "isSymbolicLink()",
        "APG81A filesystem case rejected",
    ):
        if token not in filesystem:
            fail("Node filesystem fixture does not enforce its scratch boundary")
    for retired in ("ownedScratchRoot", "beforeCreate", "constants.O_NOFOLLOW"):
        if retired in filesystem:
            fail("Node filesystem fixture retains retired containment machinery")
