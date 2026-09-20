"""APG166V-H-COMPLETE1 Scenario 14 packaging regression.

The subject manifest requires ``scenario-14/pkg/data/models.go`` while the root
``data/`` ignore rule historically excluded it from the Git product.  These
tests prove the exact-file exception through the maintained candidate-capture
owner in a disposable clone; the real repository index and object database are
never written.
"""
from __future__ import annotations

import hashlib
import io
import json
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest

from agent_phase.candidate import tree_identity
from testing.h_eval import subjects

ROOT = Path(__file__).resolve().parents[3]
CORPUS = "testing/fixtures/context-eval"
SUBJECT = f"{CORPUS}/subjects/scenario-14/pkg/data/models.go"


def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, check=check)


def _ignored(path: str) -> bool:
    completed = _git(ROOT, "check-ignore", "--no-index", "-q", path, check=False)
    if completed.returncode not in (0, 1):
        raise AssertionError(completed.stderr.decode())
    return completed.returncode == 0


def _manifest_entry() -> dict[str, object]:
    manifest = json.loads((ROOT / CORPUS / "subjects/manifest.json").read_bytes())
    (entry,) = manifest["scenarios"]["scenario-14"]["files"]
    return entry


def _clone(tmp_path: Path, name: str, *, gitignore: bytes) -> Path:
    clone = tmp_path / name
    _git(tmp_path, "clone", "--quiet", "--shared", str(ROOT), str(clone))
    (clone / ".gitignore").write_bytes(gitignore)
    target = clone / SUBJECT
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / SUBJECT, target)
    return clone


def _export(clone: Path, tree: str, destination: Path) -> dict[str, dict[str, object]]:
    # Git tree modes are the product identity; archive member modes carry a umask.
    modes = {}
    for line in _git(clone, "ls-tree", "-r", "-z", tree, "--", CORPUS).stdout.split(b"\0"):
        if line:
            meta, name = line.split(b"\t", 1)
            modes[name.decode()] = meta.split()[0].decode()
    archive = _git(clone, "archive", "--format=tar", tree, "--", CORPUS).stdout
    inventory: dict[str, dict[str, object]] = {}
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
        for member in stream.getmembers():
            if member.isfile():
                data = stream.extractfile(member).read()
                inventory[member.name] = {"bytes": len(data), "mode": modes[member.name],
                                          "sha256": hashlib.sha256(data).hexdigest()}
        stream.extractall(destination, filter="data")
    for name, item in inventory.items():
        (destination / name).chmod(0o755 if item["mode"] == "100755" else 0o644)
    return inventory


def test_exact_subject_is_reincluded_without_broadening_data_rules():
    assert not _ignored(SUBJECT)
    assert _ignored(f"{CORPUS}/subjects/scenario-14/pkg/data/sibling.go")
    assert _ignored(f"{CORPUS}/subjects/scenario-13/pkg/data/models.go")
    assert _ignored("data/generated.db")
    assert _ignored("nested/data/graph.json")


def test_retained_subject_bytes_match_existing_manifest():
    entry = _manifest_entry()
    data = (ROOT / SUBJECT).read_bytes()
    assert entry["path"] == "pkg/data/models.go"
    assert (len(data), hashlib.sha256(data).hexdigest()) == (entry["bytes"], entry["sha256"])
    assert (ROOT / SUBJECT).stat().st_mode & 0o777 == entry["mode"] == 0o644


def test_candidate_capture_exports_subject_and_verifies_manifest(tmp_path):
    real_index = ROOT / ".git/index"
    index_before = real_index.read_bytes()
    fixed = _clone(tmp_path, "fixed", gitignore=(ROOT / ".gitignore").read_bytes())
    head_ignore = _git(ROOT, "show", "HEAD:.gitignore").stdout
    historical = _clone(tmp_path, "historical", gitignore=head_ignore)

    fixed_tree = tree_identity(fixed)
    historical_tree = tree_identity(historical)

    fixed_export = tmp_path / "fixed-export"
    historical_export = tmp_path / "historical-export"
    fixed_inventory = _export(fixed, fixed_tree["tree"], fixed_export)
    historical_inventory = _export(historical, historical_tree["tree"], historical_export)
    entry = _manifest_entry()
    assert fixed_inventory[SUBJECT] == {"bytes": entry["bytes"], "mode": "100644",
                                        "sha256": entry["sha256"]}
    assert SUBJECT not in historical_inventory
    assert set(fixed_inventory) - set(historical_inventory) == {SUBJECT}

    verified = subjects.verify_manifest(corpus_root=fixed_export / CORPUS)
    assert set(verified["scenarios"]) == set(subjects.all_scenario_ids())
    with pytest.raises(subjects.SubjectError, match="scenario-14"):
        subjects.verify_manifest(corpus_root=historical_export / CORPUS)
    assert real_index.read_bytes() == index_before
