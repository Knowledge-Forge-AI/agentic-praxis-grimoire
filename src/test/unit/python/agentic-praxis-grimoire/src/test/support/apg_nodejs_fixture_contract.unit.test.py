#!/usr/bin/env python3
"""Unit evidence for the maintained APG81 Node fixture contract."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src/test/support"))

from apg_nodejs_fixture_contract import (  # noqa: E402
    ContractError,
    load_manifest,
    validate_fixture,
    validate_threat_model,
)


FIXTURE = ROOT / "src/test/fixtures/apg80-nodejs-runtime-cli"
THREAT_MODEL = ROOT / "testing/nodejs-profile-qualification-threat-model.json"


def test_current_fixture_projection_is_closed() -> None:
    validate_fixture(FIXTURE, load_manifest(FIXTURE / "fixture-manifest.json"))
    validate_threat_model(load_manifest(THREAT_MODEL))


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("continuous_identity_claim", "continuous"),
        ("same_uid_adversary", "prevented"),
        ("security_boundary", "scratch"),
        ("shell", "allowed"),
        ("fixture_network", "allowed"),
        ("application_package_installation", "allowed"),
        ("runtime_binding", "copied-sealed-runtime"),
        ("cleanup_policy", "fail-fast"),
    ],
)
def test_threat_model_rejects_overclaim_and_boundary_mutations(
    field: str, replacement: str
) -> None:
    value = deepcopy(load_manifest(THREAT_MODEL))
    value[field] = replacement
    with pytest.raises(ContractError, match="threat-model projection"):
        validate_threat_model(value)


def test_digest_and_mixed_state_mutations_are_rejected() -> None:
    manifest = load_manifest(FIXTURE / "fixture-manifest.json")
    digest_mutation = deepcopy(manifest)
    digest_mutation["artifacts"][0]["content_sha256"] = "0" * 64
    with pytest.raises(ContractError, match="exact authority projection"):
        validate_fixture(FIXTURE, digest_mutation)
    state_mutation = deepcopy(manifest)
    mapping = next(case for case in state_mutation["cases"] if case["id"] == "APG80-FX-002")
    mapping["completion_state"] = "owned-complete"
    with pytest.raises(ContractError, match="exact authority projection"):
        validate_fixture(FIXTURE, state_mutation)


def test_missing_and_foreign_artifact_states_are_rejected(tmp_path: Path) -> None:
    manifest = deepcopy(load_manifest(FIXTURE / "fixture-manifest.json"))
    mapping = next(case for case in manifest["cases"] if case["id"] == "APG80-FX-002")
    mapping["artifact_states"].pop()
    with pytest.raises(ContractError, match="exact authority projection"):
        validate_fixture(FIXTURE, manifest)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value["artifacts"][0].update(whole_file_owner="javascript-language-profile"),
        lambda value: value["artifacts"][0].update(runtime_role_state="not-invoked"),
        lambda value: value["artifacts"][0].update(rollback="remove-with-apg80-candidate"),
        lambda value: value["cases"][2].update(selection="route-to-owner"),
        lambda value: value["cases"][2].update(response="stop-and-escalate"),
        lambda value: value["cases"][2].update(completion_state="stopped-required-evidence"),
        lambda value: value["cases"][5].update(routes_or_obligations=[]),
        lambda value: value["cases"][2]["artifact_ids"].pop(),
    ],
)
def test_every_consequence_bearing_fixture_projection_is_exact(mutation) -> None:
    manifest = deepcopy(load_manifest(FIXTURE / "fixture-manifest.json"))
    mutation(manifest)
    with pytest.raises(ContractError, match="exact authority projection"):
        validate_fixture(FIXTURE, manifest)
