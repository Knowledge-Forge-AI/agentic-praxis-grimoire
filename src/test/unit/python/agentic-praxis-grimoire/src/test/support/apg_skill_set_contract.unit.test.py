"""Exact canonical derived-set controls for dynamic retained consumers."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
SUPPORT = ROOT / "src/test/support"
sys.path.insert(0, str(SUPPORT))

from apg_skill_set_contract import (  # noqa: E402
    SkillSetError,
    canonical_skill_names,
    require_exact_skill_names,
)


def _write(path: Path, text: str = "---\nname: example\n---\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_expected_set_is_sorted_and_derived_from_direct_canonical_leaves(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "skills/other-a/SKILL.md", "---\nname: other-a\n---\n")
    _write(tmp_path / "skills/other-b/SKILL.md", "---\nname: other-b\n---\n")
    assert canonical_skill_names(tmp_path) == ("other-a", "other-b")


@pytest.mark.parametrize(
    "received",
    (
        ["other-a", "other-a"],
        ["other-a", "other-c"],
        ["other-b", "other-a"],
        ["other-a", "other/../other-b"],
        ["other-a", ""],
        ["/absolute", "other-b"],
        ["other-a", "other\\b"],
        ["other-a", "other-\x00b"],
    ),
)
def test_duplicate_missing_extra_unsorted_or_unsafe_sets_fail(
    received: list[str],
) -> None:
    with pytest.raises(SkillSetError):
        require_exact_skill_names(received, ("other-a", "other-b"), consumer="topology")


def test_exact_topology_and_installer_sets_pass() -> None:
    expected = ("other-a", "other-b")
    assert require_exact_skill_names(expected, expected, consumer="topology") == expected
    assert require_exact_skill_names(expected, expected, consumer="installer") == expected


def test_canonical_skill_names_rejects_unsafe_or_nonregular_leaves(tmp_path: Path) -> None:
    _write(tmp_path / "skills/other-a/SKILL.md")
    (tmp_path / "skills/unsafe name").mkdir(parents=True)
    with pytest.raises(SkillSetError):
        canonical_skill_names(tmp_path)
