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
WHEEL = "agentic_praxis_grimoire-0.5.0-py3-none-any.whl"
SDIST = "agentic_praxis_grimoire-0.5.0.tar.gz"


def _verification_script() -> str:
    workflow = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    return workflow["jobs"]["publish"]["steps"][0]["run"]


def _fixture(
    tmp_path: Path,
    *,
    corrupt: bool = False,
    tag: str = "v0.5.0",
    extra_asset: bool = False,
    draft: bool = False,
    prerelease: bool = False,
    omit_asset: bool = False,
    malformed_checksums: bool = False,
) -> tuple[Path, Path]:
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / WHEEL).write_bytes(b"exact wheel bytes")
    (assets / SDIST).write_bytes(b"exact normalized sdist bytes")
    wheel_digest = hashlib.sha256((assets / WHEEL).read_bytes()).hexdigest()
    sdist_digest = hashlib.sha256((assets / SDIST).read_bytes()).hexdigest()
    if corrupt:
        wheel_digest = "0" * 64
    manifest = f"{wheel_digest}  {WHEEL}\n{sdist_digest}  {SDIST}\n"
    if malformed_checksums:
        manifest += f"{sdist_digest}  {SDIST}\n"
    (assets / "SHA256SUMS").write_text(
        manifest,
        encoding="ascii",
    )
    event = tmp_path / "event.json"
    release_assets = [
        {"id": 1, "name": WHEEL},
        {"id": 2, "name": SDIST},
        {"id": 3, "name": "SHA256SUMS"},
    ]
    if extra_asset:
        release_assets.append({"id": 4, "name": "unexpected.whl"})
    if omit_asset:
        release_assets.pop()
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
    corrupt: bool = False,
    tag: str = "v0.5.0",
    extra_asset: bool = False,
    draft: bool = False,
    prerelease: bool = False,
    omit_asset: bool = False,
    malformed_checksums: bool = False,
    repository: str = "Knowledge-Forge-AI/agentic-praxis-grimoire",
) -> subprocess.CompletedProcess[str]:
    assets, event = _fixture(
        tmp_path,
        corrupt=corrupt,
        tag=tag,
        extra_asset=extra_asset,
        draft=draft,
        prerelease=prerelease,
        omit_asset=omit_asset,
        malformed_checksums=malformed_checksums,
    )
    commands = tmp_path / "bin"
    commands.mkdir()
    fake = commands / "gh"
    fake.write_text(
        """#!/usr/bin/env python3
from pathlib import Path
import os
import shutil
import sys

names = {"1": "agentic_praxis_grimoire-0.5.0-py3-none-any.whl", "2": "agentic_praxis_grimoire-0.5.0.tar.gz", "3": "SHA256SUMS"}
asset_id = sys.argv[-1].rsplit("/", 1)[-1]
with (Path(os.environ["APG_FAKE_ASSETS"]) / names[asset_id]).open("rb") as source:
    shutil.copyfileobj(source, sys.stdout.buffer)
""",
        encoding="utf-8",
    )
    fake.chmod(0o700)
    checksum = commands / "sha256sum"
    checksum.write_text(
        """#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

manifest = Path(sys.argv[-1])
failed = False
for line in manifest.read_text(encoding="ascii").splitlines():
    expected, name = line.split("  ", 1)
    observed = hashlib.sha256(Path(name).read_bytes()).hexdigest()
    status = "OK" if observed == expected else "FAILED"
    print(f"{name}: {status}")
    failed = failed or status == "FAILED"
raise SystemExit(1 if failed else 0)
""",
        encoding="utf-8",
    )
    checksum.chmod(0o700)
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
    assert sorted(path.name for path in verified.iterdir()) == [WHEEL, SDIST]
    assert (verified / WHEEL).read_bytes() == b"exact wheel bytes"
    assert (verified / SDIST).read_bytes() == b"exact normalized sdist bytes"
    assert sorted(path.name for path in (tmp_path / "checksums").iterdir()) == [
        "SHA256SUMS"
    ]


def test_verification_step_stops_on_checksum_mismatch(tmp_path: Path) -> None:
    result = _run(tmp_path, corrupt=True)

    assert result.returncode != 0
    assert "FAILED" in result.stdout or "FAILED" in result.stderr


@pytest.mark.parametrize(
    "arguments",
    (
        {"tag": "v0.5.1"},
        {"extra_asset": True},
        {"draft": True},
        {"prerelease": True},
        {"omit_asset": True},
        {"malformed_checksums": True},
        {"repository": "unexpected/example"},
    ),
)
def test_verification_step_rejects_unexpected_release_identity(
    tmp_path: Path, arguments: dict[str, object]
) -> None:
    result = _run(tmp_path, **arguments)

    assert result.returncode != 0
