"""Closed evidence-envelope support for the APGR pre-review aggregate."""

from __future__ import annotations

import hashlib
import json
import sys
from collections.abc import Iterable
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Protocol

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


LOG_CAP_BYTES = 200_000
AGGREGATE_CAP_BYTES = 5 * 1024 * 1024


class NamedCheck(Protocol):
    @property
    def name(self) -> str: ...


def bounded_log(text: str) -> str:
    """Cap log output at LOG_CAP_BYTES bytes with an explicit truncation notice."""
    encoded = text.encode("utf-8")
    if len(encoded) <= LOG_CAP_BYTES:
        return text
    suffix = b"\n[log truncated at bounded evidence cap]\n"
    return (encoded[: LOG_CAP_BYTES - len(suffix)] + suffix).decode(
        "utf-8", errors="ignore"
    )


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _expected_payloads(selected: Iterable[NamedCheck]) -> tuple[str, ...]:
    names = [check.name for check in selected]
    payloads = [f"{name}.log" for name in names]
    payloads.append("results.json")
    return tuple(payloads)


def verify_evidence(evidence_dir: Path, selected: Iterable[NamedCheck]) -> None:
    """Validate closed evidence envelope integrity, schema, sizes, and cryptographic digests."""
    expected_payloads = _expected_payloads(selected)
    expected_paths = set(expected_payloads) | {"manifest.json"}
    observed = {
        path.relative_to(evidence_dir).as_posix()
        for path in evidence_dir.rglob("*")
        if path.is_file()
    }
    extra = sorted(observed - expected_paths)
    missing = sorted(expected_paths - observed)
    if extra:
        raise RuntimeError(f"unexpected evidence path: {extra[0]}")
    if missing:
        raise RuntimeError(f"missing evidence path: {missing[0]}")
    for path_str in expected_paths:
        p = evidence_dir / path_str
        if not p.is_file():
            raise RuntimeError(f"evidence artifact contains a non-file path: {path_str}")

    manifest_path = evidence_dir / "manifest.json"
    try:
        manifest_text = manifest_path.read_text(encoding="utf-8")
        if not manifest_text.strip():
            raise RuntimeError("evidence manifest is empty")
        document = json.loads(manifest_text)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise RuntimeError(f"evidence manifest is malformed: {error}") from error

    valid_manifest_schemas = {"apg-pre-review-manifest-v1", "repomap-pre-review-manifest-v1"}
    if not isinstance(document, dict) or document.get("schema") not in valid_manifest_schemas:
        raise RuntimeError("evidence manifest schema is invalid")
    artifacts = document.get("artifacts")
    if not isinstance(artifacts, list):
        raise TypeError("evidence manifest artifact list is invalid")

    by_path = {
        item.get("path"): item
        for item in artifacts
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    if set(by_path) != set(expected_payloads) or len(by_path) != len(artifacts):
        raise RuntimeError("evidence manifest paths do not match the declared payloads")

    payload_size = 0
    for relative in expected_payloads:
        path = evidence_dir / relative
        size = path.stat().st_size
        item = by_path[relative]
        if item.get("size_bytes") != size:
            raise RuntimeError(f"size mismatch for evidence path: {relative}")
        expected_sha = item.get("sha256")
        actual_sha = _digest(path)
        if expected_sha != actual_sha:
            raise RuntimeError(f"digest mismatch for evidence path: {relative}")
        if relative.endswith(".log") and size > LOG_CAP_BYTES:
            raise RuntimeError(f"oversized evidence log: {relative}")
        if size > AGGREGATE_CAP_BYTES:
            raise RuntimeError(f"oversized evidence payload: {relative}")
        if relative == "results.json":
            try:
                res_text = path.read_text(encoding="utf-8")
                if not res_text.strip():
                    raise RuntimeError("results.json is empty")
                json_doc = json.loads(res_text)
            except (OSError, ValueError, json.JSONDecodeError) as error:
                raise RuntimeError(f"malformed evidence payload: {relative}") from error
            valid_results_schemas = {"apg-pre-review-result-v1", "repomap-pre-review-result-v2"}
            if not isinstance(json_doc, dict) or json_doc.get("schema") not in valid_results_schemas:
                raise RuntimeError(f"malformed evidence payload: {relative}")
        payload_size += size

    if document.get("payload_uncompressed_bytes") != payload_size:
        raise RuntimeError("evidence manifest aggregate size is invalid")
    aggregate_size = sum(
        (evidence_dir / relative).stat().st_size for relative in expected_paths
    )
    if aggregate_size > AGGREGATE_CAP_BYTES:
        raise RuntimeError("evidence artifact exceeds the aggregate size cap")


def finalize_evidence(
    evidence_dir: Path,
    selected: Iterable[NamedCheck],
    results: Iterable[object],
) -> int:
    """Seal and verify the envelope, returning its remaining byte capacity."""
    selected = tuple(selected)
    result_document = {
        "schema": "apg-pre-review-result-v1",
        "results": [
            asdict(result) if is_dataclass(result) and not isinstance(result, type) else result
            for result in results
        ],
    }
    (evidence_dir / "results.json").write_text(
        json.dumps(result_document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    artifacts = []
    payload_size = 0
    for relative in _expected_payloads(selected):
        path = evidence_dir / relative
        if not path.is_file():
            raise RuntimeError(f"missing evidence path: {relative}")
        size = path.stat().st_size
        payload_size += size
        artifacts.append(
            {
                "path": relative,
                "sha256": _digest(path),
                "size_bytes": size,
            }
        )
    manifest = {
        "schema": "apg-pre-review-manifest-v1",
        "artifacts": artifacts,
        "payload_uncompressed_bytes": payload_size,
    }
    (evidence_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    verify_evidence(evidence_dir, selected)
    return AGGREGATE_CAP_BYTES - payload_size - (evidence_dir / "manifest.json").stat().st_size
