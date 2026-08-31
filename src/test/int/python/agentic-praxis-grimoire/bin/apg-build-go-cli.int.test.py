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
    assert version == "0.8.0"
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
    assert first_result["version"] == "0.8.0"
    assert first_result["sha256"] == second_result["sha256"]
    assert first.read_bytes() == second.read_bytes()
    version = subprocess.run(
        [first, "--version"], check=True, stdout=subprocess.PIPE, text=True
    )
    assert version.stdout == "apgr 0.8.0\n"
    built = subprocess.run(
        [first, "build-info"], check=True, stdout=subprocess.PIPE, text=True,
        env={"APGR_VERSION": "runtime-override", "APGR_CORPUS": "runtime-override"},
    )
    info = json.loads(built.stdout)
    assert info["version"] == "0.8.0"
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
