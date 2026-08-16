"""CLI state selection, rendering, and error-class contracts."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
import sys

import pytest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

from change_size import cli, policy  # noqa: E402
from change_size.git_adapter import Entry, GitError  # noqa: E402


class Repository:
    root = Path("/")

    def head(self) -> str:
        return "head"

    def resolve_commit(self, value: str) -> str:
        return value

    def parent(self, commit: str) -> str | None:
        return None if commit == "root" else "parent"

    def tree_entries(self, revision: str) -> dict[str, Entry]:
        return {"file": Entry("file", "100644", revision[0] * 40, 1)}

    def index_entries(self) -> dict[str, Entry]:
        return {"index": Entry("index", "100644", "i" * 40, 1)}

    def object_file(self, revision: str, path: str) -> bytes:
        del revision, path
        return b"{}"


@pytest.mark.parametrize(
    ("arguments", "revision"),
    [
        (Namespace(mode="staged"), "head"),
        (Namespace(mode="commit", commit="root"), "root"),
        (Namespace(mode="commit", commit="child"), "child"),
        (Namespace(mode="tree", commit=None), "HEAD"),
    ],
)
def test_selected_state_modes(arguments: Namespace, revision: str) -> None:
    selected = cli._selected_state(Repository(), arguments)  # type: ignore[arg-type]
    assert selected[0] == revision
    assert selected[-1]


def test_run_renders_both_formats_and_exit_classes(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repository = Repository()
    monkeypatch.setattr(cli.GitRepository, "discover", lambda _path: repository)
    monkeypatch.setattr(cli, "load_policy_bytes", lambda _payload: object())
    payload = {
        "aggregate_generated_evidence_bytes": 0,
        "aggregate_new_blob_bytes": 0,
        "changes": [],
        "exceptions_used": [],
        "largest_resulting_blobs": [],
        "largest_rewritten_blobs": [],
        "largest_text_line": {"bytes": 0, "path": ""},
        "mode": "staged",
        "policy_limits": {},
        "result": "pass",
        "revision": "head",
        "schema_version": 1,
        "violations": [],
    }
    monkeypatch.setattr(cli, "evaluate", lambda *_args, **_kwargs: payload)
    assert cli.run(["staged", "--format", "json"]) == 0
    assert capsys.readouterr().out.startswith("{")
    payload["violations"] = [{"control": "x", "path": "p", "observed": 2, "limit": 1}]
    payload["result"] = "violation"
    assert cli.run(["staged"]) == 1
    assert "APG change-size check: violation" in capsys.readouterr().out

    monkeypatch.setattr(
        cli,
        "load_policy_bytes",
        lambda _payload: (_ for _ in ()).throw(policy.PolicyError("bad")),
    )
    assert cli.run(["staged"]) == 2
    assert "policy error" in capsys.readouterr().err
    monkeypatch.setattr(
        cli.GitRepository,
        "discover",
        lambda _path: (_ for _ in ()).throw(GitError("bad")),
    )
    assert cli.run(["staged"]) == 2
    assert "Git error" in capsys.readouterr().err
