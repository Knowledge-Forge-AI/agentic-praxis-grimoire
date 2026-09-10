"""Focused contracts for prospective-source capture."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from libexec import apg_source_capture as capture


def git(root: Path, *arguments: str) -> None:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=False,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr.decode()


@pytest.fixture()
def source(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.name", "Capture Test")
    git(root, "config", "user.email", "capture@example.invalid")
    (root / "keep.bin").write_bytes(b"before\x00bytes\n")
    (root / "gone.txt").write_text("delete me\n", encoding="utf-8")
    (root / "run.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    (root / "run.sh").chmod(0o755)
    (root / "link").symlink_to("keep.bin")
    (root / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "base")
    return root


def test_capture_preserves_prospective_bytes_modes_links_deletions_and_source(source: Path, tmp_path: Path) -> None:
    before = (source.joinpath(".git", "index").read_bytes(), subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"]))
    (source / "keep.bin").write_bytes(b"after\x00bytes\n")
    (source / "gone.txt").unlink()
    (source / "run.sh").chmod(0o700)
    (source / "new.bin").write_bytes(b"new\x00bytes\n")
    (source / "foreign.txt").write_text("foreign\n", encoding="utf-8")
    (source / "ignored.txt").write_text("ignored\n", encoding="utf-8")
    output = tmp_path / "capture"

    result = capture.capture_source(source, output, reviewed_paths=("new.bin",))

    assert (output / "keep.bin").read_bytes() == b"after\x00bytes\n"
    assert not (output / "gone.txt").exists()
    assert (output / "run.sh").stat().st_mode & 0o111
    assert (output / "run.sh").stat().st_mode & 0o777 == 0o700
    assert os.readlink(output / "link") == "keep.bin"
    assert (output / "new.bin").read_bytes() == b"new\x00bytes\n"
    assert not (output / "foreign.txt").exists()
    assert not (output / "ignored.txt").exists()
    assert result.manifest["deleted"] == ["gone.txt"]
    assert result.manifest["reviewed_new_files"] == ["new.bin"]
    assert subprocess.check_output(["git", "-C", str(output), "status", "--porcelain"]) == b""
    assert (source / ".git" / "index").read_bytes() == before[0]
    assert subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"]) == before[1]


def test_staged_new_path_requires_review_and_cleanup(source: Path, tmp_path: Path) -> None:
    (source / "staged.txt").write_text("staged\n", encoding="utf-8")
    git(source, "add", "staged.txt")
    output = tmp_path / "capture"

    with pytest.raises(capture.CaptureError, match="not reviewed"):
        capture.capture_source(source, output)
    assert not output.exists()


def test_unresolved_index_conflict_is_refused(source: Path, tmp_path: Path) -> None:
    git(source, "checkout", "-q", "-b", "conflict-side")
    (source / "keep.bin").write_bytes(b"side\n")
    git(source, "add", "keep.bin")
    git(source, "commit", "-q", "-m", "side")
    git(source, "checkout", "-q", "main")
    (source / "keep.bin").write_bytes(b"main\n")
    git(source, "add", "keep.bin")
    git(source, "commit", "-q", "-m", "main")
    merge = subprocess.run(
        ["git", "-C", str(source), "merge", "--no-commit", "conflict-side"],
        check=False,
        capture_output=True,
    )
    assert merge.returncode != 0
    (source / ".git" / "MERGE_HEAD").unlink()

    with pytest.raises(capture.CaptureError, match="unresolved index conflict"):
        capture.capture_source(source, tmp_path / "capture")


def test_committed_gitlink_is_refused(source: Path, tmp_path: Path) -> None:
    submodule = tmp_path / "submodule"
    submodule.mkdir()
    git(submodule, "init", "-q", "-b", "main")
    git(submodule, "config", "user.name", "Capture Test")
    git(submodule, "config", "user.email", "capture@example.invalid")
    (submodule / "payload.txt").write_text("submodule\n", encoding="utf-8")
    git(submodule, "add", "payload.txt")
    git(submodule, "commit", "-q", "-m", "base")
    submodule_head = subprocess.check_output(
        ["git", "-C", str(submodule), "rev-parse", "HEAD"],
        text=True,
    ).strip()
    git(
        source,
        "update-index",
        "--add",
        "--cacheinfo",
        f"160000,{submodule_head},vendor/submodule",
    )
    git(source, "commit", "-q", "-m", "gitlink")

    with pytest.raises(capture.CaptureError, match="tracked gitlink"):
        capture.capture_source(source, tmp_path / "capture")


def test_active_index_operation_is_refused(source: Path, tmp_path: Path) -> None:
    (source / ".git" / "index.lock").touch()

    with pytest.raises(capture.CaptureError, match="active Git index operation"):
        capture.capture_source(source, tmp_path / "capture")


@pytest.mark.parametrize("path", [".env", "credentials.txt", ".scratch/new.txt", "dist/out.bin"])
def test_reviewed_new_path_rejects_credentials_and_runtime(path: str, source: Path, tmp_path: Path) -> None:
    target = source / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("private\n", encoding="utf-8")

    with pytest.raises(capture.CaptureError, match="unsafe"):
        capture.capture_source(source, tmp_path / "capture", reviewed_paths=(path,))


def test_output_overlap_and_symlink_ancestry_are_refused(source: Path, tmp_path: Path) -> None:
    with pytest.raises(capture.CaptureError, match="overlaps|active repository"):
        capture.capture_source(source, source / "child")
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(capture.CaptureError, match="symlinked"):
        capture.capture_source(source, link / "capture")


def test_source_drift_after_materialization_is_refused_and_removed(source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original = capture._materialize

    def materialize_then_drift(output: Path, entries: tuple[object, ...]) -> tuple[str, str]:
        result = original(output, entries)
        (source / "keep.bin").write_bytes(b"drifted\n")
        return result

    monkeypatch.setattr(capture, "_materialize", materialize_then_drift)
    output = tmp_path / "capture"
    with pytest.raises(capture.CaptureError, match="changed during capture"):
        capture.capture_source(source, output)
    assert not output.exists()


def test_source_root_replacement_with_identical_state_is_refused_and_removed(
    source: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = capture._materialize

    def materialize_then_replace_root(output: Path, entries: tuple[object, ...]) -> tuple[str, str]:
        result = original(output, entries)
        retained = tmp_path / "retained-source"
        source.rename(retained)
        shutil.copytree(retained, source, symlinks=True)
        return result

    monkeypatch.setattr(capture, "_materialize", materialize_then_replace_root)
    output = tmp_path / "capture"
    with pytest.raises(capture.CaptureError, match="changed during capture"):
        capture.capture_source(source, output)
    assert not output.exists()


def test_source_entry_replacement_with_identical_bytes_is_refused_and_removed(
    source: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = capture._materialize

    def materialize_then_replace_entry(output: Path, entries: tuple[object, ...]) -> tuple[str, str]:
        result = original(output, entries)
        replacement = source / "replacement.bin"
        replacement.write_bytes((source / "keep.bin").read_bytes())
        replacement.chmod((source / "keep.bin").stat().st_mode & 0o777)
        os.replace(replacement, source / "keep.bin")
        return result

    monkeypatch.setattr(capture, "_materialize", materialize_then_replace_entry)
    output = tmp_path / "capture"
    with pytest.raises(capture.CaptureError, match="changed during capture"):
        capture.capture_source(source, output)
    assert not output.exists()


def test_reviewed_manifest_aliases_and_mapping_items(source: Path, tmp_path: Path) -> None:
    (source / "new-a.txt").write_text("a\n", encoding="utf-8")
    (source / "new-b.txt").write_text("b\n", encoding="utf-8")
    assert capture._read_reviewed_manifest(None) == ()
    assert capture._read_reviewed_manifest({"added_paths": ["new-b.txt"]}) == ("new-b.txt",)

    manifest_path = tmp_path / "reviewed.json"
    manifest_path.write_text(
        json.dumps({"paths": [{"path": "new-b.txt"}, "new-a.txt"]}),
        encoding="utf-8",
    )
    assert capture._read_reviewed_manifest(manifest_path) == ("new-a.txt", "new-b.txt")

    result = capture.capture_source(
        source,
        tmp_path / "capture",
        reviewed_manifest={"new_files": ["new-b.txt", {"path": "new-a.txt"}]},
    )
    assert result.manifest["reviewed_new_files"] == ["new-a.txt", "new-b.txt"]


@pytest.mark.parametrize(
    ("manifest", "message"),
    (
        ({"new_files": "new.txt"}, "must be a list"),
        ({"new_files": [{}]}, "malformed path"),
        ({"new_files": ["new.txt", "new.txt"]}, "duplicate paths"),
    ),
)
def test_reviewed_manifest_rejects_bad_selection(
    source: Path,
    tmp_path: Path,
    manifest: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(capture.CaptureError, match=message):
        capture.capture_source(source, tmp_path / "capture", reviewed_manifest=manifest)


def test_reviewed_manifest_missing_file_is_refused(source: Path, tmp_path: Path) -> None:
    with pytest.raises(capture.CaptureError, match="cannot be read"):
        capture.capture_source(
            source,
            tmp_path / "capture",
            reviewed_manifest=tmp_path / "does-not-exist.json",
        )


@pytest.mark.parametrize(
    "path",
    (
        None,
        "",
        "bad\x00path",
        "/absolute.txt",
        "trailing/",
        "double//slash.txt",
        "./dot.txt",
        "up/../path.txt",
        "-leading.txt",
        "dir/-child.txt",
    ),
)
def test_reviewed_path_must_be_canonical(source: Path, tmp_path: Path, path: object) -> None:
    with pytest.raises(capture.CaptureError, match="malformed|unsafe|non-canonical"):
        capture.capture_source(source, tmp_path / "capture", reviewed_paths=(path,))


@pytest.mark.parametrize(
    "path",
    ("identity.pem", "token.key", "archive.p12", "bundle.pfx", "my-credential.txt", "my-secret.txt"),
)
def test_reviewed_path_rejects_credential_suffixes_and_names(
    source: Path,
    tmp_path: Path,
    path: str,
) -> None:
    target = source / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("private\n", encoding="utf-8")
    with pytest.raises(capture.CaptureError, match="unsafe credential path"):
        capture.capture_source(source, tmp_path / "capture", reviewed_paths=(path,))


def test_reviewed_path_selection_refuses_tracked_absent_and_ignored(
    source: Path,
    tmp_path: Path,
) -> None:
    (source / "ignored.txt").write_text("ignored\n", encoding="utf-8")
    cases = (
        ("keep.bin", "already tracked"),
        ("missing.txt", "absent"),
        ("ignored.txt", "ignored"),
    )
    for index, (path, message) in enumerate(cases):
        with pytest.raises(capture.CaptureError, match=message):
            capture.capture_source(source, tmp_path / f"capture-{index}", reviewed_paths=(path,))


def test_explicit_and_manifest_reviewed_paths_cannot_overlap(source: Path, tmp_path: Path) -> None:
    (source / "new.txt").write_text("new\n", encoding="utf-8")
    with pytest.raises(capture.CaptureError, match="more than once"):
        capture.capture_source(
            source,
            tmp_path / "capture",
            reviewed_paths=("new.txt",),
            reviewed_manifest={"new_files": ["new.txt"]},
        )


@pytest.mark.parametrize(
    "marker",
    ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-apply", "rebase-merge", "sequencer"),
)
def test_active_git_operation_markers_are_refused(
    source: Path,
    tmp_path: Path,
    marker: str,
) -> None:
    marker_path = source / ".git" / marker
    if marker in {"rebase-apply", "rebase-merge", "sequencer"}:
        marker_path.mkdir()
    else:
        marker_path.touch()
    with pytest.raises(capture.CaptureError, match="active Git operation"):
        capture.capture_source(source, tmp_path / "capture", reviewed_paths=())


def test_tracked_credential_path_is_refused(source: Path, tmp_path: Path) -> None:
    (source / ".env").write_text("TOKEN=private\n", encoding="utf-8")
    git(source, "add", "-f", ".env")
    git(source, "commit", "-q", "-m", "unsafe tracked path")
    with pytest.raises(capture.CaptureError, match="tracked path.*unsafe credential path"):
        capture.capture_source(source, tmp_path / "capture")


def test_staged_credential_path_is_refused(source: Path, tmp_path: Path) -> None:
    (source / ".env").write_text("TOKEN=private\n", encoding="utf-8")
    git(source, "add", "-f", ".env")
    with pytest.raises(capture.CaptureError, match="indexed path.*unsafe credential path"):
        capture.capture_source(source, tmp_path / "capture")


@pytest.mark.parametrize("kind", ("plain", "bare", "uncommitted"))
def test_unsuitable_source_repository_is_refused(tmp_path: Path, kind: str) -> None:
    source = tmp_path / kind
    source.mkdir()
    if kind == "plain":
        message = "source is not a Git worktree"
    elif kind == "bare":
        git(source, "init", "-q", "--bare")
        message = "source is not a Git worktree|source must be a non-bare"
    else:
        git(source, "init", "-q", "-b", "main")
        message = "source must have a committed HEAD"
    with pytest.raises(capture.CaptureError, match=message):
        capture.capture_source(source, tmp_path / "capture")


def test_reviewed_special_file_is_refused(source: Path, tmp_path: Path) -> None:
    os.mkfifo(source / "pipe")
    with pytest.raises(capture.CaptureError, match="entry type is unsupported"):
        capture.capture_source(source, tmp_path / "capture", reviewed_paths=("pipe",))


def test_reviewed_special_mode_is_refused(source: Path, tmp_path: Path) -> None:
    target = source / "setuid.txt"
    target.write_text("mode\n", encoding="utf-8")
    target.chmod(0o4644)
    with pytest.raises(capture.CaptureError, match="unsupported special mode"):
        capture.capture_source(source, tmp_path / "capture", reviewed_paths=("setuid.txt",))


def test_reviewed_path_with_missing_parent_is_refused(source: Path, tmp_path: Path) -> None:
    with pytest.raises(capture.CaptureError, match="reviewed path is absent"):
        capture.capture_source(source, tmp_path / "capture", reviewed_paths=("missing/new.txt",))


@pytest.mark.parametrize("ancestor", ("file", "symlink"))
def test_reviewed_path_with_unsafe_ancestor_is_refused(
    source: Path,
    tmp_path: Path,
    ancestor: str,
) -> None:
    if ancestor == "file":
        (source / "parent").write_text("not a directory\n", encoding="utf-8")
    else:
        (source / "real").mkdir()
        (source / "parent").symlink_to("real", target_is_directory=True)
    with pytest.raises(capture.CaptureError, match="unsafe ancestor"):
        capture.capture_source(source, tmp_path / "capture", reviewed_paths=("parent/new.txt",))


@pytest.mark.parametrize("kind", ("git-meta", "file", "symlink", "empty-dir", "nonempty-dir", "missing-parent", "non-dir-parent", "active-repo"))
def test_capture_output_must_be_new_safe_and_outside_repositories(
    source: Path,
    tmp_path: Path,
    kind: str,
) -> None:
    if kind == "git-meta":
        output = source / ".git"
    elif kind == "file":
        output = tmp_path / "output"
        output.write_text("preserve\n", encoding="utf-8")
    elif kind == "symlink":
        target = tmp_path / "target"
        target.mkdir()
        output = tmp_path / "output"
        output.symlink_to(target, target_is_directory=True)
    elif kind == "empty-dir":
        output = tmp_path / "output"
        output.mkdir()
    elif kind == "nonempty-dir":
        output = tmp_path / "output"
        output.mkdir()
        (output / "existing").write_text("preserve\n", encoding="utf-8")
    elif kind == "missing-parent":
        output = tmp_path / "missing" / "output"
    elif kind == "non-dir-parent":
        parent = tmp_path / "parent"
        parent.write_text("not a directory\n", encoding="utf-8")
        output = parent / "output"
    else:
        other = tmp_path / "other"
        other.mkdir()
        git(other, "init", "-q", "-b", "main")
        output = other / "output"
    with pytest.raises(
        capture.CaptureError,
        match="Git metadata|direct directory|already exists|absent or empty|parent|ancestor|active repository",
    ):
        capture.capture_source(source, output)


def test_materialized_regular_bytes_are_verified_and_removed(
    source: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = capture._materialize

    def materialize_then_tamper(output: Path, entries: tuple[object, ...]) -> tuple[str, str]:
        result = original(output, entries)
        (output / "keep.bin").write_bytes(b"tampered\n")
        return result

    monkeypatch.setattr(capture, "_materialize", materialize_then_tamper)
    output = tmp_path / "capture"
    with pytest.raises(capture.CaptureError, match="captured file bytes or mode"):
        capture.capture_source(source, output)
    assert not output.exists()


def test_materialized_symlink_target_is_verified_and_removed(
    source: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = capture._materialize

    def materialize_then_tamper(output: Path, entries: tuple[object, ...]) -> tuple[str, str]:
        result = original(output, entries)
        (output / "link").unlink()
        (output / "link").symlink_to("gone.txt")
        return result

    monkeypatch.setattr(capture, "_materialize", materialize_then_tamper)
    output = tmp_path / "capture"
    with pytest.raises(capture.CaptureError, match="captured symlink bytes"):
        capture.capture_source(source, output)
    assert not output.exists()
