from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[6]
if str(ROOT / "libexec") not in sys.path:
    sys.path.insert(0, str(ROOT / "libexec"))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"libexec/{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, module)
    spec.loader.exec_module(module)
    return module


nixdist = _load("apg_nix_distribution")
gobuild = _load("apg_go_build")
store = _load("controller_generation_store")


def tracked(*paths: str) -> list[str]:
    output = subprocess.check_output(["git", "-C", str(ROOT), "ls-files", "-z", "--", *paths], text=True)
    return [name for name in output.split("\0") if name]


DATA = nixdist.load_distribution(ROOT)


def test_systems_are_exactly_the_supported_three_and_map_to_go_targets() -> None:
    assert sorted(DATA["systems"]) == ["aarch64-darwin", "aarch64-linux", "x86_64-linux"]
    assert "x86_64-darwin" not in DATA["systems"]
    assert set(DATA["systems"].values()) == set(gobuild.TARGETS)


def test_every_declared_path_is_tracked_and_public() -> None:
    public = _load("apg_public_release")
    for entry in [*DATA["runtime"], *DATA["go_sources"], *DATA["go_excluded"],
                  *DATA["publication"]["critical_files"]]:
        names = tracked(entry) or ([entry] if (ROOT / entry).is_file() else [])
        assert names, f"{entry} is not present"
        assert all(public.is_v012_candidate_path(name) for name in names), entry


def test_runtime_covers_every_tracked_controller_generation_owner() -> None:
    for entry in store.ALLOWLIST:
        for name in tracked(entry.rstrip("/")):
            assert any(name == root or name.startswith(root + "/") for root in DATA["runtime"]), name


def test_go_sources_are_exactly_the_build_owners() -> None:
    owners = {name.split("/", 1)[0] for name in tracked("*.go")
              if not name.endswith("_test.go") and not name.startswith(("private/", "testing/"))}
    assert set(DATA["go_sources"]) == owners | {"go.mod"}
    testdata = {name[: name.index("/testdata/") + len("/testdata")] for name in tracked()
                if "/testdata/" in name and name.split("/", 1)[0] in owners}
    assert set(DATA["go_excluded"]) == testdata


def test_runtime_excludes_development_private_and_operator_material() -> None:
    names = tracked(*DATA["runtime"])
    assert not [name for name in names if name.startswith(("private/", "src/test/", "testing/", "docs/"))]
    assert not [name for name in names if Path(name).name in DATA["excluded_names"]]
    assert "claude/settings.json" not in DATA["runtime"]
    assert not [entry for entry in DATA["runtime"] if entry in {"claude", "claude/"}]


def test_publication_owners_and_commands_are_declared() -> None:
    assert DATA["publication"]["first_version"] == "0.13.0"
    assert DATA["publication"]["flake_ref"] == "github:Knowledge-Forge-AI/agentic-praxis-grimoire"
    assert {"flake.nix", "flake.lock", "nix/package.nix", "nix/distribution.json"} <= set(
        DATA["publication"]["critical_files"])
    assert {"apgr", "agent-phase-dispatch", "apgr-dispatcher-bundle"} <= set(DATA["commands"])
    assert all((ROOT / "bin" / command).is_file() for command in DATA["commands"])


def _write_data(root: Path, **changes: object) -> None:
    value = json.loads((ROOT / nixdist.DISTRIBUTION_PATH).read_text())
    value.update(changes)
    (root / "nix").mkdir(parents=True, exist_ok=True)
    (root / nixdist.DISTRIBUTION_PATH).write_text(json.dumps(value))


@pytest.mark.parametrize("changes, message", [
    ({"schema": "other"}, "schema"),
    ({"systems": {"aarch64-darwin": "darwin/arm64", "x86_64-darwin": "darwin/amd64",
                  "x86_64-linux": "linux/amd64"}}, "exactly"),
    ({"runtime": ["libexec", "bin"]}, "sorted"),
    ({"runtime": ["private/evidence"]}, "private"),
    ({"runtime": ["../outside"]}, "clean relative"),
    ({"go_sources": ["src/test/fixtures"]}, "development"),
    ({"runtime": ["claude/settings.json"]}, "excluded"),
    ({"commands": ["agent-phase-dispatch"]}, "apgr"),
    ({"unexpected": True}, "closed contract"),
])
def test_distribution_contract_rejects_violations(tmp_path: Path, changes: dict, message: str) -> None:
    _write_data(tmp_path, **changes)
    with pytest.raises(nixdist.DistributionError, match=message):
        nixdist.load_distribution(tmp_path)
    with pytest.raises(nixdist.DistributionError, match="unavailable"):
        nixdist.load_distribution(tmp_path / "missing")


def fake_install(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "source"
    _write_data(source, runtime=["LICENSE", "bin", "src/agentic_praxis_grimoire"], commands=["apgr"])
    package = source / "src/agentic_praxis_grimoire"
    (package / "resources").mkdir(parents=True)
    (package / "VERSION").write_text("1.2.3\n")
    (package / "resources/skill-metadata.json").write_text('{"skills":[]}\n')
    (source / "bin").mkdir()
    (source / "bin/apgr").write_text("#!/usr/bin/env python3\nprint('apgr')\n")
    (source / "bin/apgr").chmod(0o755)
    (source / "LICENSE").write_text("license\n")
    output = tmp_path / "out"
    runtime = output / nixdist.RUNTIME_SUBPATH
    for name in ("LICENSE", "bin", "src"):
        target = runtime / name
        target.parent.mkdir(parents=True, exist_ok=True)
        (shutil.copytree if (source / name).is_dir() else shutil.copy2)(source / name, target)
    (runtime / "bin/apgr").write_text("#!/nix/store/abc-python3-3.13/bin/python3\nprint('apgr')\n")
    binary = b"\x7fELF fake apgr"
    (runtime / nixdist.PACKAGE_BIN).mkdir(parents=True)
    (runtime / nixdist.PACKAGE_BIN / "apgr").write_bytes(binary)
    corpus = hashlib.sha256(b'{"skills":[]}\n').hexdigest()
    manifest = {"build_identity": {"target": "darwin/arm64"}, "corpus_fingerprint": corpus,
                "sha256": hashlib.sha256(binary).hexdigest(), "size_bytes": len(binary), "version": "1.2.3"}
    (runtime / nixdist.PACKAGE_BIN / nixdist.MANIFEST_NAME).write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n")
    (output / "bin").mkdir()
    (output / "bin/apgr").write_text(f'#!/bin/sh\nexec "{runtime}/bin/apgr" "$@"\n')
    (output / "bin/apgr").chmod(0o755)
    (runtime / nixdist.MARKER_NAME).write_bytes(nixdist.render_marker(runtime))
    return output, source


def test_verified_install_passes_and_marker_is_deterministic(tmp_path: Path) -> None:
    output, source = fake_install(tmp_path)
    assert nixdist.verify_installed(output, source, "aarch64-darwin") == []
    runtime = output / nixdist.RUNTIME_SUBPATH
    assert nixdist.render_marker(runtime) == (runtime / nixdist.MARKER_NAME).read_bytes()
    marker = json.loads((runtime / nixdist.MARKER_NAME).read_text())
    assert marker == {"distribution": "nix", "runtime_digest": nixdist.runtime_digest(runtime),
                      "runtime_root": str(runtime), "schema": nixdist.MARKER_SCHEMA, "version": "1.2.3"}


def _tamper_missing(runtime: Path, output: Path) -> None:
    (runtime / "LICENSE").unlink()


def _tamper_extra(runtime: Path, output: Path) -> None:
    (runtime / "bin/extra").write_text("x")


def _tamper_bytes(runtime: Path, output: Path) -> None:
    (runtime / "LICENSE").write_text("changed\n")


def _tamper_shebang(runtime: Path, output: Path) -> None:
    (runtime / "bin/apgr").write_text("#!/nix/store/abc-bash/bin/bash\nprint('apgr')\n")


def _tamper_manifest_hash(runtime: Path, output: Path) -> None:
    (runtime / nixdist.PACKAGE_BIN / "apgr").write_bytes(b"other binary!!")


def _tamper_version(runtime: Path, output: Path) -> None:
    (runtime / "src/agentic_praxis_grimoire/VERSION").write_text("9.9.9\n")


def _tamper_settings(runtime: Path, output: Path) -> None:
    (runtime / "settings.json").write_text("{}")


def _tamper_pyc(runtime: Path, output: Path) -> None:
    (runtime / "bin/__pycache__").mkdir()
    (runtime / "bin/__pycache__/x.cpython-313.pyc").write_bytes(b"")


def _tamper_wrapper(runtime: Path, output: Path) -> None:
    (output / "bin/apgr").write_text("#!/bin/sh\nexec apgr \"$@\"\n")


def _tamper_mode(runtime: Path, output: Path) -> None:
    (runtime / "bin/apgr").chmod(0o644)


@pytest.mark.parametrize("tamper, message", [
    (_tamper_missing, "missing runtime file: LICENSE"),
    (_tamper_extra, "unexpected runtime file: bin/extra"),
    (_tamper_bytes, "runtime bytes differ from source: LICENSE"),
    (_tamper_shebang, "runtime bytes differ from source: bin/apgr"),
    (_tamper_manifest_hash, "hash differs"),
    (_tamper_version, "version differs"),
    (_tamper_settings, "forbidden installed path: share/agentic-praxis-grimoire/runtime/settings.json"),
    (_tamper_pyc, "forbidden installed path"),
    (_tamper_wrapper, "does not target its runtime owner"),
    (_tamper_mode, "executable bit differs"),
])
def test_verifier_fails_closed_on_tampering(tmp_path: Path, tamper, message: str) -> None:
    output, source = fake_install(tmp_path)
    tamper(output / nixdist.RUNTIME_SUBPATH, output)
    errors = nixdist.verify_installed(output, source, "aarch64-darwin")
    assert any(message in error for error in errors), errors


def test_verifier_rejects_wrong_target_and_stale_marker(tmp_path: Path) -> None:
    output, source = fake_install(tmp_path)
    assert any("target is not linux/amd64" in e for e in nixdist.verify_installed(output, source, "x86_64-linux"))
    (output / nixdist.RUNTIME_SUBPATH / nixdist.MARKER_NAME).write_text("{}\n")
    assert any("marker is stale" in e for e in nixdist.verify_installed(output, source, None))


def test_cli_writes_marker_once_and_reports_verification(tmp_path: Path, capsys) -> None:
    output, source = fake_install(tmp_path)
    runtime = output / nixdist.RUNTIME_SUBPATH
    assert nixdist.main(["write-marker", "--runtime", str(runtime)]) == 1
    assert "already exists" in capsys.readouterr().err
    (runtime / nixdist.MARKER_NAME).unlink()
    assert nixdist.main(["write-marker", "--runtime", str(runtime)]) == 0
    assert nixdist.main(["verify-installed", "--package", str(output), "--source", str(source),
                         "--system", "aarch64-darwin"]) == 0
    assert "verified" in capsys.readouterr().out
    (runtime / "LICENSE").unlink()
    assert nixdist.main(["verify-installed", "--package", str(output), "--source", str(source)]) == 1
    assert "missing runtime file" in capsys.readouterr().err


def _release_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("+")[0].split("-")[0].split("."))


NIX_HELPERS = {"bin/apg-qualify-nix", "libexec/apg_nix_distribution.py", "libexec/apg_nix_qualification.py",
               "libexec/apg_nix_smoke.py"}


def test_release_policy_binds_nix_owners_without_rewriting_history() -> None:
    public = _load("apg_public_release")
    critical = set(DATA["publication"]["critical_files"])
    for version in ("0.6.0", "0.7.0", "0.8.0", "0.8.1", "0.9.0", "0.10.0", "0.11.0", "0.12.0"):
        for surface in public.audited_policy_surfaces(version):
            owned = {item for values in surface.values() for item in values}
            assert not (critical | NIX_HELPERS) & owned, version
    first = DATA["publication"]["first_version"]
    version = (ROOT / "src/agentic_praxis_grimoire/VERSION").read_text().strip()
    try:
        current = public.audited_policy_surfaces(first)
    except public.ToolError:
        # V0130-I adds the v0.13.0 surface; release preparation cannot bump
        # VERSION to a Nix-published release before that surface exists.
        assert _release_tuple(version) < _release_tuple(first), version
        current = ()
    for surface in current:
        assert critical <= set(surface["critical_files"])
        assert NIX_HELPERS <= set(surface["required_helpers"]) | set(surface["required_wrappers"])
