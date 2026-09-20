"""Exact-path native evidence discovery; extracted source fixtures are inert."""
from __future__ import annotations

import os
import stat
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

from tools.ci import native_release_assembly as assembly
from tools.ci.native_seal import (
    CANONICAL_TARGETS,
    CONSUMER_RECEIPT_SCHEMA,
    LANE_SEAL_SCHEMA,
    RELEASE_BUNDLE_SEAL_SCHEMA,
    REQUIRED_LANES,
    SCAN_RECEIPT_SCHEMA,
    assert_direct_dir,
    canonical_json,
    load_canonical_json,
    sha256_bytes,
    sha256_file,
)
from tools.ci.native_topology import REQUIRED_NATIVE_JOBS

AGGREGATE_SCHEMA = "apg-matrix-aggregate-v1"
MATRIX_JOBS = frozenset(REQUIRED_NATIVE_JOBS - {"native-release-candidate-gate"})
HEX_RE = assembly.HEX_RE

EXPECTED_ROOT_DIRS = frozenset(
    {f"{job}-receipt" for job in MATRIX_JOBS}
    | set(REQUIRED_LANES)
    | {assembly.BUNDLE_ARTIFACT_NAME, "native-scan-evidence"}
)
EXPECTED_ROOT_ENTRIES = frozenset(EXPECTED_ROOT_DIRS | {"matrix-aggregate.json"})

RECEIPT_REQUIRED_FILES: dict[str, tuple[str, ...]] = {
    "native-guard": ("identity.json",),
    "native-darwin-arm64": ("lane-seal.json",),
    "native-linux-x64": ("lane-seal.json",),
    "native-linux-arm64": ("lane-seal.json",),
    "native-assemble": ("release-bundle-seal.json", "public-projection-manifest.json"),
    "native-consumer-darwin-arm64": ("consumer-receipt.json",),
    "native-consumer-linux-x64": ("consumer-receipt.json",),
    "native-consumer-linux-arm64": ("consumer-receipt.json",),
    "native-release-scans": ("scan-receipt.json", "scan-results.json"),
}


class GateError(ValueError):
    """Release candidate gate verification failure."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise GateError(message)


def _env_json(name: str) -> Any:
    raw = os.environ.get(name)
    _require(bool(raw), f"missing {name} environment variable")
    try:
        return assembly.strict_json(raw or "", name)
    except assembly.AssemblyError as error:
        raise GateError(str(error)) from error


def _self_hashed(doc: Mapping[str, Any], key: str, label: str) -> str:
    recorded = doc.get(key)
    _require(isinstance(recorded, str) and bool(HEX_RE.match(recorded)), f"{label} lacks a valid {key}")
    body = {k: v for k, v in doc.items() if k != key}
    _require(sha256_bytes(canonical_json(body)) == recorded, f"{label} {key} is tampered")
    return recorded


def _scan_tree_hygiene(evidence_dir: Path) -> None:
    """Scan entire evidence tree without parsing for links and special files at every depth."""
    assert_direct_dir(evidence_dir, "evidence directory")
    for root, dirs, files in os.walk(evidence_dir, followlinks=False):
        root_path = Path(root)
        if root_path.is_symlink():
            raise GateError(f"symlink forbidden in evidence: {root_path}")
        for entry in [*dirs, *files]:
            path = root_path / entry
            try:
                st = path.lstat()
            except OSError as error:
                raise GateError(f"evidence entry unavailable: {path}") from error
            if stat.S_ISLNK(st.st_mode):
                raise GateError(f"symlink forbidden in evidence: {path}")
            if not (stat.S_ISDIR(st.st_mode) or stat.S_ISREG(st.st_mode)):
                raise GateError(f"special file forbidden in evidence: {path}")


def _discover(evidence_dir: Path, bundle_ref: Mapping[str, Any] | None = None) -> dict[str, tuple[dict[str, Any], str]]:
    """Locate each allowlisted evidence document; links, duplicates, forged copies, and strays are fatal."""
    _scan_tree_hygiene(evidence_dir)

    actual_root_entries = {p.name for p in evidence_dir.iterdir()}
    if actual_root_entries != EXPECTED_ROOT_ENTRIES:
        extra_entries = actual_root_entries - EXPECTED_ROOT_ENTRIES
        _require(not extra_entries, f"wrong-root: duplicate evidence for unexpected entries: {sorted(extra_entries)}")
        missing_root_dirs = EXPECTED_ROOT_DIRS - actual_root_entries
        if missing_root_dirs:
            raise GateError(f"missing authority directory in evidence: {sorted(missing_root_dirs)}")

    found: dict[str, tuple[dict[str, Any], str]] = {}

    # Check receipt directory inventories
    for job in sorted(MATRIX_JOBS):
        receipt_dir = evidence_dir / f"{job}-receipt"
        if not receipt_dir.is_dir():
            continue
        actual_files = {p.name for p in receipt_dir.iterdir()}
        _require(all(p.is_file() for p in receipt_dir.iterdir()),
                 f"unexpected subdirectory in receipt directory: {receipt_dir.name}")
        allowed = set(RECEIPT_REQUIRED_FILES[job]) | {f"{job}-receipt.json"}
        wrapper = f"{job}-receipt.json"
        _require(wrapper in actual_files, f"missing matrix receipt wrapper for {job}")
        receipt = load_canonical_json(receipt_dir / wrapper)
        _require(receipt.get("schema") == "apg-matrix-receipt-v1" and receipt.get("job") == job and receipt.get("status") == "success", f"matrix receipt wrapper schema/job/status mismatch: {job}")
        if job == "native-guard":
            _require("identity.json" in actual_files, "missing native guard identity")
            identity = load_canonical_json(receipt_dir / "identity.json")
            _require(identity.get("schema_version") == "apgr.native-identity/v1", "guard identity schema mismatch")
            found["guard"] = (identity, sha256_file(receipt_dir / "identity.json"))
        extra = actual_files - allowed
        _require(not extra, f"duplicate/malformed recognized JSON or unexpected entry in {receipt_dir.name}: {sorted(extra)}")

    # Lane seals (allowlisted path: <lane>-receipt/lane-seal.json + proof copy in <lane>/[<slug>/]lane-seal.json)
    for lane in REQUIRED_LANES:
        receipt_seal = evidence_dir / f"{lane}-receipt" / "lane-seal.json"
        lane_root = evidence_dir / lane
        if not receipt_seal.is_file():
            continue
        _require(lane_root.is_dir(), f"missing lane artifact directory for {lane}")
        slug = CANONICAL_TARGETS[lane]["slug"]
        _require({p.name for p in lane_root.iterdir()} == {slug} and (lane_root / slug).is_dir(), f"lane {lane} requires exact slug root")
        ldir = lane_root / slug
        lane_seal = ldir / "lane-seal.json"
        _require(lane_seal.is_file(), f"missing lane seal in lane artifact {lane}")

        actual_lane_files = {p.name for p in ldir.iterdir()}
        expected_lane_files = assembly.LANE_FILES | {"lane-seal.json"}
        _require(actual_lane_files == expected_lane_files,
                 f"lane {lane} artifact inventory differs: missing={sorted(expected_lane_files - actual_lane_files)}, extra={sorted(actual_lane_files - expected_lane_files)}")
        _require(all(p.is_file() for p in ldir.iterdir()), f"unexpected subdirectory in lane {lane} artifact")

        load_canonical_json(lane_seal)
        doc = load_canonical_json(receipt_seal)
        receipt_sha = sha256_file(receipt_seal)
        lane_sha = sha256_file(lane_seal)
        _require(receipt_sha == lane_sha, f"lane {lane} seal proof copy differs (forged copy): {receipt_sha} != {lane_sha}")

        doc = load_canonical_json(receipt_seal)
        _require(doc.get("schema_version") == LANE_SEAL_SCHEMA, f"lane {lane} seal schema mismatch")
        lane_in_doc = doc.get("lane")
        _require(lane_in_doc in CANONICAL_TARGETS, f"unknown lane: {lane_in_doc!r}")
        _require(lane_in_doc == lane, f"lane seal lane mismatch: {lane_in_doc!r} != {lane!r}")
        found[f"lane:{lane}"] = (doc, receipt_sha)

    # Bundle seal (allowlisted path: native-assemble-receipt/release-bundle-seal.json + proof copy in native-release-candidate-bundle)
    bundle_receipt_path = evidence_dir / "native-assemble-receipt" / "release-bundle-seal.json"
    bundle_dir = evidence_dir / assembly.BUNDLE_ARTIFACT_NAME
    if bundle_receipt_path.is_file():
        _require(bundle_dir.is_dir(), "missing bundle artifact directory")
        bundle_proof_path = bundle_dir / "release-bundle-seal.json"
        _require(bundle_proof_path.is_file(), "missing release-bundle-seal.json in bundle artifact")

        load_canonical_json(bundle_proof_path)
        bundle_doc = load_canonical_json(bundle_receipt_path)
        receipt_bundle_sha = sha256_file(bundle_receipt_path)
        bundle_proof_sha = sha256_file(bundle_proof_path)
        _require(receipt_bundle_sha == bundle_proof_sha,
                 f"bundle seal proof copy differs (forged copy): {receipt_bundle_sha} != {bundle_proof_sha}")

        bundle_doc = load_canonical_json(bundle_receipt_path)
        _require(bundle_doc.get("schema_version") == RELEASE_BUNDLE_SEAL_SCHEMA, "bundle seal schema mismatch")

        # Validate bundle seal self hash and NATIVE_BUNDLE_JSON pin BEFORE deriving recursive expected bundle files
        bundle_seal_hash = _self_hashed(bundle_doc, "bundle_seal_sha256", "bundle seal")
        ref = bundle_ref if bundle_ref is not None else _env_json("NATIVE_BUNDLE_JSON")
        _require(bundle_seal_hash == ref.get("seal_sha256"), "bundle seal differs from NATIVE_BUNDLE_JSON")

        expected_bundle_files = set(assembly._bundle_files(bundle_doc)) | {"release-bundle-seal.json"}
        actual_bundle_files = {p.relative_to(bundle_dir).as_posix() for p in bundle_dir.rglob("*") if p.is_file()}
        _require(actual_bundle_files == expected_bundle_files,
                 f"bundle artifact inventory differs: missing={sorted(expected_bundle_files - actual_bundle_files)}, extra={sorted(actual_bundle_files - expected_bundle_files)}")
        expected_bundle_dirs = {str(parent) for name in expected_bundle_files for parent in PurePosixPath(name).parents} - {"."}
        actual_bundle_dirs = {p.relative_to(bundle_dir).as_posix() for p in bundle_dir.rglob("*") if p.is_dir()}
        _require(actual_bundle_dirs == expected_bundle_dirs,
                 f"bundle directory hierarchy differs: extra={sorted(actual_bundle_dirs - expected_bundle_dirs)}")

        found["bundle"] = (bundle_doc, receipt_bundle_sha)

    # Public projection manifest
    proj_path = evidence_dir / "native-assemble-receipt" / "public-projection-manifest.json"
    if proj_path.is_file():
        proj_doc = load_canonical_json(proj_path)
        _require(type(proj_doc.get("schema_version")) is int and proj_doc["schema_version"] == 1, "public projection schema mismatch")
        found["public-projection"] = (proj_doc, sha256_file(proj_path))

    # Consumer receipts
    for lane in REQUIRED_LANES:
        job = f"native-consumer-{lane.removeprefix('native-')}"
        consumer_receipt = evidence_dir / f"{job}-receipt" / "consumer-receipt.json"
        if not consumer_receipt.is_file():
            continue
        consumer_doc = load_canonical_json(consumer_receipt)
        _require(consumer_doc.get("schema_version") == CONSUMER_RECEIPT_SCHEMA, f"consumer receipt {lane} schema mismatch")
        lane_in_doc = consumer_doc.get("lane")
        _require(lane_in_doc in CANONICAL_TARGETS, f"unknown lane in consumer receipt: {lane_in_doc!r}")
        _require(lane_in_doc == lane, f"consumer receipt lane mismatch for {job}: {lane_in_doc!r} != {lane!r}")
        found[f"consumer:{lane}"] = (consumer_doc, sha256_file(consumer_receipt))

    # Scan results & scan receipt
    receipt_scan_results = evidence_dir / "native-release-scans-receipt" / "scan-results.json"
    scan_evidence_dir = evidence_dir / "native-scan-evidence"
    if receipt_scan_results.is_file():
        _require(scan_evidence_dir.is_dir(), "missing native-scan-evidence directory")
        evidence_scan_results = scan_evidence_dir / "scan-results.json"
        _require(evidence_scan_results.is_file(), "missing scan-results.json in native-scan-evidence")

        load_canonical_json(evidence_scan_results)
        scan_results_doc = load_canonical_json(receipt_scan_results)
        receipt_results_sha = sha256_file(receipt_scan_results)
        evidence_results_sha = sha256_file(evidence_scan_results)
        _require(receipt_results_sha == evidence_results_sha,
                 f"scan results proof copy differs from the scan results evidence (forged copy): {receipt_results_sha} != {evidence_results_sha}")

        scan_results_doc = load_canonical_json(receipt_scan_results)
        _require(scan_results_doc.get("schema") == assembly.SCAN_SCHEMA, "scan results rejected: schema mismatch")
        found["scan-results"] = (scan_results_doc, receipt_results_sha)

    scan_receipt_path = evidence_dir / "native-release-scans-receipt" / "scan-receipt.json"
    if scan_receipt_path.is_file():
        scan_receipt_doc = load_canonical_json(scan_receipt_path)
        _require(scan_receipt_doc.get("schema_version") == SCAN_RECEIPT_SCHEMA, "scan receipt schema mismatch")
        found["scan-receipt"] = (scan_receipt_doc, sha256_file(scan_receipt_path))

    # Matrix aggregate
    matrix_path = evidence_dir / "matrix-aggregate.json"
    if matrix_path.is_file():
        matrix_doc = load_canonical_json(matrix_path)
        _require(matrix_doc.get("schema") == AGGREGATE_SCHEMA, "matrix aggregate schema mismatch")
        found["matrix"] = (matrix_doc, sha256_file(matrix_path))

    return found

