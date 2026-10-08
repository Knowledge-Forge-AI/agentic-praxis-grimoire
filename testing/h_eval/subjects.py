"""Deterministic, source-owned subjects for the APG166 H scenarios.

The frozen scenario JSON remains the authority for task text, authority, and
quality-oracle command.  This module owns only the clean input trees that a
later arm runner materializes before a provider attempt.  It deliberately
does not contain model answers or provider output.
"""
from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Iterator, Mapping


SCHEMA = "apg.h-subject/v1"
MANIFEST_SCHEMA = "apg.h-subject-manifest/v1"
_ROOT = Path(__file__).resolve().parents[1]
CORPUS_ROOT = _ROOT / "fixtures" / "context-eval"
SUBJECT_ROOT = CORPUS_ROOT / "subjects"
_SCENARIO_NAMES = tuple(f"scenario-{number:02d}" for number in range(1, 16))
_MODE_OVERRIDES = {"scenario-04/scripts/build.sh": 0o755}


class SubjectError(ValueError):
    """Raised when a frozen subject or materialization boundary is invalid."""


@dataclass(frozen=True)
class SubjectFile:
    """One regular source-owned file in a clean subject tree."""

    path: str
    data: bytes
    mode: int

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest()


def _encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("utf-8")


def _load_json(path: Path) -> dict:
    def pairs(items: list[tuple[str, object]]) -> dict:
        result: dict[str, object] = {}
        for key, value in items:
            if key in result:
                raise SubjectError(f"duplicate JSON key: {path}")
            result[key] = value
        return result

    try:
        value = json.loads(path.read_bytes(), object_pairs_hook=pairs)
    except (OSError, ValueError) as error:
        raise SubjectError(f"invalid frozen scenario: {path}") from error
    if not isinstance(value, dict):
        raise SubjectError(f"scenario is not an object: {path}")
    return value


def _scenario_path(scenario_id: str, corpus_root: Path = CORPUS_ROOT) -> Path:
    if scenario_id not in _SCENARIO_NAMES:
        raise SubjectError(f"unknown scenario: {scenario_id}")
    candidates = sorted(corpus_root.glob(f"{scenario_id}-*.json"))
    if len(candidates) != 1:
        raise SubjectError(f"expected one frozen scenario file for {scenario_id}")
    return candidates[0]


def load_scenario(scenario_id: str, *, corpus_root: Path = CORPUS_ROOT) -> dict:
    """Load one frozen scenario and verify its declared identifier."""
    value = _load_json(_scenario_path(scenario_id, Path(corpus_root)))
    if value.get("scenario_id") != scenario_id:
        raise SubjectError(f"scenario identifier mismatch for {scenario_id}")
    return value


def _fixture_root(scenario_id: str, corpus_root: Path = CORPUS_ROOT) -> Path:
    root = Path(corpus_root) / "subjects" / scenario_id
    if not root.is_dir() or root.resolve() != root:
        raise SubjectError(f"subject fixture missing: {scenario_id}")
    return root


def _safe_relative(path: Path) -> str:
    if path.is_absolute() or ".." in path.parts or "" in path.parts:
        raise SubjectError(f"unsafe subject path: {path}")
    return path.as_posix()


def _iter_fixture_files(root: Path, scenario_id: str) -> Iterator[SubjectFile]:
    files: list[SubjectFile] = []
    for path in root.rglob("*"):
        if path.is_symlink():
            raise SubjectError(f"subject fixture symlink refused: {path}")
        if path.is_dir():
            continue
        if not stat.S_ISREG(path.lstat().st_mode):
            raise SubjectError("nonregular subject fixture")
        relative = _safe_relative(path.relative_to(root))
        data = path.read_bytes()
        if relative == "schema/db.sqlite.b64":
            try:
                data = base64.b64decode(data.strip(), validate=True)
            except (ValueError, binascii.Error) as error:
                raise SubjectError("invalid source-owned SQLite encoding") from error
            if not data.startswith(b"SQLite format 3\x00"):
                raise SubjectError("source-owned SQLite header mismatch")
            relative = "schema/db.sqlite"
        mode = _MODE_OVERRIDES.get(f"{scenario_id}/{relative}", 0o644)
        files.append(SubjectFile(relative, data, mode))
    if not files:
        raise SubjectError(f"empty subject fixture: {scenario_id}")
    if len({item.path for item in files}) != len(files):
        raise SubjectError("duplicate decoded subject path")
    yield from sorted(files, key=lambda item: item.path)


def subject_files(scenario_id: str, *, corpus_root: Path = CORPUS_ROOT) -> dict[str, bytes]:
    """Return clean subject bytes keyed by safe relative path.

    This helper performs no materialization and is suitable for an arm owner
    that needs to create separate static and adaptive roots itself.
    """
    return {item.path: item.data for item in _iter_fixture_files(
        _fixture_root(scenario_id, Path(corpus_root)), scenario_id)}


def _inventory_files(root: Path) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for path in root.rglob("*"):
        if path.is_symlink():
            raise SubjectError(f"materialized subject symlink refused: {path}")
        if path.is_dir():
            continue
        if not stat.S_ISREG(path.lstat().st_mode):
            raise SubjectError("nonregular materialized subject")
        relative = _safe_relative(path.relative_to(root))
        data = path.read_bytes()
        mode = stat.S_IMODE(path.stat().st_mode)
        result.append({"path": relative, "mode": mode, "bytes": len(data),
                       "sha256": hashlib.sha256(data).hexdigest()})
    return sorted(result, key=lambda value: str(value["path"]))


def inventory(destination: Path) -> dict[str, object]:
    """Return a deterministic regular-file inventory for a materialized root."""
    destination = Path(destination)
    if not destination.is_dir() or destination.resolve() != destination:
        raise SubjectError(f"subject root is not a physical directory: {destination}")
    files = _inventory_files(destination)
    total = sum(int(value["bytes"]) for value in files)
    return {"files": files, "total_bytes": total,
            "tree_sha256": hashlib.sha256(_encoded(files)).hexdigest()}


def _ensure_physical_parent(destination: Path) -> None:
    if not destination.is_absolute():
        raise SubjectError("materialization destination must be absolute")
    parent = destination.parent
    if parent.is_symlink() or parent.resolve() != parent:
        raise SubjectError("materialization parent must be physical")
    if not parent.is_dir():
        raise SubjectError("materialization parent must exist")


def _write_file(destination: Path, item: SubjectFile) -> None:
    target = destination / item.path
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if target.parent.is_symlink() or target.parent.resolve() != target.parent:
        raise SubjectError(f"materialized parent escaped root: {item.path}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(target, flags, item.mode)
    try:
        with os.fdopen(fd, "wb") as stream:
            fd = -1
            stream.write(item.data)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if fd >= 0:
            os.close(fd)
    os.chmod(target, item.mode, follow_symlinks=False)


def materialize(scenario_id: str, destination: Path, *,
                corpus_root: Path = CORPUS_ROOT) -> dict[str, object]:
    """Materialize one clean scenario subject and return its byte inventory.

    ``destination`` must be a new absolute directory below an existing
    physical parent.  The function refuses existing roots, symlinks, unsafe
    fixture paths, and any post-copy inventory mismatch.
    """
    destination = Path(destination)
    _ensure_physical_parent(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    destination.mkdir(mode=0o700)
    scenario = load_scenario(scenario_id, corpus_root=Path(corpus_root))
    items = tuple(_iter_fixture_files(_fixture_root(scenario_id, Path(corpus_root)), scenario_id))
    for item in items:
        _write_file(destination, item)
    actual = inventory(destination)
    expected_files = [{"path": item.path, "mode": item.mode, "bytes": len(item.data),
                       "sha256": item.sha256} for item in items]
    expected = {"files": expected_files,
                "total_bytes": sum(item["bytes"] for item in expected_files),
                "tree_sha256": hashlib.sha256(_encoded(expected_files)).hexdigest()}
    manifest = load_manifest(corpus_root=Path(corpus_root))
    retained = manifest["scenarios"].get(scenario_id)
    scenario_sha256 = hashlib.sha256(_scenario_path(scenario_id, Path(corpus_root)).read_bytes()).hexdigest()
    if not isinstance(retained, dict) or retained.get("scenario_sha256") != scenario_sha256:
        raise SubjectError(f"subject manifest scenario identity mismatch: {scenario_id}")
    if {key: retained.get(key) for key in ("files", "total_bytes", "tree_sha256")} != expected:
        raise SubjectError(f"subject manifest inventory mismatch: {scenario_id}")
    if actual != expected:
        raise SubjectError(f"materialized subject inventory mismatch: {scenario_id}")
    return {"schema": SCHEMA, "scenario_id": scenario_id,
            "scenario_sha256": scenario_sha256,
            "files": expected_files, "total_bytes": expected["total_bytes"],
            "tree_sha256": expected["tree_sha256"]}


def load_manifest(*, corpus_root: Path = CORPUS_ROOT) -> dict[str, object]:
    """Load the source-owned all-fifteen initial subject manifest."""
    path = Path(corpus_root) / "subjects" / "manifest.json"
    value = _load_json(path)
    if value.get("schema") != MANIFEST_SCHEMA:
        raise SubjectError("invalid subject manifest schema")
    scenarios = value.get("scenarios")
    if not isinstance(scenarios, dict) or set(scenarios) != set(_SCENARIO_NAMES):
        raise SubjectError("subject manifest must bind all fifteen scenarios")
    for scenario_id in _SCENARIO_NAMES:
        entry = scenarios[scenario_id]
        if not isinstance(entry, dict) or not isinstance(entry.get("files"), list):
            raise SubjectError(f"invalid subject manifest entry: {scenario_id}")
    return value


def verify_manifest(*, corpus_root: Path = CORPUS_ROOT) -> dict[str, object]:
    """Recompute every source tree and fail if the retained manifest drifted."""
    manifest = load_manifest(corpus_root=Path(corpus_root))
    checked: dict[str, object] = {}
    for scenario_id in _SCENARIO_NAMES:
        items = tuple(_iter_fixture_files(_fixture_root(scenario_id, Path(corpus_root)), scenario_id))
        files = [{"path": item.path, "mode": item.mode, "bytes": len(item.data),
                  "sha256": item.sha256} for item in items]
        expected = {"files": files, "total_bytes": sum(item["bytes"] for item in files),
                    "tree_sha256": hashlib.sha256(_encoded(files)).hexdigest(),
                    "scenario_sha256": hashlib.sha256(_scenario_path(scenario_id, Path(corpus_root)).read_bytes()).hexdigest()}
        retained = manifest["scenarios"][scenario_id]
        if retained != expected:
            raise SubjectError(f"subject manifest drift: {scenario_id}")
        checked[scenario_id] = expected
    return {"schema": MANIFEST_SCHEMA, "scenarios": checked}


def verify_inventory(destination: Path, expected: Mapping[str, object]) -> None:
    """Fail closed when a subject tree differs from a retained inventory."""
    if not isinstance(expected, Mapping) or expected.get("schema") != SCHEMA:
        raise SubjectError("invalid subject inventory")
    actual = inventory(Path(destination))
    retained = {key: expected.get(key) for key in ("files", "total_bytes", "tree_sha256")}
    if actual != retained:
        raise SubjectError("subject inventory changed")


def all_scenario_ids() -> tuple[str, ...]:
    """Return the frozen fifteen identifiers in canonical order."""
    return _SCENARIO_NAMES
