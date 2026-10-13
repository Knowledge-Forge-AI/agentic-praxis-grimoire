#!/usr/bin/env python3
"""Source-only assembly and scanner verification for APGR native release bundles.

``assemble`` consumes three sealed native lane artifacts and packages the eleven
distributables through the canonical prebuilt packagers.  Nothing here compiles:
the Go binaries are taken as bytes, validated against their retained native
metadata, and embedded by ``apg_python_prebuilt_publication``,
``apg_npm_distribution`` and ``apg_distribution_candidate``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

if str(Path(__file__).resolve().parents[2]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
if str(Path(__file__).resolve().parents[2] / "libexec") not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "libexec"))

import apg_distribution_candidate as candidate
import apg_go_buildinfo as buildinfo
import apg_npm_distribution as npm
import apg_python_prebuilt_publication as prebuilt

from tools.ci import native_artifacts as artifacts
from tools.ci.native_seal import (
    CANONICAL_TARGETS,
    REQUIRED_LANES,
    SealError,
    assert_direct_dir,
    assert_direct_file,
    build_bundle_seal,
    build_scan_receipt,
    check_containment,
    load_canonical_json,
    sha256_file,
    verify_bundle_seal,
    verify_lane_seal,
    write_github_output,
)

ROOT = Path(__file__).resolve().parents[2]

SBOM_POLICY = ROOT / "release/ci/sbom_policy.json"
SCAN_SCHEMA = "apg-sbom-scan-v1"
NIX_EVIDENCE_SCHEMA = "apgr.native-nix-evidence/v1"
BUNDLE_ARTIFACT_NAME = "native-release-candidate-bundle"
SEAL_NAME = "release-bundle-seal.json"
LANE_FILES = frozenset({"apgr", "apgr.binary-manifest.json", "go-version-m.txt", "nix-evidence.json", "nix-compiler-identity.txt", "go-tests.log"})
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
HEX_RE = re.compile(r"^[0-9a-f]{64}$")
ASSET_COUNT, SBOM_COUNT, GRYPE_COUNT = 11, 14, 14
BUNDLE_FILE_COUNT = ASSET_COUNT + 3 + 2  # plus three Go binary manifests, the distribution manifest and SHA256SUMS
KIND_COUNTS = {"go-binary": 3, "python-wheel": 3, "python-sdist": 1, "npm-launcher": 1, "npm-platform": 3}


class AssemblyError(ValueError):
    """Deliverable assembly or scan validation failure."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssemblyError(message)


def strict_json(text: str, label: str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            _require(key not in result, f"duplicate key in {label}: {key}")
            result[key] = value
        return result

    try:
        return json.loads(text, object_pairs_hook=pairs)
    except json.JSONDecodeError as error:
        raise AssemblyError(f"malformed {label}: {error}") from error


def identity_from_env() -> dict[str, str]:
    """Exact source and pull-request identity; every value is mandatory."""
    values = {
        "source_commit": os.environ.get("SOURCE_COMMIT", ""),
        "source_tree": os.environ.get("SOURCE_TREE", ""),
        "pr_head_sha": os.environ.get("PR_HEAD_SHA", ""),
        "pr_base_sha": os.environ.get("PR_BASE_SHA", ""),
    }
    for key, value in values.items():
        _require(bool(SHA_RE.match(value)), f"{key.upper()} must be a 40-character lowercase hex SHA")
    return values


def parse_lane_inputs(raw: str | None) -> dict[str, dict[str, str]]:
    """Exactly three lanes, each with exactly seal_sha256, artifact_id, artifact_digest."""
    _require(bool(raw), "missing NATIVE_INPUTS_JSON environment variable")
    spec = strict_json(raw or "", "NATIVE_INPUTS_JSON")
    _require(isinstance(spec, dict) and set(spec) == set(REQUIRED_LANES), "NATIVE_INPUTS_JSON must name exactly the three native lanes")
    for lane, entry in spec.items():
        _require(isinstance(entry, dict) and set(entry) == {"seal_sha256", "artifact_id", "artifact_digest"},
                 f"NATIVE_INPUTS_JSON[{lane}] must carry exactly seal_sha256, artifact_id, artifact_digest")
        _require(all(isinstance(v, str) for v in entry.values()), f"NATIVE_INPUTS_JSON[{lane}] values must be strings")
        _require(bool(HEX_RE.match(entry["seal_sha256"])), f"NATIVE_INPUTS_JSON[{lane}].seal_sha256 is malformed")
        _require(bool(artifacts.ID_RE.match(entry["artifact_id"])), f"NATIVE_INPUTS_JSON[{lane}].artifact_id is malformed")
        _require(bool(artifacts.DIGEST_RE.match(entry["artifact_digest"])), f"NATIVE_INPUTS_JSON[{lane}].artifact_digest is malformed")
    return spec


def _lane_files_dir(lane_root: Path, slug: str) -> Path:
    assert_direct_dir(lane_root, "downloaded lane artifact")
    direct, nested = lane_root / "lane-seal.json", lane_root / slug / "lane-seal.json"
    present = [seal.parent for seal in (direct, nested) if seal.exists() or seal.is_symlink()]
    _require(len(present) == 1, f"lane artifact {lane_root} must hold exactly one lane-seal.json (direct or under {slug}/)")
    if present[0] != lane_root:
        _require({entry.name for entry in lane_root.iterdir()} == {slug}, f"nested lane artifact {lane_root} holds unexpected entries")
    return present[0]


def _verify_lane_content(lane: str, ldir: Path, seal: Mapping[str, Any], identity: Mapping[str, str]) -> None:
    spec = CANONICAL_TARGETS[lane]
    _require(seal.get("target") == spec["target"] and seal.get("target_slug") == spec["slug"], f"lane {lane} seal names the wrong target")
    _require(seal.get("source_commit") == identity["source_commit"], f"lane {lane} source commit differs from SOURCE_COMMIT")
    _require(seal.get("source_tree") == identity["source_tree"], f"lane {lane} source tree differs from SOURCE_TREE")
    _require(set(seal.get("files", {})) == LANE_FILES, f"lane {lane} seal inventory is not exactly {sorted(LANE_FILES)}")
    nix = load_canonical_json(ldir / "nix-evidence.json")
    expected = {"schema_version": NIX_EVIDENCE_SCHEMA, "lane": lane, "target": spec["target"],
                "compiler_version": buildinfo.REQUIRED_GO_VERSION, "status": "passed", "native_execution": True}
    _require(all(nix.get(k) == v and type(nix.get(k)) is type(v) for k, v in expected.items()),
             f"lane {lane} Nix evidence does not prove native {buildinfo.REQUIRED_GO_VERSION} execution")
    for label in ("store_smoke", "profile_smoke"):
        _require(nix.get(label, {}).get("controller_generation", {}).get("reason") == "installed_immutable_runtime",
                 f"lane {lane} lacks installed Nix {label}")
    _require(nix.get("profile_removed") is True, f"lane {lane} disposable Nix profile was not removed")
    _require((ldir / "nix-compiler-identity.txt").read_text().startswith("go1.26.9\n"), f"lane {lane} lacks Nix compiler identity")
    try:
        recorded = (ldir / "go-version-m.txt").read_text(encoding="utf-8")
        buildinfo.validate(ldir / "apgr", spec["target"], recorded=recorded)
    except (OSError, UnicodeDecodeError, buildinfo.BuildInfoError) as error:
        raise AssemblyError(f"lane {lane} binary build info failed validation: {error}") from error


def _copy(source: Path, destination: Path, mode: int) -> None:
    assert_direct_file(source, "bundle input")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    destination.chmod(mode)


def _go_slug(lane: str) -> str:
    return CANONICAL_TARGETS[lane]["go_binary"].split("/")[1]


def _tree_digests(root: Path) -> dict[str, str]:
    """Relative path -> sha256 for every file; links and special files are refused."""
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not (path.is_dir() or path.is_file()):
            raise AssemblyError(f"link or special file forbidden in {root}: {path}")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = sha256_file(path)
    return result


def _bundle_files(seal: Mapping[str, Any]) -> list[str]:
    """Every file the scanner expects: sealed assets, Go binary manifests, manifest, checksums."""
    go_manifests = [f"go/{_go_slug(lane)}/apgr.binary-manifest.json" for lane in REQUIRED_LANES]
    return sorted(seal["assets"]) + go_manifests + [candidate.MANIFEST_NAME, candidate.CHECKSUM_NAME]


def _verify_bundle_extras(bundle_dir: Path, seal: Mapping[str, Any]) -> list[str]:
    """Bind the manifest, checksums and Go manifests, which the seal covers only by digest."""
    for name, key in ((candidate.MANIFEST_NAME, "manifest_sha256"), (candidate.CHECKSUM_NAME, "checksums_sha256")):
        _require(sha256_file(bundle_dir / name) == seal.get(key), f"{name} differs from the bundle seal")
    names = _bundle_files(seal)
    rows: dict[str, str] = {}
    for line in (bundle_dir / candidate.CHECKSUM_NAME).read_text(encoding="ascii").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (\S+)", line)
        _require(match is not None and match.group(2) not in rows, f"malformed or duplicate {candidate.CHECKSUM_NAME} row: {line!r}")
        rows[match.group(2)] = match.group(1)
    covered = set(names) - {candidate.CHECKSUM_NAME}
    _require(set(rows) == covered, f"{candidate.CHECKSUM_NAME} does not cover exactly the bundle files")
    for name in sorted(covered):
        _require(sha256_file(bundle_dir / name) == rows[name], f"{name} differs from {candidate.CHECKSUM_NAME}")
    return names


def _build_bundle(work: Path, lane_dirs: Mapping[str, Path], identity: Mapping[str, str],
                  lane_seals: Mapping[str, Any]) -> Path:
    go_root = work / "go"
    for lane, ldir in lane_dirs.items():
        _copy(ldir / "apgr", go_root / _go_slug(lane) / "apgr", 0o755)
        _copy(ldir / "apgr.binary-manifest.json", go_root / _go_slug(lane) / "apgr.binary-manifest.json", 0o644)
        _copy(ldir / "go-version-m.txt", go_root / _go_slug(lane) / "go-version-m.txt", 0o644)

    py_work, py_dir = work / "py-work", work / "python"
    py_work.mkdir(mode=0o700)
    result = prebuilt.build_prebuilt_bundle(ROOT, go_root, py_dir, py_work)
    _require(result.get("status") == "ok", "prebuilt Python packager did not report success")
    py_names = sorted(p.name for p in py_dir.iterdir() if p.name != "SHA256SUMS")
    _require(len(py_names) == 4 and sum(n.endswith(".whl") for n in py_names) == 3
             and sum(n.endswith(".tar.gz") for n in py_names) == 1, f"Python packager produced an unexpected set: {py_names}")

    npm_a, npm_b, npm_work = work / "npm-a", work / "npm-b", work / "npm-work"
    npm_work.mkdir(mode=0o700)
    for out in (npm_a, npm_b):
        npm.build_packages(ROOT, go_root, out, work_root=npm_work)
    _require(_tree_digests(npm_a) == _tree_digests(npm_b), "npm A/B builds are not byte-identical")
    npm_names = sorted(p.name for p in npm_a.iterdir())
    _require(len(npm_names) == 4 and all(n.endswith(".tgz") for n in npm_names), f"npm packager produced an unexpected set: {npm_names}")

    manifest = candidate.build(ROOT, go_root, py_dir, npm_a, work / "candidate")
    manifest_path = work / "candidate" / candidate.MANIFEST_NAME
    candidate.check(manifest_path, ROOT, go_root, py_dir, npm_a)
    _require(manifest.get("source_commit") == identity["source_commit"] and manifest.get("source_tree") == identity["source_tree"],
             "distribution manifest source identity differs from SOURCE_COMMIT/SOURCE_TREE")

    bundle = work / "bundle"
    for lane in lane_dirs:
        slug = _go_slug(lane)
        _copy(go_root / slug / "apgr", bundle / "go" / slug / "apgr", 0o755)
        _copy(go_root / slug / "apgr.binary-manifest.json", bundle / "go" / slug / "apgr.binary-manifest.json", 0o644)
    for name in py_names:
        _copy(py_dir / name, bundle / "python" / name, 0o644)
    for name in npm_names:
        _copy(npm_a / name, bundle / "npm" / name, 0o644)
    for name in (candidate.MANIFEST_NAME, candidate.CHECKSUM_NAME):
        _copy(work / "candidate" / name, bundle / name, 0o644)
    candidate.check(bundle / candidate.MANIFEST_NAME, ROOT, bundle / "go", bundle / "python", bundle / "npm")
    _require(len(_tree_digests(bundle)) == BUNDLE_FILE_COUNT, f"exported bundle is not exactly {BUNDLE_FILE_COUNT} files")
    build_bundle_seal(bundle, identity["source_commit"], identity["source_tree"], lane_seals)
    return bundle


def run_assemble(lanes_dir: Path, output_path: Path) -> dict[str, Any]:
    """Verify three native artifacts, package eleven distributables, seal the bundle."""
    check_containment(output_path, "assembly output")
    assert_direct_dir(lanes_dir, "lanes directory")
    _require(not (output_path.exists() or output_path.is_symlink()), f"assembly output must not already exist: {output_path}")
    assert_direct_dir(output_path.parent, "assembly output parent")
    identity = identity_from_env()
    inputs = parse_lane_inputs(os.environ.get("NATIVE_INPUTS_JSON"))
    ctx = artifacts.context_from_env()

    work = Path(tempfile.mkdtemp(prefix=".apgr-assemble-", dir=output_path.parent))
    try:
        lane_dirs: dict[str, Path] = {}
        lane_seals: dict[str, Any] = {}
        for lane in REQUIRED_LANES:
            slug = CANONICAL_TARGETS[lane]["slug"]
            lane_root = lanes_dir / lane
            assert_direct_dir(lane_root, f"downloaded artifact for {lane}")
            artifacts.verify_downloaded_artifact(
                ctx, inputs[lane]["artifact_id"], inputs[lane]["artifact_digest"], lane, lane_root, scratch=work)
            ldir = _lane_files_dir(lane_root, slug)
            seal = verify_lane_seal(ldir / "lane-seal.json", expected_lane=lane)
            _require(seal["seal_sha256"] == inputs[lane]["seal_sha256"], f"lane {lane} seal differs from NATIVE_INPUTS_JSON")
            _verify_lane_content(lane, ldir, seal, identity)
            lane_dirs[lane], lane_seals[lane] = ldir, seal
        bundle = _build_bundle(work, lane_dirs, identity, lane_seals)
        os.replace(bundle, output_path)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    seal = verify_bundle_seal(output_path)
    _verify_bundle_extras(output_path, seal)
    write_github_output("bundle_seal_sha256", seal["bundle_seal_sha256"])
    return seal


def parse_bundle_input() -> dict[str, str]:
    raw = os.environ.get("NATIVE_BUNDLE_JSON", "")
    _require(bool(raw), "missing NATIVE_BUNDLE_JSON environment variable")
    binding = strict_json(raw, "NATIVE_BUNDLE_JSON")
    _require(isinstance(binding, dict) and set(binding) == {"artifact_id", "artifact_digest", "seal_sha256"}
             and all(isinstance(v, str) for v in binding.values()), "malformed NATIVE_BUNDLE_JSON fields")
    for key, pattern in (("artifact_id", artifacts.ID_RE), ("artifact_digest", artifacts.DIGEST_RE), ("seal_sha256", HEX_RE)):
        _require(bool(pattern.fullmatch(binding[key])), f"NATIVE_BUNDLE_JSON {key} is malformed")
    return binding


def verify_expected_bundle(bundle_dir: Path) -> dict[str, Any]:
    """Bind the internal seal to the producer's expected identity without a token."""
    binding = parse_bundle_input()
    seal = verify_bundle_seal(bundle_dir, expected_seal_sha256=binding["seal_sha256"])
    identity = identity_from_env()
    _require(all(seal.get(key) == identity[key] for key in ("source_commit", "source_tree")),
             "bundle source commit/tree differs from the guarded source")
    _verify_bundle_extras(bundle_dir, seal)
    return seal


def verify_downloaded_bundle(bundle_dir: Path, scratch: Path) -> dict[str, Any]:
    """Verify the immutable archive in a dedicated token-bearing workflow step."""
    check_containment(scratch, "bundle verification scratch")
    binding = parse_bundle_input()
    artifacts.verify_downloaded_artifact(artifacts.context_from_env(), binding["artifact_id"],
                                        binding["artifact_digest"], BUNDLE_ARTIFACT_NAME, bundle_dir, scratch=scratch)
    return verify_expected_bundle(bundle_dir)


def export_scan_input(bundle_dir: Path, output_path: Path) -> list[str]:
    """Copy the sealed bundle without its seal: the scanner demands the exact file set."""
    check_containment(output_path, "scan input")
    assert_direct_dir(bundle_dir, "bundle directory")
    seal = verify_expected_bundle(bundle_dir)
    names = _verify_bundle_extras(bundle_dir, seal)
    _require(not (output_path.exists() or output_path.is_symlink()), f"scan input must not already exist: {output_path}")
    observed = _tree_digests(bundle_dir)
    _require(set(observed) == set(names) | {SEAL_NAME}, "sealed bundle holds files beyond its declared assets")
    for name in names:
        _copy(bundle_dir / name, output_path / name, 0o755 if name.endswith("/apgr") else 0o644)
    _require(_tree_digests(output_path) == {n: observed[n] for n in names}, "scan input differs from the sealed bundle")
    return names


def _scan_policy() -> dict[str, Any]:
    policy_doc = load_canonical_json(SBOM_POLICY)
    scan = policy_doc["scan"]
    scanner = scan["scanner"]
    requirements = scan.get("artifact_requirements")
    sdist = requirements.get("python-sdist") if isinstance(requirements, dict) else None
    sdist_req = sdist.get("required_types") if isinstance(sdist, dict) else None
    _require(isinstance(sdist_req, list) and all(isinstance(t, str) and t for t in sdist_req)
             and sdist_req == sorted(set(sdist_req)) and "python" in sdist_req, "sdist coverage policy is malformed")
    return {"syft": scanner["syft"]["version"], "grype": scanner["grype"]["version"],
            "max_age": scanner["database"]["max_age_hours"], "fail_on": scanner["grype"]["fail_on"],
            "sdist_required_types": sdist_req}


def _sdist_coverage(sbom: Mapping[str, Any], label: str, required: list[str], *, raw: bool) -> None:
    types = sbom.get("types")
    _require(isinstance(types, dict), f"{label} SBOM types inventory is missing or malformed")
    _require(all(isinstance(k, str) and k for k in types), f"{label} SBOM type key is malformed")
    _require(all(type(v) is int and v > 0 for v in types.values()), f"{label} SBOM type count must be positive integer")
    _require(sum(types.values()) == sbom["package_count"], f"{label} SBOM package_count inconsistent with types count")
    _require(sbom.get("required_types") == required, f"{label} SBOM required_types differs from policy")
    missing = sorted(set(required) - set(types))
    if raw:
        _require(sbom.get("missing_types") == missing, f"{label} SBOM missing_types is inconsistent with types")
        _require(sbom.get("coverage_status") == ("coverage-gap" if missing else "passed"),
                 f"{label} SBOM coverage_status is inconsistent")
    else:
        _require(sbom.get("coverage_status") == "passed", f"{label} SBOM coverage did not pass")
        _require(missing == [] and sbom.get("missing_types") == [], f"{label} SBOM has coverage gap")


def _evidence(record: Any, label: str, sink: list[tuple[str, str]], *, derived: bool = False,
              raw_sdist: bool = False, sdist_required: list[str] | None = None) -> None:
    _require(isinstance(record, dict), f"{label} is not an object")
    sbom, grype = record.get("sbom"), record.get("grype")
    _require(isinstance(sbom, dict) and isinstance(grype, dict), f"{label} lacks SBOM or Grype evidence")
    _require(sbom.get("syft_returncode") == 0 and type(sbom.get("syft_returncode")) is int, f"{label} Syft did not exit cleanly")
    pkg_count = sbom.get("package_count")
    _require(isinstance(pkg_count, int) and not isinstance(pkg_count, bool) and pkg_count > 0, f"{label} SBOM is empty")

    if raw_sdist or derived:
        _require(sdist_required is not None, "internal error: missing sdist_required policy")
        _sdist_coverage(sbom, label, sdist_required, raw=raw_sdist)
    else:
        _require(sbom.get("coverage_status") == "passed" and sbom.get("missing_types") == [], f"{label} SBOM coverage is incomplete")

    _require(grype.get("status") == "passed" and grype.get("returncode") == 0 and type(grype.get("returncode")) is int
             and grype.get("blocking_severities") == [], f"{label} Grype policy did not pass")
    _require(grype.get("input_sbom_sha256") == sbom.get("sha256"), f"{label} Grype input is not its SBOM")
    for part in (sbom, grype):
        _require(isinstance(part.get("path"), str) and HEX_RE.match(str(part.get("sha256"))), f"{label} evidence path/digest is malformed")
        sink.append((part["path"], part["sha256"]))
    if derived:
        for part in (sbom, grype):
            _require(HEX_RE.match(str(part.get("source_archive_sha256"))), f"{label} lacks its source archive digest")


def _check_artifact(rec: Any, target: str, asset: Mapping[str, Any], assets: Mapping[str, Any],
                    sink: list[tuple[str, str]], policy: Mapping[str, Any]) -> str:
    _require(isinstance(rec, dict), f"scan record for {target} is not an object")
    kind = rec.get("kind")
    expected = {"go": ("go-binary",), "python": ("python-wheel", "python-sdist"),
                "npm": ("npm-launcher", "npm-platform")}.get(target.split("/")[0], ())
    _require(kind in expected, f"scan record for {target} has unexpected kind {kind!r}")
    if kind in ("python-sdist", "python-wheel"):
        suffix = ".tar.gz" if kind == "python-sdist" else ".whl"
        _require(target.endswith(suffix), f"scan record for {target} has unexpected kind {kind!r}")
    rec_status = rec.get("status")
    _require(rec_status == "passed", f"scan record for {target} did not pass: {rec_status!r}")
    _require(rec.get("target_sha256") == asset["sha256"], f"scan record for {target} is not bound to the sealed asset digest")
    if kind in ("python-wheel", "npm-platform"):
        _evidence(rec, target, sink)
        platform = rec.get("target_platform")
        binary = assets.get(f"go/{str(platform).replace('/', '-')}/apgr")
        embedded = rec.get("embedded_binary")
        _require(binary is not None and isinstance(embedded, dict) and embedded.get("matches") is True
                 and embedded.get("sha256") == binary["sha256"], f"{target} does not embed the sealed {platform} binary")
    elif kind == "python-sdist":
        sdist_required = policy["sdist_required_types"]
        _evidence(rec, target, sink, raw_sdist=True, sdist_required=sdist_required)
        derived = rec.get("derived_install")
        _require(isinstance(derived, dict), "sdist lacks its derived-install scan view")
        _require(derived.get("source_archive_sha256") == asset["sha256"], "derived install is not bound to the sealed sdist")
        installation = derived.get("installation")
        _require(isinstance(installation, dict), "derived installation is malformed")
        _require(installation.get("archive_sha256") == asset["sha256"], "installation archive_sha256 is not bound to the sealed sdist")
        installer = installation.get("installer")
        _require(isinstance(installer, dict), "derived installer is malformed")
        _require(installer.get("status") == "passed" and installer.get("returncode") == 0 and type(installer.get("returncode")) is int,
                 "sdist derived installation did not pass")
        _evidence(derived, "sdist derived install", sink, derived=True, sdist_required=sdist_required)
        for part in ("sbom", "grype"):
            _require(derived[part].get("source_archive_sha256") == asset["sha256"], f"derived {part} is not bound to the sealed sdist")
        derived_sbom = derived["sbom"]
        _require("python" in derived_sbom.get("types", {}), "sdist derived install lacks python coverage")
        union = rec.get("coverage_union")
        _require(isinstance(union, dict) and union.get("status") == "passed", "sdist coverage union is incomplete")
        raw_types = set(rec["sbom"].get("types", {}).keys())
        derived_types = set(derived_sbom.get("types", {}).keys())
        recomputed_covered = sorted(raw_types | derived_types)
        recomputed_missing = sorted(set(sdist_required) - set(recomputed_covered))
        _require(recomputed_missing == [], "sdist coverage union has missing types")
        _require(union.get("missing_types") == [], "sdist coverage union missing_types must be empty")
        _require(union.get("required_types") == list(sdist_required), "sdist coverage union required_types mismatch")
        _require(union.get("covered_types") == recomputed_covered, "sdist coverage union covered_types mismatch")
        _require("python" in recomputed_covered, "sdist coverage union lacks python coverage")
    else:
        _evidence(rec, target, sink)
    return kind


def validate_scan_document(doc: Mapping[str, Any], assets: Mapping[str, Any]) -> list[tuple[str, str]]:
    """Enforce the apg-sbom-scan-v1 contract; returns (path, sha256) evidence to hash on disk."""
    policy = _scan_policy()
    _require(doc.get("schema") == SCAN_SCHEMA, f"unexpected scan results schema: {doc.get('schema')!r}")
    _require(doc.get("status") == "passed", f"scan results status is not passed: {doc.get('status')!r}")
    _require(len(assets) == ASSET_COUNT, f"scan validation needs exactly {ASSET_COUNT} sealed assets")
    summary = doc.get("summary")
    _require(isinstance(summary, dict), "scan results lack a summary")
    exact = {"artifact_count": ASSET_COUNT, "conditional_dependency_count": 1, "sbom_count": SBOM_COUNT,
             "conditional_sbom_count": 1, "grype_count": GRYPE_COUNT, "conditional_grype_count": 1,
             "coverage_gaps": [], "policy_findings": [], "tool_failures": [], "status": "passed"}
    for key, value in exact.items():
        _require(summary.get(key) == value and type(summary.get(key)) is type(value), f"scan summary {key} must be {value!r}, got {summary.get(key)!r}")
    severities = summary.get("severity_counts")
    _require(isinstance(severities, dict) and not severities.get("high") and not severities.get("critical"), "scan summary reports High/Critical findings")
    scan_policy = doc.get("policy")
    _require(isinstance(scan_policy, dict) and scan_policy.get("grype_fail_on") == policy["fail_on"]
             and scan_policy.get("custom_ignores") == [] and scan_policy.get("lower_severities_retained") is True
             and scan_policy.get("empty_or_unsupported_inventory_is_clean") is False and scan_policy.get("catalogers") == "all",
             "scan policy block is not the maintained strict policy")
    scanners = doc.get("scanner")
    for tool in ("syft", "grype"):
        entry = scanners.get(tool) if isinstance(scanners, dict) else None
        _require(isinstance(entry, dict) and entry.get("version") == policy[tool] and HEX_RE.match(str(entry.get("binary_sha256"))),
                 f"{tool} scanner identity is not the pinned version")
    db = doc.get("database")
    _require(isinstance(db, dict) and db.get("valid") is True and db.get("update_check") == "command-observed"
             and isinstance(db.get("update"), dict) and db["update"].get("status") == "passed"
             and HEX_RE.match(str(db.get("database_sha256"))), "Grype database update/validity evidence is missing")
    age = db.get("age_hours")
    _require(isinstance(age, (int, float)) and not isinstance(age, bool) and 0 <= age <= policy["max_age"]
             and db.get("max_age_hours") == policy["max_age"], "Grype database is stale or its age policy differs")

    sink: list[tuple[str, str]] = []
    source = doc.get("source")
    _require(isinstance(source, dict) and source.get("status") == "passed" and source.get("target") == ".", "source scan did not pass")
    _evidence(source, "source", sink)
    records = doc.get("artifacts")
    _require(isinstance(records, list) and len(records) == ASSET_COUNT, f"scan results must hold exactly {ASSET_COUNT} artifact records")
    by_target: dict[str, Any] = {}
    for rec in records:
        name = rec.get("target") if isinstance(rec, dict) else None
        _require(isinstance(name, str) and name not in by_target, f"duplicate or malformed artifact record: {name!r}")
        by_target[name] = rec
    _require(set(by_target) == set(assets), f"scan targets differ from sealed assets: {sorted(set(by_target) ^ set(assets))}")
    kinds: dict[str, int] = {}
    for target in sorted(by_target):
        kind = _check_artifact(by_target[target], target, assets[target], assets, sink, policy)
        kinds[kind] = kinds.get(kind, 0) + 1
    _require(kinds == KIND_COUNTS, f"scan artifact kinds differ from the canonical eleven: {kinds}")
    conditional = doc.get("conditional_dependency")
    _require(isinstance(conditional, dict) and conditional.get("kind") == "conditional-dependency"
             and conditional.get("status") == "passed", "conditional dependency scan did not pass")
    _evidence(conditional, "conditional dependency", sink)
    receipt = conditional.get("receipt")
    _require(isinstance(receipt, dict) and HEX_RE.match(str(receipt.get("sha256"))), "conditional dependency receipt is missing")
    sink.append((receipt["path"], receipt["sha256"]))
    view = conditional.get("view")
    _require(isinstance(view, dict) and view.get("target_python") == "3.10"
             and view.get("download", {}).get("status") == "passed" and view.get("installation", {}).get("status") == "passed",
             "conditional dependency view did not pass")
    _require(len(sink) == 2 * SBOM_COUNT + 1, f"scan evidence inventory has {len(sink)} entries, expected {2 * SBOM_COUNT + 1}")
    _require(len({path for path, _ in sink}) == len(sink), "scan evidence paths must be distinct")
    return sink


def _verify_evidence_files(scans_root: Path, evidence: list[tuple[str, str]]) -> None:
    for relative, digest in evidence:
        parts = Path(relative).parts
        _require(bool(parts) and not Path(relative).is_absolute() and all(p not in ("", ".", "..") for p in parts) and "\\" not in relative,
                 f"unsafe scan evidence path: {relative!r}")
        current = scans_root
        for part in parts[:-1]:
            current = assert_direct_dir(current / part, f"scan evidence directory {part}")
        _require(sha256_file(scans_root.joinpath(*parts)) == digest, f"scan evidence digest mismatch: {relative}")


def run_check_scan(bundle_dir: Path, scans_dir: Path, output_path: Path) -> dict[str, Any]:
    """Verify the sealed bundle's eleven assets and fourteen scan views, then receipt them."""
    check_containment(output_path, "check-scan output")
    _require(output_path.suffix != ".json", "check-scan output must be a directory")
    assert_direct_dir(bundle_dir, "bundle directory")
    assert_direct_dir(scans_dir, "scans directory")
    seal = verify_expected_bundle(bundle_dir)
    _verify_bundle_extras(bundle_dir, seal)
    scan_file = assert_direct_file(scans_dir / "scan-results.json", "scan results")
    scan_doc = load_canonical_json(scan_file)
    evidence = validate_scan_document(scan_doc, seal["assets"])
    _verify_evidence_files(scans_dir, evidence)
    verify_bundle_seal(bundle_dir, expected_seal_sha256=seal["bundle_seal_sha256"])
    for name in ("scan-results.json", "scan-receipt.json"):
        _require(not (output_path / name).exists(), f"{name} already exists in the output directory")
    output_path.mkdir(parents=True, exist_ok=True)
    _copy(scan_file, output_path / "scan-results.json", 0o644)
    return build_scan_receipt(seal["bundle_seal_sha256"], ASSET_COUNT, SBOM_COUNT, "passed",
                              sha256_file(output_path / "scan-results.json"), output_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="native_release_assembly", description="APGR native release packager")
    sub = parser.add_subparsers(dest="command", required=True)
    asm = sub.add_parser("assemble", help="Package eleven deliverables from three verified native lane artifacts")
    asm.add_argument("--lanes", type=Path, required=True, help="Directory holding one downloaded directory per lane")
    asm.add_argument("--output", type=Path, required=True, help="Bundle directory to create (must not exist)")
    verify = sub.add_parser("verify-bundle", help="Verify downloaded artifact identity and expected bundle seal")
    verify.add_argument("--bundle", type=Path, required=True)
    verify.add_argument("--scratch", type=Path, required=True)
    exp = sub.add_parser("export-scan-input", help="Copy a sealed bundle minus its seal for the scanner")
    exp.add_argument("--bundle", type=Path, required=True)
    exp.add_argument("--output", type=Path, required=True, help="Directory to create (must not exist)")
    scan = sub.add_parser("check-scan", help="Verify exact 11 assets and 14 SBOM/Grype views")
    scan.add_argument("--bundle", type=Path, required=True, help="Sealed bundle directory")
    scan.add_argument("--scans", type=Path, required=True, help="Directory containing scan-results.json and its evidence")
    scan.add_argument("--output", type=Path, required=True, help="Directory for scan-results.json and scan-receipt.json")
    args = parser.parse_args(argv)
    try:
        if args.command == "assemble":
            run_assemble(args.lanes, args.output)
        elif args.command == "verify-bundle":
            verify_downloaded_bundle(args.bundle, args.scratch)
        elif args.command == "export-scan-input":
            export_scan_input(args.bundle, args.output)
        else:
            run_check_scan(args.bundle, args.scans, args.output)
        return 0
    except (AssemblyError, SealError, artifacts.ArtifactError, candidate.DistributionCandidateError,
            npm.NpmDistributionError, prebuilt.publication.PublicationError) as error:
        print(f"native_release_assembly error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
