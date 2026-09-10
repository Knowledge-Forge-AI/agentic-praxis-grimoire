"""Capture executable refusals across real Git and filesystem boundaries."""

import subprocess
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)


def git(source, *args):
    return subprocess.check_output(["git", "-C", str(source), *args], stderr=subprocess.PIPE)


def initialize(source, *, commit=True):
    source.mkdir()
    git(source, "init", "-q")
    git(source, "config", "user.name", "Capture Fixture")
    git(source, "config", "user.email", "capture@example.invalid")
    if commit:
        (source / "input.txt").write_text("maintained source\n")
        git(source, "add", "input.txt")
        git(source, "commit", "-qm", "fixture")


def invoke(source, output, *args):
    return subprocess.run([sys.executable, str(ROOT / "bin/apg-capture-source"),
        "--source", str(source), "--output", str(output), *args],
        text=True, capture_output=True, check=False)


@pytest.mark.parametrize("state,diagnostic", [
    ("not-git", "not a Git worktree"),
    ("unborn", "committed HEAD"),
    ("tracked-key", "tracked path"),
    ("indexed-sensitive", "indexed path"),
    ("indexed-gitlink", "indexed gitlink"),
])
def test_capture_refuses_ineligible_source_without_mutation(tmp_path, state, diagnostic):
    source, output = tmp_path / "source", tmp_path / "output"
    if state == "not-git":
        source.mkdir()
    else:
        initialize(source, commit=state != "unborn")
    if state == "tracked-key":
        (source / "fixture.pem").write_text("deliberately nonsecret fixture\n")
        git(source, "add", "fixture.pem")
        git(source, "commit", "-qm", "forbidden tracked path")
    elif state == "indexed-sensitive":
        (source / "fixture-secret.txt").write_text("deliberately nonsecret fixture\n")
        git(source, "add", "fixture-secret.txt")
    elif state == "indexed-gitlink":
        head = git(source, "rev-parse", "HEAD").decode().strip()
        git(source, "update-index", "--add", "--cacheinfo", f"160000,{head},module")
    index = source / ".git/index"
    before = index.read_bytes() if index.exists() else None
    result = invoke(source, output)
    assert result.returncode == 1
    assert diagnostic in result.stderr
    assert not output.exists()
    assert (index.read_bytes() if index.exists() else None) == before


@pytest.mark.parametrize("shape,diagnostic", [
    ("file", "direct directory"),
    ("link", "direct directory"),
    ("empty-directory", "already exists"),
    ("file-parent", "non-directory ancestor"),
    ("dangling-parent", "symlinked ancestor"),
    ("sidecar-equal", "manifest output overlaps capture output"),
])
def test_capture_refuses_output_aliases_and_receipt_collision(tmp_path, shape, diagnostic):
    source, output = tmp_path / "source", tmp_path / "output"
    initialize(source)
    args = ()
    if shape == "file":
        output.write_text("preserved output\n")
    elif shape == "link":
        output.symlink_to(source)
    elif shape == "empty-directory":
        output.mkdir()
    elif shape == "file-parent":
        parent = tmp_path / "parent"
        parent.write_text("preserved parent\n")
        output = parent / "output"
    elif shape == "dangling-parent":
        parent = tmp_path / "parent"
        parent.symlink_to(tmp_path / "missing")
        output = parent / "output"
    else:
        args = ("--manifest-output", str(output))
    before = git(source, "status", "--porcelain=v1")
    result = invoke(source, output, *args)
    assert result.returncode == 1
    assert diagnostic in result.stderr
    assert git(source, "status", "--porcelain=v1") == before
    assert (source / "input.txt").read_text() == "maintained source\n"
    if shape == "file":
        assert output.read_text() == "preserved output\n"
    elif shape == "file-parent":
        assert output.parent.read_text() == "preserved parent\n"
