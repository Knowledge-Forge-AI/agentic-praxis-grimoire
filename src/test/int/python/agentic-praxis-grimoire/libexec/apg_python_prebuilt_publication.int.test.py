"""Validate supplied prebuilt inputs through real files, without assembling packages.

Synthetic binary bytes and handcrafted ZIP views are fixtures, never native
consumer or release qualification. All builder calls stop before assembly.
"""

from __future__ import annotations

import importlib
import json
import sys
import zipfile
from pathlib import Path

import pytest

from src.test.apg_test_support import repository_root

ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "libexec"))

go_build = importlib.import_module("apg_go_build")
buildinfo = importlib.import_module("apg_go_buildinfo")
prebuilt = importlib.import_module("apg_python_prebuilt_publication")
publication = importlib.import_module("apg_python_publication")


@pytest.fixture
def inputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    artifacts, work, output = tmp_path / "inputs", tmp_path / "work", tmp_path / "output"
    artifacts.mkdir()
    work.mkdir()
    version, corpus = go_build.identities(ROOT)
    directories = {}
    for index, target in enumerate(publication.SUPPORTED_TARGETS):
        directory = artifacts / (target if index == 1 else target.replace("/", "-"))
        directory.mkdir(parents=True)
        data = buildinfo.make_synthetic_binary(
            target=target, format_type="macho" if target.startswith("darwin") else "elf"
        )
        (directory / "apgr").write_bytes(data)
        manifest = go_build._manifest(target=target, version=version, corpus=corpus, binary=data)
        name = ("apgr.binary-manifest.json", "manifest.json", "binary-manifest.json")[index]
        (directory / name).write_bytes(go_build.render_manifest(manifest))
        if index != 1:  # Absent recorded text is a supported input variant.
            go_version, mod_text = buildinfo.extract_raw_build_info(data)
            (directory / "go-version-m.txt").write_text(f"apgr: {go_version}\n{mod_text}")
        directories[target] = directory

    def forbidden(*args, **kwargs):
        pytest.fail("input refusal unexpectedly reached package assembly")

    monkeypatch.setattr(prebuilt, "_build_prebuilt_once", forbidden)
    return artifacts, work, output, directories


@pytest.mark.parametrize("defect, message", [
    ("missing-target", "artifact directory for target linux/arm64 not found"),
    ("linked-target", "artifact directory for target linux/arm64 not found"),
    ("missing-binary", "prebuilt binary for linux/arm64 is unavailable"),
    ("missing-manifest", "prebuilt binary manifest missing"),
    ("linked-manifest", "prebuilt binary manifest missing"),
    ("binary-drift", "prebuilt binary validation failed"),
    ("manifest-drift", "prebuilt binary validation failed"),
    ("malformed-manifest", "prebuilt binary validation failed"),
    ("compiler-drift", "build info failed validation"),
    ("recorded-drift", "recorded setting GOARCH"),
    ("unreadable-recorded", "recorded go version metadata is unreadable"),
])
def test_input_custody_refuses_before_assembly(inputs, tmp_path: Path, defect: str, message: str):
    artifacts, work, output, directories = inputs
    directory = directories["linux/arm64"]  # Earlier targets validate real manifests first.
    manifest_path = directory / "binary-manifest.json"
    if defect in ("missing-target", "linked-target"):
        moved = tmp_path / "held-target"
        directory.rename(moved)
        if defect == "linked-target":
            directory.symlink_to(moved, target_is_directory=True)
    elif defect == "missing-binary":
        (directory / "apgr").unlink()
    elif defect in ("missing-manifest", "linked-manifest"):
        data = manifest_path.read_bytes()
        manifest_path.unlink()
        if defect == "linked-manifest":
            held = tmp_path / "held-manifest.json"
            held.write_bytes(data)
            manifest_path.symlink_to(held)
    elif defect == "binary-drift":
        with (directory / "apgr").open("ab") as stream:
            stream.write(b"tamper")
    elif defect == "manifest-drift":
        manifest = json.loads(manifest_path.read_bytes())
        manifest["version"] = "9.9.9"
        manifest_path.write_bytes(go_build.render_manifest(manifest))
    elif defect == "malformed-manifest":
        manifest_path.write_bytes(b"[]")
    elif defect == "compiler-drift":
        (directory / "apgr").write_bytes(buildinfo.make_synthetic_binary(go_version="go1.0"))
    elif defect == "recorded-drift":
        recorded = directory / "go-version-m.txt"
        recorded.write_text(recorded.read_text().replace("GOARCH=arm64", "GOARCH=wrong"))
    else:
        (directory / "go-version-m.txt").write_bytes(b"\xff")
    with pytest.raises(publication.PublicationError, match=message):
        prebuilt.build_prebuilt_bundle(ROOT, artifacts, output, work)
    assert not output.exists()
    assert list(work.iterdir()) == []


@pytest.mark.parametrize("defect, message", [
    ("existing-output", "publication output must not already exist"),
    ("linked-output", "publication output must not already exist"),
    ("missing-parent", "publication output parent is unavailable"),
    ("linked-parent", "publication output parent must be one real direct directory"),
    ("existing-build-a", "publication build roots must not already exist"),
    ("existing-build-b", "publication build roots must not already exist"),
])
def test_output_custody_refuses_before_reading_inputs(inputs, tmp_path: Path, defect: str, message: str):
    artifacts, work, output, _ = inputs
    if defect == "existing-output":
        output.mkdir()
    elif defect == "linked-output":
        output.symlink_to(tmp_path / "missing")
    elif defect == "missing-parent":
        output = tmp_path / "missing-parent" / "out"
    elif defect == "linked-parent":
        parent = tmp_path / "linked-parent"
        parent.symlink_to(work, target_is_directory=True)
        output = parent / "out"
    else:
        (work / defect.removeprefix("existing-")).mkdir()
    before = {p.name for p in work.iterdir()}
    with pytest.raises(publication.PublicationError, match=message):
        prebuilt.build_prebuilt_bundle(ROOT, artifacts, output, work)
    assert {p.name for p in work.iterdir()} == before


@pytest.mark.parametrize("defect", ["none", "missing-binary", "missing-manifest", "binary-drift", "manifest-drift", "malformed"])
def test_wheel_view_custody_uses_actual_zip_members(tmp_path: Path, defect: str):
    binary, manifest = b"synthetic fixture bytes", b'{"fixture":true}\n'
    path = tmp_path / "fixture-view.zip"
    if defect == "malformed":
        path.write_bytes(b"invalid ZIP")
    else:
        with zipfile.ZipFile(path, "w") as archive:
            if defect != "missing-binary":
                archive.writestr("agentic_praxis_grimoire/bin/apgr", b"tampered" if defect == "binary-drift" else binary)
            if defect != "missing-manifest":
                archive.writestr("agentic_praxis_grimoire/bin/apgr.binary-manifest.json", b"{}" if defect == "manifest-drift" else manifest)
    before = path.read_bytes()
    if defect == "none":
        prebuilt._validate_wheel_prebuilt_binary(path, "linux/amd64", binary, manifest)
    else:
        messages = {"missing-binary": "missing binary", "missing-manifest": "missing manifest",
                    "binary-drift": "differs from supplied prebuilt binary", "manifest-drift": "differs from supplied manifest",
                    "malformed": "malformed"}
        with pytest.raises(publication.PublicationError, match=messages[defect]):
            prebuilt._validate_wheel_prebuilt_binary(path, "linux/amd64", binary, manifest)
    assert path.read_bytes() == before
