"""Unit tests for tools/ci/native_seal.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.ci.native_seal import (
    CONSUMER_RECEIPT_SCHEMA,
    LANE_SEAL_SCHEMA,
    SCAN_RECEIPT_SCHEMA,
    SealError,
    assert_direct_dir,
    assert_direct_file,
    build_bundle_seal,
    build_consumer_receipt,
    build_lane_seal,
    build_scan_receipt,
    canonical_json,
    check_containment,
    inspect_directory_files,
    load_canonical_json,
    main,
    verify_bundle_seal,
    verify_consumer_receipt,
    verify_lane_seal,
    verify_scan_receipt,
    write_github_output,
)


@pytest.fixture(autouse=True)
def runner_identity(monkeypatch):
    for name, value in {"RUNNER_OS": "macOS", "RUNNER_ARCH": "ARM64", "ImageOS": "macos15",
                        "ImageVersion": "fixture", "PR_HEAD_SHA": "c" * 40, "PR_BASE_SHA": "d" * 40}.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("GITHUB_WORKSPACE", raising=False)


def test_canonical_json_determinism() -> None:
    data1 = {"b": 2, "a": 1, "nested": {"z": 9, "y": 8}}
    data2 = {"nested": {"y": 8, "z": 9}, "a": 1, "b": 2}
    assert canonical_json(data1) == canonical_json(data2)
    assert canonical_json(data1).endswith(b"\n")
    assert b" " not in canonical_json(data1).split(b"\n")[0]


def test_load_canonical_json_duplicate_key_rejection(tmp_path: Path) -> None:
    bad_json = tmp_path / "bad.json"
    bad_json.write_text('{"key": 1, "key": 2}\n', encoding="utf-8")
    with pytest.raises(SealError, match="duplicate key"):
        load_canonical_json(bad_json)


def test_containment_checks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ws = tmp_path / "workspace"
    rt = tmp_path / "runner_temp"
    ws.mkdir()
    rt.mkdir()
    monkeypatch.setenv("GITHUB_WORKSPACE", str(ws))
    monkeypatch.setenv("RUNNER_TEMP", str(rt))
    monkeypatch.delenv("APGR_ALLOW_WORKSPACE_OUTPUT", raising=False)

    # Path inside workspace outside runner_temp must fail
    forbidden = ws / "out"
    with pytest.raises(SealError, match="must be outside GITHUB_WORKSPACE"):
        check_containment(forbidden)

    # Path inside runner_temp succeeds
    allowed_temp = rt / "out"
    assert check_containment(allowed_temp) == allowed_temp

    # All hosted output must stay beneath the designated temporary root.
    outside = tmp_path / "outside"
    with pytest.raises(SealError, match="under RUNNER_TEMP"):
        check_containment(outside)

    # A test-looking switch cannot bypass hosted output containment.
    monkeypatch.setenv("APGR_ALLOW_WORKSPACE_OUTPUT", "1")
    with pytest.raises(SealError):
        check_containment(forbidden)


def test_symlink_rejection_in_assert_direct(tmp_path: Path) -> None:
    target_file = tmp_path / "target.txt"
    target_file.write_text("hello\n", encoding="utf-8")
    symlink_file = tmp_path / "link.txt"
    symlink_file.symlink_to(target_file)

    with pytest.raises(SealError, match="must not be a symlink"):
        assert_direct_file(symlink_file)

    target_dir = tmp_path / "target_dir"
    target_dir.mkdir()
    symlink_dir = tmp_path / "link_dir"
    symlink_dir.symlink_to(target_dir)

    with pytest.raises(SealError, match="must not be a symlink"):
        assert_direct_dir(symlink_dir)


def test_symlink_rejection_in_directory_scan(tmp_path: Path) -> None:
    scan_dir = tmp_path / "scan_dir"
    scan_dir.mkdir()
    (scan_dir / "valid.txt").write_text("abc\n", encoding="utf-8")
    symlink_file = scan_dir / "bad_link.txt"
    symlink_file.symlink_to(scan_dir / "valid.txt")

    with pytest.raises(SealError, match="symlinked file forbidden"):
        inspect_directory_files(scan_dir)


def test_lane_seal_lifecycle_and_tamper(tmp_path: Path) -> None:
    lane_dir = tmp_path / "lane_darwin"
    lane_dir.mkdir()
    (lane_dir / "apgr").write_bytes(b"binary-darwin")
    (lane_dir / "apgr.binary-manifest.json").write_bytes(b'{"version":"0.13.0"}\n')
    (lane_dir / "go-version-m.txt").write_text("go1.26.9\n", encoding="utf-8")
    (lane_dir / "nix-evidence.json").write_bytes(b'{"status":"passed"}\n')
    (lane_dir / "nix-compiler-identity.txt").write_text("go1.26.9\n")
    (lane_dir / "go-tests.log").write_text("test/vet/race fixture\n")

    commit = "a" * 40
    tree = "b" * 40
    seal = build_lane_seal(
        "native-darwin-arm64", "darwin/arm64", "darwin-arm64", commit, tree, lane_dir
    )
    assert seal["schema_version"] == LANE_SEAL_SCHEMA
    assert "seal_sha256" in seal

    verified = verify_lane_seal(lane_dir / "lane-seal.json", expected_lane="native-darwin-arm64")
    assert verified["seal_sha256"] == seal["seal_sha256"]

    # Tamper with binary content
    (lane_dir / "apgr").write_bytes(b"binary-modified")
    with pytest.raises(SealError, match="verification failed"):
        verify_lane_seal(lane_dir / "lane-seal.json")

    # Restore binary and tamper with seal_sha256 in file
    (lane_dir / "apgr").write_bytes(b"binary-darwin")
    tampered_doc = json.loads((lane_dir / "lane-seal.json").read_text(encoding="utf-8"))
    tampered_doc["seal_sha256"] = "0" * 64
    (lane_dir / "lane-seal.json").write_bytes(canonical_json(tampered_doc))
    with pytest.raises(SealError, match="lane seal digest tampered"):
        verify_lane_seal(lane_dir / "lane-seal.json")


def _populate_canonical_11_bundle(bundle_dir: Path) -> None:
    bundle_dir.mkdir(parents=True, exist_ok=True)
    # 3 Go binaries
    for slug in ("darwin-arm64", "linux-amd64", "linux-arm64"):
        d = bundle_dir / "go" / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "apgr").write_bytes(f"go-bin-{slug}".encode())
        (d / "apgr.binary-manifest.json").write_bytes(b'{"schema":"apg.binary-manifest/v1"}\n')
    # 3 Python wheels + 1 sdist
    py_dir = bundle_dir / "python"
    py_dir.mkdir(parents=True, exist_ok=True)
    (py_dir / "pkg-0.13.0-py3-none-macosx_11_0_arm64.whl").write_bytes(b"wheel-1")
    (py_dir / "pkg-0.13.0-py3-none-manylinux_2_17_x86_64.whl").write_bytes(b"wheel-2")
    (py_dir / "pkg-0.13.0-py3-none-manylinux_2_17_aarch64.whl").write_bytes(b"wheel-3")
    (py_dir / "pkg-0.13.0.tar.gz").write_bytes(b"sdist-1")
    # 4 npm tarballs
    npm_dir = bundle_dir / "npm"
    npm_dir.mkdir(parents=True, exist_ok=True)
    (npm_dir / "apgr-0.13.0.tgz").write_bytes(b"npm-launcher")
    (npm_dir / "apgr-darwin-arm64-0.13.0.tgz").write_bytes(b"npm-darwin")
    (npm_dir / "apgr-linux-x64-0.13.0.tgz").write_bytes(b"npm-x64")
    (npm_dir / "apgr-linux-arm64-0.13.0.tgz").write_bytes(b"npm-arm64")
    # manifests
    (bundle_dir / "apg-distribution-manifest.json").write_bytes(b'{"deliverable_count":11}\n')
    (bundle_dir / "SHA256SUMS").write_bytes(b"checksums\n")


def test_bundle_seal_lifecycle_and_reject_assets10(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle"
    _populate_canonical_11_bundle(bundle_dir)

    lane_seals = {
        "native-darwin-arm64": {"seal_sha256": "1" * 64},
        "native-linux-x64": {"seal_sha256": "2" * 64},
        "native-linux-arm64": {"seal_sha256": "3" * 64},
    }
    seal = build_bundle_seal(bundle_dir, "c" * 40, "t" * 40, lane_seals)
    assert seal["asset_count"] == 11
    verified = verify_bundle_seal(bundle_dir)
    assert verified["bundle_seal_sha256"] == seal["bundle_seal_sha256"]

    # Test asset count rejection (assets10: delete 1 npm tarball)
    (bundle_dir / "npm" / "apgr-linux-arm64-0.13.0.tgz").unlink()
    with pytest.raises(SealError, match="expected 11 deliverables"):
        build_bundle_seal(bundle_dir, "c" * 40, "t" * 40, lane_seals)


def test_receipt_builders_and_verifiers(tmp_path: Path) -> None:
    c_out = tmp_path / "consumer-receipt.json"
    c = build_consumer_receipt(
        "native-darwin-arm64", "darwin/arm64", "s" * 64, "c" * 40, "t" * 40,
        dict.fromkeys(("wheel_install_smoke", "foreign_wheel_rejected", "npm_install_smoke", "bundle_seal_verified"), "passed"), c_out
    )
    assert c["schema_version"] == CONSUMER_RECEIPT_SCHEMA
    verified_c = verify_consumer_receipt(c_out, expected_bundle_seal="s" * 64)
    assert verified_c["status"] == "passed"

    s_out = tmp_path / "scan-receipt.json"
    s = build_scan_receipt("s" * 64, 11, 14, "passed", "d" * 64, s_out)
    assert s["schema_version"] == SCAN_RECEIPT_SCHEMA
    verified_s = verify_scan_receipt(s_out, expected_bundle_seal="s" * 64)
    assert verified_s["asset_count"] == 11
    assert verified_s["scan_count"] == 14

    # Rejection of scans13
    with pytest.raises(SealError, match="14 scans"):
        build_scan_receipt("s" * 64, 11, 13, "passed", "d" * 64, s_out)


def test_write_github_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    gh_out = tmp_path / "github_output.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(gh_out))
    write_github_output("test_key", "test_val")
    assert gh_out.read_text(encoding="utf-8") == "test_key=test_val\n"


def test_native_seal_cli(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("RUNNER_OS", "Linux")
    monkeypatch.setenv("RUNNER_ARCH", "X64")
    lane_dir = tmp_path / "lane"
    lane_dir.mkdir()
    (lane_dir / "apgr").write_bytes(b"bin")
    (lane_dir / "apgr.binary-manifest.json").write_bytes(b"{}\n")
    (lane_dir / "go-version-m.txt").write_text("go\n", encoding="utf-8")
    (lane_dir / "nix-evidence.json").write_bytes(b"{}\n")
    (lane_dir / "nix-compiler-identity.txt").write_text("go1.26.9\n")
    (lane_dir / "go-tests.log").write_text("test/vet/race fixture\n")
    build_lane_seal("native-linux-x64", "linux/amd64", "linux-x64", "c" * 40, "t" * 40, lane_dir)

    exit_code = main(["verify-lane-seal", "--seal", str(lane_dir / "lane-seal.json"), "--lane", "native-linux-x64"])
    assert exit_code == 0
