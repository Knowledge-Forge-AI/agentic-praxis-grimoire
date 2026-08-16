"""Historical APG60F/APG60H and current APG60I phase-history controls."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
SUPPORT = ROOT / "src/test/support"
sys.path.insert(0, str(SUPPORT))

from apg_candidate_actual_lifecycle_contract import (  # noqa: E402
    assert_actual_authored_proposed_unintegrated,
    assert_actual_pre_authoring_absent,
    assert_actual_rejected_preserved,
    assert_actual_retained,
)
from apg_candidate_lifecycle_fixture import (  # noqa: E402
    materialize_actual_pre_authoring_absent,
    materialize_actual_authored_proposed,
    materialize_actual_rejected_preserved,
    materialize_actual_retained,
)
from apg_candidate_phase_history_contract import (  # noqa: E402
    assert_phase_bundles,
    load_phase_history,
    validate_phase_history,
)
from apg_candidate_surface_contract import (  # noqa: E402
    SurfaceContractError,
    load_candidate_surface_manifest,
    load_removal_plan,
)


CANDIDATE = "css-language-profile"
MANIFEST = load_candidate_surface_manifest(
    ROOT / "testing/apg-skill-candidate-surfaces.json", root=ROOT
)
PLAN = load_removal_plan(
    ROOT / "src/test/fixtures/apg60-css-removal-plan.json", root=ROOT
)
HISTORICAL_HISTORY_PATH = ROOT / "src/test/fixtures/apg60f-css-phase-history.json"
HISTORY_PATH = ROOT / "src/test/fixtures/apg60i-css-phase-history.json"
HISTORY = load_phase_history(HISTORY_PATH, ROOT)
BY_PHASE = {bundle["phase_id"]: bundle for bundle in HISTORY["bundles"]}


def test_apg60d_history_remains_byte_identical() -> None:
    historical = ROOT / "src/test/fixtures/apg60d-css-phase-history.json"
    assert hashlib.sha256(historical.read_bytes()).hexdigest() == (
        "71100b5d57b32d9a138cea97d100e1a5a25cb562ff7c4a0b5501be1444f6ebe0"
    )


def test_apg60e_history_remains_byte_identical() -> None:
    historical = ROOT / "src/test/fixtures/apg60e-css-phase-history.json"
    assert hashlib.sha256(historical.read_bytes()).hexdigest() == (
        "9092b284656be4f4d8278cf64178c6743509a450c4e5e8132aaa036e61867633"
    )


def test_apg60f_history_remains_byte_identical_and_valid() -> None:
    assert hashlib.sha256(HISTORICAL_HISTORY_PATH.read_bytes()).hexdigest() == (
        "9f960e63481c70e8ca5cb4c1def04f62148d00b1deecba49af5cf133fccffeff"
    )
    historical = load_phase_history(HISTORICAL_HISTORY_PATH, ROOT)
    assert [bundle["phase_id"] for bundle in historical["bundles"]] == [
        "APG58",
        "APG59",
        "APG60",
        "APG60A",
        "APG60B",
        "APG60C",
        "APG60D",
        "APG60E",
        "APG60F",
        "APG61",
        "APG62",
    ]


def test_apg60g_history_remains_byte_identical() -> None:
    historical = ROOT / "src/test/fixtures/apg60g-css-phase-history.json"
    assert hashlib.sha256(historical.read_bytes()).hexdigest() == (
        "597540a282d83643e9b8a48eef89c72ba5a8b23a2342f6667f788747bf1ebddd"
    )


def test_apg60h_history_remains_byte_identical_and_valid() -> None:
    historical_path = ROOT / "src/test/fixtures/apg60h-css-phase-history.json"
    assert hashlib.sha256(historical_path.read_bytes()).hexdigest() == (
        "35069cfffdd38fa292b4ebc321f0d14bfe6a8c8d85e256fbb0be6f0b5ad8c5e4"
    )
    historical = load_phase_history(historical_path, ROOT)
    assert [bundle["phase_id"] for bundle in historical["bundles"]][-3:] == [
        "APG60H",
        "APG61",
        "APG62",
    ]


def _repository_paths(phase_id: str) -> list[str]:
    bundle = BY_PHASE[phase_id]
    return [
        bundle["public_evaluation_path"],
        bundle["exit_path"],
        bundle["private_index_path"],
        *bundle["private_record_paths"],
    ]


@pytest.mark.parametrize(
    "relative",
    (
        "docs/evaluations/apg60c-css-runtime-and-terminal-lifecycle-closure.md",
        (
            "docs/status/2026/07/30/"
            "00083-apg60c-css-runtime-and-terminal-lifecycle-closure-exit.md"
        ),
        "private/evaluations/apg60c/README.md",
    ),
)
def test_pre_authoring_rejects_missing_apg60c_bundle(
    tmp_path: Path, relative: str
) -> None:
    materialize_actual_pre_authoring_absent(tmp_path, MANIFEST, PLAN)
    (tmp_path / relative).unlink()

    with pytest.raises(SurfaceContractError):
        assert_actual_pre_authoring_absent(tmp_path, MANIFEST, PLAN)


@pytest.mark.parametrize(
    "relative",
    (
        "docs/evaluations/apg60d-css-source-binding-and-history-closure.md",
        (
            "docs/status/2026/07/30/"
            "00084-apg60d-css-source-binding-and-history-closure-exit.md"
        ),
        "private/evaluations/apg60d/README.md",
    ),
)
def test_pre_authoring_rejects_missing_apg60d_bundle(
    tmp_path: Path, relative: str
) -> None:
    materialize_actual_pre_authoring_absent(tmp_path, MANIFEST, PLAN)
    (tmp_path / relative).unlink()

    with pytest.raises(SurfaceContractError):
        assert_actual_pre_authoring_absent(tmp_path, MANIFEST, PLAN)


@pytest.mark.parametrize(
    "relative",
    (
        (
            "docs/evaluations/"
            "apg60e-css-repository-path-and-candidate-surface-closure.md"
        ),
        (
            "docs/status/2026/07/30/"
            "00085-apg60e-css-repository-path-and-candidate-surface-closure-exit.md"
        ),
        "private/evaluations/apg60e/README.md",
    ),
)
def test_pre_authoring_rejects_missing_apg60e_bundle(
    tmp_path: Path, relative: str
) -> None:
    materialize_actual_pre_authoring_absent(tmp_path, MANIFEST, PLAN)
    (tmp_path / relative).unlink()

    with pytest.raises(SurfaceContractError):
        assert_actual_pre_authoring_absent(tmp_path, MANIFEST, PLAN)


@pytest.mark.parametrize(
    "relative",
    (
        (
            "docs/evaluations/"
            "apg60f-css-import-owner-and-projection-closure.md"
        ),
        (
            "docs/status/2026/07/30/"
            "00086-apg60f-css-import-owner-and-projection-closure-exit.md"
        ),
        "private/evaluations/apg60f/README.md",
    ),
)
def test_pre_authoring_rejects_missing_apg60f_bundle(
    tmp_path: Path, relative: str
) -> None:
    materialize_actual_pre_authoring_absent(tmp_path, MANIFEST, PLAN)
    (tmp_path / relative).unlink()

    with pytest.raises(SurfaceContractError):
        assert_actual_pre_authoring_absent(tmp_path, MANIFEST, PLAN)


@pytest.mark.parametrize("phase_id", ("apg61", "apg62"))
def test_retained_rejects_missing_apg61_and_apg62_history(
    tmp_path: Path, phase_id: str
) -> None:
    materialize_actual_retained(
        tmp_path,
        ROOT,
        PLAN,
        maturity="provisional",
    )
    (tmp_path / f"private/evaluations/{phase_id}/README.md").unlink()

    with pytest.raises(SurfaceContractError):
        assert_actual_retained(
            tmp_path, MANIFEST, PLAN, CANDIDATE, "provisional"
        )


def test_one_wildcard_file_cannot_satisfy_apg61_private_history(
    tmp_path: Path,
) -> None:
    materialize_actual_rejected_preserved(tmp_path, MANIFEST, PLAN)
    private_root = tmp_path / "private/evaluations/apg61"
    files = [path for path in private_root.rglob("*") if path.is_file()]
    for path in files[1:]:
        path.unlink()
    assert len([path for path in private_root.rglob("*") if path.is_file()]) == 1

    with pytest.raises(SurfaceContractError):
        assert_actual_rejected_preserved(tmp_path, MANIFEST, PLAN)


def test_external_symlink_cannot_satisfy_foundation_history(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repository"
    materialize_actual_pre_authoring_absent(root, MANIFEST, PLAN)
    relative = (
        "docs/evaluations/"
        "apg58-css-language-profile-pilot-authoring.md"
    )
    path = root / relative
    external = tmp_path / "external-history.md"
    external.write_text("external substitute\n", encoding="utf-8")
    path.unlink()
    path.symlink_to(external)

    with pytest.raises(SurfaceContractError):
        assert_actual_pre_authoring_absent(root, MANIFEST, PLAN)


def test_external_symlink_directory_cannot_supply_private_history(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repository"
    materialize_actual_pre_authoring_absent(root, MANIFEST, PLAN)
    phase_root = root / "private/evaluations/apg60c"
    external = tmp_path / "external-apg60c"
    phase_root.rename(external)
    phase_root.symlink_to(external, target_is_directory=True)

    with pytest.raises(SurfaceContractError, match="direct directories"):
        assert_phase_bundles(root, HISTORY, ["APG60C"])


def test_decision_adr_is_an_exact_required_bundle_owner(
    tmp_path: Path,
) -> None:
    materialize_actual_pre_authoring_absent(tmp_path, MANIFEST, PLAN)
    (tmp_path / BY_PHASE["APG58"]["decision_adr_path"]).unlink()

    with pytest.raises(SurfaceContractError, match="missing"):
        assert_phase_bundles(tmp_path, HISTORY, ["APG58"])


def test_decision_adr_roles_and_paths_are_frozen() -> None:
    adr_0035 = (
        "docs/adr/2026/07/"
        "0035-css-language-profile-and-policy-selected-structural-limits.md"
    )
    adr_0036 = (
        "docs/adr/2026/07/"
        "0036-css-language-profile-from-frozen-contract.md"
    )
    assert BY_PHASE["APG58"]["decision_adr_path"] == adr_0035
    assert BY_PHASE["APG58"]["decision_adr_role"] == "proposed-0035"
    assert BY_PHASE["APG59"]["decision_adr_path"] == adr_0035
    assert BY_PHASE["APG59"]["decision_adr_role"] == (
        "terminal-rejected-0035"
    )
    assert all(
        BY_PHASE[phase_id]["decision_adr_path"] is None
        for phase_id in (
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
        )
    )
    assert BY_PHASE["APG61"]["decision_adr_path"] == adr_0036
    assert BY_PHASE["APG61"]["decision_adr_role"] == "proposed-0036"
    assert BY_PHASE["APG62"]["decision_adr_path"] == adr_0036
    assert BY_PHASE["APG62"]["decision_adr_role"] == "terminal-0036"


def test_manifest_symlinked_ancestor_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    external = tmp_path / "external-fixtures"
    external.mkdir()
    external_manifest = external / HISTORY_PATH.name
    external_manifest.write_text(
        HISTORY_PATH.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    fixtures = root / "src/test/fixtures"
    fixtures.parent.mkdir(parents=True)
    fixtures.symlink_to(external, target_is_directory=True)

    with pytest.raises(SurfaceContractError, match="direct directories"):
        load_phase_history(fixtures / HISTORY_PATH.name, root)


def test_current_and_future_exit_identities_advance_through_apg60i() -> None:
    assert BY_PHASE["APG60F"]["exit_path"] == (
        "docs/status/2026/07/30/"
        "00086-apg60f-css-import-owner-and-projection-closure-exit.md"
    )
    assert BY_PHASE["APG60G"]["exit_path"] == (
        "docs/status/2026/07/30/"
        "00087-apg60g-css-snapshot-role-and-derived-set-closure-exit.md"
    )
    assert BY_PHASE["APG60H"]["exit_path"] == (
        "docs/status/2026/07/31/"
        "00088-apg60h-css-snapshot-and-full-path-binding-closure-exit.md"
    )
    assert BY_PHASE["APG60I"]["exit_path"] == (
        "docs/status/2026/07/31/"
        "00089-apg60i-worker-temp-binding-and-cleanup-closure-exit.md"
    )
    assert BY_PHASE["APG61"]["exit_path"] == (
        "docs/status/2026/07/31/00090-apg61-css-language-profile-authoring-exit.md"
    )
    assert BY_PHASE["APG62"]["exit_path"] == (
        "docs/status/2026/07/31/"
        "00091-apg62-css-language-profile-validation-and-integration-exit.md"
    )


@pytest.mark.parametrize(
    "relative",
    _repository_paths("APG61"),
    ids=lambda relative: Path(relative).name,
)
def test_authored_state_requires_each_exact_apg61_record(
    tmp_path: Path, relative: str
) -> None:
    materialize_actual_authored_proposed(tmp_path, ROOT, MANIFEST, PLAN)
    (tmp_path / relative).unlink()

    with pytest.raises(SurfaceContractError):
        assert_actual_authored_proposed_unintegrated(
            tmp_path, MANIFEST, PLAN, CANDIDATE
        )


@pytest.mark.parametrize("state", ("retained", "rejected"))
@pytest.mark.parametrize(
    "relative",
    [*_repository_paths("APG61"), *_repository_paths("APG62")],
    ids=lambda relative: relative.replace("/", "-"),
)
def test_terminal_states_require_each_apg61_and_apg62_record(
    tmp_path: Path, state: str, relative: str
) -> None:
    if state == "retained":
        materialize_actual_retained(
            tmp_path, ROOT, PLAN, maturity="stable"
        )
        check = lambda: assert_actual_retained(  # noqa: E731
            tmp_path, MANIFEST, PLAN, CANDIDATE, "stable"
        )
    else:
        materialize_actual_rejected_preserved(tmp_path, MANIFEST, PLAN)
        check = lambda: assert_actual_rejected_preserved(  # noqa: E731
            tmp_path, MANIFEST, PLAN
        )
    (tmp_path / relative).unlink()

    with pytest.raises(SurfaceContractError):
        check()


@pytest.mark.parametrize("substitution", ("dangling", "in-repository"))
def test_symlink_substitution_never_satisfies_history(
    tmp_path: Path, substitution: str
) -> None:
    materialize_actual_pre_authoring_absent(tmp_path, MANIFEST, PLAN)
    relative = BY_PHASE["APG60C"]["public_evaluation_path"]
    path = tmp_path / relative
    path.unlink()
    if substitution == "dangling":
        path.symlink_to("missing-history.md")
    else:
        wrong = path.with_name("wrong-history.md")
        wrong.write_text("wrong target\n", encoding="utf-8")
        path.symlink_to(wrong.name)

    with pytest.raises(SurfaceContractError, match="direct regular"):
        assert_actual_pre_authoring_absent(tmp_path, MANIFEST, PLAN)


def test_empty_placeholder_never_satisfies_history(tmp_path: Path) -> None:
    materialize_actual_pre_authoring_absent(tmp_path, MANIFEST, PLAN)
    path = tmp_path / BY_PHASE["APG60C"]["exit_path"]
    path.write_text(" \n", encoding="utf-8")

    with pytest.raises(SurfaceContractError, match="empty placeholder"):
        assert_actual_pre_authoring_absent(tmp_path, MANIFEST, PLAN)


@pytest.mark.parametrize(
    "mutator",
    (
        lambda value: value["bundles"][0].__setitem__("unknown", True),
        lambda value: value["bundles"][0]["private_record_paths"].append(
            value["bundles"][0]["private_record_paths"][0]
        ),
        lambda value: value["state_requirements"]["foundation_history"].remove(
            "APG60C"
        ),
    ),
    ids=("unknown-key", "duplicate-record", "missing-foundation-phase"),
)
def test_phase_history_schema_is_closed(mutator) -> None:
    value = deepcopy(HISTORY)
    mutator(value)

    with pytest.raises(SurfaceContractError):
        validate_phase_history(value)


def test_phase_history_requires_canonical_json(tmp_path: Path) -> None:
    path = tmp_path / "history.json"
    path.write_text(json.dumps(HISTORY), encoding="utf-8")

    with pytest.raises(SurfaceContractError, match="canonical JSON"):
        load_phase_history(path, tmp_path)


def test_future_private_record_names_are_frozen_exactly() -> None:
    assert BY_PHASE["APG61"]["private_record_paths"] == [
        "private/evaluations/apg61/apg60i-baseline-report-and-parity.md",
        "private/evaluations/apg61/clean-room-rights-privacy-and-personal-data-review.md",
        "private/evaluations/apg61/codex-apg62-handoff.md",
        "private/evaluations/apg61/contract-map-and-clause-review.md",
        "private/evaluations/apg61/css-candidate-authoring.md",
        "private/evaluations/apg61/css-source-rights-and-target-review.md",
        "private/evaluations/apg61/review-and-disposition.md",
    ]
    assert BY_PHASE["APG62"]["private_record_paths"] == [
        "private/evaluations/apg62/adr-0036-disposition.md",
        "private/evaluations/apg62/apg61-object-report-and-delivery-verification.md",
        "private/evaluations/apg62/clean-room-rights-privacy-and-personal-data-review.md",
        "private/evaluations/apg62/failing-first-and-semantic-contract-results.md",
        "private/evaluations/apg62/integration-or-removal-results.md",
        "private/evaluations/apg62/review-and-disposition.md",
        "private/evaluations/apg62/test-and-regression-results.md",
    ]
