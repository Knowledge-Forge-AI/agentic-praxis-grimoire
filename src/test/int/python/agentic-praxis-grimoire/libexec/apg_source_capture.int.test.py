"""Exercise the capture CLI and its real release-consumer boundary."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "libexec"))

import apg_public_release as release  # noqa: E402
import apg_source_capture as capture  # noqa: E402


def run_git(root: Path, *arguments: str) -> None:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.returncode == 0, result.stderr.decode()


def git_bytes(root: Path, *arguments: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(root), *arguments])


def source_state(root: Path) -> tuple[bytes, bytes, bytes, bytes]:
    return (
        (root / ".git" / "HEAD").read_bytes(),
        git_bytes(root, "rev-parse", "HEAD"),
        git_bytes(root, "for-each-ref", "--format=%(refname)%00%(objectname)", "refs"),
        (root / ".git" / "index").read_bytes(),
    )


def capture_cli(source: Path, output: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            str(ROOT / "bin" / "apg-capture-source"),
            "--source",
            str(source),
            "--output",
            str(output),
            *arguments,
        ],
        check=False,
        text=True,
        capture_output=True,
    )


def basic_source(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    source.mkdir()
    run_git(source, "init", "-q", "-b", "main")
    run_git(source, "config", "user.name", "Capture Test")
    run_git(source, "config", "user.email", "capture@example.invalid")
    (source / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
    (source / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    run_git(source, "add", ".")
    run_git(source, "commit", "-q", "-m", "base")
    return source


def test_cli_materializes_dirty_clone_for_existing_release_manifest(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "captured"
    subprocess.run(
        ["git", "clone", "-q", "--no-hardlinks", str(ROOT), str(source)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    (source / "README.md").write_bytes((source / "README.md").read_bytes() + b"\nprospective\n")
    reviewed = source / "testing" / "fixtures" / "apg-source-capture-fixture.txt"
    reviewed.parent.mkdir(parents=True, exist_ok=True)
    reviewed.write_text("fixture\n", encoding="utf-8")
    manifest = tmp_path / "reviewed.json"
    manifest.write_text(json.dumps({"new_files": ["testing/fixtures/apg-source-capture-fixture.txt"]}), encoding="utf-8")
    evidence = tmp_path / "capture-manifest.json"

    result = subprocess.run(
        [
            str(ROOT / "bin" / "apg-capture-source"),
            "--source",
            str(source),
            "--output",
            str(output),
            "--manifest",
            str(manifest),
            "--manifest-output",
            str(evidence),
            "--format",
            "json",
        ],
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["reviewed_new_files"] == [
        "testing/fixtures/apg-source-capture-fixture.txt"
    ]
    captured = release.resolve_repository(output, "captured")
    release_manifest = release.build_manifest(captured)
    paths = {entry["path"] for entry in release_manifest["entries"]}
    assert "testing/fixtures/apg-source-capture-fixture.txt" in paths
    assert (output / "README.md").read_bytes().endswith(b"prospective\n")
    assert evidence.stat().st_mode & 0o777 == 0o600


def test_cli_preserves_source_state_and_materializes_selected_worktree_delta(
    tmp_path: Path,
) -> None:
    source = basic_source(tmp_path)
    (source / "deleted.txt").write_text("delete me\n", encoding="utf-8")
    (source / "run.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    (source / "run.sh").chmod(0o755)
    (source / "raw-link").symlink_to("../raw-target")
    run_git(source, "add", "deleted.txt", "run.sh", "raw-link")
    run_git(source, "commit", "-q", "-m", "capture inputs")

    (source / "deleted.txt").unlink()
    (source / "run.sh").chmod(0o700)
    (source / "raw-link").unlink()
    (source / "raw-link").symlink_to("../raw-target")
    (source / "selected.txt").write_bytes(b"selected\x00bytes\n")
    (source / "foreign.txt").write_text("foreign\n", encoding="utf-8")
    (source / "ignored.txt").write_text("ignored\n", encoding="utf-8")

    before = source_state(source)
    output = tmp_path / "captured"
    result = capture_cli(source, output, "--new-file", "selected.txt", "--format", "json")

    assert result.returncode == 0, result.stderr
    document = json.loads(result.stdout)
    entries = {entry["path"]: entry for entry in document["entries"]}
    assert document["deleted"] == ["deleted.txt"]
    assert document["reviewed_new_files"] == ["selected.txt"]
    assert entries["run.sh"]["mode"] == "100755"
    assert entries["run.sh"]["permissions"] == "0700"
    assert entries["raw-link"]["type"] == "symlink"
    assert entries["raw-link"]["symlink_target"] == "../raw-target"
    assert entries["selected.txt"]["sha256"]
    assert not (output / "deleted.txt").exists()
    assert (output / "run.sh").stat().st_mode & 0o777 == 0o700
    assert os.readlink(output / "raw-link") == "../raw-target"
    assert (output / "selected.txt").read_bytes() == b"selected\x00bytes\n"
    assert not (output / "foreign.txt").exists()
    assert not (output / "ignored.txt").exists()
    assert source_state(source) == before

    assert git_bytes(output, "status", "--porcelain=v1", "-z", "--untracked-files=all") == b""
    output_head = document["output"]["head"].encode("ascii")
    assert git_bytes(output, "rev-parse", "HEAD").strip() == output_head
    assert git_bytes(output, "rev-list", "--parents", "-n", "1", "HEAD").split() == [output_head]
    assert git_bytes(output, "show", "-s", "--format=%P", "HEAD") == b"\n"


def test_cli_rejects_output_overlap(tmp_path: Path) -> None:
    source = basic_source(tmp_path)
    before = source_state(source)

    result = capture_cli(source, source / "capture")

    assert result.returncode == 1
    assert "active repository" in result.stderr or "overlaps" in result.stderr
    assert not (source / "capture").exists()
    assert source_state(source) == before


def test_cli_rejects_ignored_selected_new_file(tmp_path: Path) -> None:
    source = basic_source(tmp_path)
    (source / "ignored.txt").write_text("ignored\n", encoding="utf-8")

    result = capture_cli(source, tmp_path / "captured", "--new-file", "ignored.txt")

    assert result.returncode == 1
    assert "ignored" in result.stderr
    assert not (tmp_path / "captured").exists()


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO creation is unavailable")
def test_cli_rejects_unsupported_fifo(tmp_path: Path) -> None:
    source = basic_source(tmp_path)
    fifo = source / "pipe"
    os.mkfifo(fifo)

    result = capture_cli(source, tmp_path / "captured", "--new-file", "pipe")

    assert result.returncode == 1
    assert "unsupported" in result.stderr
    assert not (tmp_path / "captured").exists()


def test_cli_rejects_symlinked_output_ancestor(tmp_path: Path) -> None:
    source = basic_source(tmp_path)
    target = tmp_path / "target"
    target.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(target, target_is_directory=True)

    result = capture_cli(source, alias / "captured")

    assert result.returncode == 1
    assert "symlinked ancestor" in result.stderr
    assert not (target / "captured").exists()


def test_cli_rejects_unreviewed_staged_addition(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    run_git(source, "init", "-q", "-b", "main")
    run_git(source, "config", "user.name", "Capture Test")
    run_git(source, "config", "user.email", "capture@example.invalid")
    (source / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    run_git(source, "add", "tracked.txt")
    run_git(source, "commit", "-q", "-m", "base")
    (source / "staged.txt").write_text("staged\n", encoding="utf-8")
    run_git(source, "add", "staged.txt")
    result = capture_cli(source, tmp_path / "out")
    assert result.returncode == 1
    assert "not reviewed" in result.stderr


@pytest.mark.parametrize(
    ("manifest_payload", "message"),
    (
        ("{", "reviewed manifest cannot be read"),
        (json.dumps({"new_files": ["new.txt", "new.txt"]}), "duplicate paths"),
    ),
)
def test_cli_rejects_malformed_or_duplicate_reviewed_manifest(
    tmp_path: Path,
    manifest_payload: str,
    message: str,
) -> None:
    source = tmp_path / "source"
    output = tmp_path / "out"
    source.mkdir()
    run_git(source, "init", "-q", "-b", "main")
    run_git(source, "config", "user.name", "Capture Test")
    run_git(source, "config", "user.email", "capture@example.invalid")
    (source / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    run_git(source, "add", "tracked.txt")
    run_git(source, "commit", "-q", "-m", "base")
    manifest = tmp_path / "reviewed.json"
    manifest.write_text(manifest_payload, encoding="utf-8")

    result = capture_cli(source, output, "--manifest", str(manifest))
    assert result.returncode == 1
    assert message in result.stderr
    assert not output.exists()


@pytest.mark.parametrize("location", ("source", "existing", "capture-child"))
def test_cli_rejects_unsafe_manifest_output_without_overwrite(
    tmp_path: Path,
    location: str,
) -> None:
    source = tmp_path / "source"
    output = tmp_path / "out"
    source.mkdir()
    run_git(source, "init", "-q", "-b", "main")
    run_git(source, "config", "user.name", "Capture Test")
    run_git(source, "config", "user.email", "capture@example.invalid")
    (source / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    run_git(source, "add", "tracked.txt")
    run_git(source, "commit", "-q", "-m", "base")
    existing = tmp_path / "existing.json"
    if location == "source":
        manifest_output = source / "manifest.json"
    elif location == "existing":
        existing.write_text("preserve\n", encoding="utf-8")
        manifest_output = existing
    else:
        manifest_output = output / "manifest.json"

    result = capture_cli(
        source,
        output,
        "--manifest-output",
        str(manifest_output),
    )
    assert result.returncode == 1
    assert not output.exists()
    if location == "existing":
        assert existing.read_text(encoding="utf-8") == "preserve\n"


def test_cli_rejects_manifest_output_inside_source(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    run_git(source, "init", "-q", "-b", "main")
    run_git(source, "config", "user.name", "Capture Test")
    run_git(source, "config", "user.email", "capture@example.invalid")
    (source / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    run_git(source, "add", "tracked.txt")
    run_git(source, "commit", "-q", "-m", "base")
    result = capture_cli(
        source,
        tmp_path / "out",
        "--manifest-output",
        str(source / "manifest.json"),
    )
    assert result.returncode == 1
    assert "active repository" in result.stderr
    assert not (tmp_path / "out").exists()


def git_supports_sha256(root: Path) -> bool:
    probe_dir = root / "probe-sha256"
    probe = subprocess.run(
        ["git", "init", "-q", "-b", "main", "--object-format=sha256", str(probe_dir)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return probe.returncode == 0


def test_cli_captures_symlink_to_directory_without_inlining(tmp_path: Path) -> None:
    source = basic_source(tmp_path)
    pkg = source / "pkg"
    pkg.mkdir()
    (pkg / "module.py").write_text("print(42)\n", encoding="utf-8")
    (source / "link_pkg").symlink_to("pkg", target_is_directory=True)
    run_git(source, "add", "pkg", "link_pkg")
    run_git(source, "commit", "-q", "-m", "add pkg and symlink")

    (source / "new_link").symlink_to("pkg", target_is_directory=True)
    output = tmp_path / "captured"
    result = capture_cli(source, output, "--new-file", "new_link", "--format", "json")

    assert result.returncode == 0, result.stderr
    document = json.loads(result.stdout)
    entries = {entry["path"]: entry for entry in document["entries"]}

    assert entries["link_pkg"]["type"] == "symlink"
    assert entries["link_pkg"]["mode"] == "120000"
    assert entries["link_pkg"]["symlink_target"] == "pkg"
    assert entries["new_link"]["type"] == "symlink"
    assert entries["new_link"]["mode"] == "120000"
    assert entries["new_link"]["symlink_target"] == "pkg"
    assert entries["pkg/module.py"]["type"] == "file"

    assert (output / "link_pkg").is_symlink()
    assert os.readlink(output / "link_pkg") == "pkg"
    assert (output / "new_link").is_symlink()
    assert os.readlink(output / "new_link") == "pkg"
    assert (output / "link_pkg" / "module.py").read_text(encoding="utf-8") == "print(42)\n"
    assert git_bytes(output, "status", "--porcelain=v1") == b""


def test_cli_rejects_path_traversing_symlinked_directory_ancestor(tmp_path: Path) -> None:
    source = basic_source(tmp_path)
    real_dir = source / "real"
    real_dir.mkdir()
    (source / "sym_dir").symlink_to("real", target_is_directory=True)
    (real_dir / "file.txt").write_text("data\n", encoding="utf-8")

    output = tmp_path / "captured"
    result = capture_cli(source, output, "--new-file", "sym_dir/file.txt")

    assert result.returncode == 1
    assert "source path has an unsafe ancestor: sym_dir/file.txt" in result.stderr
    assert not output.exists()


def test_cli_captures_sha256_repository(tmp_path: Path) -> None:
    if not git_supports_sha256(tmp_path):
        pytest.skip("git does not support --object-format=sha256")

    source = tmp_path / "source"
    source.mkdir()
    run_git(source, "init", "-q", "-b", "main", "--object-format=sha256")
    run_git(source, "config", "user.name", "Capture Test")
    run_git(source, "config", "user.email", "capture@example.invalid")
    (source / "tracked.txt").write_text("sha256 base\n", encoding="utf-8")
    run_git(source, "add", ".")
    run_git(source, "commit", "-q", "-m", "base")
    (source / "new.txt").write_text("sha256 new\n", encoding="utf-8")

    before = source_state(source)
    output = tmp_path / "captured"
    result = capture_cli(source, output, "--new-file", "new.txt", "--format", "json")

    assert result.returncode == 0, result.stderr
    document = json.loads(result.stdout)
    assert len(document["source"]["head"]) == 64
    assert len(document["source"]["tree"]) == 64
    assert (output / "tracked.txt").read_text(encoding="utf-8") == "sha256 base\n"
    assert (output / "new.txt").read_text(encoding="utf-8") == "sha256 new\n"
    assert git_bytes(output, "status", "--porcelain=v1") == b""
    assert source_state(source) == before


@pytest.mark.parametrize("kind", ("plain", "bare", "unborn"))
def test_cli_rejects_unsuitable_source_repository(tmp_path: Path, kind: str) -> None:
    source = tmp_path / kind
    source.mkdir()
    if kind == "plain":
        expected = "source is not a Git worktree"
    elif kind == "bare":
        run_git(source, "init", "-q", "--bare")
        expected = "worktree"
    else:
        run_git(source, "init", "-q", "-b", "main")
        expected = "source must have a committed HEAD"

    output = tmp_path / "captured"
    result = capture_cli(source, output)

    assert result.returncode == 1
    assert expected in result.stderr
    assert not output.exists()


@pytest.mark.parametrize("marker", ("lock", "merge"))
def test_cli_rejects_active_git_operation(tmp_path: Path, marker: str) -> None:
    source = basic_source(tmp_path)
    output = tmp_path / "captured"
    if marker == "lock":
        (source / ".git" / "index.lock").touch()
        expected = "active Git index operation"
    else:
        (source / ".git" / "MERGE_HEAD").write_text("0" * 40 + "\n", encoding="utf-8")
        expected = "active Git operation"

    result = capture_cli(source, output)

    assert result.returncode == 1
    assert expected in result.stderr
    assert not output.exists()


def test_cli_rejects_unresolved_index_conflict(tmp_path: Path) -> None:
    source = basic_source(tmp_path)
    run_git(source, "checkout", "-q", "-b", "side")
    (source / "tracked.txt").write_text("side branch\n", encoding="utf-8")
    run_git(source, "commit", "-q", "-a", "-m", "side change")
    run_git(source, "checkout", "-q", "main")
    (source / "tracked.txt").write_text("main branch\n", encoding="utf-8")
    run_git(source, "commit", "-q", "-a", "-m", "main change")

    subprocess.run(
        ["git", "-C", str(source), "merge", "--no-commit", "side"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    (source / ".git" / "MERGE_HEAD").unlink()

    output = tmp_path / "captured"
    result = capture_cli(source, output)

    assert result.returncode == 1
    assert "unresolved index conflict" in result.stderr
    assert not output.exists()


def test_cli_rejects_tracked_gitlink(tmp_path: Path) -> None:
    source = basic_source(tmp_path)
    submodule = tmp_path / "submodule"
    submodule.mkdir()
    run_git(submodule, "init", "-q", "-b", "main")
    run_git(submodule, "config", "user.name", "Capture Test")
    run_git(submodule, "config", "user.email", "capture@example.invalid")
    (submodule / "file.txt").write_text("submodule\n", encoding="utf-8")
    run_git(submodule, "add", ".")
    run_git(submodule, "commit", "-q", "-m", "submodule init")

    submodule_head = git_bytes(submodule, "rev-parse", "HEAD").decode("ascii").strip()
    run_git(
        source,
        "update-index",
        "--add",
        "--cacheinfo",
        f"160000,{submodule_head},vendor/submodule",
    )
    run_git(source, "commit", "-q", "-m", "add gitlink")

    output = tmp_path / "captured"
    result = capture_cli(source, output)

    assert result.returncode == 1
    assert "tracked gitlink is unsupported: vendor/submodule" in result.stderr
    assert not output.exists()


@pytest.mark.parametrize(
    ("path_arg", "setup_action", "expected_message"),
    (
        ("../escape.txt", "none", "unsafe"),
        ("dir/-flag.txt", "none", "non-canonical"),
        (".env", "credential", "unsafe credential path"),
        (".scratch/data.txt", "scratch", "unsafe runtime or scratch path"),
        ("absent.txt", "none", "reviewed path is absent: absent.txt"),
        ("tracked.txt", "none", "reviewed path is already tracked: tracked.txt"),
    ),
)
def test_cli_rejects_unsafe_and_unreviewed_paths(
    tmp_path: Path,
    path_arg: str,
    setup_action: str,
    expected_message: str,
) -> None:
    source = basic_source(tmp_path)
    if setup_action == "credential":
        (source / ".env").write_text("SECRET=1\n", encoding="utf-8")
    elif setup_action == "scratch":
        (source / ".scratch").mkdir()
        (source / ".scratch" / "data.txt").write_text("data\n", encoding="utf-8")

    output = tmp_path / "captured"
    result = capture_cli(source, output, "--new-file", path_arg)

    assert result.returncode == 1
    assert expected_message in result.stderr
    assert not output.exists()


def test_cli_rejects_reviewed_path_overlap_with_manifest_and_missing_manifest(
    tmp_path: Path,
) -> None:
    source = basic_source(tmp_path)
    (source / "new.txt").write_text("new\n", encoding="utf-8")
    manifest = tmp_path / "reviewed.json"
    manifest.write_text(json.dumps({"new_files": ["new.txt"]}), encoding="utf-8")

    output = tmp_path / "captured"
    result = capture_cli(
        source,
        output,
        "--new-file",
        "new.txt",
        "--manifest",
        str(manifest),
    )
    assert result.returncode == 1
    assert "more than once" in result.stderr
    assert not output.exists()

    result_missing = capture_cli(
        source,
        output,
        "--manifest",
        str(tmp_path / "absent-manifest.json"),
    )
    assert result_missing.returncode == 1
    assert "reviewed manifest cannot be read" in result_missing.stderr
    assert not output.exists()


@pytest.mark.parametrize("scenario", ("existing-nonempty", "active-repo", "git-meta"))
def test_cli_rejects_invalid_output_destinations(tmp_path: Path, scenario: str) -> None:
    source = basic_source(tmp_path)
    if scenario == "existing-nonempty":
        destination = tmp_path / "existing"
        destination.mkdir()
        (destination / "item.txt").write_text("item\n", encoding="utf-8")
        expected = "capture output must be absent or empty"
    elif scenario == "active-repo":
        other_repo = tmp_path / "other-repo"
        other_repo.mkdir()
        run_git(other_repo, "init", "-q", "-b", "main")
        destination = other_repo / "captured"
        expected = "capture output is inside an active repository"
    else:
        destination = tmp_path / ".git"
        expected = "capture output cannot be Git metadata"

    result = capture_cli(source, destination)

    assert result.returncode == 1
    assert expected in result.stderr


def test_cli_format_text_emits_pass_line(tmp_path: Path) -> None:
    source = basic_source(tmp_path)
    output = tmp_path / "captured"
    result = capture_cli(source, output, "--format", "text")

    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("PASS captured prospective source: ")
    assert git_bytes(output, "status", "--porcelain=v1") == b""


def test_symlink_mid_read_drift_refusal_and_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = basic_source(tmp_path)
    (source / "target.txt").write_text("target\n", encoding="utf-8")
    (source / "drift_link").symlink_to("target.txt")
    run_git(source, "add", "target.txt", "drift_link")
    run_git(source, "commit", "-q", "-m", "symlink base")

    output = tmp_path / "captured"
    original_readlink = os.readlink
    observation_count = 0

    def seam_readlink(path: os.PathLike[str] | str, *args: object, **kwargs: object) -> str:
        nonlocal observation_count
        result = original_readlink(path, *args, **kwargs)
        if os.fspath(path).endswith("drift_link"):
            observation_count += 1
            if observation_count == 2:
                link_path = Path(os.fspath(path))
                link_path.unlink()
                link_path.symlink_to("different_target_causing_stat_drift.txt")
        return result

    monkeypatch.setattr(os, "readlink", seam_readlink)

    with pytest.raises(capture.CaptureError, match="source changed while reading: drift_link"):
        capture.capture_source(source, output)
    assert not output.exists()


def test_file_open_drift_refusal_and_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = basic_source(tmp_path)
    (source / "drift_open.txt").write_text("before open\n", encoding="utf-8")
    run_git(source, "add", "drift_open.txt")
    run_git(source, "commit", "-q", "-m", "open drift file")

    output = tmp_path / "captured"
    original_open = os.open
    open_count = 0

    def seam_open(path: os.PathLike[str] | int | str, flags: int, *args: object, **kwargs: object) -> int:
        nonlocal open_count
        if isinstance(path, (str, os.PathLike)) and os.fspath(path) == str(source / "drift_open.txt"):
            open_count += 1
            if open_count == 2:
                target_path = source / "drift_open.txt"
                replacement = target_path.parent / "drift_replacement.txt"
                replacement.write_bytes(b"replacement bytes with different size and inode\n")
                os.replace(replacement, target_path)
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", seam_open)

    with pytest.raises(capture.CaptureError, match="source changed while opening: drift_open.txt"):
        capture.capture_source(source, output)
    assert not output.exists()


def test_file_truncated_while_reading_refusal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = basic_source(tmp_path)
    (source / "trunc.txt").write_bytes(b"A" * 512)
    run_git(source, "add", "trunc.txt")
    run_git(source, "commit", "-q", "-m", "trunc file")

    output = tmp_path / "captured"
    in_target = False
    original_read_entry = capture._read_entry

    def seam_read_entry(
        root: Path,
        path: str,
        baseline: bool,
        root_identity: capture._PathIdentity,
    ) -> capture._ReadResult:
        nonlocal in_target
        if path == "trunc.txt":
            in_target = True
            try:
                return original_read_entry(root, path, baseline, root_identity)
            finally:
                in_target = False
        return original_read_entry(root, path, baseline, root_identity)

    original_read = os.read

    def seam_read(fd: int, n: int) -> bytes:
        if in_target:
            (source / "trunc.txt").write_bytes(b"")
        return original_read(fd, n)

    monkeypatch.setattr(capture, "_read_entry", seam_read_entry)
    monkeypatch.setattr(os, "read", seam_read)

    with pytest.raises(capture.CaptureError, match="source file was truncated while reading: trunc.txt"):
        capture.capture_source(source, output)
    assert not output.exists()


def test_file_grew_while_reading_refusal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = basic_source(tmp_path)
    (source / "grow.txt").write_bytes(b"initial bytes")
    run_git(source, "add", "grow.txt")
    run_git(source, "commit", "-q", "-m", "grow file")

    output = tmp_path / "captured"
    in_target = False
    original_read_entry = capture._read_entry

    def seam_read_entry(
        root: Path,
        path: str,
        baseline: bool,
        root_identity: capture._PathIdentity,
    ) -> capture._ReadResult:
        nonlocal in_target
        if path == "grow.txt":
            in_target = True
            try:
                return original_read_entry(root, path, baseline, root_identity)
            finally:
                in_target = False
        return original_read_entry(root, path, baseline, root_identity)

    original_read = os.read

    def seam_read(fd: int, n: int) -> bytes:
        if in_target and n == 1:
            with open(source / "grow.txt", "ab") as stream:
                stream.write(b"appended")
        return original_read(fd, n)

    monkeypatch.setattr(capture, "_read_entry", seam_read_entry)
    monkeypatch.setattr(os, "read", seam_read)

    with pytest.raises(capture.CaptureError, match="source file grew while reading: grow.txt"):
        capture.capture_source(source, output)
    assert not output.exists()


def test_file_disappeared_while_reading_refusal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = basic_source(tmp_path)
    (source / "disappear.txt").write_text("content\n", encoding="utf-8")
    run_git(source, "add", "disappear.txt")
    run_git(source, "commit", "-q", "-m", "disappear file")

    output = tmp_path / "captured"
    in_target = False
    original_read_entry = capture._read_entry

    def seam_read_entry(
        root: Path,
        path: str,
        baseline: bool,
        root_identity: capture._PathIdentity,
    ) -> capture._ReadResult:
        nonlocal in_target
        if path == "disappear.txt":
            in_target = True
            try:
                return original_read_entry(root, path, baseline, root_identity)
            finally:
                in_target = False
        return original_read_entry(root, path, baseline, root_identity)

    original_close = os.close

    def seam_close(fd: int) -> None:
        original_close(fd)
        if in_target:
            (source / "disappear.txt").unlink()

    monkeypatch.setattr(capture, "_read_entry", seam_read_entry)
    monkeypatch.setattr(os, "close", seam_close)

    with pytest.raises(capture.CaptureError, match="source disappeared while reading: disappear.txt"):
        capture.capture_source(source, output)
    assert not output.exists()


def test_file_drift_after_read_refusal_and_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = basic_source(tmp_path)
    (source / "drift_read.txt").write_text("initial\n", encoding="utf-8")
    run_git(source, "add", "drift_read.txt")
    run_git(source, "commit", "-q", "-m", "drift read file")

    output = tmp_path / "captured"
    in_target = False
    close_count = 0
    original_read_entry = capture._read_entry

    def seam_read_entry(
        root: Path,
        path: str,
        baseline: bool,
        root_identity: capture._PathIdentity,
    ) -> capture._ReadResult:
        nonlocal in_target
        if path == "drift_read.txt":
            in_target = True
            try:
                return original_read_entry(root, path, baseline, root_identity)
            finally:
                in_target = False
        return original_read_entry(root, path, baseline, root_identity)

    original_close = os.close

    def seam_close(fd: int) -> None:
        nonlocal close_count
        original_close(fd)
        if in_target:
            close_count += 1
            if close_count == 2:
                target_path = source / "drift_read.txt"
                temp = target_path.parent / "temp_close_drift.txt"
                temp.write_bytes(b"drifted bytes after descriptor closed\n")
                os.replace(temp, target_path)

    monkeypatch.setattr(capture, "_read_entry", seam_read_entry)
    monkeypatch.setattr(os, "close", seam_close)

    with pytest.raises(capture.CaptureError, match="source changed while reading: drift_read.txt"):
        capture.capture_source(source, output)
    assert not output.exists()


def test_file_unsupported_special_mode_refusal(tmp_path: Path) -> None:
    source = basic_source(tmp_path)
    (source / "setuid.txt").write_text("special mode\n", encoding="utf-8")
    (source / "setuid.txt").chmod(0o4755)

    output = tmp_path / "captured"
    result = capture_cli(source, output, "--new-file", "setuid.txt")
    assert result.returncode == 1
    assert "source file has unsupported special mode: setuid.txt" in result.stderr
    assert not output.exists()


def test_directory_drift_while_observing_refusal_and_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = basic_source(tmp_path)
    sub = source / "sub"
    sub.mkdir()
    (sub / "a.txt").write_text("a\n", encoding="utf-8")
    (sub / "b.txt").write_text("b\n", encoding="utf-8")
    run_git(source, "add", "sub/a.txt", "sub/b.txt")
    run_git(source, "commit", "-q", "-m", "sub directory")

    output = tmp_path / "captured"
    original_read_entry = capture._read_entry
    read_a_count = 0

    def seam_read_entry(
        root: Path,
        path: str,
        baseline: bool,
        root_identity: capture._PathIdentity,
    ) -> capture._ReadResult:
        nonlocal read_a_count
        result = original_read_entry(root, path, baseline, root_identity)
        if path == "sub/a.txt":
            read_a_count += 1
            if read_a_count == 2:
                os.chmod(sub, 0o700)
        return result

    monkeypatch.setattr(capture, "_read_entry", seam_read_entry)

    with pytest.raises(capture.CaptureError, match=r"source changed while observing: sub"):
        capture.capture_source(source, output)
    assert not output.exists()


def test_source_drift_during_materialize_refusal_and_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = basic_source(tmp_path)
    output = tmp_path / "captured"
    original_materialize = capture._materialize

    def seam_materialize(dest: Path, entries: tuple[capture._Entry, ...]) -> tuple[str, str]:
        result = original_materialize(dest, entries)
        (source / "tracked.txt").write_text("drifted content during materialize\n", encoding="utf-8")
        return result

    monkeypatch.setattr(capture, "_materialize", seam_materialize)

    with pytest.raises(capture.CaptureError, match="source changed during capture"):
        capture.capture_source(source, output)
    assert not output.exists()


def test_captured_materialized_files_tamper_detection_and_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = basic_source(tmp_path)
    (source / "link").symlink_to("tracked.txt")
    run_git(source, "add", "link")
    run_git(source, "commit", "-q", "-m", "add link")

    output = tmp_path / "captured"
    original_materialize = capture._materialize

    def seam_tamper_file(dest: Path, entries: tuple[capture._Entry, ...]) -> tuple[str, str]:
        result = original_materialize(dest, entries)
        (dest / "tracked.txt").write_bytes(b"tampered output file\n")
        return result

    monkeypatch.setattr(capture, "_materialize", seam_tamper_file)
    with pytest.raises(capture.CaptureError, match="captured file bytes or mode do not match the source manifest"):
        capture.capture_source(source, output)
    assert not output.exists()

    def seam_tamper_link(dest: Path, entries: tuple[capture._Entry, ...]) -> tuple[str, str]:
        result = original_materialize(dest, entries)
        (dest / "link").unlink()
        (dest / "link").symlink_to("tampered_link_target")
        return result

    monkeypatch.setattr(capture, "_materialize", seam_tamper_link)
    output2 = tmp_path / "captured2"
    with pytest.raises(capture.CaptureError, match="captured symlink bytes do not match the source manifest"):
        capture.capture_source(source, output2)
    assert not output2.exists()


@pytest.mark.parametrize("document,diagnostic", [
    ({"new_files": "new.txt"}, "must be a list"),
    ({"new_files": [False]}, "malformed path"),
    ({"new_files": [""]}, "malformed"),
    ({"new_files": ["/new.txt"]}, "unsafe"),
    ({"new_files": ["new.txt", "new.txt"]}, "duplicate paths"),
    ({"paths": [{"path": "new.txt"}]}, None),
    ({"added_paths": ["new.txt"]}, None),
    (["new.txt"], None),
])
def test_cli_reviewed_manifest_shapes_preserve_source_custody(tmp_path, document, diagnostic):
    source = basic_source(tmp_path)
    (source / "new.txt").write_text("reviewed addition\n")
    before = source_state(source)
    manifest = tmp_path / "selection.json"
    manifest.write_text(json.dumps(document))
    output = tmp_path / "captured"
    result = capture_cli(source, output, "--manifest", str(manifest), "--format", "json")
    assert source_state(source) == before
    if diagnostic is not None:
        assert result.returncode == 1
        assert diagnostic in result.stderr
        assert not output.exists()
    else:
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["reviewed_new_files"] == ["new.txt"]
        assert (output / "new.txt").read_bytes() == (source / "new.txt").read_bytes()


@pytest.mark.parametrize("selection", [{"new_files": ["new.txt"]}, {"paths": [{"path": "new.txt"}]}])
def test_capture_api_accepts_in_memory_reviewed_selection(tmp_path, selection):
    source = basic_source(tmp_path)
    (source / "new.txt").write_text("reviewed API input\n")
    before = source_state(source)
    output = tmp_path / "captured"
    result = capture.capture_source(source, output, reviewed_manifest=selection)
    assert result.manifest["reviewed_new_files"] == ["new.txt"]
    assert (output / "new.txt").read_text() == "reviewed API input\n"
    assert source_state(source) == before
