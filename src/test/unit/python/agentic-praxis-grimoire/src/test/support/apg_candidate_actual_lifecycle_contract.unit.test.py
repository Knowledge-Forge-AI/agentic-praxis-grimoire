"""Complete positive actual lifecycle states for APG60C."""
from __future__ import annotations

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
    materialize_actual_authored_proposed,
    materialize_actual_pre_authoring_absent,
    materialize_actual_rejected_preserved,
    materialize_actual_retained,
)
from apg_candidate_surface_contract import (  # noqa: E402
    SurfaceContractError,
    load_candidate_surface_manifest,
    load_removal_plan,
)
import apg_repository_path_contract as path_contract  # noqa: E402


CANDIDATE = "css-language-profile"
MANIFEST = load_candidate_surface_manifest(
    ROOT / "testing/apg-skill-candidate-surfaces.json", root=ROOT
)
PLAN = load_removal_plan(
    ROOT / "src/test/fixtures/apg60-css-removal-plan.json", root=ROOT
)
BY_ID = {owner["owner_id"]: owner for owner in PLAN["owners"]}
AUTHORING_REQUIRED = [
    *(BY_ID[owner_id] for owner_id in (
        *PLAN["closure_contracts"]["actual_lifecycle"]["authored_owner_ids"],
        "candidate-decision-record",
    )),
]


def _remove_entry(root: Path, entry: dict[str, object]) -> None:
    if "path" in entry:
        paths = [root / str(entry["path"])]
    else:
        paths = list(root.glob(str(entry["path_pattern"])))
    for path in paths:
        if path.is_file() or path.is_symlink():
            path.unlink()


def _externalize_directory(
    root: Path,
    external_root: Path,
    relative: str,
    *,
    target: str = "external",
) -> None:
    directory = root / relative
    if target == "dangling":
        directory.rename(external_root / "preserved")
        directory.symlink_to(external_root / "missing", target_is_directory=True)
        return
    destination = external_root / "owner"
    directory.rename(destination)
    if target == "in-repository":
        wrong = root / "wrong-owner"
        destination.rename(wrong)
        directory.symlink_to(wrong, target_is_directory=True)
        return
    directory.symlink_to(destination, target_is_directory=True)


def test_pre_authoring_absent_state_passes(tmp_path: Path) -> None:
    materialize_actual_pre_authoring_absent(tmp_path, MANIFEST, PLAN)
    assert_actual_pre_authoring_absent(tmp_path, MANIFEST, PLAN)


def test_authored_proposed_unintegrated_state_passes(
    tmp_path: Path,
) -> None:
    materialize_actual_authored_proposed(
        tmp_path, ROOT, MANIFEST, PLAN
    )
    assert_actual_authored_proposed_unintegrated(
        tmp_path, MANIFEST, PLAN, CANDIDATE
    )


@pytest.mark.parametrize("maturity", ("provisional", "stable"))
def test_retained_states_pass(tmp_path: Path, maturity: str) -> None:
    materialize_actual_retained(
        tmp_path,
        ROOT,
        PLAN,
        maturity=maturity,
    )
    assert_actual_retained(
        tmp_path, MANIFEST, PLAN, CANDIDATE, maturity
    )


def test_retained_evaluation_pins_one_physical_root(
    monkeypatch, tmp_path: Path
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    materialize_actual_retained(
        first,
        ROOT,
        PLAN,
        maturity="provisional",
    )
    materialize_actual_retained(
        second,
        ROOT,
        PLAN,
        maturity="provisional",
    )
    (second / "release/public-surface.json").unlink()
    repository_link = tmp_path / "repository"
    repository_link.symlink_to(first, target_is_directory=True)
    original = path_contract._read_chunk
    retargeted = False

    def retarget_root(descriptor: int, size: int) -> bytes:
        nonlocal retargeted
        if not retargeted:
            retargeted = True
            repository_link.unlink()
            repository_link.symlink_to(second, target_is_directory=True)
        return original(descriptor, size)

    monkeypatch.setattr(path_contract, "_read_chunk", retarget_root)
    assert_actual_retained(
        repository_link,
        MANIFEST,
        PLAN,
        CANDIDATE,
        "provisional",
    )
    assert retargeted


@pytest.mark.parametrize(
    ("actual_maturity", "requested_maturity"),
    (("stable", "provisional"), ("provisional", "stable")),
)
def test_retained_maturity_states_do_not_overlap(
    tmp_path: Path,
    actual_maturity: str,
    requested_maturity: str,
) -> None:
    materialize_actual_retained(
        tmp_path,
        ROOT,
        PLAN,
        maturity=actual_maturity,
    )
    with pytest.raises(SurfaceContractError, match="required retained state"):
        assert_actual_retained(
            tmp_path,
            MANIFEST,
            PLAN,
            CANDIDATE,
            requested_maturity,
        )


def test_rejected_preserved_state_passes(tmp_path: Path) -> None:
    materialize_actual_rejected_preserved(tmp_path, MANIFEST, PLAN)
    assert_actual_rejected_preserved(tmp_path, MANIFEST, PLAN)


def test_authored_state_cannot_pass_other_terminal_gates(
    tmp_path: Path,
) -> None:
    materialize_actual_authored_proposed(
        tmp_path, ROOT, MANIFEST, PLAN
    )
    _assert_other_state_gates_fail(
        tmp_path, "authored-proposed-unintegrated"
    )


def _assert_other_state_gates_fail(root: Path, actual_state: str) -> None:
    checks = {
        "pre-authoring-absent": lambda: assert_actual_pre_authoring_absent(
            root, MANIFEST, PLAN
        ),
        "authored-proposed-unintegrated": lambda: (
            assert_actual_authored_proposed_unintegrated(
                root, MANIFEST, PLAN, CANDIDATE
            )
        ),
        "retained-provisional": lambda: assert_actual_retained(
            root, MANIFEST, PLAN, CANDIDATE, "provisional"
        ),
        "retained-stable": lambda: assert_actual_retained(
            root, MANIFEST, PLAN, CANDIDATE, "stable"
        ),
        "rejected-preserved": lambda: assert_actual_rejected_preserved(
            root, MANIFEST, PLAN
        ),
    }
    for state, check in checks.items():
        if state == actual_state:
            check()
        else:
            with pytest.raises(SurfaceContractError):
                check()


def test_pre_authoring_state_satisfies_no_other_gate(
    tmp_path: Path,
) -> None:
    materialize_actual_pre_authoring_absent(tmp_path, MANIFEST, PLAN)
    _assert_other_state_gates_fail(tmp_path, "pre-authoring-absent")


@pytest.mark.parametrize("maturity", ("provisional", "stable"))
def test_each_retained_state_satisfies_no_other_gate(
    tmp_path: Path, maturity: str
) -> None:
    materialize_actual_retained(
        tmp_path,
        ROOT,
        PLAN,
        maturity=maturity,
    )
    _assert_other_state_gates_fail(tmp_path, f"retained-{maturity}")


def test_rejected_state_satisfies_no_other_gate(tmp_path: Path) -> None:
    materialize_actual_rejected_preserved(tmp_path, MANIFEST, PLAN)
    _assert_other_state_gates_fail(tmp_path, "rejected-preserved")


@pytest.mark.parametrize(
    "entry",
    AUTHORING_REQUIRED,
    ids=lambda entry: str(entry["owner_id"]),
)
def test_each_authored_state_owner_is_required(
    tmp_path: Path, entry: dict[str, object]
) -> None:
    materialize_actual_authored_proposed(
        tmp_path, ROOT, MANIFEST, PLAN
    )
    _remove_entry(tmp_path, entry)
    with pytest.raises(SurfaceContractError):
        assert_actual_authored_proposed_unintegrated(
            tmp_path, MANIFEST, PLAN, CANDIDATE
        )


@pytest.mark.parametrize(
    ("relative", "target"),
    (
        ("skills/css-language-profile", "external"),
        ("skills/css-language-profile", "in-repository"),
        ("skills/css-language-profile", "dangling"),
        ("docs/specs", "external"),
    ),
    ids=(
        "candidate-parent-external",
        "candidate-parent-wrong-target",
        "candidate-parent-dangling",
        "specification-parent-external",
    ),
)
def test_authored_state_rejects_symlinked_owner_ancestor(
    tmp_path: Path,
    relative: str,
    target: str,
) -> None:
    root = tmp_path / "repository"
    external = tmp_path / "external"
    external.mkdir()
    materialize_actual_authored_proposed(root, ROOT, MANIFEST, PLAN)
    _externalize_directory(root, external, relative, target=target)

    with pytest.raises(SurfaceContractError, match="ancestor|direct"):
        assert_actual_authored_proposed_unintegrated(
            root, MANIFEST, PLAN, CANDIDATE
        )
