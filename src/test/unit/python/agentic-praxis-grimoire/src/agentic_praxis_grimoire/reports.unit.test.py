from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest


reports = importlib.import_module("agentic_praxis_grimoire.reports")


def test_report_path_uses_canonical_primary_names(tmp_path: Path) -> None:
    assert reports.report_path(tmp_path, "project", "APG82", "show") == (
        tmp_path / "project" / "APG82" / "APG82.git.show.report.txt"
    )
    assert reports.report_path(tmp_path, "project", "APG82", "diff").name == (
        "APG82.git.diff.report.txt"
    )
    assert reports.report_path(tmp_path, "project", "APG82", "ops").name == (
        "APG82.ops.report.txt"
    )


@pytest.mark.parametrize("value", ("../project", "project/name", ".", ".."))
def test_report_path_rejects_unsafe_components(tmp_path: Path, value: str) -> None:
    with pytest.raises(ValueError):
        reports.report_path(tmp_path, value, "APG82", "show")


def test_path_route_works_without_repository(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    result = reports.main(
        {"project": "synthetic", "outbox_root": str(tmp_path)},
        ["path", "--phase", "APG82", "--kind", "show"],
        None,
    )
    assert result == 0
    assert capsys.readouterr().out.strip() == str(
        tmp_path / "synthetic" / "APG82" / "APG82.git.show.report.txt"
    )


def test_git_route_fails_clearly_without_repository(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    result = reports.main(
        {"project": "synthetic", "outbox_root": str(tmp_path)},
        ["show", "APG82"],
        None,
    )
    assert result == 2
    assert "requires an APG repository" in capsys.readouterr().err


@pytest.mark.parametrize("kind", ("bad", "", "show/path"))
def test_report_path_rejects_unknown_kind(tmp_path: Path, kind: str) -> None:
    with pytest.raises(reports.ReportRouteError):
        reports.report_path(tmp_path, "project", "APG82", kind)


@pytest.mark.parametrize(
    "arguments",
    (
        [], ["path"], ["path", "--phase", "APG82"],
        ["path", "--kind", "show"], ["path", "--bad"], ["unknown"],
    ),
)
def test_report_usage_failures_are_bounded(
    tmp_path: Path,
    arguments: list[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = reports.main(
        {"project": "synthetic", "outbox_root": str(tmp_path)},
        arguments,
        None,
    )
    assert result == 2
    assert "apgr report:" in capsys.readouterr().err


@pytest.mark.parametrize(
    "action,function_name",
    (("show", "git_show_main"), ("diff", "git_diff_main"),
     ("operational", "append_operational_main"), ("ops", "append_operational_main")),
)
def test_repository_report_routes_forward_resolved_outbox(
    tmp_path: Path,
    action: str,
    function_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    observed: list[tuple[list[str], Path]] = []
    fake = SimpleNamespace()
    setattr(
        fake,
        function_name,
        lambda tail, *, outbox_root: observed.append((list(tail), outbox_root)) or 6,
    )
    monkeypatch.setattr(reports, "_report_cli", lambda _root: fake)
    outbox = tmp_path / "outbox"
    assert reports.main(
        {"project": "repository", "outbox_root": str(outbox)},
        [action, "tail"],
        repository,
    ) == 6
    assert observed == [(["tail"], outbox)]


def test_repository_report_route_rejects_conflicting_project_identity(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    result = reports.main(
        {"project": "different", "outbox_root": str(tmp_path / "outbox")},
        ["diff", "APG82", "blocked", "fail"],
        repository,
    )
    assert result == 2
    assert "must match the repository basename" in capsys.readouterr().err


def test_recovery_does_not_flatten_unexpected_programming_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()

    class UnexpectedDestination:
        def __init__(self, *_arguments: object, **_kwargs: object) -> None:
            pass

        def recover_transaction(self) -> bool:
            raise TypeError("unexpected programming error")

    class ExpectedReportError(RuntimeError):
        pass

    fake_safety = SimpleNamespace(
        Destination=UnexpectedDestination,
        ReportError=ExpectedReportError,
        UsageError=ValueError,
    )
    monkeypatch.setattr(reports, "_report_cli", lambda _root: SimpleNamespace())
    monkeypatch.setattr(reports.importlib, "import_module", lambda _name: fake_safety)

    with pytest.raises(TypeError, match="unexpected programming error"):
        reports.main(
            {"project": "repository", "outbox_root": str(tmp_path / "outbox")},
            ["recover", "--phase", "APG82"],
            repository,
        )
