from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tarfile
from io import BytesIO

import pytest


ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / "libexec"))

import apg_npm_distribution as distribution  # noqa: E402

CURRENT_VERSION = distribution.version_authority(ROOT)
CORPUS = "a" * 64


def _artifact_root(tmp_path: Path, *, tamper: str | None = None) -> Path:
    root = tmp_path / "go-artifacts"
    for target in distribution.TARGETS:
        target_root = root / target.slug
        target_root.mkdir(parents=True)
        binary = f"#!/bin/sh\nprintf '%s\\n' \"$@\"\n".encode("utf-8")
        binary_path = target_root / "apgr"
        binary_path.write_bytes(binary)
        binary_path.chmod(0o700)
        digest = hashlib.sha256(binary).hexdigest()
        if tamper == target.go_target:
            digest = "0" * 64
        manifest = {
            "schema_version": distribution.MANIFEST_SCHEMA,
            "version": CURRENT_VERSION,
            "target": {
                "go_target": target.go_target,
                "goos": target.os_name,
                "goarch": "amd64" if target.cpu == "x64" else target.cpu,
                "python_platform": {
                    "darwin/arm64": "macosx_11_0_arm64",
                    "linux/amd64": "manylinux_2_17_x86_64",
                    "linux/arm64": "manylinux_2_17_aarch64",
                }[target.go_target],
                "npm_package": target.package_name,
                "npm_os": target.os_name,
                "npm_cpu": target.cpu,
            },
            "binary_name": distribution.BINARY_BASENAME,
            "size_bytes": len(binary),
            "sha256": digest,
            "build_identity": {
                "corpus_fingerprint": CORPUS,
                "schema_version": distribution.BUILD_INFO_SCHEMA,
                "target": target.go_target,
                "version": CURRENT_VERSION,
            },
            "corpus_fingerprint": CORPUS,
            "module_path": distribution.MODULE_PATH,
            "build_info_schema": distribution.BUILD_INFO_SCHEMA,
            "build_flags": list(distribution.BUILD_FLAGS),
        }
        (target_root / "apgr.binary-manifest.json").write_text(
            json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
    return root


def test_builds_exact_four_reproducible_packages_with_shared_contract(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    artifacts = _artifact_root(tmp_path)
    records = distribution.build_packages(ROOT, artifacts, first, work_root=tmp_path)
    repeated = distribution.build_packages(ROOT, artifacts, second, work_root=tmp_path)

    assert {record.name for record in records} == {
        distribution.LAUNCHER_NAME,
        *(target.package_name for target in distribution.TARGETS),
    }
    assert [record.filename for record in records] == [record.filename for record in repeated]
    for record in records:
        assert (first / record.filename).read_bytes() == (second / record.filename).read_bytes()
    assert distribution.check_packages(first, version=CURRENT_VERSION)

    launcher = next(path for path in first.glob("*.tgz") if f"apgr-{CURRENT_VERSION}" in path.name and "darwin" not in path.name and "linux" not in path.name)
    with tarfile.open(launcher, mode="r:gz") as archive:
        names = {member.name for member in archive}
    assert names == {
        "package/package.json",
        "package/index.js",
        "package/README.md",
        "package/LICENSE",
        "package/NOTICE",
        "package/COMMERCIAL-LICENSE.md",
    }


def test_platform_metadata_has_exact_restrictions_and_no_runtime_hooks(tmp_path: Path) -> None:
    output = tmp_path / "bundle"
    distribution.build_packages(ROOT, _artifact_root(tmp_path), output, work_root=tmp_path)
    platform = output / distribution.npm_tarball_name(
        "@knowledge-forge-ai/apgr-linux-x64", CURRENT_VERSION
    )
    members, contents = distribution._archive_members(platform)
    metadata = distribution._archive_package_json(contents, platform)
    assert metadata["name"] == "@knowledge-forge-ai/apgr-linux-x64"
    assert metadata["version"] == CURRENT_VERSION
    assert metadata["os"] == ["linux"]
    assert metadata["cpu"] == ["x64"]
    assert "scripts" not in metadata
    assert "dependencies" not in metadata
    assert members["package/bin/apgr"].mode & 0o111
    assert not members["package/bin/apgr"].mode & 0o002


def test_all_npm_tarballs_carry_discovery_metadata_and_readme(tmp_path: Path) -> None:
    output = tmp_path / "bundle"
    records = distribution.build_packages(ROOT, _artifact_root(tmp_path), output, work_root=tmp_path)
    assert len(records) == 4
    for record in records:
        archive_path = output / record.filename
        _, contents = distribution._archive_members(archive_path)
        metadata = distribution._archive_package_json(contents, archive_path)
        assert metadata["version"] == CURRENT_VERSION
        assert metadata["description"]
        assert metadata["license"] == "AGPL-3.0-or-later"
        assert metadata["repository"]["url"].startswith("git+https://github.com/")
        assert metadata["homepage"].startswith("https://")
        assert metadata["bugs"]["url"].startswith("https://")
        assert metadata["keywords"]
        readme = contents["package/README.md"]
        assert readme.strip()
        assert b"__APG_" not in readme
        assert b"Once this version is published" in readme


def test_manifest_tamper_and_missing_identity_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(distribution.NpmDistributionError, match="SHA-256"):
        distribution.build_packages(
            ROOT,
            _artifact_root(tmp_path, tamper="linux/amd64"),
            tmp_path / "bundle",
            work_root=tmp_path,
        )
    root = _artifact_root(tmp_path / "missing")
    manifest = root / "darwin-arm64" / "apgr.binary-manifest.json"
    value = json.loads(manifest.read_text(encoding="utf-8"))
    value.pop("build_info_schema")
    manifest.write_text(
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(distribution.NpmDistributionError, match="fields"):
        distribution.build_packages(ROOT, root, tmp_path / "missing-bundle", work_root=tmp_path)


@pytest.mark.parametrize("name", ("", "/absolute", "package/../escape", "package\\escape"))
def test_archive_member_safety_rejects_unsafe_paths(name: str) -> None:
    with pytest.raises(distribution.NpmDistributionError, match="unsafe|outside"):
        distribution._safe_member_name(name)


def test_artifact_mapping_consumes_manifest_bytes_without_rebuilding(tmp_path: Path) -> None:
    artifact_root = _artifact_root(tmp_path)
    mapping = {}
    for target in distribution.TARGETS:
        target_root = artifact_root / target.slug
        mapping[target.go_target] = {
            "path": target_root / "apgr",
            "manifest_path": target_root / "apgr.binary-manifest.json",
        }
    records = distribution.build_packages(
        ROOT, None, tmp_path / "mapped", artifacts=mapping, work_root=tmp_path
    )
    assert len(records) == 4


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_version", "wrong", "schema"),
        ("version", "", "version"),
        ("target", {}, "target"),
        ("module_path", "wrong", "module"),
        ("build_info_schema", "wrong", "build-info"),
        ("build_flags", [], "build flags"),
        ("build_identity", {}, "build identity"),
        ("corpus_fingerprint", "wrong", "inconsistent"),
        ("binary_name", "wrong", "basename"),
        ("size_bytes", True, "size"),
        ("sha256", "wrong", "SHA-256"),
    ],
)
def test_binary_manifest_field_matrix_fails_closed(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    root = _artifact_root(tmp_path)
    raw = (root / "darwin-arm64/apgr.binary-manifest.json").read_bytes()
    manifest = json.loads(raw)
    manifest[field] = value
    with pytest.raises(distribution.NpmDistributionError, match=message):
        distribution._manifest_identity(manifest, "fixture")


def test_binary_manifest_shape_and_artifact_mapping_refusals(tmp_path: Path) -> None:
    with pytest.raises(distribution.NpmDistributionError, match="JSON object"):
        distribution._parse_manifest(b"[]\n", "fixture")
    with pytest.raises(distribution.NpmDistributionError, match="malformed"):
        distribution._parse_manifest(b'{"a":1,"a":2}\n', "fixture")
    with pytest.raises(ValueError, match="duplicate"):
        distribution._unique_object([("a", 1), ("a", 2)])
    with pytest.raises(distribution.NpmDistributionError, match="serializable"):
        distribution._canonical_json({"bad": object()})
    assert distribution._manifest_target({"target": "linux/arm64"}) is None

    target = distribution.TARGETS[0]
    with pytest.raises(distribution.NpmDistributionError, match="target"):
        distribution._artifact_from_value(
            target,
            distribution.Artifact("linux/amd64", tmp_path / "apgr"),
        )
    with pytest.raises(distribution.NpmDistributionError, match="binary path"):
        distribution._artifact_from_value(target, {})
    with pytest.raises(distribution.NpmDistributionError, match="canonical manifest"):
        distribution._artifact_from_value(
            target,
            {"path": tmp_path / "apgr", "manifest": {}},
        )
    with pytest.raises(distribution.NpmDistributionError, match="manifest is invalid"):
        distribution._artifact_from_value(
            target,
            {"path": tmp_path / "apgr", "manifest": 1},
        )


def test_path_output_and_template_refusals_are_bounded(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    with pytest.raises(distribution.NpmDistributionError, match="unavailable"):
        distribution._directory(missing, "fixture")
    regular = tmp_path / "regular"
    regular.write_bytes(b"data")
    with pytest.raises(distribution.NpmDistributionError, match="directory"):
        distribution._directory(regular, "fixture")
    output = tmp_path / "output"
    output.mkdir()
    (output / "present").write_bytes(b"data")
    with pytest.raises(distribution.NpmDistributionError, match="empty"):
        distribution._ensure_empty_output(output)
    with pytest.raises(distribution.NpmDistributionError, match="scoped"):
        distribution.npm_tarball_name("unscoped", "0.7.0")
    with pytest.raises(distribution.NpmDistributionError, match="overwrite"):
        distribution._write_file(regular, b"new", 0o600)

    template = {"version": "__APG_VERSION__", "placeholder": "__APG_OTHER__"}
    with pytest.raises(distribution.NpmDistributionError, match="placeholders"):
        distribution._package_json(
            template,
            name=distribution.LAUNCHER_NAME,
            version="0.7.0",
            target=None,
            corpus="a" * 64,
        )


def test_bundle_count_and_cli_failures_are_explicit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    with pytest.raises(distribution.NpmDistributionError, match="four tarballs"):
        distribution.check_packages(bundle)
    assert distribution.main(["check", "--bundle", str(bundle)]) == 1
    assert "four tarballs" in capsys.readouterr().err


def _rewrite_tarball(
    source: Path,
    destination: Path,
    *,
    package: dict[str, object] | None = None,
    remove: str | None = None,
    add: tuple[str, bytes, int] | None = None,
    replace: tuple[str, bytes] | None = None,
    mode: tuple[str, int] | None = None,
) -> None:
    with tarfile.open(source, mode="r:gz") as archive:
        entries = [
            (member.name, archive.extractfile(member).read(), member.mode)
            for member in archive
        ]
    updated: list[tuple[str, bytes, int]] = []
    for name, content, member_mode in entries:
        if name == remove:
            continue
        if name == "package/package.json" and package is not None:
            content = distribution._canonical_json(package)
        if replace is not None and name == replace[0]:
            content = replace[1]
        if mode is not None and name == mode[0]:
            member_mode = mode[1]
        updated.append((name, content, member_mode))
    if add is not None:
        updated.append(add)
    with tarfile.open(destination, mode="w:gz") as archive:
        for name, content, member_mode in updated:
            info = tarfile.TarInfo(name)
            info.size = len(content)
            info.mode = member_mode
            archive.addfile(info, BytesIO(content))


def test_launcher_tarball_contract_refusals_are_complete(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    distribution.build_packages(ROOT, _artifact_root(tmp_path), bundle, work_root=tmp_path)
    launcher = bundle / distribution.npm_tarball_name(distribution.LAUNCHER_NAME, CURRENT_VERSION)
    _, contents = distribution._archive_members(launcher)
    original = json.loads(contents["package/package.json"])
    cases: list[tuple[dict[str, object], str]] = []

    value = dict(original)
    value["engines"] = {"node": ">=1"}
    cases.append((value, "Node engine"))
    value = dict(original)
    value["apg"] = "wrong"
    cases.append((value, "identity is malformed"))
    value = dict(original)
    value["apg"] = {**original["apg"], "corpus_fingerprint": "wrong"}
    cases.append((value, "corpus fingerprint"))
    value = dict(original)
    value["apg"] = {**original["apg"], "extra": True}
    cases.append((value, "identity is not exact"))
    value = dict(original)
    value["dependencies"] = {"runtime": "1.0.0"}
    cases.append((value, "runtime dependencies"))
    value = dict(original)
    value["optionalDependencies"] = {}
    cases.append((value, "optional platform dependencies"))
    value = dict(original)
    value["scripts"] = {"install": "download"}
    cases.append((value, "install scripts"))

    for index, (package, message) in enumerate(cases):
        candidate = tmp_path / f"launcher-{index}.tgz"
        _rewrite_tarball(launcher, candidate, package=package)
        with pytest.raises(distribution.NpmDistributionError, match=message):
            distribution.validate_tarball(candidate)


def test_platform_tarball_contract_refusals_are_complete(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    distribution.build_packages(ROOT, _artifact_root(tmp_path), bundle, work_root=tmp_path)
    platform = bundle / distribution.npm_tarball_name(
        "@knowledge-forge-ai/apgr-linux-x64", CURRENT_VERSION
    )
    _, contents = distribution._archive_members(platform)
    original = json.loads(contents["package/package.json"])
    package_cases: list[tuple[dict[str, object], str]] = []

    value = dict(original)
    value["name"] = "@knowledge-forge-ai/unknown"
    package_cases.append((value, "unsupported npm package"))
    value = dict(original)
    value["engines"] = {"node": ">=1"}
    package_cases.append((value, "Node engine"))
    value = dict(original)
    value["os"] = ["darwin"]
    package_cases.append((value, "target restrictions"))
    value = dict(original)
    value["dependencies"] = {"runtime": "1.0.0"}
    package_cases.append((value, "forbidden runtime"))
    value = dict(original)
    value["apg"] = {}
    package_cases.append((value, "package identity"))
    value = dict(original)
    value["version"] = "0.7.0"
    package_cases.append((value, "binary identity"))

    for index, (package, message) in enumerate(package_cases):
        candidate = tmp_path / f"platform-{index}.tgz"
        _rewrite_tarball(platform, candidate, package=package)
        with pytest.raises(distribution.NpmDistributionError, match=message):
            distribution.validate_tarball(candidate)

    tampered = tmp_path / "platform-binary.tgz"
    _rewrite_tarball(platform, tampered, replace=("package/bin/apgr", b"tampered"))
    with pytest.raises(distribution.NpmDistributionError, match="binary does not match"):
        distribution.validate_tarball(tampered)

    nonexecutable = tmp_path / "platform-mode.tgz"
    _rewrite_tarball(platform, nonexecutable, mode=("package/bin/apgr", 0o644))
    with pytest.raises(distribution.NpmDistributionError, match="not executable"):
        distribution.validate_tarball(nonexecutable)

    unexpected = tmp_path / "platform-extra.tgz"
    _rewrite_tarball(platform, unexpected, add=("package/extra", b"extra", 0o644))
    with pytest.raises(distribution.NpmDistributionError, match="unexpected package members"):
        distribution.validate_tarball(unexpected)

    missing = tmp_path / "platform-missing.tgz"
    _rewrite_tarball(platform, missing, remove="package/package.json")
    with pytest.raises(distribution.NpmDistributionError, match="no package.json"):
        distribution.validate_tarball(missing)

    writable = tmp_path / "platform-writable.tgz"
    _rewrite_tarball(platform, writable, mode=("package/NOTICE", 0o666))
    with pytest.raises(distribution.NpmDistributionError, match="unsafe archive member"):
        distribution.validate_tarball(writable)

    missing_readme = tmp_path / "platform-missing-readme.tgz"
    _rewrite_tarball(platform, missing_readme, remove="package/README.md")
    with pytest.raises(distribution.NpmDistributionError, match="unexpected package members"):
        distribution.validate_tarball(missing_readme)

    empty_readme = tmp_path / "platform-empty-readme.tgz"
    _rewrite_tarball(platform, empty_readme, replace=("package/README.md", b"   \n"))
    with pytest.raises(distribution.NpmDistributionError, match="README.md is empty"):
        distribution.validate_tarball(empty_readme)

    unrendered = tmp_path / "platform-unrendered-readme.tgz"
    _rewrite_tarball(platform, unrendered, replace=("package/README.md", b"Placeholder __APG_VERSION__"))
    with pytest.raises(distribution.NpmDistributionError, match="unrendered placeholders"):
        distribution.validate_tarball(unrendered)


def test_artifact_and_version_path_refusals_are_complete(tmp_path: Path) -> None:
    with pytest.raises(distribution.NpmDistributionError, match="absolute clean path"):
        distribution._direct_path(Path("relative"), "fixture")
    with pytest.raises(distribution.NpmDistributionError, match="absolute clean path"):
        distribution._directory(Path("relative"), "fixture")

    version_root = tmp_path / "version-root"
    version_path = version_root / "src/agentic_praxis_grimoire/VERSION"
    version_path.parent.mkdir(parents=True)
    version_path.write_bytes(b"\xff")
    with pytest.raises(distribution.NpmDistributionError, match="not ASCII"):
        distribution.version_authority(version_root)
    version_path.write_text("0.7.0 candidate\n", encoding="ascii")
    with pytest.raises(distribution.NpmDistributionError, match="malformed"):
        distribution.version_authority(version_root)

    root = _artifact_root(tmp_path / "artifacts")
    target = distribution.TARGETS[0]
    binary = root / target.slug / "apgr"
    manifest = root / target.slug / "apgr.binary-manifest.json"
    artifact = distribution.Artifact(target.go_target, binary, None, manifest.read_bytes())
    assert distribution._load_artifact(artifact)[0] == binary.read_bytes()
    binary.chmod(0o600)
    with pytest.raises(distribution.NpmDistributionError, match="not executable"):
        distribution._load_artifact(artifact)
    binary.chmod(0o700)
    with pytest.raises(distribution.NpmDistributionError, match="manifest is unavailable"):
        distribution._load_artifact(
            distribution.Artifact(target.go_target, binary)
        )


def test_publication_order_and_package_identities() -> None:
    order = distribution.publication_order()
    assert order == (
        "@knowledge-forge-ai/apgr-darwin-arm64",
        "@knowledge-forge-ai/apgr-linux-x64",
        "@knowledge-forge-ai/apgr-linux-arm64",
        "@knowledge-forge-ai/apgr",
    )
    mapping = distribution.package_tarball_mapping("0.7.0")
    assert mapping["@knowledge-forge-ai/apgr-darwin-arm64"] == "knowledge-forge-ai-apgr-darwin-arm64-0.7.0.tgz"
    assert mapping["@knowledge-forge-ai/apgr-linux-x64"] == "knowledge-forge-ai-apgr-linux-x64-0.7.0.tgz"
    assert mapping["@knowledge-forge-ai/apgr-linux-arm64"] == "knowledge-forge-ai-apgr-linux-arm64-0.7.0.tgz"
    assert mapping["@knowledge-forge-ai/apgr"] == "knowledge-forge-ai-apgr-0.7.0.tgz"


def test_preflight_publication_tarballs_and_manifest_disagreement(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    artifacts = _artifact_root(tmp_path)
    records = distribution.build_packages(ROOT, artifacts, bundle, work_root=tmp_path)

    preflight = distribution.preflight_publication_tarballs(bundle, CURRENT_VERSION)
    assert [r.name for r in preflight] == list(distribution.PUBLICATION_ORDER)

    manifest = {
        "npm": {
            "launcher": {
                "name": "@knowledge-forge-ai/apgr",
                "filename": f"knowledge-forge-ai-apgr-{CURRENT_VERSION}.tgz",
                "sha256": next(r.sha256 for r in records if r.name == "@knowledge-forge-ai/apgr"),
                "size_bytes": next(r.size_bytes for r in records if r.name == "@knowledge-forge-ai/apgr"),
            },
            "platform_packages": [
                {
                    "name": r.name,
                    "filename": r.filename,
                    "sha256": r.sha256,
                    "size_bytes": r.size_bytes,
                }
                for r in records
                if r.name != "@knowledge-forge-ai/apgr"
            ],
        }
    }
    checked = distribution.preflight_publication_tarballs(bundle, CURRENT_VERSION, manifest=manifest)
    assert len(checked) == 4

    tampered_manifest = json.loads(json.dumps(manifest))
    tampered_manifest["npm"]["launcher"]["sha256"] = "0" * 64
    with pytest.raises(distribution.NpmDistributionError, match="disagrees with distribution manifest"):
        distribution.preflight_publication_tarballs(bundle, CURRENT_VERSION, manifest=tampered_manifest)

    tampered_size = json.loads(json.dumps(manifest))
    tampered_size["npm"]["launcher"]["size_bytes"] = 999999
    with pytest.raises(distribution.NpmDistributionError, match="disagrees with distribution manifest"):
        distribution.preflight_publication_tarballs(bundle, CURRENT_VERSION, manifest=tampered_size)

    incomplete_bundle = tmp_path / "incomplete"
    incomplete_bundle.mkdir()
    with pytest.raises(distribution.NpmDistributionError, match="missing npm tarball"):
        distribution.preflight_publication_tarballs(incomplete_bundle, CURRENT_VERSION)


def test_classify_registry_state_and_fail_closed_plan() -> None:
    pkg = "@knowledge-forge-ai/apgr"
    version = "0.7.0"
    local_sha = "abcdef" * 10 + "1234"

    assert distribution.classify_registry_state(pkg, version, local_sha, None) == "absent_safe_to_publish"
    assert distribution.classify_registry_state(pkg, version, local_sha, {}) == "absent_safe_to_publish"
    assert distribution.classify_registry_state(pkg, version, local_sha, {"version": "0.6.0"}) == "absent_safe_to_publish"

    exact_info = {
        "name": pkg,
        "version": version,
        "dist": {"sha256": local_sha, "tarball": f"https://registry.npmjs.org/{pkg}/-/{pkg}-{version}.tgz"},
    }
    assert distribution.classify_registry_state(pkg, version, local_sha, exact_info) == "already_exact_no_op"

    mismatched_info = {
        "name": pkg,
        "version": version,
        "dist": {"sha256": "different_hash", "tarball": f"https://registry.npmjs.org/{pkg}/-/{pkg}-{version}.tgz"},
    }
    assert distribution.classify_registry_state(pkg, version, local_sha, mismatched_info) == "mismatched_drift_stop"

    records = [
        {"name": name, "version": version, "sha256": local_sha}
        for name in distribution.PUBLICATION_ORDER
    ]

    absent_states = {name: None for name in distribution.PUBLICATION_ORDER}
    plan = distribution.evaluate_publication_plan(records, absent_states)
    assert plan["action"] == "ready_for_first_publication_bootstrap"
    assert len(plan["packages"]) == 4

    exact_states = {
        name: {
            "name": name,
            "version": version,
            "dist": {"sha256": local_sha, "tarball": "url"},
        }
        for name in distribution.PUBLICATION_ORDER
    }
    plan_exact = distribution.evaluate_publication_plan(records, exact_states)
    assert plan_exact["action"] == "already_published_exact"

    partial_states = dict(exact_states)
    partial_states["@knowledge-forge-ai/apgr"] = None
    plan_partial = distribution.evaluate_publication_plan(records, partial_states)
    assert plan_partial["action"] == "stop_partial_or_mismatched"

    drift_states = dict(exact_states)
    drift_states["@knowledge-forge-ai/apgr-darwin-arm64"] = {
        "name": "@knowledge-forge-ai/apgr-darwin-arm64",
        "version": version,
        "dist": {"sha256": "drifted", "tarball": "url"},
    }
    plan_drift = distribution.evaluate_publication_plan(records, drift_states)
    assert plan_drift["action"] == "stop_partial_or_mismatched"


def test_verify_live_readback_contract() -> None:
    pkg = "@knowledge-forge-ai/apgr"
    version = "0.7.0"
    local_sha = "abcdef" * 10 + "1234"

    valid_response = {
        "name": pkg,
        "version": version,
        "dist": {"sha256": local_sha, "tarball": "https://registry.npmjs.org/tarball.tgz"},
    }
    readback = distribution.verify_live_readback(pkg, version, local_sha, valid_response)
    assert readback["verified"] is True
    assert readback["name"] == pkg

    with pytest.raises(distribution.NpmDistributionError, match="empty response"):
        distribution.verify_live_readback(pkg, version, local_sha, {})

    with pytest.raises(distribution.NpmDistributionError, match="name mismatch"):
        distribution.verify_live_readback(pkg, version, local_sha, {"name": "wrong", "version": version, "dist": {"tarball": "t"}})

    with pytest.raises(distribution.NpmDistributionError, match="version mismatch"):
        distribution.verify_live_readback(pkg, version, local_sha, {"name": pkg, "version": "0.6.0", "dist": {"tarball": "t"}})

    with pytest.raises(distribution.NpmDistributionError, match="missing distribution metadata"):
        distribution.verify_live_readback(pkg, version, local_sha, {"name": pkg, "version": version, "dist": {}})

    with pytest.raises(distribution.NpmDistributionError, match="SHA-256 mismatch"):
        distribution.verify_live_readback(
            pkg, version, local_sha, {"name": pkg, "version": version, "dist": {"sha256": "mismatched", "tarball": "t"}}
        )


def test_verify_credential_safety() -> None:
    distribution.verify_credential_safety(["npm", "publish", "pkg.tgz", "--access", "public"], {})

    with pytest.raises(distribution.NpmDistributionError, match="credential safety violation"):
        distribution.verify_credential_safety(["npm", "publish", "--//registry.npmjs.org/:_authToken=secret"], {})

    with pytest.raises(distribution.NpmDistributionError, match="credential safety violation"):
        distribution.verify_credential_safety(["npm", "publish"], {"NODE_AUTH_TOKEN": "secret_token"})


def test_template_readme_parameterization_across_versions() -> None:
    _, _, _, launcher_readme, platform_readme = distribution._load_templates(ROOT)
    for ver in ("0.8.1", "0.8.2", "0.9.0", "0.10.0", "0.8.2-rc.1"):
        rendered_launcher = launcher_readme.decode("utf-8").replace("__APG_VERSION__", ver).encode("utf-8")
        assert b"__APG_" not in rendered_launcher
        assert f"@knowledge-forge-ai/apgr@{ver}".encode("utf-8") in rendered_launcher
        assert b"Once this version is published" in rendered_launcher

        target = distribution.TARGETS[0]
        rendered_platform = (
            platform_readme.decode("utf-8")
            .replace("__APG_PLATFORM_NAME__", target.package_name)
            .replace("__APG_TARGET__", target.go_target)
            .replace("__APG_OS__", target.os_name)
            .replace("__APG_CPU__", target.cpu)
            .replace("__APG_VERSION__", ver)
            .encode("utf-8")
        )
        assert b"__APG_" not in rendered_platform
        assert f"@knowledge-forge-ai/apgr@{ver}".encode("utf-8") in rendered_platform
        assert b"Once this version is published" in rendered_platform


def test_npm_readme_and_templates_have_durable_conditional_installation_wording() -> None:
    npm_readme = (ROOT / "npm/README.md").read_text(encoding="utf-8")
    assert "This documentation covers 0.9.0" in npm_readme
    assert "Once this version is published" in npm_readme

    for template_rel in ("npm/templates/launcher/README.md", "npm/templates/platform/README.md"):
        content = (ROOT / template_rel).read_text(encoding="utf-8")
        assert "Once this version is published" in content
        assert "__APG_VERSION__" in content
