"""Unit tests for prebuilt Python platform distribution candidate builder."""

from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path

import pytest

from src.test.apg_test_support import repository_root

REPOSITORY_ROOT = repository_root(__file__)
import sys

sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import apg_go_build as go_build
import apg_go_buildinfo as buildinfo
import apg_python_build_backend as backend
import apg_python_prebuilt_publication as prebuilt_pub
import apg_python_publication as publication


def _make_artifacts(
    artifacts_root: Path,
    source: Path,
    *,
    tamper_binary: str | None = None,
    tamper_manifest: str | None = None,
    tamper_buildinfo: str | None = None,
    tamper_recorded: str | None = None,
    missing_target: str | None = None,
    missing_file: tuple[str, str] | None = None,  # (target, "binary" | "manifest")
    include_recorded: bool = True,
) -> None:
    version, corpus = go_build.identities(source)
    for target in publication.SUPPORTED_TARGETS:
        if missing_target == target:
            continue
        slug = target.replace("/", "-")
        target_dir = artifacts_root / slug
        target_dir.mkdir(parents=True, exist_ok=True)

        fmt = "macho" if target.startswith("darwin") else "elf"
        go_ver = "go1.25.10" if tamper_buildinfo == target else "go1.26.9"
        bin_data = buildinfo.make_synthetic_binary(target=target, go_version=go_ver, format_type=fmt)

        binary_path = target_dir / "apgr"
        if missing_file != (target, "binary"):
            actual_data = (bin_data + b"\xff") if tamper_binary == target else bin_data
            binary_path.write_bytes(actual_data)
            binary_path.chmod(0o755)

        manifest = go_build._manifest(
            target=target,
            version=version,
            corpus=corpus,
            binary=bin_data,  # manifest hashes bin_data
        )
        if tamper_manifest == target:
            manifest["version"] = "9.9.9"

        manifest_path = target_dir / "apgr.binary-manifest.json"
        if missing_file != (target, "manifest"):
            manifest_path.write_bytes(go_build.render_manifest(manifest))

        if include_recorded:
            goos, goarch = target.split("/", 1)
            recorded_arch = "wrongarch" if tamper_recorded == target else goarch
            recorded_text = (
                f"{binary_path}: {go_ver}\n"
                f"	path	{go_build.MODULE}/cmd/apgr\n"
                f"	mod	{go_build.MODULE}	(devel)	\n"
                f"	build	-buildvcs=false\n"
                f"	build	-trimpath=true\n"
                f"	build	CGO_ENABLED=0\n"
                f"	build	GOARCH={recorded_arch}\n"
                f"	build	GOOS={goos}\n"
            )
            (target_dir / "go-version-m.txt").write_text(recorded_text, encoding="utf-8")


def test_build_prebuilt_bundle_success_and_reproducibility(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = REPOSITORY_ROOT
    artifacts_root = tmp_path / "artifacts"
    _make_artifacts(artifacts_root, source)

    # Strictly assert that compilation seams are never invoked
    def fail_compile(*_args, **_kwargs):
        pytest.fail("Compilation seam invoked in prebuilt publication build")

    monkeypatch.setattr(backend, "_build_binary", fail_compile)
    monkeypatch.setattr(go_build, "build", fail_compile)
    monkeypatch.setattr(subprocess, "run", fail_compile)
    monkeypatch.setattr(subprocess, "Popen", fail_compile)

    work_a = tmp_path / "work-a"
    work_a.mkdir()
    output_a = tmp_path / "output-a"

    result = prebuilt_pub.build_prebuilt_bundle(source, artifacts_root, output_a, work_a)
    assert result["status"] == "ok"
    assert result["version"] == publication.VERSION
    assert output_a.is_dir()

    # Canonical 3 wheels, 1 sdist, 1 SHA256SUMS
    expected_layout = publication.layout(source)
    assert set(result["bundle_names"]) == set(expected_layout.bundle_names)
    assert set(result["files"]) == set(expected_layout.bundle_names)
    for name in expected_layout.bundle_names:
        assert (output_a / name).is_file()

    # Validate bundle passes canonical publication validation
    paths = publication.validate_bundle(output_a, source=source)
    assert len(paths) == len(expected_layout.bundle_names)

    # Check packaged wheel contents match supplied binaries
    for target in publication.SUPPORTED_TARGETS:
        slug = target.replace("/", "-")
        supplied_bin = (artifacts_root / slug / "apgr").read_bytes()
        supplied_manifest = (artifacts_root / slug / "apgr.binary-manifest.json").read_bytes()
        tag = publication.TARGET_TAGS[target]
        wheel_name = f"{publication.DIST_NAME}-{publication.VERSION}-py3-none-{tag}.whl"
        with zipfile.ZipFile(output_a / wheel_name) as archive:
            assert archive.read("agentic_praxis_grimoire/bin/apgr") == supplied_bin
            assert archive.read("agentic_praxis_grimoire/bin/apgr.binary-manifest.json") == supplied_manifest

    # Test A/B byte-for-byte reproducibility
    work_b = tmp_path / "work-b"
    work_b.mkdir()
    output_b = tmp_path / "output-b"
    result_b = prebuilt_pub.build_prebuilt_bundle(source, artifacts_root, output_b, work_b)

    for name in expected_layout.bundle_names:
        assert (output_a / name).read_bytes() == (output_b / name).read_bytes()
        assert result["files"][name] == result_b["files"][name]


def test_build_prebuilt_bundle_missing_inputs(tmp_path: Path) -> None:
    source = REPOSITORY_ROOT

    # Missing target directory
    artifacts_missing_target = tmp_path / "artifacts-missing-target"
    _make_artifacts(artifacts_missing_target, source, missing_target="linux/amd64")
    work = tmp_path / "work1"
    work.mkdir()
    with pytest.raises(publication.PublicationError, match="artifact directory for target linux/amd64 not found"):
        prebuilt_pub.build_prebuilt_bundle(source, artifacts_missing_target, tmp_path / "out1", work)

    # Missing binary
    artifacts_missing_bin = tmp_path / "artifacts-missing-bin"
    _make_artifacts(artifacts_missing_bin, source, missing_file=("darwin/arm64", "binary"))
    work = tmp_path / "work2"
    work.mkdir()
    with pytest.raises(publication.PublicationError, match="prebuilt binary for darwin/arm64 is unavailable"):
        prebuilt_pub.build_prebuilt_bundle(source, artifacts_missing_bin, tmp_path / "out2", work)

    # Missing manifest
    artifacts_missing_man = tmp_path / "artifacts-missing-man"
    _make_artifacts(artifacts_missing_man, source, missing_file=("linux/arm64", "manifest"))
    work = tmp_path / "work3"
    work.mkdir()
    with pytest.raises(publication.PublicationError, match="prebuilt binary manifest missing for target linux/arm64"):
        prebuilt_pub.build_prebuilt_bundle(source, artifacts_missing_man, tmp_path / "out3", work)


def test_build_prebuilt_bundle_tampered_inputs(tmp_path: Path) -> None:
    source = REPOSITORY_ROOT

    # Tampered binary bytes (hash mismatch against manifest)
    artifacts_tampered_bin = tmp_path / "artifacts-tampered-bin"
    _make_artifacts(artifacts_tampered_bin, source, tamper_binary="linux/amd64")
    work = tmp_path / "work1"
    work.mkdir()
    with pytest.raises(publication.PublicationError, match="prebuilt binary validation failed"):
        prebuilt_pub.build_prebuilt_bundle(source, artifacts_tampered_bin, tmp_path / "out1", work)

    # Tampered manifest (wrong version)
    artifacts_tampered_man = tmp_path / "artifacts-tampered-man"
    _make_artifacts(artifacts_tampered_man, source, tamper_manifest="darwin/arm64")
    work = tmp_path / "work2"
    work.mkdir()
    with pytest.raises(publication.PublicationError, match="prebuilt binary validation failed"):
        prebuilt_pub.build_prebuilt_bundle(source, artifacts_tampered_man, tmp_path / "out2", work)

    # Tampered buildinfo in binary (wrong Go compiler version)
    artifacts_tampered_bi = tmp_path / "artifacts-tampered-bi"
    _make_artifacts(artifacts_tampered_bi, source, tamper_buildinfo="linux/arm64")
    work = tmp_path / "work3"
    work.mkdir()
    with pytest.raises(publication.PublicationError, match="prebuilt Go binary build info failed validation"):
        prebuilt_pub.build_prebuilt_bundle(source, artifacts_tampered_bi, tmp_path / "out3", work)

    # Tampered recorded go-version-m.txt (disagrees with binary)
    artifacts_tampered_rec = tmp_path / "artifacts-tampered-rec"
    _make_artifacts(artifacts_tampered_rec, source, tamper_recorded="linux/amd64")
    work = tmp_path / "work4"
    work.mkdir()
    with pytest.raises(publication.PublicationError, match="recorded setting GOARCH='wrongarch' does not match"):
        prebuilt_pub.build_prebuilt_bundle(source, artifacts_tampered_rec, tmp_path / "out4", work)


def test_build_prebuilt_bundle_output_and_filesystem_guards(tmp_path: Path) -> None:
    source = REPOSITORY_ROOT
    artifacts_root = tmp_path / "artifacts"
    _make_artifacts(artifacts_root, source)
    work = tmp_path / "work"
    work.mkdir()

    # Output already exists
    existing = tmp_path / "existing-out"
    existing.mkdir()
    with pytest.raises(publication.PublicationError, match="publication output must not already exist"):
        prebuilt_pub.build_prebuilt_bundle(source, artifacts_root, existing, work)

    # Build roots already exist
    (work / "build-a").mkdir()
    with pytest.raises(publication.PublicationError, match="publication build roots must not already exist"):
        prebuilt_pub.build_prebuilt_bundle(source, artifacts_root, tmp_path / "out", work)


def test_cli_build_prebuilt_subcommand(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    source = REPOSITORY_ROOT
    artifacts_root = tmp_path / "artifacts"
    _make_artifacts(artifacts_root, source)

    def fail_compile(*_args, **_kwargs):
        pytest.fail("Compilation seam invoked in CLI prebuilt build")

    monkeypatch.setattr(backend, "_build_binary", fail_compile)
    monkeypatch.setattr(go_build, "build", fail_compile)
    monkeypatch.setattr(subprocess, "run", fail_compile)

    work = tmp_path / "cli-work"
    work.mkdir()
    output = tmp_path / "cli-output"

    code = publication.main(
        [
            "build-prebuilt",
            "--source",
            str(source),
            "--artifacts",
            str(artifacts_root),
            "--output",
            str(output),
            "--work-root",
            str(work),
        ]
    )
    assert code == 0
    stdout = capsys.readouterr().out
    expected_layout = publication.layout(source)
    for name in expected_layout.bundle_names:
        assert name in stdout
