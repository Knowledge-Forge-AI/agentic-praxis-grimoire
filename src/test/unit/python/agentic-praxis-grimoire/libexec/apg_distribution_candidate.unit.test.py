"""Focused contracts for the path-free APG distribution candidate manifest."""

from __future__ import annotations

import base64
from io import BytesIO
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tarfile
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / "libexec"))

import apg_distribution_candidate as candidate  # noqa: E402


VERSION = "0.8.0"


def _source(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "source"
    resources = root / "src/agentic_praxis_grimoire/resources"
    resources.mkdir(parents=True)
    (root / "src/agentic_praxis_grimoire/VERSION").write_text(
        VERSION + "\n", encoding="ascii"
    )
    corpus_bytes = b'{"skills":[]}\n'
    (resources / "skill-metadata.json").write_bytes(corpus_bytes)
    return root, candidate._sha256(corpus_bytes)


def _binary_manifest(target: str, binary: bytes, corpus: str) -> bytes:
    return candidate.canonical_json(
        {
            "binary_name": candidate.BINARY_NAME,
            "build_flags": list(candidate.BUILD_FLAGS),
            "build_identity": {
                "corpus_fingerprint": corpus,
                "schema_version": candidate.BUILD_INFO_SCHEMA,
                "target": target,
                "version": VERSION,
            },
            "build_info_schema": candidate.BUILD_INFO_SCHEMA,
            "corpus_fingerprint": corpus,
            "module_path": candidate.MODULE,
            "schema_version": candidate.BINARY_MANIFEST_SCHEMA,
            "sha256": candidate._sha256(binary),
            "size_bytes": len(binary),
            "target": dict(candidate.TARGET_BY_GO[target]),
            "version": VERSION,
        }
    )


def _go_artifacts(tmp_path: Path, corpus: str, *, tamper: str | None = None) -> tuple[Path, dict[str, bytes]]:
    root = tmp_path / "go"
    binaries: dict[str, bytes] = {}
    for mapping in candidate.TARGETS:
        target = mapping["go_target"]
        binary = f"apgr-{target}\n".encode("ascii")
        binaries[target] = binary
        target_root = root / target.replace("/", "-")
        target_root.mkdir(parents=True)
        (target_root / "apgr").write_bytes(binary)
        (target_root / "apgr").chmod(0o700)
        manifest = _binary_manifest(target, binary, corpus)
        if tamper == target:
            value = json.loads(manifest)
            value["sha256"] = "0" * 64
            manifest = candidate.canonical_json(value)
        (target_root / "apgr.binary-manifest.json").write_bytes(manifest)
    return root, binaries


def _record(entries: dict[str, tuple[bytes, int]], info_name: str) -> bytes:
    rows: list[str] = []
    for name in sorted(entries):
        raw = entries[name][0]
        digest = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).rstrip(b"=").decode("ascii")
        rows.append(f"{name},sha256={digest},{len(raw)}")
    rows.append(f"{info_name}/RECORD,,")
    return ("\n".join(rows) + "\n").encode("ascii")


def _wheel(
    root: Path,
    target: str,
    binary: bytes,
    manifest: bytes,
    *,
    binary_override: bytes | None = None,
) -> Path:
    mapping = candidate.TARGET_BY_GO[target]
    name = f"{candidate.DIST_NAME}-{VERSION}-py3-none-{mapping['python_platform']}.whl"
    info = f"{candidate.DIST_NAME}-{VERSION}.dist-info"
    entries: dict[str, tuple[bytes, int]] = {
        "agentic_praxis_grimoire/__init__.py": (b"", 0o644),
        "agentic_praxis_grimoire/bin/apgr": (binary if binary_override is None else binary_override, 0o755),
        "agentic_praxis_grimoire/bin/apgr.binary-manifest.json": (manifest, 0o644),
        f"{info}/METADATA": (
            f"Metadata-Version: 2.4\nName: agentic-praxis-grimoire\nVersion: {VERSION}\n"
            "Requires-Python: >=3.10\nLicense-Expression: AGPL-3.0-or-later\n\n".encode("ascii"),
            0o644,
        ),
        f"{info}/WHEEL": (
            f"Wheel-Version: 1.0\nRoot-Is-Purelib: false\nTag: py3-none-{mapping['python_platform']}\n\n".encode("ascii"),
            0o644,
        ),
        f"{info}/licenses/LICENSE": (b"license", 0o644),
        f"{info}/licenses/NOTICE": (b"notice", 0o644),
        f"{info}/licenses/COMMERCIAL-LICENSE.md": (b"commercial", 0o644),
    }
    entries[f"{info}/RECORD"] = (_record(entries, info), 0o644)
    path = root / name
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for member, (raw, mode) in sorted(entries.items()):
            info_obj = zipfile.ZipInfo(member)
            info_obj.create_system = 3
            info_obj.external_attr = (stat.S_IFREG | mode) << 16
            archive.writestr(info_obj, raw)
    return path


def _sdist(root: Path) -> Path:
    path = root / f"{candidate.DIST_NAME}-{VERSION}.tar.gz"
    prefix = f"{candidate.DIST_NAME}-{VERSION}"
    entries = {
        f"{prefix}/PKG-INFO": (
            f"Metadata-Version: 2.4\nName: agentic-praxis-grimoire\nVersion: {VERSION}\n"
            "Requires-Python: >=3.10\nLicense-Expression: AGPL-3.0-or-later\n\n".encode("ascii")
        ),
        f"{prefix}/go.mod": b"module github.com/Knowledge-Forge-AI/agentic-praxis-grimoire\n",
        f"{prefix}/pyproject.toml": b"[build-system]\n",
        f"{prefix}/src/agentic_praxis_grimoire/VERSION": (VERSION + "\n").encode("ascii"),
        f"{prefix}/libexec/apg_go_build.py": b"# go builder\n",
        f"{prefix}/libexec/apg_python_build_backend.py": b"# backend\n",
        f"{prefix}/footprint/doc.go": b"package footprint\n",
        f"{prefix}/skills/example/SKILL.md": b"# canonical\n",
    }
    with path.open("wb") as stream:
        import gzip

        with gzip.GzipFile(fileobj=stream, mode="wb", filename="", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
                for name, raw in sorted(entries.items()):
                    info = tarfile.TarInfo(name)
                    info.type = tarfile.REGTYPE
                    info.mode = 0o644
                    info.size = len(raw)
                    archive.addfile(info, BytesIO(raw))
    return path


def _tgz(root: Path, package: str, version: str, files: dict[str, bytes]) -> Path:
    path = root / candidate._npm_tarball_name(package, version)
    with path.open("wb") as stream:
        import gzip

        with gzip.GzipFile(fileobj=stream, mode="wb", filename="", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as archive:
                for name, raw in sorted(files.items()):
                    info = tarfile.TarInfo("package/" + name)
                    info.type = tarfile.REGTYPE
                    info.mode = 0o755 if name in {"index.js", "bin/apgr"} else 0o644
                    info.size = len(raw)
                    archive.addfile(info, BytesIO(raw))
    return path


def _rewrite_wheel(
    source: Path,
    destination: Path,
    *,
    remove: str | None = None,
    replace: tuple[str, bytes] | None = None,
    mode: tuple[str, int] | None = None,
    add: tuple[str, bytes, int] | None = None,
    refresh_record: bool = False,
) -> None:
    with zipfile.ZipFile(source) as archive:
        entries = {
            member.filename: (archive.read(member), member.external_attr >> 16 & 0o777)
            for member in archive.infolist()
            if member.filename != remove
        }
    if replace is not None:
        entries[replace[0]] = (replace[1], entries[replace[0]][1])
    if mode is not None:
        entries[mode[0]] = (entries[mode[0]][0], mode[1])
    if add is not None:
        entries[add[0]] = (add[1], add[2])
    record_names = [name for name in entries if name.endswith(".dist-info/RECORD")]
    if refresh_record and len(record_names) == 1:
        record_name = record_names[0]
        info_name = record_name.rsplit("/", 1)[0]
        record_entries = {
            name: value for name, value in entries.items() if name != record_name
        }
        entries[record_name] = (_record(record_entries, info_name), 0o644)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, (raw, member_mode) in sorted(entries.items()):
            info = zipfile.ZipInfo(name)
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | member_mode) << 16
            archive.writestr(info, raw)


def _rewrite_sdist(
    source: Path,
    destination: Path,
    *,
    remove: str | None = None,
    replace: tuple[str, bytes] | None = None,
    mode: tuple[str, int] | None = None,
    add: tuple[str, bytes, int, bytes] | None = None,
) -> None:
    with tarfile.open(source, "r:gz") as archive:
        entries = [
            (member.name, archive.extractfile(member).read(), member.mode, member.type)
            for member in archive.getmembers()
            if member.isfile() and member.name != remove
        ]
    updated: list[tuple[str, bytes, int, bytes]] = []
    for name, raw, member_mode, member_type in entries:
        if replace is not None and name == replace[0]:
            raw = replace[1]
        if mode is not None and name == mode[0]:
            member_mode = mode[1]
        updated.append((name, raw, member_mode, member_type))
    if add is not None:
        updated.append(add)
    with tarfile.open(destination, "w:gz") as archive:
        for name, raw, member_mode, member_type in updated:
            info = tarfile.TarInfo(name)
            info.type = member_type
            info.mode = member_mode
            info.size = len(raw) if member_type == tarfile.REGTYPE else 0
            archive.addfile(info, BytesIO(raw) if member_type == tarfile.REGTYPE else None)


def _npm_artifacts(tmp_path: Path, corpus: str, binaries: dict[str, bytes]) -> Path:
    root = tmp_path / "npm"
    root.mkdir()
    licenses = {name: name.encode("ascii") for name in candidate.LICENSE_FILES}
    launcher_json = candidate.canonical_json(
        {
            "name": "@knowledge-forge-ai/apgr",
            "version": VERSION,
            "optionalDependencies": {
                mapping["npm_package"]: VERSION for mapping in candidate.TARGETS
            },
            "apg": {
                "binary_manifest_schema": candidate.BINARY_MANIFEST_SCHEMA,
                "corpus_fingerprint": corpus,
                "supported_targets": [mapping["go_target"] for mapping in candidate.TARGETS],
            },
        }
    )
    _tgz(
        root,
        "@knowledge-forge-ai/apgr",
        VERSION,
        {"package.json": launcher_json, "index.js": b"'use strict';\n", **licenses},
    )
    for mapping in candidate.TARGETS:
        target = mapping["go_target"]
        manifest = _binary_manifest(target, binaries[target], corpus)
        package_json = candidate.canonical_json(
            {
                "name": mapping["npm_package"],
                "version": VERSION,
                "os": [mapping["npm_os"]],
                "cpu": [mapping["npm_cpu"]],
                "apg": {
                    "binary_manifest_schema": candidate.BINARY_MANIFEST_SCHEMA,
                    "target": target,
                    "corpus_fingerprint": corpus,
                    "binary_basename": "apgr",
                    "manifest_file": "bin/apgr.binary-manifest.json",
                    "build_identity": {
                        "corpus_fingerprint": corpus,
                        "schema_version": candidate.BUILD_INFO_SCHEMA,
                        "target": target,
                        "version": VERSION,
                    },
                },
            }
        )
        _tgz(
            root,
            mapping["npm_package"],
            VERSION,
            {
                "package.json": package_json,
                "bin/apgr": binaries[target],
                "bin/apgr.binary-manifest.json": manifest,
                **licenses,
            },
        )
    return root


def _artifacts(tmp_path: Path, *, wheel_tamper: str | None = None):
    source, corpus = _source(tmp_path)
    go_root, binaries = _go_artifacts(tmp_path, corpus)
    python_root = tmp_path / "python"
    python_root.mkdir()
    for mapping in candidate.TARGETS:
        target = mapping["go_target"]
        manifest = _binary_manifest(target, binaries[target], corpus)
        _wheel(
            python_root,
            target,
            binaries[target],
            manifest,
            binary_override=(b"tampered\n" if wheel_tamper == target else None),
        )
    _sdist(python_root)
    npm_root = _npm_artifacts(tmp_path, corpus, binaries)
    return source, go_root, python_root, npm_root


def test_build_and_validate_emits_path_free_canonical_manifest(tmp_path: Path) -> None:
    source, go_root, python_root, npm_root = _artifacts(tmp_path)
    output = tmp_path / "candidate"
    result = candidate.build_candidate(source, go_root, python_root, npm_root, output)

    manifest_path = output / candidate.MANIFEST_NAME
    assert manifest_path.read_bytes() == candidate.canonical_json(result)
    assert (output / candidate.CHECKSUM_NAME).read_bytes().endswith(b"\n")
    assert result["schema_version"] == candidate.MANIFEST_SCHEMA
    assert result["version"] == VERSION
    source_identity = result["source_candidate_identity"]
    assert source_identity == candidate.source_candidate_identity(
        VERSION,
        candidate._sha256(b'{"skills":[]}\n'),
        sdist_sha256=result["python"]["sdist"]["sha256"],
        npm_launcher_sha256=result["npm"]["launcher"]["sha256"],
    )
    assert source_identity["schema_version"] == candidate.SOURCE_CANDIDATE_SCHEMA
    assert source_identity["source_artifacts"] == {
        "sdist_sha256": result["python"]["sdist"]["sha256"],
        "npm_launcher_sha256": result["npm"]["launcher"]["sha256"],
    }
    assert set(result["binaries"]) == set(candidate.TARGET_BY_GO)
    assert len(result["python"]["wheels"]) == 3
    assert len(result["npm"]["platform_packages"]) == 3
    assert str(tmp_path).encode() not in manifest_path.read_bytes()
    assert candidate.validate_candidate(
        manifest_path, source, go_root, python_root, npm_root
    ) == result


def test_source_candidate_identity_is_deterministic_and_public_safe() -> None:
    first = candidate.source_candidate_identity(VERSION, "a" * 64)
    second = candidate.source_candidate_identity(VERSION, "a" * 64)
    assert first == second
    rendered = candidate.canonical_json(first)
    assert b"private" not in rendered
    assert b"/tmp/" not in rendered
    assert b"commit" not in rendered
    assert b"tree" not in rendered
    assert len(first["fingerprint"]) == 64


def test_cross_ecosystem_binary_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    source, go_root, python_root, npm_root = _artifacts(
        tmp_path, wheel_tamper="linux/arm64"
    )
    with pytest.raises(candidate.DistributionCandidateError, match="canonical Go binary"):
        candidate.build_candidate(source, go_root, python_root, npm_root, tmp_path / "candidate")


def test_archive_member_safety_is_checked_before_package_identity(tmp_path: Path) -> None:
    source, go_root, python_root, npm_root = _artifacts(tmp_path)
    launcher = npm_root / candidate._npm_tarball_name("@knowledge-forge-ai/apgr", VERSION)
    _tgz(npm_root, "@knowledge-forge-ai/apgr", VERSION, {"../escape": b"unsafe"})
    assert launcher.is_file()
    with pytest.raises(candidate.DistributionCandidateError, match="unsafe member"):
        candidate.build_candidate(source, go_root, python_root, npm_root, tmp_path / "candidate")


def test_manifest_and_checksums_are_no_overwrite_and_tamper_detected(tmp_path: Path) -> None:
    source, go_root, python_root, npm_root = _artifacts(tmp_path)
    output = tmp_path / "candidate"
    candidate.build_candidate(source, go_root, python_root, npm_root, output)
    with pytest.raises(candidate.DistributionCandidateError, match="empty"):
        candidate.build_candidate(source, go_root, python_root, npm_root, output)
    checksums = output / candidate.CHECKSUM_NAME
    checksums.write_bytes(checksums.read_bytes().replace(b"  npm/", b"  changed/", 1))
    with pytest.raises(candidate.DistributionCandidateError, match="SHA256SUMS"):
        candidate.validate_candidate(
            output / candidate.MANIFEST_NAME, source, go_root, python_root, npm_root
        )


def test_cli_build_and_check_use_only_explicit_artifact_directories(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source, go_root, python_root, npm_root = _artifacts(tmp_path)
    output = tmp_path / "candidate"
    arguments = [
        "build",
        "--source-root",
        str(source),
        "--go-artifacts",
        str(go_root),
        "--python-artifacts",
        str(python_root),
        "--npm-artifacts",
        str(npm_root),
        "--output",
        str(output),
    ]
    assert candidate.main(arguments) == 0
    assert json.loads(capsys.readouterr().out)["schema_version"] == candidate.MANIFEST_SCHEMA
    assert candidate.main(
        [
            "check",
            "--source-root",
            str(source),
            "--go-artifacts",
            str(go_root),
            "--python-artifacts",
            str(python_root),
            "--npm-artifacts",
            str(npm_root),
            "--manifest",
            str(output / candidate.MANIFEST_NAME),
        ]
    ) == 0
    assert json.loads(capsys.readouterr().out)["version"] == VERSION


def test_offline_real_candidate_cli_pipeline(tmp_path: Path) -> None:
    python_output = tmp_path / "python-dist"
    python_work = tmp_path / "python-work"
    npm_output = tmp_path / "npm-dist"
    npm_work = tmp_path / "npm-work"
    distribution_output = tmp_path / "distribution"
    python_work.mkdir()
    npm_work.mkdir()
    environment = os.environ.copy()

    subprocess.run(
        [
            sys.executable,
            str(ROOT / "libexec/apg_python_publication.py"),
            "build",
            "--source",
            str(ROOT),
            "--output",
            str(python_output),
            "--work-root",
            str(python_work),
            "--python",
            sys.executable,
        ],
        cwd=ROOT,
        env=environment,
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "libexec/apg_npm_distribution.py"),
            "build",
            "--source",
            str(ROOT),
            "--artifact-root",
            str(python_work / "build-a/binaries"),
            "--output",
            str(npm_output),
            "--work-root",
            str(npm_work),
        ],
        cwd=ROOT,
        env=environment,
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "libexec/apg_distribution_candidate.py"),
            "build",
            "--source-root",
            str(ROOT),
            "--go-artifacts",
            str(python_work / "build-a/binaries"),
            "--python-artifacts",
            str(python_output),
            "--npm-artifacts",
            str(npm_output),
            "--output",
            str(distribution_output),
        ],
        cwd=ROOT,
        env=environment,
        check=True,
    )

    manifest = distribution_output / candidate.MANIFEST_NAME
    assert candidate.validate_candidate(
        manifest,
        ROOT,
        python_work / "build-a/binaries",
        python_output,
        npm_output,
    )["version"] == VERSION


@pytest.mark.parametrize("value", ("relative", "../escape", "./candidate"))
def test_cli_and_api_require_absolute_clean_paths(tmp_path: Path, value: str) -> None:
    source, go_root, python_root, npm_root = _artifacts(tmp_path)
    with pytest.raises(candidate.DistributionCandidateError, match="absolute clean"):
        candidate.build_candidate(source, go_root, python_root, npm_root, Path(value))


def test_distribution_binary_manifest_refusal_matrix_is_complete(tmp_path: Path) -> None:
    source, corpus = _source(tmp_path)
    del source
    binary = b"canonical"
    original = json.loads(_binary_manifest("linux/amd64", binary, corpus))
    mutations = (
        ("schema_version", "unknown/v1", "schema"),
        ("version", "0.7.0", "version"),
        ("target", dict(candidate.TARGET_BY_GO["darwin/arm64"]), "target"),
        ("target", {**original["target"], "npm_cpu": "arm64"}, "target mapping"),
        ("binary_name", "wrong", "binary name"),
        ("corpus_fingerprint", "0" * 64, "corpus"),
        ("module_path", "wrong", "module path"),
        ("build_info_schema", "unknown/v1", "build-info"),
        ("build_flags", [], "build flags"),
        ("build_identity", {}, "build identity"),
        ("size_bytes", True, "binary size"),
        ("sha256", "0" * 64, "SHA-256"),
    )
    for field, value, message in mutations:
        manifest = dict(original)
        manifest[field] = value
        with pytest.raises(candidate.DistributionCandidateError, match=message):
            candidate._binary_manifest_identity(
                candidate.canonical_json(manifest),
                label="fixture",
                target="linux/amd64",
                version=VERSION,
                corpus=corpus,
                binary=binary,
            )

    assert candidate._manifest_target("linux/amd64", "fixture") == "linux/amd64"
    assert candidate._manifest_target(
        {"goos": "linux", "goarch": "arm64"}, "fixture"
    ) == "linux/arm64"
    with pytest.raises(candidate.DistributionCandidateError, match="unsupported"):
        candidate._manifest_target([], "fixture")


def test_distribution_json_path_and_archive_mode_refusals_are_complete(
    tmp_path: Path,
) -> None:
    with pytest.raises(candidate.DistributionCandidateError, match="malformed"):
        candidate._parse_json(b'{"a":1,"a":2}\n', "fixture")
    with pytest.raises(candidate.DistributionCandidateError, match="JSON object"):
        candidate._parse_json(b"[]\n", "fixture")
    with pytest.raises(candidate.DistributionCandidateError, match="not canonical"):
        candidate._canonical_value(b'{"value": 1}\n', "fixture")
    with pytest.raises(candidate.DistributionCandidateError, match="canonical JSON"):
        candidate.canonical_json({"value": object()})
    with pytest.raises(candidate.DistributionCandidateError, match="unsupported member type"):
        candidate._archive_file_mode(stat.S_IFDIR | 0o755, "fixture")
    with pytest.raises(candidate.DistributionCandidateError, match="world-writable"):
        candidate._archive_file_mode(stat.S_IFREG | 0o666, "fixture")
    for name in ("C:/escape", "member\x00name", "root//member"):
        with pytest.raises(candidate.DistributionCandidateError, match="unsafe member"):
            candidate._safe_member_name(name, "fixture")

    missing = tmp_path / "missing"
    with pytest.raises(candidate.DistributionCandidateError, match="unavailable"):
        candidate._directory(missing, "fixture")
    regular = tmp_path / "regular"
    regular.write_bytes(b"fixture")
    with pytest.raises(candidate.DistributionCandidateError, match="direct real directory"):
        candidate._directory(regular, "fixture")
    directory = tmp_path / "directory"
    directory.mkdir()
    with pytest.raises(candidate.DistributionCandidateError, match="direct regular file"):
        candidate._read_direct(directory, "fixture")

    malformed = tmp_path / "source"
    version = malformed / "src/agentic_praxis_grimoire/VERSION"
    corpus = malformed / "src/agentic_praxis_grimoire/resources/skill-metadata.json"
    corpus.parent.mkdir(parents=True)
    corpus.write_bytes(b"{}\n")
    version.write_bytes(b"\xff")
    with pytest.raises(candidate.DistributionCandidateError, match="not ASCII"):
        candidate._source_identity(malformed)
    version.write_text("0.7.0 candidate\n", encoding="ascii")
    with pytest.raises(candidate.DistributionCandidateError, match="malformed"):
        candidate._source_identity(malformed)


def test_wheel_record_refusals_are_complete() -> None:
    record_name = "dist-info/RECORD"
    member = "package/module.py"
    content = b"content"
    digest = "sha256=" + base64.urlsafe_b64encode(
        hashlib.sha256(content).digest()
    ).rstrip(b"=").decode("ascii")
    valid_row = f"{member},{digest},{len(content)}"
    valid_self = f"{record_name},,"
    valid = {member: content, record_name: f"{valid_row}\n{valid_self}\n".encode()}
    candidate._wheel_record_valid(valid, record_name=record_name, label="fixture")

    failures = (
        ({member: content}, "no RECORD"),
        ({member: content, record_name: b"\xff"}, "not UTF-8"),
        ({member: content, record_name: b"malformed\n"}, "malformed row"),
        ({member: content, record_name: f"{valid_row}\n{valid_row}\n".encode()}, "duplicate rows"),
        ({member: content, record_name: f"{valid_row}\n{record_name},digest,1\n".encode()}, "self-row"),
        ({record_name: b"missing,sha256=bad,1\n"}, "missing member"),
        ({member: content, record_name: f"{member},sha256=bad,7\n".encode()}, "hash or size"),
        ({member: content, "extra": b"extra", record_name: f"{valid_row}\n{valid_self}\n".encode()}, "cover every member"),
    )
    for contents, message in failures:
        with pytest.raises(candidate.DistributionCandidateError, match=message):
            candidate._wheel_record_valid(
                contents, record_name=record_name, label="fixture"
            )


def test_distribution_archive_inventory_refusals_are_explicit(tmp_path: Path) -> None:
    source, go_root, python_root, npm_root = _artifacts(tmp_path)
    del source, go_root
    (python_root / "unexpected").write_bytes(b"fixture")
    with pytest.raises(candidate.DistributionCandidateError, match="unexpected file"):
        candidate._find_python_files(python_root, version=VERSION)
    (python_root / "unexpected").unlink()
    (npm_root / "unexpected").write_bytes(b"fixture")
    with pytest.raises(candidate.DistributionCandidateError, match="unexpected file"):
        candidate._find_npm_files(npm_root, version=VERSION)
    with pytest.raises(candidate.DistributionCandidateError, match="not scoped"):
        candidate._npm_tarball_name("unscoped", VERSION)
    with pytest.raises(candidate.DistributionCandidateError, match="metadata"):
        candidate._metadata_contract(b"Name: wrong\n\n", version=VERSION, label="fixture")


def test_distribution_wheel_refusals_are_complete(tmp_path: Path) -> None:
    source, corpus = _source(tmp_path)
    del source
    go_root, binaries = _go_artifacts(tmp_path, corpus)
    records, _ = candidate._load_go_artifacts(
        go_root, version=VERSION, corpus=corpus
    )
    target = "linux/amd64"
    wheel_root = tmp_path / "wheels"
    wheel_root.mkdir()
    wheel = _wheel(
        wheel_root,
        target,
        binaries[target],
        _binary_manifest(target, binaries[target], corpus),
    )
    candidate._validate_wheel(
        wheel,
        target=target,
        version=VERSION,
        corpus=corpus,
        binary=records[target],
    )
    info = f"{candidate.DIST_NAME}-{VERSION}.dist-info"

    wrong_name = tmp_path / "wrong.whl"
    wrong_name.write_bytes(wheel.read_bytes())
    with pytest.raises(candidate.DistributionCandidateError, match="filename"):
        candidate._validate_wheel(
            wrong_name,
            target=target,
            version=VERSION,
            corpus=corpus,
            binary=records[target],
        )

    missing = wheel_root / wheel.name
    original = tmp_path / "original.whl"
    original.write_bytes(wheel.read_bytes())
    canonical = tmp_path / "canonical" / wheel.name
    canonical.parent.mkdir()
    _rewrite_wheel(original, canonical)
    _rewrite_wheel(original, missing, remove=f"{info}/WHEEL")
    with pytest.raises(candidate.DistributionCandidateError, match="required member"):
        candidate._validate_wheel(
            missing, target=target, version=VERSION, corpus=corpus, binary=records[target]
        )

    bad_tag = tmp_path / wheel.name
    _rewrite_wheel(
        original,
        bad_tag,
        replace=(f"{info}/WHEEL", b"Root-Is-Purelib: true\nTag: py3-none-any\n"),
    )
    with pytest.raises(candidate.DistributionCandidateError, match="platform tag"):
        candidate._validate_wheel(
            bad_tag, target=target, version=VERSION, corpus=corpus, binary=records[target]
        )

    nonexecutable = tmp_path / "mode" / wheel.name
    nonexecutable.parent.mkdir()
    _rewrite_wheel(
        original,
        nonexecutable,
        mode=("agentic_praxis_grimoire/bin/apgr", 0o644),
    )
    with pytest.raises(candidate.DistributionCandidateError, match="not executable"):
        candidate._validate_wheel(
            nonexecutable,
            target=target,
            version=VERSION,
            corpus=corpus,
            binary=records[target],
        )

    missing_license = tmp_path / "license" / wheel.name
    missing_license.parent.mkdir()
    _rewrite_wheel(
        original,
        missing_license,
        remove=f"{info}/licenses/NOTICE",
        refresh_record=True,
    )
    with pytest.raises(candidate.DistributionCandidateError, match="missing NOTICE"):
        candidate._validate_wheel(
            missing_license,
            target=target,
            version=VERSION,
            corpus=corpus,
            binary=records[target],
        )

    wrong_manifest_record = dict(records[target])
    wrong_manifest_record["manifest"] = {**records[target]["manifest"], "sha256": "0" * 64}
    with pytest.raises(candidate.DistributionCandidateError, match="canonical manifest"):
        candidate._validate_wheel(
            canonical,
            target=target,
            version=VERSION,
            corpus=corpus,
            binary=wrong_manifest_record,
        )

    private_wheel = tmp_path / "private.whl"
    _rewrite_wheel(original, private_wheel, add=("private/evidence", b"private", 0o644))
    with pytest.raises(candidate.DistributionCandidateError, match="private development"):
        candidate._wheel_members(private_wheel)

    directory_wheel = tmp_path / "directory.whl"
    with zipfile.ZipFile(directory_wheel, "w") as archive:
        info_obj = zipfile.ZipInfo("package/")
        info_obj.create_system = 3
        info_obj.external_attr = (stat.S_IFDIR | 0o755) << 16
        archive.writestr(info_obj, b"")
    with pytest.raises(candidate.DistributionCandidateError, match="unsafe member|unsupported"):
        candidate._wheel_members(directory_wheel)


def test_distribution_sdist_refusals_are_complete(tmp_path: Path) -> None:
    root = tmp_path / "sdists"
    root.mkdir()
    original = _sdist(root)
    prefix = f"{candidate.DIST_NAME}-{VERSION}"
    candidate._validate_sdist(original, version=VERSION)
    cases = (
        ("private", {"add": (f"{prefix}/private/evidence", b"private", 0o644, tarfile.REGTYPE)}, "private development"),
        ("outside", {"add": ("outside/member", b"outside", 0o644, tarfile.REGTYPE)}, "archive root"),
        ("symlink", {"add": (f"{prefix}/link", b"", 0o777, tarfile.SYMTYPE)}, "unsupported member"),
        ("writable", {"add": (f"{prefix}/writable", b"data", 0o666, tarfile.REGTYPE)}, "world-writable"),
        ("binary", {"add": (f"{prefix}/src/bin/apgr", b"binary", 0o755, tarfile.REGTYPE)}, "prebuilt Go binary"),
        ("incomplete", {"remove": f"{prefix}/go.mod"}, "complete Go/Python/skill"),
        ("version", {"replace": (f"{prefix}/src/agentic_praxis_grimoire/VERSION", b"0.7.0\n")}, "VERSION differs"),
    )
    for name, arguments, message in cases:
        path = tmp_path / name / original.name
        path.parent.mkdir()
        _rewrite_sdist(original, path, **arguments)
        with pytest.raises(candidate.DistributionCandidateError, match=message):
            candidate._validate_sdist(path, version=VERSION)


def test_distribution_npm_refusals_are_complete(tmp_path: Path) -> None:
    source, corpus = _source(tmp_path)
    del source
    go_root, binaries = _go_artifacts(tmp_path, corpus)
    records, _ = candidate._load_go_artifacts(
        go_root, version=VERSION, corpus=corpus
    )
    npm_root = _npm_artifacts(tmp_path, corpus, binaries)
    launcher = npm_root / candidate._npm_tarball_name("@knowledge-forge-ai/apgr", VERSION)
    platform = npm_root / candidate._npm_tarball_name(
        "@knowledge-forge-ai/apgr-linux-x64", VERSION
    )

    with tarfile.open(launcher, "r:gz") as archive:
        launcher_json = json.loads(archive.extractfile("package/package.json").read())
    launcher_cases = []
    value = dict(launcher_json)
    value["optionalDependencies"] = {}
    launcher_cases.append(("optional", value, "optional platform"))
    value = dict(launcher_json)
    value["dependencies"] = {"runtime": "1"}
    launcher_cases.append(("dependencies", value, "runtime dependencies"))
    value = dict(launcher_json)
    value["apg"] = {}
    launcher_cases.append(("identity", value, "bound to the corpus"))
    value = dict(launcher_json)
    value["version"] = "0.7.0"
    launcher_cases.append(("version", value, "package identity"))
    for name, package, message in launcher_cases:
        path = tmp_path / f"launcher-{name}.tgz"
        _rewrite_sdist(
            launcher,
            path,
            replace=("package/package.json", candidate.canonical_json(package)),
        )
        with pytest.raises(candidate.DistributionCandidateError, match=message):
            candidate._validate_npm_package(
                path, version=VERSION, corpus=corpus, binaries=records
            )

    with tarfile.open(platform, "r:gz") as archive:
        platform_json = json.loads(archive.extractfile("package/package.json").read())
    platform_cases = []
    value = dict(platform_json)
    value["name"] = "@knowledge-forge-ai/unknown"
    platform_cases.append(("name", value, "unsupported"))
    value = dict(platform_json)
    value["os"] = ["darwin"]
    platform_cases.append(("platform", value, "platform restrictions"))
    value = dict(platform_json)
    value["scripts"] = {"install": "download"}
    platform_cases.append(("scripts", value, "runtime dependencies"))
    value = dict(platform_json)
    value["apg"] = {}
    platform_cases.append(("identity", value, "target/corpus identity"))
    for name, package, message in platform_cases:
        path = tmp_path / f"platform-{name}.tgz"
        _rewrite_sdist(
            platform,
            path,
            replace=("package/package.json", candidate.canonical_json(package)),
        )
        with pytest.raises(candidate.DistributionCandidateError, match=message):
            candidate._validate_npm_package(
                path, version=VERSION, corpus=corpus, binaries=records
            )

    tampered = tmp_path / "platform-binary.tgz"
    _rewrite_sdist(platform, tampered, replace=("package/bin/apgr", b"tampered"))
    with pytest.raises(candidate.DistributionCandidateError, match="canonical Go binary"):
        candidate._validate_npm_package(
            tampered, version=VERSION, corpus=corpus, binaries=records
        )
    nonexecutable = tmp_path / "platform-mode.tgz"
    _rewrite_sdist(platform, nonexecutable, mode=("package/bin/apgr", 0o644))
    with pytest.raises(candidate.DistributionCandidateError, match="not executable"):
        candidate._validate_npm_package(
            nonexecutable, version=VERSION, corpus=corpus, binaries=records
        )
    unexpected = tmp_path / "platform-extra.tgz"
    _rewrite_sdist(
        platform,
        unexpected,
        add=("package/extra", b"extra", 0o644, tarfile.REGTYPE),
    )
    with pytest.raises(candidate.DistributionCandidateError, match="unexpected or missing"):
        candidate._validate_npm_package(
            unexpected, version=VERSION, corpus=corpus, binaries=records
        )

    wrong_records = dict(records)
    wrong_records["linux/amd64"] = {
        **records["linux/amd64"],
        "manifest": {**records["linux/amd64"]["manifest"], "sha256": "0" * 64},
    }
    with pytest.raises(candidate.DistributionCandidateError, match="canonical manifest"):
        candidate._validate_npm_package(
            platform, version=VERSION, corpus=corpus, binaries=wrong_records
        )


def test_authoritative_release_asset_inventory_and_roles() -> None:
    inventory = candidate.release_asset_inventory(VERSION)
    assert len(inventory) == 10

    manifest_asset = inventory["apg-distribution-manifest.json"]
    assert manifest_asset["role"] == candidate.ROLE_MANIFEST
    assert manifest_asset["ecosystem"] == "manifest"

    checksum_asset = inventory["SHA256SUMS"]
    assert checksum_asset["role"] == candidate.ROLE_CHECKSUMS
    assert checksum_asset["ecosystem"] == "checksums"

    python_assets = candidate.python_release_asset_names(VERSION)
    assert len(python_assets) == 4
    for name in python_assets:
        assert name in inventory
        assert inventory[name]["ecosystem"] == "python"

    npm_assets = candidate.npm_release_asset_names(VERSION)
    assert len(npm_assets) == 4
    for name in npm_assets:
        assert name in inventory
        assert inventory[name]["ecosystem"] == "npm"

    publication_order = candidate.npm_publication_order(VERSION)
    assert len(publication_order) == 4
    assert publication_order == (
        "@knowledge-forge-ai/apgr-darwin-arm64",
        "@knowledge-forge-ai/apgr-linux-x64",
        "@knowledge-forge-ai/apgr-linux-arm64",
        "@knowledge-forge-ai/apgr",
    )

    for name, expected in inventory.items():
        classified = candidate.classify_release_asset(name, VERSION)
        assert classified == expected

    assert candidate.classify_release_asset("unknown.whl", VERSION) is None
