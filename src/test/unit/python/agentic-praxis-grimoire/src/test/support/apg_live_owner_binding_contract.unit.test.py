"""Failing-first exact Python-owner bindings for APG60B."""
from __future__ import annotations

import importlib
from pathlib import Path
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
SUPPORT = ROOT / "src/test/support"
sys.path.insert(0, str(SUPPORT))

from apg_candidate_surface_contract import SurfaceContractError  # noqa: E402
from apg_live_owner_binding_contract import (  # noqa: E402
    assert_audited_assignment,
    assert_bound_assignment,
)


CANDIDATE = "css-language-profile"


def _module():
    return importlib.import_module("apg_actual_retained_surface_contract")


@pytest.mark.parametrize(
    ("owner_id", "relative", "expected_key"),
    (
        (
            "project-integration-mirror",
            "project_mirror.py",
            "candidate",
        ),
        (
            "release-integration-mirror",
            "release_mirror.py",
            "release",
        ),
    ),
)
def test_unrelated_assignment_cannot_satisfy_bound_owner(
    tmp_path: Path,
    owner_id: str,
    relative: str,
    expected_key: str,
) -> None:
    path = tmp_path / relative
    unrelated = (
        CANDIDATE
        if expected_key == "candidate"
        else f"skills/{CANDIDATE}/SKILL.md"
    )
    path.write_text(
        f"UNRELATED = ({unrelated!r},)\n"
        "EXPECTED_SKILLS = ()\n"
        "EXPECTED_SURFACES = ()\n",
        encoding="utf-8",
    )
    owner = {"owner_id": owner_id, "path": relative}
    expected = {
        "candidate": [CANDIDATE],
        "release": [f"skills/{CANDIDATE}/SKILL.md"],
    }
    handler = (
        _module()._assert_project_owner
        if expected_key == "candidate"
        else _module()._assert_release_or_registry_owner
    )

    with pytest.raises(SurfaceContractError, match=owner_id):
        handler(tmp_path, owner, CANDIDATE, expected)


def test_exact_bound_assignment_ignores_unrelated_strings(
    tmp_path: Path,
) -> None:
    path = tmp_path / "mirror.py"
    path.write_text(
        'UNRELATED = ("css-language-profile-extra",)\n'
        'EXPECTED_SKILLS = ("css-language-profile",)\n',
        encoding="utf-8",
    )
    owner = {"owner_id": "project-integration-mirror", "path": "mirror.py"}
    assert_bound_assignment(
        tmp_path,
        owner,
        CANDIDATE,
        [CANDIDATE],
        "EXPECTED_SKILLS",
    )


@pytest.mark.parametrize(
    "values",
    (
        (),
        ("css-language-profile", "css-language-profile"),
        ("css-language-profile-extra",),
    ),
)
def test_partial_duplicate_or_wrong_bound_value_fails(
    tmp_path: Path, values: tuple[str, ...]
) -> None:
    path = tmp_path / "mirror.py"
    path.write_text(f"EXPECTED_SKILLS = {values!r}\n", encoding="utf-8")
    owner = {"owner_id": "project-integration-mirror", "path": "mirror.py"}
    with pytest.raises(SurfaceContractError, match="EXPECTED_SKILLS"):
        assert_bound_assignment(
            tmp_path,
            owner,
            CANDIDATE,
            [CANDIDATE],
            "EXPECTED_SKILLS",
        )


def test_missing_bound_variable_fails(tmp_path: Path) -> None:
    (tmp_path / "mirror.py").write_text(
        'UNRELATED = ("css-language-profile",)\n',
        encoding="utf-8",
    )
    owner = {"owner_id": "project-integration-mirror", "path": "mirror.py"}
    with pytest.raises(SurfaceContractError, match="missing"):
        assert_bound_assignment(
            tmp_path,
            owner,
            CANDIDATE,
            [CANDIDATE],
            "EXPECTED_SKILLS",
        )


def test_empty_derived_projection_value_fails(tmp_path: Path) -> None:
    path = tmp_path / "apg_public_release.py"
    path.write_text(
        'AUDITED_SKILLS = ("skills/css-language-profile/SKILL.md",)\n'
        "AUDITED_PROJECTIONS = () if AUDITED_SKILLS else ()\n",
        encoding="utf-8",
    )
    owner = {
        "owner_id": "release-helper-audited-projections",
        "path": "apg_public_release.py",
    }
    expected = {
        "skills": ["skills/css-language-profile/SKILL.md"],
        "projections": [".agents/skills/css-language-profile"],
    }
    with pytest.raises(
        SurfaceContractError,
        match="release-helper-audited-projections",
    ):
        _module()._assert_release_helper(
            tmp_path, owner, CANDIDATE, expected
        )

def test_approved_exact_derived_projection_value_passes(
    tmp_path: Path,
) -> None:
    path = tmp_path / "apg_public_release.py"
    path.write_text(
        "from pathlib import PurePosixPath\n"
        'AUDITED_SKILLS = ("skills/css-language-profile/SKILL.md",)\n'
        "AUDITED_PROJECTIONS = tuple(sorted(\n"
        '    f".agents/skills/{PurePosixPath(path).parent.name}"\n'
        "    for path in AUDITED_SKILLS\n"
        "))\n",
        encoding="utf-8",
    )
    owner = {
        "owner_id": "release-helper-audited-projections",
        "path": "apg_public_release.py",
    }
    expected = {
        "skills": ["skills/css-language-profile/SKILL.md"],
        "projections": [".agents/skills/css-language-profile"],
    }
    assert _module()._assert_release_helper(
        tmp_path, owner, CANDIDATE, expected
    )


def test_closed_audited_derivation_does_not_execute_module_side_effects(
    tmp_path: Path,
) -> None:
    path = tmp_path / "apg_public_release.py"
    sentinel = tmp_path / "executed"
    path.write_text(
        "from pathlib import Path, PurePosixPath\n"
        'AUDITED_SKILLS = ("skills/css-language-profile/SKILL.md",)\n'
        "AUDITED_PROJECTIONS = tuple(sorted(\n"
        '    f".agents/skills/{PurePosixPath(path).parent.name}"\n'
        "    for path in AUDITED_SKILLS\n"
        "))\n"
        f"Path({str(sentinel)!r}).write_text('executed')\n",
        encoding="utf-8",
    )
    owner = {
        "owner_id": "release-helper-audited-projections",
        "path": "apg_public_release.py",
    }
    expected = {
        "skills": ["skills/css-language-profile/SKILL.md"],
        "projections": [".agents/skills/css-language-profile"],
    }

    assert _module()._assert_release_helper(
        tmp_path, owner, CANDIDATE, expected
    )
    assert not sentinel.exists()


@pytest.mark.parametrize(
    "private_path",
    ("/" "Users/private/release-path", "~/private/release", "C:/private/release"),
)
def test_audited_family_rejects_private_nonrelative_members(
    tmp_path: Path, private_path: str
) -> None:
    path = tmp_path / "apg_public_release.py"
    path.write_text(
        "AUDITED_SKILLS = ("
        '"skills/css-language-profile/SKILL.md", '
        f"{private_path!r})\n",
        encoding="utf-8",
    )
    owner = {
        "owner_id": "release-helper-audited-skills",
        "path": "apg_public_release.py",
    }
    with pytest.raises(SurfaceContractError, match="private or nonrelative"):
        assert_audited_assignment(
            tmp_path,
            owner,
            CANDIDATE,
            ["skills/css-language-profile/SKILL.md"],
            "AUDITED_SKILLS",
        )


def test_wrong_or_duplicate_actual_projection_value_fails(
    tmp_path: Path,
) -> None:
    path = tmp_path / "apg_public_release.py"
    path.write_text(
        'AUDITED_SKILLS = ("skills/css-language-profile/SKILL.md",)\n'
        "AUDITED_PROJECTIONS = ("
        '".agents/skills/css-language-profile", '
        '".agents/skills/css-language-profile")\n',
        encoding="utf-8",
    )
    owner = {
        "owner_id": "release-helper-audited-projections",
        "path": "apg_public_release.py",
    }
    expected = {
        "skills": ["skills/css-language-profile/SKILL.md"],
        "projections": [".agents/skills/css-language-profile"],
    }
    with pytest.raises(
        SurfaceContractError,
        match="unsupported (?:static )?expression|actual value",
    ):
        _module()._assert_release_helper(
            tmp_path, owner, CANDIDATE, expected
        )
