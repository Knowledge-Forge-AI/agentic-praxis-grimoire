"""Regressions for Serena resolution from pinned controller generations."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest

if str(Path(__file__).resolve().parents[3] / "libexec") not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "libexec"))

from claude_vc_profile import read_only_contract
from controller_generation_store import ALLOWLIST, materialize

pytest.importorskip("agent_workers", reason="agent_workers subsystem retained in Agent-Central")
facade_context = pytest.importorskip("agent_workers.facade_context")
MCP_TOOL_NAMES = facade_context.MCP_TOOL_NAMES
WorkerFacadeContext = facade_context.WorkerFacadeContext
_serena_source_command = facade_context._serena_source_command


def _git(cwd: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=True,
    )


def _commit_all(repo: Path) -> str:
    _git(repo, "add", "-A")
    _git(
        repo,
        "-c",
        "user.email=test@example.invalid",
        "-c",
        "user.name=Serena Test",
        "commit",
        "-qm",
        "serena generation",
    )
    return _git(repo, "rev-parse", "HEAD").stdout.strip()


def test_materialized_generation_preserves_serena_source_declaration(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")

    command = tmp_path / "serena"
    command.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    command.chmod(0o755)
    declaration = repo / "common/mcp.toml"
    declaration.parent.mkdir()
    declaration.write_text(
        "schema_version = 1\n\n"
        "[[servers]]\n"
        "name = \"serena\"\n"
        "transport = \"stdio\"\n"
        f"command = {command.as_posix()!r}\n"
        "clients = { claude = \"enabled\" }\n",
        encoding="utf-8",
    )
    commit = _commit_all(repo)

    record = materialize(repo, tmp_path / "controller", commit)
    pinned = Path(record["generation_root"])

    assert "common/mcp.toml" in ALLOWLIST
    assert (pinned / "common/mcp.toml").read_bytes() == declaration.read_bytes()
    assert _serena_source_command(pinned) == os.fspath(command)


def test_missing_serena_resolution_is_evidenced_without_disabling_facade(
    tmp_path: Path,
) -> None:
    context = WorkerFacadeContext(
        parent_id="serena-evidence",
        state_dir=tmp_path / "state",
        source_root=tmp_path / "pinned",
        workspace=tmp_path / "workspace",
        parent_family="claude_fable",
        task_authority="read_only",
        lifecycle_generation="generation-1",
        profile="gemini-3.8-flash-high",
    )

    evidence = context.serena_evidence()
    assert evidence == {
        "server": "serena",
        "available": False,
        "status": "unavailable",
    }
    assert context.mcp_tool_names() == MCP_TOOL_NAMES

    contract = read_only_contract(
        Path(__file__).resolve().parents[3] / "claude",
        "normal-plan-review",
        worker_facade=context,
        headless=True,
    )
    assert contract["facade_evidence"] == {"serena": evidence}
    assert contract["tools"] == [
        "Read",
        "Glob",
        "Grep",
        "WebFetch",
        "WebSearch",
        *MCP_TOOL_NAMES,
    ]


def test_writable_launch_reports_missing_serena_without_prompt_details(tmp_path, monkeypatch, capsys):
    import json
    import claude_vc_profile as launcher
    import claude_model_catalog as catalog
    from agent_workers import facade_context
    root = Path(__file__).resolve().parents[3]
    context = WorkerFacadeContext(
        parent_id="serena-evidence", state_dir=tmp_path / "state", source_root=root,
        workspace=tmp_path / "workspace", parent_family="claude_opus",
        task_authority="mutation_capable", lifecycle_generation="generation-1",
        profile="gemini-3.8-flash-high",
    )
    monkeypatch.setattr(launcher, "_load_worker_facade", lambda *args, **kwargs: context)
    monkeypatch.setattr(facade_context, "_serena_source_command", lambda root: None)
    monkeypatch.setattr(launcher.shutil, "which", lambda name: "/fixture/claude")
    monkeypatch.setattr(catalog, "probe_claude_version", lambda executable: ("2.1.999", "available"))
    calls = []
    monkeypatch.setattr(launcher.os, "execve", lambda *args: calls.append(args))
    launcher.launch(root / "claude", "implementation-primary", ["-p", "PRIVATE_PROMPT_SENTINEL"])
    assert len(calls) == 1
    stderr = capsys.readouterr().err
    line = next(line for line in stderr.splitlines() if line.startswith("claude-profile: worker facade evidence "))
    evidence = json.loads(line.removeprefix("claude-profile: worker facade evidence "))
    assert evidence["serena"]["available"] is False
    assert "PRIVATE_PROMPT_SENTINEL" not in stderr and str(tmp_path) not in stderr
