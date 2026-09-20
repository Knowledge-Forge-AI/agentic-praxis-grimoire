"""Bind runtime bytes, entry types and executable modes independently of H readiness."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import os

SCHEMA = "apgr.runtime-manifest/v1"
RUNTIME_ROOTS = ("bin", "libexec", "common", "codex", "claude", "antigravity", "src/agentic_praxis_grimoire", "testing/h_eval")


def classify_path(rel_path: str | Path) -> str:
    path = Path(rel_path).as_posix().removeprefix("./")
    if any(path.startswith(root + "/") for root in RUNTIME_ROOTS):
        return "runtime"
    if path.startswith(("src/test/", "testing/")):
        return "test"
    if path.startswith("docs/") or "/" not in path and path.endswith(".md"):
        return "doc"
    return "other"


def runtime_manifest(root: Path) -> dict:
    root = Path(root).resolve()
    files = {}
    for directory in RUNTIME_ROOTS:
        for path in sorted((root / directory).rglob("*")):
            rel = path.relative_to(root)
            if "__pycache__" in rel.parts or path.suffix in {".pyc", ".pyo"}:
                continue
            if path.is_symlink():
                files[rel.as_posix()] = {"kind": "symlink", "target": os.readlink(path)}
            elif path.is_file():
                files[rel.as_posix()] = {"kind": "file", "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "executable": bool(path.stat().st_mode & 0o111)}
    docs = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (root / "docs").rglob("*") if p.is_file() and not p.is_symlink()}
    digest = lambda values: hashlib.sha256(json.dumps(values, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"schema": SCHEMA, "runtime_identity": digest(files), "runtime_files": files,
            "doc_identity": digest(docs), "doc_files": docs,
            "classifications": {**{p: "runtime" for p in files}, **{p: "doc" for p in docs}}}


def runtime_identity(root: Path) -> str:
    return runtime_manifest(root)["runtime_identity"]
