"""Static contract of the first-party Nix flake; installed behavior is proven by its checks."""
from __future__ import annotations

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[5]
NIX_FILES = [ROOT / "flake.nix", *sorted((ROOT / "nix").glob("*.nix"))]
FLAKE = (ROOT / "flake.nix").read_text()
PACKAGE = (ROOT / "nix/package.nix").read_text()
DATA = json.loads((ROOT / "nix/distribution.json").read_text())
SEMVER = re.compile(r"\b\d+\.\d+\.\d+\b")
TAGGED = re.compile(r"github:Knowledge-Forge-AI/agentic-praxis-grimoire(?P<ref>/[^#\s`\"']*)?")


def test_version_comes_only_from_the_release_version_authority() -> None:
    for path in NIX_FILES:
        assert not SEMVER.search(path.read_text()), f"version literal in {path.name}"
    assert 'lib.fileContents (src + "/src/agentic_praxis_grimoire/VERSION")' in PACKAGE
    assert "bin/apg-build-go-cli" in PACKAGE, "Go identity must come from the existing builder"


def test_systems_packages_and_apps_are_exact() -> None:
    assert "builtins.attrNames distribution.systems" in FLAKE
    assert sorted(DATA["systems"]) == ["aarch64-darwin", "aarch64-linux", "x86_64-linux"]
    for alias in ("default = package;", "agentic-praxis-grimoire = package;", "apgr = package;"):
        assert alias in FLAKE
    for app in ("default = app system \"apgr\";", "apgr = app system \"apgr\";",
                "agent-phase-dispatch = app system", "apgr-dispatcher-bundle = app system"):
        assert app in FLAKE
    assert "checks = forAllSystems" in FLAKE


def test_no_mutable_fetch_impurity_or_flake_config() -> None:
    for path in NIX_FILES:
        text = path.read_text()
        for forbidden in ("builtins.fetch", "fetchurl", "fetchGit", "fetchTarball", "nixConfig",
                          "\"path:", "builtins.getEnv", "__impure", "import-from-derivation"):
            assert forbidden not in text, f"{forbidden} in {path.name}"


def test_lock_pins_exactly_one_nixpkgs_input() -> None:
    lock = json.loads((ROOT / "flake.lock").read_text())
    assert lock["version"] == 7 and lock["nodes"]["root"]["inputs"] == {"nixpkgs": "nixpkgs"}
    assert set(lock["nodes"]) == {"root", "nixpkgs"}
    locked = lock["nodes"]["nixpkgs"]["locked"]
    assert locked["type"] == "github" and re.fullmatch(r"[0-9a-f]{40}", locked["rev"])
    assert locked["narHash"].startswith("sha256-")
    assert 'inputs.nixpkgs.url = "github:NixOS/nixpkgs/' in FLAKE


def test_package_never_synthesizes_operator_settings() -> None:
    for path in NIX_FILES:
        assert "settings.json" not in path.read_text()
    assert "settings.json" in DATA["excluded_names"]
    assert "dontStrip = true;" in PACKAGE and "dontPatchELF = true;" in PACKAGE


def test_install_documentation_is_tag_pinned() -> None:
    documents = [ROOT / "README.md", ROOT / "docs/distribution.md", ROOT / "docs/public-release-process.md"]
    found = 0
    for document in documents:
        for match in TAGGED.finditer(document.read_text()):
            found += 1
            assert match.group("ref") and re.fullmatch(r"/v\d+\.\d+\.\d+", match.group("ref")), (
                f"{document.name}: {match.group(0)} is not pinned to a release tag")
    assert found >= 3
