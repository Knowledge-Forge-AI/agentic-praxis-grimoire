"""Release portability preserves source instruction transport and provenance."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from agent_source_guidance import source_guidance


ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("directory,filename", [("codex", "AGENTS.md"), ("claude", "CLAUDE.md")])
def test_actual_standing_instruction_bytes_are_advertised(
    directory: str, filename: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CLAUDE_CODE_SAFE_MODE", raising=False)
    payload = (ROOT / directory / filename).read_bytes()
    prompt, permissions = source_guidance(
        ROOT / directory, [], workers=False, instruction_file=filename,
    )
    assert f"sha256={hashlib.sha256(payload).hexdigest()}" in prompt
    assert prompt.endswith(payload.decode("utf-8"))
    assert permissions == []
    for marker in ("/" + "Users" + "/", "file:" + "///"):
        assert marker not in payload.decode("utf-8")


@pytest.mark.parametrize("filename", ["AGENTS.md", "CLAUDE.md"])
def test_transport_digest_changes_with_actual_source(
    tmp_path: Path, filename: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CLAUDE_CODE_SAFE_MODE", raising=False)
    path = tmp_path / filename
    before = "Operator-supplied canon.\n".encode()
    after = "Configured scratch; portable résumé.\n".encode()
    path.write_bytes(before)
    first, _ = source_guidance(tmp_path, [], workers=False, instruction_file=filename)
    path.write_bytes(after)
    second, _ = source_guidance(tmp_path, [], workers=False, instruction_file=filename)
    assert hashlib.sha256(before).hexdigest() in first
    assert hashlib.sha256(after).hexdigest() in second
    assert hashlib.sha256(before).hexdigest() not in second
    assert second.endswith(after.decode())
