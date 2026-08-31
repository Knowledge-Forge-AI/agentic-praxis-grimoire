"""Focused APG100 contracts for Python distribution assembly."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import gzip
import hashlib
import json
import os
import stat
import subprocess
import sys
import tarfile
import tempfile
import zipfile

import pytest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import apg_go_build as go_build  # noqa: E402
import apg_python_build_backend as backend  # noqa: E402
import apg_python_distribution as distribution  # noqa: E402
import apg_python_publication as publication  # noqa: E402


def _identity(
    root: Path,
    target: str,
    content: bytes = b"canonical-apgr",
    *,
    storage: Path | None = None,
) -> backend.BinaryIdentity:
    version, corpus = go_build.identities(root)
    manifest = go_build._manifest(
        target=target,
        version=version,
        corpus=corpus,
        binary=content,
    )
    path_root = root if storage is None else storage
    path_root.mkdir(parents=True, exist_ok=True)
    path = path_root / f"fake-{target.replace('/', '-')}.apgr"
    path.write_bytes(content)
    path.chmod(0o755)
    manifest_path = path_root / f"fake-{target.replace('/', '-')}.manifest.json"
    manifest_path.write_bytes(go_build.render_manifest(manifest))
    return backend.BinaryIdentity(path, manifest_path.read_bytes(), target)


def _raw_historical_sdist(path: Path) -> None:
    metadata = (
        b"Metadata-Version: 2.4\n"
        b"Name: agentic-praxis-grimoire\n"
        b"Version: 0.6.0\n"
        b"License-Expression: AGPL-3.0-or-later\n"
        b"Requires-Python: >=3.10\n\n"
    )
    payload = BytesIO()
    with gzip.GzipFile(fileobj=payload, mode="wb", mtime=7) as compressed:
        with tarfile.open(fileobj=compressed, mode="w") as archive:
            for name, content in (
                ("agentic_praxis_grimoire-0.6.0/PKG-INFO", metadata),
                ("agentic_praxis_grimoire-0.6.0/pyproject.toml", b"[build-system]\n"),
                (
                    "agentic_praxis_grimoire-0.6.0/src/agentic_praxis_grimoire/__init__.py",
                    b"",
                ),
            ):
                info = tarfile.TarInfo(name)
                info.size = len(content)
                info.mtime = 7
                info.uid = 7
                info.gid = 7
                archive.addfile(info, BytesIO(content))
    path.write_bytes(payload.getvalue())


def _historical_wheel(path: Path) -> None:
    metadata = (
        b"Metadata-Version: 2.4\n"
        b"Name: agentic-praxis-grimoire\n"
        b"Version: 0.6.0\n"
        b"License-Expression: AGPL-3.0-or-later\n"
        b"Requires-Python: >=3.10\n\n"
    )
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("agentic_praxis_grimoire/__init__.py", b"")
        archive.writestr("agentic_praxis_grimoire-0.6.0.dist-info/METADATA", metadata)
        archive.writestr(
            "agentic_praxis_grimoire-0.6.0.dist-info/WHEEL",
            b"Wheel-Version: 1.0\nTag: py3-none-any\n",
        )


def test_version_and_target_layout_are_derived_from_the_single_authority() -> None:
    assert publication.VERSION == (REPOSITORY_ROOT / "src/agentic_praxis_grimoire/VERSION").read_text().strip()
    assert publication.VERSION == "0.8.0"
    assert len(publication.WHEEL_NAMES) == 3
    assert all(name.startswith("agentic_praxis_grimoire-0.8.0-py3-none-") for name in publication.WHEEL_NAMES)
    assert publication.SDIST_NAME == "agentic_praxis_grimoire-0.8.0.tar.gz"
    assert "py3-none-any" not in " ".join(publication.WHEEL_NAMES)
    assert publication.TARGET_TAGS == backend.TARGET_TAGS


def test_backend_wheel_is_thin_platform_specific_and_recorded(tmp_path: Path) -> None:
    identity = _identity(REPOSITORY_ROOT, "darwin/arm64", storage=tmp_path)
    filename = backend._write_wheel(REPOSITORY_ROOT, identity.target, tmp_path, identity)
    wheel = tmp_path / filename
    publication._validate_wheel_structure(
        wheel,
        source=REPOSITORY_ROOT,
        target=identity.target,
        version=publication.VERSION,
    )
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        assert "agentic_praxis_grimoire/skills.py" not in names
        assert "agentic_praxis_grimoire/bin/apgr" in names
        assert "agentic_praxis_grimoire/bin/apgr.binary-manifest.json" in names
        wheel_text = archive.read(f"agentic_praxis_grimoire-0.8.0.dist-info/WHEEL").decode()
        assert "Root-Is-Purelib: false\n" in wheel_text
        assert f"Tag: py3-none-{backend.TARGET_TAGS[identity.target]}\n" in wheel_text
        mode = archive.getinfo("agentic_praxis_grimoire/bin/apgr").external_attr >> 16
        assert mode & 0o111


def test_backend_sdist_contains_source_but_no_binary_or_legacy_consumer(tmp_path: Path) -> None:
    filename = backend._write_sdist(REPOSITORY_ROOT, tmp_path)
    path = tmp_path / filename
    with tarfile.open(path, "r:gz") as archive:
        names = set(archive.getnames())
    root = "agentic_praxis_grimoire-0.8.0/"
    assert root + "go.mod" in names
    assert root + "libexec/apg_python_build_backend.py" in names
    assert root + "libexec/apg_go_build.py" in names
    assert root + "src/agentic_praxis_grimoire/VERSION" in names
    assert any(name.startswith(root + "skills/") and name.endswith("/SKILL.md") for name in names)
    assert any(name.startswith(root + "footprint/") for name in names)
    assert root + "src/agentic_praxis_grimoire/skills.py" not in names
    assert not any(name.endswith("/bin/apgr") for name in names)
    publication.validate_distributions(
        tmp_path
        / backend._write_wheel(
            REPOSITORY_ROOT,
            "darwin/arm64",
            tmp_path,
            _identity(REPOSITORY_ROOT, "darwin/arm64", storage=tmp_path),
        ),
        path,
        target="darwin/arm64",
    )


def test_extracted_sdist_builds_the_same_host_wheel_bytes(tmp_path: Path) -> None:
    direct = tmp_path / "direct"
    extracted_root = tmp_path / "extracted"
    extracted_output = tmp_path / "extracted-wheel"
    direct.mkdir()
    extracted_root.mkdir()
    extracted_output.mkdir()
    sdist_name = backend._write_sdist(REPOSITORY_ROOT, tmp_path)
    with tarfile.open(tmp_path / sdist_name, "r:gz") as archive:
        archive.extractall(extracted_root, filter="data")
    extracted = extracted_root / "agentic_praxis_grimoire-0.8.0"
    target = backend._host_target()
    direct_name = backend.build_wheel(str(direct), {"build-target": target})
    code = (
        "import apg_python_build_backend as b; "
        f"print(b.build_wheel({str(extracted_output)!r}, {{'build-target': {target!r}}}))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=extracted,
        env={**os.environ, "PYTHONPATH": str(extracted / "libexec")},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    extracted_name = completed.stdout.strip()
    assert (direct / direct_name).read_bytes() == (extracted_output / extracted_name).read_bytes()


def test_bundle_builds_three_targets_twice_and_reuses_exact_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = backend._build_binary

    def fake_build(root: Path, target: str, output: Path) -> backend.BinaryIdentity:
        identity = _identity(
            root,
            target,
            f"canonical-{target}".encode(),
            storage=output.parent,
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(identity.path.read_bytes())
        output.chmod(0o700)
        return backend.BinaryIdentity(output, identity.manifest, target)

    monkeypatch.setattr(backend, "_build_binary", fake_build)
    try:
        work = tmp_path / "work"
        work.mkdir()
        output = tmp_path / "bundle"
        result = publication.build_bundle(REPOSITORY_ROOT, output, work, Path(sys.executable))
    finally:
        monkeypatch.setattr(backend, "_build_binary", original)
    assert tuple(path.name for path in result) == publication.BUNDLE_NAMES
    publication.validate_bundle(output)
    assert (output / publication.CHECKSUM_NAME).read_text(encoding="ascii").count("\n") == 4
    assert all((output / name).stat().st_mode & 0o777 == 0o644 for name in publication.BUNDLE_NAMES[:-1])


def test_manifest_and_archive_tampering_fails_closed(tmp_path: Path) -> None:
    identity = _identity(REPOSITORY_ROOT, "darwin/arm64", storage=tmp_path)
    wheel_name = backend._write_wheel(REPOSITORY_ROOT, identity.target, tmp_path, identity)
    wheel = tmp_path / wheel_name
    tampered = tmp_path / "tampered.whl"
    with zipfile.ZipFile(wheel) as source, zipfile.ZipFile(tampered, "w") as destination:
        for member in source.infolist():
            content = b"tampered" if member.filename == "agentic_praxis_grimoire/bin/apgr" else source.read(member)
            destination.writestr(member, content)
    tampered.replace(wheel)
    with pytest.raises(publication.PublicationError, match="duplicate|RECORD|manifest"):
        publication._validate_wheel_structure(
            wheel,
            source=REPOSITORY_ROOT,
            target=identity.target,
            version=publication.VERSION,
        )


def test_historical_v06_validation_remains_available(tmp_path: Path) -> None:
    wheel = tmp_path / publication.HISTORICAL_V06_WHEEL_NAME
    raw = tmp_path / "raw.tar.gz"
    sdist = tmp_path / publication.HISTORICAL_V06_SDIST_NAME
    _historical_wheel(wheel)
    _raw_historical_sdist(raw)
    distribution.normalize_archive(raw, sdist, distribution.V06_RELEASE_EPOCH)
    raw.unlink()
    (tmp_path / "SHA256SUMS").write_bytes(publication.checksum_bytes(tmp_path, historical=True))
    assert len(publication.validate_v06_bundle(tmp_path)) == 3
    # The old call shape remains a compatibility alias for reconstruction.
    assert len(publication.validate_bundle(tmp_path)) == 3


def test_unsafe_archive_names_are_rejected() -> None:
    for name in ("", "/absolute", "back\\slash", "../escape", "root/./member"):
        with pytest.raises(publication.PublicationError, match="unsafe member"):
            publication._safe_archive_name(name)


def test_binary_manifest_identity_refusals_are_complete(tmp_path: Path) -> None:
    identity = _identity(REPOSITORY_ROOT, "darwin/arm64", storage=tmp_path)
    binary = identity.path.read_bytes()
    original = json.loads(identity.manifest)
    mutations = (
        ("version", "9.9.9", "version"),
        ("target", {**original["target"], "goarch": "amd64"}, "target"),
        ("sha256", "0" * 64, "SHA-256"),
        ("size_bytes", len(binary) + 1, "size"),
        ("corpus_fingerprint", "0" * 64, "corpus"),
        ("schema_version", "unknown/v1", "schema"),
        ("module_path", "wrong/module", "module"),
        ("build_info_schema", "unknown/v1", "build-info schema"),
        ("build_flags", ["-wrong"], "build flags"),
        ("binary_name", "wrong-name", "binary name"),
        ("build_identity", {**original["build_identity"], "version": "wrong"}, "build identity"),
    )
    for field, value, message in mutations:
        manifest = dict(original)
        manifest[field] = value
        raw = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        with pytest.raises(publication.PublicationError, match=message):
            publication._validate_manifest(
                raw,
                binary,
                source=REPOSITORY_ROOT,
                target="darwin/arm64",
                version="0.8.0",
            )

    # Extra key
    with pytest.raises(publication.PublicationError, match="fields do not match"):
        extra = dict(original)
        extra["unexpected_field"] = "unexpected"
        raw = json.dumps(extra, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        publication._validate_manifest(
            raw,
            binary,
            source=REPOSITORY_ROOT,
            target="darwin/arm64",
            version="0.8.0",
        )

    # Missing key
    with pytest.raises(publication.PublicationError, match="fields do not match"):
        missing = dict(original)
        del missing["binary_name"]
        raw = json.dumps(missing, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        publication._validate_manifest(
            raw,
            binary,
            source=REPOSITORY_ROOT,
            target="darwin/arm64",
            version="0.7.0",
        )

    with pytest.raises(publication.PublicationError, match="malformed"):
        publication._validate_manifest(
            b"{",
            binary,
            source=REPOSITORY_ROOT,
            target="darwin/arm64",
            version="0.7.0",
        )
    with pytest.raises(publication.PublicationError, match="JSON object"):
        publication._validate_manifest(
            b"[]\n",
            binary,
            source=REPOSITORY_ROOT,
            target="darwin/arm64",
            version="0.7.0",
        )
    noncanonical = json.dumps(original, indent=2).encode() + b"\n"
    with pytest.raises(publication.PublicationError, match="not canonical"):
        publication._validate_manifest(
            noncanonical,
            binary,
            source=REPOSITORY_ROOT,
            target="darwin/arm64",
            version="0.7.0",
        )


def test_publication_path_and_metadata_refusals_are_explicit(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    with pytest.raises(publication.PublicationError, match="unavailable"):
        publication._regular(missing, "fixture")
    directory = tmp_path / "directory"
    directory.mkdir()
    with pytest.raises(publication.PublicationError, match="regular file"):
        publication._regular(directory, "fixture")
    with pytest.raises(publication.PublicationError, match="unavailable"):
        publication._directory(missing, "fixture")
    regular = tmp_path / "regular"
    regular.write_bytes(b"fixture")
    with pytest.raises(publication.PublicationError, match="directory"):
        publication._directory(regular, "fixture")
    nonexecutable = tmp_path / "python"
    nonexecutable.write_bytes(b"fixture")
    nonexecutable.chmod(0o600)
    with pytest.raises(publication.PublicationError, match="executable"):
        publication._executable(nonexecutable)

    malformed_source = tmp_path / "source"
    version = malformed_source / "src/agentic_praxis_grimoire/VERSION"
    version.parent.mkdir(parents=True)
    version.write_text("0.8.0 candidate\n", encoding="ascii")
    with pytest.raises(publication.PublicationError, match="malformed"):
        publication._source_version(malformed_source)

    with pytest.raises(publication.PublicationError, match="metadata"):
        publication._metadata_contract(
            b"Name: wrong\nVersion: 0.8.0\nRequires-Python: >=3.10\nLicense-Expression: AGPL-3.0-or-later\n\n",
            "fixture",
        )


def test_wheel_metadata_archive_refusals_are_explicit(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.whl"
    malformed.write_bytes(b"not a zip")
    with pytest.raises(publication.PublicationError, match="malformed"):
        publication._wheel_metadata(malformed)

    missing = tmp_path / "missing.whl"
    with zipfile.ZipFile(missing, "w") as archive:
        archive.writestr("package/module.py", b"")
    with pytest.raises(publication.PublicationError, match="one exact METADATA"):
        publication._wheel_metadata(missing)

    duplicate = tmp_path / "duplicate.whl"
    metadata_name = "agentic_praxis_grimoire-0.8.0.dist-info/METADATA"
    with pytest.warns(UserWarning, match="Duplicate name"):
        with zipfile.ZipFile(duplicate, "w") as archive:
            archive.writestr(metadata_name, b"first")
            archive.writestr(metadata_name, b"second")
    with pytest.raises(publication.PublicationError, match="duplicate"):
        publication._wheel_metadata(duplicate)

    unsafe = tmp_path / "unsafe.whl"
    info = zipfile.ZipInfo("unsafe")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(unsafe, "w") as archive:
        archive.writestr(info, b"target")
    with pytest.raises(publication.PublicationError, match="unsupported member"):
        publication._wheel_metadata(unsafe)


def test_sdist_structure_and_comparison_refusals_are_explicit(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.tar.gz"
    malformed.write_bytes(b"not a tarball")
    with pytest.raises(publication.PublicationError, match="malformed"):
        publication._sdist_metadata(malformed)

    wrong_root = tmp_path / publication.SDIST_NAME
    with tarfile.open(wrong_root, "w:gz") as archive:
        content = b"metadata"
        info = tarfile.TarInfo("wrong/PKG-INFO")
        info.size = len(content)
        archive.addfile(info, BytesIO(content))
    with pytest.raises(publication.PublicationError, match="archive root"):
        publication._sdist_metadata(wrong_root)

    incomplete = tmp_path / "incomplete.tar.gz"
    root = "agentic_praxis_grimoire-0.8.0"
    with tarfile.open(incomplete, "w:gz") as archive:
        info = tarfile.TarInfo(f"{root}/PKG-INFO")
        info.size = 0
        archive.addfile(info, BytesIO())
    with pytest.raises(publication.PublicationError, match="complete Go/Python"):
        publication._validate_sdist_sources(incomplete, version="0.8.0")

    required_only = tmp_path / "required-only.tar.gz"
    required = (
        "go.mod",
        "pyproject.toml",
        "libexec/apg_go_build.py",
        "libexec/apg_python_build_backend.py",
        "src/agentic_praxis_grimoire/VERSION",
    )
    with tarfile.open(required_only, "w:gz") as archive:
        for relative in required:
            info = tarfile.TarInfo(f"{root}/{relative}")
            info.size = 0
            archive.addfile(info, BytesIO())
    with pytest.raises(publication.PublicationError, match="canonical skill"):
        publication._validate_sdist_sources(required_only, version="0.8.0")

    without_footprint = tmp_path / "without-footprint.tar.gz"
    with tarfile.open(without_footprint, "w:gz") as archive:
        for relative in (*required, "skills/example/SKILL.md"):
            info = tarfile.TarInfo(f"{root}/{relative}")
            info.size = 0
            archive.addfile(info, BytesIO())
    with pytest.raises(publication.PublicationError, match="canonical footprint"):
        publication._validate_sdist_sources(without_footprint, version="0.8.0")

    with_footprint = tmp_path / "with-footprint.tar.gz"
    with tarfile.open(with_footprint, "w:gz") as archive:
        for relative in (*required, "skills/example/SKILL.md", "footprint/doc.go"):
            info = tarfile.TarInfo(f"{root}/{relative}")
            info.size = 0
            archive.addfile(info, BytesIO())
    publication._validate_sdist_sources(with_footprint, version="0.8.0")

    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "asset").write_bytes(b"first")
    (second / "asset").write_bytes(b"second")
    with pytest.raises(publication.PublicationError, match="byte reproducible"):
        publication._compare(first, second, ("asset",))
    (second / "asset").write_bytes(b"first")
    (first / "asset").chmod(0o600)
    (second / "asset").chmod(0o644)
    with pytest.raises(publication.PublicationError, match="mode is not reproducible"):
        publication._compare(first, second, ("asset",))


def test_release_workflow_targets_current_version_and_tag() -> None:
    workflow = json.loads(
        (REPOSITORY_ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    )
    command = workflow["jobs"]["publish"]["steps"][0]["run"]
    assert "expected_tag=v0.8.0" in command
    assert "expected_version=0.8.0" in command


def test_backend_manifest_and_configuration_refusals_are_complete(tmp_path: Path) -> None:
    identity = _identity(REPOSITORY_ROOT, "darwin/arm64", storage=tmp_path)
    original = json.loads(identity.manifest)
    mutations = (
        ("schema_version", "unknown/v1", "schema"),
        ("build_info_schema", "unknown/v1", "build-info"),
        ("build_identity", {}, "build identity"),
        ("module_path", "wrong", "release identity"),
        ("binary_name", "wrong", "binary/corpus"),
        ("size_bytes", 0, "packaged binary"),
        ("target", {**original["target"], "goarch": "amd64"}, "requested target"),
    )
    for field, value, message in mutations:
        manifest = dict(original)
        manifest[field] = value
        raw = backend._canonical_json(manifest)
        with pytest.raises(backend.BackendError, match=message):
            backend._validated_manifest(
                REPOSITORY_ROOT,
                "darwin/arm64",
                identity.path,
                raw,
            )

    with pytest.raises(backend.BackendError, match="malformed"):
        backend._validated_manifest(REPOSITORY_ROOT, "darwin/arm64", identity.path, b"{")
    with pytest.raises(backend.BackendError, match="JSON object"):
        backend._validated_manifest(REPOSITORY_ROOT, "darwin/arm64", identity.path, b"[]\n")
    with pytest.raises(backend.BackendError, match="fields"):
        backend._validated_manifest(REPOSITORY_ROOT, "darwin/arm64", identity.path, b"{}\n")
    with pytest.raises(backend.BackendError, match="not canonical"):
        backend._validated_manifest(
            REPOSITORY_ROOT,
            "darwin/arm64",
            identity.path,
            json.dumps(original, indent=2).encode() + b"\n",
        )

    assert backend._config_value({"--value": ["first", "last"]}, "value") == "last"
    assert backend._config_value({"value": []}, "value") is None
    assert backend._config_value(None, "value") is None
    with pytest.raises(backend.BackendError, match="unsupported APGR target"):
        backend._target("plan9/amd64")
    with pytest.raises(backend.BackendError, match="supplied together"):
        backend._provided_binary(REPOSITORY_ROOT, "darwin/arm64", str(identity.path), None)
    with pytest.raises(backend.BackendError, match="must be executable"):
        identity.path.chmod(0o600)
        backend._direct_file(identity.path, "fixture", executable=True)
    with pytest.raises(backend.BackendError, match="ambiguous"):
        backend._dist_info_from_entries({})
    with pytest.raises(backend.BackendError, match="release contract"):
        backend.build_editable(str(tmp_path))
