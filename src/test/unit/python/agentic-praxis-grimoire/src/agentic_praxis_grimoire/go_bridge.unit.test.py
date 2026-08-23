from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
import signal

import pytest


bridge = importlib.import_module("agentic_praxis_grimoire.go_bridge")


def _build_info(*, version: str | None = None, corpus: str | None = None) -> dict[str, object]:
    expected_version, expected_corpus = bridge._package_identities()
    selected_version = expected_version if version is None else version
    selected_corpus = expected_corpus if corpus is None else corpus
    return {
        "schema_version": bridge.BUILD_INFO_SCHEMA,
        "version": selected_version,
        "module_path": bridge.MODULE_PATH,
        "target": bridge._host_target(),
        "corpus_fingerprint": selected_corpus,
        "embedded_corpus_fingerprint": expected_corpus,
        "corpus_fingerprint_verified": selected_corpus == expected_corpus,
        "report_schema_versions": {"envelope": 1},
    }


def _fake_binary(tmp_path: Path, info: dict[str, object] | None = None) -> Path:
    binary = tmp_path / "apgr-go"
    payload = json.dumps(_build_info() if info is None else info, separators=(",", ":"))
    binary.write_text(
        "#!/bin/sh\n"
        f"if [ \"$1\" = build-info ]; then printf '%s\\n' '{payload}'; else exit 7; fi\n",
        encoding="utf-8",
    )
    binary.chmod(0o700)
    return binary


def _manifest(binary: Path) -> bytes:
    version, corpus = bridge._package_identities()
    value = {
        "build_flags": list(bridge.BUILD_FLAGS),
        "build_info_schema": bridge.BUILD_INFO_SCHEMA,
        "build_identity": {
            "corpus_fingerprint": corpus,
            "schema_version": bridge.BUILD_INFO_SCHEMA,
            "target": bridge._host_target(),
            "version": version,
        },
        "binary_name": "apgr",
        "corpus_fingerprint": corpus,
        "module_path": bridge.MODULE_PATH,
        "schema_version": bridge.BINARY_MANIFEST_SCHEMA,
        "sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "size_bytes": binary.stat().st_size,
        "target": bridge._host_target(),
        "version": version,
    }
    return bridge._canonical_json(value)


def test_explicit_binary_is_absolute_direct_and_first(tmp_path: Path) -> None:
    binary = _fake_binary(tmp_path)
    invocation = bridge.locate({"APGR_GO_BINARY": str(binary)})
    assert invocation.argv == (str(binary),)
    assert invocation.source_root is None
    assert invocation.kind == "override"


def test_explicit_binary_rejects_missing_relative_and_symlink(tmp_path: Path) -> None:
    with pytest.raises(bridge.GoBridgeError, match="absolute clean"):
        bridge.locate({"APGR_GO_BINARY": "relative/apgr"})
    missing = tmp_path / "missing"
    with pytest.raises(bridge.GoBridgeError, match="unavailable"):
        bridge.locate({"APGR_GO_BINARY": str(missing)})
    target = _fake_binary(tmp_path)
    link = tmp_path / "link"
    link.symlink_to(target)
    with pytest.raises(bridge.GoBridgeError, match="direct regular"):
        bridge.locate({"APGR_GO_BINARY": str(link)})


def test_direct_run_verifies_build_info_then_uses_exact_argv_and_no_shell(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    binary = _fake_binary(tmp_path)
    repository = tmp_path / "repository"
    repository.mkdir()
    observed: list[tuple[list[str], dict[str, object]]] = []

    class FakeProcess:
        def __init__(self, arguments: list[str], **kwargs: object) -> None:
            observed.append((arguments, kwargs))

        def wait(self) -> int:
            return 7

        def send_signal(self, _value: int) -> None:
            pass

    monkeypatch.setattr(bridge.subprocess, "Popen", FakeProcess)
    monkeypatch.setattr(bridge, "_build_info", lambda *_args, **_kwargs: _build_info())
    environment = {"APGR_GO_BINARY": str(binary), "SAFE": "value"}
    assert bridge.run(["--version"], repository_root=repository, environment=environment) == 7
    assert observed == [
        ([str(binary), "--version"], {
            "cwd": repository,
            "env": environment,
            "shell": False,
        })
    ]


def test_source_checkout_builds_release_like_binary_and_cleans_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    source = tmp_path / "source"
    (source / "src" / "agentic_praxis_grimoire" / "resources").mkdir(parents=True)
    (source / "src" / "agentic_praxis_grimoire" / "VERSION").write_text("0.7.0\n")
    (source / "src" / "agentic_praxis_grimoire" / "resources" / "skill-metadata.json").write_bytes(b"corpus")
    builds: list[tuple[list[str], dict[str, object]]] = []
    executions: list[tuple[list[str], dict[str, object]]] = []
    monkeypatch.setattr(
        bridge,
        "locate",
        lambda _environment=None: bridge.Invocation(("/tool/go",), source, source, "source"),
    )
    monkeypatch.setattr(bridge, "_verify_build_info", lambda *_args, **_kwargs: None)

    def fake_run(arguments: list[str], **kwargs: object) -> SimpleNamespace:
        builds.append((arguments, kwargs))
        output = Path(arguments[arguments.index("-o") + 1])
        output.write_bytes(b"built")
        output.chmod(0o700)
        return SimpleNamespace(returncode=0, stderr="", stdout=b"")

    class FakeProcess:
        def __init__(self, arguments: list[str], **kwargs: object) -> None:
            executions.append((arguments, kwargs))

        def wait(self) -> int:
            return 0

        def send_signal(self, _value: int) -> None:
            pass

    monkeypatch.setattr(bridge.subprocess, "run", fake_run)
    monkeypatch.setattr(bridge.subprocess, "Popen", FakeProcess)
    assert bridge.run(["build-info"], repository_root=repository) == 0
    assert builds[0][0][0:4] == ["/tool/go", "build", "-trimpath", "-buildvcs=false"]
    assert "-ldflags" in builds[0][0]
    assert "-buildid=" in builds[0][0][builds[0][0].index("-ldflags") + 1]
    binary = Path(executions[0][0][0])
    assert executions[0][0][1:] == ["build-info"]
    assert executions[0][1]["cwd"] == repository
    assert builds[0][1]["shell"] is False
    assert executions[0][1]["shell"] is False
    assert not binary.parent.exists()


def test_bundled_manifest_is_canonical_and_binds_hash_target_and_identity(
    tmp_path: Path,
) -> None:
    binary = _fake_binary(tmp_path)
    manifest = tmp_path / "apgr.binary-manifest.json"
    manifest.write_bytes(_manifest(binary))
    bridge._validate_manifest(binary, manifest)
    manifest.write_bytes(manifest.read_bytes().replace(b"\n", b" \n", 1))
    with pytest.raises(bridge.GoBridgeError, match="canonical"):
        bridge._validate_manifest(binary, manifest)


def test_bundled_manifest_rejects_tampered_binary(tmp_path: Path) -> None:
    binary = _fake_binary(tmp_path)
    manifest = tmp_path / "apgr.binary-manifest.json"
    manifest.write_bytes(_manifest(binary))
    binary.write_bytes(binary.read_bytes() + b"tamper")
    with pytest.raises(bridge.GoBridgeError, match="size|hash"):
        bridge._validate_manifest(binary, manifest)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("version", "0.6.0", "version"),
        ("corpus_fingerprint", "0" * 64, "corpus"),
        ("schema_version", "wrong", "schema"),
    ),
)
def test_explicit_binary_build_info_mismatch_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: object,
    message: str,
) -> None:
    binary = _fake_binary(tmp_path)
    info = _build_info()
    info[field] = value
    monkeypatch.setattr(bridge, "_build_info", lambda *_args, **_kwargs: info)
    with pytest.raises(bridge.GoBridgeError, match=message):
        bridge._verify_build_info(binary, environment=None, release_required=False)


def test_missing_checkout_has_no_python_semantic_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bridge, "_source_root", lambda: None)
    with pytest.raises(bridge.GoBridgeError, match="portable Go APGR"):
        bridge.locate({})


def test_source_checkout_requires_go_toolchain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(bridge, "_source_root", lambda: tmp_path)
    monkeypatch.setattr(bridge.shutil, "which", lambda _name: None)
    with pytest.raises(bridge.GoBridgeError, match="Go toolchain"):
        bridge.locate({})


@pytest.mark.parametrize("stderr", ("compiler detail", ""))
def test_source_build_failure_is_bounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stderr: str
) -> None:
    source = tmp_path / "source"
    (source / "src" / "agentic_praxis_grimoire" / "resources").mkdir(parents=True)
    (source / "src" / "agentic_praxis_grimoire" / "VERSION").write_text("0.7.0\n")
    (source / "src" / "agentic_praxis_grimoire" / "resources" / "skill-metadata.json").write_bytes(b"corpus")
    monkeypatch.setattr(
        bridge,
        "locate",
        lambda _environment=None: bridge.Invocation(("/tool/go",), source, source, "source"),
    )
    monkeypatch.setattr(
        bridge.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stderr=stderr, stdout=b""),
    )
    match = "compiler detail" if stderr else "build failed"
    with pytest.raises(bridge.GoBridgeError, match=match):
        bridge.run(["build-info"], repository_root=tmp_path)


@pytest.mark.parametrize(
    ("returncode", "expected"), ((-signal.SIGINT, 130), (-signal.SIGTERM, 1))
)
def test_negative_child_status_is_classified(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    returncode: int,
    expected: int,
) -> None:
    binary = _fake_binary(tmp_path)
    monkeypatch.setattr(bridge, "_verify_invocation", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(bridge, "_execute", lambda *_args, **_kwargs: returncode)
    assert bridge.run(
        ["--version"],
        repository_root=None,
        environment={"APGR_GO_BINARY": str(binary)},
    ) == expected


def test_captured_negative_child_status_is_normalised(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    binary = _fake_binary(tmp_path)
    monkeypatch.setattr(bridge, "_verify_invocation", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        bridge,
        "_execute_capture",
        lambda *_args, **_kwargs: bridge.CapturedResult(-signal.SIGINT, b"", b""),
    )
    result = bridge.run_capture(
        ["response", "capture"],
        repository_root=None,
        environment={"APGR_GO_BINARY": str(binary)},
    )
    assert result.returncode == 130


def test_testing_environment_maps_legacy_pause_controls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    binary = _fake_binary(tmp_path)
    captured: dict[str, str] = {}

    def execute(_arguments, *, cwd, environment):
        del cwd
        assert environment is not None
        captured.update(environment)
        return 0

    monkeypatch.setattr(bridge, "_verify_invocation", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(bridge, "_execute", execute)
    environment = {
        "APGR_GO_BINARY": str(binary),
        "AGENT_REPORT_TESTING": "1",
        "AGENT_REPORT_TEST_PAUSE_STEP": "ready",
        "AGENT_REPORT_TEST_SIGNAL_DIR": "/tmp/signals",
    }
    assert bridge.run([], repository_root=None, environment=environment) == 0
    assert captured["APG_REPORT_GO_TESTING"] == "1"
    assert captured["APG_REPORT_GO_TEST_PAUSE_STEP"] == "ready"
    assert captured["APG_REPORT_GO_TEST_SIGNAL_DIR"] == "/tmp/signals"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_version", "wrong", "schema"),
        ("version", "0.6.0", "version"),
        ("module_path", "example.invalid/module", "module"),
        ("build_info_schema", "wrong", "build-info schema"),
        ("build_flags", [], "build flags"),
        ("build_identity", {}, "build identity"),
        ("target", "linux/amd64", "target"),
        ("binary_name", "wrong", "executable"),
        ("corpus_fingerprint", "0" * 64, "corpus"),
        ("size_bytes", True, "size"),
        ("sha256", "not-a-hash", "hash"),
    ],
)
def test_manifest_field_matrix_fails_closed(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    binary = _fake_binary(tmp_path)
    manifest = json.loads(_manifest(binary))
    manifest[field] = value
    path = tmp_path / "apgr.binary-manifest.json"
    path.write_bytes(bridge._canonical_json(manifest))
    with pytest.raises(bridge.GoBridgeError, match=message):
        bridge._validate_manifest(binary, path)


def test_manifest_shape_json_and_binary_type_fail_closed(tmp_path: Path) -> None:
    binary = _fake_binary(tmp_path)
    path = tmp_path / "apgr.binary-manifest.json"
    path.write_bytes(b"[]\n")
    with pytest.raises(bridge.GoBridgeError, match="JSON object"):
        bridge._validate_manifest(binary, path)
    path.write_bytes(b'{"a":1,"a":2}\n')
    with pytest.raises(bridge.GoBridgeError, match="malformed"):
        bridge._validate_manifest(binary, path)
    with pytest.raises(bridge.GoBridgeError, match="canonical JSON"):
        bridge._canonical_json(float("nan"))
    with pytest.raises(ValueError, match="duplicate"):
        bridge._reject_duplicate_pairs([("a", 1), ("a", 2)])
    assert bridge._manifest_target({"goos": "linux", "goarch": "arm64"}) == "linux/arm64"
    assert bridge._manifest_target({"goos": 1, "goarch": "arm64"}) is None

    direct = tmp_path / "direct"
    direct.mkdir()
    with pytest.raises(bridge.GoBridgeError, match="direct regular"):
        bridge._direct_file_bytes(direct, "fixture")
    with pytest.raises(bridge.GoBridgeError, match="not executable"):
        bridge._direct_executable(path, "fixture")


@pytest.mark.parametrize(
    ("field", "value", "message", "release_required"),
    [
        ("module_path", "wrong", "module", False),
        ("schema_version", "wrong", "schema", False),
        ("target", "linux/amd64", "target", False),
        ("version", "wrong", "version", False),
        ("corpus_fingerprint", "0" * 64, "corpus", False),
        ("embedded_corpus_fingerprint", "0" * 64, "embedded", True),
        ("corpus_fingerprint_verified", False, "unverified", True),
        ("report_schema_versions", None, "unavailable", False),
    ],
)
def test_build_info_validation_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: object,
    message: str,
    release_required: bool,
) -> None:
    binary = _fake_binary(tmp_path)
    info = _build_info()
    info[field] = value
    monkeypatch.setattr(bridge, "_build_info", lambda *_args, **_kwargs: info)
    with pytest.raises(bridge.GoBridgeError, match=message):
        bridge._verify_build_info(
            binary,
            environment=None,
            release_required=release_required,
        )


def test_host_and_child_environment_refusals_are_explicit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bridge.sys, "platform", "unsupported")
    with pytest.raises(bridge.GoBridgeError, match="unsupported"):
        bridge._host_target()
    monkeypatch.setattr(bridge.sys, "platform", "darwin")
    monkeypatch.setattr(bridge.platform, "machine", lambda: "unsupported")
    with pytest.raises(bridge.GoBridgeError, match="unsupported"):
        bridge._host_target()

    monkeypatch.delenv("AGENT_REPORT_TESTING", raising=False)
    assert bridge._child_environment(None) is None
    monkeypatch.setenv("AGENT_REPORT_TESTING", "1")
    child = bridge._child_environment(None)
    assert child is not None and child["APG_REPORT_GO_TESTING"] == "1"
