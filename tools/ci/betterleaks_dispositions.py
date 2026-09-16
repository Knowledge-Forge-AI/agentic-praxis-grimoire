"""Reconcile redacted BetterLeaks observations with exact nonsecret contexts.

Source bytes are hashed in memory; reports never retain match payloads. Line
numbers locate current observations but are not approval identities. Each
record permits exactly one occurrence; unmatched records require investigation.
"""

from __future__ import annotations

import hashlib
import ast
import json
import re
import stat
from collections import Counter
from pathlib import Path, PurePosixPath

SCHEMA = "apg-betterleaks-dispositions-v1"
IDENTITY_FIELDS = ("path", "rule", "match_sha256", "context_sha256")


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_identity(root: Path, observation: dict) -> dict[str, str]:
    """Hash the exact reported source lines and three surrounding lines."""
    path = observation.get("File")
    rule = observation.get("RuleID")
    start, end = observation.get("StartLine"), observation.get("EndLine")
    if not isinstance(path, str) or not isinstance(rule, str) or not rule:
        raise ValueError("invalid BetterLeaks source identity")
    relative = PurePosixPath(path)
    if not relative.parts or relative.is_absolute() or relative.as_posix() != path or ".." in relative.parts:
        raise ValueError("BetterLeaks path is not repository relative")
    if not all(type(n) is int for n in (start, end)) or not 1 <= start <= end:
        raise ValueError("invalid BetterLeaks source location")
    current = root
    for part in relative.parts:
        current = current / part
        mode = current.lstat().st_mode
        if stat.S_ISLNK(mode):
            raise ValueError("BetterLeaks source traverses a symlink")
    if not stat.S_ISREG(mode):
        raise ValueError("BetterLeaks source is not a regular file")
    before = current.stat()
    data = current.read_bytes()
    after = current.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
        after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns
    ):
        raise ValueError("BetterLeaks source changed during readback")
    lines = data.splitlines(keepends=True)
    if end > len(lines):
        raise ValueError("BetterLeaks source location is outside the file")
    scopes = []
    if current.suffix == ".py":
        try:
            tree = ast.parse(data)
        except SyntaxError as error:
            raise ValueError("BetterLeaks Python source cannot be parsed") from error
        scopes = [node.name for node in sorted(ast.walk(tree), key=lambda n: getattr(n, "lineno", 0))
                  if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                  and node.lineno <= start <= end <= node.end_lineno]
    context = json.dumps(scopes, separators=(",", ":")).encode() + b"\0"
    context += b"".join(lines[max(0, start - 4):end + 3])
    return {
        "path": path,
        "rule": rule,
        "match_sha256": _digest(b"".join(lines[start - 1:end])),
        "context_sha256": _digest(context),
    }


def load_records(path: Path) -> list[dict]:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate disposition JSON key")
            result[key] = value
        return result

    document = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)
    if not isinstance(document, dict) or set(document) != {"schema", "records"}:
        raise ValueError("invalid BetterLeaks disposition document")
    records = document["records"]
    if document["schema"] != SCHEMA or not isinstance(records, list):
        raise ValueError("invalid BetterLeaks disposition schema")
    seen = set()
    for record in records:
        required = {*IDENTITY_FIELDS, "reason", "owner", "review", "disposition"}
        if not isinstance(record, dict) or set(record) != required:
            raise ValueError("invalid BetterLeaks disposition record")
        if any(not isinstance(value, str) or not value.strip() for value in record.values()):
            raise ValueError("empty BetterLeaks disposition metadata")
        if record["disposition"] != "reviewed_nonsecret":
            raise ValueError("unreviewed BetterLeaks disposition")
        for field in ("match_sha256", "context_sha256"):
            if re.fullmatch(r"[0-9a-f]{64}", record[field]) is None:
                raise ValueError("invalid BetterLeaks content digest")
        identity = tuple(record[key] for key in IDENTITY_FIELDS)
        if identity in seen:
            raise ValueError("duplicate BetterLeaks disposition")
        seen.add(identity)
    return records


def reconcile(root: Path, observations: list[dict], records: list[dict]) -> dict:
    approved = Counter(tuple(record[key] for key in IDENTITY_FIELDS) for record in records)
    reviewed = 0
    unresolved = 0
    for observation in observations:
        identity = source_identity(root, observation)
        key = tuple(identity[field] for field in IDENTITY_FIELDS)
        if approved[key]:
            approved[key] -= 1
            reviewed += 1
        else:
            unresolved += 1
    return {
        "observations": len(observations),
        "reviewed_nonsecret": reviewed,
        "unresolved": unresolved,
        "unmatched_dispositions": sum(approved.values()),
    }
