from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import subprocess

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
SPEC = importlib.util.spec_from_file_location("apg_go_build", ROOT / "libexec/apg_go_build.py")
assert SPEC is not None and SPEC.loader is not None
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


def _host_target() -> str:
    goos = {"Darwin": "darwin", "Linux": "linux"}.get(platform.system(), "")
    goarch = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "amd64"}.get(
        platform.machine(), ""
    )
    return f"{goos}/{goarch}"


def test_identity_uses_python_version_and_metadata_resource() -> None:
    version, corpus = builder.identities(ROOT)
    resource = ROOT / "src/agentic_praxis_grimoire/resources/skill-metadata.json"
    assert version == "0.13.1"
    assert corpus == hashlib.sha256(resource.read_bytes()).hexdigest()


def test_unsupported_target_fails_before_output(tmp_path: Path) -> None:
    output = tmp_path / "apgr"
    with pytest.raises(builder.BuildError, match="unsupported target"):
        builder.build(ROOT, "windows/amd64", output)
    assert not output.exists()


def test_release_like_host_build_is_injected_and_reproducible(tmp_path: Path) -> None:
    target = _host_target()
    if target not in builder.SUPPORTED_TARGETS:
        pytest.skip("host is outside the frozen v0.8 target matrix")
    first = tmp_path / "first" / "apgr"
    second = tmp_path / "second" / "apgr"
    first_result = builder.build(ROOT, target, first)
    second_result = builder.build(ROOT, target, second)
    assert first_result["version"] == "0.13.1"
    assert first_result["sha256"] == second_result["sha256"]
    assert first.read_bytes() == second.read_bytes()
    version = subprocess.run(
        [first, "--version"], check=True, stdout=subprocess.PIPE, text=True
    )
    assert version.stdout == "apgr 0.13.1\n"
    built = subprocess.run(
        [first, "build-info"], check=True, stdout=subprocess.PIPE, text=True,
        env={"APGR_VERSION": "runtime-override", "APGR_CORPUS": "runtime-override"},
    )
    info = json.loads(built.stdout)
    assert info["version"] == "0.13.1"
    assert info["corpus_fingerprint"] == first_result["corpus_fingerprint"]
    assert info["embedded_corpus_fingerprint"] == first_result["corpus_fingerprint"]
    assert info["corpus_fingerprint_verified"] is True
    assert info["target"] == target
    assert info["report_schema_versions"] == {
        "envelope": 1,
        "git_show": 2,
        "git_diff": 1,
        "operational": 1,
    }


def test_actual_darwin_arm64_output_satisfies_the_strict_deployment_predicate(tmp_path: Path) -> None:
    # SourceB evidence: real exact-go1.26.9 Darwin ARM64 bytes, not a synthetic
    # fixture, must parse as one plain ARM64 MH_EXECUTE with exactly one macOS
    # minimum declaration at or below the macosx_12_0_arm64 wheel floor.
    if _host_target() != "darwin/arm64":
        pytest.skip("actual Darwin ARM64 output requires a native darwin/arm64 host")
    output = tmp_path / "darwin" / "apgr"
    result = builder.build(ROOT, "darwin/arm64", output, require_native=True)
    data = output.read_bytes()
    deployment = builder.darwin_arm64_deployment(data)
    assert builder.require_release_deployment("darwin/arm64", data) == deployment
    assert deployment["platform"] == "macos"
    assert deployment["command"] in {"LC_BUILD_VERSION", "LC_VERSION_MIN_MACOSX"}
    minimum = tuple(int(part) for part in deployment["minimum"].split("."))
    assert (0, 0, 0) < minimum <= (12, 0, 0)
    # The SDK is reported separately and is never the admission value.
    assert deployment["sdk"].count(".") == 2
    assert result["manifest"]["target"]["python_platform"] == "macosx_12_0_arm64"
