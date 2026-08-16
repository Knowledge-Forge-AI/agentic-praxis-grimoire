"""Failing-first candidate-decision lifecycle closure for APG60B."""
from __future__ import annotations

import importlib
from pathlib import Path
import runpy
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
SUPPORT = ROOT / "src/test/support"
sys.path.insert(0, str(SUPPORT))

from apg_candidate_surface_contract import SurfaceContractError  # noqa: E402
from apg_candidate_surface_contract import load_removal_plan  # noqa: E402
from apg_candidate_decision_contract import (  # noqa: E402
    assert_candidate_decision,
)


CANDIDATE = "css-language-profile"
LEGACY_TEST = (
    ROOT
    / "src/test/unit/python/agentic-praxis-grimoire/src/test/support"
    / "apg_actual_retained_surface_contract.unit.test.py"
)
PLAN = load_removal_plan(
    ROOT / "src/test/fixtures/apg60-css-removal-plan.json", root=ROOT
)
OWNER = next(
    owner
    for owner in PLAN["owners"]
    if owner["owner_id"] == "candidate-decision-record"
)
CONFIG = PLAN["closure_contracts"]["candidate_decision"]


def _write_decision(root: Path, status: str, *, indexed: bool = True) -> None:
    path = root / OWNER["path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# ADR 0036: CSS Language Profile from Frozen Contract\n\n"
        f"- Status: {status}\n"
        "- Proposed in: APG61\n"
        "- Decided in: APG62\n\n"
        f"{CANDIDATE} decision.\n",
        encoding="utf-8",
    )
    index = root / CONFIG["index_path"]
    index.parent.mkdir(parents=True, exist_ok=True)
    entry = (
        "- [`0036 — CSS Language Profile from Frozen Contract`]"
        "(2026/07/0036-css-language-profile-from-frozen-contract.md)\n"
        f"  — {status}\n"
    )
    index.write_text(entry if indexed else "# ADR index\n", encoding="utf-8")


def test_decision_and_index_reject_symlinked_adr_ancestor(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repository"
    _write_decision(root, "Accepted")
    adr_root = root / "docs/adr"
    external = tmp_path / "external-adr"
    adr_root.rename(external)
    adr_root.symlink_to(external, target_is_directory=True)

    with pytest.raises(SurfaceContractError, match="direct|ancestor"):
        assert_candidate_decision(
            root,
            OWNER,
            CANDIDATE,
            CONFIG,
            "retained",
        )


def test_retained_candidate_without_fresh_decision_adr_fails(
    tmp_path: Path,
) -> None:
    helpers = runpy.run_path(str(LEGACY_TEST))
    helpers["_materialize_actual_retained"](
        tmp_path, omit="candidate-decision-record"
    )
    checker = importlib.import_module(
        "apg_actual_retained_surface_contract"
    ).assert_actual_retained_surface_present

    with pytest.raises(SurfaceContractError, match="candidate-decision"):
        checker(
            tmp_path,
            helpers["MANIFEST"],
            helpers["PLAN"],
            CANDIDATE,
        )


def test_unused_decision_state_requires_no_file_or_index_entry(
    tmp_path: Path,
) -> None:
    index = tmp_path / CONFIG["index_path"]
    index.parent.mkdir(parents=True)
    index.write_text("# ADR index\n", encoding="utf-8")
    assert_candidate_decision(
        tmp_path, OWNER, CANDIDATE, CONFIG, "unused"
    )


@pytest.mark.parametrize("status", ("Accepted", "Accepted with amendment"))
def test_retained_decision_accepts_terminal_statuses(
    tmp_path: Path, status: str
) -> None:
    _write_decision(tmp_path, status)
    assert_candidate_decision(
        tmp_path, OWNER, CANDIDATE, CONFIG, "retained"
    )


@pytest.mark.parametrize("status", ("Proposed", "Rejected"))
def test_retained_decision_rejects_nonaccepted_status(
    tmp_path: Path, status: str
) -> None:
    _write_decision(tmp_path, status)
    with pytest.raises(SurfaceContractError, match="not terminal"):
        assert_candidate_decision(
            tmp_path, OWNER, CANDIDATE, CONFIG, "retained"
        )


def test_rejected_decision_is_preserved_and_indexed(tmp_path: Path) -> None:
    _write_decision(tmp_path, "Rejected")
    assert_candidate_decision(
        tmp_path, OWNER, CANDIDATE, CONFIG, "rejected"
    )


def test_decision_index_mismatch_fails(tmp_path: Path) -> None:
    _write_decision(tmp_path, "Accepted", indexed=False)
    with pytest.raises(SurfaceContractError, match="index"):
        assert_candidate_decision(
            tmp_path, OWNER, CANDIDATE, CONFIG, "retained"
        )


def test_decision_status_must_belong_to_exact_index_entry(
    tmp_path: Path,
) -> None:
    _write_decision(tmp_path, "Accepted")
    index = tmp_path / CONFIG["index_path"]
    index.write_text(
        "- [`0036 — CSS Language Profile from Frozen Contract`]"
        "(2026/07/0036-css-language-profile-from-frozen-contract.md)\n"
        "  — Proposed\n"
        "- [`9999 — Unrelated`](9999-unrelated.md)\n"
        "  — Accepted\n",
        encoding="utf-8",
    )
    with pytest.raises(SurfaceContractError, match="does not agree"):
        assert_candidate_decision(
            tmp_path, OWNER, CANDIDATE, CONFIG, "retained"
        )


def test_decision_index_entry_rejects_contradictory_inline_status(
    tmp_path: Path,
) -> None:
    _write_decision(tmp_path, "Accepted")
    index = tmp_path / CONFIG["index_path"]
    index.write_text(
        "- [`0036 — CSS Language Profile from Frozen Contract`]"
        "(2026/07/0036-css-language-profile-from-frozen-contract.md)"
        " — Rejected\n"
        "  — Accepted\n",
        encoding="utf-8",
    )
    with pytest.raises(SurfaceContractError, match="does not agree"):
        assert_candidate_decision(
            tmp_path, OWNER, CANDIDATE, CONFIG, "retained"
        )


def test_rejected_decision_cannot_be_deleted(tmp_path: Path) -> None:
    index = tmp_path / CONFIG["index_path"]
    index.parent.mkdir(parents=True)
    index.write_text("# ADR index\n", encoding="utf-8")
    with pytest.raises(SurfaceContractError, match="regular file"):
        assert_candidate_decision(
            tmp_path, OWNER, CANDIDATE, CONFIG, "rejected"
        )
