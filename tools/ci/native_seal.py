#!/usr/bin/env python3
"""Deterministic sealing, hashing, and receipt contracts for APGR native CI."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

LANE_SEAL_SCHEMA = "apgr.native-lane-seal/v1"
RELEASE_BUNDLE_SEAL_SCHEMA = "apgr.native-release-bundle-seal/v1"
CONSUMER_RECEIPT_SCHEMA = "apgr.native-consumer-receipt/v1"
SCAN_RECEIPT_SCHEMA = "apgr.native-scan-receipt/v1"
RC_INDEX_SCHEMA = "apgr.native-rc-index/v1"
IDENTITY_SCHEMA = "apgr.native-identity/v1"

CANONICAL_TARGETS: dict[str, dict[str, str]] = {
    "native-darwin-arm64": {
        "lane": "native-darwin-arm64", "target": "darwin/arm64", "slug": "darwin-arm64",
        "go_binary": "go/darwin-arm64/apgr", "npm_slug": "darwin-arm64",
        "python_tag": "macosx_11_0_arm64", "system": "darwin", "arch": "arm64",
    },
    "native-linux-x64": {
        "lane": "native-linux-x64", "target": "linux/amd64", "slug": "linux-x64",
        "go_binary": "go/linux-amd64/apgr", "npm_slug": "linux-x64",
        "python_tag": "manylinux_2_17_x86_64", "system": "linux", "arch": "amd64",
    },
    "native-linux-arm64": {
        "lane": "native-linux-arm64", "target": "linux/arm64", "slug": "linux-arm64",
        "go_binary": "go/linux-arm64/apgr", "npm_slug": "linux-arm64",
        "python_tag": "manylinux_2_17_aarch64", "system": "linux", "arch": "arm64",
    },
}
REQUIRED_LANES = tuple(CANONICAL_TARGETS.keys())


class SealError(ValueError):
    """Cryptographic seal or receipt invariant failure."""


def canonical_json(data: Any) -> bytes:
    """Format JSON deterministically with sorted keys and compact separators."""
    return (json.dumps(data, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def load_canonical_json(path: Path) -> dict[str, Any]:
    """Read a JSON document with strict duplicate key prevention and direct file check."""
    assert_direct_file(path, "JSON document")

    def _object_pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for k, v in items:
            if k in result:
                raise SealError(f"duplicate key in {path}: {k}")
            result[k] = v
        return result

    try:
        doc = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_object_pairs)
        if not isinstance(doc, dict):
            raise SealError(f"expected JSON object at {path}")
        return doc
    except (OSError, json.JSONDecodeError) as err:
        raise SealError(f"failed to read JSON at {path}: {err}") from err


def check_containment(path: Path, label: str = "output") -> Path:
    """Hosted runtime outputs must be under RUNNER_TEMP and outside the checkout."""
    workspace, runner_temp = os.environ.get("GITHUB_WORKSPACE"), os.environ.get("RUNNER_TEMP")
    resolved = path.resolve()
    if workspace:
        ws_path = Path(workspace).resolve()
        if resolved == ws_path or resolved.is_relative_to(ws_path):
            raise SealError(f"{label} path must be outside GITHUB_WORKSPACE (under RUNNER_TEMP): {path}")
        if not runner_temp or not resolved.is_relative_to(Path(runner_temp).resolve()):
            raise SealError(f"{label} must be under RUNNER_TEMP")
    return path


def assert_direct_file(path: Path, label: str = "file") -> Path:
    """Ensure path is a direct regular file (never a symlink)."""
    if path.is_symlink():
        raise SealError(f"{label} must not be a symlink: {path}")
    try:
        st = path.lstat()
    except OSError as error:
        raise SealError(f"{label} is unavailable: {path}") from error
    if not stat.S_ISREG(st.st_mode):
        raise SealError(f"{label} must be a direct regular file: {path}")
    return path


def assert_direct_dir(path: Path, label: str = "directory") -> Path:
    """Ensure path is a direct directory (never a symlink)."""
    if path.is_symlink():
        raise SealError(f"{label} must not be a symlink: {path}")
    try:
        st = path.lstat()
    except OSError as error:
        raise SealError(f"{label} is unavailable: {path}") from error
    if not stat.S_ISDIR(st.st_mode):
        raise SealError(f"{label} must be a direct directory: {path}")
    return path


def sha256_file(path: Path) -> str:
    """Compute sha256 of a direct regular file."""
    assert_direct_file(path)
    hasher = hashlib.sha256()
    with open(path, "rb") as stream:
        while chunk := stream.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inspect_directory_files(directory: Path, exclude_names: set[str] | None = None) -> dict[str, dict[str, Any]]:
    """Scan directory recursively, rejecting any symlink, returning relative paths and digests."""
    assert_direct_dir(directory)
    excludes = exclude_names or set()
    files_map: dict[str, dict[str, Any]] = {}
    for root, dirs, files in os.walk(directory):
        root_path = Path(root)
        if root_path.is_symlink() or any((root_path / d).is_symlink() for d in dirs):
            raise SealError(f"symlinked directory forbidden in {directory}")
        for f in sorted(files):
            if root_path == directory and f in excludes:
                continue
            f_path = root_path / f
            if f_path.is_symlink():
                raise SealError(f"symlinked file forbidden: {f_path}")
            rel = f_path.relative_to(directory).as_posix()
            files_map[rel] = {"sha256": sha256_file(f_path), "size_bytes": f_path.stat().st_size}
    return dict(sorted(files_map.items()))


def write_github_output(key: str, value: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as stream:
        stream.write(f"{key}={value}\n")


def build_lane_seal(lane: str, target: str, slug: str, commit: str, tree: str, lane_dir: Path) -> dict[str, Any]:
    files = inspect_directory_files(lane_dir, exclude_names={"lane-seal.json"})
    required = {"apgr", "apgr.binary-manifest.json", "go-version-m.txt", "nix-evidence.json", "nix-compiler-identity.txt", "go-tests.log"}
    missing = required - set(files.keys())
    if missing:
        raise SealError(f"lane directory {lane_dir} is missing: {sorted(missing)}")
    payload: dict[str, Any] = {
        "schema_version": LANE_SEAL_SCHEMA, "lane": lane, "target": target,
        "target_slug": slug, "source_commit": commit, "source_tree": tree, "files": files,
        "evidence": "native-execution", "compiler_version": "go1.26.9",
        "pr_head_sha": os.environ.get("PR_HEAD_SHA"), "pr_base_sha": os.environ.get("PR_BASE_SHA"),
        "runner_os": os.environ.get("RUNNER_OS"), "runner_arch": os.environ.get("RUNNER_ARCH"),
        "runner_image": os.environ.get("ImageOS"), "runner_image_version": os.environ.get("ImageVersion"),
        "workflow_sha256": sha256_file(Path(__file__).resolve().parents[2] / ".github/workflows/native-qualification.yml"),
    }
    payload["seal_sha256"] = sha256_bytes(canonical_json(payload))
    (lane_dir / "lane-seal.json").write_bytes(canonical_json(payload))
    return payload


def verify_lane_seal(seal_path: Path, expected_lane: str | None = None) -> dict[str, Any]:
    doc = load_canonical_json(seal_path)
    if doc.get("schema_version") != LANE_SEAL_SCHEMA:
        raise SealError(f"invalid lane seal schema: {doc.get('schema_version')}")
    if expected_lane and doc.get("lane") != expected_lane:
        raise SealError(f"lane mismatch: expected {expected_lane}, got {doc.get('lane')}")
    lane = doc.get("lane")
    if lane not in CANONICAL_TARGETS:
        raise SealError("unknown native lane")
    spec = CANONICAL_TARGETS[lane]
    if doc.get("target") != spec["target"] or doc.get("target_slug") != spec["slug"]:
        raise SealError("native lane target identity mismatch")
    if doc.get("evidence") != "native-execution" or doc.get("compiler_version") != "go1.26.9":
        raise SealError("native execution/compiler proof missing")
    runner_os = "macOS" if spec["system"] == "darwin" else "Linux"
    runner_arch = "ARM64" if spec["arch"] == "arm64" else "X64"
    if doc.get("runner_os") != runner_os or doc.get("runner_arch") != runner_arch:
        raise SealError("native runner identity mismatch")
    if not doc.get("runner_image") or not doc.get("runner_image_version"):
        raise SealError("native runner image identity missing")
    recorded = doc.get("seal_sha256")
    if not recorded or not isinstance(recorded, str):
        raise SealError("lane seal is missing seal_sha256")
    check_doc = dict(doc)
    check_doc.pop("seal_sha256", None)
    if sha256_bytes(canonical_json(check_doc)) != recorded:
        raise SealError(f"lane seal digest tampered: {recorded}")
    actual = inspect_directory_files(seal_path.parent, exclude_names={"lane-seal.json"})
    declared = doc.get("files", {})
    if set(actual.keys()) != set(declared.keys()):
        raise SealError(f"lane file inventory mismatch in {seal_path.parent}")
    if not {"apgr", "apgr.binary-manifest.json", "go-version-m.txt", "nix-evidence.json", "nix-compiler-identity.txt", "go-tests.log"} <= set(actual):
        raise SealError("native lane required evidence missing")
    for name, spec in declared.items():
        if actual[name]["sha256"] != spec["sha256"] or actual[name]["size_bytes"] != spec["size_bytes"]:
            raise SealError(f"lane file {name} verification failed")
    return doc


def build_bundle_seal(bundle_dir: Path, commit: str, tree: str, lane_seals: dict[str, Any]) -> dict[str, Any]:
    assert_direct_dir(bundle_dir)
    files = inspect_directory_files(bundle_dir, exclude_names={"release-bundle-seal.json"})
    if set(lane_seals) != set(REQUIRED_LANES):
        raise SealError("bundle requires exactly three native lane seals")
    go_bins = [k for k in files if k.startswith("go/") and k.endswith("/apgr")]
    wheels = [k for k in files if k.startswith("python/") and k.endswith(".whl")]
    sdists = [k for k in files if k.startswith("python/") and k.endswith((".tar.gz", ".zip"))]
    npms = [k for k in files if k.startswith("npm/") and k.endswith(".tgz")]
    total = len(go_bins) + len(wheels) + len(sdists) + len(npms)
    if total != 11 or len(go_bins) != 3 or len(wheels) != 3 or len(sdists) != 1 or len(npms) != 4:
        raise SealError(f"expected 11 deliverables (3 go, 3 wheels, 1 sdist, 4 npms), found {total}")
    deliverables = sorted(go_bins + wheels + sdists + npms)
    assets = {name: files[name] for name in deliverables}
    payload: dict[str, Any] = {
        "schema_version": RELEASE_BUNDLE_SEAL_SCHEMA, "source_commit": commit, "source_tree": tree,
        "asset_count": 11, "assets": assets,
        "files": files,
        "manifest_sha256": sha256_file(bundle_dir / "apg-distribution-manifest.json"),
        "checksums_sha256": sha256_file(bundle_dir / "SHA256SUMS"),
        "lane_seals": {k: lane_seals[k]["seal_sha256"] for k in sorted(lane_seals)},
    }
    payload["bundle_seal_sha256"] = sha256_bytes(canonical_json(payload))
    (bundle_dir / "release-bundle-seal.json").write_bytes(canonical_json(payload))
    return payload


def verify_bundle_seal(bundle_dir: Path, expected_seal_sha256: str | None = None) -> dict[str, Any]:
    doc = load_canonical_json(bundle_dir / "release-bundle-seal.json")
    if doc.get("schema_version") != RELEASE_BUNDLE_SEAL_SCHEMA:
        raise SealError(f"invalid bundle seal schema: {doc.get('schema_version')}")
    if doc.get("asset_count") != 11 or len(doc.get("assets", {})) != 11:
        raise SealError(f"bundle seal asset count must be 11, got {doc.get('asset_count')}")
    recorded = doc.get("bundle_seal_sha256")
    if not recorded:
        raise SealError("bundle seal missing bundle_seal_sha256")
    if expected_seal_sha256 and recorded != expected_seal_sha256:
        raise SealError(f"bundle seal mismatch: expected {expected_seal_sha256}, got {recorded}")
    check_doc = dict(doc)
    check_doc.pop("bundle_seal_sha256", None)
    if sha256_bytes(canonical_json(check_doc)) != recorded:
        raise SealError("bundle seal digest tampered")
    actual = inspect_directory_files(bundle_dir, exclude_names={"release-bundle-seal.json"})
    if actual != doc.get("files"):
        raise SealError("bundle complete file inventory or digest mismatch")
    if sha256_file(bundle_dir / "apg-distribution-manifest.json") != doc.get("manifest_sha256"):
        raise SealError("bundle manifest digest mismatch")
    if sha256_file(bundle_dir / "SHA256SUMS") != doc.get("checksums_sha256"):
        raise SealError("bundle checksums digest mismatch")
    if set(doc.get("lane_seals", {})) != set(REQUIRED_LANES):
        raise SealError("bundle native lane inventory mismatch")
    for name, spec in doc["assets"].items():
        asset = bundle_dir / name
        if sha256_file(asset) != spec["sha256"] or asset.stat().st_size != spec["size_bytes"]:
            raise SealError(f"asset {name} digest or size mismatch")
    return doc


def build_consumer_receipt(
    lane: str, target: str, seal_hash: str, commit: str, tree: str, checks: dict[str, str], out: Path
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": CONSUMER_RECEIPT_SCHEMA, "lane": lane, "target": target,
        "bundle_seal_sha256": seal_hash, "source_commit": commit, "source_tree": tree,
        "status": "passed", "checks": checks,
        "node_provenance": {"version": "22.22.2", "provider": "pinned actions/setup-node",
                            "signed_source_verified": False, "checksum_source": "unsigned"},
    }
    payload["receipt_sha256"] = sha256_bytes(canonical_json(payload))
    dest = out if out.name.endswith(".json") else out / "consumer-receipt.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(canonical_json(payload))
    return payload


def verify_consumer_receipt(receipt_path: Path, expected_bundle_seal: str | None = None) -> dict[str, Any]:
    doc = load_canonical_json(receipt_path)
    if doc.get("schema_version") != CONSUMER_RECEIPT_SCHEMA or doc.get("status") != "passed":
        raise SealError("invalid consumer receipt schema or status")
    if expected_bundle_seal and doc.get("bundle_seal_sha256") != expected_bundle_seal:
        raise SealError("consumer receipt bundle seal mismatch")
    recorded = doc.get("receipt_sha256")
    check_doc = dict(doc)
    check_doc.pop("receipt_sha256", None)
    if not recorded or sha256_bytes(canonical_json(check_doc)) != recorded:
        raise SealError("consumer receipt digest tampered")
    lane = doc.get("lane")
    if lane not in CANONICAL_TARGETS or doc.get("target") != CANONICAL_TARGETS[lane]["target"]:
        raise SealError("consumer target/lane mismatch")
    if doc.get("checks") != dict.fromkeys(("wheel_install_smoke", "foreign_wheel_rejected", "npm_install_smoke", "bundle_seal_verified"), "passed"):
        raise SealError("consumer smoke evidence incomplete")
    return doc


def build_scan_receipt(
    seal_hash: str, assets: int, scans: int, status: str, scans_digest: str, out: Path, policy: str = "passed"
) -> dict[str, Any]:
    if assets != 11 or scans != 14:
        raise SealError(f"scan receipt requires 11 assets and 14 scans, got {assets} and {scans}")
    payload: dict[str, Any] = {
        "schema_version": SCAN_RECEIPT_SCHEMA, "bundle_seal_sha256": seal_hash,
        "asset_count": assets, "scan_count": scans, "status": status,
        "grype_policy": policy, "scans_digest": scans_digest,
    }
    payload["receipt_sha256"] = sha256_bytes(canonical_json(payload))
    dest = out if out.name.endswith(".json") else out / "scan-receipt.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(canonical_json(payload))
    return payload


def verify_scan_receipt(receipt_path: Path, expected_bundle_seal: str | None = None) -> dict[str, Any]:
    doc = load_canonical_json(receipt_path)
    if doc.get("schema_version") != SCAN_RECEIPT_SCHEMA or doc.get("status") != "passed":
        raise SealError("invalid scan receipt schema or status")
    if doc.get("asset_count") != 11 or doc.get("scan_count") != 14:
        raise SealError(f"scan receipt counts invalid: {doc.get('asset_count')}, {doc.get('scan_count')}")
    if expected_bundle_seal and doc.get("bundle_seal_sha256") != expected_bundle_seal:
        raise SealError("scan receipt bundle seal mismatch")
    recorded = doc.get("receipt_sha256")
    check_doc = dict(doc)
    check_doc.pop("receipt_sha256", None)
    if not recorded or sha256_bytes(canonical_json(check_doc)) != recorded:
        raise SealError("scan receipt digest tampered")
    if doc.get("grype_policy") != "passed":
        raise SealError("scan policy not passed")
    return doc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="native_seal", description="Native CI cryptographic sealing helper")
    sub = parser.add_subparsers(dest="command", required=True)
    v_lane = sub.add_parser("verify-lane-seal", help="Verify lane seal")
    v_lane.add_argument("--seal", type=Path, required=True)
    v_lane.add_argument("--lane", type=str)
    v_bundle = sub.add_parser("verify-bundle-seal", help="Verify bundle seal")
    v_bundle.add_argument("--bundle", type=Path, required=True)
    v_bundle.add_argument("--expected-seal", type=str)
    args = parser.parse_args(argv)
    try:
        if args.command == "verify-lane-seal":
            verify_lane_seal(args.seal, expected_lane=args.lane)
            print("lane seal verified successfully")
        elif args.command == "verify-bundle-seal":
            verify_bundle_seal(args.bundle, expected_seal_sha256=args.expected_seal)
            print("bundle seal verified successfully")
        return 0
    except SealError as err:
        print(f"native_seal error: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
