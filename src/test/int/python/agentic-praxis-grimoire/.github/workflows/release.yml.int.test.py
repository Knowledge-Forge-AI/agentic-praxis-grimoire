"""Execute the release-asset verification step against a fake GitHub API."""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import os
import subprocess

import pytest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "release.yml"
VERSION = (
    REPOSITORY_ROOT / "src" / "agentic_praxis_grimoire" / "VERSION"
).read_text(encoding="utf-8").strip()
DEFAULT_TAG = f"v{VERSION}"


def _distribution_filenames(version: str) -> tuple[list[str], str, str]:
    wheel_darwin = f"agentic_praxis_grimoire-{version}-py3-none-macosx_11_0_arm64.whl"
    wheel_linux_x64 = f"agentic_praxis_grimoire-{version}-py3-none-manylinux_2_17_x86_64.whl"
    wheel_linux_arm64 = f"agentic_praxis_grimoire-{version}-py3-none-manylinux_2_17_aarch64.whl"
    wheels = [wheel_darwin, wheel_linux_x64, wheel_linux_arm64]
    sdist = f"agentic_praxis_grimoire-{version}.tar.gz"
    npm_tarball = f"knowledge-forge-ai-apgr-{version}.tgz"
    return wheels, sdist, npm_tarball


WHEELS, SDIST, NPM_TARBALL = _distribution_filenames(VERSION)
WHEEL_DARWIN, WHEEL_LINUX_X64, WHEEL_LINUX_ARM64 = WHEELS
EXPECTED_PYTHON_DIST = [*WHEELS, SDIST]
MANIFEST_NAME = "apg-distribution-manifest.json"


def _verification_script() -> str:
    workflow = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    return workflow["jobs"]["publish"]["steps"][0]["run"]


def _fixture(
    tmp_path: Path,
    *,
    corrupt_wheel: bool = False,
    corrupt_sdist: bool = False,
    manifest_corrupt_wheel_hash: bool = False,
    manifest_corrupt_version: bool = False,
    manifest_missing_wheel: bool = False,
    tag: str = DEFAULT_TAG,
    fixture_version: str | None = None,
    extra_wheel: bool = False,
    extra_sdist: bool = False,
    universal_wheel: bool = False,
    draft: bool = False,
    prerelease: bool = False,
    omit_asset: bool = False,
    duplicate_asset: bool = False,
    malformed_checksums: bool = False,
    include_non_python_assets: bool = True,
) -> tuple[Path, Path]:
    active_version = fixture_version if fixture_version is not None else VERSION
    active_wheels, active_sdist, active_npm = _distribution_filenames(active_version)
    active_wheel_darwin = active_wheels[0]

    assets = tmp_path / "assets"
    assets.mkdir()
    asset_map: dict[str, bytes] = {
        active_wheels[0]: b"exact darwin wheel bytes",
        active_wheels[1]: b"exact linux x64 wheel bytes",
        active_wheels[2]: b"exact linux arm64 wheel bytes",
        active_sdist: b"exact normalized sdist bytes",
    }

    digests: dict[str, str] = {}
    for name, content in asset_map.items():
        digests[name] = hashlib.sha256(content).hexdigest()

    if corrupt_wheel:
        digests[active_wheels[0]] = "0" * 64
    if corrupt_sdist:
        digests[active_sdist] = "0" * 64

    wheels_manifest = [
        {"name": active_wheels[0], "sha256": digests[active_wheels[0]]},
        {"name": active_wheels[1], "sha256": digests[active_wheels[1]]},
        {"name": active_wheels[2], "sha256": digests[active_wheels[2]]},
    ]
    if manifest_corrupt_wheel_hash:
        wheels_manifest[0]["sha256"] = "f" * 64
    if manifest_missing_wheel:
        wheels_manifest = wheels_manifest[:2]

    manifest_obj = {
        "schema_version": "apg.distribution-manifest/v1",
        "version": "0.7.0" if manifest_corrupt_version else active_version,
        "python": {
            "package": "agentic-praxis-grimoire",
            "wheels": wheels_manifest,
            "sdist": {
                "name": active_sdist,
                "sha256": digests[active_sdist],
            },
        },
    }

    if include_non_python_assets:
        asset_map[active_npm] = b"exact npm tarball bytes"
        digests[active_npm] = hashlib.sha256(asset_map[active_npm]).hexdigest()
        manifest_bytes = json.dumps(manifest_obj, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
        asset_map[MANIFEST_NAME] = manifest_bytes
        digests[MANIFEST_NAME] = hashlib.sha256(manifest_bytes).hexdigest()

    for name, content in asset_map.items():
        (assets / name).write_bytes(content)

    manifest_lines = [f"{digests[name]}  {name}" for name in sorted(asset_map)]
    if malformed_checksums:
        manifest_lines.append(f"{digests[active_sdist]}  {active_sdist}")

    (assets / "SHA256SUMS").write_text(
        "\n".join(manifest_lines) + "\n",
        encoding="ascii",
    )

    release_assets = [
        {"id": idx + 1, "name": name}
        for idx, name in enumerate(sorted([*asset_map.keys(), "SHA256SUMS"]))
    ]

    if extra_wheel:
        (assets / "unexpected.whl").write_bytes(b"extra wheel")
        release_assets.append({"id": 101, "name": "unexpected.whl"})
    if universal_wheel:
        universal_name = f"agentic_praxis_grimoire-{active_version}-py3-none-any.whl"
        (assets / universal_name).write_bytes(b"universal wheel")
        release_assets.append({"id": 102, "name": universal_name})
    if extra_sdist:
        extra_sdist_name = f"agentic_praxis_grimoire-{active_version}-extra.tar.gz"
        (assets / extra_sdist_name).write_bytes(b"extra sdist")
        release_assets.append({"id": 103, "name": extra_sdist_name})
    if duplicate_asset:
        release_assets.append({"id": 104, "name": active_wheel_darwin})
    if omit_asset:
        # remove one of the required wheels
        release_assets = [a for a in release_assets if a["name"] != active_wheel_darwin]

    event = tmp_path / "event.json"
    event.write_text(
        json.dumps(
            {
                "release": {
                    "id": 84,
                    "tag_name": tag,
                    "draft": draft,
                    "prerelease": prerelease,
                    "assets": release_assets,
                }
            }
        ),
        encoding="utf-8",
    )
    return assets, event


def _run(
    tmp_path: Path,
    *,
    corrupt_wheel: bool = False,
    corrupt_sdist: bool = False,
    manifest_corrupt_wheel_hash: bool = False,
    manifest_corrupt_version: bool = False,
    manifest_missing_wheel: bool = False,
    tag: str = DEFAULT_TAG,
    fixture_version: str | None = None,
    extra_wheel: bool = False,
    extra_sdist: bool = False,
    universal_wheel: bool = False,
    draft: bool = False,
    prerelease: bool = False,
    omit_asset: bool = False,
    duplicate_asset: bool = False,
    malformed_checksums: bool = False,
    include_non_python_assets: bool = True,
    repository: str = "Knowledge-Forge-AI/agentic-praxis-grimoire",
) -> subprocess.CompletedProcess[str]:
    assets, event = _fixture(
        tmp_path,
        corrupt_wheel=corrupt_wheel,
        corrupt_sdist=corrupt_sdist,
        manifest_corrupt_wheel_hash=manifest_corrupt_wheel_hash,
        manifest_corrupt_version=manifest_corrupt_version,
        manifest_missing_wheel=manifest_missing_wheel,
        tag=tag,
        fixture_version=fixture_version,
        extra_wheel=extra_wheel,
        extra_sdist=extra_sdist,
        universal_wheel=universal_wheel,
        draft=draft,
        prerelease=prerelease,
        omit_asset=omit_asset,
        duplicate_asset=duplicate_asset,
        malformed_checksums=malformed_checksums,
        include_non_python_assets=include_non_python_assets,
    )
    commands = tmp_path / "bin"
    commands.mkdir()
    fake = commands / "gh"
    fake.write_text(
        """#!/usr/bin/env python3
from pathlib import Path
import json
import os
import shutil
import sys

event_path = Path(os.environ["GITHUB_EVENT_PATH"])
event = json.loads(event_path.read_text(encoding="utf-8"))
asset_id = int(sys.argv[-1].rsplit("/", 1)[-1])
name = next(a["name"] for a in event["release"]["assets"] if a["id"] == asset_id)
with (Path(os.environ["APG_FAKE_ASSETS"]) / name).open("rb") as source:
    shutil.copyfileobj(source, sys.stdout.buffer)
""",
        encoding="utf-8",
    )
    fake.chmod(0o700)
    environment = {
        "APG_FAKE_ASSETS": os.fspath(assets),
        "GH_TOKEN": "bounded-test-token",
        "GITHUB_EVENT_PATH": os.fspath(event),
        "GITHUB_REPOSITORY": repository,
        "PATH": os.fspath(commands) + os.pathsep + os.environ["PATH"],
    }
    return subprocess.run(
        ["bash", "-c", _verification_script()],
        cwd=tmp_path,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_verification_step_selects_the_exact_checked_distribution_paths(
    tmp_path: Path,
) -> None:
    result = _run(tmp_path)

    assert result.returncode == 0, result.stderr
    verified = tmp_path / "verified-dist"
    assert sorted(path.name for path in verified.iterdir()) == sorted(EXPECTED_PYTHON_DIST)
    assert (verified / WHEEL_DARWIN).read_bytes() == b"exact darwin wheel bytes"
    assert (verified / WHEEL_LINUX_X64).read_bytes() == b"exact linux x64 wheel bytes"
    assert (verified / WHEEL_LINUX_ARM64).read_bytes() == b"exact linux arm64 wheel bytes"
    assert (verified / SDIST).read_bytes() == b"exact normalized sdist bytes"
    assert sorted(path.name for path in (tmp_path / "manifests").iterdir()) == [
        "SHA256SUMS",
        "apg-distribution-manifest.json",
    ]


def test_verification_step_stops_on_wheel_checksum_mismatch(tmp_path: Path) -> None:
    result = _run(tmp_path, corrupt_wheel=True)

    assert result.returncode != 0


def test_verification_step_stops_on_sdist_checksum_mismatch(tmp_path: Path) -> None:
    result = _run(tmp_path, corrupt_sdist=True)

    assert result.returncode != 0


def test_verification_step_stops_on_manifest_wheel_hash_mismatch(tmp_path: Path) -> None:
    result = _run(tmp_path, manifest_corrupt_wheel_hash=True)

    assert result.returncode != 0


def test_verification_step_stops_on_manifest_version_mismatch(tmp_path: Path) -> None:
    result = _run(tmp_path, manifest_corrupt_version=True)

    assert result.returncode != 0


def test_verification_step_stops_on_manifest_missing_wheel(tmp_path: Path) -> None:
    result = _run(tmp_path, manifest_missing_wheel=True)

    assert result.returncode != 0


# These historical rejection cases assume monotonically increasing releases;
# restoring one as VERSION requires revisiting the corresponding negative.
@pytest.mark.parametrize(
    "arguments",
    (
        {"tag": "v0.6.0"},
        {"tag": "v0.7.1"},
        {"tag": "v0.8.1"},
        {"tag": "v0.9.0"},
        {"fixture_version": "0.9.0"},
        {"fixture_version": "0.9.0", "tag": "v0.9.0"},
        {"extra_wheel": True},
        {"universal_wheel": True},
        {"extra_sdist": True},
        {"draft": True},
        {"prerelease": True},
        {"omit_asset": True},
        {"duplicate_asset": True},
        {"malformed_checksums": True},
        {"repository": "unexpected/example"},
    ),
)
def test_verification_step_rejects_unexpected_release_identity(
    tmp_path: Path, arguments: dict[str, object]
) -> None:
    result = _run(tmp_path, **arguments)

    assert result.returncode != 0
