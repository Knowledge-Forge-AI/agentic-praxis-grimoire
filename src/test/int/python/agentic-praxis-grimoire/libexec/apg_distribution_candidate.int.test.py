"""End-to-end in-process qualification of the distribution candidate."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
sys.path.insert(0, os.fspath(ROOT / "libexec"))

import apg_distribution_candidate as candidate  # noqa: E402
import apg_npm_distribution as npm_distribution  # noqa: E402
import apg_python_publication as python_publication  # noqa: E402


UNIT_ROOT = ROOT / "src/test/unit/python/agentic-praxis-grimoire/libexec"


def test_complete_release_candidate_builders_compose_in_process(
    tmp_path: Path,
) -> None:
    """Build and cross-check every local distribution from one binary matrix."""

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
        ROOT,
        go_artifacts,
        python_output,
        npm_output,
        distribution_output,
    )

    assert len(python_paths) == 5
    assert len(npm_records) == 4
    assert manifest["schema_version"] == candidate.MANIFEST_SCHEMA
    assert manifest["version"] == "0.7.0"
    assert len(manifest["binaries"]) == 3
    assert len(manifest["python"]["wheels"]) == 3
    assert len(manifest["npm"]["platform_packages"]) == 3
    assert manifest["source_candidate_identity"]["fingerprint"]

    manifest_path = distribution_output / candidate.MANIFEST_NAME
    assert candidate.validate_candidate(
        manifest_path,
        ROOT,
        go_artifacts,
        python_output,
        npm_output,
    ) == manifest
    assert candidate.check(
        manifest_path,
        ROOT,
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
            ROOT,
            go_artifacts,
            python_output,
            npm_output,
        )


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
