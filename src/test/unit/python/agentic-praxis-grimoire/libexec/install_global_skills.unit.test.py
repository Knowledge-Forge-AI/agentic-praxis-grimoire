"""Unit contracts for install-global-skills CLI resolution and output."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

from src.test.apg_test_support import repository_root
from src.test.install_global_skills_cases import add_skill


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import global_skills_transaction as transaction  # noqa: E402
import install_global_skills as command  # noqa: E402


def test_cli_rejects_combined_modes_and_uninstall_sources(
    tmp_path: Path,
) -> None:
    with pytest.raises(command.InstallError, match="combined"):
        command.resolve_request(
            command.parse_args(["codex", "--check", "--dry-run"]), {}
        )
    with pytest.raises(command.InstallError, match="does not accept"):
        command.resolve_request(
            command.parse_args(
                [
                    "codex",
                    str(tmp_path / "repository"),
                    "--uninstall",
                    "--skills-root",
                    str(tmp_path / "skills"),
                ]
            ),
            {},
        )


def test_json_output_is_canonical_and_contains_discovery_note(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    add_skill(repository, "alpha")
    request = command.resolve_request(
        command.parse_args(
            [
                "claude",
                str(repository),
                "--dry-run",
                "--skills-root",
                str(tmp_path / "skills"),
                "--format",
                "json",
            ]
        ),
        {},
    )
    result = command.execute(request)
    rendered = command.render(result, "json")
    document = json.loads(rendered)

    assert rendered == json.dumps(
        document, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ) + "\n"
    assert document["agent"] == "claude"
    assert document["mode"] == "dry-run"
    assert "restart" in document["post_action_discovery_note"]
    assert isinstance(result, transaction.OperationResult)


def test_empty_records_text_render_and_missing_inventory(
    tmp_path: Path,
) -> None:
    result = transaction.OperationResult(
        "codex",
        None,
        tmp_path / "skills",
        "uninstall",
        0,
        0,
        1,
        0,
        True,
    )
    rendered = command.render(result, "text")

    assert command.source_records(None) == []
    assert command.skill_records(None) == []
    assert "source_repository_count: 0\n" in rendered
    assert "removed: 1\n" in rendered
    with pytest.raises(command.InstallError, match="absent"):
        command.execute(
            command.Request(
                "codex",
                "apply",
                "text",
                tmp_path / "skills",
                None,
            )
        )


def test_main_exit_classes_and_warning_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    check_request = command.Request(
        "codex", "check", "text", tmp_path / "skills", None
    )
    changed = transaction.OperationResult(
        "codex",
        None,
        tmp_path / "skills",
        "check",
        0,
        0,
        0,
        0,
        True,
        ("retained backup",),
    )
    monkeypatch.setattr(command, "parse_args", lambda _argv: object())
    monkeypatch.setattr(
        command, "resolve_request", lambda _arguments, _environment: check_request
    )
    monkeypatch.setattr(command, "execute", lambda _request: changed)
    assert command.main([]) == 1
    assert "warning: retained backup" in capsys.readouterr().err

    monkeypatch.setattr(
        command,
        "resolve_request",
        lambda _arguments, _environment: (_ for _ in ()).throw(
            command.InstallError("unsafe request")
        ),
    )
    assert command.main([]) == 2
    assert "unsafe request" in capsys.readouterr().err
