"""Unit contracts for deterministic Git-show and shared evidence collection."""

from __future__ import annotations

from pathlib import Path
import stat
import subprocess
import sys

import pytest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

from agent_report import diff, git_adapter, models, safety, show  # noqa: E402


COMMIT = "a" * 40
PARENT = "b" * 40


def completed(stdout: bytes = b"", returncode: int = 0) -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess(["git"], returncode, stdout, b"")


class ShowGit:
    """Fixed Git responses for the complete show collector contract."""

    root = Path("/repo/project")

    def run(
        self,
        arguments: list[str],
        *,
        input_bytes: bytes | None = None,
        diagnostic: str = "",
        check: bool = True,
        environment: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[bytes]:
        del input_bytes, diagnostic, check, environment
        if arguments[:2] == ["rev-parse", "--verify"]:
            return completed(COMMIT.encode() + b"\n")
        if arguments[0] == "show" and arguments[1] == "--no-patch":
            fields = (
                COMMIT,
                PARENT,
                "Author",
                "author@example.test",
                "2026-01-01T00:00:00+00:00",
                "Committer",
                "committer@example.test",
                "2026-01-01T00:00:01+00:00",
                "subject",
            )
            return completed("\0".join(fields).encode() + b"\0")
        if arguments[:4] == ["-c", "core.quotePath=true", "diff", "--name-status"]:
            return completed(b"A\tnew\nM\tchanged\n")
        if arguments[:4] == ["-c", "core.quotePath=true", "diff", "--numstat"]:
            return completed(b"2\t1\tnew\n3\t0\tchanged\n")
        if arguments[:3] == ["show", "--no-patch", "--no-color"]:
            return completed(b"subject\n\nbody\n")
        if "--patch" in arguments:
            return completed(b"diff --git a/new b/new\n")
        raise AssertionError(arguments)


class ScriptedGit:
    """Small response map for branch-focused Git policy tests."""

    def __init__(self, root: Path, responses: dict[tuple[str, ...], subprocess.CompletedProcess[bytes]]):
        self.root = root
        self.responses = responses

    def run(self, arguments: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        del kwargs
        return self.responses.get(tuple(arguments), completed())

    def text(self, arguments: list[str], *, diagnostic: str) -> str:
        del diagnostic
        return self.run(arguments).stdout.rstrip(b"\n").decode()


def test_complete_show_collection_renders_identity_summary_and_evidence() -> None:
    result = show.collect_show_report(
        ShowGit(),
        phase="APG28A",
        commit_input=COMMIT[:12],
        status_doc="docs/status/exit.md",
        result="complete",
        final_gate="focused",
    )
    assert result.commit == COMMIT
    assert result.record.record_id == f"GIT-SHOW-REPORT-{COMMIT}"
    assert b"FILES-CHANGED: 2\n" in result.record.payload
    assert b"INSERTIONS: 5\n" in result.record.payload
    assert b"PATCH-MODE: single-parent\n" in result.record.payload
    assert b"END-OF-PATCH-REACHED: true\n" in result.record.payload


def test_show_commit_resolution_and_metadata_reject_malformed_git_output() -> None:
    class BadResolve(ShowGit):
        def run(self, arguments: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            if arguments[:2] == ["rev-parse", "--verify"]:
                return completed(b"not-a-commit\n")
            return super().run(arguments, **kwargs)

    with pytest.raises(git_adapter.GitError, match="malformed"):
        show._resolve_commit(BadResolve(), "a" * 7)

    class BadMetadata(ShowGit):
        value = b"short\0"

        def run(self, arguments: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            del arguments, kwargs
            return completed(self.value)

    with pytest.raises(safety.ReportError, match="malformed"):
        show._collect_metadata(BadMetadata(), COMMIT)
    BadMetadata.value = b"\xff\0" * 9
    with pytest.raises(safety.ReportError, match="UTF-8"):
        show._collect_metadata(BadMetadata(), COMMIT)
    BadMetadata.value = ("c" * 40 + "\0" + "\0" * 8).encode()
    with pytest.raises(safety.ReportError, match="does not match"):
        show._collect_metadata(BadMetadata(), COMMIT)
    BadMetadata.value = (COMMIT + "\0\0bad\nname\0" + "value\0" * 6).encode()
    with pytest.raises(safety.ReportError, match="control"):
        show._collect_metadata(BadMetadata(), COMMIT)


def test_show_comparison_covers_root_single_parent_and_merge() -> None:
    git = ScriptedGit(Path("/repo"), {("mktree",): completed(b"e" * 40 + b"\n")})
    root = show._comparison(git, "")
    assert (root.parent_count, root.root_commit, root.patch_mode) == (0, "true", "root")
    single = show._comparison(git, PARENT)
    assert (single.diff_from, single.merge_commit, single.patch_mode) == (
        PARENT,
        "false",
        "single-parent",
    )
    merge = show._comparison(git, f"{PARENT} {'c' * 40}")
    assert (merge.parent_count, merge.merge_commit, merge.diff_from) == (2, "true", PARENT)


def test_show_summary_handles_status_classes_binary_and_malformed_numstat() -> None:
    changed = b"A\ta\nD\td\nR100\told\tnew\nC100\ta\tb\nM\tm\n\n"
    counts = show.summarize_diff(changed, b"1\t2\ta\n3\t4\tb\n")
    assert counts == {
        "files_changed": 5,
        "files_added": 1,
        "files_modified": 1,
        "files_deleted": 1,
        "files_renamed": 1,
        "files_copied": 1,
        "insertions": "4",
        "deletions": "6",
        "binary_files": 0,
    }
    assert show._summarize_numstat(b"-\t-\tbinary\n8\t9\tlater\n") == (
        "UNKNOWN",
        "UNKNOWN",
        1,
    )
    for malformed in (b"only-one-column\n", b"x\t1\tpath\n"):
        with pytest.raises(safety.ReportError, match="malformed"):
            show._summarize_numstat(malformed)
    with pytest.raises(safety.ReportError, match="UTF-8"):
        show.encode_lines((("field", "\udcff"),))


def observation() -> models.RealGitObservation:
    return models.RealGitObservation(
        head=COMMIT,
        index_fingerprint="sha256:abc;size:3",
        index_identity="sha256:def",
        status=b"? new\0",
        staged=b"M\ttracked\n",
        unstaged=b"M\tworking\n",
    )


def snapshot() -> models.WorktreeSnapshot:
    return models.WorktreeSnapshot(
        changed_files=b"A\tnew\n",
        numstat_raw=b"2\t0\tnew\n",
        patch=b"diff --git a/new b/new\n",
    )


def test_diff_identity_framing_and_record_rendering_are_deterministic() -> None:
    fields = {key: key.encode().hex() for key in diff._STATE_KEYS}
    identity = diff.compute_state_report_id(fields)
    assert identity.startswith("GIT-DIFF-REPORT-") and len(identity) == 80
    with pytest.raises(ValueError, match="incomplete"):
        diff.compute_state_report_id({})
    with pytest.raises(ValueError, match="incomplete"):
        diff.compute_state_report_id({**fields, "extra": "00"})

    framed = diff._frame_diff_evidence(observation(), snapshot())
    assert framed.status.endswith(b"\n") and framed.patch.endswith(b"\n")
    assert framed.numstat.startswith(b"COLUMNS:")
    record = diff._render_diff_record(
        diff.DiffRequest("APG28A", "complete", "focused", "docs/status/exit.md"),
        "project",
        "regular",
        observation(),
        snapshot(),
    )
    assert record.record_id.startswith("GIT-DIFF-REPORT-")
    assert b"REAL-INDEX-AND-WORKTREE-MUTATED: false\n" in record.payload
    assert b"FILES-ADDED: 1\n" in record.payload


def test_supported_index_rejects_unsupported_repository_states(tmp_path: Path) -> None:
    base = {
        ("rev-parse", "--verify", "HEAD^{commit}"): completed(COMMIT.encode()),
        ("rev-parse", "--shared-index-path"): completed(),
        ("config", "--bool", "core.sparseCheckout"): completed(b"false\n", 1),
        ("ls-files", "--sparse", "-z"): completed(),
        ("ls-files", "--unmerged", "-z"): completed(),
        ("rev-parse", "--path-format=absolute", "--git-path", "index"): completed(
            str(tmp_path / "index").encode() + b"\n"
        ),
    }
    git = ScriptedGit(tmp_path, base)
    path, mode = diff._supported_index(git)
    assert path == tmp_path / "index" and mode == "missing-seeded-from-head"

    cases = (
        (("rev-parse", "--verify", "HEAD^{commit}"), completed(b"", 1), "unborn"),
        (("rev-parse", "--shared-index-path"), completed(b"shared"), "split"),
        (("config", "--bool", "core.sparseCheckout"), completed(b"true"), "sparse"),
        (("ls-files", "--sparse", "-z"), completed(b"", 1), "characterization"),
        (("ls-files", "--sparse", "-z"), completed(b"dir/\0"), "sparse"),
        (("ls-files", "--unmerged", "-z"), completed(b"entry\0"), "unmerged"),
    )
    for key, value, message in cases:
        responses = dict(base)
        responses[key] = value
        with pytest.raises(safety.ReportError, match=message):
            diff._supported_index(ScriptedGit(tmp_path, responses))


def test_supported_index_and_observation_validate_real_index(tmp_path: Path) -> None:
    index = tmp_path / "index"
    index.write_bytes(b"idx")
    index.chmod(0o600)
    fingerprint, identity = diff._observe_index(index)
    assert fingerprint.startswith("sha256:") and identity.startswith("sha256:")
    assert diff._observe_index(tmp_path / "missing") == ("MISSING", "MISSING")
    index.unlink()
    index.mkdir()
    with pytest.raises(safety.ReportError, match="unsafe"):
        diff._observe_index(index)

    responses = {
        ("rev-parse", "--verify", "HEAD^{commit}"): completed(COMMIT.upper().encode()),
        ("status", "--porcelain=v2", "-z", "--untracked-files=all"): completed(b"status"),
    }
    git = ScriptedGit(tmp_path, responses)
    observed = diff._observe_real(git, tmp_path / "missing")
    assert observed.head == COMMIT and observed.status == b"status"
    responses[("rev-parse", "--verify", "HEAD^{commit}")] = completed(b"bad")
    with pytest.raises(safety.ReportError, match="malformed"):
        diff._observe_real(git, tmp_path / "missing")


def test_worktree_snapshot_uses_private_index_for_present_and_missing_index(tmp_path: Path) -> None:
    class SnapshotGit:
        root = tmp_path

        def __init__(self) -> None:
            self.calls: list[tuple[str, ...]] = []

        def run(self, arguments: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            self.calls.append(tuple(arguments))
            environment = kwargs.get("environment")
            if arguments[0] in {"read-tree", "add"} and environment:
                private = Path(environment["GIT_INDEX_FILE"])  # type: ignore[index]
                private.touch(exist_ok=True)
            if "--name-status" in arguments:
                return completed(b"A\tnew\n")
            if "--numstat" in arguments:
                return completed(b"1\t0\tnew\n")
            if "--patch" in arguments:
                return completed(b"patch\n")
            return completed()

    for present in (False, True):
        index = tmp_path / ("present" if present else "missing")
        if present:
            index.write_bytes(b"index")
        git = SnapshotGit()
        result = diff._collect_worktree_snapshot(git, index, COMMIT)
        assert result == models.WorktreeSnapshot(b"A\tnew\n", b"1\t0\tnew\n", b"patch\n")
        assert (("read-tree", COMMIT) in git.calls) is (not present)


def test_git_adapter_discovery_execution_text_and_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        calls.append((command, kwargs))
        return completed(str(tmp_path).encode() + b"\n")

    monkeypatch.setattr(subprocess, "run", fake_run)
    adapter = git_adapter.GitAdapter.discover(tmp_path)
    assert adapter.root == tmp_path
    result = adapter.run(["status"], environment={"CUSTOM": "yes"}, input_bytes=b"input")
    assert result.returncode == 0
    assert calls[-1][0][:4] == ["git", "-C", str(tmp_path), "--no-pager"]
    assert calls[-1][1]["input"] == b"input"
    assert calls[-1][1]["env"]["CUSTOM"] == "yes"  # type: ignore[index]
    assert adapter.text(["status"], diagnostic="status failed") == str(tmp_path)

    def failed(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        del command, kwargs
        return completed(b"", 1)

    monkeypatch.setattr(subprocess, "run", failed)
    with pytest.raises(git_adapter.GitError, match="not inside"):
        git_adapter.GitAdapter.discover(tmp_path)
    with pytest.raises(git_adapter.GitError, match="bounded"):
        adapter.run(["bad"], diagnostic="bounded")


def test_git_adapter_rejects_invalid_utf8_and_missing_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    values = iter((completed(b"\xff"), completed(b"\n"), completed(b"\xff")))
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: next(values))
    with pytest.raises(git_adapter.GitError, match="valid UTF-8"):
        git_adapter.GitAdapter.discover(tmp_path)
    with pytest.raises(git_adapter.GitError, match="unavailable"):
        git_adapter.GitAdapter.discover(tmp_path)
    with pytest.raises(git_adapter.GitError, match="valid UTF-8"):
        git_adapter.GitAdapter(tmp_path).text(["status"], diagnostic="read failed")


def test_index_identity_uses_stable_metadata_fields(tmp_path: Path) -> None:
    path = tmp_path / "index"
    path.write_bytes(b"content")
    metadata = path.stat()
    values = diff._index_identity(metadata).split(":")
    assert len(values) == 9
    assert int(values[2]) & stat.S_IFREG == stat.S_IFREG
