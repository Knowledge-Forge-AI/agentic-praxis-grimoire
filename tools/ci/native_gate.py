#!/usr/bin/env python3
"""Strict native CI release-candidate gate.

The gate trusts nothing it is not handed evidence for: it requires the nine
matrix jobs to have succeeded, re-confirms every GitHub artifact identity, and
links lane seals, the bundle seal, consumer receipts, scan results and the scan
receipt to each other and to the matrix receipts by digest.  Missing,
duplicate, skipped or inconsistent evidence fails the gate.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

if str(Path(__file__).resolve().parents[2]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.ci import native_artifacts as artifacts
from tools.ci import native_release_assembly as assembly
from tools.ci.native_gate_discovery import (
    GateError,
    _discover,
    _env_json,
    _require,
    _self_hashed,
)
from tools.ci.native_seal import (
    CANONICAL_TARGETS,
    RC_INDEX_SCHEMA,
    REQUIRED_LANES,
    SealError,
    canonical_json,
    check_containment,
    sha256_bytes,
)
from tools.ci.native_topology import REQUIRED_NATIVE_JOBS

ROOT = Path(__file__).resolve().parents[2]

AGGREGATE_SCHEMA = "apg-matrix-aggregate-v1"
MATRIX_JOBS = frozenset(REQUIRED_NATIVE_JOBS - {"native-release-candidate-gate"})
INDEX_NAME = "native-rc-index.json"
HEX_RE = assembly.HEX_RE



def _bound(members: Mapping[str, Any], job: str, filename: str, digest: str) -> None:
    """The matrix receipt of ``job`` must list ``filename`` with exactly this digest."""
    listed = members[job].get("artifacts")
    matches = [v for k, v in listed.items() if Path(k).name == filename] if isinstance(listed, dict) else []
    _require(matches == [digest], f"matrix receipt for {job} does not bind {filename} to the evidence digest")


def _check_matrix(found: Mapping[str, Any], identity: Mapping[str, str]) -> Mapping[str, Any]:
    _require("matrix" in found, "missing matrix aggregate in evidence")
    agg, _ = found["matrix"]
    _require(agg.get("success") is True and agg.get("errors") == [], "matrix aggregate reports failure")
    _require(agg.get("required_members_count") == 9 and agg.get("verified_members_count") == 9, "matrix aggregate does not cover nine members")
    members = agg.get("members")
    _require(isinstance(members, dict) and set(members) == MATRIX_JOBS, "matrix aggregate members are not exactly the nine jobs")
    _require(agg.get("member_receipt_status") == {job: "success" for job in sorted(MATRIX_JOBS)}, "matrix member receipt statuses are not all success")
    policy_digests = set()
    for job, receipt in members.items():
        _require(isinstance(receipt, dict) and receipt.get("job") == job and receipt.get("status") == "success", f"matrix receipt for {job} is not a success")
        _require(not receipt.get("unavailable_artifacts"), f"matrix receipt for {job} lists unavailable artifacts")
        _require(receipt.get("sha") == identity["source_commit"], f"matrix receipt for {job} names a different commit")
        for key in ("pr_head_sha", "pr_base_sha"):
            _require(receipt.get(key) == identity[key], f"matrix receipt for {job} disagrees on {key}")
        policy_digests.add(receipt.get("workflow_sha256"))
    _require(len(policy_digests) == 1 and all(isinstance(d, str) and HEX_RE.match(d) for d in policy_digests), "matrix receipts disagree on the workflow policy digest")
    return members


def _check_lane(lane: str, doc: Mapping[str, Any], ref: Mapping[str, str], identity: Mapping[str, str]) -> None:
    spec = CANONICAL_TARGETS[lane]
    seal = _self_hashed(doc, "seal_sha256", f"lane {lane} seal")
    _require(seal == ref["seal_sha256"], f"lane {lane} seal differs from NATIVE_INPUTS_JSON")
    _require(doc.get("target") == spec["target"] and doc.get("target_slug") == spec["slug"], f"lane {lane} seal names the wrong target")
    _require(doc.get("source_commit") == identity["source_commit"] and doc.get("source_tree") == identity["source_tree"], f"lane {lane} seal source identity differs")
    _require(set(doc.get("files", {})) == assembly.LANE_FILES, f"lane {lane} seal inventory is incomplete")


def _check_bundle(doc: Mapping[str, Any], ref: Mapping[str, str], lanes: Mapping[str, str], identity: Mapping[str, str]) -> None:
    seal = _self_hashed(doc, "bundle_seal_sha256", "bundle seal")
    _require(seal == ref["seal_sha256"], "bundle seal differs from NATIVE_BUNDLE_JSON")
    _require(doc.get("source_commit") == identity["source_commit"] and doc.get("source_tree") == identity["source_tree"], "bundle seal source identity differs")
    assets = doc.get("assets")
    _require(doc.get("asset_count") == 11 and isinstance(assets, dict) and len(assets) == 11, "bundle seal must list exactly eleven assets")
    go = {n for n in assets if n.startswith("go/")}
    _require(go == {spec["go_binary"] for spec in CANONICAL_TARGETS.values()}, "bundle seal Go assets are not the three canonical binaries")
    counts = (sum(n.startswith("python/") and n.endswith(".whl") for n in assets), sum(n.startswith("python/") and n.endswith(".tar.gz") for n in assets),
              sum(n.startswith("npm/") and n.endswith(".tgz") for n in assets))
    _require(counts == (3, 1, 4), f"bundle seal asset mix is not 3 wheels, 1 sdist, 4 npm: {counts}")
    for key in ("manifest_sha256", "checksums_sha256"):
        _require(isinstance(doc.get(key), str) and HEX_RE.match(doc[key]), f"bundle seal lacks {key}")
    _require(doc.get("lane_seals") == lanes, "bundle seal lane links differ from the verified lane seals")


def _check_consumer(lane: str, doc: Mapping[str, Any], bundle_seal: str, identity: Mapping[str, str]) -> str:
    receipt = _self_hashed(doc, "receipt_sha256", f"consumer receipt {lane}")
    checks = doc.get("checks")
    _require(doc.get("status") == "passed" and doc.get("target") == CANONICAL_TARGETS[lane]["target"], f"consumer receipt {lane} did not pass its own target")
    required = {"wheel_install_smoke", "foreign_wheel_rejected", "npm_install_smoke", "bundle_seal_verified"}
    _require(isinstance(checks, dict) and set(checks) == required and all(v == "passed" for v in checks.values()), f"consumer receipt {lane} has failing or empty checks")
    _require(doc.get("bundle_seal_sha256") == bundle_seal, f"consumer receipt {lane} is bound to a different bundle seal")
    _require(doc.get("source_commit") == identity["source_commit"] and doc.get("source_tree") == identity["source_tree"], f"consumer receipt {lane} source identity differs")
    return receipt


def _check_scans(results: Mapping[str, Any], receipt: Mapping[str, Any], results_sha: str, bundle: Mapping[str, Any]) -> str:
    try:
        assembly.validate_scan_document(results, bundle["assets"])
    except assembly.AssemblyError as error:
        raise GateError(f"scan results rejected: {error}") from error
    digest = _self_hashed(receipt, "receipt_sha256", "scan receipt")
    _require(receipt.get("status") == "passed" and receipt.get("grype_policy") == "passed", "scan receipt did not pass")
    _require(receipt.get("asset_count") == 11 and receipt.get("scan_count") == 14, "scan receipt counts are not 11 assets and 14 scans")
    _require(receipt.get("bundle_seal_sha256") == bundle["bundle_seal_sha256"], "scan receipt is bound to a different bundle seal")
    _require(receipt.get("scans_digest") == results_sha, "scan receipt digest differs from the scan results evidence")
    return digest


def _verify_inputs(evidence_dir: Path, ctx: Any, inputs: Mapping[str, Any], bundle_ref: Mapping[str, Any]) -> None:
    """Fatal archive checks bind every exact download, including matrix receipts."""
    receipt_refs = _env_json("NATIVE_RECEIPTS_JSON")
    scan_ref = _env_json("NATIVE_SCAN_JSON")
    _require(isinstance(receipt_refs, dict) and set(receipt_refs) == MATRIX_JOBS, "receipt artifact identity inventory must cover nine jobs")
    refs = {lane: inputs[lane] for lane in REQUIRED_LANES}
    refs[assembly.BUNDLE_ARTIFACT_NAME] = bundle_ref
    refs["native-scan-evidence"] = scan_ref
    refs.update({f"{job}-receipt": ref for job, ref in receipt_refs.items()})
    _require({p.name for p in evidence_dir.iterdir()} == {*refs, "matrix-aggregate.json"}, "downloaded artifact inventory differs")
    for name, ref in refs.items():
        _require(isinstance(ref, dict) and isinstance(ref.get("artifact_id"), str) and isinstance(ref.get("artifact_digest"), str), "missing artifact ID/digest")
        artifacts.verify_downloaded_artifact(ctx, ref["artifact_id"], ref["artifact_digest"], name,
                                             evidence_dir / name, scratch=evidence_dir.parent)


def run_gate(evidence_dir: Path, output_path: Path) -> dict[str, Any]:
    """Verify every prerequisite and write ``native-rc-index.json``."""
    check_containment(output_path, "gate output")
    try:
        identity = assembly.identity_from_env()
        inputs = assembly.parse_lane_inputs(os.environ.get("NATIVE_INPUTS_JSON"))
    except assembly.AssemblyError as error:
        raise GateError(str(error)) from error
    results = _env_json("MATRIX_NEEDS_RESULTS")
    _require(isinstance(results, dict) and set(results) == MATRIX_JOBS, "MATRIX_NEEDS_RESULTS must name exactly the nine matrix jobs")
    for job, status in sorted(results.items()):
        _require(status == "success", f"prerequisite job {job} did not succeed (status={status!r})")
    bundle_ref = _env_json("NATIVE_BUNDLE_JSON")
    _require(isinstance(bundle_ref, dict) and set(bundle_ref) == {"artifact_id", "artifact_digest", "seal_sha256"}
             and all(isinstance(v, str) for v in bundle_ref.values()) and bool(HEX_RE.match(bundle_ref["seal_sha256"])),
             "NATIVE_BUNDLE_JSON must carry exactly artifact_id, artifact_digest, seal_sha256")

    ctx = artifacts.context_from_env()
    identities = {lane: (inputs[lane]["artifact_id"], inputs[lane]["artifact_digest"], lane) for lane in REQUIRED_LANES}
    identities["bundle"] = (bundle_ref["artifact_id"], bundle_ref["artifact_digest"], assembly.BUNDLE_ARTIFACT_NAME)
    for artifact_id, digest, name in identities.values():
        artifacts.verify_artifact_metadata(ctx, artifact_id, digest, name)
    _verify_inputs(evidence_dir, ctx, inputs, bundle_ref)

    found = _discover(evidence_dir, bundle_ref)
    expected = {"matrix", "guard", "bundle", "scan-results", "scan-receipt", "public-projection",
                *(f"lane:{lane}" for lane in REQUIRED_LANES), *(f"consumer:{lane}" for lane in REQUIRED_LANES)}
    _require(set(found) == expected, f"evidence set is incomplete: missing={sorted(expected - set(found))}")
    members = _check_matrix(found, identity)
    guard, guard_sha = found["guard"]
    _require(all(guard.get(key) == value for key, value in identity.items()), "guard identity differs from source identity")
    _bound(members, "native-guard", "identity.json", guard_sha)

    lane_hashes: dict[str, str] = {}
    for lane in REQUIRED_LANES:
        doc, file_sha = found[f"lane:{lane}"]
        _check_lane(lane, doc, inputs[lane], identity)
        _bound(members, lane, "lane-seal.json", file_sha)
        lane_hashes[lane] = doc["seal_sha256"]
    bundle, bundle_sha = found["bundle"]
    _check_bundle(bundle, bundle_ref, lane_hashes, identity)
    _bound(members, "native-assemble", "release-bundle-seal.json", bundle_sha)
    projection, projection_sha = found["public-projection"]
    _require(set(projection) == {"schema_version", "canonical_public_identity", "excluded_prefix", "entries"}
             and type(projection.get("schema_version")) is int and projection["schema_version"] == 1
             and projection.get("excluded_prefix") == "private/"
             and isinstance(projection.get("entries"), list) and bool(projection["entries"]),
             "public projection manifest is malformed")
    workflow_hashes = [e.get("sha256") for e in projection["entries"] if isinstance(e, dict)
                       and e.get("path") == ".github/workflows/native-qualification.yml"]
    _require(workflow_hashes == [members["native-assemble"]["workflow_sha256"]],
             "public projection does not bind the tested native workflow")
    _bound(members, "native-assemble", "public-projection-manifest.json", projection_sha)
    consumers: dict[str, Any] = {}
    for lane in REQUIRED_LANES:
        doc, file_sha = found[f"consumer:{lane}"]
        receipt = _check_consumer(lane, doc, bundle["bundle_seal_sha256"], identity)
        _bound(members, f"native-consumer-{lane.removeprefix('native-')}", "consumer-receipt.json", file_sha)
        consumers[lane] = {"status": "passed", "receipt_sha256": receipt, "file_sha256": file_sha}
    scan_results, results_sha = found["scan-results"]
    scan_receipt, scan_receipt_sha = found["scan-receipt"]
    scan_digest = _check_scans(scan_results, scan_receipt, results_sha, bundle)
    _bound(members, "native-release-scans", "scan-results.json", results_sha)
    _bound(members, "native-release-scans", "scan-receipt.json", scan_receipt_sha)

    aggregate_sha = found["matrix"][1]
    index: dict[str, Any] = {
        "schema": RC_INDEX_SCHEMA,
        "status": "passed",
        "retention_class": "routine",
        **identity,
        "members": {job: {"name": job, "status": "passed", **identity,
                          "matrix_receipt_sha256": sha256_bytes(canonical_json(members[job]))} for job in sorted(MATRIX_JOBS)},
        "lane_artifacts": {lane: {"target": CANONICAL_TARGETS[lane]["target"], "seal_sha256": lane_hashes[lane],
                         "artifact_id": inputs[lane]["artifact_id"], "artifact_digest": inputs[lane]["artifact_digest"],
                         "file_sha256": found[f"lane:{lane}"][1]} for lane in REQUIRED_LANES},
        "bundle_artifact": {"seal_sha256": bundle["bundle_seal_sha256"], "artifact_id": bundle_ref["artifact_id"],
                   "artifact_digest": bundle_ref["artifact_digest"], "asset_count": 11,
                   "manifest_sha256": bundle["manifest_sha256"], "checksums_sha256": bundle["checksums_sha256"],
                   "file_sha256": bundle_sha, "consumers": consumers,
                   "public_projection_sha256": projection_sha,
                   "matrix": {"aggregate_sha256": aggregate_sha, "workflow_sha256": members["native-guard"]["workflow_sha256"]},
                   "scans": {"status": "passed", "asset_count": 11, "scan_count": 14, "receipt_sha256": scan_digest,
                             "receipt_file_sha256": scan_receipt_sha, "results_sha256": results_sha}},
    }
    target = output_path if output_path.suffix == ".json" else output_path / INDEX_NAME
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("xb") as stream:
            stream.write(canonical_json(index))
    except FileExistsError as error:
        raise GateError(f"gate output already exists: {target}") from error
    return index


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="native_gate", description="APGR native release candidate gate")
    parser.add_argument("--evidence", type=Path, required=True, help="Directory holding seals, receipts, scan results and the matrix aggregate")
    parser.add_argument("--output", type=Path, required=True, help="Directory (or .json path) for native-rc-index.json")
    args = parser.parse_args(argv)
    try:
        run_gate(args.evidence, args.output)
    except (GateError, SealError, assembly.AssemblyError, artifacts.ArtifactError) as error:
        print(f"native_gate failure: {error}", file=sys.stderr)
        return 1
    print("native release candidate gate PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
