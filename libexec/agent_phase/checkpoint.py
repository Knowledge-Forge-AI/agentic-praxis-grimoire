"""Exact, reconstruction-verified evidence for checkpoint candidates."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any

from . import gitstate as gitstate_module


class CheckpointError(RuntimeError):
    pass


def _git(
    root: Path,
    arguments: list[str],
    *,
    environment: dict[str, str] | None = None,
    stdin: bytes | None = None,
) -> bytes:
    completed = subprocess.run(
        ["git", *arguments], cwd=root, env=environment, input=stdin,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120, check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", "replace").strip()
        raise CheckpointError(f"git {' '.join(arguments)} failed: {detail}")
    return completed.stdout


def _reconstruct(
    root: Path,
    entry_head: str,
    patch: bytes,
    *,
    expected_tree: str,
    paths: list[str],
) -> str:
    git_dir = _git(root, ["rev-parse", "--absolute-git-dir"]).decode().strip()
    with tempfile.TemporaryDirectory(prefix="agent-phase-checkpoint-") as scratch:
        private = Path(scratch)
        private_objects = private / "objects"
        private_objects.mkdir(mode=0o700)
        environment = os.environ.copy()
        environment.update({
            "GIT_INDEX_FILE": os.fspath(private / "index"),
            "GIT_OBJECT_DIRECTORY": os.fspath(private_objects),
            "GIT_ALTERNATE_OBJECT_DIRECTORIES": os.fspath(Path(git_dir) / "objects"),
        })
        _git(root, ["read-tree", entry_head], environment=environment)
        if patch:
            _git(
                root,
                ["apply", "--cached", "--binary", "--whitespace=nowarn", "-"],
                environment=environment,
                stdin=patch,
            )
        reconstructed = _git(
            root, ["write-tree"], environment=environment
        ).decode().strip()
        pathspecs = [gitstate_module.literal_pathspec(path) for path in paths]
        drift = _git(
            root,
            [
                "diff-tree", "-r", "-z", "--no-renames", "--name-only",
                reconstructed, expected_tree, "--", *pathspecs,
            ],
            environment=environment,
        )
        if drift:
            raise CheckpointError(
                "reconstructed checkpoint differs on phase-owned candidate paths"
            )
        return reconstructed


def create(
    directory: Any,
    entry: gitstate_module.EntryState,
    terminal_tree: str,
    phase_delta: list[gitstate_module.Change],
    real_index_identity: dict[str, Any],
    *,
    raw_terminal_tree: str | None = None,
) -> dict[str, Any]:
    patch_name = "checkpoint-candidate.patch"
    manifest_name = "checkpoint-candidate-manifest.json"
    phase_paths = sorted(change.path for change in phase_delta)
    phase_pathspecs = [
        gitstate_module.literal_pathspec(path) for path in phase_paths
    ]
    if phase_paths:
        patch = _git(
            entry.root,
            [
                "diff-tree", "-p", "--binary", "--full-index", "--no-renames",
                "--no-commit-id", entry.head, terminal_tree, "--", *phase_pathspecs,
            ],
        )
        reconstructed = _reconstruct(
            entry.root,
            entry.head,
            patch,
            expected_tree=terminal_tree,
            paths=phase_paths,
        )
    else:
        patch = b""
        reconstructed = _git(
            entry.root, ["rev-parse", f"{entry.head}^{{tree}}"]
        ).decode("ascii").strip()
    entry_commit_tree = _git(
        entry.root, ["rev-parse", f"{entry.head}^{{tree}}"]
    ).decode("ascii").strip()
    try:
        expected_manifest = gitstate_module.candidate_manifest(
            entry.root, entry_commit_tree, terminal_tree, paths=phase_paths
        )
    except gitstate_module.GitStateError as error:
        raise CheckpointError(error.detail) from error
    directory.write_bytes(patch_name, patch)
    manifest = {
        "schema": "agent-phase-checkpoint-candidate-v2",
        "entry_head": entry.head,
        "entry_tree": entry.tree,
        "observed_terminal_tree": raw_terminal_tree or terminal_tree,
        "publication_tree": terminal_tree,
        "checkpoint_tree": reconstructed,
        "patch_base": {"kind": "durable_entry_head", "treeish": entry.head},
        "phase_delta": [change._asdict() for change in phase_delta],
        "paths": expected_manifest["paths"],
        "patch": {
            "filename": patch_name,
            "sha256": hashlib.sha256(patch).hexdigest(),
            "size_bytes": len(patch),
            "format": "git-diff-binary-full-index-no-renames",
        },
        "real_index_identity": real_index_identity,
        "reconstruction": {
            "verified": True,
            "base": entry.head,
            "reconstructed_tree": reconstructed,
            "scope": "phase_owned_paths",
        },
    }
    manifest_path = directory.write_json(manifest_name, manifest)
    manifest_bytes = manifest_path.read_bytes()
    return {
        "patch": manifest["patch"],
        "manifest": {
            "filename": manifest_name,
            "sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "size_bytes": len(manifest_bytes),
        },
        "reconstruction": manifest["reconstruction"],
    }
