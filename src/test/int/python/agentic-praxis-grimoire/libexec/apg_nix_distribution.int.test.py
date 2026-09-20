"""Installed-output verification of the real runtime set through the CLI.

The fixture filters this repository's exact ``nix/distribution.json`` runtime
set as ``nix/source.nix`` does, then installs it the way ``nix/package.nix``
does: copied members, ``env`` shebangs
rewritten to store interpreters, generated binary and manifest, command
wrappers, and a marker written by the real ``write-marker`` process. The Go
binary bytes are a stand-in; the binary build is outside this contract.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
SCRIPT = ROOT / "libexec/apg_nix_distribution.py"
_SPEC = importlib.util.spec_from_file_location("apg_nix_distribution", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
nixdist = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(nixdist)
ENV_SHEBANG = re.compile(rb"#!/usr/bin/env ([A-Za-z0-9_.+-]+)\n")


def _cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-B", os.fspath(SCRIPT), *arguments], cwd=ROOT,
                          stdin=subprocess.DEVNULL, capture_output=True, text=True, check=False)


def _filtered_source(source: Path) -> Path:
    """Copy the declared runtime minus bytecode and excluded names (nix/source.nix)."""
    data = nixdist.load_distribution(ROOT)
    for relative, member in nixdist.runtime_files(ROOT, data).items():
        if relative.endswith(".pyc") or set(Path(relative).parts) & set(data["excluded_names"]):
            continue
        (source / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(member, source / relative)
    (source / "nix").mkdir()
    shutil.copy2(ROOT / nixdist.DISTRIBUTION_PATH, source / nixdist.DISTRIBUTION_PATH)
    return source


def _install(output: Path, source_root: Path) -> Path:
    data = nixdist.load_distribution(source_root)
    runtime = output / nixdist.RUNTIME_SUBPATH
    for relative, source in nixdist.runtime_files(source_root, data).items():
        target = runtime / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        content = target.read_bytes()
        rewritten = ENV_SHEBANG.match(content)
        if rewritten:  # patchShebangs: `env <program>` -> one store interpreter
            program = rewritten.group(1).decode()
            interpreter = f"#!/nix/store/{'0' * 32}-{program}/bin/{program}\n".encode()
            target.write_bytes(interpreter + content[rewritten.end():])
    binary = b"\x7fELF stand-in apgr"
    corpus = hashlib.sha256((runtime / nixdist.CORPUS_PATH).read_bytes()).hexdigest()
    version = (runtime / nixdist.VERSION_PATH).read_text(encoding="ascii").strip()
    manifest = {"build_identity": {"target": data["systems"]["aarch64-darwin"]}, "corpus_fingerprint": corpus,
                "sha256": hashlib.sha256(binary).hexdigest(), "size_bytes": len(binary), "version": version}
    (runtime / nixdist.PACKAGE_BIN).mkdir(parents=True, exist_ok=True)
    (runtime / nixdist.PACKAGE_BIN / nixdist.BINARY_NAME).write_bytes(binary)
    (runtime / nixdist.PACKAGE_BIN / nixdist.BINARY_NAME).chmod(0o555)
    (runtime / nixdist.PACKAGE_BIN / nixdist.MANIFEST_NAME).write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="ascii")
    (output / "bin").mkdir()
    for command in data["commands"]:
        wrapper = output / "bin" / command
        wrapper.write_text(f'#!/bin/sh\nexec "{runtime}/bin/{command}" "$@"\n', encoding="utf-8")
        wrapper.chmod(0o755)
    marked = _cli("write-marker", "--runtime", os.fspath(runtime))
    assert marked.returncode == 0, marked.stderr
    return runtime


@pytest.fixture(scope="module")
def source(tmp_path_factory) -> Path:
    return _filtered_source(tmp_path_factory.mktemp("nix-source"))


@pytest.fixture(scope="module")
def installed(tmp_path_factory, source: Path) -> Path:
    output = tmp_path_factory.mktemp("nix-installed") / "out"
    _install(output, source)
    return output


@pytest.fixture
def copy(installed: Path, tmp_path: Path) -> Path:
    output = tmp_path / "out"
    shutil.copytree(installed, output, symlinks=True)
    runtime = output / nixdist.RUNTIME_SUBPATH
    marker = runtime / nixdist.MARKER_NAME
    marker.chmod(0o644)
    marker.write_bytes(nixdist.render_marker(runtime))  # the marker names its own runtime root
    for command in nixdist.load_distribution(ROOT)["commands"]:
        (output / "bin" / command).write_text(f'#!/bin/sh\nexec "{runtime}/bin/{command}" "$@"\n')
    return output


def _errors(output: Path, source: Path, system: str = "aarch64-darwin") -> list[str]:
    completed = _cli("verify-installed", "--package", os.fspath(output), "--source", os.fspath(source),
                     "--system", system)
    assert completed.returncode == (1 if completed.stderr else 0)
    return [line.removeprefix("apg_nix_distribution: ") for line in completed.stderr.splitlines()]


def test_real_runtime_set_installs_marks_and_verifies(installed: Path, source: Path) -> None:
    runtime = installed / nixdist.RUNTIME_SUBPATH
    assert len(nixdist.runtime_files(source, nixdist.load_distribution(source))) > 100
    completed = _cli("verify-installed", "--package", os.fspath(installed), "--source", os.fspath(source),
                     "--system", "aarch64-darwin")
    assert (completed.returncode, completed.stdout, completed.stderr) == (
        0, "apg_nix_distribution: installed output verified\n", "")
    marker = json.loads((runtime / nixdist.MARKER_NAME).read_text(encoding="ascii"))
    assert marker["runtime_root"] == str(runtime)
    assert marker["runtime_digest"] == nixdist.runtime_digest(runtime)
    assert (runtime / nixdist.MARKER_NAME).stat().st_mode & 0o777 == 0o444
    rewritten = [path for path in (runtime / "bin").iterdir()
                 if path.read_bytes().startswith(b"#!/nix/store/")]
    assert rewritten, "the fixture must exercise the store-shebang allowance"
    again = _cli("write-marker", "--runtime", os.fspath(runtime))
    assert (again.returncode, again.stderr) == (1, "apg_nix_distribution: runtime marker already exists\n")


def test_installed_tree_violations_are_each_reported(copy: Path, source: Path) -> None:
    runtime = copy / nixdist.RUNTIME_SUBPATH
    (runtime / "LICENSE").unlink()
    (runtime / "libexec/__pycache__").mkdir()
    (runtime / "libexec/__pycache__/stale.cpython-313.pyc").write_bytes(b"")
    (runtime / "libexec/linked.py").symlink_to(runtime / "libexec/apg_nix_smoke.py")
    (runtime / "NOTICE").write_text("changed\n")
    bundle = runtime / "bin/apgr-dispatcher-bundle"
    bundle.chmod(bundle.stat().st_mode & ~0o111)
    errors = _errors(copy, source)
    assert "missing runtime file: LICENSE" in errors
    assert "forbidden installed path: share/agentic-praxis-grimoire/runtime/libexec/__pycache__" in errors
    assert "installed path is a symlink: share/agentic-praxis-grimoire/runtime/libexec/linked.py" in errors
    assert "runtime bytes differ from source: NOTICE" in errors
    assert "runtime executable bit differs from source: bin/apgr-dispatcher-bundle" in errors
    assert "installed runtime marker cannot be recomputed" in errors


def test_generated_binary_identity_is_bound_to_version_corpus_and_system(copy: Path, source: Path) -> None:
    runtime = copy / nixdist.RUNTIME_SUBPATH
    manifest_path = runtime / nixdist.PACKAGE_BIN / nixdist.MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text())
    manifest.update(version="0.0.0", corpus_fingerprint="0" * 64, size_bytes=1)
    manifest_path.write_text(json.dumps(manifest, indent=1) + "\n")
    (runtime / nixdist.PACKAGE_BIN / nixdist.BINARY_NAME).chmod(0o755)
    (runtime / nixdist.PACKAGE_BIN / nixdist.BINARY_NAME).write_bytes(b"replaced binary")
    errors = _errors(copy, source, "x86_64-linux")
    for expected in ("binary manifest is not canonical JSON", "bundled Go binary hash differs from its manifest",
                     "bundled Go binary size differs from its manifest",
                     "binary manifest version differs from VERSION",
                     "binary manifest corpus identity differs from skill metadata",
                     "binary manifest target is not linux/amd64", "installed runtime marker is stale or malformed"):
        assert expected in errors
    manifest_path.unlink()
    assert ("missing generated runtime file: src/agentic_praxis_grimoire/bin/apgr.binary-manifest.json"
            in _errors(copy, source))


def test_command_wrappers_must_be_exact_executable_runtime_owners(copy: Path, source: Path) -> None:
    runtime = copy / nixdist.RUNTIME_SUBPATH
    (copy / "bin/apgr").chmod(0o644)
    (copy / "bin/agent-phase-resolve").write_text('#!/bin/sh\nexec agent-phase-resolve "$@"\n')
    assert _errors(copy, source) == ["installed command does not target its runtime owner: agent-phase-resolve",
                                     "installed command is not executable: apgr"]
    (copy / "bin/extra").write_text(f'#!/bin/sh\nexec "{runtime}/bin/extra"\n')
    assert "installed commands differ from distribution commands" in _errors(copy, source)


def test_source_and_marker_refusals_exit_before_verification(tmp_path: Path, copy: Path) -> None:
    source = tmp_path / "source"
    (source / "nix").mkdir(parents=True)
    shutil.copy2(ROOT / nixdist.DISTRIBUTION_PATH, source / nixdist.DISTRIBUTION_PATH)
    completed = _cli("verify-installed", "--package", os.fspath(copy), "--source", os.fspath(source))
    assert completed.returncode == 1
    assert completed.stderr.startswith("apg_nix_distribution: runtime entry is missing or not direct: ")
    runtime = copy / nixdist.RUNTIME_SUBPATH
    (runtime / nixdist.MARKER_NAME).unlink()
    (runtime / "libexec/linked.py").symlink_to(runtime / "libexec/apg_nix_smoke.py")
    marked = _cli("write-marker", "--runtime", os.fspath(runtime))
    assert (marked.returncode, marked.stderr) == (
        1, "apg_nix_distribution: installed runtime member is not a direct file: libexec/linked.py\n")
    assert not (runtime / nixdist.MARKER_NAME).exists()
