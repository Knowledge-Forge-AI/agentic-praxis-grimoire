"""Prebuilt Python platform distribution candidate builder and validator.

Assembles three platform wheels, one normalized source distribution, and
SHA256SUMS from previously compiled and validated Go CLI binaries without
invoking any Go compiler or subprocess during packaging or validation.
"""

from __future__ import annotations

import os
import zipfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import apg_distribution_candidate_contract as candidate_contract
import apg_go_build
import apg_go_buildinfo
import apg_python_distribution as distribution
import apg_python_publication as publication


def _find_target_directory(artifact_root: Path, target: str) -> Path:
    slug = target.replace("/", "-")
    candidate1 = artifact_root / slug
    if candidate1.is_dir() and not candidate1.is_symlink():
        return candidate1
    candidate2 = artifact_root / target
    if candidate2.is_dir() and not candidate2.is_symlink():
        return candidate2
    raise publication.PublicationError(
        f"artifact directory for target {target} not found in {artifact_root}"
    )


def _find_target_manifest(target_dir: Path, target: str) -> Path:
    candidates = (
        target_dir / "apgr.binary-manifest.json",
        target_dir / "manifest.json",
        target_dir / "binary-manifest.json",
    )
    for candidate in candidates:
        if candidate.is_file() and not candidate.is_symlink():
            return candidate
    raise publication.PublicationError(
        f"prebuilt binary manifest missing for target {target} in {target_dir}"
    )


def _build_prebuilt_once(
    source: Path,
    root: Path,
    seed: str,
    identities: Mapping[str, Any],
) -> Path:
    build_root = root / f"build-{seed}"
    final = build_root / "publication"
    build_root.mkdir(mode=0o700)
    final.mkdir(mode=0o700)
    backend = publication._backend(source)
    for target in publication.SUPPORTED_TARGETS:
        identity = identities[target]
        wheel_name = backend._write_wheel(source, target, final, identity)
        wheel = final / wheel_name
        if not wheel.is_file():
            publication._fail("Python backend did not create the expected target wheel")
    backend._write_sdist(source, final)
    return final


def _validate_wheel_prebuilt_binary(
    wheel_path: Path,
    target: str,
    expected_binary: bytes,
    expected_manifest: bytes,
) -> None:
    try:
        with zipfile.ZipFile(wheel_path) as archive:
            binary_name = "agentic_praxis_grimoire/bin/apgr"
            manifest_name = "agentic_praxis_grimoire/bin/apgr.binary-manifest.json"
            if binary_name not in archive.namelist():
                publication._fail(f"wheel {wheel_path.name} is missing binary {binary_name}")
            if manifest_name not in archive.namelist():
                publication._fail(f"wheel {wheel_path.name} is missing manifest {manifest_name}")
            actual_binary = archive.read(binary_name)
            actual_manifest = archive.read(manifest_name)
            if actual_binary != expected_binary:
                publication._fail(
                    f"packaged binary in {wheel_path.name} differs from supplied prebuilt binary"
                )
            if actual_manifest != expected_manifest:
                publication._fail(
                    f"packaged manifest in {wheel_path.name} differs from supplied manifest"
                )
    except (OSError, zipfile.BadZipFile) as error:
        raise publication.PublicationError(f"wheel {wheel_path.name} is malformed") from error


def build_prebuilt_bundle(
    source: Path,
    artifact_root: Path,
    output: Path,
    work_root: Path,
) -> dict[str, Any]:
    """Assemble deterministic Python wheels and sdist from prebuilt Go binaries.

    Validates prebuilt Go binaries against Go 1.18+ inline build info, the
    shared actual-byte deployment predicate, and binary manifests without
    invoking Go or any compilation subprocess.
    Ensures A/B byte-for-byte reproducibility across all artifacts.
    """
    source_root = publication._directory(source, "publication source")
    artifacts = publication._directory(artifact_root, "prebuilt artifacts root")
    work = publication._directory(work_root, "publication work root")

    if output.exists() or output.is_symlink():
        publication._fail("publication output must not already exist")
    try:
        output_parent = output.parent.resolve(strict=True)
    except OSError as error:
        raise publication.PublicationError("publication output parent is unavailable") from error
    if output.parent.is_symlink():
        publication._fail("publication output parent must be one real direct directory")
    if work.stat().st_dev != output_parent.stat().st_dev:
        publication._fail("publication output and work root must share one filesystem")
    if any((work / f"build-{seed}").exists() for seed in ("a", "b")):
        publication._fail("publication build roots must not already exist")

    selected_layout = publication.layout(source_root)
    try:
        selected_epoch = distribution.release_epoch(selected_layout.version)
    except distribution.NormalizationError as error:
        raise publication.PublicationError(
            "publication version has no reproducible release epoch"
        ) from error

    identities: dict[str, Any] = {}
    supplied_binaries: dict[str, bytes] = {}
    supplied_manifests: dict[str, bytes] = {}
    backend = publication._backend(source_root)

    for target in publication.SUPPORTED_TARGETS:
        target_dir = _find_target_directory(artifacts, target)
        binary_path = target_dir / "apgr"
        publication._regular(binary_path, f"prebuilt binary for {target}")
        manifest_path = _find_target_manifest(target_dir, target)
        publication._regular(manifest_path, f"prebuilt binary manifest for {target}")

        recorded_path = target_dir / "go-version-m.txt"
        recorded_text: str | None = None
        if recorded_path.is_file() and not recorded_path.is_symlink():
            try:
                recorded_text = recorded_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as error:
                raise publication.PublicationError(
                    f"recorded go version metadata is unreadable for {target}"
                ) from error

        try:
            apg_go_buildinfo.validate(binary_path, target, recorded=recorded_text)
        except apg_go_buildinfo.BuildInfoError as error:
            raise publication.PublicationError(
                f"prebuilt Go binary build info failed validation for {target}: {error}"
            ) from error
        binary_bytes = binary_path.read_bytes()
        try:
            apg_go_build.require_release_deployment(target, binary_bytes)
        except apg_go_build.BuildError as error:
            raise publication.PublicationError(
                f"prebuilt Go binary deployment failed validation for {target}: {error}"
            ) from error

        try:
            identity = backend._provided_binary(
                source_root,
                target,
                os.fspath(binary_path),
                os.fspath(manifest_path),
            )
        except Exception as error:
            raise publication.PublicationError(
                f"prebuilt binary validation failed for {target}: {error}"
            ) from error
        if identity is None:
            raise publication.PublicationError(
                f"prebuilt binary could not be loaded for {target}"
            )

        identities[target] = identity
        supplied_binaries[target] = binary_bytes
        supplied_manifests[target] = manifest_path.read_bytes()

    with publication._release_epoch_environment(selected_epoch):
        first = _build_prebuilt_once(source_root, work, "a", identities)
        second = _build_prebuilt_once(source_root, work, "b", identities)

    publication._compare(first, second, selected_layout.artifact_names)
    expected = set(selected_layout.artifact_names)
    if {entry.name for entry in first.iterdir()} != expected:
        publication._fail("Python build output contains unexpected assets")

    final = work / "build-a" / "publication"
    (final / selected_layout.checksum_name).write_bytes(
        publication.checksum_bytes(final, source=source_root)
    )
    (final / selected_layout.checksum_name).chmod(0o600)
    second_checksum = work / "build-b" / "publication" / selected_layout.checksum_name
    second_checksum.write_bytes(
        publication.checksum_bytes(work / "build-b" / "publication", source=source_root)
    )
    second_checksum.chmod(0o600)
    publication._compare(final, work / "build-b" / "publication", selected_layout.bundle_names)

    os.replace(final, output)
    bundle_paths = publication.validate_bundle(output, source=source_root)

    for target in publication.SUPPORTED_TARGETS:
        wheel_name = candidate_contract.python_wheel_filename(target, selected_layout.version)
        _validate_wheel_prebuilt_binary(
            output / wheel_name,
            target,
            supplied_binaries[target],
            supplied_manifests[target],
        )

    return {
        "artifacts": [os.fspath(p) for p in bundle_paths],
        "bundle_dir": os.fspath(output),
        "bundle_names": list(selected_layout.bundle_names),
        "checksums": (output / selected_layout.checksum_name).read_text(encoding="ascii"),
        "files": {p.name: publication._sha256(p) for p in bundle_paths},
        "paths": bundle_paths,
        "status": "ok",
        "version": selected_layout.version,
    }
