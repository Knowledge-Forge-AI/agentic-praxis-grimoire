"""Unit tests for tools/ci/native_gate.py (GitHub replaced at the native_artifacts network seam)."""

from __future__ import annotations

import copy
import hashlib
import io
import json
import urllib.error
import zipfile
from collections.abc import Callable
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
WHEELS = ("pkg-0.13.0-py3-none-macosx_12_0_arm64.whl", "pkg-0.13.0-py3-none-manylinux_2_17_x86_64.whl", "pkg-0.13.0-py3-none-manylinux_2_17_aarch64.whl")
NPMS = ("scope-apgr-0.13.0.tgz", "scope-apgr-darwin-arm64-0.13.0.tgz", "scope-apgr-linux-x64-0.13.0.tgz", "scope-apgr-linux-arm64-0.13.0.tgz")
CONSUMER_JOBS = {lane: f"native-consumer-{lane.removeprefix('native-')}" for lane in REQUIRED_LANES}
VERIFY_INPUTS = gate._verify_inputs


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
    parts = {"sbom": {"path": "p/sbom", "sha256": hex_of("sbom"), "package_count": 3, "missing_types": [], "coverage_status": "passed", "syft_returncode": 0},
             "grype": {"path": "p/grype", "sha256": hex_of("grype"), "input_sbom_sha256": hex_of("sbom"), "blocking_severities": [], "returncode": 0, "status": "passed"}}
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


Edit = Callable[[dict[str, Any]], None]


def build_evidence(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch, *, edits: dict[str, Edit] | None = None,
                   tamper: dict[str, Edit] | None = None, skip: tuple[str, ...] = ()) -> SimpleNamespace:
    """Write a complete, consistent evidence tree; ``edits`` run before each document is sealed, ``tamper`` after."""
    edits, tamper = edits or {}, tamper or {}
    evidence = tmp_path / "evidence"
    paths: dict[str, Path] = {}
    docs: dict[str, dict[str, Any]] = {}
    sealed: dict[str, str] = {}

    def emit(key: str, relative: str, doc: dict[str, Any], seal_key: str | None, pretty: bool = False) -> None:
        if key in edits:
            edits[key](doc)
        if seal_key:
            finalize(doc, seal_key)
            sealed[key] = doc[seal_key]
        if key in tamper:
            tamper[key](doc)
        path = evidence / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((json.dumps(doc, indent=2, sort_keys=True) + "\n").encode() if pretty else canonical_json(doc))
        paths[key], docs[key] = path, doc

    # 1. Native guard receipt
    guard_dir = evidence / "native-guard-receipt"
    guard_dir.mkdir(parents=True, exist_ok=True)
    guard_doc = {"schema_version": "apgr.native-identity/v1", "source_commit": COMMIT, "source_tree": TREE,
                 "repository": na.EXPECTED_REPO, "repository_id": na.EXPECTED_REPO_ID,
                 "pr_head_sha": HEAD, "pr_base_sha": BASE, "status": "passed"}
    emit("guard", "native-guard-receipt/identity.json", guard_doc, None)
    (guard_dir / "native-guard-receipt.json").write_text(
        json.dumps({"schema": "apg-matrix-receipt-v1", "job": "native-guard", "status": "success"}) + "\n")

    # 2. Lane seals, receipts and lane download artifacts with wrapper
    lane_ids: dict[str, str] = {}
    for lane in REQUIRED_LANES:
        spec = CANONICAL_TARGETS[lane]
        doc = {"schema_version": LANE_SEAL_SCHEMA, "lane": lane, "target": spec["target"], "target_slug": spec["slug"], "source_commit": COMMIT,
               "source_tree": TREE, "files": {n: {"sha256": hex_of(n), "size_bytes": 1} for n in sorted(assembly.LANE_FILES)}}
        emit(f"lane:{lane}", f"{lane}-receipt/lane-seal.json", doc, "seal_sha256")
        lane_ids[lane] = sealed[f"lane:{lane}"]
        (evidence / f"{lane}-receipt" / f"{lane}-receipt.json").write_text(
            json.dumps({"schema": "apg-matrix-receipt-v1", "job": lane, "status": "success"}) + "\n")

        # Real lane artifact download directory with wrapper slug
        lane_out = evidence / lane / spec["slug"]
        lane_out.mkdir(parents=True, exist_ok=True)
        (lane_out / "lane-seal.json").write_bytes(paths[f"lane:{lane}"].read_bytes())
        for name in assembly.LANE_FILES:
            (lane_out / name).write_bytes(f"fixture {lane} {name}\n".encode())

    # 3. Bundle seal, assemble receipt and bundle download artifact
    assets = {spec["go_binary"]: {"sha256": hex_of(spec["go_binary"]), "size_bytes": 5} for spec in CANONICAL_TARGETS.values()}
    assets.update({f"python/{n}": {"sha256": hex_of(n), "size_bytes": 5} for n in (*WHEELS, "pkg-0.13.0.tar.gz")})
    assets.update({f"npm/{n}": {"sha256": hex_of(n), "size_bytes": 5} for n in NPMS})
    baseline_assets = copy.deepcopy(assets)  # edits to the bundle must not leak into the scan document
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

    # 5. Scan results, scan receipt and scan evidence download artifact
    emit("scan-results", "native-release-scans-receipt/scan-results.json", scan_doc(baseline_assets), None, pretty=True)
    receipt = {"schema_version": SCAN_RECEIPT_SCHEMA, "bundle_seal_sha256": bundle_seal, "asset_count": 11, "scan_count": 14, "status": "passed",
               "grype_policy": "passed", "scans_digest": hashlib.sha256(paths["scan-results"].read_bytes()).hexdigest()}
    emit("scan-receipt", "native-release-scans-receipt/scan-receipt.json", receipt, "receipt_sha256")
    (evidence / "native-release-scans-receipt" / "native-release-scans-receipt.json").write_text(
        json.dumps({"schema": "apg-matrix-receipt-v1", "job": "native-release-scans", "status": "success"}) + "\n")

    scan_dir = evidence / "native-scan-evidence"
    scan_dir.mkdir(parents=True, exist_ok=True)
    (scan_dir / "scan-results.json").write_bytes(paths["scan-results"].read_bytes())
    # Exact duplicate fixture hotspot/testdata/classification/sample.json under scan extracted sdist
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

    for key in skip:
        paths[key].unlink()
        if key.startswith("lane:"):
            lane = key.removeprefix("lane:")
            (evidence / lane / CANONICAL_TARGETS[lane]["slug"] / "lane-seal.json").unlink(missing_ok=True)
        elif key == "bundle":
            (evidence / assembly.BUNDLE_ARTIFACT_NAME / "release-bundle-seal.json").unlink(missing_ok=True)
        elif key == "scan-results":
            (evidence / "native-scan-evidence" / "scan-results.json").unlink(missing_ok=True)

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
    # These cases exercise index/linkage validation. Archive transfer is covered
    # by the connected _verify_inputs fixture below and native_artifacts tests.
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


@pytest.mark.parametrize("mutation", [None, "tampered", "extra-download"])
def test_gate_archive_checks_connect_all_fourteen_downloads(tmp_path, gh, monkeypatch, mutation):
    evidence = tmp_path / "downloads"
    evidence.mkdir()
    names = [*REQUIRED_LANES, assembly.BUNDLE_ARTIFACT_NAME, "native-scan-evidence",
             *(f"{job}-receipt" for job in sorted(gate.MATRIX_JOBS))]
    bindings = {}
    for number, name in enumerate(names, 1):
        folder = evidence / name
        folder.mkdir()
        payload = ("source fixture " + name).encode()
        (folder / "proof.txt").write_bytes(payload)
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr("proof.txt", payload)
        data = stream.getvalue()
        digest = "sha256:" + hashlib.sha256(data).hexdigest()
        ref = {"artifact_id": str(number), "artifact_digest": digest}
        bindings[name] = ref
        serve(gh, str(number), name, digest=digest, size_in_bytes=len(data))
        gh.routes[f"{na.API_ROOT}/repos/{na.EXPECTED_REPO}/actions/artifacts/{number}/zip"] = data
    (evidence / "matrix-aggregate.json").write_text("{}")
    monkeypatch.setenv("NATIVE_RECEIPTS_JSON", json.dumps({job: bindings[f"{job}-receipt"] for job in gate.MATRIX_JOBS}))
    monkeypatch.setenv("NATIVE_SCAN_JSON", json.dumps(bindings["native-scan-evidence"]))
    if mutation == "tampered":
        (evidence / REQUIRED_LANES[0] / "proof.txt").write_bytes(b"changed")
    elif mutation == "extra-download":
        (evidence / "duplicate-lane").mkdir()
    def call() -> None:
        VERIFY_INPUTS(
            evidence,
            na.context_from_env(),
            {lane: bindings[lane] for lane in REQUIRED_LANES},
            bindings[assembly.BUNDLE_ARTIFACT_NAME],
        )
    if mutation:
        with pytest.raises((gate.GateError, na.ArtifactError)):
            call()
    else:
        call()
        assert sum(url.endswith("/zip") for url in gh.calls) == 14


def fails(world: SimpleNamespace, message: str, error: type[Exception] = gate.GateError) -> None:
    with pytest.raises(error, match=message):
        gate.run_gate(world.evidence, world.out)
    assert not world.out.exists() or not any(world.out.iterdir())


# --------------------------------------------------------------------------- success


def test_gate_passes_and_writes_exact_index(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
    world = build_evidence(tmp_path, gh, monkeypatch)
    index = gate.run_gate(world.evidence, world.out)
    written = load_canonical_json(world.out / "native-rc-index.json")
    assert written == index
    assert (world.out / "native-rc-index.json").read_bytes() == canonical_json(index)
    assert index["schema"] == RC_INDEX_SCHEMA == "apgr.native-rc-index/v1"
    assert index["status"] == "passed" and index["retention_class"] == "routine"
    assert (index["source_commit"], index["source_tree"], index["pr_head_sha"], index["pr_base_sha"]) == (COMMIT, TREE, HEAD, BASE)
    assert set(index["members"]) == set(gate.MATRIX_JOBS) and len(index["members"]) == 9 and {m["status"] for m in index["members"].values()} == {"passed"}
    assert set(index["lane_artifacts"]) == set(REQUIRED_LANES)
    for lane, entry in index["lane_artifacts"].items():
        assert entry["seal_sha256"] == world.docs[f"lane:{lane}"]["seal_sha256"]
        assert (entry["artifact_id"], entry["artifact_digest"]) == (LANE_IDS[lane], "sha256:" + hex_of(lane))
        assert index["bundle_artifact"]["consumers"][lane]["receipt_sha256"] == world.docs[f"consumer:{lane}"]["receipt_sha256"]
    assert index["bundle_artifact"]["seal_sha256"] == world.bundle_ref["seal_sha256"] and index["bundle_artifact"]["artifact_id"] == BUNDLE_ID
    assert index["bundle_artifact"]["asset_count"] == 11
    assert (index["bundle_artifact"]["scans"]["asset_count"], index["bundle_artifact"]["scans"]["scan_count"], index["bundle_artifact"]["scans"]["status"]) == (11, 14, "passed")
    assert index["bundle_artifact"]["scans"]["receipt_sha256"] == world.docs["scan-receipt"]["receipt_sha256"]
    assert len(gh.calls) == 4  # three lane artifacts and the bundle: metadata only
    with pytest.raises(gate.GateError, match="already exists"):
        gate.run_gate(world.evidence, world.out)


@pytest.mark.parametrize("mutation", ["missing", "unbound"])
def test_gate_requires_projection_evidence_bound_by_assembly(tmp_path, gh, monkeypatch, mutation):
    world = build_evidence(tmp_path, gh, monkeypatch)
    if mutation == "missing":
        world.paths["public-projection"].unlink()
    else:
        doc = world.docs["matrix"]
        del doc["members"]["native-assemble"]["artifacts"]["public-projection-manifest.json"]
        world.paths["matrix"].write_bytes(canonical_json(doc))
    with pytest.raises(gate.GateError, match="incomplete|does not bind"):
        gate.run_gate(world.evidence, world.out)


def test_projection_manifest_must_name_the_tested_native_workflow(tmp_path, gh, monkeypatch):
    world = build_evidence(tmp_path, gh, monkeypatch, edits={
        "public-projection": lambda d: d["entries"][0].update(sha256="f" * 64)})
    with pytest.raises(gate.GateError, match="tested native workflow"):
        gate.run_gate(world.evidence, world.out)


def test_gate_accepts_a_json_output_path(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
    world = build_evidence(tmp_path, gh, monkeypatch)
    gate.run_gate(world.evidence, tmp_path / "index" / "native-rc-index.json")
    assert (tmp_path / "index" / "native-rc-index.json").is_file()


def test_main_exit_codes(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    world = build_evidence(tmp_path, gh, monkeypatch)
    assert gate.main(["--evidence", str(world.evidence), "--output", str(world.out)]) == 0
    assert "PASSED" in capsys.readouterr().out
    assert gate.main(["--evidence", str(world.evidence), "--output", str(world.out)]) == 1
    assert "native_gate failure" in capsys.readouterr().err


# --------------------------------------------------------------------------- environment


@pytest.mark.parametrize("status", ["failure", "skipped", "cancelled", "", None, 0, True])
def test_every_matrix_job_must_report_success(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch, status: Any) -> None:
    world = build_evidence(tmp_path, gh, monkeypatch)
    for job in sorted(gate.MATRIX_JOBS):
        results = {name: "success" for name in gate.MATRIX_JOBS}
        results[job] = status
        monkeypatch.setenv("MATRIX_NEEDS_RESULTS", json.dumps(results))
        fails(world, f"prerequisite job {job} did not succeed")
    assert gh.calls == []


@pytest.mark.parametrize("variant", ["missing-job", "extra-job", "gate-itself", "empty", "list"])
def test_matrix_results_must_name_exactly_nine_jobs(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch, variant: str) -> None:
    world = build_evidence(tmp_path, gh, monkeypatch)
    results: Any = {name: "success" for name in sorted(gate.MATRIX_JOBS)}
    if variant == "missing-job":
        del results["native-release-scans"]
    elif variant == "extra-job":
        results["native-extra"] = "success"
    elif variant == "gate-itself":
        results["native-release-candidate-gate"] = "success"
    elif variant == "empty":
        results = {}
    else:
        results = ["success"] * 9
    monkeypatch.setenv("MATRIX_NEEDS_RESULTS", json.dumps(results))
    fails(world, "exactly the nine matrix jobs")


@pytest.mark.parametrize("name", ["MATRIX_NEEDS_RESULTS", "NATIVE_INPUTS_JSON", "NATIVE_BUNDLE_JSON"])
def test_required_environment_documents(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch, name: str) -> None:
    world = build_evidence(tmp_path, gh, monkeypatch)
    monkeypatch.delenv(name)
    fails(world, name)
    monkeypatch.setenv(name, "{not json")
    fails(world, "malformed|exactly|must", (gate.GateError))


@pytest.mark.parametrize(
    ("edit", "message"),
    [
        (lambda ref: ref.pop("artifact_digest"), "exactly artifact_id, artifact_digest, seal_sha256"),
        (lambda ref: ref.update({"extra": "x"}), "exactly artifact_id, artifact_digest, seal_sha256"),
        (lambda ref: ref.update({"seal_sha256": "zz"}), "exactly artifact_id, artifact_digest, seal_sha256"),
        (lambda ref: ref.update({"artifact_id": 4}), "exactly artifact_id, artifact_digest, seal_sha256"),
    ],
)
def test_bundle_reference_shape(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch, edit: Edit, message: str) -> None:
    world = build_evidence(tmp_path, gh, monkeypatch)
    ref = copy.deepcopy(world.bundle_ref)
    edit(ref)
    monkeypatch.setenv("NATIVE_BUNDLE_JSON", json.dumps(ref))
    fails(world, message)
    assert gh.calls == []


@pytest.mark.parametrize("variable", ["SOURCE_COMMIT", "SOURCE_TREE", "PR_HEAD_SHA", "PR_BASE_SHA"])
def test_identity_environment_is_mandatory(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch, variable: str) -> None:
    world = build_evidence(tmp_path, gh, monkeypatch)
    monkeypatch.delenv(variable)
    fails(world, f"{variable} must be")
    monkeypatch.setenv(variable, "not-a-sha")
    fails(world, f"{variable} must be")


def test_lane_inputs_shape_is_enforced(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
    world = build_evidence(tmp_path, gh, monkeypatch)
    inputs = copy.deepcopy(world.inputs)
    del inputs["native-linux-arm64"]
    monkeypatch.setenv("NATIVE_INPUTS_JSON", json.dumps(inputs))
    fails(world, "exactly the three native lanes")
    inputs = copy.deepcopy(world.inputs)
    inputs["native-linux-arm64"]["artifact_digest"] = "sha256:short"
    monkeypatch.setenv("NATIVE_INPUTS_JSON", json.dumps(inputs))
    fails(world, "artifact_digest is malformed")


# --------------------------------------------------------------------------- GitHub identity


def test_missing_read_token_is_fatal(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
    world = build_evidence(tmp_path, gh, monkeypatch)
    monkeypatch.delenv("GITHUB_TOKEN")
    fails(world, "read token", na.ArtifactError)
    assert gh.calls == []


@pytest.mark.parametrize(
    ("artifact", "override", "message"),
    [
        ("native-darwin-arm64", {"expired": True}, "expired"),
        ("native-linux-x64", {"workflow_run": {"id": 1, "repository_id": na.EXPECTED_REPO_ID, "head_repository_id": na.EXPECTED_REPO_ID}}, "does not belong to run"),
        ("native-linux-arm64", {"digest": "sha256:" + "0" * 64}, "digest changed"),
        ("native-linux-arm64", {"digest": None}, "no valid sha256 digest"),
        ("native-darwin-arm64", {"name": "someone-elses-artifact"}, "name mismatch"),
        (assembly.BUNDLE_ARTIFACT_NAME, {"expired": True}, "expired"),
        (assembly.BUNDLE_ARTIFACT_NAME, {"digest": "sha256:" + "1" * 64}, "digest changed"),
        (assembly.BUNDLE_ARTIFACT_NAME, {"name": "native-darwin-arm64"}, "name mismatch"),
    ],
)
def test_artifact_identity_is_reconfirmed(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch, artifact: str, override: dict[str, Any], message: str) -> None:
    world = build_evidence(tmp_path, gh, monkeypatch)
    artifact_id = BUNDLE_ID if artifact == assembly.BUNDLE_ARTIFACT_NAME else LANE_IDS[artifact]
    serve(gh, artifact_id, artifact, **override)
    fails(world, message, na.ArtifactError)


def test_unknown_artifact_is_fatal(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
    world = build_evidence(tmp_path, gh, monkeypatch)
    del gh.routes[f"{na.API_ROOT}/repos/{na.EXPECTED_REPO}/actions/artifacts/{BUNDLE_ID}"]
    fails(world, "HTTP 404", na.ArtifactError)


# --------------------------------------------------------------------------- evidence set

ALL_KEYS = [*(f"lane:{lane}" for lane in REQUIRED_LANES), "bundle", *(f"consumer:{lane}" for lane in REQUIRED_LANES), "scan-results", "scan-receipt", "matrix"]


@pytest.mark.parametrize("key", ALL_KEYS)
def test_missing_evidence_fails(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch, key: str) -> None:
    world = build_evidence(tmp_path, gh, monkeypatch, skip=(key,))
    fails(world, f"evidence set is incomplete: missing=\\['{key}'\\]")


@pytest.mark.parametrize("key", ALL_KEYS)
def test_duplicate_evidence_fails(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch, key: str) -> None:
    world = build_evidence(tmp_path, gh, monkeypatch)
    copy_to = world.evidence / "second-download" / world.paths[key].name
    copy_to.parent.mkdir()
    copy_to.write_bytes(world.paths[key].read_bytes())
    fails(world, "duplicate evidence for")


def test_evidence_directory_hygiene(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
    world = build_evidence(tmp_path, gh, monkeypatch)
    extracted_dir = world.evidence / "native-scan-evidence" / "extracted" / "python-sdist" / "agentic_praxis_grimoire-0.13.0"
    stray = extracted_dir / "notes.txt"
    stray.write_text("not json is ignored", encoding="utf-8")
    other = extracted_dir / "unrelated.json"
    other.write_text('{"schema": "something-else"}', encoding="utf-8")
    gate.run_gate(world.evidence, world.out)

    (world.out / "native-rc-index.json").unlink()
    bundle_path = world.paths["bundle"]
    bundle_proof = world.evidence / assembly.BUNDLE_ARTIFACT_NAME / "release-bundle-seal.json"
    bundle_orig = bundle_path.read_bytes()
    bundle_orig_proof = bundle_proof.read_bytes()
    for bad_content, err_msg in (
        ("{broken", "failed to read JSON"),
        ("[1]", "expected JSON object"),
        ('{"a": 1, "a": 2}', "duplicate key"),
    ):
        bundle_path.write_text(bad_content, encoding="utf-8")
        bundle_proof.write_text(bad_content, encoding="utf-8")
        fails(world, err_msg, SealError)
    bundle_path.write_bytes(bundle_orig)
    bundle_proof.write_bytes(bundle_orig_proof)

    root_stray = world.evidence / "notes.txt"
    root_stray.write_text("not allowed at root", encoding="utf-8")
    fails(world, "wrong-root")
    root_stray.unlink()

    link = world.evidence / "link.json"
    link.symlink_to(world.paths["bundle"])
    fails(world, "symlink forbidden")
    link.unlink()
    alias = world.evidence / "alias"
    alias.symlink_to(world.evidence / "native-assemble-receipt")
    fails(world, "symlink forbidden")


def test_evidence_must_be_a_direct_directory(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
    world = build_evidence(tmp_path, gh, monkeypatch)
    alias = tmp_path / "evidence-alias"
    alias.symlink_to(world.evidence)
    world.evidence = alias
    fails(world, "symlink", SealError)


def test_lane_documents_with_unknown_lane_are_fatal(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
    world = build_evidence(tmp_path, gh, monkeypatch, edits={"lane:native-linux-x64": lambda doc: doc.update({"lane": "native-riscv"})})
    fails(world, "unknown lane")


# --------------------------------------------------------------------------- lane seals

LANE = "native-linux-arm64"


@pytest.mark.parametrize(
    ("edit", "message"),
    [
        (lambda doc: doc.update({"source_commit": "9" * 40}), "source identity differs"),
        (lambda doc: doc.update({"source_tree": "9" * 40}), "source identity differs"),
        (lambda doc: doc.update({"target": "linux/amd64"}), "wrong target"),
        (lambda doc: doc.update({"target_slug": "linux-x64"}), "wrong target"),
        (lambda doc: doc["files"].pop("nix-evidence.json"), "inventory is incomplete"),
        (lambda doc: doc["files"].update({"extra": {}}), "inventory is incomplete"),
        (lambda doc: doc.update({"files": {}}), "inventory is incomplete"),
    ],
)
def test_lane_seal_semantics(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch, edit: Edit, message: str) -> None:
    # Recomputing the seal over the edited body isolates the semantic check from the tamper check; the
    # new seal then also differs from NATIVE_INPUTS_JSON, so the inputs are updated to follow it.
    world = build_evidence(tmp_path, gh, monkeypatch, edits={f"lane:{LANE}": edit})
    inputs = copy.deepcopy(world.inputs)
    inputs[LANE]["seal_sha256"] = world.docs[f"lane:{LANE}"]["seal_sha256"]
    monkeypatch.setenv("NATIVE_INPUTS_JSON", json.dumps(inputs))
    fails(world, message)


def test_lane_seal_tamper_and_input_mismatch(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
    world = build_evidence(tmp_path, gh, monkeypatch, tamper={f"lane:{LANE}": lambda doc: doc.update({"source_commit": "9" * 40})})
    fails(world, "seal_sha256 is tampered")
    (tmp_path / "second").mkdir()
    world = build_evidence(tmp_path / "second", gh, monkeypatch)
    inputs = copy.deepcopy(world.inputs)
    inputs[LANE]["seal_sha256"] = "0" * 64
    monkeypatch.setenv("NATIVE_INPUTS_JSON", json.dumps(inputs))
    fails(world, "seal differs from NATIVE_INPUTS_JSON")


@pytest.mark.parametrize("edit", [lambda doc: doc.pop("seal_sha256"), lambda doc: doc.update({"seal_sha256": "short"}), lambda doc: doc.update({"seal_sha256": 7})])
def test_lane_seal_requires_a_hash(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch, edit: Edit) -> None:
    world = build_evidence(tmp_path, gh, monkeypatch, tamper={f"lane:{LANE}": edit})
    fails(world, "lacks a valid seal_sha256")


# --------------------------------------------------------------------------- bundle seal


def _drop_asset(doc: dict[str, Any]) -> None:
    doc["assets"].pop(next(n for n in doc["assets"] if n.startswith("npm/")))


def _rename_go(doc: dict[str, Any]) -> None:
    doc["assets"]["go/linux-x64/apgr"] = doc["assets"].pop("go/linux-amd64/apgr")


def _swap_wheel_for_npm(doc: dict[str, Any]) -> None:
    doc["assets"].pop(f"python/{WHEELS[0]}")
    doc["assets"]["npm/scope-extra-0.13.0.tgz"] = {"sha256": hex_of("x"), "size_bytes": 1}


@pytest.mark.parametrize(
    ("edit", "message"),
    [
        (lambda doc: doc.update({"source_commit": "9" * 40}), "source identity differs"),
        (lambda doc: doc.update({"source_tree": "9" * 40}), "source identity differs"),
        (lambda doc: doc.update({"asset_count": 10}), "exactly eleven assets"),
        (_drop_asset, "exactly eleven assets"),
        (_rename_go, "three canonical binaries"),
        (_swap_wheel_for_npm, "asset mix"),
        (lambda doc: doc.pop("manifest_sha256"), "lacks manifest_sha256"),
        (lambda doc: doc.update({"checksums_sha256": "x"}), "lacks checksums_sha256"),
        (lambda doc: doc["lane_seals"].update({LANE: "0" * 64}), "lane links differ"),
        (lambda doc: doc["lane_seals"].pop(LANE), "lane links differ"),
        (lambda doc: doc["lane_seals"].update({"native-extra": "0" * 64}), "lane links differ"),
    ],
)
def test_bundle_seal_semantics(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch, edit: Edit, message: str) -> None:
    world = build_evidence(tmp_path, gh, monkeypatch, edits={"bundle": edit})
    ref = copy.deepcopy(world.bundle_ref)
    ref["seal_sha256"] = world.docs["bundle"]["bundle_seal_sha256"]
    monkeypatch.setenv("NATIVE_BUNDLE_JSON", json.dumps(ref))
    fails(world, message)


def test_bundle_seal_tamper_and_reference_mismatch(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
    world = build_evidence(tmp_path, gh, monkeypatch, tamper={"bundle": lambda doc: doc.update({"asset_count": 12})})
    fails(world, "bundle_seal_sha256 is tampered")
    (tmp_path / "ref").mkdir()
    world = build_evidence(tmp_path / "ref", gh, monkeypatch)
    monkeypatch.setenv("NATIVE_BUNDLE_JSON", json.dumps({**world.bundle_ref, "seal_sha256": "0" * 64}))
    fails(world, "bundle seal differs from NATIVE_BUNDLE_JSON")


# --------------------------------------------------------------------------- consumer receipts


@pytest.mark.parametrize(
    ("edit", "message"),
    [
        (lambda doc: doc.update({"status": "failed"}), "did not pass its own target"),
        (lambda doc: doc.update({"target": "darwin/arm64"}), "did not pass its own target"),
        (lambda doc: doc.update({"checks": {}}), "failing or empty checks"),
        (lambda doc: doc["checks"].update({"npm_install_smoke": "failed"}), "failing or empty checks"),
        (lambda doc: doc.pop("checks"), "failing or empty checks"),
        (lambda doc: doc.update({"bundle_seal_sha256": "0" * 64}), "different bundle seal"),
        (lambda doc: doc.update({"source_commit": "9" * 40}), "source identity differs"),
        (lambda doc: doc.update({"source_tree": "9" * 40}), "source identity differs"),
    ],
)
def test_consumer_receipt_semantics(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch, edit: Edit, message: str) -> None:
    world = build_evidence(tmp_path, gh, monkeypatch, edits={f"consumer:{LANE}": edit})
    fails(world, message)


@pytest.mark.parametrize("edit", [lambda doc: doc.pop("receipt_sha256"), lambda doc: doc.update({"status": "passed", "checks": {"x": "passed"}})])
def test_consumer_receipt_hash_is_mandatory_and_checked(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch, edit: Edit) -> None:
    world = build_evidence(tmp_path, gh, monkeypatch, tamper={f"consumer:{LANE}": edit})
    fails(world, "lacks a valid receipt_sha256|receipt_sha256 is tampered")


# --------------------------------------------------------------------------- scans


def _scan(path: tuple[str, ...], value: Any) -> Edit:
    def apply(doc: dict[str, Any]) -> None:
        node: Any = doc
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value
    return apply


@pytest.mark.parametrize(
    "edit",
    [
        _scan(("schema",), "apg-sbom-scan-v0"),
        _scan(("summary", "sbom_count"), 13),
        _scan(("summary", "grype_count"), 13),
        _scan(("summary", "artifact_count"), 10),
        _scan(("summary", "coverage_gaps"), ["x"]),
        _scan(("summary", "status"), "blocked"),
        _scan(("database", "valid"), False),
        _scan(("database", "age_hours"), 500),
        _scan(("policy", "custom_ignores"), ["CVE-1"]),
        lambda doc: doc["artifacts"].pop(),
        lambda doc: doc["artifacts"][0].update({"target_sha256": "0" * 64}),
        lambda doc: doc["artifacts"][3].update({"status": "policy-finding"}),
        lambda doc: doc["conditional_dependency"].update({"status": "tool-failure"}),
    ],
)
def test_scan_results_are_validated_against_the_sealed_bundle(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch, edit: Edit) -> None:
    world = build_evidence(tmp_path, gh, monkeypatch, edits={"scan-results": edit})
    fails(world, "scan results rejected|evidence set is incomplete")


@pytest.mark.parametrize(
    ("edit", "message"),
    [
        (lambda doc: doc.update({"status": "failed"}), "scan receipt did not pass"),
        (lambda doc: doc.update({"grype_policy": "failed"}), "scan receipt did not pass"),
        (lambda doc: doc.update({"scan_count": 13}), "counts are not 11 assets and 14 scans"),
        (lambda doc: doc.update({"asset_count": 10}), "counts are not 11 assets and 14 scans"),
        (lambda doc: doc.update({"bundle_seal_sha256": "0" * 64}), "different bundle seal"),
        (lambda doc: doc.update({"scans_digest": "0" * 64}), "differs from the scan results evidence"),
    ],
)
def test_scan_receipt_semantics(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch, edit: Edit, message: str) -> None:
    world = build_evidence(tmp_path, gh, monkeypatch, edits={"scan-receipt": edit})
    fails(world, message)


def test_scan_receipt_tamper_and_results_substitution(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
    world = build_evidence(tmp_path, gh, monkeypatch, tamper={"scan-receipt": lambda doc: doc.update({"scan_count": 14, "status": "passed", "x": 1})})
    fails(world, "receipt_sha256 is tampered")
    (tmp_path / "second").mkdir()
    world = build_evidence(tmp_path / "second", gh, monkeypatch)
    doc = json.loads(world.paths["scan-results"].read_text(encoding="utf-8"))
    doc["summary"]["severity_counts"] = {"low": 1}
    world.paths["scan-results"].write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    fails(world, "differs from the scan results evidence|do(es)? not bind")


# --------------------------------------------------------------------------- matrix aggregate


def _member(member_name: str, **update: Any) -> Edit:
    def apply(doc: dict[str, Any]) -> None:
        doc["members"][member_name].update(update)
    return apply


@pytest.mark.parametrize(
    ("edit", "message"),
    [
        (lambda doc: doc.update({"success": False}), "reports failure"),
        (lambda doc: doc.update({"errors": ["missing receipt"]}), "reports failure"),
        (lambda doc: doc.update({"verified_members_count": 8}), "nine members"),
        (lambda doc: doc.update({"required_members_count": 10}), "nine members"),
        (lambda doc: doc["members"].pop("native-release-scans"), "exactly the nine jobs"),
        (lambda doc: doc["members"].update({"native-extra": {}}), "exactly the nine jobs"),
        (lambda doc: doc["member_receipt_status"].update({"native-assemble": "skipped"}), "statuses are not all success"),
        (_member("native-assemble", status="skipped"), "is not a success"),
        (_member("native-guard", status="failure"), "is not a success"),
        (_member("native-linux-x64", job="native-darwin-arm64"), "is not a success"),
        (_member("native-guard", unavailable_artifacts=["lane-seal.json"]), "unavailable artifacts"),
        (_member("native-guard", sha="9" * 40), "names a different commit"),
        (_member("native-guard", pr_head_sha="9" * 40), "disagrees on pr_head_sha"),
        (_member("native-guard", pr_base_sha="9" * 40), "disagrees on pr_base_sha"),
        (_member("native-guard", workflow_sha256="f" * 64), "disagree on the workflow policy digest"),
        (_member("native-guard", workflow_sha256="short"), "workflow policy digest"),
    ],
)
def test_matrix_aggregate_semantics(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch, edit: Edit, message: str) -> None:
    world = build_evidence(tmp_path, gh, monkeypatch, edits={"matrix": edit})
    fails(world, message)


@pytest.mark.parametrize(
    ("job", "artifacts", "message"),
    [
        ("native-guard", {"identity.json": "0" * 64}, "does not bind identity.json"),
        ("native-guard", {}, "does not bind identity.json"),
        ("native-darwin-arm64", {"lane-seal.json": "0" * 64}, "does not bind lane-seal.json"),
        ("native-darwin-arm64", {}, "does not bind lane-seal.json"),
        ("native-darwin-arm64", "not-a-mapping", "does not bind lane-seal.json"),
        ("native-assemble", {"release-bundle-seal.json": "0" * 64}, "does not bind release-bundle-seal.json"),
        ("native-consumer-linux-x64", {"consumer-receipt.json": "0" * 64}, "does not bind consumer-receipt.json"),
        ("native-consumer-darwin-arm64", {"other.json": hex_of("x")}, "does not bind consumer-receipt.json"),
        ("native-release-scans", {"scan-results.json": "0" * 64}, "does not bind scan-results.json"),
    ],
)
def test_matrix_receipts_must_bind_the_exact_evidence_files(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch, job: str, artifacts: Any, message: str) -> None:
    world = build_evidence(tmp_path, gh, monkeypatch, edits={"matrix": _member(job, artifacts=artifacts)})
    fails(world, message)


@pytest.mark.parametrize("key", ["source_commit", "source_tree", "pr_head_sha", "pr_base_sha"])
def test_guard_must_match_source_identity(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch, key: str) -> None:
    world = build_evidence(tmp_path, gh, monkeypatch, edits={"guard": lambda doc: doc.update({key: "0" * 40})})
    fails(world, "guard identity differs from source identity")


@pytest.mark.parametrize("digest", [None, "0" * 64])
def test_matrix_binds_scan_receipt(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch, digest: str | None) -> None:
    def edit(doc):
        refs = doc["members"]["native-release-scans"]["artifacts"]
        if digest is None:
            del refs["scan-receipt.json"]
        else:
            refs["scan-receipt.json"] = digest
    world = build_evidence(tmp_path, gh, monkeypatch, edits={"matrix": edit})
    fails(world, "does not bind scan-receipt.json")


def test_substituted_evidence_breaks_matrix_binding(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
    world = build_evidence(tmp_path, gh, monkeypatch)
    # A different but internally consistent consumer receipt dropped in place of the original.
    path = world.paths[f"consumer:{LANE}"]
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["fixture_evidence"] = "substituted"
    doc.pop("receipt_sha256")
    path.write_bytes(canonical_json(finalize(doc, "receipt_sha256")))
    fails(world, "does not bind consumer-receipt.json")
