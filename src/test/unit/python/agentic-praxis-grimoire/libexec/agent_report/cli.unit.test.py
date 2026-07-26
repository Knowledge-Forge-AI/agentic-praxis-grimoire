"""Unit contracts for the three agent-report command adapters."""

from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

from agent_report import cli, models, safety  # noqa: E402
from agent_report.git_adapter import GitError  # noqa: E402


class FakeDestination:
    appended: list[object] = []

    def __init__(self, root: Path, phase: str) -> None:
        self.project = root.name
        self.path = root / f"{phase}.report.txt"

    def append(self, value: object) -> None:
        self.appended.append(value)


def install_common_fakes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> object:
    git = SimpleNamespace(root=tmp_path / "project")
    git.root.mkdir(exist_ok=True)
    monkeypatch.setattr(cli.GitAdapter, "discover", lambda _cwd: git)
    monkeypatch.setattr(cli, "Destination", FakeDestination)
    monkeypatch.setattr(cli, "private_temporary_directory", lambda _name: nullcontext())
    monkeypatch.setattr(cli, "build_record", lambda record: b"record:" + record.record_id.encode())
    FakeDestination.appended.clear()
    return git


def test_public_mains_forward_explicit_and_process_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    observed: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(
        cli,
        "_run",
        lambda name, _command, arguments: observed.append((name, arguments)) or 7,
    )
    assert cli.git_show_main(["a"]) == 7
    assert cli.git_diff_main(["b"]) == 7
    assert cli.append_operational_main(["c"]) == 7
    monkeypatch.setattr(sys, "argv", ["command", "process"])
    assert cli.git_show_main() == 7
    assert observed == [
        ("git-show-report", ["a"]),
        ("git-diff-report", ["b"]),
        ("append-operational-report", ["c"]),
        ("git-show-report", ["process"]),
    ]


@pytest.mark.parametrize(
    "error,status,text",
    [
        (cli._UsageAlreadyRendered(), 2, ""),
        (safety.UsageError("unsafe"), 2, "unsafe"),
        (safety.ReportError("broken"), 1, "broken"),
        (GitError("git failed"), 1, "git failed"),
        (InterruptedError(), 1, "interrupted"),
        (KeyboardInterrupt(), 130, "interrupted"),
        (OSError("private detail"), 1, "filesystem operation failed"),
    ],
)
def test_run_maps_bounded_error_classes(
    error: BaseException,
    status: int,
    text: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli.os, "umask", lambda _mode: 0)
    monkeypatch.setattr(cli.signal, "getsignal", lambda _signal: None)
    monkeypatch.setattr(cli.signal, "signal", lambda *_args: None)

    def raise_error(_arguments: list[str]) -> int:
        raise error

    assert cli._run("command", raise_error, []) == status
    assert text in capsys.readouterr().err


def test_run_sets_deterministic_environment_and_restores_handlers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    installed: list[tuple[object, object]] = []
    monkeypatch.setattr(cli.os, "umask", lambda mode: installed.append(("umask", mode)) or 0)
    monkeypatch.setattr(cli.signal, "getsignal", lambda value: f"old-{value}")
    monkeypatch.setattr(cli.signal, "signal", lambda value, handler: installed.append((value, handler)))
    assert cli._run("command", lambda arguments: len(arguments), ["one"]) == 1
    assert cli.os.environ["LC_ALL"] == "C"
    assert cli.os.environ["GIT_PAGER"] == "cat"
    assert installed[0] == ("umask", 0o077)
    assert any(str(handler).startswith("old-") for _, handler in installed[1:])


def test_git_show_help_usage_validation_and_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli._git_show(["--help"]) == 0
    assert "Usage: git-show-report" in capsys.readouterr().out
    assert cli._git_show([]) == 2
    assert "Usage: git-show-report" in capsys.readouterr().err
    with pytest.raises(safety.UsageError):
        cli._git_show(["../bad", "a" * 40, "status", "passed", "gate"])
    with pytest.raises(safety.UsageError, match="commit hash"):
        cli._git_show(["APG", "bad", "status", "passed", "gate"])

    install_common_fakes(monkeypatch, tmp_path)
    record = models.ReportRecord("git-show-report", 2, "show", "project", "APG", b"")
    monkeypatch.setattr(
        cli,
        "collect_show_report",
        lambda *_args, **_kwargs: SimpleNamespace(commit="a" * 40, record=record),
    )
    assert cli._git_show(["APG", "a" * 40, "status", "passed", "gate"]) == 0
    assert FakeDestination.appended == [b"record:show"]
    assert "appended " + "a" * 40 in capsys.readouterr().out


def test_git_diff_help_option_shape_and_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli._git_diff(["-h"]) == 0
    assert cli._git_diff(["APG", "passed"]) == 2
    assert cli._git_diff(["APG", "passed", "gate", "--bad", "status"]) == 2
    install_common_fakes(monkeypatch, tmp_path)
    record = models.ReportRecord("git-diff-report", 1, "diff", "project", "APG", b"")
    monkeypatch.setattr(
        cli,
        "collect_diff_report",
        lambda *_args, **_kwargs: SimpleNamespace(record=record),
    )
    assert cli._git_diff(["APG", "passed", "gate"]) == 0
    assert cli._git_diff(["APG", "passed", "gate", "--status-doc", "status.md"]) == 0
    assert FakeDestination.appended == [b"record:diff", b"record:diff"]
    assert "appended diff" in capsys.readouterr().out


def test_operational_argument_parser_and_validation_cover_association_rules(
    tmp_path: Path,
) -> None:
    parsed = cli._parse_operational_arguments(
        [
            "APG",
            str(tmp_path / "body.txt"),
            "complete",
            "gate",
            "--related-commit",
            "a" * 40,
            "--related-git-report-id",
            "GIT-SHOW-REPORT-" + "a" * 40,
        ]
    )
    cli._validate_operational_arguments(parsed)
    for arguments in (
        ["APG", "/tmp/body", "complete", "gate", "--unknown"],
        ["APG", "/tmp/body", "complete", "gate", "--related-commit"],
        ["APG", "/tmp/body", "complete", "gate", "--related-commit", "a", "--related-commit", "b"],
    ):
        with pytest.raises(cli._UsageAlreadyRendered):
            cli._parse_operational_arguments(arguments)
    invalid = (
        cli.OperationalArguments("APG", "relative", "complete", "gate", "", ""),
        cli.OperationalArguments("APG", "/tmp/../body", "complete", "gate", "", ""),
        cli.OperationalArguments("APG", "/tmp/body", "complete", "gate", "a" * 40, ""),
        cli.OperationalArguments("APG", "/tmp/body", "complete", "gate", "a" * 40, "GIT-DIFF-REPORT-" + "b" * 64),
    )
    for value in invalid:
        with pytest.raises(safety.UsageError):
            cli._validate_operational_arguments(value)


def test_related_commit_resolution_accepts_commit_and_rejects_failures() -> None:
    class Git:
        def __init__(self, returncode: int, stdout: bytes) -> None:
            self.result = SimpleNamespace(returncode=returncode, stdout=stdout)

        def run(self, _arguments: list[str], *, check: bool = False) -> object:
            assert check is False
            return self.result

    assert cli._resolve_related_commit(Git(0, b"A" * 40 + b"\n"), "abc") == "a" * 40
    assert cli._resolve_related_commit(Git(0, b""), "") == "NONE"
    with pytest.raises(safety.UsageError, match="does not resolve"):
        cli._resolve_related_commit(Git(1, b""), "bad")
    with pytest.raises(safety.UsageError, match="does not resolve"):
        cli._resolve_related_commit(Git(0, b"\xff"), "bad")


def test_operational_help_short_usage_and_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli._append_operational(["--help"]) == 0
    assert cli._append_operational([]) == 2
    source = tmp_path / "body.txt"
    source.write_text("evidence", encoding="utf-8")
    source.chmod(0o600)
    install_common_fakes(monkeypatch, tmp_path)
    monkeypatch.setattr(cli, "_resolve_related_commit", lambda *_args: "NONE")
    monkeypatch.setattr(
        cli,
        "build_operational_record",
        lambda **_kwargs: models.ReportRecord("operational-report", 1, "ops", "project", "APG", b""),
    )
    assert cli._append_operational(["APG", str(source), "complete", "gate"]) == 0
    callback = FakeDestination.appended[0]
    assert callable(callback)
    assert callback(b"", ()) == b"record:ops"
    assert "OPERATIONAL-REPORT-" in capsys.readouterr().out

    source.write_bytes(b"")
    with pytest.raises(safety.ReportError, match="empty"):
        cli._append_operational(["APG", str(source), "complete", "gate"])
