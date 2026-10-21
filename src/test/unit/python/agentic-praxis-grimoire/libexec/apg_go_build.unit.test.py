from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.test.support import apg_macho_fixtures as macho


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
        lambda args, **_kwargs: (SimpleNamespace(returncode=0, stdout=b"go1.26.9\n")
                                if args[1:3] == ["env", "GOVERSION"] else SimpleNamespace(returncode=1)),
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
        if arguments[1:3] == ["env", "GOVERSION"]:
            assert kwargs["env"]["GOTOOLCHAIN"] == "local"
            return SimpleNamespace(returncode=0, stdout=b"go1.26.9\n")
        if "-o" in arguments:
            observed.update(kwargs)
            output = Path(arguments[arguments.index("-o") + 1])
            output.write_bytes(b"binary")
            return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")
        return SimpleNamespace(
            returncode=0,
            stdout=(
                f"{arguments[-1]}: go1.26.9\n".encode()
                + b" mod github.com/Knowledge-Forge-AI/agentic-praxis-grimoire (devel)\n"
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
        if arguments[1:3] == ["env", "GOVERSION"]:
            return SimpleNamespace(returncode=0, stdout=b"go1.26.9\n")
        if arguments[1:3] == ["version", "-m"]:
            return SimpleNamespace(returncode=0, stdout=f"{arguments[-1]}: go1.26.9\n".encode())
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


def test_old_release_compiler_is_refused_before_build(tmp_path: Path, monkeypatch) -> None:
    root = authority_root(tmp_path)
    go = tmp_path / "go"
    go.write_bytes(b"stand-in")
    go.chmod(0o700)
    monkeypatch.setattr(builder.shutil, "which", lambda _: str(go))
    calls = []
    def run(argv, **kwargs):
        calls.append(argv)
        assert kwargs["env"]["GOTOOLCHAIN"] == "local"
        return SimpleNamespace(returncode=0, stdout=b"go1.25.14\n")
    monkeypatch.setattr(builder.subprocess, "run", run)
    with pytest.raises(builder.BuildError, match="exactly go1.26.9"):
        builder.build(root, "linux/arm64", tmp_path / "out")
    assert len(calls) == 1 and calls[0][1:] == ["env", "GOVERSION"]
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("version", ["go1.25.14", "go1.26.90", "go1.26.9 X:experiment", "devel go1.26.9"])
def test_wrong_actual_compiler_removes_host_and_foreign_output(tmp_path: Path, monkeypatch, version: str) -> None:
    root = authority_root(tmp_path)
    go = tmp_path / "go"
    go.write_bytes(b"stand-in")
    go.chmod(0o700)
    monkeypatch.setattr(builder.shutil, "which", lambda _: str(go))
    for host in ("linux/arm64", "darwin/arm64"):
        monkeypatch.setattr(builder, "_host_target", lambda: host)
        output = tmp_path / "out"
        def run(argv, **kwargs):
            if argv[1] == "env":
                return SimpleNamespace(returncode=0, stdout=b"go1.26.9\n")
            if argv[1] == "build":
                output.write_bytes(b"binary")
                return SimpleNamespace(returncode=0)
            return SimpleNamespace(returncode=0, stdout=f"{output}: {version}\n".encode())
        monkeypatch.setattr(builder.subprocess, "run", run)
        with pytest.raises(builder.BuildError, match="compiled with go1.26.9"):
            builder.build(root, "linux/arm64", output)
        assert not output.exists()
        assert not output.with_name("out.binary-manifest.json").exists()


def test_build_require_native_rejects_foreign_and_cli_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = authority_root(tmp_path)
    monkeypatch.setattr(builder, "_host_target", lambda: "darwin/arm64")
    output = tmp_path / "out"

    # API: require_native=True rejects foreign target
    with pytest.raises(builder.BuildError, match="native target required: linux/amd64 != darwin/arm64"):
        builder.build(root, "linux/amd64", output, require_native=True)

    # API: require_native=False allows foreign target past target check (fails later on toolchain in this test)
    monkeypatch.setattr(builder.shutil, "which", lambda _name: None)
    with pytest.raises(builder.BuildError, match="Go toolchain is unavailable"):
        builder.build(root, "linux/amd64", output, require_native=False)

    # CLI: --require-native rejects foreign target
    code = builder.main(["--target", "linux/amd64", "--output", os.fspath(output), "--require-native"])
    assert code == 1
    assert "native target required: linux/amd64 != darwin/arm64" in capsys.readouterr().err

    # CLI: --require-native accepts native target
    expected = {"path": os.fspath(output), "target": "darwin/arm64"}
    monkeypatch.setattr(builder, "build", lambda *_args, **_kwargs: expected)
    code = builder.main(["--target", "darwin/arm64", "--output", os.fspath(output), "--require-native"])
    assert code == 0
    assert json.loads(capsys.readouterr().out) == expected


# --- Shared Darwin ARM64 deployment predicate (fixture bytes are independent) ---


@pytest.mark.parametrize(
    ("fixture", "command", "minimum", "sdk"),
    [
        ({}, "LC_BUILD_VERSION", "12.0.0", "12.0.0"),
        ({"minimum": (11, 0, 0), "sdk": (11, 0, 0)}, "LC_BUILD_VERSION", "11.0.0", "11.0.0"),
        ({"declarations": ("version_min",)}, "LC_VERSION_MIN_MACOSX", "12.0.0", "12.0.0"),
        ({"sdk": (15, 2, 0)}, "LC_BUILD_VERSION", "12.0.0", "15.2.0"),
    ],
)
def test_supported_deployment_declarations_are_admitted(
    fixture: dict[str, object], command: str, minimum: str, sdk: str
) -> None:
    data = macho.darwin_arm64(**fixture)
    expected = {"command": command, "platform": "macos", "minimum": minimum, "sdk": sdk}
    assert builder.darwin_arm64_deployment(data) == expected
    assert builder.require_release_deployment("darwin/arm64", data) == expected


def test_build_version_tool_table_is_bounded_but_accepted() -> None:
    tools = ((macho.TOOL_LD, macho.encode_version((1, 0, 0))),)
    command = macho.build_version_command((12, 0, 0), (12, 0, 0), tools=tools)
    data = macho.darwin_arm64(declarations=(command,))
    assert builder.require_release_deployment("darwin/arm64", data)["minimum"] == "12.0.0"


@pytest.mark.parametrize(
    "minimum", [(12, 0, 1), (12, 1, 0), (13, 0, 0), (15, 0, 0)]
)
def test_actual_minimum_above_wheel_floor_refuses(minimum: tuple[int, int, int]) -> None:
    data = macho.darwin_arm64(minimum=minimum, sdk=(15, 0, 0))
    with pytest.raises(builder.DeploymentError, match="exceeds macosx_12_0_arm64"):
        builder.require_release_deployment("darwin/arm64", data)
    # The parser still reports the declaration; only admission refuses it.
    assert builder.darwin_arm64_deployment(data)["minimum"] == ".".join(map(str, minimum))


def test_sdk_is_never_mistaken_for_the_minimum() -> None:
    data = macho.darwin_arm64(minimum=(13, 0, 0), sdk=(12, 0, 0))
    with pytest.raises(builder.DeploymentError, match="minimum macOS 13.0.0"):
        builder.require_release_deployment("darwin/arm64", data)


@pytest.mark.parametrize(
    ("fixture", "reason"),
    [
        ({"magic": b"\xfe\xed\xfa\xcf"}, "thin little-endian 64-bit"),
        ({"magic": b"\xce\xfa\xed\xfe"}, "thin little-endian 64-bit"),
        ({"magic": b"\xca\xfe\xba\xbe"}, "thin little-endian 64-bit"),
        ({"cputype": macho.CPU_TYPE_X86_64}, "plain ARM64"),
        ({"cpusubtype": macho.CPU_SUBTYPE_ARM64E}, "plain ARM64"),
        ({"cpusubtype": 0x80000000}, "plain ARM64"),
        ({"filetype": macho.MH_OBJECT}, "not an executable"),
        ({"declarations": ()}, "no macOS minimum declaration"),
        ({"declarations": ("build_version", "version_min")}, "multiple macOS minimum"),
        ({"declarations": ("build_version", "build_version")}, "multiple macOS minimum"),
        ({"declarations": ("build_version_ios",)}, "platform is not macOS"),
        ({"declarations": ("build_version", "version_min_iphoneos")}, "contradictory iphoneos"),
        ({"minimum": (0, 0, 0)}, "declaration is empty"),
        ({"ncmds": 0}, "count is out of bounds"),
        ({"ncmds": 513}, "count is out of bounds"),
        ({"sizeofcmds": (1 << 20) + 8}, "region is out of bounds"),
        ({"truncate": 31}, "header is truncated"),
        ({"truncate": 48}, "region is out of bounds"),
    ],
)
def test_malformed_or_unsupported_darwin_bytes_refuse(fixture: dict[str, object], reason: str) -> None:
    data = macho.darwin_arm64(**fixture)
    with pytest.raises(builder.DeploymentError, match=reason):
        builder.require_release_deployment("darwin/arm64", data)


def test_command_region_arithmetic_is_exact() -> None:
    region = len(macho.uuid_command()) + len(macho.build_version_command((12, 0, 0), (12, 0, 0)))
    exact = macho.darwin_arm64()
    assert builder.require_release_deployment("darwin/arm64", exact)
    # One extra declared command overruns the region; a short region cuts the
    # last command; a long region leaves unconsumed slack.
    for fixture, reason in (
        ({"ncmds": 3}, "overruns its region"),
        ({"sizeofcmds": region - 8}, "load-command size is invalid"),
        ({"sizeofcmds": region + 8}, "do not exactly fill"),
    ):
        with pytest.raises(builder.DeploymentError, match=reason):
            builder.require_release_deployment("darwin/arm64", macho.darwin_arm64(**fixture))


@pytest.mark.parametrize(
    ("command", "reason"),
    [
        (macho.build_version_command((12, 0, 0), (12, 0, 0), cmdsize=20), "load-command size is invalid"),
        (macho.build_version_command((12, 0, 0), (12, 0, 0), cmdsize=4), "load-command size is invalid"),
        (macho.build_version_command((12, 0, 0), (12, 0, 0), cmdsize=32), "tool table is invalid"),
        (macho.build_version_command((12, 0, 0), (12, 0, 0), cmdsize=16), "LC_BUILD_VERSION size"),
        (macho.version_min_command((12, 0, 0), (12, 0, 0), cmdsize=24), "LC_VERSION_MIN_MACOSX size"),
    ],
)
def test_declaration_command_sizes_are_exact(command: bytes, reason: str) -> None:
    data = macho.darwin_arm64(declarations=(command,))
    with pytest.raises(builder.DeploymentError, match=reason):
        builder.require_release_deployment("darwin/arm64", data)


def test_linux_targets_are_unchanged_and_unknown_targets_refuse() -> None:
    elf = b"\x7fELF" + b"\0" * 60
    for target in ("linux/amd64", "linux/arm64"):
        assert builder.require_release_deployment(target, elf) is None
        assert builder.require_release_deployment(target, macho.darwin_arm64(minimum=(15, 0, 0))) is None
    with pytest.raises(builder.BuildError, match="unsupported target"):
        builder.require_release_deployment("windows/amd64", elf)
    with pytest.raises(builder.DeploymentError, match="thin little-endian 64-bit"):
        builder.require_release_deployment("darwin/arm64", elf)


def test_deployment_floor_is_derived_from_the_canonical_wheel_tag(monkeypatch: pytest.MonkeyPatch) -> None:
    assert builder.TARGETS["darwin/arm64"]["python_platform"] == "macosx_12_0_arm64"
    assert builder._deployment_ceiling("darwin/arm64") == (12, 0, 0)
    data = macho.darwin_arm64(minimum=(12, 0, 0))
    lowered = {**builder.TARGETS, "darwin/arm64": {**builder.TARGETS["darwin/arm64"], "python_platform": "macosx_11_0_arm64"}}
    monkeypatch.setattr(builder, "TARGETS", lowered)
    with pytest.raises(builder.DeploymentError, match="exceeds macosx_11_0_arm64"):
        builder.require_release_deployment("darwin/arm64", data)


def _darwin_go(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, image: bytes) -> None:
    go = tmp_path / "go"
    go.write_bytes(b"stand-in")
    go.chmod(0o700)
    monkeypatch.setattr(builder.shutil, "which", lambda _name: str(go))
    monkeypatch.setattr(builder, "_host_target", lambda: "linux/amd64")

    def run(arguments: list[str], **_kwargs: object) -> SimpleNamespace:
        if arguments[1:3] == ["env", "GOVERSION"]:
            return SimpleNamespace(returncode=0, stdout=b"go1.26.9\n")
        if "-o" in arguments:
            Path(arguments[arguments.index("-o") + 1]).write_bytes(image)
            return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")
        return SimpleNamespace(returncode=0, stdout=macho.recorded_go_version_m(arguments[-1]).encode(), stderr=b"")

    monkeypatch.setattr(builder.subprocess, "run", run)


def test_builder_admits_supported_darwin_output_and_writes_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = authority_root(tmp_path, b"0.13.1\n")
    image = macho.darwin_arm64()
    _darwin_go(tmp_path, monkeypatch, image)
    output = tmp_path / "out/apgr"
    result = builder.build(root, "darwin/arm64", output)
    manifest = json.loads(Path(result["manifest_path"]).read_text())
    assert output.read_bytes() == image
    assert manifest["sha256"] == result["sha256"] and manifest["size_bytes"] == len(image)
    assert manifest["target"]["python_platform"] == "macosx_12_0_arm64"


def test_builder_refuses_overfloor_darwin_output_before_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = authority_root(tmp_path, b"0.13.1\n")
    _darwin_go(tmp_path, monkeypatch, macho.darwin_arm64(minimum=macho.OVERFLOOR_MINIMUM))
    output = tmp_path / "out/apgr"
    with pytest.raises(builder.DeploymentError, match="exceeds macosx_12_0_arm64"):
        builder.build(root, "darwin/arm64", output)
    assert not output.exists()
    assert not output.with_name("apgr.binary-manifest.json").exists()
