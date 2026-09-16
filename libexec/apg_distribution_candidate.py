"""Build and validate a path-free APGR distribution candidate manifest.

This small facade keeps the original helper API stable while delegating
contract and archive details to bounded publication-visible modules.  It
consumes already-built artifacts only: no compiler, package manager, network
client, or publication command is invoked.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import stat
import subprocess
import sys
from typing import Any, Mapping, Sequence

import apg_distribution_candidate_archives as _archives
import apg_distribution_candidate_contract as _contract


# Re-export the old module's constants and private compatibility helpers.  A
# few repository tests intentionally inspect these names to build malformed
# fixtures; keeping them here avoids making the decomposition an API break.
for _module in (_contract, _archives):
    globals().update(
        {
            _name: getattr(_module, _name)
            for _name in dir(_module)
            if not _name.startswith("__")
        }
    )


# Keep the compatibility re-export loop above observable while giving static
# analyzers explicit bindings for the facade's implementation dependencies.
DistributionCandidateError = _contract.DistributionCandidateError
MANIFEST_SCHEMA = _contract.MANIFEST_SCHEMA
MODULE = _contract.MODULE
BINARY_MANIFEST_SCHEMA = _contract.BINARY_MANIFEST_SCHEMA
BUILD_INFO_SCHEMA = _contract.BUILD_INFO_SCHEMA
CHECKSUM_NAME = _contract.CHECKSUM_NAME
MANIFEST_NAME = _contract.MANIFEST_NAME
PYTHON_PACKAGE = _contract.PYTHON_PACKAGE
TARGETS = _contract.TARGETS
TARGET_BY_GO = _contract.TARGET_BY_GO
_absolute_clean = _contract._absolute_clean
_canonical_value = _contract._canonical_value
_directory = _contract._directory
_fail = _contract._fail
_load_go_artifacts = _contract._load_go_artifacts
_read_direct = _contract._read_direct
_sha256_file = _contract._sha256_file
_source_identity = _contract._source_identity
canonical_json = _contract.canonical_json
source_candidate_identity = _contract.source_candidate_identity
_find_npm_files = _archives._find_npm_files
_find_python_files = _archives._find_python_files
_validate_npm_package = _archives._validate_npm_package
_validate_sdist = _archives._validate_sdist
_validate_wheel = _archives._validate_wheel


def _source_revision_identity(source_root: Path | str, version: str) -> dict[str, str]:
    """Bind v0.11 distribution metadata to a source Git revision.

    Historical manifests intentionally retain their existing schema and do not
    gain a revision claim.  The public v0.11 publisher, however, must be able
    to compare the exact source used for artifacts with the observed post-merge
    commit and tree.  A non-Git source cannot provide that contract.
    """

    core = version.split("+", 1)[0].split("-", 1)[0]
    if core != "0.11.0":
        return {}
    root = _directory(source_root, "source root")
    git_prefix = ["git", "-C", os.fspath(root)]

    def status() -> str:
        result = subprocess.run(
            [*git_prefix, "status", "--porcelain=v1", "--untracked-files=all"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            _fail("v0.11 source revision identity requires a Git checkout")
        return result.stdout

    def identity() -> tuple[str, str]:
        # One commit-object read supplies HEAD and HEAD^{tree} together.  A
        # second read below detects a moving ref or tree during capture.
        result = subprocess.run(
            [*git_prefix, "show", "-s", "--format=%H%x00%T", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            _fail("v0.11 source revision identity requires a Git checkout")
        values = result.stdout.rstrip("\n").split("\x00")
        if len(values) != 2 or any(
            len(value) != 40
            or any(character not in "0123456789abcdef" for character in value)
            for value in values
        ):
            _fail("v0.11 source Git revision identity is malformed")
        return values[0], values[1]

    try:
        before = status()
        first = identity()
        between = status()
        second = identity()
        after = status()
    except OSError as error:
        raise DistributionCandidateError(
            "v0.11 source revision identity requires Git"
        ) from error
    if before or between or after:
        _fail("v0.11 source revision identity requires a clean Git checkout")
    if first != second:
        _fail("v0.11 source Git revision changed during identity capture")
    return {"source_commit": first[0], "source_tree": first[1]}


def _load_all(
    source_root: Path | str,
    go_artifacts: Path | str,
    python_artifacts: Path | str,
    npm_artifacts: Path | str,
) -> tuple[dict[str, Any], dict[str, Path]]:
    root = _directory(source_root, "source root")
    version, corpus = _source_identity(root)
    binaries, paths = _load_go_artifacts(go_artifacts, version=version, corpus=corpus)
    wheel_paths, sdist_path = _find_python_files(
        _directory(python_artifacts, "Python artifact root"), version=version
    )
    wheels = [
        _validate_wheel(
            wheel_paths[target],
            target=target,
            version=version,
            corpus=corpus,
            binary=binaries[target],
        )
        for target in TARGET_BY_GO
    ]
    sdist = _validate_sdist(sdist_path, version=version)
    paths.update({f"python/{record['name']}": wheel_paths[record["target"]] for record in wheels})
    paths[f"python/{sdist['name']}"] = sdist_path
    npm_paths = _find_npm_files(
        _directory(npm_artifacts, "npm artifact root"), version=version
    )
    launcher = _validate_npm_package(
        npm_paths["@knowledge-forge-ai/apgr"],
        version=version,
        corpus=corpus,
        binaries=binaries,
    )
    platforms = [
        _validate_npm_package(
            npm_paths[mapping["npm_package"]],
            version=version,
            corpus=corpus,
            binaries=binaries,
        )
        for mapping in TARGETS
    ]
    for record, mapping in zip(platforms, TARGETS):
        paths[f"npm/{record['filename']}"] = npm_paths[mapping["npm_package"]]
    paths[f"npm/{launcher['filename']}"] = npm_paths["@knowledge-forge-ai/apgr"]
    manifest = {
        "schema_version": MANIFEST_SCHEMA,
        "version": version,
        "source_candidate_identity": source_candidate_identity(
            version,
            corpus,
            sdist_sha256=sdist["sha256"],
            npm_launcher_sha256=launcher["sha256"],
        ),
        "corpus_fingerprint": corpus,
        "module_path": MODULE,
        "binary_manifest_schema": BINARY_MANIFEST_SCHEMA,
        "build_info_schema": BUILD_INFO_SCHEMA,
        "checksum_file": CHECKSUM_NAME,
        "target_matrix": [dict(mapping) for mapping in TARGETS],
        "binaries": binaries,
        "python": {"package": PYTHON_PACKAGE, "wheels": wheels, "sdist": sdist},
        "npm": {"launcher": launcher, "platform_packages": platforms},
    }
    manifest.update(_source_revision_identity(root, version))
    return manifest, paths


def _checksum_rows(
    manifest_path: Path, manifest: Mapping[str, Any], paths: Mapping[str, Path]
) -> bytes:
    rows: dict[str, str] = {}
    for logical, path in paths.items():
        rows[logical] = _sha256_file(path, logical)
    rows[manifest_path.name] = _sha256_file(manifest_path, manifest_path.name)
    return "".join(
        f"{digest}  {name}\n" for name, digest in sorted(rows.items())
    ).encode("ascii")


def _output_paths(output: Path | str) -> tuple[Path, Path]:
    selected = _absolute_clean(output, "candidate output")
    output_is_file = selected.name.endswith(".json")
    if output_is_file:
        manifest_path = selected
        output_root = selected.parent
    else:
        output_root = selected
        manifest_path = output_root / MANIFEST_NAME
    if output_root.exists() or output_root.is_symlink():
        try:
            parent = output_root.resolve(strict=True)
            metadata = output_root.lstat()
        except OSError as error:
            raise DistributionCandidateError("candidate output is unavailable") from error
        if (
            output_root.is_symlink()
            or metadata is None
            or not stat.S_ISDIR(metadata.st_mode)
            or parent != output_root.absolute()
        ):
            _fail("candidate output must be one direct real directory")
        if not output_is_file and any(output_root.iterdir()):
            _fail("candidate output must be empty")
    else:
        try:
            parent = output_root.parent.resolve(strict=True)
            parent_metadata = output_root.parent.lstat()
            if (
                output_root.parent.is_symlink()
                or not stat.S_ISDIR(parent_metadata.st_mode)
                or parent != output_root.parent.absolute()
            ):
                _fail("candidate output parent must be one direct real directory")
            output_root.mkdir(mode=0o700)
        except OSError as error:
            raise DistributionCandidateError("candidate output cannot be created") from error
    return manifest_path, output_root / CHECKSUM_NAME


def _write_exclusive(path: Path, data: bytes, label: str) -> None:
    if path.exists() or path.is_symlink():
        _fail(f"refusing to overwrite {label}")
    try:
        with path.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        path.chmod(0o644)
    except OSError as error:
        raise DistributionCandidateError(f"{label} cannot be written safely") from error


def build_candidate(
    source_root: Path | str,
    go_artifacts: Path | str,
    python_artifacts: Path | str,
    npm_artifacts: Path | str,
    output: Path | str,
) -> dict[str, Any]:
    """Validate prebuilt artifacts and write one candidate manifest/checksum set."""

    manifest, paths = _load_all(source_root, go_artifacts, python_artifacts, npm_artifacts)
    manifest_path, checksum_path = _output_paths(output)
    _write_exclusive(manifest_path, canonical_json(manifest), "distribution manifest")
    _write_exclusive(checksum_path, _checksum_rows(manifest_path, manifest, paths), CHECKSUM_NAME)
    validate_candidate(manifest_path, source_root, go_artifacts, python_artifacts, npm_artifacts)
    return manifest


def build_manifest(
    source_root: Path | str,
    go_artifacts: Path | str,
    python_artifacts: Path | str,
    npm_artifacts: Path | str,
    output: Path | str,
) -> dict[str, Any]:
    """Compatibility alias for :func:`build_candidate`."""

    return build_candidate(source_root, go_artifacts, python_artifacts, npm_artifacts, output)


def build(
    source_root: Path | str,
    go_artifacts: Path | str,
    python_artifacts: Path | str,
    npm_artifacts: Path | str,
    output: Path | str,
) -> dict[str, Any]:
    """Short compatibility alias for :func:`build_candidate`."""

    return build_manifest(source_root, go_artifacts, python_artifacts, npm_artifacts, output)


def validate_candidate(
    manifest_path: Path | str,
    source_root: Path | str,
    go_artifacts: Path | str,
    python_artifacts: Path | str,
    npm_artifacts: Path | str,
) -> dict[str, Any]:
    """Reconstruct and validate a candidate against explicit artifacts."""

    path = _absolute_clean(manifest_path, "distribution manifest")
    observed = _canonical_value(_read_direct(path, "distribution manifest"), "distribution manifest")
    expected, paths = _load_all(source_root, go_artifacts, python_artifacts, npm_artifacts)
    if observed != expected:
        _fail("distribution manifest does not match the explicit artifact set")
    checksum_path = path.parent / CHECKSUM_NAME
    if _read_direct(checksum_path, CHECKSUM_NAME) != _checksum_rows(path, expected, paths):
        _fail("SHA256SUMS does not match the explicit artifact set")
    return observed


def validate_manifest(
    manifest_path: Path | str,
    source_root: Path | str,
    go_artifacts: Path | str,
    python_artifacts: Path | str,
    npm_artifacts: Path | str,
) -> dict[str, Any]:
    """Compatibility alias for :func:`validate_candidate`."""

    return validate_candidate(manifest_path, source_root, go_artifacts, python_artifacts, npm_artifacts)


def check(
    manifest_path: Path | str,
    source_root: Path | str,
    go_artifacts: Path | str,
    python_artifacts: Path | str,
    npm_artifacts: Path | str,
) -> dict[str, Any]:
    """Short compatibility alias for :func:`validate_candidate`."""

    return validate_manifest(manifest_path, source_root, go_artifacts, python_artifacts, npm_artifacts)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="apg-build-distribution-candidate")
    commands = parser.add_subparsers(dest="command", required=True)
    build_parser = commands.add_parser("build", help="validate artifacts and write manifest/checksums")
    check_parser = commands.add_parser("check", help="validate an existing manifest/checksum set")
    for command in (build_parser, check_parser):
        command.add_argument("--source-root", "--source", dest="source_root", required=True, type=Path)
        command.add_argument(
            "--go-artifacts",
            "--go-artifact-root",
            "--binary-artifacts",
            dest="go_artifacts",
            required=True,
            type=Path,
        )
        command.add_argument(
            "--python-artifacts",
            "--python-artifact-root",
            "--python-distributions",
            dest="python_artifacts",
            required=True,
            type=Path,
        )
        command.add_argument(
            "--npm-artifacts",
            "--npm-artifact-root",
            "--npm-distributions",
            dest="npm_artifacts",
            required=True,
            type=Path,
        )
    build_parser.add_argument("--output", required=True, type=Path, help="empty directory or manifest JSON path")
    check_parser.add_argument("--manifest", "--output", dest="manifest", required=True, type=Path)
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(arguments)
    try:
        if args.command == "build":
            result = build_candidate(
                args.source_root,
                args.go_artifacts,
                args.python_artifacts,
                args.npm_artifacts,
                args.output,
            )
        else:
            result = validate_candidate(
                args.manifest,
                args.source_root,
                args.go_artifacts,
                args.python_artifacts,
                args.npm_artifacts,
            )
    except DistributionCandidateError as error:
        print(f"apg-build-distribution-candidate: {error}", file=sys.stderr)
        return 1
    print(canonical_json(result).decode("ascii"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
