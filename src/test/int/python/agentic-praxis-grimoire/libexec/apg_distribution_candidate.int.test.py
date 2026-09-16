"""End-to-end in-process qualification of the distribution candidate."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
sys.path.insert(0, os.fspath(ROOT / "libexec"))

import apg_distribution_candidate as candidate  # noqa: E402
import apg_npm_distribution as npm_distribution  # noqa: E402
import apg_python_build_backend as python_backend  # noqa: E402
import apg_python_publication as python_publication  # noqa: E402
import apg_source_capture  # noqa: E402


UNIT_ROOT = ROOT / "src/test/unit/python/agentic-praxis-grimoire/libexec"


@pytest.mark.parametrize("missing", ["docs/reference/go-library.md", "docs/public-pr-ci.md", "CLA.md"])
def test_current_sdist_document_inventory_survives_archive_validation(tmp_path, missing):
    filename = python_backend._write_sdist(ROOT, tmp_path)
    source = tmp_path / filename
    version = python_backend._version(ROOT)
    candidate._validate_sdist(source, version=version)
    trimmed = tmp_path / "trimmed.tar.gz"
    member_name = f"agentic_praxis_grimoire-{version}/{missing}"
    with tarfile.open(source, "r:gz") as original, tarfile.open(trimmed, "w:gz") as altered:
        assert original.extractfile(member_name).read() == (ROOT / missing).read_bytes()
        for member in original.getmembers():
            if member.name != member_name:
                altered.addfile(member, original.extractfile(member))
    with pytest.raises(candidate.DistributionCandidateError, match="complete Go/Python/skill source"):
        candidate._validate_sdist(trimmed, version=version)


def test_complete_release_candidate_builders_compose_in_process(
    tmp_path: Path,
) -> None:
    """Build and cross-check every local distribution from one binary matrix."""

    source = Path(os.path.realpath(tmp_path / "captured-source"))
    apg_source_capture.capture_source(ROOT, source)
    python_output = tmp_path / "python"
    python_work = tmp_path / "python-work"
    npm_output = tmp_path / "npm"
    npm_work = tmp_path / "npm-work"
    distribution_output = tmp_path / "distribution"
    python_work.mkdir(mode=0o700)
    npm_output.mkdir(mode=0o700)
    npm_work.mkdir(mode=0o700)

    python_paths = python_publication.build_bundle(
        ROOT,
        python_output,
        python_work,
        Path(sys.executable),
    )
    go_artifacts = python_work / "build-a/binaries"
    npm_records = npm_distribution.build_packages(
        ROOT,
        go_artifacts,
        npm_output,
        work_root=npm_work,
    )
    manifest = candidate.build_candidate(
        source,
        go_artifacts,
        python_output,
        npm_output,
        distribution_output,
    )

    assert len(python_paths) == 5
    assert len(npm_records) == 4
    assert manifest["schema_version"] == candidate.MANIFEST_SCHEMA
    assert manifest["version"] == (
        ROOT / "src/agentic_praxis_grimoire/VERSION"
    ).read_text(encoding="ascii").strip()
    assert len(manifest["binaries"]) == 3
    assert len(manifest["python"]["wheels"]) == 3
    assert len(manifest["npm"]["platform_packages"]) == 3
    assert manifest["source_candidate_identity"]["fingerprint"]

    manifest_path = distribution_output / candidate.MANIFEST_NAME
    assert candidate.validate_candidate(
        manifest_path,
        source,
        go_artifacts,
        python_output,
        npm_output,
    ) == manifest
    assert candidate.check(
        manifest_path,
        source,
        go_artifacts,
        python_output,
        npm_output,
    ) == manifest

    tampered = json.loads(manifest_path.read_bytes())
    tampered["version"] = "0.7.1"
    manifest_path.write_bytes(candidate.canonical_json(tampered))
    with pytest.raises(
        candidate.DistributionCandidateError,
        match="explicit artifact set",
    ):
        candidate.validate_manifest(
            manifest_path,
            source,
            go_artifacts,
            python_output,
            npm_output,
        )

    _verify_distributions(tmp_path, python_paths, npm_records, npm_output, manifest["version"])


def _run(argv: list[str], cwd: Path, environment: dict[str, str] | None = None) -> str:
    result = subprocess.run(argv, cwd=cwd, env=environment, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    assert result.returncode == 0, f"distribution command failed: {result.stderr}"
    return result.stdout


def _unpack_tar(source: Path, destination: Path, prefix: str) -> None:
    destination.mkdir(parents=True, mode=0o700)
    with tarfile.open(source, "r:gz") as archive:
        for member in archive.getmembers():
            relative = Path(member.name).relative_to(prefix)
            assert ".." not in relative.parts and not relative.is_absolute()
            target = destination / relative
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                assert member.isfile()
                stream = archive.extractfile(member)
                assert stream is not None
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(stream.read())
                target.chmod(member.mode)


def _verify_wheel(wheel: Path, work: Path, fixture: Path) -> None:
    prefix = work / "installed"
    # Install only this locally built artifact. No dependency or index access.
    pip = shutil.which("pip")
    assert pip is not None, "pip is required for local wheel installation qualification"
    _run([pip, "--python", sys.executable, "install", "--no-deps", "--no-index",
          "--ignore-installed", f"--prefix={prefix}", str(wheel)], work.parent)
    packages = list(prefix.glob("lib/python*/site-packages"))
    assert len(packages) == 1
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(packages[0])
    environment.pop("APGR_GO_BINARY", None)
    console = prefix / "bin/apgr"
    assert console.is_file()
    for argv in ([sys.executable, "-m", "agentic_praxis_grimoire"], [str(console)]):
        output = _run([*argv, "report", "verify", str(fixture)], work.parent, environment)
        assert "verified 1 record" in output


def _verify_distributions(work: Path, python_paths: tuple[Path, ...], npm_records: tuple,
                          npm_output: Path, version: str) -> None:
    fixture = ROOT / "report/testdata/persisted/diff.report.txt"
    original = fixture.read_bytes()
    original_stat = fixture.stat()
    target = python_backend._host_target()
    tag = python_backend.TARGET_TAGS[target]
    wheel = next(path for path in python_paths if path.name.endswith(f"-{tag}.whl"))
    _verify_wheel(wheel, work / "host-wheel", fixture)

    sdist = next(path for path in python_paths if path.name.endswith(".tar.gz"))
    source = work / "sdist-source"
    _unpack_tar(sdist, source, f"{python_backend.DIST_NAME}-{version}")
    wheel_output = work / "sdist-built-wheel"
    wheel_output.mkdir()
    # Invoke the backend shipped in the sdist and build its Go source. Supplying
    # a prebuilt binary would not qualify source-distribution buildability.
    program = "import sys; sys.path.insert(0, 'libexec'); import apg_python_build_backend as backend; print(backend.build_wheel(sys.argv[1]))"
    _run([sys.executable, "-c", program, str(wheel_output)], source)
    built = list(wheel_output.glob("*.whl"))
    assert len(built) == 1
    _verify_wheel(built[0], work / "sdist-wheel", fixture)

    node = shutil.which("node")
    assert node is not None, "Node is required for maintained npm runtime qualification"
    packages = work / "npm-runtime/node_modules/@knowledge-forge-ai"
    launcher = next(record for record in npm_records if record.target is None)
    native = next(record for record in npm_records if record.target == target)
    for record in (launcher, native):
        _unpack_tar(npm_output / record.filename, packages / record.name.split("/")[-1], "package")
    output = _run([node, str(packages / "apgr/index.js"), "report", "verify", str(fixture)], packages.parent)
    assert "verified 1 record" in output
    assert fixture.read_bytes() == original
    after = fixture.stat()
    assert (after.st_ino, after.st_mode, after.st_mtime_ns) == (original_stat.st_ino, original_stat.st_mode, original_stat.st_mtime_ns)


def test_release_candidate_refusal_contracts_replay_in_isolated_process(
    tmp_path: Path,
) -> None:
    """Keep archive and manifest refusal matrices live across a real child."""

    environment = os.environ.copy()
    environment["PYTEST_ADDOPTS"] = ""
    environment["PYTHONPATH"] = os.pathsep.join(
        (os.fspath(ROOT), os.fspath(ROOT / "src"), *[entry for entry in sys.path if entry])
    )
    selected = (
        "apg_distribution_candidate.unit.test.py",
        "apg_npm_distribution.unit.test.py",
        "apg_python_distribution.unit.test.py",
        "apg_python_publication.unit.test.py",
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            f"--basetemp={tmp_path / 'child-base'}",
            *(os.fspath(UNIT_ROOT / name) for name in selected),
        ],
        cwd=ROOT,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, (
        f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    )
    assert "passed" in completed.stdout
