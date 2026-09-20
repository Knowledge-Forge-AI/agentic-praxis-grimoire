"""Deterministic bundle, asset mapping, archive validation, and attestation hashing for APGR release boundary."""

from __future__ import annotations

import hashlib
import io
import json
import re
import stat
import zipfile
from collections.abc import Mapping
from pathlib import PurePosixPath
from typing import Any

from tools.ci import native_seal


def strict_json(data: bytes | str, label: str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise BoundaryBundleError(f"duplicate key in {label}: {key}")
            result[key] = value
        return result
    try:
        return json.loads(data, object_pairs_hook=pairs)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise BoundaryBundleError(f"malformed {label}") from error

EXPECTED_VERSION = "0.13.0"
CANDIDATE_ATTESTATION_SCHEMA = "apgr.release-candidate-attestation/v1"
MERGED_ATTESTATION_SCHEMA = "apgr.release-merged-attestation/v1"
RELEASE_ATTESTATION_SCHEMA = "apgr.release-attestation/v1"
VERIFY_PUBLISHED_SCHEMA = "apgr.release-published-verification/v1"
GOVERNANCE_WAIVER_SCHEMA = "apgr.governance-waiver/v1"

HEX_RE = re.compile(r"^[0-9a-f]{64}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
ID_RE = re.compile(r"^[1-9][0-9]{0,18}$")

MANIFEST_NAME = "apg-distribution-manifest.json"
CHECKSUM_NAME = "SHA256SUMS"
REQUIRED_FLAT_ASSET_COUNT = 16
REQUIRED_CHECKSUM_ROW_COUNT = 15

GO_SLUGS = ("darwin-arm64", "linux-amd64", "linux-arm64")
PYTHON_WHEEL_TAGS = ("macosx_11_0_arm64", "manylinux_2_17_x86_64", "manylinux_2_17_aarch64")
NPM_SLUGS = ("darwin-arm64", "linux-x64", "linux-arm64")


class BoundaryBundleError(ValueError):
    """Bundle invariant, archive structure, or checksum mapping failure."""


def canonical_json(data: Any) -> bytes:
    """Format JSON deterministically with sorted keys and compact separators."""
    return (json.dumps(data, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    """Return lowercase hex SHA-256 digest of bytes."""
    return hashlib.sha256(data).hexdigest()


def compute_self_hash(doc: Mapping[str, Any], key: str = "self_sha256") -> str:
    """Compute deterministic SHA-256 over canonical JSON excluding self_sha256."""
    body = {k: v for k, v in doc.items() if k != key}
    return sha256_bytes(canonical_json(body))


def finalize_self_hash(doc: dict[str, Any], key: str = "self_sha256") -> dict[str, Any]:
    """Populate doc[key] with its self-hash."""
    doc.pop(key, None)
    doc[key] = compute_self_hash(doc, key=key)
    return doc


def validate_self_hash(doc: Mapping[str, Any], key: str = "self_sha256", label: str = "document") -> str:
    """Validate that doc[key] matches its computed self-hash."""
    recorded = doc.get(key)
    if not isinstance(recorded, str) or not HEX_RE.match(recorded):
        raise BoundaryBundleError(f"{label} lacks a valid {key}")
    expected = compute_self_hash(doc, key=key)
    if recorded != expected:
        raise BoundaryBundleError(f"{label} {key} mismatch: {recorded} != {expected} (tampered)")
    return recorded


def safe_member_path(name: str) -> str:
    """Ensure archive member path is POSIX relative and free of directory traversal."""
    parts = PurePosixPath(name).parts
    if (
        not name
        or name.startswith("/")
        or "\\" in name
        or "\x00" in name
        or (len(name) > 1 and name[0].isalpha() and name[1] == ":")
        or not parts
        or any(part in ("", ".", "..") for part in parts)
    ):
        raise BoundaryBundleError(f"unsafe archive member path: {name!r}")
    return PurePosixPath(*parts).as_posix()


def logical_path_to_flat_name(logical_path: str, version: str = EXPECTED_VERSION) -> str:
    """Map canonical bundle logical path to flat release asset name."""
    if logical_path.startswith("go/"):
        parts = logical_path.split("/")
        if len(parts) == 3 and parts[0] == "go":
            slug, filename = parts[1], parts[2]
            if filename == "apgr":
                return f"apgr-{slug}"
            if filename == "apgr.binary-manifest.json":
                return f"apgr-{slug}.binary-manifest.json"
        raise BoundaryBundleError(f"unrecognized Go logical path: {logical_path}")
    if logical_path.startswith("python/"):
        return logical_path.removeprefix("python/")
    if logical_path.startswith("npm/"):
        return logical_path.removeprefix("npm/")
    if logical_path in (MANIFEST_NAME, CHECKSUM_NAME):
        return logical_path
    raise BoundaryBundleError(f"unrecognized logical path: {logical_path}")


def canonical_logical_paths(version: str = EXPECTED_VERSION) -> list[str]:
    """Return the ordered list of 15 logical paths present in SHA256SUMS."""
    paths: list[str] = []
    for slug in GO_SLUGS:
        paths.append(f"go/{slug}/apgr")
        paths.append(f"go/{slug}/apgr.binary-manifest.json")
    for tag in PYTHON_WHEEL_TAGS:
        paths.append(f"python/agentic_praxis_grimoire-{version}-py3-none-{tag}.whl")
    paths.append(f"python/agentic_praxis_grimoire-{version}.tar.gz")
    paths.append(f"npm/knowledge-forge-ai-apgr-{version}.tgz")
    for slug in NPM_SLUGS:
        paths.append(f"npm/knowledge-forge-ai-apgr-{slug}-{version}.tgz")
    paths.append(MANIFEST_NAME)
    return sorted(paths)


def canonical_flat_assets(version: str = EXPECTED_VERSION) -> list[str]:
    """Return the ordered list of 16 flat asset names for GitHub Release."""
    flat = [logical_path_to_flat_name(p, version=version) for p in canonical_logical_paths(version=version)]
    flat.append(CHECKSUM_NAME)
    return sorted(flat)


def parse_sha256sums(content: str | bytes) -> dict[str, str]:
    """Parse SHA256SUMS rows of form '<digest>  <logical_path>'."""
    text = content.decode("ascii") if isinstance(content, bytes) else content
    rows: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        match = re.fullmatch(r"([0-9a-f]{64})\s{2}(\S+)", line)
        if not match:
            raise BoundaryBundleError(f"malformed SHA256SUMS row: {line!r}")
        digest, logical_path = match.group(1), match.group(2)
        if logical_path in rows:
            raise BoundaryBundleError(f"duplicate logical path in SHA256SUMS: {logical_path}")
        rows[logical_path] = digest
    return rows


def inspect_zip_bytes(
    archive_bytes: bytes,
    expected_digest: str | None = None,
    max_bytes: int = 1 << 30,
) -> dict[str, tuple[str, int, bytes]]:
    """Extract and validate zip archive bytes; returns member -> (sha256, size, bytes)."""
    if len(archive_bytes) > max_bytes:
        raise BoundaryBundleError(f"archive bytes exceed limit: {len(archive_bytes)} > {max_bytes}")
    if expected_digest is not None:
        actual_digest = f"sha256:{sha256_bytes(archive_bytes)}"
        if actual_digest != expected_digest:
            raise BoundaryBundleError(f"archive digest mismatch: {actual_digest} != {expected_digest}")
    try:
        zf = zipfile.ZipFile(io.BytesIO(archive_bytes))
    except (zipfile.BadZipFile, OSError) as err:
        raise BoundaryBundleError(f"malformed zip archive: {err}") from err

    members: dict[str, tuple[str, int, bytes]] = {}
    seen: set[str] = set()
    expanded = 0
    with zf:
        for info in zf.infolist():
            is_dir = info.filename.endswith("/")
            name = safe_member_path(info.filename.rstrip("/"))
            mode = (info.external_attr >> 16) & 0xFFFF
            kind = stat.S_IFMT(mode)
            if kind not in ((0, stat.S_IFDIR) if is_dir else (0, stat.S_IFREG)):
                raise BoundaryBundleError(f"archive contains non-regular member: {name}")
            if name in seen:
                raise BoundaryBundleError(f"archive contains duplicate member: {name}")
            seen.add(name)
            if is_dir:
                continue
            expanded += info.file_size
            if expanded > max_bytes:
                raise BoundaryBundleError("expanded archive exceeds size limit")
            content = zf.read(info)
            members[name] = (sha256_bytes(content), len(content), content)
    return members


def verify_bundle_contents(
    members: dict[str, tuple[str, int, bytes]],
    version: str = EXPECTED_VERSION,
    *, index: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Verify bundle archive contents against 16 flat asset mapping and 15 checksum rows."""
    seal_name = "release-bundle-seal.json"
    expected_paths = set(canonical_logical_paths(version=version)) | {CHECKSUM_NAME, seal_name}
    observed_paths = set(members.keys())
    if observed_paths != expected_paths:
        missing = sorted(expected_paths - observed_paths)
        extra = sorted(observed_paths - expected_paths)
        raise BoundaryBundleError(
            f"bundle archive file inventory mismatch (expected 16 files): missing={missing}, extra={extra}"
        )

    checksums_member = members[CHECKSUM_NAME]
    sums = parse_sha256sums(checksums_member[2])
    if len(sums) != REQUIRED_CHECKSUM_ROW_COUNT:
        raise BoundaryBundleError(
            f"SHA256SUMS must contain exactly {REQUIRED_CHECKSUM_ROW_COUNT} rows, got {len(sums)}"
        )

    if set(sums) != set(canonical_logical_paths(version=version)):
        raise BoundaryBundleError("SHA256SUMS does not cover the exact logical paths")
    seal = strict_json(members[seal_name][2], "bundle seal")
    if not isinstance(seal, dict) or seal.get("schema_version") != native_seal.RELEASE_BUNDLE_SEAL_SCHEMA:
        raise BoundaryBundleError("bundle seal schema mismatch")
    validate_self_hash(seal, key="bundle_seal_sha256", label="bundle seal")
    files = {p: {"sha256": h, "size_bytes": n} for p, (h, n, _) in members.items() if p != seal_name}
    asset_paths = set(files) - {MANIFEST_NAME, CHECKSUM_NAME} - {p for p in files if p.endswith(".binary-manifest.json")}
    if seal.get("files") != files or seal.get("assets") != {p: files[p] for p in asset_paths} or seal.get("asset_count") != 11:
        raise BoundaryBundleError("bundle sealed inventory or assets mismatch")
    if seal.get("manifest_sha256") != members[MANIFEST_NAME][0] or seal.get("checksums_sha256") != checksums_member[0]:
        raise BoundaryBundleError("bundle manifest/checksums seal mismatch")
    if index is not None:
        ref = index["bundle_artifact"]
        if any(ref.get(k) != v for k, v in {"seal_sha256": seal["bundle_seal_sha256"], "file_sha256": members[seal_name][0],
                "manifest_sha256": members[MANIFEST_NAME][0], "checksums_sha256": checksums_member[0]}.items()):
            raise BoundaryBundleError("bundle seal/manifest/checksums differ from RC index")
        if seal.get("source_commit") != index.get("source_commit") or seal.get("source_tree") != index.get("source_tree"):
            raise BoundaryBundleError("bundle seal source identity differs from RC index")
        if seal.get("lane_seals") != {lane: entry["seal_sha256"] for lane, entry in index["lane_artifacts"].items()}:
            raise BoundaryBundleError("bundle lane seals differ from RC index")
    mapping: dict[str, dict[str, str]] = {}
    for logical_path, expected_digest in sums.items():
        if logical_path not in members:
            raise BoundaryBundleError(f"SHA256SUMS references missing archive member: {logical_path}")
        actual_digest = members[logical_path][0]
        if actual_digest != expected_digest:
            raise BoundaryBundleError(
                f"digest mismatch for {logical_path}: {actual_digest} != {expected_digest}"
            )
        flat_name = logical_path_to_flat_name(logical_path, version=version)
        mapping[logical_path] = {
            "flat_name": flat_name,
            "sha256": actual_digest,
            "size_in_bytes": str(members[logical_path][1]),
        }

    manifest_bytes = members[MANIFEST_NAME][2]
    try:
        manifest_doc = strict_json(manifest_bytes, "distribution manifest")
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise BoundaryBundleError(f"distribution manifest is not valid JSON: {err}") from err

    if manifest_doc.get("schema_version") != "apg.distribution-manifest/v1":
        raise BoundaryBundleError(f"unexpected distribution manifest schema: {manifest_doc.get('schema_version')}")
    if manifest_doc.get("version") != version:
        raise BoundaryBundleError(f"distribution manifest version mismatch: {manifest_doc.get('version')} != {version}")

    if index is not None and (manifest_doc.get("source_commit") != index.get("source_commit") or manifest_doc.get("source_tree") != index.get("source_tree")):
        raise BoundaryBundleError("distribution manifest source identity differs from tested RC")
    mapping[CHECKSUM_NAME] = {"flat_name": CHECKSUM_NAME, "sha256": checksums_member[0], "size_in_bytes": str(checksums_member[1])}
    return {
        "asset_count": REQUIRED_FLAT_ASSET_COUNT,
        "checksum_row_count": REQUIRED_CHECKSUM_ROW_COUNT,
        "sha256sums_digest": checksums_member[0],
        "manifest_digest": members[MANIFEST_NAME][0],
        "mapping": mapping,
        "manifest": manifest_doc,
    }


def format_release_notes(
    candidate_doc: dict[str, Any],
    merged_doc: dict[str, Any],
    waiver_doc: dict[str, Any] | None = None,
) -> str:
    """Format canonical GitHub release notes with Candidate-Attestation-SHA256 header and embedded docs."""
    candidate_hash = compute_self_hash(candidate_doc)
    candidate_json_str = canonical_json(candidate_doc).decode("utf-8").strip()
    merged_json_str = canonical_json(merged_doc).decode("utf-8").strip()

    lines = [
        f"# Release v{candidate_doc.get('version', EXPECTED_VERSION)}",
        "",
        f"Candidate-Attestation-SHA256: {candidate_hash}",
        "",
        "<!-- BEGIN_CANDIDATE_ATTESTATION -->",
        candidate_json_str,
        "<!-- END_CANDIDATE_ATTESTATION -->",
        "",
        "<!-- BEGIN_MERGED_ATTESTATION -->",
        merged_json_str,
        "<!-- END_MERGED_ATTESTATION -->",
    ]
    if waiver_doc is not None:
        waiver_json_str = canonical_json(waiver_doc).decode("utf-8").strip()
        lines.extend([
            "",
            "<!-- BEGIN_GOVERNANCE_WAIVER -->",
            waiver_json_str,
            "<!-- END_GOVERNANCE_WAIVER -->",
        ])
    lines.append("")
    return "\n".join(lines)


def parse_release_notes(notes: str) -> dict[str, Any]:
    """Parse and validate embedded candidate, merged, and optional waiver documents from release notes."""
    matches = re.findall(r"^Candidate-Attestation-SHA256:[ \t]*([0-9a-f]{64})[ \t]*$", notes, re.MULTILINE)
    if len(matches) != 1:
        raise BoundaryBundleError("release notes lack a valid Candidate-Attestation-SHA256 line")
    recorded_candidate_hash = matches[0]

    def extract_section(begin_tag: str, end_tag: str, required: bool = True) -> str | None:
        b_count = notes.count(begin_tag)
        e_count = notes.count(end_tag)
        if b_count == 0 and e_count == 0:
            if required:
                raise BoundaryBundleError(f"release notes missing {begin_tag}")
            return None
        if b_count != 1 or e_count != 1:
            raise BoundaryBundleError(f"ambiguous or unbalanced tags: {begin_tag} ({b_count}) / {end_tag} ({e_count})")
        start = notes.find(begin_tag) + len(begin_tag)
        stop = notes.find(end_tag)
        if start > stop:
            raise BoundaryBundleError(f"malformed tag order for {begin_tag}")
        return notes[start:stop].strip()

    cand_str = extract_section("<!-- BEGIN_CANDIDATE_ATTESTATION -->", "<!-- END_CANDIDATE_ATTESTATION -->", True)
    merged_str = extract_section("<!-- BEGIN_MERGED_ATTESTATION -->", "<!-- END_MERGED_ATTESTATION -->", True)
    waiver_str = extract_section("<!-- BEGIN_GOVERNANCE_WAIVER -->", "<!-- END_GOVERNANCE_WAIVER -->", False)

    try:
        cand_doc = strict_json(cand_str or "", "candidate notes")
    except json.JSONDecodeError as err:
        raise BoundaryBundleError(f"malformed candidate attestation JSON in release notes: {err}") from err
    try:
        merged_doc = strict_json(merged_str or "", "merged notes")
    except json.JSONDecodeError as err:
        raise BoundaryBundleError(f"malformed merged attestation JSON in release notes: {err}") from err

    waiver_doc = None
    if waiver_str is not None:
        try:
            waiver_doc = strict_json(waiver_str, "waiver notes")
        except json.JSONDecodeError as err:
            raise BoundaryBundleError(f"malformed governance waiver JSON in release notes: {err}") from err

    if not isinstance(cand_doc, dict) or not isinstance(merged_doc, dict):
        raise BoundaryBundleError("embedded attestations must be JSON objects")

    cand_hash = validate_self_hash(cand_doc, label="embedded candidate attestation")
    if cand_hash != recorded_candidate_hash:
        raise BoundaryBundleError(
            f"candidate doc self-hash does not match header: {cand_hash} != {recorded_candidate_hash}"
        )
    if cand_doc.get("schema") != CANDIDATE_ATTESTATION_SCHEMA:
        raise BoundaryBundleError(f"unexpected candidate schema: {cand_doc.get('schema')}")

    merged_hash = validate_self_hash(merged_doc, label="embedded merged attestation")
    if merged_doc.get("schema") != MERGED_ATTESTATION_SCHEMA:
        raise BoundaryBundleError(f"unexpected merged schema: {merged_doc.get('schema')}")
    if merged_doc.get("candidate_attestation_sha256") != cand_hash:
        raise BoundaryBundleError(
            f"merged attestation candidate binding mismatch: {merged_doc.get('candidate_attestation_sha256')} != {cand_hash}"
        )

    if waiver_doc is not None:
        if not isinstance(waiver_doc, dict):
            raise BoundaryBundleError("embedded governance waiver must be a JSON object")
        waiver_hash = validate_self_hash(waiver_doc, label="embedded governance waiver")
        if waiver_doc.get("schema") != GOVERNANCE_WAIVER_SCHEMA:
            raise BoundaryBundleError(f"unexpected waiver schema: {waiver_doc.get('schema')}")
        cand_waiver_hash = (cand_doc.get("governance") or {}).get("waiver_sha256")
        if cand_waiver_hash != waiver_hash:
            raise BoundaryBundleError(
                f"waiver binding mismatch: {cand_waiver_hash} != {waiver_hash}"
            )

    return {
        "candidate_attestation": cand_doc,
        "candidate_attestation_sha256": cand_hash,
        "merged_attestation": merged_doc,
        "merged_attestation_sha256": merged_hash,
        "governance_waiver": waiver_doc,
    }
