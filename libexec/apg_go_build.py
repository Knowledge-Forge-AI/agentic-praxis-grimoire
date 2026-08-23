"""Deterministic release-like APGR Go CLI builder."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Mapping


MANIFEST_SCHEMA = "apg.binary-manifest/v1"
BUILD_INFO_SCHEMA = "apg.build-info/v1"
MODULE = "github.com/Knowledge-Forge-AI/agentic-praxis-grimoire"
BINARY_NAME = "apgr"
BUILD_FLAGS = ("CGO_ENABLED=0", "-trimpath", "-buildvcs=false", "-buildid=")

# These are distribution identities, not version authorities.  The editable
# version remains the VERSION resource read by ``identities`` below.
TARGETS = {
    "darwin/arm64": {
        "go_target": "darwin/arm64",
        "goos": "darwin",
        "goarch": "arm64",
        "python_platform": "macosx_11_0_arm64",
        "npm_package": "@knowledge-forge-ai/apgr-darwin-arm64",
        "npm_os": "darwin",
        "npm_cpu": "arm64",
    },
    "linux/amd64": {
        "go_target": "linux/amd64",
        "goos": "linux",
        "goarch": "amd64",
        "python_platform": "manylinux_2_17_x86_64",
        "npm_package": "@knowledge-forge-ai/apgr-linux-x64",
        "npm_os": "linux",
        "npm_cpu": "x64",
    },
    "linux/arm64": {
        "go_target": "linux/arm64",
        "goos": "linux",
        "goarch": "arm64",
        "python_platform": "manylinux_2_17_aarch64",
        "npm_package": "@knowledge-forge-ai/apgr-linux-arm64",
        "npm_os": "linux",
        "npm_cpu": "arm64",
    },
}
SUPPORTED_TARGETS = tuple(TARGETS)


class BuildError(RuntimeError):
    """A release-like Go CLI build cannot be performed safely."""


def _read_direct(path: Path, label: str) -> bytes:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise BuildError(f"{label} is unavailable") from error
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise BuildError(f"{label} is not a direct regular file")
    try:
        return path.read_bytes()
    except OSError as error:
        raise BuildError(f"{label} cannot be read") from error


def _absolute_clean(path: Path, label: str) -> Path:
    if not path.is_absolute() or path != Path(os.path.normpath(path)):
        raise BuildError(f"{label} must be an absolute clean path")
    return path


def _ensure_direct_directory(path: Path, label: str) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise BuildError(f"{label} is unavailable") from error
    cursor = resolved
    while True:
        try:
            metadata = cursor.lstat()
        except OSError as error:
            raise BuildError(f"{label} is unavailable") from error
        if cursor.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
            raise BuildError(f"{label} is not a direct directory")
        parent = cursor.parent
        if parent == cursor:
            break
        cursor = parent


def _prepare_output(path: Path, label: str) -> Path:
    path = _absolute_clean(path, label)
    _ensure_direct_directory(path.parent, f"{label} parent")
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return path
    except OSError as error:
        raise BuildError(f"{label} cannot be inspected") from error
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise BuildError(f"{label} is not a direct regular file")
    raise BuildError(f"{label} already exists")


def target_mapping(target: str) -> dict[str, str]:
    """Return the immutable distribution mapping for one supported target."""

    try:
        return dict(TARGETS[target])
    except KeyError as error:
        raise BuildError(f"unsupported target: {target}") from error


def identities(root: Path) -> tuple[str, str]:
    """Return the single Python version and current metadata-corpus identity."""

    version_raw = _read_direct(
        root / "src" / "agentic_praxis_grimoire" / "VERSION",
        "version authority",
    )
    try:
        version = version_raw.decode("ascii").strip()
    except UnicodeDecodeError as error:
        raise BuildError("version authority is not ASCII") from error
    if not version or any(character.isspace() for character in version):
        raise BuildError("version authority is malformed")
    corpus = _read_direct(
        root
        / "src"
        / "agentic_praxis_grimoire"
        / "resources"
        / "skill-metadata.json",
        "corpus identity authority",
    )
    return version, hashlib.sha256(corpus).hexdigest()


def _host_target() -> str:
    goos = {"Darwin": "darwin", "Linux": "linux"}.get(platform.system(), "")
    goarch = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "amd64"}.get(
        platform.machine(), ""
    )
    return f"{goos}/{goarch}" if goos and goarch else ""


def _manifest(
    *,
    target: str,
    version: str,
    corpus: str,
    binary: bytes,
) -> dict[str, object]:
    """Construct a path-free manifest from one completed binary."""

    return {
        "binary_name": BINARY_NAME,
        "build_flags": list(BUILD_FLAGS),
        "build_identity": {
            "corpus_fingerprint": corpus,
            "schema_version": BUILD_INFO_SCHEMA,
            "target": target,
            "version": version,
        },
        "build_info_schema": BUILD_INFO_SCHEMA,
        "corpus_fingerprint": corpus,
        "module_path": MODULE,
        "schema_version": MANIFEST_SCHEMA,
        "sha256": hashlib.sha256(binary).hexdigest(),
        "size_bytes": len(binary),
        "target": target_mapping(target),
        "version": version,
    }


def render_manifest(manifest: Mapping[str, object]) -> bytes:
    """Render one canonical compact manifest with a single trailing newline."""

    return (
        json.dumps(
            dict(manifest), ensure_ascii=True, sort_keys=True, separators=(",", ":")
        )
        + "\n"
    ).encode("ascii")


def write_manifest(path: Path, manifest: Mapping[str, object]) -> None:
    """Atomically write one new direct manifest without overwriting an asset."""

    destination = _prepare_output(path, "manifest output")
    content = render_manifest(manifest)
    descriptor = -1
    temporary: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.", dir=destination.parent
        )
        temporary = Path(temporary_name)
        os.fchmod(descriptor, 0o644)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        # The temporary file lives beside the destination, so a hard link is
        # an atomic create that fails with EEXIST instead of overwriting an
        # asset that appeared after the preflight check.
        os.link(temporary, destination, follow_symlinks=False)
        temporary.unlink()
        temporary = None
    except OSError as error:
        raise BuildError("manifest cannot be written safely") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def _validate_binary_metadata(
    *, root: Path, target: str, output: Path, manifest: Mapping[str, object], go: Path
) -> None:
    """Validate host runtime metadata or foreign Go object metadata."""

    if target == _host_target():
        completed = subprocess.run(
            [os.fspath(output), "build-info"],
            cwd=root,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )
        if completed.returncode != 0:
            raise BuildError("host binary build-info validation failed")
        try:
            info = json.loads(completed.stdout.decode("utf-8"))
        except (AttributeError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise BuildError("host binary build-info is malformed") from error
        expected = {
            "version": manifest["version"],
            "module_path": manifest["module_path"],
            "target": target,
            "corpus_fingerprint": manifest["corpus_fingerprint"],
            "embedded_corpus_fingerprint": manifest["corpus_fingerprint"],
            "corpus_fingerprint_verified": True,
            "schema_version": BUILD_INFO_SCHEMA,
        }
        if any(info.get(key) != value for key, value in expected.items()):
            raise BuildError("host binary build-info disagrees with manifest")
        return

    completed = subprocess.run(
        [os.fspath(go), "version", "-m", os.fspath(output)],
        cwd=root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
    )
    if completed.returncode != 0:
        raise BuildError("foreign binary metadata inspection failed")
    try:
        metadata = completed.stdout.decode("utf-8")
    except (AttributeError, UnicodeDecodeError) as error:
        raise BuildError("foreign binary metadata is malformed") from error
    goos, goarch = target.split("/", 1)
    normalized_metadata = {" ".join(line.strip().split()) for line in metadata.splitlines()}
    required = {
        "build CGO_ENABLED=0",
        f"build GOOS={goos}",
        f"build GOARCH={goarch}",
        "build -trimpath=true",
    }
    module_present = any(line.startswith(f"mod {MODULE} ") for line in normalized_metadata)
    if not module_present or any(item not in normalized_metadata for item in required):
        raise BuildError("foreign binary metadata disagrees with manifest")


def build(
    root: Path,
    target: str,
    output: Path,
    manifest_output: Path | None = None,
) -> dict[str, object]:
    """Build one static target, validate it, and write its canonical manifest."""

    target_mapping(target)
    output = _prepare_output(output, "binary output")
    if manifest_output is None:
        manifest_output = output.with_name(f"{output.name}.binary-manifest.json")
    manifest_output = _absolute_clean(manifest_output, "manifest output")
    if manifest_output == output:
        raise BuildError("manifest output must differ from binary output")
    version, corpus = identities(root)
    go_value = shutil.which("go")
    if go_value is None:
        raise BuildError("Go toolchain is unavailable")
    go = Path(go_value).resolve(strict=True)
    metadata = go.lstat()
    if go.is_symlink() or not stat.S_ISREG(metadata.st_mode) or not os.access(go, os.X_OK):
        raise BuildError("Go toolchain is not a direct executable")
    goos, goarch = target.split("/", 1)
    ldflags = " ".join(
        (
            "-buildid=",
            f"-X={MODULE}/internal/buildinfo.Version={version}",
            f"-X={MODULE}/internal/buildinfo.CorpusFingerprint={corpus}",
        )
    )
    environment = dict(os.environ)
    environment.update(
        {
            "CGO_ENABLED": "0",
            "GOARCH": goarch,
            "GOFLAGS": "",
            "GOOS": goos,
            "GOTOOLCHAIN": "local",
        }
    )
    if goarch == "amd64":
        environment["GOAMD64"] = "v1"
    elif goarch == "arm64":
        environment["GOARM64"] = "v8.0"
    completed = subprocess.run(
        [
            os.fspath(go),
            "build",
            "-trimpath",
            "-buildvcs=false",
            "-ldflags",
            ldflags,
            "-o",
            os.fspath(output),
            "./cmd/apgr",
        ],
        cwd=root,
        env=environment,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
    )
    if completed.returncode != 0:
        raise BuildError("Go CLI build failed")
    binary = _read_direct(output, "built Go binary")
    output.chmod(0o700)
    manifest = _manifest(
        target=target,
        version=version,
        corpus=corpus,
        binary=binary,
    )
    try:
        _validate_binary_metadata(
            root=root, target=target, output=output, manifest=manifest, go=go
        )
        write_manifest(manifest_output, manifest)
    except BuildError:
        try:
            output.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass
        raise
    return {
        "binary_name": BINARY_NAME,
        "corpus_fingerprint": corpus,
        "manifest": manifest,
        "manifest_path": os.fspath(manifest_output),
        "module_path": MODULE,
        "path": os.fspath(output),
        "sha256": hashlib.sha256(binary).hexdigest(),
        "size_bytes": len(binary),
        "target": target,
        "version": version,
    }


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="apg-build-go-cli")
    parser.add_argument("--target", required=True, choices=SUPPORTED_TARGETS)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", type=Path)
    parsed = parser.parse_args(arguments)
    root = Path(__file__).resolve().parent.parent
    try:
        result = build(root, parsed.target, parsed.output, parsed.manifest)
    except BuildError as error:
        print(f"apg-build-go-cli: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
