"""Unit contracts for APG ADR, exit, and phase identity validation."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pytest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import apg_record_identity as identity  # noqa: E402


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def valid_tree(root: Path, *, sequence: int = 1, phase: str = "APG1") -> Path:
    write(root / "docs/adr/2026/07/0001-decision.md", "# ADR\n")
    relative = f"2026/07/22/{sequence:05d}-{phase.lower()}-result-exit.md"
    write(
        root / "docs/status" / relative,
        f"# {phase} Result Exit\n\nPhase ID: `{phase}`\n",
    )
    write(
        root / "docs/status/README.md",
        f"- [`{sequence:05d} — {phase} Result`]({relative})\n",
    )
    return root


def codes(result: identity.CheckResult) -> set[str]:
    return {item.code for item in result.diagnostics}


def test_phase_argument_and_diagnostic_value_are_bounded() -> None:
    assert identity.canonical_phase("apg28a") == "APG28A"
    assert identity.phase_argument("apg-test2") == "APG-TEST2"
    with pytest.raises(argparse.ArgumentTypeError, match="phase must match"):
        identity.phase_argument("not-a-phase")
    diagnostic = identity.Diagnostic("CODE", "path", "rule", "message", "action")
    assert diagnostic.json_value() == {
        "action": "action",
        "code": "CODE",
        "invariant": "rule",
        "message": "message",
        "path": "path",
    }
    result = identity.CheckResult((diagnostic,), 1, 2, 2, "0002", "00003")
    assert not result.passed


def test_valid_tree_reports_independent_counts_next_values_and_expectations(
    tmp_path: Path,
) -> None:
    result = identity.check_records(
        valid_tree(tmp_path),
        expect_allocated=["APG1"],
        expect_available=["APG2"],
    )
    assert result.passed
    assert (result.adrs, result.exits, result.phase_ids) == (1, 1, 1)
    assert (result.next_adr, result.next_exit) == ("0002", "00002")
    assert identity.render_text(result).startswith("PASS APG record identity")
    rendered = identity.render_json(result)
    assert '"status":"pass"' in rendered
    assert '"next_exit":"00002"' in rendered


def test_missing_and_duplicate_namespaces_are_diagnosed(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    result = identity.check_records(empty)
    assert {"APGR001", "APGR003", "APGR006"}.issubset(codes(result))

    root = valid_tree(tmp_path / "duplicates")
    write(root / "docs/adr/2026/07/0001-other.md", "# Duplicate\n")
    other = "2026/07/22/00001-apg2-other-exit.md"
    write(root / "docs/status" / other, "# APG2 Other Exit\n")
    with (root / "docs/status/README.md").open("a", encoding="utf-8") as stream:
        stream.write(f"- [`00001 — APG2 Other`]({other})\n")
    result = identity.check_records(root)
    assert {"APGR002", "APGR005"}.issubset(codes(result))


def test_exit_path_index_and_explicit_identity_disagreements_are_visible(
    tmp_path: Path,
) -> None:
    root = valid_tree(tmp_path, sequence=29, phase="APG29")
    exit_path = next((root / "docs/status").rglob("*-exit.md"))
    exit_path.write_text("# APG30 Wrong Exit\n", encoding="utf-8")
    index = root / "docs/status/README.md"
    index.write_text(
        index.read_text(encoding="utf-8")
        + "- [`00029 — APG29 Duplicate`](2026/07/22/00029-apg29-result-exit.md)\n"
        + "- [`00030 — APG30 Stale`](missing.md)\n",
        encoding="utf-8",
    )
    write(root / "docs/status/not-an-exit.md", "# Invalid\n")
    result = identity.check_records(root)
    assert {
        "APGR004",
        "APGR006",
        "APGR008",
        "APGR009",
        "APGR010",
    }.issubset(codes(result))


def test_case_spelling_phase_uniqueness_and_expectation_mismatches(tmp_path: Path) -> None:
    root = valid_tree(tmp_path)
    original = next((root / "docs/status").rglob("*-exit.md"))
    uppercase = original.with_name("00001-APG1-uppercase-exit.md")
    uppercase.write_text("# apg1 Lower Exit\n\nPhase ID: `apg1`\n", encoding="utf-8")
    index = root / "docs/status/README.md"
    with index.open("a", encoding="utf-8") as stream:
        stream.write("- [`00002 — apg1 Lower`](2026/07/22/00001-APG1-uppercase-exit.md)\n")
    result = identity.check_records(
        root,
        expect_allocated=["APG9"],
        expect_available=["APG1"],
    )
    assert {"APGR011", "APGR012", "APGR013", "APGR014", "APGR015"}.issubset(
        codes(result)
    )


def test_render_failure_and_cli_result_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    diagnostic = identity.Diagnostic("C", "p", "i", "m", "a")
    failed = identity.CheckResult((diagnostic,), 1, 1, 1, "0002", "00002")
    text = identity.render_text(failed)
    assert "1 diagnostic" in text and "FAIL APG record identity" in text
    monkeypatch.setattr(identity, "check_records", lambda *_args, **_kwargs: failed)
    assert identity.main(["--root", str(tmp_path), "--format", "json"]) == 1
    assert '"status":"fail"' in capsys.readouterr().out


def test_record_file_discovery_rejects_unsafe_owner_tree(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    owner = tmp_path / "docs/adr"
    owner.parent.mkdir(parents=True)
    owner.symlink_to(outside, target_is_directory=True)
    assert identity._record_files(tmp_path, "adr") == ()


def test_replacement_free_environment_strips_repository_selectors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GIT_DIR", "/untrusted/repository")
    monkeypatch.setenv("GIT_REPLACE_REF_BASE", "refs/untrusted/")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.hooksPath")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "/untrusted/hooks")
    environment = identity.replacement_free_git_environment()
    assert "GIT_DIR" not in environment
    assert "GIT_REPLACE_REF_BASE" not in environment
    assert "GIT_CONFIG_COUNT" not in environment
    assert "GIT_CONFIG_KEY_0" not in environment
    assert "GIT_CONFIG_VALUE_0" not in environment
    assert environment["GIT_NO_REPLACE_OBJECTS"] == "1"
    assert environment["GIT_CONFIG_GLOBAL"] == identity.os.devnull
    assert environment["GIT_CONFIG_NOSYSTEM"] == "1"
    assert environment["GIT_OPTIONAL_LOCKS"] == "0"


def test_status_chronology_matches_collapsed_commit_groups_and_one_pending() -> None:
    committed = ("APG1", "APG2", "APG3")
    status = ((1, "APG0"), (2, "APG1"), (3, "APG2"), (4, "APG3"))
    assert identity.validate_phase_chronology(committed, status) == (
        "APG1",
        "APG2",
        "APG3",
    )
    assert identity.validate_phase_chronology(
        committed, status + ((5, "APG4"),), pending_phase="APG4"
    )[-1] == "APG4"
    assert identity.validate_phase_chronology(
        committed, ((1, "APG1"), (2, "APG9"), (3, "APG2"), (4, "APG3"))
    ) == committed
    with pytest.raises(ValueError, match="no status"):
        identity.validate_phase_chronology(
            committed, status + ((5, "APG5"),), pending_phase="APG4"
        )
    with pytest.raises(ValueError, match="already committed"):
        identity.validate_phase_chronology(
            committed, status, pending_phase="APG3"
        )
    with pytest.raises(ValueError, match="no status"):
        identity.validate_phase_chronology(
            committed, status, pending_phase="APG4"
        )


def test_first_parent_chronology_collapses_groups_and_ignores_other_subjects(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    completed = identity.subprocess.CompletedProcess(
        (),
        0,
        "bootstrap\nAPG1: one\nAPG1: continuation\nAPG2: two\n",
        "",
    )
    monkeypatch.setattr(identity.subprocess, "run", lambda *_a, **_k: completed)
    assert identity.first_parent_phase_chronology(tmp_path) == ("APG1", "APG2")


@pytest.mark.parametrize(
    ("completed", "message"),
    (
        (identity.subprocess.CompletedProcess((), 1, "", "failure"), "traversal"),
        (identity.subprocess.CompletedProcess((), 0, "bootstrap\n", ""), "no APG"),
        (
            identity.subprocess.CompletedProcess(
                (), 0, "APG1: one\nAPG2: two\nAPG1: again\n", ""
            ),
            "non-adjacent",
        ),
    ),
)
def test_first_parent_chronology_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    completed: identity.subprocess.CompletedProcess[str],
    message: str,
) -> None:
    monkeypatch.setattr(identity.subprocess, "run", lambda *_a, **_k: completed)
    with pytest.raises(ValueError, match=message):
        identity.first_parent_phase_chronology(tmp_path)


def test_first_parent_chronology_fails_closed_on_spawn_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fail(*_args, **_kwargs):
        raise OSError("unavailable")

    monkeypatch.setattr(identity.subprocess, "run", fail)
    with pytest.raises(ValueError, match="traversal"):
        identity.first_parent_phase_chronology(tmp_path)


def test_status_chronology_rejects_duplicate_and_unallocated_groups() -> None:
    with pytest.raises(ValueError, match="committed"):
        identity.validate_phase_chronology(("APG1", "APG1"), ((1, "APG1"),))
    with pytest.raises(ValueError, match="duplicate"):
        identity.validate_phase_chronology(
            ("APG1",), ((1, "APG1"), (2, "APG1"))
        )
    with pytest.raises(ValueError, match="no status"):
        identity.validate_phase_chronology(("APG2",), ((1, "APG1"),))
