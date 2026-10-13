"""First-party Nix distribution data, runtime marker, and installed-output verifier.

``nix/distribution.json`` is the single data authority shared by the flake
recipe and this verifier.  The verifier compares an exact installed store
output with the filtered source it was built from; it never builds anything.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys


DISTRIBUTION_PATH = "nix/distribution.json"
DISTRIBUTION_SCHEMA = "apgr.nix-distribution/v1"
MARKER_NAME = "apgr-installed-runtime.json"
MARKER_SCHEMA = "apgr.installed-runtime/v1"
RUNTIME_SUBPATH = "share/agentic-praxis-grimoire/runtime"
PACKAGE_BIN = "src/agentic_praxis_grimoire/bin"
BINARY_NAME = "apgr"
MANIFEST_NAME = "apgr.binary-manifest.json"
VERSION_PATH = "src/agentic_praxis_grimoire/VERSION"
CORPUS_PATH = "src/agentic_praxis_grimoire/resources/skill-metadata.json"
SYSTEMS = ("aarch64-darwin", "aarch64-linux", "x86_64-linux")
DISTRIBUTION_KEYS = {
    "commands", "excluded_names", "go_excluded", "go_sources", "package", "publication",
    "runtime", "schema", "systems",
}
_SHEBANG_ENV = re.compile(rb"#!/usr/bin/env ([A-Za-z0-9_.+-]+)")
_SHEBANG_STORE = re.compile(rb"#!(/[^\s]+)/bin/([A-Za-z0-9_.+-]+)")


class DistributionError(RuntimeError):
    """The Nix distribution contract is violated."""


def _safe_relative(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or value.startswith("/"):
        raise DistributionError(f"{label} must be a relative path")
    parts = PurePosixPath(value).parts
    if value != str(PurePosixPath(value)) or any(part in {"", ".", ".."} for part in parts):
        raise DistributionError(f"{label} is not a clean relative path: {value}")
    if parts[0] == "private" or value.startswith(("src/test", "testing", "docs")):
        raise DistributionError(f"{label} names development or private material: {value}")
    return value


def load_distribution(root: Path) -> dict:
    """Load and validate the closed distribution data authority."""

    try:
        value = json.loads((root / DISTRIBUTION_PATH).read_bytes())
    except (OSError, ValueError) as error:
        raise DistributionError("distribution data is unavailable or malformed") from error
    if not isinstance(value, dict) or set(value) != DISTRIBUTION_KEYS:
        raise DistributionError("distribution data fields differ from the closed contract")
    if value["schema"] != DISTRIBUTION_SCHEMA:
        raise DistributionError("distribution data schema is unsupported")
    if not isinstance(value["systems"], dict) or tuple(sorted(value["systems"])) != SYSTEMS:
        raise DistributionError("distribution systems must be exactly " + ", ".join(SYSTEMS))
    for key in ("commands", "excluded_names", "go_excluded", "go_sources", "runtime"):
        items = value[key]
        if not isinstance(items, list) or items != sorted(set(items)) or not items:
            raise DistributionError(f"distribution {key} must be sorted, unique and non-empty")
    for key in ("go_excluded", "go_sources", "runtime"):
        for item in value[key]:
            _safe_relative(item, f"distribution {key} entry")
            if PurePosixPath(item).name in value["excluded_names"]:
                raise DistributionError(f"distribution {key} names an excluded file: {item}")
    if BINARY_NAME not in value["commands"]:
        raise DistributionError("distribution commands must include apgr")
    return value


def runtime_files(source: Path, distribution: dict) -> dict[str, Path]:
    """Return the exact runtime file set from one filtered source tree."""

    files: dict[str, Path] = {}
    for entry in distribution["runtime"]:
        path = source / entry
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise DistributionError(f"runtime entry is missing or not direct: {entry}")
        members = [path] if path.is_file() else sorted(p for p in path.rglob("*") if not p.is_dir())
        for member in members:
            relative = member.relative_to(source).as_posix()
            if member.is_symlink() or not member.is_file():
                raise DistributionError(f"runtime member is not a direct file: {relative}")
            files[relative] = member
    return files


def runtime_digest(runtime: Path) -> str:
    """Digest every installed runtime file except the marker that records it."""

    digest = hashlib.sha256()
    for path in sorted(p for p in runtime.rglob("*") if not p.is_dir()):
        relative = path.relative_to(runtime).as_posix()
        if relative == MARKER_NAME:
            continue
        if path.is_symlink() or not path.is_file():
            raise DistributionError(f"installed runtime member is not a direct file: {relative}")
        executable = "x" if path.stat().st_mode & 0o100 else "-"
        member = hashlib.sha256(path.read_bytes()).hexdigest()
        digest.update(f"{relative}\0{executable}\0{member}\n".encode("utf-8"))
    return digest.hexdigest()


def render_marker(runtime: Path) -> bytes:
    version = (runtime / VERSION_PATH).read_text(encoding="ascii").strip()
    marker = {
        "distribution": "nix",
        "runtime_digest": runtime_digest(runtime),
        "runtime_root": str(runtime),
        "schema": MARKER_SCHEMA,
        "version": version,
    }
    return (json.dumps(marker, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")


def _same_content(source: bytes, installed: bytes) -> bool:
    """Equal bytes, allowing only a Nix shebang rewrite of ``env <program>``."""

    if source == installed:
        return True
    source_first, _, source_rest = source.partition(b"\n")
    installed_first, _, installed_rest = installed.partition(b"\n")
    wanted = _SHEBANG_ENV.fullmatch(source_first)
    rewritten = _SHEBANG_STORE.fullmatch(installed_first)
    return bool(wanted and rewritten and wanted.group(1) == rewritten.group(2)
                and source_rest == installed_rest)


def _verify_binary(runtime: Path, target: str | None) -> list[str]:
    errors: list[str] = []
    binary = runtime / PACKAGE_BIN / BINARY_NAME
    try:
        manifest_raw = (runtime / PACKAGE_BIN / MANIFEST_NAME).read_bytes()
        manifest = json.loads(manifest_raw)
        content = binary.read_bytes()
        version = (runtime / VERSION_PATH).read_text(encoding="ascii").strip()
        corpus = hashlib.sha256((runtime / CORPUS_PATH).read_bytes()).hexdigest()
    except (OSError, ValueError) as error:
        return [f"bundled Go binary or manifest unreadable: {type(error).__name__}"]
    canonical = (json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
    if manifest_raw != canonical:
        errors.append("binary manifest is not canonical JSON")
    if manifest.get("sha256") != hashlib.sha256(content).hexdigest():
        errors.append("bundled Go binary hash differs from its manifest")
    if manifest.get("size_bytes") != len(content):
        errors.append("bundled Go binary size differs from its manifest")
    if manifest.get("version") != version:
        errors.append("binary manifest version differs from VERSION")
    if manifest.get("corpus_fingerprint") != corpus:
        errors.append("binary manifest corpus identity differs from skill metadata")
    if target is not None and manifest.get("build_identity", {}).get("target") != target:
        errors.append(f"binary manifest target is not {target}")
    return errors


def verify_installed(package: Path, source: Path, system: str | None = None) -> list[str]:
    """Return every contract violation of one installed package output."""

    distribution = load_distribution(source)
    runtime = package / RUNTIME_SUBPATH
    errors: list[str] = []
    expected = runtime_files(source, distribution)
    generated = {f"{PACKAGE_BIN}/{BINARY_NAME}", f"{PACKAGE_BIN}/{MANIFEST_NAME}", MARKER_NAME}
    installed: dict[str, Path] = {}
    for path in sorted(package.rglob("*")):
        relative = path.relative_to(package).as_posix()
        parts = PurePosixPath(relative).parts
        if any(part in distribution["excluded_names"] for part in parts) or relative.endswith(".pyc"):
            errors.append(f"forbidden installed path: {relative}")
        if path.is_symlink():
            errors.append(f"installed path is a symlink: {relative}")
        elif path.is_file() and relative.startswith(RUNTIME_SUBPATH + "/"):
            installed[relative[len(RUNTIME_SUBPATH) + 1:]] = path
    for name in sorted(set(expected) - set(installed)):
        errors.append(f"missing runtime file: {name}")
    for name in sorted(set(installed) - set(expected) - generated):
        errors.append(f"unexpected runtime file: {name}")
    for name in sorted(generated - set(installed)):
        errors.append(f"missing generated runtime file: {name}")
    for name in sorted(set(expected) & set(installed)):
        if not _same_content(expected[name].read_bytes(), installed[name].read_bytes()):
            errors.append(f"runtime bytes differ from source: {name}")
        if bool(expected[name].stat().st_mode & 0o100) != bool(installed[name].stat().st_mode & 0o100):
            errors.append(f"runtime executable bit differs from source: {name}")
    if generated <= set(installed):
        target = distribution["systems"].get(system) if system else None
        if system and target is None:
            errors.append(f"unsupported system: {system}")
        errors.extend(_verify_binary(runtime, target))
        try:
            if installed[MARKER_NAME].read_bytes() != render_marker(runtime):
                errors.append("installed runtime marker is stale or malformed")
        except (OSError, UnicodeError, DistributionError):
            errors.append("installed runtime marker cannot be recomputed")
    commands = sorted(p.name for p in (package / "bin").iterdir()) if (package / "bin").is_dir() else []
    if commands != distribution["commands"]:
        errors.append("installed commands differ from distribution commands")
    for name in commands:
        wrapper = package / "bin" / name
        if not os.access(wrapper, os.X_OK):
            errors.append(f"installed command is not executable: {name}")
        elif f"{runtime}/bin/{name}".encode() not in wrapper.read_bytes():
            errors.append(f"installed command does not target its runtime owner: {name}")
    return errors


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="apg_nix_distribution")
    commands = parser.add_subparsers(dest="command", required=True)
    marker = commands.add_parser("write-marker", help="write the build-owned runtime marker")
    marker.add_argument("--runtime", required=True, type=Path)
    verify = commands.add_parser("verify-installed", help="verify one installed store output")
    verify.add_argument("--package", required=True, type=Path)
    verify.add_argument("--source", required=True, type=Path)
    verify.add_argument("--system", choices=SYSTEMS)
    parsed = parser.parse_args(arguments)
    try:
        if parsed.command == "write-marker":
            runtime = parsed.runtime.resolve(strict=True)
            destination = runtime / MARKER_NAME
            if os.path.lexists(destination):
                raise DistributionError("runtime marker already exists")
            destination.write_bytes(render_marker(runtime))
            destination.chmod(0o444)
            return 0
        errors = verify_installed(parsed.package.resolve(strict=True), parsed.source.resolve(strict=True),
                                  parsed.system)
    except (OSError, DistributionError) as error:
        print(f"apg_nix_distribution: {error}", file=sys.stderr)
        return 1
    for error in errors:
        print(f"apg_nix_distribution: {error}", file=sys.stderr)
    if not errors:
        print("apg_nix_distribution: installed output verified")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
