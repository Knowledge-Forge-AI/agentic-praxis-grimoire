from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[6]
SPEC = importlib.util.spec_from_file_location("apg_go_build", ROOT / "libexec/apg_go_build.py")
assert SPEC is not None and SPEC.loader is not None
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


def authority_root(tmp_path: Path, version: bytes = b"0.6.0\n") -> Path:
    root = tmp_path / "repository"
    package = root / "src/agentic_praxis_grimoire"
    resources = package / "resources"
    resources.mkdir(parents=True)
    (package / "VERSION").write_bytes(version)
    (resources / "skill-metadata.json").write_bytes(b'{"skills":[]}\n')
    return root


def test_identities_require_direct_ascii_authorities(tmp_path: Path) -> None:
    root = authority_root(tmp_path)
    version, corpus = builder.identities(root)
    assert version == "0.6.0"
    assert len(corpus) == 64

    (root / "src/agentic_praxis_grimoire/VERSION").write_bytes(b"\xff")
    with pytest.raises(builder.BuildError, match="not ASCII"):
        builder.identities(root)
    (root / "src/agentic_praxis_grimoire/VERSION").write_text("bad version\n")
    with pytest.raises(builder.BuildError, match="malformed"):
        builder.identities(root)
    (root / "src/agentic_praxis_grimoire/VERSION").unlink()
    with pytest.raises(builder.BuildError, match="unavailable"):
        builder.identities(root)

    target = tmp_path / "VERSION"
    target.write_text("0.6.0\n")
    (root / "src/agentic_praxis_grimoire/VERSION").symlink_to(target)
    with pytest.raises(builder.BuildError, match="direct regular"):
        builder.identities(root)


def test_build_refuses_inputs_toolchain_and_failed_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = authority_root(tmp_path)
    with pytest.raises(builder.BuildError, match="unsupported target"):
        builder.build(root, "windows/amd64", tmp_path / "output")
    with pytest.raises(builder.BuildError, match="absolute clean"):
        builder.build(root, "darwin/arm64", Path("output"))

    output = tmp_path / "output/apgr"
    monkeypatch.setattr(builder.shutil, "which", lambda _name: None)
    with pytest.raises(builder.BuildError, match="unavailable"):
        builder.build(root, "darwin/arm64", output)

    bad_go = tmp_path / "go-directory"
    bad_go.mkdir()
    monkeypatch.setattr(builder.shutil, "which", lambda _name: str(bad_go))
    with pytest.raises(builder.BuildError, match="direct executable"):
        builder.build(root, "darwin/arm64", output)

    go = tmp_path / "go"
    go.write_bytes(b"go")
    go.chmod(0o700)
    monkeypatch.setattr(builder.shutil, "which", lambda _name: str(go))
    monkeypatch.setattr(
        builder.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=1),
    )
    with pytest.raises(builder.BuildError, match="build failed"):
        builder.build(root, "darwin/arm64", output)


def test_build_success_and_main_rendering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = authority_root(tmp_path)
    go = tmp_path / "go"
    go.write_bytes(b"go")
    go.chmod(0o700)
    monkeypatch.setattr(builder.shutil, "which", lambda _name: str(go))

    observed: dict[str, object] = {}

    def successful_run(arguments: list[str], **kwargs: object) -> SimpleNamespace:
        observed.update(kwargs)
        if "-o" in arguments:
            output = Path(arguments[arguments.index("-o") + 1])
            output.write_bytes(b"binary")
            return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")
        return SimpleNamespace(
            returncode=0,
            stdout=(
                b"/tmp/apgr: go1.25.10\n"
                b" mod github.com/Knowledge-Forge-AI/agentic-praxis-grimoire (devel)\n"
                b" build CGO_ENABLED=0\n"
                b" build GOOS=linux\n"
                b" build GOARCH=arm64\n"
                b" build -trimpath=true\n"
            ),
            stderr=b"",
        )

    monkeypatch.setattr(builder.subprocess, "run", successful_run)
    output = tmp_path / "nested/apgr"
    result = builder.build(root, "linux/arm64", output)
    assert result["target"] == "linux/arm64"
    assert result["version"] == "0.6.0"
    assert output.stat().st_mode & 0o777 == 0o700
    assert observed["shell"] is False
    assert observed["env"]["CGO_ENABLED"] == "0"
    assert observed["env"]["GOFLAGS"] == ""
    assert observed["env"]["GOARM64"] == "v8.0"
    manifest_path = Path(result["manifest_path"])
    assert manifest_path.read_bytes() == builder.render_manifest(result["manifest"])
    manifest = json.loads(manifest_path.read_text())
    assert manifest["binary_name"] == "apgr"
    assert manifest["build_identity"] == {
        "corpus_fingerprint": result["corpus_fingerprint"],
        "schema_version": "apg.build-info/v1",
        "target": "linux/arm64",
        "version": "0.6.0",
    }
    assert manifest["schema_version"] == "apg.binary-manifest/v1"
    assert manifest["build_info_schema"] == "apg.build-info/v1"
    assert not {"path", "host", "hostname", "timestamp", "build_timestamp"}.intersection(manifest)
    assert manifest_path.stat().st_mode & 0o777 == 0o644
    assert manifest["target"]["go_target"] == "linux/arm64"
    assert manifest["target"]["python_platform"] == "manylinux_2_17_aarch64"
    assert manifest["target"]["npm_package"] == "@knowledge-forge-ai/apgr-linux-arm64"

    expected = {"path": "/tmp/apgr", "target": "darwin/arm64"}
    monkeypatch.setattr(builder, "build", lambda *_args: expected)
    assert builder.main(["--target", "darwin/arm64", "--output", "/tmp/apgr"]) == 0
    assert json.loads(capsys.readouterr().out) == expected
    monkeypatch.setattr(
        builder,
        "build",
        lambda *_args: (_ for _ in ()).throw(builder.BuildError("bounded")),
    )
    assert builder.main(["--target", "darwin/arm64", "--output", "/tmp/apgr"]) == 1
    assert "apg-build-go-cli: bounded" in capsys.readouterr().err


def test_target_mapping_and_manifest_rendering_are_canonical() -> None:
    assert builder.SUPPORTED_TARGETS == ("darwin/arm64", "linux/amd64", "linux/arm64")
    assert builder.target_mapping("linux/amd64") == {
        "go_target": "linux/amd64",
        "goos": "linux",
        "goarch": "amd64",
        "python_platform": "manylinux_2_17_x86_64",
        "npm_package": "@knowledge-forge-ai/apgr-linux-x64",
        "npm_os": "linux",
        "npm_cpu": "x64",
    }
    manifest = {
        "version": "0.7.0",
        "schema_version": "apg.binary-manifest/v1",
        "sha256": "a" * 64,
        "size_bytes": 3,
        "binary_name": "apgr",
    }
    rendered = builder.render_manifest(manifest)
    assert rendered.endswith(b"\n")
    assert rendered.count(b"\n") == 1
    assert rendered == b'{"binary_name":"apgr","schema_version":"apg.binary-manifest/v1","sha256":"' + b"a" * 64 + b'","size_bytes":3,"version":"0.7.0"}\n'


def test_build_rejects_existing_or_symlink_outputs(tmp_path: Path) -> None:
    root = authority_root(tmp_path)
    existing = tmp_path / "existing"
    existing.write_bytes(b"old")
    with pytest.raises(builder.BuildError, match="already exists"):
        builder.build(root, "darwin/arm64", existing)

    target = tmp_path / "target"
    target.write_bytes(b"old")
    linked = tmp_path / "linked"
    linked.symlink_to(target)
    with pytest.raises(builder.BuildError, match="direct regular"):
        builder.build(root, "darwin/arm64", linked)


def test_manifest_publication_is_no_overwrite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    destination = tmp_path / "manifest.json"
    manifest = {"schema_version": "apg.binary-manifest/v1"}
    monkeypatch.setattr(builder.os, "link", lambda *_args, **_kwargs: (_ for _ in ()).throw(FileExistsError()))
    with pytest.raises(builder.BuildError, match="manifest cannot be written safely"):
        builder.write_manifest(destination, manifest)
    assert not destination.exists()
    assert list(tmp_path.iterdir()) == []


def test_host_build_info_is_checked_against_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = authority_root(tmp_path, b"0.7.0\n")
    go = tmp_path / "go"
    go.write_bytes(b"go")
    go.chmod(0o700)
    monkeypatch.setattr(builder.shutil, "which", lambda _name: str(go))
    monkeypatch.setattr(builder, "_host_target", lambda: "linux/arm64")

    def successful_run(arguments: list[str], **kwargs: object) -> SimpleNamespace:
        if "-o" in arguments:
            Path(arguments[arguments.index("-o") + 1]).write_bytes(b"binary")
            return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "schema_version": "apg.build-info/v1",
                    "version": "0.7.0",
                    "module_path": builder.MODULE,
                    "target": "linux/arm64",
                    "corpus_fingerprint": builder.identities(root)[1],
                    "embedded_corpus_fingerprint": builder.identities(root)[1],
                    "corpus_fingerprint_verified": True,
                }
            ).encode(),
            stderr=b"",
        )

    monkeypatch.setattr(builder.subprocess, "run", successful_run)
    result = builder.build(root, "linux/arm64", tmp_path / "renamed-output")
    assert result["version"] == "0.7.0"
    assert result["binary_name"] == "apgr"
