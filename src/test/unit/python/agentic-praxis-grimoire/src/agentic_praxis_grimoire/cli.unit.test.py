"""Unit contracts for the consolidated APGR command dispatcher."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from agentic_praxis_grimoire import cli  # noqa: E402
from agentic_praxis_grimoire import go_bridge  # noqa: E402
from agentic_praxis_grimoire import __main__ as module_main  # noqa: E402


def test_help_and_version_are_checkout_independent(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["--help"]) == 0
    help_text = capsys.readouterr().out
    for family in ("check", "skills", "test", "env", "report", "response", "release"):
        assert family in help_text

    assert cli.main(["--version"]) == 0
    assert capsys.readouterr().out == "apgr 0.7.0\n"


def test_python_module_entry_point_routes_the_same_version_contract(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert module_main.main(["--version"]) == 0
    assert capsys.readouterr().out == "apgr 0.7.0\n"
    completed = subprocess.run(
        [sys.executable, "-m", "agentic_praxis_grimoire", "--version"],
        cwd=REPOSITORY_ROOT,
        env={"PYTHONPATH": str(REPOSITORY_ROOT / "src"), **os.environ},
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == "apgr 0.7.0\n"


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


@pytest.mark.parametrize(
    "action,tail",
    (
        ("list", ["--format", "json"]),
        ("context-report", []),
        ("resolve", ["--stdin"]),
        (
            "materialize",
            ["--result", "/private/result.json", "--destination-parent", "/private/root"],
        ),
        ("verify-corpus", ["--repository", "/private/repository"]),
    ),
)
def test_skill_consumer_commands_delegate_to_go_without_python_fallback(
    action: str,
    tail: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agentic_praxis_grimoire import go_bridge

    observed: list[tuple[list[str], Path | None]] = []
    monkeypatch.setattr(
        go_bridge,
        "run",
        lambda arguments, *, repository_root: observed.append(
            (list(arguments), repository_root)
        )
        or 23,
    )
    assert cli.main(["skills", action, *tail]) == 23
    assert observed == [(["skills", action, *tail], None)]


def test_build_info_delegates_to_go_without_python_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agentic_praxis_grimoire import go_bridge

    observed: list[tuple[list[str], Path | None]] = []
    monkeypatch.setattr(
        go_bridge,
        "run",
        lambda arguments, *, repository_root: observed.append(
            (list(arguments), repository_root)
        )
        or 19,
    )
    assert cli.main(["build-info"]) == 19
    assert observed == [(["build-info"], None)]


def test_hotspot_analysis_delegates_exact_tail_to_go_without_python_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from agentic_praxis_grimoire import go_bridge

    root = tmp_path.resolve()
    monkeypatch.chdir(root)
    observed: list[tuple[list[str], Path | None]] = []
    monkeypatch.setattr(
        go_bridge,
        "run",
        lambda arguments, *, repository_root: observed.append(
            (list(arguments), repository_root)
        )
        or 24,
    )
    tail = ["hotspots", "--format", "json", "--top", "3"]
    assert cli.main(["analyze", *tail]) == 24
    assert observed == [
        (["--repository", str(root), "analyze", *tail], root)
    ]


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


@pytest.mark.parametrize(
    "command",
    ("git-show-report", "git-diff-report", "append-operational-report"),
)
def test_historical_report_adapters_delegate_to_go(
    command: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed: list[tuple[list[str], Path | None]] = []
    monkeypatch.setattr(
        go_bridge,
        "run",
        lambda arguments, *, repository_root: observed.append(
            (list(arguments), repository_root)
        ) or 9,
    )
    assert cli.legacy_main(command, ["one", "two"], REPOSITORY_ROOT) == 9
    assert observed == [
        ([
            "--repository", str(REPOSITORY_ROOT),
            "legacy", command, "one", "two",
        ], REPOSITORY_ROOT)
    ]


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


def test_environment_commands_delegate_with_resolved_storage_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed: list[tuple[list[str], Path | None]] = []
    monkeypatch.setattr(
        go_bridge,
        "run",
        lambda arguments, *, repository_root: observed.append(
            (list(arguments), repository_root)
        )
        or 29,
    )
    storage_root = tmp_path / "explicit-home"
    assert cli.main(
        [
            "--apgr-home", str(storage_root), "env", "snapshot",
            "--profile", "/private/profile.json",
        ]
    ) == 29
    assert observed == [
        ([
            "env", "snapshot", "--storage-root", str(storage_root),
            "--profile", "/private/profile.json",
        ], None)
    ]


def test_environment_profile_check_delegates_without_storage_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[list[str]] = []
    monkeypatch.setattr(
        go_bridge,
        "run",
        lambda arguments, *, repository_root: observed.append(list(arguments)) or 30,
    )
    assert cli.main(
        [
            "--apgr-home", "invalid-home-is-not-read", "env",
            "profile-check", "/private/profile.json",
        ]
    ) == 30
    assert observed == [["env", "profile-check", "/private/profile.json"]]


@pytest.mark.parametrize(
    ("cli_home", "environment_home", "expected_home"),
    (
        ("explicit", "environment-home", "explicit"),
        (None, "environment-home", "environment-home"),
        (None, None, None),
    ),
)
def test_environment_storage_root_preserves_python_home_precedence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    cli_home: str | None,
    environment_home: str | None,
    expected_home: str | None,
) -> None:
    operator_home = tmp_path / "operator-home"
    if environment_home is None:
        monkeypatch.delenv("APGR_HOME", raising=False)
    else:
        monkeypatch.setenv("APGR_HOME", str(tmp_path / environment_home))
    monkeypatch.setattr(Path, "home", lambda: operator_home)
    observed: list[list[str]] = []
    monkeypatch.setattr(
        go_bridge,
        "run",
        lambda arguments, *, repository_root: observed.append(list(arguments)) or 31,
    )
    arguments = ["env", "show", "--profile-id", "demo"]
    if cli_home is not None:
        arguments = ["--apgr-home", str(tmp_path / cli_home), *arguments]
    selected_home = (
        operator_home / ".apgr"
        if expected_home is None
        else tmp_path / expected_home
    )
    assert cli.main(arguments) == 31
    assert observed == [[
        "env", "show", "--storage-root", str(selected_home),
        "--profile-id", "demo",
    ]]


def test_environment_explicit_storage_root_is_not_duplicated_or_resolved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APGR_HOME", "relative-home-must-not-be-read")
    explicit = tmp_path / "command-root"
    observed: list[list[str]] = []
    monkeypatch.setattr(
        go_bridge,
        "run",
        lambda arguments, *, repository_root: observed.append(list(arguments)) or 41,
    )
    assert cli.main(
        ["env", "resolve", "--storage-root", str(explicit), "--profile-id", "demo"]
    ) == 41
    assert observed == [[
        "env", "resolve", "--storage-root", str(explicit),
        "--profile-id", "demo",
    ]]


def test_environment_bridge_failure_is_bounded_and_values_safe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    secret = "environment-value-must-not-leak"

    def fail(*_arguments: object, **_keywords: object) -> int:
        raise go_bridge.GoBridgeError(f"bridge detail: {secret}")

    monkeypatch.setattr(go_bridge, "run", fail)
    assert cli.main(["env", "show", "--storage-root", str(tmp_path / "storage")]) == 1
    error = capsys.readouterr().err
    assert error == "apgr env: Go environment bridge unavailable\n"
    assert secret not in error
