from __future__ import annotations

import importlib
from pathlib import Path
import stat
import subprocess
import shutil

import pytest

from src.test.apg_test_support import repository_root


cli = importlib.import_module("agentic_praxis_grimoire.cli")
ROOT = repository_root(__file__)


def _git(root: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=APG Test", "-c", "user.email=test@example.invalid", *arguments],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def test_canonical_diff_route_publishes_under_explicit_outbox(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "synthetic"
    repository.mkdir()
    shutil.copytree(ROOT / "libexec" / "agent_report", repository / "libexec" / "agent_report")
    _git(repository, "init", "-q")
    tracked = repository / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    _git(repository, "add", "tracked.txt")
    _git(repository, "commit", "-qm", "base")
    tracked.write_text("changed\n", encoding="utf-8")
    outbox = tmp_path / "outbox"
    legacy = tmp_path / "legacy"
    monkeypatch.setenv("GIT_SHOW_REPORT_ROOT", str(legacy))

    result = cli.main(
        [
            "--project-root", str(repository),
            "--outbox-root", str(outbox),
            "report", "diff", "APG82", "blocked", "focused-gate",
        ]
    )

    assert result == 0
    artifact = outbox / "synthetic" / "APG82" / "APG82.git.diff.report.txt"
    assert artifact.is_file()
    assert stat.S_IMODE(artifact.stat().st_mode) == 0o600
    assert b"GIT-DIFF-REPORT" in artifact.read_bytes()
    assert not legacy.exists()


def test_canonical_recover_route_resolves_retained_transaction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "synthetic"
    repository.mkdir()
    shutil.copytree(ROOT / "libexec" / "agent_report", repository / "libexec" / "agent_report")
    _git(repository, "init", "-q")
    tracked = repository / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    _git(repository, "add", "tracked.txt")
    _git(repository, "commit", "-qm", "base")
    tracked.write_text("changed\n", encoding="utf-8")
    outbox = tmp_path / "outbox"
    monkeypatch.setenv("GIT_SHOW_REPORT_ROOT", str(tmp_path / "legacy"))

    assert cli.main(
        [
            "--project-root", str(repository), "--outbox-root", str(outbox),
            "report", "diff", "APG82", "blocked", "focused-gate",
        ]
    ) == 0
    phase_dir = outbox / "synthetic" / "APG82"
    marker = phase_dir / ".phase.transaction"
    marker.write_text(
        "agent-report-transaction-v1\n"
        "phase: APG82\n"
        "target: APG82.git.diff.report.txt\n"
        "stale: APG82.git.show.report.txt,APG82.ops.report.txt\n"
        "token: interrupted\n",
        encoding="utf-8",
    )
    marker.chmod(0o600)

    assert cli.main(
        [
            "--project-root", str(repository), "--outbox-root", str(outbox),
            "report", "recover", "--phase", "APG82",
        ]
    ) == 0
    assert not marker.exists()
    assert (phase_dir / "APG82.git.diff.report.txt").is_file()
