"""Unit contracts for the consolidated APGR command dispatcher."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from agentic_praxis_grimoire import cli  # noqa: E402
from agentic_praxis_grimoire import __main__ as module_main  # noqa: E402


def test_help_and_version_are_checkout_independent(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["--help"]) == 0
    help_text = capsys.readouterr().out
    for family in ("check", "skills", "test", "report", "response", "release"):
        assert family in help_text

    assert cli.main(["--version"]) == 0
    assert capsys.readouterr().out == "apgr 0.6.0\n"


def test_python_module_entry_point_routes_the_same_version_contract(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert module_main.main(["--version"]) == 0
    assert capsys.readouterr().out == "apgr 0.6.0\n"
    completed = subprocess.run(
        [sys.executable, "-m", "agentic_praxis_grimoire", "--version"],
        cwd=REPOSITORY_ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == "apgr 0.6.0\n"


@pytest.mark.parametrize(
    "arguments,owner,forwarded",
    [
        (["check", "change-size", "staged"], "apg-check-change-size", ["staged"]),
        (["check", "phase-commit-message", "--phase", "APG82"], "apg-check-phase-commit-message", ["--phase", "APG82"]),
        (["check", "record-identity", "--format", "json"], "apg-check-record-identity", ["--format", "json"]),
        (["check", "skill-library", "--format", "json"], "apg-check-skill-library", ["--format", "json"]),
        (["skills", "project", "list", "repo"], "apg-project-skills", ["list", "repo"]),
        (["skills", "user", "list"], "apg-user-skills", ["list"]),
        (["skills", "install-global", "codex"], "install-global-skills", ["codex"]),
        (["skills", "flatten", "source", "target"], "flatten-skill-symlinks", ["source", "target"]),
        (["test", "unit"], "apg-test", ["unit"]),
        (["release", "public", "manifest"], "apg-public-release", ["manifest"]),
    ],
)
def test_repository_routes_forward_exact_tail(
    arguments: list[str],
    owner: str,
    forwarded: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[tuple[str, list[str], Path | None]] = []
    monkeypatch.setattr(
        cli,
        "legacy_main",
        lambda name, values=None, repository_root=None: observed.append(
            (name, list(values or []), repository_root)
        )
        or 17,
    )
    monkeypatch.setattr(cli, "discover_repository", lambda _start: REPOSITORY_ROOT)
    assert cli.main(arguments) == 17
    assert observed == [(owner, forwarded, REPOSITORY_ROOT)]


def test_repository_route_fails_bounded_without_authority(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "discover_repository", lambda _start: None)
    assert cli.main(["test", "unit"]) == 2
    assert "requires an Agentic Praxis Grimoire repository" in capsys.readouterr().err


def test_repository_route_rejects_an_unrelated_git_worktree_bounded(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "discover_repository", lambda _start: tmp_path)
    assert cli.main(["check", "record-identity"]) == 2
    assert "not an Agentic Praxis Grimoire repository" in capsys.readouterr().err


def test_legacy_adapter_requires_known_command() -> None:
    with pytest.raises(ValueError, match="unknown compatibility command"):
        cli.legacy_main("not-maintained", [])


@pytest.mark.parametrize(
    "command",
    (
        "apg-check-change-size", "apg-check-phase-commit-message",
        "apg-check-record-identity", "apg-check-skill-library",
        "apg-build-python-release-bundle", "apg-normalize-python-sdist",
        "apg-project-skills", "apg-public-release", "apg-test",
        "apg-user-skills", "install-global-skills", "flatten-skill-symlinks",
        "git-show-report", "git-diff-report", "append-operational-report",
    ),
)
def test_every_legacy_adapter_invokes_one_loaded_owner(
    command: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed: list[list[str]] = []
    fake = SimpleNamespace()
    for name in (
        "run", "main", "git_show_main", "git_diff_main",
        "append_operational_main",
    ):
        setattr(fake, name, lambda values, seen=observed: seen.append(list(values)) or 9)
    monkeypatch.setattr(cli, "_load", lambda *_arguments: fake)
    assert cli.legacy_main(command, ["one", "two"], REPOSITORY_ROOT) == 9
    assert observed == [["one", "two"]]


def test_repository_discovery_handles_git_failure_and_missing_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        cli.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stdout=""),
    )
    assert cli.discover_repository(tmp_path) is None
    monkeypatch.setattr(
        cli.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0, stdout=str(tmp_path / "missing") + "\n"
        ),
    )
    assert cli.discover_repository(tmp_path) is None


def test_missing_explicit_project_root_has_bounded_diagnostic(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(
        ["--project-root", str(tmp_path / "missing"), "test", "unit"]
    ) == 2
    assert "--project-root must name the exact Git worktree root" in capsys.readouterr().err


@pytest.mark.parametrize(
    "arguments,diagnostic",
    (
        (["--unknown"], "unknown global option"),
        (["--project"], "requires a value"),
        (["--project", "one", "--project", "two"], "only once"),
        ([], "command is required"),
        (["unknown"], "unknown command family"),
        (["check"], "check requires"),
        (["check", "unknown"], "unknown check"),
        (["skills"], "skills requires"),
        (["skills", "unknown"], "unknown skills"),
        (["release"], "release requires"),
        (["release", "unknown"], "release requires"),
    ),
)
def test_usage_failures_return_stable_exit_two(
    arguments: list[str], diagnostic: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(arguments) == 2
    assert diagnostic in capsys.readouterr().err


def test_global_options_are_forwarded_to_response_and_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agentic_praxis_grimoire import reports, response

    observed: list[tuple[str, dict[str, str], list[str], Path | None]] = []
    monkeypatch.setattr(cli, "discover_repository", lambda _path: None)
    monkeypatch.setattr(
        reports,
        "main",
        lambda options, tail, root: observed.append(
            ("report", dict(options), list(tail), root)
        ) or 7,
    )
    monkeypatch.setattr(
        response,
        "main",
        lambda options, tail, root: observed.append(
            ("response", dict(options), list(tail), root)
        ) or 8,
    )
    prefix = ["--project", "p", "--outbox-root", "/outbox"]
    assert cli.main([*prefix, "report", "path"]) == 7
    assert cli.main([*prefix, "response", "record"]) == 8
    assert observed == [
        ("report", {"project": "p", "outbox_root": "/outbox"}, ["path"], None),
        ("response", {"project": "p", "outbox_root": "/outbox"}, ["record"], None),
    ]
