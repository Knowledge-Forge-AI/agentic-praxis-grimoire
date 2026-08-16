"""Failing-first narrative-state semantics for APG60B."""
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
from apg_candidate_narrative_state_contract import (  # noqa: E402
    DIAGNOSTIC_SCOPE,
    HUMAN_REVIEW_BOUNDARY,
    MECHANICAL_AUTHORITY,
)


CANDIDATE = "css-language-profile"
OWNER = {"owner_id": "narrative-readme", "path": "README.md"}


def _checker():
    module = importlib.import_module("apg_actual_retained_surface_contract")
    return module._assert_narrative


def _write(root: Path, text: str) -> None:
    (root / "README.md").write_text(text, encoding="utf-8")


@pytest.mark.parametrize(
    "text",
    (
        "css-language-profile is inactive.\n",
        "css-language-profile is not integrated.\n",
        "css-language-profile is not current.\n",
    ),
)
def test_negated_terminal_state_does_not_prove_retention(
    tmp_path: Path, text: str
) -> None:
    _write(tmp_path, text)

    with pytest.raises(SurfaceContractError, match="narrative-readme"):
        _checker()(tmp_path, OWNER, CANDIDATE)


def test_multiline_contradiction_does_not_prove_retention(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "css-language-profile is active and retained.\n"
        "Status: rejected and absent.\n",
    )

    with pytest.raises(SurfaceContractError, match="narrative-readme"):
        _checker()(tmp_path, OWNER, CANDIDATE)


@pytest.mark.parametrize(
    ("state", "text"),
    (
        ("absent", "css-language-profile is currently active.\n"),
        (
            "retained-provisional",
            "css-language-profile is still not integrated.\n",
        ),
        (
            "retained-stable",
            "css-language-profile is retained.\nStatus: currently rejected.\n",
        ),
        (
            "retained-provisional",
            "css-language-profile is retained.\nStatus: not active.\n",
        ),
        (
            "retained-stable",
            "css-language-profile is not currently integrated.\n",
        ),
        (
            "retained-provisional",
            "css-language-profile is no longer active.\n",
        ),
        (
            "retained-stable",
            "css-language-profile is not present and is no longer present.\n",
        ),
    ),
)
def test_terminal_state_modifiers_do_not_bypass_contradiction_detection(
    tmp_path: Path, state: str, text: str
) -> None:
    _write(
        tmp_path,
        f"<!-- APG-CANDIDATE-STATE: {CANDIDATE} {state} -->\n\n{text}",
    )

    with pytest.raises(SurfaceContractError, match="contradicts"):
        _checker()(tmp_path, OWNER, CANDIDATE, state)


def test_duplicate_retained_markers_fail(tmp_path: Path) -> None:
    marker = (
        "<!-- APG-CANDIDATE-STATE: "
        "css-language-profile retained-provisional -->\n"
    )
    _write(tmp_path, marker + marker)

    with pytest.raises(SurfaceContractError, match="narrative-readme"):
        _checker()(tmp_path, OWNER, CANDIDATE)


@pytest.mark.parametrize(
    "state",
    ("absent", "retained-provisional", "retained-stable"),
)
def test_each_exact_candidate_state_marker_passes(
    tmp_path: Path, state: str
) -> None:
    _write(
        tmp_path,
        f"<!-- APG-CANDIDATE-STATE: {CANDIDATE} {state} -->\n",
    )
    _checker()(tmp_path, OWNER, CANDIDATE, state)


def test_historical_rejection_prose_with_absent_marker_passes(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        f"<!-- APG-CANDIDATE-STATE: {CANDIDATE} absent -->\n\n"
        f"ADR 0035 preserved the historical Rejected {CANDIDATE} evidence.\n",
    )
    _checker()(tmp_path, OWNER, CANDIDATE, "absent")


@pytest.mark.parametrize(
    "text",
    (
        "<!-- APG-CANDIDATE-STATE: css-language-profile unknown -->\n",
        "<!-- APG-CANDIDATE-STATE: css-language-profile absent -->\n"
        "<!-- APG-CANDIDATE-STATE: css-language-profile retained-stable -->\n",
    ),
)
def test_unknown_or_conflicting_marker_fails(
    tmp_path: Path, text: str
) -> None:
    _write(tmp_path, text)
    with pytest.raises(SurfaceContractError, match="marker"):
        _checker()(tmp_path, OWNER, CANDIDATE, "absent")


def test_maturity_marker_mismatch_fails(tmp_path: Path) -> None:
    _write(
        tmp_path,
        f"<!-- APG-CANDIDATE-STATE: {CANDIDATE} retained-provisional -->\n",
    )
    with pytest.raises(SurfaceContractError, match="marker"):
        _checker()(tmp_path, OWNER, CANDIDATE, "retained-stable")


def test_retained_marker_with_multiline_current_contradiction_fails(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        f"<!-- APG-CANDIDATE-STATE: {CANDIDATE} retained-provisional -->\n\n"
        f"{CANDIDATE} is active and retained.\n"
        "Status: rejected and absent.\n",
    )
    with pytest.raises(SurfaceContractError, match="contradicts"):
        _checker()(tmp_path, OWNER, CANDIDATE, "retained-provisional")


@pytest.mark.parametrize(
    "sentence",
    (
        "css-language-profile is a rejected candidate.",
        "css-language-profile has been rejected.",
        "css-language-profile was rejected.",
        "css-language-profile is not being integrated.",
        "css-language-profile is no longer an integrated skill.",
        "css-language-profile — rejected and absent.",
        "css-language-profile remains under rejection.",
    ),
)
def test_frozen_direct_retained_contradictions_fail(
    tmp_path: Path, sentence: str
) -> None:
    _write(
        tmp_path,
        "<!-- APG-CANDIDATE-STATE: "
        "css-language-profile retained-provisional -->\n\n"
        f"{sentence}\n",
    )
    with pytest.raises(SurfaceContractError, match="contradicts"):
        _checker()(
            tmp_path,
            OWNER,
            CANDIDATE,
            "retained-provisional",
        )


def test_retained_historical_section_is_not_current(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "<!-- APG-CANDIDATE-STATE: "
        "css-language-profile retained-provisional -->\n\n"
        "## Historical record\n\n"
        "css-language-profile was rejected in APG59.\n",
    )
    _checker()(
        tmp_path,
        OWNER,
        CANDIDATE,
        "retained-provisional",
    )


def test_arbitrary_prose_retains_human_review_boundary(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "<!-- APG-CANDIDATE-STATE: "
        "css-language-profile retained-provisional -->\n\n"
        "css-language-profile crossed an unnamed twilight boundary.\n",
    )
    _checker()(
        tmp_path,
        OWNER,
        CANDIDATE,
        "retained-provisional",
    )
    assert MECHANICAL_AUTHORITY == "exact candidate-state marker"
    assert DIAGNOSTIC_SCOPE == "frozen bounded contradiction vocabulary"
    assert HUMAN_REVIEW_BOUNDARY == (
        "human review remains required for arbitrary prose"
    )
