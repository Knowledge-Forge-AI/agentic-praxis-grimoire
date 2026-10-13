"""Focused discovery and authority contract unit tests for tools/ci/native_gate.py."""

from __future__ import annotations

import copy
import hashlib
import io
import json
import shutil
import urllib.error
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from tools.ci import native_artifacts as na
from tools.ci import native_gate as gate
from tools.ci import native_release_assembly as assembly
from tools.ci.native_seal import (
    CANONICAL_TARGETS,
    CONSUMER_RECEIPT_SCHEMA,
    IDENTITY_SCHEMA,
    LANE_SEAL_SCHEMA,
    RC_INDEX_SCHEMA,
    RELEASE_BUNDLE_SEAL_SCHEMA,
    REQUIRED_LANES,
    SCAN_RECEIPT_SCHEMA,
    SealError,
    canonical_json,
    load_canonical_json,
    sha256_bytes,
)

COMMIT, TREE, HEAD, BASE = "a" * 40, "b" * 40, "c" * 40, "d" * 40
RUN_ID = "555"
WORKFLOW_SHA = "e" * 64
LANE_IDS = {"native-darwin-arm64": "101", "native-linux-x64": "102", "native-linux-arm64": "103"}
BUNDLE_ID = "104"
WHEELS = (
    "pkg-0.13.0-py3-none-macosx_11_0_arm64.whl",
    "pkg-0.13.0-py3-none-manylinux_2_17_x86_64.whl",
    "pkg-0.13.0-py3-none-manylinux_2_17_aarch64.whl",
)
NPMS = (
    "scope-apgr-0.13.0.tgz",
    "scope-apgr-darwin-arm64-0.13.0.tgz",
    "scope-apgr-linux-x64-0.13.0.tgz",
    "scope-apgr-linux-arm64-0.13.0.tgz",
)
CONSUMER_JOBS = {lane: f"native-consumer-{lane.removeprefix('native-')}" for lane in REQUIRED_LANES}


class FakeGitHub:
    def __init__(self) -> None:
        self.routes: dict[str, bytes] = {}
        self.calls: list[str] = []

    def __call__(self, request: Any) -> io.BytesIO:
        self.calls.append(request.full_url)
        if request.full_url not in self.routes:
            raise urllib.error.HTTPError(request.full_url, 404, "Not Found", {}, None)
        return io.BytesIO(self.routes[request.full_url])


def hex_of(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def finalize(doc: dict[str, Any], key: str) -> dict[str, Any]:
    doc.pop(key, None)
    doc[key] = sha256_bytes(canonical_json(doc))
    return doc


def artifact_meta(artifact_id: str, artifact_name: str, **override: Any) -> dict[str, Any]:
    return {
        "id": int(artifact_id), "name": artifact_name, "size_in_bytes": 10, "expired": False, "expires_at": "2099-01-01T00:00:00Z",
        "digest": "sha256:" + hex_of(artifact_name),
        "workflow_run": {"id": int(RUN_ID), "repository_id": na.EXPECTED_REPO_ID, "head_repository_id": na.EXPECTED_REPO_ID},
        **override,
    }


def serve(gh: FakeGitHub, artifact_id: str, artifact_name: str, **override: Any) -> None:
    url = f"{na.API_ROOT}/repos/{na.EXPECTED_REPO}/actions/artifacts/{artifact_id}"
    gh.routes[url] = json.dumps(artifact_meta(artifact_id, artifact_name, **override)).encode()


def scan_doc(assets: dict[str, Any]) -> dict[str, Any]:
    policy = assembly._scan_policy()
    parts = {
        "sbom": {"path": "p/sbom", "sha256": hex_of("sbom"), "package_count": 3, "missing_types": [], "coverage_status": "passed", "syft_returncode": 0},
        "grype": {"path": "p/grype", "sha256": hex_of("grype"), "input_sbom_sha256": hex_of("sbom"), "blocking_severities": [], "returncode": 0, "status": "passed"},
    }
    specs = list(CANONICAL_TARGETS.values())
    records = []
    for name, asset in sorted(assets.items()):
        if name.startswith("go/"):
            kind, platform = "go-binary", next(s["target"] for s in specs if s["go_binary"] == name)
        elif name.endswith(".whl"):
            kind, platform = "python-wheel", next(s["target"] for s in specs if s["python_tag"] in name)
        elif name.endswith(".tar.gz"):
            kind, platform = "python-sdist", None
        else:
            match = [s["target"] for s in specs if s["npm_slug"] in name]
            kind, platform = ("npm-platform", match[0]) if match else ("npm-launcher", None)
        record: dict[str, Any] = {"kind": kind, "target": name, "target_sha256": asset["sha256"], "target_platform": platform, "status": "passed", **copy.deepcopy(parts)}
        for key in ("sbom", "grype"):
            record[key]["path"] = f"artifacts/{name}/{key}.json"
        if kind in ("python-wheel", "npm-platform"):
            record["embedded_binary"] = {"sha256": assets[f"go/{platform.replace('/', '-')}/apgr"]["sha256"], "matches": True}
        if kind == "python-sdist":
            record["sbom"].update({"package_count": 1, "types": {"go-module": 1}, "required_types": ["python"],
                                   "missing_types": ["python"], "coverage_status": "coverage-gap"})
            derived = copy.deepcopy(parts)
            for part in derived.values():
                part["source_archive_sha256"] = asset["sha256"]
                path = Path(part["path"])
                part["path"] = str(Path("artifacts/python-sdist/derived-install") / path.name)
            derived["sbom"].update({"package_count": 3, "types": {"go-module": 2, "python": 1}, "required_types": ["python"],
                                    "missing_types": [], "coverage_status": "passed"})
            record["derived_install"] = {"installation": {"installer": {"status": "passed", "returncode": 0}, "archive_sha256": asset["sha256"]},
                                         "source_archive_sha256": asset["sha256"], **derived}
            record["coverage_union"] = {"status": "passed", "missing_types": [], "covered_types": ["go-module", "python"], "required_types": ["python"]}
        records.append(record)
    conditional = copy.deepcopy(parts)
    for key, part in conditional.items():
        part["path"] = f"conditional-runtime/{key}.json"
    return {
        "schema": "apg-sbom-scan-v1", "status": "passed",
        "source": {"target": ".", "status": "passed", **copy.deepcopy(parts)},
        "artifacts": records,
        "conditional_dependency": {"kind": "conditional-dependency", "status": "passed", **conditional,
                                   "view": {"target_python": "3.10", "download": {"status": "passed"}, "installation": {"status": "passed"}},
                                   "receipt": {"path": "r", "sha256": hex_of("receipt")}},
        "scanner": {"syft": {"version": policy["syft"], "binary_sha256": hex_of("s")}, "grype": {"version": policy["grype"], "binary_sha256": hex_of("g")}},
        "database": {"valid": True, "update_check": "command-observed", "update": {"status": "passed"}, "database_sha256": hex_of("db"),
                     "age_hours": 1.0, "max_age_hours": policy["max_age"]},
        "policy": {"grype_fail_on": "high", "custom_ignores": [], "catalogers": "all", "lower_severities_retained": True,
                   "empty_or_unsupported_inventory_is_clean": False},
        "summary": {"artifact_count": 11, "conditional_dependency_count": 1, "sbom_count": 14, "conditional_sbom_count": 1, "grype_count": 14,
                    "conditional_grype_count": 1, "coverage_gaps": [], "policy_findings": [], "tool_failures": [], "severity_counts": {}, "status": "passed"},
    }


def build_discovery_evidence(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    evidence = tmp_path / "evidence"
    paths: dict[str, Path] = {}
    docs: dict[str, dict[str, Any]] = {}
    sealed: dict[str, str] = {}

    def emit(key: str, relative: str, doc: dict[str, Any], seal_key: str | None, pretty: bool = False) -> None:
        if seal_key:
            finalize(doc, seal_key)
            sealed[key] = doc[seal_key]
        path = evidence / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((json.dumps(doc, indent=2, sort_keys=True) + "\n").encode() if pretty else canonical_json(doc))
        paths[key], docs[key] = path, doc

    # 1. Native guard receipt
    guard_dir = evidence / "native-guard-receipt"
    guard_dir.mkdir(parents=True, exist_ok=True)
    guard_doc = {"schema_version": IDENTITY_SCHEMA, "source_commit": COMMIT, "source_tree": TREE,
                 "repository": na.EXPECTED_REPO, "repository_id": na.EXPECTED_REPO_ID,
                 "pr_head_sha": HEAD, "pr_base_sha": BASE, "status": "passed"}
    emit("guard", "native-guard-receipt/identity.json", guard_doc, None)
    (guard_dir / "native-guard-receipt.json").write_text(
        json.dumps({"schema": "apg-matrix-receipt-v1", "job": "native-guard", "status": "success"}) + "\n")

    # 2. Lanes and receipts
    lane_ids: dict[str, str] = {}
    for lane in REQUIRED_LANES:
        spec = CANONICAL_TARGETS[lane]
        doc = {"schema_version": LANE_SEAL_SCHEMA, "lane": lane, "target": spec["target"], "target_slug": spec["slug"], "source_commit": COMMIT,
               "source_tree": TREE, "files": {n: {"sha256": hex_of(n), "size_bytes": 1} for n in sorted(assembly.LANE_FILES)}}
        emit(f"lane:{lane}", f"{lane}-receipt/lane-seal.json", doc, "seal_sha256")
        lane_ids[lane] = sealed[f"lane:{lane}"]
        (evidence / f"{lane}-receipt" / f"{lane}-receipt.json").write_text(
            json.dumps({"schema": "apg-matrix-receipt-v1", "job": lane, "status": "success"}) + "\n")

        lane_out = evidence / lane / spec["slug"]
        lane_out.mkdir(parents=True, exist_ok=True)
        (lane_out / "lane-seal.json").write_bytes(paths[f"lane:{lane}"].read_bytes())
        for name in assembly.LANE_FILES:
            (lane_out / name).write_bytes(f"fixture {lane} {name}\n".encode())

    # 3. Bundle and assemble receipt
    assets = {spec["go_binary"]: {"sha256": hex_of(spec["go_binary"]), "size_bytes": 5} for spec in CANONICAL_TARGETS.values()}
    assets.update({f"python/{n}": {"sha256": hex_of(n), "size_bytes": 5} for n in (*WHEELS, "pkg-0.13.0.tar.gz")})
    assets.update({f"npm/{n}": {"sha256": hex_of(n), "size_bytes": 5} for n in NPMS})
    bundle = {"schema_version": RELEASE_BUNDLE_SEAL_SCHEMA, "source_commit": COMMIT, "source_tree": TREE, "asset_count": 11, "assets": assets,
              "manifest_sha256": hex_of("manifest"), "checksums_sha256": hex_of("sums"), "lane_seals": dict(lane_ids)}
    emit("bundle", "native-assemble-receipt/release-bundle-seal.json", bundle, "bundle_seal_sha256")
    bundle_seal = sealed["bundle"]
    emit("public-projection", "native-assemble-receipt/public-projection-manifest.json",
         {"schema_version": 1, "canonical_public_identity": na.EXPECTED_REPO, "excluded_prefix": "private/",
          "entries": [{"path": ".github/workflows/native-qualification.yml", "mode": "100644", "type": "file",
                       "sha256": WORKFLOW_SHA}]}, None)
    (evidence / "native-assemble-receipt" / "native-assemble-receipt.json").write_text(
        json.dumps({"schema": "apg-matrix-receipt-v1", "job": "native-assemble", "status": "success"}) + "\n")

    bundle_dir = evidence / assembly.BUNDLE_ARTIFACT_NAME
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / "release-bundle-seal.json").write_bytes(paths["bundle"].read_bytes())
    for asset_name in bundle["assets"]:
        asset_path = bundle_dir / asset_name
        asset_path.parent.mkdir(parents=True, exist_ok=True)
        asset_path.write_bytes(f"asset {asset_name}\n".encode())
    for lane in REQUIRED_LANES:
        manifest_path = bundle_dir / f"go/{assembly._go_slug(lane)}/apgr.binary-manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_bytes(b"{}\n")
    (bundle_dir / "apg-distribution-manifest.json").write_bytes(b"manifest\n")
    (bundle_dir / "SHA256SUMS").write_bytes(b"sums\n")

    # 4. Consumer receipts
    for lane in REQUIRED_LANES:
        job = CONSUMER_JOBS[lane]
        doc = {"schema_version": CONSUMER_RECEIPT_SCHEMA, "lane": lane, "target": CANONICAL_TARGETS[lane]["target"], "bundle_seal_sha256": bundle_seal,
               "source_commit": COMMIT, "source_tree": TREE, "status": "passed",
               "checks": {"wheel_install_smoke": "passed", "foreign_wheel_rejected": "passed", "npm_install_smoke": "passed", "bundle_seal_verified": "passed"}}
        emit(f"consumer:{lane}", f"{job}-receipt/consumer-receipt.json", doc, "receipt_sha256")
        (evidence / f"{job}-receipt" / f"{job}-receipt.json").write_text(
            json.dumps({"schema": "apg-matrix-receipt-v1", "job": job, "status": "success"}) + "\n")

    # 5. Scan results, scan receipt and scan evidence
    emit("scan-results", "native-release-scans-receipt/scan-results.json", scan_doc(assets), None, pretty=True)
    receipt = {"schema_version": SCAN_RECEIPT_SCHEMA, "bundle_seal_sha256": bundle_seal, "asset_count": 11, "scan_count": 14, "status": "passed",
               "grype_policy": "passed", "scans_digest": hashlib.sha256(paths["scan-results"].read_bytes()).hexdigest()}
    emit("scan-receipt", "native-release-scans-receipt/scan-receipt.json", receipt, "receipt_sha256")
    (evidence / "native-release-scans-receipt" / "native-release-scans-receipt.json").write_text(
        json.dumps({"schema": "apg-matrix-receipt-v1", "job": "native-release-scans", "status": "success"}) + "\n")

    scan_dir = evidence / "native-scan-evidence"
    scan_dir.mkdir(parents=True, exist_ok=True)
    (scan_dir / "scan-results.json").write_bytes(paths["scan-results"].read_bytes())
    sample_path = scan_dir / "extracted" / "python-sdist" / "agentic_praxis_grimoire-0.13.0" / "hotspot" / "testdata" / "classification" / "sample.json"
    sample_path.parent.mkdir(parents=True, exist_ok=True)
    sample_path.write_bytes((Path(__file__).resolve().parents[7] / 'hotspot/testdata/classification/sample.json').read_bytes())

    # 6. Matrix aggregate
    def digest(key: str) -> str:
        return hashlib.sha256(paths[key].read_bytes()).hexdigest()

    bound = {lane: {"lane-seal.json": digest(f"lane:{lane}")} for lane in REQUIRED_LANES}
    bound["native-assemble"] = {"release-bundle-seal.json": digest("bundle"),
                                "public-projection-manifest.json": digest("public-projection")}
    bound.update({CONSUMER_JOBS[lane]: {"consumer-receipt.json": digest(f"consumer:{lane}")} for lane in REQUIRED_LANES})
    bound["native-release-scans"] = {"scan-results.json": digest("scan-results"),
                                    "scan-receipt.json": digest("scan-receipt")}
    bound["native-guard"] = {"identity.json": digest("guard")}
    members = {job: {"schema": "apg-matrix-receipt-v1", "job": job, "workflow": "native-qualification", "status": "success", "sha": COMMIT,
                     "pr_head_sha": HEAD, "pr_base_sha": BASE, "workflow_sha256": WORKFLOW_SHA, "artifacts": bound.get(job, {})}
               for job in sorted(gate.MATRIX_JOBS)}
    aggregate = {"schema": gate.AGGREGATE_SCHEMA, "success": True, "required_members_count": 9, "verified_members_count": 9, "errors": [],
                 "members": members, "member_receipt_status": {job: "success" for job in sorted(members)}}
    emit("matrix", "matrix-aggregate.json", aggregate, None, pretty=True)

    inputs = {lane: {"seal_sha256": lane_ids[lane], "artifact_id": LANE_IDS[lane], "artifact_digest": "sha256:" + hex_of(lane)} for lane in REQUIRED_LANES}
    bundle_ref = {"artifact_id": BUNDLE_ID, "artifact_digest": "sha256:" + hex_of(assembly.BUNDLE_ARTIFACT_NAME), "seal_sha256": bundle_seal}
    for lane in REQUIRED_LANES:
        serve(gh, LANE_IDS[lane], lane)
    serve(gh, BUNDLE_ID, assembly.BUNDLE_ARTIFACT_NAME)
    monkeypatch.setenv("NATIVE_INPUTS_JSON", json.dumps(inputs))
    monkeypatch.setenv("NATIVE_BUNDLE_JSON", json.dumps(bundle_ref))
    return SimpleNamespace(evidence=evidence, paths=paths, docs=docs, inputs=inputs, bundle_ref=bundle_ref, out=tmp_path / "gate-out", tmp=tmp_path)


@pytest.fixture(autouse=True)
def hermetic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gate, "_verify_inputs", lambda *args: None)
    for var in ("GITHUB_WORKSPACE", "GITHUB_OUTPUT", "APGR_ALLOW_WORKSPACE_OUTPUT", "GH_TOKEN"):
        monkeypatch.delenv(var, raising=False)
    for key, value in (("SOURCE_COMMIT", COMMIT), ("SOURCE_TREE", TREE), ("PR_HEAD_SHA", HEAD), ("PR_BASE_SHA", BASE),
                       ("GITHUB_TOKEN", "read-token"), ("GITHUB_REPOSITORY", na.EXPECTED_REPO), ("GITHUB_RUN_ID", RUN_ID),
                       ("MATRIX_NEEDS_RESULTS", json.dumps({job: "success" for job in sorted(gate.MATRIX_JOBS)}))):
        monkeypatch.setenv(key, value)


@pytest.fixture()
def gh(monkeypatch: pytest.MonkeyPatch) -> FakeGitHub:
    fake = FakeGitHub()
    monkeypatch.setattr(na, "_open", fake)
    return fake


def fails(world: SimpleNamespace, message: str, error: type[Exception] = gate.GateError) -> None:
    with pytest.raises(error, match=message):
        gate.run_gate(world.evidence, world.out)
    assert not world.out.exists() or not any(world.out.iterdir())


# --------------------------------------------------------------------------- full success


def test_discovery_full_run_gate_success(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
    world = build_discovery_evidence(tmp_path, gh, monkeypatch)
    sample = world.evidence / "native-scan-evidence/extracted/python-sdist/agentic_praxis_grimoire-0.13.0/hotspot/testdata/classification/sample.json"
    assert sample.read_bytes() == (Path(__file__).resolve().parents[7] / "hotspot/testdata/classification/sample.json").read_bytes()
    with pytest.raises(SealError, match="duplicate key"):
        load_canonical_json(sample)
    found = gate._discover(world.evidence)
    assert set(found) == {"matrix", "guard", "bundle", "scan-results", "scan-receipt", "public-projection",
                          *(f"lane:{lane}" for lane in REQUIRED_LANES), *(f"consumer:{lane}" for lane in REQUIRED_LANES)}
    index = gate.run_gate(world.evidence, world.out)
    assert index["schema"] == RC_INDEX_SCHEMA
    assert index["status"] == "passed"
    assert len(index["members"]) == 9
    assert len(index["lane_artifacts"]) == 3
    assert index["bundle_artifact"]["asset_count"] == 11
    assert index["bundle_artifact"]["scans"]["scan_count"] == 14
    assert (world.out / "native-rc-index.json").is_file()


# --------------------------------------------------------------------------- duplicate / recognized JSON


def test_discovery_rejects_extra_file_in_receipt_dir(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
    world = build_discovery_evidence(tmp_path, gh, monkeypatch)
    extra = world.evidence / "native-guard-receipt" / "extra.json"
    extra.write_text('{"extra": true}\n')
    fails(world, "duplicate/malformed recognized JSON or unexpected entry in native-guard-receipt")


def test_discovery_ignores_duplicate_recognized_json_under_extracted_tree(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
    world = build_discovery_evidence(tmp_path, gh, monkeypatch)
    extracted = world.evidence / "native-scan-evidence" / "extracted" / "pkg"
    extracted.mkdir(parents=True, exist_ok=True)
    # Recognized file names placed in extracted sdist must be completely ignored
    (extracted / "lane-seal.json").write_text('{"schema_version": "apgr.native-lane-seal/v1", "duplicate": 1, "duplicate": 2}\n')
    (extracted / "release-bundle-seal.json").write_text('{broken json\n')
    (extracted / "consumer-receipt.json").write_text('["not an object"]\n')
    (extracted / "scan-results.json").write_text('{"schema": "apg-sbom-scan-v1"}\n')
    # Run gate must succeed because extracted tree is not parsed as authority
    index = gate.run_gate(world.evidence, world.out)
    assert index["status"] == "passed"


def test_discovery_extracted_tree_does_not_permit_fallback_authority(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
    world = build_discovery_evidence(tmp_path, gh, monkeypatch)
    # Remove legitimate scan-results from native-scan-evidence
    (world.evidence / "native-scan-evidence" / "scan-results.json").unlink()
    # Plant a recognized scan-results.json inside extracted sdist
    planted = world.evidence / "native-scan-evidence" / "extracted" / "scan-results.json"
    planted.parent.mkdir(parents=True, exist_ok=True)
    planted.write_bytes(world.paths["scan-results"].read_bytes())
    # Gate must refuse to use planted file as fallback authority
    fails(world, "missing scan-results.json in native-scan-evidence")


# --------------------------------------------------------------------------- malformed recognized JSON


@pytest.mark.parametrize(
    "corrupt_key",
    ["lane:native-darwin-arm64", "bundle", "public-projection", "consumer:native-darwin-arm64", "scan-results", "scan-receipt", "matrix"],
)
def test_discovery_malformed_recognized_json_fails_canonical_load(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch, corrupt_key: str) -> None:
    world = build_discovery_evidence(tmp_path, gh, monkeypatch)
    target = world.paths[corrupt_key]
    # Update proof copy as well if applicable so proof equality passes and json parsing fails
    proof: Path | None = None
    if corrupt_key.startswith("lane:"):
        lane = corrupt_key.removeprefix("lane:")
        proof = world.evidence / lane / CANONICAL_TARGETS[lane]["slug"] / "lane-seal.json"
    elif corrupt_key == "bundle":
        proof = world.evidence / assembly.BUNDLE_ARTIFACT_NAME / "release-bundle-seal.json"
    elif corrupt_key == "scan-results":
        proof = world.evidence / "native-scan-evidence" / "scan-results.json"

    target.write_text("{broken json\n")
    if proof:
        proof.write_text("{broken json\n")
    fails(world, "failed to read JSON", SealError)


# --------------------------------------------------------------------------- missing authority


@pytest.mark.parametrize("missing_job", sorted(gate.MATRIX_JOBS))
def test_discovery_missing_receipt_directory_fails(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch, missing_job: str) -> None:
    world = build_discovery_evidence(tmp_path, gh, monkeypatch)
    receipt_dir = world.evidence / f"{missing_job}-receipt"
    for item in receipt_dir.iterdir():
        item.unlink()
    receipt_dir.rmdir()
    fails(world, "missing authority directory")


@pytest.mark.parametrize("missing_lane", sorted(REQUIRED_LANES))
def test_discovery_missing_lane_directory_fails(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch, missing_lane: str) -> None:
    world = build_discovery_evidence(tmp_path, gh, monkeypatch)
    lane_dir = world.evidence / missing_lane
    shutil.rmtree(lane_dir)
    fails(world, "missing authority directory")


def test_discovery_missing_bundle_directory_fails(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
    world = build_discovery_evidence(tmp_path, gh, monkeypatch)
    bundle_dir = world.evidence / assembly.BUNDLE_ARTIFACT_NAME
    shutil.rmtree(bundle_dir)
    fails(world, "missing authority directory")


# --------------------------------------------------------------------------- forged proof copy


def test_discovery_forged_lane_seal_copy_fails(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
    world = build_discovery_evidence(tmp_path, gh, monkeypatch)
    proof = world.evidence / "native-darwin-arm64" / "darwin-arm64" / "lane-seal.json"
    proof.write_bytes(b'{"forged": true}\n')
    fails(world, "seal proof copy differs.*forged copy")


def test_discovery_forged_bundle_seal_copy_fails(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
    world = build_discovery_evidence(tmp_path, gh, monkeypatch)
    proof = world.evidence / assembly.BUNDLE_ARTIFACT_NAME / "release-bundle-seal.json"
    proof.write_bytes(b'{"forged": true}\n')
    fails(world, "bundle seal proof copy differs.*forged copy")


def test_discovery_forged_scan_results_copy_fails(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
    world = build_discovery_evidence(tmp_path, gh, monkeypatch)
    proof = world.evidence / "native-scan-evidence" / "scan-results.json"
    proof.write_bytes(b'{"forged": true}\n')
    fails(world, "scan results proof copy differs.*forged copy")


# --------------------------------------------------------------------------- wrong root


def test_discovery_wrong_root_stray_file_fails(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
    world = build_discovery_evidence(tmp_path, gh, monkeypatch)
    (world.evidence / "stray.txt").write_text("unauthorized file\n")
    fails(world, "wrong-root:.*stray.txt")


def test_discovery_wrong_root_extra_directory_fails(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
    world = build_discovery_evidence(tmp_path, gh, monkeypatch)
    (world.evidence / "unexpected-dir").mkdir()
    fails(world, "wrong-root:.*unexpected-dir")


# --------------------------------------------------------------------------- symlinks at all depths


def test_discovery_symlink_at_depth_0_fails(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
    world = build_discovery_evidence(tmp_path, gh, monkeypatch)
    alias = tmp_path / "evidence-alias"
    alias.symlink_to(world.evidence)
    world.evidence = alias
    fails(world, "symlink", SealError)


def test_discovery_symlink_at_depth_1_fails(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
    world = build_discovery_evidence(tmp_path, gh, monkeypatch)
    (world.evidence / "link.txt").symlink_to(world.paths["bundle"])
    fails(world, "symlink forbidden in evidence")


def test_discovery_symlink_at_depth_2_fails(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
    world = build_discovery_evidence(tmp_path, gh, monkeypatch)
    link = world.evidence / "native-guard-receipt" / "link.txt"
    link.symlink_to(world.paths["bundle"])
    fails(world, "symlink forbidden in evidence")


def test_discovery_symlink_at_depth_3_deep_in_extracted_tree_fails(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
    world = build_discovery_evidence(tmp_path, gh, monkeypatch)
    deep_dir = world.evidence / "native-scan-evidence" / "extracted" / "python-sdist" / "agentic_praxis_grimoire-0.13.0" / "deep"
    deep_dir.mkdir(parents=True, exist_ok=True)
    (deep_dir / "evil_link.txt").symlink_to(world.paths["bundle"])
    fails(world, "symlink forbidden in evidence")


# --------------------------------------------------------------------------- bundle seal pin and recursive inventory


def test_discovery_bundle_seal_pin_checked_before_recursive_derivation(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
    world = build_discovery_evidence(tmp_path, gh, monkeypatch)
    # Alter the NATIVE_BUNDLE_JSON pin
    monkeypatch.setenv("NATIVE_BUNDLE_JSON", json.dumps({**world.bundle_ref, "seal_sha256": "0" * 64}))
    fails(world, "bundle seal differs from NATIVE_BUNDLE_JSON")


def test_discovery_bundle_recursive_inventory_extra_file_fails(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
    world = build_discovery_evidence(tmp_path, gh, monkeypatch)
    (world.evidence / assembly.BUNDLE_ARTIFACT_NAME / "unexpected-file.txt").write_text("extra\n")
    fails(world, r"bundle artifact inventory differs:.*extra=\['unexpected-file\.txt'\]")


def test_discovery_bundle_recursive_inventory_missing_file_fails(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
    world = build_discovery_evidence(tmp_path, gh, monkeypatch)
    (world.evidence / assembly.BUNDLE_ARTIFACT_NAME / "SHA256SUMS").unlink()
    fails(world, r"bundle artifact inventory differs:.*missing=\['SHA256SUMS'\]")


def test_discovery_lane_inventory_extra_file_fails(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
    world = build_discovery_evidence(tmp_path, gh, monkeypatch)
    (world.evidence / "native-darwin-arm64" / "darwin-arm64" / "extra.txt").write_text("extra\n")
    fails(world, r"lane native-darwin-arm64 artifact inventory differs:.*extra=\['extra\.txt'\]")


@pytest.mark.parametrize("relative", [
    "native-darwin-arm64/darwin-arm64/lane-seal.json",
    "native-darwin-arm64-receipt/lane-seal.json",
    "native-release-candidate-bundle/release-bundle-seal.json",
    "native-assemble-receipt/release-bundle-seal.json",
    "native-scan-evidence/scan-results.json",
    "native-release-scans-receipt/scan-results.json",
    "matrix-aggregate.json",
    "native-assemble-receipt/public-projection-manifest.json",
    "native-consumer-darwin-arm64-receipt/consumer-receipt.json",
    "native-release-scans-receipt/scan-receipt.json",
])
def test_single_authority_primary_or_copy_duplicate_keys_fail(tmp_path, gh, monkeypatch, relative):
    world = build_discovery_evidence(tmp_path, gh, monkeypatch)
    (world.evidence / relative).write_bytes(b'{"duplicate":1,"duplicate":2}\n')
    with pytest.raises(SealError, match="duplicate key"):
        gate._discover(world.evidence)


def test_missing_matrix_wrapper_is_refused(tmp_path, gh, monkeypatch):
    world = build_discovery_evidence(tmp_path, gh, monkeypatch)
    (world.evidence / "native-guard-receipt/native-guard-receipt.json").unlink()
    with pytest.raises(gate.GateError, match="missing matrix receipt wrapper"):
        gate._discover(world.evidence)
